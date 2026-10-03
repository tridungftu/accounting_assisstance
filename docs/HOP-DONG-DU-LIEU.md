# Hợp đồng dữ liệu — thiết kế đã thống nhất và phạm vi M1

**Trạng thái hiện hành sau V6:** contract V2–V6 đã triển khai tại §12, schema SQLite là v14. Các đoạn ghi V0/v1/v8 dưới đây được giữ làm lịch sử, không mô tả trạng thái hiện hành. Mẫu và dữ liệu thật vẫn không đồng nghĩa được phép import Junsky hoặc vận hành hạch toán.

Phiên bản tài liệu: 0.4 · Cập nhật 18/09/2026 · một ứng dụng Python offline, SQLite, Excel, sáu module và hai kho fixture/that. Định dạng fixture: `ktt-fixture-v1`; phiếu tiếp nhận raw: `ktt-local-intake-v1`.

Hợp đồng cho đúng sáu module M1–M6 trong một ứng dụng. Tên bảng/trường dưới đây là **mô hình khái niệm**, không phải schema Junsky hoặc mapping đã xác minh. Đối chiếu triển khai M1 lịch sử tại §10 và phần M2–M6 bổ sung bên dưới. A09 thêm lớp tiếp nhận raw trước adapter; không thay khóa nghiệp vụ, kiểu tiền và trạng thái chứng từ đã chốt.

## Phiếu tiếp nhận qua giao diện — A09

File gốc nằm ở `var/web/ho-so-goc/raw/<sha256>.bin`, phiếu JSON ở `receipts/<id>.json`. Đây là danh mục raw trước chuẩn hóa, không phải cơ sở dữ liệu kế toán thứ hai. Không cần migration SQLite mới. Bản gốc được tải lại theo tên trên phiếu; ZIP chưa giải nén, PDF/Excel/XML chưa được đọc nghiệp vụ.

| Trường | Kiểu và kiểm tra | Ý nghĩa |
|---|---|---|
| `format` | TEXT cố định `ktt-local-intake-v1` | Phiên bản phiếu |
| `id` | TEXT SHA-256, 64 hex | Hash JSON chuẩn `[entity, period, source, sha256]`, mã receipt |
| `sha256`, `bytes` | TEXT 64 hex; INTEGER từ 1 đến 52.428.800 | Nhận dạng nguyên byte; kiểm tra hash/kích thước khi tải lại hoặc xác nhận trùng |
| `name` | TEXT NFC ≤240 ký tự; không chứa đường dẫn/control char | Tên tệp khi tiếp nhận đầu tiên; whitelist pdf/xlsx/xls/xml/csv/tsv/json/txt/zip |
| `source` | ENUM sao_ke/hoa_don_xml/hoa_don_bang_ke/base/junsky_xuat | Nhóm do người nhập chọn, chưa xác minh cấu trúc nguồn |
| `entity` | TEXT không rỗng ≤80 ký tự | Nhãn pháp nhân do người nhập, chưa ánh xạ mã/MST Junsky |
| `period` | TEXT `YYYY-MM`, tháng hợp lệ | Nhãn kỳ hồ sơ, không thay ngày nghiệp vụ hoặc `as_of` |
| `note`, `original_relative_path` | TEXT ≤2.000 / ≤2.048 ký tự | Ghi chú, tên đường dẫn tương đối khi chọn thư mục; không dùng làm đường dẫn ghi trên server |
| `received_at` | ISO UTC do ứng dụng sinh, hiển thị giờ Việt Nam | Lúc nhận tệp trên máy, không chứng minh thời điểm biết nghiệp vụ |
| `client_modified_at` | INTEGER milliseconds ≥0 hoặc null | Metadata do trình duyệt cung cấp; không dùng làm `known_at` |
| `state`, `normalized`, `posted` | `RECEIVED_WAITING_ADAPTER`, false, false | Không đi qua đề xuất/duyệt/xuất/xác minh/nhãn học |
| `known_at`, `known_at_basis` | null | Chờ bằng chứng nguồn; không tự suy từ kỳ, ngày sửa hay ngày nhận |

File cùng byte trong cùng pháp nhân/kỳ/nguồn tạo một receipt, kể cả đổi tên; giữ tên và ghi chú của lần nhận đầu. File cùng tên nhưng khác byte được giữ riêng. Khác phạm vi tạo receipt khác, có thể dùng chung raw blob. Đây là chống trùng **hồ sơ đầu vào**, chưa thay khóa chống trùng giao dịch của D04. Trùng do xuất chồng kỳ hoặc đổi layout vẫn cần adapter.

Raw được ghi bất biến trước, phiếu được công bố atomic sau. Lỗi trước khi ghi phiếu không báo thành công; có thể thử lại. Phiếu hỏng được đếm và cảnh báo; tải raw bị đổi hash bị chặn. Không nhận trường metadata ngoài contract; JSON khai báo `synthetic=true` phải vào khu mô phỏng. Backup SQLite hiện hữu không bao gồm kho raw này; sao lưu trọn `ho-so-goc` khi đã dừng ứng dụng.

Các lựa chọn khác bản 1.2 đã được Anh chấp thuận về phương án D01–D10 theo A07 ở [QUYET-DINH.md](QUYET-DINH.md). “Bắt buộc” là bất biến của thiết kế; không có nghĩa đã kiểm chứng nguồn thật hoặc đã triển khai toàn bộ hợp đồng. Tham chiếu phạm vi: bản 1.2 §3–§5 và kế hoạch module §4.

## 1. Quy ước kiểu dữ liệu và kiểm tra chung

| Nhóm | Kiểu lưu đề xuất | Ràng buộc |
|---|---|---|
| ID nội bộ | SQLite TEXT, định danh sinh offline, bất biến | PK/UNIQUE; ID kỹ thuật không thay khóa chống trùng nghiệp vụ; không lấy mã Junsky giả làm ID nội bộ |
| Mã pháp nhân, MST, số HĐ, ký hiệu, mã TK, tài khoản NH, mã đối tượng/dự án/khoản mục | TEXT | Giữ số 0 đầu và raw; không float, không ép số trong Excel; trim/chuẩn hóa theo loại trường có phiên bản |
| Tiền | INTEGER 64-bit theo đơn vị nhỏ nhất đã duyệt; `currency` TEXT và `scale` INTEGER theo chính sách tiền tệ | Tính/parse bằng Decimal; phát hiện overflow/số lẻ vượt scale; không làm tròn hoặc đổi ngoại tệ ngầm; không cộng khác tiền tệ |
| Tỷ lệ/điểm chưa quy định scale | TEXT thập phân chuẩn, xử lý bằng Decimal | Phạm vi/đơn vị phải khai báo; điểm xếp hạng không phải xác suất đúng |
| Ngày nghiệp vụ/hiệu lực | TEXT ISO `YYYY-MM-DD` nếu nguồn chỉ có ngày | Không tự biến thành giờ giao dịch; phân biệt ngày hạch toán và ngày ngân hàng khi nguồn có cả hai |
| Thời điểm | TEXT ISO 8601 UTC, kèm giá trị gốc, múi giờ/offset và độ chính xác nguồn | Hiển thị giờ Việt Nam; giữ nguồn chỉ có ngày ở độ chính xác ngày, không gán giờ giả để chứng minh thứ tự |
| Boolean | INTEGER 0/1 | CHECK; không dùng chuỗi tùy ý |
| Trạng thái/loại | TEXT theo tập giá trị contract | Trạng thái lạ từ nguồn giữ raw và báo cần mapping; không tự ánh xạ thành hợp lệ |
| Version | INTEGER dương hoặc TEXT phiên bản được quản trị tùy đối tượng | Chốt nhất quán cho từng bảng; lưu quan hệ `supersedes_id`, không ghi đè lịch sử |
| Hash | TEXT SHA-256 | Hash bytes dùng kiểm tra file; content fingerprint có version chuẩn hóa; hash không chứng minh thời điểm/độ mới |
| Bằng chứng mở rộng | TEXT JSON và liên kết đến dòng nguồn | JSON hợp lệ, có version; tiền/khóa/trạng thái cốt lõi dùng trường rõ, không chỉ giấu trong JSON |
| Trường thiếu | NULL + mã lý do thiếu/chưa xác minh | NULL không bằng số 0 hoặc chuỗi rỗng; khóa UNIQUE không dựa vào cột nullable để vô tình lọt trùng |

`PLHN` là tên pilot theo yêu cầu. Mã pháp nhân và MST chính thức dùng với Junsky phải được kế toán xác nhận, không tự suy từ chữ PLHN.

Một quy trình chuẩn hóa văn bản dùng chung: Đ/đ → D/d → NFD → bỏ dấu → viết hoa → gộp khoảng trắng, đồng thời giữ bản gốc. Chuẩn hóa tên phục vụ tìm ứng viên, không chứng minh hai đối tượng là một. Chuẩn hóa MST/số TK/số HĐ theo quy tắc riêng được xác nhận; không xóa ký tự có ý nghĩa chỉ vì chuẩn hóa tên cho phép.

Tiền/dấu trình kế toán trưởng tại C03:

- Sao kê đứng từ phía tài khoản ngân hàng của PLHN: thu là dương, chi là âm; giữ cột Nợ/Có hoặc thu/chi nguyên bản và quy tắc adapter.
- Dòng sổ lưu `debit_minor >= 0`, `credit_minor >= 0`, cùng mã TK; số dư chuẩn có dấu `balance_dc_minor = Nợ - Có`. Không tự suy tiền sao kê từ chữ “Nợ” vì cách thể hiện của ngân hàng có thể khác sổ kế toán.
- Công nợ 131 dư Nợ và 331 dư Có không dùng chung công thức “trừ số đã trả” trên số dư có dấu. Tác động kỳ vọng vào mỗi TK/công nợ = tổng Nợ phân bổ - tổng Có phân bổ của bút toán được duyệt và đưa vào batch. Ví dụ kiểm tra số học: số dư +100, tác động Có 40 → +60; số dư -100, tác động Nợ 40 → -60. Đây là ví dụ dấu, không phải mẫu định khoản đã duyệt.
- Tạm ứng/dư ngược chiều, hoàn/đảo/cấn trừ/thanh toán hộ cần phân loại và chính sách riêng. Không lấy trị tuyệt đối để che chiều công nợ; thiếu chính sách thì giữ ngoại lệ, không tự phân bổ.

Mọi FK được kiểm tra; dữ liệu nguồn không bị sửa/xóa. Staging tách dữ liệu đã chấp nhận. Promote một đơn vị nhập trong transaction: có lỗi chặn thì không đưa một phần đơn vị đó vào dữ liệu chuẩn. Đơn vị mặc định là một file; bộ nhiều file phụ thuộc nhau có manifest nhóm và chỉ dùng được khi nhóm hoàn chỉnh. Nhật ký lỗi vẫn được lưu dù transaction promote rollback.

Bộ backup phải khôi phục được cả DB và bằng chứng mà DB tham chiếu: manifest, raw, cấu hình/schema version và các workbook/batch liên quan đã tồn tại. Lập danh sách artifact/checksum tại mốc backup; sao lưu SQLite nhất quán theo D07 rồi bảo đảm đủ artifact bất biến của mốc đó. Chỉ khôi phục DB nhưng mất nguồn hoặc file xuất không được coi là restore thành công. Chính sách giữ bản sao/địa điểm nội bộ cụ thể do IT thống nhất khi làm M1; không tự sao chép dữ liệu ra dịch vụ ngoài.

## 2. Nhập nguồn, raw và provenance — M1

| Thực thể | Trường tối thiểu | Khóa và kiểm tra |
|---|---|---|
| `entity` | `entity_id`, mã nghiệp vụ nội bộ, mã pháp nhân nguồn, tên, MST, hiệu lực | Một PLHN ở pilot; ánh xạ mã nguồn phải xác nhận |
| `source_artifact` | `artifact_id`, `entity_id`, `source_system`, đường dẫn raw nội bộ, tên file gốc, SHA-256, kích thước, loại nội dung, `received_at` | Bytes bất biến, không cho tên đường dẫn thay cho nhận dạng; file được đổi tên không thành nội dung mới |
| `ingestion_attempt` | ID lần nạp, `artifact_id`, `parser_version`, `schema_version`, `config_version`, `loaded_at`, trạng thái, số bản ghi đọc/chấp nhận/trùng/lỗi | Tách lần chạy khỏi thực thể nguồn; retry có audit, không tăng thực thể/tiền |
| `source_manifest` | ID gói, pháp nhân, hệ nguồn, loại báo cáo, kỳ, `as_of`, `exported_at`, độ chính xác/múi giờ, `known_at`, bằng chứng known_at, phạm vi bao phủ, người xuất/xác nhận nếu có, version danh mục | Đủ năm nhóm nghiệp vụ và thành phần bổ sung đã duyệt; tương thích pháp nhân/thời điểm; trường nguồn không có được khai báo thiếu |
| `manifest_component` | ID gói, vai trò dữ liệu, artifact/sheet, bộ lọc, `coverage_from`, `coverage_to_exclusive`, tổng kiểm soát/số dòng nguồn, trạng thái kiểm tra | Một vai trò có thể nhiều file/sheet; không giả định luôn có năm file vật lý |
| `source_record` | ID dòng nguồn, artifact, sheet/trang/row hoặc đường dẫn XML/JSON, ordinal, raw text/payload, raw hash, `known_at` và chất lượng thời điểm | Locator chỉ xác định vị trí bằng chứng trong artifact; không mặc nhiên là ID nghiệp vụ xuyên lần xuất |
| `document` | `document_id`, pháp nhân, hệ nguồn, loại, ID/khóa nguồn, ngày nghiệp vụ/hạch toán nếu có, tiền tệ, trạng thái nguồn, version, supersedes | Header chứng từ; tổng header không cộng cùng tổng detail như hai giao dịch |
| `document_line` | `line_id`, document, ID dòng nguồn, thứ tự, giá trị/tiền/đơn vị theo loại, version | Detail có quan hệ cha–con; số dòng khác số giao dịch được đánh giá |
| `record_provenance` | ID thực thể/version/field, source_record, phương pháp/transform version, thời điểm | Nhiều nguồn có thể chứng minh một trường; chọn nguồn theo chính sách, mâu thuẫn phải lưu |
| `validation_issue` | ID lỗi, lần nạp, file/dòng/trường, severity, mã lỗi, giá trị kỳ vọng/thực tế, trạng thái/người xử lý | Phân biệt lỗi chặn, cảnh báo, nghi trùng; không im lặng bỏ dòng |
| `audit_event` | ID, thời điểm, người/tiến trình, hành động, đối tượng/version, giá trị trước/sau hoặc liên kết version, lý do, correlation ID | Append-only theo logic ứng dụng; không tuyên bố chống sửa bởi người quản trị hệ điều hành |

Một file không đổi có thể được dùng làm bằng chứng cho nhiều lần xuất/phiên đã được xác nhận. Lưu riêng manifest mỗi lần sử dụng; không nhân đôi giao dịch nền. Khi snapshot mới cùng nội dung, vẫn ghi quan sát snapshot với as-of và bằng chứng lần xuất hợp lệ. Việc chống trùng file không được làm mất lịch sử “dữ liệu nào dùng ở phiên nào”.

Trạng thái lần nạp đề xuất: `RECEIVED → STAGED → VALIDATED → COMMITTED`, hoặc `REJECTED`; `COMMITTED` chỉ có nghĩa nhập nguồn thành công, không phải ghi sổ Junsky. Mỗi báo cáo nêu số dòng nguồn thực có, dòng dùng/dòng loại và lý do, tổng theo tiền tệ/phạm vi. Số lượng fixture không được gắn nhãn số liệu khảo sát.

## 3. Cấu trúc nghiệp vụ nguồn và khóa chống trùng — M1

### 3.1 Các bảng chuyên biệt

| Thực thể | Trường khái niệm tối thiểu | Kiểm tra |
|---|---|---|
| `bank_statement` | document, mã ngân hàng, tài khoản của PLHN, tiền tệ, kỳ sao kê, số đầu/cuối, tổng thu/chi nếu có | Phạm vi không đứt đoạn ngoài phần đã khai báo; đầu + thu - chi = cuối; running balance nếu nguồn có |
| `bank_transaction` | line/document nội bộ, tài khoản, mã giao dịch/tham chiếu nguồn nếu có, booking date, value date nếu có, số tiền có dấu, currency, diễn giải gốc, thông tin đối tác, số dư sau dòng nếu có | Mã tham chiếu chưa được kiểm chứng duy nhất; lưu cả ngày giờ gốc; cùng ngày/tiền không tự gộp |
| `invoice` | document, MST bán, MST mua, ký hiệu, số HĐ, mẫu/loại khi cần, ngày HĐ, tiền tệ, tổng trước thuế/thuế/thanh toán khi có, trạng thái nguồn, quan hệ điều chỉnh/thay thế | Khóa HĐ tách khỏi file; XML và bảng kê là hai bằng chứng của một thực thể nếu định danh khớp chắc |
| `invoice_line` | line, invoice, mã/tên hàng, đơn vị/số lượng/đơn giá dạng thập phân, tiền trước thuế/thuế/tổng, nguồn | Bảng kê chỉ có header không được sinh detail giả; không thay line XML bằng tổng header; quy tắc tổng theo layout đã xác nhận |
| `base_request` | document, Base request ID, ngày/trạng thái, người/đối tượng liên quan nếu có, tiền/currency, `du_an`/`chi_phi` gốc nếu có, JSON đã giải mã, attachment references | Quét thư mục và so chỉ mục; base64 lỗi phải báo; dự án/chi phí còn cần ánh xạ danh mục đã duyệt |
| `journal_document` | document, ID nguồn nếu có, sổ/năm tài chính/loại/số chứng từ, ngày hạch toán, trạng thái đảo/hủy | Số chứng từ đơn lẻ không duy nhất |
| `journal_line` | ID nội bộ, journal document, ID dòng ổn định nếu có, mã TK, Nợ/Có, currency, đối tượng, HĐ/open item, dự án/khoản mục, bank reference, batch reference nếu có, quan hệ đảo/hủy | Contract dạng dòng TK; Junsky có thể xuất TK Nợ/Có trên cùng dòng, chỉ chuyển sau khi xác nhận. Cân chứng từ chỉ khi nguồn bao phủ đầy đủ hai phía, không báo cân giả trên sổ lọc riêng 112 |

### 3.2 Khóa và xử lý nhập trùng

