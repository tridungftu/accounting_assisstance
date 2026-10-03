# Hướng dẫn dùng màn hình Định khoản (V10)

Phần mềm chạy trên máy này, không gửi dữ liệu ra ngoài. **Phần mềm không tự nhập Junsky**: chỉ tạo File soát (Excel) gồm các giao dịch đã bấm Đồng ý.

## Mở phần mềm
- Dùng thật: bấm đúp **MỞ PHẦN MỀM.cmd**. Thanh trên ghi **KHO THẬT**.
- Chạy thử tháng 8: bấm đúp **MỞ PHẦN MỀM THỬ T8.cmd**. Thanh trên ghi **KHO THỬ**. Bản thử chạy độc lập, không đụng kho thật.
- Lần đầu mở, góc phải hiện “Đang nạp dữ liệu nền từ Junsky…” trong khoảng 1 phút. Vẫn thả file được; phần mềm chờ nạp xong rồi mới đề xuất.

## Một vòng làm việc
1. **Thả sao kê**: kéo file sao kê Excel vào ô lớn, hoặc bấm vào ô để chọn file. Thanh tiến độ hiện “Đang đề xuất x/y”.
2. **Xem bốn ô tổng**:
   - **Xanh**: đủ căn cứ.
   - **Vàng**: cần xem, thường có “Phương án 1, 2…”.
   - **Đỏ**: thiếu tài khoản đối ứng.
   - **Đã có trong Junsky**: không cần duyệt, không được xuất.
   - Bấm vào ô nào thì danh sách lọc theo mức đó.
3. **Duyệt từng dòng**:
   - **Đồng ý**: chỉ bấm được khi Nợ = Có và các TK công nợ đã có đối tượng. Chưa đủ thì nút mờ; rê chuột vào để xem lý do. Sau khi bấm có nút **Hoàn tác** trong vài giây.
   - **Sửa**: mở ngăn bên phải. Ở đây chọn tài khoản, đối tượng, dự án, khoản mục, TTCP (gõ mã hoặc tên, gõ không dấu vẫn ra) và thêm/bớt dòng. Xong bấm **Lưu và đồng ý**.
   - **Ghi nhớ cho lần sau** (bật sẵn): máy học cách hạch toán này, áp dụng ngay cho các giao dịch đang chờ cùng số tài khoản đối ứng và cho các tháng sau.
   - **Bỏ qua**: giao dịch để kế toán hạch toán tay; lý do ghi hay không đều được.
   - **Dòng Đỏ**: bấm một gợi ý “TK hay gặp…” để điền nhanh, rồi Đồng ý.
   - **Dòng Vàng có phương án**: bấm “Dùng phương án này”, rồi Đồng ý.
   - **Mở lại / Duyệt lại**: đưa giao dịch đã quyết định về Chờ duyệt. Dòng đã xuất file thì không mở lại được.
4. **Đồng ý hàng loạt**: nút “Đồng ý tất cả dòng Xanh đang lọc”. Hộp xác nhận ghi rõ số giao dịch và tổng tiền.
5. **Xuất file**: bấm “Xuất file” rồi “Xuất”. File soát nằm trong thư mục ghi trên màn hình (nút **Mở thư mục**, **Tải về**).
   - Xuất được nhiều lần; mỗi lần chỉ gồm các giao dịch mới đồng ý.
   - Kế toán nhập Junsky theo file này.

## Phím tắt
Bấm vào danh sách trước, rồi dùng:

| Phím | Việc |
|---|---|
| ↑ / ↓ | Chuyển giao dịch |
| Enter | Mở / đóng chi tiết |
| A | Đồng ý |
| E | Sửa |
| S | Bỏ qua |

## Màn hình Nguồn dữ liệu
- **Nạp lại**: bấm sau khi xuất sổ hoặc danh mục mới từ Junsky.
- **Mốc học**:
  - Để trống: máy học toàn bộ sổ. Dùng khi chạy thật.
  - Điền ngày: máy chỉ học đến ngày đó. Bản thử T8 điền 30/06/2026.
  - Đổi mốc xong, bấm “Đề xuất lại” ở màn hình Định khoản.
- **Tài khoản ngân hàng ↔ tài khoản kế toán**: số tài khoản ngân hàng của sao kê phải được gắn với TK 112 chi tiết (đang dùng 112111). Nếu thiếu, giao dịch báo “Thiếu TK tiền”.
- **TK công nợ bắt buộc có đối tượng**: danh sách chờ CFO xác nhận.

## Khi gặp lỗi
Màn hình ghi lỗi bằng một câu, kèm việc cần làm và nút sang màn hình xử lý. Nếu báo “Phiên giao diện đã đổi”, nhấn F5 để tải lại trang.
