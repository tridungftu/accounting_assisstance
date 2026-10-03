# Chuyển từ fixture sang vận hành thật

**Cập nhật V8 — 24/09/2026:** Mở `MỞ PHẦN MỀM.cmd` để dùng giao diện `that` cục bộ: staging năm nguồn, đọc nguồn, tri thức chờ duyệt, phiên đề xuất, duyệt từng dòng và shadow. Không phải gửi file qua chat. Vẫn không có import Junsky; xem [hướng dẫn vận hành](HUONG-DAN-VAN-HANH.md).

Ngày 18/09/2026. Theo yêu cầu của Anh: hướng dẫn cách chuyển sang vận hành thật. Đây là lộ trình tích hợp và vận hành đề xuất, chưa phải biên bản đã nghiệm thu hoặc đã ghi sổ. Không thay các quyết định A07/A08 hay tự gán sự phê duyệt của kế toán trưởng.

## 1. Hiện có gì và còn phải làm gì

Đã có code sáu module và báo cáo 90 tests trên fixture. Kiểm tra trực tiếp code ngày 18/09/2026 xác nhận:

- `Config.load` chỉ nhận environment fixture và entity kết thúc `_FIXTURE`.
- Catalog nguồn ghi mọi adapter thực là `WAITING_FOR_SAMPLE`; adapter hiện nhận JSON mô phỏng với `synthetic=true`.
- `ReviewExport.export` từ chối target khác fixture bằng `JUNSKY_MAPPING_MISSING`.
- Chưa có mẫu thực hoặc mapping được xác nhận trong tập tài sản sản phẩm đã kiểm kê; mọi mode hiện vẫn dùng dữ liệu giả lập.

Vì vậy chưa có lệnh PowerShell để mở vận hành hạch toán thật; `start-web.ps1` chỉ mở tiếp nhận file gốc và khu mô phỏng. Đổi tên PLHN_FIXTURE, sửa cờ synthetic hoặc bỏ điều kiện chặn không tạo ra khả năng đọc file thật hay xuất đúng Junsky. Cần phát triển adapter thực, kiểm chứng mapping và bổ sung cấu hình/luồng chạy thực tách biệt sau khi có mẫu.

Giữ nguyên một ứng dụng Python, SQLite, Excel, offline và sáu module. Phạm vi pilot vẫn là sao kê PLHN; hóa đơn/Base là chứng cứ. Khuyến nghị tích hợp đầu tiên với một tài khoản ngân hàng và một tháng đã hoàn tất; đây là lát cắt kiểm chứng ban đầu, không bỏ năm nhóm nguồn hoặc giảm phạm vi thiết kế đã duyệt.

## 2. Bộ dữ liệu kế toán chuẩn bị trước

| Nhóm | File/thông tin cần có | Dùng để xác nhận |
|---|---|---|
| Thông tin bộ mẫu | PLHN/MST và mã pháp nhân trong Junsky, tháng, ngân hàng/tài khoản, định dạng tiền, người cung cấp/kiểm tra | Đúng phạm vi; không lấy mã giả lập làm mã doanh nghiệp |
| Sao kê | File gốc PDF/Excel của tháng chọn; số dư đầu/cuối, tổng thu/chi và số giao dịch để đối chiếu | Đọc đúng layout, dấu tiền, ngày, khóa giao dịch và tổng |
| Hóa đơn | XML và bảng kê Excel có cùng các HĐ liên quan; trường hợp trả nhiều HĐ/trả một phần nếu có | Nối đúng HĐ, không đếm hai lần giữa XML/bảng kê; lưu điều chỉnh/thay thế |
| Base | Chỉ mục Excel và thư mục dữ liệu liên quan của kỳ, giữ cấu trúc thư mục gốc | Kiểm tra bộ đọc thực, số lượng và liên kết chứng từ. Nếu kỳ không có phát sinh, kế toán xác nhận rõ |
| Junsky xuất | Công nợ theo HĐ; danh mục đối tượng, tài khoản, khoản mục, dự án; kỳ khóa; sổ 112/NKC hoặc chứng từ chi tiết | Số còn mở và bằng chứng thực về TK, tiền, HĐ, đối tượng, dự án/khoản mục |
| Mốc đầu/cuối kỳ | Công nợ đầu kỳ và phát sinh hoặc snapshot có căn cứ thời điểm; bộ cuối kỳ cùng phạm vi | Tái dựng đúng trạng thái tại lúc đề xuất. Không đưa số dư cuối kỳ làm đầu vào cho đề xuất đầu kỳ |
| Junsky import | Template CB_tmpEntry1/2, một file đã import thành công, một file lỗi nếu có và kết quả trên sổ sau import | Schema, kiểu dữ liệu, header/detail, EntryID/DebtID, import lại/import một phần; không đoán mapping |
| Tri thức | Từ điển/khóa cứng/28 mã/mapping thực nếu có; 10–15 mẫu sao kê đã được kế toán trưởng duyệt và ngày hiệu lực | Đề xuất có căn cứ. Thiếu mẫu cho loại nghiệp vụ nào thì giữ ngoại lệ loại đó |
| Đáp án kiểm tra | Hạch toán/phân bổ đúng cho giao dịch trong bộ kiểm tra, có người xác nhận; tách khỏi đầu vào engine | Đo đúng thực tế thay vì tỷ lệ người dùng chấp nhận |
| Tài sản bản 1.2 | Script khảo sát, từ điển và kho lịch sử nếu đã có ở nơi khác | Kiểm kê/chạy kiểm tra để xác nhận phần có thể dùng lại, không tự suy từ tên tài liệu |

