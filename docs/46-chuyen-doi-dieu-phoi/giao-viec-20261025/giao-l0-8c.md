# L0-8c — GẤP: bộ chạy test không cưỡng được giới hạn 180 giây/module (treo 4.588 giây) + 2 điểm review

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2: không khởi động PostgreSQL/server DEMO; không nối CSDL). UTF-8 không BOM — **ghi tệp bằng UTF-8** (không dùng `Set-Content`/`Out-File` mặc định; chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/l0-8c` (từ hop-nhat, đã có L0-8 vòng 2). Sandbox không ghi `.git`: **không commit**. Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"`.

**Sự cố thật (lead chạy 25/10):** `tools/chay_test_theo_module.py --pg-demo … --module "test_crm_*"`: module `test_crm_k2` ghi `TREO … 4588.8s` dù giới hạn 180 giây; cả lần chạy 5.742 giây. Nguyên nhân khả dĩ (review Claude vòng 2, điểm Nên sửa #2, R:862-868): vòng 2 chuyển sang `stdout=PIPE` + `communicate()`; khi quá hạn, tiến trình con bị giết nhưng **tiến trình cháu còn giữ ống** → `communicate()` chờ EOF mãi.
**Điểm review #1 (R:394-401, 682) + quan sát thật:** `.pth` gọi `__import__('tools.chay_test_theo_module')._bat_bao_ve_pth` — khi chạy bộ chạy của worktree này trên **worktree khác** (cũ), tên module trỏ vào bản cũ → `AttributeError … no attribute '_bat_bao_ve_pth'`, Python in lỗi rồi chạy tiếp → bảo vệ sổ CSDL tạm bị hở (tiến trình cháu CREATE không vào sổ).

**Việc:**
1. **Cưỡng hạn chắc chắn:** đọc stdout/stderr tiến trình con bằng **luồng riêng** ghi vào nhật ký đã lọc bí mật; chờ bằng `wait(timeout=180)`; quá hạn → giết **cả cây tiến trình** (Windows: `taskkill /T /F /PID <pid>` của đúng tiến trình con do bộ chạy tạo, hoặc Job Object), đóng ống, đợi luồng đọc tối đa vài giây rồi bỏ; ghi TREO với thời gian ≈ hạn. Không bao giờ chờ EOF vô hạn.
2. **`.pth` không phụ thuộc tên module:** nạp hàm bảo vệ theo **đường dẫn tệp tuyệt đối** của chính bộ chạy (vd `importlib.util.spec_from_file_location`) hoặc ghi một tệp trợ giúp nhỏ riêng trong thư mục nhật ký; mọi lỗi khi nạp → `os._exit(2)` (fail-closed, test con không chạy tiếp mà không có bảo vệ).
3. Test thuần `tests/test_chay_test_pg_demo.py` (mock/subprocess giả): tiến trình con sinh cháu ngủ 600 giây và giữ stdout → bộ chạy trả TREO sau ≈ hạn (dùng hạn nhỏ trong test, vd 3 giây) và không còn tiến trình cháu; `.pth` nạp lỗi → tiến trình con thoát mã 2; chạy bộ chạy của worktree này với `--goc` trỏ thư mục khác vẫn nạp đúng hàm bảo vệ.

**File được sửa (chỉ):** `tools/chay_test_theo_module.py`, `tests/test_chay_test_pg_demo.py`. Không xóa file.
**Test phải đạt:** `test_chay_test_pg_demo` + chạy bộ chạy **không** `--pg-demo` cho 3 module bất kỳ (kết quả như trước).
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · ca test · thông điệp commit `[L0-8c] …`.
