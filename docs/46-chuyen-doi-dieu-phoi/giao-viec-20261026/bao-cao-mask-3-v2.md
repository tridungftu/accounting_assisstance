Anh, đã sửa đủ phạm vi vòng 2.

- **9 tệp đổi:** `privacy/server.py`, `privacy/pending.py`, `privacy/static/app.js`, `privacy/static/index.html`, `tests/test_auto_api.py`, `tests/test_pending.py`, `tests/pending_ui_smoke.cjs`, `README.md`, `CHANGELOG.md`.
- Đã bỏ polling; thêm đặt sang bên tệp chờ lỗi có xác nhận, CSRF/revision; để rỗng ngữ cảnh; tách lỗi `danh_muc_chua_co`; sửa subprocess không phụ thuộc `httpx`.
- **Đạt:** `node --check privacy/static/app.js`, `node tests/pending_ui_smoke.cjs`; kiểm tra 9 tệp UTF-8 không BOM.
- **Pytest chưa chạy được:** Python báo `Access denied`; cần lead chạy lại. CHANGELOG đã ghi số đo lead cung cấp.
- Hộp xác nhận “Đánh dấu không phải định danh” chỉ ghi vào **Việc để sau**.