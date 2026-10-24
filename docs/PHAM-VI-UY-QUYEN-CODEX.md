# Phạm vi ủy quyền và điểm tiếp tục — Codex điều phối, Claude Code triển khai

> **Lệnh trực tiếp mới nhất của Anh, 18/10/2026:** Codex được truy cập mọi file/trang web cần cho công việc, nhưng **không được xóa bất kỳ file nào**. Không chạy thao tác dọn/xóa file, kể cả file tạm và output kiểm thử; giữ bằng chứng, sao lưu trước khi sửa. Quyền truy cập không tự thay các cổng gửi dữ liệu thật ra ngoài, duyệt nghiệp vụ, nhập Junsky hoặc bật cloud AI đã chốt.

> Cập nhật 18/10/2026 theo yêu cầu trực tiếp mới nhất của Anh: đích hoàn thành là **toàn bộ module và liên kết trong file33**, gồm cả công việc hoàn thiện khảo sát/thiết kế còn thiếu. Tài liệu này giữ làm căn cứ phân kỳ ban đầu, không giới hạn dự án ở V13–V15. Phạm vi tổng thể và coverage hiện hành: [CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md](CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md).


**Ngày lập:** 18/10/2026 (Asia/Saigon).  
**Loại tài liệu:** kiểm kê phạm vi đã được ủy quyền; không phải quyết định nghiệp vụ mới, biên bản nghiệm thu hoặc báo cáo đã chạy thành công.  
**Trạng thái lúc lập:** mới đối chiếu tài liệu; chưa có bằng chứng kiểm chứng V13 trên Windows trong đợt điều phối này. Không đọc dữ liệu vận hành khi lập tài liệu này.

## 1. Lệnh hiện hành và cách giải quyết tài liệu khác thời điểm

Căn cứ trực tiếp là `C:\Users\Admin\.codex\attachments\687f7951-b63b-4d4f-bc71-66b4666517c5\goal-objective.md`. Anh giao Codex điều phối, kiểm chứng độc lập và giao Claude Code làm bên sửa mã chính; tiếp tục các hạng mục đã đủ yêu cầu, màn hình và schema trong kiến trúc/lộ trình đã chốt, không cần xin lại lệnh cho từng V. Mục còn thiếu thiết kế hoặc quyết định nghiệp vụ giữ chờ.

Thứ tự áp dụng là quyết định mới nhất đã được Anh xác nhận **trong đúng chủ đề**. Không dùng ngày sửa file, trạng thái tổng quát trong README, hoặc chữ “Xong” trong báo cáo để thay bằng chứng kiểm chứng tại máy này.

