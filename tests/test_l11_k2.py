"""L11 QUANTITY R16 — service K2 (KhoSoLuongK2.l11_* / lien_ket) + seed l11_demo + hàm CSDL kho.l11_* — coder viết, CHƯA CHẠY (CODE_ONLY/UNRUN).

Thuần (không DB): profile bằng chứng đúng SHA canonical, fixture đúng manifest đã pin, JSON bằng chứng nghiêm (BOM/khóa trùng/float), lớp yêu cầu
không nhận authority (factor/kind/PN/pool/lượng pool) và lượng phải là CHUỖI exact.
PostgreSQL (chỉ khi root cấp KHO_PG_DSN_TEST, DB DEMO mới): crm → m5 → m2 → l11 seed; workflow thật theo docs/L11-QUANTITY-CASES-01.json:
Q00 nhận 4 bằng chứng raw + CFO BOTH V4 xác nhận (không seed approval), Q01/Q02 G01↔K01 4/4 ×2 (1 parent, 2 child) + vượt pool phiếu,
replay/409, Q03 THUNG 0.5↔6 ×2 với phiếu tách sáu + sai phép nhân, Q04 đổi tuyến → CAN_SOAT giữ lượng, Q06 forgery SQL, Q07 quyền hiện hành,
Q08 undo held + replay cũ trả HUY + FILE L11_QUANTITY. Q09 (race thật) KHÔNG có ở đây — root viết/chạy riêng.
Repair02 (UNRUN): token mã hóa lấy NGUYÊN từ DTO công khai (frozen01 tự băm json_chuan ≠ `{x}::text` của SQL → VERSION_CHANGED do test); mã lỗi
chính xác thay chuỗi con `L11_`; coverage PARTIAL/UNKNOWN/lỗi báo → HOLD; PN_B sentinel không lộ qua preview; ghi trực tiếp bỏ giao thức →
L11_KHOA_GOC_THIEU; workbook cells không công thức; lớp DB riêng cho mã hóa KHÔNG đồng nhất 12/1 (dương 0.01/0.12 → 0.12/0.12, còn 11.88/7.88;
âm 0.01/1.44 → đúng L11_SAI_PHEP_NHAN dù hai pool đủ).
Không DELETE/TRUNCATE/DROP/cleanup; DB/role/thư mục giữ làm bằng chứng.
"""

from __future__ import annotations

import io
import json
import os
import secrets
import tempfile
import threading
import time
import unittest
import uuid
import zipfile
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import DataError, sha256
from kho_tri_thuc.k2 import l11_demo, lien_ket_chung, m5_demo, nguon_chung
from kho_tri_thuc.k2.kho_so_luong import KhoSoLuongK2

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
ROOT = Path(__file__).resolve().parents[1]
XMLFIX, BRIDGE = ROOT / "tests" / "fixtures" / "m2_invoice_xml", ROOT / "tests" / "fixtures" / "m2_bridge"
LINK, PCFO = "MO_PHONG_L11_LINK_A", "MO_PHONG_L11_PROOF_CFO_A"
M2_INTAKE, M2_CFO = "MO_PHONG_M0_HD_INTAKE", "MO_PHONG_CFO_MUA_A"
M5_INTAKE, M5_CFO, M5_KT = "MO_PHONG_M0_KHO_A", "MO_PHONG_CFO_KHO_A", "MO_PHONG_KT_KHO_A"
M2_INST, M2_SCOPE = "DEMO_M2_XML_INSTANCE_A", "DEMO_M2_SCOPE_BOTH_COMPANIES_V1"
SPLIT_SCOPE, SPLIT_SO = "urn:demo:m5:scope:r16-split-six-v1", "NK20261019006"
REF = {"GOODS_EQ_A": "DEMO_M2_M5_GOODS_EQ_A_V1", "CAI_EQ_A": "DEMO_M2_M5_CAI_EQ_A_V1", "THUNG_ENCODING": "DEMO_R16_THUNG_NATIVE_ENCODING_V1",
       "THUNG_12_CAI": "DEMO_NEW_THUNG12CAI_PROOF_V1"}


def _pin(path: Path, sha: str) -> bytes:
    raw = path.read_bytes()
    assert sha256(raw) == sha, f"{path.name} khác pin"
    return raw


def g01_va_fact01() -> tuple[bytes, dict]:
    """G01 + ứng viên literal 01 của R15 — cùng pin với tests/test_m2_k2.py (manifest XML + line-facts), không đọc expected."""
    man = {f["path"]: f for f in json.loads(_pin(XMLFIX / "manifest.json", "43ad28257ca646b9d43f45ed34a8c441131328cca1b576cf247b378224e2b177")
                                             .decode("utf-8"))["files"]}
    rel = "inputs/G01-wrapped-positive.xml"
    facts = json.loads(_pin(BRIDGE / "line-facts.json", "2195792bef97a1c94773f7fbe3391192e0ed24e872dfd904ac90ed54ba3b41fd").decode("utf-8"))["rows"]
    return _pin(XMLFIX / rel, man[rel]["sha256"]), facts[0]


class ThuanL11(unittest.TestCase):
    def test_profile_va_fixture_dung_pin(self):
        self.assertEqual(nguon_chung.digest_payload(l11_demo.EVIDENCE_PROFILE_PAYLOAD), l11_demo.EVIDENCE_PROFILE_SHA256)
        for ma, ref in REF.items():
            ten, raw = l11_demo.mau_bang_chung(ma)
            cfg = next(r for r in l11_demo.EVIDENCE_PROFILE_PAYLOAD["proof_references"] if r["reference_id"] == ref)
            self.assertEqual((sha256(raw), len(raw)), (cfg["raw_sha256"], cfg["byte_length"]), ma)
        with self.assertRaises(DataError):
            l11_demo.mau_bang_chung("../manifest.json")
        with self.assertRaises(DataError):
            l11_demo.doc("upstream-manifest.json")  # không thuộc manifest đã pin → không đọc
        self.assertEqual(sorted(l11_demo.dang_nhap_l11()), sorted([LINK, PCFO]))

    def test_json_bang_chung_nghiem(self):
        doc = KhoSoLuongK2._doc_json_bang_chung
        self.assertIsNotNone(doc(b'{"a": "1"}')[0])
        for raw in (b'\xef\xbb\xbf{"a": "1"}', b'{"a": "1", "a": "2"}', b'{"a": 1.5}', b'{"a": NaN}', b'\xff'):
            with self.subTest(raw=raw):
                obj, loi = doc(raw)
                self.assertIsNone(obj)
                self.assertTrue(loi)

    def test_yeu_cau_khong_nhan_authority_va_so_chuoi(self):
        base = {"cau_noi_id": str(uuid.uuid4()), "dong_phien_ban_id": str(uuid.uuid4()), "so_luong_hoa_don": "4", "so_luong_phieu": "4"}
        self.assertEqual(lien_ket_chung.l11_yeu_cau("preview", base)["so_luong_phieu"], "4")
        for sua in ({"tu_so": "12"}, {"factor": 1}, {"kind": "CROSS_NATIVE_RATIO"}, {"PROVEN": True}, {"phap_nhan_id": str(uuid.uuid4())},
                    {"pool_id": str(uuid.uuid4())}, {"so_luong_pool_phieu": "4"}, {"trang_thai": "DA_KHOP"}, {"duong_dan": "x"}):
            with self.subTest(sua=sua):
                with self.assertRaises(DataError) as cm:
                    lien_ket_chung.l11_yeu_cau("preview", base | sua)
                self.assertEqual(cm.exception.code, "L11_CLIENT_AUTHORITY")
        for v in (4, 4.0, "1e2", "-1", "0", "0.0", " 4", "4.0000000000001", None, True):
            with self.subTest(v=v):
                with self.assertRaises(DataError) as cm:
                    lien_ket_chung.l11_yeu_cau("preview", base | {"so_luong_phieu": v})
                self.assertEqual(cm.exception.code, "L11_SO_LUONG_SAI")
        with self.assertRaises(DataError) as cm:
            lien_ket_chung.l11_yeu_cau("xac-nhan", {k: v for k, v in base.items() if k != "so_luong_phieu"})  # xác nhận bắt buộc đủ hai lượng
        self.assertEqual(cm.exception.code, "L11_SO_LUONG_SAI")
        with self.assertRaises(DataError) as cm:
            lien_ket_chung.l11_yeu_cau("preview", base | {"la": 1})
        self.assertEqual(cm.exception.code, "L11_YEU_CAU_SAI")
        self.assertEqual(lien_ket_chung.l11_yeu_cau("huy", {"child_id": "x", "expected_graph": "0" * 64, "khoa": "k", "ly_do": "r"}),
                         {"child_id": "x", "expected_graph": "0" * 64, "client_key": "k", "reason": "r"})


