# KY-G5TAY vòng 2 — sửa 2 lỗi PostgreSQL lead chạy + Nên sửa của review

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.** UTF-8 không BOM — ghi tệp bằng UTF-8. Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL (lead chạy PG). Không xóa file. Worktree hiện tại, nhánh `lat/ky-g5tay` (commit 3927ae5). Đọc handoff `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\giao-ky-g5tay.md`, báo cáo `bao-cao-ky-g5tay.md`.

**Lỗi PostgreSQL lead chạy (26/10 10:20):**
1. `tests/test_crm_g5_tay.py`: `AssertionError: 400 != 200 : ('MO_PHONG_CRM_G_KT_A', 'giao-ket/kiem/luu', {'error': 'CSDL_TU_CHOI', …})` — sau khi kế toán **xác nhận kiểm tay G5**, lệnh lưu bước kế toán kiểm G6 (`giao-ket/kiem/luu`) bị CSDL từ chối → hợp đồng **chưa** sang Hiệu lực được (trái CD-010 mục 1). Tìm hàm SQL G6 lưu kiểm (`crm_kiem_*` trong M0025/M0032/M0036 — `k2/sql_crm_kiem_hd.py`, `sql_crm_doi_chieu.py`) đang đòi gì từ G5 (vd đòi `crm_g5_ket_qua` hiện hành / `ket_qua_id` trỏ bảng E5 / trạng thái việc G5) và sửa trong **M0037** (tạo lại định nghĩa hiện hành bằng thay chuỗi đúng một vị trí như M0036 đã làm, không chép tay thân hàm, không sửa migration cũ) để G6 chấp nhận **kết quả kiểm tay hợp lệ** (`crm_g5_kiem_tay` đúng `ky_id`/revision/hash) như KHOP. Không nới E5.
2. `tests/test_crm_ky_docx.py` (ca so **thân hàm đã triển khai** với định nghĩa M0036): nay M0037 định nghĩa lại `crm_kiem_g5_xet` (và có thể hàm G6) → sửa ca này so với **định nghĩa hiện hành** (định nghĩa cuối cùng trong chuỗi migration cho từng hàm), không ghim cứng M0036.

**Nên sửa của review-lat:**
- N1: `master.crm_g5_kiem_tay` thêm `ALTER TABLE … ENABLE ROW LEVEL SECURITY` (như bảng G5/G6A/bản ký); test thuần đổi `assertNotIn("ALTER TABLE", sql)` thành kiểm **không ALTER bảng E5 / `crm_hd_ky`**; test PG khẳng định `relrowsecurity`.
- N2: `test_m0037_cuoi_va_khong_sua_m0036` không đòi `PG_SCHEMA_VERSION == 37` và M0037 là phần tử **cuối** → khẳng định theo **vị trí 37** (`PG_MIGRATIONS[36]`) như `tests/test_crm_ky_ket.py` đang làm (vì MTQ-1/M4-DL1 sẽ nối thêm migration).
- D2: SQL kiểm lý do chặn ký tự điều khiển như `_KIEM_LY_DO` cũ (`[[:cntrl:]]` trừ xuống dòng/tab nếu mẫu cũ cho phép); Python chặn DEL và C1.

**File:** `k2/sql_crm_g5_tay.py`, `ha_tang/pg_migrations.py` (chỉ khối M0037), `k2/crm_ky_ket.py` (chỉ nếu cần), `tests/test_crm_g5_tay.py`, `tests/test_crm_ky_docx.py`.
**Chạy (thuần):** `python -X utf8 -m unittest tests.test_crm_g5_tay tests.test_crm_ky_ket tests.test_crm_ky_docx` (PYTHONPATH=`src;.;tests`). **Báo cáo (≤ ⅓ trang):** nguyên nhân 400 (tệp:dòng), cách sửa, số test, thông điệp commit `[KY-G5TAY] vòng 2: …`.
