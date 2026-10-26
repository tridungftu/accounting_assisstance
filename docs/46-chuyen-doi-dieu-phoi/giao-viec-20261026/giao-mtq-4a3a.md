# MTQ-4a3a: Ma trận thẩm quyền, resolver SQL cho 9 điểm CRM/M1 còn lại (CD-012). Rủi ro cao: SECURITY DEFINER + migration.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì **chặn** (trả `MTQ_CAN_RESOLVER_MTQ4`) và ghi "Cần Anh/lead".
- Đọc `AGENTS.md`, `CLAUDE.md` §2 và §4. Ghi tệp UTF-8 không BOM. `pg_migrations.py` giữ LF.
- **Không commit**. Không mở server hay PostgreSQL DEMO. Không xóa file.
- Test PG tự tạo CSDL `kho_test_*` từ DSN quản trị như `tests/test_mtq_cong_sql.py`; **không** đọc `KHO_PG_DEMO_*`, **không** đòi DSN trỏ sẵn vào `kho_test_*`.
- Làm trong worktree hiện tại, nhánh `lat/mtq-4a3a`, dựng từ hợp nhất. Đã có:
  - M0039: lõi `master.mtq_quyet_dinh`, catalog `master.mtq_danh_muc_hanh_dong`;
  - M0041/M0043: cổng phiên `master.mtq_quyet_dinh_phien(text,jsonb,numeric)` và `master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric)` trong `k2/sql_mtq_cong.py`;
  - adapter `k2/quyen.py:kiem_tham_quyen`.
- **Không sửa** M0039/M0041/M0043 hay các hằng SQL cũ. Thay đổi đi bằng migration mới:
  - tên tạm `M00xx_MTQ_CONG_C`, dòng đánh dấu `# MTQ-4a3a — CD-012:`;
  - `CREATE OR REPLACE` giữ nguyên chữ ký và ACL (`REVOKE PUBLIC`, `EXECUTE` chỉ `app_web`);
  - test không ghim migration cuối hay hash byte tệp.

**Căn cứ:**
- Thiết kế `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md`: §4.1 (bảng ô), §4.2 (điểm nối CRM luồng B/M1/file soát), §5.1 (trình tự, không fallback), §5.2 (tiền).
- Báo cáo `giao-viec-20261026/bao-cao-mtq-4a2.md`: 9 điểm bỏ vì cổng SQL chỉ giải được `master.hop_dong` (luồng B, màn `TIEP_NHAN`) và `master.du_an` (`DU_AN_BAN`).

**Ánh xạ lệnh cũ → khóa catalog** (theo §4.1; lát sau MTQ-4a3b nối Python theo đúng bảng này):

| Điểm (`k2/crm.py`) | Lệnh cũ | Khóa catalog | Đối tượng `{bang,id}` |
|---|---|---|---|
| `trich_tu_docx`, `nhan_ket_qua_6` | `NOP_HOP_DONG` | `CRM:TIEP_NHAN:LAP` | `master.phap_nhan` (chưa có HĐ) |
| `bo_sung_ho_so` | `BO_SUNG_HO_SO` | `CRM:TIEP_NHAN:SUA` | `kho.chung_tu` (hồ sơ CRM) |
| `_trich_lai` | `DOI_CHIEU_TRICH_LAI` | `CRM:TIEP_NHAN:KIEM` | `kho.chung_tu` |
| `kiem_nhan_tien` | `NHAN_TIEN` | `M1:TIEN:LAP` | `master.phap_nhan` |
| `lien_ket` | `LIEN_KET_TIEN` | `M1:TIEN:SUA` | `master.hop_dong` (HĐ của đợt `lich_thu`) |
| `go_lien_ket` | `LIEN_KET_TIEN` | `M1:TIEN:HUY` | `kho.lien_ket_chung_tu` |
| `xuat_file_soat` | `XUAT_FILE_SOAT` | `CRM:FILE_SOAT:XEM` | `master.hop_dong` |
| `tep_file_soat` | `XUAT_FILE_SOAT` | `CRM:FILE_SOAT:XEM` | `kho.lo_xuat` (lô CRM) |

