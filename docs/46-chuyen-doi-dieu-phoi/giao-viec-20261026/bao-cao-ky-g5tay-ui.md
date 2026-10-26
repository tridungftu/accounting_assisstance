Đã xong, Anh. Chỉ sửa `crm_g.js` và `tests/crm_ky_ket_async.cjs`, UTF-8 không BOM.

- Thêm xác nhận kiểm tay, kiểm lý do, khóa biên nhận, tải lại sau thành công, câu Việt cho 409/403 và kết quả kèm người/ngày giờ.
- Cả **3/3 bộ test yêu cầu đạt**, không lỗi mới trong phạm vi đã chạy; `git diff --check` đạt.
- Đã thử bằng mock DOM; chưa thử trình duyệt/PG. Không mở server, không commit.

Thông điệp commit đề xuất: `[KY-G5TAY-UI] Thêm xác nhận đã kiểm tay cho bản ký chỉ có DOCX`