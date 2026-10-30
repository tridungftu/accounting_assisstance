# CHUẨN CORE API v1.0

**Tệp:** `CHUAN-CORE-API-v1.0.md`  
**Phiên bản:** v1.0  
**Ngày Anh duyệt phiếu CSDL/API:** 30/10/2026 · **Văn bản chuẩn:** chờ Anh xem (CD-034 mục 4)

**Đối tượng:** Người lập trình module, engine, adapter và giao diện kết nối Core; áp dụng cho lập trình viên nội bộ và AI worker.

**Căn cứ đã duyệt:**

- `docs\47-core\PHIEU-DUYET-API.md`: Anh duyệt **1A, 2A** — module tự đóng sau **5 phút rảnh**; mỗi tệp tải lên **không quá 20 MB**.
- `docs\47-core\PHIEU-DUYET-CSDL.md`: Anh duyệt **1A, 2A, 3A** — CSDL xác minh mã bí mật do Core cấp; chính sách giữ dữ liệu tạm theo phương án A; Core quản lý tài khoản người dùng.
- `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`, CD-026 đến CD-036; trực tiếp áp dụng CD-027, CD-028, CD-029, CD-031, CD-032, CD-033 và CD-034.
- Đặc tả kỹ thuật: `docs\47-core\g1\DAC-TA-API.md`, `ANH-XA-ROUTE.md`, `DAC-TA-CSDL.md`, `ANH-XA-MIGRATION.md`.

Đây là bản chuẩn thiết kế API tập hợp các quyết định từ phiếu đã duyệt; văn bản chuẩn chờ Anh xem, không phải xác nhận các chức năng đã được triển khai. Việc mở lại lập trình thực hiện theo chỉ đạo riêng; bản chuẩn này không thay thế điều kiện duyệt SDK bản 2 và CD mở lại lập trình.

## 1. Thay đổi

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| v1.0 | 30/10/2026 | Bản đầu; tập hợp quy tắc API Core đã duyệt để hướng dẫn lập trình module mới. |

v1.0 (sửa trước khi gửi Anh): theo review Opus + Codex

Mọi thay đổi sau v1.0 phải tăng phiên bản và bổ sung vào mục này.

## 2. Kết luận

1. Người dùng chỉ kết nối Core; API công khai dùng tiền tố `/api/v1/`.
2. Nghiệp vụ module nằm dưới `/api/v1/module/{ma_module}/…`; từng route phải đăng ký riêng.
3. Core xác thực phiên, kiểm pháp nhân, quyền, Origin/CSRF và chuyển tiếp yêu cầu.
4. Lỗi dùng một cấu trúc chung, thông điệp tiếng Việt và `request_id`.
5. Việc lâu trả `202` cùng `viec_id`; hủy là đề nghị; gián đoạn phải thể hiện bằng `interrupted`.
6. Core giữ biên nhận operation Core; module giữ biên nhận nghiệp vụ vĩnh viễn, cùng transaction.
7. Cập nhật dùng `row_version`, xung đột trả `409`; danh sách dùng phân trang con trỏ.
8. Core giữ/nhả cổng; module tự đóng sau 5 phút rảnh; chỉ Admin áp dụng thay đổi chế độ chạy.

## 3. Bắt buộc

### 3.1. Địa chỉ, namespace và đăng ký route

API công khai của hệ thống nằm dưới:

```text
/api/v1/
```

Nghiệp vụ riêng của module nằm dưới:

```text
/api/v1/module/{ma_module}/...
```

`{ma_module}` là mã module đã đăng ký. `mau_demo` là mã giả định để minh họa quy tắc; ví dụ CAS §6.3 dùng route CRM đã khai báo trong OpenAPI của đặc tả.

Namespace module **không phải wildcard cho phép gọi operation tùy ý**. Mỗi route phải được khai báo riêng trong gói module, có method, đường dẫn và contract đầu vào/đầu ra trước khi đăng ký.

Gói module phải có OpenAPI và JSON Schema tương ứng. Các contract dữ liệu công bố, sự kiện và đầu vào nguồn nằm trong `contract/`, được liệt kê trong `module.json`. Contract nghiệp vụ mới hoặc phiên bản mới của contract đang được dùng phải được Anh duyệt trước khi kích hoạt.

Quy tắc đặt tên:

| Thành phần | Quy tắc |
|---|---|
| Segment đường dẫn | Tiếng Việt không dấu, dùng gạch nối, ví dụ `tai-lieu`, `bao-gia`. |
| Trường JSON, query parameter, path parameter | Tiếng Việt không dấu, dùng `snake_case`. |
| Mã module, engine | Giữ mã đã đăng ký, ví dụ `mau_demo`, `e_ocr`. |
| Tên kỹ thuật đã chuẩn hóa | Giữ `row_version`, `request_id`, tên header, trạng thái và từ khóa OpenAPI. |

Phải phân biệt:

- `GET /api/v1/module` và `GET /api/v1/module/{ma_module}`: metadata do **Core sở hữu**.
- `/api/v1/module/{ma_module}/…`: nghiệp vụ do **module sở hữu**, theo từng route đã đăng ký.

Core tra registry bằng mã module. Client không được chỉ định host, cổng hoặc URL nội bộ để Core chuyển tiếp tùy ý.

`/api/v1/` là major version của API. Thay đổi phá contract phải dùng major mới hoặc operation mới; không âm thầm thay schema mà module đang ghim.

### 3.2. Xác thực phiên, Origin, CSRF và TLS

Core quản lý tài khoản và là đầu mối xác thực người dùng.

Cookie phiên:

```text
__Host-ktt_phien
Secure; HttpOnly; SameSite=Strict; Path=/
```

Cookie không có thuộc tính `Domain`. SID phải ngẫu nhiên; kho phiên hỗ trợ thu hồi và không lưu SID nguyên văn.

Các thời hạn:

| Thành phần | Thời hạn |
|---|---|
| Phiên không hoạt động | 30 phút |
| Tuổi thọ tuyệt đối của phiên | 8 giờ |
| Tiền phiên | 10 phút |

Đăng nhập thành công phải đổi SID và CSRF token. Đăng xuất phải thu hồi phiên tại backend.

Luồng phiên:

1. Client gọi `GET /api/v1/phien` để nhận trạng thái phiên và CSRF token.
2. Khi chưa đăng nhập, Core cấp tiền phiên bằng cookie `__Host-ktt_tien_phien`.
3. Client dùng tiền phiên, Origin và CSRF token để đăng nhập.
4. Các thao tác tiếp theo dùng phiên đã xác thực.

**Mọi thao tác ghi, kể cả đăng nhập và đăng xuất**, phải có:

- `Origin` khớp nguồn Core;
- `X-CSRF-Token` gắn với phiên hoặc tiền phiên hợp lệ.

Thiếu hoặc sai Origin/CSRF trả `403`.

Core phải kiểm Host theo cấu hình triển khai, từ chối `Sec-Fetch-Site: cross-site` và không mở CORS tùy ý. GET không được thực hiện lệnh nghiệp vụ hoặc khởi động việc nền.

**TLS bắt buộc khi phục vụ ngoài loopback.** Không bỏ `Secure` để đăng nhập qua HTTP bằng IP LAN. Môi trường DEMO loopback phải tách riêng và chỉ dùng dữ liệu giả.

