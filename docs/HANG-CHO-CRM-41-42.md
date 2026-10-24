> **22/10/2026 · Theo lệnh mới của Anh: CRM coding trong lúc agent review M4.** Gói tiếp theo [CRM-41-04A — Ký kết lần đầu](GIAO-CODE-CRM-41-04A-KY-KET-LAN-DAU.md) đã chuẩn bị đúng 8 file, dùng lại master/quyền/storage/UI; chưa dispatch tại thời điểm ghi. Agent M4 chỉ đọc review; hai lỗi UNKNOWN UI đã kiểm độc lập còn mở, bản sửa M4 giữ hàng chờ. G4 gồm PDF ký, ngày ký, khai Có/Không, khóa G3 và lịch sử; G5 chỉ trạng thái ban đầu, G6/K5/engine/correction làm sau. Full CRM/M4 chưa nghiệm thu, M9 tiếp tục dừng, không xóa file.

> **21/10/2026 · F14 — kiểm mới nhất, chưa nghiệm thu module.** Claude hoàn tất sửa hữu hạn đúng ba file host/test/report, không thay engine nguồn hoặc thuật toán. Source native **25/25 PASS**; client/projection/wiring **32/32 PASS** giữ bằng chứng vì các phần tương ứng không đổi. Bộ owned host hiện **19/20 PASS, 1 ERROR, 0 skip**; USERBASE/.pth-only và PYTHONPATH/sitecustomize-only đều đã chạy thực tế đạt, đủ ba hook bảo vệ file.
>
> **Còn lỗi đọc trạng thái lượt trích mới:** HTTP chưa trả header trong hạn60 giây; lỗi được giữ UNKNOWN và bảo toàn ý định. Đọc lại lượt đã lưu qua owned host đạt status200/done và raw200 đúng niêm phong/hash/độ dài; đây không chứng minh luồng lượt mới đã sửa xong. Chưa kết luận nguyên nhân do lock hoặc đường dẫn. Các tiến trình kiểm đã dừng sạch, hash code/source không đổi sau kiểm. Chưa kiểm GUI/full accuracy/toàn module từ bộ kết quả này.
>
> **Bước nghiệp vụ tiếp theo là CRM41-03 Báo giá → Soạn hợp đồng** theo41–42, dùng lại G1/G7/master và renderer reference hiện có; đang chốt binding14file và xuất DOCX/PDF thật qua WordCOM tại máy. Typed G2/G3 không phụ thuộc việc khép độ chính xác trích; lỗi status engine vẫn là đầu việc mở trước nghiệm thu luồng trích. Tiếp theo M4 Review chứng từ L3, duyệt/PDF, nghiệm thu–công nợ và Request độc lập. Giữ toàn phạm vi CRM/M4; CRM → M2-00 → E1-MUA tuần tự; M9 giữ dừng. Không xóa file. Các mốc cũ bên dưới là lịch sử.
> **21/10/2026 · HANG_CHO_SAU_CRM_DA_DUOC_ANH_GIAO.** Thứ tự tiếp theo đã chốt: **CRM → M2-00 → E1-MUA**, giao tuần tự, không chồng writer. Hai gói mới chưa dispatch, chưa có code/test/nghiệm thu mới; chi tiết ở mục 7. Quyết định dùng chung engine #6 là ràng buộc kiến trúc bổ sung cho các handoff, không đồng nhất quyền xác nhận/duyệt M4, CRM và M2.

> **21/10/2026 · M4_02A_FIX03_DA_KIEM_THUAN_VA_PUBLIC_DOM**: Claude67264 đã terminal/stop/freeze367source/435runtime,354file nền nguyên;49/49kiểm thuần,4đối chứng dữ liệu và guard parent/child khác thư mục đều đạt. PublicDOM14/14đạt, có nút tải đúngbytes/nháp mới không bị refresh muộn ghi đè; không phải browser/HTTP/Excel thực đã nghiệm thu. PostgreSQL/HTTP/workerReview thực/GUI còn chờ kiểm, fullM4/CRM chưa hoàn tất. Tiếp tục dùng Review gốc và tuân thủ quyết định một engine trích dùng chung. Thứ tự hai gói mới vẫn CRM→M2-00→E1-MUA, chưa chạy M2; M9 dừng, không xóa file. Các mốc cũ bên dưới là lịch sử.

