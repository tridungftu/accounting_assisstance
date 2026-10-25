# DA-1 vòng 2 — sửa 3 điểm review (CRM · Dự án đang bán, máy chủ)

Bạn là worker Codex, chạy không tương tác. Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/da-1` (commit `b9adfe7`). Sandbox không ghi `.git`: **không commit**. Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module test_crm_du_an_ban` (thiếu psycopg → test PG skip; **lead chạy PG sau**, bạn không mở DEMO, không nối CSDL).

**Đầu vào:** review vòng 1 (nguyên văn): `C:\Users\Admin\AppData\Local\Temp\claude\D--Claude-Phan-mem-ho-tro-ke-toan-Ph-n-m-m-kho-tri-th-c\c7ce96c2-538a-4331-bac6-4382c44a8688\scratchpad\bao-cao-review-da-1.md`. Thiết kế: `docs/46-chuyen-doi-dieu-phoi/THIET-KE-DU-AN-DANG-BAN.md`; quyết định QD-20261025-07 (ghi chỉ BAN_HANG/KE_TOAN/KE_TOAN_TRUONG có module CRM).

**Việc (chỉ 3 điểm này):**
1. **Chặn #1** `k2/sql_crm_du_an_ban.py:196`: bỏ nhánh `OR … CRM_DU_AN_BAN` cho phép người XEM có phân công được ghi; quyền ghi **bắt buộc** thuộc một trong ba vai trên + module CRM + đúng pháp nhân của dự án. Thêm ca test: XEM có phân công vẫn bị từ chối (thuần/mock + ca PG viết sẵn).
2. **Nên sửa #2** `sql_crm_du_an_ban.py:518` (+ service/route tương ứng): cập nhật tiến độ G7 áp dụng ngay nhận **phiên bản mong đợi** (vd `expected_version`), kiểm sau khi khóa bộ chuẩn; bản đã đổi → lỗi xung đột (HTTP 409, mã theo mẫu `CRM_DA_PHIEN_BAN_CU`). Test hai người cùng sửa từ bản cũ.
3. **Nên sửa #3** `giao_dien/crm_g.py:675` (`_chi_query`, chỉ khối `_dieu_huong_da`): kiểm trên query **thô** (`parse_qs(..., keep_blank_values=True)`): mỗi khóa xuất hiện tối đa 1 lần, giá trị rỗng bị từ chối khi không hợp lệ, giới hạn độ dài (vd số ≤ 9 chữ số, uuid đúng 36 ký tự). Test biên: `?dang_ban=1&dang_ban=` → 400; `phien_ban` = 1.000 số 0 + "1" → 400.

**File được sửa (chỉ các file này):** `src/kho_tri_thuc/k2/sql_crm_du_an_ban.py`, `src/kho_tri_thuc/k2/crm_du_an_ban.py`, `src/kho_tri_thuc/giao_dien/crm_g.py` (chỉ khối `_dieu_huong_da`), `tests/test_crm_du_an_ban.py`, `tests/test_crm_du_an_ban_pg.py`. **Không** sửa `pg_migrations.py` (M0031 đọc SQL từ `sql_crm_du_an_ban.py`), không đụng phần khác của `crm_g.py`, không xóa file, không dữ liệu thật.
**Test phải đạt:** `--module test_crm_du_an_ban --module "test_crm_*"` không thêm mã lỗi so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json` (ghi rõ ca PG đã viết nhưng skip).
**Báo cáo cuối (≤ ½ trang):** từng điểm 1–3: sửa ở file:dòng nào, ca test nào · danh sách file đã sửa · test đạt/tổng · thông điệp commit `[DA-1] vòng 2: …`.
