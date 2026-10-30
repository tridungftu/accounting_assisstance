# Phiếu duyệt 2/3 · Bộ API (CD-029 mục 2b)

**Lập:** 30/10/2026, lead. **Trạng thái:** chờ Anh duyệt.
**Đây là tài liệu, chưa lập trình.**
**Đã kiểm:**
- Codex soạn; Codex review chéo (kiểm mẫu đúng 85% vòng 1, đã sửa).
- Opus review hai vòng: vòng 1 có 1 Chặn; vòng 2 không còn Chặn.
- Lead tự kiểm OpenAPI: đọc được, bản 3.1.0, 33 đường dẫn.

## 1. Kết luận (đề nghị Anh duyệt)

1. **Một địa chỉ duy nhất cho người dùng:** mọi chức năng đi qua Core, dưới `/api/v1/`.
   - Nghiệp vụ module nằm dưới `/api/v1/module/{ma_module}/…`, ví dụ `/api/v1/module/crm/bao-gia/…`.
   - Người dùng không bao giờ gọi thẳng cổng của module hay engine (CD-028).
2. **Quy ước chung cho mọi module:**
   - **Lỗi một dạng:** mã lỗi, thông điệp tiếng Việt, mã tra cứu, có thử lại được không. Không lộ đường dẫn, khóa hay câu SQL.
   - **Chống ghi trùng khi bấm hai lần hoặc mất mạng.**
     - Mọi lệnh ghi mang khóa chống trùng; gửi lại cùng nội dung thì nhận lại kết quả cũ.
     - Nghiệp vụ module giữ biên nhận **vĩnh viễn** (như CRM đang làm).
   - **Hai người cùng sửa một hồ sơ:** người sau nhận lỗi "đã có người sửa", không ghi đè.
   - **Việc lâu** (OCR, trích xuất, tải hóa đơn): trả ngay mã việc để theo dõi.
     - Hủy chỉ là đề nghị.
     - Core khởi động lại thì việc đang dở chuyển "bị gián đoạn", **không bao giờ tự thành "xong"**.
   - **Tải tệp:** Core kiểm quyền mỗi lần tải xuống, kể cả khi biết mã tệp.
   - **Ngày, tiền và đăng nhập:** ngày giờ chuẩn; tiền có đơn vị; đăng nhập bằng cookie an toàn và chống giả mạo yêu cầu (CSRF).
3. **Core giữ cổng, nhả cổng (CD-028):**
   - Module/engine chưa chạy: Core tự khởi động, chuyển cổng không khoảng hở, chờ sẵn sàng rồi phục vụ.
   - Rảnh quá hạn: Core đóng có kiểm soát; yêu cầu đến lúc đang đóng được báo "đang dừng, thử lại".
   - Khởi động lỗi 3 lần: khóa lại, chờ Admin.
   - **Không gì luôn chạy** nếu Admin chưa bấm áp dụng đề xuất.
4. **Truyền danh tính sang module:** dùng thẻ ký có hạn 30 giây, mang **mã ủy nhiệm bí mật**. CSDL tự kiểm mã này, khớp phiếu CSDL. Engine và máy phụ không có đăng nhập CSDL.
5. **Quản trị:**
   - Admin xem trạng thái, cài/nâng cấp/tắt module, đăng ký engine, cấp quyền module.
   - Admin xem số đo khởi động và đề xuất chế độ chạy hằng tuần; **chỉ Admin bấm áp dụng**.
6. **Route cũ** (`/api/crm/…`, `/api/khung/…`, `/api/cong-tac-module/…`, `/api/that/…`):
   - Ánh xạ đủ sang route mới.
   - Giữ tạm qua lớp chuyển tiếp theo từng nhóm; gỡ khi đã chuyển xong và có quyết định ngừng.
   - Các route cũ vi phạm (ví dụ `/api/that/…` chưa gắn người thao tác, vài đường tải xuống chỉ kiểm đường dẫn) được sửa trong route mới.

## 2. Nhóm route chính

| Nhóm | Dùng cho |
|---|---|
| `phien`, `toi`, `phap-nhan` | Đăng nhập/đăng xuất; tôi là ai, được quyền gì; chọn pháp nhân |
| `tai-lieu`, `tep`, `ket-qua` | Tài liệu, tải lên/xuống tệp, kết quả OCR/che/trích xuất |
| `module`, `engine`, `quy-trinh`, `viec` | Module được dùng; năng lực engine; chạy quy trình; theo dõi/hủy việc |
| `quan-tri/module`, `quan-tri/engine`, `quan-tri/cap-quyen`, `quan-tri/so-do`, `quan-tri/de-xuat-che-do` | Quản trị (chỉ Admin) |
| `module/{ma}/…` | Nghiệp vụ từng module; mỗi route phải khai báo riêng trong gói module |
| `/healthz`, `/readyz` | Kiểm Core còn sống / sẵn sàng |

Ví dụ đầy đủ request/response cho 3 route tiêu biểu nằm ở đặc tả §6:
- tạo tài liệu (đồng bộ);
- OCR một tài liệu (việc lâu);
- lưu ghi chú báo giá CRM khi hai người cùng sửa.

## 3. Câu cần Anh chọn

| # | Câu hỏi | A | B | Khuyến nghị |
|---|---|---|---|---|
| 1 | **Khi mở lại một module đã tự đóng vì rảnh** | Đóng sau 5 phút rảnh; lần mở sau màn hình hiện "đang khởi động" vài giây rồi tự vào | Giữ 30 phút: ít phải chờ hơn, tốn RAM hơn | **A** (ít tài nguyên, QD-09). Admin vẫn có thể giữ lâu hơn cho module cụ thể dựa trên số đo |
| 2 | **Giới hạn mỗi tệp tải lên** | 20 MB | 50 MB | **A**, nếu hồ sơ scan M4 · Nghiệm thu & chi phí dự án thường dưới 20 MB. **Anh cho biết hồ sơ scan thường nặng bao nhiêu** để chốt |

**Hỏi chung ở phiếu CSDL, không hỏi lại:**
- nguồn tài khoản đăng nhập (câu 3);
- hạn giữ dữ liệu tạm (câu 2, gồm cả kết quả OCR/Mask tạm).

**Báo, không cần chọn:**
- thẻ ký và mã ủy nhiệm là yêu cầu thiết kế. Nếu Anh chọn B ở câu 1 phiếu CSDL thì phần này sửa lại trước khi dựng;
- biên nhận chống trùng của module giữ vĩnh viễn;
- route cũ giữ chuyển tiếp theo từng nhóm.

## 4. Anh duyệt bằng cách

Trả lời một dòng, ví dụ: **"Duyệt API; câu 1 A, câu 2 A (scan thường ~N MB)"**, hoặc ghi điểm cần đổi. Bước dựng Core chỉ bắt đầu khi đủ ba phiếu được duyệt.

## Phụ lục (chi tiết kỹ thuật)

- Đặc tả: `docs\47-core\g1\DAC-TA-API.md`.
  - Quy ước §2, danh mục route §3, dispatcher §4, quản trị §5, ví dụ §6.
  - Cuối tệp có OpenAPI 3.1.
- Ánh xạ route cũ → mới: `docs\47-core\g1\ANH-XA-ROUTE.md`.
- Biên bản review:
  - `g1\RV-G1B.md` (Codex);
  - `g1\RV-G1B-OPUS.md` (Opus vòng 1);
  - vòng 2: không còn Chặn, ba câu bổ sung đã ghi vào §2.4 và §4.2 của đặc tả.
