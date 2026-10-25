# MDA-4c — Danh sách hợp đồng: cột "Đợt kế tiếp" hiện "dự kiến dd/mm/yyyy" cho đợt gắn mốc riêng chưa có ngày thực tế (CD-007 mục 2)

Bạn là worker Codex, chạy không tương tác. Căn cứ: **CD-007** mục 2 (chưa có ngày thực tế → đợt gắn mốc hiện "dự kiến dd/mm/yyyy" ở Danh sách hợp đồng — cột Đợt kế tiếp; không đếm quá hạn); máy chủ MDA-4a (`src/kho_tri_thuc/k2/crm_s1.py`): `dot_ke_tiep` có `trang_thai` `CO_NGAY` / `MOC_DU_KIEN` (kèm `han_du_kien`) / `MOC_CHUA_CO_NGAY`. **Làm ngay, không hỏi lại.** UTF-8 không BOM — ghi tệp bằng UTF-8. Worktree hiện tại, nhánh `lat/mda-4c` (dòng giao diện `lat/ui-dem`). Sandbox không ghi `.git`: **không commit**. Không mở server.

**Việc — `src/kho_tri_thuc/giao_dien/assets/app.js`:** mọi nơi hiện "Đợt kế tiếp" của danh sách hợp đồng (khối khung CRM `loc.hop_dong.dong` ~:2020–2030 đang ghi `hạn dd/mm/yyyy` / "chưa có ngày", và bảng danh sách hợp đồng của màn Hợp đồng nếu có cột tương tự — tìm `dot_ke_tiep`): `CO_NGAY` → "Đợt N · hạn dd/mm/yyyy" (như cũ); `MOC_DU_KIEN` → "Đợt N · **dự kiến** dd/mm/yyyy" (từ `han_du_kien`, kiểu chữ khác "hạn", ví dụ nghiêng/mờ, không màu đỏ); `MOC_CHUA_CO_NGAY` → "Đợt N · chưa có ngày". Không đổi logic quá hạn (máy chủ quyết).
**Test:** node (`tests/khung_luoi_async.cjs` hoặc bộ node danh sách hợp đồng có sẵn — tìm theo `dot_ke_tiep`): 3 trạng thái hiện đúng chữ, ngày dd/mm/yyyy, không chuỗi `MOC_`.
**File (≤ 2):** `app.js`, 1 tệp test node. Không sửa máy chủ. Không xóa file.
**Chạy node:** bộ đã sửa + `node tests/crm_giao_ket_async.cjs`, `node tests/crm_du_an_ban_async.cjs` (+ 20 bộ: lỗi nền như trước) — ghi số trước/sau.
**Báo cáo (≤ ¼ trang):** sửa ở file:dòng · node trước/sau · thông điệp commit `[MDA-4c] …`.