> **21/10/2026 · M4_02A_FIX02_DA_KIEM_FIX03_DANG_CHUAN_BI**: Claude91225 đã kết thúc, freeze367source/435runtime. Kiểm thuần45/45 đạt,0skip;4đối chứng dữ liệu đạt. Kiểm độc lập phát hiện guard tính toán lệch theo thư mục chạy. PublicDOM14ca:5đạt,2lỗi refresh muộn,7chưa kiểm do nút báo cáo chưa hiện; lỗi so headers ban đầu thuộc bộ kiểm và đã sửa, P02đạt. Đang chuẩn bị giao Claude sửa3điểm hữu hạn, tiếp tục dùng lõi Review gốc; chưa có writer mới/chưa nghiệm thu GUI/fullM4/CRM. R5 mới khép tĩnh, PG/HTTP còn chờ. M9 dừng, không xóa file. Các trạng thái cũ bên dưới giữ làm lịch sử.

> **21/10/2026 · M4_02A_FIX02_CLAUDE_DANG_LAM**: FIX01 đã terminal/freeze; kiểm thuần38 ca đạt36, còn1FAIL guard và1ERROR test,0skip; bốn đối chứng QD/NA/NULL/0 độc lập đạt. PublicDOM chưa vào được form:12NOT_VERIFIED, không phải12productFAIL. Đã giao Claude sửa sáu điểm hữu hạn (actual91225/cùng session), giữ code Review gốc,13file hiện có/354file nền; chưa nghiệm thu GUI/M4/CRM. Sau terminal sẽ kiểm lại rồi mở DEMO. CRM Báo giá→Soạn đã chuẩn bị gói reuse DOCX/PDF, chưa giao code. M9 dừng, không xóa file. Các trạng thái cũ bên dưới giữ làm lịch sử.

> **21/10/2026 · M4_02A_FIX01_CLAUDE_DANG_SUA_TICH_HOP**: Lượt tiếp tục82481 đã kết thúc và được freeze367source/435runtime. Kiểm thuần30/30 đạt, một ca độc lập QD/NULL còn lỗi; PG/HTTP/GUI mới chưa kiểm. Đã giao Claude sửa hữu hạn cùng session (actual24813): lifecycle worker, khóa/connection, retry/nguồn hiệu lực và vòng đời form/tab. Dùng lại Review gốc56/56 cùng65/65references; không viết lại engine. Chờ terminal rồi kiểm độc lập và mở DEMO. Full M4/CRM chưa nghiệm thu; M9 dừng, CAD để sau, không xóa file. Các dòng trạng thái cũ bên dưới là lịch sử.

> **21/10/2026 · M4_REUSE_UI_CLAUDE_DANG_LAM**: Đã giao Claude lượt tiếp tục M4-02A (actual 82481, cùng session), kế thừa bốn tệp partial, dùng lại bố cục/render của Review gốc và chỉ thích nghi API/session/context. Đối chiếu nguồn đã xác nhận 56/56 tệp runtime và 65/65 references khớp nguyên byte. Lượt hiện tại chưa kiểm product/GUI; chưa nghiệm thu M4 hay CRM. Giữ toàn bộ kế hoạch duyệt/PDF, nghiệm thu–công nợ/Request; CAD để sau, M9 dừng, không xóa file.

# Hàng chờ CRM theo tài liệu 41–42 — ngày 20/10/2026

**21/10/2026 · M4_DUNG_LAI_BAN_GOC_UI_TRUOC.** Đã đối chiếu 56/56 tệp được copy với nguồn Review hiện hành, giữ nguyên lõi và ưu tiên đưa bố cục/giao diện Review có sẵn lên M4. Lượt Claude53961/fabfff dừng timebox với code partial362/430, đã freeze/kiểm phạm vi; chưa có giao diện Review/test/report hoàn tất. Giao tiếp phần còn thiếu trong cùng session, không viết lại thuật toán nguồn. Full M4/CRM chưa nghiệm thu.

**21/10/2026 · M4_02A_NATIVE_ACTIVE_53961.** Đã giao Claude gói Review M4 Lớp 1–2 trong session hiện có: 6 file sửa + 7 file mới, giữ 354 file nền và toàn bộ migration 1–18. Native đã khởi tạo đúng 5 file tools/không MCP; bản sao lưu 492 đầu vào đã có. Gói gồm findings/nguồn ô, ghép hạng mục, chạy lại và lịch sử/báo cáo, tái sử dụng lõi Review. Đây là code đang làm, chưa self-test/kiểm độc lập/GUI M4-02A. CRM repair03 giữ kết quả kiểm public-DOM 11/11; browser mới chỉ quan sát màn hình/quyền, upload còn NOT_VERIFIED. Full M4 và CRM41–42 tiếp tục trong hàng chờ; M9 giữ dừng, không xóa file.

