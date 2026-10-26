- **(a) Đạt qua review tĩnh:** `ha_tang/pg_migrations.py:12430` lấy writer cuối bằng `_m37_ham`; bốn phép thay giữ nguyên phần M0055 ngoài nhánh mới, gồm guard, replay, biên nhận, nhật ký và trạng thái.
- **(b) Đạt qua review tĩnh:** `m4/sql_boq_bo.py:142` phân biệt có/không gửi thao tác; dòng 146 chặn lẫn lộn, dòng 153–155 giới hạn GOC; dòng 216 giữ nhánh suy luận cũ.
- **(c) Không — Chặn:** `m4/sql_boq_bo.py:207` tự gán `dong` theo vị trí mảng nhưng không tránh số dòng đã gửi. Vi phạm **giao việc §2, dòng 21: BO chỉ cần `ma_hm`**. Tình huống: GIA đang hiệu lực; gửi `[{"ma_hm":"GIA","thao_tac":"BO"},{"dong":1,"ma_hm":"MOI","thao_tac":"THEM","ten":"Mới","dvt":"m","o_goc":{}}]`. BO được gán `dong=1`, trùng dòng THEM → vi phạm khóa chính `(boq_id,dong)`, toàn bộ lần ghi thất bại. Phần chép tên/đơn vị, lọc nguồn và giữ tiền/khối lượng đúng trên đường thông thường.
- **(d) Không — Nên sửa:** `m4/sql_boq_bo.py:155` còn dùng GOC/THEM/THAY/BO trong câu hướng người dùng, chưa đạt mục B.5 về tiếng Việt nghiệp vụ. **Không mở quyền mới**; migration chỉ thay thân hàm.

**Kết luận năm việc**

1. **Phạm vi — Đạt:** đúng ba tệp được giao, fixture giả; báo cáo khớp diff, có **29 test NOT_RUN**, không tuyên bố PG xanh.
2. **Đúng yêu cầu — Không:** có **1 Chặn** tại câu (c).
3. **Tiền, số liệu, quyền — Đạt qua review tĩnh:** giữ nguyên trường tiền/khối lượng dạng text, không thêm phép tính/làm tròn; guard máy chủ giữ nguyên.
4. **Không phá phần cũ — Đạt qua review tĩnh:** giữ nhánh caller cũ; không thêm bảng/cột, thư viện, engine, kết nối, API AI trực tiếp hoặc SQL chéo module trong mã nghiệp vụ mới.
5. **Giao diện/câu người dùng — Nên sửa:** câu lỗi tại dòng 155 như trên; không thêm định dạng ngày/tiền.

**Chưa đạt để gộp: 1 Chặn; gate PostgreSQL vẫn chờ, chưa xác định lỗi mới so với nền.** Tôi chỉ đọc, không chạy test hay PostgreSQL. Số dòng trên thuộc `lat/bo-1b`; đường dẫn `m4/` và `ha_tang/` nằm dưới `src/kho_tri_thuc/`.

**Hỏi Claude**

- Claude xác nhận BO tối thiểu đi cùng THEM có `dong=1` là đầu vào hợp lệ theo §2 chứ? `m4/sql_boq_bo.py:207` khiến hai dòng cùng nhận số 1 và cả lần ghi thất bại; giao việc cho phép BO chỉ gửi mã nhưng chưa nêu ngoại lệ khi trộn số dòng tường minh/tự sinh.