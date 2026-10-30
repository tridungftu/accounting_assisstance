# G3 · đợt 1 — HD-1 và TRICH-1a (giao sớm phần thư viện thuần)

**Quyết định lead 31/10 01:15:**
- Kế hoạch (`KE-HOACH-LAT-G2-G3.md` §G3) ghi mọi lát engine phụ thuộc mốc N (G2-17 + G2-20 + G2-21).
- HD-1 và TRICH-1a chỉ **bọc thư viện đọc / ánh xạ** hiện có, không dùng SDK engine, khung tiến trình, cổng hay CSDL.
- Vì vậy giao sớm để tận dụng suất Codex. Phần nối SDK / khung chạy vẫn chờ N (HD-3a, TRICH-3a).

**Phần chung:**
- như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung", và `docs\47-core\engine\GIAO-ENGINE-2.md` (bảng "dùng lại nguyên / bọc / sửa / viết mới" bắt buộc theo CD-036);
- **không sửa nguồn ngoài repo**; không gọi COM / Word / OCR / Cloud / cổng thuế;
- dữ liệu thử chỉ DEMO.

## HD-1 · `e_hoa_don` — bọc parser XML / ZIP sang contract hóa đơn

**Tệp:**
- `src\kho_tri_thuc\engines\e_hoa_don\doc.py`
- `tests\test_g3_hd_1.py`

**Căn cứ:**
- `GIAO-ENGINE-2.md` phần `e_hoa_don` (dòng ~117–190): bảng dùng lại, mục 1 HD-1;
- dùng lại nguyên lõi `src\kho_tri_thuc\nguon\hoa_don_xml.py` (quanh :618, :1183, :1191) và wrapper `src\kho_tri_thuc\ha_tang\engine_hoa_don.py:109`;
- contract `hoa_don_da_nhan.v1` / `hoa_don.v1` ở `docs\47-core\g1\CONTRACT-NGHIEP-VU.md` và contract kỹ thuật G2-17.

**Việc:**
- bọc, không viết lại parser;
- ra dữ liệu đúng contract;
- Decimal, giữ ID và số 0 đầu, hash, context;
- phần báo cáo ZIP thiếu schema: giữ chờ, không tự thêm vỏ JSON.

**Test:**
- XML hỏng / profile lạ / ZIP CRC sai / trùng entry / partial → lỗi có mã;
- giữ nguyên test parser cũ (chạy lại không đổi);
- ví dụ DEMO đạt schema.

## TRICH-1a · `e_trich_xuat` — bọc đọc DOCX và ánh xạ 37 tham số bằng AI giả

**Tệp:**
- `src\kho_tri_thuc\engines\e_trich_xuat\docx.py`
- `src\kho_tri_thuc\engines\e_trich_xuat\tham_so.py`
- `tests\test_g3_trich_1a.py`

**Căn cứ:** `GIAO-ENGINE-2.md` phần `e_trich_xuat` (dòng ~10–110; mục 1 TRICH-1a; OPUS-5). Nguồn là phần `trich_xuat` của review xây dựng. Bản trong repo: `src\kho_tri_thuc\m4\review_goc\trich_xuat\`; bản độc lập `D:\Claude\Ho tro review ho so xay dung\review_xaydung` **chỉ đọc**.

**Việc:**
- ghi nguồn + SHA256 tệp gốc trong docstring / hằng;
- đọc DOCX bằng XML Python, xử lý Track Changes; **chặn `_word` / COM**;
- ánh xạ `tham_so.v1`, đủ 37 tham số, bằng AI giả (`cloud=None`, `ai.la_cloud=False`);
- chỉ DOCX, không đi nhánh PDF / OCR riêng.

**Test:**
- DOCX DEMO có Track Changes;
- `_word` bị chặn;
- đủ 37 tham số khớp danh mục gốc;
- không gọi COM / OCR / Cloud (mock kiểm số lần gọi = 0).

Báo cáo mỗi lát ≤ 3 dòng.
