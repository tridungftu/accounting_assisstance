# Gói M8 — bảng kê và đối chiếu hóa đơn, sổ, bằng chứng thanh toán

Ngày chuẩn bị: 19/10/2026. **Đầu bài để review trước coding; chưa triển khai/chạy/nghiệm thu M8.** Đích là C5a–C5b, L9 và dữ liệu đối chiếu L12 của toàn cây 33. Tái dùng #7, K1–K5 và shell chung; không xây lại ứng dụng tải cổng thuế. Không đọc dữ liệu thật, credential, seed/sample payload; không chạy/import/sửa product trong lúc Claude sửa CRM. Không xóa file/temp/DB.

M8 xuất **bảng kê hỗ trợ và danh sách chênh/việc cần xử lý**, không sinh bút toán, tờ khai hoặc kết luận tự động “đủ điều kiện khấu trừ”. Khớp khóa/số tiền, XML parse được hoặc mã trạng thái nguồn không tự chứng minh tính hợp lệ thuế. Gói này không nêu quy định pháp luật, thời hạn, tỷ lệ hay ngưỡng hiện hành; production policy phải được kiểm chứng/chốt riêng trước khi áp dụng.

## 1. Căn cứ và phần dùng lại

- `CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md` M8/L9/L12; `LO-TRINH-TRIEN-KHAI-TOAN-BO-33.md` C5a–C5b/C9c; `HOP-DONG-TICH-HOP-VA-TAI-SU-DUNG-33.md` R_HD; `DANH-MUC-TAI-SU-DUNG-PHAN-MEM.md` §3.
- TL29 §9, TL30 D4; TL31 #7 và mục C **Check Kế toán/Check VAT input-output vs invoice** (phương pháp chưa có tài liệu); TL35 K1–K5, hai kho/nhật ký/mã Junsky; TL37 V2/V7/V8 và chuỗi chứng từ; TL38 file gốc/chứng từ/dòng/liên kết/lô/ba thời điểm; TL40 K1 cho nguồn ngoài, quyền pháp nhân và web trung tâm.
- Dùng bộ tải #7 nguyên trạng: người vận hành đăng nhập/chạy theo quy trình hiện có, K1 đọc kết quả. Không đưa tài khoản cổng thuế vào app kế toán, không chạy lại Playwright hoặc làm portal thứ hai trong M8.
- Dùng `ThatAdapter._xml_rows/_invoice_table_rows`, `parse_invoice_xml`, ingestion raw/hash/staging/evidence hiện có. `JournalIndex.link` có thể cung cấp **ứng viên** sổ, không thay xác nhận đối chiếu thuế. Dùng typed K2, quyền, link/phân bổ và K5 đã được review từ CRM/M1/M2; không coi schema/code chưa nghiệm thu là năng lực runtime sẵn có.

**Đối chiếu bổ sung của Codex19/10:** `Record.kind=INVOICE` là contract nguồn legacy. Enum typed `kho.chung_tu.loai` thực là `HD_MUA/HD_BAN/BANG_KE_THUE/SO_JUNSKY`; không có enum `INVOICE`. Bộ chuyển `tools/chuyen_sqlite_sang_pg.py::_chung_tu` hiện chiếu BANK/JOURNAL, chưa phải đường promote INVOICE sang typed K2. Parity75XML V13 thuộc runtime legacy hai engine, không chứng minh đã có ingest invoice typed K2. Trước M8 cần hoàn thiện/kiểm đường nhận dùng lại parser K1 vào đúng HD_MUA/HD_BAN và observation bảng kê chung, không tạo kho hóa đơn M8 thứ hai hoặc coi enum đã có là runtime đã chạy.

## 2. Interface kỹ thuật đã đối chiếu tĩnh

Nguồn #7: `D:\Claude\Phan mem download hoa don`.

