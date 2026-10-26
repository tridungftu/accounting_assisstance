Anh, đã hoàn thành M4-DL1 trong đúng **3 tệp**, chưa commit.

- **DDL:** thêm 11 bảng chứng cứ nguồn, 1 bảng định danh import và 15 cột `review_*` trên hồ sơ HĐ; map đủ 12 bảng SQLite, giữ NULL/kiểu/khóa, PL hủy, BOQ `BO`, hash từng dòng, RLS và REVOKE.
- **Dùng lại:** `master.hop_dong`, `m4.ho_so_hop_dong`; có FK liên kết tham số/PL/BOQ/đợt/map/log hiện hữu. Migration chỉ append, phần cũ nguyên byte.
- **Test mới:** 5/13 đạt, 8 PG skip. Toàn repo: 1.987 đạt, 79 ERROR, 41 FAIL; chưa kết luận xanh do lỗi nền/môi trường và một lỗi HTTP chập chờn.
- **Cần Anh:** lead cấp ordinal migration và chạy 8 test PostgreSQL. Không đọc dữ liệu thật, không mở server/PostgreSQL.

Thông điệp commit đề xuất: `[M4-DL1] Bổ sung lược đồ lưu đủ nguồn Review SQLite và khóa import`