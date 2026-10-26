Anh, đã hoàn tất MTQ-3b2, chưa commit.

- Sửa đúng 4 tệp: `app.js`, `index.html`, **`khung_khai_bao.py`** và `tests/khung_luoi_async.cjs`.
- Ô hiện cho mọi vai, màu `he_thong`; màn dựng lười, chọn theo `la_admin`, cấp nhãn sẵn có và hủy phản hồi cũ khi đổi vai. Không thêm nút “Bật”.
- Test: **46/46 ca khung đạt**, gồm 6 ca MTQ mới. Toàn bộ `tests/*.cjs`: **18/23 bộ đạt**, nền `lat/ui-ky`: **17/23**; **không thêm bộ đỏ**. Còn 4 bộ thiếu fixture/môi trường và 1 bộ M4 lỗi sẵn.
- UTF-8 không BOM, diff hợp lệ. Chưa thử GUI thật; không mở server.

Thông điệp commit đề xuất: `[MTQ-3b2] Nối Ma trận thẩm quyền vào trang chủ hệ thống`