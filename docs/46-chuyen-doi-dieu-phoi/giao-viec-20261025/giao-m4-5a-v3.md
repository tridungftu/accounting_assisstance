# M4-5a vòng 3 — sửa theo review Claude (A1, A2, A4, A3 phần test)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/m4-5a` (M4 · Nghiệm thu & chi phí dự án, 03B: khai một phần bằng số tiền, migration **M0033**). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không khởi động PostgreSQL/server (lead chạy ca PostgreSQL sau). Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`; nếu sandbox chặn python → ghi rõ "lead chạy test", không đoán kết quả.

**Việc (review vòng 1 Đạt; đây là các mục Nên sửa):**
1. **A1** `src/kho_tri_thuc/k2/ghi_nhan_chung.py` ~:348 (`phan_khai_con_thieu`): hiện `max(0, giá trị đợt − số khai)` che mất trường hợp khai vượt. Khi số khai > giá trị đợt → `so_tien_con_thieu = None`, `ly_do = "KHAI_VUOT_GIA_TRI_DOT"` (giống các nhánh lý do khác). Không đổi kết quả khi khai ≤ giá trị đợt.
2. **A2** cùng tệp ~:105-114 (dịch lỗi `DC_HOA_DON_DA_GAN`): locator `thanh_phan.{i}.nguon` chỉ đúng khi **lưu** (chỉ số theo danh sách gửi lên). Khi **xác nhận**, danh sách là bản gộp → dùng trường `"$"`. Thêm tham số rõ ràng cho đường gọi (không đoán theo nội dung).
3. **A4** cùng tệp ~:387 (`xep_hang_hoa_don`): tín hiệu chênh tiền đọc `TgTTTBSo` dạng `"1100000.00"` với VND đang bị từ chối → chấp nhận khi phần lẻ toàn số 0 (chỉ cho việc **đọc tín hiệu**, không nới `parse_so_tien` dùng cho ghi).
4. **A3 (test):** trong `tests/test_m4_03b_common_pg.py`, ca kiểm `app_web` không gọi được hàm nội bộ phải bao đủ 6 hàm có trong REVOKE của `k2/sql_ghi_nhan_so_tien.py` (`_dc_hd_da_gan`, `_dc_kiem_hd_da_gan`, `_dc_so_tien_hop_le`, `_dc_kiem_tien_tp`, `_dc_dot_goi_y`, `_dc_goi_y_hoa_don`). Không sửa SQL M0033.
5. Test thuần cho 1–3 trong `tests/test_m4_03b_so_tien.py`: khai vượt → cờ; khai bằng → "0"; xác nhận trùng hóa đơn → trường `"$"`, lưu trùng → `thanh_phan.{i}.nguon`; VND `"1100000.00"` đọc được, `"1100000.50"` không.

**Lưu ý:** các tệp `tests/fixtures/*` đang hiện "đã sửa" do lead đồng bộ DEMO — không đụng, không khôi phục.
**File được sửa (chỉ):** `src/kho_tri_thuc/k2/ghi_nhan_chung.py`, `tests/test_m4_03b_so_tien.py`, `tests/test_m4_03b_common_pg.py`. Không xóa file.
**Test phải đạt:** `--module test_m4_03b_so_tien --module test_m4_03b_common_tinh` (ca PG lead chạy).
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · ca test mới · thông điệp commit `[M4-5a] vòng 3: …`.
