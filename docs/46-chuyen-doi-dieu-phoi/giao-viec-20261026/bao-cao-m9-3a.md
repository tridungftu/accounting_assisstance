Anh, đã hoàn thành M9-3a, **chưa commit**.

- Tạo [snapshot_sheet.py](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-m9-3a/src/kho_tri_thuc/m9/snapshot_sheet.py>) và [test_m9_snapshot_sheet.py](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-m9-3a/tests/test_m9_snapshot_sheet.py>), UTF-8 không BOM.
- Có cấu hình DEMO, chuẩn hóa Decimal/date/None, loại dòng lỗi và trùng mã, hash ổn định khi đảo cột.
- **Test: 38/38 đạt**, gồm tích hợp M9-4a; không lỗi mới trong hai module đã chạy. Chưa chạy toàn bộ nền.
- **Cần Anh/lead:** cung cấp Sheet/tab, ánh xạ cột và dấu thập phân thực tế cho lát nối nguồn.

Thông điệp commit đề xuất: `[M9-3a] Chuẩn hóa Sheet DEMO thành snapshot có mốc và hash`