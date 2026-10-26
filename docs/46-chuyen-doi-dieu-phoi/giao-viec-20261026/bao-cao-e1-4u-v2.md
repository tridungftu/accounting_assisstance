Anh, đã sửa deadlock và toàn bộ mục nhỏ: khóa ngắn, lỗi 400/409 riêng, nhật ký chỉ trả tên hiển thị, engine thiếu hàm trả 503, bỏ quyền `ADMIN`.

- **3 file đổi:** `crm_g.py`, `khung_khai_bao.py`, `test_khung_he_thong.py`; UTF-8 không BOM, diff sạch.
- **Test:** Node **40/40**; Python **69/69** với stub chỉ phục vụ import `openpyxl`. Lệnh Python chuẩn còn vướng thiếu dependency; chưa phát hiện lỗi code mới trong phạm vi kiểm tra.
- Regression dùng `Lock`/`dich_vu_s1` thật: bản sửa qua, bản cũ bị bắt deadlock sau 5 giây; đã kiểm nhả khóa và sửa đồng thời.

**Cần Anh: vai sửa danh mục chung — hiện chỉ Kế toán trưởng.**

Không commit. Thông điệp đề xuất: `[E1-4u] vòng 2: sửa deadlock danh mục và phản hồi nghiệp vụ`.