# Bộ prompt Codex — 6 module kho tri thức

Ngày 17/09/2026 · Dùng cùng kế hoạch 6 module trong thư mục dự án.

## Cách dùng

1. Giao **P0** trước để Codex rà soát và trình phương án, chưa lập trình.
2. Sau khi Anh duyệt, giao **một prompt M1–M6 mỗi lần**, theo thứ tự trong kế hoạch. Một module có thể làm qua nhiều lượt; không tạo thêm module quản lý.
3. Dùng **R0** để review ở cổng nghiệm thu. Review không tự cấp phép vận hành.
4. Khi mở task mới, vẫn giữ cùng thư mục dự án. Mỗi prompt đã yêu cầu đọc tài liệu và tiến độ, không phụ thuộc việc Codex nhớ cuộc trò chuyện cũ.

Trình tự đề xuất: **P0 → M1 → M2 → M3 → M6 (Baseline A) → M5 (thống kê lịch sử) → M6 (A/B) → G0 → M4 → M5 (vòng vận hành) → M6 (shadow/UAT) → G1/G2**.

M5 và M6 có một prompt chính cho mỗi module; khi gọi lại, yêu cầu tiếp tục phần chưa hoàn thành phù hợp giai đoạn. Không chạy lại toàn bộ nếu không có thay đổi hoặc lỗi mới.

## Quy ước chung cho mọi prompt module

Phần này là yêu cầu làm việc khi prompt M1–M6 viện dẫn; các prompt còn lại trong tài liệu là nội dung tham khảo, **không phải lệnh thực thi đồng thời**.

- Đọc `KE-HOACH-PHAN-MEM-KHO-TRI-THUC.md`, `KE-HOACH-MODULE-VA-LO-TRINH.md`, `DU-LIEU-VA-QUYET-DINH-CAN-CHOT.md`; đọc `AGENTS.md` và các quyết định/tiến độ nếu đã có. Yêu cầu mới nhất của Anh được ưu tiên; thay đổi kiến trúc trong kế hoạch chỉ có hiệu lực sau khi được duyệt.
- Chỉ thực hiện module được giao. Tóm tắt cách làm rồi thực hiện trong phạm vi đã duyệt; không xin lại thao tác thông thường. Nếu chưa có bằng chứng duyệt phương án, hoàn thiện thiết kế để trình trước khi coding. Chỉ hỏi những thiếu sót làm thay đổi nghiệp vụ, kiến trúc hoặc khả năng nghiệm thu.
- Không xây UI, API, AI/ML, server, tự động duyệt hoặc tự ghi sổ. Không tự sinh chính sách kế toán, mã Junsky, mapping hoặc kết quả khảo sát.
- Tìm và tái dùng script thực có; thiếu thì ghi rõ. Có thể làm phần độc lập bằng fixture giả lập; không gọi fixture là dữ liệu thực hoặc nghiệm thu adapter thật.
- Dữ liệu runtime ở nội bộ. Khi dùng Codex để đọc/gỡ lỗi, ưu tiên fixture hoặc bản đã ẩn thông tin được phép; không in dữ liệu nhạy cảm vào phản hồi, tải file ra dịch vụ ngoài, gọi API hay đưa dữ liệu thật vào nguồn tìm kiếm.
- Tiền chính xác, mã dạng chuỗi, provenance, chống trùng, transaction, phiên bản/hiệu lực và known_at theo kế hoạch. Kiểm thử các bất biến quan trọng bằng unittest hoặc bộ test đã được duyệt; không dùng test chỉ kiểm tra tên hàm tồn tại.
- Không sửa/xóa dữ liệu nguồn, thay đổi code ngoài phạm vi hoặc cài thêm dependency khi chưa có lý do/phê duyệt tương ứng. Không tự khởi tạo subagent hoặc triển khai đồng thời nhiều module.
- Cập nhật `docs/TIEN-DO.md` với đúng sáu module, trạng thái và chứng cứ; tạo khi chưa có. Ghi quyết định đã duyệt vào `docs/QUYET-DINH.md`, không tự đánh dấu một đề xuất là đã duyệt.
- Kết thúc bằng: đã làm; kiểm thử thực chạy và kết quả; demo/lệnh sử dụng; điểm chưa xác minh/đang chặn; điều kiện để nghiệm thu. Phân biệt code chạy fixture, tích hợp mẫu thực, kế toán nghiệm thu, được vận hành. Không tuyên bố test hoặc UAT đã đạt nếu chưa thực hiện.

