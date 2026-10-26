# M3-1b vòng 2: test PostgreSQL ba đẳng thức không được tự bỏ qua dưới bộ chạy của lead

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở PostgreSQL. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m3-1b` (đã nhận M3-1a vòng 2).

**Lỗi:**
- Lớp `BaDangThucPostgres` trong `tests/test_m3_dang_thuc.py` (khoảng dòng 253–266) đòi DSN `KHO_PG_DSN_TEST` đã trỏ vào CSDL tên `kho_test_*`, nếu không thì `skipTest`.
- Bộ chạy của lead đưa DSN **quản trị** (CSDL khác tên), nên toàn bộ ca PG bị bỏ qua.

**Việc:** trong `tests/test_m3_dang_thuc.py`:
- Sửa theo đúng mẫu `tests/test_m3_sql.py` vòng 2: trong `setUpClass`, tự tạo CSDL `kho_test_m3b_<hex>` từ DSN quản trị, `pg.migrate`, rồi DROP ở cleanup.
- Mỗi ca chạy trong giao dịch rollback như hiện tại.
- Không đọc biến nội bộ `KHO_PG_DEMO_*`.
- Không đổi các ca kiểm.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m3_dang_thuc`, với PYTHONPATH=`src;.;tests`. PG skip trong sandbox là đúng.

**Tệp (1):** `tests/test_m3_dang_thuc.py`.

**Báo cáo (≤ 3 dòng)**, thông điệp commit `[M3-1b] vòng 2: …`.
