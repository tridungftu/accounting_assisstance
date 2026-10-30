# DAC-TA-API.md

**Lát:** G1b-1  
**Ngày:** 30/10/2026  
**Trạng thái:** Bản nháp để review và trình Anh duyệt; chưa cho phép lập trình.

## 1. Phạm vi, căn cứ và phần giữ lại

**Đề xuất:** Core cung cấp một API `/api/v1/`, quản lý phiên, kiểm quyền, tài liệu, tệp, kết quả, việc và vòng đời module/engine. Nghiệp vụ nằm dưới `/api/v1/module/{ma_module}/...`; mỗi module chạy một tiến trình riêng. Người dùng chỉ kết nối tới Core.

Tài liệu này gồm quy ước API, danh mục route nền, chuyển tiếp liên tiến trình, API quản trị, ba ví dụ và phụ lục OpenAPI. Bảng ánh xạ đầy đủ route cũ thuộc lát khác. Các route nghiệp vụ bổ sung phải có OpenAPI và JSON Schema riêng trong gói module trước khi đăng ký.

**Quy ước dẫn nguồn:** đường dẫn tính từ gốc repo; `../54-...` và `../55-...` là tài liệu tại thư mục cha. Các đoạn dưới nhãn **đề xuất** là thiết kế mới, không phải xác nhận đã triển khai.

| Căn cứ | Ý nghĩa đối với đặc tả |
|---|---|
| `../54-ke-hoach-core-database-api-v1.md:157` | Tiền tố v1, phiên, schema, chống trùng, 202, 409 và phân trang. |
| `../54-ke-hoach-core-database-api-v1.md:255` | Registry, hồ sơ chạy, readiness, trạng thái và quyền sở hữu tiến trình. |
| `../54-ke-hoach-core-database-api-v1.md:290` | Dispatcher, kiểm quyền backend, file store, việc bền vững và audit. |
| `../55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:26` | Tên nhóm API, lỗi tiếng Việt, `viec_id`, OpenAPI và chuyển tiếp route cũ. |
| `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:326` | CD-028: cổng cố định, chuyển giao ổ nghe, tiến trình riêng, đo và đề xuất hằng tuần. |
| `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:338` | Ba phiếu CSDL/API/SDK phải được Anh duyệt trước G2. |

**Hiện trạng cần tận dụng:** shell đã có kiểm Host/Origin/token, nhưng token dùng chung ứng dụng; phiên CRM hiện là danh tính DEMO trong RAM (`src/kho_tri_thuc/giao_dien/server.py:918`, `src/kho_tri_thuc/giao_dien/server.py:193`). Báo giá đã kiểm `expected_revision` và trả các lỗi xung đột; giữ kiểm nghiệp vụ này khi bổ sung `row_version` (`src/kho_tri_thuc/giao_dien/crm_g.py:75`, `src/kho_tri_thuc/giao_dien/crm_g.py:83`). Hàng việc có nền tạo/chống trùng trong transaction và yêu cầu dừng (`src/kho_tri_thuc/ha_tang/hang_viec.py:21`, `src/kho_tri_thuc/ha_tang/hang_viec.py:69`).

KS-A xác định Dispatcher còn gọi trực tiếp trong tiến trình, chưa thành proxy liên tiến trình (`docs/47-core/g0/KS-A.md:18`). KS-C ghi nhận lỗi, phân trang, tải tệp và việc lâu chưa thống nhất (`docs/47-core/g0/KS-C.md:162`). Readiness hiện chưa thử nạp/inference; revision, duyệt và lưu RAM có vòng đời riêng (`docs/47-core/g0/KS-D.md:47`, `docs/47-core/g0/KS-E.md:110`, `docs/47-core/g0/KS-E.md:112`, `docs/47-core/g0/KS-E.md:113`, `docs/47-core/g0/KS-E.md:114`, `docs/47-core/g0/KS-E.md:116`).

Tên route giữ gạch nối đúng handoff và TL 55 §2; tên trường JSON dùng tiếng Việt không dấu, `snake_case`. Giữ các tên kỹ thuật đã được yêu cầu hoặc chuẩn hóa: `module`, `engine`, `row_version`, `request_id`, tên header, trạng thái tiến trình/việc và từ khóa OpenAPI.

**Phụ thuộc CSDL:** dùng bản vòng 2, vẫn chờ duyệt; danh tính/ủy nhiệm theo `docs/47-core/g1/DAC-TA-CSDL.md:135`, login theo `docs/47-core/g1/DAC-TA-CSDL.md:257`, xác minh transaction theo `docs/47-core/g1/DAC-TA-CSDL.md:291`. Đây là thiết kế đích; không xác nhận đã triển khai. Biên nhận nghiệp vụ tuân mẫu K2 tại `src/kho_tri_thuc/ha_tang/pg_migrations.py:3385`.

**Căn cứ hiệu chỉnh vòng 2:** `O` = `docs/47-core/g1/RV-G1B-OPUS.md`; `R` = `docs/47-core/g1/RV-G1B.md`; `D` = `docs/47-core/g1/DAC-TA-CSDL.md`. Dẫn `O:19`/`R:10`/`D:301` là `tệp:dòng`; cũng áp dụng cho `x-can-cu` và bảng xử lý cuối tệp. Đề xuất mới dưới đây viện dẫn yêu cầu thiết kế, không coi review là bằng chứng runtime.

## 2. Quy ước chung

### 2.1. Phiên, xác thực, Origin và CSRF

**Đề xuất:**

- Core là đầu mối xác thực. Nguồn đăng nhập hỏi chung ở phiếu CSDL, không hỏi lại tại API (`O:50`).
- Cookie phiên `__Host-ktt_phien`: `Secure; HttpOnly; SameSite=Strict; Path=/`, không có `Domain`. SID ngẫu nhiên; kho phiên dùng chung, có thu hồi và không lưu SID nguyên văn.
- TLS là điều kiện phục vụ ngoài loopback; `http://<IP LAN>` không phải cấu hình đăng nhập hợp lệ với cookie này. DEMO loopback vẫn tách riêng, chỉ dữ liệu giả; không bỏ `Secure` cho LAN (`O:21`).
- Phiên hết hạn sau 30 phút không hoạt động hoặc 8 giờ tuyệt đối. Đăng nhập thành công đổi SID và CSRF token; đăng xuất thu hồi phiên tại backend.
- `GET /phien` trả trạng thái phiên và CSRF token. Khi chưa đăng nhập, cấp cookie tiền phiên `__Host-ktt_tien_phien`, hiệu lực 10 phút.
- Mọi thao tác ghi, gồm đăng nhập/đăng xuất, phải có `Origin` đúng nguồn Core và `X-CSRF-Token` gắn với phiên hoặc tiền phiên. Thiếu hoặc sai trả 403.
- Kiểm Host theo cấu hình triển khai; từ chối `Sec-Fetch-Site: cross-site`; không bật CORS tùy ý. GET không thực hiện lệnh nghiệp vụ hoặc khởi động việc.
- API người dùng v1 trong tài liệu này dùng cookie. Danh tính dịch vụ và kênh nội bộ tách riêng; không dùng khóa engine thay phiên người dùng.

### 2.2. Ngữ cảnh pháp nhân và quyền

Client chọn pháp nhân bằng header **`X-Phap-Nhan-Id`** trên từng request thuộc dữ liệu pháp nhân. Không dùng “pháp nhân đang chọn” trong một biến toàn cục hoặc đổi ngầm theo tab trình duyệt.

Core xác thực phiên rồi kiểm đồng thời: thành viên pháp nhân, quyền người dùng/MTQ, quyền module, quyền thao tác, quyền hồ sơ, trường và biến thể nội dung. `actor`, vai trò hoặc pháp nhân tự khai trong body không tạo quyền.

- Tài liệu, tệp, báo giá và việc nghiệp vụ phải thuộc đúng pháp nhân đã kiểm.
- Module dùng mã ủy nhiệm bí mật do Core cấp, không dùng SID; hàm CSDL xác minh mã rồi mới đặt/đối chiếu ngữ cảnh transaction. GUC danh tính tự khai không tạo thẩm quyền; không để pool mang ngữ cảnh request trước (`D:301`, `O:19`).
- Download kiểm lại quyền trước khi mở luồng bytes; không chỉ kiểm đường dẫn.
- Việc nền lưu người tạo, pháp nhân, module và phiên bản contract; kiểm lại quyền khi nhận việc, trước bước nhạy cảm, trước ghi và trước công bố kết quả. Không chạy bằng quyền toàn hệ thống khi người tạo mất quyền.
- Việc, kết quả và tệp quản trị toàn hệ thống có `phap_nhan_id: null`, chỉ Admin hệ thống truy cập, không gắn giả một pháp nhân. Route đọc theo ID chỉ được bỏ header cho tài nguyên hệ thống; tài nguyên nghiệp vụ bắt buộc header khớp. Tệp hệ thống có `tai_lieu_id: null`, do chức trách quản trị Core tạo hoặc Admin upload gói; không dùng `null` để bỏ qua quyền dữ liệu nghiệp vụ (`R:11`, `D:303`).
- Khi tài nguyên nằm ngoài phạm vi được thấy, trả 404; không tiết lộ sự tồn tại của hồ sơ pháp nhân khác.

Lời gọi engine/quy trình có header `X-Module-Ma`; Core kiểm module được cấp quyền và quyền của người gọi. Header này là lựa chọn ngữ cảnh, không phải bằng chứng thẩm quyền.

### 2.3. JSON, lỗi và mã HTTP

JSON dùng UTF-8, kiểm schema trước xử lý; từ chối trường không khai báo. Không ép kiểu ngầm từ chuỗi sang boolean/số. Mọi response có `X-Request-Id`; Core sinh UUID và truyền xuyên tiến trình, việc, bước, lần thử.

Dạng lỗi duy nhất:

```json
{
  "ma": "XUNG_DOT_PHIEN_BAN",
  "thong_diep": "Dữ liệu đã được người khác cập nhật. Anh tải lại trước khi lưu.",
  "request_id": "10000000-0000-4000-8000-000000000099",
  "thu_lai_duoc": false
}
```

Thông điệp tiếng Việt; không chứa SQL, DSN, khóa, cookie, header xác thực, đường dẫn vật lý hoặc toàn văn tài liệu. Stack trace chỉ ở log được kiểm soát, đã loại dữ liệu nhạy cảm.

`chi_tiet` tùy chọn có dạng `[{"truong":"ten","ma":"BAT_BUOC"}]`: chỉ tên trường đã khai trong schema và mã lỗi, không có giá trị đầu vào. Mã lỗi/HTTP của module phải khai trong contract đã đăng ký; mã chưa khai hoặc payload sai trả 502 `PHAN_HOI_SAI_CONTRACT`, không chuyển lỗi thô (`O:16`).

| HTTP | Sử dụng |
|---|---|
| 200 / 201 / 204 | Đọc/cập nhật; tạo tài nguyên đồng bộ; đăng xuất không body. |
| 202 | Đã ghi bền vững việc hoặc đề nghị hủy; chưa khẳng định hoàn thành. |
| 400 | JSON/header/cursor thiếu hoặc sai cú pháp. |
| 401 | Chưa đăng nhập, phiên hết hạn hoặc bị thu hồi. |
| 403 | Sai Origin/CSRF hoặc thiếu quyền thao tác đã được phép biết. |
| 404 / 405 | Không thấy tài nguyên/route; method không hỗ trợ, kèm `Allow`. |
| 409 | `row_version`/CAS cũ; trạng thái không cho phép; khóa chống trùng khác nội dung hoặc còn xử lý. |
| 410 | Tệp/kết quả tạm đã hết hạn; chỉ trả sau kiểm quyền. |
| 413 / 415 / 422 | Quá giới hạn; MIME không hỗ trợ; vi phạm schema/nghiệp vụ. |
| 429 | Vượt hạn mức hoặc hàng đợi đầy; có `Retry-After`. |
| 500 | Lỗi nội bộ đã làm sạch. |
| 502 | Tiến trình/adapter trả dữ liệu hoặc protocol không hợp lệ. |
| 503 | Chưa sẵn sàng, khởi động lỗi, xung đột cổng hoặc thiếu chính sách bắt buộc. |
| 504 | Hết thời hạn chờ phản hồi từ tiến trình phụ thuộc. |

`thu_lai_duoc` chỉ phản ánh khả năng thử lại an toàn. Với ghi chưa rõ kết quả, không khuyến nghị tạo request mới; dùng lại cùng khóa để đối chiếu.

### 2.4. Khóa chống trùng và cập nhật đồng thời

Header **`Idempotency-Key`** bắt buộc cho POST/PATCH/PUT nghiệp vụ và quản trị; ngoại lệ đăng nhập/đăng xuất. Giá trị 16–128 ký tự ASCII an toàn, không chứa dữ liệu nghiệp vụ.

**Quyền sở hữu biên nhận** (`O:31`, `src/kho_tri_thuc/ha_tang/pg_migrations.py:3385`):

- Operation do Core sở hữu: Core ghi biên nhận cùng transaction thay đổi dữ liệu hoặc tạo việc. Phạm vi người dùng × pháp nhân/phạm vi hệ thống × module × operation × khóa. Chỉ biên nhận Core có thời hạn đề xuất 24 giờ từ kết quả cuối; giữ tiếp khi việc còn hoạt động hoặc kết quả chưa xác định.
- Operation nghiệp vụ `/module/*`: Core chỉ khóa request đang chạy, chuyển nguyên `Idempotency-Key` trong token ký. Module qua SDK giữ biên nhận **vĩnh viễn, bất biến**, cùng transaction nghiệp vụ/tạo việc qua hàm CSDL Core V2 trên chính kết nối đó (không commit việc riêng bằng HTTP); Core không ghi bản biên nhận hoàn tất thứ hai. Namespace metadata `/module` do Core sở hữu không thuộc quy tắc ghi nghiệp vụ này.
- Module giữ UNIQUE `(phap_nhan_id, module, operation, client_key)` theo K2, lưu người tạo; kiểm quyền hành động **trước** tra biên nhận và quyền đọc kết quả của người gọi **trước** phát lại, kể cả người tạo khác. Không có quyền thấy kết quả thì 404 (`src/kho_tri_thuc/k2/crm_mau.py:5`, `src/kho_tri_thuc/k2/crm_mau.py:160`, `O:35`).
- Fingerprint = mã operation ổn định + body chuẩn hóa; body logic bao gồm ID tài nguyên đích/pháp nhân và hash bytes tệp nếu có. Không gồm đường dẫn, method hay chính khóa; alias và v1 chuẩn hóa về cùng operation/body/khóa. Ràng buộc method/path trong chữ ký vận chuyển ở §4.2 độc lập với fingerprint chống trùng (`O:34`, `src/kho_tri_thuc/k2/crm_mau.py:7`).
- Cùng khóa/cùng fingerprint: trả lại kết quả hoặc cùng `viec_id`; vẫn kiểm phiên/quyền hiện tại. Sau 504/crash, biên nhận **module** là nguồn đối chiếu duy nhất cho operation module; mất khóa đang chạy tại Core không cho phép bỏ kiểm biên nhận (`O:33`).
- Cùng khóa/khác fingerprint: 409 `KHOA_CHONG_TRUNG_KHAC_NOI_DUNG`.
- Đang ghi đồng bộ: 409 `YEU_CAU_DANG_XU_LY`, `Retry-After: 2`.
- Tác động ngoài CSDL phải có cơ chế đối chiếu; không tuyên bố exactly-once. Hết thời hạn biên nhận Core không cho phép ghi trùng nghiệp vụ; tuyệt đối không áp 24 giờ để dọn biên nhận module (`O:36`).