## P0 — Rà soát và chốt thiết kế trước coding

Sao chép phần trong khung:

```text
Hãy chuẩn bị kế hoạch triển khai phần mềm kho tri thức trong thư mục dự án này; chưa viết code sản phẩm.

Đọc:
1. KE-HOACH-PHAN-MEM-KHO-TRI-THUC.md — phạm vi và quyết định gốc.
2. KE-HOACH-MODULE-VA-LO-TRINH.md — đề xuất sáu module.
3. DU-LIEU-VA-QUYET-DINH-CAN-CHOT.md — đầu vào và quyết định còn thiếu.
4. BO-PROMPT-CODEX.md — chỉ phần Quy ước chung, P0; không thực thi các prompt module.
5. AGENTS.md và tài liệu quyết định đã có nếu tìm thấy.

Yêu cầu:
- Kiểm kê file/script/mẫu đang có trong thư mục; đối chiếu tài sản tái sử dụng của bản 1.2. Không suy ra đã có script chỉ vì tài liệu nhắc tên.
- Giữ đúng sáu module M1–M6, một ứng dụng Python, SQLite, Excel, runtime offline, pilot PLHN xử lý sao kê.
- Rà D01–D10; nêu điểm mâu thuẫn, khuyến nghị và phần cần tôi/kế toán trưởng quyết định. Không tự thay quyết định cũ.
- Chuẩn bị hợp đồng dữ liệu, khóa chống trùng, quy tắc thời gian và trạng thái đề xuất/duyệt/xuất/xác minh/nhãn. Chưa có mẫu Junsky thì ghi trường cần xác nhận, không dựng mapping thật.
- Lập kế hoạch M1 có đầu vào, phạm vi, đầu ra, kiểm thử và điều kiện hoàn thành cụ thể. Nêu phần làm được bằng fixture và phần cần dữ liệu thực.
- Ước lượng theo dữ liệu/script thực tìm được; ghi giả định. Không hứa tiến độ dựa trên con số 60% chưa kiểm chứng.

Được tạo tài liệu trong docs/: HIEN-TRANG.md, HOP-DONG-DU-LIEU.md, QUYET-DINH.md, TIEN-DO.md. TIEN-DO có sáu dòng module; QUYET-DINH phân biệt đề xuất/chờ quyết định/đã duyệt.

Trả lời tiếng Việt, xưng tôi, gọi tôi là Anh. Trình phương án cụ thể và các quyết định tối thiểu cần chốt trước M1. Dừng trước coding để tôi thống nhất mục tiêu, phạm vi, kiến trúc và cách triển khai.
```

## M1 — Nền tảng và dữ liệu

Dùng sau khi đã duyệt phương án P0.

