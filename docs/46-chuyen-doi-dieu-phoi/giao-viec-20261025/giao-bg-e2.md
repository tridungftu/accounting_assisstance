# BG-e2 — Báo giá: ô "Nhập nhanh lịch" (BG-21 — CD-005)

Bạn là worker Codex, chạy không tương tác. Anh đã chốt (25/10 22:05, **CD-005**; TL 45 `D:\Claude\Phan mem ho tro ke toan\45-review-man-bao-gia-sau-lap-trinh.md` **§8 dòng BG-21**): **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§4). UTF-8 không BOM — **ghi bằng UTF-8**. Worktree hiện tại, nhánh `lat/bg-e2` (từ `lat/bg-e1` — đã có lịch 5 cột % ↔ Giá trị của BG-e1). Sandbox không ghi `.git`: **không commit**. Không mở server.

**Việc (`src/kho_tri_thuc/giao_dien/assets/crm_g.js`, phần lịch của BG-e1 ~:1480):**
1. Ô **"Nhập nhanh lịch"** ngay trên bảng lịch: gõ **một số nguyên** (vd `4`) → tạo 4 dòng trống (Lần 1…4); gõ **dãy %** (vd `10%, 30%, 40%, 10%` — tách bằng phẩy, chấm phẩy hoặc khoảng trắng sau `%`; `12,5%` đọc là 12,5%) → tạo đúng số dòng, mỗi dòng ô gốc là % tương ứng, Giá trị do máy chủ tính (đường tự tính của BG-e1). Sai dạng → câu tiếng Việt ngắn, không đổi bảng.
2. Bảng đã có dòng → hỏi **"Thay lịch hiện tại?"** (xác nhận trong trang, không `confirm()` của trình duyệt nếu màn đang có mẫu hộp hỏi riêng); Hủy → giữ nguyên.
3. Σ ≠ 100% → Σ hiện **đỏ**, nút In mờ kèm lý do (giữ cơ chế hiện có nếu đã có).
4. Test node `tests/crm_giao_ket_async.cjs`: `10%, 30%, 40%, 10%` → 4 dòng đúng %, Σ = 90% đỏ, In mờ có lý do; `4` → 4 dòng; `12,5%; 87,5%` → 2 dòng; bảng có sẵn → hỏi thay, Hủy giữ nguyên; dữ liệu gửi máy chủ đúng loại gốc PERCENT.
**File (≤ 3):** `crm_g.js`, `style.css` (nếu cần), `tests/crm_giao_ket_async.cjs`. Không xóa file.
**Báo cáo (≤ ⅓ trang):** sửa ở file:dòng · ca test · node trước/sau · thông điệp commit `[BG-e2] …`.
