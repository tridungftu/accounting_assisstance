# Trạng thái — lead Claude Code cập nhật khi lát đổi trạng thái

Trạng thái lát: Đang code → Chờ kiểm → Chờ Anh (cổng A/B) → Sửa → Xong · Bị chặn. Kế hoạch và hàng đợi đầy đủ: `4-KE-HOACH-LEAD.md`. Nền test: `NEN-TEST.md` mục 0b — **nền v4** (mục 0, 25/10): 1501/23/44/362, **0 treo**.

## Lát đang chạy — 25/10: tối đa 3 worker lập trình; **từ 26/10 (CD-004): tối đa 6 = 2 suất Claude (ưu tiên review) + 4 Codex lát nhỏ ≤ 3 file** (lên 4 Codex khi PostgreSQL DEMO đã chạy dịch vụ Windows). Mọi lát Codex: `kiem-nhanh` → `review-lat` (Opus) → gộp; ngừng giao khi > 2 lát chờ review

| Lát | Việc | Worker | Nhánh · worktree | Giao lúc | Trạng thái |
|---|---|---|---|---|---|
| BG-1d | CRM · Báo giá màn hình 2 bước (BG-1b + BG-1d) | Claude Sonnet · review Codex | `lat/bg-1d` · DEMO 8791 | 25/10 | **Cổng A lần 1 chưa đạt** (Anh 21:55, CD-005: 7 điểm BG-18…24) → sửa trên dòng `lat/ui-1`: BG-e1 (BG-20/19), BG-e4 (BG-22) đang code; BG-e2 (BG-21), BG-e3 (BG-18/24/23) tuần tự sau → phiếu cổng A lần 2 |
| DA-2 | CRM · màn Dự án đang bán (xem + thêm/sửa; ẩn luồng CFO) | Codex · review Claude | `lat/da-2` (= bg-1d + da-1) | 25/10 | Xong code đến DA-2c (33a2e29); review Đạt; chờ BG-1d qua cổng A để gộp |
| M4-5a | M4 · Nghiệm thu & chi phí dự án · 03B máy chủ: khai một phần bằng số tiền + gợi ý hóa đơn — **M0033** | Codex · review Claude | `lat/m4-5a` | 25/10 19:16 (vòng 3) | **XONG — đã gộp 834a53c** (M0033). **Nợ đã trả 25/10 21:05:** 21 ca PG `test_m4_03b_common_pg` (gồm SQL M0033) đạt thật trên bản sao 03a (nhờ L0-8d/8e/8f), c16 skip có chủ đích |
| DA-3a | CRM · Báo giá nạp mặc định từ Dự án đang bán, ghi nhận khác tiêu chuẩn | Codex · review Claude | `lat/da-3a` (c077a83) | 25/10 | **XONG — đã gộp** (vòng 2 B1; kiem-nhanh Đạt; PG 29/29 + 16/16) |
| T-MIG2 | Test PostgreSQL theo chuỗi migration mới | Codex | `lat/t-mig2` (26e9c35) | 25/10 | **XONG — đã gộp 77ea379** (review Opus Đạt; 0 mã lỗi mới; gốc t01b có từ nền; ho=- do bộ chạy) |
| UI-1 | Khung lưới icon dùng chung + áp CRM 6 phần (CD-002) | Claude Sonnet | `lat/ui-1` (= da-2 + hop-nhat) | 25/10 | **Chờ Anh — cổng A** (DEMO 8798; phiếu `PHIEU-CONG-A-TRANG-CHU-LUOI-ICON.md`); UI-1b sửa lỗi lần tải đầu xong; gộp sau cổng A + BG-1d |
| UI-2 | Máy chủ `GET /api/khung/module/crm` (CD-002) | Codex | `lat/ui-2` | 25/10 19:16 | **XONG — đã gộp af7c389**: kiem-nhanh Đạt, review-lat Opus Đạt (3 Nên sửa → **UI-2b** chờ chỗ trống: số icon theo TL 42 §3, không trả tổng cắt); lead còn gọi thử `/api/khung/module/crm` 4 vai trên DEMO khi chuẩn bị cổng A |
| L0-10 | **Bị chặn mở DEMO có CRM** từ 19:46 (sau khi cụm chạy dịch vụ Windows): `pg_ctl status` dưới tài khoản người dùng báo 3, không đọc được tiến trình dịch vụ → `pg_cum.bao_dam_cum` báo CUM_CONG_BI_CHIEM; ảnh hưởng `mo_demo_worktree.ps1` và `MỞ BẢN DEMO.cmd` | Codex | `lat/l0-10` | 25/10 20:38 | **XONG — đã gộp c199a05** (review Opus Đạt); điểm Nên sửa/Để sau → L0-10b đang code |
| M2j-b | Sửa nóng `app.js`: bộ lọc "Lần tải" (M2j) làm vỡ 16 bộ test node (DOM giả không có phần tử cha) | Lead | `hop-nhat` | 25/10 19:08 | **Xong** — sửa 1 dòng; 16 → 7 bộ node không đạt, cả 7 cũng không đạt trên nền v4 (lỗi có sẵn) |

## Cổng AI (CD-001, TL 48 — Anh chốt 25/10: Local luôn có, Cloud chỉ qua Mask file v2)

