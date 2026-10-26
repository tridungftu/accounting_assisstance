Anh, đã tạo đúng 3 tệp: `m10/__init__.py` rỗng, `m10/lich_phan_bo.py` và `tests/test_m10_lich_phan_bo.py`, UTF-8 không BOM.

Engine hỗ trợ A/B, catch-up, policy bắt buộc, Decimal, chấm dứt sớm và hash ổn định; chỉ phục vụ kiểm chéo.

**Test:** đã viết 19 test; chưa chạy được vì sandbox từ chối thực thi Python (`Access is denied`). Chưa xác nhận lỗi mới so với nền.

**Cần Anh:** lead chạy unittest ngoài sandbox; hiệu chuẩn K0 trước khi chốt A/B và quy ước tháng lẻ/làm tròn.

Không commit theo yêu cầu. Thông điệp đề xuất: `[M10-1a] Thêm engine lịch A/B chỉ để kiểm chéo Junsky`