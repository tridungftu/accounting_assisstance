"""CRM-41-06A (G6A) — kiểm service + hợp đồng SQL kế toán kiểm hợp đồng đã ký → HIEU_LUC (CODE_ONLY: coder viết, CHƯA CHẠY — WRITTEN_NOT_RUN).

Ba tầng:
  1. Thuần (không CSDL): chuẩn hóa lưu kiểm, chế độ G5, digest yêu cầu gốc, phẳng biên nhận, tệp đọc SAU quyền, tra mã Junsky kiểm dạng trước SQL.
  2. Hợp đồng tĩnh của ``CRM_G6A_SQL`` (chuỗi hằng — không chạy SQL): registry PG không bị gói này sửa; G5 VAN_HANH luôn HOLD; SYNTHETIC chỉ qua
     GUC fixture + nguồn phi_van_hanh; thứ tự kích hoạt nguyên tử; trả lại không đụng G4; guard/RLS/REVOKE; P1-A chỉ GRANT EXECUTE helper đọc K5
     cho vai ứng dụng CÓ SẴN; P1-B tra mã có quyền-trước-tra-cứu, giới hạn, che PII, nhật ký, không thay khách đã định danh.
  3. PG thật CHỈ trên bản sao DEMO SỞ HỮU do người gọi cấp (owner DSN + DSN login ứng dụng thường), SAU khi Root tích hợp M4M24 thực rồi
     G6A (tối thiểu M0025). Cổng: biến môi trường + provenance + registry đầy đủ & checksum + marker DEMO + quyền hiện hành của login. Thiếu/thiếu
     một phần → test FAIL với thông điệp ``NOT_VERIFIED`` (không skip, không coi là đạt). Không tạo DB/vai, không SET ROLE, không seed/bootstrap,
     không M9. Mọi ghi ở tầng này là giao dịch LỖI (rollback) — ca dương có ghi nằm ở tests/test_crm_kiem_hd_http.py.

Không có gì ở đây là bằng chứng nghiệm thu CRM đầy đủ; G5 vận hành / Word / GUI thật / native clone vẫn OPEN tới khi Root có biên nhận độc lập.
"""

from __future__ import annotations

import os
import re
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None
    dict_row = None

from kho_tri_thuc.ha_tang.primitives import DataError, sha256
from kho_tri_thuc.k2 import crm_kiem_hd as KH
from kho_tri_thuc.k2.crm_mau import _h
from kho_tri_thuc.k2.sql_crm_kiem_hd import _KIEM_BANG_MOI, CRM_G6A_SQL

ROOT = Path(__file__).resolve().parents[1]
SQL_TXT = "\n".join(CRM_G6A_SQL)
KY = "11111111-1111-4111-8111-111111111111"
DT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
MJ = "99999999-9999-4999-8999-999999999999"
CL_DU = {k: "XAC_NHAN" for k in KH.CHECKLIST}

# ---------------------------------------------------------------------------------------------------------------- cổng bản sao DEMO sở hữu
ENV_OWNER, ENV_APP, ENV_PROV, ENV_GHI = "KTT_G6A_CLONE_OWNER_DSN", "KTT_G6A_CLONE_APP_DSN", "KTT_G6A_CLONE_PROVENANCE", "KTT_G6A_CLONE_CHO_GHI"
SCHEMA_DU_KIEN = 25  # M0025 G6A sau M0024 M4 duyệt; cho phép owner append migration mới.
VAI_UNG_DUNG = ("app_web", "app_ke_toan", "app_doc", "app_cong_ai")
MARKER_DEMO = ("demo_seed_crm_nguoi_dung", "demo_seed_crm_g1_g7_v1")
NGUOI_CAN = {"MO_PHONG_CRM_G_KT_A": "KE_TOAN", "MO_PHONG_CRM_G_BH_A": "BAN_HANG", "MO_PHONG_CRM_G_CFO_A": "CFO", "MO_PHONG_CRM_G_TAI_A": None}
RE_PROV = re.compile(r"OWNED_DEMO_CLONE:([a-z0-9_]{1,63}):([A-Za-z0-9_.:-]{6,120})")


def _dong(*cs):
    for c in cs:
        if c is not None and not c.closed:
            c.close()


