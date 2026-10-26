Đã sửa riêng `tests/test_crm_g5_tay.py`: dùng login DEMO đúng vai, tạo phiên riêng và xác thực danh tính qua HTTP.
Giữ kiểm tra 403/404 và thu hồi quyền trước replay; không đổi mã sản phẩm.
Kiểm tra UTF-8 không BOM và `git diff --check`: đạt.
Unittest: NOT_RUN — Python bị sandbox từ chối (`Access is denied`); chưa xác minh lỗi mới.
Không commit. Thông điệp đề xuất: `[KY-G5TAY] vòng 4: sửa login DEMO và phiên test p03`.