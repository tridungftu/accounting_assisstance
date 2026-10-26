Anh, đã xử lý phần có căn cứ của MTQ-4b1b trong đúng 3 tệp, chưa commit.

- Nối guard ghi G1/G7 qua M0047; giữ đường CU, kiểm trước replay, ghim quyền và tách nhiệm. Thêm migration `M00xx_MTQ_CRM_A`.
- Viết **22 test**. **NOT_RUN** vì không có Python; chưa xác minh lỗi mới so nền. `git diff --check`, UTF-8 không BOM và LF đều đạt.
- **Cần lead:** chốt mức đọc nháp/lịch sử theo KK-MTQ4-CRM §5.2. Hiện khi bật, `DAY_DU` và đọc typed bị chặn; XEM chỉ mở đường hiệu lực. A3 cho giao dịch `READ ONLY` vẫn thuộc MTQ-NEN. Lead cần chạy unittest/PG và đánh số migration.

Thông điệp commit đề xuất: `[MTQ-4b1b] Nối guard G1/G7 qua cổng phiên, giữ tách nhiệm`