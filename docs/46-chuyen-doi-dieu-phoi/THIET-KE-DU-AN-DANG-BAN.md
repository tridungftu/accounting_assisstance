# CRM · Danh mục dự án đang bán — checklist thiết kế (lead soạn 25/10/2026, **Anh đã chốt 25/10**)

## Yêu cầu của Anh (25/10)
Thêm danh mục **dự án đang bán**, thêm được dự án mới. Mỗi dự án có **thông tin chung**, **tiến độ thanh toán tiêu chuẩn**, **các loại phí bảo trì, phí sử dụng tiêu chuẩn**. Ở **Báo giá**, chọn dự án → **mặc định nạp các thông số đó**.

## Dùng lại (đã có trong phần mềm)
| Phần | Có sẵn | Dùng thế nào |
|---|---|---|
| Danh mục dự án | `master.du_an` (pháp nhân, mã Junsky, tên, giai đoạn, trạng thái) — danh mục chung của kế toán | Dự án đang bán **gắn vào** dự án này, không tạo danh mục dự án thứ hai |
| Tiến độ thanh toán tiêu chuẩn | Bộ chuẩn G7 (`master.crm_bo_chuan` + phiên bản + dòng), có phiên bản và CFO duyệt | Giữ nguyên làm "tiến độ tiêu chuẩn" của dự án |
| Loại hình | `master.loai_hinh_doanh_thu.cau_hinh` (KCN / nhà ở…) | Loại hình mặc định của dự án |
| Phí trong báo giá | trường `phi_bao_tri` (một khoản) | Mở rộng thành **danh sách phí** nạp từ dự án |

## Mới (dự kiến)
- Bảng thông tin bán hàng của dự án: cờ **đang bán**, thông tin chung (vị trí, mô tả, loại hình mặc định, tiền tệ mặc định…), **danh sách phí tiêu chuẩn** (tên phí, mức, đơn vị tính — m²/tháng, m²/năm, lần —, tiền tệ, cơ sở tính), có **phiên bản** và nhật ký (báo giá cũ giữ đúng phiên bản đã dùng).
- Màn **Danh mục dự án đang bán** trong CRM: danh sách, thêm, sửa, xem lịch sử.
- Báo giá: chọn dự án → nạp thông tin chung + tiến độ tiêu chuẩn + phí tiêu chuẩn; ghi phiên bản đã nạp vào báo giá.
- Migration mới (append sau số hiện có).

## Checklist cổng B (dự kiến)
1. Thêm một dự án đang bán từ danh mục dự án hiện có; khai đủ thông tin chung.
2. Khai tiến độ thanh toán tiêu chuẩn (bộ chuẩn) cho dự án; trạng thái duyệt hiện đúng.
3. Khai ≥ 2 loại phí (bảo trì, sử dụng) với đơn vị tính khác nhau.
4. Sửa phí → có phiên bản mới, xem được lịch sử; báo giá đã lưu không đổi.
5. Báo giá: chọn dự án → loại hình, tiền tệ, lịch, phí tự nạp; không gõ tay.
6. Dự án ngừng bán không còn trong danh sách chọn của báo giá mới.
7. Người không có quyền không thêm/sửa được danh mục.
8. Màn hình tiếng Việt, không mã kỹ thuật, tiền có đơn vị, ngày dd/mm/yyyy.

## Anh đã chốt (25/10, bảng chọn — QD-20261025-05…09)
1. Dự án đang bán **chọn từ danh mục dự án kế toán** (`master.du_an`); dự án mới hoàn toàn do kế toán thêm vào danh mục chung trước.
2. **Bán hàng tự sửa** — hiệu lực ngay, có phiên bản + nhật ký; **kể cả tiến độ thanh toán tiêu chuẩn (bỏ bước CFO duyệt bộ chuẩn G7)**.
3. Thông số lưu sẵn: **đơn giá niêm yết + tiền tệ**, **loại hình + thuế mặc định**, **danh mục lô/căn** (diện tích, trạng thái), tiến độ, các loại phí.
4. Báo giá **được sửa riêng**, báo "khác tiêu chuẩn" + nhật ký.

## Lát dự kiến
| Lát | Việc | Worker | Phụ thuộc |
|---|---|---|---|
| DA-1 | Máy chủ + CSDL (migration sau BG-1c): bảng thông tin bán hàng của dự án (cờ đang bán, thông tin chung, đơn giá niêm yết + tiền tệ, loại hình + thuế mặc định) có phiên bản; danh sách phí tiêu chuẩn; danh mục lô/căn; bộ chuẩn G7 cho bán hàng áp dụng ngay (bỏ bước CFO); quyền bán hàng; nhật ký; route | Claude Opus | BG-1c gộp (khóa `pg_migrations.py`) |
| DA-2 | Màn **Dự án đang bán** (danh sách, thêm từ danh mục dự án, sửa thông tin/đơn giá/loại hình/thuế/phí/lô căn/tiến độ, lịch sử) | Claude | DA-1 |
| DA-3 | Báo giá: chọn dự án → nạp mặc định (bước 1: đơn giá, tiền tệ, loại hình, thuế, lô → diện tích, tiến độ; bước 2: phí); sửa riêng → "khác tiêu chuẩn" + nhật ký | Claude | DA-1, BG-1d |
