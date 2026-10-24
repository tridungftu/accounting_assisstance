# CLAUDE.md — Phần mềm kho tri thức (điều phối từ 24/10/2026)

Đọc theo thứ tự: `CLAUDE.md` ở thư mục cha (quy tắc dự án) → file này (điều phối) → quy trình chung bên dưới. Quy ước với anh Dũng: Project claude.ai "phần mềm Hỗ trợ kế toán", tài liệu `claude/00`.

@../../QUY-TRINH-CHUNG/DIEU-PHOI-CLAUDE-CODE-VA-CODEX.md

## 1. Ai làm gì (Anh chốt 23–24/10/2026)

- **Lead = phiên Claude Code chính trên máy Anh, model Opus.** Codex Root đã dừng hẳn từ 24/10; Codex chỉ còn là worker (1–2, qua `codex exec`) và reviewer chéo khi lead gọi.
- Worker Claude: subagent `worker-lat-man-hinh` (Sonnet, worktree riêng). Kiểm nhanh: `kiem-nhanh` (Haiku, chỉ đọc). Lead tự chọn từng lát giao Claude hay Codex. Tối đa 3 worker cùng lúc.
- **Lệnh của Anh 24/10/2026:** lead phân công Claude và Codex cho **tất cả các module** có thiết kế đã chốt trong hàng đợi (`HANG-DOI-YEU-CAU.md`, `THIET-KE-MODULE-DE-CHOT-2026-10-20\HANG-CHO-CODE.md`) — gồm #42 Báo giá (TL 45), #40 M2-00, #41 E1-MUA, phần còn lại của M4 · Nghiệm thu & chi phí dự án và CRM. M9 vẫn dừng. Module/đầu việc chưa chốt thiết kế: lead soạn checklist ngắn từ tài liệu thiết kế, hỏi Anh bằng bảng chọn trước khi code.

## 2. Ràng buộc cứng

- **Không xóa file**; cần bỏ thì chuyển vào `D:\Claude\Phan mem ho tro ke toan\LUU-TRU\`. Không `git clean`, `git reset --hard`, `push --force`.
- Kho thật `var\plhn-that`, `var\web-that`, `cau_hinh.that.toml`: không đọc/sửa qua công cụ; kho thật vẫn SQLite. Không đọc `.env`.
- M9 · Vốn vay & đầu tư tài chính dừng. Không bật cloud, không nhập Junsky, không gọi cổng thuế thật, không Request thật, không Word COM (xuất DOCX; PDF tạm xuất tay).
- Dữ liệu thử chỉ DEMO; không đưa dữ liệu thật vào `tests\fixtures`.

## 3. Trạng thái git khi nhận bàn giao (24/10/2026)

- `chinh` = H1 `59b7d8e` (nguyên trạng trước hợp nhất). `main` / `origin/main` là lịch sử GitHub cũ.
- `hop-nhat-20261023` = nhánh tích hợp đang dùng: 19 gói đã nhập. Mỗi gói còn một nhánh `luu/<ten>`; 13 gói xung đột + 2 gói chưa terminal chỉ có ở `luu/*`.
- Bảng chi tiết: `docs\46-chuyen-doi-dieu-phoi\TAN-DUNG-CODE.md`, `HEADS-HOP-NHAT-20261024.csv`.
- Test H4 (SQLite) **treo, chưa có nền**: 625 kết quả ghi được — 206 ok, 275 ERROR, 4 FAIL, 140 skip. Chưa biết lỗi nào có sẵn từ `chinh`. Vì vậy **hook cổng test của worker đang tắt** cho tới khi lát L0-1 lập được nền test.
- Chưa gộp vào `chinh`, chưa đẩy GitHub (chờ Anh xem kết quả test), chưa dọn thư mục.

## 4. Quy tắc riêng khi điều phối repo này

- Lát mới tạo worktree từ `hop-nhat-20261023` cho tới khi gộp về `chinh`.
- "Xanh" tạm thời = **không thêm lỗi so với nền** ở `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md` (lập ở L0-1), không phải 100% đạt.
- File dùng chung, mỗi lúc một lát giữ (ghi trong `docs\46-chuyen-doi-dieu-phoi\TRANG-THAI.md`): `src\kho_tri_thuc\server.py`, `ha_tang\pg_migrations.py`, `giao_dien\crm_g.py`, `giao_dien\assets\crm_g.js`, các file `m4\*` dùng chung.
- Gọi tên module kèm tên chu trình ("M4 · Nghiệm thu & chi phí dự án").
- Giao diện: tiếng Việt nghiệp vụ, không mã kỹ thuật, ngày dd/mm/yyyy, tiền có đơn vị.
- Kế hoạch và hàng đợi lát của lead: `docs\46-chuyen-doi-dieu-phoi\4-KE-HOACH-LEAD.md`.

## 5. Lệnh

- Test: `powershell -NoProfile -ExecutionPolicy Bypass -File test.ps1 -Engine sqlite` (đang treo — L0-1 sẽ thêm giới hạn thời gian từng test và ghi lệnh chạy nhanh vào đây).
- PostgreSQL test cần biến `KHO_PG_DSN_TEST` trỏ tới CSDL DEMO riêng; chưa cấu hình.
- [L0-1 ĐIỀN] lệnh mở server DEMO trên cổng riêng cho một worktree.
