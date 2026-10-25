# DA-3a vòng 2 — sửa B1 theo review (dự án Ngừng bán không được khóa nháp cũ)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/da-3a` (CRM · Báo giá nạp mặc định từ Dự án đang bán). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không khởi động PostgreSQL/server (lead chạy ca PostgreSQL). Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`; nếu sandbox chặn python → ghi rõ "lead chạy test".

**Lỗi (review B1):** `src/kho_tri_thuc/k2/crm_giao_ket.py` — `luu` (~:1066) luôn gọi `_gan_tieu_chuan` → `_chuan_du_an` (~:871-880) báo lỗi `CRM_GK_TRANG_THAI` khi dự án đã **Ngừng bán**, nên báo giá **nháp cũ** của dự án đó không lưu được nữa.

**Lead quyết (thà bỏ sót còn hơn nhập sai, nhưng không khóa việc đang dở):**
- Chặn "Dự án đã ngừng bán" **chỉ khi**: tạo báo giá mới, **đổi** dự án so với bản đã lưu, hoặc báo giá có `lo_id` (chọn lô/căn từ danh mục bán).
- Các trường hợp còn lại (lưu lại nháp cũ, cùng dự án, không có `lo_id`): **cho lưu**, không lấy giá/phí tiêu chuẩn mới, ghi nhận `khac_tieu_chuan` như nhánh "báo giá nhập tay cũ" hiện có (trả `None` từ chuẩn dự án), không đổi số tiền người dùng đã nhập.
- `mac_dinh_bao_gia` (nạp mặc định cho màn hình) giữ nguyên: dự án Ngừng bán vẫn báo lỗi.

**Test** trong `tests/test_crm_bao_gia_mac_dinh.py` (thuần/mock như các ca hiện có): (a) nháp cũ, dự án chuyển Ngừng bán, lưu lại cùng dự án không lô → lưu được, có cờ khác tiêu chuẩn, số tiền giữ nguyên; (b) tạo mới với dự án Ngừng bán → `CRM_GK_TRANG_THAI`; (c) đổi sang dự án Ngừng bán → lỗi; (d) có `lo_id` thuộc dự án Ngừng bán → lỗi.

**File được sửa (chỉ):** `src/kho_tri_thuc/k2/crm_giao_ket.py`, `tests/test_crm_bao_gia_mac_dinh.py`. Không xóa file.
**Test phải đạt:** `--module test_crm_bao_gia_mac_dinh --module test_crm_ky_ket --module test_crm_giao_ket_http`.
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · ca test · thông điệp commit `[DA-3a] vòng 2: …`.
