"""DA-1 — CRM · Dự án đang bán (QD-20261025-05…09): service trên K2 PostgreSQL (M0031, `k2/sql_crm_du_an_ban.py`), dùng lại toàn bộ seam G1/G7
của `CrmMauK2`: danh tính phiên do máy chủ giữ + kết nối CHỦ BẢNG + giao dịch có GUC danh tính, biên nhận idempotent `khoa`, bộ chuẩn G7.

- Dự án đang bán GẮN vào `master.du_an` (danh mục dự án kế toán): bật bán = chọn dự án có sẵn (QD-06), không tạo danh mục dự án thứ hai.
- Thông tin bán hàng có PHIÊN BẢN bất biến: cờ đang bán, vị trí, mô tả, đơn giá niêm yết + tiền tệ, loại hình + thuế mặc định, giai đoạn tiến độ,
  danh sách phí tiêu chuẩn. Sửa = phiên bản mới hiệu lực ngay từ hôm nay (đóng phiên bản cũ + thêm phiên bản mới + nhật ký, cùng giao dịch);
  ngừng bán / mở bán lại = phiên bản mới + sự kiện nhật ký (QD-07). Lô/căn: đổi = dòng lịch sử mới, không ghi đè.
- Tiến độ thanh toán tiêu chuẩn = bộ chuẩn G7; bán hàng áp dụng ngay, bỏ CFO (CAS `expected_version`, căn cứ QD-20261025-07).
- Ảnh chụp mặc định `(dự án, ngày)` cho báo giá (DA-3): `anh_chup_mac_dinh` (giao dịch riêng) / `anh_chup_trong` (trong giao dịch của người gọi).
- Đọc: phiên có module CRM trên pháp nhân. Ghi: bán hàng / kế toán / kế toán trưởng có module CRM trên đúng pháp nhân dự án. Cổng thật ở CSDL.
- Số: chuỗi thập phân chính xác, CHỈ chữ số ASCII, cùng literal với M0030 (`RE_SO` của báo giá); chuẩn hóa dạng gọn ("1.50" → "1.5"), không float.
Trình duyệt không gửi actor/pháp nhân/trạng thái/kết quả; lỗi nhập trả theo trường (`DataError.locator`, HTTP `truong`).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction

from ..ha_tang.primitives import DataError
from .crm_giao_ket import RE_SO, _frac_str, _ngay_vn, _so_vn, danh_muc_moc_chuan
from .crm_mau import GIAI_DOAN_RE, CrmMauK2, _h, _khoa, _ngay, _uuid, _v
from .sql_crm_du_an_ban import CAN_CU_G7

KIEU_ANH_CHUP = "CRM_DA_ANH_CHUP_V1"
TRUONG_TT = ("vi_tri", "mo_ta", "don_gia_niem_yet", "tien_te", "loai_hinh_id", "thue_suat", "gia_dat_tru", "giai_doan_g7")
TRUONG_PHI = ("ten", "loai", "muc", "don_vi_tinh", "tien_te", "co_so_tinh")
TRUONG_LO = ("ma", "dien_tich", "trang_thai", "ghi_chu", "expected_lan")
TIEN_TE = {"VND": "đ", "USD": "USD"}
THUE_SUAT = {"10": "Thuế suất 10%", "8": "Thuế suất 8%", "5": "Thuế suất 5%", "0": "Thuế suất 0%",
             "KCT": "Không chịu thuế", "KKKNT": "Không kê khai, nộp thuế"}
LOAI_PHI = {"BAO_TRI": "Phí bảo trì", "SU_DUNG": "Phí sử dụng", "KHAC": "Phí khác"}
DON_VI_TINH = {"M2_THANG": "m²/tháng", "M2_NAM": "m²/năm", "LAN": "lần"}
TRANG_THAI_LO = {"CON_TRONG": "Còn trống", "GIU_CHO": "Đang giữ chỗ", "DA_BAN": "Đã bán/cho thuê", "KHONG_BAN": "Tạm không bán"}
TRANG_THAI_DA = {"DANG_BAN": "Đang bán", "NGUNG_BAN": "Ngừng bán", "CHUA_BAT_BAN": "Chưa có trong danh mục đang bán",
                 "CHUA_CO_PHIEN_BAN": "Chưa bán vào ngày này"}
NGUON_G7 = {"AP_DUNG_NGAY": "Bán hàng áp dụng ngay (" + CAN_CU_G7 + ")", "CFO_DUYET": "CFO đã duyệt"}
HANH_DONG = {"CRM_DA_BAT_BAN": "Bật bán", "CRM_DA_CAP_NHAT": "Sửa thông tin", "CRM_DA_PHI": "Sửa phí tiêu chuẩn", "CRM_DA_LO": "Cập nhật lô/căn",
             "CRM_DA_NGUNG_BAN": "Ngừng bán", "CRM_DA_MO_BAN_LAI": "Mở bán lại", "CRM_CHUAN_AP_DUNG": "Áp dụng tiến độ thanh toán tiêu chuẩn",
             "CRM_DA_MOC_KHAI": "Khai mốc", "CRM_DA_MOC_CHINH_DU_KIEN": "Chỉnh ngày dự kiến",
             "CRM_DA_MOC_THUC_TE": "Ghi ngày thực tế", "CRM_DA_MOC_SUA": "Sửa mốc"}
TRANG_THAI_MOC = {"DA_XONG": "Đã xong", "CHUA_DEN": "Chưa đến ngày dự kiến", "QUA_DU_KIEN": "Quá ngày dự kiến — cần chỉnh ngày"}
TOI_DA_PHI, TOI_DA_LO = 50, 500


# ================================================================================================== chuẩn hóa dữ liệu nhập (lỗi theo trường)
def _loi(ma: str, msg: str, truong: str = "$"):
    raise DataError(ma, msg, truong)


def _chuoi(v, ten: str, toi_da: int, truong: str, *, nhieu_dong: bool = False):
    """Chuỗi có cắt khoảng trắng hai đầu; rỗng → None. Không ký tự điều khiển (trừ xuống dòng/tab khi `nhieu_dong`), không ngoặc nhọn."""
    if v is None:
        return None
    if not isinstance(v, str):
        _loi("CRM_DA_YEU_CAU_SAI", f"Trường {ten} phải là chuỗi.", truong)
    v = v.strip()
    if not v:
        return None
    cho_phep = "\n\t\r" if nhieu_dong else ""
    if len(v) > toi_da or any((ord(c) < 32 or 0x7F <= ord(c) <= 0x9F) and c not in cho_phep for c in v) or "{" in v or "}" in v:
        _loi("CRM_DA_YEU_CAU_SAI", f"Trường {ten} không hợp lệ (chuỗi ≤ {toi_da} ký tự, không ký tự điều khiển/ngoặc nhọn).", truong)
    return v


def _so(v, ten: str, truong: str, *, duong: bool = False, toi_da: int | None = None):
    """Số thập phân không âm dạng chuỗi (chữ số ASCII 0–9, dấu chấm thập phân, ≤ 24 chữ số nguyên/12 chữ số lẻ — literal M0030); trả dạng gọn."""
    if v is None or v == "":
        return None
    if not isinstance(v, str) or not RE_SO.fullmatch(v):
        _loi("CRM_DA_SO_SAI", f"{ten} phải là số thập phân không âm dạng chuỗi (chữ số 0–9, dấu chấm thập phân, ≤ 24 chữ số nguyên/12 chữ số lẻ).",
             truong)
    d = Decimal(v)
    if duong and d <= 0:
        _loi("CRM_DA_SO_SAI", f"{ten} phải lớn hơn 0.", truong)
    if toi_da is not None and d > toi_da:
        _loi("CRM_DA_SO_SAI", f"{ten} tối đa {toi_da}.", truong)
    return _frac_str(Fraction(d))


def _chon(v, ten: str, cho_phep, truong: str):
    if v is None or v == "":
        return None
    if v not in cho_phep:
        _loi("CRM_DA_YEU_CAU_SAI", f"Trường {ten} chỉ nhận: {', '.join(cho_phep)}.", truong)
    return v


def _uuid_t(v, ten: str, truong: str) -> str:
    try:
        return _uuid(v, ten)
    except DataError as exc:
        raise DataError("CRM_DA_YEU_CAU_SAI", str(exc), truong) from None


def _so_nguyen(v, ten: str, truong: str = "$", *, bat_buoc: bool = True):
    if v is None and not bat_buoc:
        return None
    if type(v) is not int or not 1 <= v <= 999_999_999:
        _loi("CRM_DA_YEU_CAU_SAI", f"Trường {ten} phải là số nguyên dương.", truong)
    return v


def chuan_hoa_thong_tin(v, truong: str = "thong_tin", *, bat_ban: bool = False) -> dict:
    """Chỉ chuẩn hóa trường được gửi; bật bán mới mặc định thuế 10, đất trừ/m² 0 (QD-20261025-20).
    Cập nhật giữ trường vắng mặt để SQL ghép với phiên bản hiện hành sau CAS rồi kiểm toàn bộ nội dung.
    """
    if not isinstance(v, dict):
        _loi("CRM_DA_YEU_CAU_SAI", "Thông tin dự án phải là object.", truong)
    la = sorted(set(v) - set(TRUONG_TT))
    if la:
        _loi("CRM_DA_YEU_CAU_SAI", "Thông tin dự án có trường ngoài phạm vi: " + ", ".join(la[:5]), f"{truong}.{la[0]}")
    def o(k: str) -> str:
        return f"{truong}.{k}"
    gd = v.get("giai_doan_g7")
    if gd not in (None, "") and (not isinstance(gd, str) or not GIAI_DOAN_RE.fullmatch(gd)):
        _loi("CRM_DA_YEU_CAU_SAI", "Giai đoạn tiến độ chỉ gồm chữ/số/_ . - (1–80).", o("giai_doan_g7"))
    tt = {"vi_tri": _chuoi(v.get("vi_tri"), "vị trí", 500, o("vi_tri")),
          "mo_ta": _chuoi(v.get("mo_ta"), "mô tả", 4000, o("mo_ta"), nhieu_dong=True),
          "don_gia_niem_yet": _so(v.get("don_gia_niem_yet"), "Đơn giá niêm yết", o("don_gia_niem_yet")),
          "tien_te": _chon(v.get("tien_te"), "tiền tệ", tuple(TIEN_TE), o("tien_te")),
          "loai_hinh_id": None if v.get("loai_hinh_id") in (None, "") else _uuid_t(v.get("loai_hinh_id"), "loai_hinh_id", o("loai_hinh_id")),
          "thue_suat": _chon(v.get("thue_suat", "10" if bat_ban else None), "thuế suất", tuple(THUE_SUAT), o("thue_suat")),
          "gia_dat_tru": _so(v.get("gia_dat_tru", "0" if bat_ban else None), "Giá đất được trừ/m²", o("gia_dat_tru")),
          "giai_doan_g7": gd or None}
    if (bat_ban or "thue_suat" in v) and tt["thue_suat"] is None:
        _loi("CRM_DA_YEU_CAU_SAI", "Cần chọn thuế suất trong danh mục.", o("thue_suat"))
    if ((bat_ban or "gia_dat_tru" in v) and tt["gia_dat_tru"] is None) or (
            tt["gia_dat_tru"] is not None and (bat_ban or "don_gia_niem_yet" in v)
            and Decimal(tt["gia_dat_tru"]) > Decimal(tt["don_gia_niem_yet"] or "0")):
        _loi("CRM_DA_SO_SAI", "Giá đất được trừ/m² phải không âm và không vượt đơn giá niêm yết.", o("gia_dat_tru"))
    if (bat_ban or "loai_hinh_id" in v) and tt["loai_hinh_id"] is None:
        _loi("CRM_DA_THIEU_LOAI_HINH", "Cần chọn loại hình của dự án.", o("loai_hinh_id"))
    if (bat_ban or "tien_te" in v) and tt["tien_te"] is None:
        _loi("CRM_DA_TIEN_TE_SAI", "Cần chọn tiền tệ của đơn giá (VND hoặc USD).", o("tien_te"))
    return tt if bat_ban else {k: x for k, x in tt.items() if k in v}


def chuan_hoa_phi(v, truong: str = "phi") -> list[dict]:
    """Danh sách phí tiêu chuẩn (0–50 dòng): tên, loại (bảo trì/sử dụng/khác), mức, đơn vị tính (m²/tháng · m²/năm · lần), tiền tệ, cơ sở tính."""
    if v is None:
        return []
    if not isinstance(v, list) or len(v) > TOI_DA_PHI:
        _loi("CRM_DA_PHI_SAI", f"Danh sách phí tối đa {TOI_DA_PHI} dòng.", truong)
    out, ten = [], set()
    for i, r in enumerate(v):
        o = f"{truong}.{i}"
        if not isinstance(r, dict) or set(r) - set(TRUONG_PHI):
            _loi("CRM_DA_PHI_SAI", f"Phí dòng {i + 1} chỉ gồm tên, loại, mức, đơn vị tính, tiền tệ, cơ sở tính.", o)
        d = {"ten": _chuoi(r.get("ten"), f"tên phí dòng {i + 1}", 200, f"{o}.ten"),
             "loai": _chon(r.get("loai"), f"loại phí dòng {i + 1}", tuple(LOAI_PHI), f"{o}.loai"),
             "muc": _so(r.get("muc"), f"Mức phí dòng {i + 1}", f"{o}.muc"),
             "don_vi_tinh": _chon(r.get("don_vi_tinh"), f"đơn vị tính dòng {i + 1}", tuple(DON_VI_TINH), f"{o}.don_vi_tinh"),
             "tien_te": _chon(r.get("tien_te"), f"tiền tệ phí dòng {i + 1}", tuple(TIEN_TE), f"{o}.tien_te"),
             "co_so_tinh": _chuoi(r.get("co_so_tinh"), f"cơ sở tính dòng {i + 1}", 300, f"{o}.co_so_tinh")}
        for k, nhan in (("ten", "tên phí"), ("loai", "loại phí"), ("muc", "mức phí"), ("don_vi_tinh", "đơn vị tính"), ("tien_te", "tiền tệ")):
            if d[k] is None:
                _loi("CRM_DA_PHI_SAI", f"Phí dòng {i + 1}: thiếu {nhan}.", f"{o}.{k}")
        if d["ten"].lower() in ten:
            _loi("CRM_DA_PHI_SAI", f"Phí dòng {i + 1}: trùng tên phí trong danh sách.", f"{o}.ten")
        ten.add(d["ten"].lower())
        out.append(d)
    return out


def chuan_hoa_lo(v, truong: str = "lo") -> list[dict]:
    """1–500 lô/căn: mã (không trùng, không phân biệt hoa thường), diện tích > 0 (m²), trạng thái, ghi chú; lô đã có cần `expected_lan`."""
    if not isinstance(v, list) or not 1 <= len(v) <= TOI_DA_LO:
        _loi("CRM_DA_LO_SAI", f"Danh sách lô/căn cần 1–{TOI_DA_LO} dòng.", truong)
    out, ma = [], set()
    for i, r in enumerate(v):
        o = f"{truong}.{i}"
        if not isinstance(r, dict) or set(r) - set(TRUONG_LO):
            _loi("CRM_DA_LO_SAI", f"Lô/căn dòng {i + 1} chỉ gồm mã, diện tích, trạng thái, ghi chú, lần mong đợi.", o)
        d = {"ma": _chuoi(r.get("ma"), f"mã lô/căn dòng {i + 1}", 80, f"{o}.ma"),
             "dien_tich": _so(r.get("dien_tich"), f"Diện tích lô/căn dòng {i + 1}", f"{o}.dien_tich", duong=True),
             "trang_thai": _chon(r.get("trang_thai"), f"trạng thái lô/căn dòng {i + 1}", tuple(TRANG_THAI_LO), f"{o}.trang_thai"),
             "ghi_chu": _chuoi(r.get("ghi_chu"), f"ghi chú lô/căn dòng {i + 1}", 1000, f"{o}.ghi_chu", nhieu_dong=True),
             "expected_lan": _so_nguyen(r.get("expected_lan"), f"lần mong đợi dòng {i + 1}", f"{o}.expected_lan", bat_buoc=False)}
        if d["ma"] is None:
            _loi("CRM_DA_LO_SAI", f"Lô/căn dòng {i + 1}: thiếu mã.", f"{o}.ma")
        if d["dien_tich"] is None:
            _loi("CRM_DA_LO_SAI", f"Lô/căn dòng {i + 1}: thiếu diện tích.", f"{o}.dien_tich")
        if d["ma"].upper() in ma:
            _loi("CRM_DA_LO_SAI", f"Lô/căn dòng {i + 1}: trùng mã {d['ma']} trong danh sách.", f"{o}.ma")
        ma.add(d["ma"].upper())
        out.append(d)
    return out


def chuan_hoa_moc(v) -> dict:
    """Giữ trường vắng mặt khi sửa; null tường minh cho phép bỏ tên tắt/ngày thực tế."""
    if not isinstance(v, dict):
        _loi("CRM_DA_MOC_SAI", "Cần thông tin mốc.", "moc")
    la = sorted(set(v) - {"moc_id", "expected_lan", "ten", "ten_tat", "ngay_du_kien", "ngay_thuc_te", "dang_dung"})
    if la:
        _loi("CRM_DA_MOC_SAI", "Mốc có trường ngoài phạm vi.", "moc." + la[0])
    out = dict(v)
    for k, nhan, dai in (("ten", "tên mốc", 120), ("ten_tat", "tên tắt", 20)):
        if k in v:
            out[k] = _chuoi(v[k], nhan, dai, "moc." + k)
    moi = v.get("moc_id") is None
    if (moi or "ten" in v) and not out.get("ten"):
        _loi("CRM_DA_MOC_SAI", "Cần nhập tên mốc.", "moc.ten")
    if not moi:
        out["moc_id"] = _uuid_t(v["moc_id"], "mốc", "moc.moc_id")
        out["expected_lan"] = _so_nguyen(v.get("expected_lan"), "lần mong đợi", "moc.expected_lan")
    elif "expected_lan" in v:
        out["expected_lan"] = _so_nguyen(v["expected_lan"], "lần mong đợi", "moc.expected_lan", bat_buoc=False)
    if "dang_dung" in v and type(v["dang_dung"]) is not bool:
        _loi("CRM_DA_MOC_SAI", "Đang dùng phải là giá trị có/không.", "moc.dang_dung")
    for k in ("ngay_du_kien", "ngay_thuc_te"):
        if k not in v:
            continue
        x = v[k]
        if x is None or x == "":
            out[k] = None
            continue
        try:
            if not isinstance(x, str):
                raise ValueError
            if re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", x):
                out[k] = datetime.strptime(x, "%d/%m/%Y").date().isoformat()
            elif re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", x):
                out[k] = date.fromisoformat(x).isoformat()
            else:
                raise ValueError
        except ValueError:
            _loi("CRM_DA_MOC_NGAY_SAI", "Ngày không hợp lệ; nhập ngày/tháng/năm.", "moc." + k)
    if (moi or "ngay_du_kien" in v) and not out.get("ngay_du_kien"):
        _loi("CRM_DA_MOC_SAI", "Cần nhập ngày dự kiến.", "moc.ngay_du_kien")
    return out


def _ly_do(v, *, bat_buoc: bool = False):
    ly = _chuoi(v, "lý do", 1000, "ly_do", nhieu_dong=True)
    if bat_buoc and not ly:
        _loi("CRM_DA_THIEU_LY_DO", "Cần nhập lý do.", "ly_do")
    return ly


def danh_muc() -> dict:
    """Danh mục chọn có nhãn tiếng Việt cho màn hình (DA-2/DA-3) — mã chỉ để gửi lại máy chủ, không hiển thị."""
    def ds(m):
        return [{"ma": k, "nhan": n} for k, n in m.items()]
    return {"tien_te": ds({"VND": "VND (đ)", "USD": "USD"}), "thue_suat": ds(THUE_SUAT), "loai_phi": ds(LOAI_PHI), "don_vi_tinh": ds(DON_VI_TINH),
            "trang_thai_lo": ds(TRANG_THAI_LO), "trang_thai_du_an": ds({"DANG_BAN": "Đang bán", "NGUNG_BAN": "Ngừng bán"})}


# ================================================================================================== hiển thị (tiếng Việt, tiền có đơn vị, dd/mm/yyyy)
def _tien_don_vi(so: str | None, tt: str | None, don_vi: str) -> str | None:
    if so is None or tt not in TIEN_TE:
        return None
    return f"{_so_vn(so)} {TIEN_TE[tt]}" + (f"/{don_vi}" if don_vi else "")


def hien_thi_anh_chup(s: dict) -> dict:
    """Chuỗi hiển thị cho ảnh chụp (không đưa vào `anh_chup_sha256`)."""
    if not isinstance(s, dict):
        return {}
    out = {"trang_thai": TRANG_THAI_DA.get(s.get("trang_thai")), "ngay": _ngay_vn(s.get("ngay"))}
    pb = s.get("phien_ban")
    if not pb:
        return out
    thue = s.get("thue") or {}
    bc = s.get("bo_chuan") or None
    out.update({
        "phien_ban": f"Phiên bản {pb['so']} — hiệu lực từ {_ngay_vn(pb['hieu_luc_tu'])}" + (f" đến trước {_ngay_vn(pb['hieu_luc_den'])}" if pb.get("hieu_luc_den") else ""),
        "don_gia": _tien_don_vi(s.get("don_gia"), s.get("tien_te"), "m²"),
        "thue": "Giá chưa gồm VAT · " + THUE_SUAT.get(thue.get("thue_suat"), ""),
        "gia_dat_tru": _tien_don_vi(s.get("gia_dat_tru"), s.get("tien_te"), "m²"),
        "loai_hinh": ((s.get("loai_hinh") or {}).get("ten") or "") + ("" if (s.get("loai_hinh") or {}).get("con_hieu_luc", True)
                                                                      else " (loại hình đã có phiên bản mới — cần chọn lại)"),
        "phi": [{"ten": f["ten"], "loai": LOAI_PHI.get(f["loai"]), "muc": _tien_don_vi(f["muc"], f["tien_te"], DON_VI_TINH.get(f["don_vi_tinh"], "")),
                 "co_so_tinh": f.get("co_so_tinh")} for f in s.get("phi") or []],
        "lo": [{"ma": x["ma"], "dien_tich": f"{_so_vn(x['dien_tich'])} m²", "trang_thai": TRANG_THAI_LO.get(x["trang_thai"])} for x in s.get("lo") or []],
        "bo_chuan": None if bc is None else ("Chưa có tiến độ tiêu chuẩn hiệu lực" if bc.get("trang_thai") != "HIEU_LUC" else
                                             f"Giai đoạn {bc.get('giai_doan')} · phiên bản {bc['version']['phien_ban']} · "
                                             f"{NGUON_G7.get(bc.get('nguon'), '')} · hiệu lực từ {_ngay_vn(bc['version']['valid_from'])}"),
    })
    # DTO hiển thị riêng, không sửa rows của ảnh chụp đã có SHA256; không qua float.
    out["bo_chuan_dong"] = []
    for r in (bc or {}).get("rows") or []:
        gia_tri = None
        if r.get("gia_tri_loai") == "PERCENT" and r.get("gia_tri_thap_phan") is not None:
            gia_tri = _so_vn(r["gia_tri_thap_phan"]) + "%"
        elif r.get("gia_tri_loai") == "AMOUNT" and r.get("so_tien_minor") is not None and r.get("tien_te") in TIEN_TE:
            so = _frac_str(Fraction(int(r["so_tien_minor"]), 100 if r["tien_te"] == "USD" else 1))
            gia_tri = _tien_don_vi(so, r["tien_te"], "")
        out["bo_chuan_dong"].append({"gia_tri_hien_thi": gia_tri})
    return out


def _hom_nay_vn() -> date:
    return datetime.now(timezone(timedelta(hours=7))).date()


# ================================================================================================== service
class CrmDuAnBanK2:
    """Danh mục dự án đang bán trên CHÍNH service G1/G7 (`CrmMauK2`): cùng kết nối chủ bảng, cùng giao dịch có danh tính, cùng biên nhận."""

    def __init__(self, mau: CrmMauK2):
        self.mau = mau

    def _hom_nay(self) -> str:
        return self.mau.hom_nay().isoformat()

    # ------------------------------------------------------------------ đọc
    def moc_ds(self, dang_nhap, du_an_id) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        da, ngay = _uuid_t(du_an_id, "dự án", "du_an_id"), self._hom_nay()
        with m._tx(dt, rr=True) as c:
            rows = _v(dict(c.execute("SELECT master.crm_da_moc_doc(%s::uuid, %s::date) AS r", (da, ngay)).fetchone()))["r"]
        ds = [{**r, "ngay_du_kien_hien_thi": _ngay_vn(r.get("ngay_du_kien")),
               "ngay_thuc_te_hien_thi": _ngay_vn(r.get("ngay_thuc_te")),
               "trang_thai_hien_thi": TRANG_THAI_MOC.get(r["trang_thai"]), "viec_cho": r["trang_thai"] == "QUA_DU_KIEN"} for r in rows]
        return {"du_an_id": da, "moc": ds, "so_viec_cho": sum(r["viec_cho"] for r in ds)}

    def moc_lich_su(self, dang_nhap, moc_id) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        mid = _uuid_t(moc_id, "mốc", "moc_id")
        with m._tx(dt, rr=True) as c:
            r = _v(dict(c.execute("SELECT master.crm_da_moc_ls_doc(%s::uuid) AS r", (mid,)).fetchone()))["r"]
        def ht(x):
            return {**x, **{k + "_hien_thi": _ngay_vn(x.get(k)) for k in
                           ("ngay_du_kien", "ngay_thuc_te", "hieu_luc_tu", "hieu_luc_den", "tao_luc")}}
        return {**r, "lich_su": [ht(x) for x in r["lich_su"]], "nhat_ky": [
            {**x, "hanh_dong_hien_thi": HANH_DONG.get(x["hanh_dong"], "Thao tác khác"), "luc_hien_thi": _ngay_vn(x.get("luc")),
             "truoc_hien_thi": ht(x["truoc"]) if x.get("truoc") else None,
             "sau_hien_thi": ht(x["sau"]) if x.get("sau") else None} for x in r["nhat_ky"]]}

    def danh_muc_moc(self, dang_nhap, du_an_id=None) -> dict:
        dm = danh_muc_moc_chuan()
        if du_an_id is None:
            return dm
        for r in self.moc_ds(dang_nhap, du_an_id)["moc"]:
            dm["moc"].append({"ma": r["ma"], "nhan": r["ten"], "ten_tat": r.get("ten_tat"),
                              "du_kien": r["ngay_du_kien"], "thuc_te": r.get("ngay_thuc_te"), "rieng": True})
            dm["moc_tham_so"].append({"mau_ma": r["ma"] + "_<n>", "nhan": r["ten"] + " + n ngày", "tham_so": "n", "toi_thieu": 1})
        return dm

    @staticmethod
    def anh_chup_trong(c, du_an_id: str, ngay: str) -> dict:
        """Ảnh chụp mặc định gọi TRONG giao dịch đang mở của người gọi (kết nối chủ bảng có GUC danh tính phiên — vd lệnh Lưu báo giá DA-3):
        cùng hàm SQL `master.crm_da_anh_chup`, quyền CRM hiện hành kiểm trong hàm. Phía SQL của lệnh lưu có thể gọi lại và so `anh_chup_sha256`."""
        return _v(dict(c.execute("SELECT master.crm_da_anh_chup(%s::uuid, %s::date) AS r", (du_an_id, ngay)).fetchone()))["r"]

    def anh_chup_mac_dinh(self, dang_nhap: str, du_an_id, ngay=None) -> dict:
        """(dự án, ngày) → {kieu, trang_thai, phien_ban, don_gia, tien_te, gia_dat_tru, loai_hinh, thue, giai_doan_g7, phi[], lo[], bo_chuan, giai_doan_co_chuan,
        anh_chup_sha256} theo phiên bản hiệu lực vào ngày đó (mặc định hôm nay) + `hien_thi`. Dự án chưa bật bán → trang_thai CHUA_BAT_BAN."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        da = _uuid(du_an_id, "du_an_id")
        ngay = _ngay(ngay, "Ngày") if ngay else self._hom_nay()
        with m._tx(dt, rr=True) as c:
            s = self.anh_chup_trong(c, da, ngay)
        return {**s, "hien_thi": hien_thi_anh_chup(s)}

    def danh_sach(self, dang_nhap: str, *, dang_ban: bool = False) -> dict:
        """Dự án trong danh mục đang bán (phiên bản hiện hành) theo quyền CRM của phiên; `dang_ban` = chỉ dự án đang bán (danh sách chọn của báo
        giá). Kèm dự án kế toán CHƯA bật bán mà phiên được ghi (để thêm), loại hình hiện hành và danh mục chọn."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt, rr=True) as c:
            ds = m._nhieu(c, """SELECT d.id AS da_ban_id, d.du_an_id, a.ma_junsky AS du_an_ma, a.ten AS du_an_ten, p.ma AS phap_nhan, p.ten AS phap_nhan_ten,
                                       v.id AS phien_ban_id, v.phien_ban, v.hieu_luc_tu, v.dang_ban, v.vi_tri, v.don_gia_niem_yet, v.tien_te,
                                       v.loai_hinh_id, l.ten AS loai_hinh_ten, l.valid_to IS NULL AS loai_hinh_con_hieu_luc, v.thue_suat,
                                       trim_scale(v.gia_dat_tru)::text AS gia_dat_tru,
                                       v.giai_doan_g7, v.so_phi, (SELECT count(*) FROM master.crm_da_ban_lo o WHERE o.da_ban_id = d.id) AS so_lo,
                                       master.crm_da_duoc_ghi(d.phap_nhan_id) AS duoc_sua
                                FROM master.crm_da_ban d JOIN master.du_an a ON a.id = d.du_an_id JOIN master.phap_nhan p ON p.id = d.phap_nhan_id
                                JOIN master.crm_da_ban_phien_ban v ON v.da_ban_id = d.id AND v.hieu_luc_den IS NULL
                                JOIN master.loai_hinh_doanh_thu l ON l.id = v.loai_hinh_id
                                WHERE master.crm_da_duoc_doc(d.phap_nhan_id) AND (v.dang_ban OR NOT %s)
                                ORDER BY p.ma, a.ma_junsky""", (bool(dang_ban),))
            chua = [] if dang_ban else m._nhieu(c, """SELECT a.id AS du_an_id, a.ma_junsky AS du_an_ma, a.ten AS du_an_ten, p.ma AS phap_nhan, p.ten AS phap_nhan_ten
                                                     FROM master.du_an a JOIN master.phap_nhan p ON p.id = a.phap_nhan_id
                                                     WHERE master.crm_da_duoc_ghi(a.phap_nhan_id) AND a.trang_thai <> 'DONG' AND a.valid_to IS NULL
                                                       AND NOT EXISTS (SELECT 1 FROM master.crm_da_ban d WHERE d.du_an_id = a.id)
                                                     ORDER BY p.ma, a.ma_junsky""")
            loai = [] if dang_ban else m._nhieu(c, """SELECT l.id, l.ma, l.ten, l.phien_ban, p.ma AS phap_nhan, l.cau_hinh -> 'tien_te_hop_le' AS tien_te_hop_le
                                                     FROM master.loai_hinh_doanh_thu l JOIN master.phap_nhan p ON p.id = l.phap_nhan_id
                                                     WHERE l.valid_to IS NULL AND master.crm_da_duoc_doc(l.phap_nhan_id) ORDER BY p.ma, l.ma""")
        for r in ds:
            r["trang_thai_hien_thi"] = "Đang bán" if r["dang_ban"] else "Ngừng bán"
            r["hieu_luc_tu_hien_thi"] = _ngay_vn(r["hieu_luc_tu"])
            r["don_gia_hien_thi"] = _tien_don_vi(r["don_gia_niem_yet"], r["tien_te"], "m²")
        return {"nguoi": {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"]}, "chi_dang_ban": bool(dang_ban), "du_an_ban": ds,
                "du_an_chua_ban": chua, "loai_hinh": loai, "danh_muc": danh_muc(), "hom_nay": self._hom_nay(),
                "ghi_nguon": {"san_sang": m.conn_tin_cay is not None}}

    def _da_ban(self, c, da_ban_id: str) -> dict:
        d = self.mau._mot(c, """SELECT d.id, d.du_an_id, d.phap_nhan_id, master.crm_da_duoc_ghi(d.phap_nhan_id) AS duoc_sua FROM master.crm_da_ban d
                                WHERE d.id = %s::uuid AND master.crm_da_duoc_doc(d.phap_nhan_id)""", (da_ban_id,))
        if d is None:
            _loi("CRM_G_KHONG_THAY", "Không thấy dự án đang bán (hoặc ngoài phạm vi).")
        return d

    def chi_tiet(self, dang_nhap: str, da_ban_id, *, phien_ban=None, ngay=None) -> dict:
        """Ảnh chụp theo phiên bản (`phien_ban` = số) hoặc theo ngày (`ngay`, mặc định hôm nay) + danh sách phiên bản + quyền sửa của phiên.
        Phiên bản cũ không kèm ngày: lô/căn và tiến độ đọc tại ngày phiên bản đó bắt đầu hiệu lực."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        da = _uuid(da_ban_id, "da_ban_id")
        if phien_ban not in (None, ""):
            if isinstance(phien_ban, str) and phien_ban.isascii() and phien_ban.isdigit():
                phien_ban = int(phien_ban)
            phien_ban = _so_nguyen(phien_ban, "phiên bản", "phien_ban")
        else:
            phien_ban = None
        ngay = _ngay(ngay, "Ngày") if ngay else None
        with m._tx(dt, rr=True) as c:
            d = self._da_ban(c, da)
            ds = m._nhieu(c, """SELECT id, phien_ban, hieu_luc_tu, hieu_luc_den, dang_ban, lap_boi, lap_luc, ly_do FROM master.crm_da_ban_phien_ban
                                WHERE da_ban_id = %s ORDER BY phien_ban""", (da,))
            if phien_ban is not None:
                v = next((x for x in ds if x["phien_ban"] == phien_ban), None)
                if v is None:
                    _loi("CRM_G_KHONG_THAY", "Không thấy phiên bản này của dự án đang bán.", "phien_ban")
                ngay_ac = ngay or (self._hom_nay() if v["hieu_luc_den"] is None else v["hieu_luc_tu"])
                s = self.mau._mot(c, "SELECT master.crm_da_anh_chup_pb(%s::uuid, %s::date) AS r", (v["id"], ngay_ac))["r"]
            else:
                s = self.anh_chup_trong(c, d["du_an_id"], ngay or self._hom_nay())
        for x in ds:
            x["hieu_luc_tu_hien_thi"], x["hieu_luc_den_hien_thi"] = _ngay_vn(x["hieu_luc_tu"]), _ngay_vn(x["hieu_luc_den"])
        return {"da_ban_id": da, "du_an_id": d["du_an_id"], "duoc_sua": bool(d["duoc_sua"]), "anh_chup": s, "hien_thi": hien_thi_anh_chup(s),
                "phien_ban_ds": ds, "danh_muc": danh_muc()}

    def lich_su(self, dang_nhap: str, da_ban_id) -> dict:
        """Lịch sử đầy đủ: mọi phiên bản (kèm nội dung), sự kiện nhật ký, lịch sử từng lô/căn, các phiên bản tiến độ tiêu chuẩn (G7) của dự án
        (đã hiệu lực; nháp/chờ CFO chỉ hiện cho kế toán/KTT/CFO)."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        da = _uuid(da_ban_id, "da_ban_id")
        with m._tx(dt, rr=True) as c:
            d = self._da_ban(c, da)
            pb = m._nhieu(c, """SELECT id, phien_ban, hieu_luc_tu, hieu_luc_den, dang_ban, lap_boi, lap_luc, ly_do, noi_dung_sha256,
                                       master.crm_da_noi_dung(id) AS noi_dung
                                FROM master.crm_da_ban_phien_ban WHERE da_ban_id = %s ORDER BY phien_ban""", (da,))
            sk = m._nhieu(c, """SELECT luc, nguoi, loai, hanh_dong, ly_do, sau - 'noi_dung' AS sau FROM nhat_ky.su_kien
                                WHERE doi_tuong_bang = 'master.crm_da_ban' AND doi_tuong_id = %s ORDER BY id""", (da,))
            lo = m._nhieu(c, """SELECT o.id AS lo_id, o.ma, s.lan, s.hieu_luc_tu, s.hieu_luc_den, s.dien_tich, s.trang_thai, s.ghi_chu, s.tao_boi, s.tao_luc
                                FROM master.crm_da_ban_lo o JOIN master.crm_da_ban_lo_ls s ON s.lo_id = o.id
                                WHERE o.da_ban_id = %s ORDER BY upper(o.ma), o.ma, s.lan""", (da,))
            g7 = m._nhieu(c, """SELECT b.giai_doan, v.id AS phien_ban_id, v.phien_ban, v.trang_thai, v.valid_from, v.valid_to, v.so_dong, v.lap_boi, v.duyet_boi,
                                       x.ap_dung_boi, x.ap_dung_luc, x.can_cu,
                                       CASE WHEN v.trang_thai <> 'HIEU_LUC' THEN NULL WHEN x.phien_ban_id IS NOT NULL THEN 'AP_DUNG_NGAY' ELSE 'CFO_DUYET' END AS nguon,
                                       (SELECT coalesce(jsonb_agg(jsonb_build_object('thu_tu', r.thu_tu, 'lan', r.lan, 'gia_tri_loai', r.gia_tri_loai,
                                                'gia_tri_thap_phan', r.gia_tri_thap_phan, 'so_tien_minor', r.so_tien_minor, 'tien_te', r.tien_te,
                                                'moc_loai', r.moc_loai, 'moc_ngay', r.moc_ngay, 'moc_su_kien', r.moc_su_kien, 'ghi_chu', r.ghi_chu)
                                                ORDER BY r.thu_tu), '[]'::jsonb) FROM master.crm_bo_chuan_dong r WHERE r.phien_ban_id = v.id) AS dong
                                FROM master.crm_bo_chuan b JOIN master.crm_bo_chuan_phien_ban v ON v.bo_chuan_id = b.id
                                LEFT JOIN master.crm_bo_chuan_ap_dung x ON x.phien_ban_id = v.id
                                WHERE b.du_an_id = %s AND b.phap_nhan_id = %s AND (v.trang_thai = 'HIEU_LUC' OR master.crm_g_chuan_doc_duoc(v.phap_nhan_id))
                                ORDER BY b.giai_doan, v.phien_ban""", (d["du_an_id"], d["phap_nhan_id"]))
        theo_lo: dict = {}
        for r in lo:
            x = theo_lo.setdefault(r["lo_id"], {"lo_id": r["lo_id"], "ma": r["ma"], "lich_su": []})
            x["lich_su"].append({k: r[k] for k in ("lan", "hieu_luc_tu", "hieu_luc_den", "dien_tich", "trang_thai", "ghi_chu", "tao_boi", "tao_luc")}
                                | {"trang_thai_hien_thi": TRANG_THAI_LO.get(r["trang_thai"]), "hieu_luc_tu_hien_thi": _ngay_vn(r["hieu_luc_tu"]),
                                   "dien_tich_hien_thi": f"{_so_vn(r['dien_tich'])} m²"})
        for r in sk:
            r["hanh_dong_hien_thi"] = HANH_DONG.get(r["hanh_dong"], "Thao tác khác")
        for r in g7:
            r["nguon_hien_thi"] = NGUON_G7.get(r["nguon"])
            r["khoang_rong"] = r["valid_to"] is not None and r["valid_to"] == r["valid_from"]  # bị thay trong cùng ngày: chưa từng được áp dụng
        for r in pb:
            r["hieu_luc_tu_hien_thi"], r["hieu_luc_den_hien_thi"] = _ngay_vn(r["hieu_luc_tu"]), _ngay_vn(r["hieu_luc_den"])
        return {"da_ban_id": da, "du_an_id": d["du_an_id"], "phien_ban": pb, "su_kien": sk, "lo": list(theo_lo.values()), "tien_do": g7}

    # ------------------------------------------------------------------ lệnh (mỗi lệnh MỘT giao dịch trên kết nối chủ bảng; replay theo khoa + H)
    def bat_ban(self, dang_nhap: str, *, du_an_id, thong_tin, phi=None, ly_do=None, khoa) -> dict:
        """Bật bán dự án có sẵn trong danh mục dự án kế toán → phiên bản 1 (đang bán), hiệu lực từ hôm nay."""
        dt = self.mau.danh_tinh(dang_nhap)
        da, tt, ph, ly, khoa = _uuid(du_an_id, "du_an_id"), chuan_hoa_thong_tin(thong_tin, bat_ban=True), chuan_hoa_phi(phi), _ly_do(ly_do), _khoa(khoa)
        h = _h("CRM_DA_BAT_BAN", {"du_an_id": da, "thong_tin": tt, "phi": ph, "ly_do": ly})
        return self.mau._lenh(dt, "SELECT master.crm_da_bat_ban(%s, %s, %s::uuid, %s::jsonb, %s::jsonb, %s) AS r",
                              (khoa, h, da, json.dumps(tt, ensure_ascii=False), json.dumps(ph, ensure_ascii=False), ly))

    def cap_nhat(self, dang_nhap: str, *, da_ban_id, expected_phien_ban, thong_tin, phi=None, ly_do=None, khoa) -> dict:
        """Sửa thông tin (và phí nếu gửi) → phiên bản mới; cùng nội dung → `khong_doi` (không tạo phiên bản)."""
        dt = self.mau.danh_tinh(dang_nhap)
        da, n = _uuid(da_ban_id, "da_ban_id"), _so_nguyen(expected_phien_ban, "phiên bản mong đợi", "expected_phien_ban")
        tt, ph, ly, khoa = chuan_hoa_thong_tin(thong_tin), None if phi is None else chuan_hoa_phi(phi), _ly_do(ly_do), _khoa(khoa)
        h = _h("CRM_DA_CAP_NHAT", {"da_ban_id": da, "expected_phien_ban": n, "thong_tin": tt, "phi": ph, "ly_do": ly})
        return self.mau._lenh(dt, "SELECT master.crm_da_cap_nhat(%s, %s, 'CRM_DA_CAP_NHAT', %s::uuid, %s, %s::jsonb, %s::jsonb, %s) AS r",
                              (khoa, h, da, n, json.dumps(tt, ensure_ascii=False), None if ph is None else json.dumps(ph, ensure_ascii=False), ly))

    def sua_phi(self, dang_nhap: str, *, da_ban_id, expected_phien_ban, phi, ly_do=None, khoa) -> dict:
        """Thay danh sách phí tiêu chuẩn (thông tin khác giữ nguyên) → phiên bản mới; báo giá đã lưu giữ phiên bản đã nạp."""
        dt = self.mau.danh_tinh(dang_nhap)
        da, n = _uuid(da_ban_id, "da_ban_id"), _so_nguyen(expected_phien_ban, "phiên bản mong đợi", "expected_phien_ban")
        if phi is None:
            _loi("CRM_DA_PHI_SAI", "Cần danh sách phí (gửi [] để bỏ hết phí).", "phi")
        ph, ly, khoa = chuan_hoa_phi(phi), _ly_do(ly_do), _khoa(khoa)
        h = _h("CRM_DA_PHI", {"da_ban_id": da, "expected_phien_ban": n, "phi": ph, "ly_do": ly})
        return self.mau._lenh(dt, "SELECT master.crm_da_cap_nhat(%s, %s, 'CRM_DA_PHI', %s::uuid, %s, NULL, %s::jsonb, %s) AS r",
                              (khoa, h, da, n, json.dumps(ph, ensure_ascii=False), ly))

    def ghi_lo(self, dang_nhap: str, *, da_ban_id, lo, ly_do=None, khoa) -> dict:
        """Thêm/sửa lô/căn theo lô: lô mới (không `expected_lan`) → lần 1; lô đã có (cần `expected_lan` = lần hiện hành) đổi → lần mới."""
        dt = self.mau.danh_tinh(dang_nhap)
        da, ds, ly, khoa = _uuid(da_ban_id, "da_ban_id"), chuan_hoa_lo(lo), _ly_do(ly_do), _khoa(khoa)
        h = _h("CRM_DA_LO", {"da_ban_id": da, "lo": ds, "ly_do": ly})
        gui = [{k: v for k, v in x.items() if v is not None} for x in ds]
        return self.mau._lenh(dt, "SELECT master.crm_da_lo_ghi(%s, %s, %s::uuid, %s::jsonb, %s) AS r",
                              (khoa, h, da, json.dumps(gui, ensure_ascii=False), ly))

    def moc_ghi(self, dang_nhap, *, da_ban_id, moc, ly_do=None, khoa) -> dict:
        dt = self.mau.danh_tinh(dang_nhap)
        da, nd, ly, khoa = _uuid_t(da_ban_id, "dự án đang bán", "da_ban_id"), chuan_hoa_moc(moc), _ly_do(ly_do), _khoa(khoa)
        if nd.get("ngay_thuc_te") and nd["ngay_thuc_te"] > self._hom_nay():
            _loi("CRM_DA_MOC_NGAY_SAI", "Ngày thực tế không được sau hôm nay.", "moc.ngay_thuc_te")
        h = _h("CRM_DA_MOC", {"da_ban_id": da, "moc": nd, "ly_do": ly})
        return self.mau._lenh(dt, "SELECT master.crm_da_moc_ghi(%s, %s, %s::uuid, %s::jsonb, %s) AS r",
                              (khoa, h, da, json.dumps(nd, ensure_ascii=False), ly))

    def _doi_trang_thai(self, dang_nhap, hanh: str, dang_ban: bool, da_ban_id, expected_phien_ban, ly_do, khoa) -> dict:
        dt = self.mau.danh_tinh(dang_nhap)
        da, n = _uuid(da_ban_id, "da_ban_id"), _so_nguyen(expected_phien_ban, "phiên bản mong đợi", "expected_phien_ban")
        ly, khoa = _ly_do(ly_do, bat_buoc=not dang_ban), _khoa(khoa)
        h = _h(hanh, {"da_ban_id": da, "expected_phien_ban": n, "ly_do": ly})
        return self.mau._lenh(dt, "SELECT master.crm_da_doi_trang_thai(%s, %s, %s::uuid, %s, %s, %s) AS r", (khoa, h, da, n, dang_ban, ly))

    def ngung_ban(self, dang_nhap: str, *, da_ban_id, expected_phien_ban, ly_do, khoa) -> dict:
        """Ngừng bán (cần lý do): phiên bản mới `dang_ban = false` + sự kiện nhật ký; không còn trong danh sách chọn của báo giá mới."""
        return self._doi_trang_thai(dang_nhap, "CRM_DA_NGUNG_BAN", False, da_ban_id, expected_phien_ban, ly_do, khoa)

    def mo_ban_lai(self, dang_nhap: str, *, da_ban_id, expected_phien_ban, ly_do=None, khoa) -> dict:
        return self._doi_trang_thai(dang_nhap, "CRM_DA_MO_BAN_LAI", True, da_ban_id, expected_phien_ban, ly_do, khoa)

    def ap_dung_tien_do(self, dang_nhap: str, *, du_an_id, expected_version=None, giai_doan=None, dong, khoa) -> dict:
        """Tiến độ thanh toán tiêu chuẩn của dự án đang bán = bộ chuẩn G7, áp dụng NGAY (bỏ CFO, QD-20261025-07); giai đoạn mặc định = giai đoạn
        tiến độ của thông tin dự án hiện hành. `expected_version` bắt buộc = số bản hiệu lực đã đọc, 0 nếu chưa có; bản đã đổi → 409."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        da = _uuid(du_an_id, "du_an_id")
        if type(expected_version) is not int or not 0 <= expected_version <= 999_999_999:
            _loi("CRM_DA_YEU_CAU_SAI", "Cần phiên bản tiến độ mong đợi (số nguyên 0–999999999; 0 nếu chưa có).", "expected_version")
        if giai_doan in ("", None):
            giai_doan = None
        elif not isinstance(giai_doan, str) or not GIAI_DOAN_RE.fullmatch(giai_doan):
            _loi("CRM_G_YEU_CAU_SAI", "Giai đoạn chỉ gồm chữ/số/_ . - (1–80).", "giai_doan")
        rows, khoa = m._dong_g7(dong), _khoa(khoa)
        h = _h("CRM_CHUAN_AP_DUNG", {"du_an_id": da, "giai_doan": giai_doan, "dong": rows, "expected_version": expected_version})
        return m._lenh(dt, "SELECT master.crm_g_chuan_ap_dung(%s, %s, %s::uuid, %s, %s::jsonb, %s) AS r",
                       (khoa, h, da, giai_doan, json.dumps(rows, ensure_ascii=False), expected_version))


