# ANH-XA-ROUTE.md — Phụ lục ánh xạ route cũ sang API v1

**Lát:** G1b-2.  
**Trạng thái:** bản nháp để ghép bộ API trình duyệt; chỉ tài liệu, chưa cho phép triển khai.

**Đề xuất chính:** giữ nghiệp vụ và các cổng kiểm quyền đã có; chuyển API công khai về Core dưới `/api/v1/`. Core chuyển tiếp nghiệp vụ tới tiến trình riêng của từng module, gọi engine qua Adapter và quản lý chung phiên, tệp, kết quả, việc nền. Route cũ chỉ được giữ tạm qua cùng cổng kiểm quyền của API mới.

Căn cứ: `../54-ke-hoach-core-database-api-v1.md:157`, `../54-ke-hoach-core-database-api-v1.md:290`, `../55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:26`, `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:329`, `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:334`.

## 1. Phạm vi và quy ước

### 1.1. Cách hiểu bảng

Danh mục nguồn là **toàn bộ các nhóm route trong KS-C §2, §3**, gồm:

- Route được nối vào shell.
- Route nội bộ của engine #6 do ứng dụng sở hữu.
- Route của server Review cũ, vốn không được nối vào shell.
- Endpoint chỉ thấy ở phía client gọi engine.

Việc đưa vào bảng **không đồng nghĩa** công khai mọi endpoint qua Core. Ranh giới ba nhóm sau được giữ rõ theo `docs/47-core/g0/KS-C.md:119`, `docs/47-core/g0/KS-C.md:132`, `docs/47-core/g0/KS-C.md:152`.

Trong bảng:

- `{a,b}` biểu diễn các route riêng tương ứng; không phải wildcard được phép nhận giá trị tùy ý.
- Các danh sách cũ và mới cùng thứ tự được ánh xạ tương ứng.
- Giữ nguyên HTTP method nếu cột hợp đồng không nêu thay đổi.
- Mọi route mới là **đề xuất**, chưa phải khẳng định đã tồn tại.
- Không có đích `/api/v1/` đối với tài sản tĩnh, endpoint vận hành ngoài HTTP hoặc chức năng bị bỏ khỏi API công khai.

Tiền tố rút gọn cho **route mới**:

| Ký hiệu | Tiền tố đầy đủ |
|---|---|
| `P` | `/api/v1` |
| `C` | `/api/v1/module/crm` |
| `M4` | `/api/v1/module/m4` |
| `M2` | `/api/v1/module/m2` |
| `M5` | `/api/v1/module/m5` |
| `M9` | `/api/v1/module/m9` |
| `T` | `/api/v1/module/m2/tai-hoa-don` |
| `V` | `/api/v1/module/{ma_module_van_hanh}` — tên giữ chỗ, chưa chốt chủ sở hữu |

Tên segment route mới dùng tiếng Việt không dấu với **gạch nối**, khớp thân/OpenAPI; trường JSON/query và path parameter dùng `snake_case`. Giữ mã engine như `e_trich_xuat`, mã module, `boq`, `pdf`, `docx`; không đổi route cũ ở cột nguồn. Căn cứ: `../55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:27`, `docs/47-core/g1/RV-G1B.md:9`.

**Căn cứ vòng 2:** `O` = `docs/47-core/g1/RV-G1B-OPUS.md`; `R` = `docs/47-core/g1/RV-G1B.md`; `D` = `docs/47-core/g1/DAC-TA-CSDL.md`; `A` = `docs/47-core/g1/DAC-TA-API.md`. Dẫn viết gọn là `tệp:dòng`. Các đích Core trong bảng phải có method/path/schema ở A; đích nghiệp vụ module ngoài ví dụ CRM chỉ là thiết kế, cần contract gói riêng trước kích hoạt, không phải wildcard (`R:10`, `docs/47-core/g1/GIAO-G1B.md:36`).

### 1.2. Dẫn chiếu mã nguồn

Đường dẫn mã nguồn tính từ `src/kho_tri_thuc/`.

Các tên `server.py`, `crm_g.py`, `m4.py`, `m4_request.py`, `m2_tai_hoa_don.py`, `khung_khai_bao.py`, `ma_tran_tham_quyen.py`, `module_cong_tac.py` trong bảng thuộc thư mục `giao_dien/`.

Ví dụ: `server.py:1019` là `src/kho_tri_thuc/giao_dien/server.py:1019`. Đường dẫn Review và engine được ghi riêng để phân biệt các server có route trùng tên.

### 1.3. Quyết định chuyển tiếp

| Mã | Ý nghĩa đề xuất |
|---|---|
| **T** | Giữ tạm alias trên Core; chỉ hoạt động sau khi đáp ứng các điều kiện bảo vệ ở §4. |
| **T\*** | Dự kiến giữ tạm, nhưng còn phụ thuộc quyết định về chủ module hoặc hợp đồng; chưa đủ điều kiện mở trên hệ thống mới. |
| **D** | Chỉ giữ trong môi trường DEMO/test với dữ liệu giả; không công khai trong production. |
| **N** | Giữ protocol nội bộ sau Adapter trong thời gian cần tương thích; không mở alias cho trình duyệt. |
| **S** | Giữ dưới cơ chế phục vụ giao diện/tài sản tĩnh của shell; không chuyển thành API. |
| **B** | Bỏ khỏi API công khai khi chuyển đổi; không chuyển tiếp hành vi cũ. |

Các mã này là phương án cho đợt chuyển đổi sau phê duyệt, không phải lệnh thay đổi hệ thống hiện tại.

### 1.4. Hợp đồng dùng chung áp dụng cho các dòng

| Mã | Thay đổi áp dụng |
|---|---|
| **Q** | Core xác thực phiên; suy ra người thao tác từ backend; kiểm pháp nhân, quyền module, MTQ và quyền hồ sơ. Module kiểm lại quyền nghiệp vụ. Không dùng actor hoặc quyền do frontend tự khai. |
| **H** | JSON Schema đầu vào/đầu ra; lỗi `{ma, thong_diep, request_id, thu_lai_duoc, chi_tiet?}`, chi tiết chỉ `[{truong, ma}]`, không giá trị; lỗi module chưa khai trả 502 (`O:16`). HTTP/phân trang theo thân API. |
| **G** | Core giữ biên nhận operation Core cùng transaction, đề xuất 24 giờ. Module qua SDK giữ biên nhận nghiệp vụ vĩnh viễn/bất biến cùng transaction K2; Core chỉ khóa request đang chạy, chuyển key trong token. Fingerprint operation + body logic chuẩn hóa (ID đích/hash tệp), không method/path/key; phát lại kiểm quyền đọc kết quả. Giữ CAS đặc thù (`O:31`, `src/kho_tri_thuc/ha_tang/pg_migrations.py:3385`). |
| **J** | Việc dài `202 + viec_id` sau ghi bền; GET `P/viec/{id}`, kết quả GET `P/viec/{id}/ket-qua` hoặc GET `P/ket-qua/{id}`; hủy POST `P/viec/{id}/huy` là đề nghị. Mất heartbeat sau restart/hết lease → `interrupted`; chỉ xếp lại nếu contract khai an toàn và đã đối chiếu. Theo dõi polling, không SSE công khai (`O:18`, `R:10`). |
| **F** | Upload POST `P/tep`, response `Tep.id` là `tep_id` cho lệnh sau. Module sinh tệp qua SDK vào kho Core. Kết quả đọc GET `P/ket-qua/{id}` lấy `tep_id`, rồi GET `P/tep/{tep_id}/noi-dung`, kiểm lại quyền kết quả/biến thể. Không có route tải bytes kết quả riêng. Tệp hệ thống `phap_nhan_id: null` chỉ Admin, bỏ header; nghiệp vụ bắt buộc header đúng pháp nhân (`O:21`, `R:10`, `R:11`). |

Căn cứ yêu cầu chung: `../55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:29`, `../55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:30`, `../54-ke-hoach-core-database-api-v1.md:134`, `../54-ke-hoach-core-database-api-v1.md:309`.

**Phụ thuộc CSDL vòng 2:** `loi`, `loi_tai_lieu`, `danh_muc`, `mod_*`, `cong_bo_*` theo bản đồ chủ dữ liệu (`D:45`); xác thực qua `loi.phien_xac_thuc` (`D:135`), login tách theo bảng tiến trình (`D:257`). Đây là thiết kế chờ duyệt, không cho client truy cập trực tiếp schema.

## 2. Bảng route cũ → route mới

