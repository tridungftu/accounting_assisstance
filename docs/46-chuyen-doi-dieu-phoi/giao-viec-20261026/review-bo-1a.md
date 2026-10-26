- **(a) Không — Chặn:** `m4/sql_boq_bo.py:79` chọn dòng cuối theo `ma_hm`, khiến THEM và THAY có cùng tác dụng. Thứ tự ngày → lần, lọc `DA_KY`, nguồn truy vết và thứ tự trả về đều đúng.
- **(b) Đạt:** `m4/sql_boq_bo.py:36` lấy tên CHECK từ catalog; chỉ mở thêm BO. `ha_tang/pg_migrations.py:12403` nối migration mới; không sửa writer hoặc dòng dữ liệu cũ.
- **(c) Đạt:** `m4/sql_boq_bo.py:62` kiểm BO với trạng thái trước phụ lục; dòng 73 báo lỗi có BOQ, dòng và mã hạng mục. Dòng 85 trả nguyên tiền/khối lượng `text`.
- **(d) Đạt:** `m4/sql_boq_bo.py:52` dùng `STABLE SECURITY INVOKER`; dòng 89 thu quyền PUBLIC, chỉ cấp EXECUTE cho `app_web`. Không có lệnh ghi trong hàm; test READ ONLY tại `tests/test_m4_boq_bo_pg.py:257`.

**Kết luận năm việc**

1. **Phạm vi — Đạt:** đúng ba tệp được giao, fixture là dữ liệu giả; báo cáo mô tả khớp diff. Tệp test mới có 3 test tĩnh và 10 PG, khớp số 10 PG NOT_RUN của worker.
2. **Đúng yêu cầu — Không, có 1 Chặn:** `m4/sql_boq_bo.py:79` và `:86` vi phạm **giao việc §2: “THEM thêm hạng mục; THAY thay dòng cùng ma_hm”**. Tình huống: BOQ gốc không có B → PL1 THEM B → PL2 THAY B → hủy PL1. Hàm vẫn trả B từ PL2, tức THAY tự tạo lại hạng mục không còn hiệu lực; không báo thao tác không hợp lệ như projection được dẫn trong giao việc (`m4/review_phu_luc_pg.py:144`).
3. **Tiền, số liệu, quyền — Đạt trong phạm vi lát:** không tính toán, ép kiểu hay làm tròn; quyền kiểm tại PostgreSQL qua RLS hiện hữu.
4. **Không phá phần cũ — Đạt qua kiểm tra tĩnh:** migration cũ/writer giữ nguyên; không thêm bảng/cột, engine, kết nối, gọi AI hoặc SQL chéo vùng dữ liệu trong mã nghiệp vụ mới.
5. **Giao diện/câu người dùng — Đạt trong phạm vi SQL:** thông báo lỗi có diễn giải tiếng Việt; không thêm giao diện hoặc định dạng ngày/tiền.

Gate **13/13** và **0 mã lỗi mới** là kết quả lead cung cấp; tôi không chạy PostgreSQL hay test.

**Hỏi Claude**

- Claude xác nhận THEM/THAY phải phân biệt theo trạng thái hạng mục đang hiệu lực như projection hiện có chứ? `m4/sql_boq_bo.py:79` hiện áp dụng “dòng cuối thắng”; tình huống hủy PL1 nêu trên làm THAY tạo lại B. Cần chốt ngữ nghĩa này trước khi gộp vì writer cũ được yêu cầu giữ nguyên trong BO-1a.

**Chưa đạt để gộp: 1 Chặn và còn mục Hỏi Claude.**