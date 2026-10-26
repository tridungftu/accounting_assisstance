Anh, đã thêm đúng hai tệp:

- [m3.py](</D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-m3-1b/src/kho_tri_thuc/k2/m3.py>): ba đẳng thức dùng Decimal exact, nguồn/phiên bản, trạng thái và DTO tiếng Việt; dịch vụ chỉ đọc.
- [test_m3_dang_thuc.py](</D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-m3-1b/tests/test_m3_dang_thuc.py>): test DEMO và PG tùy chọn.

**Test:** 27 đạt/37, 10 PG tự skip; không lỗi trong hai module được yêu cầu. Đã thử số thiếu, ứng viên, khác currency, chênh Decimal rất nhỏ; UTF-8 không BOM đạt.

**PENDING — Cần Anh:** M2 chưa hỗ trợ bán ra/tiền chuẩn hóa; PG hiện chỉ kiểm cơ sở và liên kết ứng viên. Policy thuế #7 và căn cứ đủ đợt chưa có nơi lưu.

Không sửa SQL/migration, không commit. Thông điệp đề xuất: `[M3-1b] Thêm dịch vụ chỉ đọc đối chiếu ba đẳng thức hóa đơn–hợp đồng`.