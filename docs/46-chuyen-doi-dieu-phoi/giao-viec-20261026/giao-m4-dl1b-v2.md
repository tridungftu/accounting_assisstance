# M4-DL1b vòng 2: bỏ 2 dòng kiểm ghim vị trí migration trong test, bổ sung docstring (review DL1b vòng 1)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM, giữ LF. Sandbox không ghi được `.git`: **không commit**.
- Không mở server hay PostgreSQL. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl1b` (4f11ba7).

**Việc:**
1. `tests/test_m4_review_chep_schema.py`: **bỏ** hai dòng kiểm sau, vì chúng sẽ đỏ khi có migration kế tiếp:
   - dòng ~219 `self.assertEqual(PM.PG_MIGRATIONS[idx:], (SQL_B,))`, đòi DL1b là migration cuối;
   - dòng ~212–213, ghim sha256 của cả phần đầu `pg_migrations.py`.

   Giữ nguyên các phép kiểm còn lại: `PG_MIGRATIONS[:idx] == ns["PG_MIGRATIONS"]` theo dấu, đếm đúng một lần xuất hiện, LF/BOM, M0038 không đổi byte.
2. `src/kho_tri_thuc/m4/sql_review_chep.py`: **chỉ sửa docstring**, không đổi hằng SQL nào. Thêm:
   - app_web gọi `m4.review_chep_hien_hanh` sẽ bị từ chối quyền, vì `review_chep_nguon` chỉ chủ bảng đọc. Lớp đọc (DL2) chạy bằng kết nối chủ bảng và **phải tự lọc theo quyền M4** của người gọi trước khi trả dữ liệu. Muốn mở cho app_web thì cần migration cấp SELECT `(id, chup_luc)` kèm policy, ở lát sau.
   - NULL có 3 nghĩa: chưa có lần chụp; HĐ đã xóa ở nguồn; hoặc không có quyền dự án (nếu sau này mở cho app_web). Màn hình không được hiện "đã xóa" chỉ vì nhận NULL; lớp đọc phải phân biệt.
   - Nạp lại cùng `nguon_id` phải đối chiếu `chup_luc`, vì bảng nguồn không có `dong_sha256`. Không nạp một phần theo dự án hay HĐ; gặp HĐ chưa ánh xạ thì dừng cả lần chụp.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m4_review_chep_schema`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `tests/test_m4_review_chep_schema.py`, `src/kho_tri_thuc/m4/sql_review_chep.py` (chỉ docstring).

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M4-DL1b] vòng 2: …`.
