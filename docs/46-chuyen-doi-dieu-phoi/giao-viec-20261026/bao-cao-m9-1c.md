Anh, đã hoàn thành M9-1c trên nhánh `lat/m9-1c`, chưa commit.

- **Tệp mới:** `src/kho_tri_thuc/m9/ocr_hot_folder.py` và `tests/test_m9_ocr_hot_folder.py`; UTF-8 không BOM.
- **Đã làm:** đệm SHA256, hạn mức trang, khóa theo thư mục, hủy/timeout, nhận DOCX ổn định và dọn file theo mã.
- **Test:** 45/45 đạt trong 6,38 giây, gồm 21 test OCR giả lập; không có lỗi mới trong phạm vi chạy. Không chạy ABBYY thật.
- **Cần Anh/lead:** có gộp sổ đếm M9 và Review không; hiện hai sổ tách nhau dù dùng chung giấy phép. Khóa hiện bảo vệ trong cùng tiến trình.

Thông điệp commit đề xuất: `[M9-1c] Thêm bộ nối OCR ABBYY Hot Folder riêng cho M9`.