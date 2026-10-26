(a) **Đạt** — Đối tượng cũ trả nguyên resolver đơn; hai cổng khớp M0057 sau khi loại đúng bốn thay đổi NGUON. Phần tử thiếu `nguon_khoa` giữ hành vi cũ. `src/kho_tri_thuc/k2/sql_mtq_cong.py:2109,2117,2284,2309`.

(b) **Đạt** — rS lấy đủ subject qua FK instance/ref/SHA; rA kiểm mapping hiện hành; tập giữ mọi PN và cả subject không giải được để chặn. Whitelist không mở HĐ CRM, không nhận PN từ JSON. `src/kho_tri_thuc/k2/sql_mtq_cong.py:2110,2119,2148,2169,2218`.

(c) **Không — Chặn:** Alias instance có thể dùng nhầm quyền của profile khác. `src/kho_tri_thuc/k2/sql_mtq_cong.py:2190,2202` chỉ đếm profile có `source_instance_id` chính xác; M0049 xét cả UUID profile và tên instance chuẩn hóa. **Vi phạm:** mục D(c), khóa NGUON đúng M0049 và phạm vi nguồn tường minh A1.

Tình huống: cấp `INVOICE_SET|U|CTY A` cho profile UUID `U`; sau đó thêm instance tên `U`, có profile khác và mapping `CTY A` về cùng PN. Actor có tick, không có quyền PHAP_NHAN. Resolver nguồn mới vẫn chọn khóa đã cấp cho profile cũ vì instance mới có đúng một profile → **cho phép nguồn chưa được cấp quyền**. Đây là kết luận từ đối chiếu tĩnh, chưa chạy ca PG.

(d) **Đạt** — Cặp `master.phap_nhan` mới chỉ nhận `M2:HOA_DON:DUYET` và `M5:KHO:DUYET`; PN lấy từ bản ghi DB. `src/kho_tri_thuc/k2/sql_mtq_cong.py:2115,2134`.

(e) **Đạt** — Giữ `STABLE`, `SECURITY DEFINER`, `search_path`; `CREATE OR REPLACE` giữ ACL, không cấp thêm EXECUTE cho `app_web`. Audit kiểm lại từng PN để chọn PN từ chối. `src/kho_tri_thuc/k2/sql_mtq_cong.py:2101,2233,2396,2436`.

Năm kiểm tra chung:

- **Phạm vi: Đạt.** Đúng ba tệp được giao; fixture giả; đủ 22 test. Worker ghi NOT_RUN, không tuyên bố đã chạy. Gate **607 đạt, 0 mã lỗi mới** là kết quả lead cung cấp.
- **Đúng yêu cầu: Không**, do điểm (c). Giới hạn nhiều khóa cùng PN chỉ qua PHAP_NHAN đã được lead chấp nhận tạm.
- **Tiền, số liệu, quyền: Không**, do vượt phạm vi nguồn ở (c); không phát hiện thay đổi phép tính tiền.
- **Không phá phần cũ: Đạt qua kiểm tĩnh.** Chỉ append migration; không thêm engine, bảng/cột, kết nối hoặc truy cập chéo module ngoài phạm vi được giao.
- **Giao diện/câu chữ: Nên sửa.** Lý do mới còn “đúng module từ CSDL”, chưa thuần tiếng Việt nghiệp vụ. `src/kho_tri_thuc/k2/sql_mtq_cong.py:2211`.

**Hỏi Claude**

Claude xác nhận tình huống UUID profile trùng tên instance ở (c) có phải bị chặn theo M0049? `src/kho_tri_thuc/k2/sql_mtq_cong.py:2202` — resolver hiện chỉ đếm trong instance, khác tập ứng viên của validator M0049.

**Kết luận: Chưa gộp — còn một điểm Chặn và mục Hỏi Claude.**