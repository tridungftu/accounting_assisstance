"""Nối tìm kiếm và hỏi đáp vay; nhật ký chỉ chứa câu hỏi và metadata."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import hoi_dap_vay


def hoi(cau_hoi, *, chi_muc, cong_ai, nguoi_hoi: str,
        loc_tai_lieu=None, so_ket_qua=5, ghi_nhat_ky) -> dict:
    """Tìm câu gốc, hỏi qua cổng Local và ghi nhật ký một lần khi có kết quả.

    Chuyển nguyên loc_tai_lieu xuống chỉ mục. Không truyền bộ lọc vẫn chạy
    cả khi chỉ mục có nhiều pháp nhân; lọc quyền là trách nhiệm tầng gọi.
    ghi_nhat_ky là callable do tầng gọi cấp; module không tự lưu ra đĩa/CSDL.
    Bản ghi có giờ Việt Nam (ISO, UTC+07:00), không có câu trả lời/câu trích.
    """
    luc = datetime.now(timezone(timedelta(hours=7))).isoformat()
    tim_duoc = chi_muc.tim(
        cau_hoi, loc_tai_lieu=loc_tai_lieu, so_ket_qua=so_ket_qua,
    ) if cau_hoi.strip() else []
    ket_qua = hoi_dap_vay.tra_loi(
        cau_hoi, [muc["trich_dan"] for muc in tim_duoc], cong_ai=cong_ai,
    )
    ghi_nhat_ky({
        "nguoi_hoi": nguoi_hoi,
        "luc": luc,
        "cau_hoi": cau_hoi,
        "trang_thai": ket_qua["trang_thai"],
        "so_trich_dan": len(ket_qua["trich_dan"]),
        "ma_doan_trich_dan": [
            muc["ma_doan"] for muc in tim_duoc
            if muc["trich_dan"] in ket_qua["trich_dan"]
        ],
    })
    return ket_qua