class _L11Nen:
    """Nền dùng chung (không phải TestCase): DB DEMO mới + seed thật + login app_web + kết nối chủ cấu hình; helpers nghiệp vụ qua service thật."""
    TIEN_TO_DB = "kho_test_l11_"

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.k2 import crm_demo, m2_demo
        from kho_tri_thuc.k2.crm_khoi_dong import kiem_ket_noi_chu
        from kho_tri_thuc.k2.hoa_don import HoaDonK2
        cls.db = cls.TIEN_TO_DB + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        crm_demo.khoi_tao(cls.admin)
        m5_demo.khoi_tao(cls.admin)
        m2_demo.khoi_tao(cls.admin)
        cls.quyen_cu = cls.quyen_snapshot()
        cls.seed1 = l11_demo.khoi_tao(cls.admin)
        cls.seed2 = l11_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_l11_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        opts = "-c lock_timeout=20000 -c statement_timeout=60000"
        cls.app = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row, options=opts)
        cls.chu = psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row, options=opts)
        kiem_ket_noi_chu(cls.chu, cls.app)
        cls.root = Path(tempfile.mkdtemp(prefix="ktt_l11_k2_"))
        cls.m5 = KhoSoLuongK2(cls.app, cls.root, conn_chu=cls.chu)
        cls.m2 = HoaDonK2(cls.app, cls.root, conn_chu=cls.chu)
        cls.state = {}

    @classmethod
    def tearDownClass(cls):
        for c in (cls.app, cls.chu, cls.admin):
            c.close()  # giữ DB/role/thư mục làm bằng chứng

    @classmethod
    def q(cls, sql, params=()):
        return cls.admin.execute(sql, params).fetchone()[0]

    @classmethod
    def quyen_snapshot(cls):
        return cls.q("""SELECT jsonb_build_object('pq', (SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id) FROM master.phan_quyen x),
                                                  'nl', (SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id) FROM master.nang_luc_nguon x))::text""")

    def dem(self) -> dict:
        q = self.q
        return {"ung_vien": q("SELECT count(*) FROM kho.bang_chung_ung_vien"), "bang_chung": q("SELECT count(*) FROM kho.bang_chung_quy_doi_luong"),
                "bang_chung_xn": q("SELECT count(*) FROM kho.bang_chung_quy_doi_luong WHERE trang_thai = 'DA_XAC_NHAN'"),
                "pool": q("SELECT count(*) FROM kho.dich_so_luong"), "ma_hoa": q("SELECT count(*) FROM kho.ma_hoa_luong_nguon"),
                "parent": q("SELECT count(*) FROM kho.lien_ket_chung_tu WHERE chu_so_huu_module = 'M5'"),
                "child": q("SELECT count(*) FROM kho.lien_ket_dong"),
                "child_state": q("""SELECT coalesce(jsonb_agg(jsonb_build_array(trang_thai, hieu_luc) ORDER BY id), '[]')::text FROM kho.lien_ket_dong"""),
                "bien_nhan_l11": q("SELECT count(*) FROM kho.bien_nhan_thao_tac WHERE operation LIKE 'L11_%%'"),
                "lo_l11": q("SELECT count(*) FROM kho.lo_xuat WHERE du_lieu->>'che_do' = 'L11_QUANTITY'"),
                "audit_l11": q("SELECT count(*) FROM nhat_ky.su_kien WHERE hanh_dong LIKE 'L11_%%' OR hanh_dong = 'XUAT_FILE_SOAT_L11'"),
                "core": q("SELECT count(*) FROM kho.chung_tu"), "stage": q("SELECT count(*) FROM giao_tiep.stage_tin_cay")}

    def raises(self, codes, fn):
        """Repair02: mã CHÍNH XÁC — DataError.code bằng mã, hoặc lỗi CSDL mở đầu bằng `MÃ:` (RAISE 'MÃ: …'); không chấp nhận chuỗi con rộng như `L11_`."""
        with self.assertRaises((DataError, psycopg.Error)) as ctx:
            fn()
        e = ctx.exception
        ma = getattr(e, "code", None) if isinstance(e, DataError) else (getattr(getattr(e, "diag", None), "message_primary", None) or str(e)).split(":", 1)[0].strip()
        self.assertIn(ma, (codes,) if isinstance(codes, str) else tuple(codes), str(e))

    def tu_choi_quyen(self, fn, *codes):
        """Từ chối ở tầng ACL/RLS (SQLSTATE 42501 insufficient_privilege, hoặc 42501-tương đương RLS) hoặc ĐÚNG một trong các mã trigger liệt kê."""
        with self.assertRaises(psycopg.Error) as ctx:
            fn()
        e = ctx.exception
        ma = (getattr(getattr(e, "diag", None), "message_primary", None) or str(e)).split(":", 1)[0].strip()
        self.assertTrue(getattr(e, "sqlstate", None) == "42501" or ma in codes, f"{getattr(e, 'sqlstate', None)} {e}")

    def sql(self, login, sql, params=()):
        nd = self.q("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s", (login,))
        with self.app.transaction():
            self.app.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (nd, login))
            cur = self.app.execute(sql, params)
            return cur.fetchall() if cur.description else cur.rowcount

    # ------------------------------------------------------------------ helpers nghiệp vụ (đường thật M2/M5)
    def hd(self, ky_hieu, so):
        return self.q("SELECT id::text FROM kho.hoa_don_danh_tinh WHERE ky_hieu = %s AND so_chuan = %s", (ky_hieu, so))

    def phieu(self, so):
        return self.q("SELECT id::text FROM kho.phieu_kho_danh_tinh WHERE source_instance_id = 'DEMO_KHO_A' AND so_phieu_key = %s", (so,))

    def m2_map_route(self, hd, ref, rev, logical, khoa):
        ct = self.m2.chi_tiet(M2_CFO, hd)
        row = ct["dong_nguon_hien_hanh"][0]["source_row_id"]
        self.m2.mapping_line(M2_CFO, client_key=f"ml-{khoa}", hoa_don_id=hd, expected_graph=ct["expected_graph"], source_row_id=row,
                             logical_line_key=logical, reason="DEMO L11 map", evidence_ref=ref, evidence_revision=rev)
        ct = self.m2.chi_tiet(M2_CFO, hd)
        self.m2.route(M2_CFO, {"hoa_don_id": hd, "cau_noi_id": ct["cau_noi"][0]["id"], "dich": "KHO", "expected_route_id": None,
                               "expected_graph": ct["expected_graph"], "ly_do": "DEMO L11 KHO", "khoa": f"rt-{khoa}"})
        return self.m2.chi_tiet(M2_CFO, hd)

    def m5_chap_nhan(self, pid, khoa):
        ct = self.m5.chi_tiet(M5_CFO, pid)["con_tro"]
        return self.m5.kiem_lai_nguon(M5_CFO, {"phieu_id": pid, "observation_id": ct["latest_observation_id"], "quyet_dinh": "CHAP_NHAN_NGUON",
                                               "accepted_truoc": ct["accepted_source_observation_id"], "eligible_truoc": ct["eligible_content_id"],
                                               "latest_truoc": ct["latest_observation_id"], "ly_do": "DEMO L11 review", "khoa": khoa})

    def ung_vien(self, ref, trang_thai="UNG_VIEN"):
        return next(u for u in self.m5.l11_bang_chung(PCFO)["ung_vien"] if u["reference_id"] == ref and u["trang_thai"] == trang_thai)

    def bang_chung(self, ref, actor=LINK):
        return next(b for b in self.m5.l11_bang_chung(actor)["bang_chung"] if b["reference_id"] == ref)

    def tq(self, actor=LINK):
        return self.m5.l11_tong_quan(actor)

    def token_ma_hoa(self, side, line_id):
        """Repair02 (root-cause test setup): token đồ thị mã hóa lấy NGUYÊN từ DTO công khai vừa đọc (`ma_hoa.expected_graph` của picker), không tự
        băm JSON phía chủ/nội bộ. Frozen01 tự hash master.json_chuan(g) trong khi SQL băm `{x}::text` → VERSION_CHANGED do test, không do sản phẩm."""
        tq = self.tq(PCFO)
        dong = (tq["dong_hoa_don"] if side == "M2" else tq["dong_phieu"])
        khoa = "cau_noi_id" if side == "M2" else "dong_phien_ban_id"
        return next(d for d in dong if d[khoa] == line_id)["ma_hoa"]["expected_graph"]

    def ma_hoa(self, side, line_id, proof_id=None, khoa=None):
        tok = self.token_ma_hoa(side, line_id)
        body = {"side": side, "line_id": line_id, "expected_graph": tok, "khoa": khoa or "enc-" + uuid.uuid4().hex[:10], "ly_do": "DEMO encode"}
        if proof_id:
            body["proof_id"] = proof_id
        return self.m5.l11_ma_hoa(PCFO, body)

    def cap(self, cau, dong, ei, ew, g, x, a, b):
        return {"cau_noi_id": cau, "dong_phien_ban_id": dong, "ma_hoa_hoa_don_id": ei, "ma_hoa_phieu_id": ew, "bang_chung_hang_id": g,
                "bang_chung_ty_le_id": x, "so_luong_hoa_don": a, "so_luong_phieu": b}

    def xac_nhan(self, body, khoa, actor=LINK):
        xt = self.m5.lien_ket(actor, "preview", body)
        return self.m5.lien_ket(actor, "xac-nhan", body | {"expected_graph": xt["expected_graph"], "khoa": khoa, "ly_do": "DEMO liên kết"})

    def nhan_bang_chung(self, ma, khoa):
        return self.m5.l11_nhan_bang_chung(PCFO, source_instance=l11_demo.EVIDENCE_INSTANCE, scope_ref=l11_demo.EVIDENCE_SCOPE, coverage="COMPLETE_INPUT",
                                           client_key=khoa, fixture_ref=ma)

    def duyet_bang_chung(self, ref, khoa):
        u = self.ung_vien(ref)
        return self.m5.l11_xac_nhan_bang_chung(PCFO, {"candidate_id": u["id"], "expected_graph": u["expected_graph"], "khoa": khoa, "ly_do": "DEMO CFO xác nhận"})

    def g01_k01(self):
        """Nguồn thật: G01 (nhận → CFO map → tuyến KHO) + K01 (nhận → CFO chấp nhận). Trả (cầu nối G01, dòng phiếu K01 #1, hóa đơn, phiếu)."""
        g01, f01 = g01_va_fact01()
        self.m2.nhan(M2_INTAKE, source_instance=M2_INST, scope_ref=M2_SCOPE, coverage="COMPLETE_INPUT", client_key="l11-g01", native=g01)
        hd = self.hd("DEMO_SERIES_A", "1")
        ct = self.m2_map_route(hd, f01["mapping_ref"], f01["revision"], f01["logical_line_key"], "g01")
        mm = m5_demo.mau("K01")
        scope = next(c for c in m5_demo.doc_registry()["configured_scopes"] if c["source_instance"] == mm["source_instance"])["scope_ref"]
        self.m5.nhan(M5_INTAKE, source_instance=mm["source_instance"], scope_ref=scope, coverage=mm["coverage"], reported_errors=mm["reported_errors"],
                     client_key="l11-k01", native=mm["native"], master=mm["master"])
        pk = self.phieu("NK20260814001")
        self.m5_chap_nhan(pk, "l11-k01-rv")
        dong = next(d for d in self.tq()["dong_phieu"] if d["phieu_id"] == pk and d["stt"] == 1)
        return ct["cau_noi"][0]["id"], dong, hd, pk


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PostgreSQL L11 không chạy (không tính đạt)")
class L11K2Pg(_L11Nen, unittest.TestCase):
    """Các test chạy theo thứ tự tên (t00…t11) trên MỘT DB; trạng thái truyền qua cls.state."""

    # ------------------------------------------------------------------ seed
    def test_t00_seed_mot_lan_khong_regrant(self):
        s1 = {k: v for k, v in self.seed1.items() if k != "mo_lai_giu_quyen_hien_hanh"}
        self.assertEqual((s1["instance"], s1["profile"], s1["pham_vi"], s1["tai_lieu"], s1["don_vi"], s1["ung_vien_dong"], s1["actor"]),
                         (1, 1, 1, 2, 2, 1, 2))
        self.assertEqual({k: v for k, v in self.seed2.items() if k != "mo_lai_giu_quyen_hien_hanh"}, {k: 0 for k in s1})
        self.assertTrue(self.seed2["mo_lai_giu_quyen_hien_hanh"])
        # không seed approval/pool/mã hóa/child; actor cũ không đổi quyền/năng lực
        self.assertEqual({k: self.dem()[k] for k in ("ung_vien", "bang_chung", "pool", "ma_hoa", "parent", "child")}, {k: 0 for k in
                         ("ung_vien", "bang_chung", "pool", "ma_hoa", "parent", "child")})
        cu = json.loads(self.quyen_cu)
        moi = json.loads(self.quyen_snapshot())
        ids_l11 = {r[0] for r in self.admin.execute("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = ANY(%s)", (l11_demo.dang_nhap_l11(),))}
        self.assertEqual([r for r in moi["pq"] if r["nguoi_dung_id"] not in ids_l11], cu["pq"])
        self.assertEqual([r for r in (moi["nl"] or []) if r["nguoi_dung_id"] not in ids_l11], cu["nl"] or [])
        self.assertEqual(self.q("""SELECT count(*) FROM master.nang_luc_nguon n JOIN master.nguoi_dung u ON u.id = n.nguoi_dung_id
                                   WHERE u.dang_nhap = %s AND n.source_instance_id <> %s""", (PCFO, l11_demo.EVIDENCE_INSTANCE)), 0)

    # ------------------------------------------------------------------ Q00 bằng chứng: raw candidate → CFO BOTH V4
    def test_t01_q00_nhan_va_xac_nhan_bang_chung(self):
        tham = dict(source_instance=l11_demo.EVIDENCE_INSTANCE, scope_ref=l11_demo.EVIDENCE_SCOPE, coverage="COMPLETE_INPUT")
        truoc = self.dem()
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.m5.l11_nhan_bang_chung(LINK, **tham, client_key="pf-x", fixture_ref="GOODS_EQ_A"))
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.m5.l11_nhan_bang_chung(M5_INTAKE, **tham, client_key="pf-y", fixture_ref="GOODS_EQ_A"))
        self.raises("L11_MAU", lambda: self.m5.l11_nhan_bang_chung(PCFO, **tham, client_key="pf-z", fixture_ref="../x"))
        self.assertEqual(self.dem(), truoc)
        for ma in REF:
            r = self.m5.l11_nhan_bang_chung(PCFO, **tham, client_key=f"pf-{ma.lower()}", fixture_ref=ma)
            self.assertEqual((r["lap_lai"], r["tham_chieu_cau_hinh"], r["promote"]["module"], r["promote"]["trang_thai_ung_vien"]),
                             (False, REF[ma], "L11", "UNG_VIEN"), ma)
        lai = self.m5.l11_nhan_bang_chung(PCFO, **tham, client_key="pf-goods_eq_a", fixture_ref="GOODS_EQ_A")
        self.assertTrue(lai["lap_lai"])
        self.raises("CAPTURE_KHAC_NOI_DUNG", lambda: self.m5.l11_nhan_bang_chung(PCFO, **tham, client_key="pf-goods_eq_a", fixture_ref="CAI_EQ_A"))
        # bytes không cấu hình → HOLD (giữ raw, không phải approval); JSON float → HOLD
        r = self.m5.l11_nhan_bang_chung(PCFO, **tham, client_key="pf-la", native=b'{"reference_id": "X", "evidence_revision": 1, "pn_ma": "PN_DEMO_A"}')
        self.assertEqual(r["promote"]["trang_thai_ung_vien"], "HOLD")
        self.assertIn("L11_BANG_CHUNG_KHONG_CAU_HINH", r["promote"]["issues"])
        self.assertEqual(self.dem()["bang_chung"], 0)  # nhận ≠ duyệt
        # raw candidate chỉ thấy với READ_SOURCE nguồn bằng chứng (LINK có BOTH READ nhưng không READ_SOURCE)
        self.assertEqual(self.m5.l11_bang_chung(LINK)["ung_vien"], [])
        self.assertEqual(self.sql(LINK, "SELECT count(*) AS n FROM kho.bang_chung_quy_doi_luong")[0]["n"], 0)
        self.tu_choi_quyen(lambda: self.sql(PCFO, "SELECT count(*) FROM kho.bang_chung_ung_vien"))
        # R3 repair02: CÙNG bytes cấu hình nhưng claim PARTIAL_INPUT / UNKNOWN / có lỗi báo → raw giữ, ứng viên HOLD (không coi là đầy đủ); claim gốc vào H
        for i, (cov, loi, ma) in enumerate((("PARTIAL_INPUT", [], "L11_COVERAGE_PARTIAL_INPUT"), ("UNKNOWN", [], "L11_COVERAGE_UNKNOWN"),
                                            ("COMPLETE_INPUT", ["DEMO_LOI_NGUON"], "L11_LOI_BAO_CAO_NGUON"))):
            with self.subTest(coverage=cov, loi=loi):
                r = self.m5.l11_nhan_bang_chung(PCFO, source_instance=l11_demo.EVIDENCE_INSTANCE, scope_ref=l11_demo.EVIDENCE_SCOPE, coverage=cov,
                                                reported_errors=loi, client_key=f"pf-hold-{i}", fixture_ref="GOODS_EQ_A")
                self.assertEqual((r["promote"]["trang_thai_ung_vien"], r["tham_chieu_cau_hinh"]), ("HOLD", REF["GOODS_EQ_A"]))
                self.assertIn(ma, r["promote"]["issues"])
                self.raises("CAPTURE_KHAC_NOI_DUNG", lambda: self.m5.l11_nhan_bang_chung(
                    PCFO, source_instance=l11_demo.EVIDENCE_INSTANCE, scope_ref=l11_demo.EVIDENCE_SCOPE, coverage="COMPLETE_INPUT", reported_errors=[],
                    client_key=f"pf-hold-{i}", fixture_ref="GOODS_EQ_A"))  # cùng khóa đổi claim → 409, không blob/stage mới
        hold_goods = [u for u in self.m5.l11_bang_chung(PCFO)["ung_vien"] if u["reference_id"] == REF["GOODS_EQ_A"] and u["trang_thai"] == "HOLD"]
        self.assertEqual(len(hold_goods), 3)
        self.raises("L11_BANG_CHUNG_HOLD", lambda: self.m5.l11_xac_nhan_bang_chung(PCFO, {"candidate_id": hold_goods[0]["id"],
                                                                                            "expected_graph": hold_goods[0]["expected_graph"],
                                                                                            "khoa": "pc-hold-cov", "ly_do": "x"}))
        self.assertEqual(self.dem()["bang_chung"], 0)
        # không đúng quyền xác nhận: LINK (V2), CFO M5-only, CFO M2-only; HOLD không xác nhận được
        u = self.ung_vien(REF["GOODS_EQ_A"])
        body = {"candidate_id": u["id"], "expected_graph": u["expected_graph"], "khoa": "pc-goods", "ly_do": "DEMO CFO xác nhận"}
        for actor in (LINK, M5_CFO, M2_CFO):
            with self.subTest(actor=actor):
                self.raises("KHONG_CO_QUYEN_L11_BANG_CHUNG", lambda: self.m5.l11_xac_nhan_bang_chung(actor, body))
        self.raises("L11_CLIENT_AUTHORITY", lambda: self.m5.l11_xac_nhan_bang_chung(PCFO, body | {"PROVEN": True}))
        self.raises("L11_CLIENT_AUTHORITY", lambda: self.m5.l11_xac_nhan_bang_chung(PCFO, body | {"tu_so": "12"}))
        self.raises("L11_VERSION_CHANGED", lambda: self.m5.l11_xac_nhan_bang_chung(PCFO, body | {"expected_graph": "0" * 64}))
        hold = next(x for x in self.m5.l11_bang_chung(PCFO)["ung_vien"] if x["trang_thai"] == "HOLD" and x["reference_id"] is None)
        self.raises("L11_BANG_CHUNG_HOLD", lambda: self.m5.l11_xac_nhan_bang_chung(PCFO, {"candidate_id": hold["id"], "expected_graph": hold["expected_graph"],
                                                                                            "khoa": "pc-hold", "ly_do": "x"}))
        # tỷ lệ trước bằng chứng hàng → từ chối (phụ thuộc hàng hóa đã xác nhận)
        uc = self.ung_vien(REF["CAI_EQ_A"])
        self.raises("L11_THIEU_BANG_CHUNG_HANG", lambda: self.m5.l11_xac_nhan_bang_chung(PCFO, {"candidate_id": uc["id"], "expected_graph": uc["expected_graph"],
                                                                                                  "khoa": "pc-cai-som", "ly_do": "x"}))
        self.assertEqual(self.dem()["bang_chung"], 0)
        # dương: thứ tự GOODS → CAI 1/1 → THUNG encoding → THUNG 12/1; token đọc lại trước MỖI lần (đồ thị PN đổi)
        ids = {}
        for ma in ("GOODS_EQ_A", "CAI_EQ_A", "THUNG_ENCODING", "THUNG_12_CAI"):
            if ma == "THUNG_ENCODING":
                # repair03 (C): mã hóa native chỉ duyệt khi NGUỒN THẬT đã capture — trước capture → đúng L11_HO_TRO_CHUA_CAPTURE, 0 bằng chứng mới;
                # rồi capture THUNG qua service nguồn M2 thật (không owner INSERT, không seed approval) và duyệt lại dương
                ut = self.ung_vien(REF[ma])
                truoc_bc = self.dem()["bang_chung"]
                self.raises("L11_HO_TRO_CHUA_CAPTURE", lambda: self.m5.l11_xac_nhan_bang_chung(
                    PCFO, {"candidate_id": ut["id"], "expected_graph": ut["expected_graph"], "khoa": "pc-thung-som", "ly_do": "trước capture"}))
                self.assertEqual(self.dem()["bang_chung"], truoc_bc)
                _, xml = l11_demo.mau_nguon("THUNG_XML")
                self.m2.nhan(M2_INTAKE, source_instance=M2_INST, scope_ref=M2_SCOPE, coverage="COMPLETE_INPUT", client_key="l11-thung", native=xml)
            u = self.ung_vien(REF[ma])
            r = self.m5.l11_xac_nhan_bang_chung(PCFO, {"candidate_id": u["id"], "expected_graph": u["expected_graph"], "khoa": f"pc-{ma.lower()}",
                                                       "ly_do": "DEMO CFO xác nhận"})
            self.assertFalse(r["lap_lai"], ma)
            ids[ma] = r["bang_chung_id"]
            lai = self.m5.l11_xac_nhan_bang_chung(PCFO, {"candidate_id": u["id"], "expected_graph": u["expected_graph"], "khoa": f"pc-{ma.lower()}",
                                                         "ly_do": "DEMO CFO xác nhận"})
            self.assertTrue(lai["lap_lai"])
        bc = {b["reference_id"]: b for b in self.m5.l11_bang_chung(LINK)["bang_chung"]}
        self.assertEqual((bc[REF["CAI_EQ_A"]]["tu_so"], bc[REF["CAI_EQ_A"]]["mau_so"]), ("1", "1"))
        self.assertEqual((bc[REF["THUNG_12_CAI"]]["tu_so"], bc[REF["THUNG_12_CAI"]]["mau_so"]), ("12", "1"))
        self.assertEqual({b["trang_thai"] for b in bc.values()}, {"DA_XAC_NHAN"})
        self.assertEqual(bc[REF["THUNG_ENCODING"]]["native_byte_length"], 480)  # tuple độ dài thật lưu bất biến cùng bằng chứng
        self.assertEqual(self.dem()["bang_chung_xn"], 4)
        self.state["proof"] = ids

    # ------------------------------------------------------------------ Q01/Q02 G01 (10 CAI) ↔ K01 dòng 1 (8 CAI)
    def test_t02_q01_nguon_that_va_ma_hoa(self):
        cau, dong, hd, pk = self.g01_k01()
        self.assertEqual((dong["so_luong_raw"], dong["hien_hanh"], dong["source_ordinal"]), ("8", True, 0))  # source_ordinal gốc của reader = /lines/0
        truoc = self.dem()
        self.raises("KHONG_CO_QUYEN_L11_MA_HOA", lambda: self.m5.l11_ma_hoa(LINK, {"side": "M2", "line_id": cau, "expected_graph": "0" * 64,
                                                                                   "khoa": "enc-link", "ly_do": "x"}))
        self.raises("L11_MA_HOA_KHONG_CAN_BANG_CHUNG", lambda: self.ma_hoa("M2", cau, self.state["proof"]["THUNG_ENCODING"]))
        self.assertEqual(self.dem(), truoc)
        ei = self.ma_hoa("M2", cau, khoa="enc-g01")
        ew = self.ma_hoa("M5", dong["dong_phien_ban_id"], khoa="enc-k01")
        self.assertEqual((ei["so_luong_nguon"], ei["suc_chua"], ei["can_cu"], ei["tu_so"], ei["mau_so"]), ("10", "10", "SAME_VERIFIED_DEFINITION", "1", "1"))
        self.assertEqual((ew["so_luong_nguon"], ew["suc_chua"], ew["can_cu"]), ("8", "8", "SAME_VERIFIED_DEFINITION"))
        self.raises("L11_MA_HOA_DA_CO", lambda: self.ma_hoa("M2", cau, khoa="enc-g01-2"))  # cùng căn cứ lần hai → từ chối, không revision mới
        self.assertEqual(self.dem()["pool"], 2)
        self.state.update(hd=hd, cau=cau, pk=pk, dong=dong["dong_phien_ban_id"], ei=ei["ma_hoa_id"], ew=ew["ma_hoa_id"], pool_hd=ei["pool_id"],
                          pool_pk=ew["pool_id"])

    def test_t03_q01_q02_hai_lan_4_4_mot_parent(self):
        s, pf = self.state, self.state["proof"]
        body = self.cap(s["cau"], s["dong"], s["ei"], s["ew"], pf["GOODS_EQ_A"], pf["CAI_EQ_A"], "4", "4")
        xt = self.m5.lien_ket(LINK, "preview", body)
        self.assertEqual((xt["blockers"], xt["ghi"], xt["duoc_xac_nhan"]), ([], 0, True))
        self.assertEqual(xt["so_luong"], {"hoa_don_nguon": "4", "phieu_nguon": "4", "pool_hoa_don": "4", "pool_phieu": "4"})
        self.assertEqual((xt["ngan_sach"]["hoa_don"]["con_lai"], xt["ngan_sach"]["phieu"]["con_lai"]), ("10", "8"))
        truoc = self.dem()
        self.m5.lien_ket(LINK, "preview", body)
        self.assertEqual(self.dem(), truoc)  # preview 0 ghi
        r1 = self.m5.lien_ket(LINK, "xac-nhan", body | {"expected_graph": xt["expected_graph"], "khoa": "lk-1", "ly_do": "DEMO 4/4 lần 1"})
        self.assertEqual((r1["trang_thai"], r1["hieu_luc"], r1["lap_lai"]), ("DA_KHOP", "CO_HIEU_LUC", False))
        self.raises("L11_VERSION_CHANGED", lambda: self.m5.lien_ket(LINK, "xac-nhan", body | {"expected_graph": xt["expected_graph"], "khoa": "lk-cu",
                                                                                              "ly_do": "token cũ"}))
        r2 = self.xac_nhan(body, "lk-2")
        self.assertEqual(r1["lien_ket_id"], r2["lien_ket_id"])
        self.assertNotEqual(r1["child_id"], r2["child_id"])
        d = self.dem()
        self.assertEqual((d["parent"], d["child"]), (1, 2))
        p = self.admin.execute("""SELECT loai, chu_so_huu_module, muc_dich_lien_ket, so_tien_khop_minor, trang_thai FROM kho.lien_ket_chung_tu
                                  WHERE id = %s""", (r1["lien_ket_id"],)).fetchone()
        self.assertEqual(tuple(p), ("HD_PHIEU_KHO", "M5", "EVIDENCE", None, "DA_KHOP"))
        nh = self.m5.lien_ket(LINK, "preview", body)["ngan_sach"]
        self.assertEqual((nh["hoa_don"]["con_lai"], nh["phieu"]["con_lai"], nh["hoa_don"]["da_xac_nhan"], nh["phieu"]["dang_giu"]), ("2", "0", "8", "0"))
        # replay khóa 1 nguyên body → cùng child (trạng thái hiện hành), 0 delta; khác body cùng khóa → 409
        truoc = self.dem()
        lai = self.m5.lien_ket(LINK, "xac-nhan", body | {"expected_graph": xt["expected_graph"], "khoa": "lk-1", "ly_do": "DEMO 4/4 lần 1"})
        self.assertEqual((lai["child_id"], lai["lap_lai"]), (r1["child_id"], True))
        self.raises("IDEMPOTENCY_KHAC", lambda: self.m5.lien_ket(LINK, "xac-nhan", body | {"expected_graph": xt["expected_graph"], "khoa": "lk-1",
                                                                                           "ly_do": "khác"}))
        # vượt pool phiếu (8 đã dùng) dù hóa đơn còn 2 → chặn, 0 delta
        b11 = body | {"so_luong_hoa_don": "1", "so_luong_phieu": "1"}
        x11 = self.m5.lien_ket(LINK, "preview", b11)
        self.assertIn("L11_VUOT_SO_LUONG_PHIEU", x11["blockers"])
        self.assertNotIn("L11_VUOT_SO_LUONG_HOA_DON", x11["blockers"])
        self.raises("L11_VUOT_SO_LUONG_PHIEU", lambda: self.m5.lien_ket(LINK, "xac-nhan", b11 | {"expected_graph": x11["expected_graph"], "khoa": "lk-vuot",
                                                                                                  "ly_do": "vượt"}))
        self.assertEqual(self.dem(), truoc)
        self.state.update(c1=r1["child_id"], c2=r2["child_id"], lk=r1["lien_ket_id"], body=body, xt1=xt["expected_graph"])

    # ------------------------------------------------------------------ Q05 A,A: nhận lại ĐÚNG nội dung (khóa mới) → chỉ quan sát/CAS, KHÔNG giữ soát
    def test_t03b_q05_aa_khong_giu_soat(self):
        s = self.state
        trang_thai = lambda: self.admin.execute("SELECT id::text, trang_thai, hieu_luc FROM kho.lien_ket_dong ORDER BY id").fetchall()  # noqa: E731
        truoc = trang_thai()
        self.assertEqual({(r[1], r[2]) for r in truoc}, {("DA_KHOP", "CO_HIEU_LUC")})
        g01, _ = g01_va_fact01()
        self.m2.nhan(M2_INTAKE, source_instance=M2_INST, scope_ref=M2_SCOPE, coverage="COMPLETE_INPUT", client_key="l11-g01-aa", native=g01)
        cls_moi = self.q("""SELECT classification::text FROM kho.hoa_don_quan_sat WHERE hoa_don_id = %s ORDER BY thu_tu DESC LIMIT 1""", (s["hd"],))
        self.assertIn("SAME_CONTENT_REPEAT", cls_moi)
        mm = m5_demo.mau("K01")
        scope = next(c for c in m5_demo.doc_registry()["configured_scopes"] if c["source_instance"] == mm["source_instance"])["scope_ref"]
        self.m5.nhan(M5_INTAKE, source_instance=mm["source_instance"], scope_ref=scope, coverage=mm["coverage"], reported_errors=mm["reported_errors"],
                     client_key="l11-k01-aa", native=mm["native"], master=mm["master"])
        self.assertEqual(trang_thai(), truoc)  # cùng nội dung: eligible/child giữ nguyên, không CAN_SOAT
        nh = self.m5.lien_ket(LINK, "preview", s["body"] | {"so_luong_hoa_don": "1", "so_luong_phieu": "1"})["ngan_sach"]
        self.assertEqual((nh["hoa_don"]["con_lai"], nh["phieu"]["con_lai"]), ("2", "0"))
        # A→B→A (nội dung khác rồi trở lại) cần biến thể nội dung có liên kết sống của cùng hóa đơn/phiếu — chưa có fixture: UNRUN/chưa viết

    # ------------------------------------------------------------------ Q06 forgery SQL / đồ thị typed
    def test_t04_q06_forgery_va_do_thi(self):
        s, pf = self.state, self.state["proof"]
        truoc = self.dem()
        for sql, params in (("INSERT INTO kho.lien_ket_dong (id, phap_nhan_id, lien_ket_id) SELECT gen_random_uuid(), phap_nhan_id, id FROM kho.lien_ket_chung_tu "
                             "WHERE id = %s", (s["lk"],)),
                            ("UPDATE kho.lien_ket_dong SET trang_thai = 'HUY' WHERE id = %s", (s["c1"],)),
                            ("INSERT INTO kho.dich_so_luong (phap_nhan_id, owner_module, pool_kind) SELECT phap_nhan_id, 'M2', 'L11' FROM kho.lien_ket_chung_tu "
                             "WHERE id = %s", (s["lk"],)),
                            ("UPDATE kho.bang_chung_quy_doi_luong SET tu_so = 2 WHERE id = %s", (pf["CAI_EQ_A"],)),
                            ("SELECT kho.l11_can_soat_noi_bo(ARRAY[%s::uuid], 'X')", (s["c1"],)),
                            ("SELECT kho.l11_khoa_goc_noi_bo(NULL, NULL)", ()),
                            ("INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor) "
                             "SELECT phap_nhan_id, 'M5', 'L11_CONFIRM', 'forge', %s, '{}'::jsonb, 'x' FROM kho.lien_ket_chung_tu WHERE id = %s",
                             ("0" * 64, s["lk"]))):
            with self.subTest(sql=sql[:60]):
                self.tu_choi_quyen(lambda: self.sql(LINK, sql, params), "BIEN_NHAN_M5_CHI_CHU", "BIEN_NHAN_KHONG_CO_QUYEN")
        # repair03 (D): app UPDATE parent L11 (app có quyền UPDATE + RLS BOTH thấy hàng) → đúng P0001 L11_CHA_BAT_BIEN cho RIÊNG thao tác này
        self.raises("L11_CHA_BAT_BIEN", lambda: self.sql(LINK, "UPDATE kho.lien_ket_chung_tu SET trang_thai = 'HUY' WHERE id = %s", (s["lk"],)))
        # chủ bảng cũng không sửa child/parent L11 (bất biến), không trỏ liên kết chung vào core M2/M5
        self.raises("L11_CHA_BAT_BIEN", lambda: self.admin.execute("UPDATE kho.lien_ket_chung_tu SET trang_thai = 'HUY' WHERE id = %s", (s["lk"],)))
        self.raises("L11_BAT_BIEN", lambda: self.admin.execute("UPDATE kho.lien_ket_dong SET so_luong_pool_phieu = 1 WHERE id = %s", (s["c1"],)))
        # R1 repair02: ghi nguồn trực tiếp (chủ bảng, bỏ giao thức closure) làm đổi eligible của gốc có child sống → trigger KIỂM khóa gốc → từ chối
        self.raises("L11_KHOA_GOC_THIEU", lambda: self.admin.execute(
            "UPDATE kho.hoa_don_danh_tinh SET eligible_content_id = NULL WHERE id = %s", (s["hd"],)))
        a, b = self.admin.execute("SELECT chung_tu_a_id, chung_tu_b_id FROM kho.lien_ket_chung_tu WHERE id = %s", (s["lk"],)).fetchone()
        self.raises("L11_LIEN_KET_CHUNG_GIA", lambda: self.admin.execute(
            "INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai) SELECT phap_nhan_id, %s, %s, 'KHAC' FROM kho.lien_ket_chung_tu "
            "WHERE id = %s", (a, b, s["lk"])))
        # cặp sai: dòng phiếu K01 dòng 2 với mã hóa dòng 1; bằng chứng tỷ lệ dùng làm bằng chứng hàng; ID ngẫu nhiên
        dong2 = next(d for d in self.tq()["dong_phieu"] if d["phieu_id"] == s["pk"] and d["stt"] == 2)["dong_phien_ban_id"]
        for sua, ma in (({"dong_phien_ban_id": dong2}, "L11_MA_HOA_PHIEU_KHONG_HIEN_HANH"),
                        ({"bang_chung_hang_id": pf["CAI_EQ_A"]}, "L11_BANG_CHUNG_HANG_THIEU"),
                        ({"bang_chung_ty_le_id": pf["THUNG_12_CAI"]}, "L11_TY_LE_DON_VI_KHAC"),
                        ({"ma_hoa_hoa_don_id": s["ew"]}, "L11_MA_HOA_HOA_DON_KHONG_HIEN_HANH")):
            with self.subTest(ma=ma):
                xt = self.m5.lien_ket(LINK, "preview", s["body"] | {"so_luong_hoa_don": "1", "so_luong_phieu": "1"} | sua)
                self.assertIn(ma, xt["blockers"])
        self.raises("KHONG_CO_QUYEN_L11_XEM", lambda: self.m5.lien_ket(LINK, "preview", s["body"] | {"cau_noi_id": str(uuid.uuid4())}))
        self.assertEqual(self.dem(), truoc)

    def test_t04b_q06_peer_pn_khong_lo(self):
        """R3 repair02: cặp A-invoice ↔ B-warehouse (PN_B riêng tư) bị từ chối TRƯỚC mọi projection — lỗi không chứa sentinel PN_B; dương samePN ở t03."""
        s = self.state
        mm = m5_demo.mau("K02")
        scope = next(c for c in m5_demo.doc_registry()["configured_scopes"] if c["source_instance"] == mm["source_instance"])["scope_ref"]
        self.m5.nhan("MO_PHONG_M0_KHO_B", source_instance=mm["source_instance"], scope_ref=scope, coverage=mm["coverage"],
                     reported_errors=mm["reported_errors"], client_key="l11-k02-b", native=mm["native"], master=mm["master"])
        b = self.admin.execute("""SELECT lw.id::text, d.so_phieu_key, d.id::text, dd.id_dong_nguon, lw.so_luong_raw FROM kho.phieu_kho_dong_phien_ban lw
                                  JOIN kho.phieu_kho_danh_tinh d ON d.id = lw.phieu_id JOIN kho.phieu_kho_dong_danh_tinh dd ON dd.id = lw.dong_id
                                  JOIN master.phap_nhan p ON p.id = d.phap_nhan_id WHERE p.ma = 'PN_DEMO_B' ORDER BY lw.stt LIMIT 1""").fetchone()
        self.assertIsNotNone(b)  # setup thật phải có dòng PN_B (lỗi setup không được tính là từ chối đạt)
        truoc = self.dem()
        body = s["body"] | {"dong_phien_ban_id": b[0], "so_luong_hoa_don": "1", "so_luong_phieu": "1"}
        with self.assertRaises((DataError, psycopg.Error)) as cm:
            self.m5.lien_ket(LINK, "preview", body)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith("KHONG_CO_QUYEN_L11_XEM"), msg)
        for sentinel in (b[0], b[1], b[2], b[3], "PN_DEMO_B", "DEMO_KHO_B"):
            self.assertNotIn(sentinel, msg)
        self.raises("L11_CAP_KHAC_PHAP_NHAN", lambda: self.m5.lien_ket(LINK, "xac-nhan", body | {"expected_graph": "0" * 64, "khoa": "lk-pnb", "ly_do": "x"}))
        self.assertEqual(self.dem(), truoc)

    # ------------------------------------------------------------------ Q07 quyền hiện hành
    def test_t05_q07_quyen_hien_hanh(self):
        s = self.state
        truoc = self.dem()
        for actor in (M5_CFO, M5_KT, M2_CFO):  # M5-only / M2-only
            with self.subTest(actor=actor):
                self.raises("KHONG_CO_QUYEN_L11_XEM", lambda: self.m5.lien_ket(actor, "preview", s["body"]))
                self.raises("KHONG_CO_QUYEN_MODULE", lambda: self.m5.l11_tong_quan(actor))
                self.assertEqual((self.m5.l11_trang(actor)["dong_hoa_don"], self.m5.l11_trang(actor)["bang_chung"]), ([], []))
                self.assertEqual(self.sql(actor, "SELECT count(*) AS n FROM kho.lien_ket_dong")[0]["n"], 0)  # RLS BOTH READ
                self.assertEqual(self.sql(actor, "SELECT count(*) AS n FROM kho.lien_ket_chung_tu WHERE chu_so_huu_module IS NOT NULL")[0]["n"], 0)
                self.assertIsNone(self.sql(actor, "SELECT kho.luong_con_lai(%s::uuid) AS v", (s["pool_hd"],))[0]["v"])
        self.raises("KHONG_CO_QUYEN_L11_LIEN_KET", lambda: self.xac_nhan(s["body"] | {"so_luong_hoa_don": "1", "so_luong_phieu": "1"}, "lk-cfo", PCFO))
        # thu hồi M2 của LINK → replay khóa cũ bị chặn TRƯỚC tra biên nhận; trả quyền (UPDATE, không DELETE) → replay lại dương
        nd = self.q("SELECT id FROM master.nguoi_dung WHERE dang_nhap = %s", (LINK,))
        self.admin.execute("UPDATE master.phan_quyen SET module = ARRAY['M5'] WHERE nguoi_dung_id = %s", (nd,))
        self.raises("KHONG_CO_QUYEN_L11_LIEN_KET", lambda: self.m5.lien_ket(LINK, "xac-nhan", s["body"] | {"expected_graph": s["xt1"], "khoa": "lk-1",
                                                                                                             "ly_do": "DEMO 4/4 lần 1"}))
        self.admin.execute("UPDATE master.phan_quyen SET module = ARRAY['M2','M5'] WHERE nguoi_dung_id = %s", (nd,))
        lai = self.m5.lien_ket(LINK, "xac-nhan", s["body"] | {"expected_graph": s["xt1"], "khoa": "lk-1", "ly_do": "DEMO 4/4 lần 1"})
        self.assertEqual((lai["child_id"], lai["lap_lai"]), (s["c1"], True))
        self.assertEqual(self.dem(), truoc)

    # ------------------------------------------------------------------ Q08 FILE L11_QUANTITY
    def test_t06_q08_file_l11(self):
        s = self.state
        lk = next(x for x in self.tq()["lien_ket"] if x["id"] == s["lk"])
        self.assertTrue(lk["co_so"]["duoc_file"])
        self.raises("L11_FILE_KHONG_CO", lambda: self.m5.l11_xuat_file(M5_KT, {"lien_ket_id": s["lk"], "co_so_truoc": lk["co_so"]["co_so_sha256"],
                                                                                "khoa": "f-kt", "ly_do": "x"}))
        self.raises("L11_VERSION_CHANGED", lambda: self.m5.l11_xuat_file(LINK, {"lien_ket_id": s["lk"], "co_so_truoc": "0" * 64, "khoa": "f-cu", "ly_do": "x"}))
        body = {"lien_ket_id": s["lk"], "co_so_truoc": lk["co_so"]["co_so_sha256"], "khoa": "f-1", "ly_do": "DEMO file L11"}
        r = self.m5.l11_xuat_file(LINK, body)
        self.assertEqual((r["che_do"], r["lap_lai"]), ("L11_QUANTITY", False))
        lai = self.m5.l11_xuat_file(LINK, body)
        self.assertEqual((lai["id"], lai["sha256"], lai["lap_lai"]), (r["id"], r["sha256"], True))
        ten, raw = self.m5.tep_file_soat(LINK, r["id"])
        self.assertEqual((sha256(raw), len(raw)), (r["sha256"], r["byte_length"]))
        # cells thật của workbook: không công thức, có lượng exact dạng chữ + định nghĩa đơn vị native (không đọc theo đường dẫn ngoài m5-xuat)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            xml = b"".join(z.read(n) for n in z.namelist() if n.startswith("xl/"))
        self.assertNotIn(b"<f>", xml)
        for chuoi in (b"DONG_SO_LUONG", b"NGAN_SACH_POOL", b"dinh_nghia_don_vi_native_hoa_don", b"DEMO_UNIT_CAI_A"):
            self.assertIn(chuoi, xml)
        self.raises("FILE_SOAT", lambda: self.m5.tep_file_soat(M5_KT, r["id"]))  # M5 FILE không M2_READ: RLS lô chéo ẩn, cùng từ chối như ngoài quyền
        self.raises("FILE_SOAT", lambda: self.m5.tep_file_soat(M2_CFO, r["id"]))
        self.state["lo"] = r["id"]

    # ------------------------------------------------------------------ Q03 THUNG: hóa đơn 1 THUNG ↔ phiếu tách sáu (6 CAI ×2), tỷ lệ 12/1
    def test_t07_q03_thung_exact(self):
        pf = self.state["proof"]
        _, xml = l11_demo.mau_nguon("THUNG_XML")
        self.m2.nhan(M2_INTAKE, source_instance=M2_INST, scope_ref=M2_SCOPE, coverage="COMPLETE_INPUT", client_key="l11-thung", native=xml)
        hd = self.hd("DEMO_SERIES_R16", "9001")
        ct = self.m2_map_route(hd, "DEMO_M2_LITERAL_LINE_FACT_R16_THUNG_A_V1", 1, "DEMO_LINE_R16_THUNG_A", "thung")
        cau = ct["cau_noi"][0]["id"]
        _, nat = l11_demo.mau_nguon("SPLIT_NATIVE")
        _, mst = l11_demo.mau_nguon("SPLIT_MASTER")
        mm = m5_demo.mau("K01")
        self.m5.nhan(M5_INTAKE, source_instance="DEMO_KHO_A", scope_ref=SPLIT_SCOPE, coverage=mm["coverage"], reported_errors=[], client_key="l11-split",
                     native=nat, master=mst)
        pk = self.phieu(SPLIT_SO)
        self.m5_chap_nhan(pk, "l11-split-rv")
        dongs = sorted((d for d in self.tq()["dong_phieu"] if d["phieu_id"] == pk), key=lambda d: d["stt"])
        self.assertEqual([d["so_luong_raw"] for d in dongs], ["6", "6"])
        self.raises("L11_THIEU_BANG_CHUNG_MA_HOA", lambda: self.ma_hoa("M2", cau))  # THUNG không có định nghĩa xác minh → cần bằng chứng mã hóa
        self.raises("L11_THIEU_BANG_CHUNG_MA_HOA", lambda: self.ma_hoa("M2", cau, pf["GOODS_EQ_A"]))  # bằng chứng hàng không phải mã hóa native
        ei = self.ma_hoa("M2", cau, pf["THUNG_ENCODING"], khoa="enc-thung")
        self.assertEqual((ei["so_luong_nguon"], ei["suc_chua"], ei["can_cu"]), ("1", "1", "APPROVED_NATIVE_ENCODING"))
        ew = [self.ma_hoa("M5", d["dong_phien_ban_id"], khoa=f"enc-split-{d['stt']}") for d in dongs]
        sai = self.cap(cau, dongs[0]["dong_phien_ban_id"], ei["ma_hoa_id"], ew[0]["ma_hoa_id"], pf["GOODS_EQ_A"], pf["THUNG_12_CAI"], "0.5", "5")
        self.assertIn("L11_SAI_PHEP_NHAN", self.m5.lien_ket(LINK, "preview", sai)["blockers"])
        self.assertIn("L11_TY_LE_DON_VI_KHAC", self.m5.lien_ket(LINK, "preview", sai | {"bang_chung_ty_le_id": pf["CAI_EQ_A"]})["blockers"])
        out = []
        for i, d in enumerate(dongs):
            b = self.cap(cau, d["dong_phien_ban_id"], ei["ma_hoa_id"], ew[i]["ma_hoa_id"], pf["GOODS_EQ_A"], pf["THUNG_12_CAI"], "0.5", "6")
            r = self.xac_nhan(b, f"lk-thung-{i}")
            self.assertEqual(r["so_luong"], {"hoa_don_nguon": "0.5", "phieu_nguon": "6", "pool_hoa_don": "0.5", "pool_phieu": "6"})
            out.append(r)
        n = self.m5.lien_ket(LINK, "preview", self.cap(cau, dongs[0]["dong_phien_ban_id"], ei["ma_hoa_id"], ew[0]["ma_hoa_id"], pf["GOODS_EQ_A"],
                                                        pf["THUNG_12_CAI"], "0.5", "6"))
        self.assertEqual((n["ngan_sach"]["hoa_don"]["con_lai"], n["ngan_sach"]["phieu"]["con_lai"]), ("0", "0"))
        self.assertTrue({"L11_VUOT_SO_LUONG_HOA_DON", "L11_VUOT_SO_LUONG_PHIEU"} <= set(n["blockers"]))
        self.assertEqual(len({r["lien_ket_id"] for r in out}), 1)
        self.state.update(thung=out)

    # ------------------------------------------------------------------ Q04 đổi tuyến KHO → CHI_PHI: CAN_SOAT đồng bộ, giữ lượng, pool bị chặn
    def test_t08_q04_doi_tuyen_can_soat(self):
        s = self.state
        truoc_luong = self.admin.execute("""SELECT id, so_luong_pool_hoa_don::text, so_luong_pool_phieu::text FROM kho.lien_ket_dong
                                            WHERE id IN (%s, %s) ORDER BY id""", (s["c1"], s["c2"])).fetchall()
        ct = self.m2.chi_tiet(M2_CFO, s["hd"])
        cur = ct["tuyen"][0]["id"]
        self.m2.route(M2_CFO, {"hoa_don_id": s["hd"], "cau_noi_id": s["cau"], "dich": "CHI_PHI", "expected_route_id": cur, "expected_graph": ct["expected_graph"],
                               "ly_do": "DEMO đổi tuyến", "khoa": "rt-g01-cp"})
        rows = self.admin.execute("""SELECT id, trang_thai, hieu_luc, can_soat_ly_do, so_luong_pool_hoa_don::text, so_luong_pool_phieu::text FROM kho.lien_ket_dong
                                     WHERE id IN (%s, %s) ORDER BY id""", (s["c1"], s["c2"])).fetchall()
        self.assertEqual([(r[1], r[2]) for r in rows], [("DA_KHOP", "CAN_SOAT")] * 2)
        self.assertTrue(all("TUYEN_DOI_KHOI_KHO" in r[3] for r in rows))
        self.assertEqual([(r[0], r[4], r[5]) for r in rows], [tuple(x) for x in truoc_luong])  # giữ lượng, không giải phóng
        xt = self.m5.lien_ket(LINK, "preview", s["body"] | {"so_luong_hoa_don": "1", "so_luong_phieu": "1"})
        self.assertIn("L11_TUYEN_KHONG_PHAI_KHO", xt["blockers"])
        nh = xt["ngan_sach"]["hoa_don"]
        self.assertEqual((nh["con_lai"], nh["da_xac_nhan"], nh["dang_giu"]), (None, "0", "8"))  # NULL bị chặn, held 8, không 16

    # ------------------------------------------------------------------ Q08 undo held + replay cũ trả HUY hiện hành
    def test_t09_q08_undo_held(self):
        s = self.state
        tok = next(x for x in self.tq()["lien_ket"] if x["id"] == s["lk"])["co_so"]["token_dong"][s["c1"]]
        body = {"child_id": s["c1"], "expected_graph": tok, "khoa": "undo-1", "ly_do": "DEMO undo held"}
        self.raises("KHONG_CO_QUYEN_L11_LIEN_KET", lambda: self.m5.lien_ket(M5_CFO, "huy", body))
        self.raises("L11_VERSION_CHANGED", lambda: self.m5.lien_ket(LINK, "huy", body | {"expected_graph": "0" * 64, "khoa": "undo-cu"}))
        r = self.m5.lien_ket(LINK, "huy", body)
        self.assertEqual((r["trang_thai"], r["hieu_luc"], r["lap_lai"]), ("HUY", "CAN_SOAT", False))
        self.assertTrue(self.m5.lien_ket(LINK, "huy", body)["lap_lai"])
        lai = self.m5.lien_ket(LINK, "xac-nhan", s["body"] | {"expected_graph": s["xt1"], "khoa": "lk-1", "ly_do": "DEMO 4/4 lần 1"})
        self.assertEqual((lai["child_id"], lai["trang_thai"], lai["lap_lai"]), (s["c1"], "HUY", True))  # không trả DA_KHOP lịch sử
        nh = self.m5.lien_ket(LINK, "preview", s["body"] | {"so_luong_hoa_don": "1", "so_luong_phieu": "1"})["ngan_sach"]["hoa_don"]
        self.assertEqual(nh["dang_giu"], "4")  # giải phóng ĐÚNG 4 của child đã hủy; child còn lại vẫn held
        self.assertEqual(self.q("SELECT count(*) FROM kho.lien_ket_dong WHERE id = %s AND huy_bien_nhan_id IS NOT NULL AND huy_boi = %s", (s["c1"], LINK)), 1)

    # ------------------------------------------------------------------ Q04 thu hồi bằng chứng → CAN_SOAT closure
    def test_t10_q04_thu_hoi_bang_chung(self):
        b = self.bang_chung(REF["THUNG_12_CAI"], PCFO)
        self.raises("KHONG_CO_QUYEN_L11_BANG_CHUNG", lambda: self.m5.l11_huy_bang_chung(LINK, {"proof_id": b["id"], "expected_graph": b["expected_graph"],
                                                                                                  "khoa": "rv-link", "ly_do": "x"}))
        r = self.m5.l11_huy_bang_chung(PCFO, {"proof_id": b["id"], "expected_graph": b["expected_graph"], "khoa": "rv-thung", "ly_do": "DEMO thu hồi"})
        self.assertEqual(r["trang_thai"], "DA_THU_HOI")
        ids = [c["child_id"] for c in self.state["thung"]]
        rows = self.admin.execute("SELECT trang_thai, hieu_luc, so_luong_pool_phieu::text FROM kho.lien_ket_dong WHERE id = ANY(%s::uuid[]) ORDER BY id",
                                  (ids,)).fetchall()
        self.assertEqual([(x[0], x[1]) for x in rows], [("DA_KHOP", "CAN_SOAT")] * 2)
        self.assertEqual({x[2] for x in rows}, {"6.000000000000"})

    def test_t11_mo_lai_giu_trang_thai(self):
        truoc = self.dem()
        self.assertEqual({k: v for k, v in l11_demo.khoi_tao(self.admin).items() if k != "mo_lai_giu_quyen_hien_hanh"},
                         {k: 0 for k in self.seed1 if k != "mo_lai_giu_quyen_hien_hanh"})
        self.assertEqual(self.dem(), truoc)  # pool/held/tombstone/thu hồi/core giữ nguyên; không thêm chứng từ/BANK/331


