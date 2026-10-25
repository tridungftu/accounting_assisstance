# L0-8f vòng 2 — gắn đối tác DEMO trước khi nộp hồ sơ test 03B (mở rộng phạm vi theo chẩn đoán vòng 1)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Cùng quy tắc như `giao-l0-8f.md` (UTF-8 không BOM; không commit; không nối CSDL — lead chạy PG). Worktree hiện tại, nhánh `lat/l0-8f`.

**Lead quyết theo chẩn đoán vòng 1 của bạn:** gốc lỗi c01 là **helper test** `tests/test_m4_02c_pg.py:~166` tạo HĐ theo `run_id` mà không gắn đối tác trước khi nộp (luồng thật có bước gắn đối tác — `sql_master_dung_chung.py:~470` chặn sau khi nộp); không phải lỗi sản phẩm.

**Việc:**
1. `tests/test_m4_02c_pg.py`: helper tạo/nộp hồ sơ nhận tham số **tùy chọn** (ví dụ `gan_doi_tac: str | None = None`, mặc định None → hành vi cũ y nguyên cho mọi module đang dùng); khi có giá trị → gọi đường chính thức `gan_doi_tac_hop_dong` bằng actor DEMO **trước khi nộp**.
2. `tests/test_m4_03b_common_pg.py`: `ho_so_seal(...)` truyền tham số đó với đối tác DEMO của bản sao (đọc từ biến môi trường mới do họ 03a cấp, ví dụ `KHO_M4_03B_DOI_TAC`); thiếu biến → skip `NOT_VERIFIED` như hiện nay (không đạt giả).
3. `tools/pg_demo_ho_03a.py`: seed đối tác DEMO có MST `DEMO_M2_SUPPLIER` (bên bán hóa đơn fixture G01) + ánh xạ hiện hành thuộc `PN_DEMO_A` bằng đường chính thức; cấp biến `KHO_M4_03B_DOI_TAC` cho module 03B (khai trong danh sách biến họ 03a của `tools/chay_test_theo_module.py` nếu danh sách nằm ở đó — khi đó được sửa thêm đúng chỗ khai biến).

**File được sửa (≤ 4):** `tests/test_m4_02c_pg.py`, `tests/test_m4_03b_common_pg.py`, `tools/pg_demo_ho_03a.py`, và chỉ chỗ khai biến trong `tools/chay_test_theo_module.py` nếu cần. Không sửa mã sản phẩm, không xóa file. Các module khác dùng helper (02c, 03a…) **không đổi hành vi**.
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · biến mới · ca dự kiến chạy/skip · thông điệp commit `[L0-8f] …`.