| Điểm neo | Fact có bằng chứng | Giới hạn |
|---|---|---|
| `src/build.js:18–65` | ExcelJS tạo `.xlsx`, cột từ `cfg.EXCEL_COLUMNS`; `tdlap` qua formatDate; giữ field số/text của API và format các money field | Format `#,##0` là hiển thị, không chứng minh tiền gốc exact/đơn vị/currency hoặc đủ căn cứ thuế |
| `config.js:63–82` — chỉ đọc khai báo header | `_stt→STT`, `khmshdon→Ky hieu mau so`, `khhdon→Ky hieu HD`, `shdon→So HD`, `tdlap→Ngay lap`, `nbmst/nbten→MST/Ten nguoi ban`, `nmmst/nmten→MST/Ten nguoi mua`, `nmcccd→So giay to (CCCD)`, `tgtcthue→Tien chua thue`, `tgtthue→Tien thue`, `tgtttbso→Tong thanh toan`, `dvtte→Don vi tien te`, **`tthai→Trang thai`** | Không đọc seed/sample hay giá trị công ty thật. Không tự đồng nhất `tthai` với `ttxly` hoặc nhãn pháp lý |
| `src/job.js:197–227,256–276` | Ghi XML/ZIP, PDF, bảng kê theo kỳ/chiều; có số tổng/XML ok/không có XML gốc/XML lỗi/PDF lỗi; bảng kê khóa có thể xuất tên thay thế | Phiên tải chưa có manifest đủ chuẩn M8. Không có XML gốc theo nguồn không tự là hóa đơn không hợp lệ; thiếu file không được coi đủ kỳ |
| `nguon/that.py:459–476` | Đọc `.xml` và XML trong ZIP, lọc pháp nhân theo MST cấu hình, giữ issue parse | Parse lỗi có thể trả warning và không có row; phải giữ file lỗi/số lỗi trong manifest, không tính danh sách rỗng là đối chiếu đạt |
| `nguon/that.py:478–498` | Nhận header có/không dấu của bảng kê; giữ model/series/number/date/seller/buyer/net/tax/total/currency/status, cảnh báo lệch tổng/phần lẻ | Hiện gán cột “Trạng thái” vào `ttxly`, thiếu thì mặc định `1`, thiếu currency mặc định VND. **Đây là hành vi legacy, chưa chứng minh đúng contract #7/M8**; không nâng các default thành bằng chứng trạng thái/currency đã xác minh |
| `nguon/that.py:689–747` | XML đọc `KHMSHDon/KHHDon/SHDon/NLap/DVTTe`, MST hai bên, các tổng, dòng `HHDVu`, raw `TTHDLQuan` gồm loại/khóa hóa đơn liên quan | `source_status=XML_RECEIVED` chỉ là đã nhận XML. `related_invoice` còn là mã/tham chiếu nguồn, cần mapping semantics/version, đủ căn cứ chuỗi; parser có hành vi làm tròn VND/cảnh báo cần bảo toàn giới hạn |

Hash lúc đọc: `src/build.js` = `ca7fe35cafe7c802d5ebe7506db9fd7a1294552d833569306f03b1a03976f209`; `src/job.js` = `a7fcd2e791b29acf62acdb6b0c303613f24c4fb63f5c975e025b079bf0f1a553`; parser `src/kho_tri_thuc/nguon/that.py` = `f7330761f1ef8dbbcdc49429a09919f6135001dd0a50d804e6212af3de0ff1fc`. Đây là kiểm tra code/header, chưa là chất lượng tải hoặc đối chiếu runtime. Khi giao code phải kiểm lại hash/current state.

## 3. Contract trung tính và provenance

Mỗi phiên nguồn cần manifest dùng registry K1 chung: instance/adapter contract version, pháp nhân, chiều mua/bán, kỳ/phạm vi truy vấn, lúc bắt đầu/kết thúc nhận do server ghi, ngày xuất nguồn riêng, file/MIME/hash/kích thước, số dòng nguồn/thành công/lỗi/thiếu XML và trạng thái **đủ/chưa đủ phạm vi**. Tên thư mục/tháng hóa đơn/ngày lập không thay `known_at`; thời điểm nguồn tra cứu trạng thái khác `ngay_nghiep_vu`. Dữ liệu học/chấm chỉ được dùng theo eligible_at đúng cutoff, không lấy snapshot mới sửa hồi tố để làm sạch chấm cũ.

