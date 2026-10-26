Đã sửa đúng 3 tệp: test độc lập LF/CRLF, thêm migration B chống trùng request theo người/lệnh/ID đối tượng và index, kiểm quyền PUBLIC.
Giữ nguyên `MTQ_CONG_SQL`; UTF-8 không BOM, `pg_migrations.py` giữ LF.
Test: 23/61 đạt, 38 skip PostgreSQL; không lỗi mới; `git diff --check` đạt.
Giới hạn: đối tượng được đối chiếu bằng ID đã lưu; chưa kiểm runtime PostgreSQL.
Không commit. Thông điệp đề xuất: `[MTQ-4a0b] Ổn định test xuống dòng và chặn request từ chối trùng sai ngữ cảnh`.