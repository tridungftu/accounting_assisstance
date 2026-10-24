# Gói M9 — nhận dữ liệu khoản vay #9, nối tiền và lịch định kỳ

**Ngày khảo sát:** 19/10/2026. **Trạng thái:** đầu bài triển khai sau CRM-01, chưa có bridge M9 được nghiệm thu. Chỉ kiểm tra tĩnh tài liệu và mã kỹ thuật; không chạy app, gọi mạng, đọc Google Sheets/dữ liệu thật hoặc thông tin xác thực. Không sửa phần mềm khoản vay. Không xóa bất kỳ file nào, kể cả file tạm khi triển khai/kiểm thử.

**Đích toàn chương trình giữ nguyên:** toàn cây 33, gồm M9 vốn vay **và** phần đầu tư tài chính phải hoàn thiện đặc tả. Gói nguồn vay dưới đây phủ C4a/C4b, chuẩn bị C4c, L7 và L12; hoàn tất adapter không đồng nghĩa toàn M9 đã xong. Các chính sách còn thiếu là việc phải hoàn thiện trong chương trình, không phải lý do bỏ phần hành.

## 1. Căn cứ và phần giữ nguyên

- `CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md`: M9, L7, L8, L12; `LO-TRINH-TRIEN-KHAI-TOAN-BO-33.md` C4a–C4d; `HOP-DONG-TICH-HOP-VA-TAI-SU-DUNG-33.md` R_VAY; `DANH-MUC-TAI-SU-DUNG-PHAN-MEM.md` §4.
- TL29 §10; TL30 F1–F3; TL31 #9 và quyết định **đọc Google Sheets API**, không xuất CSV thủ công thành quy trình vận hành; TL32 L7/L8/L12; TL33 HDVAY; TL35 K1–K5, master có phiên bản và mã chung; TL37 V1/V3/V4/V7/V8; TL38 hợp đồng/phiên bản/lịch trả nợ/liên kết/ba thời điểm; TL40 §4, §8.
- Tái dùng danh mục vay, khế ước, lịch gốc, mốc lãi suất, phát sinh, giao diện và phép tính có sẵn của #9. Không xây lại phần mềm theo dõi vay, bộ tính gốc/lãi hoặc dashboard hạn mức/covenant.
- Dùng tiếp typed K2 PostgreSQL, quyền actor–hành động–pháp nhân/module, K5 và link/phân bổ chung **sau review CRM-01**. Đọc API/service/migration thực khi giao code; không coi schema hoặc code đang viết là runtime đã nghiệm thu. Không tạo framework, kho SQLite K2, bảng duyệt hoặc bảng link riêng cho M9; không dùng `quick_items.*_json` làm master/lịch authoritative.
- Google Sheets là nguồn đọc theo TL40; không cấp tài khoản Google quyền PostgreSQL. Chỉ adapter của lõi ghi qua repository/service đã kiểm và quyền tương ứng. SQLite thật vẫn giữ nguyên; mức 2 Junsky, duyệt thật, cloud AI và gửi tin thật tiếp tục qua cổng riêng. DEMO dùng actor `MO_PHONG_` được server xác thực, không tin actor/entity từ client.

## 2. Khóa đúng phiên bản nguồn — các fact đã đọc lại

Root kỹ thuật: `D:\Claude\Phan mem theo doi khoan vay`. Hai bộ dưới đây khác nội dung, chưa có bằng chứng bộ nào đang triển khai trên Google:

| Mã nhận dạng khảo sát | File | Dòng / byte | SHA-256 |
|---|---|---|---|
| `VAY_ROOT_20260829` | `Code.gs` | 920 / 54.959 | `98774668ddf909b328e21e399d938d6740f1db4266e1661df78ec87e665b38db` |
| `VAY_DEPLOY_20260922` | `apps-script-deploy/Code.js` | 1.203 / 74.697 | `593d6ba8efce4a301a3f42ad2b2c2936ed90119ccfdc8375e11fd3a85768d8f4` |
| UI root khảo sát | `loan-tracker.html` | 1.551 / 140.381 | `8f4612df3f8cd5ac2ba57efa447723b0d3c2c4892a56b89ebca431bcb6bbc555` |
| UI bộ deploy khảo sát | `apps-script-deploy/Index.html` | 1.959 / 181.267 | `767f1f17680633564681ba3fdafd1aba4decc7e9406bc696a30dcfab2495e6b7` |

Đây là tên contract phục vụ khảo sát, không phải version do app công bố hoặc xác nhận đang deploy. Cần pin contract theo hash mã và **header thực**; không chọn bản deploy chỉ vì tên thư mục/ngày file. DEMO khóa một profile, thử profile kia phải báo không hỗ trợ thay vì âm thầm ép schema. Có thể hỗ trợ profile thứ hai bằng adapter khai báo riêng và bộ test riêng sau đó.

