Anh, đã sửa đúng 3 tệp, UTF-8 không BOM:

- Thêm POST `phong`, `gan-vai`, `pham-vi`, `admin`: kiểm Admin/token/phiên, CAS, replay; cấp/thu hồi tường minh và bảo vệ Admin cuối qua M0039.
- Ánh xạ 8 mã lỗi sang câu nghiệp vụ; nhật ký từ chối giữ mã gốc trong `ly_do`.
- Bỏ `khoi-phuc`: **Cần lead: thiếu lệnh SQL KHOI_PHUC**.
- Test: **80 tổng — 51 đạt, 29 PG tự skip**; không lỗi mới trong hai module. `git diff --check` đạt.

Không nối `server.py`, không commit. Thông điệp đề xuất: `[MTQ-2c] Bổ sung route quản trị thẩm quyền và thông báo lỗi theo mã`.