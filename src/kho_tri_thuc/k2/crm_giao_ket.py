"""CRM-41-03 — service G2 Báo giá (hai cột) → G3 Soạn hợp đồng từ mẫu (ba cột) trên K2 PostgreSQL (M0021), dùng lại toàn bộ seam G1/G7:
danh tính phiên + kết nối CHỦ BẢNG + giao dịch có GUC danh tính (CrmMauK2), biên nhận/ghim quyền của M0018, mẫu đã duyệt + facts/bản đồ G1,
bộ chuẩn G7 đọc trong cùng giao dịch, kho bất biến write_immutable, renderer tối thiểu nguon/crm_docx.

- Trình duyệt chỉ gửi dữ liệu nhập tay typed (chuỗi số chính xác, ngày, mã), ID đối tượng, revision mong đợi, khóa; KHÔNG actor/PN/trạng thái/facts/
  hash/đường dẫn. Mọi số tiền tính bằng số nguyên đơn vị nhỏ nhất/Fraction — không float, không làm tròn ngầm; không biểu diễn đúng scale →
  "chưa tính được" + chặn In/Chuyển/Xuất; Lưu nháp vẫn được phép. Tỷ lệ suy ra từ tiền chỉ làm tròn khi hiển thị.
- Không sinh nghĩa vụ/lịch thu/công nợ/M1/duyệt; không HIEU_LUC/DA_KY. Chuyển sang Soạn tạo đúng MỘT master.hop_dong (SQL).
- In/Xuất là ba pha: (A) dưới khóa + giao dịch ngắn: quyền hiện hành → biên nhận → chụp revision/mẫu đã ghim/raw đã kiểm hash → cổng; (B) NGOÀI
  khóa/giao dịch: render DOCX (giữ bất biến TRƯỚC PDF) → Word COM sở hữu → kiểm PDF; (C) dưới khóa + giao dịch ngắn: quyền hiện hành + CAS revision
  → công bố trung thực (PDF_DAT | PDF_CHUA_SAN_SANG | PDF_LOI | DA_CU). Không xóa/ghi đè tệp; mọi lần chạy giữ thư mục riêng.

BG-1c (QD-20261025-01…04) — dữ liệu báo giá v2 (`tien_chinh = "VND"`, máy chủ đặt): VND là tiền chính của MỌI báo giá mới.
- Tổng giá trị (VND) = đơn giá × tỷ giá × diện tích, LÀM TRÒN ĐẾN ĐỒNG, ĐÚNG NỬA LÀM TRÒN LÊN (`lam_tron_nua_len`; mọi số ≥ 0). Đây là phép
  làm tròn DUY NHẤT trên tiền; bước kiểm khi Ký (M0030, `k2/sql_crm_bg1c.py`) dùng cùng công thức (`round(numeric, 0)` của PostgreSQL).
- Báo giá USD: tỷ giá nhập tay, thiếu → mặc định chung `master.cau_hinh` khóa `crm.bao_gia.ty_gia_usd_mac_dinh` (kế toán sửa, có nhật ký);
  chưa có dòng cấu hình → 26.000 của phần mềm. Tỷ giá đã dùng được LƯU vào báo giá (báo giá đã lưu giữ tỷ giá của nó). Báo giá VND: tỷ giá = 1.
- Lịch thanh toán, ghi đè tổng, tổng typed `gia.tong`, bằng chữ: đều VND. USD chỉ là tham chiếu = đơn giá × diện tích (làm tròn đến cent).
- Dữ liệu cũ (không có `tien_chinh`) giữ nguyên nghĩa cũ: tiền chính = tiền tệ báo giá; không tự chuyển đổi.
- Hai bước (QD-20261025-03): In sơ bộ chỉ cần phần giá + lịch hợp lệ (+ tỷ giá khi USD); khách hàng và phí quản lý/bảo trì (khi profile loại
  hình khai `bao_gia.truong_ap_dung` có "phi_bao_tri") là điều kiện Chuyển sang soạn hợp đồng, chặn tại máy chủ.
"""

from __future__ import annotations

import json
import re
import uuid
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from ..ha_tang.primitives import DataError, canonical_json, money_minor, sha256
from ..ha_tang.store import write_immutable
from ..nguon import crm_docx as R
from .crm_mau import CrmMauK2, _h, _khoa, _ngay, _uuid, _v
from .sql_crm_bg1c import CRM_BG1C_SQL as _M0030

PHIEN_BAN_BG, PHIEN_BAN_SOAN = "crm-bao-gia/v2", "crm-soan/v1"  # v2 (BG-1c): thêm tien_chinh = VND; v1 đã lưu vẫn đọc theo nghĩa cũ
TIEN_TE = ("VND", "USD")
TIEN_CHINH = "VND"
KHOA_TY_GIA_MAC_DINH = "crm.bao_gia.ty_gia_usd_mac_dinh"  # master.cau_hinh (M0001), phap_nhan_id NULL = cấu hình chung mọi pháp nhân
TY_GIA_USD_MAC_DINH_PHAN_MEM = "26000"  # chỉ khi chưa có dòng cấu hình (QD-20261025-04); kế toán lưu một lần là thành cấu hình
VAI_SUA_CAU_HINH = ("KE_TOAN", "KE_TOAN_TRUONG")
TRUONG_HD_USD_THAM_CHIEU, TRUONG_HD_TY_GIA = "gia_tri_usd_tham_chieu", "ty_gia_usd_vnd"  # điền khi danh mục mẫu có trường cùng mã + kiểu


def _hang_m0030(mau: str) -> int:
    m = re.search(mau, _M0030[0])
    if m is None:
        raise RuntimeError("Không đọc được hằng giới hạn từ M0030 (k2/sql_crm_bg1c.py)")
    return int(m.group(1))


# Miền tiền RÚT TỪ M0030 (bước kiểm khi Ký): tổng và tiền từng đợt, đơn vị nhỏ nhất, phải 0 < x ≤ v_max (bigint) — một nguồn cho hai tầng.
TIEN_TOI_DA_MINOR = _hang_m0030(r"v_max constant numeric := ([0-9]+);")
RE_SO = re.compile(r"\d{1,24}(\.\d{1,12})?")
RE_MA = re.compile(r"[A-Za-z0-9_.-]{1,80}")
KHOA_BG = {"loai_hinh_id", "du_an_id", "giai_doan_g7", "nguon_lich", "don_vi", "khach", "gia", "fx", "phi_bao_tri", "lich", "het_han", "ghi_chu",
           "tong_gia_tri_ghi_de", "tien_chinh"}
TRAM = Fraction(100)
HAN_PDF_GIAY = 180.0
MOC_CHUAN = (("KY_HD", "Ký"), ("BAN_GIAO", "Bàn giao"), ("SO", "Sổ"))


def nhan_moc_su_kien(ma: str | None) -> str:
    if not ma:
        return "Sự kiện: chưa xác định"
    nhan = dict(MOC_CHUAN).get(ma)
    if nhan:
        return nhan
    for mau, nhan in ((r"SAU_KY_([0-9]+)", "Sau ký + {} ngày"), (r"XONG_TANG_([0-9]+)", "Xây xong tầng {}")):
        m = re.fullmatch(mau, ma)
        if m:
            return nhan.format(int(m.group(1)))
    # Mã cũ/tùy chỉnh vẫn được giữ trong dữ liệu, không in mã kỹ thuật làm nhãn.
    return "Sự kiện khác (chưa có nhãn)"


def danh_muc_moc_chuan() -> dict:
    return {"moc": [{"ma": ma, "nhan": nhan} for ma, nhan in MOC_CHUAN],
            "moc_tham_so": [{"mau_ma": "XONG_TANG_<n>", "nhan": "Xây xong tầng n", "tham_so": "n", "toi_thieu": 1},
                            {"mau_ma": "SAU_KY_<n>", "nhan": "Sau ký + n ngày", "tham_so": "n", "toi_thieu": 0}]}


def _loi(ma: str, msg: str):
    raise DataError(ma, msg)


def _str(v, ten: str, toi_da: int, *, ngoac: bool = False):
    if v is None or v == "":
        return None
    if not isinstance(v, str) or len(v) > toi_da or any(ord(c) < 32 for c in v) or (not ngoac and ("{" in v or "}" in v)):
        _loi("CRM_GK_YEU_CAU_SAI", f"Trường {ten} không hợp lệ (chuỗi ≤ {toi_da}, không ký tự điều khiển/ngoặc nhọn).")
    return v


def _so(v, ten: str):
    """Số thập phân KHÔNG ÂM dạng chuỗi chính xác ('1234.5'); sai dạng/vượt miền → lỗi rõ (không làm tròn/không thành 0)."""
    if v is None or v == "":
        return None
    if not isinstance(v, str) or not RE_SO.fullmatch(v):
        _loi("CRM_GK_SO_SAI", f"{ten} phải là số thập phân không âm dạng chuỗi, dấu chấm thập phân, ≤ 24 chữ số nguyên/12 chữ số lẻ.")
    return v


def _chon(v, ten: str, cho_phep: tuple):
    if v is None or v == "":
        return None
    if v not in cho_phep:
        _loi("CRM_GK_YEU_CAU_SAI", f"Trường {ten} chỉ nhận: {', '.join(cho_phep)}.")
    return v


def _obj(v, ten: str, khoa: set) -> dict:
    if v is None:
        return {}
    if not isinstance(v, dict) or set(v) - khoa:
        _loi("CRM_GK_YEU_CAU_SAI", f"Nhóm {ten} có trường ngoài phạm vi.")
    return v


def _uuid_hoac_none(v, ten):
    return None if v in (None, "") else _uuid(v, ten)


def _frac_str(f: Fraction, toi_da_le: int = 12) -> str | None:
    """Fraction → chuỗi thập phân CHÍNH XÁC (hữu hạn ≤ toi_da_le chữ số lẻ); không biểu diễn được → None (không làm tròn)."""
    for le in range(toi_da_le + 1):
        n = f * 10 ** le
        if n.denominator == 1:
            s = str(abs(n.numerator)).rjust(le + 1, "0")
            s = s if le == 0 else s[:-le] + "." + s[-le:]
            return ("-" if f < 0 else "") + s
    return None


def _minor(s: str | None, tien_te: str | None):
    """(minor:int|None, mã lỗi|None) theo ĐÚNG scale của tiền tệ, qua primitives.money_minor (cấm làm tròn ngầm)."""
    if s is None or tien_te not in TIEN_TE:
        return None, None
    try:
        return money_minor(s, R.SCALE[tien_te]), None
    except DataError as exc:  # vượt INTEGER 64-bit = ngoài miền của bước Ký (M0030), không phải lỗi scale
        return None, "NGOAI_MIEN" if exc.code == "MONEY_OVERFLOW" else "KHONG_DUNG_SCALE_TIEN_TE"


def _gia_tri_nhap(v) -> tuple[str | None, str | None, str | None]:
    """Ô thông minh/ghi đè dùng quy ước VN; trường typed cũ vẫn dùng dấu chấm thập phân."""
    if not isinstance(v, str) or len(v) > 100 or re.search(r"[\x00-\x1f\x7f-\x9f]", v):
        return None, None, "Giá trị phải là chuỗi tối đa 100 ký tự, không có ký tự điều khiển."
    s = v.strip()
    if not s:
        return None, None, None
    loai = "PERCENT" if "%" in s else "AMOUNT"
    so = s[:-1].strip() if s.endswith("%") else s
    if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)(?:,[0-9]{1,12})?", so):
        return None, None, "Giá trị phải là số không âm kiểu Việt (450.000 hoặc 1.500.000,50); thêm % khi nhập tỷ lệ."
    so = so.replace(".", "").replace(",", ".")
    if not RE_SO.fullmatch(so):
        return None, None, "Giá trị tối đa 24 chữ số nguyên và 12 chữ số thập phân."
    return loai, so, None


def _so_vn(s: str | None) -> str:
    if s is None:
        return "chưa tính được"
    _, _, le = s.partition(".")
    le = le.rstrip("0")
    return R.so_hien_thi(Fraction(Decimal(s)), len(le))


def _tien_vn(minor: int, tt: str) -> str:
    return R.tien_hien_thi(minor, tt)


def _ty_le_vn(f: Fraction, *, xap_xi: bool = False) -> str:
    if xap_xi:
        # Chỉ phần hiển thị được làm tròn; tiền và tổng tỷ lệ vẫn tính bằng Fraction chính xác.
        return "≈ " + R.so_hien_thi(Fraction(round(f * 100), 100), 2) + "%"
    s = _frac_str(f)
    return _so_vn(s) + "%" if s is not None else "chưa tính được"


def _ngay_vn(iso: str | None) -> str | None:
    return R.ngay_hien_thi(iso[:10], "dd/MM/yyyy") if iso else None


def lam_tron_nua_len(f: Fraction) -> int:
    """Làm tròn số KHÔNG ÂM đến số nguyên gần nhất; đúng nửa (…,5) làm tròn LÊN. Quy tắc tiền duy nhất của báo giá v2 (Tổng VND đến đồng, USD
    tham chiếu đến cent); trùng `round(numeric, 0)` của PostgreSQL với số ≥ 0 (bước kiểm khi Ký, M0030)."""
    f = Fraction(f)
    if f < 0:
        raise ValueError("lam_tron_nua_len chỉ nhận số không âm")
    return (2 * f.numerator + f.denominator) // (2 * f.denominator)


def la_tien_chinh_vnd(d: dict) -> bool:
    """Báo giá v2 (máy chủ đặt `tien_chinh = VND`)? Dữ liệu cũ không có khóa → nghĩa cũ (tiền chính = tiền tệ báo giá)."""
    return (d or {}).get("tien_chinh") == TIEN_CHINH


def quy_uoc_bao_gia(d: dict) -> dict:
    """Nhãn quy ước tiền của dữ liệu đã lưu để màn hình ghi chú (không tự chuyển đổi dữ liệu cũ)."""
    if la_tien_chinh_vnd(d):
        return {"ma": "VND_CHINH", "ghi_chu": None}
    tt = ((d or {}).get("gia") or {}).get("tien_te")
    return {"ma": "CU_TIEN_TE_BAO_GIA",
            "ghi_chu": f"Báo giá lưu theo quy ước cũ: tổng và lịch tính bằng {tt or 'tiền tệ báo giá'}. Sửa và lưu lại sẽ tính theo VND là tiền chính "
                       "— kiểm lại tổng giá trị và số tiền các đợt."}


def loai_hinh_co_phi(cau_hinh) -> bool:
    """Profile loại hình có trường phí quản lý/bảo trì? Chỉ khi profile KHAI `bao_gia.truong_ap_dung` chứa "phi_bao_tri" (BG-06); không suy từ
    tên/loại hợp đồng. Profile chưa khai → không đòi phí trước Chuyển."""
    bg = (cau_hinh or {}).get("bao_gia") if isinstance(cau_hinh, dict) else None
    ap = bg.get("truong_ap_dung") if isinstance(bg, dict) else None
    return isinstance(ap, list) and "phi_bao_tri" in ap


