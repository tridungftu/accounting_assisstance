# REVIEW DA-2b1 + DA-2b2 (CRM · màn Dự án đang bán — thêm/sửa) · vòng 1/2 · reviewer Claude (chỉ đọc)

Bạn là reviewer chéo cho code Codex viết. **Chỉ đọc**: không sửa tệp, không commit, không mở server. Worktree `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\.claude\worktrees\lat-da-2`, nhánh `lat/da-2`. Hai commit: `be23e42` (DA-2b1: bật bán, sửa thông tin, ngừng/mở bán) và commit `[DA-2b2]` ngay sau (phí, lô/căn, tiến độ áp dụng ngay, ẩn nút CFO ở G7). Xem: `git -C <worktree> log --oneline -6` rồi `git show <commit>` cho từng commit. Tệp: `src/kho_tri_thuc/giao_dien/assets/crm_g.js` (khối Dự án đang bán + tab G7), `assets/style.css`, `tests/crm_du_an_ban_async.cjs`. Được chạy: `node tests/crm_du_an_ban_async.cjs`, `node tests/crm_giao_ket_async.cjs` (trong worktree).

**Căn cứ:** `docs/46-chuyen-doi-dieu-phoi/THIET-KE-DU-AN-DANG-BAN.md` (checklist cổng B 1–8); `docs/QUYET-DINH.md` QD-20261025-07 (bán hàng tự sửa, hiệu lực ngay, nhật ký), -17 (tắt luồng CFO trên màn hình, giữ bản cũ xem được), -18 (đơn giá theo m², 4 trạng thái lô), -20 (giá chưa gồm VAT, thuế danh mục mặc định 10%, giá đất trừ). Hợp đồng dữ liệu máy chủ: `src/kho_tri_thuc/giao_dien/crm_g.py` khối `_dieu_huong_da`, `src/kho_tri_thuc/k2/crm_du_an_ban.py`.

**Kiểm 5 việc, Đạt/Không:**
1. **Tiền và số:** mọi số nhập kiểu Việt ("1.234,5") chuyển thành chuỗi ASCII đúng trước khi gửi, không qua float; ô trống/sai → báo lỗi tại ô, không gửi; tiền/diện tích hiển thị lấy chuỗi máy chủ.
2. **Ghi đồng thời:** mọi lệnh ghi gửi đúng `expected_phien_ban` / `expected_lan` / `expected_version` của bản đang xem; 409 giữ nháp, báo rõ (lô nào), có nút tải lại; không ghi đè lặng lẽ; `khoa` idempotent không bị dùng lại cho lệnh khác nội dung.
3. **Cập nhật một phần:** form sửa thông tin gửi đủ trường hiện hành (đặc biệt `thue_suat`, `gia_dat_tru`) để không đổi ngoài ý — máy chủ đã giữ giá trị khi thiếu, nhưng màn hình không được gửi giá trị mặc định đè lên giá trị đang có.
4. **Quyền và luồng CFO:** nút thêm/sửa chỉ hiện khi `duoc_sua`; tab G7 không còn nút "Gửi CFO duyệt"/"CFO duyệt" nhưng bản CFO cũ vẫn xem được; không lỗi với vai không có quyền.
5. **An toàn + tiếng Việt:** chèn DOM qua `textContent` (không `innerHTML` dữ liệu); không mã kỹ thuật (uuid, enum) trên màn hình; ngày dd/mm/yyyy; test mới có nghĩa (không test rỗng) và `crm_giao_ket_async.cjs` 23/23 vẫn đạt.

**Báo cáo cuối (≤ ½ trang, tiếng Việt, ≤ 8 điểm):**
```
REVIEW DA-2b · vòng 1/2 · Claude
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi gửi sai số tiền/thuế, ghi đè không có CAS, lộ nút cho người không có quyền, hoặc chèn DOM không an toàn.
