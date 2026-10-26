Anh, đã hoàn thành màn **Danh mục tham số**: chọn 6 loại, xem/sửa có lý do, nhật ký tiếng Việt và thời gian `dd/mm/yyyy hh:mm`; kiểm quyền phía máy chủ, trả 400 khi tham số lạ và 409 khi phiên bản đổi.

- **5 tệp đổi:** `khung_khai_bao.py`, `crm_g.py`, `app.js`, `test_khung_he_thong.py`, `khung_luoi_async.cjs`.
- **Test:** Python **91/91**, Node **40/40**; không lỗi mới trong phạm vi đã chạy. Đã kiểm UTF-8 không BOM và diff.
- **Cần Anh:** chốt vai sửa Kế toán trưởng/admin; schema hiện chưa có vai `ADMIN`. Lead cần thử DEMO với engine đã áp E1-4a/4b. Chưa thử trình duyệt/PostgreSQL; khóa phiên bản web không bao phủ CLI chạy đồng thời.

Không commit. Thông điệp đề xuất: `[E1-4u] Thêm màn danh mục tham số chung và nhật ký thay đổi`.