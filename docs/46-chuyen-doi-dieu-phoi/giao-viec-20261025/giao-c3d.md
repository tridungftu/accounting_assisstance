# C3d — Test PostgreSQL S1: có đợt thu quá hạn thật để kiểm che cờ theo quyền xem tiền (theo review-lat C3c)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM — **ghi tệp bằng UTF-8**. Worktree hiện tại, nhánh `lat/c3d` (từ hop-nhat, đã có C3 + C3c `k2/crm_s1.py`). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không khởi động PostgreSQL — **lead chạy ca PG**. Chỉ sửa **test**, không sửa mã sản phẩm.

**Vì sao (review Opus C3c):** dữ liệu PG trong `tests/test_crm_42_s1_http.py` chưa có hợp đồng hiệu lực có **đợt thu quá hạn**, nên ca `?co=QUA_HAN → 0` cho vai XEM và KT thiếu M1 (~:384-401) **vẫn đạt kể cả khi chưa có bản sửa C3c** — phép che cờ `qua_han` trong SQL (`k2/crm_s1.py` ~:146) mới chỉ được kiểm bằng so chuỗi.

**Việc (`tests/test_crm_42_s1_http.py`, ca PG):**
1. Dựng dữ liệu DEMO (qua đúng đường dịch vụ/hàm SQL có sẵn mà test đang dùng để tạo hợp đồng hiệu lực + lịch thu) cho **một hợp đồng hiệu lực ở PN_DEMO_A có một đợt còn phải thu đã quá hạn** so với ngày nghiệp vụ của test.
2. Kiểm: vai **Kế toán PN A** (có quyền xem tiền) thấy cờ `QUA_HAN` trên dòng đó, `?co=QUA_HAN` trả dòng đó, thẻ W5/quá hạn đếm đúng; vai **XEM** (không quyền xem tiền) **không** thấy cờ, `?co=QUA_HAN` → 0 dòng, không suy ra được qua `tong`/thẻ; **KT thiếu M1** như XEM.
3. Nếu dựng được gọn: một ca **trộn phạm vi** (người có quyền xem tiền ở PN A nhưng không ở PN B) — chỉ thấy cờ ở dòng PN A. Không gọn → ghi "để sau" trong báo cáo.
4. Thêm ca `?the=W5` cho XEM / KT thiếu M1 (không có số).

**File được sửa (chỉ 1):** `tests/test_crm_42_s1_http.py`. Không xóa file, không sửa mã sản phẩm.
**Test:** chạy thuần được thì chạy (`--module test_crm_42_s1_http` — ca PG sẽ skip khi thiếu DSN); lead chạy PG.
**Báo cáo cuối (≤ ⅓ trang):** dữ liệu dựng thêm · ca mới · thông điệp commit `[C3d] …`.
