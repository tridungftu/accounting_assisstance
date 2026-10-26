# Sổ quyết định — P0

## A12 — QĐ-V1b-1…6 đã được Anh duyệt, giao điều chỉnh V1

Ngày 18/09/2026. Căn cứ: phần V1b trong BO-PROMPT-CODEX-VONG-2.md và chỉ dẫn “Đọc V1b Prompt codex, điều chỉnh lại bước V1”. A12 thay kết luận nghiệm thu của A11/V1: **V1 chưa đạt**; hồi cứu có mẫu sinh từ chính tháng 8 không được dùng vượt cổng. Không sửa hồ sơ trong var/vong-2/V1 hoặc gói chạy thử gốc.

| Quyết định | ĐÃ DUYỆT BỞI ANH | Phạm vi thay thế |
|---|---|---|
| QĐ-V1b-1 | known_at = max(lan_dau, lúc đọc); cột nghiệm thu chỉ lấy lan_dau < 01/08/2026; báo hai cột tách biệt | Không dùng 19/44 của hồi cứu V1 làm bằng chứng qua cổng. Thống kê quy tắc còn chứa tháng 8 là giới hạn đã biết |
| QĐ-V1b-2 | STK bậc 1/2 và ánh xạ STK: 365 ngày từ lần cuối; định danh CHAC_CHAN không hết hạn; bậc 3/4/5: 180 ngày. Giữ hạn gốc | Thay việc áp han_dung 90 ngày từ nguồn. Tham số pilot tạm, được điều chỉnh khi kế toán duyệt V4 |
| QĐ-V1b-3 | Bậc 2/4 là KEY dự phòng, không có phủ định từ khóa | Thay cách diễn giải chữ ký rỗng của script nguồn. Anh xác nhận thêm qua câu hỏi trong chat: 110 hàng bậc 1/3 thiếu từ khóa chuyển thành dự phòng bậc 2/4, giữ source_tier và hàng nguồn |
| QĐ-V1b-4 | Mẫu bậc 5 để counterparty=null, vẫn bắt buộc đối tượng; thiếu định danh thì PARTIAL | Không dùng mã đối tượng phổ biến nhất của mẫu từ khóa để đoán đối tác |
| QĐ-V1b-5 | Kéo cache Knowledge.query/expired và tra thứ tự bằng chỉ mục lên V1b; mở phiên <15 s, đề xuất 105 dòng <30 s với 133 mã | V5 vẫn giữ tối ưu đầy đủ và ngưỡng 2.027 mã; cache không đổi kết quả hoặc che sự kiện mới |
| QĐ-V1b-6 | Duyệt hướng mẫu nhiều dòng; giao triển khai cùng V2 khi có lệnh V2. V1b chỉ xuất danh sách chờ kèm mẫu và tiền | Chưa triển khai lines/Entry2 ở V1b; cần căn cứ thuế và xác nhận mapping |

Chuyển bốn loại trừ regex ra dữ liệu cấu hình/mẫu, không còn nhúng từ khóa nghiệp vụ trong hàm dựng regex chung. Hai mã ngoài danh mục do Anh xác nhận (`131.KH.ANQUAN`, `NCC.TSG`) được ghi chờ kết xuất lại, không tự thêm danh mục. Toàn bộ tri thức vận hành vẫn pending; CFO_NTD chưa duyệt từng hàng. Actor mô phỏng giữ MO_PHONG_KIEM_CHUNG. Không tự sang V2.

Migration v9 chỉ thêm index biểu thức thứ tự POLICY và token thay đổi tri thức với trigger, không thay payload nguồn hoặc sửa checksum v1–v8. Token đổi trong transaction, rollback khôi phục token cũ; token mới không tái sử dụng số thứ tự của transaction đã rollback. Cache theo category/cutoff, lọc ngày nghiệp vụ riêng, trả bản sao để người gọi không sửa cache.

**Cập nhật hiện hành — A11, 18/09/2026:** Anh đã duyệt `KE-HOACH-VONG-2.md`, trả lời QV01–QV08 và giao **V1**. Các mục V0 “chờ quyết định” dưới đây là lịch sử trước A11; cách sửa trong kế hoạch đã được duyệt, chưa đồng nghĩa từng bước đã nghiệm thu.

## A11 — phê duyệt kế hoạch V1–V6 và giao V1

| Lựa chọn | Quyết định của Anh — ĐÃ DUYỆT |
|---|---|
| QV01 | Giữ mục tiêu, kiến trúc, thứ tự V1→V6; giao V1 ngay, các bước sau chưa tự thực hiện |
| QV02 | Bậc 1→5, trong bậc theo hàng nguồn; trùng thứ tự trong khoảng hiệu lực phải chặn |
| QV03 | Cho mô phỏng C1/C2 riêng, actor `MO_PHONG_KIEM_CHUNG`; toàn bộ 809 quy tắc và 164 ánh xạ vận hành chờ duyệt |
| QV04 | Đo hồi cứu T8 bằng tri thức hiện có, giữ known_at thực; không gọi là ngoài mẫu |
| QV05 | Tên đối ứng chỉ là điều kiện bậc 3/4; không thành khóa cứng; xung đột với định danh đã xác minh phải chặn |
| QV06 | CASE không vượt cổng dữ liệu; CASE mâu thuẫn chờ người |
| QV07 | han_dung là ngày cuối còn hiệu lực; valid_to = ngày kế tiếp, giữ raw |
| QV08 | V1 chỉ trình thiết kế mẫu nhiều dòng, chưa triển khai |

Đính chính của Anh: Entry1 **17 cột gồm ErrorText**; V6 dùng đúng mẫu này. TU-DIEN đã được thay bằng **9 sheet, có 0B và 3B · KHÓA CỨNG**; đọc lại tại V4, không ghi đè kết quả kiểm kê V0 của phiên bản trước. **Chưa nhập Junsky**: file đang có là file xuất tham khảo, không là bằng chứng nhập thành công. Được cài offline `xlrd 2.0.x`; khóa `xlrd==2.0.2` trong nhóm dependency `source-xls` của pyproject, chưa cần cài cho V1. Actor duyệt tri thức vận hành là **CFO_NTD**; tên actor này không tự cấp quyền duyệt một hàng cụ thể.

V1 tiếp tục giữ schema SQLite v8: thay hợp đồng payload, validation và lựa chọn; không có DDL/migration nên không sửa checksum các migration cũ. Kiểm tra thứ tự nằm trong giao dịch BEGIN IMMEDIATE, áp dụng cả hàng chờ để từ chối lô va chạm. Mọi kiểm chứng dữ liệu thật ở `var/vong-2/V1/`, không đưa vào tests/fixtures.

Ngày lập: 17/09/2026. Cập nhật sau phản hồi của Anh: **“Đồng ý các khuyến nghị, hãy bắt đầu coding”.** Anh đã duyệt phương án khuyến nghị và cho bắt đầu M1 theo A07 bên dưới. Bản 1.2 vẫn được giữ nguyên làm nguồn lịch sử; phê duyệt thiết kế không thay cho xác nhận dữ liệu thực hoặc nghiệm thu kế toán.

## 1. Cách đọc trạng thái và thẩm quyền

- **ĐÃ DUYỆT / GIỮ NGUYÊN:** có chỉ dẫn trực tiếp của Anh trong nhiệm vụ hiện tại, hoặc bản 1.2 ghi nhận quyết định gốc. Ghi rõ loại bằng chứng; tài liệu ghi nhận không thay cho biên bản chưa tìm thấy.
- **ĐỀ XUẤT:** phương án để xem xét, chưa được áp dụng vào sản phẩm.
- **CHỜ QUYẾT ĐỊNH:** có lựa chọn/ràng buộc ảnh hưởng phần sắp làm; chỉ rõ người chốt và hạn phụ thuộc. Khuyến nghị trong dòng này vẫn là đề xuất.
- **ĐÃ DUYỆT MỚI:** chỉ được ghi sau phản hồi rõ của Anh/người được Anh giao thẩm quyền, kèm ngày, phạm vi, bằng chứng và quyết định bị thay thế nếu có. A07 là phê duyệt mới hiện tại.

Anh chốt mục tiêu, phạm vi, kiến trúc và thay đổi quyết định gốc. Kế toán trưởng xác nhận nghiệp vụ, tiền/dấu, danh mục/TK/hiệu lực và đáp án; IT đề xuất kỹ thuật và chứng minh test. Chưa tự gán tên cá nhân hoặc xem sự im lặng là đồng ý. Khi duyệt, thêm bản ghi; không sửa lịch sử thành như thể đề xuất đã được duyệt từ trước.

## 2. Những nội dung đã có căn cứ giữ nguyên

| ID | Nội dung | Trạng thái / căn cứ | Giới hạn |
|---|---|---|---|
| A01 | Đúng sáu module M1–M6; một Python, SQLite, Excel; runtime offline; PLHN xử lý sao kê | ĐÃ DUYỆT / GIỮ NGUYÊN — yêu cầu trực tiếp của Anh ở nhiệm vụ này; phạm vi bản 1.2 §0/§3 | Chỉ được lập kế hoạch lúc này, chưa được coding |
| A02 | Hóa đơn/Base là bằng chứng; Junsky qua Excel; không UI/API/AI runtime, không tự duyệt/ghi sổ | GIỮ NGUYÊN — bản 1.2 §0/§3/§8 và kế hoạch module §1 | Mở rộng hóa đơn/đơn vị khác phải có kế hoạch và quyết định riêng |
| A03 | Xuất 131/331 + danh mục trước mỗi phiên; một phiên hoạt động; phải chốt cuối phiên | Bản 1.2 §4.4 ghi nhận Anh chốt 17/09/2026; chưa tìm thấy biên bản dẫn chiếu | Giữ nguyên chủ trương; cách chứng minh độ mới, đã ghi sổ và khóa tháng đang có đề xuất sửa |
| A04 | Năm nhóm tri thức, trạng thái vận hành tách riêng; version/hiệu lực; point-in-time; người thắng máy; thống kê dẫn xuất | GIỮ NGUYÊN — bản 1.2 §0/§4/§5 | Không biến số liệu khảo sát thành bằng chứng nghiệm thu hiện tại |
| A05 | Tất cả ngưỡng là cấu hình; Python 3.11+ và danh sách thư viện hạn chế; pilot tắt duyệt nhanh theo lô | GIỮ NGUYÊN — bản 1.2 §5/§6/§8 | YAML có xung đột dependency D05; giá trị ngưỡng kế toán phải do người có thẩm quyền xác nhận |
| A06 | P0 chỉ tạo bốn tài liệu trong docs, dừng trước coding để Anh thống nhất | ĐÃ DUYỆT — yêu cầu trực tiếp của Anh; P0 đã hoàn thành | Giới hạn dừng trước coding được cập nhật bởi A07; không thay đổi nội dung đã bàn giao P0 |
| A07 | Duyệt các khuyến nghị C01–C06 và phương án D01–D10; bắt đầu coding M1 theo nhịp lõi/fixture rồi mẫu thực | ĐÃ DUYỆT MỚI — Anh, 17/09/2026, phản hồi trực tiếp “Đồng ý các khuyến nghị, hãy bắt đầu coding” | Cho làm M1; chưa triển khai M2–M6 hoặc vận hành Junsky. Các dữ kiện, tên đầu mối, mẫu thực, mapping và đáp án kế toán còn thiếu vẫn phải được cung cấp/xác nhận |

