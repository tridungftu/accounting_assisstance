# Kế hoạch vòng 2 — từ dữ liệu đã chuyển đổi tới phiên shadow PLHN

**Cập nhật A12/V1b:** Anh đã giao đợt bổ sung V1b giữa V1 và V2. Kết luận V1 đạt bằng số hồi cứu cũ bị thay thế: cột lan_dau trước 01/08/2026 mới dùng nghiệm thu. Cache/tra thứ tự được kéo lên V1b; hướng nhiều dòng đã duyệt, đưa vào V2 khi giao riêng. V1b đã sửa và đo nhưng chưa đạt chất lượng; chưa tự chuyển V2. Chi tiết sáu quyết định tại QUYET-DINH.md và kết quả tại BAO-CAO-V1.md.

**A11 — ĐÃ ĐƯỢC ANH DUYỆT ngày 18/09/2026:** QV01–QV08 được chấp thuận rõ; chỉ V1 được giao thực hiện ở lượt này. Phần “chờ duyệt/mặc định” bên dưới giữ nội dung bản đã trình để truy vết. Đính chính hiện hành: Entry1 17 cột; TU-DIEN bản mới 9 sheet đọc lại tại V4; chưa nhập Junsky; cho phép xlrd 2.0.x offline; actor duyệt vận hành CFO_NTD. Xem nhật ký A11 trong QUYET-DINH.md.

Ngày 18/09/2026. **ĐỀ XUẤT — CHỜ ANH DUYỆT.** V0 không thay code sản phẩm, schema hoặc quyết định kế toán. Căn cứ: [bộ prompt vòng 2](../BO-PROMPT-CODEX-VONG-2.md), kiểm kê thực và [kết quả V0](BAO-CAO-V0.md). Không ước lượng ngày; không dùng tỷ lệ “60% đã có”.

## 1. Kết luận và phạm vi

Đủ tài sản để bắt đầu V1 sau khi Anh duyệt phương án. Chưa đủ căn cứ mở vận hành hạch toán. Có script cũ, mẫu Junsky, dữ liệu nguồn và lát cắt tháng 8; các adapter sản phẩm vẫn chưa có, tri thức chưa được kế toán duyệt và một số ý nghĩa cột Junsky còn chưa xác nhận. Kết quả chạy JSON chỉ chứng minh tái hiện kịch bản hồi cứu đã cấp.

Giữ **đúng sáu module M1–M6**, một ứng dụng Python, SQLite, Excel, runtime offline, pilot PLHN xử lý sao kê. Giao diện HTML cục bộ đã được Anh yêu cầu tại A09 tiếp tục là cửa nhận hồ sơ. V1–V6 là sáu đợt cải tiến các module hiện hữu, không phải sáu module mới.

| Module | Công việc vòng 2 |
|---|---|
| M1 — Nền tảng và dữ liệu | Hợp đồng v2, bộ đọc năm nhóm nguồn, kiểm soát tổng/khóa/thời gian, raw và migration |
| M2 — Kho tri thức | POLICY/CASE, thứ tự xét, Excel của người, hiệu lực và phê duyệt |
| M3 — Phiên và đề xuất | Kích hoạt mẫu bằng định danh/từ khóa, bằng chứng, ràng buộc, hiệu năng |
| M4 — Duyệt và xuất | Workbook gọn, round-trip, mapping Entry1/2 được xác nhận, batch shadow |
| M5 — Đối soát và học | Trạng thái ghi sổ theo nguồn, xác minh từng trường, nhãn từ bằng chứng |
| M6 — Kiểm chứng và vận hành | Hồi quy tháng 8, đo phủ/đúng/hiệu năng, backup/restore, hồ sơ nghiệm thu |

Chung một code nhưng tách hai cấu hình và SQLite: `fixture` cho dữ liệu giả lập; `that` với pháp nhân PLHN, thư mục riêng, nhận dữ liệu thật. Các JSON tháng 8 đã được bên chạy thử chuyển đổi và gắn nhãn fixture trước khi cấp: giữ nguyên, lưu dưới `var/`, ghi rõ **dữ liệu thật đã chuyển đổi**, không đưa vào `tests/fixtures/` hoặc dùng làm demo công khai. V0 không gắn lại `synthetic=true` cho nguồn gốc.

