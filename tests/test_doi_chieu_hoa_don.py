"""Đối chiếu hóa đơn pure — `kho_tri_thuc.nguon.doi_chieu_hoa_don` (gói DOI-CHIEU-HOA-DON-PURE-01, CODE_ONLY; coder KHÔNG chạy).

Expected viết tay (không lấy output implementation làm expected). Không mock parser/core. Không DB/ghi file/process/network/skip.
Tích hợp parser M2 thật trên fixture DEMO chỉ-đọc (`tests/fixtures/m2_invoice_xml`, `tests/fixtures/l11_quantity/native`); SHA pin trước dùng,
sai → FAIL. Biến thể bytes dựng trong bộ nhớ từ G01. Dữ liệu phía M5 là DTO nội bộ synthetic — KHÔNG phải format M5 thật
(EXTERNAL_BINDING_PENDING).
"""

from __future__ import annotations

import copy
import decimal
import json
import unittest
from decimal import Decimal
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json, sha256
from kho_tri_thuc.nguon.doi_chieu_hoa_don import DongDoiChieu, HoaDonDoiChieu, doi_chieu_hoa_don, tu_ket_qua_m2
from kho_tri_thuc.nguon.hoa_don_xml import CompanyFact, InvoiceReadContext, XmlRawRef, doc_goi_hoa_don_zip, doc_hoa_don_xml

ROOT = Path(__file__).resolve().parents[1]
M2_INPUTS = ROOT / "tests" / "fixtures" / "m2_invoice_xml" / "inputs"
L11_NATIVE = ROOT / "tests" / "fixtures" / "l11_quantity" / "native"

# SHA viết tay theo overlay/manifest fixture đã root stage
G01_SHA = "863ce3c1330ce67e6a41e74699f2ac378dbb574d03afa5d8257ce0d23c15fe97"
G03_ZIP_SHA = "51cb0f3a0dbac5be45ffe4cdad32f9b45bcccb994690b0b62beb342d6b9975b4"
G04_PAD_SHA = "87b3ed5d3a2aa1c77155b6272488d4feb147e6a873c8d1dfbe41efff49cc3646"
G04_UNPAD_SHA = "3597177c6b1c9f36d15d6b9187ede8e31a8650250c61b01c0653081de977d355"
THUNG_SHA = "65ce193e68053e59d5b18e4a7fa6879fa31499fbc2cd1ca5d138a95a30883a7a"
LINE1 = "/HDon/DLHDon/NDHDon/DSHHDVu/HHDVu[1]"

K1 = ("PN_DEMO_A", "MUA_VAO", "DEMO_M2_SUPPLIER", "1", "DEMO_SERIES_A", "1")
K2 = ("PN_DEMO_A", "MUA_VAO", "DEMO_M2_SUPPLIER", "1", "DEMO_SERIES_A", "2")
K3 = ("PN_DEMO_A", "MUA_VAO", "DEMO_M2_SUPPLIER", "1", "DEMO_SERIES_A", "3")
K_G04 = ("PN_DEMO_A", "MUA_VAO", "DEMO_M2_SUPPLIER", "1", "DEMO_SERIES_A", "7")
K_THUNG = ("PN_DEMO_A", "MUA_VAO", "DEMO_M2_SUPPLIER", "1", "DEMO_SERIES_R16", "9001")

TRANG_THAI_DONG_0 = {"MATCH": 0, "DIFFERENCE": 0, "UNIT_MISMATCH": 0, "UNKNOWN": 0, "OUT_OF_SCOPE": 0, "AMBIGUOUS": 0, "MISSING_IN_M5": 0,
                     "EXCESS_IN_M5": 0, "UNMATCHED_NO_CODE": 0}


def D(ref, ma="ITEM_A", dv="CAI", sl="10", tc="GOODS", vd=()) -> DongDoiChieu:
    return DongDoiChieu(ref, ma, dv, sl, tc, vd)


def H(ma_ban_ghi, khoa=K1, dong=(), nguon=None) -> HoaDonDoiChieu:
    return HoaDonDoiChieu(ma_ban_ghi, nguon or f"src:{ma_ban_ghi}", khoa, dong)


def so(q2, q5, *, dv2="CAI", dv5="CAI", tc2="GOODS", tc5="GOODS", ma="ITEM_A"):
    """Một cặp dòng mã duy nhất → (trang_thai, delta, ly_do)."""
    out = doi_chieu_hoa_don([H("A", dong=[D("L1", ma, dv2, q2, tc2)])], [H("B", dong=[D("R1", ma, dv5, q5, tc5)])])
    self_check = out["hoa_don"]
    assert len(self_check) == 1 and self_check[0]["trang_thai"] == "PAIRED" and len(self_check[0]["dong"]) == 1, self_check
    d = self_check[0]["dong"][0]
    return d["trang_thai"], d["delta"], d["ly_do"]


def tom_dong(out) -> list:
    """(trang_thai, ma_hang, delta, ly_do, refs M2, refs M5) cho mọi mục dòng của mọi khóa."""
    return [(d["trang_thai"], d["ma_hang"], d["delta"], d["ly_do"], [x["tham_chieu_dong"] for x in d["m2"]],
             [x["tham_chieu_dong"] for x in d["m5"]]) for e in out["hoa_don"] for d in e["dong"]]


def _doc(path: Path, sha: str) -> bytes:
    raw = path.read_bytes()
    assert sha256(raw) == sha, f"fixture {path.name} khác pin — FAIL, không skip"
    return raw


COMPANY_A = CompanyFact("DEMO_M2_COMPANY_A", "PN_DEMO_A", "DEMO_M2_COMPANY_MAP_A", 1, "DEMO_M2_COMPANY_SCOPE_A")


