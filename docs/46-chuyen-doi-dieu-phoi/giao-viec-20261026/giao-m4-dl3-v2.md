# M4-DL3 vòng 2: lớp đọc phụ lục/BOQ theo phương án (a) (tự kiểm quyền, 3 trạng thái NULL) + nên sửa của DL2

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở PostgreSQL. Không xóa file.
- **Không đọc dữ liệu Review thật.**
- Làm trong worktree hiện tại, nhánh `lat/m4-dl3`. Nhánh đã nhận hợp nhất, trong đó có **DL2 vòng 2** đã gộp: `m4/review_data_pg.py` với `doc_hien_hanh(hop_dong_id, *, conn_phien)`, kiểm quyền XEM/REVIEW qua `master.m4_duoc`, 3 trạng thái `CHUA_CO_LAN_CHUP` / `CHUA_CO_TRONG_NGUON` / `DA_XOA_O_NGUON`.

**1. `m4/review_phu_luc_pg.py`, hàm đọc `doc_hien_hanh` (khoảng dòng 275):**
- Làm **đúng như DL2**:
  - bắt buộc `conn_phien`;
  - kiểm quyền trên kết nối phiên **trước** mọi lần đọc bằng kết nối chủ bảng;
  - dự án lấy từ `master.hop_dong.du_an_id` (không từ tham số);
  - không quyền → 404 giống hệt UUID ngẫu nhiên;
  - 3 trạng thái NULL.
- **Dùng lại** hàm hoặc khối kiểm của DL2 nếu đã tách được; tránh chép lại logic.

**2. Nên sửa của review DL2, sửa trong `m4/review_data_pg.py`, phạm vi nhỏ, không đổi chữ ký hàm ghi:**
- Gộp `review_chep_hien_hanh` và 2 câu `EXISTS` vào **một câu SELECT** (khoảng dòng 301–306), để trạng thái NULL không sai thoáng qua dưới READ COMMITTED.
- `hop_dong_id` không phải UUID → kiểm `uuid.UUID(str(...))` trước; sai thì trả 404, không để lỗi CSDL thô làm hỏng giao dịch phiên.
- Mã lỗi theo quy ước `M4_REVIEW_KHONG_THAY` (ánh xạ HTTP 404) thay cho chuỗi `"404"`, theo mẫu `m4/ke_toan_nghiem_thu.py` khoảng dòng 79.
- Docstring ghi rõ khe hở giữa kiểm quyền (kết nối phiên) và đọc (kết nối chủ bảng) là chấp nhận được, và lý do.

**Test:**
- `tests/test_m4_review_phu_luc_pg.py`: 3 trạng thái NULL; không quyền → 404, không gọi đọc chủ bảng; UUID sai → 404.
- Cập nhật `tests/test_m4_review_data_pg.py` theo mã lỗi mới, UUID sai và câu SELECT gộp.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_review_phu_luc_pg tests.test_m4_review_data_pg`, với PYTHONPATH=`src;.;tests`.

**Tệp (≤ 4):** `m4/review_phu_luc_pg.py`, `m4/review_data_pg.py`, 2 test.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M4-DL3] vòng 2: …`.
