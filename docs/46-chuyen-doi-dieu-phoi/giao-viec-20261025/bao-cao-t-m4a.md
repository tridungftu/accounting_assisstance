Anh, đã sửa đúng 3 file test, không sửa sản phẩm, không commit:

- `tests/test_m4_01b_pg.py:110`: thêm client #6 giả, tiêm vào service; giữ kiểm replay.
- `tests/test_m4_01c_http.py:90`: tiêm qua factory; kiểm Track Changes chặn trước client.
- `tests/test_m4_review_k2.py:192,299`: kiểm đủ migration 1–20 và hàm M20 hiện hành; R00 migrate đúng 19 → 20. R01 dùng cùng client giả.

Đã chạy 3 module: **2/2 ca thuần đạt** (adapter/raw hash và Track Changes); **32 ca PG/HTTP skip** vì thiếu psycopg/DSN — **NOT_RUN, không tính đạt**, chờ lead chạy. Không ERROR/FAIL; diff sạch, UTF-8 không BOM.

Thông điệp commit đề xuất: `[T-M4a] Cập nhật test M4 cho engine trích dùng chung và migration M20`