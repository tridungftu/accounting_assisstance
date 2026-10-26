# M4-CD2b: M4 · Nghiệm thu & chi phí dự án, nên sửa của review M4-CD2 (làm trước lần nạp dữ liệu thật CD-011)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL DEMO. Không xóa file.
- Test PG tự tạo CSDL `kho_test_*` như `tests/test_chuyen_review_pg.py`; **không** đọc `KHO_PG_DEMO_*`.
- **Không đọc dữ liệu Review thật.** Chỉ dữ liệu DEMO dựng trong test.
- Làm trong worktree hiện tại, nhánh `lat/m4-cd2b`, dựng từ hợp nhất (đã có CD1 và CD2).

**Căn cứ:** `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-m4-cd2.md`, mục "Nên sửa" 1–3 và "Để sau" 6.

**Việc:**
1. `tools/chuyen_review_sqlite_sang_pg.py` (khoảng dòng 379, 404–405):
   - Thêm cờ giai đoạn (`NAP` / `DOI_CHIEU`). In báo cáo HOAN_TAT của bước nạp **ngay sau** `ghi_pg` commit.
   - Lỗi ở bước nạp: báo "Nạp không hoàn tất; không ghi gì (đã hoàn tác)."
   - Lỗi ở bước đối chiếu: báo "Đối chiếu không hoàn tất; dữ liệu đã nạp vẫn được giữ."
   - Giữ mã thoát (lệch 2, lỗi 1) và thông báo ASCII-safe như CD1.
2. `m4/review_doi_chieu.py` (khoảng dòng 151–157):
   - Mỗi bảng có `ma_hd`: thêm `so_dong_mo_coi` cho cả hai phía (SQLite: `ma_hd` không có trong `hop_dong`; PG: `hop_dong_id IS NULL`).
   - Đọc `hop_dong_id` ở PG và kiểm:
     - dòng mồ côi phải có `hop_dong_id` NULL;
     - dòng không mồ côi phải có `hop_dong_id` đúng HĐ cùng `ma_hd` (qua `review_chep_hop_dong` cùng `nguon_id`).
   - Sai → dòng lỗi loại `GAN_HD_SAI`, `khop = false`.
3. `m4/review_doi_chieu.py` (khoảng dòng 204–206):
   - Đưa `tong_sqlite == tong_pg` (theo HĐ và theo đợt) vào `khop`.
   - Trả danh sách khóa HĐ/đợt lệch tổng (chỉ mã/khóa và hai số tổng; không tên đối tác).
4. In `sha256_khop`: SHA256 tệp nguồn so với giá trị ghi trong `review_chep_nguon` của lần chụp đang đối chiếu. Không khớp thì `khop = false`.

**Test** (thêm vào `tests/test_chuyen_review_pg.py`):
- Phần thuần/tĩnh:
  - đếm mồ côi đúng;
  - lệch tổng HĐ/đợt làm `khop = false` kể cả khi từng ô được dựng cho khớp (giả lập bằng dữ liệu đọc sẵn);
  - thông báo theo giai đoạn đúng.
- Phần PG:
  - dòng `canh_bao` mồ côi bị gán `hop_dong_id` → `GAN_HD_SAI`;
  - dòng gán nhầm HĐ khác → `GAN_HD_SAI`;
  - SHA khác → `sha256_khop = false`;
  - lỗi giả ở bước đối chiếu → HOAN_TAT nạp đã in và dữ liệu nạp còn nguyên.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_chuyen_review_pg`, PYTHONPATH=`src;.;tests`.

**Tệp (3):** `tools/chuyen_review_sqlite_sang_pg.py`, `m4/review_doi_chieu.py`, `tests/test_chuyen_review_pg.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M4-CD2b] …`.
