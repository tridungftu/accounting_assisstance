# C3c — CRM 42 · danh sách hợp đồng S1: che cờ suy từ tiền + làm chắc test (sau review vòng 2)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/c3c` (từ hop-nhat, đã gộp C3). Sandbox không ghi `.git`: **không commit**. Không nối CSDL (lead chạy PostgreSQL sau).

**Quyết định:** `docs/QUYET-DINH.md` **QD-20261025-22** — cờ "Quá hạn" (`QUA_HAN`) và "Thiếu căn cứ" (`THIEU_CAN_CU`) suy từ lịch + số đã thu → **che** với vai không có quyền xem tiền (QD-15), và **không cho lọc** `co=QUA_HAN`/`co=THIEU_CAN_CU` với vai đó (bỏ qua bộ lọc hoặc 400 tiếng Việt — chọn cách không lộ: trả như không có kết quả lọc tiền, kèm `khong_quyen_xem_tien`).

**Việc (file:dòng theo review):**
1. `src/kho_tri_thuc/k2/crm_s1.py:144-145, 336-341`: che hai cờ bằng điều kiện `xem_tien` ngay trong SQL (vd `CASE WHEN h.xem_tien THEN … END`) và phía Python `_dong`; lọc theo hai cờ chỉ áp khi có quyền xem tiền. Cờ không suy từ tiền (vd chờ ký, chờ kiểm) giữ nguyên.
2. `tests/test_crm_42_s1_http.py:318-330` — làm chắc ca dương bán hàng: thêm một hợp đồng của bán hàng **có** `gia_tri_minor` hoặc lịch hiệu lực có đợt đến hạn, rồi assert giá trị tiền khác null và ít nhất một thẻ khác 0 cho bán hàng có binding; thêm ca **binding lệch dự án** (binding có `du_an_id` khác) → hợp đồng bị ẩn; thêm ca vai XEM: không thấy cờ `QUA_HAN`/`THIEU_CAN_CU`, lọc theo cờ không lộ hợp đồng. Ca thuần/mock tương ứng trong `tests/test_crm_42_s1_tinh.py`.

**File được sửa (chỉ):** `src/kho_tri_thuc/k2/crm_s1.py`, `tests/test_crm_42_s1_http.py`, `tests/test_crm_42_s1_tinh.py`. Không xóa file.
**Test phải đạt:** `--module test_crm_42_s1_tinh --module test_crm_42_s1_http --module "test_crm_*"` không thêm mã lỗi so với nền v4 (PG skip; lead chạy PG).
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · ca test · thông điệp commit `[C3c] …`.