Nguồn: [bản 1.2](../KE-HOACH-PHAN-MEM-KHO-TRI-THUC.md), [kế hoạch module](../KE-HOACH-MODULE-VA-LO-TRINH.md), [dữ liệu cần chốt](../DU-LIEU-VA-QUYET-DINH-CAN-CHOT.md). Chưa có `AGENTS.md` trên đĩa ở phạm vi đã kiểm tra; áp dụng nội dung Anh cung cấp trong hội thoại.

## 3. Rà D01–D10

Các phương án khuyến nghị D01–D10 dưới đây đã được Anh duyệt theo A07. Bảng giữ nguyên đối chiếu với bản 1.2 và các yêu cầu xác nhận nghiệp vụ/dữ liệu trước phần phụ thuộc. Việc đã duyệt bổ sung sổ, chẳng hạn, chưa chứng minh Junsky có xuất được bộ trường yêu cầu. [HOP-DONG-DU-LIEU.md](HOP-DONG-DU-LIEU.md) là hợp đồng thiết kế được thống nhất; phần triển khai thực tế được ghi riêng.

| ID | Mâu thuẫn hoặc lỗ hổng so với bản 1.2 | Phương án khuyến nghị và lý do | Phương án khác / giới hạn | Người chốt; hạn |
|---|---|---|---|---|
| D01 | §4.4/§7 E4 suy “HĐ đóng = đã nhập”; số dư không xác nhận bút toán nào, TK hay dự án nào làm số dư đổi. Nhóm B bị xem là nhãn tốt mà chưa có kiểm tra độc lập | Xác minh bằng chứng từ/bút toán và quan hệ nguồn; đánh dấu từng trường. Thiếu chứng cứ giữ CHƯA XÁC MINH, không học trường đó; ghi tay là ứng viên nhãn | Có thể chỉ đối soát số dư và tắt học phần không xác minh. Không báo độ đúng bút toán từ biến động số dư | Anh + kế toán trưởng; thống nhất định hướng khi duyệt thiết kế, chốt tiêu chí trước M5 |
| D02 | §4.4 lấy hash khác làm một dấu hiệu bắt buộc về độ mới; file đổi metadata có thể đổi hash, file vừa xuất lại có thể cùng hash. Điều kiện as_of không chứng minh Junsky chưa chứa sao kê | Xét pháp nhân, as_of, phạm vi đầy đủ, exported_at, phiên bản danh mục và tổng; hash dùng nhận dạng. Cùng nội dung cần bằng chứng lần xuất/xác nhận không thay đổi, không chỉ một ô “có” | Nếu Junsky thiếu metadata, dùng manifest kế toán ký + tổng báo cáo; mức đảm bảo và giới hạn phải công bố, không gọi máy biết chắc “mới nhất” | Anh/IT + kế toán trưởng; contract M1, cổng thực M3 |
| D03 | Gói §4.4 có 131/331 và danh mục nhưng thiếu chứng cứ phí NH/lãi vay, bút toán 112 và TK/dự án để xác minh | Bổ sung sổ 112/NKC hoặc danh sách chứng từ đủ trường, ID dòng và phạm vi đối soát. Là thành phần bổ sung của nguồn Junsky trong M1, không tạo module thứ bảy; không bắt buộc API/kết quả import trực tiếp | Nếu không xuất được, giữ adapter chờ; lõi fixture vẫn làm sau duyệt, nhưng liên kết/kiểm tra đã ghi sổ/nhãn liên quan không được nghiệm thu. Năm nhóm snapshot vẫn giữ | Anh duyệt mở rộng yêu cầu dữ liệu; kế toán trưởng/Junsky xác nhận; schema M1, sử dụng M2/M3/M5 |
| D04 | §3 khóa sổ là số chứng từ; §4.1 công nợ theo phiên–đối tượng–số HĐ; thiếu pháp nhân/TK/tiền tệ/ID dòng. Tham chiếu NH cũng chưa được chứng minh duy nhất | ID nội bộ + khóa nguồn được kiểm chứng theo namespace; định danh dòng tách định danh file; HĐ hợp nhất XML/bảng kê; nghi trùng không tự gộp. Tránh mất giao dịch cùng ngày/tiền | Dùng ngày–tiền–tên chỉ để tìm ứng viên, không làm khóa cứng. Nếu không có ID ổn định, kế toán giải quyết collision trước khi phần đó đủ điều kiện dùng | Anh/IT chốt nguyên tắc; kế toán trưởng xác nhận ý nghĩa khóa; M1 |
| D05 | §8 chọn `cau_hinh.yaml` nhưng PyYAML không nằm trong danh sách thư viện trực tiếp; chưa tìm thấy file YAML hoặc code phụ thuộc | TOML + tomllib theo Python 3.11+, mọi ngưỡng/mã vẫn ở cấu hình. Không có config hiện hữu để phải di chuyển | Giữ YAML và duyệt PyYAML nếu đội IT đã có chuẩn YAML; không tự viết parser YAML riêng | Anh/IT; trước cấu hình M1 |
| D06 | Snapshot đủ mới có thể đã bao gồm chính khoản sao kê đang xử lý; số còn mở/khóa trong phiên không ngăn tái xuất xuyên phiên | Kiểm tra quan hệ sao kê–bút toán, quyết định/batch chưa xác minh và allocations xuyên phiên. Nghi đã ghi sổ thì chặn xuất để xác minh | Không hạ kiểm tra về “hash file chưa gặp”; nếu không đủ chứng cứ chỉ cho rà soát thủ công trường hợp liên quan, không tự xuất | Kế toán trưởng xác nhận quy trình; IT thiết kế; M3 trước xử lý thật |
| D07 | §3 nói backup = copy file; copy DB đang ghi có thể thiếu trạng thái; §4.4 chốt gồm ghi file và DB nhưng hai bên không có một transaction chung | Backup bằng SQLite backup API hoặc đóng toàn bộ kết nối trước copy; restore thử. Xuất theo manifest/checksum và trạng thái phục hồi; chỉ đánh dấu đã xuất sau khi file hoàn chỉnh được kiểm tra | Đóng DB để backup đơn giản hơn nhưng gián đoạn phiên. Local recovery không chứng minh Junsky chưa import file; trường hợp không rõ phải đối chiếu trước thử lại | Anh/IT; phần backup M1, batch/recovery M4 |
| D08 | §4.4 gọi phiên cuối tháng là khóa tháng với chênh = 0, nhưng batch vừa xuất chưa xuất hiện trong snapshot đầu vào; có nguy cơ khóa trước khi biết kết quả | Sau import có lượt xác minh cuối gắn vào phiên đã chốt, lấy snapshot + chứng từ. Chỉ khóa khi mọi chênh thuộc kỳ xử lý về 0, không batch chờ/mục chưa xác minh; xét từng HĐ, không bù chênh | Chờ lần đối soát tiếp theo và chưa khóa kỳ. Giải trình được không thay điều kiện bằng 0; nếu muốn ngoại lệ khóa cần Anh/kế toán trưởng quyết định riêng | Anh + kế toán trưởng; M5/M6. Lượt xác minh cuối là đề xuất quy trình, không phải phiên đề xuất mới |
| D09 | §4.2/§8 có hiệu lực và point-in-time nhưng chưa tách lúc nghiệp vụ, lúc biết, lúc duyệt/xác minh; dùng lịch sử nạp hôm nay có thể rò đáp án tương lai | Lưu business_date, known_at và chứng cứ, loaded_at, [valid_from, valid_to), approved_at/verified_at/eligible_at. Replay phải qua cả thời điểm hiệu lực và thời điểm sẵn có | Không chứng minh known_at thì chỉ báo cáo hồi cứu có giả định; không gán thời điểm nghiệp vụ thành thời điểm biết | Anh/IT chốt contract; kế toán trưởng xác nhận metadata; M1/M2/M6 |
| D10 | §4.4 giữ chỗ chỉ ở SQLite, không ngăn người ghi tay Junsky trong khi mở phiên; kiểm tra số còn mở trên snapshot cũ không đủ | Chốt cửa sổ không ghi tay các đối tượng/phạm vi liên quan từ khi xuất snapshot đến hoàn tất import; nếu có thay đổi phải xuất lại, đối soát và duyệt lại phần bị ảnh hưởng trước chốt/xuất | Cho phép ghi tay nhưng bắt buộc lấy bộ kiểm tra mới trước xuất, và bảo đảm cửa sổ ngắn từ lần kiểm tra cuối đến import; nhiều công hơn. Không có cửa sổ tin cậy thì không cam kết tránh đua cập nhật | Kế toán trưởng + Anh chốt cách vận hành; M3/M4 |

D01/D03 đã được duyệt về nguyên tắc; phần bằng chứng thực tế và tiêu chí xác minh chi tiết vẫn cần kế toán xác nhận trước M5. Không suy luận “đóng HĐ = đúng bút toán” và không nghiệm thu theo chuẩn yếu hơn chỉ vì thiếu dữ liệu.

## 4. Các điểm khác cũng cần ghi nhận

| Điểm | Nhận định / khuyến nghị | Trạng thái / hạn |
|---|---|---|
| Bảy gói Python ở §3 so với sáu module | Không phải mâu thuẫn nghiệp vụ: sáu gói giao việc, nhiều package kỹ thuật trong một ứng dụng. M6 bao trùm kiểm chứng, không tách service | Giữ sáu module theo yêu cầu hiện tại |
| “60% đã có”, tỷ lệ phủ/đúng và thời gian E2 một ngày | Chưa có script/dữ liệu. Đo lại; không dùng để cam kết. E2 cần sổ 112 và mã tham chiếu sao kê thực | CHỜ DỮ LIỆU; M1/M2 |
| E1 ở §7 còn nói xuất hàng tháng; §4.4 cập nhật trước mỗi phiên | Giữ nhịp mỗi phiên theo phần cập nhật 1.2. Chưa xác nhận layout và độ chi tiết HĐ; không tự hạ xuống đối tượng dù §7/§9 nêu fallback | GIỮ nhịp phiên; mức hạ cần Anh duyệt riêng trước M3 |
| Giai đoạn 1 ở bản gốc yêu cầu chạy ngầm hằng ngày | Đề xuất theo nhịp có snapshot đạt cổng; chỉ chạy hằng ngày khi kế toán cung cấp và kiểm soát được hằng ngày | CHỜ QUYẾT ĐỊNH với D10, trước G1 |
| TT99/TK 2026 và các ngưỡng 30 triệu/5 triệu | Chưa có sổ 2026, bảng cũ–mới hoặc chính sách được duyệt; không coi đây là tư vấn pháp lý hay giá trị mặc định để coding | Kế toán trưởng xác nhận chính sách/mốc hiệu lực trước M2/M3; chưa thực hiện thẩm định pháp lý trong P0 |
| Ba chỉ số từ khóa, bảy mã lý do, sáu phần báo cáo | Chưa có định nghĩa nguyên bản; để chờ, không dựng bộ mới rồi gọi là đã chốt | M2/M4/M5/M6 theo phần sử dụng |
| Tập vàng 200–300 và “9 tháng học, 3 tháng thử” | Cần nguồn có thời điểm; tách development/holdout/mẫu mù. Không dùng mẫu đã nhìn đáp án để chứng nhận cải thiện ngoài mẫu | ĐỀ XUẤT phương pháp; chốt kế hoạch đánh giá trước G0 |