**Phân biệt cặp UI/server:** `apps-script-deploy/Code.js:92–96` yêu cầu HTML tên `Index`; file tương ứng có thật tại `apps-script-deploy/Index.html`. UI deploy gửi lịch gốc có `maKheUoc` (`:1569–1586`), phù hợp cột/phạm vi của server deploy. Ở root, `Code.gs:86–90` cũng yêu cầu `Index`, nhưng **không có `Index.html` tại root**; có `loan-tracker.html` với lịch gốc cấp khoản vay không có `maKheUoc` (`:1273–1285`), phù hợp phần schema cũ đã kiểm trong `Code.gs`. Điều này chỉ chứng minh tương ứng tĩnh ở các field đã đối chiếu, không chứng minh cả cặp root chạy được, file đã được đổi tên/upload trên Google, hoặc hai UI/server tương thích đầy đủ. Không gán dòng/hash của UI deploy cho UI root. Mọi trích dẫn UI/export dưới đây dùng **`apps-script-deploy/Index.html`**; nếu nhận output do UI tạo, manifest cần nhận dạng cả hash/profile UI lẫn server/schema nguồn.

`apps-script-deploy/Code.js:37–68` khai báo các cột bên dưới. `Code.gs:36–62` có các sheet tương ứng nhưng **không có** `maKheUoc` ở `LichTraGoc`, các cột mới của hợp đồng mua/vay ngắn hạn cũng thiếu. Đọc theo tên cột, không theo vị trí vật lý.

### 2.1 Dài hạn — whitelist nguồn đầu tiên

| Sheet / grain | Khóa logic nguồn | Trường nhận và ý nghĩa kỹ thuật |
|---|---|---|
| `DaiHan` / một HĐTD | `maKV` | `nhom, congTy, nganHang, soHD, duAn, tienTe, hanMuc, kyHan, anHan, quyUocTinhLai, trangThai, duNoSaoKe, ngaySaoKe`; `updatedAt/updatedBy` chỉ là metadata nguồn. `hanMuc` là hạn mức, **không** là số đã giải ngân hoặc dư nợ. `tsdb/ghiChu` chỉ giữ cục bộ khi cần bằng chứng, không dùng làm khóa/mẫu học. |
| `KheUoc` / một lần giải ngân | `maKV + maKheUoc` | `ngayGiaiNgan, soTien`; tham chiếu HĐ cha và tiền tệ từ HĐ đã map. Không nhân `hanMuc` thành khoản giải ngân. |
| `LichTraGoc` / một kỳ trong một phạm vi | `maKV + scope + kySo` | `ngayDenHan, soTienGoc`; deploy có `maKheUoc`, trống nghĩa **lịch chung cả khoản vay** (`apps-script-deploy/Code.js:415–441`). Root chỉ có lịch cấp khoản vay. Không nhân lịch chung sang từng khế ước rồi cộng thêm lịch riêng. Hai lịch cùng bao phủ nghĩa vụ mà chưa có quy tắc ưu tiên → chờ làm rõ. |
| `LichLaiSuat` / một mốc hiệu lực | `maKheUoc + apDungTuNgay` | `laiSuat` (%/năm), `ghiChu` làm bằng chứng cục bộ; không có id hoặc timestamp từng mốc. Nhiều dòng cùng khóa, khác tỷ lệ → xung đột; không chọn dòng cuối theo thứ tự sheet. |
| `PhatSinh` / một sự kiện đã ghi nguồn | `id` | `ngay, maKV, maKheUoc, traGoc, traLai, phi, soChungTu`; `updatedAt/updatedBy` metadata. Một dòng có thể có nhiều cấu phần. Tham chiếu chứng từ là bằng chứng khớp, **không** chứng minh đã có bút toán kế toán/đã thanh toán trong hệ thống. |

`scope` là định danh kỹ thuật cần lưu rõ: `LOAN` với mã khế ước trống, hoặc `DRAW + maKheUoc`. `kySo` phải là số nguyên dương theo profile đã kiểm; thiếu/không duy nhất thì chờ xử lý, không lấy số dòng làm khóa vĩnh viễn. Không để lịch thiếu `maKV` hoặc mốc lãi không tìm được khế ước lọt vào lịch đã duyệt.

### 2.2 Ngắn hạn, LC và giới hạn bằng chứng bảo lãnh

