Anh, đã sửa đúng 2 file, chưa commit:

- `tools/chay_test_theo_module.py:304,662,946`: `_goi` không nạp provider; tiến trình test vẫn giữ guard. Sau DROP, kiểm lại `pg_database`: còn thì ghi `con_lai_sau_xoa`, cảnh báo và cho phép dọn lại; chỉ ghi `da_xoa` khi xác nhận đã mất. Đã cập nhật docstring.
- `tests/test_chay_test_pg_demo.py:24,199,485`: cô lập provider của caller, bổ sung test DROP bị nuốt và kiểm sau DROP lỗi.

**Test sandbox trước/sau:** 40/41 → **44/45**, cùng 1 skip A517 thật; không lỗi mới. Ba test review nêu đạt **3/3** với caller giả lập có provider. UTF-8 không BOM và `git diff --check` đạt.

Chưa nối CSDL; runtime DEMO thật và kiểm số CSDL trước/sau do lead chạy.

Thông điệp commit đề xuất: `[L0-8e] vòng 2: kiểm DROP trung thực và cô lập provider trong test`