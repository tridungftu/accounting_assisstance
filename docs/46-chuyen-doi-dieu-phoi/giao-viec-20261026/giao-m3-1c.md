# M3-1c: M3 · Hóa đơn bán ra & doanh thu BĐS, điểm nên sửa của review M3-1b (câu chữ, hóa đơn bị thay thế, một hóa đơn hai hợp đồng)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì PENDING và ghi "Cần Anh".
- Ghi tệp UTF-8 không BOM. `pg_migrations.py` giữ LF. **Không commit**.
- Không mở server hay PostgreSQL; test PG tự tạo CSDL `kho_test_*` như `tests/test_m3_sql.py` và **không** đọc biến `KHO_PG_DEMO_*`. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m3-1c`, dựng từ hợp nhất.
- Đã có **M0042** (`k2/sql_m3.py`, `M3_CO_SO_SQL`) và dịch vụ `k2/m3.py` (M3-1b). **Không sửa M0042**; thay đổi SQL dùng migration mới, tên tạm `M00xx_M3_CO_SO_B`, dấu `# M3-1c — CD-013:`. Test không ghim số thứ tự hay hash byte tệp.
- Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-dl2-cd1-m3-1.md`, phần M3-1b.

**Việc:**
1. **Câu hiện cho người dùng** (`k2/m3.py` khoảng dòng 134–211):
   - Bỏ "Cần Anh…" và "policy thuế số 7". Thay bằng câu nghiệp vụ trung tính, ví dụ "Chưa có xác nhận cơ sở thuế của bộ phận thuế." hoặc "Chưa đủ căn cứ để đối chiếu.".
   - Tách lý do "thiếu đơn vị tiền" và "không xem được hóa đơn" khỏi "đồng tiền khác nhau" (dòng ~164–166).
2. **Hóa đơn đã bị thay thế hoặc hủy không được cộng:**
   - Lớp đọc so phiên bản hóa đơn đã ghim trong liên kết với bản hiện hành (`eligible_content_id` hoặc bản thay thế trong M2).
   - Khác nhau hoặc đã có hóa đơn thay thế → `PENDING`, lý do "Hóa đơn đã được thay thế/điều chỉnh, cần xác nhận lại liên kết.".
   - Không tự chuyển sang hóa đơn mới.
3. **Một hóa đơn không được xác nhận vào hai hợp đồng:**
   - Migration mới: chỉ mục UNIQUE một phần trên liên kết **đã xác nhận** theo hóa đơn, hoặc trigger tương đương trên bảng liên kết của M0042.
   - Chưa có quy tắc chia giá trị: không thêm cột chia, ghi "Cần Anh: hóa đơn chung cho nhiều hợp đồng có cần chia giá trị không".
4. Đăng ký migration trong `pg_migrations.py` như mô tả trên.

**Test:**
- `tests/test_m3_dang_thuc.py`:
  - câu không chứa "Cần Anh", "policy", "#7";
  - lý do thiếu đơn vị tiền tách riêng;
  - hóa đơn bị thay thế → PENDING (thuần + PG).
- `tests/test_m3_sql.py` (PG): xác nhận cùng hóa đơn vào hợp đồng thứ hai bị từ chối; ứng viên thì vẫn được.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m3_dang_thuc tests.test_m3_sql`, với PYTHONPATH=`src;.;tests`.

**Tệp (≤ 4):** `k2/m3.py`, `k2/sql_m3.py` (thêm hằng `M3_CO_SO_B_SQL`, không đổi hằng cũ), `ha_tang/pg_migrations.py`, test (≤ 2).

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M3-1c] …`.