```text
Triển khai module M1 — Nền tảng và dữ liệu — theo phương án đã được tôi duyệt. Đọc phần Quy ước chung trong BO-PROMPT-CODEX.md, kế hoạch sáu module, hợp đồng dữ liệu, quyết định và tiến độ hiện có. Chỉ thực hiện M1.

Kết quả cần đạt: ứng dụng Python có thể nhận các nguồn được xác nhận, kiểm tra, chuẩn hóa chứng từ/dòng và lưu SQLite có truy nguồn, chống trùng, báo lỗi rõ.

Phạm vi:
1. Khung src/kho_tri_thuc, cấu hình được duyệt, CLI tối thiểu, logging, kiểu tiền/ngày và một hàm chuẩn hóa chữ chung.
2. SQLite, migration có phiên bản, foreign keys, transaction, audit và backup nhất quán. Lưu batch nguồn, chứng từ/dòng, khóa nguồn, provenance, as_of/exported_at/known_at, số dòng/tổng kiểm soát. Tạo schema theo nhu cầu, không xây bảng dư.
3. Giao diện bộ đọc chung. Tìm và bọc script sao kê, XML hóa đơn, bảng kê, Base, Junsky thực có; không viết lại khi chưa đánh giá khả năng tái sử dụng.
4. XML và bảng kê cùng hóa đơn phải hợp nhất thực thể nhưng giữ hai nguồn. Base quét thư mục, đối chiếu chỉ mục, ghi lỗi giải mã. Junsky gồm snapshot, danh mục và sổ chứng từ nếu có mẫu.
5. Staging và báo cáo kiểm tra trước khi ghi nghiệp vụ. Chỉ chấp nhận batch hợp lệ, không bỏ dòng lỗi im lặng.

Kiểm thử bắt buộc:
- Nạp lại cùng file, file đổi tên và bản xuất chồng kỳ không tạo trùng.
- Hai giao dịch thật cùng ngày/tiền nhưng khác tham chiếu không bị gộp.
- Mã có số 0 đầu; tiếng Việt có Đ/đ; số tiền lớn, số âm và định dạng ngày mơ hồ.
- File sai cấu trúc/tổng, lỗi giữa import: rollback, báo file/dòng và lý do.
- Sai pháp nhân/tiền tệ; HĐ trùng giữa hai nguồn; Base thiếu/chênh chỉ mục.
- Khởi tạo/nâng schema và backup/restore trên DB thử.

Không tự suy ra layout PDF/XML/Junsky chưa được cung cấp. Nếu thiếu mẫu, hoàn thiện contract và test giả lập cho phần đó, ghi rõ adapter thực còn chờ; không tạo hàm rỗng rồi báo xong. Không tự thêm ORM, web framework hoặc dependency ngoài phương án.

Bàn giao code, fixture, báo cáo nạp/validation, hướng dẫn chạy M1 và cập nhật tiến độ. Báo riêng nguồn đã kiểm tra thực và nguồn chỉ kiểm tra bằng fixture.
```

## M2 — Kho tri thức

```text
Triển khai module M2 — Kho tri thức — theo thiết kế đã duyệt. Đọc Quy ước chung trong BO-PROMPT-CODEX.md và tài liệu quyết định/tiến độ. Kiểm tra M1 đáp ứng hợp đồng cần dùng; chỉ thực hiện M2.

Kết quả: kho tri thức năm nhóm có phiên bản và liên kết lịch sử giải thích được, dùng được tại một thời điểm cụ thể.

Phạm vi:
1. Danh mục đối tượng Junsky; định danh MST, số tài khoản, bí danh và các khóa có sẵn, kèm mức xác minh.
2. Chính sách, mẫu bút toán, ràng buộc, ánh xạ tài khoản, khoản mục/dự án có hiệu lực và ngày biết/duyệt.
3. Bộ nhớ tình huống: liên kết hóa đơn–sổ trước, sao kê–sổ 112–công nợ sau; Base là bằng chứng bổ sung. Lưu LINK_A/B/C, ứng viên, lý do và chứng cứ; đo E2 từ dữ liệu có thật.
4. Quy tắc/từ khóa/khóa cứng/ngoại lệ/nhật ký từ workbook được cung cấp; thay đổi vào CHỜ DUYỆT. Lấy đúng định nghĩa chỉ số và mã lý do, không tự coi bộ mới là bộ đã chốt.
5. Contract/query cho thống kê dẫn xuất; M5 sẽ tính. Chưa tự xây vòng học trong M2.
6. Tra cứu point-in-time theo hiệu lực và known_at/approved_at; version bất biến. Thay đổi danh mục có báo cáo diff và phê duyệt.

Kiểm thử:
- Một MST nhiều tên; cùng số HĐ khác MST/ký hiệu; số chứng từ lặp giữa năm/loại.
- Định danh xung đột phải báo; nhiều ứng viên không bị ép thành LINK_A.
- Biên ngày đổi tài khoản; quy tắc biết/duyệt sau không xuất hiện trong truy vấn trước.
- Nhập Excel hai lần không tạo phiên bản thừa; thay đổi chưa duyệt không áp dụng.
- Sửa/thu hồi giữ được lịch sử và nguồn gốc.

Xuất báo cáo tỷ lệ A/B/C và không nối được, phân theo nguồn/thu/chi/giá trị; tạo mẫu để người kiểm. Nếu chưa có dữ liệu, chỉ báo kết quả fixture, không lặp số liệu bản kế hoạch như kết quả chạy. Chưa có kế toán xác nhận thì không báo độ đúng đã nghiệm thu.

Bàn giao code, dữ liệu giả lập, test, báo cáo/Excel chờ duyệt phù hợp giai đoạn, hướng dẫn và tiến độ. Không tự phê duyệt chính sách nghiệp vụ.
```