## M4 và CRM được Anh yêu cầu triển khai dần — 20/10/2026

Anh yêu cầu giao Claude làm dần cả M4 và CRM theo các phần đã chốt; báo tiến độ mỗi 30 phút và báo riêng khi module có giao diện sẵn sàng để Anh xem. Lệnh mới mở lại CRM bên cạnh M4; các quyết định còn mở chỉ giữ chờ ở nhánh phụ thuộc, không chặn toàn bộ CRM. Các module khác chưa chốt giữ trong hàng chờ; M9 không mở lại code.

M4-01B6 đã khép kiểm nền hữu hạn: native đọc tệp 50/50, 4/4 nhóm độc lập; native PostgreSQL 10/10, 8/8 nhóm PostgreSQL độc lập. [Báo cáo B6](REVIEW-M4-01B6-RUNTIME-20261020.md) ghi giới hạn. M4-01C3 đã terminal cùng session Claude (48960/082b72); source352/runtime418 được freeze và đối chiếu hash. Root chạy16 pure,10 nhóm async native đạt; diagnostic độc lập xác nhận3 cửa sổ lỗi cũ được sửa. Backend giữ nguyên sau C2 với8 HTTP/PG thật đạt. Kiểm giao diện DEMO thực tế đã đi qua tạo HĐ, tải/gắn DOCX, trích37 mã (8 có giá trị/29 chưa có), tạo đợt nháp và danh sách thiếu với nút Nộp bị chặn. Đây là quan sát một phần, chưa nghiệm thu18 ca GUI hay toàn M4. Owned GUI đã dừng, giữ toàn bộ dữ liệu và ảnh.

Hai lỗi upload đã được Claude sửa trong C4, terminal69281/59ecd1; actual5contracts độc lập đạt. Khi đó native đạt12 nhóm và còn1lỗi setup test, diagnostic riêng không phải native13PASS. Lượt CRM đã sửa đúng setup, giữ nguyên mọi assertion và M4 product JS. Root chạy lại trên partial source358/frozen424: **13/13 nhóm native M4 đạt**, actual357cb1; chín file Python qua AST và script S6 qua Node syntax check. Đây là hồi quy hữu hạn, không nghiệm thu toàn M4/CRM. [Review C4](REVIEW-M4-01C4-DOC-LAP-20261021.md) giữ bằng chứng lịch sử.

**CRM-41-02 đã có code partial**, lượt owned70436/eb98ec dừng theo timebox30phút tại terminaleca51c: stop/scope check đạt, chưa có report hoàn tất. Root lưu nguyên trạng358 source/424 runtime, sáu existing đổi và sáu file mới;345 file được bảo vệ. Còn thiếu test HTTP và báo cáo. Ba agent cùng Root đã rà parser/service/SQL/API/UI, xác định các sửa về transaction upload, parser fail-closed và intent/context giao diện trong [bản giao sửa tiếp](GIAO-SUA-CRM-41-02-TIEP-01.md). Phạm vi vẫn15targets, lượt tiếp13existing+2new, cùng session52783bcd-6e1d-46d2-9e45-3c527aa43e5b và5filetools. [Handoff gốc](GIAO-CODE-CRM-41-02-MAU-DOCX-G7-S6.md), [DEMO inputs](CRM-41-02-DEMO-INPUTS.json) và [prefix17](CRM-41-02-MIGRATION-PREFIX-17.json) giữ nguyên; M18 chỉ append sau17migration cũ. Tại mốc partial này, parser/service/DB/HTTP/GUI CRM mới chưa chạy; kết quả mới nhất được ghi riêng bên dưới. Chín fixture DOCX độc lập giữ private; không chạy product/test/SQL/GUI khi writer hoạt động.

Không chờ hoàn tất toàn bộ Review M4 mới giao CRM. Tái sử dụng đầy đủ Review M4-02, duyệt/PDF, nghiệm thu/công nợ và Request tiếp tục trong phạm vi; một product writer, agent chuẩn bị/rà soát song song. Chỉ báo module sẵn sàng cho Anh xem khi GUI và phạm vi tương ứng đã kiểm độc lập.

