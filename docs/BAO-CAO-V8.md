# Báo cáo V8 — giao diện kho `that`

## Đã làm

- Tách launcher: `MỞ PHẦN MỀM.cmd` mở `cau_hinh.that.toml`; `MỞ BẢN DEMO.cmd` giữ kho fixture.
- Bổ sung sáu màn hình local: Kho, Nạp dữ liệu, Tri thức, Phiên và đề xuất, Duyệt bút toán, Xuất và đối soát.
- Nạp năm nguồn qua staging bất biến, xử lý nền, báo cáo/cách ly/mã ngoài danh mục; local token và loopback-only.
- Mở phiên shadow cho sao kê, hóa đơn và Base. Hóa đơn mua dùng MST được duyệt, vocabulary riêng, policy hiệu lực và lines net/VAT/phải trả; không có căn cứ thì chờ.
- Danh mục/cây hóa đơn dùng ngày hiệu lực cấu hình; eFAST nhận chu kỳ ISO; shadow không gọi import Junsky.

## Kiểm thử

`tests/test_v8.py` dùng toàn bộ dữ liệu/workbook giả lập: hóa đơn mua có ba lines cân đối và duyệt UI qua service; ngày hiệu lực danh mục; chu kỳ eFAST ISO; khởi tạo `Operations` chỉ chấp nhận kho `that`. Toàn bộ suite **175/175 PASS**, 0 failure/error, ghi tại `var/vong-2/V8-giao-viec/TESTS.json`.

## Lệnh mở ứng dụng

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\MỞ PHẦN MỀM.cmd
```

## Chưa xác minh

- Sao kê `.xls` cần wheel `xlrd==2.0.2` offline hoặc bản `.xlsx` tương đương.
- Chưa có quyết định/mapping Junsky, UAT kế toán, bằng chứng nhập Junsky hoặc quyền bật import.
- Vocabulary/policy hóa đơn và liên kết chuỗi chứng từ chỉ dùng khi được nạp và duyệt; tên đối tác không là khóa cứng.

## Giả định

Xem `GIẢ ĐỊNH-V8-1…4` tại [QUYET-DINH.md](QUYET-DINH.md). Không có tri thức nào được tự duyệt và không có dữ liệu thật trong test.
