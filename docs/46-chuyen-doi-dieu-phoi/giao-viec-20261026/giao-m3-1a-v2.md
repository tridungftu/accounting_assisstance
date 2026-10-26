# M3-1a vòng 2: test PostgreSQL của M3 không được tự bỏ qua dưới bộ chạy test của lead

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở PostgreSQL. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m3-1a` (3c445d1).

**Lỗi:** lead chạy `tools/chay_test_theo_module.py --pg-demo`, nhưng lớp `M3Postgres` trong `tests/test_m3_sql.py` (khoảng dòng 104–107) **bỏ qua toàn bộ**.
- Test đọc `KHO_PG_DEMO_SO` và `KHO_PG_DEMO_DB`, là biến nội bộ của bộ chạy.
- `KHO_PG_DEMO_SO` được đặt cho mọi module. `KHO_PG_DEMO_DB` chỉ đặt cho module cần bản sao DEMO (`*_CLONE_*`).
- Vì vậy `cls.db` = None, và test gặp `SkipTest`.

**Việc:**
- `tests/test_m3_sql.py`: bỏ nhánh `runner_cap`/`KHO_PG_DEMO_*`. Luôn tự tạo CSDL `kho_test_m3_<hex>` từ `KHO_PG_DSN_TEST`, migrate, và DROP ở cleanup, đúng như `tests/test_mtq_sql.py` hay `tests/test_m4_review_chep_schema.py` đang làm.
- Không đổi các ca kiểm. Không đọc biến môi trường nội bộ nào khác của bộ chạy.
- Nếu chính `k2/sql_m3.py` có lỗi lộ ra khi chạy PG thì **không sửa** ở vòng này; lead sẽ chạy và báo.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m3_sql`, với PYTHONPATH=`src;.;tests`. Phần PG vẫn skip trong sandbox là đúng.

**Tệp (1):** `tests/test_m3_sql.py`.

**Báo cáo (≤ 3 dòng)**, thông điệp commit `[M3-1a] vòng 2: …`.
