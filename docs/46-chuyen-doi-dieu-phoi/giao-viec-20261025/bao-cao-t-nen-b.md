Anh, đã sửa đúng 3 file test, không commit:

- `tests/test_e1_mua_danh_muc_sua.py:40`: đếm chính xác lời gọi dọn; guard bật kiểm vị trí, số lượng và nội dung tệp giữ lại; guard tắt giữ kỳ vọng cũ.
- `tests/test_e1_mua_trich_phien_ban.py:40`: dùng cùng phép kiểm, bảo đảm lượt trích không sinh thêm `.tmp`.
- `tests/test_m1.py:403`: giả đường dẫn raw không tồn tại; kiểm `FileNotFoundError` đúng đường dẫn, raw gốc nguyên vẹn, backup chưa công bố.

Kiểm bằng mock an toàn: **58/58 mỗi trạng thái guard**, không lỗi mới; hai kiểm tra âm đều bắt được sai lệch. UTF-8 không BOM và `git diff --check` đạt. Chưa kiểm runtime DEMO thật vì sandbox chặn đọc runtime.

Mã sản phẩm vẫn có `rollback.unlink()` tại `tools/source6_g5_e5/trich_xuat/danh_muc.py:280`; giữ nguyên để lead xử lý.

Thông điệp commit: `[T-NEN-b] Sửa test E1/M1 tương thích guard không xóa tệp`