# T-WORD — Test không tự mở Word qua COM trừ khi bật rõ ràng (ràng buộc cứng CLAUDE.md §2 "không Word COM")

Bạn là worker Codex, chạy không tương tác. Lead quyết (sự cố KY-DOCX 25/10: lớp test `WordThat` tự chạy trên máy có Word → tiến trình con mở Word qua COM). **Làm ngay, không hỏi lại.** Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/t-word` (từ `lat/t-pdf` = KY-DOCX). Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL, **không chạy bất kỳ test nào có thể gọi Word** (chỉ chạy sau khi đã sửa cổng bật).

**Việc:**
1. `tests/test_crm_giao_ket.py`: hàm `_co_word()` (~:1089) trả `False` (kèm lý do) **trừ khi** biến môi trường `KHO_TEST_WORD_THAT == "1"`; kiểm biến môi trường **trước** mọi kiểm khác (không gọi `R._winword_ok`, không tìm module, không dựng tiến trình con khi chưa bật). Mọi lớp/ca dùng Word thật (`WordThat`, ca `--word-control`, `_chuyen_pdf_mot` với `WINWORD_GHIM`, `WordSoHuu` thật) đều đi qua `_co_word()`/`skipUnless` tương ứng — rà toàn tệp, ca nào gọi Word thật mà chưa qua cổng thì thêm cổng. Lý do skip tiếng Việt: "Chỉ chạy khi bật KHO_TEST_WORD_THAT=1 (không tự mở Word COM)".
2. `tests/test_crm_doi_chieu_pg.py` (~:41, :126) dùng `_co_word` → giữ nguyên cách gọi (tự hưởng cổng mới); chỉ sửa nếu có chỗ gọi Word thật không qua `_co_word`.
3. Thêm 1 ca tĩnh trong `tests/test_crm_giao_ket.py`: khi không có biến môi trường, `_co_word()` là `False` và không gọi `R._winword_ok` (giả lập/patch để chứng minh).
**File (≤ 2):** `tests/test_crm_giao_ket.py`, `tests/test_crm_doi_chieu_pg.py` (chỉ khi cần). Không đổi mã sản phẩm. Không xóa file.
**Chạy test (sau khi sửa, KHÔNG đặt biến môi trường):** `python -X utf8 -m unittest tests.test_crm_giao_ket` — ghi số đạt/skip; xác nhận lớp Word thật đều skip.
**Báo cáo (≤ ⅓ trang):** sửa ở file:dòng · số test · thông điệp commit `[T-WORD] …`.