`row_version` truyền dưới dạng **chuỗi số nguyên**, tránh mất chính xác trong JavaScript; cập nhật so sánh và ghi nguyên tử, lệch trả 409. Giữ thêm CAS nghiệp vụ như `expected_revision`, hash căn cứ hoặc phiên bản mẫu khi operation cần; không tự đồng nhất chúng với `row_version`.

Mỗi operation khai trường CAS bắt buộc; PATCH ghi chú báo giá yêu cầu cả `row_version` lẫn `expected_revision`, lệch một trong hai trả 409 (`O:46`, `src/kho_tri_thuc/giao_dien/crm_g.py:75`).

### 2.5. Phân trang, thời gian, số tiền và phiên bản

Danh sách dùng `kich_thuoc_trang` mặc định 25, tối đa 100; `con_tro` opaque. Response gồm `danh_sach`, `con_tiep`, `con_tro_tiep`; không bắt buộc đếm tổng. Sắp xếp ổn định theo khóa công bố của tài nguyên và khóa duy nhất. Cursor gắn với người dùng, pháp nhân, bộ lọc, thứ tự; đề xuất TTL 15 phút. Đây không phải snapshot bất biến; quyền luôn kiểm theo thời điểm đọc.

ID nghiệp vụ là UUID. Thời điểm dùng RFC 3339 có múi giờ, response chuẩn UTC `Z`; ngày nghiệp vụ `YYYY-MM-DD`. Tiền dùng chuỗi decimal và `don_vi_tien`, không dùng float; schema từng trường xác định độ chính xác, giới hạn và cách làm tròn. Giao diện mới định dạng theo người dùng.

Đường dẫn `/api/v1/` là major version. Thay đổi phá contract phải mở major mới hoặc operation mới; không âm thầm đổi schema đang được ghim. Phiên bản module, quy trình, capability và adapter được ghi trong lần chạy. Core và module cùng kiểm input/output bằng JSON Schema 2020-12.

### 2.6. Việc lâu, tải lên và tải xuống

Việc lâu trả **202 + `viec_id` + `Location: /api/v1/viec/{id}`**, chỉ sau khi commit việc và biên nhận. Frontend poll theo `Retry-After`, mặc định 2 giây.

Trạng thái việc: `queued/running/waiting_input/cancel_requested/cancelled/succeeded/failed/interrupted`. Hủy là đề nghị hợp tác; không hoàn tác tác động đã commit. Gửi lại đề nghị cho việc đã kết thúc trả cùng trạng thái cuối. `succeeded` không đồng nghĩa kết quả đã được phê duyệt.

Sau restart Core hoặc hết lease, việc `running` mất heartbeat chuyển `interrupted`, không suy thành `succeeded`. Chỉ xếp lại nếu contract khai thử lại an toàn, đã đối chiếu tác động/biên nhận và kiểm quyền; thu hồi mã ủy nhiệm thế hệ cũ, tạo lần thử và mã mới. Việc ghi/nhập chưa rõ kết quả phải đối chiếu hoặc chờ xử lý, không chạy lại mù (`O:18`, `D:301`, `D:315`).

Theo dõi dùng polling; v1 này không công bố SSE. `GET /viec` lọc `ma_module`, `trang_thai`, phân trang và chỉ trả việc người tạo còn quyền xem hoặc có MTQ `viec.giam_sat` theo đúng pháp nhân + module; việc hệ thống chỉ Admin. Không có quyền xem việc người khác thì GET theo ID trả 404; danh sách loại dòng đó. Mất kết nối thì đọc lại snapshot, không cam kết phát lại sự kiện (`O:18`, `R:10`).

Upload qua `multipart/form-data`, không base64 trong JSON; metadata có schema. **Đề xuất:** JSON tối đa 1 MiB, tệp tối đa 20 MiB và tiếp tục chịu giới hạn nhỏ hơn của capability. Nhận vào vùng tạm, kiểm kích thước/MIME thực/hash/quyền trước công bố; kiểm nội dung lâu chuyển thành việc riêng. Chưa hỗ trợ chia mảnh hoặc tiếp tục upload.

Download dùng ID, không nhận đường dẫn hoặc URL tùy ý. Frontend gọi bằng `fetch` với cookie và header pháp nhân rồi tải blob. Trả `Content-Disposition: attachment`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`; tên tệp được làm sạch. V1 chưa hỗ trợ Range.

Kết quả tải theo hai bước: GET `/ket-qua/{id}` lấy `tep_id`, rồi GET `/tep/{tep_id}/noi-dung`; không có `/ket-qua/{id}/noi-dung`. Core giữ quan hệ kết quả–tệp, kiểm lại quyền kết quả/biến thể khi tải; tệp hệ thống chỉ Admin, bỏ header pháp nhân. Module sinh DOCX/báo cáo phải ghi qua SDK vào File Store Core, đăng ký metadata/quan hệ trước công bố; Core không proxy bytes thô từ module (`O:21`, `R:10`, `R:11`).

Retention theo loại dữ liệu phải được duyệt; chưa cấu hình chính sách thì từ chối tiếp nhận tương ứng. Không tự biến dữ liệu RAM-only của OCR/Mask thành lưu lâu dài. API kết quả trong lát này trả **metadata và tham chiếu tệp**; cấu trúc nội dung JSON bên trong tệp theo các contract của phiếu SDK.

## 3. Danh mục route

Trong bảng, mọi đường dẫn trừ health được đặt sau `/api/v1`. **ĐB** = đồng bộ; **202** = việc bền vững. Quyền là mã đề xuất, phải ánh xạ MTQ hiện có trước triển khai.

| Method · đường dẫn | Mục đích | Quyền/phạm vi | Kiểu |
|---|---|---|---|
| GET `/phien` | Trạng thái phiên, cấp CSRF/tiền phiên | Công khai, không lộ danh tính khi chưa đăng nhập | ĐB |
| POST `/phien` | Đăng nhập | Tiền phiên + CSRF + Origin | ĐB |
| DELETE `/phien` | Thu hồi phiên | Phiên + CSRF + Origin | ĐB, 204 |
| GET `/toi` | Danh tính và quyền hiệu lực | Phiên | ĐB |
| GET `/phap-nhan` | Pháp nhân được phép chọn | Phiên/thành viên | ĐB |
| GET `/tai-lieu` | Danh sách theo quyền | `tai_lieu.doc`, pháp nhân | ĐB |
| POST `/tai-lieu` | Tạo tài liệu từ tệp đã nhận | `tai_lieu.tao`, quyền tệp | ĐB, 201 |
| GET `/tai-lieu/{id}` | Metadata tài liệu | `tai_lieu.doc`, quyền hồ sơ | ĐB |
| PATCH `/tai-lieu/{id}` | Sửa tên, kiểm `row_version` | `tai_lieu.sua`, quyền hồ sơ | ĐB |
| POST `/tep` | Nhận một tệp | `tep.tai_len`; gói module cần Admin | ĐB, 201 |
| GET `/tep/{id}` | Metadata tệp | `tep.doc`, đúng biến thể | ĐB |
| GET `/tep/{id}/noi-dung` | Tải bytes | `tep.tai_xuong`, quyền nội dung | ĐB, stream |
| GET `/ket-qua/{id}` | Metadata/provenance kết quả | `ket_qua.doc`, đúng biến thể | ĐB |
| GET `/module` | Module được phép dùng tại pháp nhân | Quyền module/MTQ | ĐB |
| GET `/module/{ma_module}` | Khai báo module được phép thấy | Quyền module/MTQ | ĐB |
| GET `/engine` | Năng lực được phép dùng | Quyền capability/pháp nhân | ĐB |
| GET `/engine/{ma_engine}` | Năng lực, giới hạn và trạng thái | Quyền capability | ĐB |
| POST `/engine/{ma_engine}/viec` | Gửi lệnh có schema qua Core/adapter | `engine.goi` + quyền module/dữ liệu | 202 |
| GET `/quy-trinh` | Quy trình được phép chạy | `quy_trinh.doc`, pháp nhân | ĐB |
| POST `/quy-trinh/{id}/lan-chay` | Chạy phiên bản quy trình đã ghim | `quy_trinh.chay` + quyền module | 202 |
| GET `/viec` | Danh sách việc, lọc module/trạng thái, phân trang (`R:10`) | Chủ việc còn quyền hoặc MTQ `viec.giam_sat` theo pháp nhân + module; hệ thống chỉ Admin (`O:18`) | ĐB |
| GET `/viec/{id}` | Theo dõi snapshot việc | Chủ việc còn quyền hoặc MTQ `viec.giam_sat` theo pháp nhân + module; ngoài quyền → 404 (`O:18`) | ĐB |
| GET `/viec/{id}/ket-qua` | Danh sách metadata kết quả | Quyền việc và từng kết quả | ĐB |
| POST `/viec/{id}/huy` | Ghi đề nghị hủy | Chủ việc có quyền hủy hoặc quản trị phù hợp | 202 |
| GET `/quan-tri/module` | Registry module | Admin hệ thống | ĐB |
| POST `/quan-tri/module/{ma_module}/thao-tac` | Kiểm gói, cài/nâng cấp, khởi động/dừng | Admin hệ thống | 202 |
| GET `/quan-tri/module/{ma_module}/che-do` | Đọc công tắc/người thử/phiên bản (`R:10`) | Admin pháp nhân hoặc hệ thống | ĐB |
| PATCH `/quan-tri/module/{ma_module}/che-do` | Đổi `TAT/THU/VAN_HANH`, người thử | Admin pháp nhân hoặc hệ thống | ĐB |
| GET `/quan-tri/engine` | Registry engine | Admin hệ thống | ĐB |
| POST `/quan-tri/engine` | Đăng ký engine từ hồ sơ chạy đã duyệt | Admin hệ thống | ĐB, 201 |
| GET `/quan-tri/engine/{ma_engine}/ho-so-chay` | Đọc hồ sơ an toàn và phiên bản (`R:10`) | Admin hệ thống | ĐB |
| PUT `/quan-tri/engine/{ma_engine}/ho-so-chay` | Đổi hồ sơ/chính sách, kiểm phiên bản | Admin hệ thống | ĐB |
| POST `/quan-tri/engine/{ma_engine}/thao-tac` | Kiểm tra, khởi động hoặc dừng | Admin hệ thống | 202 |
| GET `/quan-tri/cap-quyen/{ma_module}` | Quyền thực cấp cho module | Admin pháp nhân/hệ thống | ĐB |
| PUT `/quan-tri/cap-quyen/{ma_module}` | Thay quyền thực cấp, kiểm phiên bản | Admin đúng phạm vi; không tự vượt quyền | ĐB |
| GET `/quan-tri/so-do` | Số đo theo module/engine và khoảng ngày | Admin hệ thống | ĐB |
| GET `/quan-tri/de-xuat-che-do` | Đề xuất tuần và căn cứ | Admin hệ thống | ĐB |
| POST `/quan-tri/de-xuat-che-do/{id}/ap-dung` | Admin áp dụng đề xuất cụ thể | Admin hệ thống, CAS cấu hình | ĐB |
| GET `/module/crm/bao-gia/{id}` | Đọc ghi chú và phiên bản báo giá | `crm.bao_gia.doc`, quyền hồ sơ | ĐB |
| PATCH `/module/crm/bao-gia/{id}` | Lưu ghi chú, kiểm hai phiên bản | `crm.bao_gia.sua`, quyền hồ sơ | ĐB |
| GET `/healthz` | Core còn sống | Công khai, thông tin tối thiểu | ĐB |
| GET `/readyz` | Core đủ nền phục vụ | Công khai, thông tin tối thiểu | ĐB |

`/module/{ma_module}/...` là **namespace đăng ký**, không phải route wildcard chấp nhận operation tùy ý. Hai route báo giá trên là contract tối thiểu cho ví dụ CAS, không thay toàn bộ API báo giá. Những route CRM/M4/M2 khác phải được khai báo riêng; không chuyển toàn bộ nghiệp vụ vào Core.

## 4. Dispatcher và chuyển giao tiến trình

### 4.1. Luồng phục vụ

1. Core xác thực, kiểm Origin/CSRF nếu ghi, pháp nhân, quyền, route/schema/version. Operation Core tra biên nhận Core; operation module chỉ khóa request đang chạy, biên nhận do module kiểm trong transaction (§2.4; `O:31`).
2. Dispatcher tra registry bằng mã module, không dùng host/cổng do client gửi. Chỉ chuyển route đã đăng ký; tách rõ route metadata Core và route nghiệp vụ.
3. Module chưa chạy: khóa phối hợp theo module/node; các request dùng chung một lần khởi động.
4. Core giữ cổng cố định trong sổ cổng `loi`, **theo phiếu CSDL**. Khởi động headless từ hồ sơ đã duyệt; chuyển ổ nghe qua kênh khởi động riêng.
5. Kiểm instance ID, process identity gồm thời điểm tạo, phiên bản, contract và readiness. Có TCP listener chưa đủ để đánh dấu `ready`.
6. Khi sẵn sàng mới chuyển request; kiểm schema response, chuẩn hóa lỗi và giữ `request_id`.
7. Khi dừng: lấy cùng khóa với dispatch, đổi `dang_dung`, ngừng nhận request/việc mới và chờ bàn giao. Đếm cả request đồng bộ, lease, download/kết quả đang dùng; chỉ thu hồi accept và trả ổ nghe cho Core khi drain xong. Request đến lúc `dang_dung` trả 503 `TIEN_TRINH_DANG_DUNG`, `Retry-After: 2`, chưa chuyển nên được thử lại cùng khóa (`O:20`).

Engine dùng cùng nền vòng đời nhưng lời gọi capability đi qua adapter; không proxy nguyên URL engine cho trình duyệt.

### 4.2. Ngữ cảnh liên tiến trình

**Báo kỹ thuật:** dùng token ngữ cảnh ký; không coi loopback là danh tính; không cần Anh chọn lại cơ chế này (`O:22`).

Core loại header nội bộ do client tự gửi, tạo token TTL tối đa 30 giây chứa: bên phát hành, module nhận/instance, người dùng, **mã ủy nhiệm bí mật (không phải SID)**, pháp nhân hoặc phạm vi hệ thống, module nguồn, operation, `Idempotency-Key` nếu ghi, `request_id`, thời điểm phát hành/hết hạn, nonce và hash method/đường dẫn/body. Mã ủy nhiệm ràng buộc login nhận + module + pháp nhân + hạn + phạm vi hành động (`O:19`, `O:33`, `D:135`, `D:301`).

Khóa ký chỉ Core giữ; module nhận khóa kiểm chứng qua kênh bootstrap được bảo vệ. Module kiểm chữ ký, đối tượng nhận, thời hạn, nonce và ràng buộc request. Không chuyển cookie người dùng hoặc khóa engine sang module.

Token không thay kiểm quyền hiện hành. Hàm `SECURITY DEFINER` băm mã ủy nhiệm rồi đối chiếu `loi.phien_xac_thuc`: hạn/thu hồi, `session_user`, module, pháp nhân, hành động. Runtime không SELECT/DML bảng phiên; GUC người dùng/ngày hiệu lực chỉ để đối chiếu, không thể tự đặt thành danh tính khác. Việc nền dùng mã riêng gắn `viec_id` + thế hệ lease, được cấp lại sau kiểm quyền, không lưu token HTTP để dùng về sau (`D:135`, `D:301`, `O:19`).

Mỗi instance nhận credential SDK riêng cùng instance ID qua stdin/handle kế thừa được bảo vệ, cùng kênh bootstrap `fromshare`. Core xác thực credential + instance đang sống trên mỗi lời gọi SDK, thu hồi khi dừng/crash; không đưa credential/mã ủy nhiệm/mật khẩu vào biến môi trường, dòng lệnh, manifest, response công khai hoặc log. Login CSDL module cũng trao qua kênh này, không dùng credential SDK thay mật khẩu CSDL (`O:19`, `D:267`).

| Tiến trình | Login CSDL / đường truy cập đích (`D:257`) |
|---|---|
| Core, worker Core nội bộ | `dang_nhap_loi`, chỉ các role runtime Core đã cấp |
| Module X | `dang_nhap_mod_x`, chỉ runtime riêng + EXECUTE/SELECT contract đã cấp; mã ủy nhiệm phải khớp login |
| Adapter kế toán chuyển tiếp | `dang_nhap_ke_toan_cu`, không dùng làm login chung module |
| Engine, worker máy phụ | **Không có login CSDL**, chỉ kéo việc/đầu vào và trả kết quả qua API Core với ủy nhiệm đúng việc |
| Cài đặt/bảo trì | `dang_nhap_cai_dat`, chỉ chức trách bảo trì, không xử lý request nghiệp vụ |

Membership runtime kế thừa quyền hữu hạn, `SET FALSE, ADMIN FALSE`, không owner/BYPASSRLS; máy phụ không nhận mật khẩu CSDL hay khóa mã hóa (`D:265`, `D:267`, `D:315`).

### 4.3. Thời hạn và lỗi

**Ngưỡng đề xuất, chưa phải số đo hiệu năng:**

| Tình huống | Giới hạn và phản hồi |
|---|---|
| Request đồng bộ | Deadline 30 giây, gồm chờ module khởi động và xử lý. |
| Khởi động một instance | Hồ sơ được cấu hình 1–120 giây; mặc định 120 giây. |
| Hết 30 giây khi chưa chuyển request | 503 `MODULE_DANG_KHOI_DONG`, `Retry-After: 2`; khởi động có thể tiếp tục trong giới hạn instance. |
| Hết hạn khởi động | `failed`; 503 `KHOI_DONG_QUA_HAN`. |
| Đang drain | 503 `TIEN_TRINH_DANG_DUNG`, `Retry-After: 2`, không chuyển request (`O:20`). |
| Đã chuyển request nhưng hết deadline | 504 `PHAN_HOI_QUA_HAN`; đối chiếu bằng cùng khóa, không tự ghi lại. |
| Sai danh tính/phiên bản/readiness | Không chuyển tiếp; 503 `TIEN_TRINH_KHONG_HOP_LE`. |
| Response sai contract | 502 `PHAN_HOI_SAI_CONTRACT`; không trả payload thô. |
| Cổng bị ứng dụng khác chiếm | 503 `CONG_BI_CHIEM`; không dừng ứng dụng lạ. |

Lệnh đã thiết kế là việc lâu được ghi việc và trả 202 ngay; worker khởi động engine/module sau. Không đổi một request ghi đang dở thành 202 khi chưa có bản ghi việc bền vững.

Đề xuất chống vòng khởi động lỗi: giãn 2/4 giây sau hai lần lỗi liên tiếp; lần thứ ba giữ `failed`, request trả ngay 503 `KHOI_DONG_BI_KHOA`, không tự khởi động tiếp. Chỉ Admin kiểm tra/khởi động qua `/thao-tac` để mở lại; trạng thái khóa/bộ đếm lưu trong registry Core và không mất khi Core restart (`O:20`).

Engine cũ chưa nhận socket: đóng listener giữ cổng rồi khởi động ngay với cổng được cấp; ghi rõ đây là chế độ chuyển tiếp có khoảng hở. Không tự dò cổng khác. Chuyển giao socket trên Windows và thu hồi sau crash phải được thử ở G2; khảo sát chưa xác nhận cơ chế này đã có (`docs/47-core/g0/KS-A.md:75`, `docs/47-core/g0/KS-D.md:79`).

Chuyển ổ nghe chỉ áp dụng tiến trình trên máy Core. Máy phụ chỉ chủ động kéo việc từ Core, không có cổng nhận do Core cấp/chuyển giao (`O:20`, `D:262`).

## 5. Quản trị và đề xuất chế độ chạy

Trạng thái tiến trình dùng `stopped/starting/ready/busy/dang_dung/failed`, độc lập với (`O:20`):

- Công tắc nghiệp vụ module `TAT/THU/VAN_HANH`.
- Trạng thái việc và trạng thái duyệt kết quả.
- Chính sách `tu_kich_hoat_tu_dong/giu_lau_hon/luon_chay`.

Mặc định mọi module/engine tự kích hoạt và tự đóng khi rảnh; đề xuất ban đầu rảnh 300 giây. Quyết định rảnh và tăng/giảm bộ đếm request đồng bộ dùng **cùng khóa với dispatch**, ngăn đóng tiến trình vừa nhận request. Không đóng khi còn request, việc, lease, download hoặc ánh xạ Mask đang dùng. `dang_dung` chờ tối đa 300 giây; hết hạn báo lỗi dừng, giữ drain và cổng thuộc instance hiện tại để Admin xử lý, không tự cưỡng bức hủy việc (`O:20`). Tắt nghiệp vụ không xóa dữ liệu và không mặc nhiên cấm mọi quyền đọc lịch sử.

Mỗi lần khởi động ghi: giờ yêu cầu, giờ sẵn sàng, độ trễ khởi động, thời gian xử lý việc, thời gian rảnh trước đóng, RAM đỉnh, CPU và kết quả khởi động. Tổng hợp số lần/ngày và p50/p95 khởi động.

Hằng tuần tạo đề xuất bất biến theo từng module/engine, kèm kỳ số liệu, số mẫu, cấu hình hiện tại, cấu hình đề xuất và lý do. Thiếu số mẫu hoặc thiếu đo RAM/CPU phải ghi rõ; không suy ra chế độ luôn chạy từ dữ liệu thiếu.

**Chỉ Admin bấm áp dụng.** API kiểm quyền, phiên bản đề xuất, `row_version` cấu hình hiện tại; ghi audit trước/sau. Không tự áp dụng, không khởi động lại tiến trình đang bận để áp dụng chính sách. Gói module và hồ sơ chạy phải được kiểm trước; API không nhận lệnh shell, executable, URL hoặc khóa bí mật tùy ý.

PUT hồ sơ chạy cũng ghi audit người sửa, thời điểm, `request_id`, trước/sau như áp dụng đề xuất; không ghi credential (`O:45`).

## 6. Ba ví dụ đầy đủ

Các UUID, tài khoản và nội dung dưới đây hoàn toàn giả định. Giá trị cookie/token chỉ là ký hiệu minh họa.

### 6.1. Core đồng bộ: tạo tài liệu

```http
POST /api/v1/tai-lieu HTTP/1.1
Host: core.example.test
Origin: https://core.example.test
Cookie: __Host-ktt_phien=PHIEN_MINH_HOA
X-CSRF-Token: CSRF_MINH_HOA
X-Phap-Nhan-Id: 10000000-0000-4000-8000-000000000001
Idempotency-Key: demo-tao-tai-lieu-0001
Content-Type: application/json
Accept: application/json

