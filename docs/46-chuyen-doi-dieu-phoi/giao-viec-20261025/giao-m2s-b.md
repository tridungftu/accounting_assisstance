# M2s-b — nhãn tiếng Việt cho người dùng DEMO "Kế toán M2 (mô phỏng)" trong danh sách đổi vai

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§4: giao diện tiếng Việt, không mã kỹ thuật). UTF-8 — **ghi tệp bằng UTF-8**. Worktree hiện tại, nhánh `lat/m2s-b` (từ hop-nhat, đã có M2s: người dùng `MO_PHONG_KT_M2_A` trong `src/kho_tri_thuc/k2/m2_demo.py`). Sandbox không ghi `.git`: **không commit**. Chạy: node test giao diện hiện có liên quan đổi vai (tìm trong `tests/*.cjs`).

**Việc:** trong danh sách đổi vai mô phỏng của giao diện (`src/kho_tri_thuc/giao_dien/assets/app.js` — tìm nơi đang gán nhãn tiếng Việt cho các login `MO_PHONG_*`), thêm nhãn **"Kế toán M2 (mô phỏng)"** cho `MO_PHONG_KT_M2_A` theo đúng cách các nhãn khác đang làm (bảng nhãn hoặc hàm), không hiện tên đăng nhập kỹ thuật. Nếu nhãn đến từ máy chủ thay vì `app.js` → sửa đúng chỗ đó (1 tệp). Thêm 1 ca vào node test hiện có kiểm nhãn.
**File được sửa (≤ 2):** tệp chứa bảng nhãn + 1 tệp test. Không xóa file.
**Báo cáo cuối (≤ 5 dòng):** sửa ở tệp:dòng · ca test · thông điệp commit `[M2s-b] …`.
