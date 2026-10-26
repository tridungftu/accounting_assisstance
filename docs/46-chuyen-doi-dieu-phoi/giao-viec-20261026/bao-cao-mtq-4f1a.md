Anh, đã thực hiện MTQ-4f1a, sửa đúng 3 tệp được giao:

- Thêm `MTQ_CONG_E_SQL`: resolver 11 đối tượng M4 qua FK, whitelist từng cặp bảng–lệnh; K chưa mở Duyệt có tiền.
- Append `M00xx_MTQ_CONG_E`, giữ nguyên migration cũ.
- Viết 23 test trong `tests/test_mtq_m4_resolver.py`.

Đối chiếu thân hàm M0047, UTF-8 không BOM/LF và `git diff --check`: đạt. **Test: NOT_RUN** vì không có Python; chưa xác nhận lỗi mới so nền. Không commit, không mở server/PG DEMO.

**Cần lead:** chạy test/PG và cập nhật ca âm tại `tests/test_mtq_crm_resolver_sql.py:336`, vốn còn kỳ vọng các cặp M4–dự án mới được mở phải thiếu resolver. Tệp này ngoài phạm vi nên tôi giữ nguyên.

Thông điệp commit đề xuất: `[MTQ-4f1a] Bổ sung resolver phạm vi M4 cho cổng phiên`