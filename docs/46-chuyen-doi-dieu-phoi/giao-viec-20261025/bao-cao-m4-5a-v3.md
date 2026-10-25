Anh, đã hoàn tất vòng 3 trong đúng 3 tệp:

- [ghi_nhan_chung.py:90](src/kho_tri_thuc/k2/ghi_nhan_chung.py#L90): sửa A2; dòng 354 sửa A1; dòng 379 sửa A4, giữ nguyên `parse_so_tien` cho ghi.
- [test_m4_03b_so_tien.py:146](tests/test_m4_03b_so_tien.py#L146): kiểm khai vượt/bằng, locator lưu/xác nhận và VND `.00`/`.50`.
- [test_m4_03b_common_pg.py:464](tests/test_m4_03b_common_pg.py#L464): đủ 6 hàm REVOKE, yêu cầu đúng `InsufficientPrivilege`.

Test thuần: **104/104 đạt** (44 + 60), không ERROR/FAIL. PostgreSQL: **lead chạy test**. Đã kiểm UTF-8 không BOM và diff; không sửa M0033/fixtures, không commit.

Thông điệp commit: `[M4-5a] vòng 3: sửa cờ khai vượt, locator xác nhận và đọc tín hiệu VND; bổ sung test`