# M9-2c: M9 · Vốn vay & đầu tư tài chính, nối tìm kiếm + hỏi đáp thành một luồng, có nhật ký câu hỏi (thuần, QD-20261026-07)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi tệp UTF-8 không BOM. Không commit. Không mạng, không AI thật (dùng cổng giả), không thư viện ngoài. Không xóa file.
- Chỗ chưa rõ: dừng, ghi "Cần lead".
- Làm trong worktree hiện tại, nhánh `lat/m9-2c`, dựng từ hợp nhất. Đã có:
  - `m9/chi_muc_vay.py` (`ChiMucVay.tim` trả `trich_dan`);
  - `m9/hoi_dap_vay.py` (`tra_loi(cau_hoi, trich_dan, *, cong_ai)`, chỉ Local);
  - `m9/tai_lieu_vay.py`.

**Căn cứ:**
- Thiết kế M9 §5.3: nhật ký mọi câu hỏi (ai, lúc nào, câu hỏi; **không** lưu nội dung trả lời ra ngoài máy).
- CD-015: chỉ Local AI, có trích dẫn, không trích dẫn được thì không trả lời bằng số.

**Việc: tệp mới `src/kho_tri_thuc/m9/dich_vu_hoi_dap.py`.**
1. Hàm `hoi(cau_hoi, *, chi_muc, cong_ai, nguoi_hoi: str, loc_tai_lieu=None, so_ket_qua=5, ghi_nhat_ky) -> dict`.
   - Gọi `chi_muc.tim(...)` rồi `hoi_dap_vay.tra_loi(...)`, trả đúng kết quả của `tra_loi` (`KHONG_THAY` / `CHI_TRICH_DAN` / `CO_TRA_LOI`).
   - `ghi_nhat_ky` là callable do bên gọi cấp; tầng lưu (CSDL) làm sau khi Anh duyệt phiếu cổng A.
   - Mỗi lượt gọi `ghi_nhat_ky` **một lần**, với `{nguoi_hoi, luc (giờ VN, ISO), cau_hoi, trang_thai, so_trich_dan, ma_doan_trich_dan:[...]}`. **Không** có câu trả lời hay nội dung câu trích.
2. Câu hỏi rỗng hoặc chỉ khoảng trắng → `{"trang_thai": "KHONG_THAY", ...}`, không gọi cổng; vẫn ghi nhật ký với `trang_thai` tương ứng.
3. `loc_tai_lieu` truyền thẳng xuống chỉ mục (để sau này lọc theo pháp nhân/quyền).
   - Không có `loc_tai_lieu` khi chỉ mục có nhiều pháp nhân thì vẫn chạy (lọc quyền là việc tầng gọi). Ghi rõ điều này trong docstring.

**Test, tệp mới `tests/test_m9_dich_vu_hoi_dap.py`** (DOCX DEMO dựng trong bộ nhớ hoặc danh sách đoạn; cổng AI giả trả `KetQuaAI`):
- Luồng đủ: có trích dẫn + trả lời đúng → `CO_TRA_LOI`.
- Không có trích dẫn → `KHONG_THAY`, cổng không bị gọi.
- Nhật ký đúng một lần mỗi lượt, có đủ khóa, **không** chứa chuỗi câu trả lời hay câu trích.
- `loc_tai_lieu` được truyền xuống.
- Grep `m9/` không có `api.anthropic.com`, `api.openai.com`, `mask`.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_dich_vu_hoi_dap tests.test_m9_hoi_dap_vay tests.test_m9_chi_muc_vay`, PYTHONPATH=`src;.;tests`.

**Tệp (2):** `m9/dich_vu_hoi_dap.py`, `tests/test_m9_dich_vu_hoi_dap.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[M9-2c] …`.
