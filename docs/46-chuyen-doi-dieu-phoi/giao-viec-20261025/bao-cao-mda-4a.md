Anh, đã sửa đúng 2 tệp:

- [crm_s1.py:161](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mda-4a/src/kho_tri_thuc/k2/crm_s1.py:161>): JOIN mốc đang mở; tính hạn thực tế + n, thêm `han_du_kien`/`MOC_DU_KIEN`; dự kiến không tính QUA_HAN/W5.
- [test_crm_s1_moc_du_an.py:32](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mda-4a/tests/test_crm_s1_moc_du_an.py:32>): thêm test thuần và PostgreSQL.

Test trước: **13 đạt, 11 skip**, module mới chưa có. Sau: **22 đạt, 12 skip, 0 lỗi**. Hồi quy S1 thuần: **23/23 đạt**. UTF-8 không BOM; diff sạch.

PG chờ lead chạy. Tệp thiết kế dẫn chiếu không có trong worktree.

Không commit. Thông điệp đề xuất: `[MDA-4a] Tính hạn đợt theo mốc riêng dự án`.