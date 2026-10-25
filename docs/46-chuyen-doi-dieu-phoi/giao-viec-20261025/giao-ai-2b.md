# AI-2b — Nhật ký cổng AI vào PostgreSQL: migration M0034 + bộ ghi `nhat_ky.cong_ai_goi`

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại** (TL 48 §1.1: mọi lượt gọi cổng ghi `nhat_ky.cong_ai_goi`). Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM. Worktree hiện tại, nhánh `lat/ai-2b` (từ hop-nhat, đã có AI-2a `src/kho_tri_thuc/tri_thuc/cong_ai.py`). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không khởi động PostgreSQL — lead chạy PG.

**Việc:**
1. Migration **M0034** (append-only, theo mẫu các migration gần nhất trong `src/kho_tri_thuc/ha_tang/pg_migrations.py`; không sửa migration cũ): thêm các cột còn thiếu vào `nhat_ky.cong_ai_goi` (bảng đã có ~:431-448) theo bảng ánh xạ trong docstring `BanGhiCongAI` (`tri_thuc/cong_ai.py`) — worker AI-2a ghi cần **9 cột mới**; hai cột `dau_vao_mask_hash`, `ket_qua_tom_tat` để NULL. Bảng chỉ ghi thêm (không UPDATE/DELETE cho vai ứng dụng), quyền giống các bảng `nhat_ky` khác; **không có cột chứa văn bản gốc/đã che hay khóa**.
2. Bộ ghi PostgreSQL (lớp mới, ví dụ `BoGhiPostgres` trong `cong_ai.py` hoặc module mỏng cạnh đó) cài giao diện `BoGhiNhatKy`: ghi một dòng mỗi `BanGhiCongAI`; lỗi ghi không làm mất kết quả gọi AI (chỉ ghi tên loại lỗi như AI-2a).
3. Test: thuần (bộ ghi giả kết nối) + ca PG (skip khi thiếu `KHO_PG_DSN_TEST`, lead chạy): migrate lên M0034 sạch; ghi 1 lượt Local + 1 lượt Cloud không gửi; vai ứng dụng không UPDATE/DELETE được; không có cột văn bản.
**File được sửa/tạo (≤ 3):** `ha_tang/pg_migrations.py` (chỉ thêm M0034), `tri_thuc/cong_ai.py` hoặc module mới, `tests/test_cong_ai_nhat_ky.py` (mới). Test ghim tổng migration nếu có → báo lead (không sửa test khác).
**Báo cáo cuối (≤ ⅓ trang):** cột thêm · quyền · test · thông điệp commit `[AI-2b] …`.
