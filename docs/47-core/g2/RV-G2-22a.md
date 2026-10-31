**Biên bản review chéo G2-22a — Kết luận: Cần sửa**

Nhánh `lat/g2-22`, HEAD `67bf132`; đối chiếu với `hop-nhat-20261023` tại `d57133c`.

**Kết quả kiểm trọng tâm:**

- **Phạm vi đạt:** đúng 3 tệp whitelist; không sửa 016.
- **Quyền đạt qua kiểm tĩnh:** migration dùng owner Core, `SECURITY DEFINER`, `search_path=pg_catalog,pg_temp`, thu hồi PUBLIC và giới hạn EXECUTE. Không thấy SQL chéo module, DROP/xóa hoặc ghi bí mật/DSN.
- **Drain đạt qua kiểm tĩnh:** chờ tiến trình/Job ngoài khóa; có ca kiểm `503 TIEN_TRINH_DANG_DUNG` + `Retry-After: 2`.
- **Đối chiếu PID/thời điểm tạo/Job:** có kiểm và từ chối khi chưa xác minh; không diệt tiến trình lạ. Đường nâng cấp còn thiếu như bảng dưới.
- **Test G2-21:** không thêm skip hoặc bỏ ca; các assertion đổi từ khóa lần đầu sang lần thứ ba phù hợp đề. Nghiệp vụ PG dùng login Core thật; thiếu ca lỗi sau readiness.

Quy ước đường dẫn: `C = src/kho_tri_thuc/core`, `T = tests`.

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| **Counter bị reset trước khi khởi động hoàn tất.** Trigger reset khi chuyển `CON_GIU`, nhưng controller còn phải gửi `nhan_accept`. Nếu readiness hợp lệ rồi gửi lệnh này bị lỗi pipe, mỗi lần lại reset về 0 rồi ghi lỗi thành 1. Tôi đã tái hiện bằng mock **3 lần: counter đều bằng 1, trạng thái `CORE_GIU`**, không khóa. Vi phạm yêu cầu giãn 2/4 giây, lần ba khóa tại API §3.10b. | **Chặn** | `C/sql/022_vong_doi.sql:52`; `C/tien_trinh.py:340`; `T/test_g2_21.py:111` |
| **Phiên G2-21 tồn tại trước nâng cấp vẫn không đối chiếu được.** Migration thêm `ten_job` với giá trị NULL cho phiên cũ; `_phien_da_dung` trả False ngay khi thiếu tên Job. Sau Core restart, dòng `CON_GIU` cũ vẫn mắc `CONG_CAN_DOI_CHIEU`, kể cả tiến trình đã chết. Chưa có đường xử lý nâng cấp an toàn hoặc test chứng minh trường hợp này. | **Cần sửa** | `C/sql/022_vong_doi.sql:38`; `C/tien_trinh.py:84` |
| **Hồi quy G2-16 chưa được giải quyết.** Fixture G2-16 áp toàn bộ migration nhưng `_khoa()` chỉ ghi một lỗi. Với 022, kết quả là `CORE_GIU`; ca Admin mở khóa sẽ gặp `CONG_CAS`, còn ca khóa sau restart vẫn đòi `CONG_KHOA_LOI`. Đây là bất tương thích xác định qua mã; chưa xác nhận bằng chạy PG. | **Cần sửa** | `C/sql/022_vong_doi.sql:83`; `T/test_g2_16.py:241`; `T/test_g2_16.py:367`; `T/test_g2_16.py:378` |

**Bằng chứng kiểm:** `git diff --check` đạt; tái hiện lỗi counter bằng mock trong bộ nhớ. Không chạy gate suite/PG/Windows thật trong sandbox chỉ đọc, nên chưa xác nhận đạt/tổng hoặc không có lỗi mới so với nền. Không đọc kho thật, tệp bí mật hay `*.local.json`; không sửa tệp.

**Hỏi Claude:** xác nhận điểm Chặn trước khi giao vòng sửa; chốt cách xử lý hồi quy G2-16 vì tệp test này nằm ngoài whitelist hiện tại.