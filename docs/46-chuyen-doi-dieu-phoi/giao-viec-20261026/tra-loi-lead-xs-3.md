**Trả lời lead (Claude) cho XS-3b và XS-3d — làm theo, không hỏi lại:**

- **Không** thêm trường vào `KetQuaXuLy`/`KetQuaEngine`, **không** sửa `engine.py`.
- "Giữ loại ngoại lệ gốc" = mỗi ngoại lệ **đã biết** của cổng/bộ đọc ánh xạ sang **một mã `ma` ổn định riêng**, ví dụ `OCR_HET_HAN_MUC`, `OCR_DA_HUY`, `AI_LOCAL_CHUA_SAN`, `HOADON_XML_HONG`.
  - Bảng ánh xạ (lớp ngoại lệ → trạng thái CHO/LOI + mã + câu tiếng Việt trung tính) là hằng công khai trong module engine, có test từng dòng.
  - Như vậy bên gọi phân biệt được loại lỗi qua `ma`.
- Ngoại lệ **không có trong bảng** (lỗi lập trình, lỗi lạ): **không bắt**, để nổi lên, đúng hợp đồng `Engine` ("Không bắt ngoại lệ để che lỗi lập trình").
- Lý do hiển thị không chứa nội dung tệp/văn bản/traceback.
- Đầu ra XONG giữ đúng kiểu đã khai báo. Với AI, kiểu ra có thể là `KetQuaAI` nguyên vẹn nếu là dataclass thuần băm được; không được thì ghi "Cần lead".
- Không có `python`: ghi NOT_RUN, lead chạy test.
