Anh, đã hoàn tất phần code trong đúng 3 tệp được giao, chưa commit.

- Nạp đủ PL/tham số đổi/BOQ từ snapshot hiện hành sau kiểm quyền `conn_phien`; giữ hành vi cũ khi không có snapshot.
- Trùng nguồn → `FAILED`, ghi “Cần xem lại”, không chạy tính.
- Đã thử NULL/0, lịch sử hủy, projection chỉ đọc và parity BOQ/tham số tại hai ngày: **8/8 test mới đạt**.
- Vendor PIN **24/24 khớp**; UTF-8 không BOM; `git diff --check` đạt.

| Test | Trước: đạt/lỗi/skip | Sau: đạt/lỗi/skip |
|---|---:|---:|
| Compute | 47/2/2 | 55/2/5 |
| Toàn bộ M4 review | 103/2/76 | 111/2/79 |

Không thêm lỗi so với lần chạy trước. Hai lỗi cũ do thiếu `openpyxl`.

**Cần lead:** chạy parity P/B đầy đủ và PG trong runtime có `openpyxl`, `KHO_PG_DSN_TEST`; chưa đủ căn cứ chốt nghiệm thu parity.

Thông điệp commit đề xuất: `[M4-DL5a] Nối phụ lục và BOQ Review vào snapshot tính toán có kiểm quyền`.