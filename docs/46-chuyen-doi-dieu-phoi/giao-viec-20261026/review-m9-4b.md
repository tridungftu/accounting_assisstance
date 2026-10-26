## Review Codex (chỉ đọc) — m9-4b · 26/10 ~17:27

- **(a) Đạt** — Sao chép nguyên văn `cau` và nguồn trích dẫn; không dùng số trong hợp đồng để tính lại báo cáo. `src/kho_tri_thuc/m9/bao_cao_lai_suat.py:125`.
- **(b) Đạt** — Mỗi truy vấn lọc theo tài liệu của đúng khoản vay; mã chưa ánh xạ dùng tập rỗng. `src/kho_tri_thuc/m9/bao_cao_lai_suat.py:117`, `:120`.
- **(c) Đạt** — Thiếu chỉ mục hoặc ánh xạ thì giữ cột trống và ghi chú cũ. `src/kho_tri_thuc/m9/bao_cao_lai_suat.py:113`, `:116`.
- **(d) Đạt** — Cột Excel ghép thành văn bản, đi qua hàm ghi ô ép kiểu chuỗi; test đọc lại kiểm tra không có công thức. `src/kho_tri_thuc/m9/bao_cao_lai_suat.py:220`, `:242`, `:290`; `tests/test_m9_bao_cao_lai_suat.py:303`.

Năm kiểm tra:

1. **Phạm vi: Đạt.** Diff chỉ chạm hai tệp được giao; fixture mới là DEMO. Báo cáo worker khớp thay đổi; hai module có tổng 54 test, khớp số khai báo.
2. **Đúng yêu cầu: Đạt.** Đủ ba truy vấn cố định, tối đa một câu/chủ đề, đủ trường trích dẫn và thông báo khi không tìm thấy.
3. **Tiền, số liệu, quyền: Đạt trong phạm vi lát.** Không thay phép tính, làm tròn hoặc đơn vị tiền; không thêm endpoint hay thay cơ chế quyền. Bộ lọc tài liệu được truyền vào truy vấn.
4. **Không phá phần cũ: Đạt qua đối chiếu mã.** Có test giữ nguyên toàn bộ kết quả khi thiếu một tham số; không thêm lời gọi AI hoặc mạng.
5. **Giao diện/câu người dùng: Đạt phần bổ sung.** Chủ đề, thông báo thiếu căn cứ và nguồn trích dẫn dùng tiếng Việt; định dạng ngày, tiền giữ nguyên.

**Chặn / Nên sửa / Để sau:** Không có phát hiện.

Tôi chưa chạy lại test vì `python` không có trong PATH. Gate **70 đạt, 0 lỗi, 0 skip** là kết quả runner Anh cung cấp; `git diff --check` đạt.

**Hỏi Claude:** Không có. **Kết luận: Đạt review, không có điểm Chặn gộp.**
**Lead lọc (Claude):** Đạt, không lọc. Kiểm xác suất: co.