| Sheet | Khóa / các field có thật trong deploy | Giới hạn sử dụng |
|---|---|---|
| `VayNganHan` | `id`; `soNhanNo, congTy, nganHang, nhaCungCap, tenHang, soVay, soDaTra, tienTe, soNguyenTe, ngayNhanNo, kyHan, ngayDenHan, laiSuat, quyUocTinhLai, trangThai, soLC, ngayTraNoThucTe, maLienKet, soToKhai, soHoaDon, trangThaiHang, ngayMoLC, tyGia, chiTiet` | Một lần nhận nợ; source ghi `soVay/soDaTra` trên VND, `soNguyenTe/tienTe` riêng. Trạng thái nguồn có `LC đã mở`, `Đang vay`, `Đã tất toán` (`apps-script-deploy/Index.html:871`). Mở LC chưa tự là giải ngân. `chiTiet` là JSON nguồn, cần pin schema con trước khi diễn giải. Không chia `soDaTra` tổng thành các lần trả tưởng tượng. |
| `HopDongMua` | `id` một dòng hàng, `maHDM` nhóm HĐ; `soHD, ngayHD, loaiHD, loaiHang, hinhThucVay, congTyMua, duAn, maHDTDLienKet, nhaCungCap, tienTe, paymentTerm, nganHang, maHang, soLuong, triGia, soToKhai, soHoaDon, ngayThanhToan, donGia, triGiaNT, tyGia` | Bằng chứng liên kết khoản tài trợ với HĐ mua/hóa đơn/dự án, không sinh thêm HĐ vay hoặc công nợ hóa đơn M2 từ từng dòng hàng. `triGia` là VND; `triGiaNT` là nguyên tệ ở bản deploy. |
| `HanMucTinDung` | `id, nganHang, congTy, loaiHanMuc, hanMucDuocCap, hieuLucTu, hieuLucDen` | Chỉ metadata tham chiếu nếu cần giải thích; không giám sát sử dụng hạn mức, thêm covenant hoặc cảnh báo hạn mức. |

Chưa thấy bảng bảo lãnh chi tiết có khóa sự kiện, lịch phí/ký quỹ và hồ sơ phát hành tại các cột đã kiểm. `bankCfg.baoLanh` và `manualRows.lcBl` là tổng thông tin dashboard, **không đủ** thay chứng từ bảo lãnh. C4c vẫn phải có nguồn hồ sơ/contract cho phí bảo lãnh, ký quỹ, phát hành/giải tỏa khi làm phần đó; không dựng phát sinh từ số tổng hoặc mặc định LC = bảo lãnh.

## 3. Kênh đọc thật và rủi ro export đã xác minh từ code

1. **Vận hành đích:** Google Sheets API với service account **scope readonly**, chỉ whitelist spreadsheet/ranges của profile đã khóa. Khóa/bí mật ở `.env` cục bộ, không đọc/ghi vào prompt hoặc báo cáo. Có phân quyền Google không thay kiểm mapping/pháp nhân của hệ thống. Việc này chưa kết nối trong khảo sát; thiếu quyền hoặc chưa xác nhận file đang dùng là cổng vận hành, không chặn code/test DEMO.
2. Không dùng nguyên Apps Script `load` làm payload kế toán. `apps-script-deploy/Code.js:233–282` trả cả `shortLoans`, danh mục, tỷ giá, cấu hình ngân hàng, dòng thủ công và yêu cầu xóa; `load` còn gọi `doLoadMaster`, hàm này gọi `ensureSheet` (`:629–637`). Vì vậy chưa chứng minh route đó là thao tác thuần đọc; không gọi app/source để “khảo sát thử”. Cả root và deploy còn có action ghi/xóa, bridge không được gọi các action này.
3. **JSON DEMO/offline:** `apps-script-deploy/Index.html:1807–1808` xuất `{version:6, exportedAt, ... longLoans, kheUoc, lichGoc, laiSuat, phatSinh, hopDongMua, vayNH, hanMuc, ...}`. Tên ngắn hạn ở JSON là **`vayNH`**, còn response `load` là **`vayNganHan`**; chỉ normalize qua profile khai báo. `version:6` không chứng minh khớp schema trên Google. Loại bỏ `seqS/seqL/shortLoans/rates/bankCfg/manualRows` khỏi canonical nghiệp vụ khi không được whitelist; raw đầy đủ chỉ ở kho cục bộ có quyền.
4. `exportExcel` (`apps-script-deploy/Index.html:1719–1756`) tạo **SpreadsheetML/XML đuôi `.xls`**, không phải `.xlsx` hay BIFF. Lịch gốc export **bỏ `maKheUoc`**, phát sinh bỏ `id`, bảng ngắn hạn bỏ `id` và một số cột deploy mới. File này hữu ích để xem nhưng không bảo toàn đủ khóa làm nguồn canonical cho mọi profile; không ép đọc bằng openpyxl/xlrd rồi coi lỗi parser là lỗi dữ liệu. Dùng Sheets/JSON có khóa đầy đủ cho gói đầu, không bắt Anh xuất lại file xem để nối lịch.
5. `exportLai` (`apps-script-deploy/Index.html:1760–1803`) có công thức Excel và mã/kỳ, nhưng dùng **dư nợ hiện tại** và mốc lãi suất **cuối cùng** của khế ước để lập cả khoảng tháng (`:1773`, `:1777–1780`); cutoff ngân hàng có fallback ngày 25 (`:1063`). Đây chưa phải bằng chứng lịch sử phân đoạn dư nợ/lãi suất theo kỳ hoặc cutoff đã duyệt. Không tính lại một engine cạnh nguồn để che khác biệt. Nhận kết quả nguồn với provenance và nhãn ước tính/chờ kiểm; cần bảng lãi/giấy báo ngân hàng hoặc bảng kế toán đã duyệt để dùng làm giá trị hạch toán khi chưa chứng minh đủ điều kiện.

### 3.1 Độ chính xác có thể đã mất trước khi bridge nhận

