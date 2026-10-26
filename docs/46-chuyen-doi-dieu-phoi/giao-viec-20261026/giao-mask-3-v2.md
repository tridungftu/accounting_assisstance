# MASK-3 vòng 2: Mask file v2 2.7.2, sửa điểm Chặn và các điểm nên sửa của review vòng 1

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Thư mục làm việc: `D:\GPT\Phan mem Mask file\Mask file v2`. Thư mục này **không phải git**.
- **Tuyệt đối không** đọc, mở hay liệt kê `data\`, `*.key`, `*.maskvault`, `*.maskkeep`, `*.maskpending` thật, `config\mask-api.key`, `.backups\`, `.venv*\`, `File ví dụ\`.
- Không thêm thư viện. Ghi tệp UTF-8 không BOM. Không xóa file; cần bỏ thì đổi tên.
- Không chạy server thật; test dùng TestClient/tmp như hiện có.
- Giữ nguyên định dạng `.maskvault`/`.maskkeep`. Không nới Host/Origin/CSRF/Bearer hay kiểm "còn sót".

**1. Chặn: không để tự tải lại làm phiên không hết hạn.**
- `privacy/static/app.js` (khoảng dòng 728) đặt `setInterval` 15 giây gọi `/api/pending`. Mỗi lần gọi, `session_for` (`privacy/server.py:329`) gia hạn phiên, nên tab bỏ quên giữ danh mục mở mãi; trái quy tắc "phiên giao diện khóa sau 1 giờ".
- Sửa: **bỏ tự tải lại định kỳ**. Chỉ tải khi mở mục "chờ duyệt", khi bấm "Tải lại danh sách", hoặc sau một thao tác duyệt.
- Thêm kiểm vào `tests/pending_ui_smoke.cjs`: không có `setInterval`/`setTimeout` lặp gọi `/api/pending`.
- Sửa README và CHANGELOG cho khớp.

**2. Nên sửa:**
- `privacy/server.py` (khoảng dòng 587):
  - Khi **tạo danh mục mới**, đặt sang bên tệp `.maskpending` cũ, giống cách đang làm với `.maskkeep` (đổi tên có dấu thời gian, không xóa).
  - Khi tệp chờ không đọc được, màn duyệt có nút "Đặt sang bên tệp chờ không đọc được". Nút đổi tên tệp, có hỏi xác nhận, cần CSRF và revision như các lệnh khác.
- `privacy/pending.py` (khoảng dòng 108–110): **không lưu ngữ cảnh bí danh của lượt** (để rỗng).
  - Sửa test `tests/test_auto_api.py::test_turn_mapping_is_never_written_to_disk` để bao cả lượt có cụm mới: chỉ được ghi `.maskpending` cùng tệp khóa/tệp tạm của nó, không ghi gì khác.
- `privacy/server.py` (khoảng dòng 1565): chưa có danh mục mà lượt có cụm mới thì trả mã **riêng** `danh_muc_chua_co`, câu "Chưa có danh mục: tạo và mở khóa danh mục để lưu cụm mới chờ duyệt." Giữ HTTP 423 và `gui_duoc:false`.
- `tests/test_auto_api.py` (script `GUARDED_SERVER`): **bỏ `import httpx`** trong script tiến trình con. Mở danh mục từ tiến trình cha bằng thư viện chuẩn (`urllib`), hoặc gửi đủ `dinh_danh_da_biet` để lượt không có cụm mới. Tiến trình con chỉ dùng thư viện runtime.
- `CHANGELOG.md` mục 2.7.2: thay câu "không khởi chạy được pytest/benchmark" bằng số lead đã đo:
  - pytest `-m "not ocr"`: 469 đạt.
  - Đỏ có từ trước 2.7.0: `test_local_ai::test_cancel_and_reset…`.
  - `test_p0_fixes::test_relevant_rules_scales…` đỏ khi máy tải nặng, chạy riêng đạt.
  - `test_outbound_guard…` đỏ ở môi trường thiếu httpx trong tiến trình con; đã sửa ở vòng này.
  - Benchmark: bộ chính lộ 1/101, held_out lộ 6/51, đều giữ nguyên so 2.7.1.
  - Ghi thêm các thay đổi vòng 2.

**Không làm** (chờ Anh): hộp xác nhận cho "Đánh dấu không phải định danh". Chỉ ghi vào "Việc để sau" trong CHANGELOG.

**Chạy:**
- `node --check privacy/static/app.js`;
- `node tests/pending_ui_smoke.cjs`;
- pytest nếu chạy được. Không chạy được thì nêu rõ, lead sẽ chạy.

**Báo cáo (≤ ¼ trang):** danh sách tệp đổi, kết quả chạy.
