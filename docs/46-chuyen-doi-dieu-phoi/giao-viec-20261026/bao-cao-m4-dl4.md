Anh, đã hoàn thiện hai tệp `review_dot_pg.py` và `test_m4_review_dot_pg.py`: ghi cùng transaction DL2/DL3, kiểm replay/hash, quyền 404, giữ Decimal/NULL/chuỗi legacy và dòng mồ côi; DTO lọc trường cấm, không suy duyệt từ `DA_NOP`.

Đã sửa fixture DL3 thiếu trường bắt buộc và mock tuple gây test đỏ.

- **DL4:** 14 đạt, 10 PG bỏ qua.
- **Hồi quy DL2/DL3/schema:** tổng 55 đạt, 52 PG bỏ qua; không lỗi trong phạm vi chạy.
- Hai tệp UTF-8 không BOM; **chưa commit**.

**Cần Anh/lead:** kiểm chứng PG với `psycopg` và DSN quản trị `KHO_PG_DSN_TEST`; môi trường hiện thiếu cả hai.

Thông điệp commit đề xuất: `[M4-DL4] bổ sung đọc ghi đợt thanh toán và lịch sử Review`