### 2.1. Shell, tiếp nhận, DEMO và vận hành hệ thống

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/health` | `server.py:1003` | Core | GET `/healthz`, GET `/readyz` | Tách sống/sẵn sàng; không lộ thông tin kết nối nội bộ. Không yêu cầu mọi engine đang chạy để Core sẵn sàng. | T |
| GET `/`, `/index.html`; `/{app.js,style.css,that.css,mark.svg,crm_g.js,m2_tai_hoa_don.js,ma_tran_tham_quyen.js}` | `server.py:1007`, `server.py:1010` | Core Shell | Giữ trang shell và tài sản tĩnh | Bỏ phụ thuộc token chung chèn trong HTML; giao diện dùng phiên Core. | S |
| GET `/api/state` | `server.py:81`, `server.py:1014` | Core và module tiếp nhận/vận hành, chờ chốt phần nghiệp vụ | GET `P/toi`; GET `P/module`; GET `V/trang-thai` cho phần nghiệp vụ | Tách trạng thái người dùng, module và nghiệp vụ; bỏ đường dẫn lưu trữ vật lý, không dùng phiên nghiệp vụ chung mới nhất. Q, H. | T* |
| GET `/api/sample` | `server.py:92`, `server.py:1016` | Bộ dữ liệu DEMO | Không có đích production | Chỉ dữ liệu giả, giữ tham số nguồn trong môi trường thử. | D |
| POST `/api/upload` | `server.py:1143` | Core File Store; module tiếp nhận giữ liên kết nghiệp vụ | POST `P/tep`; nếu cần đăng ký tài liệu: POST `P/tai-lieu` | F, Q, G; tiếp nhận tệp không tự động đồng nghĩa đã nhập nghiệp vụ. | T |
| GET `/api/files/{id}/download` | `server.py:1019` | Core File Store | GET `P/tep/{id}/noi-dung` | F; ánh xạ ID cũ sang ID Core, kiểm quyền hồ sơ/pháp nhân trước khi trả bytes. | T |
| POST `/api/demo/{validate,ingest}` | `server.py:99`, `server.py:1277` | Bộ kiểm chứng DEMO | Không có đích production | Giữ validate/ingest dữ liệu giả trong môi trường thử; không nâng thành đường nhập dữ liệu thật. | D |
| GET `/api/demo/vai` | `server.py:1065` | Bộ kiểm chứng DEMO | Không có đích production; xác thực thật dùng `P/phien`, GET `P/toi` | Bỏ hành vi GET cấp/đổi danh tính DEMO trên production. | D |
| POST `/api/shutdown` | `server.py:1282` | Vận hành Core | Không có đích API nghiệp vụ | Tắt Core qua cơ chế vận hành được quản lý; không giữ lệnh tắt từ token dùng chung. | B |
| OPTIONS mọi đường dẫn | `server.py:973` | Core Dispatcher | OPTIONS tại route được khai báo | Không tạo endpoint nghiệp vụ. Mặc định cùng nguồn; chỉ hỗ trợ preflight nếu chính sách CORS được phê duyệt, không mở wildcard. | T |

### 2.2. Nhóm `/api/that/...`

**Phân ranh nhóm V để ghép duyệt:** registry/tiếp nhận chung thuộc Core; lịch lấy nguồn riêng thuộc M0; định khoản/tri thức/duyệt/báo cáo chưa phân loại giữ adapter `ke_toan_cu`. Đây là đề xuất theo `D:225`, `D:51`, `D:57`, không tự gán mọi phần cho M0 hoặc tạo module `that`. `V` vẫn là tên giữ chỗ **không được đăng ký**; lead phải ghép chủ nghiệp vụ/mã module/contract và trình trong bộ API trước mở T*. Phương án thay thế là tách từng nghiệp vụ thành module riêng khi có bản đồ được duyệt; ưu điểm ranh giới rõ, chi phí thêm gói/contract. Quyết định phân ranh được ghép ở §7 phiếu API, không phát sinh câu hỏi thứ tư (`R:12`, `O:48`; hiện trạng `docs/47-core/g0/KS-C.md:199`, `docs/47-core/g0/KS-C.md:220`).

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/that/job?id=...` | `server.py:1023` | Core Job Worker; module tạo việc giữ nghiệp vụ | GET `P/viec/{id}` | ID cũ ánh xạ việc Core; Q, H, J. | T |
| GET `/api/that/{knowledge,knowledge-cards}` | `server.py:1025`, `server.py:1042` | Module tri thức, mã chờ chốt | GET `V/{tri-thuc,the-tri-thuc}` | Q, H; phân trang và lọc theo phạm vi được phép. | T* |
| GET `/api/that/catalog` | `server.py:1028` | Module sử dụng danh mục; Core cung cấp dữ liệu chung | GET `V/danh-muc` | Giữ ý nghĩa thời điểm/ngày chốt; lấy dữ liệu chung qua dịch vụ được cấp quyền, theo phiếu CSDL. | T* |
| GET `/api/that/source-settings` | `server.py:1030` | Module quản lý nguồn, mã chờ chốt | GET `V/cau-hinh-nguon` | Q, H; chỉ trả cấu hình an toàn theo quyền, không trả bí mật. | T* |
| GET `/api/that/{overview,runs,history,cfo-rules,invoice-months,report,proposals,quick}` | `server.py:1032`, `server.py:1034`, `server.py:1036`, `server.py:1038`, `server.py:1040`, `server.py:1044`, `server.py:1046`, `server.py:1055` | Các module nghiệp vụ tương ứng, chờ chốt | GET `V/{tong-quan,lan-chay,lich-su,quy-tac-cfo,thang-hoa-don,bao-cao,de-xuat,dinh-khoan-nhanh}` | Q, H; giữ bộ lọc nghiệp vụ qua schema tường minh; không dùng mặc định phiên chung. | T* |
| GET `/api/that/quick/{run}/download`, `/api/that/outside-catalog/download`, `/api/that/shadow/{id}/{direction}/download` | `server.py:1048`, `server.py:1057`, `server.py:1138` | Core File Store và module tạo kết quả | GET `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` | F; ánh xạ đầy đủ run/tệp/hướng/biến thể sang kết quả được cấp quyền; không biến chuỗi tên tệp thành quyền tải. | T |
| POST `/api/that/source` | `server.py:1150` | Module quản lý nguồn, mã chờ chốt | POST `P/tep`; POST `V/nguon` | F, Q, G; tách nhận bytes và đăng ký nguồn. | T* |
| POST `/api/that/knowledge/import` | `server.py:1204` | Module tri thức, mã chờ chốt | POST `P/tep`; POST `V/tri-thuc/nhap` | F, Q, G; actor lấy từ phiên, không lấy metadata client; J nếu nhập dài. | T* |
| POST `/api/that/quick/{upload,invoice-month,repropose}` | `server.py:1156`, `server.py:1162`, `server.py:1166` | Module định khoản, mã chờ chốt | POST `V/dinh-khoan-nhanh/{nhan-tep,hoa-don-thang,de-xuat-lai}` | Upload dùng `tep_id`; cả ba lệnh áp dụng J thay 201/202 không thống nhất và hàng đợi RAM. | T* |
| POST `/api/that/{reload,ingest,session/run,shadow/export}` | `server.py:1185`, `server.py:1208`, `server.py:1214`, `server.py:1220` | Module nghiệp vụ tương ứng, chờ chốt | POST `V/{nap-lai-nguon,nap-nguon,phien-nghiep-vu/chay,doi-chieu/xuat}` | Q, G, J; xác định rõ phiên nghiệp vụ thuộc pháp nhân/người có quyền. | T* |
| POST `/api/that/quick/{decide,ai-note,ai-context,score,export}` | `server.py:1170`, `server.py:1173`, `server.py:1176`, `server.py:1179`, `server.py:1182` | Module định khoản, mã chờ chốt | POST `V/dinh-khoan-nhanh/{quyet-dinh,ghi-chu-ai,ngu-canh-ai,cham-diem,xuat}` | Q, G; giữ phân biệt ghi chú, tính toán và quyết định duyệt. Nhánh xử lý dài dùng J; AI qua cổng chung; xuất trả tham chiếu kết quả. | T* |
| POST `/api/that/{learning-settings,cfo-rules/toggle,cash-mapping,source-settings,knowledge/decide,proposals/decide}` | `server.py:1188`, `server.py:1190`, `server.py:1193`, `server.py:1201`, `server.py:1211`, `server.py:1217` | Module nghiệp vụ tương ứng, chờ chốt | POST `V/{cau-hinh-hoc,quy-tac-cfo/bat-tat,anh-xa-tien,cau-hinh-nguon,tri-thuc/quyet-dinh,de-xuat/quyet-dinh}` | Q, G; quyền cấu hình khác quyền duyệt; thời điểm audit do server ghi, ngày hiệu lực nghiệp vụ vẫn kiểm theo schema. | T* |
| POST `/api/that/open` | `server.py:1196` | Module tạo kết quả và Core File Store | Không giữ hành vi mở thư mục; dùng GET `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` để tải kết quả | Trình duyệt tải kết quả được phép; không ra lệnh mở thư mục trên máy chủ. | B |

### 2.3. Bridge nghiệm thu cũ

