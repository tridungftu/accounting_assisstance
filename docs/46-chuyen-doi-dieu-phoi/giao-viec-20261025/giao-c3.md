# C3 — CRM 42 · Read-model danh sách hợp đồng (S1): `GET /api/crm/hop-dong`

Bạn là worker Codex, chạy không tương tác. Thiết kế CRM 42 Anh đã chốt (20/10, 4 điểm §16) và Anh ra lệnh code mọi module đã chốt (24/10) qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/c3` (từ hop-nhat). Sandbox không ghi `.git`: **không commit**. Chạy Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>` (thiếu psycopg → test PG skip; ghi rõ).

**Căn cứ (đọc đúng mục):**
- `docs/CRM-42-00-MA-TRAN-MAN-HINH-VA-CA-KIEM.md`: dòng D1, D3 (bảng quyết định); **§ "S1 · Danh sách hợp đồng"** (~dòng 163–190: cột, lọc, ca S1-a, S1-b); bảng thẻ việc W1–W5 (~dòng 110–122).
- `docs/CRM-42-00-DELTA-DU-LIEU-API-QUYEN.md`: §1 hiện trạng (bảng/hàm có sẵn), §3.8 ô Junsky, §4 bảng route dòng `GET /api/crm/hop-dong?…` ("đọc · theo vai + scope · trang danh sách + thẻ số (W) · rỗng không lộ số").
**Dùng lại (không viết lại):** dữ liệu hợp đồng `master.hop_dong` + trạng thái giao kết CRM-G (`crm_giao_ket`), lịch thu `lich_thu`, phạm vi/quyền theo vai sẵn có (`ktt_danh_tinh`/`ktt_duoc`/`ktt_co_vai`, cách các route `crm_g.py` hiện kiểm phiên `crm_phien`), mẫu đọc trong `src/kho_tri_thuc/k2/crm.py` / `k2/crm_giao_ket.py` / `k2/crm_ky_ket.py`. Route đăng ký theo cách module mỏng `giao_dien/crm_g.py` đang làm.
**Việc cụ thể:**
1. Service đọc (mới hoặc trong `k2/crm.py`): danh sách hợp đồng trong **phạm vi của vai** (bán hàng: khách/dự án của mình — ca S1-a; KT/CFO theo pháp nhân) với các cột theo §S1 (số HĐ, khách, dự án/lô, trạng thái giao kết tiếng Việt, người phụ trách, giá trị, ngày…), lọc + phân trang theo §S1; **thẻ số W1–W5** đếm trong đúng phạm vi (rỗng thì 0 nhưng không lộ số ngoài phạm vi).
2. Ô "Công nợ ghi sổ Junsky" (D3): chưa có sổ → trả trạng thái **"chưa có sổ"** (không 0) — ca S1-b. Ô "Tình hình thu theo CRM" lấy từ lịch thu nếu đã có; không có → trạng thái rõ.
3. Route `GET /api/crm/hop-dong` (đọc, theo phiên + vai), tham số lọc/trang kiểm kiểu/độ dài; lỗi tiếng Việt + mã.
4. Nếu cần bảng/cột/hàm SQL mới → **dừng**, ghi vào báo cáo (khóa migration đang thuộc lát khác).
5. Test: `tests/test_crm_42_s1_tinh.py` (thuần/mock: phạm vi, thẻ số, "chưa có sổ", lọc, PII theo vai) và `tests/test_crm_42_s1_http.py` (theo mẫu test HTTP CRM-G hiện có, PG skip khi không có DSN).
**File được sửa/tạo (≤ 5):** service (mới hoặc `k2/crm.py`), `giao_dien/crm_g.py` (hoặc `server.py` chỉ một điểm dispatch), 2 test mới.
**Không làm:** giao diện S1/menu (lát C4), S2, báo cáo S9, đối chiếu Junsky thật, schema/migration, dữ liệu thật, xóa file.
**Test phải đạt:** `--module test_crm_42_s1_tinh --module test_crm_42_s1_http --module "test_crm_*"` — không mã lỗi mới so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json`.
**Báo cáo cuối (≤ 1 trang):** hợp đồng dữ liệu `GET /api/crm/hop-dong` (tham số, trường trả về, ví dụ JSON ngắn — lát C4 dùng) · cách tính phạm vi & thẻ W1–W5 (nguồn dữ liệu từng thẻ, thẻ nào chưa có dữ liệu thì ghi rõ) · test · thông điệp commit `[C3] …` · điểm cần lead/Anh.
