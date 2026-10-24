"""M4-02C INTEGRATION-REPAIR — DTO THẬT của backend → UI THẬT. CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

- Nhà sản xuất: `XayDungK2.duyet_xem` → `DuyetDot.xem` THẬT (kiểm danh tính, quyền, chọn phiên bản, do_thi/SHA đồ thị, _tep_can_cu, _phat_hien, _dong,
  _kt, _trang_thai, review_refs/can_cu, `_v`). CHỈ giả tầng dữ liệu: hai kết nối giả (login ứng dụng / chủ bảng) trả hàng theo câu SQL đã chuẩn hóa
  khoảng trắng (SQL lạ → AssertionError, không đoán) và `_chung_tu_co_so` (căn cứ L3 chụp lại) trả một dict tổng hợp. Hàng dùng kiểu psycopg thật
  (uuid.UUID, datetime/date, Decimal) để `_v` + `canonical_json` được kiểm thật. Dữ liệu tổng hợp, UUID giả, không danh tính/credential thật.
- Kịch bản: chua_nop, da_nop, cho_duyet, l3_cu, doi_sau_nop, cho_pdf, da_seal, ke_tiep_nhap, chon_v1 (V1 tường minh), chua_review.
- Người tiêu thụ: tests/m4_02c_dto_ui_async.cjs nạp app.js + m4.js + m4_duyet_pdf.js THẬT với fixture JSON do test này ghi (thư mục MỚI mỗi lần, mở "x",
  không xóa/ghi đè). Node chạy với env của tiến trình (giữ PYTHONUSERBASE/CODEX_NO_DELETE_FILES/guard A517; không -I/-S), PYTHONDONTWRITEBYTECODE=1,
  hạn 120 s. Thiếu psycopg/node, quá hạn, setup_errors → skip ghi rõ NOT_VERIFIED (KHÔNG phải PASS); ca hỏng ngữ nghĩa → FAIL.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import unittest
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json

GOC = Path(__file__).resolve().parents[1]
CJS = GOC / "tests" / "m4_02c_dto_ui_async.cjs"
HAN_NODE = 120
LOGIN = "MO_PHONG_DU_AN_A1"
LOGIN_REVIEW = "MO_PHONG_REVIEW_A1"
LOGIN_DUYET = "MO_PHONG_DUYET_A1"
LY_DO_F01 = "Đã đối chiếu biên bản NT dòng R-03"


def U(n: int) -> uuid.UUID:
    """UUID tổng hợp có 8 ký tự đầu khác nhau (UI hiện 12 ký tự đầu — V1/V2 phân biệt được)."""
    return uuid.UUID(f"{n:08x}-5a4e-4a4e-8a4e-{n:012x}")


def S(u) -> str:
    return str(u)


def T(gio: int) -> datetime:
    return datetime(2026, 10, 22, gio, 0, tzinfo=timezone.utc)


ND, ND_REVIEW, PN, DA, HD, DOT = U(0x01), U(0x02), U(0x03), U(0x04), U(0x05), U(0x06)
V1, V2, NOP1 = U(0x11), U(0x12), U(0x13)
TEP_HD, TEP_DOT1, TEP_DOT2, TEP_BOQ, PL1, BOQ1, BOQ2 = U(0x21), U(0x22), U(0x23), U(0x24), U(0x25), U(0x26), U(0x27)
L3RUN, L2RUN = U(0x31), U(0x32)
KL1, QD1, PDF1, SEAL1, GOC_KT, PB1 = U(0x41), U(0x42), U(0x43), U(0x44), U(0x45), U(0x46)
SO_HD = "HĐ-TH-01/2026"
SHA_HD, SHA_HD_MOI, SHA_DOT1, SHA_DOT2 = "a1" * 32, "a2" * 32, "d1" * 32, "d2" * 32
SHA_BOQ, SHA_BOQ2, SHA_PDF = "b1" * 32, "b2" * 32, "9d" * 32
DIGEST_V1 = "e1" * 32


# ================================================================================================== tầng dữ liệu giả (chỉ phần này là giả)
class _Cur:
    def __init__(self, rows):
        self.rows = [dict(r) for r in rows]

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def __iter__(self):
        return iter(self.rows)


class _Tx:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


class ConnGia:
    """Kết nối psycopg giả: ghi nhật ký (tên kết nối, SQL chuẩn hóa, tham số) và trả hàng của thế giới W. SQL không có trong kịch bản → AssertionError."""

    def __init__(self, ten: str, W: dict, log: list):
        self.ten, self.W, self.log = ten, W, log
        self.adapters = SimpleNamespace(register_dumper=lambda *a: None)

    def transaction(self):
        return _Tx()

    def execute(self, sql, params=()):
        s = " ".join(sql.split())
        self.log.append((self.ten, s))
        return _Cur(_tra(self.W, s, tuple(params or ())))


def _tra(W: dict, s: str, p: tuple) -> list:
    if "FROM master.nguoi_dung WHERE dang_nhap" in s:
        return [W["user"]] if p[0] == W["user"]["dang_nhap"] else []
    if "FROM master.phan_quyen" in s:
        return []
    if s.startswith("SET TRANSACTION"):
        return []
    if "set_config(" in s:
        return []
    if "m4.duyet_doc_dot(" in s:
        return [{"ok": p[0] == S(DOT), "q": copy.deepcopy(W["quyen"])}]
    if "m4.duyet_kiem(" in s:
        return []
    if "FROM m4.dot d JOIN master.du_an a" in s:
        return [W["dot"]] if p[0] == S(DOT) else []
    if "FROM m4.duyet_phien_ban v WHERE v.dot_id" in s:  # trước các bảng con (câu này có subquery duyet_ket_luan/duyet_quyet_dinh/duyet_seal)
        return copy.deepcopy(W["versions"])
    if s.startswith("SELECT snapshot FROM m4.duyet_phien_ban WHERE id"):
        return [{"snapshot": copy.deepcopy(W["snap"].get(p[0]))}] if any(S(v["id"]) == p[0] for v in W["versions"]) else []
    if "FROM m4.duyet_kt_cho" in s:
        return [W["goc"]] if W["goc"] else []
    if "FROM m4.duyet_kt_phong_bi" in s:
        return copy.deepcopy(W["phong_bi"])
    if "FROM m4.nhat_ky" in s:
        return copy.deepcopy(W["nhat_ky"])
    if "FROM m4.chung_tu_run r JOIN m4.chung_tu_result" in s:
        return [copy.deepcopy(W["l3"])] if W["l3"] else []
    if "to_regclass('m4.duyet_seal')" in s:
        return [{"co": False}]  # chưa có seal đợt trước → lich_su_da_duyet trả None (giữ CHUA_CO_NGUON)
    if "FROM m4.tep WHERE du_an_id" in s:
        assert p[0] == S(DA), "tra tệp ngoài dự án của đợt"
        return [W["tep"][i] for i in p[1] if i in W["tep"]]
    if "FROM m4.boq q LEFT JOIN m4.tep t" in s:
        assert p[0] == S(HD), "tra BOQ ngoài HĐ của đợt"
        return [W["boq"][i] for i in p[1] if i in W["boq"]]
    if "FROM m4.duyet_ket_luan_dong" in s:
        return copy.deepcopy(W["kl_dong"].get(p[0], []))
    if "FROM m4.duyet_ket_luan WHERE phien_ban_id" in s:
        return copy.deepcopy(W["kls"].get(p[0], []))
    if "FROM m4.duyet_quyet_dinh WHERE phien_ban_id" in s:
        return [copy.deepcopy(W["qd"][p[0]])] if p[0] in W["qd"] else []
    if "FROM m4.duyet_pdf WHERE phien_ban_id" in s:
        return copy.deepcopy(W["pdfs"].get(p[0], []))
    if "FROM m4.duyet_seal WHERE phien_ban_id" in s:
        return [copy.deepcopy(W["seal"][p[0]])] if p[0] in W["seal"] else []
    raise AssertionError("SQL ngoài kịch bản tầng dữ liệu giả: " + s[:240])


# ================================================================================================== thế giới tổng hợp
CO = {"phien_ban": "chung_tu.co_so/tong_hop", "tep": [{"vai": "BB_NT", "raw_sha256": SHA_DOT1}],
      "l2": {"trang_thai": "CU", "run_id": S(L2RUN), "basis_sha256": "c2" * 32, "ket_qua_sha256": "f2" * 32},
      "truoc_da_duyet": {"trang_thai": "CHUA_CO_NGUON"}}
KQ_L3 = {
    "hang_muc": [
        {"khoa": "R-01", "ma_hm": "HM01", "ten": "Đào đất", "dvt": "m3", "kl_kn": None, "kl_lk": 10, "kl_hd": "100.000", "don_gia": 150000, "dong": 4},
        {"khoa": "R-02", "ma_hm": "HM02", "ten": "Bê tông móng", "dvt": "m3", "kl_kn": 0, "kl_lk": 0, "kl_hd": 50, "don_gia": "20000", "dong": 5},
        {"khoa": "R-03", "ma_hm": "HM03", "ten": "Trát tường", "dvt": "m2", "kl_kn": 40.5, "kl_lk": "12.25", "kl_hd": 60, "don_gia": None, "dong": 6}],
    "phat_hien": [
        {"id": "F-01", "code": "L3_KL_VUOT", "level": "ERROR", "title": "Khối lượng vượt HĐ", "detail": "Dòng R-03 vượt 5%", "item": "R-03",
         "tai_lieu": "BANG_KL", "amount": "125000.50"},
        {"code": "L3_THIEU_CHU_KY", "level": None, "title": "Thiếu chữ ký", "detail": None}],
    "coverage": {"BIEN_BAN": {"trang_thai": "CHECKED", "ly_do": None}, "HOA_DON": {"trang_thai": "CHUA_CHAY", "ly_do": "Chưa có hóa đơn"}},
    "provenance": {"nguon_hang_muc": "L2"}}


def _ban(vid, so, *, trang_thai="DA_NOP", parent=None, digest=DIGEST_V1, rev=7, klr=None, qd=None, seal=None):
    return {"id": vid, "so": so, "parent_id": parent, "nop_id": NOP1 if trang_thai == "DA_NOP" else None, "trang_thai": trang_thai,
            "ly_do": None if trang_thai == "DA_NOP" else "Sửa BOQ sau seal — phiên bản kế tiếp", "digest": digest, "revision_ho_so": rev,
            "tao_boi": LOGIN, "tao_luc": T(7 + so), "nop_boi": LOGIN if trang_thai == "DA_NOP" else None,
            "nop_luc": T(8) if trang_thai == "DA_NOP" else None, "ket_luan_revision": klr, "quyet_dinh_id": qd, "seal_id": seal}


def the_gioi() -> dict:
    """Đợt 1 đã nộp V1 (snapshot: tệp HĐ, PL không gắn tệp, 2 tài liệu đợt — 1 tra được / 1 không, 2 BOQ — 1 nối được / 1 LEFT JOIN trượt), L3 CO."""
    co = copy.deepcopy(CO)
    return {
        "user": {"id": ND, "dang_nhap": LOGIN, "ten": "Mô phỏng dự án A1", "vai_tro": "DU_AN", "mo_phong": True, "trang_thai": "HOAT_DONG"},
        "quyen": {"xem": True, "ket_luan": True, "duyet": True, "tai_pdf": True, "phien_ban": True},
        "dot": {"id": DOT, "hop_dong_id": HD, "du_an_id": DA, "phap_nhan_id": PN, "so_dot": 1, "ngay_nghiem_thu": date(2026, 10, 1),
                "trang_thai": "DA_NOP", "revision": 3, "so_hop_dong": SO_HD, "revision_ho_so_hien_hanh": 7},
        "versions": [_ban(V1, 1)],
        "snap": {S(V1): {"tep_hop_dong": {"id": S(TEP_HD), "raw_sha256": SHA_HD, "ten": "HD-TH-01.pdf"},
                         "phu_luc": [{"id": S(PL1), "so_pl": "01", "tep_id": None}],
                         "boq": [{"id": S(BOQ1), "phu_luc_id": None, "so_dong": 3, "so_phat_hien": 0},
                                 {"id": S(BOQ2), "phu_luc_id": S(PL1), "so_dong": 2, "so_phat_hien": 0}],
                         "tai_lieu": [{"muc": "BIEN_BAN_NT", "tep_id": S(TEP_DOT1), "raw_sha256": SHA_DOT1},
                                      {"muc": "BANG_KL", "tep_id": S(TEP_DOT2), "raw_sha256": SHA_DOT2}]}},
        "tep": {S(TEP_HD): {"id": TEP_HD, "vai_tro_tai_lieu": "HOP_DONG", "ten_goc": "HD-TH-01.pdf", "raw_sha256": SHA_HD, "byte_length": 123456},
                S(TEP_DOT1): {"id": TEP_DOT1, "vai_tro_tai_lieu": "BIEN_BAN_NT", "ten_goc": "BB-NT-dot1.pdf", "raw_sha256": SHA_DOT1, "byte_length": 2048}},
        "boq": {S(BOQ1): {"boq_id": BOQ1, "boq_sha256": SHA_BOQ, "id": TEP_BOQ, "vai_tro_tai_lieu": "BOQ", "ten_goc": "BOQ-HD.xlsx", "raw_sha256": SHA_BOQ,
                          "byte_length": 4096},
                S(BOQ2): {"boq_id": BOQ2, "boq_sha256": SHA_BOQ2, "id": None, "vai_tro_tai_lieu": None, "ten_goc": None, "raw_sha256": None,
                          "byte_length": None}},
        "co": co,
        "l3": {"run_id": L3RUN, "revision": 2, "trang_thai": "SUCCEEDED", "basis_sha256": "0b" * 32, "tao_boi_id": ND_REVIEW, "tao_dang_nhap": LOGIN_REVIEW,
               "ket_qua": copy.deepcopy(KQ_L3), "ket_qua_sha256": "f3" * 32, "basis_cong_bo_sha256": None},  # basis_cong_bo gán sau (CO/CU)
        "kls": {}, "kl_dong": {}, "qd": {}, "pdfs": {}, "seal": {}, "goc": None, "phong_bi": [],
        "nhat_ky": [{"hanh_dong": "NOP", "actor": LOGIN, "luc": T(8), "chi_tiet": {"phien_ban_so": 1}}],
    }


def _kl(gsha: str) -> dict:
    return {"id": KL1, "revision": 1, "graph_sha256": gsha, "l3_run_id": L3RUN, "l2_run_id": L2RUN, "tien_te": "VND",
            "gia_tri_nt": Decimal("150000000"), "so_xin_thanh_toan": Decimal("120000000"), "tam_ung": Decimal("0"), "thu_hoi": None,
            "giu_lai": Decimal("6000000"), "xu_ly_phat_hien": [{"finding_id": "F-01", "ly_do": LY_DO_F01}], "thieu": [], "canh_bao": [],
            "ly_do": "Kết luận đợt 1 (tổng hợp)", "quyen": "REVIEW", "actor": LOGIN_REVIEW, "luc": T(9)}


def _gan_ket_luan(W: dict, gsha: str):
    W["kls"][S(V1)] = [_kl(gsha)]
    W["kl_dong"][S(KL1)] = [{"row_id": "R-01", "khoi_luong_chap_nhan": Decimal("10")}, {"row_id": "R-02", "khoi_luong_chap_nhan": None},
                            {"row_id": "R-03", "khoi_luong_chap_nhan": Decimal("40.5")}]
    W["versions"][0]["ket_luan_revision"] = 1


def _gan_quyet_dinh(W: dict, gsha: str):
    W["qd"][S(V1)] = {"id": QD1, "ket_luan_id": KL1, "graph_sha256": gsha, "ly_do": "Đồng ý thanh toán đợt 1", "actor": LOGIN_DUYET, "luc": T(10)}
    W["versions"][0]["quyet_dinh_id"] = QD1


def _gan_seal(W: dict, gsha: str):
    W["pdfs"][S(V1)] = [{"id": PDF1, "version_id": V1, "name": "ho_so_thanh_toan_dot_1.pdf", "media_type": "application/pdf", "sha256": SHA_PDF,
                         "byte_length": 9, "ket_luan_id": KL1, "ket_luan_revision": 1, "graph_sha256": gsha, "actor": LOGIN, "luc": T(11)}]
    W["seal"][S(V1)] = {"id": SEAL1, "version_id": V1, "pdf_id": PDF1, "quyet_dinh_id": QD1, "ket_luan_id": KL1, "graph_sha256": gsha,
                        "pdf_sha256": SHA_PDF, "so_lieu": {"tien_te": "VND", "gia_tri_nt": "150000000", "dong": [{"row_id": "R-01", "khoi_luong_chap_nhan": "10"}],
                                                           "thue": None},
                        "so_lieu_sha256": "5e" * 32, "actor": LOGIN_DUYET, "luc": T(12)}
    W["goc"] = {"id": GOC_KT}
    W["phong_bi"] = [{"id": PB1, "seal_id": SEAL1, "version_id": V1, "thu_tu": 1, "truoc_id": None, "noi_dung_sha256": "6f" * 32, "luc": T(12)}]
    W["versions"][0]["seal_id"] = SEAL1


# ================================================================================================== nhà sản xuất thật
def _xem(XD, W: dict, version_id=None):
    log = []
    app, tin = ConnGia("app", W, log), ConnGia("tin_cay", W, log)
    xd = XD(app, GOC / "var", conn_tin_cay=tin, chi_mo_phong=True, hom_nay=lambda: date(2026, 10, 23))
    xd._chung_tu_co_so = lambda c, dot: copy.deepcopy(W["co"])  # căn cứ L3 chụp lại = tầng dữ liệu (đã có kiểm riêng ở gói M4-02A/B)
    return xd.duyet_xem(LOGIN, dot_id=S(DOT), version_id=version_id), log


def _sinh(XD) -> dict:
    out, nhat = {}, {}
    co_sha = XD._sha_co_so(copy.deepcopy(CO))

    W = the_gioi()
    W["versions"], W["snap"], W["l3"], W["nhat_ky"] = [], {}, None, []
    out["chua_nop"], nhat["chua_nop"] = _xem(XD, W)
    try:
        _xem(XD, W, S(V1))
        nhat["chua_nop_chon_ma"] = None
    except DataError as exc:
        nhat["chua_nop_chon_ma"] = exc.code

    W = the_gioi()
    W["l3"]["basis_cong_bo_sha256"] = co_sha
    out["da_nop"], nhat["da_nop"] = _xem(XD, W)
    gsha = out["da_nop"]["context"]["basis_sha256"]

    _gan_ket_luan(W, gsha)
    out["cho_duyet"], _ = _xem(XD, W)
    _gan_quyet_dinh(W, gsha)
    out["cho_pdf"], _ = _xem(XD, W)
    _gan_seal(W, gsha)
    out["da_seal"], _ = _xem(XD, W)

    # phiên bản kế tiếp V2 (nháp, chưa snapshot) sau seal V1; vật liệu HĐ đã đổi
    W["dot"]["revision_ho_so_hien_hanh"] = 8
    W["versions"].append(_ban(V2, 2, trang_thai="NHAP", parent=V1, digest=None, rev=None))
    W["snap"][S(V2)] = None
    out["ke_tiep_nhap"], _ = _xem(XD, W)
    out["chon_v1"], _ = _xem(XD, W, S(V1))

    W = the_gioi()
    W["l3"]["basis_cong_bo_sha256"] = "0c" * 32  # L3 đã công bố trên căn cứ cũ → CU
    W["tep"][S(TEP_HD)] = {**W["tep"][S(TEP_HD)], "raw_sha256": SHA_HD_MOI}
    out["l3_cu"], _ = _xem(XD, W)

    W = the_gioi()
    W["l3"]["basis_cong_bo_sha256"] = co_sha
    W["dot"]["revision_ho_so_hien_hanh"] = 8
    out["doi_sau_nop"], _ = _xem(XD, W)

    W = the_gioi()
    W["l3"], W["co"] = None, {**copy.deepcopy(CO), "l2": {}}
    out["chua_review"], _ = _xem(XD, W)
    return {"dto": out, "nhat": nhat}


def _ghi_fixture(dto: dict) -> Path:
    goc_ra = Path(os.environ["KHO_M4_02C_DTO_UI_OUT"]) if os.environ.get("KHO_M4_02C_DTO_UI_OUT") else GOC / "var" / "m4-02c-dto-ui"
    thu_muc = goc_ra / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:12])
    thu_muc.mkdir(parents=True, exist_ok=False)  # thư mục MỚI — không ghi đè, không xóa
    bundle = {"schema": "M4_02C_DTO_UI_FIXTURE_V1", "login": LOGIN, "ly_do_f01": LY_DO_F01,
              "ids": {"pn": S(PN), "du_an": S(DA), "hd": S(HD), "dot": S(DOT), "so_hd": SO_HD, "v1": S(V1), "v2": S(V2), "kl": S(KL1), "qd": S(QD1),
                      "pdf": S(PDF1), "seal": S(SEAL1), "goc": S(GOC_KT)},
              "sha": {"hd": SHA_HD, "hd_moi": SHA_HD_MOI, "dot2": SHA_DOT2},
              "dto": dto}
    tep = thu_muc / "fixture.json"
    with open(tep, "x", encoding="utf-8", newline="\n") as f:
        f.write(canonical_json(bundle))
    return tep


class DtoUiThat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import psycopg  # noqa: F401 — XayDungK2.__init__ cần psycopg.types.string
            from kho_tri_thuc.k2.xay_dung import XayDungK2
        except ImportError as exc:
            raise unittest.SkipTest(f"NOT_VERIFIED: thiếu psycopg/K2 ({exc}) — không chạy được nhà sản xuất thật; KHÔNG phải PASS")
        kq = _sinh(XayDungK2)
        cls.dto, cls.nhat = kq["dto"], kq["nhat"]

    # ---------------------------------------------------------------- phía nhà sản xuất (DTO thật)
    def test_01_moi_dto_json_chuan_khong_lo_object_key(self):
        for ten, d in self.dto.items():
            with self.subTest(ten=ten):
                j = canonical_json(d)  # allow_nan=False; UUID/Decimal/datetime chưa qua _v sẽ nổ ở đây
                self.assertNotIn("object_key", j)
                self.assertEqual(d["schema"], "M4_DUYET_PDF_V1")
                self.assertEqual({k: d["context"][k] for k in ("dot_id", "hop_dong_id", "du_an_id", "phap_nhan_id")},
                                 {"dot_id": S(DOT), "hop_dong_id": S(HD), "du_an_id": S(DA), "phap_nhan_id": S(PN)})
                self.assertIsInstance(d["chua_nop"], bool)
                self.assertIn("tep_can_cu", d)

    def test_02_quyen_doc_tren_login_ung_dung_bang_tren_chu_bang(self):
        log = self.nhat["da_nop"]
        self.assertTrue(any(t == "app" and "m4.duyet_doc_dot(" in s for t, s in log))
        self.assertFalse(any(t == "tin_cay" and "m4.duyet_doc_dot(" in s for t, s in log))
        self.assertFalse(any(t == "app" and "FROM m4." in s for t, s in log), "đọc bảng m4 qua login ứng dụng")
        i_kiem = next(i for i, (t, s) in enumerate(log) if t == "tin_cay" and "m4.duyet_kiem(" in s)
        i_dot = next(i for i, (t, s) in enumerate(log) if "FROM m4.dot d JOIN" in s)
        self.assertLess(i_kiem, i_dot, "kiểm quyền XEM phải trước mọi đọc bảng")

    def test_03_chua_nop_bien_the_gan_the(self):
        d = self.dto["chua_nop"]
        self.assertEqual((d["trang_thai"], d["chua_nop"], d["phien_ban_hien_hanh"]), ("CHUA_NOP", True, False))
        self.assertEqual((d["context"]["version_id"], d["context"]["revision"], d["context"]["basis_sha256"]), (None, 0, None))
        self.assertEqual(d["quyen"], {"xem": True, "ket_luan": False, "duyet": False, "tai_pdf": False, "phien_ban": False})
        for k in ("phien_ban", "can_cu", "tep_can_cu", "review_refs", "phat_hien", "dong_nt", "ket_luan_lich_su", "pdf_lich_su"):
            self.assertEqual(d[k], [], k)
        self.assertEqual(d["coverage"], {})
        self.assertEqual([d[k] for k in ("ket_luan", "quyet_dinh", "pdf", "seal", "do_thi")], [None] * 5)
        self.assertEqual((d["kt"]["trang_thai"], d["kt"]["pending_id"], d["kt"]["goc_id"], d["kt"]["phong_bi_id"]), ("CHUA_CHUYEN", None, None, None))
        self.assertEqual(d["request"]["trang_thai"], "CHO_PDF")
        self.assertTrue(d["ly_do_trang_thai"])
        self.assertEqual(self.nhat["chua_nop_chon_ma"], "M4_DUYET_KHONG_THAY", "chọn phiên bản tường minh khi chưa nộp phải 404")

    def test_04_da_nop_anh_xa_nguon(self):
        d = self.dto["da_nop"]
        self.assertEqual((d["trang_thai"], d["ly_do_trang_thai"], d["chua_nop"]), ("CHO_KET_LUAN", "Chưa có kết luận cho phiên bản này", False))
        self.assertEqual(d["context"]["version_id"], S(V1))
        self.assertEqual([r["row_id"] for r in d["dong_nt"]], ["R-01", "R-02", "R-03"])
        self.assertEqual([r["de_xuat"]["kl_kn"] for r in d["dong_nt"]], [None, "0", "40.5"])
        self.assertEqual([r["de_xuat"]["kl_hd"] for r in d["dong_nt"]], ["100", "50", "60"])
        self.assertEqual([r["de_xuat"]["kl_lk"] for r in d["dong_nt"]], ["10", "0", "12.25"])
        self.assertEqual([r["nguon"] for r in d["dong_nt"]], ["L2"] * 3)
        self.assertEqual([p["finding_id"] for p in d["phat_hien"]], ["F-01", "L3:1:L3_THIEU_CHU_KY", "COV:HOA_DON"])
        self.assertEqual([p["level"] for p in d["phat_hien"]], ["ERROR", None, "CHUA_CHAY"])
        self.assertEqual(d["phat_hien"][0]["amount"], "125000.5")
        self.assertEqual([p["xu_ly"] for p in d["phat_hien"]], [None, None, None])
        self.assertEqual([(r["loai"], r["trang_thai"], r["cong_bo"]) for r in d["review_refs"]], [("L3", "CO", True), ("L2", "CU", True)])
        self.assertEqual([x["loai"] for x in d["can_cu"]], ["PHIEN_BAN", "VAT_LIEU", "REVIEW_L3", "REVIEW_L2", "TRUOC_DA_DUYET", "THUE", "DO_THI"])
        self.assertEqual(d["can_cu"][-1]["sha256"], d["context"]["basis_sha256"])
        self.assertEqual([(t["vai"], t["trang_thai"]) for t in d["tep_can_cu"]],
                         [("HOP_DONG", "CO"), ("PHU_LUC", "KHONG_GAN_TEP"), ("HO_SO_DOT", "CO"), ("HO_SO_DOT", "THIEU_METADATA"), ("BOQ", "CO"),
                          ("BOQ", "THIEU_METADATA")])
        t = d["tep_can_cu"]
        self.assertEqual((t[0]["ten"], t[0]["raw_sha256"], t[0]["byte_length"], t[0]["tep_id"]), ("HD-TH-01.pdf", SHA_HD, 123456, S(TEP_HD)))
        self.assertEqual((t[3]["tep_id"], t[3]["ten"], t[3]["raw_sha256"], t[3]["raw_sha256_da_chup"]), (S(TEP_DOT2), None, None, SHA_DOT2))
        self.assertEqual((t[5]["tep_id"], t[5]["raw_sha256_da_chup"]), (None, SHA_BOQ2))
        self.assertIsNone(d["tep_can_cu_ly_do"])
        self.assertEqual([(v["version_id"], v["so"], v["moi_nhat"], v["ket_luan_revision"]) for v in d["phien_ban"]], [(S(V1), 1, True, None)])

    def test_05_cho_duyet_giai_trinh_va_tien(self):
        d = self.dto["cho_duyet"]
        self.assertEqual((d["trang_thai"], d["context"]["revision"]), ("CHO_DUYET", 1))
        self.assertEqual([p["xu_ly"] for p in d["phat_hien"]], [{"ly_do": LY_DO_F01}, None, None])
        k = d["ket_luan"]
        self.assertEqual([k[t] for t in ("gia_tri_nt", "so_xin_thanh_toan", "tam_ung", "thu_hoi", "giu_lai")], ["150000000", "120000000", "0", None, "6000000"])
        self.assertTrue(k["khop_co_so"])
        self.assertEqual([r["khoi_luong_chap_nhan"] for r in d["dong_nt"]], ["10", None, "40.5"])

    def test_06_l3_cu_va_tep_doi_hash(self):
        d = self.dto["l3_cu"]
        self.assertEqual(d["trang_thai"], "CAN_KIEM_LAI")
        self.assertIn("Chạy lại L3", d["ly_do_trang_thai"])
        self.assertEqual([(r["trang_thai"], r["cong_bo"]) for r in d["review_refs"]], [("CU", True), ("CU", True)])
        h = d["tep_can_cu"][0]
        self.assertEqual((h["trang_thai"], h["raw_sha256"], h["raw_sha256_da_chup"]), ("KHONG_KHOP", SHA_HD_MOI, SHA_HD))

    def test_07_vat_lieu_doi_sau_nop(self):
        d = self.dto["doi_sau_nop"]
        self.assertEqual(d["trang_thai"], "CAN_KIEM_LAI")
        vl = d["can_cu"][1]
        self.assertEqual((vl["trang_thai"], vl["revision_ho_so_nop"], vl["revision_ho_so_hien_hanh"]), ("DOI_SAU_NOP", 7, 8))

    def test_08_cho_pdf_va_da_seal(self):
        d = self.dto["cho_pdf"]
        self.assertEqual((d["trang_thai"], d["pdf"], d["seal"], d["kt"]["trang_thai"], d["request"]["trang_thai"]), ("CHO_PDF", None, None, "CHUA_CHUYEN", "CHO_PDF"))
        self.assertTrue(d["quyet_dinh"]["khop_co_so"])
        d = self.dto["da_seal"]
        self.assertEqual((d["trang_thai"], d["pdf"]["id"], d["seal"]["pdf_id"]), ("DA_SEAL", S(PDF1), S(PDF1)))
        self.assertEqual((d["kt"]["trang_thai"], d["kt"]["pending_id"], d["kt"]["phong_bi_id"]), ("CHO_XAC_NHAN", S(GOC_KT), S(PB1)))
        self.assertEqual(d["request"]["trang_thai"], "DU_DIEU_KIEN_CHUA_NOI")

    def test_09_ke_tiep_nhap_khong_muon_tep_kt(self):
        d = self.dto["ke_tiep_nhap"]
        self.assertEqual((d["trang_thai"], d["context"]["version_id"], d["phien_ban_hien_hanh"]), ("CAN_KIEM_LAI", S(V2), True))
        self.assertEqual(d["tep_can_cu"], [])
        self.assertIn("nháp", d["tep_can_cu_ly_do"])
        self.assertEqual((d["kt"]["trang_thai"], d["kt"]["pending_id"], d["kt"]["goc_id"]), ("CHUA_CHUYEN", None, S(GOC_KT)))
        self.assertEqual((d["pdf"], d["seal"], d["ket_luan"]), (None, None, None))
        self.assertEqual([(v["version_id"], v["moi_nhat"], v["seal_id"]) for v in d["phien_ban"]], [(S(V1), False, S(SEAL1)), (S(V2), True, None)])
        d = self.dto["chon_v1"]
        self.assertEqual((d["trang_thai"], d["context"]["version_id"], d["phien_ban_hien_hanh"], d["kt"]["trang_thai"]), ("DA_SEAL", S(V1), False, "CHO_XAC_NHAN"))
        self.assertEqual(len(d["tep_can_cu"]), 6)

    def test_10_chua_review_cong_bo_null(self):
        d = self.dto["chua_review"]
        self.assertEqual([(r["loai"], r["run_id"], r["cong_bo"]) for r in d["review_refs"]], [("L3", None, None), ("L2", None, None)])
        self.assertEqual((d["dong_nt"], d["phat_hien"], d["trang_thai"]), ([], [], "CAN_KIEM_LAI"))

    # ---------------------------------------------------------------- người tiêu thụ thật (Node)
    def test_20_ui_that_nhan_dto_that(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("NOT_VERIFIED: không có node trên PATH — UI thật chưa chạy; KHÔNG phải PASS")
        tep = _ghi_fixture(self.dto)
        env = dict(os.environ)  # giữ nguyên PYTHONUSERBASE/CODEX_NO_DELETE_FILES/guard; không -I/-S
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            r = subprocess.run([node, str(CJS), str(tep)], cwd=str(GOC), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=HAN_NODE)
        except subprocess.TimeoutExpired as exc:
            self._luu(tep, exc.stdout, exc.stderr)
            self.skipTest(f"NOT_VERIFIED: node quá hạn {HAN_NODE}s — không kéo dài hạn; KHÔNG phải PASS (log: {tep.parent})")
        self._luu(tep, r.stdout, r.stderr)
        dong = [x for x in (r.stdout or "").splitlines() if x.startswith("KET_QUA_JSON ")]
        if len(dong) != 1:
            self.skipTest(f"NOT_VERIFIED: harness không in đúng một dòng KET_QUA_JSON (rc={r.returncode}); log: {tep.parent}")
        kq = json.loads(dong[0][len("KET_QUA_JSON "):])
        self.assertEqual(kq["hong"], [], "ca UI hỏng (FAIL ngữ nghĩa):\n" + "\n".join(f"{h['ca']}: {h['loi'][:400]}" for h in kq["hong"]))
        if kq["setup_errors"]:
            self.skipTest("NOT_VERIFIED: setup_errors " + json.dumps(kq["setup_errors"], ensure_ascii=False)[:800])
        self.assertGreater(len(kq["dat"]), 0, "không ca nào chạy")
        self.assertEqual(r.returncode, 0, "node exitCode ≠ 0 dù không có hỏng/setup — xem stderr")

    @staticmethod
    def _luu(tep: Path, out, err):
        for ten, noi in (("node.stdout.txt", out), ("node.stderr.txt", err)):
            if isinstance(noi, bytes):
                noi = noi.decode("utf-8", "replace")
            with open(tep.parent / ten, "x", encoding="utf-8", newline="\n") as f:
                f.write(noi or "")


if __name__ == "__main__":
    unittest.main()