Bridge hiện tại chỉ phục vụ DEMO và có actor cố định; GET danh sách gọi đồng bộ ghi dữ liệu. Căn cứ: `server.py:123`, `server.py:129`, `server.py:137`.

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/nghiem-thu` | `server.py:1128`, `server.py:137` | M4 | GET `M4/nghiem-thu`; thao tác đồng bộ tách thành POST `M4/nghiem-thu/dong-bo` | GET chỉ đọc nghiệp vụ. Lệnh đồng bộ có Q, G và J nếu dài; bỏ actor cố định. | D; không giữ tác dụng ghi của GET |
| GET `/api/nghiem-thu/sample` | `server.py:1131`, `server.py:143` | Bộ kiểm chứng M4 | Không có đích production | Chỉ mẫu giả. | D |
| GET `/api/nghiem-thu/file-soat/{id}` | `server.py:1134`, `server.py:187` | M4 và Core File Store | GET `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` | F, Q; ánh xạ hồ sơ và kết quả từ bridge. | D |
| POST `/api/nghiem-thu/{nhan,mau,xac-nhan,quyet-dinh,xuat}` | `server.py:1262`, `server.py:1267` | M4 | Với nghiệp vụ được chuyển: POST `M4/nghiem-thu/{nhan,xac-nhan,quyet-dinh,xuat}`; `mau` không có đích production | Q, G, F; J cho xử lý dài. Chuyển logic có giá trị, không coi bridge DEMO là API production đã có. | D |

### 2.4. CRM và khung module

Tiền tố cũ `c = /api/crm`.

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `c` | `server.py:1060` | CRM | GET `C/trang-thai` | Q, H; GET không tự tạo danh tính DEMO. | T |
| GET `c/file-soat/{id}` | `server.py:1074` | CRM và Core File Store | GET `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` | F; giữ kiểm quyền CRM hiện có trước khi trả nội dung. | T |
| POST `c/danh-tinh` | `server.py:340` | Bộ kiểm chứng CRM | Không có đích production; phiên thật dùng `P/phien`, GET `P/toi` | Bỏ đổi vai bằng tên đăng nhập tự khai. | D |
| POST `c/{mau,m1-sao-ke}` | `server.py:345`, `server.py:369`, `server.py:379` | Bộ kiểm chứng CRM/M1 | Không có đích production | Giữ fixture tại môi trường thử; không thay bằng đường nhập sao kê thật trong lát này. | D |
| POST `c/{bo-sung,trich-lai/doi-chieu,trich-lai/xu-ly,xac-nhan-tham-so,kiem,duyet,duyet-v4,tu-choi,mapping,lien-ket,go-lien-ket,file-soat}` | `server.py:336` | CRM | POST `C/{bo-sung,trich-lai/doi-chieu,trich-lai/xu-ly,xac-nhan-tham-so,kiem,duyet,duyet-v4,tu-choi,anh-xa,lien-ket,go-lien-ket,file-soat}` | Q, H, G; giữ quy tắc duyệt/liên kết. `trich_lai/doi_chieu` vẫn là thao tác tính/đọc; tạo file soát trả kết quả Core, J nếu dài. | T |
| POST `c/nhan`; POST `c/trich6` | `server.py:1232`, `server.py:1223`, `server.py:494`, `server.py:514` | CRM; engine trích xuất là bên thực thi | POST `C/nhan`; POST `C/trich-tham-so` | F, Q, G; trích xuất dùng J và Adapter `e_trich_xuat`, không giữ HTTP chờ toàn bộ xử lý. | T |
| GET `c/hop-dong` | `crm_g.py:480` | CRM | GET `C/hop-dong` | Q, H; giữ bộ lọc và phân trang S1, chuẩn hóa envelope. | T |
| GET `c/mau`, `c/mau/{id}`, `c/mau/so-sanh`, `c/bo-chuan` | `crm_g.py:493`, `crm_g.py:512`, `crm_g.py:500`, `crm_g.py:600` | CRM | GET `C/mau`, `C/mau/{id}`, `C/mau/so-sanh`, `C/bo-chuan` | Q, H; giữ phiên bản mẫu và ngữ nghĩa thời điểm. Đây là mẫu hợp đồng nghiệp vụ, khác POST `c/mau` nhận fixture. | T |
| GET `c/mau/tep/{id}` | `crm_g.py:505` | CRM và Core File Store | GET `P/tep/{id}/noi-dung` | F; không làm yếu kiểm quyền trước khi tra tệp hiện có. | T |
| POST `c/mau/tai`; `c/mau/{anh-xa,gui-kiem,kiem,tra-lai,duyet,tu-choi,xem-thu}`; `c/bo-chuan/{lap,gui-duyet,duyet}` | `crm_g.py:608`, `crm_g.py:444`, `crm_g.py:60` | CRM | POST `C/mau/tai`; `C/mau/{anh-xa,gui-kiem,kiem,tra-lai,duyet,tu-choi,xem-thu}`; `C/bo-chuan/{lap,gui-duyet,duyet}` | F cho tải mẫu; Q, G; giữ token graph/revision của quy trình mẫu; `xem_thu` không trở thành duyệt. | T |
| GET `c/bao-gia`, `c/bao-gia/{id}`, `c/bao-gia/{mac-dinh,moc-chuan,ty-gia-mac-dinh}`, `c/soan/{id}` | `crm_g.py:518`, `crm_g.py:536`, `crm_g.py:546` | CRM | GET `C/bao-gia`, `C/bao-gia/{id}`, `C/bao-gia/{mac-dinh,moc-chuan,ty-gia-mac-dinh}`, `C/soan/{id}` | Q, H; giữ quy tắc thuế, tỷ giá, mốc và căn cứ nghiệp vụ đã chốt. | T |
| POST `c/bao-gia/{luu,huy,chuyen,xem-truoc,ty-gia-mac-dinh,in}`, `c/soan/{luu,xuat}` | `crm_g.py:388`, `crm_g.py:406`, `crm_g.py:74` | CRM | POST `C/bao-gia/{luu,huy,chuyen,xem-truoc,ty-gia-mac-dinh,in}`, `C/soan/{luu,xuat}` | Q, G; giữ CAS đặc thù; `in/xuat` dùng J và trả kết quả Core; xem trước không tự ghi quyết định. | T |
| GET `c/giao-ket/tep/{id}/{docx,pdf}`, `c/giao-ket/ban-ky/{id}/tep` | `crm_g.py:551`, `crm_g.py:565` | CRM và Core File Store | GET `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` hoặc `P/tep/{id}/noi-dung` theo loại đã đăng ký | F; định dạng và bản ký là biến thể được kiểm quyền, không suy ra từ tên tệp. | T |
| GET `c/giao-ket/ky/{id}`; POST `c/giao-ket/ky-ket` | `crm_g.py:559`, `crm_g.py:346`, `crm_g.py:631` | CRM | GET `C/giao-ket/ky/{id}`; POST `C/giao-ket/ky-ket` | Q, G; lệnh ký kết dùng J; giữ điều kiện và lịch sử ký kết. | T |
| GET `c/giao-ket/kiem`, `c/giao-ket/kiem/{id}` | `crm_g.py:574`, `crm_g.py:579` | CRM | GET `C/giao-ket/kiem`, `C/giao-ket/kiem/{id}` | Q, H; giữ audit nghiệp vụ. | T |
| GET `c/giao-ket/kiem/{id}/tep/{ban-ky,g3}` | `crm_g.py:585` | CRM và Core File Store | GET `P/tep/{id}/noi-dung` hoặc `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` | F; ánh xạ rõ hồ sơ, bản ký và bản G3. | T |
| POST `c/giao-ket/kiem/{luu,check,xu-ly-lech,bo-sung,hieu-luc,tra-lai,tim-junsky}` | `crm_g.py:317`, `crm_g.py:659`, `crm_g.py:103` | CRM | POST `C/giao-ket/kiem/{luu,kiem-tra,xu-ly-lech,bo-sung,hieu-luc,tra-lai,tim-junsky}` | Q, G; giữ tra cứu khác với nhập/duyệt; lệnh có IO dài dùng J. | T |
| GET `c/giao-ket/doi-chieu/{id}`; POST `c/giao-ket/doi-chieu/{chay,doi-soat,xac-nhan-tay}` | `crm_g.py:594`, `crm_g.py:308`, `crm_g.py:636`, `crm_g.py:646` | CRM | GET `C/giao-ket/doi-chieu/{id}`; POST `C/giao-ket/doi-chieu/{chay,doi-soat,xac-nhan-tay}` | Giữ hàng việc G5 bền và CAS; `chay/doi_soat` đổi ACK 200 thành J; xác nhận tay giữ điều kiện riêng. | T |
| GET `c/du-an-ban`, `c/du-an-ban/anh-chup`, `c/du-an-ban/{id}`, `c/du-an-ban/{id}/lich-su`, `c/du-an-ban/moc`, `c/du-an-ban/moc/{id}/lich-su` | `crm_g.py:786` | CRM | GET `C/du-an-ban`, `C/du-an-ban/anh-chup`, `C/du-an-ban/{id}`, `C/du-an-ban/{id}/lich-su`, `C/du-an-ban/moc`, `C/du-an-ban/moc/{id}/lich-su` | Q, H; giữ ảnh chụp, lịch sử và bộ lọc mốc. | T |
| POST `c/du-an-ban/{bat-ban,cap-nhat,phi,lo,moc,ngung-ban,mo-ban-lai,tien-do}` | `crm_g.py:757`, `crm_g.py:706` | CRM | POST `C/du-an-ban/{bat-ban,cap-nhat,phi,lo,moc,ngung-ban,mo-ban-lai,tien-do}` | Q, G; giữ căn cứ/version nghiệp vụ từng lệnh. | T |
| GET `/api/khung/module/crm` | `khung_khai_bao.py:170`, `khung_khai_bao.py:103` | Core Shell và CRM | GET `P/module/crm` | Metadata khung và khả năng truy cập lấy từ backend; module cung cấp đếm/drill-down theo quyền. | T |
| GET `c/{bao-gia,mau}?trang_thai=...` | `crm_g.py:475`, `khung_khai_bao.py:183` | CRM | GET `C/{bao-gia,mau}?trang_thai=...` | Hợp nhất contract danh sách có bộ lọc; giữ cách kiểm giá trị rỗng/lặp và phạm vi quyền. | T |

### 2.5. MTQ và công tắc module

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/tham-quyen/{ma-tran,nhat-ky}` | `ma_tran_tham_quyen.py:16`, `ma_tran_tham_quyen.py:42` | Core Identity/Access | Không công bố alias v1 trong bộ contract này | Không dùng `cap-quyen/{ma_module}` thay vòng đời ma trận/nhật ký MTQ. Giữ nhu cầu trong danh mục chuyển đổi, chặn kích hoạt alias cho tới contract MTQ riêng được duyệt (`R:10`, `D:157`). | T* |
| GET `/api/tham-quyen/cua-toi` | `ma_tran_tham_quyen.py:16`, `ma_tran_tham_quyen.py:42` | Core Identity/Access | GET `P/toi` | Trả danh tính/quyền hiệu lực của người gọi theo schema `NguoiDung`; client cần chi tiết ma trận ngoài schema phải chờ contract MTQ, không thêm `/toi/tham-quyen` giả định (`R:10`). | T |
| POST `/api/tham-quyen/{luu-nhap,cong-bo,kich-hoat,phong,gan-vai,pham-vi,admin}` | `ma_tran_tham_quyen.py:16`, `ma_tran_tham_quyen.py:42` | Core Identity/Access | Không công bố alias v1 trong bộ contract này | Không thay công bố/kích hoạt/phòng/gán vai/Admin bằng PUT quyền module vì khác nghiệp vụ. Chặn alias cho tới contract MTQ riêng, giữ nguyên nhu cầu và revision trong kế hoạch chuyển client (`R:10`, `D:157`). | T* |
| GET `/api/cong-tac-module/{trang-thai,nguoi-thu}` | `module_cong_tac.py:12`, `module_cong_tac.py:73` | Core Module Manager | GET `P/quan-tri/module/{ma_module}/che-do` | Q, H; response `CheDoModule` gồm công tắc, `nguoi_thu_ids`, `row_version`; mã module phải đối chiếu với request cũ (`R:10`). | T |
| POST `/api/cong-tac-module/{che-do,nguoi-thu/cap,nguoi-thu/thu-hoi}` | `module_cong_tac.py:12`, `module_cong_tac.py:65`, `module_cong_tac.py:73` | Core Module Manager | PATCH `P/quan-tri/module/{ma_module}/che-do` | Q, G; gửi đủ `che_do`, tập `nguoi_thu_ids` mong muốn và `row_version` đã đọc. Alias cấp/thu hồi tính tập từ snapshot client; thiếu phiên bản phải đọc lại, không tự dùng mới nhất. 409 khi cạnh tranh; công tắc khác vòng đời tiến trình (`R:10`). | T |

### 2.6. M4 và Request nháp

Tiền tố cũ `x = /api/m4`.

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `x`; `x/{hop-dong,dot}/{id}`; `x/mau`, `x/mau/{ma}` | `m4.py:502`, `m4.py:507`, `m4.py:520` | M4 | GET `M4/trang-thai`; `M4/{hop-dong,dot}/{id}`; `M4/mau`, `M4/mau/{ma}` | Q, H; root không tự cấp phiên DEMO. Mẫu trả metadata; nội dung tệp theo F. | T |
| GET `x/tep/{id}` | `m4.py:507` | M4 và Core File Store | GET `P/tep/{id}/noi-dung` | F; giữ kiểm quyền dự án/hồ sơ M4. | T |
| GET `x/{master-hop-dong,master-doi-tac}` | `m4.py:457` | M4 tiêu thụ danh mục chung | GET `M4/danh-muc/{hop-dong,doi-tac}` | Q, H; lấy dữ liệu qua dịch vụ/contract được cấp, theo phiếu CSDL. | T |
| GET `x/{review,chung-tu}`, `x/{review,chung-tu}/{id}` | `m4.py:465`, `m4.py:481` | M4 | GET `M4/{soat-xet,chung-tu}`, `M4/{soat-xet,chung-tu}/{id}` | Q, H; danh sách/chi tiết nghiệp vụ khác trạng thái việc Core. | T |
| GET `x/{review,chung-tu}/{id}/tep/{tep_id}` | `m4.py:465`, `m4.py:481` | M4 và Core File Store | GET `P/tep/{id}/noi-dung` hoặc `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` | F; kiểm quan hệ tệp với hồ sơ trước tải. | T |
| GET `x/duyet`, `x/ke-toan`, `x/ke-toan/{id}` | `m4.py:425`, `m4.py:442` | M4 | GET `M4/duyet`, `M4/ke-toan`, `M4/ke-toan/{id}` | Q, H; giữ phạm vi người duyệt/kế toán. | T |
| GET `x/duyet/{id}/pdf/{pdf_id}`, `x/ke-toan/{id}/phong-bi/{id}/pdf` | `m4.py:425`, `m4.py:442` | M4 và Core File Store | GET `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` | F; alias phải giữ đủ các ID hồ sơ/phong bì/tệp, không nhập nhằng hai `{id}` cũ. | T |
| GET `x/doi-chieu/{dot,lich-su,con-thieu}/{id}` | `m4.py:391` | M4 | GET `M4/doi-chieu/{dot,lich-su,con-thieu}/{id}` | Q, H; giữ căn cứ và lịch sử đối chiếu. | T |
| POST `x/tep`, `x/duyet/pdf` | `m4.py:547`, `m4.py:564` | Core File Store và M4 | POST `P/tep`; POST `M4/duyet/pdf` với `tep_id` | F, Q, G; xử lý PDF dài dùng J; nhận bytes không tự duyệt hồ sơ. | T |
| POST `x/danh-tinh` | `m4.py:596` | Bộ kiểm chứng M4 | Không có đích production | Dùng phiên Core; không đổi vai bằng payload DEMO. | D |
| POST `x/hop-dong/{tao,nhan-master,gan-doi-tac,gan-tep,trich}`; `x/tham-so/{sua,xac-nhan}`; `x/phu-luc/{khai,them,huy}`; `x/boq/{xem,nhap}`; `x/dot/{tao,sua,gan-tep,nop}` | `m4.py:205`, `m4.py:20` | M4 | POST `M4/hop-dong/{tao,nhan-danh-muc,gan-doi-tac,gan-tep,trich}`; `M4/tham-so/{sua,xac-nhan}`; `M4/phu-luc/{khai,them,huy}`; `M4/boq/{xem,nhap}`; `M4/dot/{tao,sua,gan-tep,nop}` | Q, G, F; `hop_dong/trich` dùng J. `boq/xem` giữ tính xem trước. | T |
| POST `x/review/{chay,chay-lai,ghep}`; `x/chung-tu/{chay,chay-lai,sua,ghep}`; `x/duyet/{ket-luan,chap-thuan,phien-ban,phien-ban/nop}` | `m4.py:245`, `m4.py:316`, `m4.py:588` | M4 | POST `M4/soat-xet/{chay,chay-lai,ghep}`; `M4/chung-tu/{chay,chay-lai,sua,ghep}`; `M4/duyet/{ket-luan,chap-thuan,phien-ban,phien-ban/nop}` | Q, G; chạy/chạy lại và xử lý dài dùng J; sửa/ghép/duyệt giữ CAS, không tự duyệt từ kết quả engine. | T |
| POST `x/ke-toan/{luu,xac-nhan}`, `x/doi-chieu/{xem,luu,xac-nhan}` | `m4.py:532`, `m4.py:574` | M4 | POST `M4/ke-toan/{luu,xac-nhan}`, `M4/doi-chieu/{xem,luu,xac-nhan}` | Q, G; giữ token căn cứ và phân biệt xem/ghi/xác nhận. | T |
| GET `/api/m4-request`; POST `/api/m4-request/{tao,doi-soat}` | `m4_request.py:206`, `m4_request.py:237` | M4 | GET `M4/yeu-cau-nhap`; POST `M4/yeu-cau-nhap/{tao,doi-soat}` | Q, G, J cho IO dài; giữ kiểm lại phiên/quyền sau IO và trạng thái chưa cấu hình/tắt. | T |
| GET `/m4.js`, `/m4.css`, `/m4/{review.js,chung-tu.js,m4_duyet_pdf.js,m4_ke_toan.js,m4_request_nhap.js}`, `/m4/fonts/{ten}` | `m4.py:403`, `m4.py:497` | Core Shell và gói giao diện M4 | Tài sản giao diện do Core phục vụ | Giữ allowlist; không biến đường dẫn asset thành API nghiệp vụ. | S |

