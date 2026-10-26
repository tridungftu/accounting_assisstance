[MTQ-4a3a] vòng 3: thêm `SET CONSTRAINTS ALL IMMEDIATE` trước ALTER trong `tests/test_mtq_cong_c_sql.py`.
Giữ bước bật lại trigger trước kiểm và rollback như cũ; không đổi SQL nghiệp vụ.
Kiểm tra: `git diff --check` đạt; UTF-8 không BOM; chỉ đổi đúng 1 tệp.
Unittest chưa chạy được vì shell không tìm thấy `python`; PG chờ lead kiểm chứng.
Không commit, không mở server/PostgreSQL DEMO, không xóa file.