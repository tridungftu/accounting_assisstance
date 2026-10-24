"""Fixture DEMO M9 — tự dựng đúng shape nguồn #9 (profile native JSON v6) và bảng lãi xác nhận DEMO; mọi giá trị là giả định kỹ thuật
có nhãn DEMO (giải ngân/kỳ gốc/lãi/phí theo gói bridge §6), không phải tỷ lệ/chính sách công ty, không lấy từ dữ liệu thật/Google.
Hai công ty nguồn ↔ hai pháp nhân DEMO; biến thể dùng cho các ca corpus (S01 hai draw cùng kỳ, S03/S04 PhatSinh trùng, S05 LOAN+DRAW,
S09/S10 precision, S14 profile root, S16 rate mơ hồ, S19 thiếu key, RC2 LC→nhận nợ)."""

from __future__ import annotations

import copy
import json

INSTANCE = "SHEET_VAY_DEMO_1"
CONG_TY = {"CT_DEMO_A": "PN_DEMO_A", "CT_DEMO_B": "PN_DEMO_B"}
NGAN_HANG = {"PN_DEMO_A": "NH_DEMO.A", "PN_DEMO_B": "NH_DEMO.B"}  # ObjectID ngân hàng cho vay trong danh mục DEMO của PN
DU_AN = {"PN_DEMO_A": "DA_KCN_DEMO", "PN_DEMO_B": "DA_NHA_DEMO"}


