**Trả lời lead (Claude) cho câu "Cần lead" lần trước — làm theo, không hỏi lại:**
Đợt trước có đợt M4 cùng số chưa seal (ví dụ DA_NOP):
- Nếu dòng chép Review của đợt đó có `m4_dot_id` trỏ **đúng** đợt M4 này → **TÍNH** khối lượng Review vào lũy kế (đợt đã được duyệt ở phần mềm cũ), `nguon="REVIEW_CHEP"`, thêm cờ `m4_dang_mo_lai=true` trên đợt đó; khi M4 seal đợt này thì seal thắng (như quy tắc chung).
- Nếu cùng số nhưng `m4_dot_id` NULL hoặc trỏ đợt khác → `CAN_XEM_LAI`, không cộng.
Bỏ gạch đầu dòng test cũ "Đợt M4 cùng số đang mở chưa seal → không dùng Review"; thay bằng hai ca trên. Môi trường không có `python` thì ghi NOT_RUN — lead chạy test.

