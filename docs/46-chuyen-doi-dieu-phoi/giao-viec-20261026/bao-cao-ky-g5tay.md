Anh, đã hoàn thành KY-G5TAY trong 5 file được giao.

- **M0037:** thêm bảng bất biến `crm_g5_kiem_tay` và hàm `crm_g5_xac_nhan_tay`; kiểm quyền/phạm vi, tách nhiệm, lý do 10–1000 ký tự, replay và nhật ký ai/lúc/lý do.
- **G5/G6:** xác nhận tay hợp lệ cho qua G5; vẫn cần kế toán duyệt G6 để sang Hiệu lực. Giữ nguyên E5 và migration cũ.
- **Route:** `POST /api/crm/giao-ket/doi-chieu/xac-nhan-tay`, thân `{ky_id, ly_do, khoa}`; lỗi theo trường, trạng thái đổi trả 409.
- **Test:** 137 đạt/162, 25 skip; không có lỗi trong nhóm đã chạy. Bộ mới: 8 đạt, 7 PG/HTTP chờ lead chạy. Đã kiểm UTF-8 không BOM và `diff --check`.

Không làm giao diện, không mở server/PostgreSQL, không commit.

Thông điệp commit đề xuất: `[KY-G5TAY] Thêm xác nhận kiểm tay G5 cho bản sinh chỉ DOCX`