Hai backend ép các field trong `NUM_FIELDS` qua `num(v) → Number(v)`: root `Code.gs:59–60,199–208,670–673,819`; deploy `apps-script-deploy/Code.js:65–66,286–295,864–867,1096`. UI cũng parse số trước khi lưu: deploy `apps-script-deploy/Index.html:1509–1512,1538,1575–1576`; UI root có `loan-tracker.html:1250,1282–1283`. Export Excel gọi `num0 → Number` (deploy `:1756`, root `:1416`); JSON stringify xuất giá trị Number đang có trong RAM, không phục hồi chuỗi người dùng đã nhập. Google Sheets API bỏ qua `coerce` của Apps Script nhưng không đảo được mất mát đã xảy ra khi nhập/ghi vào sheet kiểu số.

**Decimal ở bridge chỉ tránh làm mất thêm chính xác của payload nhận được, không bảo đảm đúng giá trị ban đầu.** Nếu nguồn đã làm tròn, hash raw/typed cùng khớp cũng chỉ chứng minh cùng giá trị sau làm tròn. Không thêm số 0 hoặc suy lại chữ số đã mất từ tổng, lịch hay tỷ giá.

Profile cần khai báo **precision contract theo field**: currency/scale, đơn vị lãi suất/tỷ giá, encoding gốc (text exact hay Number), đường nhập/ghi/export đã biết, miền giá trị nguồn đã chứng minh đủ chính xác ở scale đó và nguồn bằng chứng khi vượt miền. Không lấy một ngưỡng “15 chữ số” áp cho mọi field: số nguyên qua Number phải kiểm giới hạn safe integer `2^53−1`, còn số thập phân cần kiểm scale và độ phân giải tại độ lớn tương ứng. Một Number hiện nhìn nguyên và dưới ngưỡng đó vẫn có thể xuất phát từ phần lẻ đã mất; payload đơn lẻ không cho phép phát hiện hết các trường hợp này.

Field ngoài miền được chứng minh, text đã đi qua Number không còn chứng cứ gốc, hoặc đối chiếu giấy báo/bảng đã duyệt cho thấy khác số → giữ raw và gắn **`SOURCE_PRECISION_UNPROVEN`** hoặc **`SOURCE_PRECISION_LOST`**, không tự duyệt/nâng Xanh/xuất hay dùng làm nhãn học. Hoàn thiện bằng chứng từ trường text exact hoặc hồ sơ gốc đã duyệt là bước xử lý gap cục bộ; không đổi quy trình đích thành xuất CSV tay, không sửa engine #9 trong bridge. Việc parse/hash/round-trip ở phía nhận vẫn phải test riêng; không được hạ dải hợp lệ của typed K2 để che giới hạn của nguồn.

## 4. Hợp đồng dữ liệu kế toán — typed, có phiên bản, không mất số

Envelope của adapter là **thiết kế cần triển khai**, không phải field sẵn có của #9. Dùng registry/manifest chung của lõi, không dựng format điều phối khác cho riêng vay:

| Nhóm | Field / điều kiện |
|---|---|
| Nguồn | `source_kind=SHEET_VAY`, `source_instance_id` ổn định, `contract_profile`, mã/hash source đã pin, transport, fingerprint header, phạm vi sheet/field; `source_instance_id` không là URL chứa token. |
| Snapshot | ID snapshot, hash bytes/raw từng file hoặc response, hash dữ liệu chuẩn hóa có kiểu, thời điểm bắt đầu/kết thúc lấy do server ghi, `exportedAt` nguồn nếu có, trạng thái đủ/thiếu/lỗi, phạm vi bao phủ. Không dùng cùng lỗi/tập rỗng làm đồng bộ thành công. |
| Mapping | Mapping có phiên bản `source_instance + congTy/congTyMua → phap_nhan`, nguồn ngân hàng → `ObjectID`, `duAn → ProjectID`, `maKV → hop_dong.ma_noi_bo/so_hop_dong`; khế ước liên kết đúng HĐ cha. Mã nguồn giữ nguyên; mã Junsky chỉ nhận từ danh mục đã duyệt. Không fuzzy tên, tự sinh mã hoặc dùng mã cùng tên của pháp nhân khác. |
| Số | Parse token JSON/Sheets thành Decimal/giá trị exact **của payload nhận** trước mọi hash; kiểm precision contract nguồn theo §3.1, không tuyên bố phục hồi số đã bị Number làm tròn. Giữ nguyên tệ, scale và số minor theo currency contract đã duyệt. VND không mặc định cho field thiếu tiền tệ; với bảng ngắn hạn phải tách VND và nguyên tệ đúng source. Phân biệt NULL/blank/0. Cấm NaN/Infinity, boolean-as-number, duplicate JSON key, số chuỗi phân cách không rõ locale và sai scale. |
| Ngày / kỳ | Ngày nghiệp vụ và hạn là date; lãi suất có ngày hiệu lực; timestamp nguồn giữ offset nếu có. Timestamp thiếu timezone/không hợp lệ không được tự xem là UTC. Thiếu ngày không tự lấy ngày import; thiếu kỳ không lấy tháng hiện tại. |
| Bằng chứng | Dòng sheet/khóa nguồn/hash snapshot; ngày/giá trị nguồn và trường đã map; liên kết hợp đồng/khế ước/mốc lãi/phát sinh. Row number chỉ là locator trong snapshot. `ghiChu/chiTiet` không tự biến thành rule kế toán hoặc nguồn học. |

