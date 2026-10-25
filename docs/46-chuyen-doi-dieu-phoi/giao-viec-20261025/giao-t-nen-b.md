# T-NEN-b — Test E1/M1 va với hook "không xóa" (CODEX_NO_DELETE_FILES) khi chạy dưới runtime DEMO

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2: không xóa file). UTF-8 không BOM. Worktree hiện tại (từ hop-nhat `f62c36a`, nền PG v2 — `docs/46-chuyen-doi-dieu-phoi/NEN-TEST-PG.md` mục cuối, `nen-test-hop-nhat-pg-v2.json`). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không khởi động PostgreSQL — lead chạy PG. **Chỉ sửa test**, không sửa mã sản phẩm; không nới assert để đạt giả.

**Bối cảnh:** từ L0-8e, test chạy dưới runtime DEMO có hook bảo vệ "không xóa" (giống server DEMO thật; quy tắc Anh "không xóa file"). Ba test đang dựa vào việc **xóa** tệp/thư mục:
- `tests/test_e1_mua_danh_muc_sua.py` (4 FAIL) và `tests/test_e1_mua_trich_phien_ban.py` (1 FAIL): "Lists differ: [WindowsPath('…tmp')] != []" — test chờ thư mục tạm bị dọn.
- `tests/test_m1.py::WorkspaceTests::test_backup_does_not_succeed_without_referenced_raw`: "OSError not raised" — test xóa tệp raw để giả "thiếu raw".
**Việc:** sửa test để **không cần xóa** mà vẫn kiểm đúng ý: (a) giả "thiếu raw" bằng đường dẫn không tồn tại / tham chiếu sai thay vì xóa tệp; (b) kiểm dọn thư mục tạm: khi guard bật (`CODEX_NO_DELETE_FILES=1`) thì kỳ vọng thư mục tạm **được giữ lại đúng chỗ** (trong thư mục lần chạy/retained-temp) và mã sản phẩm đã gọi bước dọn (mock/đếm lời gọi), khi guard tắt thì kỳ vọng như cũ. Không sửa mã sản phẩm; mã sản phẩm có xóa tệp thật → ghi vào báo cáo cho lead (không sửa).
**File (≤ 3, đều là test):** ba tệp trên.
**Báo cáo (≤ ⅓ trang):** sửa ở file:dòng · cách kiểm mới · mã sản phẩm có xóa tệp (nếu thấy) · thông điệp commit `[T-NEN-b] …`.
