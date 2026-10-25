Anh, đã hoàn tất đúng 2 file:

- [server.py:269](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-bg-e6s/src/kho_tri_thuc/giao_dien/server.py:269>): gom 5 điểm vào một hàm, một truy vấn; bổ sung tên pháp nhân đã sắp xếp và `co_crm`, giữ login và registry. Tên ghép thành chuỗi tương thích `app.js`.
- [test_danh_tinh_demo.py:18](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-bg-e6s/tests/test_danh_tinh_demo.py:18>): thêm 10 test.

Test trước: **21/24 đạt**, 1 FAIL, 2 ERROR (gồm module mới chưa tồn tại). Sau: **27/33 đạt**, 1 FAIL cũ, 5 PostgreSQL skip vì thiếu DSN. **Không thêm lỗi.**

UTF-8 không BOM; `git diff --check` đạt. Không commit.

Thông điệp dự kiến: `[BG-e6s] Bổ sung tên pháp nhân và quyền CRM cho vai DEMO`