def _chan_ty_gia_vnd(d: dict) -> None:
    """Lệnh Lưu: báo giá VND chỉ có tỷ giá 1 (QD-20261025-01) — không lưu tỷ giá khác (xem trước báo lỗi tại trường fx.ty_gia)."""
    if d["gia"]["tien_te"] == "VND" and d.get("fx"):
        _loi("CRM_GK_FX_SAI", "Báo giá VND có tỷ giá cố định bằng 1 — bỏ tỷ giá hoặc chọn tiền tệ USD.")


# ================================================================================================== chuẩn hóa dữ liệu nhập
def _dong_lich(rows) -> list[dict]:
    if rows is None:
        return []
    if not isinstance(rows, list) or len(rows) > 200:
        _loi("CRM_GK_LICH_SAI", "Lịch tối đa 200 dòng.")
    out, ids = [], set()
    for i, r in enumerate(rows, start=1):
        r = _obj(r, f"lịch dòng {i}", {"dong_id", "lan", "loai", "ty_le", "so_tien", "tien_te", "moc_loai", "moc_ngay", "moc_su_kien", "ghi_chu", "gia_tri_nhap"})
        nhap = None
        if "gia_tri_nhap" in r:
            nhap = r["gia_tri_nhap"]
            loai_nhap, so, _ = _gia_tri_nhap(nhap)
            # Ô thông minh là nguồn duy nhất khi có mặt, kể cả rỗng/sai; bỏ giá trị typed cũ còn trên form.
            r = {**r, "loai": loai_nhap, "ty_le": so if loai_nhap == "PERCENT" else None,
                 "so_tien": so if loai_nhap == "AMOUNT" else None, "tien_te": None}
        loai = _chon(r.get("loai"), f"loại giá trị dòng {i}", ("PERCENT", "AMOUNT"))
        ml = _chon(r.get("moc_loai"), f"loại mốc dòng {i}", ("NGAY", "SU_KIEN"))
        d = {"dong_id": _uuid_hoac_none(r.get("dong_id"), f"dong_id dòng {i}"), "lan": _str(r.get("lan"), f"lần dòng {i}", 40) or str(i),
             "loai": loai, "ty_le": _so(r.get("ty_le"), f"tỷ lệ dòng {i}"), "so_tien": _so(r.get("so_tien"), f"số tiền dòng {i}"),
             "tien_te": _chon(r.get("tien_te"), f"tiền tệ dòng {i}", TIEN_TE), "moc_loai": ml,
             "moc_ngay": _ngay(r["moc_ngay"], f"Mốc ngày dòng {i}") if r.get("moc_ngay") else None,
             "moc_su_kien": _str(r.get("moc_su_kien"), f"sự kiện dòng {i}", 80), "ghi_chu": _str(r.get("ghi_chu"), f"ghi chú dòng {i}", 1000)}
        if "gia_tri_nhap" in r:
            d["gia_tri_nhap"] = nhap
        if d["moc_su_kien"] is not None and not RE_MA.fullmatch(d["moc_su_kien"]):
            _loi("CRM_GK_LICH_SAI", f"Sự kiện dòng {i} chỉ gồm chữ/số/_ . - (1–80).")
        if (loai == "PERCENT" and d["so_tien"] is not None) or (loai == "AMOUNT" and d["ty_le"] is not None) or \
                (loai is None and (d["ty_le"] is not None or d["so_tien"] is not None)):
            _loi("CRM_GK_LICH_SAI", f"Dòng {i}: giá trị phải khớp loại (tỷ lệ % hoặc số tiền) — không suy từ nhãn.")
        if (ml == "NGAY" and d["moc_su_kien"]) or (ml == "SU_KIEN" and d["moc_ngay"]) or (ml is None and (d["moc_ngay"] or d["moc_su_kien"])):
            _loi("CRM_GK_LICH_SAI", f"Dòng {i}: mốc phải khớp loại (ngày hoặc sự kiện).")
        if d["dong_id"] in ids and d["dong_id"] is not None:
            _loi("CRM_GK_LICH_SAI", "Trùng mã dòng lịch.")
        ids.add(d["dong_id"])
        out.append(d)
    return out


def chuan_hoa_bao_gia(du_lieu, *, fx_mac_dinh: dict | None = None, hom_nay: str | None = None) -> dict:
    """Chuẩn hóa dữ liệu báo giá nhập tay (thiếu vẫn lưu được; sai dạng → lỗi rõ). Không nhận actor/PN/trạng thái/kết quả tính.

    BG-1c: luôn ra dữ liệu v2 (`tien_chinh = VND`). Báo giá USD không gửi tỷ giá + có `fx_mac_dinh` ({ty_gia, ngay}) → nhận tỷ giá mặc định
    (`nguon = MAC_DINH`); gửi tỷ giá không có ngày → ngày = `hom_nay` (nếu có). Báo giá VND: tỷ giá 1 (bỏ khối tỷ giá); tỷ giá khác 1 được giữ
    lại để phép tính báo lỗi tại trường `fx.ty_gia` và lệnh Lưu từ chối."""
    d = _obj(du_lieu, "báo giá", KHOA_BG)
    if d.get("tien_chinh") not in (None, "", TIEN_CHINH):
        _loi("CRM_GK_YEU_CAU_SAI", "Tiền chính của báo giá do máy chủ đặt (VND).")
    gia = _obj(d.get("gia"), "giá", {"tien_te", "don_gia", "dien_tich", "tong", "co_so_thue", "vat_phan_tram"})
    fx = d.get("fx")
    pbt = d.get("phi_bao_tri")
    khach = _obj(d.get("khach"), "khách", {"doi_tac_id", "du_thao"})
    du_thao = _obj(khach.get("du_thao"), "khách dự thảo", {"ten", "lien_he"})
    don_vi = _obj(d.get("don_vi"), "đơn vị", {"ma", "mo_ta", "can_cu"})  # can_cu luôn do máy chủ đặt (chưa có nguồn lô/căn) — giá trị gửi lên bị bỏ
    out = {
        "phien_ban_du_lieu": PHIEN_BAN_BG,
        "tien_chinh": TIEN_CHINH,
        "loai_hinh_id": _uuid(d.get("loai_hinh_id"), "loai_hinh_id"),
        "du_an_id": _uuid_hoac_none(d.get("du_an_id"), "du_an_id"),
        "giai_doan_g7": _str(d.get("giai_doan_g7"), "giai đoạn bộ chuẩn", 80),
        "nguon_lich": _chon(d.get("nguon_lich"), "nguồn lịch", ("DU_AN", "KHACH")) or "KHACH",
        "don_vi": {"ma": _str(don_vi.get("ma"), "mã lô/căn", 80), "mo_ta": _str(don_vi.get("mo_ta"), "mô tả lô/căn", 300), "can_cu": None},
        "khach": {"doi_tac_id": _uuid_hoac_none(khach.get("doi_tac_id"), "doi_tac_id"),
                  "du_thao": None if not du_thao else {"ten": _str(du_thao.get("ten"), "tên khách dự thảo", 300),
                                                       "lien_he": _str(du_thao.get("lien_he"), "liên hệ", 300)}},
        "gia": {"tien_te": _chon(gia.get("tien_te"), "tiền tệ", TIEN_TE), "don_gia": _so(gia.get("don_gia"), "đơn giá"),
                "dien_tich": _so(gia.get("dien_tich"), "diện tích"), "tong": _so(gia.get("tong"), "tổng giá trị"),
                "co_so_thue": _chon(gia.get("co_so_thue"), "cơ sở thuế", ("NET", "GROSS")), "vat_phan_tram": _so(gia.get("vat_phan_tram"), "VAT %")},
        "fx": None, "phi_bao_tri": None,
        "lich": _dong_lich(d.get("lich")),
        "het_han": _ngay(d["het_han"], "Ngày hết hạn") if d.get("het_han") else None,
        "ghi_chu": _str(d.get("ghi_chu"), "ghi chú", 2000),
    }
    if "tong_gia_tri_ghi_de" in d:
        # Giữ nguyên đầu vào để phép tính trả lỗi tại trường, giống ô thông minh của lịch.
        out["tong_gia_tri_ghi_de"] = d["tong_gia_tri_ghi_de"]
    if out["giai_doan_g7"] is not None and not RE_MA.fullmatch(out["giai_doan_g7"]):
        _loi("CRM_GK_YEU_CAU_SAI", "Giai đoạn bộ chuẩn chỉ gồm chữ/số/_ . - (1–80).")
    tt = out["gia"]["tien_te"]
    if fx not in (None, {}):
        fx = _obj(fx, "tỷ giá", {"cap", "ty_gia", "ngay"})
        if tt == "VND":
            # Báo giá VND: tỷ giá khóa = 1. Không gửi/gửi 1 → bỏ khối; khác 1 → giữ để báo lỗi theo trường (VND_TY_GIA_KHAC_1), Lưu từ chối.
            tg = _so(fx.get("ty_gia"), "tỷ giá")
            if tg is not None and Fraction(Decimal(tg)) != 1:
                out["fx"] = {"cap": "USD/VND", "ty_gia": tg, "ngay": None}
        else:
            if fx.get("cap") not in (None, "", "USD/VND"):
                _loi("CRM_GK_FX_SAI", "Tỷ giá chỉ nhận cặp USD/VND (nhập tay).")
            tg = _so(fx.get("ty_gia"), "tỷ giá")
            if tg is None or Fraction(Decimal(tg)) <= 0:
                _loi("CRM_GK_FX_SAI", "Tỷ giá phải dương.")
            ngay = fx.get("ngay")
            if ngay in (None, "") and hom_nay:
                ngay = hom_nay
            out["fx"] = {"cap": "USD/VND", "ty_gia": tg, "ngay": _ngay(ngay, "Ngày tỷ giá") if ngay not in (None, "") else None}
    elif tt == "USD" and fx_mac_dinh:
        out["fx"] = {"cap": "USD/VND", "ty_gia": _so(fx_mac_dinh["ty_gia"], "tỷ giá mặc định"), "ngay": fx_mac_dinh.get("ngay") or hom_nay}
        nguon = fx_mac_dinh.get("nguon", "MAC_DINH")  # None = tỷ giá đã lưu do người nhập (giữ nguyên, không gắn nhãn mặc định)
        if nguon:
            out["fx"]["nguon"] = nguon
    if pbt not in (None, {}):
        pbt = _obj(pbt, "phí bảo trì", {"gia_tri", "tien_te", "co_so"})
        out["phi_bao_tri"] = {"gia_tri": _so(pbt.get("gia_tri"), "phí bảo trì"), "tien_te": _chon(pbt.get("tien_te"), "tiền tệ phí bảo trì", TIEN_TE),
                              "co_so": _str(pbt.get("co_so"), "cơ sở phí bảo trì", 300)}
    return out


# ================================================================================================== tính chính xác + kiểm
def _phep_tinh(g: dict, tt: str, ty_gia: str | None, f_tich: Fraction, tich: int) -> str:
    """Chuỗi phép tính Tổng VND cho màn hình, vd "100 USD × 26.000 × 15.000 m² = 39.000.000.000 đ"."""
    if tt == "USD":
        s = f"{_so_vn(g['don_gia'])} USD × {_so_vn(ty_gia)} × {_so_vn(g['dien_tich'])} m²"
    else:
        s = f"{_so_vn(g['don_gia'])} đ × {_so_vn(g['dien_tich'])} m²"
    s += f" = {R.so_hien_thi(Fraction(tich), 0)} đ"
    return s + (" (đã làm tròn đến đồng)" if f_tich != tich else "")


