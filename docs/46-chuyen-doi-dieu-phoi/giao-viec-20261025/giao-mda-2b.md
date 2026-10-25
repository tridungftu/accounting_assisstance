# MDA-2b — Mục Mốc thanh toán: bỏ chữ trạng thái lặp (review dòng giao diện điểm 3)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.** UTF-8 không BOM — ghi tệp bằng UTF-8. Worktree hiện tại, nhánh `lat/mda-2b` (`lat/ui-dem`). Sandbox không ghi `.git`: **không commit**. Không mở server.
Việc: `src/kho_tri_thuc/giao_dien/assets/crm_g.js` hàm vẽ dòng mốc (`veMoc` trong khối Dự án đang bán): dòng mốc quá dự kiến đang hiện "Quá ngày dự kiến — cần chỉnh ngày" **hai lần** (nhãn `trang_thai_hien_thi` của máy chủ + thẻ `strong` nối thêm) → chỉ một lần (giữ nhãn máy chủ, dòng vẫn nổi bật cảnh báo). Thêm assert vào `tests/crm_du_an_ban_async.cjs`: chuỗi đó xuất hiện đúng 1 lần trong dòng mốc quá hạn.
**File (≤ 2):** `crm_g.js`, `tests/crm_du_an_ban_async.cjs`. Không xóa file.
**Chạy node:** `node tests/crm_du_an_ban_async.cjs`, `node tests/crm_giao_ket_async.cjs` — ghi số.
**Báo cáo (≤ 5 dòng):** sửa ở file:dòng · số test · thông điệp commit `[MDA-2b] …`.