### 2.7. M2, M5/L11 và M9

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/m2`; `/api/m2/{hoa-don,nguon}/{id}` | `server.py:1115`, `server.py:771` | M2 | GET `M2/trang-thai`; `M2/{hoa-don,nguon}/{id}` | Q, H; bỏ cấp danh tính DEMO ngầm khi đọc root. | T |
| GET `/api/m2/nguon/{id}/raw/{vai_tro}` | `server.py:839` | M2 và Core File Store | GET `P/tep/{id}/noi-dung` hoặc `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` | F; giữ kiểm quyền nguồn và vai trò biến thể; ID được ánh xạ. | T |
| POST `/api/m2/danh-tinh` | `server.py:789` | Bộ kiểm chứng M2 | Không có đích production | Phiên thật do Core quản lý. | D |
| POST `/api/m2/{nhan,mapping,mapping-line,nguon/kiem-lai,route}` | `server.py:784`, `server.py:817`, `server.py:821`, `server.py:827`, `server.py:831` | M2 | POST `M2/{nhan,anh-xa,anh-xa-dong,nguon/kiem-lai,dinh-tuyen}` | Q, G, F; giữ `expected_graph`, căn cứ dòng, tuyến và revision. Nhánh nhận fixture chỉ DEMO. | T |
| POST `/api/m2/lien-ket/{...}` | `server.py:835`, `server.py:1292` | M2 | Chưa đăng ký route v1 tương ứng | KS-C ghi chưa phát hành/501; không suy ra tập operation hoặc công bố chức năng đã có. | B; chờ đặc tả nghiệp vụ |
| GET `/api/m5`; `/api/m5/{phieu,nguon}/{id}`; `/api/m5/{kiem-ke,ton-nguon}` | `server.py:1089`, `server.py:598` | M5 | GET `M5/trang-thai`; `M5/{phieu,nguon}/{id}`; `M5/{kiem-ke,ton-nguon}` | Q, H; giữ phân trang và quyền dữ liệu nguồn. | T |
| GET `/api/m5/nguon/{id}/raw/{vai_tro}`, `/api/m5/file-soat/{id}` | `server.py:723`, `server.py:598` | M5 và Core File Store | GET `P/tep/{id}/noi-dung`, `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` tương ứng | F; giữ kiểm quyền nguồn/hồ sơ và token căn cứ nếu áp dụng. | T |
| POST `/api/m5/danh-tinh`; `/api/m5/l11/danh-tinh` | `server.py:620`, `server.py:664` | Bộ kiểm chứng M5/L11 | Không có đích production | Không biến bộ chọn vai DEMO thành đăng nhập thật. | D |
| POST `/api/m5/{nhan,mapping,nguon/kiem-lai,xuat-file-soat}` | `server.py:615` | M5 | POST `M5/{nhan,anh-xa,nguon/kiem-lai,xuat-file-soat}` | Q, G, F; giữ bộ con trỏ và token basis của xuất file soát; nhận fixture chỉ DEMO; J nếu xuất dài. | T |
| GET `/api/m5/l11`, `/api/m5/l11/proof`; POST `/api/m5/l11/{proof/nhan,proof/xac-nhan,proof/huy,ma-hoa,file-soat}` | `server.py:1094`, `server.py:664`, `server.py:718` | M5/L11 | GET `M5/l11`, `M5/l11/bang-chung`; POST `M5/l11/{bang-chung/nhan,bang-chung/xac-nhan,bang-chung/huy,ma-hoa,file-soat}` | Q, G, F; giữ điều kiện BOTH, phạm vi hai phía và quyền hồ sơ L11; không thay bằng kiểm một module. | T |
| POST `/api/m5/lien-ket/{preview,xac-nhan,huy}` | `server.py:657`, `k2/kho_so_luong.py:906` | M5/L11 | POST `M5/lien-ket/{xem-truoc,xac-nhan,huy}` | Giữ preview không ghi, token preview/căn cứ và biên nhận bền; Q, G. | T |
| GET `/api/m9`, `/api/m9/file-soat/{id}` | `server.py:1079`, `server.py:486` | M9 và Core File Store | GET `M9/trang-thai`; GET `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` | Q, H, F; root không tự cấp danh tính DEMO. | T |
| POST `/api/m9/danh-tinh` | `server.py:443` | Bộ kiểm chứng M9 | Không có đích production | Phiên do Core quản lý. | D |
| POST `/api/m9/{mau,m1-sao-ke}` | `server.py:448`, `server.py:458`, `server.py:469` | Bộ kiểm chứng M9/M1 | Không có đích production cho nhánh nhận mẫu | Giữ luồng kiểm chứng riêng; không tự thiết kế lại nhập sao kê thật. | D |
| POST `/api/m9/{anh-xa,anh-xa/anh-huong,anh-xa/dong,lap,pham-vi,kiem,duyet,duyet-v4,tu-choi,goi-y,xem-truoc,xac-nhan,go,file-soat}` | `server.py:438` | M9 | POST `M9/{anh-xa,anh-xa/anh-huong,anh-xa/dong,lap,pham-vi,kiem,duyet,duyet-v4,tu-choi,goi-y,xem-truoc,xac-nhan,go,file-soat}` | Q, G; giữ phân biệt gợi ý/xem trước với xác nhận; file soát trả tham chiếu kết quả, J nếu dài. | T |

### 2.8. Bộ tải hóa đơn M2

Tiền tố cũ `t = /api/m2/tai-hoa-don`. M2 giữ nghiệp vụ; quản lý tiến trình bộ tải thuộc Core/Engine Manager.

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `t`, `t/trang-thai` | `m2_tai_hoa_don.py:1048` | M2 | GET `T/trang-thai` | Q, H; tách trạng thái nghiệp vụ khỏi trạng thái tiến trình engine. | T |
| GET `t/hang-doi` | `m2_tai_hoa_don.py:1048`, `m2_tai_hoa_don.py:213` | Core Job Worker và M2 | GET `P/viec?ma_module=m2`, tùy chọn `trang_thai` theo contract | Hàng đợi dùng việc bền; người dùng chỉ xem phạm vi được cấp. Không suy rằng mọi binding hiện có đều ở RAM. | T |
| GET `t/su-kien` | `m2_tai_hoa_don.py:1048` | Core Job Worker và M2 | GET `P/viec?ma_module=m2`; GET `P/viec/{id}` | Đổi SSE thành polling snapshot theo `Retry-After`; client cũ cần nâng cấp, không giả stream tương thích. Mỗi lần poll kiểm quyền, chỉ xem việc của mình còn quyền hoặc MTQ `viec.giam_sat` đúng pháp nhân/module (`R:10`, `O:18`). | T |
| GET `t/{manifest,hoa-don}` | `m2_tai_hoa_don.py:1048` | M2 | GET `T/{manifest,hoa-don}` | Q, H; giữ binding run/manifest và quyền nguồn. | T |
| POST `t/{khoi-dong,khoi-dong-lai}` | `m2_tai_hoa_don.py:1069`, `m2_tai_hoa_don.py:874` | Core Engine Manager | POST `P/quan-tri/engine/e_hoa_don/thao-tac` | Body `ThaoTacEngine` với `khoi_dong`; restart là `dung` → chờ việc kết thúc/drain → đọc lại phiên bản → `khoi_dong`, mỗi lệnh key riêng. Chỉ Admin; Core tự kích hoạt khi người dùng làm nghiệp vụ (`R:10`, `O:20`). | T |
| POST `t/{bat-dau,tai-tat-ca}` | `m2_tai_hoa_don.py:1069`, `m2_tai_hoa_don.py:1076` | M2; `e_hoa_don` thực thi | POST `T/{bat-dau,tai-tat-ca}` | Q, G, J; giữ mapping nguồn/pháp nhân và bước người dùng đăng nhập/CAPTCHA. | T |
| POST `t/huy-hang-doi` | `m2_tai_hoa_don.py:1069` | Core Job Worker và M2 | POST `T/hang-doi/huy`; mỗi việc được yêu cầu hủy theo contract `P/viec/{id}/huy` | Chụp rõ tập việc thuộc phạm vi yêu cầu; trả trạng thái từng việc, không báo đã hủy ngay toàn bộ. | T |
| POST `t/{nhan,doi-soat}` | `m2_tai_hoa_don.py:1069` | M2 | POST `T/{nhan,doi-soat}` | Q, G, J nếu dài; giữ kiểm lại quyền quanh IO và biên nhận nhập. | T |
| POST `t/mo-thu-muc` | `m2_tai_hoa_don.py:1069` | M2 và Core File Store | Không giữ hành vi mở thư mục; dùng metadata/tải kết quả qua `P/ket-qua/{id}` | Không mở thư mục máy chủ từ trình duyệt người dùng. | B |

### 2.9. Engine #6 do ứng dụng sở hữu

Đây là **protocol dịch vụ nội bộ**, không phải phiên người dùng. Cổng và token hiện có không thay kiểm quyền của consumer; nguồn handler nghiệp vụ kế thừa còn nằm ngoài phạm vi mã khảo sát. Căn cứ: `docs/47-core/g0/KS-C.md:125`, `docs/47-core/g0/KS-C.md:128`.

| Route cũ | Tệp:dòng | Module chủ | Route mới qua Core | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/trich_xuat/common` trên host #6 | `nguon/trich6_host.py:431`, `nguon/trich6_host.py:498` | Core Adapter và `e_trich_xuat` | GET `P/engine/e_trich_xuat` | Response `BoPhan.chuc_nang` chứa capability/schema/giới hạn/readiness, không route `/nang-luc` riêng; không tự công bố năng lực nguồn chưa hỗ trợ (`R:10`). | N |
| GET `/api/trich_xuat/{luot}` | `nguon/trich6_host.py:431`, `nguon/trich6_host.py:529` | Core Job Worker và `e_trich_xuat` | GET `P/viec/{id}`; kết quả qua `P/ket-qua/{id}` | Ánh xạ lượt engine với việc/bước/lần thử Core; không dùng lượt engine làm quyền truy cập. | N |
| GET `/tai/{rel}` trên host #6 | `nguon/trich6_host.py:498`, `nguon/trich6_host.py:484` | Adapter và Core File Store | GET `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` | Giữ kiểm token/allowlist/seal nội bộ; Core kiểm quyền người dùng và nhận kết quả theo F. | N |
| POST `/api/trich_xuat`; POST `/api/trich_xuat/{luot}/{tep,chay}` | `nguon/trich6_host.py:510`, `nguon/trich6_host.py:533` | Core Adapter và `e_trich_xuat` | POST `P/engine/e_trich_xuat/viec`, hoặc lệnh nghiệp vụ CRM/M4/M2 đã khai báo | Một việc Core điều phối chuỗi tạo lượt → gửi tệp → chạy nội bộ; Q, G, J. Không tạo thêm việc khi Adapter retry từng bước. | N |
| POST `/api/trich_xuat/{luot}/dung` | `nguon/trich6_host.py:533` | Core Job Worker và Adapter | POST `P/viec/{id}/huy` | Gửi đề nghị dừng tới đúng lượt/lần thử; chờ trạng thái xác nhận. | N |