def ctx(**sua) -> InvoiceReadContext:
    """Context tin cậy DEMO viết tay (không measurement facts, không crosswalk); KHÔNG đưa identity vào context."""
    tham = dict(source_instance="DEMO_M2_XML_INSTANCE_A", source_profile_ref="DEMO_M2_XML_QD1271_FIELDS_V1",
                profile_document_sha256="37d57c38138e7b76f916cb20ef72d92306967d1cce572820b15b135246c32fcf", company=COMPANY_A,
                identity_profile_ref="DEMO_M2_ID_DIGITS_V1")
    tham.update(sua)
    return InvoiceReadContext(**tham)


# ================================================================================================================ golden
class Golden(unittest.TestCase):
    def test_item_a_cai_10_vs_8_toan_bo_output(self):
        out = doi_chieu_hoa_don([H("A1", dong=[D("L1", sl="10")])], [H("B1", dong=[D("R1", sl="8")])])
        self.assertEqual(out, {
            "contract": "DOI_CHIEU_HOA_DON_PURE_V1",
            "delta_basis": "M5_MINUS_M2",
            "tom_tat": {
                "ban_ghi": {"m2": 1, "m5": 1, "m2_khoa_null": 0, "m5_khoa_null": 0},
                "khoa_hoa_don": {"tong": 1, "PAIRED": 1, "MISSING_IN_M5": 0, "EXCESS_IN_M5": 0, "DUPLICATE": 0},
                "khoa_trung_theo_phia": {"M2_ONLY": 0, "M5_ONLY": 0, "BOTH": 0},
                "muc_dong": {"tong": 1, **TRANG_THAI_DONG_0, "DIFFERENCE": 1},
                "dong_nguon": {"m2_da_xet": 1, "m5_da_xet": 1, "m2_khong_xet": 0, "m5_khong_xet": 0, "m2_trong_nhom_mo_ho": 0,
                               "m5_trong_nhom_mo_ho": 0},
            },
            "hoa_don": [{
                "khoa": ["PN_DEMO_A", "MUA_VAO", "DEMO_M2_SUPPLIER", "1", "DEMO_SERIES_A", "1"], "trang_thai": "PAIRED", "ly_do": [],
                "trung_phia": [],
                "m2": [{"ma_ban_ghi": "A1", "tham_chieu_nguon": "src:A1", "van_de": [], "so_dong": 1, "tham_chieu_dong": ["L1"]}],
                "m5": [{"ma_ban_ghi": "B1", "tham_chieu_nguon": "src:B1", "van_de": [], "so_dong": 1, "tham_chieu_dong": ["R1"]}],
                "dong": [{"trang_thai": "DIFFERENCE", "ma_hang": "ITEM_A", "ly_do": [], "delta": "-2",
                          "m2": [{"tham_chieu_dong": "L1", "ma_hang": "ITEM_A", "don_vi": "CAI", "so_luong_text": "10", "tinh_chat": "GOODS",
                                  "van_de": []}],
                          "m5": [{"tham_chieu_dong": "R1", "ma_hang": "ITEM_A", "don_vi": "CAI", "so_luong_text": "8", "tinh_chat": "GOODS",
                                  "van_de": []}]}],
            }],
            "chua_xac_dinh": [],
        })

    def test_golden_huu_han(self):
        self.assertEqual(so("0", "0"), ("MATCH", "0", []))
        self.assertEqual(so(None, "0"), ("UNKNOWN", None, ["QUANTITY_MISSING_M2"]))
        self.assertEqual(so("-2", "-1"), ("DIFFERENCE", "1", []))
        self.assertEqual(so("999999999999999.123456", "999999999999999.123457"), ("DIFFERENCE", "0.000001", []))

    def test_golden_duoi_ambient_prec2_va_bay(self):
        with decimal.localcontext() as c:
            c.prec = 2
            c.rounding = decimal.ROUND_FLOOR
            c.traps[decimal.Inexact] = True
            c.traps[decimal.Rounded] = True
            self.assertEqual(so("999999999999999.123456", "999999999999999.123457"), ("DIFFERENCE", "0.000001", []))
            self.assertEqual(so("10", "8"), ("DIFFERENCE", "-2", []))
            self.assertEqual(so("2", "2"), ("MATCH", "0", []))  # không ra -0 dù ROUND_FLOOR ambient
            self.assertEqual(so("-999999999999999999999", "999999999999999999999"), ("DIFFERENCE", "1999999999999999999998", []))
            self.assertEqual(decimal.getcontext().prec, 2)  # không đổi context của caller


