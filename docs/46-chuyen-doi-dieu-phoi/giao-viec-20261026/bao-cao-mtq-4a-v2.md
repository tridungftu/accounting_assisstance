Anh, đã hoàn thành **phạm vi rút gọn trong đúng 3 tệp**: adapter chung và ba điểm `duyet`, `duyet_v4`, `tu_choi`. Có khóa căn cứ tiền, so sánh Decimal, chặn không fallback và ghi từ chối sau rollback. Không bật ma trận, không thêm migration, không commit.

- **MTQ:** 78 đạt/112 bài, 34 skip.
- **CRM trước = sau:** 436 bài; 319 đạt, 21 FAIL, 2 ERROR, 94 skip; không thêm lỗi, không giảm số bài.
- Kiểm thêm M0041: 1 FAIL do CRLF có sẵn ở tệp ngoài phạm vi sửa.

**Cần Anh:** lead tách lát nối các điểm nộp/bổ sung/trích lại/mapping/kiểm, M1 và file soát; hoàn thiện SQL/RLS và HTTP 404. Ngoại tệ chưa có tỷ giá ghim hoặc V4 không xác định duy nhất phiên bản đều bị chặn. PG chưa được xác minh thực tế.

Thông điệp commit đề xuất: `[MTQ-4a] Thêm adapter thẩm quyền và nối ba điểm duyệt CRM`