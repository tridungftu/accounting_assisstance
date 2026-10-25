# T-NEN-a — Test M4 còn ghim số migration / ghim byte helper sau L0-8f

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2: không xóa file). UTF-8 không BOM. Worktree hiện tại (từ hop-nhat `f62c36a`, nền PG v2 — `docs/46-chuyen-doi-dieu-phoi/NEN-TEST-PG.md` mục cuối, `nen-test-hop-nhat-pg-v2.json`). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không khởi động PostgreSQL — lead chạy PG. **Chỉ sửa test**, không sửa mã sản phẩm; không nới assert để đạt giả.

**Việc:**
1. `tests/test_m4_02b_k2.py::test_k01_dung_ho_so` (AssertionError 33 != 22) và `tests/test_m4_02c_pg.py` `setUpClass` ("schema/registry không phải 24 với M0024 cuối"): bỏ ghim **tổng** số migration; kiểm migration cần thiết (M0022 / M0024) đã áp và đúng checksum, lịch sử trước đó nguyên vẹn (mẫu: T-M4a đã làm cho `test_m4_review_k2`, T-MIG2 cho `test_crm_k2`).
2. Ghim nguyên byte helper `tests/test_m4_02c_pg.py` trong `tests/test_m4_03a_m26_integration.py` và `tests/test_m4_04c_m27_integration.py` (`test_helper_m4_02c_pg_nguyen_byte`): cập nhật SHA theo **bản cuối** của `test_m4_02c_pg.py` (sau bước 1), ghi chú lý do (L0-8f thêm `gan_doi_tac` tùy chọn; T-NEN-a bỏ ghim tổng).
**File (≤ 4, đều là test):** `tests/test_m4_02b_k2.py`, `tests/test_m4_02c_pg.py`, `tests/test_m4_03a_m26_integration.py`, `tests/test_m4_04c_m27_integration.py`.
**Báo cáo (≤ ⅓ trang):** sửa ở file:dòng · SHA mới · thông điệp commit `[T-NEN-a] …`.
