"""Profile loại hình doanh thu DEMO (cấu hình có version, nạp vào master.loai_hinh_doanh_thu.cau_hinh).

GIẢ ĐỊNH ĐỂ MÔ PHỎNG: mã tham số, định dạng số/ngày, mẫu lịch nghĩa vụ và cơ sở tiền dưới đây là cấu hình DEMO công khai,
không phải policy đã phê duyệt và không lấy từ hợp đồng thật. Thêm loại hình = thêm một profile, không sửa code nghiệp vụ.
Profile chỉ mô tả cách đọc tham số → field chuẩn và lịch nghĩa vụ tường minh; không chứa quy tắc ghi nhận doanh thu/VAT/giá vốn.
"""

from __future__ import annotations

from ..ha_tang.primitives import canonical_json, sha256

GIA_DINH = "Profile DEMO — giả định để mô phỏng, không phải policy đã phê duyệt."

# v2 (19/10/2026): thêm alias đơn vị tiền theo nguồn #6 (`đồng`) — v1 giữ trong CSDL làm lịch sử, không ghi đè.
ALIAS_TIEN = {"đồng": "VND", "VNĐ": "VND", "đ": "VND"}

KCN_THUE_DAT_DEMO = {
    "ma": "DT-KCN-THUE-DAT-DEMO", "phien_ban": 2, "ten": "Thuê đất/hạ tầng KCN — DEMO", "loai_hop_dong": "THUE_DAT",
    "gia_dinh_mo_phong": GIA_DINH,
    "dinh_dang_so": {"nghin": ".", "thap_phan": ","}, "dinh_dang_ngay": "dd/mm/yyyy", "tien_te_hop_le": ["VND", "USD"],
    "don_vi_tien_alias": ALIAS_TIEN,
    "truong": [
        {"truong": "so_hop_dong", "ma_nguon": ["TC-01"], "kieu": "text", "bat_buoc": True},
        {"truong": "ngay_ky", "ma_nguon": ["TC-02"], "kieu": "ngay", "bat_buoc": True},
        {"truong": "gia_tri_hop_dong", "ma_nguon": ["TT-02"], "kieu": "tien", "bat_buoc": True, "co_so": "TIEN_THUE_DAT_CHUA_VAT"},
        {"truong": "dien_tich", "ma_nguon": ["KCN-01"], "kieu": "so", "don_vi": "m2", "bat_buoc": False},
        {"truong": "so_phu_luc", "ma_nguon": ["PL-01"], "kieu": "text", "bat_buoc": False, "chi_phu_luc": True},
        {"truong": "ngay_hieu_luc_phu_luc", "ma_nguon": ["PL-02"], "kieu": "ngay", "bat_buoc": False, "chi_phu_luc": True},
    ],
    "lich": [
        {"khoa": "COC-1", "loai": "COC", "dot": 1, "so_tien": "LT-COC-TIEN", "han": "LT-COC-HAN", "co_so": "TIEN_THUE_DAT_CHUA_VAT"},
        {"khoa": "DOT-1", "loai": "DOT", "dot": 1, "so_tien": "LT-D1-TIEN", "han": "LT-D1-HAN", "co_so": "TIEN_THUE_DAT_CHUA_VAT"},
        {"khoa": "DOT-2", "loai": "DOT", "dot": 2, "so_tien": "LT-D2-TIEN", "han": "LT-D2-HAN", "moc": "LT-D2-MOC", "co_so": "TIEN_THUE_DAT_CHUA_VAT"},
        {"khoa": "DOT-3", "loai": "DOT", "dot": 3, "ty_le": "LT-D3-TYLE", "han": "LT-D3-HAN", "co_so": None},
    ],
    "moc_hop_le": {"Bàn giao đất": "BAN_GIAO_DAT"},
    "kiem_tong": {"truong": "gia_tri_hop_dong", "co_so": "TIEN_THUE_DAT_CHUA_VAT"},
}

NHA_O_DEMO = {
    "ma": "DT-NHA-O-DEMO", "phien_ban": 2, "ten": "Mua bán nhà ở — DEMO", "loai_hop_dong": "BAN_NHA",
    "gia_dinh_mo_phong": GIA_DINH,
    "dinh_dang_so": {"nghin": ".", "thap_phan": ","}, "dinh_dang_ngay": "dd/mm/yyyy", "tien_te_hop_le": ["VND"],
    "don_vi_tien_alias": ALIAS_TIEN,
    "truong": [
        {"truong": "so_hop_dong", "ma_nguon": ["TC-01"], "kieu": "text", "bat_buoc": True},
        {"truong": "ngay_ky", "ma_nguon": ["TC-02"], "kieu": "ngay", "bat_buoc": True},
        {"truong": "ma_can", "ma_nguon": ["NO-01"], "kieu": "text", "bat_buoc": True},
        {"truong": "gia_tri_hop_dong", "ma_nguon": ["TT-02"], "kieu": "tien", "bat_buoc": True, "co_so": "GIA_BAN_CHUA_VAT"},
        {"truong": "so_phu_luc", "ma_nguon": ["PL-01"], "kieu": "text", "bat_buoc": False, "chi_phu_luc": True},
        {"truong": "ngay_hieu_luc_phu_luc", "ma_nguon": ["PL-02"], "kieu": "ngay", "bat_buoc": False, "chi_phu_luc": True},
    ],
    "lich": [
        {"khoa": "COC-1", "loai": "COC", "dot": 1, "so_tien": "LT-COC-TIEN", "han": "LT-COC-HAN", "co_so": "GIA_BAN_CHUA_VAT"},
        {"khoa": "DOT-1", "loai": "DOT", "dot": 1, "so_tien": "LT-D1-TIEN", "han": "LT-D1-HAN", "co_so": "GIA_BAN_CHUA_VAT"},
        {"khoa": "DOT-2", "loai": "DOT", "dot": 2, "so_tien": "LT-D2-TIEN", "han": "LT-D2-HAN", "moc": "LT-D2-MOC", "co_so": "GIA_BAN_CHUA_VAT"},
    ],
    "moc_hop_le": {"Bàn giao căn hộ": "BAN_GIAO_CAN"},
    "kiem_tong": {"truong": "gia_tri_hop_dong", "co_so": "GIA_BAN_CHUA_VAT"},
}

PROFILES_DEMO = (KCN_THUE_DAT_DEMO, NHA_O_DEMO)


def profile_hash(profile: dict) -> str:
    return sha256(canonical_json(profile).encode())
