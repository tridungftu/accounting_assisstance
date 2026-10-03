# Báo cáo V9b — Sửa đề xuất sao kê và chấm lại F

**Trạng thái:** hoàn tất S1–S12 và F4. Báo cáo chỉ công bố số liệu tổng hợp; không chứa dòng giao dịch, số tài khoản, số chứng từ, tên đối tác hoặc dữ liệu thật khác.

## Phạm vi đã giao

V9b giữ nguyên N1–N5 của V9 và triển khai theo thứ tự S1–S12: vế tiền, nhãn tin cậy, mã chính đơn vị, điều kiện đối tượng, ưu tiên nhận diện, học từ sổ, ghép sao kê–sổ, hóa đơn tháng 8, xuất Junsky, học theo tình huống, test synthetic và chấm F.

Quyết định S7 đã được Anh duyệt được ghi tại [QUYET-DINH.md](QUYET-DINH.md#v9b--quyết-định-và-giả-định-thực-thi-s1s12). Import Junsky không được thực hiện.

## Đã sửa

- S1–S2: bắt buộc vế TK tiền chi tiết 112 theo chiều thu/chi; chỉ dùng mapping Anh nhập hoặc suy ra duy nhất từ sổ. PENDING giữ nhãn PENDING và chỉ PENDING mạnh mới có thể Xanh.
- S3–S5: suy mã chính đơn vị từ MST/tên cấu hình và loại khỏi quy tắc, định danh, mẫu học; quy tắc REGEX/từ khóa không tự điền đối tượng; áp dụng đủ bảy bậc ưu tiên và chỉ chặn xung đột cùng bậc.
- S6–S8: học mẫu BR/BP trước cutoff, giữ cấu trúc nhiều dòng gồm 1331, dự án/khoản mục/TTCP và chỉ tạo tri thức PENDING; đọc hóa đơn tháng 8 theo net/VAT/công nợ, MST và chứng cứ sổ.
- S7–S10: ghép duy nhất ngày + số tiền TK 112 + độ giống diễn giải, mặc định loại trường hợp nghi đã ghi sổ; số chứng từ xuất theo đơn vị/tháng; header dự phòng ở dòng 1; học tình huống sau quyết định `CFO_NTD`.
- S9 UI: cấu hình mapping TK tiền, BankID, ngưỡng, mẫu và chế độ `DOI_UNG`/`DAY_DU`; tải file xuất/file soát qua API cục bộ có token, chỉ trong thư mục của đúng lượt xuất.
- S11: bổ sung test synthetic cho S1–S10, tất cả cặp ưu tiên S5, mã chính đơn vị, nhiều dòng cân Nợ/Có, nhiều đơn vị/tháng, fallback mẫu, `.xls` có/không có `xlrd` và giới hạn tải file.

## Kiểm thử và migration

| Hạng mục | Kết quả |
|---|---|
| Full suite synthetic | **198/198 PASS** |
| Migration | Bản sao schema v16 → **v18**; `integrity_check=ok`, foreign key = **0**, DB gốc không đổi khi kiểm thử migration ([MIGRATION-CHECK.json](../var/vong-2/V9-giao-viec/migration-v18-copy/MIGRATION-CHECK.json)) |
| Kiểm thử `.xls` khi có/không có `xlrd` | PASS; test ép cả hai trạng thái môi trường, không phụ thuộc máy đang cài `xlrd` |
| Chạy thử UI/API cục bộ | PASS: khởi động local, `/api/health` phản hồi; test UI/API tải file và path traversal PASS |
| Ràng buộc N5 | PASS: nguồn không đổi; fixture chỉ synthetic; không gọi AI/dịch vụ ngoài; không nhập Junsky |

## S12 — Kết quả F1–F2

Ngưỡng giống diễn giải dùng khi chấm: **0,80**. F chạy ở kho sao chép: sổ cut đến 31/07/2026 và sổ đầy đủ đến 29/08/2026; không thay bằng số liệu V9 hoặc số đo kiểm tra độc lập trước V9b.

| Phạm vi | Tổng dòng/chứng từ | Ghép duy nhất với sổ | Xanh | Vàng | Đỏ | Độ đúng TK | Độ đúng đối tượng | Ghi chú |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Sao kê tháng 8 | 105 · 543.876.349.858 VND | 57 duy nhất; 0 mơ hồ; 48 không ghép | 0 | 0 | 105 | 44,737%* | 57,895%* | Thiếu mapping TK tiền và mẫu/căn cứ TK đối ứng |
| Hóa đơn mua tháng 8 | 39 · 1.508.185.015 VND | 8 duy nhất; 6 mơ hồ; 25 không ghép | 0 | 0 | 39 | 50,000%* | 12,500%* | Thiếu chứng cứ TK hóa đơn; 4/4 bộ lines tạo được cân |
| Hóa đơn bán tháng 8 | 36 · 823.436.561.831 VND | 15 duy nhất; 16 mơ hồ; 5 không ghép | 0 | 0 | 36 | 50,000%* | 0,000%* | Thiếu chứng cứ TK hóa đơn; 15/15 bộ lines tạo được cân |

\* Tỷ lệ chỉ tính trên lát cắt ghép duy nhất tương ứng và trường có đáp án đối chiếu; không phải tỷ lệ nghiệm thu toàn lô.

| Chỉ tiêu S12 bổ sung | Kết quả |
|---|---|
| Sao kê đủ bút toán (Xanh + Vàng) so với mốc cũ 23% | **0,0%**; chưa đạt mốc 23% |
| Tỷ lệ đúng của Xanh — TK / đối tượng | Không đánh giá được: không có mẫu Xanh ghép duy nhất; mục tiêu 98% chưa thể kết luận |
| Số dòng “Có thể đã có trong Junsky” ghép duy nhất | **57**; mặc định loại khỏi file xuất, có thể bỏ đánh dấu từng dòng |
| Số dòng ghép mơ hồ, không kết luận trùng | **0** sao kê; không có kết luận trùng cho trường hợp không duy nhất |
| Kết quả hóa đơn theo engine nhiều dòng net/VAT/công nợ | Hóa đơn mua 4/4 và bán 15/15 proposal có lines đều cân; thiếu chứng cứ vẫn giữ Đỏ |

Kết quả máy đầy đủ, chỉ số tổng hợp tại [KET-QUA-F2.json](../var/vong-2/V9-giao-viec/F-score/KET-QUA-F2.json).

## Nguyên nhân còn Đỏ và phần chưa xác minh

- Sao kê: 85 dòng thiếu mapping TK tiền; 66 thiếu TK Có, 28 thiếu TK Nợ và 20 không có mẫu duy nhất. Đây là nguyên nhân cấu trúc nên không tự hạ ngưỡng để tạo Xanh.
- Hóa đơn mua: 39 thiếu chứng cứ TK hóa đơn, trong đó 35 thiếu TK Nợ; 13 thiếu hoặc nằm ngoài danh mục đối tượng theo MST.
- Hóa đơn bán: 36 thiếu chứng cứ TK hóa đơn/TK Nợ, 21 thiếu TK Có; 3 thiếu hoặc nằm ngoài danh mục đối tượng theo MST.
- Cần kế toán xác nhận mapping STK chính đơn vị → TK 112 chi tiết cho các nguồn sao kê, căn cứ MST → TK công nợ/chi phí/doanh thu và danh mục đối tượng cập nhật. Sau đó cần chạy lại F; không dùng kết quả hiện tại làm nghiệm thu chất lượng.

## Bàn giao và giới hạn vận hành

Kho chính đã được thay bằng kho F4 dựng sạch: schema v18, integrity/FK đạt, không có quick run, quyết định, batch xuất hoặc tri thức điều kiện từ quyết định. Nền có 4.507 chứng từ sổ, 7.818 phiên bản tri thức; bootstrap lần hai không thay đổi dữ liệu, không còn logical key trùng/overlap. Bản kho cũ đã được sao lưu có kiểm tra và giữ thêm bản rollback cục bộ ([kiểm tra kho sạch](../var/vong-2/V9-giao-viec/F4-main-candidate/KET-QUA-F4-CLEAN.json), [kết quả chuyển](../var/vong-2/V9-giao-viec/F4-main-candidate/KET-QUA-F4-PROMOTE.json)).

Giao diện local đã khởi động được. File Junsky chỉ được tạo sau khi Anh bấm Đồng ý; không có thao tác nhập Junsky. Mẫu định dạng chỉ được kiểm tra cấu trúc, không phải bằng chứng đã nhập thành công.

## Giả định

Áp dụng `GIẢ ĐỊNH-V9b-1` đến `GIẢ ĐỊNH-V9b-8` trong [QUYET-DINH.md](QUYET-DINH.md). Các giả định là tham số có thể đổi, không phải quyết định duyệt tri thức hay mapping dữ liệu cụ thể.
