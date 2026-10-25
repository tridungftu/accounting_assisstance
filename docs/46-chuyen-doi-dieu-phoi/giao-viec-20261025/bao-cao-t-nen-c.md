Anh, tôi đã sửa **2 tệp test**, không sửa sản phẩm/bộ chạy và không commit.

- **DTO — `tests/test_m4_master_dung_chung_pg.py:420`, commit `04ba10b`:** `dict(..., **sai)` trùng keyword, lỗi xảy ra trước khi gọi service. Đã tách thành tạo `dict` rồi `kw.update(sai)`; giữ nguyên ba trường hợp và assert.
- **Source #6 — `tests/test_source6_lazy_excel.py:36,45`, commit `f1e973d`:** test bắt buộc bố cục đóng băng `files/input-extra`; bộ chạy dùng worktree và runtime không thay bố cục này. **Đã có trong nền v4:** 3 lỗi `setUpClass`; PG v2 thành 2 lỗi setup + 3 FAIL. Lớp subprocess thiếu preflight baseline; đã bổ sung tại dòng 583, giữ nguyên SHA, guard và assert. **Chưa xử lý hết:** candidate `tools/source6_lazy_excel/master_hd.py` thiếu trong Git; khôi phục tệp này nằm ngoài phạm vi.

**Kiểm tra:** `git diff --check` đạt; UTF-8 không BOM; assert/skip không đổi. Chưa chạy được test vì sandbox từ chối thực thi Python; chưa xác nhận kết quả so nền. Không nối CSDL.

Thông điệp commit đề xuất: `[T-NEN-c] Sửa DTO trùng keyword và bổ sung preflight baseline Source6`