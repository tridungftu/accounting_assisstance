# Phiếu cổng A lần 2 — Báo giá (BG-18…BG-24) + Dự án đang bán + Mốc thanh toán theo dự án + Trang chủ hệ thống · 26/10/2026

**Căn cứ:** hộp thư CD-005 (BG-18…24), CD-006 (gộp BG-1d + DA-2; mốc do dự án tự khai), CD-007 (ngày dự kiến/thực tế); TL 45 §7–§8; TL 49 §1. **Bản thử:** DEMO cổng **8798** — mở `http://127.0.0.1:8798/` (CSDL DEMO riêng, không đụng CSDL DEMO của Anh). Lead đã tự đi các bước trên trình duyệt lúc 00:50–00:58; đã có sẵn 1 báo giá nháp thử `BG-2026-00001`.

**Đổi vai:** khối **"Vai mô phỏng"** (cuối trang CRM) → ô "Đổi vai" → bấm **Dùng vai này**. Nhãn vai nay là tiếng Việt kèm pháp nhân:
| Vai trong phiếu | Chọn trong danh sách |
|---|---|
| Bán hàng | **Bán hàng · Pháp nhân DEMO A — KCN (mô phỏng)** |
| Kế toán | Kế toán · Pháp nhân DEMO A — KCN (mô phỏng) · 1 |

## A. Báo giá (vai Bán hàng)
1. **BG-18:** CRM → icon **Báo giá** → nút **"+ Báo giá mới"** ở đầu màn (cạnh tiêu đề), không phải cuộn.
2. **BG-19:** chọn Dự án **"KCN DEMO — khu A"**, Tiền tệ **VND**, Đơn giá **2.650.000**, Diện tích **10.000** → khối Tổng giá trị **26.500.000.000 VND**, dòng phép tính, **Bằng chữ: Hai mươi sáu tỷ năm trăm triệu đồng**; giá trị từng lần và Σ chữ to, đậm như khối Tổng.
3. **BG-21:** ô **Nhập nhanh lịch** gõ `10%, 30%, 40%, 10%` → Enter → 4 dòng đúng %; **Σ 90%** hiện đỏ, nút **In** mờ kèm lý do "Tổng % = 90, thiếu 10". Sửa dòng cuối thành 20% → Σ 100%. Gõ `4` khi bảng đã có dòng → hỏi "Thay lịch hiện tại?" ngay trong trang (Hủy giữ nguyên).
4. **BG-20:** bảng lịch 5 cột **Lần · % · Giá trị · Mốc thời gian · Ghi chú**; gõ % → Giá trị tự tính; gõ tiền → % tự tính (máy chủ tính khi rời ô); đổi Tổng giá trị → ô người gõ giữ nguyên, ô kia tính lại.
5. **BG-23 + mốc dự án (CD-006 mục 3):** ô Mốc gõ `cndt` → thành **"Xong chứng nhận đầu tư"** (mốc riêng của dự án KCN DEMO); gõ `CNĐT + 30` → **"Xong chứng nhận đầu tư + 30 ngày"**; gõ chữ lạ (vd `xyz`) → câu lỗi "Dòng N: chưa có mốc "xyz" trong danh sách — chọn mốc bên dưới hoặc gõ ngày dd/mm/yyyy." kèm **danh sách mốc bấm chọn** (mốc cơ bản + mốc của dự án, có "dự kiến dd/mm/yyyy").
6. **BG-24:** mọi số tiền ghi **VND** (không còn "đ"/"VNĐ").
7. **BG-22:** nhãn vai không mã kỹ thuật, ngày dd/mm/yyyy; cột **Người lập** của danh sách ghi "Người dùng mô phỏng" (không còn `MO_PHONG_…`).
8. **Lưu nháp** → báo giá vào danh sách; mở lại thấy đúng lịch và mốc đã chọn.

