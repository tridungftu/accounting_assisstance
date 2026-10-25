# REVIEW M4-6 (M4 · Nghiệm thu & chi phí dự án · 04 Request nháp — nối máy chủ) · vòng 1/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8.

**Đối tượng:** worktree hiện tại, nhánh `lat/m4-6`, commit `5f7b913` (một file): `git show 5f7b913 -- src/kho_tri_thuc/giao_dien/server.py` (+16 dòng). Đặc tả: docstring đầu `src/kho_tri_thuc/giao_dien/m4_request.py`; test `tests/test_m4_04b_request_wiring_http.py`. Worker báo: test wiring 3/13 ERROR → 16/0; cả bộ 0 mã lỗi mới.
**Ràng buộc cứng:** không gọi Request thật/mạng; vắng cấu hình → 503 `CHUA_CAU_HINH` sau kiểm quyền; không đọc env/khóa.

**Kiểm 4 việc, Đạt/Không:**
1. `LocalApp.gan_request_nhap` / `go_request_nhap`: mặc định khi khởi động là **vắng**; không nơi nào tự gắn transport thật; sai kiểu → lỗi, không gắn nửa chừng.
2. `Handler.handle_route`: chỉ **đúng ba route** `/api/m4-request`, `/tao`, `/doi-soat` vào `m4_request.dieu_huong`; đứng **sau** `authorize` (token/phiên/cookie như M4) và trước dispatcher `/api/m4*`; route lạ cùng tiền tố → 404; không có đường vòng bỏ qua quyền.
3. `parse_qs(..., keep_blank_values=True)` chỉ áp cho ba route này; route khác không đổi hành vi.
4. Không đổi gì ngoài `server.py`; không lộ khóa/đường dẫn trong lỗi.

**Báo cáo cuối (≤ ½ trang, tiếng Việt, ≤ 6 điểm):**
```
REVIEW M4-6 · vòng 1/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
