Đã hoàn thành đúng 2 tệp: `m4/review_data_pg.py` và `tests/test_m4_review_data_pg.py`, UTF-8 không BOM.

Repository ghi nguyên tử, kiểm ánh xạ/hash/replay; đọc bản hiện hành và giữ xác nhận từng ô; DTO loại trường tệp và mã nội bộ.

**Test:** mới 9 đạt, 10 PG skip. Chạy chung: **17 đạt, 28 skip, 1 lỗi hash DL1b có sẵn**, đã tái hiện trên `HEAD`; không thêm lỗi.

**Cần Anh:** lead chạy test PG và xử lý lỗi hash nền DL1b trước nghiệm thu.

Không commit. Thông điệp đề xuất: `[M4-DL2] Thêm repository PostgreSQL cho bản chụp HĐ, tham số và nguồn gốc Review`.