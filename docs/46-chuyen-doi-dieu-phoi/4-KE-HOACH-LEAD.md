# 4 · Kế hoạch lead Claude Code — nhận bàn giao từ Codex (24/10/2026)

## 0. Kết luận

- Codex đã làm xong phần cần nhất: **toàn bộ 36 đầu việc đã vào git** (19 gói trên `hop-nhat-20261023`; mỗi gói có nhánh `luu/*`; 13 gói xung đột và 2 gói chưa terminal chỉ có ở `luu/*`). Từ giờ không còn code nằm ngoài git.
- Chưa dùng được làm nền: test H4 **treo**, 275/625 kết quả là ERROR, và chưa so với `chinh` nên không biết lỗi nào do hợp nhất gây ra.
- Ba việc đầu tiên của lead, chạy song song: **L0-1** lập nền test; **L0-2a** gộp chuỗi sửa M4 common identity; **L0-2d** gộp nhánh CRM (mở đường cho màn Báo giá).
- **Anh ra lệnh 24/10:** lead phân công Claude và Codex cho tất cả các module đã chốt thiết kế (M9 vẫn dừng). Màn Báo giá (TL 45, #42) bắt đầu ngay khi L0-2d xong.
- **Ô Giá trị thông minh (Anh chốt 24/10):** gõ có `%` → tỷ lệ, máy tự hiện số tiền ngay khi rời ô; gõ số không có `%` → luôn là số tiền. Không có gợi ý "Ý anh là 30%?".

## 1. Hàng đợi lát

| Mã | Việc | Worker gợi ý | Giữ file chung | Phụ thuộc | Trạng thái |
|---|---|---|---|---|---|
| L0-1 | Nền test `chinh` vs `hop-nhat`, tìm test treo, nhóm nguyên nhân ERROR | Claude | — | — | Đang code (24/10) |
| L0-2a | Gộp chuỗi `m4-03b-common-identity` fix01→fix04 | Codex | — | — | Đang code (24/10) |
| L0-2d | Gộp `crm-g5-doi-chieu` + `crm-m4-three` | Claude | `crm_g.py`, `crm_g.js`, `pg_migrations.py` | — | Đang code (24/10) |
| L0-2b | Gộp `m4-02c-ui` → `ui-fix01` | Codex | — | — | Sẵn sàng |
| L0-2e | Gộp `m2-00b-fix01` (có thể là nguyên nhân 114 ERROR M2-00B) | Codex | — | — | Sẵn sàng |
| L0-2f | Gộp `source6-g5-e5-ordered-fix01` | Codex | — | — | Chờ slot |
| L0-2g | Gộp `m4-review-basis-c18-testfix` | Codex | — | — | Chờ slot |
| L0-2c | Gộp `m4-02c-backend` + `m4-04c-request-m27` | Claude | `pg_migrations.py` | sau L0-2d | Chờ |
| L0-2h | Rà `m4b2`, `m4b3` (chưa terminal): còn dùng được gì | Codex | — | — | Chờ slot |
| L0-3 | Sửa nhóm ERROR còn lại theo nguyên nhân gốc L0-1 | theo nhóm | tùy nhóm | sau L0-1, L0-2* | Chờ |
| H5 | Gộp `hop-nhat` → `chinh`, đẩy GitHub | lead | — | sau L0-1, L0-2*, Anh xem `NEN-TEST.md` | Chờ Anh |
| BG-1 | Báo giá gói 1: BG-01…05 (lịch 4 cột, dòng tổng, tính tự động, tổng tự tính, bỏ mã kỹ thuật) | Claude | `crm_g.*` | sau L0-2d (Anh đã ra lệnh 24/10) | Chờ L0-2d |
| BG-2, BG-3 | Báo giá gói 2 (BG-06…12), gói 3 (BG-13, 14) | Claude | `crm_g.*` | sau cổng A gói 1 | Chờ |
| MOD | Lập hàng đợi lát cho các module còn lại đã chốt thiết kế: CRM 42 (danh sách hợp đồng, 6 mục), M4 phần còn lại (công nợ 03B, Request thật để sau), #40 M2-00, #41 E1-MUA; module chưa chốt → checklist + hỏi Anh | lead | — | song song L0-* | Sẵn sàng |
| (theo MOD) | Các lát backend/SQL/test của từng module → ưu tiên Codex; màn hình/luồng → Claude | Codex / Claude | theo lát | sau H5 hoặc trên hop-nhat | Chờ |
| D | Dọn thư mục (chuyển lưu trữ) | lead | — | sau H5 | Chờ |

Ưu tiên khi có slot trống: nhận xét của Anh → lỗi review → lát theo thứ tự bảng.

## 2. Handoff L0-1 · Nền test

```
# L0-1 — Nền test và test treo
Worker: Claude · Nhánh: lat/l0-1 (từ hop-nhat-20261023) · Hạn: 1/2 ngày
Mục tiêu: có bảng nền test đo được cho chinh và hop-nhat, để "xanh" = không thêm lỗi so với nền.
Căn cứ: docs/46-chuyen-doi-dieu-phoi/H4-KET-QUA-TEST-20261024.md; log var/test-results/h4-20261024-output.txt
File được sửa: tools/chay_test_theo_module.py (mới), docs/46-chuyen-doi-dieu-phoi/NEN-TEST.md (mới), CLAUDE.md mục 5 (chỉ dòng lệnh test)
Dùng lại nguyên: test.ps1 (cách tìm Python, engine sqlite)
Việc cụ thể:
- Script chạy từng module test riêng, giới hạn 180 giây/module, ghi ok/ERROR/FAIL/skip/TREO cho từng module.
- Chạy trên hai worktree: chinh (59b7d8e) và hop-nhat-20261023. Chỉ engine sqlite.
- NEN-TEST.md: bảng module · chinh · hop-nhat · chênh · nguyên nhân gốc (1 dòng, đọc traceback đầu tiên) · có treo không.
- Gom ERROR thành ≤ 5 nguyên nhân gốc, mỗi nguyên nhân: số lỗi, module, gợi ý lát sửa.
Không làm: sửa code sản phẩm; sửa test; chạy PostgreSQL; đụng kho thật.
Test phải đạt: script chạy hết cả hai nhánh, không treo quá 180 giây/module.
Báo cáo: ≤ 1 trang, kèm 5 nguyên nhân gốc.
```

## 3. Handoff L0-2a · Chuỗi M4 common identity

```
# L0-2a — Gộp m4-03b-common-identity fix01→fix04
Worker: Codex · Nhánh: lat/l0-2a (từ hop-nhat-20261023) · Hạn: 2–3 giờ
Mục tiêu: nhánh hop-nhat có bản cuối của chuỗi sửa common identity.
Căn cứ: TAN-DUNG-CODE.md dòng m4-03b-*; nhánh luu/m4-03b-common-identity-fix01…fix04
File được sửa: src/kho_tri_thuc/**/ghi_nhan_chung.py, sql_ghi_nhan_chung.py và test đi kèm các nhánh luu này (≤ 5 file)
Quy tắc gộp: bản kế nhiệm thắng — áp lần lượt fix01, fix02, fix03, fix04 lên hop-nhat; xung đột trong 2 file trên lấy nội dung của bản fix sau cùng có chứa file đó; mỗi fix một commit "[L0-2a] áp fix0N".
Không làm: sửa logic ngoài nội dung các bản fix; thêm tính năng; sửa file khác.
Test phải đạt: các module test của common identity / ghi nhận chung chạy được; không thêm lỗi so với cùng module trên hop-nhat trước lát.
Báo cáo: ≤ 1 trang: commit, file, test trước/sau.
```

## 4. Handoff L0-2d · Nhánh CRM

```
# L0-2d — Gộp crm-g5-doi-chieu và crm-m4-three
Worker: Claude · Nhánh: lat/l0-2d (từ hop-nhat-20261023) · Hạn: 1/2 ngày · Giữ khóa: crm_g.py, crm_g.js, pg_migrations.py
Mục tiêu: hop-nhat có đủ code CRM G4+G5+liên kết M4 để màn Báo giá sửa trên bản mới nhất.
Căn cứ: TAN-DUNG-CODE.md dòng crm-*; nhánh luu/crm-g5-doi-chieu-20261023-01, luu/crm-m4-three
File được sửa: crm_g.py, crm_g.js, pg_migrations.py và test đi kèm hai nhánh (≤ 8 file)
Quy tắc gộp: giữ cả hai phía; trùng hàm thì giữ bản có thêm hành vi mới, không bỏ hành vi cũ; migration giữ thứ tự số, không đổi số đã dùng.
Không làm: sửa giao diện Báo giá (để BG-1); thay engine #6; sửa M4 ngoài phần nối CRM.
Test phải đạt: test CRM G4/G5 và test nối M4–CRM chạy; không thêm lỗi so với hop-nhat trước lát.
Tự thử: mở màn CRM DEMO, vào Báo giá và Đối chiếu, chụp màn hình.
Báo cáo: ≤ 1 trang.
```

Các lát L0-2b, L0-2e, L0-2f, L0-2g, L0-2c, L0-2h dùng cùng mẫu với L0-2a; lead viết handoff khi có slot.

## 5. Lệnh dừng gửi Codex Root (Anh dán)

> Theo quyết định của Anh ngày 24/10: **dừng hẳn vai Codex Root từ bây giờ.** Không làm H5, không đẩy GitHub, không dọn thư mục, không giao việc, không chạy test, không bật lại automation nào. Xác nhận trong một dòng: đã tắt mọi lịch tự động/heartbeat và không còn tiến trình nào của Codex đang chạy trong repo. Từ nay Claude Code điều phối; Codex chỉ nhận lát cụ thể khi Claude gọi qua `codex exec`, theo `AGENTS.md` ở gốc repo.

## 6. Lệnh khởi động phiên lead (Anh dán vào Claude Code trên máy)

Mở ứng dụng Claude trên máy → tab Code → phiên **trên máy này** (không phải đám mây) → chọn thư mục `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức` → chọn model Opus, rồi dán:

> Bạn là lead điều phối của repo này từ hôm nay. Đọc `CLAUDE.md`, `AGENTS.md` và `docs\46-chuyen-doi-dieu-phoi\4-KE-HOACH-LEAD.md`. Chép nguyên cây `docs\46-chuyen-doi-dieu-phoi\cai-dat-claude\` (settings.json, agents\, hooks\) vào `.claude\` ở gốc repo, chạy thử hook `chan_lenh_nguy_hiem.py` với một lệnh `rm` giả để chắc nó chặn được, rồi khởi động lại phiên để nạp cấu hình. Kiểm `git status`, nhánh hiện tại phải là `hop-nhat-20261023`. Kiểm `codex --version`: nếu chưa có Codex CLI thì đề xuất cài (`npm install -g @openai/codex`) và đăng nhập bằng tài khoản ChatGPT của tôi (`codex login`, mở trình duyệt) — hỏi tôi trước khi cài; thử một lệnh `codex exec` nhỏ chỉ đọc để chắc chạy được. Sau đó giao song song L0-1 (subagent worker-lat-man-hinh), L0-2a (Codex nếu có, không thì Claude) và L0-2d (subagent worker-lat-man-hinh), đồng thời làm lát MOD: lập hàng đợi lát cho mọi module đã chốt thiết kế theo lệnh của tôi ngày 24/10 (M9 dừng), chia việc cho Claude và Codex. Cập nhật cột trạng thái trong kế hoạch và `TRANG-THAI.md` khi mỗi lát đổi trạng thái. Chỉ báo tôi khi: L0-1 có bảng nền test, một lát bị chặn, hoặc cần tôi quyết.

## 7. Nhật ký lead

**24/10/2026 — phiên lead đầu tiên**
- Cài cấu hình: chép `cai-dat-claude\` vào `.claude\` (commit 1502fe7 trên `hop-nhat`). Hook chặn thử 13/13 ca đúng; đã sửa hook đọc/ghi UTF-8 (Windows cp1252 làm lỗi phông), thêm matcher PowerShell/Read/Grep/Glob và deny đọc kho thật. Bản mẫu trong `cai-dat-claude\` đồng bộ theo.
- Worktree: `isolation: worktree` của Claude Code tạo worktree từ nhánh `main` (48e164f, nền cũ, không có hook) → hook lỗi chặn mọi công cụ. Bỏ `isolation` khỏi `worker-lat-man-hinh`; **lead tự tạo worktree**: `git worktree add -b lat/<ma> .claude/worktrees/lat-<ma> hop-nhat-20261023`.
- Subagent tự định nghĩa (`worker-lat-man-hinh`, `kiem-nhanh`) chỉ nạp khi khởi động lại phiên; tới lúc đó lead gọi worker bằng agent chung + Sonnet + đọc file vai.
- Codex CLI 0.164.0 đã cài, đã đăng nhập ChatGPT sẵn. Lệnh worker: `codex exec --sandbox workspace-write --add-dir <repo>/.git -c model_reasoning_effort=high -o <báo cáo> - < <handoff>` chạy trong worktree của lát. Cấu hình Codex toàn máy có quy tắc "hỏi trước khi code" và mức `ultra` → handoff ghi rõ "Anh đã duyệt qua lead, làm ngay"; hạ `high` cho lát gộp/sửa.
- Giao song song: L0-1 (Claude), L0-2a (Codex), L0-2d (Claude).
