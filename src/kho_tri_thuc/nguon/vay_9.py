"""K1 · M9 — đọc nguồn #9 Theo dõi khoản vay theo profile ĐÃ PIN (không gọi app/Google, không load/ensureSheet/export mutation).

Hai profile (proposal revision2 §1.1, §6; binding §3):
  * `VAY_DEPLOY_20260922_NATIVE_JSON_V6` — JSON native `exportJSON` của UI deploy v6: đủ 16 key; tám section nghiệp vụ đọc theo TÊN cột
    (header set pin `3d4d00…`), sáu key phụ chỉ giữ raw. Không tự thêm section rỗng; thiếu key → PARTIAL; key/version lạ → REJECTED;
    một section thiếu cột bắt buộc của profile (vd lịch gốc không có maKheUoc như bản root) → REJECTED `HEADER_KHONG_KHOP_PROFILE`.
  * `M9_BANG_LAI_XAC_NHAN_DEMO_V1` — bảng lãi/phí kỳ ĐÃ XÁC NHẬN dạng DEMO (giả định kỹ thuật, không phải nguồn Google bảo đảm):
    LAI/PHI theo HĐ/khế ước/kỳ/khoảng ngày/số tiền text exact/giấy báo. Không tính lãi từ lãi suất.
Precision contract theo field (DEMO, khai báo rõ): text exact → PROVEN; số JSON nguyên |x| ≤ 2^53−1 → PROVEN; số thập phân ≤ 15 chữ số có
nghĩa (đi vòng IEEE double vẫn giữ) → PROVEN; vượt → UNPROVEN (không phục hồi chữ số bằng Decimal). Boolean/NaN/khóa lặp/sai scale → lỗi.
Không suy currency, ngày, công ty hay khế ước từ tên/thứ tự dòng; con thiếu công ty resolve qua cha DUY NHẤT trong cùng snapshot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from ..ha_tang.primitives import DataError, canonical_json, sha256
from .review_xay_dung import chuan_hoa_so, doc_json_chinh_xac

SAFE_INT = 2 ** 53 - 1
INT64 = 2 ** 63 - 1
TIEN_TE_SCALE = {"VND": 0, "USD": 2}  # bản sao kiểm của registry master.don_vi_tien (DEMO_FIXTURE_CONTRACT); service đối chiếu DB

HEADER_TEXT = """DaiHan|anHan|congTy|duAn|duNoSaoKe|ghiChu|hanMuc|kyHan|maKV|nganHang|ngaySaoKe|nhom|quyUocTinhLai|soHD|tienTe|trangThai|tsdb|updatedAt|updatedBy
HanMucTinDung|congTy|ghiChu|hanMucDuocCap|hieuLucDen|hieuLucTu|id|loaiHanMuc|nganHang|updatedAt|updatedBy
HopDongMua|congTyMua|donGia|duAn|eta|etd|ghiChu|hinhThucVay|id|loaiHD|loaiHang|maHDM|maHDTDLienKet|maHang|nganHang|ngayHD|ngayNhanHang|ngayThanhToan|nhaCungCap|paymentTerm|soHD|soHoaDon|soLuong|soToKhai|tenHang|tienTe|triGia|triGiaNT|tyGia|updatedAt|updatedBy|xuatXu
KheUoc|ghiChu|maKV|maKheUoc|ngayGiaiNgan|soTien|updatedAt|updatedBy
LichLaiSuat|apDungTuNgay|ghiChu|laiSuat|maKheUoc
LichTraGoc|ghiChu|kySo|maKV|maKheUoc|ngayDenHan|soTienGoc
PhatSinh|ghiChu|id|maKV|maKheUoc|ngay|phi|soChungTu|traGoc|traLai|updatedAt|updatedBy
VayNganHan|chiTiet|congTy|ghiChu|id|kyHan|laiSuat|maLienKet|nganHang|ngayDenHan|ngayMoLC|ngayNhanNo|ngayTraNoThucTe|nhaCungCap|quyUocTinhLai|soDaTra|soHoaDon|soLC|soNguyenTe|soNhanNo|soToKhai|soVay|tenHang|tienTe|trangThai|trangThaiHang|tyGia|updatedAt|updatedBy
"""
HEADER_SET_SHA256 = "3d4d006a8c0bb459288ced136f204a8b5937d05cbef5aa393e5ee33a37a02967"
HEADERS = {line.split("|")[0]: frozenset(line.split("|")[1:]) for line in HEADER_TEXT.strip().split("\n")}
NATIVE_KEYS = ("version", "exportedAt", "seqS", "seqL", "shortLoans", "longLoans", "kheUoc", "lichGoc", "laiSuat", "phatSinh", "hopDongMua", "vayNH",
               "hanMuc", "rates", "bankCfg", "manualRows")
SECTION_SHEET = {"longLoans": "DaiHan", "kheUoc": "KheUoc", "lichGoc": "LichTraGoc", "laiSuat": "LichLaiSuat", "phatSinh": "PhatSinh",
                 "hopDongMua": "HopDongMua", "vayNH": "VayNganHan", "hanMuc": "HanMucTinDung"}
BAT_BUOC = {"DaiHan": {"maKV", "congTy", "tienTe"}, "KheUoc": {"maKV", "maKheUoc"}, "LichTraGoc": {"maKV", "maKheUoc", "kySo"},
            "LichLaiSuat": {"maKheUoc", "apDungTuNgay", "laiSuat"}, "PhatSinh": {"id", "maKV"}, "VayNganHan": {"id", "congTy"},
            "HopDongMua": {"id"}, "HanMucTinDung": {"id"}}

PRECISION_CONTRACT = {"id": "DEMO_M9_PRECISION_V1", "version": "1",
                      "rules": "EXACT_TEXT→PROVEN; JSON int |x|≤2^53−1→PROVEN; JSON decimal ≤15 chữ số có nghĩa→PROVEN; còn lại UNPROVEN; scale theo currency"}
PROFILE_NATIVE = {"code": "VAY_DEPLOY_20260922_NATIVE_JSON_V6", "version": "1", "transport": "NATIVE_JSON_EXPORT",
                  "source_code_sha256": "593d6ba8efce4a301a3f42ad2b2c2936ed90119ccfdc8375e11fd3a85768d8f4",
                  "ui_sha256": "767f1f17680633564681ba3fdafd1aba4decc7e9406bc696a30dcfab2495e6b7", "header_set_sha256": HEADER_SET_SHA256,
                  "keys": list(NATIVE_KEYS), "sections": SECTION_SHEET, "precision_contract": PRECISION_CONTRACT}
PROFILE_BANG_LAI = {"code": "M9_BANG_LAI_XAC_NHAN_DEMO_V1", "version": "1", "transport": "DEMO_JSON", "format": "ktt-bang-lai-demo-v1",
                    "gia_dinh": "DEMO: bảng lãi/phí kỳ đã xác nhận do fixture khai báo — không phải nguồn Google, không tính lãi",
                    "precision_contract": PRECISION_CONTRACT}


def profile_sha256(profile: dict) -> str:
    return sha256(canonical_json(profile).encode())


PROFILES = {p["code"]: p for p in (PROFILE_NATIVE, PROFILE_BANG_LAI)}


# ------------------------------------------------------------------ giá trị typed
@dataclass
class GiaTri:
    value: Any
    precision: str | None = None  # PROVEN / UNPROVEN / None (NULL)
    loi: str | None = None


def _text(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (str, int, Decimal)):
        return None
    s = str(v).strip()
    return s or None


def tien(v, currency: str | None) -> GiaTri:
    """Số tiền → minor int64 theo scale của currency. NULL/blank → NULL (không 0)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return GiaTri(None)
    if isinstance(v, bool):
        return GiaTri(None, None, "BOOLEAN_KHONG_PHAI_SO")
    if currency not in TIEN_TE_SCALE:
        return GiaTri(None, None, "TIEN_TE_KHONG_HO_TRO" if currency else "THIEU_TIEN_TE")
    scale = TIEN_TE_SCALE[currency]
    if isinstance(v, str):
        # text exact: chỉ chữ số, dấu chấm thập phân tối đa `scale` chữ số; "1.000"/"1,000" với VND là phân cách mơ hồ → lỗi, không đoán locale
        if not re.fullmatch(r"-?\d+" + (rf"(\.\d{{1,{scale}}})?" if scale else ""), v.strip()):
            return GiaTri(None, None, "SO_TEXT_PHAN_CACH_MO_HO")
        d, exact, ok = Decimal(v.strip()), True, True
    elif isinstance(v, (int, Decimal)):
        d, exact, ok = Decimal(v), False, Decimal(v).is_finite()
    else:
        return GiaTri(None, None, "KIEU_SO_SAI")
    if not ok:
        return GiaTri(None, None, "SO_KHONG_HUU_HAN")
    minor = d.scaleb(scale)
    if minor != minor.to_integral_value():
        return GiaTri(None, None, "SAI_SCALE")
    m = int(minor)
    if abs(m) > INT64:
        return GiaTri(None, None, "VUOT_INT64")
    if exact:
        return GiaTri(m, "PROVEN")
    if isinstance(v, int):
        return GiaTri(m, "PROVEN" if abs(v) <= SAFE_INT else "UNPROVEN")
    sig = len(d.normalize().as_tuple().digits)
    return GiaTri(m, "PROVEN" if sig <= 15 else "UNPROVEN")


