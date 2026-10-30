# Phiếu hỏi Anh · 3 câu trước khi mở lập trình engine (CD-035, CD-036)

**Lập:** 30/10/2026, lead. **Trạng thái:** chờ Anh chọn.

**Bối cảnh:** bản giao việc 5 engine đã qua review chéo của Codex (18/18 dòng nguồn có thật) và review Opus bảng "dùng lại / bọc / sửa / viết mới". Định hướng "ưu tiên bọc code gốc" đúng ở cả 5 engine. Có 3 chỗ **không làm được nếu chỉ bọc mà không đổi cách chạy**, nên cần Anh chọn. Các lát không phụ thuộc 3 câu này vẫn giao được ngay khi mở lập trình.

| # | Vấn đề | A | B | C | Khuyến nghị |
|---|---|---|---|---|---|
| 1 | **AI của trích xuất hợp đồng.** Bản review xây dựng gọi thẳng máy AI theo kiểu có "khuôn trả lời" (bắt AI trả đúng mẫu tham số). Cổng AI chung hiện chưa có kiểu này | Mở rộng cổng AI thêm đường "Local có khuôn trả lời": chỉ Local, vẫn kiểm địa chỉ LAN/Tailscale. Sửa cổng AI của phần mềm, **không sửa bản review** | Cho trích xuất gọi thẳng máy AI như bản review cũ (ngoại lệ của TL 48) | Đổi câu hỏi của bản review sang mẫu của cổng AI: đổi thuật toán, phải sửa test gốc | **A** |
| 2 | **Tải hóa đơn từ cổng thuế cần người gõ CAPTCHA** trên cửa sổ trình duyệt. Engine chạy ẩn dưới tài khoản hạn chế thì không có ai gõ | Phần tải chạy trong một phiên Windows riêng có màn hình (ngoại lệ như ABBYY). Mỗi pháp nhân một hồ sơ trình duyệt, xóa sau phiên; mật khẩu lấy từ két của Core | Sửa bộ tải sang chạy ẩn, chuyển ảnh CAPTCHA về màn hình Core cho người gõ (sửa bản gốc) | Tạm chỉ làm phần **đọc** XML/ZIP; tải vẫn làm tay như hiện nay | **A** |
| 3 | **Mask và bí mật của engine.** Mask giữ mật khẩu danh mục trong bộ nhớ, chỉ mở khóa được ngay trên máy chủ (quy tắc của Mask v2). Nếu module và engine dùng chung một tài khoản máy, module đọc được khóa Mask | Anh mở khóa danh mục Mask tại máy chủ; Mask **không tự đóng** khi danh mục đang mở. Engine giữ bí mật (Mask, AI Cloud, tải hóa đơn, ABBYY) mỗi engine một tài khoản máy riêng, khác tài khoản module | Mask tự đóng như engine khác; mỗi lần cần gửi Cloud, Anh mở khóa lại | — | **A** |

**Anh trả lời:** một dòng, ví dụ **"Engine: 1A, 2A, 3A"**.

**Chi tiết:**
- `docs\47-core\engine\RV-ENGINE-OPUS.md`;
- `docs\47-core\engine\GIAO-ENGINE-1.md`, `GIAO-ENGINE-2.md` (đang sửa theo review).

## Kết quả Anh chọn (30/10/2026 17:30, CD-038)

- **Câu 1 – C:** đổi câu hỏi trích xuất sang mẫu cổng AI chung.
  - Chép phần trích xuất vào engine; không sửa bản gốc.
  - Đo lại độ chính xác trên bộ đáp án 37 tham số, không được thấp hơn bản gốc; thấp hơn thì dừng, báo Anh.
- **Câu 2 – A.**
- **Câu 3 – A.**
