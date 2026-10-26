**Cần lead:** `src/kho_tri_thuc/m4/sql_duyet.py:477–483` hiện dựng JSON seal **không chứa `truoc_da_duyet` hoặc `de_xuat_nguon`**; nguồn này chỉ được lưu trong kết luận. Để nguồn `REVIEW_CHEP` nằm trong JSON seal cần sửa `sql_duyet.py`, ngoài danh sách handoff. Tôi đã dừng tại đây.

Đã sửa 2 tệp: `m4/duyet_dot.py`, `tests/test_m4_dl5b_lich_su.py`: tích hợp lũy kế Review, seal thắng, hai ca đợt đang mở, cờ DTO và test JSON kết luận.

Kiểm tra: `git diff --check` đạt; đọc JS 02C xác nhận tương thích, không sửa JS. Unittest **NOT_RUN — thiếu `python`**; chưa xác định lỗi mới so với nền. Không commit, không mở server/PG.