Danh tính dịch vụ và kênh nội bộ tách khỏi phiên người dùng. Khóa engine không thay thế phiên đăng nhập.

### 3.3. Pháp nhân và kiểm quyền

Mỗi request thuộc dữ liệu pháp nhân phải gửi:

```text
X-Phap-Nhan-Id: <uuid_phap_nhan>
```

Không dùng một biến toàn cục “pháp nhân đang chọn” để thay ngữ cảnh của từng request.

Core xác thực phiên rồi kiểm đồng thời:

- Thành viên pháp nhân.
- Quyền người dùng theo ma trận thẩm quyền.
- Quyền module và công tắc nghiệp vụ.
- Quyền thao tác.
- Quyền hồ sơ, trường và biến thể nội dung.

`actor`, vai trò hoặc pháp nhân do client tự khai trong body không tạo quyền. Module vẫn phải kiểm quyền nghiệp vụ thuộc trách nhiệm của mình.

Lời gọi engine hoặc quy trình có:

```text
X-Module-Ma: <ma_module>
```

Header này chỉ chọn ngữ cảnh module; Core phải kiểm quyền thực tế của người gọi và module.

Khi người gọi không được phép biết tài nguyên tồn tại, trả `404`. Không tiết lộ sự tồn tại của hồ sơ ngoài phạm vi được xem.

Việc nền phải lưu người tạo, pháp nhân, module và phiên bản contract. Quyền phải được kiểm lại khi nhận việc, trước bước nhạy cảm, trước ghi và trước công bố kết quả. Không chuyển sang quyền toàn hệ thống khi người tạo mất quyền.

Tài nguyên quản trị toàn hệ thống có thể có `phap_nhan_id: null`, chỉ Admin hệ thống được truy cập. Tệp hệ thống có thể có `tai_lieu_id: null`. Không dùng `null` để bỏ kiểm quyền dữ liệu nghiệp vụ.

### 3.4. JSON, schema và định dạng dữ liệu

Core và module cùng kiểm đầu vào/đầu ra bằng JSON Schema 2020-12.

Bắt buộc:

- JSON dùng UTF-8.
- Từ chối trường ngoài schema.
- Không ép kiểu ngầm từ chuỗi sang số hoặc boolean.
- ID nghiệp vụ dùng UUID.
- `row_version` truyền bằng **chuỗi số nguyên**.
- Thời điểm dùng RFC 3339 có múi giờ; response chuẩn UTC với hậu tố `Z`.
- Ngày nghiệp vụ dùng `YYYY-MM-DD`.
- Tiền dùng chuỗi decimal cùng `don_vi_tien`, không dùng float.
- Độ chính xác, giới hạn và cách làm tròn phải theo schema từng trường.

Dữ liệu giao tiếp có hai lớp:

| Lớp | Chủ thể định nghĩa |
|---|---|
| Contract kỹ thuật chung | Core |
| Contract nghiệp vụ | Module sở hữu dữ liệu; Anh duyệt trước khi kích hoạt |

Phiên bản module, quy trình, capability và adapter phải được ghi trong lần chạy. Module không được tự suy thêm capability từ tên engine hoặc từ một route cũ.

### 3.5. Lỗi chuẩn và mã HTTP

Mọi response có header `X-Request-Id`. Core sinh UUID và truyền xuyên tiến trình, việc, bước và lần thử.

Lỗi dùng một cấu trúc:

```json
{
  "ma": "XUNG_DOT_PHIEN_BAN",
  "thong_diep": "Dữ liệu đã được người khác cập nhật. Anh tải lại trước khi lưu.",
  "request_id": "10000000-0000-4000-8000-000000000099",
  "thu_lai_duoc": false
}
```

| Trường | Yêu cầu |
|---|---|
| `ma` | Mã lỗi ổn định, đã khai trong contract. |
| `thong_diep` | Thông điệp tiếng Việt, an toàn để hiển thị. |
| `request_id` | Mã tra cứu yêu cầu. |
| `thu_lai_duoc` | Boolean thể hiện khả năng thử lại an toàn. |
| `chi_tiet` | Tùy chọn; chỉ tên trường đã khai và mã lỗi. |

Dạng `chi_tiet`:

```json
[
  {
    "truong": "ten",
    "ma": "BAT_BUOC"
  }
]
```

Không đưa giá trị đầu vào vào `chi_tiet`. Không trả SQL, DSN, khóa, cookie, header xác thực, đường dẫn vật lý, stack trace hoặc toàn văn tài liệu trong lỗi.

Stack trace chỉ được ghi vào log có kiểm soát, sau khi loại dữ liệu nhạy cảm.

Module phải khai mã lỗi và HTTP status trong contract. Response sai schema hoặc mã lỗi chưa khai phải được Core chuyển thành `502 PHAN_HOI_SAI_CONTRACT`, không chuyển nguyên payload thô.

| HTTP | Cách dùng |
|---|---|
| `200` | Đọc hoặc cập nhật đồng bộ thành công. |
| `201` | Tạo tài nguyên đồng bộ thành công. |
| `204` | Đăng xuất thành công, không body. |
| `202` | Đã ghi bền vững việc hoặc đề nghị hủy; chưa khẳng định hoàn thành. |
| `400` | JSON, header hoặc cursor thiếu/sai cú pháp. |
| `401` | Chưa đăng nhập, phiên hết hạn hoặc bị thu hồi. |
| `403` | Sai Origin/CSRF hoặc thiếu quyền thao tác đối với tài nguyên được phép biết. |
| `404` | Không thấy route/tài nguyên hoặc tài nguyên ngoài phạm vi được thấy. |
| `405` | Method không được hỗ trợ; kèm `Allow`. |
| `409` | Xung đột phiên bản, trạng thái hoặc khóa chống trùng. |
| `410` | Tệp/kết quả tạm hết hạn; chỉ trả sau kiểm quyền. |
| `413` | Vượt giới hạn kích thước. |
| `415` | MIME không hỗ trợ. |
| `422` | Vi phạm schema hoặc quy tắc nghiệp vụ. |
| `429` | Vượt hạn mức hoặc hàng đợi đầy; kèm `Retry-After`. |
| `500` | Lỗi nội bộ đã làm sạch. |
| `502` | Phản hồi/protocol từ tiến trình phụ thuộc không hợp lệ. |
| `503` | Chưa sẵn sàng, đang dừng, khởi động lỗi, xung đột cổng hoặc thiếu chính sách bắt buộc. |
| `504` | Hết thời hạn chờ phản hồi sau khi đã chuyển request. |

Với lệnh ghi chưa rõ kết quả, client phải đối chiếu bằng **cùng khóa chống trùng**, không tạo request mới chỉ vì nhận timeout.

### 3.6. Chống trùng và quyền sở hữu biên nhận

Header bắt buộc cho POST/PATCH/PUT nghiệp vụ và quản trị:

```text
Idempotency-Key: <khoa_chong_trung>
```

Đăng nhập và đăng xuất là ngoại lệ.

Khóa dài 16–128 ký tự ASCII an toàn, theo mẫu:

```text
^[A-Za-z0-9._:-]+$
```

Không chứa dữ liệu nghiệp vụ.

#### a. Operation do Core sở hữu

Core ghi biên nhận cùng transaction với thay đổi dữ liệu hoặc tạo việc.

