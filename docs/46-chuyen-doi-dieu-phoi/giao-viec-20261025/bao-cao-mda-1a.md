Anh, đã hoàn thành MDA-1a trong đúng 3 tệp được giao.

- Tạo `crm_da_moc`, `crm_da_moc_ls`; hàm ghi, đọc danh sách, đọc lịch sử; kiểm trùng tên, lý do đổi ngày, CAS, idempotency, nhật ký và RLS/REVOKE.
- Append `M0035_CRM_DU_AN_MOC`; xác nhận toàn bộ migration cũ giữ nguyên.
- Test: **4/4 tĩnh đạt**, **15 PostgreSQL skip — chờ lead chạy**. UTF-8 không BOM và kiểm tra diff đạt.
- Không khởi động PostgreSQL/server, không commit.

Thông điệp commit đề xuất: `[MDA-1a] Thêm mốc thanh toán theo dự án và kiểm thử PostgreSQL`.