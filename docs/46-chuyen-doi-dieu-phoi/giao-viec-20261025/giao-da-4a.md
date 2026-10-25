# DA-4a — Lưới CRM: thêm phần thứ 7 "Dự án đang bán" (máy chủ khai báo khung, TL 49) — CD-006 mục 1

Bạn là worker Codex, chạy không tương tác. Căn cứ: hộp thư **CD-006** mục 1 (Anh: "chưa thấy phần danh mục dự án bán hàng" trên DEMO; DEMO phải có màn **Dự án đang bán** sáng 26/10); hợp đồng dữ liệu khung `docs\46-chuyen-doi-dieu-phoi\HOP-DONG-DU-LIEU-KHUNG-LUOI.md`; thiết kế `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MOC-DU-AN.md` §3 dòng DA-4. **Làm ngay, không hỏi lại.** UTF-8 không BOM. Worktree hiện tại, nhánh `lat/da-4a` (dòng giao diện CRM `lat/bg-gom`). Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL.

**Việc — `src/kho_tri_thuc/giao_dien/khung_khai_bao.py`:**
1. `MODULE["crm"]["phan"]` thêm phần `_phan("du_an_ban", "Dự án đang bán", "du-an", "danh_muc", 35, VAI)` — đứng sau "Mẫu hợp đồng" (thu_tu 30), trước "Tiếp nhận hợp đồng ký" (40); đường dẫn tự sinh `#crm/du-an-ban`. Không thêm bộ đếm lúc này (số việc chờ "Chỉnh ngày dự kiến mốc" là lát MDA-4).
2. Không đổi 6 phần cũ, không đổi thẻ, không đổi quyền/bộ đếm khác.
**Test — `tests/test_khung_luoi_crm.py`:** cập nhật ca đang ghim 6 phần (nếu có) thành 7 phần đúng thứ tự; thêm ca: vai Bán hàng/Kế toán/Kế toán trưởng/CFO/Người xem đều thấy phần "Dự án đang bán", đường dẫn `#crm/du-an-ban`, icon `du-an`, không có `so_viec`.
**File (≤ 2):** `src/kho_tri_thuc/giao_dien/khung_khai_bao.py`, `tests/test_khung_luoi_crm.py`. Không xóa file.
**Chạy test:** `python -X utf8 -m unittest tests.test_khung_luoi_crm` (phần cần PostgreSQL tự skip) — ghi số trước/sau.
**Báo cáo (≤ ¼ trang):** sửa ở file:dòng · số test · thông điệp commit `[DA-4a] …`.