# R2 repair02 — đối chứng mã hóa KHÔNG đồng nhất: native THUNG của hóa đơn → pool CAI phía hóa đơn (DEMO_M2_UNIT_CAI_V1) 12/1, bằng chứng tổng hợp
# trong bộ nhớ (không tệp fixture mới) qua ĐƯỜNG ĐĂNG KÝ COMMON sẵn có (instance/profile/scope bằng chứng riêng + năng lực nguồn của CFO), rồi nhận
# raw → CFO duyệt → mã hóa → liên kết. Profile/4 tham chiếu mặc định giữ nguyên. Đây là đối chứng kỹ thuật DEMO, không phải chính sách tài chính.
SYN_INSTANCE, SYN_PROFILE_REF, SYN_SCOPE = "DEMO_L11_TEST_SYN_INSTANCE_N1", "DEMO_L11_TEST_SYN_PROFILE_N1", "DEMO_L11_TEST_SYN_SCOPE_N1"
SYN_REF = "DEMO_TEST_THUNG_TO_M2CAI_POOL_12_V1"
# repair03 (C): biến thể ÂM đăng ký cùng profile tổng hợp (mỗi biến thể một tham chiếu riêng) — sai đúng MỘT claim so với nguồn thật đã capture
SYN_AM = {"DEMO_TEST_SYN_LEN479_V1": ({"native_byte_length": 479}, "L11_DO_DAI_NATIVE_SAI"),
          "DEMO_TEST_SYN_LENSTR_V1": ({"native_byte_length": "480"}, "L11_DO_DAI_NATIVE_SAI"),
          "DEMO_TEST_SYN_QTY2_V1": ({"quantity_decoded_lexeme": "2"}, "L11_HO_TRO_DON_VI_KHONG_KHOP"),
          "DEMO_TEST_SYN_CTX_V1": ({"profile_ref_unchanged": "DEMO_PROFILE_KHAC_V1"}, "L11_BANG_CHUNG_MA_HOA_KHONG_KHOP")}


