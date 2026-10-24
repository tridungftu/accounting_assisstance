# -*- coding: utf-8 -*-
"""Source #6 lazy Excel - kiểm candidate tools/source6_lazy_excel/master_hd.py (bản vá thay thế master_hd.py nguồn).

Ba nhóm kiểm (theo docs/GIAO-CODE-SOURCE6-LAZY-EXCEL.md):
1. Tĩnh (AST/văn bản): candidate = nguồn pinned + đúng các hunk trong allowlist; không còn Excel ở lúc nạp module,
   kể cả giá trị mặc định / decorator / chuỗi gọi hàm lúc nạp.
2. Subprocess mới (-B -X utf8, kế thừa môi trường khởi động của Root) có bộ chặn import chỉ dùng trong test: trước hết
   chứng minh guard chống xóa nạp lúc khởi động; rồi nạp candidate + trich_xuat(..., llm=None) không được thử import
   numpy/openpyxl; kết quả so với golden viết tay.
Bố cục: chỉ chạy trong bố cục đóng băng của Root (F/files + F/input-extra); thiếu/sai baseline hoặc guard -> SETUP
NOT_VERIFIED, không lùi về nguồn khác.
3. Excel thật (không chặn): openpyxl đã cài, file tổng hợp; so candidate với nguồn pinned và kiểm ngữ nghĩa
   style/công thức/validation/round-trip. Không có mô phỏng openpyxl; thiếu Excel thì test lỗi (Root ghi NOT_VERIFIED).
"""
from __future__ import annotations

import ast
import contextlib
import difflib
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "tools" / "source6_lazy_excel" / "master_hd.py"
# Bố cục chạy đóng băng của Root: F/files/{tests,tools}; baseline đã duyệt ở F/input-extra/docs/CRM-41-01-SOURCE-PATCH.
# Chỉ dùng đúng quan hệ cố định này từ vị trí file test; không tìm nơi khác, không lùi về dự án/S37/snapshot khác.
ORIGINAL = ROOT.parent / "input-extra" / "docs" / "CRM-41-01-SOURCE-PATCH" / "master_hd.py"
ORIGINAL_SHA256 = "2a63289f5daa73a2500fff59c547395a56d823da7f0fdadd02ecfe8506429648"
ORIGINAL_BYTES = 71366
GUARD_MODULE = "codex_no_delete_guard"


def _kiem_baseline():
    """Kiểm bố cục + baseline pinned TRƯỚC mọi import Excel; sai/thiếu -> lỗi SETUP NOT_VERIFIED (không phải lỗi candidate)."""
    loi = []
    if ROOT.name != "files":
        loi.append(f"thư mục chứa tests/tools phải là 'files' của bố cục đóng băng, đang là {ROOT}")
    b = None
    if not ORIGINAL.is_file():
        loi.append(f"thiếu baseline {ORIGINAL}")
    else:
        b = ORIGINAL.read_bytes()
        if len(b) != ORIGINAL_BYTES:
            loi.append(f"baseline {len(b)} B, cần {ORIGINAL_BYTES} B")
        if hashlib.sha256(b).hexdigest() != ORIGINAL_SHA256:
            loi.append(f"baseline SHA256 {hashlib.sha256(b).hexdigest()}, cần {ORIGINAL_SHA256}")
    if loi:
        raise RuntimeError("SETUP NOT_VERIFIED (baseline/bố cục): " + "; ".join(loi))
    return b


# Bằng chứng guard chống xóa đã nạp lúc khởi động. Dùng chung (cùng mã) cho tiến trình test và child; chỉ đọc
# sys.modules, không import/chạy guard, không thay hook. Giữ ASCII vì được ghép vào script child đọc từ stdin.
_GUARD_PROOF_SRC = r'''
def _bang_chung_guard():
    import hashlib, os, shutil, sys
    GUARD_SHA256 = "a517c5359ceada062900edd34280d4dc7daa2a001d5e05c84a9eae174813a229"
    ev = {"module": False, "file": None, "sha256": None, "unlink": False, "remove": False, "rmtree": False,
          "env_CODEX_NO_DELETE_FILES": os.environ.get("CODEX_NO_DELETE_FILES"),
          "dont_write_bytecode": sys.dont_write_bytecode}
    loi = []
    g = sys.modules.get("codex_no_delete_guard")
    if g is None:
        loi.append("codex_no_delete_guard not loaded at startup")
    else:
        ev["module"] = True
        ev["file"] = getattr(g, "__file__", None)
        if ev["file"]:
            with open(ev["file"], "rb") as fh:
                ev["sha256"] = hashlib.sha256(fh.read()).hexdigest()
        if ev["sha256"] != GUARD_SHA256:
            loi.append("guard file sha256 %r != %s" % (ev["sha256"], GUARD_SHA256))
        rf, rt = getattr(g, "_retain_file", None), getattr(g, "_retain_tree", None)
        ev["unlink"] = rf is not None and os.unlink is rf
        ev["remove"] = rf is not None and os.remove is rf
        ev["rmtree"] = rt is not None and shutil.rmtree is rt
        for k, ten in (("unlink", "os.unlink is guard._retain_file"), ("remove", "os.remove is guard._retain_file"),
                       ("rmtree", "shutil.rmtree is guard._retain_tree")):
            if not ev[k]:
                loi.append(ten + " is False")
    if ev["env_CODEX_NO_DELETE_FILES"] != "1":
        loi.append("CODEX_NO_DELETE_FILES=%r != '1'" % (ev["env_CODEX_NO_DELETE_FILES"],))
    if sys.dont_write_bytecode is not True:
        loi.append("sys.dont_write_bytecode is not True")
    ev["loi"] = loi
    ev["ok"] = not loi
    return ev
'''
_ns_guard = {}
exec(_GUARD_PROOF_SRC, _ns_guard)
_bang_chung_guard = _ns_guard["_bang_chung_guard"]


def _kiem_guard_cha():
    """Guard gốc phải có trong tiến trình test trước khi spawn child / tạo-dọn thư mục tạm; không có -> fail đóng."""
    try:
        ev = _bang_chung_guard()
    except Exception as e:
        raise RuntimeError(f"SETUP NOT_VERIFIED (guard tiến trình test): không lập được bằng chứng: {e!r}") from e
    if not ev["ok"]:
        raise RuntimeError("SETUP NOT_VERIFIED (guard tiến trình test): " + json.dumps(ev, ensure_ascii=False))
    return ev

EXCEL_NAMES = frozenset({"openpyxl", "Alignment", "Border", "Font", "PatternFill", "Side", "get_column_letter",
                         "DataValidation", "THIN", "HF", "HFONT", "BASE", "BOLD", "BLUE", "YELLOW", "RED", "GREEN"})
STYLE_NAMES = ("THIN", "HF", "HFONT", "BASE", "BOLD", "BLUE", "YELLOW", "RED", "GREEN")
# hàm công khai/CLI dùng Excel; mỗi hàm phải gọi _excel() trước khi dùng tên Excel
EXCEL_ENTRIES = frozenset({"ghi_so_sanh", "put", "header", "ghi_master", "doc_master", "nap_dot", "doi_chieu", "main"})
# phần quy tắc / RULE_ONLY: phải giống nguồn pinned từng ký tự
RULE_NAMES = ("nfc", "bo_dau", "TU_TIEU_DE", "bo_dau_tieu_de", "so", "num", "doc_to_docx", "doc_hop_dong", "_pct", "_txt",
              "_money", "RULES", "_collect_list", "trich_xuat", "AI_SYSTEM", "AI_FORMAT", "AI_KEEP", "rut_gon", "an_danh",
              "SO_CHU", "kiem_tra_nhat_quan", "_CH", "CAU_HINH_AI", "MAC_DINH_AI", "cau_hinh_ai", "LocalLLM", "_chuan",
              "so_sanh_ai", "doc_dap_an", "_so_trong", "cham_diem", "_hdr_text", "tim_bang_chi_tiet", "MAU_MA_RIENG",
              "la_dong_mo_ta", "khoa", "LABELS", "tim_so_tong_hop", "NUMF", "QF", "_doan_so_dot")

