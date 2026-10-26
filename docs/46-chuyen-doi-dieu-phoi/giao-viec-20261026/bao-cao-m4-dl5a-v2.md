Anh, đã hoàn tất vòng 2, đúng 3 tệp; **chưa commit**.

- Sửa fixture gây `KeyError`, không mặc định thiếu khóa thành `DA_MAP`.
- Hoàn tất kiểm quyền trên `c`, đóng lỗi công bố bằng nhánh có sẵn, kiểm xung đột chéo và THAY/BO trên tập gộp; lọc basis, bỏ dữ liệu lặp. Parity đạt.
- **03B nguồn NT dùng cổng KE_TOAN của 03A**, không có vai riêng; đã bổ sung kiểm chứng PG.
- File đổi: `k2/xay_dung.py`, `m4/nguon_review.py`, `tests/test_m4_review_compute.py`. UTF-8 không BOM; `git diff --check` đạt.
- Test yêu cầu: **72 đạt/110, 38 skip**. Nhóm Review: **125 đạt/205, 80 skip**. Không có lỗi mới trong phần đã chạy.

**Cần lead:** chạy PG để xác minh DUYET/KE_TOAN và 8 mã lỗi fallback; chưa xác nhận các ca này đã trở về nền.

Thông điệp commit đề xuất: `[M4-DL5a] vòng 2: sửa quyền snapshot, công bố lỗi và basis PL/BOQ`