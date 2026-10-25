# BG-e4 vòng 2 — nhãn vai "Phụ trách dự án"; test M4 kiểm đổi vai bằng giá trị ô chọn

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Cùng quy tắc `giao-bg-e4.md`. Worktree hiện tại, nhánh `lat/bg-e4`.
1. `app.js` (~:524, hàm `vai`): thêm `DU_AN` → "Phụ trách dự án" (và vai khác có trong `danh_tinh_demo` nếu còn thiếu nhãn — tìm trong seed/test hiện có); không suy vai từ login.
2. `tests/m4_01c_async.cjs` ~:219 (P0): với `crm-nguoi`, kiểm vai mới bằng **giá trị ô `crm-danh-tinh`** (= login) hoặc nội dung đã đổi so với trước — vì dòng mô tả không còn in login (BG-22); giữ nguyên các kiểm khác.
**File (≤ 3):** `app.js`, `tests/m4_01c_async.cjs`, `tests/khung_luoi_async.cjs` (nếu thêm ca DU_AN). Không xóa file.
**Báo cáo (≤ 5 dòng):** sửa ở file:dòng · node trước/sau · thông điệp commit `[BG-e4] vòng 2: …`.
