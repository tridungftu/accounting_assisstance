Anh, đã hoàn thành M4-DL1b trong đúng 3 tệp được giao:

- Thêm UNIQUE, `chup_luc` bắt buộc, index và hàm chọn bản hiện hành có tính HĐ đã xóa; giữ nguyên byte SQL M0038.
- Cập nhật docstring và test. UTF-8 không BOM; `pg_migrations.py` giữ LF.
- **Test:** 45 test — 9 đạt, 36 PG skip; không lỗi mới trong bộ đã chạy. `git diff --check` đạt.
- **Cần Anh:** xác nhận dùng một CSDL Review; nếu nhiều CSDL cần cột phân biệt nguồn.

Không tạo commit. Thông điệp đề xuất: `[M4-DL1b] Bổ sung khóa lần chụp và bản Review hiện hành`.