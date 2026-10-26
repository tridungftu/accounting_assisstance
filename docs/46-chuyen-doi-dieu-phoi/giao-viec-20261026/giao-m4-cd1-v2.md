# M4-CD1 vòng 2: công cụ chuyển Review, sửa điểm Chặn (lộ bí mật qua traceback) và chính sách HĐ mồ côi (lead chốt)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở PostgreSQL. Không xóa file.
- **TUYỆT ĐỐI không mở** thư mục dữ liệu Review thật. Chỉ dùng SQLite giả trong thư mục tạm.
- Làm trong worktree hiện tại, nhánh `lat/m4-cd1` (ada4108).
- Không sửa DL2/DL3.

**1. Chặn — lộ bí mật qua traceback** (`tools/chuyen_review_sqlite_sang_pg.py` dòng ~322 `emit`, ~350–353):
- Khi stdout không phải UTF-8 (ví dụ `cp1252`), `print` ở nhánh `except` ném `UnicodeEncodeError`, và Python in traceback **kèm exception gốc**. Exception gốc có thể chứa đoạn DSN hoặc mật khẩu từ thông báo libpq.
- Sửa:
  - `emit` dùng `ensure_ascii=True`;
  - nhánh `except` ngoài cùng **không bao giờ** để lọt traceback: bắt mọi lỗi in ra, thoát bằng mã khác 0, chỉ in mã lỗi ASCII.
  - Không in `repr(exc)`/`str(exc)` của lỗi từ driver.
- Thêm test:
  - chạy `main` với stdout là `io.TextIOWrapper(io.BytesIO(), encoding="cp1252")`, cùng driver giả ném lỗi có chuỗi `invalid percent-encoded token: "BI_MAT_DEMO_123"`;
  - kiểm: mã thoát khác 0, stderr và stdout **không** có `Traceback`, **không** có `BI_MAT_DEMO_123`.

**2. Chính sách HĐ mồ côi (lead chốt):**
- Bảng `canh_bao` và `nhat_ky` của Review giữ `ma_hd` của HĐ đã xóa (`_xoa_hd` của vendor).
- **Chỉ đòi ánh xạ cho `ma_hd` có trong bảng `hop_dong`** của lần chụp. Dòng mồ côi: lưu `hop_dong_id`/`du_an_id` = NULL như hiện tại, không đòi ánh xạ.
- Báo cáo thêm **số dòng mồ côi theo từng bảng** (chỉ số đếm).
- Thêm ca DEMO: có `nhat_ky` với `ma_hd` không còn trong `hop_dong` → chạy được, đếm mồ côi đúng.

**3. Báo cáo lỗi:** với `DataError` mã `M4_REVIEW_*`, thêm trường `bang` (tên bảng/cột lấy từ hằng, **không** giá trị dữ liệu).

**4. Ghi SHA256 tệp nguồn vào `mo_ta`** của lần chụp (DL2 đã có tham số), để truy vết.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_chuyen_review_pg`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `tools/chuyen_review_sqlite_sang_pg.py`, `tests/test_chuyen_review_pg.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M4-CD1] vòng 2: …`.