| Đối tượng | Khóa đề xuất | Khi thiếu hoặc xung đột |
|---|---|---|
| Nội dung file | SHA-256 bytes + phạm vi bảo quản; kiểm tra pháp nhân/hệ nguồn khi dùng | Trùng file chỉ bỏ việc nhập lặp thực thể, vẫn ghi lần nạp/manifest. File khác hash vẫn có thể chứa giao dịch cũ |
| Sao kê có ID nguồn ổn định | `(entity, ngân hàng, tài khoản, namespace ID, ID giao dịch nguồn)` sau khi kiểm chứng; ngày/tiền/currency là trường kiểm tra consistency | Cùng ID nhưng khác tiền/ngày phải cách ly thay vì ghi đè; ID có thể cần thêm kỳ/năm nếu nhà băng tái dùng |
| Sao kê chưa chứng minh ID ổn định | Ứng viên từ `(entity, ngân hàng, tài khoản, tham chiếu, ngày, currency, tiền có dấu)` và bằng chứng trang/số dư/trình tự | Không coi tổ hợp này luôn duy nhất. Hai giao dịch thật cùng ngày/tiền có ID khác được giữ cả hai. Thiếu tham chiếu hoặc collision giữ bản nguồn riêng và chờ người xác minh; không tự thêm hậu tố để lách trùng |
| Hóa đơn | `(entity, MST người bán, ký hiệu, số HĐ, namespace mẫu/loại khi nguồn yêu cầu)` | Không chỉ dùng số HĐ; không đổi khóa do trạng thái/tiền thay đổi. XML–bảng kê khớp khóa nhưng khác header thì một thực thể có mâu thuẫn bằng chứng, chưa chọn dữ liệu hiệu lực. Quan hệ HĐ thay thế không gộp HĐ mới vào HĐ cũ |
| Base | `(entity, hệ/tenant Base, request_id)` | Bản sửa là revision. Thiếu ID đưa chờ; hash nội dung giống không chứng minh cùng đề nghị |
| Chứng từ sổ | ID Junsky ổn định trong phạm vi đã xác minh; nếu không có thì `(entity, hệ nguồn, sổ, năm tài chính, loại chứng từ, số chứng từ)` | Giữ nguyên phần khóa chưa biết; nếu tổ hợp còn trùng thì cần thông tin phân biệt, không tự nhận là duy nhất |
| Dòng sổ | ID dòng nguồn ổn định + namespace; hoặc khóa chứng từ + line ID ổn định do nguồn cấp | Ordinal chỉ dùng làm provenance nếu lần xuất có thể đổi thứ tự. Nội dung giống nhau không đủ để gộp các dòng hạch toán hợp lệ |
| Snapshot công nợ | `(snapshot_id, open_item_id)`; open item có định danh ổn định theo §4 | Snapshot mới không tạo “hóa đơn mới” chỉ vì số dư thay đổi |
| Danh mục | `(entity, loại danh mục, mã Junsky, version)` | MST/tên không phải mã quản trị; kiểm tra trùng/hiệu lực chồng/mã dùng lại |
| Phân bổ/quyết định/batch/nhãn | ID nội bộ + khóa idempotency nghiệp vụ theo §6–§7 | Retry giữ ID, không sinh ID mới để tránh xung đột; thay thế có quan hệ version |

Không có cơ sở bảo đảm chống trùng xuyên file khi nguồn không có định danh hoặc bằng chứng đủ phân biệt. Mục tiêu là **chặn xử lý tiếp phần mơ hồ**, không tuyên bố giải quyết bằng thuật toán suy đoán. Khóa nghiệp vụ có trường thiếu phải được đánh giá trước khi UNIQUE; không dựa vào hành vi NULL của SQLite. Có thể lưu composite key chuẩn dạng có version; không nối chuỗi tùy tiện gây collision dấu phân cách.

## 4. Hợp đồng gói Junsky và snapshot

### 4.1 Năm nhóm bắt buộc theo bản 1.2 và bằng chứng bổ sung

| Nhóm nghiệp vụ | Trường khái niệm cần xác nhận từ mẫu | Quy tắc kiểm tra |
|---|---|---|
| Công nợ 131/331 theo HĐ | Pháp nhân, as-of, TK chi tiết, mã đối tượng, ID khoản công nợ/HĐ đủ phân biệt, ngày HĐ, currency, số dư Nợ/Có/còn mở; phát sinh/đã trả nếu có | Tổng theo TK/đối tượng/currency; item tạm ứng/không HĐ tách rõ; báo phần thiếu. Phải biết báo cáo là open-only hay toàn bộ: HĐ biến mất không tự có nghĩa bằng 0 nếu phạm vi lọc thay đổi |
| Danh mục đối tượng | Mã nội bộ, tên, MST, số TK/ngân hàng nếu có, trạng thái, hiệu lực nếu có | Định danh mâu thuẫn/chưa xác minh không tự chọn; các mã mới/đổi tên/MST được so và chờ duyệt |
| Hệ thống tài khoản | Mã/tên TK, cha/cấp, trạng thái/hiệu lực, mốc và bảng cũ–mới nếu đổi | TK theo kỳ; thiếu nguồn hiệu lực phải xác nhận, không tự đặt mốc 2026 |
| Khoản mục phí và dự án | Mã/tên, loại danh mục, trạng thái/hiệu lực | Không tạo đủ “28 mã” bằng phỏng đoán; giữ nhóm chưa mapping ở trạng thái thiếu |
| Kỳ khóa | Pháp nhân, khoảng ngày, trạng thái và phạm vi khóa | Kiểm tra ngày hạch toán; chuyển sang [từ, đến) nhưng giữ ranh giới gốc nguồn |
| **Bổ sung D03** — sổ 112/NKC hoặc danh sách bút toán | ID chứng từ/dòng, ngày hạch toán, TK, Nợ/Có hoặc cấu trúc nguồn, tiền/currency, đối tượng, HĐ, dự án/khoản mục, tham chiếu NH/batch nếu có, hủy/đảo | Phạm vi từ snapshot trước đến snapshot hiện tại đủ để giải thích biến động, gồm bút toán tay/điều chỉnh/đảo. Trường không có thì không xác minh trường đó |

### 4.2 Snapshot và item

| Thực thể | Trường tối thiểu | Khóa/bất biến |
|---|---|---|
| `snapshot` | ID, entity, manifest, as_of + precision, coverage/filter, source totals, currency totals, trạng thái valid/incomplete/rejected | Bất biến sau chấp nhận; sửa bằng snapshot mới có liên kết thay thế; không chồng sửa số gốc |
| `open_item` | ID, entity, TK công nợ, mã đối tượng, currency, `item_type`, nguồn ID khoản công nợ, invoice ID nếu có, phân biệt đợt/khoản khi cần | Ưu tiên ID khoản công nợ Junsky ổn định; fallback khóa tổng hợp có đủ TK/đối tượng/currency/HĐ hoặc tham chiếu khoản riêng. HĐ đơn lẻ có thể không đủ |
| `open_item_balance` | snapshot, open_item, số dư Nợ/Có gốc, `balance_dc_minor`, phát sinh/đã thanh toán nếu có, provenance | UNIQUE snapshot + item; cùng item nhiều dòng nguồn phải có quy tắc cộng được xác nhận, không cộng tự động khi không biết do trùng hay phân đoạn |
| `catalog_snapshot` | snapshot/version danh mục, entity, loại/mã, giá trị, hiệu lực/known_at, trạng thái duyệt | Không tự có hiệu lực vì xuất hiện trong file mới |

Khoản không có HĐ có item riêng với tham chiếu được kiểm chứng; không dùng HĐ rỗng chung cho tất cả tạm ứng. Nếu báo cáo chỉ có tổng đối tượng, không tự dựng open item theo HĐ; đây là hạn chế phải đưa Anh quyết định.

Snapshot đầu phiên làm mốc công nợ hiện tại. Phân bổ **các phiên cũ đã phản ánh trong snapshot không bị cộng lại**. Giữ lịch sử phân bổ/batch để kiểm tra đã ghi sổ và các batch còn chờ; nếu batch cũ chưa xác minh, mục liên quan chưa được tự do phân bổ lại chỉ vì phiên cũ đã chốt.

## 5. Quy tắc thời gian và tri thức có hiệu lực

| Trường | Ý nghĩa | Không được thay bằng |
|---|---|---|
| `business_date` / `posting_date` / `value_date` | Ngày nghiệp vụ, hạch toán, giá trị ngân hàng theo nguồn | Ngày nhập hoặc ngày xuất |
| `as_of` | Dữ liệu phản ánh đến thời điểm/ngày nào, kèm độ chính xác và phạm vi | Hash hay exported_at |
| `exported_at` | Lúc hệ nguồn tạo báo cáo/file nếu có bằng chứng | Ngày sửa file của hệ điều hành một cách mặc định |
| `received_at` / `loaded_at` | Lúc hệ thống nhận/nhập dữ liệu hiện tại | Thời điểm thông tin đã có trong lịch sử |
| `known_at` | Lúc thông tin cụ thể có thể được biết, kèm căn cứ và chất lượng | business_date hoặc as_of theo suy đoán |
| `valid_from`, `valid_to` | Khoảng hiệu lực nghiệp vụ [từ, đến), đến NULL nghĩa không có mốc hết đã biết | Khoảng tồn tại của file |
| `approved_at`, `verified_at`, `eligible_at` | Lúc được duyệt, xác minh và đủ điều kiện học | Ngày chứng từ; không lùi thời điểm duyệt vì sửa chính sách hồi tố |

Quy tắc sử dụng:

