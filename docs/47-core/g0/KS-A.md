# KS-A · Xương sống hiện có ↔ 12 khối Core

**Kết luận:** có thể nâng xương sống hiện tại thành Core; cần giữ lại MTQ, công tắc module, bus, hàng việc PostgreSQL, hợp đồng engine và cổng AI/OCR. Tuy nhiên, **chưa có khối nào đủ toàn bộ yêu cầu Core của TL 54 §9**: 11 khối có một phần; chưa thấy Workflow Runner dùng chung. Các khoảng trống lớn là đóng gói/cài module, quản lý tiến trình–cổng theo CD-028, contract liên tiến trình, kho tài liệu thống nhất và phục hồi đồng bộ CSDL–file.

**Phạm vi:** khảo sát tĩnh ngày 30/10/2026 trên nhánh `hop-nhat-20261023`, HEAD `6feb66d`. Không sửa tệp, không chạy dịch vụ, test, migration hoặc truy cập dữ liệu thật. “Có mã” không đồng nghĩa đã nghiệm thu vận hành.

**Căn cứ:** TL 54, đặc biệt §9 và §14; TL 55; `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md:297–356`. CD-028 thay hướng module cùng backend bằng **mỗi module một tiến trình riêng**; không engine/module nào mặc định luôn chạy, kể cả OCR/AI. CD-029 yêu cầu duyệt riêng CSDL, API, SDK trước G2.

**Quy ước dẫn chiếu:** các đường dẫn `giao_dien/`, `ha_tang/`, `k2/`, `nguon/`, `tri_thuc/`, `workflow.py` dưới đây tính từ `src/kho_tri_thuc/`; `tools/` tính từ gốc repo. “Không thấy” chỉ kết luận trong mã thuộc phạm vi khảo sát.

## 1. Đối chiếu 12 khối Core

