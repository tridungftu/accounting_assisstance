# MTQ-4a0: Ma trận thẩm quyền, cổng SQL để vai `app_web` hỏi lõi quyết định (gỡ chặn MTQ-4a). Rủi ro cao.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách **chặn** và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM. `pg_migrations.py` giữ LF, không ghi CRLF.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-4a0`, dựng từ hợp nhất. Migration cuối hiện là **M0040**. MTQ-1 = M0039 (`k2/sql_ma_tran_tham_quyen.py`).

**Bối cảnh:**
- MTQ-4a dừng vì `CrmK2` và các hàm SQL/RLS chạy dưới vai `app_web`, trong khi M0039 thu hồi quyền của `app_web` với lõi `master.mtq_quyet_dinh` và với ghi nhật ký.
- Thiết kế §5.1 (`docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md`): Python và SQL/RLS gọi **cùng lõi** trong giao dịch có ID và login của phiên; danh tính không lấy từ client. §5.2: nhật ký từ chối phải sống qua rollback, ghi bằng giao dịch riêng, lỗi ghi không thành cho phép.
- **Lead chốt hướng:** thêm hàm `SECURITY DEFINER` bọc lõi, lấy danh tính **chỉ** từ GUC phiên (`ktt_danh_tinh()` hoặc hàm danh tính đang dùng; đọc trong SQL hiện có), cấp EXECUTE cho `app_web`.

**Việc:**
1. Tệp mới `src/kho_tri_thuc/k2/sql_mtq_cong.py`, chỉ chứa hằng SQL `MTQ_CONG_SQL`:
   - `master.mtq_quyet_dinh_phien(p_hanh_dong text, p_doi_tuong jsonb, p_so_tien numeric)`:
     - `SECURITY DEFINER`, `SET search_path` cố định (`pg_catalog, master, ...` theo mẫu các hàm definer có sẵn).
     - Lấy actor từ GUC phiên; **không** nhận actor, pháp nhân hay vai từ tham số.
     - Gọi `master.mtq_quyet_dinh`; trả đúng quyết định (cho phép, mã, lý do, nguồn CU/MA_TRAN, revision, hạn mức).
     - Khi pháp nhân chưa bật trả `nguon='CU'` để Python gọi đường cũ; **không** tự quyết bằng quyền cũ trong SQL.
     - Danh tính trống hoặc không hợp lệ → từ chối.
   - `master.mtq_ghi_tu_choi_phien(...)`: ghi `nhat_ky.mtq_tu_choi` từ quyết định tin cậy (mã, hành động, đối tượng, hạn mức, số tiền so).
     - `SECURITY DEFINER`, actor từ GUC.
     - Chỉ ghi được dòng từ chối, không ghi gì khác.
     - Gọi được trong giao dịch riêng sau rollback.
   - `REVOKE ALL ... FROM PUBLIC`; `GRANT EXECUTE` cho `app_web` nếu vai tồn tại, theo mẫu `DO $$ IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_web') ...`.
   - Không mở thêm quyền đọc bảng MTQ nào cho `app_web`.
2. `src/kho_tri_thuc/ha_tang/pg_migrations.py`:
   - Append migration với tên tạm `M00xx_MTQ_CONG`, dấu chú thích `# MTQ-4a0 — CD-012:` (lead đánh số khi gộp).
   - Không sửa migration cũ.
   - `PG_SCHEMA_VERSION = len(PG_MIGRATIONS)`.

**Test, tệp mới `tests/test_mtq_cong_sql.py`:**
- Phần tĩnh:
  - hằng chỉ là SQL; có `SECURITY DEFINER` kèm `SET search_path`;
  - không có tham số actor, pháp nhân hay vai;
  - có REVOKE PUBLIC;
  - registry append đúng sau migration trước theo dấu, **không ghim số thứ tự hay hash byte tệp**.
- Phần PG (`skipUnless KHO_PG_DSN_TEST`, CSDL `kho_test_*` riêng, theo mẫu `tests/test_mtq_sql.py`):
  - `SET ROLE app_web` + GUC danh tính DEMO:
    - gọi `mtq_quyet_dinh_phien` được;
    - pháp nhân chưa bật trả `CU`;
    - không có danh tính → từ chối;
    - không đọc trực tiếp được bảng `master.mtq_*`.
  - `mtq_ghi_tu_choi_phien` ghi được một dòng; ghi xong vẫn còn sau khi giao dịch nghiệp vụ khác rollback.
  - `app_web` không gọi được `mtq_quyet_dinh` gốc.
  - Đổi GUC sang người khác thì quyết định theo người đó, không lẫn cache.
- Chạy thuần: `python -X utf8 -m unittest tests.test_mtq_cong_sql tests.test_mtq_sql`, với PYTHONPATH=`src;.;tests`.

**Tệp (3):** `k2/sql_mtq_cong.py`, `ha_tang/pg_migrations.py`, `tests/test_mtq_cong_sql.py`.

**Báo cáo (≤ ¼ trang):** chữ ký hai hàm, số test, phần "Cần Anh", thông điệp commit `[MTQ-4a0] …`.
