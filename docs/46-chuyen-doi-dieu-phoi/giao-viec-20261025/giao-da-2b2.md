# DA-2b2 — CRM · màn "Dự án đang bán": phí tiêu chuẩn, lô/căn, tiến độ áp dụng ngay; tắt luồng CFO trên màn hình

Bạn là worker Codex, chạy không tương tác. Anh đã chốt (QD-20261025-07, 17, 18, 20): **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM. Worktree hiện tại, nhánh `lat/da-2` (đầu `be23e42`: DA-2a + DA-2b1). Sandbox không ghi `.git`: **không commit**. Chạy: `node tests/crm_du_an_ban_async.cjs`, `node tests/crm_giao_ket_async.cjs`.

**Máy chủ (đã có — đọc `src/kho_tri_thuc/giao_dien/crm_g.py` khối `_dieu_huong_da`):** `POST /api/crm/du-an-ban/phi {da_ban_id, expected_phien_ban, phi:[{ten, loai BAO_TRI|SU_DUNG|KHAC, muc (chuỗi, chưa gồm VAT), don_vi_tinh M2_THANG|M2_NAM|LAN, tien_te, co_so_tinh}], ly_do, khoa}` · `lo {da_ban_id, lo:[{ma, dien_tich, trang_thai CON_TRONG|GIU_CHO|DA_BAN|KHONG_BAN, ghi_chu, expected_lan}], khoa}` · `tien-do {du_an_id, giai_doan?, dong, expected_version, khoa}` (áp dụng ngay, 409 khi bản đã đổi). Nhãn tiếng Việt lấy từ `danh_muc` của `GET /api/crm/du-an-ban`.
**Dùng lại:** khối Dự án đang bán (DA-2a/2b1: form, xử lý 400 theo ô, 409 giữ nháp, nhập số kiểu Việt → chuỗi ASCII), bảng nhập lịch 4 cột / ô Giá trị thông minh của màn Báo giá cho bảng tiến độ nếu dùng được (không viết lại helper).

**Việc:**
1. Chi tiết dự án — nút **"Sửa phí"**: bảng thêm/bớt dòng phí (tên, loại, mức, đơn vị tính, tiền tệ, cơ sở tính), ghi rõ "mức chưa gồm VAT", lý do bắt buộc → `phi` (CAS phiên bản).
2. Nút **"Sửa lô/căn"**: bảng lô (mã, diện tích m², trạng thái 4 loại, ghi chú), thêm lô mới, đổi trạng thái; gửi `lo` với `expected_lan` từng lô; 409 → báo lô nào vừa bị người khác đổi.
3. Nút **"Sửa tiến độ tiêu chuẩn"**: bảng đợt (%, hoặc số tiền, mốc) → `tien-do` với `expected_version`; ghi rõ "Áp dụng ngay — QD-20261025-07".
4. **Tắt luồng CFO trên màn hình (QD-20261025-17):** trong tab "Bộ chuẩn dự án (G7)" của mục 5, **ẩn** các nút "Gửi CFO duyệt" và "CFO duyệt (V4)" (khoảng `crm_g.js:747, 825-829`); bản CFO đã duyệt cũ vẫn xem được; thêm dòng chú thích "Tiến độ tiêu chuẩn sửa trong Dự án đang bán, áp dụng ngay". Không xóa mã máy chủ.
5. Test thêm nhóm vào `tests/crm_du_an_ban_async.cjs`: phí (body, đơn vị, 400 theo ô `phi.0.muc`), lô (thêm/đổi trạng thái, 409 theo lô), tiến độ (body + 409), G7 không còn nút gửi/duyệt CFO nhưng vẫn xem bản cũ; `crm_giao_ket_async.cjs` 23/23 vẫn đạt (sửa ca nào đang kiểm nút CFO thì ghi rõ).

**File được sửa (chỉ):** `src/kho_tri_thuc/giao_dien/assets/crm_g.js`, `src/kho_tri_thuc/giao_dien/assets/style.css` (chỉ thêm lớp), `tests/crm_du_an_ban_async.cjs`, `tests/crm_giao_ket_async.cjs` (chỉ nếu ca cũ kiểm nút CFO). Không sửa máy chủ, phần Báo giá; không xóa file.
**Báo cáo cuối (≤ ½ trang):** nút/bảng gồm gì · ca test · file đã sửa · thông điệp commit `[DA-2b2] …`.
