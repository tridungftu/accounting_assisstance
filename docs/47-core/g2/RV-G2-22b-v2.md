**Biên bản review chéo G2-22b-v2 — Kết luận: Cần sửa**

Nhánh `lat/g2-22b`, HEAD `d9217fa`; đối chiếu `hop-nhat-20261023...HEAD` và các thay đổi sau vòng trước.

| Kiểm trọng tâm | Kết quả |
|---|---|
| Đánh thức từ hàng việc/inbox thật qua DEFINER | **Đã bổ sung** vòng quét, đọc dữ liệu bền vững; có test PG/Windows cho luồng cơ bản. Còn lỗi phục hồi khởi động bên dưới. |
| Rảnh xét cả việc chờ và inbox | **Chưa đầy đủ**: đã kiểm hàng chờ, nhưng điều kiện “được phép nhận” chưa khớp G2-14. |
| Công tắc từng pháp nhân | **Đạt qua đọc mã**: lọc công tắc mới nhất; thiếu công tắc coi là `TAT`; kiểm lại dưới advisory lock trước khởi động. |
| Whitelist | **Đạt**: 4 tệp đã được Lead duyệt tại `KE-HOACH-LAT-G2-G3.md:268`. Điểm vượt whitelist vòng trước đã đóng. |

Các đường dẫn `core/…` dưới đây thuộc `src/kho_tri_thuc/core/…`.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Vòng quét ngừng thử lại sau lỗi khởi động đầu tiên.** Khi có việc chờ, lần bật đầu thất bại, `TienTrinhCore` chuyển sang `failed`; cleanup giải phóng tiến trình nhưng giữ trạng thái này (`tien_trinh.py:263,379`). Vòng quét chỉ chấp nhận `stopped`, nên mọi lượt sau đều bỏ qua, kể cả đã hết 2 giây chờ. Việc/inbox bị treo cho đến khi có tác động ngoài; không tiếp tục được chuỗi retry 2/4 giây, lần 3 mới khóa theo đề và API §3.10b. Test “sau lỗi tạm thời” chỉ gây lỗi đọc hàng chờ, không gây lỗi khởi động. | **Chặn** | `core/vong_doi.py:68`; `tests/test_g2_22.py:186` |
| **Đếm cả việc hiện không được phép nhận, khiến không thể đóng rảnh.** SQL chỉ kiểm người dùng, quyền module và công tắc; không kiểm quyền hành động/phạm vi MTQ trên đối tượng như `viec_kiem_quyen()` của G2-14. Tình huống: tạo việc hợp lệ, sau đó thu hồi phạm vi MTQ nhưng vẫn giữ quyền module → `viec_nhan()` từ chối, trong khi `so_viec` vẫn lớn hơn 0; sau 300 giây `kiem_ranh()` tiếp tục từ chối drain dù không còn việc được phép nhận. Chưa đáp ứng SDK §3.6.4; thiếu ca âm tương ứng. | **Chặn** | `core/sql/024_che_do_chay.sql:119`; `core/vong_doi.py:136` |

**Các kiểm tra còn lại:** qua đọc diff, DEFINER có `search_path` cố định, thu hồi PUBLIC và chỉ cấp EXECUTE cho login Core; không thấy mở quyền bảng, SQL nghiệp vụ chéo module, DROP/xóa hoặc ghi DSN/token vào log/audit. Dùng lại controller và fixture hiện có. Các thao tác nghiệp vụ trong test dùng login Core/module thật; owner phục vụ fixture và đối soát.

**Kiểm chứng:** `git diff --check` đạt. Không chạy lại test PG/Windows trong phiên chỉ đọc; kết quả đạt/tổng và lỗi mới so nền: **CHƯA KIỂM độc lập**. Không đọc kho thật, tệp bí mật hoặc `*.local.json`.

**Hỏi Claude:** xác nhận hai tình huống Chặn tại `vong_doi.py:68` và `024_che_do_chay.sql:119` trước khi giao sửa; bộ test hiện chưa bao phủ retry sau lỗi khởi động và việc bị thu hồi quyền MTQ.