def bang_chung_tong_hop(ref: str = SYN_REF, **sua) -> bytes:
    from kho_tri_thuc.k2 import m2_demo
    enc = json.loads(l11_demo.mau_bang_chung("THUNG_ENCODING")[1].decode("utf-8"))
    obj = {"reference_id": ref, "evidence_revision": 1, "pn_ma": "PN_DEMO_A", "native_xml_sha256": enc["native_xml_sha256"],
           "native_byte_length": enc["native_byte_length"], "profile_ref_unchanged": enc["profile_ref_unchanged"],
           "quantity_field_locator": enc["quantity_field_locator"], "quantity_decoded_lexeme": enc["quantity_decoded_lexeme"],
           "unit_field_locator": enc["unit_field_locator"], "unit_decoded_lexeme": enc["unit_decoded_lexeme"], "encoding_kind": enc["encoding_kind"],
           "unit_definition": {"reference_id": enc["unit_definition"]["reference_id"], "definition_sha256": enc["unit_definition"]["definition_sha256"]},
           "pool_unit_definition_ref": "DEMO_M2_UNIT_CAI_V1", "pool_unit_definition_sha256": m2_demo.UNIT_PAYLOAD_SHA256,
           "native_to_pool_ratio": {"numerator_text": "12", "denominator_text": "1", "same_definition_required": False},
           "goods_domain_evidence_sha256": enc["goods_domain_evidence_sha256"]}
    obj.update(sua)
    return json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PostgreSQL L11 không chạy (không tính đạt)")
