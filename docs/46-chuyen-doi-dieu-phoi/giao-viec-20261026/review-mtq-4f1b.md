| Câu trọng tâm | Kết luận và căn cứ |
|---|---|
| **(a)** | **Đạt qua đối chiếu tĩnh.** Lấy thân hàm mới nhất từ registry, chỉ thay guard; nhánh PN tắt giữ guard và replay cũ. Không thấy lấy lại thân lỗi thời. `src/kho_tri_thuc/ha_tang/pg_migrations.py:12314`; `tests/test_mtq_m4_ho_so_sql.py:86`. |
| **(b)** | **Đạt.** Đủ 14 lệnh, đúng khóa catalog; kiểm trước replay/CAS/ghi. `_SOAN` chỉ chạy khi cổng trả chế độ cũ, không có `cũ OR mới`. `src/kho_tri_thuc/m4/sql_mtq.py:13`; `src/kho_tri_thuc/ha_tang/pg_migrations.py:12312`; `tests/test_mtq_m4_ho_so_sql.py:106`. |
| **(c)** | **Không đủ để kết luận toàn câu.** Đối tượng đi qua resolver M0048/M0051, phụ lục tra HĐ thật, tạo mới giải dự án từ CSDL. Tuy nhiên, B6 tải mẫu/bộ chọn master chưa được nối trong diff. `src/kho_tri_thuc/m4/sql_mtq.py:23`; `src/kho_tri_thuc/m4/sql_mtq.py:32`; `src/kho_tri_thuc/ha_tang/pg_migrations.py:12346`. |
| **(d)** | **Đạt.** Không thêm Duyệt có tiền; không thay RLS, `ktt_duoc`, hàm master hay lệnh 02A/02B/02C. `src/kho_tri_thuc/ha_tang/pg_migrations.py:12317`; `tests/test_mtq_m4_ho_so_sql.py:77`. |
| **(e)** | **Đạt với đối tượng giải được.** Kiểm bật theo PN của đối tượng; có ca so đủ 14 lệnh tại B tắt trước/sau bật A. `src/kho_tri_thuc/m4/sql_mtq.py:34`; `tests/test_mtq_m4_ho_so_sql.py:418`. |

Năm mục kiểm: **Phạm vi đạt** — đúng ba tệp, fixture giả, đúng 22 test; worker ghi NOT_RUN, không nhận đã chạy. **Đúng yêu cầu chưa kết luận** vì B6. **Tiền/số liệu/quyền đạt trong phạm vi** — kiểm tại SQL, không đổi phép tính tiền. **Không phá phần cũ đạt qua đối chiếu tĩnh** — không thêm thư viện, engine, bảng/cột hay kết nối ngoài; không thấy vi phạm CD-018/CD-019/QD-09. **Câu cho người dùng: Nên sửa** như dưới.

**Chặn:** chưa phát hiện.

**Nên sửa:** `src/kho_tri_thuc/m4/sql_mtq.py:40` đưa khóa kỹ thuật như `M4:HO_SO:SUA` vào thông báo từ chối; đường HTTP hiện trả thông báo này cho người dùng. Chưa đạt mục B.5 về tiếng Việt nghiệp vụ.

Tôi chỉ kiểm tĩnh; `git diff --check` đạt. Kết quả PG **347 đạt, không mã lỗi mới, skip khớp nền v5** là gate lead cung cấp, tôi không chạy lại.

**Hỏi Claude**

- B6 được xác nhận là gate của **4f1c/4g4**, hay bắt buộc ngay trong **4f1b**? `src/kho_tri_thuc/ha_tang/pg_migrations.py:12320` để đọc/master cho lát sau, trong khi câu trọng tâm (c) yêu cầu B6 tại đây. Vì còn điểm này, tôi **chưa kết luận Đạt toàn lát**.