# T-MIG2 vòng 2 — sửa 2 hồi quy do vòng 1 gây ra (lead chạy PostgreSQL thật)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 — **ghi tệp bằng UTF-8**. Worktree hiện tại, nhánh `lat/t-mig2` (commit vòng 1 `9d1ff86`). Sandbox không ghi `.git`: **không commit**. Không nối CSDL. Chỉ sửa **test**.

**Kết quả lead chạy `--pg-demo` trên vòng 1 (so với nền PostgreSQL):**
1. **Mã lỗi mới** `test_crm_k2.CrmK2Test.test_t21_buoc_chuan_bi_nut_mo_demo` (và `test_t01b_…_m0010…`, `test_t01c_…schema11…` cùng lỗi): `kho_tri_thuc.ha_tang.primitives.DataError: Phần tử 0010 của chuỗi tùy chỉnh không phải định nghĩa lịch sử đã review.` — vòng 1 sửa `tests/test_crm_k2.py` (bỏ ghim tổng 13) đã dựng **chuỗi migration tùy chỉnh** sai: phần tử thứ 10 không phải đúng đối tượng định nghĩa lịch sử (`PG_MIGRATIONS[9]` hoặc định nghĩa đã review mà `ha_tang` kiểm theo danh tính/checksum). Đọc kỹ hàm kiểm "chuỗi tùy chỉnh" trong `src/kho_tri_thuc/ha_tang/` (tìm thông điệp lỗi trên) để dựng chuỗi đúng: các phần tử lịch sử phải là **đúng object** từ `PG_MIGRATIONS` (không tạo lại/sao chép), chỉ cắt/ghép theo vị trí.
2. **Họ bản sao G6A không còn được dựng:** trước vòng 1, bộ chạy ghi `pg[ho=g6a …]` cho `test_crm_kiem_hd`, `test_crm_kiem_hd_http`, `test_crm_doi_chieu_pg`, `test_crm_g6a_m25_integration`; sau vòng 1 ghi `pg[ho=- …]` và test báo `NOT_VERIFIED: thiếu biến môi trường KTT_G6A_CLONE_OWNER_DSN…`. Bộ chạy chọn họ bằng regex trên **mã nguồn module test** (`tools/chay_test_theo_module.py:416-417`: `KTT_G6A_CLONE_|\btest_crm_kiem_hd\b`) và cấp biến tại `:483-484`. Tìm vì sao 4 module trên không còn khớp (vd tên biến/chuỗi bị chuyển sang nơi khác, import đổi) và sửa **trong test** để khớp lại — **không** sửa bộ chạy.
3. Giữ nguyên các sửa đúng của vòng 1 (CASE WHEN EXISTS trước pg_has_role; bỏ ghim tổng; ca g04 theo BG-1c).

**File được sửa (chỉ):** `tests/test_crm_k2.py`, `tests/test_crm_kiem_hd.py` và tối đa 3 test G6A nêu trên nếu cần. Không xóa file.
**Test phải đạt (không PG):** các module trên không thêm mã lỗi so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json`; tự kiểm regex họ G6A bằng cách đọc mã bộ chạy và áp lên nội dung 4 tệp (in kết quả khớp trong báo cáo).
**Báo cáo cuối (≤ ⅓ trang):** nguyên nhân 1 và 2 · sửa ở tệp:dòng · bằng chứng regex khớp · thông điệp commit `[T-MIG2] vòng 2: …`.
