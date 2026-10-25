# M4-6 — M4 · Nghiệm thu & chi phí dự án · 04 Request nháp: nối route vào máy chủ (giữ CHUA_CAU_HINH, không gọi Request thật)

Bạn là worker Codex, chạy không tương tác. Anh đã chốt kế hoạch M4 (20/10) và ra lệnh code mọi module đã chốt (24/10) qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/m4-6` (từ hop-nhat). Sandbox không ghi `.git`: **không commit**. Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`.

**Hiện trạng (lead đã kiểm):** domain + SQL + route mỏng + widget đã có trên hop-nhat: `m4/request_nhap.py`, `m4/request_api.py`, `m4/sql_request_nhap.py` (M0027), `giao_dien/m4_request.py` (`dieu_huong`, docstring mô tả đúng seam), `m4/giao_dien/m4_request_nhap.js`, `giao_dien/m4.py:391` phục vụ widget. **Thiếu đúng phần nối trong máy chủ:** `tests/test_m4_04b_request_wiring_http.py` 3 đạt / **13 ERROR** `AttributeError: 'LocalApp' object has no attribute 'go_request_nhap'` (nằm trong nền v4). Gói gốc `luu/m4-04b-request-wiring-20261023-01` chỉ có `m4_request.py` + test, không có phần `server.py`.
**Dùng lại:** docstring đầu `giao_dien/m4_request.py` (3 route, seam `app._m4_request = {"cau_hinh", "transport"}`, vắng → 503 `CHUA_CAU_HINH` sau kiểm quyền, chạy ngoài mutation lock trên kết nối riêng); cách `server.Handler.handle_route` đang chuyển các module mỏng khác (vd `crm_g`, `m2_tai_hoa_don`); test và `tests/m4_04b_request_async.cjs` là đặc tả.
**Việc cụ thể:**
1. `server.LocalApp.gan_request_nhap(cau_hinh, transport)` và `go_request_nhap()` (gỡ, về mặc định vắng = CHUA_CAU_HINH); mặc định khi khởi động: **vắng** — không đọc env/khóa, không tạo transport thật.
2. `Handler.handle_route`: chuyển **đúng ba route** `/api/m4-request…` vào `m4_request.dieu_huong` **trước** dispatcher `/api/m4*` chung; cùng token/phiên/cookie như route M4 khác.
3. Không đổi domain/SQL/widget; nếu test đòi đổi chỗ khác ngoài `server.py` → làm tối thiểu và ghi rõ.
**File được sửa (≤ 2):** `src/kho_tri_thuc/giao_dien/server.py` (+ `giao_dien/m4_request.py` chỉ nếu bắt buộc).
**Không làm:** gọi Request thật/mạng, cấu hình khóa thật, đọc `.env`, migration, dữ liệu thật, xóa file.
**Test phải đạt:** `--module test_m4_04b_request_wiring_http --module "test_m4_request*" --module "test_m4_*" --module test_server* ` — `test_m4_04b_request_wiring_http` 0 ERROR; không mã lỗi mới so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json`. `node tests/m4_04b_request_async.cjs` nếu có node (không có → ghi NOT_VERIFIED).
**Báo cáo cuối (≤ 1 trang):** seam + điểm chuyển route (file:dòng) · bằng chứng không gọi mạng khi vắng cấu hình · test trước/sau · thông điệp commit `[M4-6] …`.
