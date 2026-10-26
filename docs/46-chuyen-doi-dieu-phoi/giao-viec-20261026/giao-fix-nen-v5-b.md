# FIX-NEN-V5 vòng b: test OCR M9 chạy đúng dưới guard "không xóa tệp" của runner kiểm thử (chỉ sửa test)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. Không commit. Không xóa file.
- **Chỉ sửa `tests/test_m9_ocr_hot_folder.py`.** Không sửa `m9/ocr_hot_folder.py`; nếu cần sửa mã nguồn thì dừng, ghi "Cần lead".
- Làm trong worktree hiện tại, nhánh `lat/fix-nen-v5` (HEAD 48fdab7).

**Bối cảnh (lead đã xác minh):**
- Chạy bằng Python thường: 21/21 đạt.
- Chạy bằng runner kiểm thử của lead: **25 FAIL**. Runner là `tools/chay_test_theo_module.py`, dùng runtime `var\app-runtime\…\Python313` có module `codex_no_delete_guard` và đặt `CODEX_NO_DELETE_FILES=1`.
  - Ví dụ `test_cac_dinh_dang_anh_tinh_mot_trang`: `self.assertEqual(self._trang(), 5)` ra `0 != 5`.
- Guard chỉ nạp cho tiến trình kiểm thử, không áp vào phần mềm thật. Nó làm ba việc:
  - biến các hàm xóa tệp và xóa cây thư mục thành **giữ lại tệp**;
  - đổi `TEMP`/`TMP` và thư mục tạm của `tempfile` sang `var\codex-dieu-phoi\retained-temp`;
  - không xóa thư mục tạm.
- Hệ quả: tệp, đệm, sổ trang của ca trước còn lại. Ca sau lấy kết quả từ đệm nên đếm 0 trang. Các khẳng định "thư mục in/out/tam sạch" sai.

**Việc:**
1. Mỗi ca dùng **thư mục gốc mới, tên duy nhất** cho Hot Folder, dữ liệu, sổ trang và đệm, ví dụ `tempfile.mkdtemp(prefix=...)` cộng uuid.
   - Không dùng lại đường dẫn giữa các ca.
   - Không dựa vào việc tệp của ca trước đã bị xóa.
2. Khẳng định "đã dọn / không còn tệp" chỉ chạy khi **không** chạy dưới guard. Cách kiểm: `os.environ.get("CODEX_NO_DELETE_FILES","").strip().lower() in ("1","true","yes","on")`.
   - Dưới guard: thay bằng khẳng định yếu hơn nhưng vẫn có ý nghĩa (tệp kết quả trả đúng; tệp của mã khác không bị đụng), hoặc `skipTest` riêng cho phần kiểm dọn kèm lý do "guard giữ tệp của runner kiểm thử".
   - Làm theo mẫu `tests/test_m4_review_compute.py`, khoảng dòng 451.
3. Giữ nguyên các ý định khác: đệm SHA, hạn mức, hủy, quá giờ, định dạng, không lộ đường dẫn, đồng bộ bằng Event.

**Tự kiểm (nếu sandbox cho chạy Python):**
- Chạy thường: `python -X utf8 -m unittest tests.test_m9_ocr_hot_folder`.
- Chạy mô phỏng guard: đặt biến môi trường trên, đồng thời patch các hàm xóa tệp/thư mục thành không làm gì.
- Cả hai cách đều phải đạt.

Báo cáo ≤ 5 dòng. Thông điệp commit `[FIX-NEN-V5] vòng b: …`.
