Anh, đã hoàn tất MTQ-4i-a trên nhánh `lat/mtq-4i-a`, chưa commit.

- **Đã làm:** validator NGUON chuẩn hóa khóa; kiểm mapping hiện hành `COMPANY`/`WAREHOUSE` trong `master.anh_xa_nguon`, đúng PN/phòng; giữ guard và audit cấp/thu hồi. Docstring ghi rõ caller 4i-c phải kiểm đủ mọi PN.
- **File đổi:** đúng ba tệp được giao; append `M00xx_MTQ_LMOD_A`, giữ nguyên migration cũ.
- **Kiểm tra:** `git diff --check`, UTF-8 không BOM và LF đạt. Đã viết 18 test; **NOT_RUN** vì không có Python. Chưa xác định lỗi mới so nền.
- **Cần lead:** chạy test thuần/PG và đánh số migration khi gộp. Cả hai loại nguồn đều tìm thấy bảng ánh xạ.

Thông điệp commit đề xuất: `[MTQ-4i-a] Kiểm hợp lệ phạm vi nguồn theo ánh xạ hiện hành`