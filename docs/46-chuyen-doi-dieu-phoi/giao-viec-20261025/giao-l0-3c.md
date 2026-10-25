# L0-3c — Cập nhật test lỗi thời (nhóm N5) sau hợp nhất

Bạn là worker Codex, chạy không tương tác. Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`, `docs/46-chuyen-doi-dieu-phoi/NEN-TEST.md` (mục 0b và nhóm N5). UTF-8 không BOM.
**Thư mục:** worktree hiện tại, nhánh `lat/l0-3c` (từ `hop-nhat-20261023` c4deb00 — 27 migration PostgreSQL). Sandbox không ghi `.git`: **không commit**. Nếu sandbox không cho chạy Python, ghi rõ (lead chạy test).

**Bối cảnh:** sau khi gộp nhiều gói, một số test còn mã hóa trạng thái CŨ của một thời điểm (đếm cứng số migration, khẳng định "chưa đăng ký", kết nối giả thiếu hàm mới). Chúng đỏ dù code đúng. Việc của bạn là cập nhật các test đó cho đúng trạng thái hiện tại **mà không làm yếu đi điều test bảo vệ**.

**Danh sách (lấy `ids_loi` và `loi_dau` trong `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v2.json` + chạy lại để xác nhận):**
- Đếm cứng số migration: `test_m0_m5_migrations` (25 ≠ 14), `test_m4_02c_tinh` (27 ≠ 24), `test_crm_41_02`, `test_crm_giao_ket`, `test_crm_ky_ket`, `test_l11_migrations`, `test_m2_migrations`, `test_m4_02b_pure`, `test_m4_review_compute` (các assert "N ≠ 14/15/16/18/20/…").
- Khẳng định trạng thái cũ: `test_m4_03a_tinh` ("`sql_ke_toan_nghiem_thu` unexpectedly found" — nay M0026 đã đăng ký đúng), `test_m4_01c` ("`/api/m4/ke-toan` unexpectedly found" — route do gói M4-03A thêm sau).
- Kết nối giả thiếu hàm: `test_crm_khoi_dong` (`_KetNoiGia` không có `transaction`).
- Kiểm "chỉ append, byte đầu giữ nguyên" (`PrefixMigration…`, các test băm prefix `pg_migrations.py`): **đọc kỹ** — nếu chỉ lệch vì đoạn sau mốc được nối thêm thì cập nhật cách cắt prefix cho đúng ý "migration 1…N không đổi byte"; nếu thật sự byte của một migration cũ đã đổi → **KHÔNG sửa test**, ghi vào báo cáo mục "nghi lỗi thật" (lead điều tra).

**Quy tắc sửa:**
- Đếm migration: thay số cứng bằng kiểm có ý nghĩa — ví dụ migration của gói đó nằm đúng vị trí số của nó (`PG_MIGRATIONS[k-1] is M00kk_...`), và `len(PG_MIGRATIONS) >= k`; không xóa assert, không đổi thành `assertTrue(True)`.
- Trạng thái cũ: đổi kỳ vọng sang trạng thái mới VÀ thêm kiểm điều kiện mới (ví dụ M0026 đăng ký đúng một lần, đúng object `M4_03A_SQL`); ghi chú 1 dòng trong test nêu gói làm thay đổi.
- Kết nối giả: bổ sung đúng hàm mà code thật gọi (theo giao diện kết nối thật trong `ha_tang/`), không đổi code sản phẩm.
- **Chỉ sửa file trong `tests/`** (tối đa ~10 file). Không sửa `src/`. Test nào bạn thấy đỏ vì lỗi sản phẩm thật → không sửa, ghi báo cáo.

**Test phải đạt:** chạy từng module đã sửa: `python -X utf8 tools/chay_test_theo_module.py . --module <tên>` — mã lỗi N5 nêu trên hết; không module nào khác có mã lỗi mới.
**Báo cáo cuối (≤ 1 trang, tiếng Việt):** bảng module · lỗi cũ · cách sửa (1 dòng) · kết quả sau · danh sách "nghi lỗi thật" (nếu có) · thông điệp commit `[L0-3c] …`.
