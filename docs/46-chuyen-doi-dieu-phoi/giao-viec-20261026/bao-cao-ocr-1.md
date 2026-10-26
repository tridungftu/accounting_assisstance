Anh, đã triển khai OCR-1 trên `lat/ocr-1`, chưa commit.

- **Đã làm:** `CongOCR` dùng sổ Review hai cột, khóa liên tiến trình cho sổ và `in`, ghi atomic, gộp trước replace, kiểm sau ghi và khôi phục tối đa một lần. Giữ API/mã lỗi M9, dùng mã `hd…`.
- **File đổi:** [cong_ocr.py](src/kho_tri_thuc/ha_tang/cong_ocr.py), [ocr_hot_folder.py](src/kho_tri_thuc/m9/ocr_hot_folder.py), [test_cong_ocr.py](tests/test_cong_ocr.py), [test_m9_ocr_hot_folder.py](tests/test_m9_ocr_hot_folder.py).
- **Kiểm tra:** `git diff --check` đạt; cả 4 tệp UTF-8 không BOM. Test **NOT_RUN** vì không có Python; gồm 20 ca mới và 21 ca M9. Chưa xác định lỗi mới so với nền.
- **Rủi ro:** Review chưa tham gia khóa; đã ghi giới hạn bảo đảm trong docstring, hết khi chuyển hẳn sang M4 ở cổng B.

**Cần lead:** chạy `python -X utf8 -m unittest tests.test_cong_ocr tests.test_m9_ocr_hot_folder` với `PYTHONPATH=src;.;tests`, rồi chạy thêm với `CODEX_NO_DELETE_FILES=1`.