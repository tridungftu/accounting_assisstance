## Review Codex (chỉ đọc) — MTQ-4f1a · 26/10 ~20:05

(a) **Đạt** — So toàn thân hai hàm sau khi loại phần bổ sung M4: khớp M0047. Chữ ký, `SECURITY DEFINER`, `search_path`, ACL giữ nguyên; không SQL động. `k2/sql_mtq_cong.py:843`, `:1237`, `:1342`.

(b) **Đạt** — Giải phạm vi qua FK, whitelist từng cặp đối tượng–lệnh M4; HĐ mới chỉ nhận `module_chu='M4'`, không mở HĐ CRM. `k2/sql_mtq_cong.py:1019`, `:1031`, `:1107`, `:1166`.

(c) **Đạt** — K có resolver phạm vi nhưng không nằm trong whitelist cấp quyền; `M4:02C_DUYET:DUYET` vẫn bị chặn bất kể tiền caller truyền. `k2/sql_mtq_cong.py:1069`, `:1190`.

(d) **Đạt trong phạm vi resolver** — Cho `M4:HO_SO:LAP` trên dự án thật; thiếu dự án hoặc dùng đối tượng pháp nhân thay thế bị chặn khi MTQ bật. `k2/sql_mtq_cong.py:1112`, `:1120`, `:1167`.

(e) **Đạt** — PN tắt trả `CU`; bật không fallback. Audit bổ sung suy PN cho đủ các bảng M4, riêng đợt đi qua dự án. `k2/sql_mtq_cong.py:1114`, `:1192`, `:1307`.

*Số dòng thuộc nhánh `lat/mtq-4f1a`; đường dẫn mã tính từ `src/kho_tri_thuc/`.*

| Việc kiểm | Kết luận |
|---|---|
| Phạm vi | **Nên sửa:** diff có 4/3 tệp, thêm `tests/test_mtq_crm_resolver_sql.py:47` ngoài danh sách giao. Báo cáo worker có bàn giao việc này cho lead; số **23 test** khớp mã: 8 tĩnh, 15 PG; ghi rõ `NOT_RUN`. Fixture tổng hợp, không thấy dữ liệu thật. |
| Đúng yêu cầu | **Đạt:** đủ 11 đối tượng, migration chỉ append, có test so toàn thân hàm. `ha_tang/pg_migrations.py:12188`; `tests/test_mtq_m4_resolver.py:68`. |
| Tiền, số liệu, quyền | **Đạt:** chưa mở Duyệt có tiền; quyền kiểm tại SQL máy chủ, không dựa nút UI. |
| Không phá phần cũ | **Đạt:** các hằng cũ nguyên vẹn, phần kế thừa M0047 khớp; không thêm gọi API AI trực tiếp. |
| Giao diện/câu người dùng | **Đạt:** không đổi UI, định dạng ngày/tiền; không thêm câu hướng người dùng hỏi Anh/lead. |

**Chặn:** Không phát hiện. **Để sau:** Không có.

Tôi tự kiểm so thân hàm và `git diff --check`: đạt; không chạy Python/PG. Gate **41/41 đạt, 0 mã lỗi mới so nền v5** là kết quả máy lead Anh cung cấp.

**Hỏi Claude:** Thay đổi `tests/test_mtq_crm_resolver_sql.py:47` đã được lead nhận vào phạm vi chưa? Báo cáo worker yêu cầu lead xử lý, nhưng giao việc vẫn chỉ liệt kê 3 tệp. **Chưa kết luận Đạt toàn lát khi xác nhận này còn mở.**
**Lead lọc (Claude):** Hỏi Claude → có: lead đã nhận tệp thứ 4 `tests/test_mtq_crm_resolver_sql.py` vào phạm vi ở vòng sửa test (thêm đúng 3 khóa M4 trên dự án theo B6). Đạt. Kiểm xác suất: khong.