{
  "ten": "Hợp đồng minh họa",
  "tep_id": "10000000-0000-4000-8000-000000000002"
}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json
Location: /api/v1/tai-lieu/10000000-0000-4000-8000-000000000003
X-Request-Id: 10000000-0000-4000-8000-000000000011
Cache-Control: no-store

{
  "id": "10000000-0000-4000-8000-000000000003",
  "phap_nhan_id": "10000000-0000-4000-8000-000000000001",
  "ten": "Hợp đồng minh họa",
  "tep_id": "10000000-0000-4000-8000-000000000002",
  "row_version": "1",
  "tao_luc": "2026-10-30T03:00:00Z"
}
```

### 6.2. Việc lâu: OCR một tài liệu

```http
POST /api/v1/engine/e_ocr/viec HTTP/1.1
Host: core.example.test
Origin: https://core.example.test
Cookie: __Host-ktt_phien=PHIEN_MINH_HOA
X-CSRF-Token: CSRF_MINH_HOA
X-Phap-Nhan-Id: 10000000-0000-4000-8000-000000000001
X-Module-Ma: m4
Idempotency-Key: demo-ocr-tai-lieu-0001
Content-Type: application/json
Accept: application/json

{
  "capability": "ocr.trich_van_ban@1",
  "tai_lieu_id": "10000000-0000-4000-8000-000000000003",
  "tep_id": "10000000-0000-4000-8000-000000000002",
  "bo_xu_ly": "dual",
  "ep_ocr": true
}
```

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
Location: /api/v1/viec/10000000-0000-4000-8000-000000000004
Retry-After: 2
X-Request-Id: 10000000-0000-4000-8000-000000000012
Cache-Control: no-store

{
  "viec_id": "10000000-0000-4000-8000-000000000004",
  "trang_thai": "queued",
  "request_id": "10000000-0000-4000-8000-000000000012"
}
```

```http
GET /api/v1/viec/10000000-0000-4000-8000-000000000004 HTTP/1.1
Host: core.example.test
Cookie: __Host-ktt_phien=PHIEN_MINH_HOA
X-Phap-Nhan-Id: 10000000-0000-4000-8000-000000000001
Accept: application/json
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Request-Id: 10000000-0000-4000-8000-000000000013
Cache-Control: no-store

{
  "id": "10000000-0000-4000-8000-000000000004",
  "phap_nhan_id": "10000000-0000-4000-8000-000000000001",
  "ma_module": "m4",
  "trang_thai": "succeeded",
  "tien_do": 100,
  "ket_qua_ids": ["10000000-0000-4000-8000-000000000005"],
  "loi": null,
  "tao_luc": "2026-10-30T03:01:00Z",
  "cap_nhat_luc": "2026-10-30T03:02:00Z"
}
```

Kết quả OCR vẫn có thể mang `trang_thai_duyet: "can_duyet"` dù việc đã `succeeded`.

### 6.3. Module: lưu ghi chú báo giá có CAS

```http
PATCH /api/v1/module/crm/bao-gia/10000000-0000-4000-8000-000000000006 HTTP/1.1
Host: core.example.test
Origin: https://core.example.test
Cookie: __Host-ktt_phien=PHIEN_MINH_HOA
X-CSRF-Token: CSRF_MINH_HOA
X-Phap-Nhan-Id: 10000000-0000-4000-8000-000000000001
Idempotency-Key: demo-luu-bao-gia-0001
Content-Type: application/json
Accept: application/json

{
  "row_version": "7",
  "expected_revision": 3,
  "ghi_chu": "Ghi chú minh họa đã được cập nhật."
}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Request-Id: 10000000-0000-4000-8000-000000000014
Cache-Control: no-store

{
  "id": "10000000-0000-4000-8000-000000000006",
  "phap_nhan_id": "10000000-0000-4000-8000-000000000001",
  "row_version": "8",
  "revision": 4,
  "ghi_chu": "Ghi chú minh họa đã được cập nhật."
}
```

Nếu phiên bản đã đổi, trả 409 theo dạng lỗi ở §2.3. Nếu gửi lại đúng request đã thành công với cùng khóa, trả biên nhận thành công sau kiểm quyền, không kiểm CAS lại như một lệnh mới.

## 7. Câu cần Anh chọn

Các giá trị trong OpenAPI phản ánh phương án khuyến nghị; chưa phải quyết định đã duyệt.

| Câu | Phương án và trade-off | Khuyến nghị |
|---|---|---|
| **C1. Nguồn đăng nhập** | **hỏi chung ở phiếu CSDL**, câu 3: A. Tài khoản Core. B. Danh tính sẵn có; quản trị tập trung nhưng cần xác định hệ nguồn. | A nếu chưa có hệ tập trung; không lấy hai quyết định (`O:50`, `D:453`). |
| **C2. Chờ khi mở module sau lúc rảnh?** | A. Đóng sau 5 phút, ít RAM; lần mở sau hiện “đang khởi động”, tự thử lại cùng khóa nếu 503 trước dispatch. B. Giữ 30 phút, giảm chờ nhưng tăng RAM. | A; không module nào luôn chạy nếu Admin chưa áp dụng. Chính sách deadline 30 giây/khởi động 120 giây giữ ở phần báo kỹ thuật (`O:53`). |
| **C3. Giới hạn upload ban đầu?** | A. 20 MiB. B. 50 MiB ở Core, vẫn chịu giới hạn nhỏ hơn của capability. Cần Anh cho biết hồ sơ scan M4 thường nặng bao nhiêu. | A, JSON 1 MiB; chưa upload tiếp tục/chia mảnh (`O:56`, `docs/47-core/g0/KS-E.md:111`). |

**Báo kỹ thuật, không thêm câu hỏi:** token ký/credential instance và chống trùng là yêu cầu thiết kế ở §2.4/§4.2, không còn phương án loopback + bí mật chung hoặc dọn biên nhận module sau 24 giờ (`O:22`, `O:31`). Retention **hỏi chung ở phiếu CSDL**, câu 2 (`D:452`), không đặt mặc định mới cho OCR/Mask tại API.

