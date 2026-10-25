Anh, đã hoàn tất đúng 3 file, chưa commit.

- **M0034:** thêm **11 cột** theo ánh xạ AI-2a: `ma_yeu_cau`, `duong`, `da_gui`, `so_ky_tu_gui/nhan`, `ma_luot_mask`, `ly_do_chuyen_cloud`, `ly_do_khong_gui`, `ket_qua`, `ly_do`, `so_truong_bi_loai`. Hai cột cũ buộc NULL cho dòng mới; M0001–M0033 giữ nguyên byte.
- **Quyền:** SELECT/INSERT cho vai kế toán và AI; thu hồi UPDATE/DELETE/TRUNCATE khỏi vai ứng dụng, giữ trigger bất biến.
- **Bộ ghi:** INSERT tham số hóa, giao dịch riêng; lỗi chỉ log tên loại lỗi, không làm mất kết quả AI.
- **Test:** 58 đạt, 20 skip, 0 lỗi trong phạm vi chạy. Có 5 ca PG mới chờ lead chạy; không nối CSDL. Test cũ ghim phiên bản 13/24 được giữ nguyên.
- **Commit đề xuất:** `[AI-2b] Thêm M0034 và bộ ghi nhật ký cổng AI PostgreSQL`