API/UI phải truyền số exact bằng string/minor integer an toàn; không vòng qua JavaScript `Number` làm tròn rồi gửi lại. File soát phải giữ chính xác số lớn/nguyên tệ; tránh formula injection từ mã/ghi chú. Không làm tròn im lặng, không thu hẹp dải hợp lệ chỉ để test qua; quy tắc rounding kế toán là cấu hình được duyệt, không suy từ UI nguồn.

### 4.1 Namespace, revision và chống trùng

- Namespace tối thiểu: `(source_instance_id, phap_nhan_id, kind, source_key)`. HĐ dài hạn thêm `maKV`; khế ước thêm `maKV/maKheUoc`; kỳ gốc thêm `scope/kySo`; mốc lãi thêm `maKheUoc/apDungTuNgay`; phát sinh thêm `id`; ngắn hạn/LC thêm `id`. `soHD`, `soNhanNo`, ngày hay số tiền **không** thay khóa ổn định.
- Trong một snapshot: cùng khóa cùng nội dung → nhận một; cùng khóa khác nội dung → cách ly/xung đột có lý do. Tham chiếu cha phải cùng namespace/pháp nhân/currency hợp lệ; không cho trùng `maKheUoc` giữa hai HĐ rồi gán con tùy thứ tự.
- Nạp lại nội dung không đổi hoặc chỉ đổi thời điểm lấy → không thêm master/lịch/link/nghĩa vụ/bút toán; có thể thêm log lần lấy. Đổi dữ liệu có ý nghĩa → revision mới + vết before/after, giữ raw/version cũ. Hash nghiệp vụ không đưa timestamp lần sync vào để tạo revision giả; hash raw vẫn giữ đầy đủ bằng chứng.
- Chỉ khi duyệt revision mới mới đổi bản hiệu lực. Kỳ đã khớp/đã xuất/đã đối chiếu giữ nguyên liên kết; thay lịch không mở lại toàn bộ nghĩa vụ để trả/hạch toán lần hai. Đổi sau xuất cần việc điều chỉnh có căn cứ, không overwrite/hoàn tác lịch sử đã xuất.
- Nguồn không có full changelog hoặc trạng thái approval kế toán. Dòng vắng ở snapshot không tự là xóa/hủy/đã trả; snapshot thiếu/truncated không được retire cả danh mục. Ghi việc chờ xác minh, giữ bản cũ và không xóa file/bản ghi.

### 4.2 Ba thời điểm và cutoff

`business_date` lấy ngày nghiệp vụ thực của từng loại; `known_at` do lõi ghi lúc **lần đầu nhận được bằng chứng**; `eligible_at` chỉ có sau mapping/kiểm tra/phê duyệt cần thiết, theo TL38. `updatedAt`, `apDungTuNgay`, `exportedAt` nguồn không thay hai thời điểm sau và không cho người gửi backdate.

Lịch sửa hôm nay có hiệu lực hồi tố vẫn là tri thức biết hôm nay. Mốc lãi không có timestamp từng dòng không thể chứng minh đã biết trước 30/06/2026. Snapshot mới không làm sạch backtest cũ; những ca thiếu snapshot/approval trước cutoff phải ghi **chưa kiểm chứng**, không dùng nâng điểm. Có thể hoàn thiện DEMO/runtime M9 song song; không biến clean-cutoff của chấm điểm thành cổng ngăn mọi module.

## 5. Luồng bấm và nghiệp vụ được làm

**Nhận snapshot DEMO → kiểm profile/cột/khóa → master hợp đồng/khế ước/lịch chờ duyệt → kiểm mapping và số → CFO mô phỏng duyệt tham số → lịch trả nợ có phiên bản → nối dòng tiền M1 → giải thích chênh/đề xuất theo mẫu đã có căn cứ → file soát → đối chiếu lô/kỳ.**

Trong shell hiện có: thẻ nguồn “Khoản vay” hiển thị lần lấy, profile, đủ/thiếu/lỗi và số mới; mục master cho HĐ/khế ước/lịch/phiên bản; K5 nhận việc V3/V4/V8 và V1/V7 đúng loại. Chi tiết có chuỗi snapshot → HĐ/khế ước → kỳ/phát sinh → tiền → lô/đối chiếu, số nguồn/đã khớp/còn lại và lý do chờ. Form phải có label truy cập được. Không dựng trang app khoản vay thứ hai; không bắt Anh gõ lệnh hoặc sửa file Junsky thủ công.

### 5.1 L8 — gốc, giải ngân, lãi và phí nối M1