### 2.10. Server Review cũ — quản trị, cấu hình, việc và tài sản

Server này tồn tại riêng, không nằm trong nhánh chuyển tiếp shell. Không tự thêm alias các route chung như `/api/cai_dat` vào Core vì có thể trùng với server khác. Căn cứ: `docs/47-core/g0/KS-C.md:132`.

| Route cũ trên server Review | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/phien_ban`, `/api/he_thong` | `m4/review_goc/may_chu/server.py:53`, `m4/review_goc/may_chu/server.py:58` | Core Module Manager và M4 | GET `P/quan-tri/module` | Admin đọc trang registry `TrangBoPhan`, chọn mã m4 ở client; không giả bộ lọc chưa khai. Phiên bản/trạng thái nằm trong `BoPhan`, không trả chi tiết máy chủ/bí mật (`R:10`). | T* |
| GET `/api/tong_quan` | `m4/review_goc/may_chu/server.py:63` | M4 | GET `M4/tong-quan` | Q, H; chỉ dữ liệu pháp nhân/hồ sơ được phép. | T* |
| GET `/api/ai`, `/api/ocr/trang_thai` | `m4/review_goc/may_chu/server.py:68`, `m4/review_goc/may_chu/server.py:109` | Core Engine Manager và cổng AI/OCR | GET `P/quan-tri/engine` | Admin đọc trang registry, chọn engine đã đăng ký ở client; không thêm bộ lọc hoặc route trạng thái chưa có contract. Không gọi thử ghi tệp khi đọc; AI vẫn qua cổng chung (`R:10`). | T* |
| GET `/api/cai_dat`; POST `/api/cai_dat` | `m4/review_goc/may_chu/server.py:74`, `m4/review_goc/may_chu/server.py:79` | Core Engine Manager và quản trị M4 | GET/PUT `P/quan-tri/engine/{ma_engine}/ho-so-chay`; cấu hình nghiệp vụ về M4 sau phân loại | Chỉ trường của `HoSoChay`; PUT kiểm CAS/audit, hồ sơ mẫu đã duyệt, không trả đường dẫn/khóa. Trường Review không có trong schema không chuyển tiếp, phải có contract M4 riêng trước mở T* (`R:10`, `O:45`). | T* |
| POST `/api/cai_dat/{kiem_tra_ai,thu_cloud,tim_may_ai}` | `m4/review_goc/may_chu/server.py:84`, `m4/review_goc/may_chu/server.py:89`, `m4/review_goc/may_chu/server.py:94` | Core quản trị và cổng AI | POST `P/quan-tri/engine/{ma_engine}/thao-tac` cho `kiem_tra_ai`; không alias trực tiếp `thu_cloud`, `tim_may_ai` | Admin gửi `ThaoTacEngine.thao_tac=kiem_tra`, CAS + key, 202. Dò máy/gọi Cloud thử khác kiểm trạng thái, chưa công bố trong contract này; chỉ bật sau contract cổng AI/Mask v2 được duyệt, không nhận URL tùy ý (`R:10`). | T* |
| POST `/api/cai_dat/khoa`; DELETE `/api/cai_dat/khoa/{anthropic,openai}` | `m4/review_goc/may_chu/server.py:99`, `m4/review_goc/may_chu/server.py:104` | Quản trị bí mật của Core/cổng AI | Không có alias trực tiếp | Bỏ API quản lý khóa riêng của Review khỏi bề mặt nghiệp vụ; dùng cơ chế cấu hình bí mật tập trung được thân API/SDK quy định. | B |
| GET `/api/cai_dat/nhat_ky_gui_ngoai` | `m4/review_goc/may_chu/server.py:189` | Core Audit và cổng AI | Không công bố alias v1 trong bộ contract này | Nhu cầu audit gửi ngoài giữ ở cổng AI; không giả một route engine nhật ký không có schema. Cần contract audit riêng trước kích hoạt T*, chỉ metadata an toàn theo quyền (`R:10`). | T* |
| GET `/api/tham_so`; PUT `/api/tham_so` | `m4/review_goc/may_chu/server.py:200`, `m4/review_goc/may_chu/server.py:205` | M4 | GET/PUT `M4/tham-so` | Giữ tham số nghiệp vụ tại M4; Q, G. Không nhập chung với cấu hình engine. | T* |
| POST `/api/ocr/chay_thu` | `m4/review_goc/may_chu/server.py:184` | Core Engine Manager và `e_ocr` | POST `P/engine/e_ocr/viec` | Gửi `LenhOcr` đủ tài liệu/tệp/module/pháp nhân, 202; đây là OCR thực trên dữ liệu được phép, không coi probe liveness là OCR thử. Q, G, J; kết quả theo F (`R:10`). | T* |
| POST `/api/csdl/sao_luu` | `m4/review_goc/may_chu/server.py:194`, `m4/review_goc/may_chu/dich_vu.py:799` | Core Backup/Restore | Không có đích API công khai trong bộ contract này | Bỏ hành vi backup SQLite riêng; backup CSDL–kho tệp theo cơ chế vận hành sau chuyển dữ liệu, không tự công bố `/quan-tri/sao-luu` chưa có contract (`R:10`). | B đối với hành vi SQLite cũ |
| POST `/api/csdl/xuat_excel` | `m4/review_goc/may_chu/server.py:404`, `m4/review_goc/may_chu/dich_vu.py:811` | M4 | POST `M4/xuat-du-lieu/excel` | Q, G, J; xuất dữ liệu đúng phạm vi, trả kết quả Core. | T* |
| GET `/api/viec`, `/api/viec/{id}`; POST `/api/viec/{id}/dung` | `m4/review_goc/may_chu/server.py:211`, `m4/review_goc/may_chu/server.py:216`, `m4/review_goc/may_chu/server.py:224` | Core Job Worker; M4 là chủ nghiệp vụ | GET `P/viec?ma_module=m4`, `P/viec/{id}`; POST `P/viec/{id}/huy` | Ánh xạ ID QLV sang việc Core; Q, J; không dùng hàng RAM Review làm nguồn trạng thái bền duy nhất. | T* |
| POST `/api/tat` | `m4/review_goc/may_chu/server.py:489` | Core Module Manager/Engine Manager | Không giữ alias; Admin dừng qua POST `P/quan-tri/module/m4/thao-tac` | Body `ThaoTacModule` có `thao_tac=dung`, CAS/key, 202; drain và kiểm danh tính tiến trình, không gọi handler tắt server Review cũ (`R:10`, `O:20`). | B |
| GET `/tai/{rel}` | `m4/review_goc/may_chu/server.py:512`, `m4/review_goc/may_chu/dich_vu.py:58` | M4 và Core File Store | GET `P/ket-qua/{id}` lấy `tep_id` rồi GET `P/tep/{tep_id}/noi-dung` | F; kiểm quyền hồ sơ/pháp nhân, thay đường dẫn tương đối bằng tham chiếu được đăng ký. | T* |
| GET `/`, `/index.html`, tài sản tĩnh hợp lệ | `m4/review_goc/may_chu/server.py:512` | Core Shell và gói giao diện M4 | Trang/tài sản của module M4 qua Core | Không mở lại server giao diện riêng cho người dùng. | S |

### 2.11. Server Review cũ — nghiệp vụ và trích xuất

Tiền tố cũ trong bảng này vẫn thuộc **server Review**, không phải host #6 ở §2.9.

| Route cũ trên server Review | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/phu_luc_ai`, `/api/phu_luc_ai/{id}`; POST `/api/phu_luc_ai/{tai_len,chay}`, `/api/phu_luc_ai/{id}/{cap_nhat,hoi_lai_ai,nap}`; DELETE `/api/phu_luc_ai/{id}` | `m4/review_goc/may_chu/server.py:114`, `m4/review_goc/may_chu/server.py:124`, `m4/review_goc/may_chu/server.py:134`, `m4/review_goc/may_chu/server.py:149` | M4 | Cùng tập method và hậu tố dưới `M4/phu-luc-ai` | F cho tải lên; Q, G; `chay/hoi_lai_ai` dùng J và cổng AI chung. `nap` vẫn là lệnh nghiệp vụ riêng; DELETE theo retention, không mặc định xóa dây chuyền. | T* |
| GET `/api/chung_tu`, `/api/chung_tu/{id}`; POST `/api/chung_tu/{tai_len,chay}`, `/api/chung_tu/{id}/cap_nhat`; DELETE `/api/chung_tu/{id}` | `m4/review_goc/may_chu/server.py:154`, `m4/review_goc/may_chu/server.py:164`, `m4/review_goc/may_chu/server.py:174`, `m4/review_goc/may_chu/server.py:179` | M4 | Cùng tập method và hậu tố dưới `M4/chung-tu` | Hợp nhất vào contract chứng từ M4 ở §2.6; không tạo hai handler cùng method/path. F, Q, G, J cho `chay`. | T* |
| GET `/api/trich_xuat`; POST `/api/trich_xuat`; GET `/api/trich_xuat/{luot}` | `m4/review_goc/may_chu/server.py:233`, `m4/review_goc/may_chu/server.py:238`, `m4/review_goc/may_chu/server.py:243` | M4 quản lý lượt chuẩn bị; engine chỉ thực thi | GET/POST `M4/trich-xuat/luot`; GET `M4/trich-xuat/luot/{id}` | Lượt nghiệp vụ tách khỏi việc engine; Q, G; ID cũ ánh xạ theo nguồn. | T* |
| POST `/api/trich_xuat/{luot}/tep`; DELETE `/api/trich_xuat/{luot}/tep/{ten}`; DELETE `/api/trich_xuat/{luot}` | `m4/review_goc/may_chu/server.py:253`, `m4/review_goc/may_chu/server.py:258`, `m4/review_goc/may_chu/server.py:248` | M4 và Core File Store | POST `P/tep`, sau đó POST `M4/trich-xuat/luot/{id}/tep`; DELETE `M4/trich-xuat/luot/{id}/tep/{tep_id}`; DELETE `M4/trich-xuat/luot/{id}` | F, Q, G; gỡ liên kết tệp khác xóa vật lý. Không dùng tên tệp làm ID. Không xóa lượt đang chạy mà bỏ qua quy trình hủy. | T* |
| POST `/api/trich_xuat/{luot}/{chay,chay_lai}` | `m4/review_goc/may_chu/server.py:263`, `m4/review_goc/may_chu/server.py:268` | M4 điều phối; `e_trich_xuat` thực thi | POST `M4/trich-xuat/luot/{id}/{chay,chay-lai}` | Q, G, J; module gọi capability qua Core/Adapter, giữ snapshot/catalog/version của lượt. | T* |
| POST `/api/trich_xuat/{luot}/dung` | `m4/review_goc/may_chu/server.py:273` | Core Job Worker và M4 | POST `P/viec/{id}/huy` | Ánh xạ đúng việc đang chạy; hủy là đề nghị. | T* |
| POST `/api/trich_xuat/{luot}/danh_muc` | `m4/review_goc/may_chu/server.py:281` | Chủ danh mục trích xuất đã đăng ký; M4 là consumer | POST `M4/trich-xuat/luot/{id}/danh-muc` để chọn/ghim danh mục được phép | Giữ phiên bản/hash danh mục. Không trao quyền sửa catalog engine bằng cách chọn catalog trong lượt; quyền sửa quản lý riêng. | T* |
| GET `/api/trich_xuat/{luot}/hd/{ten}` | `m4/review_goc/may_chu/server.py:286` | M4 | GET `M4/trich-xuat/luot/{id}/hop-dong/{hop_dong_id}` | Ánh xạ tên cũ sang ID; Q, H; kết quả OCR/trích xuất chưa đồng nghĩa hợp đồng đã duyệt. | T* |
| PATCH `/api/trich_xuat/{luot}/hd/{ten}/o/{ma}` | `m4/review_goc/may_chu/server.py:291` | M4 | PATCH `M4/trich-xuat/luot/{id}/hop-dong/{hop_dong_id}/o/{ma}` | Q, G; giữ revision kết quả và dẫn chứng của ô được sửa. | T* |
| POST `/api/trich_xuat/{luot}/hd/{ten}/{xac_nhan,nap_csdl}` | `m4/review_goc/may_chu/server.py:296`, `m4/review_goc/may_chu/server.py:301` | M4 | POST `M4/trich-xuat/luot/{id}/hop-dong/{hop_dong_id}/{xac-nhan,nap}` | Giữ hai bước xác nhận/nạp; kiểm quyền và CAS lại khi ghi. Giữ nhánh chỉ so sánh khi hợp đồng đã tồn tại; không ép thành ghi mới. | T* |
| GET `/api/hop_dong`, `/api/hop_dong/{ref}`, `/api/hop_dong/{ref}/boq`, `/api/hop_dong/{ref}/phu_luc/{so}` | `m4/review_goc/may_chu/server.py:307`, `m4/review_goc/may_chu/server.py:312`, `m4/review_goc/may_chu/server.py:317`, `m4/review_goc/may_chu/server.py:354` | M4 | GET `M4/hop-dong`, `M4/hop-dong/{id}`, `M4/hop-dong/{id}/boq`, `M4/hop-dong/{id}/phu-luc/{so}` | Ánh xạ `ref` Review sang ID M4 theo phiếu CSDL; hợp nhất route chi tiết với §2.6, không giữ hai nguồn sự thật. | T* |
| POST `/api/hop_dong/{ref}/{phieu_phu_luc,kiem_dot}`, `/api/hop_dong/{ref}/phu_luc/{so}/huy`, `/api/hop_dong/{ref}/tham_so/{ma}/xac_nhan` | `m4/review_goc/may_chu/server.py:322`, `m4/review_goc/may_chu/server.py:332`, `m4/review_goc/may_chu/server.py:327`, `m4/review_goc/may_chu/server.py:349` | M4 | POST `M4/hop-dong/{id}/{phieu-phu-luc,kiem-dot}`, `M4/hop-dong/{id}/phu-luc/{so}/huy`, `M4/hop-dong/{id}/tham-so/{ma}/xac-nhan` | Q, G, F; `kiem_dot` dùng J; giữ căn cứ và điều kiện hủy/xác nhận. | T* |
| POST `/api/phu_luc/{kiem_tra,nap}` | `m4/review_goc/may_chu/server.py:339`, `m4/review_goc/may_chu/dich_vu.py:774` | M4 | POST `M4/phu-luc/{kiem-tra,nap}` | Cả hai có thể nhận/lưu tệp; F. Kiểm tra không đồng nghĩa đã nạp nghiệp vụ; Q, G, J nếu dài. | T* |
| POST `/api/toan_ven` | `m4/review_goc/may_chu/server.py:344` | M4 | POST `M4/toan-ven` | Q, G, J; giữ kết quả kiểm như căn cứ chờ xử lý. | T* |
| GET `/api/kiem_tra/{kiem_tra_dot,toan_ven}` và `/api/kiem_tra/{kiem_tra_dot,toan_ven}/{ma}` | `m4/review_goc/may_chu/server.py:359`, `m4/review_goc/may_chu/server.py:364` | M4 | GET `M4/kiem-tra/{kiem-tra-dot,toan-ven}` và `M4/kiem-tra/{kiem-tra-dot,toan-ven}/{id}` | Q, H; danh sách/chi tiết kết quả nghiệp vụ khác trạng thái việc. | T* |
| POST `/api/kiem_tra/kiem_tra_dot/{ma}/{nap,ghep,chay_lai}` | `m4/review_goc/may_chu/server.py:369`, `m4/review_goc/may_chu/server.py:374`, `m4/review_goc/may_chu/server.py:379` | M4 | POST `M4/kiem-tra/kiem-tra-dot/{id}/{nap,ghep,chay-lai}` | Q, G; `chay_lai` dùng J; nạp/ghép phải kiểm revision và căn cứ hiện hành. | T* |
| POST `/api/boq/{tai_len,sheet,kiem_tra,ghi}` | `m4/review_goc/may_chu/server.py:384`, `m4/review_goc/may_chu/server.py:389`, `m4/review_goc/may_chu/server.py:394`, `m4/review_goc/may_chu/server.py:399` | M4; OCR qua engine | POST `M4/boq/{tai-len,trang-tinh,kiem-tra,ghi}` | F, Q, G; nhánh tải có OCR/chuyển đổi dùng J, không giữ xử lý dài trong upload HTTP. `trang_tinh/kiem_tra` không tự ghi BOQ; `ghi` là lệnh riêng. | T* |

