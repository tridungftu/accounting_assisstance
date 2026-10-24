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

- Test (từng module trong tiến trình riêng, tối đa 180 giây/module, ghi ok/ERROR/FAIL/skip/TREO): `python -X utf8 tools\chay_test_theo_module.py . --ra "$env:TEMP\kq.json"`; một module: `python -X utf8 tools\chay_test_theo_module.py . --module test_m1`. Cả bộ mất khoảng 6 phút — chạy nền (`run_in_background`). So với nền ở `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md` và `nen-test-hop-nhat.json`. `test.ps1` (một tiến trình) vẫn dùng được cho PostgreSQL nhưng sẽ treo ở `test_source6_g5_e5`.
- PostgreSQL test cần biến `KHO_PG_DSN_TEST` trỏ tới CSDL DEMO riêng; chưa cấu hình.
- Server DEMO cho một worktree, có CRM PostgreSQL (mỗi worktree một cổng riêng, ví dụ 8783; cấm 8766/8767/8768), chạy nền, từ thư mục bất kỳ: `powershell -NoProfile -ExecutionPolicy Bypass -File "<worktree>\tools\mo_demo_worktree.ps1" -Port 8783 -CsdlRieng p8783` (dữ liệu ở `<worktree>\var\demo-8783`; `-CsdlRieng auto` = `p<cổng>`). **Mặc định cho worktree là CSDL DEMO riêng**: script gọi `tools\tao_ket_noi_demo_rieng.py` ghi `<DataRoot>\crm-demo\ket-noi.local.json` chỉ khác tên CSDL (`kho_crm_demo_lt_<hậu tố>`, cùng máy chủ/login với CSDL DEMO của Anh, không in DSN), rồi bước chuẩn bị CRM tự `CREATE DATABASE` nếu chưa có, migrate và seed DEMO — CSDL DEMO của Anh (dùng bởi `var\web`) không bị nâng schema hay lẫn dữ liệu thử; hết cần kiểm chuỗi migration. Mỗi cổng/lát một hậu tố riêng (CSDL riêng cho cổng 8783 giữ lại giữa các lần mở; dọn bằng tay khi bỏ, script không DROP). Script chép sẵn runtime và cụm PostgreSQL DEMO, đồng bộ `tests\fixtures` từ repo chính, in `pid` và trạng thái CRM; thêm `-KhongCrm` để mở không nối CSDL (loại trừ với `-CsdlRieng`). Kiểm `http://127.0.0.1:8783/api/health`; dừng đúng tiến trình theo `pid` trong health (server cũ khởi động trước khi tệp kết nối đổi → script dừng với mã 2, dừng pid rồi chạy lại). Không dùng `var\web`, `var\plhn-*`, `var\web-that` làm thư mục dữ liệu. Không có `-CsdlRieng` → CSDL dùng chung với bản DEMO của Anh (migration chỉ tiến nên script chỉ chuẩn bị CRM khi chuỗi migration của worktree trùng repo chính, khác thì dừng mã 2; dữ liệu thử hiện ở DEMO của Anh) — chỉ dùng khi cố ý xem đúng bản của Anh.
