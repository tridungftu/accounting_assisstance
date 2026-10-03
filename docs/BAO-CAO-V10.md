# Báo cáo V10 — Giao diện Định khoản (bản Claude Design) nối với lõi

Ngày: 03/10/2026. Người thực hiện: Claude (phiên Cowork), theo bản bàn giao `BAN-GIAO-dinh-khoan.md` + `dinh-khoan-prototype.html`.
Quy tắc giữ nguyên: **không tự nhập Junsky; chỉ giao dịch “Đã đồng ý” mới được xuất.**

## 1. Kết luận

- Màn hình mới đã thay `that.html / that.css / that.js`. Có đủ bốn màn hình: Định khoản, Nguồn dữ liệu, Tra cứu tri thức, Lịch sử xuất file.
- Nút Đồng ý / Sửa / Bỏ qua chạy trên từng giao dịch. Ngoài ra có Hoàn tác, Mở lại, Đồng ý hàng loạt dòng Xanh và phím tắt A/E/S/↑/↓/Enter.
- Xuất mức 1: chỉ có **File soát (Excel)**, liệt kê từng dòng bút toán đã đồng ý.
  - Không ra file nhập Junsky: nút trên màn hình khóa, máy chủ cũng chặn (`junsky_export_enabled = false`).
- Kiểm thử: **224/224 test PASS**, cả Python 3.13 và 3.11. Trong đó có 198 test cũ và 26 test V10 mới, đều dùng dữ liệu giả.
- Thời gian đề xuất 105 dòng sao kê:
  - trước: khoảng 47–49 giây (V9b);
  - sau: khoảng 7–9 giây trên máy đám mây.
  - Lý do nhanh hơn: bỏ sao chép sâu toàn bộ danh mục ở mỗi dòng, tra định danh một lượt, nhớ tạm phần chuẩn hóa chữ. Kết quả đề xuất không đổi; có test đối chứng.

## 2. Thay đổi phần lõi

| Hạng mục | Nội dung |
|---|---|
| Dòng bút toán đầy đủ | `rows()` trả `entry_lines` (Nợ/Có, TK, số tiền, đối tượng, dự án, khoản mục, TTCP), `basis` (chứng từ cũ làm căn cứ), `options` (phương án khi chứng từ cũ không thống nhất), `suggest_accounts`, `proposal_level` (không đổi sau khi duyệt) |
| Vế TK tiền | Hiện cả khi không có quy tắc nào khớp, để Anh chỉ cần chọn TK đối ứng. Ánh xạ “Anh khai” luôn thắng ánh xạ máy suy ra |
| Sửa nhiều dòng | Có thể sửa toàn bộ bút toán (bảng `quick_items.decision_lines_json`, migration v19). Máy chủ kiểm tra từng điểm, xem bảng ngay dưới |
| Duyệt đúng cái đã thấy | Màn hình gửi kèm đúng các dòng đang hiển thị khi Đồng ý, kể cả Đồng ý hàng loạt |
| Ghi nhớ | Ghi nhớ cả cấu trúc nhiều dòng (ví dụ 6427 + 1331), không chỉ TK chính. Áp dụng ngay cho các giao dịch đang chờ có cùng STK hoặc tên đối ứng. Bỏ tích “Ghi nhớ” thì không học |
| Hoàn tác / Mở lại | `REOPEN` đưa dòng về Chờ duyệt, ngừng quy tắc và thu hồi định danh STK đã học từ lần duyệt đó. Dòng đã xuất file thì không mở lại được |
| Đã có trong Junsky | Bỏ đánh dấu chỉ đưa dòng về Chờ duyệt, không tự thành Đồng ý. Đề xuất lại không đánh dấu lại dòng Anh đã xác nhận “không trùng” |
| Mốc học | Thiết lập `learning_cutoff`. Máy chỉ học chứng từ BR/BP đến ngày này. Quy tắc trong `BO-QUY-TAC` có `lan_dau` sau mốc bị loại |
| Đề xuất lại | `repropose()` chỉ tính lại dòng Chờ duyệt. Dòng đã quyết định giữ nguyên |
| Xuất | `export(junsky_files=False)` ghi File soát. Mỗi lần xuất ghi vào bảng `quick_exports` (Lịch sử) và đánh dấu Đã xuất, nên lần sau không xuất lặp. Bộ đếm số chứng từ, đánh dấu và lịch sử nằm trong cùng một giao dịch dữ liệu |
| Mở lại tệp cũ | Thả lại đúng tệp đã làm thì mở lại kết quả cũ (nhận theo mã băm), không tạo lần làm rỗng |

Máy chủ chặn Đồng ý khi gặp một trong các lỗi sau:

- Nợ ≠ Có.
- Dòng TK tiền không đúng số tiền sao kê.
- Vế tiền không phải TK 112 chi tiết, hoặc khác TK đã khai.
- TK công nợ thiếu đối tượng.
- Mã không có trong danh mục.

Nếu một lần xuất lỗi giữa chừng, toàn bộ lần đó được hủy; lần xuất lại dùng đúng số chứng từ cũ, không phát sinh số trùng.

## 3. API mới (chỉ trên máy, có mã phiên)

| Phương thức | Đường dẫn |
|---|---|
| GET | `/api/that/overview` |
| GET | `/api/that/runs` |
| GET | `/api/that/history` |
| GET | `/api/that/knowledge-cards?q=` |
| POST | `/api/that/reload` |
| POST | `/api/that/learning-settings` |
| POST | `/api/that/cash-mapping` |
| POST | `/api/that/quick/repropose` |
| POST | `/api/that/open` (mở thư mục hoặc file xuất bằng Explorer) |

- Upload trả tiến độ thật dạng “Đang đề xuất x/y”.
- CSP: thêm `'unsafe-inline'` cho style, vì bản thiết kế dùng thuộc tính style. Script vẫn chỉ cho `'self'`.

## 4. Chạy thử tháng 08/2026 (máy học đến 30/06/2026)

- **Cách chạy**:
  - Sổ NKC được cắt chỉ còn chứng từ đến 30/06/2026.
  - Ánh xạ TK ngân hàng (•••• 0496) → 112111.
  - Mốc học đặt 30/06/2026.
  - Thả “Sao kê NH T08.xlsx” (105 giao dịch).
- **Cách chấm** (`run/score.py`): ghép từng dòng với chứng từ thật tháng 8 trong Sổ NKC đến 29/08/2026. Chỉ ghép khi khớp duy nhất theo ngày và số tiền trên TK 112; sau đó so TK đối ứng và đối tượng.

| Mức | Số dòng | Ghép được | TK đối ứng đúng | Có đối tượng / đúng |
|---|---|---|---|---|
| Xanh | 27 | 20 | 19/20 | 12 / 12 |
| Vàng | 44 | 33 | 22/33 | 22 / 15 |
| Đỏ | 34 | 10 | — (chưa có TK đối ứng, cần Anh chọn) | 9 / 9 |

- **Lỗi duy nhất ở mức Xanh**: “rút séc” được đề xuất Nợ 1111, còn sổ tháng 8 ghi 13881. Đây là trường hợp phải phán đoán; Anh xử lý khi duyệt từng dòng.
- **Đối tượng học từ ngày nào**:
  - Đổi “Chỉ học đối tượng từ ngày” từ 01/07/2026 sang 01/01/2026 **không làm thay đổi kết quả** của lần chạy thử này.
  - Lý do: máy chỉ nhận đối tượng từ sổ khi mọi chứng từ mẫu đều thống nhất.
- **Giới hạn đã biết (QĐ-V1b-1)**:
  - Số lần gặp/đúng trong `BO-QUY-TAC` vẫn tính cả tháng 7–8. Vì vậy kết quả chạy thử hơi lạc quan.
  - Bản chạy trước (chưa lọc `lan_dau`) cho Xanh 29 / Vàng 39 / Đỏ 37. Bản đó **có lẫn tri thức tháng 7–8**, không dùng làm căn cứ.
  - Danh sách công nợ (dgbList) là ảnh chụp hiện tại.

## 5. Cấu hình chạy thử và chạy thật

- **Bản thử T8**:
  - Mở bằng `MỞ PHẦN MỀM THỬ T8.cmd` (cổng 8767).
  - Cấu hình `cau_hinh.thu-T8.toml`, kho `var/plhn-thu-T8`, thư mục giao diện `var/web-thu-T8`.
  - Nguồn: `Mang ngan hang/Thu nghiem T8 (hoc den 30-06)`.
- **Bản thật**:
  - Mở bằng `MỞ PHẦN MỀM.cmd` (cổng 8766). Kho thật `var/plhn-that` được nâng schema lên v19 khi mở lần đầu; đã sao lưu trước.
  - `var/web-that/source-settings.json` được bổ sung ánh xạ TK ngân hàng → 112111. Mốc học để trống, tức máy học toàn bộ sổ đến ngày của từng giao dịch.

## 6. Còn chờ Anh xác nhận

1. Danh sách TK công nợ bắt buộc có đối tượng. Hiện là 131, 331, 141, 344, 1388, 3388, so theo tiền tố; Anh sửa được ở màn hình Nguồn dữ liệu.
2. Mở “File nhập Junsky” (mức 2) chỉ sau khi nhập thử 1 rồi 5 chứng từ thành công.
3. Hóa đơn XML: màn hình mới tạm chỉ nhận sao kê Excel.
