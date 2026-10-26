Anh, đã sửa đúng 4 tệp được giao: chặn cộng khác/thiếu ĐVT, mã HM trùng và ngày nghiệm thu thiếu/sau đợt hiện tại. Basis, `truoc_da_duyet`, JSON kết luận/seal giữ nguyên; test hồi quy đạt.

- **Trước:** 44 test — 29 đạt, 15 skip.
- **Sau:** 60 test — 41 đạt, 19 skip; không lỗi mới.
- **Hồi quy 02C:** 28 test — 23 đạt, 5 skip.
- UTF-8 không BOM; `git diff --check` đạt. Không commit, không mở server/PG.

**Cần Anh/lead:** chạy 19 test PG còn skip; bổ sung `review-m4-dl5b.md` đang thiếu trong worktree.

Thông điệp commit đề xuất: `[M4-DL5b] vòng 2: chặn cộng khác ĐVT, mã trùng và ngày NT chưa hợp lệ`.