Lịch cập nhật 30 phút đã được bật lại đúng chat này theo lệnh mới; nhịp đó chỉ đọc bằng chứng và báo, không tự khởi chạy coder hoặc product/test/SQL. Kho thật tiếp tục SQLite; giữ toàn bộ file/lịch sử, không bật cloud hoặc duyệt nghiệp vụ thật. Các mốc dừng bên dưới là lịch sử đã được lệnh mới thay thế trong phạm vi M4 và CRM.

**CRM_G1_G7_S6_REPAIR03_PUBLIC_DOM11_PASS_GUI_PENDING.** Claude hoàn tất lượt73112/408e4f, exit0/stop/scope/posthash đạt, đúng2file JS/report/NEW0/358protected; Root freeze source360/runtime428. Root chạy cùng11 oracle public DOM trên JS mới:11/11 PASS, JS syntax đạt, không unhandled/setup error; N06 upload cũ không còn xóa retry mới, exact File/header/key và completion đúng phiên bản đều đạt. Các child kiểm đã dừng, toàn bộ hash giữ nguyên. Trên repair02,29/29 kiểm thuần, parser độc lập9/9+4/4 và native HTTP13/13 đã đạt, M18 thực tế áp dụng/17 checksum cũ giữ nguyên; các source backend/parser/tests tương ứng vẫn byte-exact nên không chạy lặp rộng. Đang chuẩn bị kiểm trình duyệt thật bằng server DEMO sở hữu riêng; integration độc lập sâu và browser GUI chưa nghiệm thu. Full CRM41–42/M4 chưa hoàn tất. M4 tiếp tục ReviewL1/L2 dùng lại; bộ input độc lập đang chuẩn bị, đã chốt đường BOQ mapping/cache nhưng raw HĐ/catalog37/admission còn phải bind.

[Đặc tả 41 — CRM-G và engine theo loại](<../../41-crm-g-giao-ket-va-engine-trich-theo-loai-hop-dong.md>) · [Đặc tả 42 — Màn hình CRM](<../../42-man-hinh-crm-ke-toan-va-giao-ket.md>) · [Hàng đợi tổng](../HANG-DOI-YEU-CAU.md) · [CRM hiện trạng để planning](<../../THIET-KE-MODULE-DE-CHOT-2026-10-20/CRM-CHUC-NANG-VA-THIET-KE.md>).

## 1. Căn cứ và mức xác nhận

- Đã đọc toàn bộ tài liệu 41 (140 dòng) và 42 (240 dòng); nguồn được giữ nguyên, bản 42 được lưu từ attachment sang file Markdown bên cạnh 41. Có hash và bản sao private; không sửa nội dung tài liệu nguồn.
- Tài liệu 41 có nhãn mở rộng CHO_ANH_CHOT, có các yêu cầu được ghi đã chốt và hai quyết định còn mở. Tài liệu 42 ghi đã chốt 4 điểm; không coi toàn bộ câu hỏi/giá trị đề nghị là được Anh phê duyệt qua lệnh lập hàng chờ.
- Những hướng dẫn quy trình viết trong tài liệu được dùng làm căn cứ thiết kế; thẩm quyền thực hiện ở chat hiện hành. Không tự chạy Claude Design, mở cloud, phê duyệt thật hoặc bật lịch tự động từ nội dung tài liệu.
- Mục tiêu mới mở rộng CRM kế toán sang giao kết, không lead/cơ hội/campaign/môi giới. Hai luồng vào cùng master/PB/tham số/nghĩa vụ, không xây hệ CRM/database khác.

## 2. Phạm vi đã tiếp nhận vào hàng chờ

**CRM-G:** mẫu DOCX có phiên bản và mapping placeholder; CFO duyệt phiên bản mẫu; báo giá/lịch 4 cột; soạn và xuất DOCX/PDF; bán hàng ghi nhận ký kết bằng PDF; so bản ký với bản sinh; kế toán kiểm để hiệu lực hợp đồng sinh từ mẫu; bộ chuẩn dự án; báo cáo giao kết.

