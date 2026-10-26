# E1-4u — Màn "Danh mục tham số" chung (xem/sửa + nhật ký) trên trang chủ hệ thống (QD-20261026-02)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.** Đọc `AGENTS.md`, `CLAUDE.md` §4 (tiếng Việt nghiệp vụ, không mã kỹ thuật, ngày dd/mm/yyyy). UTF-8 không BOM — ghi tệp bằng UTF-8. Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL. Không xóa file.

Worktree hiện tại, nhánh `lat/e1-4u` (dòng giao diện `lat/ui-ky`, có trang chủ hệ thống UI-3). Căn cứ: `docs\QUYET-DINH.md` **QD-20261026-02** (một ô riêng trên trang chủ hệ thống "Danh mục tham số" dùng chung cho mọi module); máy chủ E1-4a đã có lệnh **xem/sửa danh mục + nhật ký** (E1-MUA: 5 loại hợp đồng mua + DV, `danh_muc_theo_loai`, phiên bản danh mục — tìm trong `src/kho_tri_thuc/` theo `danh_muc_theo_loai`, `phien_ban_danh_muc`, E1-4a/E1-4b trong `docs\46-chuyen-doi-dieu-phoi\TRANG-THAI.md`). Nếu máy chủ **chưa có route HTTP** cho các lệnh này → thêm route mỏng (quyền ở máy chủ: xem cho người có module liên quan, sửa cho kế toán trưởng/admin — ghi "Cần Anh" vai sửa).
**Việc:**
1. `giao_dien/khung_khai_bao.py`: thêm module **"Danh mục tham số"** vào `HE_THONG` (icon có sẵn hoặc `mac-dinh`, nhóm `danh_muc`, đường dẫn riêng).
2. Màn (JS/HTML theo cách các trang khác đăng ký trong `app.js`/`index.html`): chọn **loại** (5 loại + DV) → bảng tham số (mã tham số hiển thị tên tiếng Việt, mô tả, bắt buộc/không…), **Sửa** (lý do bắt buộc), **Nhật ký** (cũ → mới, ai, lúc dd/mm/yyyy hh:mm); 409 khi phiên bản đổi.
3. Test: Python route (quyền, tham số lạ 400) + node màn (chọn loại, sửa có lý do, nhật ký, không mã kỹ thuật).
**File (≤ 5, gồm test):** `khung_khai_bao.py`, (route) tệp HTTP liên quan, `app.js` hoặc tệp JS mới, `index.html` (nếu cần vùng), 1–2 test. **Báo cáo (≤ ⅓ trang)**, Cần Anh, thông điệp commit `[E1-4u] …`.
