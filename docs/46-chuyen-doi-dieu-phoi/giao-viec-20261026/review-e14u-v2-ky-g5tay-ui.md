# Review 26/10 ~11:20: E1-4u vòng 2 và KY-G5TAY-UI (review-lat, Opus)

## E1-4u vòng 2 (`lat/e1-4u` 4bfe9be): ĐẠT, không còn điểm Chặn
- Lỗi treo khóa đã hết: `mutation_lock` chỉ bọc `crm_phien`; `_quyen_danh_muc` và `_ten_nguoi_nhat_ky` chạy ngoài khóa; `_KHOA_DANH_MUC` là khóa lá, không lồng nên không thể đảo thứ tự khóa.
- Reviewer chạy ca hồi quy trên bản cũ 456dca1: treo, FAIL sau 5,07 giây. Bản mới qua.
- So phiên bản, đọc và ghi tệp nằm trong cùng một khóa. Kiểm quyền (chỉ Kế toán trưởng) làm trước khi ghi. DTO nhật ký không trả tên đăng nhập.
- **Nên sửa:**
  1. Lỗi toàn vẹn tệp dùng mã riêng `CRM_G_TEP_HONG`, câu "Báo quản trị…".
  2. Mô tả bị xóa trống → câu "Mô tả tham số không được để trống."
  3. Thu hẹp `except ValueError` hoặc ghi log mã lỗi.
  4. Bọc `_nap_danh_muc` lần đầu trong khóa.
  5. Ca 403 khẳng định tệp và nhật ký không đổi.
- **Cần Anh:** vai được sửa danh mục dùng chung (hiện chỉ Kế toán trưởng của mọi pháp nhân).
- **Cổng lead (điểm reviewer không thấy):** `app.js:2152` gọi `$("page-hoso").after(...)` ngay khi nạp, nên DOM giả của 17 bộ test node lỗi `TypeError`. Trên `lat/ui-ky` các bộ này đạt. Sửa ở vòng 3.

## KY-G5TAY-UI (`lat/ky-g5tay-ui` d105422): ĐẠT, không có điểm Chặn
- Thân yêu cầu `{ky_id, ly_do, khoa}` khớp route. Khối chỉ hiện khi máy chủ trả HOLD với đúng mã `G5_BAN_SINH_CHI_DOCX` và `quyen.kiem`.
- Lý do 10–1000 ký tự, chặn ký tự điều khiển như máy chủ. Không dùng `innerHTML`; bấm đúp chỉ gửi một lần.
- Node 3 bộ đạt.
- **Nên sửa:**
  1. Bỏ câu xưng "Anh" ở `crm_g.js:3114`.
  2. Phân lỗi 400 theo mã `CRM_G5_TAY_LY_DO`. Lỗi khác và 404 dùng câu chung; hiện 404 đang lộ "CSDL từ chối thao tác (CRM_G_KHONG_THAY)". **Lead xếp điểm này là phải sửa trước khi gộp** (giao diện không được hiện mã kỹ thuật).
  3. Ẩn khối ngay khi có biên nhận hợp lệ.
  4. Bỏ đọc trường đoán `xac_nhan_boi_ten`.
- **Test còn thiếu:** biên nhận đúng hình dạng máy chủ (giờ PG `+07:00`, có micro giây); ca 400/404; lý do có chuỗi giống HTML.
