Anh, đã hoàn tất MDA-1b, đúng 3 tệp, UTF-8 không BOM:

- [crm_du_an_ban.py](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mda-1b/src/kho_tri_thuc/k2/crm_du_an_ban.py:194>): chuẩn hóa nhập; service danh sách/lịch sử/ghi mốc; danh mục theo dự án; seed 2 mốc idempotent, hỗ trợ DEMO đã seed trước.
- [crm_g.py](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mda-1b/src/kho_tri_thuc/giao_dien/crm_g.py:521>): thêm GET/POST `/api/crm/du-an-ban/moc`, GET `/api/crm/du-an-ban/moc/{moc_id}/lich-su`; mở rộng `moc-chuan?du_an_id=`; lỗi 400 theo trường và 409 khi lần cũ.
- [test_crm_du_an_moc.py](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mda-1b/tests/test_crm_du_an_moc.py:34>): 14 đạt, 1 PostgreSQL skip.

**Test trước → sau:** 87/125 đạt, 38 skip → **101/140 đạt, 39 skip**; không lỗi mới. Đã chạy 3 module bắt buộc cùng `test_crm_42_s1_http`, `test_crm_giao_ket_http`, `test_crm_bao_gia_mac_dinh`. `git diff --check` đạt.

Phần PostgreSQL cần lead chạy với `KHO_PG_DSN_TEST`. Không sửa SQL, không commit.

Thông điệp commit đề xuất: `[MDA-1b] Thêm dịch vụ, HTTP và mốc thanh toán DEMO theo dự án`