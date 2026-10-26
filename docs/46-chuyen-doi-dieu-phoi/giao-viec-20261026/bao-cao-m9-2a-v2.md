Anh, tôi đã sửa đúng hai tệp trên nhánh `lat/m9-2a`, chưa commit:

- `src/kho_tri_thuc/m9/chi_muc_vay.py`: lọc hư từ trước khi bỏ dấu, phân biệt “vậy”/“vay”, tính tỷ lệ khớp trên từ nội dung; giữ ngưỡng BM25 và chỉ mục hợp đồng.
- `tests/test_m9_chi_muc_vay.py`: thêm 8 câu hỏi tự nhiên, 4 câu ngoài chủ đề, ca khoản 7.2 và kiểm tra giữ từ nghiệp vụ.

Kiểm tra tĩnh đạt UTF-8 không BOM, không có chuỗi bị cấm. **Chưa chạy được test:** sandbox chặn Python với `Access is denied`; chưa thể xác nhận đạt/tổng hoặc lỗi mới so với nền.

Thông điệp commit đề xuất: `[M9-2a] Sửa bỏ sót câu hỏi tự nhiên trong chỉ mục từ khóa`.