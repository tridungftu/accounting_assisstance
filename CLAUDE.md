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

## 3. Trạng thái git (lead cập nhật, 24/10/2026 chiều)

- `chinh` = H1 `59b7d8e` (nguyên trạng trước hợp nhất). `main` / `origin/main` là lịch sử GitHub cũ.
- `hop-nhat-20261023` = nhánh tích hợp; thư mục chính đang checkout nhánh này. Đã gộp thêm L0-1, L0-2a/d/e/f/i, P0 (khôi phục 24 file chưa vào git), L0-3a, L0-4, L0-4b. Gói còn lại chỉ ở `luu/*`: xem `docs\46-chuyen-doi-dieu-phoi\4-KE-HOACH-LEAD.md` (L0-2b, L0-2c, L0-2g, L0-2h).
- Nền test **v2** (hop-nhat `7b114e2`, có `--runtime`): 1276 ok / 34 ERROR / 57 FAIL / 292 skip, 1 module treo (`test_source6_g5_e5`) — `NEN-TEST.md` mục 0b, `nen-test-hop-nhat-v2.json`. Số H4 cũ (275 ERROR) không tái hiện được, bỏ.
- Hook cổng test của worker vẫn tắt (lát L0-5 sẽ bật, so theo `ids_loi`).
- Chưa gộp vào `chinh`, chưa đẩy GitHub (chờ Anh xem kết quả test, H5), chưa dọn thư mục. Thư mục chính ở nhánh hợp nhất chưa nghiệm thu: không mở `MỞ BẢN DEMO.cmd` (sẽ nâng CSDL CRM DEMO của Anh) khi chưa báo Anh.

## 4. Quy tắc riêng khi điều phối repo này

- Lát mới tạo worktree từ `hop-nhat-20261023` cho tới khi gộp về `chinh`.
- "Xanh" tạm thời = **không thêm mã lỗi (`ids_loi`) so với nền v4** ở `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md` mục 0 (`nen-test-hop-nhat-v4.json`; `test_trich6_host.HandlerSoHuuTests…` chập chờn khi chạy cả bộ), không phải 100% đạt.
- File dùng chung, mỗi lúc một lát giữ (ghi trong `docs\46-chuyen-doi-dieu-phoi\TRANG-THAI.md`): `src\kho_tri_thuc\giao_dien\server.py`, `ha_tang\pg_migrations.py`, `giao_dien\crm_g.py`, `giao_dien\assets\crm_g.js`, `giao_dien\m4.py`, `giao_dien\assets\app.js`, `index.html`, `style.css`, các file `m4\*` dùng chung.
- Worktree của lát do lead tạo (`git worktree add -b lat/<ma> .claude/worktrees/lat-<ma> hop-nhat-20261023`); không dùng `isolation: worktree` (Claude Code tạo từ `main` cũ). Mọi lệnh có thể quá 2 phút và mọi server phải chạy nền, nếu không agent bị ngắt sau 600 giây.
- Gọi tên module kèm tên chu trình ("M4 · Nghiệm thu & chi phí dự án").
- Giao diện: tiếng Việt nghiệp vụ, không mã kỹ thuật, ngày dd/mm/yyyy, tiền có đơn vị.
- Kế hoạch và hàng đợi lát của lead: `docs\46-chuyen-doi-dieu-phoi\4-KE-HOACH-LEAD.md`.

## 5. Lệnh

