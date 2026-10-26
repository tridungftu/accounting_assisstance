# M4-DL3b: điểm nên sửa nhỏ của review M4-DL3 (lớp đọc phụ lục/BOQ Review)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở PostgreSQL. Không xóa file.
- Test PG tự tạo CSDL `kho_test_*`.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl3b`, dựng từ hợp nhất.

**Việc:**
1. `src/kho_tri_thuc/m4/review_phu_luc_pg.py`:
   - Trường `gt_hd_sau_pl` (khoảng dòng 166) là "giá trị HĐ ghi trên phụ lục cuối còn hiệu lực", **không phải** giá trị HĐ hiệu lực của Review gốc (gốc sau VAT + Σ `gt_sau_vat`). Đổi tên khóa DTO thành `gt_hd_ghi_tren_pl_cuoi` và ghi rõ trong docstring, để màn hình không hiển thị nhầm.
   - Ở trạng thái NULL (khoảng dòng 292): trả `boq: None` kèm `thong_bao` dùng chung của DL2, không trả `boq: []`.
   - Cờ "cần xem lại": `ly_do` nêu **số phụ lục** gây cờ.
2. `src/kho_tri_thuc/m4/review_data_pg.py`: công khai hai hàm DL3/DL4 đang gọi là `_kiem_quyen_doc` và `_nguon_hien_hanh`.
   - Thêm tên công khai `kiem_quyen_doc`, `nguon_hien_hanh`, giữ tên cũ làm bí danh để không vỡ.
   - Đổi chỗ gọi trong `review_phu_luc_pg.py`. **Không** sửa `review_dot_pg.py` ở lát này.
3. Không đổi chữ ký hàm ghi.

**Test:** cập nhật `tests/test_m4_review_phu_luc_pg.py` theo khóa mới, `boq: None`, lý do có số PL.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_review_phu_luc_pg tests.test_m4_review_data_pg tests.test_m4_review_dot_pg`, với PYTHONPATH=`src;.;tests`.

**Tệp (3):** `review_phu_luc_pg.py`, `review_data_pg.py`, `tests/test_m4_review_phu_luc_pg.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M4-DL3b] …`.
