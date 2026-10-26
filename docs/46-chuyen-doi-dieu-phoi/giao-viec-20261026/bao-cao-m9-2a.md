Anh, đã triển khai đúng hai tệp:

- [chi_muc_vay.py](src/kho_tri_thuc/m9/chi_muc_vay.py): chuẩn hóa token, BM25, trích dẫn nguyên văn, lọc/xóa tài liệu và JSON round-trip.
- [test_m9_chi_muc_vay.py](tests/test_m9_chi_muc_vay.py): 19 test DEMO.

Kiểm tra tĩnh đạt: UTF-8 không BOM, không chuỗi cấm, không lỗi whitespace. Chưa commit.

**Test:** chưa xác nhận đạt/tổng 40 test vì cả Python và launcher bị `Access is denied`; chưa xác định lỗi mới so với nền.

**Cần Anh/lead:** chạy lại unittest; rà soát ngưỡng điểm 0,1 kèm độ khớp 50%. Đoạn nhiều trang giữ khoảng trang, không đoán trang từng câu.

Thông điệp commit đề xuất: `[M9-2a] Thêm chỉ mục BM25 hợp đồng vay có trích dẫn nguyên văn`.