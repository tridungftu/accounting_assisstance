# Phiếu kiểm cổng A (xem lại) — CRM · Báo giá sau khi sửa theo nhận xét 25/10

## 1. Thông tin lát

| | |
|---|---|
| Màn | CRM · Hợp đồng & lịch thu → mục 6 "Báo giá" |
| Cổng | **A — xem lại** sau kết luận "Sửa rồi xem lại" (phiếu gói 1, mục 5: NX1–NX4) |
| Căn cứ | NX1–NX4 của Anh; QD-20261025-01…04 (VND là chính, USD tham chiếu; In sơ bộ không cần khách/phí; tỷ giá mặc định trong cấu hình chung, kế toán sửa được) |
| Nhánh · commit | `lat/bg-1d` · `f904fcc` (màn hình BG-1b + BG-1d; review Codex vòng 2/2: **Đạt**) — máy chủ BG-1c đã gộp nhánh tích hợp (`ec73112`) |
| Test | Màn hình 23/23 nhóm ca; CRM 321 đạt, 0 mã lỗi mới so với nền |
| Cách mở | Mở trình duyệt, vào **http://127.0.0.1:8791** → menu trái **Hợp đồng & lịch thu** → cuộn tới mục **6 · Báo giá** → bấm **↻ Làm mới** nếu danh sách chưa hiện → ở dòng **BG-2026-00001** bấm **Mở**. (Bản DEMO chạy trên CSDL DEMO riêng `p8791`, không đụng DEMO hay kho thật của Anh.) |
| Lead đã tự thử | 25/10, màn 1440×900: bước 1 ở trên cùng; 100 USD × 26.000 × 15.000 m² = **39.000.000.000 VND**, "Ba mươi chín tỷ đồng"; tỷ giá 25.999,5 → 38.999.250.000 VND, bằng chữ đổi theo, nhãn "đã sửa", xóa trống → về 26.000; VND → tỷ giá 1 khóa; lịch 30% / 70% = 11.700.000.000 / 27.300.000.000 VND, Σ xanh; bước 2 gấp sẵn, Chuyển mờ kèm lý do — đúng |

**Điểm đã biết, chưa làm ở vòng này (không cần ghi nhận xét):**
- Chọn dự án → tự nạp đơn giá, loại hình, thuế, lô/căn, tiến độ, phí: thuộc **Dự án đang bán** (DA-1…DA-3, đang làm).
- Nút "Chuyển sang soạn hợp đồng" luôn mờ trên DEMO vì DEMO **chưa có mẫu hợp đồng hiệu lực** (lý do hiện cạnh nút).
- Cột "Người lập" còn hiện tên đăng nhập của vai giả lập; thanh nút cố định → gói 3 (BG-13).
- Cơ sở thuế / VAT % vẫn nằm ở bước 1 (ảnh hưởng tổng tiền).
- Báo giá đã sửa tỷ giá tay, xóa trống rồi Lưu: số tiền đúng theo tỷ giá mặc định, nhưng mở lại nhãn ghi "đã sửa" thay vì "mặc định" (cần sửa nhỏ ở máy chủ, để gói sau).
- Danh sách có thêm dòng **BG-2026-00003 · Đã hủy** — báo giá thử của lần sửa, bỏ qua.

## 2. Các bước thử

| # | Làm gì | Mong đợi | Nhận xét gốc |
|---|---|---|---|
| 1 | Mở BG-2026-00001 như trên | Khối **"Bước 1 · Giá và lịch thanh toán"** ở trên cùng; số lớn **39.000.000.000 VND**; dòng phép tính "100 USD × 26.000 × 15.000 m² = 39.000.000.000 đ"; **"Bằng chữ: Ba mươi chín tỷ đồng"**; "Tham chiếu: 1.500.000,00 USD" | NX1, NX3 |
| 2 | Nhìn ô **Tỷ giá USD → VND** | Sẵn **26.000**, dưới ô ghi "mặc định · 25/10/2026" | NX2 |
| 3 | Sửa tỷ giá thành `25.500` rồi bấm Tab | Tổng thành **38.250.000.000 VND**, bằng chữ đổi theo, nhãn "đã sửa"; xóa trống ô rồi Tab → về 26.000 | NX2 |
| 4 | Đổi **Tiền tệ** sang VND | Ô tỷ giá thành **1**, xám, không sửa được ("cố định = 1"); tổng = đơn giá × diện tích | NX2 |
| 5 | Đổi lại USD, nhìn **Lịch thanh toán (VND)** ngay dưới số lớn | Mỗi đợt hiện tiền VND; dòng Σ xanh "Σ 100% ✓ · Σ tiền … VND = Tổng giá trị ✓" | NX3 |
| 6 | Nhìn nút **"In báo giá sơ bộ (PDF)"** dưới lịch | Bấm được dù chưa có khách hàng/phí | QD-02 |
| 7 | Bấm dòng **"Bước 2 · Sau khi khách đồng ý"** | Mở ra: khách hàng, liên hệ, phí quản lý/bảo trì, tiền tệ phí, cơ sở phí, hạn, mô tả lô/căn, ghi chú; nút **"Chuyển sang soạn hợp đồng"** mờ, lý do hiện ngay cạnh ("Chưa có thông tin khách hàng.") | NX4 |
| 8 | Nhìn dòng **"Tỷ giá USD mặc định: 26.000 · cập nhật 25/10/2026"** ở đầu mục 6 (vai mặc định của DEMO là Kế toán) | Có nút **Sửa**; bấm thì nhập tỷ giá + **lý do bắt buộc**; báo giá đã lưu giữ tỷ giá cũ. Vai không phải kế toán: chỉ thấy dòng, không có nút | QD-04 |

Không cần bấm Lưu. Nếu bấm "Lưu nháp", dữ liệu chỉ nằm trong CSDL DEMO riêng.

## 3. Nhận xét của Anh (gõ thẳng trong chat cũng được)

Mẫu: `NX · bước … · mong đợi … · thấy … · P/N/S` — **P** phải sửa trước khi đi tiếp · **N** nên sửa trong gói · **S** để sau.

Kết luận cổng A: **Đi tiếp** (sang gói 2) / **Sửa rồi xem lại** / **Sai hướng — bàn lại thiết kế**.

## 4. Số đo (CHANGELOG)

- Ô bắt buộc phải chạm để In báo giá USD KCN: **7 → 5** (bỏ tỷ giá nhập tay, bỏ khách).
- Vị trí Tổng giá trị trên màn đầu 1440×900: y=583 trong cột cuộn riêng → **y=244**, cỡ chữ lớn; tỷ giá từ ngoài khung → y=142.
