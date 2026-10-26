# M9-2a: M9 · Vốn vay & đầu tư tài chính (kho hợp đồng vay), chỉ mục từ khóa có trích dẫn (phần thuần của M9-2, CD-015)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh/lead".
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file.
- **Không gọi AI nào**, không mạng, không thêm thư viện ngoài. Không có chuỗi `api.anthropic.com`, `api.openai.com`, `mask` trong mã M9.
- Làm trong worktree hiện tại, nhánh `lat/m9-2a`, dựng từ hợp nhất (đã có M9-1a/1b: `m9/tai_lieu_vay.py` với `doc_docx`, `cat_doan`).

**Căn cứ:**
- Thiết kế `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M9-KHO-HOP-DONG-VAY-HOI-DAP-20261026.md` §1, §2, §5.
- CD-015:
  - trả lời có trích dẫn file · trang · điều/khoản · câu nguyên văn;
  - không tìm thấy căn cứ → "không thấy trong hợp đồng";
  - chỉ Local AI (phần vector để lát sau).

**Việc: tệp mới `src/kho_tri_thuc/m9/chi_muc_vay.py`.**
1. `chuan_hoa(chu: str) -> list[str]`: tách từ tiếng Việt cho tìm kiếm.
   - Thường hóa, bỏ dấu (giữ `đ` → `d`), tách theo ký tự không phải chữ/số.
   - Giữ nguyên số tiền/ngày/tỷ lệ thành một token (`1.000.000.000`, `01.02.2026`, `8,5%` → `8,5`).
2. Lớp `ChiMucVay`.
   - `them(tai_lieu_id: str, ten_tep: str, doan_cat: list[dict])`: nhận kết quả `cat_doan`. Mỗi **câu** là một đơn vị tìm kiếm, mang theo `tai_lieu_id`, `ten_tep`, `trang_dau`/`trang_cuoi`, `dieu`, `khoan`, `diem`, `ma_doan`, câu nguyên văn.
   - `xoa(tai_lieu_id)`: bỏ toàn bộ câu của tài liệu (dùng khi có phiên bản mới).
   - `tim(cau_hoi: str, *, so_ket_qua=5, loc_tai_lieu: set[str] | None = None) -> list[dict]`:
     - xếp hạng BM25 tự cài (k1=1.2, b=0.75), có cộng điểm nhỏ khi khớp cụm hai từ liền nhau;
     - kết quả có `diem` và `trich_dan` = `{ten_tep, trang, dieu, khoan, diem, cau}`;
     - **không** sửa câu nguyên văn.
   - Không có kết quả vượt ngưỡng tối thiểu → trả `[]`.
   - Bên gọi hiển thị "Không thấy trong hợp đồng"; hằng `KHONG_THAY = "Không thấy trong hợp đồng."` đặt trong module.
3. `to_dict()` / `from_dict()` để lưu và nạp lại chỉ mục (JSON thuần, ổn định thứ tự), chưa ghi đĩa.
4. Không trả lời bằng số, không tổng hợp. Lát này chỉ tìm và trích.

**Test, tệp mới `tests/test_m9_chi_muc_vay.py`** (dựng DOCX giả **DEMO** bằng `zipfile` như `tests/test_m9_tai_lieu_vay.py`, hoặc dựng thẳng danh sách đoạn):
- Hỏi "lãi suất cho vay" (không dấu và có dấu) → câu ở Điều về lãi suất đứng đầu, trích dẫn đúng trang/điều/khoản.
- Hỏi "phí trả nợ trước hạn" → đúng khoản.
- Hỏi chủ đề không có trong tài liệu → `[]`.
- `loc_tai_lieu` chỉ trả câu của tài liệu được chọn.
- `xoa` xong không còn câu của tài liệu đó.
- `to_dict`/`from_dict` vòng tròn cho kết quả giống hệt.
- Câu trích dẫn trùng **nguyên văn** với câu trong `cat_doan`.
- Token số tiền `1.000.000.000` tìm được.
- Grep: thư mục `src/kho_tri_thuc/m9` không chứa `api.anthropic.com`, `api.openai.com`, `mask`.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_chi_muc_vay tests.test_m9_tai_lieu_vay`, PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m9/chi_muc_vay.py`, `tests/test_m9_chi_muc_vay.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M9-2a] …`.
