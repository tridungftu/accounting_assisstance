"""SOURCE6-G5-E5 — kiểm đối chiếu bản ký `doi_chieu_ban_ky` (contract CRM_G5_*). CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN). Root chạy riêng.

Phân loại rõ:
- `E5HinhThucTests`: ma trận đầu vào THUẦN trên hàm thật của client central (`trich_chung_6`) — khóa lạ/thiếu, kiểu, typed 0 ≠ NULL, tiền tệ,
  ngày, bảng, mức 0..3, catalog đã ghim (không mượn XD), body SHA 13 khóa E5 vs 8 khóa legacy (golden tính độc lập bằng hashlib/json).
- `E5G5ClientTests`: golden/negative của `kiem_g5`/`seal_e5_hop_le` (vai PDF, coverage, vị trí, 100 vs 1000, ô bảng sửa, dòng thiếu).
- `E5ClientIoMockTests`: vòng đời client với transport giả lập (IO-mock, lớp `NguonGia` của tests/test_trich_chung_6.py) — preflight E5, đúng 13
  khóa, ý định bền/xung đột, g5/niêm phong bị sửa → không nhận. KHÔNG chứng minh engine trích đúng.
- `E5HostGateTests`: cổng `trich6_host.lop_handler_so_huu` trên Handler giả (không mở cổng mạng) — chỉ thân E5 đúng 13 khóa, JSON nghiêm.
- `E5OverlayNguonTests`: Source6 THẬT = cây private37 sở hữu (biến môi trường `SOURCE6_E5_PRIVATE37`) chép sang thư mục tạm + ghép ĐÚNG ba artefact
  `tools/source6_g5_e5/...`; chạy một tiến trình con python (cùng sys.executable, KẾ THỪA môi trường A517/no-bytecode/PYTHONUSERBASE/PYTHONPATH,
  KHÔNG -I/-S/-E/-s). PDF có lớp chữ dựng tay (DEMO) → KHOP; một trường/dòng lịch sửa → LECH + vị trí; PDF scan khi OCR tắt → CHUA_DOI_CHIEU_DUOC;
  sửa raw/expected/catalog/seal sau khi xong → UNKNOWN (không công bố). Bản sao cấu hình trong thư mục tạm đặt OCR 'tat' (không đổi cấu hình thật).
Thiếu biến môi trường / private37 khác baseline / thiếu thư viện đọc PDF / mức chưa ghim trong catalog thật → skip ghi NOT_VERIFIED (skip KHÔNG phải
PASS). ABBYY OCR, catalog KCN/NHAO, G3 Word producer, CRM-B chưa có → không kiểm ở đây (NOT_VERIFIED trong báo cáo).
Mọi expected/binding/PDF/catalog trong tệp này là DEMO, không phải đăng ký vận hành. Không Node/PG/Office/cloud/provider; thư mục tạm GIỮ LẠI.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unicodedata
import unittest
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError, sha256
from kho_tri_thuc.nguon import trich6_host as TH
from kho_tri_thuc.nguon import trich_chung_6 as T6

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "tools" / "source6_g5_e5"
BASELINE = ROOT / "docs" / "E5-SOURCE6-READONLY"
ARTEFACT = ("may_chu/dich_vu.py", "trich_xuat/quy_trinh.py", "trich_xuat/danh_muc.py")
ENV_P37 = "SOURCE6_E5_PRIVATE37"
CAT = T6.CATALOG["XD"]["catalog_sha256"]
PDF_DEMO = b"%PDF-1.4\n% DEMO ban ky E5 - bytes gia lap cho IO-mock, khong phai PDF that\n"


def _nap_tc6():
    """Dùng lại NguonGia (IO-mock đúng hình API nguồn) của bộ test client gốc — không dựng mock thứ hai."""
    spec = importlib.util.spec_from_file_location("_tc6_cho_e5", ROOT / "tests" / "test_trich_chung_6.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_TC6 = _nap_tc6()


def _h(x) -> str:
    """Golden độc lập: JSON sort_keys, không khoảng trắng, UTF-8 (không gọi helper của module đang kiểm)."""
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ fixture DEMO
LN = {"ky_id": "11111111-1111-4111-8111-111111111111", "hop_dong_id": "22222222-2222-4222-8222-222222222222",
      "soan_id": "33333333-3333-4333-8333-333333333333", "xuat_id": "44444444-4444-4444-8444-444444444444",
      "mau_phien_ban_id": "55555555-5555-4555-8555-555555555555", "anh_xa_id": "66666666-6666-4666-8666-666666666666",
      "revision": 1, "g3_input_sha256": "1" * 64, "g3_docx_sha256": "2" * 64, "g3_pdf_sha256": "3" * 64, "ban_do_sha256": "4" * 64,
      "danh_muc_digest": "7" * 64, "profile_sha256": "8" * 64, "du_lieu_sha256": "9" * 64, "danh_muc_ref": "DEMO-XD-DANH-MUC", "danh_muc_rev": 1}
BANG = {"cot": [{"ten": "Đợt", "kieu": "text"}, {"ten": "Tỷ lệ", "kieu": "so"}, {"ten": "Hạn", "kieu": "ngay"}],
        "dong": [["Đợt 1", {"so": "30", "don_vi": "%"}, "2026-12-31"], ["Đợt 2", {"so": "70", "don_vi": "%"}, "2027-06-30"]]}
TS = [{"ma": "TC-02", "kieu": "ngay", "gia_tri": "2026-10-15"},
      {"ma": "TT-02", "kieu": "tien", "gia_tri": {"so": "1000000000", "tien_te": "VND"}},
      {"ma": "TT-04", "kieu": "so", "gia_tri": {"so": "0", "don_vi": "%"}},          # 0 THẬT (khác null/rỗng)
      {"ma": "TT-10", "kieu": "so", "gia_tri": {"so": "10", "don_vi": "%"}},
      {"ma": "TT-20", "kieu": "bang", "gia_tri": BANG}]


def _expected(ts=None, **ln):
    return {"kieu": T6.KIEU_EXPECTED, "lineage": {**LN, **ln}, "tham_so": copy.deepcopy(TS if ts is None else ts)}


def _binding(ts=None, *, ln=None, muc=None, **doi):
    ln = ln or LN
    ts = TS if ts is None else ts
    b = {"kieu": T6.KIEU_BINDING, "loai_hop_dong": "XD", "catalog_id": "XD", "catalog_sha256": CAT,
         "mapping": [{"ma": t["ma"], "crm_truong": "demo." + t["ma"].lower().replace("-", "_"),
                      "muc": (muc or {}).get(t["ma"], 0 if t["ma"].startswith("TC-") else 3)} for t in ts],
         **{k: ln[k] for k in T6.BINDING_LINEAGE}}
    b.update(doi)
    return b


def _tham(ts=None, *, expected=None, binding=None, request_id="e5-demo-01", tham_so=None):
    e = expected if expected is not None else _expected(ts)
    b = binding if binding is not None else _binding(ts)
    return {"loai_hop_dong": "XD", "tham_so": tham_so if tham_so is not None else [t["ma"] for t in e["tham_so"]], "request_id": request_id,
            "expected": e, "expected_sha256": _h(e), "catalog_binding": b, "catalog_binding_sha256": _h(b)}


def _yc(raw=PDF_DEMO, **kw):
    return T6.yeu_cau_e5(signed_pdf_sha256=sha256(raw), **_tham(**kw))


def _g5_khop(yc, *, nguon="PDF_LOP_CHU"):
    """g5 golden KHOP dựng tay (literal): mỗi mã expected một mục khớp, vị trí trang/dòng truy về đúng PDF ký."""
    src = yc["source_sha256"]
    muc = {m["ma"]: m["muc"] for m in yc["catalog_binding"]["mapping"]}
    ocr = "6" * 64 if nguon == "OCR_DOCX" else None
    nd = {"kieu": nguon, "pdf_sha256": src, "ocr_docx_sha256": ocr, "so_trang": 2 if nguon == "PDF_LOP_CHU" else None, "loi": None}
    khop = [{"ma": t["ma"], "muc": muc[t["ma"]], "kieu": t["kieu"], "gia_tri": copy.deepcopy(t["gia_tri"]), "trich_dan": f"DEMO dòng {i + 1}",
             "vi_tri_do_duoc": [{"nguon": nguon, "pdf_sha256": src, "ocr_docx_sha256": ocr, "trang": 1 if nguon == "PDF_LOP_CHU" else None,
                                 "dong": i + 1}]} for i, t in enumerate(yc["expected"]["tham_so"])]
    return {"kieu": T6.KIEU_G5, "source_sha256": src, "signed_pdf_sha256": src, "expected_sha256": yc["expected_sha256"],
            "catalog_binding_sha256": yc["catalog_binding_sha256"], "g3_pdf_sha256": yc["expected"]["lineage"]["g3_pdf_sha256"],
            "coverage": [t["ma"] for t in yc["expected"]["tham_so"]], "trang_thai": "KHOP", "khop": khop, "lech": [], "thieu": [], "nguon_doc": nd}


def _sang_lech(g5, ma, ban_ky):
    it = next(x for x in g5["khop"] if x["ma"] == ma)
    g5["khop"].remove(it)
    g5["lech"].append({"ma": ma, "muc": it["muc"], "kieu": it["kieu"], "gia_tri_ky_vong": it["gia_tri"], "gia_tri_ban_ky": ban_ky,
                       "trich_dan": it["trich_dan"], "vi_tri_do_duoc": it["vi_tri_do_duoc"]})
    g5["trang_thai"] = "CHUA_DOI_CHIEU_DUOC" if g5["thieu"] else "LECH"
    return g5


def _sang_thieu(g5, ma, ly_do, mot_phan=None):
    it = next(x for x in g5["khop"] if x["ma"] == ma)
    g5["khop"].remove(it)
    g5["thieu"].append({"ma": ma, "muc": it["muc"], "kieu": it["kieu"], "ly_do": ly_do, "gia_tri_ky_vong": it["gia_tri"], "mot_phan": mot_phan or []})
    g5["trang_thai"] = "CHUA_DOI_CHIEU_DUOC"
    return g5


# ================================================================== 1. ma trận hình thức (client central)
class E5HinhThucTests(unittest.TestCase):
    def test_body_sha_13_khoa_e5_va_8_khoa_legacy(self):
        yc = _yc()
        self.assertEqual(set(yc), set(T6.KHOA_E5))
        self.assertEqual(len(T6.KHOA_E5), 13)
        self.assertEqual(TH.KHOA_E5, frozenset(T6.KHOA_E5))  # host và client cùng tập 13 khóa
        self.assertEqual((yc["mode"], yc["source_sha256"]), (T6.MODE_E5, sha256(PDF_DEMO)))
        self.assertEqual(yc["signed_pdf_sha256"], yc["source_sha256"])
        self.assertNotEqual(yc["signed_pdf_sha256"], yc["expected"]["lineage"]["g3_pdf_sha256"])  # vai PDF ký ≠ G3 PDF
        self.assertEqual(T6.body_sha256(yc), _h({k: yc[k] for k in T6.KHOA_E5}))
        self.assertNotEqual(T6.body_sha256(yc), _h({k: yc[k] for k in T6.KHOA_COMMON}))
        for k, v in (("signed_pdf_sha256", "a" * 64), ("expected_sha256", "b" * 64), ("catalog_binding_sha256", "c" * 64),
                     ("expected", {**yc["expected"], "kieu": "X"}), ("catalog_binding", {**yc["catalog_binding"], "mapping": []})):
            self.assertNotEqual(T6.body_sha256({**yc, k: v}), T6.body_sha256(yc), k)  # mỗi khóa E5 nằm trong body SHA
        leg = T6.yeu_cau_common(source_sha256="d" * 64, loai_hop_dong="XD", tham_so=["TC-01"], request_id="leg-1")
        self.assertEqual(set(leg), set(T6.KHOA_COMMON))
        self.assertEqual(T6.body_sha256(leg), _h({k: leg[k] for k in T6.KHOA_COMMON}))   # legacy giữ đúng 8 khóa
        self.assertEqual(T6.body_sha256({**leg, "expected": {"x": 1}}), T6.body_sha256(leg))  # khóa lạ không vào hash legacy
        self.assertEqual((T6.MODE, T6.CONTRACT), ("RULE_ONLY", "trich-tham-so-common/v1"))  # không đổi MODE toàn cục

    def test_gia_tri_typed(self):
        hop_le = (("text", "HĐ-01"), ("ngay", "2026-10-15"), ("ngay", "2028-02-29"), ("so", {"so": "0", "don_vi": "%"}),
                  ("so", {"so": "0.5", "don_vi": None}), ("so", {"so": "-12.25", "don_vi": "ngày"}),
                  ("tien", {"so": "1000000000", "tien_te": "VND"}), ("tien", {"so": "0", "tien_te": "USD"}),
                  ("bang", BANG), ("bang", {"cot": BANG["cot"], "dong": [["Đợt 1", None, "2026-12-31"]]}))  # ô null = chưa có
        for kieu, v in hop_le:
            self.assertTrue(T6.gia_tri_e5_hop_le(kieu, v), (kieu, v))
        sai = (("text", ""), ("text", None), ("ngay", "2026-02-30"), ("ngay", "15/10/2026"), ("ngay", "2026-1-5"),
               ("so", {"so": None, "don_vi": "%"}), ("so", {"so": "0100", "don_vi": None}), ("so", {"so": "1e3", "don_vi": None}),
               ("so", {"so": "-0", "don_vi": None}), ("so", {"so": "1.50", "don_vi": None}), ("so", {"so": 100, "don_vi": None}),
               ("so", {"so": "+1", "don_vi": None}), ("so", {"so": "1", "don_vi": ""}), ("so", {"so": "1"}),
               ("tien", {"so": "100", "tien_te": "vnd"}), ("tien", {"so": "100", "tien_te": None}), ("tien", {"so": "100"}),
               ("tien", {"so": "1.000", "tien_te": "VND"}), ("phan_tram", "10"),
               ("bang", {"cot": BANG["cot"], "dong": [[None, {"so": "30", "don_vi": "%"}, "2026-12-31"]]}),
               ("bang", {"cot": BANG["cot"], "dong": [BANG["dong"][0], BANG["dong"][0]]}),                 # khóa dòng trùng
               ("bang", {"cot": BANG["cot"], "dong": [["Đợt 1", {"so": "30", "don_vi": "%"}]]}),            # thiếu ô
               ("bang", {"cot": BANG["cot"], "dong": [["Đợt 1", "30%", "2026-12-31"]]}),                    # ô không typed
               ("bang", {"cot": [{"ten": "Tỷ lệ", "kieu": "so"}], "dong": [[{"so": "1", "don_vi": None}]]}),  # cột đầu phải text
               ("bang", {"cot": BANG["cot"], "dong": []}))
        for kieu, v in sai:
            self.assertFalse(T6.gia_tri_e5_hop_le(kieu, v), (kieu, v))

    def _loi(self, ma, raw=PDF_DEMO, **kw):
        with self.assertRaises(DataError) as cm:
            T6.yeu_cau_e5(signed_pdf_sha256=sha256(raw), **kw)
        self.assertEqual(cm.exception.code, ma)

    def test_yeu_cau_e5_tu_choi_truoc_side_effect(self):
        tot = _tham()
        T6.yeu_cau_e5(signed_pdf_sha256=sha256(PDF_DEMO), **tot)  # đối chứng dương
        self._loi("TRICH6_E5_THAM_SO_ALL", **{**tot, "tham_so": "ALL"})
        self._loi("TRICH6_LOAI_CHUA_CO_DANH_MUC", **{**tot, "loai_hop_dong": "KCN"})  # không mượn XD
        self._loi("TRICH6_REQUEST_ID", **{**tot, "request_id": "a b"})
        self._loi("TRICH6_E5_EXPECTED_SAI", **_tham(expected={**_expected(), "kieu": "CRM_G5_EXPECTED_V2"}))
        self._loi("TRICH6_E5_EXPECTED_SAI", **_tham(expected={**_expected(), "them": 1}))
        self._loi("TRICH6_E5_LINEAGE_SAI", **_tham(expected=_expected(revision=True)))       # bool không phải int
        self._loi("TRICH6_E5_LINEAGE_SAI", **_tham(expected=_expected(revision=0)))
        # L0-3b: LN["ky_id"] toàn chữ số nên .upper() không đổi gì (test cũ không bao giờ có chuỗi chữ hoa) → dùng UUID có chữ cái a-f;
        # đối chứng dương: bản chữ thường của ĐÚNG UUID này hợp lệ → chỉ KIỂU CHỮ làm nên lỗi.
        ky_chu = "abcdef12-1111-4111-8111-111111111111"
        T6.yeu_cau_e5(signed_pdf_sha256=sha256(PDF_DEMO), **_tham(expected=_expected(ky_id=ky_chu)))
        self._loi("TRICH6_E5_LINEAGE_SAI", **_tham(expected=_expected(ky_id=ky_chu.upper())))
        self._loi("TRICH6_E5_LINEAGE_SAI", **_tham(expected=_expected(g3_pdf_sha256="X" * 64)))
        thieu_ln = _expected()
        del thieu_ln["lineage"]["xuat_id"]
        self._loi("TRICH6_E5_LINEAGE_SAI", **_tham(expected=thieu_ln))
        # L0-3b: tham_so mặc định suy từ expected → rỗng và bị `yeu_cau_common` chặn (TRICH6_THAM_SO_RONG) TRƯỚC khi tới kiểm expected; truyền mã tường minh
        # để chỉ expected.tham_so rỗng là lý do lỗi.
        self._loi("TRICH6_E5_EXPECTED_RONG", **_tham(expected=_expected(ts=[]), tham_so=["TT-02"]))
        self._loi("TRICH6_E5_KIEU_SAI", **_tham([{"ma": "TT-10", "kieu": "phan_tram", "gia_tri": "10"}]))
        self._loi("TRICH6_E5_GIA_TRI_SAI", **_tham([{"ma": "TT-04", "kieu": "so", "gia_tri": {"so": None, "don_vi": "%"}}]))  # NULL ≠ 0
        self._loi("TRICH6_E5_GIA_TRI_SAI", **_tham([{"ma": "TT-02", "kieu": "tien", "gia_tri": {"so": "100", "tien_te": "vnd"}}]))
        self._loi("TRICH6_E5_GIA_TRI_SAI", **_tham([{"ma": "TC-02", "kieu": "ngay", "gia_tri": "2026-02-30"}]))
        trung = [TS[1], {**TS[1]}]
        self._loi("TRICH6_E5_EXPECTED_TRUNG", **_tham(expected=_expected(ts=trung), binding=_binding([TS[1]]), tham_so=["TT-02"]))
        self._loi("TRICH6_E5_BINDING_SAI", **_tham(binding={**_binding(), "kieu": "X"}))
        self._loi("TRICH6_E5_BINDING_CATALOG", **_tham(binding=_binding(catalog_sha256="0" * 64)))
        self._loi("TRICH6_E5_BINDING_CATALOG", **_tham(binding=_binding(loai_hop_dong="KCN")))
        self._loi("TRICH6_E5_BINDING_LINEAGE", **_tham(binding=_binding(danh_muc_rev="1")))      # cùng giá trị khác kiểu
        self._loi("TRICH6_E5_BINDING_LINEAGE", **_tham(binding=_binding(profile_sha256="0" * 64)))
        self._loi("TRICH6_E5_BINDING_MAPPING", **_tham(binding=_binding(muc={"TT-02": 4})))
        self._loi("TRICH6_E5_BINDING_MAPPING", **_tham(binding=_binding(muc={"TT-02": True})))
        self._loi("TRICH6_E5_BINDING_MAPPING", **_tham(binding=_binding(mapping=[])))
        b = _binding()
        b["mapping"].append(dict(b["mapping"][0]))
        self._loi("TRICH6_E5_BINDING_TRUNG", **_tham(binding=b))
        self._loi("TRICH6_E5_MA_KHAC", **{**tot, "tham_so": ["TT-02", "TT-04"]})
        self._loi("TRICH6_E5_MA_KHAC", **_tham(binding=_binding(TS[:2])))
        self._loi("TRICH6_E5_SHA_SAI", **{**tot, "expected_sha256": tot["expected_sha256"].upper()})
        self._loi("TRICH6_E5_SHA_KHAC", **{**tot, "expected_sha256": "0" * 64})
        self._loi("TRICH6_E5_SHA_KHAC", **{**tot, "catalog_binding_sha256": tot["expected_sha256"]})

    def test_seal_e5(self):
        yc = _yc()
        g5 = _g5_khop(yc)
        seal = {"mode": T6.MODE_E5, "signed_pdf_sha256": yc["signed_pdf_sha256"], "expected_sha256": yc["expected_sha256"],
                "catalog_binding_sha256": yc["catalog_binding_sha256"], "g5_trang_thai": "KHOP", "g5_coverage": g5["coverage"]}
        self.assertTrue(T6.seal_e5_hop_le(seal, yc, g5))
        for k, v in (("mode", "RULE_ONLY"), ("signed_pdf_sha256", "3" * 64), ("expected_sha256", "0" * 64),
                     ("catalog_binding_sha256", "0" * 64), ("g5_trang_thai", "LECH"), ("g5_coverage", list(reversed(g5["coverage"])))):
            self.assertFalse(T6.seal_e5_hop_le({**seal, k: v}, yc, g5), k)
        self.assertFalse(T6.seal_e5_hop_le({k: v for k, v in seal.items() if k != "mode"}, yc, g5))


# ================================================================== 2. g5 typed (client central)
class E5G5ClientTests(unittest.TestCase):
    def setUp(self):
        self.yc = _yc()

    def ok(self, g5):
        return T6.kiem_g5(g5, self.yc)

    def sai(self, g5, msg=""):
        with self.assertRaises(DataError, msg=msg) as cm:
            T6.kiem_g5(g5, self.yc)
        self.assertEqual(cm.exception.code, "TRICH6_E5_G5_SAI", msg)

    def test_golden_khop_lech_chua(self):
        self.assertEqual(self.ok(_g5_khop(self.yc))["trang_thai"], "KHOP")
        self.assertEqual(self.ok(_g5_khop(self.yc, nguon="OCR_DOCX"))["trang_thai"], "KHOP")  # OCR: vị trí dòng, không trang
        # tiền tệ khác → LECH (không quy đổi); 100 triệu vs 1 tỷ → LECH
        self.assertEqual(self.ok(_sang_lech(_g5_khop(self.yc), "TT-02", {"so": "1000000000", "tien_te": "USD"}))["trang_thai"], "LECH")
        self.assertEqual(self.ok(_sang_lech(_g5_khop(self.yc), "TT-02", {"so": "100000000", "tien_te": "VND"}))["trang_thai"], "LECH")
        o_sua = copy.deepcopy(BANG)
        o_sua["dong"][1][1] = {"so": "75", "don_vi": "%"}
        self.assertEqual(self.ok(_sang_lech(_g5_khop(self.yc), "TT-20", o_sua))["trang_thai"], "LECH")  # ô lịch đã sửa
        g = _sang_lech(_g5_khop(self.yc), "TT-02", {"so": "100000000", "tien_te": "VND"})
        g = _sang_thieu(g, "TT-20", "BANG_CHUA_DU", [{"dong": "Đợt 2", "ly_do": "KHONG_THAY_DONG"}])  # dòng lịch thiếu
        self.assertEqual(self.ok(g)["trang_thai"], "CHUA_DOI_CHIEU_DUOC")  # giữ lệch một phần nhưng KHÔNG coi là KHỚP/LỆCH đủ
        self.assertEqual(len(g["lech"]), 1)
        self.assertEqual(self.ok(_sang_thieu(_g5_khop(self.yc), "TT-04", "KHONG_THAY_GIA_TRI"))["trang_thai"], "CHUA_DOI_CHIEU_DUOC")

    def test_khong_doc_duoc_pdf(self):
        g = _g5_khop(self.yc)
        for ma in list(g["coverage"]):
            g = _sang_thieu(g, ma, "KHONG_DOC_DUOC_NGUON")
        g["nguon_doc"] = {"kieu": None, "pdf_sha256": self.yc["source_sha256"], "ocr_docx_sha256": None, "so_trang": None, "loi": "PDF scan, OCR tắt"}
        self.assertEqual(self.ok(g)["trang_thai"], "CHUA_DOI_CHIEU_DUOC")
        g2 = copy.deepcopy(g)
        g2["nguon_doc"]["loi"] = None
        self.sai(g2, "không đọc được nguồn phải có lỗi")
        g3 = copy.deepcopy(g)
        g3["nguon_doc"]["so_trang"] = 2
        self.sai(g3, "không đọc được thì không bịa trang")
        g4 = _g5_khop(self.yc)
        g4["nguon_doc"] = copy.deepcopy(g["nguon_doc"])
        self.sai(g4, "không có nguồn đọc mà KHỚP")

    def test_negative_gia_tri(self):
        g = _g5_khop(self.yc)
        g["khop"][1]["gia_tri"] = {"so": "100", "tien_te": "VND"}
        self.sai(g, "khop phải bằng ĐÚNG expected (100 ≠ 1000000000)")
        g = _g5_khop(self.yc)
        g["khop"][2]["gia_tri"] = {"so": None, "don_vi": "%"}
        self.sai(g, "0 ≠ NULL")
        g = _sang_lech(_g5_khop(self.yc), "TT-02", {"so": "1000000000", "tien_te": "VND"})
        self.sai(g, "lech mà bản ký = kỳ vọng")
        g = _sang_lech(_g5_khop(self.yc), "TT-04", {"so": None, "don_vi": "%"})
        self.sai(g, "lech với giá trị bản ký null")
        g = _sang_lech(_g5_khop(self.yc), "TT-02", {"so": "100000000", "tien_te": "VND"})
        g["lech"][0]["gia_tri_ky_vong"] = {"so": "100000000", "tien_te": "VND"}
        self.sai(g, "giá trị kỳ vọng phải là expected đã gửi")
        o_sua = copy.deepcopy(BANG)
        o_sua["dong"][1][1] = {"so": "75", "don_vi": "%"}
        g = _g5_khop(self.yc)
        g["khop"][4]["gia_tri"] = o_sua
        self.sai(g, "ô bảng sửa không được nằm trong khop")
        g = _sang_thieu(_g5_khop(self.yc), "TT-10", "KHONG_THAY_GIA_TRI")
        g["thieu"][0]["gia_tri_ky_vong"] = {"so": "1", "don_vi": "%"}
        self.sai(g, "thieu mang kỳ vọng khác expected")
        g = _sang_thieu(_g5_khop(self.yc), "TT-10", "")
        self.sai(g, "thieu phải có lý do")

    def test_negative_cau_truc_va_vai(self):
        def bien(f):
            g = _g5_khop(self.yc)
            f(g)
            return g
        self.sai(bien(lambda g: g.update(them=1)), "khóa lạ")
        self.sai(bien(lambda g: g.update(kieu="CRM_G5_COMPARE_RESULT_V2")), "kiểu")
        self.sai(bien(lambda g: g.update(g3_pdf_sha256=g["signed_pdf_sha256"])), "G3 PDF không được thay vai PDF ký")
        self.sai(bien(lambda g: g.update(signed_pdf_sha256="3" * 64)), "PDF ký khác yêu cầu")
        self.sai(bien(lambda g: g.update(expected_sha256="0" * 64)), "expected SHA")
        self.sai(bien(lambda g: g.update(coverage=list(reversed(g["coverage"])))), "coverage phải đúng thứ tự expected")
        self.sai(bien(lambda g: g.update(trang_thai="LECH")), "trạng thái không nhất quán")
        self.sai(bien(lambda g: g["khop"].pop()), "thiếu một mã")
        self.sai(bien(lambda g: g["khop"].append(copy.deepcopy(g["khop"][0]))), "mã trùng")
        self.sai(bien(lambda g: g["khop"][0].update(ma="TT-99")), "mã lạ")
        self.sai(bien(lambda g: g["khop"][1].update(muc=2)), "mức khác binding")
        self.sai(bien(lambda g: g["khop"][1].update(kieu="so")), "kiểu khác expected")
        self.sai(bien(lambda g: g["khop"][1].update(trich_dan=" ")), "khop thiếu trích dẫn")
        self.sai(bien(lambda g: g["khop"][1].update(vi_tri_do_duoc=[])), "khop thiếu vị trí")
        self.sai(bien(lambda g: g["khop"][1]["vi_tri_do_duoc"][0].update(trang=3)), "trang > số trang")
        self.sai(bien(lambda g: g["khop"][1]["vi_tri_do_duoc"][0].update(trang=0)), "trang 0")
        self.sai(bien(lambda g: g["khop"][1]["vi_tri_do_duoc"][0].update(dong=0)), "dòng 0")
        self.sai(bien(lambda g: g["khop"][1]["vi_tri_do_duoc"][0].update(pdf_sha256="3" * 64)), "vị trí trỏ PDF khác")
        self.sai(bien(lambda g: g["khop"][1]["vi_tri_do_duoc"][0].update(nguon="OCR_DOCX")), "vị trí khác nguồn đọc")
        self.sai(bien(lambda g: g["nguon_doc"].update(pdf_sha256="3" * 64)), "nguon_doc trỏ PDF khác")
        self.sai(bien(lambda g: g["nguon_doc"].update(so_trang=None)), "PDF lớp chữ phải có số trang")
        ocr = _g5_khop(self.yc, nguon="OCR_DOCX")
        ocr["khop"][0]["vi_tri_do_duoc"][0]["trang"] = 1
        self.sai(ocr, "OCR không bịa trang")
        ocr = _g5_khop(self.yc, nguon="OCR_DOCX")
        ocr["nguon_doc"]["ocr_docx_sha256"] = None
        self.sai(ocr, "OCR phải ghi SHA DOCX OCR")


# ================================================================== 3. vòng đời client (IO-mock)
MA_E5 = [t["ma"] for t in TS]


class NguonGiaE5(_TC6.NguonGia):
    """NguonGia + biến thể E5: preflight công bố khối e5, raw mang common 13 trường + g5, niêm phong mang cờ E5. Hook sửa để kiểm cổng nhận."""

    def __init__(self, e5=True):
        super().__init__(ma=MA_E5)
        if e5:
            v = self.nang_luc[1]
            v["modes"] = ["RULE_ONLY", T6.MODE_E5]
            v["e5"] = {"kieu": T6.KIEU_NANG_LUC_E5, "mode": T6.MODE_E5, "san_sang": True, "ly_do": None, "implementation_sha256": "c" * 64,
                       "loai": {"XD": {"catalog_id": "XD", "catalog_sha256": CAT, "san_sang": True, "ly_do": None,
                                       "bo_trich": {"TC-02": "ngay", "TT-02": "tien", "TT-04": "so", "TT-10": "so", "TT-20": "bang"}}}}
        self.g5 = _g5_khop
        self.sua_raw = None
        self.sua_seal = None
        self.sua_tt = self._seal_e5

    def _raw(self, lu):
        yc = self.chay_body[lu]
        if yc.get("mode") != T6.MODE_E5:
            return super()._raw(lu)
        # L0-3b: raw của nguồn thật là JSON tuần tự hóa → độc lập với yêu cầu máy chủ đã lưu. Phải SAO SÂU, nếu không hook `sua_raw` sửa tại chỗ
        # (vd `kq["common"]["expected"][...] = ...`) làm hỏng luôn `chay_body` → body_sha256 của niêm phong lệch → client chờ niêm phong tới hết 1800 giây.
        cm = copy.deepcopy({k: yc[k] for k in ("contract", "request_id", "source_sha256", "catalog_sha256", "loai_hop_dong", "catalog_id",
                                               "signed_pdf_sha256", "expected", "expected_sha256", "catalog_binding", "catalog_binding_sha256")})
        cm.update(mode=T6.MODE_E5, body_sha256=T6.body_sha256(yc), tham_so_yeu_cau=copy.deepcopy(yc["tham_so"]),
                  tham_so_da_dung=copy.deepcopy(yc["tham_so"]), implementation={"sha256": "c" * 64})
        kq = {"hop_dong": "ban_ky_demo.pdf", "ten": "x", "che_do": "RULE_ONLY", "tao_luc": "2026-10-23T10:00:00", "bang": _TC6._bang(yc["tham_so"], rule=()),
              "phieu_kiem_tra": {}, "common": cm, "g5": self.g5(yc)}
        if self.sua_raw is not None:
            kq = self.sua_raw(kq)
        return json.dumps(kq, ensure_ascii=False).encode("utf-8")

    def _seal_e5(self, lu, s):
        yc = self.chay_body[lu]
        seal = (s.get("common") or {}).get("seal")
        if yc.get("mode") == T6.MODE_E5 and isinstance(seal, dict):
            g5 = json.loads(self._raw(lu)).get("g5") or {}
            seal.update(mode=T6.MODE_E5, signed_pdf_sha256=yc["signed_pdf_sha256"], expected_sha256=yc["expected_sha256"],
                        catalog_binding_sha256=yc["catalog_binding_sha256"], g5_trang_thai=g5.get("trang_thai"), g5_coverage=g5.get("coverage"))
            if self.sua_seal is not None:
                self.sua_seal(seal)
        return s


class E5ClientIoMockTests(unittest.TestCase):
    def client(self, nguon=None, goc=None):
        nguon = nguon or NguonGiaE5()
        # L0-3b: đồng hồ giả (mỗi lần đọc +1 giây) + hạn chờ 30 giây → mock không niêm phong được thì ChuaRo sau ≤ ~30 vòng, không bao giờ bận-chờ 1800 giây thật.
        tick = itertools.count()
        return nguon, T6.Trich6Client("http://127.0.0.1:18600", goc=goc, transport=nguon, ngu=lambda s: None, cho_toi_da=30.0,
                                      dong_ho=lambda: float(next(tick)))

    def goi(self, c, raw=PDF_DEMO, ten_tep="ban_ky_demo.pdf", **kw):
        return c.doi_chieu_ban_ky(raw, ten_tep=ten_tep, **_tham(**kw))

    def test_khop_dung_13_khoa_va_y_dinh_ben(self):
        goc = Path(tempfile.mkdtemp(prefix="ktt_s6e5_client_"))  # giữ lại
        nguon, c = self.client(goc=goc)
        r = self.goi(c)
        self.assertEqual(r["g5"]["trang_thai"], "KHOP")
        self.assertEqual(set(r) - {"g5"}, {"luot", "raw_ket_qua", "raw_sha256", "ket_qua", "common", "yeu_cau"})  # cùng envelope .trich()
        self.assertEqual(r["raw_sha256"], sha256(r["raw_ket_qua"]))
        b = nguon.chay_body[r["luot"]]
        self.assertEqual(set(b), set(T6.KHOA_E5))
        self.assertEqual((b["mode"], b["source_sha256"], b["signed_pdf_sha256"]), (T6.MODE_E5, sha256(PDF_DEMO), sha256(PDF_DEMO)))
        self.assertEqual(nguon.y_dinh["e5-demo-01"][0], b)  # create mang đúng thân 13 khóa
        self.assertEqual(nguon.tep[r["luot"]], PDF_DEMO)
        self.assertEqual(nguon.goi[0][:2], ("GET", "/api/trich_xuat/common"))  # preflight trước mọi POST
        d = goc / "trich6-y-dinh" / sha256(b"e5-demo-01")
        self.assertEqual((d / f"01_nguon_{sha256(PDF_DEMO)}.pdf").read_bytes(), PDF_DEMO)
        self.assertEqual(json.loads((d / "00_yeu_cau.json").read_text(encoding="utf-8"))["yeu_cau"], b)
        # thử lại cùng ý định → đối soát, không tạo lượt mới
        so_luot = nguon.luot
        r2 = self.goi(c)
        self.assertEqual((nguon.luot, r2["luot"], r2["g5"]), (so_luot, r["luot"], r["g5"]))
        # cùng request_id + gốc, expected đổi → xung đột TRƯỚC mọi gọi
        n = len(nguon.goi)
        e = _expected()
        e["tham_so"][1]["gia_tri"] = {"so": "1000000001", "tien_te": "VND"}
        with self.assertRaises(DataError) as cm:
            self.goi(c, expected=e)
        self.assertEqual(cm.exception.code, "TRICH6_XUNG_DOT")
        with self.assertRaises(DataError) as cm:  # PDF khác, cùng ý định
            self.goi(c, raw=PDF_DEMO + b"%sua\n")
        self.assertEqual(cm.exception.code, "TRICH6_XUNG_DOT")
        self.assertEqual(len(nguon.goi), n)

    def test_legacy_trich_van_8_khoa(self):
        nguon, c = self.client()
        r = c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01"], request_id="leg-e5")
        b = nguon.chay_body[r["luot"]]
        self.assertEqual(set(b), set(T6.KHOA_COMMON))
        self.assertEqual(b["mode"], "RULE_ONLY")
        self.assertNotIn("g5", r)
        self.assertEqual(r["common"]["tham_so_da_dung"], ["TC-01"])

    def test_loi_ro_truoc_side_effect(self):
        nguon, c = self.client()
        for raw, ten in ((b"PK\x03\x04demo", "ban_ky.docx"), (PDF_DEMO, "ban_ky.docx"), (b"PK\x03\x04", "ban_ky.pdf")):
            with self.assertRaises(DataError) as cm:
                self.goi(c, raw=raw, ten_tep=ten)
            self.assertEqual(cm.exception.code, "TRICH6_E5_CHI_PDF")  # không DOCX/Word thay PDF ký
        with self.assertRaises(DataError) as cm:
            c.doi_chieu_ban_ky(PDF_DEMO, ten_tep="a.pdf", **{**_tham(), "expected_sha256": "0" * 64})
        self.assertEqual(cm.exception.code, "TRICH6_E5_SHA_KHAC")
        self.assertEqual(nguon.goi, [])
        for sua in (lambda v: v.update(modes=["RULE_ONLY"]), lambda v: v.pop("e5"), lambda v: v["e5"].update(san_sang=False),
                    lambda v: v["e5"].update(implementation_sha256=None), lambda v: v["e5"]["loai"]["XD"].update(bo_trich={}),
                    lambda v: v["e5"]["loai"]["XD"].update(catalog_sha256="0" * 64)):
            nguon, c = self.client()
            sua(nguon.nang_luc[1])
            with self.assertRaises(DataError) as cm:
                self.goi(c)
            self.assertEqual(cm.exception.code, "TRICH6_KHONG_HO_TRO_E5")
            self.assertEqual([m for m, *_ in nguon.goi], ["GET"])  # chỉ preflight, zero POST

    def test_g5_sai_khong_nhan(self):
        def g5_noi_doi(yc):
            g = _sang_lech(_g5_khop(yc), "TT-02", {"so": "100000000", "tien_te": "VND"})
            g["trang_thai"] = "KHOP"  # nói dối KHỚP khi có lệch
            return g
        for hook in (g5_noi_doi, lambda yc: None, lambda yc: {**_g5_khop(yc), "coverage": []}):
            nguon, c = self.client()
            nguon.g5 = hook
            with self.assertRaises(DataError) as cm:
                self.goi(c)
            self.assertEqual(cm.exception.code, "TRICH6_E5_G5_SAI")

    def test_raw_khac_yeu_cau_khong_nhan(self):
        def doi_expected(kq):
            kq["common"]["expected"]["tham_so"][1]["gia_tri"]["so"] = "1"
            return kq
        for sua in (doi_expected, lambda kq: {**kq, "common": {**kq["common"], "mode": "RULE_ONLY"}},
                    lambda kq: {**kq, "common": {**kq["common"], "expected_sha256": "0" * 64}},
                    lambda kq: {**kq, "common": {**kq["common"], "signed_pdf_sha256": "3" * 64}}):
            nguon, c = self.client()
            nguon.sua_raw = sua
            with self.assertRaises(DataError) as cm:
                self.goi(c)
            self.assertEqual(cm.exception.code, "TRICH6_KET_QUA_KHAC_YEU_CAU")

    def test_niem_phong_e5_sai_khong_nhan(self):
        for sua in (lambda s: s.pop("mode"), lambda s: s.update(g5_trang_thai="LECH"), lambda s: s.update(expected_sha256="0" * 64),
                    lambda s: s.update(g5_coverage=[])):
            nguon, c = self.client()
            nguon.sua_seal = sua
            with self.assertRaises(DataError) as cm:
                self.goi(c)
            self.assertEqual(cm.exception.code, "TRICH6_E5_NIEM_PHONG_SAI")

    def test_mat_ack_start_doi_soat_khong_chay_lai(self):
        goc = Path(tempfile.mkdtemp(prefix="ktt_s6e5_ack_"))  # giữ lại
        nguon, c = self.client(goc=goc)
        nguon.dut_sau.add(("POST", "chay"))  # máy chủ đã nhận lệnh chạy, ACK mất
        with self.assertRaises(T6.ChuaRo):
            self.goi(c)
        r = self.goi(c)
        self.assertEqual(r["g5"]["trang_thai"], "KHOP")
        self.assertEqual((nguon.luot, len(nguon.chay_body)), (1, 1))
        self.assertEqual(sum(1 for m, p, *_ in nguon.goi if m == "POST" and p.endswith("/tep")), 1)


# ================================================================== 4. cổng host sở hữu
class _GocGia:
    def raw(self):
        return self._raw

    def _send(self, ma, body):
        self.gui = (ma, body)


class _LoiGia(Exception):
    def __init__(self, ma, thong_bao, chi_tiet=None):
        super().__init__(thong_bao)
        self.ma, self.thong_bao, self.chi_tiet = ma, thong_bao, chi_tiet


class E5HostGateTests(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp(prefix="ktt_s6e5_host_"))  # thư mục lượt giả (giữ lại)
        dv = types.SimpleNamespace(CONTRACT_COMMON=T6.CONTRACT, LoiNguoiDung=_LoiGia, _thu_muc_luot=lambda luot: d,
                                   _la_luot_common=lambda luot, dd: True, ch=None)
        self.H = TH.lop_handler_so_huu(_GocGia, dv, "tok-demo")

    def cho(self, path, raw):
        h = object.__new__(self.H)
        h._raw = raw if isinstance(raw, bytes) else json.dumps(raw, ensure_ascii=False).encode("utf-8")
        return h._cho_phep("POST", path)

    def test_create_va_chay(self):
        yc = _yc()
        leg = T6.yeu_cau_common(source_sha256="d" * 64, loai_hop_dong="XD", tham_so=["TC-01"], request_id="leg-1")
        tao = "/api/trich_xuat"
        chay = "/api/trich_xuat/20261023_100000/chay"
        self.assertTrue(self.cho(tao, {"contract": T6.CONTRACT, "request_id": "leg-1", "yeu_cau": leg}))   # legacy giữ nguyên
        self.assertTrue(self.cho(chay, leg))
        self.assertTrue(self.cho(tao, {"contract": T6.CONTRACT, "request_id": yc["request_id"], "yeu_cau": yc}))
        self.assertTrue(self.cho(chay, yc))
        thieu = {k: v for k, v in yc.items() if k != "catalog_binding_sha256"}
        self.assertFalse(self.cho(tao, {"contract": T6.CONTRACT, "request_id": yc["request_id"], "yeu_cau": thieu}))
        self.assertFalse(self.cho(chay, thieu))
        self.assertFalse(self.cho(chay, {**yc, "duong_dan": "C:/x.xlsx"}))
        self.assertFalse(self.cho(tao, {"contract": T6.CONTRACT, "request_id": yc["request_id"], "yeu_cau": {**yc, "signed_pdf_sha256": "3" * 64}}))
        self.assertFalse(self.cho(tao, {"contract": T6.CONTRACT, "request_id": "khac", "yeu_cau": yc}))
        self.assertFalse(self.cho(tao, {"contract": T6.CONTRACT, "request_id": yc["request_id"], "yeu_cau": yc, "them": 1}))
        than = json.dumps(yc, ensure_ascii=False)
        trung = ('{"contract":"%s","request_id":"%s","request_id":"%s","yeu_cau":%s}' % (T6.CONTRACT, yc["request_id"], yc["request_id"], than)).encode("utf-8")
        self.assertFalse(self.cho(tao, trung))                                          # khóa trùng
        self.assertFalse(self.cho(chay, (than[:-1] + ',"mode":"doi_chieu_ban_ky"}').encode("utf-8")))
        nan = json.dumps({**yc, "tham_so": [float("nan")]}).encode("utf-8")
        self.assertFalse(self.cho(chay, nan))                                           # NaN


# ================================================================== 5. Source6 THẬT (overlay trên private37 sở hữu, tiến trình con)
def _pdf_demo(trang):
    """PDF lớp chữ tối thiểu dựng tay (DEMO): font Type0/Identity-H + ToUnicode bfchar cho đúng ký tự NFC dùng; mỗi phần tử `trang` là danh sách dòng."""
    trang = [[unicodedata.normalize("NFC", ln) for ln in tr] for tr in trang]
    chu = sorted({c for tr in trang for ln in tr for c in ln})
    cid = {c: i + 1 for i, c in enumerate(chu)}
    bf = "".join(f"{len(chu[i:i + 100])} beginbfchar\n" + "".join(f"<{cid[c]:04X}> <{ord(c):04X}>\n" for c in chu[i:i + 100]) + "endbfchar\n"
                 for i in range(0, len(chu), 100))
    cmap = ("/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
            "/CMapName /DEMO-UCS def\n/CMapType 2 def\n1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n" + bf +
            "endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n").encode("ascii")
    obj = {1: b"<< /Type /Catalog /Pages 2 0 R >>",
           3: b"<< /Type /Font /Subtype /Type0 /BaseFont /DemoE5 /Encoding /Identity-H /DescendantFonts [4 0 R] /ToUnicode 6 0 R >>",
           4: b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /DemoE5 /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
              b"/FontDescriptor 5 0 R /DW 500 /CIDToGIDMap /Identity >>",
           5: b"<< /Type /FontDescriptor /FontName /DemoE5 /Flags 32 /FontBBox [0 -200 1000 900] /ItalicAngle 0 /Ascent 900 /Descent -200 "
              b"/CapHeight 700 /StemV 80 >>",
           6: b"<< /Length %d >>\nstream\n" % len(cmap) + cmap + b"\nendstream"}
    kids = []
    for i, tr in enumerate(trang):
        noi = ("BT /F1 11 Tf 14 TL 40 790 Td\n" + "".join("<" + "".join(f"{cid[c]:04X}" for c in ln) + "> Tj T*\n" for ln in tr) + "ET\n").encode("ascii")
        p, n = 7 + 2 * i, 8 + 2 * i
        obj[p] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % n
        obj[n] = b"<< /Length %d >>\nstream\n" % len(noi) + noi + b"\nendstream"
        kids.append(p)
    obj[2] = b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % k for k in kids) + b"] /Count %d >>" % len(kids)
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    vt = {}
    for k in sorted(obj):
        vt[k] = len(out)
        out += b"%d 0 obj\n" % k + obj[k] + b"\nendobj\n"
    xref = len(out)
    n = max(obj) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % n + b"".join(b"%010d 00000 n \n" % vt[k] for k in range(1, n))
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (n, xref)
    return bytes(out)


TRANG1 = ["HỢP ĐỒNG THI CÔNG XÂY DỰNG DEMO",
          "Số: 15/2026/HĐ-DEMO",
          "Hôm nay, ngày 15 tháng 10 năm 2026, tại Hà Nội, chúng tôi gồm các bên dưới đây.",
          "Bên A: Công ty DEMO Chủ đầu tư, đại diện ông Nguyễn Văn An, chức vụ Giám đốc.",
          "Bên B: Công ty DEMO Nhà thầu, đại diện bà Trần Thị Bình, chức vụ Giám đốc.",
          "Điều 1. Phạm vi công việc",
          "Bên B thực hiện thi công toàn bộ hạng mục theo hồ sơ thiết kế được duyệt.",
          "Điều 2. Thời gian thực hiện",
          "Thời gian thực hiện là một trăm tám mươi ngày kể từ ngày khởi công."]
TRANG2 = ["Điều 3. Giá trị hợp đồng",
          "Giá trị hợp đồng: 1.000.000.000 đồng",
          "Điều 4. Tạm ứng và thanh toán",
          "Tạm ứng 10% sau khi ký hợp đồng.",
          "Đợt 1: 30% giá trị nghiệm thu, hạn 31/12/2026",
          "Đợt 2: 70% giá trị nghiệm thu, hạn 30/06/2027",
          "Điều 5. Điều khoản chung",
          "Hai bên cam kết thực hiện đúng các điều khoản đã thỏa thuận trong văn bản này.",
          "Văn bản được lập thành bốn bản có giá trị pháp lý như nhau, mỗi bên giữ hai bản."]
DONG_TT02 = len(TRANG1) + 2          # dòng (1-based, toàn văn bản) của "Giá trị hợp đồng: ..." trên trang 2
DONG_LICH = [len(TRANG1) + 5, len(TRANG1) + 6]


def _sua(tr, cu, moi):
    return [moi if x == cu else x for x in tr]


# Tiến trình con chạy TRONG bản sao overlay: import nguồn thật, quan sát nguyên văn ra JSON; parent kết luận. Không ghi gì ngoài thư mục tạm.
CON = r'''
import hashlib, json, os, sys, time, traceback, copy
sys.dont_write_bytecode = True
CFG = json.loads(open(sys.argv[1], encoding="utf-8").read())
sys.path.insert(0, CFG["goc"])
OBS = {}


def ghi():
    with open(CFG["ra"], "w", encoding="utf-8") as f:
        f.write(json.dumps(OBS, ensure_ascii=False, indent=1, default=str))


def ma_loi(e):
    ct = getattr(e, "chi_tiet", None)
    if isinstance(ct, dict) and isinstance(ct.get("ma"), str):
        return ct["ma"]
    m = getattr(e, "ma", None)
    return m if isinstance(m, str) else None


def thu(ten, f):
    try:
        OBS[ten] = {"ok": f()}
    except BaseException as e:  # noqa: BLE001 — quan sát nguyên văn để parent kết luận
        http = getattr(e, "ma", None)
        OBS[ten] = {"loi": type(e).__name__, "ma": ma_loi(e), "http": http if isinstance(http, int) else None, "thong_bao": str(e)[:500],
                    "vet": traceback.format_exc()[-2000:]}
    ghi()


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def h(x):
    return hashlib.sha256(canon(x).encode("utf-8")).hexdigest()


def sha_tep(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


try:
    from trich_xuat import danh_muc as DM
    from trich_xuat import quy_trinh as Q
    from trich_xuat.kiem_tra import norm
except BaseException as e:  # noqa: BLE001
    OBS["_import"] = {"loi": type(e).__name__, "ten": getattr(e, "name", None), "thong_bao": str(e)[:500], "vet": traceback.format_exc()[-2000:]}
    ghi()
    sys.exit(0)

LN = CFG["ln"]
CAT = DM.CATALOG_COMMON["XD"]
BANG = CFG["bang"]


def expected(ts):
    return {"kieu": "CRM_G5_EXPECTED_V1", "lineage": dict(LN), "tham_so": copy.deepcopy(ts)}


def binding(ts, muc):
    return {"kieu": "CRM_G5_CATALOG_BINDING_V1", "loai_hop_dong": "XD", "catalog_id": "XD", "catalog_sha256": CAT["sha256"],
            "mapping": [{"ma": t["ma"], "crm_truong": "demo." + t["ma"].lower().replace("-", "_"), "muc": muc[t["ma"]]} for t in ts],
            **{k: LN[k] for k in ("danh_muc_ref", "danh_muc_rev", "danh_muc_digest", "mau_phien_ban_id", "profile_sha256")}}


def meta_demo(ts, src="5" * 64, muc=None):
    muc = muc or {t["ma"]: (0 if t["ma"].startswith("TC-") else 3) for t in ts}
    e, b = expected(ts), binding(ts, muc)
    return {"mode": "doi_chieu_ban_ky", "source_sha256": src, "signed_pdf_sha256": src, "expected": e, "expected_sha256": h(e),
            "catalog_binding": b, "catalog_binding_sha256": h(b), "g3_pdf_sha256": LN["g3_pdf_sha256"],
            "bo_trich": {m: list(v) for m, v in DM.bo_trich_e5("XD").items()}, "muc_ghim": {t["ma"]: muc[t["ma"]] for t in ts}}


def kiem(g5, m):
    try:
        Q.kiem_g5_e5(g5, m)
        return "OK"
    except Q.LoiE5 as e:
        return e.ma


# ---------------------------------------------------------------- danh mục / bộ trích / mức ghim
thu("dm_bo_trich", lambda: {"XD": {m: list(v) for m, v in DM.bo_trich_e5("XD").items()}, "KCN": DM.bo_trich_e5("KCN"),
                            "NHAO": DM.bo_trich_e5("NHAO"), "registry": sorted(DM.CATALOG_COMMON)})


def dm_demo():
    p = os.path.join(CFG["tam"], "DANH_MUC_DEMO.xlsx")
    rows = [{"ma": m, "nhom": "DEMO", "mo_ta": "DEMO " + m, "tk": "", "bk": "", "dung": True, "muc": v, "bat_buoc": "", "loai_tru": "",
             "luon_cloud": False} for m, v in (("TT-02", 3), ("TT-10", ""), ("TT-04", 5), ("TT-20", 0), ("TC-01", 1), ("TC-01", 2), ("TT-11", "x"))]
    DM._ghi(p, rows)
    return {"ghim": DM.muc_da_ghim(p), "muc_mac_dinh": {x["ma"]: x["muc"] for x in DM.load_params_ban_chup(p)}}


thu("dm_ghim_demo", dm_demo)

# ---------------------------------------------------------------- token typed
thu("token", lambda: {s: [list(t) for t in Q._token_e5(norm(s))] for s in CFG["token"]})
thu("legacy_compare_100_1000", lambda: Q.compare("100", "1000"))  # chỉ ghi nhận hành vi substring cũ; E5 không dùng

# ---------------------------------------------------------------- _g5_tu: ma trận dòng DEMO (không PDF)
L = CFG["dong"]
PARAMS = CFG["params"]
TC = CFG["tc"]
TS_DU = CFG["ts_du"]


def g5_case(lines, ts, tc=None, nd=None):
    m = meta_demo(ts)
    nd = nd or {"kieu": "PDF_LOP_CHU", "pdf_sha256": m["signed_pdf_sha256"], "ocr_docx_sha256": None, "so_trang": 2, "loi": None}
    trang = [1 if i < 5 else 2 for i in range(len(lines))] if nd["kieu"] == "PDF_LOP_CHU" else None
    g5 = Q._g5_tu(m, nd, lines, trang, PARAMS, TC if tc is None else tc)
    return {"g5": g5, "kiem": kiem(g5, m)}


def doi(lines, i, moi):
    x = list(lines)
    x[i] = moi
    return x


TS_100 = [t if t["ma"] != "TT-02" else {"ma": "TT-02", "kieu": "tien", "gia_tri": {"so": "100", "tien_te": "VND"}} for t in TS_DU]
TS_KIEU = [t if t["ma"] != "TT-02" else {"ma": "TT-02", "kieu": "so", "gia_tri": {"so": "1000000000", "don_vi": None}} for t in TS_DU]
TC_16 = {**TC, "TC-02": {"gia_tri": "16/10/2026", "trich_dan": "Hôm nay, ngày 16/10/2026, tại Hà Nội"}}
TC_LECH_VT = {**TC, "TC-01": {"gia_tri": "15/2026/HĐ-DEMO", "trich_dan": "Số: KHÔNG CÓ TRONG VĂN BẢN"}}
CASES = {
    "khop": (L, TS_DU, None, None),
    "lech_100tr": (doi(L, 4, "Giá trị hợp đồng: 100.000.000 đồng"), TS_DU, None, None),
    "lech_100_vs_1000": (doi(L, 4, "Giá trị hợp đồng: 1.000 đồng"), TS_100, None, None),
    "lech_usd": (doi(L, 4, "Giá trị hợp đồng: 1.000.000.000 USD"), TS_DU, None, None),
    "khong_0": (doi(L, 5, "Thuế suất GTGT: không chịu thuế"), TS_DU, None, None),
    "ngay_lech": (doi(L, 2, "Hôm nay, ngày 16/10/2026, tại Hà Nội"), TS_DU, TC_16, None),
    "tc_khong_vi_tri": (L, TS_DU, TC_LECH_VT, None),
    "nhieu_gia_tri": (L + ["Giá trị hợp đồng sau điều chỉnh: 1.200.000.000 đồng"], TS_DU, None, None),
    "bang_thieu_dong": (L[:-1], TS_DU, None, None),
    "bang_o_sua": (doi(L, 9, "Đợt 2: 75% giá trị nghiệm thu, hạn 30/06/2027"), TS_DU, None, None),
    "chua_bo_trich": (L, TS_DU + [{"ma": "TT-21", "kieu": "text", "gia_tri": "DEMO"}], None, None),
    "kieu_khac_bo_trich": (L, TS_KIEU, None, None),
    "ocr": (L, TS_DU, None, {"kieu": "OCR_DOCX", "pdf_sha256": "5" * 64, "ocr_docx_sha256": "6" * 64, "so_trang": None, "loi": None}),
}
for ten, (ls, ts, tc, nd) in CASES.items():
    thu("g5_" + ten, lambda ls=ls, ts=ts, tc=tc, nd=nd: g5_case(ls, ts, tc, nd))


def khong_doc():
    m = meta_demo(TS_DU)
    g5 = Q.g5_khong_doc_duoc(m, "ValueError: PDF scan, OCR tắt")
    return {"g5": g5, "kiem": kiem(g5, m)}


thu("g5_khong_doc", khong_doc)


def g5_sua():
    m = meta_demo(TS_DU)
    base = g5_case(L, TS_DU)["g5"]
    out = {"goc": kiem(base, m)}

    def bien(ten, f, req=None):
        g = copy.deepcopy(base)
        f(g)
        out[ten] = kiem(g, req or m)
    bien("trang_thai", lambda g: g.update(trang_thai="LECH"))
    bien("coverage", lambda g: g.update(coverage=list(reversed(g["coverage"]))))
    bien("trang_vuot", lambda g: g["khop"][0]["vi_tri_do_duoc"][0].update(trang=3))
    bien("gia_tri_100", lambda g: next(x for x in g["khop"] if x["ma"] == "TT-02").update(gia_tri={"so": "100", "tien_te": "VND"}))
    bien("g3_trung_ky", lambda g: g.update(g3_pdf_sha256=g["signed_pdf_sha256"]))
    bien("bo_ma", lambda g: g["khop"].pop())
    bien("khoa_la", lambda g: g.update(them=1))
    bien("khong_nguon_ma_khop", lambda g: g.update(nguon_doc={"kieu": None, "pdf_sha256": "5" * 64, "ocr_docx_sha256": None, "so_trang": None,
                                                              "loi": "X"}))
    m2 = copy.deepcopy(m)
    m2["muc_ghim"]["TT-02"] = 2
    bien("muc_ghim_khac", lambda g: None, m2)
    return out


thu("g5_sua", g5_sua)

# ---------------------------------------------------------------- PDF lớp chữ thật (read_contract + doi_chieu_e5), không qua máy chủ
TS_PDF = CFG["ts_pdf"]
PDF = CFG["pdf"]


def pdf_g5(ten, ky=None):
    from trich_xuat.doc_hop_dong import read_contract
    p = PDF[ten]
    info = read_contract(p)
    m = meta_demo(TS_PDF, src=sha_tep(PDF[ky or ten]))
    g5 = Q.doi_chieu_e5(m, PARAMS, p, info, None, p, {})
    return {"dong": info["text"].split("\n"), "g5": g5, "kiem": kiem(g5, m)}


for ten, ky in (("khop", None), ("lech_tien", None), ("lech_bang", None), ("lech_tien_sha_khac", "khop")):
    thu("pdf_" + ten, lambda ten=ten, ky=ky: pdf_g5("lech_tien" if ten == "lech_tien_sha_khac" else ten, ky))


def scan_xu_ly():
    params = [DM.to_param(m, "DEMO", "DEMO " + m, "", "", 3) for m in [t["ma"] for t in TS_PDF]]
    m = meta_demo(TS_PDF, src=sha_tep(PDF["scan"]))
    tx = Q.TrichXuat(params, out_dir=os.path.join(CFG["tam"], "xu_ly_scan"), che_do="RULE_ONLY", meta=m)
    kq = tx.xu_ly(PDF["scan"])
    return {"g5": kq["g5"], "che_do": kq["che_do"], "bang": [d["ma"] for d in kq["bang"]], "kiem": kiem(kq["g5"], m)}


thu("pdf_scan_xu_ly", scan_xu_ly)

# ---------------------------------------------------------------- máy chủ (dich_vu) — cùng vòng đời common/v1
try:
    from may_chu import dich_vu as DV
except BaseException as e:  # noqa: BLE001
    OBS["_import_dv"] = {"loi": type(e).__name__, "ten": getattr(e, "name", None), "thong_bao": str(e)[:500], "vet": traceback.format_exc()[-2000:]}
    ghi()
    sys.exit(0)

P_CAT = str(CAT["path"])
GHIM, CO = {}, []
try:
    GHIM = DM.muc_da_ghim(P_CAT)
    CO = [p["ma"] for p in DM.load_params_ban_chup(P_CAT)]
except BaseException as e:  # noqa: BLE001
    OBS["dv_catalog_loi"] = {"loi": type(e).__name__, "thong_bao": str(e)[:500]}
PIPE = [t for t in TS_PDF if t["ma"] in GHIM and t["ma"] in CO]
OBS["dv_ghim"] = {"ghim": GHIM, "co": CO, "pipe": [t["ma"] for t in PIPE], "catalog_sha_khop": sha_tep(P_CAT) == CAT["sha256"] if os.path.isfile(P_CAT) else None}
ghi()


def body(raw, ts, rid, muc=None):
    src = hashlib.sha256(raw).hexdigest()
    muc = muc or {t["ma"]: GHIM.get(t["ma"], 3) for t in ts}
    e, b = expected(ts), binding(ts, muc)
    return {"contract": DV.CONTRACT_COMMON, "mode": "doi_chieu_ban_ky", "loai_hop_dong": "XD", "catalog_id": "XD", "catalog_sha256": CAT["sha256"],
            "source_sha256": src, "request_id": rid, "tham_so": [t["ma"] for t in ts], "signed_pdf_sha256": src, "expected": e,
            "expected_sha256": h(e), "catalog_binding": b, "catalog_binding_sha256": h(b)}


RAW_KHOP = open(PDF["khop"], "rb").read()
B = body(RAW_KHOP, TS_PDF, "kiem-e5")
L8 = {k: B[k] for k in ("contract", "loai_hop_dong", "catalog_id", "catalog_sha256", "source_sha256", "request_id", "tham_so")}
L8["mode"] = "RULE_ONLY"


def kc(x):
    q = DV._kiem_common(x)
    return {"mode": q.get("mode"), "body_sha256": q["body_sha256"], "h": h(x)}


thu("dv_kiem_legacy", lambda: kc(L8))
thu("dv_kiem_legacy_khoa_e5", lambda: kc({**L8, "expected": B["expected"]}))
thu("dv_kiem_e5", lambda: kc(B))


def bo(k):
    x = dict(B)
    x.pop(k)
    return x


def e_sai():
    e = expected(TS_PDF)
    e["kieu"] = "X"
    return e


def e_gia_tri():
    e = expected(TS_PDF)
    e["tham_so"][0]["gia_tri"] = {"so": "1e9", "tien_te": "VND"}
    return e


def bind_cat():
    b = copy.deepcopy(B["catalog_binding"])
    b["catalog_sha256"] = "0" * 64
    return b


AM = {
    "thieu": bo("catalog_binding_sha256"),
    "la": {**B, "duong_dan": "C:/catalog_khac.xlsx"},
    "all": {**B, "tham_so": "ALL"},
    "pdf_ky": {**B, "signed_pdf_sha256": "0" * 64},
    "expected_sai": {**B, "expected": e_sai()},
    "gia_tri_sai": {**B, "expected": e_gia_tri()},
    "binding_catalog": {**B, "catalog_binding": bind_cat()},
    "sha_khac": {**B, "expected_sha256": "0" * 64},
    "ma_khac": {**B, "tham_so": B["tham_so"][:1]},
    "catalog_ngoai": {**B, "catalog_sha256": "0" * 64},
    "loai_kcn": {**B, "loai_hop_dong": "KCN"},
}
for ten, x in AM.items():
    thu("dv_am_" + ten, lambda x=x: kc(x))
thu("dv_nang_luc", DV.nang_luc_common)


def cho(luot, ack, st):
    het = time.time() + CFG.get("cho", 300)
    while True:
        s = DV.chi_tiet_luot(luot)
        cm = s.get("common") or {}
        if cm.get("tt") not in ("capturing", "running", None) or time.time() > het:
            break
        time.sleep(0.5)
    out = {"luot": luot, "ack": ack, "start": {"lap_lai": st.get("lap_lai"), "trang_thai_common": st.get("trang_thai_common")}, "tt": s.get("tt"),
           "common_tt": cm.get("tt"), "loi": cm.get("loi"), "seal": cm.get("seal"), "thong_bao": s.get("thong_bao"), "log": (s.get("log") or [])[-30:],
           "tai": s.get("tai")}
    if cm.get("tt") == "done":
        kq = json.loads((DV._thu_muc_luot(luot) / cm["seal"]["ref"]).read_text(encoding="utf-8"))
        out.update(g5=kq.get("g5"), che_do=kq.get("che_do"), bang=[d.get("ma") for d in kq.get("bang") or []])
    return out


def chay(ten_pdf, rid, ts=None, muc=None, ten_tep="ban_ky_demo.pdf", raw=None):
    raw = raw if raw is not None else open(PDF[ten_pdf], "rb").read()
    b = body(raw, PIPE if ts is None else ts, rid, muc)
    ack = DV.luot_moi_common({"contract": DV.CONTRACT_COMMON, "request_id": rid, "yeu_cau": b})
    DV.tai_len_hop_dong(ack["luot"], ten_tep, raw)
    st = DV.chay_luot(ack["luot"], b)
    return cho(ack["luot"], ack, st), b, raw


def lat_cuoi(p):
    with open(p, "r+b") as f:
        f.seek(-1, 2)
        c = f.read(1)
        f.seek(-1, 2)
        f.write(b" " if c != b" " else b"\n")


def sua_seal(p):
    b = open(p, "rb").read()
    moi = b.replace(b'"g5_trang_thai":"KHOP"', b'"g5_trang_thai":"LECH"')
    if moi == b:
        raise RuntimeError("seal không có g5_trang_thai KHOP để sửa")
    with open(p, "r+b") as f:  # cùng độ dài, không xóa/thay tệp
        f.write(moi)


if PIPE:
    def khop():
        r, b, raw = chay("khop", "e5-khop")
        lai = DV.luot_moi_common({"contract": DV.CONTRACT_COMMON, "request_id": "e5-khop", "yeu_cau": b})
        st2 = DV.chay_luot(lai["luot"], b)
        r["lap_lai"] = {"create": lai, "start_lap_lai": st2.get("lap_lai")}
        try:
            DV.tai_len_hop_dong(r["luot"], "khac.pdf", raw + b"%khac\n")
            r["tai_bytes_khac"] = "NHAN"
        except BaseException as e:  # noqa: BLE001
            r["tai_bytes_khac"] = ma_loi(e)
        e2 = copy.deepcopy(b)
        e2["expected"]["tham_so"][0]["gia_tri"] = {"so": "1", "tien_te": "VND"} if e2["expected"]["tham_so"][0]["kieu"] == "tien" else \
            e2["expected"]["tham_so"][0]["gia_tri"]
        e2["expected"]["lineage"]["revision"] = 2
        e2["expected_sha256"] = h(e2["expected"])
        try:
            DV.luot_moi_common({"contract": DV.CONTRACT_COMMON, "request_id": "e5-khop", "yeu_cau": e2})
            r["expected_doi_cung_rid"] = "NHAN"
        except BaseException as e:  # noqa: BLE001
            r["expected_doi_cung_rid"] = ma_loi(e)
        return r
    thu("dv_khop", khop)
    thu("dv_lech_tien", lambda: chay("lech_tien", "e5-lech-tien")[0])
    thu("dv_lech_bang", lambda: chay("lech_bang", "e5-lech-bang")[0])
    thu("dv_scan", lambda: chay("scan", "e5-scan")[0])
    thu("dv_muc_khac", lambda: chay("khop", "e5-muc-khac", muc={t["ma"]: (GHIM[t["ma"]] + 1) % 4 for t in PIPE})[0])
    thu("dv_docx_thay_pdf", lambda: chay(None, "e5-docx", ten_tep="ban_ky.docx", raw=b"PK\x03\x04DEMO-docx")[0])
    thu("dv_khong_phai_pdf", lambda: chay(None, "e5-khong-pdf", raw=b"NOT-A-PDF DEMO")[0])

    def tamper(chon):
        r, _b, _raw = chay("khop", "e5-sua-" + chon)
        if r["common_tt"] != "done":
            return {"truoc": r, "sau": None}
        d = DV._thu_muc_luot(r["luot"])
        if chon == "raw":
            lat_cuoi(d / r["seal"]["ref"])
        elif chon == "expected":
            lat_cuoi(next((d / "_common").glob("EXPECTED_*.json")))
        elif chon == "catalog":
            lat_cuoi(next((d / "_common").glob("DANH_MUC_*.xlsx")))
        elif chon == "seal":
            sua_seal(d / "_common" / "ket_qua_seal.json")
        s = DV.chi_tiet_luot(r["luot"])
        cm = s.get("common") or {}
        return {"truoc": r["common_tt"], "truoc_g5": (r.get("g5") or {}).get("trang_thai"), "sau": cm.get("tt"), "sau_loi": cm.get("loi"),
                "sau_seal": cm.get("seal"), "sau_tai": s.get("tai"), "sau_s_tt": s.get("tt")}
    for chon in ("raw", "expected", "catalog", "seal"):
        thu("dv_sua_" + chon, lambda chon=chon: tamper(chon))
OBS["_xong"] = True
ghi()
'''

DONG_DEMO = ["HỢP ĐỒNG THI CÔNG XÂY DỰNG DEMO",
             "Số: 15/2026/HĐ-DEMO",
             "Hôm nay, ngày 15/10/2026, tại Hà Nội",
             "Điều 1. Giá trị hợp đồng",
             "Giá trị hợp đồng: 1.000.000.000 đồng",
             "Thuế suất GTGT: 0%",
             "Điều 2. Tạm ứng và thanh toán",
             "Tạm ứng 10% sau khi ký hợp đồng.",
             "Đợt 1: 30% giá trị nghiệm thu, hạn 31/12/2026",
             "Đợt 2: 70% giá trị nghiệm thu, hạn 30/06/2027"]
PARAMS_DEMO = [{"ma": "TT-02", "noi_dung_kws": ["giá trị hợp đồng", "bằng chữ"], "bat_buoc": ["giá", "giá trị"], "loai_tru": ["tạm ứng", "bảo lãnh"]},
               {"ma": "TT-04", "noi_dung_kws": ["vat", "gtgt", "thuế suất"], "bat_buoc": ["vat", "gtgt", "thuế"], "loai_tru": []},
               {"ma": "TT-10", "noi_dung_kws": ["tạm ứng"], "bat_buoc": ["tạm ứng"], "loai_tru": []}]
TC_DEMO = {"TC-01": {"gia_tri": "15/2026/HĐ-DEMO", "trich_dan": "Số: 15/2026/HĐ-DEMO"},
           "TC-02": {"gia_tri": "15/10/2026", "trich_dan": "Hôm nay, ngày 15/10/2026, tại Hà Nội"}}
TS_DU = [{"ma": "TC-01", "kieu": "text", "gia_tri": "15/2026/HĐ-DEMO"}] + TS
TS_PDF = [TS[1], TS[3], TS[4]]          # TT-02 tiền, TT-10 %, TT-20 bảng lịch — mã chạy được qua RULE_ONLY không cần TC master_hd
TOKEN = ["Giá trị hợp đồng: 1.000.000.000 đồng", "Tạm ứng 10% sau khi ký", "hạn 31/12/2026", "0,5 USD", "ngày 15 tháng 10 năm 2026",
         "ngày 30/02/2026", "1.000 đồng", "100 đ", "200 EUR"]


def _vt(dong, trang):
    return {"nguon": "PDF_LOP_CHU", "pdf_sha256": "5" * 64, "ocr_docx_sha256": None, "trang": trang, "dong": dong}


class E5OverlayNguonTests(unittest.TestCase):
    """Source6 THẬT trên bản sao private37 + ba artefact E5. Một tiến trình con duy nhất (quan sát) — các test dưới đây kết luận trên quan sát đó."""
    OBS: dict = {}

    @classmethod
    def setUpClass(cls):
        p37 = os.environ.get(ENV_P37)
        if not p37:
            raise unittest.SkipTest(f"NOT_VERIFIED: chưa đặt {ENV_P37} (gốc private37 sở hữu) — skip KHÔNG phải PASS")
        p37 = Path(p37)
        for rel in ARTEFACT:
            a, b = p37 / rel, BASELINE / rel
            if not a.is_file() or not b.is_file() or a.read_bytes() != b.read_bytes():
                raise unittest.SkipTest(f"NOT_VERIFIED: private37 {rel} khác baseline docs/E5-SOURCE6-READONLY — không ghép overlay")
        tam = Path(tempfile.mkdtemp(prefix="ktt_s6e5_overlay_"))  # GIỮ LẠI toàn bộ (không dọn)
        goc = tam / "nguon"
        bo_goc = {"ket_qua_AI", "co_so_du_lieu", "ocr", "cau_hinh_may_ai.json", "khoa_api.json"}

        def bo_qua(thu_muc, ten):
            rel = os.path.relpath(thu_muc, p37).replace("\\", "/")
            out = {t for t in ten if t in ("__pycache__", ".git") or t.endswith((".pyc", ".pyo"))}
            if rel == ".":
                out |= {t for t in ten if t in bo_goc}
            out |= {t for t in ten if (t if rel == "." else f"{rel}/{t}") in ARTEFACT}
            return out
        shutil.copytree(p37, goc, ignore=bo_qua)
        for rel in ARTEFACT:
            (goc / rel).write_bytes((OVERLAY / rel).read_bytes())
        (goc / "cau_hinh_may_ai.json").write_text(json.dumps({"ocr": {"che_do": "tat"}}), encoding="utf-8")  # chỉ bản sao tạm: OCR tắt
        pdf = tam / "pdf"
        pdf.mkdir()
        fx = {"khop": [TRANG1, TRANG2],
              "lech_tien": [TRANG1, _sua(TRANG2, "Giá trị hợp đồng: 1.000.000.000 đồng", "Giá trị hợp đồng: 100.000.000 đồng")],
              "lech_bang": [TRANG1, _sua(TRANG2, "Đợt 2: 70% giá trị nghiệm thu, hạn 30/06/2027", "Đợt 2: 75% giá trị nghiệm thu, hạn 30/06/2027")],
              "scan": [[]]}
        duong = {}
        for ten, tr in fx.items():
            duong[ten] = str(pdf / f"ban_ky_{ten}.pdf")
            Path(duong[ten]).write_bytes(_pdf_demo(tr))
        cfg = {"goc": str(goc), "tam": str(tam), "ra": str(tam / "quan_sat.json"), "cho": 300, "ln": LN, "bang": BANG, "dong": DONG_DEMO,
               "params": PARAMS_DEMO, "tc": TC_DEMO, "ts_du": TS_DU, "ts_pdf": TS_PDF, "pdf": duong, "token": TOKEN}
        (tam / "dau_vao.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        con = tam / "kiem_con"
        con.mkdir()
        (con / "con_e5.py").write_text(CON, encoding="utf-8")
        env = dict(os.environ)  # kế thừa A517/no-bytecode/PYTHONUSERBASE/PYTHONPATH nguyên trạng
        du = tam / "du_lieu"
        env.update(HD_DU_LIEU=str(du), HD_OUT_DIR=str(du / "trich_xuat"), HD_DANH_MUC_HD=str(du / "DANH_MUC_HD" / "DANH_MUC_HOP_DONG.xlsx"),
                   HD_CSDL=str(tam / "csdl" / "hop_dong.db"), HD_THU_MUC_KHOA=str(tam / "khoa"), PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        kq = subprocess.run([sys.executable, str(con / "con_e5.py"), str(tam / "dau_vao.json")], cwd=str(goc), env=env, capture_output=True,
                            timeout=3600)
        (tam / "con_stdout.txt").write_bytes(kq.stdout)
        (tam / "con_stderr.txt").write_bytes(kq.stderr)
        cls.TAM = tam
        ra = tam / "quan_sat.json"
        if not ra.is_file():
            raise AssertionError(f"Tiến trình con không ghi quan sát (mã {kq.returncode}); xem {tam}")
        cls.OBS = json.loads(ra.read_text(encoding="utf-8"))
        imp = cls.OBS.get("_import")
        if imp and imp["loi"] == "ModuleNotFoundError" and (imp.get("ten") or "").split(".")[0] not in ("trich_xuat", "may_chu"):
            raise unittest.SkipTest(f"NOT_VERIFIED: môi trường thiếu thư viện {imp.get('ten')} — {tam}")
        if imp:
            raise AssertionError(f"Import nguồn overlay lỗi: {imp}")

    def o(self, ten):
        v = self.OBS.get(ten)
        self.assertIsNotNone(v, f"thiếu quan sát {ten} (xem {self.TAM})")
        self.assertNotIn("loi", v, f"{ten}: {v}")
        return v["ok"]

    def can_pdf(self, v):
        if "loi" in v and ("pdfplumber" in v.get("thong_bao", "") or v.get("loi") == "ModuleNotFoundError"):
            self.skipTest(f"NOT_VERIFIED: máy thiếu thư viện đọc lớp chữ PDF — {v['thong_bao']}")

    # -------------------------------------------------------------- danh mục / mức ghim / token
    def test_bo_trich_va_muc_ghim(self):
        v = self.o("dm_bo_trich")
        self.assertEqual(v["XD"], {"TC-01": ["QUY_TAC_TC", "text"], "TC-02": ["QUY_TAC_TC", "ngay"], "TT-02": ["NEO_DONG", "tien"],
                                   "TT-04": ["NEO_DONG", "so"], "TT-10": ["NEO_DONG", "so"], "TT-20": ["BANG_DONG", "bang"]})
        self.assertEqual((v["KCN"], v["NHAO"], v["registry"]), ({}, {}, ["XD"]))  # không mượn XD
        g = self.o("dm_ghim_demo")
        self.assertEqual(g["ghim"], {"TT-02": 3, "TT-20": 0})  # trống/5/'x'/mã trùng → KHÔNG có mức (không default 2)
        self.assertEqual(g["muc_mac_dinh"]["TT-10"], 2)          # đối chứng: _muc legacy tự default 2 — E5 không dùng

    def test_token_typed(self):
        t = self.o("token")
        self.assertEqual(t["Giá trị hợp đồng: 1.000.000.000 đồng"], [["so", "1000000000", "VND"]])
        self.assertEqual(t["Tạm ứng 10% sau khi ký"], [["so", "10", "%"]])
        self.assertEqual(t["hạn 31/12/2026"], [["ngay", "2026-12-31", None]])
        self.assertEqual(t["0,5 USD"], [["so", "0.5", "USD"]])
        self.assertEqual(t["ngày 15 tháng 10 năm 2026"], [["ngay", "2026-10-15", None]])
        self.assertEqual(t["ngày 30/02/2026"], [["ngay", None, None]])   # ngày không có thật → không phải giá trị
        self.assertEqual(t["1.000 đồng"], [["so", "1000", "VND"]])
        self.assertEqual(t["100 đ"], [["so", "100", "VND"]])
        self.assertEqual(t["200 EUR"], [["so", "200", "EUR"]])

    # -------------------------------------------------------------- _g5_tu ma trận
    def g5(self, ten, tt):
        v = self.o("g5_" + ten)
        self.assertEqual(v["kiem"], "OK", ten)
        self.assertEqual(v["g5"]["trang_thai"], tt, ten)
        return v["g5"]

    def test_g5_khop_va_vi_tri(self):
        g = self.g5("khop", "KHOP")
        self.assertEqual(g["coverage"], [t["ma"] for t in TS_DU])
        k = {x["ma"]: x for x in g["khop"]}
        self.assertEqual(k["TT-02"]["vi_tri_do_duoc"], [_vt(5, 1)])
        self.assertEqual(k["TT-02"]["trich_dan"], DONG_DEMO[4])
        self.assertEqual(k["TT-04"]["gia_tri"], {"so": "0", "don_vi": "%"})  # 0 thật khớp 0
        self.assertEqual(k["TT-20"]["vi_tri_do_duoc"], [_vt(9, 2), _vt(10, 2)])
        self.assertEqual((k["TC-01"]["muc"], k["TT-02"]["muc"]), (0, 3))
        o = self.g5("ocr", "KHOP")
        self.assertEqual(o["khop"][0]["vi_tri_do_duoc"][0]["trang"], None)  # OCR: không bịa trang
        self.assertEqual(o["nguon_doc"]["ocr_docx_sha256"], "6" * 64)

    def test_g5_lech(self):
        g = self.g5("lech_100tr", "LECH")
        self.assertEqual(g["lech"], [{"ma": "TT-02", "muc": 3, "kieu": "tien", "gia_tri_ky_vong": {"so": "1000000000", "tien_te": "VND"},
                                      "gia_tri_ban_ky": {"so": "100000000", "tien_te": "VND"}, "trich_dan": "Giá trị hợp đồng: 100.000.000 đồng",
                                      "vi_tri_do_duoc": [_vt(5, 1)]}])
        g = self.g5("lech_100_vs_1000", "LECH")   # legacy substring có thể coi 100 ~ 1000 là ĐÚNG; E5 so typed nguyên vẹn
        self.assertEqual(g["lech"][0]["gia_tri_ban_ky"], {"so": "1000", "tien_te": "VND"})
        g = self.g5("lech_usd", "LECH")
        self.assertEqual(g["lech"][0]["gia_tri_ban_ky"], {"so": "1000000000", "tien_te": "USD"})  # không quy đổi tiền tệ
        g = self.g5("ngay_lech", "LECH")
        self.assertEqual((g["lech"][0]["ma"], g["lech"][0]["gia_tri_ban_ky"]), ("TC-02", "2026-10-16"))
        g = self.g5("bang_o_sua", "LECH")
        self.assertEqual(g["lech"][0]["ma"], "TT-20")
        self.assertEqual(g["lech"][0]["gia_tri_ban_ky"]["dong"][1], ["Đợt 2", {"so": "75", "don_vi": "%"}, "2027-06-30"])
        self.assertEqual(g["lech"][0]["vi_tri_do_duoc"], [_vt(9, 2), _vt(10, 2)])

    def test_g5_chua_doi_chieu_duoc(self):
        def thieu(ten):
            g = self.g5(ten, "CHUA_DOI_CHIEU_DUOC")
            return {x["ma"]: x for x in g["thieu"]}
        self.assertEqual(thieu("khong_0")["TT-04"]["ly_do"], "KHONG_THAY_GIA_TRI")      # không có số → KHÔNG thành 0/KHỚP
        self.assertEqual(thieu("tc_khong_vi_tri")["TC-01"]["ly_do"], "KHONG_XAC_DINH_VI_TRI")
        self.assertEqual(thieu("nhieu_gia_tri")["TT-02"]["ly_do"], "NHIEU_GIA_TRI")
        t = thieu("bang_thieu_dong")["TT-20"]
        self.assertEqual(t["ly_do"], "BANG_CHUA_DU")
        self.assertIn({"dong": "Đợt 2", "ly_do": "KHONG_THAY_DONG"}, t["mot_phan"])
        self.assertEqual(thieu("chua_bo_trich")["TT-21"]["ly_do"], "CHUA_CO_BO_TRICH")  # mã chưa có bộ trích → không đoán
        self.assertEqual(thieu("kieu_khac_bo_trich")["TT-02"]["ly_do"], "KIEU_KHAC_BO_TRICH")
        k = self.o("g5_khong_doc")
        self.assertEqual((k["kiem"], k["g5"]["trang_thai"], k["g5"]["khop"], k["g5"]["lech"]), ("OK", "CHUA_DOI_CHIEU_DUOC", [], []))
        self.assertEqual({x["ly_do"] for x in k["g5"]["thieu"]}, {"KHONG_DOC_DUOC_NGUON"})
        self.assertEqual(len(k["g5"]["thieu"]), len(TS_DU))

    def test_g5_sua_khong_nhan(self):
        s = self.o("g5_sua")
        self.assertEqual(s.pop("goc"), "OK")
        self.assertEqual(s, {k: "E5_G5_SAI" for k in ("trang_thai", "coverage", "trang_vuot", "gia_tri_100", "g3_trung_ky", "bo_ma", "khoa_la",
                                                       "khong_nguon_ma_khop", "muc_ghim_khac")})

    # -------------------------------------------------------------- PDF lớp chữ dựng tay
    def test_pdf_khop_va_lech_co_vi_tri(self):
        v = self.OBS.get("pdf_khop") or {}
        self.can_pdf(v)
        k = self.o("pdf_khop")
        self.assertEqual(k["dong"], [unicodedata.normalize("NFC", x) for x in TRANG1 + TRANG2])
        self.assertEqual((k["kiem"], k["g5"]["trang_thai"], k["g5"]["nguon_doc"]["kieu"], k["g5"]["nguon_doc"]["so_trang"]),
                         ("OK", "KHOP", "PDF_LOP_CHU", 2))
        vt = {x["ma"]: x["vi_tri_do_duoc"] for x in k["g5"]["khop"]}
        self.assertEqual([(p["trang"], p["dong"]) for p in vt["TT-02"]], [(2, DONG_TT02)])
        self.assertEqual([(p["trang"], p["dong"]) for p in vt["TT-20"]], [(2, d) for d in DONG_LICH])
        lt = self.o("pdf_lech_tien")
        self.assertEqual((lt["kiem"], lt["g5"]["trang_thai"]), ("OK", "LECH"))
        self.assertEqual([x["ma"] for x in lt["g5"]["lech"]], ["TT-02"])
        self.assertEqual(lt["g5"]["lech"][0]["gia_tri_ban_ky"], {"so": "100000000", "tien_te": "VND"})
        self.assertEqual([(p["trang"], p["dong"]) for p in lt["g5"]["lech"][0]["vi_tri_do_duoc"]], [(2, DONG_TT02)])
        lb = self.o("pdf_lech_bang")
        self.assertEqual((lb["kiem"], lb["g5"]["trang_thai"], [x["ma"] for x in lb["g5"]["lech"]]), ("OK", "LECH", ["TT-20"]))
        self.assertEqual([(p["trang"], p["dong"]) for p in lb["g5"]["lech"][0]["vi_tri_do_duoc"]], [(2, d) for d in DONG_LICH])
        sk = self.o("pdf_lech_tien_sha_khac")    # PDF đọc khác bytes PDF ký đã chụp → không đối chiếu
        self.assertEqual((sk["g5"]["trang_thai"], sk["g5"]["nguon_doc"]["loi"]), ("CHUA_DOI_CHIEU_DUOC", "PDF_KHAC_SHA_BAN_KY"))

    def test_pdf_scan_ocr_tat_chua(self):
        v = self.OBS.get("pdf_scan_xu_ly") or {}
        self.can_pdf(v)
        s = self.o("pdf_scan_xu_ly")
        self.assertEqual((s["kiem"], s["che_do"], s["g5"]["trang_thai"], s["g5"]["nguon_doc"]["kieu"]), ("OK", "RULE_ONLY", "CHUA_DOI_CHIEU_DUOC", None))
        self.assertEqual(s["bang"], [t["ma"] for t in TS_PDF])

    # -------------------------------------------------------------- máy chủ
    def test_dv_kiem_body(self):
        lg = self.o("dv_kiem_legacy")
        self.assertEqual((lg["mode"], lg["body_sha256"]), (None, lg["h"]))     # legacy 8 khóa không đổi
        self.assertEqual(self.OBS["dv_kiem_legacy_khoa_e5"]["ma"], "COMMON_TRUONG_LA")
        e5 = self.o("dv_kiem_e5")
        self.assertEqual((e5["mode"], e5["body_sha256"]), ("doi_chieu_ban_ky", e5["h"]))  # 13 khóa
        mong = {"thieu": "E5_TRUONG_THIEU", "la": "COMMON_TRUONG_LA", "all": "E5_THAM_SO_ALL", "pdf_ky": "E5_PDF_KY_SHA",
                "expected_sai": "E5_EXPECTED_SAI", "gia_tri_sai": "E5_GIA_TRI_SAI", "binding_catalog": "E5_BINDING_CATALOG",
                "sha_khac": "E5_SHA_KHAC", "ma_khac": "E5_MA_KHAC", "catalog_ngoai": "COMMON_CATALOG_SHA_KHAC", "loai_kcn": "COMMON_LOAI_KHONG_HO_TRO"}
        self.assertEqual({k: self.OBS["dv_am_" + k].get("ma") for k in mong}, mong)

    def test_dv_nang_luc_e5_trung_thuc(self):
        n = self.o("dv_nang_luc")
        g = self.OBS["dv_ghim"]
        e5 = n["e5"]
        self.assertEqual((n["contract"], n["modes"][0], e5["kieu"], e5["ocr"]), ("trich-tham-so-common/v1", "RULE_ONLY", "nang_luc_e5/v1",
                                                                                 "ABBYY_HOT_FOLDER_KHONG_THAM_DO"))
        bt = self.o("dm_bo_trich")["XD"]
        du = n["san_sang"] and bool(e5["doc_pdf"]) and not e5["implementation_thieu"] and g["catalog_sha_khop"] is True and \
            all(m in g["ghim"] for m in bt)
        self.assertEqual(e5["san_sang"], du)                                    # sẵn sàng tính từ catalog/bộ trích/thư viện thật
        self.assertEqual("doi_chieu_ban_ky" in n["modes"], e5["san_sang"])
        if not du:
            self.assertFalse(e5["loai"].get("XD", {}).get("bo_trich"))             # chưa đủ → không công bố bộ trích

    def can_pipe(self):
        g = self.OBS.get("dv_ghim") or {}
        if self.OBS.get("_import_dv"):
            imp = self.OBS["_import_dv"]
            if imp["loi"] == "ModuleNotFoundError" and (imp.get("ten") or "").split(".")[0] not in ("trich_xuat", "may_chu"):
                self.skipTest(f"NOT_VERIFIED: thiếu thư viện {imp.get('ten')}")
            self.fail(f"Import may_chu.dich_vu overlay lỗi: {imp}")
        if g.get("pipe") != [t["ma"] for t in TS_PDF]:
            self.skipTest(f"NOT_VERIFIED: catalog ghim thật chưa có mức tường minh/không dùng cho {[t['ma'] for t in TS_PDF]} "
                          f"(ghim={g.get('ghim')}, pipe={g.get('pipe')}) — không tự gán mức")
        k = self.OBS.get("dv_khop") or {}
        if "loi" not in k and k.get("ok", {}).get("common_tt") == "loi" and "ModuleNotFoundError" in str(k["ok"].get("thong_bao")):
            self.skipTest(f"NOT_VERIFIED: worker thiếu thư viện — {k['ok'].get('thong_bao')}")
        if not (self.o("dv_nang_luc")["e5"]["doc_pdf"]):
            self.skipTest("NOT_VERIFIED: máy engine không có pdfplumber/pypdf")

    def test_dv_vong_doi_khop_lech_scan(self):
        self.can_pipe()
        k = self.o("dv_khop")
        self.assertEqual((k["common_tt"], k["tt"], k["che_do"], k["g5"]["trang_thai"]), ("done", "xong", "RULE_ONLY", "KHOP"), k)
        self.assertEqual((k["seal"]["mode"], k["seal"]["g5_trang_thai"], k["seal"]["g5_coverage"]), ("doi_chieu_ban_ky", "KHOP", [t["ma"] for t in TS_PDF]))
        self.assertEqual(k["seal"]["kieu"], "seal_common/v1")
        vt = {x["ma"]: x["vi_tri_do_duoc"] for x in k["g5"]["khop"]}
        self.assertEqual([(p["trang"], p["dong"]) for p in vt["TT-02"]], [(2, DONG_TT02)])
        self.assertEqual((k["lap_lai"]["create"]["lap_lai"], k["lap_lai"]["create"]["luot"], k["lap_lai"]["start_lap_lai"]), (True, k["luot"], True))
        self.assertEqual(k["tai_bytes_khac"], "COMMON_SOURCE_SHA_KHAC")
        self.assertEqual(k["expected_doi_cung_rid"], "COMMON_XUNG_DOT")
        lt = self.o("dv_lech_tien")
        self.assertEqual((lt["common_tt"], lt["g5"]["trang_thai"], lt["seal"]["g5_trang_thai"]), ("done", "LECH", "LECH"), lt)
        self.assertEqual(lt["g5"]["lech"][0]["gia_tri_ban_ky"], {"so": "100000000", "tien_te": "VND"})
        self.assertEqual([(p["trang"], p["dong"]) for p in lt["g5"]["lech"][0]["vi_tri_do_duoc"]], [(2, DONG_TT02)])
        lb = self.o("dv_lech_bang")
        self.assertEqual((lb["common_tt"], lb["g5"]["trang_thai"], [x["ma"] for x in lb["g5"]["lech"]]), ("done", "LECH", ["TT-20"]), lb)
        sc = self.o("dv_scan")
        self.assertEqual((sc["common_tt"], sc["g5"]["trang_thai"], sc["g5"]["nguon_doc"]["kieu"]), ("done", "CHUA_DOI_CHIEU_DUOC", None), sc)
        self.assertEqual(sc["seal"]["g5_trang_thai"], "CHUA_DOI_CHIEU_DUOC")

    def test_dv_tu_choi_truoc_worker(self):
        self.can_pipe()
        self.assertEqual(self.OBS["dv_muc_khac"].get("ma"), "E5_MUC_KHAC_CATALOG")   # mức binding khác mức ghim → không chạy
        self.assertEqual(self.OBS["dv_docx_thay_pdf"].get("ma"), "COMMON_MOT_PDF")   # không DOCX/Word thay PDF ký
        self.assertEqual(self.OBS["dv_khong_phai_pdf"].get("ma"), "E5_KHONG_PHAI_PDF")

    def test_dv_sua_sau_niem_phong_unknown(self):
        self.can_pipe()
        for chon in ("raw", "expected", "catalog", "seal"):
            v = self.o("dv_sua_" + chon)
            self.assertEqual((v["truoc"], v["truoc_g5"]), ("done", "KHOP"), (chon, v))
            self.assertEqual(v["sau"], "unknown", (chon, v))                        # không công bố kết quả đã bị sửa
            self.assertIsNone(v["sau_seal"], chon)
            self.assertEqual(v["sau_tai"], {}, chon)
            self.assertNotEqual(v["sau_s_tt"], "xong", chon)


class E5BangThuTuFix01Tests(unittest.TestCase):
    """FIX01 (pure, CODE_ONLY/NOT_RUN): `_doc_ma_e5(BANG_DONG)` THẬT trên bản sao private37 + overlay, tiến trình con riêng (kế thừa env, không -I/-S/-E/-s).
    Bảng phải đọc từ dòng bản ký (thứ tự dòng/ô, dòng thừa), không dựng lại từ expected. Chạy cả hai probe read-only docs/E5-FIX01-READONLY (không sửa).
    Không phải PDF thật/producer. Thiếu env/baseline/thư viện → NOT_VERIFIED (skip KHÔNG phải PASS). Thư mục tạm giữ lại."""
    COT2 = [{"ten": "Dot", "kieu": "text"}, {"ten": "Thanh toan", "kieu": "tien"}]
    KV2 = {"cot": COT2, "dong": [["Dot A", {"so": "100", "tien_te": "VND"}], ["Dot B", {"so": "200", "tien_te": "VND"}]]}
    KV_TEXT = {"cot": [{"ten": "Dot", "kieu": "text"}, {"ten": "Nguoi nhan", "kieu": "text"}, {"ten": "Noi dung", "kieu": "text"}],
               "dong": [["Dot A", "ANPHA", "BETA"]]}
    KV_TRON = {"cot": [{"ten": "Dot", "kieu": "text"}, {"ten": "Noi dung", "kieu": "text"}, {"ten": "Thanh toan", "kieu": "tien"}],
               "dong": [["Dot A", "Tam ung", {"so": "100", "tien_te": "VND"}]]}
    CA = {"duong": ("KV2", ["Dot A 100 VND", "Dot B 200 VND"]),
          "dao_dong": ("KV2", ["Dot B 200 VND", "Dot A 100 VND"]),
          "dao_o_text": ("KV_TEXT", ["Dot A BETA ANPHA"]),
          "them_dong": ("KV2", ["Dot A 100 VND", "Dot B 200 VND", "Dot C 300 VND"]),
          "text_duong": ("KV_TEXT", ["Dot A ANPHA BETA"]),
          "text_tu_du": ("KV_TEXT", ["Dot A ANPHA BETA GAMMA"]),
          "typed_du": ("KV2", ["Dot A 100 VND 50 VND", "Dot B 200 VND"]),
          "vung_co_loi_van": ("KV2", ["Dieu 4. Thanh toan", "Dot A 100 VND", "Dot B 200 VND", "Dieu 5. Chung"]),
          "vung_dut": ("KV2", ["Dot A 100 VND", "Ghi chu giua bang", "Dot B 200 VND"]),
          "mat_dong": ("KV2", ["Dot B 200 VND"]),
          "tron_duong": ("KV_TRON", ["Dot A: Tam ung, 100 VND"])}
    CON = r'''
import json, sys, traceback, unittest
sys.dont_write_bytecode = True
CFG = json.loads(open(sys.argv[1], encoding="utf-8").read())
sys.path.insert(0, CFG["goc"])
OBS = {}
try:
    from trich_xuat import quy_trinh as Q
    for ten, (kv, lines) in CFG["ca"].items():
        try:
            OBS[ten] = {"ok": Q._doc_ma_e5("BANG_DONG", "bang", kv, None, lines, [Q.norm(x) for x in lines], {}, "DEMO_SCHEDULE")}
        except BaseException as e:  # noqa: BLE001
            OBS[ten] = {"loi": type(e).__name__, "vet": traceback.format_exc()[-2000:]}
    for ten, p in CFG["probe"].items():
        r = unittest.TextTestRunner(stream=open(p + ".out.txt", "w", encoding="utf-8"), verbosity=2).run(
            unittest.defaultTestLoader.discover(CFG["probe_dir"], pattern=ten))
        OBS["probe_" + ten] = {"so": r.testsRun, "fail": len(r.failures), "error": len(r.errors), "skip": len(r.skipped)}
except BaseException as e:  # noqa: BLE001
    OBS["_import"] = {"loi": type(e).__name__, "ten": getattr(e, "name", None), "vet": traceback.format_exc()[-2000:]}
open(CFG["ra"], "w", encoding="utf-8").write(json.dumps(OBS, ensure_ascii=False, indent=1, default=str))
'''

    @classmethod
    def setUpClass(cls):
        p37 = os.environ.get(ENV_P37)
        if not p37:
            raise unittest.SkipTest(f"NOT_VERIFIED: chưa đặt {ENV_P37} — skip KHÔNG phải PASS")
        p37 = Path(p37)
        for rel in ARTEFACT:
            a, b = p37 / rel, BASELINE / rel
            if not a.is_file() or not b.is_file() or a.read_bytes() != b.read_bytes():
                raise unittest.SkipTest(f"NOT_VERIFIED: private37 {rel} khác baseline docs/E5-SOURCE6-READONLY")
        tam = Path(tempfile.mkdtemp(prefix="ktt_s6e5_fix01_"))  # GIỮ LẠI
        goc = tam / "nguon"

        def bo_qua(thu_muc, ten):
            rel = os.path.relpath(thu_muc, p37).replace("\\", "/")
            out = {t for t in ten if t in ("__pycache__", ".git") or t.endswith((".pyc", ".pyo"))}
            if rel == ".":
                out |= {t for t in ten if t in ("ket_qua_AI", "co_so_du_lieu", "ocr", "cau_hinh_may_ai.json", "khoa_api.json")}
            return out | {t for t in ten if (t if rel == "." else f"{rel}/{t}") in ARTEFACT}
        shutil.copytree(p37, goc, ignore=bo_qua)
        for rel in ARTEFACT:
            (goc / rel).write_bytes((OVERLAY / rel).read_bytes())
        probe_dir = tam / "probe"
        probe_dir.mkdir()
        probe = {}
        for ten in ("probe_e5_ordered_table03.py", "probe_e5_table_positive01.py"):
            (probe_dir / ten).write_bytes((ROOT / "docs" / "E5-FIX01-READONLY" / ten).read_bytes())  # bản sao nguyên byte, không sửa
            probe[ten] = str(probe_dir / ten)
        ca = {k: (copy.deepcopy(getattr(cls, kv)), lines) for k, (kv, lines) in cls.CA.items()}
        cfg = {"goc": str(goc), "ra": str(tam / "quan_sat.json"), "ca": ca, "probe": probe, "probe_dir": str(probe_dir)}
        (tam / "dau_vao.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        (tam / "con_fix01.py").write_text(cls.CON, encoding="utf-8")
        env = dict(os.environ)
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", HD_DU_LIEU=str(tam / "du_lieu"), HD_OUT_DIR=str(tam / "du_lieu" / "trich_xuat"),
                   HD_CSDL=str(tam / "csdl" / "hop_dong.db"), HD_THU_MUC_KHOA=str(tam / "khoa"))
        kq = subprocess.run([sys.executable, str(tam / "con_fix01.py"), str(tam / "dau_vao.json")], cwd=str(goc), env=env, capture_output=True,
                            timeout=600)
        (tam / "con_stdout.txt").write_bytes(kq.stdout)
        (tam / "con_stderr.txt").write_bytes(kq.stderr)
        cls.TAM = tam
        if not (tam / "quan_sat.json").is_file():
            raise AssertionError(f"Tiến trình con không ghi quan sát (mã {kq.returncode}); xem {tam}")
        cls.OBS = json.loads((tam / "quan_sat.json").read_text(encoding="utf-8"))
        imp = cls.OBS.get("_import")
        if imp and imp["loi"] == "ModuleNotFoundError" and (imp.get("ten") or "").split(".")[0] not in ("trich_xuat", "may_chu"):
            raise unittest.SkipTest(f"NOT_VERIFIED: thiếu thư viện {imp.get('ten')} — {tam}")
        if imp:
            raise AssertionError(f"Import overlay lỗi: {imp}")

    def kq(self, ten):
        v = self.OBS.get(ten)
        self.assertIsNotNone(v, f"thiếu quan sát {ten} ({self.TAM})")
        self.assertNotIn("loi", v, f"{ten}: {v}")
        return v["ok"]

    def doc(self, ten, dong, ix):
        r = self.kq(ten)
        self.assertEqual(r[0], "doc", (ten, r))
        self.assertEqual(r[1]["dong"], dong, ten)
        self.assertEqual(r[2], ix, ten)
        return r

    def chua(self, ten, ly_do, phan):
        r = self.kq(ten)
        self.assertEqual(r[:2], ["thieu", ly_do], (ten, r))
        for x in phan:
            self.assertIn(x, r[2], ten)
        return r

    def test_probe_doc_lap(self):
        for ten, so in (("probe_e5_ordered_table03.py", 3), ("probe_e5_table_positive01.py", 1)):
            self.assertEqual(self.OBS.get("probe_" + ten), {"so": so, "fail": 0, "error": 0, "skip": 0}, ten)

    def test_duong_tinh_giu_nguyen(self):
        self.assertEqual(self.doc("duong", self.KV2["dong"], [0, 1])[1], self.KV2)
        self.doc("vung_co_loi_van", self.KV2["dong"], [1, 2])               # lời văn ngoài vùng bảng không thành dòng
        self.doc("text_duong", [["Dot A", "ANPHA", "BETA"]], [0])
        self.doc("tron_duong", [["Dot A", "Tam ung", {"so": "100", "tien_te": "VND"}]], [0])

    def test_ba_ca_tai_hien_doc_dung_ban_ky(self):
        b, a = self.KV2["dong"][1], self.KV2["dong"][0]
        self.doc("dao_dong", [b, a], [0, 1])                                 # thứ tự dòng bản ký
        self.doc("dao_o_text", [["Dot A", "BETA", "ANPHA"]], [0])            # thứ tự ô bản ký
        self.doc("them_dong", [a, b, ["Dot C", {"so": "300", "tien_te": "VND"}]], [0, 1, 2])  # dòng thừa trong vùng giữ lại

    def test_khong_xac_dinh_thi_chua(self):
        r = self.chua("text_tu_du", "BANG_CHUA_DU", [{"dong": "Dot A", "ly_do": "O_KHONG_XAC_DINH", "dong_so": 1}])  # từ dư → không đoán ranh giới
        self.assertNotIn({"dong": "Dot A", "ly_do": "KHONG_THAY_DONG"}, r[2])   # dòng đã thấy, chỉ ô không xác định
        self.chua("typed_du", "BANG_CHUA_DU", [{"dong": "Dot A", "ly_do": "O_KHONG_XAC_DINH", "dong_so": 1}])
        self.chua("vung_dut", "NHIEU_VUNG_BANG", [{"dong_so": [1, 3]}])
        r = self.chua("mat_dong", "BANG_CHUA_DU", [{"dong": "Dot A", "ly_do": "KHONG_THAY_DONG"}])
        self.assertNotIn("Dot B", [x.get("dong") for x in r[2] if x.get("ly_do")])  # dòng đọc được và khớp không bị báo thiếu


if __name__ == "__main__":
    unittest.main()
