Anh, đã hoàn tất MDA-5a trong đúng 5 file:

- [crm_giao_ket.py:79](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mda-5a/src/kho_tri_thuc/k2/crm_giao_ket.py:79>): regex chung, giới hạn 3650; dòng 1318 kiểm mốc trong giao dịch `luu_soan`.
- [crm_s1.py:161](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-mda-5a/src/kho_tri_thuc/k2/crm_s1.py:161>): dùng chung regex, `CASE` bảo vệ ép kiểu; mã sai giữ `MOC_CHUA_CO_NGAY`.
- Test bổ sung tại `test_crm_moc_du_an_bao_gia.py:151`, `test_crm_s1_moc_du_an.py:35`; cập nhật duy nhất dòng SHA trong `test_crm_ky_ket.py:43`.

**Test trước → sau:** 62/81 đạt, 19 skip → **68/89 đạt, 21 skip**; không lỗi mới. PG chưa chạy, dành cho lead. UTF-8 không BOM; `git diff --check` đạt.

Review được chỉ định không tồn tại trong worktree. Không commit. Thông điệp đề xuất: `[MDA-5a] Thống nhất quy tắc mốc riêng và kiểm mốc khi lưu soạn hợp đồng`.