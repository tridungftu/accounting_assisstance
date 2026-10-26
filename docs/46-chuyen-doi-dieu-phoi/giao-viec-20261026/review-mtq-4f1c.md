- **(a) Đạt qua review tĩnh:** thay đúng tên policy; nhánh PN tắt giữ biểu thức quyền cũ, kể cả actor biên nhận và điều kiện REVIEW/đợt đã nộp. `m4/sql_mtq.py:82,125,132,135,151`.
- **(b) Không — chưa đủ căn cứ kết luận:** có lọc từng dòng qua `master.mtq_duoc_doc`, không `cũ OR mới`; nhưng điều kiện đợt đã nộp/vai trò tài liệu chỉ nằm trong nhánh CU. Cần Claude xác nhận giới hạn đọc khi bật. `m4/sql_mtq.py:84,112,135,139`.
- **(c) Đạt qua review tĩnh:** bộ chọn và guard tải mẫu dùng `M4:HO_SO:LAP` theo dự án; thiếu dự án trả false/chặn. `m4/sql_mtq.py:99,117`; `ha_tang/pg_migrations.py:12424`. Chưa xác minh bằng PG.
- **(d) Đạt qua review tĩnh:** không sửa hai hàm quyền/RLS nền; đường đọc không thêm khóa hoặc ghi; câu từ chối mới là tiếng Việt nghiệp vụ. `m4/sql_mtq.py:94`; `ha_tang/pg_migrations.py:12426,12430`.

*Các đường dẫn `m4/`, `ha_tang/` nằm dưới `src/kho_tri_thuc/`; số dòng thuộc nhánh lát.*

| Việc kiểm | Kết luận |
|---|---|
| Phạm vi | **Đạt:** đúng ba tệp; fixture giả; 20 test = 7 tĩnh + 13 PG. Báo cáo ghi NOT_RUN, không tuyên bố đã chạy đạt. |
| Đúng yêu cầu | **Không:** test bắt buộc có lỗi đầu vào cụ thể bên dưới; giới hạn đọc còn cần xác nhận. |
| Tiền, số liệu, quyền | **Chưa kết luận:** không thêm phép tính tiền; quyền kiểm tại SQL, nhưng phạm vi đọc đợt/tệp còn câu hỏi. |
| Không phá phần cũ | **Nên sửa/làm rõ:** không thêm engine, dịch vụ ngoài, bảng/cột phát sinh; helper mới đọc trực tiếp schema `master`, cần đối chiếu CD-018. |
| Giao diện/câu người dùng | **Đạt qua review tĩnh:** câu mới rõ nghiệp vụ; không phát sinh hiển thị ngày/tiền. |

**Chặn — test B6/CU/READ ONLY truyền tham số không hợp lệ.**  
`tests/test_mtq_m4_doc_sql.py:212,277,349` truyền `p_limit=100`, trong khi `_Q` của hai hàm bộ chọn giữ giới hạn **1–50**. Với dự án hợp lệ và đủ quyền Lập, lời gọi sẽ báo `M4_THAM_SO_SAI`, thay vì trả danh sách để kiểm assertion. Vi phạm phần **Test (PG): oracle PN tắt, B6, READ ONLY** của giao việc.

**Kết luận: chưa đủ điều kiện gộp — 1 Chặn; còn “Hỏi Claude”.** `git diff --check` sạch. Không chạy test/PＧ; máy không có `python` trên PATH.

**Hỏi Claude**

- Có xác nhận sửa đầu vào `limit=100` của các ca dương trước gate PG không? `tests/test_mtq_m4_doc_sql.py:277` — guard hiện hành chắc chắn từ chối.
- Khi PN bật, `HO_SO:XEM` được đọc cả đợt nháp và tệp `HO_SO_DOT` chưa nộp hay vẫn phải giữ hạn chế tài liệu/đợt trong KK §1? `m4/sql_mtq.py:135,139` — điều kiện này chỉ còn ở nhánh CU.
- Các SELECT mới từ M4 tới `master.du_an`, `master.hop_dong`, `master.mtq_kich_hoat` có ngoại lệ CD-018 được chốt không? `m4/sql_mtq.py:103,104,111` — diff đọc trực tiếp bảng ngoài schema M4; chưa có căn cứ ngoại lệ.