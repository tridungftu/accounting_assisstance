# Kiểm thử giao diện HTML v0.3.0

Ngày 18/09/2026 · A09 · chỉ dùng file kiểm thử do hệ thống tạo; không dùng dữ liệu kế toán thực.

## Kiểm thử tự động

`test.ps1` chạy **111 tests: PASS, 0 failure, 0 error, 0 skipped**, gồm 90 tests hồi quy M1–M6 và 21 tests mới của lớp tiếp nhận/server. Chứng cứ máy đọc: `var/test-results/latest.json`, có tên test, thời điểm chạy, Python và hash source/tests/tài sản giao diện/launcher.

| Nhóm | Nội dung được kiểm tra |
|---|---|
| Lưu và truy vết | Giữ nguyên byte/hash/tên; tải lại; mở kho lần nữa vẫn có dữ liệu; `known_at` chưa biết giữ null; không gán normalized/posted |
| Chống trùng hồ sơ | Đổi tên cùng nội dung; cùng tên khác nội dung; khác nguồn/pháp nhân/kỳ; nhận song song 12 lần chỉ có 1 receipt; dung lượng không đếm lặp raw dùng chung |
| Lỗi lưu và dữ liệu hỏng | Lỗi trước công bố receipt không báo thành công, thử lại được; raw sửa hash bị chặn tải/xác nhận trùng; receipt hỏng được cảnh báo |
| Kiểm tra đầu vào | Tên có đường dẫn/control char, nguồn sai, kỳ sai, field lạ, file rỗng/quá 50 MB, phần mở rộng ngoài danh sách |
| HTTP local | Chỉ bind 127.0.0.1; Host/Origin/token; chặn cross-site/CORS; chống đọc đường dẫn ngoài assets; từ chối Content-Length quá lớn trước khi nhận bytes; lỗi JSON không làm chết server |
| Tách kho | Fixture không vào hộp hồ sơ thật; nguồn thật không tự nạp qua adapter fixture; kiểm tra mẫu không ghi DB; nạp lại mẫu không thêm chứng từ |
| Vận hành | Phục hồi danh sách qua instance mới; assets phục vụ local; dừng server cần token đúng; không có chức năng xuất Junsky thật |

## Kiểm tra trực tiếp trình duyệt

Dùng riêng `var/ui-check`, cổng 18765; kho bàn giao `var/web` không chứa các file kiểm thử này.

- Trang HTML tải đúng tiếng Việt, CSS/JS local; đã xem ảnh giao diện trên màn hình desktop.
- Chọn `SAO-KE-KIEM-THU.csv` qua file chooser, gắn pháp nhân `KIEM_THU_UI` và ghi chú thử; nút lưu được bật.
- Bấm **Lưu hồ sơ**: báo 1 mới, 0 trùng, 0 lỗi; danh sách hiển thị “Chờ bộ đọc”.
- Tìm theo tên file, mở chi tiết: đúng pháp nhân/kỳ/ghi chú/hash và trạng thái chưa chuẩn hóa/ghi sổ.
- Tải lại trang: hồ sơ vẫn có trong kho.
- Nạp mẫu sao kê: 2 chứng từ mới; nạp lần hai: 0 mới, 2 trùng; hồ sơ raw vẫn tách biệt.
- Console không ghi nhận lỗi JavaScript ở các bước đã kiểm tra.
- Nút Dừng ứng dụng dừng đúng server kiểm thử, giao diện chuyển sang “Ứng dụng đã dừng”.
- Launcher chạy được qua Windows PowerShell 5.1, dừng/mở lại được; chọn mặc định cổng 8766 vì cổng 8765 trên máy đang có dịch vụ khác trả 404 tại health endpoint. Không dừng hoặc sửa dịch vụ khác đó.

Đã bấm nút tải gốc nhưng công cụ in-app browser không trả sự kiện download trong thời hạn; chưa xác minh file nằm ở thư mục tải xuống bằng UI đó. Endpoint tải gốc đã được test HTTP xác minh đúng byte, tên attachment và checksum. Không lấy việc không thấy lỗi console thay cho xác nhận tải xuống ở mọi trình duyệt.

Chưa kiểm thử tay bởi Anh/kế toán trưởng, chưa kiểm thử UI mọi kích thước màn hình, chưa nghiệm thu nguồn thực, ánh xạ Junsky hoặc độ chính xác hạch toán. 111 tests không đại diện nghiệm thu PLHN.