**Quyết định chuyển đổi phải ghép khi duyệt bộ API:** đề xuất phân ranh nhóm `V` theo bản đồ CSDL: registry/tiếp nhận chung về Core; cấu hình lịch nguồn riêng M0; định khoản/tri thức/duyệt/báo cáo kế toán chưa phân loại giữ adapter `ke_toan_cu`, không tự đăng ký module `that`. Lead phải ghép mã module/chủ nghiệp vụ và contract cụ thể trước mở T*; tài liệu này không coi tên `V` là đã duyệt (`D:225`, `D:51`, `D:57`, `R:12`). Đề xuất giữ alias theo từng nhóm đủ contract/quyền, gỡ sau khi hết phụ thuộc và có quyết định ngừng; phương án ngừng ngay chỉ dùng khi client đã chuyển đủ. Hai phương án và điều kiện này là nội dung phê duyệt chuyển đổi trong bộ phiếu, không thêm câu hỏi riêng vượt ba câu ưu tiên Opus (`R:12`, `O:48`).

**Tình trạng kiểm tra:** chỉ sửa hai tài liệu và kiểm contract tĩnh; không chạy ứng dụng, test nghiệp vụ, migration hoặc dịch vụ. Kết quả kiểm phụ lục ghi ở mục “Vòng 2 — đã xử lý”; chưa có bằng chứng runtime/tích hợp (`docs/47-core/g1/GIAO-G1B.md:8`).

# Phụ lục — openapi-v1.yaml

