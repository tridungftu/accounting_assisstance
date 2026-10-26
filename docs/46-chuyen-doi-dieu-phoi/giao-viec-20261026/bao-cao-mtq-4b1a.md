Anh, đã hoàn thành phần mã MTQ-4b1a, chưa commit.

- Thêm `MTQ_CONG_D_SQL`, đăng ký M0047; bổ sung resolver và audit PN cho các bảng CRM được giao.
- Giữ nguyên whitelist H của M0045; các cặp H đọc theo màn và `TY_GIA` tiếp tục bị chặn khi bật.
- Đổi đúng 3 tệp: `k2/sql_mtq_cong.py`, `ha_tang/pg_migrations.py`, `tests/test_mtq_crm_resolver_sql.py`; thêm 18 test.
- Tự kiểm: `git diff --check` đạt, UTF-8 không BOM, migration giữ LF.
- **Test: NOT_RUN — không có `python`.** Chưa xác định lỗi mới so với nền.

**Cần lead:** chạy bộ unittest được giao và PG để xác nhận resolver, fixture, ACL.

Thông điệp commit dự kiến: `[MTQ-4b1a] Bổ sung resolver SQL cho bảng riêng CRM`.