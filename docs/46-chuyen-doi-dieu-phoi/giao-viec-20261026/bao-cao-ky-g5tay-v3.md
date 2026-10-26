Anh, đã sửa M0037. **Nguyên nhân thực tế là lỗi cú pháp `IF NOT CASE …` thiếu ngoặc tại dòng 32**, khi kiểm trạng thái việc theo hồ sơ; không phải điều kiện G5 tự động.

- Tạo lại `kho.crm_kiem_viec_kiem()` và `master.crm_kiem_ho_so_kiem()` bằng thay chuỗi có kiểm đúng một vị trí, thêm ngoặc CASE. Giữ nguyên quyền, trạng thái, revision và E5.
- Đổi 4 tệp theo handoff; cập nhật test so thân hàm hiện hành cho cả hai schema. Migration 1–36 nguyên byte; UTF-8 không BOM; `diff --check` đạt.
- Test: **55 đạt/73, 18 skip, không lỗi mới**. p01/p07 chưa chạy PG; lead cần xác nhận.

Không commit. Thông điệp đề xuất: `[KY-G5TAY] vòng 3: sửa cú pháp CASE trong hai guard G6, giữ nguyên điều kiện kiểm tay G5`.