**Việc: migration mới, `CREATE OR REPLACE` cả hai hàm cổng.**
1. Thêm resolver whitelist trong `mtq_quyet_dinh_phien` (không SQL động, không để client chọn bảng tùy ý):
   - `master.phap_nhan`: `pn = id`; HĐ/DA/LH/khách đều NULL, nên chỉ phạm vi loại `PHAP_NHAN` khớp. Chỉ hợp lệ cho `CRM:TIEP_NHAN:LAP` và `M1:TIEN:LAP`.
   - `kho.chung_tu`:
     - `pn` lấy từ dòng, chỉ khi `loai` là hồ sơ CRM luồng B (hằng `KIND` mà `k2/crm.py` dùng).
     - Nếu hồ sơ đã gắn phiên bản HĐ (`master.hop_dong_phien_ban.chung_tu_id`) thì lấy HĐ đó để xét phạm vi HĐ/DA/LH/khách.
     - Chỉ hợp lệ cho `CRM:TIEP_NHAN:SUA` và `CRM:TIEP_NHAN:KIEM`.
   - `master.hop_dong`: giữ nguyên luồng B/`TIEP_NHAN` hiện có. Mở thêm:
     - `M1:TIEN:SUA`;
     - `CRM:FILE_SOAT:XEM`;
     - chỉ cho HĐ thuộc CRM. Đọc code để xác định điều kiện (vd `module_chu IS NULL`); không chắc thì chặn và ghi "Cần lead".
   - `kho.lien_ket_chung_tu`:
     - `pn` từ dòng, HĐ từ `hop_dong_id` (có thể NULL, khi đó chỉ phạm vi PN).
     - Chỉ hợp lệ cho `M1:TIEN:HUY`.
   - `kho.lo_xuat`:
     - `pn` từ dòng, chỉ khi `loai = 'FILE_SOAT'` và `du_lieu->>'module' = 'CRM'`.
     - Chỉ hợp lệ cho `CRM:FILE_SOAT:XEM`.
   - Cặp (bảng, khóa catalog) ngoài bảng trên → `MTQ_CAN_RESOLVER_MTQ4` như cũ.
   - **PN chưa bật MTQ → trả `CU` như cũ, không đổi hành vi.**
2. `mtq_ghi_tu_choi_phien`: suy `pn` cho nhật ký từ chối theo đúng các bảng mới.
3. Tiền: cả 8 khóa trên là `PHI_TIEN` trong catalog nên không đòi tiền. **Không** đổi catalog.
4. Đăng ký migration trong `pg_migrations.py` theo mẫu M0043/M0044 (lead đánh số khi gộp).

**Test, tệp mới `tests/test_mtq_cong_c_sql.py` (PG, `skipUnless KHO_PG_DSN_TEST`; tự tạo CSDL):**
- Từng dòng bảng ánh xạ, khi PN bật MTQ:
  - người có phạm vi đúng thì cho phép;
  - sai phòng hoặc không có phạm vi thì từ chối có mã;
  - không fallback.
- PN chưa bật → `nguon = 'CU'` cho mọi bảng mới.
- Cặp sai, ví dụ `kho.chung_tu` với `CRM:FILE_SOAT:XEM`, hoặc `master.phap_nhan` với `M1:TIEN:SUA` → `MTQ_CAN_RESOLVER_MTQ4`.
- `kho.chung_tu` không phải hồ sơ CRM, hoặc `kho.lo_xuat` của module khác → chặn.
- Phạm vi `HOP_DONG` khớp qua `kho.lien_ket_chung_tu.hop_dong_id` và qua hồ sơ đã gắn phiên bản.
- Ghi từ chối có `phap_nhan_id` đúng.
- ACL: `PUBLIC` không có `EXECUTE`; `app_web` có.
- Không ghim migration cuối.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_cong_c_sql tests.test_mtq_cong_sql`, PYTHONPATH=`src;.;tests`. Phần PG sẽ skip trong sandbox; lead chạy PG.

**Tệp (3):** `k2/sql_mtq_cong.py` (thêm hằng `MTQ_CONG_C_SQL`, không đổi hằng cũ), `ha_tang/pg_migrations.py`, `tests/test_mtq_cong_c_sql.py`.

**Báo cáo (≤ ⅓ trang):** resolver đã thêm, điều kiện "HĐ thuộc CRM" đã chọn và căn cứ, "Cần Anh/lead", thông điệp commit `[MTQ-4a3a] …`.