def cong_clone(*, can_ghi: bool) -> tuple[dict | None, str | None]:
    """Cổng TRƯỚC mọi ghi. Trả (ngữ cảnh, None) hoặc (None, lý do NOT_VERIFIED). Lý do không chứa DSN/mật khẩu."""
    if psycopg is None:
        return None, "thiếu driver psycopg"
    owner, app, prov = os.environ.get(ENV_OWNER), os.environ.get(ENV_APP), os.environ.get(ENV_PROV)
    thieu = [n for n, v in ((ENV_OWNER, owner), (ENV_APP, app), (ENV_PROV, prov)) if not v]
    if thieu:
        return None, "thiếu biến môi trường " + ", ".join(thieu)
    if can_ghi and os.environ.get(ENV_GHI) != "1":
        return None, f"chưa có xác nhận ghi trên bản sao ({ENV_GHI}=1)"
    m = RE_PROV.fullmatch(prov)
    if not m:
        return None, "provenance phải dạng OWNED_DEMO_CLONE:<tên_db>:<mã biên nhận Root>"
    from kho_tri_thuc.ha_tang import pg_migrations as PM
    from kho_tri_thuc.k2.crm_khoi_dong import TIEN_TO_DB, TIEN_TO_DB_KIEM_THU
    vi_tri = [i for i, x in enumerate(PM.PG_MIGRATIONS) if tuple(x) == tuple(CRM_G6A_SQL)]
    from kho_tri_thuc.m4.sql_duyet import M0024_M4_DUYET
    vi_tri_m4 = [i for i, x in enumerate(PM.PG_MIGRATIONS) if tuple(x) == tuple(M0024_M4_DUYET)]
    if (PM.PG_SCHEMA_VERSION < SCHEMA_DU_KIEN or PM.PG_SCHEMA_VERSION != len(PM.PG_MIGRATIONS)
            or vi_tri != [SCHEMA_DU_KIEN - 1] or vi_tri_m4 != [23]):
        return None, (f"registry code chưa tích hợp M4M24 + G6A (PG_SCHEMA_VERSION={PM.PG_SCHEMA_VERSION}, vị trí G6A={vi_tri}; "
                      f"cần ít nhất {SCHEMA_DU_KIEN}, G6A đúng một lần tại M0025 và M4 duyệt tại M0024; vị trí M4={vi_tri_m4})")
    mong = {i + 1: {PM._hash(x)} | set(PM.PG_MIGRATION_TUONG_THICH.get(i + 1, {})) for i, x in enumerate(PM.PG_MIGRATIONS)}
    co = ca = None
    try:
        co = psycopg.connect(owner, autocommit=True)
        ca = psycopg.connect(app, autocommit=True, row_factory=dict_row)
        db, port, t0 = co.execute("SELECT current_database(), inet_server_port(), pg_postmaster_start_time()").fetchone()
        r = ca.execute("SELECT current_database() AS db, inet_server_port() AS port, pg_postmaster_start_time() AS t0").fetchone()
        loi = None
        if (r["db"], r["port"], r["t0"]) != (db, port, t0):
            loi = "DSN chủ và DSN ứng dụng không cùng một CSDL/máy chủ"
        elif db != m.group(1):
            loi = "provenance không khớp tên CSDL đang kết nối"
        elif not db.startswith(TIEN_TO_DB + TIEN_TO_DB_KIEM_THU):
            loi = "CSDL không phải DEMO/fixture (kho_crm_demo*/kho_test_*)"
        if loi is None:
            ls = co.execute("SELECT version, checksum FROM master.schema_migrations ORDER BY version").fetchall()
            if [v for v, _ in ls] != list(range(1, PM.PG_SCHEMA_VERSION + 1)) or any(c not in mong[v] for v, c in ls):
                loi = "lịch sử schema_migrations của bản sao không đúng đầy đủ registry hiện hành + checksum (giữ prefix M0001–M0025)"
        if loi is None:
            mk = {k for (k,) in co.execute("SELECT key FROM master.he_thong WHERE key = ANY(%s)", (list(MARKER_DEMO),)).fetchall()}
            pn = [p for (p,) in co.execute("SELECT ma FROM master.phap_nhan").fetchall()]
            if mk != set(MARKER_DEMO) or "PN_DEMO_A" not in pn or any(not p.startswith("PN_DEMO_") for p in pn):
                loi = "thiếu marker DEMO hoặc có pháp nhân không phải DEMO (không chạy trên dữ liệu thật)"
        if loi is None and not co.execute("SELECT master.la_chu_bang('master.crm_mau_phien_ban'::regclass)").fetchone()[0]:
            loi = "DSN chủ không phải chủ bảng (đường ghi tin cậy)"
        if loi is None:
            v = ca.execute("""SELECT r.rolsuper, r.rolbypassrls, session_user = current_user AS khong_set_role,
                                     pg_has_role(current_user, (SELECT relowner FROM pg_class WHERE oid = 'master.crm_kiem_ho_so'::regclass), 'USAGE') AS la_chu,
                                     (SELECT array_agg(a) FROM unnest(%s::text[]) a WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = a)
                                                                                       AND pg_has_role(current_user, a, 'MEMBER')) AS vai
                              FROM pg_roles r WHERE r.rolname = current_user""", (list(VAI_UNG_DUNG),)).fetchone()
            if v["rolsuper"] or v["rolbypassrls"] or not v["khong_set_role"] or v["la_chu"] or not v["vai"]:
                loi = "DSN ứng dụng phải là login thường NOSUPERUSER/NOBYPASSRLS, không phải chủ bảng, thuộc vai ứng dụng có sẵn, không SET ROLE"
        if loi is None:
            for login, vai in NGUOI_CAN.items():
                ok = co.execute("""SELECT EXISTS (SELECT 1 FROM master.nguoi_dung n JOIN master.phan_quyen q ON q.nguoi_dung_id = n.id
                                                  JOIN master.phap_nhan p ON p.id = q.phap_nhan_id
                                                  WHERE n.dang_nhap = %s AND n.trang_thai = 'HOAT_DONG' AND n.mo_phong AND p.ma = 'PN_DEMO_A'
                                                    AND 'CRM' = ANY(q.module) AND (%s::text IS NULL OR n.vai_tro = %s))""", (login, vai, vai)).fetchone()[0]
                if not ok:
                    loi = f"thiếu quyền hiện hành của người dùng DEMO {login} trên PN_DEMO_A/CRM"
                    break
        if loi:
            _dong(co, ca)
            return None, loi
        return {"owner": co, "app": ca, "db": db, "kiem_thu": db.startswith(TIEN_TO_DB_KIEM_THU), "bien_nhan": m.group(2)}, None
    except psycopg.Error as e:
        _dong(co, ca)
        return None, f"không kiểm được bản sao ({type(e).__name__})"


