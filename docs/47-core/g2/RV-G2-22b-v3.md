**Biên bản review chéo G2-22b-v3 — Kết luận: Cần sửa**

Nhánh `lat/g2-22b`, HEAD `ce6d616`; đối chiếu `hop-nhat-20261023...HEAD` và thay đổi sau `d9217fa`. Các đường dẫn `core/` dưới đây thuộc `src/kho_tri_thuc/core/`.

| Trọng tâm vòng 3 | Kết quả |
|---|---|
| Quét thử lại theo giãn 2/4 giây, lần 3 khóa | **Đã đóng qua đọc mã:** quét chấp nhận `failed`, dùng lại hạn retry và khóa bền vững của controller. Test kiểm trước/đúng hạn, lần 3 khóa và phục hồi sau lỗi readiness. `core/vong_doi.py:68`; `tests/test_g2_22.py:212,235,256`. |
| Chỉ đếm việc được phép nhận qua G2-14/06 | **Đã đóng về điều kiện quyền:** gọi lại `viec_kiem_quyen()`, rollback phiên kiểm tạm. Có ca thu hồi phạm vi/hành động, đối chiếu `viec.nhan()` bị từ chối và cho phép drain. Tuy nhiên, đường gọi mới phát sinh lỗi khóa dưới đây. `core/sql/024_che_do_chay.sql:107,109,147`; `tests/test_g2_22.py:702,711,740`. |

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Đảo thứ tự khóa, có thể deadlock với thu hồi quyền MTQ.** Hàm mới gọi `cap_phien()` trước, giữ khóa người dùng (`003_phien.sql:107`), rồi `viec_kiem_quyen()` mới lấy khóa MTQ chung (`006_mtq.sql:323`). Trong khi trigger đổi quyền lấy khóa MTQ độc quyền trước, rồi chờ khóa người dùng (`006_mtq.sql:699–701`; `003_phien.sql:224`). Tình huống: người tạo việc còn phiên lưu trong CSDL; lượt quét giữ khóa người dùng → giao dịch thu hồi phạm vi giữ khóa MTQ và chờ người dùng → lượt quét chờ MTQ. PostgreSQL phải hủy một giao dịch; nếu chọn giao dịch Admin, yêu cầu thu hồi bị rollback. Đây là hồi quy do diff vòng sửa, vi phạm tiêu chí mẫu review B.4 **“Không phá phần cũ”**. Các test mới đổi quyền và quét tuần tự nên chưa bắt trường hợp này. | **Chặn** | `core/sql/024_che_do_chay.sql:107,109` |

**Các kiểm tra còn lại:**

- **Phạm vi:** đúng 4 tệp theo ngoại lệ Lead đã duyệt tại `KE-HOACH-LAT-G2-G3.md:268`; không có tệp ngoài whitelist.
- **Chuẩn/quyền:** tên SQL không dấu; DEFINER có `search_path` cố định, thu hồi PUBLIC, giới hạn caller Core; không thấy mở quyền bảng hoặc SQL nghiệp vụ chéo module.
- **An toàn/dùng lại:** không thấy DROP, thao tác xóa hay ghi DSN/token vào log/audit. Dùng lại controller, cửa quyền và fixture hiện có. Test nghiệp vụ dùng login Core/module thật; owner dùng dựng và đối soát fixture.
- **Kiểm chứng:** `git diff --check` đạt. Lead báo **172/172**; tôi không chạy lại PG/Windows trong phiên chỉ đọc, chưa xác nhận độc lập số skip và lỗi so nền. Không đọc kho thật, tệp bí mật hoặc `*.local.json`.

**Hỏi Claude:** xác nhận phân loại **Chặn** tại `024_che_do_chay.sql:107,109` trước khi giao sửa? Tình huống deadlock đã xác định qua thứ tự khóa; gate được cung cấp chưa bao phủ ca quét và thu hồi quyền đồng thời.