Các nhóm Review và M4 có cùng đích phải được ghép thành **một contract chuẩn**, với Adapter chuyển payload cũ theo nguồn. Không đăng ký hai operation cho cùng method/path, không dùng thứ tự handler để chọn ngầm hợp đồng.

### 2.12. Endpoint chỉ thấy từ client trong KS-C

Các endpoint này là địa chỉ engine mà backend đang gọi, **không phải route công khai do shell cung cấp**. Ánh xạ dưới đây mô tả nơi chức năng xuất hiện qua Core; không yêu cầu đổi ngay protocol nguồn.

| Endpoint cũ | Tệp:dòng | Module chủ | Route mới qua Core | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| Mask GET `/api/v1/trang-thai`; POST `/api/v1/{che,mo-che}` | `tri_thuc/cong_ai.py:635`, `tri_thuc/cong_ai.py:660`, `tri_thuc/cong_ai.py:669`, `tri_thuc/cong_ai.py:683` | Cổng AI chung, Adapter và `e_mask` | GET `P/engine/e_mask`; POST `P/engine/e_mask/viec` với capability được cấp; GET `P/viec/{id}` | Response `BoPhan.chuc_nang`, không route năng lực riêng. Nguồn cùng tiền tố nhưng khác dịch vụ; không proxy browser/Bearer. Giữ kiểm danh mục, `gui_duoc`, `con_sot` (`R:10`). | N |
| Bộ tải GET `/api/config`; POST `/api/profiles` | `m2/tai_hoa_don/khach.py:95`, `m2/tai_hoa_don/khach.py:101` | Core Engine Manager, Adapter và M2 | GET `P/quan-tri/engine/e_hoa_don/ho-so-chay`; phần nghiệp vụ GET `T/trang-thai` | Admin chỉ đọc `HoSoChay` an toàn; profile đăng nhập nội bộ do Adapter ánh xạ từ hồ sơ đã duyệt, không chuyển POST tạo profile thành GET có ghi. Phần cần sửa dùng PUT cùng hồ sơ với CAS/quyền; không công khai credential (`R:10`). | N |
| Bộ tải POST `/api/{start,status,reconcile}` | `m2/tai_hoa_don/khach.py:129`, `m2/tai_hoa_don/khach.py:133`, `m2/tai_hoa_don/khach.py:137` | M2 và Adapter `e_hoa_don` | POST `T/bat-dau`; GET `P/viec/{id}`; POST `T/doi-soat` tương ứng | Chuẩn hóa method trạng thái về GET; Q, G, J. Phải khớp protocol bản nguồn/bản vá trước khi bật. | N |
| Bộ tải POST `/api/open-folder` | `m2/tai_hoa_don/khach.py:140` | Adapter bộ tải | Không có đích API công khai; tải kết quả qua Core | Không chuyển thao tác mở thư mục máy chủ sang UI nhiều người dùng. | B |
| Bộ tải POST `/api/events` | `m2/tai_hoa_don/khach.py:156` | Adapter và Core Job Worker | GET `P/viec/{id}` | Adapter tiếp tục nhận sự kiện nguồn nội bộ rồi cập nhật việc bền; client Core poll snapshot theo J, không phát stream Core. Không đồng nhất POST nguồn với SSE GET (`R:10`, `O:18`). | N |

**Không có route cũ để ánh xạ:**

| Thành phần | Kết luận có căn cứ | Xử lý trong bộ API |
|---|---|---|
| OCR-1 | Là API Python/Hot Folder, chưa thấy HTTP dispatcher tại lớp được khảo sát: `ha_tang/cong_ocr.py:127`, `ha_tang/cong_ocr.py:274`, `ha_tang/cong_ocr.py:339`. | Chức năng mới qua `P/engine/e_ocr/viec` và Adapter; không ghi thành “đổi route OCR cũ”. |
| Cổng AI | Có `CongAI.goi`, chưa thấy nhóm HTTP `/api/ai/...` được nối vào shell: `tri_thuc/cong_ai.py:979`, `tri_thuc/cong_ai.py:1236`, `server.py:982`. | Các module tiếp tục dùng cổng AI chung qua hợp đồng SDK/Adapter; không dựng đường gọi Cloud riêng trong lớp chuyển tiếp. |
| M3 | Có dịch vụ Python, chưa thấy route HTTP trong dispatcher được khảo sát: `k2/m3.py:240`, `k2/m3.py:246`, `server.py:976`. | API M3 là phần đặc tả module sau; không suy ra route từ tên hàm. |
| Workflow chung | Chưa thấy route workflow dùng chung trong shell: `docs/47-core/g0/KS-C.md:202`. | Nhóm `P/quy-trinh` là API mới thuộc thân đặc tả, không phải đổi tiền tố route hiện có. |

## 3. Route và quy ước chưa đạt nguyên tắc — cách sửa

Bảng này đối chiếu các quy ước hiện tại ở KS-C §4 và các chênh lệch quyền ở KS-C §6. Mức kết luận giới hạn theo đường xử lý đã khảo sát; không suy rằng mọi module đều có cùng lỗi.

