# Báo cáo V9 — Định khoản nhanh

Ngày chạy: 26/09/2026. V9 thay V8b. Các số dưới đây là tổng hợp của kho sao chép; không chứa dòng giao dịch, mã tham chiếu hoặc diễn giải nguồn.

## Đã làm

- Màn hình mở đầu là **Định khoản**. Người vận hành chọn/thả sao kê, hóa đơn XML hoặc bảng kê; ứng dụng tự nhận nguồn, tạo đề xuất ngay và không yêu cầu phiên, mã phiên hay duyệt tri thức trước.
- Đề xuất nhanh được phép dùng tri thức `PENDING`; quyết định **Đồng ý** là cổng duy nhất để xuất. Mỗi quyết định lưu actor `CFO_NTD`, học lại theo chứng từ và không học khi **Bỏ**.
- Nền Junsky, danh mục và ba workbook tri thức được nạp nền với actor `HE_THONG_JUNSKY`; danh bạ đối tác được đọc cục bộ. Không có thao tác nhập Junsky.
- File xuất sao kê chép từ mẫu nhà cung cấp khi mẫu có mặt, kiểm cấu trúc `CB_tmpEntry1` 17 cột và `CB_tmpEntry2` 37 cột, giữ `DocsNo` từ mã tham chiếu nguồn. Hóa đơn chỉ xuất file soát, ghi **CHƯA PHẢI FILE NHẬP**.
- Migration v16 bổ sung lượt định khoản nhanh, dòng quyết định và tri thức học. Ứng dụng `that` vẫn tách kho, và hai cờ import/xuất Junsky trong cấu hình vẫn là `false`.

## Kết quả F2 — tháng 8/2026

Chấm trên kho sao chép độc lập: nền Junsky cắt đến 31/07 có 8.155 bản ghi; nền đầy đủ có 8.302 bản ghi. Sao kê tháng 8 tạo 105 đề xuất trong 99,141 giây.

| Nguồn / chiều | Xanh | Vàng | Đỏ |
|---|---:|---:|---:|
| Sao kê THU | 0 chứng từ / 0 VND | 0 / 0 VND | 43 / 228.968.949.776 VND |
| Sao kê CHI | 0 chứng từ / 0 VND | 0 / 0 VND | 62 / 314.907.400.082 VND |
| Hóa đơn mua | Chưa chạy — không có nguồn tháng 8 được giao | Chưa chạy | Chưa chạy |
| Hóa đơn bán | Chưa chạy — không có nguồn tháng 8 được giao | Chưa chạy | Chưa chạy |

Lý do Đỏ được gộp như sau: thiếu TK Có 51 chứng từ / 193.208.324.892 VND; thiếu TK Nợ 19 / 216.156.398.592 VND; thiếu căn cứ còn lại 39 / 285.121.141.974 VND; mã đối tượng không hợp lệ 2 / 4.246.214.400 VND; mã dự án không hợp lệ 4 / 23.284.938 VND. Một chứng từ có thể có nhiều lý do nên các tổng theo lý do không cộng thành tổng chứng từ.

Tỷ lệ đúng TK Nợ, TK Có, đối tượng, dự án và khoản mục hiện là **không đo được** ở cả ba mức: sổ đầy đủ không có mã tham chiếu sao kê để ghép duy nhất với 105 dòng sao kê. Vì vậy mẫu đối chiếu bằng 0, không được báo là 0% đúng. Lần chạy lại với sổ đầy đủ cũng chưa nhận diện dòng nào **Đã có trong Junsky** vì cùng thiếu khóa ghép đó.

Không có dòng Xanh, nên không có trường hợp nào được gắn nhãn Xanh dưới 98%. Ngưỡng Xanh giữ ở mức bảo thủ: mọi trường bắt buộc phải có căn cứ đã duyệt/xác minh; V9 không hạ ngưỡng để tạo tỷ lệ Xanh.

## Kiểm thử và giới hạn

- Toàn suite: **178/178 PASS**, hoàn toàn synthetic; migration v16 được tạo trong kho kiểm thử.
- Đã khởi động lại giao diện local và xác nhận trang đầu là **Định khoản**; màn hình không trình bày ID phiên hay mã lỗi kỹ thuật cho thao tác thường.
- Chưa có tệp hóa đơn tháng 8 để chạy F1/F2 cho mua/bán.
- Sổ Junsky hiện thiếu khóa tham chiếu sao kê nên chưa thể kiểm chứng tỷ lệ đúng hoặc chống trùng theo cặp sao kê ↔ sổ. Đây là giới hạn dữ liệu nguồn, không phải kết luận chất lượng nghiệp vụ.
- Không có quyết định `CFO_NTD`, không có `quick_learning`, và không có file nào được nhập vào Junsky trong kho chính.

Chứng cứ máy: `var/vong-2/V9-giao-viec/TESTS.json` và `var/vong-2/V9-giao-viec/F-score/KET-QUA-F2.json`.
