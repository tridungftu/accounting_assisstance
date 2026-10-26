# M4-KK — Kiểm kê chép phần mềm review hồ sơ xây dựng vào M4 (CD-011 việc 1, CHỈ ĐỌC + viết 1 tài liệu)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.** Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM — ghi tệp bằng UTF-8. Sandbox không ghi `.git`: **không commit**. Không xóa file. Worktree hiện tại, nhánh `lat/m4-kk` (hợp nhất). Đọc hộp thư `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` **CD-011**.

**Việc (chỉ đọc mã; chỉ ghi 1 tệp tài liệu):** bản gốc `D:\Claude\Ho tro review ho so xay dung\review_xaydung` (**chỉ đọc**: README, API.md, mã giao diện 8 màn — Tổng quan · Trích tham số · Danh mục hợp đồng · Phụ lục · BOQ · Kiểm tra đợt · Chứng từ · Cài đặt; lớp dữ liệu `csdl_hop_dong.py` SQLite) so với repo này (`src/kho_tri_thuc/m4/`, `m4/review_goc/`, `giao_dien/m4.py`, `m4/giao_dien/*.js`, SQL `k2/sql_review.py`, `k2/sql_master_dung_chung.py`…). **Không** mở/đọc dữ liệu thật trong thư mục `co_so_du_lieu` của bản gốc (chỉ đọc **lược đồ** từ mã `csdl_hop_dong.py` — CREATE TABLE, cột), không chạy chương trình bản gốc.

Ghi `docs\46-chuyen-doi-dieu-phoi\M4-KIEM-KE-CHEP-REVIEW.md`:
1. Bảng **màn × nút/chức năng × API** (theo API.md) → trạng thái ở M4: **đã có / thiếu / khác** (kèm tệp:dòng).
2. Bảng **SQLite (bảng, cột chính, khóa) ↔ PostgreSQL M4 hiện có** → map / thiếu / khác kiểu.
3. Phần code chép được nguyên vs phần phải viết lại (lớp dữ liệu `csdl_hop_dong.py` → PostgreSQL).
4. Đề xuất chia lát ≤ 3–5 tệp theo thứ tự: lớp dữ liệu → công cụ chuyển dữ liệu idempotent + báo cáo đối chiếu (số dòng từng bảng, tổng giá trị hợp đồng, tổng BOQ, tổng từng đợt) → từng màn vào khung icon M4.
5. Rủi ro: băm ghim lõi Review (`m4/nguon_review.py` PIN), Word COM trong `master_hd.py`, đường dẫn tuyệt đối, khác biệt kiểu dữ liệu tiền/ngày…

Tiếng Việt, bảng gọn. **Báo cáo (≤ ⅓ trang):** số màn/API/bảng đã kiểm, số thiếu, đề xuất lát đầu, thông điệp commit `[M4-KK] …`.
