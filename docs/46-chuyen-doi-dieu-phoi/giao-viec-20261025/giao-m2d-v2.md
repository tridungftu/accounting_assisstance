# M2d — sửa vòng 2 (chỉ các điểm lead chọn từ review vòng 1)

Bạn là worker Codex, chạy không tương tác. Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/m2d` (commit vòng 1 của bạn là HEAD). Sandbox không ghi `.git`: **không commit**.
**Chạy test:** `python` hệ thống không dùng được trong sandbox — dùng Python đi kèm Codex: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module "test_m2_00*"` (thiếu openpyxl/psycopg thì ghi rõ test nào không chạy được; lead sẽ chạy lại bằng Python đầy đủ).

**Chỉ sửa các điểm sau** trong `src/kho_tri_thuc/m2/tai_hoa_don/manifest.py`, `hoi_cuu.py` và test tương ứng (`tests/test_m2_00_manifest_tinh.py`, `tests/test_m2_00_hoi_cuu_tinh.py`):
1. **Gốc hồi cứu tin cậy (manifest.py ~307–315, ~496; nhan.py nếu cần chỉ để truyền tham số):** `doc_manifest(...)` và `lap_ke_hoach_nhan(...)` nhận tham số tùy chọn `goc_hoi_cuu_tin_cay` (một hoặc nhiều thư mục). Khi có: manifest HOI_CUU có `thu_muc_tep_goc` không nằm trong (sau khi giải tên thật, đã kiểm reparse) một gốc tin cậy → từ chối mã `HOI_CUU_GOC_KHONG_TIN_CAY`. Khi không truyền: giữ hành vi hiện tại (để không gãy test cũ) — ghi rõ trong docstring rằng đường nhận tự động (M2e/M2f) PHẢI truyền gốc từ cấu hình. Test: gốc ngoài danh sách → từ chối; trong danh sách → nhận.
2. **Test reparse chạy được trên Windows (test manifest ~446–458):** thêm ca dùng junction (`cmd /c mklink /J`, không cần quyền quản trị) cho nhánh chặn reparse; giữ ca symlink (skip có lý do khi không tạo được).
3. **`run_id` không phụ thuộc hoa/thường đường dẫn (hoi_cuu.py ~160, ~225):** chuẩn hóa gốc bằng tên thật trên đĩa (sau khi kiểm reparse) trước khi băm; test: gọi với `d:\...` và `D:\...` (hoặc đổi hoa/thường một đoạn) → cùng `run_id`.
4. **`dem_doi_chieu` kiểm manifest đúng thư mục (hoi_cuu.py ~273–282):** `thu_muc_tep_goc` của manifest ≠ thư mục tháng đã giải → báo lỗi mã rõ, không trả số lệch. Test.
5. **Giới hạn độ dài trước khi quét giá trị cấm (manifest.py `RE_GIA_TRI_CAM`):** chuỗi dài quá ngưỡng hợp lý (vd > 4 096 ký tự) → từ chối mã `GIA_TRI_QUA_DAI` trước khi chạy regex; test chuỗi 40 000 ký tự trả lỗi nhanh (< 1 giây).
6. **Lỗi nêu đúng file (hoi_cuu.py ~57–66, 139–147):** tên file không hợp lệ / bảng kê sai cột → `locator` là tên file gây lỗi (không chỉ mã chung). Test.
**Không làm:** điểm khác của review (ghi nguyên tử, basename trong biên nhận K2, run_id dạng ngày), đọc dữ liệu thật, schema, xóa file.
**Báo cáo cuối (≤ ½ trang):** 6 điểm (file:dòng) · test thêm · test đạt/tổng (hoặc chưa chạy được) · thông điệp commit `[M2d] vòng 2: …`.