| Khối TL 54 §9 | Mức hiện có | Dùng lại được — căn cứ mã | Phần còn thiếu so với Core |
|---|---|---|---|
| **Application Shell** | Một phần | Shell HTML, điều hướng và phục vụ asset: `giao_dien/assets/index.html:14–34`, `giao_dien/server.py:1007–1013`. Khung CRM trả phần/thẻ theo quyền và đếm từ danh sách nghiệp vụ: `giao_dien/khung_khai_bao.py:103–167`. | Chưa thấy shell lưới icon hai cấp TL 49 được nối vào giao diện hiện tại; HTML vẫn dùng menu chữ. Chưa thấy menu động cho mọi module theo registry. |
| **Identity/Access** | Một phần | Quyền pháp nhân–module và danh tính từ DB: `k2/quyen.py:88–120`. MTQ có phiên bản, gán vai, phạm vi: `k2/sql_ma_tran_tham_quyen.py:87–144`. Cổng quyết định lấy danh tính/pháp nhân từ DB: `k2/sql_mtq_cong.py:2262–2307`. | Phiên web hiện là danh tính DEMO giữ trong RAM, có thao tác đổi vai; chưa phải đăng nhập production: `giao_dien/server.py:191–205`, `:340–344`. Cần xác thực dùng chung và truyền ngữ cảnh tin cậy qua tiến trình/job. |
| **Module Manager** | Một phần | Khai báo phần, engine, chế độ, vùng dữ liệu: `ha_tang/khai_bao_module.py:350–403`. Công tắc theo module × pháp nhân, người thử, revision và audit: `k2/sql_module.py:8–40`, `:115–151`. | Chưa thấy đọc gói `module.json`, kiểm tương thích, cài/nâng cấp, migration theo gói và kích hoạt nguyên tử. Catalog hiện được khai báo bằng SQL; công tắc không thay cho quản lý gói. |
| **API Dispatcher** | Một phần | Handler chung kiểm origin/token, đọc JSON và điều hướng tới module: `giao_dien/server.py:918–953`, `:976–1001`. | Dispatcher hiện import/gọi trực tiếp, chưa thấy định tuyến động theo module/version, kiểm JSON Schema chung, trace xuyên tiến trình và proxy nội bộ. |
| **Database Manager** | Một phần | Kết nối PostgreSQL và migration có transaction/checksum: `ha_tang/postgres.py:66–76`, `:217–260`; cấu trúc migration chung: `ha_tang/pg_migrations.py:1–5`. Ngữ cảnh đặt theo transaction: `k2/crm_mau.py:135–143`. | Chưa thấy connection pool chung. Migration vẫn tập trung; còn đường dịch vụ dùng kết nối chủ bảng: `k2/crm_mau.py:111–133`. Cần role runtime/migration theo khối, rà RLS và bảo vệ dữ liệu cũ; catalog/quyền thực tế thuộc KS-B. |
| **Document/File Store** | Một phần | Ghi file bất biến, chống ghi đè: `ha_tang/store.py:26–46`. Tiếp nhận theo hash, phiếu nhận, kiểm checksum khi tải: `giao_dien/intake.py:75–128`. PostgreSQL có `kho.tep_goc` với UUID/pháp nhân/hash: `ha_tang/pg_migrations.py:196–206`. | Các nền lưu trữ chưa thành một dịch vụ tài liệu–file–kết quả thống nhất. Chưa thấy contract chung về biến thể, revision, trạng thái duyệt, retention và quyền đọc nội dung áp dụng đồng nhất. |
| **Engine Manager** | Một phần | Host #6 có tiến trình sở hữu, bắt tay instance/PID/implementation, kiểm readiness, Windows Job và dừng có xác nhận: `nguon/trich6_host.py:203–280`, `:280–365`. Bộ tải hóa đơn có host tương tự: `m2/tai_hoa_don/tien_trinh.py:1–9`. | Chưa thấy registry bền vững về launch profile/instance, sổ cổng cố định, chuyển giao socket, tự dừng khi rảnh và số liệu đề xuất chế độ chạy. Host #6 hiện mở cùng server DEMO: `giao_dien/server.py:1315–1323`. |
| **Adapter Registry** | Một phần | Hợp đồng Python kiểm kiểu, hash đầu vào/đầu ra và bằng chứng: `ha_tang/engine.py:35–53`, `:165–191`. Danh bạ ghim mã/version: `ha_tang/danh_ba_engine.py:12–42`. Có wrapper OCR/AI và đọc hóa đơn. | Danh bạ là RAM chứa object Python, chưa phải registry capability/API liên tiến trình. Chưa thấy JSON Schema/wire contract dùng chung hoặc ánh xạ launch profile–capability–adapter bền vững. |
| **Workflow Runner** | **Chưa thấy runner chung** | Có điều phối nghiệp vụ cố định: `workflow.py:15–47`; CRM có các thao tác kiểm/duyệt/từ chối riêng: `giao_dien/server.py:353–366`. | `workflow.py` là bảng dispatch action, chưa phải runner khai báo dependency, nhánh, mapping, bước chờ duyệt và phiên bản workflow. Giữ logic nghiệp vụ hiện có để đưa vào bước của runner sau này. |
| **Job Worker** | Một phần | Hàng việc PostgreSQL có dedupe, lease/token, retry, yêu cầu dừng, phục hồi: `k2/sql_hang_viec.py:25–60`, `:137–205`, `:237–284`. Worker có heartbeat và lưu kết quả cùng CAS: `ha_tang/chay_engine.py:102–177`. | Worker ghi rõ chưa nối server/tự khởi động: `ha_tang/chay_engine.py:1–16`. Chưa thấy lớp job–step–attempt và vòng đời workflow đầy đủ. Job giao diện cũ còn giữ RAM: `giao_dien/operations.py:79–81`. |
| **Audit/Operations** | Một phần | Nhật ký chung: `ha_tang/pg_migrations.py:413–430`; audit MTQ: `k2/sql_ma_tran_tham_quyen.py:138–149`; cổng AI ghi metadata: `tri_thuc/cong_ai.py:463–489`. Handler tránh log nội dung request: `giao_dien/server.py:887–889`. | Chưa thấy trang vận hành Core thống nhất, trace request–job–step–attempt và đo vòng đời/RAM/CPU theo CD-028. Lịch sử xuất file chỉ là một phần lịch sử nghiệp vụ. |
| **Backup/Restore** | Một phần | Backup kho cũ kiểm hash và kèm artifact; restore vào đích mới: `ha_tang/backup.py:40–83`, `:120–147`. Có công cụ `pg_dump → GPG`: `tools/sao_luu_ma_hoa.py:1–12`. | SL-1 ghi rõ chưa bao gồm file/roles/globals, chưa xác nhận giải mã/restore. Chưa thấy phục hồi đầy đủ CSDL Core và kho file theo cùng mốc nhất quán. |

## 2. Các nền bắt buộc phải giữ và giới hạn sử dụng lại

