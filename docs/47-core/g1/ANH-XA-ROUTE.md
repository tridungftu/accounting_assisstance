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
| `T` | `/api/v1/module/m2/tai_hoa_don` |
| `V` | `/api/v1/module/{ma_module_van_hanh}` — tên giữ chỗ, chưa chốt chủ sở hữu |

Tên nghiệp vụ mới dùng tiếng Việt không dấu, `snake_case`; giữ mã module, mã engine, thuật ngữ kỹ thuật như `boq`, định dạng `pdf`, `docx` và các tên contract đã quy định. Căn cứ hướng đặt tên: `docs/47-core/g0/KS-C.md:178`.

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
| **H** | JSON Schema cho đầu vào/đầu ra; lỗi `{ma, thong_diep, request_id, thu_lai_duoc}`; mã HTTP và phân trang theo thân đặc tả API. |
| **G** | Lệnh ghi có idempotency; đối tượng sửa đồng thời có `row_version` khi phù hợp. Giữ các token CAS nghiệp vụ đặc thù và biên nhận hiện có. |
| **J** | Việc dài trả `202 + viec_id`, theo dõi qua `GET P/viec/{id}`, kết quả qua `P/ket_qua`, hủy bằng `POST P/viec/{id}/huy` và chỉ là đề nghị. Việc phải được ghi nhận bền trước khi ACK. |
| **F** | Tải lên qua `POST P/tep`, trả `tep_id`; module nhận tham chiếu tệp. Tải xuống qua `GET P/tep/{id}/noi_dung` hoặc `GET P/ket_qua/{id}/noi_dung`, có kiểm quyền nội dung và biến thể. Không nhận đường dẫn máy chủ tùy ý. |

Căn cứ yêu cầu chung: `../55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:29`, `../55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:30`, `../54-ke-hoach-core-database-api-v1.md:134`, `../54-ke-hoach-core-database-api-v1.md:309`.

**Phụ thuộc CSDL:** danh tính, quyền, registry và việc dùng tên nháp `loi`; tệp, tài liệu, kết quả dùng `loi_tai_lieu`; nghiệp vụ dùng `mod_crm`, `mod_m2`, `mod_m4`, các `mod_*` tương ứng; dữ liệu dùng chung qua `danh_muc`, dữ liệu công bố qua `cong_bo_<module>` — **theo phiếu CSDL**. API không cam kết tên bảng hoặc cho phép client truy cập trực tiếp schema. Nguồn tên nháp: `../55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:16`.

## 2. Bảng route cũ → route mới

### 2.1. Shell, tiếp nhận, DEMO và vận hành hệ thống

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/health` | `server.py:1003` | Core | GET `/healthz`, GET `/readyz` | Tách sống/sẵn sàng; không lộ thông tin kết nối nội bộ. Không yêu cầu mọi engine đang chạy để Core sẵn sàng. | T |
| GET `/`, `/index.html`; `/{app.js,style.css,that.css,mark.svg,crm_g.js,m2_tai_hoa_don.js,ma_tran_tham_quyen.js}` | `server.py:1007`, `server.py:1010` | Core Shell | Giữ trang shell và tài sản tĩnh | Bỏ phụ thuộc token chung chèn trong HTML; giao diện dùng phiên Core. | S |
| GET `/api/state` | `server.py:81`, `server.py:1014` | Core và module tiếp nhận/vận hành, chờ chốt phần nghiệp vụ | GET `P/toi`; GET `P/module`; GET `V/trang_thai` cho phần nghiệp vụ | Tách trạng thái người dùng, module và nghiệp vụ; bỏ đường dẫn lưu trữ vật lý, không dùng phiên nghiệp vụ chung mới nhất. Q, H. | T* |
| GET `/api/sample` | `server.py:92`, `server.py:1016` | Bộ dữ liệu DEMO | Không có đích production | Chỉ dữ liệu giả, giữ tham số nguồn trong môi trường thử. | D |
| POST `/api/upload` | `server.py:1143` | Core File Store; module tiếp nhận giữ liên kết nghiệp vụ | POST `P/tep`; nếu cần đăng ký tài liệu: POST `P/tai_lieu` | F, Q, G; tiếp nhận tệp không tự động đồng nghĩa đã nhập nghiệp vụ. | T |
| GET `/api/files/{id}/download` | `server.py:1019` | Core File Store | GET `P/tep/{id}/noi_dung` | F; ánh xạ ID cũ sang ID Core, kiểm quyền hồ sơ/pháp nhân trước khi trả bytes. | T |
| POST `/api/demo/{validate,ingest}` | `server.py:99`, `server.py:1277` | Bộ kiểm chứng DEMO | Không có đích production | Giữ validate/ingest dữ liệu giả trong môi trường thử; không nâng thành đường nhập dữ liệu thật. | D |
| GET `/api/demo/vai` | `server.py:1065` | Bộ kiểm chứng DEMO | Không có đích production; xác thực thật dùng `P/phien`, GET `P/toi` | Bỏ hành vi GET cấp/đổi danh tính DEMO trên production. | D |
| POST `/api/shutdown` | `server.py:1282` | Vận hành Core | Không có đích API nghiệp vụ | Tắt Core qua cơ chế vận hành được quản lý; không giữ lệnh tắt từ token dùng chung. | B |
| OPTIONS mọi đường dẫn | `server.py:973` | Core Dispatcher | OPTIONS tại route được khai báo | Không tạo endpoint nghiệp vụ. Mặc định cùng nguồn; chỉ hỗ trợ preflight nếu chính sách CORS được phê duyệt, không mở wildcard. | T |

### 2.2. Nhóm `/api/that/...`

**Chưa chốt module chủ.** `V` chỉ là tên giữ chỗ cho bảng thiết kế. Không đăng ký nguyên một module tên `that`, không đưa các nghiệp vụ định khoản/tri thức/báo cáo vào Core chỉ vì đang nằm trong `Operations`. Trạng thái chưa chốt đã được KS-C ghi tại `docs/47-core/g0/KS-C.md:199`, `docs/47-core/g0/KS-C.md:220`.

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/that/job?id=...` | `server.py:1023` | Core Job Worker; module tạo việc giữ nghiệp vụ | GET `P/viec/{id}` | ID cũ ánh xạ việc Core; Q, H, J. | T |
| GET `/api/that/{knowledge,knowledge-cards}` | `server.py:1025`, `server.py:1042` | Module tri thức, mã chờ chốt | GET `V/{tri_thuc,the_tri_thuc}` | Q, H; phân trang và lọc theo phạm vi được phép. | T* |
| GET `/api/that/catalog` | `server.py:1028` | Module sử dụng danh mục; Core cung cấp dữ liệu chung | GET `V/danh_muc` | Giữ ý nghĩa thời điểm/ngày chốt; lấy dữ liệu chung qua dịch vụ được cấp quyền, theo phiếu CSDL. | T* |
| GET `/api/that/source-settings` | `server.py:1030` | Module quản lý nguồn, mã chờ chốt | GET `V/cau_hinh_nguon` | Q, H; chỉ trả cấu hình an toàn theo quyền, không trả bí mật. | T* |
| GET `/api/that/{overview,runs,history,cfo-rules,invoice-months,report,proposals,quick}` | `server.py:1032`, `server.py:1034`, `server.py:1036`, `server.py:1038`, `server.py:1040`, `server.py:1044`, `server.py:1046`, `server.py:1055` | Các module nghiệp vụ tương ứng, chờ chốt | GET `V/{tong_quan,lan_chay,lich_su,quy_tac_cfo,thang_hoa_don,bao_cao,de_xuat,dinh_khoan_nhanh}` | Q, H; giữ bộ lọc nghiệp vụ qua schema tường minh; không dùng mặc định phiên chung. | T* |
| GET `/api/that/quick/{run}/download`, `/api/that/outside-catalog/download`, `/api/that/shadow/{id}/{direction}/download` | `server.py:1048`, `server.py:1057`, `server.py:1138` | Core File Store và module tạo kết quả | GET `P/ket_qua/{id}/noi_dung` | F; ánh xạ đầy đủ run/tệp/hướng/biến thể sang kết quả được cấp quyền; không biến chuỗi tên tệp thành quyền tải. | T |
| POST `/api/that/source` | `server.py:1150` | Module quản lý nguồn, mã chờ chốt | POST `P/tep`; POST `V/nguon` | F, Q, G; tách nhận bytes và đăng ký nguồn. | T* |
| POST `/api/that/knowledge/import` | `server.py:1204` | Module tri thức, mã chờ chốt | POST `P/tep`; POST `V/tri_thuc/nhap` | F, Q, G; actor lấy từ phiên, không lấy metadata client; J nếu nhập dài. | T* |
| POST `/api/that/quick/{upload,invoice-month,repropose}` | `server.py:1156`, `server.py:1162`, `server.py:1166` | Module định khoản, mã chờ chốt | POST `V/dinh_khoan_nhanh/{nhan_tep,hoa_don_thang,de_xuat_lai}` | Upload dùng `tep_id`; cả ba lệnh áp dụng J thay 201/202 không thống nhất và hàng đợi RAM. | T* |
| POST `/api/that/{reload,ingest,session/run,shadow/export}` | `server.py:1185`, `server.py:1208`, `server.py:1214`, `server.py:1220` | Module nghiệp vụ tương ứng, chờ chốt | POST `V/{nap_lai_nguon,nap_nguon,phien_nghiep_vu/chay,doi_chieu/xuat}` | Q, G, J; xác định rõ phiên nghiệp vụ thuộc pháp nhân/người có quyền. | T* |
| POST `/api/that/quick/{decide,ai-note,ai-context,score,export}` | `server.py:1170`, `server.py:1173`, `server.py:1176`, `server.py:1179`, `server.py:1182` | Module định khoản, mã chờ chốt | POST `V/dinh_khoan_nhanh/{quyet_dinh,ghi_chu_ai,ngu_canh_ai,cham_diem,xuat}` | Q, G; giữ phân biệt ghi chú, tính toán và quyết định duyệt. Nhánh xử lý dài dùng J; AI qua cổng chung; xuất trả tham chiếu kết quả. | T* |
| POST `/api/that/{learning-settings,cfo-rules/toggle,cash-mapping,source-settings,knowledge/decide,proposals/decide}` | `server.py:1188`, `server.py:1190`, `server.py:1193`, `server.py:1201`, `server.py:1211`, `server.py:1217` | Module nghiệp vụ tương ứng, chờ chốt | POST `V/{cau_hinh_hoc,quy_tac_cfo/bat_tat,anh_xa_tien,cau_hinh_nguon,tri_thuc/quyet_dinh,de_xuat/quyet_dinh}` | Q, G; quyền cấu hình khác quyền duyệt; thời điểm audit do server ghi, ngày hiệu lực nghiệp vụ vẫn kiểm theo schema. | T* |
| POST `/api/that/open` | `server.py:1196` | Module tạo kết quả và Core File Store | Không giữ hành vi mở thư mục; dùng GET `P/ket_qua/{id}/noi_dung` để tải kết quả | Trình duyệt tải kết quả được phép; không ra lệnh mở thư mục trên máy chủ. | B |

