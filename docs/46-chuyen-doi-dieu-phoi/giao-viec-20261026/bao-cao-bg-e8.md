Anh, đã bỏ cột “VND quy đổi”; lịch còn đúng 5 cột cho VND/USD, giữ payload, Σ/tổng và bằng chữ “đồng”.
Đổi đúng `crm_g.js` và `crm_giao_ket_async.cjs`; UTF-8 không BOM, diff hợp lệ.
Test: 4/4 bộ Node đạt; không có lỗi mới trong phạm vi kiểm tra. Chưa thử trình duyệt thật.
Không commit. Thông điệp: `[BG-e8] Bỏ cột VND quy đổi trùng Giá trị, giữ bằng chữ đồng`.