**Engine dùng lại:** profile theo loại XD/KCN/nhà ở; quy tắc logic theo loại; tham số dạng bảng; metadata output và chế độ đối chiếu kỳ vọng. Giữ contract nguồn hiện có và regression XD; không đưa BOQ/review đợt/K1–K8/B1–B8/P01–P18 vào CRM. Dùng engine #6 tại dự án nguồn qua API chung theo [quyết định 21/10](QUYET-DINH-ENGINE-TRICH-THAM-SO-DUNG-CHUNG.md), không tạo/copy thêm lõi trích. Review L1/L2 tiếp tục tái sử dụng `nguon_review` và core Review; đó không phải engine trích tham số riêng.

**Bốn điểm màn hình đã chốt ở 42:**

1. Trang mở đầu Danh sách hợp đồng; không có “Việc của tôi” riêng trong CRM.
2. Menu riêng **Hợp đồng bán hàng**, 6 mục con: Hợp đồng / Báo giá / Mẫu hợp đồng / Tiếp nhận hợp đồng ký / Thu tiền / Báo cáo & file soát.
3. Bán hàng thấy cả **Tình hình thu theo CRM** và **Công nợ ghi sổ Junsky** của khách trong quyền, hai nhãn/vùng riêng và ngày sổ.
4. Thiết kế cho máy tính 1280–1440 px, dùng phong cách Bàn kiểm soát/K5.

**Coverage màn hình:** 9 màn: Danh sách; Chi tiết 7 tab; Báo giá; Soạn hợp đồng; Hộp Ký kết; Mẫu/ánh xạ; Tiếp nhận bản ký; Thu tiền; Báo cáo. Đặc tả 42 liệt kê 16 trạng thái thiết kế và một trạng thái Báo cáo bổ sung, tổng 17 hình/trạng thái khi làm đủ. Việc duyệt vẫn qua K5, không tạo bộ duyệt CRM riêng.

**Hiện trạng cần thay đổi:** CRM hiện chỉ nhận JSON trích và hiệu lực qua KT kiểm → CFO/V3; chưa có origin MAU, quản lý mẫu được CFO duyệt, vòng báo giá/soạn/ký hoặc tỷ giá nhập tay. Profile KCN/nhà ở DEMO không thay workflow duyệt mẫu. Luồng A cần service/DB guard riêng, không cho KT giả danh CFO hoặc hạ quyền luồng B.

## 3. Hàng chờ theo phụ thuộc