| Nền | Đã thấy trong mã | Giới hạn cần giữ rõ |
|---|---|---|
| **Khung TL 49, XS-4a** | Khai báo phần/thẻ CRM và backend lọc quyền, đếm, drill-down: `giao_dien/khung_khai_bao.py:132–167`; route được nối qua `giao_dien/crm_g.py:475–479`. Có adapter sang `KhaiBaoModule`: `ha_tang/khai_bao_module.py:443–468`. | Đây là nền metadata/backend. Chưa thấy frontend hiện tại gọi khung để dựng lưới; shell đang khai báo menu tĩnh tại `giao_dien/assets/index.html:18–29`. |
| **Công tắc module** | `TAT/THU/VAN_HANH`, revision, người thử, audit; API quản trị: `k2/sql_module.py:55–79`, `:115–193`; `giao_dien/module_cong_tac.py:12–17`, `:73–108`. Cổng kiểm trong transaction: `k2/module.py:62–86`. | Tắt vẫn có thể xem dữ liệu cũ; quyền MTQ vẫn phải kiểm. Công tắc chưa phải cơ chế dừng tiến trình/cài gói. Chưa thấy màn frontend quản lý công tắc. |
| **Vùng dữ liệu XS-5a1** | Có V1–V4, chủ theo dòng, điểm truy cập chéo và kiểm khai báo: `ha_tang/khai_bao_module.py:143–175`, `:225–279`; bản khai các module tại `k2/vung_du_lieu.py:182–255`. | Chỉ là metadata/kiểm khai báo, không GRANT hay kiểm SQL runtime: `ha_tang/khai_bao_module.py:50`, `:228–231`. Nhiều nguồn công bố còn ghi “chưa có”; không coi V1–V4 là cách ly DB đã hoàn tất. |
| **MTQ** | Tách quyết định đọc/đếm khỏi thực hiện hành động: `k2/sql_mtq_nen.py:1–4`, `:45–91`. Có nối CRM và phạm vi nguồn liên module: `k2/sql_mtq_crm.py:119–139`, `k2/sql_mtq_lien_module.py:24–83`. Có dịch vụ cấu hình/nhật ký: `k2/ma_tran_tham_quyen.py:222–283`. | Có cơ chế giữ đường quyền cũ khi MTQ chưa bật: `k2/sql_mtq_cong.py:2299–2307`. Khung Core phải giữ rõ chuyển tiếp này; không coi mọi chức năng đã dùng duy nhất MTQ. |
| **Bus XS-1** | Outbox/inbox PostgreSQL, payload chỉ UUID tham chiếu, dedupe, nhận/ACK cùng transaction: `k2/sql_bus_su_kien.py:1–18`; wrapper `ha_tang/bus_su_kien.py:30–74`. | Giao ít nhất một lần; chưa có subscription/lease/worker riêng. Không bảo đảm exactly-once cho tác động ngoài PostgreSQL. |
| **Hàng việc XS-2b** | Wrapper mỏng trên M0060/M0061: `ha_tang/hang_viec.py:1`. `tao_viec` tạo/dedupe trong giao dịch nghiệp vụ của caller, không commit; `nhan` nhận tối đa một việc với lease và giữ nguyên token: `ha_tang/hang_viec.py:21–40`. Có gia hạn lease, cập nhật tiến độ, kết thúc, retry, yêu cầu dừng và đọc trạng thái lease: `ha_tang/hang_viec.py:43–77`. | Wrapper không tự quản lý giao dịch; caller phải cấp kết nối đã đặt danh tính ứng dụng, máy chủ xác định pháp nhân/module qua quyền phiên, không lấy trực tiếp từ body client: `ha_tang/hang_viec.py:1–4`. `thu_lai` chỉ dùng khi kết quả `LOI` chứng minh lần thử thất bại an toàn: `ha_tang/hang_viec.py:62–66`. |
| **Engine và cổng** | Wrapper dùng cổng được tiêm, không dựng cổng thứ hai: `ha_tang/engine_cong.py:1–6`, `:127–158`, `:184–191`. `EngineHoaDon` bọc reader XML/ZIP: `ha_tang/engine_hoa_don.py:109–146`. | Nhánh hóa đơn wrapper chưa bọc tải cổng thuế, chưa nối M2/M3: `ha_tang/engine_hoa_don.py:1–9`. Không đồng nhất wrapper Python với engine process đã chuẩn hóa. |
| **OCR-1** | `CongOCR` nhận PDF/ảnh → DOCX, có đệm SHA-256, hạn mức trang, khóa file và hủy: `ha_tang/cong_ocr.py:339–386`. | Dùng lại tích hợp ABBYY Hot Folder; chưa phải OCR API nhận socket do Core chuyển giao. Cache đang bền vững trên đĩa; phải đưa vào chính sách lưu trữ, không suy thành RAM-only. |
| **AI, MASK-1/2** | Local trước, Cloud khi cần/kiểm xác suất: `tri_thuc/cong_ai.py:1236–1258`. Client Mask kiểm danh mục mở, `gui_duoc`, không còn sót; che/mở che qua API: `:660–694`. Cloud kiểm thêm trước gửi: `:1149–1171`; mở che rồi đánh giá: `:1192–1199`. | Giữ một cổng AI và một bộ Mask. KS-A chỉ xác nhận client/luồng phía repo này; chưa kiểm mã hoặc vận hành MASK-1/2 ở ứng dụng ngoài. Không suy từ client rằng Mask server đã đạt nghiệm thu. |
| **Mã hóa** | SL-1 mã hóa backup; MH-1 có khóa DPAPI CurrentUser, phiên bản khóa và HMAC tra cứu: `tools/sao_luu_ma_hoa.py:1–12`; `ha_tang/ma_hoa_cot.py:142–204`. | MH-1 ghi rõ chưa nối caller/CSDL: `ha_tang/ma_hoa_cot.py:1–7`. Không kết luận dữ liệu cột hiện tại đã được mã hóa; cần thiết kế phục hồi khóa khi đổi tài khoản/máy. |

