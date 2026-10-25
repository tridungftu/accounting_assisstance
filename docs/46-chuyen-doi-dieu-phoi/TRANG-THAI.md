# Trạng thái — lead Claude Code cập nhật khi lát đổi trạng thái

Trạng thái lát: Đang code → Chờ kiểm → Chờ Anh (cổng A/B) → Sửa → Xong · Bị chặn. Kế hoạch và hàng đợi đầy đủ: `4-KE-HOACH-LEAD.md`. Nền test: `NEN-TEST.md` mục 0b — **nền v4** (mục 0, 25/10): 1501/23/44/362, **0 treo**.

## Lát đang chạy — 25/10: tối đa 3 worker lập trình; **từ 26/10 (CD-004): tối đa 6 = 2 suất Claude (ưu tiên review) + 4 Codex lát nhỏ ≤ 3 file** (lên 4 Codex khi PostgreSQL DEMO đã chạy dịch vụ Windows). Mọi lát Codex: `kiem-nhanh` → `review-lat` (Opus) → gộp; ngừng giao khi > 2 lát chờ review

| Lát | Việc | Worker | Nhánh · worktree | Giao lúc | Trạng thái |
|---|---|---|---|---|---|
| BG-1d | CRM · Báo giá màn hình 2 bước (BG-1b + BG-1d) | Claude Sonnet · review Codex | `lat/bg-1d` · DEMO 8791 | 25/10 | Chờ Anh — cổng A xem lại (`PHIEU-CONG-A-BAO-GIA-XEM-LAI.md`) |
| DA-2 | CRM · màn Dự án đang bán (xem + thêm/sửa; ẩn luồng CFO) | Codex · review Claude | `lat/da-2` (= bg-1d + da-1) | 25/10 | Xong code đến DA-2c (33a2e29); review Đạt; chờ BG-1d qua cổng A để gộp |
| M4-5a | M4 · Nghiệm thu & chi phí dự án · 03B máy chủ: khai một phần bằng số tiền + gợi ý hóa đơn — **M0033** | Codex · review Claude | `lat/m4-5a` | 25/10 19:16 (vòng 3) | Vòng 3 xong (7ef9e21, Codex 104/104 thuần); đã nhận nền mới → lead chạy bộ M4 có PostgreSQL → `kiem-nhanh` → gộp |
| DA-3a | CRM · Báo giá nạp mặc định từ Dự án đang bán, ghi nhận khác tiêu chuẩn | Codex · review Claude | `lat/da-3a` (c077a83) | 25/10 | Review Đạt → **vòng 2 đang code** (Codex 19:33): B1 — chỉ chặn dự án Ngừng bán khi tạo mới/đổi dự án/có lô; sau đó lead chạy ca PostgreSQL |
| T-MIG2 | Test PostgreSQL theo chuỗi migration mới | Codex | `lat/t-mig2` (26e9c35) | 25/10 | `t21` hết sau **L0-9b** (gốc: 8 fixture L11 bị L0-9 ép LF, lệch ghim SHA) — `test_crm_k2` chỉ còn lỗi có sẵn của nền; chờ chạy lại cả bộ PG → `kiem-nhanh` → `review-lat` → gộp |
| UI-1 | Khung lưới icon dùng chung + áp CRM 6 phần (CD-002) | Claude Sonnet | `lat/ui-1` (= da-2 + hop-nhat) | 25/10 | **Đang code** (worker Claude Sonnet, giao 19:21) |
| UI-2 | Máy chủ `GET /api/khung/module/crm` (CD-002) | Codex | `lat/ui-2` | 25/10 19:16 | Xong code (95ef025, 16/16 test mới) → lead chạy CRM có PostgreSQL → `kiem-nhanh` → `review-lat` |
| M2j-b | Sửa nóng `app.js`: bộ lọc "Lần tải" (M2j) làm vỡ 16 bộ test node (DOM giả không có phần tử cha) | Lead | `hop-nhat` | 25/10 19:08 | **Xong** — sửa 1 dòng; 16 → 7 bộ node không đạt, cả 7 cũng không đạt trên nền v4 (lỗi có sẵn) |

## Cổng AI (CD-001, TL 48 — Anh chốt 25/10: Local luôn có, Cloud chỉ qua Mask file v2)

