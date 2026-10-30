# G2 · giao G2-07 — hợp nhất validator NGUON và HOP_DONG/DU_AN từ M0065/M0067

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-06` (G2-00…G2-06; MTQ + RLS theo phiên).

## Lát G2-07

**Tệp:** `src\kho_tri_thuc\core\sql\007_pham_vi.sql`; `tests\test_g2_07.py`.

**Căn cứ:**
- Đặc tả CSDL §7, đoạn "Hành vi validator đích M0065/M0067": giữ **đồng thời**
  - nhánh NGUON của M0067 — chuẩn hóa khóa, đúng một ứng viên/ánh xạ hiện hành, kiểm mọi pháp nhân, khóa hàng;
  - ghim/kiểm quan hệ HOP_DONG/DU_AN khi cấp phạm vi của M0065, **kể cả chưa tick**.

  Không lấy nguyên bản M0067 dựng từ M0049 để làm mất B3.
- **Mã cũ (định nghĩa cuối, đọc để nâng, không chạy chuỗi cũ):**
  - `src\kho_tri_thuc\k2\sql_mtq_lien_module.py` (`MTQ_LMOD_B_SQL`, helper `mtq_nguon_ung_vien`);
  - `src\kho_tri_thuc\k2\sql_mtq_crm.py` (`MTQ_CRM_C`, ghim `quan_he`);
  - `src\kho_tri_thuc\k2\sql_mtq_cong.py` (`MTQ_CONG_H`);
  - các test cũ `tests\test_mtq_nguon_scope_sql.py`, `test_mtq_lmod_resolver_sql.py`, `test_mtq_crm_sql.py` để lấy ca kiểm.
- **Core không SQL bảng module:**
  - giải/ghim quan hệ CRM gọi resolver CRM qua `loi.dang_ky_ham_module` (G2-05/06);
  - thiếu resolver → `CHO`.

**Việc:** hàm validator cấp phạm vi MTQ trong `loi`, một định nghĩa hợp nhất cả hai nhánh. Dùng phiên xác minh (G2-03), audit (G2-04).

**Test PG** (dưới login thật + phiên):
- nguồn mơ hồ / sai pháp nhân bị chặn;
- quan hệ CRM sai bị chặn;
- quan hệ đổi sau ghim bị chặn;
- cấp phạm vi chưa tick vẫn kiểm đủ hai nhánh;
- thiếu resolver → `CHO`.

**Lưu ý lead:** nhánh hợp nhất cũ đang có `test_mtq_crm_sql` đỏ sau khi gộp 4b2b + 4i-b1 (TRANG-THAI 30/10). Đọc test này để hiểu hai nhánh va chạm thế nào; **thiết kế hợp nhất phải tránh lỗi đó**.
