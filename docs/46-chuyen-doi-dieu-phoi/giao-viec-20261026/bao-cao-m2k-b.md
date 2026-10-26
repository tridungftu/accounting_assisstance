Anh, đã sửa M2k-b trong đúng 2 tệp Python được giao:

- `config()` chạy ngoài khóa chung và transaction; kiểm lại phiên/quyền trước khi ghi nhật ký và dừng bộ tải.
- Chỉ đánh dấu treo với timeout/mất kết nối; lỗi từ chối hoặc DTO sai không hiện nút.
- Giữ đủ 22 test cũ, thêm 3 test regression. Tệp UTF-8 không BOM.

Test: Python **91/91 đạt với dumper `psycopg` giả**; lệnh nguyên bản gặp 25 ERROR do thiếu driver. Node **13/13**, kiểm thêm ba trạng thái lỗi đạt **16/16**. Không ghi nhận lỗi sản phẩm mới.

Không commit. Thông điệp đề xuất: `[M2k-b] Nhả khóa chung khi kiểm bộ tải và thống nhất trạng thái treo`.