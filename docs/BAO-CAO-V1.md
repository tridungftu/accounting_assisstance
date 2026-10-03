# V1 — Máy đề xuất và tri thức sao kê

**Đính chính theo A12/V1b:** Kết luận “đạt ngưỡng” bên dưới là kết luận lịch sử V1 đã bị thay thế. Anh không chấp nhận hồi cứu có mẫu sinh trong tháng 8 làm căn cứ nghiệm thu. V1 chưa đạt trên bộ lọc trước tháng 8; phần V1b ở cuối báo cáo là trạng thái hiện hành. Giữ nguyên số đo cũ để đối chiếu, không sửa các hồ sơ V1 trên đĩa.

Ngày 18/09/2026, thực hiện theo QV01–QV08/A11. Chỉ V1; giữ sáu module, Python/SQLite/Excel, offline. **Lõi V1 và ngưỡng độ đúng hồi cứu đạt:** trên cohort FULL gốc, đối tượng 19/44 (từ 12/44), TK Nợ 37/40 và TK Có 36/40 (gốc 36/40). Đây chưa phải nghiệm thu kế toán hoặc vận hành. Phần kiểm chứng cuối và số đo chi tiết ở cuối báo cáo.

## Phần đã triển khai

- POLICY payload v2 hỗ trợ khóa, regex và kết hợp; định danh đã xác minh giữ ưu tiên. Tên đối ứng chỉ là điều kiện mẫu; xung đột với đối tượng đã xác minh bị chặn.
- Chọn theo bậc 1–5 rồi hàng workbook. Validation chặn hai mẫu cùng partition/bậc/thứ tự và giao khoảng hiệu lực, ngay cả đang pending; runtime chặn hòa thứ tự hoặc nhiều partition cùng thắng.
- Regex có ranh giới từ và loại trừ năm trường hợp đã chỉ định; CASE theo số giao dịch/số chứng từ/hash, scope pháp nhân/tài khoản, hiệu lực và known_at. CASE trước POLICY, không vượt cổng dữ liệu hoặc bị RULE/nhãn học ghi đè.
- han_dung gồm ngày cuối, valid_to ngày kế tiếp; giữ raw, bằng chứng mẫu hết hạn. Schema v8 không đổi; payload v1 giữ tương thích fixture.
- Mẫu nhiều dòng chỉ có [thiết kế](THIET-KE-MAU-NHIEU-DONG.md). Chưa triển khai lines/Entry2 mới. Có cổng chặn 29 mẫu nguồn chứa nhiều tài khoản.
- Khóa dependency tùy chọn `source-xls = xlrd==2.0.2`; chưa cài vì V1 không đọc XLS và chưa có wheel offline được tìm thấy. V3 xử lý việc cài từ bộ offline.

## Kiểm thử và dữ liệu

Đã chạy 138/138 test đạt: 111 cũ + 27 V1. Có một lần chạy lỗi đồng thời tại bước kiểm đường dẫn receipt của giao diện cũ. Đã đưa kiểm đường dẫn vào cùng khóa tiếp nhận để thư mục ổn định; test đồng thời riêng và toàn suite sau sửa đều đạt. Đây là sửa hồi quy nhỏ phát hiện trong kiểm thử, không mở thêm tính năng UI. Lần gọi test thiếu PYTHONPATH ban đầu chỉ lỗi môi trường import; không dùng lần đó làm bằng chứng đạt.

Bằng chứng: [TESTS.json](../var/vong-2/V1/TESTS.json), [TESTS.log](../var/vong-2/V1/TESTS.log). Đối chiếu hash 18 file được theo dõi gồm nguồn gốc, tài liệu gốc, fixture và hai workbook đọc ở V1: tất cả không đổi; xem [BAO-TOAN-NGUON.json](../var/vong-2/V1/BAO-TOAN-NGUON.json).

Đã chuyển đủ 809 POLICY và 164 ánh xạ, giữ trạng thái nguồn, hàng/sheet/hash và known_at lúc đọc thực. Kho hồi cứu riêng mô phỏng C1: 182 DE_CU + 35 CHAC_CHAN + 290 danh mục; C2 thêm toàn bộ NHAP. Actor duy nhất của các sự kiện này là MO_PHONG_KIEM_CHUNG. Phê duyệt mô phỏng không biến 129 ánh xạ NHAP thành định danh đã xác minh; chỉ 35 CHAC_CHAN có dấu verified từ nguồn.

