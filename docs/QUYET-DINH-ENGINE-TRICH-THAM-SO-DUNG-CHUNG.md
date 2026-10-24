# Engine trích tham số dùng chung cho M4, CRM và M2

**Quyết định của Anh ngày 21/10/2026 — ĐÃ CHỐT về kiến trúc.** M4, CRM và M2 sử dụng một engine trích tham số hiện có; từng lần trích yêu cầu bộ tham số phù hợp. Tài liệu này bổ sung quyết định mới cho các handoff, không phải bằng chứng code hoặc nghiệm thu.

## 1. Dùng một lõi hiện có

- Engine nguồn là #6 trong `D:\Claude\Ho tro review ho so xay dung\review_xaydung\trich_xuat`.
- Giữ engine tại dự án nguồn, các module gọi qua interface/API dùng chung. Không tạo engine M4, engine CRM và engine M2 riêng; không sao chép thêm lõi trích vào từng module.
- Tận dụng bộ đọc tài liệu/bảng, danh mục, quy trình trích, quy tắc, nguồn trích và màn hình soát hiện có. Các bản sao tham chiếu/lịch sử đã có được giữ nguyên; khi chuyển interface phải xác minh đường gọi thực, không để hai lõi cùng xử lý.
- Chỉ phần trích tham số được dùng chung ở quyết định này. Luồng nộp/review/duyệt đợt M4, giao kết CRM và tiếp nhận hóa đơn M2 tiếp tục theo trách nhiệm đã chốt.

## 2. Từng lần trích mang bộ yêu cầu riêng

Cổng gọi chung cần gắn tài liệu/phiên bản nguồn, loại hợp đồng, danh mục/phiên bản danh mục và danh sách mã tham số yêu cầu. Nếu có tham số dạng bảng, giữ yêu cầu bảng và nguồn từng dòng.

**Hiện có:** API nguồn đã nhận JSON tại `POST /api/trich_xuat/{luot}/chay`; dịch vụ đọc `opts.get('tham_so')` để chọn mã tham số. Phải mở rộng từ đường gọi này.

**Cần triển khai/kiểm:** loại hợp đồng, ràng buộc phiên bản danh mục và quy tắc theo loại xuyên suốt request–run–output. Tên trường cuối cùng bám API thật; không coi các trường còn thiếu là đã có.

- Mỗi lần trích chụp danh mục/quy tắc riêng của lần đó; không đổi biến danh mục toàn cục theo module khiến hai request lẫn bộ tham số.
- Không có loại/danh mục hoặc mã yêu cầu không hợp lệ thì báo rõ; không âm thầm fallback sang danh mục xây dựng.
- Kiểm tra tập mã yêu cầu rõ ràng: phân biệt không truyền, danh sách rỗng và chọn toàn bộ; không âm thầm bỏ mã lạ hoặc biến danh sách rỗng thành trích tất cả.
- Output giữ mã tham số, giá trị/trạng thái, nguồn trích và phiên bản đã dùng. Tham số không được yêu cầu phải phân biệt với tham số đã tìm nhưng thiếu, không áp dụng hoặc không quy định; không điền số 0 thay phần thiếu.
- Danh mục và quy tắc dùng chung được mở rộng theo loại. Adapter của module chỉ ánh xạ vào/ra, quyền và ngữ cảnh; không chép lại quy tắc trích.
- Kiểm khớp output nguồn #6 `bang[]` với contract tiếp nhận `tham_so[]`; nếu cần chuyển dạng, dùng một adapter chung và giữ raw nguồn. Bộ đọc bảng hiện có chưa tự thành DTO bảng typed giữ ô/dòng; phần E3 mở rộng ngay trong #6, không viết bộ trích bảng riêng cho mỗi module.
- Quyền truy cập tài liệu và cổng AI/Mask hiện hành vẫn áp dụng. Quyết định dùng chung engine không tự bật cloud hoặc gửi tài liệu thật ra ngoài.

## 3. Trách nhiệm và xác nhận giữ đúng từng module

- **M4:** phòng dự án soát/xác nhận tham số hợp đồng xây dựng; Anh/sếp duyệt đợt; kế toán xác nhận nghiệm thu/công nợ.
- **CRM:** giữ quy trình soát/duyệt tham số và giao kết theo tài liệu 41–42; không lấy xác nhận M4 thay xác nhận CRM.
- **M2:** dùng kết quả/căn cứ hợp đồng phù hợp cho nghiệp vụ mua; không tự duyệt công nợ từ kết quả engine.

Dùng chung kết quả nguồn có kiểm phiên bản và quyền; không đồng nhất các bước xác nhận nghiệp vụ này.

## 4. Thứ tự giao Claude

1. Tiếp tục M4 và CRM đã được Anh giao. Chuẩn hóa interface dùng engine chung trong gói CRM/engine liên quan; không dựng thêm lõi trước khi đến gói E1-MUA.
2. **Sau CRM: M2-00** — [nút Tải từ cổng thuế](GIAO-CODE-M2-00-TAI-HOA-DON-TRONG-M2.md), dùng lại #7.
3. **Sau M2-00, tuần tự: E1-MUA** — [danh mục tham số theo loại](GIAO-CODE-E1-MUA-DANH-MUC-THAM-SO-THEO-LOAI.md), mở rộng chính #6 dùng chung.

Hai gói mới đang ở hàng chờ, chưa khởi chạy. Không mở hai writer sửa chung engine/schema. Lượt sửa ba lỗi Review L1/L2 hiện tại chỉ sửa tích hợp/guard/UI, không xây engine trích mới.

## 5. Kiểm độc lập khi triển khai

- Ba module thực sự gọi cùng một implementation/version; từng request lấy đúng danh mục và đúng mã yêu cầu.
- Hai request dùng bộ yêu cầu khác nhau không lẫn dữ liệu/quy tắc; test xây dựng hiện có giữ nguyên kết quả.
- Kiểm nguồn/phiên bản, tham số dạng bảng, trường thiếu, quyền và lịch sử bằng đầu vào DEMO không rỗng.
- Kiểm riêng luồng nghiệp vụ và giao diện của từng module; engine đạt không tự thành cả M4/CRM/M2 đạt.

Giữ nguyên file và lịch sử; không xóa bản cũ khi chuyển đường gọi.
