Anh, `5 != 3` là **test ghim sai số bảng**, không phải migration chạy lặp: MTQ thêm hai bảng vào `nhat_ky` ngay lần đầu; `migrate()` bỏ qua migration đã áp dụng.

- **Đã sửa:** `test_pg_schema.py` so trạng thái trước/sau; `test_mtq_sql.py` kiểm MTQ theo `len(old)`, xuất hiện đúng một lần và thêm regression PG so dữ liệu/lịch sử. SQL migration và checksum giữ nguyên.
- **Docstring:** bootstrap chỉ khi `mtq_admin` chưa từng có dòng; `session_user` thuộc vai chủ bảng; `cap_boi = p_nguoi`. **MTQ-2 không mở bootstrap qua HTTP**, chỉ công cụ lead.
- **Kiểm tra:** 12/51 test đạt, 39 PG skip; không có lỗi. Mock xác nhận test chấp nhận 5→5, chặn 5→6; UTF-8 không BOM, diff sạch. PG thực tế chờ lead chạy.

Không commit. Thông điệp đề xuất: `[MTQ-1] vòng 2: sửa test idempotent và làm rõ bootstrap`.