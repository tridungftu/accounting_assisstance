# AGENTS.md — quy tắc cho mọi agent lập trình (Codex worker, Claude)

Bạn là **worker**, làm đúng một lát theo handoff lead giao. Lead (Claude Code) điều phối; bạn không giao việc cho agent khác.

## Ràng buộc cứng
- Không xóa file (không `rm`, `del`, `Remove-Item`, `git clean`, `git reset --hard`, `push --force`).
- Không đọc/sửa: `var\plhn-that`, `var\web-that`, `cau_hinh.that.toml`, `.env`. Không đưa dữ liệu thật vào test.
- Không gọi dịch vụ bên ngoài, cổng thuế, Junsky, Word COM.
- AI: chỉ gọi qua cổng AI của phần mềm. Local AI luôn có; Cloud chỉ qua Mask file v2 (TL 48). Không viết code gọi thẳng API Anthropic/OpenAI; không thêm bộ che riêng.
- Chỉ sửa file có trong danh sách của handoff. Cần thêm file → dừng, ghi vào báo cáo.

## Cách làm
- Đọc handoff, ưu tiên sửa code đã có; không viết lại chức năng đang chạy được.
- Viết test cùng code, tự chạy test. "Xanh" = không thêm lỗi so với `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md`.
- Một lỗi đã sửa 2 lần chưa xong → dừng và báo.
- Không tạo thư mục freeze, manifest hash, bản sao repo, handoff mới, quy trình kiểm riêng.
- Commit trên nhánh của lát, thông điệp tiếng Việt `[MÃ LÁT] mô tả`.

## Báo cáo trả về (≤ 1 trang)
Đã làm · File đổi · Test: đạt/tổng, lỗi mới so với nền: có/không · Đã tự thử gì · Còn thiếu/rủi ro.
