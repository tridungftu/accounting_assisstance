"""M4-04A — kiểm PostgreSQL THẬT cho Request nháp (hằng M4_REQUEST_NHAP + RequestNhap trên XayDungK2/DuyetDot). CODE_ONLY: coder viết, CHƯA CHẠY.

KHÔNG tạo CSDL/role, KHÔNG template0, KHÔNG migrate/bootstrap/M9, KHÔNG SET ROLE, KHÔNG apply SQL: chạy DUY NHẤT trên một CLONE DEMO SỞ HỮU mà Root đã
dựng (schema = PG_SCHEMA_VERSION hiện hành của registry) VÀ đã tự apply `M4_REQUEST_NHAP` (gói này không đăng ký/ordinal). Env lúc chạy (không .env/var,
không hardcode DSN, không in DSN):
  KHO_M4_04A_CLONE_DSN         DSN chủ bảng (owner) — đường tin cậy của máy chủ
  KHO_M4_04A_CLONE_APP_DSN     DSN login ứng dụng có sẵn (SCRAM, IN ROLE app_web, NOSUPERUSER, NOBYPASSRLS) — test KHÔNG tạo role
  KHO_M4_04A_CLONE_DB          tên CSDL clone mong đợi (bắt đầu 'kho_test_')
  KHO_M4_04A_CLONE_PROVENANCE  = master.he_thong['m4_04a_clone_provenance'] Root ghi khi dựng clone
  KHO_M4_04A_SQL_SHA256        SHA-256 Root ghim của '\\n'.join(M4_REQUEST_NHAP) (= master.he_thong['m4_04a_request_sql_sha256'] = định nghĩa hiện tại)
Không env nào → SkipTest 'NOT_VERIFIED' (KHÔNG phải PASS). Env dở dang / clone không chứng minh được (kể cả không đọc được pg_authid để chứng minh SCRAM)
→ LoiThietLap TRƯỚC mọi ghi. Request là `FakeRequest` (TEST_ONLY, tests/test_m4_request_tinh.py) — không mạng, không Request thật.
Ghi sau cổng: duyệt viên DEMO (m4_demo.khoi_tao_duyet, insert-only), hồ sơ DEMO mới của lượt (run_id), mapping DEMO (request_anh_xa_dat).
Không DROP/DELETE/TRUNCATE, không dọn dẹp; ca bất biến dùng giao dịch force_rollback (luôn hủy). Q06 thu hồi mapping DEMO — clone sau đó không dùng lại.

Q01 chưa mapping → CHUA_CAU_HINH ['anh_xa_nhan_vien'], 0 IO, 0 hàng request_*.
Q02 dương: mapping → tạo → DOC → tải PDF seal → chờ quét → clean → DA_DOI_SOAT; hàng intent literal (31500000/VND, người đứng tên, key, SHA PDF),
    13 sự kiện đúng thứ tự, 2 biên nhận; xem() qua RLS; phát lại cùng khóa 0 POST; cùng khóa khác hành động → IDEMPOTENCY_KHAC.
Q03 mất ACK tạo + xoay khóa (CAN_CU_DOI, 0 POST) + khởi động lại (lease còn → DANG_XU_LY; lease hết → CHUA_RO_TAO → gửi lại cùng key → một Request).
Q04 đồng thời (lệnh thứ hai trên kết nối khác giữa lúc POST → DANG_XU_LY; không giữ giao dịch qua HTTP) + hash sai → HOLD TEP_HASH_LECH.
Q05 bypass SQL (login app gọi hàm lệnh/ghi bảng → từ chối), bất biến (force_rollback), phạm vi (XEM → PHAM_VI; A2/B1 → KHONG_THAY), RLS đọc.
Q06 thu hồi hiện hành giữa lúc POST → bằng chứng ghi + PHAM_VI_DA_DOI; lệnh sau → CHUA_CAU_HINH 0 IO; mapping mới → HOLD ANH_XA_DOI / DA_DOI_SOAT
    + canh_bao. Cửa sổ 20h KHÔNG kiểm ở đây (cần đổi đồng hồ/cột ghi-một-lần) — chỉ ở test thuần.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import time
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from tests.test_m4_02c_pg import A1, A2, B1, DUYET, REVIEW, XEM, LoiThietLap, _q1, chuan_bi_duyet_vien, dung_ho_so, than_ket_luan
from tests.test_m4_request_tinh import CHU_KHOA, NV, DongHo, FakeRequest, SapTienTrinh, cau_hinh

ENV_CHU, ENV_APP, ENV_DB, ENV_NGUON, ENV_SQL = ("KHO_M4_04A_CLONE_DSN", "KHO_M4_04A_CLONE_APP_DSN", "KHO_M4_04A_CLONE_DB",
                                                "KHO_M4_04A_CLONE_PROVENANCE", "KHO_M4_04A_SQL_SHA256")
ENV = (ENV_CHU, ENV_APP, ENV_DB, ENV_NGUON, ENV_SQL)
KHOA_NGUON, KHOA_SQL = "m4_04a_clone_provenance", "m4_04a_request_sql_sha256"
TIEN_TO_DB = "kho_test_"
CO_ENV = any(os.environ.get(k) for k in ENV)
LY_DO_SKIP = "NOT_VERIFIED: chưa cấp clone DEMO sở hữu đã apply M4_REQUEST_NHAP (KHO_M4_04A_CLONE_*) — test M4-04A PG/HTTP không chạy, KHÔNG tính đạt"
BANG = ("request_anh_xa", "request_y_dinh", "request_su_kien", "request_bien_nhan")
PN_MA = "PN_DEMO_A"


# ================================================================================================== cổng clone (dùng chung với test_m4_request_http)
def cau_hinh_clone() -> dict:
    gia_tri = {k: os.environ.get(k) or "" for k in ENV}
    thieu = [k for k, v in gia_tri.items() if not v]
    if thieu:
        raise LoiThietLap("SETUP_FAILURE: cấu hình clone dở dang — thiếu " + ", ".join(thieu))
    if psycopg is None:
        raise LoiThietLap("SETUP_FAILURE: thiếu driver psycopg")
    if not re.fullmatch(r"[0-9a-f]{64}", gia_tri[ENV_SQL]):
        raise LoiThietLap(f"SETUP_FAILURE: {ENV_SQL} phải là SHA-256 hex thường")
    return gia_tri


def sql_sha256() -> str:
    from kho_tri_thuc.m4.sql_request_nhap import M4_REQUEST_NHAP
    return hashlib.sha256("\n".join(M4_REQUEST_NHAP).encode("utf-8")).hexdigest()


def kiem_clone_request(chu, web, cfg: dict) -> dict:
    """Cổng CHỈ ĐỌC trước mọi ghi. chu = owner (autocommit), web = login ứng dụng (autocommit). Sai → LoiThietLap (không chứa DSN)."""
    from kho_tri_thuc.ha_tang import pg_migrations as PGM
    from kho_tri_thuc.ha_tang import postgres as pg
    from kho_tri_thuc.k2 import crm_demo, m4_demo

    def sai(ly_do):
        raise LoiThietLap("SETUP_FAILURE: " + ly_do + " — không ghi gì; Root cấp clone DEMO sở hữu đúng lineage + SQL M4-04A đã ghim")
    db = _q1(chu, "SELECT current_database()")
    if db != cfg[ENV_DB] or not str(db).startswith(TIEN_TO_DB):
        sai(f"CSDL owner không phải clone mong đợi (phải = {ENV_DB}, bắt đầu '{TIEN_TO_DB}')")
    if _q1(web, "SELECT current_database()") != db:
        sai("login ứng dụng không trỏ cùng CSDL clone")
    r = web.execute("""SELECT r.rolname, r.rolsuper, r.rolbypassrls, pg_has_role(current_user, 'app_web', 'MEMBER')
                       FROM pg_roles r WHERE r.rolname = current_user""").fetchone()
    vals = tuple(r.values()) if isinstance(r, dict) else tuple(r or ())
    if len(vals) != 4 or vals[1:] != (False, False, True):
        sai("login ứng dụng phải IN ROLE app_web, NOSUPERUSER, NOBYPASSRLS")
    app_role = vals[0]
    if getattr(web.pgconn, "used_password", None) is not True:
        sai("login ứng dụng không xác thực bằng mật khẩu")
    try:
        scram = _q1(chu, "SELECT rolpassword LIKE 'SCRAM-SHA-256$%%' FROM pg_authid WHERE rolname = %s", (app_role,))
    except psycopg.Error:
        raise LoiThietLap("NOT_VERIFIED: owner không đọc được pg_authid — không chứng minh được login ứng dụng dùng SCRAM; không ghi gì") from None
    if scram is not True:
        sai("mật khẩu login ứng dụng không phải SCRAM-SHA-256")
    try:
        version = pg.kiem_lineage_ung_dung(chu)
    except DataError as exc:
        sai(f"lineage không khớp ({exc.code})")
    if version != PGM.PG_SCHEMA_VERSION:
        sai("schema clone ≠ PG_SCHEMA_VERSION của registry hiện hành")
    for t in BANG:
        if _q1(chu, f"SELECT to_regclass('m4.{t}') IS NOT NULL") is not True:
            sai(f"clone chưa có m4.{t} (Root chưa apply M4_REQUEST_NHAP)")
    if _q1(chu, "SELECT pg_has_role(current_user, c.relowner, 'MEMBER') FROM pg_class c WHERE c.oid = 'm4.request_y_dinh'::regclass") is not True:
        sai("kết nối owner không sở hữu bảng Request (không phải đường tin cậy của máy chủ)")
    he = dict(chu.execute("SELECT key, value FROM master.he_thong WHERE key = ANY(%s)",
                          ([pg.APP_MARKER_KEY, crm_demo.MARKER, m4_demo.MARKER, KHOA_NGUON, KHOA_SQL],)).fetchall())
    ck = sql_sha256()
    if not (he.get(KHOA_SQL) == ck == cfg[ENV_SQL]):
        sai("SHA SQL M4-04A trong clone ≠ định nghĩa hiện tại ≠ giá trị Root ghim")
    if he.get(pg.APP_MARKER_KEY) != pg.APP_MARKER_VALUE:
        sai("thiếu marker ứng dụng")
    if crm_demo.MARKER not in he or m4_demo.MARKER not in he:
        sai("thiếu marker seed CRM/M4 DEMO (clone phải dựng từ DEMO, test không seed)")
    if he.get(KHOA_NGUON) != cfg[ENV_NGUON]:
        sai(f"provenance clone ({KHOA_NGUON}) không khớp {ENV_NGUON}")
    if _q1(chu, r"SELECT count(*) FROM master.phap_nhan WHERE ma NOT LIKE 'PN\_DEMO\_%'") != 0:
        sai("có pháp nhân ngoài DEMO — có thể là CSDL thật")
    if _q1(chu, "SELECT count(*) FROM master.nguoi_dung WHERE NOT mo_phong") != 0:
        sai("có người dùng không mô phỏng — có thể là CSDL thật")
    if _q1(chu, "SELECT count(*) FROM m4.request_anh_xa") != 0 or _q1(chu, "SELECT count(*) FROM m4.request_y_dinh") != 0:
        sai("clone đã có mapping/intent Request (đã dùng) — cần clone mới; test không dọn")
    return {"trang_thai": "CLONE_DEMO_DA_KIEM", "schema": version, "request_sql_sha256": ck, "scram": True}


# ================================================================================================== dựng hồ sơ đã seal + mapping (dùng chung với HTTP)
def dung_seal(svc, admin, K, nhan: str, run_id: str) -> dict:
    """Hồ sơ DEMO mới (dung_ho_so của 02C) → kết luận REVIEW (KET_LUAN_VND) → chấp thuận DUYET → PDF A1 → DA_SEAL. Trả định danh + bytes PDF."""
    h = dung_ho_so(svc, admin, K, nhan, run_id)
    dot = h["dot"]
    svc.duyet_ket_luan(REVIEW, **than_ket_luan(svc.duyet_xem(REVIEW, dot_id=dot)), khoa=K(f"{nhan}-kl"))
    x = svc.duyet_xem(DUYET, dot_id=dot)
    c = x["context"]
    svc.duyet_chap_thuan(DUYET, dot_id=dot, version_id=c["version_id"], revision=c["revision"], expected_basis=c["basis_sha256"],
                         ket_luan_id=x["ket_luan"]["id"], ly_do="Chấp thuận hồ sơ đợt DEMO (M4-04A)", khoa=K(f"{nhan}-ct"))
    c = svc.duyet_xem(A1, dot_id=dot)["context"]
    raw = F.ho_so_dot_duyet_pdf(f"REQ-{nhan}")
    p = svc.duyet_pdf(A1, raw, dot_id=dot, version_id=c["version_id"], revision=c["revision"], expected_basis=c["basis_sha256"],
                      ten="ho_so_da_duyet.pdf", media_type="application/pdf", khoa=K(f"{nhan}-pdf"))
    if p.get("trang_thai") != "DA_SEAL":
        raise AssertionError(f"hồ sơ {nhan} không DA_SEAL: {p.get('trang_thai')}")
    return {**h, "raw": raw, "pb": c["version_id"], "seal": p["seal_id"], "pdf": p["pdf_id"], "pn": str(c["phap_nhan_id"])}


def dat_anh_xa(svc, login: str, pn: str, request_dang_nhap: str) -> dict:
    """Mapping DEMO qua hàm tin cậy (kết nối chủ bảng + danh tính phiên). Đây là việc của máy chủ/Root — test làm thay trên clone DEMO."""
    dt = svc.danh_tinh(login)
    with svc._tx_review(dt) as c:
        return svc._r1(c, "SELECT m4.request_anh_xa_dat(%s::uuid, %s::uuid, %s, %s) AS r",
                       (dt["id"], pn, request_dang_nhap, "TEST_ONLY: mapping DEMO M4-04A trên clone sở hữu"))["r"]


def thu_hoi_anh_xa(svc, login: str, anh_xa_id: str) -> dict:
    with svc._tx_review(svc.danh_tinh(login)) as c:
        return svc._r1(c, "SELECT m4.request_anh_xa_thu_hoi(%s::uuid, %s) AS r", (anh_xa_id, "TEST_ONLY: thu hồi DEMO"))["r"]


def cau_hinh_pg(pn: str, **thay):
    return cau_hinh(phap_nhan_ma={pn: PN_MA}, **thay)


@unittest.skipUnless(CO_ENV, LY_DO_SKIP)
class M4RequestPG(unittest.TestCase):
    """Chạy theo thứ tự q01…q06 trên MỘT clone; trạng thái qua cls.s. Q06 thu hồi mapping DEMO (không đảo ngược)."""

    @classmethod
    def setUpClass(cls):
        import tests.test_m4_02b_k2 as K2B
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        cfg = cau_hinh_clone()
        cls.cfg = cfg
        cls.admin = psycopg.connect(cfg[ENV_CHU], autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        cls.web_raw = psycopg.connect(cfg[ENV_APP], autocommit=True)
        cls.addClassCleanup(cls.web_raw.close)
        cls.gate = kiem_clone_request(cls.admin, cls.web_raw, cfg)  # CHỈ ĐỌC
        from tests.test_m4_02b_pure import _docx, openpyxl
        if not (K2B._nguon_da_nap() and openpyxl is not None and _docx is not None):
            raise unittest.SkipTest("NOT_RUN: lõi nguồn Review chưa nạp hoặc thiếu openpyxl/python-docx — không dựng được hồ sơ")
        cls.goc = Path(tempfile.mkdtemp(prefix="ktt_m4_04a_pg_"))  # DataRoot DEMO của lượt — giữ lại
        cls.run_id = uuid.uuid4().hex[:8]
        cls.trich6, cls.gate6 = K2B.M4ChungTuPG._gate_trich6.__func__(cls)
        cls.seed = chuan_bi_duyet_vien(cls.admin)  # ghi đầu tiên — sau cổng
        cls.XayDungK2 = XayDungK2
        cls.svc = cls._svc_moi()
        cls.s = {}

    @classmethod
    def _svc_moi(cls):
        web = psycopg.connect(cls.cfg[ENV_APP], autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(web.close)
        chu = psycopg.connect(cls.cfg[ENV_CHU], autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(chu.close)
        return cls.XayDungK2(web, cls.goc / "m4-k2", conn_tin_cay=chu, trich6=cls.trich6)

    # ------------------------------------------------------------------ helpers
    def K(self, ten):
        return f"m4rq-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return _q1(self.admin, sql, params)

    def can(self, *khoa):
        for k in khoa:
            if k not in self.s:
                self.skipTest(f"ca trước chưa dựng '{k}' — NOT_RUN")

    def ho_so(self, nhan) -> dict:
        if nhan not in self.s:
            self.s[nhan] = dung_seal(self.svc, self.admin, self.K, nhan, self.run_id)
        return self.s[nhan]

    def rq(self, h, fake, svc=None, **kw):
        from kho_tri_thuc.m4.request_nhap import RequestNhap
        ch = kw.pop("ch", None) or cau_hinh_pg(h["pn"])
        return RequestNhap(svc or self.svc, ch, fake, **kw)

    def tao(self, h, fake, khoa, login=A1, **kw):
        return self.rq(h, fake, **kw).tao(login, dot_id=h["dot"], version_id=h["pb"], khoa=self.K(khoa))

    def doi_soat(self, h, fake, khoa, login=A1, **kw):
        return self.rq(h, fake, **kw).doi_soat(login, dot_id=h["dot"], version_id=h["pb"], khoa=self.K(khoa))

    def loi(self, fn, *a, **k) -> str:
        try:
            fn(*a, **k)
        except DataError as exc:
            return exc.code
        except psycopg.Error as exc:
            p = (getattr(exc.diag, "message_primary", "") or "").split(":", 1)[0]
            return p if re.fullmatch(r"[A-Z][A-Z0-9_]*", p) else type(exc).__name__
        self.fail("thao tác không bị chặn")

    def y(self, h) -> dict:
        r = self.svc.conn_tin_cay.execute("SELECT * FROM m4.request_y_dinh WHERE seal_id = %s AND nhanh = 'GOC'", (h["seal"],)).fetchone()
        return r

    def su_kien(self, h) -> list:
        return [(r["buoc"], r["tu_trang_thai"], r["den_trang_thai"], r["quyen_con"]) for r in self.svc.conn_tin_cay.execute(
            "SELECT s.* FROM m4.request_su_kien s JOIN m4.request_y_dinh y ON y.id = s.y_dinh_id WHERE y.seal_id = %s ORDER BY s.thu_tu",
            (h["seal"],)).fetchall()]

    def dem(self) -> dict:
        return {t: self.q(f"SELECT count(*) FROM m4.{t}") for t in BANG}

    # ------------------------------------------------------------------ Q01
    def test_q01_chua_mapping(self):
        h = self.ho_so("A")
        fake = FakeRequest(DongHo())
        truoc = self.dem()
        r = self.tao(h, fake, "A-chua-map")
        self.assertEqual((r["trang_thai"], r["thieu"], r["y_dinh"]), ("CHUA_CAU_HINH", ["anh_xa_nhan_vien"], None))
        self.assertEqual((fake.nhat_ky, self.dem()), ([], truoc))
        r = self.tao(h, None, "A-chua-khoa")
        self.assertEqual(r["thieu"], ["anh_xa_nhan_vien", "khoa_api"])
        self.assertEqual(self.dem(), truoc)
        x = self.rq(h, None).xem(A1, dot_id=h["dot"])
        self.assertEqual((x["quyen"], x["cau_hinh"], x["y_dinh"]),
                         ({"tao": False, "tai_pdf": True, "anh_xa": False}, {"trang_thai": "CHUA_CAU_HINH", "thieu": ["anh_xa_nhan_vien", "khoa_api"]}, []))
        self.s["q01"] = True

    # ------------------------------------------------------------------ Q02
    def test_q02_duong(self):
        h = self.ho_so("A")
        ax = dat_anh_xa(self.svc, A1, h["pn"], NV)
        self.assertEqual(ax["revision"], 1)
        self.s["ax1"] = str(ax["id"])
        fake = FakeRequest(DongHo())
        r = self.tao(h, fake, "A-tao")
        self.assertEqual((r["trang_thai"], r["buoc"], r["lap_lai"]), ("CHO_QUET", ["TAO", "DOC", "TAI", "DOI_SOAT"], False))
        self.assertEqual(len(fake.de_xuat), 1)
        x = next(iter(fake.de_xuat.values()))
        self.assertEqual((x["nguoiTao"], x["giaTri"]["so_tien"], x["giaTri"]["phap_nhan"], x["nhom"]),
                         (NV, {"amount": "31500000", "currency": "VND"}, PN_MA, "THANH_TOAN_HD"))
        self.assertNotEqual(x["nguoiTao"], CHU_KHOA)
        tid = x["tep"][0]
        self.assertEqual(fake.tep[tid]["bytes"], h["raw"])
        fake.quet(tid, "clean")
        r = self.doi_soat(h, fake, "A-ds")
        self.assertEqual((r["trang_thai"], r["buoc"]), ("DA_DOI_SOAT", ["DOC", "DOI_SOAT"]))
        y = self.y(h)
        sha = hashlib.sha256(h["raw"]).hexdigest()
        self.assertEqual((y["trang_thai"], y["so_tien"], y["tien_te"], y["nguoi_tao"], y["idem_key"], str(y["remote_id"]), str(y["remote_tep_id"]),
                          y["pdf_sha256"], y["doi_soat_sha256"], y["doi_soat_byte_length"], y["tep_trang_thai_quet"], y["hold_ma"], y["lease_id"]),
                         ("DA_DOI_SOAT", "31500000", "VND", NV, f"m4-request:{y['id']}", x["id"], tid, sha, sha, len(h["raw"]), "clean", None, None))
        self.assertEqual(self.su_kien(h), [
            ("Y_DINH", None, "MOI", True), ("GIU_TAO", "MOI", "MOI", True), ("GHI_TAO", "MOI", "DA_TAO", True),
            ("GIU_DOC", "DA_TAO", "DA_TAO", True), ("GHI_DOC", "DA_TAO", "DA_TAO_NHAP", True),
            ("GIU_TAI", "DA_TAO_NHAP", "DA_TAO_NHAP", True), ("GHI_TAI", "DA_TAO_NHAP", "CHO_QUET", True),
            ("GIU_DOI_SOAT", "CHO_QUET", "CHO_QUET", True), ("GHI_DOI_SOAT", "CHO_QUET", "CHO_QUET", True),
            ("GIU_DOC", "CHO_QUET", "CHO_QUET", True), ("GHI_DOC", "CHO_QUET", "CHO_QUET", True),
            ("GIU_DOI_SOAT", "CHO_QUET", "CHO_QUET", True), ("GHI_DOI_SOAT", "CHO_QUET", "DA_DOI_SOAT", True)])
        self.assertEqual(self.q("SELECT count(*) FROM m4.request_bien_nhan WHERE y_dinh_id = %s", (y["id"],)), 2)
        # phát lại cùng khóa: không POST mới; cùng khóa khác hành động → từ chối
        n_post = fake.dem("POST", r"/api/v1/.*")
        r = self.tao(h, fake, "A-tao")
        self.assertEqual((r["trang_thai"], r["lap_lai"], fake.dem("POST", r"/api/v1/.*")), ("DA_DOI_SOAT", True, n_post))
        self.assertEqual(self.loi(self.doi_soat, h, fake, "A-tao"), "M4_IDEMPOTENCY_KHAC")
        # đọc qua RLS login ứng dụng
        v = self.rq(h, fake).xem(A1, dot_id=h["dot"])
        self.assertEqual((v["quyen"], v["cau_hinh"]["trang_thai"], len(v["y_dinh"]), v["y_dinh"][0]["trang_thai"]),
                         ({"tao": True, "tai_pdf": True, "anh_xa": True}, "SAN_SANG", 1, "DA_DOI_SOAT"))
        self.assertEqual(len(v["y_dinh"][0]["su_kien"]), 13 + 2)  # lần phát lại: TAO không nhận (không sự kiện) → GIU_DOC + GHI_DOC quan sát
        self.assertNotIn("canonical", v["y_dinh"][0])
        self.s["A_xong"] = str(y["id"])

    # ------------------------------------------------------------------ Q03
    def test_q03_mat_ack_xoay_khoa_khoi_dong(self):
        self.can("ax1")
        h = self.ho_so("C")
        dh = DongHo()
        fake = FakeRequest(dh)
        fake.tiem("POST_DE_XUAT", "MAT_ACK")
        r = self.tao(h, fake, "C-1")
        self.assertEqual(r["trang_thai"], "CHUA_RO_TAO")
        y = self.y(h)
        self.assertEqual((y["trang_thai"], y["co_chua_ro"], y["remote_id"], y["so_lan_tao"]), ("CHUA_RO_TAO", True, None, 1))
        self.assertEqual(len(fake.de_xuat), 1)
        # xoay khóa: căn cứ đổi → HOLD, 0 POST
        fake.khoa_api = "k2"
        r = self.doi_soat(h, fake, "C-xoay", ch=cau_hinh_pg(h["pn"], khoa_ref="khoa-demo:2"))
        self.assertEqual((r["trang_thai"], r["chan"], fake.dem("POST", "/api/v1/de-xuat")), ("HOLD", "CAN_CU_DOI", 1))
        fake.khoa_api = "k1"
        # tiến trình chết sau khi nguồn nhận (lease 5 giây) → còn lease: DANG_XU_LY; hết lease: chưa rõ → gửi lại cùng key
        fake.tiem("POST_DE_XUAT", "SAP")
        with self.assertRaises(SapTienTrinh):
            self.doi_soat(h, fake, "C-2", lease_giay=5)
        self.assertEqual(self.y(h)["lease_buoc"], "TAO")
        self.assertEqual(self.loi(self.doi_soat, h, fake, "C-3"), "M4_REQUEST_DANG_XU_LY")
        time.sleep(6)
        svc_moi = self._svc_moi()  # "khởi động lại": kết nối/service mới
        r = self.rq(h, fake, svc=svc_moi).doi_soat(A1, dot_id=h["dot"], version_id=h["pb"], khoa=self.K("C-4"))
        self.assertEqual(r["trang_thai"], "CHO_QUET")
        self.assertEqual(len(fake.de_xuat), 1)
        y = self.y(h)
        self.assertEqual((str(y["remote_id"]), y["so_lan_tao"]), (next(iter(fake.de_xuat)), 3))
        self.assertIn(("LEASE_HET", "CHUA_RO_TAO", "CHUA_RO_TAO", True), self.su_kien(h))
        keys = {hd["Idempotency-Key"] for p, d, hd in fake.nhat_ky if p == "POST" and d == "/api/v1/de-xuat"}
        self.assertEqual(keys, {f"m4-request:{y['id']}"})

    # ------------------------------------------------------------------ Q04
    def test_q04_dong_thoi_hash(self):
        self.can("ax1")
        h = self.ho_so("D")
        fake = FakeRequest(DongHo())
        svc2 = self._svc_moi()
        kq = {}

        def chen(_fake):  # lệnh thứ hai, kết nối khác, đúng lúc lệnh một đang ở HTTP (ngoài giao dịch)
            kq["ma"] = self.loi(lambda: self.rq(h, fake, svc=svc2).tao(A1, dot_id=h["dot"], version_id=h["pb"], khoa=self.K("D-2")))
        fake.tiem("POST_DE_XUAT", chen)
        r = self.tao(h, fake, "D-1")
        self.assertEqual((kq["ma"], r["trang_thai"], len(fake.de_xuat)), ("M4_REQUEST_DANG_XU_LY", "CHO_QUET", 1))
        self.assertEqual(self.q("SELECT count(*) FROM m4.request_y_dinh WHERE seal_id = %s", (h["seal"],)), 1)
        self.assertEqual(self.q("SELECT count(*) FROM m4.request_bien_nhan WHERE khoa = %s", (self.K("D-2"),)), 0)  # raise → rollback biên nhận
        x = next(iter(fake.de_xuat.values()))
        t = fake.tep[x["tep"][0]]
        t["bytes"] = bytes([t["bytes"][0] ^ 1]) + t["bytes"][1:]
        fake.quet(t["meta"]["id"], "clean")
        r = self.doi_soat(h, fake, "D-3")
        y = self.y(h)
        self.assertEqual((r["trang_thai"], y["trang_thai"], y["hold_ma"], y["doi_soat_sha256"]), ("HOLD", "HOLD", "TEP_HASH_LECH", None))
        self.s["D"] = h

    # ------------------------------------------------------------------ Q05
    def test_q05_bypass_bat_bien_pham_vi(self):
        self.can("A_xong")
        h = self.s["A"]
        for sql in ("SELECT m4.request_giu('k', 'REQUEST_TAO', '{}'::jsonb, gen_random_uuid(), gen_random_uuid(), '{}'::jsonb, NULL, 'TAO', 60)",
                    "SELECT m4.request_ghi(gen_random_uuid(), gen_random_uuid(), 1, '{}'::jsonb)",
                    "SELECT m4.request_anh_xa_dat(gen_random_uuid(), gen_random_uuid(), 'x', 'y')",
                    "INSERT INTO m4.request_bien_nhan (nguoi_dung_id, khoa, hanh_dong, yeu_cau) VALUES (gen_random_uuid(), 'k', 'REQUEST_TAO', '{}')",
                    "UPDATE m4.request_y_dinh SET hold_ma = 'X'"):
            with self.subTest(sql=sql[:40]):
                with self.assertRaises(psycopg.Error) as cm:
                    self.web_raw.execute(sql)
                self.assertIsInstance(cm.exception, psycopg.errors.InsufficientPrivilege)
        truoc = self.y(h)
        for sql, ma in (("UPDATE m4.request_y_dinh SET so_tien = '1' WHERE id = %s", "M4_BAT_BIEN"),
                        ("UPDATE m4.request_y_dinh SET remote_id = gen_random_uuid(), revision = revision + 1 WHERE id = %s", "M4_BAT_BIEN"),
                        ("UPDATE m4.request_y_dinh SET trang_thai = 'MOI', revision = revision + 1 WHERE id = %s", "M4_BAT_BIEN")):
            with self.subTest(sql=sql[:50]):
                with self.assertRaises(psycopg.Error) as cm:
                    with self.admin.transaction(force_rollback=True):
                        self.admin.execute(sql, (truoc["id"],))
                self.assertEqual((getattr(cm.exception.diag, "message_primary", "") or "").split(":", 1)[0], ma)
        self.assertEqual(self.y(h), truoc)
        fake = FakeRequest(DongHo())
        self.assertEqual(self.loi(self.tao, h, fake, "A-xem", login=XEM), "M4_REQUEST_PHAM_VI")
        for ai in (A2, B1):
            self.assertEqual(self.loi(self.tao, h, fake, f"A-{ai}", login=ai), "M4_REQUEST_KHONG_THAY")
            self.assertEqual(self.loi(lambda: self.rq(h, fake).xem(ai, dot_id=h["dot"])), "M4_REQUEST_KHONG_THAY")
        self.assertEqual(fake.nhat_ky, [])
        v = self.rq(h, fake).xem(XEM, dot_id=h["dot"])
        self.assertEqual((v["quyen"], v["cau_hinh"]), ({"tao": False, "tai_pdf": False, "anh_xa": False}, None))
        # RLS kỹ thuật: login app không có GUC danh tính → không thấy hàng nào
        self.assertEqual(_q1(self.web_raw, "SELECT count(*) FROM m4.request_y_dinh"), 0)
        self.assertEqual(_q1(self.web_raw, "SELECT count(*) FROM m4.request_anh_xa"), 0)

    # ------------------------------------------------------------------ Q06 (cuối — thu hồi không đảo ngược)
    def test_q06_thu_hoi_hien_hanh(self):
        self.can("ax1", "A_xong")
        h = self.ho_so("E")
        fake = FakeRequest(DongHo())
        svc2 = self._svc_moi()

        def thu_hoi(_fake):
            thu_hoi_anh_xa(svc2, A1, self.s["ax1"])
        fake.tiem("POST_DE_XUAT", thu_hoi)
        self.assertEqual(self.loi(self.tao, h, fake, "E-1"), "M4_REQUEST_PHAM_VI_DA_DOI")
        y = self.y(h)
        self.assertEqual((y["trang_thai"], str(y["remote_id"])), ("DA_TAO", next(iter(fake.de_xuat))))  # bằng chứng đã ghi
        self.assertEqual(self.su_kien(h)[-1], ("GHI_TAO", "MOI", "DA_TAO", False))
        n = len(fake.nhat_ky)
        r = self.doi_soat(h, fake, "E-2")
        self.assertEqual((r["trang_thai"], r["thieu"], len(fake.nhat_ky)), ("CHUA_CAU_HINH", ["anh_xa_nhan_vien"], n))
        ax2 = dat_anh_xa(self.svc, A1, h["pn"], NV)
        self.assertEqual(ax2["revision"], 2)
        r = self.doi_soat(h, fake, "E-3")
        self.assertEqual((r["trang_thai"], r["chan"], fake.dem("POST", r"/api/v1/de-xuat/.*/tep")), ("HOLD", "ANH_XA_DOI", 0))
        a = self.s["A"]
        r = self.doi_soat(a, FakeRequest(DongHo()), "A-sau-thu-hoi")
        self.assertEqual((r["trang_thai"], r["canh_bao"]), ("DA_DOI_SOAT", "ANH_XA_DOI"))
        self.assertEqual(self.y(a)["trang_thai"], "DA_DOI_SOAT")


if __name__ == "__main__":
    unittest.main()
