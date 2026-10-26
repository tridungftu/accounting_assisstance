## Review Codex (chỉ đọc) — m3-1d · 26/10 ~16:05

1. **Trọng tâm (a) — Đạt.** `k2/sql_m3.py:212`: `CREATE OR REPLACE` giữ nguyên thân hàm M0044, chỉ thêm tiền tố khóa tại dòng 216; giữ `search_path`, không đổi quyền. Test đối chiếu OID/owner/ACL/security/search_path tại `tests/test_m3_sql.py:482`.

2. **Trọng tâm (b) — Đạt.** `k2/sql_m3.py:211`: hằng mới được nối sau hằng cũ. Đối chiếu Git blob xác nhận toàn bộ nội dung SQL cũ, gồm M0044, giữ nguyên từng byte.

3. **Migration/LF/test — Đạt.** `ha_tang/pg_migrations.py:12177`: M0046 nối cuối, 45 migration cũ nguyên vẹn; tệp dùng LF, không BOM. `tests/test_m3_sql.py:49,113`: tìm migration theo dấu/tên hằng, không ghim migration cuối hay hash.

4. **Phạm vi — Đạt.** Diff đúng 3 tệp được giao; fixture mới dùng UUID sinh ngẫu nhiên và DEMO (`tests/test_m3_sql.py:499–507`). Báo cáo khớp cấu trúc **54 test: 36 thuần, 18 PG skip**.

5. **Đúng yêu cầu — Đạt trong phạm vi đọc mã.** Tiền tố đúng `M3_HD_XAC_NHAN|`; không có advisory lock khác cần sửa trong module. Test mới kiểm định nghĩa hàm và hai giao dịch xác nhận trùng (`tests/test_m3_sql.py:482,489`); các ca M3-1c được giữ và chạy với hàm mới tại dòng 410.

6. **Tiền, số liệu, quyền — Đạt.** Diff không đổi phép tính, làm tròn hay đơn vị tiền. Kiểm tra từ chối liên kết trùng vẫn nằm trong trigger máy chủ (`k2/sql_m3.py:217–224`).

7. **Không phá phần cũ — Đạt.** Nội dung migration cũ không đổi; hàm mới khớp chính xác hàm cũ sau hai thay thế được giao. Diff không thêm lời gọi AI/API bên ngoài.

8. **Giao diện/câu người dùng — Đạt.** Thông báo nghiệp vụ tiếng Việt được giữ nguyên tại `k2/sql_m3.py:223`; không thêm giao diện, ngày hay tiền hiển thị.

**Kết luận: Đạt review M3-1d.** Không có điểm **Chặn / Nên sửa / Để sau**. Tôi không chạy lại test; gate thuần OK theo thông tin Anh cung cấp, PG do lead chạy riêng.

**Hỏi Claude:** Không có.

*Các dòng trên thuộc nhánh `lat/m3-1d`; đường dẫn `k2/`, `ha_tang/` nằm dưới `src/kho_tri_thuc/`.*
---
**Lead lọc (Claude):** Đạt, không lọc. Gate máy: thuần OK, PG 105 ok 0 mã mới 0 skip.
