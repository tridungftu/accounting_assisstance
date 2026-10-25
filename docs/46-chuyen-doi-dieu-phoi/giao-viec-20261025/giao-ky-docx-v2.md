# KY-DOCX vòng 2 — sửa 1 ca test PostgreSQL lệch trạng thái (k10)

Bạn là worker Codex, chạy không tương tác. Lead chạy PostgreSQL cho KY-DOCX (`docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\bao-cao-ky-docx.md`): mọi ca đạt trừ `tests/test_crm_ky_ket_http.py::CrmKyKetHttp.test_k10_g5_ban_sinh_chi_docx_can_kiem_tay` — `AssertionError: 'CHO_CAU_HINH' != 'CHO'`. **Làm ngay, không hỏi lại.** UTF-8 không BOM. Worktree hiện tại, nhánh `lat/t-pdf`. Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL.

Việc: đọc M0035 trong `src/kho_tri_thuc/ha_tang/pg_migrations.py` (phần `crm_g5_hang_doi`/`crm_g5_nhan` — KY-DOCX ghi việc G5 bản sinh chỉ DOCX ở trạng thái **chờ cấu hình** với lý do `G5_BAN_SINH_CHI_DOCX`) và các giá trị trạng thái việc G5 có sẵn (CHECK/enum trong migration cũ). Nếu `CHO_CAU_HINH` là trạng thái hợp lệ có sẵn và đúng ý thiết kế ("không giao worker, việc vẫn mở chờ cấu hình") → sửa **test** k10 kỳ vọng `CHO_CAU_HINH` (giữ mọi kiểm khác: lý do, không ý định/kết quả). Nếu không phải (trạng thái mới tự đặt, không có trong CHECK cũ) → **dừng**, báo lead tệp:dòng, không sửa migration.
**File (≤ 1):** `tests/test_crm_ky_ket_http.py`. Không xóa file.
**Báo cáo (≤ 8 dòng):** căn cứ trạng thái (tệp:dòng) · sửa ở dòng nào · thông điệp commit `[KY-DOCX] vòng 2: …`.