Phạm vi chống trùng gồm:

```text
nguoi_dung × phap_nhan_hoac_he_thong × module × operation × khoa
```

Biên nhận operation Core lưu tách khỏi biên nhận nghiệp vụ module. Biên nhận operation Core giữ 24 giờ từ kết quả cuối (đặc tả API §2.4); giữ tiếp khi việc còn hoạt động hoặc kết quả chưa xác định; hết hạn không cho phép tạo trùng nghiệp vụ.

#### b. Operation nghiệp vụ module

Đối với `/api/v1/module/{ma_module}/…`:

- Core chỉ giữ khóa request đang chạy.
- Core chuyển nguyên `Idempotency-Key` trong thẻ ngữ cảnh đã ký.
- Module qua SDK ghi biên nhận vào `loi_tai_lieu.bien_nhan_thao_tac`.
- Biên nhận **bất biến, giữ vĩnh viễn**.
- Biên nhận, thay đổi nghiệp vụ và việc được tạo phải nằm trong **cùng transaction, trên cùng kết nối CSDL của module**, qua hàm Core V2.
- Không tạo việc bằng một HTTP request commit độc lập với transaction nghiệp vụ.
- Core không ghi thêm bản biên nhận hoàn tất thứ hai cho operation module.

Khóa duy nhất của biên nhận module:

```text
(phap_nhan_id, module, operation, client_key)
```

Biên nhận phải lưu người tạo. Phải kiểm quyền hành động trước khi tra biên nhận và kiểm quyền đọc kết quả trước khi phát lại, kể cả khi người gửi lại khác người tạo. Không được xem kết quả thì trả `404`.

**Không dọn dòng nào của `loi_tai_lieu.bien_nhan_thao_tac`.** Thời hạn của dấu chống trùng hoặc dữ liệu tạm khác không áp dụng cho bảng này.

#### c. Fingerprint và phát lại

Fingerprint gồm mã operation ổn định và body logic đã chuẩn hóa, bao gồm:

- ID tài nguyên đích.
- Pháp nhân.
- Hash bytes tệp nếu có.

Fingerprint không gồm method, đường dẫn hoặc chính khóa chống trùng. Route cũ và v1 của cùng operation phải chuẩn hóa về cùng operation, body logic và khóa.

| Tình huống | Xử lý |
|---|---|
| Cùng khóa, cùng fingerprint, đã hoàn tất | Trả kết quả cũ hoặc cùng `viec_id`, sau kiểm quyền hiện tại. |
| Cùng khóa, khác fingerprint | `409 KHOA_CHONG_TRUNG_KHAC_NOI_DUNG`. |
| Lệnh đồng bộ còn đang ghi | `409 YEU_CAU_DANG_XU_LY`, `Retry-After: 2`. |
| Timeout/crash ở operation module | Đối chiếu biên nhận module trước khi thực hiện lại. |

Mất khóa đang chạy tại Core không cho phép module bỏ kiểm biên nhận.

Tác động ngoài CSDL phải có cơ chế đối chiếu. Không tuyên bố exactly-once cho toàn bộ tác động ngoài CSDL.

### 3.7. Cập nhật đồng thời và phân trang

#### a. `row_version` và CAS

`row_version` truyền bằng chuỗi số nguyên:

```json
{
  "row_version": "7"
}
```

Module phải so sánh phiên bản và ghi nguyên tử. Phiên bản không khớp trả `409`; không ghi đè thay đổi của người khác.

Mỗi operation phải khai các trường CAS bắt buộc. Nếu nghiệp vụ có `expected_revision`, hash căn cứ hoặc phiên bản mẫu thì giữ các kiểm tra đó cùng `row_version`.

Không tự đồng nhất `expected_revision` với `row_version`.

Nếu request đã thành công được gửi lại với cùng khóa và nội dung, phải phát lại kết quả từ biên nhận sau kiểm quyền; không coi đó là lệnh mới rồi kiểm CAS lại.

#### b. Phân trang

Danh sách dùng:

| Thành phần | Quy định |
|---|---|
| `kich_thuoc_trang` | Mặc định 25, tối đa 100. |
| `con_tro` | Con trỏ opaque. |
| `danh_sach` | Các dòng của trang hiện tại. |
| `con_tiep` | Có trang tiếp hay không. |
| `con_tro_tiep` | Con trỏ trang tiếp; `null` khi hết. |

Phải sắp xếp ổn định theo khóa công bố của tài nguyên và khóa duy nhất. Con trỏ gắn với người dùng, pháp nhân, bộ lọc và thứ tự; thời hạn theo đặc tả là 15 phút.

Không bắt buộc đếm tổng. Phân trang không cam kết snapshot bất biến; quyền được kiểm tại thời điểm đọc.

### 3.8. Việc lâu, theo dõi và hủy

OCR, trích xuất, tải hóa đơn và các operation đã thiết kế là việc lâu phải trả:

```text
202 Accepted
Location: /api/v1/viec/{id}
Retry-After: 2
```

Body có `viec_id`.

Chỉ trả `202` sau khi việc và biên nhận đã được commit bền vững. Không chuyển một lệnh ghi đang dở sang `202` khi chưa có bản ghi việc.

Trạng thái việc:

| Trạng thái | Nghĩa |
|---|---|
| `queued` | Đã xếp hàng. |
| `running` | Đang chạy. |
| `waiting_input` | Chờ đầu vào hoặc xử lý bổ sung. |
| `cancel_requested` | Đã nhận đề nghị hủy. |
| `cancelled` | Đã hủy. |
| `succeeded` | Việc hoàn thành thành công. |
| `failed` | Việc thất bại. |
| `interrupted` | Việc bị gián đoạn. |

Frontend theo dõi bằng polling, tuân thủ `Retry-After`, mặc định 2 giây. API v1 này không công bố SSE. Sau mất kết nối, đọc lại snapshot; không cam kết phát lại sự kiện.

Hủy qua:

```text
POST /api/v1/viec/{id}/huy
```

Hủy là **đề nghị hợp tác**, không hoàn tác tác động đã commit. Gửi lại đề nghị hủy đối với việc đã kết thúc trả trạng thái cuối hiện có.

Sau Core restart hoặc hết lease, việc `running` mất heartbeat phải chuyển `interrupted`. Không suy thành `succeeded`.

Chỉ xếp lại khi:

- Contract khai việc có thể thử lại an toàn.
- Đã đối chiếu tác động và biên nhận.
- Đã kiểm lại quyền.
- Đã thu hồi mã ủy nhiệm thế hệ cũ và cấp mã cho lần thử mới.

Việc ghi/nhập chưa rõ kết quả phải chờ đối chiếu hoặc xử lý, không chạy lại mù.

`GET /viec` chỉ trả việc người tạo còn quyền xem hoặc người có MTQ `viec.giam_sat` đúng pháp nhân và module. Việc hệ thống chỉ Admin được xem. Ngoài quyền thì danh sách loại dòng đó; truy cập theo ID trả `404`.

`succeeded` không đồng nghĩa kết quả đã được phê duyệt.

### 3.9. Tải lên, tải xuống và kết quả

#### a. Tải lên

Tải lên qua:

```text
POST /api/v1/tep
Content-Type: multipart/form-data
```

Quy định:

