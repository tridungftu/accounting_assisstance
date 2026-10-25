# DA-1d — CRM · Dự án đang bán máy chủ: 2 điểm cuối trước khi gộp

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM. Worktree hiện tại, nhánh `lat/da-1` (đầu `9e0378c`). Sandbox không ghi `.git`: **không commit**. Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module test_crm_du_an_ban` (PG skip; lead chạy PostgreSQL thật sau).

**Việc (review Claude vòng 2):**
1. `src/kho_tri_thuc/k2/crm_mau.py:417-431` — phương thức `ap_dung_bo_chuan` không còn route nào gọi và gọi `crm_g_chuan_ap_dung` bản 5 tham số **không còn tồn tại** trong M0031 (bản hiện có kèm CAS `expected_version`). **Bỏ phương thức này** (xóa đoạn mã trong tệp, không xóa tệp); nếu còn chỗ tham chiếu → trỏ sang đường áp dụng tiến độ hiện hành có CAS.
2. `src/kho_tri_thuc/k2/crm_du_an_ban.py:120-121` và `src/kho_tri_thuc/k2/sql_crm_du_an_ban.py:217` — mặc định `thue_suat = "10"` và `gia_dat_tru = "0"` đang áp **cả khi sửa** (`cap_nhat`): thiếu trường thì thuế 8%/KCT đã lưu bị đè im lặng thành 10% — trái nguyên tắc "thà bỏ sót còn hơn nhập sai". Sửa: chỉ mặc định ở **bật bán**; ở **cập nhật**, trường không gửi thì **giữ giá trị của phiên bản hiện hành** (cả Python và SQL — không để SQL tự đặt mặc định khi cập nhật). Thêm ca test: bản hiện hành thuế 8% + giá đất 20, cập nhật chỉ đổi mô tả → bản mới vẫn 8% + 20; ca PG tương ứng viết sẵn.

**File được sửa (chỉ):** `src/kho_tri_thuc/k2/crm_mau.py`, `src/kho_tri_thuc/k2/crm_du_an_ban.py`, `src/kho_tri_thuc/k2/sql_crm_du_an_ban.py`, `tests/test_crm_du_an_ban.py`, `tests/test_crm_du_an_ban_pg.py`. Không sửa `pg_migrations.py`; không xóa file.
**Test phải đạt:** `--module test_crm_du_an_ban --module "test_crm_*"` không thêm mã lỗi so với trước khi sửa.
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · ca test · thông điệp commit `[DA-1] giữ thuế khi cập nhật, bỏ hàm áp dụng G7 cũ`.
