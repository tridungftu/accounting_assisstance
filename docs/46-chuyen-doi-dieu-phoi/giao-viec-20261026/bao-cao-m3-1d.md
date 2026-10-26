Anh, đã hoàn thành M3-1d, chưa commit.

- Thêm `M3_CO_SO_C_SQL` và đăng ký `M00xx_M3_CO_SO_C`, dùng tiền tố `M3_HD_XAC_NHAN|`; giữ nguyên 45 migration cũ, gồm M0044/M0045.
- Rà soát không thấy advisory lock khác cần sửa.
- Đổi đúng 3 tệp: `k2/sql_m3.py`, `ha_tang/pg_migrations.py`, `tests/test_m3_sql.py`.
- Test: **36/54 đạt, 18 skip**, không có lỗi trong các ca đã chạy. Đã thêm test định nghĩa hàm, quyền/search_path và hai giao dịch xác nhận trùng.
- Kiểm tra UTF-8 không BOM, registry LF và `git diff --check`: đạt.

**Còn thiếu:** chưa kiểm chứng PG thực tế vì thiếu `psycopg` và `KHO_PG_DSN_TEST`.

Thông điệp commit đề xuất: `[M3-1d] Thêm tiền tố khóa advisory xác nhận hóa đơn`