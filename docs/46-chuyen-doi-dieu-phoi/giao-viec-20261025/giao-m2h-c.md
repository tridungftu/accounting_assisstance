# M2h-c — M2-00 · "Tải tất cả công ty": 4 điểm còn lại sau review vòng 2

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM. Worktree hiện tại, nhánh `lat/m2h-c` (từ hop-nhat, đã gộp M2h). Sandbox không ghi `.git`: **không commit**. Chạy: `node tests/m2_tai_tat_ca.cjs`; Python `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module test_m2_tai_tat_ca`. Không gọi cổng thuế thật, không mạng.

**Việc (review Claude vòng 2, `src/kho_tri_thuc/giao_dien/m2_tai_hoa_don.py` và `assets/m2_tai_hoa_don.js`):**
1. `:185` — `self._khach().config()` có thể ném `LoiKhach` khi cờ `_dang_chay` cũ và bộ tải không trả lời → bọc `try/except LoiKhach` rồi đổi thành `DataError("M2_00B_" + ma)` như `status()` (người dùng nhận thông báo tiếng Việt).
2. `:242,314` — `huy_hang_doi` và nhánh ngoại lệ bỏ qua kết quả `stop()`: khi không phải `DA_DUNG` (vd `DUNG_CHUA_XAC_NHAN`) → hủy trả cảnh báo rõ ("Đã hủy hàng đợi nhưng bộ tải chưa xác nhận dừng"), không báo `da_huy` sạch; `khoi_dong_neu_can` từ chối mở bộ tải thứ hai khi tiến trình cũ còn (`chung_dung`).
3. `:201-206` — gán `_hang_doi` **sau** khi `Thread.start()` thành công, hoặc bọc `try/except` đặt lại `None` → không kẹt `dang_chay` khi tạo luồng lỗi.
4. JS `:293,329` — `huyHangDoi` luôn gọi lại `theoDoiHangDoi` trong `catch`; poll lỗi 0/500/502 dừng sau khoảng 20 lần liên tiếp và hiện "Mất kết nối — bấm Làm mới".
5. Test cho cả 4 điểm (Python + node).

**File được sửa (chỉ):** `src/kho_tri_thuc/giao_dien/m2_tai_hoa_don.py`, `src/kho_tri_thuc/giao_dien/assets/m2_tai_hoa_don.js`, `tests/test_m2_tai_tat_ca.py`, `tests/m2_tai_tat_ca.cjs`. Không xóa file.
**Test phải đạt:** hai test trên + node test M2e hiện có.
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng, ca test · thông điệp commit `[M2h-c] …`.
