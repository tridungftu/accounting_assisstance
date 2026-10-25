Anh, đã sửa BG-20/BG-19 trong đúng 3 tệp:

- [crm_g.js:1480](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-bg-e1/src/kho_tri_thuc/giao_dien/assets/crm_g.js:1480>): lịch 5 cột, USD thêm VND quy đổi; % ↔ tiền lấy kết quả máy chủ, giữ ô gốc khi đổi tổng; phân biệt “Đã nhập”/“Tự tính”.
- [style.css:26](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-bg-e1/src/kho_tri_thuc/giao_dien/assets/style.css:26>): tiền từng lần và Σ dùng chữ 36px, đậm như Tổng giá trị; bỏ dòng tiền nhỏ mờ.
- [crm_giao_ket_async.cjs:1333](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-bg-e1/tests/crm_giao_ket_async.cjs:1333>): **4/4 ca đạt**: gõ %, gõ tiền, đổi tổng với gốc %, đổi tổng với gốc tiền.

Node giao kết: **trước 23/23 → sau 27/27**. Toàn bộ 20 bộ Node: **12 đạt, 8 lỗi nền đã nêu; không thêm lỗi mới**. Diff và UTF-8 không BOM đạt. Chưa thử trình duyệt; không mở server/PostgreSQL.

Không commit theo handoff. Thông điệp đề xuất: `[BG-e1] Tách lịch thanh toán hai chiều và làm nổi bật số tiền`