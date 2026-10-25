# M4-5d — Khối 03B: giữ thông báo máy chủ khi lỗi không mã DC; đợt ứng viên lỗi thì bỏ qua (review lô 7 lát, Nên sửa 2–3)

Bạn là worker Codex, chạy không tương tác. Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\review-lo-7-lat.md` (Nên sửa 2, 3). **Làm ngay, không hỏi lại.** UTF-8 không BOM — ghi tệp bằng UTF-8. Worktree hiện tại, nhánh `lat/m4-5d` (từ `lat/m4-5c`). Sandbox không ghi `.git`: **không commit**. Không mở server.
Việc — `src/kho_tri_thuc/m4/giao_dien/m4_ke_toan.js`: (1) `dcLoiMayChu`: chỉ dịch khi có mã `DC_*`; lỗi không mã DC (403 quyền, 404, 400, 5xx) → hiện thông báo máy chủ qua `dcChu(d.message)` (như trước M4-5c); thao tác chỉ đọc không bao giờ hiện "Không lưu được…". (2) `dcNap`: đọc chi tiết từng hồ sơ ứng viên (`GET /api/m4/ke-toan/{id}`) — một ứng viên lỗi (mạng/400/409/5xx) thì **bỏ qua ứng viên đó** (null), khối vẫn mở, lịch sử vẫn nạp; không hiện câu "Chỉ chọn đợt đã xác nhận…" sai nghĩa; nếu được, chỉ đọc ứng viên cùng hợp đồng (giảm số lượt gọi).
**Test — `tests/m4_03b_async.cjs`:** ca 03B-7 (thu hồi quyền) hiện đúng thông báo quyền của máy chủ; một ứng viên lỗi 500 → khối vẫn mở với các ứng viên còn lại; ca cũ đạt.
**File (≤ 2):** `m4_ke_toan.js`, `tests/m4_03b_async.cjs`. Không xóa file.
**Chạy:** `node tests/m4_03b_async.cjs`, `node tests/m4_01c_async.cjs` — ghi số.
**Báo cáo (≤ ¼ trang):** sửa ở file:dòng · số test · thông điệp commit `[M4-5d] …`.