class L11PhiDongNhatPg(_L11Nen, unittest.TestCase):
    """DB DEMO riêng: một dòng hóa đơn THUNG chỉ có MỘT pool (đơn vị cố định) nên đối chứng 12/1 không chạy chung DB với Q03 (pool THUNG)."""
    TIEN_TO_DB = "kho_test_l11ni_"

    def test_n01_dang_ky_va_duyet(self):
        mm = m5_demo.mau("K01")
        scope = next(c for c in m5_demo.doc_registry()["configured_scopes"] if c["source_instance"] == mm["source_instance"])["scope_ref"]
        self.m5.nhan(M5_INTAKE, source_instance=mm["source_instance"], scope_ref=scope, coverage=mm["coverage"], reported_errors=mm["reported_errors"],
                     client_key="ni-k01", native=mm["native"], master=mm["master"])
        pk = self.phieu("NK20260814001")
        self.m5_chap_nhan(pk, "ni-k01-rv")
        for ma, khoa in (("GOODS_EQ_A", "ni-pf-goods"), ("THUNG_12_CAI", "ni-pf-12")):
            self.nhan_bang_chung(ma, khoa)
        g = self.duyet_bang_chung(REF["GOODS_EQ_A"], "ni-pc-goods")["bang_chung_id"]
        x = self.duyet_bang_chung(REF["THUNG_12_CAI"], "ni-pc-12")["bang_chung_id"]
        # đăng ký nguồn bằng chứng tổng hợp bằng đường cấu hình COMMON sẵn có (như seed): instance/profile/scope + năng lực nguồn hiện hành của CFO
        raw = bang_chung_tong_hop()
        raws = {SYN_REF: raw, **{ref: bang_chung_tong_hop(ref, **sua) for ref, (sua, _) in SYN_AM.items()}}
        payload = dict(l11_demo.EVIDENCE_PROFILE_PAYLOAD)
        payload["proof_references"] = [{"byte_length": len(b), "evidence_revision": 1, "kind": "NATIVE_ENCODING", "raw_sha256": sha256(b), "reference_id": ref}
                                       for ref, b in sorted(raws.items())]
        psha = nguon_chung.digest_payload(payload)
        pn = self.q("SELECT id FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'")
        nd = self.q("SELECT id FROM master.nguoi_dung WHERE dang_nhap = %s", (PCFO,))
        self.admin.execute("INSERT INTO master.nguon_instance (source_instance_id) VALUES (%s)", (SYN_INSTANCE,))
        self.admin.execute("INSERT INTO master.nguon_profile (source_instance_id, profile_ref, profile_sha256, payload) VALUES (%s,%s,%s,%s::jsonb)",
                           (SYN_INSTANCE, SYN_PROFILE_REF, psha, json.dumps(payload, ensure_ascii=False)))
        self.admin.execute("""INSERT INTO master.nguon_pham_vi (source_instance_id, profile_ref, profile_sha256, scope_ref, ma_kho, so_phieu, sections,
                              coverage_binding, scope_kind, company_keys, phap_nhan_id) VALUES (%s,%s,%s,%s,NULL,NULL,%s,%s,'L11_EVIDENCE_SET',NULL,%s)""",
                           (SYN_INSTANCE, SYN_PROFILE_REF, psha, SYN_SCOPE, ["L11_PROOF_JSON"], l11_demo.EVIDENCE_COVERAGE_BINDING, pn))
        for hanh_dong in ("INTAKE", "READ_SOURCE", "SOURCE_MAP"):
            self.admin.execute("""INSERT INTO master.nang_luc_nguon (nguoi_dung_id, source_instance_id, profile_ref, profile_sha256, hanh_dong, target_phap_nhan_id)
                                  VALUES (%s,%s,%s,%s,%s,%s)""", (nd, SYN_INSTANCE, SYN_PROFILE_REF, psha, hanh_dong, pn if hanh_dong == "SOURCE_MAP" else None))
        for i, (ref, b) in enumerate(sorted(raws.items())):
            r = self.m5.l11_nhan_bang_chung(PCFO, source_instance=SYN_INSTANCE, scope_ref=SYN_SCOPE, coverage="COMPLETE_INPUT", client_key=f"ni-pf-syn-{i}",
                                            native=b)
            self.assertEqual((r["promote"]["trang_thai_ung_vien"], r["tham_chieu_cau_hinh"], r["kind"]), ("UNG_VIEN", ref, "NATIVE_ENCODING"))
        # repair03 (C): TRƯỚC khi nguồn THUNG được capture → không duyệt được (giữ raw, 0 bằng chứng đã duyệt mới)
        truoc = self.dem()
        u0 = self.ung_vien(SYN_REF)
        self.raises("L11_HO_TRO_CHUA_CAPTURE", lambda: self.m5.l11_xac_nhan_bang_chung(
            PCFO, {"candidate_id": u0["id"], "expected_graph": u0["expected_graph"], "khoa": "ni-pc-syn-som", "ly_do": "trước capture"}))
        self.assertEqual((self.dem()["bang_chung"], self.dem()["ung_vien"]), (truoc["bang_chung"], truoc["ung_vien"]))
        # capture THUNG THẬT qua service nguồn M2 (reader + COMMON), rồi map/tuyến KHO
        _, xml = l11_demo.mau_nguon("THUNG_XML")
        self.m2.nhan(M2_INTAKE, source_instance=M2_INST, scope_ref=M2_SCOPE, coverage="COMPLETE_INPUT", client_key="ni-thung", native=xml)
        hd = self.hd("DEMO_SERIES_R16", "9001")
        ct = self.m2_map_route(hd, "DEMO_M2_LITERAL_LINE_FACT_R16_THUNG_A_V1", 1, "DEMO_LINE_R16_THUNG_A", "ni-thung")
        # âm: mỗi biến thể sai đúng một claim so với nguồn thật → đúng mã, raw giữ, 0 bằng chứng đã duyệt/mã hóa/child mới
        for ref, (_, ma) in sorted(SYN_AM.items()):
            with self.subTest(am=ref):
                truoc = self.dem()
                ua = self.ung_vien(ref)
                self.raises(ma, lambda: self.m5.l11_xac_nhan_bang_chung(PCFO, {"candidate_id": ua["id"], "expected_graph": ua["expected_graph"],
                                                                                "khoa": f"ni-pc-{ref}", "ly_do": "âm"}))
                sau = self.dem()
                self.assertEqual({k: sau[k] for k in ("bang_chung", "ma_hoa", "child", "ung_vien")},
                                 {k: truoc[k] for k in ("bang_chung", "ma_hoa", "child", "ung_vien")})
        # dương hợp lệ (nguồn thật khớp mọi claim) — cùng ứng viên đã bị từ chối lúc chưa capture
        e = self.duyet_bang_chung(SYN_REF, "ni-pc-syn")["bang_chung_id"]
        bc = next(b for b in self.m5.l11_bang_chung(LINK)["bang_chung"] if b["id"] == e)
        self.assertEqual((bc["tu_don_vi"], bc["den_don_vi"], bc["tu_so"], bc["mau_so"]), ("DEMO_M2_UNIT_THUNG_R16_V1", "DEMO_M2_UNIT_CAI_V1", "12", "1"))
        self.state.update(cau=ct["cau_noi"][0]["id"], pk=pk, g=g, x=x, e=e)

    def test_n02_ma_hoa_va_hai_phep_tinh_doc_lap(self):
        s = self.state
        dong = next(d for d in self.tq()["dong_phieu"] if d["phieu_id"] == s["pk"] and d["stt"] == 1)
        ei = self.ma_hoa("M2", s["cau"], s["e"], khoa="ni-enc-thung")
        self.assertEqual((ei["so_luong_nguon"], ei["don_vi_nguon"], ei["dinh_nghia_nguon"], ei["don_vi_pool"], ei["tu_so"], ei["mau_so"], ei["suc_chua"]),
                         ("1", "THUNG", "DEMO_M2_UNIT_THUNG_R16_V1", "DEMO_M2_UNIT_CAI_V1", "12", "1", "12"))
        ew = self.ma_hoa("M5", dong["dong_phien_ban_id"], khoa="ni-enc-k01")
        self.assertEqual((ew["suc_chua"], ew["dinh_nghia_nguon"], ew["don_vi_pool"]), ("8", "DEMO_UNIT_CAI_A", "DEMO_UNIT_CAI_A"))
        self.assertIsNotNone(ew["do_luong_sha256"])
        cap = self.cap(s["cau"], dong["dong_phien_ban_id"], ei["ma_hoa_id"], ew["ma_hoa_id"], s["g"], s["x"], "0.01", "0.12")
        # âm trước: native 0.01×12 ≠ 1.44×1 dù hai pool 0.12/1.44 đều đủ ngân sách → đúng guard phương trình NATIVE, 0 delta
        truoc = self.dem()
        sai = cap | {"so_luong_phieu": "1.44"}
        xs = self.m5.lien_ket(LINK, "preview", sai)
        self.assertEqual(xs["blockers"], ["L11_SAI_PHEP_NHAN"])
        self.assertEqual((xs["so_luong"]["pool_hoa_don"], xs["so_luong"]["pool_phieu"]), ("0.12", "1.44"))
        self.raises("L11_SAI_PHEP_NHAN", lambda: self.m5.lien_ket(LINK, "xac-nhan", sai | {"expected_graph": xs["expected_graph"], "khoa": "ni-lk-sai",
                                                                                            "ly_do": "sai phép nhân native"}))
        self.assertEqual(self.dem(), truoc)
        # dương: 0.01 THUNG ↔ 0.12 CAI → tiêu thụ 0.12/0.12 pool CAI hai phía (dẫn xuất riêng), còn lại 11.88/7.88
        r = self.xac_nhan(cap, "ni-lk-1")
        self.assertEqual(r["so_luong"], {"hoa_don_nguon": "0.01", "phieu_nguon": "0.12", "pool_hoa_don": "0.12", "pool_phieu": "0.12"})
        self.assertEqual((r["don_vi"]["dinh_nghia_nguon_hoa_don"], r["don_vi"]["dinh_nghia_nguon_phieu"]), ("DEMO_M2_UNIT_THUNG_R16_V1", "DEMO_UNIT_CAI_A"))
        ns = self.m5.lien_ket(LINK, "preview", cap)["ngan_sach"]
        self.assertEqual((ns["hoa_don"]["suc_chua"], ns["hoa_don"]["con_lai"], ns["phieu"]["suc_chua"], ns["phieu"]["con_lai"]), ("12", "11.88", "8", "7.88"))


