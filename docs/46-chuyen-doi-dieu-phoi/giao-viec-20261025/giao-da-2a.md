# DA-2a — CRM · màn "Dự án đang bán": phần XEM (danh sách, chi tiết, lịch sử)

Bạn là worker Codex, chạy không tương tác. Anh đã chốt thiết kế (25/10, QD-20261025-05…09, 17, 18) và ra lệnh code: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/da-2` (= màn Báo giá `lat/bg-1d` + máy chủ dự án đang bán `lat/da-1`). Sandbox không ghi `.git`: **không commit**. Chạy được: `node tests/crm_giao_ket_async.cjs`, `node tests/<test mới>.cjs`. Không mở server/DEMO (lead thử trên DEMO).

**Căn cứ:** `docs/46-chuyen-doi-dieu-phoi/THIET-KE-DU-AN-DANG-BAN.md` (checklist cổng B dòng 1–8). Hợp đồng dữ liệu máy chủ (đã có trên nhánh — đọc `src/kho_tri_thuc/giao_dien/crm_g.py` khối `_dieu_huong_da` và `src/kho_tri_thuc/k2/crm_du_an_ban.py`):
- `GET /api/crm/du-an-ban[?dang_ban=1]` → `{du_an_ban:[{da_ban_id, du_an_id, du_an_ma, phien_ban, dang_ban, don_gia_niem_yet, tien_te, loai_hinh_id, giai_doan_g7, so_phi, so_lo, duoc_sua, don_gia_hien_thi}], du_an_chua_ban:[…], loai_hinh:[…], danh_muc:{…nhãn tiếng Việt}}`
- `GET /api/crm/du-an-ban/{da_ban_id}[?phien_ban=&ngay=]` → `{anh_chup, hien_thi, phien_ban_ds, duoc_sua}`
- `GET /api/crm/du-an-ban/{da_ban_id}/lich-su` → `{phien_ban[+noi_dung], su_kien, lo[lich_su], tien_do[nguon]}`
**Dùng lại:** cách mục 5 "Mẫu hợp đồng & bộ chuẩn dự án" trong `src/kho_tri_thuc/giao_dien/assets/crm_g.js` dựng nút chuyển "Mẫu hợp đồng (G1)" / "Bộ chuẩn dự án (G7)", hàm gọi API có token/phiên, hàm định dạng ngày/tiền/escape (`node`, `textContent`) sẵn có — **không viết helper trùng**.

**Việc:**
1. Mục 5 thêm nút thứ ba **"Dự án đang bán"**: bảng danh sách (Dự án, Đơn giá niêm yết dạng "120 USD/m²" từ máy chủ, Số loại phí, Số lô/căn, Trạng thái Đang bán/Ngừng bán, Phiên bản); lọc "Chỉ dự án đang bán".
2. Bấm một dòng → khung chi tiết: thông tin chung (vị trí, mô tả, đơn giá + tiền tệ, loại hình, thuế mặc định — hiện đúng như máy chủ trả, **không tự tính**), bảng phí (tên, loại, mức, đơn vị tính tiếng Việt, tiền tệ, cơ sở tính), bảng lô/căn (mã, diện tích m², trạng thái 4 loại tiếng Việt), tiến độ thanh toán tiêu chuẩn (đợt, %, mốc). Chọn phiên bản cũ trong `phien_ban_ds` → xem đúng phiên bản đó.
3. Nút **"Lịch sử"** → danh sách phiên bản (số, hiệu lực từ–đến dd/mm/yyyy, người lập, lý do, trường đã đổi) + sự kiện ngừng/mở bán + lịch sử lô.
4. **Chưa** làm nút thêm/sửa (lát DA-2b); chỉ chừa chỗ (không hiện nút giả).
5. Test mới `tests/crm_du_an_ban_async.cjs` theo mẫu `tests/crm_giao_ket_async.cjs` (DOM giả + fetch giả): danh sách/lọc, chi tiết theo phiên bản, lịch sử, ngày dd/mm/yyyy, không chèn HTML thô (chuỗi `<b>` hiện nguyên văn), không lộ mã kỹ thuật (id/uuid, mã enum) trên màn hình.

**File được sửa/tạo (chỉ):** `src/kho_tri_thuc/giao_dien/assets/crm_g.js` (thêm khối riêng, không sửa phần Báo giá), `src/kho_tri_thuc/giao_dien/assets/style.css` (chỉ thêm lớp mới), `tests/crm_du_an_ban_async.cjs` (mới).
**Không làm:** máy chủ, thêm/sửa dữ liệu, phần thuế theo khoản (đang chờ Anh thiết kế), xóa file.
**Test phải đạt:** `node tests/crm_du_an_ban_async.cjs` và `node tests/crm_giao_ket_async.cjs` (23/23 nhóm cũ không đổi).
**Báo cáo cuối (≤ ½ trang):** màn hình gồm gì (vị trí, cột) · ca test · file đã sửa · thông điệp commit `[DA-2a] …` · điểm cần lead thử trên DEMO.