| Gói | Kết quả để giao Claude | Điều kiện và trạng thái hiện tại |
|---|---|---|
| CRM-42-00 — Chốt liên kết màn hình/dữ liệu | Ma trận 41 G1–G8/E1–E6 ↔ 9 màn/7 tab/17 trạng thái ↔ dữ liệu/API/quyền/ca kiểm. | **DOCS_ROOT_PEER_REVIEW_CLOSED.** [Ma trận](CRM-42-00-MA-TRAN-MAN-HINH-VA-CA-KIEM.md) và [delta/handoff](CRM-42-00-DELTA-DU-LIEU-API-QUYEN.md) đã giao; gói docs không phải CRM đã code/test/GUI. Câu hỏi mở chỉ chặn nhánh phụ thuộc. |
| CRM-41-01 — Engine trích theo loại | Tái dùng parser/core chung; catalogue/version theo loại; logic và lịch dạng bảng; output tương thích, chế độ so với bộ tham số kỳ vọng. | **HANDOFF_PREPARED_NOT_DISPATCHED.** [Giao Claude: engine chung và chuyển M4/CRM](GIAO-CODE-CRM-41-01-ENGINE-DUNG-CHUNG.md). Gói này sở hữu common API/client và chuyển đường trích thật, tách renderer CRM-41-03; không đợi E1-MUA mới ngăn tạo lõi riêng. Bind interface/API engine #6 tại source theo [quyết định 21/10](QUYET-DINH-ENGINE-TRICH-THAM-SO-DUNG-CHUNG.md), gồm loại/catalog/version/tập mã yêu cầu; không lấy bản sao lõi trong M4 làm engine chung. DEMO plumbing làm được; độ chính xác KCN/nhà ở chờ mẫu/đáp án thực. |
| CRM-41-02 — Mẫu và bộ chuẩn tối thiểu | G1: upload mẫu, phát hiện placeholder, mapping, xem thử, KT kiểm/Trả lại và CFO duyệt version; G7 tối thiểu bốn cột/S6. | **REPAIR03_UI11_PASS_BROWSER_PARTIAL_PENDING.** Lượt73112/408e4f đã kết thúc; Root public-DOM11/11 đạt, browser mới kiểm mount/đổi vai, upload/G7 xuyên suốt chưa kiểm. CRM backend/parser/tests giữ nguyên; full CRM chưa nghiệm thu. M4-02A đang do Claude viết riêng. |
| CRM-41-03 — Báo giá và soạn hợp đồng | G2/G3: lịch 4 cột, nhập tỷ giá có người/ngày, in báo giá, chuyển lịch sang cùng hồ sơ soạn; xuất DOCX/PDF có revision và nguồn mẫu. | **QUEUED_AFTER_02.** Phần “theo dự án” cần bộ chuẩn tối thiểu; “theo khách” không giả là theo chuẩn. Renderer/tiền tệ/basis được bind trước phép tính. |
| CRM-41-04 — Ký kết, kiểm và hiệu lực | G4/G6 + G5 đối chiếu cơ bản: PDF bắt buộc, khóa bản ký; khai Có/Không sửa; sửa → đối chiếu bắt buộc; KT xử lý lệch/kiểm và hiệu lực luồng A; sinh nghĩa vụ, nối M1 hiện có. Luồng B tiếp nhận/trích dùng quyền duyệt hiện hành đến khi có quyết định mới. | **QUEUED_AFTER_01_03.** Mẫu phải được CFO duyệt; không tự bỏ duyệt cho luồng B. Có ca trả lại/bản ký bất biến trước code. |
| CRM-42-05 — Hoàn thiện màn hình và tra cứu/thu/file | Hoàn thiện các màn/tab còn lại, bộ lọc lưu theo người, việc K5, thu/nối/gỡ M1, hai nhãn thu CRM/công nợ Junsky theo scope khách, file soát/giao kết và lịch sử. UI từng gói trước phải đã dùng được, không đợi tới đây mới có giao diện. | **QUEUED_AFTER_CORE.** Sổ Junsky phải có scope/ngày chốt; thiếu nguồn hiện thiếu, không dùng 0. M3 chỉ tham chiếu, không tự ghi doanh thu. |
| CRM-41-06 — Lấy mẫu và mở rộng bộ chuẩn/báo cáo | G5 tự điều chỉnh, G7 màn quản trị đầy đủ, G8 report; kiểm độ chính xác theo mẫu/đáp án độc lập từng loại. | **QUEUED_POLICY_INPUT.** Tham số/cửa sổ/denominator còn chờ xác nhận; không hardcode 50/10/20 là policy đã duyệt. G5 đối chiếu bắt buộc/thủ công không bị chặn bởi nhánh tự điều chỉnh. |

Đây là thứ tự kỹ thuật đề xuất để giao tuần tự. V16a/b/c trong 41 là mốc chương trình, không phải số migration PostgreSQL. Số migration/schema và API vật lý được bind theo baseline sau M4, tránh tranh file.

## 4. Quy tắc phải giữ khi cụ thể hóa schema/handoff

- Luồng A từ mẫu: CFO duyệt **version mẫu**; KT kiểm hợp đồng đủ điều kiện mới hiệu lực. Bán hàng bấm Ký kết không tự làm hợp đồng hiệu lực.
- Luồng B ngoài mẫu: giữ CFO duyệt hiện có trong khi câu hỏi 41 §9 chưa có trả lời; không áp quy tắc department confirm của M4 sang CRM.
- Nguồn tham số Mẫu/Trích/Nhập tay phải trace được. HĐ đang soạn giữ version mẫu cũ; nâng mẫu mới là hành động có revision, không tự đổi.
- Bản ký/pháp lý, file đã xuất và liên kết tiền đã có giữ bất biến/lịch sử. “Trả lại” không được mở khóa để ghi đè bản ký; dùng bản làm việc/bổ sung/correction có quan hệ và chốt luồng này trước code gói 04.
- Tỷ giá báo giá/giá trị VND tham chiếu khác tỷ giá/căn cứ thanh toán thực. Không biến VND quy đổi thành BANK hay nối VND vào nghĩa vụ USD khi chưa có căn cứ FX.
- Kiểm mẫu hợp đồng khác lấy mẫu tham số trong engine #6. Lần không được chọn hoặc OCR lỗi không phải “khớp”; chỉ kết quả có kiểm thật mới là bằng chứng cho bộ điều chỉnh.
- Hồ sơ khai có sửa hoặc đã được chọn kiểm phải hoàn tất đối chiếu/xử lý có căn cứ trước Hiệu lực; PENDING/FAILED không phải NOT_SELECTED/MATCH. Kế toán chấp nhận một chênh lệch không được đổi kết quả khách quan DIFF thành MATCH để làm đẹp tỷ lệ.
- “Bộ chuẩn dự án” là dependency của lựa chọn Theo dự án và cờ lệch chuẩn; chưa có chuẩn thì ghi chưa có, không đánh tất cả HĐ là lệch.
- Số dư 131 theo đối tượng có thể bao gồm nhiều HĐ: không tự chia hoặc gắn toàn bộ vào từng HĐ; so chênh phải cùng grain/phạm vi/currency/ngày sổ, truy ngược đúng nguồn.
- CCCD/STK mã hóa theo kiến trúc chung; API trả dữ liệu theo quyền, không chỉ che CSS. Bán hàng không nhận full CCCD/STK qua JSON; PDF bản ký/tệp thật phải kiểm quyền riêng, giữ audit truy cập. Yêu cầu xuất văn bản có thông tin nhạy cảm cần được ràng buộc bằng policy vai/mục đích trong schema/handoff.
- Quyền theo PN + dự án + người phụ trách/khách; cùng một PN không tự có quyền thấy khách/dự án khác. Giữ file/hash/lịch sử, không xóa.

