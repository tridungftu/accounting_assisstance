# E1-4b — E1-MUA · danh mục đã sửa được máy trích dùng + dọn tệp tạm (bản vá engine #6)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/e1-4b` (từ hop-nhat, đã có E1-4a `7d483bf`). Sandbox không ghi `.git`: **không commit**. Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`.

**Hiện trạng:** E1-4a thêm `python -m trich_xuat danh-muc xem|sua` trong `tools/source6_g5_e5/trich_xuat/` (`danh_muc.py`: `save_catalog(..., su_kien=)`, `sua_danh_muc`, `danh_muc_theo_loai` đã chấp nhận SHA theo chuỗi nhật ký `*.nhat_ky.jsonl`). Hai điểm còn lại (worker E1-4a + lead đọc diff):
1. `save_catalog` luôn tạo tệp tạm `rollback` (bản sao danh mục cũ) nhưng **không dọn khi lưu thành công** → mỗi lần sửa để lại một tệp `.tmp` cạnh danh mục.
2. `quy_trinh.py` (đường trích của engine) **vẫn kiểm SHA ghim gốc** → sau khi sửa danh mục, lượt trích từ chối hoặc không dùng phiên bản mới.

**Việc:**
1. `danh_muc.py`: sau khi thay danh mục + nhật ký thành công thì dọn tệp tạm hoàn tác do chính lần lưu tạo (chỉ đúng đường dẫn tệp tạm vừa tạo, tên khớp tiền tố + `.tmp`); lỗi giữa chừng vẫn giữ tệp để chẩn đoán như hiện nay.
2. `quy_trinh.py` (trong `tools/source6_g5_e5/trich_xuat/`): lấy danh mục **qua `danh_muc_theo_loai`** (đã kiểm chuỗi nhật ký) thay vì so SHA ghim gốc riêng; kết quả trích ghi **phiên bản danh mục đã dùng** (SHA hiện hành). Loại XD giữ đúng hành vi cũ (kết quả XD trước/sau trùng trên fixture hiện có — bằng chứng).
3. Test (thư mục tạm, danh mục giả DEMO): sửa danh mục một loại không phải XD → lượt trích dùng phiên bản mới và ghi đúng SHA; nhật ký bị sửa tay (chuỗi gãy) → lượt trích từ chối với lỗi tiếng Việt; lưu thành công không để lại `.tmp`; XD không đổi.

**File được sửa/tạo (≤ 4):** `tools/source6_g5_e5/trich_xuat/danh_muc.py`, `tools/source6_g5_e5/trich_xuat/quy_trinh.py`, `tests/test_e1_mua_danh_muc_sua.py` (thêm ca), có thể một test mới `tests/test_e1_mua_trich_phien_ban.py`.
**Không làm:** áp vào engine #6 thật, đọc hợp đồng thật/`DAP_AN_*.xlsx`, AI/cloud, xóa file ngoài tệp tạm do chính code tạo.
**Test phải đạt:** `--module test_e1_mua_danh_muc_sua --module test_e1_mua_danh_muc --module test_e1_mua_quy_tac --module test_e1_mua_bang --module test_source6_g5_e5 --module test_source6_docx_tables` — không mã lỗi mới so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json`.
**Báo cáo cuối (≤ ½ trang):** sửa ở file:dòng · bằng chứng XD không đổi · test · thông điệp commit `[E1-4b] …`.