1. Cổng vào giữ yêu cầu bản 1.2: as_of bao phủ ngày cuối dữ liệu xử lý, gói cùng pháp nhân, danh mục được xác nhận, phiên trước đã chốt. D02 bổ sung kiểm tra metadata/phạm vi thay vì chỉ hash. D06 tách kiểm tra “đã ghi sổ” vì snapshot đủ mới có thể chứa chính giao dịch đang đề xuất.
2. Với danh mục ít đổi, bản nội dung cũ chỉ được tái dùng khi manifest phiên mới xác nhận đúng version đang dùng và đủ bằng chứng về phạm vi; không dựng known_at mới để xóa lịch sử.
3. Truy vấn tại cutoff chỉ dùng version đã biết vào cutoff, đã duyệt khi yêu cầu, có hiệu lực tại ngày nghiệp vụ. Sửa hồi tố vẫn giữ lúc thực sự biết/duyệt; không để backtest trước đó thấy bản sửa tương lai.
4. Nhãn đưa vào thống kê chỉ nếu eligible_at không sau cutoff; liên kết xác minh lập sau cutoff không được dùng làm feature cho đề xuất ở trước cutoff. Đáp án tương lai chỉ dùng ở bước chấm tách riêng.
5. Thiếu bằng chứng known_at: ghi NULL/UNKNOWN và lý do. Nếu dùng giả định, lưu riêng loại giả định và báo cáo backtest hồi cứu; không gắn nhãn point-in-time đã chứng minh. Không tự backdate từ sổ hoặc tên file.
6. Hiệu lực cùng khóa không chồng nhau trong tập version cùng có hiệu lực ở một thời điểm biết; xung đột đưa chờ duyệt. Thay đổi TK/chính sách đã khai báo tạo phân vùng cứng; giảm trọng số mềm chỉ trong vùng được phép.
7. Cấm trộn múi giờ hoặc độ chính xác. Nguồn chỉ có ngày nhưng quyết định cần thứ tự trong ngày: đánh dấu không đủ bằng chứng, dùng cutoff ngày theo quy ước được duyệt hoặc loại khỏi kiểm chứng nghiêm ngặt.

### Năm nhóm tri thức — M2; M5 cập nhật phần dẫn xuất

| Nhóm | Cấu trúc đề xuất | Trường/kiểm tra quan trọng |
|---|---|---|
| Danh mục và định danh | `counterparty`, `identifier`, catalog account/project/expense | Khóa quản trị mã Junsky; định danh MST/TK/bí danh/biển số/số HĐ có nguồn, mức xác minh, version/hiệu lực/known_at; không coi một định danh mơ hồ là khóa cứng |
| Chính sách/ràng buộc/mẫu | `accounting_template`, `constraint`, `account_mapping` | Slot bắt buộc, điều kiện/mẫu đảo, phạm vi, người duyệt, bằng chứng; mọi ngưỡng cấu hình được duyệt; chưa tự điền mẫu kế toán |
| Bộ nhớ tình huống | `historical_link`, `case_group` | Liên kết nguồn–bút toán, evidence, phương pháp/version, LINK_A/B/C, thời điểm, người kiểm; các ngưỡng phân loại A/B/C cần duyệt |
| Thống kê dẫn xuất | view hoặc dữ liệu tái tạo có lineage từ `learning_label` | Không chỉnh bộ đếm như dữ liệu gốc; lưu cutoff/phiên bản công thức/tập nhãn để tái lập; đếm cả số lượng và giá trị |
| Quy tắc và nhật ký | `keyword_rule`, `rule_candidate`, `decision_log`, `exception` | Người duyệt thắng máy; đề cử có báo cáo tác động, không tự kích hoạt; ba chỉ số từ khóa/bảy mã lý do chưa có định nghĩa thì để chờ |

`LINK_A/B/C` là mức bằng chứng liên kết lịch sử; không phải `RECON_A/B/C` là loại chênh đối soát. Không dùng score để thay mức người kiểm; nếu nhiều ứng viên cùng mạnh thì không ép một ứng viên thành A.

## 6. Phiên, đề xuất, phân bổ, duyệt và xuất — M3/M4

| Thực thể | Trường chính | Bất biến |
|---|---|---|
| `processing_session` | ID, entity, snapshot/gói nguồn, cutoff, version tri thức/config, opened_at/by, closed_at/by, trạng thái, các control totals | Một phiên xử lý mở tại một thời điểm ở pilot; thao tác giữ chỗ/kiểm tra tiền trong transaction. Đóng phiên không có nghĩa batch đã nhập Junsky |
| `proposal` | ID, session, bank_transaction ID, revision, case_id, completeness FULL/PARTIAL/NONE, trạng thái, version tri thức/thuật toán, created_at | Một revision hiện hành cho giao dịch trong phiên; sửa tạo revision; giữ nguyên bản máy để đo thiên lệch |
| `proposal_field` | proposal revision, tên trường, giá trị đề xuất, mức/điểm tin cậy, evidence, kết quả ràng buộc | Mỗi trường tách; thiếu đối tượng chịu chi phí không suy từ hóa đơn; ràng buộc thắng điểm |
| `allocation` | ID, revision, session, bank_transaction, open_item, amount_minor dương, currency, tác động Nợ/Có dự kiến, trạng thái, decision/batch refs, supersedes | Quan hệ M:N; tổng hiệu lực không vượt tiền còn của giao dịch và khoản công nợ theo chiều hợp lệ |
| `review_decision` | ID, session/proposal revision, người/thời điểm, chấp nhận/sửa/từ chối, trường trước/sau, mã lý do hoặc trạng thái chưa có danh mục lý do, evidence | Bản duyệt cuối mới có thể xuất; sửa phải kiểm lại ràng buộc. Danh mục bảy mã nguyên bản còn chờ, không tự điền bảy mã giả |
| `export_batch` | ID, session, mapping version, decision revisions, manifest, file paths/checksums, control totals, trạng thái, created/exported_at, recovery info | Nội dung batch bất biến; retry kỹ thuật không tạo giao dịch mới. Chỉ bản duyệt cuối đủ trường, đúng kỳ, cân Nợ/Có và đạt mapping mới vào batch |
| `export_item` | ID batch/item, bank_transaction, decision revision, allocation refs, ID nghiệp vụ ổn định, Junsky IDs nếu đã xác nhận nguồn/quy tắc | Theo dõi từng item khi import một phần; không chỉ cờ “cả file thành công” |
| `expected_balance` | session, snapshot gốc, open_item, balance_before, movement_in_batch, balance_expected, batch refs | Kỳ vọng có dấu = số dư đầu + tác động Nợ - Có thuộc batch. Phần chỉ giữ chỗ/chờ duyệt không vào kỳ vọng đã xuất |

Khóa chống lặp xuất được kiểm tra xuyên phiên theo bank_transaction/decision revision và phần phân bổ: khoản đã xuất hoặc đang chờ xác minh không được tạo batch mới tương đương. Retry giữ cùng batch/item IDs. Nếu xuất sửa, có quan hệ thay thế và xác minh trạng thái batch cũ; không chỉ tăng revision để vượt khóa. Một giao dịch tách nhiều bút toán vẫn có một anchor để không đếm lại giá trị giao dịch.

Giữ chỗ và phân bổ: `RESERVED → APPROVED → EXPORTED_PENDING → POSTED_VERIFIED`, hoặc `CANCELLED/SUPERSEDED` theo điều kiện. Các trạng thái là các giai đoạn của cùng allocation, **không cộng tiền giữ chỗ + tiền đã duyệt + tiền đã ghi sổ ba lần**. Hủy đề xuất chưa xuất có thể giải phóng; batch đã xuất chưa rõ import thì chưa giải phóng để tái xuất. Mẫu chi phí NH trực tiếp không bị ép qua công nợ; cần mẫu kế toán được duyệt.

### Chuỗi trạng thái đề xuất → duyệt → xuất → xác minh → nhãn

| Chuyển trạng thái | Điều kiện và chứng cứ | Không được suy ra |
|---|---|---|
| Nguồn hợp lệ → `PROPOSED` | Qua cổng vào/ràng buộc; đề xuất có version/bằng chứng; có thể đầy đủ, một phần hoặc không có đề xuất | “Có đề xuất” không có nghĩa đủ để xuất |
| `PROPOSED → APPROVED_FINAL` | Người có quyền duyệt đúng revision, đủ trường, ràng buộc chạy lại; lưu mọi sửa và lý do | Người bấm duyệt không chứng minh đúng so với sổ |
| `APPROVED_FINAL → EXPORTED` | File hoàn chỉnh, được kiểm tra theo mapping đã duyệt, manifest/checksum và trạng thái DB nhất quán sau recovery | Ghi file không có nghĩa đã import hoặc ghi sổ |
| `EXPORTED → PARTIALLY_VERIFIED` | Chỉ một số item hoặc trường có chứng cứ nguồn sổ độc lập; lưu mask trường được xác minh | Không nâng toàn bộ batch/chứng từ thành đã ghi sổ |
| `EXPORTED/PARTIALLY_VERIFIED → POSTED_VERIFIED` | Xác định được bút toán tương ứng và trường bắt buộc đúng theo chuẩn D01 đã duyệt | Tổng số dư bằng nhau chưa đủ |
| `POSTED_VERIFIED → RECONCILED` | Đối soát khoản/tiền/phạm vi với snapshot và bút toán; sai khác liên quan đã xử lý, không che bằng bù chênh | Đối soát một phiên chưa tự cho phép khóa tháng |
| Xác minh hợp lệ → nhãn `ELIGIBLE` | Đạt điều kiện §7 cho từng trường và ngày eligible_at; không bị thu hồi/thay thế | Duyệt cuối hoặc đã xuất không đủ làm nhãn |

Quyết định bị từ chối, hủy hoặc thay thế giữ lịch sử; không “quay lùi” bản cũ bằng sửa trực tiếp. Nếu đã ghi sổ thì cần quy trình điều chỉnh/đảo có chứng từ được xác minh, không xóa giao dịch để tạo cảm giác chưa từng xuất.