Khóa hóa đơn dùng danh tính đã xác nhận: pháp nhân/chiều + MST người bán + mẫu/ký hiệu + số chuẩn hóa theo contract. Giữ số/ký hiệu raw, không bỏ chữ số có ý nghĩa hoặc ghép theo tên. MST người mua/người bán xác định chiều trong phạm vi đã duyệt, không từ folder hoặc số tiền. Chưa đủ khóa → chờ xử lý, không fuzzy merge. Cùng key nhưng nội dung khác là conflict/revision có vết, không chọn file mới nhất theo tên.

XML và bảng kê cùng hóa đơn là **một danh tính hóa đơn với nhiều bằng chứng/observation**, không hai công nợ/bút toán. Bảng kê phải giữ file/sheet/row locator, raw `tthai` và namespace status/source version. Trạng thái nguồn, trạng thái duyệt kế toán, kết quả đối chiếu, và kết luận policy thuế là các trường khác nhau. Chưa có mapping `tthai/ttxly/TTHDLQuan` được kiểm thì giữ mã raw + “chưa mapping”; không gọi default `1` là gốc/hợp lệ.

Tiền: giữ các đại lượng net/tax/total/other/non-taxable, currency, tax-rate raw và precision/rounding provenance riêng. Bằng nhau chỉ so khi cùng đồng tiền/cơ sở/phạm vi; không tự FX, phân bổ VAT hay chấp nhận dung sai mới. Decimal/minor bảo toàn payload nhận được, không phục hồi số đã bị JS/Excel hoặc legacy làm tròn. Dữ liệu ngoài precision contract/thiếu đơn vị giữ chờ. Các hành vi default/làm tròn legacy chỉ được tái dùng khi profile có căn cứ và ghi rõ; không tự sửa parser dùng chung giữa lúc Claude đang viết CRM.

## 4. Ma trận yêu cầu → tái sử dụng → ca DEMO → gap

| Yêu cầu | Field/bằng chứng nguồn | Tái sử dụng | Output | Ca DEMO cần chạy | Gap/cổng |
|---|---|---|---|---|---|
| Danh sách mua/bán theo kỳ | Khóa hóa đơn, ngày, chiều, MST, file/hash; manifest kỳ/chiều | #7 + K1/ThatAdapter | Bảng kê nguồn có provenance, số nhận/lỗi/thiếu | Hai pháp nhân, hai chiều; parse lỗi/thiếu kỳ không thành đạt | Coverage/manifest thực #7; header/profile đã pin |
| XML ↔ bảng kê | Key, net/tax/total/currency, raw status/source time | INVOICE/evidence hiện có; link chung | KHOP_DU_LIEU/THIEU_XML/THIEU_BANG_KE/LECH/XUNG_DOT/TRUNG_NGUON; không kết luận thuế | Cùng hóa đơn hai nguồn → một identity/hai evidence; nhận lại delta 0 | Thiếu phạm vi thì CHUA_DU_PHAM_VI, không gắn “thiếu” chắc chắn |
| XML/bảng kê ↔ sổ | Khóa invoice, journal row/EntryID/EntryDM, account/debit/credit, lô/kỳ | Parser sổ và JournalIndex ứng viên; typed SO_JUNSKY/lô/liên kết | Chuỗi từng invoice–dòng sổ, nhóm thiếu/thừa/lệch và tổng theo cùng cơ sở | Hai hóa đơn cùng tiền; một hóa đơn nhiều dòng sổ; một sổ nhiều hóa đơn; cùng tiền khác key không tự khớp | Mẫu xuất sổ/CheckVAT method chưa đủ; không dùng cửa sổ thời gian khớp lịch sử làm bằng chứng chắc chắn |
| Điều chỉnh/thay thế/hủy | Raw relation/status, hóa đơn liên quan và hồ sơ nguồn | `related_invoice`, raw, common link/version | Chuỗi quan hệ chờ xác minh/đã xác nhận; danh sách trạng thái nguồn mâu thuẫn với sổ | Mã trạng thái lạ; relation thiếu hóa đơn gốc; chu trình/vòng lặp; một hóa đơn nhiều revision | Mapping code/loại quan hệ và căn cứ xử lý production cần review; không tự net hoặc bỏ thuế/sổ cũ |
| L9 bằng chứng thanh toán | Link M2↔M1, amount/currency/allocations, bản chứng từ gốc, trạng thái xác nhận | N1/link/phân bổ chung; BANK và công nợ đã có | DA_CO_BANG_CHUNG/THIEU_BANG_CHUNG/CHUA_XAC_NHAN hoặc tương đương; ghi căn cứ, không “đủ điều kiện” | Trả một phần/nhiều hóa đơn; thiếu chứng từ; gỡ link/đã xuất; không thêm BANK/112 | Policy điều kiện/ngưỡng/thời điểm/ngoại lệ production và văn bản chính thức chưa chốt trong gói này |
| L12/lô/kỳ | Snapshot đầu vào, kết quả version, lô/EntryID, kết quả xử lý | Kỳ/lo_xuat/đối chiếu chung | File soát M8 + việc V7/V8 có vết; liên kết M10 | Restart còn phiên; đổi input tạo revision mới; kỳ khóa chặn chốt theo quyền | Đối chiếu lô thực cần gate Junsky, mẫu EntryID và dữ liệu đã cấp |
| Cảnh báo NCC/hồ sơ | Tài liệu tra cứu/nguồn/ngày tra cứu/người xác nhận | File gốc + việc chờ/chú thích evidence | Cờ theo nguồn, chưa kết luận pháp lý | Tài liệu quá phạm vi/không nguồn → chưa xác minh | Nguồn cập nhật và người phụ trách chưa được xác định; không xây crawler rủi ro mới |

