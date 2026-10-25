# T-DA2 — Cập nhật 2 test còn đòi giao diện cũ sau khi gộp BG-1d + DA-2 (CD-006 mục 1)

Bạn là worker Codex, chạy không tương tác. Lead gộp thử `lat/da-2` (BG-1d + DA-2) vào hợp nhất (nhánh `kiem/gop-da-2`), test so nền có 2 mã lỗi mới, đều do test còn đòi giao diện cũ (giao diện mới đúng ý Anh: bỏ mã kỹ thuật "(G2)/(G3)" trên nút; QD-20261025-07 bỏ bước CFO duyệt bộ chuẩn G7 — áp dụng ngay trong Dự án đang bán). **Làm ngay, không hỏi lại.** UTF-8 không BOM. Worktree hiện tại, nhánh `kiem/gop-da-2`. Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL. **Chỉ sửa test, không sửa mã sản phẩm.**

1. `tests/crm_ky_ket_async.cjs` (~:208): tìm nút theo nhãn mới ("Soạn hợp đồng", "Báo giá" — xem `src/kho_tri_thuc/giao_dien/assets/crm_g.js` ~:1746) — rà cả tệp mọi nhãn/luồng đã đổi theo BG-1d (màn Báo giá 2 bước) và DA-2; giữ nguyên ý mọi ca (không xóa assert, chỉ đổi cách tìm phần tử/nhãn). Chạy `node tests/crm_ky_ket_async.cjs` đến khi đạt.
2. `tests/test_crm_41_02.py` (`HttpShellTinh.test_shell_mount_va_s6`, ~:444): bỏ đòi chuỗi `"bo-chuan/gui-duyet"`, `"bo-chuan/duyet"` trong `crm_g.js` **chỉ nếu** giao diện mới không còn gọi các route đó (kiểm bằng grep `crm_g.js`); thay bằng kiểm route áp dụng ngay `du-an-ban/tien-do` có trong `crm_g.js` và ghi chú căn cứ QD-20261025-07. Route máy chủ cũ (nếu `crm_g.py` còn) giữ nguyên, không kiểm ở đây.
**File (≤ 2):** `tests/crm_ky_ket_async.cjs`, `tests/test_crm_41_02.py`. Không xóa file.
**Chạy test:** `node tests/crm_ky_ket_async.cjs`; `python -X utf8 -m unittest tests.test_crm_41_02` — ghi số trước/sau.
**Báo cáo (≤ ¼ trang):** sửa ở file:dòng · số test · thông điệp commit `[T-DA2] …`.