Luồng nghiệp vụ giữ nguyên: **đề xuất → người duyệt → xuất batch → xác minh bằng sổ → nhãn học đủ điều kiện → đề cử tri thức chờ duyệt**. Xuất không đồng nghĩa đã ghi sổ; dữ liệu sổ không tự chứng minh mọi trường; nhãn mô phỏng không được nhập vào kho học vận hành.

## 2. Cách đo và quản lý thay đổi

- Giữ 105 dòng sao kê và 62 đáp án chắc chắn của tháng 8; ghi hash dữ liệu, cấu hình, code, môi trường, cutoff, nguồn tri thức và actor mỗi lần chạy. Không thay đáp án để làm đẹp kết quả.
- Tách **tái hiện kịch bản cũ C1/C2/C3**, **đánh giá hồi cứu bằng tri thức hiện có**, và **kiểm chứng ngoài mẫu theo thời gian**. Workbook mới biết trong tháng 9 không được giả định đã biết đầu tháng 8. `lan_dau`, `mtime`, ngày nghiệp vụ và `known_at` không thay thế nhau.
- C2 cũ có duyệt mô phỏng NHAP. Không chuyển sự kiện đó sang kho thật; V1 cần Anh xác nhận kịch bản mô phỏng riêng nếu muốn dùng nhóm NHAP để so sánh cùng điều kiện. Tri thức nhập mới mặc định chờ duyệt.
- Trình đồng thời số đúng/mẫu số trên FULL hiện hành, kết quả trên cùng tập dòng FULL gốc, số dòng mới có/không còn đề xuất và độ phủ theo trị tuyệt đối tiền. Mẫu số thay đổi phải được giải thích; không chỉ so hai tỷ lệ của hai tập khác nhau.
- Giữ bộ chấm cũ để tái hiện; tới V5 thêm bộ chấm đã sửa với phiên bản riêng và tính lại các mốc so sánh. `NONE` là không đề xuất; không tính trường hoặc tiền sai như một đề xuất đã đưa ra.
- Đo riêng mở phiên, đề xuất, tạo workbook, đánh giá; ghi số đối tượng thực dùng. Con số 19 giây trong runner cũ là cả bước phiên, không phải một phép đo riêng `propose`.
- Mọi thay đổi DB tiếp nối schema v8, thêm migration mới có checksum; không sửa migration đã áp dụng. Backup trước nâng cấp, kiểm tra dữ liệu trước/sau, chạy lại migration không đổi kết quả, rollback giao dịch khi lỗi. Nếu chỉ thay payload/validation thì ghi rõ không có DDL, vẫn có phiên bản hợp đồng.
- Kết thúc từng V: chạy toàn bộ fixture, lát cắt tháng 8, lưu bảng trước/sau, lỗi còn lại và điều kiện nghiệm thu. Chỉ sang V kế tiếp sau khi Anh giao; không tự mở rộng sang xử lý kỳ dài ngoài phạm vi nạp thử ở V3.

## 3. V1 — máy đề xuất, làm trước bộ đọc thật

**Đầu vào đã có:** 13 JSON của gói chạy thử; code/schema v8; `BO-QUY-TAC.xlsx` có 809 quy tắc, 164 dòng STK và danh mục đầy đủ 2.027 đối tượng; từ điển 431 regex; 105 sao kê, 62 đáp án. 809 quy tắc hiện gồm 182 DE_CU và 627 NHAP; STK gồm 35 CHAC_CHAN và 129 NHAP. Chưa có phê duyệt vận hành cho các hàng này.

**Phạm vi M2/M3:**