## 5. Workflow chung, quyền và màn hình

Luồng bấm trong shell: **Nhận nguồn DEMO → xem coverage/lỗi → chọn pháp nhân/kỳ/chiều/snapshot sổ → chạy đối chiếu dữ liệu → xem từng chênh và chuỗi nguồn → đề nghị/xác nhận/gỡ link theo quyền → ghi hồ sơ xử lý → xuất file soát → mở lại phiên/lịch sử**. Không nút tải portal thứ hai; không bắt Anh gõ lệnh hoặc chỉnh file Junsky.

Kế toán thuế kiểm/chốt kết quả đối chiếu trong quyền được cấp; người xem chỉ đọc; người nộp không được thay duyệt/chốt. Server xác thực actor–module–pháp nhân–hành động; RLS và FK cùng pháp nhân, không tin body/token local đơn thuần. DEMO actor `MO_PHONG_`, hai pháp nhân; không dùng `CFO_NTD` để phê duyệt thật. Phòng ban chỉ thấy phạm vi được cấp.

Khớp/không khớp và bằng chứng được lưu phiên bản theo input snapshot + profile/rule version; xác nhận không sửa XML/bảng kê/sổ/BANK gốc. Link/gỡ link có audit và transaction, kiểm lại số/phạm vi trước chốt/xuất, không double allocation. Sau khi snapshot/trạng thái nguồn/link thanh toán đổi phải tạo kết quả mới hoặc đánh dấu kết quả cũ không còn hiện hành; không giữ màu Xanh cũ im lặng. Kỳ/lô đã chốt theo cơ chế chung; xử lý sửa sau chốt có hồ sơ/việc tương ứng, không rewrite lịch sử hoặc tự tạo bút toán.

File soát phải ghi **“Đối chiếu dữ liệu hỗ trợ kế toán thuế — không phải tờ khai/kết luận điều kiện thuế”**, có mã dòng/khóa giả DEMO, raw/canonical values, nguồn/row/snapshot, trạng thái dữ liệu, lý do, người/thời điểm xử lý và link truy ngược. Số exact được giữ qua DB/API/UI/workbook cell; text nguồn chống formula injection. Tách nhóm chưa đủ phạm vi/chưa kiểm và tổng số lỗi; không xuất một file trống để gọi thành công. Mức 2 Junsky vẫn khóa; M8 không tạo CB_tmpEntry bút toán.

## 6. Typed K2 — đề xuất cần review trước coding

Giữ `kho.tep_goc/chung_tu/chung_tu_dong`, typed `HD_MUA/HD_BAN/BANG_KE_THUE/SO_JUNSKY` và link/phân bổ chung làm nguồn authoritative; tái dùng adapter/contract INVOICE legacy ở biên K1, không sao chép invoice/BANK/sổ vào một kho M8. Promote/observation typed còn là việc cần triển khai và kiểm như §1, chưa được coi là năng lực đã có. Cần kiểm runtime/schema hiện hành sau CRM để quyết định chi tiết, không sửa migration checksum cũ.

