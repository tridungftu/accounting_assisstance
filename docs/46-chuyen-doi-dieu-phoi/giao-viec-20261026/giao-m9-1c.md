# M9-1c: M9 · Vốn vay & đầu tư tài chính (kho hợp đồng vay), bộ nối OCR ABBYY Hot Folder cho bản scan (CD-015 mục 6)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh/lead".
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file người dùng.
- **Không** chạy ABBYY thật, không đụng thư mục Hot Folder thật: test dùng thư mục tạm và một luồng giả lập ABBYY.
- Không gọi AI. Không mạng. Không thêm thư viện ngoài.
- Làm trong worktree hiện tại, nhánh `lat/m9-1c`, dựng từ hợp nhất.

**Căn cứ:**
- CD-015 mục 6 (`docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`): "dùng lại cách ABBYY Hot Folder của phần mềm review (**chép code, không sửa bản gốc**)".
- Bản gốc đã ghim trong repo: `src/kho_tri_thuc/m4/review_goc/trich_xuat/ocr_abbyy.py`. **Chỉ đọc; không import, không sửa.** Nó phụ thuộc cấu hình/thư mục của phần mềm Review.
- Các phần cần chép và chỉnh:
  - `thu_muc` (in/out/tam/nhan);
  - `_chay_hot_folder`: ghi `tam` → `os.replace` vào `in`; chờ `out/<mã>.docx` đứng yên và là DOCX hợp lệ; nhận bằng `os.replace` sang `nhan`; hết hạn thì rút file; dọn file của mã;
  - `_docx_hop_le`;
  - đệm theo SHA;
  - sổ đếm trang (hạn mức 5.000 trang / 30 ngày).

**Việc: tệp mới `src/kho_tri_thuc/m9/ocr_hot_folder.py`.**
1. Lớp `HotFolderM9(thu_muc_goc: Path, *, thu_muc_du_lieu: Path, cho_nhan=300, cho_toi_da=1800, nghi=1.0, on_dinh=2.0)`.
   - Thư mục do bên gọi truyền (cấu hình M9 sau này), **không** dùng thư mục của Review.
   - Hàm `ocr(raw: bytes, duoi: str, *, huy: threading.Event | None = None) -> bytes` trả DOCX.
   - Chỉ nhận `pdf`, `jpg`, `jpeg`, `png`, `tif`, `tiff`.
2. Đệm kết quả theo **SHA256** của tệp vào: cùng tệp thì không đưa vào ABBYY lần hai.
3. Sổ đếm trang của M9:
   - Đếm trang PDF bằng cách đọc `/Type /Page` đơn giản như bản gốc; ảnh = 1 trang.
   - Vượt 5.000 trang / 30 ngày → lỗi `M9_OCR_HET_HAN_MUC` **trước khi** đưa file vào.
   - Ghi trong docstring: hạn mức giấy phép ABBYY dùng chung với phần mềm Review nhưng hai sổ đếm tách nhau. "Cần Anh": có gộp sổ đếm không.
4. Lỗi bằng `DataError` mã `M9_OCR_*` (`KHONG_NHAN`, `QUA_GIO`, `LOI_ABBYY`, `HUY`, `DINH_DANG`), câu tiếng Việt trung tính.
   - **Không** đưa đường dẫn thư mục hay nội dung tài liệu vào thông điệp lỗi hoặc log.
   - Hết hạn hoặc hủy thì rút file khỏi `in` nếu ABBYY chưa nhận.
5. Một khóa (`threading.Lock`) cho mỗi thư mục gốc: mỗi lúc chỉ một tài liệu trong Hot Folder, như bản gốc.

**Test, tệp mới `tests/test_m9_ocr_hot_folder.py`** (thư mục tạm; luồng giả lập ABBYY: thấy file ở `in` → xóa → ghi DOCX hợp lệ vào `out` theo từng phần rồi dừng):
- Thành công trả đúng DOCX; `in`/`out`/`tam` sạch sau khi xong.
- Gọi lại cùng tệp → lấy từ đệm, luồng giả không thấy file mới.
- ABBYY không nhận trong `cho_nhan` → `M9_OCR_KHONG_NHAN`, file đã được rút.
- Quá `cho_toi_da` → `M9_OCR_QUA_GIO`.
- `huy.set()` → `M9_OCR_HUY`.
- File đang ghi dở (kích thước đổi) chưa bị nhận.
- Vượt hạn mức → lỗi trước khi ghi vào `in`.
- Định dạng lạ → `M9_OCR_DINH_DANG`.
- Thông điệp lỗi không chứa đường dẫn thư mục tạm.
- Dùng thời gian chờ ngắn (`nghi` 0.05, `on_dinh` 0.1, `cho_nhan` 1) để cả bộ dưới 20 giây.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_ocr_hot_folder`, PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m9/ocr_hot_folder.py`, `tests/test_m9_ocr_hot_folder.py`.

**Báo cáo (≤ ¼ trang)**, "Cần Anh", thông điệp commit `[M9-1c] …`.
