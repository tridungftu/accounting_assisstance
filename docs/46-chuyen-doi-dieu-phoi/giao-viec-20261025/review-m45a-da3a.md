# REVIEW M4-5a (M0033) và DA-3a · vòng 1/2 · reviewer Claude (chỉ đọc)

Bạn là reviewer chéo cho code Codex viết. **Chỉ đọc**: không sửa tệp, không commit, không nối CSDL. Làm lần lượt hai lát, mỗi lát một bảng.

## A. M4-5a — M4 · Nghiệm thu & chi phí dự án · 03B máy chủ (M0033)
Worktree `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\.claude\worktrees\lat-m4-5a`, nhánh `lat/m4-5a` (2 commit trên `lat/c1a`: `8677e2c` vòng 1, `7e9025c` vòng 2). Diff: `git -C <worktree> diff lat/c1a...lat/m4-5a`. Căn cứ: `docs/46-chuyen-doi-dieu-phoi/CHECKLIST-M4-03B.md` (Anh duyệt: một phần **khai bằng số tiền**; nhiều–nhiều trong một đối chiếu; **hóa đơn đã gắn ở đối chiếu khác → từ chối, báo "đã gắn ở …"**; gợi ý xếp hạng, máy **không tự ghép, không điểm khớp**; không ghi công nợ). Lead đã chạy: test M4 không PG 0 mã lỗi mới; PostgreSQL 03B chưa có họ bản sao.
Kiểm (Đạt/Không): (1) M0033 chỉ append, M0001–M0032 trùng byte, `sql_ghi_nhan_chung.py` (M0029) nguyên byte; `CREATE OR REPLACE` giữ chữ ký/kiểu trả. (2) Tiền: `so_tien_khai` parse chặt (ASCII, Decimal, VND nguyên, USD ≤ 2 số lẻ, > 0, < 10^18) khớp Python ↔ SQL; bản cũ có `ty_le_khai` đọc đúng nghĩa; bản mới từ chối `ty_le_khai`. (3) Chống gắn trùng: khóa advisory theo hóa đơn đủ chặn hai giao dịch song song; chỉ xét phiên bản mới nhất còn hiệu lực; phiên bản mới của cùng gốc không tự chặn mình; thông báo "đã gắn ở …" không lộ dữ liệu ngoài quyền. (4) `goi_y_hoa_don`: lọc pháp nhân + đối tác trước khi đọc, xếp theo tín hiệu, không trả điểm, thiếu quyền M2 → rỗng + `khong_quyen`. (5) Test có nghĩa (gồm ca PG viết sẵn).

## B. DA-3a — CRM · Báo giá máy chủ: chọn dự án → mặc định + "khác tiêu chuẩn"
Worktree `...\.claude\worktrees\lat-da-3a`, nhánh `lat/da-3a`, commit `c077a83` (`git show c077a83`). Căn cứ: `docs/QUYET-DINH.md` QD-20261025-05…09, 20; giao việc: route `GET /api/crm/bao-gia/mac-dinh`, lưu `nguon_tieu_chuan` **lấy lại ảnh chụp tại máy chủ (không tin số máy khách)**, `khac_tieu_chuan` + nhật ký **cùng giao dịch**, không chặn lưu; `lo_id` thuộc dự án và đang "Còn trống"; **chưa** đổi cách tính thuế/tổng tiền. Lead đã chạy: 403 đạt, 0 mã lỗi mới; PostgreSQL phần dự án đang bán 16/16.
Kiểm (Đạt/Không): (1) không đổi số tiền/tổng/lịch so với trước (chỉ thêm siêu dữ liệu); bước Ký (M0030) không bị ảnh hưởng. (2) Quyền đọc route mặc định như đọc báo giá; dự án ngừng bán bị từ chối. (3) `nguon_tieu_chuan`/`khac_tieu_chuan` tính tại máy chủ, idempotent (lặp lại cùng `khoa` không ghi nhật ký thêm). (4) `lo_id` sai dự án / không trống bị từ chối; diện tích lấy từ lô. (5) Cập nhật ghim SHA ở `tests/test_crm_ky_ket.py` hợp lý.

**Báo cáo cuối (≤ 1 trang, tiếng Việt):** hai bảng
```
REVIEW M4-5a · vòng 1/2 · Claude   |   REVIEW DA-3a · vòng 1/2 · Claude
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi sai tiền/miền tiền, gắn trùng lọt được, lộ dữ liệu ngoài quyền, đổi số tiền báo giá, hoặc M0033 phá migration cũ. Lệnh > 1 phút dùng `run_in_background`.
