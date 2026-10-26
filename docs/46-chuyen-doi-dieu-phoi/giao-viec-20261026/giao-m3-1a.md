# M3-1a: M3 · Hóa đơn bán ra & doanh thu BĐS, SQL cơ sở doanh thu/thuế của hợp đồng + liên kết hóa đơn–hợp đồng (CD-013; v2 §6, §16; mô hình `THIET-KE-M3-DU-LIEU.md`)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn (PENDING, không đoán) và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM. `pg_migrations.py` giữ LF.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m3-1a`, dựng từ hợp nhất. Migration cuối hiện là **M0040**. MTQ-4a0 đang chờ gộp (sẽ là M0041), nên dùng tên tạm `M00xx_M3_CO_SO` với dấu `# M3-1a — CD-013:`. Test **không ghim số thứ tự, không ghim hash byte tệp**.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\THIET-KE-M3-DU-LIEU.md`: thực thể hợp đồng-cơ sở, liên kết hóa đơn–hợp đồng, ba đẳng thức, PENDING.
- Thiết kế `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M3-HOA-DON-BAN-VA-DOANH-THU-v2-20261026.md` §6, §9, §10, §16.
- Hộp thư CD-013, CD-014: **không số tài khoản**; tài khoản là policy, làm ở bước sau.
- CRM hiện có: `k2/sql_crm*.py`. Lưu ý `sql_crm_du_an_ban.py` có `gia_dat_tru` là **mức/m²** mặc định 0.

**Việc: tệp mới `src/kho_tri_thuc/k2/sql_m3.py` (chỉ hằng SQL `M3_CO_SO_SQL`), schema mới `m3` hoặc theo quy ước schema hiện có.**
1. Bảng **cơ sở hợp đồng** theo hợp đồng/phiên bản CRM:
   - giá trị trước VAT, **tổng giá đất được trừ** (nhập/xác nhận theo hợp đồng; **không** tự nhân từ mức/m² × diện tích), phần chịu thuế, VAT, tổng thanh toán;
   - currency; trạng thái xác nhận (PENDING / ĐÃ XÁC NHẬN), người/lúc xác nhận;
   - tiền `numeric`, không float;
   - bất biến theo phiên bản: sửa thì tạo bản mới, giữ bản cũ;
   - ràng buộc: phần chịu thuế = giá trị trước VAT − giá đất được trừ, khi cả hai có giá trị; không âm.
2. Bảng **liên kết hóa đơn bán (M2) ↔ hợp đồng/phiên bản**:
   - khóa ổn định, nguồn, người/lúc;
   - một hóa đơn có thể là ứng viên chưa xác nhận;
   - không tạo kho hóa đơn M3 song song; tham chiếu bảng hóa đơn M2 đang có.
3. **"Hình thức doanh thu" theo loại hình** (ghi nhận luôn / phân bổ): bảng policy cấu hình, có hiệu lực từ ngày. Không cứng trong code. Không cột tài khoản.
4. RLS và quyền theo mẫu các bảng CRM/M4: `app_web` chỉ đọc theo pháp nhân được phép; ghi qua kết nối chủ bảng. Nhật ký thay đổi theo mẫu có sẵn.
5. Append migration vào `pg_migrations.py` như mô tả trên.

**Không làm ở lát này:** ba đẳng thức (lát M3-1b, Python), màn hình, đợt thu, máy chuyển lớp.

**Test, tệp mới `tests/test_m3_sql.py`:**
- Phần tĩnh: hằng chỉ SQL; không có chữ "tài khoản" hay số tài khoản trong DDL; registry append theo dấu.
- Phần PG (`skipUnless KHO_PG_DSN_TEST`, CSDL `kho_test_*` riêng):
  - ràng buộc phần chịu thuế;
  - không âm;
  - bản mới giữ bản cũ;
  - app_web không ghi được, chỉ đọc đúng pháp nhân;
  - liên kết hóa đơn tham chiếu đúng bảng M2;
  - policy hình thức doanh thu theo ngày hiệu lực.
- Chạy thuần: `python -X utf8 -m unittest tests.test_m3_sql tests.test_pg_schema`, với PYTHONPATH=`src;.;tests`.

**Tệp (3):** `k2/sql_m3.py`, `ha_tang/pg_migrations.py`, `tests/test_m3_sql.py`.

**Báo cáo (≤ ¼ trang):** bảng đã tạo, số test, phần "Cần Anh", thông điệp commit `[M3-1a] …`.
