Anh, đã sửa đủ 3 mục trong đúng 4 file được giao: chỉ thêm `treo` khi True; trả 409 khi đang tải và còn phản hồi, kiểm quyền hồ sơ và ghi mã bị ngắt; ẩn nút khi chưa mở.

Test: JS **13/13**; Python M2k **22/22** với import `LocalServer` được thay bằng hàm cấm mở server. Lệnh unittest đầy đủ bị chặn do thiếu `openpyxl`, nên chưa kết luận so nền HTTP. UTF-8 không BOM, diff sạch; không commit.

Thông điệp commit: `[M2k] vòng 2: sửa khóa treo, chặn khởi động lại khi đang tải`