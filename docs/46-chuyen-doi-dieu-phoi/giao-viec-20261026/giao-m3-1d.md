# M3-1d: M3 · Hóa đơn bán ra & doanh thu BĐS, tiền tố khóa advisory cho trigger một liên kết xác nhận/hóa đơn (nên sửa review M3-1c)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. `pg_migrations.py` giữ LF. **Không commit**. Không mở server hay PostgreSQL DEMO. Không xóa file.
- Test PG tự tạo CSDL `kho_test_*` như `tests/test_m3_sql.py`; không đọc `KHO_PG_DEMO_*`.
- Làm trong worktree hiện tại, nhánh `lat/m3-1d`, dựng từ hợp nhất.
- Đã có **M0044** (`k2/sql_m3.py`, hằng `M3_CO_SO_B_SQL`, trigger `m3.lien_ket_mot_xac_nhan`).
- **Không sửa** hằng cũ. Thay đổi bằng migration mới:
  - tên tạm `M00xx_M3_CO_SO_C`, dấu `# M3-1d — CD-013:`;
  - test không ghim migration cuối hay hash byte tệp.

**Vấn đề:** trigger khóa bằng `pg_advisory_xact_lock(hashtextextended(NEW.hoa_don_id::text, 0))`, không có không gian tên. Khóa này có thể trùng khóa advisory khác cũng băm từ chuỗi UUID, ví dụ cổng MTQ khóa theo `request_id`, gây chờ chéo vô cớ giữa hai miền.

**Việc:**
1. Hằng mới `M3_CO_SO_C_SQL` trong `k2/sql_m3.py`: `CREATE OR REPLACE FUNCTION m3.lien_ket_mot_xac_nhan()`.
   - Thân hàm giữ nguyên; chỉ đổi khóa thành `hashtextextended('M3_HD_XAC_NHAN|' || NEW.hoa_don_id::text, 0)`.
   - Giữ `SET search_path` và quyền như cũ.
2. Đăng ký migration trong `pg_migrations.py` theo mẫu M0044 (lead đánh số khi gộp).
3. Rà các `pg_advisory_xact_lock` khác trong `k2/sql_m3.py`. Nếu có khóa thiếu tiền tố, cùng sửa trong hằng mới với tiền tố riêng `M3_…|` và ghi vào báo cáo.

**Test** (`tests/test_m3_sql.py`, thêm ca):
- Phần tĩnh:
  - hằng mới có tiền tố `'M3_HD_XAC_NHAN|'`;
  - hằng cũ M0044 không đổi.
- Phần PG:
  - sau migrate, `pg_get_functiondef` của hàm có tiền tố;
  - hai giao dịch xác nhận cùng hóa đơn vào hai hợp đồng vẫn bị từ chối;
  - các ca M3-1c cũ vẫn đạt.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m3_sql tests.test_m3_dang_thuc`, PYTHONPATH=`src;.;tests`.

**Tệp (3):** `k2/sql_m3.py`, `ha_tang/pg_migrations.py`, `tests/test_m3_sql.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M3-1d] …`.