- Sao kê là sự kiện tiền; lịch và `PhatSinh` bổ sung căn cứ/đối tượng/phân bổ cho **cùng** sự kiện. Nhận nguồn trước hoặc sau sao kê đều chỉ tạo một sự kiện tiền logic. Nếu M1 đã có đề xuất/đã duyệt/đã xuất, việc nối không tạo khoản chi/thu và đề xuất 112 lần hai.
- Khóa HĐ/khế ước/tham chiếu rõ + pháp nhân/ngân hàng/currency/số tiền/kỳ phù hợp là bằng chứng khớp; chỉ ngân hàng + số tiền + tháng có thể nhiều ứng viên, không tự chọn Xanh. Mã trong diễn giải hoặc `soChungTu` là ứng viên cần đối chiếu, không bypass quyền/pháp nhân.
- Hỗ trợ một giao dịch tách gốc/lãi/phí, nhiều giao dịch cho một kỳ, một giao dịch cho nhiều kỳ và trả một phần qua link/phân bổ chung. Kiểm tổng phân bổ không vượt tiền khả dụng/nghĩa vụ còn lại, đồng tiền tương thích; số còn lại tính từ liên kết đang hiệu lực, không từ tổng `soDaTra` nguồn một cách máy móc.
- Mẫu đã nêu TL29: giải ngân 112/341, trả gốc 341/112; chỉ đề xuất sau khi có **TK chi tiết**, `ObjectID`, mã HĐ, mã dự án khi bắt buộc và bằng chứng. Không dùng TK tổng hợp hay sinh mã Junsky để vượt chặn.
- Lãi/phí thiếu căn cứ, trích lệch, trả sớm, thiếu lịch hoặc hai ứng viên → Vàng/Đỏ với lý do và việc bổ sung. Thao tác xác nhận/gỡ/đổi phân bổ, duyệt/xuất phải revalidate trong transaction; không tin trạng thái cũ trên client. Chặn duyệt/xuất kỳ khóa, double allocation và revision stale, giữ các lô đã xuất.

### 5.2 L7 / M10 — lãi dự trả, vốn hóa và actual rate

Chỉ nhận số lãi đã đủ căn cứ/đã được duyệt cùng phạm vi kỳ, HĐ/khế ước, dự án và phương pháp nguồn. Dữ liệu lịch gốc/mốc lãi là nguồn để đối chiếu, không tự là số lãi kế toán đã chốt. Không lấy `exportLai` mặc định đúng lịch sử, không tự tính lại/correct engine #9 trong bridge.

- Vốn hóa cần chính sách được duyệt có phiên bản, dự án/phạm vi, thời gian áp dụng, tỷ lệ/phân bổ và loại chi phí đủ điều kiện. Thiếu → **chờ chính sách**; không mặc định 100%, 0% hoặc tự chuyển hết 635 để làm ca đạt.
- Lãi dự trả cuối kỳ cần bảng/kết quả đã được duyệt, TK chi tiết và quy tắc tất toán/đảo khi tiền đến. Khóa nghĩa vụ `(pháp nhân, HĐ/khế ước, loại, kỳ, version căn cứ)` không được cho xuất trùng kỳ chỉ vì import mới; link tới M1 phải dùng phần dự trả đang hiệu lực để không ghi nhận lãi hai lần.
- Actual rate, ngày tính lãi, cutoff ngân hàng, cơ sở ngày, FX/tỷ giá ghi sổ/đánh giá cuối kỳ và rounding chưa có chính sách xác nhận → ghi thiếu/chờ, không dùng tỷ giá dashboard hoặc fallback ngày 25 làm chính sách CFO. Mẫu DEMO phải khai báo rõ giả định kỹ thuật, không ghi thành chính sách vận hành.

### 5.3 LC, bảo lãnh và đầu tư tài chính trong toàn M9

- **C4c:** nhận dạng hồ sơ LC/nhận nợ theo source; tách mở LC, ký quỹ, giải ngân/nhận nợ, trả ngân hàng, phí LC, phí bảo lãnh và giải tỏa. Không giả định mỗi trạng thái sinh tiền; nối từng sự kiện có chứng từ với M1. Mẫu TK/phân loại phí/ký quỹ/thuế cần chính sách đã duyệt trước đề xuất đủ điều kiện xuất. HĐ mua/hóa đơn M2 chỉ bổ sung chuỗi, không nhân nghĩa vụ do `maHDM` lặp nhiều dòng.
- **C4d:** đầu tư tài chính vẫn trong chương trình, nhưng #9 chưa chứng minh có register tiền gửi kỳ hạn/góp vốn hoặc lịch đầu tư. Codex kiểm kê sổ/hồ sơ **cục bộ**, chỉ trả bảng aggregate loại × số chứng từ × nguồn × đủ/thiếu; CFO xác nhận loại thực có và mẫu trước code từng nhánh. Không tự mặc định bao gồm chứng khoán/phái sinh/định giá hoặc dựng module trống gọi là hoàn tất. Lãi tiền gửi đã ở M1 phải nối cùng sự kiện, không tạo lãi lần hai; điều kiện tự duyệt chỉ có hiệu lực khi cổng mức 2 mở.
- Hạn mức/covenant/dashboard treasury không được thêm vào gói này. Bảo lãnh ở cây 33 là hồ sơ/phát sinh kế toán đúng căn cứ; không tự mở quản trị hạn mức bảo lãnh.