Với mỗi file xuất, giữ thời điểm xuất, phạm vi/bộ lọc, as_of, tổng kiểm soát và người xuất. Khi không có bằng chứng known_at của lịch sử, ghi chưa biết; kết quả chỉ là đối chiếu hồi cứu có giả định, không gọi là backtest đúng thời điểm.

Chưa cần gom đủ 12 tháng để bắt đầu viết và thử adapter. Cần đủ nguồn liên quan cho lát cắt được chọn; trước khi nghiệm thu chất lượng tổng thể phải bổ sung kỳ/ngoại lệ đủ đại diện. Nếu chưa có tháng lịch sử đủ mốc, có thể bắt đầu ghi nhận bộ nguồn hiện tại để chạy song song sau khi adapter sẵn sàng.

Không chỉnh cột/đổi mã hoặc biến nguồn thật thành JSON có `synthetic=true` để vượt kiểm tra. Nếu dùng bản ẩn thông tin cho phát triển, giữ nhất quán mã thay thế giữa các nguồn, cấu trúc, quan hệ và tổng kiểm soát. Bản gốc dùng đối chiếu tại môi trường nội bộ được phép.

## 3. Lộ trình và điểm hoàn thành từng bước

| Bước | Tôi/IT thực hiện | Anh/kế toán thực hiện | Điều kiện sang bước tiếp |
|---|---|---|---|
| 1. Tích hợp nguồn thực | Kiểm kê file/script thực; ghi mapping; bổ sung parser và kiểm thử từng layout; đối chiếu số dòng/tổng; thiết kế kho/cấu hình thực riêng, giữ nguyên demo | Cung cấp bộ mẫu và xác nhận khóa, dấu tiền, cột, phạm vi, tổng | Nạp nguồn đầy đủ, lỗi có báo cáo; nạp lại không tăng số chứng từ; tổng khớp nguồn được xác nhận |
| 2. Chạy song song chỉ tạo đề xuất | Nạp tri thức đã duyệt; chạy trên bản sao dữ liệu, xuất workbook duyệt; đo sai/đúng và phần thiếu; sửa lỗi | Kiểm tra độc lập với sổ/đáp án; chốt tiêu chí chất lượng và trường hợp phải xử lý tay | Đạt tiêu chí đã chốt; mọi sai lệch về tiền, khóa, HĐ, ghi sổ trùng được xử lý; có người xác nhận kết quả. Chưa import lại tháng lịch sử |
| 3. Thử tương thích Junsky | Hoàn thiện xuất Entry1/2 đúng mẫu và xác minh sau import; thử một phần/lặp/lỗi/restore trên bộ được phép | Bố trí môi trường Junsky thử hoặc bản sao riêng; trực tiếp thực hiện/cho phép từng lượt import thử | Đọc lại đúng chứng từ, dòng Nợ/Có, đối tượng, HĐ/phân bổ, dự án/khoản mục; hiểu rõ hành vi import lại và cách phục hồi |
| 4. Pilot một phiên thật | Chuẩn bị phiên, kiểm dữ liệu mới, tạo đề xuất/workbook, xuất batch đã duyệt, lưu manifest và đối soát sổ nhập lại | Chọn nhóm giao dịch hiện tại chưa ghi sổ; duyệt từng chứng từ, thực hiện import và xác minh; phân công người nhập/kiểm | Phiên khớp đầy đủ; không còn khoản chưa xác minh/chênh trong phạm vi; backup/restore đã kiểm tra; Anh quyết định mở rộng |

