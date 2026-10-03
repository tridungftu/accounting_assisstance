# V0 — kết quả kiểm kê và tái hiện tháng 08/2026

Ngày 18/09/2026. **V0 hoàn thành; kế hoạch V1–V6 chờ Anh duyệt. Chưa sửa code sản phẩm.** Dự án đủ tài sản để bắt đầu V1, chưa được xác nhận vận hành hạch toán thật.

## 1. Đã thực hiện

Đọc bộ prompt vòng 2, báo cáo độc lập, converter/runner và tài liệu nguồn bắt buộc; kiểm kê các thư mục được chỉ định bằng danh sách file thực; mở 57 đường dẫn workbook read-only; đọc sâu năm script chính, kiểm tra AST/I/O của 23 script. Không chạy các script nguồn có ghi đè, không chạy lại converter phụ thuộc Linux/pickle thiếu. Không cài dependency.

Giải nén gói thử vào bản sao riêng để giữ nguyên thư mục gốc. Chạy `chay_thu.py` hai lần trong hai kho V0 mới, dùng 13 JSON có sẵn. Bản runner chỉ đổi đường dẫn Windows, nơi ghi kết quả, actor mô phỏng, ẩn nội dung dòng khỏi console và thêm đồng hồ từng pha; bỏ thao tác xóa đệ quy vì dùng đích mới. Không sửa thuật toán/đáp án/ngưỡng/phê duyệt của kịch bản gốc. Các bước approval C1/C2 chỉ tái hiện mô phỏng có trong gói cấp, không duyệt tri thức cho vận hành.

Lần dùng cho bảng dưới: `replay-20260918T111158927230Z`. Exit code 0; lỗi có chủ đích `SESSION_INPUT_CHANGED` ở bước 33 là kiểm tra gói cũ bị chặn, không phải lần chạy thất bại. Nạp 5 hóa đơn trùng bị từ chối là lỗi sản phẩm cần sửa đã tái hiện, không được tính thành nạp thành công.

## 2. Bảng so sánh tháng 8

| Chỉ tiêu | Gốc 18/09/2026 | V0 trên máy này | Kết luận |
|---|---|---|---|
| Sao kê nạp / trùng khi nạp lại | 105 / 105 | 105 / 105; thêm 0 khi nạp lại | Khớp |
| XML / bảng kê mới / bảng kê trùng bị chặn | 75 / 19 / 5 | 75 / 19 / 5 | Khớp lỗi cũ; chưa sửa |
| Tri thức C2: POLICY / IDENTIFIER / CASE | 52 / 35 / 0 | 52 / 35 / 0 | Khớp; 133 mã đối tượng |
| C1 FULL trên 105 / phủ theo tiền | 25 / 34.99% | 25 / 34.99% | Khớp |
| C2 FULL trên 105 / phủ theo tiền | 51 / 46.70% | 51 / 46.70% | Khớp |
| C2 FULL có đáp án: đối tượng / TK Nợ / TK Có / dự án | 12/44 · 36/40 · 36/40 · 13/16 | 12/44 · 36/40 · 36/40 · 13/16 | Khớp |
| Không mẫu duy nhất (C2) / hòa thứ tự / hết hạn / đã ghi sổ (C3) | 54 / không tách riêng / chưa có chỉ số / 64 | 54 / không tách riêng / chưa có chỉ số / 64 | Không biến chỉ số chưa đo thành 0 |
| Mở phiên C2 / đề xuất 105 | Báo cáo ≈1 s / 19 s; runner gốc không tách hai pha | 27.74 s / 38.15 s | Phép đo mới; không so 19 s như propose riêng |
| Toàn bước phiên C1 / C2, gồm workbook | 18,4 s / 19,3 s | 77.8 s / 124.7 s | Chậm hơn; chưa quy nguyên nhân cho một thành phần |
| Toàn bước đánh giá C2, hai baseline | 25,9 s | 141.7 s | Runner thực chạy 105 dòng/baseline, 62 dòng có đáp án |
| Workbook C2 / PHAN_BO gồm header | 3,174,387 byte / 52.606 hàng | 3,176,053 byte / 52.606 hàng | Cùng quy mô; có UUID mới, không so hash workbook |
| Fixture tự động | 111/111 được báo cáo | 111/111 thực chạy, 0 lỗi, 0 fail, 0 skip | Đạt |
| Toàn vẹn SQLite / khóa ngoại | OK / không lỗi | OK / không lỗi | Đạt |