```yaml
openapi: 3.1.0
jsonSchemaDialect: https://json-schema.org/draft/2020-12/schema
info:
  title: Bo API Core v1
  version: 0.1.0-draft
  description: |
    Ban nhap G1b-1, chua duoc phep trien khai.
    Duong dan dung gach noi; truong JSON dung snake_case.
    Danh tinh va login theo phieu CSDL vong 2; bien nhan module vinh vien theo K2.
    Contract noi dung tep ket qua theo phieu SDK.
    Tat ca response co X-Request-Id va Cache-Control: no-store.
    Ghi phai kiem Origin, CSRF, quyen va schema.
    Moi loi HTTP dung schema Loi, ke ca loi tu proxy/adapter.
    Cac nguong thoi gian, dung luong va retention la de xuat cho Anh duyet.
    Can cu hieu chinh: O:16, O:18, O:19, O:20, O:21, O:31; R:9, R:10, R:11.
servers:
  - url: /
security:
  - phien: []

tags:
  - name: phien
  - name: du_lieu
  - name: module
  - name: engine
  - name: quy_trinh
  - name: viec
  - name: quan_tri
  - name: van_hanh

paths:
  /api/v1/phien:
    get:
      tags: [phien]
      operationId: doc_phien
      security: []
      summary: Doc phien va cap CSRF token
      description: |
        Neu chua dang nhap, tra nguoi_dung_id va het_han_luc bang null,
        dong thoi cap cookie tien phien hieu luc 10 phut.
        Neu cookie phien hop le thi tra thong tin phien hien tai.
      responses:
        '200':
          description: Trang thai phien
          headers: &dau_ra_chung
            X-Request-Id:
              schema: { $ref: '#/components/schemas/Id' }
            Cache-Control:
              schema: { type: string, const: no-store }
            Set-Cookie:
              description: |
                Cookie phien hoac tien phien; Secure, HttpOnly,
                SameSite=Strict, Path=/, khong co Domain.
              schema: { type: string }
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Phien' }
        default: &loi
          $ref: '#/components/responses/Loi'
    post:
      tags: [phien]
      operationId: dang_nhap
      summary: Dang nhap va doi SID
      security:
        - tien_phien: []
          csrf: []
      parameters:
        - $ref: '#/components/parameters/Origin'
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/DangNhap' }
      responses:
        '200':
          description: Dang nhap thanh cong; cookie va CSRF da doi
          headers: *dau_ra_chung
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Phien' }
        default: *loi
    delete:
      tags: [phien]
      operationId: dang_xuat
      summary: Thu hoi phien va xoa cookie
      security: &xac_thuc_ghi
        - phien: []
          csrf: []
      parameters:
        - $ref: '#/components/parameters/Origin'
      responses:
        '204':
          description: Da thu hoi phien; khong co body
          headers: *dau_ra_chung
        default: *loi

  /api/v1/toi:
    get:
      tags: [phien]
      operationId: doc_toi
      summary: Doc danh tinh va quyen hieu luc
      responses:
        '200':
          description: Nguoi dung hien tai
          headers: &dau_ra_khong_cookie
            X-Request-Id:
              schema: { $ref: '#/components/schemas/Id' }
            Cache-Control:
              schema: { type: string, const: no-store }
          content:
            application/json:
              schema: { $ref: '#/components/schemas/NguoiDung' }
        default: *loi

  /api/v1/phap-nhan:
    get:
      tags: [phien]
      operationId: liet_ke_phap_nhan
      summary: Liet ke phap nhan duoc phep chon
      parameters: &phan_trang
        - $ref: '#/components/parameters/ConTro'
        - $ref: '#/components/parameters/KichThuocTrang'
      responses:
        '200':
          description: Danh sach phap nhan theo quyen
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TrangPhapNhan' }
        default: *loi

  /api/v1/tai-lieu:
    parameters:
      - $ref: '#/components/parameters/PhapNhan'
    get:
      tags: [du_lieu]
      operationId: liet_ke_tai_lieu
      summary: Liet ke tai lieu theo quyen
      x-quyen: tai_lieu.doc
      parameters: *phan_trang
      responses:
        '200':
          description: Danh sach tai lieu
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TrangTaiLieu' }
        default: *loi
    post:
      tags: [du_lieu]
      operationId: tao_tai_lieu
      summary: Tao tai lieu tu tep da nhan
      x-quyen: tai_lieu.tao
      security: *xac_thuc_ghi
      parameters: &ghi
        - $ref: '#/components/parameters/Origin'
        - $ref: '#/components/parameters/KhoaChongTrung'
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/TaoTaiLieu' }
      responses:
        '201':
          description: Tai lieu da tao
          headers:
            X-Request-Id:
              schema: { $ref: '#/components/schemas/Id' }
            Cache-Control:
              schema: { type: string, const: no-store }
            Location:
              schema: { type: string, format: uri-reference }
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TaiLieu' }
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/tai-lieu/{id}:
    parameters:
      - $ref: '#/components/parameters/Id'
      - $ref: '#/components/parameters/PhapNhan'
    get:
      tags: [du_lieu]
      operationId: doc_tai_lieu
      summary: Doc metadata tai lieu
      x-quyen: tai_lieu.doc
      responses:
        '200':
          description: Tai lieu
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TaiLieu' }
        default: *loi
    patch:
      tags: [du_lieu]
      operationId: sua_tai_lieu
      summary: Sua ten tai lieu voi row_version
      x-quyen: tai_lieu.sua
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/SuaTaiLieu' }
      responses:
        '200':
          description: Tai lieu sau cap nhat
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TaiLieu' }
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/tep:
    parameters:
      - $ref: '#/components/parameters/PhapNhanTuyChon'
    post:
      tags: [du_lieu]
      operationId: tai_len_tep
      summary: Nhan mot tep qua multipart
      description: |
        Tep toi da 20 MiB; kiem MIME thuc va gioi han capability.
        Goi module chi Admin he thong duoc tai len, bo header phap nhan,
        tao tep he thong phap_nhan_id/tai_lieu_id null.
        muc_dich tai_lieu bat buoc header phap nhan va quyen tep.tai_len.
        Can cu: R:11.
        Khong tu dong OCR hoac phe duyet noi dung trong request upload.
      x-quyen: tep.tai_len
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema: { $ref: '#/components/schemas/TaiLenTep' }
            encoding:
              tep:
                contentType: application/octet-stream
      responses:
        '201':
          description: Tep da duoc kiem va nhan
          headers:
            X-Request-Id:
              schema: { $ref: '#/components/schemas/Id' }
            Cache-Control:
              schema: { type: string, const: no-store }
            Location:
              schema: { type: string, format: uri-reference }
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Tep' }
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/tep/{id}:
    parameters:
      - $ref: '#/components/parameters/Id'
      - $ref: '#/components/parameters/PhapNhanTuyChon'
    get:
      tags: [du_lieu]
      operationId: doc_tep
      summary: Doc metadata tep
      description: |
        Tep nghiep vu bat buoc header phap nhan khop va quyen noi dung.
        Tep he thong phap_nhan_id null chi Admin, bo header phap nhan.
        Can cu: R:11.
      x-quyen: tep.doc
      responses:
        '200':
          description: Metadata tep
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Tep' }
        default: *loi

  /api/v1/tep/{id}/noi-dung:
    parameters:
      - $ref: '#/components/parameters/Id'
      - $ref: '#/components/parameters/PhapNhanTuyChon'
    get:
      tags: [du_lieu]
      operationId: tai_xuong_tep
      summary: Tai bytes sau khi kiem lai quyen
      description: |
        Khong nhan duong dan vat ly; khong ho tro Range trong v1.
        Content-Type co the dung application/octet-stream an toan.
        Tep ket qua phai kiem lai quyen ket qua/bien the da dang ky.
        Tep he thong phap_nhan_id null chi Admin, bo header phap nhan.
        Khong proxy bytes tho tu module; module ghi qua SDK vao kho Core.
        Can cu: O:21; R:11; D:317.
      x-quyen: tep.tai_xuong
      responses:
        '200':
          description: Luong bytes cua tep
          headers:
            X-Request-Id:
              schema: { $ref: '#/components/schemas/Id' }
            Cache-Control:
              schema: { type: string, const: no-store }
            Content-Disposition:
              schema: { type: string }
              description: Attachment voi ten tep da lam sach
            X-Content-Type-Options:
              schema: { type: string, const: nosniff }
            Content-Length:
              schema: { type: integer, minimum: 0 }
          content:
            application/octet-stream:
              schema:
                type: string
                format: binary
        default: *loi

  /api/v1/ket-qua/{id}:
    parameters:
      - $ref: '#/components/parameters/Id'
      - $ref: '#/components/parameters/PhapNhanTuyChon'
    get:
      tags: [du_lieu]
      operationId: doc_ket_qua
      summary: Doc metadata va nguon ket qua
      description: |
        Ket qua nghiep vu bat buoc header phap nhan khop.
        Ket qua quan tri co phap_nhan_id null chi Admin he thong doc.
        Noi dung duoc tai qua tep_id; khong tra object JSON tuy y.
      x-quyen: ket_qua.doc
      responses:
        '200':
          description: Metadata ket qua
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/KetQua' }
        default: *loi

  /api/v1/module:
    parameters:
      - $ref: '#/components/parameters/PhapNhan'
    get:
      tags: [module]
      operationId: liet_ke_module
      summary: Liet ke module theo quyen va phap nhan
      parameters: *phan_trang
      responses:
        '200':
          description: Module duoc phep thay
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TrangBoPhan' }
        default: *loi

  /api/v1/module/{ma_module}:
    parameters:
      - $ref: '#/components/parameters/MaModule'
      - $ref: '#/components/parameters/PhapNhan'
    get:
      tags: [module]
      operationId: doc_module
      summary: Doc khai bao module theo quyen
      description: Doc registry khong tu khoi dong tien trinh.
      responses:
        '200':
          description: Module
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/BoPhan' }
        default: *loi

  /api/v1/engine:
    parameters:
      - $ref: '#/components/parameters/PhapNhan'
    get:
      tags: [engine]
      operationId: liet_ke_engine
      summary: Liet ke engine va capability duoc phep dung
      parameters: *phan_trang
      responses:
        '200':
          description: Engine duoc phep thay
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TrangBoPhan' }
        default: *loi

  /api/v1/engine/{ma_engine}:
    parameters:
      - $ref: '#/components/parameters/MaEngine'
      - $ref: '#/components/parameters/PhapNhan'
    get:
      tags: [engine]
      operationId: doc_engine
      summary: Doc capability va trang thai
      description: |
        Khong tra dia chi noi bo, khoa hoac lenh khoi dong.
        GET khong tu khoi dong engine.
      responses:
        '200':
          description: Engine
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/BoPhan' }
        default: *loi

  /api/v1/engine/{ma_engine}/viec:
    parameters:
      - $ref: '#/components/parameters/MaEngine'
      - $ref: '#/components/parameters/PhapNhan'
      - $ref: '#/components/parameters/ModuleNguon'
    post:
      tags: [engine]
      operationId: tao_viec_engine
      summary: Gui capability qua Core va adapter
      description: |
        Kiem capability thuoc dung ma_engine, module da duoc cap quyen,
        nguoi dung va moi tham chieu du lieu.
        Chi cong bo capability da co adapter va schema duoc duyet.
        OCR/Mask/Trich/HoaDon duoi day la danh sach lenh cua ban nhap;
        khong xac nhan capability da trien khai.
        Cloud chi qua cong AI cua phan mem va Mask v2.
      x-quyen: engine.goi
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/LenhEngine' }
      responses:
        '202':
          $ref: '#/components/responses/DaNhanViec'
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/quy-trinh:
    parameters:
      - $ref: '#/components/parameters/PhapNhan'
    get:
      tags: [quy_trinh]
      operationId: liet_ke_quy_trinh
      summary: Liet ke quy trinh theo quyen
      x-quyen: quy_trinh.doc
      parameters: *phan_trang
      responses:
        '200':
          description: Danh sach quy trinh
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TrangQuyTrinh' }
        default: *loi

  /api/v1/quy-trinh/{id}/lan-chay:
    parameters:
      - $ref: '#/components/parameters/Id'
      - $ref: '#/components/parameters/PhapNhan'
      - $ref: '#/components/parameters/ModuleNguon'
    post:
      tags: [quy_trinh]
      operationId: chay_quy_trinh
      summary: Tao lan chay quy trinh da ghim phien ban
      description: |
        Ban nhap chi nhan quy trinh co input theo schema LanChayQuyTrinh.
        Quy trinh can input khac phai bo sung schema va contract truoc dang ky.
        Module nguon phai khop chu so huu hoac quyen goi duoc cap.
      x-quyen: quy_trinh.chay
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/LanChayQuyTrinh' }
      responses:
        '202':
          $ref: '#/components/responses/DaNhanViec'
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/viec:
    get:
      tags: [viec]
      operationId: liet_ke_viec
      summary: Liet ke snapshot viec theo quyen
      description: |
        Loc theo ma_module/trang_thai neu co, phan trang on dinh.
        Co header phap nhan thi chi liet ke viec thuoc phap nhan do.
        Bo header chi cho Admin he thong, chi liet ke viec he thong.
        Chu viec phai con quyen; xem nguoi khac can MTQ viec.giam_sat
        dung phap nhan va module; loai dong ngoai quyen.
        Poll theo Retry-After; khong co SSE hay phat lai su kien trong v1.
        Can cu: O:18; R:10.
      x-quyen: chu_viec_con_quyen_hoac_MTQ_viec.giam_sat
      parameters:
        - $ref: '#/components/parameters/PhapNhanTuyChon'
        - $ref: '#/components/parameters/ConTro'
        - $ref: '#/components/parameters/KichThuocTrang'
        - name: ma_module
          in: query
          required: false
          schema: { $ref: '#/components/schemas/Ma' }
        - name: trang_thai
          in: query
          required: false
          schema: { $ref: '#/components/schemas/TrangThaiViec' }
      responses:
        '200':
          description: Trang snapshot viec duoc phep xem
          headers:
            X-Request-Id:
              schema: { $ref: '#/components/schemas/Id' }
            Cache-Control:
              schema: { type: string, const: no-store }
            Retry-After:
              schema: { type: integer, minimum: 1, default: 2 }
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TrangViec' }
        default: *loi

  /api/v1/viec/{id}:
    parameters:
      - $ref: '#/components/parameters/Id'
      - $ref: '#/components/parameters/PhapNhanTuyChon'
    get:
      tags: [viec]
      operationId: doc_viec
      summary: Theo doi viec theo quyen
      description: |
        Viec nghiep vu bat buoc header phap nhan khop.
        Viec he thong co phap_nhan_id null chi Admin he thong doc.
        Chu viec phai con quyen; xem nguoi khac can MTQ viec.giam_sat
        dung phap nhan va module; thieu quyen tra 404. Can cu: O:18.
        Sau restart/het lease, running mat heartbeat thanh interrupted.
        Chi xep lai khi contract khai thu_lai_an_toan va da doi chieu;
        khong tu coi thanh succeeded hoac chay lai ghi/nhap mu. Can cu: O:18.
      x-quyen: chu_viec_con_quyen_hoac_MTQ_viec.giam_sat
      responses:
        '200':
          description: Trang thai viec
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Viec' }
        default: *loi

  /api/v1/viec/{id}/ket-qua:
    parameters:
      - $ref: '#/components/parameters/Id'
      - $ref: '#/components/parameters/PhapNhanTuyChon'
    get:
      tags: [viec]
      operationId: liet_ke_ket_qua_viec
      summary: Liet ke ket qua duoc phep doc cua viec
      description: |
        Kiem quyen viec va tung ket qua; viec thanh cong khong tu phe duyet.
        Ap dung quy tac phap nhan nhu doc_viec.
      parameters: *phan_trang
      responses:
        '200':
          description: Danh sach metadata ket qua
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TrangKetQua' }
        default: *loi

  /api/v1/viec/{id}/huy:
    parameters:
      - $ref: '#/components/parameters/Id'
      - $ref: '#/components/parameters/PhapNhanTuyChon'
    post:
      tags: [viec]
      operationId: de_nghi_huy_viec
      summary: Ghi de nghi huy, khong khang dinh da huy ngay
      description: |
        Neu viec da ket thuc thi tra lai trang thai cuoi trong response 202.
        Khong hoan tac tac dong da commit.
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/DeNghiHuy' }
      responses:
        '202':
          $ref: '#/components/responses/DaNhanViec'
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/quan-tri/module:
    get:
      tags: [quan_tri]
      operationId: quan_tri_liet_ke_module
      summary: Doc registry module
      x-quyen: quan_tri.he_thong
      parameters: *phan_trang
      responses:
        '200':
          description: Registry module
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TrangBoPhan' }
        default: *loi

  /api/v1/quan-tri/module/{ma_module}/thao-tac:
    parameters:
      - $ref: '#/components/parameters/MaModule'
    post:
      tags: [quan_tri]
      operationId: thao_tac_module
      summary: Kiem goi, cai, nang cap, khoi dong hoac dung module
      description: |
        Viec quan tri co phap_nhan_id null.
        cai_dat chi chap nhan row_version "0" khi module chua ton tai.
        Cac thao tac con lai phai khop registry hien tai.
        Goi cai/nang cap phai qua kiem tra chu ky/nguon noi bo,
        manifest, schema, tuong thich va quyen; khong chay ma khi kiem goi.
        Viec kiem goi tra ket qua dang metadata bao cao.
      x-quyen: quan_tri.he_thong
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ThaoTacModule' }
      responses:
        '202':
          $ref: '#/components/responses/DaNhanViec'
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/quan-tri/module/{ma_module}/che-do:
    parameters:
      - $ref: '#/components/parameters/MaModule'
      - $ref: '#/components/parameters/PhapNhan'
    get:
      tags: [quan_tri]
      operationId: doc_che_do_module
      summary: Doc cong tac, nguoi thu va phien ban
      x-can-cu: 'R:10'
      x-quyen: quan_tri.module
      responses:
        '200':
          description: Cong tac hien tai theo phap nhan
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/CheDoModule' }
        default: *loi
    patch:
      tags: [quan_tri]
      operationId: doi_che_do_module
      summary: Doi cong tac nghiep vu tai phap nhan
      description: |
        TAT/THU/VAN_HANH tach biet trang thai tien trinh.
        Khong xoa du lieu; quyen doc lich su van theo MTQ.
      x-quyen: quan_tri.module
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/CheDoModule' }
      responses:
        '200':
          description: Cong tac sau cap nhat
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/CheDoModule' }
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/quan-tri/engine:
    get:
      tags: [quan_tri]
      operationId: quan_tri_liet_ke_engine
      summary: Doc registry engine
      x-quyen: quan_tri.he_thong
      parameters: *phan_trang
      responses:
        '200':
          description: Registry engine
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TrangBoPhan' }
        default: *loi
    post:
      tags: [quan_tri]
      operationId: dang_ky_engine
      summary: Dang ky engine tu ho so chay da duyet
      description: |
        Cap cong trong so cong theo phieu CSDL.
        Dang ky khong tu khoi dong engine.
        ho_so_mau_id tro toi cau hinh may chu da duoc phe duyet,
        khong phai lenh shell hoac URL do client tuy chon.
      x-quyen: quan_tri.he_thong
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/DangKyEngine' }
      responses:
        '201':
          description: Engine da dang ky o trang thai stopped
          headers:
            X-Request-Id:
              schema: { $ref: '#/components/schemas/Id' }
            Cache-Control:
              schema: { type: string, const: no-store }
            Location:
              schema: { type: string, format: uri-reference }
          content:
            application/json:
              schema: { $ref: '#/components/schemas/BoPhan' }
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/quan-tri/engine/{ma_engine}/ho-so-chay:
    parameters:
      - $ref: '#/components/parameters/MaEngine'
    get:
      tags: [quan_tri]
      operationId: doc_ho_so_chay_engine
      summary: Doc ho so an toan va phien ban
      x-can-cu: 'R:10'
      x-quyen: quan_tri.he_thong
      responses:
        '200':
          description: Ho so da duyet, khong bi mat hay duong dan vat ly
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/HoSoChay' }
        default: *loi
    put:
      tags: [quan_tri]
      operationId: doi_ho_so_chay_engine
      summary: Cap nhat ho so va chinh sach engine
      description: |
        Kiem row_version; khong doi am tham cau hinh cua viec dang chay.
        Khong nhan khoa, duong dan executable hay lenh shell trong body.
        Audit nguoi sua, thoi diem, request_id va gia tri truoc/sau. Can cu: O:45.
      x-quyen: quan_tri.he_thong
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/HoSoChay' }
      responses:
        '200':
          description: Ho so sau cap nhat, row_version moi
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/HoSoChay' }
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/quan-tri/engine/{ma_engine}/thao-tac:
    parameters:
      - $ref: '#/components/parameters/MaEngine'
    post:
      tags: [quan_tri]
      operationId: thao_tac_engine
      summary: Kiem tra, khoi dong hoac dung engine
      description: |
        Viec quan tri co phap_nhan_id null.
        Dung phai drain, doi ban giao ket qua va kiem quyen so huu.
        Khong dung ung dung la dang giu cong.
      x-quyen: quan_tri.he_thong
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ThaoTacEngine' }
      responses:
        '202':
          $ref: '#/components/responses/DaNhanViec'
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/quan-tri/cap-quyen/{ma_module}:
    parameters:
      - $ref: '#/components/parameters/MaModule'
      - $ref: '#/components/parameters/PhapNhan'
    get:
      tags: [quan_tri]
      operationId: doc_cap_quyen_module
      summary: Doc quyen thuc cap cho module
      x-quyen: quan_tri.cap_quyen
      responses:
        '200':
          description: Quyen thuc cap tai phap nhan
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/CapQuyen' }
        default: *loi
    put:
      tags: [quan_tri]
      operationId: thay_cap_quyen_module
      summary: Thay tap quyen thuc cap voi CAS
      description: |
        Danh sach moi thay toan bo tap quyen trong pham vi nay.
        Khong cap vuot quyen cua nguoi cap hoac yeu cau manifest.
        row_version "0" chi hop le khi chua co ban ghi cap quyen.
      x-quyen: quan_tri.cap_quyen
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/CapQuyen' }
      responses:
        '200':
          description: Tap quyen va row_version moi
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/CapQuyen' }
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/quan-tri/so-do:
    get:
      tags: [quan_tri]
      operationId: doc_so_do
      summary: Doc so do khoi dong va tai nguyen
      x-quyen: quan_tri.he_thong
      parameters:
        - $ref: '#/components/parameters/LoaiBoPhan'
        - $ref: '#/components/parameters/MaBoPhan'
        - name: tu_ngay
          in: query
          required: true
          schema: { type: string, format: date }
        - name: den_ngay
          in: query
          required: true
          schema: { type: string, format: date }
        - $ref: '#/components/parameters/ConTro'
        - $ref: '#/components/parameters/KichThuocTrang'
      responses:
        '200':
          description: So do va thong ke cua toan khoang ngay
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/SoDo' }
        default: *loi

  /api/v1/quan-tri/de-xuat-che-do:
    get:
      tags: [quan_tri]
      operationId: liet_ke_de_xuat_che_do
      summary: Doc de xuat tuan va can cu
      x-quyen: quan_tri.he_thong
      parameters:
        - name: tuan_bat_dau
          in: query
          required: true
          description: Ngay thu Hai bat dau tuan theo Asia/Ho_Chi_Minh
          schema: { type: string, format: date }
        - $ref: '#/components/parameters/ConTro'
        - $ref: '#/components/parameters/KichThuocTrang'
      responses:
        '200':
          description: Danh sach de xuat bat bien
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/TrangDeXuat' }
        default: *loi

  /api/v1/quan-tri/de-xuat-che-do/{id}/ap-dung:
    parameters:
      - $ref: '#/components/parameters/Id'
    post:
      tags: [quan_tri]
      operationId: ap_dung_de_xuat_che_do
      summary: Admin ap dung mot de xuat
      description: |
        Kiem row_version cau hinh hien tai va de xuat chua bi thay the.
        Chi doi chinh sach; khong cuong buc khoi dong lai viec dang ban.
        Ghi audit nguoi ap dung, thoi diem va gia tri truoc/sau.
      x-quyen: quan_tri.he_thong
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ApDungDeXuat' }
      responses:
        '200':
          description: Chinh sach da duoc Admin ap dung
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/DaApDungDeXuat' }
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /api/v1/module/crm/bao-gia/{id}:
    parameters:
      - $ref: '#/components/parameters/Id'
      - $ref: '#/components/parameters/PhapNhan'
    get:
      tags: [module]
      operationId: crm_doc_ghi_chu_bao_gia
      summary: Doc ghi chu va phien ban bao gia
      description: Contract toi thieu cho vi du CAS, khong phai toan bo bao gia.
      x-quyen: crm.bao_gia.doc
      responses:
        '200':
          description: Ghi chu bao gia
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/GhiChuBaoGia' }
        default: *loi
    patch:
      tags: [module]
      operationId: crm_luu_ghi_chu_bao_gia
      summary: Luu ghi chu bao gia voi row_version va expected_revision
      description: |
        Dispatcher chuyen toi tien trinh CRM sau kiem quyen/schema.
        Module kiem CAS nghiep vu va row_version trong giao dich ghi.
        Bat buoc ca row_version va expected_revision; lech mot trong hai tra 409.
        Core chi khoa request dang chay va chuyen Idempotency-Key trong token ky.
        Module giu bien nhan bat bien vinh vien cung transaction nghiep vu;
        kiem quyen hanh dong truoc tra va quyen doc ket qua truoc replay.
        Fingerprint la operation + body logic chuan hoa (gom id dich), khong path/key.
        Sau 504 chi doi chieu bien nhan module, khong tu ghi de. Can cu: O:31; O:46.
      x-quyen: crm.bao_gia.sua
      security: *xac_thuc_ghi
      parameters: *ghi
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/LuuGhiChuBaoGia' }
      responses:
        '200':
          description: Ghi chu va hai phien ban sau cap nhat
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema: { $ref: '#/components/schemas/GhiChuBaoGia' }
        '409':
          $ref: '#/components/responses/XungDot'
        default: *loi

  /healthz:
    get:
      tags: [van_hanh]
      operationId: kiem_tra_song
      summary: Core con song
      description: Khong goi OCR, AI hoac tao tep thu.
      security: []
      responses:
        '200':
          description: Core con song
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema:
                type: object
                additionalProperties: false
                required: [trang_thai]
                properties:
                  trang_thai: { type: string, const: song }
        default: *loi

  /readyz:
    get:
      tags: [van_hanh]
      operationId: kiem_tra_san_sang
      summary: Core du nen phuc vu
      description: |
        Kiem CSDL, registry va cac dich vu nen bat buoc.
        Engine/module stopped khong tu lam Core mat readiness.
        Khong cong bo chi tiet ha tang hoac khoa.
      security: []
      responses:
        '200':
          description: Core san sang
          headers: *dau_ra_khong_cookie
          content:
            application/json:
              schema:
                type: object
                additionalProperties: false
                required: [trang_thai]
                properties:
                  trang_thai: { type: string, const: san_sang }
        '503':
          $ref: '#/components/responses/Loi'
        default: *loi

components:
  securitySchemes:
    phien:
      type: apiKey
      in: cookie
      name: __Host-ktt_phien
      description: |
        SID opaque; Secure, HttpOnly, SameSite=Strict, Path=/.
        TLS bat buoc ngoai loopback; HTTP IP LAN khong ho tro dang nhap. Can cu: O:21.
    tien_phien:
      type: apiKey
      in: cookie
      name: __Host-ktt_tien_phien
      description: Cookie tien phien hieu luc 10 phut, chi dung dang nhap
    csrf:
      type: apiKey
      in: header
      name: X-CSRF-Token
      description: Token opaque gan voi phien hoac tien phien; 16-512 ky tu

  parameters:
    Id:
      name: id
      in: path
      required: true
      schema: { $ref: '#/components/schemas/Id' }
    MaModule:
      name: ma_module
      in: path
      required: true
      schema: { $ref: '#/components/schemas/Ma' }
    MaEngine:
      name: ma_engine
      in: path
      required: true
      schema: { $ref: '#/components/schemas/Ma' }
    PhapNhan:
      name: X-Phap-Nhan-Id
      in: header
      required: true
      schema: { $ref: '#/components/schemas/Id' }
      description: Lua chon phap nhan; Core phai kiem lai quyen
    PhapNhanTuyChon:
      name: X-Phap-Nhan-Id
      in: header
      required: false
      schema: { $ref: '#/components/schemas/Id' }
      description: |
        Bat buoc voi tai nguyen nghiep vu.
        Chi duoc bo voi tai nguyen he thong co phap_nhan_id null
        va nguoi goi la Admin he thong.
    ModuleNguon:
      name: X-Module-Ma
      in: header
      required: true
      schema: { $ref: '#/components/schemas/Ma' }
      description: Core kiem quyen module va rang buoc operation/capability
    Origin:
      name: Origin
      in: header
      required: true
      schema: { type: string, format: uri }
      description: Phai trung nguon Core duoc cau hinh
    KhoaChongTrung:
      name: Idempotency-Key
      in: header
      required: true
      schema:
        type: string
        minLength: 16
        maxLength: 128
        pattern: '^[A-Za-z0-9._:-]+$'
      description: |
        Core: pham vi nguoi dung/phap nhan hoac he thong/module/operation;
        bien nhan cung transaction, 24 gio tu ket qua cuoi, giu tiep khi chua xac dinh.
        Module: UNIQUE phap_nhan/module/operation/key theo K2, bien nhan vinh vien
        cung transaction nghiep vu; replay kiem quyen hanh dong va doc ket qua.
        Fingerprint operation + body logic chuan hoa, gom id dich va hash tep;
        khong gom method/path/key; alias va v1 dung chung. Can cu: O:31.
    ConTro:
      name: con_tro
      in: query
      required: false
      schema: { type: string, minLength: 1, maxLength: 4096 }
      description: Cursor opaque gan ngu canh; de xuat TTL 15 phut
    KichThuocTrang:
      name: kich_thuoc_trang
      in: query
      required: false
      schema: { type: integer, minimum: 1, maximum: 100, default: 25 }
    LoaiBoPhan:
      name: loai
      in: query
      required: true
      schema: { type: string, enum: [module, engine] }
    MaBoPhan:
      name: ma
      in: query
      required: true
      schema: { $ref: '#/components/schemas/Ma' }

  responses:
    Loi:
      description: |
        Loi da lam sach, theo bang ma HTTP trong than dac ta.
        Cac ma co the gom 400/401/403/404/405/409/410/413/415/422/
        429/500/502/503/504. 405 co Allow; 429 va loi tam thoi
        co the co Retry-After. Khong tra SQL, khoa hay payload upstream.
      headers:
        X-Request-Id:
          schema: { $ref: '#/components/schemas/Id' }
        Cache-Control:
          schema: { type: string, const: no-store }
        Retry-After:
          schema: { type: integer, minimum: 1 }
        Allow:
          schema: { type: string }
      content:
        application/json:
          schema: { $ref: '#/components/schemas/Loi' }
    XungDot:
      description: CAS cu, khoa khac noi dung hoac yeu cau dang xu ly. Can cu R:14.
      headers:
        X-Request-Id:
          schema: { $ref: '#/components/schemas/Id' }
        Cache-Control:
          schema: { type: string, const: no-store }
        Retry-After:
          description: Gia tri 2 khi YEU_CAU_DANG_XU_LY
          schema: { type: integer, minimum: 1 }
      content:
        application/json:
          schema: { $ref: '#/components/schemas/Loi' }
          examples:
            phien_ban:
              value:
                ma: XUNG_DOT_PHIEN_BAN
                thong_diep: Dữ liệu đã đổi. Anh tải lại trước khi lưu.
                request_id: 10000000-0000-4000-8000-000000000099
                thu_lai_duoc: false
            khoa_khac_noi_dung:
              value:
                ma: KHOA_CHONG_TRUNG_KHAC_NOI_DUNG
                thong_diep: Khóa đã dùng với nội dung khác.
                request_id: 10000000-0000-4000-8000-000000000099
                thu_lai_duoc: false
            dang_xu_ly:
              value:
                ma: YEU_CAU_DANG_XU_LY
                thong_diep: Yêu cầu đang xử lý. Anh thử lại cùng khóa.
                request_id: 10000000-0000-4000-8000-000000000099
                thu_lai_duoc: true
    DaNhanViec:
      description: Viec hoac de nghi huy da duoc ghi ben vung
      headers:
        X-Request-Id:
          schema: { $ref: '#/components/schemas/Id' }
        Cache-Control:
          schema: { type: string, const: no-store }
        Location:
          required: true
          schema: { type: string, format: uri-reference }
          description: Duong dan /api/v1/viec/{id}
        Retry-After:
          required: true
          schema: { type: integer, minimum: 1, default: 2 }
      content:
        application/json:
          schema: { $ref: '#/components/schemas/DaNhanViec' }

  schemas:
    Id:
      type: string
      format: uuid
    Ma:
      type: string
      pattern: '^[a-z][a-z0-9_]{0,31}$'
    RowVersion:
      type: string
      pattern: '^[1-9][0-9]{0,18}$'
      description: |
        So nguyen duong truyen dang chuoi; backend kiem mien gia tri
        tuong ung cot CSDL theo phieu CSDL.
    RowVersionHoacChuaCo:
      type: string
      pattern: '^(0|[1-9][0-9]{0,18})$'
      description: '"0" chi dung tao ban ghi chua ton tai tai route cho phep'
    ThoiDiem:
      type: string
      format: date-time
      description: Response chuan UTC Z; request phai co mui gio
    Tien:
      type: object
      additionalProperties: false
      required: [gia_tri, don_vi_tien]
      properties:
        gia_tri:
          type: string
          pattern: '^-?(0|[1-9][0-9]{0,17})(\.[0-9]{1,6})?$'
        don_vi_tien:
          type: string
          pattern: '^[A-Z]{3}$'
      description: |
        Contract tien co so, khong dung float.
        Tung truong nghiep vu phai quy dinh them mien va lam tron.
    Loi:
      type: object
      additionalProperties: false
      required: [ma, thong_diep, request_id, thu_lai_duoc]
      properties:
        ma:
          type: string
          pattern: '^[A-Z][A-Z0-9_]{0,95}$'
        thong_diep:
          type: string
          minLength: 1
          maxLength: 1000
          description: Thong diep tieng Viet an toan cho nguoi dung
        request_id: { $ref: '#/components/schemas/Id' }
        thu_lai_duoc: { type: boolean }
        chi_tiet:
          type: array
          maxItems: 100
          items:
            type: object
            additionalProperties: false
            required: [truong, ma]
            properties:
              truong: { type: string, minLength: 1, maxLength: 255 }
              ma: { type: string, pattern: '^[A-Z][A-Z0-9_]{0,95}$' }
          description: Chi ten truong da khai va ma loi, khong chua gia tri. Can cu O:16.

    DangNhap:
      type: object
      additionalProperties: false
      required: [ten_dang_nhap, mat_khau]
      properties:
        ten_dang_nhap: { type: string, minLength: 1, maxLength: 254 }
        mat_khau:
          type: string
          format: password
          writeOnly: true
          minLength: 1
          maxLength: 1024
    Phien:
      type: object
      additionalProperties: false
      required: [nguoi_dung_id, het_han_luc, csrf_token]
      properties:
        nguoi_dung_id: { type: [string, 'null'], format: uuid }
        het_han_luc: { type: [string, 'null'], format: date-time }
        csrf_token: { type: string, minLength: 16, maxLength: 512 }
    NguoiDung:
      type: object
      additionalProperties: false
      required: [id, ten_hien_thi, quyen]
      properties:
        id: { $ref: '#/components/schemas/Id' }
        ten_hien_thi: { type: string, minLength: 1, maxLength: 255 }
        quyen:
          type: array
          maxItems: 2000
          uniqueItems: true
          items: { type: string, minLength: 1, maxLength: 128 }
    PhapNhan:
      type: object
      additionalProperties: false
      required: [id, ten]
      properties:
        id: { $ref: '#/components/schemas/Id' }
        ten: { type: string, minLength: 1, maxLength: 255 }

    TaoTaiLieu:
      type: object
      additionalProperties: false
      required: [ten, tep_id]
      properties:
        ten: { type: string, minLength: 1, maxLength: 255 }
        tep_id: { $ref: '#/components/schemas/Id' }
    SuaTaiLieu:
      type: object
      additionalProperties: false
      required: [row_version, ten]
      properties:
        row_version: { $ref: '#/components/schemas/RowVersion' }
        ten: { type: string, minLength: 1, maxLength: 255 }
    TaiLieu:
      type: object
      additionalProperties: false
      required: [id, phap_nhan_id, ten, tep_id, row_version, tao_luc]
      properties:
        id: { $ref: '#/components/schemas/Id' }
        phap_nhan_id: { $ref: '#/components/schemas/Id' }
        ten: { type: string, minLength: 1, maxLength: 255 }
        tep_id: { $ref: '#/components/schemas/Id' }
        row_version: { $ref: '#/components/schemas/RowVersion' }
        tao_luc: { $ref: '#/components/schemas/ThoiDiem' }

    TaiLenTep:
      type: object
      additionalProperties: false
      required: [tep, muc_dich]
      properties:
        tep:
          type: string
          format: binary
          description: Toi da 20971520 bytes; server dem bytes khi stream
        muc_dich:
          type: string
          enum: [tai_lieu, goi_module]
        tai_lieu_id:
          $ref: '#/components/schemas/Id'
      description: |
        Tep chua gan tai lieu chi chu tai len hoac Admin dung pham vi duoc doc.
        Khi gan tai lieu, Core kiem quyen tai lieu va phap nhan.
        muc_dich tai_lieu can header phap nhan khop; goi_module chi Admin,
        bo header va cam tai_lieu_id, tao tep he thong. Can cu: R:11.
      allOf:
        - if:
            properties:
              muc_dich: { const: goi_module }
          then:
            not:
              required: [tai_lieu_id]
    Tep:
      description: |
        phap_nhan_id null chi tep he thong, tai_lieu_id phai null, chi Admin doc/tai.
        Tep ket qua giu cung pham vi voi ket qua/viec va quan he quyen tai Core.
        Can cu: R:11; O:21.
      allOf:
        - if:
            properties:
              phap_nhan_id: { type: 'null' }
          then:
            properties:
              tai_lieu_id: { type: 'null' }
      type: object
      additionalProperties: false
      required:
        - id
        - phap_nhan_id
        - tai_lieu_id
        - ten_tep
        - mime
        - kich_thuoc_byte
        - sha256
        - het_han_luc
      properties:
        id: { $ref: '#/components/schemas/Id' }
        phap_nhan_id: { type: [string, 'null'], format: uuid }
        tai_lieu_id: { type: [string, 'null'], format: uuid }
        ten_tep: { type: string, minLength: 1, maxLength: 255 }
        mime: { type: string, minLength: 1, maxLength: 127 }
        kich_thuoc_byte: { type: integer, minimum: 0 }
        sha256: { type: string, pattern: '^[a-f0-9]{64}$' }
        het_han_luc: { type: [string, 'null'], format: date-time }

    KetQua:
      type: object
      additionalProperties: false
      required:
        - id
        - phap_nhan_id
        - viec_id
        - tep_id
        - contract
        - bien_the
        - trang_thai_duyet
        - revision
        - nguon_tep_ids
        - tao_luc
        - het_han_luc
      properties:
        id: { $ref: '#/components/schemas/Id' }
        phap_nhan_id: { type: [string, 'null'], format: uuid }
        viec_id: { $ref: '#/components/schemas/Id' }
        tep_id: { $ref: '#/components/schemas/Id' }
        contract:
          type: string
          enum:
            - van_ban_tai_lieu.v1
            - du_lieu_bang.v1
            - tham_so.v1
            - noi_dung_da_che.v1
            - tra_loi_ai.v1
            - hoa_don.v1
            - bao_cao_quan_tri.v1
        bien_the:
          type: string
          enum: [goc, ocr_chua_che, da_che, khac]
        trang_thai_duyet:
          type: string
          enum: [nhap, can_duyet, da_duyet, tu_choi, khong_ap_dung]
        revision: { type: integer, minimum: 1 }
        nguon_tep_ids:
          type: array
          maxItems: 1000
          uniqueItems: true
          items: { $ref: '#/components/schemas/Id' }
        tao_luc: { $ref: '#/components/schemas/ThoiDiem' }
        het_han_luc: { type: [string, 'null'], format: date-time }
      description: |
        Chi metadata; noi dung tai qua tep_id va contract theo phieu SDK.
        Ket qua/tep quan tri he thong cung phap_nhan_id null, chi Admin doc/tai,
        bo header phap nhan; khong gan phap nhan gia hoac suy quyen nghiep vu.
        GET ket-qua lay tep_id, GET tep/{tep_id}/noi-dung tai bytes tu kho Core.
        Khong co route ket-qua/{id}/noi-dung. Can cu: R:10; R:11; O:21.
        Khong dong nhat succeeded voi da_duyet.

    TrangThaiTienTrinh:
      type: string
      enum: [stopped, starting, ready, busy, dang_dung, failed]
      description: |
        dang_dung tu choi request moi 503 TIEN_TRINH_DANG_DUNG, Retry-After 2.
        Quyet dinh dong va dem request dong bo cung khoa voi dispatch. Can cu: O:20.
    CheDoChay:
      type: string
      enum: [tu_kich_hoat_tu_dong, giu_lau_hon, luon_chay]
    ChucNang:
      type: object
      additionalProperties: false
      required:
        - ma
        - schema_vao
        - schema_ra
        - san_sang
        - tep_toi_da_byte
        - dong_thoi_toi_da
      properties:
        ma: { type: string, minLength: 1, maxLength: 128 }
        schema_vao: { type: string, minLength: 1, maxLength: 255 }
        schema_ra: { type: string, minLength: 1, maxLength: 255 }
        san_sang: { type: boolean }
        tep_toi_da_byte: { type: integer, minimum: 0 }
        dong_thoi_toi_da: { type: integer, minimum: 1 }
      description: |
        schema_vao/schema_ra la ID schema da dang ky, khong phai URL client dua vao.
        Registry chi duoc cong bo sau khi schema va adapter da kiem tuong thich.
    BoPhan:
      type: object
      additionalProperties: false
      required:
        - ma
        - phien_ban
        - trang_thai
        - row_version
        - che_do_chay
        - chuc_nang
      properties:
        ma: { $ref: '#/components/schemas/Ma' }
        phien_ban: { type: string, minLength: 1, maxLength: 64 }
        trang_thai: { $ref: '#/components/schemas/TrangThaiTienTrinh' }
        row_version: { $ref: '#/components/schemas/RowVersion' }
        che_do_chay: { $ref: '#/components/schemas/CheDoChay' }
        chuc_nang:
          type: array
          maxItems: 1000
          items: { $ref: '#/components/schemas/ChucNang' }

    LenhEngine:
      oneOf:
        - $ref: '#/components/schemas/LenhOcr'
        - $ref: '#/components/schemas/LenhMask'
        - $ref: '#/components/schemas/LenhTrich'
        - $ref: '#/components/schemas/LenhDocHoaDon'
        - $ref: '#/components/schemas/LenhTaiHoaDon'
    LenhOcr:
      type: object
      additionalProperties: false
      required: [capability, tai_lieu_id, tep_id, bo_xu_ly, ep_ocr]
      properties:
        capability:
          type: string
          enum: [ocr.trich_van_ban@1, ocr.trich_bang@1]
        tai_lieu_id: { $ref: '#/components/schemas/Id' }
        tep_id: { $ref: '#/components/schemas/Id' }
        bo_xu_ly:
          type: string
          enum: [tu_dong, abbyy, tesseract, vietocr, dual]
        ep_ocr: { type: boolean }
      description: Chi ma_engine e_ocr; backend khong san sang thi khong tu doi ngam
    LenhMask:
      type: object
      additionalProperties: false
      required: [capability, ket_qua_id, revision, danh_muc_phien_ban]
      properties:
        capability:
          type: string
          enum:
            - mask.phat_hien@1
            - mask.che_van_ban@1
            - mask.mo_che@1
        ket_qua_id: { $ref: '#/components/schemas/Id' }
        revision: { type: integer, minimum: 1 }
        danh_muc_phien_ban: { type: string, minLength: 1, maxLength: 128 }
      description: |
        Chi ma_engine e_mask. Khong cong bo che_tai_lieu khi chua co contract.
        mo_che can quyen rieng va anh xa con hieu luc.
    LenhTrich:
      type: object
      additionalProperties: false
      required: [capability, tai_lieu_id, tep_id, loai, danh_muc_phien_ban]
      properties:
        capability: { type: string, const: trich.tham_so_hop_dong@1 }
        tai_lieu_id: { $ref: '#/components/schemas/Id' }
        tep_id: { $ref: '#/components/schemas/Id' }
        loai: { type: string, pattern: '^[A-Z][A-Z0-9_]{0,31}$' }
        danh_muc_phien_ban: { type: string, minLength: 1, maxLength: 128 }
      description: |
        Chi ma_engine e_trich_xuat; loai phai co catalog va adapter duoc duyet.
        Khong suy tu schema nay rang moi loai da duoc ho tro.
    LenhDocHoaDon:
      type: object
      additionalProperties: false
      required: [capability, tep_id, ho_so_doc]
      properties:
        capability:
          type: string
          enum: [hoa_don.doc_xml@1, hoa_don.doc_zip_bang_ke@1]
        tep_id: { $ref: '#/components/schemas/Id' }
        ho_so_doc: { type: string, minLength: 1, maxLength: 128 }
      description: Chi ma_engine e_hoa_don; ho_so_doc phai duoc dang ky
    LenhTaiHoaDon:
      type: object
      additionalProperties: false
      required: [capability, nguon_id, tu_ngay, den_ngay, huong]
      properties:
        capability: { type: string, const: hoa_don.tai_cong_thue@1 }
        nguon_id: { $ref: '#/components/schemas/Id' }
        tu_ngay: { type: string, format: date }
        den_ngay: { type: string, format: date }
        huong: { type: string, enum: [mua_vao, ban_ra] }
      description: |
        Chi ma_engine e_hoa_don; Core kiem nguon thuoc phap nhan.
        tu_ngay <= den_ngay va khoang ngay theo han muc nguon.
        Dang nhap/CAPTCHA la buoc nguoi dung, co the waiting_input.

    QuyTrinh:
      type: object
      additionalProperties: false
      required: [id, ma_module, ten, phien_ban]
      properties:
        id: { $ref: '#/components/schemas/Id' }
        ma_module: { $ref: '#/components/schemas/Ma' }
        ten: { type: string, minLength: 1, maxLength: 255 }
        phien_ban: { type: string, minLength: 1, maxLength: 64 }
    LanChayQuyTrinh:
      type: object
      additionalProperties: false
      required: [phien_ban, tai_lieu_ids, ket_qua_ids]
      properties:
        phien_ban: { type: string, minLength: 1, maxLength: 64 }
        tai_lieu_ids:
          type: array
          maxItems: 100
          uniqueItems: true
          items: { $ref: '#/components/schemas/Id' }
        ket_qua_ids:
          type: array
          maxItems: 100
          uniqueItems: true
          items: { $ref: '#/components/schemas/Id' }

    TrangThaiViec:
      description: |
        running mat heartbeat sau restart/het lease thanh interrupted, khong succeeded.
        Chi xep lai khi contract khai thu_lai_an_toan, doi chieu tac dong/bien nhan,
        kiem quyen va cap uy nhiem the he moi; khong chay lai ghi/nhap mu. Can cu: O:18; D:301.
      type: string
      enum:
        - queued
        - running
        - waiting_input
        - cancel_requested
        - cancelled
        - succeeded
        - failed
        - interrupted
    DaNhanViec:
      type: object
      additionalProperties: false
      required: [viec_id, trang_thai, request_id]
      properties:
        viec_id: { $ref: '#/components/schemas/Id' }
        trang_thai: { $ref: '#/components/schemas/TrangThaiViec' }
        request_id: { $ref: '#/components/schemas/Id' }
    Viec:
      type: object
      additionalProperties: false
      required:
        - id
        - phap_nhan_id
        - ma_module
        - trang_thai
        - tien_do
        - ket_qua_ids
        - loi
        - tao_luc
        - cap_nhat_luc
      properties:
        id: { $ref: '#/components/schemas/Id' }
        phap_nhan_id: { type: [string, 'null'], format: uuid }
        ma_module: { type: [string, 'null'], pattern: '^[a-z][a-z0-9_]{0,31}$' }
        trang_thai: { $ref: '#/components/schemas/TrangThaiViec' }
        tien_do: { type: [integer, 'null'], minimum: 0, maximum: 100 }
        ket_qua_ids:
          type: array
          maxItems: 1000
          uniqueItems: true
          items: { $ref: '#/components/schemas/Id' }
        loi:
          oneOf:
            - $ref: '#/components/schemas/Loi'
            - type: 'null'
        tao_luc: { $ref: '#/components/schemas/ThoiDiem' }
        cap_nhat_luc: { $ref: '#/components/schemas/ThoiDiem' }
    DeNghiHuy:
      type: object
      additionalProperties: false
      required: [ly_do]
      properties:
        ly_do: { type: string, minLength: 1, maxLength: 1000 }

    ThaoTacModule:
      type: object
      additionalProperties: false
      required: [row_version, thao_tac]
      properties:
        row_version: { $ref: '#/components/schemas/RowVersionHoacChuaCo' }
        thao_tac:
          type: string
          enum: [kiem_goi, cai_dat, nang_cap, khoi_dong, dung]
        tep_goi_id: { $ref: '#/components/schemas/Id' }
      allOf:
        - if:
            properties:
              thao_tac: { enum: [kiem_goi, cai_dat, nang_cap] }
          then:
            required: [tep_goi_id]
        - if:
            properties:
              thao_tac: { const: cai_dat }
          then:
            properties:
              row_version: { const: '0' }
        - if:
            properties:
              thao_tac: { enum: [khoi_dong, dung] }
          then:
            properties:
              row_version: { $ref: '#/components/schemas/RowVersion' }
            not:
              required: [tep_goi_id]
      description: |
        Kiem goi co the dung row_version "0" neu module chua dang ky.
        Nang cap bat buoc row_version hien tai, khac "0".
        Kiem lai goi va hash duoc ghim truoc cai/nang cap.
    CheDoModule:
      type: object
      additionalProperties: false
      required: [row_version, che_do, nguoi_thu_ids]
      properties:
        row_version: { $ref: '#/components/schemas/RowVersion' }
        che_do: { type: string, enum: [TAT, THU, VAN_HANH] }
        nguoi_thu_ids:
          type: array
          maxItems: 1000
          uniqueItems: true
          items: { $ref: '#/components/schemas/Id' }
      description: |
        Nguoi thu phai la thanh vien hop le cua phap nhan.
        Danh sach nguoi thu chi co hieu luc khi che_do THU.

    DangKyEngine:
      type: object
      additionalProperties: false
      required: [ma_engine, phien_ban, ho_so_mau_id]
      properties:
        ma_engine: { $ref: '#/components/schemas/Ma' }
        phien_ban: { type: string, minLength: 1, maxLength: 64 }
        ho_so_mau_id: { $ref: '#/components/schemas/Id' }
    HoSoChay:
      type: object
      additionalProperties: false
      required:
        - row_version
        - ho_so_mau_id
        - cho_khoi_dong_giay
        - ranh_toi_da_giay
        - che_do_chay
      properties:
        row_version: { $ref: '#/components/schemas/RowVersion' }
        ho_so_mau_id: { $ref: '#/components/schemas/Id' }
        cho_khoi_dong_giay:
          type: integer
          minimum: 1
          maximum: 120
          default: 120
        ranh_toi_da_giay:
          type: integer
          minimum: 60
          maximum: 86400
          default: 300
        che_do_chay: { $ref: '#/components/schemas/CheDoChay' }
    ThaoTacEngine:
      type: object
      additionalProperties: false
      required: [row_version, thao_tac]
      properties:
        row_version: { $ref: '#/components/schemas/RowVersion' }
        thao_tac:
          type: string
          enum: [kiem_tra, khoi_dong, dung]

    QuyenTaiNguyen:
      type: object
      additionalProperties: false
      required: [tai_nguyen, thao_tac, truong, bien_the, pham_vi]
      properties:
        tai_nguyen: { type: string, minLength: 1, maxLength: 128 }
        thao_tac:
          type: array
          minItems: 1
          maxItems: 100
          uniqueItems: true
          items: { type: string, minLength: 1, maxLength: 64 }
        truong:
          type: array
          maxItems: 500
          uniqueItems: true
          items: { type: string, minLength: 1, maxLength: 128 }
        bien_the:
          type: array
          maxItems: 10
          uniqueItems: true
          items:
            type: string
            enum: [goc, ocr_chua_che, da_che, khac]
        pham_vi:
          type: string
          enum: [phap_nhan, ho_so_duoc_cap]
      description: |
        Tai nguyen/thao tac/truong phai co trong registry va manifest.
        Mang truong rong khong co nghia la tat ca truong.
        Khong nhan bieu thuc SQL hoac dieu kien tuy y.
    CapQuyen:
      type: object
      additionalProperties: false
      required: [row_version, quyen]
      properties:
        row_version: { $ref: '#/components/schemas/RowVersionHoacChuaCo' }
        quyen:
          type: array
          maxItems: 1000
          items: { $ref: '#/components/schemas/QuyenTaiNguyen' }

    MauKhoiDong:
      type: object
      additionalProperties: false
      required:
        - id
        - yeu_cau_luc
        - san_sang_luc
        - khoi_dong_ms
        - xu_ly_viec_ms
        - ranh_truoc_dong_ms
        - ram_dinh_byte
        - cpu_ms
        - ket_cuc
      properties:
        id: { $ref: '#/components/schemas/Id' }
        yeu_cau_luc: { $ref: '#/components/schemas/ThoiDiem' }
        san_sang_luc: { type: [string, 'null'], format: date-time }
        khoi_dong_ms: { type: [integer, 'null'], minimum: 0 }
        xu_ly_viec_ms: { type: [integer, 'null'], minimum: 0 }
        ranh_truoc_dong_ms: { type: [integer, 'null'], minimum: 0 }
        ram_dinh_byte: { type: [integer, 'null'], minimum: 0 }
        cpu_ms: { type: [integer, 'null'], minimum: 0 }
        ket_cuc:
          type: string
          enum: [dang_chay, da_dong, khoi_dong_loi, gian_doan]
      description: null la chua do/chua ket thuc, khong thay bang 0
    SoLanNgay:
      type: object
      additionalProperties: false
      required: [ngay, so_lan]
      properties:
        ngay: { type: string, format: date }
        so_lan: { type: integer, minimum: 0 }
    CanCuDo:
      type: object
      additionalProperties: false
      required:
        - tu_ngay
        - den_ngay
        - so_mau
        - khoi_dong_p50_ms
        - khoi_dong_p95_ms
        - ram_dinh_byte
        - cpu_tong_ms
        - so_lan_ngay
        - thieu_so_do
      properties:
        tu_ngay: { type: string, format: date }
        den_ngay: { type: string, format: date }
        so_mau: { type: integer, minimum: 0 }
        khoi_dong_p50_ms: { type: [integer, 'null'], minimum: 0 }
        khoi_dong_p95_ms: { type: [integer, 'null'], minimum: 0 }
        ram_dinh_byte: { type: [integer, 'null'], minimum: 0 }
        cpu_tong_ms: { type: [integer, 'null'], minimum: 0 }
        so_lan_ngay:
          type: array
          maxItems: 366
          items: { $ref: '#/components/schemas/SoLanNgay' }
        thieu_so_do:
          type: array
          maxItems: 20
          uniqueItems: true
          items:
            type: string
            enum: [khoi_dong, xu_ly_viec, ranh_truoc_dong, ram, cpu]
    SoDo:
      type: object
      additionalProperties: false
      required: [loai, ma, can_cu, danh_sach, con_tiep, con_tro_tiep]
      properties:
        loai: { type: string, enum: [module, engine] }
        ma: { $ref: '#/components/schemas/Ma' }
        can_cu: { $ref: '#/components/schemas/CanCuDo' }
        danh_sach:
          type: array
          maxItems: 100
          items: { $ref: '#/components/schemas/MauKhoiDong' }
        con_tiep: { type: boolean }
        con_tro_tiep: { type: [string, 'null'], maxLength: 4096 }
      description: can_cu thong ke toan khoang ngay, khong chi trang hien tai
    DeXuat:
      type: object
      additionalProperties: false
      required:
        - id
        - loai
        - ma
        - row_version_cau_hinh
        - che_do_hien_tai
        - che_do_de_xuat
        - ranh_toi_da_giay
        - ly_do
        - can_cu
        - tao_luc
        - da_ap_dung
      properties:
        id: { $ref: '#/components/schemas/Id' }
        loai: { type: string, enum: [module, engine] }
        ma: { $ref: '#/components/schemas/Ma' }
        row_version_cau_hinh: { $ref: '#/components/schemas/RowVersion' }
        che_do_hien_tai: { $ref: '#/components/schemas/CheDoChay' }
        che_do_de_xuat: { $ref: '#/components/schemas/CheDoChay' }
        ranh_toi_da_giay:
          type: integer
          minimum: 60
          maximum: 86400
        ly_do: { type: string, minLength: 1, maxLength: 2000 }
        can_cu: { $ref: '#/components/schemas/CanCuDo' }
        tao_luc: { $ref: '#/components/schemas/ThoiDiem' }
        da_ap_dung: { type: boolean }
      description: |
        De xuat bat bien, chi Admin ap dung; thieu so lieu phai ghi ro.
        Ban ghi trang thai ap dung khong duoc thay doi noi dung de xuat.
    ApDungDeXuat:
      type: object
      additionalProperties: false
      required: [row_version]
      properties:
        row_version: { $ref: '#/components/schemas/RowVersion' }
      description: Phien ban cau hinh hien tai, khong phai phien ban viec
    DaApDungDeXuat:
      type: object
      additionalProperties: false
      required:
        - de_xuat_id
        - loai
        - ma
        - row_version
        - che_do_chay
        - ranh_toi_da_giay
        - ap_dung_luc
      properties:
        de_xuat_id: { $ref: '#/components/schemas/Id' }
        loai: { type: string, enum: [module, engine] }
        ma: { $ref: '#/components/schemas/Ma' }
        row_version: { $ref: '#/components/schemas/RowVersion' }
        che_do_chay: { $ref: '#/components/schemas/CheDoChay' }
        ranh_toi_da_giay:
          type: integer
          minimum: 60
          maximum: 86400
        ap_dung_luc: { $ref: '#/components/schemas/ThoiDiem' }

    LuuGhiChuBaoGia:
      type: object
      additionalProperties: false
      required: [row_version, expected_revision, ghi_chu]
      properties:
        row_version: { $ref: '#/components/schemas/RowVersion' }
        expected_revision: { type: integer, minimum: 1 }
        ghi_chu: { type: string, maxLength: 4000 }
    GhiChuBaoGia:
      type: object
      additionalProperties: false
      required: [id, phap_nhan_id, row_version, revision, ghi_chu]
      properties:
        id: { $ref: '#/components/schemas/Id' }
        phap_nhan_id: { $ref: '#/components/schemas/Id' }
        row_version: { $ref: '#/components/schemas/RowVersion' }
        revision: { type: integer, minimum: 1 }
        ghi_chu: { type: string, maxLength: 4000 }

    TrangPhapNhan:
      type: object
      additionalProperties: false
      required: [danh_sach, con_tiep, con_tro_tiep]
      properties:
        danh_sach:
          type: array
          maxItems: 100
          items: { $ref: '#/components/schemas/PhapNhan' }
        con_tiep: { type: boolean }
        con_tro_tiep: { type: [string, 'null'], maxLength: 4096 }
    TrangTaiLieu:
      type: object
      additionalProperties: false
      required: [danh_sach, con_tiep, con_tro_tiep]
      properties:
        danh_sach:
          type: array
          maxItems: 100
          items: { $ref: '#/components/schemas/TaiLieu' }
        con_tiep: { type: boolean }
        con_tro_tiep: { type: [string, 'null'], maxLength: 4096 }
    TrangViec:
      type: object
      additionalProperties: false
      required: [danh_sach, con_tiep, con_tro_tiep]
      properties:
        danh_sach:
          type: array
          maxItems: 100
          items: { $ref: '#/components/schemas/Viec' }
        con_tiep: { type: boolean }
        con_tro_tiep: { type: [string, 'null'], maxLength: 4096 }
      x-can-cu: 'R:10; O:18'
    TrangKetQua:
      type: object
      additionalProperties: false
      required: [danh_sach, con_tiep, con_tro_tiep]
      properties:
        danh_sach:
          type: array
          maxItems: 100
          items: { $ref: '#/components/schemas/KetQua' }
        con_tiep: { type: boolean }
        con_tro_tiep: { type: [string, 'null'], maxLength: 4096 }
    TrangBoPhan:
      type: object
      additionalProperties: false
      required: [danh_sach, con_tiep, con_tro_tiep]
      properties:
        danh_sach:
          type: array
          maxItems: 100
          items: { $ref: '#/components/schemas/BoPhan' }
        con_tiep: { type: boolean }
        con_tro_tiep: { type: [string, 'null'], maxLength: 4096 }
    TrangQuyTrinh:
      type: object
      additionalProperties: false
      required: [danh_sach, con_tiep, con_tro_tiep]
      properties:
        danh_sach:
          type: array
          maxItems: 100
          items: { $ref: '#/components/schemas/QuyTrinh' }
        con_tiep: { type: boolean }
        con_tro_tiep: { type: [string, 'null'], maxLength: 4096 }
    TrangDeXuat:
      type: object
      additionalProperties: false
      required: [danh_sach, con_tiep, con_tro_tiep]
      properties:
        danh_sach:
          type: array
          maxItems: 100
          items: { $ref: '#/components/schemas/DeXuat' }
        con_tiep: { type: boolean }
        con_tro_tiep: { type: [string, 'null'], maxLength: 4096 }

x-quy-uoc-bat-buoc:
  xac_thuc:
    phien_ranh_giay: 1800
    phien_tuyet_doi_giay: 28800
    tien_phien_giay: 600
    csrf_gan_voi_phien: true
    tls_bat_buoc_ngoai_loopback: true
    x-can-cu: 'O:21'
    origin_phai_khop: true
    cors_tuy_y: false
  gioi_han:
    json_toi_da_byte: 1048576
    tep_toi_da_byte: 20971520
    capability_co_the_gioi_han_nho_hon: true
    ho_tro_range: false
    ho_tro_upload_tiep_tuc: false
  timeout:
    request_dong_bo_giay: 30
    khoi_dong_toi_da_giay: 120
    drain_toi_da_giay: 300
    ranh_mac_dinh_giay: 300
    x-can-cu: 'O:20'
    gian_cach_khoi_dong_loi_giay: [2, 4]
    loi_lien_tiep_giu_failed: 3
    chi_admin_mo_lai: true
    khoa_khoi_dong_loi_luu_ben: true
    dang_dung_tu_choi_request_moi: true
    dong_ranh_cung_khoa_dispatch: true
    dem_ca_request_dong_bo: true
    drain_qua_han_giu_instance_va_cong: true
  chong_trung:
    header: Idempotency-Key
    x-can-cu: 'O:31; src/kho_tri_thuc/ha_tang/pg_migrations.py:3385'
    core:
      chu_bien_nhan: Core
      giu_sau_ket_qua_giay: 86400
      giu_tiep_khi_chua_ket_thuc: true
      cung_transaction: true
    module:
      chu_bien_nhan: module_qua_SDK
      core_chi_khoa_request_dang_chay: true
      chuyen_key_trong_token_ky: true
      vinh_vien_bat_bien: true
      cung_transaction_nghiep_vu: true
      pham_vi: [phap_nhan_id, module, operation, client_key]
      kiem_quyen_doc_ket_qua_truoc_replay: true
      nguon_doi_chieu_504: bien_nhan_module
    fingerprint: operation_va_body_logic_chuan_hoa_gom_id_dich_hash_tep
    fingerprint_khong_gom: [method, duong_dan, client_key]
    kiem_quyen_truoc_replay: true
    replay_cung_viec_id: true
    khong_tuyen_bo_exactly_once: true
  phan_trang:
    cursor_ttl_giay: 900
    cursor_gan_nguoi_dung_phap_nhan_bo_loc: true
    con_tro_tiep_null_khi_het: true
    khong_cam_ket_snapshot_bat_bien: true
  lien_tien_trinh:
    moi_module_mot_tien_trinh: true
    cong_noi_bo_loopback: true
    token_ngu_canh_co_chu_ky: true
    token_ttl_toi_da_giay: 30
    x-can-cu: 'O:19; D:135; D:257; D:301'
    ma_uy_nhiem_bi_mat_khong_phai_SID: true
    ham_csdl_bam_doi_chieu: loi.phien_xac_thuc
    xac_minh: [session_user, module, phap_nhan_id, han, thu_hoi, hanh_dong, viec_id, the_he_lease]
    khong_tin_GUC_danh_tinh_tu_khai: true
    credential_SDK_rieng_moi_instance: true
    bootstrap: stdin_hoac_handle_cung_kenh_fromshare
    thu_hoi_credential_khi_dung_crash: true
    cam_bi_mat_qua: [bien_moi_truong, dong_lenh, manifest, log]
    engine_va_may_phu_khong_login_CSDL: true
    chuyen_socket_chi_may_Core: true
    may_phu_chi_keo_viec_khong_cong_nhan: true
    rang_buoc_instance_method_path_body_hash: true
    khong_chuyen_cookie_nguoi_dung: true
    kiem_quyen_hien_hanh: true
    cong_co_dinh_theo_so_cong: true
    chuyen_giao_o_nghe_uu_tien: true
    engine_cu_co_che_do_chuyen_tiep: true
    khong_dung_ung_dung_la: true
  du_lieu:
    ten_khoi: theo_phieu_CSDL
    contract_noi_dung_tep: theo_phieu_SDK
    x-can-cu: 'O:16; O:18; O:21; R:11'
    loi_chi_tiet_chi_ten_truong_va_ma: true
    loi_module_chua_khai_tra_502: true
    tep_module_qua_SDK_kho_Core: true
    tep_he_thong_phap_nhan_null_chi_Admin: true
    viec_mat_heartbeat_thanh_interrupted: true
    chi_xep_lai_khi_contract_thu_lai_an_toan_va_da_doi_chieu: true
    giam_sat_viec: MTQ_viec.giam_sat_theo_phap_nhan_va_module
    theo_doi_viec: polling_snapshot
    SSE_cong_khai: false
    chinh_sach_retention_phai_duoc_duyet: true
    succeeded_khong_tu_phe_duyet: true
    kiem_quyen_api_download_viec_nen: true
  quan_tri:
    de_xuat_hang_tuan: true
    chi_admin_ap_dung: true
    khong_tu_doi_che_do: true
    khong_mac_dinh_engine_nao_luon_chay: true
    khong_nhan_lenh_shell_hoac_khoa_tuy_y: true
```

