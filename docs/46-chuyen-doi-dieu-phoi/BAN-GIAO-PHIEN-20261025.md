# Bàn giao phiên lead 25/10/2026 (Anh mở lại phiên để nạp cài đặt quyền thư mục mới)

Phiên mới: đọc `CLAUDE.md`, `CHI-DAO-TU-ANH.md`, `TRANG-THAI.md`, rồi tệp này. Tệp giao việc/review của phiên cũ đã chép vào `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\` (gồm `lead_so_nen.py` — so `ids_loi` với nền: `python lead_so_nen.py <kq.json> <nen.json>`).

## Nhánh tích hợp `hop-nhat-20261023` — đã gộp hôm nay
BG-1c, M4-6, L0-9, E1-4a, E1-4b, M2h, M2h-c, M2j, M2s, L0-8 + L0-8c, DA-1 (M0031), C1a (M0032 G5) + T-MIG, C3, AI-0b. Chuỗi migration: **32**.

## Lát dở bị dừng khi mở lại phiên (worker đang chạy thì mất)
| Lát | Tình trạng lúc dừng | Việc phiên mới làm |
|---|---|---|
| AI-1 (Codex) | **XONG trước khi mở lại phiên** — `lat-ai-1` 3 tệp chưa commit; báo cáo `giao-viec-20261025ao-cao-ai-1.md` (40/40 test, mock/loopback) | Cổng kiểm soát (diff, mã hóa, tự chạy test) → commit → gộp |
| C3c (Codex) | **XONG** — `lat-c3c` 3 tệp chưa commit; Codex **chưa chạy được test** (sandbox chặn python) | Lead chạy test (có PG) → commit → gộp |
| M2s-b (Codex) | **XONG** — `lat-m2s-b` 2 tệp chưa commit (nhãn "Kế toán M2 (mô phỏng)", 7/7 node) | Kiểm → commit → gộp |
| MASK-1 (Claude) | Mask v2: **0 tệp đã đổi** so với bản sao lưu `LUU-TRU\mask1-sao-luu-mask-v2-20261025-183855` | Giao lại `giao-mask-1.md` (Anh đã cấp quyền D:/GPT) |
| Review M4-5a + DA-3a (Claude) | **XONG — Đạt cả hai, không Chặn**; kết quả `giao-viec-20261025ao-cao-review-m45a-da3a.md` | Giao Codex sửa A1, A2, B1; chạy PG (M4-5a c11–c18, DA-3a `KTT_DA3A_KET_NOI`) → gộp |

## Lát xong nhưng chưa gộp
- **AI-0a** (engine #6 độc lập `D:\Claude\Ho tro review ho so xay dung\review_xaydung`, ngoài git): 4 tệp sửa + `tests/test_cloud_tam_khoa.py` (18 ca OK, không gọi mạng); `test_common_api` 25/25; `test_trich_xuat` 9 ca kiểm hành vi Cloud cũ nay thất bại đúng thiết kế (`TestNguonClaude` 3, `TestCloud` 6) → đánh dấu bỏ qua/viết lại ở AI-3. Sao lưu gốc: `LUU-TRU\ai-0a-sao-luu-review_xaydung-20261025-175621`.
- **M4-5a** (M0033, `lat/m4-5a` 7e9025c): test M4 0 mã lỗi mới; M0033 áp sạch CSDL p8797; chờ review Claude → gộp.
- **DA-3a** (`lat/da-3a` c077a83): 0 mã lỗi mới; chờ review Claude → gộp.
- **T-MIG2** (`lat/t-mig2` 26e9c35): còn 1 mã lỗi mới `test_crm_k2.test_t21_buoc_chuan_bi_nut_mo_demo`; họ bản sao G6A vẫn `ho=-` → lead xem nhật ký dựng bản sao trước khi giao vòng 3.
- **Chuỗi Báo giá** `lat/bg-1d` (chờ Anh cổng A, phiếu `PHIEU-CONG-A-BAO-GIA-XEM-LAI.md`, DEMO 8791) → `lat/da-2` (DA-2a/b/c xong) → UI-1 dựng trên đó.

## Sẵn sàng giao (đã soạn trong `giao-viec-20261025\`)
UI-1 (Claude), UI-2 (Codex) theo `HOP-DONG-DU-LIEU-KHUNG-LUOI.md` (CD-002); AI-1 lại (nếu dở); MASK-1 lại.

## Máy chủ DEMO đang chạy (dừng đúng pid trong `/api/health` khi không cần)
8791 (Báo giá — **giữ cho Anh kiểm cổng A**), 8793, 8795, 8796, 8797 (CSDL riêng thử DA-1/C1a/M4-5a — có thể dừng).

## Nhắc
- Tối đa 3 worker lập trình cùng lúc (phiên cũ lỡ để 5).
- Codex không chạy được trong `review_xaydung` (lỗi sandbox) → việc ở đó giao worker Claude.
- PostgreSQL DEMO vẫn chạy tay (pid do lead khởi động 25/10 14:29); Anh chưa bấm `DỌN CSDL TEST CŨ.cmd` / `CÀI DỊCH VỤ POSTGRES DEMO.cmd`.
