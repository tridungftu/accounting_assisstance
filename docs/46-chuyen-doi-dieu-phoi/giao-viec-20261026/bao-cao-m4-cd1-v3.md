Đã hoàn tất từ `18e3bc8`; chỉ sửa `tests/test_chuyen_review_pg.py`: mock trả đủ số đếm 12 bảng, kiểm tra warning và báo cáo thành công.
Test: 24/30 đạt, 6 PostgreSQL bỏ qua; exit 0, không lỗi mới trong bộ chỉ định; UTF-8 không BOM. Không mở PostgreSQL/dữ liệu thật, không commit.
Thông điệp đề xuất: `[M4-CD1] vòng 3: hoàn tất kiểm thử Ctrl+C và chặn cảnh báo psycopg`.