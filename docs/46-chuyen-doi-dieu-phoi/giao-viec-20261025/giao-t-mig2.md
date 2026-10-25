# T-MIG2 — Sửa nốt test PostgreSQL hỏng do giả định cũ (sau khi gắn G5 M0032)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM — **ghi tệp bằng UTF-8**. Worktree hiện tại, nhánh `lat/t-mig2` (từ hop-nhat, đã có M0032 + T-MIG). Sandbox không ghi `.git`: **không commit**. Không nối CSDL — lead chạy `--pg-demo` sau. Chỉ sửa **test**.

**Kết quả lead chạy thật `--pg-demo` (25/10, chuỗi 32 migration):**
1. `test_crm_kiem_hd`, `test_crm_kiem_hd_http`, `test_crm_doi_chieu_pg`, `test_crm_g6a_m25_integration`: `NOT_VERIFIED: không kiểm được bản sao (UndefinedObject)` — từ hàm kiểm bản sao (vd `tests/test_crm_kiem_hd.py:~105-112`): câu SQL `SELECT array_agg(a) FROM unnest(%s::text[]) a WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = a) AND pg_has_role(current_user, a, 'MEMBER')` — PostgreSQL **không bảo đảm thứ tự** AND nên `pg_has_role` có thể chạy với vai chưa tồn tại → `UndefinedObject`. Sửa bằng `CASE WHEN EXISTS(...) THEN pg_has_role(...) ELSE false END` (hoặc JOIN `pg_roles` trước). Tìm **mọi bản sao** của hàm kiểm này trong `tests/` (các test G6A/G5 có thể có bản riêng) và sửa cùng cách.
2. `test_crm_k2`: `Tuples differ: (32, 32, 32) != (13, 13, 13)`; `test_crm_ky_ket`: `32 != 23` — còn ghim tổng migration (T-MIG chưa phủ) → đổi sang "có mặt đúng một lần ở vị trí đã chốt + checksum prefix", không ghim tổng (như T-MIG đã làm cho 7 tệp khác).
3. `test_crm_giao_ket_http.test_g04_usd_fx_g7` (`:298`): `a["tinh"]` là `None` — đọc kỹ: nếu do quy tắc Báo giá đã đổi ở BG-1c (Tổng VND = đơn giá × tỷ giá × diện tích; tỷ giá mặc định trong cấu hình; `fx.nguoi_nhap`…) thì cập nhật kỳ vọng theo hợp đồng mới (đọc `docs/QUYET-DINH.md` QD-20261025-01…04, `k2/crm_giao_ket.py`); nếu là lỗi sản phẩm → **không sửa**, ghi báo cáo với lý do.
4. `test_pg_schema` (`1 != 0`, mã thoát công cụ chuyển SQLite → PostgreSQL): **không sửa**, chỉ ghi nhận.

**File được sửa:** chỉ các tệp `tests/test_*.py` liên quan (≤ 8). Không sửa mã sản phẩm, fixture, migration; không xóa file.
**Test phải đạt (không PG):** các module trên không thêm mã lỗi so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json`.
**Báo cáo cuối (≤ ½ trang):** từng tệp sửa gì · điểm 3 kết luận (test cũ hay lỗi sản phẩm) · thông điệp commit `[T-MIG2] …`.
