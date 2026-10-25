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
