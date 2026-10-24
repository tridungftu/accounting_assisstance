# Phiếu kiểm cổng A — CRM · Báo giá gói 1 (BG-01…BG-05)

## 1. Thông tin lát

| | |
|---|---|
| Màn | CRM · Hợp đồng & lịch thu → mục 6 "Báo giá" (màn Báo giá mới / sửa báo giá) |
| Cổng | **A — thử khung, góp ý ngay** (chưa phải nghiệm thu) |
| Căn cứ | TL 45 §2 BG-01…BG-05, §3 ô Giá trị thông minh (Anh chốt 23–24/10) |
| Nhánh · commit | `lat/bg-1b` · `86d5b5b` (đã gồm máy chủ BG-1a vòng 2) |
| Cách mở | Mở trình duyệt, vào **http://127.0.0.1:8784** → menu trái **Hợp đồng & lịch thu** → cuộn tới mục **6 · Báo giá** → ở dòng **BG-2026-00001** bấm **Mở**. (Bản DEMO này chạy trên CSDL DEMO riêng `p8784`, không đụng DEMO hay kho thật của Anh.) |
| Tài khoản thử | Vai mặc định của bản DEMO: Bán hàng (giả lập) |
| Lead đã tự thử | 24/10: mở được, lịch 4 cột, dòng tổng xanh/đỏ, ca Σ% = 90 chặn In/Chuyển — đúng |

**Điểm đã biết, chưa làm trong gói 1 (không cần ghi nhận xét):**
- Nhãn nút vẫn là "In báo giá (PDF)" / "Chuyển sang Soạn"; thanh nút cố định 4 nút → gói 3 (BG-13).
- Form bên trái chưa gom 4 khối, chưa ẩn trường theo loại hình, khách/lô còn gõ tay, thuế chưa mặc định → gói 2 (BG-06…BG-12).
- Nút "Chuyển sang Soạn" luôn mờ trên DEMO vì DEMO **chưa có mẫu hợp đồng hiệu lực** (lý do hiện khi rê chuột).
- "Người lập" còn hiện tên đăng nhập của vai giả lập.

## 2. Các bước thử

| # | Làm gì | Mong đợi |
|---|---|---|
| 1 | Mở báo giá BG-2026-00001 như trên | Lịch thanh toán 4 cột (Lần · Giá trị · Mốc thời gian · Ghi chú), mỗi đợt **3 ô nhập**; không có nút "Tính thử", không có chữ "chưa tính lại" |
| 2 | Nhìn dòng tổng dưới lịch | **Σ 100% xanh**, Σ tiền 1.500.000,00 USD = Tổng giá trị, ≈ 38.250 tr VND, tỷ giá 25.500 |
| 3 | Sửa đợt 1 từ `30%` thành `20%` rồi bấm Tab | Ngay sau khi rời ô: phần mờ cạnh ô thành "= 300.000,00 USD"; dòng tổng **đỏ** "Tổng % = 90, thiếu 10"; nút In và Chuyển mờ, rê chuột thấy lý do |
| 4 | Gõ `450.000` (không có %) vào đợt 1 rồi Tab | Máy hiểu là **tiền**, phần mờ hiện "= 30%" |
| 5 | Gõ `500.000` vào cả 3 đợt | Σ tiền = Tổng giá trị; mỗi đợt hiện "≈ 33,33%"; **không** bị chặn In |
| 6 | Đổi tỷ giá rồi rời ô | Cột VND quy đổi và tổng VND đổi theo |
| 7 | Gõ `1.400.000` vào ô Tổng giá trị | Hiện cảnh báo "Khác tính toán: …" và lưu ý "Tổng ghi đè sẽ được kiểm lại khi ký hợp đồng"; xóa ô → máy tự tính lại 1.500.000,00 USD |
| 8 | Ở ô Mốc thời gian, chọn "Sau ký + n ngày" (hoặc gõ ngày dd/mm/yyyy) | Mốc hiện bằng chữ tiếng Việt / ngày dd/mm/yyyy, không mã kỹ thuật |
| 9 | Nhìn toàn màn | Tên pháp nhân/dự án/loại hình là tên tiếng Việt; ngày dd/mm/yyyy; số có dấu chấm hàng nghìn |

Không cần bấm Lưu. Nếu bấm "Lưu nháp", dữ liệu chỉ nằm trong CSDL DEMO riêng.

## 3. Nhận xét của Anh (gõ thẳng trong chat cũng được)

Mẫu: `NX1 · bước 3 · mong đợi … · thấy … · P/N/S` — **P** phải sửa trước khi đi tiếp · **N** nên sửa trong gói · **S** để sau.

Kết luận cổng A: **Đi tiếp** (sang gói 2) / **Sửa rồi xem lại** / **Sai hướng — bàn lại thiết kế**.

## 4. Số đo (CHANGELOG)

- Ô nhập mỗi dòng lịch: 9 → **3** (đích ≤ 4).
- Nút tính: 1 → **0**.
