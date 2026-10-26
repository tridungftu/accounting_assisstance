Đã nối GET/POST `/api/tham-quyen/*`, chuyển đường lạ qua module trả 404; không giữ `mutation_lock`, đã thêm asset vào whitelist.
Đúng 2 tệp: `server.py`, `tests/test_mtq_http_dispatch.py`; UTF-8 không BOM.
Test: mới 5/5; tổng 32 đạt/36, 4 PostgreSQL skip; không FAIL/ERROR.
`git diff --check` đạt; chưa kiểm PostgreSQL. Không mở server, không commit.
Thông điệp commit đề xuất: `[MTQ-3b1] Nối route ma trận thẩm quyền và phục vụ asset`.