Bản chuyển tiếp cho vận hành vẫn pending toàn bộ 809+164, actor duyệt được chỉ định CFO_NTD. Chưa có kho `that` hoặc adapter thật; không tuyên bố đã nhập tri thức vào một DB vận hành. File pending nằm trong thư mục chạy chỉ bởi [LAN-CHAY-V1.json](../var/vong-2/V1/LAN-CHAY-V1.json).

110 hàng từ khóa rỗng là chữ ký không bắt được từ khóa nào theo script nguồn, được chuyển thành điều kiện phủ định tường minh. Tên đối ứng từ workbook sao kê được nối theo số giao dịch/ngày/tiền: 80 dòng tìm được duy nhất, 25 không có hoặc không duy nhất nên giữ thiếu; không điền tên từ đáp án. Chuẩn hóa viết tắt tên dùng phiên bản legacy-chung-v1 đã đối chiếu script nguồn.

## Giới hạn so sánh

C2 chọn được 68 mẫu: 52 bậc 1, 16 bậc 5; không đổi thứ tự nguồn để nâng điểm. Có 59 FULL, 5 PARTIAL, 41 NONE. Trong 51 FULL gốc, còn 46 FULL: 4 bị chặn bởi mã đối tượng ngoài danh mục và 1 bởi mẫu nhiều dòng. Kiểm tra thêm danh mục nguồn đủ 2.027 mã cũng không thấy 4 mã này (kể cả so hoa/thường); cần kế toán xác nhận tri thức nguồn, không giả định V5 sẽ tự sửa. Các nhóm cổng có thể trùng nhau nên không cộng tổng lỗi để suy số giao dịch.

5 dòng mất FULL chiếm 28,9853 điểm phần trăm giá trị toàn lát cắt; các dòng mới FULL bù 1,3884 điểm. Vì vậy phủ theo số dòng tăng nhưng phủ theo tiền giảm từ 46,6990% xuống 19,1021%. Không làm mờ sự giảm này bằng việc chỉ báo tỷ lệ FULL. Có 22 dòng có bằng chứng mẫu hết hạn; 14 trong đó không còn mẫu hiện hành khớp. Không có dòng hòa thứ tự. Trường hợp mẫu hết hạn nhưng còn mẫu hợp lệ khác được phép dùng mẫu hợp lệ.

Trên tập FULL mới có đáp án, đối tượng chỉ đúng 29/55: còn 26 dòng sai đối tượng, dù ngưỡng cải thiện V1 đạt. Cổng V1 là ngưỡng sửa máy đề xuất, không phải tỷ lệ đủ an toàn để tự duyệt/hạch toán. Tất cả sai/thiếu trên tập có đáp án được lưu riêng, cần tiếp tục xem xét tri thức và nghiệp vụ theo các đợt đã duyệt.

Đây là hồi cứu tháng 8 với tri thức hiện có, không phải backtest ngoài mẫu. Giữ known_at và thời điểm duyệt mô phỏng thực; không lùi ngày. Hợp đồng nguồn chưa thay đổi: dùng bản sao 13 JSON chuyển đổi của V0; các bản sao còn nhãn kỹ thuật fixture của bộ chạy cũ, không đổi nhãn hay nội dung file gốc. Bản gốc và dữ liệu thật không được đưa vào tests/fixtures.

Giữ 133 mã đối tượng để đối chiếu bộ gốc, chưa chuyển toàn bộ 2.027 mã (V5). Bản chuyển đổi cũ còn giả định công nợ và tham chiếu sổ có liên quan tập chuẩn; needs_open_item=false chỉ là điều kiện benchmark, không phải chính sách công nợ đã được kế toán duyệt. Không dùng kết quả này cấp phép vận hành.

Độ đúng được đếm riêng trên dòng FULL có đáp án; đồng thời đo trên đúng cohort FULL gốc (đối tượng 44, Nợ/Có 40, dự án 16), coi dòng nay không FULL là chưa đạt. Không dùng điểm tổng của bộ chấm cũ để che việc mất phủ; lỗi chấm NONE của bộ cũ để V5 xử lý. Số đo hiệu năng gồm đọc SQLite hiện hành, không dùng để cam kết tiến độ hay ngoại suy cho danh mục đầy đủ.