## 5. Những lựa chọn tối thiểu để giao M1

Sáu lựa chọn C01–C06 đã được Anh đồng ý theo A07. Bảng lưu phương án để đối chiếu; không yêu cầu Anh duyệt lại thao tác trong phạm vi đó. M1 hiện thực hiện lõi fixture; chi tiết adapter chưa biết tiếp tục chờ mẫu.

| ID | Nội dung cần chốt | Phương án khuyến nghị | Phương án khác và trade-off | Người chốt |
|---|---|---|---|---|
| C01 | Giao việc M1 đến mức nào khi chưa có mẫu | Cho làm lõi + fixture; adapter thực triển khai tuần tự khi có mẫu và mapping được xác nhận. Vẫn giữ đủ năm nhóm nguồn trong đích M1 | Chờ đủ mẫu rồi bắt đầu: ít sửa giả định hơn nhưng IT chờ toàn bộ | Anh đã duyệt coding M1 theo A07; chưa cho vận hành thực |
| C02 | Cấu hình D05 | TOML + tomllib; lý do: không có YAML/code cũ cần giữ, phù hợp danh sách dependency | YAML + PyYAML nếu có chuẩn IT sẵn; cần duyệt thêm dependency | Anh/IT |
| C03 | Tiền tệ và dấu | Pilot xử lý VND nếu kế toán xác nhận bộ sao kê chỉ cần VND; Decimal khi tính, INTEGER theo đơn vị đã duyệt khi lưu. Sao kê thu dương/chi âm; số dư công nợ theo Nợ–Có, giữ Nợ/Có gốc | Có ngoại tệ: bổ sung currency/scale/tỷ giá và quy tắc đánh giá, ước lượng lại. Dù chọn VND, dòng khác tiền tệ vẫn phải giữ raw/báo ngoài phạm vi, không tự quy đổi | Kế toán trưởng xác nhận thực tế/quy tắc; Anh duyệt phạm vi |
| C04 | Gói nguyên tắc dữ liệu D02/D04/D07/D09 | Duyệt ID nội bộ + khóa nguồn kiểm chứng; metadata/known_at riêng; raw bất biến, transaction và backup nhất quán. Trường thiếu/khóa mơ hồ phải báo chờ | Có thể hoãn chi tiết khóa theo layout tới mẫu thực; không hoãn chống trùng/tiền/thời gian đến sau khi nạp dữ liệu thật vì làm lại khó | Anh/IT; kế toán trưởng xác nhận ý nghĩa nguồn |
| C05 | Mức công nợ và bổ sung bằng chứng D03 | Giữ công nợ theo HĐ; đưa sổ 112/NKC hoặc chứng từ đủ trường vào yêu cầu nguồn Junsky. Mẫu thật mới quyết định mapping; hỗ trợ schema bằng chứng D01 từ đầu | Nếu nguồn chỉ có tổng đối tượng, giữ adapter chờ hoặc trình giảm phạm vi riêng. Không tự suy HĐ và không lấy số dư làm nhãn | Anh + kế toán trưởng; Junsky xác nhận khả năng xuất |
| C06 | Cách nghiệm thu, đầu mối và bộ mẫu M1 | Chỉ định một đầu mối dữ liệu/đáp án kế toán và IT; duyệt hai mức fixture/mẫu thực, catalog layout và tổng kiểm soát theo HIEN-TRANG §6. Tính lại công khi nhận mẫu | Nếu chưa có đầu mối/mẫu, chỉ nhận bàn giao lõi fixture; không hứa ngày M1 đầy đủ hoặc pilot | Anh phân công; kế toán trưởng xác nhận đáp án |

**Chi tiết còn cần xác nhận trước phần phụ thuộc:** tiêu chí xác minh từng trường D01 trước M5; cách áp dụng xuyên phiên D06 trước M3; lịch/người thực hiện cửa sổ Junsky D10 trước M3/M4; thủ tục khóa tháng D08 trước M5/M6; E5 trước G1; giá trị ngưỡng đúng/phủ/rủi ro sau Baseline nhưng trước cổng tương ứng. Không hiểu A07 thành đã nhận được các dữ kiện hoặc phân công chưa được nêu.

Đối chiếu với Q1–Q10 trong tài liệu đầu vào: Q1 giữ theo A01 và cụ thể hóa C01; Q2=C02; Q3=C03; Q4=C05; Q5=D01/D03; Q6 chờ kế toán trước M2/M3; Q7=D10; Q8=E5; Q9=cổng chất lượng; Q10=D08. Không đổi tên Dxx thành Qxx hoặc coi hai danh sách là một bộ quyết định đã duyệt.

## 6. Các trường phải lấy từ Junsky, không tự dựng mapping

1. Bộ xuất thực: tên file/sheet/cột, kiểu/độ dài, phạm vi/thời điểm, tổng kiểm soát; có công nợ theo HĐ hay chỉ theo đối tượng; tạm ứng/không HĐ, tiền tệ và dấu thể hiện ra sao.
2. Sổ/chứng từ: ID chứng từ và dòng có ổn định giữa lần xuất không, trường nào có mặt (TK, HĐ, đối tượng, dự án/khoản mục, số tiền), cách thể hiện hủy/đảo và batch tham chiếu; sổ 112 có mã giao dịch NH không.
3. `EntryID`: ai sinh, phạm vi duy nhất, có tái dùng khi sửa/import lại không, import lần hai có bị chặn không.
4. `DebtID`: tham chiếu đối tượng/HĐ/chứng từ nào, nguồn ID, có bắt buộc và cách chia nhiều HĐ/trả một phần.
5. `CB_tmpEntry2`: khi nào bắt buộc, quan hệ với Entry1, cột/kiểu/độ dài/thứ tự; file đã nhập thành công và lỗi thật.

Đây là danh sách yêu cầu thông tin, không phải lệnh gửi thư hay thao tác Junsky. Hiện chưa tìm thấy mẫu hoặc câu trả lời trong thư mục.

## 7. Nhật ký phê duyệt mới

**A09 — 18/09/2026, Anh:** “Hãy tạo luôn giao diện html để tôi nhập dữ liệu trên đó cho tiện”. Anh cho bổ sung giao diện HTML chạy cục bộ để nhập file trực tiếp. Đây là cập nhật rõ ràng cho giới hạn **không UI** tại A02; phần giao tiếp HTTP chỉ bind `127.0.0.1` trong cùng ứng dụng Python, không công bố dịch vụ ra mạng. Giữ đúng sáu module: tiếp nhận file thuộc M1, giao diện vận hành/kiểm chứng dùng chung thuộc M6. Giữ SQLite, Excel, offline, không AI runtime.

Phạm vi A09 thực hiện: chọn tệp/thư mục, gắn nguồn/pháp nhân/kỳ, lưu nguyên byte và phiếu tiếp nhận, chống trùng hồ sơ, tra cứu/tải bản gốc; khu mô phỏng riêng nối với adapter và Store hiện hữu. Chưa có mẫu thực nên file thật giữ `RECEIVED_WAITING_ADAPTER`, `normalized=false`, `posted=false`. A09 không phê duyệt mapping Junsky, không biến receipt thành chứng từ, không xác nhận chính sách kế toán hay cho ghi sổ thực. Quyết định gốc trong bốn tài liệu nguồn giữ nguyên để truy vết.

**A08 — chỉ dẫn tiếp theo của Anh:** “tôi sẽ kiểm thử tay ở bước sau, hay hoan thien va tu kiem thu tat ca module con lai”. Phạm vi coding được mở rộng từ M1 sang toàn bộ M2–M6, triển khai tuần tự và tự kiểm thử xuyên module. Không phải chờ Anh chạy kiểm thử tay mới tiếp tục. Vẫn giữ giới hạn dữ liệu thật/mapping Junsky/chính sách kế toán chưa được cung cấp; tự kiểm thử không thay nghiệm thu kế toán hoặc quyền import/vận hành thật. Khi hướng dẫn PowerShell, luôn kèm `Set-Location -LiteralPath` với đầy đủ đường dẫn dự án.

| Ngày / ID | Người và bằng chứng | Phạm vi áp dụng | Còn chờ |
|---|---|---|---|
| 17/09/2026 — A07 | Anh; nguyên văn: “Đồng ý các khuyến nghị, hãy bắt đầu coding” | Triển khai M1 theo C01–C06; TOML, tiền chính xác, khóa nguồn, metadata/known_at, raw/staging/transaction và backup theo phương án đã trình. D01–D10 được chấp thuận về hướng thiết kế | Mẫu thực; xác nhận phạm vi tiền tệ/dấu trên nguồn thật; mã pháp nhân/MST; người cung cấp và ký đáp án; schema/khả năng xuất Junsky; chi tiết các cổng sau |
| 17/09/2026 — A08 | Anh; nguyên văn đã ghi ở đầu mục 7 | Hoàn thiện code và tự kiểm thử toàn bộ M2–M6; không chờ kiểm thử tay. Giữ một ứng dụng/sáu module/offline/SQLite/Excel/pilot sao kê | Kiểm thử tay theo lịch Anh; dữ liệu/mapping thật, chính sách và ngưỡng có giá trị cụ thể, nghiệm thu kế toán, quyền vận hành |
| 18/09/2026 — A09 | Anh; nguyên văn nêu trên | Bổ sung giao diện HTML local, nhập và giữ file gốc, khu thử fixture tách biệt; thay giới hạn không UI của A02 trong phạm vi này | Bộ đọc/mapping thật và nghiệm thu kế toán; chưa mở vận hành hạch toán/Junsky |

Cấu hình ban đầu dùng `PLHN_FIXTURE`, VND/scale 0 và môi trường `fixture`; đây là dữ liệu giả lập thực hiện phương án được duyệt, không phải mã Junsky hoặc xác nhận kế toán về dữ liệu thực. A08 đã cho coding M2–M6; vẫn chưa cho import thực/vận hành pilot. Các sự kiện `AUTOMATED_FIXTURE_*`, policy/ngưỡng fixture và chốt tháng mô phỏng không được ghi nhận thành quyết định của Anh hoặc kế toán trưởng.

## 8. Vòng 2 — tiếp nhận V0 ngày 18/09/2026

