Anh, đã hoàn tất MTQ-2d trong đúng 4 tệp được phép:

- Bổ sung mã lỗi 409/400, thông báo theo ngữ cảnh, `la_admin` từ SQL và lý do từ chối có nghĩa.
- Ghi chú khôi phục bằng `NHAP` + `CONG_BO`; không thêm route.
- Bổ sung test nghiệp vụ, CSRF âm và PG qua SQL thật.

**Test:** 62 đạt/95, 33 skip do thiếu điều kiện PG; không có lỗi mới. `git diff --check` đạt; 4/4 tệp UTF-8 không BOM. PG chưa được kiểm chứng thực tế.

Không commit, không mở server/PostgreSQL, không sửa SQL/migration.

Thông điệp commit đề xuất: `[MTQ-2d] Chuẩn hóa lỗi thẩm quyền và bổ sung trạng thái Admin theo phiên`