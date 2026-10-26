"""Chuẩn hóa values.get đã có trong bộ nhớ; không kéo Sheet hay ghi dữ liệu."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal

from kho_tri_thuc.ha_tang.primitives import DataError


CAU_HINH_MAU = {
    "ten_tab": "DEMO - Dư nợ và lãi suất (Sheet giả)",
    "dong_tieu_de": 1,  # Số dòng Sheet, bắt đầu từ 1.
    "dau_thap_phan": ",",  # Dùng cho tiền; lãi suất nhận 8,5% hoặc 8.5.
    "tien_te_cho_phep": ["VND", "USD"],
    "cach_tinh_cho_phep": ["CO_DINH", "THA_NOI"],
    "anh_xa_cot": {
        "Pháp nhân DEMO": "phap_nhan",
        "Ngân hàng DEMO": "ngan_hang",
        "Mã khoản vay DEMO": "ma_khoan_vay",
        "Tiền tệ": "tien_te",
        "Dư nợ": "du_no",
        "Lãi suất năm (%)": "lai_suat_nam",
        "Cách tính": "cach_tinh",
        "Lãi cơ sở (%)": "lai_co_so",
        "Biên độ (%)": "bien_do",
        "Kỳ điều chỉnh kế tiếp": "ky_dieu_chinh_ke_tiep",
        "Ngày đáo hạn": "ngay_dao_han",
    },
}

_TRUONG = (
    "phap_nhan", "ngan_hang", "ma_khoan_vay", "tien_te", "du_no",
    "lai_suat_nam", "cach_tinh", "lai_co_so", "bien_do",
    "ky_dieu_chinh_ke_tiep", "ngay_dao_han",
)
_LAI = frozenset({"lai_suat_nam", "lai_co_so", "bien_do"})
_NGAY = frozenset({"ky_dieu_chinh_ke_tiep", "ngay_dao_han"})
_O_LOI_SHEET = frozenset({
    "#N/A", "#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#NUM!",
    "#NULL!", "#ERROR!", "#CALC!", "#SPILL!", "Loading...",
})
_CHO_PHEP_MAC_DINH = {
    "tien_te": ("VND", "USD"),
    "cach_tinh": ("CO_DINH", "THA_NOI"),
}


def _loi_cau_hinh() -> DataError:
    return DataError(
        "M9_SHEET_CAU_HINH",
        "Cấu hình phải có tab, dòng tiêu đề (từ 1), ánh xạ đủ 11 trường "
        "không trùng, dấu thập phân ',' hoặc '.' và danh sách giá trị cho phép hợp lệ.",
    )


def _cau_hinh(cau_hinh: dict) -> tuple[str, int, dict, str, dict]:
    if not isinstance(cau_hinh, dict):
        raise _loi_cau_hinh()
    tab = cau_hinh.get("ten_tab")
    dong = cau_hinh.get("dong_tieu_de")
    cot = cau_hinh.get("anh_xa_cot")
    dau = cau_hinh.get("dau_thap_phan", ",")
    if (not isinstance(tab, str) or not tab.strip()
            or type(dong) is not int or dong < 1
            or not isinstance(cot, dict) or len(cot) != len(_TRUONG)
            or dau not in (",", ".")):
        raise _loi_cau_hinh()
    if any(not isinstance(k, str) or not k.strip()
           or not isinstance(v, str) or v not in _TRUONG for k, v in cot.items()):
        raise _loi_cau_hinh()
    anh_xa = {k.strip(): v for k, v in cot.items()}
    if len(anh_xa) != len(_TRUONG) or set(anh_xa.values()) != set(_TRUONG):
        raise _loi_cau_hinh()
    cho_phep = {}
    for truong, mac_dinh in _CHO_PHEP_MAC_DINH.items():
        ds = cau_hinh.get(truong + "_cho_phep", mac_dinh)
        if (not isinstance(ds, (list, tuple, set, frozenset))
                or not ds or any(not isinstance(v, str) or not v.strip() for v in ds)):
            raise _loi_cau_hinh()
        cho_phep[truong] = {v.strip().upper() for v in ds}
    return tab, dong, anh_xa, dau, cho_phep


def _tien(chu: str, dau: str) -> Decimal:
    nhom = "." if dau == "," else ","
    # Chỉ nhận nhóm nghìn đủ ba chữ số; không đoán locale hay sửa số sai.
    mau = (r"[+-]?(?:[0-9]+|[0-9]{1,3}(?:" + re.escape(nhom)
           + r"[0-9]{3})+)(?:" + re.escape(dau) + r"[0-9]+)?")
    if not re.fullmatch(mau, chu):
        raise ValueError
    return Decimal(chu.replace(nhom, "").replace(dau, "."))


def _lai(chu: str) -> Decimal:
    # Đơn vị luôn %/năm, không chia 100 và không tự suy ra từ phần thập phân.
    if not re.fullmatch(r"[+-]?[0-9]+(?:[.,][0-9]+)?\s*%?", chu):
        raise ValueError
    return Decimal(chu.removesuffix("%").strip().replace(",", "."))


def _doc_o(chu: str, truong: str, dau: str):
    chu = chu.strip()
    if not chu:
        return None
    if truong in _CHO_PHEP_MAC_DINH:
        return chu.upper()
    if truong == "du_no":
        return _tien(chu, dau)
    if truong in _LAI:
        return _lai(chu)
    if truong in _NGAY:
        if not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", chu):
            raise ValueError
        return datetime.strptime(chu, "%d/%m/%Y").date()
    return chu


def _hash_tho(gia_tri: list[list[str]], dong: int) -> str:
    # Cột sắp theo tiêu đề thô; giữ nguyên chuỗi ô và thứ tự dòng, kể cả
    # cột không ánh xạ/dòng lỗi. Ô cuối bị values.get lược bỏ tương đương ''.
    tieu_de = gia_tri[dong - 1]
    du_lieu = gia_tri[dong:]
    rong = max(map(len, gia_tri[dong - 1:]), default=0)
    cot = []
    for i in range(rong):
        cot.append({
            "tieu_de": tieu_de[i] if i < len(tieu_de) else "",
            "gia_tri": [hang[i] if i < len(hang) else "" for hang in du_lieu],
        })
    cot.sort(key=lambda c: c["tieu_de"])
    raw = json.dumps(
        {"truoc_tieu_de": gia_tri[:dong - 1], "cot": cot},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def lap_snapshot(gia_tri: list[list[str]], *, cau_hinh: dict,
                 keo_luc: datetime, nguon_id: str) -> dict:
    """Trả snapshot đầu vào trực tiếp cho bao_cao_lai_suat.lap_bao_cao.

    anh_xa_cot ánh xạ tên tiêu đề -> trường; đủ 11 tiêu đề là bắt buộc,
    nhưng từng ô trống (kể cả ô cuối bị Sheets bỏ) thành None. Tên tiêu đề
    và ô được strip khi đọc; giữ nguyên mã, tiền tệ/cách tính viết hoa.
    tien_te_cho_phep mặc định VND/USD; cach_tinh_cho_phep mặc định
    CO_DINH/THA_NOI; danh sách cấu hình so không phân biệt hoa thường.
    Ô lỗi Sheet ở mọi cột, kể cả ngoài ánh xạ, đều loại cả dòng.
    Tiền theo dau_thap_phan (mặc định ','); lãi là Decimal %/năm.

    Lỗi toàn bảng/cấu hình: DataError có code; thiếu tiêu đề có code
    M9_SHEET_THIEU_COT và nêu tên cột. Lỗi ô: dong_loi gồm so_dong
    (từ 1), ten_cot, ma_loi, ghi_chu; không chép nội dung ô vào lỗi.
    Một dòng có thể có nhiều lỗi; mọi dòng trùng mã không rỗng đều bị loại,
    kể cả dòng đã sai ô khác. Dòng hoàn toàn trống bỏ qua; so_dong_doc
    đếm tất cả dòng sau tiêu đề, kể cả dòng trống/lỗi.

    sha256 chỉ hash dữ liệu thô theo thứ tự cột chuẩn, giữ thứ tự dòng,
    không gồm giờ kéo/cấu hình/nguồn. Mốc giữ giờ keo_luc bên gọi cung cấp,
    không tự chuyển múi giờ. Hàm không sửa đầu vào, ghi đĩa hay log ô.
    """
    tab, dong, anh_xa, dau, cho_phep = _cau_hinh(cau_hinh)
    if (not isinstance(gia_tri, list)
            or any(not isinstance(hang, list)
                   or any(not isinstance(o, str) for o in hang) for hang in gia_tri)):
        raise DataError("M9_SHEET_DAU_VAO", "Đầu vào phải là list các dòng ô chuỗi.")
    if not isinstance(keo_luc, datetime) or not isinstance(nguon_id, str) or not nguon_id.strip():
        raise DataError("M9_SHEET_NGUON", "Nguồn Sheet phải có giờ kéo và ID nguồn hợp lệ.")

    tieu_de = gia_tri[dong - 1] if dong <= len(gia_tri) else []
    vi_tri = {}
    for i, ten in enumerate(tieu_de):
        ten = ten.strip()
        if ten in anh_xa:
            if ten in vi_tri:
                raise DataError("M9_SHEET_TRUNG_COT", "Tiêu đề trùng: " + ten)
            vi_tri[ten] = i
    thieu = sorted(set(anh_xa) - set(vi_tri))
    if thieu:
        raise DataError("M9_SHEET_THIEU_COT", "Thiếu cột: " + ", ".join(thieu))

    dong_loi = []
    dong_sai = set()
    cac_dong = []
    theo_ma = {}
    ten_theo_truong = {v: k for k, v in anh_xa.items()}

    def them_loi(so_dong: int, ten: str, ma: str):
        dong_sai.add(so_dong)
        dong_loi.append({
            "so_dong": so_dong, "ten_cot": ten, "ma_loi": ma,
            "ghi_chu": "Ô nguồn Sheet không hợp lệ; dòng bị loại khỏi snapshot khoản vay.",
        })

    for so_dong, hang in enumerate(gia_tri[dong:], start=dong + 1):
        if not any(o.strip() for o in hang):
            continue
        for i, o in enumerate(hang):
            if o.strip() in _O_LOI_SHEET:
                ten = tieu_de[i].strip() if i < len(tieu_de) else ""
                them_loi(so_dong, ten or f"Cột {i + 1}", "O_LOI_SHEET")
        khoan = {}
        for truong in _TRUONG:
            ten = ten_theo_truong[truong]
            i = vi_tri[ten]
            chu = hang[i] if i < len(hang) else ""
            if chu.strip() in _O_LOI_SHEET:
                khoan[truong] = None
                continue
            try:
                khoan[truong] = _doc_o(chu, truong, dau)
                if (truong in cho_phep and khoan[truong] is not None
                        and khoan[truong] not in cho_phep[truong]):
                    ma = ("TIEN_TE_KHONG_HO_TRO" if truong == "tien_te"
                          else "CACH_TINH_KHONG_HO_TRO")
                    them_loi(so_dong, ten, ma)
            except ValueError:
                ma = "M9_SHEET_NGAY_SAI" if truong in _NGAY else "M9_SHEET_SO_SAI"
                them_loi(so_dong, ten, ma)
        cac_dong.append((so_dong, khoan))
        ma = khoan["ma_khoan_vay"]
        if ma is not None:
            theo_ma.setdefault(ma, []).append(so_dong)

    for cac_so_dong in theo_ma.values():
        if len(cac_so_dong) > 1:
            for so_dong in cac_so_dong:
                them_loi(so_dong, ten_theo_truong["ma_khoan_vay"], "TRUNG_MA")
    dong_loi.sort(key=lambda e: (e["so_dong"], e["ten_cot"], e["ma_loi"]))
    return {
        "moc": keo_luc.strftime("%d/%m/%Y %H:%M"),
        "nguon": "Sheet", "nguon_id": nguon_id, "tab": tab,
        "sha256": _hash_tho(gia_tri, dong),
        "khoan_vay": [k for so, k in cac_dong if so not in dong_sai],
        "dong_loi": dong_loi, "so_dong_doc": len(gia_tri[dong:]),
    }