1. Version payload POLICY mới: kiểu trigger, khóa có loại/giá trị, regex, chiều, phân vùng, bậc và thứ tự, các trường kết quả có thể thiếu, provenance file/sheet/dòng. Biểu diễn cả số TK, MST, mã đối tượng; tên đối ứng có loại điều kiện riêng, không tự thành định danh đã xác minh.
2. Thứ tự thực trong workbook: bậc 1 **STK + từ khóa**, bậc 2 **STK**, bậc 3 **tên + từ khóa**, bậc 4 **tên**, bậc 5 **từ khóa**. Đề xuất dùng bậc rồi thứ tự hàng nguồn làm bản thứ tự trình duyệt; không dùng thống kê T8 để xếp lại. Khớp đầu tiên trong phân vùng; thứ tự trùng trong khoảng hiệu lực chồng nhau bị từ chối. Không bỏ cổng xung đột giữa các phân vùng nếu chúng cùng định khoản một giao dịch.
3. Chuẩn hóa văn bản dùng hàm Đ→D đã có. Regex được kiểm tra riêng, không chuẩn hóa phá cú pháp; loại trừ và ranh giới được khai báo trong mẫu. Mẫu sai cú pháp, rỗng/quá rộng hoặc ngoài giới hạn xử lý phải bị báo tới hàng nguồn.
4. CASE có khóa chính xác theo pháp nhân + phạm vi tài khoản/loại tham chiếu + giá trị hoặc hash mô tả chuẩn hóa; có phiên bản chuẩn hóa, hiệu lực, known_at, actor và bằng chứng. Xét trước POLICY nhưng vẫn chịu kiểm tra trùng, khóa kỳ, mã danh mục và cân tiền. Hai CASE cùng khớp mâu thuẫn → chờ người.
5. `han_dung` ánh xạ vào `valid_to` loại trừ ở cuối khoảng. Đề xuất hiểu ngày ghi trên Excel là ngày cuối còn dùng: lưu ngày kế tiếp; giữ raw. Báo mẫu hết hạn khớp nhưng không sử dụng, không làm lộ tri thức chưa biết tại cutoff.
6. Trình thiết kế mẫu nhiều dòng 1331/6427; chưa triển khai trong V1. Không biến chuỗi có dấu `|` thành mã tài khoản hợp lệ; giao dịch cần tách dòng tiếp tục chờ.

**Tương thích/schema:** fixture POLICY cũ vẫn dùng contract v1 để giữ 111 test; payload mới có version rõ. Dự kiến tận dụng bảng version/event hiện có cho CASE/trigger. Nếu cần cấu trúc lưu thứ tự phục vụ ràng buộc đồng thời thì thêm migration sau v8, duy nhất theo phân vùng/bậc/thứ tự và khoảng hiệu lực; không đặt UNIQUE bỏ qua lịch sử phiên bản. Chưa sửa hợp đồng nguồn ở V1.

**Triển khai và đầu ra:** bản chuyển đổi nằm riêng `var/vong-2/V1/`, đọc workbook hiện hữu, tạo manifest đầy đủ 809 + 164 hàng và phân nhóm chờ duyệt; không chạy lại phần `chuan_bi.py` phụ thuộc pickle thiếu. Tầng tên đối ứng trong V1 dùng trường đã có hoặc bằng chứng phụ được đánh dấu trong harness; không tự sửa BANK v1 để lách V2. Nếu thiếu trường để kích hoạt một mẫu thì báo không đánh giá được. Xuất bằng chứng mẫu chọn, mẫu bị loại, thiếu dữ liệu và `SAI-CON-LAI.json` riêng tư.

**Test thêm:** ba kiểu trigger; định danh đã xác minh thắng từ khóa; thiếu trường chỉ điền phần còn thiếu; thứ tự/va chạm/khác phân vùng; CASE trùng hoặc khác kỳ/known_at; thu hồi/thay thế; hạn dùng; mẫu thiếu tên đối ứng; giữ kiểu ID; 5 bẫy UNG HO, MUA HOA, DAU, HOA CHAT, PHI kèm cả ví dụ phải khớp; regex lỗi; không tự duyệt NHAP. Test tự động dùng dữ liệu giả lập.

**Nghiệm thu tháng 8:** toàn bộ fixture đạt; hàng nhập + hàng chờ/lỗi = 809 quy tắc và 164 ánh xạ; số đúng đối tượng trên tập FULL gốc tăng so với 12/44, TK Nợ/Có không dưới 36/40 trên tập đối chiếu tương ứng; công bố cả mẫu số mới và thay đổi độ phủ; đếm riêng không mẫu/hòa thứ tự/hết hạn. Nếu chưa được duyệt mô phỏng cùng cohort, ghi chưa đủ điều kiện so ngưỡng C2, không tự nâng trạng thái NHAP. V1 xong chưa đồng nghĩa được vận hành thật.

**Làm bằng giả lập:** engine, CASE, validation, lỗi regex, xung đột, thời gian, tương thích. **Cần dữ liệu thật:** chuyển đúng 809 quy tắc, xác nhận nghĩa khóa/tên, đo tháng 8 và xem từng sai sót. **Cần Anh/kế toán:** các lựa chọn tại mục 9, không cần chờ bộ đọc thật hoặc mapping Junsky để bắt đầu phần đã duyệt.

