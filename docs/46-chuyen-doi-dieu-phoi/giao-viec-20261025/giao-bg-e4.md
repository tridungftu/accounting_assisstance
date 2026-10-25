# BG-e4 — Khối "Vai mô phỏng" CRM: tên tiếng Việt, ngày dd/mm/yyyy (BG-22 — CD-005)

Bạn là worker Codex, chạy không tương tác. Anh đã chốt (25/10 22:05, **CD-005**; TL 45 §8 dòng BG-22: "hiện tên tiếng Việt (vai, pháp nhân), ngày dd/mm/yyyy; không hiện `MO_PHONG_KT_A`, `KE_TOAN`, `PN_DEMO_A`, `2026-10-25`"; tiêu chí: không còn chuỗi có `_` hoặc ngày yyyy-mm-dd): **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§4). UTF-8 không BOM. Worktree hiện tại, nhánh `lat/bg-e4` (từ `lat/ui-1`). Sandbox không ghi `.git`: **không commit**. Không mở server.

**Việc (`src/kho_tri_thuc/giao_dien/assets/app.js` `crmRender` ~:522-530 — ô `crm-danh-tinh` và dòng mô tả người đang dùng):**
1. Ô chọn vai: nhãn tiếng Việt (vd. "Kế toán · Pháp nhân A (mô phỏng)", "Bán hàng · …", "CFO · …", "Người xem · …") theo **vai + pháp nhân** từ dữ liệu máy chủ (có tên pháp nhân thì dùng tên; không có thì nhãn chung tiếng Việt), **giá trị** option vẫn là login để đổi vai đúng; hai vai trùng nhãn → thêm số thứ tự. Theo mẫu M2s-b (`m2Render` đã đổi nhãn `MO_PHONG_KT_M2_A`).
2. Dòng mô tả: vai, pháp nhân bằng tên tiếng Việt; **ngày nghiệp vụ dd/mm/yyyy**; không in login/mã.
3. Test node: thêm ca vào `tests/khung_luoi_async.cjs` hoặc bộ CRM node hiện có phù hợp — không còn chuỗi có `_` hoặc ngày `yyyy-mm-dd` trong khối; đổi vai vẫn gửi đúng login.
**File (≤ 2):** `app.js`, 1 tệp test node. Không xóa file.
**Báo cáo (≤ 5 dòng):** sửa ở file:dòng · ca test · thông điệp commit `[BG-e4] …`.