| Vấn đề và phạm vi | Căn cứ hiện trạng | Cách sửa trong route mới |
|---|---|---|
| **Actor do client khai:** `/api/that/knowledge/decide`, `/api/that/quick/decide`, `/api/that/proposals/decide`; metadata nhập tri thức cũng mang actor. | `server.py:1170`, `server.py:1204`, `server.py:1211`, `server.py:1217`, `giao_dien/operations.py:972` | Actor audit lấy từ phiên backend. Nếu nghiệp vụ có “người được giao” thì là trường riêng được kiểm quyền, không dùng làm danh tính người gọi. Quyền duyệt do MTQ/hồ sơ quyết định. |
| **Token chung chưa phải xác thực từng người**, nhóm `/api/that/...` chưa gắn phiên người dùng; trạng thái nghiệp vụ có thể chọn phiên OPEN chung mới nhất. | `server.py:63`, `server.py:928`, `server.py:1023`, `giao_dien/operations.py:834` | Tất cả API riêng tư dùng phiên Core. Pháp nhân và phiên nghiệp vụ phải xác định, kiểm quyền rõ; không lấy phiên “mới nhất toàn hệ thống” làm mặc định. |
| **Danh tính DEMO và kho phiên RAM** không đáp ứng phiên production nhiều tiến trình. | `server.py:193`, `server.py:196`, `server.py:340`; `docs/47-core/g0/KS-C.md:173` | Tách hoàn toàn đổi vai DEMO khỏi `P/phien`. Phiên có vòng đời, hết hạn/thu hồi và khả năng dùng xuyên tiến trình theo thân API/phiếu CSDL. |
| **Download chỉ có kiểm ID/đường dẫn** ở intake, quick, shadow, outside-catalog và bridge nghiệm thu. | `server.py:1019`, `server.py:1048`, `server.py:1057`, `server.py:1134`, `server.py:1138`, `giao_dien/operations.py:771`, `giao_dien/operations.py:1044` | Tải qua File Store Core; kiểm pháp nhân, quyền hồ sơ, biến thể và trạng thái công bố. ID hợp lệ hoặc biết tên tệp không tạo quyền tải. Alias cũ phải gọi cùng cổng này. |
| **Download Review cũ** chỉ ràng buộc thư mục; không được gán kết luận này cho host #6 có token/allowlist/seal. | `m4/review_goc/may_chu/server.py:512`, `m4/review_goc/may_chu/dich_vu.py:58`, `nguon/trich6_host.py:484` | Đăng ký kết quả và quan hệ hồ sơ ở Core trước khi tải. Giữ bảo vệ seal/token của host #6 phía nội bộ. |
| **Lỗi và mã HTTP chưa thống nhất.** | `server.py:1288`, `crm_g.py:693`, `m4.py:616`, `m2_tai_hoa_don.py:574`, `m4/review_goc/may_chu/server.py:477`; `docs/47-core/g0/KS-C.md:167` | API v1 dùng envelope chung. Phân biệt 401 chưa có phiên hợp lệ, 403 không đủ quyền, 409 xung đột, 413 quá giới hạn, 422 lỗi nghiệp vụ theo contract; phân loại lỗi dependency/timeout trong thân API. Không trả exception/đường dẫn/bí mật nguyên trạng. |
| **Việc dài trả 200/201/202 khác nhau hoặc giữ HTTP đến khi xong.** | `server.py:1161`, `server.py:1169`, `server.py:1231`, `crm_g.py:658`, `m4.py:592`, `m2_tai_hoa_don.py:1076` | Dùng J. 202 nghĩa đã tiếp nhận việc bền, không phải xử lý thành công. Không giả lập thành công đồng bộ từ một ACK nền. |
| **Điều phối còn RAM** ở Operations, tải tất cả M2, QLV Review; G5 đã có hàng việc bền. | `giao_dien/operations.py:873`, `m2_tai_hoa_don.py:213`, `m4/review_goc/may_chu/viec.py:79`, `k2/crm_doi_chieu.py:371` | Dùng nền hàng việc PostgreSQL hiện có, bổ sung ánh xạ việc/bước/lần thử theo phiếu CSDL. Giữ hàng việc G5; không tạo một hàng đợi Core song song không liên thông. |
| **Idempotency phân tán**, chưa có chính sách HTTP chung. | `giao_dien/intake.py:74`, `k2/xay_dung.py:154`, `k2/crm_mau.py:160`, `k2/lien_ket_chung.py:3` | Chuẩn hóa header, phạm vi, thời hạn và fingerprint trong thân API. Module giữ namespace K2 pháp nhân/module/operation/key; người gọi khác chỉ được phát lại nếu còn quyền hành động và đọc kết quả; Core tách thêm người dùng trong phạm vi riêng (`O:35`). Nối với biên nhận/dedupe cũ; khác payload cùng key phải bị từ chối. |
| **CAS có nhiều loại token**, không thể thay tất cả bằng một số phiên bản dòng. | `crm_g.py:60`, `crm_g.py:75`, `crm_g.py:123`, `crm_g.py:706`, `m4.py:20`, `module_cong_tac.py:65` | Bổ sung `row_version` nơi phù hợp; giữ graph/revision/basis/context token và ý nghĩa của chúng. Client cũ thiếu căn cứ bắt buộc phải tải lại dữ liệu, không tự điền version mới nhất để cho ghi qua. |
| **Phân trang khác tên/tham số**, có danh sách chỉ cắt LIMIT. | `k2/crm_s1.py:52`, `k2/crm_s1.py:72`, `k2/hoa_don.py:505`, `k2/kho_so_luong.py:473`, `giao_dien/operations.py:945`, `khung_khai_bao.py:116` | V1 dùng contract phân trang chung, thứ tự ổn định, giới hạn và thông tin còn dữ liệu. Alias đổi tên tham số nhưng không âm thầm bỏ các trang sau. |
| **Upload raw/header metadata và base64 JSON chưa thống nhất**; giới hạn từng lớp khác nhau. | `server.py:931`, `server.py:945`, `server.py:1143`, `server.py:1232`, `crm_g.py:608` | Dùng F; schema khai rõ metadata, MIME, kích thước và checksum. Alias giải mã định dạng cũ có giới hạn; không tăng trần để bỏ qua giới hạn module/engine. |
| **CSRF/Origin dựa token chung hoặc header `X-HD`** chưa thay được xác thực người dùng. | `server.py:918`, `server.py:980`, `server.py:1008`, `m4/review_goc/may_chu/server.py:417` | Giữ kiểm Origin/Host phù hợp địa chỉ Core triển khai; thêm bảo vệ CSRF gắn với cơ chế phiên theo thân API. Không coi loopback hoặc header tĩnh là quyền người dùng. |
| **GET có ghi nghiệp vụ:** `/api/nghiem-thu` gọi `dong_bo`. | `server.py:137`, `server.py:1128` | Tách POST đồng bộ và GET danh sách. Alias GET không được tiếp tục ghi ngầm. |
| **Lệnh mở thư mục/tắt server** không phù hợp thao tác từ nhiều máy người dùng. | `server.py:1196`, `server.py:1282`, `m2_tai_hoa_don.py:1069`, `m4/review_goc/may_chu/server.py:489` | Thay mở thư mục bằng tải kết quả; dừng tiến trình qua quản trị Core có drain và xác minh danh tính. |
| **Dispatcher hiện gọi module trong cùng backend**, chưa phải chuyển tiếp tiến trình riêng. | `docs/47-core/g0/KS-A.md:18`, `server.py:976` | Dispatcher định tuyến theo registry tới tiến trình module riêng; không giữ cách import trực tiếp làm kiến trúc đích. Ngữ cảnh người dùng/pháp nhân/request phải truyền qua kênh tin cậy do bộ API/SDK chốt. |

**Phần phải giữ:** kiểm quyền backend của download CRM/M4/M5/M9 và khung CRM đã có giá trị sử dụng; không bỏ để thay bằng kiểm quyền chung yếu hơn. Căn cứ: `k2/crm.py:860`, `k2/xay_dung.py:309`, `k2/kho_so_luong.py:720`, `k2/vay.py:798`, `khung_khai_bao.py:103`.

**Lưu ý engine:** xử lý thành công, hết mục cần soát và phê duyệt nghiệp vụ là ba trạng thái khác nhau (`docs/47-core/g0/KS-E.md:110`). Adapter giữ revision và thu nhận kết quả theo chính sách trước khi engine giải phóng RAM; TTL API 600 giây, session UI RAM 3.600 giây không phải retention Core (`docs/47-core/g0/KS-E.md:112`, `docs/47-core/g0/KS-E.md:113`, `docs/47-core/g0/KS-E.md:114`). ABBYY có API/TTL riêng, không áp bảo đảm RAM-only của dual cho Hot Folder (`docs/47-core/g0/KS-E.md:122`, `docs/47-core/g0/KS-E.md:126`).

## 4. Nguyên tắc lớp chuyển tiếp route cũ

### 4.1. Một đường thực thi có kiểm quyền

Luồng đề xuất:

`Client cũ → alias tại Core → chuẩn hóa đầu vào → xác thực/quyền/schema chung → operation v1 → module hoặc Adapter → kết quả chuẩn → bộ đổi response cũ nếu an toàn`.

Alias không gọi ngược vào handler cũ để bỏ qua cổng bảo vệ mới. Không cho tồn tại hai đường ghi độc lập cho cùng operation.

Route cũ và route v1 phải dùng chung:

- Danh tính đã xác thực, phạm vi pháp nhân và quyền hồ sơ.
- Công tắc module, quyền người thử và MTQ.
- Biên nhận idempotency tại **chủ operation** và điều kiện CAS; cùng operation/body logic/khóa dù khác path. Module giữ vĩnh viễn cùng transaction, đối chiếu 504 tại module; Core không giữ bản hoàn tất riêng (`O:31`).
- Việc nền, kết quả và audit nghiệp vụ.

Một người dùng có thể dùng cả client cũ và mới nhưng không được tạo hai lần tác động chỉ vì đổi tiền tố route. Yêu cầu này nối tiếp nền dedupe/biên nhận hiện có tại `k2/lien_ket_chung.py:3`, `k2/crm_mau.py:160`, `k2/xay_dung.py:154`.

### 4.2. Tương thích có giới hạn rõ

Alias được đổi tên trường, path/query parameter, định dạng upload và response theo bảng ánh xạ. Không giữ các hành vi:

- Tự nhận actor từ client hoặc tự đăng nhập bằng vai DEMO.
- Tải tệp chỉ nhờ biết ID/đường dẫn.
- Ghi nghiệp vụ trong GET.
- Mở thư mục máy chủ, quản lý khóa riêng của Review hoặc tắt server bằng token chung.
- Bỏ điều kiện CAS, quyền hoặc trạng thái cần duyệt để client cũ tiếp tục chạy.

Nếu client cũ không hỗ trợ hợp đồng an toàn mới thì phải nâng cấp client hoặc dừng operation tương ứng. Không tuyên bố tương thích hoàn toàn với mọi client cũ.

Với việc dài, phương án ưu tiên là cập nhật client cũ nhận 202 và theo dõi việc Core. Không giữ HTTP kéo dài chỉ để mô phỏng response đồng bộ cũ; không trả 200 “đã xong” khi việc mới được xếp hàng.

### 4.3. Định tuyến và ranh giới dịch vụ

