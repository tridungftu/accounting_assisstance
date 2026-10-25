# PDF-1 vòng 2 — 2 test ở test_crm_giao_ket.py còn chờ lý do của đường Word

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Cùng quy tắc `giao-pdf-1.md` (UTF-8 không BOM; không commit; không nối CSDL; không khởi chạy Word). Worktree hiện tại, nhánh `lat/t-pdf` (đã có T-PDF + PDF-1 6767cde).

**Lead chạy PG (25/10 21:58):** 2 mã lỗi mới do công tắc mặc định TẮT (QD-20261025-26): `tests/test_crm_giao_ket.py::NhaCungCapPdf::test_thieu_word_khong_spawn_giu_docx` và `::WordThat::test_qua_han_trung_thuc` — `('PDF_CHUA_SAN_SANG', 'PDF_XUAT_TAY') != ('PDF_CHUA_SAN_SANG', 'WORD_…')`. Hai test này kiểm **đường Word** → trong test phải **bật công tắc** (`KHO_CRM_WORD_PDF=1` bằng `patch.dict(os.environ, …)` cho riêng ca đó) để giữ nguyên ý kiểm cũ; thêm (nếu chưa có ở test này) một ca mặc định tắt → `PDF_XUAT_TAY`, không tạo tiến trình.
**File (chỉ 1):** `tests/test_crm_giao_ket.py`. Không sửa mã sản phẩm.
**Báo cáo (≤ 5 dòng):** sửa ở file:dòng · thông điệp commit `[PDF-1] vòng 2: …`.