Chạy song song và xuất thật là hai khả năng riêng. Sau bước 1 mới có thể đưa ra lệnh chạy dữ liệu thật chính xác; chưa tạo lệnh hoặc tên chế độ chưa được hiện thực. Không ước lượng ngày hoàn tất adapter/pilot từ tỷ lệ “60% đã có” hoặc số tests fixture; ước lượng lại sau khi kiểm tra bộ mẫu và phản hồi Junsky.

Nếu chưa có môi trường thử Junsky, cần thống nhất phương án thử trên bản sao với người quản trị trước bước 3; không lấy môi trường sổ đang dùng làm môi trường thử mặc định. Không tự giả định Junsky có sandbox, API hoặc tự chống import trùng.

## 4. Chu trình mỗi phiên khi bản thực đã được nghiệm thu

1. Người phụ trách lấy bộ sao kê/HĐ/Base và bộ Junsky mới, cùng phạm vi/thời điểm; kiểm tra phiên trước, kỳ khóa và khả năng chứng minh khoản đã ghi sổ.
2. Chốt cửa sổ thao tác theo D10: không ghi tay/import các khoản cùng phạm vi trong lúc dùng snapshot. Nếu có thay đổi, lấy lại bộ nguồn và rà soát phần bị ảnh hưởng trước xuất/import.
3. Tạo đề xuất, giữ chỗ công nợ; dòng thiếu hoặc ngoài mẫu được chuyển cho kế toán xử lý, không đoán trường còn thiếu.
4. Kế toán duyệt từng chứng từ trong Excel. Sửa trường/phân bổ phải có lý do và qua kiểm tra lại. Pilot không dùng duyệt nhanh cả lô.
5. Chụp backup nhất quán; xuất một batch có ID/hash, chỉ gồm bản duyệt cuối. Người được giao nhập vào Junsky và giữ kết quả nhập/lỗi.
6. Xuất lại sổ chi tiết và công nợ từ Junsky để đối soát từng item. Số dư giảm không tự chứng minh đúng chứng từ/TK/dự án; nhập một phần thì xác minh phần đã nhập trước mọi xử lý tiếp.
7. Chỉ đưa trường đủ chứng cứ vào nhãn học. Cuối kỳ đối soát toàn bộ phạm vi; còn chênh/chưa xác minh thì chưa chốt tháng trong ứng dụng.

Sự cố nhập thật không được xử lý bằng cách gửi lại cả batch, xóa SQLite hay chạy lại demo. Điều chỉnh/hủy chứng từ trên Junsky phải theo quy trình kế toán được xác nhận, có nguồn xuất lại chứng minh kết quả. Phát sinh ngoài batch cần quy trình xử lý riêng trước nghiệm thu; hiện còn chặn chốt tháng nếu chưa giải quyết.

## 5. Việc Anh cần cung cấp ngay

- Chọn tháng và tài khoản ngân hàng cho lát cắt đầu tiên, hoặc cho biết bộ dữ liệu hiện có nằm ở đâu để tôi kiểm kê trước.
- Chỉ định một đầu mối cung cấp nguồn/đáp án, một người duyệt nghiệp vụ và người phụ trách import Junsky. Anh không cần tự chạy mọi test kỹ thuật, nhưng cần có kế toán xác nhận nghiệp vụ thực.
- Đưa đường dẫn bộ file gốc và mẫu import đã dùng thành công. Chưa có mẫu import vẫn bắt đầu kiểm kê/adapter nguồn; phần xuất thật tiếp tục chờ schema xác nhận.

Đây là yêu cầu thông tin để bắt đầu phần tích hợp còn thiếu, không phải yêu cầu duyệt lại kiến trúc sáu module đã thống nhất. Hướng dẫn không thay đổi code/cấu hình, không tạo DB thực và không thực hiện import Junsky.
