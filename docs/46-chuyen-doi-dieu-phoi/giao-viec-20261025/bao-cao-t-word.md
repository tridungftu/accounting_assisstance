Anh, đã hoàn tất:

- `tests/test_crm_giao_ket.py:1089,1104,1160`: `_co_word()` kiểm biến môi trường trước mọi kiểm tra khác; thêm test chứng minh không probe Word/tìm module/spawn khi chưa bật; cập nhật lý do skip.
- `tests/test_crm_doi_chieu_pg.py:140`: chặn helper xuất hợp đồng khi cổng Word đóng.
- Test: **62 đạt / 64 tổng, 2 skip**, không lỗi mới. Cả hai ca `WordThat` đều skip; không đặt `KHO_TEST_WORD_THAT`.
- Hai tệp UTF-8 không BOM; không đổi mã sản phẩm, không commit.

Thông điệp commit đề xuất: `[T-WORD] Chặn test Word COM trừ khi bật rõ KHO_TEST_WORD_THAT=1`.