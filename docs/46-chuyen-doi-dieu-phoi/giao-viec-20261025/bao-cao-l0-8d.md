Đã bổ sung họ `03a`, sửa đúng 3 tệp; không nối PostgreSQL, không commit.

- **Cách dựng:** [runner:409](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-l0-8d/tools/chay_test_theo_module.py:409>) nhận đúng hai module, tạo clone riêng, migrate và dùng sổ sở hữu để dọn sau module. [Helper:51](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/.claude/worktrees/lat-l0-8d/tools/pg_demo_ho_03a.py:51>) dùng seed M4 với ma trận kế toán DEMO riêng; nhận hóa đơn G01 và map dòng qua `HoaDonK2`.
- **Biến 03A:** tiền tố `KHO_M4_03A_` với `CLONE_DSN`, `CLONE_APP_DSN`, `CLONE_DB`, `CLONE_PROVENANCE`, `M24_SHA256`, `VERSION`, `SHA256`, `KT1`, `KT2`, `KT_KHAC`.
- **03B:** nhận toàn bộ biến 03A, thêm `KHO_M4_03B_DA_AP_DUNG=1`, `HOA_DON_ID`, `DONG_ID`, `CFO`, `XEM` cùng tiền tố `KHO_M4_03B_`.
- **Dự kiến skip:** C16 thiếu lịch sử tỷ lệ trước M0033; C03 và các ca phụ thuộc có thể skip nếu MST không khớp. Gate engine #6 chưa sẵn sàng vẫn skip theo test hiện có. **Rủi ro ngoài phạm vi:** C01 yêu cầu `doi_tac_id` khác NULL nhưng producer hiện chưa gắn đối tác, có nguy cơ FAIL.
- **Test:** 11/11 ca mới đạt; toàn module 33/34, một FAIL Windows chập chờn đã xuất hiện trước sửa. Không thêm lỗi so lần chạy trước sửa. UTF-8 không BOM, syntax và `git diff --check` đạt.

Thông điệp commit đề xuất: `[L0-8d] Bổ sung họ clone DEMO 03a cho test PostgreSQL M4-03A/03B`.