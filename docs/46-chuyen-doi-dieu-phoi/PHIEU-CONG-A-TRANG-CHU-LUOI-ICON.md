# Phiếu cổng A — Trang chủ lưới icon CRM (UI-1 + UI-2) · 25/10/2026

**Căn cứ:** TL 49 `D:\Claude\Phan mem ho tro ke toan\49-trang-chu-luoi-icon.md` §1–§4 (Anh chốt 25/10, CD-002). **Bản thử:** DEMO cổng **8798** (CSDL DEMO riêng, không đụng CSDL DEMO của Anh) — mở `http://127.0.0.1:8798/#crm` trong trình duyệt. Lead đã tự đi hết các bước dưới đây với 4 vai trước khi gửi phiếu.

**Đổi vai:** khối **"Vai mô phỏng"** ở cuối trang CRM → chọn trong ô "Đổi vai" → bấm **Dùng vai này**.
| Vai trong phiếu | Chọn trong danh sách |
|---|---|
| Bán hàng | `MO_PHONG_CRM_G_BH_A` |
| Kế toán | `MO_PHONG_KT_A` |
| CFO | `MO_PHONG_CRM_G_CFO_A` |
| Người xem | `MO_PHONG_XEM_A` |

## Các bước (đánh Đạt / Không đạt + ghi chú)

1. **Thẻ và icon theo vai.** Với từng vai, trang chủ CRM có 2–4 thẻ tổng quan và lưới icon:
   - Bán hàng: thẻ "Báo giá đang nháp", "Hợp đồng có đợt thu đến hạn 7 ngày"; 6 icon.
   - Kế toán: "Hợp đồng ký chờ kiểm", "Hợp đồng có đợt thu quá hạn"; 6 icon.
   - CFO: "Mẫu hợp đồng chờ duyệt", "Hợp đồng hiệu lực"; 6 icon.
   - Người xem: "Hợp đồng hiệu lực"; **chỉ 3 icon** (Hợp đồng, Thu tiền, Báo cáo & file soát).
2. **Bấm thẻ → danh sách.** Bấm một thẻ: mở đúng phần, đầu trang có danh sách theo thẻ "N mục" **bằng số trên thẻ**, có nút "Bỏ lọc".
3. **Số trên icon.** Ở vai Bán hàng, vào **Báo giá** tạo một báo giá nháp (lưu nháp), về trang chủ (icon **Lưới module** trên thanh trái hoặc bấm "CRM · Hợp đồng bán hàng") → thẻ "Báo giá đang nháp" = 1 và icon Báo giá có **số 1** ở góc (nền xám; nền đỏ chỉ khi có việc quá hạn).
4. **Thanh icon trái.** Vào Báo giá: menu chữ bên trái được thay bằng **thanh icon** (Trang chủ, Lưới module, 6 phần); phần đang mở có viền xanh, chữ đậm; đường dẫn trên đầu "Không gian làm việc / CRM · Hợp đồng bán hàng / Báo giá". Bấm **Thu tiền** trên thanh icon → chuyển thẳng, **không về trang chủ**. Thử nút Back của trình duyệt.
5. **Trang chủ / Lưới module.** Bấm **Trang chủ** trên thanh icon → về trang "Nhập dữ liệu" (tạm, cho tới khi có trang chủ hệ thống ở UI-3) và menu chữ hiện lại; bấm **Lưới module** → về trang chủ CRM.
6. **Không còn mã kỹ thuật** trên thẻ, icon, danh sách theo thẻ (không thấy W2, QUA_HAN, hop-dong…); ngày dd/mm/yyyy, tiền có đơn vị.

**Thêm (không bắt buộc):** nếu máy chủ trang chủ lỗi → thông báo tiếng Việt + "Thử lại" + "Mở màn đầy đủ (bản cũ)"; mục menu cũ "Hợp đồng" (`#hopdong`) vẫn mở màn đầy đủ như trước.

## Đã biết, chưa làm trong lát này
- Mọi số đang là **0** vì CSDL thử mới, chưa có hợp đồng — bước 3 để Anh tự tạo số.
- Danh sách theo thẻ là bảng tối thiểu (25 mục đầu), chưa phải màn danh sách hợp đồng S1 đầy đủ (lát C4).
- Ô "Đổi vai" còn hiện tên đăng nhập mô phỏng (`MO_PHONG_…`) — khối này có từ trước, chỉ dùng cho DEMO.
- Cách đếm số trên icon theo TL 42 §3: Bán hàng — Hợp đồng = trả lại/bổ sung + chờ ký; Kế toán — Thu tiền = đợt đến hạn 7 ngày; CFO — Hợp đồng = chờ duyệt. Anh muốn đổi thẻ/số nào thì ghi vào phiếu.

**Kết luận của Anh:** Đạt / Cần sửa (ghi rõ bước) — ghi vào hộp thư chỉ đạo hoặc trả lời trong phiên lead.
