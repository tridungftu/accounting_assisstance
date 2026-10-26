# MTQ-4a2: Ma trận thẩm quyền, nối các điểm CRM luồng B/M1 còn lại vào adapter + 3 điểm nên sửa của review MTQ-4a. Rủi ro cao.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì **chặn** và ghi "Cần Anh".
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL; test PG tự tạo CSDL `kho_test_*`, không đọc `KHO_PG_DEMO_*`. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-4a2`, dựng từ hợp nhất. Đã có MTQ-4a: adapter `kiem_tham_quyen` trong `k2/quyen.py`; 3 điểm `duyet`, `duyet_v4`, `tu_choi` trong `k2/crm.py` đã nối; M0041/M0043 cổng SQL.

**Căn cứ:**
- Thiết kế `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md` §4.2 (danh sách điểm CRM luồng B, M1), §5.1, §5.2.
- Giao việc `giao-viec-20261026/giao-mtq-4a-v2.md`.
- Cách MTQ-4a nối 3 điểm: `git show 6a8b253`.

**Việc:**
1. Nối các điểm còn lại theo **đúng mẫu** 3 điểm đã nối:
   - `trich_tu_docx` / `nhan_ket_qua_6` (NOP_HOP_DONG);
   - `bo_sung_ho_so`;
   - `_trich_lai`;
   - `cap_nhat_mapping`;
   - `xac_nhan_tham_so` / `kiem_truoc`;
   - `kiem_nhan_tien`;
   - `lien_ket` / `go_lien_ket`;
   - `xuat_file_soat` / `tep_file_soat`.

   Yêu cầu chung cho mọi điểm:
   - Nhánh CU gọi đúng `quyen.kiem(...)` cũ, kết quả **không đổi một bit**.
   - Đối tượng `{bang,id}` dựng từ đối tượng thật đã đọc qua RLS.
   - Hành động nào **không mang tiền** thì khai `KHONG_AP_DUNG` theo catalog, không đòi tiền.

   Nếu một điểm cần thêm resolver hoặc thêm tệp ngoài 3 tệp, **không làm** điểm đó; ghi vào báo cáo.
2. Nên sửa của review MTQ-4a:
   - `crm.py:83`: log sự cố thêm `exc_info=True`, chỉ vào log máy chủ, không trả client.
   - `quyen.py:146`: `can_tien` suy từ `loai_tien` của catalog thay vì ghim 2 lệnh.
   - `quyen.py:208`: bắt `DataError` riêng trong bộ lấy tiền, giữ mã gốc ("không thấy HĐ/phiên bản"), không đổi thành "thiếu căn cứ tiền".
3. Không bật ma trận; không sửa SQL hay migration.

**Test `tests/test_mtq_crm.py`:**
- Hồi quy CU cho **từng** điểm mới: so với oracle `quyen.kiem` thật, nhiều vai.
- Nhánh bật: không fallback.
- Hành động không mang tiền không đòi tiền.
- `DataError` giữ mã gốc.
- Báo số test CRM trước/sau (`tests/test_crm*.py`), không được giảm.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_crm` và các test CRM liên quan (PYTHONPATH=`src;.;tests`).

**Tệp (3):** `k2/quyen.py`, `k2/crm.py`, `tests/test_mtq_crm.py`.

**Báo cáo (≤ ⅓ trang):** điểm đã nối và điểm bỏ (kèm lý do), số test, "Cần Anh", thông điệp commit `[MTQ-4a2] …`.
