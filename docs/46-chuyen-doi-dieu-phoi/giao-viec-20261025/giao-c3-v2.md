# C3 vòng 2 — sửa theo review Claude (CRM 42 · S1 `GET /api/crm/hop-dong`)

Bạn là worker Codex, chạy không tương tác. Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/c3` (commit vòng 1 `5138079`). Sandbox không ghi `.git`: **không commit**. Python: `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 tools/chay_test_theo_module.py . --module <tên>` (thiếu psycopg → test PG skip; lead chạy PG sau).

**Đầu vào:** review vòng 1 (nguyên văn) `C:\Users\Admin\AppData\Local\Temp\claude\D--Claude-Phan-mem-ho-tro-ke-toan-Ph-n-m-m-kho-tri-th-c\c7ce96c2-538a-4331-bac6-4382c44a8688\scratchpad\review-c3-v1.md`; quyết định lead `docs/QUYET-DINH.md` **QD-20261025-15**.

**Việc:**
1. **#4 quyền xem tiền (QD-20261025-15):** ô tiền (giá trị HĐ, thu theo CRM, công nợ Junsky) chỉ trả cho người có `XEM_TIEN` trên pháp nhân của dòng (dùng `quyen.pham_vi(dt, "XEM_TIEN")` như `k2/crm.py:794`) hoặc bán hàng trong phạm vi binding của mình; còn lại trả `null` + cờ/nhãn "không có quyền xem tiền". Thẻ W5 (tiền đến hạn) theo cùng quy tắc.
2. **#5 tải:** đẩy lọc pháp nhân, loại, dự án, ngày, trạng thái gốc vào CTE phạm vi; tách hai bước — thẻ/đếm bằng cột rẻ, phần nặng (lịch, G5, Junsky) chỉ cho các dòng của trang (≤ 100); Junsky tính một lần (CTE `DISTINCT ON`). Không giữ `mutation_lock` lâu hơn cần (đọc REPEATABLE READ READ ONLY như hiện tại).
3. **#8:** `dich_vu_s1` bắt `DataError` như `dich_vu` (→ 503 có cấu trúc); thiếu module CRM → 200 rỗng **kèm** `khong_quyen: true` như mẫu `crm_state`; test không dùng `patcher.temp_original`.
4. **#2 test:** ca PG dương cho bán hàng (dùng lại `cap_phan_cong`/`cap_pham_vi` của `tests/test_crm_ky_ket_http.py:149-160`): BH có binding thấy đúng HĐ mình + thẻ đúng; BH thứ hai cùng pháp nhân không binding thấy 0; cùng pháp nhân khác dự án/khách bị ẩn; vai XEM nhận tiền `null`; JSON thật không có CCCD/STK/`du_lieu`; ca **có sổ** Junsky (nạp `kho.cong_no_mo` DEMO: ngày chụp mới nhất, `con_lai` NULL, hai HĐ cùng khách). Ca thuần/mock tương ứng cho 1 và 3.
5. **#7 (nhỏ):** trả kèm đơn vị của từng thẻ (`don_vi: "hop_dong" | "dot"`) để C4 hiện đúng.
6. Không làm #3 (lát C3b, chờ Anh) và #6 (ghi chú cho C4) — chỉ thêm một dòng docstring "không cộng cột Junsky giữa các HĐ (số dư cấp khách)".

**File được sửa:** `src/kho_tri_thuc/k2/crm_s1.py`, `giao_dien/crm_g.py` (chỉ khối route S1), `tests/test_crm_42_s1_tinh.py`, `tests/test_crm_42_s1_http.py`. **Không làm:** schema/migration, giao diện, dữ liệu thật, xóa file.
**Test phải đạt:** `--module test_crm_42_s1_tinh --module test_crm_42_s1_http --module "test_crm_*"` — không mã lỗi mới so với `docs/46-chuyen-doi-dieu-phoi/nen-test-hop-nhat-v4.json` (ghi rõ ca PG đã viết nhưng skip).
**Báo cáo cuối (≤ 1 trang):** từng điểm 1–5: sửa thế nào / ca test · contract JSON đổi gì so với vòng 1 (C4 dùng) · test đạt/tổng · thông điệp commit `[C3] vòng 2: …`.
