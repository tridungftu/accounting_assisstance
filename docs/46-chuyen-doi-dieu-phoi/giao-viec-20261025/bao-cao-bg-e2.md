Anh, đã hoàn thành BG-e2 trong 2 file:

- [crm_g.js:1687](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-bg-e2/src/kho_tri_thuc/giao_dien/assets/crm_g.js:1687>): nhập số dòng/dãy %, hỏi thay lịch trong trang, Hủy giữ nguyên; dùng đường tự tính BG-e1. Giới hạn 1.000 dòng.
- [crm_giao_ket_async.cjs:1390](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-bg-e2/tests/crm_giao_ket_async.cjs:1390>): kiểm tra `4`, các dấu tách, `12,5%`, Σ 90% đỏ, In mờ có lý do, Hủy, dữ liệu sai và payload gốc `%`.
- Node trước/sau: **27/27 → 31/31 nhóm ca**, không lỗi mới. Syntax, diff và UTF-8 không BOM đạt. Chưa thử trình duyệt; không mở server.
- Không commit. Thông điệp đề xuất: `[BG-e2] Thêm nhập nhanh lịch thanh toán báo giá`.