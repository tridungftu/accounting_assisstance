Đã sửa đúng 1 dòng, Anh.
- Căn cứ: `src/kho_tri_thuc/k2/sql_crm_doi_chieu.py:192` cho phép `CHO_CAU_HINH`; dòng 38 xác định đây là trạng thái mở.
- M0035: `src/kho_tri_thuc/ha_tang/pg_migrations.py:12017` và `:12031` quy định không giao/nhận worker, giữ việc mở chờ cấu hình.
- Sửa `tests/test_crm_ky_ket_http.py:628`: kỳ vọng `CHO_CAU_HINH`; giữ nguyên mọi kiểm khác.
- Kiểm tra: diff đúng 1 dòng, `git diff --check` đạt, UTF-8 không BOM; chưa chạy PostgreSQL theo yêu cầu.
- Không commit. Thông điệp đề xuất: `[KY-DOCX] vòng 2: sửa kỳ vọng trạng thái chờ cấu hình của k10`.