**Extension DDL dự kiến, chưa chốt:** một bảng phiên đối chiếu typed (`id`, pháp nhân FK, kỳ/chiều, bộ snapshot/hash đầu vào, profile/rule version/hash, coverage, trạng thái, người/thời điểm tạo/chốt, supersedes) và một bảng kết quả typed theo danh tính/nhóm đối chiếu (`id`, phiên FK, khóa hóa đơn chuẩn, loại kết quả, số dòng mỗi nguồn, currency/cơ sở, các tổng/chenh minor nullable, tình trạng bằng chứng thanh toán, tình trạng xử lý, người/thời điểm, lý do). Raw/locator/chi tiết giải thích có thể JSONB có schema, không nhét authoritative amounts/status vào JSON không kiểm soát.

Quan hệ nhiều XML/bảng kê/dòng sổ/tiền dùng bảng link/evidence chung đã review; mỗi dòng kết quả truy được tất cả row nguồn. Không giả ID dòng bảng kê thành UUID chứng từ khác. Bản kê và dòng cùng hóa đơn phải có source observation/identity riêng, giữ duplicate source row để điều tra dù canonical identity chỉ một. Unique theo `(pháp nhân, input fingerprint, profile version, kết quả version)` và khóa dòng ổn định; FK/transaction ngăn cross-entity, kết quả mồ côi và thay input sau chốt. Schema cụ thể, tên bảng, nơi lưu observation và loại link phải review với TL38/core hiện hành **trước giao Claude coding**; đây không phải migration được phép tự áp ngay.

## 7. Tiêu chí bàn giao và phần thiếu thật

DEMO tối thiểu: hai pháp nhân/hai chiều; XML+bảng kê+sổ+payment link; thiếu từng nguồn; source scope thiếu/parse lỗi; duplicate cùng/khác payload; trạng thái lạ/thiếu (không default hợp lệ); điều chỉnh/thay thế thiếu gốc/chu trình; nhiều dòng sổ/nhiều hóa đơn cùng tiền; lãi/FX hoặc đơn vị chưa rõ không tự đổi tiền; thanh toán một phần/nhiều lần/gỡ link; input đổi sau chốt; role/RLS/cross-entity; restart/dedup/migration upgrade; file soát tải bằng nút và kiểm nội dung/cell thực. Không sinh thêm INVOICE/công nợ/BANK/bút toán khi chỉ thêm bằng chứng hoặc link.

Claude tự chạy unit/integration trên PostgreSQL DEMO có dữ liệu và role thật sau khi được giao; Codex/agent độc lập kiểm oracle/negative case/GUI. Giữ DB/file/temp, đặt guard và `PYTHONDONTWRITEBYTECODE=1`; không import backup tạo cache, không cleanup. Skip, 0/0, cùng lỗi hoặc chỉ so tổng không được tính đạt cả dòng nghiệp vụ. Ghi nguồn/hash/count trước–sau, phiên bản rule/schema, hạn chế và ca chưa chạy; regression parser hóa đơn/M1/M2/M3 liên quan.

**Đã chốt đủ để thiết kế/demo:** M8 là đối chiếu/bảng kê, dùng #7/K1 và một kho/shell; L9 đọc bằng chứng từ M1/M2; L12 giữ phiên/lô và truy nguồn; không làm tờ khai hoặc hạch toán thuế thay Junsky.

**Gap phải hoàn thiện trong toàn chương trình:** mẫu và phương pháp CheckVAT đang làm tay; schema/mapping trạng thái chính xác `tthai` so với `ttxly` và XML relation; căn cứ liên kết invoice–dòng sổ/thuế trong export Junsky; policy production về cơ sở/precision/dung sai/currency; quy tắc điều kiện thuế/ngoại lệ cùng nguồn chính thức hiện hành khi tới bước đó; nguồn và quy trình kiểm NCC; coverage/manifest tải thực. Thu thập mẫu/technical mapping có sẵn tại máy trước, chỉ hỏi phần không thể lấy hoặc quyết định mới. Không mặc định các gap thành đã chốt để nâng màu/điểm hoặc coi toàn M8 hoàn thành.
