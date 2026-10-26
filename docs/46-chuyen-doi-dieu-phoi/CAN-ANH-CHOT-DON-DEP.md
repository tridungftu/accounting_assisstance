# Phiếu cần Anh chốt — dọn dẹp dữ liệu tạm (QD-20261026-09)

26/10/2026 · lead tóm tắt từ `KK-DON-DEP.md`. Anh trả lời "Đồng ý D1–D2", hoặc ghi mã muốn đổi.

**Ranh giới luôn giữ, không dọn:**
- chứng từ, tệp gốc và mã băm;
- các phiên bản hợp đồng / hóa đơn / BOQ / đợt;
- lịch sử tham số;
- bằng chứng duyệt, đóng dấu, PDF đã duyệt;
- nhật ký kiểm toán.

Số dòng nghiệp vụ tăng dần là bình thường.

| Mã | Câu cần chốt | Đề xuất của lead |
|---|---|---|
| D1 | **Hạn giữ ở vùng dùng thường xuyên** của dữ liệu tạm (tệp trung gian OCR, nhật ký, việc chạy máy đã xong…) | Tệp tạm **7 ngày**; cache và nhật ký **30 ngày**; việc chạy máy đã đóng và đối soát xong **90 ngày**. Quá hạn thì **chuyển sang vùng lưu trữ, giữ đủ, vẫn tra được**, không xóa. Thiếu sao lưu cùng mốc thì không chuyển. |
| D2 | **Cho phép xóa** hai loại dữ liệu thử của môi trường làm việc | (a) Khoảng **303 CSDL test cũ** trên cụm DEMO (dữ liệu giả). Chỉ đúng mẫu tên `kho_test_*`, lead xác minh từng cái, sao lưu trước, không đụng CSDL DEMO của Anh. (b) **Thư mục làm việc (worktree) của lát đã gộp ≥ 7 ngày.** Nhánh git vẫn giữ nên lấy lại được mã; không gỡ thư mục đang có thay đổi chưa commit. Thu về khoảng 8–9 GB. Ổ D đang trống 174 GB nên không gấp. |

**Lead tự làm, không cần Anh chốt:**
- **Bổ sung "bỏ dòng" (BO) cho BOQ của M4 · Nghiệm thu & chi phí dự án:** phụ lục bỏ một hạng mục thì thêm dòng "bỏ" có ngày hiệu lực, dòng cũ giữ nguyên. Đúng QD-09; phần mềm Review cũ đã có, bản M4 còn thiếu. Giao 3 lát BO-1…3.
- Các lát dọn sau này đều lấy hạn giữ khai báo trong từng module. Chạy sau sao lưu, có nhật ký số dòng và dung lượng thu về.
