# DA-2c — CRM · màn "Dự án đang bán": 5 điểm sau review Claude (DA-2b)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2, §4: không mã kỹ thuật trên màn hình). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/da-2` (đầu `0bf55ae`). Sandbox không ghi `.git`: **không commit**. Chạy: `node tests/crm_du_an_ban_async.cjs`, `node tests/crm_giao_ket_async.cjs`.

**Việc (số dòng `src/kho_tri_thuc/giao_dien/assets/crm_g.js`):**
1. `:545`, `:685` (+ assert `tests/crm_du_an_ban_async.cjs:197`): màn hình đang hiện mã "QD-20261025-07" ("Áp dụng ngay — QD-…", cột "Căn cứ" lấy `CAN_CU_G7`) → đổi thành chữ nghiệp vụ: "Áp dụng ngay, không cần CFO duyệt"; cột Căn cứ: "Bán hàng/kế toán áp dụng ngay" hoặc "CFO duyệt (bản cũ)". Không hiện mã quyết định ở bất kỳ đâu.
2. `:886` (`veLap`): tab G7 vẫn còn form "Lập bộ chuẩn (nháp) — kế toán" → **ẩn form lập nháp** (QD-20261025-17), giữ bảng "Phiên bản bộ chuẩn" để xem bản cũ; chú thích chỉ sang "Dự án đang bán → Sửa tiến độ tiêu chuẩn".
3. `:531` + `moForm` (~388): loại hình của dự án đã có phiên bản mới (id cũ không có trong danh sách chọn) → đặt giá trị rỗng, buộc chọn lại, lỗi "Cần chọn loại hình" chặn Lưu; không gửi id cũ.
4. `:488`, `:398`: lỗi 400 tiến độ trả khóa `dong.N.gia_tri_thap_phan` (và các `dong.N.*` khác) → ánh xạ đúng ô để tô đỏ; form tiến độ hiện tên giai đoạn đang sửa; dự án chưa có giai đoạn mặc định → báo trước khi mở form.
5. `:489-491`: mọi 409 (kể cả `CRM_DA_TRANG_THAI`, `CRM_DA_DA_CO`…) dùng chung nhánh "giữ nháp + nút Tải lại bản mới".
6. Test: cập nhật/thêm nhóm cho 1–5 trong `tests/crm_du_an_ban_async.cjs` (không hiện "QD-"; G7 không còn form lập nháp; loại hình cũ → rỗng + chặn; lỗi `dong.0.gia_tri_thap_phan` tô đúng ô; 409 khác loại có nút tải lại).

**File được sửa (chỉ):** `src/kho_tri_thuc/giao_dien/assets/crm_g.js`, `tests/crm_du_an_ban_async.cjs`. Không sửa máy chủ, phần Báo giá; không xóa file.
**Test phải đạt:** `node tests/crm_du_an_ban_async.cjs`, `node tests/crm_giao_ket_async.cjs` 23/23.
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · ca test · thông điệp commit `[DA-2c] …`.
