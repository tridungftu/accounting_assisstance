Anh, tôi đã chỉ sửa `tests/test_crm_42_s1_http.py`, UTF-8 không BOM.

- Thêm 2 hợp đồng DEMO hiệu lực tại A/B, qua nhận #6 → KT kiểm → CFO duyệt sinh lịch; mỗi hợp đồng có 1 đợt quá hạn và 1 đợt thuộc W5.
- Thêm 4 ca PG: KT thấy cờ/lọc đúng; XEM và KT thiếu M1 không suy ra qua cờ, `tong`, thẻ; trộn phạm vi A/B; kiểm scalar SQL trước lớp Python.
- Test thuần: **13 đạt, 0 lỗi; 11 ca PG skip**, chờ lead chạy. Kiểm fixture bằng bộ phân tích thật và `git diff --check` đạt.
- Không commit. Thông điệp đề xuất: `[C3d] Bổ sung test quá hạn S1 và che cờ theo quyền xem tiền`.