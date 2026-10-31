**Biên bản review chéo G2-22b — Kết luận: Cần sửa**

Nhánh `lat/g2-22b`, HEAD `86f3d2e`; commit triển khai `c4ab266`. Đối chiếu `hop-nhat-20261023...HEAD`.

| Kiểm trọng tâm | Kết quả |
|---|---|
| Không sửa migration 001–023 | **Đạt**: diff chỉ thêm migration 024. |
| Owner / DEFINER / search_path / REVOKE | **Đạt qua đọc mã**: tạo dưới owner, FORCE RLS, policy owner, thu hồi PUBLIC và chỉ cấp EXECUTE cho login Core — `core/sql/024_che_do_chay.sql:28,69,233`. |
| Rảnh 300 giây, drain quá hạn giữ trạng thái | **Chưa đạt đầy đủ**: có ngưỡng và bộ đếm, nhưng thiếu điều kiện hàng chờ — phát hiện bên dưới. |
| Đánh thức đúng một instance | **Đạt ở mức callback**, chưa chứng minh luồng queue/inbox thật — `core/vong_doi.py:55`, `tests/test_g2_22.py:370`. |
| `TAT` không tự bật | **Đạt qua đọc mã**: kiểm công tắc và giữ shared transaction lock trong lúc khởi động — `core/sql/024_che_do_chay.sql:103`. |
| Admin áp chế độ qua CAS + audit | **Đạt qua đọc mã**: xác minh phiên/Admin, khóa dòng, CAS và audit cùng transaction — `core/sql/024_che_do_chay.sql:204`. |
| Không diệt tiến trình lạ; dùng lại G2-21/22a | **Đạt trong diff**: gọi controller hiện có, không thêm đường kill; chờ drain ngoài khóa — `core/vong_doi.py:41,86`. |

Các đường dẫn `core/…` dưới đây thuộc `src/kho_tri_thuc/core/…`.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Chưa có đường đánh thức từ hàng việc/inbox thật.** `nguon='viec'/'inbox'` chỉ là tham số; tìm trong `src` không thấy caller của `VongDoiCore`, cũng không có nối với G2-14/15. Tình huống: module đang stopped, một việc được ghi `queued` hoặc inbox nhận sự kiện, không có HTTP → mã hiện tại không khởi động module. Vi phạm yêu cầu đánh thức ngay không cần HTTP của SDK §3.6.4 và đề G2-22. | **Chặn** | `core/vong_doi.py:51`; `tests/test_g2_22.py:370` |
| **Điều kiện “rảnh” thiếu việc chờ và inbox.** `kiem_ranh()` chỉ kiểm bộ đếm RAM và thời gian. Tình huống: còn việc được phép nhận hoặc inbox chưa xử lý, nhưng chưa có lượt `su_dung()` → sau 300 giây vẫn drain. SDK §3.6.4 quy định inbox phải rỗng và không còn việc chờ được phép nhận. Test hiện chỉ truyền tên nguồn, không tạo các trạng thái bền vững này. | **Chặn** | `core/vong_doi.py:77`; `core/vong_doi.py:83`; `tests/test_g2_22.py:373` |
| **Vượt whitelist:** diff thêm **4 tệp**, trong khi đề và mục “Tách G2-22” chỉ giao 3; chưa thấy căn cứ mở whitelist cho migration 024. | **Cần sửa** | `core/sql/024_che_do_chay.sql:1` |

**Kiểm chứng:** `git diff --check` đạt. Test PG dùng login Core/module/cài đặt thật; owner dùng để dựng fixture và kiểm kết quả. Có ca âm CAS, non-Admin, ACL và rollback. Không thấy DROP/xóa, SQL chéo module hoặc ghi DSN/token vào audit trong diff. Không đọc kho thật hay tệp bí mật.

Kết quả G2-22 **23/23**, G2-08 **24**, G2-16 **34**, G2-21 **49** là số liệu Lead cung cấp; tôi chưa chạy lại độc lập.

**Hỏi Claude:** xác nhận hai tình huống Chặn trên và căn cứ duyệt tệp thứ tư trước khi giao sửa hoặc gộp.