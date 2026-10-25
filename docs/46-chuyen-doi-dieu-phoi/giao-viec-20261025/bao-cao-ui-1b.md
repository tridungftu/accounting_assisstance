Đã sửa UI-1b trong đúng hai tệp:

- [app.js:1743](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-ui-1/src/kho_tri_thuc/giao_dien/assets/app.js:1743>): nhận mã `error: CRM_PHIEN`, chờ `crmLoad()` rồi thử lại đúng một lần; giữ epoch/gen và cổng đổi vai.
- [khung_luoi_async.cjs:444](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-ui-1/tests/khung_luoi_async.cjs:444>): thêm ca phục hồi thành công, vẫn lỗi, phân biệt mã lỗi và chống phản hồi cũ.

**Test:** khung đạt **16/16 ca**; toàn bộ node **12/20 bộ đạt**, 8 bộ lỗi đúng nền, không thêm bộ lỗi. UTF-8 không BOM; kiểm tra cú pháp và diff đạt.

Không mở server, không commit. Thông điệp đề xuất: `[UI-1b] Khôi phục phiên CRM và thử lại trang chủ đúng một lần`.