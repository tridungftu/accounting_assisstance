# G2 · giao G2-06 — MTQ và RLS dùng phiên xác minh, resolver động (rủi ro cao, Opus review bắt buộc)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-05` (G2-00…G2-05).

Dùng lại:
- vai (001);
- danh tính (002);
- phiên `loi.xac_minh_phien` (003);
- audit + `doi_cau_truc.py` (004);
- registry `loi.dang_ky_ham_module` (005).

Quy ước như cũ: tiền tố vai test, login thật, không DROP.

## Lát G2-06

**Tệp:** `src\kho_tri_thuc\core\sql\006_mtq.sql`; `src\kho_tri_thuc\core\mtq.py`; `tests\test_g2_06.py`.

**Căn cứ:**
- Chuẩn CSDL §3.6–§3.7 (RLS theo pháp nhân từ phiên đã xác minh; MTQ là nguồn duy nhất quyết định hành động/hạn mức/phạm vi; không dùng `ktt_duoc(pn,'M1')` làm bộ lọc tổng; đối tượng nhiều pháp nhân phải đạt quyền ở mọi pháp nhân — QD-20261026-10);
- Đặc tả CSDL §5;
- **Nâng (không viết lại)** MTQ hiện có: `src\kho_tri_thuc\k2\sql_mtq_cong.py` (định nghĩa cuối: cổng `mtq_quyet_dinh_phien`, `mtq_ghi_tu_choi_phien`, resolver tập M0057, `mtq_duoc_doc` M0058…), `k2\ma_tran_tham_quyen.py`, `k2\sql_ma_tran_tham_quyen.py`. Chỉ lấy định nghĩa cuối, đổi schema / owner / danh tính sang phiên xác minh.

**Việc:**
1. **Bảng / hàm MTQ trong `loi`** (tên đúng bảng tên chuẩn).
   - Quyết định hành động nhận **mã phiên** (bind), gọi `loi.xac_minh_phien`, không tin GUC / `current_user`.
   - Resolver nghiệp vụ gọi **động** qua `loi.dang_ky_ham_module`; thiếu → `CHO`.
   - Không SQL bảng riêng module trong Core.
2. **RLS cho bảng danh tính G2-02** (`nguoi_dung`, `phap_nhan`, `phan_quyen`): thay policy runtime `false` bằng policy **theo phiên xác minh**.
   - Người chỉ thấy pháp nhân mình thuộc; ghi chỉ qua hàm Core có kiểm MTQ.
   - FORCE RLS, USING / WITH CHECK; không cho đổi `phap_nhan_id` để chuyển hồ sơ.
   - **Đây cũng là phần G2-02b bị chặn** — gộp vào lát này.
3. **Ghi từ chối** vào audit G2-04; thông điệp tiếng Việt, không lộ khóa.

**Test PG** (dưới login thật + phiên G2-03):
- đúng pháp nhân thấy / sai pháp nhân bị chặn;
- giả GUC không có tác dụng;
- đối tượng hai pháp nhân thiếu quyền một bên → từ chối;
- hỗn hợp bật / tắt MTQ → từ chối;
- thiếu resolver → `CHO`;
- `vai_chay_loi` không SELECT thẳng bảng MTQ nội bộ.
- **Bật ca nghiệp vụ G2-02 còn skip:** được sửa `tests\test_g2_02.py`? **Không** (ngoài whitelist) — viết ca tương đương trong `tests\test_g2_06.py`.