## 4. V2 — hợp đồng dữ liệu nguồn

**Đầu vào:** XML/bảng kê gốc, CSV đã khảo sát, workbook Base, sáu danh mục Junsky và các sổ thực; hợp đồng v1 và JSON tháng 8.

**Thay đổi M1:** tiền hóa đơn tách trước thuế/thuế/tổng, dòng có thuế suất/tính chất; dung sai khai báo, đề xuất 1 VND/dòng; giữ điều chỉnh âm, chiết khấu, thay thế/hủy và liên kết hóa đơn gốc. Khóa invoice là pháp nhân + MST bán + ký hiệu + số + mẫu số, tất cả ID dạng text. XML và bảng kê một chứng từ, nhiều bằng chứng với known_at riêng. Trạng thái riêng của từng nguồn nằm trong bằng chứng; khác tiền vượt dung sai thì quarantine chứng từ, không từ chối toàn bộ file.

Base bổ sung tên/trạng thái/ngày duyệt/tiền/tiền tệ/tài khoản thụ hưởng/dự án thô/tệp đính kèm; chưa phân nhóm G tại tầng nguồn. OPEN_ITEM lấy từ chứng từ công nợ thật; ID chứng từ/hóa đơn/đối tượng/TK, as_of/snapshot do người nạp khai, không từ mtime. JOURNAL giữ DocsNo/số CT đính kèm, dòng định khoản và các dimension; trạng thái ghi sổ có cấu hình. BANK giữ MTID/CITAD, tên/TK đối ứng, ngày phát sinh; thiếu tham chiếu thì khóa dự phòng kèm mức tin cậy, không gộp hai giao dịch chưa phân biệt được.

**Schema/migration:** version hợp đồng nguồn v2; thêm cấu trúc tiền thuế, quan hệ HĐ, metadata bằng chứng, mâu thuẫn nguồn, thuộc tính Base/sổ/sao kê. Giữ khóa document hiện có, không tái tính ID toàn bộ lịch sử; nếu canonical core đổi phải có chuyển đổi rõ và hash trước/sau. Chuyển trạng thái nguồn ra khỏi invoice core phải giữ bằng chứng cũ. Đồng thời sửa đường promote để ghi nhận kết quả từng chứng từ và chặn dùng chứng từ mâu thuẫn.

**Test:** trong/ngoài dung sai; dòng âm/chiết khấu/ghi chú; XML→bảng kê và ngược lại; nguồn mâu thuẫn không ghi đè; known_at từng header/detail; mã số 0 đầu; Base tiền có hậu tố; công nợ nhiều snapshot; trạng thái ghi sổ cấu hình; khóa dự phòng và va chạm.

**Nghiệm thu:** 75 XML nạp từ nội dung thuế đúng, không dựng dòng thuế giả; 19 bảng kê mới + 5 trùng tạo tổng 94 hóa đơn duy nhất, 5 hóa đơn có hai bằng chứng; lệch thực được báo thay vì ép khớp. Sổ T8 lấy tham chiếu từ nguồn nếu có, không âm thầm lấy Tập chuẩn; trường không có phải đánh dấu. Đề xuất không giảm so V1 trên cùng điều kiện; thay đổi có căn cứ từ sửa hợp đồng phải giải trình riêng.

## 5. V3 — bộ đọc thực và chế độ `that`

**Đầu vào:** 8 `.xls` eFAST; 24 PDF/2 layout; 1.907 XML/67 bảng kê; 1.283 thư mục Base có JSON và chỉ mục 1.115; danh mục/sổ/công nợ. Script cũ chỉ là ứng viên: cần sửa đường dẫn, bỏ ghi đè nguồn, đổi tiền float và thử trên bản sao. `xlrd` chưa có trong runtime khảo sát; chuẩn bị dependency khóa phiên bản và gói cài offline trước khi thử `.xls`.

**M1/M6:** năm adapter phát cùng contract v2. `.xls` tìm nhãn STT/No. và khối tổng, không cố định dòng; PDF kiểm tra số dòng, dư lũy kế, tổng và chồng file. Quét Base độc lập chỉ mục, báo phần dư/thiếu/lỗi; không coi tệp đính kèm là đề nghị. XML/bảng kê giữ đầy đủ trạng thái gốc. Chọn sổ theo cột thực, khai rõ sổ không có tham chiếu. Kỳ khóa khai báo tay phải có người và thời điểm. Lệnh nạp có as_of/exported_at/cơ sở known_at, kiểm tra trước commit và chống trùng.

