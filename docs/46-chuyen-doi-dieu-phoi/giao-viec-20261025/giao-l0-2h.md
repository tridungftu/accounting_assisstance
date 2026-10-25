# L0-2h — Rà hai gói M4 chưa hoàn tất `m4b2`, `m4b3`: còn dùng được gì (chỉ đọc)

Bạn là worker Codex, chạy không tương tác (sandbox chỉ đọc). Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8. Nếu cần chạy Python dùng `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"` (có thể thiếu thư viện — khi đó chỉ đọc mã).

**Bối cảnh:** khi hợp nhất H3, hai gói `m4b2` (`luu/m4b2`, commit cf75c4d, tệp chính `docx_an_toan.py` + 1 test) và `m4b3` (`luu/m4b3`, c43404b, không có tệp mã mới theo bảng) được ghi "chưa xác nhận terminal" (worker cũ có thể dừng giữa chừng). Xem `docs/46-chuyen-doi-dieu-phoi/TAN-DUNG-CODE.md`, `HEADS-HOP-NHAT-20261024.csv`; nhánh tích hợp hiện tại `hop-nhat-20261023`.

**Việc cụ thể (chỉ đọc, không sửa file):**
1. Với mỗi nhánh: `git diff --stat 59b7d8e luu/<nhánh>`, `git log -3 luu/<nhánh>`; liệt kê tệp, mục đích (đọc docstring/đầu tệp), mức hoàn chỉnh (có test? test có chạy được không — chạy thử bằng Python đi kèm nếu được).
2. So với `hop-nhat-20261023`: tệp đó đã có trên hop-nhat chưa (cùng/khác nội dung)? Chức năng đã được gói sau làm thay chưa (grep tên hàm/khái niệm, vd "docx an toàn", "xuất DOCX", "Word COM")? Có ai trên hop-nhat import nó không?
3. Kết luận cho từng nhánh: **GỘP** (dùng được, chưa có trên hop-nhat — nêu tệp, chỗ nối, rủi ro), **BỎ — đã có bản thay** (nêu bản thay), hoặc **CẦN THIẾT KẾ/ANH QUYẾT** (vì sao).
4. Có dữ liệu thật trong các tệp này không (tên công ty, MST, số tiền thật)? Chỉ trả lời có/không + vị trí, không in giá trị.

**Không làm:** sửa/commit/gộp; đọc `var/`, `.env`, kho thật; xóa gì.

**Báo cáo cuối (≤ 1 trang, tiếng Việt):** bảng nhánh · tệp · mục đích · trạng thái trên hop-nhat · kết luận · việc đề xuất (nếu GỘP: handoff 3–5 dòng cho lát gộp).
