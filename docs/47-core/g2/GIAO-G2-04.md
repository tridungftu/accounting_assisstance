# G2 · giao G2-04 — nâng audit và sổ migration theo gói

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". Nền: worktree dựng từ `lat/g2-03` (đã có G2-00…G2-03). Dùng lại cách viết SQL/test của `001_vai.sql`…`003_phien.sql`:
- tiền tố vai test;
- login thật;
- không DROP ROLE / DATABASE (bộ chạy của lead tự dọn `kho_test_*`).

## Lát G2-04

**Tệp:** `src\kho_tri_thuc\core\sql\004_kiem_toan.sql`; `src\kho_tri_thuc\core\doi_cau_truc.py`; `tests\test_g2_04.py`.

**Căn cứ:**
- Chuẩn CSDL: audit; sổ migration theo gói §3.12.
- Đặc tả CSDL §7: `loi.lich_su_doi_cau_truc` với `ma_goi`, `so_phien_ban`, `ma_bam`, `ap_dung_luc`, người áp dụng, nguồn lịch sử.
- `ANH-XA-MIGRATION.md` (lineage M0013 COMMON / M0017 import hiện hành).
- **Dùng lại** cơ chế checksum / chặn hạ phiên bản của `src\kho_tri_thuc\ha_tang\postgres.py:217–260` (đọc, không sửa tệp này).

**Việc:**
- **Bảng nhật ký kiểm toán `loi`:**
  - chỉ thêm, bất biến (trigger chặn UPDATE / DELETE);
  - ghi ai (danh tính đã xác minh từ G2-03 nếu có ngữ cảnh), lúc nào, hành động, đối tượng, kết luận;
  - không ghi mã phiên / bí mật / toàn văn tài liệu.
- **Sổ `loi.lich_su_doi_cau_truc`:**
  - một dòng mỗi lần áp gói / phiên bản, checksum;
  - lệch checksum → chặn;
  - hạ phiên bản → chặn.
- **`doi_cau_truc.py`:**
  - áp một tệp SQL Core theo thứ tự (001, 002, 003, 004…), ghi sổ **trong cùng transaction**;
  - lỗi SQL → rollback cả sổ;
  - chạy lại: bỏ qua gói đã áp đúng checksum;
  - không in DSN.

**Test PG:**
- audit bất biến;
- checksum lệch bị chặn;
- hạ phiên bản bị chặn;
- lỗi SQL rollback cả sổ;
- chạy lại idempotent;
- runtime không ghi trực tiếp sổ.
