# PDF-1 — Công tắc Word → PDF, mặc định TẮT (QD-20261025-26)

Bạn là worker Codex, chạy không tương tác. Anh đã chốt (25/10, QD-20261025-26; `CLAUDE.md` §2 "không Word COM (xuất DOCX; PDF tạm xuất tay)"): **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM. Worktree hiện tại, nhánh `lat/t-pdf` (đã có commit T-PDF f603a5d sửa kỳ vọng test g02/g06/g07). Sandbox không ghi `.git`: **không commit**. Không nối CSDL, không mở server, **không khởi chạy Word**.

**Việc:**
1. `src/kho_tri_thuc/nguon/crm_docx.py` `chuyen_pdf` (~:356): thêm công tắc **mặc định TẮT** (đọc biến môi trường `KHO_CRM_WORD_PDF == "1"` mới bật; không đọc tệp cấu hình thật). Tắt → **không tạo tiến trình Word/worker nào**, trả `{"trang_thai": "PDF_CHUA_SAN_SANG", "ly_do": "PDF_XUAT_TAY", ...}`; DOCX vẫn tạo đủ như trước. Bật → hành vi Word hiện có giữ nguyên.
2. Thông báo cho người dùng (nơi đang hiển thị lý do PDF chưa sẵn sàng — tìm trong `k2/crm_giao_ket.py`/`giao_dien/assets/crm_g.js`, **chỉ** sửa nếu không có sẵn cách hiển thị theo `ly_do`): tiếng Việt "PDF xuất tay từ tệp DOCX (chưa bật chuyển PDF tự động)". Nếu phải sửa `crm_giao_ket.py` → ghim SHA trong `tests/test_crm_ky_ket.py` sẽ đổi: **báo lead**, không tự sửa ghim. Ưu tiên không đụng `crm_giao_ket.py`.
3. Test: `tests/test_crm_giao_ket_http.py` (đã sửa ở T-PDF) cập nhật cho mặc định tắt: g02/g06/g07 kỳ vọng `PDF_CHUA_SAN_SANG` + `ly_do == "PDF_XUAT_TAY"`, DOCX có; một ca thuần chứng minh **không gọi** tạo tiến trình khi tắt (mock `subprocess.Popen`/hàm tạo worker); nhánh bật giữ test hiện có bằng cờ môi trường trong test.
**File được sửa (≤ 3):** `nguon/crm_docx.py`, `tests/test_crm_giao_ket_http.py`, + 1 tệp hiển thị thông báo nếu thật cần (ghi lý do). Không xóa file.
**Báo cáo cuối (≤ ⅓ trang):** sửa ở file:dòng · hành vi tắt/bật · test · thông điệp commit `[PDF-1] …`.
