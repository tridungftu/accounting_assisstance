Anh, đã hoàn thành M9-4a, chỉ thêm đúng hai tệp được giao: `bao_cao_lai_suat.py` và `test_m9_bao_cao_lai_suat.py`, UTF-8 không BOM.

- Tính bình quân riêng từng đồng tiền, giữ `Decimal`, đánh dấu dữ liệu thiếu, cảnh báo kỳ điều chỉnh và xuất Excel một sheet.
- Test: **18/18 đạt**, không có lỗi trong phạm vi đã chạy; chưa chạy toàn bộ nền. Đã đọc lại Excel, kiểm tra ô số/ngày, làm tròn và không có công thức.
- **Cần Anh/lead:** nối M9-2/M9-3; chốt số lẻ tiền ngoài VND/USD.
- Chưa commit. Thông điệp đề xuất: `[M9-4a] Tính lãi cao theo snapshot và xuất Excel`.