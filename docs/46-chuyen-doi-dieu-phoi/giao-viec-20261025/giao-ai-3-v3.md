# AI-3 vòng 3 — sửa 3 điểm "Nên sửa" của review (trước khi gộp)

Bạn là worker Codex, chạy không tương tác. Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\review-ai-3.md` (mục Nên sửa 1–4) và handoff `giao-ai-3.md`, `giao-ai-3-v2.md`. **Làm ngay, không hỏi lại.** UTF-8 không BOM. Worktree hiện tại, nhánh `lat/ai-3`. Sandbox không ghi `.git`: **không commit**. Không gọi mạng thật, không mở server/PostgreSQL.

**Việc:** (1) `cloud.tao_cong_ai()`: chỉ đưa vào cổng `settings.get("cong_ai") or {}` và `settings.get("local_ai") or {}` theo đúng cách `cong_ai_settings` nhận (đọc `cong_ai.py`), không đưa nguyên cấu hình engine; thêm test với cấu hình engine **không có** khóa `cong_ai` → model Cloud của cổng không bị lấy tên model Local. (2) `test_may_cloud_da_ghim_goi_duoc_cong_o_ngoai_review`: thêm đúng điều kiện skip như test lân cận khi thiếu 2 tệp gitignore của lõi Review. (3) `kiem_tra_cloud`: một nhóm gặp lỗi cổng (`AILoi`, Mask còn sót, Cloud trả không hợp lệ) → bỏ **riêng nhóm đó** (ghi vào `khong_gui` với lý do tiếng Việt), **tiếp tục** các nhóm sau; dòng tổng kết đếm đúng số không gửi; `so_khong_gui` chỉ tăng khi thật sự không gửi. Thêm test 2 nhóm: nhóm 1 lỗi, nhóm 2 vẫn được hỏi. (4) Báo cáo ghi rõ các giới hạn ở mục 4 của review.
Sau khi sửa `ai_cloud.py`/`cloud.py` → **cập nhật lại 2 băm `PIN`** trong `src/kho_tri_thuc/m4/nguon_review.py` (byte trên đĩa, như vòng 2).
**File:** `ai_cloud.py`, `cloud.py`, `nguon_review.py` (2 dòng PIN), `tests/test_ai0_khoa_cloud.py`. Không xóa file.
**Chạy test:** `python -X utf8 -m unittest tests.test_ai0_khoa_cloud tests.test_cong_ai` + test lõi Review thuần đã chạy ở vòng 2 — ghi số.
**Báo cáo (≤ ⅓ trang):** sửa ở file:dòng · số test · thông điệp commit `[AI-3] vòng 3: …`.