### 2.3. Bridge nghiệm thu cũ

Bridge hiện tại chỉ phục vụ DEMO và có actor cố định; GET danh sách gọi đồng bộ ghi dữ liệu. Căn cứ: `server.py:123`, `server.py:129`, `server.py:137`.

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/nghiem-thu` | `server.py:1128`, `server.py:137` | M4 | GET `M4/nghiem_thu`; thao tác đồng bộ tách thành POST `M4/nghiem_thu/dong_bo` | GET chỉ đọc nghiệp vụ. Lệnh đồng bộ có Q, G và J nếu dài; bỏ actor cố định. | D; không giữ tác dụng ghi của GET |
| GET `/api/nghiem-thu/sample` | `server.py:1131`, `server.py:143` | Bộ kiểm chứng M4 | Không có đích production | Chỉ mẫu giả. | D |
| GET `/api/nghiem-thu/file-soat/{id}` | `server.py:1134`, `server.py:187` | M4 và Core File Store | GET `P/ket_qua/{id}/noi_dung` | F, Q; ánh xạ hồ sơ và kết quả từ bridge. | D |
| POST `/api/nghiem-thu/{nhan,mau,xac-nhan,quyet-dinh,xuat}` | `server.py:1262`, `server.py:1267` | M4 | Với nghiệp vụ được chuyển: POST `M4/nghiem_thu/{nhan,xac_nhan,quyet_dinh,xuat}`; `mau` không có đích production | Q, G, F; J cho xử lý dài. Chuyển logic có giá trị, không coi bridge DEMO là API production đã có. | D |

### 2.4. CRM và khung module

Tiền tố cũ `c = /api/crm`.

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `c` | `server.py:1060` | CRM | GET `C/trang_thai` | Q, H; GET không tự tạo danh tính DEMO. | T |
| GET `c/file-soat/{id}` | `server.py:1074` | CRM và Core File Store | GET `P/ket_qua/{id}/noi_dung` | F; giữ kiểm quyền CRM hiện có trước khi trả nội dung. | T |
| POST `c/danh-tinh` | `server.py:340` | Bộ kiểm chứng CRM | Không có đích production; phiên thật dùng `P/phien`, GET `P/toi` | Bỏ đổi vai bằng tên đăng nhập tự khai. | D |
| POST `c/{mau,m1-sao-ke}` | `server.py:345`, `server.py:369`, `server.py:379` | Bộ kiểm chứng CRM/M1 | Không có đích production | Giữ fixture tại môi trường thử; không thay bằng đường nhập sao kê thật trong lát này. | D |
| POST `c/{bo-sung,trich-lai/doi-chieu,trich-lai/xu-ly,xac-nhan-tham-so,kiem,duyet,duyet-v4,tu-choi,mapping,lien-ket,go-lien-ket,file-soat}` | `server.py:336` | CRM | POST `C/{bo_sung,trich_lai/doi_chieu,trich_lai/xu_ly,xac_nhan_tham_so,kiem,duyet,duyet_v4,tu_choi,anh_xa,lien_ket,go_lien_ket,file_soat}` | Q, H, G; giữ quy tắc duyệt/liên kết. `trich_lai/doi_chieu` vẫn là thao tác tính/đọc; tạo file soát trả kết quả Core, J nếu dài. | T |
| POST `c/nhan`; POST `c/trich6` | `server.py:1232`, `server.py:1223`, `server.py:494`, `server.py:514` | CRM; engine trích xuất là bên thực thi | POST `C/nhan`; POST `C/trich_tham_so` | F, Q, G; trích xuất dùng J và Adapter `e_trich_xuat`, không giữ HTTP chờ toàn bộ xử lý. | T |
| GET `c/hop-dong` | `crm_g.py:480` | CRM | GET `C/hop_dong` | Q, H; giữ bộ lọc và phân trang S1, chuẩn hóa envelope. | T |
| GET `c/mau`, `c/mau/{id}`, `c/mau/so-sanh`, `c/bo-chuan` | `crm_g.py:493`, `crm_g.py:512`, `crm_g.py:500`, `crm_g.py:600` | CRM | GET `C/mau`, `C/mau/{id}`, `C/mau/so_sanh`, `C/bo_chuan` | Q, H; giữ phiên bản mẫu và ngữ nghĩa thời điểm. Đây là mẫu hợp đồng nghiệp vụ, khác POST `c/mau` nhận fixture. | T |
| GET `c/mau/tep/{id}` | `crm_g.py:505` | CRM và Core File Store | GET `P/tep/{id}/noi_dung` | F; không làm yếu kiểm quyền trước khi tra tệp hiện có. | T |
| POST `c/mau/tai`; `c/mau/{anh-xa,gui-kiem,kiem,tra-lai,duyet,tu-choi,xem-thu}`; `c/bo-chuan/{lap,gui-duyet,duyet}` | `crm_g.py:608`, `crm_g.py:444`, `crm_g.py:60` | CRM | POST `C/mau/tai`; `C/mau/{anh_xa,gui_kiem,kiem,tra_lai,duyet,tu_choi,xem_thu}`; `C/bo_chuan/{lap,gui_duyet,duyet}` | F cho tải mẫu; Q, G; giữ token graph/revision của quy trình mẫu; `xem_thu` không trở thành duyệt. | T |
| GET `c/bao-gia`, `c/bao-gia/{id}`, `c/bao-gia/{mac-dinh,moc-chuan,ty-gia-mac-dinh}`, `c/soan/{id}` | `crm_g.py:518`, `crm_g.py:536`, `crm_g.py:546` | CRM | GET `C/bao_gia`, `C/bao_gia/{id}`, `C/bao_gia/{mac_dinh,moc_chuan,ty_gia_mac_dinh}`, `C/soan/{id}` | Q, H; giữ quy tắc thuế, tỷ giá, mốc và căn cứ nghiệp vụ đã chốt. | T |
| POST `c/bao-gia/{luu,huy,chuyen,xem-truoc,ty-gia-mac-dinh,in}`, `c/soan/{luu,xuat}` | `crm_g.py:388`, `crm_g.py:406`, `crm_g.py:74` | CRM | POST `C/bao_gia/{luu,huy,chuyen,xem_truoc,ty_gia_mac_dinh,in}`, `C/soan/{luu,xuat}` | Q, G; giữ CAS đặc thù; `in/xuat` dùng J và trả kết quả Core; xem trước không tự ghi quyết định. | T |
| GET `c/giao-ket/tep/{id}/{docx,pdf}`, `c/giao-ket/ban-ky/{id}/tep` | `crm_g.py:551`, `crm_g.py:565` | CRM và Core File Store | GET `P/ket_qua/{id}/noi_dung` hoặc `P/tep/{id}/noi_dung` theo loại đã đăng ký | F; định dạng và bản ký là biến thể được kiểm quyền, không suy ra từ tên tệp. | T |
| GET `c/giao-ket/ky/{id}`; POST `c/giao-ket/ky-ket` | `crm_g.py:559`, `crm_g.py:346`, `crm_g.py:631` | CRM | GET `C/giao_ket/ky/{id}`; POST `C/giao_ket/ky_ket` | Q, G; lệnh ký kết dùng J; giữ điều kiện và lịch sử ký kết. | T |
| GET `c/giao-ket/kiem`, `c/giao-ket/kiem/{id}` | `crm_g.py:574`, `crm_g.py:579` | CRM | GET `C/giao_ket/kiem`, `C/giao_ket/kiem/{id}` | Q, H; giữ audit nghiệp vụ. | T |
| GET `c/giao-ket/kiem/{id}/tep/{ban-ky,g3}` | `crm_g.py:585` | CRM và Core File Store | GET `P/tep/{id}/noi_dung` hoặc `P/ket_qua/{id}/noi_dung` | F; ánh xạ rõ hồ sơ, bản ký và bản G3. | T |
| POST `c/giao-ket/kiem/{luu,check,xu-ly-lech,bo-sung,hieu-luc,tra-lai,tim-junsky}` | `crm_g.py:317`, `crm_g.py:659`, `crm_g.py:103` | CRM | POST `C/giao_ket/kiem/{luu,kiem_tra,xu_ly_lech,bo_sung,hieu_luc,tra_lai,tim_junsky}` | Q, G; giữ tra cứu khác với nhập/duyệt; lệnh có IO dài dùng J. | T |
| GET `c/giao-ket/doi-chieu/{id}`; POST `c/giao-ket/doi-chieu/{chay,doi-soat,xac-nhan-tay}` | `crm_g.py:594`, `crm_g.py:308`, `crm_g.py:636`, `crm_g.py:646` | CRM | GET `C/giao_ket/doi_chieu/{id}`; POST `C/giao_ket/doi_chieu/{chay,doi_soat,xac_nhan_tay}` | Giữ hàng việc G5 bền và CAS; `chay/doi_soat` đổi ACK 200 thành J; xác nhận tay giữ điều kiện riêng. | T |
| GET `c/du-an-ban`, `c/du-an-ban/anh-chup`, `c/du-an-ban/{id}`, `c/du-an-ban/{id}/lich-su`, `c/du-an-ban/moc`, `c/du-an-ban/moc/{id}/lich-su` | `crm_g.py:786` | CRM | GET `C/du_an_ban`, `C/du_an_ban/anh_chup`, `C/du_an_ban/{id}`, `C/du_an_ban/{id}/lich_su`, `C/du_an_ban/moc`, `C/du_an_ban/moc/{id}/lich_su` | Q, H; giữ ảnh chụp, lịch sử và bộ lọc mốc. | T |
| POST `c/du-an-ban/{bat-ban,cap-nhat,phi,lo,moc,ngung-ban,mo-ban-lai,tien-do}` | `crm_g.py:757`, `crm_g.py:706` | CRM | POST `C/du_an_ban/{bat_ban,cap_nhat,phi,lo,moc,ngung_ban,mo_ban_lai,tien_do}` | Q, G; giữ căn cứ/version nghiệp vụ từng lệnh. | T |
| GET `/api/khung/module/crm` | `khung_khai_bao.py:170`, `khung_khai_bao.py:103` | Core Shell và CRM | GET `P/module/crm` | Metadata khung và khả năng truy cập lấy từ backend; module cung cấp đếm/drill-down theo quyền. | T |
| GET `c/{bao-gia,mau}?trang_thai=...` | `crm_g.py:475`, `khung_khai_bao.py:183` | CRM | GET `C/{bao_gia,mau}?trang_thai=...` | Hợp nhất contract danh sách có bộ lọc; giữ cách kiểm giá trị rỗng/lặp và phạm vi quyền. | T |

### 2.5. MTQ và công tắc module

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/tham-quyen/{ma-tran,nhat-ky}` | `ma_tran_tham_quyen.py:16`, `ma_tran_tham_quyen.py:42` | Core Identity/Access | GET `P/quan_tri/cap_quyen/{ma_tran,nhat_ky}` | Q, H; quyền quản trị và pháp nhân vẫn kiểm tại backend. | T |
| GET `/api/tham-quyen/cua-toi` | `ma_tran_tham_quyen.py:16`, `ma_tran_tham_quyen.py:42` | Core Identity/Access | GET `P/toi/tham_quyen` | Chỉ quyền của người được xác thực; không cho truyền danh tính khác để thay ngữ cảnh. | T |
| POST `/api/tham-quyen/{luu-nhap,cong-bo,kich-hoat,phong,gan-vai,pham-vi,admin}` | `ma_tran_tham_quyen.py:16`, `ma_tran_tham_quyen.py:42` | Core Identity/Access | POST `P/quan_tri/cap_quyen/{luu_nhap,cong_bo,kich_hoat,phong,gan_vai,pham_vi,admin}` | Q, G; giữ vòng đời bản nháp/công bố/kích hoạt và revision MTQ. | T |
| GET `/api/cong-tac-module/{trang-thai,nguoi-thu}` | `module_cong_tac.py:12`, `module_cong_tac.py:73` | Core Module Manager | GET `P/quan_tri/module/{ma}/cong_tac/{trang_thai,nguoi_thu}` | Mã module chuyển thành path parameter, đối chiếu với payload cũ; Q, H. | T |
| POST `/api/cong-tac-module/{che-do,nguoi-thu/cap,nguoi-thu/thu-hoi}` | `module_cong_tac.py:12`, `module_cong_tac.py:65`, `module_cong_tac.py:73` | Core Module Manager | POST `P/quan_tri/module/{ma}/cong_tac/{che_do,nguoi_thu/cap,nguoi_thu/thu_hoi}` | Giữ revision, pháp nhân, audit và chế độ TAT/THU/VAN_HANH. Công tắc nghiệp vụ khác vòng đời tiến trình. | T |

