# M2s — M2-00 · seed DEMO: vai đủ quyền tải + nhận hóa đơn trên cùng pháp nhân

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM — **ghi tệp bằng UTF-8**. Worktree hiện tại, nhánh `lat/m2s` (từ hop-nhat). Sandbox không ghi `.git`: **không commit**. Không nối CSDL (lead chạy seed thật trên CSDL DEMO riêng sau).

**Vấn đề (ghi chú lead sau M2e):** seed DEMO **chưa có vai** có đủ `INTAKE` + `READ_SOURCE` + `M2_READ` (hoặc tên tương đương trong K5) **trên cùng một pháp nhân** → trên DEMO không ai vừa bấm "Tải từ cổng thuế" vừa nhận và xem hóa đơn được, nên không thử trọn luồng M2-00.
**Dùng lại:** nơi seed vai/phân công DEMO hiện có (tìm trong `tools/chuan_bi_crm_demo.py`, `k2/m4_demo.py` hoặc seed M2 DEMO — theo mẫu đang cấp vai `MO_PHONG_*`), hàm kiểm quyền M2e trong `giao_dien/m2_tai_hoa_don.py` (để biết đúng tên quyền cần).

**Việc:**
1. Xác định đúng tập quyền/module mà luồng M2-00 cần (tải, nhận, xem hóa đơn) từ mã kiểm quyền hiện có — không đoán.
2. Seed DEMO thêm **một** người dùng mô phỏng (tiền tố `MO_PHONG_`, vd `MO_PHONG_KT_M2_A`) có đủ các quyền đó trên **Pháp nhân DEMO A**; seed chạy lại không tạo trùng (idempotent); không đổi quyền người dùng mô phỏng khác.
2b. Nếu giao diện có danh sách đổi vai mô phỏng: người dùng mới xuất hiện với nhãn tiếng Việt ("Kế toán M2 (mô phỏng)").
3. Test thuần: seed gọi đúng hàm cấp quyền với đúng tập quyền, idempotent (mock DB theo mẫu test seed hiện có).

**File được sửa/tạo (≤ 3):** tệp seed DEMO liên quan + 1 test. Cần migration → **dừng**, ghi báo cáo.
**Không làm:** dữ liệu thật, quyền cho người dùng thật, xóa file.
**Báo cáo cuối (≤ ⅓ trang):** tập quyền cần (nguồn file:dòng) · người dùng seed · test · thông điệp commit `[M2s] …`.