Nối receipt HTML đã có với adapter đã chọn và báo cáo kiểm soát; nhận file gốc vẫn giữ nguyên byte. Không biến thao tác tải lên thành duyệt tri thức hoặc duyệt hạch toán. Bổ sung chỉ báo rõ môi trường, kết quả nạp và lỗi nguồn; không thiết kế lại toàn bộ UI trong V3.

**Schema/migration:** môi trường gắn chặt vào kho, adapter/version/source-status mapping, manifest đầy đủ và liên kết receipt→attempt; migration mới nếu có bảng/cột phát sinh. Chặn mở nhầm SQLite giữa hai môi trường. Xuất/nhập Junsky thật tiếp tục khóa.

**Test/nghiệm thu:** test giả lập mỗi layout/lỗi và kiểm chứng riêng trên nguồn thật trong `var/`; T8 đường thật và JSON cho cùng 105 kết quả hoặc có giải trình từng lệch do bản chuyển đổi cũ mất dữ liệu. Nạp lại không tăng chứng từ; tổng theo kỳ của XML/bảng kê khớp nguồn CSV hoặc báo chênh có căn cứ. Quét toàn kỳ vào kho riêng, chỉ nạp/đo, chưa đề xuất. 236 nhóm trùng PDF là mốc cần đối chiếu với workbook cũ, không dùng số đó để ép parser báo đúng. Đo chênh 1.283/1.115 Base bằng ID, không chỉ trừ số lượng.

## 6. V4 — Excel tri thức để người dùng quản trị

**Đầu vào:** ba workbook BO-QUY-TAC, TU-DIEN-NHOM-NGHIEP-VU, HOA-DON-CAY-PHAN-NHANH; contract V1/V2. Đã thấy 431 regex, 33 nhóm, 149 NCC, 28 khoản mục; từ điển hiện **không có sheet 3B KHÓA CỨNG**, phải báo thiếu hoặc tạo cấu trúc rỗng trong bản xuất mới, không bịa dữ liệu.

**M2/M4/M5:** nhập Excel thành version chờ duyệt, giữ trạng thái nguồn riêng. DE_CU/CHAC_CHAN/ĐANG DÙNG chỉ là gợi ý cho người. Xuất cột người đọc được; JSON kỹ thuật ở sheet ẩn; quyết định có actor/lý do và kiểm tra version workbook. Ba chỉ số từ khóa tính lại từ chứng từ đủ điều kiện tại cutoff theo lượng và tiền, không tự đổi trạng thái. Nhật ký/hiệu lực theo kỳ; báo cáo kỳ sáu phần; lô tri thức có known_at và nguồn rõ.

**Schema/migration:** provenance lô/hàng, mã workbook/revision, quyết định và sự kiện vòng đời; tận dụng version/event, migration bổ sung khi cần. Không copy bộ đếm tích lũy cũ thành nhãn mới.

**Test/nghiệm thu:** đối chiếu tổng hàng từng sheet, báo hàng chú thích không phải dữ liệu; import→export→import không sửa tạo 0 sự kiện; một quyết định hợp lệ tạo đúng 1; workbook cũ/dòng sai bị chặn; chưa duyệt không có hiệu lực; kỳ chồng và known_at tương lai không lọt vào đề xuất. T8 bằng Excel tri thức không kém V1/V2 trong cùng điều kiện phê duyệt; giữ nguyên các hàng chưa được duyệt.

## 7. V5 — hiệu năng, workbook và chấm điểm

**Đầu vào:** V4, toàn bộ 2.027 đối tượng, 105 sao kê, 62 đáp án. Không thu hẹp danh mục để đạt thời gian.

**M2/M3/M4/M6:** gom truy vấn tri thức theo snapshot/cutoff/ngày/nhóm, cache theo phiên với invalidation khi có event; đo trước khi chọn index mới. PHAN_BO chỉ liệt kê ứng viên phù hợp, tối đa N/đề xuất, đề xuất N=10; CONG_NO_KHAC cho tra/chọn phần còn lại mà vẫn kiểm tra mã và số dư khi nhập ngược. Bộ chấm phân biệt abstain/sai, thêm phủ theo tiền và không chấm fields của NONE. Bỏ POSTED_SOURCE_FIXTURE khỏi logic engine/đối soát, dùng cấu hình nguồn; giữ fixture đúng nơi cần tương thích. Mã Excel dạng text, ngày ISO.

