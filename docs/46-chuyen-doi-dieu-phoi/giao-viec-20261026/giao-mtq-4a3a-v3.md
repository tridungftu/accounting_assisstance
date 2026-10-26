# MTQ-4a3a vòng 3: sửa một test PG (fixture), không đổi SQL

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.** Ghi UTF-8 không BOM. **Không commit**. Không mở server/PostgreSQL DEMO. Không xóa file. Worktree hiện tại, nhánh `lat/mtq-4a3a` (commit 978b041).

**Lead chạy PG (15:32):** 149 ok, chỉ 1 lỗi mới ở `tests/test_mtq_cong_c_sql.py:483` `test_ho_so_gan_hd_m4_hoac_crm_giao_ket_bi_chan_va_audit`:
`self.c.execute("ALTER TABLE master.hop_dong DISABLE TRIGGER hop_dong_gk_kiem")` → `psycopg.errors.ObjectInUse: cannot ALTER TABLE "hop_dong" because it has pending trigger events`.
(Giao dịch đã có DML kéo theo trigger deferred trước khi ALTER.)

**Việc:** sửa **chỉ** `tests/test_mtq_cong_c_sql.py` để dựng dữ liệu bất thường mà không vướng sự kiện trigger đang chờ — ví dụ `SET CONSTRAINTS ALL IMMEDIATE` ngay trước ALTER, hoặc đưa ALTER/ENABLE lên **trước** mọi DML trong giao dịch đó, hoặc dựng dòng hồ sơ trong một giao dịch riêng của CSDL `kho_test_*`. Phải bật lại trigger trước bước kiểm và vẫn rollback/dọn như cũ. **Không** sửa `k2/sql_mtq_cong.py`, migration hay test khác.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_cong_c_sql` (PG skip; lead chạy PG). **Tệp (1):** `tests/test_mtq_cong_c_sql.py`. **Báo cáo (≤ 5 dòng)**, thông điệp `[MTQ-4a3a] vòng 3: …`.