Excel duyệt mang session_id/proposal_id/revision và trường khóa cần đối chiếu với DB; file cũ/sai phiên/sửa ID bị từ chối; nhập quyết định theo transaction. Checksum không phải cơ chế xác thực người dùng. Người duyệt được nhận diện theo quy trình nội bộ cần chốt; không tự khẳng định chữ ký số hoặc hệ phân quyền chưa xây.

Batch xuất có bước chuẩn bị → file tạm được kiểm tra → hoàn tất artifact/manifest → hoàn tất trạng thái DB có thể phục hồi. Thiết kế chi tiết atomicity thuộc M4/D07; P0 chưa tạo file import. Không xem transaction SQLite là transaction chung với filesystem hay Junsky. Import một phần hoặc không rõ đã nhập phải đối chiếu từng item trước retry; không tự gửi lại cả file. Khóa local không ngăn kế toán import hai lần ở Junsky.

## 7. Đối soát, xác minh và nhãn học — M5

| Thực thể | Trường chính | Kiểm tra |
|---|---|---|
| `verification_run` | ID, session/batch refs, snapshot/sổ chứng cứ, thời điểm, phạm vi, người/phương pháp, version thuật toán | Có thể chạy sau khi chốt phiên, gồm lượt cuối tháng theo đề xuất D08; không cần mở thêm phiên đề xuất để xác minh |
| `reconciliation_item` | ID, expected item/batch, source actual refs, tiền kỳ vọng/thực tế/chênh, currency, trạng thái, RECON category nếu đủ bằng chứng, lý do/người xử lý | Đối chiếu từng item/HĐ; không để chênh +x và -x triệt tiêu; MATCHED hoặc UNRESOLVED là trạng thái, không phải nhóm chênh thứ tư |
| `field_verification` | ID, bank_transaction/decision revision, field, expected/observed value, evidence links, kết quả, phương pháp, verified_at/by | Trường không có trên chứng cứ giữ UNVERIFIED; không biến người chấp nhận đề xuất thành kiểm tra độc lập |
| `learning_label` | ID, entity, document/bank_transaction anchor, revision, giá trị từng trường, eligibility mask, value_minor/currency, evidence, status, eligible_at, supersedes/revoked_at | Mỗi chứng từ một revision nhãn hiệu lực tại một thời điểm; field đủ điều kiện mới được dùng; giữ lịch sử thay thế |
| `learning_run` | ID, cutoff, partition hiệu lực, tập nhãn/version/hash, công thức/version/config, thống kê và báo cáo tác động | Chạy lại cùng đầu vào tái lập, không cộng lặp; mọi view/materialization có thể tính lại |

Nhóm chênh chỉ kết luận sau khi có chứng cứ:

- `RECON_A`: phần mềm có khoản đã xuất/kỳ vọng nhưng Junsky không có khoản tương ứng; xác minh phạm vi báo cáo đủ trước khi kết luận chưa nhập. Giữ chờ xác minh/đã xuất; xử lý retry có kiểm soát.
- `RECON_B`: Junsky có nghiệp vụ mà phần mềm không có. Là ứng viên bổ sung, cần chứng từ/liên kết và kiểm tra độc lập; không tự học. Trong pilot chỉ tạo nhãn thuộc đối tượng sao kê và đủ liên kết.
- `RECON_C`: có ở hai bên nhưng khác số/phân bổ/HĐ/trường liên quan. Kế toán xử lý, thay thế version nhãn sau khi xác minh bản sửa.

Chênh chưa rõ nguyên nhân giữ `UNRESOLVED`, không ép A/B/C. Chênh số dư bằng 0 nhưng sai HĐ/TK/dự án vẫn có thể chưa xác minh đúng. Báo cáo phải tách kết quả khớp số dư với chứng cứ đúng từng trường.

Điều kiện nhãn đề xuất:

1. Nhãn nguồn vận hành: bản duyệt cuối và item xuất xác định được; bằng chứng ghi sổ/đối soát phù hợp; chỉ trường đã xác minh mới đủ điều kiện. Nếu phân bổ/tiền còn tranh chấp thì các trường phụ thuộc giữ chưa đủ điều kiện; không dùng một trường “có vẻ đúng” để vượt ràng buộc tiền.
2. Nhãn lịch sử hoặc bút toán ngoài phần mềm: có nguồn sổ, liên kết được kiểm chứng và người kiểm độc lập; không phải bịa trạng thái “đã xuất bởi phần mềm” để đi qua chuỗi. Cùng tuân thủ điều kiện bằng chứng và thời điểm.
3. Không đủ chỉ vì LINK_A, tỷ lệ chấp nhận, số dư giảm hoặc HĐ đóng. Nhãn chưa có bằng chứng là `CANDIDATE/PENDING_EVIDENCE`; đủ là `ELIGIBLE`; sai/đặc thù là `EXCEPTION`; bị thay/thu hồi là `SUPERSEDED/REVOKED`. Các tên này là trạng thái contract đề xuất, không thay bộ bảy mã lý do gốc chưa có.
4. Chỉ một nhãn hiệu lực cho document/bank_transaction; nhiều trường xác minh từng đợt tạo revision có mask, không tạo nhiều nhãn hiệu lực song song. Thu hồi/thay thế rồi tính lại thống kê, không trừ tay bộ đếm.
5. Thống kê lượng và tiền: mỗi giao dịch tính một lần cho mẫu số tổng giá trị tuyệt đối; khi tách allocation không nhân nguyên tiền sao kê lên từng dòng. Nếu thống kê theo item, dùng đúng tiền phân bổ và công bố mẫu số. Giữ riêng các tiền tệ, không cộng quy đổi khi chưa có chính sách.
6. Chỉ dùng nhãn đúng vùng hiệu lực và eligible_at không sau cutoff; đề cử quy tắc có tác động trên tập đánh giá được quản lý, người duyệt mới kích hoạt. Tập holdout và mẫu kiểm tra mù độc lập với dữ liệu dùng để điều chỉnh quy tắc.

Khóa tháng theo D08: sau import và lượt xác minh cuối, không còn chênh, batch chờ hoặc item chưa xác minh thuộc kỳ. Giữ nguyên điều kiện chênh = 0 của bản gốc; giải trình không thay số chênh. Kỳ có nghiệp vụ ngoài phạm vi pilot cần kế toán xác nhận đối soát sổ tổng thể, ứng dụng không tự tuyên bố toàn bộ Junsky đã khóa đúng.

## 8. Mapping Junsky còn chờ — không có tên cột nào được xác nhận

| Đầu vào/đầu ra | Cần xác nhận | Trạng thái hiện tại |
|---|---|---|
| File xuất năm nhóm | File/sheet/header, kiểu, đơn vị tiền/dấu, hàng tổng, header nhiều dòng, bộ lọc/thời điểm, cách biểu diễn open item và ID | Chưa có mẫu; chỉ có yêu cầu khái niệm ở §4 |
| Sổ 112/NKC/chứng từ | ID chứng từ/dòng ổn định; có trường gì; dòng Nợ/Có riêng hay cặp; full/sliced scope; hủy/đảo; bank/batch refs | Hướng D03 đã chấp thuận tại A07; chờ mẫu và xác nhận khả năng xuất |
| `CB_tmpEntry1` | Bộ cột, kiểu/độ dài, bắt buộc/null, header/detail, cách sinh/giữ EntryID, định dạng tiền/ngày/mã | Chưa có mẫu hoặc file thành công |
| `CB_tmpEntry2` | Bắt buộc khi nào, quan hệ Entry1, DebtID trỏ đến đâu/lấy ở đâu, chia nhiều HĐ/trả một phần, thứ tự dòng | Chưa có mẫu hoặc câu trả lời nhà cung cấp |
| Import/re-import | Cơ chế báo lỗi, có import một phần không, phát hiện trùng, EntryID khi retry/sửa, xuất lại bút toán để xác minh | Chưa kiểm chứng; không giả định Junsky có idempotency |

Mẫu mapping cần được điền sau khi có file: vai trò nguồn → file/sheet/cột hoặc đường dẫn → trường nội bộ → kiểu/đơn vị → biến đổi → bắt buộc/điều kiện → kiểm tra → người xác nhận/ngày/version → chứng cứ file thành công/lỗi. Hiện không có dòng mapping thật và không đặt trước cột bắt buộc của Junsky.

## 9. Bàn giao và kiểm chứng hợp đồng

Các test M1 T01–T15 và phân biệt fixture/mẫu thực ở [HIEN-TRANG.md](HIEN-TRANG.md) §6. Khi đổi contract cần ghi version, quyết định phê duyệt, ảnh hưởng dữ liệu/migration, thay đổi adapter và test hồi quy liên quan; không sửa raw lịch sử để phù hợp schema mới.

M1 bàn giao bằng chứng về tiền/chuỗi/khóa/truy nguồn/atomic ingest/tổng/restore. M2–M6 kiểm chứng phần hiệu lực, phân bổ, trạng thái, Excel/batch, xác minh/nhãn và cutoff đúng trách nhiệm. P0 chưa có code; sau A07 đã có schema và test fixture như §10. Vẫn **chưa có adapter thực được nghiệm thu, mapping Junsky được xác nhận hoặc nghiệm thu kế toán**.

## 10. Phần đã triển khai trong M1

