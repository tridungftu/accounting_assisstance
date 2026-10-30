# G2 · giao G2-09 — metadata tài liệu, tệp, biến thể và kết quả

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-08` (đã có G2-00…G2-08). Dùng lại vai / phiên / audit / registry / MTQ / công tắc; quy ước như cũ.

## Lát G2-09

**Tệp:** `src\kho_tri_thuc\core\sql\009_tai_lieu.sql`; `src\kho_tri_thuc\core\tai_lieu.py`; `tests\test_g2_09.py`.

**Căn cứ:**
- Chuẩn CSDL: khối `loi_tai_lieu`;
- Đặc tả CSDL §3.4 (tài liệu, tệp, biến thể, quyền nội dung, kết quả, nguồn kết quả);
- Chuẩn SDK (`tai_lieu`, `tep`, `ket_qua`; nguồn kết quả do Core gắn);
- contract `tham_chieu_tep.v1` (G2-17).
- **Dùng lại** bất biến / hash của kho tệp hiện có (`src\kho_tri_thuc\ha_tang\store.py`, `giao_dien\intake.py`) — chỉ đọc để giữ quy tắc. Bytes tệp là G2-10.

**Việc:**
- Bảng trong schema `loi_tai_lieu`: tài liệu, tệp (hash, kích thước, mime), biến thể (gốc / ocr / đã che…), quyền nội dung, kết quả (revision, trạng thái duyệt riêng), nguồn kết quả.
- **Quan hệ cùng pháp nhân;** RLS theo phiên xác minh như G2-06.
- **Revision và trạng thái duyệt tách riêng;** "xong" của engine ≠ "đã duyệt".
- **Không công bố kết quả thiếu tệp / hash.** Nguồn kết quả do Core gắn (module không tự khai).
- Thêm dòng, không sửa đè / xóa.

**Test PG** (login thật + phiên):
- cùng pháp nhân / sai pháp nhân bị chặn;
- revision tăng, duyệt riêng;
- công bố thiếu hash bị chặn;
- module khai nguồn bị bác;
- runtime không ghi thẳng.
