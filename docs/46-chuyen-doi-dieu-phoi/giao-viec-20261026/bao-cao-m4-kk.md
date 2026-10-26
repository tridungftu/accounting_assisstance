Anh, đã ghi [M4-KIEM-KE-CHEP-REVIEW.md](docs/46-chuyen-doi-dieu-phoi/M4-KIEM-KE-CHEP-REVIEW.md).

- Kiểm **8 màn, 68 mẫu API, 12 bảng SQLite**.
- API: **8 đã có · 23 khác · 37 thiếu**. Dữ liệu: **2 bảng nghiệp vụ thiếu**, 10 bảng ánh xạ khác/một phần.
- Lát đầu đề xuất: **M4-DL1**, bổ sung schema PostgreSQL, registry migration và test — 3 tệp.
- Kiểm tĩnh: 182 tham chiếu hợp lệ, 24 PIN khớp; UTF-8 không BOM. Không chạy test ứng dụng, không đọc dữ liệu thật, chỉ ghi một tài liệu, không commit.

Thông điệp commit đề xuất: `[M4-KK] Kiểm kê 8 màn Review và ánh xạ SQLite sang PostgreSQL M4`