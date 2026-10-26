# M4-DL1b vòng 3: phép kiểm byte M0038 không phụ thuộc kiểu xuống dòng khi checkout (một dòng)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở PostgreSQL. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m4-dl1b`. Các thay đổi vòng 2 đang chờ commit; giữ nguyên chúng.

**Việc:** trong `tests/test_m4_review_chep_schema.py` (khoảng dòng 201–204):
- Phép kiểm ghim sha256 phần M0038 đang đọc `SQL_PATH.read_bytes()` thô. Tệp `sql_review_chep.py` không có thuộc tính `eol`, nên bản checkout CRLF (thư mục chính, worktree khác) đỏ, còn bản LF thì đạt.
- Sửa: chuẩn hóa `b"\r\n"` thành `b"\n"` **trước** khi tách và băm. Giữ nguyên giá trị hash đã ghim (tính trên LF).
- Không đổi phép kiểm nào khác.

**Kiểm:** chạy test trên cả hai dạng xuống dòng. Chép tệp sang thư mục tạm và đổi LF thành CRLF để thử hàm chuẩn hóa; không sửa tệp nguồn thật thành CRLF.
- Chạy thuần: `python -X utf8 -m unittest tests.test_m4_review_chep_schema`, với PYTHONPATH=`src;.;tests`.

**Báo cáo (≤ 3 dòng)**, thông điệp commit `[M4-DL1b] vòng 3: …`.
