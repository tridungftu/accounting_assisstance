# Hướng dẫn vận hành kho `that`

**Mở phần mềm:** nhấp đúp `MỞ PHẦN MỀM.cmd`. Giao diện tại `http://127.0.0.1:8766` hiển thị dải đỏ **KHO THẬT — PLHN**, có sáu màn hình: Kho, Nạp dữ liệu, Tri thức, Phiên và đề xuất, Duyệt bút toán, Xuất và đối soát. Không gửi tệp vào chat và không cần Internet. `MỞ BẢN DEMO.cmd` chỉ dành cho dữ liệu giả lập.

Trên màn hình **Nạp dữ liệu**, chọn đúng một trong năm nguồn, chọn tệp/thư mục, khai ngày `as_of`, coverage, căn cứ `known_at`, rồi bấm nạp. Tệp được sao chép nguyên trạng vào vùng cục bộ trước khi bộ đọc chạy nền; xem JSON báo cáo, cách ly và danh sách mã ngoài danh mục trước khi mở phiên. Mã ngoài danh mục không chặn cả lô và không tự được thêm.

Trên màn hình **Tri thức**, nạp workbook rồi rà từng dòng chờ duyệt. Chỉ actor `CFO_NTD` mới ghi Duyệt/Từ chối. Trên màn hình **Duyệt bút toán**, mọi quyết định là từng dòng và chọn mã từ danh mục hiệu lực. Màn hình **Xuất và đối soát** chỉ tạo file shadow, luôn ghi rõ không nhập Junsky.

Ảnh kiểm tra giao diện được chụp từ kho `that` trống tách biệt; dải trạng thái, sáu màn hình và cờ không nhập Junsky là các dấu hiệu phải kiểm trước khi nạp nguồn.

Ngày 17/09/2026. Anh đã để kiểm thử tay sang bước sau. Hiện chỉ cần đọc báo cáo bàn giao; không bắt buộc chạy các bước dưới để tiếp tục coding.

## 1. Tự chạy toàn bộ, không cần mở Excel

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\test.ps1
```

Kết thúc phải có `OK` và `status: PASS`; báo cáo tại `var/test-results/latest.json`, có số bài, tên test, lỗi, Python và hash code/test. Test dùng thư mục tạm riêng. Nếu Python trên PATH thiếu openpyxl, dùng runtime đã kiểm tra trên máy:

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\test.ps1 -PythonExecutable 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
```

