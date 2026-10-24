"""CRM-01 trên PostgreSQL thật (K2 typed), sửa theo review 02.

- Nâng cấp: DB schema 9 có dữ liệu (kể cả link HUY lịch sử không vết) → 11; DB đã nhận M0010 bản bàn giao đầu → 11 qua hash tương thích
  có audit (không sửa schema_migrations); migration bị sửa khác → MIGRATION_CHANGED.
- Ranh giới CSDL bằng vai trò ứng dụng app_web thật (không superuser): danh tính phiên ID + login fail-closed, RLS pháp nhân + module,
  bất biến phiên bản/tham số/lịch đã duyệt, chặn chèn bản đã duyệt, FK cùng pháp nhân/cùng hợp đồng, V3/V4 tách quyền, vân tay kiểm.
- Luồng: #6 → chờ → KT kiểm → CFO MO_PHONG duyệt → lịch → phụ lục (quá khứ/tương lai theo đồng hồ nghiệp vụ) → tiền về qua M1 thật
  (Store.ingest + engine đề xuất + bộ chiếu) → nối đợt (một phần/nhiều lần/lặp/gỡ), race nghĩa vụ–tiền hai thứ tự, retry đồng thời,
  bổ sung hồ sơ, trích lại, xác nhận tham số, file soát CRM + tải về, HTTP danh tính theo phiên.
Dữ liệu DEMO, actor MO_PHONG_. Chạy khi có KHO_PG_DSN_TEST (helper điều phối). Không DROP database/role: giữ làm bằng chứng."""

from __future__ import annotations

import os
import secrets
import tempfile
import threading
import time
import unittest
import uuid
from datetime import date
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang import postgres as pg
from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.pg_migrations import M0010, M0010_V1_BAN_GIAO_DAU, PG_MIGRATIONS, PG_SCHEMA_VERSION
from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json, sha256
from kho_tri_thuc.k2 import crm_demo, m1_demo
from kho_tri_thuc.k2.crm import CrmK2
from kho_tri_thuc.kiem_chung import fixtures_crm as F

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
ROOT = Path(__file__).resolve().parents[1]
BH, KTA, KTB, CFO, XEM = "MO_PHONG_BAN_HANG", "MO_PHONG_KT_A", "MO_PHONG_KT_B", "MO_PHONG_CFO", "MO_PHONG_XEM_A"
CFO_V3, KT_M1 = "MO_PHONG_CFO_CHI_V3", "MO_PHONG_KT_KHONG_CRM_A"
H = lambda statements: sha256("\n".join(statements).encode())  # noqa: E731


def kcn_khac(n, **sua):
    """Hợp đồng KCN DEMO khác số (cùng profile), văn bản đối chiếu có mục Điều/Khoản."""
    fx = F.kcn_goc()
    next(p for p in fx["tham_so"] if p["ma"] == "TC-01").update(gia_tri=f"HD-KCN-DEMO/{n}", trich_dan=f"Hợp đồng số HD-KCN-DEMO/{n}")
    vb = [dict(m, noi_dung=m["noi_dung"].replace("HD-KCN-DEMO/01", f"HD-KCN-DEMO/{n}")) for m in F.VB_KCN]
    for ma, (gia_tri, trich, cu, moi) in sua.items():
        next(p for p in fx["tham_so"] if p["ma"] == ma).update(gia_tri=gia_tri, trich_dan=trich)
        vb = [dict(m, noi_dung=m["noi_dung"].replace(cu, moi)) for m in vb]
    env = F.env("PN_DEMO_A", "DT-KCN-THUE-DAT-DEMO", "GOC", f"HD_KCN_{n}", ma_hop_dong_chung=f"HDC-KCN-DEMO-{n}",
                doi_tac_object_id="KH_DEMO.A01", du_an="DA_KCN_DEMO")
    return fx, env, vb


def kcn_pl(n, so, ngay, ma, gia_tri, trich):
    fx = F.ket_qua(f"{so}.docx", [F._p("PL-01", "Số phụ lục", so, f"PHỤ LỤC DEMO số {so}"),
                                  F._p("PL-02", "Ngày hiệu lực", ngay, f"có hiệu lực từ ngày {ngay}"), F._p(ma, ma, gia_tri, trich)])
    vb = f"PHỤ LỤC DEMO số {so} có hiệu lực từ ngày {ngay}. {trich}."
    return fx, F.env("PN_DEMO_A", "DT-KCN-THUE-DAT-DEMO", "PHU_LUC", "PL_" + so, hop_dong_goc=f"HDC-KCN-DEMO-{n}"), vb


