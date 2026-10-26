Anh, đã hoàn tất DL5b trong đúng 4 tệp, chưa commit.

- Lịch sử chép nằm riêng trong DTO 02C, đối chiếu theo mã HM; seal thắng legacy cùng đợt. Thiếu/mâu thuẫn không cộng; lệch lũy kế giữ cả hai số.
- Basis, `truoc_da_duyet` và JSON kết luận giữ nguyên byte.
- Test trước → sau: **220/257 → 234/271 đạt**, cùng **37 skip**, không lỗi mới. JS 02C: **65/65 đạt**, gồm DTO có khóa mới.
- File đổi: `duyet_dot.py`, `review_dot_pg.py`, `test_m4_review_dot_pg.py`, `test_m4_dl5b_lich_su.py`.

**Cần Anh:** quyết định có đưa lịch sử chép vào lũy kế chính thức.  
**Cần lead:** chạy PG với DSN quản trị và `psycopg`; môi trường này chưa đủ nên chưa xác minh PG.

Thông điệp commit đề xuất: `[M4-DL5b] Bổ sung lịch sử Review chép riêng trên DTO duyệt đợt`