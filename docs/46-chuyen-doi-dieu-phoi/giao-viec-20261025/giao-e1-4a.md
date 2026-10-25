# E1-4a — E1-MUA · lệnh sửa danh mục tham số theo loại + nhật ký (trong bản vá engine #6)

Bạn là worker Codex, chạy không tương tác. Anh đã chốt (20/10: kế toán tổng hợp sửa danh mục, **không cần CFO duyệt**; 25/10 QD-20261025-11: sửa trong bản vá trong repo): **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/e1-4a` (từ hop-nhat, đã có E1-1/E1-2/E1-3). Sandbox không ghi `.git`: **không commit**. Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`.

**Căn cứ:** `docs/GIAO-CODE-E1-MUA-DANH-MUC-THAM-SO-THEO-LOAI.md` §4 dòng ~39 ("Màn hình danh mục (nếu #6 có web) **hoặc lệnh `python -m trich_xuat danh-muc sua …`** — kế toán tổng hợp sửa dòng → `save_catalog` + nhật ký") và dòng ~40 (test nhật ký sửa danh mục).
**Dùng lại:** sổ danh mục theo loại `tools/source6_g5_e5/trich_xuat/danh_muc.py` (E1-1: `danh_muc_theo_loai`, phiên bản danh mục), quy tắc `logic.py` (E1-2), điểm vào CLI hiện có của gói `trich_xuat` trong bản vá (tìm `__main__`/argparse; nếu chưa có thì thêm tối thiểu). **Không** viết sổ danh mục mới.

**Việc:**
1. Lệnh `python -m trich_xuat danh-muc xem <loai>` (in bảng tham số của loại, tiếng Việt) và `danh-muc sua <loai> <ma_tham_so> --truong <ten> --gia-tri <...> --nguoi <ten> --ly-do <...>`: kiểm loại/mã/trường hợp lệ (loại lạ, mã lạ, trường không được sửa → lỗi tiếng Việt, mã thoát ≠ 0, không ghi gì); lưu bằng hàm lưu danh mục hiện có (`save_catalog` hoặc tương đương) **tăng phiên bản danh mục**; ghi **nhật ký** dạng JSON Lines cạnh tệp danh mục (thời điểm, người, lý do, loại, mã, trường, giá trị cũ → mới, phiên bản cũ → mới). Ghi nguyên tử (tệp tạm + đổi tên); lỗi giữa chừng không để danh mục nửa vời.
2. Loại **XD không sửa được qua lệnh này** (giữ nguyên hàm gốc — 9 đầu vào trùng hàm gốc theo E1-2) → báo lỗi rõ.
3. Test `tests/test_e1_mua_danh_muc_sua.py` (thư mục tạm, danh mục giả DEMO): sửa hợp lệ → phiên bản tăng + 1 dòng nhật ký đúng nội dung; loại/mã/trường lạ → không đổi tệp; XD bị từ chối; lỗi ghi giữa chừng (mock) → danh mục cũ còn nguyên.

**File được sửa/tạo (≤ 4):** `tools/source6_g5_e5/trich_xuat/danh_muc.py`, điểm vào CLI trong `tools/source6_g5_e5/trich_xuat/` (vd `__main__.py`), `tests/test_e1_mua_danh_muc_sua.py` (mới).
**Không làm:** màn hình web, áp vào engine #6 thật, đọc hợp đồng thật/`DAP_AN_*.xlsx`, gọi AI/cloud, xóa file.
**Test phải đạt:** `--module test_e1_mua_danh_muc_sua --module test_e1_mua_danh_muc --module test_e1_mua_quy_tac --module test_e1_mua_bang --module test_source6_g5_e5` — không mã lỗi mới so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json`.
**Báo cáo cuối (≤ ½ trang):** cú pháp lệnh + ví dụ · định dạng dòng nhật ký · test · file đã sửa · thông điệp commit `[E1-4a] …`.