Các nền SQL đã được đưa vào chuỗi migration nguồn: bus tại `ha_tang/pg_migrations.py:12230–12235`, công tắc tại `:12391–12396`, hàng việc tại `:12420–12424`. Điều này **không xác nhận migration đã chạy trên CSDL đích**.

## 3. Giao diện cần có

Đối chiếu danh sách cuối TL 54 §9; “có” dưới đây là có mã màn/component, chưa xác nhận bằng chạy UI.

| Màn cần có | Hiện trạng trên nhánh khảo sát |
|---|---|
| **Cấu hình hệ thống** | Một phần: màn Nguồn dữ liệu và thông tin Local AI, chưa phải quản trị Core tập trung — `giao_dien/assets/that.js:878–887`, `:941`; API cấu hình tại `giao_dien/server.py:1030–1031`. |
| **Quản lý module** | Có API công tắc; chưa thấy màn cài/nâng cấp/cấp quyền gói — `giao_dien/module_cong_tac.py:12–17`. Shell vẫn có menu tĩnh — `giao_dien/assets/index.html:18–29`. |
| **Quản lý engine** | Có thông tin sức khỏe #6 trong API health và các thao tác bộ tải hóa đơn; chưa thấy màn registry/launch profile/cổng dùng chung — `giao_dien/server.py:1003–1006`, `giao_dien/m2_tai_hoa_don.py:349–394`. |
| **Quyền dữ liệu** | Có component MTQ độc lập và API ma trận/quyền của tôi/nhật ký — `giao_dien/assets/ma_tran_tham_quyen.js:1–7`, `:52`; `giao_dien/ma_tran_tham_quyen.py:16–21`. Chưa thấy mount component vào shell hiện tại. |
| **Workflow** | Chưa thấy màn thiết kế/quản lý workflow dùng chung; điều phối hiện là action cố định — `workflow.py:15–47`. |
| **Tài liệu/kết quả** | Có Nhập dữ liệu, Hồ sơ đã nhận và các màn hồ sơ nghiệp vụ — `giao_dien/assets/index.html:37–85`. Chưa thành thư viện chung quản lý biến thể/revision/quyền tài liệu. |
| **Công việc** | Có polling tiến độ job cũ và trạng thái bộ tải — `giao_dien/assets/that.js:35`, `giao_dien/m2_tai_hoa_don.py:225–241`. Chưa thấy màn hàng việc XS-2 thống nhất; worker chưa nối server — `ha_tang/chay_engine.py:1`. |
| **Lịch sử vận hành** | Có Lịch sử xuất file và component nhật ký MTQ; chưa thấy dashboard vận hành Core — `giao_dien/assets/that.js:990–997`, `giao_dien/ma_tran_tham_quyen.py:17`. |

## 4. Một tiến trình hiện tại so với CD-028

**Đánh giá:** mô tả “một tiến trình” đúng với shell và các module nghiệp vụ ghép trong backend chính. Tuy nhiên, toolchain đã có ngoại lệ tiến trình con: host engine #6 và Node tải hóa đơn. Không nên thiết kế G1 từ giả định toàn bộ hệ thống chỉ có một OS process (`giao_dien/server.py:1315–1334`; `giao_dien/m2_tai_hoa_don.py:502–530`).

Các vị trí phải tách hoặc thay ranh giới trong `giao_dien/server.py`:

