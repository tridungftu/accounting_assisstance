# Phiếu kiểm tra chức năng — mẫu dùng cho cổng A và cổng B

**Bản nháp 23/10/2026.** Lead điền phần 1–2 trước khi gửi Anh; Anh chỉ điền phần 3 (cổng A) hoặc cột "Kết quả" ở phần 4 (cổng B). Dữ liệu trên màn đều là DEMO.

- **Cổng A — kiểm chức năng sớm:** khung màn hình vừa chạy được. Mục đích: Anh thấy sớm chỗ sai cách làm việc để sửa ngay. Không chấm đạt/không đạt.
- **Cổng B — nghiệm thu:** chấm từng dòng checklist đã duyệt. Đạt hết dòng mức A mới chuyển sang làm phần cứng hóa và màn kế.

---

## 1. Thông tin lát (lead điền)

| Mục | Nội dung |
|---|---|
| Màn hình | ví dụ: CRM · Báo giá (CRM-G2) — M3 · Hóa đơn bán ra & doanh thu BĐS |
| Cổng | A / B |
| Căn cứ thiết kế | ví dụ: TL 42 §6; TL 45 BG-01…BG-14 |
| Phiên bản | nhánh + commit, ngày giờ |
| Cách mở | nhấp đúp `<tên file .cmd>` hoặc mở trong cửa sổ xem trước của Claude; địa chỉ `http://127.0.0.1:<cổng>` |
| Tài khoản thử | vai: Bán hàng / Kế toán / CFO / Xem (DEMO) |
| Đã biết chưa làm | liệt kê để Anh không mất công ghi lại |
| Thời gian thử dự kiến | ≤ 15 phút |

## 2. Các bước thử (lead điền 5–10 bước)

| # | Làm gì | Mong đợi |
|---|---|---|
| 1 | | |
| 2 | | |
| … | | |

## 3. Nhận xét của Anh — cổng A

Mỗi điểm một dòng. Anh có thể gõ thẳng trong chat theo mẫu `NX1 · bước 3 · mong đợi … · thấy … · P`; lead tự chép vào bảng.

| Mã | Bước / vị trí | Anh làm gì | Mong đợi | Thấy gì | Mức |
|---|---|---|---|---|---|
| NX1 | | | | | P / N / S |
| NX2 | | | | | |

Mức: **P** = phải sửa trước khi đi tiếp · **N** = nên sửa trong lát này · **S** = để sau, ghi hàng đợi.

**Kết luận cổng A (Anh chọn một):**
- [ ] Đi tiếp — sửa các điểm P/N rồi chuyển cổng B
- [ ] Sửa rồi cho xem lại cổng A lần nữa
- [ ] Sai hướng — dừng, bàn lại thiết kế

## 4. Checklist nghiệm thu — cổng B

Lead lấy từ thiết kế đã duyệt; không thêm tiêu chí kỹ thuật Anh không đọc được. Mức A = chặn nghiệm thu; mức B = sửa trong module; mức C = để sau.

| # | Tiêu chí (ngôn ngữ nghiệp vụ) | Mức | Cách thử | Kết quả (Đạt / Không / Ghi chú) |
|---|---|---|---|---|
| 1 | | A | | |
| 2 | | | | |

**Kết luận cổng B:** [ ] Nghiệm thu  [ ] Nghiệm thu có điều kiện (ghi điểm)  [ ] Chưa đạt

---

## 5. Ví dụ điền sẵn — màn Báo giá (theo TL 45)

### Bước thử cổng A (4 ca của TL 45 §5)

| # | Làm gì | Mong đợi |
|---|---|---|
| 1 | Tạo báo giá KCN theo bộ chuẩn dự án, chọn lô, tiền USD, nhập tỷ giá | Lịch tự nạp; Tổng giá trị tự tính; dòng tổng hiện Σ 100% và VND quy đổi; không bấm nút tính nào |
| 2 | Tạo báo giá nhà ở theo khách, tự nhập lịch | Không thấy Đơn giá/m², Diện tích; lịch 4 cột |
| 3 | Sửa một đợt để Σ% = 90 | Nút "In cho khách" và "Chuyển sang soạn hợp đồng" mờ, rê chuột thấy "Tổng % = 90, thiếu 10" |
| 4 | Đổi tỷ giá | Cột VND quy đổi và tổng VND đổi theo sau khi rời ô |

### Checklist cổng B (rút từ TL 45 §2, nhóm A và B)

| # | Tiêu chí | Mức | Cách thử |
|---|---|---|---|
| BG-01 | Lịch thanh toán 4 cột; mỗi dòng ≤ 4 ô nhập; số "Lần" tự đánh | A | Ca 1, 2 |
| BG-02 | Có dòng tổng Σ% và Σ tiền; Σ% ≠ 100 thì nút In/Chuyển mờ có lý do | A | Ca 3 |
| BG-03 | Máy tính tự động khi rời ô; không còn nút "Tính thử" | A | Ca 1, 4 |
| BG-04 | KCN: Tổng giá trị = Đơn giá × Diện tích; ghi đè có cảnh báo | A | Ca 1 |
| BG-05 | Không còn mã kỹ thuật trên màn; ngày dd/mm/yyyy; số có dấu chấm | A | Cả 4 ca |
| BG-06 | Trường hiện theo loại hình (KCN không thấy Phí bảo trì; nhà ở không thấy Diện tích) | A | Ca 1, 2 |
| BG-07 | Form 4 khối gấp/mở; báo giá KCN theo bộ chuẩn đụng ≤ 8 ô | B | Ca 1, đếm ô |
| BG-08 | Một ô tìm khách + nút "Khách mới" | B | Ca 2 |
| BG-09 | Chọn lô/căn từ danh mục; diện tích tự điền | B | Ca 1 |
| BG-10 | Chọn "Theo dự án" là có lịch, không cần nút nạp riêng | B | Ca 1 |
| BG-11 | Thuế lấy mặc định theo loại hình, chỉ sửa khi bấm "Khác" | B | Ca 1 |
| BG-12 | Tiền khác VND bắt buộc tỷ giá · ngày · người nhập; thiếu thì In mờ | B | Ca 4 |
| BG-13 | Thanh nút cố định: Lưu nháp · In cho khách · Chuyển sang soạn hợp đồng · Hủy | B | Cuộn trang |
| BG-14 | Ngăn kiểm bên phải, bấm lỗi nhảy tới ô | B | Ca 3 |

Còn mở theo TL 45 §7 (cần Anh quyết trước cổng B): ô thông minh khi gõ số ≤ 100 không có `%`; độ trễ tính tự động chấp nhận; hạn báo giá mặc định.
