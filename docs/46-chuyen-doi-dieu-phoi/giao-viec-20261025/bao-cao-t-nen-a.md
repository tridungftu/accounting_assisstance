Anh, đã sửa đúng 4 file test:

- `tests/test_m4_02b_k2.py:253`: kiểm M0022 và checksum lịch sử 1–22, bỏ ghim tổng.
- `tests/test_m4_02c_pg.py:118,371,661`: cập nhật cổng clone/P01, giữ kiểm lịch sử 1–24 và thêm test mock.
- `tests/test_m4_03a_m26_integration.py:38`, `tests/test_m4_04c_m27_integration.py:37`: cập nhật SHA, ghi chú L0-8f/T-NEN-a.

SHA helper cuối: `1c2a85b3f9731cfcad386eda6f8306423c51164c20db7c1b1bad26c1d6b7f3a1`.

Kiểm tra: **22/58 đạt, 36 skip**, 0 lỗi; UTF-8 không BOM, compile và `git diff --check` đạt. PostgreSQL chưa chạy, chờ lead xác minh so nền PG v2. Không commit.

Thông điệp commit: `[T-NEN-a] Bỏ ghim tổng migration M4 và cập nhật SHA helper`