# ================================================================================================== seed DEMO (chủ CSDL; qua CHÍNH hàm lệnh)
SEED_NGUOI = "MO_PHONG_BAN_HANG"  # bán hàng DEMO có module CRM trên cả hai pháp nhân DEMO (crm_demo.NGUOI_DUNG)
SEED_KHOA = "seed-du-an-ban-v1"
SEED_MOC_KHOA = "seed-du-an-moc-v1"
_G7_DEMO = ("lan", "gia_tri_loai", "gia_tri_thap_phan", "moc_loai", "moc_su_kien", "ghi_chu")
SEED_DU_AN = (
    {"phap_nhan": "PN_DEMO_A", "du_an": "DA_KCN_DEMO", "loai_hinh": "DT-KCN-THUE-DAT-DEMO",
     "thong_tin": {"vi_tri": "KCN DEMO — khu A, đường trục chính (DEMO)", "mo_ta": "Đất công nghiệp cho thuê có hạ tầng — dữ liệu DEMO, không phải chính sách giá thật.",
                   "don_gia_niem_yet": "120", "tien_te": "USD", "thue_suat": "10", "gia_dat_tru": "24", "giai_doan_g7": "GD1"},
     "phi": [{"ten": "Phí bảo trì hạ tầng DEMO", "loai": "BAO_TRI", "muc": "0.5", "don_vi_tinh": "M2_NAM", "tien_te": "USD", "co_so_tinh": "Diện tích đất thuê"},
             {"ten": "Phí sử dụng hạ tầng DEMO", "loai": "SU_DUNG", "muc": "0.05", "don_vi_tinh": "M2_THANG", "tien_te": "USD", "co_so_tinh": "Diện tích đất thuê"},
             {"ten": "Phí đấu nối DEMO", "loai": "KHAC", "muc": "5000000", "don_vi_tinh": "LAN", "tien_te": "VND", "co_so_tinh": "Mỗi điểm đấu nối"}],
     "lo": [{"ma": "CN-A01-DEMO", "dien_tich": "15000", "trang_thai": "CON_TRONG"}, {"ma": "CN-A02-DEMO", "dien_tich": "20000", "trang_thai": "GIU_CHO"},
            {"ma": "CN-A03-DEMO", "dien_tich": "12000.5", "trang_thai": "DA_BAN"}],
     "g7": [("1", "PERCENT", "30", "SU_KIEN", "KY_HD", "Đặt cọc khi ký — DEMO"), ("2", "PERCENT", "40", "SU_KIEN", "SAU_KY_90", None),
            ("3", "PERCENT", "30", "SU_KIEN", "BAN_GIAO", None)]},
    {"phap_nhan": "PN_DEMO_B", "du_an": "DA_NHA_DEMO", "loai_hinh": "DT-NHA-O-DEMO",
     "thong_tin": {"vi_tri": "Khu nhà ở DEMO — tòa A (DEMO)", "mo_ta": "Căn hộ để bán — dữ liệu DEMO, không phải chính sách giá thật.",
                   "don_gia_niem_yet": "35000000", "tien_te": "VND", "thue_suat": "10", "gia_dat_tru": "0", "giai_doan_g7": "GD1"},
     "phi": [{"ten": "Phí quản lý vận hành DEMO", "loai": "SU_DUNG", "muc": "15000", "don_vi_tinh": "M2_THANG", "tien_te": "VND", "co_so_tinh": "Diện tích thông thủy"},
             {"ten": "Kinh phí bảo trì DEMO", "loai": "BAO_TRI", "muc": "1500000", "don_vi_tinh": "LAN", "tien_te": "VND", "co_so_tinh": "Mỗi căn, nộp khi bàn giao"}],
     "lo": [{"ma": "CAN-A0101-DEMO", "dien_tich": "75.5", "trang_thai": "CON_TRONG"}, {"ma": "CAN-A0102-DEMO", "dien_tich": "82", "trang_thai": "CON_TRONG"},
            {"ma": "CAN-A0201-DEMO", "dien_tich": "68.25", "trang_thai": "DA_BAN"}],
     "g7": [("1", "PERCENT", "10", "SU_KIEN", "KY_HD", None), ("2", "PERCENT", "60", "SU_KIEN", "XONG_TANG_10", None),
            ("3", "PERCENT", "30", "SU_KIEN", "BAN_GIAO", None)]},
)


