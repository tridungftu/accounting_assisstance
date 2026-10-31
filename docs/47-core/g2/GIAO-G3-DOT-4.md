# G3 · đợt 4 (sau mốc N) — OCR-2, TRICH-3a, HD-2a; G2-31a

**Phần chung:**
- như `GIAO-G2-DOT-A.md`, mục "Phần chung";
- bảng dùng lại / bọc / sửa / viết mới (CD-036) theo `docs\47-core\engine\GIAO-ENGINE-1.md` / `GIAO-ENGINE-2.md`;
- quy tắc manifest: `engine.json` chỉ khai capability **đã có bộ chuyển đổi + test trong chính lát**, schema G2-17b;
- dùng khung G2-21 / SDK engine G2-20 như OCR-4a / AI-4a đã gộp (`engines\e_ocr\chay.py`, `engines\e_hoi_ai\chay.py`);
- không gọi ABBYY / AI / portal thuế / Chromium thật;
- dữ liệu DEMO;
- không sửa nguồn ngoài repo (`D:\GPT\OCR`, review_xaydung, bộ tải hóa đơn): chỉ đọc / bọc.

## OCR-2 · `e_ocr` — văn bản có vị trí / nguồn từ ABBYY → DOCX
**Tệp:**
- `src\kho_tri_thuc\engines\e_ocr\van_ban.py`
- `src\kho_tri_thuc\engines\e_ocr\engine.json`
- `tests\test_g3_ocr_2.py`

**Việc:**
- bọc `HotFolderClient.convert` và `extract_docx` (nguồn gốc theo GIAO-ENGINE-1 phần `e_ocr`; dùng bản trong repo `ha_tang\cong_ocr.py` nếu đã bọc);
- không import `app.py`, không hiệu đính / OCR ảnh nhúng khác;
- ra `van_ban_tai_lieu.v1`.
- **Manifest:** capability văn bản OCR, `headless=false` + `ngoai_le_man_hinh` `CD-038-ENGINE-3A` (ABBYY).

**Test:** HotFolder giả trả DOCX DEMO → văn bản có vị trí / nguồn đúng contract; manifest đạt schema.

## TRICH-3a · `e_trich_xuat` — manifest + khung tiến trình giả lập
**Tệp:**
- `src\kho_tri_thuc\engines\e_trich_xuat\engine.json`
- `src\kho_tri_thuc\engines\e_trich_xuat\chay.py`
- `tests\test_g3_trich_3a.py`

**Việc:**
- khung chạy theo mẫu `e_ocr\chay.py` (chờ ACK, giữ kết quả chưa ACK, không thoát khi drain);
- dùng `docx.py` / `tham_so.py` (TRICH-1a) với AI giả;
- manifest chỉ khai capability đã có test (đọc DOCX + ánh xạ 37 tham số); **không** ready capability chưa đạt.

## HD-2a · `e_hoa_don` — tải hóa đơn với portal giả
**Tệp:**
- `src\kho_tri_thuc\engines\e_hoa_don\tai.py`
- `tests\test_g3_hd_2a.py`

**Việc:** theo GIAO-ENGINE-2 mục HD-2a:
- chờ đăng nhập giả;
- PARTIAL / coverage; bàn giao / dedupe;
- kỳ trọn tháng, tháng nhuận / đổi năm.
- Không Chromium, không thuế thật.
- Dùng `doc.py` (HD-1) để đọc kết quả.

Báo cáo mỗi lát ≤ 3 dòng.