# ---------------------------------------------------------------- allowlist: các hunk duy nhất được phép đổi
_STYLE_OLD = '''THIN = Side(style="thin", color="BFC5C2")
HF = PatternFill("solid", fgColor="1F4A7A")
HFONT = Font(name="Arial", bold=True, color="FFFFFF", size=10)
BASE = Font(name="Arial", size=10)
BOLD = Font(name="Arial", size=10, bold=True)
BLUE = Font(name="Arial", size=10, color="0000FF")
YELLOW = PatternFill("solid", fgColor="FFF2CC")
RED = PatternFill("solid", fgColor="F8D7D3")
GREEN = PatternFill("solid", fgColor="DDEFE3")
NUMF = '#,##0;(#,##0);"-"'
QF = '#,##0.000;(#,##0.000);"-"'


def put(ws, r, c, v, font=BASE, fmt=None, fill=None, wrap=False, text=False):
    """Ghi ô. Chuỗi bắt đầu bằng '=' là công thức, trừ khi text=True (nội dung trích từ tài liệu)."""
'''

_STYLE_NEW = '''_EXCEL_SAN_SANG = False
# tên Excel trước đây tạo khi nạp module; nay tạo trong _excel() ở lần dùng Excel đầu tiên
_TEN_EXCEL = ("openpyxl", "Alignment", "Border", "Font", "PatternFill", "Side", "get_column_letter", "DataValidation",
              "THIN", "HF", "HFONT", "BASE", "BOLD", "BLUE", "YELLOW", "RED", "GREEN")


def _excel():
    """Nạp openpyxl (thư viện thật đã cài) và tạo các kiểu ô dùng chung, một lần, khi thật sự đọc/ghi Excel."""
    global _EXCEL_SAN_SANG, openpyxl, Alignment, Border, Font, PatternFill, Side, get_column_letter, DataValidation
    global THIN, HF, HFONT, BASE, BOLD, BLUE, YELLOW, RED, GREEN
    if _EXCEL_SAN_SANG:
        return
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    THIN = Side(style="thin", color="BFC5C2")
    HF = PatternFill("solid", fgColor="1F4A7A")
    HFONT = Font(name="Arial", bold=True, color="FFFFFF", size=10)
    BASE = Font(name="Arial", size=10)
    BOLD = Font(name="Arial", size=10, bold=True)
    BLUE = Font(name="Arial", size=10, color="0000FF")
    YELLOW = PatternFill("solid", fgColor="FFF2CC")
    RED = PatternFill("solid", fgColor="F8D7D3")
    GREEN = PatternFill("solid", fgColor="DDEFE3")
    _EXCEL_SAN_SANG = True


def __getattr__(name):
    """Giữ `master_hd.BASE`, `from master_hd import Font, openpyxl`... cho mã gọi từ ngoài: nạp Excel khi được hỏi tới."""
    if name in _TEN_EXCEL:
        _excel()
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


NUMF = '#,##0;(#,##0);"-"'
QF = '#,##0.000;(#,##0.000);"-"'
_BASE_MAC_DINH = object()  # put(..., font không truyền) = BASE; BASE chỉ có sau _excel() nên không làm giá trị mặc định


def put(ws, r, c, v, font=_BASE_MAC_DINH, fmt=None, fill=None, wrap=False, text=False):
    """Ghi ô. Chuỗi bắt đầu bằng '=' là công thức, trừ khi text=True (nội dung trích từ tài liệu)."""
    _excel()
    if font is _BASE_MAC_DINH:
        font = BASE
'''


def _them_excel(def_line):
    return (def_line, def_line + "    _excel()\n")


HUNKS = (
    ("import openpyxl\n"
     "from openpyxl.styles import Alignment, Border, Font, PatternFill, Side\n"
     "from openpyxl.utils import get_column_letter\n"
     "from openpyxl.worksheet.datavalidation import DataValidation\n",
     "# openpyxl (kéo theo numpy) chỉ nạp khi thật sự đọc/ghi Excel - xem _excel() ở phần \"ghi master\".\n"
     "# Trích tham số bằng quy tắc (trich_xuat, llm=None) không dùng Excel nên không chịu thời gian khởi tạo các thư viện này.\n"),
    _them_excel("def ghi_so_sanh(out, hop_dong, cmp, stats, model, n_chars, an):\n"),
    (_STYLE_OLD, _STYLE_NEW),
    _them_excel("def header(ws, row, names, widths):\n"),
    _them_excel("def ghi_master(out, contract_file, rows, boq=None, boq_src=\"\"):\n"),
    _them_excel("def doc_master(path):\n"),
    _them_excel("def nap_dot(master_path, file_dot, so_dot=None):\n"),
    _them_excel("def doi_chieu(master_path, file_moi, out):\n"),
    ("    args = ap.parse_args()\n", "    args = ap.parse_args()\n    _excel()  # mọi lệnh CLI đều đọc/ghi Excel\n"),
)

# ---------------------------------------------------------------- dữ liệu tổng hợp (không DOCX, không dữ liệu thật)
P3 = "Hôm nay, ngày 5 tháng 3 năm 2026 tại văn phòng công ty"
P4 = "Gói thầu: Thi công nhà kho mẫu."
P5 = "Bên giao thầu (Bên A): Công ty Mẫu Thử A"
P6 = "Bên nhận thầu (Bên C): Công ty Mẫu Thử B"
P7 = "Giá trị hợp đồng là 1.234.567.890 VNĐ"
P8 = "Giá trên đã bao gồm thuế GTGT 10%"
P9 = "Tạm ứng: Không áp dụng"
P10 = "Bên A thanh toán cho bên B 95% giá trị khối lượng nghiệm thu"
P11 = "Thời gian thanh toán: Tối đa 30 ngày"
P15 = "+ Số lượng hồ sơ: 03 bộ"
P16 = "Thời hạn bảo hành là 12 tháng"
D3, D4, D9 = "Điều 3. Giá hợp đồng", "Điều 4. Thanh toán", "Điều 9. Bảo hành"

CASE_TC01 = [
    ("", "HỢP ĐỒNG THI CÔNG XÂY DỰNG"),
    ("", "Số: 0001/2026"),
    ("", "Căn cứ Bộ luật Dân sự năm 2015"),
    ("", P3), ("", P4), ("", P5), ("", P6),
    (D3, P7), (D3, P8),
    (D4, P9), (D4, P10), (D4, P11),
    (D4, "Hồ sơ thanh toán gồm:"),
    (D4, "+ Biên bản nghiệm thu khối lượng;"),
    (D4, "+ Hóa đơn GTGT."),
    (D4, P15),
    (D9, P16),
    (D9, "Thông báo trong 03 (bốn) ngày"),
]

Q2 = "Bên giao thầu (Bên A): Công ty Alpha"
Q4 = "Tạm ứng hợp đồng: 15,5 %"
Q5 = "Mỗi đợt giữ lại 5% giá trị"
D5 = "Điều 5. Thanh toán"
CASE_NHAT_QUAN = [
    ("", "Số : HD-07/2025."),
    ("", "Căn cứ nhu cầu hai bên"),
    ("", Q2),
    ("Điều 1. Định nghĩa", "“Bên giao thầu” (viết tắt là Bên A) là Công ty Beta như nêu trên"),
    (D5, Q4),
    (D5, Q5),
    ("Điều 7. Phạt", "Biên bản vi phạm có xác nhận của Bên B"),
    ("Điều 7. Phạt", "Trường hợp khẩn cấp không cần xác nhận của Bên B"),
]