## Bảng so sánh tháng 08/2026 — lượt hoàn tất

Lượt chính thức: `replay-20260918T122154979077Z`; known_at đọc nguồn 18/09/2026 12:21:54 UTC. Lượt khảo sát dừng trước đó không dùng làm kết quả nghiệm thu. Dữ liệu tổng hợp tại [KET-QUA-V1.json](../var/vong-2/V1/KET-QUA-V1.json), phân tích cohort tại [PHAN-TICH.json](../var/vong-2/V1/PHAN-TICH.json).

| Chỉ tiêu | Gốc 18/09, JSON 133 mã | Sau V1, C2 mô phỏng |
|---|---|---|
| Sao kê nạp / trùng khi nạp lại | 105 / 105 | 105 / 105; nạp lại thêm 0 |
| XML / bảng kê mới / mâu thuẫn nguồn | 75 / 19 / 5 từ chối | 75 / 19 / 5 từ chối; để V2 |
| Tri thức: mẫu / khóa cứng / CASE | 52 / 35 / 0 | Nạp 809; hiệu lực tại 01/08 là 267, 31/08 là 241; 35 verified / 0 CASE. 164 ánh xạ đã phát, không phải 164 định danh verified |
| FULL, tỷ lệ tiền C1 | 25/105 · 34,9882% | 39/105 · 7,6387% |
| FULL, tỷ lệ tiền C2 | 51/105 · 46,6990% | 59/105 · 19,1021% |
| Đúng trên FULL hiện tại: đối tượng / Nợ / Có / dự án | 12/44 · 36/40 · 36/40 · 13/16 | 29/55 · 50/51 · 49/51 · 18/20 |
| Đúng trên cohort FULL gốc, không FULL coi chưa đạt | 12/44 · 36/40 · 36/40 · 13/16 | **19/44 · 37/40 · 36/40 · 13/16** |
| Không mẫu / hòa thứ tự | 54 / 0 | 37 / 0 |
| Hết hạn | Chưa đo | 22 có bằng chứng hết hạn; 14 không còn mẫu hiện hành khớp |
| Cổng nhiều dòng / mã ĐT ngoài danh mục / mã dự án ngoài danh mục | Chưa tách | 4 / 4 / 1; các lỗi có thể giao nhau |
| Có sổ T8: chặn đã ghi sổ / bằng chứng không rõ | 64 / 1 | 64 / 1 |
| Mở phiên / đề xuất 105 dòng | Khoảng 1 s / 19 s | 89,76 s / 354,33 s |
| Đánh giá A/B | Khoảng 25 s, mô tả gốc 62×2 | 184,70 s; code hiện chạy **105×2**, trong đó 62 dòng có đáp án |
| Workbook C2 | Khoảng 3,1 MB; 52.606 hàng PHAN_BO | 3.178.212 byte; 52.606 hàng PHAN_BO; tạo 36,42 s |
| Test đạt / tổng | 111/111 | **138/138** |
| SQLite integrity / foreign key lỗi | Đạt | ok / 0 |

Hiệu năng chưa đạt nhu cầu vận hành. Các lượt test có chạy đồng thời trong một phần replay; đây là số đo quan sát, không phải benchmark cô lập. Không so trực tiếp thời gian đề xuất với đánh giá để kết luận A/B nhanh hơn: số truy vấn và điều kiện transaction khác nhau. V5 phải tối ưu/đo lại trên đủ danh mục theo ngưỡng đã duyệt.

Validation cuối bổ sung chặn tên đối ứng ngoài bậc 3/4 và báo lỗi đúng kiểu khi trigger sai kiểu. Đã xác thực lại toàn bộ 1.263 payload của lượt hồi cứu bằng validator cuối; không có hàng bị loại, không thay logic khớp/xếp thứ tự hoặc kết quả đề xuất. Suite cuối có 27 test V1, đạt 138/138.