## M3 — Phiên xử lý và máy đề xuất

```text
Triển khai module M3 — Phiên xử lý và máy đề xuất — trong phạm vi đã duyệt. Đọc Quy ước chung của BO-PROMPT-CODEX.md, hợp đồng, quyết định và tiến độ; kiểm tra M1/M2. Chỉ thực hiện M3.

Kết quả: từ snapshot và tri thức hợp lệ, mở một phiên và tạo đề xuất sao kê có bằng chứng, giữ đúng giới hạn tiền/công nợ.

Phạm vi:
1. Cổng vào: phiên trước chốt, đúng pháp nhân/kỳ, as_of phù hợp, metadata/hash/tổng của gói xuất, danh mục thay đổi đã xử lý. Hash không được coi là bằng chứng duy nhất dữ liệu mới nhất.
2. Một phiên hoạt động; snapshot bất biến trong phiên; cơ chế phục hồi/hủy phiên được duyệt có audit. Phân biệt vận hành, shadow, backtest để không ghi vào cùng trạng thái nghiệp vụ.
3. Công nợ và phân bổ nhiều–nhiều, giữ chỗ/duyệt/ghi sổ/hủy. Kiểm soát tổng theo giao dịch và HĐ; quy tắc dấu/tiền tệ phải theo contract đã duyệt. Tiền dư vẫn chưa phân bổ, không ép khớp.
4. Chuỗi nhận diện → đối chiếu → ràng buộc → xếp hạng → tin cậy. Lưu bằng chứng và kết quả từng bước, phiên bản cấu hình/tri thức. Khóa cứng đã xác minh thắng từ khóa; ràng buộc cứng thắng điểm.
5. Đầu ra đầy đủ/một phần/không, tin cậy từng trường. Điểm không gọi là xác suất khi chưa hiệu chuẩn. Thiếu dự án/khoản mục thì để chưa xác định.
6. Baseline A chỉ dùng nguồn, đối chiếu, ràng buộc và mẫu kế toán đã duyệt; chuẩn bị giao diện thêm thống kê của M5. Kiểm tra đã ghi sổ trước khi đề xuất.

Kiểm thử:
- Một trả nhiều, nhiều trả một, trả một phần; thu khách hàng/chi nhà cung cấp.
- Hai thao tác tranh cùng công nợ; retry, hủy giữ chỗ; giao dịch đã xuất/ghi ở phiên trước.
- Dữ liệu cũ, sai pháp nhân, phiên trước chưa chốt, hai phiên cùng mở.
- Sai HĐ nhưng cùng tiền; hai ứng viên bằng điểm; phí NH không có công nợ.
- Thiếu đối tượng chịu chi phí; mẫu/TK hết hiệu lực; hoàn/đảo/bù trừ chưa có quy tắc thì vào ngoại lệ.

Khóa nội bộ không được quảng bá là khóa được Junsky. Thiếu bằng chứng giao dịch đã ghi sổ hay chưa phải đưa vào kiểm tra, không tự xuất lại. Chưa có 10–15 mẫu được duyệt thì thử bằng fixture có nhãn, không bịa mẫu vận hành.

Bàn giao CLI mở phiên/đề xuất, báo cáo có giải thích, test, demo và tiến độ. Excel duyệt/xuất thật thuộc M4; M3 chỉ dùng interface/fixture khi kiểm thử.
```

