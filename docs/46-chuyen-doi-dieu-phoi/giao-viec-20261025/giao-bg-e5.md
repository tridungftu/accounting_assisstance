# BG-e5 — Báo giá: sửa sau kiểm nhanh BG-e3/BG-e4 (bằng chữ "đồng", nhãn "Người xem", tên DEMO trong test)

Bạn là worker Codex, chạy không tương tác. Lead quyết sau kiểm nhanh (`docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\giao-bg-e3.md`, `giao-bg-e4-v2.md`): **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM — **ghi tệp bằng UTF-8**. Worktree hiện tại, nhánh `lat/bg-e5` (từ `lat/bg-gom` = BG-e1…e4). Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL. Chạy node: `node tests/crm_giao_ket_async.cjs`, `node tests/khung_luoi_async.cjs`, `node tests/m4_01c_async.cjs`, `node tests/crm_du_an_ban_async.cjs` (+ 20 bộ: 8 bộ lỗi nền như handoff BG-e3).

**Việc:**
1. **Bằng chữ giữ "đồng"** (BG-24 chỉ áp cho đơn vị sau **số** tiền): bỏ phần đổi "đồng" → "VND" trong dòng *Bằng chữ* ở màn Báo giá (`crm_g.js`, hàm `hienTienChuBg` ~:1014 và nơi dùng) để khớp bản DOCX/PDF do máy chủ sinh ("… đồng"). Số tiền vẫn "… VND". Cập nhật assert tương ứng trong `tests/crm_giao_ket_async.cjs` (vd "Bằng chữ: Ba mươi chín tỷ đồng").
2. **Nhãn vai thống nhất "Người xem"**: `VAI_VN` trong `crm_g.js` (~:976) đang "Chỉ xem" → "Người xem" (cùng nhãn với khung vai mô phỏng `app.js`); sửa assert node nếu có.
3. **Tên DEMO trong test**: `tests/khung_luoi_async.cjs` (~:234–242) "Công ty Ánh Dương", "Công ty Bình Minh" → tên có chữ DEMO (vd "Công ty DEMO Ánh Dương", "Công ty DEMO Bình Minh"), giữ nguyên ý ca test.
**File (≤ 3):** `src/kho_tri_thuc/giao_dien/assets/crm_g.js`, `tests/crm_giao_ket_async.cjs`, `tests/khung_luoi_async.cjs`. Không xóa file.
**Báo cáo (≤ ⅓ trang):** sửa ở file:dòng · node trước/sau · thông điệp commit `[BG-e5] …`.
