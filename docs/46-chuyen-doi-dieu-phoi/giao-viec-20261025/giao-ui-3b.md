# UI-3b — Trang chủ hệ thống (giao diện): lưới icon module, tìm nhanh, thanh cố định 4 mục, M9 "Tạm dừng" (TL 49 §1, CD-008 ưu tiên 5)

Bạn là worker Codex, chạy không tương tác. Căn cứ: `D:\Claude\Phan mem ho tro ke toan\49-trang-chu-luoi-icon.md` §1, §3; hợp đồng dữ liệu `docs\46-chuyen-doi-dieu-phoi\HOP-DONG-DU-LIEU-KHUNG-LUOI.md`; máy chủ UI-3a: `GET /api/khung/he-thong` → `{module: [{ma, ten, icon, nhom_mau, so_viec, qua_han, tam_dung, duong_dan}], thanh_co_dinh: [...]}` (đọc `src/kho_tri_thuc/giao_dien/khung_khai_bao.py`, báo cáo `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\bao-cao-ui-3a.md`). Khung lưới icon của module (UI-1) đã có trong `app.js` (khối "UI-1": `khungDangKy`, `KHUNG_ICON`, `khungLienKet`, ô số việc) — **dùng lại**, không viết khung thứ hai. **Làm ngay, không hỏi lại.** UTF-8 không BOM — ghi tệp bằng UTF-8. Worktree hiện tại, nhánh `lat/ui-3b` (dòng giao diện `lat/ui-dem`). Sandbox không ghi `.git`: **không commit**. Không mở server.

**Việc:**
1. Trang chủ hệ thống (hash trang chủ hiện có của ứng dụng — đọc `index.html`/`app.js` `route()` để biết; nếu chưa có thì `#trang-chu`, và trang mặc định khi mở ứng dụng): lưới icon **module** từ API (tên module, icon theo `nhom_mau`, số việc góc icon như lưới CRM: `so_viec > 0` mới hiện, nền đỏ khi `qua_han`); module `tam_dung` hiện mờ với nhãn **"Tạm dừng"**, bấm không vào (hoặc vào trang báo tạm dừng — chọn cách đơn giản, ghi báo cáo). Bấm module → `duong_dan`.
2. Ô **tìm nhanh** trên đầu: gõ không dấu lọc module theo tên (và tên phần của CRM nếu có sẵn trong dữ liệu đã tải — không gọi thêm API mới), Enter mở mục đầu.
3. **Thanh cố định 4 mục** (`thanh_co_dinh`) luôn hiện (thanh trái hoặc trên như TL 49 §1).
4. API lỗi/không đăng nhập → thông báo tiếng Việt, không vỡ trang; làm mới số theo `lam_moi_sau_giay` nếu API trả (không thì 60 giây, như lưới CRM).
5. Icon tên lạ → `mac-dinh` (như lưới CRM); không mã kỹ thuật trên màn.
**Test — `tests/khung_luoi_async.cjs`:** API giả: lưới đủ module đúng thứ tự; M9 "Tạm dừng" mờ, không điều hướng; số việc CRM hiện, nền đỏ khi `qua_han`; tìm `hoa don` → còn M2; thanh cố định 4 mục; API 503 → thông báo.
**File (≤ 4, gồm 1 test):** `app.js`, `index.html` (chỉ khi buộc thêm vùng), `style.css`, `tests/khung_luoi_async.cjs`. Không sửa máy chủ. Không xóa file.
**Chạy node:** `node tests/khung_luoi_async.cjs`, `node tests/crm_giao_ket_async.cjs`, `node tests/crm_du_an_ban_async.cjs` (+ 20 bộ: lỗi nền như trước) — ghi số trước/sau.
**Báo cáo (≤ ⅓ trang):** sửa ở file:dòng · node trước/sau · Cần Anh · thông điệp commit `[UI-3b] …`.
