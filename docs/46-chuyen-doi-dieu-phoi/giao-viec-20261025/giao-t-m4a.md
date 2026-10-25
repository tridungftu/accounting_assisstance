# T-M4a — sửa test M4 lỗi thời lộ ra khi lõi nguồn đã nạp (M4 · Nghiệm thu & chi phí dự án)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/t-m4a` (từ hop-nhat). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không khởi động PostgreSQL/server — **lead chạy test PostgreSQL**. Chỉ sửa **test**, không sửa mã sản phẩm.

**Bối cảnh (lead đã chạy có PostgreSQL 25/10, nhánh tích hợp):** so với nền PG (`8ff21a2`), 4 bộ ca nay hỏng vì giả định cũ của test, không phải lỗi sản phẩm:
1. `tests/test_m4_01b_pg.py::test_t04_luong_day_du_va_replay` và `tests/test_m4_01c_http.py::test_h05_track_changes`, `test_h06_luong_day_du_den_nop_va_reviewer`: trước đây bị skip vì `_nguon_da_nap()` = sai; nay lõi nguồn `m4/review_goc` đã nạp đúng ghim nên ca chạy thật, nhưng test dựng `XayDungK2(...)` **không tiêm engine trích dùng chung #6** (`trich6`), trong khi từ CRM-41-01 `trich` bắt buộc có engine (`k2/xay_dung.py:451` → `M4_TRICH6_CHUA_SAN_SANG`, HTTP 503).
2. `tests/test_m4_review_k2.py::test_r00_nang_19_len_20`, `test_r01_dung_ho_so`: còn ghim "chuỗi migration = 20" (`:189`, `:294`) trong khi chuỗi nay là 32 (sẽ còn tăng).

**Việc:**
1. Ca trích M4: tiêm một client engine #6 **giả trong tiến trình** cho `XayDungK2(..., trich6=...)` (mẫu: `_Trich6Goc` ở `tests/test_crm_doi_chieu_tinh.py:458`; giao diện client ở `src/kho_tri_thuc/nguon/trich_chung_6.py`, cách máy chủ tiêm ở `giao_dien/m4.py:322`) sao cho luồng trích/replay/track changes của 3 ca chạy đúng như ý định ban đầu. Không làm được gọn trong phạm vi file dưới → để ca **skip có lý do** "chưa có engine #6 cho test — NOT_RUN, không tính đạt" và ghi rõ trong báo cáo (không được biến thành "đạt" giả).
2. `test_m4_review_k2`: R00 kiểm nâng **19 → 20** (dùng đúng cách migrate tới một mốc nếu `ha_tang/pg_migrations.py` có; không có thì kiểm bản ghi M20 đã áp và lịch sử 1–19 giữ nguyên, không ghim tổng); R01 kiểm "DB mới có đủ 1–20 và M20 là bản hàm hiện hành", **không** so bằng tổng số migration.

**File được sửa (chỉ 3):** `tests/test_m4_01b_pg.py`, `tests/test_m4_01c_http.py`, `tests/test_m4_review_k2.py`. Không xóa file.
**Test:** chạy thuần được thì chạy (`--module test_m4_01b_pg --module test_m4_01c_http --module test_m4_review_k2` — không có PostgreSQL các ca sẽ skip); ca PG lead chạy.
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · ca nào chạy thật / ca nào skip có lý do · thông điệp commit `[T-M4a] …`.