- Mỗi tệp không quá 20 MB (= 20 MiB = 20.971.520 byte theo OpenAPI của đặc tả; Core đếm byte khi nhận luồng).
- Tiếp tục chịu giới hạn nhỏ hơn của capability.
- JSON tối đa 1 MiB theo đặc tả.
- Không đưa tệp base64 vào JSON.
- Metadata phải có schema.
- Core nhận vào vùng tạm, kiểm kích thước, MIME thực, hash và quyền trước công bố.
- Kiểm nội dung lâu phải chuyển thành việc riêng.
- V1 chưa hỗ trợ upload chia mảnh hoặc tiếp tục upload.

Tải gói module là thao tác quản trị, yêu cầu Admin hệ thống.

Tệp tạm và kết quả OCR/Mask tạm theo chính sách đã duyệt: thành công giữ 24 giờ, lỗi giữ 7 ngày. Bản gốc, kết quả đã duyệt và nhật ký nghiệp vụ không thuộc diện dọn này. Thiếu chính sách tương ứng thì từ chối tiếp nhận; không tự biến dữ liệu RAM-only thành lưu lâu dài.

#### b. Tải xuống

Tải bytes bằng:

```text
GET /api/v1/tep/{id}/noi-dung
```

Core phải kiểm quyền **mỗi lần tải**, trước khi mở luồng bytes. Biết ID không tạo quyền tải.

Không nhận đường dẫn vật lý hoặc URL tùy ý làm đầu vào tải xuống. Frontend dùng `fetch` với cookie và header pháp nhân, sau đó tải blob.

Response tải xuống có:

```text
Content-Disposition: attachment
Cache-Control: no-store
X-Content-Type-Options: nosniff
```

Tên tệp phải được làm sạch. V1 chưa hỗ trợ Range.

#### c. Kết quả và tệp do module tạo

Luồng lấy nội dung kết quả:

1. `GET /api/v1/ket-qua/{id}` lấy metadata và `tep_id`.
2. `GET /api/v1/tep/{tep_id}/noi-dung` tải bytes.

Không có route `/api/v1/ket-qua/{id}/noi-dung`.

Core giữ quan hệ kết quả–tệp và kiểm lại quyền kết quả, biến thể nội dung khi tải.

Module sinh DOCX hoặc báo cáo phải ghi qua SDK vào File Store Core, đăng ký metadata và quan hệ trước công bố. Core không proxy bytes thô từ module.

API kết quả trả metadata và tham chiếu tệp; nội dung JSON bên trong tệp phải theo contract tương ứng.

### 3.10. Core giữ/nhả cổng và vòng đời tiến trình

Mỗi module chạy một tiến trình riêng. Mỗi module/engine trên máy Core có một cổng nội bộ cố định do Core cấp trong sổ cổng thuộc `loi`.

Người dùng chỉ biết địa chỉ Core. Frontend không nhận URL, cổng hoặc credential engine để gọi trực tiếp.

Luồng phục vụ:

1. Core kiểm phiên, Origin/CSRF khi ghi, pháp nhân, quyền, route, schema và phiên bản.
2. Dispatcher tra registry; chỉ chuyển route đã đăng ký.
3. Nếu module chưa chạy, Core dùng khóa phối hợp theo module/node; các request dùng chung một lần khởi động.
4. Core khởi động headless từ hồ sơ đã duyệt.
5. Core chuyển ổ nghe đang giữ qua kênh khởi động riêng, dùng `socket.share()`/`fromshare()` trên Windows.
6. Core kiểm instance ID, danh tính tiến trình gồm thời điểm tạo, phiên bản, contract và readiness.
7. Chỉ chuyển request khi tiến trình sẵn sàng; kiểm schema response và giữ `request_id`.

Có TCP listener chưa đủ để kết luận `ready`.

Engine dùng cùng nền vòng đời, nhưng capability phải qua adapter.

Trạng thái tiến trình:

```text
stopped / starting / ready / busy / dang_dung / failed
```

Các trạng thái này độc lập với:

- Công tắc nghiệp vụ `TAT/THU/VAN_HANH`.
- Trạng thái việc.
- Trạng thái duyệt kết quả.
- Chính sách `tu_kich_hoat_tu_dong/giu_lau_hon/luon_chay`.

#### a. Đóng sau 5 phút rảnh

Mặc định module tự đóng sau **300 giây rảnh**. Lần mở tiếp theo, giao diện hiển thị “đang khởi động”, sau đó tự vào khi sẵn sàng.

Quyết định đóng rảnh và bộ đếm request phải dùng cùng khóa với dispatch. Không đóng khi còn request đồng bộ, việc, lease, download hoặc ánh xạ Mask đang dùng.

Khi dừng:

- Chuyển `dang_dung`.
- Ngừng nhận request/việc mới.
- Chờ drain và bàn giao.
- Chỉ thu hồi accept, trả ổ nghe về Core sau khi drain xong.

Request đến lúc `dang_dung` trả:

```text
503 TIEN_TRINH_DANG_DUNG
Retry-After: 2
```

Request này chưa được chuyển tiếp và có thể thử lại cùng khóa.

Drain tối đa 300 giây. Hết hạn phải báo lỗi dừng, giữ drain và cổng thuộc instance hiện tại để Admin xử lý; không tự cưỡng bức hủy việc.

Theo CD-033, module tự đóng mà có việc chờ thì Core bật lại ngay. Không tự bật module Anh đã tắt.

#### b. Thời hạn và chống vòng khởi động lỗi

Các ngưỡng sau là cấu hình thiết kế, không phải cam kết hiệu năng:

| Tình huống | Xử lý |
|---|---|
| Request đồng bộ | Deadline 30 giây, gồm chờ khởi động và xử lý. |
| Khởi động instance | Cấu hình 1–120 giây; mặc định 120 giây. |
| Hết 30 giây, chưa chuyển request | `503 MODULE_DANG_KHOI_DONG`, `Retry-After: 2`; khởi động có thể tiếp tục. |
| Hết hạn khởi động | `failed`, `503 KHOI_DONG_QUA_HAN`. |
| Đã chuyển request nhưng quá hạn | `504 PHAN_HOI_QUA_HAN`; đối chiếu bằng cùng khóa. |
| Sai danh tính/phiên bản/readiness | Không chuyển tiếp; `503 TIEN_TRINH_KHONG_HOP_LE`. |
| Cổng bị chiếm | `503 CONG_BI_CHIEM`; không dừng ứng dụng lạ. |

Khởi động lỗi liên tiếp phải giãn 2 giây rồi 4 giây. Lần lỗi thứ ba giữ `failed`, trả ngay `503 KHOI_DONG_BI_KHOA` và chờ Admin.

Bộ đếm lỗi và trạng thái khóa phải lưu bền trong registry Core, không mất khi Core restart. Chỉ Admin kiểm tra/khởi động qua `/thao-tac` để mở lại.

Engine cũ chưa nhận socket được dùng chế độ chuyển tiếp: đóng listener giữ cổng rồi khởi động ngay bằng cổng đã cấp. Đây là chế độ có khoảng hở; không tự chọn cổng khác.

Chuyển ổ nghe chỉ áp dụng trên máy Core. Máy phụ chủ động kéo việc, không có cổng nhận do Core cấp/chuyển giao.

#### c. Số đo và quyền áp dụng chính sách