| Khái niệm | Schema/code hiện tại | Phạm vi kiểm chứng |
|---|---|---|
| Pháp nhân/cấu hình | `workspace_meta`, `config_history` | Một entity fixture; TOML gốc được lưu/hash; từ chối runtime production |
| Raw/lần nạp/manifest | `artifacts`, `attempts`, `source_records`, `staging` | Raw content-addressed; manifest giữ cả giá trị gốc và timestamp chuẩn; file lỗi không promote một phần |
| Header/detail | `documents`, `document_lines` | Khóa riêng theo kind; invoice hợp nhất giữa hai nguồn; detail không bị cộng lại vào header |
| Truy nguồn và nhật ký | `evidence`, `issues`, `audit_events` | Bằng chứng theo header/dòng và known_at; lỗi có locator, audit có OS user/process. Đây không phải hệ xác thực người duyệt |
| Migration | `schema_migrations`, `PRAGMA user_version` | Hai migration, kiểm tra checksum/history, FK và rollback khi nâng schema lỗi |
| Snapshot/danh mục/sổ | Các kind OPEN_ITEM/COUNTERPARTY/ACCOUNT/EXPENSE/PROJECT/LOCK_PERIOD/JOURNAL trong `documents` | Chỉ chuẩn hóa từ contract fixture. Số dư từng snapshot tách trong báo cáo; chưa phải kho trạng thái hay danh mục đã được M2 duyệt |
| HĐ sửa/thay thế | `source_status`, `related_invoice_key` và raw/provenance | Giữ quan hệ được nguồn khai báo; cùng khóa đổi dữ liệu sẽ bị cách ly, chưa có thao tác duyệt revision hoặc hiệu ứng kế toán tự động |
| Mốc thời gian | Hàm ISO/UTC, khoảng [từ, đến), evidence known_at, truy vấn header có bằng chứng trước cutoff | Không tự điền known_at; chưa là engine backtest/tri thức hiệu lực của M2/M6 |

Adapter hiện có là **một adapter JSON giả lập có nhánh kiểm tra năm nhóm nguồn**; không phải năm parser thực. Quét Base nhận chỉ mục/item JSON fixture có payload base64; chưa nhận layout Excel/JSON Base thật. `check-bundle` kiểm tra đủ vai trò và metadata tương thích, chưa kiểm tra toàn bộ quan hệ danh mục, chưa chứng minh dữ liệu mới nhất, không mở phiên M3.

Sau A08, phần §5–§7 đã có hiện thực fixture cho M2–M6 như §11. Không có mapping Junsky thật nào được tạo. Các mô tả “chưa triển khai” trong phần M1 ở §10 ghi nhận phạm vi bàn giao M1 trước A08.

## 11. Hiện thực M2–M6 sau A08 — v0.2.0 / schema v8

### 11.1 Bảng và khóa

| Bảng/giao diện | Trường/khóa chính đã có | Bất biến/kiểm tra |
|---|---|---|
| `knowledge_versions` | id UUID; category, logical_key, revision; payload_json/content_hash; valid_from/to; known_at; evidence_json; supersedes_id; actor/created_at | UNIQUE(category,logical_key,revision); chờ duyệt không dùng; khoảng [from,to); chồng lấn cần thay thế rõ; thu hồi không hồi sinh bản cũ |
| `knowledge_events` | version_id, APPROVE/REVOKE, event_at, actor, reason | Lịch sử không ghi đè; đúng cutoff, không duyệt lại bản đã thu hồi |
| `historical_links` | source/target document, LINK_A/B/C, evidence_json, known_at, checker/checked_at | Nhiều ứng viên không ép A; Base chỉ C; không tự thành nhãn; E2 đo sự hiện diện mã tham chiếu, không phải độ đúng |
| `sessions` | UUID, mode, state, cutoff, source_attempt_id/snapshot_id, bank_ids/knowledge_ids JSON, actor, opened/closed_at, reason | Một OPEN/PREPARING bằng unique index; các mode không chung DB; từ chối thiếu nguồn/danh mục/tháng khóa/phiên trước chưa đóng |
| `proposals` | UUID, session_id/bank_id, revision/state, payload_json, created_at | UNIQUE(session_id,bank_id); năm bước, fields/confidence/evidence, constraints, candidates, allocations, unallocated_minor, completeness |
| `allocations` | UUID, proposal_id/open_item_id/item_key, amount_minor INTEGER >0, state | UNIQUE(proposal_id,open_item_id); trạng thái RESERVED/APPROVED/EXPORTED/POSTED/CANCELLED; trong transaction; không vượt sao kê/công nợ |
| `review_workbooks`, `review_imports`, `decisions` | Workbook ID/session/baseline/hash; import hash; quyết định ID/proposal/revision/action/payload/reason/actor/time | Excel kiểm cả tập dòng và khóa/revision; sửa mã phải là chuỗi; một dòng sai rollback cả lần; nhập đúng file lặp trả kết quả đã lưu |
| `export_batches`, `export_items` | Batch UUID/session UNIQUE, target fixture, trạng thái, hash workbook/manifest/path, times/actor; item UUID/proposal UNIQUE/decision/payload | Chỉ bản duyệt cuối; PREPARING → EXPORTED → PARTIALLY_VERIFIED/VERIFIED; xuất không làm nhãn |
| `export_batches.cancelled_*` | cancelled_at, cancelled_by, cancellation_reason (migration v8) | Chỉ hủy PREPARING chưa có file công bố. Trạng thái kỹ thuật cũ giữ, trạng thái hiệu dụng ABORTED_BEFORE_PUBLICATION; phiên/giữ chỗ hủy; không phục hồi batch đã hủy |
| `expected_balances` | PK(batch_id,item_key), source_open_item_id, before_minor/delta_minor/expected_minor | Kỳ vọng ngay sau batch; M5 cộng thêm batch phát sinh sau snapshot neo trước bộ đối soát, không so sai số tức thời với cuối tháng |
| `verification_runs`, `field_verifications` | UNIQUE(batch_id,source_hash); nguồn/time/actor/report; PK(run,item), mask/evidence/status | Nguồn mới sau xuất, đủ phạm vi; không ghi đè kết quả mới bằng bộ cũ; missing evidence → UNRESOLVED, chứng cứ trái giá trị → RECON_C |
| `labels`, `label_events` | UUID/bank/revision, fields/mask/context, amount, known/verified/eligible_at, valid_from/to, evidence/origin/verifier; ACTIVATE/REVOKE/SUPERSEDE | UNIQUE(bank,revision); một bản hiệu lực tại cutoff; chỉ trường được chứng minh; thu hồi/thay thế giữ lịch sử |
| `learning_runs` | cutoff/context, fingerprint UNIQUE, report | Tính lại từ tập nhãn đủ điều kiện; không tăng bộ đếm mỗi lần chạy; lưu danh sách nhãn và code/config hash |
| `evaluation_datasets`, `quality_runs` | Dataset key JSON [logical_id,version], artifact/hash/manifest; quality fingerprint UNIQUE/report/time | Đóng băng version; đổi dữ liệu cần version mới; nhóm không bị chia DEV/HOLDOUT/BLIND; không dùng nhãn của chính các bank thuộc dataset làm dữ liệu học |
| `month_closures` | month PK, nguồn, actor, closed_at/evidence | Bộ cuối tháng đủ kỳ, mọi sao kê/batch thuộc kỳ được đối soát; không còn phiên hoạt động hoặc phát sinh ngoài batch chưa giải quyết |
| `activity_log` | module/action/subject/actor/event_at/recorded_at/details | Tách thời điểm sự kiện giả lập khỏi thời điểm máy thực ghi log; actor tự khai báo, chưa phải cơ chế xác thực |

Mọi số tiền nội bộ dùng INTEGER VND scale 0; Excel xuất dưới dạng chuỗi để giữ độ chính xác, không công thức. Mã/tài khoản giữ số 0. Tiền công nợ có dấu Nợ−Có, phân bổ là trị tuyệt đối dương. `item_key` xuyên snapshot gồm account/counterparty/currency/item_id; đây là khóa fixture theo hệ nguồn ổn định, phải xác nhận lại khi có Junsky thật.

### 11.2 Nguồn và ngữ cảnh bổ sung

Fixture BANK nhận thêm `counterparty_account`, `counterparty_tax_id`, `invoice_references`. JOURNAL fixture nhận `bank_reference`, `bank_account`, `counterparty`, `project`, `expense`, `export_item_id`, `batch_id`, `invoice_key`, `invoice_allocations` = [{invoice_reference,amount_minor}]. Đây là tên trong contract mô phỏng; **chưa phải cột tồn tại ở Junsky**. Trường không có trên bằng chứng giữ chưa xác minh. TK và số tiền thực đối chiếu được suy từ các dòng Nợ/Có, không tin giá trị header tự khai.

Manifest phiên cần `posting_evidence_complete=true` và đủ bảy vai trò OPEN_ITEM/COUNTERPARTY/ACCOUNT/EXPENSE/PROJECT/LOCK_PERIOD/JOURNAL. `scope_open_items_complete=true` mới cho phép hiểu việc không có một item là số dư 0; thiếu xác nhận thì giữ unknown. Bộ fixture hiện cần bản ghi đại diện từng vai trò, kể cả dòng số dư 0 khi hết nợ; hỗ trợ nguồn thật không có bản ghi phải thiết kế khi có mẫu, không bịa bản ghi thật để vượt cổng.

Context nhãn/thống kê gồm **partition, pattern, policy_version, direction, bank_account, counterparty**. Chuyển policy_version thì không tự mang thống kê cũ sang. Thiếu tham số `min_count`/`min_share` trong policy thì không gợi ý từ thống kê. Khi có, thắng đồng thời theo trọng số số lượng và tiền, với hệ số mềm `1/(1+age_days/half_life_days)`; đây là công thức fixture công khai, chưa là ngưỡng chất lượng vận hành. Mỗi bank chỉ tính một lần trong tổng tiền, không nhân tiền nguyên giao dịch theo số dòng phân bổ.