# ================================================================================================================ hóa đơn
class HoaDon(unittest.TestCase):
    def test_khop_chinh_xac(self):
        out = doi_chieu_hoa_don([H("A1", dong=[D("L1"), D("L2", ma="ITEM_B", sl="3")])],
                                [H("B1", dong=[D("R1"), D("R2", ma="ITEM_B", sl="3")])])
        self.assertEqual(tom_dong(out), [("MATCH", "ITEM_A", "0", [], ["L1"], ["R1"]), ("MATCH", "ITEM_B", "0", [], ["L2"], ["R2"])])
        self.assertEqual(out["tom_tat"]["khoa_hoa_don"], {"tong": 1, "PAIRED": 1, "MISSING_IN_M5": 0, "EXCESS_IN_M5": 0, "DUPLICATE": 0})
        self.assertEqual(out["tom_tat"]["muc_dong"], {"tong": 2, **TRANG_THAI_DONG_0, "MATCH": 2})
        self.assertEqual(out["hoa_don"][0]["trung_phia"], [])  # nhiều dòng KHÔNG là trùng hóa đơn

    def test_thieu_thua_hai_phia(self):
        out = doi_chieu_hoa_don([H("A1", K1, [D("L1")]), H("A2", K2, [D("L1")])], [H("B2", K2, [D("R1")]), H("B3", K3, [D("R1")])])
        self.assertEqual([(e["khoa"][5], e["trang_thai"], e["ly_do"], [r["ma_ban_ghi"] for r in e["m2"]], [r["ma_ban_ghi"] for r in e["m5"]])
                          for e in out["hoa_don"]],
                         [("1", "MISSING_IN_M5", ["ABSENT_M5"], ["A1"], []), ("2", "PAIRED", [], ["A2"], ["B2"]),
                          ("3", "EXCESS_IN_M5", ["ABSENT_M2"], [], ["B3"])])
        self.assertEqual(out["hoa_don"][0]["dong"], [])  # không biến bên vắng thành dòng 0
        self.assertEqual(out["tom_tat"]["khoa_hoa_don"], {"tong": 3, "PAIRED": 1, "MISSING_IN_M5": 1, "EXCESS_IN_M5": 1, "DUPLICATE": 0})
        self.assertEqual(out["tom_tat"]["dong_nguon"], {"m2_da_xet": 1, "m5_da_xet": 1, "m2_khong_xet": 1, "m5_khong_xet": 1,
                                                        "m2_trong_nhom_mo_ho": 0, "m5_trong_nhom_mo_ho": 0})

    def test_trung_m2_m5_ca_hai(self):
        ca = (
            ([H("A2", dong=[D("L1")]), H("A1", dong=[D("L1")])], [H("B1", dong=[D("R1")])],
             ["M2"], ["DUPLICATE_M2", "LINES_NOT_COMPARED"], ["A1", "A2"], ["B1"], {"M2_ONLY": 1, "M5_ONLY": 0, "BOTH": 0}),
            ([H("A1", dong=[D("L1")])], [H("B2", dong=[D("R1")]), H("B1", dong=[D("R1")])],
             ["M5"], ["DUPLICATE_M5", "LINES_NOT_COMPARED"], ["A1"], ["B1", "B2"], {"M2_ONLY": 0, "M5_ONLY": 1, "BOTH": 0}),
            ([H("A1", dong=[D("L1")]), H("A2", dong=[D("L1")])], [H("B1", dong=[D("R1")]), H("B2", dong=[D("R1")])],
             ["M2", "M5"], ["DUPLICATE_M2", "DUPLICATE_M5", "LINES_NOT_COMPARED"], ["A1", "A2"], ["B1", "B2"],
             {"M2_ONLY": 0, "M5_ONLY": 0, "BOTH": 1}),
            ([H("A1", dong=[D("L1")]), H("A2", dong=[D("L1")])], [],
             ["M2"], ["DUPLICATE_M2", "ABSENT_M5", "LINES_NOT_COMPARED"], ["A1", "A2"], [], {"M2_ONLY": 1, "M5_ONLY": 0, "BOTH": 0}),
        )
        for m2, m5, phia, ly_do, ids2, ids5, dem in ca:
            with self.subTest(phia=phia, ly_do=ly_do):
                out = doi_chieu_hoa_don(m2, m5)
                self.assertEqual(len(out["hoa_don"]), 1)
                e = out["hoa_don"][0]
                self.assertEqual((e["trang_thai"], e["trung_phia"], e["ly_do"], e["dong"]), ("DUPLICATE", phia, ly_do, []))
                self.assertEqual(([r["ma_ban_ghi"] for r in e["m2"]], [r["ma_ban_ghi"] for r in e["m5"]]), (ids2, ids5))
                self.assertEqual(out["tom_tat"]["khoa_trung_theo_phia"], dem)
                self.assertEqual(out["tom_tat"]["khoa_hoa_don"]["tong"], 1)  # một khóa, không đếm double
                self.assertEqual(out["tom_tat"]["khoa_hoa_don"]["DUPLICATE"], 1)
                self.assertEqual(out["tom_tat"]["muc_dong"]["tong"], 0)  # không so dòng
                self.assertEqual(out["tom_tat"]["dong_nguon"]["m2_da_xet"] + out["tom_tat"]["dong_nguon"]["m5_da_xet"], 0)

    def test_sau_truong_khoa_khac_khong_ghep(self):
        khac = ("PN_DEMO_B", "BAN_RA", "DEMO_M2_SUPPLIER_2", "2", "DEMO_SERIES_B", "01")  # số "01" ≠ "1": không normalize
        for i in range(6):
            with self.subTest(truong=i):
                k = list(K1)
                k[i] = khac[i]
                out = doi_chieu_hoa_don([H("A1", K1, [D("L1")])], [H("B1", tuple(k), [D("R1")])])
                self.assertEqual(out["tom_tat"]["khoa_hoa_don"], {"tong": 2, "PAIRED": 0, "MISSING_IN_M5": 1, "EXCESS_IN_M5": 1, "DUPLICATE": 0})
                self.assertEqual(sorted(e["trang_thai"] for e in out["hoa_don"]), ["EXCESS_IN_M5", "MISSING_IN_M5"])
                self.assertEqual(tom_dong(out), [])

    def test_khoa_none_khong_ghep_nhau(self):
        out = doi_chieu_hoa_don([H("A1", None, [D("L1")]), H("A2", K1, [D("L1")])], [H("B1", None, [D("R1")]), H("B2", K1, [D("R1")])])
        self.assertEqual([(e["phia"], e["khoa"], e["trang_thai"], e["ly_do"], e["ban_ghi"]["ma_ban_ghi"]) for e in out["chua_xac_dinh"]],
                         [("M2", None, "UNRESOLVED_KEY", ["INVOICE_KEY_NULL"], "A1"), ("M5", None, "UNRESOLVED_KEY", ["INVOICE_KEY_NULL"], "B1")])
        self.assertEqual([e["trang_thai"] for e in out["hoa_don"]], ["PAIRED"])
        self.assertEqual(out["tom_tat"]["ban_ghi"], {"m2": 2, "m5": 2, "m2_khoa_null": 1, "m5_khoa_null": 1})
        self.assertEqual(out["tom_tat"]["khoa_hoa_don"], {"tong": 1, "PAIRED": 1, "MISSING_IN_M5": 0, "EXCESS_IN_M5": 0, "DUPLICATE": 0})
        self.assertEqual(out["tom_tat"]["dong_nguon"]["m2_khong_xet"], 1)
        # chỉ None hai phía: không ghép, không thiếu/thừa
        out2 = doi_chieu_hoa_don([H("A1", None)], [H("B1", None)])
        self.assertEqual((out2["hoa_don"], len(out2["chua_xac_dinh"])), ([], 2))

    def test_ma_ban_ghi_va_ref_trung_fail(self):
        for m2 in ([H("A1", K1), H("A1", K2)], [H("A1", K1), H("A1", K1)]):  # replay cùng ID ≠ hóa đơn trùng
            with self.assertRaises(DataError) as e:
                doi_chieu_hoa_don(m2, [])
            self.assertEqual(e.exception.code, "DOI_CHIEU_MA_BAN_GHI_TRUNG")
        with self.assertRaises(DataError) as e:
            doi_chieu_hoa_don([], [H("B1"), H("B1", K2)])
        self.assertEqual(e.exception.code, "DOI_CHIEU_MA_BAN_GHI_TRUNG")
        with self.assertRaises(DataError) as e:
            H("A1", dong=[D("L1"), D("L1", ma="ITEM_B")])
        self.assertEqual(e.exception.code, "DOI_CHIEU_REF_DONG_TRUNG")
        # cùng ID ở HAI phía là hợp lệ
        out = doi_chieu_hoa_don([H("X", dong=[D("L1")])], [H("X", dong=[D("L1")])])
        self.assertEqual(out["hoa_don"][0]["trang_thai"], "PAIRED")