## M4 — Duyệt và xuất Junsky

```text
Triển khai module M4 — Duyệt và xuất Junsky — theo thiết kế đã duyệt. Đọc Quy ước chung trong BO-PROMPT-CODEX.md và tiến độ/quyết định. Xác nhận cổng G0, contract M3 và mẫu Junsky trước phần phụ thuộc. Chỉ thực hiện M4.

Kết quả: kế toán duyệt từng chứng từ trên Excel, nhập quyết định vào hệ thống, xuất batch Junsky đúng chuẩn và chốt phiên có recovery.

Phạm vi:
1. Workbook duyệt có ID phiên, ID đề xuất, version, trường máy đề xuất, bằng chứng, trường người sửa, quyết định, lý do. Giữ số 0 đầu, kiểu tiền/ngày; chuỗi từ nguồn không được trở thành công thức Excel.
2. Nhập lại: kiểm tra schema/ID/version, dòng trùng, sửa cột bất biến, giá trị ngoài danh mục. Người sửa phải chạy lại ràng buộc và phân bổ; file lỗi không cập nhật một phần. Duyệt theo lô tắt.
3. Xuất CB_tmpEntry1/2 theo template, chú thích và quy tắc EntryID/DebtID/Entry2 đã xác nhận; không suy ra schema từ tên bảng.
4. Chốt phiên: đóng băng quyết định, tạo kỳ vọng công nợ theo quy tắc dấu, batch ID/manifest/checksum, số dòng/tổng, người chốt; chỉ đổi đã xuất khi file hợp lệ và batch được xác lập.
5. Thiết kế trạng thái trung gian và recovery cho ghi file/DB; không tuyên bố atomic cho cả hai. Tái chạy không tạo nghiệp vụ mới; kiểm soát batch chưa xác minh và việc xuất lại.

Kiểm thử:
- Excel đúng/sai phiên, version cũ, dòng bị chèn/xóa/đổi khóa, nhập cùng quyết định hai lần.
- Người sửa vượt công nợ, sửa vào kỳ khóa, thay trường bắt buộc.
- Header–detail, kiểu/cột, cân Nợ/Có, đọc lại workbook đã xuất; mẫu import đã chấp nhận nếu có.
- Excel đang mở, ghi file lỗi, dừng sau xuất file nhưng trước commit, dừng trước publish; khôi phục không trùng.
- Quyết định sau chốt không âm thầm sửa batch cũ; thay thế có version/audit.

Thiếu contract Junsky thì hoàn thiện phần duyệt và export contract bằng fixture, ghi xuất vận hành bị chặn. Không tự nhập Junsky thật; kiểm thử nhập do người có quyền thực hiện và cung cấp kết quả. Phần mềm không bảo đảm Junsky chống được người nhập cùng file hai lần.

Bàn giao workbook mẫu, batch thử có đánh dấu, code/test, hướng dẫn nhập/phục hồi, các câu hỏi còn thiếu và tiến độ. Xuất thành công chưa được coi là đã ghi sổ.
```

## M5 — Đối soát và học liên tục

Dùng trước cho thống kê lịch sử; sau M4 dùng lại để nối vòng vận hành. Đọc tiến độ để tiếp tục, không viết lại phần đã đạt.

