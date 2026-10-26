# M4-CD1: M4 · Nghiệm thu & chi phí dự án, công cụ chuyển dữ liệu Review SQLite → PostgreSQL, chạy lại không trùng (CD-011, lát 7 theo kiểm kê)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md` (mục 2: **ngoại lệ CD-011** chỉ dành cho lead chạy thật). Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m4-cd1`, dựng từ `lat/m4-dl3` (đã có DL2 `m4/review_data_pg.py` và DL3 `m4/review_phu_luc_pg.py`). **Không sửa** hai tệp đó; chỉ import hàm công khai.
- **TUYỆT ĐỐI không mở, đọc hay liệt kê** `D:\Claude\Ho tro review ho so xay dung\review_xaydung\co_so_du_lieu\` hay tệp `hop_dong.db` thật. Test tự tạo **SQLite giả** (dữ liệu DEMO) trong thư mục tạm, đúng lược đồ 12 bảng.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\M4-KIEM-KE-CHEP-REVIEW.md`: §3 (12 bảng, kiểu, khóa), §5 dòng 7 · M4-CD1 (chạy lại không tăng bản ghi/trùng ID; nguồn chỉ đọc; lỗi thì dừng, không sửa tay).
- Docstring `m4/sql_review_chep.py`: lần chụp, `chup_luc`, không nạp một phần, nạp lại đối chiếu `chup_luc`, ánh xạ `ma_hd` do người chốt.
- Lược đồ SQLite nguồn lấy từ mã vendor đã có trong repo (`m4/review_goc/...`; tìm DDL `csdl_hop_dong`), **không** từ tệp DB thật.

**Việc: tệp mới `tools/chuyen_review_sqlite_sang_pg.py`, CLI.**
1. Tham số:
   - `--nguon <tệp .db>`: mở **chỉ đọc**, kiểu URI `file:...?mode=ro&immutable=1`; không tạo, không sửa.
   - `--anh-xa <tệp CSV ma_hd,hop_dong_id,du_an_id>`: do người chốt cung cấp.
   - `--dsn-tep <tệp kết nối JSON>`: đọc DSN bằng chương trình, **không in hay log DSN**.
   - `--nguon-id`, `--chup-luc` (thời điểm chụp tệp nguồn, bắt buộc).
   - `--thu`: chạy thử, chỉ báo cáo, không ghi.
2. Đọc đủ 12 bảng nguồn và gọi ghi lần chụp của DL2 và DL3 **trong một giao dịch**.
   - Thiếu ánh xạ một `ma_hd` → dừng, không ghi gì.
   - Lỗi bất kỳ → rollback, mã thoát khác 0.
3. **Chạy lại:**
   - Cùng `nguon_id`, cùng dữ liệu → không tăng dòng.
   - Cùng `nguon_id` mà `chup_luc` hay dữ liệu khác → dừng, báo rõ.
4. Báo cáo kết thúc, **chỉ số đếm và tổng kiểm soát**, không in dòng dữ liệu, tên đối tác, số HĐ:
   - số dòng từng bảng đọc và ghi;
   - tổng giá trị HĐ;
   - tổng BOQ;
   - tổng từng đợt.
5. Trước khi đọc, ghi **SHA256 tệp nguồn** vào báo cáo; đọc xong kiểm lại SHA256 không đổi.

**Test, tệp mới `tests/test_chuyen_review_pg.py`:**
- Phần thuần: tạo SQLite giả 12 bảng; nguồn mở chỉ đọc (thử ghi thì lỗi); SHA256 trước và sau như nhau; thiếu ánh xạ thì dừng; `--thu` không ghi; báo cáo không chứa chuỗi dữ liệu mẫu (tên giả).
- Phần PG (`skipUnless KHO_PG_DSN_TEST`; CSDL `kho_test_*` riêng, dựng HĐ DEMO như test DL2):
  - nạp lần 1 thì số đếm khớp nguồn;
  - chạy lại không tăng;
  - đổi `chup_luc` cùng `nguon_id` thì dừng;
  - lỗi giữa chừng thì không còn dòng nào.
- Chạy thuần: `python -X utf8 -m unittest tests.test_chuyen_review_pg`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `tools/chuyen_review_sqlite_sang_pg.py`, `tests/test_chuyen_review_pg.py`.

**Báo cáo (≤ ¼ trang):** số test, phần "Cần Anh", thông điệp commit `[M4-CD1] …`.
