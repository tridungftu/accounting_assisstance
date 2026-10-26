Đã sửa DL3 dùng chung kiểm quyền DL2, đủ 3 trạng thái NULL; kiểm UUID trước SQL, đổi mã lỗi và gộp SELECT.
Tệp đổi: đúng 2 repository và 2 test được giao; UTF-8 không BOM.
Test: 32/32 đạt, 24 PostgreSQL test bỏ qua; không thêm lỗi trong bộ chạy, `git diff --check` đạt.
Không mở PostgreSQL, không đọc dữ liệu Review thật; khe hở kiểm quyền–đọc đã ghi rõ trong docstring.
Không commit. Thông điệp đề xuất: `[M4-DL3] vòng 2: dùng chung kiểm quyền, phân biệt ba trạng thái NULL và sửa lớp đọc DL2`.