| Vị trí | Hiện trạng | Hướng tách trong đặc tả |
|---|---|---|
| `:54–67`, `:196–205` | `LocalApp` giữ cấu hình, token, khóa chung và phiên RAM. | Core giữ danh tính/phiên; module nhận ngữ cảnh được xác thực qua contract. Không chia sẻ trực tiếp dictionary hoặc object ứng dụng giữa tiến trình. |
| `:207–259`; các factory `:409`, `:543`, `:736` | Backend chính tạo/cất dịch vụ CRM, M9, M5, M2 và kết nối của chúng. | Chuyển vòng đời dịch vụ, kết nối runtime và trạng thái riêng sang tiến trình module; Core giữ dịch vụ chung theo SDK. |
| `:333–377`, `:435–468`, `:612–697`, `:781–838` | Server chứa điều phối action của từng module. | Đưa action về module tương ứng; Core giữ xác thực, định tuyến, kiểm contract và truy vết. |
| `:976–1001`, `:1060–1127`, `:1229–1261` | Handler import/gọi module trong cùng tiến trình; nhiều đường dùng `mutation_lock`. | Thay bằng dispatcher/proxy tới tiến trình nội bộ. Giữ transaction/khóa DB/CAS; `threading.Lock` không phối hợp được các tiến trình. |
| `:871–881`, `:918–929`, `:1007–1013` | Server tự bind loopback; kiểm Host/token và phục vụ asset theo danh sách cố định. | Tách cổng truy cập Core với listener của module/engine; đặc tả cấp/nhận socket, proxy và asset theo gói. Chính sách truy cập Core phải phù hợp mô hình máy chủ nhiều người. |
| `:1310–1334` | `serve()` tạo host #6, mở ngay cùng DEMO và dừng khi server đóng; đóng bộ tải M2 tại đây. | Chuyển sang quản lý vòng đời tập trung: kích hoạt khi cần, readiness, chờ việc kết thúc, tự đóng khi rảnh, thu hồi cổng và phục hồi sau gián đoạn. |

**Chênh lệch cổng:** host #6 hiện để tiến trình con tự mở cổng ngẫu nhiên rồi báo về (`nguon/trich6_host.py:607–617`). Trong phần mã đã rà không thấy `socket.share()`/`fromshare()` hoặc sổ cổng cố định. Danh bạ engine chỉ là dictionary RAM (`ha_tang/danh_ba_engine.py:12–31`). Đây chưa đáp ứng CD-028.

**Phần nên dùng lại:** bắt tay instance/implementation, kiểm readiness và Windows Job sở hữu tiến trình của host #6 (`nguon/trich6_host.py:240–268`, `:280–365`). Bổ sung cơ chế cổng vào nền này; chưa có căn cứ cần viết lại toàn bộ host.

G1 phải mô tả cả luồng nhận lại cổng khi dừng, chống khởi động trùng, xử lý request đang chờ và engine cũ không nhận socket. Khả năng chuyển giao không khoảng hở cần kiểm chứng kỹ thuật ở G2; G0 chưa chạy thử. Số liệu khởi động, thời gian rảnh, RAM/CPU và đề xuất chế độ chạy phải theo CD-028; chỉ Admin áp dụng.

## Chờ Anh

- Chốt nguồn đăng nhập production và quan hệ pháp nhân–workspace; phiên DEMO hiện tại chưa thay thế được đăng nhập thật.
- Chốt retention cho bản gốc, OCR/cache, bản đã che, kết quả và dữ liệu tạm; mục tiêu thời gian phục hồi/mức mất dữ liệu chấp nhận được.
- Duyệt lần lượt ba bộ CSDL/API/SDK theo CD-029; các tên TL 55 vẫn là nháp.

## Gợi ý cho đặc tả G1

- Lập bảng giữ lại–bọc lại–bổ sung cho từng khối; ưu tiên contract và ranh giới tiến trình, giữ logic nghiệp vụ đã có.
- Chuẩn hóa `module.json`, JSON Schema, SDK và ngữ cảnh quyền xuyên HTTP/job; tách trạng thái hoàn tất xử lý khỏi duyệt nghiệp vụ.
- Đặc tả sổ cổng, chuyển giao/thu hồi socket, readiness, chống spawn trùng và số liệu vận hành theo CD-028.
- Hoàn thiện kho tài liệu và backup/restore đồng bộ CSDL–file–khóa; mọi tên mới dùng tiếng Việt không dấu, `snake_case`.

Vòng 2: đã sửa theo RV-AD (1 mục)