# ================================================================================================================ dòng
class Dong(unittest.TestCase):
    def test_ma_lap_mot_phia_hai_phia_vang(self):
        ca = (
            ([D("L1", sl="4"), D("L2", sl="6")], [D("R1", sl="10")], ["CODE_REPEATED_M2"], ["L1", "L2"], ["R1"]),
            ([D("L1")], [D("R2", sl="4"), D("R1", sl="6")], ["CODE_REPEATED_M5"], ["L1"], ["R1", "R2"]),
            ([D("L1"), D("L2")], [D("R1"), D("R2")], ["CODE_REPEATED_M2", "CODE_REPEATED_M5"], ["L1", "L2"], ["R1", "R2"]),
            ([D("L1"), D("L2")], [D("R1", ma="ITEM_Z")], ["CODE_REPEATED_M2", "CODE_ABSENT_M5"], ["L1", "L2"], []),
        )
        for d2, d5, ly_do, r2, r5 in ca:
            with self.subTest(ly_do=ly_do):
                out = doi_chieu_hoa_don([H("A", dong=d2)], [H("B", dong=d5)])
                self.assertEqual(tom_dong(out)[0], ("AMBIGUOUS", "ITEM_A", None, ly_do, r2, r5))  # tổng 4+6=10 vẫn KHÔNG gộp
                self.assertEqual(out["tom_tat"]["muc_dong"]["AMBIGUOUS"], 1)
                self.assertEqual(out["tom_tat"]["muc_dong"]["MATCH"], 0)
                self.assertEqual((out["tom_tat"]["dong_nguon"]["m2_trong_nhom_mo_ho"], out["tom_tat"]["dong_nguon"]["m5_trong_nhom_mo_ho"]),
                                 (len(r2), len(r5)))

    def test_ma_duy_nhat_ghep_exact(self):
        out = doi_chieu_hoa_don([H("A", dong=[D("L1", ma="ITEM_A"), D("L2", ma="ITEM_B", sl="1")])],
                                [H("B", dong=[D("R9", ma="ITEM_B", sl="2"), D("R1", ma="item_a")])])
        self.assertEqual(tom_dong(out), [("MISSING_IN_M5", "ITEM_A", None, ["CODE_ABSENT_M5"], ["L1"], []),
                                         ("DIFFERENCE", "ITEM_B", "1", [], ["L2"], ["R9"]),
                                         ("EXCESS_IN_M5", "item_a", None, ["CODE_ABSENT_M2"], [], ["R1"])])

    def test_ma_none_rong_khong_ghep(self):
        out = doi_chieu_hoa_don([H("A", dong=[D("L2", ma=""), D("L1", ma=None)])], [H("B", dong=[D("R1", ma=None)])])
        self.assertEqual(tom_dong(out), [("UNMATCHED_NO_CODE", None, None, ["CODE_MISSING_M2"], ["L1"], []),
                                         ("UNMATCHED_NO_CODE", "", None, ["CODE_EMPTY_M2"], ["L2"], []),
                                         ("UNMATCHED_NO_CODE", None, None, ["CODE_MISSING_M5"], [], ["R1"])])
        self.assertEqual(out["tom_tat"]["muc_dong"], {"tong": 3, **TRANG_THAI_DONG_0, "UNMATCHED_NO_CODE": 3})

    def test_dong_mot_phia(self):
        out = doi_chieu_hoa_don([H("A", dong=[D("L1")])], [H("B", dong=[])])
        self.assertEqual(tom_dong(out), [("MISSING_IN_M5", "ITEM_A", None, ["CODE_ABSENT_M5"], ["L1"], [])])
        out = doi_chieu_hoa_don([H("A", dong=[])], [H("B", dong=[D("R1", sl="0")])])
        self.assertEqual(tom_dong(out), [("EXCESS_IN_M5", "ITEM_A", None, ["CODE_ABSENT_M2"], [], ["R1"])])

    def test_don_vi(self):
        self.assertEqual(so("1", "1", dv2="CAI", dv5="THUNG"), ("UNIT_MISMATCH", None, ["UNIT_MISMATCH"]))
        self.assertEqual(so("1", "1", dv2="CAI", dv5="cai"), ("UNIT_MISMATCH", None, ["UNIT_MISMATCH"]))
        self.assertEqual(so("1", "1", dv2="CAI ", dv5="CAI"), ("UNIT_MISMATCH", None, ["UNIT_MISMATCH"]))
        self.assertEqual(so("1", "1", dv2=None, dv5="CAI"), ("UNKNOWN", None, ["UNIT_MISSING_M2"]))
        self.assertEqual(so("1", "1", dv2="CAI", dv5=""), ("UNKNOWN", None, ["UNIT_EMPTY_M5"]))
        self.assertEqual(so("1", "1", dv2=None, dv5=None), ("UNKNOWN", None, ["UNIT_MISSING_M2", "UNIT_MISSING_M5"]))
        self.assertEqual(so(None, "1", dv2="CAI", dv5="THUNG"), ("UNIT_MISMATCH", None, ["UNIT_MISMATCH", "QUANTITY_MISSING_M2"]))

    def test_tinh_chat(self):
        for tc in ("NOTE", "DISCOUNT", "SPECIAL_GOODS"):
            self.assertEqual(so("1", "1", tc2=tc, tc5=tc), ("OUT_OF_SCOPE", None, ["NATURE_OUT_OF_SCOPE"]), tc)
        self.assertEqual(so("1", "1", tc2="DISCOUNT", tc5="GOODS"), ("OUT_OF_SCOPE", None, ["NATURE_OUT_OF_SCOPE"]))
        self.assertEqual(so("1", "1", tc2="UNKNOWN"), ("UNKNOWN", None, ["NATURE_UNKNOWN_M2"]))
        self.assertEqual(so("5", "3", tc2="PROMOTION", tc5="PROMOTION"), ("DIFFERENCE", "-2", []))
        self.assertEqual(so("1", "1", tc2="GOODS", tc5="PROMOTION"), ("UNKNOWN", None, ["NATURE_MISMATCH"]))
        out = doi_chieu_hoa_don([H("A", dong=[D("L1", tc="NOTE")])], [H("B", dong=[D("R1", tc="NOTE")])])
        self.assertEqual(out["tom_tat"]["muc_dong"]["OUT_OF_SCOPE"], 1)  # vẫn nằm trong báo cáo
        with self.assertRaises(DataError) as e:
            D("L1", tc="HANG_HOA")
        self.assertEqual(e.exception.code, "DOI_CHIEU_TINH_CHAT")


