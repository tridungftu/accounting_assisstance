Anh, đã hoàn thành M9-1a đúng ba tệp: `m9/__init__.py`, `m9/tai_lieu_vay.py`, `tests/test_m9_tai_lieu_vay.py`.

- Đọc DOCX, bảng và ngắt trang; cắt điều/khoản/điểm; giữ nguyên số tiền/ngày; tạo mã đoạn ổn định và metadata.
- Test: **14/14 đạt**, gồm DOCX hỏng, loại tài liệu lạ, chuỗi cấm và UTF-8 không BOM. Không lỗi mới trong bộ test lát; chưa chạy toàn nền.
- Giới hạn: chỉ đếm ngắt trang tường minh, chưa dựng lại đánh số tự động Word.
- Không commit, gọi AI hay mở server.

Thông điệp commit đề xuất: `[M9-1a] Đọc DOCX và cắt điều khoản tài liệu vay`.