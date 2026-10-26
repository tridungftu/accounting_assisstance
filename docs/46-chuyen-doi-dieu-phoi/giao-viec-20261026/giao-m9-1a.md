# M9-1a: M9 · Vốn vay & đầu tư tài chính (kho hợp đồng vay), đọc tài liệu và cắt đoạn theo điều/khoản (CD-015, phần thuần của M9-1/M9-2)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh/lead".
- Đọc `AGENTS.md`, `CLAUDE.md` (dòng M9 và Cổng AI). Ghi tệp UTF-8 không BOM.
- **Không commit**. Không mở server. Không xóa file.
- **Không** thêm thư viện ngoài: chỉ thư viện chuẩn, đọc DOCX bằng `zipfile` + `xml.etree`.
- **Không gọi AI nào**, kể cả Local; lát này thuần.
- **Không** có chuỗi `api.anthropic.com`, `api.openai.com`, `mask` trong mã M9.
- Làm trong worktree hiện tại, nhánh `lat/m9-1a`, dựng từ hợp nhất.

**Căn cứ:**
- Thiết kế `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M9-KHO-HOP-DONG-VAY-HOI-DAP-20261026.md` §1, §2, §5.
- `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` mục CD-015:
  - hỏi đáp có trích dẫn file · trang · điều/khoản · câu nguyên văn;
  - chỉ Local AI.
- OCR bản scan: kết quả ABBYY Hot Folder là **DOCX** (xem docstring `m4/review_goc/trich_xuat/ocr_abbyy.py`, chỉ đọc, **không** import, **không** sửa). Lát này nhận DOCX (gốc hoặc DOCX do OCR trả); việc gọi Hot Folder để lát sau.

**Việc: gói mới `src/kho_tri_thuc/m9/`** (`__init__.py` rỗng + `tai_lieu_vay.py`).
1. `doc_docx(raw: bytes) -> list[dict]`: danh sách đoạn văn theo thứ tự.
   - Mỗi đoạn có `trang` (đếm từ ngắt trang tường minh `w:br w:type="page"` và `w:lastRenderedPageBreak`, bắt đầu 1), `thu_tu`, `van_ban` (giữ nguyên chữ, chỉ chuẩn hóa khoảng trắng thừa).
   - Bảng (`w:tbl`): đọc từng ô theo hàng, đánh dấu `la_bang=True`.
   - Không phải DOCX hợp lệ → `DataError` (`ha_tang.primitives`) mã `M9_TAI_LIEU_KHONG_DOC_DUOC`, câu tiếng Việt, không lộ đường dẫn.
2. `cat_doan(doan: list[dict]) -> list[dict]`: cắt theo cấu trúc hợp đồng tín dụng Việt Nam.
   - Nhận diện cấp: `Chương …`, `Điều N.` / `ĐIỀU N:`, khoản `N.` / `N.N` / `Khoản N`, điểm `a)` / `a.`.
   - Mỗi đoạn kết quả có:
     - `dieu` (số + tiêu đề), `khoan`, `diem` (None khi không có);
     - `trang_dau`, `trang_cuoi`;
     - `cau` (tách câu theo dấu chấm/chấm phẩy cuối câu, giữ nguyên văn để trích dẫn; không tách số tiền dạng `1.000.000` hay ngày `01.02.2026`);
     - `ma_doan` ổn định (hash từ vị trí + nội dung).
   - Văn bản trước Điều 1 → phần `MO_DAU`.
3. `nhan_thong_tin(raw, *, ten_tep, loai_tai_lieu)` → `{sha256, so_trang, so_doan, loai_tai_lieu}`.
   - `loai_tai_lieu` thuộc danh mục: `HD_TIN_DUNG`, `KHE_UOC_NHAN_NO`, `PHU_LUC`, `HD_BAO_DAM`, `THONG_BAO_LAI_SUAT`; khác → lỗi.
   - Không lưu file ở lát này.
4. Không đoán số tiền hay lãi suất; chỉ cắt và giữ nguyên văn.

**Test, tệp mới `tests/test_m9_tai_lieu_vay.py`:**
- Dựng DOCX giả **DEMO** trong test bằng `zipfile`, không thêm fixture nhị phân. Nội dung:
  - mở đầu, Điều 1, Điều 2 có khoản và điểm;
  - một bảng;
  - một ngắt trang;
  - câu chứa số tiền `1.000.000.000 VND` và ngày `01.02.2026`.
- Kiểm:
  - trang đúng;
  - điều/khoản/điểm đúng;
  - câu không bị cắt ở số tiền/ngày;
  - `ma_doan` ổn định giữa hai lần chạy;
  - DOCX hỏng → mã lỗi;
  - loại tài liệu lạ → lỗi.
- Grep trong test: thư mục `src/kho_tri_thuc/m9` không chứa `api.anthropic.com`, `api.openai.com`, `mask`.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_tai_lieu_vay`, PYTHONPATH=`src;.;tests`.

**Tệp (3):** `m9/__init__.py`, `m9/tai_lieu_vay.py`, `tests/test_m9_tai_lieu_vay.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M9-1a] …`.