# ================================================================================================================ số lượng
class SoLuong(unittest.TestCase):
    def test_none_khac_0(self):
        self.assertEqual(so(None, "0"), ("UNKNOWN", None, ["QUANTITY_MISSING_M2"]))
        self.assertEqual(so("0", None), ("UNKNOWN", None, ["QUANTITY_MISSING_M5"]))
        self.assertEqual(so(None, None), ("UNKNOWN", None, ["QUANTITY_MISSING_M2", "QUANTITY_MISSING_M5"]))
        self.assertEqual(so("", "0"), ("UNKNOWN", None, ["QUANTITY_EMPTY_M2"]))

    def test_lexeme_sai_giu_ly_do_khong_crash(self):
        for t in ("NaN", "nan", "Infinity", "-Infinity", "inf", "1e3", "1E3", "1,5", "1 ", " 1", "1 000", "+1", ".5", "1.", "１", "٣", "0x10",
                  "1_000", "--1", "-", "1.2.3", "\n1"):
            with self.subTest(t=t):
                self.assertEqual(so(t, "1"), ("UNKNOWN", None, ["QUANTITY_LEXEME_INVALID_M2"]))
                self.assertEqual(so("1", t), ("UNKNOWN", None, ["QUANTITY_LEXEME_INVALID_M5"]))

    def test_kieu_khong_phai_str_fail(self):
        for v in (1, 0, 1.0, float("nan"), True, False, Decimal("1")):
            with self.subTest(v=repr(v)):
                with self.assertRaises(DataError) as e:
                    DongDoiChieu("L1", "ITEM_A", "CAI", v)
                self.assertEqual(e.exception.code, "DOI_CHIEU_SO_LUONG_KIEU")

    def test_mien_21_6(self):
        self.assertEqual(so("999999999999999999999", "999999999999999999998"), ("DIFFERENCE", "-1", []))  # đúng 21 chữ số
        self.assertEqual(so("0.000001", "0.000002"), ("DIFFERENCE", "0.000001", []))  # đúng 6 thập phân
        self.assertEqual(so("1000000000000000000000", "1"), ("UNKNOWN", None, ["QUANTITY_DIGITS_EXCEEDED_M2"]))
        self.assertEqual(so("1", "0.0000001"), ("UNKNOWN", None, ["QUANTITY_SCALE_EXCEEDED_M5"]))
        self.assertEqual(so("1000000000000000000000.0000001", "1"),
                         ("UNKNOWN", None, ["QUANTITY_DIGITS_EXCEEDED_M2", "QUANTITY_SCALE_EXCEEDED_M2"]))

    def test_am_khong_va_dang_text(self):
        self.assertEqual(so("-0", "0"), ("MATCH", "0", []))
        self.assertEqual(so("-2", "-2"), ("MATCH", "0", []))
        self.assertEqual(so("0", "-0.5"), ("DIFFERENCE", "-0.5", []))
        self.assertEqual(so("10", "10.000"), ("MATCH", "0", []))
        self.assertEqual(so("1.50", "2"), ("DIFFERENCE", "0.5", []))
        self.assertEqual(so("8", "10"), ("DIFFERENCE", "2", []))
        out = doi_chieu_hoa_don([H("A", dong=[D("L1", sl="10.000")])], [H("B", dong=[D("R1", sl="10")])])
        d = out["hoa_don"][0]["dong"][0]
        self.assertEqual((d["m2"][0]["so_luong_text"], d["m5"][0]["so_luong_text"]), ("10.000", "10"))  # giữ text gốc hai phía


