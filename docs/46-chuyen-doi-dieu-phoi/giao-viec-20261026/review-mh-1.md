(a) **Đạt** — `src/kho_tri_thuc/ha_tang/ma_hoa_cot.py:55`: DATA_BLOB đúng cấu trúc; CurrentUser, UI-forbidden, có `LocalFree`; hai khóa sinh riêng; ghi `"xb"` không đè; import không truy cập thư mục khóa.

(b) **Đạt trong diff** — `src/kho_tri_thuc/ha_tang/ma_hoa_cot.py:24`, `:130`, `:185`: mẫu SQL chỉ placeholder; đối tượng giữ khóa che `repr`/`str`; lỗi dùng mã cố định, không log. Không thấy đường đưa khóa vào chuỗi SQL hoặc argv. Tuple chứa passphrase được trả theo giao việc; caller chưa nối.

(c) **Không — Chặn** — `src/kho_tri_thuc/ha_tang/ma_hoa_cot.py:232`: `casefold()` toàn email vi phạm mục D(c), yêu cầu không gộp hai giá trị khác nhau. **Tình huống hỏng:** hệ thống thư có hai mailbox phân biệt local-part `Anh@example.com` và `anh@example.com` → cả hai chuẩn hóa thành `anh@example.com` → cùng HMAC, tra cứu nhầm hoặc xung đột UNIQUE. HMAC-SHA256, khóa riêng, giữ số 0 đầu và dùng lại `bank_account` đều đúng.

(d) **Không — chưa đủ căn cứ kết luận Đạt; Nên sửa/làm rõ** — `src/kho_tri_thuc/ha_tang/ma_hoa_cot.py:254`: STK/CCCD giữ bốn số cuối, email/SĐT che giữa. Tuy nhiên số dấu `*` tại `:258` tiết lộ chính xác độ dài STK/CCCD; chưa có ngưỡng xác định mức lộ “quá mức”.

(e) **Đạt** — `src/kho_tri_thuc/ha_tang/ma_hoa_cot.py:12`: chỉ thêm thư viện chuẩn và dùng lại helper hiện có; không thêm dependency ngoài.

**Năm kiểm tra bắt buộc**

| Kiểm tra | Kết luận |
|---|---|
| Phạm vi | **Đạt:** đúng hai tệp được giao; fixture giả. Có đúng 22 test; worker báo NOT_RUN 0/22, khớp báo cáo. Gate lead 22 đạt là thông tin Anh cung cấp. |
| Đúng yêu cầu | **Không:** còn điểm Chặn tại (c), điểm cần làm rõ tại (d). |
| Tiền, số liệu, quyền | **Không phát sinh trong diff:** chưa nối caller/CSDL, không tính tiền hay cấp quyền. |
| Không phá phần cũ | **Đạt trong diff:** chỉ thêm tệp; không API AI trực tiếp, engine/kết nối trùng, schema mới hay SQL chéo module. |
| Giao diện/câu người dùng | **Chưa kết luận Đạt:** còn (d); chưa có UI/caller hiển thị lỗi. Không phát sinh ngày/tiền. |

Tôi chỉ đọc, không chạy lại test vì bộ test tạo thư mục/tệp tạm. **Chưa đủ điều kiện gộp.**

**Hỏi Claude**

Điểm Chặn (c): nghiệp vụ có chủ động coi local-part email không phân biệt hoa/thường không? — `src/kho_tri_thuc/ha_tang/ma_hoa_cot.py:232`; căn cứ hiện có chưa cho phép gộp hai mailbox trong tình huống trên.

Mức tiết lộ độ dài STK/CCCD qua số dấu `*` có được chấp nhận theo D(d) không? — `src/kho_tri_thuc/ha_tang/ma_hoa_cot.py:258`; giao việc chưa quy định ngưỡng này.