Anh, đã nối 03B trên nhánh `lat/m4-5b`, đúng **4 tệp**, UTF-8 không BOM; **không commit**.

- **Route mới:** đọc theo đợt, còn thiếu, lịch sử; xem đồ thị, lưu nháp, xác nhận. Dùng dịch vụ sẵn có, danh tính từ phiên; tham số lạ trả 400 tại [m4.py:370](src/kho_tri_thuc/giao_dien/m4.py).
- **Giao diện:** [m4_ke_toan.js:513](src/kho_tri_thuc/m4/giao_dien/m4_ke_toan.js). Checklist **1–3:** khối dưới đợt đã xác nhận, chọn hóa đơn theo danh sách lọc/xếp hạng, nhiều–nhiều, khai số tiền. **4:** chọn tệp căn cứ có sẵn. **5–8:** nháp/xác nhận/khóa, phiên bản mới/lịch sử, còn thiếu, chặn gắn trùng, “Cần kiểm lại”. **9–11:** khối không hiển thị công nợ/mã kỹ thuật; quyền do dịch vụ kiểm; ngày và tiền có định dạng.
- **Test mới:** [Python:46](tests/test_m4_03b_http.py) **11/11**; [node:16](tests/m4_03b_async.cjs) **12/12**. Python trước/sau: **208/248 → 219/259 đạt**, giữ nguyên **1 lỗi SHA**, 39 skip. Node: **7/14 → 8/15 bộ đạt**, giữ nguyên 7 bộ lỗi nền. Không phát sinh lỗi mới; PG chưa chạy.

**Cần Anh:** tải tệp mới hiện yêu cầu quyền `SOAN` tại `xay_dung.py:408`; chưa có đường dành cho kế toán. Màn 03A thực tế nằm ở `#m4`; `#nghiemthu` là màn khác, nên khối được đặt trong màn 03A hiện hữu.

Thông điệp commit đề xuất: `[M4-5b] Nối đối chiếu căn cứ với hóa đơn trong Kế toán nghiệm thu`.