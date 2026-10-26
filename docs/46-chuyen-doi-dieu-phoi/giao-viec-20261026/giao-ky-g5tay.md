# KY-G5TAY — G5: "Kế toán xác nhận đã kiểm tay" cho bản ký gắn bản sinh chỉ có DOCX (CD-010 mục 1)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại** (điểm chưa rõ → chọn cách đơn giản, an toàn, ghi "Cần Anh" trong báo cáo). Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM — ghi tệp bằng UTF-8 (chữ Việt không thành `?`). Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL (test PG tự skip — lead chạy). Không xóa file. Không đọc kho thật/tệp bí mật (CLAUDE.md §2).

Worktree hiện tại, nhánh `lat/ky-g5tay` (hợp nhất 3dd1661, đã có KY-DOCX **M0036** — đọc khối M0036 cuối `src/kho_tri_thuc/ha_tang/pg_migrations.py`, `k2/crm_ky_ket.py`, G5 `k2/sql_crm_doi_chieu.py` (M0032), `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\review-ky-docx.md`).

**Anh chốt (hộp thư CD-010 mục 1):** bản ký gắn bản sinh chỉ có DOCX → G5 luôn HOLD (`G5_BAN_SINH_CHI_DOCX`) → hợp đồng không sang Hiệu lực. Thêm đường **"Kế toán xác nhận đã kiểm tay"** cho bước đối chiếu bản ký G5: **bắt buộc lý do**, ghi **nhật ký** (ai, lúc nào), sau đó hợp đồng **sang được Hiệu lực** qua cổng kế toán kiểm (G6) như khi G5 khớp. **Không** nới hợp đồng dữ liệu E5 nhận hash DOCX. PDF lỗi vẫn được Chờ ký (đã có).

**Việc:**
1. Migration **M0037** (append sau M0036, không đổi migration cũ): lệnh SQL `master.crm_g5_xac_nhan_tay(p_khoa, p_h, p_ky uuid, p_ly_do text)` theo đúng mẫu lệnh G5 hiện có (preflight quyền + biên nhận idempotent, khóa dòng, kết nối chủ bảng): chỉ vai **kế toán / kế toán trưởng** có module CRM trên đúng pháp nhân; chỉ khi bản ký đang HOLD vì `G5_BAN_SINH_CHI_DOCX` (đúng revision hiện hành, chưa có kết quả G5 khác); lý do 10–1000 ký tự bắt buộc; ghi một **kết quả G5 loại kiểm tay** (bảng kết quả G5 hiện có, hoặc bảng nhỏ mới nếu ràng buộc NOT NULL hash PDF không cho — chọn cách **không nới E5**) + sự kiện `nhat_ky.su_kien`; `crm_kiem_g5_xet` coi kết quả kiểm tay hợp lệ là **qua G5** (không còn HOLD) để G6 cho kế toán duyệt Hiệu lực. Người xác nhận tay không được là người ghi bản ký (tách nhiệm), nếu dữ liệu có người ghi.
2. Dịch vụ + HTTP: `k2/crm_ky_ket.py` (hoặc tệp dịch vụ G5 đang có) hàm gọi lệnh; route POST trong `giao_dien/crm_g.py` (cùng chỗ các route G5/kiểm), thân `{ky_id, ly_do, khoa}`, lỗi theo trường, 409 khi trạng thái đổi.
3. Test: PG (`skipUnless KHO_PG_DSN_TEST`, mẫu `tests/test_crm_ky_ket_http.py` k09/k10): bản chỉ DOCX → HOLD → kế toán xác nhận tay (có lý do) → G5 qua → G6 kế toán duyệt sang Hiệu lực; thiếu lý do → lỗi; vai bán hàng → từ chối; bản có PDF (G5 tự động) → lệnh từ chối; gọi lặp cùng khóa → cùng kết quả; nhật ký đủ ai/lúc/lý do. Thuần: SQL có đủ hàm/REVOKE, M0037 là phần tử cuối.

**Không làm** giao diện (lát sau, trên dòng giao diện).
**File:** `ha_tang/pg_migrations.py` (+ tệp SQL mới `k2/sql_crm_g5_tay.py` nếu tách), dịch vụ, `crm_g.py`, 1 tệp test mới.
**Báo cáo (≤ ½ trang):** bảng/hàm, cách qua G5/G6, route, số test, thông điệp commit `[KY-G5TAY] …`.
