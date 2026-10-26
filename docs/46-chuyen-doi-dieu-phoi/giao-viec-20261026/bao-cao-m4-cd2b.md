Anh, đã sửa đủ 4 mục: báo cáo theo giai đoạn, kiểm dòng mồ côi/gán sai HĐ, bắt lệch tổng HĐ/đợt và kiểm `sha256_khop`.

- **File đổi:** `tools/chuyen_review_sqlite_sang_pg.py`, `src/kho_tri_thuc/m4/review_doi_chieu.py`, `tests/test_chuyen_review_pg.py`.
- **Test:** 42 đạt, 13 PG skip vì thiếu `KHO_PG_DSN_TEST`; không có lỗi trong phần đã chạy. PG chưa được xác minh.
- `git diff --check` sạch; cả ba tệp UTF-8 không BOM. Chưa commit, không mở server hay đọc dữ liệu thật.

Thông điệp commit đề xuất: `[M4-CD2b] Sửa báo cáo nạp và kiểm tra đối chiếu Review`