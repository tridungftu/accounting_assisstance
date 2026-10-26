# KY-G5TAY-UI vòng 2: 4 điểm nên sửa của review và test còn thiếu

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. Sandbox không ghi được `.git`: **không commit**.
- Không mở server. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/ky-g5tay-ui` (d105422).
- Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-e14u-v2-ky-g5tay-ui.md`, phần KY-G5TAY-UI.
- Máy chủ đọc bằng `git show hop-nhat-20261023:<tệp>`: `giao_dien/crm_g.py`, `k2/crm_ky_ket.py`, `k2/sql_crm_g5_tay.py`.

**Việc trong `src/kho_tri_thuc/giao_dien/assets/crm_g.js`:**
1. Dòng khoảng 3114: bỏ câu xưng "Anh". Dùng: "Vai hiện hành không có quyền xác nhận đã kiểm tay cho bản ký này."
2. Phân lỗi theo mã (`e.code`):
   - `CRM_G5_TAY_LY_DO` → câu về độ dài và ký tự của lý do.
   - 409 → câu tải lại.
   - 403 → câu không quyền.
   - Mọi lỗi khác, kể cả 400 khác và 404 → câu chung "Không thực hiện được. Tải lại rồi thử lại."
   - **Không** hiện `e.message` của máy chủ (hiện đang lộ "CSDL từ chối thao tác (CRM_G_KHONG_THAY)").
3. Có biên nhận hợp lệ thì ẩn khối "Xác nhận đã kiểm tay" ngay, rồi mới tải lại.
4. Bỏ đọc trường `xac_nhan_boi_ten`, vì máy chủ không trả trường này. Dùng đúng trường máy chủ trả.

**Test `tests/crm_ky_ket_async.cjs`:**
- Biên nhận đúng hình dạng máy chủ thật (có `id`, `phap_nhan_id`…; giờ dạng PG `2026-10-26T10:15:30.123456+07:00`).
- Ca 400 mã khác, ca 404: câu chung, không lộ mã.
- Lý do chứa `<b>x</b>` hiển thị nguyên văn bằng chữ.
- Sau biên nhận, khối ẩn trước khi tải lại xong.

**Chạy:** `node tests/crm_ky_ket_async.cjs`, `node tests/crm_giao_ket_async.cjs`, `node tests/khung_luoi_async.cjs`.

**Tệp (≤ 2):** `crm_g.js`, `tests/crm_ky_ket_async.cjs`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[KY-G5TAY-UI] vòng 2: …`.
