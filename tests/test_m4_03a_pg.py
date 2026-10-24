"""M4-03A — kiểm PostgreSQL THẬT cho inbox/xác nhận kế toán (KeToanNghiemThuK2). CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

KHÔNG tạo CSDL, KHÔNG migrate, KHÔNG apply SQL M4-03A, KHÔNG seed/cấp quyền/khôi phục quyền, KHÔNG M9/full bootstrap. Chạy DUY NHẤT trên một CLONE
DEMO SỞ HỮU do Root chuẩn bị: registry đã nối `sql_ke_toan_nghiem_thu.M4_03A_SQL` ở ordinal Root cấp, clone đã migrate tới ordinal đó, các login
DEMO đã có vai dự án. Cấp qua env lúc chạy (không .env/var, không hardcode DSN/credentials, không in DSN):
  KHO_M4_03A_CLONE_DSN         DSN chủ bảng (owner) của clone — đường tin cậy của máy chủ
  KHO_M4_03A_CLONE_APP_DSN     DSN login ứng dụng có sẵn (IN ROLE app_web, NOSUPERUSER, NOBYPASSRLS) — test KHÔNG tạo role
  KHO_M4_03A_CLONE_DB          tên CSDL clone mong đợi (bắt đầu 'kho_test_')
  KHO_M4_03A_CLONE_PROVENANCE  giá trị master.he_thong['m4_03a_clone_provenance'] Root ghi khi dựng clone
  KHO_M4_03A_M24_SHA256        checksum M0024 Root ghim
  KHO_M4_03A_VERSION           ordinal Root cấp cho M4_03A_SQL (số nguyên > 24)
  KHO_M4_03A_SHA256            checksum M4_03A_SQL Root ghim (= master.schema_migrations[ordinal])
  KHO_M4_03A_KT1 / _KT2        hai login DEMO mo_phong, vai trò KE_TOAN/KE_TOAN_TRUONG, vai dự án KE_TOAN hiện hành trên DA_XD_A1
  KHO_M4_03A_KT_KHAC           login DEMO mo_phong vai trò kế toán nhưng KHÔNG có vai dự án KE_TOAN trên DA_XD_A1
Không env nào → SkipTest 'NOT_VERIFIED' (không phải PASS). Thiếu một phần / clone, registry, checksum, provenance, DEMO hoặc quyền hiện hành không chứng
minh được → LỖI THIẾT LẬP (setUpClass raise) TRƯỚC mọi ghi. Cổng CHỈ ĐỌC; test không cấp/khôi phục vai nào — thiếu → cần clone mới.

Producer: hồ sơ/đợt DEMO MỚI qua lệnh M24 THẬT (dung_ho_so → kết luận REVIEW → chấp thuận DUYET → PDF SOAN ⇒ DA_SEAL, gốc + phong bì do M24 tạo).
Không INSERT giả duyệt/seal/phong bì/revision KT. Mọi lệnh KT qua KeToanNghiemThuK2 thật (login app đọc; kết nối owner + GUC danh tính ghi).
Mọi ca đo delta TOÀN BỘ bảng (đếm chính xác qua owner): lệnh KT chỉ được thêm m4.kt_xac_nhan + m4.bien_nhan + m4.nhat_ky; không AP/sổ cái/Request/M24.

Ánh xạ ca thiết kế (docs/M4-03A-FIXTURE-DESIGN-01.md):
P01 kt=null ban đầu (gốc A)            P02 nháp null vs "0" (gốc C)           P03 CO_CAN_CU thật xem→luu→xac_nhan (gốc A)
P04 KHONG_AP_DUNG thật + thiếu lý do (gốc B)                                  P05 căn cứ VAT ngoài tập ứng viên (gốc C)
P06 CAS revision/SHA (gốc C)           P07a = thiết kế P08: phiên bản kế tiếp chưa seal (gốc A)
P07b = thiết kế P07: hai phong bì cùng gốc, lịch sử, A chỉ đọc, kt của B không mượn A
P08 bypass SQL login app               P09 lịch sử KT chỉ ghi thêm             P11 replay/khác body/đồng thời (gốc D)
P12 phạm vi/vai/chéo gốc               P99 = thiết kế P10 (CUỐI, không đảo ngược): thu hồi KE_TOAN của KT2 → đọc/PDF/lệnh/replay bị chặn, 0 delta.
Phần SAI_DTO/thiếu metadata (thiết kế P05/P06 phía boundary) nằm ở tests/test_m4_03a_tinh.py (khung tay có nhãn, không tính producer PASS).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
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

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from kho_tri_thuc.m4 import ke_toan_nghiem_thu as KT
from kho_tri_thuc.m4 import sql_ke_toan_nghiem_thu as SK
from tests.test_m4_02c_pg import A1, A2, B1, DUYET, REVIEW, XEM, _q1, dung_ho_so, than_ket_luan

ENV_CHU, ENV_APP, ENV_DB, ENV_NGUON, ENV_M24 = ("KHO_M4_03A_CLONE_DSN", "KHO_M4_03A_CLONE_APP_DSN", "KHO_M4_03A_CLONE_DB",
                                                "KHO_M4_03A_CLONE_PROVENANCE", "KHO_M4_03A_M24_SHA256")
ENV_VER, ENV_SHA, ENV_KT1, ENV_KT2, ENV_KT_KHAC = ("KHO_M4_03A_VERSION", "KHO_M4_03A_SHA256", "KHO_M4_03A_KT1", "KHO_M4_03A_KT2",
                                                   "KHO_M4_03A_KT_KHAC")
ENV = (ENV_CHU, ENV_APP, ENV_DB, ENV_NGUON, ENV_M24, ENV_VER, ENV_SHA, ENV_KT1, ENV_KT2, ENV_KT_KHAC)
KHOA_NGUON = "m4_03a_clone_provenance"
TIEN_TO_DB = "kho_test_"
CO_ENV = any(os.environ.get(k) for k in ENV)
LY_DO_SKIP = "NOT_VERIFIED: chưa cấp clone DEMO sở hữu đã nối M4-03A (KHO_M4_03A_*) — test M4-03A PG không chạy, KHÔNG tính đạt"
DUOC_GHI = ("m4.kt_xac_nhan", "m4.bien_nhan", "m4.nhat_ky")  # bảng DUY NHẤT lệnh KT được thêm hàng
SO_NGUON = F.KET_LUAN_VND  # số nguồn đã seal của mọi hồ sơ test (VND, giu_lai 1750000, tam_ung/thu_hoi "0")
TRICH = "HĐ DEMO Điều 3.1: giá trị hợp đồng chưa bao gồm thuế GTGT"
LY_DO_NA = "Đợt DEMO không phát sinh hóa đơn GTGT — kế toán đã đối chiếu hồ sơ"


class LoiThietLap(Exception):
    """SETUP_FAILURE / NOT_VERIFIED: clone/registry/quyền không chứng minh được — dừng TRƯỚC mọi ghi. Thông điệp không chứa DSN."""


def cau_hinh_clone() -> dict:
    gia_tri = {k: os.environ.get(k) or "" for k in ENV}
    thieu = [k for k, v in gia_tri.items() if not v]
    if thieu:
        raise LoiThietLap("SETUP_FAILURE: cấu hình clone dở dang — thiếu " + ", ".join(thieu))
    if psycopg is None:
        raise LoiThietLap("SETUP_FAILURE: thiếu driver psycopg")
    for k in (ENV_M24, ENV_SHA):
        if not re.fullmatch(r"[0-9a-f]{64}", gia_tri[k]):
            raise LoiThietLap(f"SETUP_FAILURE: {k} phải là SHA-256 hex thường")
    if not re.fullmatch(r"[0-9]{2,4}", gia_tri[ENV_VER]) or int(gia_tri[ENV_VER]) <= 24:
        raise LoiThietLap(f"SETUP_FAILURE: {ENV_VER} phải là ordinal Root cấp (> 24) — test không đoán ordinal")
    if len({gia_tri[ENV_KT1], gia_tri[ENV_KT2], gia_tri[ENV_KT_KHAC]} | {A1, A2, B1, REVIEW, XEM, DUYET}) != 9:
        raise LoiThietLap("SETUP_FAILURE: KT1/KT2/KT_KHAC phải là ba login riêng, khác login M24 DEMO")
    return gia_tri


def kiem_clone(chu, web, cfg: dict) -> dict:
    """Cổng CHỈ ĐỌC trước mọi ghi: clone DEMO + lineage + registry M4_03A đúng ordinal/checksum + quyền DEMO hiện hành đã có sẵn (không seed)."""
    from kho_tri_thuc.ha_tang import pg_migrations as PGM
    from kho_tri_thuc.ha_tang import postgres as pg
    from kho_tri_thuc.k2 import crm_demo, m4_demo
    from kho_tri_thuc.m4.sql_duyet import M0024_M4_DUYET

    def sai(ly_do):
        raise LoiThietLap("SETUP_FAILURE: " + ly_do + " — không ghi gì; Root cấp clone DEMO sở hữu đã nối M4-03A")
    db = _q1(chu, "SELECT current_database()")
    if db != cfg[ENV_DB] or not str(db).startswith(TIEN_TO_DB):
        sai(f"CSDL kết nối owner không phải clone mong đợi (phải = {ENV_DB} và bắt đầu '{TIEN_TO_DB}')")
    if _q1(web, "SELECT current_database()") != db:
        sai("login ứng dụng không trỏ cùng CSDL clone")
    r = web.execute("""SELECT r.rolsuper, r.rolbypassrls, pg_has_role(current_user, 'app_web', 'MEMBER')
                       FROM pg_roles r WHERE r.rolname = current_user""").fetchone()
    if tuple(r.values() if isinstance(r, dict) else (r or ())) != (False, False, True):
        sai("login ứng dụng phải IN ROLE app_web, NOSUPERUSER, NOBYPASSRLS")
    for bang in ("m4.duyet_kt_phong_bi", "m4.kt_xac_nhan"):
        if _q1(chu, "SELECT to_regclass(%s) IS NOT NULL", (bang,)) is not True:
            sai(f"clone chưa có {bang}")
        if _q1(chu, "SELECT pg_has_role(current_user, c.relowner, 'MEMBER') FROM pg_class c WHERE c.oid = %s::regclass", (bang,)) is not True:
            sai(f"kết nối owner không sở hữu {bang}")
    try:
        version = pg.kiem_lineage_ung_dung(chu)  # checksum 1..N khớp chuỗi phần mềm + N = PG_SCHEMA_VERSION
    except DataError as exc:
        sai(f"lineage không khớp ({exc.code})")
    n = int(cfg[ENV_VER])
    ck24 = hashlib.sha256("\n".join(M0024_M4_DUYET).encode()).hexdigest()
    ckn = hashlib.sha256("\n".join(SK.M4_03A_SQL).encode()).hexdigest()
    if not (version == PGM.PG_SCHEMA_VERSION == len(PGM.PG_MIGRATIONS) and version >= n):
        sai("schema clone ≠ registry phần mềm")
    if tuple(PGM.PG_MIGRATIONS[23]) != tuple(M0024_M4_DUYET) or tuple(PGM.PG_MIGRATIONS[n - 1]) != tuple(SK.M4_03A_SQL):
        sai(f"registry không có M0024 ở 24 và M4_03A_SQL ở {n}")
    if not (_q1(chu, "SELECT checksum FROM master.schema_migrations WHERE version = 24") == ck24 == cfg[ENV_M24]):
        sai("checksum M0024 trong clone ≠ định nghĩa hiện tại ≠ giá trị Root ghim")
    if not (_q1(chu, "SELECT checksum FROM master.schema_migrations WHERE version = %s", (n,)) == ckn == cfg[ENV_SHA]):
        sai("checksum M4_03A trong clone ≠ định nghĩa hiện tại ≠ giá trị Root ghim")
    he = dict(chu.execute("SELECT key, value FROM master.he_thong WHERE key = ANY(%s)",
                          ([pg.APP_MARKER_KEY, crm_demo.MARKER, m4_demo.MARKER, KHOA_NGUON],)).fetchall())
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

    def co_vai(login, vai, *, vai_tro=None) -> bool:
        return _q1(chu, """SELECT EXISTS (SELECT 1 FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                                          JOIN master.du_an d ON d.id = q.du_an_id
                                          WHERE d.ma_junsky = 'DA_XD_A1' AND n.dang_nhap = %s AND q.vai = %s AND q.thu_hoi_luc IS NULL
                                            AND n.trang_thai = 'HOAT_DONG' AND n.mo_phong AND (%s::text[] IS NULL OR n.vai_tro = ANY(%s::text[])))""",
                   (login, vai, vai_tro, vai_tro)) is True
    for k in (ENV_KT1, ENV_KT2):
        if not co_vai(cfg[k], SK.VAI_KT, vai_tro=list(SK.VAI_TRO_KT)):
            sai(f"{k} chưa có vai dự án KE_TOAN hiện hành + vai trò kế toán trên DA_XD_A1 (clone đã dùng cho ca thu hồi?) — cần clone mới")
    if co_vai(cfg[ENV_KT_KHAC], SK.VAI_KT):
        sai(f"{ENV_KT_KHAC} không được có vai dự án KE_TOAN trên DA_XD_A1")
    if _q1(chu, "SELECT count(*) FROM master.nguoi_dung WHERE dang_nhap = %s AND trang_thai = 'HOAT_DONG' AND mo_phong",
           (cfg[ENV_KT_KHAC],)) != 1:
        sai(f"{ENV_KT_KHAC} phải là login DEMO hoạt động")
    for login, vai in ((REVIEW, "REVIEW"), (DUYET, "DUYET")):
        if not co_vai(login, vai):
            sai(f"{login} chưa có vai {vai} hiện hành (producer M24 cần) — test không tự cấp")
    return {"trang_thai": "CLONE_DEMO_DA_KIEM", "schema": version, "ordinal_m4_03a": n, "m4_03a_sha256": ckn}


@unittest.skipUnless(CO_ENV, LY_DO_SKIP)
class M4KeToanPG(unittest.TestCase):
    """Chạy theo thứ tự tên p01…p12, p99 trên MỘT clone; trạng thái qua cls.s. P99 thu hồi KE_TOAN của KT2 (không đảo ngược) — clone sau đó không
    dùng lại cho bộ này."""

    @classmethod
    def setUpClass(cls):
        import tests.test_m4_02b_k2 as K2B  # module (không import lớp TestCase)
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        cfg = cau_hinh_clone()
        cls.cfg = cfg
        cls.KT1, cls.KT2, cls.KT_KHAC = cfg[ENV_KT1], cfg[ENV_KT2], cfg[ENV_KT_KHAC]
        cls.admin = psycopg.connect(cfg[ENV_CHU], autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        web0 = psycopg.connect(cfg[ENV_APP], autocommit=True)
        cls.addClassCleanup(web0.close)
        cls.web_raw = web0
        cls.gate = kiem_clone(cls.admin, web0, cfg)  # CHỈ ĐỌC — sai → LoiThietLap, chưa ghi gì
        from tests.test_m4_02b_pure import _docx, openpyxl
        if not (K2B._nguon_da_nap() and openpyxl is not None and _docx is not None):
            raise unittest.SkipTest("NOT_RUN: lõi nguồn Review chưa nạp hoặc thiếu openpyxl/python-docx — không dựng được hồ sơ producer")
        cls.goc = Path(tempfile.mkdtemp(prefix="ktt_m4_03a_pg_"))  # DataRoot DEMO của lượt — giữ lại
        cls.run_id = uuid.uuid4().hex[:8]
        cls.trich6, cls.gate6 = K2B.M4ChungTuPG._gate_trich6.__func__(cls)
        cls.XayDungK2 = XayDungK2
        cls.svc = cls._svc_moi()
        cls.kt = KT.KeToanNghiemThuK2(cls.svc)
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
        return f"m4kt-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return _q1(self.admin, sql, params)

    @staticmethod
    def ma(exc) -> str:
        if isinstance(exc, DataError):
            return exc.code
        if psycopg is not None and isinstance(exc, psycopg.Error):
            p = (getattr(exc.diag, "message_primary", "") or "").split(":", 1)[0]
            return p if re.fullmatch(r"[A-Z][A-Z0-9_]*", p) else type(exc).__name__
        return type(exc).__name__

    def loi(self, fn, *a, **k) -> str:
        try:
            fn(*a, **k)
        except (DataError, psycopg.Error) as exc:
            return self.ma(exc)
        self.fail("thao tác không bị chặn")

    def song_song(self, viec) -> tuple[list, list]:
        kq, loi = [], []

        def mot(fn):
            try:
                kq.append(fn())
            except BaseException as exc:  # noqa: BLE001
                loi.append(self.ma(exc))
        ts = [threading.Thread(target=mot, args=(fn,), daemon=True) for fn in viec]
        try:
            for t in ts:
                t.start()
        finally:
            for t in ts:
                t.join(600)
        self.assertEqual([t.is_alive() for t in ts], [False] * len(ts), "luồng đồng thời không kết thúc trong hạn")
        return kq, loi

    def can(self, *khoa):
        for k in khoa:
            if k not in self.s:
                self.skipTest(f"ca trước chưa dựng '{k}' — NOT_RUN")

    def dem_tat_ca(self) -> dict:
        """Đếm CHÍNH XÁC mọi bảng người dùng (owner, mọi schema ngoài catalog) — oracle 0 delta tài chính/M24/AP/Request."""
        bang = self.admin.execute(r"""SELECT format('%I.%I', n.nspname, c.relname) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                                      WHERE c.relkind IN ('r', 'p') AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                                        AND n.nspname NOT LIKE 'pg\_%' AND has_table_privilege(c.oid, 'SELECT') ORDER BY 1""").fetchall()
        return {t: self.q(f"SELECT count(*) FROM {t}") for (t,) in bang}

    def doi(self, truoc: dict, **mong):
        """Delta thực tế phải ĐÚNG bằng mong (tên 'schema__bang' → số hàng thêm); mọi bảng khác 0 delta."""
        sau = self.dem_tat_ca()
        thuc = {t: sau.get(t, 0) - truoc.get(t, 0) for t in set(truoc) | set(sau) if sau.get(t, 0) != truoc.get(t, 0)}
        self.assertEqual(thuc, {k.replace("__", "."): v for k, v in mong.items() if v})
        self.assertTrue(set(thuc) <= set(DUOC_GHI), thuc)

    def ghi_mot(self, truoc):
        self.doi(truoc, m4__kt_xac_nhan=1, m4__bien_nhan=1, m4__nhat_ky=1)

    def chap_thuan(self, dot, khoa, login=DUYET):
        x = self.svc.duyet_xem(login, dot_id=dot, version_id=None)
        c = x["context"]
        return self.svc.duyet_chap_thuan(login, dot_id=dot, version_id=c["version_id"], revision=c["revision"], expected_basis=c["basis_sha256"],
                                         ket_luan_id=x["ket_luan"]["id"], ly_do="Chấp thuận hồ sơ đợt DEMO", khoa=self.K(khoa))

    def ket_luan(self, dot, khoa):
        return self.svc.duyet_ket_luan(REVIEW, **than_ket_luan(self.svc.duyet_xem(REVIEW, dot_id=dot, version_id=None)), khoa=self.K(khoa))

    def pdf(self, dot, raw, khoa, ten):
        c = self.svc.duyet_xem(A1, dot_id=dot, version_id=None)["context"]
        return self.svc.duyet_pdf(A1, raw, dot_id=dot, version_id=c["version_id"], revision=c["revision"], expected_basis=c["basis_sha256"],
                                  ten=ten, media_type="application/pdf", khoa=self.K(khoa))

    def ho_so_seal(self, nhan) -> dict:
        """Producer THẬT: hồ sơ DEMO mới → kết luận (REVIEW) → chấp thuận (DUYET) → [chưa có gốc KT] → PDF (SOAN) ⇒ DA_SEAL + gốc + phong bì M24."""
        h = dung_ho_so(self.svc, self.admin, self.K, nhan, self.run_id)
        dot = str(h["dot"])
        self.ket_luan(dot, f"{nhan}-kl")
        self.assertEqual(self.chap_thuan(dot, f"{nhan}-ct")["trang_thai"], "CHO_PDF")
        self.assertEqual(self.q("SELECT count(*) FROM m4.duyet_kt_cho WHERE dot_id = %s", (dot,)), 0)  # chưa PDF → chưa gốc KT
        self.assertNotIn(dot, [r["dot_id"] for r in self.kt.danh_sach(self.KT1)["items"]])
        raw = F.ho_so_dot_duyet_pdf(f"KT-{self.run_id}-{nhan}-1")
        ten = f"ho_so_da_duyet_{nhan}.pdf"
        p = self.pdf(dot, raw, f"{nhan}-pdf", ten)
        self.assertEqual(p["trang_thai"], "DA_SEAL", p)
        v1 = self.svc.duyet_xem(A1, dot_id=dot, version_id=None)["context"]["version_id"]
        return {**h, "dot": dot, "cho": str(p["kt_pending_id"]), "pdf_id": str(p["pdf_id"]), "raw": raw, "ten_pdf": ten, "v1": v1}

    def phong_bi(self, cho) -> list:
        r = self.admin.execute("""SELECT id::text, noi_dung_sha256, noi_dung, seal_id::text, thu_tu, truoc_id::text, phien_ban_id::text
                                  FROM m4.duyet_kt_phong_bi WHERE cho_id = %s ORDER BY thu_tu""", (cho,)).fetchall()
        return [dict(zip(("id", "sha", "noi_dung", "seal_id", "thu_tu", "truoc_id", "phien_ban_id"), x)) for x in r]

    def kt_db(self, cho) -> list:
        r = self.admin.execute("SELECT to_jsonb(x) FROM m4.kt_xac_nhan x WHERE cho_id = %s ORDER BY revision", (cho,)).fetchall()
        return [x[0] for x in r]

    def xem(self, cho, login=None, pb=None):
        return self.kt.xem(login or self.KT1, kt_pending_id=cho, phong_bi_id=pb)

    @staticmethod
    def than_luu(x, khoa, **du):
        c = x["context"]
        nen = {k: None for k in KT.DU_LIEU} | {"co_so_gia_tri": "CHUA_RO", "vat_trang_thai": "CHUA_DU"}
        return {"kt_pending_id": c["kt_pending_id"], "phong_bi_id": c["phong_bi_id"], "expected_phong_bi_sha256": c["phong_bi_sha256"],
                "expected_revision": 0 if x["kt"] is None else x["kt"]["revision"], **nen, **du, "khoa": khoa}

    @staticmethod
    def than_xn(x, khoa):
        c, k = x["context"], x["kt"]
        return {"kt_pending_id": c["kt_pending_id"], "phong_bi_id": c["phong_bi_id"], "kt_revision_id": k["kt_revision_id"],
                "expected_revision": k["revision"], "expected_phong_bi_sha256": c["phong_bi_sha256"], "khoa": khoa}

    @staticmethod
    def du_day(vat, **them) -> dict:
        """Số KT đủ điều kiện (KT tự nhập — bằng số nguồn ở đây chỉ vì kế toán xác nhận cùng số; máy chủ không copy)."""
        return {"gia_tri_nt_xac_nhan": SO_NGUON["gia_tri_nt"], "tien_te": "VND", "co_so_gia_tri": "TRUOC_VAT",
                "tam_ung_xac_nhan": SO_NGUON["tam_ung"], "thu_hoi_xac_nhan": SO_NGUON["thu_hoi"], "giu_lai_xac_nhan": SO_NGUON["giu_lai"],
                "vat_trang_thai": vat, **them}

    def kiem_ack(self, a, *, khoa, revision, trang_thai, lap_lai, hanh_dong):
        self.assertTrue(set(KT.ACK_KEYS) <= set(a), a)
        self.assertEqual((a["schema"], a["revision"], a["trang_thai"], a["lap_lai"], a["hanh_dong"], a["khoa"]),
                         (KT.SCHEMA, revision, trang_thai, lap_lai, hanh_dong, khoa))
        self.assertEqual((a["ap"], a["request"]), (KT.AP, KT.REQUEST))
        self.assertEqual(self.q("SELECT id::text FROM m4.bien_nhan WHERE khoa = %s AND hanh_dong = %s",
                                (khoa, "KT_LUU" if hanh_dong == "LUU" else "KT_XAC_NHAN")), a["receipt_id"])
        json.dumps(a, ensure_ascii=False)

    def kiem_xem(self, x, h, pb: dict):
        """DTO xem khớp ĐÚNG dữ liệu M24 trong CSDL (đọc độc lập qua owner) — không DTO gương."""
        self.assertEqual(tuple(x), KT.XEM_KEYS)
        self.assertIn("kt", x)
        c, nd = x["context"], pb["noi_dung"]
        self.assertEqual((c["kt_pending_id"], c["dot_id"], c["du_an_id"], c["hop_dong_id"], c["phong_bi_id"], c["phong_bi_sha256"], c["seal_id"]),
                         (h["cho"], h["dot"], str(h["du_an"]), str(h["hd"]), pb["id"], pb["sha"], pb["seal_id"]))
        self.assertEqual((c["version_id"], c["ket_luan_id"], c["pdf_id"], c["pdf_sha256"]),
                         (nd["phien_ban_id"], nd["ket_luan_id"], nd["pdf"]["id"], nd["pdf"]["raw_sha256"]))
        n = x["nguon"]
        self.assertEqual(tuple(n), KT.NGUON_KEYS)
        for k in (*SK.TIEN, "tien_te", "dong"):
            self.assertEqual(n[k], nd.get(k), k)  # đúng giá trị phong bì, không copy thành KT
        self.assertEqual((n["pdf"]["id"], n["pdf"]["raw_sha256"], n["pdf"]["byte_length"], n["pdf"]["media_type"]),
                         (nd["pdf"]["id"], nd["pdf"]["raw_sha256"], nd["pdf"]["byte_length"], "application/pdf"))
        self.assertIsInstance(n["tep_can_cu"], list)
        for t in n["tep_can_cu"]:
            self.assertEqual(tuple(t), KT.TEP_KEYS)
            db = self.admin.execute("SELECT ten_goc, raw_sha256, media_type, byte_length, du_an_id::text, phap_nhan_id::text FROM m4.tep WHERE id = %s",
                                    (t["id"],)).fetchone()
            self.assertEqual((t["ten"], t["raw_sha256"], t["media_type"], t["byte_length"], db[4], db[5]),
                             (db[0], db[1], db[2], db[3], c["du_an_id"], c["phap_nhan_id"]))
        self.assertEqual((x["ap"], x["request"]), (KT.AP, KT.REQUEST))
        self.assertEqual(set(x["lich_su"]), {"phong_bi", "kt"})
        s = json.dumps(x, ensure_ascii=False)
        self.assertNotIn("object_key", s)

    # ------------------------------------------------------------------ P01 kt=null
    def test_p01_kt_null_ban_dau(self):
        self.assertGreater(self.gate["ordinal_m4_03a"], 24)
        h = self.ho_so_seal("A")
        pbs = self.phong_bi(h["cho"])
        self.assertEqual([(p["thu_tu"], p["truoc_id"]) for p in pbs], [(1, None)])
        self.assertEqual(self.q("SELECT count(*) FROM m4.duyet_kt_cho WHERE dot_id = %s", (h["dot"],)), 1)
        ds = [r for r in self.kt.danh_sach(self.KT1)["items"] if r["kt_pending_id"] == h["cho"]]
        self.assertEqual(ds, [{"kt_pending_id": h["cho"], "dot_id": h["dot"], "phong_bi_id": pbs[0]["id"], "phong_bi_sha256": pbs[0]["sha"],
                               "revision": None, "trang_thai": KT.TT_CHO_XAC_NHAN, "ap": KT.AP}])
        x = self.xem(h["cho"])
        self.kiem_xem(x, h, pbs[0])
        self.assertIsNone(x["kt"])  # explicit null — không {}, không UUID/revision 0 giả
        self.assertEqual(x["quyen"], {"xem": True, "luu": True, "xac_nhan": False, "tai_pdf": True})
        self.assertTrue(x["can_cu_hien_hanh"])
        self.assertEqual(x["lich_su"]["kt"], [])
        self.assertEqual([(r["thu_tu"], r["truoc_id"], r["phien_ban_so"], r["can_cu_hien_hanh"], r["context"]) for r in x["lich_su"]["phong_bi"]],
                         [(1, None, 1, True, x["context"])])
        self.assertTrue(x["nguon"]["tep_can_cu"], "không có ứng viên căn cứ VAT thật — nhánh CO_CAN_CU không dùng được (NOT_VERIFIED)")
        tep_hd = str(self.q("SELECT tep_hop_dong_id FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s", (h["hd"],)))
        self.assertIn(tep_hd, [t["id"] for t in x["nguon"]["tep_can_cu"]])
        self.assertNotIn(h["pdf_id"], [t["id"] for t in x["nguon"]["tep_can_cu"]])  # PDF hồ sơ đã duyệt không tự là căn cứ VAT
        self.assertEqual(self.kt.tep_pdf(self.KT1, h["cho"], pbs[0]["id"]), (h["ten_pdf"], "application/pdf", h["raw"]))
        self.assertEqual(self.kt_db(h["cho"]), [])
        # PDF lặp sau seal: M24 từ chối, vẫn MỘT gốc
        self.assertEqual(self.loi(self.pdf, h["dot"], F.ho_so_dot_duyet_pdf(f"KT-{self.run_id}-A-2"), "A-pdf-2", "x.pdf"), "M4_DUYET_DA_SEAL")
        self.assertEqual(self.q("SELECT count(*) FROM m4.duyet_kt_cho WHERE dot_id = %s", (h["dot"],)), 1)
        self.s["A"] = {**h, "pb1": pbs[0]}

    # ------------------------------------------------------------------ P02 nháp null vs "0"
    def test_p02_nhap_null_khac_0(self):
        h = self.ho_so_seal("C")
        x = self.xem(h["cho"])
        self.assertIsNone(x["kt"])
        truoc = self.dem_tat_ca()
        than = self.than_luu(x, self.K("C-luu-1"), gia_tri_nt_xac_nhan="35000000", tien_te="VND", tam_ung_xac_nhan=None, thu_hoi_xac_nhan="0",
                             giu_lai_xac_nhan="1000000")
        a = self.kt.luu(self.KT1, than)
        self.kiem_ack(a, khoa=than["khoa"], revision=1, trang_thai=KT.TT_CHO_BO_SUNG, lap_lai=False, hanh_dong="LUU")
        self.assertEqual(a["thieu"], ["CO_SO_CHUA_XAC_DINH", "LY_DO_KHAC_NGUON", "VAT_CHUA_DU"])
        self.ghi_mot(truoc)
        x2 = self.xem(h["cho"])
        k = x2["kt"]
        self.assertEqual(tuple(k), KT.KT_KEYS)
        self.assertEqual((k["kt_revision_id"], k["revision"], k["trang_thai"]), (a["kt_revision_id"], 1, KT.TT_CHO_BO_SUNG))
        self.assertEqual((k["tam_ung_xac_nhan"], k["thu_hoi_xac_nhan"], k["giu_lai_xac_nhan"]), (None, "0", "1000000"))  # NULL ≠ "0"
        self.assertEqual((x2["nguon"]["tam_ung"], x2["nguon"]["giu_lai"]), (SO_NGUON["tam_ung"], SO_NGUON["giu_lai"]))  # nguồn không bị đè
        self.assertEqual(x2["quyen"], {"xem": True, "luu": True, "xac_nhan": False, "tai_pdf": True})
        db = self.kt_db(h["cho"])
        self.assertEqual(len(db), 1)
        self.assertEqual((db[0]["tam_ung_xac_nhan"], db[0]["thu_hoi_xac_nhan"], db[0]["loai"], db[0]["revision"], db[0]["truoc_id"]),
                         (None, "0", "NHAP", 1, None))
        self.assertEqual(db[0]["tao_boi"], self.KT1)
        self.assertEqual([x["kt"]["revision"] for x in x2["lich_su"]["kt"]], [1])
        row = next(r for r in self.kt.danh_sach(self.KT1)["items"] if r["kt_pending_id"] == h["cho"])
        self.assertEqual((row["revision"], row["trang_thai"]), (1, KT.TT_CHO_BO_SUNG))
        self.s["C"] = h

    # ------------------------------------------------------------------ P03 CO_CAN_CU thật
    def test_p03_co_can_cu_xem_luu_xac_nhan(self):
        self.can("A")
        h = self.s["A"]
        x = self.xem(h["cho"])
        self.assertIsNone(x["kt"])
        tep = next(t for t in x["nguon"]["tep_can_cu"])  # id đúng từ mảng ứng viên máy chủ trả
        truoc = self.dem_tat_ca()
        than = self.than_luu(x, self.K("A-luu-1"), **self.du_day("CO_CAN_CU", vat_can_cu_tep_id=tep["id"], vat_trich_dan=TRICH))
        a = self.kt.luu(self.KT1, than)
        self.kiem_ack(a, khoa=than["khoa"], revision=1, trang_thai=KT.TT_CHO_XAC_NHAN, lap_lai=False, hanh_dong="LUU")
        self.assertEqual(a["thieu"], [])
        self.ghi_mot(truoc)
        db = self.kt_db(h["cho"])[0]
        self.assertEqual((db["vat_can_cu_tep_id"], db["vat_can_cu_sha256"], db["vat_trich_dan"], db["loai"]),
                         (tep["id"], tep["raw_sha256"], TRICH, "NHAP"))  # SHA máy chủ resolve từ m4.tep, không nhận từ trình duyệt
        x = self.xem(h["cho"])
        self.assertEqual((x["kt"]["revision"], x["kt"]["trang_thai"], x["kt"]["vat_can_cu_tep_id"]), (1, KT.TT_CHO_XAC_NHAN, tep["id"]))
        self.assertEqual(x["quyen"], {"xem": True, "luu": True, "xac_nhan": True, "tai_pdf": True})
        sha_pb = self.phong_bi(h["cho"])[0]["sha"]
        truoc = self.dem_tat_ca()
        bx = self.than_xn(x, self.K("A-xn-1"))
        xn = self.kt.xac_nhan(self.KT1, bx)
        self.kiem_ack(xn, khoa=bx["khoa"], revision=2, trang_thai=SK.TT_DA_XAC_NHAN, lap_lai=False, hanh_dong="XAC_NHAN")
        self.ghi_mot(truoc)  # 0 AP/sổ cái/Request/M24
        db = self.kt_db(h["cho"])
        self.assertEqual([(r["revision"], r["loai"]) for r in db], [(1, "NHAP"), (2, "XAC_NHAN")])
        self.assertEqual((db[1]["nhap_id"], db[1]["truoc_id"]), (db[0]["id"], db[0]["id"]))
        for k in (*KT.DU_LIEU, "vat_can_cu_sha256"):
            self.assertEqual(db[1][k], db[0][k], k)  # xác nhận sao y nháp đã lưu
        x = self.xem(h["cho"])
        self.assertEqual((x["kt"]["kt_revision_id"], x["kt"]["revision"], x["kt"]["trang_thai"]), (xn["kt_revision_id"], 2, SK.TT_DA_XAC_NHAN))
        self.assertEqual(x["quyen"], {"xem": True, "luu": False, "xac_nhan": False, "tai_pdf": True})
        self.assertEqual(x["ap"], {"trang_thai": "CHUA_TRIEN_KHAI_M4_03B", "da_ghi_cong_no": False})
        self.assertEqual([(r["kt"]["revision"], r["context"]["phong_bi_id"]) for r in x["lich_su"]["kt"]], [(1, x["context"]["phong_bi_id"]),
                                                                                                           (2, x["context"]["phong_bi_id"])])
        self.assertEqual(self.phong_bi(h["cho"])[0]["sha"], sha_pb)  # phong bì M24 không bị sửa
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.kt.luu, self.KT1, self.than_luu(x, self.K("A-luu-sau-xn"), **self.du_day("KHONG_AP_DUNG", ly_do=LY_DO_NA))),
                         "M4_KT_DA_XAC_NHAN")
        self.doi(truoc)
        self.s["A"].update(xn=xn, bx=bx, tep=tep)

    # ------------------------------------------------------------------ P04 KHONG_AP_DUNG thật
    def test_p04_khong_ap_dung(self):
        h = self.ho_so_seal("B")
        x = self.xem(h["cho"])
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.kt.luu, self.KT1, self.than_luu(x, self.K("B-na-tep"), **self.du_day(
            "KHONG_AP_DUNG", vat_can_cu_tep_id=x["nguon"]["tep_can_cu"][0]["id"], ly_do=LY_DO_NA))), "M4_KT_VAT_SAI")
        self.doi(truoc)
        than = self.than_luu(x, self.K("B-luu-1"), **self.du_day("KHONG_AP_DUNG"))  # thiếu lý do
        a = self.kt.luu(self.KT1, than)
        self.kiem_ack(a, khoa=than["khoa"], revision=1, trang_thai=KT.TT_CHO_BO_SUNG, lap_lai=False, hanh_dong="LUU")
        self.assertEqual(a["thieu"], ["VAT_LY_DO_THIEU"])
        x = self.xem(h["cho"])
        self.assertFalse(x["quyen"]["xac_nhan"])
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.kt.xac_nhan, self.KT1, self.than_xn(x, self.K("B-xn-thieu"))), "M4_KT_CHO_BO_SUNG")
        self.doi(truoc)  # HOLD: 0 xác nhận, 0 biên nhận
        than = self.than_luu(x, self.K("B-luu-2"), **self.du_day("KHONG_AP_DUNG", ly_do=LY_DO_NA))
        self.assertEqual(than["expected_revision"], 1)
        a = self.kt.luu(self.KT1, than)
        self.kiem_ack(a, khoa=than["khoa"], revision=2, trang_thai=KT.TT_CHO_XAC_NHAN, lap_lai=False, hanh_dong="LUU")
        x = self.xem(h["cho"])
        self.assertEqual((x["kt"]["vat_trang_thai"], x["kt"]["ly_do"], x["kt"]["vat_can_cu_tep_id"], x["quyen"]["xac_nhan"]),
                         ("KHONG_AP_DUNG", LY_DO_NA, None, True))
        bx = self.than_xn(x, self.K("B-xn"))
        truoc = self.dem_tat_ca()
        xn = self.kt.xac_nhan(self.KT1, bx)
        self.kiem_ack(xn, khoa=bx["khoa"], revision=3, trang_thai=SK.TT_DA_XAC_NHAN, lap_lai=False, hanh_dong="XAC_NHAN")
        self.ghi_mot(truoc)
        self.assertEqual([(r["revision"], r["loai"], r["nhap_id"]) for r in self.kt_db(h["cho"])],
                         [(1, "NHAP", None), (2, "NHAP", None), (3, "XAC_NHAN", a["kt_revision_id"])])
        self.s["B"] = h

    # ------------------------------------------------------------------ P05 căn cứ ngoài tập ứng viên
    def test_p05_can_cu_ngoai_pham_vi(self):
        self.can("A", "C")
        c, a = self.s["C"], self.s["A"]
        x = self.xem(c["cho"])
        ung_vien = {t["id"] for t in x["nguon"]["tep_can_cu"]}
        ngoai = self.svc.tai_tep(A1, F.pdf_demo(f"KT-{self.run_id}-ngoai"), du_an_id=c["du_an"], vai_tro="HO_SO_DOT", ten="hoa_don_ngoai.pdf",
                                 media_type="application/pdf", khoa=self.K("C-tep-ngoai"))["tep_id"]  # cùng dự án, KHÔNG gắn hồ sơ/HĐ
        cheo = self.s["A"]["tep"]["id"] if "tep" in a else str(self.q("SELECT tep_hop_dong_id FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s",
                                                                      (a["hd"],)))
        self.assertEqual(self.xem(c["cho"])["nguon"]["tep_can_cu"], x["nguon"]["tep_can_cu"])  # tải tệp mới không tự thành ứng viên
        for i, tid in enumerate((str(ngoai), cheo, str(uuid.uuid4()))):
            self.assertNotIn(tid, ung_vien)
            truoc = self.dem_tat_ca()
            self.assertEqual(self.loi(self.kt.luu, self.KT1, self.than_luu(x, self.K(f"C-tep-sai-{i}"), **self.du_day(
                "CO_CAN_CU", vat_can_cu_tep_id=tid, vat_trich_dan=TRICH, giu_lai_xac_nhan="1000000", ly_do="KT giữ lại theo biên bản"))),
                "M4_KT_CAN_CU_VAT_SAI")
            self.doi(truoc)
        # cùng tệp ngoài, đi THẲNG lệnh SQL (bỏ qua kiểm sớm Python) trên seam owner + danh tính thật → SQL tự chặn, 0 delta
        than = self.than_luu(x, self.K("C-tep-sql"), **self.du_day("CO_CAN_CU", vat_can_cu_tep_id=str(ngoai), vat_trich_dan=TRICH,
                                                                   giu_lai_xac_nhan="1000000", ly_do="KT giữ lại theo biên bản"))
        yc = {k: v for k, v in than.items() if k != "khoa"}
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.kt._goi, self.svc.danh_tinh(self.KT1),
                                  "SELECT m4.kt_luu(%s, %s::jsonb, %s::uuid, %s::uuid, %s, %s::integer, %s::jsonb) AS r",
                                  (than["khoa"], json.dumps(yc, ensure_ascii=False), than["kt_pending_id"], than["phong_bi_id"],
                                   than["expected_phong_bi_sha256"], than["expected_revision"],
                                   json.dumps({k: than[k] for k in KT.DU_LIEU}, ensure_ascii=False)), than["khoa"]),
                         "M4_KT_CAN_CU_VAT_SAI")
        self.doi(truoc)

    # ------------------------------------------------------------------ P06 CAS revision / SHA
    def test_p06_cas_revision(self):
        self.can("A", "C")
        c = self.s["C"]
        x = self.xem(c["cho"])
        self.assertEqual(x["kt"]["revision"], 1)
        truoc = self.dem_tat_ca()
        for rev in (0, 2):  # 0 chỉ hợp lệ khi kt === null; revision tương lai cũng bị CAS chặn
            self.assertEqual(self.loi(self.kt.luu, self.KT1, {**self.than_luu(x, self.K(f"C-cas-{rev}")), "expected_revision": rev}),
                             "M4_KT_REVISION_CU")
        for rev in (True, "1", 1.0, None):
            self.assertEqual(self.loi(self.kt.luu, self.KT1, {**self.than_luu(x, self.K("C-cas-kieu")), "expected_revision": rev}), "M4_THAM_SO_SAI")
        sha_khac = self.s["A"]["pb1"]["sha"]
        self.assertEqual(self.loi(self.kt.luu, self.KT1, {**self.than_luu(x, self.K("C-cas-sha")), "expected_phong_bi_sha256": sha_khac}),
                         "M4_KT_NGUON_DOI")
        bx = self.than_xn(x, self.K("C-xn-cas"))
        self.assertEqual(self.loi(self.kt.xac_nhan, self.KT1, {**bx, "expected_revision": 2}), "M4_KT_REVISION_CU")
        self.assertEqual(self.loi(self.kt.xac_nhan, self.KT1, {**bx, "expected_revision": 0}), "M4_THAM_SO_SAI")  # xác nhận không từ null
        self.assertEqual(self.loi(self.kt.xac_nhan, self.KT1, {**bx, "kt_revision_id": str(uuid.uuid4())}), "M4_KT_REVISION_CU")
        self.assertEqual(self.loi(self.kt.xac_nhan, self.KT1, {**bx, "gia_tri_nt_xac_nhan": "1"}), "M4_CLIENT_AUTHORITY")  # không gửi lại số
        self.doi(truoc)
        self.assertEqual(self.xem(c["cho"])["kt"]["revision"], 1)

    # ------------------------------------------------------------------ P07a (thiết kế P08) phiên bản kế tiếp chưa seal
    def test_p07a_ke_tiep_chua_seal(self):
        self.can("A")
        a = self.s["A"]
        if "xn" not in a:
            self.skipTest("P03 chưa xác nhận gốc A — NOT_RUN")
        dot = a["dot"]
        c = self.svc.duyet_xem(A1, dot_id=dot, version_id=None)["context"]
        pb = self.svc.duyet_phien_ban(A1, dot_id=dot, parent_version_id=a["v1"], revision=c["revision"], expected_basis=c["basis_sha256"],
                                      ly_do="Đính chính hồ sơ đã duyệt (DEMO)", khoa=self.K("A-pb2"))
        v2 = pb["phien_ban_id"]
        c = self.svc.duyet_xem(A1, dot_id=dot, version_id=v2)["context"]
        self.svc.duyet_phien_ban_nop(A1, dot_id=dot, version_id=v2, revision=0, expected_basis=c["basis_sha256"], khoa=self.K("A-nop2"))
        self.assertEqual(len(self.phong_bi(a["cho"])), 1)
        x = self.xem(a["cho"])
        self.assertEqual((x["can_cu_hien_hanh"], x["quyen"]["luu"], x["quyen"]["xac_nhan"], x["context"]["version_id"]), (False, False, False, a["v1"]))
        self.assertEqual([(r["thu_tu"], r["can_cu_hien_hanh"]) for r in x["lich_su"]["phong_bi"]], [(1, False)])  # không phong bì giả cho v2
        self.assertEqual([r["kt"]["revision"] for r in x["lich_su"]["kt"]], [1, 2])
        row = next(r for r in self.kt.danh_sach(self.KT1)["items"] if r["kt_pending_id"] == a["cho"])
        self.assertEqual((row["trang_thai"], row["phong_bi_id"]), (KT.TT_CAN_KIEM_LAI, a["pb1"]["id"]))
        truoc, db = self.dem_tat_ca(), self.kt_db(a["cho"])
        self.assertEqual(self.loi(self.kt.luu, self.KT1, self.than_luu(x, self.K("A-luu-hold"), **self.du_day("KHONG_AP_DUNG", ly_do=LY_DO_NA))),
                         "M4_KT_CAN_KIEM_LAI")
        self.assertEqual(self.loi(self.kt.xac_nhan, self.KT1, {**a["bx"], "khoa": self.K("A-xn-hold")}), "M4_KT_CAN_KIEM_LAI")
        self.assertEqual(self.loi(self.kt.xac_nhan, self.KT1, a["bx"]), "M4_KT_NGUON_CU")  # replay cùng khóa không vượt nguồn không hiện hành
        self.doi(truoc)
        self.assertEqual(self.kt_db(a["cho"]), db)
        self.s["A"].update(v2=v2)

    # ------------------------------------------------------------------ P07b (thiết kế P07) hai phong bì cùng gốc
    def test_p07b_hai_phong_bi_lich_su(self):
        self.can("A")
        a = self.s["A"]
        if "v2" not in a:
            self.skipTest("P07a chưa có phiên bản kế tiếp — NOT_RUN")
        dot = a["dot"]
        self.ket_luan(dot, "A-kl-v2")
        self.assertEqual(self.chap_thuan(dot, "A-ct-v2")["trang_thai"], "CHO_PDF")
        raw2 = F.ho_so_dot_duyet_pdf(f"KT-{self.run_id}-A-dinh-chinh")
        p2 = self.pdf(dot, raw2, "A-pdf-v2", "ho_so_da_duyet_A_v2.pdf")
        self.assertEqual((p2["trang_thai"], str(p2["kt_pending_id"])), ("DA_SEAL", a["cho"]))  # cùng gốc KT
        pbs = self.phong_bi(a["cho"])
        self.assertEqual([(p["thu_tu"], p["truoc_id"]) for p in pbs], [(1, None), (2, pbs[0]["id"])])
        x = self.xem(a["cho"])  # mặc định = phong bì mới nhất B
        self.kiem_xem(x, a, pbs[1])
        self.assertIsNone(x["kt"])  # không mượn KT của phong bì A
        self.assertEqual((x["can_cu_hien_hanh"], x["quyen"]), (True, {"xem": True, "luu": True, "xac_nhan": False, "tai_pdf": True}))
        lpb = x["lich_su"]["phong_bi"]
        self.assertEqual([(r["thu_tu"], r["truoc_id"], r["phien_ban_so"], r["can_cu_hien_hanh"], r["context"]["phong_bi_id"]) for r in lpb],
                         [(1, None, 1, False, pbs[0]["id"]), (2, pbs[0]["id"], 2, True, pbs[1]["id"])])
        self.assertEqual([(r["kt"]["revision"], r["context"]["phong_bi_id"], r["context"]["pdf_id"]) for r in x["lich_su"]["kt"]],
                         [(1, pbs[0]["id"], a["pdf_id"]), (2, pbs[0]["id"], a["pdf_id"])])  # lịch sử giữ đúng ngữ cảnh cũ
        xa = self.xem(a["cho"], pb=pbs[0]["id"])  # phong bì A: chỉ đọc, đúng ngữ cảnh cũ
        self.kiem_xem(xa, a, pbs[0])
        self.assertEqual(xa["context"], lpb[0]["context"])
        self.assertEqual((xa["kt"]["revision"], xa["kt"]["trang_thai"], xa["can_cu_hien_hanh"], xa["quyen"]["luu"], xa["quyen"]["xac_nhan"]),
                         (2, SK.TT_DA_XAC_NHAN, False, False, False))
        self.assertEqual(self.kt.tep_pdf(self.KT1, a["cho"], pbs[0]["id"])[2], a["raw"])
        self.assertEqual(self.kt.tep_pdf(self.KT1, a["cho"], pbs[1]["id"])[2], raw2)
        truoc = self.dem_tat_ca()
        self.assertEqual(self.loi(self.kt.luu, self.KT1, self.than_luu(xa, self.K("A-luu-cu"), **self.du_day("KHONG_AP_DUNG", ly_do=LY_DO_NA))),
                         "M4_KT_NGUON_CU")
        self.doi(truoc)
        than = self.than_luu(x, self.K("A-luu-b"), **self.du_day("KHONG_AP_DUNG", ly_do=LY_DO_NA))
        self.assertEqual(than["expected_revision"], 0)  # sentinel tạo nháp đầu của phong bì B
        ack = self.kt.luu(self.KT1, than)
        self.kiem_ack(ack, khoa=than["khoa"], revision=3, trang_thai=KT.TT_CHO_XAC_NHAN, lap_lai=False, hanh_dong="LUU")  # đơn điệu theo gốc
        self.assertEqual(ack["context"]["phong_bi_id"], pbs[1]["id"])
        x = self.xem(a["cho"])
        self.assertEqual((x["kt"]["kt_revision_id"], x["kt"]["revision"]), (ack["kt_revision_id"], 3))
        self.assertEqual([(r["kt"]["revision"], r["context"]["phong_bi_id"]) for r in x["lich_su"]["kt"]],
                         [(1, pbs[0]["id"]), (2, pbs[0]["id"]), (3, pbs[1]["id"])])
        row = next(r for r in self.kt.danh_sach(self.KT1)["items"] if r["kt_pending_id"] == a["cho"])
        self.assertEqual((row["phong_bi_id"], row["revision"], row["trang_thai"]), (pbs[1]["id"], 3, KT.TT_CHO_XAC_NHAN))
        self.s["A"].update(pbs=pbs)

    # ------------------------------------------------------------------ P08 bypass SQL bằng login ứng dụng
    def test_p08_bypass_sql_login_ung_dung(self):
        self.can("C")
        c = self.s["C"]
        web = self.web_raw
        for ham in SK.HAM_DOC:
            self.assertIs(_q1(web, "SELECT has_function_privilege(current_user, %s, 'EXECUTE')", (ham,)), True, ham)
        for ham in (*SK.HAM_LENH, *SK.HAM_NOI_BO):
            self.assertIs(_q1(web, "SELECT has_function_privilege(current_user, %s, 'EXECUTE')", (ham,)), False, ham)
        for quyen in ("INSERT", "UPDATE", "DELETE"):
            self.assertIs(_q1(web, "SELECT has_table_privilege(current_user, 'm4.kt_xac_nhan', %s)", (quyen,)), False, quyen)
        pb = self.phong_bi(c["cho"])[0]
        truoc = self.dem_tat_ca()
        lenh = (("SELECT m4.kt_luu('k', '{}'::jsonb, %s::uuid, %s::uuid, %s, 1, '{}'::jsonb)", (c["cho"], pb["id"], pb["sha"])),
                ("SELECT m4.kt_xac_nhan_lenh('k', '{}'::jsonb, %s::uuid, %s::uuid, %s, %s::uuid, 1)", (c["cho"], pb["id"], pb["sha"], str(uuid.uuid4()))),
                ("SELECT m4.kt_khoa(%s::uuid, 'LUU')", (c["cho"],)),
                ("SELECT m4._kt_tep_can_cu(%s::uuid)", (pb["id"],)))
        for sql, p in lenh:
            self.assertIn(self.loi(web.execute, sql, p), ("InsufficientPrivilege", "M4_CHI_MAY_CHU_NGUON"), sql)
        for sql in ("INSERT INTO m4.kt_xac_nhan (cho_id) VALUES (%s::uuid)", "UPDATE m4.kt_xac_nhan SET ly_do = 'x' WHERE cho_id = %s::uuid",
                    "DELETE FROM m4.kt_xac_nhan WHERE cho_id = %s::uuid"):
            self.assertEqual(self.loi(web.execute, sql, (c["cho"],)), "InsufficientPrivilege", sql)
        try:  # SELECT kỹ thuật qua RLS: login không danh tính KT → 0 hàng (hoặc từ chối), không bao giờ thấy revision
            thay = _q1(web, "SELECT count(*) FROM m4.kt_xac_nhan WHERE cho_id = %s", (c["cho"],))
        except psycopg.Error:
            thay = 0
        self.assertEqual(thay, 0)
        self.assertGreater(len(self.kt_db(c["cho"])), 0)
        self.doi(truoc)

    # ------------------------------------------------------------------ P09 lịch sử KT chỉ ghi thêm
    def test_p09_lich_su_chi_ghi_them(self):
        self.can("A")
        a = self.s["A"]
        db = self.kt_db(a["cho"])
        self.assertGreaterEqual(len(db), 2)
        for sql in ("UPDATE m4.kt_xac_nhan SET ly_do = 'sua' WHERE id = %s", "DELETE FROM m4.kt_xac_nhan WHERE id = %s"):
            chan = False
            try:
                with self.admin.transaction(force_rollback=True):  # luôn hủy, kể cả khi (sai) không bị chặn
                    self.admin.execute(sql, (db[0]["id"],))
            except psycopg.Error as exc:  # trigger chỉ ghi thêm (P0001) — chủ bảng cũng không sửa/xóa được
                chan = self.ma(exc) != "InsufficientPrivilege"
            self.assertTrue(chan, f"chủ bảng sửa/xóa được revision KT: {sql}")
        x1 = self.xem(a["cho"])
        if "pbs" in a:
            self.xem(a["cho"], pb=a["pbs"][0]["id"])
        self.assertEqual(self.kt_db(a["cho"]), db)  # đọc không đổi lịch sử
        self.assertEqual([r["kt"]["kt_revision_id"] for r in x1["lich_su"]["kt"]], [r["id"] for r in db])
        self.assertEqual([r["revision"] for r in db], list(range(1, len(db) + 1)))
        self.assertEqual([r["truoc_id"] for r in db], [None] + [r["id"] for r in db[:-1]])

    # ------------------------------------------------------------------ P11 replay / khác body / đồng thời
    def test_p11_replay_dong_thoi(self):
        h = self.ho_so_seal("D")
        x = self.xem(h["cho"])
        than = self.than_luu(x, self.K("D-luu"), **self.du_day("KHONG_AP_DUNG", ly_do=LY_DO_NA))
        a1 = self.kt.luu(self.KT1, than)
        truoc = self.dem_tat_ca()
        a2 = self.kt.luu(self.KT1, than)  # mất phản hồi → gửi lại ĐÚNG ý định + khóa
        self.assertEqual((a2["lap_lai"], a2["kt_revision_id"], a2["revision"], a2["receipt_id"]),
                         (True, a1["kt_revision_id"], 1, a1["receipt_id"]))
        self.assertEqual(self.loi(self.kt.luu, self.KT1, {**than, "ly_do": "lý do khác"}), "M4_IDEMPOTENCY_KHAC")
        self.doi(truoc)
        x = self.xem(h["cho"])
        kts = [KT.KeToanNghiemThuK2(self._svc_moi()) for _ in range(2)]
        bodies = [self.than_xn(x, self.K(f"D-xn-{i}")) for i in range(2)]
        truoc = self.dem_tat_ca()
        kq, loi = self.song_song([lambda k=k, b=b, ai=ai: k.xac_nhan(ai, b) for k, b, ai in zip(kts, bodies, (self.KT1, self.KT2))])
        self.assertEqual((len(kq), loi), (2, []))
        self.assertEqual(sorted(r["lap_lai"] for r in kq), [False, True])  # một xác nhận mới + một trả cùng xác nhận
        self.assertEqual(len({r["kt_revision_id"] for r in kq}), 1)
        self.doi(truoc, m4__kt_xac_nhan=1, m4__bien_nhan=2, m4__nhat_ky=1)
        self.assertEqual(self.q("SELECT count(*) FROM m4.kt_xac_nhan WHERE cho_id = %s AND loai = 'XAC_NHAN'", (h["cho"],)), 1)
        xn_id, rev = kq[0]["kt_revision_id"], kq[0]["revision"]
        truoc = self.dem_tat_ca()
        lai = self.kt.xac_nhan(self.KT1, bodies[0])  # replay khóa cũ
        self.assertEqual((lai["lap_lai"], lai["kt_revision_id"], lai["revision"]), (True, xn_id, rev))
        moi = self.kt.xac_nhan(self.KT1, {**bodies[0], "khoa": self.K("D-xn-moi")})  # khóa mới, cùng nháp/revision → cùng xác nhận
        self.assertEqual((moi["lap_lai"], moi["kt_revision_id"], moi["revision"]), (True, xn_id, rev))
        self.doi(truoc, m4__bien_nhan=1)
        self.assertEqual(self.loi(self.kt.xac_nhan, self.KT1, {**bodies[0], "khoa": self.K("D-xn-khac"), "kt_revision_id": xn_id,
                                                               "expected_revision": rev}), "M4_KT_DA_XAC_NHAN")
        self.s["D"] = h

    # ------------------------------------------------------------------ P12 phạm vi / vai / chéo gốc
    def test_p12_pham_vi_vai_cheo_goc(self):
        self.can("A", "C")
        a, c = self.s["A"], self.s["C"]
        pb_c = self.phong_bi(c["cho"])[0]
        x = self.xem(c["cho"])
        truoc = self.dem_tat_ca()
        mong = {A1: ("M4_KT_PHAM_VI",), REVIEW: ("M4_KT_PHAM_VI",), DUYET: ("M4_KT_PHAM_VI",), XEM: ("M4_KT_PHAM_VI",),
                A2: ("M4_KT_KHONG_THAY",), B1: ("M4_KT_KHONG_THAY",), self.KT_KHAC: ("M4_KT_KHONG_THAY", "M4_KT_PHAM_VI")}
        for ai, ma in mong.items():  # vai M24 (SOAN/REVIEW/DUYET/XEM) không ngụ ý quyền KT; ngoài dự án → không lộ tồn tại
            self.assertIn(self.loi(self.xem, c["cho"], ai), ma, ai)
            self.assertIn(self.loi(self.kt.tep_pdf, ai, c["cho"], pb_c["id"]), ma, ai)
            self.assertIn(self.loi(self.kt.luu, ai, self.than_luu(x, self.K(f"C-pv-{ai}"))), ma, ai)
            self.assertEqual([r for r in self.kt.danh_sach(ai)["items"] if r["kt_pending_id"] in (a["cho"], c["cho"])], [], ai)
        self.assertEqual(self.loi(self.xem, c["cho"], None, a["pb1"]["id"]), "M4_KT_KHONG_THAY")  # phong bì gốc khác
        self.assertEqual(self.loi(self.kt.tep_pdf, self.KT1, c["cho"], a["pb1"]["id"]), "M4_KT_KHONG_THAY")
        self.assertEqual(self.loi(self.kt.luu, self.KT1, {**self.than_luu(x, self.K("C-cheo")), "phong_bi_id": a["pb1"]["id"],
                                                          "expected_phong_bi_sha256": a["pb1"]["sha"]}), "M4_KT_KHONG_THAY")
        self.assertEqual(self.loi(self.xem, str(uuid.uuid4())), "M4_KT_KHONG_THAY")
        self.assertEqual(self.loi(self.kt.luu, self.KT1, {**self.than_luu(x, self.K("C-quyen")), "du_an_id": c["du_an"]}), "M4_CLIENT_AUTHORITY")
        self.doi(truoc)
        # nghĩa M24 cũ giữ nguyên: DUYET vẫn xem/tải PDF đợt qua route M24 (không cần KE_TOAN)
        self.assertEqual(self.svc.duyet_pdf_tai(DUYET, c["v1"], c["pdf_id"])[2], c["raw"])
        self.assertEqual(self.svc.duyet_xem(DUYET, dot_id=c["dot"], version_id=None)["trang_thai"], "DA_SEAL")

    # ------------------------------------------------------------------ P99 (thiết kế P10, CUỐI) thu hồi KE_TOAN của KT2
    def test_p99_thu_hoi_kt(self):
        self.can("C")
        c = self.s["C"]
        pb = self.phong_bi(c["cho"])[0]
        x = self.xem(c["cho"], self.KT2)
        self.assertEqual(self.kt.tep_pdf(self.KT2, c["cho"], pb["id"])[2], c["raw"])  # trước thu hồi: đọc/tải được
        than = self.than_luu(x, self.K("C-kt2-luu"), giu_lai_xac_nhan="1000000", ly_do="KT2 ghi chú trước thu hồi")
        ack = self.kt.luu(self.KT2, than)
        self.assertEqual(ack["revision"], x["kt"]["revision"] + 1)
        qid = self.q("""SELECT q.id FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id JOIN master.du_an d ON d.id = q.du_an_id
                        WHERE n.dang_nhap = %s AND q.vai = 'KE_TOAN' AND d.ma_junsky = 'DA_XD_A1' AND q.thu_hoi_luc IS NULL""", (self.KT2,))
        self.assertIsNotNone(qid)
        self.admin.execute("SELECT m4.thu_hoi_quyen_du_an(%s, 'MO_PHONG_QUAN_TRI_TEST', 'Kiểm thu hồi M4-03A')", (qid,))
        truoc, db = self.dem_tat_ca(), self.kt_db(c["cho"])
        bi_chan = ("M4_KT_KHONG_THAY", "M4_KT_PHAM_VI")
        self.assertIn(self.loi(self.xem, c["cho"], self.KT2), bi_chan)
        self.assertIn(self.loi(self.xem, c["cho"], self.KT2, pb["id"]), bi_chan)
        self.assertIn(self.loi(self.kt.tep_pdf, self.KT2, c["cho"], pb["id"]), bi_chan)
        self.assertIn(self.loi(self.kt.luu, self.KT2, than), bi_chan)  # replay đúng body/khóa cũ
        self.assertEqual([r for r in self.kt.danh_sach(self.KT2)["items"] if r["kt_pending_id"] == c["cho"]], [])
        # replay đi THẲNG lệnh SQL (bỏ qua kiểm sớm Python) trên seam owner + danh tính thật → quyền hiện hành chặn trước biên nhận
        dt = self.svc.danh_tinh(self.KT2)
        nd = {k: than[k] for k in KT.DU_LIEU}
        yc = {k: v for k, v in than.items() if k != "khoa"}
        self.assertIn(self.loi(self.kt._goi, dt, "SELECT m4.kt_luu(%s, %s::jsonb, %s::uuid, %s::uuid, %s, %s::integer, %s::jsonb) AS r",
                               (than["khoa"], json.dumps(yc, ensure_ascii=False), than["kt_pending_id"], than["phong_bi_id"],
                                than["expected_phong_bi_sha256"], than["expected_revision"], json.dumps(nd, ensure_ascii=False)), than["khoa"]),
                      bi_chan)
        self.doi(truoc)
        self.assertEqual(self.kt_db(c["cho"]), db)
        self.assertEqual(self.xem(c["cho"])["kt"]["revision"], ack["revision"])  # KT1 vẫn đọc được, không ảnh hưởng
        self.assertEqual(self.q("SELECT trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (self.KT2,)), "HOAT_DONG")


if __name__ == "__main__":
    unittest.main()
