# UI-3e — Trang chủ hệ thống: thanh cố định 4 mục theo vai; giữ tiền tố "M2 · / M4 ·" (CD-010 mục 3)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.** Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM — ghi tệp bằng UTF-8. Sandbox không ghi `.git`: **không commit**. Không mở server. Không xóa file. Worktree hiện tại, nhánh `lat/ui-3e` (dòng giao diện `lat/ui-ky`). Đọc hộp thư `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` **CD-010 mục 3**.

**Việc:**
1. `src/kho_tri_thuc/giao_dien/khung_khai_bao.py` (UI-3a/3c/3d): `thanh_co_dinh` **khác nhau theo vai**. Lead đề xuất (đưa vào phiếu cổng A để Anh duyệt; khai báo bảng đề xuất **một chỗ**, dễ sửa khi Anh chốt):
   - Bán hàng: CRM · Báo giá (phần CRM) · Dự án đang bán (phần CRM) · Nhập dữ liệu.
   - Kế toán / Kế toán trưởng: Nhập dữ liệu · CRM · M2 · Hóa đơn mua · M4 · Nghiệm thu & chi phí dự án.
   - CFO: CRM · M4 · Nghiệm thu & chi phí dự án · Hồ sơ đã nhận · M2 · Hóa đơn mua.
   - Người xem: CRM · Hướng dẫn sử dụng.
   Chỉ mục vai **được dùng**; thiếu thì lấp bằng module đầu tiên được dùng cho đủ 4 (nếu có).
2. Tên module **giữ tiền tố** "M2 ·", "M4 ·": UI-3b đã bỏ ở giao diện — tìm chỗ cắt tiền tố trong `src/kho_tri_thuc/giao_dien/assets/app.js` (khối trang chủ hệ thống) và bỏ việc cắt. M9 vẫn "Tạm dừng" với mọi vai.

**Test:** `tests/test_khung_he_thong.py` (thanh theo từng vai), `tests/khung_luoi_async.cjs` (tên module có tiền tố).
**Chạy:** `python -X utf8 -m unittest tests.test_khung_he_thong tests.test_khung_luoi_crm` (PYTHONPATH=`src;.;tests`), `node tests/khung_luoi_async.cjs`.
**File (≤ 4, gồm test):** `khung_khai_bao.py`, `app.js`, 2 tệp test. **Báo cáo (≤ ¼ trang)**, thông điệp commit `[UI-3e] …`.