def ty_le(v) -> GiaTri:
    if v is None or (isinstance(v, str) and not v.strip()):
        return GiaTri(None)
    if isinstance(v, bool):
        return GiaTri(None, None, "BOOLEAN_KHONG_PHAI_SO")
    try:
        d = Decimal(v.strip()) if isinstance(v, str) else Decimal(v)
    except (InvalidOperation, TypeError):
        return GiaTri(None, None, "SO_KHONG_DOC_DUOC")
    if not d.is_finite() or d < 0 or d >= 1000:
        return GiaTri(None, None, "LAI_SUAT_NGOAI_MIEN")
    prec = "PROVEN" if isinstance(v, str) or len(d.normalize().as_tuple().digits) <= 15 else "UNPROVEN"
    return GiaTri(d, prec)


def ty_gia(v) -> GiaTri:
    """Tỷ giá nguồn: số dương hữu hạn, giữ nguyên làm metadata — không dùng để quy đổi/ghi sổ (chưa có chính sách FX)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return GiaTri(None)
    if isinstance(v, bool):
        return GiaTri(None, None, "BOOLEAN_KHONG_PHAI_SO")
    try:
        d = Decimal(v.strip()) if isinstance(v, str) else Decimal(v)
    except (InvalidOperation, TypeError):
        return GiaTri(None, None, "SO_KHONG_DOC_DUOC")
    if not d.is_finite() or d <= 0:
        return GiaTri(None, None, "TY_GIA_NGOAI_MIEN")
    return GiaTri(d, "PROVEN" if isinstance(v, str) or len(d.normalize().as_tuple().digits) <= 15 else "UNPROVEN")


def ngay(v) -> GiaTri:
    if v is None or (isinstance(v, str) and not v.strip()):
        return GiaTri(None)
    if not isinstance(v, str):
        return GiaTri(None, None, "NGAY_KHONG_PHAI_CHUOI")
    try:
        return GiaTri(date.fromisoformat(v.strip()[:10]) if len(v.strip()) == 10 else None, "PROVEN", None if len(v.strip()) == 10 else "NGAY_SAI_DINH_DANG")
    except ValueError:
        return GiaTri(None, None, "NGAY_SAI_DINH_DANG")


def so_nguyen_duong(v) -> GiaTri:
    if isinstance(v, bool) or v is None:
        return GiaTri(None, None, "KY_KHONG_HOP_LE")
    try:
        d = Decimal(str(v).strip())
    except InvalidOperation:
        return GiaTri(None, None, "KY_KHONG_HOP_LE")
    if d != d.to_integral_value() or d <= 0:
        return GiaTri(None, None, "KY_KHONG_HOP_LE")
    return GiaTri(int(d), "PROVEN")


# ------------------------------------------------------------------ snapshot
@dataclass
class Dong:
    section: str
    locator: str
    raw: dict
    source_key: str | None
    company_key: str | None = None
    state: str = "HOP_LE"
    error: str | None = None

    @property
    def raw_sha256(self) -> str:
        return sha256(canonical_json(chuan_hoa_so(self.raw)).encode())

    def as_payload(self) -> dict:
        return {"section": self.section, "locator": self.locator, "source_company_key": self.company_key, "source_key": self.source_key,
                "row_raw": chuan_hoa_so(self.raw), "row_raw_sha256": self.raw_sha256, "validation_state": self.state, "error_code": self.error}


@dataclass
class AnhChup:
    profile: dict
    state: str
    coverage_kind: str
    loi: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    exported_at: str | None = None
    coverage_manifest: dict = field(default_factory=dict)

    @property
    def typed_sha256(self) -> str:
        return sha256(canonical_json([r.as_payload() for r in self.rows]).encode())


def _key(sheet, r) -> str | None:
    if sheet == "DaiHan":
        return _text(r.get("maKV"))
    if sheet in ("KheUoc",):
        return f"{_text(r.get('maKV'))}/{_text(r.get('maKheUoc'))}"
    if sheet == "LichTraGoc":
        return f"{_text(r.get('maKV'))}/{_text(r.get('maKheUoc')) or ''}/{_text(r.get('kySo'))}"
    if sheet == "LichLaiSuat":
        return f"{_text(r.get('maKheUoc'))}/{_text(r.get('apDungTuNgay'))}"
    return _text(r.get("id"))


def doc_native(raw: bytes) -> AnhChup:
    try:
        value = doc_json_chinh_xac(raw)
    except DataError as exc:
        return AnhChup(PROFILE_NATIVE, "REJECTED", "NONE", [exc.code])
    if not isinstance(value, dict):
        return AnhChup(PROFILE_NATIVE, "REJECTED", "NONE", ["SHAPE_KHONG_PHAI_OBJECT"])
    la, thieu = sorted(set(value) - set(NATIVE_KEYS)), [k for k in NATIVE_KEYS if k not in value]
    if la:
        return AnhChup(PROFILE_NATIVE, "REJECTED", "NONE", ["KEY_LA:" + ",".join(la)])
    if value.get("version") != 6:
        return AnhChup(PROFILE_NATIVE, "REJECTED", "NONE", ["VERSION_KHONG_HO_TRO"])
    snap = AnhChup(PROFILE_NATIVE, "VALIDATED" if not thieu else "PARTIAL", "FULL_SHAPE" if not thieu else "PARTIAL",
                   ["THIEU_KEY:" + ",".join(thieu)] if thieu else [], exported_at=_text(value.get("exportedAt")),
                   coverage_manifest={"keys_co": sorted(set(value) & set(NATIVE_KEYS)), "keys_thieu": thieu,
                                      "so_dong": {s: len(value.get(s) or []) for s in SECTION_SHEET if isinstance(value.get(s), list)}})
    for section, sheet in SECTION_SHEET.items():
        rows = value.get(section)
        if rows is None:
            continue
        if not isinstance(rows, list):
            snap.state, snap.loi = "REJECTED", snap.loi + [f"SECTION_KHONG_PHAI_MANG:{section}"]
            continue
        for i, r in enumerate(rows):
            if not isinstance(r, dict):
                snap.state, snap.loi = "REJECTED", snap.loi + [f"DONG_KHONG_PHAI_OBJECT:{sheet}"]
                continue
            if set(r) - HEADERS[sheet]:
                snap.state, snap.loi = "REJECTED", snap.loi + [f"HEADER_KHONG_KHOP_PROFILE:{sheet}:" + ",".join(sorted(set(r) - HEADERS[sheet]))]
            if BAT_BUOC[sheet] - set(r):
                snap.state, snap.loi = "REJECTED", snap.loi + [f"HEADER_KHONG_KHOP_PROFILE:{sheet}:thieu " + ",".join(sorted(BAT_BUOC[sheet] - set(r)))]
            snap.rows.append(Dong(sheet, f"{section}[{i}]", r, _key(sheet, r)))
    snap.loi = sorted(set(snap.loi))
    _gan_cong_ty(snap)
    _danh_dau_trung(snap)
    return snap


def doc_bang_lai(raw: bytes) -> AnhChup:
    try:
        value = doc_json_chinh_xac(raw)
    except DataError as exc:
        return AnhChup(PROFILE_BANG_LAI, "REJECTED", "NONE", [exc.code])
    if not isinstance(value, dict) or value.get("format") != PROFILE_BANG_LAI["format"] or value.get("demo") is not True or not isinstance(value.get("rows"), list) \
            or set(value) - {"format", "demo", "exportedAt", "rows"}:
        return AnhChup(PROFILE_BANG_LAI, "REJECTED", "NONE", ["SHAPE_BANG_LAI_KHONG_HO_TRO"])
    snap = AnhChup(PROFILE_BANG_LAI, "VALIDATED", "FULL_SHAPE", exported_at=_text(value.get("exportedAt")),
                   coverage_manifest={"so_dong": len(value["rows"])})
    cot = {"id", "congTy", "maKV", "maKheUoc", "ky", "tuNgay", "denNgay", "cauPhan", "soTien", "tienTe", "soGiayBao"}
    for i, r in enumerate(value["rows"]):
        if not isinstance(r, dict) or set(r) != cot:
            snap.state, snap.loi = "REJECTED", snap.loi + ["HEADER_KHONG_KHOP_PROFILE:BangLai"]
            continue
        d = Dong("BangLai", f"rows[{i}]", r, _text(r.get("id")), _text(r.get("congTy")))
        snap.rows.append(d)
    _danh_dau_trung(snap)
    return snap


def doc(profile_code: str, raw: bytes) -> AnhChup:
    if profile_code == PROFILE_NATIVE["code"]:
        return doc_native(raw)
    if profile_code == PROFILE_BANG_LAI["code"]:
        return doc_bang_lai(raw)
    raise DataError("M9_PROFILE_KHONG_HO_TRO", "Profile nguồn khoản vay chưa được pin.")


def _gan_cong_ty(snap: AnhChup) -> None:
    """Công ty nguồn: DaiHan/VayNganHan/HĐ mua/hạn mức ghi trực tiếp; con resolve qua cha DUY NHẤT trong cùng snapshot."""
    kv_cty: dict[str, set] = {}
    for r in snap.rows:
        if r.section == "DaiHan":
            r.company_key = _text(r.raw.get("congTy"))
            kv_cty.setdefault(_text(r.raw.get("maKV")) or "", set()).add(r.company_key)
        elif r.section in ("VayNganHan", "HanMucTinDung"):
            r.company_key = _text(r.raw.get("congTy"))
        elif r.section == "HopDongMua":
            r.company_key = _text(r.raw.get("congTyMua"))
    ku_cha: dict[str, set] = {}
    for r in snap.rows:
        if r.section in ("KheUoc", "LichTraGoc", "PhatSinh"):
            cty = kv_cty.get(_text(r.raw.get("maKV")) or "")
            if not cty:
                r.state, r.error = "LOI", "MO_COI_KHONG_CO_HOP_DONG_CHA"
            elif len(cty) > 1:
                r.state, r.error = "MO_HO", "AMBIGUOUS_COMPANY"
            else:
                r.company_key = next(iter(cty))
            if r.section == "KheUoc" and r.company_key:
                ku_cha.setdefault(_text(r.raw.get("maKheUoc")) or "", set()).add((r.company_key, _text(r.raw.get("maKV"))))
    for r in snap.rows:
        if r.section == "LichLaiSuat":
            cha = ku_cha.get(_text(r.raw.get("maKheUoc")) or "")
            if not cha:
                r.state, r.error = "LOI", "MO_COI_KHONG_CO_KHE_UOC"
            elif len(cha) > 1:
                r.state, r.error = "MO_HO", "AMBIGUOUS_RATE_PARENT"
            else:
                r.company_key = next(iter(cha))[0]
        if r.company_key is None and r.state == "HOP_LE":
            r.state, r.error = "LOI", "THIEU_CONG_TY_NGUON"


def _danh_dau_trung(snap: AnhChup) -> None:
    """Cùng section + khóa: cùng payload → một logical candidate (dòng sau là bằng chứng trùng); khác payload → cả hai XUNG_DOT."""
    nhom: dict[tuple, list] = {}
    for r in snap.rows:
        if r.source_key:
            nhom.setdefault((r.section, r.company_key, r.source_key), []).append(r)
    for rows in nhom.values():
        if len({r.raw_sha256 for r in rows}) > 1:
            for r in rows:
                if r.state == "HOP_LE":
                    r.state, r.error = "XUNG_DOT", "TRUNG_KHOA_KHAC_NOI_DUNG"


# ------------------------------------------------------------------ đồ thị typed theo alias (cho một pháp nhân, các dòng đã map)
def _p(*vals: GiaTri) -> str:
    ps = [v.precision for v in vals if v.value is not None]
    return "UNPROVEN" if "UNPROVEN" in ps else "PROVEN"


def do_thi(native: AnhChup, bang_lai: AnhChup | None, cong_ty_cua_pn: set[str]) -> dict[tuple, dict]:
    """{(section, company, key): graph}. Chỉ dùng dòng HOP_LE của công ty đã map vào PN; dòng lỗi/xung đột được liệt kê làm blocker."""
    rows = [r for r in native.rows if r.company_key in cong_ty_cua_pn]
    out: dict[tuple, dict] = {}
    for r in rows:
        if r.section == "DaiHan" and r.state == "HOP_LE":
            cur = _text(r.raw.get("tienTe"))
            hm, dn, nsk = tien(r.raw.get("hanMuc"), cur), tien(r.raw.get("duNoSaoKe"), cur), ngay(r.raw.get("ngaySaoKe"))
            loi = [x.loi for x in (hm, dn, nsk) if x.loi]
            out[("DaiHan", r.company_key, r.source_key)] = {
                "row": r, "kind": "LONG_TERM", "currency": cur if cur in TIEN_TE_SCALE else None, "loi_dong": loi,
                "facts": {"so_hop_dong_nguon": _text(r.raw.get("soHD")), "han_muc_minor": hm.value, "du_no_nguon_minor": dn.value,
                          "ngay_du_no_nguon": nsk.value, "ky_han_nguon": _text(r.raw.get("kyHan")), "an_han_nguon": _text(r.raw.get("anHan")),
                          "quy_uoc_lai_nguon": _text(r.raw.get("quyUocTinhLai")), "source_status": _text(r.raw.get("trangThai"))},
                "ngan_hang": _text(r.raw.get("nganHang")), "du_an": _text(r.raw.get("duAn")), "precision": _p(hm, dn),
                "draws": {}, "rates": [], "lich": [], "events": [], "blockers": set(loi) | ({"TIEN_TE_KHONG_HO_TRO"} if cur not in TIEN_TE_SCALE else set())}
        elif r.section == "VayNganHan" and r.state == "HOP_LE":
            cur = _text(r.raw.get("tienTe"))
            vnd, tra = tien(r.raw.get("soVay"), "VND"), tien(r.raw.get("soDaTra"), "VND")
            nt = tien(r.raw.get("soNguyenTe"), cur) if cur else GiaTri(None)
            fx = ty_gia(r.raw.get("tyGia"))
            st = _text(r.raw.get("trangThai")) or ""
            kind = "LC" if "LC" in st.upper() and not _text(r.raw.get("ngayNhanNo")) else "SHORT_TERM"
            dates = {k: ngay(r.raw.get(s)) for k, s in (("ngay_mo_lc", "ngayMoLC"), ("ngay_nhan_no", "ngayNhanNo"), ("ngay_den_han", "ngayDenHan"),
                                                       ("ngay_tra_no_thuc_te", "ngayTraNoThucTe"))}
            loi = [x.loi for x in (vnd, tra, nt, fx, *dates.values()) if x.loi]
            out[("VayNganHan", r.company_key, r.source_key)] = {
                "row": r, "kind": kind, "currency": "VND", "loi_dong": loi,
                "facts": {"so_nhan_no": _text(r.raw.get("soNhanNo")), "so_lc": _text(r.raw.get("soLC")), **{k: v.value for k, v in dates.items()},
                          "so_vay_vnd_minor": vnd.value, "so_da_tra_vnd_minor": tra.value, "so_nguyen_te_minor": nt.value,
                          "nguyen_te_code": cur if nt.value is not None else None, "nguyen_te_scale": TIEN_TE_SCALE.get(cur) if nt.value is not None else None,
                          "source_fx_rate": fx.value, "source_fx_basis": "TY_GIA_NGUON_KHONG_CHINH_SACH" if fx.value is not None else None,
                          "ma_lien_ket_nguon": _text(r.raw.get("maLienKet")), "source_status": st or None, "ky_han_nguon": _text(r.raw.get("kyHan")),
                          "quy_uoc_lai_nguon": _text(r.raw.get("quyUocTinhLai")), "chi_tiet_raw": chuan_hoa_so(r.raw.get("chiTiet")),
                          "so_hop_dong_nguon": _text(r.raw.get("soNhanNo")) or _text(r.raw.get("soLC"))},
                "ngan_hang": _text(r.raw.get("nganHang")), "du_an": None, "precision": _p(vnd, tra, nt, fx), "draws": {}, "rates": [], "lich": [],
                "events": [], "blockers": set(loi)}
    by_kv = {k[2]: g for k, g in out.items() if k[0] == "DaiHan"}
    for r in rows:
        kv = _text(r.raw.get("maKV"))
        g = by_kv.get(kv) if r.section in ("KheUoc", "LichTraGoc", "PhatSinh") else None
        if r.section in ("KheUoc", "LichTraGoc", "PhatSinh", "LichLaiSuat") and r.state != "HOP_LE":
            target = g or next((x for x in out.values() if any(d.get("ma") == _text(r.raw.get("maKheUoc")) for d in x["draws"].values())), None)
            if target is not None:
                target["blockers"].add(f"{r.error}:{r.section}")
            continue
        if g is None:
            continue
        cur = g["currency"]
        if r.section == "KheUoc":
            ma = _text(r.raw.get("maKheUoc"))
            nd, st = ngay(r.raw.get("ngayGiaiNgan")), tien(r.raw.get("soTien"), cur)
            if nd.loi or st.loi:
                g["blockers"].add(f"{nd.loi or st.loi}:KheUoc")
            g["draws"][ma] = {"ma": ma, "row": r, "ngay": nd.value, "so_tien": st.value, "precision": _p(st)}
        elif r.section == "LichTraGoc":
            ma = _text(r.raw.get("maKheUoc"))
            ky, nh, st = so_nguyen_duong(r.raw.get("kySo")), ngay(r.raw.get("ngayDenHan")), tien(r.raw.get("soTienGoc"), cur)
            if ky.loi or nh.loi or st.loi:
                g["blockers"].add(f"{ky.loi or nh.loi or st.loi}:LichTraGoc")
                continue
            scope = "DRAW" if ma else "LOAN"
            g["lich"].append({"row": r, "pham_vi": scope, "ma_khe_uoc": ma, "cau_phan": "GOC", "ky": ky.value, "ngay_den_han": nh.value,
                              "period_from": None, "period_to": None, "amount": st.value, "precision": _p(st), "amount_kind": "SOURCE_SCHEDULE",
                              "nghia_vu_key": f"{scope}/{ma or '-'}/{ky.value}/GOC"})
        elif r.section == "PhatSinh":
            if any(e["key"] == r.source_key for e in g["events"]):
                continue  # cùng id + cùng payload (khác payload đã thành XUNG_DOT ở trên): một sự kiện logic, dòng sau chỉ là bằng chứng trùng
            ngd = ngay(r.raw.get("ngay"))
            parts = {c: tien(r.raw.get(s), cur) for c, s in (("GOC", "traGoc"), ("LAI", "traLai"), ("PHI", "phi"))}
            loi = [x.loi for x in (ngd, *parts.values()) if x.loi]
            g["events"].append({"row": r, "key": r.source_key, "ngay": ngd.value, "so_chung_tu": _text(r.raw.get("soChungTu")),
                                "ma_khe_uoc": _text(r.raw.get("maKheUoc")), "parts": {c: (v.value, v.precision or "PROVEN") for c, v in parts.items()},
                                "loi": loi})
    draw_cha = {}
    for g in out.values():
        for ma in g["draws"]:
            draw_cha.setdefault(ma, []).append(g)
    for r in native.rows:  # mốc lãi mơ hồ cha (S16) không có công ty → không lọt theo PN: chặn mọi HĐ có khế ước cùng mã
        if r.section == "LichLaiSuat" and r.state != "HOP_LE" and r.company_key is None:
            for g in draw_cha.get(_text(r.raw.get("maKheUoc")), []):
                g["blockers"].add(f"{r.error}:LichLaiSuat")
    for r in rows:
        if r.section == "LichLaiSuat" and r.state == "HOP_LE":
            cha = draw_cha.get(_text(r.raw.get("maKheUoc")), [])
            if len(cha) != 1:
                continue
            ad, ls = ngay(r.raw.get("apDungTuNgay")), ty_le(r.raw.get("laiSuat"))
            if ad.loi or ls.loi or ad.value is None or ls.value is None:
                cha[0]["blockers"].add(f"{ad.loi or ls.loi or 'LAI_SUAT_THIEU'}:LichLaiSuat")
                continue
            cha[0]["rates"].append({"row": r, "ma": _text(r.raw.get("maKheUoc")), "ap_dung_tu": ad.value, "pct": ls.value, "precision": ls.precision})
    if bang_lai is not None:
        for r in bang_lai.rows:
            if r.company_key not in cong_ty_cua_pn:
                continue
            g = by_kv.get(_text(r.raw.get("maKV")))
            if g is None:
                continue
            if r.state != "HOP_LE":
                g["blockers"].add(f"{r.error}:BangLai")
                continue
            cp, ma = _text(r.raw.get("cauPhan")), _text(r.raw.get("maKheUoc"))
            ky, tu, den = so_nguyen_duong(r.raw.get("ky")), ngay(r.raw.get("tuNgay")), ngay(r.raw.get("denNgay"))
            cur = _text(r.raw.get("tienTe"))
            st = tien(r.raw.get("soTien"), cur)
            bad = ky.loi or tu.loi or den.loi or st.loi or (None if cp in ("LAI", "PHI") else "CAU_PHAN_SAI") or (None if cur == g["currency"] else "KHAC_TIEN_TE_HOP_DONG")
            if bad:
                g["blockers"].add(f"{bad}:BangLai")
                continue
            scope = "DRAW" if ma else "LOAN"
            g["lich"].append({"row": r, "pham_vi": scope, "ma_khe_uoc": ma, "cau_phan": cp, "ky": ky.value, "ngay_den_han": den.value,
                              "period_from": tu.value, "period_to": den.value, "amount": st.value, "precision": st.precision or "PROVEN",
                              "amount_kind": "CONFIRMED_ACCOUNTING_RESULT", "nghia_vu_key": f"{scope}/{ma or '-'}/{ky.value}/{cp}",
                              "so_giay_bao": _text(r.raw.get("soGiayBao"))})
    for g in out.values():
        theo_khoa: dict[str, list] = {}
        for x in g["lich"]:
            theo_khoa.setdefault(x["nghia_vu_key"], []).append(x)
        uniq = []
        for khoa, xs in theo_khoa.items():
            if len({canonical_json({k: (v.isoformat() if isinstance(v, date) else v) for k, v in x.items() if k not in ("row", "so_giay_bao")}) for x in xs}) > 1:
                g["blockers"].add("LICH_TRUNG_KHOA_NGHIA_VU")  # cùng nghĩa vụ, khác nội dung: giữ chờ, không chọn dòng cuối
            uniq.append(xs[0])
        g["lich"] = uniq
        for x in g["lich"]:
            if x["ma_khe_uoc"] and x["ma_khe_uoc"] not in g["draws"]:
                g["blockers"].add("LICH_KHE_UOC_KHONG_CO")
    return out


def noi_dung_typed(g: dict) -> dict:
    """Nội dung typed canonical của một alias (KHÔNG gồm ID dòng/lần fetch) — dùng cho source_revision_sha256 / chống revision giả."""
    def d(v):
        return v.isoformat() if isinstance(v, date) else (str(v) if isinstance(v, Decimal) else v)
    return {"kind": g["kind"], "currency": g["currency"], "facts": {k: d(v) for k, v in sorted(g["facts"].items())},
            "ngan_hang": g["ngan_hang"], "du_an": g["du_an"], "precision": g["precision"], "blockers": sorted(g["blockers"]),
            "draws": [{"ma": x["ma"], "ngay": d(x["ngay"]), "so_tien": x["so_tien"], "p": x["precision"]} for _, x in sorted(g["draws"].items())],
            "rates": sorted([{"ma": x["ma"], "tu": d(x["ap_dung_tu"]), "pct": d(x["pct"]), "p": x["precision"]} for x in g["rates"]],
                            key=lambda r: (r["ma"], r["tu"])),
            "lich": sorted([{k: d(v) for k, v in x.items() if k != "row"} for x in g["lich"]], key=lambda r: r["nghia_vu_key"]),
            "events": sorted([{"key": e["key"], "ngay": d(e["ngay"]), "ct": e["so_chung_tu"], "ma": e["ma_khe_uoc"],
                               "parts": {c: list(v) for c, v in sorted(e["parts"].items())}, "loi": e["loi"]} for e in g["events"]], key=lambda r: r["key"])}
