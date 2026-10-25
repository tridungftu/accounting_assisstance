Anh, đã sửa đúng 2 file, UTF-8 không BOM:

- [sql_crm_du_an_moc.py:50](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mda-1b/src/kho_tri_thuc/k2/sql_crm_du_an_moc.py:50>): `translate` đủ 146 cặp → bỏ dấu tổ hợp → `upper` → gộp khoảng trắng/`btrim`. Dòng 137 thêm câu riêng “Ngày dự kiến không được để trống” khi sửa mốc.
- [test_crm_du_an_moc_pg.py:32](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mda-1b/tests/test_crm_du_an_moc_pg.py:32>): bỏ khóa số migration; kiểm đủ ánh xạ, ASCII upper, NFD, khoảng trắng; thêm ca PostgreSQL và sửa ngày thành null.

Test hai module: **36 test — 18 đạt, 18 skip**, 0 lỗi; không thêm lỗi so với trước sửa. PostgreSQL chưa chạy vì thiếu DSN. `git diff --check` đạt.

Không commit. Thông điệp đề xuất: `[MDA-1a] vòng 2: chuẩn hóa tên mốc độc lập locale C, bổ sung test và sửa lỗi ngày trống`.