def tinh_bao_gia(d: dict, g7: dict | None, *, co_phi: bool = False) -> dict:
    """Tính/kiểm báo giá bằng số nguyên đơn vị nhỏ nhất + Fraction (không float/residual). Trả kết quả + thieu/canh_bao/chan_in/chan_chuyen.

    BG-1c — dữ liệu v2 (`tien_chinh = VND`): tiền chính `tien_te` của kết quả = VND; Tổng VND = đơn giá × tỷ giá × diện tích làm tròn đến đồng
    (nửa lên — phép làm tròn duy nhất); ghi đè/tổng typed/lịch/bằng chữ bằng VND; `tien_te_don_gia` = tiền tệ báo giá; USD chỉ tham chiếu.
    Dữ liệu cũ (không `tien_chinh`): giữ nguyên nghĩa và phép tính cũ (tiền chính = tiền tệ báo giá, đơn giá × diện tích không làm tròn).
    `co_phi`: profile loại hình có phí quản lý/bảo trì → thiếu phí chặn Chuyển (không chặn In sơ bộ)."""
    g = d["gia"]
    tt = g["tien_te"]  # tiền tệ của đơn giá (USD/VND)
    moi = la_tien_chinh_vnd(d)
    tc = (TIEN_CHINH if tt in TIEN_TE else None) if moi else tt  # tiền chính: tổng, ghi đè, lịch, bằng chữ
    thieu, canh_bao, chan, loi = [], [], [], []
    if tt is None:
        thieu.append({"ma": "THIEU_TIEN_TE", "truong": "gia.tien_te"})
    fx = d.get("fx")
    fxv = None
    if moi and tt == "VND":
        fxv = Fraction(1)  # tỷ giá khóa = 1
        if fx and fx.get("ty_gia") is not None and Fraction(Decimal(fx["ty_gia"])) != 1:
            loi.append({"ma": "VND_TY_GIA_KHAC_1", "truong": "fx.ty_gia",
                        "thong_bao": "Báo giá VND có tỷ giá cố định bằng 1 — không nhập tỷ giá khác."})
    elif tt == "USD" and fx:
        fxv = Fraction(Decimal(fx["ty_gia"]))
    # Ưu tiên ghi đè tường minh, rồi tổng typed cũ (tương thích); thiếu cả hai mới lấy phép tính. v2: cả hai đều là VND (tiền chính).
    ghi_de = d.get("tong_gia_tri_ghi_de")
    loi_ghi_de = None
    if ghi_de is not None:
        loai, so, loi_ghi_de = _gia_tri_nhap(ghi_de)
        if loai == "PERCENT":
            loi_ghi_de = "Tổng giá trị ghi đè phải là số tiền, không nhận %."
        if not loi_ghi_de:
            ghi_de = so
    if loi_ghi_de:
        tong, e1 = None, "TONG_GIA_TRI_GHI_DE_SAI"
        loi.append({"ma": e1, "truong": "tong_gia_tri_ghi_de", "thong_bao": loi_ghi_de})
    else:
        tong, e1 = _minor(ghi_de if ghi_de is not None else g["tong"], tc)
    if e1 == "NGOAI_MIEN":
        loi.append({"ma": "TONG_NGOAI_MIEN", "truong": "tong_gia_tri_ghi_de" if ghi_de is not None else "gia.tong",
                    "thong_bao": f"Tổng giá trị phải lớn hơn 0 và không quá {_tien_vn(TIEN_TOI_DA_MINOR, tc)}."})
    elif e1 and not loi_ghi_de:
        loi.append({"ma": "TONG_KHONG_DUNG_SCALE", "truong": "tong_gia_tri_ghi_de" if ghi_de is not None else "gia.tong"})
    tich, f_tich = None, None
    if tt and g["don_gia"] and g["dien_tich"]:
        if moi:
            if fxv is not None:
                f_tich = Fraction(Decimal(g["don_gia"])) * fxv * Fraction(Decimal(g["dien_tich"]))  # VND chính xác, chưa làm tròn
                tich = lam_tron_nua_len(f_tich)  # làm tròn đến đồng, đúng nửa làm tròn lên
        else:
            f = Fraction(Decimal(g["don_gia"])) * Fraction(Decimal(g["dien_tich"])) * 10 ** R.SCALE[tt]
            if f.denominator != 1:
                loi.append({"ma": "DON_GIA_X_DIEN_TICH_KHONG_DUNG_SCALE", "truong": "gia.don_gia"})
            else:
                tich = f.numerator
    if tong is None and tich is not None and not e1:
        tong = tich
    elif tong is not None and tich is not None and tong != tich:
        cong_thuc = "đơn giá × tỷ giá × diện tích" if moi and tt == "USD" else "đơn giá × diện tích"
        canh_bao.append({"ma": "TONG_LECH_DON_GIA_X_DIEN_TICH", "truong": "tong_gia_tri_ghi_de",
                         "thong_bao": f"Khác tính toán: {_tien_vn(tong, tc)}; {cong_thuc} = {_tien_vn(tich, tc)}.",
                         "tong_tinh_minor": str(tich), "tong_ghi_de_minor": str(tong)})
    if tong is None and not e1:
        thieu.append({"ma": "THIEU_TONG_GIA_TRI", "truong": "gia.tong"})
    # Miền tổng = miền của bước Ký (M0030 TONG_NGOAI_MIEN): 0 < tổng ≤ TIEN_TOI_DA_MINOR. Ngoài miền → lỗi theo trường, chặn In/Chuyển; lịch
    # không tính trên tổng ngoài miền (như SQL: tổng NULL → đợt CHUA_CO_TONG); giá trị đã khai vẫn trả để màn hình hiện.
    truong_tong = "tong_gia_tri_ghi_de" if ghi_de is not None else "gia.tong" if g["tong"] is not None else "gia.don_gia"
    tong_trong_mien = tong is not None and 0 < tong <= TIEN_TOI_DA_MINOR
    if tong is not None and not tong_trong_mien:
        loi.append({"ma": "TONG_NGOAI_MIEN", "truong": truong_tong,
                    "thong_bao": f"Tổng giá trị phải lớn hơn 0 và không quá {_tien_vn(TIEN_TOI_DA_MINOR, tc)}."})
    tong_lich = tong if tong_trong_mien else None
    bang_chu = None
    if tong_trong_mien:
        try:
            bang_chu = R.bang_chu(tong, tc)
        except R.LoiRender:
            loi.append({"ma": "TONG_BANG_CHU_KHONG_DOC_DUOC", "truong": truong_tong,
                        "thong_bao": "Không đọc được Tổng giá trị thành chữ — kiểm lại tổng giá trị."})
    if g["co_so_thue"] is None:
        thieu.append({"ma": "THIEU_CO_SO_THUE", "truong": "gia.co_so_thue"})
    if not d["khach"]["doi_tac_id"]:
        canh_bao.append({"ma": "KHACH_CHUA_MA", "thong_bao": "Khách chưa có mã Junsky — lưu dự thảo, không tự cấp mã."})
        if not (d["khach"]["du_thao"] or {}).get("ten"):
            thieu.append({"ma": "THIEU_KHACH", "truong": "khach"})
    if not d["don_vi"]["ma"]:
        thieu.append({"ma": "THIEU_LO_CAN", "truong": "don_vi.ma"})
    else:
        canh_bao.append({"ma": "LO_CAN_CHUA_CO_CAN_CU", "thong_bao": "Lô/căn nhập tay — chưa có nguồn lô/căn/diện tích/trạng thái đủ kiểu."})
    if not d["lich"]:
        thieu.append({"ma": "THIEU_LICH", "truong": "lich"})
    if tt == "USD" and fx is None:
        chan.append({"ma": "USD_THIEU_FX", "truong": "fx.ty_gia",
                     "thong_bao": "Báo giá USD cần tỷ giá USD/VND để tính Tổng giá trị (VND) trước khi in." if moi
                     else "Báo giá USD cần tỷ giá tham chiếu nhập tay trước khi in."})
    co_phi_nhap = bool(d.get("phi_bao_tri") and d["phi_bao_tri"]["gia_tri"] is not None)
    if co_phi and not co_phi_nhap:
        thieu.append({"ma": "THIEU_PHI_QUAN_LY_BAO_TRI", "truong": "phi_bao_tri.gia_tri"})
    dong, tong_tl, tong_tien, du = [], Fraction(0), 0, True
    for i, r in enumerate(d["lich"], start=1):
        x = {"dong_id": r["dong_id"], "dong": i, "so_tien_minor": None, "ty_le": None, "loi": [], "loi_chi_tiet": [],
             "ty_le_xap_xi": False, "ty_le_hien_thi": None,
             "nguon_nhap": {"PERCENT": "TY_LE", "AMOUNT": "SO_TIEN"}.get(r["loai"]),
             "moc_hien_thi": _moc(r), "moc_ngay_hien_thi": _ngay_vn(r["moc_ngay"])}
        loi_nhap = _gia_tri_nhap(r["gia_tri_nhap"])[2] if "gia_tri_nhap" in r else None
        if loi_nhap:
            x["loi"].append("GIA_TRI_NHAP_SAI")
            x["loi_chi_tiet"].append({"ma": "GIA_TRI_NHAP_SAI", "dong": i, "truong": f"lich.{i - 1}.gia_tri_nhap",
                                      "thong_bao": f"Dòng {i}: {loi_nhap}"})
        elif r["loai"] is None:
            x["loi"].append("CHUA_CO_GIA_TRI")
        elif r["loai"] == "PERCENT":
            if r["ty_le"] is None:
                x["loi"].append("CHUA_CO_TY_LE")
            else:
                tl = Fraction(Decimal(r["ty_le"]))
                x["ty_le"] = r["ty_le"]
                tong_tl += tl
                if tong_lich is None:
                    x["loi"].append("CHUA_CO_TONG")
                else:
                    f = Fraction(tong_lich) * tl / TRAM
                    if f.denominator != 1:
                        x["loi"].append("KHONG_BIEU_DIEN_DUNG_SCALE")
                    else:
                        x["so_tien_minor"] = str(f.numerator)
                        tong_tien += f.numerator
        else:
            if r["tien_te"] is not None and r["tien_te"] != tc:
                x["loi"].append("KHAC_TIEN_TE")  # không cộng USD + VND
            mi, e = _minor(r["so_tien"], tc)
            if r["so_tien"] is None:
                x["loi"].append("CHUA_CO_SO_TIEN")
            elif e:
                x["loi"].append("SO_TIEN_KHONG_DUONG" if e == "NGOAI_MIEN" else e)
            elif mi is None:
                x["loi"].append("CHUA_CO_TIEN_TE")
            else:
                x["so_tien_minor"] = str(mi)
                tong_tien += mi
                if tong_lich:
                    tl = Fraction(mi) * TRAM / Fraction(tong_lich)
                    tong_tl += tl
                    x["ty_le"] = _frac_str(tl)  # None vẫn giữ nghĩa không biểu diễn chính xác trong 12 chữ số lẻ.
                    x["ty_le_xap_xi"] = x["ty_le"] is None
                    x["ty_le_hien_thi"] = _ty_le_vn(tl, xap_xi=x["ty_le_xap_xi"])
                else:
                    x["loi"].append("CHUA_CO_TONG")
        # Miền tiền từng đợt = M0030 (SO_TIEN_KHONG_DUONG): 0 < tiền đợt ≤ TIEN_TOI_DA_MINOR
        if x["so_tien_minor"] is not None and not 0 < int(x["so_tien_minor"]) <= TIEN_TOI_DA_MINOR:
            x["loi"].append("SO_TIEN_KHONG_DUONG")
        # FIX01 #8: mốc trống (chưa chọn loại, hoặc đã chọn NGAY/SU_KIEN mà giá trị NULL/rỗng) luôn chỉ là CẢNH BÁO — giữ NULL, không tự tạo ngày
        if r["moc_loai"] is None or (r["moc_loai"] == "NGAY" and not r["moc_ngay"]) or (r["moc_loai"] == "SU_KIEN" and not r["moc_su_kien"]):
            canh_bao.append({"ma": "MOC_TRONG", "dong": i, "thong_bao": f"Dòng {r['lan']}: chưa có mốc thời gian/sự kiện (chỉ cảnh báo)."})
        for ma in x["loi"]:
            if ma != "GIA_TRI_NHAP_SAI":
                msg = {"CHUA_CO_GIA_TRI": "Chưa nhập giá trị.", "CHUA_CO_TY_LE": "Chưa nhập tỷ lệ.",
                       "CHUA_CO_SO_TIEN": "Chưa nhập số tiền.", "CHUA_CO_TONG": "Chưa có tổng giá trị để tính.",
                       "CHUA_CO_TIEN_TE": "Chưa chọn tiền tệ báo giá để tính số tiền.",
                       "KHAC_TIEN_TE": "Tiền tệ dòng lịch khác tiền chính của báo giá.",
                       "SO_TIEN_KHONG_DUONG": "Số tiền đợt phải lớn hơn 0 và không quá "
                                              + (_tien_vn(TIEN_TOI_DA_MINOR, tc) if tc else str(TIEN_TOI_DA_MINOR)) + "."}.get(
                           ma, "Số tiền không biểu diễn đúng đơn vị nhỏ nhất của tiền tệ; cần sửa giá trị.")
                x["loi_chi_tiet"].append({"ma": ma, "dong": i, "truong": f"lich.{i - 1}", "thong_bao": f"Dòng {i}: {msg}"})
        if x["loi"]:
            du = False
        dong.append(x)
    if d["lich"]:
        if not du:
            chan.append({"ma": "LICH_CHUA_TINH_DUOC", "thong_bao": "Có dòng lịch chưa có/không tính đúng scale — nhập giá trị/cơ sở hợp lệ."})
        elif any(x["nguon_nhap"] == "SO_TIEN" for x in dong) and tong_lich is not None and tong_tien != tong_lich:
            chan.append({"ma": "TONG_TIEN_LECH", "thong_bao": "Tổng tiền các đợt khác tổng giá trị."})
        elif tong_tl != TRAM:
            lech = TRAM - tong_tl
            chan.append({"ma": "TONG_TY_LE_KHAC_100", "thong_bao":
                         f"Tổng % = {_so_vn(_frac_str(tong_tl))}, {'thiếu' if lech > 0 else 'thừa'} {_so_vn(_frac_str(abs(lech)))}"})
        elif tong_lich is not None and tong_tien != tong_lich:
            chan.append({"ma": "TONG_TIEN_LECH", "thong_bao": "Tổng tiền các đợt khác tổng giá trị."})
    vnd = None  # dữ liệu cũ: VND chỉ tham chiếu của báo giá USD (tiền chính USD)
    if not moi and tt == "USD" and fx and tong is not None:
        vnd = {"tong": _frac_str(Fraction(tong, 100) * fxv, 14),
               "dong": [None if x["so_tien_minor"] is None else _frac_str(Fraction(int(x["so_tien_minor"]), 100) * fxv, 14) for x in dong]}
    usd = None  # v2: USD chỉ tham chiếu = đơn giá × diện tích, làm tròn đến cent (nửa lên)
    if moi and tt == "USD" and g["don_gia"] and g["dien_tich"]:
        f_usd = Fraction(Decimal(g["don_gia"])) * Fraction(Decimal(g["dien_tich"])) * 100
        mi = lam_tron_nua_len(f_usd)
        usd = {"tong_minor": str(mi), "tong": f"{mi // 100}.{mi % 100:02d}", "tong_hien_thi": R.tien_hien_thi(mi, "USD"),
               "lam_tron": f_usd != mi, "cong_thuc": "Đơn giá × diện tích (USD, chỉ tham chiếu)"}
    for i, x in enumerate(dong):
        x["so_tien"] = x["so_tien_minor"]  # alias minor cho BG-1b; giữ khóa cũ cho bên dùng hiện hành
        if x["ty_le"] is not None:
            x["ty_le_hien_thi"] = _so_vn(x["ty_le"]) + "%"
        x["so_tien_hien_thi"] = None if x["so_tien_minor"] is None or not tc else _tien_vn(int(x["so_tien_minor"]), tc)
        phan_con_lai = x["so_tien_hien_thi"] if x["nguon_nhap"] == "TY_LE" else x["ty_le_hien_thi"]
        x["hien_thi_mo"] = "= " + phan_con_lai if phan_con_lai else ""
        x["vnd_hien_thi"] = None
        if vnd and vnd["dong"][i] is not None:
            tr = _frac_str(Fraction(Decimal(vnd["dong"][i])) / 1000000, 20)
            x["vnd_hien_thi"] = "≈ " + _so_vn(tr) + " tr VND"
            x["hien_thi_mo"] += (" · " if x["hien_thi_mo"] else "") + x["vnd_hien_thi"]
    g7_lech = []
    if d["nguon_lich"] == "DU_AN":
        if not g7 or g7.get("trang_thai") != "HIEU_LUC":
            canh_bao.append({"ma": "THIEU_G7", "thong_bao": "Chưa có bộ chuẩn dự án hiệu lực — không so lệch, không coi là khớp."})
        else:
            rows = g7.get("rows") or []
            if len(rows) != len(d["lich"]):
                g7_lech.append({"ma": "LECH_G7_SO_DONG", "thong_bao": f"Bộ chuẩn có {len(rows)} đợt, báo giá có {len(d['lich'])} đợt."})
            for i, (a, b) in enumerate(zip(rows, dong), start=1):
                if a.get("gia_tri_loai") == "PERCENT":
                    if b["ty_le"] is None or Fraction(Decimal(b["ty_le"])) != Fraction(Decimal(a["gia_tri_thap_phan"])):
                        g7_lech.append({"ma": "LECH_G7_TY_LE", "dong": i, "thong_bao": f"Đợt {i}: chuẩn {a['gia_tri_thap_phan']}% — báo giá "
                                                                                     f"{b['ty_le'] or 'chưa có/không hữu hạn'}%."})
                elif a.get("gia_tri_loai") == "AMOUNT":
                    if a.get("tien_te") != tc or b["so_tien_minor"] != a.get("so_tien_minor"):
                        g7_lech.append({"ma": "LECH_G7_SO_TIEN", "dong": i, "thong_bao": f"Đợt {i}: chuẩn {a.get('so_tien_minor')} {a.get('tien_te')} "
                                                                                       f"(đơn vị nhỏ nhất) — báo giá {b['so_tien_minor'] or 'chưa có'} {tc or ''}."})
                if (a.get("moc_loai"), a.get("moc_ngay"), a.get("moc_su_kien")) != (d["lich"][i - 1]["moc_loai"], d["lich"][i - 1]["moc_ngay"],
                                                                                    d["lich"][i - 1]["moc_su_kien"]):
                    g7_lech.append({"ma": "LECH_G7_MOC", "dong": i, "thong_bao": f"Đợt {i}: mốc khác bộ chuẩn."})
            canh_bao.extend(g7_lech)
    if co_phi_nhap:
        _, e = _minor(d["phi_bao_tri"]["gia_tri"], d["phi_bao_tri"]["tien_te"])
        if d["phi_bao_tri"]["tien_te"] is None or e:
            chan.append({"ma": "PHI_BAO_TRI_KHONG_HOP_LE", "truong": "phi_bao_tri",
                         "thong_bao": "Phí bảo trì cần tiền tệ và giá trị đúng scale (giữ riêng, không gộp lịch)."})
    chan.extend({**l, "thong_bao": l.get("thong_bao") or "Không tính được đúng scale tiền tệ — nhập giá trị/cơ sở hợp lệ."} for l in loi)
    nhan_thieu = {"THIEU_TIEN_TE": "Chưa chọn tiền tệ báo giá.", "THIEU_TONG_GIA_TRI": "Chưa có tổng giá trị báo giá.",
                  "THIEU_LICH": "Chưa nhập lịch thanh toán.", "THIEU_CO_SO_THUE": "Chưa chọn cơ sở thuế.",
                  "THIEU_KHACH": "Chưa có thông tin khách hàng.", "THIEU_PHI_QUAN_LY_BAO_TRI": "Chưa nhập phí quản lý/bảo trì."}
    # Bước 1 — In sơ bộ: chỉ phần giá + lịch hợp lệ (+ tỷ giá khi USD). Bước 2 — Chuyển: thêm khách hàng + phí (khi loại hình có phí).
    chan_in = chan + [{"ma": t["ma"], "truong": t["truong"], "thong_bao": nhan_thieu[t["ma"]]} for t in thieu
                      if t["ma"] in ("THIEU_TIEN_TE", "THIEU_TONG_GIA_TRI", "THIEU_LICH", "THIEU_CO_SO_THUE")]
    chan_chuyen = chan_in + [{"ma": t["ma"], "truong": t["truong"], "thong_bao": nhan_thieu[t["ma"]]} for t in thieu
                             if t["ma"] in ("THIEU_KHACH", "THIEU_PHI_QUAN_LY_BAO_TRI")]
    ty_gia = None
    if moi and tt == "VND":
        ty_gia = {"gia_tri": "1", "hien_thi": "1", "khoa": True, "nguon": "CO_DINH_VND", "ngay": None, "ngay_hien_thi": None}
    elif tt == "USD" and fx:
        ty_gia = {"gia_tri": fx["ty_gia"], "hien_thi": _so_vn(fx["ty_gia"]), "khoa": False, "nguon": fx.get("nguon") or "NHAP",
                  "ngay": fx.get("ngay"), "ngay_hien_thi": _ngay_vn(fx.get("ngay"))}
    return {"tien_te": tc, "tien_te_don_gia": tt, "quy_uoc": quy_uoc_bao_gia(d)["ma"], "scale": R.SCALE.get(tc),
            "tong_minor": None if tong is None else str(tong), "dong": dong,
            "tong_ty_le": _frac_str(tong_tl) if d["lich"] else None, "tong_dong_minor": str(tong_tien) if d["lich"] else None,
            "tong_ty_le_khop": bool(d["lich"]) and du and tong_tl == TRAM,
            "tong_ty_le_hien_thi": _ty_le_vn(tong_tl, xap_xi=any(x["ty_le_xap_xi"] for x in dong)) if d["lich"] else None,
            "tong_tinh_minor": None if tich is None else str(tich), "tong_hien_thi": _tien_vn(tong, tc) if tong is not None and tc else None,
            "tong_bang_chu": bang_chu, "tong_lam_tron": f_tich is not None and f_tich != tich,
            "phep_tinh": _phep_tinh(g, tt, (fx or {}).get("ty_gia"), f_tich, tich) if f_tich is not None else None,
            "ty_gia": ty_gia, "usd_tham_chieu": usd,
            "tong_dong_hien_thi": _tien_vn(tong_tien, tc) if d["lich"] and tc else None,
            "tong_tien_khop": bool(d["lich"]) and du and tong is not None and tong_tien == tong,
            "ly_do_chan_in": "\n".join(x["thong_bao"] for x in chan_in), "ly_do_chan_chuyen": "\n".join(x["thong_bao"] for x in chan_chuyen),
            "vnd_tham_chieu": vnd, "thieu": thieu, "canh_bao": canh_bao, "g7_lech": g7_lech, "chan_in": chan_in, "chan_chuyen": chan_chuyen}


