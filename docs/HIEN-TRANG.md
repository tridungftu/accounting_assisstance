# Hiện trạng và kế hoạch triển khai kho tri thức

**Hiện hành A12/V1b — 18/09/2026:** đã điều chỉnh theo kiểm tra độc lập và sáu quyết định V1b. 152/152 test đạt, schema v9, cache đạt tốc độ; **chưa đạt cổng chất lượng không rò rỉ**. Kết luận V1 đạt ở lịch sử bên dưới đã bị thay thế. Xem mục V1b của BAO-CAO-V1.md và TIEN-DO.md; chưa sang V2, chưa vận hành hạch toán.

**Hiện hành V1 — 18/09/2026:** Anh đã duyệt kế hoạch V1–V6 theo A11 và giao riêng V1. Đã bổ sung trigger/thứ tự/regex/CASE/hạn dùng trong lõi, giữ sáu module và schema v8. Kết quả và giới hạn nghiệm thu tại [báo cáo V1](BAO-CAO-V1.md). Chưa có adapter thực được nghiệm thu. Mục 3 đã cập nhật từ file thực tại V0; các câu “chưa có dữ liệu/mẫu” và ước lượng ở phần P0/A08/A09 bên dưới là lịch sử.

**Cập nhật V8 — 24/09/2026:** `MỞ PHẦN MỀM.cmd` mở UI `that` sáu màn hình trên loopback; `MỞ BẢN DEMO.cmd` giữ UI fixture. V8 dùng reader nguồn thật, tri thức chờ duyệt, phiên shadow và file shadow; vẫn không có quyền import Junsky. Toàn bộ 175 test synthetic/web đạt; xem [báo cáo V8](BAO-CAO-V8.md). Các mô tả kiểm kê P0 bên dưới là lịch sử, không phải danh sách file hiện tại.

Ngày kiểm kê P0: 17/09/2026. Phạm vi: thư mục dự án `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức`, kể cả mục ẩn. Các mục 1–8 giữ kiểm kê/kế hoạch tại P0. **Cập nhật A08:** đã có code + fixture M1–M6; xem mục 9 bên dưới, [TIEN-DO.md](TIEN-DO.md) và [báo cáo toàn bộ](BAO-CAO-KIEM-THU-M1-M6.md). Code mới không phải script khảo sát bản 1.2 tìm lại được. Chưa có dữ liệu thực.

## 1. Kết luận về mức độ sẵn sàng

**Đủ căn cứ để thống nhất thiết kế; chưa đủ để xác nhận khả năng tái sử dụng, nghiệm thu bộ đọc hoặc cam kết lịch pilot.** Trước khi lập `docs/`, thư mục có đúng bốn file Markdown, tổng 85.985 byte; không có script, dữ liệu, workbook, mẫu import, test, dependency manifest hoặc DB. Không tìm thấy thư mục `.git` hay `.agents` tại dự án.