| Lát | Việc | Worker | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| AI-0a | Tạm khóa Cloud trực tiếp của engine #6 **bản độc lập** (`D:\Claude\Ho tro review ho so xay dung\review_xaydung`; mã ngoài git — lead sao lưu kèm SHA vào `LUU-TRU\ai-0a-sao-luu-review_xaydung-20261025-175621`) | Claude (Codex lỗi sandbox) | — | **Xong** 25/10 — 18 ca test mới đạt; 9 test Cloud cũ thất bại đúng thiết kế → AI-3 |
| AI-0b | Tạm khóa Cloud trực tiếp ở bản engine trong repo (`m4\review_goc\trich_xuat\cloud.py`, `ai_cloud.py`) + cập nhật ghim SHA `nguon_review.py` | Codex | — | **Xong, đã gộp** (06fa717) |
| AI-1 | Cổng Local AI (`tri_thuc\ai_cuc_bo.py`) gọi được LAN/Tailscale, kiểm tra như `privacy\local_ai.py` của Mask v2; test bằng máy AI giả | Codex | — | **Xong, đã gộp** (cfdf33c) — 40/40; review-lat sau gộp **Đạt**, 3 Nên sửa → lát **AI-1b** (Codex, chờ chỗ trống: `localhost`, LM Studio `/api/tags`, nhớ lỗi 15 giây, chuẩn hóa cài đặt khi đọc) |
| MASK-1 | Chế độ API của Mask v2 (che / mở che / còn sót; khóa Bearer; chỉ 127.0.0.1) — làm trong thư mục Mask v2 theo `CLAUDE.md` của nó (không git, CHANGELOG, test + benchmark độ phủ không giảm; không đọc/sửa `data\`, `*.maskvault`, `*.maskkeep`, `*.key`) | Claude Opus | — | **Xong code** (Mask v2 2.7.0, 19 test mới; benchmark không giảm) → review Claude đang chạy; review Opus vòng 1 **Không đạt** (1 Chặn: định danh dạng nhóm 3 số bị bỏ qua) → vòng 2 **xong 19:48** (387 test đạt; lỗi Chặn đã sửa + làm QD-24: danh mục mở cho API đến khi tắt Mask, nút khóa ngay, siết quyền tệp khóa) → review Opus vòng 2 đang chạy; Anh đã chốt QD-23 (cụm mới → tệp riêng mã hóa + màn duyệt, lát MASK-3) và QD-24 (danh mục mở cho API đến khi tắt Mask — làm trong vòng 2) |
| MASK-2 | Đưa "định danh đã biết" và kiểm `dau_vet` của `AnDanh` vào lõi Mask v2; đo lại độ phủ | Claude | MASK-1 | Chờ |
| AI-2 | Cổng AI dùng chung: định tuyến loại việc, Cloud qua Mask API, nhật ký `nhat_ky.cong_ai_goi`, công tắc tắt Cloud | Claude | AI-1, MASK-1 | Chờ |
| AI-3 | Engine #6 (độc lập + bản trong repo) chuyển Cloud sang cổng AI; bỏ `AnDanh`, `goi_api` riêng | Codex | AI-2, MASK-2 | Chờ |
| AI-4 | Mở Cloud theo TL 48 §1.5; đo độ chính xác Local theo loại việc; lịch giảm tỷ lệ kiểm xác suất **Anh đã đồng ý (§1.6)**: bắt đầu 20%; ≥ 90% trên 50 lượt gần nhất → 10%; ≥ 95% trên 100 lượt → 5%; tối thiểu 5%, không về 0; tụt dưới 90% → tự về 20% và báo lead | Claude | AI-3 qua review | Chờ |

Quy tắc áp cho mọi lát từ 25/10 (CD-001 việc 3): không lát nào viết code gọi thẳng `api.anthropic.com`/`api.openai.com` hoặc thêm bộ che riêng — lead kiểm bằng grep ở cổng kiểm soát.

## Trang chủ lưới icon (CD-002, TL 49 — Anh chốt 25/10, phương án B; ưu tiên sau AI-0, trước lát CRM mới)

| Lát | Việc | Worker | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| UI-1 | Khung dùng chung: trang chủ module (thẻ tổng quan + lưới icon), thanh icon trái thay menu chữ; áp CRM 6 phần (màn bên trong giữ nguyên) | Claude | — (dựng trên `lat/da-2` vì khóa `crm_g.js`/`style.css`) | Đang code (19:21) |
| UI-2 | Máy chủ `GET /api/khung/module/crm` đã lọc quyền + đếm việc chờ (nguồn sẵn có) — hợp đồng dữ liệu `HOP-DONG-DU-LIEU-KHUNG-LUOI.md` | Codex | — (song song UI-1) | Xong code 19:30; đang kiểm |
| UI-3 | Trang chủ hệ thống: icon module, tìm nhanh, thanh cố định 4 mục, M9 "Tạm dừng" | Claude | UI-1 | Chờ |
| UI-4 | Áp khung cho M2, M4, Duyệt chung K5 | Claude/Codex | Cổng A của UI-1 | Chờ |

## Nhật ký lát (CD-003 — mỗi lát giao/đóng một dòng; model Codex theo cấu hình `gpt-6.1-sol`, mức suy luận ghi theo lần giao)

| Lát | Worker | Model | Bắt đầu | Kết thúc | Vòng review | Test (so nền v4) |
|---|---|---|---|---|---|---|
| M4-5a v1–v2 | Codex | gpt-6.1-sol · high | 25/10 17:25 | 18:17 | 1 (Claude Sonnet) — Đạt | Xanh — 0 mã lỗi mới (M4); PG chưa chạy |
| DA-3a | Codex | gpt-6.1-sol · high | 17:50 | 18:17 | 1 (Claude Sonnet) — Đạt | Xanh — 0 mã lỗi mới; PG chưa chạy |
| T-MIG2 v1–v2 | Codex | gpt-6.1-sol | 17:44 | 18:44 | 0 | Đỏ — 1 mã lỗi mới |
| C3c | Codex | gpt-6.1-sol · high | 17:52 | gộp 19:03 | 0 (sửa theo review C3) | Xanh — 43/43 có PostgreSQL (lead chạy) |
| MASK-1 | Claude | Opus | 18:39 | 18:59 | review Opus đang chạy | Mask v2: 378 đạt / 1 lỗi có sẵn; benchmark không giảm |
| AI-1 | Codex | gpt-6.1-sol · high | 18:45 | gộp 18:58 | 0 (lead đọc diff mạng) | Xanh — 40/40 |
| M2s-b | Codex | gpt-6.1-sol · low | 18:45 | gộp 19:02 | 0 | Xanh — node 7/7 |
| Review M4-5a + DA-3a | Claude | Sonnet | 18:40 | ~18:55 | — | — |
| M2j-b (sửa nóng) | Lead | Opus | 19:08 | 19:15 | 0 | Xanh — node về đúng nền v4 (7 bộ lỗi có sẵn) |
| M4-5a v3 | Codex | gpt-6.1-sol · high | 19:16 | 19:20 | (vòng 1 Đạt) | thuần 104/104; PG đang chạy |
| UI-2 | Codex | gpt-6.1-sol · high | 19:16 | 19:30 | — | test mới 16/16; CRM PG chờ lượt |
| Review MASK-1 | Claude | Opus | 19:17 | 19:26 | vòng 1 | Không đạt — 1 Chặn |
| MASK-1 vòng 2 | Claude | Opus | 19:35 | 19:48 | review vòng 2 đang chạy | Mask v2: 387 đạt / 1 lỗi có sẵn; benchmark không giảm |
| Review MASK-1 vòng 2 | Claude | Opus | 19:48 | 19:52 | vòng 2 | **Đạt** — 2 Nên sửa → MASK-2 |
| AI-1b | Codex | gpt-6.1-sol · high | 19:49 | — | — | — |
| DA-3a v2 | Codex | gpt-6.1-sol · high | 19:33 | — | — | — |
| L0-9b (fixture L11 đúng byte ghim) | Lead | Opus | 19:24 | 19:31 | 0 | Xanh — checkout mới 19/19 ghim; `t21` hết |
| UI-1 | Claude | Sonnet | 19:21 | — | — | — |
| review-lat sau gộp AI-1 + C3c | Claude | Opus | 19:22 | 19:29 | vòng 1 | Đạt cả hai; AI-1: 3 Nên sửa (→ AI-1b); C3c: Nên sửa test quá hạn PG (→ C3d) |

## Lát đã xong (24/10)

| Lát | Kết quả | Gộp vào hop-nhat |
|---|---|---|
| L0-2h | Rà `luu/m4b2`, `luu/m4b3` (Codex, chỉ đọc): **không gộp** — phần dùng được (`docx_an_toan.py`) đã có trên hop-nhat giống hệt; delta còn lại đưa code/test về bản cũ (bỏ hàm review/chứng từ, bỏ UNIQUE cần cho FK M17, helper test lỗi `lam() got multiple values for argument ten`). Nhánh `luu/*` giữ nguyên, không xóa | — |
| L0-2g | Testfix C18 review basis M4 (bản kế nhiệm `m4_02a_basis_async.cjs`): 31/32 → 32/32 | fdc3c2e |
| C1a + T-MIG | CRM 41 · M0032 gắn SQL G5-B (đối chiếu bản ký ↔ bản sinh, có sẵn nhưng chưa từng vào chuỗi migration) + test bỏ ghim tổng migration; review Codex Đạt 4/4; PostgreSQL thật 0 mã lỗi mới, +36 ca | 174e9e0 |
| L0-8c | Bộ chạy test: cưỡng hạn cây tiến trình (Job Object) — sửa sự cố test_crm_k2 treo 4.588 giây; nạp bảo vệ .pth theo đường dẫn tuyệt đối; PostgreSQL test_crm_* 5.742 → 125 giây | 433ec7e |
| L0-8 | Bộ chạy test `--pg-demo` (CSDL tạm có sổ sở hữu, lọc bí mật) — review vòng 1 Codex 5 Chặn → vòng 2 Claude Đạt; chạy thật cả bộ 1577 đạt | ae0d3b3 |
| DA-1 | CRM · Dự án đang bán máy chủ + M0031 (phiên bản, phí, lô/căn, G7 áp dụng ngay, thuế QD-20 giữ khi cập nhật) — PostgreSQL thật 55/55 | 691b959 |
| M2h-c | M2-00 · Tải tất cả công ty: 4 điểm sau review (dừng chưa xác nhận, lỗi luồng, mất kết nối); 248 đạt | 4f4e18c |
| M2h | M2-00 · "Tải tất cả công ty" (ca M2-00-02): hàng đợi tuần tự có hạn chờ, hủy, xác nhận; review Claude vòng 1 Cần sửa (kẹt khóa) → vòng 2 Đạt; 243 đạt, 0 mã lỗi mới | aa7ad23 |
| E1-4b | E1-MUA · máy trích dùng danh mục đã sửa (chuỗi nhật ký) + dọn tệp tạm; XD không đổi; 70 đạt, 0 mã lỗi mới | 58e8391 |
| E1-4a | E1-MUA · lệnh `python -m trich_xuat danh-muc xem|sua` + nhật ký nguyên tử; 65 đạt, 0 mã lỗi mới | 3fc5998 |
| M4-6 | M4 · Nghiệm thu & chi phí dự án · 04 Request nháp nối máy chủ (`gan/go_request_nhap` + 3 route, giữ CHUA_CAU_HINH); review Codex Đạt; lead chạy test_m4_*: 467 đạt, 0 mã lỗi mới | 0737071 |
| L0-9 | EOL checkout đúng SHA fixture (15 ghim CRLF → eol=crlf, ZIP -text); worktree mới khớp byte thư mục chính 14/14; 8 ghim L11 không khớp cả LF lẫn CRLF ghi riêng | c6ef9a6 |
| BG-1c | CRM · Báo giá máy chủ theo cổng A: Tổng VND = đơn giá × tỷ giá × diện tích (làm tròn một lần) + bằng chữ; tỷ giá mặc định 26.000 trong cấu hình chung (kế toán sửa, nhật ký); In sơ bộ; Chuyển cần khách + phí; M0030 bước Ký. Review Codex: 2 Chặn + 1 Nên sửa, vòng 2 sửa đủ; Python = SQL 9/9 trên PostgreSQL thật; 170 đạt, 0 mã lỗi mới | ec73112 |
| E1-3 | E1-MUA · bảng TT-05 (hàng/đơn giá) và lịch TT-20 từ DOCX trong bản vá #6; ô mơ hồ để trống + cờ rà soát; XD không đổi; 13 test mới | a7431d1 |
| E1-2 | E1-MUA · quy tắc theo loại hợp đồng (bảng quy tắc; XD giữ nguyên — 9 đầu vào trùng hàm gốc) + phiên bản danh mục, trong bản vá #6; 42/0/0 | b391e09 |
| M2e | M2-00 · nút "Tải từ cổng thuế" (route mỏng + giao diện + cấu hình); review Codex: 3 Chặn an toàn đã sửa vòng 2; 266 đạt; chạy với bộ tải giả — ca thật là M2f | 3b7f9e8 |
| M4-4/7 | M0028 master dùng chung + M0029 03B ghi nhận chung (append, 29 migration); áp thật 0→29 và 27→29; review Codex Đạt cả 4 tiêu chí | 3d0be04 |
| L0-7 | Engine #6 nạp sẵn openpyxl/numpy ở luồng chính tiến trình con → hết treo lệnh trích đầu (A/B: 1,8 s vs 503); .gitattributes review_goc (35/35 pin khớp ở clone mới); seed duyệt viên M4 cho DEMO; review Codex: 0 Chặn | d4eb6a5 |
| M2d | M2-00 · manifest hồi cứu HOI_CUU (chỉ đọc thư mục cũ); review Đạt (~45 ca tấn công đường dẫn bị chặn); vòng 2: gốc hồi cứu tin cậy, junction, run_id theo tên thật, chặn chuỗi quá dài; 173/0/0/1 | da3d666 |
| L0-6 | Engine #6 DEMO: nguyên nhân gốc — openpyxl tự import numpy (Python hệ thống) lần đầu ở luồng worker khi tiến trình con đang phục vụ → kẹt, timeout 60s. Vá tạm ở launcher worktree (chặn numpy), đồng bộ byte-pin review_goc; dựng 2 đợt DEMO M4 (cổng 8786). **DEMO của Anh và `MỞ PHẦN MỀM.cmd` có thể treo 60s ở lệnh trích đầu** → sửa sản phẩm ở L0-7 | 1d1c12f |
| L0-3b | Hết treo `test_source6_g5_e5`: mock dùng chung tham chiếu yêu cầu làm lệch niêm phong → client chờ 30 phút không nghỉ; sửa mock (deepcopy, đồng hồ giả) + 2 test sai đầu vào; module 16/0/0/2 | 146a28b |
| E1-1 | E1-MUA · sổ đăng ký 6 danh mục tham số hợp đồng mua trong bản vá #6, ghim SHA, không fallback XD; 13 test mới đạt; tệp .xlsx áp vào #6 thật ở E1-5 | d5fe3cc |
| L0-3c | 12 test lỗi thời N5 cập nhật (không nới ý nghĩa); pin crm_giao_ket theo BG-1a; toàn bộ test: ok 1276→1408, ERROR 34→22, FAIL 57→44 → **nền v3** | ad7d3d4 |
| M2c | M2-00 · nhận hóa đơn theo manifest qua đường K2 sẵn có; review Đạt, vòng 2 sửa 4 điểm (độ phủ, giữ chờ theo mục, thiếu bảng kê, số 0 đầu SHDon); 141/141 | b190569 |
| M4-2 | M4 · giao diện Duyệt đợt & PDF: hop-nhat đã có logic fix01 (3 lỗi); thêm 15 dòng style + test hồi quy fix01 12/12 (chứng minh bắt lỗi trên bản chưa sửa). Chưa chụp được màn có dữ liệu: engine #6 DEMO ngắt sau lệnh trích đầu (→ L0-6) | ff9503f |
| L0-2c | M4 · Nghiệm thu & chi phí dự án: gộp backend duyệt/PDF (13 xung đột, giữ HN mới hơn) + đăng ký M0026/M0027 (27 migration, chỉ append); ok 728→757, ERROR 27→18; Request M4 103/0 | c4deb00 |
| BG-1a | CRM · Báo giá gói 1 máy chủ: ô thông minh, ghi đè tổng có cảnh báo + nhật ký, nhãn tên, mốc chuẩn; vòng 2: % xấp xỉ cho dòng nhập tiền, chặn Chuyển ở máy chủ, định dạng tiền, số kiểu Việt; 85 đạt, 0 lỗi mới | 5a8042a |
| M2b | M2-00 · đọc/kiểm manifest + POLICY-TIENTE-01 v1 (ca M2-00-06, -10, 3 ràng buộc); review Claude Đạt, vòng 2 sửa 2 điểm lệch TL 43 §6; 67/67 | 4e1f6bb |
| L0-4b | CSDL CRM DEMO riêng cho lập trình (`-CsdlRieng`); CSDL DEMO của Anh không đổi (schema 23, băm trước = sau) | 550f573 |
| P0 | Khôi phục 24 file chưa vào git (CRM G6A/G5-B, M4 duyệt/Request/03A); `pg_migrations` nạp được (25); module lỗi nạp 29 → 1; ok 501 → 1067; không test vốn đạt nào hỏng | 1c5c67a |
| L0-3a | Runner: gốc repo vào sys.path + `--runtime` (Python có psycopg); `.gitattributes` cho file bị ghim byte; 19 fixture DEMO vào git; trên nhánh lát: ERROR 112 → 62, FAIL 20 → 6 | 7b114e2 |
| L0-4 | `tools\mo_demo_worktree.ps1`: mở DEMO cho worktree, chặn khi CSDL CRM DEMO dùng chung có thể hỏng | 7cbc41b |
| L0-1 | Nền test: chinh 711/25/31/272 · 0 treo; hop-nhat 501/112/20/140 · 1 treo; 5 nhóm nguyên nhân | a1da3d4 |
| L0-2a | Common identity fix01→04, khớp byte bản fix | 73deacb |
| L0-2d | CRM m4-three + G5; khôi phục hồi quy H3 (M0023 về đúng checksum `chinh`) | b2fd07c |
| L0-2e | M2-00 fix01 + `config.js` bị sót | 3a2b083 |
| L0-2f | Source6 ordered-fix01; không hết treo → L0-3b | d07117a |
| L0-2i | 27 file chưa vào git, 26 file có bản mới hơn ngoài git | 8b4670f |

Worktree đo nền: `.claude/worktrees/nen-chinh-59b7d8e` (chinh) · `.claude/worktrees/nen-hop-nhat-v2` (hop-nhat 7b114e2).

## Khóa file dùng chung (mỗi lúc một lát)

| File | Lát giữ |
|---|---|
| `src\kho_tri_thuc\giao_dien\server.py` | — |
| `giao_dien\m4.py` | — |
| `nguon\trich6_host.py`, `tools\chuan_bi_crm_demo.py`, `.gitattributes` | — |
| `giao_dien\assets\app.js`, `index.html`, `ha_tang\config.py` | — |
| `ha_tang\pg_migrations.py` | M4-5a (M0033; M0031 DA-1 + M0032 G5 đã gộp) |
| `giao_dien\crm_g.py` | — (C3 chờ gộp) |
| `k2\crm_giao_ket.py` | — (DA-3 giữ khi bắt đầu) |
| `giao_dien\assets\crm_g.js`, `style.css` | BG-1d (chờ Anh) + DA-2 (khối riêng, nền = bg-1d) |
| `m4\*` dùng chung | — |
| `tests\` (chỉ test lỗi thời N5) | — |
| `m4\giao_dien\m4_duyet_pdf.js`, `m4.js`, `m4.css` | — |
| `tools\mo_demo_worktree.ps1`, `CLAUDE.md` | lead |

## Màn hình / module chờ Anh

| Màn | Trạng thái |
|---|---|
| CRM · Báo giá (#42, TL 45) | **Chờ Anh kiểm cổng A (xem lại)** — `PHIEU-CONG-A-BAO-GIA-XEM-LAI.md`, DEMO http://127.0.0.1:8791 (25/10) |
| CRM · Dự án đang bán (yêu cầu mới 25/10) | Anh đã chốt thêm QD-17…20 (tắt luồng CFO trên màn hình, đơn giá theo m², 4 trạng thái lô, thuế) — DA-1 chờ gộp; DA-2 màn hình đang làm; DA-3 báo giá nạp mặc định sau |
| M4 · màn 03B | Anh duyệt checklist (QD-20261025-13) — M4-5a máy chủ (một phần bằng số tiền) → M4-5b màn hình |

## Việc phụ (lead làm, ghi để Anh biết)

- 24/10, khi L0-4 chạy thử trên bản sao `chinh`, CSDL CRM DEMO dùng chung của Anh đã được nâng lên schema 23 (đúng bản `chinh`) và nạp thêm dữ liệu mẫu DEMO. Từ L0-4b trở đi lập trình dùng CSDL riêng.

---

# Trạng thái hợp nhất — 24/10/2026 (bàn giao từ Codex, giữ làm lịch sử)

| Phần | Đã có | Còn pending / kết luận |
|---|---|---|
| Nền Git | `chinh` giữ H1 `59b7d8e`; `hop-nhat-20261023` giữ H2/H3; không push, không xóa tệp | H5 chờ Anh xem báo cáo H4; không gộp vào `chinh` |
| M2 | 00A Source7 và 00B owned-RPC đã nhập; FIX01 còn ở `luu/m2-00b-fix01` do xung đột | H4 có lỗi nhiều ở các test M2-00B; chưa nghiệm thu |
| M4 | Căn cứ, master reuse, 03A, common identity gốc, 04A/04B/UI copy và một số registration đã nhập; các gói xung đột nằm trên `luu/*` | M4B2/B3 chưa terminal; UI/Review chưa kiểm độc lập hoặc xác minh GUI; chưa nghiệm thu |
| CRM | G4 và G6A-M25 registration đã nhập; G5, CRM-M4-three giữ riêng trên `luu/*` | CRM chưa kiểm độc lập trên head hợp nhất; chưa xác minh GUI; chưa nghiệm thu |
| Shared extraction Source6 | Lazy Excel, DOCX tables, G5/E5 đã nhập | Ordered fix còn `luu/*`; toàn engine chưa nghiệm thu |
| M0/M1/M3/M5/M6–M10 | Không có gói code mới được H3 nhập riêng trong đợt này | H1 là nền cũ; không có căn cứ để kết luận các module này hoàn tất. H4 có lỗi M1 và bridge tests |
| H4 | SQLite log ghi 625 kết quả: 206 ok, 275 ERROR, 4 FAIL, 140 skipped; tiến trình treo trước footer/report | H4 không đạt/không hoàn tất; PostgreSQL chưa chạy; không sửa và không chạy lại |

H3 phân loại 36 đầu việc: 19 gói đã nhập `hop-nhat`, 13 xung đột giữ ở `luu/*`, 2 gói chưa xác nhận terminal giữ ở `luu/*`, 2 dòng không có code delta mới (report-only/bản trùng). Không có path xóa trong diff `chinh..hop-nhat`; working tree sạch tại thời điểm ghi.

**Thời gian đo được:** từ commit H1 lúc 07:16:48 đến commit H3 cuối lúc 07:45:03 là khoảng 28 phút 15 giây; tới log H4 cuối lúc 07:47:29 là khoảng 30 phút 41 giây. Đây là khoảng giữa mốc commit/log, không phải tổng thời gian lịch sử của dự án hay thời gian chạy từng worker.

**Agent:** tại lần kiểm tra hiện tại không có tiến trình Claude Code đang chạy. Trong cây Codex có 1 root và 3 subagent ở trạng thái interrupted; không có subagent hoạt động. 36 dòng frozen là 36 đầu việc, không chứng minh có 36 agent. Sổ theo dõi không có số phút hoặc danh tính worker đầy đủ cho toàn bộ lịch sử.

**Tiếp theo:** Anh xem các nhánh `hop-nhat` và `luu/*`, cùng log H4; sau đó chốt hướng phân tích lại. Chưa làm H5, không push GitHub và không di chuyển thư mục.
| PostgreSQL DEMO (sự cố 25/10) | Anh chọn: **dịch vụ Windows** + **dọn 323 CSDL test** — chờ Anh bấm `DỌN CSDL TEST CŨ.cmd` rồi `CÀI DỊCH VỤ POSTGRES DEMO.cmd` (`SU-CO-POSTGRES-DEMO.md`) |