| Căn cứ | Nội dung dùng để xác định phạm vi | Giới hạn khi đọc |
|---|---|---|
| Goal hiện hành, §2–§7 | Ủy quyền liên tục trong phần đủ thiết kế; kiểm chứng V13 Windows trước; Claude Code sửa chính; các cổng dữ liệu/vận hành giữ nguyên | Không ủy quyền mọi dòng trong hàng đợi; không cho tự duyệt nghiệp vụ hoặc bật cloud |
| `..\CLAUDE.md`, §Quy tắc riêng | Người dùng nhận phần mềm bằng nút bấm; dữ liệu thật ở máy; fixture DEMO; học đến 30/06/2026; review độc lập cuối V | Phân công cũ trong TL39 được goal hiện hành thay: Claude Code sửa chính, Codex điều phối/kiểm tra |
| `..\35-kien-truc-tong-the.md`, §1, §3, §5, §8 | K1–K5; hai kho + nhật ký; tri thức một nơi; mã Junsky do Junsky cấp; nhiều pháp nhân; các giới hạn module | Đoạn cũ nói Mask sáu nhóm được §6 và TL38 thay bằng bảy nhóm |
| `..\37-man-hinh-duyet-chung.md`, §2–§8, §13 | K5 một danh sách gộp; tám loại việc; quyền duyệt, chuỗi chứng từ, trạng thái, điều kiện Đồng ý | Không đồng nghĩa cả tám loại việc và mọi chu trình đều triển khai trong V14; xem lát cắt theo TL39/TL40 |
| `..\38-schema-lop-du-lieu.md`, §0–§7, §9 | Schema, khóa, phiên bản, ràng buộc; bảy nhóm Mask; STK/CCCD mã hóa; học theo thời điểm đủ điều kiện | TL40 bổ sung `giao_tiep`, vai trò phần mềm và RLS; còn các cập nhật tài liệu được ghi ở hàng đợi #36 |
| `..\39-ke-hoach-V13-xuong-song-K2.md`, §2–§4, §8 | Tiêu chí V13; V14 K3/K5; V15 cổng AI/Zalo; V16 CRM; V17+ theo phụ thuộc | Không dùng mô tả V13 ban đầu để đảo phương án C đã chốt 17/10 |
| `..\40-kien-truc-da-phong-ban-va-tich-hop.md`, §5, §8–§12 | Chốt 17/10/2026 13:20: web trung tâm, `giao_tiep`, vai trò phần mềm; mở rộng V14/V16 | SSO, chủ danh mục khoản mục phí, chứng chỉ và schema phần mềm kết nối có mục còn mở |
| `HANG-DOI-YEU-CAU.md`, #18–#37 | Danh sách việc cụ thể, nợ kỹ thuật, phần đang chờ | #16 còn “Để sau” nhưng phân quyền/RLS V14 đã được TL40 chốt; #23/#26/#29 ghi xong chưa chứng minh nghiệm thu Windows |
| `docs/BAO-CAO-V13.md`, §2–§7b | Báo cáo phần đã làm và các review; §5 ghi phương án C; các giới hạn Windows và hiệu năng | Báo cáo trên máy ảo chỉ là bằng chứng môi trường đó; cần tái kiểm chứng Windows |
| `docs/QUYET-DINH.md` | Nguyên tắc bằng chứng, thẩm quyền, chống rò rỉ hồi cứu, mapping/actor | Nội dung lịch sử đến V9b không thay các quyết định kiến trúc TL35–40 mới hơn |

`D:\Claude\CACH-LAM-VIEC-CHUNG.md` được CLAUDE.md dẫn chiếu nhưng **không tồn tại tại thời điểm kiểm tra**. Không suy ra thêm yêu cầu từ tài liệu chưa đọc được.

Các điểm đã có quyết định mới hơn cần giữ thống nhất:

- **V13 giữ phương án C:** bộ dịch phương ngữ và bảng V12 nguyên trạng trong PostgreSQL, ghi nhật ký K2; chuyển lõi sang `kho.*` thuộc V14 (`docs/BAO-CAO-V13.md` §5; hàng đợi #37).
- **V14/V15 theo TL39 và TL40:** TL34 còn đoạn cũ gộp cả K3/LLM vào V13 không phải lộ trình hiện hành.
- **Mask bảy nhóm:** tên, MST, địa chỉ, số tiền, STK, CCCD, số hợp đồng; tên khu/dự án cũng thay bí danh theo thiết kế (TL35 §6/§8; TL38 §9).
- **Tri thức sửa chữa của kế toán chờ CFO duyệt** theo TL37; không lấy hành vi duyệt tri thức lịch sử V9 để tự cấp quyền phê duyệt mới.

## 2. Ma trận phạm vi nhận làm

“Nhận làm” dưới đây là phạm vi được phép thực hiện khi qua phụ thuộc; không mang nghĩa đã có code, đã kiểm chứng hoặc đang vận hành. Bằng chứng triển khai và kiểm thử phải được ghi riêng sau mỗi bước.

| Hạng mục | Căn cứ | Phụ thuộc / điều kiện | Trạng thái đúng lúc lập |
|---|---|---|---|
| Kiểm kê code, Git chưa commit, cấu hình, Python/PostgreSQL và các nút mở | Goal §3 | Chỉ đọc trước; giữ thay đổi chưa rõ nguồn; không lộ khóa hoặc dữ liệu thật | **Nhận làm ngay**; chưa ghi kết quả kiểm kê vào tài liệu này |
| Kiểm chứng V13 trên Windows; sửa thiếu sót để đáp ứng đúng phương án C | Goal §3; TL39 §2–§4; hàng đợi #35 | Bản sao dữ liệu; backup/hash trước thay đổi; đầy đủ các tiêu chí §3 dưới đây | **Nhận làm trước V14; chưa kiểm chứng Windows** |
| Review độc lập cuối V13 và bằng chứng bàn giao bằng nút | Goal §4/§7; hàng đợi #14; TL39 §4 | Agent không tham gia triển khai; kiểm tra lỗi chặn; không thay nghiệm thu của Anh | **Nhận làm**, sau vòng kiểm chứng/sửa |
| Nợ kỹ thuật V13 #36: chuẩn hóa tên, hash có khóa, đồng bộ loại lô, cập nhật TL38, khác biệt SQL còn lại | Hàng đợi #36; `docs/BAO-CAO-V13.md` §7/§7b | Xác nhận tình huống sử dụng; không thay checksum migration cũ; test có ý nghĩa với thay đổi | **Nhận ở V14 sau cổng V13**. G7: queue mới xếp V14, báo cáo cũ nói V15; dùng queue mới cho kế hoạch, chưa suy ra khóa đã có |
| Chuyển lõi PostgreSQL từ bảng V12 sang schema K2 `kho.*` #37 | Hàng đợi #37; TL39 §8; báo cáo V13 §5 | Cùng K3/K5; bản sao; đối chiếu dữ liệu/kết quả; giữ SQLite vận hành thật | **Nhận ở V14 sau cổng V13**; chuyển kho thật là cổng riêng |
| K3 #24: nhận diện, liên kết, định tuyến trên kho chung; dùng tri thức chung | TL35 §1/§5; TL34 §2; TL39 §8 | Không tự chốt hai câu nghiệp vụ phễu còn mở; không gọi AI trực tiếp; thiếu căn cứ giữ chờ | **Nhận phần không LLM ở V14**, trên loại chứng từ/chu trình đã đủ thiết kế |
| Liên kết dùng chung #18; chuẩn hóa bậc 0/EntryDM; chuỗi chứng từ | TL38 §3 bảng `lien_ket_chung_tu`; TL37 §6; hàng đợi #18 | Khóa nguồn đúng; liên kết máy là đề xuất trước người duyệt; không tự tạo bằng chứng nguồn còn thiếu | **Nhận ở V14**, triển khai/kiểm thử bằng DEMO hoặc bản sao được bảo vệ |
| Đề xuất đích dòng hóa đơn #22 | TL35 §5; TL34 §2.2–§2.4; hàng đợi #22 | Từ tri thức có căn cứ; một dòng một đích; thiếu Base/nhóm G hoặc chính sách thì giữ chờ | **Nhận phần đủ căn cứ cùng K3**; không nhận thay việc #1/#2 còn chờ chốt |
| K5 bản 1: V1/V2, danh sách gộp, bộ lọc, chuỗi, Đồng ý/Sửa/Bỏ/Hoàn tác; Hỏi chưa gửi | TL37 §2–§6/§13; TL39 §8 dòng V14; hàng đợi #28 | Điều kiện duyệt ở DB/server; UI kiểm tra bằng DEMO; mức 2 khóa; không duyệt dữ liệu thật | **Nhận ở V14 sau cổng V13**. Không mặc nhiên nhận mọi chức năng V3–V8 hoặc module còn thiếu thiết kế |
| Cập nhật prompt/tài liệu K5 để phản ánh TL37 đã chốt | TL37 §14; `docs/thiet-ke/PROMPT-CLAUDE-DESIGN.md` hiện có | File hiện tại vẫn là prompt màn hình Định khoản cũ; không ghi có bản v2/HTML bàn giao khi chưa có | **Nhận chuẩn bị cho K5 V14**, không cần yêu cầu Anh chốt lại bố cục đã chốt |
| Đăng nhập, phiên, khóa sau 5 lần sai, đổi mật khẩu lần đầu; quyền pháp nhân/module, menu và `[modules]` | TL40 §3/§8/§9; hàng đợi #31, #16 | Mật khẩu băm; kiểm tra quyền phía server và RLS; không phụ thuộc SSO | **Nhận ở V14**; #16 “Để sau” là trạng thái cũ đã được TL40 mở rộng |
| RLS, `giao_tiep` v1, view/hàm có phiên bản, hàng đợi chống trùng, vai trò từng phần mềm | TL40 §5; hàng đợi #30 | Không quyền bảng nghiệp vụ/`bao_mat`; test vai trò thực; input được kiểm; idempotency; giải quyết kỹ thuật quyền view/RLS mà không mở quyền trái thiết kế | **Nhận ở V14 phần hạ tầng đã đủ thiết kế**. Hợp đồng dữ liệu M4/RQ chuyên biệt thiếu thì giữ chờ, không tự dựng toàn bộ module |
| Chuẩn bị LAN/HTTPS nội bộ, nhật ký, backup hằng đêm và restore | TL40 §8; hàng đợi #31 | Chứng chỉ/tường lửa/địa chỉ máy được phép; quyền OS nếu cần; không Internet | **Nhận triển khai và kiểm chứng phần tự làm được ở V14**; kích hoạt thực chờ điều kiện vận hành/quyền còn thiếu |
| Cổng AI #25: một cổng, Mask đảo ngược, định tuyến tĩnh, Python validation, log, công tắc tắt | TL35 §3; TL38 §4b; TL39 §8 dòng V15 | Đáp án mẫu theo loại; bối cảnh đã duyệt; khóa bảo mật; test fail-closed; không tự bật cloud | **Nhận phần đủ thiết kế ở V15**, có thể kiểm chứng offline/DEMO; kích hoạt cloud giữ khóa |
| Bối cảnh pháp nhân #27: lưu phiên bản, lựa bản rút gọn, Mask trước cổng | TL35 §3A/§3; TL38 bảng `phap_nhan_boi_canh`; hàng đợi #27 | Chỉ bản đã duyệt được dùng; điểm còn cần xác nhận không tự biến thành chính sách; không đưa hồ sơ thật vào prompt lập trình | **Nhận cấu trúc/xử lý đã chốt cùng K2/cổng AI**; phê duyệt nội dung mới vẫn chờ CFO |
| Zalo thử nghiệm #5: adapter, câu hỏi/phương án, phản hồi/trạng thái và nhật ký | TL37 §7; TL39 §8 dòng V15; hàng đợi #5 | Bot/token; kiểm giới hạn và khởi tạo QR; không tự gửi tin thật; phân tích cloud phải qua cổng đủ điều kiện | **Nhận phần offline/DEMO đủ thiết kế ở V15**; kết nối và vận hành thật còn phụ thuộc |
| CRM hợp đồng #20/#21/#32 và CFO-03 #19 | TL39 §8 dòng V16; TL40 §7/§9; hàng đợi #19–#21/#32 | Hợp đồng/phụ lục mẫu; bộ tham số từng loại doanh thu; đáp án mẫu; nguồn chạy mô hình; màn hình/schema chi tiết còn thiếu phải chốt | **Chưa nhận triển khai trọn module**. Bảo toàn quyết định đã chốt; #19 phụ thuộc danh mục hợp đồng, không tự duyệt tri thức thật |
| Nối thực phần mềm Review/Base/Request #34; module M4/M9/M8 | TL40 §4/§9; TL39 §8; hàng đợi #6/#7/#13/#34 | Khóa chung, định dạng/payload, schema module; quyền nguồn; chủ danh mục; Request sau go-live 31/12/2026 | **Giữ chờ phần thiếu**; chỉ chuẩn bị giao diện tích hợp chung đủ thiết kế, không xây lại dự án nguồn |

## 3. Cổng kiểm chứng V13 tại Windows

Tất cả mục dưới đây **chưa được kiểm chứng trên Windows trong tài liệu audit này**. Các số đếm/mốc của báo cáo cũ chỉ giúp xác định tập so sánh, không thay kết quả tự chạy trên máy hiện tại.

| Yêu cầu nghiệm thu | Bằng chứng phải có | Điều kiện ghi đạt |
|---|---|---|
| Hai engine | Kết quả cùng bộ test trên SQLite và PostgreSQL, phiên bản runtime, test được chọn/bỏ qua | Test cần thiết thực chạy; skip vì thiếu PG không phải đạt; test DEMO không thay so sánh thật |
| Chuyển dữ liệu trên bản sao | Manifest nguồn/đích, số đếm từng bảng, hash dữ liệu, chạy lại lần hai | Không mất bản ghi; hash/đếm khớp theo mapping được giải thích; không trùng khi chạy lại |
| Song song sao kê T8 | Đối chiếu từng dòng của tập 105 sao kê về mức, TK, đối tượng, dự án và trường quyết định khác | 105/105 khớp; có dữ liệu và đề xuất hợp lệ; cùng lỗi không phải khớp |
| Song song hóa đơn T8 | Đối chiếu từng dòng của tập 75 hóa đơn, tách mua vào/bán ra | Đủ tập được chọn, không rỗng; kết quả nghiệp vụ khớp từng dòng; không chỉ so tổng số |
| Chấm Junsky và mốc học | Kết quả chấm T7–T8, cutoff 30/06/2026, số mẫu chấm được/không chấm được, số trước/sau | Không dùng tri thức tương lai; giữ nguyên cách chấm theo đặc tả; thiếu đáp án/khớp duy nhất ghi chưa đánh giá được |
| Hiệu năng | Thời gian đề xuất 105 sao kê trên máy Windows, điều kiện đo và kết quả không đổi | Đạt tiêu chí ≤10 giây; nếu chưa đạt, giao sửa và đo lại đúng tập |
| Nhật ký và quyền | Thử thật bằng vai trò ứng dụng; hành động có trước/sau; UPDATE/DELETE/TRUNCATE nhật ký bị từ chối; không đọc được `bao_mat` | Bằng chứng cơ chế DB và ứng dụng, không chỉ kiểm chuỗi SQL |
| Backup/restore và quay lui | Backup nhất quán, hash/manifest, phục hồi thử, xác nhận trạng thái sau phục hồi; SQLite vẫn chạy | Không nhận backup rỗng là thành công; thao tác không ảnh hưởng kho thật; đường lui được kiểm |
| Giao diện và nút bấm | Mở được phần mềm thử, nhãn đúng engine/kho, thao tác DEMO/ẩn thông tin, file soát và mức 2 khóa | Codex tự kiểm tra GUI; không bắt Anh gõ lệnh; không duyệt bút toán thật |
| Review và continuity | Review độc lập; lỗi chặn được sửa/kiểm lại; báo cáo, checklist và điểm tiếp tục | Chỉ ghi “sẵn sàng nghiệm thu” khi các mục thuộc phạm vi đã có bằng chứng; “Anh đã nghiệm thu” cần xác nhận riêng |

**Cổng sang V14:** hoàn tất kiểm chứng kỹ thuật V13 trên Windows và xử lý lỗi chặn, hoặc ghi rõ phần bị chặn bởi dữ liệu/quyền và chỉ tiếp tục phần độc lập không dựa vào giả định chưa được chứng minh. Không đánh dấu V13 đạt bằng tập rỗng, cùng lỗi hoặc test bỏ qua.

## 4. Các cổng tiếp tục giữ chờ

- **Kho thật:** tiếp tục SQLite. Được xây/kiểm chứng chuyển lõi V14 trên bản sao; chuyển kho thật sang PostgreSQL là quyết định riêng của Anh.
- **Junsky:** mức 2, nhập Junsky, tự duyệt theo loại và đối chiếu vận hành sau nạp vẫn khóa. Cần câu trả lời nhà cung cấp, mapping/danh mục, nhập thử và phê duyệt riêng đúng đặc tả. File được tạo không chứng minh đã nhập.
- **Thẩm quyền:** không dùng actor `CFO_NTD` thay Anh duyệt tri thức/bút toán thật. Mô phỏng dùng `MO_PHONG_` trong kho/thử nghiệm phù hợp.
- **Cloud AI:** không bật hoặc gửi dữ liệu thật. Chỉ kích hoạt sau khi toàn bộ cổng Mask bảy nhóm, bối cảnh đã duyệt, đáp án mẫu, log, công tắc tắt và kiểm chứng đã đủ, cùng phê duyệt vận hành nếu cần.
- **Danh mục/chính sách nghiệp vụ:** không tự chốt mapping đối tác, chính sách dự án, hai câu phễu, chủ khoản mục phí, tham số hợp đồng, danh sách TK công nợ/ngưỡng/hạn chưa được xác nhận.
- **SSO:** TL40 §12 còn chờ xác nhận; không chặn đăng nhập bằng mật khẩu đã chốt.
- **`du_an`/`rq`:** tên schema ở TL40 §12 là đề xuất chốt khi làm V14; không lấy ví dụ tên schema làm bằng chứng đã chốt payload/bảng nghiệp vụ đầy đủ. Chỉ hỏi khi phần thực sự cần quyết định mới không thể làm độc lập.
- **HTTPS/LAN/quyền OS:** kiểm kê và chuẩn bị được làm; chứng chỉ IT, firewall, địa chỉ máy kết nối hoặc nâng quyền chưa có thì ghi cổng cụ thể trước vận hành. Không mở ra Internet.
- **API HTTP ngoài vào #33:** trạng thái “Khi cần”; không có trong V14. Chỉ xây khi có nhu cầu phần mềm ngoài đẩy dữ liệu và đủ hợp đồng dữ liệu/quyết định.
- **M4/M9/M8, M5/M7/M10, CRM còn thiếu thiết kế:** giữ đúng phụ thuộc khảo sát, mẫu, schema, nguồn và thứ tự đã chốt. Không coi lộ trình tương lai là giấy phép tự bổ sung nghiệp vụ còn thiếu.
- **Dữ liệu/bí mật:** chỉ xử lý thật tại máy; chat/prompt/báo cáo/Git chỉ số tổng hợp; fixture DEMO; backup cũ chỉ đọc; không in tên pháp nhân/đối tác, giao dịch, STK hoặc credential.
- **Thư viện ngoài:** CLAUDE.md yêu cầu nêu lý do và hỏi một lần trước khi thêm; kiểm tra trước việc đã được cho phép hoặc dependency hiện có. Không suy ra lệnh triển khai liên tục thành phê duyệt mọi dependency mới.

## 5. Điểm tiếp tục và cập nhật sau kiểm chứng

1. Hoàn tất kiểm kê chỉ đọc code/Git/runtime/cấu hình/nút mở và kết nối Claude Code bằng nhiệm vụ chỉ đọc; lưu định danh session để giao sửa tiếp.
2. Lập checklist V13 theo §3; Claude Code sửa chính theo từng đầu việc có đầu vào, đầu ra và tiêu chí; Codex chạy kiểm tra độc lập. Không hai bên sửa cùng file.
3. Ghi bằng chứng Windows thực tế vào báo cáo phù hợp; tách kết quả kỹ thuật, phần sẵn sàng nghiệm thu, phần Anh đã nghiệm thu và cổng chờ. Không sửa trạng thái hàng đợi thành hoàn tất khi chưa đủ bằng chứng.
4. Khi qua cổng V13, giao lát cắt V14 theo §2: nền K2/nợ kỹ thuật → K3/liên kết → K5 → quyền/RLS/`giao_tiep` và web nội bộ theo phụ thuộc. Review độc lập cuối V, xử lý lỗi chặn rồi mới kết luận.
5. Tiếp tục V15 phần đã đủ thiết kế; triển khai và kiểm chứng offline trước. Các cổng thiếu dữ liệu, quyết định hoặc quyền được gom lại; vẫn làm phần độc lập.

Tài liệu này **chỉ tạo căn cứ phạm vi và continuity**; chưa cập nhật `HANG-DOI-YEU-CAU.md`, `CHANGELOG.md` hoặc kết luận nghiệm thu của bất kỳ V nào.
