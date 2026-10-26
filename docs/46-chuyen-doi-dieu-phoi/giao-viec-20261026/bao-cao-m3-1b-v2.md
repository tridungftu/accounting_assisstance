Đã sửa duy nhất `tests/test_m3_dang_thuc.py`: tạo CSDL riêng, migrate, cleanup DROP; giữ rollback và các ca kiểm; UTF-8 không BOM.
`git diff --check` đạt; unittest chưa chạy được vì thiếu Python trong PATH, chưa xác minh lỗi mới; không mở PostgreSQL, không commit.
Thông điệp commit đề xuất: `[M3-1b] vòng 2: tạo CSDL PostgreSQL riêng từ DSN quản trị cho test ba đẳng thức`.