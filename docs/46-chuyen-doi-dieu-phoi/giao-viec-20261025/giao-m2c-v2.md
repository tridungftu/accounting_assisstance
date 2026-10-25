# M2c — sửa vòng 2 (chỉ các điểm lead chọn từ review vòng 1)

Bạn là worker Codex, chạy không tương tác. Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/m2c` (commit `6022ef9` là bản vòng 1 của bạn). Sandbox không ghi `.git`: **không commit**. Nếu không chạy được Python, ghi rõ (lead chạy test).
Nguyên tắc dự án: **thà bỏ sót còn hơn nhập sai** — khi nghi ngờ thì giữ chờ / ngoại lệ, không khai đủ.
**Chỉ sửa 4 điểm sau trong `src/kho_tri_thuc/m2/tai_hoa_don/nhan.py` và thêm test vào `tests/test_m2_00_nhan_tinh.py`. Không sửa SQL, `k2/hoa_don.py`, file khác.**

1. **Độ phủ đầu vào (`nhan.py` ~202):** manifest có trạng thái run khác `COMPLETE` (vd `FAILED` có `loi_chung`, `PARTIAL`, `KHONG_YEU_CAU`) KHÔNG được ra `coverage = COMPLETE_INPUT`. `COMPLETE` → `COMPLETE_INPUT`; còn lại → `PARTIAL_INPUT` kèm mã lý do (`FAILED` giữ các mục đọc được nhưng gắn cờ). Test: manifest `FAILED` còn mục → `PARTIAL_INPUT`.
2. **Lỗi theo mục không dừng cả run (`nhan.py` ~224–249):** DataError của một mục (ví dụ `M2_MANIFEST_IDENTITY_KHAC`, `CAPTURE_KHAC_NOI_DUNG`) chỉ đưa mục đó vào trạng thái `GIU_CHO_K2` kèm mã + thông báo, rồi chạy tiếp các mục sau; kết quả cuối có danh sách mục bị giữ. Lỗi cấp run (manifest hỏng, hash lệch) vẫn dừng như cũ. Test: 2 mục, mục 1 lỗi → mục 2 vẫn nhận, mục 1 có trong danh sách giữ chờ.
3. **`KHONG_XML_GOC` không có bảng kê (`nhan.py` ~166):** chỉ gán `bang_chung = "BANG_KE"` khi manifest có bảng kê hợp lệ (đã kiểm hash ở M2b); thiếu bảng kê (`bang_ke` None / trạng thái `KHONG_YEU_CAU`/`LOI`) → ngoại lệ `BANG_KE_THIEU`, không gán mức bằng chứng. Test cả hai nhánh.
4. **Số hóa đơn có số 0 đầu (`nhan.py` ~180):** so khớp `SHDon` giữa XML và manifest theo dạng chuẩn hóa (bỏ số 0 đầu, giống K2), vẫn giữ nguyên bản thô trong `key_raw`. Test: manifest `1`, XML `000001` → không ngoại lệ; khác số thật → vẫn ngoại lệ `IDENTITY_XML_MANIFEST_KHAC`.

**Test phải đạt:** `python -X utf8 tools/chay_test_theo_module.py . --module test_m2_00_nhan_tinh --module "test_m2_00*"`.
**Báo cáo cuối (≤ ½ trang):** 4 điểm đã sửa (file:dòng) · test thêm · test đạt/tổng (hoặc "chưa chạy được") · thông điệp commit `[M2c] vòng 2: …`.
