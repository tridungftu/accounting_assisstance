Đã hoàn tất đúng 3 tệp, thêm DDL cho:

- `m3.hop_dong_co_so`: tiền exact, NULL/PENDING, ràng buộc phần chịu thuế, revision bất biến.
- `m3.hoa_don_hop_dong`: mapping ứng viên, ghim phiên bản/quan sát M2.
- `m3.policy_hinh_thuc_doanh_thu`: policy theo ngày hiệu lực.

Đã append `M00xx_M3_CO_SO`; bổ sung RLS, quyền chỉ đọc và nhật ký. UTF-8 không BOM; registry giữ LF và nguyên phần cũ.

**Test:** 34 = 7 đạt + 27 PG skip; không FAIL/ERROR. `git diff --check` đạt. Chưa kiểm chứng thực thi PostgreSQL.

**Cần Anh:** cơ sở thuế #7; M2 hiện chỉ hỗ trợ `MUA_VAO`, cần lát promote `BAN_RA` để xác nhận mapping bán; hiện giữ PENDING.

Không commit. Thông điệp đề xuất: `[M3-1a] Thêm cơ sở hợp đồng, liên kết hóa đơn M2 và policy doanh thu`.