# M9 — kết quả root review thiết kế trước coding

Ngày19/10/2026. Root đã đọc toàn proposal và đối chiếu các điểm ảnh hưởng với core nguồn. **Revision2 được dùng làm đầu bài kỹ thuật cho bước bind/triển khai M9 sau CRM03; chưa migration/runtime/acceptance M9.** File `THIET-KE-M9-TYPED-DEMO-33.md` SHA256 `e3e9704f5af808bc3c398a84ba85e3a80e0bc4b51c4042c1bda90fb73cfa9bf3`. Bản trước hash `c5bd5a67…203cf40` và backup đã giữ; corpus19ca không đổi.

## Các điểm đã sửa qua review

1. **Raw nhiều PN/chưa map:** core `kho.tep_goc` bắt buộc PN và hash unique toàn bảng. Metadata intake thuộc integration M0, dùng cùng immutable file store; derivative PN có envelope/hash và provenance tới raw gốc. Không gán PN giả, nới tenant hoặc dùng nhầm file PN khác vì cùng hash. Không tạo raw engine riêng M9.
2. **Danh tính hồ sơ vay:** source instance/section/company/source ID ổn định, financial kind nằm trong revision. LC chuyển nhận nợ cùng source ID không tạo thêm hợp đồng, alias hoặc tiền.
3. **Một ngân sách BANK qua mọi module:** link CHILD lấy tổng child active, DIRECT giữ parent một lần; không cộng cả hai. Trước xác nhận phải kiểm remaining chung cùng PN/currency, không dùng sum bị RLS che mất phân bổ module khác. Khóa theo HĐ sorted→BANK sorted→nghĩa vụ, bind protocol core cuối; kiểm cross-module concurrency và parent/child mismatch.
4. **Mapping công ty:** một approved interval theo source company identity, không đưa target PN vào khóa để cho phép hai mapping trùng. Thiếu disambiguation giữ chờ. Retarget PN sau promote mở impact task, không tự thêm master/alias hoặc chuyển link/lô. Source code giống ở hai namespace/company thật vẫn độc lập theo S15.

## Phần làm tiếp trong phạm vi đã chốt

Sau khi CLI89659 terminal và core được review, đối chiếu schema/API/quyền cuối rồi chọn migration mới: nhận snapshot/profile → validate → mapping → candidate vay/draw/rate/lịch → K5 kiểm/duyệt → link/phân bổ M1 thật → file soát/khởi động lại. Dùng lại HĐ/PB, proposal/work/link/lô/audit; validator doanh thu CRM không dùng để duyệt VAY. Các bảng/cột proposal trùng grain với core cuối phải bind/reuse, không tạo bản song song.

Đầu bài nghiệp vụ `GIAO-VIEC-BRIDGE-KHOAN-VAY-M9-33.md`, proposal revision2 và corpusv2 cùng là căn cứ; danh mục19ca đầu vào không tự phủ hết quyền/concurrency/UI/source Google. Giữ source precision UNPROVEN/LOST, NULL khác0, scope LOAN/DRAW, valid/known time và nguyên tệ/VND riêng. Không suy export lãi hiện tại thành accrual oracle hoặc tính lại engine vay/lãi.

Full M9 vẫn gồm short/long/draw/LC/bảo lãnh, L7/L8/L12 và C4d đầu tư; các phần thiếu current register/policy/source detail tiếp tục có việc cụ thể, không bị loại khỏi toàn33. Không tự chốt vốn hóa/FX/template LC/loại đầu tư thật. Google readonly/deploy/profile/credential và production policy là gate vận hành riêng, không cản phát triển và kiểm DEMO đúng contract. Không có phép chuyển kho thật, nhập Junsky, cloud AI hoặc duyệt thật trong review này.

Mọi file/DB/role kiểm thử phải giữ lại. Bằng chứng runtime sau coder terminal phải bao gồm positive controls, typed FK/RLS/ordinary role, exact amounts/provenance, retry/revision, atomic reject, hai thứ tự tiền/lịch, lock quan sát thực, artifact bytes/cell và GUI khi công cụ hỗ trợ. Không lấy DDL hoặc một adapter chạy được làm nghiệm thu toàn M9.

## Root review binding core12 và amendment R1–R4 — 19/10/2026

Root đã đọc full binding44e28 và toàn amendment cuối, đối chiếu review độc lập `REVIEW-BINDING-M9-CORE-01.md` SHA080b32acecf7d569ec184d113fb6f388cb9bb61853418b692562a78c4d93fa24. Bản giao code là `BINDING-M9-CORE-SAU-CRM03.md` SHA **28af9c1045c8da5448056baa45b679fd476f48aaa40d897ff92430764b168bc5** cùng proposal revision2 và source contract/corpus đã pin. Bản44e28 được giữ tại m9-binding-before-r1r4-20261019-080802-fc6363d9; không rewrite lịch sử review.

Bốn điều kiện kỹ thuật đã được cụ thể hóa đủ để đưa vào đầu bài triển khai: discriminator/subject owner bất biến tại DB; action/eligibility/V4/wholegraph canonical digest và lock không dựa riêng service; stable logical target/consumption xuyên PB/rate/basis revision giữ oldFK/paid; BANK money-encoding proof có căn cứ, unknown không thành eligible numeric remaining. Root chấp nhận hướng contract này cho implementation và các ca âm/dương/race đã ghi; **không coi các ràng buộc chưa code là đã có hiệu lực**. Không có policy account/FX/capitalization mới được phê duyệt từ review kỹ thuật.

Sau gate launcher05, bind lại core cuối nếu file schema/quyền/link có đổi; hiện sửa04/05 chỉ bootstrap/runtime, migration1–12 vẫn cùng baseline03. Giao Claude triển khai nối nguồn vay vào shared K2/K5/UI/file và common allocation, không adapter/schema đơn lẻ hoặc engine vay/lãi mới. Fresh/upgrade CRM DIRECT và typed lifecycle, consumer CRM regression, two-domain remaining và logicaltarget capacity phải kiểm cùng nhau trước bật CHILD. Đủ input DEMO vẫn làm toàn chuỗi; actual Google/source precision/policy/current register còn gate đúng thao tác. FullM9/C4d/toàn33 vẫn chưa hoàn thành hoặc nghiệm thu.
