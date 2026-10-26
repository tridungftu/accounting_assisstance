**Trả lời lead (Claude) cho XS-4c2 — làm theo, không hỏi lại (26/10 ~23:12):**

1. **Pháp nhân cho `GET trang-thai`:** phiên không giữ PN. Không thêm PN vào phiên ở lát này.
   - `GET /api/cong-tac-module/trang-thai?module=<mã>` trả **danh sách** `[{phap_nhan_id, ten_phap_nhan, ...cờ}]` cho **mọi pháp nhân mà người dùng phiên được phép**.
   - Lấy tập PN bằng **đúng nguồn khung khai báo đang dùng** (`giao_dien/khung_khai_bao.py` ~dòng 108 — PN từ phiên/ktt; đọc mã để dùng lại cùng hàm/truy vấn). Không tự viết truy vấn PN mới nếu đã có.
   - Client không gửi PN. Có `phap_nhan_id` trong query → 400.
2. **Phạm vi Admin:** Admin ma trận thẩm quyền là **Admin toàn hệ thống** (`master.mtq_la_admin()`, M0039). Theo S2 "chỉ Admin" (Anh chốt), Admin đổi công tắc và quản người thử **ở mọi pháp nhân**.
   - POST nhận `phap_nhan_id` mục tiêu; SQL M0056 đã kiểm Admin và FK pháp nhân.
   - Không thêm khái niệm Admin theo pháp nhân. Ghi một dòng docstring.
3. Còn lại làm đúng đề `giao-xs-4c2.md`. Không thêm thư viện, không sửa JS.
