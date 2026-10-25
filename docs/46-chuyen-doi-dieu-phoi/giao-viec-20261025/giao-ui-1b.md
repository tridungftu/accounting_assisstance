# UI-1b — Trang chủ CRM lần tải đầu báo "Phiên CRM chưa có" (lead thử DEMO 8798, 25/10)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§4: giao diện tiếng Việt). UTF-8 không BOM — **ghi tệp bằng UTF-8** (chữ tiếng Việt không được thành `?`). Worktree hiện tại, nhánh `lat/ui-1` (khung lưới icon UI-1, đã có UI-2/UI-2b). Sandbox không ghi `.git`: **không commit**. Không mở server.

**Hiện tượng:** mở `#crm` lần đầu (phiên trình duyệt mới) → trang chủ khung hiện "Chưa tải được trang chủ … Phiên CRM chưa có hoặc đã hết — tải lại trang để nhận phiên mới"; bấm "Thử lại" thì tải đúng. Gốc: `GET /api/crm` (`crmLoad`, `src/kho_tri_thuc/giao_dien/assets/app.js` ~:614-618) là nơi **cấp** phiên CRM (`server.py` `crm_phien(..., tao=True)` ~:196-205), còn `GET /api/khung/module/crm` chỉ **đọc** phiên (`khung_khai_bao.py` ~:174, `tao=False` → `CRM_PHIEN`). Lần đầu hai GET chạy song song nên khung đến trước khi có phiên.

**Việc (chỉ phía giao diện, `app.js` khối UI-1):**
1. `khungTaiModule` (~:1750): khi lỗi là thiếu phiên CRM (mã `CRM_PHIEN` — đọc đúng mã máy chủ trả, không so chuỗi thông báo), **chờ một lần nạp CRM** (`crmLoad()` hoặc promise phiên đang chạy) rồi thử lại **đúng một lần**; vẫn lỗi → hiện thông báo như cũ. Không vòng lặp, không chặn đổi vai (`vaiDangChan`), giữ cơ chế epoch/gen chống phản hồi cũ.
2. Test node `tests/khung_luoi_async.cjs`: ca "lần đầu khung trả CRM_PHIEN, sau `/api/crm` thì đạt" → trang chủ hiện thẻ/icon, chỉ 1 lần thử lại; ca "vẫn CRM_PHIEN sau khi thử lại" → thông báo tiếng Việt + nút Thử lại.

**Lưu ý:** tệp `tests/fixtures/*` và `m4/review_goc/*` có thể hiện "đã sửa" do server DEMO 8798 đồng bộ — không đụng.
**File được sửa (chỉ 2):** `src/kho_tri_thuc/giao_dien/assets/app.js`, `tests/khung_luoi_async.cjs`. Không sửa máy chủ, không xóa file.
**Test:** `node tests/khung_luoi_async.cjs` + các bộ node CRM khác vẫn như nền (8 bộ lỗi có sẵn: crm_doi_chieu_async, crm_ky_ket_async, m2_00a_source7_fix02, m2_00b_source7_rpc, m4_02c_dto_ui_async, m4_03a_async, m4_03a_gui_fix02_async, m4_04b_request_async).
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · ca test · thông điệp commit `[UI-1b] …`.
