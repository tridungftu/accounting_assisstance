# L0-10b — `pg_cum`: bằng chứng trái chiều thắng; không tự `pg_ctl start` khi đã có dịch vụ (theo review-lat L0-10)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM. Worktree hiện tại, nhánh `lat/l0-10b` (từ hop-nhat, đã có L0-10). Sandbox không ghi `.git`: **không commit**. **Không gọi pg_ctl/sc/PowerShell thật, không nối CSDL** — test bằng `HeDieuHanh` giả.

**Việc (`src/kho_tri_thuc/ha_tang/pg_cum.py`):**
1. (~:257) Nhánh dịch vụ chỉ được dùng khi **không có bằng chứng trái chiều**: đọc được `exe` → bắt buộc bằng `cum.postgres`; đọc được `cmd` → `-D` bắt buộc trỏ đúng data. Trái chiều → `CUM_KHONG_XAC_MINH`. Thêm ca âm "exe khác, cmd rỗng" và "cmd -D khác".
2. (~:291-298) Khi `pg_ctl status` = 3 và cổng trống: nếu có dịch vụ Windows trỏ đúng `pg_ctl runservice -D <data>` với trạng thái **khác Stopped** (Running/Start Pending/…) → **không** chạy `pg_ctl start`, báo lỗi rõ tiếng Việt (mã mới, ví dụ `CUM_DICH_VU_DANG_LEN`: "Dịch vụ PostgreSQL DEMO đang khởi động — chờ rồi thử lại"); dịch vụ **Stopped** → báo lỗi rõ `CUM_DICH_VU_DUNG` ("Dịch vụ PostgreSQL DEMO đang dừng — bật dịch vụ ktt-postgres-demo"), **không** tự khởi động dịch vụ hay cụm tay. Không có dịch vụ nào trỏ đúng data → giữ hành vi cũ (start tay).
3. (~:145 `dich_vu_pg`) Tìm **dòng JSON** trong đầu ra thay vì lấy dòng cuối (PowerShell có thể ghi tiến độ ra stderr gộp chung).
4. Test trong `tests/test_crm_khoi_dong.py` cho 1–3; hành vi cũ khi cụm chạy tay giữ nguyên.

**File được sửa (chỉ 2):** `src/kho_tri_thuc/ha_tang/pg_cum.py`, `tests/test_crm_khoi_dong.py`. Không xóa file.
**Test:** `--module test_crm_khoi_dong`; sandbox chặn python → "lead chạy test".
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · mã lỗi mới · ca test · thông điệp commit `[L0-10b] …`.