- Test (từng module trong tiến trình riêng, tối đa 180 giây/module, ghi ok/ERROR/FAIL/skip/TREO): `python -X utf8 tools\chay_test_theo_module.py . --runtime "D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\var\web\crm-demo\runtime.local.json" --ra "$env:TEMP\kq.json"` (`--runtime` = Python có psycopg của bản DEMO; chỉ đọc khóa `python`, `duong_dan_phu_thuoc`); một module: thêm `--module test_m1`. Cả bộ mất khoảng 6–7 phút — chạy nền (`run_in_background`). So với nền v4: `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md` mục 0 và `nen-test-hop-nhat-v4.json`. `test.ps1` (một tiến trình) vẫn dùng được cho PostgreSQL nhưng sẽ treo ở `test_source6_g5_e5`.
- Test có PostgreSQL (L0-8, Anh chốt 25/10): thêm `--pg-demo "D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\var\web\crm-demo\ket-noi.local.json" --gioi-han 900` vào lệnh test ở trên (kèm `--runtime`; cả bộ ~16 phút — chạy nền). Công cụ đọc DSN bằng chương trình (không in/log), đặt `KHO_PG_DSN_TEST` chỉ cho tiến trình con, chụp danh sách CSDL trước, sau MỖI module chỉ DROP các `kho_test_*` MỚI (không có ở ảnh chụp, tên khớp `^kho_test_[a-z0-9_]+$`, không FORCE), và dựng bản sao DEMO `kho_test_pgd_*` cho module cần biến `*_CLONE_*` rồi xóa. Không đụng `kho_crm_demo*` (kể cả `_lt_`); không DROP vai trò (test để lại `ktt_test_*`). Giới hạn: chỉ một lần chạy `--pg-demo` cùng lúc và không chạy bộ test PostgreSQL khác song song trên cụm DEMO; lần chạy chết giữa chừng: thêm `--pg-demo-don-so <nhat-ky>\pg-demo-so-ghi.json` (chỉ dọn, không chạy test). Số đo: `docs\46-chuyen-doi-dieu-phoi\NEN-TEST-PG.md`.
- Server DEMO cho một worktree, có CRM PostgreSQL (mỗi worktree một cổng riêng, ví dụ 8783; cấm 8766/8767/8768), chạy nền, từ thư mục bất kỳ: `powershell -NoProfile -ExecutionPolicy Bypass -File "<worktree>\tools\mo_demo_worktree.ps1" -Port 8783 -CsdlRieng p8783` (dữ liệu ở `<worktree>\var\demo-8783`; `-CsdlRieng auto` = `p<cổng>`). **Mặc định cho worktree là CSDL DEMO riêng**: script gọi `tools\tao_ket_noi_demo_rieng.py` ghi `<DataRoot>\crm-demo\ket-noi.local.json` chỉ khác tên CSDL (`kho_crm_demo_lt_<hậu tố>`, cùng máy chủ/login với CSDL DEMO của Anh, không in DSN), rồi bước chuẩn bị CRM tự `CREATE DATABASE` nếu chưa có, migrate và seed DEMO — CSDL DEMO của Anh (dùng bởi `var\web`) không bị nâng schema hay lẫn dữ liệu thử; hết cần kiểm chuỗi migration. Mỗi cổng/lát một hậu tố riêng (CSDL riêng cho cổng 8783 giữ lại giữa các lần mở; dọn bằng tay khi bỏ, script không DROP). Script chép sẵn runtime và cụm PostgreSQL DEMO, đồng bộ `tests\fixtures` từ repo chính, in `pid` và trạng thái CRM; thêm `-KhongCrm` để mở không nối CSDL (loại trừ với `-CsdlRieng`). Kiểm `http://127.0.0.1:8783/api/health`; dừng đúng tiến trình theo `pid` trong health (server cũ khởi động trước khi tệp kết nối đổi → script dừng với mã 2, dừng pid rồi chạy lại). Không dùng `var\web`, `var\plhn-*`, `var\web-that` làm thư mục dữ liệu. Không có `-CsdlRieng` → CSDL dùng chung với bản DEMO của Anh (migration chỉ tiến nên script chỉ chuẩn bị CRM khi chuỗi migration của worktree trùng repo chính, khác thì dừng mã 2; dữ liệu thử hiện ở DEMO của Anh) — chỉ dùng khi cố ý xem đúng bản của Anh.