```text
Triển khai hoặc tiếp tục module M5 — Đối soát và học liên tục. Đọc Quy ước chung của BO-PROMPT-CODEX.md, quyết định và tiến độ. Chỉ làm phần được phép ở giai đoạn hiện tại:
- Trước M4: nhãn lịch sử đã xác minh, thống kê dẫn xuất và giao diện Baseline B.
- Sau M4: thêm đối soát hai phiên, xác minh và vòng học vận hành.
Không coi phần chưa có đầu vào là hoàn thành.

Kết quả: chỉ những trường có nhãn đáng tin và đúng thời điểm mới đóng góp vào thống kê; mọi quy tắc mới phải qua phê duyệt.

Phạm vi:
1. Tách trạng thái xử lý, xác minh và nhãn. Nhãn lưu trường/giá trị, tiền, bằng chứng, lý do, known_at/verified_at/eligible_at, hiệu lực, người và nhãn thay thế. Một nhãn hiệu lực mỗi chứng từ.
2. Nhãn lịch sử cần quy trình kiểm tra riêng từ liên kết/chứng từ và người có thẩm quyền, không phải copy trực tiếp kho đếm cũ.
3. Thống kê là view hoặc kết quả tính lại được từ nhãn đủ điều kiện. Đếm số lần lẫn giá trị tuyệt đối, không nhân tiền theo dòng phân bổ; phân vùng cứng theo kỳ hiệu lực, trọng số mềm chỉ bên trong vùng.
4. Khi có M4: so kỳ vọng với snapshot mới và chứng từ trong khoảng; RECON_A/B/C tách khỏi LINK_A/B/C. Xét cả phát sinh mới, bút toán tay, nhập một phần, đảo/bù trừ; số dư tổng không đủ kết luận nguyên nhân.
5. Công nợ giảm/HĐ đóng không tự nâng thành đã ghi sổ. Liên kết chứng từ và xác minh từng trường; chưa đủ giữ chưa xác minh. Nhãn B cần chứng cứ và kiểm tra độc lập, đồng thời loại nhầm bút toán do chính batch hệ thống sinh ra.
6. Đề cử quy tắc vào CHỜ DUYỆT, kèm mẫu số, giá trị, xung đột và tác động dự kiến. Chạy kiểm chứng/tập vàng qua M6 trước duyệt; không tự kích hoạt.

Kiểm thử:
- Nhãn chỉ duyệt/đã xuất không được học; nhãn lịch sử xác minh đúng mới được học.
- Thu hồi/thay thế/tính lại nhiều lần cho kết quả nhất quán; known_at/eligible_at sau cutoff không lọt vào backtest.
- Một giao dịch nhiều dòng không tăng đếm; thay TK giữa kỳ không học chéo ranh giới.
- Công nợ bằng 0 do điều chỉnh khác, hai chênh trái dấu, đúng tiền sai HĐ/TK/dự án đều không tự xác minh đúng.
- Phí NH ngoài 131/331 cần bằng chứng sổ; nhập một phần không xác nhận cả batch.

Bàn giao code/test, báo cáo đối soát khi đủ nguồn, thống kê có nguồn gốc, đề cử và tiến độ. Chưa đo hiệu quả thật thì không khẳng định học cải thiện chất lượng; so sánh đó do M6 thực hiện trên dữ liệu hợp lệ.
```

## M6 — Kiểm chứng, báo cáo và vận hành

