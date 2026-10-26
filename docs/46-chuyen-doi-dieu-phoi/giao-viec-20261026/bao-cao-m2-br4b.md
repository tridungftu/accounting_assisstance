Đã sửa đúng 2 tệp được giao: đối chiếu đủ ba tổng, lệch → `MONEY_TOTAL_CONFLICT`; nhiều quan hệ → `RELATION_MULTIPLE`, giữ nguyên số nguồn.
Đã bổ sung docstring M3/V2; hợp đồng đầu ra cũ và strict V1 không đổi.
Reader trước/sau: **41/45 → 52/52**; xử lý CRLF trong bộ nhớ test.
Test liên quan trước/sau: **67/68 → 67/68**; vẫn thiếu `openpyxl`, không có lỗi mới. UTF-8 không BOM.
Không commit. Thông điệp đề xuất: `[M2-BR4b] Đối chiếu tổng tiền và giữ HOLD khi có nhiều quan hệ`.