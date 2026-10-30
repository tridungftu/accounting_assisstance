# Khảo sát Core (G0) — CD-026 mục 2 · TL 55

Lập ngày 30/10/2026, lead ghép. Năm phần khảo sát do Codex làm (chỉ đọc). Mỗi phần qua **một vòng review chéo Codex**. Lead kiểm xác suất phần **KS-B** (chọn trước khi gộp): 7/7 tham chiếu đúng.

## Kết luận chung

- **Xương sống hiện có nâng được thành Core, không làm Core thứ hai.**
  - Giữ lại: ma trận thẩm quyền, công tắc module, bus sự kiện, hàng việc PostgreSQL, hợp đồng engine, cổng AI/OCR.
  - Chưa khối nào đủ yêu cầu TL 54 §9: 11 khối mới có một phần; Workflow Runner dùng chung chưa có.
- **CSDL phải chia theo chủ sở hữu từng đối tượng**, không đổi tên nguyên schema.
  - `master` và `kho` đang trộn dữ liệu chung, nghiệp vụ nhiều module và kho cũ.
  - Một số migration thay hàm của phần khác.
  - CSDL thật chung `D:\DU-LIEU-KE-TOAN\postgresql` chưa dựng.
  - Cụm DEMO còn 303 CSDL test và 651 role test tồn đọng.
- **API hiện tại chưa là API Core đa người dùng.**
  - Nhóm `/api/that/...` chưa gắn người thao tác vào phiên.
  - Một số đường tải xuống chỉ kiểm đường dẫn.
  - Việc chạy lâu phân tán ở ba cơ chế.
- **Công cụ ngoài dùng lại được qua adapter**, nhưng chưa phải engine Core:
  - API Mask còn phụ thuộc trạng thái phiên;
  - bộ tải hóa đơn nguồn khác giao thức M2-00;
  - Engine Studio mới là bộ cấu hình.
- **OCR:** lấy `D:\GPT\OCR` (bản 2.1.0) làm nguồn hiệu chỉnh thành `e_ocr`. `ocr-dual-release` là bản phát hành cũ hơn (2.0.0). Giữ nguyên thuật toán, bổ sung adapter và lớp vận hành.

## Các phần

| Phần | Nội dung | Tệp | Review |
|---|---|---|---|
| KS-A | 12 khối Core (TL 54 §9) ↔ mã hiện có; chỗ tách tiến trình (CD-028) | `g0\KS-A.md` | `RV-AD.md`: 12/12 đúng, đã sửa vòng 2 |
| KS-B | CSDL, 67 migration → khối đích, role/RLS, tên, dọn test | `g0\KS-B.md`, `so-lieu-csdl-demo.json` | `RV-B.md`: Đạt |
| KS-C | Route/API hiện có → `/api/v1/`, quy ước, vi phạm | `g0\KS-C.md` | `RV-C.md`: 13/14 đúng, đã sửa vòng 2 |
| KS-D | Mask v2, Engine Studio, OCR-1, bộ tải hóa đơn, #6/E1, review XD, theo dõi khoản vay; TL 54 §12 | `g0\KS-D.md` | `RV-AD.md`: 12/12 đúng, đã sửa vòng 2 |
| KS-E | `D:\GPT\OCR` → `e_ocr`: bản đồ, API, danh sách hiệu chỉnh | `g0\KS-E.md` | `RV-E.md` (đang chạy) |

## Chờ Anh

Gom từ mục "Chờ Anh" của từng phần; chi tiết xem từng phần.

### Từ KS-A
- Chốt nguồn đăng nhập production và quan hệ pháp nhân–workspace; phiên DEMO hiện tại chưa thay thế được đăng nhập thật.
- Chốt retention cho bản gốc, OCR/cache, bản đã che, kết quả và dữ liệu tạm; mục tiêu thời gian phục hồi/mức mất dữ liệu chấp nhận được.
- Duyệt lần lượt ba bộ CSDL/API/SDK theo CD-029; các tên TL 55 vẫn là nháp.

### Từ KS-B
- Chốt ranh giới định danh/liên kết chung M2–M4, phần kho kế toán cũ và nơi giữ ánh xạ Mask.
- Chốt hạn giữ cùng quyền thực thi dọn tập CSDL/role test đã được lead xác minh; chưa coi số đếm là danh sách được phép dọn.

### Từ KS-C
- Chốt nguồn tài khoản production, vòng đời phiên và quan hệ người dùng–pháp nhân/workspace.
- Chốt module sở hữu các nghiệp vụ `/api/that/...`, cùng quyền đọc/duyệt/xuất tương ứng.
- Chốt thời hạn duy trì route cũ, phạm vi tương thích và chính sách lưu tệp/kết quả tạm.

### Từ KS-D
- Xác nhận đúng bản `engine-console`, `ocr-dual-release` và nguồn triển khai chính thức của #6/#7; bản vá trong repo chưa được coi là đã áp dụng.
- Chốt thông tin còn thiếu tại bảng §5, deployment khoản vay đang dùng và chính sách mở danh mục Mask sau khi engine khởi động lại.
- Lát này không đổi tệp; không chạy test/runtime. Chưa có bằng chứng hiệu năng hoặc nghiệm thu tích hợp mới.

### Từ KS-E
- Chốt phạm vi đợt đầu: OCR local + ABBYY, hay gồm cả hiệu đính AI/ứng dụng `ocr-abbyy-ai`.
- Chốt chính sách giữ bản gốc, OCR chưa mask, snapshot duyệt và thời hạn; cần tiếp tục duyệt thế nào sau khi engine đóng.
- Chốt máy chạy/tài khoản dịch vụ, tải đồng thời dự kiến và đầu mối Hot Folder/sổ hạn mức chung.
- Ba bộ đặc tả CSDL/API/SDK vẫn phải được Anh duyệt trước G2 (`CD:338–344`).
