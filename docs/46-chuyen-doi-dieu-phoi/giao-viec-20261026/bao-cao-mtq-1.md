Anh, đã bổ sung MTQ-1 đúng ba tệp được giao, chưa commit.

- **SQL:** 11 bảng; lõi `mtq_quyet_dinh`, lệnh cấu hình chỉ Admin, bootstrap tin cậy; có CAS revision, audit cũ → mới, snapshot bất biến và RLS/REVOKE.
- **Chuyển tiếp:** mặc định tắt, giữ đường quyền cũ; readiness chặn bật trước MTQ-4. Migration append, giữ nguyên 36/36 checksum cũ.
- **Test:** MTQ đạt 12 test thuần, 20 PG skip. Hồi quy liên quan đạt 28 test, 50 skip; không lỗi trong nhóm đã chạy. Chưa đo toàn nền v4. Ba tệp UTF-8 không BOM.
- **Cần Anh/lead:** chạy PG; scope nguồn đang chặn an toàn, chờ resolver MTQ-4i.

Thông điệp commit đề nghị: `[MTQ-1] Thêm SQL ma trận thẩm quyền, phiên bản và nhật ký bất biến`