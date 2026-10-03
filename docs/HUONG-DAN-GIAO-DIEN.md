# Nhập hồ sơ bằng giao diện HTML

Ngày 18/09/2026 · v0.3.0 · Theo yêu cầu A09 của Anh.

## Mở ứng dụng

Tài liệu này mô tả **bản demo**: trong thư mục `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức`, nhấp đúp **MỞ BẢN DEMO.cmd**. Kho vận hành PLHN dùng `MỞ PHẦN MỀM.cmd` và được hướng dẫn tại [HUONG-DAN-VAN-HANH.md](HUONG-DAN-VAN-HANH.md). Không cần gửi file vào chat, không cần tài khoản AI hoặc Internet.

Nếu muốn dùng PowerShell, chạy nguyên khối:

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\start-web.ps1
```

Launcher mở Python nền, chỉ nhận kết nối trên chính máy này. Mở launcher lần nữa sẽ dùng lại ứng dụng đang chạy với đúng thư mục và phiên bản. Không mở trực tiếp `index.html`: file HTML riêng lẻ không có dịch vụ Python để lưu hồ sơ.

## Nhập file của Anh

1. Trong **Nhập dữ liệu**, bấm **Chọn tệp** hoặc kéo file từ máy vào vùng nhận tệp. Có thể chọn nhiều file; **Chọn cả thư mục** nhận các file phù hợp trong thư mục con.
2. Chọn **Loại dữ liệu**: sao kê, hóa đơn XML, bảng kê hóa đơn, Base hoặc Junsky. Điền **Pháp nhân**, **Kỳ dữ liệu**, ghi chú nếu cần. Mỗi lượt dùng cùng loại nguồn/pháp nhân/kỳ; tách lượt nếu thư mục có nhiều nhóm hoặc nhiều kỳ.
3. Bấm **Lưu hồ sơ**. Kết quả ghi rõ số hồ sơ mới, số file trùng đã có và số file chưa lưu. File lỗi giữ lại trong danh sách, kèm lý do để sửa và thử lại.
4. Vào **Hồ sơ đã nhận** để tìm tên file/pháp nhân/kỳ/ghi chú, lọc loại nguồn, bấm **Chi tiết** và **Tải tệp gốc**.

Hỗ trợ tiếp nhận PDF, XLSX, XLS, XML, CSV, TSV, JSON, TXT, ZIP; mỗi file tối đa 50 MB, mỗi lượt chọn tối đa 300 file. Không nhận file rỗng. ZIP được giữ nguyên, chưa giải nén. Giao diện không chỉnh sửa file nguồn trên máy Anh.

**“Đã nhận — chờ bộ đọc” nghĩa là đã lưu file, chưa đọc các dòng nghiệp vụ, chưa chuẩn hóa, chưa hạch toán và chưa xuất Junsky.** Kỳ Anh nhập là nhãn quản lý hồ sơ, không phải máy đã xác minh thời điểm nghiệp vụ. Bộ đọc thực sẽ được phát triển và kiểm chứng theo mẫu nguồn sau đó.

Cùng nội dung + pháp nhân + kỳ + nguồn: nhận lại không tạo hồ sơ mới, kể cả đổi tên; giữ tên/ghi chú lần đầu. Cùng tên nhưng nội dung khác: lưu riêng. Đây là chống trùng file; chưa thay việc chống trùng giao dịch trong sao kê xuất chồng kỳ. Không tự sửa/xóa receipt đã lưu trên giao diện.

## Thử dữ liệu mẫu

Bấm **Thử dữ liệu mẫu** ở góc trên. **Nạp mẫu sao kê** thêm hai giao dịch chi 100 VND vào kho mô phỏng; nạp lần hai tạo 0 chứng từ mới và bỏ qua 2 dòng trùng. **Nạp bộ mẫu Junsky** dùng hợp đồng giả lập nội bộ.

Nếu có file JSON fixture, chọn file trong khu này. **Kiểm tra tệp mẫu** chỉ kiểm tra, **Nạp vào kho mô phỏng** mới ghi vào SQLite. JSON `synthetic=true` bị từ chối ở khu hồ sơ thật để tránh nhập nhầm. Khu mẫu không chứng minh layout Junsky thật đã được hỗ trợ; không dùng file fixture để import Junsky.

Giao diện hiện phục vụ tiếp nhận/tra cứu và thử nạp nguồn. Các nghiệp vụ duyệt Excel, xuất batch fixture, đối soát và đánh giá M2–M6 vẫn dùng quy trình hiện hữu trong [hướng dẫn M1–M6](HUONG-DAN-VAN-HANH.md); chưa có màn hình thao tác từng nghiệp vụ đó.

## Lưu trữ, đóng và mở lại

| Thành phần | Vị trí dưới thư mục dự án |
|---|---|
| File thật đã nhận | `var/web/ho-so-goc/raw/<sha256>.bin` |
| Tên gốc, nguồn, kỳ, ghi chú, hash và trạng thái | `var/web/ho-so-goc/receipts/<id>.json` |
| SQLite và raw mô phỏng của giao diện | `var/web/mo-phong/` |
| File fixture chọn qua giao diện | `var/web/mo-phong-upload/` |
| Log khởi động | `var/web/server-out.log`, `var/web/server-error.log` |

Không đổi tên các file hash trong kho. Nút tải gốc trả lại đúng byte, dùng tên trên receipt và kiểm tra checksum trước khi trả file. Dung lượng trên trang đếm các raw blob được receipt tham chiếu, không cộng lặp blob cùng nội dung.

Đóng tab không xóa hồ sơ và không dừng Python. Nút **Dừng ứng dụng** dừng server cục bộ; bấm khi đã lưu xong. Sau khi tắt máy, mở lại bằng launcher để tiếp tục dùng cùng kho. Không cần để Codex mở khi dùng ứng dụng. Khi đổi máy cần chuẩn bị Python 3.11+ và openpyxl 3.1.x trước, cùng source và dữ liệu đã sao lưu.

## Sao lưu hồ sơ thật

**Backup SQLite bằng lệnh `backup` cũ không bao gồm kho tiếp nhận `ho-so-goc`.** Trước khi sao lưu kho này, bấm **Dừng ứng dụng**. Sau đó sao chép toàn bộ `var/web/ho-so-goc` (cả raw và receipts) sang vị trí sao lưu của Anh. Chỉ giữ receipt mà thiếu raw thì không phục hồi được file gốc.

Ví dụ tạo bản sao mới trong dự án, sau đó Anh có thể chuyển bản sao sang ổ lưu trữ riêng:

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
$kttBackupPath = Join-Path $PWD ('var\sao-luu-ho-so-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
if (Test-Path -LiteralPath $kttBackupPath) { throw 'Thu muc sao luu da ton tai.' }
Copy-Item -LiteralPath (Join-Path $PWD 'var\web\ho-so-goc') -Destination $kttBackupPath -Recurse -ErrorAction Stop
Write-Output $kttBackupPath
```

