# G2 · giao G2-08 — nâng công tắc module theo pháp nhân và người thử

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `hop-nhat-20261023` (đã gộp G2-00…G2-06, G2-17, G2-24). Dùng lại vai / phiên / audit / registry / MTQ của các lát trước; quy ước như cũ.

## Lát G2-08

**Tệp:** `src\kho_tri_thuc\core\sql\008_cong_tac.sql`; `src\kho_tri_thuc\core\cong_tac.py`; `tests\test_g2_08.py`.

**Căn cứ:**
- Kế hoạch G2-08: `TAT` / `THU` / `VAN_HANH`, CAS / audit; `THU` không xuất chính thức; `TAT` giữ lịch sử, không tự bật.
- Chuẩn API (`/quan-tri/module/{ma}/che-do`).
- **Nâng (không viết lại)** công tắc hiện có M0056: `src\kho_tri_thuc\k2\sql_module.py` (định nghĩa cuối), `k2\module.py` (`kiem_module`, `trang_thai_cho`). Đổi danh tính sang phiên xác minh (G2-03), quyền đổi chế độ qua MTQ (G2-06), audit (G2-04), module tham chiếu registry (G2-05).

**Việc:**
- Bảng chế độ module theo pháp nhân + danh sách người thử.
- Đổi chế độ chỉ qua hàm Core có `row_version` / CAS; ghi audit.
- `TAT` giữ dữ liệu / lịch sử; không tự bật lại; chỉ Admin.
- Hàm đọc chế độ cho Core và module.
- Thêm dòng, không sửa đè / xóa lịch sử (QD-09).

**Test PG** (login thật + phiên):
- đổi chế độ đúng quyền / sai quyền bị chặn;
- CAS lệch → lỗi;
- `THU` chỉ người thử dùng được;
- `TAT` giữ lịch sử;
- audit có dòng;
- runtime không ghi thẳng bảng.