# ================================================================================================== giá trị trường hợp đồng (typed + hiển thị)
def chuan_hoa_truong(kieu: str, v):
    if v is None or v == "":
        return None
    if kieu == "text":
        return _str(v, "giá trị văn bản", 2000)
    if kieu == "ngay":
        return _ngay(v, "Giá trị ngày")
    if kieu == "so":
        return _so(v, "giá trị số")
    if kieu == "tien":
        v = _obj(v, "giá trị tiền", {"so_tien", "tien_te"})
        st, t = _so(v.get("so_tien"), "số tiền"), _chon(v.get("tien_te"), "tiền tệ", TIEN_TE)
        if st is None or t is None:
            _loi("CRM_GK_YEU_CAU_SAI", "Giá trị tiền cần số tiền + tiền tệ.")
        if _minor(st, t)[1]:
            _loi("CRM_GK_SO_SAI", "Số tiền không đúng scale tiền tệ (không làm tròn).")
        return {"so_tien": st, "tien_te": t}
    _loi("CRM_GK_KIEU_KHONG_HO_TRO", f"Kiểu trường '{kieu}' chưa hỗ trợ soạn.")


def hien_thi_truong(t: dict, v) -> str:
    """Chuỗi hiển thị của giá trị ĐÃ typed theo định dạng của danh mục; định dạng lạ → LoiRender (không xuất giả)."""
    if v is None:
        return ""
    k, dd = t["kieu"], t["dinh_dang"]
    if k == "text":
        if not dd.startswith("TEXT"):
            raise R.LoiRender("CRM_GK_DINH_DANG_KHONG_HO_TRO", f"Định dạng '{dd}' của trường văn bản chưa hỗ trợ.")
        return v
    if k == "ngay":
        return R.ngay_hien_thi(v, dd)
    if k == "so":
        s = v.split(".")
        return R.so_hien_thi(Fraction(Decimal(v)), len(s[1]) if len(s) > 1 else 0)
    if k == "tien":
        mi, _ = _minor(v["so_tien"], v["tien_te"])
        if dd in ("EXPLICIT_MINOR_AND_CURRENCY", "TIEN_DV"):
            return R.tien_hien_thi(mi, v["tien_te"])
        if dd == "TIEN":
            return R.tien_hien_thi(mi, v["tien_te"], kem_ma=False)
        if dd == "CHU":
            return R.bang_chu(mi, v["tien_te"])
    raise R.LoiRender("CRM_GK_DINH_DANG_KHONG_HO_TRO", f"Kiểu/định dạng '{k}/{dd}' chưa hỗ trợ xuất.")


def rang_buoc_tong(cau_hinh) -> dict | None:
    """FIX01 #7 — ràng buộc NGỮ NGHĨA của trường tổng canonical do profile loại hình đã khai (`cau_hinh.kiem_tong = {truong, co_so}`, vd
    gia_tri_hop_dong/TIEN_THUE_DAT_CHUA_VAT). Chỉ cơ sở '*_CHUA_VAT' được hiểu là NET đã khai; cơ sở khác → không suy NET/GROSS/VAT."""
    kt = (cau_hinh or {}).get("kiem_tong") if isinstance(cau_hinh, dict) else None
    if not isinstance(kt, dict) or not kt.get("truong") or not kt.get("co_so"):
        return None
    return {"truong": kt["truong"], "co_so": kt["co_so"], "co_so_thue": "NET" if str(kt["co_so"]).endswith("_CHUA_VAT") else None}


def kiem_tong_canonical(rb: dict | None, gia_tri_truong: dict, bao_gia: dict, tinh: dict, truong_dung: set) -> tuple[list, list]:
    """(chặn, cảnh báo): trường tổng canonical đã ánh xạ phải CÙNG tiền tệ/số tiền với tổng báo giá/lịch và cùng cơ sở thuế đã khai; không gán khoản
    tiền khác thành tổng, không tự suy VAT. Thiếu ràng buộc → cảnh báo rõ (không tự điền)."""
    chan, cb = [], []
    if rb is None:
        cb.append({"ma": "CHUA_CO_RANG_BUOC_TONG", "thong_bao": "Profile loại hình chưa khai trường tổng canonical/cơ sở — không tự điền tổng vào mẫu."})
        return chan, cb
    if rb["truong"] not in truong_dung:
        return chan, cb
    v = (gia_tri_truong or {}).get(rb["truong"])
    if v is None:
        return chan, cb
    if rb["co_so_thue"] is None or (bao_gia.get("gia") or {}).get("co_so_thue") != rb["co_so_thue"]:
        chan.append({"ma": "CO_SO_TONG_KHONG_KHOP", "truong": rb["truong"],
                     "thong_bao": f"Trường {rb['truong']} có cơ sở {rb['co_so']} — khác cơ sở thuế đã khai của báo giá (không tự quy đổi NET/GROSS)."})
    else:
        mi, _ = _minor(v.get("so_tien"), v.get("tien_te"))
        if v.get("tien_te") != tinh.get("tien_te") or tinh.get("tong_minor") is None or mi != int(tinh["tong_minor"]):
            chan.append({"ma": "TONG_TRUONG_KHAC_TONG_LICH", "truong": rb["truong"],
                         "thong_bao": f"Trường {rb['truong']} khác tổng giá trị/lịch cùng cơ sở của bản soạn — không xuất văn bản mâu thuẫn."})
    return chan, cb


def _gia_tri_lich(r: dict, x: dict, tt: str | None) -> str:
    if r["loai"] == "PERCENT":
        s = _so_vn(r['ty_le']) + "%"
        return s + (f" — {R.tien_hien_thi(int(x['so_tien_minor']), tt)}" if x["so_tien_minor"] is not None and tt else "")
    if r["loai"] == "AMOUNT" and x["so_tien_minor"] is not None and tt:
        return R.tien_hien_thi(int(x["so_tien_minor"]), tt)
    return ""


def _moc(r: dict) -> str:
    """Diễn đạt mốc TRUNG THỰC — mốc trống in là chưa xác định (không TypeError, không tự gán ngày/hạn)."""
    if r.get("moc_loai") == "NGAY":
        return "Ngày " + R.ngay_hien_thi(r["moc_ngay"], "dd/MM/yyyy") if r.get("moc_ngay") else "Ngày: chưa xác định"
    if r.get("moc_loai") == "SU_KIEN":
        return nhan_moc_su_kien(r.get("moc_su_kien"))
    return "Chưa xác định"


