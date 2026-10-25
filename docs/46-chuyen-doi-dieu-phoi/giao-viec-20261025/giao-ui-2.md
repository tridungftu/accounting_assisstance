# UI-2 — Máy chủ khung lưới icon: khai báo module + `GET /api/khung/module/crm` (đã lọc quyền, đếm việc chờ)

Bạn là worker Codex, chạy không tương tác. Anh đã chốt (25/10, TL 49 `D:\Claude\Phan mem ho tro ke toan\49-trang-chu-luoi-icon.md` §1–§4; hộp thư CD-002): **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2, §4). UTF-8 — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/ui-2` (từ hop-nhat, đã có C3 `GET /api/crm/hop-dong`). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không mở server.

**Hợp đồng dữ liệu bắt buộc theo đúng:** `docs/46-chuyen-doi-dieu-phoi/HOP-DONG-DU-LIEU-KHUNG-LUOI.md` (lead chốt; UI-1 làm giao diện song song theo cùng tệp này).

**Việc:**
1. `src/kho_tri_thuc/giao_dien/khung_khai_bao.py` (mới): khai báo module CRM — 6 phần (TL 49 §2) và thẻ theo 4 vai, đúng dạng §1 của hợp đồng dữ liệu; quyền từng phần theo ma trận vai TL 42 §1 (đọc `D:\Claude\Phan mem ho tro ke toan\42-man-hinh-crm-ke-toan-va-giao-ket.md` §1) và mã kiểm quyền CRM hiện có (`ktt_duoc`/`ktt_co_vai`, cách `crm_g.py` kiểm phiên).
2. Route `GET /api/khung/module/<ma>` (đăng ký gọn trong `giao_dien/crm_g.py` hoặc một module mỏng mới nếu cách đăng ký route cho phép mà **không** sửa danh sách tài sản tĩnh của `server.py`): lọc phần/thẻ theo vai + module của người đăng nhập **ở máy chủ**; đếm `so_viec`/`qua_han` và số trên thẻ **bằng nguồn sẵn có** — thẻ W1–W5 của `k2/crm_s1.py` (C3: cùng phạm vi + quyền xem tiền QD-15/QD-22), báo giá nháp (`k2/crm_giao_ket.py`), mẫu chờ duyệt (`k2/crm_mau.py`)… Nguồn chưa có → bỏ thẻ/số đó, liệt kê trong báo cáo (không bịa số). `loc` của mỗi thẻ là đúng tham số danh sách cho ra cùng con số.
3. Người không có module CRM → `{"module":…, "the": [], "phan": [], "khong_quyen": true}`; lỗi CSDL → 503 có cấu trúc như route CRM khác.
4. Test `tests/test_khung_luoi_crm.py` (thuần/mock theo mẫu `tests/test_crm_42_s1_tinh.py`): 4 vai DEMO thấy đúng phần/thẻ TL 49 §2; người xem chỉ 3 phần; số thẻ = số danh sách lọc (gọi cùng service); `so_viec = 0` vẫn trả 0; không lộ thẻ ngoài vai; không trả mã kỹ thuật trong `ten`/`nhan`.

**File được sửa/tạo (≤ 4):** `giao_dien/khung_khai_bao.py` (mới), `giao_dien/crm_g.py` (chỉ thêm route gọn một khối) hoặc module route mỏng mới, `tests/test_khung_luoi_crm.py` (mới). Không sửa `server.py`, `crm_g.js`, `app.js`, `index.html`, `style.css` (UI-1 làm); không xóa file.
**Test phải đạt:** test mới + `--module "test_crm_*"` không thêm mã lỗi so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json`.
**Báo cáo cuối (≤ ½ trang):** ví dụ JSON thật từ test cho 4 vai · nguồn đếm từng thẻ/phần (thẻ nào bỏ vì chưa có nguồn) · test · thông điệp commit `[UI-2] …`.