**Schema/migration:** migration nếu thêm index/cache lưu DB; cache trong RAM không cần bảng. Version workbook mới, tương thích đọc bản cũ theo hợp đồng; version bộ chấm tách biệt để không so chỉ tiêu khác định nghĩa.

**Test/nghiệm thu:** invalidation sau approve/revoke/supersede, kết quả không đổi với cache; nhiều cutoff/phiên không lẫn; workbook 105 dòng <500 KB; chọn đối tượng ngoài top N không vượt số dư hoặc phá liên kết; NONE không bị tính sai. Với đầy đủ 2.027 đối tượng, đề xuất 105 dòng <10 giây và đánh giá 62×2 <30 giây trên máy này; đo riêng pha, không chạy suite đồng thời. Đề xuất trùng V4 trên cùng đầu vào, báo mọi khác biệt khi thêm danh mục.

## 8. V6 — phiên shadow và cổng R1

**Đầu vào:** V1–V5 đã nghiệm thu; tri thức được duyệt đúng phạm vi; nguồn tháng 8 thật; công nợ/as_of/kỳ khóa; mẫu Entry1/2 và xác nhận các cột còn thiếu. Nếu không có Base 2026 thì ghi thiếu, không dùng hồ sơ 2025 giả thành cùng kỳ.

**M3–M6:** nạp, đề xuất, workbook người dùng; 62 đáp án chắc chỉ dùng duyệt mô phỏng với actor rõ; dòng mơ hồ WAIT. Xuất file **SHADOW — CHƯA NHẬP** trong thư mục riêng, không import Junsky. Cổng xuất shadow là quyền thử riêng để làm V6; cổng vận hành thật tiếp tục khóa tới quyết định của Anh/kế toán sau nghiệm thu.

Mẫu thực hiện có Entry1 **17 cột, gồm ErrorText**, Entry2 37 cột. Prompt ghi Entry1 16: đề xuất giữ nguyên 17 theo mẫu NCC, cần xác nhận trước viết exporter. Chưa suy ra `EntryID`, `DebtID`, `EntryDM`, BankID/CashflowID hoặc chế độ Entry2 từ tên cột. Tệp JUNSKY-CHI/THU-T8 đang có là tệp được script dựng; cần bằng chứng nhập thành công hoặc xác nhận của kế toán để gọi là chuẩn đã nhập.

**Schema/migration:** export mapping có version/hash và trạng thái shadow, manifest giữ nguồn/decision; nhãn mô phỏng tách nhãn vận hành. Mẫu nhiều dòng nếu được duyệt phải thay contract proposal/decision/export_items và quan hệ Entry1→Entry2 bằng migration mới; không lén đưa vào V6.

**Test/nghiệm thu:** đối chiếu từng cột theo DocsNo, Entry2 theo khóa dòng/cụm chứng từ, tổng theo TK và từng tiền tệ; báo thiếu/thừa/mơ hồ và các nhóm nguyên nhân, không ép khớp bằng đổi chứng từ. Sổ T8 dùng cho đối soát sau xuất, không lọt vào nguồn đề xuất. RECON_A/B/C có bằng chứng từng trường, nhãn mô phỏng không dùng để học vận hành. Backup/restore và batch recovery giữ đúng byte/hash. Hoàn tất bảng tháng 8 và danh sách chặn pilot; không tuyên bố sẵn sàng vận hành.

R1 là review hồ sơ/tám phát hiện/rò rỉ thời gian/dữ liệu/hiệu năng, cập nhật REVIEW-CONG, không tự sửa code hoặc mở quyền import. Việc nhận tri thức kỳ dài theo lô sau đó là lần giao việc riêng.

## 9. Các lựa chọn cần Anh duyệt trước V1

Các mặc định dưới đây là **khuyến nghị/chế độ chờ**, không phải phê duyệt bằng im lặng. Chỉ dẫn “tiếp tục chạy” tiếp tục V0, không tự đánh dấu kế hoạch V1–V6 đã duyệt.