## Vòng 2 — đã xử lý

Mã O theo mục/C1 của review Opus; R-1…R-6 theo thứ tự dòng phát hiện Codex (`O:14`, `O:26`, `R:7`). Thiết kế vẫn chờ duyệt, không xác nhận đã lập trình.

| Mã phát hiện | Chỗ sửa |
|---|---|
| O-C1 (chặn) | §2.4: Core cùng transaction/24 giờ; module qua SDK/K2 vĩnh viễn; fingerprint không path; đối chiếu 504; thân `docs/47-core/g1/DAC-TA-API.md:106`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:2501` |
| O-1 | §2.3: chi_tiet an toàn và lỗi module chưa khai → 502; schema Loi; thân `docs/47-core/g1/DAC-TA-API.md:81`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:1694` |
| O-3a | §2.6: mất heartbeat → interrupted, đối chiếu trước thử lại; enum/quy tắc việc; thân `docs/47-core/g1/DAC-TA-API.md:135`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:2037` |
| O-3b | §2.6/§3: MTQ viec.giam_sat theo pháp nhân + module, ngoài quyền → 404; thân `docs/47-core/g1/DAC-TA-API.md:137`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:978` |
| O-4a | §4.2: mã bí mật, hàm băm đối chiếu loi.phien_xac_thuc, mã việc/thế hệ lease, bảng login; thân `docs/47-core/g1/DAC-TA-API.md:220`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:2528` |
| O-4b | §4.2: credential riêng mỗi instance/bootstrap, thu hồi, cấm môi trường/dòng lệnh; thân `docs/47-core/g1/DAC-TA-API.md:222`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:2538` |
| O-5a | §4.1/§5: dang_dung, từ chối request mới, cùng khóa dispatch/đếm request đồng bộ; thân `docs/47-core/g1/DAC-TA-API.md:208`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:1883` |
| O-5b | §4.3: giãn 2/4 giây, ba lỗi giữ failed, lưu bền, chờ Admin; thân `docs/47-core/g1/DAC-TA-API.md:252`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:2494` |
| O-5c | §4.3: chuyển socket chỉ máy Core, máy phụ chỉ kéo việc; thân `docs/47-core/g1/DAC-TA-API.md:256`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:2543` |
| O-6a | §2.1: TLS ngoài loopback, cookie Secure, DEMO riêng; thân `docs/47-core/g1/DAC-TA-API.md:42`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:2477` |
| O-6b | §2.6: module ghi SDK/kho Core, tải theo ID, không proxy bytes; thân `docs/47-core/g1/DAC-TA-API.md:143`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:728` |
| O-7; R-4 | §7: ba câu, đăng nhập/retention hỏi chung CSDL; báo kỹ thuật; ghép phê duyệt V/alias; thân `docs/47-core/g1/DAC-TA-API.md:420` |
| O-để sau (audit/CAS) | §2.4/§5: CAS bắt buộc theo operation và audit PUT hồ sơ; thân `docs/47-core/g1/DAC-TA-API.md:274`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:1201` |
| R-1 (chặn) | §1/§3, ví dụ, OpenAPI và bảng ánh xạ: tên route gạch nối; thân `docs/47-core/g1/DAC-TA-API.md:28`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:1377` |
| R-2 (chặn) | §2.6/§3: GET viec, GET che-do/ho-so-chay; polling/tải hai bước/thao-tac; không đích Core giả định; thân `docs/47-core/g1/DAC-TA-API.md:173`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:931` |
| R-3 | §2.2/§2.6: kết quả/tệp hệ thống null chỉ Admin, không pháp nhân giả; header tùy phạm vi; thân `docs/47-core/g1/DAC-TA-API.md:59`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:1798` |
| R-5 | §1: thay nguồn KS-E về revision, duyệt, TTL/RAM và readiness; thân `docs/47-core/g1/DAC-TA-API.md:26` |
| R-6 (gợi ý) | 409 tường minh tại mọi operation ghi chống trùng/CAS; ba ví dụ XungDot; thân `docs/47-core/g1/DAC-TA-API.md:117`, OpenAPI `docs/47-core/g1/DAC-TA-API.md:1594` |

**Kiểm tĩnh vòng 2:** 42/42 operation thân ↔ OpenAPI, 33 path, 235 `$ref` có đích; không trùng `operationId`, alias YAML có anchor. Bảng ánh xạ giữ nguyên 147 dòng nguồn/tệp:dòng (các mẫu gộp), 88 tham chiếu đích Core đều khớp 27 dạng path/giá trị sau khi đối chiếu tham số. Đã kiểm UTF-8 không BOM và `git diff --check`; không chạy test nghiệp vụ. Môi trường chưa có YAML/OpenAPI validator dùng được, nên chưa chứng nhận cú pháp/schema bằng validator đầy đủ hoặc runtime; không cài thêm hay gọi dịch vụ (`docs/47-core/g1/GIAO-G1B.md:8`; contract ở các vị trí trong bảng trên).