Timestamp lưu UTC có microsecond, ngày nghiệp vụ giữ date. Ngày lịch pilot Việt Nam tính theo UTC+07 khi so với cutoff; không cắt ngày UTC để suy ngày địa phương. `known_at`, thời điểm duyệt/xác minh/eligible và [valid_from,valid_to) đều được lọc. Ngày biết thiếu vẫn NULL, không thay bằng ngày nghiệp vụ.

### 11.3 Excel, xuất và phục hồi

Workbook duyệt có META, DUYET, PHAN_BO. META/bộ dòng/các cột bất biến so với baseline trong DB; có thể đổi thứ tự hàng nhưng không thêm/xóa/trùng/sửa khóa. Người duyệt sửa năm trường và tiền phân bổ, chọn WAIT/APPROVE/REJECT; sửa/từ chối cần lý do tự do vì bộ bảy mã gốc chưa có. Code từ chối công thức và kiểm tra kiểu chuỗi các mã.

Batch nội bộ có CANH_BAO, FIXTURE_HEADER, FIXTURE_LINES và manifest JSON. Không có CB_tmpEntry1/2. Workbook/manifest đăng ký artifact trong transaction trước công bố, ghi bất biến; recovery giữ nguyên ID/byte. Nếu chưa công bố mà nguồn đã đổi, có thể hủy chuẩn bị có audit. Nếu file cũ đã công bố nhưng DB chưa hoàn tất, phục hồi chỉ hoàn tất cùng batch; đánh dấu nguồn đổi và yêu cầu đối soát, không tạo lại quyết định hoặc khẳng định đã import.

### 11.4 Đánh giá và giới hạn

Đáp án chỉ vào bước chấm, không truyền vào engine. A/B dùng cùng dữ liệu/cutoff và giữ chỗ mô phỏng theo thứ tự xác định; B chỉ bổ sung trường thiếu từ nhãn đủ điều kiện. Báo cáo có cỡ mẫu, phần chưa có đáp án, độ đúng toàn bộ/từng trường/phân bổ, phủ và sai số giá trị tuyệt đối theo thu/chi/dải tiền. `candidate-evaluate` là **thí nghiệm giả định áp dụng quy tắc**, được ghi rõ khác replay lịch sử; cần holdout và cấu hình QUALITY_GATE_FIXTURE đã duyệt, sau đó vẫn phải duyệt quy tắc riêng.

Khôi phục công nợ lịch sử chỉ tính tiến từ neo có as_of ≤ ngày cần dựng và known_at ≤ cutoff; không trừ ngược từ số dư tương lai. Các phát sinh chưa biết được báo thiếu, không coi là 0. Chưa có lịch sử PLHN đủ bằng chứng nên chưa có backtest thực hoặc độ đúng vận hành.

Nhãn lịch sử có đường xác minh riêng từ journal và người kiểm fixture. RECON_B chưa được giải quyết vẫn chặn chốt tháng; hệ thống không có nút bỏ qua chênh lệch. Hiện chưa có quy trình chỉnh sửa sổ thực/hủy đảo/import bổ sung để nghiệm thu; những nghiệp vụ ấy cần mẫu và quy trình kế toán, giữ ngoài khả năng vận hành đã xác nhận.
# Bổ sung đã triển khai ở V1 — A11

## Điều chỉnh hiện hành V1b — A12

Schema v9 thêm index `knowledge_policy_rank` trên category/partition/tier/order trích từ JSON, cùng `knowledge_epoch` và trigger đổi token khi phiên bản/sự kiện tri thức thay đổi. Migration v1–v8 giữ nguyên. Cache trong đối tượng Knowledge dùng `(category, cutoff)`, giữ snapshot phiên bản/sự kiện; ngày nghiệp vụ được lọc mỗi lần gọi. Không cache đề xuất, quyết định hoặc đáp án. Token trong transaction bảo đảm nhận thay đổi từ instance/connection khác, thu hồi và rollback; kết quả trả ra là bản sao. Có đường `cache_enabled=False` để kiểm chứng.

Payload mới có thể khai `expiry_policy`:

- `LAST_SEEN_DAYS`: `days` integer dương, `last_seen` ngày ISO và `basis` truy nguyên; ngày cuối hiệu lực = last_seen + days, valid_to = ngày kế tiếp.
- `VERIFIED_IDENTIFIER_NO_EXPIRY`: chỉ dùng khi kind=IDENTIFIER và verified=true, valid_to=null.
- `expiry_raw` và source_fields_raw giữ hạn nguồn; khi có expiry_policy, validation so valid_to với cấu hình, không còn bắt khớp hạn nguồn 90 ngày. Payload cũ không có expiry_policy vẫn kiểm theo hợp đồng V1.

Tham số của lượt V1b ở `var/vong-2/V1b/CAU-HINH.json`: STK 365 ngày; tên/từ khóa 180 ngày; định danh CHAC_CHAN không hết hạn. Sheet Ánh xạ STK không có lần cuối: ánh xạ chưa xác minh lấy max lan_cuoi của các hàng Quy tắc cùng STK, giữ hàng làm bằng chứng. Không suy ngày từ lúc đọc để giả lập lịch sử. Không có bằng chứng lần cuối thì phải dừng chuyển đổi để xử lý, không mặc định vô hạn.

110 hàng nguồn bậc 1/3 không có từ khóa chuyển thành KEY ở bậc 2/4 theo phê duyệt bổ sung của Anh; giữ source_tier, source_row và mã gốc. Bậc 2/4 không có empty_signature. Mẫu bậc 5 giữ mã đối tượng nguồn trong raw nhưng fields.counterparty=null; required_fields vẫn chứa counterparty. Các loại trừ regex là dữ liệu cấu hình được đưa thành regex đầy đủ trong payload, không nhúng nghiệp vụ vào literal_pattern.

known_at bản chuyển đổi = max(ngày lần đầu, thời điểm đọc thực). Bộ nghiệm thu T8 chỉ nhận POLICY có first_seen < 01/08/2026, loại cả ngày thiếu; không lùi known_at. Cột “không rò rỉ” có nghĩa bộ lọc này, vẫn nêu hạn chế thống kê/lần cuối và dữ liệu snapshot kế thừa; không tuyên bố là backtest độc lập sạch hoàn toàn.

Danh sách chờ nhiều dòng gồm variant, scenario, bank_id, amount_minor, template_id và source_policy đầy đủ; lưu riêng trong var, không công bố giá trị tiền giao dịch lên chat. Phủ loại phần chờ nhiều dòng = tổng trị tuyệt đối tiền FULL / (tổng trị tuyệt đối tiền sao kê − tổng trị tuyệt đối tiền chờ nhiều dòng); không cộng phần chờ vào tử số.

Phần hợp đồng V1 bên dưới là lịch sử; khi khác A12, áp dụng điều chỉnh V1b này.

Ngày 18/09/2026. Phần này áp dụng payload tri thức `contract_version=2`; hợp đồng nguồn chưa đổi (chờ V2). Payload version 1 vẫn chạy cho các fixture cũ. Không trộn POLICY hai version cùng khớp một giao dịch: chặn `MIXED_POLICY_CONTRACTS`. Schema SQLite giữ v8 vì dữ liệu mới nằm trong payload JSON và sự kiện hiện có; không sửa migration lịch sử.

| Thành phần | Kiểu và kiểm tra |
|---|---|
| POLICY | `template_id`, `partition`: text; `direction`: IN/OUT; `tier`: integer 1–5; `order`: integer dương, bằng hàng Excel nguồn; `needs_open_item`: boolean; `required_fields`: danh sách tên trường |
| fields | Object gồm counterparty, debit_account, credit_account, project, expense; giá trị text hoặc null; giữ số 0 đầu. Tài khoản chứa dấu `\|` bị từ chối, không tự tách dòng |
| trigger.mode | KEY, REGEX, KEY_REGEX; lần lượt khóa chính xác, regex, hoặc cả hai |
| trigger.key_type/key_value | BANK_ACCOUNT, TAX_ID, COUNTERPARTY hoặc COUNTERPARTY_NAME; giá trị text, không ép số; ba loại đầu so sánh chính xác |
| Tên đối ứng | Chỉ điều kiện mẫu, không chứng minh định danh. Mặc định normalize_text; tùy chọn `name_normalization=legacy-chung-v1` tái hiện chuẩn hóa tên từ script nguồn đã kiểm tra. Chỉ áp dụng cho COUNTERPARTY_NAME |
| trigger.regex | Biểu thức tường minh, tối đa 512 ký tự; kiểm cú pháp và cấm khớp chuỗi rỗng. Chạy trên diễn giải normalize_text. Giới hạn độ dài không phải bảo đảm giới hạn thời gian chạy regex |
| CASE.selector | Chính xác bốn trường type, value, entity_id, bank_account. type là BANK_REFERENCE, VOUCHER_NUMBER hoặc DESCRIPTION_HASH. Hash SHA-256 kèm `normalization=normalize_text-v1`; giữ scope pháp nhân/tài khoản và chiều |
| Thời gian | valid_from bao gồm; valid_to không bao gồm. `expiry_raw` giữ ngày han_dung nguồn; valid_to phải bằng ngày kế tiếp. known_at là lúc nhập thực, không lùi về kỳ nghiệp vụ; sự kiện duyệt cũng phải có trước cutoff |
| Truy nguyên | Giữ hash file, sheet, hàng nguồn, source_status, dữ liệu gốc. Trạng thái nguồn không thay thế sự kiện duyệt |

