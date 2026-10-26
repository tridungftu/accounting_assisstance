# M9-2b: M9 · Vốn vay & đầu tư tài chính (kho hợp đồng vay), soạn câu trả lời hỏi đáp có trích dẫn qua cổng AI, **chỉ Local** (CD-015)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn (không trả lời bằng số) và ghi "Cần Anh/lead".
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file.
- **Không gọi AI thật hay mạng trong test**: dùng cổng giả.
- Không có chuỗi `api.anthropic.com`, `api.openai.com`, `mask` trong `src/kho_tri_thuc/m9/`.
- Làm trong worktree hiện tại, nhánh `lat/m9-2b`, dựng từ hợp nhất.

**Căn cứ:**
- CD-015 (`docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`):
  - chỉ Local AI cho hỏi đáp, **không Cloud kể cả qua Mask**;
  - trả lời có trích dẫn file · trang · điều/khoản · câu nguyên văn;
  - không trích dẫn được thì không trả lời bằng số;
  - tiền luôn kèm đơn vị.
- Cổng AI dùng chung `src/kho_tri_thuc/tri_thuc/cong_ai.py`: `LOAI_VIEC`, `LoaiViec(ma, mo_ta, duoc_dung_cloud, nguong_tin_cay)`, `YeuCauAI`, `KetQuaAI`, `TruongAI`, lớp `CongAI`. Đọc docstring đầu tệp và hàm `danh_gia` (kiểm trích dẫn nguyên văn).
- Thiết kế M9 §1, §5: `D:\Claude\Phan mem ho tro ke toan\THIET-KE-MODULE-DE-CHOT-2026-10-20\M9-KHO-HOP-DONG-VAY-HOI-DAP-20261026.md`.

**Việc:**
1. `tri_thuc/cong_ai.py`: thêm **một** dòng `LoaiViec("HOI_DAP_VAY", "Hỏi đáp hợp đồng vay có trích dẫn (M9 · Vốn vay & đầu tư tài chính) — chỉ Local AI", False, 0.80)`. Không sửa gì khác trong tệp.
2. Tệp mới `src/kho_tri_thuc/m9/hoi_dap_vay.py`, hàm `tra_loi(cau_hoi: str, trich_dan: list[dict], *, cong_ai) -> dict`.
   - `trich_dan` là danh sách kết quả tìm kiếm, mỗi phần tử có `ten_tep`, `trang`, `dieu`, `khoan`, `diem`, `cau` (đúng shape `trich_dan` của M9-2a, lát song song). **Không** import M9-2a.
   - **Không có trích dẫn** → `{"trang_thai": "KHONG_THAY", "tra_loi": "Không thấy trong hợp đồng.", "trich_dan": []}`, **không** gọi cổng.
   - Có trích dẫn:
     - dựng `YeuCauAI(loai_viec="HOI_DAP_VAY", van_ban=<các câu đánh số [1]..[n], nguyên văn>, chi_dan=<yêu cầu trả lời ngắn bằng tiếng Việt, chỉ dựa vào các câu, trích lại câu nguyên văn>, truong=("tra_loi",))`;
     - gọi `cong_ai` qua phương thức công khai mà `CongAI` dùng cho một yêu cầu (đọc mã để xác định tên);
     - **kiểm thêm** trước khi trả, ngoài kiểm của cổng:
       - (a) câu trích của trường `tra_loi` phải trùng nguyên văn một câu trong `trich_dan`;
       - (b) mọi số trong câu trả lời (tiền, tỷ lệ %, ngày, kỳ hạn) phải xuất hiện nguyên văn trong câu trích được dẫn;
       - (c) số tiền phải có đơn vị (VND/USD/đồng) trong câu trả lời hoặc câu trích.
     - Hỏng (a) hoặc (b) → `{"trang_thai": "CHI_TRICH_DAN", "tra_loi": None, "trich_dan": [...]}`: chỉ đưa câu trích, không câu trả lời.
     - Đạt → `{"trang_thai": "CO_TRA_LOI", "tra_loi": ..., "trich_dan": [câu được dẫn trước, các câu khác sau], "muc": "VANG"}`.
   - Không lưu câu hỏi hay câu trả lời ra đĩa; nhật ký do cổng ghi (không có nội dung).
   - Không tự tính dư nợ hay lãi.
3. Docstring ghi rõ: số dư/lãi suất hiện hành lấy từ snapshot Sheet ở M9-3, không lấy từ câu trả lời AI.

**Test, tệp mới `tests/test_m9_hoi_dap_vay.py`** (cổng giả trả `KetQuaAI` dựng sẵn; có test dùng `CongAI` thật với Local giả, nếu dựng được bằng tiêm phụ thuộc như `tests/test_ai4a_kiem_xac_suat.py`):
- `HOI_DAP_VAY` có `duoc_dung_cloud is False`.
- Bật công tắc Cloud trong cài đặt + Local "không chắc" → **vẫn không** gọi Mask hay Cloud (dùng `CongAI` với provider/Mask giả ghi nhận lần gọi).
- Không trích dẫn → `KHONG_THAY`, cổng không bị gọi.
- Câu trả lời có số không có trong câu trích (ví dụ "lãi suất 9%" khi câu trích ghi "8,5%/năm") → `CHI_TRICH_DAN`.
- Câu trích không trùng nguyên văn → `CHI_TRICH_DAN`.
- Trả lời đúng → `CO_TRA_LOI`, câu được dẫn đứng đầu.
- Grep: `m9/` không chứa `api.anthropic.com`, `api.openai.com`, `mask`.
- Test cổng AI hiện có vẫn đạt: `tests.test_ai4a_kiem_xac_suat`, cùng các test `test_cong_ai*` nếu có.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_m9_hoi_dap_vay tests.test_ai4a_kiem_xac_suat`, PYTHONPATH=`src;.;tests`.

**Tệp (3):** `tri_thuc/cong_ai.py` (một dòng), `m9/hoi_dap_vay.py`, `tests/test_m9_hoi_dap_vay.py`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[M9-2b] …`.
