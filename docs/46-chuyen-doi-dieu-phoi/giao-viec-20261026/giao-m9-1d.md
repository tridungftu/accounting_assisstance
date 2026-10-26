# M9-1d: M9 · Vốn vay & đầu tư tài chính (kho hợp đồng vay), nhận "Điều N" / "Chương N" đứng một dòng, tiêu đề ở đoạn sau

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi UTF-8 không BOM. **Không commit**. Không mạng, không AI, không thư viện ngoài. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/m9-1d`, dựng từ hợp nhất. Đã có `m9/tai_lieu_vay.py` (M9-1a/1b), `m9/chi_muc_vay.py` (M9-2a).

**Vấn đề (lead ghi khi gộp M9-1b):** hợp đồng tín dụng hay trình bày nhãn điều riêng một đoạn, tiêu đề ở đoạn kế:
- "ĐIỀU 5" ↵ "LÃI SUẤT CHO VAY";
- "Điều 5." ↵ "Lãi suất".

Hiện `_DIEU`/`_CHUONG` đòi dấu câu, hoặc chữ hoa ngay sau số trong **cùng** đoạn. Nhãn đứng một mình không được nhận, nên các khoản của Điều 5 bị gán cho điều trước: **trích dẫn sai số điều**.

**Việc** (`m9/tai_lieu_vay.py`, hàm `cat_doan` và regex liên quan):
1. Đoạn chỉ gồm nhãn `Điều N` / `ĐIỀU N` / `Chương N|La Mã` (có hoặc không `.`/`:` ở cuối), không có chữ nào khác:
   - là đầu Điều/Chương mới;
   - tiêu đề = đoạn **không phải bảng** kế tiếp nếu đoạn đó ngắn (≤ 120 ký tự), không bắt đầu bằng nhãn khoản/điểm/điều, và không kết thúc bằng dấu chấm câu thường;
   - không thỏa thì tiêu đề rỗng, chỉ giữ số.
2. Đoạn tiêu đề đã gộp vào nhãn **không** sinh câu nội dung riêng.
3. Câu "Điều 5 của hợp đồng này…" (chữ thường sau số) vẫn **không** là đầu điều, như M9-1b.
4. Giữ `ma_doan` ổn định và các trường hiện có; không đổi shape đầu ra.

**Test** (thêm vào `tests/test_m9_tai_lieu_vay.py`, DOCX giả DEMO dựng bằng `zipfile` như các ca có sẵn):
- "ĐIỀU 5" ↵ "LÃI SUẤT CHO VAY" ↵ "5.1 Lãi suất là 8,5%/năm." → khoản 5.1 có `dieu` chứa "5" và "LÃI SUẤT CHO VAY".
- "Điều 6." ↵ "Trả nợ trước hạn" ↵ "Bên vay được trả nợ trước hạn." → điều 6, tiêu đề đúng; câu nội dung giữ nguyên văn.
- Nhãn đứng một mình, đoạn sau là "1. Nội dung …" (nhãn khoản) → tiêu đề rỗng, khoản 1 thuộc điều mới.
- Đoạn sau dài hoặc là câu thường → không lấy làm tiêu đề.
- Ca cũ M9-1a/1b vẫn đạt. `tests.test_m9_chi_muc_vay` vẫn đạt (tiêu đề làm ngữ cảnh).

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_tai_lieu_vay tests.test_m9_chi_muc_vay`, PYTHONPATH=`src;.;tests` (sandbox chặn Python thì ghi rõ).

**Tệp (2):** `m9/tai_lieu_vay.py`, `tests/test_m9_tai_lieu_vay.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M9-1d] …`.
