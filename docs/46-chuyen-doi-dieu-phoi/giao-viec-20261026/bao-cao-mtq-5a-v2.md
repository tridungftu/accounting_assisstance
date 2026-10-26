Đã sửa đúng 3 tệp: bổ sung tick màn gốc, log sqlstate/mã MTQ đã lọc, thêm 2 ca PG chặn seed.
Test: 12 đạt/22; 9 skip PG; 1 ERROR thiếu `psycopg`, trùng nền; không lỗi mới.
UTF-8 không BOM, cú pháp và `git diff --check` đạt. Hai ca PG mới chưa chạy.
Không commit, không mở server/PostgreSQL, không xóa tệp.
Thông điệp commit đề xuất: `[MTQ-5a] vòng 2: bổ sung tick màn gốc, log mã lỗi và test chặn seed`.