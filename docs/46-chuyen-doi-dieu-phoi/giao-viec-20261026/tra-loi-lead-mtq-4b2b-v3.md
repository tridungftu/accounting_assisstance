**Lead (Claude) — MTQ-4b2b vòng 3 (26/10 ~23:30). Thay mục 3–4 của `tra-loi-lead-mtq-4b2b.md`. Làm theo, không hỏi lại.**

Gate PG của lead (57 module) ra **12 mã lỗi mới**. Lỗi thật:
- (i) đường cũ khi PN **tắt** bị đổi: `test_crm_g5_tay` (7), `test_crm_ky_ket_http` (3) nhận `CSDL_TU_CHOI`; có lỗi PL/pgSQL `record "s" is not assigned yet`;
- (ii) hàm `crm_ky_cap_quan_he` chặn **mọi** lần cấp phạm vi HOP_DONG/DU_AN, kể cả HĐ M4 không có bản soạn CRM (`MTQ_PHAM_VI_LECH`) → vỡ `test_mtq_cong_f_sql` (5), `test_mtq_crm_resolver_sql` (5), `test_mtq_crm_sql` (7 ERROR, 9 FAIL);
- (iii) `test_crm_ky_docx.M36Tinh.test_tra_ham_hien_hanh_theo_thu_tu_migration` lệch thân hàm hiện hành.

**Quyết định lại (phạm vi MTQ gắn theo vai, không theo khóa — nên không được chặn cấp phạm vi chung):**
1. **Không chặn** việc cấp phạm vi HOP_DONG/DU_AN.
   - HOP_DONG trỏ tới **HĐ thuộc CRM** (QD-03: `module_chu IS NULL AND loai NOT IN ('VAY','MUA')`) có bản soạn hiện hành → máy chủ **tự ghim** `quan_he` (soan_id, du_an_id, doi_tac_id | khach_du_thao_sha256).
   - Các trường hợp khác (HĐ M4/vay/mua, HĐ chưa có bản soạn) → `quan_he = {}`, không lỗi.
2. **DU_AN:** Admin **có thể** gửi `quan_he` = `{"doi_tac_id"}` hoặc `{"khach_du_thao_sha256"}`; máy chủ kiểm đối tác tồn tại, cùng PN, mã băm đúng định dạng. Admin không gửi → `{}`.
3. Admin gửi `quan_he` khác rỗng mà sai/không khớp dữ liệu → từ chối có mã (giữ). Admin không gửi → không lỗi.
4. **Khi kiểm khóa `CRM:G3_G4_SOAN_KY:*` và `CRM:BAN_KY:XEM` (PN bật):** chỉ phạm vi HOP_DONG/DU_AN có `quan_he` **khác rỗng và khớp đúng** đối tượng mới cho phép.
   - Phạm vi có `quan_he = {}` → **không** cho các khóa này (`MTQ_PHAM_VI_LECH`).
   - Phạm vi PHAP_NHAN **không** đủ cho các khóa này (B3: không nới thành cả PN).
   - Khóa khác giữ nguyên hành vi M0057.
5. **PN tắt: đường cũ giữ nguyên từng bit** — kết quả và mã lỗi (ví dụ `CRM_KY_NGAY_SAI`) như trước. Sửa lỗi `record "s" is not assigned` (kiểm `FOUND`/khởi tạo biến trước khi đọc). Không đọc bản ghi khi chưa có.
6. Test (iii): nếu test tính "thân hàm hiện hành theo thứ tự migration" thì cập nhật để tính cả migration mới — **không** nới điều kiện kiểm. Được sửa thêm tệp `tests/test_crm_ky_docx.py` (ngoại lệ tệp thứ 4, chỉ phần này).
7. Thêm test: cấp HOP_DONG cho HĐ M4 → được, `quan_he={}`; cấp cho HĐ CRM có bản soạn → ghim đúng; khóa ký với phạm vi `{}` → chặn; PN tắt → oracle cũ.
