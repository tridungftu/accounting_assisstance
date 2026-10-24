"""M9 typed + common M0/K2/K5/money trên PostgreSQL thật (binding 28af9c1, proposal e3e9704f).

- Migration: fresh → 13 (chạy lại idempotent); DB dừng ở 12 có CRM DIRECT + HUY + lịch trả nợ cũ → 13 giữ dữ liệu/checksum, phân loại link.
- Luồng DEMO: nhận nguồn #9 (profile pin) → snapshot/row không PN → CFO map công ty/ngân hàng/dự án → KT lập HĐ VAY/phiên bản theo PN
  (nguyên tử) → KT kiểm (vân tay đồ thị) → CFO duyệt V3/V4 → tiền M1 (Store.ingest + bộ chiếu + proof) → xem trước/xác nhận/gỡ nối tiền
  (parent CHILD + child, biên nhận) → revision xuyên đích → LC→SHORT cùng alias → S05/S09/S10/S04/S16 giữ chờ → retarget → file soát → HTTP.
- Âm có đối chứng dương: quyền hành động/module/PN, RLS, discriminator, bất biến typed, digest cũ, proof thiếu/lệch, ngân sách chung CRM+M9,
  race hai domain, idempotency.
Dữ liệu DEMO, actor MO_PHONG_*. Chạy khi có KHO_PG_DSN_TEST (runner retained). Không DROP database/role/file: giữ làm bằng chứng."""

from __future__ import annotations

import os
import secrets
import tempfile
import threading
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang import postgres as pg
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.pg_migrations import PG_MIGRATIONS, PG_SCHEMA_VERSION
from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json, sha256
from kho_tri_thuc.k2 import crm_demo, m1_demo
from kho_tri_thuc.k2.crm import CrmK2
from kho_tri_thuc.k2.vay import VayK2
from kho_tri_thuc.kiem_chung import fixtures_crm as FC
from kho_tri_thuc.kiem_chung import fixtures_m9 as F

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
ROOT = Path(__file__).resolve().parents[1]
KTA, KTB, CFO, CFO_V3, BH = "MO_PHONG_KT_A", "MO_PHONG_KT_B", "MO_PHONG_CFO", "MO_PHONG_CFO_CHI_V3", "MO_PHONG_BAN_HANG"
XEM_CRM, XEM_M9, KT_KHONG_M1 = "MO_PHONG_XEM_A", "MO_PHONG_XEM_M9_A", "MO_PHONG_KT_M9_KHONG_M1_A"
KV_A, NH_A, KV_B = "DaiHan/CT_DEMO_A/KV-A-01", "VayNganHan/CT_DEMO_A/NH-A-01", "DaiHan/CT_DEMO_B/KV-B-01"
H = lambda statements: sha256("\n".join(statements).encode())  # noqa: E731


def _db(prefix):
    name = prefix + uuid.uuid4().hex[:8]
    with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
        a.execute(f'CREATE DATABASE "{name}" ENCODING \'UTF8\' TEMPLATE template0')
    return name, ADMIN_DSN.rsplit("/", 1)[0] + "/" + name