class _Luong(threading.Thread):
    def __init__(self, fn, barrier=None):
        super().__init__(daemon=True)
        self.fn, self.barrier, self.ket_qua, self.loi = fn, barrier, None, None

    def run(self):
        try:
            if self.barrier:
                self.barrier.wait(10)
            self.ket_qua = self.fn()
        except Exception as exc:  # noqa: BLE001 — trả lỗi về luồng test
            self.loi = exc


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — không chạy được test PostgreSQL CRM (không tính đạt)")
class CrmK2Test(unittest.TestCase):
    ngay = date(2026, 10, 19)  # đồng hồ nghiệp vụ của test (không phụ thuộc ngày máy)

    @classmethod
    def _db(cls, prefix):
        name = prefix + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{name}" ENCODING \'UTF8\' TEMPLATE template0')
        return name, ADMIN_DSN.rsplit("/", 1)[0] + "/" + name

    @classmethod
    def setUpClass(cls):
        cls.db, cls.dsn = cls._db("kho_test_crm_")
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        # --- DB "đã có dữ liệu" ở schema 9 (trước CRM-01), có link HUY lịch sử không có người/thời điểm hủy, rồi nâng cấp
        pg.migrate(cls.admin, target=9)
        a = cls.admin
        cls.legacy_pn = a.execute("INSERT INTO master.phap_nhan (ma, ten) VALUES ('LEGACY_DEMO','Pháp nhân DEMO cũ') RETURNING id").fetchone()[0]
        hd = a.execute("INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong) VALUES (%s,'THUE_DAT','LEG-1','LEG/01') RETURNING id", (cls.legacy_pn,)).fetchone()[0]
        pb = a.execute("INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon) VALUES (%s,1,'TAY') RETURNING id", (hd,)).fetchone()[0]
        a.execute("INSERT INTO master.lich_thu (phien_ban_id, dot, so_tien_minor) VALUES (%s,1,1000)", (pb,))
        c1, c2 = (a.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash) VALUES (%s,'SAO_KE',%s,'2026-08-01',%s) RETURNING id""",
                            (cls.legacy_pn, k, "0" * 64)).fetchone()[0] for k in ("LEG-SK-1", "LEG-SK-2"))
        a.execute("INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai) VALUES (%s,%s,%s,'NHIEU_LAN_CHUYEN')", (cls.legacy_pn, c1, c2))
        cls.legacy_huy = a.execute("""INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai, trang_thai)
                                      VALUES (%s,%s,%s,'NHIEU_LAN_CHUYEN','HUY') RETURNING id""", (cls.legacy_pn, c2, c1)).fetchone()[0]
        cls.truoc_nang_cap = cls.counts()
        cls.version_sau = pg.migrate(cls.admin)
        cls.version_lan_2 = pg.migrate(cls.admin)
        cls.ids = crm_demo.khoi_tao(cls.admin)
        crm_demo.khoi_tao(cls.admin)  # seed idempotent
        # --- vai trò ứng dụng thật (đăng nhập, thành viên app_web, không superuser); giữ lại, không DROP
        cls.role, pw = "ktt_test_web_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.app = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row)
        cls.app2 = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row)
        cls.root = Path(tempfile.mkdtemp(prefix="ktt_crm_k2_"))
        clock = lambda: CrmK2Test.ngay  # noqa: E731
        cls.crm = CrmK2(cls.app, cls.root, hom_nay=clock)
        cls.crm2 = CrmK2(cls.app2, cls.root, hom_nay=clock)
        cls.cfg = Config.load(ROOT / "cau_hinh.toml", cls.root / "mo-phong")
        cls.state = {}

    @classmethod
    def tearDownClass(cls):
        for c in (cls.app, cls.app2, cls.admin):
            c.close()  # giữ DB/role/thư mục làm bằng chứng (chế độ không xóa)

    @classmethod
    def counts(cls):
        q = lambda sql: cls.admin.execute(sql).fetchone()[0]  # noqa: E731
        return {t: q(f"SELECT count(*) FROM {t}") for t in ("master.hop_dong", "master.hop_dong_phien_ban", "master.hop_dong_tham_so", "master.lich_thu",
                                                             "kho.tep_goc", "kho.chung_tu", "kho.de_xuat", "kho.de_xuat_dong", "kho.lien_ket_chung_tu",
                                                             "kho.viec_can_duyet", "kho.lo_xuat", "nhat_ky.su_kien")}

    def nhan(self, ten, actor=BH, **sua):
        raw, env, vb = F.mau(ten)
        env.update(sua)
        return self.crm.nhan_ket_qua_6(actor, raw, env, van_ban_nguon=vb)

    def nhan_fx(self, fx, env, vb, actor=BH):
        return self.crm.nhan_ket_qua_6(actor, canonical_json(fx).encode(), env, van_ban_nguon=vb)

    def hd(self, actor, ma):
        return next(h for h in self.crm.danh_sach(actor)["hop_dong"] if h["ma_noi_bo"] == ma)

    def lich(self, ma, idx=-1, actor=KTA):
        return {l["khoa"]: l for l in self.hd(actor, ma)["phien_ban"][idx]["lich"]}

    def tien(self, actor, ma):
        pn = "PN_DEMO_A" if ma.startswith("DEMO-A") else "PN_DEMO_B"
        _, ngay, so, _ = next(g for dot in F.SAO_KE_M1[pn].values() for g in dot if g[0] == ma)
        [t] = [t for t in self.crm.danh_sach(actor)["tien"] if (t["ngay"], t["so_tien"]) == (ngay, str(so))]
        return t["id"]

    def m1(self, pn, dot):
        actor, doi_tac = (KTA, "KH_DEMO.A01") if pn == "PN_DEMO_A" else (KTB, "KH_DEMO.B01")
        facts = self.crm.fact_hop_dong_m1(actor, pn)  # fact HĐ/lịch hiệu lực từ K2 theo quyền người thao tác → context engine M1
        r = m1_demo.nhan_sao_ke(self.cfg, self.root, pn, F.SAO_KE_M1[pn][dot], actor, doi_tac, hop_dong=facts)
        self.state.setdefault("sqlite", {})[pn] = r["sqlite"]
        c = m1_demo.chieu_sang_k2(r["sqlite"], self.dsn)
        self.assertEqual((c["ok"], c["da_ghi"], c.get("lech_dem"), c.get("lech_noi_dung")), (True, True, [], []), c)
        self.assertTrue(all(x["bang"] in m1_demo.DUNG_CHUNG_MODULE_KHAC and x["dich"] > x["nguon"] for x in c["lech_dung_chung"]), c)
        self.assertTrue(all(v["thieu"] == 0 for v in c["dung_chung_tung_ban_ghi"].values()), c)  # mọi bản ghi nguồn có ở đích
        self.state.setdefault("chieu", []).append({"pn": pn, "dot": dot, **{k: c[k] for k in ("ma_thoat", "lech_dung_chung", "bank_sao_ke", "quick_de_xuat")}})
        return r

    def raises(self, code, fn):
        with self.assertRaises((DataError, psycopg.Error)) as ctx:
            fn()
        self.assertIn(code, getattr(ctx.exception, "code", "") + str(ctx.exception))

    def sql(self, login, sql, params=(), *, id_login=None, chi_id=False, chi_login=False):
        """Chạy SQL thẳng bằng vai trò app_web với danh tính phiên đặt tay (mô phỏng client bỏ qua service)."""
        nd = self.admin.execute("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s", (id_login or login,)).fetchone()[0]
        with self.app.transaction():
            self.app.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)",
                             ("" if chi_login else nd, "" if chi_id else login))
            cur = self.app.execute(sql, params)
            return cur.fetchall() if cur.description else cur.rowcount

    def sql_loi(self, code, login, sql, params=()):
        self.raises(code, lambda: self.sql(login, sql, params))

    def cho_khoa(self):
        for _ in range(400):
            if self.admin.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = %s AND wait_event_type = 'Lock'", (self.db,)).fetchone()[0]:
                return True
            time.sleep(0.05)
        return False

    # ------------------------------------------------------------------ nâng cấp
    def test_t01_nang_cap_v9_giu_du_lieu_va_link_huy_lich_su(self):
        self.assertEqual((self.version_sau, self.version_lan_2, PG_SCHEMA_VERSION), (13, 13, 13))  # M0013 = M9/common (sau CRM 12)
        after = self.counts()
        for t in ("kho.chung_tu", "kho.lien_ket_chung_tu", "master.lich_thu"):
            self.assertGreaterEqual(after[t], self.truoc_nang_cap[t])
        row = self.admin.execute("SELECT phap_nhan_id, khoa_nghia_vu FROM master.lich_thu WHERE so_tien_minor = 1000").fetchone()
        self.assertEqual((row[0], row[1]), (self.legacy_pn, "DOT-1"))
        self.assertEqual(self.admin.execute("SELECT count(*) FROM master.schema_migrations").fetchone()[0], PG_SCHEMA_VERSION)
        self.assertEqual([r[0] for r in self.admin.execute("SELECT checksum FROM master.schema_migrations ORDER BY version")], [H(m) for m in PG_MIGRATIONS])
        huy = self.admin.execute("SELECT trang_thai, huy_khong_vet_truoc_v10, huy_boi, huy_luc, ly_do_huy FROM kho.lien_ket_chung_tu WHERE id = %s",
                                 (self.legacy_huy,)).fetchone()
        self.assertEqual(tuple(huy), ("HUY", True, None, None, None))  # giữ nguyên, đánh dấu lịch sử, không bịa người/thời điểm hủy
        self.raises("LIEN_KET_KHONG_SUA", lambda: self.admin.execute("UPDATE kho.lien_ket_chung_tu SET huy_khong_vet_truoc_v10 = false WHERE id = %s", (self.legacy_huy,)))
        self.raises("LIEN_KET_MOI_KHONG_HOP_LE", lambda: self.admin.execute(
            """INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai, trang_thai, huy_khong_vet_truoc_v10)
               SELECT phap_nhan_id, chung_tu_a_id, chung_tu_b_id, 'KHAC', 'HUY', true FROM kho.lien_ket_chung_tu WHERE id = %s""", (self.legacy_huy,)))
        self.assertEqual(self.admin.execute("SELECT to_regclass('master.migration_tuong_thich')").fetchone()[0], None)  # DB đi v9→11 không cần tương thích

    def test_t01b_nang_cap_db_da_nhan_m0010_ban_dau_qua_hash_tuong_thich(self):
        db, dsn = self._db("kho_test_crm_v10_")
        with psycopg.connect(dsn, autocommit=True) as c:
            self.assertEqual(pg.migrate(c, migrations=PG_MIGRATIONS[:9] + (M0010_V1_BAN_GIAO_DAU,)), 10)
            truoc = [tuple(r) for r in c.execute("SELECT version, checksum, applied_at FROM master.schema_migrations ORDER BY version")]
            self.assertEqual(truoc[-1][1], H(M0010_V1_BAN_GIAO_DAU))
            self.assertEqual(pg.migrate(c), PG_SCHEMA_VERSION)
            self.assertEqual(pg.migrate(c), PG_SCHEMA_VERSION)
            sau = [tuple(r) for r in c.execute("SELECT version, checksum, applied_at FROM master.schema_migrations ORDER BY version")]
            self.assertEqual(sau[:10], truoc)  # không sửa dòng đã ghi
            self.assertEqual([r[:2] for r in sau[10:]], [(i + 1, H(PG_MIGRATIONS[i])) for i in range(10, PG_SCHEMA_VERSION)])
            tt = [tuple(r[:3]) for r in c.execute("SELECT version, checksum_da_ghi, checksum_hien_tai, ghi_chu FROM master.migration_tuong_thich")]
            self.assertEqual(tt, [(10, H(M0010_V1_BAN_GIAO_DAU), H(M0010))])
            self.assertEqual(c.execute("SELECT count(*) FROM pg_constraint WHERE conname = 'lien_ket_huy_co_vet'").fetchone()[0], 1)
            self.state["compat"] = {"db": db, "m0010_ban_dau": H(M0010_V1_BAN_GIAO_DAU), "m0010_hien_hanh": H(M0010), "m0011": H(PG_MIGRATIONS[10]),
                                    "m0012": H(PG_MIGRATIONS[11])}
        db2, dsn2 = self._db("kho_test_crm_sai_")
        with psycopg.connect(dsn2, autocommit=True) as c:
            pg.migrate(c, migrations=PG_MIGRATIONS[:9] + (M0010_V1_BAN_GIAO_DAU + ("SELECT 1",),))
            self.raises("MIGRATION_CHANGED", lambda: pg.migrate(c))  # chỉ hash liệt kê chính xác mới được chấp nhận

    def test_t01c_db_dung_schema11_co_lich_su_da_duyet_len_12(self):
        """DB dừng ở M0011 (như DB DEMO giữ lại) có bản đã duyệt + lịch → M0012: dữ liệu/lịch sử checksum giữ nguyên, bảo vệ mới áp lên dòng cũ."""
        db, dsn = self._db("kho_test_crm_v11_")
        with psycopg.connect(dsn, autocommit=True) as c:
            self.assertEqual(pg.migrate(c, target=11), 11)
            pn = c.execute("INSERT INTO master.phap_nhan (ma, ten) VALUES ('PN_V11_DEMO','Pháp nhân DEMO v11') RETURNING id").fetchone()[0]
            ids = {}
            for login, vai, duyet in (("MO_PHONG_KT_V11", "KE_TOAN", []), ("MO_PHONG_CFO_V11", "CFO", ["V3"])):
                ids[login] = str(c.execute("INSERT INTO master.nguoi_dung (ten, dang_nhap, vai_tro, mo_phong) VALUES (%s,%s,%s,true) RETURNING id",
                                           (login, login, vai)).fetchone()[0])
                c.execute("INSERT INTO master.phan_quyen (nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module) VALUES (%s,%s,%s,%s)", (ids[login], pn, duyet, ["CRM"]))
            hd = c.execute("INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong) VALUES (%s,'THUE_DAT','V11-1','V11/1') RETURNING id", (pn,)).fetchone()[0]
            pb = c.execute("INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon) VALUES (%s,1,'TAY') RETURNING id", (hd,)).fetchone()[0]
            c.execute("INSERT INTO master.hop_dong_tham_so (phien_ban_id, ten, gia_tri, nguon) VALUES (%s,'X',NULL,'TAY')", (pb,))

            def phien(login):
                c.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (ids[login], login))
            with c.transaction():
                phien("MO_PHONG_KT_V11")
                c.execute("UPDATE master.hop_dong_phien_ban SET kiem_boi = %s, kiem_luc = now(), kiem_van_tay = master.van_tay_phien_ban(id) WHERE id = %s", ("MO_PHONG_KT_V11", pb))
            with c.transaction():
                phien("MO_PHONG_CFO_V11")
                c.execute("""UPDATE master.hop_dong_phien_ban SET trang_thai = 'DA_DUYET', nguoi_duyet = %s, duyet_luc = now(), valid_from = '2026-09-01T00:00:00+00'
                             WHERE id = %s""", ("MO_PHONG_CFO_V11", pb))
                c.execute("INSERT INTO master.lich_thu (phien_ban_id, phap_nhan_id, dot, so_tien_minor, khoa_nghia_vu) VALUES (%s,%s,1,1000,'DOT-1')", (pb, pn))
                c.execute("UPDATE master.hop_dong SET phien_ban_hien_hanh = %s WHERE id = %s", (pb, hd))
            snap = lambda: [[tuple(r) for r in c.execute(f"SELECT t::text FROM {t} t ORDER BY 1")] for t in  # noqa: E731
                            ("master.hop_dong", "master.hop_dong_phien_ban", "master.hop_dong_tham_so", "master.lich_thu")]
            truoc, hist = snap(), [tuple(r) for r in c.execute("SELECT version, checksum, applied_at FROM master.schema_migrations ORDER BY version")]
            self.assertEqual(len(truoc[1]), 1)
            self.assertEqual(pg.migrate(c), PG_SCHEMA_VERSION)
            self.assertEqual(snap(), truoc)  # dữ liệu/approved history không đổi
            sau = [tuple(r) for r in c.execute("SELECT version, checksum, applied_at FROM master.schema_migrations ORDER BY version")]
            self.assertEqual((sau[:11], [r[:2] for r in sau[11:]]), (hist, [(i + 1, H(PG_MIGRATIONS[i])) for i in range(11, PG_SCHEMA_VERSION)]))
            with self.assertRaises(psycopg.Error) as ctx:  # bảo vệ biên hiệu lực áp lên bản đã duyệt có từ trước M0012
                with c.transaction():
                    phien("MO_PHONG_CFO_V11")
                    c.execute("UPDATE master.hop_dong_phien_ban SET valid_to = '2026-12-01T00:00:00+00' WHERE id = %s", (pb,))
            self.assertIn("HIEU_LUC_KHONG_HOP_LE", str(ctx.exception))
            self.assertEqual(snap(), truoc)
            self.assertEqual(c.execute("SELECT has_function_privilege('app_web', 'master.da_lien_ket(uuid, text)', 'EXECUTE')").fetchone()[0], False)

    # ------------------------------------------------------------------ nhận #6, quyền đọc
    def test_t02_vai_tro_ung_dung_that_va_khong_danh_tinh(self):
        self.assertFalse(self.app.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()["rolsuper"])
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.app.execute("SELECT count(*) FROM bao_mat.mask_bi_danh")
        self.assertEqual(self.app.execute("SELECT count(*) AS n FROM kho.chung_tu").fetchone()["n"], 0)  # chưa có danh tính phiên → không thấy dòng nào
        with self.assertRaises(psycopg.Error):
            self.app.execute("DELETE FROM kho.chung_tu")

    def test_t03_nhan_6_hai_phap_nhan_va_nhan_lai_khong_trung(self):
        r = self.nhan("kcn_goc")
        self.assertEqual((r["ket_qua"], r["chan"]), ("HOP_DONG_CHO_DUYET", []))
        before = self.counts()
        again = self.nhan("kcn_goc")
        self.assertEqual((again["trung"], again["ket_qua"]), (True, "TRUNG_RAW"))
        self.assertEqual(self.counts(), before)  # cùng raw → 0 hợp đồng/phiên bản/tham số/việc/sự kiện mới
        self.assertEqual(self.nhan("nha_goc")["ket_qua"], "HOP_DONG_CHO_DUYET")
        kcn = self.hd(KTA, "HDC-KCN-DEMO-01")
        self.assertEqual((kcn["phap_nhan"], kcn["doi_tac_object_id"], kcn["gia_tri"], kcn["trang_thai"], kcn["v4"]),
                         ("PN_DEMO_A", "KH_DEMO.A01", "3000000000", "CHO_DUYET", "CHO_DUYET"))
        [v1] = kcn["phien_ban"]
        self.assertEqual((v1["trang_thai"], v1["nguon"], len(v1["lich"]), v1["profile"]["phien_ban"]), ("CHO_DUYET", "BAN_HANG", 0, 2))
        can_cu = {p["ma"]: p["can_cu"] for p in v1["tham_so"]}
        self.assertEqual(can_cu.pop("LT-D3-TYLE"), "KHONG_QUY_DINH")  # dòng optional rỗng của nguồn
        self.assertEqual(set(can_cu.values()), {"CO_CAN_CU"})
        tt02 = next(p for p in v1["tham_so"] if p["ma"] == "TT-02")
        self.assertEqual((tt02["typed"]["don_vi_nguon"], tt02["typed"]["alias_profile"]), ("đồng", "DT-KCN-THUE-DAT-DEMO@v2"))
        self.state["kcn_v1"], self.state["nha_v1"] = v1["id"], self.hd(KTB, "HDC-NHA-DEMO-07")["phien_ban"][0]["id"]

    def test_t04_quyen_doc_phap_nhan_module_va_danh_tinh_fail_closed(self):
        self.assertEqual({h["phap_nhan"] for h in self.crm.danh_sach(KTA)["hop_dong"]}, {"PN_DEMO_A"})
        self.assertEqual({h["phap_nhan"] for h in self.crm.danh_sach(KTB)["hop_dong"]}, {"PN_DEMO_B"})
        self.assertEqual({h["phap_nhan"] for h in self.crm.danh_sach(CFO)["hop_dong"]}, {"PN_DEMO_A", "PN_DEMO_B"})
        self.raises("PHIEN_BAN", lambda: self.crm.kiem_truoc(KTA, self.state["nha_v1"]))  # RLS: KT_A không thấy pháp nhân B
        self.raises("KHONG_CO_QUYEN_PHAP_NHAN", lambda: self.nhan("nha_goc", actor=KTA, ma_hop_dong_chung="X"))
        # module: KT có pháp nhân A nhưng không có module CRM → service và CSDL đều không cho đọc CRM
        self.raises("KHONG_CO_QUYEN_MODULE", lambda: self.crm.danh_sach(KT_M1))
        for table in ("master.hop_dong", "master.hop_dong_phien_ban", "master.hop_dong_tham_so", "master.loai_hinh_doanh_thu"):
            self.assertEqual(self.sql(KT_M1, f"SELECT count(*) AS n FROM {table}")[0]["n"], 0, table)
        self.assertEqual(self.sql(KT_M1, "SELECT count(*) AS n FROM kho.chung_tu WHERE loai = 'HOP_DONG_TEP'")[0]["n"], 0)
        self.assertGreater(self.sql(KTA, "SELECT count(*) AS n FROM master.hop_dong")[0]["n"], 0)
        xem = self.crm.danh_sach(XEM)
        self.assertEqual(({h["phap_nhan"] for h in xem["hop_dong"]}, xem["tien"], xem["nguoi"]["xem_tien"]), ({"PN_DEMO_A"}, [], False))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.crm.kiem_truoc(XEM, self.state["kcn_v1"]))
        # danh tính phiên: thiếu login, thiếu ID, hoặc ID và login của hai người khác nhau → không thấy gì (fail-closed)
        q = "SELECT count(*) AS n FROM master.hop_dong"
        self.assertEqual(self.sql(KTA, q, chi_id=True)[0]["n"], 0)
        self.assertEqual(self.sql(KTA, q, chi_login=True)[0]["n"], 0)
        self.assertEqual(self.sql(CFO, q, id_login=KTA)[0]["n"], 0)
        with self.app.transaction():  # ghi thẳng bằng vai trò app_web vào pháp nhân ngoài quyền → RLS WITH CHECK chặn
            nd = self.admin.execute("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s", (KTA,)).fetchone()[0]
            self.app.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (nd, KTA))
            with self.assertRaises(psycopg.Error):
                with self.app.transaction():
                    self.app.execute("INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, hash) VALUES (%s,'KHAC','X','2026-10-01',%s)",
                                     (self.ids["PN_DEMO_B"], "0" * 64))

    def test_t05_duyet_dung_vai_tro_v3_v4_va_lich_dung_expected(self):
        v1 = self.state["kcn_v1"]
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.crm.kiem_truoc(BH, v1))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.crm.duyet(KTA, v1))
        self.raises("CHUA_KIEM_TRUOC", lambda: self.crm.duyet(CFO, v1))
        self.admin.execute("INSERT INTO master.nguoi_dung (ten, dang_nhap, vai_tro) VALUES ('Người thật DEMO','NGUOI_THAT_DEMO','CFO') ON CONFLICT DO NOTHING")
        self.raises("DANH_TINH_MO_PHONG", lambda: self.crm.duyet("NGUOI_THAT_DEMO", v1))
        self.crm.kiem_truoc(KTA, v1)
        self.sql_loi("KHONG_CO_QUYEN_DUYET", KTA, "UPDATE master.hop_dong_phien_ban SET trang_thai = 'DA_DUYET', nguoi_duyet = %s, duyet_luc = now() WHERE id = %s", (KTA, v1))
        self.sql_loi("KHONG_CO_QUYEN_DUYET", KTA, "UPDATE master.hop_dong_phien_ban SET trang_thai = 'DA_DUYET', nguoi_duyet = %s, duyet_luc = now() WHERE id = %s", (CFO, v1))
        # CFO chỉ có V3: không được hoàn tất hợp đồng mới còn việc V4 (service và trigger việc)
        before = self.counts()
        self.raises("KHONG_CO_QUYEN_LOAI_VIEC", lambda: self.crm.duyet(CFO_V3, v1))
        self.raises("KHONG_CO_QUYEN_LOAI_VIEC", lambda: self.crm.duyet_v4(CFO_V3, self.hd(KTA, "HDC-KCN-DEMO-01")["id"]))
        self.sql_loi("KHONG_CO_QUYEN_LOAI_VIEC", CFO_V3, """UPDATE kho.viec_can_duyet SET trang_thai = 'DA_DUYET', duyet_boi = %s
                                                           WHERE loai = 'V4' AND tham_chieu_bang = 'master.hop_dong' AND trang_thai = 'CHO_DUYET'""", (CFO_V3,))
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.crm.duyet(CFO, v1)["so_dot"], 3)  # CFO đủ V3+V4: hoàn tất V4 cùng giao dịch
        after = self.counts()
        for t in ("kho.de_xuat", "kho.de_xuat_dong", "kho.lo_xuat", "kho.chung_tu"):
            self.assertEqual(after[t], before[t])  # duyệt/sinh lịch không tạo bút toán, đề xuất, lô hay chứng từ
        kcn = self.hd(KTA, "HDC-KCN-DEMO-01")
        self.assertEqual((kcn["v4"], kcn["hieu_luc_hom_nay"]), ("DA_DUYET", v1))
        self.assertEqual([(l["khoa"], l["so_tien"], l["han"], l["moc"]) for l in kcn["phien_ban"][0]["lich"]],
                         [("COC-1", "300000000", "2026-09-15", None), ("DOT-1", "1200000000", "2026-10-15", None), ("DOT-2", "1500000000", None, "BAN_GIAO_DAT")])
        nha = self.hd(KTB, "HDC-NHA-DEMO-07")
        self.crm.kiem_truoc(KTB, self.state["nha_v1"])
        self.raises("KHONG_CO_QUYEN_LOAI_VIEC", lambda: self.crm.duyet(CFO_V3, self.state["nha_v1"]))
        self.assertEqual(self.crm.duyet_v4(CFO, nha["id"]), {"v4": "DA_DUYET"})
        self.assertEqual(self.crm.duyet(CFO_V3, self.state["nha_v1"])["so_dot"], 3)  # V4 đã có người đủ quyền hoàn tất → V3 duyệt tham số

    def test_t06_bat_bien_va_fk_cung_phap_nhan_o_csdl(self):
        v1 = self.state["kcn_v1"]
        hd = self.hd(KTA, "HDC-KCN-DEMO-01")
        self.sql_loi("PHIEN_BAN_MOI_PHAI_CHO_DUYET", CFO, """INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon, trang_thai, nguoi_duyet, duyet_luc)
                                                             VALUES (%s, 9, 'TAY', 'DA_DUYET', %s, now())""", (hd["id"], CFO))
        self.sql_loi("PHIEN_BAN_DA_DUYET_BAT_BIEN", CFO, "UPDATE master.hop_dong_phien_ban SET tham_so = '{}'::jsonb WHERE id = %s", (v1,))
        self.sql_loi("PHIEN_BAN_DA_DUYET_BAT_BIEN", CFO, "UPDATE master.hop_dong_phien_ban SET ngay_hieu_luc = '2026-01-01' WHERE id = %s", (v1,))
        self.sql_loi("THAM_SO_BAT_BIEN", KTA, "UPDATE master.hop_dong_tham_so SET gia_tri = '1' WHERE phien_ban_id = %s", (v1,))
        self.sql_loi("THAM_SO_BAT_BIEN", KTA, "INSERT INTO master.hop_dong_tham_so (phien_ban_id, ten, gia_tri, nguon) VALUES (%s, 'X', NULL, 'TAY')", (v1,))
        self.sql_loi("LICH_BAT_BIEN", KTA, "UPDATE master.lich_thu SET so_tien_minor = 1 WHERE phien_ban_id = %s", (v1,))
        self.sql_loi("LICH_CHI_SINH_KHI_DUYET", CFO, """INSERT INTO master.lich_thu (phien_ban_id, phap_nhan_id, dot, so_tien_minor, khoa_nghia_vu)
                                                        VALUES (%s, %s, 9, 1, 'DOT-9')""", (v1, self.ids["PN_DEMO_A"]))
        self.raises("permission denied", lambda: self.sql(KTA, "DELETE FROM master.lich_thu WHERE phien_ban_id = %s", (v1,)))
        self.sql_loi("HOP_DONG_DA_DUYET_KHONG_DOI_MAPPING", KTA, """UPDATE master.hop_dong SET doi_tac_id = (SELECT doi_tac_id FROM master.doi_tac_ma_junsky
                                                                     WHERE object_id_junsky = 'KH_DEMO.CHUNG_A') WHERE id = %s""", (hd["id"],))
        self.sql_loi("HOP_DONG_KHONG_DOI_DINH_DANH", KTA, "UPDATE master.hop_dong SET so_hop_dong = 'KHAC' WHERE id = %s", (hd["id"],))
        self.sql_loi("CON_TRO_PHIEN_BAN_SAI", CFO, "UPDATE master.hop_dong SET phien_ban_hien_hanh = %s WHERE id = %s", (self.state["nha_v1"], hd["id"]))
        # FK cùng pháp nhân / cùng hợp đồng: kể cả chủ CSDL (bỏ qua RLS) cũng không ghi được tham chiếu chéo
        a, b = self.ids["PN_DEMO_A"], self.ids["PN_DEMO_B"]
        du_an_b = self.admin.execute("SELECT id FROM master.du_an WHERE phap_nhan_id = %s", (b,)).fetchone()[0]
        lh_b = self.admin.execute("SELECT id FROM master.loai_hinh_doanh_thu WHERE phap_nhan_id = %s LIMIT 1", (b,)).fetchone()[0]
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            self.admin.execute("INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, du_an_id) VALUES (%s,'THUE_DAT','FK-1','FK/1',%s)", (a, du_an_b))
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            self.admin.execute("INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, loai_hinh_dt_id) VALUES (%s,'THUE_DAT','FK-2','FK/2',%s)", (a, lh_b))
        self.raises("DOI_TAC_KHONG_THUOC_PHAP_NHAN", lambda: self.admin.execute(
            """INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, doi_tac_id)
               SELECT %s,'THUE_DAT','FK-3','FK/3', doi_tac_id FROM master.doi_tac_ma_junsky WHERE object_id_junsky = 'KH_DEMO.B01'""", (a,)))
        hd_khac = self.admin.execute("INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong) VALUES (%s,'THUE_DAT','FK-4','FK/4') RETURNING id", (a,)).fetchone()[0]
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):  # thay_cho trỏ phiên bản của hợp đồng khác cùng pháp nhân
            self.admin.execute("INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon, thay_cho_id) VALUES (%s, 2, 'TAY', %s)", (hd_khac, v1))
        self.raises("CHUNG_TU_KHAC_PHAP_NHAN", lambda: self.admin.execute(  # chứng từ hợp đồng của pháp nhân khác
            """INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon, chung_tu_id)
               SELECT %s, 1, 'TAY', id FROM kho.chung_tu WHERE phap_nhan_id = %s AND loai = 'HOP_DONG_TEP' LIMIT 1""", (hd_khac, b)))
        self.raises("PROFILE_KHAC_PHAP_NHAN", lambda: self.admin.execute(
            "INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon, loai_hinh_dt_id) VALUES (%s, 1, 'TAY', %s)", (hd_khac, lh_b)))

    def test_t07_thieu_can_cu_khoa_mapping_va_bo_sung_ho_so(self):
        fx, env, vb = kcn_khac("09")
        next(p for p in fx["tham_so"] if p["ma"] == "TT-02")["trich_dan"] = None
        env.pop("doi_tac_object_id")
        r = self.nhan_fx(fx, env, vb)
        self.assertEqual({c["ma"] for c in r["chan"]}, {"THIEU_CAN_CU", "MAPPING_DOI_TAC"})
        pb = r["phien_ban_id"]
        self.raises("CRM_CHUA_DU_DIEU_KIEN", lambda: self.crm.kiem_truoc(KTA, pb))
        self.raises("MAPPING_KHONG_CO_MA", lambda: self.crm.cap_nhat_mapping(KTA, pb, {"doi_tac_object_id": "KH_DEMO.B01"}))  # mã của pháp nhân khác
        self.assertEqual({c["ma"] for c in self.crm.cap_nhat_mapping(KTA, pb, {"doi_tac_object_id": "KH_DEMO.CHUNG_A"})["chan"]}, {"THIEU_CAN_CU"})
        h09 = self.hd(KTA, "HDC-KCN-DEMO-09")
        tt02 = next(p for p in h09["phien_ban"][0]["tham_so"] if p["ma"] == "TT-02")
        self.assertEqual((tt02["can_cu"], tt02["gia_tri_hieu_luc"], tt02["gia_tri_tho"], h09["gia_tri"]), ("KHONG_QUY_DINH", None, "3.000.000.000", None))
        # CHO_KHOA (thiếu mã HĐ chung) → bổ sung đúng hồ sơ, không nhận raw lần 2
        fx, env, vb = kcn_khac("12")
        env.pop("ma_hop_dong_chung")
        r = self.nhan_fx(fx, env, vb)
        self.assertEqual((r["ket_qua"], r["ly_do"]), ("CHO_KHOA", ["THIEU_MA_HOP_DONG_CHUNG"]))
        ct = r["chung_tu_id"]
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.crm.bo_sung_ho_so(BH, ct, {"ma_hop_dong_chung": "HDC-KCN-DEMO-12"}))
        self.raises("BO_SUNG_TRUONG_LA", lambda: self.crm.bo_sung_ho_so(KTA, ct, {"phap_nhan": "PN_DEMO_B"}))
        before = self.counts()
        r2 = self.crm.bo_sung_ho_so(KTA, ct, {"ma_hop_dong_chung": "HDC-KCN-DEMO-12"})
        self.assertEqual((r2["ket_qua"], r2["chan"], r2["chung_tu_id"]), ("HOP_DONG_CHO_DUYET", [], ct))
        after = self.counts()
        self.assertEqual((after["kho.chung_tu"], after["kho.tep_goc"], after["master.hop_dong"]), (before["kho.chung_tu"], before["kho.tep_goc"], before["master.hop_dong"] + 1))
        self.assertEqual(self.admin.execute("SELECT count(*) FROM nhat_ky.su_kien WHERE doi_tuong_id = %s AND hanh_dong = 'BO_SUNG_HO_SO'", (ct,)).fetchone()[0], 1)
        self.assertEqual(self.admin.execute("""SELECT count(*) FROM kho.viec_can_duyet WHERE tham_chieu_id = %s AND trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')""",
                                            (ct,)).fetchone()[0], 0)
        self.raises("HO_SO_DA_LAP", lambda: self.crm.bo_sung_ho_so(KTA, ct, {"du_an": "DA_KCN_DEMO"}))
        # CHO_MAPPING (thiếu loại hình/loại bản) → bổ sung → lập tiếp; trùng số hợp đồng đã có → giữ chờ, không gộp
        r = self.crm.nhan_ket_qua_6(BH, canonical_json({**F.kcn_goc(), "model": "DEMO-KHAC"}).encode(), {"namespace": "TRICH_6_DEMO", "phap_nhan": "PN_DEMO_A"},
                                    van_ban_nguon=F.VB_KCN)
        self.assertEqual((r["ket_qua"], r["ly_do"]), ("CHO_MAPPING", ["THIEU_LOAI_HINH", "THIEU_LOAI_BAN"]))
        r3 = self.crm.bo_sung_ho_so(KTA, r["chung_tu_id"], {"loai_hinh": "DT-KCN-THUE-DAT-DEMO", "loai_ban": "GOC", "ma_hop_dong_chung": "HDC-KCN-DEMO-01"})
        self.assertEqual((r3["ket_qua"], r3["ly_do"]), ("XUNG_DOT", ["HOP_DONG_DA_CO"]))
        no_key = F.kcn_goc()
        next(p for p in no_key["tham_so"] if p["ma"] == "TC-01")["trich_dan"] = None
        before = self.counts()["master.hop_dong"]
        r = self.nhan_fx(no_key, F.env("PN_DEMO_A", "DT-KCN-THUE-DAT-DEMO", "GOC", "HD_DEMO_KHONG_SO", ma_hop_dong_chung="HDC-KCN-DEMO-10"), F.VB_KCN)
        self.assertEqual((r["ket_qua"], r["ly_do"]), ("CHO_KHOA", ["THIEU_SO_HOP_DONG_CO_CAN_CU"]))
        self.assertEqual(self.counts()["master.hop_dong"], before)
        chua_ai = F.ket_qua("HD_CHUA_AI_DEMO.docx", [{"ma": "TC-01", "doan_lien_quan": "Hợp đồng số ..."}], che_do="chua_chay_AI")
        r = self.nhan_fx(chua_ai, F.env("PN_DEMO_A", "DT-KCN-THUE-DAT-DEMO", "GOC", "HD_CHUA_AI", ma_hop_dong_chung="HDC-KCN-DEMO-11"), F.VB_KCN)
        self.assertEqual(r["ket_qua"], "CHO_KHOA")
        self.assertIn("TRICH6_CHUA_CHAY_AI", r["issues"])

    # ------------------------------------------------------------------ tiền từ M1 thật và liên kết
    def test_t08_tien_ve_qua_m1_va_noi_mot_phan_nhieu_lan_lap_go(self):
        before = self.counts()
        m1a = self.m1("PN_DEMO_A", "truoc_hop_dong")  # tiền ngày 25/08 — trước ngày hiệu lực HĐ 01/09
        t1 = self.tien(KTA, "DEMO-A-0001")
        lich = {k: v["id"] for k, v in self.lich("HDC-KCN-DEMO-01", 0).items()}
        self.crm.lien_ket(KTA, t1, lich["COC-1"], "300000000", "k-coc")  # tiền đến trước hợp đồng: chỉ thêm liên kết
        m1b = self.m1("PN_DEMO_A", "sau_hop_dong")  # tiền 10/10, 14/10 — HĐ đang hiệu lực, cọc đã nối → đợt gần nhất DOT-1
        self.assertEqual((m1a["moi"], m1b["moi"]), (1, 2))
        mid = self.counts()
        self.assertEqual(mid["kho.chung_tu"] - before["kho.chung_tu"], 3)  # một BANK logic = một chứng từ K2
        self.assertEqual(mid["kho.de_xuat"] - before["kho.de_xuat"], m1a["de_xuat"] + m1b["de_xuat"])  # đề xuất do engine M1 sinh, chiếu sang
        self.assertGreater(m1a["de_xuat"] + m1b["de_xuat"], 0)
        # TL32 §3.2: chưa có HĐ hiệu lực ngày tiền về → Có 344; có HĐ → Có 131 (đối tượng A01), Vàng, có bằng chứng HĐ, không tự phân bổ
        nhanh = {r[0]: r[1:] for r in self.admin.execute(
            """SELECT c.so_tien_minor, d.acct_id, d.object_id_junsky, x.can_cu->'_v12_proposal' FROM kho.de_xuat x JOIN kho.chung_tu c ON c.id = x.chung_tu_id
               JOIN kho.de_xuat_dong d ON d.de_xuat_id = x.id AND d.no_co = 'C' WHERE c.phap_nhan_id = %s AND c.loai = 'SAO_KE' AND c.du_lieu ? '_sqlite_id'""",
            (self.ids["PN_DEMO_A"],))}
        self.assertEqual({k: v[:2] for k, v in nhanh.items()}, {300_000_000: ("344", "KH_DEMO.A01"), 500_000_000: ("131", "KH_DEMO.A01"), 900_000_000: ("131", "KH_DEMO.A01")})
        self.assertIsNone(nhanh[300_000_000][2].get("contract_evidence"))
        for so in (500_000_000, 900_000_000):
            p = nhanh[so][2]
            ev = p["contract_evidence"]
            self.assertEqual((ev["applied"], ev["auto_allocate"], ev["previous_account"], ev["facts"][0]["dot_gan_nhat"]["khoa"]), (True, False, "344", "DOT-1"))
            self.assertEqual(ev["facts"][0]["provenance"]["ma_noi_bo"], "HDC-KCN-DEMO-01")
            self.assertEqual((p["allocations"], p["confidence"]["credit_account"]["level"]), ([], "CONTRACT_FACT"))
            self.assertFalse(any(c.startswith("CONTRACT_") for c in p["constraints"]))
        dong_id = lambda: [r[0] for r in self.admin.execute(  # noqa: E731
            """SELECT d.id::text FROM kho.de_xuat_dong d JOIN kho.de_xuat x ON x.id = d.de_xuat_id JOIN kho.chung_tu c ON c.id = x.chung_tu_id
               WHERE c.phap_nhan_id = %s ORDER BY 1""", (self.ids["PN_DEMO_A"],))]
        ids_truoc = dong_id()
        lap = self.m1("PN_DEMO_A", "sau_hop_dong")  # nạp lại + chiếu lại: không nhân BANK/đề xuất, giữ nguyên ID dòng đề xuất chưa duyệt
        self.assertEqual((lap["moi"], lap["trung"]), (0, 2))
        self.assertEqual({k: v for k, v in self.counts().items() if k != "nhat_ky.su_kien"}, {k: v for k, v in mid.items() if k != "nhat_ky.su_kien"})
        self.assertEqual(dong_id(), ids_truoc)
        ds = self.crm.danh_sach(KTA)["tien"]
        self.assertEqual((len(ds), {t["nguon_m1"] for t in ds}), (3, {True}))
        self.assertEqual(self.sql(BH, "SELECT count(*) AS n FROM kho.de_xuat")[0]["n"], 0)  # bán hàng (chỉ CRM) không đọc đề xuất M1
        self.assertEqual(self.sql(BH, "SELECT count(*) AS n FROM kho.chung_tu WHERE loai = 'SAO_KE'")[0]["n"], 0)
        self.assertEqual(self.crm.danh_sach(BH)["tien"], [])
        self.assertGreater(self.sql(KTA, "SELECT count(*) AS n FROM kho.de_xuat")[0]["n"], 0)
        t2, t3 = (self.tien(KTA, m) for m in ("DEMO-A-0002", "DEMO-A-0003"))
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.crm.lien_ket(CFO, t1, lich["COC-1"], "300000000", "k-coc"))  # quyền trước nhánh lặp
        first = self.crm.lien_ket(KTA, t2, lich["DOT-1"], "500000000", "k-d1-a")
        self.assertTrue(self.crm.lien_ket(KTA, t2, lich["DOT-1"], "500000000", "k-d1-a")["lap_lai"])  # retry cùng khóa
        self.raises("IDEMPOTENCY_KHAC", lambda: self.crm.lien_ket(KTA, t2, lich["DOT-1"], "400000000", "k-d1-a"))
        self.raises("LIEN_KET_DA_CO", lambda: self.crm.lien_ket(KTA, t2, lich["DOT-1"], "1", "k-d1-a-trung"))
        self.crm.lien_ket(KTA, t3, lich["DOT-1"], "700000000", "k-d1-b")
        self.raises("VUOT_NGHIA_VU", lambda: self.crm.lien_ket(KTA, t3, lich["COC-1"], "1", "k-vuot"))
        self.raises("LIEN_KET_THAM_CHIEU", lambda: self.crm.lien_ket(KTB, t3, lich["DOT-2"], "1", "k-cheo"))
        self.crm.go_lien_ket(KTA, first["lien_ket_id"], "DEMO gỡ để nối lại")
        self.assertTrue(self.crm.go_lien_ket(KTA, first["lien_ket_id"], "DEMO gỡ lặp")["lap_lai"])
        self.assertEqual(self.crm.lien_ket(KTA, t2, lich["DOT-1"], "500000000", "k-d1-a"), {"lien_ket_id": first["lien_ket_id"], "lap_lai": True, "trang_thai": "HUY"})
        st = {k: l["trang_thai"] for k, l in self.lich("HDC-KCN-DEMO-01", 0).items()}
        self.assertEqual(st, {"COC-1": "DA_THU", "DOT-1": "MOT_PHAN", "DOT-2": "CHUA_THU"})
        self.crm.lien_ket(KTA, t2, lich["DOT-1"], "500000000", "k-d1-a-lan2")
        self.assertEqual(self.lich("HDC-KCN-DEMO-01", 0)["DOT-1"]["trang_thai"], "DA_THU")
        self.assertEqual(self.lich("HDC-KCN-DEMO-01", 0)["DOT-1"]["da_thu"], "1200000000")
        self.raises("VUOT_TIEN_KHA_DUNG", lambda: self.crm.lien_ket(KTA, t1, lich["DOT-2"], "1", "k-het-tien"))
        usd = self.admin.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, tien_te, so_tien_minor, chieu, hash)
                                    VALUES (%s,'SAO_KE','DEMO-A-USD','2026-10-15','USD',100000,'THU',%s) RETURNING id""", (self.ids["PN_DEMO_A"], "1" * 64)).fetchone()[0]
        self.raises("LIEN_KET_KHAC_TIEN_TE", lambda: self.crm.lien_ket(KTA, usd, lich["DOT-2"], "100000", "k-usd"))
        after = self.counts()
        self.assertEqual((after["kho.de_xuat"], after["kho.de_xuat_dong"]), (mid["kho.de_xuat"], mid["kho.de_xuat_dong"]))  # nối không thêm đề xuất
        self.assertEqual(self.admin.execute("SELECT count(*) FROM kho.lien_ket_chung_tu WHERE loai = 'HOP_DONG_DOT_TIEN' AND trang_thai = 'HUY'").fetchone()[0], 1)
        self.state["tien_a3"] = t3
        self.state["m1_counts"] = {"truoc": before, "sau_nap": mid, "sau_noi": after, "de_xuat_m1": m1a["de_xuat"] + m1b["de_xuat"]}

    def test_t09_phu_luc_qua_khu_doi_phan_chua_thu_giu_link_cu(self):
        r = self.nhan("kcn_phu_luc")
        self.assertEqual((r["ket_qua"], r["chan"]), ("PHU_LUC_CHO_DUYET", []))
        hd = self.hd(KTA, "HDC-KCN-DEMO-01")
        v1, v2 = hd["phien_ban"]
        self.assertEqual((hd["hieu_luc_hom_nay"], v2["trang_thai"], len(v2["lich"])), (v1["id"], "CHO_DUYET", 0))  # chưa duyệt không đổi lịch hiệu lực
        self.crm.kiem_truoc(KTA, v2["id"])
        plan = {p["khoa"]: p["hanh_dong"] for p in self.crm.duyet(CFO, v2["id"])["ke_hoach"]}
        self.assertEqual(plan, {"COC-1": "GIU", "DOT-1": "GIU", "DOT-2": "DOI"})
        hd = self.hd(KTA, "HDC-KCN-DEMO-01")
        v1, v2 = hd["phien_ban"]
        self.assertEqual((hd["hien_hanh"], hd["hieu_luc_hom_nay"], v2["hieu_luc_hom_nay"], v1["hieu_luc_hom_nay"]), (v2["id"], v2["id"], True, False))
        new, old = {l["khoa"]: l for l in v2["lich"]}, {l["khoa"]: l for l in v1["lich"]}
        self.assertEqual((new["DOT-2"]["han"], new["DOT-2"]["moc"], new["DOT-2"]["thay_cho"]), ("2026-12-20", "BAN_GIAO_DAT", old["DOT-2"]["id"]))
        self.assertEqual(old["DOT-2"]["han"], None)  # lịch sử bản 1 giữ nguyên
        self.assertEqual(len([k for k in old["DOT-1"]["lien_ket"] if k["trang_thai"] != "HUY"]), 2)  # link đã thu trỏ đúng bản cũ
        self.assertEqual((new["COC-1"]["trang_thai"], new["DOT-1"]["trang_thai"], new["DOT-1"]["lien_ket"]), ("DA_THU", "DA_THU", []))
        self.raises("LICH_KHONG_HIEU_LUC", lambda: self.crm.lien_ket(KTA, self.state["tien_a3"], old["DOT-2"]["id"], "200000000", "k-cu"))
        self.crm.lien_ket(KTA, self.state["tien_a3"], new["DOT-2"]["id"], "200000000", "k-d2")  # một khoản tiền chia hai đợt, hai phiên bản
        self.assertEqual(self.lich("HDC-KCN-DEMO-01")["DOT-2"]["trang_thai"], "MOT_PHAN")

    def test_t10_phu_luc_tuong_lai_va_phu_luc_mo_ho_giu_cho(self):
        self.m1("PN_DEMO_B", "truoc_hop_dong")
        self.m1("PN_DEMO_B", "sau_hop_dong")
        b1, b2 = self.tien(KTB, "DEMO-B-0001"), self.tien(KTB, "DEMO-B-0002")
        nhanh = {r[0]: r[1:] for r in self.admin.execute(
            """SELECT c.so_tien_minor, d.acct_id, x.can_cu->'_v12_proposal'->'constraints' FROM kho.de_xuat x JOIN kho.chung_tu c ON c.id = x.chung_tu_id
               JOIN kho.de_xuat_dong d ON d.de_xuat_id = x.id AND d.no_co = 'C' WHERE c.phap_nhan_id = %s AND c.loai = 'SAO_KE'""", (self.ids["PN_DEMO_B"],))}
        # HĐ nhà ở hiệu lực 05/09: cả hai khoản → 131; khoản 300m vượt phần còn lại của đợt gần nhất (cọc 100m chưa nối) → chờ hỏi, không tự phân bổ
        self.assertEqual((nhanh[100_000_000][0], nhanh[300_000_000][0]), ("131", "131"))
        self.assertFalse(any(c.startswith("CONTRACT_") for c in nhanh[100_000_000][1]))
        self.assertIn("CONTRACT_AMOUNT_EXCEEDS_INSTALLMENT_WAIT", nhanh[300_000_000][1])
        lich = {k: v["id"] for k, v in self.lich("HDC-NHA-DEMO-07", 0, KTB).items()}
        self.crm.lien_ket(KTB, b1, lich["COC-1"], "100000000", "kb-coc")
        self.crm.lien_ket(KTB, b2, lich["DOT-1"], "300000000", "kb-d1")
        r = self.nhan("nha_phu_luc_mo_ho")
        self.assertIn("PHU_LUC_DOI_DOT_DA_THU", {c["ma"] for c in r["chan"]})
        self.raises("CRM_CHUA_DU_DIEU_KIEN", lambda: self.crm.kiem_truoc(KTB, r["phien_ban_id"]))
        lich_truoc = self.counts()["master.lich_thu"]
        self.crm.tu_choi(CFO, r["phien_ban_id"], "DEMO: phụ lục đổi đợt đã thu một phần chưa nêu cách chuyển nghĩa vụ")
        self.assertEqual(self.counts()["master.lich_thu"], lich_truoc)  # không nhân đôi nghĩa vụ
        r = self.nhan("nha_phu_luc")  # hiệu lực 01/11/2026 — sau ngày nghiệp vụ 19/10/2026
        self.crm.kiem_truoc(KTB, r["phien_ban_id"])
        out = self.crm.duyet(CFO, r["phien_ban_id"])
        self.assertEqual(({p["khoa"]: p["hanh_dong"] for p in out["ke_hoach"]}, out["hieu_luc_tu"]), ({"COC-1": "GIU", "DOT-1": "GIU", "DOT-2": "DOI"}, "2026-11-01"))
        h = self.hd(KTB, "HDC-NHA-DEMO-07")
        v1, _, v3 = h["phien_ban"]
        self.assertEqual([v["trang_thai"] for v in h["phien_ban"]], ["DA_DUYET", "TU_CHOI", "DA_DUYET"])
        self.assertEqual((h["hieu_luc_hom_nay"], v1["hieu_luc_hom_nay"], v3["sap_hieu_luc"]), (v1["id"], True, True))  # bản tương lai chưa thay bản hôm nay
        cur = {l["khoa"]: l for l in v3["lich"]}
        self.assertEqual((cur["DOT-1"]["trang_thai"], cur["DOT-2"]["han"]), ("MOT_PHAN", "2027-01-15"))
        self.raises("LICH_KHONG_HIEU_LUC", lambda: self.crm.lien_ket(KTB, b2, cur["DOT-2"]["id"], "1", "kb-tuong-lai"))
        self.raises("NGHIA_VU_SAP_THAY_DOI", lambda: self.crm.lien_ket(KTB, b2, lich["DOT-2"], "1", "kb-sap-doi"))  # CSDL chặn nối vào đợt sắp đổi
        try:
            CrmK2Test.ngay = date(2026, 11, 2)
            h = self.hd(KTB, "HDC-NHA-DEMO-07")
            self.assertEqual(h["hieu_luc_hom_nay"], v3["id"])
            self.raises("VUOT_TIEN_KHA_DUNG", lambda: self.crm.lien_ket(KTB, b2, cur["DOT-2"]["id"], "1", "kb-sau-hieu-luc"))  # qua kiểm hiệu lực, hết tiền
        finally:
            CrmK2Test.ngay = date(2026, 10, 19)

    # ------------------------------------------------------------------ V3/V4, race nghĩa vụ–tiền, retry đồng thời
    def test_t11_race_phu_luc_va_noi_tien_hai_thu_tu_va_retry_dong_thoi(self):
        fx, env, vb = kcn_khac("03")
        pb = self.nhan_fx(fx, env, vb)["phien_ban_id"]
        self.crm.kiem_truoc(KTA, pb)
        self.crm.duyet(CFO, pb)
        self.m1("PN_DEMO_A", "hop_dong_khac")
        t4 = self.tien(KTA, "DEMO-A-0004")
        v1 = {k: v["id"] for k, v in self.lich("HDC-KCN-DEMO-03").items()}
        # Thứ tự 1: nối tiền vào DOT-2 đang chạy (giữ khóa) → CFO duyệt phụ lục đổi DOT-2 phải chờ, rồi thấy đợt đã có tiền → chặn
        pl1 = self.nhan_fx(*kcn_pl("03", "PL01-KCN-DEMO-03", "01/10/2026", "LT-D2-HAN", "20/12/2026", "Đợt 2 thanh toán trước ngày 20/12/2026"))["phien_ban_id"]
        self.crm.kiem_truoc(KTA, pl1)
        with self.app2.transaction():
            self.crm2.lien_ket(KTA, t4, v1["DOT-2"], "100000000", "race-1")
            luong = _Luong(lambda: self.crm.duyet(CFO, pl1))
            luong.start()
            self.assertTrue(self.cho_khoa())
            self.assertTrue(luong.is_alive())
        luong.join(30)
        self.assertIsInstance(luong.loi, DataError)
        self.assertEqual(luong.loi.code, "CRM_CHUA_DU_DIEU_KIEN")
        self.assertIn("đổi đợt DOT-2 đã thu", str(luong.loi))  # PHU_LUC_DOI_DOT_DA_THU tính lại sau khi chờ khóa
        self.crm.tu_choi(CFO, pl1, "DEMO: đợt 2 đã có tiền khi duyệt")
        # Thứ tự 2: CFO duyệt phụ lục đổi DOT-1 đang chạy → nối tiền vào DOT-1 cũ phải chờ, rồi thấy đợt cũ hết hiệu lực → chặn
        pl2 = self.nhan_fx(*kcn_pl("03", "PL02-KCN-DEMO-03", "01/10/2026", "LT-D1-HAN", "30/10/2026", "Đợt 1 thanh toán trước ngày 30/10/2026"))["phien_ban_id"]
        self.crm.kiem_truoc(KTA, pl2)
        with self.app2.transaction():
            self.crm2.duyet(CFO, pl2)
            luong = _Luong(lambda: self.crm.lien_ket(KTA, t4, v1["DOT-1"], "100000000", "race-2"))
            luong.start()
            self.assertTrue(self.cho_khoa())
            self.assertTrue(luong.is_alive())
        luong.join(30)
        self.assertIsInstance(luong.loi, DataError)
        self.assertEqual(luong.loi.code, "LICH_KHONG_HIEU_LUC")
        moi = self.lich("HDC-KCN-DEMO-03")
        self.assertEqual((moi["DOT-1"]["han"], moi["DOT-2"]["trang_thai"], moi["DOT-2"]["da_thu"]), ("2026-10-30", "MOT_PHAN", "0"))  # DOT-2 GIU: tiền theo chuỗi khóa
        # Retry đồng thời cùng khóa trên hai kết nối: đúng một liên kết, lần kia trả lặp
        barrier = threading.Barrier(2)
        a = _Luong(lambda: self.crm.lien_ket(KTA, t4, moi["DOT-1"]["id"], "100000000", "retry-dong-thoi"), barrier)
        b = _Luong(lambda: self.crm2.lien_ket(KTA, t4, moi["DOT-1"]["id"], "100000000", "retry-dong-thoi"), barrier)
        a.start(); b.start(); a.join(30); b.join(30)
        self.assertEqual((a.loi, b.loi), (None, None))
        self.assertEqual(sorted([a.ket_qua["lap_lai"], b.ket_qua["lap_lai"]]), [False, True])
        self.assertEqual(a.ket_qua["lien_ket_id"], b.ket_qua["lien_ket_id"])
        self.assertEqual(self.admin.execute("SELECT count(*) FROM kho.lien_ket_chung_tu WHERE khoa_idempotency = 'retry-dong-thoi'").fetchone()[0], 1)
        self.raises("IDEMPOTENCY_KHAC", lambda: self.crm.lien_ket(KTA, t4, v1["COC-1"], "100000000", "retry-dong-thoi"))

    def test_t12_mapping_sau_kiem_va_xac_nhan_tham_so(self):
        fx, env, vb = kcn_khac("04")
        pb = self.nhan_fx(fx, env, vb)["phien_ban_id"]
        self.crm.kiem_truoc(KTA, pb)
        self.crm.cap_nhat_mapping(KTA, pb, {"doi_tac_object_id": "KH_DEMO.CHUNG_A"})
        v = self.hd(KTA, "HDC-KCN-DEMO-04")["phien_ban"][0]
        self.assertIsNone(v["kiem_boi"])  # đổi mapping → lần kiểm cũ hết hiệu lực (có sự kiện VO_HIEU_KIEM)
        self.raises("CHUA_KIEM_TRUOC", lambda: self.crm.duyet(CFO, pb))
        self.assertEqual(self.admin.execute("SELECT count(*) FROM nhat_ky.su_kien WHERE doi_tuong_id = %s AND hanh_dong = 'VO_HIEU_KIEM'", (pb,)).fetchone()[0], 1)
        self.crm.kiem_truoc(KTA, pb)
        hd = self.hd(KTA, "HDC-KCN-DEMO-04")["id"]
        self.sql(KTA, """UPDATE master.hop_dong SET doi_tac_id = (SELECT doi_tac_id FROM master.doi_tac_ma_junsky WHERE object_id_junsky = 'KH_DEMO.A01')
                         WHERE id = %s""", (hd,))  # client sửa thẳng mapping sau khi kiểm, bỏ qua service
        self.raises("KIEM_DA_HET_HIEU_LUC", lambda: self.crm.duyet(CFO, pb))  # vân tay lần kiểm không còn khớp → CSDL chặn
        self.crm.kiem_truoc(KTA, pb)
        self.assertEqual(self.crm.duyet(CFO, pb)["so_dot"], 3)
        # tham số "Suy ra": chặn đến khi kế toán xác nhận riêng tham số đó, có lý do
        fx, env, vb = kcn_khac("05")
        next(p for p in fx["tham_so"] if p["ma"] == "LT-D1-HAN")["ghi_chu"] = "Suy ra từ tiến độ dự kiến"
        r = self.nhan_fx(fx, env, vb)
        self.assertIn("SUY_RA", {c["ma"] for c in r["chan"]})
        pb = r["phien_ban_id"]
        self.raises("CRM_CHUA_DU_DIEU_KIEN", lambda: self.crm.kiem_truoc(KTA, pb, xac_nhan_can_cu_thu_cong=True))  # xác nhận chung không thay
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.crm.xac_nhan_tham_so(BH, pb, "LT-D1-HAN", "x"))
        self.raises("CAN_LY_DO", lambda: self.crm.xac_nhan_tham_so(KTA, pb, "LT-D1-HAN", " "))
        self.raises("THAM_SO_KHONG_CAN_XAC_NHAN", lambda: self.crm.xac_nhan_tham_so(KTA, pb, "TT-02", "x"))
        self.assertEqual(self.crm.xac_nhan_tham_so(KTA, pb, "LT-D1-HAN", "DEMO: đối chiếu tiến độ đã ký")["chan"], [])
        self.crm.kiem_truoc(KTA, pb)
        self.crm.duyet(CFO, pb)
        p = next(p for p in self.hd(KTA, "HDC-KCN-DEMO-05")["phien_ban"][0]["tham_so"] if p["ma"] == "LT-D1-HAN")
        self.assertEqual((p["can_cu"], p["xac_nhan_thu_cong"]["boi"], p["gia_tri_hieu_luc"]), ("SUY_RA", KTA, "15/10/2026"))

    def test_t13_trich_lai_doi_chieu_va_xu_ly(self):
        before = self.counts()["master.hop_dong_phien_ban"]
        r = self.crm.nhan_ket_qua_6(BH, canonical_json(F.kcn_goc(model="DEMO-MODEL-LAN-2")).encode(), F.mau("kcn_goc")[1], van_ban_nguon=F.VB_KCN)
        self.assertEqual((r["trung"], r["ket_qua"]), (False, "TRICH_LAI"))
        self.assertEqual(self.counts()["master.hop_dong_phien_ban"], before)
        dc = self.crm.doi_chieu_trich_lai(KTA, r["chung_tu_id"])
        self.assertEqual((dc["so_khac"], dc["co_the_ap_dung"], dc["trang_thai_ban"]), (0, False, "DA_DUYET"))
        self.raises("TRICH_LAI_BAN_DA_DUYET", lambda: self.crm.xu_ly_trich_lai(KTA, r["chung_tu_id"], "AP_DUNG", "DEMO"))
        self.assertEqual(self.crm.xu_ly_trich_lai(KTA, r["chung_tu_id"], "GIU_BAN_CU", "DEMO: cùng nội dung"), {"ket_qua": "GIU_BAN_CU"})
        self.raises("KHONG_PHAI_TRICH_LAI_CHO", lambda: self.crm.doi_chieu_trich_lai(KTA, r["chung_tu_id"]))
        # bản đang chờ duyệt: trích lại đổi hạn đợt 1 → đối chiếu → áp dụng → bản cũ THAY_THE có vết, bản mới phải kiểm/duyệt lại
        fx, env, vb = kcn_khac("06")
        pb_cu = self.nhan_fx(fx, env, vb)["phien_ban_id"]
        fx2, _, vb2 = kcn_khac("06", **{"LT-D1-HAN": ("16/10/2026", "trước ngày 16/10/2026", "15/10/2026", "16/10/2026")})
        r = self.nhan_fx(fx2, env, vb2)
        self.assertEqual(r["ket_qua"], "TRICH_LAI")
        dc = self.crm.doi_chieu_trich_lai(KTA, r["chung_tu_id"])
        self.assertEqual(([d["ma"] for d in dc["dong"] if d["khac"]], dc["co_the_ap_dung"], dc["phien_ban_id"]), (["LT-D1-HAN"], True, pb_cu))
        self.raises("TRICH_LAI_HANH_DONG", lambda: self.crm.xu_ly_trich_lai(KTA, r["chung_tu_id"], "AP_DUNG", ""))
        ap = self.crm.xu_ly_trich_lai(KTA, r["chung_tu_id"], "AP_DUNG", "DEMO: bản trích lại đúng Word")
        h = self.hd(KTA, "HDC-KCN-DEMO-06")
        self.assertEqual([(v["phien_ban"], v["trang_thai"]) for v in h["phien_ban"]], [(1, "THAY_THE"), (2, "CHO_DUYET")])
        self.sql_loi("PHIEN_BAN_DA_CHOT", KTA, "UPDATE master.hop_dong_phien_ban SET ly_do = 'x' WHERE id = %s", (pb_cu,))
        self.crm.kiem_truoc(KTA, ap["phien_ban_id"])
        self.crm.duyet(CFO, ap["phien_ban_id"])
        self.assertEqual(self.lich("HDC-KCN-DEMO-06")["DOT-1"]["han"], "2026-10-16")

    # ------------------------------------------------------------------ file soát, HTTP theo phiên, restart, vai trò cũ
    def test_t14_file_soat_crm_xuat_tai_va_restart(self):
        from kho_tri_thuc.xuat import excel
        hd = self.hd(KTA, "HDC-KCN-DEMO-01")["id"]
        self.raises("KHONG_CO_QUYEN_HANH_DONG", lambda: self.crm.xuat_file_soat(BH, hd))
        before = self.counts()
        out = self.crm.xuat_file_soat(CFO, hd)
        self.assertEqual(self.counts()["kho.lo_xuat"], before["kho.lo_xuat"] + 1)
        for t in ("kho.de_xuat", "kho.chung_tu", "kho.lien_ket_chung_tu", "master.lich_thu"):
            self.assertEqual(self.counts()[t], before[t])
        ten, raw = self.crm.tep_file_soat(KTA, out["id"])
        self.assertEqual((ten, sha256(raw)), (out["ten"], out["sha256"]))
        wb = excel.load(raw)
        self.assertEqual(wb.sheetnames, ["HOP_DONG_PHIEN_BAN", "LICH_NGHIA_VU", "THAM_SO_CAN_CU", "CANH_BAO"])
        lich = excel.rows(wb, "LICH_NGHIA_VU", [c.value for c in wb["LICH_NGHIA_VU"][1]])
        self.assertEqual(len(lich), 6)  # 3 đợt bản 1 + 3 đợt bản 2, giữ lịch sử
        self.assertEqual(sorted(r["khoa_nghia_vu"] for r in lich if r["hieu_luc_hom_nay"] == "CÓ"), ["COC-1", "DOT-1", "DOT-2"])
        self.assertIn("KHÔNG phải file nhập Junsky", " ".join(str(r["noi_dung"]) for r in excel.rows(wb, "CANH_BAO", ["noi_dung"])))
        row = self.admin.execute("SELECT loai, du_lieu->>'module', du_lieu->>'loai' FROM kho.lo_xuat WHERE id = %s", (out["id"],)).fetchone()
        self.assertEqual(tuple(row), ("FILE_SOAT", "CRM", "LICH_NGHIA_VU"))
        self.raises("FILE_SOAT", lambda: self.crm.tep_file_soat(KTB, out["id"]))  # RLS: pháp nhân khác không thấy lô
        app3 = psycopg.connect(self.app_dsn, autocommit=True, row_factory=dict_row)
        try:
            self.assertEqual(sha256(CrmK2(app3, self.root).tep_file_soat(CFO, out["id"])[1]), out["sha256"])  # restart: tải lại đúng bytes
        finally:
            app3.close()
        self.state["file_soat"] = out

    def test_t14b_bo_chieu_tu_choi_truoc_ghi_va_hoan_tac_toan_bo(self):
        """G12: nguồn sai không được đổi đích. Chạy SAU mọi lần chiếu dương của lớp (ca 3 để lại một dòng mồ côi DEMO làm bằng chứng)."""
        import json
        import shutil
        import sqlite3
        a = self.ids["PN_DEMO_A"]

        def snap():
            q = lambda sql: [tuple(r) for r in self.admin.execute(sql, (a,))]  # noqa: E731
            return (q("SELECT id::text, hash, mo_ta, du_lieu::text, trang_thai, so_tien_minor FROM kho.chung_tu WHERE phap_nhan_id = %s AND loai = 'SAO_KE' ORDER BY 1"),
                    q("SELECT x.id::text, x.muc, x.can_cu::text FROM kho.de_xuat x JOIN kho.chung_tu c ON c.id = x.chung_tu_id WHERE c.phap_nhan_id = %s ORDER BY 1"),
                    q("""SELECT d.id::text, d.acct_id, d.base_deb, d.base_crd, d.object_id_junsky FROM kho.de_xuat_dong d JOIN kho.de_xuat x ON x.id = d.de_xuat_id
                         JOIN kho.chung_tu c ON c.id = x.chung_tu_id WHERE c.phap_nhan_id = %s ORDER BY 1"""),
                    q("SELECT count(*) FROM kho.lien_ket_chung_tu WHERE phap_nhan_id = %s"), q("SELECT count(*) FROM kho.lo_xuat WHERE phap_nhan_id = %s"),
                    q("SELECT count(*) FROM kho.tep_goc WHERE phap_nhan_id = %s"))
        goc = self.state["sqlite"]["PN_DEMO_A"]
        tmp = Path(tempfile.mkdtemp(prefix="ktt_crm_g12_"))
        truoc = snap()
        # Ca 1 — core_hash nguồn sai trên BẢN SAO: từ chối trước mọi ghi
        sai = tmp / "sai-core-hash.sqlite"
        shutil.copy2(goc, sai)
        with sqlite3.connect(sai) as s:
            s.execute("UPDATE documents SET core_hash = ? WHERE id = (SELECT id FROM documents WHERE kind = 'BANK' ORDER BY id LIMIT 1)", ("0" * 64,))
        s.close()
        c = m1_demo.chieu_sang_k2(str(sai), self.dsn)
        self.assertEqual((c["ok"], c["da_ghi"], c["tu_choi"], c["lech_noi_dung"]), (False, False, "CORE_HASH_NGUON_TRUOC_GHI", ["core_hash_nguon"]))
        self.assertEqual(snap(), truoc)
        # Ca 2 — chạy lại nguồn đúng sau lỗi: đạt, không nhân, không mất lịch sử, giữ nguyên ID dòng
        c = m1_demo.chieu_sang_k2(goc, self.dsn)
        self.assertEqual((c["ok"], c["da_ghi"]), (True, True), c)
        self.assertEqual(snap(), truoc)
        # Ca 3 — nguồn hợp lệ nhưng đổi nội dung một BANK (hash tính lại đúng) + đích có bản ghi lạ: bộ chiếu đã GHI nội dung mới rồi đối
        # chiếu thấy thừa → rollback toàn bộ: nội dung BANK đích vẫn như cũ (oracle nhân quả: không rollback thì mo_ta sẽ là bản sửa)
        sua = tmp / "sua-noi-dung.sqlite"
        shutil.copy2(goc, sua)
        with sqlite3.connect(sua) as s:
            did, core = s.execute("SELECT id, core_json FROM documents WHERE kind = 'BANK' ORDER BY id LIMIT 1").fetchone()
            core = {**json.loads(core), "description": "DEMO MO TA SUA DE KIEM ROLLBACK"}
            s.execute("UPDATE documents SET core_json = ?, core_hash = ? WHERE id = ?", (canonical_json(core), sha256(canonical_json(core).encode()), did))
        s.close()
        self.admin.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, du_lieu, hash)
                              VALUES (%s,'KHAC','DEMO-MO-COI-T14B','2026-10-01','{"_sqlite_id": 987654321, "ghi_chu": "DEMO t14b"}',%s)""", (a, "2" * 64))
        truoc = snap()
        c = m1_demo.chieu_sang_k2(str(sua), self.dsn)
        self.assertEqual((c["ok"], c["da_ghi"], c["tu_choi"]), (False, False, "DOI_CHIEU_KHONG_DAT_DA_HOAN_TAC"), c)
        self.assertIn("kho.chung_tu", c["lech_noi_dung"])
        self.assertEqual(snap(), truoc)
        self.assertEqual(self.admin.execute("SELECT count(*) FROM kho.chung_tu WHERE mo_ta = 'DEMO MO TA SUA DE KIEM ROLLBACK'").fetchone()[0], 0)

    def test_t15_http_danh_tinh_theo_phien_va_tai_file_soat(self):
        import http.client
        import json
        from unittest.mock import patch
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        with patch.dict(os.environ, {LocalApp.CRM_ENV: self.app_dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"}):  # DB fixture kho_test_* cho phép rõ
            os.environ.pop(LocalApp.CRM_ENV_ADMIN, None)
            app = LocalApp(ROOT / "cau_hinh.toml", Path(tempfile.mkdtemp(prefix="ktt_crm_http_")) / "web")
            self.assertEqual(app.crm_state(KTA)["nguoi"]["dang_nhap"], KTA)  # đường kết nối/kiểm role trực tiếp, ngoài HTTP
            server = LocalServer(app, 0)
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
            thread.start()
            try:
                def call(path, body=None, cookie=None, token=True):
                    c = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=30)
                    headers = {"X-KTT-Token": app.token} if token else {}
                    if cookie:
                        headers["Cookie"] = f"{LocalApp.CRM_COOKIE}={cookie}"
                    c.request("POST" if body is not None else "GET", path, body=None if body is None else json.dumps(body), headers=headers)
                    r = c.getresponse()
                    raw, set_cookie = r.read(), r.getheader("Set-Cookie")
                    c.close()
                    is_json = (r.getheader("Content-Type") or "").startswith("application/json")
                    return r.status, (json.loads(raw or b"{}") if is_json else raw), set_cookie
                self.assertEqual(call("/api/crm", token=False)[0], 403)
                status, s1, ck = call("/api/crm")
                self.assertIn("HttpOnly", ck)
                self.assertIn("SameSite=Strict", ck)
                c1 = ck.split(";", 1)[0].split("=", 1)[1]
                self.assertEqual((status, s1["cau_hinh"], s1["nguoi"]["dang_nhap"]), (200, True, KTA))
                self.assertEqual({h["phap_nhan"] for h in s1["hop_dong"]}, {"PN_DEMO_A"})
                _, _, ck2 = call("/api/crm")
                c2 = ck2.split(";", 1)[0].split("=", 1)[1]
                self.assertNotEqual(c1, c2)
                self.assertEqual(call("/api/crm/danh-tinh", {"dang_nhap": CFO}, c2)[0], 200)
                self.assertEqual({h["phap_nhan"] for h in call("/api/crm", cookie=c2)[1]["hop_dong"]}, {"PN_DEMO_A", "PN_DEMO_B"})
                self.assertEqual(call("/api/crm", cookie=c1)[1]["nguoi"]["dang_nhap"], KTA)  # phiên khác không bị đổi danh tính
                self.assertIsNone(call("/api/crm", cookie=c1)[2])  # phiên đã có: không cấp cookie mới
                self.assertEqual(call("/api/crm/duyet", {"id": self.state["kcn_v1"]})[1]["error"], "CRM_PHIEN")  # không cookie → không thao tác
                self.assertEqual(call("/api/crm/duyet", {"id": self.state["kcn_v1"]}, "sid-tu-dat")[1]["error"], "CRM_PHIEN")
                self.assertEqual(call("/api/crm/danh-tinh", {"dang_nhap": "NGUOI_THAT_DEMO"}, c1)[1]["error"], "DANH_TINH_MO_PHONG")
                self.assertEqual(call("/api/crm/duyet", {"id": self.state["kcn_v1"], "actor": CFO}, c1)[1]["error"], "CRM_CLIENT_IDENTITY")
                self.assertEqual(call("/api/crm/duyet", {"id": self.state["kcn_v1"]}, c1)[1]["error"], "KHONG_CO_QUYEN_HANH_DONG")
                self.assertTrue(call("/api/crm/mau", {"mau": "kcn_goc"}, c1)[1]["trung"])  # nhận lại cùng raw qua giao diện → không trùng
                self.assertEqual(call("/api/crm/m1-sao-ke", {"mau": "PN_DEMO_A:sau_hop_dong"}, c1)[1]["error"], "CRM_M1_CHUA_CAU_HINH")
                lich = self.lich("HDC-KCN-DEMO-01")["DOT-2"]["id"]
                status, err, _ = call("/api/crm/lien-ket", {"tien": self.state["tien_a3"], "lich": lich, "so_tien": "1", "khoa": "k-http"}, c2)
                self.assertEqual((status, err["error"]), (400, "KHONG_CO_QUYEN_HANH_DONG"))  # CFO không nối tiền
                hd = self.hd(KTA, "HDC-KCN-DEMO-01")["id"]
                status, lo, _ = call("/api/crm/file-soat", {"id": hd}, c2)
                self.assertEqual(status, 200)
                status, raw, _ = call(f"/api/crm/file-soat/{lo['id']}", cookie=c2)
                self.assertEqual((status, raw[:2], sha256(raw)), (200, b"PK", lo["sha256"]))
                self.assertEqual(call(f"/api/crm/file-soat/{lo['id']}")[1]["error"], "CRM_PHIEN")
                call("/api/crm/danh-tinh", {"dang_nhap": KTB}, c1)
                self.assertEqual(call(f"/api/crm/file-soat/{lo['id']}", cookie=c1)[1]["error"], "FILE_SOAT")
                call("/api/crm/danh-tinh", {"dang_nhap": KT_M1}, c1)
                s = call("/api/crm", cookie=c1)[1]
                self.assertEqual((s["hop_dong"], s["nguoi"]["dang_nhap"]), ([], KT_M1))
                self.assertTrue(s["khong_quyen"])
            finally:
                server.shutdown(); server.server_close(); thread.join(3)

    def test_t16_restart_nhat_ky_chi_ghi_them_va_tong_hop(self):
        app3 = psycopg.connect(self.app_dsn, autocommit=True, row_factory=dict_row)
        try:
            again = CrmK2(app3, self.root, hom_nay=lambda: CrmK2Test.ngay).danh_sach(CFO)
            self.assertEqual(len(again["hop_dong"]), len(self.crm.danh_sach(CFO)["hop_dong"]))
            with self.assertRaises(psycopg.Error):
                app3.execute("UPDATE nhat_ky.su_kien SET ly_do = 'x'")
        finally:
            app3.close()
        c = self.counts()
        self.assertGreater(c["nhat_ky.su_kien"], 10)
        print("\nCRM_K2_AGGREGATE", canonical_json({"db": self.db, "role": self.role, "schema": PG_SCHEMA_VERSION, "counts": c,
                                                     "compat": self.state.get("compat"), "m1": self.state.get("m1_counts"), "chieu": self.state.get("chieu"),
                                                     "file_soat": self.state.get("file_soat")}))

    def test_t17_vai_tro_ke_toan_cu_khong_thay_bao_mat_giu_role(self):
        """Tương đương test_pg_schema t15 nhưng KHÔNG chạy DROP OWNED/DROP ROLE: role DEMO giữ lại làm bằng chứng."""
        if self.admin.execute("SELECT 1 FROM pg_roles WHERE rolname = 'app_ke_toan'").fetchone() is None:
            self.skipTest("chưa có vai trò app_ke_toan trên máy chủ test (không tính đạt)")
        role, pw = "rv_demo_kt_" + uuid.uuid4().hex[:8], uuid.uuid4().hex
        self.admin.execute(f"CREATE ROLE {role} LOGIN PASSWORD '{pw}' IN ROLE app_ke_toan")
        self.admin.execute(f'GRANT CONNECT ON DATABASE "{self.db}" TO {role}')
        with psycopg.connect(f"postgresql://{role}:{pw}@{self.dsn.split('@', 1)[1]}", autocommit=True) as kt:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                kt.execute("SELECT count(*) FROM bao_mat.mask_bi_danh")
            self.assertGreaterEqual(kt.execute("SELECT count(*) FROM kho.chung_tu").fetchone()[0], 1)
            for sql in ("DELETE FROM nhat_ky.su_kien", "UPDATE nhat_ky.su_kien SET ly_do='x'", "TRUNCATE nhat_ky.su_kien"):
                with self.assertRaises(psycopg.Error):
                    kt.execute(sql)
            kt.execute("INSERT INTO nhat_ky.su_kien (nguoi, loai, doi_tuong_bang, hanh_dong) VALUES ('DEMO','HE_THONG','test','GHI')")
        print("\nCRM_RETAINED_ROLE", role)

    def test_t18_bien_hieu_luc_ban_da_duyet(self):
        kcn = self.hd(CFO, "HDC-KCN-DEMO-01")["phien_ban"]
        v1, v2 = kcn[0]["id"], kcn[1]["id"]
        q = lambda: [tuple(r) for r in self.admin.execute(  # noqa: E731
            "SELECT id::text, valid_from, valid_to FROM master.hop_dong_phien_ban WHERE hop_dong_id = (SELECT hop_dong_id FROM master.hop_dong_phien_ban WHERE id = %s) ORDER BY phien_ban", (v1,))]
        truoc = q()
        # control dương (đã chạy ở t09 qua service): CFO duyệt phụ lục đóng đúng bản trước tại đúng valid_from của bản thay
        self.assertEqual((truoc[0][2], truoc[1][2]), (truoc[1][1], None))
        cases = ((BH, "UPDATE master.hop_dong_phien_ban SET valid_to = '2026-01-02T00:00:00+00' WHERE id = %s", v2, "HIEU_LUC_KHONG_HOP_LE"),
                 (BH, "UPDATE master.hop_dong_phien_ban SET valid_to = NULL WHERE id = %s", v1, "HIEU_LUC_DA_DONG"),
                 (XEM, "UPDATE master.hop_dong_phien_ban SET valid_to = '2026-01-02T00:00:00+00' WHERE id = %s", v2, "HIEU_LUC_KHONG_HOP_LE"),
                 (CFO, "UPDATE master.hop_dong_phien_ban SET valid_to = '2027-01-01T00:00:00+00' WHERE id = %s", v2, "HIEU_LUC_KHONG_HOP_LE"),
                 (CFO, "UPDATE master.hop_dong_phien_ban SET valid_to = NULL WHERE id = %s", v1, "HIEU_LUC_DA_DONG"),
                 (CFO, "UPDATE master.hop_dong_phien_ban SET valid_to = '2026-01-01T00:00:00+00' WHERE id = %s", v1, "HIEU_LUC_DA_DONG"))
        for login, sql, pid, code in cases:
            self.sql_loi(code, login, sql, (pid,))
        pending = self.hd(KTA, "HDC-KCN-DEMO-09")["phien_ban"][0]
        self.assertEqual(pending["trang_thai"], "CHO_DUYET")
        self.sql_loi("HIEU_LUC_KHONG_HOP_LE", KTA, "UPDATE master.hop_dong_phien_ban SET valid_from = '2020-01-01T00:00:00+00' WHERE id = %s", (pending["id"],))
        self.assertEqual(q(), truoc)  # trước/sau giống hệt: không dòng nào đổi

    def test_t19_helper_doc_chi_trong_pham_vi(self):
        kcn, nha = self.hd(CFO, "HDC-KCN-DEMO-01"), self.hd(CFO, "HDC-NHA-DEMO-07")
        lich_a = {l["khoa"]: l["id"] for l in kcn["phien_ban"][0]["lich"]}["DOT-1"]
        lich_b = {l["khoa"]: l["id"] for l in nha["phien_ban"][0]["lich"]}["DOT-1"]
        goi = (("SELECT master.crm_da_lien_ket(%s, 'DOT-1') AS v", kcn["id"], nha["id"]), ("SELECT master.crm_da_lien_ket_dong(%s) AS v", lich_a, lich_b),
               ("SELECT master.crm_phien_ban_hieu_luc(%s, '2026-10-19') AS v", kcn["id"], nha["id"]),
               ("SELECT master.crm_van_tay_phien_ban(%s) AS v", kcn["phien_ban"][1]["id"], nha["phien_ban"][0]["id"]))
        # control dương trước: KT_A và bán hàng (chỉ CRM, không M1) đọc aggregate của chính PN_A
        dung = {}
        for login in (KTA, BH):
            dung[login] = [self.sql(login, sql, (id_a,))[0]["v"] for sql, id_a, _ in goi]
        self.assertEqual(dung[KTA], dung[BH])
        self.assertEqual((dung[KTA][0], dung[KTA][1], str(dung[KTA][2])), (1_200_000_000, 1_200_000_000, kcn["phien_ban"][1]["id"]))
        self.assertTrue(dung[KTA][3])
        self.assertIsNotNone(self.sql(KTB, goi[0][0], (nha["id"],))[0]["v"])  # control dương PN_B cho KT_B
        # ngoài phạm vi: PN khác, không module CRM, thiếu/lệch danh tính, ID không tồn tại → NULL như nhau (không lộ dữ liệu/tồn tại)
        for sql, id_a, id_b in goi:
            self.assertIsNone(self.sql(KTA, sql, (id_b,))[0]["v"], sql)
            self.assertIsNone(self.sql(KT_M1, sql, (id_a,))[0]["v"], sql)
            self.assertIsNone(self.sql(KTA, sql, (id_a,), chi_id=True)[0]["v"], sql)
            self.assertIsNone(self.sql(CFO, sql, (id_a,), id_login=KTA)[0]["v"], sql)
            self.assertIsNone(self.sql(KTA, sql, (str(uuid.uuid4()),))[0]["v"], sql)
            self.assertIsNone(self.app.execute(sql, (id_a,)).fetchone()["v"], sql)  # không có danh tính phiên
        for sql in ("SELECT master.da_lien_ket(%s, 'DOT-1')", "SELECT master.phien_ban_hieu_luc(%s, '2026-10-19')", "SELECT master.van_tay_phien_ban(%s)"):
            self.raises("permission denied", lambda: self.sql(KTA, sql, (kcn["id"],)))
        self.raises("permission denied", lambda: self.sql(KTA, "SELECT master.da_lien_ket_dong(%s)", (lich_a,)))
        acl = {r[0]: r[1] for r in self.admin.execute("""SELECT p.proname, coalesce(p.proacl::text, '') FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                                                         WHERE n.nspname = 'master' AND p.proname IN ('da_lien_ket','da_lien_ket_dong','phien_ban_hieu_luc','van_tay_phien_ban',
                                                         'crm_da_lien_ket','crm_da_lien_ket_dong','crm_phien_ban_hieu_luc','crm_van_tay_phien_ban')""")}
        self.assertEqual(len(acl), 8)
        for name, text in acl.items():
            items = text.strip("{}").split(",")
            self.assertTrue(text and not any(i.startswith("=") for i in items), (name, text))  # không PUBLIC EXECUTE (ACL NULL = mặc định PUBLIC)
            self.assertEqual(any(i.startswith("app_web=") for i in items), name.startswith("crm_"), (name, text))

    def test_t21_buoc_chuan_bi_nut_mo_demo(self):
        """crm_khoi_dong.chuan_bi với kết nối truyền trong bộ nhớ (không ghi DSN ra đĩa): DB mới → tạo + migrate + seed; mở lại → dùng lại."""
        import json
        from psycopg.conninfo import make_conninfo
        from kho_tri_thuc.k2 import crm_khoi_dong
        ten = "kho_test_crm_nut_" + uuid.uuid4().hex[:8]
        kn = {"admin_dsn": make_conninfo(self.dsn, dbname=ten), "app_dsn": make_conninfo(self.app_dsn, dbname=ten)}
        lan1 = crm_khoi_dong.chuan_bi(kn, tien_to=("kho_test_crm_",))
        self.assertEqual((lan1["trang_thai"], lan1["db"], lan1["tao_db_moi"], lan1["schema_truoc"], lan1["schema_sau"]), ("SAN_SANG", ten, True, 0, PG_SCHEMA_VERSION))
        self.assertEqual(lan1["phap_nhan"], ["PN_DEMO_A", "PN_DEMO_B"])
        self.assertIn("DT-KCN-THUE-DAT-DEMO@v2", lan1["profile"])
        self.assertEqual({k: lan1["role_ung_dung"][k] for k in ("superuser", "bypassrls", "app_web")}, {"superuser": False, "bypassrls": False, "app_web": True})
        with psycopg.connect(kn["admin_dsn"], autocommit=True) as c:
            c.execute("INSERT INTO kho.tep_goc (phap_nhan_id, loai_nguon, duong_dan, hash, kich_thuoc, nguon, nguoi) SELECT id, 'TRICH_6', 'demo', %s, 1, 'TAY', 'MO_PHONG_KT_A' "
                      "FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'", ("3" * 64,))
        lan2 = crm_khoi_dong.chuan_bi(kn, tien_to=("kho_test_crm_",))
        self.assertEqual((lan2["tao_db_moi"], lan2["schema_truoc"], lan2["schema_sau"]), (False, PG_SCHEMA_VERSION, PG_SCHEMA_VERSION))
        with psycopg.connect(kn["admin_dsn"], autocommit=True) as c:  # mở lại giữ dữ liệu đã có
            self.assertEqual(c.execute("SELECT count(*) FROM kho.tep_goc WHERE hash = %s", ("3" * 64,)).fetchone()[0], 1)
        pw = self.app_dsn.split(":", 2)[2].split("@", 1)[0]
        self.assertNotIn(pw, json.dumps([lan1, lan2]))  # trạng thái không chứa bí mật
        self.raises("KET_NOI_DB_KHONG_DEMO", lambda: crm_khoi_dong.chuan_bi(kn))  # tên DB ngoài tiền tố DEMO bị từ chối
        if self.admin.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()[0]:
            self.raises("ROLE_UNG_DUNG_SAI", lambda: crm_khoi_dong.chuan_bi({**kn, "app_dsn": kn["admin_dsn"]}, tien_to=("kho_test_crm_",)))


if __name__ == "__main__":
    unittest.main()
