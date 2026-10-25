# BG-e6u — Màn CRM không hiện login/mã vai (BG-22, review cụm Báo giá điểm 2)

Bạn là worker Codex, chạy không tương tác. Căn cứ: **CD-005** mục 5 (BG-22); review cụm Báo giá điểm 2: `crm_g.js` ~:1843 (màn Báo giá) hiện "Vai hiện hành: MO_PHONG_… (…)", ~:733 (màn Mẫu hợp đồng) hiện `dang_nhap (vai_tro)` nguyên mã; `VAI_VN.DU_AN` là "Dự án" còn `app.js` là "Phụ trách dự án". **Làm ngay, không hỏi lại.** UTF-8 không BOM — ghi tệp bằng UTF-8. Worktree hiện tại, nhánh `lat/bg-e6u` (`lat/ui-dem`). Sandbox không ghi `.git`: **không commit**. Không mở server.

**Việc — `src/kho_tri_thuc/giao_dien/assets/crm_g.js`:** hai dòng vai hiện hành chỉ hiện **tên vai tiếng Việt** (`VAI_VN`) — và tên pháp nhân nếu dữ liệu máy chủ của màn có sẵn trường tên hiển thị (không có thì bỏ, **không** hiện login, không hiện mã vai): vd "Vai hiện hành: Bán hàng · đổi vai ở mục Vai mô phỏng phía trên." `VAI_VN.DU_AN` → "Phụ trách dự án"; vai lạ → "Vai mô phỏng". Rà toàn `crm_g.js` mọi chỗ khác in `dang_nhap`/`vai_tro` thô ra màn hình (nêu số chỗ đã sửa); nhật ký/lịch sử hiện người thao tác thì giữ nguyên (đó là dữ liệu, không phải nhãn vai).
**Test — `tests/crm_giao_ket_async.cjs`:** màn Báo giá và màn Mẫu hợp đồng với vai `MO_PHONG_CRM_G_BH_A`/`BAN_HANG` → DOM không chứa `MO_PHONG_` hay `BAN_HANG`, có "Bán hàng"; vai `DU_AN` → "Phụ trách dự án".
**File (≤ 2):** `crm_g.js`, `tests/crm_giao_ket_async.cjs`. Không xóa file.
**Chạy node:** `node tests/crm_giao_ket_async.cjs`, `node tests/crm_du_an_ban_async.cjs`, `node tests/khung_luoi_async.cjs` (+ 20 bộ: 8 bộ lỗi nền như handoff BG-e3, trừ `crm_ky_ket_async` nay phải đạt) — ghi số trước/sau.
**Báo cáo (≤ ¼ trang):** sửa ở file:dòng · node trước/sau · thông điệp commit `[BG-e6u] …`.