# ---------------------------------------------------------------------------------------------------------------- 1. thuần
def _loi(test, ma, fn, *a, **kw):
    with test.assertRaises(DataError) as cm:
        fn(*a, **kw)
    test.assertEqual(cm.exception.code, ma)


class ChuanHoaLuu(unittest.TestCase):
    def goc(self, **sua):
        d = {"ky_id": KY, "expected_revision": 0, "checklist": dict(CL_DU), "doi_tac_id": DT, "ma_junsky_id": MJ, "ngay_hieu_luc": "2026-11-01",
             "can_cu_ngay": "DIEU_KHOAN_HD", "trich_dan_ngay": "Điều 12", "ghi_chu": None, "khoa": "crmkiem-1"}
        d.update(sua)
        return d

    def test_hop_le(self):
        y = KH.chuan_hoa_luu(**self.goc())
        self.assertEqual((y["ky_id"], y["doi_tac_id"], y["ma_junsky_id"], y["ngay_hieu_luc"], y["expected_revision"]), (KY, DT, MJ, "2026-11-01", 0))
        self.assertEqual(list(y["checklist"]), list(KH.CHECKLIST))

    def test_checklist_chua_chon_khong_mac_dinh_dat(self):
        y = KH.chuan_hoa_luu(**self.goc(checklist={k: None for k in KH.CHECKLIST}))
        self.assertTrue(all(v is None for v in y["checklist"].values()))

    def test_checklist_sai(self):
        _loi(self, "CRM_KIEM_CHECKLIST_SAI", KH.chuan_hoa_luu, **self.goc(checklist={"khach_dung": "XAC_NHAN"}))
        _loi(self, "CRM_KIEM_CHECKLIST_SAI", KH.chuan_hoa_luu, **self.goc(checklist={**CL_DU, "khach_dung": "DAT"}))
        _loi(self, "CRM_KIEM_CHECKLIST_SAI", KH.chuan_hoa_luu, **self.goc(checklist={**CL_DU, "them": "XAC_NHAN"}))

    def test_junsky_phai_di_cap(self):
        _loi(self, "CRM_KIEM_JUNSKY_SAI", KH.chuan_hoa_luu, **self.goc(ma_junsky_id=None))
        _loi(self, "CRM_KIEM_JUNSKY_SAI", KH.chuan_hoa_luu, **self.goc(doi_tac_id=None))
        _loi(self, "CRM_G_YEU_CAU_SAI", KH.chuan_hoa_luu, **self.goc(ma_junsky_id="KH_DEMO.A01"))  # không nhận mã thô / tạo mã
        y = KH.chuan_hoa_luu(**self.goc(doi_tac_id=None, ma_junsky_id=None))
        self.assertEqual((y["doi_tac_id"], y["ma_junsky_id"]), (None, None))

    def test_ngay_hieu_luc_du_bo(self):
        _loi(self, "CRM_KIEM_NGAY_SAI", KH.chuan_hoa_luu, **self.goc(can_cu_ngay=None))
        _loi(self, "CRM_KIEM_NGAY_SAI", KH.chuan_hoa_luu, **self.goc(trich_dan_ngay=None))
        _loi(self, "CRM_G_YEU_CAU_SAI", KH.chuan_hoa_luu, **self.goc(can_cu_ngay="NGAY_KY"))  # ngày ký không phải căn cứ hiệu lực
        _loi(self, "CRM_G_YEU_CAU_SAI", KH.chuan_hoa_luu, **self.goc(ngay_hieu_luc="01/11/2026"))
        _loi(self, "CRM_G_YEU_CAU_SAI", KH.chuan_hoa_luu, **self.goc(trich_dan_ngay="   "))

    def test_revision_khoa(self):
        _loi(self, "CRM_G_YEU_CAU_SAI", KH.chuan_hoa_luu, **self.goc(expected_revision=True))
        _loi(self, "CRM_G_YEU_CAU_SAI", KH.chuan_hoa_luu, **self.goc(expected_revision="0"))
        _loi(self, "CRM_G_YEU_CAU_SAI", KH.chuan_hoa_luu, **self.goc(expected_revision=-1))
        _loi(self, "CRM_G_KHOA", KH.chuan_hoa_luu, **self.goc(khoa="k k"))
        _loi(self, "CRM_G_YEU_CAU_SAI", KH.chuan_hoa_luu, **self.goc(ky_id="x"))

    def test_che_do_g5(self):
        with self.assertRaises(ValueError):
            KH.CrmKiemHdK2(_FakeKy(), g5_che_do="MATCH")
        self.assertEqual(KH.CrmKiemHdK2(_FakeKy()).g5_che_do, "VAN_HANH")


