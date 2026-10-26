- **(a) Đạt qua review tĩnh:** hàm `STABLE SECURITY DEFINER`, cố định `search_path`; chỉ cấp `EXECUTE`, không cấp quyền bảng, không trả dòng thô/tệp. `k2/sql_cong_bo_hoa_don.py:15,17,38,70–73`.
- **(b) Đạt qua review tĩnh:** kiểm PN phiên trước khi đọc; công tắc M2 theo đúng PN, không công bố chính thức thì trả `CHO`, lý do “Chờ hóa đơn mua vào”, `hoa_don=[]`. PN B độc lập. `k2/sql_cong_bo_hoa_don.py:21–32,62`.
- **(c) Đạt qua review tĩnh:** phiên bản lấy theo `latest_observation_id`; trả hash nội dung đã lưu; tổng tiền thiếu giữ `NULL`, không thay bằng 0, giữ `UNPROVEN_NO_MINOR`. `k2/sql_cong_bo_hoa_don.py:40–46,57–60`.
- **(d) Đạt qua review tĩnh:** tái sử dụng `_dc_m2_doc`, không thay guard quyền hiện hữu; thân hàm chỉ đọc. Có ca `READ ONLY`, chưa chạy. `k2/sql_cong_bo_hoa_don.py:24`; `tests/test_xst1_cong_bo.py:298–304`.

Năm kết luận kiểm tra:

1. **Phạm vi — Đạt:** đúng 3 tệp giao; migration chỉ nối thêm tại `ha_tang/pg_migrations.py:12487`. Fixture là dữ liệu giả. Báo cáo khớp **3 test tĩnh + 7 test PG**, khai rõ **NOT_RUN, 0/10**, không nhận đã đạt.
2. **Đúng yêu cầu — Đạt về mã tĩnh:** đủ trường đầu hóa đơn, version/hash/PN, trạng thái nguồn và coverage; không sửa nơi tiêu thụ.
3. **Tiền, số liệu, quyền — Đạt về mã tĩnh:** không tính/suy diễn tiền; trả kèm tiền tệ, giữ thiếu căn cứ; quyền kiểm trong hàm máy chủ trước lookup.
4. **Không phá phần cũ — Chưa thấy vi phạm:** chỉ thêm gateway và migration; không đổi đường cũ, không gọi API AI trực tiếp, không thêm engine/kết nối/bảng tạm hay đường đọc chéo ngoài gateway được giao.
5. **Giao diện/câu người dùng — Đạt trong phạm vi:** lý do chờ bằng tiếng Việt nghiệp vụ; không thay giao diện. Ngày trong JSON là dữ liệu hợp đồng, chưa phải phần hiển thị.

**Chặn / Nên sửa / Để sau:** chưa phát hiện điểm cần ghi nhận. `git diff --check` đạt; reviewer không chạy test hoặc mở PostgreSQL. **Chưa kết luận Đạt toàn lát vì còn gate PG.**

**Hỏi Claude**

- Khi đến lượt PostgreSQL, 7 ca PG có đạt dưới `app_web`, gồm ACL bảng nguồn và `READ ONLY` không? `tests/test_xst1_cong_bo.py:81,282,298` — hiện chưa có kết quả thực thi để xác nhận.