```text
Triển khai hoặc tiếp tục module M6 — Kiểm chứng, báo cáo và vận hành. Đọc Quy ước chung trong BO-PROMPT-CODEX.md và tiến độ/quyết định. Chọn phần tương ứng đầu vào đã có: kiểm chứng dữ liệu; Baseline A; Baseline A/B; shadow; hoặc UAT. Không triển khai lại phần đã đạt nếu không có thay đổi/lỗi mới.

Kết quả: có bằng chứng đáng tin để tôi quyết định qua cổng G0/G1/G2; không chỉ có báo cáo test kỹ thuật.

Phạm vi:
1. Fixture giả lập và kiểm thử tích hợp các bất biến; CLI điều phối dễ dùng, thông báo lỗi tiếng Việt, chế độ shadow/backtest tách dữ liệu vận hành.
2. Tái dựng công nợ lịch sử bằng mốc và phát sinh đủ chứng cứ; kiểm tra số dư tại các mốc. Không dùng snapshot cuối tháng tương lai làm trạng thái dự báo ngày trước.
3. Backtest point-in-time: cùng dữ liệu/cutoff/config/version cho A và B; A dùng mẫu/ràng buộc, B thêm thống kê đủ điều kiện. Cắt theo known_at, approved_at, eligible_at và hiệu lực; đáp án chỉ xuất hiện khi chấm.
4. Tập vàng có phiên bản, holdout riêng và mẫu kiểm tra mù độc lập. Chưa có thời điểm biết dữ liệu thì công bố giới hạn hồi cứu; chưa có người kiểm thì không báo độ đúng đã xác minh.
5. Báo đúng toàn bộ/từng trường, phủ đầy đủ/một phần/không, đúng phân bổ, lỗi theo trị tuyệt đối tiền, theo thu/chi/giá trị. Công bố mẫu số, mục bị loại/chưa có đáp án và phân tích phần dư.
6. Báo cáo kỳ theo bộ 6 phần đã được cung cấp/duyệt; nếu chưa có, trình cấu trúc đề xuất và ghi trạng thái chờ. Kiểm tra mù che đề xuất trước khi người lập đáp án.
7. Khi đủ M1–M5: test hai phiên, import một phần/trùng, ghi tay ngoài hệ thống, sai HĐ cùng tiền, lỗi giữa xuất, phục hồi DB/batch. Khóa tháng chỉ sau đối soát cuối không còn mục chặn.
8. Hướng dẫn kế toán/IT, backup/restore thử trên bản sao, checklist UAT và biên bản kết quả. Không thay DB thật hoặc nhập Junsky thật chỉ để test.

Bàn giao báo cáo có thể tái lập với input hash/config/version/cutoff, test và kết quả thực chạy, hướng dẫn, các lỗi còn lại và đề nghị go/no-go có căn cứ.

Ngưỡng G0/G1/G2 phải lấy từ quyết định đã duyệt. 98% hoặc 50 mẫu/tuần trong kế hoạch gốc là gợi ý, không tự biến thành chuẩn chốt. B không tốt hơn thì kiến nghị giữ A. Codex không tự ký nghiệm thu kế toán hoặc tự mở chế độ vận hành.
```

## R0 — Review trước khi qua cổng

```text
Review kết quả hiện tại của dự án kho tri thức theo kế hoạch sáu module và cổng đang xin nghiệm thu. Đọc quyết định/tiến độ, kiểm tra code, test và báo cáo có thật. Chỉ review và cập nhật báo cáo, chưa sửa code hay chuyển cổng.

Ưu tiên lỗi có thể gây: nhập trùng; sai tiền/dấu/HĐ; vượt công nợ; mất giữ chỗ; Excel cũ ghi đè; xuất lỗi nhưng DB báo thành công; xác nhận ghi sổ từ số dư đơn thuần; nhãn chưa đủ điều kiện được học; rò rỉ tương lai; hoặc mất khả năng phục hồi.

Với mỗi lỗi, chỉ ra file/vị trí, tình huống tái hiện, tác động và cách kiểm tra sửa. Chạy test liên quan khi an toàn, không thao tác DB/dữ liệu thật. Phân biệt bằng chứng đã quan sát và giả thuyết chưa kiểm tra.

Đối chiếu acceptance criteria, ghi từng tiêu chí đạt/chưa đạt/chưa đủ dữ liệu. Tách code chạy fixture, adapter đã thử mẫu thật, nghiệp vụ đã được kế toán ký, quyền được vận hành.

Bàn giao docs/REVIEW-CONG.md: kết luận đề nghị qua/chưa qua cổng, lỗi theo mức ảnh hưởng, dữ liệu/quyết định còn thiếu. Không nói đã qua chỉ vì tất cả unit test xanh; quyết định cuối theo vai trò và ngưỡng đã duyệt.
```

## Nguồn tham khảo về cách viết prompt

Cấu trúc giao việc nêu hành vi mong muốn, bối cảnh/tài liệu, giới hạn và cách xác minh phù hợp hướng dẫn [Prompting Codex — OpenAI](https://learn.chatgpt.com/docs/prompting#prompting-codex), đã đọc ngày 17/09/2026. Toàn bộ thiết kế nghiệp vụ và tiêu chí cụ thể ở trên được xây từ tài liệu dự án và phân tích, không phải hướng dẫn kế toán của OpenAI.
