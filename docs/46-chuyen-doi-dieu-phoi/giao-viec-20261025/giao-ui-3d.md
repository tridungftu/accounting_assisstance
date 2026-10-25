# UI-3d — Trang chủ hệ thống DEMO: cấp phiên kèm cookie khi chưa có (review lô 7 lát, Nên sửa 1)

Bạn là worker Codex, chạy không tương tác. Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\review-lo-7-lat.md` (Nên sửa 1, Để sau 7). **Làm ngay, không hỏi lại.** UTF-8 không BOM. Worktree hiện tại, nhánh `lat/ui-3d` (`lat/ui-dem`). Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL.
Việc — `src/kho_tri_thuc/giao_dien/khung_khai_bao.py` (route `/api/khung/he-thong`, UI-3c): khi **không phải kho thật** và chưa có phiên CRM hợp lệ trong cookie → **cấp phiên như `app.crm_phien` đang cấp** và trả kèm `Set-Cookie` trên chính phản hồi 200 (đúng tên/thuộc tính cookie mà `/api/crm` đang đặt — đọc `server.py`), để trang chủ lần đầu có đủ module theo quyền; **kho thật** (THAT_UI/CRM chưa cấu hình) → giữ hành vi UI-3c (không tạo phiên, CRM không số). Không tạo phiên mới khi cookie đã có phiên hợp lệ (làm mới 60 giây không sinh phiên).
**Test — `tests/test_khung_he_thong.py`:** (a) chưa có cookie, không phải kho thật → 200 + `Set-Cookie`, module theo quyền đầy đủ (M2/M4/M5/L11 theo seed); (b) gọi lại với cookie đó → không cấp phiên mới; (c) kho thật → không `Set-Cookie`, không tạo phiên; ca cũ đạt.
**File (≤ 2):** `khung_khai_bao.py`, `tests/test_khung_he_thong.py`. Không xóa file.
**Chạy test:** `python -X utf8 -m unittest tests.test_khung_he_thong tests.test_khung_luoi_crm` (PYTHONPATH=`src;.;tests`) — ghi số.
**Báo cáo (≤ ¼ trang):** sửa ở file:dòng · số test · thông điệp commit `[UI-3d] …`.
