- **(a) Đạt qua kiểm tĩnh:** nhận bằng `FOR UPDATE SKIP LOCKED`, cấp token mới; gia hạn/kết thúc khóa dòng, kiểm worker, token, danh tính và hạn lease. `k2/sql_hang_viec.py:181`, `:199`, `:202`, `:220`, `:260`.
- **(b) Đạt qua kiểm tĩnh:** việc có tác động ngoài hết lease chuyển `CHUA_RO`; không được nhận lại tự động. Retry có giới hạn/khoảng chờ; dừng hợp tác giữ việc đang chạy tới khi worker xác nhận. `k2/sql_hang_viec.py:148`, `:154`, `:179`, `:251`, `:279`.
- **(c) Đạt qua kiểm tĩnh:** khóa đồng bộ với M0056 theo module × PN, kiểm `cho_ghi` trước nhận; PN B dùng khóa và bộ lọc riêng. `k2/sql_hang_viec.py:172`, `:173`, `:178`.
- **(d) Đạt qua kiểm tĩnh:** tạo trong transaction caller, unique chống trùng và từ chối khác hợp đồng; tham chiếu UUID, RLS/ACL theo PN; không sửa `ktt_duoc`; một bảng chung, có mốc/hạn giữ, không lệnh xóa. `k2/sql_hang_viec.py:33`, `:52`, `:68`, `:116`, `:127`, `:286`.

*Đường dẫn `k2/` và `ha_tang/` tính từ `src/kho_tri_thuc/`.*

| Việc kiểm | Kết luận |
|---|---|
| **1. Phạm vi** | Đạt: đúng 3 tệp giao. Fixture dùng dữ liệu giả. Báo cáo khớp 24 test, gồm 22 ca PG; ghi **NOT_RUN 0/24**, không tuyên bố test xanh. |
| **2. Đúng yêu cầu** | Đạt về nội dung tĩnh: đủ vòng đời, tiến độ, nhật ký, dedupe, lease, retry, dừng và khai báo hạn giữ. Chưa xác nhận runtime. |
| **3. Tiền, số liệu, quyền** | Không có phép tính tiền. Giới hạn số lần thử/tiến độ có constraint; quyền kiểm tại SQL, helper riêng không cấp cho `app_web`. |
| **4. Không phá phần cũ** | Đạt qua diff: migration chỉ nối thêm tại `ha_tang/pg_migrations.py:12404`; không chạm queue cũ, thêm cổng/engine trùng hay SQL tới dữ liệu nghiệp vụ module khác. |
| **5. Giao diện/câu người dùng** | Không có thay đổi giao diện hoặc định dạng ngày/tiền. Mã lỗi SQL phục vụ hợp đồng nội bộ; chưa có đường hiển thị người dùng trong lát. |

**Không phát hiện điểm Chặn hoặc Nên sửa trong diff. Chưa kết luận Đạt toàn lát khi gate PostgreSQL còn chờ.** `git diff --check` đạt; tôi không chạy test, mở PostgreSQL hay ghi tệp.

**Hỏi Claude**

- Khi tới lượt PostgreSQL, kết quả 24 test và lỗi mới so với nền là gì? `tests/test_xs2_sql.py:43`, `:63` — hiện chưa có bằng chứng chạy migration, tranh nhận, CAS và RLS/ACL thực tế.