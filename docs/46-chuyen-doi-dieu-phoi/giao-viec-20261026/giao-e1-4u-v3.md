# E1-4u vòng 3: sửa lỗi cổng lead (17 bộ test node hỏng) và 4 điểm nên sửa của review vòng 2

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. Sandbox không ghi được `.git`: **không commit**.
- Không mở server. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/e1-4u` (4bfe9be).
- Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261026\review-e14u-v2-ky-g5tay-ui.md`, phần E1-4u.

**1. Bắt buộc, lỗi cổng lead.**
- `src/kho_tri_thuc/giao_dien/assets/app.js:2152` gọi `$("page-hoso").after(dmPage)` ngay khi nạp tệp. DOM giả của các bộ test node không có `.after`, nên 17 bộ lỗi `TypeError: $(...).after is not a function`. Ví dụ: `tests/crm_ky_ket_async.cjs`, `m4_03b_async.cjs`, `m4_01c_async.cjs`, `crm_giao_ket_async.cjs`, `crm_du_an_ban_async.cjs`, các bộ `m4_0*`.
- Trên nhánh gốc `lat/ui-ky` các bộ này đạt; chỉ `crm_doi_chieu_async.cjs`, `m2_00a_source7_fix02.cjs`, `m2_00b_source7_rpc.cjs` đỏ sẵn.
- Sửa cách gắn vùng "Danh mục tham số":
  - Không dùng API DOM mà các DOM giả không có.
  - Có thể dựng lười (chỉ khi mở màn lần đầu) hoặc dùng `appendChild`/`insertBefore` lên phần tử cha như các màn mở rộng khác đang làm. Xem cách các vùng khác trong `app.js` được thêm vào.
  - Giữ nguyên hành vi trên trình duyệt thật.
- **Không** sửa test của bộ khác để lách lỗi.

**2. Nên sửa của review, trong `src/kho_tri_thuc/giao_dien/khung_khai_bao.py`:**
- Lỗi toàn vẹn (tệp lệch SHA đã ghim, lệch chuỗi nhật ký) dùng mã **`CRM_G_TEP_HONG`** (đã có trong MA_409), câu: "Tệp danh mục không khớp nhật ký đã xác nhận. Báo quản trị kiểm tra trước khi sửa tiếp."
  - `app.js` hiện câu này, không báo "người khác sửa".
- Lỗi engine "Dòng thiếu Mã hoặc Mô tả" → 400 với câu "Mô tả tham số không được để trống."
- Nhánh `except ValueError` cuối: chỉ đổi thành 400 cho các thông điệp đã biết của engine.
  - Lỗi `ValueError` khác thì ghi log mã lỗi (không ghi dữ liệu) rồi trả câu chung.
  - Không nuốt lỗi mà không để lại dấu vết.
- Lần nạp engine đầu tiên (`_nap_danh_muc`) chạy dưới một khóa, tránh nạp hai lần đồng thời.
  - Không lồng với `mutation_lock`; không làm lại lỗi treo khóa.

**3. Test `tests/test_khung_he_thong.py`:**
- Ca 403: khẳng định tệp và nhật ký không đổi.
- Ca mã `CRM_G_TEP_HONG`.
- Ca mô tả trống.
- Giữ ca hồi quy treo khóa.

**Chạy:**
- **Toàn bộ** `tests/*.cjs` bằng node: báo từng bộ đạt hay không. Ngoài 3 bộ đỏ sẵn, mọi bộ phải đạt.
- `python -X utf8 -m unittest tests.test_khung_he_thong tests.test_khung_luoi_crm` (PYTHONPATH=`src;.;tests`).

**Tệp (≤ 3):** `app.js`, `khung_khai_bao.py`, `tests/test_khung_he_thong.py`.

**Báo cáo (≤ ¼ trang):** số bộ node đạt/tổng, số test, thông điệp commit `[E1-4u] vòng 3: …`.