**A10 — ĐÃ GIAO V0:** Anh yêu cầu đọc và triển khai bộ prompt vòng 2, sau đó “tiếp tục chạy”. Cách dùng/V0 yêu cầu kiểm kê, chạy lại, trình phương án và dừng trước sửa sản phẩm. A10 cho thực hiện V0; **chưa phê duyệt V1–V6 hoặc tri thức vận hành**. A07–A09 và D01–D10 không bị thay thế ngầm; giao diện HTML A09 vẫn trong phạm vi.

Đã tìm thấy nguồn thật ngoài thư mục dự án. Các câu “chưa có mẫu” trong hồ sơ vòng 1 là lịch sử: hiện có mẫu Entry1/2, còn thiếu xác nhận ý nghĩa cột và quyền vận hành. Chỉ dẫn giải nén “tại chỗ” xung đột với cấm sửa thư mục thử gốc: V0 giải nén bản sao vào `var/vong-2/V0/ban-sao-goi-goc/`, giữ nguyên gốc.

### 8.1. Tám phát hiện — tất cả CHỜ QUYẾT ĐỊNH VÒNG 2

“Xác nhận” bên dưới là kết luận kiểm tra, không phải Anh đã duyệt cách sửa. Dòng code tham chiếu thuộc bản được giữ hash tại V0. Kế hoạch triển khai/migration/test chi tiết: [KE-HOACH-VONG-2.md](KE-HOACH-VONG-2.md).

| ID / mục báo cáo | Kết luận và bằng chứng file/dòng | Phương án tối thiểu đề xuất | Hợp đồng/schema và bước |
|---|---|---|---|
| V0-F01 / 6.1 | **Xác nhận có giới hạn.** `de_xuat/engine.py:56–69` định danh đối tượng nhưng POLICY chỉ lọc chiều/từ khóa. `:80–82` đã giữ ưu tiên trường định danh cứng, không được kết luận cơ chế đó chưa có. CASE được khai báo tại `tri_thuc/service.py:11` nhưng engine không dùng. Excel có 747 mẫu bậc 1–4, 62 bậc 5; JSON thử thực chỉ phát 52 POLICY sau lọc | Trigger định danh/regex/kết hợp, thứ tự trong phân vùng; CASE trước mẫu, vẫn giữ cổng dữ liệu | V1: version payload POLICY/CASE, validation thứ tự theo hiệu lực; migration mới nếu cần lưu ràng buộc thứ tự |
| V0-F02 / 6.2 | **Xác nhận.** `de_xuat/engine.py:69,91` dùng substring, thiếu regex/loại trừ. Đ→D đã đúng tại `ha_tang/primitives.py:47`, test `tests/test_m1.py:56` | Regex có ranh giới/loại trừ và validation; giữ chuẩn hóa đang đúng; test 5 bẫy cả ca dương/âm | V1: version biểu thức; không đổi contract nguồn, không coi mọi từ khóa cũ là regex đã duyệt |
| V0-F03 / 6.3 | **Xác nhận.** `nguon/fixture.py:167–187` thiếu thuế riêng, bắt tổng dòng bằng tổng header. Converter cũ thêm dòng thuế và bỏ chi tiết 4 hóa đơn; không chứng minh XML gốc sai | Tách trước thuế/thuế/tổng, tính chất dòng, dung sai và quan hệ điều chỉnh; bỏ dòng thuế giả | V2: contract v2 + migration HĐ/dòng/quan hệ, giữ raw/audit |
| V0-F04 / 6.4 | **Xác nhận lỗi 5 cặp, bác bỏ diễn giải không thể gộp mọi nguồn.** So header 5 cặp chỉ khác `source_status`. Trường vào core tại `nguon/fixture.py:169`, hash khác bị chặn ở `ha_tang/store.py:142`; file rollback tại `:117–135`. Core giống đã gộp/thêm evidence ở `:140–150,165`, test `tests/test_m1.py:186` đạt | Trạng thái theo nguồn nằm trong evidence; header chung giữ khóa. Khác tiền quá dung sai quarantine chứng từ, tiếp tục chứng từ hợp lệ | V2: migration core/evidence giữ ID/known_at; trạng thái mâu thuẫn và promote/báo cáo cấp chứng từ |
| V0-F05 / 6.5 | **Xác nhận.** `tri_thuc/service.py:12,136–159` xuất/nhập payload_json/evidence_json, chưa là từ điển người đọc được | Cột nghiệp vụ/duyệt/ghi chú; JSON kỹ thuật ẩn; kiểm tra revision, tạo event cho thay đổi | V4: version workbook/provenance; tận dụng event hiện có, migration nếu cần thêm bảng/cột |
| V0-F06 / 6.6 | **Xác nhận 105×501 + header = 52.606 hàng.** `xuat/service.py:34–45,60` lặp mọi OPEN_ITEM cho mỗi proposal. Workbook vẫn đọc được trong V0; không khẳng định mọi máy đều không mở nổi | Ứng viên theo đối tượng, top N cấu hình (đề xuất 10), CONG_NO_KHAC và kiểm tra lại khi nhập | V5: version workbook/baseline, chưa cần DDL nếu không phát sinh bảng; mục tiêu <500 KB |
| V0-F07 / 6.7 | **Xác nhận trạng thái hard-code** ở `de_xuat/engine.py:51`, `hoc/service.py:66,175`, `tri_thuc/service.py:173`. **Không thấy phân vùng PLHN_FIXTURE hard-code trong nghiệp vụ:** engine lấy partition từ policy ở `:85,98`; literal trong bộ tạo fixture. Khóa fixture ở `ha_tang/config.py:26` là giới hạn môi trường chủ đích | Mapping trạng thái nguồn→trạng thái chuẩn; tách fixture/that, giữ khóa xuất; không thay toàn cục chuỗi “fixture” | V2/V3/V5: contract trạng thái/cấu hình/binding DB, migration tương thích lịch sử |
| V0-F08 / 6.8 | **Xác nhận N+1.** `tri_thuc/service.py:62–80` quét version, 2 SQL duyệt/thu hồi cho hàng đủ điều kiện và vòng APPROVE bổ sung; mô tả “2 SQL/phiên bản” chưa hết chi phí. `trang_thai/service.py:47` query theo từng bank. V0 mới đo 133 mã; mốc 2.027 mã trong báo cáo cũ chưa đo lại | Snapshot/cache theo cutoff/ngày, invalidation theo event; đo trước khi chọn index | V5: cache RAM hoặc migration index/view khi cần; <10 s/105 đề xuất, <30 s/62×2 với đủ 2.027 mã |

**V0-F09 — bộ chấm, CHỜ QUYẾT ĐỊNH:** `kiem_chung/service.py:22–59` vẫn chấm fields khi NONE; `de_xuat/engine.py:143–146` chuyển NONE nhưng giữ fields giải thích. V5 tách không đề xuất/sai, không chấm fields NONE, thêm phủ theo tiền; version bộ chấm mới và tính lại các mốc. Không diễn giải số đúng C3 là độ đúng đề xuất vận hành.

### 8.2. Mâu thuẫn và phần không tự chốt

- **Phê duyệt:** V1 ghi DE_CU/CHAC_CHAN “duyệt”; V4/quy ước chung yêu cầu chờ duyệt. Đề xuất kho vận hành nhập tất cả chờ. Mô phỏng C1/C2 có actor/kho riêng và quyền rõ; các approval trong runner V0 chỉ tái hiện kịch bản đã cấp, không phải quyết định kế toán.
- **Thời gian:** converter cũ gán known_at/approval hồi cứu, xếp mẫu theo thống kê có T8, chọn 133 mã có tham chiếu T8, lấy bank_reference sổ từ Tập chuẩn. Kết quả tái hiện không phải backtest ngoài mẫu sạch. Đề xuất benchmark hồi cứu riêng, không lùi ngày để vượt cutoff.
- **Phiên bản tài sản:** README ghi 873/177, workbook thực là 809/164. Script PDF hiện viết 7 sheet, workbook SAO-KE-2-NAM có 9 sheet; chưa chứng minh script tái tạo được workbook. TU-DIEN không có sheet 3B; 149 NCC là ứng viên có cột duyệt, chưa thành định danh đã xác minh.
- **Mẫu Junsky:** V6 ghi Entry1 16 cột, file thật có 17 gồm ErrorText; Entry2 37. Đề xuất giữ template NCC. Entry2 đối ứng/đầy đủ, EntryID, DebtID/EntryDM, BankID/CashflowID còn phải xác nhận, không biến suy luận trong hướng dẫn thành mapping sản phẩm.
- **Bằng chứng nhập:** file JUNSKY-CHI/THU-T8 có trên đĩa nhưng việc script dựng file không chứng minh đã nhập thành công. Cần xác nhận/log/sổ đối chiếu trước gọi là chuẩn đã nhập.
- **Quyền xuất:** V6 cần quyền tạo file shadow riêng để nghiệm thu, trong khi import/vận hành thật tiếp tục khóa. Không hiểu V6 thành cho phép import Junsky.
- **Nguồn công nợ/phạm vi:** 501 OPEN_ITEM JSON là tái dựng, kỳ khóa giả định, POLICY JSON không yêu cầu công nợ. File công nợ thật cần as_of/snapshot do người khai. Đề xuất chuyển trọng tâm sang hóa đơn trong tài liệu phân hành không thay pilot sao kê.

