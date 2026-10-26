| Câu trọng tâm | Kết luận và căn cứ trên `lat/xs-4b` |
|---|---|
| **(a) Cờ trạng thái** | **Đạt** — đúng 3 chế độ × 3 nhóm người; THU khóa xuất/công bố, TAT chỉ đọc và ẩn lưới; mã ngoài danh mục → TAT. `k2/sql_module.py:63–79`. |
| **(b) Admin, CAS, nhật ký, giữ kín người thử** | **Không** — Admin hiện hành, lý do, CAS và nhật ký đã có (`sql_module.py:88–140`), nhưng danh sách người thử lộ qua nhật ký (`sql_module.py:161,178`). |
| **(c) S5, không lối tắt** | **Không — chưa đủ căn cứ chốt**. Đường `app_web` chặn đúng mã (`sql_module.py:125–126`); chưa rõ yêu cầu bảo vệ trước DML bằng quyền chủ bảng đối với mặc định và `da_van_hanh` (`sql_module.py:8,20,124`). |
| **(d) ACL/RLS, READ ONLY, độc lập PN** | **Đạt** — thu hồi quyền bảng/helper; DEFINER có `search_path` cố định; hàm đọc không ghi; khóa và truy vấn theo module × PN. `sql_module.py:55–80,102,181–201`. |
| **(e) Bảng chung, thu hồi bằng đánh dấu** | **Đạt** — 3 bảng cố định; thu hồi cập nhật dấu thời gian, cấp lại thêm dòng. `sql_module.py:8–43,156,173–174`. |

**Chặn — Lộ danh sách người thử qua nhật ký.**  
Tại **`src/kho_tri_thuc/k2/sql_module.py:161,178`**, `to_jsonb(moi/cu)` đưa cả `nguoi_dung_id`, module, PN và dấu cấp/thu hồi vào `nhat_ky.su_kien`. Vi phạm **giao việc §2 và D(b): không lộ danh sách người thử cho `app_web`**. Tình huống: Admin cấp thử CRM/PN A cho U → phiên `app_web` đọc `sau` của các dòng `doi_tuong_bang='master.module_nguoi_thu'` → lấy được U và dựng danh sách hiện hành từ lịch sử cấp/thu hồi. Quyền SELECT nhật ký đã được cấp tại `ha_tang/pg_migrations.py:1156`; diff không bảo vệ các bản ghi mới này.

**Kết luận 5 kiểm tra:** Phạm vi **Đạt**: đúng 3 tệp, fixture giả, báo cáo khớp 15 test/10 PG và ghi rõ NOT_RUN. Đúng yêu cầu **chưa đạt** vì điểm Chặn trên và S5 còn cần làm rõ. Tiền/số liệu/quyền: không phát sinh tính tiền; quyền **chưa đạt** về bảo mật người thử. Không phá phần cũ: migration chỉ append, không thêm engine/kết nối hay SQL chéo module; QD-09 còn câu hỏi dưới. Giao diện/câu người dùng: **Đạt trong phạm vi SQL**, không thêm UI/ngày/tiền.

`git diff --check` đạt. Tôi không chạy PG; kết quả 15 test đạt và hồi quy không thêm mã lỗi là **gate lead cung cấp**.

**Hỏi Claude**

- **Chặn:** Cơ chế nào ngăn `app_web` đọc danh sách người thử trong nhật ký? `sql_module.py:161,178` — quyền SELECT hiện có vẫn đọc được payload mới.
- **Nên sửa/chưa rõ:** S5 có yêu cầu chặn DML thông thường của chủ bảng không? `sql_module.py:116,124–125` — đổi mặc định M9 thành VAN_HANH hoặc sửa `da_van_hanh=true` sẽ vượt kiểm tra, dù các role ứng dụng đã bị khóa.
- **Nên sửa/chưa rõ:** CSDL `kho_test_xs4_*` có hạn giữ/cách dọn bên ngoài nào? `tests/test_xs4_sql.py:99–108` — mỗi lần chạy tạo DB mới, cleanup chỉ đóng kết nối; chưa thấy căn cứ đáp ứng QD-09.

**Chưa thể kết luận Đạt hoặc gộp lát.**