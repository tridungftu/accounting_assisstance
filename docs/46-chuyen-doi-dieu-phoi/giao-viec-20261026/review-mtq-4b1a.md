## Review Codex (chỉ đọc) — MTQ-4b1a · 26/10 ~19:34

(a) **Đạt** — Hai hàm giữ chữ ký, `SECURITY DEFINER`, `search_path` và ACL; không SQL động. So thân hàm với M0045: các nhánh cũ giữ nguyên, riêng D bổ sung whitelist G7. `k2/sql_mtq_cong.py:474`, `:507`, `:595`, `:744`, `:831`.

(b) **Đạt** — Whitelist ghép từng bảng với khóa catalog đúng màn; X phân biệt báo giá/hợp đồng. Không mở thêm cặp trên H hoặc TY_GIA. `k2/sql_mtq_cong.py:665`, `:670`, `:685`.

(c) **Đạt** — PN tắt trả `CU`; PN bật không fallback; không suy được PN mà có PN khác bật thì trả `MTQ_CAN_RESOLVER_MTQ4`. `k2/sql_mtq_cong.py:649`.

(d) **Đạt** — Resolver lấy PN/HĐ/DA/LH/khách từ dòng và FK thật; báo giá dùng revision hiện hành, bản xuất báo giá dùng revision ghim. Nhánh nối H kiểm cùng PN, loại module khác và VAY/MUA. `k2/sql_mtq_cong.py:515`, `:529`, `:540`, `:547`, `:556`, `:581`.

(e) **Đạt** — Audit bổ sung suy PN trực tiếp từ từng bảng mới; giữ phần kiểm request và ghi nhật ký của M0045. `k2/sql_mtq_cong.py:785`, `:818`.

*Số dòng trên thuộc nhánh `lat/mtq-4b1a`, đường dẫn mã tính từ `src/kho_tri_thuc/`.*

- **Phạm vi — Đạt:** đúng 3 tệp được giao; fixture tổng hợp. Báo cáo khớp nội dung diff và số lượng 18 test; worker ghi rõ NOT_RUN.
- **Đúng yêu cầu — Đạt:** M0047 append cuối, giữ nguyên migration/hằng SQL cũ; test phủ whitelist, cặp sai, bật/tắt, ID thiếu và ACL.
- **Tiền, số liệu, quyền — Đạt:** khóa mới thuộc PHI_TIEN, không thêm phép tính tiền; quyền kiểm tại SQL phía máy chủ.
- **Không phá phần cũ — Đạt:** đối chiếu thân hàm xác nhận phần cũ giữ nguyên; diff không thêm gọi API AI hoặc dịch vụ ngoài.
- **Giao diện/câu người dùng — Đạt:** không đổi UI/ngày/tiền; không thêm câu hướng người dùng hỏi Anh/lead.

**Kết luận: Đạt trong phạm vi lát; không phát hiện Chặn, Nên sửa hoặc Để sau.** Tôi tự kiểm `git diff --check` đạt và đối chiếu mã; không chạy unittest/PG vì không có Python. Gate **18/18 đạt**, các module khác **0 lỗi mới so nền v5**, là kết quả máy lead Anh cung cấp.

**Hỏi Claude:** Không có.
**Lead lọc (Claude):** Đạt, không lọc. Kiểm xác suất: co.
