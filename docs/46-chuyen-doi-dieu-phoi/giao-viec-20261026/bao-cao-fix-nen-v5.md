[FIX-NEN-V5] Đã sửa đúng 3 tệp test được giao, UTF-8 không BOM.
CRM: bổ sung `_tx` và nhánh `kiem_cu`; DL5b: cô lập DL5a; OCR: đồng bộ Event/Queue, nới timeout.
Chạy thuần: 76/79 đạt, 1 skip, 1 fail nền `LENH_RIENG`, 1 error cleanup `WinError 145`; 4,4 giây.
`WinError 145` cũng tái hiện với test nguyên bản HEAD; không còn lỗi `_tx`, `id` hoặc timeout OCR.
`git diff --check` đạt. Chưa xác minh PG cả bộ.
Không sửa mã nguồn, không commit, không mở server/PostgreSQL DEMO.