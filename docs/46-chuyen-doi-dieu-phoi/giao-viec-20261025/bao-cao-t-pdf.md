Anh, đã sửa duy nhất `tests/test_crm_giao_ket_http.py`, UTF-8 không BOM; không commit.

- **Gốc:** `crm_docx.py:374–376,530,933` chuyển lỗi guard/quyền COM thành `PDF_CHUA_SAN_SANG`; `_co_word()` chỉ kiểm metadata. Không thấy cờ sản phẩm tắt Word COM. Chưa xác nhận `ly_do` của lần lỗi lead ghi nhận vì không chạy Word.
- **Điều kiện mới:** g02/g06 kiểm lý do cụ thể và giữ DOCX; `PDF_DAT` cần bằng chứng PID/Job/Word đã dừng. g07 dựa vào kết quả xuất thực tế.
- **Test:** 2/2 test thuần đạt; 11 HTTP skip. Mock xác nhận `GUARD_KHONG_NAP`, `COM_TAO_WORD:PermissionError`. Không lỗi mới trong phần đã chạy; `git diff --check` đạt.
- **Thông điệp commit đề xuất:** `[T-PDF] Sửa kỳ vọng PDF theo guard và bằng chứng Word thực tế`