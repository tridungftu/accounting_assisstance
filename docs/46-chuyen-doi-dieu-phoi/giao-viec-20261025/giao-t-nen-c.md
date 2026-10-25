# T-NEN-c — Điều tra 2 nhóm lỗi mới của nền PG v2

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2: không xóa file). UTF-8 không BOM. Worktree hiện tại (từ hop-nhat `f62c36a`, nền PG v2 — `docs/46-chuyen-doi-dieu-phoi/NEN-TEST-PG.md` mục cuối, `nen-test-hop-nhat-pg-v2.json`). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không khởi động PostgreSQL — lead chạy PG. **Chỉ sửa test**, không sửa mã sản phẩm; không nới assert để đạt giả.

1. `tests/test_m4_master_dung_chung_pg.py::test_g02_tu_choi_huy_loai_pn_du_an_quyen_khong_ghi (ca='DTO')`: `TypeError: dict() got multiple values for keyword argument 'expected_master'` (đã thấy từ lần chạy 19:36 trên nhánh M4-5a). Tìm commit/thay đổi gây lỗi (git log/diff các tệp liên quan: helper test, `k2`/`m4` master dùng chung), sửa **nếu là test**; nếu do mã sản phẩm → dừng, báo lead tệp:dòng + commit gây ra.
2. `tests/test_source6_lazy_excel.py` ×3 (`TestRuleOnlyBlockedSubprocess`): "SETUP NOT_VERIFIED (baseline/bố cục): thư mục chứa tests/tools phải là 'files' của bố cục đóng băng" — tìm vì sao chạy dưới bộ chạy (`tools/chay_test_theo_module.py`, runtime DEMO) thì bố cục không đúng; có trong nền v4 (không PG) không (`nen-test-hop-nhat-v4.json`). Sửa nếu là test/bộ chạy trong phạm vi; không thì báo.
**File (≤ 3):** chỉ tệp test liên quan (+ `tools/chay_test_theo_module.py` nếu gốc ở bộ chạy — ghi lý do). Không sửa mã sản phẩm.
**Báo cáo (≤ ½ trang):** gốc từng lỗi (tệp:dòng, commit) · sửa · thông điệp commit `[T-NEN-c] …`.
