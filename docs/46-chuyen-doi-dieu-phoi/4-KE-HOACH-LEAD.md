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
| L0-1 | Nền test `chinh` vs `hop-nhat`, tìm test treo, nhóm nguyên nhân ERROR | Claude | — | — | Xong 24/10 — gộp a1da3d4 |
| L0-2a | Gộp chuỗi `m4-03b-common-identity` fix01→fix04 | Codex | — | — | Xong 24/10 — gộp hop-nhat 73deacb |
| L0-2i | Tìm code/test chỉ có trong `var\codex-dieu-phoi` (chưa vào git) — phát hiện khi làm L0-2a | Codex | — | — | Xong 24/10 — gộp 8b4670f; A=27, B=26 |
| L0-2d | Gộp `crm-g5-doi-chieu` + `crm-m4-three` | Claude | `crm_g.py`, `crm_g.js`, `pg_migrations.py` | — | Xong 24/10 — gộp b2fd07c |
| L0-4 | Lệnh mở DEMO cho worktree, có CRM PostgreSQL: DataRoot `var\demo-<lát>` trong worktree + chép `runtime.local.json`, `ket-noi.local.json` từ `var\web\crm-demo` (không mở nội dung), kiểm CSDL DEMO không đụng nhau giữa worktree; ghi lệnh vào CLAUDE.md mục 5 | Claude | — | sau L0-1 | Xong 24/10 — gộp 7cbc41b |
| L0-4b | CSDL CRM DEMO riêng cho lập trình (Anh chốt 24/10: không dùng chung DEMO của Anh) | Claude | `mo_demo_worktree.ps1`, CLAUDE.md mục 5 | sau L0-4 | Xong 24/10 — gộp 550f573 |
| L0-2b | Gộp `m4-02c-ui` → `ui-fix01` | Codex | — | — | Sẵn sàng |
| L0-2e | Gộp `m2-00b-fix01` (có thể là nguyên nhân 114 ERROR M2-00B) | Codex | — | — | Xong 24/10 — gộp 3a2b083 |
| L0-2f | Gộp `source6-g5-e5-ordered-fix01` | lead | — | — | Xong 24/10 — gộp d07117a; không hết treo → L0-3b |
| L0-3a | Lỗi môi trường N3/N4 (CRLF, fixture bị ignore, sys.path) + bộ chạy test dùng Python có psycopg | Codex | `run_suite.py`, `chay_test_theo_module.py`, `.gitattributes` | sau L0-1 | Xong 24/10 — gộp 7b114e2 |
| L0-3b | Sửa test treo `test_source6_g5_e5` (vòng lặp bận ở `json.raw_decode`) | Codex | — | — | Chờ slot |
| L0-5 | Bật hook cổng test so với nền theo `ids_loi` (`cong_test.py`) | Codex | `.claude\hooks` | sau đo lại nền | Chờ |
| L0-2g | Gộp `m4-review-basis-c18-testfix` | Codex | — | — | Chờ slot |
| L0-2c | Gộp `m4-02c-backend` + `m4-04c-request-m27` | Claude | `pg_migrations.py` | sau L0-2d | Chờ kiểm — 2 lượt đã commit; lead chạy test lượt 2 |
| L0-2h | Rà `m4b2`, `m4b3` (chưa terminal): còn dùng được gì | Codex | — | — | Chờ slot |
| L0-3 | Sửa nhóm ERROR còn lại theo nguyên nhân gốc L0-1 | theo nhóm | tùy nhóm | sau L0-1, L0-2* | Chờ |
| H5 | Gộp `hop-nhat` → `chinh`, đẩy GitHub | lead | — | sau L0-1, L0-2*, Anh xem `NEN-TEST.md` | Chờ Anh |
| BG-1 | Báo giá gói 1: BG-01…05 (lịch 4 cột, dòng tổng, tính tự động, tổng tự tính, bỏ mã kỹ thuật) | Claude | `crm_g.*` | sau L0-2d (Anh đã ra lệnh 24/10) | Chờ L0-2d |
| BG-2, BG-3 | Báo giá gói 2 (BG-06…12), gói 3 (BG-13, 14) | Claude | `crm_g.*` | sau cổng A gói 1 | Chờ |
| MOD | Lập hàng đợi lát cho các module còn lại đã chốt thiết kế: CRM 42 (danh sách hợp đồng, 6 mục), M4 phần còn lại (công nợ 03B, Request thật để sau), #40 M2-00, #41 E1-MUA; module chưa chốt → checklist + hỏi Anh | lead | — | song song L0-* | Xong 24/10 → mục 1b |
| (theo MOD) | Các lát backend/SQL/test của từng module → ưu tiên Codex; màn hình/luồng → Claude | Codex / Claude | theo lát | trên hop-nhat (xem mục 1b) | Theo mục 1b |
| D | Dọn thư mục (chuyển lưu trữ) | lead | — | sau H5 | Chờ |