## 6. Bộ ca DEMO và bằng chứng bắt buộc

Fixture tự tạo đúng shape nguồn, chữ `DEMO`, hai pháp nhân và hai `source_instance_id` có mã nguồn trùng để kiểm namespace. Không sao chép row thật, không đọc Sheets thật để lấy ví dụ. Các số sau là **giả định test kỹ thuật**, không phải tỷ lệ/chính sách công ty: giải ngân VND `100000000`, kỳ gốc `20000000`, lãi đã xác nhận `800000`, phí đã xác nhận `50000`; một dòng sao kê tổng `20850000` được phân bổ đúng ba phần khi mẫu DEMO đã khai báo. Có ca nguyên tệ và số vượt 15 chữ số để kiểm exactness, không suy FX hoặc actual rate tự động.

| Ca | Kết quả cần chứng minh |
|---|---|
| Profile/header | Profile đã khóa nhận đúng; profile khác/sai header/trùng cột/mất field bắt buộc cách ly, không promote nửa snapshot; đảo cột vật lý vẫn đọc đúng theo tên. JSON `vayNH` và route `vayNganHan` không bị lẫn profile. |
| Khóa và số | Trùng key khác giá trị, orphan, cross-entity, currency sai/thiếu, boolean/NaN/duplicate JSON key, blank vs 0, decimal và số lớn qua raw → typed K2 → API/UI → file soát không đổi. Lịch chung và riêng khế ước không tạo nghĩa vụ kép. |
| Precision đã mất ở nguồn | Fixture tạo rõ hai tầng: chuỗi gốc DEMO và payload sau đường Number của nguồn, gồm `9007199254740993` thành `9007199254740992`, số thập phân có phần minor/scale không còn bảo toàn và hai chuỗi gốc khác nhau cho cùng payload. Không ghi test pass vì Decimal parse đúng payload đã sai; field thiếu bằng chứng precision phải ở trạng thái chờ, không xuất/khớp tự động. Có ca text exact lớn hợp lệ không đi qua Number vẫn giữ đầy đủ số, chứng minh typed K2 không bị thu hẹp theo giới hạn nguồn. |
| Đồng bộ | Nhận hai lần → 0 master/lịch/nghĩa vụ mới; chỉ đổi thời điểm lấy không tạo revision; đổi số/ngày/mốc lãi tạo revision mới chờ duyệt; mất row/partial response không tự hủy lịch. |
| Thời điểm | Nguồn backdate, lãi có hiệu lực trước cutoff nhưng mới nhận hôm nay → không đủ điều kiện học trước cutoff; không có snapshot đúng mốc thì báo chưa kiểm chứng. |
| L8 hai thứ tự | Nguồn trước tiền và tiền trước nguồn đều một sự kiện tiền; nhận thêm `PhatSinh`/HĐ mua không tăng số bút toán 112; tiền đã xuất vẫn nối được bằng chứng trong đúng quyền, không xuất lại. |
| Phân bổ | Gốc+lãi+phí tổng đúng; trả một phần/cùng kỳ nhiều lần/một tiền nhiều kỳ đúng số còn lại; vượt tổng, hai giao dịch tranh cùng phần còn lại, đồng thời duyệt/xuất, undo cũ sau revision đều bị chặn trong transaction. |
| Chính sách | Chưa có vốn hóa/actual rate/FX/TK chi tiết/mẫu LC → giữ chờ có lý do, không xuất mặc định; có policy DEMO phiên bản cụ thể mới ra kết quả expected. Lãi dự trả rồi trả tiền không nhân chi phí. |
| LC / bảo lãnh | Mở LC không tự là giải ngân; ký quỹ/phí/thanh toán nối đúng dòng tiền. Chỉ tổng `baoLanh/lcBl` không đủ sinh chứng từ. Case thiếu nguồn chi tiết được ghi gap thật. |
| Quyền / kỳ / lô | Role thực của lõi/app, RLS hai pháp nhân, server không tin client actor/entity; người nguồn không duyệt kế toán, CFO mô phỏng đúng V3; kỳ khóa chặn mutation; file soát chỉ gồm bản đã duyệt còn hiệu lực, mức 2 vẫn khóa. |
| Migration/runtime | DB PostgreSQL DEMO mới và upgrade DB có sẵn, chạy migration lặp giữ dữ liệu, FK/hash/checksum/audit; không chỉ test superuser. Không drop/recreate DB hoặc xóa output để vượt lỗi. |
| Bấm trên UI | Nhận → xem lỗi → xác nhận mapping → duyệt tham số → xem lịch → nối tiền → hoàn tác hợp lệ → file soát; kiểm label, số exact và tải file thật với timeout hữu hạn; thiếu trình duyệt thì ghi chưa kiểm, không thay bằng HTML grep. |

