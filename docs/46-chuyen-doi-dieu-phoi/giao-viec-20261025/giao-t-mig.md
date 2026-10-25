# T-MIG — Sửa test cũ đặt cứng số/vị trí migration (để test PostgreSQL chạy thật thay vì FAIL "NOT_VERIFIED")

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/c1a` (hop-nhat + **M0032 G5** do lead gắn, commit `0b636d1`). Sandbox không ghi `.git`: **không commit**. Không nối CSDL (lead chạy PostgreSQL sau). Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`.

**Hiện trạng (lead chạy `--pg-demo`, chuỗi migration hiện có 32):** nhiều test viết khi chuỗi còn 18–25 nên khẳng định cứng:
- `test_crm_doi_chieu_pg`, `test_crm_kiem_hd`, `test_crm_kiem_hd_http`, `test_crm_g6a_m25_integration`: `NOT_VERIFIED: registry code chưa tích hợp M4M24 + G6A (PG_SCHEMA_VERSION=32, vị trí G6A=[24]; cần 25 với G6A là migration cuối)`;
- `test_crm_giao_ket_http` (`32 != 21`), `test_crm_ky_ket_http` (`32 != 23`), `test_crm_41_02_http` (`32 != 18`), `test_crm_neutral_compat`, `test_pg_schema` (`1 != 0`);
- `test_crm_doi_chieu_tinh`: `True is not false : gói không tự đăng ký migration` — nay G5 **đã được owner gắn** thành M0032.

**Việc:**
1. Thay các khẳng định "đúng N migration" / "G6A là migration cuối" bằng khẳng định **bất biến đúng nghĩa**: migration cần thiết **có mặt đúng một lần** ở **vị trí đã chốt** (G6A = M0025, M4 duyệt = M0024, G5 = M0032 …) và checksum M0001..Mk không đổi; số tổng ≥ vị trí đó (không ghim tổng). Giữ nguyên ý đồ kiểm tra của từng test.
2. `test_crm_doi_chieu_tinh`: khẳng định module `sql_crm_doi_chieu.py` **không tự import/đăng ký** `ha_tang.pg_migrations` (giữ), và `CRM_G5_SQL` được đăng ký **đúng một lần** là M0032 (thay cho "không có trong chuỗi").
3. `test_pg_schema` `1 != 0` và `test_crm_neutral_compat`: đọc kỹ lỗi; nếu cùng loại (số migration cứng) thì sửa như trên; nếu là lỗi khác → **không sửa**, ghi vào báo cáo.
4. Chỉ sửa **test**; không sửa mã sản phẩm, migration, fixture.

**File được sửa:** chỉ các tệp `tests/test_*.py` nêu trên (≤ 9). Không xóa file.
**Test phải đạt (không PG):** các module trên không thêm mã lỗi so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json`; lead chạy lại với `--pg-demo`.
**Báo cáo cuối (≤ ½ trang):** từng tệp: khẳng định cũ → mới · tệp nào để nguyên vì lỗi khác loại · thông điệp commit `[T-MIG] …`.