Danh sách từng dòng sai/thiếu có bank_id, mẫu chọn, đề xuất, đáp án: [SAI-CON-LAI.json](../var/vong-2/V1/SAI-CON-LAI.json), chỉ lưu nội bộ. Không dùng danh sách này tự sửa mẫu hay duyệt vận hành. Workbook C1/C2 và đề xuất C3 nằm trong thư mục lượt chính thức; đã hủy phiên mô phỏng, không tạo batch nhập Junsky.

**Kết luận cổng:** hoàn tất phạm vi code V1 và đạt ngưỡng cải thiện hồi cứu đã giao. Chưa nghiệm thu vận hành; còn độ đúng đối tượng thấp, mã nguồn không hợp lệ, mẫu nhiều dòng, dữ liệu công nợ/sổ/thuế và hiệu năng. Kế toán cần xác nhận tri thức nguồn; V2 tiếp theo xử lý hợp đồng dữ liệu khi Anh giao riêng. Không tự thực hiện V2 hoặc tự mở quyền xuất/nhập.

## Lệnh chạy lại

Lệnh dùng runtime đã có trên máy; tạo thư mục chạy mới, không ghi đè nguồn. Chạy hồi cứu có thể mất nhiều phút. Không phải lệnh vận hành hay nhập Junsky.

```powershell
Set-Location -LiteralPath 'D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức'
$env:PYTHONPATH = 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
& 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 tests/run_suite.py --report var/vong-2/V1b/TESTS.json
& 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 -u var/vong-2/V1b/chay_thu.py
& 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 var/vong-2/V1b/phan_tich.py
```

V2–V6 chưa thực hiện trong lượt này. Entry1 ở V6 phải đúng 17 cột có ErrorText; TU-DIEN phải đọc lại bản 9 sheet ở V4. Anh xác nhận chưa nhập Junsky: mọi file xuất tham khảo hiện có chưa chứng minh nhập thành công.

## V1b — Điều chỉnh theo A12, kết quả hiện hành

**Đã thực hiện thay đổi và đo lại; CHƯA ĐẠT nghiệm thu chất lượng.** Kết luận V1 trước đây dùng số hồi cứu có rò rỉ không còn hiệu lực. Chỉ cột “không rò rỉ” dưới đây dùng xét cổng; không hạ ngưỡng hoặc dùng độ đúng từng trường của dòng PARTIAL thay cho FULL.

### Thay đổi và bằng chứng

- Chuẩn bị hai bộ từ cùng workbook: hồi cứu 809 POLICY, bộ lọc trước 01/08/2026 còn 750; cả hai có 164 ánh xạ, 133 mã đối tượng. known_at=max(lan_dau, lúc đọc thực). 110 hàng thiếu từ khóa chuyển KEY bậc 2/4 theo lựa chọn Anh xác nhận trong chat; giữ source_tier/source_row. Bậc 5 bỏ counterparty, không bỏ yêu cầu phải xác định đối tượng.
- Hạn STK 365 ngày, tên/từ khóa 180 ngày, CHAC_CHAN không hết hạn. Ánh xạ chưa xác minh không có cột lần cuối nên lấy max lan_cuoi của quy tắc cùng STK và lưu hàng bằng chứng; không lấy ngày nhập làm ngày gặp. Regex loại trừ đưa ra CAU-HINH.json và thành biểu thức đầy đủ trong payload nguồn đã chuyển; literal_pattern chỉ còn dựng ranh giới từ chung.
- Cache snapshot category/cutoff, tự vô hiệu theo token sự kiện/phiên bản trong transaction; lọc hiệu lực ngày nghiệp vụ, không cache đáp án. Migration v9 thêm index tra thứ tự và token/trigger. Đã nâng schema trên bản sao DB V1: checksum v1–v8 không đổi, số dòng nghiệp vụ không đổi, integrity/foreign key đạt; [MIGRATION-CHECK.json](../var/vong-2/V1b/MIGRATION-CHECK.json).
- **152/152 test đạt**, gồm 138 cũ và 14 V1b; so query/expired và đề xuất khi bật/tắt cache, invalidation giữa hai instance/connection, rollback rồi ghi mới, không cho người gọi sửa cache, sử dụng index, migration, hạn dùng và không đoán đối tượng. Năm bẫy regex giữ nguyên kỳ vọng, biểu thức lấy từ dữ liệu fixture. [TESTS.json](../var/vong-2/V1b/TESTS.json).
- Đối chiếu riêng **105/105 đề xuất thực của bộ lọc trước T8**: bật cache, tắt cache và kết quả lượt chính thức giống hệt nhau. Pha preview đo riêng: 9,38 s khi bật, 68,98 s khi tắt; không thay số đo Sessions.propose ở bảng dưới. [CACHE-CHECK.json](../var/vong-2/V1b/CACHE-CHECK.json).
- Hồ sơ trong V1 và gói thử gốc được bảo toàn theo hash. Không tạo sự kiện duyệt vận hành; chỉ MO_PHONG_KIEM_CHUNG trong các kho mô phỏng. Chưa sang V2, chưa làm lines/Entry2, chưa nhập Junsky.