class CrmGiaoKetK2:
    """G2/G3 trên cùng service G1/G7 (CrmMauK2): cùng kết nối chủ bảng, cùng giao dịch có danh tính, cùng biên nhận."""

    def __init__(self, mau: CrmMauK2):
        self.mau = mau
        self.kho = Path(mau.root) / "giao-ket"

    # ------------------------------------------------------------------ hạ tầng
    def _tra(self, c, hanh: str, khoa: str, dich: str, h: str):
        r = _v(dict(c.execute("SELECT master.crm_gk_tra(%s, %s, %s::uuid, %s) AS r", (hanh, khoa, dich, h)).fetchone()))["r"]
        return None if r is None else {**r["ket_qua"], "lap_lai": True}

    @staticmethod
    def _kq(row) -> dict:
        r = _v(dict(row))["r"]
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    def _bao_gia(self, c, bao_gia_id: str) -> dict:
        b = self.mau._mot(c, """SELECT b.*, r.du_lieu, r.tinh, r.g7, r.du_an_id, r.doi_tac_id, r.du_lieu_sha256, r.tao_boi AS rev_boi, r.tao_luc AS rev_luc,
                                       (SELECT d.ten_phap_ly FROM master.doi_tac d WHERE d.id = r.doi_tac_id) AS khach_ten
                                FROM master.crm_bao_gia b JOIN master.crm_bao_gia_rev r ON r.bao_gia_id = b.id AND r.revision = b.revision_hien_hanh
                                WHERE b.id = %s::uuid AND master.crm_gk_duoc('CRM_BAO_GIA', b.phap_nhan_id)""", (_uuid(bao_gia_id, "bao_gia_id"),))
        if b is None:
            _loi("CRM_G_KHONG_THAY", "Không thấy báo giá (hoặc ngoài phạm vi).")
        return b

    def _trung_don_vi(self, c, pn, d: dict, tru_soan=None) -> list:
        if not d["don_vi"]["ma"]:
            return []
        n = self.mau._mot(c, """SELECT count(*) AS n FROM master.crm_hd_soan s JOIN master.crm_hd_soan_rev r ON r.soan_id = s.id AND r.revision = s.revision_hien_hanh
                                WHERE s.phap_nhan_id = %s AND r.du_lieu -> 'bao_gia' -> 'don_vi' ->> 'ma' = %s
                                  AND (r.du_lieu -> 'bao_gia' ->> 'du_an_id') IS NOT DISTINCT FROM %s AND s.id IS DISTINCT FROM %s::uuid""",
                          (pn, d["don_vi"]["ma"], d["du_an_id"], tru_soan))["n"]
        return [{"ma": "LO_CAN_DA_CO_BAN_SOAN", "thong_bao": f"Lô/căn {d['don_vi']['ma']} đã có {n} bản soạn hợp đồng khác (chỉ cảnh báo)."}] if n else []

    # ------------------------------------------------------------------ BG-1c tỷ giá USD/VND mặc định (cấu hình chung master.cau_hinh)
    @staticmethod
    def _can_fx_mac_dinh(d: dict) -> bool:
        return d["gia"]["tien_te"] == "USD" and not d.get("fx")

    def _doc_ty_gia(self, c) -> dict:
        """Dòng hiện hành của khóa chung (phap_nhan_id NULL, valid_to NULL); chưa có/giá trị hỏng → 26.000 của phần mềm (nguon PHAN_MEM)."""
        r = self.mau._mot(c, """SELECT id, gia_tri, nguoi_duyet, (valid_from AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS ngay FROM master.cau_hinh
                                WHERE khoa = %s AND phap_nhan_id IS NULL AND valid_to IS NULL ORDER BY valid_from DESC LIMIT 1""",
                          (KHOA_TY_GIA_MAC_DINH,))
        tg = r["gia_tri"].get("ty_gia") if r and isinstance(r.get("gia_tri"), dict) else None
        if isinstance(tg, str) and RE_SO.fullmatch(tg) and Fraction(Decimal(tg)) > 0:
            return {"ty_gia": tg, "hien_thi": _so_vn(tg), "nguon": "CAU_HINH", "ap_dung_tu": r["ngay"], "ap_dung_tu_hien_thi": _ngay_vn(r["ngay"]),
                    "nguoi_sua": r["nguoi_duyet"], "id": r["id"]}
        return {"ty_gia": TY_GIA_USD_MAC_DINH_PHAN_MEM, "hien_thi": _so_vn(TY_GIA_USD_MAC_DINH_PHAN_MEM), "nguon": "PHAN_MEM", "ap_dung_tu": None,
                "ap_dung_tu_hien_thi": None, "nguoi_sua": None, "id": None}

    def _fx_mac_dinh(self, c, truoc: dict | None = None) -> dict:
        """Tỷ giá khi báo giá USD không gửi tỷ giá: báo giá ĐÃ LƯU (USD, có tỷ giá) giữ tỷ giá đã lưu; báo giá mới nhận mặc định chung hiện hành."""
        fx_cu = (truoc or {}).get("fx") if ((truoc or {}).get("gia") or {}).get("tien_te") == "USD" else None
        if isinstance(fx_cu, dict) and fx_cu.get("ty_gia"):
            return {"ty_gia": fx_cu["ty_gia"], "ngay": fx_cu.get("ngay"), "nguon": fx_cu.get("nguon")}
        x = self._doc_ty_gia(c)
        return {"ty_gia": x["ty_gia"], "ngay": x["ap_dung_tu"], "nguon": "MAC_DINH"}

    def _quyen_ty_gia(self, c) -> dict:
        """Đọc: phiên có quyền báo giá ở ít nhất một pháp nhân. Sửa: vai kế toán/kế toán trưởng có module CRM ở ít nhất một pháp nhân."""
        q = self.mau._mot(c, """SELECT coalesce(bool_or(master.crm_gk_duoc('CRM_BAO_GIA', p.id)), false) AS doc,
                                       coalesce(bool_or(master.ktt_duoc(p.id, 'CRM') AND master.ktt_co_vai(p.id, %s::text[], NULL)), false) AS sua
                                FROM master.phap_nhan p""", (list(VAI_SUA_CAU_HINH),))
        return {"doc": bool(q and q["doc"]), "sua": bool(q and q["sua"])}

    def ty_gia_mac_dinh(self, dang_nhap: str) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt, rr=True) as c:
            q = self._quyen_ty_gia(c)
            if not q["doc"]:
                _loi("CRM_G_KHONG_CO_QUYEN", "Phiên không có quyền xem cấu hình báo giá.")
            x = self._doc_ty_gia(c)
        x.pop("id")
        return {**x, "cap": "USD/VND", "khoa": KHOA_TY_GIA_MAC_DINH, "duoc_sua": q["sua"]}

    def sua_ty_gia_mac_dinh(self, dang_nhap: str, *, ty_gia, ly_do=None) -> dict:
        """Kế toán sửa tỷ giá mặc định chung (QD-20261025-04): đóng dòng cũ (valid_to) + thêm dòng mới + nhật ký `nhat_ky.su_kien`, cùng giao dịch.
        Nhận số kiểu Việt ("26.000", "25.950,5"); cùng giá trị đang dùng → không ghi. Báo giá đã lưu giữ tỷ giá của nó."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        loai, so, loi = _gia_tri_nhap(ty_gia) if ty_gia is not None else (None, None, "Chưa nhập tỷ giá.")
        if loi or loai != "AMOUNT" or so is None or Fraction(Decimal(so)) <= 0:
            _loi("CRM_GK_FX_SAI", "Tỷ giá phải là số dương kiểu Việt (vd 26.000 hoặc 25.950,5), không có %." if not loi else loi)
        tg = _frac_str(Fraction(Decimal(so)))
        ly = _str(ly_do, "lý do", 1000)
        with m._tx(dt) as c:
            q = self._quyen_ty_gia(c)
            if not q["sua"]:
                _loi("CRM_G_KHONG_CO_QUYEN", "Chỉ kế toán/kế toán trưởng được sửa tỷ giá mặc định của báo giá.")
            c.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (KHOA_TY_GIA_MAC_DINH,))
            cu = self._doc_ty_gia(c)
            doi = not (cu["nguon"] == "CAU_HINH" and Fraction(Decimal(cu["ty_gia"])) == Fraction(Decimal(tg)))
            if doi:
                if cu["id"]:
                    c.execute("UPDATE master.cau_hinh SET valid_to = now() WHERE id = %s::uuid AND valid_to IS NULL", (cu["id"],))
                moi = c.execute("""INSERT INTO master.cau_hinh (khoa, phap_nhan_id, gia_tri, mo_ta, nguoi_duyet) VALUES (%s, NULL, %s::jsonb, %s, %s)
                                   RETURNING id""", (KHOA_TY_GIA_MAC_DINH, json.dumps({"cap": "USD/VND", "ty_gia": tg}),
                                                     "Tỷ giá USD/VND mặc định cho báo giá USD mới (CRM · Báo giá)", dt["dang_nhap"])).fetchone()
                c.execute("""INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, truoc, sau, ly_do)
                             VALUES (NULL, %s, 'HE_THONG', 'master.cau_hinh', %s::uuid, 'CRM_CAU_HINH_TY_GIA_MAC_DINH', %s::jsonb, %s::jsonb, %s)""",
                          (dt["dang_nhap"], str(moi["id"]), json.dumps({"ty_gia": cu["ty_gia"], "nguon": cu["nguon"]}),
                           json.dumps({"ty_gia": tg, "khoa": KHOA_TY_GIA_MAC_DINH}), ly or "Sửa tỷ giá mặc định của báo giá"))
            x = self._doc_ty_gia(c)
        x.pop("id")
        return {**x, "cap": "USD/VND", "khoa": KHOA_TY_GIA_MAC_DINH, "duoc_sua": True, "da_doi": doi}

    # ------------------------------------------------------------------ G2 đọc
    def danh_sach(self, dang_nhap: str) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt, rr=True) as c:
            loai = m._nhieu(c, """SELECT l.id, l.ma, l.ten, l.phien_ban, p.ma AS phap_nhan, p.ten AS phap_nhan_ten FROM master.loai_hinh_doanh_thu l
                                  JOIN master.phap_nhan p ON p.id = l.phap_nhan_id
                                  WHERE l.valid_to IS NULL AND master.crm_gk_duoc('CRM_BAO_GIA', l.phap_nhan_id) ORDER BY p.ma, l.ma""")
            du_an = m._nhieu(c, """SELECT a.id, a.ma_junsky, a.ten, p.ma AS phap_nhan, p.ten AS phap_nhan_ten FROM master.du_an a JOIN master.phap_nhan p ON p.id = a.phap_nhan_id
                                   WHERE master.crm_gk_duoc('CRM_BAO_GIA', a.phap_nhan_id) ORDER BY p.ma, a.ma_junsky""")
            khach = m._nhieu(c, """SELECT d.id, d.ten_phap_ly AS ten, j.object_id_junsky AS ma, p.ma AS phap_nhan, p.ten AS phap_nhan_ten FROM master.doi_tac d
                                   JOIN master.doi_tac_ma_junsky j ON j.doi_tac_id = d.id AND j.valid_to IS NULL JOIN master.phap_nhan p ON p.id = j.phap_nhan_id
                                   WHERE master.crm_gk_duoc('CRM_BAO_GIA', j.phap_nhan_id) ORDER BY d.ten_phap_ly LIMIT 500""")
            bg = m._nhieu(c, """SELECT b.id, b.so_bao_gia, b.ngay, b.trang_thai, b.tao_boi, b.revision_hien_hanh, p.ma AS phap_nhan, l.ma AS loai_hinh,
                                       p.ten AS phap_nhan_ten, l.ten AS loai_hinh_ten, a.ma_junsky AS du_an, a.ten AS du_an_ten,
                                       r.du_lieu, r.tinh, (SELECT d.ten_phap_ly FROM master.doi_tac d WHERE d.id = r.doi_tac_id) AS khach_ten,
                                       (SELECT s.id FROM master.crm_hd_soan s WHERE s.bao_gia_id = b.id) AS soan_id
                                FROM master.crm_bao_gia b JOIN master.crm_bao_gia_rev r ON r.bao_gia_id = b.id AND r.revision = b.revision_hien_hanh
                                JOIN master.phap_nhan p ON p.id = b.phap_nhan_id JOIN master.loai_hinh_doanh_thu l ON l.id = b.loai_hinh_id
                                LEFT JOIN master.du_an a ON a.id = r.du_an_id AND a.phap_nhan_id = b.phap_nhan_id
                                WHERE master.crm_gk_duoc('CRM_BAO_GIA', b.phap_nhan_id) ORDER BY b.tao_luc DESC LIMIT 200""")
            soan = m._nhieu(c, """SELECT s.id, s.trang_thai, s.revision_hien_hanh, h.ma_noi_bo, b.so_bao_gia, p.ma AS phap_nhan, s.cap_nhat_luc
                                  FROM master.crm_hd_soan s JOIN master.hop_dong h ON h.id = s.hop_dong_id JOIN master.crm_bao_gia b ON b.id = s.bao_gia_id
                                  JOIN master.phap_nhan p ON p.id = s.phap_nhan_id
                                  WHERE master.crm_gk_duoc('CRM_SOAN', s.phap_nhan_id) ORDER BY s.cap_nhat_luc DESC LIMIT 200""")
        out = []
        for b in bg:
            d, t = b.pop("du_lieu"), b.pop("tinh")
            ten = b.pop("khach_ten") or ((d.get("khach") or {}).get("du_thao") or {}).get("ten")
            tong = t.get("tong_minor")
            out.append({**b, "ngay_hien_thi": _ngay_vn(b["ngay"]), "het_han_hien_thi": _ngay_vn(d.get("het_han")),
                        "khach": ten, "lo_can": (d.get("don_vi") or {}).get("ma"), "tien_te": t.get("tien_te"),
                        "tong_hien_thi": R.tien_hien_thi(int(tong), t["tien_te"]) if tong is not None and t.get("tien_te") else None})
        return {"nguoi": {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"]}, "loai_hinh": loai, "du_an": du_an, "khach": khach,
                "bao_gia": out, "soan": soan, "ghi_nguon": {"san_sang": m.conn_tin_cay is not None}}

    def chi_tiet(self, dang_nhap: str, bao_gia_id) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt, rr=True) as c:
            b = self._bao_gia(c, bao_gia_id)
            rev = m._nhieu(c, "SELECT revision, tao_boi, tao_luc, du_lieu_sha256 FROM master.crm_bao_gia_rev WHERE bao_gia_id = %s ORDER BY revision", (b["id"],))
            xuat = m._nhieu(c, """SELECT id, revision, trang_thai, docx_len, pdf_len, ly_do, tao_boi, tao_luc FROM master.crm_gk_xuat
                                  WHERE bao_gia_id = %s ORDER BY tao_luc""", (b["id"],))
            mau = m._mot(c, "SELECT master.crm_gk_mau_hieu_luc(%s::uuid) AS r", (b["loai_hinh_id"],))["r"]
            soan = m._mot(c, "SELECT id FROM master.crm_hd_soan WHERE bao_gia_id = %s", (b["id"],))
        return {"bao_gia": {k: b[k] for k in ("id", "so_bao_gia", "ngay", "trang_thai", "tao_boi", "tao_luc", "revision_hien_hanh", "loai_hinh_id",
                                               "hop_dong_id", "huy_ly_do", "huy_boi")},
                "du_lieu": b["du_lieu"], "tinh": b["tinh"], "g7": b["g7"], "khach_ten": b["khach_ten"], "revisions": rev, "xuat": xuat,
                "mau_hieu_luc": mau, "soan_id": soan["id"] if soan else None,
                "quy_uoc": quy_uoc_bao_gia(b["du_lieu"])}  # BG-1c: dữ liệu cũ (USD là tiền chính) đọc nguyên nghĩa cũ, kèm ghi chú cho màn hình

    def xem_truoc(self, dang_nhap: str, *, du_lieu) -> dict:
        """FIX01 #4 — tính thử CHỈ ĐỌC trên form chưa lưu: cùng chuẩn hóa + phép tính typed chính xác của service (không engine thứ hai, không ghi);
        quyền hiện hành trên PN của loại hình kiểm trong giao dịch RR; G7 đọc trong cùng giao dịch. Trả {tinh, du_lieu_sha256} để UI ghép đúng form,
        cùng nhan (mã/tên pháp nhân, loại hình, dự án) và ngày hiển thị Việt; số typed giữ nguyên, chuỗi *_hien_thi/hien_thi_mo dùng định dạng Việt.
        BG-1c: báo giá USD chưa gửi tỷ giá → nhận tỷ giá mặc định chung (cùng giao dịch); `tinh` có Tổng VND, bằng chữ, phép tính, USD tham chiếu,
        `chan_in` (In sơ bộ) và `chan_chuyen` (thêm khách/phí theo profile loại hình)."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        hom_nay = m.hom_nay().isoformat()
        d = chuan_hoa_bao_gia(du_lieu, hom_nay=hom_nay)
        with m._tx(dt, rr=True) as c:
            ok = m._mot(c, """SELECT master.crm_gk_duoc('CRM_BAO_GIA', l.phap_nhan_id) AS ok, l.phap_nhan_id,
                                    p.ma AS phap_nhan, p.ten AS phap_nhan_ten, l.ma AS loai_hinh, l.ten AS loai_hinh_ten, l.cau_hinh
                             FROM master.loai_hinh_doanh_thu l JOIN master.phap_nhan p ON p.id = l.phap_nhan_id WHERE l.id = %s""",
                        (d["loai_hinh_id"],))
            if not ok or not ok["ok"]:
                _loi("CRM_G_KHONG_THAY", "Không thấy loại hình (hoặc ngoài phạm vi).")
            du_an = None
            if d["du_an_id"]:
                du_an = m._mot(c, """SELECT a.ma_junsky AS ma, a.ten FROM master.du_an a
                                       WHERE a.id = %s AND a.phap_nhan_id = %s AND master.crm_gk_duoc('CRM_BAO_GIA', a.phap_nhan_id)""",
                               (d["du_an_id"], ok["phap_nhan_id"]))
                if du_an is None:
                    _loi("CRM_G_KHONG_THAY", "Không thấy dự án (hoặc ngoài phạm vi pháp nhân báo giá).")
            if self._can_fx_mac_dinh(d):
                d = chuan_hoa_bao_gia(du_lieu, fx_mac_dinh=self._fx_mac_dinh(c), hom_nay=hom_nay)
            g7 = None
            if d["nguon_lich"] == "DU_AN" and d["du_an_id"] and d["giai_doan_g7"]:
                g7 = c.execute("SELECT master.crm_g_chuan_doc(%s::uuid, %s, %s::date) AS r", (d["du_an_id"], d["giai_doan_g7"],
                                                                                             m.hom_nay().isoformat())).fetchone()["r"]
        co_phi = loai_hinh_co_phi(ok.get("cau_hinh"))
        return {"tinh": tinh_bao_gia(d, g7, co_phi=co_phi), "du_lieu_sha256": sha256(canonical_json(d).encode("utf-8")),
                "nhan": {"phap_nhan": {"ma": ok["phap_nhan"], "ten": ok["phap_nhan_ten"]},
                         "loai_hinh": {"ma": ok["loai_hinh"], "ten": ok["loai_hinh_ten"]}, "du_an": du_an},
                "het_han_hien_thi": _ngay_vn(d["het_han"]), "fx_ngay_hien_thi": _ngay_vn((d["fx"] or {}).get("ngay")),
                "fx": d["fx"], "co_phi": co_phi}

    # ------------------------------------------------------------------ G2 lệnh
    def luu(self, dang_nhap: str, *, bao_gia_id, expected_revision, du_lieu, khoa) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        d0, khoa = chuan_hoa_bao_gia(du_lieu), _khoa(khoa)  # H theo yêu cầu gốc: không phụ thuộc cấu hình tỷ giá/ngày máy chủ
        _chan_ty_gia_vnd(d0)
        bg = _uuid_hoac_none(bao_gia_id, "bao_gia_id")
        if bg is not None and type(expected_revision) is not int:
            _loi("CRM_GK_YEU_CAU_SAI", "Cần revision mong đợi khi lưu báo giá đã có.")
        hanh = "CRM_BAO_GIA_LUU" if bg else "CRM_BAO_GIA_TAO"
        h = _h(hanh, {"bao_gia_id": bg, "expected_revision": expected_revision, "du_lieu": d0})
        with m._tx(dt, rr=True) as c:  # RR: G7 đọc để tính và G7 hàm lệnh đọc lại là CÙNG snapshot
            cu = self._tra(c, hanh, khoa, bg or d0["loai_hinh_id"], h)
            if cu is not None:
                return cu
            lh = m._mot(c, "SELECT phap_nhan_id, cau_hinh FROM master.loai_hinh_doanh_thu WHERE id = %s", (d0["loai_hinh_id"],))
            truoc = self._bao_gia(c, bg)["du_lieu"] if bg else None
            # BG-1c: USD không gửi tỷ giá → báo giá đã lưu giữ tỷ giá đã lưu; báo giá mới nhận mặc định chung đọc trong CÙNG giao dịch rồi LƯU
            # vào báo giá (đổi cấu hình sau không đổi báo giá đã lưu)
            d = chuan_hoa_bao_gia(du_lieu, fx_mac_dinh=self._fx_mac_dinh(c, truoc) if self._can_fx_mac_dinh(d0) else None,
                                  hom_nay=m.hom_nay().isoformat())
            for r in d["lich"]:  # row ID logic giữ qua revision/chuyển; dòng mới nhận ID máy chủ
                r["dong_id"] = r["dong_id"] or str(uuid.uuid4())
            if d["fx"]:  # người nhập/ngày nhập do máy chủ ghi; giữ nguyên khi tỷ giá không đổi
                fx_cu = (truoc or {}).get("fx")
                giu = fx_cu and (fx_cu.get("cap"), fx_cu.get("ty_gia"), fx_cu.get("ngay")) == (d["fx"]["cap"], d["fx"]["ty_gia"], d["fx"]["ngay"])
                d["fx"]["nguoi_nhap"] = fx_cu["nguoi_nhap"] if giu else dt["dang_nhap"]
                d["fx"]["nhap_ngay"] = fx_cu["nhap_ngay"] if giu else m.hom_nay().isoformat()
            g7 = None
            if d["nguon_lich"] == "DU_AN" and d["du_an_id"] and d["giai_doan_g7"]:
                g7 = c.execute("SELECT master.crm_g_chuan_doc(%s::uuid, %s, %s::date) AS r", (d["du_an_id"], d["giai_doan_g7"],
                                                                                             m.hom_nay().isoformat())).fetchone()["r"]
            tinh = tinh_bao_gia(d, g7, co_phi=loai_hinh_co_phi((lh or {}).get("cau_hinh")))
            tinh["canh_bao"].extend(self._trung_don_vi(c, lh and lh["phap_nhan_id"], d))
            kq = self._kq(c.execute("""SELECT master.crm_gk_bao_gia_luu(%s, %s, %s::uuid, %s::uuid, %s, %s::uuid, %s::uuid, %s::jsonb, %s::jsonb, %s::uuid,
                                                                          %s, %s::date, %s::jsonb) AS r""",
                                      (khoa, h, bg, d["loai_hinh_id"], expected_revision, d["du_an_id"], d["khach"]["doi_tac_id"],
                                       json.dumps(d, ensure_ascii=False), json.dumps(tinh, ensure_ascii=False),
                                       d["du_an_id"] if g7 is not None else None, d["giai_doan_g7"] if g7 is not None else None,
                                       m.hom_nay().isoformat() if g7 is not None else None, None if g7 is None else json.dumps(g7, ensure_ascii=False))).fetchone())
            lech = next((x for x in tinh["canh_bao"] if x["ma"] == "TONG_LECH_DON_GIA_X_DIEN_TICH"), None)
            if lech and not kq["lap_lai"]:
                # Cùng giao dịch với revision/biên nhận; replay (kể cả hàm SQL trả replay) không ghi thêm sự kiện.
                c.execute("""INSERT INTO nhat_ky.su_kien
                             (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, truoc, sau, ly_do)
                             SELECT b.phap_nhan_id, %s, 'DIEU_CHINH', 'master.crm_bao_gia', b.id, 'CRM_BAO_GIA_GHI_DE_TONG',
                                    %s::jsonb, %s::jsonb, %s FROM master.crm_bao_gia b WHERE b.id = %s::uuid""",
                          (dt["dang_nhap"], json.dumps(None if truoc is None else {"gia": truoc["gia"],
                              "tong_gia_tri_ghi_de": truoc.get("tong_gia_tri_ghi_de")}, ensure_ascii=False),
                           json.dumps({"revision": kq["revision"], "tien_te": tinh["tien_te"], "tong_tinh_minor": lech["tong_tinh_minor"],
                                       "tong_ghi_de_minor": lech["tong_ghi_de_minor"]}, ensure_ascii=False), lech["thong_bao"], kq["bao_gia_id"]))
            return kq

    def huy(self, dang_nhap: str, *, bao_gia_id, expected_revision, ly_do, khoa) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        bg, khoa = _uuid(bao_gia_id, "bao_gia_id"), _khoa(khoa)
        ly = _str(ly_do, "lý do hủy", 1000)
        if not ly or not ly.strip():
            _loi("CRM_GK_THIEU_LY_DO", "Hủy nháp cần lý do.")
        h = _h("CRM_BAO_GIA_HUY", {"bao_gia_id": bg, "expected_revision": expected_revision, "ly_do": ly})
        with m._tx(dt) as c:
            return self._kq(c.execute("SELECT master.crm_gk_bao_gia_huy(%s, %s, %s::uuid, %s, %s) AS r", (khoa, h, bg, expected_revision, ly)).fetchone())

    def chuyen(self, dang_nhap: str, *, bao_gia_id, expected_revision, mau_phien_ban_id, khoa) -> dict:
        """Báo giá → Soạn: cần quyền hiện hành, tổng lịch/FX hợp lệ theo TL 45 và mẫu hiệu lực tương thích."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        bg, mau, khoa = _uuid(bao_gia_id, "bao_gia_id"), _uuid(mau_phien_ban_id, "mau_phien_ban_id"), _khoa(khoa)
        h = _h("CRM_BAO_GIA_CHUYEN", {"bao_gia_id": bg, "expected_revision": expected_revision, "mau_phien_ban_id": mau})
        with m._tx(dt, rr=True) as c:
            cu = self._tra(c, "CRM_BAO_GIA_CHUYEN", khoa, bg, h)
            if cu is not None:
                return cu
            b = self._bao_gia(c, bg)
            cau_hinh = (m._mot(c, "SELECT cau_hinh FROM master.loai_hinh_doanh_thu WHERE id = %s", (b["loai_hinh_id"],)) or {}).get("cau_hinh")
            # Tính lại từ dữ liệu đã lưu (revision cũ có thể chưa có ly_do_chan_chuyen); BG-1c: bước 2 đòi khách + phí (theo profile loại hình).
            t = tinh_bao_gia(b["du_lieu"], b.get("g7"), co_phi=loai_hinh_co_phi(cau_hinh))
            if t["ly_do_chan_chuyen"]:
                _loi("CRM_GK_CHAN_CHUYEN", t["ly_do_chan_chuyen"])
            pin = c.execute("SELECT master.crm_gk_ghim_mau(%s::uuid, %s::uuid, %s::uuid) AS r", (b["phap_nhan_id"], b["loai_hinh_id"], mau)).fetchone()["r"]
            dm = {f["khoa"]: f for f in m._nhieu(c, """SELECT khoa, kieu, nguon FROM master.crm_danh_muc_truong WHERE loai_hinh_id = %s
                                                       AND danh_muc_ref = %s AND revision = %s""", (b["loai_hinh_id"], pin["danh_muc_ref"], pin["danh_muc_rev"]))}
            rb = rang_buoc_tong(cau_hinh)
            q = b["du_lieu"]
            gia_tri = {}
            # FIX01 #7: điền sẵn CHỈ trường tổng canonical đã khai (profile.kiem_tong), cùng cơ sở thuế đã khai, đúng số tiền typed — không áp mọi
            # trường tiền. BG-1c: số tiền là TIỀN CHÍNH của phép tính (v2: Tổng VND); mẫu/engine không đổi.
            if rb and rb["truong"] in dm and dm[rb["truong"]]["kieu"] == "tien" and rb["co_so_thue"] and q["gia"]["co_so_thue"] == rb["co_so_thue"] \
                    and t.get("tong_minor") is not None and t.get("tien_te"):
                gia_tri[rb["truong"]] = {"so_tien": _frac_str(Fraction(int(t["tong_minor"]), 10 ** R.SCALE[t["tien_te"]])), "tien_te": t["tien_te"]}
            # BG-1c: USD tham chiếu + tỷ giá chỉ khi danh mục của mẫu CÓ trường cùng mã và kiểu (không thêm trường, không đổi mẫu)
            if t.get("usd_tham_chieu") and (dm.get(TRUONG_HD_USD_THAM_CHIEU) or {}).get("kieu") == "tien":
                gia_tri[TRUONG_HD_USD_THAM_CHIEU] = {"so_tien": t["usd_tham_chieu"]["tong"], "tien_te": "USD"}
            if t.get("tien_te_don_gia") == "USD" and (t.get("ty_gia") or {}).get("gia_tri") and (dm.get(TRUONG_HD_TY_GIA) or {}).get("kieu") == "so":
                gia_tri[TRUONG_HD_TY_GIA] = t["ty_gia"]["gia_tri"]
            du_lieu = {"phien_ban_du_lieu": PHIEN_BAN_SOAN, "bao_gia": {k: v for k, v in q.items() if k != "phien_ban_du_lieu"},
                       "gia_tri_truong": gia_tri}
            return self._kq(c.execute("SELECT master.crm_gk_chuyen(%s, %s, %s::uuid, %s, %s::uuid, %s::jsonb, %s) AS r",
                                      (khoa, h, bg, expected_revision, mau, json.dumps(du_lieu, ensure_ascii=False), R.PHIEN_BAN_RENDERER)).fetchone())

    # ------------------------------------------------------------------ G3 đọc
    def _soan(self, c, soan_id: str) -> dict:
        s = self.mau._mot(c, """SELECT s.*, h.ma_noi_bo, h.so_hop_dong, r.du_lieu, r.mau_phien_ban_id, r.renderer, r.tao_boi AS rev_boi, r.tao_luc AS rev_luc,
                                       r.du_lieu_sha256, r.raw_sha256, r.ban_do_sha256, r.danh_muc_digest, r.profile_sha256, b.so_bao_gia
                                FROM master.crm_hd_soan s JOIN master.hop_dong h ON h.id = s.hop_dong_id JOIN master.crm_bao_gia b ON b.id = s.bao_gia_id
                                JOIN master.crm_hd_soan_rev r ON r.soan_id = s.id AND r.revision = s.revision_hien_hanh
                                WHERE s.id = %s::uuid AND master.crm_gk_duoc('CRM_SOAN', s.phap_nhan_id)""", (_uuid(soan_id, "soan_id"),))
        if s is None:
            _loi("CRM_G_KHONG_THAY", "Không thấy bản soạn (hoặc ngoài phạm vi).")
        return s

    def _profile(self, c, s) -> tuple:
        """(ràng buộc tổng canonical, profile hiện hành có khớp bản đã ghim của revision?) — đọc trong giao dịch của người gọi."""
        p = self.mau._mot(c, """SELECT cau_hinh, encode(sha256(convert_to(cau_hinh::text, 'UTF8')), 'hex') AS sha FROM master.loai_hinh_doanh_thu
                                WHERE id = %s""", (s["loai_hinh_id"],))
        return rang_buoc_tong(p["cau_hinh"]), p["sha"] == s["profile_sha256"]

    @staticmethod
    def kiem_soan(du_lieu: dict, ghim: dict, tinh: dict, rb: dict | None = None, profile_khop: bool = True) -> dict:
        """Nhóm trường theo bản đồ đã duyệt + đoạn văn có ô (điền/thiếu) + danh sách thiếu/chặn xuất/cảnh báo."""
        dm = {t["khoa"]: t for t in ghim["danh_muc"]}
        bd = ghim["ban_do"]
        dung = []
        for o in bd:
            if o.get("truong") and o["truong"] not in dung:
                dung.append(o["truong"])
        gt = du_lieu.get("gia_tri_truong") or {}
        chan, canh_bao, nhom, hien = [], [], {}, {}
        for k in dung:
            t = dm.get(k)
            if t is None:
                chan.append({"ma": "TRUONG_KHONG_TRONG_DANH_MUC", "truong": k, "thong_bao": f"Ô ánh xạ tới trường {k} không có trong danh mục đã ghim."})
                continue
            v = gt.get(k)
            try:
                hien[k] = hien_thi_truong(t, v)
            except (R.LoiRender, DataError) as exc:
                chan.append({"ma": exc.code, "truong": k, "thong_bao": str(exc)})
                hien[k] = None
            if v is None and t["bat_buoc"]:
                chan.append({"ma": "THIEU_GIA_TRI_BAT_BUOC", "truong": k, "thong_bao": f"Thiếu giá trị bắt buộc: {t['nhan']}."})
            nhom.setdefault(t["nhom"], []).append({**t, "gia_tri": v, "hien_thi": hien.get(k), "trong_mau": True})
        for k, t in dm.items():  # trường bắt buộc vắng TRONG MẪU: cảnh báo G1, không chặn
            if k not in dung and t["bat_buoc"]:
                canh_bao.append({"ma": "TRUONG_BAT_BUOC_VANG_TRONG_MAU", "truong": k, "thong_bao": f"Mẫu không có ô cho trường bắt buộc {t['nhan']} (cảnh báo G1)."})
        # lịch/required values hợp lệ trước Xuất; BG-1c: hợp đồng cần cả điều kiện bước 2 (khách) — `chan_chuyen` khi có
        chan.extend({"ma": x["ma"], "thong_bao": x["thong_bao"]} for x in tinh.get("chan_chuyen", tinh["chan_in"]))
        canh_bao.extend(tinh["canh_bao"])
        c2, cb2 = kiem_tong_canonical(rb, gt, du_lieu.get("bao_gia") or {}, tinh, set(dung))  # FIX01 #7
        chan.extend(c2)
        canh_bao.extend(cb2)
        if not profile_khop:
            chan.append({"ma": "PROFILE_DA_DOI", "thong_bao": "Profile loại hình đã đổi so với bản ghim của revision — lưu revision mới sau khi rà lại."})
        theo_doan = {}
        for k, o in enumerate((ghim["facts"] or {}).get("occurrences") or [], start=1):
            theo_doan.setdefault(o["doan"], []).append((o, next((b.get("truong") for b in bd if int(b["thu_tu"]) == k), None)))
        doan = []
        for dd in (ghim["facts"] or {}).get("doan") or []:
            van, vt, manh = dd["van_ban"], 0, []
            for o, k in sorted(theo_doan.get(dd["chi_so"], []), key=lambda x: x[0]["bat_dau"]):
                if o["ket_thuc"] > len(van):
                    break
                manh.append({"loai": "van_ban", "text": van[vt:o["bat_dau"]]})
                manh.append({"loai": "o", "ten": o["ten"], "truong": k, "text": hien.get(k) if hien.get(k) else None})
                vt = o["ket_thuc"]
            manh.append({"loai": "van_ban", "text": van[vt:]})
            doan.append({"chi_so": dd["chi_so"], "phan": dd["loai_phan"], "vi_tri": dd["vi_tri"], "manh": manh})
        return {"nhom": nhom, "doan": doan, "chan_xuat": chan, "canh_bao": canh_bao}

    def doc_soan(self, dang_nhap: str, soan_id) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt, rr=True) as c:
            s = self._soan(c, soan_id)
            ghim = m.mau_ghim_trong(c, s["id"], s["revision_hien_hanh"])  # mẫu ĐÃ GHIM (v1 vẫn mở được sau khi v2 hiệu lực)
            rev = m._nhieu(c, """SELECT revision, mau_phien_ban_id, raw_sha256, ly_do, tao_boi, tao_luc FROM master.crm_hd_soan_rev WHERE soan_id = %s
                                 ORDER BY revision""", (s["id"],))
            xuat = m._nhieu(c, """SELECT id, revision, trang_thai, docx_len, pdf_len, ly_do, kiem_pdf, tao_boi, tao_luc FROM master.crm_gk_xuat
                                  WHERE soan_id = %s ORDER BY tao_luc""", (s["id"],))
            mau = m._mot(c, "SELECT master.crm_gk_mau_hieu_luc(%s::uuid) AS r", (s["loai_hinh_id"],))["r"]
            bg = s["du_lieu"]["bao_gia"]
            trung = self._trung_don_vi(c, s["phap_nhan_id"], {"don_vi": (bg.get("don_vi") or {"ma": None}), "du_an_id": bg.get("du_an_id")}, s["id"])
            g7 = None  # lệch G7 ở cột phải: đọc bộ chuẩn hiệu lực hôm nay trong CÙNG giao dịch RR (không fake khớp khi chưa có)
            if bg.get("nguon_lich") == "DU_AN" and bg.get("du_an_id") and bg.get("giai_doan_g7"):
                g7 = c.execute("SELECT master.crm_g_chuan_doc(%s::uuid, %s, %s::date) AS r", (bg["du_an_id"], bg["giai_doan_g7"],
                                                                                             m.hom_nay().isoformat())).fetchone()["r"]
            rb, profile_khop = self._profile(c, s)
        tinh = tinh_bao_gia(bg, g7)  # dữ liệu đã chuẩn hóa khi lưu (giữ người nhập FX do máy chủ ghi)
        kiem = self.kiem_soan(s["du_lieu"], ghim, tinh, rb, profile_khop)
        kiem["canh_bao"].extend(trung)
        ghim.pop("raw", None)
        return {"soan": {k: s[k] for k in ("id", "hop_dong_id", "ma_noi_bo", "so_bao_gia", "trang_thai", "revision_hien_hanh", "loai_hinh_id",
                                           "rev_boi", "rev_luc", "mau_phien_ban_id")},
                "du_lieu": s["du_lieu"], "tinh": tinh, "mau": {k: ghim[k] for k in ("mau_phien_ban_id", "ma_mau", "phien_ban", "ten_tep", "raw_sha256")},
                "danh_muc": ghim["danh_muc"], "kiem": kiem, "revisions": rev, "xuat": xuat, "mau_hieu_luc": mau}

    def luu_soan(self, dang_nhap: str, *, soan_id, expected_revision, gia_tri_truong, bao_gia=None, doi_mau_phien_ban_id=None, ly_do=None, khoa) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        sid, khoa = _uuid(soan_id, "soan_id"), _khoa(khoa)
        doi = _uuid_hoac_none(doi_mau_phien_ban_id, "doi_mau_phien_ban_id")
        if not isinstance(gia_tri_truong, dict) or len(gia_tri_truong) > 500:
            _loi("CRM_GK_YEU_CAU_SAI", "Giá trị trường phải là object {mã trường: giá trị}.")
        h = _h("CRM_SOAN_LUU", {"soan_id": sid, "expected_revision": expected_revision, "gia_tri_truong": gia_tri_truong, "bao_gia": bao_gia,
                                "doi_mau_phien_ban_id": doi, "ly_do": ly_do})
        with m._tx(dt, rr=True) as c:
            cu = self._tra(c, "CRM_SOAN_LUU", khoa, sid, h)
            if cu is not None:
                return cu
            s = self._soan(c, sid)
            if doi and doi != s["mau_phien_ban_id"]:  # đổi mẫu tường minh: danh mục của mẫu mới (đã kiểm hiệu lực trong SQL)
                pin = c.execute("SELECT master.crm_gk_ghim_mau(%s::uuid, %s::uuid, %s::uuid) AS r", (s["phap_nhan_id"], s["loai_hinh_id"], doi)).fetchone()["r"]
                ref, rev = pin["danh_muc_ref"], pin["danh_muc_rev"]
            else:
                r0 = m._mot(c, "SELECT danh_muc_ref, danh_muc_rev FROM master.crm_hd_soan_rev WHERE soan_id = %s AND revision = %s", (sid, s["revision_hien_hanh"]))
                ref, rev = r0["danh_muc_ref"], r0["danh_muc_rev"]
            dm = {t["khoa"]: t for t in m._nhieu(c, """SELECT khoa, kieu FROM master.crm_danh_muc_truong WHERE loai_hinh_id = %s AND danh_muc_ref = %s
                                                       AND revision = %s""", (s["loai_hinh_id"], ref, rev))}
            la = sorted(set(gia_tri_truong) - set(dm))
            if la:
                _loi("CRM_GK_TRUONG_LA", "Trường không thuộc danh mục của mẫu: " + ", ".join(la[:5]))
            gt = {k: chuan_hoa_truong(dm[k]["kieu"], v) for k, v in gia_tri_truong.items()}
            bg = s["du_lieu"]["bao_gia"]
            if bao_gia is not None:  # sửa lịch/giá/FX khi soạn: cùng validator báo giá; giữ row ID logic; FX người nhập do máy chủ ghi
                vao = {**bao_gia, "loai_hinh_id": bg["loai_hinh_id"]} if isinstance(bao_gia, dict) else bao_gia
                moi = chuan_hoa_bao_gia(vao)
                _chan_ty_gia_vnd(moi)
                if self._can_fx_mac_dinh(moi):  # BG-1c: cùng quy tắc tỷ giá như báo giá (giữ tỷ giá đã lưu của bản soạn; chưa có → mặc định chung)
                    moi = chuan_hoa_bao_gia(vao, fx_mac_dinh=self._fx_mac_dinh(c, bg), hom_nay=m.hom_nay().isoformat())
                else:
                    moi = chuan_hoa_bao_gia(vao, hom_nay=m.hom_nay().isoformat())
                for r in moi["lich"]:
                    r["dong_id"] = r["dong_id"] or str(uuid.uuid4())
                if moi["fx"]:
                    fx_cu = bg.get("fx") or {}
                    giu = (fx_cu.get("cap"), fx_cu.get("ty_gia"), fx_cu.get("ngay")) == (moi["fx"]["cap"], moi["fx"]["ty_gia"], moi["fx"]["ngay"])
                    moi["fx"]["nguoi_nhap"] = fx_cu.get("nguoi_nhap") if giu else dt["dang_nhap"]
                    moi["fx"]["nhap_ngay"] = fx_cu.get("nhap_ngay") if giu else m.hom_nay().isoformat()
                if (moi["du_an_id"], moi["khach"]["doi_tac_id"]) != (bg.get("du_an_id"), (bg.get("khach") or {}).get("doi_tac_id")):
                    _loi("CRM_GK_PHAM_VI", "Không đổi dự án/khách đã gắn với hợp đồng khi soạn.")
                bg = {k: v for k, v in moi.items() if k != "phien_ban_du_lieu"}
            du_lieu = {"phien_ban_du_lieu": PHIEN_BAN_SOAN, "bao_gia": bg, "gia_tri_truong": {k: v for k, v in gt.items() if v is not None}}
            return self._kq(c.execute("SELECT master.crm_gk_soan_luu(%s, %s, %s::uuid, %s, %s::jsonb, %s::uuid, %s, %s) AS r",
                                      (khoa, h, sid, expected_revision, json.dumps(du_lieu, ensure_ascii=False), doi,
                                       _str(ly_do, "lý do", 1000), R.PHIEN_BAN_RENDERER)).fetchone())

    # ------------------------------------------------------------------ in/xuất ba pha
    def chuan_bi_in(self, dang_nhap: str, *, bao_gia_id, expected_revision, khoa) -> dict:
        """Pha A (dưới khóa, giao dịch RR ngắn): quyền + biên nhận + chụp revision + cổng In + điều khoản đã khai. Trả {'lap_lai': kq} hoặc kế hoạch."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        bg, khoa = _uuid(bao_gia_id, "bao_gia_id"), _khoa(khoa)
        h = _h("CRM_BAO_GIA_IN", {"bao_gia_id": bg, "expected_revision": expected_revision})
        with m._tx(dt, rr=True) as c:
            cu = self._tra(c, "CRM_BAO_GIA_IN", khoa, bg, h)
            if cu is not None:
                return {"lap_lai": cu}
            b = self._bao_gia(c, bg)
            if b["revision_hien_hanh"] != expected_revision:
                _loi("CRM_GK_REVISION_CU", "Báo giá đã có revision mới — tải lại rồi in.")
            if b["trang_thai"] == "HUY":
                _loi("CRM_GK_TRANG_THAI", "Báo giá đã hủy — không in.")
            dk = [r["noi_dung"] for r in m._nhieu(c, "SELECT noi_dung FROM master.crm_bao_gia_dieu_khoan WHERE loai_hinh_id = %s ORDER BY ma",
                                                   (b["loai_hinh_id"],))]
            da = m._mot(c, "SELECT ten FROM master.du_an WHERE id = %s", (b["du_an_id"],)) if b["du_an_id"] else None
        d = b["du_lieu"]
        # BG-1c: cổng In tính lại từ dữ liệu đã chụp theo luật hiện hành (In sơ bộ không đòi khách/phí — QD-20261025-03), không dùng kết quả cũ
        t = tinh_bao_gia(d, b.get("g7"))
        chan = list(t["chan_in"]) + ([] if dk else [{"ma": "THIEU_DIEU_KHOAN_THAM_CHIEU", "thong_bao": "Loại hình chưa khai điều khoản tham chiếu cho bản in."}])
        if chan:
            raise DataError("CRM_GK_CHAN_IN", "Chưa in được: " + "; ".join(x["thong_bao"] for x in chan))
        tc, tt = t["tien_te"], d["gia"]["tien_te"]
        moi = la_tien_chinh_vnd(d)
        ten_khach = b["khach_ten"] or ((d["khach"].get("du_thao") or {}).get("ten"))
        lich = [(r["lan"], _gia_tri_lich(r, x, tc), _moc(r), r["ghi_chu"] or "") for r, x in zip(d["lich"], t["dong"])]
        thong_tin = [("Dự án", da["ten"])] if da else []
        thong_tin += [("Lô/căn", " — ".join(x for x in (d["don_vi"]["ma"], d["don_vi"]["mo_ta"]) if x))]
        if not ten_khach:
            thong_tin.append(("Loại bản in", "Báo giá sơ bộ — thông tin khách hàng và phí quản lý/bảo trì bổ sung khi khách đồng ý"))
        if moi:
            if d["gia"]["don_gia"]:
                thong_tin.append(("Đơn giá", f"{_so_vn(d['gia']['don_gia'])} {tt}"))
            if d["gia"]["dien_tich"]:
                thong_tin.append(("Diện tích", _so_vn(d["gia"]["dien_tich"]) + " m²"))
            if tt == "USD":
                thong_tin.append(("Tỷ giá USD/VND", t["ty_gia"]["hien_thi"]))
        else:
            if d["gia"]["don_gia"]:
                thong_tin.append(("Đơn giá", f"{d['gia']['don_gia']} {tt}"))
            if d["gia"]["dien_tich"]:
                thong_tin.append(("Diện tích", d["gia"]["dien_tich"]))
        tong_ht = R.tien_hien_thi(int(t["tong_minor"]), tc)
        thong_tin.append(("Tổng giá trị", tong_ht))
        if moi and t["tong_bang_chu"]:
            thong_tin.append(("Bằng chữ", t["tong_bang_chu"]))
        if moi and t["usd_tham_chieu"]:
            thong_tin.append(("Giá trị tham chiếu (USD)", t["usd_tham_chieu"]["tong_hien_thi"]))
        thong_tin.append(("Cơ sở giá", "Giá chưa gồm VAT" if d["gia"]["co_so_thue"] == "NET" else "Giá đã gồm VAT"))
        if d["gia"]["vat_phan_tram"]:
            thong_tin.append(("Thuế suất VAT khai báo", d["gia"]["vat_phan_tram"] + "%"))
        fx_cau = None
        if tt == "USD" and moi:
            fx = d["fx"]
            nguon = "tỷ giá mặc định chung" if fx.get("nguon") == "MAC_DINH" else f"do {fx.get('nguoi_nhap') or 'người lập'} nhập"
            fx_cau = (f"Tỷ giá áp dụng USD/VND = {_so_vn(fx['ty_gia'])}" + (f" (ngày {R.ngay_hien_thi(fx['ngay'], 'dd/MM/yyyy')})" if fx.get("ngay") else "")
                      + f", {nguon}. Giá trị thanh toán tính bằng VND; giá trị bằng USD chỉ để tham chiếu.")
        elif tt == "USD":
            fx = d["fx"]
            fx_cau = (f"Tỷ giá tham chiếu {fx['cap']} = {fx['ty_gia']} (ngày {R.ngay_hien_thi(fx['ngay'], 'dd/MM/yyyy')}), do {fx['nguoi_nhap']} nhập "
                      f"ngày {R.ngay_hien_thi(fx['nhap_ngay'], 'dd/MM/yyyy')}; giá trị VND tương đương {t['vnd_tham_chieu']['tong']} VND chỉ để tham "
                      f"chiếu, không phải tỷ giá thanh toán.")
        pbt = None
        if d["phi_bao_tri"] and d["phi_bao_tri"]["gia_tri"] is not None:
            mi, _ = _minor(d["phi_bao_tri"]["gia_tri"], d["phi_bao_tri"]["tien_te"])
            pbt = f"Phí bảo trì (khai riêng, không gộp lịch thanh toán): {R.tien_hien_thi(mi, d['phi_bao_tri']['tien_te'])}" + \
                  (f" — {d['phi_bao_tri']['co_so']}" if d["phi_bao_tri"]["co_so"] else "")
        ten_khach = ten_khach or "Quý khách hàng"
        nd = {"so_bao_gia": b["so_bao_gia"], "ngay": R.ngay_hien_thi(b["ngay"], "dd/MM/yyyy"), "nguoi_lap": b["tao_boi"],
              "het_han": R.ngay_hien_thi(d["het_han"], "dd/MM/yyyy") if d["het_han"] else None, "khach": ten_khach, "thong_tin": thong_tin,
              "lich": lich, "fx_cau": fx_cau, "phi_bao_tri": pbt, "dieu_khoan": dk}
        # FIX01 #12: nội dung kỳ vọng ĐẦY ĐỦ từ dữ liệu typed đã chụp — số/ngày/người lập/khách/thông tin giá/từng dòng lịch (lần/giá trị/mốc/ghi chú)/
        # câu FX đầy đủ/phí bảo trì/điều khoản (mỗi mục ≥ 1 lần trong PDF). Đây là kiểm VĂN BẢN cơ bản, không phải fidelity bố cục/glyph.
        mong = [(x, 1) for x in [b["so_bao_gia"], nd["ngay"], nd["nguoi_lap"], ten_khach, *(v for _, v in thong_tin if v),
                                 *(c for row in lich for c in row if c), fx_cau, pbt, *dk, nd["het_han"]] if x]
        input_sha = sha256(canonical_json({"bao_gia_id": bg, "revision": expected_revision, "du_lieu_sha256": b["du_lieu_sha256"], "dieu_khoan": dk,
                                           "renderer": R.PHIEN_BAN_RENDERER}).encode("utf-8"))
        kh = {"hanh": "CRM_BAO_GIA_IN", "dich": bg, "revision": expected_revision, "h": h, "khoa": khoa, "input_sha": input_sha,
              "loai": "BAO_GIA", "nd": nd, "mong_doi": mong, "ten": b["so_bao_gia"]}
        return self._dat_lan(dt, kh)

    def _dat_lan(self, dt, kh: dict) -> dict:
        """FIX01 #5 — đặt chỗ BỀN (giao dịch READ COMMITTED ngắn, dưới khóa namespace biên nhận) TRƯỚC pha B. FINAL đã có → trả FINAL. Lần cũ cùng
        khóa/H → ĐỐI SOÁT theo kết quả đã giữ trong thư mục của chính lần đó (ket_qua.json bất biến); chưa có kết quả → chưa rõ, KHÔNG render lại."""
        m = self.mau
        with m._tx(dt) as c:
            r = _v(dict(c.execute("SELECT master.crm_gk_dat_lan(%s, %s, %s::uuid, %s, %s, %s) AS r",
                                  (kh["hanh"], kh["khoa"], kh["dich"], kh["h"], kh["revision"], kh["input_sha"])).fetchone()))["r"]
        if r.get("lap_lai"):
            return {"lap_lai": {**r["ket_qua"], "lap_lai": True}}
        kh = {**kh, "lan_id": r["lan_id"]}
        if r["moi"]:
            return kh
        if r["trang_thai"] != "DANG_RENDER" or r["input_sha256"] != kh["input_sha"] or r["revision"] != kh["revision"]:
            _loi("CRM_GK_LAN_KHONG_KHOP", "Lần in/xuất đã đặt cho khóa này không khớp ảnh chụp hiện tại — chưa rõ; không render lại.")
        p = self.kho / "lan" / r["lan_id"] / "ket_qua.json"
        if not p.is_file():
            _loi("CRM_GK_DANG_XU_LY", "Lần in/xuất cùng khóa đang chạy hoặc dừng giữa chừng — chưa rõ kết quả; không render lại (giữ nguyên khóa, thử lại sau).")
        return {**kh, "doi_soat": json.loads(p.read_text(encoding="utf-8"))}

    def chuan_bi_xuat(self, dang_nhap: str, *, soan_id, expected_revision, khoa) -> dict:
        """Pha A cho Xuất: quyền + biên nhận + revision + mẫu ĐÃ GHIM (raw kiểm hash) + giá trị đã typed/hiển thị + cổng Xuất (required/lịch)."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        sid, khoa = _uuid(soan_id, "soan_id"), _khoa(khoa)
        h = _h("CRM_SOAN_XUAT", {"soan_id": sid, "expected_revision": expected_revision})
        with m._tx(dt, rr=True) as c:
            cu = self._tra(c, "CRM_SOAN_XUAT", khoa, sid, h)
            if cu is not None:
                return {"lap_lai": cu}
            s = self._soan(c, sid)
            if s["revision_hien_hanh"] != expected_revision:
                _loi("CRM_GK_REVISION_CU", "Bản soạn đã có revision mới — tải lại rồi xuất.")
            ghim = m.mau_ghim_trong(c, sid, expected_revision)
            rb, profile_khop = self._profile(c, s)
        tinh = tinh_bao_gia(s["du_lieu"]["bao_gia"], None)  # cổng Xuất: lịch/tổng/FX; lệch G7 chỉ cảnh báo, không chặn
        kiem = self.kiem_soan(s["du_lieu"], ghim, tinh, rb, profile_khop)
        if kiem["chan_xuat"]:
            raise DataError("CRM_GK_CHAN_XUAT", "Chưa xuất được: " + "; ".join(x["thong_bao"] for x in kiem["chan_xuat"]))
        dm = {t["khoa"]: t for t in ghim["danh_muc"]}
        dung = {o["truong"] for o in ghim["ban_do"] if o.get("truong")}
        gia_tri = {k: hien_thi_truong(dm[k], s["du_lieu"]["gia_tri_truong"].get(k)) for k in dung if k in dm}
        # FIX01 #12: MỌI giá trị đã ánh xạ (kể cả 1 ký tự) với số lần tối thiểu = số ô của trường trong mẫu (thân/header/footer)
        so_o = {}
        for o in ghim["ban_do"]:
            if o.get("truong"):
                so_o[o["truong"]] = so_o.get(o["truong"], 0) + 1
        mong = [(v, so_o[k]) for k, v in sorted(gia_tri.items()) if v]
        input_sha = sha256(canonical_json({"soan_id": sid, "revision": expected_revision, "du_lieu_sha256": s["du_lieu_sha256"], "raw_sha256": s["raw_sha256"],
                                           "ban_do_sha256": s["ban_do_sha256"], "danh_muc_digest": s["danh_muc_digest"], "profile_sha256": s["profile_sha256"],
                                           "renderer": R.PHIEN_BAN_RENDERER}).encode("utf-8"))
        kh = {"hanh": "CRM_SOAN_XUAT", "dich": sid, "revision": expected_revision, "h": h, "khoa": khoa, "input_sha": input_sha, "loai": "HOP_DONG",
              "raw": ghim["raw"], "facts": ghim["facts"], "ban_do": ghim["ban_do"], "gia_tri": gia_tri, "mong_doi": mong, "ten": s["ma_noi_bo"]}
        return self._dat_lan(dt, kh)

    def render(self, kh: dict) -> dict:
        """Pha B — NGOÀI khóa toàn cục/giao dịch, không kết nối CSDL: DOCX thật → giữ bất biến (lần chạy riêng + kho nội dung) TRƯỚC PDF →
        Word COM sở hữu → kiểm PDF. Không xóa/ghi đè; thiếu nhà cung cấp/lỗi → DOCX giữ, PDF trạng thái rõ. FIX01 #5: thư mục = định danh lần đã đặt
        chỗ bền (không UUID mới); lần đối soát dùng kết quả đã giữ, không render/không Word lần hai."""
        if kh.get("doi_soat") is not None:
            if kh["doi_soat"].get("loi_ma"):  # lần đã đặt kết thúc bằng lỗi render xác định (không có DOCX) → trả đúng lỗi đó
                raise DataError(kh["doi_soat"]["loi_ma"], kh["doi_soat"].get("loi") or "Lỗi render đã ghi nhận.")
            return kh["doi_soat"]
        lan = self.kho / "lan" / kh["lan_id"]
        lan.mkdir(parents=True, exist_ok=False)  # đã tồn tại = có lần chạy khác của cùng chỗ đặt → lỗi, không chạy chồng
        try:
            kq = self._render_trong(kh, lan)
        except DataError as exc:  # lỗi xác định trước DOCX (ánh xạ/facts/định dạng): ghi bền để đối soát trả cùng lỗi
            write_immutable(lan / "ket_qua.json", json.dumps({"loi_ma": exc.code, "loi": str(exc)}, ensure_ascii=False).encode("utf-8"))
            raise
        write_immutable(lan / "ket_qua.json", json.dumps(kq, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8"))  # đối soát sau mất ACK/crash
        return kq

    def _render_trong(self, kh: dict, lan: Path) -> dict:
        if kh["loai"] == "HOP_DONG":
            docx_b, bao_cao = R.dien_mau(kh["raw"], kh["facts"], kh["ban_do"], kh["gia_tri"])
        else:
            docx_b = R.tao_docx_bao_gia(kh["nd"])
            bao_cao = {"kiem": R.kiem_docx_chuan_bi(docx_b)}
        ten = re.sub(r"[^A-Za-z0-9_.-]", "_", kh["ten"])[:80] or "tep"
        p_docx = lan / f"{ten}.docx"
        write_immutable(p_docx, docx_b)
        write_immutable(self.kho / "tep" / sha256(docx_b), docx_b)
        pdf = R.chuyen_pdf(lan, p_docx, han=HAN_PDF_GIAY)
        out = {"docx_sha": sha256(docx_b), "docx_len": len(docx_b), "pdf_sha": None, "pdf_len": None, "bao_cao": bao_cao,
               "engine": R.PHIEN_BAN_RENDERER, "kiem": {"word": pdf.get("word"), "pha": pdf.get("pha"), "lan_id": kh["lan_id"]}}
        # FIX01 #9: chỉ PDF_DA_TAO khi tiến trình/Job/Word ĐÃ xác nhận dừng (crm_docx._ket_luan); ngoài ra giữ DOCX + trạng thái trung thực
        if pdf["trang_thai"] != "PDF_DA_TAO" or (pdf.get("word") or {}).get("da_dung") is not True:
            tt = pdf["trang_thai"] if pdf["trang_thai"] != "PDF_DA_TAO" else "PDF_LOI"
            return {**out, "trang_thai": tt, "ly_do": pdf.get("ly_do") or "WORD_CHUA_XAC_NHAN_DUNG"}
        kiem = R.kiem_pdf(Path(pdf["pdf"]), kh["mong_doi"])
        out["kiem"].update({k: kiem.get(k) for k in ("ok", "so_trang", "phong", "thieu_pdfium", "thieu_pdfplumber", "render_ok", "loi", "muc_kiem")})
        if not kiem["ok"]:
            return {**out, "trang_thai": "PDF_LOI", "ly_do": kiem.get("loi") or "PDF_KHONG_DAT"}
        pdf_b = Path(pdf["pdf"]).read_bytes()
        if sha256(pdf_b) != kiem["sha256"]:
            return {**out, "trang_thai": "PDF_LOI", "ly_do": "PDF_DOI_SAU_KIEM"}
        write_immutable(self.kho / "tep" / kiem["sha256"], pdf_b)
        return {**out, "trang_thai": "PDF_DAT", "pdf_sha": kiem["sha256"], "pdf_len": len(pdf_b), "ly_do": None}

    def cong_bo(self, dang_nhap: str, kh: dict, kq: dict) -> dict:
        """Pha C (dưới khóa, giao dịch ngắn): quyền hiện hành + CAS revision trong hàm SQL; revision đổi → DA_CU (bằng chứng, không gắn hiện hành)."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt) as c:
            r = self._kq(c.execute("""SELECT master.crm_gk_xuat_ghi(%s, %s, %s, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb) AS r""",
                                   (kh["khoa"], kh["h"], kh["hanh"], kh["dich"], kh["revision"], kh["input_sha"], kq["docx_sha"], kq["docx_len"],
                                    kq["pdf_sha"], kq["pdf_len"], kq["trang_thai"], kq["engine"], kq.get("ly_do"),
                                    json.dumps(kq["kiem"], ensure_ascii=False, default=str))).fetchone())
        return {**r, "bao_cao": {k: v for k, v in (kq.get("bao_cao") or {}).items() if k != "kiem"}}

    def tep(self, dang_nhap: str, xuat_id, loai: str) -> tuple[str, bytes, str]:
        """Tải tệp đã công bố: quyền hiện hành TRƯỚC tra hash/kho; kiểm lại hash/độ dài."""
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        if loai not in ("docx", "pdf"):
            _loi("NOT_FOUND", "Không có loại tệp này.")
        with m._tx(dt, rr=True) as c:
            x = c.execute("SELECT master.crm_gk_tep(%s::uuid) AS r", (_uuid(xuat_id, "xuat_id"),)).fetchone()["r"]
        sha, dai = x[f"{loai}_sha256"], x[f"{loai}_len"]
        if not sha:
            _loi("CRM_G_TEP_KHONG_CO", "Lần xuất này không có PDF đã kiểm đạt.")
        p = self.kho / "tep" / sha
        if not re.fullmatch(r"[0-9a-f]{64}", sha) or not p.is_file():
            _loi("CRM_G_TEP_KHONG_CO", "Tệp không có trong kho lưu trữ.")
        raw = p.read_bytes()
        if sha256(raw) != sha or len(raw) != int(dai):
            _loi("CRM_G_TEP_HONG", "Tệp trong kho khác hash đã ghi — không trả.")
        mime = "application/pdf" if loai == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return f"{x['ten']}-r{x['revision']}.{loai}", raw, mime
