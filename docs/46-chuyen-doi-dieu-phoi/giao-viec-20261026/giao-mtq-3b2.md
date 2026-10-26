# MTQ-3b2: Ma trận thẩm quyền, nối màn hình vào khung (menu, trang Quản trị), dòng giao diện (CD-012; thiết kế dòng MTQ-3b, phần giao diện)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Đọc `AGENTS.md`, `CLAUDE.md` §4. Giao diện dùng tiếng Việt nghiệp vụ, không mã kỹ thuật.
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-3b2`, dựng từ **`lat/ui-ky`** (dòng giao diện, đã nhận hợp nhất có MTQ-2/2b/2c/2d/3a/3b1).

**Đã có:**
- Module `src/kho_tri_thuc/giao_dien/assets/ma_tran_tham_quyen.js`, hàm `dungMaTranThamQuyen(...)`, có chỗ nhận `tenPhapNhan`/`tenNguoi`.
- Máy chủ phục vụ `/ma_tran_tham_quyen.js` và route `/api/tham-quyen/*`.
- GET `cua-toi` trả `la_admin`.
- Khung trang chủ hệ thống dạng lưới icon (UI-1/UI-3, `khung_khai_bao.py` + `app.js`); màn "Danh mục tham số" chung (E1-4u) là mẫu thêm một màn vào trang chủ hệ thống.

**Việc:**
1. `src/kho_tri_thuc/giao_dien/assets/index.html`: nạp `ma_tran_tham_quyen.js` giống các asset riêng khác.
2. `src/kho_tri_thuc/giao_dien/assets/app.js`: thêm màn "Ma trận thẩm quyền" vào **trang chủ hệ thống**, theo đúng cách E1-4u thêm "Danh mục tham số".
   - Vùng trang được dựng lười, **không dùng API DOM mà DOM giả của test không có** (bài học `.after` của E1-4u).
   - Mở màn: gọi `cua-toi`; `la_admin` true thì dựng màn Admin, false thì dựng "Quyền của tôi". **Không đoán ở trình duyệt.**
   - Cấp `tenPhapNhan`/`tenNguoi` từ dữ liệu khung đã có (danh sách pháp nhân, người mô phỏng); thiếu thì để module dùng nhãn dự phòng.
   - Đổi vai DEMO: tải lại màn và hủy phản hồi cũ.
   - Không thêm nút "Bật". Module đã ẩn nút khi máy chủ chưa cho bật.
3. Ô trên lưới trang chủ hệ thống: "Ma trận thẩm quyền", nhóm màu `he_thong`. **Mọi vai đều thấy** vì người thường xem được "Quyền của tôi".

Nếu cần đăng ký ô trong `khung_khai_bao.py` (máy chủ) thì được sửa tệp đó; ghi rõ trong báo cáo. Tổng tệp không quá 4.

**Test:**
- Thêm ca vào bộ node của khung hoặc tạo tệp `tests/mtq_man_async.cjs`:
  - ô hiện trên trang chủ hệ thống;
  - `la_admin` true dựng màn Admin, false dựng "Quyền của tôi";
  - đổi vai thì tải lại;
  - không lỗi khi DOM giả không có `.after`/`.before`.
- Chạy **toàn bộ** `tests/*.cjs`, báo số đạt. So với `lat/ui-ky` trước sửa: không thêm bộ đỏ.

**Tệp (≤ 4):** `app.js`, `index.html`, (tùy) `khung_khai_bao.py`, 1 test.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[MTQ-3b2] …`.