def native_demo(**bien_the) -> dict:
    v = {
        "version": 6, "exportedAt": "2026-10-16T08:00:00+07:00", "seqS": 1001, "seqL": 2001, "shortLoans": [], "rates": [], "bankCfg": {}, "manualRows": [],
        "longLoans": [
            {"maKV": "KV-A-01", "nhom": "DAI_HAN", "congTy": "CT_DEMO_A", "nganHang": "NH_DEMO", "soHD": "HDTD-DEMO-A-01", "duAn": "DA_KCN_DEMO",
             "tienTe": "VND", "hanMuc": 100000000, "kyHan": "36 tháng", "anHan": "6 tháng", "quyUocTinhLai": "DEMO thực tế/365", "trangThai": "Đang vay",
             "duNoSaoKe": 100000000, "ngaySaoKe": "2026-09-30", "tsdb": "", "ghiChu": "DEMO", "updatedAt": "2026-09-30T10:00:00+07:00", "updatedBy": "DEMO"},
            {"maKV": "KV-B-01", "nhom": "DAI_HAN", "congTy": "CT_DEMO_B", "nganHang": "NH_DEMO", "soHD": "HDTD-DEMO-B-01", "duAn": "DA_NHA_DEMO",
             "tienTe": "VND", "hanMuc": 50000000, "kyHan": "24 tháng", "anHan": "", "quyUocTinhLai": "DEMO", "trangThai": "Đang vay",
             "duNoSaoKe": 50000000, "ngaySaoKe": "2026-09-30", "tsdb": "", "ghiChu": "DEMO", "updatedAt": "2026-09-30T10:00:00+07:00", "updatedBy": "DEMO"}],
        "kheUoc": [
            {"maKV": "KV-A-01", "maKheUoc": "KU-A-01", "ngayGiaiNgan": "2026-09-01", "soTien": 60000000, "ghiChu": "", "updatedAt": "", "updatedBy": ""},
            {"maKV": "KV-A-01", "maKheUoc": "KU-A-02", "ngayGiaiNgan": "2026-09-15", "soTien": 40000000, "ghiChu": "", "updatedAt": "", "updatedBy": ""},
            {"maKV": "KV-B-01", "maKheUoc": "KU-B-01", "ngayGiaiNgan": "2026-09-05", "soTien": 50000000, "ghiChu": "", "updatedAt": "", "updatedBy": ""}],
        "lichGoc": [  # S01: hai DRAW cùng kỳ 1 của một HĐ — hai nghĩa vụ phân biệt 12.000.000 + 8.000.000
            {"maKV": "KV-A-01", "maKheUoc": "KU-A-01", "kySo": 1, "ngayDenHan": "2026-10-15", "soTienGoc": 12000000, "ghiChu": ""},
            {"maKV": "KV-A-01", "maKheUoc": "KU-A-02", "kySo": 1, "ngayDenHan": "2026-10-15", "soTienGoc": 8000000, "ghiChu": ""},
            {"maKV": "KV-B-01", "maKheUoc": "", "kySo": 1, "ngayDenHan": "2026-11-05", "soTienGoc": 10000000, "ghiChu": ""}],
        "laiSuat": [  # S06: hai mốc giữ lịch sử; không dùng lãi cuối cho kỳ cũ
            {"maKheUoc": "KU-A-01", "apDungTuNgay": "2026-01-16", "laiSuat": 7.5, "ghiChu": ""},
            {"maKheUoc": "KU-A-01", "apDungTuNgay": "2026-04-01", "laiSuat": 7.2, "ghiChu": ""},
            {"maKheUoc": "KU-B-01", "apDungTuNgay": "2026-09-05", "laiSuat": 8, "ghiChu": ""}],
        "phatSinh": [  # S17: 12.000.000 gốc + 800.000 lãi + 50.000 phí = 12.850.000, tham chiếu DEMO-REF-01 (bằng chứng, chưa là tiền)
            {"id": "PS-A-01", "ngay": "2026-10-15", "maKV": "KV-A-01", "maKheUoc": "KU-A-01", "traGoc": 12000000, "traLai": 800000, "phi": 50000,
             "soChungTu": "DEMO-REF-01", "ghiChu": "", "updatedAt": "", "updatedBy": ""}],
        "hopDongMua": [
            {"id": "HDM-DEMO-01", "maHDM": "HDM-DEMO", "soHD": "MUA-DEMO-01", "ngayHD": "2026-08-20", "loaiHD": "NHAP_KHAU", "loaiHang": "THIET_BI",
             "hinhThucVay": "LC", "congTyMua": "CT_DEMO_A", "duAn": "DA_KCN_DEMO", "maHDTDLienKet": "", "nhaCungCap": "NCC DEMO", "tienTe": "USD",
             "paymentTerm": "LC 90", "nganHang": "NH_DEMO", "maHang": "TB-DEMO", "tenHang": "Thiết bị DEMO", "soLuong": 1, "triGia": 250000000,
             "soToKhai": "", "soHoaDon": "", "ngayThanhToan": "", "donGia": 10000, "triGiaNT": 10000, "tyGia": 25000, "eta": "", "etd": "",
             "ngayNhanHang": "", "xuatXu": "DEMO", "ghiChu": "", "updatedAt": "", "updatedBy": ""}],
        "vayNH": [  # RC2: LC đã mở — chưa nhận nợ/giải ngân; nguyên tệ USD và VND nguồn là hai đại lượng riêng
            {"id": "NH-A-01", "soNhanNo": "", "congTy": "CT_DEMO_A", "nganHang": "NH_DEMO", "nhaCungCap": "NCC DEMO", "tenHang": "Thiết bị DEMO",
             "soVay": "", "soDaTra": "", "tienTe": "USD", "soNguyenTe": 10000, "ngayNhanNo": "", "kyHan": "90 ngày", "ngayDenHan": "",
             "laiSuat": "", "quyUocTinhLai": "", "trangThai": "LC đã mở", "soLC": "LC-DEMO-01", "ngayTraNoThucTe": "", "maLienKet": "HDM-DEMO",
             "soToKhai": "", "soHoaDon": "", "trangThaiHang": "", "ngayMoLC": "2026-09-10", "tyGia": 25000, "chiTiet": "", "ghiChu": "",
             "updatedAt": "", "updatedBy": ""}],
        "hanMuc": [{"id": "HM-DEMO-01", "nganHang": "NH_DEMO", "congTy": "CT_DEMO_A", "loaiHanMuc": "DEMO", "hanMucDuocCap": 500000000,
                    "hieuLucTu": "2026-01-01", "hieuLucDen": "2026-12-31", "ghiChu": "", "updatedAt": "", "updatedBy": ""}],
    }
    if bien_the.get("lc_nhan_no"):  # cùng VayNganHan.id chuyển sang nhận nợ — giữ alias/HĐ, phiên bản mới
        v["vayNH"][0].update({"trangThai": "Đang vay", "soNhanNo": "NN-DEMO-01", "ngayNhanNo": "2026-10-01", "ngayDenHan": "2026-12-30", "soVay": 250000000})
        v["exportedAt"] = "2026-10-17T08:00:00+07:00"
    if bien_the.get("loan_overlap"):  # S05: thêm lịch LOAN 20.000.000 bao phủ hai DRAW
        v["lichGoc"].append({"maKV": "KV-A-01", "maKheUoc": "", "kySo": 1, "ngayDenHan": "2026-10-15", "soTienGoc": 20000000, "ghiChu": ""})
    if bien_the.get("phat_sinh_trung"):  # S03: cùng id cùng payload
        v["phatSinh"].append(copy.deepcopy(v["phatSinh"][0]))
    if bien_the.get("phat_sinh_xung_dot"):  # S04: cùng id, gốc khác 1 VND
        v["phatSinh"].append({**copy.deepcopy(v["phatSinh"][0]), "traGoc": 12000001})
    if bien_the.get("rate_mo_ho"):  # S16: cùng mã khế ước dưới hai HĐ, mốc lãi chỉ có mã khế ước
        v["kheUoc"].append({"maKV": "KV-B-01", "maKheUoc": "KU-A-01", "ngayGiaiNgan": "2026-09-06", "soTien": 1000000, "ghiChu": "", "updatedAt": "", "updatedBy": ""})
    if bien_the.get("exact_text"):  # S09: text exact lớn, không qua Number
        v["longLoans"][0]["duNoSaoKe"] = "9007199254740993"
    if bien_the.get("number_mat"):  # S10: payload đã qua Number (2^53) — precision chưa chứng minh
        v["longLoans"][0]["duNoSaoKe"] = 9007199254740992
    if bien_the.get("draw_doi_so"):  # revision có ý nghĩa: số giải ngân KU-A-02 đổi
        v["kheUoc"][1]["soTien"] = 45000000
    if bien_the.get("thieu_key"):  # S19: thiếu sáu key native
        for k in ("seqS", "seqL", "shortLoans", "rates", "bankCfg", "manualRows"):
            v.pop(k)
    if bien_the.get("profile_root"):  # S14: lịch gốc root không có maKheUoc
        for r in v["lichGoc"]:
            r.pop("maKheUoc")
    return v


