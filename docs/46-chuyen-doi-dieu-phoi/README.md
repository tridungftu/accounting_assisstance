# 46 · Chuyển đổi điều phối — Claude Code làm lead, Codex làm reviewer

Bản nháp 23/10/2026, chờ Anh duyệt. Không file nào trong thư mục này có hiệu lực tự động: tên file đã đổi (`NHAP`, `.nhap.json`) để Claude Code/Codex không tự nạp.

| Tài liệu | Dùng để | Khi nào áp dụng |
|---|---|---|
| `1-NHAP-CLAUDE.md` | Quy tắc chung cho mọi phiên Claude Code của repo | Sau bước H (hợp nhất code): đổi tên thành `CLAUDE.md` ở gốc repo |
| `1-agents\*.md` | Định nghĩa worker (Sonnet, worktree, được chạy test) và kiểm nhanh (Haiku, chỉ đọc) | Chép vào `.claude\agents\` |
| `1-settings.nhap.json`, `1-hooks\*.py` | Chặn lệnh xóa, chặn kho thật/.env; không cho worker kết thúc khi test đỏ | Chép thành `.claude\settings.json`, `.claude\hooks\`; lead chạy thử trên máy trước |
| `2-PHIEU-KIEM-TRA-CHUC-NANG.md` | Mẫu phiếu cổng A (Anh góp ý sớm) và cổng B (nghiệm thu); có ví dụ màn Báo giá | Mỗi lần lead báo "màn sẵn sàng" |
| `3-CHI-DAO-GUI-CODEX.md` | Lệnh cho Codex: dừng, hợp nhất code vào git, dọn thư mục (chỉ di chuyển), đổi vai | Anh duyệt rồi dán cho Codex |

Thứ tự: 3 (Codex dừng → hợp nhất → dọn) → 1 (cài cấu hình Claude Code) → màn đầu tiên Báo giá với phiếu 2.