Core ghi mỗi lần khởi động: giờ yêu cầu, giờ sẵn sàng, độ trễ, thời gian xử lý việc, thời gian rảnh trước đóng, RAM đỉnh, CPU và kết quả. Tổng hợp số lần/ngày, p50/p95 khởi động.

Hằng tuần Core tạo đề xuất theo module/engine, kèm kỳ số liệu, số mẫu, cấu hình hiện tại, cấu hình đề xuất và lý do.

**Chỉ Admin bấm áp dụng.** Core không tự đổi sang giữ lâu hơn hoặc luôn chạy. Không module/engine nào mặc định luôn chạy, kể cả OCR và AI.

Áp dụng phải kiểm quyền, phiên bản đề xuất, `row_version` cấu hình và ghi audit trước/sau. Không khởi động lại tiến trình đang bận để áp dụng chính sách.

### 3.11. Thẻ liên tiến trình, mã ủy nhiệm và credential instance

Không coi loopback là bằng chứng danh tính.

Ba thành phần có trách nhiệm khác nhau:

| Thành phần | Vai trò |
|---|---|
| Thẻ ngữ cảnh có chữ ký | Chứng minh ngữ cảnh request do Core chuyển sang đúng module/instance. |
| Mã ủy nhiệm bí mật | Để CSDL xác minh người dùng, module, pháp nhân và phạm vi hành động. |
| Credential SDK của instance | Để Core xác thực instance đang gọi SDK. |

#### a. Thẻ ngữ cảnh

Core loại các header nội bộ do client tự gửi rồi tạo thẻ có chữ ký, TTL tối đa **30 giây**, chứa:

- Bên phát hành, module nhận và instance.
- Người dùng, mã ủy nhiệm bí mật.
- Pháp nhân hoặc phạm vi hệ thống.
- Module nguồn, operation.
- `Idempotency-Key` khi ghi.
- `request_id`, thời điểm phát hành/hết hạn, nonce.
- Hash ràng buộc method, đường dẫn và body.

Khóa ký chỉ Core giữ. Module nhận khóa kiểm chứng qua bootstrap được bảo vệ và phải kiểm chữ ký, đối tượng nhận, thời hạn, nonce cùng ràng buộc request.

Không chuyển cookie người dùng hoặc khóa engine sang module.

#### b. Mã ủy nhiệm

Mã ủy nhiệm không phải SID. Mã ràng buộc login nhận, module, pháp nhân, hạn dùng và phạm vi hành động.

Hàm CSDL `SECURITY DEFINER` băm mã rồi đối chiếu `loi.phien_xac_thuc`, gồm hạn, thu hồi, `session_user`, module, pháp nhân và hành động.

Runtime không được SELECT/DML bảng phiên. GUC danh tính tự khai không tạo quyền; pool không được mang ngữ cảnh request trước sang request sau.

Mã ủy nhiệm theo phiên không dài hơn phiên người dùng; phải thu hồi khi đăng xuất, phiên bị thu hồi hoặc quyền thay đổi.

Việc nền dùng mã riêng gắn `viec_id` và thế hệ lease, được cấp sau kiểm quyền. Không lưu thẻ HTTP 30 giây để dùng cho việc nền về sau.

#### c. Credential instance và login CSDL

Mỗi instance nhận credential SDK riêng cùng instance ID qua stdin hoặc handle kế thừa được bảo vệ, cùng kênh bootstrap nhận ổ nghe.

Core kiểm credential và instance đang sống trên mỗi lời gọi SDK; thu hồi credential khi dừng hoặc crash.

Không đưa credential, mã ủy nhiệm hoặc mật khẩu vào biến môi trường, dòng lệnh, manifest, response công khai hoặc log.

| Tiến trình | Đăng nhập CSDL |
|---|---|
| Core, worker Core nội bộ | `dang_nhap_loi`, chỉ quyền runtime Core được cấp. |
| Module | Login riêng; với `mau_demo` là `dang_nhap_mod_mau_demo`. |
| Adapter kế toán chuyển tiếp | `dang_nhap_ke_toan_cu`; không dùng chung cho module khác. |
| Engine, worker máy phụ | **Không có login CSDL**; trao đổi qua API Core theo việc được giao. |
| Cài đặt/bảo trì | `dang_nhap_cai_dat`; không xử lý request nghiệp vụ. |

Login CSDL module cũng được trao qua kênh bảo vệ. Credential SDK không thay mật khẩu CSDL.

Module/engine chạy dưới tài khoản máy tính có quyền hạn chế, tách khỏi tài khoản Core theo CD-033. Ngoại lệ tài khoản engine phải hỏi Anh, không tự nới quyền.

### 3.12. Danh sách route Core được sử dụng

Các đường dẫn dưới đây đặt sau `/api/v1`, trừ `/healthz` và `/readyz`.

Đây là danh sách API công khai. Giao diện module dùng phiên người dùng; backend module dùng SDK và ủy nhiệm phù hợp. Danh sách này không cấp quyền ngầm cho module hoặc cho phép sao chép cookie sang tiến trình module.

#### a. Phiên, danh tính và pháp nhân

| Method | Route | Mục đích |
|---|---|---|
| GET | `/phien` | Trạng thái phiên, CSRF và tiền phiên. |
| POST | `/phien` | Đăng nhập; cần tiền phiên, CSRF và Origin. |
| DELETE | `/phien` | Thu hồi phiên; trả `204`. |
| GET | `/toi` | Danh tính và quyền hiệu lực. |
| GET | `/phap-nhan` | Pháp nhân người dùng được phép chọn. |

#### b. Tài liệu, tệp và kết quả

| Method | Route | Quyền/phạm vi |
|---|---|---|
| GET | `/tai-lieu` | `tai_lieu.doc`, pháp nhân, quyền hồ sơ. |
| POST | `/tai-lieu` | `tai_lieu.tao`, quyền tệp; trả `201`. |
| GET | `/tai-lieu/{id}` | `tai_lieu.doc`, quyền hồ sơ. |
| PATCH | `/tai-lieu/{id}` | `tai_lieu.sua`, quyền hồ sơ và `row_version`. |
| POST | `/tep` | `tep.tai_len`; gói module cần Admin. |
| GET | `/tep/{id}` | `tep.doc`, đúng biến thể. |
| GET | `/tep/{id}/noi-dung` | `tep.tai_xuong`, quyền nội dung. |
| GET | `/ket-qua/{id}` | `ket_qua.doc`, đúng biến thể. |

#### c. Module, engine, quy trình và việc

| Method | Route | Quyền/phạm vi |
|---|---|---|
| GET | `/module` | Module được dùng tại pháp nhân, theo MTQ. |
| GET | `/module/{ma_module}` | Khai báo module được phép thấy. |
| GET | `/engine` | Capability được phép dùng. |
| GET | `/engine/{ma_engine}` | Năng lực, giới hạn và trạng thái được phép thấy. |
| POST | `/engine/{ma_engine}/viec` | `engine.goi`, quyền module/dữ liệu; trả `202`. |
| GET | `/quy-trinh` | `quy_trinh.doc`, pháp nhân. |
| POST | `/quy-trinh/{id}/lan-chay` | `quy_trinh.chay`, quyền module; trả `202`. |
| GET | `/viec` | Chủ việc còn quyền hoặc quyền giám sát đúng phạm vi. |
| GET | `/viec/{id}` | Snapshot việc; ngoài quyền trả `404`. |
| GET | `/viec/{id}/ket-qua` | Quyền việc và từng kết quả. |
| POST | `/viec/{id}/huy` | Quyền hủy phù hợp; trả `202`. |