# ---------------------------------------------------------------------------------------------------------------- service với kết nối giả
class _Cur:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _Conn:
    def __init__(self, tra=None, loi=None):
        self.calls, self.tra, self.loi = [], list(tra or []), loi

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        if "set_config" in sql:
            return _Cur({"set_config": "SYNTHETIC_FIXTURE"})
        if self.loi is not None:
            raise self.loi
        return _Cur({"r": self.tra.pop(0) if self.tra else {"lap_lai": False, "ket_qua": {"ho_so_id": "x"}}})


class _FakeMau:
    def __init__(self, conn):
        self.conn_gia = conn

    def danh_tinh(self, dang_nhap):
        return {"id": "00000000-0000-4000-8000-000000000001", "dang_nhap": dang_nhap}

    @contextmanager
    def _tx(self, dt, *, rr=False):
        yield self.conn_gia


class _Kho:
    """Thư mục kho giả: ghi lại mọi lần tra đường dẫn/đọc — để chứng minh không tra kho trước quyền."""

    def __init__(self, files=None):
        self.files, self.truy = dict(files or {}), []

    def __truediv__(self, ten):
        self.truy.append(ten)
        kho = self

        class _P:
            def is_file(self_):
                return ten in kho.files

            def read_bytes(self_):
                return kho.files[ten]
        return _P()


class _FakeKy:
    def __init__(self, conn=None, kho_ky=None, kho_tep=None):
        self.mau = _FakeMau(conn or _Conn())
        self.kho_ky = kho_ky or _Kho()
        self.gk = type("GK", (), {"kho": type("K", (), {"__truediv__": lambda s, x: kho_tep or _Kho()})()})()


class DichVuGia(unittest.TestCase):
    def test_guc_chi_dat_cho_synthetic(self):
        c = _Conn()
        KH.CrmKiemHdK2(_FakeKy(c)).check("KT", ky_id=KY, expected_revision=1, khoa="k1")
        self.assertFalse(any("set_config" in s for s, _ in c.calls), "VAN_HANH không được đặt GUC fixture")
        self.assertEqual(c.calls[-1][1][-1], "VAN_HANH")
        c2 = _Conn()
        KH.CrmKiemHdK2(_FakeKy(c2), g5_che_do="SYNTHETIC_FIXTURE").check("KT", ky_id=KY, expected_revision=1, khoa="k1")
        self.assertIn("ktt.crm_kiem_g5", c2.calls[0][0])
        self.assertEqual(c2.calls[-1][1][-1], "SYNTHETIC_FIXTURE")

    def test_digest_khong_gom_khoa_va_gom_che_do(self):
        c = _Conn()
        s = KH.CrmKiemHdK2(_FakeKy(c))
        s.luu("KT", ky_id=KY, expected_revision=0, checklist=CL_DU, doi_tac_id=DT, ma_junsky_id=MJ, khoa="a1")
        s.luu("KT", ky_id=KY, expected_revision=0, checklist=CL_DU, doi_tac_id=DT, ma_junsky_id=MJ, khoa="b2")
        (_, p1), (_, p2) = c.calls
        self.assertEqual((p1[0], p2[0]), ("a1", "b2"))
        self.assertEqual(p1[1], p2[1])
        y = KH.chuan_hoa_luu(ky_id=KY, expected_revision=0, checklist=CL_DU, doi_tac_id=DT, ma_junsky_id=MJ, khoa="a1")
        self.assertEqual(p1[1], _h("CRM_KIEM_LUU", {k: v for k, v in y.items() if k != "khoa"}))
        c3, c4 = _Conn(), _Conn()
        KH.CrmKiemHdK2(_FakeKy(c3)).hieu_luc("KT", ky_id=KY, expected_revision=1, check_id=MJ, do_thi_sha256="d" * 64, khoa="h1")
        KH.CrmKiemHdK2(_FakeKy(c4), g5_che_do="SYNTHETIC_FIXTURE").hieu_luc("KT", ky_id=KY, expected_revision=1, check_id=MJ, do_thi_sha256="d" * 64,
                                                                          khoa="h1")
        self.assertNotEqual(c3.calls[-1][1][1], c4.calls[-1][1][1], "digest kích hoạt phải gắn chế độ G5")

    def test_phang_bien_nhan(self):
        c = _Conn(tra=[{"lap_lai": True, "ket_qua": {"ho_so_id": "h", "trang_thai": "DANG_KIEM"}}])
        r = KH.CrmKiemHdK2(_FakeKy(c)).bo_sung("KT", ky_id=KY, expected_revision=1, ly_do="thiếu phụ lục", khoa="k")
        self.assertEqual(r, {"ho_so_id": "h", "trang_thai": "DANG_KIEM", "lap_lai": True})

    def test_lenh_kiem_dang_truoc_sql(self):
        c = _Conn()
        s = KH.CrmKiemHdK2(_FakeKy(c))
        _loi(self, "CRM_G_YEU_CAU_SAI", s.hieu_luc, "KT", ky_id=KY, expected_revision=1, check_id=MJ, do_thi_sha256="D" * 64, khoa="k")
        _loi(self, "CRM_G_YEU_CAU_SAI", s.xu_ly_lech, "KT", ky_id=KY, expected_revision=1, loai="G9_LECH", muc_tieu_id=MJ, ma_lech="X", ly_do="x", khoa="k")
        _loi(self, "CRM_G_YEU_CAU_SAI", s.tra_lai, "KT", ky_id=KY, expected_revision=1, ly_do=" ", khoa="k")
        self.assertEqual(c.calls, [])

    def test_tep_quyen_truoc_kho(self):
        kho = _Kho()
        c = _Conn(loi=DataError("CRM_KIEM_CHUA_CO_PHAM_VI", "x"))
        s = KH.CrmKiemHdK2(_FakeKy(c, kho_ky=kho))
        _loi(self, "CRM_KIEM_CHUA_CO_PHAM_VI", s.tep, "KT", KY, "ban-ky")
        self.assertEqual(kho.truy, [], "tra kho trước khi quyền/phạm vi hiện hành đạt")
        _loi(self, "CRM_G_YEU_CAU_SAI", s.tep, "KT", KY, "docx")
        raw = b"%PDF-1.7 demo"
        sha = sha256(raw)
        kho2 = _Kho({sha: raw})
        c2 = _Conn(tra=[{"sha256": sha, "len": len(raw), "ten": "HĐ/01", "revision": 2}])
        ten, out, mime = KH.CrmKiemHdK2(_FakeKy(c2, kho_ky=kho2)).tep("KT", KY, "ban-ky")
        self.assertEqual((ten, out, mime), ("H__01-r2-ban-ky.pdf", raw, "application/pdf"))
        c3 = _Conn(tra=[{"sha256": sha, "len": len(raw) + 1, "ten": "x", "revision": 2}])
        _loi(self, "CRM_G_TEP_HONG", KH.CrmKiemHdK2(_FakeKy(c3, kho_ky=kho2)).tep, "KT", KY, "ban-ky")
        c4 = _Conn(tra=[{"sha256": "../x", "len": 1, "ten": "x", "revision": 2}])
        _loi(self, "CRM_G_TEP_KHONG_CO", KH.CrmKiemHdK2(_FakeKy(c4, kho_ky=kho2)).tep, "KT", KY, "ban-ky")

    def test_tim_junsky_kiem_dang_truoc_sql(self):
        c = _Conn()
        s = KH.CrmKiemHdK2(_FakeKy(c))
        for tu in ("KH", "  ab  ", "x" * 61, "KH\x00DEMO", None, 123):
            _loi(self, "CRM_G_YEU_CAU_SAI", s.tim_junsky, "KT", KY, tu)
        _loi(self, "CRM_G_YEU_CAU_SAI", s.tim_junsky, "KT", "khong-uuid", "KH_DEMO")
        self.assertEqual(c.calls, [], "tra cứu chạm CSDL khi yêu cầu sai dạng")
        c2 = _Conn(tra=[{"ky_id": KY, "ung_vien": [], "gioi_han": 10}])
        r = KH.CrmKiemHdK2(_FakeKy(c2)).tim_junsky("KT", KY, "KH_DEMO")
        self.assertEqual(r["gioi_han"], 10)
        self.assertIn("master.crm_kiem_tim_junsky", c2.calls[-1][0])
        self.assertEqual(c2.calls[-1][1], (KY, "KH_DEMO"))


