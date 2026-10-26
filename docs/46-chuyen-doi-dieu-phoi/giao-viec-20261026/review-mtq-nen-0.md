## Review Codex (chỉ đọc) — MTQ-NEN-0 · 26/10 ~20:30

(a) **Đạt** — So khối trực tiếp: resolver và whitelist giữ nguyên M0048; phần phạm vi, lõi quyết định và ghi audit không đổi. Hai cổng gọi helper mới tại `k2/sql_mtq_cong.py:1730`, `:1827`. Test so toàn JSON trước/sau tại `tests/test_mtq_cong_f_sql.py:128`, `:147`.

(b) **Đạt** — Helper là `STABLE SECURITY DEFINER`, đúng `search_path`, không có lệnh ghi hoặc SQL động; ACL thu hồi PUBLIC, cấp EXECUTE cho `app_web`: `k2/sql_mtq_cong.py:1357`, `:1852`. Test READ ONLY dưới vai `app_web` và kiểm số dòng nhật ký: `tests/test_mtq_cong_f_sql.py:226`, `:247`.

(c) **Đạt** — Chữ ký, thuộc tính bảo mật và ACL hai cổng khớp nguyên M0048; không SQL động: `k2/sql_mtq_cong.py:1699`, `:1788`, `:1844`. Có test đối chiếu ACL/owner trước–sau tại `tests/test_mtq_cong_f_sql.py:260`.

(d) **Không bảo đảm cách ly metadata — Nên sửa/chờ Claude chốt.** `app_web` biết UUID hợp đồng thuộc PN khác có thể gọi helper để nhận `pn`, `hd`, `da`, `lh`, `khach`; không cần danh tính/phạm vi hợp lệ. Các trường vẫn trả khi whitelist từ chối: `k2/sql_mtq_cong.py:1381`, `:1695`, `:1855`. **Rủi ro trung bình về cách ly PN**, tác động giới hạn ở UUID và quan hệ đối tượng; chưa thấy trả tiền, nội dung hồ sơ hoặc cấp quyền thao tác. Chưa ghi Chặn vì giao việc mục 1 yêu cầu rõ quyền EXECUTE trực tiếp này.

*Số dòng thuộc `lat/mtq-nen-0`; đường dẫn mã tính từ `src/kho_tri_thuc/`.*

- **Phạm vi — Đạt:** đúng 3 tệp được giao, chỉ append migration; test dùng fixture tổng hợp. Báo cáo worker tóm tắt khớp diff.
- **Đúng yêu cầu — Đạt phần triển khai:** helper đủ trường; hai cổng tái sử dụng; test kế thừa toàn bộ ca C/CRM/M4 và so với M0048.
- **Tiền, số liệu, quyền — Chưa kết luận:** không đổi phép tính/hạn mức; hai cổng giữ kiểm quyền máy chủ. Riêng metadata trực tiếp còn điểm (d).
- **Không phá phần cũ — Đạt qua đối chiếu tĩnh:** nhánh CU, lỗi, khóa và lõi giữ nguyên; không sửa M0039/catalog, không thêm gọi AI/dịch vụ ngoài.
- **Giao diện/câu người dùng — Đạt:** không đổi UI/ngày/tiền; câu trả về giữ nguyên. “Cần Anh/lead” chỉ nằm trong comment được chuyển nguyên khối.

**Kết luận:** Chưa kết luận Đạt vì còn **Hỏi Claude**; chưa xác lập điểm Chặn. Tôi kiểm `git diff --check` đạt, không chạy PostgreSQL. **224 ok, 0 lỗi, 0 mã mới so v5** là gate máy lead Anh cung cấp.

**Hỏi Claude:** Lead có chủ ý chấp nhận `app_web` đọc UUID/quan hệ đối tượng ngoài PN được cấp không? — `k2/sql_mtq_cong.py:1695`, `:1855`; chưa rõ ngoại lệ này so với nguyên tắc chung “không làm rộng quyền ra ngoài module hoặc pháp nhân”.
**Lead lọc (Claude):** Hỏi Claude (d) → KHÔNG chấp nhận lộ metadata đối tượng ngoài PN. Chuyển thành Chặn: thu hồi EXECUTE của app_web trên `master.mtq_giai_doi_tuong` (chỉ chủ sở hữu/hai cổng SECURITY DEFINER gọi). Hàm mở cho app_web ở NEN-1 chỉ trả boolean quyết định. Lỗi do giao việc của lead (mục 1 ghi EXECUTE cho app_web) — sửa ở vòng 2.

## Vòng 2 (lead tự kiểm theo mẫu: chỉ xem điểm Chặn vòng 1)
Đã sửa: không còn EXECUTE app_web trên master.mtq_giai_doi_tuong; test ACL + lỗi quyền chạy PG đạt (143 ok, 0 mã mới). Đạt.
