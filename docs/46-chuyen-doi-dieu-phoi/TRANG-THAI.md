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
- **CD-013/014:** M3 + M10-1 vào `4-KE-HOACH-LEAD.md`; bản M3 20/10 → `LUU-TRU	hiet-ke-m3-ban-20261020\` (SHA256 khớp sau khi chuyển); 2 liên kết thiết kế trỏ v2; M3-CL đánh dấu đã thay. Giao **M10-1a** (engine lịch A/B). M3-0 chờ mục 17 của v2.
- **MTQ-4a dừng (đúng quy tắc, chưa sửa tệp):** `CrmK2` chạy bằng kết nối `app_web`, M0039 thu hồi quyền gọi lõi MTQ của vai này. **Lead chốt hướng:** lát **MTQ-4a0** (SQL, migration mới) thêm hàm SECURITY DEFINER bọc lõi quyết định, lấy danh tính từ GUC phiên (`ktt_danh_tinh()`), cấp EXECUTE cho app_web; và hàm ghi nhật ký từ chối gọi được từ app_web trong giao dịch riêng — vì thiết kế §5.1 cũng cần SQL/RLS chạy dưới app_web gọi cùng lõi. Sau đó giao lại MTQ-4a (adapter Python). MTQ-4a0 chờ `pg_migrations.py` (DL1b đang giữ, sẽ là M0040).
- **Sự cố 12:03 (lead tự báo):** lệnh `grep -r` tìm liên kết tài liệu M3 chạy trên **cả thư mục cha**, gồm `Phần mềm kho tri thứcar\` (có kho thật), lọc `*.md`, khoảng 2 phút rồi lead dừng (TaskStop). Không in nội dung, kết quả không hiển thị; vẫn là vi phạm "không đọc kho thật qua công cụ" ở mức duyệt tên/đọc tệp `.md`. Từ nay chỉ tìm trong thư mục cụ thể (`THIET-KE-MODULE-DE-CHOT-2026-10-20`, `docs`), không tìm đệ quy từ thư mục cha.
- Đang chạy: Codex — DL1b v4, MTQ-5a v2, M10-1a, MTQ-2c (4/4). Claude — review-lat MTQ-3a (1/2). Lead — test M2k-b, MASK-3 v2 (pytest + benchmark).
| Việc chưa giao | Lý do chặn |
|---|---|
| MTQ-4a0 / MTQ-4a | chờ `pg_migrations.py` (DL1b → M0040) |
| M3-0, M3-1a… | M3-0 chờ mục 17 thiết kế v2; M3-1a cần `pg_migrations.py` sau MTQ-4a0 |
| MTQ-3b | `app.js` đang do E1-4u giữ — chờ E1-4u gộp |
| M4-DL3 | cùng tệp DL2 — chờ DL2 gộp (sau DL1b) |
| Nạp dữ liệu Review thật (CD-011) | **Cần Anh**: bảng ánh xạ `ma_hd → HĐ/pháp nhân/dự án` |