1. Alias chỉ được đăng ký theo allowlist method/path/schema; không dùng quy tắc thay tiền tố tùy ý cho toàn bộ `/api/*`.
2. Các route trùng tên giữa shell, Review và host #6 phải được định danh bằng **nguồn dịch vụ + method + mẫu path** trước khi ánh xạ.
3. Không dùng HTTP redirect để chuyển lệnh ghi hoặc upload sang route mới. Core thực hiện chuyển đổi nội bộ để kiểm soát body, quyền và idempotency.
4. Core loại header nội bộ giả mạo rồi ký token TTL 30 giây, ràng buộc instance/method/path/body, key và mã ủy nhiệm bí mật không phải SID. Hàm CSDL băm mã, đối chiếu `loi.phien_xac_thuc`/login/pháp nhân/hạn/hành động; GUC tự khai không tạo danh tính. Việc nền gắn mã với `viec_id`/thế hệ lease (`O:19`, `D:135`, `D:301`).
5. Frontend chỉ thấy địa chỉ Core; không nhận URL, cổng hoặc credential engine để tự gọi.
6. Alias vẫn chịu thời hạn, giới hạn body, rate/concurrency và chính sách lỗi của Core; không phải đường dự phòng nới quyền.
7. Credential SDK riêng mỗi instance qua kênh stdin/handle bootstrap cùng `fromshare`, gắn instance ID và thu hồi khi dừng/crash; không qua môi trường/dòng lệnh/log. Module có login CSDL riêng được cấp hữu hạn; engine/máy phụ **không login CSDL**, máy phụ chỉ kéo việc và không có cổng nhận/chuyển ổ nghe (`O:19`, `O:20`, `D:257`, `D:267`).
8. TLS bắt buộc ngoài loopback để dùng cookie `__Host-` Secure; không bỏ Secure cho HTTP IP LAN. DEMO loopback vẫn riêng (`O:21`).

Theo CD-028, mỗi module/engine có cổng nội bộ cố định do Core cấp. Khi chưa chạy, Core giữ socket; khi cần thì khởi động, chuyển giao socket và kiểm danh tính/phiên bản/readiness trước khi chuyển tiếp. Với engine cũ chưa nhận socket, dùng phương án chuyển tiếp có kiểm xung đột; không tự chọn cổng khác hoặc dừng tiến trình lạ. Căn cứ: `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:329`, `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:330`, `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:333`.

Khi drain, trạng thái `dang_dung` từ chối request mới 503/`Retry-After: 2`; quyết định đóng rảnh dùng cùng khóa dispatch và đếm cả request đồng bộ. Ba lỗi khởi động liên tiếp sau giãn 2/4 giây giữ `failed`, 503 ngay, chờ Admin; lưu khóa lỗi bền ở Core. Chuyển ổ nghe chỉ trên máy Core (`O:20`).

Không module/engine nào mặc định luôn chạy. Việc giữ lâu hơn hoặc luôn chạy phải dựa số đo và do Admin áp dụng, theo `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:331`, `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:332`.

### 4.4. Ánh xạ ID và hợp đồng dữ liệu

- Giữ ID nghiệp vụ ổn định khi đã phù hợp; ID nguồn cũ được ánh xạ có namespace, tránh trùng giữa Review, CRM, bridge và engine.
- Không mặc định mọi `{id}`, `{ref}`, `{luot}`, `{ten}` cũ đều là UUID Core.
- Mỗi alias tải xuống phải xác định được đối tượng nghiệp vụ, pháp nhân, tệp/kết quả, phiên bản và biến thể trước khi trả bytes.
- Alias không tự truy vấn chéo schema để ghép quyền hoặc tái tạo nghiệp vụ. Dữ liệu chung qua dịch vụ Core; dữ liệu module khác qua contract công bố — theo phiếu CSDL.
- Hợp đồng nội bộ engine có thể tiếp tục khác API Core; Adapter chịu trách nhiệm chuyển đổi. Không dùng bảng này để khẳng định engine nguồn đã hỗ trợ capability mới.

Chênh lệch protocol bộ tải và phạm vi capability #6 phải được giải quyết trước khi kích hoạt Adapter: `docs/47-core/g0/KS-D.md:60`, `docs/47-core/g0/KS-D.md:62`, `docs/47-core/g0/KS-D.md:63`. Mask API khảo sát mới đủ căn cứ cho che/mở che văn bản; không mặc định đã có contract che tài liệu độc lập: `docs/47-core/g0/KS-D.md:53`.

### 4.5. Theo dõi sử dụng và thông báo ngừng

Mỗi nhóm alias được giữ cần có:

- Chủ module và người chịu trách nhiệm chuyển client.
- Phiên bản client còn phụ thuộc.
- Ngày dự kiến ngừng và thời gian quan sát được duyệt.
- Số lượt gọi, lỗi, độ trễ và số việc đang chạy; không ghi toàn văn tài liệu, token hoặc dữ liệu nhạy cảm vào log.
- `request_id` xuyên alias–operation–module–việc; audit nghiệp vụ chỉ ghi một lần, có dấu vết request đi qua alias.

Response có thể thêm `Deprecation`, liên kết tài liệu thay thế và `Sunset` khi ngày ngừng đã được phê duyệt. Không tự đặt ngày để biến bản nháp thành cam kết vận hành.

## 5. Điều kiện gỡ route cũ

Gỡ theo từng nhóm operation/module, không yêu cầu giữ toàn bộ route cũ đến khi mọi module của hệ thống chuyển xong. Route **N** nội bộ có vòng đời riêng với alias công khai.

| Điều kiện bắt buộc | Bằng chứng cần có trước khi gỡ |
|---|---|
| Đích v1 đã chốt | Route, schema, quyền, HTTP status và thay đổi hợp đồng được ghép vào bộ API đã duyệt; các dòng T* đã có quyết định. |
| Nghiệp vụ đã chuyển đủ | Client/gói module dùng API mới; các thao tác đọc, ghi, duyệt, xuất và tải tệp cần thiết đều có đích hoạt động. |
| Dữ liệu và ID liên tục | Ánh xạ ID/phiên bản/biên nhận được kiểm; không làm mất liên kết hồ sơ, lịch sử hoặc kết quả cũ. |
| Không tạo lỗ hổng khi chuyển | Kiểm truy cập khác người dùng/pháp nhân, quyền bị thu hồi, tải tệp trái phép, actor giả, CSRF và gọi thẳng cổng nội bộ đều đạt tiêu chí đã duyệt. |
| Ghi và việc nền an toàn | Retry cùng key, cùng key khác payload, CAS xung đột, restart worker/module, ngắt kết nối và hủy việc không gây ghi trùng hoặc mất trạng thái. |
| Hết phụ thuộc đang chạy | Không còn việc/lượt/luồng SSE cần alias để theo dõi, hủy hoặc nhận kết quả; đã bàn giao hoặc chuyển sang ID Core. |
| Đã quan sát sử dụng | Không còn client hợp lệ gọi alias trong khoảng quan sát đã duyệt; phân biệt probe/lỗi do client cũ với sử dụng nghiệp vụ thực. |
| Có quyết định ngừng | Chủ module xác nhận hoàn tất; ngày ngừng và thông báo cho người sử dụng theo kế hoạch phát hành được duyệt. |
| Có phương án quay lại | Có thể khôi phục alias an toàn hoặc phiên bản client tương thích mà không khôi phục đường bỏ qua quyền, không hoàn tác bằng xóa dữ liệu. |

Khi đã ngừng có chủ đích, có thể giữ phản hồi `410 Gone` với lỗi chuẩn và chỉ dẫn API thay thế trong thời gian đã duyệt; route chưa từng công bố tiếp tục trả 404. Không giữ handler nghiệp vụ cũ phía sau phản hồi ngừng.

**Ghép phê duyệt chuyển đổi vào §7 phiếu API:** phân ranh `V` theo đề xuất §2.2; giữ alias từng nhóm đủ contract rồi gỡ theo §5 (khuyến nghị), hoặc ngừng ngay khi client đã chuyển đủ (ít bảo trì nhưng cần chuyển đồng loạt). Không tự đặt lịch ngừng. Chủ nghiệp vụ/mã module, trường cấu hình Review và contract MTQ/audit chưa được duyệt là cổng chặn **kích hoạt T***, không phải route Core đã công bố (`R:12`, `O:48`). Nguồn đăng nhập và retention **hỏi chung ở phiếu CSDL** câu 3/câu 2 (`D:453`, `D:452`); cơ chế phiên/ủy nhiệm và biên nhận đã ghi cụ thể ở thân/OpenAPI, không còn câu chọn kỹ thuật (`O:22`).

**Tự kiểm của lát:** đối chiếu các nhóm route KS-C §2–§3, quy ước §4 và chênh lệch §6; vòng 2 chỉ sửa hai tài liệu và kiểm tĩnh, không chạy ứng dụng/test nghiệp vụ/migration hay gọi dịch vụ. Tài liệu này chưa phải bằng chứng kiểm thử triển khai; việc lập trình vẫn dừng theo CD-026 và chỉ mở lại khi đủ điều kiện CD-029 tại `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:344`.

## Vòng 2 — đã xử lý

Mã O theo các mục/C1 của review Opus; R-1…R-6 theo thứ tự dòng phát hiện Codex (`O:14`, `O:26`, `R:7`). Bảng chỉ ghi xử lý đặc tả; T* vẫn là cổng triển khai cần duyệt, không phải xác nhận runtime.

| Mã phát hiện | Chỗ sửa |
|---|---|
| O-C1 — biên nhận module/Core | §1.4 G; §4.1; §3 dòng idempotency (`docs/47-core/g1/ANH-XA-ROUTE.md:75`) |
| O-1 — chi tiết lỗi/mã module | §1.4 H (`docs/47-core/g1/ANH-XA-ROUTE.md:74`) |
| O-3a/3b — interrupted/MTQ | §1.4 J; §2.8 polling (`docs/47-core/g1/ANH-XA-ROUTE.md:76`) |
| O-4a/4b — ủy nhiệm/login/credential | §4.3, quy tắc 4/7 (`docs/47-core/g1/ANH-XA-ROUTE.md:374`) |
| O-5a/5b/5c — drain/failed/máy phụ | §4.3, vòng đời và máy phụ (`docs/47-core/g1/ANH-XA-ROUTE.md:382`) |
| O-6a/6b — TLS/kho tệp Core | §1.4 F; §4.3 quy tắc 8 (`docs/47-core/g1/ANH-XA-ROUTE.md:77`) |
| O-7; R-4 — câu hỏi/V/alias | §2.2; quyết định chuyển đổi cuối §5; hỏi chung CSDL (`docs/47-core/g1/ANH-XA-ROUTE.md:426`) |
| R-1 — thống nhất gạch nối | §1.1, toàn bộ cột route mới; nguồn cũ được giữ (`docs/47-core/g1/ANH-XA-ROUTE.md:44`) |
| R-2 — đích Core thiếu contract | §2.5, §2.8–2.12: operation đã khai hoặc không công bố/chặn T* (`docs/47-core/g1/ANH-XA-ROUTE.md:164`) |
| R-3 — tệp hệ thống | §1.4 F: null, Admin, không header giả (`docs/47-core/g1/ANH-XA-ROUTE.md:77`) |
| R-5 — nguồn KS-E sai | §3: revision/duyệt/RAM/TTL/ABBYY (`docs/47-core/g1/ANH-XA-ROUTE.md:334`) |
| R-6 (gợi ý) — 409 tường minh | Dùng response XungDot trong A; G giữ CAS và chống trùng (`docs/47-core/g1/ANH-XA-ROUTE.md:75`) |
