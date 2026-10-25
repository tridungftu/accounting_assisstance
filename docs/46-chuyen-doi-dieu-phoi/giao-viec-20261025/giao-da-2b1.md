# DA-2b1 — CRM · màn "Dự án đang bán": bật bán + sửa thông tin chung + ngừng/mở bán

Bạn là worker Codex, chạy không tương tác. Anh đã chốt thiết kế (QD-20261025-05…09, 17, 18, 20): **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2: không khởi động PostgreSQL/server DEMO trong sandbox). UTF-8 không BOM. Worktree hiện tại, nhánh `lat/da-2` (đầu `acab3b6`: màn xem DA-2a vòng 2 + máy chủ DA-1 có thuế). Sandbox không ghi `.git`: **không commit**. Chạy: `node tests/crm_du_an_ban_async.cjs`, `node tests/crm_giao_ket_async.cjs`.

**Máy chủ (đã có, chỉ dùng — đọc `src/kho_tri_thuc/giao_dien/crm_g.py` khối `_dieu_huong_da`, `src/kho_tri_thuc/k2/crm_du_an_ban.py`):** `POST /api/crm/du-an-ban/bat-ban {du_an_id, thong_tin, phi, ly_do, khoa}` · `cap-nhat {da_ban_id, expected_phien_ban, thong_tin, phi?, ly_do, khoa}` · `ngung-ban` / `mo-ban-lai {da_ban_id, expected_phien_ban, ly_do, khoa}`; `thong_tin` gồm vị trí, mô tả, `don_gia_niem_yet` (chuỗi, theo m², chưa gồm VAT), `tien_te` VND|USD, `loai_hinh_id`, `thue_suat` (danh mục, mặc định "10"), `gia_dat_tru` (chuỗi, ≤ đơn giá), `giai_doan_g7`; lỗi 400 kèm `truong`, 409 `CRM_DA_PHIEN_BAN_CU`, 403 không quyền. `GET /api/crm/du-an-ban` trả `du_an_chua_ban`, `loai_hinh`, `danh_muc` (nhãn thuế…), `duoc_sua`.
**Dùng lại:** khối Dự án đang bán hiện có trong `assets/crm_g.js` (DA-2a), helper gọi API/khóa idempotent `khoa`, helper nhập số kiểu Việt của màn Báo giá (BG-1b/1d — tìm hàm chuyển "1.234,5" → chuỗi số), `node`/`textContent`.

**Việc:**
1. Nút **"Thêm dự án đang bán"** (chỉ hiện khi `duoc_sua`): chọn dự án từ `du_an_chua_ban` (tên dự án, không mã kỹ thuật) → form thông tin chung: vị trí, mô tả, đơn giá niêm yết **/m² (chưa gồm VAT)** + tiền tệ, loại hình, **thuế suất** (danh sách thả xuống từ `danh_muc`, mặc định 10%), **giá đất được trừ /m²**, giai đoạn tiến độ mặc định, **lý do** (bắt buộc) → `bat-ban`.
2. Ở chi tiết: nút **"Sửa thông tin"** → cùng form, nạp giá trị phiên bản hiện hành, gửi `cap-nhat` với `expected_phien_ban`; 409 → thông báo "Dự án vừa được người khác sửa — tải lại để xem bản mới" + nút tải lại, giữ nội dung đang gõ.
3. Nút **"Ngừng bán"** / **"Mở bán lại"** (hộp xác nhận + lý do bắt buộc).
4. Lỗi 400 có `truong` → báo đỏ đúng ô; mọi số nhập kiểu Việt chuyển thành chuỗi số ASCII trước khi gửi (không float); sau khi lưu → tải lại danh sách + chi tiết (phiên bản mới).
5. Test `tests/crm_du_an_ban_async.cjs` thêm nhóm: bật bán (body đúng, mặc định thuế 10), sửa + 409, ngừng/mở bán, lỗi theo trường, người không `duoc_sua` không thấy nút, nhập "1.234,5" → gửi "1234.5".

**File được sửa (chỉ):** `src/kho_tri_thuc/giao_dien/assets/crm_g.js` (khối Dự án đang bán), `src/kho_tri_thuc/giao_dien/assets/style.css` (chỉ thêm lớp), `tests/crm_du_an_ban_async.cjs`. **Không làm:** phí, lô/căn, tiến độ (lát DA-2b2), máy chủ, phần Báo giá, xóa file.
**Test phải đạt:** `node tests/crm_du_an_ban_async.cjs` (nhóm cũ + mới), `node tests/crm_giao_ket_async.cjs` 23/23.
**Báo cáo cuối (≤ ½ trang):** nút/form gồm gì · ca test · file đã sửa · thông điệp commit `[DA-2b1] …`.
