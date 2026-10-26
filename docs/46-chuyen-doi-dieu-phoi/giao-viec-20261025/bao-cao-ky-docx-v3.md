Anh, đã sửa 6 file, UTF-8 không BOM:

- `tests/test_crm_ky_ket_http.py:628`: k10 chấp nhận hai trạng thái; kéo `thu_lai_sau` về quá khứ trong giao dịch trước khi nhận việc; giữ kiểm tra một sự kiện.
- `tests/test_crm_ky_docx.py:29`, `tests/test_crm_ky_ket_http.py:232`: chuyển kiểm tra sang M0036, bổ sung ghim byte M0001–M0035. Cập nhật chú thích tại `tests/test_crm_ky_ket.py:12`, `tests/test_crm_giao_ket_http.py:9`.
- `crm_g.js:1128`, `tests/crm_giao_ket_async.cjs:272`: dùng nhãn “PDF xuất tay…” từ `LY_DO_PDF`, thêm assert không kèm mã.

Test: Python **45 đạt/74**, 27 skip, 2 lỗi ghim byte do migration trong worktree là CRLF. Ghim khớp bản LF trong Git. Node giao kết **23/23**, ký **14/14** đạt.

Chưa chạy PG; không sửa migration, không commit.

Thông điệp commit: `[KY-DOCX] vòng 3: sửa test đua k10, cập nhật M0036 và nhãn PDF xuất tay`