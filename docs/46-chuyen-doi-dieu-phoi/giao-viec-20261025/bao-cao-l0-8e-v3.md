Anh, đã sửa đúng hai file được giao, chưa commit.

- **Gốc lỗi:** `tools/chay_test_theo_module.py:368` bản cũ chỉ kiểm `_pg_demo` trên hàm ngoài cùng. Guard che dấu này khiến hook cài hai lần; test giả tái hiện đúng lỗi tại `dang_ky:292`.
- **Cách sửa:** giữ dấu đã cài trên module psycopg, gắn với sổ/lần chạy/cụm. Giữ guard và toàn bộ kiểm tra sở hữu.
- **Test:** trước sửa 44 đạt/1 skip; sau sửa **50 đạt/1 skip**, ERROR/FAIL = 0. Sáu ca mới kiểm CREATE đăng ký một lần, tên có sẵn/tái dùng bị từ chối, nạp khác tên module, khác sổ và DROP bị guard giữ rồi `_goi` dọn. UTF-8 không BOM; `git diff --check` đạt.
- **Còn lại:** lead kiểm runtime thật + PostgreSQL và số CSDL trước/sau; tôi không nối CSDL.

Thông điệp commit đề xuất: `[L0-8e] vòng 3: tránh cài lặp hook sở hữu PG khi guard bọc ngoài`