def _dong_g7_demo(rows) -> list[dict]:
    return CrmMauK2._dong_g7([dict(zip(_G7_DEMO, r)) for r in rows])


def _seed_moc_demo(c, nguoi_id, da, ma, ngay) -> bool:
    """Khóa riêng từng mốc; biên nhận giữ nguyên ngày seed kể cả mở lại vào ngày khác."""
    if ma != "DA_KCN_DEMO":
        return False
    if not c.execute("SELECT to_regclass('master.crm_da_moc') IS NOT NULL").fetchone()[0]:
        return False  # bản schema cũ vẫn seed dự án được
    tao = False
    for i, (ten, tat, lech) in enumerate((("Xong chứng nhận đầu tư", "CNĐT", 30),
                                        ("Bàn giao hạ tầng giai đoạn 1 — DEMO", None, -5)), start=1):
        khoa = f"{SEED_MOC_KHOA}-{ma}-{i}"
        if c.execute("""SELECT 1 FROM master.crm_g_bien_nhan WHERE nguoi_dung_id = %s::uuid
                        AND hanh_dong = 'CRM_DA_MOC' AND khoa = %s""", (nguoi_id, khoa)).fetchone():
            continue
        moc = chuan_hoa_moc({"ten": ten, "ten_tat": tat, "ngay_du_kien": (date.fromisoformat(ngay) + timedelta(days=lech)).isoformat()})
        c.execute("SELECT master.crm_da_moc_ghi(%s, %s, %s::uuid, %s::jsonb, %s)",
                  (khoa, _h("CRM_DA_MOC", {"da_ban_id": da, "moc": moc, "ly_do": None}), da, json.dumps(moc, ensure_ascii=False), None)).fetchone()
        tao = True
    return tao


