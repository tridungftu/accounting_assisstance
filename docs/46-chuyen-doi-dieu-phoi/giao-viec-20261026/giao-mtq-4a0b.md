# MTQ-4a0b: cổng SQL ma trận, test không phụ thuộc kiểu xuống dòng khi checkout + 2 điểm nên sửa của review vòng 2

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM; `pg_migrations.py` giữ LF. **Không commit**. Không mở PostgreSQL. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-4a0b`, dựng từ hợp nhất. M0041 = `M0041_MTQ_CONG` đã phát hành: **không sửa hằng `MTQ_CONG_SQL`**.

**1. Test dễ vỡ.**
- `tests/test_mtq_cong_sql.py` khẳng định `b"\r\n"` không có trong byte của `src/kho_tri_thuc/k2/sql_mtq_cong.py`.
- Tệp này không có thuộc tính `eol`, nên bản checkout CRLF (thư mục chính, worktree khác) luôn đỏ.
- Sửa:
  - chỉ kiểm LF/BOM với `ha_tang/pg_migrations.py` (có `eol=lf`);
  - với `sql_mtq_cong.py`, kiểm **nội dung hằng SQL** (ví dụ hash `"\x00".join(MTQ_CONG_SQL)` hoặc kiểm cấu trúc), không kiểm byte tệp.
- Không nới kiểm bảo mật nào.

**2. Nên sửa — chống trùng nhật ký từ chối** (`sql_mtq_cong.py` khoảng dòng 121–123):
- Hiện cùng `request_id` thì trả `id` cũ dù người, hành động hay đối tượng khác.
- Vì M0041 đã phát hành, **thêm hằng SQL mới** `MTQ_CONG_B_SQL` trong cùng tệp, tạo lại hàm `master.mtq_ghi_tu_choi_phien` (`CREATE OR REPLACE`, giữ nguyên chữ ký, quyền và `search_path`): cùng `request_id` mà người, hành động hoặc đối tượng khác thì **báo lỗi**, không trả `id` cũ.
- Thêm index `request_id` cho `nhat_ky.mtq_tu_choi` nếu chưa có.
- Append migration tên tạm `M00xx_MTQ_CONG_B`, dấu `# MTQ-4a0b — CD-012:`.

**3. Nên sửa — test quyền** (`tests/test_mtq_cong_sql.py` khoảng dòng 191–199):
- Khẳng định có ít nhất 1 vai trong danh sách được kiểm, hoặc kiểm thêm `PUBLIC` không có EXECUTE, để test không đạt khống khi cụm thiếu vai.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_cong_sql tests.test_mtq_sql`, với PYTHONPATH=`src;.;tests`.

**Tệp (3):** `k2/sql_mtq_cong.py`, `ha_tang/pg_migrations.py`, `tests/test_mtq_cong_sql.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[MTQ-4a0b] …`.
