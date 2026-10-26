# MTQ-4a3b vòng 2: kiểm quyền nhan_ket_qua_6 trong CÙNG giao dịch ghi (Chặn)

Bạn là worker Codex, chạy không tương tác. Làm ngay. Ghi UTF-8 không BOM. Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Worktree hiện tại, nhánh `lat/mtq-4a3b` (HEAD a3a635a). Gặp chỗ chưa rõ: **dừng và ghi "Cần lead"**, không đoán.

**Đọc:** `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-mtq-4a3b.md` (đã lead lọc) và giao việc gốc `giao-mtq-4a3b.md`.

**Việc (chỉ điểm Chặn):** `k2/crm.py` `nhan_ket_qua_6` (khoảng dòng 240–255): lời gọi `quyen.kiem_tham_quyen(... "CRM:TIEP_NHAN:LAP" ...)` phải chạy **bên trong** giao dịch ghi (`with self._tx(dt):` đang mở ở ~:252), trước mọi INSERT/UPDATE, để khóa của cổng (advisory shared, dòng kích hoạt/gán vai) giữ tới commit — không commit một giao dịch kiểm riêng rồi mới mở giao dịch ghi. Nhánh CU vẫn gọi `quyen.kiem(dt, "NOP_HOP_DONG", pn)` cùng vị trí tương đối (trước side effect). Rà luôn các điểm khác của lát: nếu điểm nào cũng "kiểm ở giao dịch riêng rồi ghi ở giao dịch khác" thì sửa cùng cách; riêng `trich_tu_docx` giữ kiểm trước engine (ngoài giao dịch) vì `nhan_ket_qua_6` sẽ kiểm lại trong giao dịch ghi. Không đổi gì khác.

**Test** (`tests/test_mtq_crm.py`): ca chứng minh kiểm và ghi cùng một giao dịch (ví dụ mock đếm `_tx`/ghi thứ tự gọi, hoặc PG: thu hồi gán vai giữa chừng không lọt). Ca cũ vẫn đạt. **Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_crm`. **Tệp (2):** `k2/crm.py`, `tests/test_mtq_crm.py`. Báo cáo ≤ 5 dòng, thông điệp `[MTQ-4a3b] vòng 2: …`.