# ================================================================================================================ xác định / bất biến
class XacDinh(unittest.TestCase):
    def du_lieu(self):
        m2 = [H("A2", K2, [D("L2", ma="ITEM_B"), D("L1")]), H("A1", K1, [D("L1", sl="3")]), H("A9", None, [D("L1")]),
              H("A3", K3, [D("L1"), D("L2")])]
        m5 = [H("B3", K3, [D("R1")]), H("B1", K1, [D("R1", sl="5")]), H("B8", None), H("B2", K2, [D("R1"), D("R2", ma="ITEM_B", sl="1")])]
        return m2, m5

    def test_thu_tu_on_dinh(self):
        m2, m5 = self.du_lieu()
        goc = doi_chieu_hoa_don(m2, m5)
        dao = lambda ds: [HoaDonDoiChieu(h.ma_ban_ghi, h.tham_chieu_nguon, h.khoa_hoa_don, tuple(reversed(h.dong))) for h in reversed(ds)]
        for a, b in ((list(reversed(m2)), m5), (m2[1:] + m2[:1], list(reversed(m5))), (dao(m2), dao(m5)), (tuple(m2), tuple(m5))):
            self.assertEqual(doi_chieu_hoa_don(a, b), goc)
            self.assertEqual(canonical_json(doi_chieu_hoa_don(a, b)), canonical_json(goc))
        self.assertEqual([e["khoa"][5] for e in goc["hoa_don"]], ["1", "2", "3"])
        self.assertEqual(tom_dong(goc), [("DIFFERENCE", "ITEM_A", "2", [], ["L1"], ["R1"]),
                                         ("MATCH", "ITEM_A", "0", [], ["L1"], ["R1"]),
                                         ("DIFFERENCE", "ITEM_B", "-9", [], ["L2"], ["R2"]),
                                         ("AMBIGUOUS", "ITEM_A", None, ["CODE_REPEATED_M2"], ["L1", "L2"], ["R1"])])

    def test_input_khong_doi_output_co_lap(self):
        m2, m5 = self.du_lieu()
        truoc = (list(m2), list(m5), copy.deepcopy(m2), copy.deepcopy(m5))
        out = doi_chieu_hoa_don(m2, m5)
        self.assertEqual((m2, m5), (truoc[0], truoc[1]))
        self.assertEqual((m2, m5), (truoc[2], truoc[3]))
        ky_vong = json.loads(canonical_json(out))
        out["hoa_don"][0]["dong"][0]["m2"][0]["van_de"].append("SUA")
        out["hoa_don"][0]["khoa"][0] = "SUA"
        out["tom_tat"]["muc_dong"]["MATCH"] = 99
        out["chua_xac_dinh"].clear()
        self.assertEqual(doi_chieu_hoa_don(m2, m5), ky_vong)

    def test_dto_snapshot_va_bat_bien(self):
        dong = [D("L1")]
        van_de = ["X"]
        khoa = list(K1)
        h = HoaDonDoiChieu("A1", "src", khoa, dong, van_de)
        dong.append(D("L2"))
        van_de.append("Y")
        khoa[0] = "PN_KHAC"
        self.assertEqual((h.dong, h.van_de, h.khoa_hoa_don), ((D("L1"),), ("X",), K1))
        with self.assertRaises(Exception):
            h.ma_ban_ghi = "B"  # frozen

    def test_dto_tu_choi_dau_vao_sai(self):
        sai = (
            lambda: HoaDonDoiChieu("", "src", K1, ()),
            lambda: HoaDonDoiChieu("A", None, K1, ()),
            lambda: HoaDonDoiChieu("A", "src", K1[:5], ()),
            lambda: HoaDonDoiChieu("A", "src", K1[:5] + ("",), ()),
            lambda: HoaDonDoiChieu("A", "src", K1[:5] + (1,), ()),
            lambda: HoaDonDoiChieu("A", "src", "|".join(K1), ()),
            lambda: HoaDonDoiChieu("A", "src", K1, ({"tham_chieu_dong": "L1"},)),
            lambda: HoaDonDoiChieu("A", "src", K1, (), ("",)),
            lambda: DongDoiChieu("", "ITEM_A", "CAI", "1"),
            lambda: DongDoiChieu("L1", 1, "CAI", "1"),
            lambda: DongDoiChieu("L1", "ITEM_A", 1, "1"),
            lambda: DongDoiChieu("L1", "ITEM_A", "CAI", "1", "GOODS", "X"),
            lambda: doi_chieu_hoa_don({"A": H("A")}, []),
            lambda: doi_chieu_hoa_don([], [("B",)]),
        )
        for i, f in enumerate(sai):
            with self.subTest(i=i):
                self.assertRaises(DataError, f)

    def test_json_safe(self):
        m2, m5 = self.du_lieu()
        out = doi_chieu_hoa_don(m2, m5)

        def kiem(v):
            if isinstance(v, dict):
                for k, x in v.items():
                    self.assertIsInstance(k, str)
                    kiem(x)
            elif isinstance(v, list):
                for x in v:
                    kiem(x)
            else:
                self.assertTrue(v is None or type(v) in (str, int), repr(v))
        kiem(out)
        self.assertEqual(json.loads(json.dumps(out)), out)

    def test_module_thuan(self):
        src = (ROOT / "src" / "kho_tri_thuc" / "nguon" / "doi_chieu_hoa_don.py").read_text("utf-8")
        for cam in ("import os", "open(", "datetime", "uuid", "random", "time.", "float(", "normalized_quantity_text", "sqlite", "psycopg",
                    "socket", "subprocess", "urllib", "getcontext(", "environ", "InvoiceReadContext("):
            self.assertNotIn(cam, src, cam)
        self.assertIn("from ..ha_tang.primitives import DataError, canonical_json", src)
        self.assertIn("from .hoa_don_xml import", src)