CASES = {"tc01": CASE_TC01, "nhat_quan": CASE_NHAT_QUAN, "rong": []}

MA_THU_TU = ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07", "TC-08",
             "TT-01", "TT-02", "TT-03", "TT-04", "TT-05", "TT-10", "TT-11", "TT-12", "TT-20", "TT-21", "TT-22",
             "TT-30", "TT-31", "TT-32", "TT-33", "TT-40", "TT-41", "TT-42",
             "TT-50", "TT-51", "TT-52", "TT-53", "TT-54", "TT-55", "TT-56", "TT-62", "TT-60", "TT-61"]
KEYS = ["ma", "nhom", "ten", "gia_tri", "don_vi", "cach", "dieu", "trich", "ghi_chu"]
TD, KTT = "Tự động", "Không tìm thấy"
# (gia_tri, cach, dieu, trich, ghi_chu) cho mã có kết quả; mã khác: (None, KTT, "", "", "")
GOLDEN = {
    "tc01": {
        "TC-01": ("0001/2026", TD, "", "Số: 0001/2026", ""),
        "TC-02": ("05/03/2026", TD, "", P3, ""),
        "TC-03": ("Thi công nhà kho mẫu", TD, "", P4, ""),
        "TC-06": ("Công ty Mẫu Thử A", TD, "", P5, ""),
        "TC-07": ("Công ty Mẫu Thử B", TD, "", P6, "Hợp đồng ghi '(BÊN C)' - sai ký hiệu bên, cần lưu ý"),
        "TC-08": (None, KTT, "", "", "Số và chữ không khớp tại Điều 9: '03 (bốn)'"),
        "TT-02": (1234567890.0, TD, D3, P7, ""),
        "TT-03": ("Có", TD, D3, P8, ""),
        "TT-04": (0.1, TD, D3, P8, ""),
        "TT-10": ("Không áp dụng", TD, D4, P9, ""),
        "TT-11": ("Không áp dụng", "Suy ra từ TT-10", "", "", ""),
        "TT-20": (0.95, TD, D4, P10, ""),
        "TT-21": (0.05, "Suy ra = 100% - TT-20", D4, P10, ""),
        "TT-22": (30, TD, D4, P11, ""),
        "TT-32": (12, TD, D9, P16, ""),
        "TT-62": (3, TD, D4, P15, ""),
        "TT-60": ("Biên bản nghiệm thu khối lượng; Hóa đơn GTGT", TD, D4, "Hồ sơ thanh toán gồm:", ""),
    },
    "nhat_quan": {
        "TC-01": ("HD-07/2025", TD, "", "Số : HD-07/2025.", ""),
        "TC-06": ("Công ty Alpha", TD, "", Q2,
                  "MÂU THUẪN: Điều 1 định nghĩa Bên giao thầu là 'Công ty Beta', khác phần các bên ('Công ty Alpha')"),
        "TT-10": (0.155, TD, D5, Q4, ""),
        "TT-21": (0.05, TD, D5, Q5, ""),
        "TT-56": (None, KTT, "", "", "MÂU THUẪN: một chỗ yêu cầu biên bản vi phạm có xác nhận của Bên B, "
                                     "chỗ khác ghi không cần xác nhận của Bên B"),
    },
    "rong": {},
}
GOLDEN_ITEMS = {"tc01": {"TT-60": ["Biên bản nghiệm thu khối lượng", "Hóa đơn GTGT"], "TT-61": []},
                "nhat_quan": {"TT-60": [], "TT-61": []}, "rong": {"TT-60": [], "TT-61": []}}


def _doc(path):
    return path.read_bytes().decode("utf-8")


def _nap(path, ten):
    spec = importlib.util.spec_from_file_location(ten, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ten] = mod
    spec.loader.exec_module(mod)
    return mod


def _ham(tree):
    return {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def _la_main_guard(n):
    return (isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and isinstance(n.test.left, ast.Name)
            and n.test.left.id == "__name__")


def _nut_luc_nap(tree):
    """Mọi nút được Python tính khi nạp module: thân module, default/annotation/decorator của hàm, thân class.
    Không tính thân hàm (chỉ chạy khi gọi) và khối `if __name__ == "__main__"`."""
    stack = list(tree.body)
    while stack:
        n = stack.pop()
        if _la_main_guard(n):
            continue
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = n.args
            stack.extend(a.defaults)
            stack.extend(d for d in a.kw_defaults if d is not None)
            if not isinstance(n, ast.Lambda):
                stack.extend(n.decorator_list)
                if n.returns is not None:
                    stack.append(n.returns)
                for arg in a.posonlyargs + a.args + a.kwonlyargs + [x for x in (a.vararg, a.kwarg) if x]:
                    if arg.annotation is not None:
                        stack.append(arg.annotation)
            continue
        if isinstance(n, ast.ClassDef):
            stack.extend(n.decorator_list + n.bases + [k.value for k in n.keywords] + n.body)
            continue
        yield n
        stack.extend(ast.iter_child_nodes(n))


def _vi_pham_luc_nap(tree):
    """Các cạnh Excel lúc nạp: import openpyxl/numpy, tên Excel được đọc/gán, và hàm cục bộ (gọi lúc nạp, bắc cầu)
    có dùng tên Excel hoặc gọi _excel."""
    loi = []
    funcs = _ham(tree)
    goi = set()
    for n in _nut_luc_nap(tree):
        if isinstance(n, ast.Import):
            loi += [f"import {a.name} (dòng {n.lineno})" for a in n.names if a.name.split(".")[0] in ("openpyxl", "numpy")]
        elif isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] in ("openpyxl", "numpy"):
            loi.append(f"from {n.module} import ... (dòng {n.lineno})")
        elif isinstance(n, ast.Name) and n.id in EXCEL_NAMES:
            loi.append(f"tên {n.id} lúc nạp (dòng {n.lineno})")
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in funcs:
            goi.add(n.func.id)
    da, cho = set(), list(goi)
    while cho:
        f = cho.pop()
        if f in da:
            continue
        da.add(f)
        for n in ast.walk(funcs[f]):
            if isinstance(n, ast.Name) and n.id in funcs and n.id not in da:
                cho.append(n.id)
    for f in sorted(da):
        if f == "_excel":
            loi.append("_excel được gọi lúc nạp (bắc cầu)")
        dung = sorted({n.id for n in ast.walk(funcs[f]) if isinstance(n, ast.Name) and n.id in EXCEL_NAMES})
        if dung:
            loi.append(f"hàm {f} chạy lúc nạp dùng {dung}")
    return loi


def _la_goi_excel(stmt):
    return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name)
            and stmt.value.func.id == "_excel" and not stmt.value.args and not stmt.value.keywords)


def _bo_docstring(body):
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        return body[1:]
    return body


def _ten_toplevel(tree):
    out = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out[n.name] = n
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = n
    return out


