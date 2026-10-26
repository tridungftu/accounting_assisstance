# MTQ-2d: Ma trận thẩm quyền, điểm nên sửa của review MTQ-2c/3b1 và trường "là Admin" cho màn hình

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-2d`, dựng từ hợp nhất (đã gộp MTQ-2c, MTQ-3b1).
- Không sửa SQL hay migration (`k2/sql_ma_tran_tham_quyen.py`, `pg_migrations.py`).

**Việc:**
1. **Lỗi trùng hoặc khóa ngoại không được hiện mã kỹ thuật.**
   - Các ca: cấp vai cho người đã có vai ở phòng đó, cấp Admin cho người đã là Admin, trùng mã phòng, phạm vi trùng, pháp nhân hoặc người dùng không tồn tại.
   - Trong `k2/ma_tran_tham_quyen.py` (`_quan_tri` khoảng dòng 385, hoặc `_write`): kiểm trùng bản hiện hành **dưới khóa đang giữ**, hoặc bắt SQLSTATE 23505/23503. Đổi sang mã riêng:
     - `MTQ_DA_CAP` → 409, "Đã cấp trước đó; tải lại để xem bản hiện hành.";
     - `MTQ_KHONG_THAY` → 400, "Pháp nhân, phòng hoặc người dùng không tồn tại.".
   - Ghi `mtq_tu_choi` như các từ chối khác.
2. **Tách nghĩa `MTQ_DANH_TINH`:** khi người **được cấp** không còn hoạt động, dùng mã riêng `MTQ_NGUOI_NHAN_NGUNG` → 400, "Người được cấp không còn hoạt động.". `MTQ_DANH_TINH` 403 chỉ dành cho người thao tác.
3. **Câu theo mã đúng ngữ cảnh** (`giao_dien/ma_tran_tham_quyen.py` khoảng dòng 65):
   - Thu hồi vai hay Admin với revision cũ → "Dữ liệu đã thay đổi; tải lại trước khi thao tác.", không nói "bản nháp".
   - GET `ma-tran` của người không phải Admin giữ gợi ý "xem Quyền của tôi".
   - `MTQ_PHAM_VI` khi phòng ngừng hoạt động → câu riêng.
4. **Trường "là Admin" cho màn hình:** GET `cua-toi` trả thêm `la_admin: true|false`, tính từ SQL theo danh tính phiên (bảng Admin còn hiệu lực). Màn hình (MTQ-3b2) dùng trường này để chọn màn Admin hay "Quyền của tôi"; không đoán ở trình duyệt.
5. Sửa ghi chú báo cáo cũ: "khôi phục" ghép được từ `NHAP` (sao chép từ bản đã công bố) + `CONG_BO`. **Không** thêm route `khoi-phuc` ở lát này; chỉ ghi vào docstring module là việc để sau.
6. Lưu `ly_do` của `mtq_tu_choi`: câu chính của SQL (không chứa dữ liệu hồ sơ) thay vì chỉ lặp mã.

**Test:**
- `tests/test_mtq_dich_vu.py`: các mã mới (409/400 kèm câu), `la_admin` đúng cho Admin và người khác, câu theo ngữ cảnh.
- `tests/test_mtq_http_dispatch.py`: **test âm CSRF** — POST/GET `/api/tham-quyen/*` thiếu token hoặc Origin lạ → 403, module **không** được gọi lần nào.
- Phần PG chạy qua SQL thật (`skipUnless KHO_PG_DSN_TEST`).

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_dich_vu tests.test_mtq_http_dispatch tests.test_mtq_sql`, với PYTHONPATH=`src;.;tests`.

**Tệp (≤ 4):** `k2/ma_tran_tham_quyen.py`, `giao_dien/ma_tran_tham_quyen.py`, `tests/test_mtq_dich_vu.py`, `tests/test_mtq_http_dispatch.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[MTQ-2d] …`.