Đã đối chiếu riêng **105/105 dòng C1 và 105/105 dòng C2 giống về ngày, chiều, tiền nội bộ, trường đề xuất, constraints, completeness và phần chưa phân bổ**, bỏ UUID ngẫu nhiên. Không đưa tiền hay định danh từng giao dịch vào báo cáo này. Tỷ lệ tiền là tổng trị tuyệt đối tiền của dòng FULL / toàn bộ 105 dòng.

**Giới hạn thời gian:** lần chạy đầu có bước C2 kéo dài 19.158,9 giây qua giai đoạn phiên làm việc bị gián đoạn; không coi là benchmark bình thường. Lần thứ hai C1 mở 8.59 s, đề xuất 15.05 s; C2 như bảng. Thời gian các bước vẫn biến động lớn; chưa tách được ảnh hưởng máy/IO/ngắt quãng khỏi chi phí code, không quy tất cả cho N+1. Chưa đo lại với 2.027 mã; các số 60/159/360 giây chỉ thuộc báo cáo cấp. V5 phải đo lại pha bằng full danh mục trong điều kiện kiểm soát.

**Đính chính đơn vị phép đo:** prompt gọi “đánh giá 62×2”, nhưng JSON dataset hiện có 105 dòng và 62 dòng có truth; runner tạo đề xuất cho toàn bộ mỗi baseline. Khi V5 nghiệm thu phải báo cả số dòng chạy và số dòng có đáp án, đồng thời đo đúng cohort 62×2 được yêu cầu; không so hai phép đo khác kích thước như cùng chỉ tiêu.

## 3. Phát hiện có tác động tới kế hoạch

- Có thực 809 quy tắc, 164 ánh xạ STK, 2.027 đối tượng; 431 regex/33 nhóm; 149 NCC và 28 khoản mục. Chưa phải số hàng tri thức đã được kế toán duyệt. Nguồn có 24 PDF, 8 xls, 1.907 XML/67 bảng kê, CSV 1.907/5.198/2.716; Base 1.283 thư mục đề nghị so 1.115 dòng chỉ mục.
- Năm header XML/bảng kê trùng trong gói thử **chỉ khác source_status**, không khác tiền. Core giống đã được gộp từ trước. Cần sửa phân biệt trạng thái nguồn/canonical core và quarantine, không viết lại toàn bộ cơ chế hợp nhất.
- Định danh cứng đã giữ ưu tiên đối tượng; thiếu đường kích hoạt POLICY theo khóa và CASE. Normalize Đ→D đã đúng; substring/regex mới là phần thiếu.
- Từ điển thiếu 3B KHÓA CỨNG. Entry1 thực có 17 cột gồm ErrorText, khác 16 trong V6. File JUNSKY-CHI/THU-T8 có trên đĩa nhưng chưa chứng minh đã nhập thành công.
- Script PDF hiện viết 7 sheet nhưng workbook kết quả có 9; nhiều script cần pickle không có và dùng float. Chưa chứng nhận tái dùng nguyên trạng. Runtime thiếu xlrd; pandas hiện có chưa được thử tương thích các script cũ.
- JSON thử có known_at/approval hồi cứu, công nợ tái dựng, kỳ khóa giả định, bank_reference sổ lấy từ Tập chuẩn; POLICY đều không yêu cầu công nợ. Kết quả này không chứng minh độ đúng ngoài mẫu hoặc khả năng phân bổ công nợ thật.

