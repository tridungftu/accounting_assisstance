# Câu lệnh cho Claude Design — màn hình Định khoản

Cách dùng: copy nguyên khối `text` dưới đây, dán vào Claude Design. Dữ liệu trong câu lệnh là dữ liệu giả, không có tên công ty, đối tác hay số tài khoản thật.

```text
Thiết kế giao diện cho một phần mềm hỗ trợ kế toán chạy cục bộ trên máy tính Windows (mở bằng trình duyệt tại localhost), dùng cho CFO và kế toán của một công ty kinh doanh hạ tầng khu công nghiệp tại Việt Nam.

MỤC ĐÍCH: người dùng thả file sao kê ngân hàng (sau này cả hóa đơn điện tử) → phần mềm đề xuất bút toán cho từng giao dịch → người dùng duyệt TỪNG giao dịch ngay trên màn hình (Đồng ý / Sửa / Bỏ qua) → xuất file để nhập vào phần mềm kế toán Junsky. Phần mềm không bao giờ tự nhập Junsky; chỉ giao dịch đã Đồng ý mới được xuất.

NGƯỜI DÙNG: không phải kỹ thuật viên, không gõ lệnh, chỉ bấm chuột. Mỗi tháng duyệt khoảng 100–150 giao dịch. Nhìn một giao dịch phải hiểu ngay máy đề xuất gì và vì sao.

QUY ƯỚC: giao diện tiếng Việt; ngày dd/mm/yyyy; tiền VND, phân cách hàng nghìn bằng dấu chấm, không số lẻ; màn hình máy tính 1366–1920px, không cần bản di động; tông sáng, chuyên nghiệp, chữ đủ lớn để đọc bảng số; màu mức tin cậy luôn đi kèm biểu tượng và chữ, không chỉ dựa vào màu.

RÀNG BUỘC BẢN BÀN GIAO: HTML + CSS + JavaScript thuần (không React, không framework); không tải font, icon hay thư viện từ internet vì máy có thể không có mạng; dùng font hệ thống. Kèm danh sách thành phần và trạng thái để lập trình viên dựng lại trong ứng dụng có sẵn.

========== CẤU TRÚC CHUNG ==========
- Thanh trên: tên phần mềm "Kho tri thức kế toán"; nhãn "KHO THẬT"; dòng nhỏ "Không tự nhập Junsky — chỉ tạo file". Góc phải: tình trạng dữ liệu nền "Sổ Junsky đến 29/08/2026 · Máy học đến 30/06/2026".
- Menu trái, luôn hiện chữ: 1. Định khoản (màn hình chính) · 2. Nguồn dữ liệu · 3. Tra cứu tri thức · 4. Lịch sử xuất file.

========== MÀN HÌNH 1 — ĐỊNH KHOẢN (thiết kế kỹ nhất) ==========
A. VÙNG NHẬP FILE (trên cùng)
- Ô lớn "Thả file vào đây hoặc bấm để chọn". Nhận: sao kê (.xlsx, .xls), hóa đơn XML (nhiều file hoặc cả thư mục), bảng kê. Phần mềm tự nhận loại file, không hỏi.
- Sau khi thả: thẻ tóm tắt "Sao kê ngân hàng · TK 1121 · 01/08/2026–31/08/2026 · 105 giao dịch · Số dư đầu–cuối khớp ✓".
- Khi đang xử lý: thanh tiến trình "Đang đề xuất 63/105…".
- Bên dưới: danh sách "Đã làm gần đây" để mở lại.

B. THANH TỔNG
- Bốn ô: Xanh (đủ căn cứ) · Vàng (cần xem) · Đỏ (thiếu căn cứ) · Đã có trong Junsky. Mỗi ô có số giao dịch và tổng tiền; bấm vào ô là lọc theo mức đó.
- Thanh tiến độ "Đã duyệt 42/105".
- Nút "Xuất file" ở góc phải.

C. BỘ LỌC
- Mức · Trạng thái (Chờ duyệt / Đã đồng ý / Đã bỏ qua / Đã có trong Junsky) · Chiều (Thu / Chi) · ô tìm kiếm (diễn giải, đối tượng, số tiền).

D. DANH SÁCH GIAO DỊCH
Mỗi giao dịch là một dòng thu gọn; bấm để mở chi tiết ngay tại chỗ.
- Dòng thu gọn: Ngày · Thu/Chi và Số tiền · Diễn giải gốc (cắt một dòng) · Đối tượng (mã – tên) · Bút toán tóm tắt "Nợ 6427 / Có 1121" · nhãn mức · ba nút ngay trên dòng: [Đồng ý] [Sửa] [Bỏ qua].
- Phần mở rộng:
  · Bảng bút toán: Nợ/Có · Tài khoản (mã – tên) · Số tiền · Đối tượng · Dự án · Khoản mục · Trung tâm chi phí. Có thể nhiều dòng (ví dụ phí ngân hàng: Nợ 6427 + Nợ 1331 / Có 1121). Dòng tổng Nợ = Có; báo đỏ nếu lệch.
  · "Vì sao": một câu tiếng Việt, ví dụ "5/5 chứng từ cũ giống nhất hạch toán Nợ 6427 + 1331" hoặc "Số tài khoản đối ứng thuộc đối tượng KH.ALPHA theo danh bạ (độ tin cậy Cao)". Nút "Xem căn cứ" mở danh sách chứng từ cũ được dùng (ngày, số chứng từ, diễn giải, hạch toán).
  · Giao dịch Vàng: hiện phương án 2 (và 3) dạng thẻ nhỏ có nút "Dùng phương án này".
  · Giao dịch Đỏ: các ô thiếu để trống, viền đỏ, ghi rõ "Thiếu: tài khoản đối ứng" và gợi ý "TK hay gặp cho chi tiền: 331 · 6427 · 141" (bấm là điền).
  · Giao dịch "Đã có trong Junsky": làm mờ, hiện số chứng từ Junsky, không có nút Đồng ý.

E. HÀNH VI NÚT
- Đồng ý: chỉ bấm được khi Nợ = Có và tài khoản công nợ (131, 331, 141, 344…) đã có đối tượng. Chưa đủ thì nút mờ, rê chuột hiện lý do. Bấm xong: dòng chuyển "Đã đồng ý" (dấu tích, nền nhạt), có "Hoàn tác" vài giây, rồi tự chuyển sang giao dịch chờ duyệt kế tiếp.
- Sửa: mở ngăn bên phải, không rời màn hình. Các ô chọn có tìm kiếm theo mã hoặc tên trong danh mục (tài khoản, đối tượng, dự án, khoản mục, trung tâm chi phí); thêm/bớt dòng bút toán; kiểm tra Nợ = Có ngay khi sửa. Ô tích "Ghi nhớ cho lần sau: áp dụng cho các giao dịch cùng số tài khoản đối ứng" (mặc định bật). Nút "Lưu và đồng ý".
- Bỏ qua: hỏi lý do ngắn (không bắt buộc); giao dịch để kế toán hạch toán tay.
- Phím tắt: ↑/↓ chuyển giao dịch, Enter mở/đóng, A đồng ý, E sửa, S bỏ qua.
- Đồng ý hàng loạt: nút "Đồng ý tất cả dòng Xanh đang lọc" → hộp xác nhận ghi rõ "Anh sắp đồng ý 25 giao dịch, tổng 1.234.567.890 VND".

F. XUẤT FILE
- Hộp thoại: số giao dịch đã đồng ý / còn chờ duyệt (cảnh báo nếu còn chờ).
- Lựa chọn "File soát (Excel)": luôn bật.
- Lựa chọn "File nhập Junsky (Phiếu thu / Phiếu chi ngân hàng)": tạm khóa, ghi "Mở sau khi nhập thử thành công".
- Nút Xuất; sau khi xuất hiện đường dẫn file và nút "Mở thư mục".

========== MÀN HÌNH 2 — NGUỒN DỮ LIỆU ==========
Các thẻ trạng thái, mỗi thẻ có ngày cập nhật, nút "Nạp lại", và lỗi (nếu có) viết bằng một câu tiếng Việt kèm việc cần làm:
- Sổ Junsky (đến ngày) · Danh sách chứng từ công nợ (đến ngày) · Danh mục đối tượng, tài khoản, khoản mục, dự án, trung tâm chi phí · Danh bạ đối tác (số tài khoản ngân hàng đã biết).
- Mốc học: "Máy học từ sổ đến 30/06/2026" — đổi bằng ô chọn ngày.
- Tài khoản ngân hàng ↔ tài khoản kế toán: bảng số tài khoản ngân hàng → TK 1121.

========== MÀN HÌNH 3 — TRA CỨU TRI THỨC ==========
Ô tìm theo số tài khoản, tên đối tượng, từ khóa. Kết quả dạng thẻ chỉ đọc: "Khi … / Thì … / Vì sao …".

========== MÀN HÌNH 4 — LỊCH SỬ XUẤT FILE ==========
Danh sách các lần xuất: ngày giờ, số giao dịch, người duyệt, tên file, nút mở.

========== CÁC TRẠNG THÁI CẦN VẼ ==========
Chưa có file · đang xử lý · danh sách đầy đủ · một giao dịch đang mở · ngăn Sửa đang mở · hộp xác nhận đồng ý hàng loạt · hộp xuất file · lỗi chặn (ví dụ "Chưa có danh mục đối tượng" kèm nút "Sang Nguồn dữ liệu").

========== DỮ LIỆU GIẢ (10 giao dịch tháng 08/2026, tên đối tác giả) ==========
1. Chi 55.000 — "Thu phi SMS BDSD T7/2026" — Xanh — Nợ 6427 50.000; Nợ 1331 5.000 / Có 1121 55.000 — đối tượng NH.MAU (ngân hàng).
2. Thu 85.000.000 — "CTY TNHH ALPHA chuyen tien phi quan ly T8" — Xanh — Nợ 1121 / Có 131 — đối tượng KH.ALPHA.
3. Chi 120.000.000 — "TT dot 2 HD 15/2026 thi cong duong noi bo" — Vàng — phương án 1: Nợ 331 (NCC.GAMMA) / Có 1121; phương án 2: Nợ 2412 / Có 1121.
4. Thu 300.000.000 — "CTY BETA chuyen tien" — Vàng — chưa rõ thanh toán hay đặt cọc: phương án 1 Có 131; phương án 2 Có 344 — đối tượng KH.BETA.
5. Chi 15.400.000 — "Thanh toan tien dien thang 7" — Vàng (thiếu đối tượng) — Nợ 331 / Có 1121, ô đối tượng trống.
6. Chi 2.000.000 — "Chuyen tien" — Đỏ — thiếu tài khoản đối ứng và đối tượng.
7. Thu 1.250.000 — "Tra lai tai khoan DDA" — Xanh — Nợ 1121 / Có 515.
8. Chi 50.000.000 — "Rut tien mat ve quy" — Xanh — Nợ 1111 / Có 1121.
9. Chi 7.800.000 — "TT phi kiem toan" — Đã có trong Junsky — số chứng từ 02BP2608-0012.
10. Chi 4.500.000 — "Mua xang may cat co T8" — Đã đồng ý — Nợ 154 / Có 1121 — khoản mục "Xăng dầu cho máy cắt cỏ".

========== ĐẦU RA MONG MUỐN ==========
- Prototype bấm được trên dữ liệu giả: mở/đóng giao dịch, Đồng ý / Hoàn tác / Sửa / Bỏ qua, lọc, đồng ý hàng loạt, hộp xuất file, chuyển menu.
- Danh sách thành phần giao diện và các trạng thái của từng thành phần.
- Ưu tiên mật độ thông tin vừa phải: CFO duyệt 100 giao dịch liên tục không mỏi mắt.
```

## Sau khi thiết kế xong

- Anh xuất bản HTML (hoặc gửi link/ảnh chụp các màn hình) cho Claude trong phiên Cowork.
- Claude dựng lại giao diện vào phần mềm hiện có, nối với phần lõi đề xuất bút toán.
