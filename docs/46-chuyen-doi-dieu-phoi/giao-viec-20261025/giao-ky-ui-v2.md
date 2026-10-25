# KY-UI vòng 2 — sửa 1 bộ node bị lỗi do đổi nhãn nút

Bạn là worker Codex, chạy không tương tác. Đọc `docs\46-chuyen-doi-dieu-phoi\giao-viec-20261025\giao-ky-ui.md` và báo cáo `bao-cao-ky-ui.md`: sau KY-UI, `tests/crm_giao_ket_async.cjs` ~:842 còn tìm nút "Xuất DOCX" (nhãn mới "Xuất hợp đồng (DOCX)") → bộ giao kết lỗi. **Làm ngay, không hỏi lại.** UTF-8 không BOM. Worktree hiện tại, nhánh `lat/ky-ui`. Sandbox không ghi `.git`: **không commit**. Không mở server.
Việc: sửa **test** `tests/crm_giao_ket_async.cjs` tìm theo nhãn mới (rà cả tệp mọi chuỗi/nhãn cũ KY-UI đã đổi: "DOCX + PDF", "Chờ ký (đã xuất DOCX+PDF)", "In báo giá (PDF)" nếu bị đổi…), giữ nguyên ý mọi ca, không xóa assert. Không sửa `crm_g.js` trừ khi phát hiện lỗi thật (khi đó báo rõ).
**File (≤ 1–2):** `tests/crm_giao_ket_async.cjs` (+ `crm_g.js` chỉ khi lỗi thật). Không xóa file.
**Chạy node:** `node tests/crm_giao_ket_async.cjs`, `node tests/crm_ky_ket_async.cjs`, `node tests/crm_du_an_ban_async.cjs`, `node tests/khung_luoi_async.cjs` — cả 4 phải đạt; 20 bộ: không thêm bộ lỗi so với trước KY-UI (7 bộ lỗi nền).
**Báo cáo (≤ 6 dòng):** sửa ở file:dòng · số test · thông điệp commit `[KY-UI] vòng 2: …`.