def bang_lai_demo(lai: str = "800000", phi: str = "50000") -> dict:
    """Lãi/phí kỳ 1 của KU-A-01 ĐÃ XÁC NHẬN (DEMO) — số text exact, có giấy báo; dùng làm nghĩa vụ LAI/PHI, không tính từ lãi suất."""
    return {"format": "ktt-bang-lai-demo-v1", "demo": True, "exportedAt": "2026-10-14T09:00:00+07:00", "rows": [
        {"id": "BL-A-01", "congTy": "CT_DEMO_A", "maKV": "KV-A-01", "maKheUoc": "KU-A-01", "ky": 1, "tuNgay": "2026-09-01", "denNgay": "2026-10-15",
         "cauPhan": "LAI", "soTien": lai, "tienTe": "VND", "soGiayBao": "GB-DEMO-01"},
        {"id": "BL-A-02", "congTy": "CT_DEMO_A", "maKV": "KV-A-01", "maKheUoc": "KU-A-01", "ky": 1, "tuNgay": "2026-09-01", "denNgay": "2026-10-15",
         "cauPhan": "PHI", "soTien": phi, "tienTe": "VND", "soGiayBao": "GB-DEMO-01"}]}


def bytes_cua(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=1).encode("utf-8")


MAU = {  # mẫu DEMO allowlist cho API/UI (không nhận đường dẫn/URL tùy ý)
    "native_v6": ("VAY_DEPLOY_20260922_NATIVE_JSON_V6", lambda: native_demo()),
    "native_v6_lc_nhan_no": ("VAY_DEPLOY_20260922_NATIVE_JSON_V6", lambda: native_demo(lc_nhan_no=True)),
    "native_v6_doi_so_giai_ngan": ("VAY_DEPLOY_20260922_NATIVE_JSON_V6", lambda: native_demo(draw_doi_so=True)),
    "native_v6_loan_drawoverlap": ("VAY_DEPLOY_20260922_NATIVE_JSON_V6", lambda: native_demo(loan_overlap=True)),
    "native_v6_thieu_key": ("VAY_DEPLOY_20260922_NATIVE_JSON_V6", lambda: native_demo(thieu_key=True)),
    "native_root_khong_ho_tro": ("VAY_DEPLOY_20260922_NATIVE_JSON_V6", lambda: native_demo(profile_root=True)),
    "bang_lai_xac_nhan": ("M9_BANG_LAI_XAC_NHAN_DEMO_V1", lambda: bang_lai_demo()),
}

# BANK M1 DEMO cho M9 (đi qua đường M1 hiện có + bộ chiếu): tiền đi trả gốc+lãi+phí và tiền về giải ngân
SAO_KE_M9 = {
    "PN_DEMO_A": {
        "tra_no_ky_1": [("DEMO-REF-01", "2026-10-15", -12_850_000, "DEMO TRA NO KV-A-01 KY 1 DEMO-REF-01")],
        "giai_ngan_ku_a_01": [("DEMO-GN-KU-A-01", "2026-09-01", 60_000_000, "DEMO GIAI NGAN KU-A-01")],
    },
}
