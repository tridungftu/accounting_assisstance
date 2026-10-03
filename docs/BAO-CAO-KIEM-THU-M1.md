# Báo cáo kiểm thử bản lõi M1

> Báo cáo lịch sử bàn giao M1. Kết quả toàn bộ sau A08 nằm trong [BAO-CAO-KIEM-THU-M1-M6.md](BAO-CAO-KIEM-THU-M1-M6.md).

Ngày: 17/09/2026 · Phạm vi: code mới sau phê duyệt A07 · Môi trường: Windows, Python 3.12.14, thư viện chuẩn. **Toàn bộ dữ liệu là fixture; chưa có nghiệm thu nguồn thực hoặc kế toán.**

## 1. Kết quả đã chạy

Lệnh: `python -X utf8 -m unittest discover -s tests -v` với `PYTHONPATH=src`, dùng Python bundled trên máy. Kết quả lượt cuối: **42 tests, 2.907 giây, OK**, mã thoát 0. Bộ test ở [tests/test_m1.py](../tests/test_m1.py).

Đã thử launcher PowerShell `run.ps1 catalog` và `run.ps1 --data-dir var/launcher-smoke init`, đều thành công. Đã chạy riêng demo 14 bước qua CLI: init; nạp năm file; nạp lại sao kê; quét Base; kiểm tra bundle; status; backup; verify; restore; status trên kho khôi phục. Cả 14 bước trả mã 0.

Bằng chứng demo: [SUMMARY.json](../var/demo-reports/SUMMARY.json), [status trước backup](../var/demo-reports/10-status.json), [status sau restore](../var/demo-reports/14-restored-status.json). Các JSON là kết quả thực của CLI, không phải kết quả dựng tay. `var/` là đầu ra cục bộ được bỏ qua bởi gitignore.

Kết quả dữ liệu demo:

- Năm file có 12 bản ghi nguồn, tạo **11 thực thể chuẩn**: hai giao dịch sao kê, một HĐ từ hai nguồn, một Base và bảy thực thể Junsky fixture.
- Nạp lại sao kê: **0 thực thể mới, 2 bản trùng**; hai giao dịch cùng ngày/tiền nhưng khác tham chiếu vẫn tồn tại riêng.
- Base fixture: hai file, chỉ mục hai file, giải mã hai, không thiếu/dư/lỗi.
- HĐ XML–bảng kê: một header; giữ hai dòng hàng và hai nguồn chứng cứ.
- Backup/restore: số lượng và tổng theo loại/tiền tệ/snapshot khớp; integrity OK, foreign-key check không có lỗi; raw được kiểm tra checksum và có đủ trong bộ khôi phục.

Lượt kiểm thử đầu phát hiện kết nối SQLite chưa đóng trong backup khiến Windows không đổi tên được thư mục. Đã sửa bằng đóng kết nối rõ ràng và kiểm tra lại. Kết quả 42/42 ở trên là sau sửa lỗi.

## 2. Đối chiếu T01–T15 của kế hoạch

