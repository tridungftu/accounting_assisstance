# M9-4b: M9 · Vốn vay & đầu tư tài chính, điền cột "điều khoản liên quan tới đàm phán" của báo cáo lãi suất bằng trích dẫn hợp đồng (thuần, QD-20261026-07)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi tệp UTF-8 không BOM. Không commit. Không mạng, không AI, không thư viện ngoài. Không xóa file.
- Chỗ chưa rõ: dừng, ghi "Cần lead".
- Làm trong worktree hiện tại, nhánh `lat/m9-4b`, dựng từ hợp nhất. Đã có:
  - `m9/bao_cao_lai_suat.py`: cột `dieu_khoan_lien_quan_toi_dam_phan` đang để trống, ghi chú "chờ nối trích dẫn hợp đồng (M9-2)";
  - `m9/chi_muc_vay.py`: `ChiMucVay.tim` có `loc_tai_lieu`.

**Căn cứ:** thiết kế M9 §4: điều khoản liên quan tới đàm phán (biên độ, điều chỉnh lãi, phí trả nợ trước hạn) trích từ hợp đồng **kèm trích dẫn**.

**Việc** (`m9/bao_cao_lai_suat.py`):
1. Thêm tham số tùy chọn cho `lap_bao_cao`:
   - `chi_muc=None`;
   - `tai_lieu_theo_khoan_vay: dict[str, set[str]] | None` (mã khoản vay → tập `tai_lieu_id`). Ánh xạ này do bên gọi cấp; lưu trữ làm sau.
2. Có cả hai tham số thì với mỗi khoản vay chạy **3 truy vấn cố định**, lọc theo tài liệu của đúng khoản vay đó:
   - "biên độ lãi suất";
   - "điều chỉnh lãi suất";
   - "phí trả nợ trước hạn".

   Mỗi truy vấn lấy tối đa 1 câu. Điền danh sách `{chu_de, ten_tep, trang, dieu, khoan, cau}`.
   - Không tìm thấy → chủ đề đó ghi "Không thấy trong hợp đồng".
   - **Không** sửa câu, **không** suy số.
3. Không có `chi_muc` hoặc ánh xạ → giữ **nguyên** hành vi cũ (cột trống + ghi chú cũ), để test M9-4a hiện có vẫn đạt.
4. `xuat_excel`: cột điều khoản ghi gọn từng chủ đề "Chủ đề: câu (tệp, trang, Điều/Khoản)". Văn bản thuần, không công thức.

**Test** (thêm vào `tests/test_m9_bao_cao_lai_suat.py`; chỉ mục DEMO dựng trong test):
- Khoản vay có hợp đồng chứa đủ 3 chủ đề → điền đúng câu nguyên văn và trích dẫn.
- Khoản vay không có chủ đề "phí trả nợ trước hạn" → "Không thấy trong hợp đồng" cho chủ đề đó.
- Câu của tài liệu khoản vay khác **không** lọt sang.
- Không truyền chỉ mục → kết quả giống hệt trước (so với ca cũ).
- Excel đọc lại có cột điều khoản đúng, không công thức.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_bao_cao_lai_suat tests.test_m9_chi_muc_vay`, PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m9/bao_cao_lai_suat.py`, `tests/test_m9_bao_cao_lai_suat.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M9-4b] …`.
