Anh, đã sửa đúng hai file, chưa commit:

- [khung_khai_bao.py:67](</D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-ui-2b/src/kho_tri_thuc/giao_dien/khung_khai_bao.py:67>): sửa số icon; bỏ cảnh báo mẫu CFO; bỏ W5 của Người xem; báo giá chạm 200 trả `tong: null`, `day_du: false`.
- [test_khung_luoi_crm.py:108](</D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-ui-2b/tests/test_khung_luoi_crm.py:108>): bổ sung/cập nhật ca hồi quy.

| Vai | Trước: Hợp đồng / Thu tiền | Sau |
|---|---|---|
| Bán hàng | W2 / W5 | W1+W2 / ẩn số |
| Kế toán, KTT | W3 / quá hạn | W3 / W5 trong 7 ngày |
| CFO | Ẩn số / quá hạn | CHO_DUYET / quá hạn |
| Người xem | Ẩn số / ẩn số | Giữ nguyên; không truy vấn W5 |

Test bao phủ quyền tiền, cờ đỏ, số khớp danh sách và báo giá 199/200/205 dòng. Module có **20 ca**, chưa chạy vì sandbox không có Python — **lead chạy test**; lỗi mới chưa xác minh. `git diff --check` đạt; hai file UTF-8 không BOM.

Thông điệp commit: `[UI-2b] Sửa số việc trên icon CRM và tổng báo giá bị cắt`