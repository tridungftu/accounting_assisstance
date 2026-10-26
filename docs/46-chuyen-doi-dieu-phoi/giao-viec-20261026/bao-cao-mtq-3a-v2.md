Đã sửa đủ 4 điểm, đúng hai tệp được giao; UTF-8 không BOM.
`node tests/mtq_bang_tick.cjs`: **30/30 đạt**, không thêm lỗi trong bộ test này; `git diff --check` đạt.
Đã thử số JSON lớn, phục hồi nút sau tải lại, lỗi 409/503 và câu “chưa dùng ma trận”.
Chưa kiểm thử trình duyệt thật; không commit, không mở server.
Thông điệp commit đề xuất: `[MTQ-3a] vòng 2: xử lý hạn mức lớn, phục hồi màn và sửa thông báo lỗi`.