| ID | Câu hỏi cho Anh/kế toán trưởng | Khuyến nghị và lý do | Nếu chưa trả lời |
|---|---|---|---|
| QV01 | Anh duyệt mục tiêu, kiến trúc và thứ tự V1→V6 này để giao V1 trước? | Giữ sáu module và các cổng từng V; sửa máy đề xuất trước bộ đọc để đo được lợi ích ngay | Dừng ở hồ sơ V0; không sửa sản phẩm |
| QV02 | Dùng thứ tự hiện tại trong từng bậc workbook làm danh sách trình duyệt? | Bậc 1→5 đúng dữ liệu; trong bậc dùng hàng nguồn, không số lần đúng có chứa T8; va chạm trong thời gian hiệu lực phải chặn | Chỉ dựng danh sách đề xuất, chưa đưa thứ tự vào kho có hiệu lực |
| QV03 | Anh cho dùng những nhóm trạng thái nào trong **mô phỏng kiểm chứng V1**, đặc biệt 627 quy tắc và 129 ánh xạ NHAP? | Cho tái hiện riêng C1/C2 với actor mô phỏng nếu cần so ngưỡng C2; kho thật tất cả chờ duyệt, không kế thừa phê duyệt thử | NHAP chờ duyệt; số đo có thể xuất nhưng chưa kết luận đạt ngưỡng C2 cùng điều kiện |
| QV04 | Chấp nhận dùng tri thức biết hiện tại để đo hồi cứu T8, tách khỏi đánh giá ngoài mẫu? | Giữ known_at thật; báo benchmark hồi cứu, không lùi ngày tạo/duyệt về trước cutoff cũ | Chỉ tái hiện bộ JSON cũ; chưa coi Excel mới là tri thức đã biết tại C1/C2 |
| QV05 | Tên đối ứng được dùng như điều kiện mẫu ở bậc 3/4, còn định danh đã xác minh vẫn ưu tiên? | Có; tên khớp không chứng minh danh tính. Xung đột với mã đã xác minh thì chặn/đề nghị rà, tránh điền sai đối tượng | Không nâng tên thành khóa cứng; hàng thiếu tên đối ứng báo thiếu điều kiện |
| QV06 | CASE được ưu tiên mẫu nhưng có được vượt xung đột định danh, khóa kỳ hoặc chống trùng? | Không; CASE chỉ sửa quyết định nghiệp vụ có căn cứ, các cổng dữ liệu vẫn giữ. Hai CASE mâu thuẫn phải chờ | Giữ chặn; ngoại lệ chưa duyệt không dùng |
| QV07 | Ngày `han_dung` trên Excel là ngày cuối quy tắc còn hiệu lực? | Có; lưu `valid_to` bằng ngày kế tiếp, phù hợp khoảng nửa mở đang dùng, giữ raw để kiểm tra | Hàng chưa xác định nghĩa ngày đưa chờ, không tự kéo dài thời hạn |
| QV08 | V1 chỉ trình thiết kế nhiều dòng và giữ các ca cần tách thuế ở trạng thái chờ? | Có; cần chốt phân bổ thuế và quan hệ Entry2 trước khi sửa export_items, tránh ghép mã tài khoản bằng dấu `|` | Chưa triển khai mẫu nhiều dòng; ca liên quan chờ người |

## 10. Phần còn thiếu và điều kiện mở việc phụ thuộc

Không cần xin lại các file đã kiểm kê. Cần **quyết định/metadata**: actor duyệt tri thức, thứ tự và thời hạn; thời điểm xuất/as_of/cơ sở known_at của các snapshot; phạm vi sổ và người khai kỳ khóa; ý nghĩa chính xác mã công nợ/EntryID/Entry2 và danh mục BankID/CashflowID; bằng chứng file T8 nhập thành công; Base kỳ 2026 nếu muốn dùng trong phiên T8; ngưỡng kế toán và người nghiệm thu pilot.

Có thể làm ngay sau khi V1 được giao: nâng engine, CASE, regex, kiểm thử giả lập, chuyển tri thức vào trạng thái chờ và chạy kiểm chứng được cho phép. Bộ đọc `.xls`, contract hóa đơn, UI xử lý thật, workbook người dùng, mapping xuất và đối soát hoàn chỉnh làm đúng V tương ứng. Không bỏ qua việc kiểm tra script cũ: parser PDF và workbook cùng tên có dấu hiệu khác phiên bản; nhiều script phụ thuộc pickle chưa có. Công tái sử dụng được xác nhận từng phần sau smoke test, không quy thành phần trăm hoàn thành.