Đối chiếu **94 file được bảo vệ: 0 file đổi, 0 file thêm** trong V1/gói gốc; [BAO-TOAN-NGUON.json](../var/vong-2/V1b/BAO-TOAN-NGUON.json).

### Hai cột so sánh C2

| Chỉ tiêu | V1 không rò rỉ, kiểm tra độc lập | V1b hồi cứu (có rò rỉ) | V1b không rò rỉ — xét nghiệm thu |
|---|---:|---:|---:|
| POLICY được nạp | 750 | 809 | 750 |
| Sao kê / đáp án / mã ĐT | 105 / 62 / 133 | 105 / 62 / 133 | 105 / 62 / 133 |
| FULL / PARTIAL / NONE | 55 / 1 / 49 | 63 / 15 / 27 | 57 / 14 / 34 |
| Cohort gốc: đối tượng | 12/44 | 19/44 | **13/44 — đạt >12** |
| Cohort gốc: TK Nợ | 36/40 | 32/40 | **28/40 — không đạt ≥36** |
| Cohort gốc: TK Có | 32/40 | 33/40 | **28/40 — không đạt ≥36** |
| Cohort gốc: dự án | 13/16 | 7/16 | **6/16 — không đạt ≥13** |
| Đúng trên FULL hiện tại: ĐT / Nợ / Có / DA | 18/51 · 45/47 · 41/47 · chưa nêu | 26/48 · 46/47 · 47/47 · 12/14 | 16/42 · 38/41 · 38/41 · 8/10 |
| Phủ theo tiền, mẫu số toàn bộ | Khoảng 17,5% | 6,8362% | **5,1180%** |
| Số dòng / tỷ trọng tiền chờ nhiều dòng | 6 / chưa nêu chính xác | 4 / 27,6919% | 6 / 28,6012% |
| Phủ theo tiền sau loại chờ nhiều dòng khỏi mẫu số | Chưa nêu | 9,4542% | **7,1681% — không đạt ≥46,7%** |
| Mẫu sinh trong T8 được chọn | 0 | 24 | **0** |
| Xung đột định danh do mẫu bậc 5 | 2 | 0 | **0** |
| Không có mẫu | 42 | 23 | **28** |
| Mở phiên | 14 s, máy người kiểm | 10,31 s | **6,33 s — đạt <15 s** |
| Đề xuất 105 dòng | 50 s, máy người kiểm | 12,70 s | **10,66 s — đạt <30 s** |
| Đánh giá A/B thực chạy 105×2, 62 dòng có đáp án | Không dùng so tốc độ khác máy | 147,68 s | 91,84 s |
| Tạo workbook | Chưa so | 37,78 s | 33,33 s |

Các pha mở/đề xuất được đo tách trước khi chạy suite cuối; đánh giá/workbook có thể trùng một phần với kiểm thử sau đó, không dùng các pha này để chứng minh ngưỡng mở/đề xuất. Workbook còn khoảng 3,17 MB và 52.606 hàng PHAN_BO; chưa tối ưu V5. Hai lượt C3 đều giữ cổng đã ghi sổ; bộ không rò rỉ chặn 64 đã ghi sổ, 1 bằng chứng không rõ. Nạp sao kê lần hai vẫn 105 trùng, 0 thêm; XML 75, bảng kê 19, 5 mâu thuẫn vẫn chờ V2.

### Nguyên nhân không có mẫu — bốn nhóm cùng cách đọc báo cáo độc lập

