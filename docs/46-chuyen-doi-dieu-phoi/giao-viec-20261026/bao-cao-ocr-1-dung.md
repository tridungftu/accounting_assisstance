**Cần lead.** Tôi dừng trước khi sửa vì có hai điểm xung đột:

- Review chỉ dùng `threading.Lock`; `_ghi_so()` ghi trực tiếp, không dùng `.lock`. Vì vậy, khóa trong `CongOCR` không ngăn được Review chen hàng hoặc ghi đè mất bản ghi khi chạy đồng thời. Cần lead xử lý phía Review để bảo đảm dùng chung an toàn.
- Test M9 hiện cố định sổ `ocr_hot_folder_m9/so_trang.json`, bản ghi 3 phần tử và mẫu `m9_*.docx` khi giữ tệp. Chuyển sang sổ Review và mã `hd...` cần cập nhật test này; nhưng danh sách giao chỉ cho phép 3 tệp. Cần lead xác nhận ngoại lệ cho tệp test thứ tư.

**Đã làm:** đọc đối chiếu code/test trên nhánh `lat/ocr-1`. **File đổi:** 0. **Test:** chưa chạy. Không commit, không chạm dữ liệu thật.