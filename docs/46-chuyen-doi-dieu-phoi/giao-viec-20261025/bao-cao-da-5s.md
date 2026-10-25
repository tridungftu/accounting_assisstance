Anh, đã sửa đúng 3 tệp, UTF-8 không BOM.

- **Nguồn tên lỗi:** `crm_demo.py:60–61` cũ seed `"Dự án " + mã`; SQL ảnh chụp đọc `master.du_an.ten` tại `sql_crm_du_an_ban.py:598`.
- **Đã sửa:** `crm_demo.py:19,62` đặt hai tên yêu cầu, cập nhật tên trống/mã/tên mẫu cũ, giữ tên riêng. `crm_du_an_ban.py:32,260` dùng VND và tên dự phòng; danh sách/chi tiết/hiển thị ảnh chụp trả `du_an_ten`.
- **Test:** trước 57 = 56 đạt + 1 skip; sau 60 = 58 đạt + 2 skip. Không lỗi mới; PostgreSQL chưa kiểm chứng, để lead chạy. `git diff --check` đạt.
- Không sửa SQL/migration/giao diện, không commit. Thông điệp đề xuất: `[DA-5s] Hiển thị tên dự án và thống nhất đơn vị VND`.