## Review MTQ-4a3a (3392a36) — review-lat (Opus), 26/10 ~15:30

**Kết luận: Cần sửa.** Có 1 điểm chặn. M0045 chưa gộp, chưa chạy ở DEMO, nên sửa thẳng trong M0045.

**Chặn**
1. `k2/sql_mtq_cong.py:289-298`, `:327-328`: resolver `kho.lien_ket_chung_tu` nhận mọi liên kết, kể cả:
   - `VAY_TIEN` của M9 (`k2/vay.py:665`, `hop_dong_id` là HĐ VAY);
   - L11 `HD_PHIEU_KHO` của M5 (`chu_so_huu_module='M5'`, `pg_migrations.py:7799`).

   Khi PN đã bật, người có ô `M1:TIEN:HUY` cùng phạm vi gỡ được liên kết VAY hoặc L11. Lệch với nhánh `master.hop_dong` (đòi HĐ CRM); trái §5.1 (L11 đòi cả ô M2 và M5).

   Sửa resolver:
   - chỉ nhận `l.loai = 'HOP_DONG_DOT_TIEN'` (`crm.py:740`) và `chu_so_huu_module IS NULL`;
   - có `hop_dong_id` thì HĐ phải cùng PN và là HĐ CRM.

   Sửa test:
   - helper `lien_ket` (`tests/test_mtq_cong_c_sql.py:135-139`) đổi `'KHAC'` → `HOP_DONG_DOT_TIEN`;
   - thêm ca `VAY_TIEN`, `HD_PHIEU_KHO`, HĐ M4: PN bật → `MTQ_CAN_RESOLVER_MTQ4`, PN tắt → `CU`.

**Nên sửa**
2. `:299-301`: `kho.lo_xuat` chỉ suy được phạm vi PN, dù lô nào cũng có `du_lieu.hop_dong_id` (`crm.py:828`). Hậu quả: người có phạm vi HĐ/DA xuất được file soát nhưng không tải được chính file đó, buộc cấp phạm vi PN (làm rộng). Sửa: suy HĐ từ `du_lieu->>'hop_dong_id'`; kiểm UUID trước khi ép kiểu; HĐ phải là HĐ CRM cùng PN.
3. Test thiếu hai ca, khi PN bật:
   - id không tồn tại cho từng bảng mới → `MTQ_CAN_RESOLVER_MTQ4`;
   - hồ sơ gắn HĐ M4 hoặc HĐ có `crm_giao_ket` → chặn.

**Để sau**
4. Định nghĩa "HĐ thuộc CRM" (`module_chu IS NULL AND loai NOT IN ('VAY','MUA')`) theo `crm_s1.py:93` là đúng. RLS (`pg_migrations.py:1660`) và `crm.py:867` vẫn coi MUA là CRM, nhưng profile CRM chỉ tạo `THUE_DAT`/`BAN_NHA`, nên định nghĩa này hẹp hơn, an toàn. Ghi vào QUYET-DINH.
5. Nhánh `TIEP_NHAN` (M0041, giữ nguyên): `hd_ho_tro` không loại HĐ VAY. Hành vi cũ, để lát MTQ-4 sau xem.
6. Dòng 413-423 so `id::text = …`, nên mỗi lần ghi từ chối quét cả `kho.chung_tu` (theo mẫu cũ). Chỉ ảnh hưởng tốc độ.

**Đạt**
- Chữ ký, `SECURITY DEFINER`, `search_path`, ACL giống hệt M0041. Không SQL động. Danh tính chỉ từ `ktt_danh_tinh()`.
- Nhánh `TIEP_NHAN`/`DU_AN_BAN` tương đương logic cũ.
- `mtq_ghi_tu_choi_phien` giữ khóa theo request, không nuốt lỗi INSERT.
- PN tắt → `CU` cho mọi bảng. PN bật → không có đường fallback. `pn IS NULL` mà có PN khác bật → chặn.
- M0045 nối cuối, `PG_SCHEMA_VERSION = len(...)`, LF, test không ghim migration cuối.
- Test PG tự tạo CSDL, phủ 9 điểm, ca PN tắt, ca cặp sai, ACL. Phần nới test của lead không làm yếu kiểm hai hằng cũ.
