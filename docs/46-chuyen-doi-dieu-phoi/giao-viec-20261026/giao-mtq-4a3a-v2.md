# MTQ-4a3a vòng 2: sửa theo review (chặn: liên kết tiền lọt VAY/L11). Rủi ro cao.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi UTF-8 không BOM. `pg_migrations.py` giữ LF. **Không commit**. Không mở server hay PostgreSQL DEMO. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-4a3a`. Đã có commit 3392a36: M0045 `M0045_MTQ_CONG_C`, hằng `MTQ_CONG_C_SQL`.
- M0045 **chưa phát hành**: sửa thẳng trong `MTQ_CONG_C_SQL`. **Không** đổi M0041/M0043, tên M0045 hay `pg_migrations.py`.

**Đọc trước:** `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-mtq-4a3a.md` và giao việc gốc `giao-mtq-4a3a.md`.

**Việc** (`k2/sql_mtq_cong.py`, hằng `MTQ_CONG_C_SQL`, ở cả `mtq_quyet_dinh_phien` lẫn `mtq_ghi_tu_choi_phien`):
1. **Chặn:** resolver `kho.lien_ket_chung_tu`.
   - Chỉ nhận dòng có `loai = 'HOP_DONG_DOT_TIEN'` (loại CRM ghi ở `k2/crm.py` hàm `lien_ket`) **và** `chu_so_huu_module IS NULL`.
   - Có `hop_dong_id`: HĐ phải cùng PN và là HĐ CRM, cùng điều kiện đã dùng cho `master.hop_dong` ở M1/FILE_SOAT.
   - Ngoài các điều kiện trên → không suy được đối tượng → `MTQ_CAN_RESOLVER_MTQ4` khi PN bật; `CU` khi PN tắt (như hiện có).
2. **Nên sửa:** resolver `kho.lo_xuat` suy thêm HĐ từ `du_lieu->>'hop_dong_id'` để phạm vi HĐ/DA/LH/khách khớp được.
   - Kiểm chuỗi là UUID hợp lệ trước khi ép kiểu (regex hoặc khối `BEGIN … EXCEPTION`); sai dạng thì chỉ phạm vi PN.
   - HĐ phải là HĐ CRM cùng PN; khác thì chặn.
3. Một dòng chú thích trong SQL: định nghĩa "HĐ thuộc CRM" = `module_chu IS NULL AND loai NOT IN ('VAY','MUA')` theo `crm_s1.py:93`, hẹp hơn RLS (an toàn).

**Test** (`tests/test_mtq_cong_c_sql.py`):
- Helper `lien_ket`: đổi `'KHAC'` thành `HOP_DONG_DOT_TIEN`.
- Thêm ca liên kết `VAY_TIEN` (HĐ VAY), `HD_PHIEU_KHO` (`chu_so_huu_module='M5'`), liên kết gắn HĐ M4:
  - PN bật → `MTQ_CAN_RESOLVER_MTQ4`;
  - PN tắt → `CU`.
- `lo_xuat` có `du_lieu.hop_dong_id`:
  - người có phạm vi `HOP_DONG` đúng HĐ → cho phép;
  - HĐ khác → chặn;
  - `hop_dong_id` sai dạng → chỉ xét phạm vi PN, không lỗi SQL.
- PN bật, id không tồn tại cho từng bảng mới (`master.phap_nhan`, `kho.chung_tu`, `kho.lien_ket_chung_tu`, `kho.lo_xuat`) → `MTQ_CAN_RESOLVER_MTQ4`.
- Hồ sơ `kho.chung_tu` gắn HĐ M4 hoặc HĐ có `crm_giao_ket` → chặn.
- Ghi từ chối có `phap_nhan_id` đúng cho ca mới.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_cong_c_sql tests.test_mtq_cong_sql`, PYTHONPATH=`src;.;tests`. PG sẽ skip; lead chạy.

**Tệp (2):** `k2/sql_mtq_cong.py`, `tests/test_mtq_cong_c_sql.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[MTQ-4a3a] vòng 2: …`.

**Thêm: lỗi PG lead chạy (15:09).** Lỗi ở `tests/test_mtq_cong_c_sql.py:258` `test_sai_loai_ho_so_lo_xuat_va_module_bi_chan_nhung_pn_tat_giu_cu`: `self.lo_xuat(pn, "M5")` bị trigger `lo_xuat_m5_chi_chu` chặn.
- Trigger ở `ha_tang/pg_migrations.py` khoảng dòng 3495–3520. Lô M5 phải do chủ bảng ghi, `loai='FILE_SOAT'`, có `hash`, `duong_dan = 'm5-xuat/<sha>.xlsx'`, `du_lieu` có `stage_id` và `muc_dich='FILE_SOAT'`.
- Sửa helper test cho ca "module khác CRM": dựng lô M5 đúng các điều kiện đó, chạy bằng vai chủ bảng như test khác đang dựng dữ liệu. Nếu không dựng được thì dùng một `du_lieu->>'module'` khác CRM mà trigger không chặn (ví dụ `'M2'`) và ghi rõ trong báo cáo.