Bản sao cùng ổ đĩa chỉ phục vụ phục hồi thao tác; cần bản sao ở ổ khác cho sự cố ổ đĩa. Khi phục hồi, giữ nguyên bản hiện hữu, dừng app và dùng một thư mục kho phục hồi mới chứa `ho-so-goc`, không chép đè lẫn hai kho. `start-web.ps1 -DataRoot` có thể mở kho ở vị trí khác; mở đồng thời trên cổng khác sẽ là kho riêng.

## Khi không mở được

- Cổng 8766 đang được ứng dụng khác dùng: launcher báo lỗi, không tắt tiến trình khác. Có thể mở kho này trên cổng khác bằng khối lệnh sau.
- Tải lại trang nếu báo phiên giao diện đã đổi sau khi khởi động lại server.
- Lỗi lưu file: xem lỗi dưới tên file; kiểm tra dung lượng/quyền ghi. Thử lại an toàn vì ứng dụng kiểm tra trùng nội dung.
- Máy khác không truy cập được URL này là đúng phạm vi hiện tại: đây là ứng dụng chạy trên một máy, chưa phải web dùng chung qua mạng.

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\start-web.ps1 -Port 8767
```

Không mở đồng thời cùng một kho ở nhiều cổng. Chỉ chọn cổng khác khi cổng mặc định không thể dùng và kho này chưa chạy ở cổng khác.
