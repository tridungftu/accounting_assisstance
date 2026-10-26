Anh, đã sửa đúng 2 tệp được giao, chưa commit.

- Chặn liên kết ngoài CRM, VAY/L11/M4; lô xuất suy HĐ, kiểm UUID an toàn; audit giữ đúng PN.
- Bổ sung test hồi quy và sửa fixture M5 đủ điều kiện trigger.
- Test thuần: **15 đạt, 36 skip**, không FAIL/ERROR; `git diff --check` đạt.
- M0041/M0043 và `pg_migrations.py` nguyên vẹn; UTF-8 không BOM, migration giữ LF.

**Còn cần lead chạy PG.** Fixture VAY nới CHECK trong giao dịch test; fixture hồ sơ `crm_giao_ket` tạm tắt một guard khi dựng dữ liệu bất thường, bật lại trước kiểm; cả hai rollback.

Thông điệp commit đề xuất: `[MTQ-4a3a] vòng 2: chặn liên kết ngoài CRM và suy phạm vi HĐ cho lô xuất`