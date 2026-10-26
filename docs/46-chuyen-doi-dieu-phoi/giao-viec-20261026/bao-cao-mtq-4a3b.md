Anh, đã nối đủ 9 điểm và chỉ sửa `crm.py`, `quyen.py`, `tests/test_mtq_crm.py`. Đã bổ sung log `exc_info=True`, đổi thông báo trung tính; engine #6 vẫn ngoài giao dịch.

- **Audit:** chưa phát hiện route thiếu; các điểm đi qua `_tx`, rollback rồi ghi từ chối riêng.
- **Test:** thêm 20 ca, MTQ-CRM **32 → 52**; CRM giữ **690** test method (đếm tĩnh). UTF-8 không BOM và `git diff --check` đạt.
- **Cần Anh/lead:** chạy unittest và PG để nghiệm thu. Sandbox từ chối executable Python (`Access is denied`), nên chưa xác định lỗi mới so với nền.

Không commit. Thông điệp đề xuất: `[MTQ-4a3b] Nối 9 điểm CRM/M1 vào adapter thẩm quyền và bổ sung hồi quy`