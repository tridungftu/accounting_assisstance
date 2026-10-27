**Lead (Claude) quyết các điểm "Cần lead" của KK-UI-DA-BG (27/10 ~16:10):**

1. **Nhánh và migration:** các lát backend (DA-B1…B4, TEN-B1/B2, BG-B1/B2, BG-IN) làm trên `hop-nhat-20261023`; lead cấp số migration khi gộp. Xong backend → `lat/ui-dem` nhận bản hợp nhất → các lát JS (DA-U1/U2, TEN-U, BG-U) làm trên `lat/ui-dem`, rồi lead mở lại DEMO 8798 cho Anh thử.
2. **Đợt cọc ở dòng cuối hoặc lịch chỉ một dòng:** chặn, lỗi rõ tại ô cọc ("Đợt đặt cọc cần có đợt thanh toán kế tiếp để nhận phần VAT"); không tự dồn ngược, không tự thêm đợt.
3. **Nhiều bộ chuẩn G7, không có mặc định:** không tự chọn. Màn khai báo cho người dùng chọn một lần; lưu vào tiến độ chuẩn của dự án.
4. **Tạo dự án gốc `master.du_an`:** giữ luồng hiện có (chọn dự án kế toán đã có để bật bán). Danh mục gốc thuộc M0, không mở rộng ở đợt này; lead ghi vào báo cáo cho Anh.
5. **CD-019 "một engine":** hàm tính lịch thanh toán (% / VAT / cọc / làm tròn) là **một** chỗ dùng chung cho Báo giá, bản in, chuyển Soạn hợp đồng và tiến độ dự án nạp vào Báo giá. Không tính lại ở JS ngoài phần hiển thị tạm.