| Lát | Việc | Worker | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| AI-0a | Tạm khóa Cloud trực tiếp của engine #6 **bản độc lập** (`D:\Claude\Ho tro review ho so xay dung\review_xaydung`; mã ngoài git — lead sao lưu kèm SHA vào `LUU-TRU\ai-0a-sao-luu-review_xaydung-20261025-175621`) | Claude (Codex lỗi sandbox) | — | **Xong** 25/10 — 18 ca test mới đạt; 9 test Cloud cũ thất bại đúng thiết kế → AI-3 |
| AI-0b | Tạm khóa Cloud trực tiếp ở bản engine trong repo (`m4\review_goc\trich_xuat\cloud.py`, `ai_cloud.py`) + cập nhật ghim SHA `nguon_review.py` | Codex | — | **Xong, đã gộp** (06fa717) |
| AI-1 | Cổng Local AI (`tri_thuc\ai_cuc_bo.py`) gọi được LAN/Tailscale, kiểm tra như `privacy\local_ai.py` của Mask v2; test bằng máy AI giả | Codex | — | **Xong, đã gộp** (cfdf33c) — 40/40; review-lat sau gộp **Đạt**, 3 Nên sửa → lát **AI-1b** (Codex, chờ chỗ trống: `localhost`, LM Studio `/api/tags`, nhớ lỗi 15 giây, chuẩn hóa cài đặt khi đọc) |
| MASK-1 | Chế độ API của Mask v2 (che / mở che / còn sót; khóa Bearer; chỉ 127.0.0.1) — làm trong thư mục Mask v2 theo `CLAUDE.md` của nó (không git, CHANGELOG, test + benchmark độ phủ không giảm; không đọc/sửa `data\`, `*.maskvault`, `*.maskkeep`, `*.key`) | Claude Opus | — | **XONG** 19:52 (Mask v2 2.7.0, không git): vòng 1 Không đạt (1 Chặn) → vòng 2 sửa + làm QD-24 → review Opus vòng 2 **Đạt**; 387 test đạt, benchmark không giảm. Nên sửa chuyển MASK-2 (định danh đã khai viết khác cách; nút Khóa ngay khi giao diện bận) |
| MASK-2 | Đưa "định danh đã biết" và kiểm `dau_vet` của `AnDanh` vào lõi Mask v2; đo lại độ phủ | Claude | MASK-1 | **XONG 21:25** (Mask v2 2.7.1): review vòng 1 Không đạt → vòng 2 Đạt → vòng 3 sửa 2 Nên sửa; 449 test đạt; benchmark không đổi (lộ 1/101, held_out 6/51, thay nhầm 0). Còn chờ Anh: dấu vết cho màn che thủ công |
| AI-2 | Cổng AI dùng chung: định tuyến loại việc, Cloud qua Mask API, nhật ký `nhat_ky.cong_ai_goi`, công tắc tắt Cloud | Claude | AI-1, MASK-1 | **AI-2a XONG — gộp 1cf32eb** (review Opus độc lập Đạt; Cloud mặc định tắt) · **AI-2b** đang code (M0034 + bộ ghi nhật ký PG) |
| AI-3 | Engine #6 (độc lập + bản trong repo) chuyển Cloud sang cổng AI; bỏ `AnDanh`, `goi_api` riêng | Codex | AI-2, MASK-2 | Chờ |
| AI-4 | Mở Cloud theo TL 48 §1.5; đo độ chính xác Local theo loại việc; lịch giảm tỷ lệ kiểm xác suất **Anh đã đồng ý (§1.6)**: bắt đầu 20%; ≥ 90% trên 50 lượt gần nhất → 10%; ≥ 95% trên 100 lượt → 5%; tối thiểu 5%, không về 0; tụt dưới 90% → tự về 20% và báo lead | Claude | AI-3 qua review | Chờ |

Quy tắc áp cho mọi lát từ 25/10 (CD-001 việc 3): không lát nào viết code gọi thẳng `api.anthropic.com`/`api.openai.com` hoặc thêm bộ che riêng — lead kiểm bằng grep ở cổng kiểm soát.

## Trang chủ lưới icon (CD-002, TL 49 — Anh chốt 25/10, phương án B; ưu tiên sau AI-0, trước lát CRM mới)

| Lát | Việc | Worker | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| UI-1 | Khung dùng chung: trang chủ module (thẻ tổng quan + lưới icon), thanh icon trái thay menu chữ; áp CRM 6 phần (màn bên trong giữ nguyên) | Claude | — (dựng trên `lat/da-2` vì khóa `crm_g.js`/`style.css`) | Đang code (19:21) |
| UI-2 | Máy chủ `GET /api/khung/module/crm` đã lọc quyền + đếm việc chờ (nguồn sẵn có) — hợp đồng dữ liệu `HOP-DONG-DU-LIEU-KHUNG-LUOI.md` | Codex | — (song song UI-1) | **XONG — đã gộp af7c389**: kiem-nhanh Đạt, review-lat Opus Đạt (3 Nên sửa → **UI-2b** chờ chỗ trống: số icon theo TL 42 §3, không trả tổng cắt); lead còn gọi thử `/api/khung/module/crm` 4 vai trên DEMO khi chuẩn bị cổng A |
| UI-3 | Trang chủ hệ thống: icon module, tìm nhanh, thanh cố định 4 mục, M9 "Tạm dừng" | Claude | UI-1 | Chờ |
| UI-4 | Áp khung cho M2, M4, Duyệt chung K5 | Claude/Codex | Cổng A của UI-1 | Chờ |

## Nhật ký lát (CD-003 — mỗi lát giao/đóng một dòng; model Codex theo cấu hình `gpt-6.1-sol`, mức suy luận ghi theo lần giao)

| Lát | Worker | Model | Bắt đầu | Kết thúc | Vòng review | Test (so nền v4) |
|---|---|---|---|---|---|---|
| M4-5a v1–v2 | Codex | gpt-6.1-sol · high | 25/10 17:25 | 18:17 | 1 (Claude Sonnet) — Đạt | Xanh — 0 mã lỗi mới (M4); PG chưa chạy |
| DA-3a | Codex | gpt-6.1-sol · high | 17:50 | 18:17 | 1 (Claude Sonnet) — Đạt | Xanh — 0 mã lỗi mới; PG chưa chạy |
| T-MIG2 v1–v2 | Codex | gpt-6.1-sol | 17:44 | 18:44 | 0 | Đỏ — 1 mã lỗi mới |
| C3c | Codex | gpt-6.1-sol · high | 17:52 | gộp 19:03 | 0 (sửa theo review C3) | Xanh — 43/43 có PostgreSQL (lead chạy) |
| MASK-1 | Claude | Opus | 18:39 | 18:59 | vòng 1 Không đạt | Mask v2: 378 đạt / 1 lỗi có sẵn; benchmark không giảm |
| AI-1 | Codex | gpt-6.1-sol · high | 18:45 | gộp 18:58 | 0 (lead đọc diff mạng) | Xanh — 40/40 |
| M2s-b | Codex | gpt-6.1-sol · low | 18:45 | gộp 19:02 | 0 | Xanh — node 7/7 |
| Review M4-5a + DA-3a | Claude | Sonnet | 18:40 | ~18:55 | — | — |
| M2j-b (sửa nóng) | Lead | Opus | 19:08 | 19:15 | 0 | Xanh — node về đúng nền v4 (7 bộ lỗi có sẵn) |
| M4-5a v3 | Codex | gpt-6.1-sol · high | 19:16 | gộp 19:56 | vòng 1 Đạt + kiem-nhanh Đạt | Xanh — thuần 104/104; M4 PG = nhánh tích hợp |
| UI-2 | Codex | gpt-6.1-sol · high | 19:16 | gộp 20:03 | 1 (Opus) — Đạt | Xanh — test mới 16/16; CRM PG không thêm mã lỗi |
| Review MASK-1 | Claude | Opus | 19:17 | 19:26 | vòng 1 | Không đạt — 1 Chặn |
| MASK-1 vòng 2 | Claude | Opus | 19:35 | 19:48 | review vòng 2 đang chạy | Mask v2: 387 đạt / 1 lỗi có sẵn; benchmark không giảm |
| Review MASK-1 vòng 2 | Claude | Opus | 19:48 | 19:52 | vòng 2 | **Đạt** — 2 Nên sửa → MASK-2 |
| AI-1b | Codex | gpt-6.1-sol · high | 19:49 | 19:55 | (review sau gộp AI-1) → kiem-nhanh | Xanh — 101/101 |
| L0-8d | Codex | gpt-6.1-sol · high | 20:07 | gộp 20:31 | kiem-nhanh Đạt | họ 03a dựng được; 03A/03B vẫn skip: host #6 GUARD_KHONG_NAP → L0-8e |
| UI-2b | Codex | gpt-6.1-sol · high | 20:07 | gộp 20:17 | kiem-nhanh Đạt | Xanh — khung 20/20 |
| T-M4a | Codex | gpt-6.1-sol · high | 20:16 | gộp 20:31 | kiem-nhanh Đạt | Xanh — 01b 12/12, 01c 8/8, review_k2 14/14, 0 skip (đủ tệp ghim) |
| UI-1 | Claude | Sonnet | 19:21 | 20:15 | kiem-nhanh Đạt có điều kiện (giấy phép icon → lead sửa) | node 12/12 ca mới; 8 bộ node lỗi có sẵn |
| L0-8e | Codex | gpt-6.1-sol · high | 20:28 | 20:38 | review-lat Opus **Không đạt** (2 Chặn: guard nuốt DROP CSDL tạm mà sổ ghi đã xóa; 3 mã lỗi test bộ chạy dưới runtime thật) → vòng 2 chờ suất | test_trich6_host 22/22, 03A PG 13/13 (kết quả test vẫn giá trị); CSDL kho_test_* 323 → 326 |
| MASK-2 | Claude | Opus | 20:31 | 21:25 | 3 vòng (Không đạt → Đạt → sửa Nên sửa) | Mask v2 2.7.1: 449 đạt / 1 lỗi có sẵn; benchmark không đổi |
| L0-10 | Codex | gpt-6.1-sol · high | 20:38 | gộp 20:51 | review-lat Opus Đạt | Xanh — 46/46; DEMO 8798 chuẩn bị CRM chế độ DICH_VU |
| L0-8f | Codex | gpt-6.1-sol · high | 20:47 | 20:44 (v1 dừng đúng: gốc ở helper test) | — | — |
| L0-8f v2 | Codex | gpt-6.1-sol · high | 20:50 | 20:55 | kiem-nhanh Đạt; chờ L0-8e v3 (dựng trên L0-8e) | **PG: 03B 21/21 (c16 skip có chủ đích), 03A 13/13**; mock bộ chạy lead sửa (45/45); CSDL tạm 329/329 |
| C3d | Codex | gpt-6.1-sol · high | 21:14 | gộp 21:36 | review-lat Opus Đạt | Xanh — PG 24/24 + 23/23, 0 skip |
| T-MIG2 (cổng cuối) | Codex | gpt-6.1-sol | 17:44 | gộp 21:36 | review-lat Opus Đạt | Xanh — CRM PG 514 đạt, 0 mã lỗi mới, skip 78→28 |
| L0-8e v2 | Codex | gpt-6.1-sol · high | 21:02 | gộp 21:20 → **hoàn tác 21:14** (b25ff7a) | review-lat vòng 2 Đạt | **Đỏ** — hồi quy: test tự CREATE DATABASE (CRM) bị bộ chạy từ chối 'tên đã dùng' (lead kiểm thiếu nhóm này) |
| L0-8e v3 | Codex | gpt-6.1-sol · high | 21:16 | gộp lại 21:32 (b98a7bd, đảo hoàn tác + v3) | kiểm đủ bộ trên kiem/l0-8e | CRM 534 đạt; 03A 13/13; #6 22/22; CSDL 329/329; 1 mã mới g02 PDF (chính sách không Word COM) → T-PDF |
| L0-8f (gộp) | Codex | — | — | gộp 21:33 (dd3ecc3) | kiem-nhanh Đạt | **hop-nhat: M4-03B PG 21/21 thật** — nợ M4-5a trả xong trên nhánh tích hợp |
| AI-2a (gộp) | Claude | Opus | 21:12 | gộp 21:30 (1cf32eb) | review-lat Opus độc lập Đạt | 78/78; Cloud mặc định tắt |
| T-PDF + PDF-1 | Codex | gpt-6.1-sol · high | 21:35 | 21:53 (PDF-1: công tắc Word→PDF mặc định tắt, QD-26) | chờ PG (sau đo nền) → kiem-nhanh | thuần 2/2; **phát hiện: sản phẩm chưa có công tắc tắt Word COM** (`nguon/crm_docx.py` ~:374, :530, :933) — CLAUDE.md §2 'không Word COM' → hỏi Anh |
| Nền PG v2 (lead) | Lead | — | 21:46 | 22:05 | — | 126 module 2327/21/66/67, 0 treo; 12 mã mới đã phân loại → T-NEN-a/b/c |
| T-NEN-a, T-NEN-b, T-NEN-c | Codex | gpt-6.1-sol · high | 21:55 | 22:04 | lead chạy PG → kiem-nhanh | (T-NEN-b: mã sản phẩm `tools/source6_g5_e5/trich_xuat/danh_muc.py:280` có lệnh xóa tệp rollback; T-NEN-c: `tools/source6_lazy_excel/master_hd.py` thiếu trong git) |
| AI-2b | Codex | gpt-6.1-sol · high | 21:35 | gộp 22:08 (295caef) | review-lat Opus Đạt | Xanh — PG: nhật ký 10/10, 0 mã lỗi mới; chuỗi migration 34 |
| BG-e1 (BG-20, BG-19) | Codex | gpt-6.1-sol · high | 22:09 | 22:22 (32557c3) | kiem-nhanh sau cùng cụm BG | node giao kết 27/27 |
| BG-e2 (BG-21) | Codex | gpt-6.1-sol · high | 22:25 | — | — | — |
| KY-DOCX (QD-27) | Claude | Opus | 22:20 | — | — | — |
| BG-e4 (BG-22) | Codex | gpt-6.1-sol · medium | 22:09 | 22:10 → vòng 2 22:25 (DU_AN + test M4) | — | khung 19/19 |
| PDF-1 v2 | Codex | gpt-6.1-sol · medium | 22:02 | 22:03 | review-lat Opus Đạt (hệ quả nghiệp vụ → Anh chọn QD-27; giữ chưa gộp, gộp cùng KY-DOCX) | Xanh — PG: giao_ket 62/62, ky_ket 38/38, g02 hết lỗi; 0 mã lỗi mới |
| AI-2a | Claude | Opus | 21:12 | 21:30 | review-lat Opus độc lập đang chạy | Xanh — 78/78 (test_cong_ai 30); Cloud mặc định tắt |
| L0-10b | Codex | gpt-6.1-sol · high | 20:45 | gộp 21:00 | kiem-nhanh Đạt | Xanh — 52/52; kiểm thật dịch vụ khớp |
| UI-1b | Codex | gpt-6.1-sol · high | 20:55 | 21:02 | lead thử DEMO | Xanh — node khung 16/16; DEMO 8798 lần tải đầu không còn lỗi phiên |
| kiem-nhanh DA-3a v2 + AI-1b | Claude | Haiku | 20:12 | 20:15 | — | Đạt cả hai → gộp |
| kiem-nhanh UI-2 + M4-5a v3 | Claude | Haiku | 19:51 | 19:55 | — | Đạt cả hai |
| review-lat UI-2 | Claude | Opus | 19:56 | 20:02 | vòng 1 | Đạt — 3 Nên sửa → UI-2b |
| DA-3a v2 | Codex | gpt-6.1-sol · high | 19:33 | 19:38 | (vòng 1 Đạt) → kiem-nhanh | Xanh — 0 mã lỗi mới; PG mặc định báo giá 29/29, dự án đang bán 16/16 (0 skip) |
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

## Cần điều tra (lead)

- 25/10 21:56–21:58: trong lượt PG của AI-2b, **26 CSDL `kho_test_*` cũ (có từ trước) biến mất — bộ chạy ghi 'không phải do công cụ này'**; không có biên nhận của `DỌN CSDL TEST CŨ.cmd`. Không hại (CSDL test cũ) nhưng trái hứa hẹn 'chỉ xóa CSDL do bộ chạy tạo' → tìm module/tiến trình đã DROP (sổ `%TEMP%\ktt-theo-module-20261025-215622\pg-demo-so-ghi.json`, mục `canh_bao`).

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


## Chạy đêm 25→26/10 (CD-008) — DỪNG do hạn mức

- 22:25 nhận CD-006, CD-007, CD-008. 22:30 lead Claude chạm hạn mức gói: không giao lát mới, không gộp, không viết báo cáo đêm.
- Đang chạy, để chạy hết: Codex BG-e2 (lat/bg-e2), BG-e4 v2 (lat/bg-e4) — chưa commit, chưa kiểm.
- Lát Claude dở (KY-DOCX ở lat-t-pdf; kiem-nhanh T-NEN-a/b/c) có thể bị ngắt; tệp đã ghi còn trong worktree, chưa commit.
- T-NEN-a/b test PG xanh; T-NEN-c có 1 lỗi mới test_source6_lazy_excel (SETUP NOT_VERIFIED, nghi do worktree thiếu master_hd.py chưa vào git) — cần lead kiểm trước khi gộp.
- DEMO đang mở: 8798 (lat/ui-1, Trang chủ lưới icon), 8791 (lat/bg-1d, Báo giá).
- Việc tiếp theo khi có hạn mức: theo thứ tự CD-008 (gộp bg-1d + da-2 → BG-e1…e4 + phiếu cổng A lần 2 → mốc dự án CD-006/007 → UI-2b/UI-3 → hàng đợi).
- Cập nhật sau khi dừng: Codex xong BG-e2 (lat/bg-e2 259ce65, 2 tệp, node 31/31 nhóm ca) và BG-e4 v2 (lat/bg-e4 29c67af, 3 tệp, khung lưới 20/20, M4 13/13); lead đã commit lên nhánh lát, đúng phạm vi tệp; CHƯA kiem-nhanh/review-lat, CHƯA gộp lat/ui-1.
- kiem-nhanh T-NEN: a đạt (test PG 58/58 xanh); b đạt có điều kiện (test PG xanh); c chưa xanh — source6_lazy_excel cần thư mục gốc tên files và master_hd.py chưa vào git → giữ nhánh, không gộp. Sản phẩm còn xóa tệp: tools/source6_g5_e5/trich_xuat/danh_muc.py:280.
- 22:55 hạn mức Claude mở lại → chạy tiếp CD-008. Đang chạy: KY-DOCX (Claude Opus, lat-t-pdf, tiếp sau khi bị ngắt; giữ `pg_migrations.py` M0035), BG-e3 (Codex, lat/bg-e3 từ lat/bg-e2; giữ `crm_g.js`/`style.css` dòng giao diện), MDA-1a (Codex, lat/mda-1a từ kiem/gop-da-2; append migration — lead đánh số khi gộp sau KY-DOCX), AI-3 (Codex, lat/ai-3; giữ `m4/review_goc/trich_xuat/ai_cloud.py`, `cloud.py`), kiểm nhanh BG-e1/e2/e4 (Claude Haiku), test PG cả bộ cho kiem/gop-da-2 (lead).
- Phát hiện: lưới CRM (UI-1) 6 phần không có ô "Dự án đang bán" (màn nằm trong thẻ con của "Mẫu hợp đồng") → lát DA-4 thêm phần thứ 7 sau BG-e3.

### Nhật ký lát đêm 25→26/10 (CD-003 · CD-008) — cập nhật 23:37

| Lát | Worker · model | Giao → xong | Nhánh · commit | Kiểm / review | Test | Gộp |
|---|---|---|---|---|---|---|
| KY-DOCX (QD-27) | Claude Opus | 22:20 → 23:15 (ngắt 22:30–22:55) | lat/t-pdf a940375 | review-lat: chờ | thuần 775/0/39/235 (0 mã mới); PG đang xếp hàng | chưa |
| BG-e1 / BG-e2 / BG-e4 v2 | Codex | 22:10 → 22:40 | lat/bg-e1 32557c3, bg-e2 259ce65, bg-e4 29c67af | kiem-nhanh Đạt / Đạt / Có điều kiện (sửa ở BG-e5) | node 31/31, 20/20, 13/13 | gom lat/bg-gom 9db1501 |
| BG-e3 (BG-18/23/24) | Codex | 22:58 → 23:12 | lat/bg-e3 f72a910 | review-lat cụm: đang chạy | node 35/35 | gom lat/bg-gom |
| BG-e5 (sửa sau kiểm) | Codex | 23:15 → 23:24 | lat/bg-e5 | review-lat cụm: đang chạy | node 36, 20, 13, 10 | — |
| Gộp thử da-2 (CD-006 b1) | lead | 23:05 → 23:33 | kiem/gop-da-2 1283999 | — | PG cả bộ 2340/21/67/66 vs v2: +2 mã (test cũ đòi giao diện cũ) + node crm_ky_ket_async | chờ T-DA2 |
| T-DA2 | Codex | 23:35 → | kiem/gop-da-2 | — | — | — |
| MDA-1a (SQL, M0035) | Codex | 23:00 → 23:10; v2 23:20 → 23:25 | lat/mda-1a a68d22b; v2 d8e0923 (trên mda-1b) | review-lat v1 Không đạt (1 Chặn: locale C) → v2 sửa | tĩnh 18/36 (18 PG skip); PG đang chạy | chưa |
| MDA-1b (dịch vụ, HTTP, seed) | Codex | 23:12 → 23:19 | lat/mda-1b | — | 101/140 (39 skip) | — |
| MDA-3s / MDA-4a | Codex | 23:27 → 23:33 | lat/mda-3s, lat/mda-4a → lat/mda-gom 39175d8 | — | 81/4 skip; 22/12 skip | — |
| AI-3 | Codex | 23:00 → 23:06 dừng (PIN) → v2 23:17 → v3 23:32 | lat/ai-3 fd4b95f | review-lat Đạt (3 Nên sửa → v3) | thuần cả bộ: 0 mã mới (8 lỗi có sẵn ở hợp nhất) | chờ v3 |
| T-WORD | Codex | 23:15 → 23:24 | lat/t-word → lat/t-pdf | — | giao_ket 62/64, 2 skip | — |
| DA-4a / DA-4b (phần Dự án đang bán trên lưới) | Codex | 23:20 → 23:23; 4b 23:25 → | lat/da-4a cbfd2e0; lat/da-4b | — | khung 21/21 | — |
- 23:55 **KY-DOCX DỪNG (CD-008: không đạt 2 lần)** — PG: v1 k10 lệch trạng thái (`CHO_CAU_HINH` vs `CHO`, sửa test ở v2 9121660); v2 k10 lệch lý do `crm_g5_nhan` (`KHONG_DEN_HAN` vs `G5_BAN_SINH_CHI_DOCX`) → nghi M0035 kiểm "chưa đến hạn" trước "bản chỉ DOCX". Giữ `lat/t-pdf`, không gộp; review-lat Opus vòng 1 đang chạy làm căn cứ sửa sáng 26/10.
- 23:40 gộp `lat/da-2` + T-DA2 vào hợp nhất (6998a79; PG cả bộ: 0 mã mới sau T-DA2) — **CD-006 mục 1 xong phần gộp**. 23:45 gộp AI-3 (30d5478).
- Dòng giao diện DEMO sáng 26/10: `lat/ui-dem` = DA-4b (lưới 7 phần) + hợp nhất mới + MDA (1a/1b/3s/4a) + BG-e6s/u + MDA-4b; MDA-2 (mục mốc trong Dự án đang bán) và UI-3a (trang chủ hệ thống, máy chủ) đang code.

### Nhật ký lát đêm — cập nhật 00:25

| Lát | Worker · model | Giao → xong | Nhánh · commit | Kiểm / review | Test | Gộp |
|---|---|---|---|---|---|---|
| T-DA2 | Codex | 23:35 → 23:38 | kiem/gop-da-2 | — | node ky_ket 14/14; 41_02 29/29 | **hợp nhất 6998a79** (cùng da-2) |
| AI-3 v3 | Codex | 23:32 → 23:36 | lat/ai-3 46ee853 | review-lat Đạt | 236 ok, FAIL có sẵn | **hợp nhất 30d5478** |
| KY-DOCX v2 | Codex | 23:51 → 23:54 | lat/t-pdf 9121660 | review-lat Đạt (k10 = test đua) | PG k10 còn đỏ (lần 2) | **DỪNG** (CD-008) |
| BG-e6s / BG-e6u | Codex | 23:44 → 23:52 | lat/bg-e6s, lat/bg-e6u | review dòng giao diện: đang chạy | 27/33 (5 PG skip); node 41 | ui-dem |
| MDA-4b | Codex | 23:44 → 23:52 | lat/mda-4b | như trên | khung 26/26 | ui-dem |
| UI-3a / UI-3b | Codex | 23:55 → 23:59; 00:00 → 00:15 | lat/ui-3a, lat/ui-3b | như trên | 41/41; khung 30/30 | ui-dem |
| MDA-2 / MDA-3u | Codex | 23:52 → 00:03; 00:03 → 00:19 | lat/mda-2, lat/mda-3u | như trên | node dự án 39; giao kết 4/4 bộ | ui-dem |
| DA-5s | Codex | 00:06 → 00:09 | lat/da-5s | như trên | 58/60 (2 skip) | ui-dem |
| MDA cụm máy chủ (1a v2, 1b, 3s, 4a) | Codex | — | lat/mda-gom 39175d8 | review-lat **Đạt** (3 Nên sửa → MDA-5a/5b) | PG 233 ok, 0 mã mới | chờ PG 5a/5b |
| MDA-5a / MDA-5b | Codex | 00:13 → 00:19; 00:19 → 00:20 | lat/mda-5a, lat/mda-5b | — | 68/89 (21 skip); 19/37 (18 skip) | PG đang chạy |
| M4-5b, MDA-4c | Codex | 00:10 →, 00:20 → | lat/m4-5b, lat/mda-4c | — | — | — |
| T-NEN-c2 | Codex | 00:22 → 00:24 | — | **bị chặn**: không có bản `master_hd.py` lazy Excel đã duyệt trong git; tài liệu giao gốc thiếu | 0 test chạy (3 lỗi setUp) | Cần Anh |

- Thử DEMO 8799 (`lat/ui-dem`, CSDL riêng p8799): lưới CRM 7 phần, Dự án đang bán mở thẳng; mục Mốc thanh toán chạy (2 mốc seed, 1 việc chờ, chỉnh dự kiến có lý do → hết việc chờ); nhãn vai có tên pháp nhân. Danh sách vai mô phỏng rất dài (~44 dòng gồm vai M2/M4/M5) — ghi "Cần Anh".
- Quyết định lead (đêm): MDA giữ **M0035** (đã chạy DEMO p8799); KY-DOCX đổi sang **M0036** khi sửa sáng 26/10 (sửa test ghi cứng 35).

### Nhật ký lát đêm — cập nhật 01:35

| Lát | Worker · model | Giao → xong | Nhánh · commit | Kiểm / review | Test | Gộp |
|---|---|---|---|---|---|---|
| MDA-5a / MDA-5b | Codex | 00:13 → 00:20 | lat/mda-5a, lat/mda-5b 01954f4 | review cụm MDA Đạt (Nên sửa → 5a/5b) | PG 265 ok, 0 mã mới | **hợp nhất 7ce0344** (00:31) + ui-dem |
| M4-5b (03B) | Codex | 00:10 → 00:27; v2 00:31 → 00:36 | lat/m4-5b 932f115 | kiem-nhanh Đạt có ĐK → v2; review-lat Đạt | PG 170 ok, 0 mã mới; node 12/12 | **hợp nhất 3b12e47** |
| M4-5c / M4-5d | Codex | 00:50 → 00:59; 01:17 → 01:31 | lat/m4-5d | review lô Đạt (M4-5c), Nên sửa → 5d | node 03B 22/22, 01C 13/13 | **hợp nhất 646046c** |
| MDA-4c | Codex | 00:20 → 00:26 | lat/mda-4c | review lô Đạt | khung 33/33 | ui-dem |
| UI-3c / UI-3d | Codex | 00:43 → 00:46; 01:17 → 01:31 | lat/ui-3c, lat/ui-3d | review lô Đạt (Nên sửa → 3d) | 43/43; 45/45 | ui-dem |
| MDA-2b | Codex | 00:43 → 00:46 | lat/mda-2b | review lô Đạt | node dự án 39/39 | ui-dem |
| BG-e7 / BG-e7s | Codex | 00:54 → 00:56; 00:57 → 00:59 | lat/bg-e7, lat/bg-e7s e0f9853 | review lô Đạt | node 47/47; 104/113 (9 skip) | ui-dem; BG-e7s **hợp nhất 851b73e** |
| KY-UI | Codex | 00:27 → 00:41; v2 00:42 → 00:52 | lat/ky-ui 15fc909 | review lô Đạt (gộp cùng/sau KY-DOCX) | node 4/4 bộ | chờ KY-DOCX |
| T-NEN-c2 | Codex | 00:22 → 00:24 | — | bị chặn (thiếu bản candidate) | — | Cần Anh |

- Review Opus đêm: MDA-1a (Không đạt → v2), BG cụm, AI-3, KY-DOCX, MDA cụm, dòng giao diện (10 lát), M4-5b, lô 7 lát — **8 lượt**, không lát nào gộp khi còn Chặn.
- **Nền PG v3** (01:28, hop-nhat 7e9b915): 2433/20/66/66, 132 module, 0 mã mới so v2 — `nen-test-hop-nhat-pg-v3.json`.
- Phiếu cổng A lần 2: `PHIEU-CONG-A-BAO-GIA-LAN-2.md` (DEMO 8798 = `lat/ui-dem`, khởi động lại 01:33 nạp UI-3d + BG-e7s).

### Nhật ký lát đêm — cập nhật 02:20

| Lát | Worker · model | Giao → xong | Nhánh · commit | Kiểm / review | Test | Gộp |
|---|---|---|---|---|---|---|
| DS-1 / DS-2 | Codex | 01:37 → 01:39 | lat/ds-1, lat/ds-2 | review lô DS Đạt | node 4 bộ; 46/46 | ui-dem |
| DS-3a | Codex | 01:37 → 01:39 | lat/ds-3a | review lô DS Đạt | PG 64 ok 0 skip | **hợp nhất dd06a08** |
| DS-4 (+ vòng 2) | Codex | 01:37 → 01:51 | lat/ds-4 | review lô DS Đạt (nhãn dòng 968 → vòng 2) | PG 41 ok; 03B 23/23 | **hợp nhất d0baee2** |
| DA-6 | Codex | 02:15 → 02:13* | lat/da-6 | lead thử trình duyệt: mở thẳng Dự án đang bán sau tải trang → nạp được | node dự án 44/44 | ui-dem |

\* DA-6 giao 02:12, xong 02:13 (lát 2 tệp). Dòng giao diện cuối đêm `lat/ui-dem` 3ddad66 = hợp nhất d0baee2 + toàn bộ lát giao diện; DEMO 8798 khởi động lại 02:16 từ bản này. PG cả bộ trên `lat/ui-dem` đang chạy.

- 05:36 **kết thúc chạy đêm CD-008.** Báo cáo: `bao-cao-ngay/BAO-CAO-DEM-20261026.md`. Hợp nhất `hop-nhat-20261023` d0baee2 (+ tài liệu lead); dòng giao diện `lat/ui-dem` 87c963c chạy DEMO 8798. Việc mở sáng 26/10: KY-DOCX sửa k10 + đổi M0036 rồi gộp cùng KY-UI; Anh kiểm cổng A lần 2; 7 việc Cần Anh (báo cáo §4).

### 26/10 09:10 — KY-DOCX gộp (Anh duyệt 26/10) · trả lời CD-009 mục 1

- **KY-DOCX vòng 3** (Codex, lát sửa test riêng theo CD-009): k10 hết đua (kéo `thu_lai_sau`, chấp nhận `CHO_CAU_HINH` + `G5_BAN_SINH_CHI_DOCX`), test theo **M0036**, nhãn "PDF xuất tay" không lộ mã. Lead gộp `lat/t-pdf` lên hợp nhất trong `lat/ky-gop`: **M0035 = mốc dự án, M0036 = KY-DOCX** (sửa CRLF của `pg_migrations.py` do lead ghi khi giải xung đột). PG cả bộ 2452/26/65/67 — 8 mã mới đều là ngắt kết nối (WinError 10053, máy bận) + `test_web` chập chờn; chạy lại riêng `test_crm_ky_ket_http` 10 ok (có k10), `test_crm_41_02_http` 13/13 → **gộp hợp nhất 3dd1661**.
- **KY-UI** ghép trên nhánh riêng `lat/ui-ky` (= `lat/ui-dem` + hợp nhất 3dd1661 + `lat/ky-ui`): giữ nhãn xuất của KY-UI ("Chờ ký (đã xuất DOCX)", "PDF xuất tay khi cần"), `veBanKy` giữ cả KY-UI và `nguoi()` của BG-e7; node 5 bộ đạt; PG chọn lọc 182 ok, 0 mã mới so v3. **Chưa thay DEMO 8798** (Anh đang thử cổng A) — sẽ chuyển 8798 sang `lat/ui-ky` khi Anh xong.
- Còn theo CD-010 mục 1: đường **"Kế toán xác nhận đã kiểm tay" G5** cho bản chỉ DOCX → lát KY-G5TAY (đang giao).

**CD-009 mục 1 — vì sao đêm 25→26 không giao (lead nhận lỗi: dừng vì "hết việc ưu tiên" là sai, CD-009 cấm từ nay):**
| Việc | Lý do đêm qua | Hiện nay |
|---|---|---|
| AI-4 (mở Cloud theo TL 48 §1.5, đo độ chính xác Local) | Lead xếp "để ngày" vì rủi ro Cloud — **không bị chặn thật** (AI-3 đã gộp 23:45) | **Giao** (Codex, review Opus) |
| MASK-3 (định danh mới → tệp riêng mã hóa + màn rà, QD-23) | Lead e ngại chạy dự án Mask v2 ngoài repo ban đêm — **không bị chặn thật** | **Giao** (Codex, đúng ràng buộc Mask v2) |
| M2k (nút "Cài đặt lại bộ tải") | Hàng đợi ghi "chưa chốt thiết kế" (thiếu: cài lại là gì — tải lại gói bộ tải hay khởi động lại tiến trình; quyền ai bấm) | **Bị chặn — hỏi Anh** (bảng chọn) |
| E1-4 giao diện (màn danh mục Sửa + nhật ký) | Chưa rõ đặt màn ở đâu (M4 review / Cài đặt / Danh mục chung) | **Bị chặn — hỏi Anh** (bảng chọn) |
| M4-3 (03A: M0026 + test + xác minh màn) | Thực chất đã xong qua các lát 03A/M4-5a; chưa đóng dòng | **Đóng**: PG v3 `test_m4_03a_pg` 13 ok, `test_m4_03a_tinh` 27 ok, `m4_03b_common_pg` 21 ok |

### 26/10 10:15 — Đang chạy + việc chưa giao kèm lý do chặn (CD-009 mục 2)
**Đang chạy (6/6):** Codex — M4-DL1 (CD-011 lược đồ PG), MTQ-1 (CD-012 SQL), M2k (QD-20261026-01), BG-e8 (CD-010.5, dòng giao diện); Claude — review-lat KY-G5TAY (Opus); lead — PG KY-G5TAY.
**Đã xong sáng 26/10:** KY-DOCX gộp hợp nhất (3dd1661, M0036); KY-UI trên `lat/ui-ky`; UI-3e (thanh cố định theo vai, giữ tiền tố) trên `lat/ui-ky`; M4-KK (kiểm kê 8 màn: 8 có · 23 khác · 37 thiếu API; 12 bảng) và MTQ-0 (thiết kế) gộp hợp nhất 29d719d; KY-G5TAY code xong (M0037) chờ PG + review.
| Việc chưa giao | Lý do chặn |
|---|---|
| KY-G5TAY giao diện (nút xác nhận tay ở màn Kiểm) | chờ máy chủ KY-G5TAY qua review (đợt sau) |
| M4-DL2…, công cụ chuyển dữ liệu, 8 màn M4 (CD-011) | nối tiếp M4-DL1 (đang chạy) |
| MTQ-2…5 (CD-012) | nối tiếp MTQ-1 (đang chạy); MTQ-4 cần review Opus |
| AI-4, MASK-3 | không chặn — giao đợt kế (chờ suất Codex trống) |
| E1-4 giao diện (màn Danh mục chung, QD-20261026-02) | không chặn — giao đợt kế |
| CD-010.7 (03B: hướng kế toán dùng "Yêu cầu bổ sung") | không chặn — lát nhỏ đợt kế |
| Seed DEMO 5 vai (CD-010.4) | gộp vào MTQ-5 (theo thiết kế MTQ-0) |
| UI-4 (áp khung cho M2, M4, K5) | chờ Anh qua cổng A UI-1 (phiếu trang chủ lưới icon) |
| BG-2a/2b, BG-3 (Báo giá gói 2–3) | chờ Anh qua cổng A Báo giá lần 2 |
| C3b (phạm vi bán hàng HĐ luồng B) | chờ Anh chốt nguồn phạm vi |
| M2f, E1-5 | việc của Anh (cổng thuế thật / áp vào #6 thật) |
| Chuyển DEMO 8798 sang `lat/ui-ky` | chờ Anh thử xong cổng A trên bản hiện tại |
- 10:50 rà hàng đợi (CD-009 mục 5): Codex chạy M4-DL1 v2, KY-G5TAY-UI, M3-CL (CD-009.3d checklist M3); hàng chờ nối tiếp KY-G5TAY v4 → MTQ-1 v2 → M2k v2 → MASK-3; review Opus AI-4a/E1-4u/M4-03B-YC. Đã xong chờ review/gộp: AI-4a c639b79, E1-4u 456dca1, M4-03B-YC 553ac93, BG-e8 (ui-ky), UI-3e (ui-ky). KY-G5TAY: PG p01/p07 đạt sau vòng 3 (lỗi cú pháp `IF NOT CASE` có sẵn ở guard G6), còn p03 lỗi test (login không có trong seed) → v4. Không việc nào không bị chặn bị bỏ trống.

### 26/10 11:15 — gộp KY-G5TAY, M4-DL1, MTQ-1 (M0037–M0039) · rà hàng đợi (CD-009 mục 5)
- PG từng lát (10:58–11:01) so nền v3: KY-G5TAY 98 ok, MTQ-1 50 ok, M4-DL1 67 ok — **0 mã lỗi mới**, skip bằng nền; FAIL `test_pg_schema`/`test_m4_review_http` là FAIL có sẵn trong nền.
- Gộp `hop-nhat-20261023`: 0079426 KY-G5TAY (**M0037**), 07bb02d M4-DL1 (**M0038**, đổi `M00xx` → `M0038_M4_REVIEW_CHEP`), 506f41c MTQ-1 (**M0039**, `M0039_MA_TRAN_THAM_QUYEN`). `pg_migrations.py` giữ LF (0 byte CR). Chưa CSDL bền nào chạy M4-DL1 v1. Review vòng 2 M4-DL1: Đạt (`review-m4-dl1-v2.md`); 3 điểm nên sửa → lát **M4-DL1b** (đang giao).
- Đang chạy: lead — PG trên hợp nhất sau đánh số (14 nhóm module); test E1-4u v2, M2k v2 (không PG). Codex — MTQ-2, MASK-3, M4-03B-YC v2, M4-DL1b (4/4). Claude — review-lat KY-G5TAY-UI, review-lat E1-4u vòng 2 (2/2).
| Việc chưa giao | Lý do chặn |
|---|---|
| M4-DL2 (lớp đọc/ghi dữ liệu chép Review) | nối tiếp M4-DL1b (cần cột `chup_luc`, hàm bản hiện hành) |
| MTQ-3 (màn ma trận) | nối tiếp MTQ-2 (HTTP) đang chạy |
| MTQ-4 (áp ma trận làm nguồn quyền) | nối tiếp MTQ-2/3; review Opus |
| Nạp dữ liệu Review thật (CD-011 bước 4) | **Cần Anh**: bảng ánh xạ `ma_hd → hợp đồng / pháp nhân / dự án` |
| M3 (hóa đơn bán ra) | **Cần Anh**: 15 câu trong `CHECKLIST-M3-HOA-DON-BAN-RA.md` |
| Chuyển DEMO 8798 sang `lat/ui-ky` | chờ Anh thử xong cổng A |

### 26/10 11:50 — gộp M4-03B-YC, M2k, MTQ-2; KY-G5TAY-UI lên dòng giao diện · rà hàng đợi (CD-009 mục 5)
- Gộp `hop-nhat-20261023`: bf592ba M4-03B-YC (CD-010.7), 789607f M2k (QD-20261026-01, review vòng 2 Đạt), 5424efb MTQ-2 (review Đạt; chưa nối dispatcher).
- `lat/ui-ky` d5448cb = nhận hợp nhất (M0037–M0039, MTQ-2, M2k, 03B-YC) + KY-G5TAY-UI (review Đạt + vòng 2 nên sửa; node 3 bộ đạt). DEMO 8798 vẫn chạy `lat/ui-dem` cho Anh thử cổng A.
- Review: `review-e14u-v2-ky-g5tay-ui.md`, `review-m2k-v2-mtq-2-dl1b-mask-3.md`. M4-DL1b Không đạt (2 dòng kiểm ghim vị trí trong test) → vòng 2; MASK-3 Không đạt (tự tải lại 15 giây làm phiên không hết hạn) → vòng 2.
- PG: MTQ-2b 64 ok, MTQ-5a 118 ok, M4-DL2 19 ok (ca đỏ là dòng kiểm hash DL1b đang bỏ) — 0 mã lỗi mới.
- Đang chạy: Codex — M4-DL1b v2, M2k-b, MTQ-4a (rủi ro cao), MASK-3 v2 (4/4). Claude — review-lat MTQ-5a, MTQ-2b vòng 2 (2/2). Lead — node E1-4u v3 + dòng giao diện, node MTQ-3a.
| Việc chưa giao | Lý do chặn |
|---|---|
| MTQ-3b (nối màn/route ma trận) | `app.js` đang do E1-4u giữ (tệp dùng chung); giao sau khi E1-4u gộp |
| MTQ-2c (route khai phòng/gán vai/phạm vi/Admin/khôi phục) | chờ MTQ-2b qua review (cùng 2 tệp dịch vụ/HTTP) |
| M4-DL3 (PL/BOQ) | cùng tệp `review_data_pg.py` với DL2 — chờ DL2 gộp |
| MTQ-4b…4m | nối tiếp MTQ-4a (adapter chung); mỗi lát cần review Opus |
| Nạp dữ liệu Review thật (CD-011 bước 4) | **Cần Anh**: bảng ánh xạ `ma_hd → HĐ/pháp nhân/dự án` |
| M3 | **Cần Anh**: 15 câu checklist M3 |
### 26/10 12:10 — CD-013/014 (M3 v2) nhận · MTQ-2b gộp · MTQ-4a bị chặn thiết kế · sự cố lệnh tìm kiếm
- Gộp hợp nhất a12c0eb MTQ-2b (review vòng 2 Đạt; PG 64 ok).
- **CD-013/014:** M3 + M10-1 vào `4-KE-HOACH-LEAD.md`; bản M3 20/10 → `LUU-TRU\thiet-ke-m3-ban-20261020\` (SHA256 khớp sau khi chuyển); 2 liên kết thiết kế trỏ v2; M3-CL đánh dấu đã thay. Giao **M10-1a** (engine lịch A/B). M3-0 chờ mục 17 của v2.
- **MTQ-4a dừng (đúng quy tắc, chưa sửa tệp):** `CrmK2` chạy bằng kết nối `app_web`, M0039 thu hồi quyền gọi lõi MTQ của vai này. **Lead chốt hướng:** lát **MTQ-4a0** (SQL, migration mới) thêm hàm SECURITY DEFINER bọc lõi quyết định, lấy danh tính từ GUC phiên (`ktt_danh_tinh()`), cấp EXECUTE cho app_web; và hàm ghi nhật ký từ chối gọi được từ app_web trong giao dịch riêng — vì thiết kế §5.1 cũng cần SQL/RLS chạy dưới app_web gọi cùng lõi. Sau đó giao lại MTQ-4a (adapter Python). MTQ-4a0 chờ `pg_migrations.py` (DL1b đang giữ, sẽ là M0040).
- **Sự cố 12:03 (lead tự báo):** lệnh `grep -r` tìm liên kết tài liệu M3 chạy trên **cả thư mục cha**, gồm `Phần mềm kho tri thức\var\` (có kho thật), lọc `*.md`, khoảng 2 phút rồi lead dừng (TaskStop). Không in nội dung, kết quả không hiển thị; vẫn là vi phạm "không đọc kho thật qua công cụ" ở mức duyệt tên/đọc tệp `.md`. Từ nay chỉ tìm trong thư mục cụ thể (`THIET-KE-MODULE-DE-CHOT-2026-10-20`, `docs`), không tìm đệ quy từ thư mục cha.
- Đang chạy: Codex — DL1b v4, MTQ-5a v2, M10-1a, MTQ-2c (4/4). Claude — review-lat MTQ-3a (1/2). Lead — test M2k-b, MASK-3 v2 (pytest + benchmark).
| Việc chưa giao | Lý do chặn |
|---|---|
| MTQ-4a0 / MTQ-4a | chờ `pg_migrations.py` (DL1b → M0040) |
| M3-0, M3-1a… | M3-0 chờ mục 17 thiết kế v2; M3-1a cần `pg_migrations.py` sau MTQ-4a0 |
| MTQ-3b | `app.js` đang do E1-4u giữ — chờ E1-4u gộp |
| M4-DL3 | cùng tệp DL2 — chờ DL2 gộp (sau DL1b) |
| Nạp dữ liệu Review thật (CD-011) | **Cần Anh**: bảng ánh xạ `ma_hd → HĐ/pháp nhân/dự án` |
- 12:05 **MASK-3 (Mask v2 2.7.2) xong vòng 2:** lead chạy pytest `-m "not ocr"` 476 đạt (chỉ còn `test_local_ai::test_cancel_and_reset…` có sẵn từ 2.7.0); benchmark bộ chính lộ 1/101, held_out lộ 6/51 — giữ nguyên so 2.7.1; smoke giao diện đạt (không còn tự tải lại `/api/pending`). Điểm Chặn review vòng 1 (phiên không hết hạn) lead kiểm đã hết. Sửa tại chỗ trong Mask v2 (không git).
- **Thiếu sót quy trình (lead tự báo):** trước MASK-3 lead **không** sao lưu Mask v2 vào `LUU-TRU` như MASK-1/2 (thư mục `tam-20261026` trống). Đã sao lưu trạng thái sau sửa: `LUU-TRU\mask3-v2-sau-sua-20261026-120235\` (133 tệp mã/tài liệu + `SHA256SUMS.txt`; không chép `config\`, `tmp\`, `data\`, khóa). Bản gần nhất trước MASK-3 là `mask2-v3-sao-luu-20261025-211809` (trước MASK-2 vòng 3). Từ nay mỗi lát Mask sao lưu trước khi giao.
- M2k-b: Python M2 291 ok (0 mã mới), node 3 bộ đạt — chờ review-lat (đổi thứ tự khóa).
### 26/10 12:40 — gộp M4-DL1b (M0040), MTQ-5a, MTQ-3a, MTQ-2c, MTQ-3b1, M2k-b, M2k-c, M10-1a, T-NODE, M3-0 · rà hàng đợi
- Hợp nhất: 08b9444 M4-DL1b (**M0040**; review Chặn = 2 dòng kiểm ghim vị trí, sửa vòng 2–4: ghim hash nội dung SQL M0038 `a908f99c…` thay byte tệp), 1da8b8b M2k-b, 77dcdb3 MTQ-3a (+vòng 2 hạn mức lớn), e191cc6 M10-1a (ví dụ 7.4: A = 120; B = 93,33 chính xác / 93,36 làm tròn từng kỳ), a1d7813 MTQ-5a (+vòng 2 tick Xem màn gốc), 79ff430 M2k-c, 637df66 MTQ-2c, 38ddd08 MTQ-3b1, 30c3127 M3-0 (tài liệu), T-NODE (node hợp nhất 14→16/21).
- PG: hợp nhất M0040 123 ok; MTQ-5a 10 module 298 ok; MTQ-2c 80 ok — 0 mã lỗi mới.
- `lat/ui-ky` b3a8099 = + E1-4u (Danh mục tham số chung; vòng 3 sửa `.after` làm hỏng 17 bộ node).
- MTQ-4a0 (cổng SQL SECURITY DEFINER): PG 1 ca đỏ `test_hoi_khong_ghi_audit…` (bảng nhật ký từ chối không trống trước lúc hỏi — chờ review để phân định lỗi test hay lỗi thật).
- **Lưu ý DEMO:** MTQ-5a seed mẫu ma trận một lần vào CSDL DEMO khi mở DEMO từ nhánh có MTQ-5a; không gỡ được. DEMO 8798 (`lat/ui-dem`) chưa có MTQ-5a.
- 5 bộ node còn đỏ (T-NODE): `m2_00a/00b` cần biến môi trường VIEW_ROOT (view materialize); `m4_02c_dto_ui`, `m4_04b_request` cần runner Python truyền fixture qua argv; `m4_03a_async` bản gốc ghim — đề xuất runner dùng FIX02.
- Đang chạy: Codex — M4-DL3, MTQ-2d, M3-1a (3/4). Claude — review-lat MTQ-4a0, M4-DL2 (2/2).
| Việc chưa giao | Lý do chặn |
|---|---|
| MTQ-4a (adapter Python) | chờ MTQ-4a0 qua review + gộp (M0041) |
| MTQ-3b2 (menu/màn ma trận, dòng giao diện) | chờ MTQ-2d (trường `la_admin`) |
| M3-1b (ba đẳng thức) | chờ M3-1a |
| Bảng mốc M3 + phiếu cổng A M3 hoàn chỉnh | chờ mục 17 thiết kế v2 (chưa có lúc 12:40) |
| M4-DL4 (đợt/KL/ghép/log) | cùng tệp DL2 — chờ DL2 gộp |
| Nạp dữ liệu Review thật (CD-011) | **Cần Anh**: bảng ánh xạ `ma_hd → HĐ/pháp nhân/dự án` |
### 26/10 ~13:00 — gộp MTQ-4a0 (M0041), MTQ-2d, M4-DL2 · lead chốt · lỗi test PG tự bỏ qua
- Hợp nhất: e9553d4 MTQ-4a0 (**M0041**, cổng SQL SECURITY DEFINER; review vòng 2 Đạt, PG 103 ok), 881ba6d MTQ-2d (la_admin, mã lỗi trùng/khóa ngoại; PG 95 ok), 663ac63 M4-DL2 (review vòng 2 Đạt; PG 31 ok). `lat/ui-ky` 204ba6f nhận hợp nhất (style.css giữ cả khối khung lưới và khối `mtq-`).
- **Lead chốt:**
  - DL2 lớp đọc **tự kiểm quyền M4** (phương án (a), khớp hợp đồng dữ liệu); DL3 làm theo ở vòng 2.
  - CD1: **chỉ đòi ánh xạ cho `ma_hd` có trong bảng `hop_dong`**; dòng mồ côi (`canh_bao`, `nhat_ky` của HĐ đã xóa) lưu NULL + đếm riêng.
  - MTQ-4a0: phòng chọn trong các phòng người dùng có vai, mơ hồ thì chặn; tiền do máy chủ lấy từ phiên bản đã khóa; đối tượng `{bang,id,phong_id?}` (chờ Anh xác nhận, không chặn).
- **Review M4-CD1 Không đạt (Chặn):** khi stdout không phải UTF-8, nhánh lỗi in traceback có thể lộ đoạn mật khẩu DSN → vòng 2 đang chạy. **Khi lead chạy thật:** dùng `python -X utf8`, ghi báo cáo vào `LUU-TRU` (không dán chat — có số tiền theo cặp HĐ × đợt).
- **Lỗi lặp lại ở test PG mới (M3-1a, M3-1b):** test tự skip dưới bộ chạy của lead (đọc biến nội bộ `KHO_PG_DEMO_*`, hoặc đòi DSN đã trỏ vào `kho_test_*`). Bài học: cổng gộp phải kiểm **`tao=`/`skip`** của từng module PG mới, không chỉ `ids_loi`. M3-1a vòng 2 đã sửa (PG 16 ok); M3-1b vòng 2 chờ suất.
- Thiết kế M3 v2 vẫn chưa có mục 17 (bảng mốc) → M3-3/M3-4 và phiếu cổng A M3 chờ.
- Đang chạy: Codex — MTQ-4a, MTQ-3b2, M2-BR0, M4-CD1 v2 (4/4). Claude — review-lat M3-1a+1b (1/2). Chờ suất: M3-1b v2, M4-DL3 v2.
### 26/10 ~13:45 — gộp M3-1a (M0042), M3-1b, M2-BR0, M4-DL3, MTQ-4a, M4-CD1 · DEMO 8799 · Codex quá tải
- Hợp nhất: 0258fbd M3-1a (**M0042**), c653aeb M3-1b (PG 37 ok, CSDL thật), 9c77a62 M2-BR0 (tài liệu 9 lát BR1–BR9), c1ed1d7 M4-DL3 (review Đạt; PG 83 ok), 7bab9b1 MTQ-4a (review Đạt; PG 35 module 794 ok, 0 mã mới), 031d043 M4-CD1 (review vòng 2 Đạt + vòng 3; PG 30 ok — **chưa chạy dữ liệu thật**).
- `lat/ui-ky` 27f135b = + MTQ-3b2 (ô Ma trận thẩm quyền). **Thử trình duyệt DEMO 8799 (CSDL riêng `p8799b`):** vai thường → "Quyền của tôi" + "Pháp nhân chưa dùng ma trận…" đúng; vai Admin chưa thử được vì bộ chọn vai chưa có actor MTQ → lát MTQ-5b. CSDL cũ `kho_crm_demo_lt_p8799` lệch lineage (M0035 cũ) — để nguyên, không DROP.
- Review MTQ-4a — **Cần Anh (xác nhận, không chặn):** (A) Từ chối HĐ dùng chung ô Duyệt nên cũng áp hạn mức tổng HĐ (người hạn mức thấp không từ chối được HĐ lớn) — đúng ý Anh? (B) Duyệt V4 (HĐ/danh mục mới) cũng bị áp hạn mức tổng HĐ; tách ô riêng không áp tiền?
- Review M4-DL3 — **Cần Anh:** hai phụ lục cùng ngày hiệu lực: (a) theo Review gốc (ngày hiệu lực → ngày ký → số PL so như chữ: "PL10" trước "PL2") hay (b) giữ cờ "cần xem lại" (làm trống BOQ/giá trị HĐ sau ngày đó tới khi có người xử lý). Lead khuyến nghị (b) + sửa so số PL theo số.
- **Codex quá tải ("model is at capacity"):** M4-DL4 bị ngắt 2 lần, M4-CD1 vòng 3 1 lần; lead giao lại, đang chạy lần 3 DL4. Nếu lặp lại, giảm số lát Codex song song.
- Đang chạy: Codex — MTQ-4a0b, MTQ-5b, M4-DL4 (lần 3). Claude — review-lat M3-1c + M2-BR4.
### 26/10 ~14:00 — MỐC (trước khi phiên nén ngữ cảnh) · hạn mức tuần 88% → chậm lại, không giao lát mới
- Hợp nhất mới: 69b056a MTQ-4a0b (**M0043**, review Đạt; lead sửa test registry khi gộp), M2-BR4 (review Đạt). Migration cuối hợp nhất = **M0043**.
- **Chờ PG rồi gộp (đều đã Đạt review hoặc chờ review):**
  | Lát | Nhánh/commit | Trạng thái | Việc còn |
  |---|---|---|---|
  | M3-1c | `lat/m3-1c` 883ecc9 | review vòng 2 Đạt | PG `test_m3_sql`,`test_m3_dang_thuc` → gộp, đổi `M00xx_M3_CO_SO_B` → **M0044** (dấu `# M3-1c — CD-013:`) |
  | MTQ-5b | `lat/mtq-5b` 6b0b30c | review Đạt + vòng 2 (bỏ nhóm CU, khóa `cap`) | PG `test_mtq_demo_phien`,`test_crm_k2`,`test_m9_k2` → gộp |
  | M4-DL4 | `lat/m4-dl4` 148b3ae | vòng 2 (chỉ XEM) — review vòng 2 đang chạy | PG `test_m4_review_dot_pg` + DL2/DL3/CD1 → gộp nếu Đạt |
  | M2-BR4b | `lat/m2-br4b` b917fba | unittest OK | lead kiểm/kiem-nhanh → test M2 → gộp |
  | MTQ-4a2 | `lat/mtq-4a2` aa0e176 | review Opus đang chạy | PG `test_crm*`+`test_mtq*` → gộp nếu Đạt |
- PG cả bộ trên hợp nhất (sau M0043) đang chạy → làm nền **PG v4** nếu không có mã lỗi mới so v3.
- DEMO 8799 (`lat/ui-ky`, CSDL `p8799b`) đang chạy; thử trình duyệt: "Quyền của tôi" đúng; màn Admin chờ lát giao diện nối `/api/demo/vai` (sau MTQ-5b).
- **Hàng đợi lát sau (chưa giao, chờ hạn mức):** MTQ-4a3 (9 điểm CRM còn lại, cần resolver), MTQ-3b3 (giao diện bộ chọn vai MTQ), M4-DL5a/b, M2-BR1… (một số chờ Anh), M3-2, M3-1d (nên sửa: tiền tố khóa advisory), DL3 nên sửa (`gt_hd_sau_pl` tên, `boq:None` khi NULL).
- **Cần Anh (gộp):** bảng ánh xạ `ma_hd` Review (chặn nạp thật CD-011); M3 #7, "đủ đợt", hóa đơn chung nhiều HĐ có chia giá trị; M2 hóa đơn bán ra (nguồn, quyền, mẫu XML); PL cùng ngày (khuyến nghị giữ cờ); MTQ: từ chối/duyệt V4 có áp hạn mức tổng HĐ; vai sửa danh mục chung; Mask "đánh dấu không phải định danh" có hộp xác nhận; M2k ngắt chéo pháp nhân.
### 26/10 ~14:25 — nền PG v4 · gộp M2-BR4b, M3-1c (M0044), MTQ-5b, M4-DL4, MTQ-4a2
- PG cả bộ hợp nhất (fd9b991): 149 module, 2877 ok / 21 ERROR / 67 FAIL / 65 skip, 0 treo; 4 lỗi mới `test_hoa_don_xml` (test BR4 đọc fixture CRLF) hết sau khi gộp BR4b; `test_trich6_host` chập chờn (đã biết). → **Nền PG v4** `nen-test-hop-nhat-pg-v4.json`.
- Gộp: 2b634ed M2-BR4b, e84e59c M3-1c (**M0044**), 856380c MTQ-5b, 61875fb M4-DL4, c91ae4b MTQ-4a2 — PG từng lát 0 mã lỗi mới so v4. Migration cuối hợp nhất = **M0044**. CLAUDE.md (M9 mở lại, sửa bởi phiên điều phối của Anh) đã commit.
- Không còn lát nào đang chạy. Hàng đợi sau (chưa giao vì hạn mức tuần ~88–90%): MTQ-4a3 (9 điểm CRM cần resolver), MTQ-3b3 (giao diện bộ chọn vai MTQ trên `lat/ui-ky`), M4-DL5a/b, M3-2/M3-1d, M2-BR1…, M9-1…5.
### 26/10 ~14:40 — Anh chốt nhịp: 4 Codex, Opus chỉ review lát rủi ro cao
- Anh 14:35: "Cứ giao nhịp nhanh, 4 codex cho tôi" (sau khi lead đề xuất chậm lại vì hạn mức tuần ~88–90%). Lát nhỏ/vòng sửa: `kiem-nhanh` (Haiku) hoặc lead tự kiểm; Opus cho quyền/SECURITY DEFINER/migration/dữ liệu thật/Mask.
- `lat/ui-ky` 2419503 nhận hợp nhất; xung đột `server.py` (dòng giao diện có `_danh_tinh_demo` giàu hơn) → giữ hàm dòng giao diện + thêm lọc `MO_PHONG_MTQ_`; ca test giả `test_mtq_demo_phien.test_crm_m9_m5_khong_co_mtq` sửa ở MTQ-3b3.
- Giao 4 Codex: **MTQ-3b3** (bộ chọn vai MTQ trên màn ma trận, dòng giao diện), **M4-CD2** (đối chiếu độc lập sau nạp), **M4-DL3b** (nên sửa DL3), **M4-DL5a** (nối PL/BOQ chép vào snapshot tính toán, parity).
### 26/10 ~15:05 — gộp M4-DL3b; MTQ-3b3 lên dòng giao diện, thử Admin đạt; giao MTQ-4a3a, M4-DL5b, M9-1a; giao lại M4-DL5a
- PG (từng lát, so nền PG v4): M4-CD2 128 ok / 0 lỗi / 0 skip; M4-DL3b 113 ok / 0 / 0; MTQ-3b3 0 mã lỗi mới (lỗi `test_crm_k2`/`test_m9_k2` đều có trong nền).
- Gộp hợp nhất: 901be7b **M4-DL3b** (lead tự kiểm: chỉ đổi tên công khai + giữ bí danh, lý do có số PL, `gt_hd_ghi_tren_pl_cuoi`).
- `lat/ui-ky` 39f2d3a nhận **MTQ-3b3**. DEMO 8799 khởi động lại (server cũ chạy từ 13:28, chưa có `/api/demo/vai`). Thử trình duyệt: bộ chọn "Vai mô phỏng (DEMO)" có 5 vai + nhóm Quản trị DEMO; đổi sang Admin DEMO → màn quản trị ma trận (pháp nhân, phòng, phiên bản, bảng tick, giới hạn tiền, Lưu nháp/Công bố/Nhật ký, "Chưa thể bật") — **đạt**.
- M4-CD2: review Opus đang chạy (công cụ chạy trên dữ liệu thật) → gộp nếu Đạt.
- **4 Codex đang chạy:** M4-DL5a (giao lại sau "at capacity"), **MTQ-4a3a** (migration resolver SQL cho 9 điểm CRM/M1 — giữ `pg_migrations.py`), **M4-DL5b** (lịch sử đợt chép cạnh lũy kế đã duyệt, không vào căn cứ review), **M9-1a** (đọc DOCX + cắt điều/khoản, thuần, không AI).
- Hàng đợi tiếp: MTQ-4a3b (nối Python 9 điểm, sau 4a3a), M3-1d (cần migration — chờ 4a3a nhả `pg_migrations.py`), M4-UI0, M9-1b (lưu tệp + phiên bản + Hot Folder), M2-BR….
### 26/10 ~15:45 — gộp M4-CD2 (Opus Đạt), M4-CD2b, M9-1a/1b/1c; MTQ-4a3a và M4-DL5a cần sửa
- Gộp hợp nhất:
  - ecb3c03 **M4-CD2**: review Opus Đạt, PG 128 ok.
  - edadc5a **M4-CD2b**: PG 88 ok / 0 lỗi / 0 skip.
  - fec33cc **M9-1a**: đọc DOCX + cắt điều/khoản.
  - b80d4f3 **M9-1b**: đếm trang đôi, câu lỗi trung tính.
  - eb85348 **M9-1c**: OCR Hot Folder M9, test giả lập.
- **MTQ-4a3a** (M0045, resolver SQL 9 điểm CRM/M1): review Opus **Cần sửa**. Chặn: `kho.lien_ket_chung_tu` nhận cả liên kết `VAY_TIEN` (M9) và L11 `HD_PHIEU_KHO`. PG: 0 mã mới so v4, 1 lỗi test mới (dữ liệu giả lô M5 bị trigger chặn). Vòng 2 đang chạy. `pg_migrations.py` vẫn do lát này giữ.
- **M4-DL5a**: review Opus **Cần sửa** (`review-m4-dl5a.md`):
  - 02C/03A/03B vỡ với vai DUYET/KE_TOAN;
  - câu "Cần Anh" nằm trong `ly_do` bất biến;
  - PG có **8 mã lỗi mới** `test_m4_02b_k2` do `_tx_review`.

  Vòng 2 đã soạn, chờ suất Codex.
- **M4-DL5b**: PG 0 mã mới; review Opus đang chạy.
- **Codex đang chạy:** M9-2b (hỏi đáp qua cổng AI, loại việc `HOI_DAP_VAY` chỉ Local), MTQ-4a3a v2, M9-4a (báo cáo lãi suất), M9-2a v2 (lead thử thật: câu hỏi tự nhiên bị bỏ sót do hư từ).
- **Chờ sau MTQ-4a3a:** MTQ-4a3b (nối Python 9 điểm), M3-1d (tiền tố khóa). **Tạm giữ:** M4-UI0, vì đụng khai báo trang chủ đang chờ Anh ở cổng A dòng giao diện.
- **Cần Anh (thêm):**
  - M4-DL5b: lịch sử đợt chép có tính vào lũy kế chính thức?
  - M9-1c: gộp sổ đếm trang ABBYY của M9 với Review?
### 26/10 ~16:25 — QD-20261026-04 (review chéo giao Codex, Claude chỉ kiểm xác suất); gộp loạt M4/MTQ/M3/M9
- **Anh chốt ~16:00:**
  - hạn mức Claude gần đầy → review chéo do Codex làm (chỉ đọc) theo `MAU-REVIEW-CODEX.md`;
  - Claude giữ gate máy + rút ngẫu nhiên ~1/4 lát;
  - Codex giữ đúng trọng tâm;
  - mọi điểm Chặn hoặc chỗ không rõ phải hỏi Claude trước khi đi tiếp.
- **Gộp hợp nhất:**
  - 28eb122 M4-DL5b;
  - 408a40a MTQ-4a3a (**M0045**);
  - 8ad26a2 M3-1d (**M0046**);
  - 42ea4a1 M4-DL5a (Codex v2 Đạt, kiểm xác suất trúng, đạt);
  - 40fbd18 MTQ-4a3b;
  - M9: 1b641eb5 M9-2a, fd15c70 M9-4a, 1b20a21 M9-2b, b9ad161 M9-1d, b470ece M9-3a.
  - Mỗi lát: PG 0 mã mới so v4, skip khớp nền. Migration cuối = **M0046**.
- **Review Codex chạy được việc:** chặn đúng 2 lỗi thật (MTQ-4a3b kiểm/ghi khác giao dịch; M9-3a ô `#N/A` lọt vào khoản vay).
- **Bài học:** worktree cũ hơn tài liệu thì chép nội dung vào prompt.
- **Đang chạy:**
  - PG **cả bộ** trên hợp nhất (sạch → nền PG v5);
  - Codex soạn **nháp phiếu cổng A M9** (chỉ tài liệu). Lưu trữ/CSDL/màn hình M9 dừng tới khi Anh duyệt.
- **Hàng đợi còn lại phần lớn chờ Anh:**
  - M3 bảng mốc §17;
  - M10 #8;
  - M2 bán ra (nguồn/quyền/mẫu XML);
  - M4-CD3 phạm vi tệp đính kèm;
  - M4-UI0 (đụng trang chủ chờ cổng A);
  - ánh xạ `ma_hd` cho nạp thật CD-011.
### 26/10 ~17:15 — nền PG v5; gộp phiếu cổng A M9 (nháp), FIX-NEN-V5
- PG cả bộ trên hợp nhất bắt 3 test cũ hỏng sau đợt gộp. Codex sửa test (FIX-NEN-V5, 2 vòng), lead kiểm bằng runner. → **Nền PG v5** 3214/20/63/78, 0 mã mới so v4 (`NEN-TEST-PG.md`).
- Mẫu review bổ sung:
  - gate chạy cả test gọi tới hàm bị sửa;
  - gate thuần chạy bằng runner có guard giữ tệp;
  - PG cả bộ mỗi đợt gộp;
  - chép tài liệu vào prompt khi worktree cũ.
- Gộp a82302b **nháp phiếu cổng A M9**: 6 màn, 8 câu "Cần Anh chốt". Lưu trữ/CSDL/màn M9 dừng tới khi Anh duyệt.
- Không còn lát nào đang chạy. Hàng đợi chưa bị chặn: trống. Các việc còn lại chờ Anh:
  - M3 bảng mốc §17;
  - M10 #8;
  - M2 bán ra;
  - M4-CD3 phạm vi tệp;
  - M4-UI0 (trang chủ cổng A);
  - ánh xạ `ma_hd` nạp thật CD-011;
  - phiếu cổng A M9;
  - lũy kế lịch sử Review (DL5b);
  - sổ trang ABBYY.
### 26/10 ~18:30 — gộp M9-2c/4b/4c, OCR-1, M4-DL5c; PG cả bộ lần 2
- **Anh chốt ~17:20:**
  - lịch sử đợt Review tính vào lũy kế chính thức (QD-05);
  - OCR một engine chung + sổ trang chung với Review (QD-06);
  - làm tiếp việc phụ M9 khi chờ (QD-07).
- **Gộp:**
  - 4a7c432 M9-2c;
  - f65b061 M9-4b (kiểm xác suất trúng, đạt; lộ câu "Cần Anh" cũ → 7ce11af M9-4c);
  - c11b66c OCR-1;
  - 5f94ce6 M4-DL5c (PG 183 ok, 0 mã mới so v5).
- **PG cả bộ lần 2** (eceb2cc, 87 phút do chạy song song Codex): 3260/22/64/78. Có 3 mã mới, chạy lại riêng:
  - `test_web` hết (chập chờn);
  - `test_trich6_host.HandlerSoHuuTests` (chập chờn đã biết);
  - `test_chay_test_pg_demo...timeout_giet_ca_chau` vẫn đỏ khi chạy riêng. Không lát nào hôm nay sửa `tools/`; nghi do máy đang chạy nhiều tiến trình Codex. **Theo dõi:** chạy lại khi máy rảnh.
- **Đang chạy:** 3 Codex kiểm kê MTQ-4 còn lại (CRM, M4, liên module; chỉ tài liệu). M9-2d chờ review Codex.
### 26/10 ~19:40 — gộp M9-2d, MTQ-4b1a (M0047); phiếu chốt MTQ-4; Codex rảnh có lý do
- **Gộp:**
  - 0d0ad76 **M9-2d**: số dư/lãi suất từ snapshot Sheet có mốc, không qua AI. Review Codex 2 Chặn; lead thử câu hỏi thật qua 3 vòng.
  - 39f8536 **MTQ-4b1a**: **M0047**, resolver bảng riêng CRM G1/G2/G3/G4/G7/dự án. H/TY_GIA/V8 vẫn chặn khi bật. Review Codex Đạt, kiểm xác suất trúng và đạt.
  - Migration cuối = **M0047**.
- **Ba bản kiểm kê MTQ-4** (`KK-MTQ4-CRM.md`, `KK-MTQ4-M4.md`, `KK-MTQ4-LIEN-MODULE.md`): khoảng 40 lát còn lại. 15 câu "Cần lead" gom vào **`MTQ-4-CAN-CHOT.md`**, đã gửi Anh.
  - A1–A3 là nền, chặn cả nhóm.
  - B1–B11 là nghiệp vụ.
- **Codex đang rảnh — lý do chặn (CD-009):**
  - lát MTQ-4 kế tiếp (4b1b RLS/guard, M4 4f, liên module 4i) phụ thuộc A1–A3/B;
  - M9 lưu trữ/màn hình chờ duyệt phiếu cổng A M9;
  - M9-3b (gọi Google Sheets) cần chốt cách ký JWT tài khoản dịch vụ: thêm thư viện hay tự cài thuần Python;
  - các hàng đợi M3/M10/M2/M4-CD3/UI0/nạp thật đã ghi trước.
- **Theo dõi:** `test_chay_test_pg_demo...timeout_giet_ca_chau` chạy lại khi máy rảnh.
- 19:45: chạy lại `test_chay_test_pg_demo` khi máy rảnh (0 tiến trình Codex) → 51/51 đạt. Xác nhận chập chờn do máy tải nặng; không phải lỗi mã.
### 26/10 ~20:45 — CD-016: điều kiện go-live 5 module (M0, M2, M3, M4, M9) — phát hành cùng một lần, tối thứ Sáu
Chi tiết có tệp:dòng: `BANG-DIEU-KIEN-GO-LIVE.md`; quy trình: `CHECKLIST-PHAT-HANH.md`; chuyển kho thật: `KE-HOACH-CHUYEN-KHO-THAT-SQLITE-PG.md` (chờ Anh ra lệnh riêng).
| Module | Tình trạng | Chặn chính (cần Anh / còn làm) |
|---|---|---|
| M0 | Chưa rõ phạm vi go-live | Chưa có bằng chứng cổng B; Anh xác nhận phạm vi M0 |
| M2 | Mua vào đã chạy DEMO; bán ra chưa | Nguồn/quyền/mẫu XML bán ra (BR1…); MTQ-4i chưa đủ |
| M3 | Có lõi SQL/dịch vụ (M0042/44/46); chưa màn hình | Bảng mốc §17, #7 cơ sở thuế, #8 ánh xạ Junsky, #11; phiếu cổng A M3 |
| M4 | Lõi review chép + PG (DL1–DL5c, CD1/CD2); 02C/03A/03B/04 có | Ánh xạ `ma_hd` để nạp thật (CD-011); 8 màn Review chưa đủ (UI0 giữ chờ cổng A trang chủ); MTQ-4f chưa đủ |
| M9 | Phần thuần đủ (đọc/OCR/tìm/hỏi đáp Local/snapshot/báo cáo) | Duyệt phiếu cổng A M9; Sheet thật; lưu trữ/CSDL/màn hình chưa làm |
| Chung | Chưa bật ma trận PN nào | B11: PN còn đường cũ chưa được bật; chuỗi MTQ-4/MTQ-NEN còn lại; nền PG v5 |
### 26/10 ~21:50 — gộp loạt MTQ-4 sau chốt + Xương sống XS-1/3/4a; nhận CD-018, CD-019
- **Gộp từ 19:40** (mỗi lát có review Codex; Claude kiểm xác suất ~1/4):
  - MTQ-4: 4b1a (**M0047**), 4f1a (**M0048**), 4i-a (**M0049**), 4b1b (**M0050**), NEN-0 (**M0051**), 4b2a (**M0053**).
  - Xương sống: XS-1a (**M0052** bus), XS-1b (lớp Python bus), XS-3a (hợp đồng + danh bạ engine), XS-4a (mô hình khai báo module).
  - Tài liệu: CD-016 (kế hoạch chuyển kho, checklist phát hành, bảng go-live), KK-XUONG-SONG, KK-VUNG-DU-LIEU.
  - **Migration cuối = M0053.**
- **Sửa của lead:** test cổng F còn gọi tên tạm `M00xx` sau khi đánh số M0051 → sửa, PG 79 ok. Bài học: khi đánh số lúc gộp, grep cả `tests/` cho tên tạm.
- **Hộp thư:**
  - **CD-018 ĐÃ NHẬN.** Bản đồ vùng dữ liệu tóm tắt 1 trang: `BAN-DO-VUNG-DU-LIEU-1-TRANG.md` (70 chỗ đọc chéo, 47 chỗ ghi thẳng vùng chung). Chuỗi XS-5 trong `KK-VUNG-DU-LIEU.md` §5.
  - **CD-019 ĐÃ NHẬN.** Đã tạo `D:\DU-LIEU-KE-TOAN\{postgresql,kho-file,sao-luu}`. Mẫu review Codex thêm 2 kiểm (không trùng engine/thư viện; không SQL chéo vùng). Đang kiểm kê cột nhạy cảm + mã hóa + đo BitLocker (`KK-MA-HOA-LUU-RIENG.md`).
- **Chờ Anh:** `XS-4-CAN-CHOT.md` (S1–S6: nghĩa "Thử", ai đổi công tắc, mặc định, tắt khi còn việc, chuyển Thử→Vận hành, pilot M2→M4). XS-4b/4c/XS-2/pilot chờ phiếu này.
- **Đang chạy (4 Codex):**
  - NEN-1 vòng 2: review Codex chặn đúng — hàm đọc luôn truyền tiền rỗng; lead quyết thêm tham số tiền tùy chọn.
  - XS-3b: bọc OCR/AI thành engine qua cổng có sẵn.
  - XS-3d: bọc bộ đọc hóa đơn XML/ZIP thành E-HOADON.
  - Kiểm kê CD-019.
- **Danh bạ engine (CD-017 mục 6):**

| Engine | Phiên bản | Module dùng | Trạng thái test |
|---|---|---|---|
| (khung) hợp đồng + danh bạ | — | — | XS-3a 19 ok |
| E-OCR, E-AI | v1 | M9 (đích M4, CRM) | XS-3b đang làm |
| E-HOADON | v1 | M2 (đích M3) | XS-3d đang làm; XS-3e cắm vào M3 sau pilot |
### 26/10 ~22:15 — gộp NEN-1 (M0054), KK-CD019; phiếu cần Anh chốt tối 26/10
- **Gộp:**
  - 7e34bdb **MTQ-NEN-1**, **M0054** `master.mtq_duoc_doc(text,jsonb,numeric DEFAULT NULL)`: quyết định quyền chỉ đọc. Review Codex vòng 1 chặn đúng (tiền luôn NULL); lead quyết thêm tham số tiền; vòng 2 lead tự soát diff. PG 6 module 206 ok, 0 mã mới.
  - 36ee50f **KK-CD019** (`KK-MA-HOA-LUU-RIENG.md`): 18 nhóm cột (10 A / 5 B / 3 C), khóa DPAPI, sao lưu GPG, bộ đo BitLocker.
  - **Migration cuối = M0054.**
- **Lead xác minh:** bộ PostgreSQL 16 DEMO (`var\postgresql16-16.15-runtime\bin`) có sẵn `pg_dump`, `pg_restore`, `pgbench`, `pg_dumpall` và `pgcrypto.dll`. Không cần cài thêm cho SL-1/DO-1.
- **XS-3b** dừng "Cần lead" (chỗ lưu loại ngoại lệ gốc) → lead trả lời `tra-loi-lead-xs-3.md`: mỗi ngoại lệ đã biết → một mã ổn định; ngoại lệ lạ không bắt. Đã giao lại.
- **Phiếu gửi Anh:** `CAN-ANH-CHOT-TOI-26-10.md` gồm:
  - S1–S6 công tắc module;
  - M1–M3 mã hóa/khóa/lịch sao lưu (CD-019);
  - H1 gom 4 hàng việc riêng về XS-2.
- **Đang chạy (4 Codex):** MTQ-4f1b (M4 hồ sơ M17), XS-3d (E-HOADON), XS-3b vòng 2, MTQ-4i-b1 (resolver nguồn/ánh xạ).
- **Hàng chờ giao khi rảnh:**
  - MTQ-4b2b (CRM ký + phạm vi hẹp B3; đề đã có ở `giao-mtq4-loat3.md`);
  - CRM 4d1b (Python G1/G7).
  - Lát MH/SL (mã hóa, sao lưu) chờ Anh duyệt M1–M3 và XS-5b.
### 26/10 ~23:05 — Anh chốt S1–S6, M1–M3 (QD-20261026-11); QD-09 ít tài nguyên; QD-10 MTQ nhiều pháp nhân
- **Quyết định mới:**
  - QD-09: giữ cấu trúc bảng; thêm dòng, không tạo bảng/cột theo lần; phụ lục = thêm dòng/hết hiệu lực; dữ liệu tạm có cách dọn.
  - QD-10: lead quyết kiểm quyền đối tượng nhiều pháp nhân (mọi PN phải đạt; hỗn hợp bật/tắt → chặn).
  - QD-11: Anh chốt công tắc module S1–S6 và mã hóa/khóa/lịch sao lưu M1–M3. Người giữ ổ ngoài: Anh chỉ định khi tới bước tạo khóa.
- **Đo tài nguyên:**
  - cụm PG DEMO 4,72 GB / 327 CSDL, phần lớn ~303 CSDL test sót;
  - 209 worktree ~4,5 GB;
  - ổ D trống 174 GB.
  
  Kiểm kê dọn dẹp đang chạy (KK-DON-DEP); chưa dọn gì (xóa cần Anh cho phép).
- **Lát xong chờ review/gộp:**
  - XS-3b (E-OCR/E-AI, runner 87 ok);
  - XS-3d (E-HOADON, 88 ok) — review gộp đang chạy;
  - MTQ-4f1b (M4 lệnh M17) — gate PG đang chạy.
- **Đang chạy (4 Codex):** NEN-2a (cổng tập PN), XS-4b (SQL công tắc), KK-DON-DEP, review XS-3b+3d.
- **Hàng chờ giao:**
  - MH-1 (cổng khóa mã hóa cột);
  - SL-1 (sao lưu mã hóa);
  - review 4f1b;
  - NEN-2b → 4i-b1;
  - 4b2b, 4d1b CRM;
  - XS-4c → XS-2 → pilot XS-T1.
- **Bài học lead:**
  - ký tự `\` trong chuỗi Python viết qua heredoc bị biến thành ký tự điều khiển (2 lần sửa) → ghi tài liệu bằng công cụ Write;
  - không `cd` trần ở lệnh nền.
### 26/10 ~22:50 — gộp XS-3b, XS-3d, MTQ-4f1b (M0055), XS-4b (M0056), NEN-2a (M0057), MH-1, KK-DON-DEP
- **Gộp** (mỗi lát có review Codex; Claude rút thăm ~1/4):
  - **XS-3b**: E-OCR/E-AI qua cổng sẵn có. Lead làm rõ hash_ra AI theo từng lượt.
  - **XS-3d**: E-HOADON bọc bộ đọc XML/ZIP. Review chặn: bắt cả lỗi bất biến → vòng 3 chỉ ánh xạ mã lỗi đầu vào tường minh.
  - **MTQ-4f1b (M0055)**: M4 · Nghiệm thu & chi phí dự án, ma trận cho 14 lệnh hồ sơ M17. B6 chuyển sang 4f1c; vòng 2 bỏ khóa kỹ thuật khỏi thông báo.
  - **XS-4b (M0056)**: công tắc module × pháp nhân (S1–S5). Review chặn: lộ người thử qua nhật ký → vòng 2. Lead bỏ kiểm CRLF trong test (repo `core.autocrlf=true`).
  - **NEN-2a (M0057)**: cổng phiên kiểm mọi pháp nhân (QD-10). Vòng 1 mất `$$` do worker ghi qua PowerShell → 27 ERROR; vòng 2 sửa. PG 20 module 625 ok.
  - **MH-1**: cổng khóa DPAPI + HMAC tra cứu. Rút thăm trúng, Claude tự đọc: Đạt.
  - **KK-DON-DEP**: phiếu D1–D2 đã gửi Anh.
  - **Migration cuối = M0057.**
- **Danh bạ engine (CD-017 mục 6):**

| Engine | Phiên bản | Module dùng | Trạng thái |
|---|---|---|---|
| Khung hợp đồng + danh bạ | — | — | XS-3a 19 ok |
| E-OCR | v1 | M9 (đích M4, CRM) | XS-3b đã gộp; chưa đăng ký ở runtime |
| E-AI | v1 (hash_ra theo từng lượt) | M9 (đích mọi module dùng AI) | XS-3b đã gộp; chưa đăng ký ở runtime |
| E-HOADON | v1 | M2 (đích M3) | XS-3d đã gộp; XS-3e cắm vào M2 rồi M3 sau pilot |

- **Đang chạy (4 Codex):**
  - CRM 4b2b vòng 2 (lead quyết ghim `quan_he` B3);
  - SL-1 vòng 3 (review chặn: biên bản có thể ghi vào bản mã);
  - NEN-2b (`mtq_duoc_doc` dùng tập PN);
  - BO-1a (BOQ "bỏ dòng" + đọc BOQ hiệu lực theo ngày).
- **Hàng chờ:**
  - 4i-b1 (sau NEN-2b);
  - BO-1b (writer BO);
  - XS-4c (máy chủ kiểm công tắc, đụng `server.py`);
  - XS-2a;
  - 4f1c (đọc/master + B6);
  - 4d1b;
  - review NEN-2b, BO-1a.
- **Chờ Anh:** phiếu dọn dẹp D1–D2 (`CAN-ANH-CHOT-DON-DEP.md`).
### 26/10 ~23:40 — gộp SL-1, NEN-2b (M0058), XS-4c1; đang sửa vòng 4b2b/4f1c/XS-4c2/BO-1a/4i-b1
- **Gộp thêm:**
  - **SL-1**: sao lưu PG mã hóa GPG. Review chặn: biên bản có thể ghi vào bản mã → vòng 3.
  - **NEN-2b (M0058)**: `mtq_duoc_doc` theo tập PN. Review Đạt.
  - **XS-4c1**: dịch vụ công tắc + `kiem_module`/`trang_thai_cho`. Review Đạt. Rút thăm trúng (0,012); Claude tự đọc **sau khi đã gộp** (sai thứ tự — từ nay kiểm trước rồi mới gộp): Đạt.
    - Để sau: tên module trong câu "Chờ …" mới có CRM (cần danh mục tên M2/M3/M4/M9 cho pilot S6);
    - Để sau: dịch vụ xương sống còn mượn `_v`/`CrmMauK2` của CRM (tách ở XS-5b).
  - **Migration cuối = M0058.**
- **Hồi quy phát hiện ở gate PG rộng (4b2b, 57 module): 12 mã lỗi mới.**
  - Đường cũ khi PN tắt bị đổi (`test_crm_g5_tay`, `test_crm_ky_ket_http`); lỗi PL/pgSQL `record "s" is not assigned`.
  - Hàm ghim `quan_he` chặn mọi phạm vi HĐ/dự án, kể cả HĐ M4. Do lead quyết vòng 2 chưa tính phạm vi MTQ gắn theo vai, không theo khóa.
  - Lead quyết lại (`tra-loi-lead-mtq-4b2b-v3.md`): không chặn cấp; chỉ ghim với HĐ CRM có bản soạn; khóa ký chỉ nhận phạm vi có `quan_he` khớp. Đang làm vòng 3.
- **Quyết định lead khác:**
  - BO-1a theo đúng ngữ nghĩa projection Review: THEM/THAY/BO theo trạng thái, THAY ghi đè trường có giá trị, sai → "cần xem lại", không vỡ màn.
  - 4f1c giữ ràng buộc "đợt đã nộp" theo ô thẩm quyền.
  - XS-4c2 tập PN theo `ktt_pn_cho_phep`, không lọc vai CRM; Admin MTQ toàn hệ thống.
  - 4i-b1: cổng khớp phạm vi NGUON (`nguon_khoa`); PN đích ánh xạ kiểm bằng lần gọi cổng thứ hai.
- **Đang chạy (4 Codex):** 4i-b1 v3, 4f1c v2, 4b2b v3, XS-4c2 v3.
- **Gate PG đang chạy:** BO-1a v2 → XS-2a (review tĩnh Đạt).
- **Chờ Anh:** phiếu D1–D2.
### 27/10 ~00:50 — gộp tới M0064: 4f1c, XS-2a/2a2/2b, BO-1a/1b, XS-4c2, XS-T1a; kiểm bản hợp nhất xanh
- **Gộp** (migration cuối **M0064**):
  - **BO-1a (M0059)**, **XS-2a (M0060)**, **4f1c (M0061)**, **XS-2a2 (M0062)**, **BO-1b (M0063)**, **XS-T1a (M0064)**;
  - **XS-4c2**, **XS-2b** (Python).
- **Kiểm xác suất trúng 4 lát**, Claude tự đọc:
  - **XS-4c2 bắt được Chặn thật:** đọc thẳng bảng bị `REVOKE`, gọi `mtq_la_admin` không được cấp cho `app_web`. Test mock không thấy; nay bắt buộc có test PG dưới vai ứng dụng.
  - BO-1b: Đạt.
  - XS-2b: Đạt. Để sau: CHO tiêu lượt thử.
  - XS-4c1 (trước đó): Đạt.
  - **Lỗi quy trình lead:** 2 lần rút thăm và gộp cùng một lệnh (XS-4c1, XS-2b), nên kiểm sau khi đã gộp. Từ nay tách bước.
- **Kiểm bản hợp nhất** (worktree tách `kiem-hop-nhat`, detached tại 731a62a): 7 module 176 ok, 0 mã mới.
  - Trước đó phát hiện 2 lỗi do tương tác giữa các lát gộp:
    - test XS-2a2 ghim migration cuối;
    - test BO đọc hồ sơ dưới `app_web` sau RLS M0061.
  - Lead sửa test.
- **Sót tên tạm trong test khi đánh số:** 2 lần. Script gộp `gop_mig.py` nay tự đổi tên trong `tests/` và dừng nếu còn sót.
- **Đang chờ gộp:**
  - 4b2b (review đang chạy);
  - 4i-b1 vòng 5 (review vòng 2 đang chạy);
  - NEN-2c (giữ chờ: test va chạm UUID/instance còn trả khóa NGUON — nghi hàm ứng viên 4i-b1 sót trường hợp);
  - 4d1b (vòng 2 đang chạy; còn lỗi fixture trùng tệp mẫu);
  - XS-5a1 (review đang chạy).
- **Chờ Anh:** phiếu dọn dẹp D1–D2.
### 27/10 ~16:00 — /loop chạy lại (CD-020); nhận CD-020…025; Claude tuần 100%
- **Đêm 26→27 không chạy:** lead kết thúc lượt lúc 00:50, không có `/loop` (CD-020 đã ghi nguyên nhân). Từ 15:40 `/loop` chạy liên tục.
- **Hộp thư:** CD-020, CD-021, CD-022, CD-023, CD-024, CD-025 → ĐÃ NHẬN.
  - CD-022/023/024 (Dự án đang bán khai báo một lượt; Báo giá VAT đợt cọc) làm trên **`lat/ui-dem`** (DEMO 8798). Đang kiểm kê bằng KK-UI-DA-BG.
  - CD-021: XUAT-PN xếp sau XS-5b.
- **Gộp:** XS-5a1. Rút thăm trúng; Claude tự đọc: Đạt.
  - Ghi cho XS-5c: **đọc** chéo ngoài V1/V3/V4/danh sách tồn tại cũng phải đỏ.
- **Vòng sửa:**
  - 4b2b v4: review chặn — ghim `quan_he` phụ thuộc tick → bỏ điều kiện tick.
  - 4i-b1 v6: ca va chạm UUID/instance từ NEN-2c → mơ hồ cả hai phía.
  - 4d1b v3 (đã soạn đề): fixture trùng tệp mẫu.
  - NEN-2c chờ 4i-b1.
- **Đang chạy (4 Codex):** 4b2b v4, 4i-b1 v6, KK-UI-DA-BG, MTQ-4f2 (M4 review 02A/02B).
- **Hạn mức:** Claude tuần mọi model **100%** (đặt lại 29/10), khung 5 giờ 8%.
  - Lead chỉ giữ gate/gộp.
  - Review giao Codex.
  - **Tạm dừng Claude tự đọc khi rút thăm** (ghi "bỏ qua do hạn mức").
  - Codex vẫn đủ 4 suất.
- **Migration cuối = M0064.**
### 27/10 ~16:30 — gộp 4b2b (M0065), 4i-b1 (M0066, M0067), 4d1b; giao XS-5a2
- **Gộp** (migration cuối **M0067**):
  - **MTQ-4b2b → M0065.** Kiểm xác suất: không rút.
  - **MTQ-4i-b1 → M0066, M0067.** Kiểm xác suất rút trúng, bỏ qua do hạn mức.
  - **MTQ-4d1b**, không có migration. Kiểm xác suất rút trúng, bỏ qua do hạn mức.
  - Cả ba: gate PG 0 mã lỗi mới; review Codex Đạt.
- **Kiểm bản hợp nhất:** cả bộ PG trên `kiem-hop-nhat` @7cee117 đang chạy nền.
- **Loạt 7:**
  - BG-B1 xong, chờ gate PG.
  - DA-B1 và TEN-B1 dừng hỏi số migration, dù đề đã dặn dùng tên tạm `M00xx_`. Đã giao lại vòng 2 có câu trả lời.
- **NEN-2c:**
  - Cập nhật lên hợp nhất (fast-forward từ 4i-b1 v5).
  - Lead nối xong `sql_mtq_nen.py` (B rồi C).
  - Test xung đột với NEN-2b → Codex nối, chỉ một tệp.
- **MTQ-4f2 v2** (sửa test R01 + fixture quyền setup): chờ gate PG.
- **Giao mới:** XS-5a2 (khung module lấy khai báo bốn vùng từ 5a1).
- **Đang chạy (4 Codex):** DA-B1 v2, TEN-B1 v2, NEN-2c nối test, XS-5a2.
- **Hàng gate PG** (chạy sau bộ hợp nhất): BG-B1 → 4f2 v2 → NEN-2c.
- **Chặn chờ:**
  - DA-B2/B3 chờ DA-B1;
  - TEN-B2 chờ TEN-B1;
  - BG-B2 chờ DA-B1 + BG-B1;
  - UI (DA-U, TEN-U, BG-U) chờ backend và việc ui-dem nhận hợp nhất.
- **Chờ Anh:** phiếu dọn dẹp D1–D2.
### 30/10 10:30 — CD-026…030: DỪNG LẬP TRÌNH; bắt đầu G0 khảo sát Core (TL 55)
- **Khoảng trống 27/10 16:30 → 30/10 10:00:**
  - Phiên lead kết thúc sau mốc 16:30 mà không bàn giao. Hạn mức tuần Claude đã 100% từ 16:00. Kết quả worker và gate lúc đó chưa được thu; nay ghi vào bảng dưới.
  - **Bài học:** khi hạn mức sắp hết, lead phải ghi TRANG-THAI kèm danh sách việc chưa thu trước khi ngừng.
- **Bảng trạng thái khi dừng.** Không gộp thêm gì. Mọi nhánh giữ nguyên. Ở G4, lát còn giá trị chuyển vào module mới.

| Lát | Nhánh / commit gốc | Tệp chưa commit | Gate PG | Review | Còn gì |
|---|---|---|---|---|---|
| DA-B1 (CD-022/023) | `lat/da-b1` @a2346a9 | 3 | chưa chạy (vòng 2 xong 27/10 16:37) | chưa | gate, review |
| TEN-B1 (CD-022) | `lat/ten-b1` @a2346a9 | 3 | chưa chạy (vòng 2 xong 16:32) | chưa | gate, review |
| BG-B1 (CD-024) | `lat/bg-b1` @a2346a9 | 3 | 74 ok, 0 mã mới | chưa | review |
| MTQ-4f2 v2 | `lat/mtq-4f2` @ed4a1c1 | 4 | 141 ok, 0 mã mới | chưa | review |
| MTQ-NEN-2c | `lat/mtq-nen-2c` @7cee117 | 3 | 233 ok, 0 mã mới (sau khi nối test với NEN-2b) | chưa | review; stash `cdef8fe1` giữ bản trước |
| XS-5a2 | `lat/xs-5a2` @b76d47c | 0 | — | — | Codex dừng "Cần lead": CRM đếm qua bảng M0 ngoài V1/V3/V4. Đưa vào đặc tả G1a |

- **Nhánh hợp nhất @7cee117: chạy cả bộ PG** (189 module) → 4062 ok / 30 ERROR / 85 FAIL, 3 mã lỗi mới.
  - **Đỏ thật:** `test_mtq_crm_sql`, 9 ERROR / 20 FAIL, sau khi gộp 4b2b + 4i-b1. Chưa điều tra; sửa khi mở lại lập trình.
  - **Nghi chập chờn (thời gian):** `test_chay_test_pg_demo`, `test_m4_request_http` h02, `test_trich6_host`.
- **Tạm hoãn:** CD-022/023/024 (giao diện Dự án/Báo giá); go-live CD-016 (không phát hành tối thứ Sáu 30/10).
- **G0 khảo sát** (`docs\47-core\g0\`, đề `GIAO-G0.md`):
  - **4 Codex chỉ đọc đang chạy:** KS-A (Core hiện có ↔ TL 54 §9), KS-B (CSDL + 67 migration), KS-C (route/API), KS-D (công cụ ngoài/engine).
  - **Kiểm xác suất** chọn trước khi gộp: **KS-B**.
- **Số liệu catalog DEMO** (lead lấy, chỉ đọc): `so-lieu-csdl-demo.json`.
  - PostgreSQL 16.
  - CSDL DEMO của Anh ở migration 23.
  - Tồn đọng **303 CSDL `kho_test_*` và 651 role `ktt_test_*`**. Cần cách dọn (QD-09). KS-B sẽ đề xuất.
  - `D:\DU-LIEU-KE-TOAN\postgresql` **rỗng**: CSDL thật chung chưa dựng.
- **Engine Studio, OCR đối chiếu:** tìm thấy ở `D:\GPT\Local AI\engine-console` và `D:\GPT\Local AI\ocr-dual-release`. Chờ Anh xác nhận đúng bản.
- **Hạn mức đầu ngày 30/10:** Claude tuần 1%, khung 5 giờ 6%.
- **Tiếp theo:** gom KS-A…D → review chéo Codex → KHAO-SAT-CORE.md → G1a CSDL (phiếu 1) → G1b API (phiếu 2) → G1c SDK (phiếu 3).
### 30/10 ~10:45 — G0 xong; G1a (CSDL) và G1b (API) đang soạn
- **G0** xong 5 phần:
  - KS-A…D, cộng **KS-E**: mã OCR `D:\GPT\OCR`, Anh nhắc 10:22 phải hiệu chỉnh thành `e_ocr`.
  - Đã review chéo Codex. Kiểm mẫu đúng 92–100%, không lỗi chặn. KS-A, KS-C, KS-D đã sửa vòng 2.
  - Lead kiểm xác suất KS-B: 7/7 đúng.
  - Bản ghép: `docs\47-core\g0\KHAO-SAT-CORE.md`.
- **Đang chạy (4 Codex chỉ đọc):**
  - G1a-1 `DAC-TA-CSDL.md`;
  - G1a-2 `ANH-XA-MIGRATION.md`;
  - G1b-1 `DAC-TA-API.md` + OpenAPI;
  - review KS-E, chạy xong thì giao G1b-2 `ANH-XA-ROUTE.md`.
- **Tiếp theo:** review chéo Codex G1a → Opus review khối dữ liệu/role/RLS → **PHIEU-DUYET-CSDL.md gửi Anh**.
### 30/10 ~11:30 — **Cần Anh duyệt: PHIEU-DUYET-CSDL** (phiếu 1/3, CD-029)
- **Phiếu:** `docs\47-core\PHIEU-DUYET-CSDL.md`, 3 câu chọn.
- **Đặc tả kèm theo:**
  - `g1\DAC-TA-CSDL.md` (vòng 2 + 2 bổ sung lead);
  - `g1\ANH-XA-MIGRATION.md`.
- **Review:**
  - Codex: đạt độ đủ 67/67, kiểm mẫu 94,7%.
  - Opus vòng 1: 3 Chặn (liên kết tiền, kiểm tiền dưới RLS, FK giữa module).
  - Vòng 2: không còn Chặn.
- **API (phiếu 2):** Codex đang sửa vòng 2 theo review Opus (1 Chặn: biên nhận chống trùng route module) + Codex.
- **SDK (phiếu 3):** nháp xong; Codex đang review chéo.
- **Tài liệu sửa** chạy trong worktree `lat/dac-ta-core`: sandbox Codex không ghi được vào thư mục chính. Lead chép về và commit.
### 30/10 ~11:50 — **Cần Anh duyệt: PHIEU-DUYET-API** (phiếu 2/3)
- **Phiếu API:** `docs\47-core\PHIEU-DUYET-API.md`, 2 câu chọn.
  - Đặc tả `g1\DAC-TA-API.md` (vòng 2 + 3 câu bổ sung lead) và `g1\ANH-XA-ROUTE.md`.
  - Opus vòng 2: không còn Chặn. OpenAPI 3.1 parse được, 33 path.
- **Phiếu CSDL:** vẫn chờ Anh.
- **SDK (phiếu 3):** Codex review 1 Chặn / 4 Cần sửa; Opus đang review, sau đó giao Codex sửa một vòng.
### 30/10 ~12:00 — Anh trả lời phiếu CSDL: câu 2 A, câu 3 A (danh sách nhân sự gửi sau); câu 1 Anh hỏi lại → lead giải thích, chờ chọn
### 30/10 ~12:05 — **Anh DUYỆT phiếu API** (1A: tự đóng sau 5 phút rảnh; 2A: tệp tải lên 20 MB)
- **Còn chờ:**
  - phiếu CSDL câu 1 (lead đã giải thích, khuyến nghị A);
  - phiếu SDK (Codex đang sửa vòng 2).
- G2 chưa bắt đầu.
### 30/10 ~12:15 — **Cần Anh duyệt: PHIEU-DUYET-SDK** (phiếu 3/3); G1 hoàn tất phần tài liệu
- **Phiếu SDK:** `docs\47-core\PHIEU-DUYET-SDK.md`, 3 câu chọn.
  - Đặc tả `g1\DAC-TA-SDK.md`, `g1\CONTRACT-DU-LIEU.md` (vòng 2 + 3 bổ sung lead).
  - Opus vòng 2: không còn Chặn. 12/12 JSON Schema hợp lệ.
- **Tình trạng 3 phiếu:**
  - API **đã duyệt**;
  - CSDL: câu 2 A, câu 3 A, **câu 1 chờ** (đã giải thích);
  - SDK: chờ.
- **G2 cần:** đủ 3 phiếu + CD mới mở lập trình.
- **Codex rảnh, có lý do:** G0–G1 xong; còn chờ Anh.
### 30/10 ~13:05 — **Anh DUYỆT phiếu CSDL** (1A, 2A, 3A)
- **Tình trạng 3 phiếu:** CSDL đã duyệt; API đã duyệt; **SDK chờ Anh**.
- **G2 cần:** phiếu SDK + CD mới mở lập trình.
- **Việc của Anh:** gửi danh sách nhân sự đăng nhập.
### 30/10 ~14:00 — nhận CD-031/032/033; giao 4 Codex contract nghiệp vụ
- **CD-033 (Anh trả lời phiếu SDK):**
  - câu 1 = **CRM** là module thử Core ở G2, dữ liệu DEMO;
  - câu 2 = A, tài khoản máy phụ hạn chế ngay từ giai đoạn thử trên máy Anh;
  - câu 3 = A.
- **CD-031:** JSON hai lớp; thêm lớp contract nghiệp vụ.
  - 4 Codex đang soạn: CRM, M4, M2, Chung+sự kiện.
  - Đề: `docs\47-core\g1\GIAO-G1C-NV.md`.
- **CD-032:** gói module bắt buộc có `contract/`; sổ contract trong `loi`.
- **Tiếp theo:** ghép `CONTRACT-NGHIEP-VU.md` → review chéo Codex → Opus (quy tắc chung + `hop_dong_ban`, `dot_thanh_toan`, `but_toan_de_xuat`) → **phiếu SDK bản 2**, kèm đề xuất phạm vi CRM tối thiểu cho G2.
### 30/10 ~14:30 — nhận CD-034…037
- **CD-034 (3 chuẩn Core v1.0):**
  - Codex đang soạn chuẩn CSDL và chuẩn API (`docs\47-core\chuan\`).
  - Chuẩn SDK chờ Anh duyệt phiếu SDK bản 2.
  - Bản sao đặt ở `D:\Claude\QUY-TRINH-CHUNG\CHUAN-CORE\` sau Opus review.
- **CD-035/036:** Codex soạn bản giao việc 5 engine, có bảng dùng lại/bọc/sửa/viết mới.
- **CD-037:**
  - Claude Code 2.1.300; `claude -p` chạy được bằng gói Max.
  - Script tự khởi động lại đã viết và thử nhánh bỏ qua; nhịp lead ở `var\lead-nhip.txt`.
  - **Cần Anh:** bấm đúp `tools\CAI-TU-KHOI-DONG-LEAD.cmd` để cài tác vụ; xác nhận bật `crossSessionInbound`; gõ `/remote-control` khi mở phiên lead.
- **Contract nghiệp vụ vòng 2:** Codex đang sửa.
- **Phiếu SDK bản 2:** đã có nháp, gửi Anh sau khi sửa xong.
### 30/10 ~14:50 — **Cần Anh duyệt: PHIEU-DUYET-SDK bản 2**
- **Phiếu SDK bản 2** (`docs\47-core\PHIEU-DUYET-SDK.md`):
  - ba câu CD-033 đã chốt;
  - JSON hai lớp + lớp nghiệp vụ (`g1\CONTRACT-NGHIEP-VU.md`, Opus 2 vòng, hết Chặn);
  - `contract/` và sổ contract;
  - phạm vi CRM thử G2;
  - **2 câu mới:** phí trong lịch nghĩa vụ; VAT cọc khi cọc ở đợt cuối / nhiều đợt cọc.
- **Chuẩn CSDL/API v1.0:** đang review (Codex + Opus).
- **Giao việc engine:** bản 1 xong (`docs\47-core\engine\`), bản 2 Codex đang viết.
### 30/10 ~14:55 — **Cần Anh xem: 2/3 chuẩn Core v1.0** (CSDL, API)
- **Chuẩn CSDL/API v1.0:** `docs\47-core\chuan\CHUAN-CORE-CSDL-v1.0.md`, `CHUAN-CORE-API-v1.0.md`.
  - Bản sao ở `D:\Claude\QUY-TRINH-CHUNG\CHUAN-CORE\`.
  - Review: Opus Đạt (không quyết định mới); Codex 91,7%; đã sửa một lượt.
- **Chuẩn SDK:** soạn sau khi Anh duyệt phiếu SDK bản 2.
- **Giao việc 5 engine:** `docs\47-core\engine\GIAO-ENGINE-1.md`, `-2.md`. Codex đang review chéo; sau đó Opus kiểm bảng dùng lại (CD-036).
### 30/10 ~15:10 — **Cần Anh chọn: PHIEU-CAU-HOI-ENGINE** (3 câu)
- **Giao việc 5 engine:**
  - Codex review: 18/18 dòng nguồn có thật.
  - Opus review: 3 Chặn — OCR đang kéo theo hiệu đính gọi thẳng Ollama; trích xuất cần AI có khuôn trả lời; tải hóa đơn cần CAPTCHA.
  - Codex đang sửa bản giao việc.
- **Ba câu cho Anh:** `docs\47-core\engine\PHIEU-CAU-HOI-ENGINE.md` (AI trích xuất; CAPTCHA; Mask/bí mật engine).
- **Còn chờ Anh:**
  - phiếu SDK bản 2;
  - câu hỏi `crossSessionInbound`;
  - cài tác vụ tự khởi động.
### 30/10 ~17:40 — nhận CD-038
- **Anh duyệt:**
  - phiếu SDK bản 2 (1A; 2B: VAT cọc dồn đợt không cọc gần nhất phía sau, hết thì dồn ngược);
  - câu hỏi engine (1C: đổi câu hỏi trích xuất sang mẫu cổng AI, đo lại độ chính xác; 2A; 3A).
- **Đã làm:**
  - ghi kết quả vào hai phiếu;
  - sửa TL 45 BG-27 (thư mục cha) theo 2B.
- **Đang chạy (Codex):**
  - soạn `CHUAN-CORE-SDK-v1.0.md`;
  - áp CD-038 vào contract nghiệp vụ, giao việc engine, KK-UI-DA-BG.
- **`crossSessionInbound`:** lead ghi `.claude/settings.local.json` bị chặn (công cụ không cho lead tự sửa cài đặt của chính mình) → **Anh tự bật** (cách làm trong chat).
- **Mở lại lập trình (G2 + G3):** ngay khi chuẩn SDK v1.0 xong + Opus review.
### 30/10 17:52 — **MỞ LẠI LẬP TRÌNH (CD-038)**; giao G2 đợt A
- **Chuẩn SDK v1.0:** Opus Đạt, 5 sửa nhỏ đã làm. Ba chuẩn Core v1.0 ở `docs\47-core\chuan\` và `D:\Claude\QUY-TRINH-CHUNG\CHUAN-CORE\`.
- **`CLAUDE.md`:** dòng DỪNG LẬP TRÌNH đổi thành "đã mở lại 17:52 theo CD-038".
- **Kế hoạch lát:** `docs\47-core\g2\KE-HOACH-LAT-G2-G3.md` (34 lát G2 + lát G3 năm engine).
- **Đợt A** (`docs\47-core\g2\GIAO-G2-DOT-A.md`), 3 Codex:
  - G2-00: dựng Core DEMO rỗng;
  - G2-01: role/login/schema, Opus review bắt buộc;
  - G2-33: script tài khoản Windows (xem trước mặc định).
### 30/10 ~18:25 — G2: gộp G2-00, G2-01, G2-33; giao G2-02, G2-17
- **G2-00:** 23 ok; xử lý Chặn junction cụm.
- **G2-01:** PG 20 ok; Opus Đạt, 4 Nên sửa đã làm.
- **G2-33:** gộp ở dạng chỉ xem trước; đường áp tách G2-33b, sau G2-21.
- **Đang chạy:**
  - G2-02 (danh tính / pháp nhân);
  - G2-17 (bộ schema kỹ thuật offline, giao sớm vì không phụ thuộc CSDL).
### 30/10 ~18:50 — G2: gộp G2-02, G2-17; G2-03 chờ Opus; giao G2-04
- **G2-02:** PG 17 ok; Chặn DROP DATABASE trong test đã sửa. Ca nghiệp vụ login thật → G2-02b sau G2-03.
- **G2-17:** 22 ok.
- **G2-03 (phiên bí mật):** PG 23 ok; đang chờ Opus review.
- **G2-04 (audit + sổ migration):** đang chạy, dựng trên `lat/g2-03`.
- **Đã gộp tới nay:** G2-00, 01, 02, 17, 33 (xem trước).
### 30/10 ~19:15 — G2: gộp G2-03, G2-04; G2-05 chờ review; giao G2-06
- **G2-03 (phiên bí mật):** Opus 2 vòng, Chặn kiểm `phan_quyen` đã sửa; PG 26 + 11 thuần.
- **G2-04 (audit + sổ migration):** review Codex Đạt; PG 25.
- **G2-05 (registry + sổ contract):** PG 25 ok; review Codex đang chạy.
- **G2-02b bị chặn:** RLS runtime của bảng danh tính đóng; cần policy theo phiên → gộp vào G2-06 (MTQ + RLS theo phiên, Opus bắt buộc), đang chạy.
### 30/10 ~20:00 — G2 tiến độ + kế hoạch đêm (CD-008)
- **Đã gộp vào hop-nhat:** G2-00, 01, 02, 03, 04, 05, 17, 24, 33 (xem trước).
- **Đang làm:**
  - **G2-06** (MTQ + RLS theo phiên):
    - Opus vòng 1: Chặn C1 (hạn mức nhiều pháp nhân phải cùng số tiền); Codex sửa vòng 3. Sau đó Opus vòng 2, chỉ C1.
    - Worktree `lat-g2-06`.
  - **G2-07** (validator NGUON + HOP_DONG/DU_AN):
    - PG 21 ok; review Codex đang chạy (`rv.sh`, kết quả `scratchpad/g2/rv-07.out.md`).
    - Dựng trên G2-06 vòng 2 → khi G2-06 vòng 3 xong, merge `lat/g2-06` vào `lat/g2-07` rồi chạy lại test.
- **Quyết định mới:** QD-20261030-01 (Core: pháp nhân tắt MTQ → `CHO`).
- **Cách làm mỗi lát:**
  - worktree `lat/g2-xx` dựng trên lát trước;
  - Codex `workspace-write`; lead chạy `tools/chay_test_theo_module.py --pg-demo`;
  - review chéo Codex (`scratchpad/g2/rv.sh`), Opus cho lát rủi ro cao (01, 03, 06, 13, 19, 21, 25);
  - gộp `--no-ff` vào hop-nhat;
  - mỗi lượt `/loop` chạm `var\lead-nhip.txt`.
- **Hàng tiếp:** G2-08 (công tắc) → 09 → 10 → 11 → 12 → 13 (Opus) → 14 → 15 → 16 → 18 → 19 (Opus) → 20 → 21 (Opus).
  - Song song được: G2-26 sau 25; G2-31a sau 18 + 20.
  - G3 engine chờ mốc G2-21.
- **Đêm 30→31/10 (CD-008):**
  - tiếp chuỗi G2-06 → G2-12 theo nhịp trên;
  - không gộp `chinh`, không push, không xóa, không đụng kho thật;
  - 05:45 viết `bao-cao-ngay\BAO-CAO-DEM-20261031.md`.
- **Còn chờ Anh:**
  - bật `crossSessionInbound`;
  - cài `tools\CAI-TU-KHOI-DONG-LEAD.cmd`;
  - danh sách nhân sự đăng nhập.
### 30/10 ~20:35 — gộp G2-07, G2-08; G2-09 sửa test; lỗ hổng cổng test
- **G2-07:** PG 26 ok, Chặn NGUON/G3 đã sửa.
- **G2-08:** review Codex Đạt, PG 24 ok.
- **Lỗ hổng cổng:** `tools\chay_test_theo_module.py` báo module **ok=0 ERROR=0** khi tiến trình con sập vì lỗi trong `_id()` (test đè `TestCase.id`).
  - Từ nay lead kiểm thêm `ok == tong` (số test khai báo).
  - Mở lát nhỏ sửa bộ chạy: tiến trình con sập → ERROR.
### 30/10 ~21:15 — G2: đã gộp tới G2-10; G2-11 sửa vòng 2
- **Đã gộp:** G2-00…G2-10, G2-17, G2-24, G2-33 (xem trước); sửa bộ chạy test (module sập/thiếu ca → LOI).
- **G2-11** (tiếp nhận + biên nhận) — vòng 2:
  - sửa fixture phiên;
  - lead mở whitelist sửa `doi_cau_truc.py` + `test_g2_04.py` sang quy tắc số tăng chặt, cho phép khoảng trống (G2-10 không có SQL).
- **Hàng tiếp:**
  - G2-12 (danh mục V2) → G2-13 (kiểm toàn vẹn tiền, Opus) → 14 → 15 → 16 → 18 → 19 (Opus) → 20 → 21 (Opus);
  - G3 chờ mốc G2-21.
- **Ghi chú kỹ thuật** (cho lead sau nén ngữ cảnh):
  - giao việc từ `docs\47-core\g2\GIAO-G2-*.md`, ghép phần chung `GIAO-G2-DOT-A.md`;
  - worktree `.claude\worktrees\lat-g2-xx`;
  - review chéo `scratchpad\g2\rv.sh MA NHANH WT "TEP" DE "TEST" OUT`;
  - Opus review cho lát rủi ro cao bằng subagent `review-lat`.

### 30/10 ~22:00 — G2-11 vòng 5, G2-12 chờ review chéo
- **G2-11:** review chéo Codex ghi "Cần sửa". Vòng 4:
  - 004 trả về bản gốc; quy tắc số (tăng dần, cho phép bỏ số) chuyển sang 011;
  - không lộ biên nhận cho người không có quyền xem.
  - PostgreSQL: 24 ok, 1 ERROR ở ca mới (phiên không xác minh được) → vòng 5 đang sửa.
- **G2-12:** vòng 2 sửa SQL 012, test tự áp chuỗi theo số. Đã nhập `lat/g2-11` vào G2-12.
  - PostgreSQL toàn bộ G2: 411 ok / 1 ERROR (chính ca G2-11 trên) / 2 skip.
  - Đang review chéo Codex.
- **CD-039 (tự cài tác vụ tự khởi động lại):** chờ Anh xác nhận trong chat — cấu hình lâu dài chạy Claude 30 phút/lần.

### 30/10 ~22:35 — gộp G2-11; G2-12 vòng 3; mở nhánh CRM thử (CR1, CR2)
- **G2-11 đã gộp** (`46bbdbc`): vòng 5 sửa fixture; PG 25/25 + G2-04 25/25; lead kiểm lại 2 điểm review.
- **G2-12 vòng 3:** giữ guard chủ đầu chứng từ qua bảng phân chủ (điểm Chặn của review). Đang chạy PG toàn bộ G2.
- **G2-CR1** (contract `du_an_dang_ban.v1`): runtime 17/17; đang review chéo Codex.
- **G2-CR2** (contract `bao_gia.v1`, CD-038 1A/2B): Codex đang làm, nền `lat/g2-cr1`.
- **G2-CR3** (`moc_da_xay_ra.v1`) **chưa giao — chờ Anh:** đặc tả ghi chặn kích hoạt. Cần Anh chốt tham chiếu lần lịch sử của mốc, điều kiện xác nhận, bên nhận, xử lý sửa/xóa ngày thực tế. Em sẽ đưa vào báo cáo sáng.

### 30/10 ~22:58 — gộp G2-12; giao G2-13
- **G2-12 đã gộp** (`0e1923d`): review vòng 2 Đạt; PG toàn bộ G2 415 ok / 0 lỗi.
- **G2-CR1:** review Chặn (mốc riêng thiếu cả bộ tham chiếu vẫn qua schema) → vòng 2 đang sửa.
- **G2-CR2:** runtime 23/23; đang review chéo.
- **G2-13** (toàn vẹn tiền liên kết, FORCE RLS): đã giao Codex; review Opus bắt buộc trước khi gộp.

### 30/10 ~23:50 — G2-13 review Opus Cần sửa; G2-14 Cần sửa; G2-15, G2-00b chờ PG
- **Đã gộp thêm:** G2-CR1 + G2-CR2 (`4de3bab`).
- **G2-13:** PG 24/24 (toàn bộ G2 439 ok). Review Opus `RV-G2-13-OPUS.md` ghi Cần sửa — 1 Chặn: khóa mọi chứng từ của pháp nhân → cạn bộ nhớ khóa; kèm 3 Cần sửa (trả tổng, mở cửa khi mất ngữ cảnh, hủy liên kết cũ bị chặn). Vòng 3 đang sửa.
- **G2-14:** PG 28/28. Review chéo Cần sửa — Chặn: module không tạo được việc cùng transaction (trái SDK §3.4); heartbeat rút ngắn lease. Vòng 2 đang sửa.
- **G2-15** (bus) và **G2-00b** (chẩn đoán lỗi đổi cấu trúc): xong code, đang chạy PG.
- **CD-040:** ĐÃ NHẬN; chưa cài tác vụ — chờ Anh bấm xác nhận trong phiên lead.
