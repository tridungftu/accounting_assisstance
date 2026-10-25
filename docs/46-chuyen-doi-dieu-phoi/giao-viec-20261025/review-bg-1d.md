# REVIEW BG-1b + BG-1d (màn Báo giá) · vòng 1/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8. Có thể chạy `node tests/crm_giao_ket_async.cjs` (chỉ đọc, không ghi tệp).

**Đối tượng:** worktree hiện tại, nhánh `lat/bg-1d`; diff `git diff hop-nhat-20261023...lat/bg-1d` — `src/kho_tri_thuc/giao_dien/assets/crm_g.js`, `assets/style.css`, `tests/crm_giao_ket_async.cjs`, `CHANGELOG.md`. Máy chủ (BG-1c) đã review xong, nằm trên hop-nhat; màn hình phải **hiện đúng số máy chủ trả**, không tự tính tiền khác máy chủ.
**Nhận xét cổng A của Anh (docs/46-chuyen-doi-dieu-phoi/PHIEU-CONG-A-BAO-GIA-GOI-1.md §5; QD-20261025-01…04):** đơn giá × tỷ giá × diện tích tự ra Tổng giá trị + bằng chữ; USD cho nhập tỷ giá, mặc định 26.000 sửa được; VND tỷ giá = 1; phần tính lịch thanh toán + giá trị **to và trước**; thông tin khách + phí quản lý/bảo trì **sau khi khách đồng ý**; VND là chính, USD tham chiếu; In sơ bộ được (không cần khách/phí).

**Kiểm 5 việc, Đạt/Không:**
1. **Tiền trên màn hình:** số hiện = số máy chủ trả (Tổng VND, bằng chữ, tiền từng đợt, Σ); không dùng float để ra số tiền hiển thị/gửi đi; nhập kiểu Việt (dấu chấm nghìn, phẩy thập phân) chuyển đúng thành chuỗi gửi máy chủ; ô tỷ giá VND khóa = 1.
2. **Luồng 2 bước:** bước 1 (giá, tỷ giá, Tổng VND + bằng chữ, USD tham chiếu, lịch VND, In sơ bộ) đứng trước, cỡ lớn; bước 2 (khách, phí, Chuyển) chỉ sau "khách đồng ý"; Chuyển bị chặn/hiện lý do khi thiếu khách/phí, khớp máy chủ chặn; báo giá cũ (USD chính) vẫn mở/hiện đúng.
3. **An toàn giao diện:** mọi chuỗi từ máy chủ/người dùng chèn DOM qua escape/textContent (không innerHTML thô); không lộ mã kỹ thuật/ID trên màn hình; không gọi URL ngoài.
4. **Tiếng Việt nghiệp vụ:** ngày dd/mm/yyyy, tiền có đơn vị, không mã kỹ thuật.
5. **Test:** `tests/crm_giao_ket_async.cjs` có ca cho 1–2 ở trên và chạy đạt; ca nào thiếu thì nêu.

**Báo cáo cuối (≤ 1 trang, tiếng Việt, ≤ 10 điểm):**
```
REVIEW BG-1b+1d · vòng 1/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi số tiền hiện khác máy chủ, Chuyển không bị chặn đúng, chèn DOM không escape, lộ dữ liệu, hoặc vi phạm ràng buộc cứng.
