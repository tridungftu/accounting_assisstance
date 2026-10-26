Đã tạo đúng 2 tệp CLI và test, UTF-8 không BOM. Công cụ đọc đủ 12 bảng, kiểm SHA256, ghi trong một transaction, chặn replay khác dữ liệu và báo cáo không lộ định danh.

- **Test lát:** 16 đạt, 6 PG skip.
- **Kèm regression DL2/DL3/schema:** 45 đạt, 42 skip; không lỗi trong phạm vi đã chạy.
- Không truy cập DB thật, không sửa DL2/DL3, không commit.

**Cần Anh:** lead chạy 6 test PostgreSQL trên CSDL `kho_test_*` riêng trước nghiệm thu.

Thông điệp commit đề xuất: `[M4-CD1] Thêm công cụ chuyển Review SQLite sang PostgreSQL nguyên tử, chạy lại không trùng`