| Câu trọng tâm | XS-3b | XS-3d |
|---|---|---|
| **(a) Dùng đúng cổng/bộ đọc** | **Đạt** — `engine_cong.py:136,160`: gọi cổng được tiêm; giữ `loai_viec`, không tự chọn Cloud hay tạo tài nguyên OCR riêng. | **Đạt** — `engine_hoa_don.py:103,106`: gọi đúng hai bộ đọc XML/ZIP. |
| **(b) Ánh xạ lỗi** | **Đạt** — `engine_cong.py:138,162`: lỗi ngoài bảng nổi lên; lý do là câu cố định. | **Không** — `engine_hoa_don.py:56,112`: bắt cả `DataError` biểu diễn lỗi lập trình. |
| **(c) Bảo toàn kết quả, hash** | **Không đủ căn cứ chốt hash giữa hai lượt gọi thực** — `engine_cong.py:149`: giữ mã yêu cầu thay đổi mỗi lượt. Bảo toàn DTO có đối chiếu tại `test_xs3_cong.py:267`. | **Đạt** — `engine_hoa_don.py:115`; đối chiếu toàn bộ kết quả, Decimal và hash tại `test_xs3_hoa_don.py:77,231`. |
| **(d) Không sửa lõi, không truy cập bảng** | **Đạt** — diff chỉ thêm `engine_cong.py`, `test_xs3_cong.py`; wrapper tại `engine_cong.py:134,158`. | **Đạt** — diff chỉ thêm `engine_hoa_don.py`, `test_xs3_hoa_don.py`; wrapper tại `engine_hoa_don.py:97`. |

Đường dẫn engine trong bảng thuộc `src/kho_tri_thuc/ha_tang/`; đường dẫn test thuộc `tests/`, trên nhánh tương ứng.

**Năm kiểm tra**

- **Phạm vi — Đạt cả hai:** đúng hai tệp/lát, fixture DEMO. Báo cáo XS-3b 37/37 khớp số test; XS-3d 86/86 thuộc bản đầu, bản v2 ghi NOT_RUN. Gate lead cung cấp là 87 và 88 đạt.
- **Đúng yêu cầu — XS-3b chưa chốt; XS-3d không đạt:** vướng hash AI cần xác nhận và điểm Chặn dưới đây.
- **Tiền, số liệu, quyền — Đạt trong phạm vi:** không thêm phép tính/làm tròn hay đường cấp quyền; XS-3d giữ nguyên Decimal, tiền tệ và chi tiết reader.
- **Không phá phần cũ — Đạt về cấu trúc:** không sửa đường cũ, không thêm SQL, bảng/cột, kết nối hay engine trùng; không có đường gọi nhà cung cấp AI trực tiếp.
- **Giao diện/câu người dùng — Đạt:** lý do cố định bằng tiếng Việt; không thêm màn hình, ngày hoặc tiền hiển thị.

**Chặn — XS-3d:** `engine_hoa_don.py:56,112` vi phạm câu **D(b)** và chỉ đạo “lỗi lập trình phải nổi lên”. Ca kiểm lỗi: truyền XML DEMO, giả lập reader ném `DataError("DECIMAL_INVARIANT", ...)` → wrapper trả `LOI/DECIMAL_INVARIANT` thay vì ném lại. Đây là mã kiểm invariant có sẵn trong reader (`hoa_don_xml.py:440,443`), cùng bị bắt bởi bảng dành cho lỗi đầu vào.

**Nên sửa — XS-3b:** bằng chứng hiện kiểm hash với DTO giả cố định; chưa giải quyết cách hiểu “cùng vào → cùng hash” khi cổng thực sinh `ma_yeu_cau` mới.

**Kết luận riêng:** XS-3b **chưa kết luận Đạt**, chờ Claude làm rõ; XS-3d **chưa được gộp**, có một điểm Chặn. Tôi chỉ đọc, không chạy lại Python; kết quả chạy test dựa trên báo cáo và gate Anh cung cấp.

**Hỏi Claude**

- XS-3b: tiêu chí hash yêu cầu ổn định theo **cùng DTO**, hay cùng yêu cầu qua hai lượt gọi thực? `engine_cong.py:149` — giữ nguyên mã yêu cầu khiến `hash_ra` có thể khác.
- XS-3d: Claude xác nhận ca `DataError("DECIMAL_INVARIANT", ...)` phải nổi lên? `engine_hoa_don.py:56,112` — bảng hiện không phân biệt lỗi đầu vào với lỗi invariant cùng lớp.