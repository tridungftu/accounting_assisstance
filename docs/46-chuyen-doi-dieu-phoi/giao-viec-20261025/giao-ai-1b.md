# AI-1b — Local AI: cấu hình cũ, LM Studio, trạng thái lỗi (theo review-lat sau gộp AI-1)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2 dòng "Cổng AI"). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/ai-1b` (từ hop-nhat, đã có AI-1). Sandbox không ghi `.git`: **không commit**. **Không gọi mạng thật** (máy AI giả/mock như `tests/test_ai1_local_ai_lan.py`). Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`; sandbox chặn python → ghi "lead chạy test".

**Mục tiêu nghiệp vụ:** người dùng đã cài Local AI theo hướng dẫn cũ vẫn dùng được hoặc thấy ngay lý do không dùng được; máy AI LM Studio dùng được; máy AI tắt không làm việc đề xuất chậm cả phút.

**Việc:**
1. `src/kho_tri_thuc/tri_thuc/ai_cuc_bo.py` `_parse_url` (~:32-50): nhận `localhost` và đổi thành `127.0.0.1` **không tra DNS** (như Mask v2 `privacy\local_ai.py` ~:135, chỉ đọc tham khảo); các tên miền khác vẫn từ chối.
2. Cùng tệp `_check_model` (~:182-196): `/api/tags` trả 200 nhưng **không có** `models` dạng danh sách (LM Studio trả 200 cho đường lạ) → coi như máy AI không phải Ollama, bỏ qua bước này (không báo lỗi); chỉ đối chiếu khi `models` là danh sách.
3. Cùng tệp: nhớ **trạng thái lỗi kết nối 15 giây** theo URL (như Mask v2 ~:277): trong 15 giây sau một lần không kết nối được, `choose_counterparty` trả `None` ngay, không gọi lại. Không lưu nội dung prompt/câu trả lời.
4. `src/kho_tri_thuc/giao_dien/operations.py` (~:183-210 đọc `source_settings`, ~:1100 đưa lên giao diện, ~:274 lưu): chuẩn hóa `local_ai` bằng `local_ai_settings` **ngay khi đọc** để giao diện hiện đúng "đang bật"/thông báo lỗi; khi lưu **không** ghi khóa `error` vào `source-settings.json` và không tự đổi `enabled` của người dùng.
5. Test trong `tests/test_ai1_local_ai_lan.py`: `localhost` → gọi tới 127.0.0.1, không `getaddrinfo`; `/api/tags` 200 không có `models` → vẫn trả lời; lỗi kết nối → lần gọi thứ 2 trong 15 giây không chạm mạng; `0.0.0.0`, `::ffff:127.0.0.1` bị từ chối; đọc cấu hình cũ `http://localhost:1234/v1/chat/completions` → giao diện thấy bật; lưu không ghi `error`.

**File được sửa (chỉ 3):** `src/kho_tri_thuc/tri_thuc/ai_cuc_bo.py`, `src/kho_tri_thuc/giao_dien/operations.py`, `tests/test_ai1_local_ai_lan.py`. Không xóa file.
**Test phải đạt:** `--module test_ai1_local_ai_lan --module test_v11` + module test hiện có của `operations.py` liên quan cài đặt nguồn (tìm bằng grep `source_settings`).
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · ca test · thông điệp commit `[AI-1b] …`.
