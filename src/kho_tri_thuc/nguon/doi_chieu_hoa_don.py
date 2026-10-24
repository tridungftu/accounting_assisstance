"""Đối chiếu hóa đơn M2 ↔ M5 — lõi báo cáo THUẦN (gói DOI-CHIEU-HOA-DON-PURE-01, CODE_ONLY; coder KHÔNG chạy).

Đầu bài: docs/GIAO-CODE-DOI-CHIEU-HOA-DON-PURE-01.md; báo cáo: docs/BAO-CAO-DOI-CHIEU-HOA-DON-PURE-01.md.

- `HoaDonDoiChieu`/`DongDoiChieu` là DTO NỘI BỘ cho báo cáo; KHÔNG là schema nguồn M5, không authority duyệt/ghi sổ/liên kết.
- Phía M2 dựng bằng `tu_ket_qua_m2` từ output bộ đọc `hoa_don_xml` sẵn có (canonical_identity, raw_ref, source_locator, field qua
  `duy_nhat`, quantity chỉ khi EXACT). Không parser/identity thứ hai, không dùng số lượng chuẩn hóa hay proof L11.
- Phía M5: format import/export thật EXTERNAL_BINDING_PENDING — module KHÔNG có reader/adapter M5; caller tương lai bind format rồi dựng DTO.
- Báo thiếu/thừa/trùng hóa đơn theo khóa 6 chuỗi (PN, chiều, MST bán, mẫu, ký hiệu, số chuẩn) và chênh số lượng dòng theo mã hàng exact.
  Không quy đổi đơn vị, pool, allocation, tolerance, cộng tiền, thuế, duyệt hay ghi sổ. Không suy phiên bản sửa/hủy/điều chỉnh.
- Không I/O, giờ, UUID, env, DB, network. Kết quả là dict/list/str/int/None MỚI mỗi lần gọi, xác định, không phụ thuộc thứ tự input.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import (ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, Inexact, InvalidOperation, Overflow, Rounded)

from ..ha_tang.primitives import DataError, canonical_json
from .hoa_don_xml import _DECIMAL, QUANTITY_MAX_DIGITS, QUANTITY_MAX_SCALE, InvoiceReadResult, _prefix

CONTRACT = "DOI_CHIEU_HOA_DON_PURE_V1"
DELTA_BASIS = "M5_MINUS_M2"

TINH_CHAT = ("GOODS", "PROMOTION", "DISCOUNT", "NOTE", "SPECIAL_GOODS", "UNKNOWN")  # đúng tập nature của parser M2
_TINH_CHAT_NGOAI = frozenset({"DISCOUNT", "NOTE", "SPECIAL_GOODS"})  # không so số lượng, vẫn giữ trong báo cáo

TRANG_THAI_HOA_DON = ("PAIRED", "MISSING_IN_M5", "EXCESS_IN_M5", "DUPLICATE")
TRANG_THAI_DONG = ("MATCH", "DIFFERENCE", "UNIT_MISMATCH", "UNKNOWN", "OUT_OF_SCOPE", "AMBIGUOUS", "MISSING_IN_M5", "EXCESS_IN_M5",
                   "UNMATCHED_NO_CODE")

# Context riêng, bẫy Inexact/Rounded: phép trừ luôn exact và không phụ thuộc context Decimal ambient của caller.
# Miền 21 chữ số / 6 thập phân ⇒ hiệu ≤ 28 chữ số, prec 64 dư.
_CTX = Context(prec=64, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999, capitals=1, clamp=0, flags=[],
               traps=[InvalidOperation, DivisionByZero, Overflow, Inexact, Rounded])


def _loi(code: str, message: str, locator: str = "$"):
    raise DataError(code, message, locator)


def _chuoi(v, f: str) -> str:
    if not isinstance(v, str) or v == "":
        _loi("DOI_CHIEU_KIEU", f"{f} phải là chuỗi không rỗng.", f)
    return v


def _chuoi_hoac_none(v, f: str) -> str | None:
    if v is not None and not isinstance(v, str):
        _loi("DOI_CHIEU_KIEU", f"{f} phải là chuỗi hoặc None.", f)
    return v


def _van_de(v, f: str) -> tuple:
    if not isinstance(v, (tuple, list)):
        _loi("DOI_CHIEU_KIEU", f"{f} phải là tuple/list mã vấn đề.", f)
    out = tuple(v)
    for i, x in enumerate(out):
        if not isinstance(x, str) or x == "":
            _loi("DOI_CHIEU_KIEU", f"{f}[{i}] phải là chuỗi không rỗng.", f"{f}[{i}]")
    return out


def _khong_trung(codes) -> tuple:
    out: list[str] = []
    for c in codes:
        if c not in out:
            out.append(c)
    return tuple(out)


# ---------------------------------------------------------------------------------------------------------------- DTO nội bộ (frozen)
@dataclass(frozen=True)
class DongDoiChieu:
    """Một dòng nguồn. ma_hang/don_vi/so_luong_text None = thiếu/mơ hồ/không cấp (chi tiết ở van_de); không đoán, không mặc định 0."""
    tham_chieu_dong: str
    ma_hang: str | None
    don_vi: str | None
    so_luong_text: str | None
    tinh_chat: str = "GOODS"
    van_de: tuple = ()

    def __post_init__(self):
        _chuoi(self.tham_chieu_dong, "DongDoiChieu.tham_chieu_dong")
        _chuoi_hoac_none(self.ma_hang, "DongDoiChieu.ma_hang")
        _chuoi_hoac_none(self.don_vi, "DongDoiChieu.don_vi")
        if self.so_luong_text is not None and not isinstance(self.so_luong_text, str):
            _loi("DOI_CHIEU_SO_LUONG_KIEU", "so_luong_text chỉ nhận str hoặc None (không int/float/bool/Decimal).",
                 "DongDoiChieu.so_luong_text")
        if not isinstance(self.tinh_chat, str) or self.tinh_chat not in TINH_CHAT:
            _loi("DOI_CHIEU_TINH_CHAT", f"tinh_chat phải thuộc {', '.join(TINH_CHAT)}.", "DongDoiChieu.tinh_chat")
        object.__setattr__(self, "van_de", _van_de(self.van_de, "DongDoiChieu.van_de"))


@dataclass(frozen=True)
class HoaDonDoiChieu:
    """Một bản ghi hóa đơn của một phía. khoa_hoa_don = 6 chuỗi không rỗng hoặc None (unresolved); không normalize/mặc định."""
    ma_ban_ghi: str
    tham_chieu_nguon: str
    khoa_hoa_don: tuple | None
    dong: tuple
    van_de: tuple = ()

    def __post_init__(self):
        _chuoi(self.ma_ban_ghi, "HoaDonDoiChieu.ma_ban_ghi")
        _chuoi(self.tham_chieu_nguon, "HoaDonDoiChieu.tham_chieu_nguon")
        k = self.khoa_hoa_don
        if k is not None:
            if not isinstance(k, (tuple, list)) or len(k) != 6 or any(not isinstance(x, str) or x == "" for x in k):
                _loi("DOI_CHIEU_KHOA_KIEU", "khoa_hoa_don phải là None hoặc 6 chuỗi không rỗng (PN, chiều, MST bán, mẫu, ký hiệu, số chuẩn).",
                     "HoaDonDoiChieu.khoa_hoa_don")
            object.__setattr__(self, "khoa_hoa_don", tuple(k))
        if not isinstance(self.dong, (tuple, list)):
            _loi("DOI_CHIEU_KIEU", "dong phải là tuple/list DongDoiChieu.", "HoaDonDoiChieu.dong")
        dong = tuple(self.dong)
        da_thay: set[str] = set()
        for i, d in enumerate(dong):
            if not isinstance(d, DongDoiChieu):
                _loi("DOI_CHIEU_KIEU", f"dong[{i}] phải là DongDoiChieu.", f"HoaDonDoiChieu.dong[{i}]")
            if d.tham_chieu_dong in da_thay:
                _loi("DOI_CHIEU_REF_DONG_TRUNG", f"tham_chieu_dong '{d.tham_chieu_dong}' trùng trong bản ghi '{self.ma_ban_ghi}'.",
                     f"HoaDonDoiChieu.dong[{i}]")
            da_thay.add(d.tham_chieu_dong)
        object.__setattr__(self, "dong", dong)
        object.__setattr__(self, "van_de", _van_de(self.van_de, "HoaDonDoiChieu.van_de"))


# ---------------------------------------------------------------------------------------------------------------- M2 → DTO (reuse parser)
def _text_duy_nhat(line, name: str) -> str | None:
    fv = line.field(name).duy_nhat
    return fv.lexeme if fv is not None and fv.state == "TEXT" else None


def tu_ket_qua_m2(ma_ban_ghi: str, result: InvoiceReadResult) -> HoaDonDoiChieu:
    """Dựng DTO từ InvoiceReadResult của bộ đọc M2. Khóa = canonical_identity của parser (None giữ None); tham chiếu nguồn = tiền tố
    locator parser (`xml:<sha>` hoặc `zip:<container>!<ordinal>:<entry>`); dòng = `<nguồn>#<source_locator>` (locator mang ordinal nguồn).
    Mã hàng/đơn vị chỉ lấy occurrence TEXT duy nhất; số lượng chỉ exact_text khi quantity.state == 'EXACT'. Vấn đề hóa đơn = mã issue
    không thuộc dòng + candidate_reasons; vấn đề dòng = mã issue của dòng."""
    if not isinstance(result, InvoiceReadResult):
        _loi("DOI_CHIEU_KIEU", "result phải là InvoiceReadResult của bộ đọc M2.", "result")
    nguon = _prefix(result.raw_ref)
    cua_dong = {i for ln in result.lines for i in ln.issues}
    dong = tuple(DongDoiChieu(tham_chieu_dong=f"{nguon}#{ln.source_locator}", ma_hang=_text_duy_nhat(ln, "MHHDVu"),
                              don_vi=_text_duy_nhat(ln, "DVTinh"),
                              so_luong_text=ln.quantity.exact_text if ln.quantity.state == "EXACT" else None,
                              tinh_chat=ln.nature, van_de=_khong_trung(i.code for i in ln.issues))
                 for ln in result.lines)
    van_de = _khong_trung([i.code for i in result.issues if i not in cua_dong] + list(result.candidate_reasons))
    return HoaDonDoiChieu(ma_ban_ghi, nguon, result.canonical_identity, dong, van_de)


# ---------------------------------------------------------------------------------------------------------------- số lượng
def _so_luong(text: str | None) -> tuple[Decimal | None, list[str]]:
    """Ngữ pháp/miền như M2: -?[0-9]+(\\.[0-9]+)?, ≤21 chữ số, ≤6 thập phân. Sai → (None, lý do); không crash, không 0."""
    if text is None:
        return None, ["QUANTITY_MISSING"]
    if text == "":
        return None, ["QUANTITY_EMPTY"]
    if not _DECIMAL.fullmatch(text):
        return None, ["QUANTITY_LEXEME_INVALID"]
    digits = sum(ch.isdigit() for ch in text)
    scale = len(text.split(".", 1)[1]) if "." in text else 0
    ly_do = (["QUANTITY_DIGITS_EXCEEDED"] if digits > QUANTITY_MAX_DIGITS else []) + (
        ["QUANTITY_SCALE_EXCEEDED"] if scale > QUANTITY_MAX_SCALE else [])
    if ly_do:
        return None, ly_do
    return Decimal(text), []  # constructor exact, không theo context


def _hieu(m5: Decimal, m2: Decimal) -> str:
    """M5 − M2 exact trong _CTX; text cố định không exponent, bỏ 0 thừa sau dấu chấm, 0 (kể cả -0) → '0'."""
    s = format(_CTX.subtract(m5, m2), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("0", "-0") else s


# ---------------------------------------------------------------------------------------------------------------- dựng output
def _ra_dong(d: DongDoiChieu) -> dict:
    return {"tham_chieu_dong": d.tham_chieu_dong, "ma_hang": d.ma_hang, "don_vi": d.don_vi, "so_luong_text": d.so_luong_text,
            "tinh_chat": d.tinh_chat, "van_de": list(d.van_de)}


def _ra_ban_ghi(h: HoaDonDoiChieu) -> dict:
    return {"ma_ban_ghi": h.ma_ban_ghi, "tham_chieu_nguon": h.tham_chieu_nguon, "van_de": list(h.van_de), "so_dong": len(h.dong),
            "tham_chieu_dong": sorted(d.tham_chieu_dong for d in h.dong)}


def _muc(trang_thai: str, ma_hang, ly_do: list, delta, m2: list, m5: list) -> dict:
    return {"trang_thai": trang_thai, "ma_hang": ma_hang, "ly_do": list(ly_do), "delta": delta,
            "m2": [_ra_dong(d) for d in m2], "m5": [_ra_dong(d) for d in m5]}


def _ref(d: DongDoiChieu) -> str:
    return d.tham_chieu_dong


def _so_cap(ma: str, x: DongDoiChieu, y: DongDoiChieu) -> dict:
    """Một cặp dòng mã duy nhất hai phía. Lý do gom đủ (tính chất → đơn vị → số lượng); trạng thái theo thứ tự ưu tiên:
    OUT_OF_SCOPE > UNKNOWN (tính chất) > UNKNOWN (đơn vị thiếu) > UNIT_MISMATCH > UNKNOWN (số lượng) > MATCH/DIFFERENCE."""
    ly_do: list[str] = []
    ngoai = x.tinh_chat in _TINH_CHAT_NGOAI or y.tinh_chat in _TINH_CHAT_NGOAI
    if ngoai:
        ly_do.append("NATURE_OUT_OF_SCOPE")
    tc_chua_ro = False
    for phia, d in (("M2", x), ("M5", y)):
        if d.tinh_chat == "UNKNOWN":
            ly_do.append(f"NATURE_UNKNOWN_{phia}"); tc_chua_ro = True
    if not ngoai and not tc_chua_ro and x.tinh_chat != y.tinh_chat:
        ly_do.append("NATURE_MISMATCH"); tc_chua_ro = True
    dv_thieu = False
    for phia, d in (("M2", x), ("M5", y)):
        if d.don_vi is None:
            ly_do.append(f"UNIT_MISSING_{phia}"); dv_thieu = True
        elif d.don_vi == "":
            ly_do.append(f"UNIT_EMPTY_{phia}"); dv_thieu = True
    dv_khac = not dv_thieu and x.don_vi != y.don_vi  # exact: không trim/casefold/quy đổi
    if dv_khac:
        ly_do.append("UNIT_MISMATCH")
    q2, r2 = _so_luong(x.so_luong_text)
    q5, r5 = _so_luong(y.so_luong_text)
    ly_do.extend([f"{r}_M2" for r in r2] + [f"{r}_M5" for r in r5])
    delta = None
    if ngoai:
        st = "OUT_OF_SCOPE"
    elif tc_chua_ro or dv_thieu:
        st = "UNKNOWN"
    elif dv_khac:
        st = "UNIT_MISMATCH"
    elif r2 or r5:
        st = "UNKNOWN"
    else:
        delta = _hieu(q5, q2)
        st = "MATCH" if delta == "0" else "DIFFERENCE"
    return _muc(st, ma, ly_do, delta, [x], [y])


def _so_dong(a: HoaDonDoiChieu, b: HoaDonDoiChieu) -> list[dict]:
    """Ghép dòng theo ma_hang exact, chỉ khi mã duy nhất ở CẢ hai bản ghi. Không fuzzy/STT/ordinal/gộp dòng cùng mã."""
    def nhom(h):
        co: dict[str, list] = {}
        khong: list = []
        for d in h.dong:
            if d.ma_hang is None or d.ma_hang == "":
                khong.append(d)
            else:
                co.setdefault(d.ma_hang, []).append(d)
        return co, khong

    co2, khong2 = nhom(a)
    co5, khong5 = nhom(b)
    out = []
    for ma in sorted(set(co2) | set(co5)):
        x, y = sorted(co2.get(ma, []), key=_ref), sorted(co5.get(ma, []), key=_ref)
        if len(x) > 1 or len(y) > 1:
            ly_do = ((["CODE_REPEATED_M2"] if len(x) > 1 else []) + (["CODE_REPEATED_M5"] if len(y) > 1 else [])
                     + (["CODE_ABSENT_M2"] if not x else []) + (["CODE_ABSENT_M5"] if not y else []))
            out.append(_muc("AMBIGUOUS", ma, ly_do, None, x, y))
        elif not y:
            out.append(_muc("MISSING_IN_M5", ma, ["CODE_ABSENT_M5"], None, x, []))
        elif not x:
            out.append(_muc("EXCESS_IN_M5", ma, ["CODE_ABSENT_M2"], None, [], y))
        else:
            out.append(_so_cap(ma, x[0], y[0]))
    for phia, ds in (("M2", khong2), ("M5", khong5)):
        for d in sorted(ds, key=_ref):
            ly_do = [f"CODE_MISSING_{phia}" if d.ma_hang is None else f"CODE_EMPTY_{phia}"]
            out.append(_muc("UNMATCHED_NO_CODE", d.ma_hang, ly_do, None, [d] if phia == "M2" else [], [d] if phia == "M5" else []))
    return out


def _snapshot(v, phia: str) -> tuple:
    if not isinstance(v, (tuple, list)):
        _loi("DOI_CHIEU_KIEU", f"{phia} phải là tuple/list HoaDonDoiChieu.", phia)
    out = tuple(v)
    da_thay: set[str] = set()
    for i, h in enumerate(out):
        if not isinstance(h, HoaDonDoiChieu):
            _loi("DOI_CHIEU_KIEU", f"{phia}[{i}] phải là HoaDonDoiChieu.", f"{phia}[{i}]")
        if h.ma_ban_ghi in da_thay:
            _loi("DOI_CHIEU_MA_BAN_GHI_TRUNG", f"ma_ban_ghi '{h.ma_ban_ghi}' trùng trong phía {phia} (replay không phải hóa đơn trùng).",
                 f"{phia}[{i}]")
        da_thay.add(h.ma_ban_ghi)
    return out


def doi_chieu_hoa_don(m2, m5) -> dict:
    """Báo cáo đối chiếu M2 ↔ M5 (JSON-safe, xác định). Cấu trúc và ý nghĩa counts: docs/BAO-CAO-DOI-CHIEU-HOA-DON-PURE-01.md §3.

    - Khóa chỉ một phía: MISSING_IN_M5 / EXCESS_IN_M5. ≥2 ma_ban_ghi khác cùng khóa ở một phía: DUPLICATE (giữ mọi bản ghi, không so dòng).
    - Khóa None: `chua_xac_dinh` riêng, không ghép None với nhau, không tính thiếu/thừa.
    - Dòng chỉ so khi khóa PAIRED (đúng một bản ghi mỗi phía); delta = M5 − M2 exact."""
    hd2, hd5 = _snapshot(m2, "m2"), _snapshot(m5, "m5")

    def nhom(ds):
        theo: dict[tuple, list] = {}
        chua: list = []
        for h in ds:
            if h.khoa_hoa_don is None:
                chua.append(h)
            else:
                theo.setdefault(h.khoa_hoa_don, []).append(h)
        return theo, chua

    theo2, chua2 = nhom(hd2)
    theo5, chua5 = nhom(hd5)
    ma = lambda h: h.ma_ban_ghi  # noqa: E731

    hoa_don = []
    dem_khoa = {s: 0 for s in TRANG_THAI_HOA_DON}
    dem_trung = {"M2_ONLY": 0, "M5_ONLY": 0, "BOTH": 0}
    da_xet = {"M2": 0, "M5": 0}
    for k in sorted(set(theo2) | set(theo5)):
        a, b = sorted(theo2.get(k, []), key=ma), sorted(theo5.get(k, []), key=ma)
        trung = (["M2"] if len(a) > 1 else []) + (["M5"] if len(b) > 1 else [])
        dong: list = []
        if trung:
            st = "DUPLICATE"
            ly_do = ([f"DUPLICATE_{p}" for p in trung] + (["ABSENT_M2"] if not a else []) + (["ABSENT_M5"] if not b else [])
                     + ["LINES_NOT_COMPARED"])
            dem_trung["BOTH" if len(trung) == 2 else f"{trung[0]}_ONLY"] += 1
        elif not b:
            st, ly_do = "MISSING_IN_M5", ["ABSENT_M5"]
        elif not a:
            st, ly_do = "EXCESS_IN_M5", ["ABSENT_M2"]
        else:
            st, ly_do = "PAIRED", []
            dong = _so_dong(a[0], b[0])
            da_xet["M2"] += len(a[0].dong)
            da_xet["M5"] += len(b[0].dong)
        dem_khoa[st] += 1
        hoa_don.append({"khoa": list(k), "trang_thai": st, "ly_do": ly_do, "trung_phia": trung,
                        "m2": [_ra_ban_ghi(h) for h in a], "m5": [_ra_ban_ghi(h) for h in b], "dong": dong})

    chua_xac_dinh = [{"phia": phia, "khoa": None, "trang_thai": "UNRESOLVED_KEY", "ly_do": ["INVOICE_KEY_NULL"], "ban_ghi": _ra_ban_ghi(h)}
                     for phia, ds in (("M2", chua2), ("M5", chua5)) for h in sorted(ds, key=ma)]

    dem_dong = {s: 0 for s in TRANG_THAI_DONG}
    mo_ho = {"M2": 0, "M5": 0}
    for e in hoa_don:
        for d in e["dong"]:
            dem_dong[d["trang_thai"]] += 1
            if d["trang_thai"] == "AMBIGUOUS":
                mo_ho["M2"] += len(d["m2"])
                mo_ho["M5"] += len(d["m5"])
    tong2, tong5 = sum(len(h.dong) for h in hd2), sum(len(h.dong) for h in hd5)

    out = {
        "contract": CONTRACT,
        "delta_basis": DELTA_BASIS,
        "tom_tat": {
            "ban_ghi": {"m2": len(hd2), "m5": len(hd5), "m2_khoa_null": len(chua2), "m5_khoa_null": len(chua5)},
            "khoa_hoa_don": {"tong": len(hoa_don), **dem_khoa},
            "khoa_trung_theo_phia": dem_trung,
            "muc_dong": {"tong": sum(dem_dong.values()), **dem_dong},
            "dong_nguon": {"m2_da_xet": da_xet["M2"], "m5_da_xet": da_xet["M5"], "m2_khong_xet": tong2 - da_xet["M2"],
                           "m5_khong_xet": tong5 - da_xet["M5"], "m2_trong_nhom_mo_ho": mo_ho["M2"], "m5_trong_nhom_mo_ho": mo_ho["M5"]},
        },
        "hoa_don": hoa_don,
        "chua_xac_dinh": chua_xac_dinh,
    }
    canonical_json(out)  # chốt JSON-safe (allow_nan=False); lỗi kiểu ở đây là lỗi lập trình, không nuốt
    return out