Demo hai phiên, tự tạo workbook và mô phỏng duyệt/ghi sổ:

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
$kttDemo = Join-Path 'var' ('demo-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
.\run.ps1 demo-full $kttDemo
```

Đầu ra `PASS_FIXTURE`, 2 phiên, tổng chi 200, công nợ cuối 0, backup đã kiểm tra. Báo cáo nằm trong `<thư mục demo>/reports`. Mốc 01/10/2026 là thời gian mô phỏng; không có sự kiện thực tương ứng được tuyên bố.

## 2. Khi Anh kiểm thử tay Excel sau này

Workbook trong demo đã dùng để duyệt nên không nhập lại các bản cũ nhằm thay quyết định. IT tạo **phiên fixture mới**, dùng `session-open` → `session-propose` → `review-export`, lấy `path` trong kết quả để Anh mở.

1. Mở file bằng Excel. Sheet **DUYET**: mỗi dòng là một giao dịch sao kê. Xem ngày, diễn giải, tiền và năm trường `doi_tuong`, `tk_no`, `tk_co`, `du_an`, `khoan_muc`.
2. Cột `quyet_dinh`: chọn **WAIT** nếu để lại, **APPROVE** nếu duyệt, **REJECT** nếu từ chối. Không có nút duyệt nhanh cả lô trong chương trình; demo ghi APPROVE tự động chỉ để kiểm thử.
3. Nếu sửa mã hoặc từ chối, ghi `ly_do`. Mã là chuỗi, giữ số 0 đầu. Không đổi các cột định danh/phiên bản; cột kỹ thuật được ẩn để giảm nhầm lẫn.
4. Sheet **PHAN_BO**: xem công nợ từng HĐ, chỉ sửa `tien_duyet`. Tiền phân bổ dùng số nguyên VND không âm. Tổng phải bằng trị tuyệt đối tiền sao kê nếu mẫu dùng công nợ; không vượt số còn mở sau các khoản giữ chỗ khác. Mẫu trực tiếp như phí không dùng phân bổ HĐ.
5. Lưu thành **file mới**, đóng Excel rồi IT chạy `review-import`. Nếu một dòng sai, toàn bộ lần duyệt bị từ chối; không có cập nhật một nửa.
6. Kết quả mong đợi: `applied` là số chứng từ đã ghi quyết định; `pending` là dòng WAIT. Phải quyết định từng dòng trước `batch-export`. Sai mã/HĐ, workbook cũ hoặc sửa khóa phải bị chặn; lý do sửa không cho phép bỏ qua ràng buộc.

Workbook duyệt không phải file import Junsky. Batch sau xuất vẫn phải có sổ nhập lại và đối soát; không học từ APPROVE hoặc EXPORTED.

## 3. Giao diện CLI cho IT

Một lệnh chung: `workflow <action> <request.json>`. Các đường dẫn trong request nên là đường dẫn tuyệt đối. Actor do người chạy khai báo, chưa phải danh tính đã xác thực. Thời điểm dạng `2026-09-16T08:00:00+07:00`, lưu chuẩn UTC. Các ví dụ dưới chỉ đọc demo đã bàn giao:

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
$kttRequest = Join-Path (Get-Location) 'var\query-knowledge.json'
@{
    business_date = '2026-09-15'
    cutoff = '2026-09-16T08:00:00+07:00'
    category = 'POLICY'
} | ConvertTo-Json | Set-Content -LiteralPath $kttRequest -Encoding UTF8
.\run.ps1 --data-dir var/full-demo-final-v2/data workflow knowledge-query $kttRequest
.\run.ps1 --data-dir var/full-demo-final-v2/data status
```

| Action | Khóa JSON bắt buộc; tùy chọn trong ngoặc |
|---|---|
| knowledge-stage | items, actor, at; items là danh sách theo contract tri thức |
| knowledge-approve | identifier, actor, at |
| knowledge-revoke | identifier, actor, at, reason |
| knowledge-query | business_date, cutoff, (category) |
| knowledge-export | path, actor, at; xuất danh sách chưa có sự kiện duyệt/thu hồi |
| knowledge-import | path, actor, at; chỉ vào chờ duyệt |
| history-link | cutoff, (checker); kết quả liên kết có chứng cứ, không tự tạo nhãn |
| session-open | attempt_id, bank_ids, cutoff, actor, (mode=fixture) |
| session-propose | session_id, (baseline=A hoặc B) |
| session-cancel | session_id, actor, at, reason; chỉ phiên OPEN |
| review-export | session_id, actor, at |
| review-import | path, actor, at |
| batch-export | session_id, actor, at, (target=fixture); target khác bị chặn |
| batch-recover | batch_id, actor, at |
| batch-cancel-prepared | batch_id, actor, at, reason; chỉ khi chưa có file công bố |
| reconcile | batch_id, source_attempt_id, actor, at |
| label-from-journal | bank_id, journal_id, context, actor, at; chứng cứ lịch sử trực tiếp và người kiểm fixture |
| label-revoke | label_id, actor, at, reason |
| learning-rebuild | context, cutoff, business_date, settings |
| rule-propose | item, actor, at; luôn chờ kiểm chứng/duyệt |
| dataset-register | path; fixture dataset có ID/version, split, cutoff, bằng chứng đáp án |
| evaluate | dataset_id, actor, at; trả A/B theo từng split, không tự cho vận hành |
| candidate-evaluate | candidate_id, dataset_id, gate_id, actor, at; cần holdout và QUALITY_GATE_FIXTURE đã duyệt |
| blind-export | dataset_id, path, actor, at; chỉ các hàng BLIND, để trống đáp án |
| month-close | month, source_attempt_id, actor, at; month dạng YYYY-MM |
| reconstruct | anchors, movements, as_of, cutoff; chỉ tính tiến từ mốc quá khứ đã biết |

Request thực tế phải lấy ID từ kết quả lệnh trước hoặc DB/report; không tự tạo ID Junsky. `--output` ghi JSON kết quả mới, không ghi đè file có nội dung khác. `inspect.signature` kiểm tra khóa thừa/thiếu ở lớp CLI, các service kiểm tra ràng buộc nghiệp vụ.

## 4. Phục hồi và ngoại lệ

| Tình huống | Cách xử lý |
|---|---|
| Nạp nguồn thất bại | Xem report/locator, sửa file đầu vào thành bản mới; raw cũ giữ nguyên. Nạp lặp hợp lệ không tạo giao dịch trùng |
| Workbook cũ/sai khóa/mã không hợp lệ | Không sửa DB. Tạo workbook mới từ phiên hiện hành, rà soát và duyệt lại |
| Nguồn hoặc tri thức đổi trước xuất | Hủy phiên OPEN, lấy bộ mới và mở lại; bản duyệt cũ không đi tiếp |
| Batch PREPARING chưa có file công bố | `batch-recover` nếu đầu vào còn hợp lệ; nếu nguồn đã đổi, `batch-cancel-prepared` có lý do, rồi mở phiên mới. Không xóa audit/artifact |
| File đã công bố nhưng DB chưa hoàn tất | `batch-recover` kiểm checksum và hoàn tất chính batch/ID cũ. Nếu nguồn đã đổi sau công bố, kết quả đánh dấu `source_changed_after_publication=true`; cần đối soát, không tạo file nghiệp vụ mới hoặc tái nhập cả batch |
| File công bố bị sửa/hỏng | Bị từ chối; giữ để điều tra, phục hồi từ backup vào kho khác. Không ghi đè bản hỏng một cách âm thầm |
| Import một phần/không rõ đã import | Nạp sổ/snapshot mới và reconcile từng item; giữ khoản chưa rõ, không giải phóng để xuất lặp. Không tự gửi lại cả file |
| RECON_A | Nguồn có phạm vi đủ nhưng không tìm thấy chứng từ đã xuất; chưa xác minh/không nhãn |
| RECON_B | Phát sinh ngoài batch: ứng viên điều tra, không tự làm nhãn hoặc bỏ qua khi chốt tháng. Quy trình nghiệp vụ thực chờ kế toán xác nhận |
| RECON_C / UNRESOLVED | Điều tra sai tiền/HĐ/TK/dự án hoặc chứng cứ mơ hồ; không bù chênh trái dấu. Chứng cứ sửa là bản nguồn mới, không sửa raw |
| Thiếu mẫu chính sách | Đề xuất PARTIAL/NONE; không đoán trường hoặc cấp quyền chạy thật |

## 5. Backup và phạm vi nghiệm thu

Lệnh đầy đủ ở [README](../README.md). Dùng SQLite backup API cùng tất cả artifact được DB tham chiếu. Restore vào thư mục mới rồi `status`, kiểm count/hash, `batch-recover` nếu cần dựng lại file đã xuất. Có thể khôi phục backup schema v1/v2 và nâng schema khi mở bằng ứng dụng mới. Không copy DB đang ghi bằng lệnh copy thông thường.

Chưa có kế toán/IT ký UAT, xác nhận cửa sổ thao tác Junsky, phân quyền hệ điều hành, mã pháp nhân thật, schema import hoặc ngưỡng G0/G1/G2. Test xanh chỉ cho phép kết luận mức kỹ thuật fixture. Bốn tài liệu nguồn và quyết định trước vẫn được giữ; báo cáo chẩn đoán hiện tại không thay bộ sáu phần báo cáo kỳ chưa được cung cấp.

## 6. Vận hành kho that sau V7

Các lệnh dưới dùng kho riêng `var/plhn-that`, không bật xuất hay nhập Junsky. Dừng nếu báo `XLRD_OFFLINE_WHEEL_MISSING`: cài wheel offline `xlrd==2.0.2` đã được duyệt hoặc lưu bản `.xlsx` cạnh file `.xls`; không tải thư viện từ mạng.

Khởi tạo và nạp năm nguồn. Thay tham số ngày bằng bằng chứng của lần kết xuất; `--known-at` là tùy chọn khi thời điểm biết đã rõ hơn `exported-at`.

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\run-that.ps1 init
.\run-that.ps1 nap-nguon --nguon sao_ke --duong-dan 'D:\nguon\Sao ke NH T08.xlsx' --as-of 2026-08-31 --exported-at '2026-09-03T00:00:00+07:00' --known-at-basis 'eFAST export' --coverage-from 2026-08-01 --coverage-to-exclusive 2026-09-01
```

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\run-that.ps1 nap-nguon --nguon hoa_don --duong-dan 'D:\nguon\hoa-don\2026-08' --as-of 2026-08-31 --exported-at '2026-09-05T00:00:00+07:00' --known-at-basis 'tax gateway download' --coverage-from 2026-08-01 --coverage-to-exclusive 2026-09-01
.\run-that.ps1 nap-nguon --nguon bang_ke --duong-dan 'D:\nguon\hoa-don\2026-08\mua_vao\bang_ke_purchase_2026-08.xlsx' --as-of 2026-08-31 --exported-at '2026-09-05T00:00:00+07:00' --known-at-basis 'tax gateway download' --coverage-from 2026-08-01 --coverage-to-exclusive 2026-09-01
```

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\run-that.ps1 nap-nguon --nguon base --duong-dan 'D:\nguon\base\PLHN\2026' --as-of 2026-08-31 --exported-at '2026-09-12T00:00:00+07:00' --known-at-basis 'Base backup fetched_at' --coverage-from 2026-01-01 --coverage-to-exclusive 2026-09-01
.\run-that.ps1 nap-nguon --nguon junsky --duong-dan 'D:\nguon\Mang ngan hang\DANH MỤC' --as-of 2026-08-31 --exported-at '2026-09-03T00:00:00+07:00' --known-at-basis 'Junsky export declared by operator' --coverage-from 2026-01-01 --coverage-to-exclusive 2026-09-01 --snapshot-id SNAP_T8 --posting-evidence-complete --lock-from 2026-01-01 --lock-to 2026-08-01 --lock-scope PLHN-T1-T7
```

Xem report hoặc chỉ các dòng cách ly. `xem-cach-ly` ghi JSON có ordinal, mã lỗi, ngày, số chứng từ/hóa đơn và tiền; không in diễn giải.

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\run-that.ps1 report --attempt-id '<ATTEMPT_ID>'
.\run-that.ps1 xem-cach-ly --attempt-id '<ATTEMPT_ID>' --output 'var\van-hanh\cach-ly.json'
```

Nạp rồi xuất workbook tri thức. Chỉ người được Anh chỉ định mới điền `quyet_dinh=APPROVE|REJECT`; `REJECT` phải có `ghi_chu`. Chạy thử trước để kiểm workbook mà không ghi event.

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\run-that.ps1 nap-tri-thuc 'D:\tri-thuc\TU-DIEN-NHOM-NGHIEP-VU.xlsx' 'D:\tri-thuc\BO-QUY-TAC.xlsx' 'D:\tri-thuc\HOA-DON-CAY-PHAN-NHANH.xlsx' --actor 'IMPORTER' --at '2026-09-19T08:00:00+07:00'
.\run-that.ps1 xuat-tri-thuc --duong-dan 'var\van-hanh\tri-thuc-cho-duyet.xlsx' --actor 'IMPORTER' --at '2026-09-19T08:05:00+07:00'
.\run-that.ps1 duyet-tri-thuc 'var\van-hanh\tri-thuc-cho-duyet.xlsx' --actor 'CFO_NTD' --at '2026-09-19T09:00:00+07:00' --kho-thu
.\run-that.ps1 duyet-tri-thuc 'var\van-hanh\tri-thuc-cho-duyet.xlsx' --actor 'CFO_NTD' --at '2026-09-19T09:00:00+07:00' --chi-nhom 'NHOM,TU_KHOA,KHOA_CUNG,MAU_DINH_KHOAN,NGOAI_LE'
```

Liệt kê sao kê và mở phiên shadow. `attempt-id` của `mo-phien-that` là lần nạp Junsky có đủ scope, không phải ID Junsky. Nếu danh mục chưa khớp tri thức đã duyệt, lệnh nêu số phiên bản PENDING và dừng.

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\run-that.ps1 liet-ke-sao-ke --tu 2026-08-01 --den 2026-08-31 --chua-de-xuat --output 'var\van-hanh\sao-ke-T8.json'
.\run-that.ps1 mo-phien-that --attempt-id '<JUNSKY_ATTEMPT_ID>' --tu 2026-08-01 --den 2026-08-31 --cutoff '2026-09-19T10:00:00+07:00' --actor 'OPERATOR' --mode shadow --output 'var\van-hanh\phien.json'
```

Sau khi có `session_id`, các thao tác đề xuất, workbook duyệt, shadow và đối soát vẫn dùng request JSON có actor/thời điểm rõ. Các lệnh này không có đường import Junsky.

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
.\run-that.ps1 workflow session-propose 'D:\van-hanh\session-propose.json' --output 'var\van-hanh\proposals.json'
.\run-that.ps1 workflow review-export 'D:\van-hanh\review-export.json' --output 'var\van-hanh\review-export.json'
.\run-that.ps1 workflow review-import 'D:\van-hanh\review-import.json' --output 'var\van-hanh\review-import.json'
.\run-that.ps1 workflow shadow-export 'D:\van-hanh\shadow-export.json' --output 'var\van-hanh\shadow-export.json'
.\run-that.ps1 workflow shadow-reconcile 'D:\van-hanh\shadow-reconcile.json' --output 'var\van-hanh\shadow-reconcile.json'
```
