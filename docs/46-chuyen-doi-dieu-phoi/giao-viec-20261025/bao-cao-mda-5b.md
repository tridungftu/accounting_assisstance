Đã sửa xong, Anh. Chỉ thay đổi 2 file, UTF-8 không BOM; không commit.

- `src/kho_tri_thuc/k2/sql_crm_du_an_moc.py:196`: bỏ lọc dự án đang bán; thêm boolean `du_an_dang_ban`. Giữ nguyên quyền và `crm_da_moc_ghi`.
- `tests/test_crm_du_an_moc_pg.py:79,322`: thêm kiểm tĩnh; cập nhật ca ngừng bán vẫn trả mốc, cờ `false`, trạng thái `QUA_DU_KIEN`.
- Test trước: **18 đạt/36, 18 skip**. Sau: **19 đạt/37, 18 skip**, không lỗi mới; `git diff --check` đạt. PostgreSQL chưa chạy, để lead kiểm chứng.
- `danh_muc_moc` giữ nguyên: tiếp tục trả mốc riêng khi ngừng bán, phục vụ tên mốc trên báo giá cũ; báo giá mới chỉ chọn dự án đang bán.
- File review được chỉ định không có trong worktree; đã thực hiện theo handoff.

Thông điệp commit đề xuất: `[MDA-5b] Giữ mốc riêng và việc chờ khi dự án ngừng bán`.