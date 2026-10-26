## Review M4-DL5a (27dd92e) — review-lat (Opus), 26/10 ~15:40 · PG lead 15:12

**Kết luận: Cần sửa.** 2 điểm chặn. PG lead chạy ra thêm **8 mã lỗi mới** ở `test_m4_02b_k2` (`test_b1/b2/b3_fallback_…`: `AssertionError: 44 != 22`), khớp với điểm 3 (đổi `_tx_review`).

**Chặn**
1. **Hỏng 02C/03A/03B với người chỉ có vai DUYET hoặc KE_TOAN, kể cả khi chưa có bản chụp.**
   - Đường gọi: `do_thi`/`_ghim_do_thi` → `_chung_tu_co_so` → `_chung_tu_l2` (`k2/xay_dung.py:1251`) → `_co_so(conn_phien=self.conn)` → `chup_review_l2` (`m4/nguon_review.py:617`) → `_kiem_quyen_doc`.
   - `_kiem_quyen_doc` chỉ nhận `m4_duoc` XEM/REVIEW và chạy **trước** `_nguon_hien_hanh`. Vì vậy đợt nào đã có L1+L2 công bố cùng engine là báo "Không tìm thấy hợp đồng.".
   - Test PG 02C/03A hiện có không tạo L2 công bố có `doi_chieu_hm`, nên không bắt được.
   - Hướng sửa: kiểm quyền bằng SQL trên chính `c` (danh tính đã đặt; cổng `*_kiem` của từng luồng đã chạy), chấp nhận mọi vai M4 đã qua cổng gọi.
   - Thêm test PG: người chỉ DUYET / chỉ KE_TOAN, khi đã có L2 công bố → không lỗi, SHA basis giống reviewer.
2. **Câu cho người dùng có "Cần Anh/lead chốt nguồn"** (`xay_dung.py:854`, `nguon_review.py:679`). Câu này nằm trong `ly_do` của lần chạy, là bản ghi bất biến; test `test_xung_dot_cong_bo_failed…` khẳng định chuỗi này. Sửa thành câu nghiệp vụ trung tính, ví dụ "Cần xem lại nguồn phụ lục/BOQ: … Chưa tính.", và sửa test.

**Nên sửa**
3. `_tx_review` (`xay_dung.py:699`) mở thêm giao dịch trên kết nối phiên cho **mọi** luồng (Review, L3, 02C, 03A, 03B). Kết nối phiên commit trước kết nối chủ bảng; lỗi kết nối phiên rollback phần ghi review; `_loi_ket_noi(exc, c)` xếp sai loại lỗi. **Bỏ thay đổi này** khi sửa điểm 1 bằng kiểm trên `c` (lead: đây cũng là nguồn 8 mã lỗi mới).
4. Thu hồi quyền giữa hai câu lệnh lúc công bố: `_kiem_quyen_doc` ném `DataError`, mà `_review_cong_bo` chỉ bắt `psycopg.Error`, nên lần chạy treo RUNNING. Sửa theo điểm 1 thì lỗi vào nhánh bắt có sẵn.
5. Kiểm trùng (`nguon_review.py:649`) chặt hơn vendor: hai PL chép cùng ngày hoặc trạng thái lạ cũng bị chặn, trong khi vendor tự xếp `ngay_ky, so_pl` hoặc bỏ qua. Chỉ chặn **xung đột chéo hai nguồn**. Ngược lại, trộn hai nguồn khi không trùng số PL có thể làm dòng THAY/BO của PL chép bị bỏ qua im lặng. Áp kiểm "thao tác BOQ không khớp hạng mục" của DL3 trên tập gộp.
6. Basis và `co_so.json` (ai đọc được lần chạy đều tải được) chứa cột thô `file_nguon`, `nguoi_nhap`, `phieu`, `ly_do_huy`, id nguồn, lặp 2 lần (`review_chep` và `phu_luc`). Chỉ giữ cột cần cho tính toán; tệp chỉ giữ tên, bỏ đường dẫn.

**Để sau**
7. L3 (`_chung_tu_co_so`) tính trên BOQ vận hành, L2 tính có phần chép. Ghi rõ cho lát L3. Ghép tay không nhắm được dòng BOQ chép ("0 dòng nguồn" dễ hiểu nhầm).
8. Danh sách chưa báo "cần xem lại" trước khi chạy, nên mỗi lần bấm Chạy thêm một lần chạy FAILED.

**Đạt**
- Giữ nguyên byte khi không có bản chụp/không `conn_phien`.
- 5 chỗ gọi `_co_so` cho L2 truyền `conn_phien` thống nhất.
- Projection đúng SCHEMA nguồn; PL hủy vẫn nạp và vendor bỏ qua đúng; vendor PIN không đổi.
- Parity vendor ↔ projection tại 2 ngày so thật (P01, `tinh_doi_chieu_dot`, `_lop2`, B); `test_m4_review_compute` 60 ok / 2 skip với openpyxl.
- REAL→Decimal khứ hồi chính xác; NULL không thành 0.
- Đúng 3 tệp, không Cloud.
