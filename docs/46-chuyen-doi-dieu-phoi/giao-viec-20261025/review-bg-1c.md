# REVIEW BG-1c · vòng 1/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8. Chạy Python nếu cần: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"` (thiếu psycopg là bình thường — test thuần chạy được).

**Đối tượng:** nhánh `lat/bg-1c` (worktree hiện tại), 3 commit trên hop-nhat; diff `git diff hop-nhat-20261023...lat/bg-1c`. Tệp: `src/kho_tri_thuc/k2/crm_giao_ket.py`, `giao_dien/crm_g.py`, `ha_tang/pg_migrations.py` (append M0030), `k2/sql_crm_bg1c.py` (mới), test.
**Quyết định của Anh (docs/QUYET-DINH.md QD-20261025-01…04, QD-20261024-02):** báo giá USD: **Tổng VND = đơn giá × tỷ giá × diện tích**, làm tròn đến đồng (nửa lên), bằng chữ VND; lịch thanh toán bằng VND; USD chỉ tham chiếu; báo giá VND tỷ giá = 1 khóa; tỷ giá mặc định 26.000 trong cấu hình chung, kế toán sửa được (có nhật ký); In sơ bộ không cần khách/phí; Chuyển cần khách + phí (máy chủ chặn); bước Ký vẫn chặn ghi đè tổng / % không tròn.

**Kiểm 4 việc, Đạt/Không — trọng tâm TIỀN:**
1. **Đúng quy tắc tiền:** tính bằng Decimal (không float); làm tròn đúng một chỗ, nửa lên; tổng các đợt % / tiền so với Tổng VND chính xác theo đơn vị nhỏ nhất; ghi đè tổng không làm tròn; tỷ giá dạng chuỗi được parse chặt (âm, 0, chữ, quá dài → lỗi theo trường). Tự viết vài ca biên (tỷ giá 25.999,5; diện tích lẻ 0,001; đơn giá 0; số rất lớn 10^15) bằng lệnh Python tạm và báo ca sai.
2. **M0030:** chỉ APPEND (prefix 1–29 trùng byte với hop-nhat); chỉ `CREATE OR REPLACE FUNCTION master.crm_kiem_lich_ky(uuid)` cùng chữ ký/kiểu trả; công thức SQL khớp Python (round(đơn giá × tỷ giá × diện tích, 0) cho báo giá v2; dữ liệu cũ giữ hành vi M0025); không bỏ mã lỗi nào của M0025.
3. **Quyền & nhật ký tỷ giá mặc định:** chỉ KE_TOAN/KE_TOAN_TRUONG có module CRM sửa; đóng dòng cũ + thêm dòng mới + `nhat_ky.su_kien` trong cùng giao dịch; báo giá đã lưu giữ tỷ giá đã lưu; không ai khác đổi được qua route khác.
4. **Phạm vi/tương thích:** báo giá cũ (USD chính) đọc đúng nghĩa cũ; `chuyen()` chặn đúng khi thiếu khách/phí; không sửa `crm_g.js`; không dữ liệu thật; không xóa tệp.

**Báo cáo cuối (≤ 1 trang, tiếng Việt, ≤ 10 điểm):**
```
REVIEW BG-1c · vòng 1/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi tính tiền sai, làm tròn sai/nhiều lần, M0030 đổi byte 1–29 hoặc SQL ≠ Python, người không có quyền sửa được tỷ giá mặc định, hoặc vi phạm ràng buộc cứng.
