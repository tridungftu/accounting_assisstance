# T-PDF — Test in PDF báo giá theo chính sách "không Word COM" (test_crm_giao_ket_http g02)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2: "không Word COM (xuất DOCX; PDF tạm xuất tay)"). UTF-8 không BOM. Worktree hiện tại, nhánh `lat/t-pdf` (từ hop-nhat, đã có L0-8e). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không mở server, **không khởi chạy Word**.

**Hiện tượng (lead 25/10 21:30):** từ khi bộ chạy test nạp guard bảo vệ (L0-8e — giống môi trường server DEMO thật), `tests/test_crm_giao_ket_http.py::test_g02_bao_gia_vnd_luu_in` (~:258) hỏng: test chờ `PDF_DAT` khi máy có Word đúng ghim (`self.co_word`), nhưng nhận `PDF_CHUA_SAN_SANG`. Đường PDF qua Word: `src/kho_tri_thuc/nguon/crm_docx.py` `chuyen_pdf` (~:356-410, tiến trình `--word-worker`).

**Việc:**
1. Đọc mã để xác định vì sao dưới guard `chuyen_pdf` trả `PDF_CHUA_SAN_SANG` (ly_do nào) và mã sản phẩm có cờ/cấu hình nào tắt đường Word theo chính sách "không Word COM" không. **Không sửa mã sản phẩm** — nếu cần đổi hành vi sản phẩm (vd. tắt hẳn Word COM) → dừng, báo lead tệp:dòng.
2. Sửa test g02 (và ca liên quan như g07 nếu cùng gốc) để kỳ vọng đúng môi trường: khi đường Word bị chặn bởi chính sách/guard → `PDF_CHUA_SAN_SANG` với lý do tương ứng, DOCX vẫn tạo đủ; giữ nhánh `PDF_DAT` chỉ khi Word thật sự được phép (điều kiện rõ ràng, không dựa vào việc có tệp WINWORD.EXE).
**File được sửa (chỉ 1):** `tests/test_crm_giao_ket_http.py`. Không xóa file.
**Báo cáo cuối (≤ ⅓ trang):** gốc (tệp:dòng) · điều kiện mới · thông điệp commit `[T-PDF] …`.