def khoi_tao_demo(admin_conn, *, hom_nay: date | None = None) -> dict:
    """Seed DEMO (chủ CSDL, psycopg autocommit, tuple row) — 2 dự án đang bán DEMO + phí + lô/căn + tiến độ tiêu chuẩn áp dụng ngay, ĐI QUA CHÍNH
    các hàm lệnh M0031/M0035 dưới danh tính bán hàng DEMO (GUC cục bộ của giao dịch), khóa idempotent cố định: mở lại không thêm phiên
    bản/mốc; M0035 bổ sung hai mốc cho dự án KCN đã seed ở bản cũ, giữ nguyên ngày khai khi mở lại khác ngày.
    Dự án đã được người dùng bật bán (không phải seed) → BO_QUA_DA_CO, không đè. Không raise khi chưa sẵn sàng — trả trạng thái trung thực."""
    kq = {"trang_thai": "CHUA_SAN_SANG", "du_an": [], "ly_do": None}
    ngay = (hom_nay or _hom_nay_vn()).isoformat()
    with admin_conn.transaction():
        if admin_conn.execute("SELECT to_regclass('master.crm_da_ban') IS NOT NULL").fetchone()[0] is not True:
            return {**kq, "ly_do": "Schema chưa có dự án đang bán — migrate 31 trước."}
        nd = admin_conn.execute("""SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s AND trang_thai = 'HOAT_DONG' AND mo_phong""",
                                (SEED_NGUOI,)).fetchone()
        if nd is None:
            return {**kq, "ly_do": f"Thiếu người dùng DEMO {SEED_NGUOI}."}
        admin_conn.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                           "set_config('ktt.ngay_hieu_luc', %s, true)", (nd[0], SEED_NGUOI, ngay))
        for x in SEED_DU_AN:
            ma = x["du_an"]
            r = admin_conn.execute("""SELECT a.id::text, l.id::text FROM master.du_an a JOIN master.phap_nhan p ON p.id = a.phap_nhan_id
                                      JOIN master.loai_hinh_doanh_thu l ON l.phap_nhan_id = p.id AND l.ma = %s AND l.valid_to IS NULL
                                      WHERE p.ma = %s AND a.ma_junsky = %s""", (x["loai_hinh"], x["phap_nhan"], ma)).fetchall()
            if len(r) != 1:
                kq["du_an"].append({"du_an": ma, "trang_thai": "CHUA_SAN_SANG", "ly_do": "Thiếu/mơ hồ dự án hoặc loại hình DEMO — không tạo master mới."})
                continue
            du_an_id, lh = r[0]
            tt = chuan_hoa_thong_tin({**x["thong_tin"], "loai_hinh_id": lh})
            ph = chuan_hoa_phi(x["phi"])
            khoa = f"{SEED_KHOA}-{ma}"
            mot = {"du_an": ma}
            try:
                with admin_conn.transaction():
                    da_co = admin_conn.execute("SELECT id::text FROM master.crm_da_ban WHERE du_an_id = %s", (du_an_id,)).fetchone()
                    co_bien_nhan = admin_conn.execute("""SELECT 1 FROM master.crm_g_bien_nhan WHERE nguoi_dung_id = %s::uuid AND hanh_dong = 'CRM_DA_BAT_BAN'
                                                         AND khoa = %s""", (nd[0], khoa + "-bat-ban")).fetchone()
                    if da_co:  # đã seed (biên nhận của seed, cả ba lệnh cùng một savepoint) → DU; người dùng tự bật bán → không đè
                        tao_moc = _seed_moc_demo(admin_conn, nd[0], da_co[0], ma, ngay) if co_bien_nhan else False
                        kq["du_an"].append({**mot, "trang_thai": "DA_TAO" if tao_moc else "DU" if co_bien_nhan else "BO_QUA_DA_CO",
                                            "mo_lai_khong_them": not tao_moc})
                        continue
                    b = admin_conn.execute("SELECT master.crm_da_bat_ban(%s, %s, %s::uuid, %s::jsonb, %s::jsonb, %s)",
                                           (khoa + "-bat-ban", _h("CRM_DA_BAT_BAN", {"du_an_id": du_an_id, "thong_tin": tt, "phi": ph, "ly_do": None}),
                                            du_an_id, json.dumps(tt, ensure_ascii=False), json.dumps(ph, ensure_ascii=False), None)).fetchone()[0]
                    da = b["ket_qua"]["da_ban_id"]
                    lo = chuan_hoa_lo(x["lo"])
                    lk = admin_conn.execute("SELECT master.crm_da_lo_ghi(%s, %s, %s::uuid, %s::jsonb, %s)",
                                            (khoa + "-lo", _h("CRM_DA_LO", {"da_ban_id": da, "lo": lo, "ly_do": None}), da,
                                             json.dumps([{k: v for k, v in z.items() if v is not None} for z in lo], ensure_ascii=False), None)).fetchone()[0]
                    dong = _dong_g7_demo(x["g7"])
                    g = admin_conn.execute("SELECT master.crm_g_chuan_ap_dung(%s, %s, %s::uuid, %s, %s::jsonb, %s)",
                                           (khoa + "-tien-do", _h("CRM_CHUAN_AP_DUNG", {"du_an_id": du_an_id, "giai_doan": None, "dong": dong,
                                                                                     "expected_version": 0}), du_an_id,
                                            None, json.dumps(dong, ensure_ascii=False), 0)).fetchone()[0]
                    _seed_moc_demo(admin_conn, nd[0], da, ma, ngay)
                    kq["du_an"].append({**mot, "trang_thai": "DU" if b["lap_lai"] else "DA_TAO", "phien_ban": b["ket_qua"]["phien_ban"],
                                        "so_phi": len(ph), "so_lo": len(lk["ket_qua"]["lo"]), "tien_do_phien_ban": g["ket_qua"]["phien_ban"],
                                        "mo_lai_khong_them": bool(b["lap_lai"] and lk["lap_lai"] and g["lap_lai"])})
            except Exception as exc:  # noqa: BLE001 — một dự án lỗi không chặn dự án kia; chỉ mã lỗi đã làm sạch
                prim = (getattr(getattr(exc, "diag", None), "message_primary", "") or "").split(":", 1)[0]
                kq["du_an"].append({**mot, "trang_thai": "LOI", "ma": prim if prim.replace("_", "").isalnum() and prim.isupper() else type(exc).__name__})
    tt_ds = [x["trang_thai"] for x in kq["du_an"]]
    tong = "LOI" if "LOI" in tt_ds else "CHUA_SAN_SANG" if "CHUA_SAN_SANG" in tt_ds else "DA_TAO" if "DA_TAO" in tt_ds else "DU"
    return {**kq, "trang_thai": tong, "nguoi_seed": SEED_NGUOI, "ngay": ngay}