Các mã quyền phải được ánh xạ với MTQ hiện có trước triển khai; tên mã trong bảng không tự cấp quyền.

#### d. Quản trị

Các route này dành cho Admin đúng phạm vi, không phải quyền mặc định của module.

| Method | Route | Phạm vi |
|---|---|---|
| GET | `/quan-tri/module` | Admin hệ thống. |
| POST | `/quan-tri/module/{ma_module}/thao-tac` | Kiểm gói, cài/nâng cấp, khởi động/dừng; Admin hệ thống; `202`. |
| GET/PATCH | `/quan-tri/module/{ma_module}/che-do` | Công tắc, người thử, phiên bản; Admin pháp nhân/hệ thống. |
| GET | `/quan-tri/engine` | Admin hệ thống. |
| POST | `/quan-tri/engine` | Đăng ký từ hồ sơ đã duyệt; Admin hệ thống. |
| GET/PUT | `/quan-tri/engine/{ma_engine}/ho-so-chay` | Admin hệ thống; sửa có kiểm phiên bản và audit. |
| POST | `/quan-tri/engine/{ma_engine}/thao-tac` | Admin hệ thống; `202`. |
| GET/PUT | `/quan-tri/cap-quyen/{ma_module}` | Admin đúng phạm vi; không tự vượt quyền. |
| GET | `/quan-tri/so-do` | Admin hệ thống. |
| GET | `/quan-tri/de-xuat-che-do` | Admin hệ thống. |
| POST | `/quan-tri/de-xuat-che-do/{id}/ap-dung` | Admin hệ thống; kiểm CAS cấu hình. |

API quản trị không nhận lệnh shell, executable, URL hoặc khóa bí mật tùy ý.

#### e. Kiểm tra Core

| Method | Route đầy đủ | Ý nghĩa |
|---|---|---|
| GET | `/healthz` | Core còn sống; thông tin tối thiểu. |
| GET | `/readyz` | Core đủ nền phục vụ; thông tin tối thiểu. |

Hai route này công khai nhưng không thay kiểm readiness của từng module/engine.

### 3.13. Lớp chuyển tiếp route cũ

Các nhóm route cũ như `/api/crm/…`, `/api/khung/…`, `/api/cong-tac-module/…`, `/api/that/…` được chuyển theo bảng ánh xạ riêng.

Luồng chuyển tiếp:

```text
Client cu
  → alias tai Core
  → chuan hoa dau vao
  → xac thuc, quyen, schema
  → operation v1
  → module hoac adapter
  → ket qua chuan
  → doi response cu neu an toan
```

Bắt buộc:

- Alias đăng ký theo allowlist method/path/schema; không thay tiền tố tùy ý cho toàn bộ `/api/*`.
- Route trùng tên giữa các dịch vụ cũ phải phân biệt bằng nguồn dịch vụ, method và mẫu path.
- Không dùng HTTP redirect cho lệnh ghi hoặc upload.
- Alias và v1 dùng chung danh tính, pháp nhân, MTQ, công tắc module, CAS, việc nền và biên nhận tại chủ operation.
- Không duy trì hai đường ghi độc lập cho cùng operation.
- Audit nghiệp vụ chỉ ghi một lần; giữ `request_id` xuyên luồng.
- Alias không gọi handler cũ để bỏ qua bảo vệ mới.

Không giữ các hành vi cũ: actor tự khai, tự đăng nhập vai DEMO, tải tệp chỉ nhờ ID/đường dẫn, ghi trong GET, mở thư mục máy chủ hoặc tắt server bằng token chung.

Client cũ không đáp ứng contract an toàn thì phải được nâng cấp hoặc dừng operation tương ứng. Việc lâu vẫn phải nhận `202` và theo dõi việc Core.

Phân loại trong bảng ánh xạ:

| Mã | Cách xử lý |
|---|---|
| `T` | Alias giữ tạm sau khi đủ điều kiện bảo vệ. |
| `T*` | Còn phụ thuộc chủ module hoặc contract; chưa được kích hoạt. |
| `D` | Chỉ DEMO/test, dữ liệu giả. |
| `N` | Protocol nội bộ sau adapter, không mở cho trình duyệt. |
| `S` | Tài sản giao diện/tĩnh, không chuyển thành API. |
| `B` | Bỏ khỏi API công khai. |

Gỡ alias theo từng nhóm sau khi đích v1 hoạt động đủ, client đã chuyển, ID/biên nhận liên tục, kiểm quyền và retry đạt, không còn việc phụ thuộc, đã quan sát sử dụng và có quyết định ngừng.

Ngày ngừng chưa duyệt thì không tự đặt `Sunset`. Nhóm `T*`, mã giữ chỗ `{ma_module_van_hanh}`, chủ nghiệp vụ và contract chưa được duyệt: **chờ Anh**, không tự chốt hoặc tự đăng ký module `that`.

## 4. Khuyến nghị

Các khuyến nghị dưới đây không thay thế yêu cầu bắt buộc:

- Giao diện hiển thị “đang khởi động” khi Core đang mở module; tự thử lại cùng khóa sau `503` trước dispatch, theo `Retry-After`.
- Với client cũ, ưu tiên cập nhật để nhận `202` và polling việc Core; tránh giữ HTTP kéo dài để mô phỏng xử lý đồng bộ.
- Khi tích hợp code đã có, ưu tiên bọc adapter và dùng lại thuật toán/test gốc theo CD-036; phần viết mới tập trung vào contract và khung vận hành Core.
- Với alias đang chuyển đổi, có thể thêm `Deprecation`, liên kết API thay thế và `Sunset` khi ngày ngừng đã được duyệt.

## 5. Module được làm / không được làm

| Module được làm | Module không được làm |
|---|---|
| Đăng ký từng route trong namespace của mình. | Chiếm route Core, namespace module khác hoặc mở wildcard tùy ý. |
| Dùng dịch vụ Core/SDK theo quyền đã cấp. | Gọi thẳng cổng engine từ trình duyệt hoặc dùng host/cổng client gửi để định tuyến. |
| Định nghĩa contract nghiệp vụ và trình duyệt trước kích hoạt. | Tự kích hoạt contract mới hoặc sửa phá phiên bản đang được dùng. |
| Xử lý nghiệp vụ trong khối riêng bằng login hữu hạn. | Đọc/ghi thẳng bảng module khác hoặc tự cấp danh tính bằng GUC. |
| Giữ biên nhận module vĩnh viễn qua hàm V2. | Dọn biên nhận nghiệp vụ hoặc tạo bản hoàn tất thứ hai tại Core. |
| Phát lại kết quả sau kiểm quyền hiện tại. | Dùng biên nhận cũ để vượt quyền đã bị thu hồi. |
| Dùng việc bền vững, đề nghị hủy và trạng thái `interrupted`. | Tự kết luận việc mất heartbeat đã thành công hoặc chạy lại mù. |
| Sinh tệp vào File Store Core qua SDK. | Công bố đường dẫn máy chủ, URL tùy ý hoặc bytes thô để bỏ kiểm quyền Core. |
| Nhận cổng, bootstrap và credential từ Core. | Tự đổi cổng, dừng ứng dụng lạ hoặc coi loopback là xác thực. |
| Nhận đề nghị dừng và drain có kiểm soát. | Tự cưỡng bức hủy việc để đóng rảnh. |
| Dùng engine qua capability đã đăng ký và cấp quyền. | Tự gọi API AI ngoài cổng của phần mềm; tự thêm bộ che riêng. |

