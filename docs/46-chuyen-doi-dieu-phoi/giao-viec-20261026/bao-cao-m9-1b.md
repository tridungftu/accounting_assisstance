Anh, đã sửa đủ 3 điểm trong đúng hai tệp:

- `src/kho_tri_thuc/m9/tai_lieu_vay.py`: chống đếm đôi trang, đổi câu lỗi trung tính, nhận tiêu đề Điều/Chương theo điều kiện chữ hoa.
- `tests/test_m9_tai_lieu_vay.py`: thêm 7 test, giữ nguyên 14 test cũ.

Đã kiểm tra: `git diff --check` đạt; cả hai tệp UTF-8 không BOM.

**Test: chưa chạy được 21 ca** vì Python bị từ chối thực thi (`Access is denied`). Chưa xác định lỗi mới so với nền.

Không commit. Thông điệp đề xuất: `[M9-1b] Sửa đếm trang DOCX, thông báo lỗi và nhận diện Điều/Chương`