## B. Dự án đang bán + Mốc thanh toán (CD-006 mục 1–2, CD-007)
9. Trang chủ CRM có **7 ô**, thêm ô **"Dự án đang bán"**; icon có **số 1** (một mốc quá ngày dự kiến). Bấm → mở thẳng màn Dự án đang bán (không qua Mẫu hợp đồng).
10. Bấm **KCN DEMO — khu A** → mục **"Mốc thanh toán của dự án"**: 2 mốc DEMO — "Xong chứng nhận đầu tư" (tên tắt CNĐT, dự kiến 24/11/2026) và "Bàn giao hạ tầng giai đoạn 1 — DEMO" (dự kiến 20/10/2026, **quá ngày dự kiến — cần chỉnh ngày**, dòng tô cảnh báo; đầu mục "1 mốc cần chỉnh ngày dự kiến").
11. **Chỉnh ngày dự kiến** mốc quá hạn: nút Lưu mờ tới khi nhập **lý do**; lưu → mốc thành "Chưa đến ngày dự kiến", số việc chờ về 0. **Lịch sử** ghi cũ → mới, ai, lúc nào, lý do.
12. **Ghi ngày thực tế** (≤ hôm nay) cho một mốc; **+ Khai mốc** mới (tên, tên tắt, ngày dự kiến bắt buộc).
13. Danh sách hợp đồng: đợt gắn mốc chưa có ngày thực tế hiện "Đợt N · *dự kiến* dd/mm/yyyy", không bị tính quá hạn (DEMO chưa có hợp đồng gắn mốc riêng — xem bằng test, chưa thấy trên màn).

## C. Trang chủ hệ thống (UI-3, ưu tiên 5 — chỉ xem)
14. Mở `http://127.0.0.1:8798/` → **Trang chủ hệ thống**: thanh cố định 4 mục trên đầu, ô **Tìm nhanh** (gõ không dấu, Enter mở mục đầu), lưới module; **"Vốn vay & đầu tư tài chính" hiện mờ, nhãn "Tạm dừng"**, không bấm được.

## Đã biết / Cần Anh chọn
- **Danh sách vai mô phỏng rất dài (~44 dòng)** vì gồm vai DEMO của M2/M4/M5; nhãn đã có tên pháp nhân. Anh muốn rút gọn (chỉ vai CRM) không?
- **Thanh cố định 4 mục** tạm = 4 module đầu theo thứ tự (Nhập dữ liệu · CRM · Nghiệm thu & chi phí dự án · Hồ sơ đã nhận); tên module bỏ tiền tố "M2 · / M4 · / M9 ·". Anh chọn 4 mục nào?
- **M9 "Tạm dừng" hiện với mọi vai** (lead chọn; TL 49 §1.2 ẩn theo quyền vs §1.6 hiện mờ).
- **Việc chờ "Chỉnh ngày dự kiến mốc"** hiện cho vai **Bán hàng** (CRM chưa có trường "người phụ trách" từng dự án). Mốc vẫn hiện và vẫn sinh việc chờ khi dự án **ngừng bán**; số trên icon hiện chỉ đếm dự án đang bán.
- **Gõ tắt mốc:** khớp tên tắt đã khai và chữ cái đầu của ≥ 2 từ liền nhau trong tên.
- **Bằng chữ giữ "đồng"** (khớp bản DOCX/PDF); số tiền ghi "VND". Cột "VND quy đổi" của báo giá USD đang trùng số với cột Giá trị (lịch đã tính bằng VND) — giữ hay bỏ?
- Nhập nhanh khi bảng **chỉ có một dòng trống** thì thay thẳng, không hỏi.
- **Không gộp** dòng giao diện này vào nhánh hợp nhất khi Anh chưa qua cổng A (CD-008).

**Kết luận của Anh:** Đạt / Cần sửa (ghi rõ bước) — ghi vào hộp thư chỉ đạo hoặc trả lời trong phiên lead.
