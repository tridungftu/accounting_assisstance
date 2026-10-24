# M4 — ưu tiên dùng lại bản Review đã chạy được

**21/10/2026 · Chỉ dẫn bổ sung theo ý kiến của Anh.** Giữ nguyên kế hoạch M4 đã chốt; ưu tiên đưa giao diện Review hiện có vào ứng dụng, tránh viết lại chức năng nguồn.

## Căn cứ đã kiểm trực tiếp

- Nguồn: `D:/Claude/Ho tro review ho so xay dung/review_xaydung`.
- Root đã đối chiếu 56 tệp trong `src/kho_tri_thuc/m4/review_goc/`: cả 56 khớp nguyên byte với nguồn hiện hành; 65/65 tệp reference cũng khớp. Bao gồm 29 Python, 9 JavaScript, HTML/CSS, danh mục và tài nguyên.
- Các lời gọi hiện có trong `review_compute.py` dùng lại `toan_ven.KiemTra.chay`, `nghiep_vu._lop1`, `csdl_hop_dong.tinh_doi_chieu_dot`, `_lop2`, `bang_kiem_lop2`, `_lop2b`; không thay bằng thuật toán kiểm mới.

## Yêu cầu cho lượt Claude tiếp theo

1. Lấy `review_goc/giao_dien/checks.js` và các component/bố cục sẵn có làm điểm xuất phát. Giữ cách trình bày bảng, phát hiện, cây truy vết, ghép và chạy lại; chỉ sửa import/API/context và các thao tác cần nối với M4 hiện hành. Không thiết kế lại màn Review từ đầu.
2. Phần viết mới tập trung vào kết nối: tài liệu đã tiếp nhận, danh mục/quyền dùng chung, phiên bản căn cứ, lịch sử/kết quả/báo cáo và các nhánh duyệt sau này. Không dựng bộ tính, master, quyền hoặc CSDL nghiệp vụ song song.
3. Tiếp tục đủ gói M4-02A đã giao, lấy luồng bấm Review làm đầu ra nhìn thấy được: chọn hồ sơ → chạy kiểm → xem bảng/nguồn ô → ghép/chạy lại → lịch sử/tải báo cáo. Không kết luận đạt từ màn demo hoặc code chưa kiểm.
4. Giữ các cổng Nộp hồ sơ, xác nhận phòng dự án, quyền reviewer, duyệt/PDF và hai nhánh kế toán/Request theo kế hoạch đã chốt. Ưu tiên giao diện không bỏ các điều kiện này.
5. Lõi và giao diện nguồn giữ nguyên bản để đối chiếu; chỉ thích nghi những điểm nối thật sự cần thiết. Báo cáo rõ tệp được dùng nguyên, phần thay để tích hợp và phần chưa nối xong.

## Điểm tiếp tục thực tế

- Lượt M4-02A đầu dừng ở timebox 15 phút, đã lưu mốc 362 source/430 runtime: đổi migration và adapter; thêm compute/SQL. Chưa có service/HTTP/UI/tests/report hoàn chỉnh; chưa chạy product.
- Lượt tiếp tục giữ nguyên 13 đường dẫn gốc; trên mốc hiện tại có 8 đường dẫn đã tồn tại và 5 còn phải tạo. Đây là trạng thái thực hiện của cùng gói, không đổi mục tiêu.
- M4 đầy đủ vẫn gồm Lớp 1–2–3, nguồn/lịch sử/OCR/jobs/báo cáo, duyệt/PDF và nghiệm thu–công nợ/Request. CAD để sau; M9 giữ dừng. Không xóa file, không sửa ứng dụng nguồn đang có.