# ================================================================================================================ parser M2 thật
class TichHopM2(unittest.TestCase):
    def test_g01_xml_den_dto_va_doi_chieu(self):
        raw = _doc(M2_INPUTS / "G01-wrapped-positive.xml", G01_SHA)
        c = ctx()
        res = doc_hoa_don_xml(raw, c)
        self.assertEqual(res.canonical_identity, K1)
        h = tu_ket_qua_m2("M2-G01", res)
        self.assertEqual((h.ma_ban_ghi, h.tham_chieu_nguon, h.khoa_hoa_don, h.van_de),
                         ("M2-G01", f"xml:{G01_SHA}", K1, ("RAW_REF_NOT_BOUND",)))
        self.assertEqual(h.dong, (DongDoiChieu(f"xml:{G01_SHA}#{LINE1}", "DEMO_ITEM_A", "CAI", "10", "GOODS", ("UNIT_UNPROVEN",)),))
        self.assertEqual(c, ctx())  # context không bị gắn identity/authority
        m5 = H("M5-SYN-1", K1, [D("R1", "DEMO_ITEM_A", "CAI", "8")])
        out = doi_chieu_hoa_don([h], [m5])
        self.assertEqual(tom_dong(out), [("DIFFERENCE", "DEMO_ITEM_A", "-2", [], [f"xml:{G01_SHA}#{LINE1}"], ["R1"])])
        self.assertEqual(out["hoa_don"][0]["m2"][0]["van_de"], ["RAW_REF_NOT_BOUND"])

    def test_g04_so_chuan_bo_0_dau_va_trung(self):
        pad = doc_hoa_don_xml(_doc(M2_INPUTS / "G04-purchase-a-padded.xml", G04_PAD_SHA), ctx())
        unpad = doc_hoa_don_xml(_doc(M2_INPUTS / "G04-purchase-a-unpadded.xml", G04_UNPAD_SHA), ctx())
        self.assertEqual(pad.header("SHDon").occurrences[0].lexeme, "0007")
        h_pad, h_unpad = tu_ket_qua_m2("M2-PAD", pad), tu_ket_qua_m2("M2-UNPAD", unpad)
        self.assertEqual((h_pad.khoa_hoa_don, h_unpad.khoa_hoa_don), (K_G04, K_G04))  # số chuẩn do parser, comparator không tự strip
        m5_7 = H("M5-7", K_G04, [D("R1", "DEMO_ITEM_A", "CAI", "10")])
        out = doi_chieu_hoa_don([h_pad], [m5_7])
        self.assertEqual(tom_dong(out), [("MATCH", "DEMO_ITEM_A", "0", [], [f"xml:{G04_PAD_SHA}#{LINE1}"], ["R1"])])
        m5_0007 = H("M5-0007", K_G04[:5] + ("0007",), [D("R1", "DEMO_ITEM_A", "CAI", "10")])
        out = doi_chieu_hoa_don([h_pad], [m5_0007])
        self.assertEqual([(e["khoa"][5], e["trang_thai"]) for e in out["hoa_don"]], [("0007", "EXCESS_IN_M5"), ("7", "MISSING_IN_M5")])
        out = doi_chieu_hoa_don([h_unpad, h_pad], [m5_7])
        e = out["hoa_don"][0]
        self.assertEqual((e["trang_thai"], e["trung_phia"], [(r["ma_ban_ghi"], r["tham_chieu_nguon"]) for r in e["m2"]]),
                         ("DUPLICATE", ["M2"], [("M2-PAD", f"xml:{G04_PAD_SHA}"), ("M2-UNPAD", f"xml:{G04_UNPAD_SHA}")]))

    def test_g03_zip_hai_entry_cung_khoa_la_trung(self):
        raw = _doc(M2_INPUTS / "G03-identical-members.zip", G03_ZIP_SHA)
        ctxs = tuple(ctx(expected_raw_ref=XmlRawRef(G01_SHA, 523, "application/xml", G03_ZIP_SHA, i, n))
                     for i, n in ((1, "invoice-a.xml"), (2, "invoice-b.xml")))
        z = doc_goi_hoa_don_zip(raw, ctxs)
        self.assertEqual([(e.entry_ordinal, e.entry_name, e.state) for e in z.entries], [(1, "invoice-a.xml", "PARSED"), (2, "invoice-b.xml", "PARSED")])
        hs = [tu_ket_qua_m2(f"M2-ZIP-{e.entry_ordinal}", e.result) for e in z.entries]
        self.assertEqual([(h.tham_chieu_nguon, h.khoa_hoa_don, h.van_de) for h in hs],
                         [(f"zip:{G03_ZIP_SHA}!1:invoice-a.xml", K1, ()), (f"zip:{G03_ZIP_SHA}!2:invoice-b.xml", K1, ())])
        self.assertEqual(hs[1].dong[0].tham_chieu_dong, f"zip:{G03_ZIP_SHA}!2:invoice-b.xml#{LINE1}")
        out = doi_chieu_hoa_don(hs, [H("M5-1", K1, [D("R1", "DEMO_ITEM_A", "CAI", "10")])])
        self.assertEqual([(e["trang_thai"], e["trung_phia"], [r["ma_ban_ghi"] for r in e["m2"]]) for e in out["hoa_don"]],
                         [("DUPLICATE", ["M2"], ["M2-ZIP-1", "M2-ZIP-2"])])
        # không context → identity None giữ unresolved, không fabricate, không ghép None với nhau
        z0 = doc_goi_hoa_don_zip(raw)
        h0 = [tu_ket_qua_m2(f"M2-NOCTX-{e.entry_ordinal}", e.result) for e in z0.entries]
        self.assertEqual([h.khoa_hoa_don for h in h0], [None, None])
        self.assertTrue(all("CONTEXT_ABSENT" in h.van_de for h in h0))
        out0 = doi_chieu_hoa_don(h0, [H("M5-N", None)])
        self.assertEqual((out0["hoa_don"], [(e["phia"], e["ban_ghi"]["ma_ban_ghi"]) for e in out0["chua_xac_dinh"]]),
                         ([], [("M2", "M2-NOCTX-1"), ("M2", "M2-NOCTX-2"), ("M5", "M5-N")]))

    def test_field_mo_ho_khong_doan(self):
        g01 = _doc(M2_INPUTS / "G01-wrapped-positive.xml", G01_SHA)
        ca = (
            (b"<DVTinh>CAI</DVTinh>", b"<DVTinh>CAI</DVTinh><DVTinh>CAI</DVTinh>",
             ("DEMO_ITEM_A", None, "10"), ("UNIT_AMBIGUOUS",), [("UNKNOWN", "DEMO_ITEM_A", None, ["UNIT_MISSING_M2"])]),
            (b"<SLuong>10</SLuong>", b"<SLuong>10</SLuong><SLuong>10</SLuong>",
             ("DEMO_ITEM_A", "CAI", None), ("QUANTITY_AMBIGUOUS", "UNIT_UNPROVEN"),
             [("UNKNOWN", "DEMO_ITEM_A", None, ["QUANTITY_MISSING_M2"])]),
            (b"<MHHDVu>DEMO_ITEM_A</MHHDVu>", b"<MHHDVu>DEMO_ITEM_A</MHHDVu><MHHDVu>DEMO_ITEM_B</MHHDVu>",
             (None, "CAI", "10"), ("FIELD_DUPLICATE", "UNIT_UNPROVEN"),
             [("EXCESS_IN_M5", "DEMO_ITEM_A", None, ["CODE_ABSENT_M2"]), ("UNMATCHED_NO_CODE", None, None, ["CODE_MISSING_M2"])]),
        )
        for a, b, gia_tri, van_de, ky_vong in ca:
            with self.subTest(field=a):
                self.assertEqual(g01.count(a), 1)
                raw = g01.replace(a, b, 1)
                res = doc_hoa_don_xml(raw, ctx())
                h = tu_ket_qua_m2("M2-AMB", res)
                self.assertEqual(h.khoa_hoa_don, K1)
                self.assertEqual(h.van_de, ("RAW_REF_NOT_BOUND", "CONTENT_AMBIGUOUS"))
                d = h.dong[0]
                self.assertEqual((d.tham_chieu_dong, (d.ma_hang, d.don_vi, d.so_luong_text), d.van_de),
                                 (f"xml:{sha256(raw)}#{LINE1}", gia_tri, van_de))
                out = doi_chieu_hoa_don([h], [H("M5", K1, [D("R1", "DEMO_ITEM_A", "CAI", "10")])])
                self.assertEqual([t[:4] for t in tom_dong(out)], ky_vong)

    def test_thung_native_exact_khong_quy_doi(self):
        raw = _doc(L11_NATIVE / "new-thung-one.xml", THUNG_SHA)
        res = doc_hoa_don_xml(raw, ctx())
        ln = res.lines[0]
        self.assertEqual((ln.quantity.state, ln.quantity.exact_text, ln.normalized_quantity_text), ("EXACT", "1", None))
        h = tu_ket_qua_m2("M2-THUNG", res)
        self.assertEqual(h.khoa_hoa_don, K_THUNG)
        self.assertIn("RAW_REF_NOT_BOUND", h.van_de)
        self.assertEqual(h.dong, (DongDoiChieu(f"xml:{THUNG_SHA}#{LINE1}", "DEMO_ITEM_A", "THUNG", "1", "GOODS", ("UNIT_UNPROVEN",)),))
        out = doi_chieu_hoa_don([h], [H("M5-T", K_THUNG, [D("R1", "DEMO_ITEM_A", "THUNG", "1")])])
        self.assertEqual(tom_dong(out), [("MATCH", "DEMO_ITEM_A", "0", [], [f"xml:{THUNG_SHA}#{LINE1}"], ["R1"])])
        out = doi_chieu_hoa_don([h], [H("M5-C", K_THUNG, [D("R1", "DEMO_ITEM_A", "CAI", "12")])])
        self.assertEqual(tom_dong(out), [("UNIT_MISMATCH", "DEMO_ITEM_A", None, ["UNIT_MISMATCH"], [f"xml:{THUNG_SHA}#{LINE1}"], ["R1"])])

    def test_tu_ket_qua_m2_tu_choi_khong_phai_result(self):
        for v in (None, {"canonical_identity": list(K1)}, b"<HDon/>"):
            with self.assertRaises(DataError):
                tu_ket_qua_m2("M2-X", v)


if __name__ == "__main__":
    unittest.main()
