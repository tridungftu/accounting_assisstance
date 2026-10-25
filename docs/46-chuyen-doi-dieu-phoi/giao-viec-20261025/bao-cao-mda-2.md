Anh, đã hoàn tất MDA-2, đúng 3 tệp:

- `crm_g.js:622`: danh sách mốc, khai/sửa ngày, lý do, ngừng dùng, lịch sử; xử lý 400/403/409 và khóa gửi lại.
- `style.css:76`: cảnh báo mốc quá ngày.
- `tests/crm_du_an_ban_async.cjs:317`: **7/7 ca yêu cầu đạt**.

Node trước → sau: Dự án **32 → 39 nhóm đạt**; Giao kết đạt; Khung lưới **22/22**. Toàn bộ **13/20 bộ đạt, 7 lỗi nền, không lỗi mới** (`crm_ky_ket_async` hiện đạt). Đã sửa mock đổi vai khiến bộ Dự án trước đây thoát sớm sau 10 nhóm.

UTF-8 không BOM, cú pháp và `git diff --check` đạt. Chưa thử trình duyệt; không mở server/PostgreSQL, không commit.

Thông điệp đề xuất: `[MDA-2] Bổ sung quản lý mốc thanh toán và lịch sử dự án`