class _Luong(threading.Thread):
    def __init__(self, fn, barrier):
        super().__init__(daemon=True)
        self.fn, self.barrier, self.ket_qua, self.loi = fn, barrier, None, None

    def run(self):
        try:
            self.barrier.wait(10)
            self.ket_qua = self.fn()
        except Exception as exc:  # noqa: BLE001
            self.loi = exc


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — không chạy được (không tính đạt)")
class M9MigrationTest(unittest.TestCase):
    def test_m01_fresh_len_13(self):
        name, dsn = _db("kho_test_m9_fresh_")
        with psycopg.connect(dsn, autocommit=True) as c:
            self.assertEqual(pg.migrate(c), PG_SCHEMA_VERSION)
            self.assertEqual(pg.migrate(c), PG_SCHEMA_VERSION)
            self.assertEqual(PG_SCHEMA_VERSION, 13)
            self.assertEqual([r[0] for r in c.execute("SELECT checksum FROM master.schema_migrations ORDER BY version")], [H(m) for m in PG_MIGRATIONS])
            self.assertEqual(c.execute("SELECT count(*) FROM master.don_vi_tien").fetchone()[0], 2)

    def test_m02_nang_cap_tu_12_co_crm_direct_huy_va_lich_tra_no_cu(self):
        """DB dừng ở 12 có HĐ CRM đã duyệt, link DIRECT hiệu lực + DIRECT đã hủy có vết + link bằng chứng + lịch trả nợ cũ → 13."""
        name, dsn = _db("kho_test_m9_up12_")
        with psycopg.connect(dsn, autocommit=True) as c:
            self.assertEqual(pg.migrate(c, target=12), 12)
            hist = [tuple(r) for r in c.execute("SELECT version, checksum, applied_at FROM master.schema_migrations ORDER BY version")]
            with c.transaction():  # dữ liệu "đã có" dựng bằng chủ CSDL ở chế độ replica (không qua trigger nghiệp vụ) — chỉ để có dòng lịch sử
                c.execute("SET LOCAL session_replication_role = replica")
                pn = c.execute("INSERT INTO master.phap_nhan (ma, ten) VALUES ('PN_UP12_DEMO','DEMO nâng cấp') RETURNING id").fetchone()[0]
                hd = c.execute("INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong) VALUES (%s,'THUE_DAT','UP12-1','UP12/1') RETURNING id", (pn,)).fetchone()[0]
                ct6 = c.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash) VALUES (%s,'HOP_DONG_TEP','UP12-6','2026-08-01',%s)
                                   RETURNING id""", (pn, "1" * 64)).fetchone()[0]
                pb = c.execute("""INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon, trang_thai, chung_tu_id, valid_from)
                                  VALUES (%s,1,'TAY','DA_DUYET',%s,'2026-08-01T00:00:00+00') RETURNING id""", (hd, ct6)).fetchone()[0]
                lt = c.execute("INSERT INTO master.lich_thu (phien_ban_id, phap_nhan_id, dot, so_tien_minor, khoa_nghia_vu) VALUES (%s,%s,1,1000,'DOT-1') RETURNING id",
                               (pb, pn)).fetchone()[0]
                bank = c.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, tien_te, so_tien_minor, chieu, hash)
                                    VALUES (%s,'SAO_KE','UP12-SK','2026-08-02','VND',5000,'THU',%s) RETURNING id""", (pn, "2" * 64)).fetchone()[0]
                for so, tt in ((700, "DA_KHOP"), (300, "HUY")):
                    c.execute("""INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai, so_tien_khop_minor, trang_thai, lich_thu_id, hop_dong_id,
                                 huy_luc, huy_boi, ly_do_huy) VALUES (%s,%s,%s,'HOP_DONG_DOT_TIEN',%s,%s,%s,%s,%s,%s,%s)""",
                              (pn, bank, ct6, so, tt, lt, hd, "2026-08-03" if tt == "HUY" else None, "MO_PHONG_KT_UP12" if tt == "HUY" else None,
                               "DEMO hủy" if tt == "HUY" else None))
                c.execute("INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai) VALUES (%s,%s,%s,'KHAC')", (pn, ct6, bank))
                pbv = c.execute("INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong) VALUES (%s,'VAY','UP12-V','UP12/V') RETURNING id", (pn,)).fetchone()[0]
                pbv = c.execute("INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon) VALUES (%s,1,'TAY') RETURNING id", (pbv,)).fetchone()[0]
                c.execute("INSERT INTO master.lich_tra_no (phien_ban_id, ky, goc_minor, lai_minor) VALUES (%s,1,100,10)", (pbv,))
            snap = lambda: [[tuple(r) for r in c.execute(f"SELECT {cols} FROM {t} ORDER BY 1")] for t, cols in (  # noqa: E731
                ("master.hop_dong", "id, loai, so_hop_dong"), ("master.hop_dong_phien_ban", "id, trang_thai, valid_from"), ("master.lich_thu", "id, so_tien_minor"),
                ("kho.lien_ket_chung_tu", "id, so_tien_khop_minor, trang_thai, huy_boi"), ("master.lich_tra_no", "id, ky, goc_minor, lai_minor"))]
            truoc = snap()
            self.assertEqual(pg.migrate(c), 13)
            self.assertEqual(snap(), truoc)
            sau = [tuple(r) for r in c.execute("SELECT version, checksum, applied_at FROM master.schema_migrations ORDER BY version")]
            self.assertEqual((sau[:12], sau[12][:2]), (hist, (13, H(PG_MIGRATIONS[12]))))
            phan_loai = sorted(tuple(r) for r in c.execute("SELECT trang_thai, link_purpose, allocation_model FROM kho.lien_ket_chung_tu"))
            self.assertEqual(phan_loai, [("CHO", "EVIDENCE", None), ("DA_KHOP", "MONEY", "DIRECT"), ("HUY", "MONEY", "DIRECT")])
            self.assertEqual(dict(c.execute("SELECT loai, module_nghiep_vu FROM kho.chung_tu").fetchall()), {"HOP_DONG_TEP": "CRM", "SAO_KE": "M1"})
            self.assertEqual(c.execute("SELECT kho.tien_da_phan_bo_noi_bo(%s)", (bank,)).fetchone()[0], 700)  # DIRECT hiệu lực, HUY không trừ
            self.assertEqual(tuple(c.execute("SELECT model_version, phap_nhan_id = %s FROM master.lich_tra_no", (pn,)).fetchone()), ("LEGACY", True))
            with self.assertRaises(psycopg.errors.UniqueViolation):  # khóa (PB, kỳ) của lịch cũ vẫn giữ
                with c.transaction():
                    c.execute("SET LOCAL session_replication_role = replica")
                    c.execute("INSERT INTO master.lich_tra_no (phien_ban_id, ky, goc_minor, lai_minor) VALUES (%s,1,1,1)", (pbv,))
            with self.assertRaises(psycopg.Error) as ctx:  # lịch cũ không ghi mới (chỉ M9_TYPED qua kiểm ghi nháp)
                c.execute("INSERT INTO master.lich_tra_no (phien_ban_id, ky, goc_minor, lai_minor) VALUES (%s,2,1,1)", (pbv,))
            self.assertIn("M9_LICH_LEGACY_KHONG_GHI_MOI", str(ctx.exception))
            self.assertEqual(pg.migrate(c), 13)


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — không chạy được (không tính đạt)")
class M9K2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db, cls.dsn = _db("kho_test_m9_")
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        pg.migrate(cls.admin)
        cls.ids = crm_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_m9_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.app = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row)
        cls.app2 = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row)
        cls.root = Path(tempfile.mkdtemp(prefix="ktt_m9_k2_"))
        cls.vay, cls.vay2 = VayK2(cls.app, cls.root / "k2"), VayK2(cls.app2, cls.root / "k2")
        cls.crm = CrmK2(cls.app, cls.root / "k2")
        cls.cfg = Config.load(ROOT / "cau_hinh.toml", cls.root / "mo-phong")
        cls.s = {}

    @classmethod
    def tearDownClass(cls):
        for c in (cls.app, cls.app2, cls.admin):
            c.close()  # giữ DB/role/thư mục làm bằng chứng

    # ------------------------------------------------------------------ helper
    def raises(self, code, fn):
        with self.assertRaises((DataError, psycopg.Error)) as ctx:
            fn()
        self.assertIn(code, getattr(ctx.exception, "code", "") + str(ctx.exception))
        return ctx.exception

    def q(self, sql, params=()):
        return self.admin.execute(sql, params).fetchall()

    def sql(self, login, sql, params=()):
        """SQL thẳng bằng vai trò app_web với danh tính phiên đặt tay (client bỏ qua service)."""
        nd = self.q("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s", (login,))[0][0]
        with self.app.transaction():
            self.app.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (nd, login))
            cur = self.app.execute(sql, params)
            return cur.fetchall() if cur.description else cur.rowcount

    def lap(self, actor, snap, pn):
        return {r["khoa"]: r for r in self.vay.lap_phien_ban(actor, snap, pn)["khoan_vay"]}

    def loan(self, actor, khoa):
        return next(h for h in self.vay.danh_sach(actor)["khoan_vay"] if h["khoa_nguon"] == khoa)

    def hieu_luc(self, actor, khoa):
        h = self.loan(actor, khoa)
        return next(v for v in h["phien_ban"] if v["hieu_luc_hom_nay"])

    def m1(self, pn, actor, giao_dich, doi_tac):
        r = m1_demo.nhan_sao_ke(self.cfg, self.root / "m1", pn, giao_dich, actor, doi_tac)
        c = m1_demo.chieu_sang_k2(r["sqlite"], self.dsn)
        self.assertEqual((c["ok"], c["da_ghi"], c.get("lech_dem"), c.get("lech_noi_dung")), (True, True, [], []), c)
        return r

    def bank(self, ref):
        return str(self.q("SELECT id FROM kho.chung_tu WHERE loai = 'SAO_KE' AND du_lieu->>'reference' = %s", (ref,))[0][0])

    def con_lai(self, actor, bank):
        return next(t for t in self.vay.danh_sach(actor)["tien"] if t["id"] == bank)

    # ------------------------------------------------------------------ M0/K1 intake
    def test_m01_nhan_nguon_giu_raw_snapshot_khong_pn_va_quyen(self):
        r = self.vay.nhan_mau(KTA, "native_v6")
        self.assertEqual((r["moi"], r["trang_thai"], r["pham_vi"], r["loi"]), (True, "VALIDATED", "FULL_SHAPE", []))
        self.assertEqual(r["cong_ty_cho_map"], ["CT_DEMO_A", "CT_DEMO_B"])  # chưa map: row giữ không PN, không ép PN giả
        self.assertEqual(r["so_dong"]["LichTraGoc"], 3)
        self.s["snap1"] = r["snapshot_id"]
        self.assertTrue((self.root / "k2" / "m9-tep" / f"{r['raw_sha256']}.bin").is_file())
        self.assertEqual(self.q("SELECT count(*) FROM kho.ban_ghi_nguon WHERE snapshot_id = %s AND phap_nhan_id IS NULL", (r["snapshot_id"],))[0][0], 15)
        lai = self.vay.nhan_mau(KTA, "native_v6")
        self.assertEqual((lai["moi"], lai["snapshot_id"]), (False, r["snapshot_id"]))  # cùng raw/profile → cùng snapshot
        self.assertEqual(self.q("SELECT count(*) FROM kho.anh_chup_nguon")[0][0], 1)
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.nhan_mau(XEM_M9, "native_v6"))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.nhan_mau(CFO, "native_v6"))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.nhan_mau(BH, "native_v6"))
        self.raises("M9_KHONG_CO_QUYEN_NHAN", lambda: self.sql(BH, "SELECT * FROM giao_tiep.ghi_anh_chup('{}'::jsonb)"))
        self.raises("permission denied", lambda: self.sql(KTA, "SELECT count(*) FROM giao_tiep.tep_tiep_nhan"))  # metadata raw toàn phần chỉ integration
        self.assertEqual(self.sql(KTA, "SELECT count(*) AS n FROM kho.ban_ghi_nguon")[0]["n"], 0)  # row chưa PN không lộ qua RLS
        self.raises("M9_MAU", lambda: self.vay.nhan_mau(KTA, "../../duong_dan_tuy_y"))

    def test_m02_shape_partial_va_profile_root_bi_tu_choi(self):
        p = self.vay.nhan_mau(KTA, "native_v6_thieu_key")
        self.assertEqual((p["trang_thai"], p["pham_vi"]), ("PARTIAL", "PARTIAL"))
        self.s["snap_partial"] = p["snapshot_id"]
        r = self.vay.nhan_mau(KTA, "native_root_khong_ho_tro")
        self.assertEqual(r["trang_thai"], "REJECTED")
        self.assertTrue(any(x.startswith("HEADER_KHONG_KHOP_PROFILE:LichTraGoc") for x in r["loi"]))
        self.assertEqual(self.q("SELECT count(*) FROM kho.ban_ghi_nguon WHERE snapshot_id = %s", (r["snapshot_id"],))[0][0], 0)
        self.raises("SNAPSHOT_TU_CHOI", lambda: self.vay.lap_phien_ban(KTA, r["snapshot_id"], "PN_DEMO_A"))

    # ------------------------------------------------------------------ mapping CFO V4 + M9, overlap, ranh giới PN
    def test_m03_mapping_cong_ty_ngan_hang_du_an(self):
        self.raises("M9_CHUA_CO_CONG_TY_MAP", lambda: self.vay.lap_phien_ban(KTA, self.s["snap1"], "PN_DEMO_A"))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.xac_nhan_anh_xa(KTA, "COMPANY", "CT_DEMO_A", "PN_DEMO_A"))
        self.raises("KHONG_CO_QUYEN_LOAI_VIEC", lambda: self.vay.xac_nhan_anh_xa(CFO_V3, "COMPANY", "CT_DEMO_A", "PN_DEMO_A"))
        nd = self.q("SELECT id FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'")[0][0]
        self.raises("ANH_XA_KHONG_CO_QUYEN", lambda: self.sql(KTA, """INSERT INTO master.anh_xa_nguon (source_instance_id, source_company_key, kind, source_value,
                    phap_nhan_id, revision, duyet_boi) VALUES ('SHEET_VAY_DEMO_1','CT_DEMO_A','COMPANY','CT_DEMO_A',%s,1,'MO_PHONG_KT_A')""", (nd,)))
        a = self.vay.xac_nhan_anh_xa(CFO, "COMPANY", "CT_DEMO_A", "PN_DEMO_A", ly_do="DEMO")
        self.assertGreater(a["so_dong_gan_phap_nhan"], 0)
        self.s["map_a"] = a["id"]
        self.raises("ANH_XA_CHONG_LAN", lambda: self.vay.xac_nhan_anh_xa(CFO, "COMPANY", "CT_DEMO_A", "PN_DEMO_B"))
        self.s["map_b"] = self.vay.xac_nhan_anh_xa(CFO, "COMPANY", "CT_DEMO_B", "PN_DEMO_B")["id"]
        self.raises("MAPPING_KHONG_CO_MA", lambda: self.vay.xac_nhan_anh_xa(CFO, "BANK", "CT_DEMO_A", "NH_DEMO.B", source_value="NH_DEMO"))
        for cty, ma, da in (("CT_DEMO_B", "NH_DEMO.B", "DA_NHA_DEMO"),):
            self.vay.xac_nhan_anh_xa(CFO, "BANK", cty, ma, source_value="NH_DEMO")
            self.vay.xac_nhan_anh_xa(CFO, "PROJECT", cty, da, source_value=da)
        rows = lambda who: {r["pn"] for r in self.sql(who, "SELECT p.ma AS pn FROM kho.ban_ghi_nguon b JOIN master.phap_nhan p ON p.id = b.phap_nhan_id")}  # noqa: E731
        self.assertEqual((rows(KTA), rows(KTB)), ({"PN_DEMO_A"}, {"PN_DEMO_B"}))  # RLS theo PN của row
        ds = self.vay.danh_sach(CFO)
        self.assertEqual({(u["kind"], u["cong_ty"], u["nguon"]) for u in ds["ung_vien_anh_xa"]}, {("BANK", "CT_DEMO_A", "NH_DEMO"), ("PROJECT", "CT_DEMO_A", "DA_KCN_DEMO")})
        self.assertEqual(ds["cong_ty_cho_map"], [])

    # ------------------------------------------------------------------ lập HĐ/phiên bản typed (S01, NULL≠0, LC, bảng lãi), holding mapping
    def test_m04_lap_phien_ban_pn_a_giu_cho_mapping_roi_bo_sung(self):
        r = self.lap(KTA, self.s["snap1"], "PN_DEMO_A")
        self.assertEqual(set(r), {KV_A, NH_A})  # chỉ alias của công ty đã map vào PN_A
        self.assertEqual((r[KV_A]["ket_qua"], r[NH_A]["ket_qua"], r[NH_A]["financing_kind"]), ("TAO_MOI", "TAO_MOI", "LC"))
        self.assertIn("MAPPING_NGAN_HANG", r[KV_A]["chan"])  # thiếu mapping ngân hàng → giữ chờ, vẫn có HĐ/phiên bản để bổ sung
        self.assertIn("MAPPING_NGAN_HANG_NGUON", r[KV_A]["chan"])
        self.raises("M9_CHUA_DU_DIEU_KIEN", lambda: self.vay.kiem(KTA, r[KV_A]["phien_ban_id"]))
        self.vay.xac_nhan_anh_xa(CFO, "BANK", "CT_DEMO_A", "NH_DEMO.A", source_value="NH_DEMO")
        self.vay.xac_nhan_anh_xa(CFO, "PROJECT", "CT_DEMO_A", "DA_KCN_DEMO", source_value="DA_KCN_DEMO")
        bl = self.vay.nhan_mau(KTA, "bang_lai_xac_nhan")
        self.assertEqual((bl["trang_thai"], bl["cong_ty_cho_map"]), ("VALIDATED", []))  # công ty đã map: row bảng lãi có PN ngay
        r2 = self.lap(KTA, self.s["snap1"], "PN_DEMO_A")
        self.assertEqual((r2[KV_A]["ket_qua"], r2[KV_A]["hop_dong_id"], r2[KV_A]["chan"]), ("PHIEN_BAN_MOI", r[KV_A]["hop_dong_id"], []))
        self.assertEqual((r2[NH_A]["ket_qua"], r2[NH_A]["chan"]), ("PHIEN_BAN_MOI", []))
        cu = self.q("SELECT trang_thai FROM master.hop_dong_phien_ban WHERE id = %s", (r[KV_A]["phien_ban_id"],))[0][0]
        self.assertEqual(cu, "THAY_THE")  # bản chờ cũ thay có vết, không xóa
        h = self.loan(KTA, KV_A)
        self.assertEqual((h["ngan_hang"], h["du_an"], h["so_hop_dong"]), ("NH_DEMO.A", "DA_KCN_DEMO", "HDTD-DEMO-A-01"))
        v = h["phien_ban"][-1]
        lich = {x["nghia_vu_key"]: x for x in v["lich"]}
        self.assertEqual({k: (x["so_tien"], x["amount_kind"]) for k, x in lich.items()},
                         {"DRAW/KU-A-01/1/GOC": ("12000000", "SOURCE_SCHEDULE"), "DRAW/KU-A-02/1/GOC": ("8000000", "SOURCE_SCHEDULE"),
                          "DRAW/KU-A-01/1/LAI": ("800000", "CONFIRMED_ACCOUNTING_RESULT"), "DRAW/KU-A-01/1/PHI": ("50000", "CONFIRMED_ACCOUNTING_RESULT")})
        self.assertNotEqual(lich["DRAW/KU-A-01/1/GOC"]["dich"], lich["DRAW/KU-A-02/1/GOC"]["dich"])  # S01: hai nghĩa vụ cùng kỳ phân biệt
        self.assertEqual([(x["ma"], x["pct_nam"]) for x in v["lai_suat"]], [("KU-A-01", "7.5"), ("KU-A-01", "7.2")])  # S06 giữ lịch sử mốc lãi
        self.assertEqual([(d["ma"], d["so_tien"], d["ngay"]) for d in v["khe_uoc"]], [("KU-A-01", "60000000", "2026-09-01"), ("KU-A-02", "40000000", "2026-09-15")])
        lc = self.loan(KTA, NH_A)["phien_ban"][-1]["vay"]
        self.assertEqual((lc["financing_kind"], lc["currency_code"], lc["so_vay_vnd"], lc["so_nguyen_te"], lc["nguyen_te_code"], lc["source_fx_rate"]),
                         ("LC", "VND", None, "1000000", "USD", "25000"))  # NULL ≠ 0; nguyên tệ (cent) và VND riêng; tỷ giá chỉ metadata
        truoc = self.q("SELECT count(*) FROM master.hop_dong_phien_ban")[0][0]
        r3 = self.lap(KTA, self.s["snap1"], "PN_DEMO_A")
        self.assertEqual({k: x["ket_qua"] for k, x in r3.items()}, {KV_A: "KHONG_DOI", NH_A: "KHONG_DOI"})  # replay không tạo revision giả
        self.assertEqual(self.q("SELECT count(*) FROM master.hop_dong_phien_ban")[0][0], truoc)
        self.s.update(kv_a=r2[KV_A]["hop_dong_id"], kv_a_pb2=r2[KV_A]["phien_ban_id"], nh_a=r2[NH_A]["hop_dong_id"], nh_a_pb=r2[NH_A]["phien_ban_id"])
        t = self.q("SELECT tep_goc_id FROM master.hop_dong_phien_ban WHERE id = %s", (r2[KV_A]["phien_ban_id"],))[0][0]
        self.assertEqual(self.q("SELECT loai_nguon FROM kho.tep_goc WHERE id = %s", (t,))[0][0], "M9_TACH_PN")
        self.assertEqual(self.q("SELECT count(*) FROM giao_tiep.tep_tach_phap_nhan WHERE tep_goc_id = %s", (t,))[0][0], 1)

    # ------------------------------------------------------------------ K5: kiểm/duyệt, quyền, discriminator, bất biến
    def test_m05_kiem_duyet_v3_v4_va_rao_csdl(self):
        pb = self.s["kv_a_pb2"]
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.kiem(XEM_M9, pb))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.kiem(CFO, pb))
        self.raises("PHIEN_BAN", lambda: self.vay.kiem(KTB, pb))  # RLS: KT_B không thấy PN_A
        self.raises("CHUA_KIEM_TRUOC", lambda: self.vay.duyet(CFO, pb))
        self.assertEqual(self.vay.kiem(KTA, pb)["kiem_boi"], KTA)
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.duyet(KTA, pb))
        self.raises("KHONG_CO_QUYEN_LOAI_VIEC", lambda: self.vay.duyet(CFO_V3, pb))  # HĐ mới còn V4
        self.raises("KHONG_CO_QUYEN_LOAI_VIEC", lambda: self.vay.duyet_v4(CFO_V3, self.s["kv_a"]))
        out = self.vay.duyet(CFO, pb)
        self.assertTrue(out["ho_so_vay_id"])
        ho_so = self.q("SELECT module_nghiep_vu, ngay_nghiep_vu::text, du_lieu->>'hop_dong_id' FROM kho.chung_tu WHERE id = %s", (out["ho_so_vay_id"],))[0]
        self.assertEqual(tuple(ho_so), ("M9", "2026-09-01", self.s["kv_a"]))
        self.assertEqual(self.hieu_luc(KTA, KV_A)["id"], pb)
        self.vay.kiem(KTA, self.s["nh_a_pb"])
        self.assertEqual(self.q("SELECT ngay_nghiep_vu::text FROM kho.chung_tu WHERE id = %s", (self.vay.duyet(CFO, self.s["nh_a_pb"])["ho_so_vay_id"],))[0][0],
                         "2026-09-10")  # LC: ngày mở LC
        self.s["ho_so_kv_a"] = out["ho_so_vay_id"]
        # bất biến typed: không ghi thêm vào bản đã duyệt, không sửa/xóa (kể cả chủ CSDL qua trigger)
        self.raises("M9_PHIEN_BAN_DA_CHOT", lambda: self.sql(KTA, """INSERT INTO master.lai_suat_vay (phap_nhan_id, khe_uoc_phien_ban_id, hop_dong_phien_ban_id,
                    source_row_id, ap_dung_tu, lai_suat_pct_nam, precision_status, revision_sha256, known_at_server)
                    SELECT phap_nhan_id, khe_uoc_phien_ban_id, hop_dong_phien_ban_id, source_row_id, '2027-01-01', 1, 'PROVEN', revision_sha256, now()
                    FROM master.lai_suat_vay WHERE hop_dong_phien_ban_id = %s LIMIT 1""", (pb,)))
        self.raises("permission denied", lambda: self.sql(KTA, "UPDATE master.lich_tra_no SET amount_minor = 1 WHERE phien_ban_id = %s", (pb,)))
        self.raises("M9_BAT_BIEN", lambda: self.admin.execute("UPDATE master.lich_tra_no SET amount_minor = 1 WHERE phien_ban_id = %s", (pb,)))
        self.raises("M9_BAT_BIEN", lambda: self.admin.execute("DELETE FROM master.khe_uoc_vay_phien_ban WHERE hop_dong_phien_ban_id = %s", (pb,)))
        self.raises("PHIEN_BAN_KHONG_XOA", lambda: self.admin.execute("DELETE FROM master.hop_dong_phien_ban WHERE id = %s", (pb,)))
        # R1 discriminator chủ sở hữu (DB đặt/kiểm, bất biến)
        pn = self.q("SELECT phap_nhan_id FROM master.hop_dong WHERE id = %s", (self.s["kv_a"],))[0][0]
        self.raises("CHU_SO_HUU_SAI", lambda: self.sql(KTA, """INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, du_lieu, hash, module_nghiep_vu)
                    VALUES (%s,'HO_SO_VAY','X-1','2026-10-01',%s,%s,'CRM')""", (pn, canonical_json({"hop_dong_id": self.s["kv_a"]}), "3" * 64)))
        self.raises("CHU_SO_HUU_BAT_BIEN", lambda: self.sql(KTA, "UPDATE kho.chung_tu SET module_nghiep_vu = 'M1' WHERE id = %s", (out["ho_so_vay_id"],)))
        self.raises("VIEC_CHU_THE_SAI", lambda: self.sql(KTA, """INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, module, tham_chieu_bang, tham_chieu_id)
                    VALUES (%s,'V3','CRM','master.hop_dong',%s)""", (pn, self.s["kv_a"])))
        self.raises("LO_CHU_THE_SAI", lambda: self.sql(KTA, """INSERT INTO kho.lo_xuat (phap_nhan_id, ky, ma_lo, loai, nguoi, du_lieu)
                    VALUES (%s,'2026-10','X-LO','FILE_SOAT','MO_PHONG_KT_A',%s)""", (pn, canonical_json({"module": "CRM", "hop_dong_id": self.s["kv_a"]}))))
        # domain dispatch: người chỉ có CRM không thấy HĐ VAY; CRM danh sách không có HĐ VAY; người đọc M9 không kiểm
        self.assertEqual(self.sql(XEM_CRM, "SELECT count(*) AS n FROM master.hop_dong WHERE loai = 'VAY'")[0]["n"], 0)
        self.assertIsNone(self.sql(KTA, "SELECT master.crm_phien_ban_hieu_luc(%s, current_date) AS v", (self.s["kv_a"],))[0]["v"])
        self.assertEqual([h for h in self.crm.danh_sach(KTA)["hop_dong"] if h["loai"] == "VAY"], [])
        self.assertEqual(len(self.vay.danh_sach(XEM_M9)["khoan_vay"]), 2)

    def test_m06_tien_truoc_nguon_sau_va_van_tay_cu_pn_b(self):
        """PN_B: tiền giải ngân về TRƯỚC khi có HĐ vay (gợi ý rỗng) → lập/kiểm → đổi mapping HĐ sau kiểm (digest cũ) → CFO duyệt bị chặn →
        kiểm lại → duyệt → gợi ý thấy khế ước → nối."""
        self.m1("PN_DEMO_B", KTB, [("DEMO-GN-KU-B-01", "2026-09-05", 50_000_000, "DEMO GIAI NGAN KU-B-01")], "NH_DEMO.B")
        with psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row) as a:
            m1_demo.ghi_proof_tien(a, "PN_DEMO_B")
        bank = self.bank("DEMO-GN-KU-B-01")
        self.assertEqual(self.vay.goi_y_noi(KTB, bank)["goi_y"], [])
        r = self.lap(KTB, self.s["snap1"], "PN_DEMO_B")
        self.assertEqual((set(r), r[KV_B]["chan"]), ({KV_B}, []))
        pb, hd = r[KV_B]["phien_ban_id"], r[KV_B]["hop_dong_id"]
        lich = self.loan(KTB, KV_B)["phien_ban"][-1]["lich"]
        self.assertEqual([(x["nghia_vu_key"], x["pham_vi"], x["so_tien"]) for x in lich], [("LOAN/-/1/GOC", "LOAN", "10000000")])
        self.vay.kiem(KTB, pb)
        self.assertEqual(self.sql(KTB, "UPDATE master.hop_dong SET du_an_id = NULL WHERE id = %s", (hd,)), 1)  # đổi đồ thị sau kiểm (trước duyệt)
        self.raises("KIEM_DA_HET_HIEU_LUC", lambda: self.vay.duyet(CFO, pb))
        self.assertEqual(self.q("SELECT trang_thai FROM master.hop_dong_phien_ban WHERE id = %s", (pb,))[0][0], "CHO_DUYET")
        self.vay.kiem(KTB, pb)
        self.vay.duyet(CFO, pb)
        [g] = self.vay.goi_y_noi(KTB, bank)["goi_y"]
        self.assertEqual((g["hop_dong_id"], g["tong"], g["du_dich"]), (hd, "50000000", True))
        pv = self.vay.xem_truoc_noi(KTB, bank, [{"dich": x["dich"], "so_tien": x["so_tien"]} for x in g["phan_bo"]])
        self.assertEqual(pv["chan"], [])
        ok = self.vay.xac_nhan_noi(KTB, bank, [{"dich": x["dich"], "so_tien": x["so_tien"]} for x in g["phan_bo"]], "k-b-gn", pv["xem_truoc_token"])
        self.assertEqual((ok["trang_thai"], self.con_lai(KTB, bank)["con_lai"]), ("DA_KHOP", "0"))

    # ------------------------------------------------------------------ L8: tiền đi M1 → proof → xem trước/xác nhận/gỡ, idempotency, R4
    def test_m07_noi_tien_tra_no_proof_bien_nhan_go(self):
        self.m1("PN_DEMO_A", KTA, F.SAO_KE_M9["PN_DEMO_A"]["tra_no_ky_1"], "NH_DEMO.A")
        bank = self.bank("DEMO-REF-01")
        t = self.con_lai(KTA, bank)
        self.assertEqual((t["chieu"], t["so_tien"], t["chan"], t["con_lai"]), ("CHI", "12850000", "KHONG_CO_PROOF_TIEN", None))  # unknown encoding → chặn
        [g] = self.vay.goi_y_noi(KTA, bank)["goi_y"]
        self.assertEqual(({x["cau_phan"]: x["so_tien"] for x in g["phan_bo"]}, g["khop_so_tien"], g["du_dich"]),
                         ({"GOC": "12000000", "LAI": "800000", "PHI": "50000"}, True, True))
        pb_ = [{"dich": x["dich"], "so_tien": x["so_tien"]} for x in g["phan_bo"]]
        self.assertIn("KHONG_CO_PROOF_TIEN", self.vay.xem_truoc_noi(KTA, bank, pb_)["chan"])
        with psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row) as a:
            self.assertEqual(m1_demo.ghi_proof_tien(a, "PN_DEMO_A")["proof_moi"], 1)
            self.assertEqual(m1_demo.ghi_proof_tien(a, "PN_DEMO_A")["proof_moi"], 0)  # bất biến, gọi lại không ghi thêm
        self.raises("PROOF_TIEN_BAT_BIEN", lambda: self.admin.execute("UPDATE kho.chung_tu_tien_encoding SET precision_status = 'LOST'"))
        self.raises("permission denied", lambda: self.sql(KTA, "SELECT count(*) FROM kho.chung_tu_tien_encoding"))
        self.assertEqual(self.con_lai(KTA, bank)["con_lai"], "12850000")
        self.raises("TIEN_KHONG_THAY", lambda: self.vay.xem_truoc_noi(KT_KHONG_M1, bank, pb_))  # không M1 → không thấy BANK
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.xem_truoc_noi(CFO, bank, pb_))
        gn = self.hieu_luc(KTA, KV_A)["khe_uoc"][0]["dich"]
        self.assertTrue(any(c.startswith("SAI_CHIEU_TIEN") for c in self.vay.xem_truoc_noi(KTA, bank, [{"dich": gn, "so_tien": "1"}])["chan"]))
        qua = [dict(x, so_tien="12000001") if x["so_tien"] == "12000000" else x for x in pb_]
        self.assertTrue({"VUOT_TIEN_KHA_DUNG"} <= set(self.vay.xem_truoc_noi(KTA, bank, qua)["chan"]))
        self.raises("SO_TIEN", lambda: self.vay.xem_truoc_noi(KTA, bank, [{"dich": gn, "so_tien": 1.5}]))
        pv = self.vay.xem_truoc_noi(KTA, bank, pb_)
        self.assertEqual((pv["chan"], pv["tong"]), ([], "12850000"))
        self.raises("XEM_TRUOC_HET_HIEU_LUC", lambda: self.vay.xac_nhan_noi(KTA, bank, pb_, "k1", "0" * 64))
        ok = self.vay.xac_nhan_noi(KTA, bank, pb_, "k1", pv["xem_truoc_token"])
        self.assertEqual((ok["lap_lai"], ok["tong"]), (False, "12850000"))
        lai = self.vay.xac_nhan_noi(KTA, bank, pb_, "k1", "bat-ky")
        self.assertEqual((lai["lap_lai"], lai["lien_ket_id"]), (True, ok["lien_ket_id"]))  # cùng khóa + cùng nội dung → biên nhận cũ
        self.raises("IDEMPOTENCY_KHAC", lambda: self.vay.xac_nhan_noi(KTA, bank, pb_[:1], "k1", "x"))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.xac_nhan_noi(CFO, bank, pb_, "k1", "x"))  # quyền trước replay
        self.assertEqual(self.con_lai(KTA, bank)["con_lai"], "0")
        self.assertTrue({"VUOT_TIEN_KHA_DUNG"} <= set(self.vay.xem_truoc_noi(KTA, bank, pb_)["chan"]))
        rows = self.q("SELECT allocation_model, link_purpose, so_tien_khop_minor FROM kho.lien_ket_chung_tu WHERE id = %s", (ok["lien_ket_id"],))
        self.assertEqual(tuple(rows[0]), ("CHILD", "MONEY", 12850000))
        self.assertEqual(self.q("SELECT count(*), sum(amount_minor) FROM kho.lien_ket_phan_bo WHERE lien_ket_id = %s", (ok["lien_ket_id"],))[0], (3, 12850000))
        self.raises("PHAN_BO_SAI_PARENT", lambda: self.sql(KTA, """INSERT INTO kho.lien_ket_phan_bo (phap_nhan_id, lien_ket_id, cau_phan, logical_target_id, lich_tra_no_id,
                    amount_minor, currency_code, currency_scale, basis_revision_sha256, tao_boi)
                    SELECT phap_nhan_id, lien_ket_id, cau_phan, logical_target_id, lich_tra_no_id, 1, currency_code, currency_scale, basis_revision_sha256, 'MO_PHONG_KT_A'
                    FROM kho.lien_ket_phan_bo WHERE lien_ket_id = %s LIMIT 1""", (ok["lien_ket_id"],)))
        self.raises("PHAN_BO_BAT_BIEN", lambda: self.sql(KTA, "UPDATE kho.lien_ket_phan_bo SET amount_minor = 1 WHERE lien_ket_id = %s", (ok["lien_ket_id"],)))
        go = self.vay.go_noi(KTA, ok["lien_ket_id"], "DEMO gỡ", "g1")
        self.assertEqual((go["so_child_huy"], go["lap_lai"]), (3, False))
        self.assertTrue(self.vay.go_noi(KTA, ok["lien_ket_id"], "DEMO gỡ", "g1")["lap_lai"])
        self.raises("LIEN_KET_DA_HUY", lambda: self.vay.go_noi(KTA, ok["lien_ket_id"], "DEMO gỡ", "g2"))
        self.assertEqual(self.con_lai(KTA, bank)["con_lai"], "12850000")
        self.assertEqual(self.q("SELECT count(*) FROM kho.lien_ket_phan_bo WHERE lien_ket_id = %s AND trang_thai = 'HUY' AND huy_boi = %s", (ok["lien_ket_id"], KTA))[0][0], 3)
        # R4: số tiền BANK bị sửa sau proof → chặn (digest lệch); trả lại → hết chặn
        self.admin.execute("UPDATE kho.chung_tu SET so_tien_minor = so_tien_minor + 1 WHERE id = %s", (bank,))
        self.assertEqual(self.con_lai(KTA, bank)["chan"], "PROOF_TIEN_LECH")
        self.assertIn("PROOF_TIEN_LECH", self.vay.xem_truoc_noi(KTA, bank, pb_)["chan"])
        self.admin.execute("UPDATE kho.chung_tu SET so_tien_minor = so_tien_minor - 1 WHERE id = %s", (bank,))
        pv = self.vay.xem_truoc_noi(KTA, bank, pb_)
        self.assertEqual(pv["chan"], [])
        self.s["lk_tra_no"] = self.vay.xac_nhan_noi(KTA, bank, pb_, "k3", pv["xem_truoc_token"])["lien_ket_id"]

    # ------------------------------------------------------------------ ngân sách BANK chung CRM DIRECT + M9 CHILD, race hai domain
    def test_m08_ngan_sach_chung_crm_direct_va_m9_child_race(self):
        raw, env, vb = FC.mau("kcn_goc")
        r = self.crm.nhan_ket_qua_6(BH, raw, env, van_ban_nguon=vb)
        self.crm.kiem_truoc(KTA, r["phien_ban_id"])
        self.crm.duyet(CFO, r["phien_ban_id"])
        hd = next(h for h in self.crm.danh_sach(KTA)["hop_dong"] if h["id"] == r["hop_dong_id"])
        lich, lich2 = [x["id"] for x in hd["phien_ban"][-1]["lich"] if int(x["so_tien"]) >= 10_000_000][:2]
        self.m1("PN_DEMO_A", KTA, F.SAO_KE_M9["PN_DEMO_A"]["giai_ngan_ku_a_01"], "NH_DEMO.A")
        with psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row) as a:
            m1_demo.ghi_proof_tien(a, "PN_DEMO_A")
        bank = self.bank("DEMO-GN-KU-A-01")
        gn = next(d for d in self.hieu_luc(KTA, KV_A)["khe_uoc"] if d["ma"] == "KU-A-01")["dich"]
        pv = self.vay2.xem_truoc_noi(KTA, bank, [{"dich": gn, "so_tien": "55000000"}])
        self.assertEqual(pv["chan"], [])
        crm_ = CrmK2(self.app, self.root / "k2")
        b = threading.Barrier(2)
        t1 = _Luong(lambda: crm_.lien_ket(KTA, bank, lich, "10000000", "crm-race"), b)
        t2 = _Luong(lambda: self.vay2.xac_nhan_noi(KTA, bank, [{"dich": gn, "so_tien": "55000000"}], "m9-race", pv["xem_truoc_token"]), b)
        t1.start(); t2.start(); t1.join(30); t2.join(30)
        thang = [t for t in (t1, t2) if t.loi is None]
        self.assertEqual(len(thang), 1, (t1.loi, t2.loi))  # đúng một bên thắng; bên kia bị chặn bởi ngân sách chung/xem trước cũ
        thua = t2 if thang[0] is t1 else t1
        self.assertTrue(any(c in getattr(thua.loi, "code", "") + str(thua.loi) for c in ("VUOT_TIEN_KHA_DUNG", "XEM_TRUOC_HET_HIEU_LUC")), thua.loi)
        if thang[0] is t1:  # CRM thắng: M9 xem trước lại phần còn lại 50M
            pv = self.vay.xem_truoc_noi(KTA, bank, [{"dich": gn, "so_tien": "50000000"}])
            self.vay.xac_nhan_noi(KTA, bank, [{"dich": gn, "so_tien": "50000000"}], "m9-sau-race", pv["xem_truoc_token"])
            self.raises("VUOT_TIEN_KHA_DUNG", lambda: self.crm.lien_ket(KTA, bank, lich2, "1", "crm-sau-race"))  # đợt khác, cùng BANK
        else:  # M9 thắng: CRM chỉ còn 5M
            self.raises("VUOT_TIEN_KHA_DUNG", lambda: self.crm.lien_ket(KTA, bank, lich, "10000000", "crm-sau-race"))
            self.crm.lien_ket(KTA, bank, lich, "5000000", "crm-sau-race-2")
        t = self.con_lai(KTA, bank)
        self.assertEqual((t["da_phan_bo"], t["con_lai"]), ("60000000", "0"))
        direct = self.q("SELECT coalesce(sum(so_tien_khop_minor),0) FROM kho.lien_ket_chung_tu WHERE chung_tu_a_id = %s AND allocation_model = 'DIRECT' AND trang_thai <> 'HUY'", (bank,))[0][0]
        child = self.q("""SELECT coalesce(sum(c.amount_minor),0) FROM kho.lien_ket_phan_bo c JOIN kho.lien_ket_chung_tu k ON k.id = c.lien_ket_id
                          WHERE k.chung_tu_a_id = %s AND c.trang_thai = 'HIEU_LUC' AND k.trang_thai <> 'HUY'""", (bank,))[0][0]
        self.assertEqual(direct + child, 60_000_000)
        crm_lk = self.q("SELECT id FROM kho.lien_ket_chung_tu WHERE chung_tu_a_id = %s AND allocation_model = 'DIRECT' AND trang_thai <> 'HUY' LIMIT 1", (bank,))[0][0]
        self.crm.go_lien_ket(KTA, crm_lk, "DEMO gỡ CRM")  # gỡ DIRECT → ngân sách chung trả lại cho cả M9
        self.assertEqual(self.con_lai(KTA, bank)["con_lai"], str(direct))
        self.s["gn_bank"] = bank

    # ------------------------------------------------------------------ R3: revision mới, tiêu thụ đích logic xuyên revision
    def test_m09_revision_tieu_thu_xuyen_revision(self):
        r = self.vay.nhan_mau(KTA, "native_v6_doi_so_giai_ngan")
        out = self.lap(KTA, r["snapshot_id"], "PN_DEMO_A")
        self.assertEqual((out[KV_A]["ket_qua"], out[NH_A]["ket_qua"], out[KV_A]["chan"]), ("PHIEN_BAN_MOI", "KHONG_DOI", []))
        pb3 = out[KV_A]["phien_ban_id"]
        self.vay.kiem(KTA, pb3)
        self.vay.duyet(CFO, pb3)
        v = self.hieu_luc(KTA, KV_A)
        self.assertEqual(v["id"], pb3)
        self.assertEqual(self.q("SELECT valid_to IS NOT NULL FROM master.hop_dong_phien_ban WHERE id = %s", (self.s["kv_a_pb2"],))[0][0], True)
        lich = {x["nghia_vu_key"]: x for x in v["lich"]}
        goc = lich["DRAW/KU-A-01/1/GOC"]
        self.assertEqual((goc["da_phan_bo"], goc["con_lai"]), ("12000000", "0"))  # tiêu thụ ở revision cũ vẫn trừ đích logic
        self.assertIsNotNone(goc["thay_cho"])
        self.assertEqual({d["ma"]: d["so_tien"] for d in v["khe_uoc"]}, {"KU-A-01": "60000000", "KU-A-02": "45000000"})
        self.assertNotEqual(next(d for d in v["khe_uoc"] if d["ma"] == "KU-A-01")["da_phan_bo"], "0")  # giải ngân đã nối giữ qua revision
        self.assertTrue(any(c.startswith("VUOT_NGHIA_VU") for c in self.vay.xem_truoc_noi(KTA, self.bank("DEMO-REF-01"), [{"dich": goc["dich"], "so_tien": "1"}])["chan"]))
        self.s["kv_a_pb3"] = pb3

    # ------------------------------------------------------------------ RC2 LC→SHORT cùng alias; S05 phạm vi; holding precision/xung đột/mơ hồ
    def test_m10_lc_nhan_no_cung_alias_khong_hai_hd(self):
        r = self.vay.nhan_mau(KTA, "native_v6_lc_nhan_no")
        out = self.lap(KTA, r["snapshot_id"], "PN_DEMO_A")
        self.assertEqual((out[NH_A]["ket_qua"], out[NH_A]["hop_dong_id"], out[NH_A]["financing_kind"]), ("PHIEN_BAN_MOI", self.s["nh_a"], "SHORT_TERM"))
        self.assertEqual(self.q("SELECT count(*) FROM master.vay_dinh_danh_nguon WHERE source_key = 'NH-A-01'")[0][0], 1)
        self.vay.kiem(KTA, out[NH_A]["phien_ban_id"])
        self.vay.duyet(CFO, out[NH_A]["phien_ban_id"])
        v = self.hieu_luc(KTA, NH_A)["vay"]
        self.assertEqual((v["financing_kind"], v["so_vay_vnd"], v["so_nguyen_te"], v["ngay_nhan_no"], v["so_nhan_no"]),
                         ("SHORT_TERM", "250000000", "1000000", "2026-10-01", "NN-DEMO-01"))
        self.assertEqual([v["trang_thai"] for v in self.loan(KTA, NH_A)["phien_ban"]], ["THAY_THE", "DA_DUYET", "DA_DUYET"])  # một HĐ, ba phiên bản

    def test_m11_s05_loan_draw_cho_xac_nhan_pham_vi_roi_bo_sung(self):
        r = self.vay.nhan_mau(KTA, "native_v6_loan_drawoverlap")
        out = self.lap(KTA, r["snapshot_id"], "PN_DEMO_A")
        self.assertIn("CHO_XAC_NHAN_PHAM_VI_LICH", out[KV_A]["chan"])
        self.raises("M9_CHUA_DU_DIEU_KIEN", lambda: self.vay.kiem(KTA, out[KV_A]["phien_ban_id"]))
        self.raises("PHAM_VI_LUA_CHON", lambda: self.vay.xac_nhan_pham_vi(KTA, self.s["kv_a"], "TU_DOAN", "x"))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.xac_nhan_pham_vi(CFO, self.s["kv_a"], "DUNG_DRAW", "x"))
        q = self.vay.xac_nhan_pham_vi(KTA, self.s["kv_a"], "DUNG_DRAW", "DEMO: lịch theo khế ước là nghĩa vụ")
        [kv] = [x for x in q["khoan_vay"] if x["khoa"] == KV_A]
        self.assertEqual((kv["ket_qua"], kv["chan"]), ("PHIEN_BAN_MOI", []))
        v = self.loan(KTA, KV_A)["phien_ban"][-1]
        self.assertEqual((v["nguon"]["lich_bo_qua"], v["nguon"]["quyet_dinh_pham_vi"]["boi"]), (["LOAN/-/1/GOC"], KTA))
        self.assertNotIn("LOAN/-/1/GOC", {x["nghia_vu_key"] for x in v["lich"]})
        self.vay.kiem(KTA, kv["phien_ban_id"])  # bổ sung xong → kiểm được

    def test_m12_precision_xung_dot_mo_ho_giu_cho(self):
        from kho_tri_thuc.nguon.vay_9 import PROFILE_NATIVE
        ca = {"number_mat": "PRECISION_CHUA_CHUNG_MINH", "phat_sinh_xung_dot": "TRUNG_KHOA_KHAC_NOI_DUNG:PhatSinh",
              "rate_mo_ho": "AMBIGUOUS_RATE_PARENT:LichLaiSuat"}
        for bien_the, ma in ca.items():
            r = self.vay.nhan_tep(KTA, PROFILE_NATIVE["code"], F.bytes_cua(F.native_demo(**{bien_the: True})), f"DEMO:{bien_the}")
            out = self.lap(KTA, r["snapshot_id"], "PN_DEMO_A")
            self.assertIn(ma, out[KV_A]["chan"], bien_the)
            self.raises("M9_CHUA_DU_DIEU_KIEN", lambda: self.vay.kiem(KTA, out[KV_A]["phien_ban_id"]))
        r = self.vay.nhan_tep(KTA, PROFILE_NATIVE["code"], F.bytes_cua(F.native_demo(exact_text=True)), "DEMO:exact_text")
        out = self.lap(KTA, r["snapshot_id"], "PN_DEMO_A")
        self.assertNotIn("PRECISION_CHUA_CHUNG_MINH", out[KV_A]["chan"])
        self.assertEqual(self.loan(KTA, KV_A)["phien_ban"][-1]["vay"]["du_no_nguon"], "9007199254740993")  # S09 text exact > 2^53 giữ đủ
        self.assertEqual(self.hieu_luc(KTA, KV_A)["id"], self.s["kv_a_pb3"])  # bản giữ chờ không ảnh hưởng bản hiệu lực

    # ------------------------------------------------------------------ file soát + HTTP + retarget
    def test_m13_file_soat_lossless_va_tai_ve(self):
        from kho_tri_thuc.xuat import excel
        lo = self.vay.xuat_file_soat(KTA, self.s["kv_a"])
        ten, raw = self.vay.tep_file_soat(CFO, lo["id"])
        self.assertEqual((sha256(raw), raw[:2]), (lo["sha256"], b"PK"))
        wb = excel.load(raw)
        lich = excel.rows(wb, "LICH_TRA_NO", ["phien_ban", "khoa_nghia_vu", "pham_vi", "khe_uoc", "cau_phan", "ky", "tu_ngay", "den_ngay", "den_han", "so_tien", "tien_te",
                                               "loai_so", "precision", "dich_logic", "da_phan_bo", "con_lai"])
        goc = [x for x in lich if x["khoa_nghia_vu"] == "DRAW/KU-A-01/1/GOC"]
        self.assertTrue(goc and all(x["so_tien"] == "12000000" and isinstance(x["so_tien"], str) for x in goc))
        self.assertIn("LIEN_KET_TIEN", wb.sheetnames)
        self.raises("FILE_SOAT", lambda: self.vay.tep_file_soat(KTB, lo["id"]))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.xuat_file_soat(XEM_M9, self.s["kv_a"]))
        self.assertEqual(self.q("SELECT du_lieu->>'module' FROM kho.lo_xuat WHERE id = %s", (lo["id"],))[0][0], "M9")

    def test_m14_http_cung_phien_cookie(self):
        import http.client
        import json
        from unittest.mock import patch
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        with patch.dict(os.environ, {LocalApp.CRM_ENV: self.app_dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"}):
            os.environ.pop(LocalApp.CRM_ENV_ADMIN, None)
            app = LocalApp(ROOT / "cau_hinh.toml", Path(tempfile.mkdtemp(prefix="ktt_m9_http_")) / "web")
            server = LocalServer(app, 0)
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
            thread.start()
            try:
                def call(path, body=None, cookie=None, token=True):
                    c = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=60)
                    headers = {"X-KTT-Token": app.token} if token else {}
                    if cookie:
                        headers["Cookie"] = f"{LocalApp.CRM_COOKIE}={cookie}"
                    c.request("POST" if body is not None else "GET", path, body=None if body is None else json.dumps(body), headers=headers)
                    r = c.getresponse()
                    raw, ck = r.read(), r.getheader("Set-Cookie")
                    c.close()
                    return r.status, (json.loads(raw or b"{}") if (r.getheader("Content-Type") or "").startswith("application/json") else raw), ck
                self.assertEqual(call("/api/m9", token=False)[0], 403)
                status, s1, ck = call("/api/m9")
                self.assertIsNotNone(ck, (status, s1))
                sid = ck.split(";", 1)[0].split("=", 1)[1]
                self.assertEqual((status, s1["cau_hinh"], s1["nguoi"]["dang_nhap"]), (200, True, KTA))
                self.assertEqual({h["phap_nhan"] for h in s1["khoan_vay"]}, {"PN_DEMO_A"})
                kv = next(h for h in s1["khoan_vay"] if h["khoa_nguon"] == KV_A)
                self.assertTrue(all(isinstance(x["so_tien"], str) for v in kv["phien_ban"] for x in v["lich"]))  # tiền JSON là chuỗi
                self.assertEqual(call("/api/m9/duyet", {"id": self.s["kv_a_pb3"], "actor": CFO}, sid)[1]["error"], "CRM_CLIENT_IDENTITY")
                self.assertEqual(call("/api/m9/duyet", {"id": self.s["kv_a_pb3"]})[1]["error"], "CRM_PHIEN")
                self.assertEqual(call("/api/m9/duyet", {"id": self.s["kv_a_pb3"]}, sid)[1]["error"], "KHONG_CO_QUYEN_HANH_DONG")
                self.assertEqual(call("/api/m9/m1-sao-ke", {"mau": "PN_DEMO_A:tra_no_ky_1"}, sid)[1]["error"], "CRM_M1_CHUA_CAU_HINH")
                self.assertFalse(call("/api/m9/mau", {"mau": "native_v6"}, sid)[1]["moi"])
                self.assertEqual(call("/api/m9/khong-co", {}, sid)[1]["error"], "NOT_FOUND")
                status, gy, _ = call("/api/m9/goi-y", {"tien": self.bank("DEMO-REF-01")}, sid)
                self.assertEqual(status, 200)
                self.assertEqual(call("/api/m9/danh-tinh", {"dang_nhap": CFO}, sid)[0], 200)
                status, lo, _ = call("/api/m9/file-soat", {"id": self.s["kv_a"]}, sid)
                self.assertEqual(status, 200)
                status, raw, _ = call(f"/api/m9/file-soat/{lo['id']}", cookie=sid)
                self.assertEqual((status, sha256(raw)), (200, lo["sha256"]))
                self.assertEqual({h["phap_nhan"] for h in call("/api/m9", cookie=sid)[1]["khoan_vay"]}, {"PN_DEMO_A", "PN_DEMO_B"})
                s2 = call("/api/m9", cookie=sid)[1]
                self.assertTrue(s2["khoang_trong"] and any(g["ma"] == "C4D_DAU_TU" for g in s2["khoang_trong"]))
                self.assertEqual(call("/api/crm/danh-tinh", {"dang_nhap": XEM_CRM}, sid)[0], 200)
                s3 = call("/api/m9", cookie=sid)[1]
                self.assertEqual((s3["khoan_vay"], bool(s3.get("khong_quyen"))), ([], True))
            finally:
                server.shutdown(); server.server_close(); thread.join(3)

    def test_m15_retarget_cong_ty_co_impact_va_chan_alias(self):
        im = self.vay.anh_huong_anh_xa(CFO, self.s["map_b"])
        self.assertEqual((im["so_hop_dong"], im["so_phien_ban_da_duyet"], im["so_lien_ket_tien_hieu_luc"]), (1, 1, 1))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.vay.dong_anh_xa(KTB, self.s["map_b"], "x"))
        self.raises("CAN_LY_DO", lambda: self.vay.dong_anh_xa(CFO, self.s["map_b"], ""))
        self.vay.dong_anh_xa(CFO, self.s["map_b"], "DEMO: công ty nguồn B chuyển sang PN_A")
        self.raises("ANH_XA_BAT_BIEN", lambda: self.sql(CFO, "UPDATE master.anh_xa_nguon SET state = 'DA_DUYET', valid_to = NULL WHERE id = %s", (self.s["map_b"],)))
        m = self.vay.xac_nhan_anh_xa(CFO, "COMPANY", "CT_DEMO_B", "PN_DEMO_A", ly_do="DEMO retarget")
        self.assertEqual(m["revision"], 2)
        v = F.native_demo()
        v["exportedAt"] = "2026-10-18T08:00:00+07:00"
        from kho_tri_thuc.nguon.vay_9 import PROFILE_NATIVE
        r = self.vay.nhan_tep(KTA, PROFILE_NATIVE["code"], F.bytes_cua(v), "DEMO:retarget")
        out = self.lap(KTA, r["snapshot_id"], "PN_DEMO_A")
        self.assertEqual(out[KV_B]["ket_qua"], "CHAN_ALIAS_PHAP_NHAN_KHAC")  # khóa nguồn đã có HĐ ở PN_B — không tự chuyển
        self.assertEqual(self.q("SELECT count(*) FROM master.vay_dinh_danh_nguon WHERE source_key = 'KV-B-01'")[0][0], 1)
        self.assertEqual(self.q("SELECT p.ma FROM master.vay_dinh_danh_nguon a JOIN master.phap_nhan p ON p.id = a.phap_nhan_id WHERE source_key = 'KV-B-01'")[0][0], "PN_DEMO_B")

    def test_m16_nhat_ky_va_tong_hop(self):
        with self.assertRaises(psycopg.Error):
            self.sql(KTA, "UPDATE nhat_ky.su_kien SET ly_do = 'x'")
        dem = {r[0]: r[1] for r in self.q("SELECT hanh_dong, count(*) FROM nhat_ky.su_kien WHERE left(hanh_dong, 3) = 'M9_' GROUP BY 1")}
        self.assertTrue({"M9_NHAN_ANH_CHUP", "M9_DUYET_ANH_XA", "M9_LAP_PHIEN_BAN", "M9_KIEM", "M9_DUYET_V3", "M9_NOI_TIEN", "M9_GO_NOI_TIEN"} <= set(dem), dem)
        bang = ("kho.anh_chup_nguon", "kho.ban_ghi_nguon", "master.anh_xa_nguon", "master.vay_dinh_danh_nguon", "master.vay_phien_ban", "master.khe_uoc_vay_phien_ban",
                "master.lai_suat_vay", "master.lich_tra_no", "kho.su_kien_vay", "kho.dich_phan_bo_tien", "kho.lien_ket_phan_bo", "kho.bien_nhan_thao_tac",
                "kho.chung_tu_tien_encoding", "kho.lo_xuat")
        print("\nM9_K2_AGGREGATE", canonical_json({"db": self.db, "role": self.role, "schema": PG_SCHEMA_VERSION,
                                                    "counts": {t: self.q(f"SELECT count(*) FROM {t}")[0][0] for t in bang}, "su_kien": dem}))


if __name__ == "__main__":
    unittest.main()
