# M2h — M2-00 · nút "Tải tất cả công ty" (xếp hàng tuần tự) — ca M2-00-02

Bạn là worker Codex, chạy không tương tác. Anh đã chốt thiết kế M2-00 (TL 43) và ra lệnh code mọi module đã chốt: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/m2h` (từ hop-nhat). Sandbox không ghi `.git`: **không commit**. Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>`; node nếu có.

**Căn cứ:** `D:\Claude\Phan mem ho tro ke toan\43-M2-00-nhan-nguon-tu-cong-thue.md` dòng ~43 (profile theo pháp nhân; "Tải tất cả công ty, kỳ X" xếp hàng tuần tự), ~60 (hộp chọn: pháp nhân có quyền theo K5, kỳ, chiều, định dạng; "Tải tất cả công ty"), ~144 (ca **M2-00-02**: hai pháp nhân, hai profile, đúng tài khoản/thư mục/hồ sơ riêng; chạy tuần tự, không chồng job).
**Dùng lại (đã có trên hop-nhat, lát M2e):** `src/kho_tri_thuc/giao_dien/m2_tai_hoa_don.py` (route mỏng "Tải từ cổng thuế", kiểm quyền theo pháp nhân, gọi RPC bộ tải `/api/profiles|start|status|reconcile|events`) và `src/kho_tri_thuc/giao_dien/assets/m2_tai_hoa_don.js`; test M2e hiện có (`tests/test_m2*tai*` hoặc tương đương — tìm theo tên route) và **bộ tải giả** test đang dùng. **Không viết lại** route/hộp chọn; chỉ thêm hàng đợi.

**Việc:**
1. Máy chủ: lệnh "tải tất cả" nhận kỳ + chiều + định dạng, lấy **đúng các pháp nhân người dùng có quyền** (cùng hàm kiểm quyền M2e) có profile, tạo **hàng đợi tuần tự**: chỉ một job chạy tại một thời điểm; job sau bắt đầu khi job trước kết thúc (xong/lỗi/hủy); lỗi một pháp nhân không chặn các pháp nhân sau; trạng thái từng dòng (Chờ / Đang tải / Xong / Lỗi — lý do tiếng Việt); không chạy hai hàng đợi chồng nhau (lần bấm thứ hai khi đang chạy → báo "đang có hàng đợi").
2. Màn hình: trong hộp "Tải từ cổng thuế" thêm nút **"Tải tất cả công ty"** + bảng tiến độ theo pháp nhân (tên pháp nhân, không mã kỹ thuật).
3. Test (dùng bộ tải giả, **không** gọi cổng thuế thật, không mạng): ca M2-00-02 — hai pháp nhân → hai job tuần tự, đúng profile/thư mục từng pháp nhân, không chồng; pháp nhân không có quyền bị loại; lỗi giữa chừng → pháp nhân sau vẫn chạy; bấm lần hai bị từ chối.

**File được sửa/tạo (≤ 4):** `giao_dien/m2_tai_hoa_don.py`, `giao_dien/assets/m2_tai_hoa_don.js`, một test Python mới `tests/test_m2_tai_tat_ca.py` (+ test node nếu mẫu M2e có).
**Không làm:** gọi cổng thuế thật, đọc `.env`, sửa `server.py`/`app.js`/`index.html` (nếu bắt buộc phải sửa → dừng, ghi báo cáo), migration, dữ liệu thật, xóa file.
**Test phải đạt:** test mới + test M2e hiện có + `--module "test_m2*"` không thêm mã lỗi so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json`.
**Báo cáo cuối (≤ ½ trang):** cách xếp hàng (file:dòng) · bằng chứng không chồng job · test · file đã sửa · thông điệp commit `[M2h] …`.