Tám lựa chọn, khuyến nghị và mặc định an toàn tại [kế hoạch mục 9](KE-HOACH-VONG-2.md#9-các-lựa-chọn-cần-anh-duyệt-trước-v1) đều **chờ Anh/kế toán trưởng**; không tự chuyển thành “đã duyệt”.

## A13 — giao liên tục V2 → V6 và R1

Anh đã giao thực hiện liên tục V2–V6, sau đó R1; bỏ cổng ngưỡng chất lượng tháng 8 trong từng V. Mỗi V phải chạy lát cắt tháng 8 ở hai cột hồi cứu/không rò rỉ, chỉ kiểm hồi quy kỹ thuật và ghi `var/vong-2/<V>/KET-QUA.json`. Không được gọi số đó là đạt/không đạt hoặc dùng để dừng tiến độ.

Anh đồng thời chốt: nhiều dòng triển khai ở V2 từ chứng cứ hóa đơn/thuế suất mẫu, thiếu chứng cứ thì chờ; `xlrd==2.0.2` chỉ cài offline nếu có wheel; danh mục lấy file kết xuất mới nhất và mã ngoài danh mục không chặn lô; toàn bộ tri thức V4 là PENDING; actor duyệt riêng là `CFO_NTD`; Entry1 đúng 17 cột gồm `ErrorText`; JUNSKY-CHI/THU-T8 chỉ là mẫu cấu trúc, không là bằng chứng import; không nhập Junsky. Các quyết định cũ A07–A12/D01–D10 giữ nguyên, không bị suy diễn thành mapping Junsky hoặc quyền vận hành.

### Giả định có tham số — rà tại R1

| ID | Nội dung | Lý do | Cách đổi lại |
|---|---|---|---|
| GIẢ ĐỊNH-V2-1 | Dung sai tổng hóa đơn mặc định 1 VND/dòng. | Bù sai số làm tròn nhưng không che chênh lệch nguồn. | Khai `rounding_tolerance` theo chứng từ/mẫu nguồn. |
| GIẢ ĐỊNH-V2-2 | XML↔bảng kê cùng khóa nhưng lệch tiền thành cảnh báo `WARNING_MONEY_CONFLICT`. | Cần giữ cả hai bằng chứng, không loại cả file. | Kế toán trưởng có thể đổi policy thành quarantine/chặn theo ngưỡng. |
| GIẢ ĐỊNH-V3-1 | Thiếu `known_at` dùng `exported_at`; thiếu coverage dùng đúng một ngày `as_of`. | Không suy từ mtime/kỳ; vẫn cần metadata có thể truy vết. | Truyền `--known-at`/coverage/basis khi nạp. |
| GIẢ ĐỊNH-V3-2 | Kỳ khóa là khai báo tay; trạng thái ghi sổ lấy `operation.posted_journal_statuses`. | Chưa có file kỳ khóa và mỗi nguồn có tên trạng thái riêng. | Sửa `cau_hinh.that.toml` hoặc truyền khai báo kỳ khóa, không sửa engine. |
| GIẢ ĐỊNH-V3-3 | File danh mục mới nhất chọn theo thời điểm file trong từng vai trò; sổ chọn bộ có nhiều cột hợp đồng V2 nhất. | Chưa có manifest kết xuất chung từ Junsky. | Cung cấp manifest/ID lần xuất để khóa lựa chọn. |
| GIẢ ĐỊNH-V4-1 | `known_at` tri thức lấy ngày trên sheet nếu có, nếu không là thời điểm nhập; `NGỦ` dùng ngày chuyển làm ngày cuối hiệu lực. | Không lùi thời điểm biết; giữ quy tắc khoảng nửa mở. | Điền ngày nguồn/chuyển trạng thái rồi nhập lô mới. |
| GIẢ ĐỊNH-V5-1 | `review_candidate_limit=10`. | Giảm workbook từ danh sách công nợ toàn cục, vẫn có `CONG_NO_KHAC`. | Đổi `operation.review_candidate_limit` từ 1 đến 100. |
| GIẢ ĐỊNH-V6-1 | Shadow dùng `DAY_DU` và tiền tố `SHADOW` nếu mapping không chỉ rõ. | Chỉ tạo cấu trúc kiểm soát, tránh nhầm file vận hành. | Cấp mapping có version sau khi nhà cung cấp xác nhận Entry2/EntryID. |
| GIẢ ĐỊNH-V6-2 | Thiếu BankID, TK ngân hàng, BranchID, EntryDM/DebtID/CashflowID hoặc Base 2026 thì không tự dựng; dòng giữ chờ hoặc phạm vi Base bị bỏ qua. | Các nghĩa mã chưa có bằng chứng và Base 2026 chưa được giao. | Nạp mapping/Base đã xác nhận bằng lô riêng sau R1. |

### Giả định có tham số — V7

| ID | Nội dung | Lý do | Cách đổi lại |
|---|---|---|---|
| GIẢ ĐỊNH-V7-1 | Công nợ dùng dấu theo `[account_nature]`: tiền tố dư Có là âm, dư Nợ là dương; Bảng CĐPS được ưu tiên nếu có tính chất. | Engine chỉ phân bổ phải trả có số âm. | Sửa bảng `account_nature` trong `cau_hinh.that.toml`, rồi nạp snapshot mới. |
| GIẢ ĐỊNH-V7-2 | Số XML có phần lẻ làm tròn `ROUND_HALF_UP` đến VND scale 0, kèm `INVOICE_FRACTION_MINOR`. | TCT 2.1.0 có tối đa sáu chữ số lẻ, kho dùng INTEGER VND. | Đổi quy tắc trong bộ đọc và nạp evidence mới; không sửa số nguồn. |
| GIẢ ĐỊNH-V7-3 | `fetched_at` Base không có offset được hiểu UTC+07; `known_at` lô là `fetched_at` muộn nhất. | Backup thực có ISO không offset, kho cần một thời điểm biết bảo thủ. | Khai `--known-at` hoặc chuẩn hóa timestamp nguồn khi nạp. |
| GIẢ ĐỊNH-V7-4 | Sổ Junsky lịch sử mở rộng `coverage_from` về ngày sổ sớm nhất khi `journal_history_extend_coverage=true`; coverage người khai vẫn giữ trong manifest. | Sổ được giao chứa bút toán lịch sử trước snapshot công nợ. | Đặt cờ false hoặc khai coverage rộng hơn trong lần nạp mới. |
| GIẢ ĐỊNH-V7-5 | Danh mục ưu tiên ngày `YYYY-MM-DD`/`YYYYMMDD` trong tên file, không có mới dùng mtime. | mtime thay đổi khi sao chép, ngày tên file ổn định hơn. | Đổi chiến lược sau khi có manifest Junsky chuẩn. |

V7 không tự duyệt tri thức. `duyet-tri-thuc` chỉ áp dụng ô `APPROVE`/`REJECT` do người duyệt điền với actor tường minh; `--kho-thu` không ghi sự kiện. `xlrd==2.0.2` chỉ nhận từ wheel offline do Anh cung cấp, không tải mạng hay tự dựng parser `.xls`.

### Giả định có tham số — V8

| ID | Nội dung | Lý do | Cách đổi lại |
|---|---|---|---|
| GIẢ ĐỊNH-V8-1 | Danh mục và cây hóa đơn dùng `operation.catalog_valid_from`, mặc định `1900-01-01`; policy vẫn giữ ngày hiệu lực của nguồn. | Danh mục không có ngày hiệu lực tin cậy trong workbook, còn policy có. | Đổi `catalog_valid_from` hoặc truyền ngày khi nạp, rồi nạp lô mới. |
| GIẢ ĐỊNH-V8-2 | Ngưỡng cảnh báo chứng cứ thanh toán VAT là `operation.vat_payment_evidence_threshold_minor`, cấu hình `20.000.000` VND. | Cần nêu rõ điểm rà soát nhưng chưa có quyết định cổng từ kế toán trưởng. | Đổi giá trị cấu hình; cảnh báo không thay quyết định thuế. |
| GIẢ ĐỊNH-V8-3 | Hóa đơn/Base thiếu MST, policy, căn cứ thuế hoặc chuỗi thanh toán tạo ràng buộc chờ; không suy diễn từ tên đối tác. | Tránh tạo bút toán/công nợ trùng khi quan hệ chứng từ chưa đủ bằng chứng. | Nạp tri thức/evidence được duyệt rồi mở phiên mới. |
| GIẢ ĐỊNH-V8-4 | UI `that` dùng local token theo phiên, staging cục bộ và chỉ gọi service hiện hữu; `junsky_import_enabled=false`. | Bảo đảm thao tác trên máy, có audit và không mở đường nhập Junsky. | Chỉ thay cờ/quyền sau UAT và quyết định riêng của Anh/kế toán trưởng. |

## V9 — Quyết định của Anh ngày 25/09/2026: Định khoản nhanh

- **N1:** Chế độ Định khoản nhanh được dùng tri thức PENDING và tri thức học có bằng chứng để đề xuất, luôn kèm mức tin cậy/lý do. Quy ước tri thức phải được duyệt trước khi đề xuất không áp dụng cho chế độ này.
- **N2:** Không có dòng nào vào file Junsky nếu Anh chưa bấm Đồng ý cho bút toán đó. Phần mềm chỉ tạo file, không tự nhập Junsky.
- **N3:** Đồng ý hoặc Sửa bút toán là quyết định duyệt tri thức với actor `CFO_NTD`; phương án Anh chọn được lưu cho lần đề xuất sau. Bỏ không tạo tri thức mới.
- **N4:** Danh mục và sổ Junsky là dữ liệu gốc của đơn vị; hệ thống nạp với actor `HE_THONG_JUNSKY`, có audit, hiệu lực toàn kỳ xử lý và không cần duyệt từng mã.

| ID | Nội dung | Lý do | Cách đổi lại |
|---|---|---|---|
| GIẢ ĐỊNH-V9-1 | Xanh yêu cầu đủ trường và không có thiếu căn cứ; ngưỡng lịch sử để nâng căn cứ lên Xanh mặc định là 3 lần khớp 100%. | Chưa có cấu hình ngưỡng thống kê riêng. | Thay thông số sau báo cáo hồi cứu F. |
| GIẢ ĐỊNH-V9-2 | Thiếu BankID/CashflowID/BranchID để trống trong file xuất và được ghi tại file soát. | Danh mục mã quản lý tiền chưa được xác nhận. | Nạp danh mục được xác nhận; bộ xuất tự dùng mapping mới. |
| GIẢ ĐỊNH-V9-3 | Lần thả tệp và nền Junsky khai coverage từ `1900-01-01` đến ngày kế tiếp ngày chụp, không dùng mốc `9999-12-31`. | Hợp đồng source yêu cầu `as_of` phải bao phủ ngày cuối coverage; đây là phạm vi kiểm tra, không khẳng định sổ đầy đủ đến vô hạn. | Khai coverage cụ thể từ manifest Junsky khi có. |
| GIẢ ĐỊNH-V9-4 | Danh bạ STK có “Đúng” hoặc mã đối tượng do Anh điền được xem là mapping xác nhận; ô Sửa/trống chỉ là căn cứ PENDING trong Định khoản nhanh. | Đúng theo cột trạng thái của workbook danh bạ và N1; không tự tạo mã đối tượng ngoài danh mục Junsky. | Kế toán trưởng có thể quy định lại thang độ tin cậy hoặc hủy mapping bằng phiên bản mới. |

## V9b — Quyết định và giả định thực thi S1–S12

V9b giữ nguyên các nguyên tắc N1–N5 của V9. Mọi kết quả F và số liệu nghiệm thu của V9b được ghi sau khi chạy xong trong `docs/BAO-CAO-V9b.md`; phần này chỉ ghi quyết định và các mặc định có thể đổi cấu hình.

### QĐ-V9b-S7 — Ghép sao kê với sổ Junsky và chống trùng

| Trạng thái | Quyết định | Phạm vi và giới hạn |
|---|---|---|
| **ĐÃ DUYỆT BỞI ANH** | Một dòng sao kê chỉ được gắn trạng thái **“Có thể đã có trong Junsky – số CT …”** khi có đúng một chứng từ BR/BP khớp đồng thời ngày, số tiền trên TK 112 và ngưỡng giống diễn giải. Dòng đó mặc định bị loại khỏi file xuất; Anh có thể bỏ đánh dấu để xét xuất lại. | Nếu có từ hai ứng viên trở lên hoặc không có ứng viên, hệ thống không kết luận trùng. Trạng thái chỉ là tín hiệu rà soát, không phải bằng chứng đã nhập Junsky và không bật chức năng nhập Junsky. |

**Căn cứ:** Anh đã duyệt đề xuất S7 bằng việc gửi yêu cầu V9b, trong đó ghi rõ quy tắc S7 là “đề xuất của Claude, Anh duyệt khi gửi V9b”.

### Quy ước V9b Anh đã giao triển khai

- Vế tiền của sao kê: tiền vào ghi Nợ TK tiền, tiền ra ghi Có TK tiền; chỉ dùng ánh xạ TK 112 chi tiết có căn cứ.
- Quy tắc PENDING phải mang nhãn PENDING tương ứng, không mang nhãn `APPROVED_*`; quy tắc PENDING yếu không được lên Xanh.
- Mã đối tượng của chính đơn vị không được dùng để điền đối tượng từ quy tắc, STK hoặc mẫu học.
- Thứ tự nhận diện đối tượng là: quyết định của Anh; danh bạ Đúng/Anh điền mã; danh bạ Cao; Trung bình; máy `CHAC_CHAN`; danh bạ Thấp; máy `NHAP`. Chỉ xung đột cùng mức mới báo chặn.
- Quy tắc theo từ khóa/REGEX không được tự điền đối tượng; chỉ điều kiện gắn đối tác (`BANK_ACCOUNT` hoặc `COUNTERPARTY_NAME`) mới được làm việc đó.
- Học từ sổ chỉ tạo tri thức PENDING có bằng chứng; Đồng ý/Sửa của Anh mới tạo tri thức đã duyệt với actor `CFO_NTD`.
- Mẫu Junsky luôn lấy đường dẫn từ cấu hình; thiếu mẫu thì file dự phòng ghi tiêu đề ở dòng 1. Chế độ xuất mặc định là `DOI_UNG`; không nhập Junsky.

### Giả định có tham số — V9b

| ID | Nội dung | Lý do | Cách đổi lại |
|---|---|---|---|
| GIẢ ĐỊNH-V9b-1 | `object_learning_from` mặc định `2026-07-01`; chỉ trường đối tượng học từ sổ bị giới hạn từ ngày này, còn TK/dự án/TTCP/khoản mục vẫn xét toàn bộ lịch sử hợp lệ. | Quan sát thay đổi cách ghi đối tượng từ tháng 7/2026 cần được kiểm soát, nhưng chưa có xác nhận nghiệp vụ riêng về ngày cắt. | Đổi `object_learning_from` trong cấu hình Nguồn dữ liệu, nạp/chấm lại; không sửa dữ liệu nguồn. |
| GIẢ ĐỊNH-V9b-2 | Ngưỡng giống diễn giải dùng cho ghép/lọc mẫu mặc định `0.80`. | Cần một ngưỡng vận hành có thể kiểm thử trước khi kế toán xác nhận ngưỡng nghiệp vụ. | Đổi `description_similarity_threshold` trong cấu hình, sau đó chạy lại F; báo cáo phải ghi ngưỡng đã dùng. |
| GIẢ ĐỊNH-V9b-3 | Mã độ tin cậy số của danh bạ được hiểu `1 = Cao`, `2 = Trung bình`, `3 = Thấp` khi nguồn chỉ có mã số. | Workbook có thể dùng mã số thay nhãn chữ; cần quy đổi rõ để áp dụng thứ tự S5. | Sửa bảng quy đổi trong cấu hình/importer rồi nạp danh bạ phiên bản mới. |
| GIẢ ĐỊNH-V9b-4 | Danh sách mã đối tượng chính đơn vị được suy ra từ MST trùng MST cấu hình hoặc tên chuẩn hóa trùng tên đơn vị; danh sách Anh sửa tay trong cấu hình có ưu tiên cao hơn suy ra. | Danh mục chưa có một cờ riêng đánh dấu nội bộ. | Sửa danh sách `own_counterparty_codes`, MST hoặc tên đơn vị trong Nguồn dữ liệu rồi chạy lại đề xuất. |
| GIẢ ĐỊNH-V9b-5 | Ánh xạ tài khoản ngân hàng → TK tiền ưu tiên giá trị Anh sửa tay; chỉ tự suy từ sổ khi đúng một TK 112 chi tiết có căn cứ. Không có hoặc có nhiều TK thì giữ cảnh báo/Đỏ. | Tránh đoán TK 112 khi chứng từ lịch sử cho kết quả không duy nhất. | Sửa ánh xạ trong Nguồn dữ liệu; cấu hình mới thay thế suy luận mà không sửa chứng từ nguồn. |
| GIẢ ĐỊNH-V9b-6 | Mẫu học sổ thiếu căn cứ thuế, số hóa đơn hoặc khóa cứng MST chỉ tạo PENDING/WAIT; không tự suy MST → TK từ tên đối tác. | Hóa đơn tháng 8 cần được chấm bằng căn cứ sổ hoặc khóa cứng có truy vết. | Nạp chứng cứ hóa đơn/sổ hoặc mapping MST được xác nhận, rồi chấm lại. |
| GIẢ ĐỊNH-V9b-7 | Khi chưa có `source-settings.json`, F4 dùng các đường dẫn nguồn mặc định đã khai trong ứng dụng; các đường dẫn này trở thành cấu hình hiển thị/sửa được ở màn hình Nguồn dữ liệu. | Kho cũ không có cấu hình nguồn đã lưu, nhưng nền mặc định đã được kiểm tra đủ để dựng kho sạch. | Anh lưu đường dẫn mới ở màn hình Nguồn dữ liệu rồi để bootstrap kiểm tra lại; không sửa file nguồn. |
| GIẢ ĐỊNH-V9b-8 | Không có mẫu Xanh ghép duy nhất thì chỉ số đúng của Xanh ghi `NOT_EVALUABLE`, không ghi 100% và không tự đổi ngưỡng. | Siết ngưỡng không giải quyết thiếu mapping TK tiền hoặc chứng cứ MST → TK; số đo rỗng không phải chất lượng đạt. | Cấp mapping/căn cứ còn thiếu, chạy lại F với ngưỡng cấu hình và đánh giá lại mục tiêu 98%. |

Các giả định trên không phải phê duyệt dữ liệu, mapping Junsky hoặc tri thức cụ thể. Thay đổi tham số phải được lưu cấu hình/audit và chạy lại F trước khi dùng kết quả mới.

## 24/10/2026 — Quyết định của Anh trong phiên lead Claude Code

| Mã | Quyết định | Căn cứ / hệ quả |
|---|---|---|
| QD-20261024-01 | **CSDL CRM DEMO riêng cho lập trình** (bảng chọn): worker, lead và cổng A chạy trên CSDL `kho_crm_demo_lt_<hậu tố>`; CSDL DEMO của Anh không bị nâng schema hay lẫn dữ liệu thử. | Lát L0-4b, `tools\mo_demo_worktree.ps1 -CsdlRieng`. |
| QD-20261024-02 | **Báo giá → Ký: giữ chặn ở bước Ký** (bảng chọn, khuyến nghị): báo giá ghi đè tổng hoặc chia tiền không tròn % qua được In/Chuyển (TL 45) nhưng bước Ký vẫn kiểm tổng = đơn giá × diện tích và % hữu hạn; kế toán đối chiếu lại khi ký. | Không mở lát sửa bước Ký. Màn Báo giá đã báo trước "Tổng ghi đè sẽ được kiểm lại khi ký hợp đồng". |
| QD-20261024-03 | Cài Codex CLI làm worker (bảng chọn). | `codex-cli 0.164.0`, đăng nhập ChatGPT sẵn có. |
| QD-20261025-01 | **Cổng A Báo giá gói 1 — Sửa rồi xem lại** (nhận xét của Anh 25/10): (1) đơn giá × tỷ giá × diện tích tự tính ra Tổng giá trị, ghi kèm **giá trị bằng chữ**; (2) USD: cho nhập tỷ giá, mặc định 26.000, sửa được; VND: tỷ giá = 1; (3) phần tính giá trị và lịch thanh toán **để to và đặt trước**; (4) thông tin khách hàng và phí quản lý/bảo trì **điền sau khi khách đồng ý**. | Lát BG-1c (máy chủ) → BG-1d (màn hình). |
| QD-20261025-02 | Báo giá USD: **VND là tiền chính** — Tổng giá trị (VND) = đơn giá USD × tỷ giá × diện tích, bằng chữ VND; lịch thanh toán tính bằng VND; USD chỉ hiện tham chiếu (bảng chọn). | Ảnh hưởng: soạn hợp đồng nhận giá trị VND; bước kiểm khi Ký phải tính cùng công thức (xem BG-1c). |
| QD-20261025-03 | **Được In báo giá sơ bộ** trước khi có thông tin khách/phí (bảng chọn); thông tin khách + phí là bước 2, bắt buộc trước khi Chuyển sang soạn hợp đồng. | |
| QD-20261025-04 | Tỷ giá mặc định 26.000 đặt trong **cấu hình chung, kế toán sửa được** (bảng chọn); người lập sửa từng báo giá khi cần. | |
| QD-20261025-05 | **CRM · Danh mục dự án đang bán** (yêu cầu mới của Anh 25/10): mỗi dự án có thông tin chung, tiến độ thanh toán tiêu chuẩn, các loại phí bảo trì/phí sử dụng tiêu chuẩn; báo giá chọn dự án → nạp mặc định. | Thiết kế: `docs\46-chuyen-doi-dieu-phoi\THIET-KE-DU-AN-DANG-BAN.md`; lát DA-1…DA-3. |
| QD-20261025-06 | Dự án đang bán **chọn từ danh mục dự án kế toán** (`master.du_an`, có mã Junsky) rồi bật "đang bán"; dự án mới hoàn toàn do kế toán thêm vào danh mục chung trước (bảng chọn, khuyến nghị). | Không tạo danh mục dự án thứ hai. |
| QD-20261025-07 | **Bán hàng tự sửa** dự án đang bán và thông số tiêu chuẩn — hiệu lực ngay, có phiên bản + nhật ký (bảng chọn). **Kể cả tiến độ thanh toán tiêu chuẩn: bỏ bước CFO duyệt** của bộ chuẩn G7 (bảng chọn). | Phải sửa luồng duyệt bộ chuẩn G7 hiện có (migration mới). |
| QD-20261025-08 | Thông số dự án lưu sẵn để báo giá tự nạp: **đơn giá niêm yết + tiền tệ**, **loại hình + thuế mặc định**, **danh mục lô/căn** (diện tích, trạng thái — thay BG-09), cùng tiến độ và các loại phí (bảng chọn). Không lưu hạn hiệu lực báo giá theo dự án. | BG-09 nhập vào lát DA. |
| QD-20261025-09 | Báo giá đã nạp thông số tiêu chuẩn **được sửa riêng**, màn hình báo **"khác tiêu chuẩn"** và ghi nhật ký (bảng chọn). | |
| QD-20261025-10 | **Bật test PostgreSQL** (bảng chọn): bộ chạy tạo CSDL tạm tiền tố `kho_test_` trên cụm PostgreSQL DEMO rồi xóa sau khi chạy; không đụng CSDL DEMO của Anh hay kho thật. | Lát L0-8. |
| QD-20261025-11 | **E1-MUA bước 2–3 sửa trong bản vá trong repo** (`tools\source6_*`, có git + review); áp vào engine #6 thật một lần khi Anh cho phép (bảng chọn). | Lát E1-2, E1-3. |
| QD-20261025-12 | **Màn M4 03B**: lead soạn checklist màn hình, Anh duyệt bằng bảng chọn trước khi code (bảng chọn). | |
| QD-20261025-13 | **Màn M4 03B** (bảng chọn): **khối trong màn Kế toán nghiệm thu** (mỗi đợt đã xác nhận); **có xếp hạng gợi ý** hóa đơn gần với đợt (vẫn do kế toán bấm chọn, máy không tự ghép); liên kết "một phần" **khai bằng số tiền** (thay tỷ lệ % ở máy chủ 03B hiện có → cần migration mới). | Checklist `docs\46-chuyen-doi-dieu-phoi\CHECKLIST-M4-03B.md`; lát M4-5a (máy chủ), M4-5b (màn hình). Lưu ý: tiền hóa đơn M2 chưa xác thực (UNPROVEN) → số tiền khai là khai báo của kế toán, xếp hạng theo số tiền chỉ dùng được khi hóa đơn có số tiền đọc được. |
| QD-20261025-14 | Lead chốt kỹ thuật BG-1c: tên khóa cờ phí trong profile loại hình `cau_hinh.bao_gia.truong_ap_dung`; bước Ký (M0030) đọc cả `tong_gia_tri_ghi_de` → báo giá ghi đè tổng bị chặn ở Ký (đúng QD-20261024-02); số bằng chữ dùng chung bộ đọc của mẫu hợp đồng (không có chữ "chẵn" — đổi thì đổi cả hợp đồng). | |
| QD-20261025-15 | Lead chốt kỹ thuật C3 (danh sách hợp đồng S1, review Claude #4): ô tiền (giá trị HĐ, thu theo CRM, công nợ Junsky) **theo quyền xem tiền hiện hành** `XEM_TIEN` (KT/KTT/CFO có M1) + bán hàng trong phạm vi của mình (D3); vai chỉ xem (XEM) hoặc thiếu M1 nhận ô tiền rỗng kèm nhãn "không có quyền xem tiền" — không mở rộng quyền so với danh sách cũ. Anh muốn khác thì đổi. | Hợp đồng bán hàng của bán hàng **luồng B** (nhận từ #6 → KT kiểm → CFO duyệt) chưa có phạm vi bán hàng → đang ẩn với bán hàng (an toàn); lát C3b cần Anh chốt nguồn phạm vi (không suy từ người nộp). |
| QD-20261025-16 | **Giao Codex nhiều hơn** (lệnh Anh 25/10): lead ưu tiên giao lát lập trình cho Codex, chia nhỏ (≤ 3–5 file), kể cả màn hình; luôn kiểm soát: lead kiểm diff đúng file được phép, tự chạy test so nền, Claude review chéo trước khi gộp, lead commit. Vẫn tối đa 3 worker lập trình cùng lúc. | Thay câu "Codex chỉ còn là worker (1–2)" ở `CLAUDE.md` §1. |
| QD-20261025-17 | Dự án đang bán (bảng chọn): luồng cũ "kế toán lập → CFO duyệt" tiến độ thanh toán **tắt trên màn hình, giữ bản cũ** — màn hình chỉ còn sửa hiệu lực ngay (bán hàng/kế toán, nhật ký); bản CFO đã duyệt giữ nguyên để tra cứu, hợp đồng cũ không đổi. | DA-2 ẩn nút gửi/duyệt CFO; máy chủ giữ hàm cũ. |
| QD-20261025-18 | Dự án đang bán (bảng chọn): **đơn giá niêm yết theo m²**; lô/căn **4 trạng thái** Còn trống / Đang giữ chỗ / Đã bán–cho thuê / Tạm không bán, báo giá chỉ chọn lô Còn trống. | Đúng bản DA-1. |
| QD-20261025-19 | Dự án đang bán (bảng chọn): **nhiều mức thuế theo khoản** (tiền đất/thuê, hạ tầng, các loại phí…) thay cho một mức VAT chung — cần thiết kế thêm (lead soạn checklist, hỏi Anh) rồi sửa M0031 trước khi gộp. | Mỗi dự án vẫn một giai đoạn tiến độ mặc định. |
| QD-20261025-20 | Dự án đang bán · **thuế** (bảng chọn, thay phần "nhiều mức" của QD-19): đơn giá niêm yết và mức phí **luôn là giá chưa gồm VAT**; mức thuế chọn từ **danh mục cố định** (10% / 8% / 5% / 0% / Không chịu thuế / Không kê khai), **mặc định 10%**; khoản có xử lý thuế riêng là **phần giá đất được trừ** (khai đơn giá đất/m², không tính VAT); báo giá hiện **từng khoản** (trước thuế, VAT, sau thuế) **+ tổng** sau thuế VND và bằng chữ. | Lead hiểu: một mức thuế chung của dự án áp cho giá chính và các phí (Anh không chọn "từng loại phí có mức riêng"); giá tính VAT của giá chính = (đơn giá − giá đất được trừ) × diện tích. Anh muốn khác thì đổi. |
| QD-20261025-21 | **Chia tối đa việc cho Codex** (lệnh Anh 25/10, nâng QD-16): mọi việc lập trình — kể cả gắn migration, sửa test, viết script, review chéo code Claude viết — giao Codex theo lát nhỏ; lead chỉ giữ việc Codex không làm được (git/commit/gộp, chạy PostgreSQL/DEMO, thử trình duyệt) và cổng kiểm soát (diff đúng file, chữ Việt không hỏng, tự chạy test so nền). Claude chỉ review lát rủi ro cao (tiền, quyền, xóa dữ liệu); lát nhỏ lead đọc diff. Vẫn tối đa 3 worker lập trình cùng lúc. | |
| QD-20261025-22 | Lead chốt kỹ thuật C3 (review Claude vòng 2 #1): cờ **"Quá hạn"** và **"Thiếu căn cứ"** trên danh sách hợp đồng suy ra từ lịch + số đã thu → coi như thông tin tiền: **che** (và không cho lọc theo cờ đó) với vai không có quyền xem tiền theo QD-15 — "thà bỏ sót". Anh muốn khác thì đổi. | Câu hỏi để Anh (gom cùng C3b): bán hàng có binding có được thấy **số dư công nợ Junsky cấp khách** (gồm cả hợp đồng ngoài binding của khách đó) không. |
| QD-20261025-23 | Mask v2 · chế độ API (bảng chọn, cụ thể hóa TL 48 §1.4/§7.3): cụm định danh **mới** gặp trong lượt tự động được lưu "chờ Anh duyệt" vào **tệp riêng mã hóa** (như `.maskkeep`) kèm **màn hình duyệt**; không đổi định dạng danh mục `.maskvault`. Làm ở lát **MASK-3** (sau MASK-2); trước đó cụm mới chỉ giữ trong RAM của lượt (`cum_moi`). | Anh 25/10 |
| QD-20261025-24 | Mask v2 · chế độ API (bảng chọn, sau khi lead làm rõ luồng: dữ liệu → Mask che → Cloud → Mask mở che; danh mục khóa thì không gửi Cloud, dùng Local AI): danh mục đã mở khóa một lần được dùng cho API **đến khi tắt Mask** (phiên giao diện vẫn khóa sau 1 giờ); có thao tác "Khóa danh mục ngay". Giảm rủi ro: mật khẩu chỉ trong RAM; tệp khóa API giới hạn quyền cho tài khoản Windows chạy Mask. Làm trong MASK-1 vòng 2. | Anh 25/10 |
| QD-20261025-25 | Mask v2 · màn che file thủ công (bảng chọn): **giữ như nay** — Anh tự duyệt danh sách "Còn lại cần rà soát"; kiểm "dấu vết" chỉ áp ở chế độ API (MASK-2), không thêm bước chặn duyệt ở màn thủ công. | Anh 25/10 |
| QD-20261025-26 | CRM · Báo giá/hợp đồng (bảng chọn, theo CLAUDE.md §2 "không Word COM"): thêm **công tắc đổi DOCX → PDF bằng Word, mặc định TẮT** — phần mềm chỉ xuất DOCX và báo "PDF xuất tay"; đường Word giữ trong mã nhưng không chạy cho tới khi Anh bật. Lát PDF-1. | Anh 25/10 |
| QD-20261025-27 | CRM · hợp đồng (bảng chọn, hệ quả của QD-26): **cho ký trên bản DOCX** — bản soạn sang "Chờ ký" khi đã có DOCX của đúng revision (không cần PDF đạt); PDF (nếu có) chỉ là bản tham khảo. Bản ký gắn bản xuất G3 theo DOCX (PDF khớp khi có). Đối chiếu bản ký ↔ bản sinh (G5) khi bản sinh chỉ có DOCX: thà bỏ sót — không tự kết luận khớp nếu chưa đối chiếu được, chuyển kiểm tay. Lát KY-DOCX (Claude Opus, review riêng). | Anh 25/10 |

## QD-20261026-01 · M2k — nút "Cài đặt lại bộ tải" = khởi động lại bộ tải
Anh chốt 26/10 (bảng chọn, lead hỏi theo CD-009): nút chỉ **dừng tiến trình bộ tải đang treo rồi chạy lại**; không tải lại gói, không đổi cấu hình. Chỉ kế toán có quyền M2 bấm; ghi nhật ký.

## QD-20261026-02 · E1-4 — màn "Danh mục tham số (sửa + nhật ký)" là màn Danh mục chung riêng
Anh chốt 26/10 (bảng chọn): một ô riêng trên trang chủ hệ thống "Danh mục tham số" dùng chung cho mọi module (không gộp vào M4 hay M2).

## QD-20261026-03 · MTQ-4a3a — "Hợp đồng thuộc CRM" trong cổng ma trận thẩm quyền
Lead ghi 26/10 theo review MTQ-4a3a: trong resolver SQL M0045, HĐ thuộc CRM = `module_chu IS NULL AND loai NOT IN ('VAY','MUA')` (cùng bộ lọc `k2/crm_s1.py:93`). Hẹp hơn RLS (RLS và `crm.py` vẫn coi MUA là CRM) nên an toàn; profile CRM hiện chỉ tạo `THUE_DAT`/`BAN_NHA`. Liên kết tiền chỉ nhận `HOP_DONG_DOT_TIEN` không chủ sở hữu module (chặn `VAY_TIEN` của M9 và L11 `HD_PHIEU_KHO`). Đổi định nghĩa phải qua migration mới + review.

## QD-20261026-04 · Review chéo giao Codex; Claude chỉ kiểm xác suất
Anh chốt 26/10 ~16:00: "do hạn mức đã gần đầy, hãy giao cho cả codex tự kiểm theo bài của Claude, để claude code chỉ kiểm xác suất thôi". Thay phần review của CD-004 (kiem-nhanh Haiku + review-lat Opus): mỗi lát Codex được một Codex khác review chỉ đọc theo `docs/46-chuyen-doi-dieu-phoi/MAU-REVIEW-CODEX.md`; lead giữ gate máy (diff/mã hóa/test + PG so nền/skip) cho mọi lát và rút ngẫu nhiên ~1/4 lát đã Đạt để tự đọc nhanh điểm nóng, không gọi subagent. Vẫn tối đa 4 Codex (kể cả việc review).
Bổ sung cùng ngày (Anh nhắc): kiểm soát Codex để không review quá phạm vi/lệch trọng tâm (mẫu mục B "Giữ đúng trọng tâm", mục E lead lọc); và **mọi điểm Chặn gây hỏng cụ thể hoặc chỗ không rõ phải hỏi lại Claude (lead) trước khi thực hiện tiếp** — reviewer ghi mục "Hỏi Claude", worker dừng và báo "Cần lead".

## QD-20261026-05 · M4 — lịch sử đợt chép từ Review tính vào lũy kế chính thức
Anh chốt 26/10 ~17:20 (bảng chọn): "Tính vào lũy kế chính thức" (thay mặc định "chỉ hiển thị riêng" của M4-DL5b). Áp dụng với các điều kiện:
- seal M4 luôn thắng, không cộng trùng;
- chỉ đợt không có seal M4;
- cùng đơn vị tính; mã hạng mục trùng → cần xem lại;
- ngày nghiệm thu hợp lệ;
- nguồn ghi rõ "REVIEW_CHEP".

Làm ở lát M4-DL5c.

## QD-20261026-06 · OCR — một engine dùng chung cho mọi module, gộp sổ đếm trang với Review
Anh chốt 26/10 ~17:20: "Gộp sổ chung. Lưu ý OCR dùng chung 1 engine cho tất cả model".
- Một cổng OCR dùng chung (giống cổng AI) cho M4/M9/…: cùng Hot Folder ABBYY và cùng sổ đếm trang với phần mềm Review (hạn mức 5.000 trang/30 ngày).
- Có khóa tệp khi ghi sổ; tiền tố mã việc riêng để không đụng việc của Review.
- Bản gốc Review đóng băng, không sửa. Đường dẫn lấy từ cấu hình.

Làm ở lát OCR-1.

## QD-20261026-07 · Nhịp khi hàng đợi chỉ còn việc chờ Anh
Anh chốt 26/10 ~17:20: làm tiếp việc phụ M9 (thuần, chưa CSDL/màn hình) trong lúc chờ.
Bổ sung lead 26/10 ~17:25 (Codex hỏi khi làm M4-DL5c/OCR-1):
- (a) Đợt M4 cùng số chưa seal, có dòng chép Review liên kết `m4_dot_id` đúng: tính khối lượng Review vào lũy kế (`REVIEW_CHEP`, cờ `m4_dang_mo_lai`); seal M4 về sau thắng. Cùng số mà không liên kết: cần xem lại.
- (b) Sổ trang chung với Review: Review đóng băng ghi không khóa tệp. Chấp nhận rủi ro chen ghi, phía mình đọc lại + gộp + kiểm sau ghi. Hết rủi ro khi chuyển hẳn sang M4 (cổng B).

## QD-20261026-08 · Ma trận thẩm quyền — chốt 14 điểm MTQ-4 (A1–A3, B1–B11)
Anh chốt 26/10 ~19:50: "Đồng ý toàn bộ đề xuất A1–A3, B1–B11 trong MTQ-4-CAN-CHOT.md; giao tiếp các lát MTQ-4".
- **Nền (A):**
  - A1: Admin cấp phạm vi nguồn tường minh (profile, công ty nguồn) → pháp nhân; nguồn gộp đòi đủ quyền mọi pháp nhân.
  - A2: lead giữ chuỗi **MTQ-NEN** cho `ktt_duoc/ktt_pn_cho_phep`, RLS nền, wrapper nhật ký từ chối, kiểm sẵn sàng bật.
  - A3: hàm quyết định **chỉ đọc**, không ghi nhật ký, cho lọc danh sách.
- **Nghiệp vụ (B):**
  - B1: tỷ giá chung cần quyền ở mọi pháp nhân dùng nó.
  - B2: ô riêng cho CFO duyệt lệch bộ chuẩn (V8).
  - B3: phạm vi hẹp theo HĐ/dự án, giữ ràng buộc khách/phiên bản.
  - B4: ghi PDF 02C = "Duyệt hồ sơ đợt: Sửa".
  - B5: 03A xem PDF cần cả ô 03A Xem và ô PDF Xem.
  - B6: tải mẫu/bộ chọn master M4 = Lập "Hồ sơ" theo dự án; không dự án → chặn.
  - B7: chặn chấp thuận ngoại tệ khi chưa có tỷ giá ghim.
  - B8: L11 xem bằng chứng thô cần cả M2 và M5.
  - B9: khởi động lại/dừng bộ tải M2 chỉ Admin.
  - B10: 03B kiểm theo từng nguồn.
  - B11: pháp nhân còn dùng đường cũ thì chưa được bật.
- **Lead tự quyết (C):** thứ tự migration; `m4_request.py` thuộc nhóm M4; guard kỹ thuật giữ nguyên.

## QD-20261026-09 · Giữ cấu trúc bảng; luôn có cách dọn; ưu tiên ít tài nguyên
Anh chốt 26/10 ~22:30 (sau câu hỏi vì sao CRM 46 bảng, M4 56 bảng): "Nếu mỗi bảng sẽ không tốn nhiều không gian với PostgreSQL thì giữ nguyên cách thức, nhưng nên có phương thức để dọn dẹp, ví dụ dữ liệu với BOQ và từng lần nghiệm thu thì bản chất là thêm cột trên bảng mà không phải là tạo bảng mới. Tương tự nếu có phụ lục thêm BOQ thì bản chất là append thêm dòng hoặc deactive những dòng bị thay đổi. Hãy luôn giữ phương thức để tốn ít tài nguyên."
- **Giữ cấu trúc bảng hiện có.** Không đặt mục tiêu gom 4 hàng việc riêng về XS-2; chỉ chuyển khi chạm tới (H1 của phiếu tối 26/10 coi như Anh đã trả lời).
- **Không tạo bảng hay cột mới cho từng lần phát sinh** (đợt nghiệm thu, phụ lục, kỳ). Mỗi lần là thêm dòng có khóa lần/đợt trong bảng cố định — trong Excel tương đương "thêm cột đợt".
- **Phụ lục đổi BOQ = thêm dòng** (`THEM`, `THAY`, và `BO` cho dòng bỏ). Dòng cũ không sửa đè, không xóa; coi như hết hiệu lực từ phụ lục đó.
- **Dữ liệu tạm phải có hạn giữ và cách dọn:** khóa giữ, việc chạy máy đã xong, hộp nhận sự kiện đã xác nhận, tệp trung gian, CSDL test, worktree đã gộp. Dữ liệu nghiệp vụ và bằng chứng duyệt không dọn.
- **Áp vào cổng kiểm soát:** thêm vào mẫu review Codex; lát mới vi phạm → Chặn.

## QD-20261026-10 · Ma trận thẩm quyền — đối tượng thuộc nhiều pháp nhân (lead, kỹ thuật)
Lead quyết 26/10 ~22:40 khi MTQ-4i-b1 dừng "Cần lead" (resolver chỉ trả một PN, chưa đáp ứng A1).
- Hàm giải trả **tập** PN (`mtq_giai_doi_tuong_tap`).
- Cổng chỉ cho khi **mọi** PN đạt, hạn mức tính từng PN với cùng số tiền.
- Không PN nào bật → đường cũ (CU). **Hỗn hợp bật/tắt → chặn** (`MTQ_PN_HON_HOP`).
- `phong_id` chỉ dùng khi một PN.
- Nhật ký từ chối ghi theo từng PN không đạt.
- `mtq_duoc_doc`: mọi PN tắt → NULL; hỗn hợp → false; mọi PN bật → true khi tất cả true.
- Đối tượng một PN giữ nguyên kết quả.
- Lát NEN-2a (cổng), NEN-2b (đọc), rồi 4i-b1 làm tiếp. Chi tiết: `docs/46-chuyen-doi-dieu-phoi/giao-viec-20261026/giao-mtq-nen-2.md`.

## QD-20261026-11 · Công tắc module (S1–S6) và mã hóa/sao lưu (M1–M3)
Anh chốt 26/10 ~22:50: "Đồng ý toàn bộ đề xuất S1–S6 và M1–M3 trong CAN-ANH-CHOT-TOI-26-10.md; giao tiếp các lát."
- **Công tắc Tắt / Thử / Vận hành theo module × pháp nhân** (không thay ma trận thẩm quyền):
  - S1 Thử = chỉ Admin và người được chỉ định thấy; không xuất ra ngoài; không đẩy kết quả chính thức sang module khác; dải "Đang thử".
  - S2 chỉ Admin đổi, bắt buộc lý do, có nhật ký.
  - S3 module đang dùng (CRM, M2, M4, lõi) mặc định Vận hành; module mới mặc định Tắt.
  - S4 Tắt = không nhận việc mới, ẩn khỏi lưới; việc đang chạy chạy nốt; dữ liệu xem chỉ đọc; module khác hiện "Chờ".
  - S5 Thử → Vận hành phải đạt bảng điều kiện go-live; dữ liệu thử không tự thành chính thức.
  - S6 thử nghiệm đầu: tắt M2 → M4 hiện "Chờ hóa đơn M2".
- **Mã hóa và sao lưu (CD-019):**
  - M1 mã hóa 10 nhóm A ngay; 5 nhóm B chờ; 3 nhóm C (tiền, ngày, mã nội bộ) để nguyên.
  - M2 khóa cột bọc DPAPI theo tài khoản chạy phần mềm, trong `D:\DU-LIEU-KE-TOANi-mat\`; khóa sao lưu riêng cất ổ ngoài + bản dự phòng. **Người giữ ổ ngoài: Anh chỉ định khi tới bước tạo khóa sao lưu.**
  - M3 sao lưu mã hóa 23:00 hằng ngày và trước/sau nâng cấp hoặc nạp; chép ổ khác hằng ngày, ổ ngoài hằng tuần; giữ 30 bản ngày + 12 bản tháng, không tự xóa; mục tiêu mất ≤ 24 giờ, khôi phục ≤ 2 giờ; báo Anh nếu BitLocker làm chậm > 10% (pgbench) hoặc > 15% (thao tác lưu).
- Lát mở: XS-4b (SQL công tắc), XS-4c (máy chủ), XS-2 (hàng việc nền), pilot XS-T1; MH-1 (cổng mã hóa cột), SL-1 (sao lưu mã hóa), rồi MH-2…, SL-2, DO-1.
