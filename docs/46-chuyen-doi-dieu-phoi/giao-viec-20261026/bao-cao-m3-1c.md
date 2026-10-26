Anh, đã sửa câu nghiệp vụ, tách lý do thiếu đơn vị tiền/không xem được hóa đơn; loại hóa đơn thay thế khỏi phép cộng và trả `PENDING`. Đã thêm UNIQUE index cho liên kết xác nhận, giữ nguyên M0042.

- **4 tệp đổi:** `m3.py`, `sql_m3.py`, `pg_migrations.py`, `test_m3_sql.py`; gom test bổ sung để giữ giới hạn.
- **Test:** 33/45 đạt, 12 PG skip do thiếu DSN test; không lỗi mới trong phần đã chạy. UTF-8 không BOM, registry LF, `git diff --check` đạt.
- **PENDING:** chưa xác minh PG thực tế. UNIQUE giữ cả xác nhận lịch sử, nên cũng chặn xác nhận lại cùng hóa đơn.
- **Cần Anh:** hóa đơn chung cho nhiều hợp đồng có cần chia giá trị không.

Không commit. Thông điệp đề xuất: `[M3-1c] Sửa cảnh báo và chặn hóa đơn thay thế, liên kết trùng`.