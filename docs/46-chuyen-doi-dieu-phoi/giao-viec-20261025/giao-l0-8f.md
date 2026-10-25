# L0-8f — Bản sao họ 03a: hợp đồng DEMO có đối tác (để chạy đủ ca PostgreSQL M4-03B)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2, §5). UTF-8 không BOM — **ghi tệp bằng UTF-8**. Worktree hiện tại, nhánh `lat/l0-8f` (từ `lat/l0-8e` = hop-nhat + L0-8d + L0-8e). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không khởi động PostgreSQL — **lead chạy test PG**.

**Hiện tượng (lead chạy thật 25/10 20:40, bộ chạy L0-8e):** `test_m4_03a_pg` 13/13 đạt; `test_trich6_host` 22/22. `test_m4_03b_common_pg`: **c01 FAIL** — `tests/test_m4_03b_common_pg.py:205` `assertIsNotNone(nt["doi_tac_id"], "đối tác resolve từ master.hop_dong — không từ body")`; vì c01 hỏng nên c02, c05, c07, c08, c10… skip dây chuyền ("ca trước chưa dựng …"); tổng 2 đạt / 1 FAIL / 15 skip. Báo cáo L0-8d đã cảnh báo: "producer hiện chưa gắn đối tác". c16 skip có chủ đích (không chèn giả lịch sử trước M0033) — giữ nguyên.

**Việc:**
1. Tìm vì sao hồ sơ do `ho_so_seal(...)` dựng trên bản sao 03a có `master.hop_dong` **không có đối tác**: test dựa vào dữ liệu nào (đối tác DEMO, ánh xạ mã Junsky đối tác `master.doi_tac_ma_junsky`, dự án, MST bên bán khớp hóa đơn G01 — xem `:269`, `:289`), và bản sao do Root dựng tay trước đây có gì mà `tools/pg_demo_ho_03a.py` hiện chưa seed.
2. Bổ sung seed trong `tools/pg_demo_ho_03a.py` bằng **đường chính thức** của dự án (hàm seed/dịch vụ có sẵn, actor DEMO), **chỉ dữ liệu DEMO**, để hợp đồng của hồ sơ test có đối tác DEMO đúng MST bên bán của hóa đơn fixture G01 (nếu test cần), không chèn giả lịch sử migration, không SQL vượt quyền.
3. Nếu gốc lỗi là **mã sản phẩm** (producer M4 đáng lẽ phải gắn đối tác) → **dừng, không sửa**, báo lead với tệp:dòng.
4. Test thuần trong `tests/test_chay_test_pg_demo.py`: seed 03a tạo đối tác/ánh xạ DEMO đúng một lần, không dữ liệu thật.

**File được sửa (≤ 2):** `tools/pg_demo_ho_03a.py`, `tests/test_chay_test_pg_demo.py`. Không xóa file, không sửa test M4 hay mã sản phẩm.
**Báo cáo cuối (≤ ⅓ trang):** gốc lỗi (tệp:dòng) · seed thêm gì · ca nào dự kiến còn skip và vì sao · thông điệp commit `[L0-8f] …`. Lead sẽ chạy `--pg-demo --module test_m4_03b_common_pg`.