Trong mỗi partition, chọn mẫu khớp đầu tiên theo `(tier, order)` tăng dần. Hai logical_key khác nhau trùng partition/tier/order và giao khoảng hiệu lực bị chặn ngay trong transaction nhập, kể cả còn chờ duyệt. Khi chạy, nhiều partition cùng khớp hoặc hòa thứ tự đều chặn, không chọn ngẫu nhiên. CASE đã duyệt được xét trước POLICY; từ hai CASE cùng khớp trở lên phải chờ người, không dùng RULE hoặc nhãn học để thay CASE.

Khóa đã xác minh mâu thuẫn với đối tượng trong mẫu gây `TEMPLATE_IDENTIFIER_CONFLICT`. CASE không vượt khóa kỳ, đã hạch toán, trùng chứng từ, xung đột định danh hay cổng dữ liệu khác. Các lỗi cứng mới cũng chặn việc điền tay quyết định để xuất.

`matching_evidence` của đề xuất chứa case_ids, policy_ids và expired_policy_ids. Mẫu hết hạn không được chọn; có mẫu hết hạn từng khớp không đồng nghĩa toàn giao dịch phải bị chặn nếu còn mẫu hợp lệ khác.

Chuyển đổi hồi cứu BO-QUY-TAC: 110 chữ ký từ khóa rỗng được biểu diễn bằng điều kiện không bắt bất kỳ từ khóa nào trong từ điển nguồn, không thành wildcard. 29 mẫu nhiều tài khoản giữ raw, gắn `requires_multiline_review=true`, chặn FULL; thiết kế ở THIET-KE-MAU-NHIEU-DONG.md, chưa có lines hay export mới. Các điều kiện regex chống khớp nhầm được kiểm thử riêng; không lấy đáp án tháng 8 để đổi thứ tự nguồn.

Kho vận hành: 809 POLICY và 164 ánh xạ đều chờ duyệt bởi CFO_NTD. Các sự kiện MO_PHONG_KIEM_CHUNG chỉ nằm trong kho hồi cứu tách riêng. Đây không phải cơ chế phân quyền đăng nhập đã triển khai; actor là dấu vết sự kiện hiện hành. Bản pending chuyển tiếp được lưu trong thư mục chạy V1, chưa nạp vào chế độ that (V3).

## 12. Hiện thực V2–V6 — schema v14

Mục này thay thế mọi mô tả cũ về schema v8/v9 khi có khác biệt. Các migration v1–v9 giữ nguyên byte; v10–v14 có checksum, đã kiểm trên bản sao DB that có tri thức chờ duyệt và integrity/foreign key đạt.

### 12.1. Nguồn và chống trùng V2/V3

| Loại | Trường đã nhận | Khóa và kiểm tra |
|---|---|---|
| `INVOICE` | `net_minor`, `tax_minor`, `total_minor`, currency thuế, `ttxly`, trạng thái nguồn, liên kết điều chỉnh/thay thế/hủy, line có thuế suất/tính chất | Khóa chung XML↔bảng kê là MST bán + ký hiệu + số + mẫu. Hai bằng chứng giữ `known_at` riêng; lệch tiền vượt dung sai thành `WARNING_MONEY_CONFLICT`, không làm hỏng lô. Dung sai mặc định là 1 VND/dòng, cấu hình được. |
| `BANK` | MTID/CITAD, TK/tên đối ứng, ngày giờ phát sinh, số dư sau | Có `reference`: khóa ổn định. Không có: tài khoản + ngày giờ + tiền + số dư sau, ghi `identity_key_level=FALLBACK_ACCOUNT_TIME_AMOUNT_BALANCE`; thiếu thành phần thì chặn dòng. |
| `BASE` | mã/tên đề nghị, nhóm, trạng thái/ngày duyệt, tiền, TK thụ hưởng, dự án thô, đính kèm | Đọc tiền có hậu tố VND; không phân loại nhóm G ở tầng nguồn. |
| `OPEN_ITEM` | chứng từ công nợ, ngày, đối tượng, TK, tiền, dự án, hóa đơn, nội dung, hợp đồng vay | `as_of`/`snapshot_id` chỉ lấy từ metadata người nạp. `item_key` không đổi giữa snapshot theo account/counterparty/currency/item_id. |
| `JOURNAL` | DocsNo/số giao dịch NH, hóa đơn, đối tượng, dự án, khoản mục, trung tâm chi phí, lines Nợ/Có, posting status | Trạng thái đã ghi sổ lấy từ `operation.posted_journal_statuses`, không hard-code fixture. |

`that` dùng database riêng, `entity_id=PLHN`, chặn cờ xuất/nhập Junsky. `nap-nguon` nhận `as_of`, `exported_at`, `known_at`, basis, coverage và snapshot do người nạp khai. Nếu không truyền `known_at`, adapter dùng `exported_at` và ghi rõ basis. `.xls` chỉ đọc qua `xlrd==2.0.2`; không có wheel offline thì báo `XLRD_OFFLINE_WHEEL_MISSING`, không có parser `.xls` tự viết. Danh mục đọc file mới nhất theo từng vai trò; mã có trong sổ/công nợ mà vắng danh mục sinh `OUTSIDE_CATALOG_CODE`, vẫn nạp lô và không tự thêm mã.

### 12.2. Nhiều dòng, tri thức và workbook người duyệt

Migration v10 thêm `proposals.lines_json`, `decisions.lines_json`, `export_items.line_checksum`, `export_item_lines` và `document_observations`. `journal_lines[]` chỉ được tính khi có hóa đơn đã nối hoặc thuế suất khai báo trong mẫu. Không có căn cứ thuế hoặc không cân Nợ/Có sinh `MULTILINE_TAX_EVIDENCE_WAIT`/`MULTILINE_UNBALANCED`, giữ WAIT và không tự chia.

`knowledge_import_batches`, `knowledge_workbooks`, `knowledge_review_requests` lưu hash/lô/provenance của V4. Ba workbook nguồn được nhập thành PENDING; trạng thái cột nguồn không sinh APPROVE. Workbook người đọc có `NHOM`, `TU_KHOA`, `KHOA_CUNG`, `MAU_DINH_KHOAN`, `NGOAI_LE`, `CHO_DUYET`, `NHAT_KY` và JSON ẩn. Nhập ngược chỉ nhận “Anh duyệt”/ghi chú thành **yêu cầu** duyệt; sửa cột nghiệp vụ hoặc workbook cũ bị từ chối. `CFO_NTD` chỉ được dùng khi Anh ra lệnh duyệt riêng.

### 12.3. Chuỗi trạng thái và giới hạn shadow

`PROPOSED → APPROVED | REJECTED → EXPORTED → VERIFIED | PARTIALLY_VERIFIED`; giữ chỗ phân bổ đi theo `RESERVED → APPROVED → EXPORTED → POSTED` hoặc `CANCELLED`. Nhãn chỉ được tạo từ trường đã được sổ xác minh; `NONE` là khoảng trống phủ, không phải đề xuất sai.

Workbook duyệt V5 có `META`, `DUYET`, `PHAN_BO`, `CONG_NO_KHAC`. `PHAN_BO` chỉ giữ ứng viên đã xếp hạng/giữ chỗ, tối đa `review_candidate_limit` (mặc định 10) theo đề xuất. `CONG_NO_KHAC` cho nhập mã công nợ khác; khi nhập lại vẫn kiểm đối tượng, TK, tiền tệ, chiều, số dư và lý do.

V6 thêm `shadow_exports` và `shadow_verification_runs`. Shadow chỉ chạy ở `that` với actor bắt đầu `MO_PHONG_`; cấu trúc hai workbook có chính xác `CB_tmpEntry1` 17 cột và `CB_tmpEntry2` 37 cột, gồm `ErrorText`. Các cột có nghĩa chưa được xác nhận — `BankID`, `EntryID`, `EntryDM`, `DebtID`, `CashflowID` và chế độ `DAY_DU`/`DOI_UNG` — là mapping truyền vào, không có mapping ngầm. Thiếu mapping giữ chứng từ trong danh sách chờ. Tệp luôn gắn `SHADOW — CHƯA NHẬP JUNSKY`; đối chiếu T8 chỉ so header/cấu trúc, không phải bằng chứng đã import.

### 12.4. Điều chỉnh V7 cho nguồn thật

- `BANK` tách header eFAST theo `/` hoặc xuống dòng, giữ `mtid_citad`, và lưu ngày/giờ theo hợp đồng. Float chỉ nhận khi nguyên; số có lẻ thành `INEXACT_MONEY` và cách ly dòng. Báo cáo lô có tổng Có-Nợ, số dòng, số dư và coverage.
- `INVOICE` dùng khóa `seller_tax_id`, series, số bỏ số 0 đầu và `invoice_type=GTGT|BAN_HANG|model`; lưu model, direction, tax status, khoản khác/không chịu thuế, hóa đơn liên quan và mã `ttxly`. Mẫu 2 là `net=total`, `tax=0`; chênh nguồn là WARNING.
- `BASE` đọc `get.request`, `form[]`, `custom_table`, attachment và `fetched_at`. `business_date` là ngày `last_update` UTC+07. Thiếu tổng tiền là `BASE_AMOUNT_MISSING`: giữ placeholder truy nguyên nhưng không promote document.
- `OPEN_ITEM` dùng `business_date=as_of`, giữ `document_date` và dấu theo `account_nature`. `JOURNAL` nhận bố cục cặp `Ghi nợ/Ghi có/Số tiền` lẫn bố cục Nợ/Có.
- Migration v15 thêm `quarantine_records(attempt_id, ordinal, code, message, raw_hash)`. Lô that chỉ commit phần hợp lệ khi tỷ lệ ordinal cách ly không vượt `operation.quarantine_max_ratio`; `xem-cach-ly` không xuất diễn giải nguồn.