# ---------------------------------------------------------------------------------------------------------------- 2. hợp đồng tĩnh SQL
def _ham(ten: str) -> str:
    ds = [s for s in CRM_G6A_SQL if re.search(r"CREATE OR REPLACE FUNCTION " + re.escape(ten) + r"\(", s)]
    assert len(ds) == 1, ten
    return ds[0]


class HopDongSql(unittest.TestCase):
    def test_khong_dang_ky_registry(self):
        src = (ROOT / "src/kho_tri_thuc/k2/sql_crm_kiem_hd.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"^\s*(from|import)\s[^\n]*pg_migrations", src, re.M), "module G6A không được import/đăng ký registry")
        from kho_tri_thuc.ha_tang import pg_migrations as PM
        vi_tri = [i for i, x in enumerate(PM.PG_MIGRATIONS) if tuple(x) == tuple(CRM_G6A_SQL)]
        self.assertEqual(vi_tri, [24], "owner đăng ký G6A đúng một lần tại M0025")
        self.assertGreaterEqual(PM.PG_SCHEMA_VERSION, SCHEMA_DU_KIEN)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        from kho_tri_thuc.m4.sql_duyet import M0024_M4_DUYET
        self.assertEqual([i for i, x in enumerate(PM.PG_MIGRATIONS) if tuple(x) == tuple(M0024_M4_DUYET)], [23])
        self.assertEqual(CRM_G6A_SQL[0], "SET LOCAL check_function_bodies = off")

    def test_g5_van_hanh_hold_khong_bia(self):
        g5 = _ham("master.crm_kiem_g5_xet")
        self.assertIn("'UNREGISTERED_G5_PROOF'", g5)
        self.assertIn("'trang_thai', 'HOLD'", g5)
        self.assertNotRegex(SQL_TXT, r"'MATCH'|'MATCHED'")
        self.assertIn("'G5_SYNTHETIC_KHONG_DUOC_PHEP'", g5)
        self.assertIn("n.phi_van_hanh", g5)
        gate = "current_setting('ktt.crm_kiem_g5', true) IS DISTINCT FROM 'SYNTHETIC_FIXTURE'"
        self.assertIn(gate, g5)
        self.assertIn(gate, _ham("master.crm_kiem_g5_kiem"))
        self.assertIn("CHECK (phi_van_hanh)", SQL_TXT)
        self.assertIn("CHECK (ma ~ '^SYNTHETIC_", SQL_TXT)
        # khởi tạo G4 (PENDING/NOT_SELECTED) không bao giờ là bằng chứng
        self.assertIn("'la_bang_chung', false", g5)

    def test_kich_hoat_nguyen_tu_dung_thu_tu(self):
        f = _ham("master.crm_kiem_hieu_luc")
        moc = ["crm_g_bn_tra", "'CRM_KIEM_DA_HIEU_LUC", "'CRM_KIEM_CHECK_CU", "'CRM_KIEM_CHUA_DU_DIEU_KIEN", "INSERT INTO master.crm_kiem_quyet_dinh",
               "UPDATE master.hop_dong SET crm_giao_ket = 'HIEU_LUC'", "INSERT INTO kho.chung_tu", "INSERT INTO master.hop_dong_phien_ban",
               "INSERT INTO master.hop_dong_tham_so", "UPDATE master.hop_dong_phien_ban SET trang_thai = 'DA_DUYET'",
               "UPDATE master.hop_dong SET phien_ban_hien_hanh", "INSERT INTO master.lich_thu", "INSERT INTO master.crm_kiem_hieu_luc",
               "UPDATE master.crm_kiem_ho_so SET trang_thai = 'HIEU_LUC'", "UPDATE kho.viec_can_duyet SET trang_thai = 'DA_DUYET'", "crm_g_bn_ghi"]
        vt = [f.find(x) for x in moc]
        self.assertNotIn(-1, vt, dict(zip(moc, vt)))
        self.assertEqual(vt, sorted(vt), "thứ tự kích hoạt lệch hợp đồng")
        self.assertIn("doi_tac_id = rv.de_xuat_doi_tac_id", f)  # cặp KT đã chọn CÓ CHỦ Ý → master
        self.assertIn("'CRM-DOT-' ||", f)
        self.assertIn("'CRM_MAU:BAN_KY'", f)
        self.assertIn("'CRM_G6A:' || k.id::text", f)
        self.assertIn("q.check_id = p_check AND q.do_thi_sha256 = p_sha AND q.g5_che_do = p_che_do", f)  # replay chỉ cùng check + cùng chế độ

    def test_tra_lai_khong_dung_g4(self):
        f = _ham("master.crm_kiem_tra_lai")
        for cam in ("UPDATE master.crm_hd_ky", "UPDATE master.crm_hd_soan", "UPDATE master.hop_dong", "SOAN_THAO", "DELETE"):
            self.assertNotIn(cam, f)
        self.assertIn("'g4_trang_thai', h.crm_giao_ket", f)
        self.assertIn("'CHAN_PHU_THUOC'", f)

    def test_guard_csdl(self):
        for t in ("hop_dong_crm_kiem", "crm_kiem_pb_chen", "crm_kiem_pb_sua", "crm_kiem_tham_so_kiem", "crm_kiem_lich_thu_kiem", "crm_kiem_ho_so_kiem",
                  "crm_kiem_pham_vi_kiem", "crm_kiem_viec_kiem", "crm_kiem_rev_kiem", "crm_kiem_check_kiem", "crm_kiem_quyet_dinh_kiem",
                  "crm_kiem_hieu_luc_kiem"):
            self.assertRegex(SQL_TXT, r"CREATE TRIGGER " + t + r" BEFORE")
        self.assertIn("CREATE CONSTRAINT TRIGGER crm_kiem_quyet_dinh_hoan_tat AFTER INSERT ON master.crm_kiem_quyet_dinh DEFERRABLE INITIALLY DEFERRED", SQL_TXT)
        for ma in ("CRM_KIEM_HD_BAT_BIEN", "CRM_KIEM_HD_KICH_HOAT_SAI", "CRM_KIEM_PB_CHI_MAU", "CRM_KIEM_PB_BAT_BIEN", "CRM_KIEM_THAM_SO_BAT_BIEN",
                   "CRM_KIEM_LICH_SAI", "CRM_KIEM_HOAN_TAT_SAI", "CRM_KIEM_PHAM_VI_CHI_QUAN_TRI", "CRM_KIEM_G5_KHONG_PHAI_FIXTURE"):
            self.assertIn(ma, SQL_TXT)

    def test_rls_revoke(self):
        for t in _KIEM_BANG_MOI:
            self.assertIn(f"ALTER TABLE master.{t} ENABLE ROW LEVEL SECURITY", CRM_G6A_SQL)
        self.assertIn("REVOKE ALL ON " + ", ".join(f"master.{t}" for t in _KIEM_BANG_MOI) + " FROM PUBLIC", CRM_G6A_SQL)
        self.assertTrue(any("REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC" in s and "LIKE 'crm\\_kiem\\_%'" in s for s in CRM_G6A_SQL))
        self.assertNotRegex(SQL_TXT, r"(?i)\b(CREATE|ALTER|DROP)\s+ROLE\b|\bSET\s+ROLE\b|BYPASSRLS|DISABLE ROW LEVEL SECURITY|FORCE ROW LEVEL")

    def test_p1a_grant_chi_helper_doc(self):
        grants = re.findall(r"GRANT\s[^']*", SQL_TXT)
        self.assertEqual(grants, ["GRANT EXECUTE ON FUNCTION master.crm_kiem_viec_doc_duoc(text, uuid, uuid) TO %I"], grants)
        cuoi = CRM_G6A_SQL[-1]
        self.assertIn("ARRAY['app_web','app_ke_toan','app_doc','app_cong_ai']", cuoi)
        self.assertIn("IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r)", cuoi)  # không tạo vai
        i_revoke = max(i for i, s in enumerate(CRM_G6A_SQL) if "REVOKE EXECUTE ON FUNCTION" in s)
        self.assertEqual(i_revoke, len(CRM_G6A_SQL) - 2, "GRANT helper phải đứng SAU REVOKE EXECUTE")
        self.assertNotRegex(SQL_TXT, r"GRANT[^;']*PUBLIC")
        h = _ham("master.crm_kiem_viec_doc_duoc")
        self.assertIn("RETURNS boolean", h)
        self.assertIn("STABLE SECURITY DEFINER", h)
        self.assertIn("CREATE POLICY viec_can_duyet_crm_kiem_doc ON kho.viec_can_duyet AS RESTRICTIVE FOR SELECT", SQL_TXT)
        self.assertIn("master.crm_kiem_viec_doc_duoc(tham_chieu_bang, tham_chieu_id, phap_nhan_id)", SQL_TXT)
        self.assertIn("IF NEW.tham_chieu_bang IN ('master.crm_kiem_ho_so','master.crm_kiem_hieu_luc') THEN", _ham("kho.viec_chu_so_huu"))

    def test_khong_tao_ma_khong_doi_khach(self):
        self.assertNotRegex(SQL_TXT, r"(INSERT INTO|UPDATE|DELETE FROM)\s+master\.(doi_tac_ma_junsky|doi_tac)\b")
        self.assertNotRegex(SQL_TXT, r"UPDATE\s+master\.crm_hd_(ky|soan_rev|soan)\b")

    def test_p1b_tra_ma_va_khong_thay_khach(self):
        f = _ham("master.crm_kiem_tim_junsky")
        i_dich, i_tra = f.find("crm_kiem_dich(p_ky, true)"), f.find("FROM master.doi_tac_ma_junsky")
        self.assertTrue(0 < i_dich < i_tra, "quyền lệnh + phạm vi hiện hành phải TRƯỚC tra cứu")
        self.assertLess(f.find("CRM_KIEM_KHACH_DA_DINH"), i_tra)
        for x in ("y.phap_nhan_id = d.pn", "y.valid_to IS NULL AND NOT y.dong", "LIMIT 10", "master.crm_kiem_che(y.ten_junsky)",
                  "'CRM_KIEM_TIM_JUNSKY'", "'tu_khoa_sha256'", "'gioi_han', 10"):
            self.assertIn(x, f)
        self.assertNotIn("'tu_khoa', ", f)  # nhật ký không lưu từ khóa thô
        rv = _ham("master.crm_kiem_rev_kiem")
        self.assertIn("CRM_KIEM_KHACH_DA_DINH", rv)
        self.assertIn("v_ky_dt IS NOT NULL AND v_ky_dt <> NEW.de_xuat_doi_tac_id::text", rv)
        self.assertIn("v_hd_dt IS NOT NULL AND v_hd_dt <> NEW.de_xuat_doi_tac_id", rv)
        doc = _ham("master.crm_kiem_doc")
        self.assertIn("'khach_du_thao'", doc)
        self.assertIn("y.id = rv.de_xuat_ma_junsky_id AND y.doi_tac_id = rv.de_xuat_doi_tac_id", doc)
        dg = _ham("master.crm_kiem_danh_gia")
        self.assertIn("'THIEU_KHACH_JUNSKY'", dg)
        self.assertIn("'KHACH_GAN_MA_KHI_KIEM'", dg)


# ---------------------------------------------------------------------------------------------------------------- 3. PG thật — bản sao DEMO sở hữu
class CrmKiemBanSao(unittest.TestCase):
    """Chỉ giao dịch LỖI (rollback) trên chủ bảng + đọc quyền trên login ứng dụng thường. Thiếu cổng → FAIL 'NOT_VERIFIED'."""

    @classmethod
    def setUpClass(cls):
        cls.ctx, cls.ly_do = cong_clone(can_ghi=True)
        if cls.ctx:
            cls.addClassCleanup(_dong, cls.ctx["owner"], cls.ctx["app"])

    def setUp(self):
        if not self.ctx:
            self.fail("NOT_VERIFIED: " + self.ly_do)
        self.o, self.a = self.ctx["owner"], self.ctx["app"]

    def sql_loi(self, conn, ma, sql, params=()):
        with self.assertRaises(psycopg.Error) as cm:
            with conn.transaction():
                conn.execute(sql, params)
        self.assertIn(ma, str(cm.exception))

    def test_p01_guard_chu_bang(self):
        pn = self.o.execute("SELECT id FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'").fetchone()[0]
        self.sql_loi(self.o, "CRM_KIEM_HD_BAT_BIEN", "INSERT INTO master.hop_dong (phap_nhan_id, crm_giao_ket) VALUES (%s, 'HIEU_LUC')", (pn,))
        self.sql_loi(self.o, "CRM_KIEM_PB_", "INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, nguon) VALUES (%s, 1, 'CRM_MAU')", (str(uuid.uuid4()),))
        self.sql_loi(self.o, "CRM_KIEM_G5_KHONG_PHAI_FIXTURE",
                     "INSERT INTO master.crm_kiem_g5_nguon (ma, loai, phi_van_hanh, tao_boi) VALUES ('SYNTHETIC_X', 'SYNTHETIC_FIXTURE', true, 'TEST')")
        self.sql_loi(self.o, "CRM_KIEM_PHAM_VI_SAI",
                     "INSERT INTO master.crm_kiem_pham_vi (phan_cong_id, phap_nhan_id, hop_dong_id, ky_id, cap_boi) VALUES (%s, %s, %s, %s, 'TEST')",
                     (str(uuid.uuid4()), pn, str(uuid.uuid4()), str(uuid.uuid4())))
        # hàm lệnh gọi trực tiếp trên chủ bảng, không danh tính phiên → cùng bất biến (ẩn đích), không ghi
        self.sql_loi(self.o, "CRM_G_KHONG_THAY", "SELECT master.crm_kiem_hieu_luc('k', %s, %s::uuid, 1, %s::uuid, %s, 'VAN_HANH')",
                     ("0" * 64, str(uuid.uuid4()), str(uuid.uuid4()), "d" * 64))

    def test_p02_g5_van_hanh_hold(self):
        g = self.o.execute("SELECT master.crm_kiem_g5_xet(%s::uuid, 'VAN_HANH')", (str(uuid.uuid4()),)).fetchone()[0]
        self.assertEqual((g["trang_thai"], g["chan"]), ("HOLD", [{"ma": "UNREGISTERED_G5_PROOF"}]))
        g = self.o.execute("SELECT master.crm_kiem_g5_xet(%s::uuid, 'SYNTHETIC_FIXTURE')", (str(uuid.uuid4()),)).fetchone()[0]
        self.assertEqual((g["trang_thai"], g["chan"]), ("HOLD", [{"ma": "G5_SYNTHETIC_KHONG_DUOC_PHEP"}]))

    def test_p03_quyen_login_ung_dung(self):
        """P1-A: login thường CHỈ có EXECUTE helper đọc K5; mọi hàm crm_kiem_* khác và mọi bảng G6A mới đều không."""
        ham = self.a.execute("""SELECT n.nspname || '.' || p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')' AS ten,
                                       has_function_privilege(current_user, p.oid, 'EXECUTE') AS duoc
                                FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                                WHERE n.nspname IN ('master','kho') AND p.proname LIKE 'crm\\_kiem\\_%'""").fetchall()
        self.assertTrue(ham)
        duoc = sorted(r["ten"] for r in ham if r["duoc"])
        self.assertEqual(duoc, ["master.crm_kiem_viec_doc_duoc(p_bang text, p_id uuid, p_pn uuid)"], duoc)
        for t in _KIEM_BANG_MOI:
            r = self.a.execute("""SELECT has_table_privilege(current_user, %s, 'SELECT') OR has_table_privilege(current_user, %s, 'INSERT')
                                         OR has_table_privilege(current_user, %s, 'UPDATE') OR has_table_privilege(current_user, %s, 'DELETE') AS co""",
                               (f"master.{t}",) * 4).fetchone()
            self.assertFalse(r["co"], t)
        self.sql_loi(self.a, "permission denied", "SELECT master.crm_kiem_hieu_luc('k', %s, %s::uuid, 1, %s::uuid, %s, 'VAN_HANH')",
                     ("0" * 64, str(uuid.uuid4()), str(uuid.uuid4()), "d" * 64))
        self.sql_loi(self.a, "permission denied", "SELECT count(*) FROM master.crm_kiem_ho_so")
        self.sql_loi(self.a, "permission denied", "SELECT master.crm_kiem_g5_xet(%s::uuid, 'VAN_HANH')", (str(uuid.uuid4()),))

    def test_p04_k5_doc_khong_loi_quyen(self):
        """P1-A: policy RESTRICTIVE gọi helper — SELECT kho.viec_can_duyet bằng login thường KHÔNG còn lỗi quyền (kể cả khi chưa có việc G6A)."""
        from kho_tri_thuc.k2 import quyen
        dt = quyen.nap_danh_tinh(self.a, "MO_PHONG_CRM_G_KT_A", chi_mo_phong=True)
        with self.a.transaction():
            self.a.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (dt["id"], dt["dang_nhap"]))
            self.a.execute("SELECT count(*) AS n FROM kho.viec_can_duyet").fetchone()


if __name__ == "__main__":
    unittest.main()