Claude tự chạy test phù hợp và ghi kết quả riêng; Codex/agent độc lập kiểm probe âm, database typed, workbook/cell thực và UI. Dùng chế độ giữ file/temp/database theo chỉ đạo không xóa. Test cần xóa vật lý phải ghi giới hạn kiểm thử và kiểm invariant tương đương, không tắt guard để làm xanh. Skip/tập rỗng/cùng lỗi không tính đạt; không dùng một ca DEMO hoặc test unit để tuyên bố tích hợp Google thật/hoàn thành M9.

## 7. Thứ tự giao Claude và trạng thái coverage

1. **M9-01:** sau CRM-01 được review, đọc API/repository chung thực, khóa profile DEMO; adapter nguồn dài hạn + master/khế ước/lịch typed + K5 + namespace/revision/ba thời điểm, kiểm PG/RLS và UI. Chưa cấp kết nối Google thật vẫn hoàn thiện gói này.
2. **M9-02:** L8 end-to-end qua link/phân bổ chung và M1 thực, gốc/lãi/phí, hai thứ tự nhận, exactness/concurrency/khóa kỳ/lô; không sinh tiền lần hai. Không dựng service tiền mới để né M1.
3. **M9-03:** LC/ngắn hạn/bảo lãnh theo source + hồ sơ còn thiếu và mẫu đã duyệt; L7/lãi dự trả/M10 theo policy đủ căn cứ. Phần thiếu chính sách giữ việc chờ cụ thể, không áp mặc định.
4. **M9-04:** kiểm kê local đầu tư tài chính → chốt nguồn/loại/mẫu → triển khai từng loại có nguồn và ca DEMO, nối M1/M10. Không loại C4d khỏi đích toàn chương trình.
5. **Cổng Google/vận hành:** xác định file/profile đang dùng, chủ cập nhật và đủ phạm vi khoản vay; service account readonly, snapshot đầy đủ, hết quyền/thay schema/lấy lỗi/retry/sync hai lần, audit và nút bấm. Kết nối mạng/khóa chưa cấp chỉ chặn bước vận hành này. Không chờ/cài lại PostgreSQL hoặc tối ưu kho tri thức vô hạn trước các gói nghiệp vụ đã đủ yêu cầu.

Mỗi gói cập nhật hàng đợi, báo cáo, CHANGELOG và coverage theo **yêu cầu → code/migration → test → bằng chứng độc lập → trạng thái**, giữ danh sách còn thiếu. Nghiệm thu một bridge không tự chuyển toàn M9, L7/L8/L12 hoặc toàn cây 33 sang đạt.

## 8. Gap thật cần hoàn thiện, không hỏi lại những gì source đã trả lời

| Cần có | Đã biết từ source | Phần còn cần lấy/xác nhận đúng lúc |
|---|---|---|
| Cấu trúc dài hạn | Năm sheet, mã HĐ/khế ước, lịch gốc và mốc lãi đã có | Profile/file đang dùng và header thực; lịch nguồn chung/riêng có ý nghĩa thế nào khi đồng thời xuất hiện. Không hỏi lại có bảng theo dõi vay hay không. |
| Mapping | Có `congTy`, `duAn`, `nganHang`, `maKV`, `soHD` | Danh mục Junsky và mapping có phiên bản/được duyệt; mã nguồn chưa chắc trùng mã kế toán. Không suy ngân hàng/công ty từ tên gần giống. |
| Precision nguồn | Backend/UI có đường Number/parseFloat; JSON/Sheets không tự khôi phục số gốc | Precision contract theo field/đường nhập; miền scale đã kiểm và bằng chứng gốc khi vượt miền hoặc nghi bị làm tròn. Decimal phía nhận không thay xác minh này. |
| Số lãi kế toán | Có `PhatSinh.traLai/phi`, mốc lãi và export tính lãi | Bằng chứng tính đúng theo kỳ/actual rate/cutoff và bảng lãi/giấy báo đã duyệt; nguồn lãi dự trả khi chưa thanh toán. |
| Vốn hóa / FX / LC | Có dự án, nguyên tệ và một số tỷ giá nguồn | Chính sách vốn hóa/phân bổ, tỷ giá ghi sổ/đánh giá, mẫu TK LC/ký quỹ/phí/bảo lãnh và hồ sơ chi tiết thiếu. |
| Đầu tư | Chỉ thấy vốn vay/LC/hợp đồng mua trong #9 đã kiểm | Aggregate kiểm kê loại đầu tư thực có, hồ sơ nguồn và mẫu được CFO chốt; chưa có bằng chứng triển khai. |

Các xác nhận nghiệp vụ mới gom từ gap thực sau khi đã kiểm kê local, không bắt Anh mô tả lại phần mềm #9. Quyền đọc mọi file/trang web không thay cổng gửi dữ liệu thật ra ngoài hoặc phê duyệt thật. Tài liệu này chứa duy nhất schema kỹ thuật, hash mã và fixture dự kiến; không có dòng dữ liệu vận hành.
