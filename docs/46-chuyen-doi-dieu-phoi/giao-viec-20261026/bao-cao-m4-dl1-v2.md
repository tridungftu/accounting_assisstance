Anh, đã sửa đủ điểm 1–5, đúng ba tệp: `sql_review_chep.py`, `pg_migrations.py`, `test_m4_review_chep_schema.py`.

- HĐ nguồn sang bảng riêng, PK `(nguon_id, ma_hd)`, FK về hồ sơ; bỏ định nghĩa 15 cột `review_*`.
- Mỗi `nguon_id` là một lần chụp; docstring hướng dẫn lấy bản hiện hành từ lần chụp mới nhất của HĐ.
- Đổi đủ 16 cột sang `numeric`, ghi rõ `Decimal(repr(x))`, giữ NULL; sửa RLS và test migration theo index.
- **Test:** 7/7 thuần đạt, không lỗi mới trong module; 11 test PG skip, chờ lead chạy. `git diff --check` đạt; UTF-8 không BOM.

**Cần Anh:** trước khi nạp, người phụ trách phải chốt bảng ánh xạ `ma_hd → master.hop_dong / pháp nhân / dự án`.

Không commit. Thông điệp đề xuất: `[M4-DL1] vòng 2: tách nguồn HĐ theo lần chụp, chuẩn numeric và RLS`.