## 5. Điểm còn mở — chỉ chặn phần phụ thuộc

| Mục | Cần làm rõ/đầu vào | Xử lý khi chưa có |
|---|---|---|
| Q-B | Hợp đồng ngoài mẫu tiếp tục CFO duyệt hay chuyển KT kiểm? | Giữ quyền hiện hành; không chặn thiết kế/gói mẫu luồng A. |
| Q-SAMPLE | 50% khởi điểm, 10–100%, cửa sổ 20, bậc 20 điểm % là đề nghị; 20 HĐ toàn bộ hay 20 HĐ đã đối chiếu, gồm/không gồm ca bắt buộc? | Chưa bật bộ tự điều chỉnh; không đếm ca chưa kiểm là sạch. Tách nhánh kiểm bắt buộc/thủ công. |
| Q-RETURN | Bản ký bị trả lại: sửa mapping/nguồn hay điều khoản thực sự? Quyền thay bằng chứng/hủy sau ký? | Giữ bản ký bất biến; không mở khóa tại chỗ hoặc hủy tự động. Chốt đường xử lý trước gói 04. |
| Q-INPUT | Mẫu DOCX/PL và 2–3 HĐ đã ẩn mỗi loại, catalogue/đáp án; câu tham chiếu FX; loại cọc/phí/lãi còn thiếu. | Dùng DEMO để làm khung/contract; không gọi độ chính xác/policy thực đã đạt. Chưa có profile nhà ở thì giữ cấu hình chờ. |
| Q-UI | Danh sách cột cần bớt/thêm, hạn chờ ký/báo giá hết hạn; bố cục 17 trạng thái. | Bám các cột đề xuất của 42 khi chuẩn bị, giữ 4 điểm đã chốt. Không tự phát triển màn Việc riêng/mobile. |
| Q-PII | Bán hàng nhập thông tin khách để sinh HĐ nhưng quy tắc xem lại chỉ 4 số cuối; quyền mở/tải DOCX/PDF/preview có đầy đủ CCCD/STK cần ràng buộc cụ thể theo vai/mục đích. | Không coi che CSS hoặc mask JSON là đủ; chuẩn bị ma trận artifact/access, chốt trước nhánh xuất tài liệu thật. Mẫu gửi ra ngoài cần che đủ nhận diện/chữ ký/QR, không chỉ tên. |

Không yêu cầu Anh trả lời lại toàn bộ ngay để hoàn tất việc lập hàng chờ này. Các lựa chọn chưa rõ được mang tới bước chốt đúng gói trước coding phần ảnh hưởng.

## 6. Ma trận kiểm cho coder và kiểm độc lập