| Nhóm | V1 không rò rỉ | V1b không rò rỉ |
|---|---:|---:|
| Không có STK đối ứng | 14 | 14 |
| Có quy tắc bậc 2 nhưng hết hạn | 14 | **0** |
| STK chưa từng có quy tắc | 11 | 11 |
| Quy tắc bậc 2 sinh trong T8 bị loại | 3 | 3 |
| Tổng | 42 | 28 |

Trong 51 dòng FULL gốc, nay còn 33 FULL, 14 PARTIAL, 4 NONE. Có 15 dòng thiếu đối tượng: 11 không có STK đối ứng, 3 chỉ có ánh xạ chưa xác minh, 1 không có định danh đủ điều kiện. Ngoài ra có 1 dòng nhiều tài khoản và 3 dòng không mẫu; các nhóm cổng có giao nhau. Không thể khôi phục FULL bằng cách điền mã phổ biến nhất vào mẫu bậc 5 hoặc coi NHAP đã xác minh.

Nếu chỉ nhìn giá trị trường và bỏ cổng FULL, số đúng Nợ/Có/dự án là 36/40, 33/40, 13/16. Đây **không phải số nghiệm thu**, chỉ giúp tách thiếu dữ kiện khỏi sai trường. Như vậy ngoài thiếu định danh, vẫn cần rà các trường TK Có trong mẫu được chọn. Trong lượt không rò rỉ không có mẫu được chọn từ 110 hàng vừa chuyển bậc, nên việc chuyển bậc này không trực tiếp gây thay đổi kết quả của lát cắt.

Hai mã Anh xác nhận cần kết xuất lại nằm trong [MA-NGOAI-DANH-MUC.json](../var/vong-2/V1b/MA-NGOAI-DANH-MUC.json). Không tự thêm catalog. Cột không rò rỉ hiện không có lỗi INVALID_COUNTERPARTY, vì vậy không quy nguyên nhân thất bại cột này cho hai mã đó.

### Hồ sơ bàn giao và phần cần xử lý tiếp

- [KET-QUA-V1b.json](../var/vong-2/V1b/KET-QUA-V1b.json): hai cột, các pha, tham số, cổng đạt/không đạt và đường dẫn lượt chạy.
- [SAI-CON-LAI.json](../var/vong-2/V1b/SAI-CON-LAI.json): từng bank_id, mẫu chọn, đề xuất và đáp án, tách variant/scenario.
- [CHO-MAU-NHIEU-DONG.json](../var/vong-2/V1b/CHO-MAU-NHIEU-DONG.json): mẫu nguồn và giá trị các dòng C2 chờ nhiều dòng. Chi tiết C1 lưu riêng trong mỗi thư mục lượt chạy.
- [NGUYEN-NHAN-KHONG-MAU.json](../var/vong-2/V1b/NGUYEN-NHAN-KHONG-MAU.json): phân nhóm có truy nguyên từng dòng, không in thông tin giao dịch lên chat.

Để tiến tới nghiệm thu: CFO_NTD cần xác minh các định danh còn thiếu và rà mẫu có trường sai dựa trên chứng từ độc lập, không chỉ nhìn đáp án T8. Những giao dịch không có STK cần một điều kiện/CASE chính xác có bằng chứng, hiệu lực và người duyệt; không biến tên thành khóa cứng. Tri thức mới rút ra từ T8 không được thêm vào cột nghiệm thu trước T8. Mẫu nhiều dòng đã duyệt hướng nhưng chỉ triển khai khi Anh giao V2. Việc nạp danh mục mới vẫn cần kết xuất của Anh. **Chưa tự thực hiện các thay đổi nghiệp vụ này hoặc chuyển V2; trạng thái cổng V1b là chưa đạt.**

Giới hạn giữ nguyên: thống kê và lan_cuoi nguồn còn chứa T8, bộ JSON có giả định công nợ/snapshot và tham chiếu sổ đã ghi nhận ở V0. “Không rò rỉ” ở đây là bộ lọc lan_dau theo quyết định của Anh, không khẳng định đã có backtest độc lập sạch hoàn toàn. Đánh giá A/B của bộ cũ còn điểm số NONE chưa sửa; số nghiệm thu ở trên được đếm riêng trên cohort cố định và đòi hỏi FULL.
