# M4-CD2: M4 · Nghiệm thu & chi phí dự án, đối chiếu độc lập sau khi nạp dữ liệu Review (CD-011, lát 8 theo kiểm kê)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở PostgreSQL. Không xóa file.
- Test PG tự tạo CSDL `kho_test_*` từ DSN quản trị; không đọc `KHO_PG_DEMO_*`.
- **TUYỆT ĐỐI không mở** thư mục dữ liệu Review thật; test dùng SQLite giả.
- Làm trong worktree hiện tại, nhánh `lat/m4-cd2`, dựng từ hợp nhất (đã có CD1 `tools/chuyen_review_sqlite_sang_pg.py`, DL2/DL3/DL4).

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\M4-KIEM-KE-CHEP-REVIEW.md` §5 dòng 8 · M4-CD2: số dòng từng bảng; tổng HĐ, tổng BOQ, từng đợt; dòng lỗi; **phát hiện lệch dù tổng chung triệt tiêu**.
- Công cụ CD1 và các repository `m4/review_*_pg.py`.

**Việc:**
1. Tệp mới `src/kho_tri_thuc/m4/review_doi_chieu.py`: đối chiếu **độc lập** giữa nguồn SQLite (mở chỉ đọc) và một lần chụp đã nạp ở PG (`nguon_id`). Không dùng chung mã chuyển đổi của CD1 để tự so chính nó.
   - Số dòng từng bảng trong 12 bảng.
   - Tổng giá trị HĐ, tổng BOQ, tổng từng đợt **theo từng HĐ và từng đợt** (không chỉ tổng chung), so chính xác bằng Decimal.
   - Danh sách khóa có ở một bên mà thiếu ở bên kia.
   - Đếm HĐ bị cờ "cần xem lại" (từ DL3).
   - Kết quả chỉ chứa số đếm, tổng và **khóa kỹ thuật dạng mã nội bộ** (`HD0001`, số đợt). **Không** in tên đối tác, số hợp đồng, nội dung.
2. `tools/chuyen_review_sqlite_sang_pg.py`: thêm tùy chọn `--doi-chieu` chạy sau khi nạp (hoặc chạy riêng với `--nguon-id` đã nạp).
   - In báo cáo ASCII an toàn như CD1, không traceback hay bí mật.
   - Mã thoát khác 0 khi có lệch.

**Test `tests/test_chuyen_review_pg.py`:**
- SQLite giả: nạp xong thì đối chiếu khớp.
- Sửa 1 dòng BOQ ở PG (trong test, qua kết nối chủ bảng, trên CSDL test) hoặc dựng nguồn khác thì phát hiện lệch đúng HĐ.
- Hai lệch triệt tiêu nhau ở tổng chung vẫn bị phát hiện ở cấp HĐ/đợt.
- Báo cáo không chứa chuỗi tên giả của dữ liệu mẫu.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_chuyen_review_pg`, với PYTHONPATH=`src;.;tests`.

**Tệp (3):** `m4/review_doi_chieu.py`, `tools/chuyen_review_sqlite_sang_pg.py`, `tests/test_chuyen_review_pg.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M4-CD2] …`.