Tám phát hiện và bổ sung bộ chấm được ghi từng file/dòng, cách sửa, tác động schema ở [QUYET-DINH.md mục 8](QUYET-DINH.md#8-vòng-2--tiếp-nhận-v0-ngày-18092026), tất cả **chờ quyết định**. Không tự thay các quyết định vòng 1.

## 4. Tài liệu và bằng chứng bàn giao

| Tài liệu | Nội dung |
|---|---|
| [HIEN-TRANG.md](HIEN-TRANG.md) | Mục 3 cập nhật đúng tài sản mới, kích thước/ngày sửa/đường dẫn |
| [TAI-SAN-VONG-2.md](TAI-SAN-VONG-2.md) | 23 script với I/O/dependency, 57 đường dẫn workbook, nguồn và giới hạn tái dùng |
| [QUYET-DINH.md](QUYET-DINH.md) | Tám phát hiện, bộ chấm, mâu thuẫn, phân biệt đã giao/chờ duyệt |
| [KE-HOACH-VONG-2.md](KE-HOACH-VONG-2.md) | V1–V6: đầu vào, schema/migration, test, nghiệm thu, tám lựa chọn có mặc định |
| [TIEN-DO.md](TIEN-DO.md) | Đúng sáu module, thêm đợt V0–V6 |
| [HOP-DONG-DU-LIEU.md](HOP-DONG-DU-LIEU.md) | Ghi chú đề xuất V2; contract sản phẩm chưa đổi |

Bằng chứng tổng hợp không có chi tiết giao dịch: [DOI-CHIEU-V0.json](../var/vong-2/V0/DOI-CHIEU-V0.json), [TESTS.json](../var/vong-2/V0/TESTS.json), [BAO-TOAN-NGUON.json](../var/vong-2/V0/BAO-TOAN-NGUON.json). Log/DB/đề xuất/workbook có dữ liệu thật nằm trong `var/vong-2/V0/`, không đưa vào tests/fixtures hoặc chat. Bản manifest lần đầu được giữ tại LAN-CHAY-DAU.json, lần sau LAN-CHAY-V0.json.

Kiểm tra SHA-256: **64 file được bảo vệ không đổi**, không thêm file sản phẩm/test. Phạm vi hash gồm file gốc ở root, src, tests (trừ pycache) và thư mục thử nguyên bản; không tuyên bố hash toàn bộ nguồn ngoài dự án. Không xuất file Junsky từ sản phẩm, không nhập Junsky và không duyệt tri thức vận hành.

## 5. Cách chạy lại, phần chưa xác minh và cổng tiếp theo

Anh chưa cần kiểm thử tay ở V0. Nếu cần tái hiện, lệnh dưới luôn vào đúng thư mục; mỗi lần tạo kho V0 mới, giữ nguồn. Bộ replay có dữ liệu thật chuyển đổi và sự kiện duyệt mô phỏng, không dùng làm kho vận hành.

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
& 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 '.\var\vong-2\V0\tai_hien_v0.py'
& 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 '.\var\vong-2\V0\tong_hop_v0.py'
```

Lệnh chạy test độc lập đã thực hiện:

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
& 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 '.\tests\run_suite.py' --report '.\var\vong-2\V0\TESTS.json'
```

Chưa xác minh: parser thực từng layout, tổng tiền toàn kỳ trực tiếp từ nguồn, danh sách chênh ID Base, metadata snapshot/known_at thật, full danh mục về hiệu năng, chuẩn và bằng chứng nhập Junsky, nghiệm thu kế toán. Các phần này có nơi xử lý cụ thể tại V1–V6.

Điều kiện nghiệm thu V0 đã đáp ứng: kiểm kê thực, tái hiện kết quả/thuyết minh sai lệch thời gian, đối chiếu tám phát hiện bằng code, kế hoạch và không quá 10 lựa chọn. Bước kế tiếp là Anh duyệt kế hoạch và giao V1. Cổng dừng lấy từ mục Cách dùng và V0 của BO-PROMPT-CODEX-VONG-2.md: “Dừng để tôi duyệt kế hoạch V1–V6 trước khi code.”
