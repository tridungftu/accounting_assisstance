# M9-1b: M9 · Vốn vay & đầu tư tài chính (kho hợp đồng vay), sửa 3 điểm sau lead kiểm M9-1a

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file.
- Không gọi AI. Không thêm thư viện ngoài.
- Làm trong worktree hiện tại, nhánh `lat/m9-1b`, dựng từ hợp nhất (đã có M9-1a: `src/kho_tri_thuc/m9/tai_lieu_vay.py`).

**Việc** (`m9/tai_lieu_vay.py`):
1. **Đếm trang đôi.** Word ghi `w:lastRenderedPageBreak` ở đầu trang mới, kể cả trang mới do ngắt trang tường minh `w:br w:type="page"` tạo ra. Hiện mã tăng `trang` cho cả hai, nên trích dẫn lệch trang.
   - Sửa: một `lastRenderedPageBreak` đứng ngay sau một ngắt trang tường minh, chưa có chữ nào ở giữa (kể cả qua ranh giới đoạn/run), là **cùng một** ngắt trang.
   - Hai `lastRenderedPageBreak` liên tiếp không có chữ ở giữa cũng chỉ tính một.
2. **Câu báo lỗi trung tính** cho người dùng (không xưng "Anh"): "Không đọc được tài liệu. Hãy tải lên tệp Word (.docx) hợp lệ."
3. **Nhận "Điều N" không có dấu câu sau số.** Ví dụ "Điều 5 Lãi suất cho vay", "ĐIỀU 5 LÃI SUẤT".
   - Chỉ nhận khi ngay sau số là khoảng trắng rồi một chữ cái viết hoa.
   - Không nhận câu thường như "Điều 5 của hợp đồng này…" (chữ thường sau số).
   - Áp tương tự cho "Chương".

**Test** (`tests/test_m9_tai_lieu_vay.py`, thêm ca; không thêm fixture nhị phân):
- DOCX giả có `w:br w:type="page"` rồi đoạn sau bắt đầu bằng `w:lastRenderedPageBreak` → chỉ tăng 1 trang.
- Hai `lastRenderedPageBreak` liền nhau → tăng 1.
- `lastRenderedPageBreak` đứng một mình (không có ngắt tường minh trước) → vẫn tăng 1.
- Câu lỗi không chứa "Anh".
- "Điều 5 Lãi suất cho vay" là đầu điều; "Điều 5 của hợp đồng này quy định" không phải.
- 14 ca cũ vẫn đạt.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_tai_lieu_vay`, PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m9/tai_lieu_vay.py`, `tests/test_m9_tai_lieu_vay.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M9-1b] …`.