def zip_trong_bo_nho(*thanh_vien: tuple[str, bytes]) -> bytes:
    """ZIP dựng trong bộ nhớ từ bytes XML đã pin (không tệp fixture mới); thứ tự thành viên = thứ tự delivery của batch."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for ten, raw in thanh_vien:
            z.writestr(ten, raw)
    return buf.getvalue()


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PostgreSQL L11 không chạy (không tính đạt)")
class L11LoDanhTinhPg(_L11Nen, unittest.TestCase):
    """Repair03 (A) — consumer M2 với batch NHIỀU danh tính qua cổng identity toàn batch: hai thứ tự [A,B]/[B,A] và trộn mới/đã có, TUẦN TỰ.
    Chỉ chứng minh hành vi/phân loại giữ nguyên dưới cổng mới; KHÔNG phải bằng chứng nhân quả hai batch đồng thời (ca đó UNRUN/chưa viết)."""
    TIEN_TO_DB = "kho_test_l11lo_"

    def danh_tinh(self):
        return self.q("SELECT count(*) FROM kho.hoa_don_danh_tinh")

    def test_b01_ab_moi_roi_ba_da_co_va_tron(self):
        g01, _ = g01_va_fact01()
        _, thung = l11_demo.mau_nguon("THUNG_XML")
        r = self.m2.nhan(M2_INTAKE, source_instance=M2_INST, scope_ref=M2_SCOPE, coverage="COMPLETE_INPUT", client_key="lo-ab",
                         native=zip_trong_bo_nho(("a.xml", g01), ("b.xml", thung)), artifact_name="lo-ab.zip")
        self.assertEqual(sorted(i["classification"][0] for i in r["promote"]["items"]), ["FIRST_OBSERVATION", "FIRST_OBSERVATION"])
        self.assertEqual(self.danh_tinh(), 2)
        r = self.m2.nhan(M2_INTAKE, source_instance=M2_INST, scope_ref=M2_SCOPE, coverage="COMPLETE_INPUT", client_key="lo-ba",
                         native=zip_trong_bo_nho(("b.xml", thung), ("a.xml", g01)), artifact_name="lo-ba.zip")
        self.assertEqual(sorted(i["classification"][0] for i in r["promote"]["items"]), ["SAME_CONTENT_REPEAT", "SAME_CONTENT_REPEAT"])
        self.assertEqual(self.danh_tinh(), 2)  # không danh tính thừa; skeleton chỉ tạo khi chưa có
        # trộn đã có + mới: G01 (đã có) + G04 purchase A (mới) trong một batch
        g04 = m2_xml("inputs/G04-purchase-a-padded.xml")
        r = self.m2.nhan(M2_INTAKE, source_instance=M2_INST, scope_ref=M2_SCOPE, coverage="COMPLETE_INPUT", client_key="lo-tron",
                         native=zip_trong_bo_nho(("a.xml", g01), ("c.xml", g04)), artifact_name="lo-tron.zip")
        self.assertEqual(sorted(i["classification"][0] for i in r["promote"]["items"]), ["FIRST_OBSERVATION", "SAME_CONTENT_REPEAT"])
        self.assertEqual(self.danh_tinh(), 3)
        # mỗi danh tính đúng MỘT hàng danh tính, mọi quan sát có nội dung (không skeleton mồ côi)
        self.assertEqual(self.q("""SELECT count(*) FROM kho.hoa_don_danh_tinh d WHERE NOT EXISTS (SELECT 1 FROM kho.hoa_don_quan_sat o WHERE o.hoa_don_id = d.id)"""), 0)


def m2_xml(rel: str) -> bytes:
    xmlfix = ROOT / "tests" / "fixtures" / "m2_invoice_xml"
    man = {f["path"]: f for f in json.loads(_pin(xmlfix / "manifest.json", "43ad28257ca646b9d43f45ed34a8c441131328cca1b576cf247b378224e2b177")
                                             .decode("utf-8"))["files"]}
    return _pin(xmlfix / rel, man[rel]["sha256"])


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PostgreSQL L11 không chạy (không tính đạt)")
class L11Q09TuyenXacNhanPg(_L11Nen, unittest.TestCase):
    """Repair03 Q09 (một phần): route ↔ confirm trên HAI kết nối app thật tách biệt, danh tính phiên hiện hành, hàm CSDL thật trong giao dịch MỞ (kết quả
    trả về khi CHƯA COMMIT để quan sát chờ nhân quả), `pg_blocking_pids` đúng PID kẻ thắng, watchdog hữu hạn (lock_timeout + join timeout). Cả hai thứ tự
    thắng. Không sleep giả, không giả kết quả UDF. Revoke↔confirm và undo-held↔confirm mới: CHƯA VIẾT (UNRUN)."""
    TIEN_TO_DB = "kho_test_l11q9_"
    CHO = 30.0

    def ket_noi(self, login):
        opts = "-c lock_timeout=25000 -c statement_timeout=60000"
        c = psycopg.connect(self.app_dsn, autocommit=True, row_factory=dict_row, options=opts)
        self.addCleanup(c.close)  # chỉ đóng kết nối, không dọn dữ liệu
        nd = self.q("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s", (login,))
        c.execute("BEGIN")
        c.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (nd, login))
        return c

    def cho_bi_chan(self, pid_cho, pid_thang):
        het = time.monotonic() + self.CHO
        while time.monotonic() < het:
            if pid_thang in (self.q("SELECT pg_blocking_pids(%s)", (pid_cho,)) or []):
                return True
            time.sleep(0.05)
        return False

    def chay_nen(self, conn, sql, params):
        kq = {}

        def chay():
            try:
                kq["v"] = conn.execute(sql, params).fetchone()
            except Exception as e:  # noqa: BLE001 — giữ nguyên lỗi thật để assert mã
                kq["e"] = e
        t = threading.Thread(target=chay, daemon=True)
        t.start()
        return t, kq

    def test_q01_chuan_bi(self):
        cau, dong, hd, pk = self.g01_k01()
        for ma, khoa in (("GOODS_EQ_A", "q9-pf-goods"), ("CAI_EQ_A", "q9-pf-cai")):
            self.nhan_bang_chung(ma, khoa)
        g = self.duyet_bang_chung(REF["GOODS_EQ_A"], "q9-pc-goods")["bang_chung_id"]
        x = self.duyet_bang_chung(REF["CAI_EQ_A"], "q9-pc-cai")["bang_chung_id"]
        ei = self.ma_hoa("M2", cau, khoa="q9-enc-g01")
        ew = self.ma_hoa("M5", dong["dong_phien_ban_id"], khoa="q9-enc-k01")
        self.state.update(hd=hd, cau=cau, body=self.cap(cau, dong["dong_phien_ban_id"], ei["ma_hoa_id"], ew["ma_hoa_id"], g, x, "1", "1"))

    def tuyen_hien_hanh(self, ct):
        """Repair04 (Q09-TEST-1): tuyến HIỆN HÀNH duy nhất của ĐÚNG dòng nguồn của cầu nối đang thử, đọc từ DTO thật (`cau_noi` → `source_dong_id`,
        `tuyen` lọc hien_hanh + DA_DUYET cùng dòng). Không lấy theo vị trí mảng (`tuyen[0]` là bản lịch sử cũ nhất sau khi đổi tuyến). Không có ĐÚNG
        một tuyến hiện hành hợp lệ → fail rõ (lỗi dựng test, không phải kết quả race)."""
        cau = [b for b in ct["cau_noi"] if b["id"] == self.state["cau"]]
        self.assertEqual(len(cau), 1, f"cầu nối {self.state['cau']} không duy nhất trong DTO")
        hien = [r for r in ct["tuyen"] if r["source_dong_id"] == cau[0]["source_dong_id"] and r["hien_hanh"] and r["trang_thai"] == "DA_DUYET"]
        self.assertEqual(len(hien), 1, f"dòng nguồn {cau[0]['source_dong_id']} phải có đúng một tuyến hiện hành DA_DUYET: {hien}")
        return hien[0]

    def route_body(self, dich, khoa):
        ct = self.m2.chi_tiet(M2_CFO, self.state["hd"])
        return {"hoa_don_id": self.state["hd"], "cau_noi_id": self.state["cau"], "dich": dich, "expected_route_id": self.tuyen_hien_hanh(ct)["id"],
                "expected_graph": ct["expected_graph"], "reason": "Q09 route", "client_key": khoa}

    def confirm_body(self, khoa):
        xt = self.m5.lien_ket(LINK, "preview", self.state["body"])
        self.assertEqual(xt["blockers"], [])
        return {**self.state["body"], "expected_graph": xt["expected_graph"], "client_key": khoa, "reason": "Q09 confirm"}

    def test_q02_route_thang_confirm_sau_nhan_dung_ma_0_delta(self):
        self.assertEqual(self.tuyen_hien_hanh(self.m2.chi_tiet(M2_CFO, self.state["hd"]))["dich"], "KHO")  # tiền điều kiện thật, không giả
        cb = self.confirm_body("q9-lk-thua")  # token đọc khi tuyến còn KHO
        a, b = self.ket_noi(M2_CFO), self.ket_noi(LINK)
        a.execute("SELECT kho.m2_route(%s::jsonb) AS v", (json.dumps(self.route_body("CHI_PHI", "q9-rt-1")),)).fetchone()  # trả về, CHƯA COMMIT
        pid_a, pid_b = a.info.backend_pid, b.info.backend_pid
        truoc = self.dem()
        t, kq = self.chay_nen(b, "SELECT kho.l11_xac_nhan(%s::jsonb) AS v", (json.dumps(cb),))
        self.assertTrue(self.cho_bi_chan(pid_b, pid_a), "confirm không bị chặn bởi route đang giữ gốc — không tính đạt")
        a.execute("COMMIT")
        t.join(self.CHO)
        self.assertFalse(t.is_alive(), "watchdog: confirm treo — không tính đạt")
        self.assertIn("e", kq)
        self.assertEqual(kq["e"].diag.message_primary.split(":", 1)[0], "L11_VERSION_CHANGED")
        b.execute("ROLLBACK")
        sau = self.dem()
        self.assertEqual({k: sau[k] for k in ("child", "parent", "bien_nhan_l11")}, {k: truoc[k] for k in ("child", "parent", "bien_nhan_l11")})
        # trả tuyến về KHO TUẦN TỰ (đối chứng tuần tự, không gọi là thành công đồng thời)
        self.route_tuan_tu("KHO", "q9-rt-ve-kho")

    def route_tuan_tu(self, dich, khoa):
        """Bước TUẦN TỰ riêng với token mới (không phải kết quả đồng thời): phải thành công thật và để lại đúng một tuyến hiện hành mang đích yêu cầu."""
        rb = self.route_body(dich, khoa)
        r = self.m2.route(M2_CFO, {"hoa_don_id": rb["hoa_don_id"], "cau_noi_id": rb["cau_noi_id"], "dich": dich, "expected_route_id": rb["expected_route_id"],
                                   "expected_graph": rb["expected_graph"], "ly_do": rb["reason"], "khoa": khoa})
        self.assertEqual((r["lap_lai"], r["dich"], r["predecessor_route_id"]), (False, dich, rb["expected_route_id"]))
        hien = self.tuyen_hien_hanh(self.m2.chi_tiet(M2_CFO, self.state["hd"]))
        self.assertEqual((hien["id"], hien["dich"]), (r["route_id"], dich))
        return r

    def test_q03_confirm_thang_route_sau_khoi_dong_lai(self):
        # tiền điều kiện: q02 đã khôi phục KHO TUẦN TỰ thành công — nếu không, fail ở đây (lỗi dựng), không chạy race trên trạng thái sai
        self.assertEqual(self.tuyen_hien_hanh(self.m2.chi_tiet(M2_CFO, self.state["hd"]))["dich"], "KHO")
        cb = self.confirm_body("q9-lk-thang")
        rb = self.route_body("CHI_PHI", "q9-rt-2")
        a, b = self.ket_noi(LINK), self.ket_noi(M2_CFO)
        r = a.execute("SELECT kho.l11_xac_nhan(%s::jsonb) AS v", (json.dumps(cb),)).fetchone()["v"]  # child tạo, CHƯA COMMIT
        pid_a, pid_b = a.info.backend_pid, b.info.backend_pid
        tuyen_truoc = self.q("SELECT count(*) FROM kho.mua_dich_dong")
        t, kq = self.chay_nen(b, "SELECT kho.m2_route(%s::jsonb) AS v", (json.dumps(rb),))
        self.assertTrue(self.cho_bi_chan(pid_b, pid_a), "route không bị chặn bởi confirm đang giữ gốc — không tính đạt")
        a.execute("COMMIT")
        t.join(self.CHO)
        self.assertFalse(t.is_alive(), "watchdog: route treo — không tính đạt")
        # route precollect TRƯỚC khi child của kẻ thắng hiện ra; sau khi giữ gốc đọc lại thấy closure khác → khởi động lại toàn thao tác, 0 hiệu lực
        self.assertIn("e", kq)
        self.assertEqual(kq["e"].diag.message_primary.split(":", 1)[0], "L11_CLOSURE_MO_RONG")
        b.execute("ROLLBACK")
        self.assertEqual(self.q("SELECT count(*) FROM kho.mua_dich_dong"), tuyen_truoc)
        self.assertEqual(self.admin.execute("SELECT hieu_luc FROM kho.lien_ket_dong WHERE id = %s", (r["child_id"],)).fetchone()[0], "CO_HIEU_LUC")
        # đối chứng TUẦN TỰ riêng (token mới, không gọi là thành công đồng thời): route lại → child giữ soát nguyên tử, giữ lượng
        self.route_tuan_tu("CHI_PHI", "q9-rt-2-lai")
        row = self.admin.execute("SELECT trang_thai, hieu_luc, can_soat_ly_do FROM kho.lien_ket_dong WHERE id = %s", (r["child_id"],)).fetchone()
        self.assertEqual((row[0], row[1]), ("DA_KHOP", "CAN_SOAT"))
        self.assertIn("TUYEN_DOI_KHOI_KHO", row[2])


if __name__ == "__main__":
    unittest.main()
