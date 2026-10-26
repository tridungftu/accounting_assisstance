# OCR-1: cổng OCR dùng chung một engine ABBYY cho mọi module, sổ đếm trang chung với phần mềm Review (QD-20261026-06)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi tệp UTF-8 không BOM. Không commit. Không mở server. Không xóa file người dùng.
- **Không** đụng thư mục Hot Folder/dữ liệu thật; test dùng thư mục tạm, mỗi ca một gốc riêng như `tests/test_m9_ocr_hot_folder.py`, và chạy được dưới guard giữ tệp `CODEX_NO_DELETE_FILES`.
- **Không sửa** bản gốc Review `m4/review_goc/...` (đóng băng; chỉ đọc để lấy định dạng).
- Chỗ chưa rõ: dừng, ghi "Cần lead".
- Làm trong worktree hiện tại, nhánh `lat/ocr-1`, dựng từ hợp nhất. Đã có `m9/ocr_hot_folder.py` (lớp `HotFolderM9`) chép cách của Review.

**Quyết định Anh:** "Gộp sổ chung. Lưu ý OCR dùng chung 1 engine cho tất cả" module.
- **Một** cổng OCR dùng chung (như cổng AI) cho M4/M9/… dùng **cùng** Hot Folder ABBYY và **cùng** sổ đếm trang với phần mềm Review.
- Hạn mức giấy phép chung 5.000 trang / 30 ngày.

**Việc:**
1. Tệp mới `src/kho_tri_thuc/ha_tang/cong_ocr.py`: chuyển lõi `HotFolderM9` thành `CongOCR` dùng chung, không gắn tên module. Cấu hình nhận từ bên gọi:
   - thư mục gốc Hot Folder (in/out/tam/nhan) — trỏ đúng thư mục Hot Folder mà phần mềm Review đang dùng;
   - **đường dẫn sổ đếm trang dùng chung** = tệp `ocr_abbyy/so_trang.json` trong thư mục dữ liệu của Review;
   - thư mục đệm riêng của phần mềm này.
2. **Sổ đếm trang:** đọc/ghi **đúng định dạng của Review** (danh sách `[thời điểm epoch, số trang]`, xem `m4/review_goc/trich_xuat/ocr_abbyy.py` hàm `so_trang_da_dung`/`_ghi_so`; chỉ đọc mã đó, không import).
   - Ghi có **khóa tệp liên tiến trình** (tệp `.lock` cạnh sổ, `msvcrt.locking` trên Windows), đọc–cộng–ghi trong cùng khóa.
   - Ghi qua tệp tạm rồi thay thế để không làm hỏng sổ của Review.
   - Kiểm hạn mức trên **tổng chung**, trước khi đưa tệp vào.
3. **Mã việc** theo đúng mẫu của Review `hd%Y%m%d%H%M%S_<6 hex ngẫu nhiên>`, để màn kiểm tra của Review không coi là tệp lạ.
   - Mỗi tiến trình chỉ nhận/dọn tệp đúng mã của mình (như Review).
   - Một khóa liên tiến trình cho thư mục `in` để mỗi lúc chỉ một tài liệu vào Hot Folder, kể cả khi Review cùng chạy. Khóa của Review chỉ là khóa trong tiến trình; ghi "Cần lead" nếu thấy rủi ro chen hàng.
4. `m9/ocr_hot_folder.py` thành lớp mỏng gọi `CongOCR`, giữ API `HotFolderM9.ocr(...)` và mã lỗi `M9_OCR_*` để test M9 hiện có vẫn đạt.
5. Không ghi nội dung tài liệu/đường dẫn vào log hay thông điệp lỗi.

**Test, tệp mới `tests/test_cong_ocr.py`:**
- Sổ chung: hai tiến trình (`multiprocessing`) cùng ghi sổ → tổng trang đúng, không mất bản ghi.
- Sổ có sẵn bản ghi kiểu Review → cộng đúng, vượt hạn mức chung thì chặn trước khi đưa tệp.
- Bản ghi quá 30 ngày không tính.
- Mã việc khớp mẫu Review.
- Không đụng tệp mã khác.
- `tests/test_m9_ocr_hot_folder.py` vẫn đạt; không sửa tệp này, trừ khi bắt buộc thì ghi lý do.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_cong_ocr tests.test_m9_ocr_hot_folder`, PYTHONPATH=`src;.;tests`.

**Tệp (3):** `ha_tang/cong_ocr.py` (mới), `m9/ocr_hot_folder.py`, `tests/test_cong_ocr.py` (mới).

**Báo cáo (≤ ¼ trang)**, "Cần lead". Thông điệp commit `[OCR-1] …`.