Cloud AI chỉ được đi qua Mask file v2 theo quy định của cổng AI. Việc có Local AI không đồng nghĩa tiến trình AI mặc định luôn chạy.

## 6. Ba ví dụ request/response

Tất cả UUID, nội dung, cookie và token dưới đây đều là dữ liệu giả. Các request được gửi tới Core qua HTTPS.

`mau_demo` là module mẫu giả định. Route nghiệp vụ của mẫu chỉ minh họa cách áp dụng chuẩn; phải được khai báo trong gói trước khi dùng.

### 6.1. Tạo tài liệu đồng bộ cho `mau_demo`

Giả định tệp đã được tải lên Core và người dùng có quyền sử dụng tệp.

```http
POST /api/v1/tai-lieu HTTP/1.1
Host: core.example.test
Origin: https://core.example.test
Cookie: __Host-ktt_phien=PHIEN_MINH_HOA
X-CSRF-Token: CSRF_MINH_HOA
X-Phap-Nhan-Id: 10000000-0000-4000-8000-000000000001
Idempotency-Key: mau_demo-tao-tai-lieu-0001
Content-Type: application/json
Accept: application/json

{
  "ten": "Tài liệu minh họa mau_demo",
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
  "ten": "Tài liệu minh họa mau_demo",
  "tep_id": "10000000-0000-4000-8000-000000000002",
  "row_version": "1",
  "tao_luc": "2026-10-30T03:00:00Z"
}
```

Đây là operation Core; Core giữ biên nhận. Gửi lại cùng khóa và nội dung phải đối chiếu kết quả đã có sau kiểm quyền.

### 6.2. `mau_demo` yêu cầu OCR và theo dõi việc lâu

Giả định capability và backend được yêu cầu đã đăng ký, sẵn sàng và được cấp quyền. Không tự đổi backend nếu backend được chọn chưa sẵn sàng.

```http
POST /api/v1/engine/e_ocr/viec HTTP/1.1
Host: core.example.test
Origin: https://core.example.test
Cookie: __Host-ktt_phien=PHIEN_MINH_HOA
X-CSRF-Token: CSRF_MINH_HOA
X-Phap-Nhan-Id: 10000000-0000-4000-8000-000000000001
X-Module-Ma: mau_demo
Idempotency-Key: mau_demo-ocr-tai-lieu-0001
Content-Type: application/json
Accept: application/json

{
  "capability": "ocr.trich_van_ban@1",
  "tai_lieu_id": "10000000-0000-4000-8000-000000000003",
  "tep_id": "10000000-0000-4000-8000-000000000002",
  "bo_xu_ly": "abbyy",
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

Client theo dõi snapshot:

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
  "ma_module": "mau_demo",
  "trang_thai": "succeeded",
  "tien_do": 100,
  "ket_qua_ids": [
    "10000000-0000-4000-8000-000000000005"
  ],
  "loi": null,
  "tao_luc": "2026-10-30T03:01:00Z",
  "cap_nhat_luc": "2026-10-30T03:02:00Z"
}
```

Kết quả vẫn có thể cần duyệt dù việc đã `succeeded`. Nếu mất heartbeat sau restart hoặc hết lease, trạng thái phải là `interrupted`.

### 6.3. Cập nhật ghi chú báo giá CRM với CAS

Ví dụ dùng nguyên contract tối thiểu đã khai báo trong Phụ lục — `openapi-v1.yaml` của đặc tả API: `GET` và `PATCH /api/v1/module/crm/bao-gia/{id}`. PATCH dùng operation `crm_luu_ghi_chu_bao_gia`: body theo `#/components/schemas/LuuGhiChuBaoGia`, response `200` theo `#/components/schemas/GhiChuBaoGia`, lỗi `409` qua `#/components/responses/XungDot` theo schema `Loi`. Cả `row_version` và `expected_revision` đều bắt buộc; dữ liệu dưới đây hoàn toàn giả định, không khai báo thêm route cho `mau_demo`.

```http
PATCH /api/v1/module/crm/bao-gia/10000000-0000-4000-8000-000000000006 HTTP/1.1
Host: core.example.test
Origin: https://core.example.test
Cookie: __Host-ktt_phien=PHIEN_MINH_HOA
X-CSRF-Token: CSRF_MINH_HOA
X-Phap-Nhan-Id: 10000000-0000-4000-8000-000000000001
Idempotency-Key: crm-luu-bao-gia-0001
Content-Type: application/json
Accept: application/json

{
  "row_version": "7",
  "expected_revision": 3,
  "ghi_chu": "Ghi chú minh họa đã được cập nhật."
}
```

Khi cả hai phiên bản khớp:

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

Nếu một trong hai phiên bản không khớp:

```http
HTTP/1.1 409 Conflict
Content-Type: application/json
X-Request-Id: 10000000-0000-4000-8000-000000000015
Cache-Control: no-store

{
  "ma": "XUNG_DOT_PHIEN_BAN",
  "thong_diep": "Dữ liệu đã được người khác cập nhật. Anh tải lại trước khi lưu.",
  "request_id": "10000000-0000-4000-8000-000000000015",
  "thu_lai_duoc": false
}
```

Module ghi thay đổi và biên nhận bất biến trong cùng transaction. Nếu gửi lại request đã thành công với cùng khóa và nội dung, module phát lại kết quả thành công sau kiểm quyền, không ghi thêm và không kiểm CAS như lệnh mới.

## 7. Checklist trước khi nộp gói

### 7.1. Route và contract

- [ ] Mọi route nghiệp vụ nằm dưới `/api/v1/module/{ma_module}/…`, khai báo riêng theo method/path.
- [ ] Không chiếm route Core hoặc namespace module khác.
- [ ] Có OpenAPI, JSON Schema đầu vào/đầu ra, HTTP status và mã lỗi.
- [ ] Có `contract/`, khai trong `module.json`; contract nghiệp vụ đã được duyệt trước kích hoạt.
- [ ] Kiểm schema ở cả Core và module; từ chối trường ngoài schema, không ép kiểu ngầm.
- [ ] Không thay phá contract mà phiên bản đang được dùng đã ghim.

### 7.2. Danh tính và quyền

- [ ] Kiểm phiên, Origin/CSRF cho thao tác ghi; TLS ngoài loopback.
- [ ] Dữ liệu nghiệp vụ dùng `X-Phap-Nhan-Id` trên từng request.
- [ ] Kiểm MTQ, module, hồ sơ, trường và biến thể; không tin actor tự khai.
- [ ] Thử tài nguyên khác pháp nhân, quyền bị thu hồi và tải tệp trái phép.
- [ ] Thẻ liên tiến trình kiểm chữ ký, instance, hạn, nonce và ràng buộc request.
- [ ] Mã ủy nhiệm được CSDL xác minh; thử mã giả, sai phạm vi, hết hạn, thu hồi và sai thế hệ việc.
- [ ] Credential riêng từng instance; không lộ qua môi trường, dòng lệnh, manifest hoặc log.
- [ ] Engine/máy phụ không có login CSDL; module/engine chạy bằng tài khoản máy tính hạn chế.