### 2.6. M4 và Request nháp

Tiền tố cũ `x = /api/m4`.

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `x`; `x/{hop-dong,dot}/{id}`; `x/mau`, `x/mau/{ma}` | `m4.py:502`, `m4.py:507`, `m4.py:520` | M4 | GET `M4/trang_thai`; `M4/{hop_dong,dot}/{id}`; `M4/mau`, `M4/mau/{ma}` | Q, H; root không tự cấp phiên DEMO. Mẫu trả metadata; nội dung tệp theo F. | T |
| GET `x/tep/{id}` | `m4.py:507` | M4 và Core File Store | GET `P/tep/{id}/noi_dung` | F; giữ kiểm quyền dự án/hồ sơ M4. | T |
| GET `x/{master-hop-dong,master-doi-tac}` | `m4.py:457` | M4 tiêu thụ danh mục chung | GET `M4/danh_muc/{hop_dong,doi_tac}` | Q, H; lấy dữ liệu qua dịch vụ/contract được cấp, theo phiếu CSDL. | T |
| GET `x/{review,chung-tu}`, `x/{review,chung-tu}/{id}` | `m4.py:465`, `m4.py:481` | M4 | GET `M4/{soat_xet,chung_tu}`, `M4/{soat_xet,chung_tu}/{id}` | Q, H; danh sách/chi tiết nghiệp vụ khác trạng thái việc Core. | T |
| GET `x/{review,chung-tu}/{id}/tep/{tep_id}` | `m4.py:465`, `m4.py:481` | M4 và Core File Store | GET `P/tep/{id}/noi_dung` hoặc `P/ket_qua/{id}/noi_dung` | F; kiểm quan hệ tệp với hồ sơ trước tải. | T |
| GET `x/duyet`, `x/ke-toan`, `x/ke-toan/{id}` | `m4.py:425`, `m4.py:442` | M4 | GET `M4/duyet`, `M4/ke_toan`, `M4/ke_toan/{id}` | Q, H; giữ phạm vi người duyệt/kế toán. | T |
| GET `x/duyet/{id}/pdf/{pdf_id}`, `x/ke-toan/{id}/phong-bi/{id}/pdf` | `m4.py:425`, `m4.py:442` | M4 và Core File Store | GET `P/ket_qua/{id}/noi_dung` | F; alias phải giữ đủ các ID hồ sơ/phong bì/tệp, không nhập nhằng hai `{id}` cũ. | T |
| GET `x/doi-chieu/{dot,lich-su,con-thieu}/{id}` | `m4.py:391` | M4 | GET `M4/doi_chieu/{dot,lich_su,con_thieu}/{id}` | Q, H; giữ căn cứ và lịch sử đối chiếu. | T |
| POST `x/tep`, `x/duyet/pdf` | `m4.py:547`, `m4.py:564` | Core File Store và M4 | POST `P/tep`; POST `M4/duyet/pdf` với `tep_id` | F, Q, G; xử lý PDF dài dùng J; nhận bytes không tự duyệt hồ sơ. | T |
| POST `x/danh-tinh` | `m4.py:596` | Bộ kiểm chứng M4 | Không có đích production | Dùng phiên Core; không đổi vai bằng payload DEMO. | D |
| POST `x/hop-dong/{tao,nhan-master,gan-doi-tac,gan-tep,trich}`; `x/tham-so/{sua,xac-nhan}`; `x/phu-luc/{khai,them,huy}`; `x/boq/{xem,nhap}`; `x/dot/{tao,sua,gan-tep,nop}` | `m4.py:205`, `m4.py:20` | M4 | POST `M4/hop_dong/{tao,nhan_danh_muc,gan_doi_tac,gan_tep,trich}`; `M4/tham_so/{sua,xac_nhan}`; `M4/phu_luc/{khai,them,huy}`; `M4/boq/{xem,nhap}`; `M4/dot/{tao,sua,gan_tep,nop}` | Q, G, F; `hop_dong/trich` dùng J. `boq/xem` giữ tính xem trước. | T |
| POST `x/review/{chay,chay-lai,ghep}`; `x/chung-tu/{chay,chay-lai,sua,ghep}`; `x/duyet/{ket-luan,chap-thuan,phien-ban,phien-ban/nop}` | `m4.py:245`, `m4.py:316`, `m4.py:588` | M4 | POST `M4/soat_xet/{chay,chay_lai,ghep}`; `M4/chung_tu/{chay,chay_lai,sua,ghep}`; `M4/duyet/{ket_luan,chap_thuan,phien_ban,phien_ban/nop}` | Q, G; chạy/chạy lại và xử lý dài dùng J; sửa/ghép/duyệt giữ CAS, không tự duyệt từ kết quả engine. | T |
| POST `x/ke-toan/{luu,xac-nhan}`, `x/doi-chieu/{xem,luu,xac-nhan}` | `m4.py:532`, `m4.py:574` | M4 | POST `M4/ke_toan/{luu,xac_nhan}`, `M4/doi_chieu/{xem,luu,xac_nhan}` | Q, G; giữ token căn cứ và phân biệt xem/ghi/xác nhận. | T |
| GET `/api/m4-request`; POST `/api/m4-request/{tao,doi-soat}` | `m4_request.py:206`, `m4_request.py:237` | M4 | GET `M4/yeu_cau_nhap`; POST `M4/yeu_cau_nhap/{tao,doi_soat}` | Q, G, J cho IO dài; giữ kiểm lại phiên/quyền sau IO và trạng thái chưa cấu hình/tắt. | T |
| GET `/m4.js`, `/m4.css`, `/m4/{review.js,chung-tu.js,m4_duyet_pdf.js,m4_ke_toan.js,m4_request_nhap.js}`, `/m4/fonts/{ten}` | `m4.py:403`, `m4.py:497` | Core Shell và gói giao diện M4 | Tài sản giao diện do Core phục vụ | Giữ allowlist; không biến đường dẫn asset thành API nghiệp vụ. | S |

