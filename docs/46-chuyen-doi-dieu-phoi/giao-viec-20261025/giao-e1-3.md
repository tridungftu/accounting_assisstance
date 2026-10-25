# E1-3 — E1-MUA · Tham số dạng bảng (E3): TT-05 bảng hàng/đơn giá, TT-20 lịch/kỳ — trong bản vá engine #6

Bạn là worker Codex, chạy không tương tác. Anh đã chốt (20/10 thiết kế; 25/10 QD-20261025-11 **sửa trong bản vá trong repo**) qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/e1-3` (hop-nhat, đã có E1-1, E1-2). Sandbox không ghi `.git`: **không commit**. Chạy Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`.

**Căn cứ:** TL 44 `D:\Claude\Phan mem ho tro ke toan\44-bo-tham-so-hop-dong-mua-theo-loai.md` dòng ~14, ~56, ~60, ~96–102 (TT-05 = bảng hàng hóa/đơn giá cho MUA_HH, NHAP_KHAU; đơn giá kỳ cho DV_KY, THUE_TS; TT-20 = lịch/kỳ thanh toán); `docs/GIAO-CODE-E1-MUA-DANH-MUC-THAM-SO-THEO-LOAI.md` §2, §4 (test "bảng TT-05/TT-20 đọc đúng số dòng từ fixture **giả**"). **Không mở `DAP_AN_DV_nhap_20261020.xlsx`** (giá trị thật, kể cả sheet `TT-05_bang`).
**Dùng lại:** bản vá đọc bảng DOCX `tools/source6_docx_tables/` (`doc_hop_dong.py`, `quy_trinh.py`) — đọc cách nó trích bảng DOCX hiện nay; sổ danh mục theo loại `tools/source6_g5_e5/trich_xuat/danh_muc.py` (E1-1); quy tắc theo loại `tools/source6_g5_e5/trich_xuat/logic.py` (E1-2). Không viết bộ đọc DOCX mới.
**Việc cụ thể:**
1. Với loại có TT-05 dạng bảng (MUA_HH, NHAP_KHAU; DV_KY, THUE_TS đơn giá kỳ) và TT-20 dạng lịch: nhận diện bảng trong DOCX theo tiêu đề cột (tên hàng/mã, ĐVT, số lượng, đơn giá, thành tiền; đợt/kỳ, tỷ lệ/số tiền, hạn) và trả về **danh sách dòng có cấu trúc** (giữ nguyên chuỗi gốc + giá trị đã chuẩn hóa nếu chắc chắn; không chắc → để trống + cờ cần rà soát; không suy diễn).
2. Kết quả trích của loại đó có thêm `bang` (TT-05, TT-20) cạnh giá trị đơn; loại XD **không đổi** (bằng chứng: kết quả XD trước/sau trùng trên các fixture hiện có).
3. Fixture **giả** mới: 1–2 DOCX nhỏ tự tạo trong test (dùng zipfile tạo document.xml tối thiểu, tên/hàng hóa có chữ DEMO) có bảng hàng 5 dòng và bảng lịch 3 đợt.
4. Test mới `tests/test_e1_mua_bang.py`: đọc đúng số dòng/cột; ô trống/gộp ô → cờ rà soát, không đoán; XD không đổi.
**File được sửa/tạo (≤ 5):** `tools/source6_docx_tables/doc_hop_dong.py` và/hoặc `quy_trinh.py`, `tools/source6_g5_e5/trich_xuat/quy_trinh.py` chỉ nếu cần nối kết quả, `tests/test_e1_mua_bang.py` (mới).
**Không làm:** sinh nghĩa vụ M1/M2 từ bảng, so hóa đơn, màn hình, áp vào #6 thật, gọi AI/cloud, đọc hợp đồng thật, xóa file.
**Test phải đạt:** `--module test_e1_mua_bang --module test_e1_mua_quy_tac --module test_e1_mua_danh_muc --module test_source6_docx_tables --module test_source6_g5_e5` — không mã lỗi mới so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json`.
**Báo cáo cuối (≤ 1 trang):** cấu trúc `bang` trả về (ví dụ JSON ngắn) · cách nhận diện bảng · XD không đổi (bằng chứng) · test đạt/tổng · thông điệp commit `[E1-3] …` · `[CẦN ANH XÁC NHẬN]` nếu có.
