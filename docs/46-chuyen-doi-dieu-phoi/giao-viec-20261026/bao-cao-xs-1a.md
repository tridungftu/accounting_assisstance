Anh, đã hoàn thành code **XS-1A** trên `lat/xs-1a`, chưa commit.

- **Đã làm:** schema `bus`, outbox/inbox, dedupe chống xung đột, ACK riêng từng bên nhận; kiểm quyền phiên/pháp nhân, RLS và ACL. Payload chỉ nhận tham chiếu UUID.
- **File đổi:** `src/kho_tri_thuc/k2/sql_bus_su_kien.py`, `src/kho_tri_thuc/ha_tang/pg_migrations.py`, `tests/test_xs1_sql.py`.
- **Kiểm tra:** `git diff --check` đạt; UTF-8 không BOM, LF đúng; migration cũ không đổi.
- **Test:** đã viết 19 test; **NOT_RUN** vì không có Python. Chưa xác định lỗi mới so với nền.

**Cần lead:** đánh số `M00xx_BUS_SU_KIEN`; chạy test Python, PG qua `KHO_PG_DSN_TEST` và hồi quy.

Thông điệp commit đề xuất: `[XS-1a] Thêm SQL bus sự kiện bền outbox/inbox theo pháp nhân`.