### 2.7. M2, M5/L11 và M9

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/m2`; `/api/m2/{hoa-don,nguon}/{id}` | `server.py:1115`, `server.py:771` | M2 | GET `M2/trang_thai`; `M2/{hoa_don,nguon}/{id}` | Q, H; bỏ cấp danh tính DEMO ngầm khi đọc root. | T |
| GET `/api/m2/nguon/{id}/raw/{vai_tro}` | `server.py:839` | M2 và Core File Store | GET `P/tep/{id}/noi_dung` hoặc `P/ket_qua/{id}/noi_dung` | F; giữ kiểm quyền nguồn và vai trò biến thể; ID được ánh xạ. | T |
| POST `/api/m2/danh-tinh` | `server.py:789` | Bộ kiểm chứng M2 | Không có đích production | Phiên thật do Core quản lý. | D |
| POST `/api/m2/{nhan,mapping,mapping-line,nguon/kiem-lai,route}` | `server.py:784`, `server.py:817`, `server.py:821`, `server.py:827`, `server.py:831` | M2 | POST `M2/{nhan,anh_xa,anh_xa_dong,nguon/kiem_lai,dinh_tuyen}` | Q, G, F; giữ `expected_graph`, căn cứ dòng, tuyến và revision. Nhánh nhận fixture chỉ DEMO. | T |
| POST `/api/m2/lien-ket/{...}` | `server.py:835`, `server.py:1292` | M2 | Chưa đăng ký route v1 tương ứng | KS-C ghi chưa phát hành/501; không suy ra tập operation hoặc công bố chức năng đã có. | B; chờ đặc tả nghiệp vụ |
| GET `/api/m5`; `/api/m5/{phieu,nguon}/{id}`; `/api/m5/{kiem-ke,ton-nguon}` | `server.py:1089`, `server.py:598` | M5 | GET `M5/trang_thai`; `M5/{phieu,nguon}/{id}`; `M5/{kiem_ke,ton_nguon}` | Q, H; giữ phân trang và quyền dữ liệu nguồn. | T |
| GET `/api/m5/nguon/{id}/raw/{vai_tro}`, `/api/m5/file-soat/{id}` | `server.py:723`, `server.py:598` | M5 và Core File Store | GET `P/tep/{id}/noi_dung`, `P/ket_qua/{id}/noi_dung` tương ứng | F; giữ kiểm quyền nguồn/hồ sơ và token căn cứ nếu áp dụng. | T |
| POST `/api/m5/danh-tinh`; `/api/m5/l11/danh-tinh` | `server.py:620`, `server.py:664` | Bộ kiểm chứng M5/L11 | Không có đích production | Không biến bộ chọn vai DEMO thành đăng nhập thật. | D |
| POST `/api/m5/{nhan,mapping,nguon/kiem-lai,xuat-file-soat}` | `server.py:615` | M5 | POST `M5/{nhan,anh_xa,nguon/kiem_lai,xuat_file_soat}` | Q, G, F; giữ bộ con trỏ và token basis của xuất file soát; nhận fixture chỉ DEMO; J nếu xuất dài. | T |
| GET `/api/m5/l11`, `/api/m5/l11/proof`; POST `/api/m5/l11/{proof/nhan,proof/xac-nhan,proof/huy,ma-hoa,file-soat}` | `server.py:1094`, `server.py:664`, `server.py:718` | M5/L11 | GET `M5/l11`, `M5/l11/bang_chung`; POST `M5/l11/{bang_chung/nhan,bang_chung/xac_nhan,bang_chung/huy,ma_hoa,file_soat}` | Q, G, F; giữ điều kiện BOTH, phạm vi hai phía và quyền hồ sơ L11; không thay bằng kiểm một module. | T |
| POST `/api/m5/lien-ket/{preview,xac-nhan,huy}` | `server.py:657`, `k2/kho_so_luong.py:906` | M5/L11 | POST `M5/lien_ket/{xem_truoc,xac_nhan,huy}` | Giữ preview không ghi, token preview/căn cứ và biên nhận bền; Q, G. | T |
| GET `/api/m9`, `/api/m9/file-soat/{id}` | `server.py:1079`, `server.py:486` | M9 và Core File Store | GET `M9/trang_thai`; GET `P/ket_qua/{id}/noi_dung` | Q, H, F; root không tự cấp danh tính DEMO. | T |
| POST `/api/m9/danh-tinh` | `server.py:443` | Bộ kiểm chứng M9 | Không có đích production | Phiên do Core quản lý. | D |
| POST `/api/m9/{mau,m1-sao-ke}` | `server.py:448`, `server.py:458`, `server.py:469` | Bộ kiểm chứng M9/M1 | Không có đích production cho nhánh nhận mẫu | Giữ luồng kiểm chứng riêng; không tự thiết kế lại nhập sao kê thật. | D |
| POST `/api/m9/{anh-xa,anh-xa/anh-huong,anh-xa/dong,lap,pham-vi,kiem,duyet,duyet-v4,tu-choi,goi-y,xem-truoc,xac-nhan,go,file-soat}` | `server.py:438` | M9 | POST `M9/{anh_xa,anh_xa/anh_huong,anh_xa/dong,lap,pham_vi,kiem,duyet,duyet_v4,tu_choi,goi_y,xem_truoc,xac_nhan,go,file_soat}` | Q, G; giữ phân biệt gợi ý/xem trước với xác nhận; file soát trả tham chiếu kết quả, J nếu dài. | T |

### 2.8. Bộ tải hóa đơn M2

Tiền tố cũ `t = /api/m2/tai-hoa-don`. M2 giữ nghiệp vụ; quản lý tiến trình bộ tải thuộc Core/Engine Manager.

| Route cũ | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `t`, `t/trang-thai` | `m2_tai_hoa_don.py:1048` | M2 | GET `T/trang_thai` | Q, H; tách trạng thái nghiệp vụ khỏi trạng thái tiến trình engine. | T |
| GET `t/hang-doi` | `m2_tai_hoa_don.py:1048`, `m2_tai_hoa_don.py:213` | Core Job Worker và M2 | GET `P/viec?ma_module=m2` với bộ lọc nghiệp vụ tương ứng | Hàng đợi dùng việc bền; người dùng chỉ xem phạm vi được cấp. Không suy rằng mọi binding hiện có đều ở RAM. | T |
| GET `t/su-kien` | `m2_tai_hoa_don.py:1048` | Core Job Worker và M2 | GET `P/viec/{id}/su_kien` | Giữ SSE; xác thực lại khi nối lại, cursor và chính sách mất đoạn theo thân API; không chuyển tiếp stream toàn cục không lọc. | T |
| GET `t/{manifest,hoa-don}` | `m2_tai_hoa_don.py:1048` | M2 | GET `T/{manifest,hoa_don}` | Q, H; giữ binding run/manifest và quyền nguồn. | T |
| POST `t/{khoi-dong,khoi-dong-lai}` | `m2_tai_hoa_don.py:1069`, `m2_tai_hoa_don.py:874` | Core Engine Manager | POST `P/quan_tri/engine/e_hoa_don/{khoi_dong,khoi_dong_lai}` | Chỉ quản trị; người dùng bắt đầu nghiệp vụ thì Core tự kích hoạt engine. Khởi động lại phải xét việc đang chạy. | T |
| POST `t/{bat-dau,tai-tat-ca}` | `m2_tai_hoa_don.py:1069`, `m2_tai_hoa_don.py:1076` | M2; `e_hoa_don` thực thi | POST `T/{bat_dau,tai_tat_ca}` | Q, G, J; giữ mapping nguồn/pháp nhân và bước người dùng đăng nhập/CAPTCHA. | T |
| POST `t/huy-hang-doi` | `m2_tai_hoa_don.py:1069` | Core Job Worker và M2 | POST `T/hang_doi/huy`; mỗi việc được yêu cầu hủy theo contract `P/viec/{id}/huy` | Chụp rõ tập việc thuộc phạm vi yêu cầu; trả trạng thái từng việc, không báo đã hủy ngay toàn bộ. | T |
| POST `t/{nhan,doi-soat}` | `m2_tai_hoa_don.py:1069` | M2 | POST `T/{nhan,doi_soat}` | Q, G, J nếu dài; giữ kiểm lại quyền quanh IO và biên nhận nhập. | T |
| POST `t/mo-thu-muc` | `m2_tai_hoa_don.py:1069` | M2 và Core File Store | Không giữ hành vi mở thư mục; dùng metadata/tải kết quả qua `P/ket_qua` | Không mở thư mục máy chủ từ trình duyệt người dùng. | B |

### 2.9. Engine #6 do ứng dụng sở hữu

Đây là **protocol dịch vụ nội bộ**, không phải phiên người dùng. Cổng và token hiện có không thay kiểm quyền của consumer; nguồn handler nghiệp vụ kế thừa còn nằm ngoài phạm vi mã khảo sát. Căn cứ: `docs/47-core/g0/KS-C.md:125`, `docs/47-core/g0/KS-C.md:128`.

| Route cũ | Tệp:dòng | Module chủ | Route mới qua Core | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/trich_xuat/common` trên host #6 | `nguon/trich6_host.py:431`, `nguon/trich6_host.py:498` | Core Adapter và `e_trich_xuat` | GET `P/engine/e_trich_xuat/nang_luc` | Chuẩn hóa capability/version/readiness; không tự công bố loại hợp đồng chưa được nguồn hỗ trợ. | N |
| GET `/api/trich_xuat/{luot}` | `nguon/trich6_host.py:431`, `nguon/trich6_host.py:529` | Core Job Worker và `e_trich_xuat` | GET `P/viec/{id}`; kết quả qua `P/ket_qua/{id}` | Ánh xạ lượt engine với việc/bước/lần thử Core; không dùng lượt engine làm quyền truy cập. | N |
| GET `/tai/{rel}` trên host #6 | `nguon/trich6_host.py:498`, `nguon/trich6_host.py:484` | Adapter và Core File Store | GET `P/ket_qua/{id}/noi_dung` | Giữ kiểm token/allowlist/seal nội bộ; Core kiểm quyền người dùng và nhận kết quả theo F. | N |
| POST `/api/trich_xuat`; POST `/api/trich_xuat/{luot}/{tep,chay}` | `nguon/trich6_host.py:510`, `nguon/trich6_host.py:533` | Core Adapter và `e_trich_xuat` | POST `P/engine/e_trich_xuat/viec`, hoặc lệnh nghiệp vụ CRM/M4/M2 đã khai báo | Một việc Core điều phối chuỗi tạo lượt → gửi tệp → chạy nội bộ; Q, G, J. Không tạo thêm việc khi Adapter retry từng bước. | N |
| POST `/api/trich_xuat/{luot}/dung` | `nguon/trich6_host.py:533` | Core Job Worker và Adapter | POST `P/viec/{id}/huy` | Gửi đề nghị dừng tới đúng lượt/lần thử; chờ trạng thái xác nhận. | N |