# ================================================================ 1. tĩnh
class TestStaticCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_bytes = _kiem_baseline()
        cls.orig = cls.orig_bytes.decode("utf-8")
        cls.cand = _doc(CANDIDATE)
        cls.t_orig = ast.parse(cls.orig)
        cls.t_cand = ast.parse(cls.cand)

    def test_nguon_pinned_dung_hash(self):
        self.assertEqual(len(self.orig_bytes), ORIGINAL_BYTES)
        self.assertEqual(hashlib.sha256(self.orig_bytes).hexdigest(), ORIGINAL_SHA256)

    def test_candidate_chi_khac_dung_allowlist(self):
        expected = self.orig
        for old, new in HUNKS:
            self.assertEqual(expected.count(old), 1, f"hunk không duy nhất/không có trong nguồn: {old[:70]!r}")
            expected = expected.replace(old, new, 1)
        if self.cand != expected:
            diff = list(difflib.unified_diff(expected.splitlines(), self.cand.splitlines(),
                                             "expected(nguồn+allowlist)", "candidate", lineterm="", n=1))
            self.fail("candidate khác nguồn ngoài allowlist:\n" + "\n".join(diff[:120]))
        self.assertNotIn("\r", self.cand)

    def test_phan_quy_tac_giu_nguyen_tung_ky_tu(self):
        a, b = _ten_toplevel(self.t_orig), _ten_toplevel(self.t_cand)
        for ten in RULE_NAMES:
            self.assertIn(ten, a, ten)
            self.assertIn(ten, b, ten)
            self.assertEqual(ast.get_source_segment(self.cand, b[ten]), ast.get_source_segment(self.orig, a[ten]), ten)
        # tập tên cấp module: chỉ bỏ style (chuyển vào _excel) và chỉ thêm phần lazy
        them = set(b) - set(a)
        bot = set(a) - set(b)
        self.assertEqual(them, {"_EXCEL_SAN_SANG", "_TEN_EXCEL", "_excel", "__getattr__", "_BASE_MAC_DINH"})
        self.assertEqual(bot, set(STYLE_NAMES))

    def test_khong_excel_luc_nap_ke_ca_default_va_bac_cau(self):
        self.assertEqual(_vi_pham_luc_nap(self.t_cand), [])

    def test_bo_kiem_bat_duoc_nguon_goc_eager(self):
        # đối chứng: cùng bộ kiểm phải bắt được import dòng 37-40, style 827-835 và default font=BASE của nguồn gốc
        loi = _vi_pham_luc_nap(self.t_orig)
        txt = "\n".join(loi)
        for mau in ("import openpyxl (dòng 37)", "from openpyxl.styles", "from openpyxl.utils",
                    "from openpyxl.worksheet.datavalidation", "tên Side lúc nạp (dòng 827)", "tên BASE lúc nạp (dòng 840)"):
            self.assertIn(mau, txt)

    def test_moi_ham_excel_goi_excel_truoc(self):
        funcs = _ham(self.t_cand)
        dung_excel = set()
        for ten, fn in funcs.items():
            if ten in ("_excel", "__getattr__") or isinstance(fn, ast.ClassDef):
                continue
            dung = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and n.id in EXCEL_NAMES}
            if not dung:
                continue
            dung_excel.add(ten)
            body = _bo_docstring(fn.body)
            if ten == "main":
                i = next((k for k, s in enumerate(body) if _la_goi_excel(s)), None)
                self.assertIsNotNone(i, "main thiếu _excel()")
                truoc = {n.id for s in body[:i] for n in ast.walk(s) if isinstance(n, ast.Name) and n.id in EXCEL_NAMES}
                self.assertEqual(truoc, set(), "main dùng tên Excel trước _excel()")
                self.assertTrue(all(not isinstance(s, ast.If) for s in body[:i]), "_excel() phải trước mọi nhánh lệnh")
            else:
                self.assertTrue(_la_goi_excel(body[0]), f"{ten}: lệnh đầu tiên phải là _excel()")
        self.assertEqual(dung_excel, EXCEL_ENTRIES)
        for ten in ("tim_bang_chi_tiet", "tim_so_tong_hop", "trich_xuat", "kiem_tra_nhat_quan"):
            self.assertNotIn(ten, dung_excel)

    def test_excel_tao_dung_style_cua_nguon(self):
        orig_vals = {t.id: ast.dump(n.value) for n in self.t_orig.body if isinstance(n, ast.Assign)
                     for t in n.targets if isinstance(t, ast.Name) and t.id in STYLE_NAMES}
        fn = _ham(self.t_cand)["_excel"]
        cand_vals = {t.id: ast.dump(n.value) for n in ast.walk(fn) if isinstance(n, ast.Assign)
                     for t in n.targets if isinstance(t, ast.Name) and t.id in STYLE_NAMES}
        self.assertEqual(cand_vals, orig_vals)
        globs = {x for n in fn.body if isinstance(n, ast.Global) for x in n.names}
        self.assertTrue(EXCEL_NAMES <= globs)
        imps = sorted((n.module or "", tuple(a.name for a in n.names)) if isinstance(n, ast.ImportFrom)
                      else ("", tuple(a.name for a in n.names)) for n in fn.body if isinstance(n, (ast.Import, ast.ImportFrom)))
        self.assertEqual(imps, sorted([("", ("openpyxl",)),
                                       ("openpyxl.styles", ("Alignment", "Border", "Font", "PatternFill", "Side")),
                                       ("openpyxl.utils", ("get_column_letter",)),
                                       ("openpyxl.worksheet.datavalidation", ("DataValidation",))]))
        # cờ sẵn sàng chỉ bật sau khi import + tạo style xong (lỗi import không bị nuốt)
        self.assertFalse(any(isinstance(n, ast.Try) for n in ast.walk(fn)))
        last = fn.body[-1]
        self.assertIsInstance(last, ast.Assign)
        self.assertEqual(last.targets[0].id, "_EXCEL_SAN_SANG")

    def test_put_default_sentinel_va_getattr(self):
        tree = self.t_cand
        put = _ham(tree)["put"]
        names = [a.arg for a in put.args.args]
        self.assertEqual(names, ["ws", "r", "c", "v", "font", "fmt", "fill", "wrap", "text"])
        d = put.args.defaults
        self.assertEqual(len(d), 5)
        self.assertIsInstance(d[0], ast.Name)
        self.assertEqual(d[0].id, "_BASE_MAC_DINH")
        self.assertEqual([ast.literal_eval(x) for x in d[1:]], [None, None, False, False])
        body = _bo_docstring(put.body)
        self.assertTrue(_la_goi_excel(body[0]))
        self.assertEqual(ast.unparse(body[1]), "if font is _BASE_MAC_DINH:\n    font = BASE")
        sent = [n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_BASE_MAC_DINH" for t in n.targets)]
        self.assertEqual(len(sent), 1)
        self.assertEqual(ast.unparse(sent[0].value), "object()")
        ten = [n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_TEN_EXCEL" for t in n.targets)]
        self.assertEqual(set(ast.literal_eval(ten[0].value)), set(EXCEL_NAMES))


# ================================================================ 2. subprocess có bộ chặn numpy/openpyxl
_SCRIPT_CHAN = _GUARD_PROOF_SRC + r'''
import builtins, importlib.abc, importlib.util, json, sys
CHAN = ("numpy", "openpyxl")
truoc = sorted(m for m in sys.modules if m.split(".")[0] in CHAN)
log = []

# startup-loaded guard must be proven BEFORE touching the candidate; otherwise record evidence and exit 3
try:
    guard = _bang_chung_guard()
except Exception as e:
    guard = {"ok": False, "loi": ["guard proof raised %r" % (e,)]}
if not guard.get("ok"):
    sys.stdout.write(json.dumps({"truoc": truoc, "guard": guard,
                                 "setup_error": "SETUP NOT_VERIFIED: startup no-delete guard"}, ensure_ascii=True))
    sys.stdout.flush()
    sys.exit(3)

class Chan(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in CHAN:
            log.append(["meta_path", name])
            raise ImportError("test blocker: " + name)
        return None

_goc = builtins.__import__
def _import(name, globals=None, locals=None, fromlist=(), level=0):
    if level == 0 and name.split(".")[0] in CHAN:
        log.append(["__import__", name])
        raise ImportError("test blocker: " + name)
    return _goc(name, globals, locals, fromlist, level)

sys.meta_path.insert(0, Chan())
builtins.__import__ = _import
ket = {"truoc": truoc, "guard": guard}
try:
    spec = importlib.util.spec_from_file_location("source6_candidate_master_hd", sys.argv[1])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    ket["log_sau_nap"] = list(log)
    cases = json.loads(sys.argv[2])
    ket["cases"] = {k: mod.trich_xuat([tuple(p) for p in v], llm=None) for k, v in cases.items()}
    ket["log_quy_tac"] = list(log)
    ket["excel_san_sang"] = mod._EXCEL_SAN_SANG
    ket["sau"] = sorted(m for m in sys.modules if m.split(".")[0] in CHAN)
    # đối chứng: bộ chặn thật sự hoạt động và _excel() không nuốt lỗi thiếu thư viện
    try:
        mod._excel()
        ket["excel_bi_chan"] = "KHONG_LOI"
    except ImportError as e:
        ket["excel_bi_chan"] = str(e)
    ket["log_doi_chung"] = list(log)
    ket["excel_san_sang_sau_doi_chung"] = mod._EXCEL_SAN_SANG
except BaseException as e:
    ket["error"] = repr(e)
    ket["log_loi"] = list(log)
finally:
    builtins.__import__ = _goc
sys.stdout.write(json.dumps(ket, ensure_ascii=True))
'''


class TestRuleOnlyBlockedSubprocess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard_cha = _kiem_guard_cha()   # guard gốc của tiến trình test, trước khi spawn
        payload = json.dumps(CASES, ensure_ascii=True)
        # tiến trình Python mới cùng interpreter, kế thừa nguyên môi trường khởi động do Root kiểm soát (kể cả
        # PYTHONUSERBASE) để guard được nạp lúc khởi động; không -I/-E/-S/-s; script đọc từ stdin
        cls.proc = subprocess.run([sys.executable, "-B", "-X", "utf8", "-", str(CANDIDATE), payload], input=_SCRIPT_CHAN,
                                  capture_output=True, text=True, encoding="utf-8", timeout=120)

    def _ket(self):
        try:
            ket = json.loads(self.proc.stdout)
        except ValueError:
            self.fail(f"NOT_VERIFIED: child không trả JSON (rc={self.proc.returncode}); stderr={self.proc.stderr[-2000:]}")
        guard = ket.get("guard") or {}
        if "setup_error" in ket or not guard.get("ok"):
            self.fail(f"SETUP NOT_VERIFIED (guard trong child, candidate chưa được nạp): "
                      f"{json.dumps(guard, ensure_ascii=False)}; rc={self.proc.returncode}")
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        self.assertNotIn("error", ket, ket)
        return ket

    def test_khong_thu_import_numpy_openpyxl(self):
        ket = self._ket()
        self.assertEqual(ket["truoc"], [], "numpy/openpyxl đã nạp sẵn - phép thử không hợp lệ")
        self.assertEqual(ket["log_sau_nap"], [])
        self.assertEqual(ket["log_quy_tac"], [])
        self.assertEqual(ket["sau"], [])
        self.assertIs(ket["excel_san_sang"], False)

    def test_bo_chan_hoat_dong_va_khong_nuot_loi(self):
        ket = self._ket()
        self.assertIn("test blocker: openpyxl", ket["excel_bi_chan"])
        self.assertTrue(ket["log_doi_chung"], "đối chứng: _excel() phải chạm bộ chặn")
        self.assertEqual(ket["log_doi_chung"][0][1], "openpyxl")
        self.assertIs(ket["excel_san_sang_sau_doi_chung"], False)

    def test_golden_rule_only(self):
        ket = self._ket()
        for case, rows in ket["cases"].items():
            with self.subTest(case=case):
                self.assertEqual([r["ma"] for r in rows], MA_THU_TU)
                gold = GOLDEN[case]
                for r in rows:
                    ma = r["ma"]
                    want_keys = KEYS + (["items"] if ma in ("TT-60", "TT-61") else [])
                    self.assertEqual(list(r), want_keys, ma)
                    exp = gold.get(ma, (None, KTT, "", "", ""))
                    got = (r["gia_tri"], r["cach"], r["dieu"], r["trich"], r["ghi_chu"])
                    self.assertEqual(got, exp, f"{case} {ma}")
                    self.assertIs(type(r["gia_tri"]), type(exp[0]), f"{case} {ma} kiểu giá trị")
                    if ma in ("TT-60", "TT-61"):
                        self.assertEqual(r["items"], GOLDEN_ITEMS[case][ma], f"{case} {ma} items")


# ================================================================ 3. Excel thật (không chặn)
def _tao_ho_so(openpyxl, path):
    """File thanh toán tổng hợp: bảng chi tiết + sheet tổng hợp số."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Chi tiet"
    ws.cell(1, 1, "BẢNG XÁC ĐỊNH GIÁ TRỊ KHỐI LƯỢNG HOÀN THÀNH")
    hdr = ["STT", "Tên công việc", "Đơn vị", "Khối lượng hợp đồng", "Khối lượng kỳ trước", "Khối lượng kỳ này",
           "Lũy kế đến hết kỳ này", "Đơn giá", "Giá trị hợp đồng", "Giá trị kỳ này"]
    for j, h in enumerate(hdr, 1):
        ws.cell(3, j, h)
    data = [("A", "NHÀ KHO", None, None, None, None, None, None, None, None),
            ("1", "Bê tông móng", "m3", 10.5, 0, 4, 4, 1500000, 15750000, 6000000),
            ("2", "Cốt thép", "kg", 200, 50, 100, 150, 25000, 5000000, 2500000),
            (None, "Cộng", None, None, None, None, None, None, 20750000, 8500000)]
    for i, row in enumerate(data, 4):
        for j, v in enumerate(row, 1):
            if v is not None:
                ws.cell(i, j, v)
    t = wb.create_sheet("Tong hop")
    for i, (nhan, so_) in enumerate((("Giá trị hợp đồng", 20750000), ("Giá trị thực hiện kỳ này", 8500000),
                                     ("Lũy kế thực hiện đến hết kỳ này", 11000000), ("Giữ lại", 425000)), 1):
        t.cell(i, 1, nhan)
        t.cell(i, 2, so_)
    wb.save(path)


_TG = re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}")


def _chu_ky_o(c):
    v = c.value
    if isinstance(v, str):
        v = _TG.sub("<TG>", v)
    f, fl, al = c.font, c.fill, c.alignment
    return (c.coordinate, v, c.data_type, c.number_format,
            (f.name, f.sz, f.b, f.i, f.color.rgb if f.color is not None else None),
            (fl.fill_type, fl.fgColor.rgb if fl.fgColor is not None else None),
            (al.wrap_text, al.vertical))


def _chu_ky_wb(openpyxl, path):
    wb = openpyxl.load_workbook(path, data_only=False)
    out = {"sheets": wb.sheetnames}
    for ws in wb.worksheets:
        out[ws.title] = dict(
            freeze=ws.freeze_panes,
            cells=[_chu_ky_o(c) for row in ws.iter_rows() for c in row],
            widths={k: d.width for k, d in sorted(ws.column_dimensions.items())},
            heights={k: d.height for k, d in sorted(ws.row_dimensions.items()) if d.height},
            dv=[(d.type, d.formula1, d.allow_blank, str(d.sqref)) for d in ws.data_validations.dataValidation])
    return out


class TestExcelThat(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        _kiem_baseline()       # baseline pinned phải đúng trước khi import Excel thật
        cls.guard = _kiem_guard_cha()   # thư mục tạm chỉ tạo/dọn khi guard giữ-file gốc đang hiệu lực
        import openpyxl  # thư viện thật đã cài; thiếu/lỗi -> test lỗi thật, Root ghi NOT_VERIFIED
        cls.openpyxl = openpyxl
        cls.cand = _nap(CANDIDATE, "source6_lazy_excel_candidate")
        cls.orig = _nap(ORIGINAL, "source6_lazy_excel_pinned_original")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.ho_so = cls.dir / "ho_so.xlsx"
        _tao_ho_so(openpyxl, cls.ho_so)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _thu_muc(self, ten):
        d = self.dir / ten
        d.mkdir(exist_ok=True)
        return d

    # ---------------- dùng thư viện thật, style giống nguồn
    def test_openpyxl_that_va_style_giong_nguon(self):
        c, o, op = self.cand, self.orig, self.openpyxl
        c._excel()
        self.assertIs(c.openpyxl, sys.modules["openpyxl"])
        self.assertIs(c.openpyxl, op)
        from openpyxl.styles import Font, PatternFill
        from openpyxl.worksheet.datavalidation import DataValidation
        self.assertIs(c.Font, Font)
        self.assertIs(c.PatternFill, PatternFill)
        self.assertIs(c.DataValidation, DataValidation)
        for n in STYLE_NAMES:
            self.assertEqual(getattr(c, n), getattr(o, n), n)
        self.assertEqual((c.BASE.name, c.BASE.sz), ("Arial", 10))
        self.assertFalse(c.BASE.b)
        self.assertFalse(c.BASE.i)
        self.assertEqual((c.HFONT.b, c.HFONT.color.rgb, c.HFONT.sz), (True, "00FFFFFF", 10))
        self.assertEqual(c.BLUE.color.rgb, "000000FF")
        self.assertEqual([getattr(c, n).fgColor.rgb for n in ("HF", "YELLOW", "RED", "GREEN")],
                         ["001F4A7A", "00FFF2CC", "00F8D7D3", "00DDEFE3"])
        self.assertEqual((c.THIN.style, c.THIN.color.rgb), ("thin", "00BFC5C2"))
        self.assertEqual((c.NUMF, c.QF), (o.NUMF, o.QF))

    def test_ten_excel_qua_module_getattr_va_from_import(self):
        fresh = _nap(CANDIDATE, "source6_lazy_excel_fresh")
        self.assertIs(fresh._EXCEL_SAN_SANG, False)
        self.assertNotIn("BASE", vars(fresh))
        self.assertEqual(fresh.BASE, self.orig.BASE)       # truy cập thuộc tính -> nạp Excel thật
        self.assertIs(fresh._EXCEL_SAN_SANG, True)
        fresh2 = _nap(CANDIDATE, "source6_lazy_excel_fresh2")
        ns = {}
        exec("from source6_lazy_excel_fresh2 import BASE, BOLD, GREEN, NUMF, QF, RED, YELLOW, HF, HFONT, put, header", ns)
        self.assertEqual(ns["HFONT"], self.orig.HFONT)
        self.assertEqual(ns["GREEN"], self.orig.GREEN)
        with self.assertRaises(AttributeError):
            getattr(fresh2, "khong_co_ten_nay")
        with self.assertRaises(ImportError):
            exec("from source6_lazy_excel_fresh2 import khong_co_ten_nay", {})

    # ---------------- put / header
    def test_put_font_mac_dinh_tuong_minh_va_tuy_chinh(self):
        c, op = self.cand, self.openpyxl
        c._excel()
        wb = op.Workbook()
        ws = wb.active
        a = c.put(ws, 1, 1, "mặc định")
        b = c.put(ws, 1, 2, "BASE tường minh", font=c.BASE)
        rieng = op.styles.Font(name="Times New Roman", size=14, italic=True, color="00112233")
        d = c.put(ws, 1, 3, "tùy chỉnh", rieng)
        e = c.put(ws, 1, 4, "BOLD vị trí", c.BOLD)
        self.assertEqual(a.font, c.BASE)
        self.assertEqual(b.font, c.BASE)
        self.assertEqual(d.font, rieng)
        self.assertEqual((d.font.name, d.font.sz, d.font.i), ("Times New Roman", 14, True))
        self.assertEqual(e.font, c.BOLD)
        import inspect
        self.assertIs(inspect.signature(c.put).parameters["font"].default, c._BASE_MAC_DINH)
        # công thức vs text=True, định dạng, nền, xuống dòng
        f1 = c.put(ws, 2, 1, "=SUM(1,2)")
        f2 = c.put(ws, 2, 2, "=SUM(1,2)", text=True)
        f3 = c.put(ws, 2, 3, 1234.5, fmt=c.NUMF, fill=c.YELLOW, wrap=True)
        f4 = c.put(ws, 2, 4, 0.155, fmt="0.00%")
        self.assertEqual((f1.data_type, f1.value), ("f", "=SUM(1,2)"))
        self.assertEqual((f2.data_type, f2.value), ("s", "=SUM(1,2)"))
        self.assertEqual(f3.number_format, c.NUMF)
        self.assertEqual(f3.fill, c.YELLOW)
        self.assertEqual((f3.alignment.wrap_text, f3.alignment.vertical), (True, "top"))
        self.assertEqual(f4.number_format, "0.00%")
        c.header(ws, 4, ["Mã", "Tham số", "Giá trị"], [8, 34, 22])
        p = self._thu_muc("put") / "put.xlsx"
        wb.save(p)
        w2 = op.load_workbook(p, data_only=False)
        s = w2.active
        self.assertEqual(s["A1"].font, c.BASE)
        self.assertEqual(s["B1"].font, c.BASE)
        self.assertEqual((s["C1"].font.name, s["C1"].font.sz, s["C1"].font.i), ("Times New Roman", 14, True))
        self.assertTrue(s["D1"].font.b)
        self.assertEqual((s["A2"].data_type, s["A2"].value), ("f", "=SUM(1,2)"))
        self.assertEqual((s["B2"].data_type, s["B2"].value), ("s", "=SUM(1,2)"))
        self.assertEqual(s["C2"].number_format, c.NUMF)
        self.assertEqual(s["C2"].fill.fgColor.rgb, "00FFF2CC")
        self.assertTrue(s["C2"].alignment.wrap_text)
        self.assertEqual(s["D2"].number_format, "0.00%")
        self.assertEqual(s["A4"].font, c.HFONT)
        self.assertEqual(s["A4"].fill.fgColor.rgb, "001F4A7A")
        self.assertEqual((s["B4"].alignment.wrap_text, s["B4"].alignment.vertical), (True, "center"))
        self.assertEqual([s.column_dimensions[k].width for k in "ABC"], [8, 34, 22])
        self.assertEqual(s.row_dimensions[4].height, 32)
        self.assertEqual(s.freeze_panes, "A5")

    # ---------------- quy tắc: candidate = nguồn pinned (khi Excel có thật)
    def test_trich_xuat_giong_nguon(self):
        for k, paras in CASES.items():
            self.assertEqual(self.cand.trich_xuat(paras, llm=None), self.orig.trich_xuat(paras, llm=None), k)

    # ---------------- ghi_master -> doc_master -> nap_dot -> doi_chieu
    def _quy_trinh(self, mod, ten):
        d = self._thu_muc(ten)
        op = self.openpyxl
        rows = mod.trich_xuat(CASE_TC01, llm=None)
        boq = mod.tim_bang_chi_tiet(op.load_workbook(self.ho_so, data_only=True))
        master = d / "master.xlsx"
        mod.ghi_master(master, "hop_dong_mau.docx", rows, boq, "ho_so.xlsx")
        doc = mod.doc_master(master)
        nap = mod.nap_dot(master, self.ho_so, 1)
        doc2 = mod.doc_master(master)
        out = d / "doi_chieu.xlsx"
        dc_rows, tong, cnt = mod.doi_chieu(master, self.ho_so, out)
        return d, boq, doc, nap, doc2, (dc_rows, tong, cnt)

    def test_quy_trinh_master_ngu_nghia_va_giong_nguon(self):
        op, c = self.openpyxl, self.cand
        d, boq, doc, nap, doc2, dc = self._quy_trinh(c, "qt_cand")
        d0, boq0, doc0, nap0, doc20, dc0 = self._quy_trinh(self.orig, "qt_orig")
        # giá trị trả về giống nguồn
        self.assertEqual(boq, boq0)
        self.assertEqual(doc, doc0)
        self.assertEqual(nap, nap0)
        self.assertEqual(doc2, doc20)
        self.assertEqual(dc, dc0)
        # ngữ nghĩa
        k1, k2 = "nha kho|be tong mong|m3", "nha kho|cot thep|kg"
        self.assertEqual([i["khoa"] for i in boq["items"] if i["dvt"]], [k1, k2])
        p, bq, kt, ls = doc
        self.assertEqual(p["TC-01"], dict(ten="Số hợp đồng", gia_tri="0001/2026", trang_thai="Chưa xác nhận"))
        self.assertEqual(p["TT-02"]["gia_tri"], 1234567890)
        self.assertEqual(bq[k1], dict(ma="HM0001", stt="1", nhom="NHÀ KHO", ten="Bê tông móng", dvt="m3",
                                      kl_hd=10.5, don_gia=1500000.0))
        self.assertEqual(set(bq), {k1, k2})
        self.assertEqual(kt["HM0001"], dict(kl=None, dot=None, nguon="Đợt đầu: nhập tay (hoặc 0 nếu chưa thi công)"))
        self.assertEqual(ls, [])
        ok, miss, tong = nap
        self.assertEqual((ok, miss), (2, []))
        self.assertEqual({k: (v["gia_tri"], v["o"]) for k, v in tong.items()},
                         {"gt_hd": (20750000.0, "Tong hop!B1"), "gt_kn": (8500000.0, "Tong hop!B2"),
                          "gt_lk": (11000000.0, "Tong hop!B3"), "giu_lai": (425000.0, "Tong hop!B4")})
        self.assertEqual({k: v["kl"] for k, v in doc2[2].items()}, {"HM0001": 4, "HM0002": 150})
        self.assertEqual(doc2[3][0][0], 1)
        self.assertEqual(doc2[3][0][2], 8500000)
        dc_rows, _, cnt = dc
        self.assertEqual([r["ma"] for r in dc_rows], ["HM0001", "HM0002"])
        self.assertEqual(cnt, Counter({"KL kỳ trước khác master (đợt trước đã duyệt)": 2}))

        # master sau round-trip (data_only=False): style/công thức/validation
        wb = op.load_workbook(d / "master.xlsx", data_only=False)
        self.assertEqual(wb.sheetnames, ["Huong dan", "Thong tin HD", "Dieu khoan TT", "Ho so TT theo HD", "BOQ",
                                         "Phu luc", "KL ky truoc", "Lich su TT", "Nhat ky"])
        hd = wb["Huong dan"]
        self.assertEqual(hd["A1"].font, c.BOLD)
        self.assertEqual(hd["A4"].font, c.BASE)
        self.assertEqual(hd.column_dimensions["A"].width, 120)
        for sh in ("Thong tin HD", "Dieu khoan TT"):
            ws = wb[sh]
            dvs = ws.data_validations.dataValidation
            self.assertEqual(len(dvs), 1, sh)
            self.assertEqual((dvs[0].type, dvs[0].formula1, dvs[0].allow_blank),
                             ("list", '"Chưa xác nhận,Đã xác nhận,Đã sửa tay,Không áp dụng"', True))
            self.assertIn("I2", dvs[0].sqref)
            self.assertEqual(ws.freeze_panes, "A2")
            self.assertEqual(ws["A1"].font, c.HFONT)
            self.assertEqual(ws["I2"].value, "Chưa xác nhận")
            self.assertEqual(ws["I2"].fill.fgColor.rgb, "00FFF2CC")
        th = wb["Thong tin HD"]
        self.assertEqual((th["A2"].value, th["D2"].value), ("TC-01", "0001/2026"))
        self.assertEqual(th["D2"].fill.fgColor.rgb, "00FFF2CC")
        self.assertEqual((th["A5"].value, th["D5"].value, th["D5"].fill.fgColor.rgb), ("TC-04", None, "00F8D7D3"))
        self.assertEqual((th["D2"].alignment.wrap_text, th["D2"].alignment.vertical), (True, "top"))
        dk = wb["Dieu khoan TT"]
        self.assertEqual((dk["A3"].value, dk["D3"].value, dk["D3"].number_format), ("TT-02", 1234567890, c.NUMF))
        self.assertEqual((dk["A5"].value, dk["D5"].value, dk["D5"].number_format), ("TT-04", 0.1, "0.00%"))
        boq_ws = wb["BOQ"]
        self.assertEqual([boq_ws.cell(r, 1).value for r in (2, 3)], ["HM0001", "HM0002"])
        self.assertEqual((boq_ws["F2"].value, boq_ws["F2"].number_format), (10.5, c.QF))
        self.assertEqual(boq_ws["F2"].font, c.BLUE)
        self.assertEqual((boq_ws["G2"].number_format, boq_ws["G2"].font.color.rgb), (c.NUMF, "000000FF"))
        self.assertEqual((boq_ws["H2"].data_type, boq_ws["H2"].value), ("f", "=ROUND(F2*G2,0)"))
        self.assertEqual((boq_ws["K2"].data_type, boq_ws["K2"].value), ("s", k1))
        self.assertEqual((boq_ws["K2"].font.sz, boq_ws["K2"].font.color.rgb), (8, "00808080"))
        self.assertEqual((boq_ws["D5"].value, boq_ws["D5"].font), ("Cộng (chưa VAT)", c.BOLD))
        self.assertEqual((boq_ws["H5"].data_type, boq_ws["H5"].value), ("f", "=SUM(H2:H3)"))
        self.assertEqual(boq_ws["H6"].value,
                         "=ROUND(H5*INDEX('Dieu khoan TT'!D:D,MATCH(\"TT-04\",'Dieu khoan TT'!A:A,0)),0)")
        self.assertEqual((boq_ws["H9"].value, boq_ws["H9"].fill.fgColor.rgb), ("=H7-H8", "00FFF2CC"))
        kt_ws = wb["KL ky truoc"]
        self.assertEqual((kt_ws["D2"].value, kt_ws["D2"].number_format, kt_ws["D2"].font.color.rgb), (4, c.QF, "000000FF"))
        self.assertEqual(kt_ws["G2"].value, 1)
        self.assertEqual(kt_ws["H2"].value, "ho_so.xlsx (Chi tiet!dòng 5, cột lũy kế đến hết kỳ này)")
        self.assertEqual(kt_ws["E2"].value, "=INDEX(BOQ!G:G,MATCH(A2,BOQ!A:A,0))")
        ls_ws = wb["Lich su TT"]
        self.assertEqual((ls_ws["A2"].value, ls_ws["A2"].font), (1, c.BASE))
        self.assertEqual((ls_ws["C2"].value, ls_ws["C2"].number_format, ls_ws["C2"].font), (8500000, c.NUMF, c.BLUE))
        self.assertEqual(ls_ws["B2"].fill.fgColor.rgb, "00FFF2CC")
        self.assertEqual(ls_ws["J2"].value,
                         "ho_so.xlsx: gt_hd=Tong hop!B1; gt_kn=Tong hop!B2; gt_lk=Tong hop!B3; giu_lai=Tong hop!B4")
        nk = wb["Nhat ky"]
        self.assertEqual([nk.cell(r, 2).value for r in (2, 3)], ["Tạo master", "Nạp đợt 1"])
        # kết quả đối chiếu
        w3 = op.load_workbook(d / "doi_chieu.xlsx", data_only=False)
        self.assertEqual(w3.sheetnames, ["Tong hop", "Hang muc", "Thieu trong ho so"])
        th = w3["Tong hop"]
        self.assertEqual(th.freeze_panes, "A5")
        self.assertEqual((th["A1"].font.b, th["A1"].font.sz), (True, 12))
        self.assertEqual((th["D5"].data_type, th["D5"].value), ("f", "=B5-C5"))
        self.assertEqual(th["E5"].value, '=IF(ABS(D5)<=1,"Khớp","Lệch - kiểm tra")')
        self.assertEqual(th["B6"].number_format, "0.00%")
        hm = w3["Hang muc"]
        self.assertEqual(hm["M2"].value, '=IF(H2="","",(G2-H2)*L2)')
        self.assertEqual((hm["O2"].value, hm["O2"].fill.fgColor.rgb),
                         ("KL kỳ trước khác master (đợt trước đã duyệt)", "00F8D7D3"))
        self.assertEqual(hm["E2"].number_format, c.QF)
        # toàn bộ file giống nguồn (ô, kiểu, định dạng, độ rộng, cố định dòng, validation)
        for f in ("master.xlsx", "doi_chieu.xlsx"):
            self.assertEqual(_chu_ky_wb(op, d / f), _chu_ky_wb(op, d0 / f), f)

    # ---------------- ghi_so_sanh (dữ liệu AI tổng hợp, không gọi mạng)
    def test_ghi_so_sanh_giong_nguon(self):
        op, c = self.openpyxl, self.cand
        ai = {"TC-01": {"gia_tri": "0001/2026", "trich_dan": "Số: 0001/2026", "dieu_khoan": "", "ghi_chu": ""},
              "TT-04": {"gia_tri": "12%", "trich_dan": "=bịa 12%", "dieu_khoan": "Điều 3", "ghi_chu": "=ghi chú"}}
        full = "\n".join(t for _, t in CASE_TC01)
        stats = {"token_vao": 10, "token_ra": 5, "giay": 1.5}
        outs = []
        for mod, ten in ((c, "ss_cand"), (self.orig, "ss_orig")):
            rows = mod.trich_xuat(CASE_TC01, llm=None)
            cmp = mod.so_sanh_ai(rows, ai, full)
            out = self._thu_muc(ten) / "so_sanh.xlsx"
            mod.ghi_so_sanh(out, "hop_dong_mau.docx", cmp, stats, "model-mau", 1234, True)
            outs.append(out)
        ws = op.load_workbook(outs[0], data_only=False)["So sanh"]
        self.assertEqual((ws["A1"].font.b, ws["A1"].font.sz), (True, 12))
        self.assertTrue(ws["A2"].value.startswith("Hợp đồng: hop_dong_mau.docx | Model: model-mau | Văn bản gửi AI: 1,234 ký tự (đã ẩn danh)"))
        self.assertEqual(ws.freeze_panes, "C5")
        self.assertEqual(ws["A4"].fill.fgColor.rgb, "001F4A7A")
        self.assertEqual((ws["A5"].value, ws["E5"].value, ws["E5"].fill.fgColor.rgb), ("TC-01", "Khớp", "00DDEFE3"))
        r = 5 + MA_THU_TU.index("TT-04")
        self.assertEqual((ws.cell(r, 1).value, ws.cell(r, 5).value, ws.cell(r, 5).fill.fgColor.rgb), ("TT-04", "Lệch", "00F8D7D3"))
        self.assertEqual((ws.cell(r, 7).data_type, ws.cell(r, 7).value), ("s", "=bịa 12%"))
        self.assertEqual((ws.cell(r, 9).data_type, ws.cell(r, 9).value), ("s", "=ghi chú"))
        self.assertEqual(ws.cell(r, 6).value, "KHÔNG - AI viết lại hoặc bịa")
        self.assertEqual(ws.cell(r, 6).fill.fgColor.rgb, "00F8D7D3")
        self.assertEqual(_chu_ky_wb(op, outs[0]), _chu_ky_wb(op, outs[1]))

    # ---------------- CLI: tao / nap-dot / doi-chieu / cham (ai-trich cần máy AI: không kiểm ở đây)
    def _cli(self, mod, d, hop_dong, gold, ket):
        lenh = [["tao", str(hop_dong), "--boq", str(self.ho_so), "--out", str(d / "master.xlsx")],
                ["nap-dot", str(d / "master.xlsx"), str(self.ho_so), "--dot", "1"],
                ["doi-chieu", str(d / "master.xlsx"), str(self.ho_so), "--out", str(d / "doi_chieu.xlsx")],
                ["cham", str(gold), str(ket), "--out", str(d / "cham.xlsx")]]
        in_ra = []
        argv = sys.argv
        try:
            for args in lenh:
                sys.argv = ["master_hd.py"] + args
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    mod.main()
                in_ra.append(buf.getvalue().replace(str(d), "<OUT>"))
        finally:
            sys.argv = argv
        return in_ra

    def test_cli_excel_giong_nguon(self):
        op = self.openpyxl
        vao = self._thu_muc("cli_vao")
        hop_dong = vao / "hop_dong_mau.txt"
        hop_dong.write_text("\n".join(t for _, t in CASE_TC01) + "\n", encoding="utf-8")
        gold = vao / "dap_an.tsv"
        gold.write_text("Mã\tNhóm\tTham số\tGiá trị\tĐơn vị\tĐiều\tTrích dẫn\tGhi chú\n"
                        "TC-01\tThông tin chung\tSố hợp đồng\t0001/2026\t\tĐầu\tSố: 0001/2026\t\n"
                        "TT-04\tGiá hợp đồng\tThuế suất GTGT\t10%\t%\tĐiều 3\tthuế GTGT 10%\t\n"
                        "TT-05\tGiá hợp đồng\tCơ sở\t=A1 không phải công thức\t\t\t\tbẫy dấu bằng\n", encoding="utf-8")
        ket = vao / "ket_qua.tsv"
        ket.write_text("TC-01\t\t\t0001/2026\t\t\tSố: 0001/2026\t\n"
                       "TT-04\t\t\t12%\t%\t\t\t\n"
                       "TT-05\t\t\t=A1 không phải công thức\t\t\t\t=ghi chú\n", encoding="utf-8")
        dc, do = self._thu_muc("cli_cand"), self._thu_muc("cli_orig")
        out_c = self._cli(self.cand, dc, hop_dong, gold, ket)
        out_o = self._cli(self.orig, do, hop_dong, gold, ket)
        self.assertEqual(out_c, out_o)
        self.assertIn("Nạp 2 hạng mục; 0 không khớp BOQ", out_c[1])
        for f in ("master.xlsx", "doi_chieu.xlsx", "cham.xlsx"):
            self.assertEqual(_chu_ky_wb(op, dc / f), _chu_ky_wb(op, do / f), f)
        ws = op.load_workbook(dc / "cham.xlsx", data_only=False)["Cham diem"]
        self.assertEqual(ws.freeze_panes, "A5")
        self.assertEqual([ws.cell(r, 1).value for r in (5, 6, 7)], ["TC-01", "TT-04", "TT-05"])
        self.assertEqual((ws["D5"].value, ws["D5"].fill.fgColor.rgb), ("Đúng", "00DDEFE3"))
        self.assertEqual((ws["D6"].value, ws["D6"].fill.fgColor.rgb), ("Sai", "00F8D7D3"))
        self.assertEqual((ws["B7"].data_type, ws["B7"].value), ("s", "=A1 không phải công thức"))
        self.assertEqual((ws["F7"].data_type, ws["F7"].value), ("s", "=ghi chú"))


if __name__ == "__main__":
    unittest.main()