| Mục | Đã kiểm chứng | Giới hạn / còn chờ |
|---|---|---|
| T01 | Tiền âm, Decimal, INTEGER 64-bit, phân cách khai báo; chặn float/bool/số lẻ/overflow/tiền tệ ngoài phạm vi | Tiền tệ/dấu trên nguồn thật chưa được kế toán xác nhận |
| T02 | Giữ số 0 của mã/tài khoản; Đ/đ chuẩn hóa đúng; raw giữ nguyên | Chưa thử Excel thực |
| T03 | Nạp lại, đổi tên file và file khác hash có dữ liệu chồng kỳ không tăng trùng | Chỉ fixture với khóa được khai báo ổn định |
| T04 | Hai giao dịch cùng ngày/tiền khác tham chiếu được giữ; thiếu chứng cứ khóa bị chặn; cùng khóa khác nội dung rollback toàn file | Chưa kiểm chứng tính duy nhất mã NH thực |
| T05 | Hợp nhất HĐ hai nguồn; giữ detail và provenance; header/detail mâu thuẫn không ghi đè | Chưa có XML/bảng kê thực |
| T06 | Giữ trạng thái/quan hệ thay thế dù chưa có HĐ gốc; không dựng bản gốc | Chưa áp dụng nghiệp vụ điều chỉnh/hủy hoặc quy trình duyệt revision; không tự suy tác động kế toán |
| T07 | Quét thư mục, so chỉ mục, báo thiếu/dư, lỗi base64/JSON, ID lặp và đường dẫn vượt phạm vi | Format chỉ mục/item **JSON fixture**, chưa phải Base Excel/JSON thực |
| T08 | Dữ liệu không thuộc fixture, bao gồm PDF, bị từ chối; không báo đã đọc thành công | **Chưa có parser PDF**; chưa kiểm tra trang nối/dòng dài/layout thật |
| T09 | Tổng header/detail HĐ, tổng file, đầu–cuối sao kê và cân Nợ/Có chứng từ fixture; snapshot được báo riêng | Chưa đối chiếu tổng được kế toán ký; chưa xác minh sai HĐ giữa sổ và nguồn (M5) |
| T10 | Sai pháp nhân/as-of/tiền tệ bị chặn; bundle thiếu vai trò/metadata lệch không đạt | Chưa chứng minh “mới nhất” từ Junsky; chưa có cổng mở phiên M3 |
| T11 | Inject lỗi ở bản ghi thứ hai: rollback; ngắt tiến trình con trong transaction: không có dữ liệu chuẩn nửa chừng, retry thành công | Lần bị ngắt được giữ STAGED để truy vết, status liệt kê chưa kết thúc; chưa tự giải quyết nghiệp vụ |
| T12 | FK chặn orphan; migration nâng phiên bản/giữ dữ liệu/rollback; khóa xung đột chặn; hai tiến trình nạp không nhân đôi | Chưa có hai lần xuất Junsky thật để xác nhận ID ổn định; chưa xác minh quan hệ danh mục nghiệp vụ đầy đủ |
| T13 | ISO/UTC, khoảng [từ, đến), known_at NULL, cutoff không thấy header chưa biết; detail đến sau không xuất hiện trong bằng chứng trước cutoff | Chỉ primitive/M1 evidence; quản trị hiệu lực/phiên bản tri thức và backtest toàn hệ thống thuộc M2/M6 |
| T14 | Backup với kết nối nguồn đang mở; snapshot không đổi khi nguồn tiếp tục nạp; restore đủ raw/config, chặn tamper/thiếu raw/đường dẫn sai/ghi đè | Chưa thử trên bộ dữ liệu thực hoặc môi trường vận hành kế toán |
| T15 | Nạp và nạp lại toàn bộ bộ fixture năm nguồn đạt | **Chưa đạt nghiệm thu thực:** chưa có bộ mẫu thực, đáp án hoặc người ký |

## 3. Tình trạng bàn giao

**Có bản lõi M1 chạy và được kiểm thử bằng fixture. Chưa đóng toàn bộ M1.** Các phần quản trị hiệu lực/đề xuất/duyệt/xuất/đối soát/học không được báo hoàn thành chỉ vì đã có contract.

Chưa chạy backtest 12 tháng, chưa đo các tỷ lệ trong bản 1.2, chưa xác nhận khả năng tái sử dụng script cũ, chưa import Junsky hoặc kiểm thử UI. Không có nguồn thật nào được đánh dấu đã tích hợp.

Hướng dẫn chạy tại [README.md](../README.md). Để đi tiếp trong M1, cần mẫu nguồn được phép sử dụng, tổng kiểm soát/metadata và xác nhận ý nghĩa khóa; đầu mối dữ liệu/đáp án kế toán vẫn cần được chỉ định cụ thể.
