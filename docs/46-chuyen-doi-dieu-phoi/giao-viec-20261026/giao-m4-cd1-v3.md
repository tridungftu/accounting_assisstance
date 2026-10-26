# M4-CD1 vòng 3: hai điểm nên sửa bắt buộc trước khi lead chạy dữ liệu thật (review vòng 2 Đạt)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở PostgreSQL. Không xóa file.
- **Không mở** thư mục dữ liệu Review thật.
- Làm trong worktree hiện tại, nhánh `lat/m4-cd1` (30b5010 + merge hợp nhất).

**Việc trong `tools/chuyen_review_sqlite_sang_pg.py`:**
1. **`KeyboardInterrupt` / `BaseException`:**
   - Nhánh ngoài cùng (khoảng dòng 359) đang là `except Exception`, nên Ctrl+C vẫn in traceback. Nếu Ctrl+C rơi lúc driver đang rollback sau một lỗi, traceback xâu chuỗi có thể in DETAIL chứa giá trị dữ liệu.
   - Thêm nhánh `except KeyboardInterrupt`: in mã ASCII `M4_REVIEW_CHUYEN_DUNG` ra stderr, `return 130`.
   - Các `BaseException` khác: xử lý như lỗi chung, không traceback.
2. **Cảnh báo của logger `psycopg`:**
   - `Connection.__exit__` của psycopg tự `logger.warning(... self, exc2)` ra stderr, lộ host, user, tên CSDL và nội dung lỗi.
   - Ngay đầu `main`: gắn `logging.NullHandler()` và đặt `propagate = False` cho logger `"psycopg"` (và logger con nếu cần).
   - Không đổi cấu hình logging toàn cục khác.

**Test `tests/test_chuyen_review_pg.py`:**
- Driver giả ném `KeyboardInterrupt` trong lúc ghi, sau một lỗi driver có chuỗi `DETAIL: BI_MAT_DEMO_456`: mã thoát 130; không `Traceback`; không `BI_MAT_DEMO_456`.
- Logger `psycopg` ghi warning thì không có gì ra stderr.
- Ca cp1252 có sẵn: thêm `driver.connect.assert_called_once()`.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_chuyen_review_pg`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `tools/chuyen_review_sqlite_sang_pg.py`, `tests/test_chuyen_review_pg.py`.

**Báo cáo (≤ 3 dòng)**, thông điệp commit `[M4-CD1] vòng 3: …`.