- Gói mẫu: placeholder chưa ánh xạ → chặn duyệt mẫu; trường bắt buộc thiếu trong mẫu → cảnh báo; giá trị bắt buộc trống khi xuất hợp đồng → chặn xuất; version mẫu đổi không làm đổi HĐ cũ; người không quyền không duyệt.
- Báo giá/soạn: 100% và tổng tiền trên cơ sở đã chốt; FX có người/ngày; DOCX/PDF đúng placeholder/lịch; revision/hash/file cũ còn.
- Ký/hiệu lực: thiếu PDF/khai Có Không bị chặn; replay cùng PDF không trùng; bản sửa buộc đối chiếu; OCR fail/chưa được chọn không giả khớp; KT chỉ hiệu lực đúng luồng/quyền.
- Nghĩa vụ/tiền: đúng dòng/tiền tệ/mốc, mốc chưa có ngày không quá hạn; nối/gỡ/retry/budget guards M1; không doanh thu/Junsky import tự động.
- Privacy/đối chiếu: cross PN/same PN wrong project/khách, current rights trước replay/file, không lọt full CCCD/STK; hai ô CRM/Junsky đúng grain và ngày sổ; nguồn thiếu khác 0.
- Engine: XD trước/sau cùng oracle, đủ catalog 37 và khóa JSON cũ; KCN/nhà ở actual accuracy chỉ khi có mẫu độc lập. Không dùng output hệ thống làm đáp án kỳ vọng.
- Bộ lấy mẫu: unit cases của từng bậc/cửa sổ/exempt mandatory/unknown theo policy đã chốt; lưu quyết định chọn mẫu để retry không bốc thăm lại.
- UI: 9 màn/7 tab/6 menu/17 trạng thái ở 1280–1440 px; đúng nút/role/state, xử lý async/current rights, file thực và keyboard/focus.

Trạng thái bàn giao hiện tại: **Claude đang sửa lượt02 cho lát CRM-G1/G7 tối thiểu/S6 sau kiểm độc lập có phát hiện. Chưa nghiệm thu HTTP/PG/GUI hay toàn module.** Full CRM41–42 vẫn gồm các gói phía trên. M4 Review tiếp theo giữ trong hàng chờ đã chốt; M9 giữ dừng. Lịch báo30phút đang ACTIVE theo lệnh mới của Anh, chỉ đọc tiến độ.


**CRM_REPAIR03_GUI04_PARTIAL_STOPPED_M4_02A_PREPARED — 21/10/2026.** GUI04 actual owned50390/terminal40982e: fresh DEMO18 READY, CRM/G1 loaded and role-dependent upload form observed. Browser filechooser blocked; DOCX upload/G7 end-to-end still NOT_VERIFIED. Server stopped at deadline, exit0, source pre/post unchanged; private DEMO DB/roles/files retained. Prior public-DOM11/11 remains a component result, not full GUI/module acceptance. M4 independent five XLSX materialized and Root/L11 raw ZIP/XML checks match 298 cells/51 formula caches; product/admission not run. M4-02A merged technical handoff108lines/13targets content reviewed by Root+KHO, not dispatched; launch/source staging still to bind before same-session Claude. Full M4 and CRM41–42 obligations remain pending.

## 7. Sau CRM: M2-00 rồi E1-MUA — Anh đã giao ngày 21/10/2026

1. **M2-00 — QUEUED_AFTER_CRM_1, chưa dispatch:** [Tải hóa đơn trong M2](GIAO-CODE-M2-00-TAI-HOA-DON-TRONG-M2.md), tận dụng #7; tiếp sau CRM, không chạy chồng gói đang ghi.
2. **E1-MUA — QUEUED_AFTER_M2_00_2, chưa dispatch:** [Danh mục tham số theo loại](GIAO-CODE-E1-MUA-DANH-MUC-THAM-SO-THEO-LOAI.md), tiếp sau M2-00; chỉ một product writer và kiểm phạm vi từng gói trước khi giao tiếp.

[Quyết định engine #6 dùng chung](QUYET-DINH-ENGINE-TRICH-THAM-SO-DUNG-CHUNG.md) đã được Anh chốt: M4/M2/CRM gọi ONE engine #6 hiện có tại source qua API chung; mỗi lần trích gửi tập tham số yêu cầu và gắn đúng danh mục/profile/version. Không tạo/copy engine riêng hoặc đổi danh mục toàn cục theo module. API chọn tham số đã có; các trường loại/version còn phải bind theo API thật trong handoff triển khai, không coi đã code/test.

Giữ riêng xác nhận/duyệt từng module; engine đạt không tự thành CRM/M4/M2 đạt. M4 tiếp tục toàn bộ roadmap đã chốt; M9 giữ dừng. Các handoff gốc được giữ nguyên, ủy quyền xếp hàng mới này thay câu chờ lệnh code cũ trong phạm vi hai gói, không phải phát lệnh runtime hoặc nghiệm thu.