### 2.10. Server Review cũ — quản trị, cấu hình, việc và tài sản

Server này tồn tại riêng, không nằm trong nhánh chuyển tiếp shell. Không tự thêm alias các route chung như `/api/cai_dat` vào Core vì có thể trùng với server khác. Căn cứ: `docs/47-core/g0/KS-C.md:132`.

| Route cũ trên server Review | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/phien_ban`, `/api/he_thong` | `m4/review_goc/may_chu/server.py:53`, `m4/review_goc/may_chu/server.py:58` | Core Module Manager và M4 | GET `P/quan_tri/module/m4/phien_ban`, `P/quan_tri/module/m4/trang_thai` | Tách phiên bản/trạng thái module khỏi năng lực engine; lọc chi tiết hệ thống theo quyền quản trị. | T* |
| GET `/api/tong_quan` | `m4/review_goc/may_chu/server.py:63` | M4 | GET `M4/tong_quan` | Q, H; chỉ dữ liệu pháp nhân/hồ sơ được phép. | T* |
| GET `/api/ai`, `/api/ocr/trang_thai` | `m4/review_goc/may_chu/server.py:68`, `m4/review_goc/may_chu/server.py:109` | Core Engine Manager và cổng AI/OCR | GET `P/quan_tri/engine` với bộ lọc đã khai báo; GET `P/quan_tri/engine/e_ocr/trang_thai` | Trạng thái AI lấy từ hồ sơ đã đăng ký qua cổng AI chung; không tạo thêm cổng AI. Không gọi phép thử ghi tệp như health check thông thường. | T* |
| GET `/api/cai_dat`; POST `/api/cai_dat` | `m4/review_goc/may_chu/server.py:74`, `m4/review_goc/may_chu/server.py:79` | Core Engine Manager và quản trị M4 | GET/PATCH `P/quan_tri/engine/{ma}/cau_hinh`; phần cấu hình nghiệp vụ về M4 | Phân loại từng trường theo chủ sở hữu; không chuyển nguyên cấu hình gồm đường dẫn/khóa sang client. Q, G. | T* |
| POST `/api/cai_dat/{kiem_tra_ai,thu_cloud,tim_may_ai}` | `m4/review_goc/may_chu/server.py:84`, `m4/review_goc/may_chu/server.py:89`, `m4/review_goc/may_chu/server.py:94` | Core quản trị và cổng AI | POST `P/quan_tri/engine/{ma}/kiem_tra`; POST `P/quan_tri/engine/kham_pha` cho thao tác dò đã cấu hình | Chỉ quản trị, J nếu dài. Cloud qua cổng AI và Mask v2; không nhận URL/chương trình tùy ý từ client. | T* |
| POST `/api/cai_dat/khoa`; DELETE `/api/cai_dat/khoa/{anthropic,openai}` | `m4/review_goc/may_chu/server.py:99`, `m4/review_goc/may_chu/server.py:104` | Quản trị bí mật của Core/cổng AI | Không có alias trực tiếp | Bỏ API quản lý khóa riêng của Review khỏi bề mặt nghiệp vụ; dùng cơ chế cấu hình bí mật tập trung được thân API/SDK quy định. | B |
| GET `/api/cai_dat/nhat_ky_gui_ngoai` | `m4/review_goc/may_chu/server.py:189` | Core Audit và cổng AI | GET `P/quan_tri/engine/{ma}/nhat_ky_gui_ngoai` | Chỉ metadata an toàn, có phân quyền và phân trang; không trả khóa hoặc mặc định toàn văn gửi đi. | T* |
| GET `/api/tham_so`; PUT `/api/tham_so` | `m4/review_goc/may_chu/server.py:200`, `m4/review_goc/may_chu/server.py:205` | M4 | GET/PUT `M4/tham_so` | Giữ tham số nghiệp vụ tại M4; Q, G. Không nhập chung với cấu hình engine. | T* |
| POST `/api/ocr/chay_thu` | `m4/review_goc/may_chu/server.py:184` | Core Engine Manager và `e_ocr` | POST `P/quan_tri/engine/e_ocr/chay_thu` | Q, G, J; dữ liệu thử theo quyền, kết quả qua Core. | T* |
| POST `/api/csdl/sao_luu` | `m4/review_goc/may_chu/server.py:194`, `m4/review_goc/may_chu/dich_vu.py:799` | Core Backup/Restore | POST `P/quan_tri/sao_luu` | Thay sao lưu SQLite riêng bằng chính sách CSDL–kho tệp chung sau chuyển dữ liệu; J; không đồng nhất với xuất nghiệp vụ. | B đối với hành vi SQLite cũ |
| POST `/api/csdl/xuat_excel` | `m4/review_goc/may_chu/server.py:404`, `m4/review_goc/may_chu/dich_vu.py:811` | M4 | POST `M4/xuat_du_lieu/excel` | Q, G, J; xuất dữ liệu đúng phạm vi, trả kết quả Core. | T* |
| GET `/api/viec`, `/api/viec/{id}`; POST `/api/viec/{id}/dung` | `m4/review_goc/may_chu/server.py:211`, `m4/review_goc/may_chu/server.py:216`, `m4/review_goc/may_chu/server.py:224` | Core Job Worker; M4 là chủ nghiệp vụ | GET `P/viec?ma_module=m4`, `P/viec/{id}`; POST `P/viec/{id}/huy` | Ánh xạ ID QLV sang việc Core; Q, J; không dùng hàng RAM Review làm nguồn trạng thái bền duy nhất. | T* |
| POST `/api/tat` | `m4/review_goc/may_chu/server.py:489` | Core Module Manager/Engine Manager | Không giữ alias; dừng module qua POST `P/quan_tri/module/m4/dung` khi có quyền | Drain việc và kiểm danh tính tiến trình; không gọi lại lệnh tắt server Review công khai. | B |
| GET `/tai/{rel}` | `m4/review_goc/may_chu/server.py:512`, `m4/review_goc/may_chu/dich_vu.py:58` | M4 và Core File Store | GET `P/ket_qua/{id}/noi_dung` | F; kiểm quyền hồ sơ/pháp nhân, thay đường dẫn tương đối bằng tham chiếu được đăng ký. | T* |
| GET `/`, `/index.html`, tài sản tĩnh hợp lệ | `m4/review_goc/may_chu/server.py:512` | Core Shell và gói giao diện M4 | Trang/tài sản của module M4 qua Core | Không mở lại server giao diện riêng cho người dùng. | S |

### 2.11. Server Review cũ — nghiệp vụ và trích xuất

Tiền tố cũ trong bảng này vẫn thuộc **server Review**, không phải host #6 ở §2.9.

| Route cũ trên server Review | Tệp:dòng | Module chủ | Route mới | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| GET `/api/phu_luc_ai`, `/api/phu_luc_ai/{id}`; POST `/api/phu_luc_ai/{tai_len,chay}`, `/api/phu_luc_ai/{id}/{cap_nhat,hoi_lai_ai,nap}`; DELETE `/api/phu_luc_ai/{id}` | `m4/review_goc/may_chu/server.py:114`, `m4/review_goc/may_chu/server.py:124`, `m4/review_goc/may_chu/server.py:134`, `m4/review_goc/may_chu/server.py:149` | M4 | Cùng tập method và hậu tố dưới `M4/phu_luc_ai` | F cho tải lên; Q, G; `chay/hoi_lai_ai` dùng J và cổng AI chung. `nap` vẫn là lệnh nghiệp vụ riêng; DELETE theo retention, không mặc định xóa dây chuyền. | T* |
| GET `/api/chung_tu`, `/api/chung_tu/{id}`; POST `/api/chung_tu/{tai_len,chay}`, `/api/chung_tu/{id}/cap_nhat`; DELETE `/api/chung_tu/{id}` | `m4/review_goc/may_chu/server.py:154`, `m4/review_goc/may_chu/server.py:164`, `m4/review_goc/may_chu/server.py:174`, `m4/review_goc/may_chu/server.py:179` | M4 | Cùng tập method và hậu tố dưới `M4/chung_tu` | Hợp nhất vào contract chứng từ M4 ở §2.6; không tạo hai handler cùng method/path. F, Q, G, J cho `chay`. | T* |
| GET `/api/trich_xuat`; POST `/api/trich_xuat`; GET `/api/trich_xuat/{luot}` | `m4/review_goc/may_chu/server.py:233`, `m4/review_goc/may_chu/server.py:238`, `m4/review_goc/may_chu/server.py:243` | M4 quản lý lượt chuẩn bị; engine chỉ thực thi | GET/POST `M4/trich_xuat/luot`; GET `M4/trich_xuat/luot/{id}` | Lượt nghiệp vụ tách khỏi việc engine; Q, G; ID cũ ánh xạ theo nguồn. | T* |
| POST `/api/trich_xuat/{luot}/tep`; DELETE `/api/trich_xuat/{luot}/tep/{ten}`; DELETE `/api/trich_xuat/{luot}` | `m4/review_goc/may_chu/server.py:253`, `m4/review_goc/may_chu/server.py:258`, `m4/review_goc/may_chu/server.py:248` | M4 và Core File Store | POST `P/tep`, sau đó POST `M4/trich_xuat/luot/{id}/tep`; DELETE `M4/trich_xuat/luot/{id}/tep/{tep_id}`; DELETE `M4/trich_xuat/luot/{id}` | F, Q, G; gỡ liên kết tệp khác xóa vật lý. Không dùng tên tệp làm ID. Không xóa lượt đang chạy mà bỏ qua quy trình hủy. | T* |
| POST `/api/trich_xuat/{luot}/{chay,chay_lai}` | `m4/review_goc/may_chu/server.py:263`, `m4/review_goc/may_chu/server.py:268` | M4 điều phối; `e_trich_xuat` thực thi | POST `M4/trich_xuat/luot/{id}/{chay,chay_lai}` | Q, G, J; module gọi capability qua Core/Adapter, giữ snapshot/catalog/version của lượt. | T* |
| POST `/api/trich_xuat/{luot}/dung` | `m4/review_goc/may_chu/server.py:273` | Core Job Worker và M4 | POST `P/viec/{id}/huy` | Ánh xạ đúng việc đang chạy; hủy là đề nghị. | T* |
| POST `/api/trich_xuat/{luot}/danh_muc` | `m4/review_goc/may_chu/server.py:281` | Chủ danh mục trích xuất đã đăng ký; M4 là consumer | POST `M4/trich_xuat/luot/{id}/danh_muc` để chọn/ghim danh mục được phép | Giữ phiên bản/hash danh mục. Không trao quyền sửa catalog engine bằng cách chọn catalog trong lượt; quyền sửa quản lý riêng. | T* |
| GET `/api/trich_xuat/{luot}/hd/{ten}` | `m4/review_goc/may_chu/server.py:286` | M4 | GET `M4/trich_xuat/luot/{id}/hop_dong/{hop_dong_id}` | Ánh xạ tên cũ sang ID; Q, H; kết quả OCR/trích xuất chưa đồng nghĩa hợp đồng đã duyệt. | T* |
| PATCH `/api/trich_xuat/{luot}/hd/{ten}/o/{ma}` | `m4/review_goc/may_chu/server.py:291` | M4 | PATCH `M4/trich_xuat/luot/{id}/hop_dong/{hop_dong_id}/o/{ma}` | Q, G; giữ revision kết quả và dẫn chứng của ô được sửa. | T* |
| POST `/api/trich_xuat/{luot}/hd/{ten}/{xac_nhan,nap_csdl}` | `m4/review_goc/may_chu/server.py:296`, `m4/review_goc/may_chu/server.py:301` | M4 | POST `M4/trich_xuat/luot/{id}/hop_dong/{hop_dong_id}/{xac_nhan,nap}` | Giữ hai bước xác nhận/nạp; kiểm quyền và CAS lại khi ghi. Giữ nhánh chỉ so sánh khi hợp đồng đã tồn tại; không ép thành ghi mới. | T* |
| GET `/api/hop_dong`, `/api/hop_dong/{ref}`, `/api/hop_dong/{ref}/boq`, `/api/hop_dong/{ref}/phu_luc/{so}` | `m4/review_goc/may_chu/server.py:307`, `m4/review_goc/may_chu/server.py:312`, `m4/review_goc/may_chu/server.py:317`, `m4/review_goc/may_chu/server.py:354` | M4 | GET `M4/hop_dong`, `M4/hop_dong/{id}`, `M4/hop_dong/{id}/boq`, `M4/hop_dong/{id}/phu_luc/{so}` | Ánh xạ `ref` Review sang ID M4 theo phiếu CSDL; hợp nhất route chi tiết với §2.6, không giữ hai nguồn sự thật. | T* |
| POST `/api/hop_dong/{ref}/{phieu_phu_luc,kiem_dot}`, `/api/hop_dong/{ref}/phu_luc/{so}/huy`, `/api/hop_dong/{ref}/tham_so/{ma}/xac_nhan` | `m4/review_goc/may_chu/server.py:322`, `m4/review_goc/may_chu/server.py:332`, `m4/review_goc/may_chu/server.py:327`, `m4/review_goc/may_chu/server.py:349` | M4 | POST `M4/hop_dong/{id}/{phieu_phu_luc,kiem_dot}`, `M4/hop_dong/{id}/phu_luc/{so}/huy`, `M4/hop_dong/{id}/tham_so/{ma}/xac_nhan` | Q, G, F; `kiem_dot` dùng J; giữ căn cứ và điều kiện hủy/xác nhận. | T* |
| POST `/api/phu_luc/{kiem_tra,nap}` | `m4/review_goc/may_chu/server.py:339`, `m4/review_goc/may_chu/dich_vu.py:774` | M4 | POST `M4/phu_luc/{kiem_tra,nap}` | Cả hai có thể nhận/lưu tệp; F. Kiểm tra không đồng nghĩa đã nạp nghiệp vụ; Q, G, J nếu dài. | T* |
| POST `/api/toan_ven` | `m4/review_goc/may_chu/server.py:344` | M4 | POST `M4/toan_ven` | Q, G, J; giữ kết quả kiểm như căn cứ chờ xử lý. | T* |
| GET `/api/kiem_tra/{kiem_tra_dot,toan_ven}` và `/api/kiem_tra/{kiem_tra_dot,toan_ven}/{ma}` | `m4/review_goc/may_chu/server.py:359`, `m4/review_goc/may_chu/server.py:364` | M4 | GET `M4/kiem_tra/{kiem_tra_dot,toan_ven}` và `M4/kiem_tra/{kiem_tra_dot,toan_ven}/{id}` | Q, H; danh sách/chi tiết kết quả nghiệp vụ khác trạng thái việc. | T* |
| POST `/api/kiem_tra/kiem_tra_dot/{ma}/{nap,ghep,chay_lai}` | `m4/review_goc/may_chu/server.py:369`, `m4/review_goc/may_chu/server.py:374`, `m4/review_goc/may_chu/server.py:379` | M4 | POST `M4/kiem_tra/kiem_tra_dot/{id}/{nap,ghep,chay_lai}` | Q, G; `chay_lai` dùng J; nạp/ghép phải kiểm revision và căn cứ hiện hành. | T* |
| POST `/api/boq/{tai_len,sheet,kiem_tra,ghi}` | `m4/review_goc/may_chu/server.py:384`, `m4/review_goc/may_chu/server.py:389`, `m4/review_goc/may_chu/server.py:394`, `m4/review_goc/may_chu/server.py:399` | M4; OCR qua engine | POST `M4/boq/{tai_len,trang_tinh,kiem_tra,ghi}` | F, Q, G; nhánh tải có OCR/chuyển đổi dùng J, không giữ xử lý dài trong upload HTTP. `trang_tinh/kiem_tra` không tự ghi BOQ; `ghi` là lệnh riêng. | T* |

Các nhóm Review và M4 có cùng đích phải được ghép thành **một contract chuẩn**, với Adapter chuyển payload cũ theo nguồn. Không đăng ký hai operation cho cùng method/path, không dùng thứ tự handler để chọn ngầm hợp đồng.

### 2.12. Endpoint chỉ thấy từ client trong KS-C

Các endpoint này là địa chỉ engine mà backend đang gọi, **không phải route công khai do shell cung cấp**. Ánh xạ dưới đây mô tả nơi chức năng xuất hiện qua Core; không yêu cầu đổi ngay protocol nguồn.

| Endpoint cũ | Tệp:dòng | Module chủ | Route mới qua Core | Thay đổi hợp đồng | Chuyển tiếp |
|---|---|---|---|---|---|
| Mask GET `/api/v1/trang-thai`; POST `/api/v1/{che,mo-che}` | `tri_thuc/cong_ai.py:635`, `tri_thuc/cong_ai.py:660`, `tri_thuc/cong_ai.py:669`, `tri_thuc/cong_ai.py:683` | Cổng AI chung, Adapter và `e_mask` | GET `P/engine/e_mask/nang_luc`; POST `P/engine/e_mask/viec` với capability được cấp; theo dõi qua `P/viec/{id}` | Route nguồn vốn có `/api/v1/` nhưng khác dịch vụ. Không proxy thẳng cho browser; không đưa Bearer xuống frontend. Giữ kiểm danh mục đã mở, `gui_duoc`, `con_sot`. | N |
| Bộ tải GET `/api/config`; POST `/api/profiles` | `m2/tai_hoa_don/khach.py:95`, `m2/tai_hoa_don/khach.py:101` | Core Engine Manager, Adapter và M2 | GET `P/quan_tri/engine/e_hoa_don/cau_hinh`; phần trạng thái nghiệp vụ qua `T/trang_thai` | Profile nội bộ được ánh xạ từ cấu hình đã cấp quyền; không công khai cấu hình đăng nhập bộ tải. | N |
| Bộ tải POST `/api/{start,status,reconcile}` | `m2/tai_hoa_don/khach.py:129`, `m2/tai_hoa_don/khach.py:133`, `m2/tai_hoa_don/khach.py:137` | M2 và Adapter `e_hoa_don` | POST `T/bat_dau`; GET `P/viec/{id}`; POST `T/doi_soat` tương ứng | Chuẩn hóa method trạng thái về GET; Q, G, J. Phải khớp protocol bản nguồn/bản vá trước khi bật. | N |
| Bộ tải POST `/api/open-folder` | `m2/tai_hoa_don/khach.py:140` | Adapter bộ tải | Không có đích API công khai; tải kết quả qua Core | Không chuyển thao tác mở thư mục máy chủ sang UI nhiều người dùng. | B |
| Bộ tải POST `/api/events` | `m2/tai_hoa_don/khach.py:156` | Adapter và Core Job Worker | GET `P/viec/{id}/su_kien` | Adapter nhận sự kiện bằng protocol nguồn rồi phát stream Core đã lọc quyền. Không đồng nhất POST này với SSE GET của nguồn khác. | N |

**Không có route cũ để ánh xạ:**

| Thành phần | Kết luận có căn cứ | Xử lý trong bộ API |
|---|---|---|
| OCR-1 | Là API Python/Hot Folder, chưa thấy HTTP dispatcher tại lớp được khảo sát: `ha_tang/cong_ocr.py:127`, `ha_tang/cong_ocr.py:274`, `ha_tang/cong_ocr.py:339`. | Chức năng mới qua `P/engine/e_ocr/viec` và Adapter; không ghi thành “đổi route OCR cũ”. |
| Cổng AI | Có `CongAI.goi`, chưa thấy nhóm HTTP `/api/ai/...` được nối vào shell: `tri_thuc/cong_ai.py:979`, `tri_thuc/cong_ai.py:1236`, `server.py:982`. | Các module tiếp tục dùng cổng AI chung qua hợp đồng SDK/Adapter; không dựng đường gọi Cloud riêng trong lớp chuyển tiếp. |
| M3 | Có dịch vụ Python, chưa thấy route HTTP trong dispatcher được khảo sát: `k2/m3.py:240`, `k2/m3.py:246`, `server.py:976`. | API M3 là phần đặc tả module sau; không suy ra route từ tên hàm. |
| Workflow chung | Chưa thấy route workflow dùng chung trong shell: `docs/47-core/g0/KS-C.md:202`. | Nhóm `P/quy_trinh` là API mới thuộc thân đặc tả, không phải đổi tiền tố route hiện có. |

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
| **Idempotency phân tán**, chưa có chính sách HTTP chung. | `giao_dien/intake.py:74`, `k2/xay_dung.py:154`, `k2/crm_mau.py:160`, `k2/lien_ket_chung.py:3` | Chuẩn hóa header, phạm vi, thời hạn và fingerprint trong thân API. Phạm vi phải phân biệt người dùng, pháp nhân, module và operation. Nối với biên nhận/dedupe cũ; khác payload cùng key phải bị từ chối. |
| **CAS có nhiều loại token**, không thể thay tất cả bằng một số phiên bản dòng. | `crm_g.py:60`, `crm_g.py:75`, `crm_g.py:123`, `crm_g.py:706`, `m4.py:20`, `module_cong_tac.py:65` | Bổ sung `row_version` nơi phù hợp; giữ graph/revision/basis/context token và ý nghĩa của chúng. Client cũ thiếu căn cứ bắt buộc phải tải lại dữ liệu, không tự điền version mới nhất để cho ghi qua. |
| **Phân trang khác tên/tham số**, có danh sách chỉ cắt LIMIT. | `k2/crm_s1.py:52`, `k2/crm_s1.py:72`, `k2/hoa_don.py:505`, `k2/kho_so_luong.py:473`, `giao_dien/operations.py:945`, `khung_khai_bao.py:116` | V1 dùng contract phân trang chung, thứ tự ổn định, giới hạn và thông tin còn dữ liệu. Alias đổi tên tham số nhưng không âm thầm bỏ các trang sau. |
| **Upload raw/header metadata và base64 JSON chưa thống nhất**; giới hạn từng lớp khác nhau. | `server.py:931`, `server.py:945`, `server.py:1143`, `server.py:1232`, `crm_g.py:608` | Dùng F; schema khai rõ metadata, MIME, kích thước và checksum. Alias giải mã định dạng cũ có giới hạn; không tăng trần để bỏ qua giới hạn module/engine. |
| **CSRF/Origin dựa token chung hoặc header `X-HD`** chưa thay được xác thực người dùng. | `server.py:918`, `server.py:980`, `server.py:1008`, `m4/review_goc/may_chu/server.py:417` | Giữ kiểm Origin/Host phù hợp địa chỉ Core triển khai; thêm bảo vệ CSRF gắn với cơ chế phiên theo thân API. Không coi loopback hoặc header tĩnh là quyền người dùng. |
| **GET có ghi nghiệp vụ:** `/api/nghiem-thu` gọi `dong_bo`. | `server.py:137`, `server.py:1128` | Tách POST đồng bộ và GET danh sách. Alias GET không được tiếp tục ghi ngầm. |
| **Lệnh mở thư mục/tắt server** không phù hợp thao tác từ nhiều máy người dùng. | `server.py:1196`, `server.py:1282`, `m2_tai_hoa_don.py:1069`, `m4/review_goc/may_chu/server.py:489` | Thay mở thư mục bằng tải kết quả; dừng tiến trình qua quản trị Core có drain và xác minh danh tính. |
| **Dispatcher hiện gọi module trong cùng backend**, chưa phải chuyển tiếp tiến trình riêng. | `docs/47-core/g0/KS-A.md:18`, `server.py:976` | Dispatcher định tuyến theo registry tới tiến trình module riêng; không giữ cách import trực tiếp làm kiến trúc đích. Ngữ cảnh người dùng/pháp nhân/request phải truyền qua kênh tin cậy do bộ API/SDK chốt. |

**Phần phải giữ:** kiểm quyền backend của download CRM/M4/M5/M9 và khung CRM đã có giá trị sử dụng; không bỏ để thay bằng kiểm quyền chung yếu hơn. Căn cứ: `k2/crm.py:860`, `k2/xay_dung.py:309`, `k2/kho_so_luong.py:720`, `k2/vay.py:798`, `khung_khai_bao.py:103`.

**Lưu ý engine:** trạng thái xử lý thành công, hết mục cần soát và phê duyệt nghiệp vụ là ba trạng thái khác nhau. Adapter phải giữ revision và thu nhận kết quả theo chính sách trước khi engine giải phóng RAM; không tự biến TTL engine thành thời hạn lưu Core. Căn cứ: `docs/47-core/g0/KS-E.md:93`, `docs/47-core/g0/KS-E.md:95`, `docs/47-core/g0/KS-E.md:123`, `docs/47-core/g0/KS-E.md:124`.

## 4. Nguyên tắc lớp chuyển tiếp route cũ

### 4.1. Một đường thực thi có kiểm quyền

Luồng đề xuất:

`Client cũ → alias tại Core → chuẩn hóa đầu vào → xác thực/quyền/schema chung → operation v1 → module hoặc Adapter → kết quả chuẩn → bộ đổi response cũ nếu an toàn`.

Alias không gọi ngược vào handler cũ để bỏ qua cổng bảo vệ mới. Không cho tồn tại hai đường ghi độc lập cho cùng operation.

Route cũ và route v1 phải dùng chung:

- Danh tính đã xác thực, phạm vi pháp nhân và quyền hồ sơ.
- Công tắc module, quyền người thử và MTQ.
- Biên nhận idempotency và điều kiện CAS.
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
4. Core loại bỏ thông tin danh tính nội bộ giả mạo từ request bên ngoài, rồi tạo ngữ cảnh tin cậy cho tiến trình module. Cơ chế bảo vệ kênh cụ thể phải thống nhất với thân API/SDK.
5. Frontend chỉ thấy địa chỉ Core; không nhận URL, cổng hoặc credential engine để tự gọi.
6. Alias vẫn chịu thời hạn, giới hạn body, rate/concurrency và chính sách lỗi của Core; không phải đường dự phòng nới quyền.

Theo CD-028, mỗi module/engine có cổng nội bộ cố định do Core cấp. Khi chưa chạy, Core giữ socket; khi cần thì khởi động, chuyển giao socket và kiểm danh tính/phiên bản/readiness trước khi chuyển tiếp. Với engine cũ chưa nhận socket, dùng phương án chuyển tiếp có kiểm xung đột; không tự chọn cổng khác hoặc dừng tiến trình lạ. Căn cứ: `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:329`, `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:330`, `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:333`.

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

**Các điểm còn phải ghép quyết định vào phiếu API:** chủ sở hữu các nhóm `V`; phân loại trường cấu hình Review; hợp nhất operation Review–M4 trùng đích; thời hạn idempotency, cơ chế phiên/kênh liên tiến trình và lịch ngừng alias. Tên khối, quyền dữ liệu và ánh xạ ID phụ thuộc **phiếu CSDL**.

**Tự kiểm của lát:** đã đối chiếu các nhóm route KS-C §2–§3, các quy ước §4 và chênh lệch §6; đọc bổ sung các nhánh DEMO, bridge và handler liên quan. Không sửa tệp, không chạy ứng dụng/test/migration, không gọi dịch vụ. Tài liệu này chưa phải bằng chứng kiểm thử triển khai; việc lập trình vẫn dừng theo CD-026 và chỉ mở lại khi đủ điều kiện CD-029 tại `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:344`.