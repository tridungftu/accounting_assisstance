Đã sửa đủ 6 điểm trong đúng 3 tệp, lưu UTF-8 không BOM; giữ nguyên SQL/migration.

- Test: **39 đạt, 25 PG tự skip, tổng 64**; không FAIL/ERROR. `git diff --check` đạt.
- Đã thử `dich_vu` thật với app giả dùng `Lock`: không treo, nhả khóa và đóng kết nối khi lỗi.
- **Cần Anh:** Lead chạy 25 test PG ngoài sandbox.
- Không commit. Thông điệp đề xuất: `[MTQ-2b] Sửa lưu nháp, kiểm quyền đọc và xử lý lỗi nhật ký thẩm quyền`.