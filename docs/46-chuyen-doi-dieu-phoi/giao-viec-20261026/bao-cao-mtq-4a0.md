Anh, đã sửa đúng 3 tệp, append `M00xx_MTQ_CONG`; giữ UTF-8 không BOM/LF, không commit.

Chữ ký hai hàm:

- `master.mtq_quyet_dinh_phien(text,jsonb,numeric) → jsonb`
- `master.mtq_ghi_tu_choi_phien(uuid,text,jsonb,numeric) → uuid`

Test: **19 đạt, 31 PG skip**, không lỗi trong phạm vi chạy; `git diff --check` đạt.

**Cần Anh:** xác nhận hợp đồng JSON `{bang,id,phong_id?}`. Hiện hỗ trợ HĐ tiếp nhận CRM và dự án bán; M1/đối tượng khác đang chặn, nên chưa xác nhận gỡ toàn bộ MTQ-4a. Audit tính lại quyết định sau rollback; nếu đã chuyển sang cho phép/`CU`, hàm báo lỗi. Lead cần chạy PG ngoài sandbox.

Thông điệp commit đề nghị: `[MTQ-4a0] Thêm cổng SQL quyết định và ghi từ chối theo danh tính phiên`.