Ưu tiên khi có slot trống: nhận xét của Anh → lỗi review → lát theo thứ tự bảng.

## 1b. Hàng đợi theo module (lát MOD, lead lập 24/10)

Căn cứ: lệnh của Anh 24/10 (mọi module đã chốt thiết kế; M9 dừng) · kiểm kê chỉ đọc 24/10 (đối chiếu thiết kế với code trên `hop-nhat` và `luu/*`).

**Phát hiện chặn (đã kiểm lại):** `hop-nhat` không import được `ha_tang\pg_migrations.py` — cuối file đăng ký M0024 từ `m4\sql_duyet.py` (chỉ có ở `luu/m4-02c-backend`) và M0025 từ `k2\sql_crm_kiem_hd.py` (**không có ở nhánh nào**). Cũng không có ở nhánh nào: `k2\crm_kiem_hd.py`, `k2\crm_doi_chieu.py`, `m4\request_api.py`, `m4\sql_request_nhap.py`, `tests\test_crm_kiem_hd*.py`, `tests\test_m4_03a_pg.py` — chỉ còn trong bản chụp `var\codex-dieu-phoi\`. Đây nhiều khả năng là nguồn chính của ERROR H4 (L0-1 xác nhận). → Lát **P0** đứng trước gần như mọi lát CRM/M4/Báo giá.

**Lead đã quyết (không cần hỏi Anh):**
- BG-02 (Σ% ≠ 100 → mờ cả In và Chuyển) và BG-04 (cho ghi đè tổng, có cảnh báo + nhật ký) làm đúng TL 45 — TL 45 (23–24/10) mới hơn handoff 41-03.
- BG-01 mốc "Sau ký + n ngày": lưu mã sự kiện `SAU_KY` + số ngày, hiển thị tiếng Việt; không đổi schema.
- M2-00: giữ hợp đồng RPC đã code (`/api/profiles|start|status|reconcile|events`) thay cho mô tả `/api/start` + SSE cũ — tận dụng code.
- E1-MUA chạy song song M2-00 (lệnh 24/10 thay thứ tự tuần tự 21/10; hai bên không chung file).
- CRM S1 bộ lọc nhớ theo người: lưu trên trình duyệt theo mã người dùng, không thêm bảng.
- File máy chủ dùng chung thật là `src\kho_tri_thuc\giao_dien\server.py` (CLAUDE.md mục 4 ghi thiếu `giao_dien`); khóa thêm `giao_dien\m4.py`, `assets\app.js`, `index.html`, `style.css`.

**Hàng đợi** (Worker: lead chọn theo loại việc; Codex sửa + test, lead commit):

| Mã | Module · việc | Worker | Phụ thuộc | Khóa file chung | Trạng thái |
|---|---|---|---|---|---|
| P0 | Nền · khôi phục file chưa vào git (theo L0-2i; L0-2d đã liệt kê 11 file G6A/G5-B + `m4\sql_duyet.py` + `crm_g.js` bản 27a0d3db — phải vào TRƯỚC BG-1) + gộp `m4-02c-backend`, `m4-04c-request-m27` (= L0-2c) + chuỗi migration import được: 24 duyệt · 25 G6A · 26 KT · 27 Request nháp · rồi master-reuse, 03B | Claude Opus | L0-2d, L0-2i | `crm_g.js`, `m4\*` (chỉ thêm file) | Xong 24/10 — gộp 1c5c67a; module lỗi nạp 29 → 1 |
| BG-1a | CRM · Báo giá gói 1 phía máy chủ: parse ô thông minh (`%`, dấu chấm/phẩy VN), BG-04 ghi đè + nhật ký, nhãn tên thay mã, mốc chuẩn | Codex | P0 | `crm_g.py` | Xong 24/10 — gộp 5a8042a (review Đạt, vòng 2 sửa 4 điểm) |
| BG-1b | CRM · Báo giá gói 1 màn hình: BG-01…05, đo số ô trước/sau → **cổng A** | Claude | BG-1a | `crm_g.js` | Đang code (24/10, từ lat/bg-1a) |
| BG-2a | CRM · Báo giá gói 2 máy chủ: profile loại hình v3 (BG-06/11), tìm khách (BG-08) | Codex | BG-1a | `crm_g.py` | Chờ |
| BG-2b | CRM · Báo giá gói 2 màn hình: BG-06, 07, 08, 10, 11, 12 | Claude | cổng A gói 1, BG-2a | `crm_g.js` | Chờ |
| BG-2c | CRM · Báo giá BG-09 lô/căn từ danh mục | Codex + Claude | **Anh chọn nguồn danh mục** (hỏi sau cổng A gói 1) | `pg_migrations.py` | Chờ Anh |
| BG-3 | CRM · Báo giá gói 3: BG-13 thanh nút, BG-14 ngăn kiểm, số đo CHANGELOG → **cổng B** | Claude | BG-2b | `crm_g.js` | Chờ |
| C1 | CRM 41 · G6A/G5 dịch vụ (`crm_kiem_hd`, `crm_doi_chieu`) chạy test thuần + PG DEMO | Codex | P0 | — | Chờ |
| C2 | CRM 41 · hộp KT kiểm → Hiệu lực / Trả lại, xử lý lệch | Claude | C1 | `crm_g.*` | Chờ |
| C3 | CRM 42 · read-model danh sách hợp đồng `GET /api/crm/hop-dong` (trạng thái, người phụ trách, thẻ W1–W5; ô Junsky tạm "chưa có sổ") | Codex | P0 | `server.py` | Chờ |
| C4 | CRM 42 · menu "Hợp đồng bán hàng" 6 mục + S1 danh sách (thẻ, cột, lọc) | Claude | C3 | `index.html`, `app.js` | Chờ |
| C5 | CRM 42 · S2 tab Tổng quan / Nguồn & tham số / Lịch nghĩa vụ | Claude | C4 | `crm_g.*` | Chờ |
| C6 | CRM 42 · S2 tab Thu tiền (+S8) / Phụ lục / Bản ký / Lịch sử | Claude | C5; ô Junsky chờ kiểm RLS | `crm_g.*` | Chờ |
| C7 | CRM 42 · S9 báo cáo, file soát | Codex + Claude | C6; tỷ lệ kiểm mẫu chờ Q-SAMPLE | — | Chờ |
| M2a | M2-00 · = L0-2e gộp `m2-00b-fix01` | Codex | — | — | Xong (= L0-2e) |
| M2b | M2-00 · `manifest.py`, `chinh_sach_tien_te.py` (POLICY-TIENTE-01) + ca M2-00-06/10 | Codex | — | — | Xong 24/10 — gộp 4e1f6bb (review Đạt, vòng 2 sửa 2 điểm) |
| M2c | M2-00 · `nhan.py` nhận theo manifest (identity, revision/xung đột, KHONG_XML_GOC → bảng kê) nối `k2\hoa_don.py` | Codex | M2b | (migration nếu cần → khóa) | Đang code (24/10, Codex) |
| M2d | M2-00 · `hoi_cuu.py` manifest hồi cứu 33 tháng, fixture giả | Codex | M2b | — | Chờ |
| M2e | M2-00 · nút "Tải từ cổng thuế" + route + cấu hình | Claude | M2a, M2c | `server.py`, `app.js`, `index.html` | Chờ |
| M2f | M2-00 · ca -03/-07/-09 trên cổng thật, áp bản vá vào #7 thật | Anh | M2e | — | Chờ Anh (cần lệnh riêng: gọi cổng thuế thật) |
| E1-1 | E1-MUA · đăng ký 5 loại + DV trong `CATALOG_COMMON`, `danh_muc_theo_loai`, từ chối loại lạ; test XD nguyên trạng | Codex | L0-2f | — | Chờ |
| E1-2 | E1-MUA · quy tắc theo loại + `phien_ban_danh_muc` | Codex | E1-1 | — | Chờ |
| E1-3 | E1-MUA · bảng TT-05/TT-20 trên `source6_docx_tables` | Codex | E1-1 | — | Chờ |
| E1-4 | E1-MUA · màn danh mục Sửa + nhật ký; mở loại ở trích chung #6 | Claude | E1-1 | `app.js` | Chờ |
| E1-5 | E1-MUA · áp vào #6 thật, chấm 2 hợp đồng thật offline | Anh | E1-2 | — | Chờ Anh |
| M4-2 | M4 · Nghiệm thu & chi phí dự án · UI 02C duyệt/PDF: đối chiếu với fix01 + 3 lỗi đã tái hiện (gồm L0-2b) | Claude | P0 | `m4\*` UI | Chờ |
| M4-3 | M4 · 03A kế toán nghiệm thu: M0026 + test + xác minh màn | Codex | P0 | — | Chờ |
| M4-4 | M4 · 03B căn cứ nghiệm thu ↔ hóa đơn: L0-2a + migration + test PG | Codex | L0-2a, M4-3 | `pg_migrations.py` | Chờ |
| M4-5 | M4 · 03B route + panel trong màn kế toán nghiệm thu | Claude | M4-4 | `giao_dien\m4.py` | Chờ |
| M4-6 | M4 · 04 Request nháp: khôi phục `request_api.py`, `sql_request_nhap.py`, M0027; giữ CHUA_CAU_HINH, **không gọi Request thật** | Codex | P0 | — | Chờ |
| M4-7 | M4 · migration master-reuse + rà `m4b2`/`m4b3` (= L0-2h) | Codex | P0 | — | Chờ |

**Chưa chốt thiết kế — lead soạn checklist, hỏi Anh bằng bảng chọn khi tới lượt (không hỏi dồn):**
- **Báo giá → Ký (hỏi cùng phiếu cổng A gói 1):** bước kiểm lịch khi Ký (`k2/sql_crm_kiem_hd.py` `crm_kiem_lich_ky`) vẫn tính tổng = đơn giá × diện tích và đòi % hữu hạn → báo giá có tổng ghi đè, hoặc chia tiền không tròn %, qua được In/Chuyển nhưng bị chặn ở Ký. Phương án: (a) giữ chặn ở Ký (kế toán đối chiếu lại); (b) lát SQL + migration cho bước Ký đọc tổng ghi đè và kiểm Σ tiền. Ngoài phạm vi TL 45 (không đụng Ký).
- M4 · ghi nhận công nợ nội bộ (kế toán xác nhận giá trị/thuế → công nợ): chưa có thiết kế gói; 03B chỉ là quan hệ căn cứ.
- BG-09 nguồn danh mục lô/căn (bảng mới + dữ liệu DEMO, hay kế toán nhập).
- CRM: Q-B (luồng B do CFO hay KT), Q-SAMPLE, Q-RETURN, Q-INPUT, Q-PII, Q-UI; quyền xem công nợ Junsky của Bán hàng.
- Báo giá: số ngày hết hạn mặc định (TL 42 §16) — không chặn code, dùng tạm 30 ngày có ghi chú.

**Thứ tự slot:** (1) L0-2e, L0-2f, M2b cho Codex khi rảnh; (2) P0 ngay khi L0-2d + L0-2i xong; (3) BG-1a → BG-1b (cổng A sớm nhất); song song M2c/M2d, E1-1…3 (không chung file); (4) C1→C2, M4-2…M4-7; (5) phần còn lại theo phụ thuộc.

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
- L0-2a: sandbox Codex trên Windows **không ghi được `.git`** dù có `--add-dir` → Codex áp fix01 rồi dừng; lead commit fix01 và áp fix02→04 (bản kế nhiệm thắng, khớp byte). Từ nay handoff Codex ghi: **Codex sửa + chạy test, không commit; lead commit** theo danh sách Codex báo.
- Phát hiện: `tests/test_m4_03a_pg.py` không có ở nhánh nào, chỉ trong `var\codex-dieu-phoi\*frozen*`. Mở lát L0-2i để dò hết file bị sót.
- L0-2d (24/10): worker đứng 600 giây (mở server ở chế độ thường) → lead nối lại, xong. Gộp theo dòng dõi (m4-three trước G5) vì crm-g4 trên hop-nhat là bản cũ hơn nền chinh. CRM DEMO cần `<DataRoot>\crm-demo\runtime.local.json` (Python + thư mục thư viện có psycopg) và `ket-noi.local.json` (kết nối PG DEMO, không mở) → lát L0-4. Lead đã tắt server 8781.
- Quy tắc mới cho worker: mọi lệnh có thể quá 2 phút và mọi server phải chạy nền (`run_in_background`), nếu không agent bị ngắt sau 600 giây.
- L0-2i xong: phần lớn file bị sót đến từ job `m4-financial-basis-a-20261023-01` (không có trong 36 gói của TAN-DUNG-CODE) — P0 phải xác định gói này là gì trước khi khôi phục.
- L0-1 xong (24/10): bảng nền ở `NEN-TEST.md`. Số H4 (275 ERROR) không tái hiện được trong worktree sạch → dùng nền mới, bỏ số H4. Sau P0 + L0-3a phải **đo lại nền** bằng cùng script (module bị N1 che sẽ chạy thật).
- L0-2d review Codex vòng 1: #1 M0023 — lead tính `_hash` trên bản xuất tạm: L0-2d = chinh (43 câu, 574129b2), hop-nhat 1502fe7 (42 câu) là hồi quy H3 → không lỗi; #2 duyệt mở phạm vi `k2\crm_ky_ket.py`. Không cần vòng 2.
- L0-3a: sandbox Codex không đọc được `var\web\crm-demo\runtime.local.json` và không checkout lại được → lead tự chuyển 97 file bị ghim sang LF trên đĩa, đưa 19 fixture DEMO vào git (đã kiểm: 17 có DEMO, 2 file lỗi cố ý; 0 nghi thật), chạy lại toàn bộ test có `--runtime`.

- 24/10: Anh chốt CSDL CRM DEMO riêng cho lập trình → lát L0-4b. Lần thử L0-4 trên bản sao `chinh` đã nâng CSDL DEMO dùng chung lên schema 23 (đúng `chinh`) và nạp thêm dữ liệu mẫu — đã ghi trong TRANG-THAI.
- 24/10: Anh hỏi Codex có chạy không — đã chạy 6 lần `codex exec` (~474 nghìn token, gpt-6.1-sol, tài khoản ChatGPT trong `~/.codex`); nhật ký ở `~/.codex/sessions/2026/10/24/`.
- 24/10: BG-1b tách nhánh từ `lat/bg-1a` để chạy song song với review BG-1a (không ai đứng chờ); nếu review BG-1a có sửa, BG-1b gộp lại trước cổng A.
- 24/10: M2b — 3 điểm 'Để sau' của review chuyển sang M2c: số thực dạng mũ trong thành phần khóa (Python/JS in khác), file lạ ngoài .xml/.pdf trong thư mục run, package-data cho `quy_tac/*.json` khi đóng gói.
