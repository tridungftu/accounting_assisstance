Anh, đã triển khai **XS-3A** trên nhánh `lat/xs-3a`, chưa commit.

- Thêm `ha_tang/engine.py`: hợp đồng vào/ra, `XONG/CHO/LOI`, mã lý do, bằng chứng hash và thời điểm UTC.
- Thêm `ha_tang/danh_ba_engine.py`: đăng ký, tra cứu, liệt kê; từ chối trùng; thêm phiên bản cần cờ tường minh.
- Thêm `tests/test_xs3_engine.py`: 19 test và khung kiểm hợp đồng dùng lại.

Tự kiểm: đúng ba tệp, UTF-8 không BOM, LF, không lỗi whitespace. Chưa bọc engine thật.

**Test: NOT_RUN — 0/19 đã chạy**, môi trường không có Python. Chưa xác minh lỗi mới so với nền v4.

**Cần lead:** chạy test và hồi quy. Thông điệp commit đề xuất: `[XS-3a] Thêm hợp đồng engine và danh bạ phiên bản`.