### 7.3. Ghi, chống trùng và việc lâu

- [ ] Lệnh ghi có `Idempotency-Key` đúng quy định.
- [ ] Đúng chủ biên nhận; biên nhận module bất biến, vĩnh viễn tại `loi_tai_lieu.bien_nhan_thao_tac`.
- [ ] Biên nhận, nghiệp vụ và tạo việc cùng transaction trên cùng kết nối.
- [ ] Thử cùng khóa/cùng nội dung, khác nội dung, đang xử lý, mất mạng, `504` và crash.
- [ ] Phát lại kiểm quyền hiện tại; alias và v1 dùng chung operation/body logic/khóa.
- [ ] `row_version` là chuỗi; kiểm CAS nguyên tử và trả `409` khi xung đột.
- [ ] Việc lâu chỉ trả `202` sau commit; hủy là đề nghị.
- [ ] Restart/mất heartbeat chuyển `interrupted`; không tự thành công hoặc chạy lại mù.
- [ ] Phân trang đúng kích thước, con trỏ, thứ tự ổn định và kiểm quyền.

### 7.4. Tệp và vận hành

- [ ] Upload multipart; giới hạn nhỏ hơn của capability vẫn áp dụng. Mỗi tệp không quá 20 MB (= 20 MiB = 20.971.520 byte theo OpenAPI của đặc tả; Core đếm byte khi nhận luồng).
- [ ] Kiểm MIME thực, hash, kích thước và quyền trước công bố.
- [ ] Download kiểm quyền trước bytes; không nhận đường dẫn/URL tùy ý.
- [ ] Tệp module qua File Store Core; kết quả tải theo metadata → `tep_id`.
- [ ] Nhận cổng từ Core, kiểm readiness và dùng chung một lần khởi động.
- [ ] Đóng rảnh sau 5 phút, dùng khóa dispatch, không đóng khi còn tài nguyên đang dùng.
- [ ] Drain từ chối request mới; quá hạn không cưỡng bức hủy việc.
- [ ] Ba lỗi khởi động khóa bền chờ Admin; không tự đổi cổng hoặc dừng ứng dụng lạ.
- [ ] Không mặc định luôn chạy; đề xuất chế độ chỉ được Admin áp dụng.
- [ ] Nếu có route cũ: đủ ánh xạ, bảo vệ chung, điều kiện ngừng và không kích hoạt mục còn “chờ Anh”.
- [ ] Test dùng dữ liệu giả; báo kết quả đạt/tổng và lỗi mới so với nền test được giao.

## 8. Phụ lục — đặc tả chi tiết và điểm còn chờ

Các tài liệu sau cung cấp schema và ánh xạ chi tiết; không cần đọc phiếu duyệt hoặc biên bản review để hiểu quy tắc trong bản chuẩn này.

Các đường dẫn dưới đây tính từ gốc repo `accounting_assisstance`, để vẫn tra cứu được khi sao chép chuẩn sang `D:\Claude\QUY-TRINH-CHUNG\CHUAN-CORE\`.

| Tài liệu | Nội dung tra cứu |
|---|---|
| `docs\47-core\g1\DAC-TA-API.md` | §2 quy ước; §3 route; §4 dispatcher, thẻ và thời hạn; §5 vận hành; §6 ví dụ; Phụ lục — `openapi-v1.yaml`: OpenAPI 3.1 và schema API. |
| `docs\47-core\g1\ANH-XA-ROUTE.md` | Ánh xạ theo nguồn/method/path; phân loại `T/T*/D/N/S/B`; chuyển tiếp và điều kiện gỡ route cũ. |
| `docs\47-core\g1\DAC-TA-CSDL.md` | Chủ dữ liệu, biên nhận, phiên/mã ủy nhiệm, login, RLS, giao dịch và quyền CSDL. |
| `docs\47-core\g1\ANH-XA-MIGRATION.md` | Chuyển đối tượng cũ sang chủ mới; giữ lịch sử và tránh đọc/ghi chéo module. |

**Các điểm còn chờ, không tự quyết định:**

Cách gọi cụ thể (hàm SDK cho biên nhận V2, File Store, mã ủy nhiệm, credential instance) nằm ở `CHUAN-CORE-SDK-v1.0.md` — **đã ban hành (CD-038, 30/10/2026)**.

- Danh sách nhân sự đăng nhập thật: **chờ Anh**.
- Phiếu SDK bản 2 và điều kiện mở lại lập trình: theo trạng thái phê duyệt, **chờ Anh** khi chưa có quyết định.
- Chủ nghiệp vụ, mã module hoặc contract của các đích `T*` và `{ma_module_van_hanh}` chưa được duyệt: **chờ Anh**; chưa kích hoạt.
- Ngày ngừng alias chưa được duyệt: **chờ Anh**; không tự đặt lịch ngừng.
- Ngoại lệ tài khoản cho engine cũ cần tài khoản riêng: **chờ Anh**; không tự nới quyền.
- Route quản trị sổ contract: bổ sung khi mở G2.

Không dùng nhãn “đề xuất” hoặc “chờ duyệt” lịch sử trong đặc tả để mở lại các lựa chọn đã chốt: API **1A/2A**, CSDL **1A/2A/3A**. Các điểm chưa được duyệt vẫn giữ trạng thái chờ; bản chuẩn này không tự bổ sung quyết định mới.

## 9. Đã xử lý review

Mã C/D theo `RV-CHUAN-OPUS.md`; mã CX dưới đây định danh theo thứ tự các phát hiện trong `RV-CHUAN.md`.

| Mã | Chỗ sửa |
|---|---|
| C1 / CX-3 — giới hạn upload | §3.9a và §7.4: giữ cách gọi 20 MB của phiếu 2A, ghi rõ 20 MiB = 20.971.520 byte theo OpenAPI, đếm byte khi nhận luồng. |
| C2 | Đầu tệp: phân biệt ngày duyệt phiếu với văn bản chuẩn còn chờ Anh xem. |
| C3 | §3.6a: biên nhận Core giữ 24 giờ từ kết quả cuối, giữ tiếp khi cần; hết hạn không cho tạo trùng. |
| C4 | §8: ghi rõ chuẩn SDK chưa ban hành, chờ Anh duyệt phiếu bản 2. |
| C5 | §8: dùng đường dẫn từ gốc repo cho toàn bộ tài liệu tra cứu. |
| D2 | §3.5: bổ sung 503 khi thiếu chính sách bắt buộc; §8: route quản trị sổ contract bổ sung khi mở G2. |
| CX-2 — path parameter | §2, §3.1, §3.6b và §7.1: đồng bộ `{ma_module}` với route metadata và namespace của đặc tả. |
| CX-4 — route/schema ví dụ CAS | §6.3: dùng GET/PATCH báo giá CRM đã khai báo; chỉ rõ operation và ánh xạ schema request/response/lỗi, không tạo contract `mau_demo`. |
| CX-5 — dẫn chiếu OpenAPI (gợi ý) | §8: sửa đích dẫn chiếu thành Phụ lục — `openapi-v1.yaml`. |