Đã kiểm kê bằng `rg --files --hidden --no-ignore` và danh sách file đệ quy của PowerShell. Không tìm thấy `AGENTS.md` ở dự án và các cấp cha từ `D:\` đến dự án; áp dụng nội dung AGENTS.md Anh cung cấp trong hội thoại. Không tìm thấy tài liệu quyết định riêng, tài liệu “Phản biện vòng 2 và quyết định chốt” hoặc danh sách “D.1 — 9 loại dữ liệu”. Không suy rộng kết quả kiểm kê sang các thư mục khác trên máy.

Các tỷ lệ, số lượng và tên tài sản trong bản 1.2 là **báo cáo của tài liệu**, chưa phải kết quả kiểm thử lại. Không sử dụng “60% đã có” làm hệ số giảm công. Việc chưa có script trong thư mục này cũng không chứng minh script không tồn tại ở nơi khác.

## 2. Tài liệu thực tìm thấy

| File | Byte | Đã đọc | Vai trò |
|---|---:|---|---|
| `KE-HOACH-PHAN-MEM-KHO-TRI-THUC.md` | 27.827 | Toàn bộ | Bản 1.2; phạm vi, quyết định gốc và số liệu khảo sát được báo cáo |
| `KE-HOACH-MODULE-VA-LO-TRINH.md` | 20.939 | Toàn bộ | Đề xuất sáu module, D01–D10 và cổng nghiệm thu |
| `DU-LIEU-VA-QUYET-DINH-CAN-CHOT.md` | 12.167 | Toàn bộ | Yêu cầu đầu vào; Q1–Q10 và câu hỏi Junsky |
| `BO-PROMPT-CODEX.md` | 25.052 | Chỉ Quy ước chung và P0 | Giới hạn nhiệm vụ; không đọc nội dung hoặc thực thi prompt module |

Nội dung “thư mục chỉ có bản 1.2” trong kế hoạch module là mô tả ở thời điểm trước; kiểm kê hiện tại là bốn tài liệu. Bốn nguồn được giữ nguyên. Các tài liệu mới trong `docs/` là thiết kế đề xuất, không được tính là tài sản sản phẩm đã có.

## 3. Đối chiếu tài sản bản 1.2 — cập nhật V0 18/09/2026

**Đã tìm thấy script, workbook và nguồn thật trong các thư mục mới được Anh chỉ định.** Kết luận “không có” ở P0 chỉ áp dụng thư mục dự án lúc đó. Không còn dùng kết luận này cho hiện trạng vòng 2.

| Tài sản bắt buộc kiểm kê | Byte | Ngày sửa (UTC+07) | Mức xác minh |
|---|---:|---|---|
| [14_xuat_junsky.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/14_xuat_junsky.py>) | 24,458 | 05/09/2026 14:12:15 | Đã đọc phần đầu/main hoặc API; chưa chạy; xem đánh giá tĩnh |
| [15_doc_pdf_2nam.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/15_doc_pdf_2nam.py>) | 19,186 | 06/09/2026 20:26:17 | Đã đọc phần đầu/main hoặc API; chưa chạy; xem đánh giá tĩnh |
| [17_doi_chieu_2nam.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/17_doi_chieu_2nam.py>) | 13,865 | 06/09/2026 22:17:06 | Đã đọc phần đầu/main hoặc API; chưa chạy; xem đánh giá tĩnh |
| [20_doc_hoa_don_xml.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/20_doc_hoa_don_xml.py>) | 12,330 | 11/09/2026 20:49:50 | Đã đọc phần đầu/main hoặc API; chưa chạy; xem đánh giá tĩnh |
| [kho_tri_thuc.py](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/kho_tri_thuc.py>) | 12,672 | 11/09/2026 20:36:58 | Đã đọc phần đầu/main hoặc API; chưa chạy; xem đánh giá tĩnh |
| [BO-QUY-TAC.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/BO-QUY-TAC.xlsx>) | 429,074 | 04/09/2026 13:13:07 | Mở read-only, kiểm tra sheet/cột; chưa nghiệm thu nghiệp vụ |
| [TU-DIEN-NHOM-NGHIEP-VU.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/TU-DIEN-NHOM-NGHIEP-VU.xlsx>) | 59,770 | 14/09/2026 07:31:33 | Mở read-only, kiểm tra sheet/cột; chưa nghiệm thu nghiệp vụ |
| [HOA-DON-CAY-PHAN-NHANH.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/HOA-DON-CAY-PHAN-NHANH.xlsx>) | 41,625 | 17/09/2026 14:27:46 | Mở read-only, kiểm tra sheet/cột; chưa nghiệm thu nghiệp vụ |
| [SAO-KE-2-NAM.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/SAO-KE-2-NAM.xlsx>) | 751,667 | 06/09/2026 20:44:08 | Mở read-only, kiểm tra sheet/cột; chưa nghiệm thu nghiệp vụ |
| [NHOM-NGHIEP-VU-BASE-v2.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/ket_qua/NHOM-NGHIEP-VU-BASE-v2.xlsx>) | 120,685 | 14/09/2026 06:58:26 | Mở read-only, kiểm tra sheet/cột; chưa nghiệm thu nghiệp vụ |
| [MAU-JUNSKY-PHIEU-CHI-NH.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/mau/MAU-JUNSKY-PHIEU-CHI-NH.xlsx>) | 19,188 | 05/09/2026 07:04:30 | Mở read-only, kiểm tra sheet/cột; chưa nghiệm thu nghiệp vụ |
| [MAU-JUNSKY-PHIEU-THU-NH.xlsx](<D:/Claude/Phan mem ho tro ke toan/Mang ngan hang/bo_quy_tac/mau/MAU-JUNSKY-PHIEU-THU-NH.xlsx>) | 19,188 | 05/09/2026 07:04:30 | Mở read-only, kiểm tra sheet/cột; chưa nghiệm thu nghiệp vụ |

Kiểm kê thực: 23 script/48 workbook trong bo_quy_tac, 24 PDF và 8 sao kê .xls ở nguồn ngân hàng, 6 file danh mục, 1.907 XML/67 bảng kê, CSV 1.907 HĐ/5.198 dòng/2.716 bảng kê, Base 1.283 thư mục đề nghị so chỉ mục 1.115. Các đường dẫn có bản sao nên không cộng số lượng như tài sản duy nhất.

809 quy tắc/164 STK/2.027 đối tượng đã đếm trên workbook. Từ điển có 431 regex/33 nhóm, thiếu sheet 3B; cây hóa đơn có 149 NCC và 28 mã khoản mục. Mẫu Junsky thực có Entry1 17 cột/Entry2 37; chưa xác minh được việc nhập thành công.

**Chưa chứng nhận script bản 1.2 nào có thể đưa nguyên trạng vào sản phẩm.** Cả năm script chính cần thử trên bản sao, một số dùng float, đường dẫn cố định, pickle chưa có hoặc ghi đè đầu ra. Runtime thiếu xlrd cho .xls. Parser PDF hiện có và workbook kết quả không cùng số sheet, cần kiểm phiên bản. Không dùng “60% đã có” để hứa tiến độ.

Đầu vào/đầu ra/dependency từng script, đường dẫn tuyệt đối/kích thước/ngày sửa mọi workbook và phần thiếu được ghi tại [TAI-SAN-VONG-2.md](TAI-SAN-VONG-2.md). [Báo cáo V0](BAO-CAO-V0.md) ghi kết quả chạy lại; [kế hoạch V1–V6](KE-HOACH-VONG-2.md) là đề xuất chờ Anh duyệt. Các mục P0 còn lại giữ làm lịch sử, không thay trạng thái hiện hành.

## 4. Phạm vi và kiến trúc đề xuất

Một ứng dụng Python 3.11+, một SQLite; Excel để quản trị tri thức, duyệt và chuyển dữ liệu Junsky; CLI theo phiên. Runtime nội bộ, offline. Thư viện trực tiếp trong phạm vi gốc: thư viện chuẩn, pandas, openpyxl, lxml, pdfplumber. Cấu hình TOML là đề xuất D05, chưa thay YAML đã ghi trong bản 1.2. Phiên bản thư viện và gói cài offline chỉ khóa sau khi thử adapter.

Pilot PLHN, sao kê là đối tượng đề xuất; hóa đơn/XML/bảng kê và Base là bằng chứng. Không UI, server, API, AI/ML/LLM, tự duyệt hoặc tự ghi sổ. Thu và chi đều phải được đo; ưu tiên công việc chiều chi không có nghĩa tự loại chiều thu khỏi phạm vi. Thiếu mẫu nghiệp vụ thì đưa vào ngoại lệ. Không mở rộng sang hóa đơn làm đối tượng đề xuất hoặc pháp nhân thứ hai.

| Module | Trách nhiệm và ranh giới | Đầu ra chính |
|---|---|---|
| M1 — Nền tảng và dữ liệu | Nhập năm nhóm nguồn: sao kê, XML, bảng kê HĐ, Base, Junsky xuất; kiểu dữ liệu, SQLite, raw/staging, audit, backup | Dữ liệu chuẩn và báo cáo kiểm tra; không làm đề xuất/phân bổ |
| M2 — Kho tri thức | Năm nhóm: danh mục/định danh; chính sách/mẫu/ràng buộc; tình huống; giao diện thống kê dẫn xuất; quy tắc/nhật ký. Liên kết lịch sử | Tri thức có phiên bản/hiệu lực; LINK_A/B/C. M5 tính thống kê qua giao diện này |
| M3 — Phiên xử lý và máy đề xuất | Cổng vào, khóa phiên, snapshot/giữ chỗ; nhận diện → đối chiếu → ràng buộc → xếp hạng → tin cậy từng trường | Đề xuất đầy đủ/một phần/không, chứng cứ và tiền còn phân bổ |
| M4 — Duyệt và xuất Junsky | Excel round-trip, duyệt từng chứng từ, xuất theo mapping được xác nhận, chốt phiên, recovery batch | Quyết định có phiên bản, file import và công nợ kỳ vọng; không tự xác nhận đã ghi sổ |
| M5 — Đối soát và học liên tục | RECON_A/B/C, xác minh từng trường, nhãn hiệu lực, thống kê theo lượng/tiền, đề cử quy tắc | Nhãn đủ điều kiện, đối soát và quy tắc CHỜ DUYỆT |
| M6 — Kiểm chứng, báo cáo và vận hành | Backtest A/B, holdout/kiểm tra mù, kiểm thử xuyên module, hai phiên/UAT, hướng dẫn và phục hồi | Bằng chứng nghiệm thu và quyết định qua cổng |

Đây là sáu gói giao việc trong một ứng dụng, không phải sáu dịch vụ. Các gói Python nội bộ nêu ở bản 1.2 không phải module quản lý thứ bảy. Kho trạng thái và kho tri thức tách bảng/trách nhiệm nhưng chung SQLite. Raw, workbook và manifest là file có truy nguồn; SQLite không thay việc lưu bằng chứng nguồn. Không cho sửa DB trực tiếp; Excel là nơi con người nhập quyết định, chỉ dữ liệu được kiểm tra và duyệt mới có hiệu lực trong SQLite.

## 5. Thứ tự triển khai và cổng

1. **P0 đã hoàn thành:** bốn tài liệu đã trình; sau đó Anh duyệt A07 và cho coding. Hiện M1 có bản lõi/fixture; kết quả hiện hành ở TIEN-DO.md.
2. **G0 — kiểm chứng khả thi:** M1 → M2 → M3 → M6 đo Baseline A → M5 thống kê từ nhãn lịch sử đã xác minh → M6 so Baseline B. M6 thiết kế kiểm chứng từ M1, không đợi cuối dự án. M3 có thể dùng quyết định giả lập để kiểm tra nhưng không tính thành nghiệm thu nghiệp vụ.
3. **G1 — chạy ngầm:** M4 → hoàn thiện vòng vận hành M5 → M6 kiểm tra hai phiên, import một phần, kiểm tra mù. Nhịp chạy theo snapshot được cung cấp; thay yêu cầu “hằng ngày” ở bản gốc cần ghi nhận theo thực tế nhịp phiên.
4. **G2 — pilot vận hành:** sau G1, người có trách nhiệm cho phép chạy; kế toán duyệt từng chứng từ. M6 tập hợp chứng cứ vận hành thực, UAT và restore. Không dùng file shadow để nhập thật.

G0 cần nguồn đạt tổng/bao phủ; LINK_A được người kiểm; có báo cáo chênh và phần dư. Gợi ý gốc A đúng 98%, tỷ lệ A dưới 50% cần rà nguồn, tập vàng 200–300 và kiểm tra 100 A + 100 B được lưu làm đề xuất, chưa gọi là ngưỡng đã duyệt. G1 cần người E5, tiêu chí đúng/phủ/rủi ro theo tiền và lịch kiểm tra mù được duyệt; gợi ý 50 chứng từ/tuần chưa là cam kết. G2 cần hai phiên hoàn chỉnh, bằng chứng ghi sổ, không trùng, xử lý import một phần, restore và phân vai rõ.

B chỉ được chọn nếu tăng phủ mà giữ chuẩn đúng/rủi ro đã duyệt trên tập đánh giá tương thích. B chưa đạt thì có thể xem xét pilot A; không bật học chỉ vì đã viết xong. Khóa tháng cần đối soát sau nhập và điều kiện D08; giải trình chênh không có nghĩa chênh bằng 0.

## 6. Kế hoạch M1 để Anh phê duyệt

### Mục tiêu và giới hạn

Tạo nền tảng nhập có thể truy nguồn, kiểm tra và nạp lại an toàn. M1 không làm quy tắc kế toán, liên kết lịch sử/xếp hạng, giữ chỗ, workbook duyệt, file import Junsky hoặc học. M1 thiết kế lưu dữ liệu cần cho các module sau; không triển khai hành vi của các module đó.

Hai mức bàn giao: **(a) lõi + fixture**, **(b) adapter + mẫu thực**. Mức (a) không được đánh dấu M1 hoàn thành toàn bộ. Chỉ bắt đầu mức (a) sau khi Anh duyệt cách làm; thiếu mẫu không được bịa mapping để chuyển sang mức (b).

### Đầu vào

- Hợp đồng và các lựa chọn tối thiểu C01–C06 trong [QUYET-DINH.md](QUYET-DINH.md); mã pháp nhân chính thức, tiền tệ/quy tắc dấu, thời điểm và phạm vi nguồn.
- Script cũ và dependency nếu tìm lại được. Nếu vẫn không có, công phần đọc nguồn được tính như viết mới; không phải điều kiện chặn lõi fixture.
- Mỗi layout sao kê ít nhất một file, gồm trang nối/diễn giải dài/giao dịch trùng ngày–tiền/tổng đầu–cuối; PDF ảnh nếu có phải được khai báo. OCR chưa thuộc phạm vi thư viện, cần quyết định nếu phát sinh.
- XML/bảng kê của cùng HĐ, hóa đơn không mã, điều chỉnh/thay thế/hủy; schema thực và cách xác nhận tổng.
- Base: chỉ mục và thư mục JSON tương ứng, file giải mã được/lỗi, ID và trường dự án/chi phí.
- Gói Junsky năm nhóm có manifest/as-of/tổng; thêm sổ 112/NKC hoặc danh sách bút toán theo D03 nếu được chấp thuận. Năm nhóm nghiệp vụ có thể là nhiều file/sheet.
- Kế toán xác nhận đáp án về số dòng/tổng/định danh của bộ mẫu đã ẩn thông tin hợp lệ. Mẫu import Entry1/2 chưa cần để lập lõi M1, nhưng cần lấy sớm vì chặn M4.

### Các bước trong M1 sau khi được giao

1. Chốt catalog layout được hỗ trợ, bảng ánh xạ từ mẫu thực, độ bao phủ và tổng kiểm soát; ghi mục chưa biết. Lưu phiên bản script nhận được và kiểm tra smoke trên mẫu trước khi nhận định tái dùng.
2. Xây cấu hình theo lựa chọn đã duyệt; kiểu tiền/chuỗi/thời gian; SQLite/migration/khóa ngoại/transaction; raw bất biến, staging, audit và sao lưu khôi phục.
3. Xây contract/fixture và CLI nạp–kiểm tra–báo cáo; báo lỗi đến file/trang/sheet/dòng. Một đơn vị nhập lỗi không đưa một phần dữ liệu vào bảng chuẩn; raw và log lỗi vẫn được giữ. Gói phiên chỉ đủ điều kiện sử dụng khi toàn bộ thành phần bắt buộc đạt.
4. Tích hợp adapter lần lượt: sao kê → Junsky snapshot/danh mục/sổ → XML và bảng kê → Base. Ưu tiên rủi ro công nợ/định danh Junsky; không đợi cuối mới phát hiện thiếu HĐ hoặc ID dòng.
5. Chạy bộ kiểm thử dưới đây, nạp bộ mẫu thực được phép, đối chiếu đáp án với kế toán; chạy lại và phục hồi trên bản sao. Bàn giao giới hạn layout và các lỗi còn treo.

### Đầu ra dự kiến, chưa được tạo ở P0

Bộ adapter thống nhất; `kho.sqlite` với phiên bản schema; raw/manifest/staging/audit; CLI nạp/kiểm tra/backup/restore; fixture và test hành vi; báo cáo file–dòng–tổng, bản trùng/nghi trùng và lỗi; mapping nguồn có phiên bản dựa trên mẫu đã xác nhận; hướng dẫn IT/kế toán và biên bản nghiệm thu. Tên lệnh cụ thể chốt khi thực hiện M1, chưa có lệnh sản phẩm để demo.

### Kiểm thử và chứng cứ phải bàn giao

| ID | Tình huống | Kết quả bắt buộc | Fixture / cần mẫu thực |
|---|---|---|---|
| T01 | Tiền có số lẻ, số lớn, ký hiệu phân cách, tiền tệ lạ | Không float; không âm thầm làm tròn/quy đổi; phát hiện vượt miền lưu trữ | Fixture; quy tắc tiền cần kế toán duyệt |
| T02 | MST/TK/mã có số 0 đầu; chữ Đ/đ | Chuỗi giữ nguyên, bản chuẩn hóa nhất quán, giữ raw | Fixture + Excel thực |
| T03 | Nạp lại đúng file và bản đổi tên | Không tăng số thực thể/tiền; vẫn có nhật ký lần nạp | Fixture + mẫu thực |
| T04 | File chồng kỳ; hai giao dịch cùng ngày/tiền; thiếu/trùng tham chiếu | Không gộp nhầm; giao dịch thật khác ID vẫn tồn tại; trường hợp không phân biệt được phải chờ xác minh | Fixture + sao kê thực |
| T05 | Một hóa đơn trong XML và bảng kê; header mâu thuẫn | Một thực thể với hai nguồn, không cộng hai lần; mâu thuẫn bị báo, không ghi đè | Fixture + cặp file thực |
| T06 | HĐ thay thế/điều chỉnh/hủy, chưa thấy HĐ gốc | Giữ phiên bản/quan hệ và trạng thái nguồn; không xóa lịch sử hoặc giả định tác động kế toán | Fixture + trường hợp thực |
| T07 | Base thiếu chỉ mục, dư file, JSON lỗi/base64 lỗi, ID trùng | Quét thư mục, báo từng chênh/lỗi; không bỏ im lặng | Fixture + thư mục thực |
| T08 | PDF qua trang/dòng dài/layout không hỗ trợ | Đọc đúng layout hỗ trợ; phần không đọc được làm file lỗi, không báo thành công thiếu dòng | Cần PDF thực; fixture chỉ kiểm tra đường xử lý |
| T09 | Tổng đầu/cuối, thu/chi, HĐ header/detail, Junsky TK/đối tượng | Khớp tổng theo từng tiền tệ/phạm vi; chênh có định danh. Không bù chênh trái dấu giữa HĐ | Fixture + tổng kế toán xác nhận |
| T10 | Sai pháp nhân, thiếu nhóm, phạm vi/as-of lệch; hash giống/khác | Kiểm tra nội dung và metadata; hash không tự quyết định độ mới; gói chưa đủ không dùng được | Fixture + manifest thực |
| T11 | File lỗi sau khi đọc một phần; crash khi promote | Raw/log còn nguyên, bảng chuẩn rollback; retry không nhân đôi | Fixture |
| T12 | Trùng mã, orphan FK, khóa nguồn không ổn định giữa hai bản xuất | Chặn/quarantine; không dùng số thứ tự dòng file như ID xuyên lần xuất | Fixture + hai bản xuất Junsky |
| T13 | known_at thiếu, hiệu lực chồng, ngày địa phương và timestamp khác | Không tạo known_at giả; không đưa dữ liệu tương lai vào truy vấn cutoff | Fixture; lịch sử thực để xác nhận khả năng backtest |
| T14 | Backup lúc DB có hoạt động và restore ở vị trí thử | Bản khôi phục nhất quán, kiểm tra integrity/FK, số dòng/tổng/hash nguồn truy được; không ghi đè DB đang dùng | Fixture; thử lại trên bộ mẫu được phép |
| T15 | Nạp toàn bộ bộ nghiệm thu và nạp lại | Mọi file/dòng thuộc phạm vi có kết quả; các file hợp lệ khớp đáp án, không trùng; lỗi không gây dữ liệu nửa chừng | Bắt buộc bộ mẫu thực và kế toán ký |

T09 là bộ kiểm tra **đề xuất mới cho M1**, không tuyên bố đã khôi phục đúng bốn phép kiểm tra trong script khảo sát chưa nhận được.

### Điều kiện hoàn thành

- **Lõi + fixture đạt:** T01–T14 ở phạm vi mô phỏng đạt, có báo cáo test thực chạy, migration và restore kiểm chứng. Adapter thiếu mẫu vẫn ghi “chưa tích hợp mẫu thực”.
- **M1 đầy đủ đạt:** catalog layout/phạm vi được ký; tất cả năm nhóm nguồn bắt buộc có mẫu; T03–T15 liên quan nguồn thực đạt; 100% file hợp lệ thuộc catalog được đọc đủ và tổng khớp, file lỗi bị từ chối có lý do; kế toán xác nhận tổng/định danh; IT xác nhận chống trùng/truy nguồn/restore. Nếu chưa có dữ liệu lịch sử đầy đủ, ghi rõ mới nghiệm thu bộ mẫu, chưa nghiệm thu việc nạp 12 tháng ở G0.
- Nếu thiếu công nợ theo HĐ hoặc chứng cứ bắt buộc đã thống nhất ở D03, giữ hạng mục đó ở trạng thái chờ. Bất kỳ giảm phạm vi nghiệm thu cần quyết định của Anh, không đổi tên một phần thành hoàn thành.
- Nghiệm thu M1 không cấp quyền vận hành hạch toán; quyền đó cần các cổng M3–M6.

## 7. Ước lượng nguồn lực có điều kiện

**Độ chắc chắn thấp:** hiện có 0 script và 0 mẫu để đo tốc độ, lỗi layout hoặc công tái sử dụng. Các khoảng dưới đây là dự toán công việc từ thiết kế, chưa phải năng suất đã đo hoặc lịch cam kết; mặc định phải viết mới adapter. Không dùng hệ số “60%”.

Giả định: một IT có kinh nghiệm Python/SQLite làm liên tục; kế toán trưởng dành khoảng 2–4 giờ/tuần để xác nhận và có đầu mối chuẩn bị dữ liệu; một pháp nhân; tối đa hai layout sao kê PDF dạng text, một họ XML, một layout bảng kê, một cấu trúc Base và một bộ Junsky được xác nhận; không OCR, ngoại tệ phức tạp, thay schema lớn hoặc sửa sổ lịch sử. Giả định này chưa được chứng minh bằng mẫu. Mọi ngày dưới đây là **ngày công IT**, gồm test cục bộ và tài liệu, không gồm ngày chờ.

| Thành phần M1 | Ngày công dự kiến | Căn cứ/điều kiện |
|---|---:|---|
| Contract, lõi dữ liệu, fixture, CLI, transaction, backup/restore | 5–8 | Có thể làm sau duyệt mà chưa cần adapter thực; chỉ chứng minh với fixture |
| Sao kê | 3–6 | Hai layout text được cung cấp; parser hiện chưa có |
| XML và bảng kê HĐ | 3–5 | Có mẫu cặp, trạng thái và tổng; hiện chưa có |
| Base | 2–4 | Có chỉ mục/thư mục/cách giải mã; hiện chưa có |
| Junsky xuất | 3–6 | Năm nhóm nghiệp vụ và sổ theo D03, schema được xác nhận; không gồm import M4 |
| Tích hợp mẫu thực, kiểm tra tổng/chống trùng và bàn giao | 2–4 | Có đáp án và người đối chiếu; công lấy/sửa dữ liệu bên kế toán tính riêng |
| **Tổng M1** | **18–33** | Trong đó 5–8 cho lõi/fixture; 13–25 phụ thuộc mẫu thực |

Khung nguồn lực sơ bộ cho các module còn lại: M2 12–20; M3 15–25; M4 12–20; M5 15–25; M6 12–20 ngày công. Tổng sáu module **84–143 ngày công**, độ tin cậy thấp; chỉ dùng thảo luận nguồn lực, chưa đặt ngày bắt đầu/kết thúc. M6 tính công đánh giá xuyên module, backtest, báo cáo/UAT; không tính lại unit test và restore cục bộ đã nằm trong M1. Không suy khung này thành cam kết tuần lịch.

Ước lượng lại khi nhận script + mẫu đại diện và hoàn thành thử một bộ đọc sao kê/Junsky ở M1; chốt lại toàn dự án sau M1 và Baseline G0. Script chạy được, có test và phù hợp contract có thể giảm công; script cần sửa lớn hoặc không có provenance không được hưởng giảm mặc định. Chờ lấy dữ liệu, phản hồi Junsky, tạo đáp án, ít nhất hai chu kỳ phiên và đối soát cuối kỳ là phần thời gian lịch riêng chưa đo. Dự toán cũ 14–18 tuần không được xác nhận lại trong P0.

## 8. Dữ liệu thiếu, phần làm được và phần chờ

| Nhóm | Người chuẩn bị | Mốc cần | Làm được khi thiếu / điều bị chặn |
|---|---|---|---|
| Script khảo sát + phiên bản/dependency | IT/người khảo sát | Đầu M1 nếu muốn tái dùng | Contract/fixture vẫn làm sau duyệt; chưa xác nhận tái dùng |
| Sao kê, XML/bảng kê, Base đã ẩn thông tin và tổng đúng | Kế toán/IT | Adapter M1 | Thiết kế lỗi/chống trùng mô phỏng; chưa nghiệm thu parser thực |
| Năm nhóm Junsky, danh mục/MST PLHN, ngày/phạm vi/tổng và hai lần xuất để so | Kế toán | Adapter M1, trước M3 thật | Chỉ schema khái niệm; không mở phiên thực |
| Sổ 112/NKC hoặc chứng từ có ID dòng và trường hạch toán | Kế toán/Junsky | M1 xác nhận schema, M2/M5 xác minh | Không đo E2, không chứng nhận bút toán/nhãn từ số dư |
| Entry1/2 thành công/lỗi + trả lời EntryID/DebtID/Entry2 | Kế toán/Junsky | Trước M4 thực | Thiết kế batch/recovery với fixture; không xuất vận hành |
| Từ điển/khóa cứng/28 mã; ba chỉ số từ khóa; 10–15 mẫu sao kê; mốc TK 2026 | Kế toán trưởng/người khảo sát | M2/M3 | Khung version/hiệu lực; không tự dựng chính sách/mã/ngưỡng |
| 12 tháng nguồn/sổ, snapshot neo và bằng chứng known_at; kho nhãn cũ | Kế toán/IT | M5 lịch sử/M6 backtest | Replay giả lập; lịch sử thiếu thời điểm chỉ là hồi cứu có giả định |
| Bảy mã lý do, sáu phần báo cáo kỳ; tập vàng/holdout/mẫu mù và E5 | Kế toán trưởng/Anh | M4–M6; E5 trước G1 | Khung dữ liệu/kiểm thử; chưa nghiệm thu báo cáo hoặc độ đúng |

Ở thời điểm P0 chỉ có bốn tài liệu. Sau A07/A08 đã triển khai lõi/fixture M1–M6; dữ liệu và script khảo sát thực vẫn chưa được cung cấp. Mẫu dùng trong Codex phải là fixture hoặc bản ẩn thông tin được phép, giữ quan hệ/kiểu/tổng cần kiểm tra; dữ liệu vận hành thực xử lý trong môi trường nội bộ được phép. Chưa gửi dữ liệu hoặc yêu cầu đến nhà cung cấp.

## 9. Kiểm kê sau coding A08 — 17/09/2026

Kiểm kê trực tiếp bằng `rg --files`, đọc file và chạy Python/PowerShell. Bốn tài liệu nguồn có SHA-256 khớp lần P0, không sửa. BO-PROMPT đã được đọc thêm phần M2–M6 và tiêu chí review để thực hiện phạm vi A08; mô tả “chỉ đọc P0” ở bảng mục 2 là lịch sử tại P0.

| Tài sản hiện có | Nguồn gốc | Khả năng sử dụng / giới hạn |
|---|---|---|
| `src/kho_tri_thuc/ha_tang`, `nguon` | Code M1 được viết sau A07, mở rộng migration/artifact | Dùng lại lõi tiền/khóa/thời gian/raw/SQLite/backup; một adapter JSON fixture phân nhánh năm nguồn, không phải năm parser thực |
| `tri_thuc`, `trang_thai`, `de_xuat`, `xuat`, `hoc`, `kiem_chung`, `workflow.py` | Code mới A08 | Luồng M2–M6 chạy fixture; chưa chứng minh tương thích file ngân hàng/Junsky thực |
| `pyproject.toml`, `cau_hinh.toml`, `run.ps1`, `test.ps1` | Code/cấu hình mới | Một ứng dụng v0.2.0, VND/PLHN_FIXTURE; Python và openpyxl; script chạy/test offline |
| `tests/test_m1.py`, `tests/test_modules.py`, `tests/run_suite.py` | Kiểm thử mới | 90 test hành vi, gồm 42 hồi quy M1; báo cáo tên test/kết quả/hash tại `var/test-results/latest.json` |
| `tests/fixtures/*.json`, `base_directory/*.json` | Fixture M1, không phải nguồn được khảo sát năm 1.2 | Mẫu năm nhóm và Base để kiểm tra cấu trúc/lỗi/chống trùng |
| `kiem_chung/fixtures.py`, `kiem_chung/demo.py` | Bộ sinh dữ liệu và mô phỏng tích hợp A08 | Hai phiên, workbook, sổ mô phỏng, chốt tháng, backup/restore; không phải mapping hoặc kết quả import Junsky |
| `var/full-demo-final-v2/` | Đầu ra thật của lần chạy code trên giả lập | Nguồn JSON, SQLite, workbook chờ duyệt/đã duyệt/mù, batch, báo cáo A/B/đối soát/tháng, backup và bản restore |
| `docs/`, `README.md` | Kế hoạch, hợp đồng và hướng dẫn/báo cáo mới | Có phân biệt code-fixture, mẫu thực, kế toán ký và quyền vận hành; kiểm thử tay được để sau |

Không tìm được bổ sung bất kỳ script/mẫu khảo sát bản 1.2 nào ở danh sách mục 3. Tất cả workbook và DB mới là đầu ra fixture do lần coding tạo. Runtime Python 3.12.14/openpyxl 3.1.5 đã có sẵn trên máy, không phát sinh cài thư viện hoặc dùng dịch vụ mạng.

Ước lượng 84–143 ngày công tại mục 7 là dự toán P0 trước coding, **không phải khối lượng còn lại hoặc cam kết tiến độ hiện tại**. Chưa thể ước lượng có căn cứ thời gian hoàn thiện adapter thực/pilot khi chưa có mẫu, script, số layout, chất lượng lịch sử, đáp án độc lập và phản hồi Junsky. Lõi fixture hiện có là tài sản tái sử dụng đã chạy được; chỉ đánh giá mức giảm công adapter sau khi thử mẫu thực. Không dùng hệ số “60% đã có”.
