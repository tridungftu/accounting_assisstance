# DA-5s — Dự án đang bán (máy chủ): hiện tên dự án thay mã, đơn vị "VND" (lead thử DEMO 26/10 00:10)

Bạn là worker Codex, chạy không tương tác. Lead thử DEMO (cổng 8799, dòng giao diện `lat/ui-dem`): danh sách Dự án đang bán hiện **"Dự án DA_KCN_DEMO"**, **"Dự án DA_NHA_DEMO"** (mã kỹ thuật — trái CLAUDE.md §4) và đơn giá **"35.000.000 đ/m²"** (Anh chốt BG-24: đơn vị "VND" mọi chỗ). **Làm ngay, không hỏi lại.** UTF-8 không BOM. Worktree hiện tại, nhánh `lat/da-5s` (`lat/ui-dem`). Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL (test PG tự skip — lead chạy).

**Việc:**
1. Tìm nguồn tên dự án trong danh sách/chi tiết/ảnh chụp Dự án đang bán (`src/kho_tri_thuc/k2/crm_du_an_ban.py` + SQL `k2/sql_crm_du_an_ban.py` đọc `master.du_an`): nếu `master.du_an` có cột tên mà seed DEMO để trống/bằng mã → seed DEMO (tìm nơi seed `DA_KCN_DEMO`, `DA_NHA_DEMO` — `k2/crm_g_demo.py`/`crm_demo.py`/…) đặt tên hiển thị "KCN DEMO — khu A" và "Khu nhà ở DEMO — tòa A" (idempotent: CSDL DEMO đã seed vẫn được cập nhật tên **chỉ khi** tên đang trống/bằng mã); dịch vụ trả `du_an_ten` và mọi chỗ hiển thị dùng tên (không có tên → "Dự án chưa có tên", **không** in mã). Nếu tên do giao diện ghép `"Dự án " + mã` → báo lead tệp:dòng (lát giao diện sẽ sửa), máy chủ vẫn trả `du_an_ten`.
2. `TIEN_TE` (`crm_du_an_ban.py` ~:31 `{"VND": "đ", …}`) → hiển thị "VND" (vd "35.000.000 VND/m²"); rà các chuỗi hiển thị tiền của module (phí, ảnh chụp, lịch sử) không còn "đ"/"₫"/"VNĐ" sau số.
**Không** đổi SQL/migration (nếu buộc → dừng, báo lead), không sửa giao diện.
**Test:** cập nhật/ thêm trong `tests/test_crm_du_an_ban.py`: hiển thị tiền VND; `du_an_ten` có trong danh sách/chi tiết, không chuỗi `DA_` trong trường hiển thị; phần PG (seed DEMO) đặt tên đúng, chạy seed lần 2 không đổi gì.
**File (≤ 3):** `k2/crm_du_an_ban.py`, tệp seed DEMO dự án (nếu cần), `tests/test_crm_du_an_ban.py`. Không xóa file.
**Chạy test:** `python -X utf8 -m unittest tests.test_crm_du_an_ban tests.test_crm_du_an_moc` — ghi số trước/sau.
**Báo cáo (≤ ¼ trang):** nguồn tên (tệp:dòng) · sửa ở file:dòng · số test · thông điệp commit `[DA-5s] …`.
