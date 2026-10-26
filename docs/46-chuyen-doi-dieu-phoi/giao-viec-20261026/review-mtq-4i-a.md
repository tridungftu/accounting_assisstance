## Review Codex (chỉ đọc) — mtq-4i-a · 26/10 ~20:30

- **(a) Đạt** — khóa chuẩn hóa đủ ba thành phần; chỉ nhận `INVOICE_SET`/`KHO10_PHIEU`, loại L11 bị chặn: `src/kho_tri_thuc/k2/sql_mtq_lien_module.py:32–45,83`.
- **(b) Đạt** — giải duy nhất profile thuộc instance hoạt động; kiểm mapping `master.anh_xa_nguon` đúng instance/ref/SHA, loại, hiệu lực và PN; phòng phải thuộc PN: `sql_mtq_lien_module.py:47–81`. Không có hoặc mapping mơ hồ → từ chối.
- **(c) Đạt** — thêm migration, không sửa hằng M0039; `CREATE OR REPLACE` chỉ thay nhánh NGUON, giữ guard và audit cấp/thu hồi: `sql_mtq_lien_module.py:24–27,91–102`; `src/kho_tri_thuc/ha_tang/pg_migrations.py:12188`. Test đối chiếu OID/owner/ACL và audit tại `tests/test_mtq_nguon_scope_sql.py:152,160,249`.
- **(d) Đạt** — mỗi dòng chỉ cấp cho PN khớp mapping; docstring giao rõ caller 4i-c kiểm mọi PN và kiểm lại mapping khi sử dụng: `sql_mtq_lien_module.py:9–11,76–81`; test nguồn gộp: `tests/test_mtq_nguon_scope_sql.py:238`.

Năm kết luận kiểm tra:

1. **Phạm vi — Nên sửa báo cáo:** diff đúng bốn tệp được phép, gồm `tests/test_mtq_sql.py` được lead bổ sung; fixture dùng dữ liệu giả. Nhưng `docs/46-chuyen-doi-dieu-phoi/giao-viec-20261026/bao-cao-mtq-4i-a.md:4` vẫn ghi “ba tệp”. Số **18 test mới** khớp mã.
2. **Đúng yêu cầu — Đạt:** thực hiện A1 và phần làm rõ của lead; chưa nối caller đúng giới hạn lát.
3. **Tiền, số liệu, quyền — Đạt:** không đổi phép tính tiền; quyền kiểm tại SQL, giữ Admin, revision, bất biến và audit.
4. **Không phá phần cũ — Đạt trong diff:** giữ các nhánh validator cũ; không sửa RLS nền, không thêm lời gọi AI trực tiếp.
5. **Giao diện/câu người dùng — Đạt:** không đổi UI/ngày/tiền; lỗi mới qua cơ chế chuyển thông báo tiếng Việt hiện có.

**Kết luận: Đạt kỹ thuật, không có Chặn; có thể gộp.** `git diff --check` đạt. Gate **51 đạt, 0 mã lỗi mới so v5** theo thông tin Anh cung cấp; tôi không chạy PostgreSQL.

**Hỏi Claude:** Không có.
**Lead lọc (Claude):** Đạt. Kiểm xác suất: co.
