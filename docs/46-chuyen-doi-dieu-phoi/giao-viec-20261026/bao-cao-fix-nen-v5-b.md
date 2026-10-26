Anh, tôi đã chỉ sửa `tests/test_m9_ocr_hot_folder.py`: gốc UUID riêng từng ca, ABBYY giả nhận bằng `os.replace`, kiểm dọn tệp theo guard.
Giữ nguyên kiểm SHA, hạn mức, hủy, timeout, định dạng, ẩn đường dẫn và Event.
`git diff --check` đạt; UTF-8 không BOM; không commit, không xóa file.
Test thường và mô phỏng guard: **NOT_RUN** vì sandbox không có Python executable; chưa xác minh 21/21 hay lỗi mới so với nền.