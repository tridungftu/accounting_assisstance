# M3-1c vòng 2: bỏ chỉ mục UNIQUE chặn nhầm, thay bằng trigger chỉ xét bản liên kết hiện hành (điểm Chặn của review)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM; `pg_migrations.py` giữ LF. **Không commit**.
- Không mở PostgreSQL; test PG tự tạo CSDL `kho_test_*`. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m3-1c` (a7b3997). Migration của lát này **chưa phát hành** (tên tạm `M00xx_M3_CO_SO_B`), nên được sửa trực tiếp hằng `M3_CO_SO_B_SQL`. M0042 không đổi.
- Nhánh hợp nhất hiện đã có M0043 (MTQ-4a0b). Lát này sẽ thành M0044 khi lead gộp. Test **không** ghim migration cuối hay số thứ tự: định vị theo dấu `# M3-1c — CD-013:` và `PG_MIGRATIONS[:i]`.

**Lỗi:** `sql_m3.py` (khoảng dòng 188–192) tạo `UNIQUE (phap_nhan_id, hoa_don_id) WHERE trang_thai='DA_XAC_NHAN'`.
- `m3.hoa_don_hop_dong` chỉ ghi thêm. Mỗi lần xác nhận hoặc sửa là một revision mới nối bằng `khoa_lien_ket`/`thay_cho_id`, nên dòng DA_XAC_NHAN cũ ở lại mãi.
- Hệ quả, chỉ mục chặn nhầm:
  - (a) xác nhận lại sau khi hóa đơn có phiên bản mới;
  - (b) hủy liên kết sai (revision PENDING) rồi xác nhận lại đúng HĐ;
  - (c) chuyển liên kết sang cơ sở HĐ revision mới.

**Sửa (trong `M3_CO_SO_B_SQL`):**
- **Bỏ** chỉ mục UNIQUE trên.
- Thêm **trigger BEFORE INSERT** trên `m3.hoa_don_hop_dong`. Khi `NEW.trang_thai = 'DA_XAC_NHAN'`:
  - `pg_advisory_xact_lock` theo `hoa_don_id`;
  - từ chối (SQLSTATE 23505, thông điệp tiếng Việt) nếu có dòng `l` DA_XAC_NHAN cùng `(phap_nhan_id, hoa_don_id)` thỏa `l.khoa_lien_ket <> NEW.khoa_lien_ket` **và** `l` là bản hiện hành của chuỗi (`NOT EXISTS (SELECT 1 FROM m3.hoa_don_hop_dong s WHERE s.thay_cho_id = l.id)`).
- Hàm trigger không dùng `SECURITY DEFINER`, có `SET search_path` cố định, đủ schema.

**Test `tests/test_m3_sql.py` (PG):**
1. Cùng chuỗi, revision 2 xác nhận lại → được.
2. Chuỗi cũ đã có revision PENDING (hủy) → chuỗi mới xác nhận cùng hóa đơn được.
3. Hai chuỗi hiện hành cùng xác nhận một hóa đơn → bị từ chối.
4. Ứng viên (chưa xác nhận) trùng → vẫn được.

Giữ mọi ca cũ của vòng 1 trừ ca ghim chỉ mục UNIQUE.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m3_sql tests.test_m3_dang_thuc`, với PYTHONPATH=`src;.;tests`.

**Tệp (≤ 3):** `k2/sql_m3.py`, `tests/test_m3_sql.py`, và `ha_tang/pg_migrations.py` chỉ khi cần.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M3-1c] vòng 2: …`.
