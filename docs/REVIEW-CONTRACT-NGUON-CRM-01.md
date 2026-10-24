# Review độc lập hợp đồng nguồn #6 cho CRM-01

Ngày kiểm: 19/10/2026. Phạm vi: đọc tĩnh source kỹ thuật và catalog tham số của `D:\Claude\Local AI\hop_dong`, đối chiếu gói `GIAO-VIEC-CRM-KE-TOAN-33.md`. Không đọc hợp đồng, đáp án, kết quả trích hoặc output thật; không import module, chạy app/model/test hay kết nối mạng. Không sửa hoặc xóa file nguồn. Đây là oracle đầu vào cho review CRM-01, **chưa phải kết quả kiểm runtime adapter CRM**.

## 1. Kết luận ảnh hưởng trực tiếp đến triển khai

1. Có thể nhận JSON kết quả #6 mà không xây lại Word reader, bộ định vị hay công cụ trích. JSON xuất là bảng **tham số dạng text**, chưa có lịch thu hoặc định danh pháp lý/pháp nhân chuẩn.
2. Catalog hiện hành có 36 mã đang bật, khớp bộ mã mặc định trong source. Chưa có mã mặc định biểu diễn lịch thu KCN/nhà ở. Có thể dùng catalog/profile DEMO tùy biến, nhưng phải ghi đúng nguồn gốc đó.
3. `kiem_tra` là chuỗi tự kiểm. `OK`, `OK (khớp gần đúng)`, số tự kiểm đạt và trường so đáp án đều không thay CFO duyệt, kiểm nguồn Word hay hiệu lực pháp lý.
4. Không có version catalog/schema, hash Word hay khóa pháp lý trong JSON nguồn. Envelope và profile của kế toán phải bổ sung provenance/version, giữ trường chưa biết ở trạng thái chưa xác minh.
5. Cùng Word được trích lại không tự là phụ lục. Cùng mã tham số cũng chưa chứng minh cùng ý nghĩa nếu catalog đổi; riêng `Y-01…` được đánh lại theo thứ tự từng đợt.

## 2. Bằng chứng source có thể tái kiểm

| Tệp kỹ thuật | SHA256 tại thời điểm đọc |
|---|---|
| `doc_reader.py` | `67ec05dd12dab514364ddf4afd35a5919caf97a8f9ed91ecc4f6f1e050e6e296` |
| `trich_xuat_v3.py` | `764f45a6e08dc35500f0d9674dea5022ebb7b50be087bf745d73451c30e43008` |
| `cau_truc_hop_dong.py` | `efaca7e9d724a07889e01c22e2fb10aab05450f6f3f638b1818d2462ae83a9ba` |
| `danh_muc.py` | `dae8ddf522cc69f27a936e94528cbb924a07f66677de4f4c9fd6cb47eea9e94c` |
| `DANH_MUC_THAM_SO.xlsx` | `ab35c1468950b674266da5d21702ff9619c72a372e9ef8146686f5df005c2443` |

Catalog chỉ được đọc trực tiếp các cột mã, nhóm, mô tả kỹ thuật và bật/tắt trong ZIP/XML; không gọi `load_params()` vì hàm này có thể tạo catalog khi thiếu. Không mở `dau_vao`, `mau_that`, `ket_qua`, `*_KET_QUA.json` hoặc đáp án thật.

Điểm neo: `doc_reader.py:292` (`read_contract`); `cau_truc_hop_dong.py:19/62/165` (mã mặc định/cấu trúc/xuất cấu trúc); `danh_muc.py:45/82` (catalog/yêu cầu thêm); `trich_xuat_v3.py:44/194/198/222/226/255/460/618/623` (schema AI, chuẩn hóa, tự kiểm, xử lý và xuất JSON).

## 3. Shape thực và giới hạn của nguồn

| Thành phần | Shape được code xuất | Ý nghĩa cần giữ |
|---|---|---|
| JSON ngoài | `hop_dong`, `che_do`, `model`, `so_tham_so`, `so_ok_tu_kiem`, `dung_so_dap_an`, `token_vao`, `token_ra`, `thoi_gian_giay`, `tao_luc`, `tham_so`, `phieu_kiem_tra` | Số đo lượt chạy không phải xác nhận chất lượng kế toán |
| `hop_dong` | Basename file Word, có extension | Không phải UUID, khóa pháp lý hoặc mã pháp nhân; không dùng tự mở đường dẫn theo payload |
| `che_do` | `AI` hoặc `chua_chay_AI` | Chế độ chưa AI không có giá trị đã trích |
| `model` | Chuỗi khi AI; `null` khi chưa AI | Không dùng model làm khóa phiên bản hợp đồng |
| `tao_luc` | `datetime.now().isoformat(timespec="seconds")`, không có offset | Giữ raw; không tự coi là UTC hoặc thời điểm thực nhận/biết/đủ điều kiện |
| `tham_so[]` | Mỗi phần tử có `ma`, `nhom`, `tham_so`, `gia_tri`, `don_vi`, `dieu_khoan`, `trich_dan`, `ghi_chu`, `kiem_tra`, `vi_tri_do_duoc`; có thể thêm `dap_an`, `so_voi_dap_an` | Schema AI yêu cầu các trường giá trị/trích dẫn là string; kế toán phải parse có cấu hình |
| `vi_tri_do_duoc` | Một chuỗi ghép nhiều nhãn bằng `; ` | Là vị trí dò theo từ khóa/AI, có thể nhiều ứng viên; không phải page index hoặc citation đã xác minh |
| `doan_lien_quan` | Khi chưa AI: mảng `{vi_tri, noi_dung}` trong từng tham số | Đoạn gợi ý để người đọc; không biến thành giá trị typed hoặc tự sinh lịch |
| `phieu_kiem_tra` | Object từ phiếu đầu vào, gồm chỉ tiêu số/text; cảnh báo danh sách được ghép chuỗi | Giữ nguyên cảnh báo thiếu Điều/ảnh/phụ lục lớn/embedded object/track changes… |

Kết quả `*_cau_truc.json` riêng có `file`, `phieu_kiem_tra`, `cau_truc[]`, `vi_tri_tham_so[]`. Mỗi dòng cấu trúc có `id=R001…`, `dieu`, `tieu_de_dieu`, `khoan`, `tieu_de_khoan`, `noi_dung`; fallback có thêm `doan`. Đây là địa chỉ trong bản đọc của một artifact, **không phải ID pháp lý ổn định** qua lần đọc/chỉnh sửa. Nguồn không xuất số trang.

`read_contract` chuyển `.doc` khi cần, đọc DOCX XML và dựng số tự động. Không có nhánh PDF/OCR tại interface này. Ảnh trong phụ lục, object nhúng hoặc văn bản bị thiếu là giới hạn có cảnh báo, không được coi là đã đọc hết tài liệu ký.

### Tự kiểm thực sự kiểm gì

- `norm()` chuẩn hóa text, `loose()` bỏ dấu câu/khoảng trắng. `check()` có thể trả `OK (khớp gần đúng)`; các giá trị bắt đầu `OK` đều được cộng vào số tự kiểm đạt.
- Citation có thể chia theo `...` hoặc `…`; bộ kiểm so từng mảnh trong toàn văn. Chỉ từ chuỗi `OK` không chứng minh một câu nguyên văn liên tục, đúng vị trí, đúng bản ký hoặc đúng phạm vi nghĩa vụ.
- Kiểm số dùng tập các token số đã chuẩn hóa, không kiểm công thức hoặc vai trò từng số trong câu. `ghi_chu` chứa `Suy ra` làm bỏ qua bước số giá trị phải xuất hiện trong citation. Vì vậy phải giữ phân biệt giá trị trực tiếp và suy ra.
- Không có `sent_rows` thì kiểm nhãn điều khoản cho qua. Kết quả JSON thông thường không chứa toàn văn/những đoạn đã gửi AI để bên nhận tái dựng toàn bộ phép kiểm.
- Có các chuỗi cảnh báo riêng cho thiếu giá trị, không quy định, thiếu citation, citation không khớp, số không có trong citation, sai đoạn, nhiều giá trị, chỉ tìm thấy khi rà lại. CRM giữ chúng như cảnh báo; không chọn hàng cuối hay tự gắn approved.

## 4. Mã tham số đã xác minh

Đây là mã/ý nghĩa kỹ thuật, không chứa nội dung hợp đồng thật. Cả 36 mã hiện hành đều bật.

| Nhóm | Mã → ý nghĩa |
|---|---|
| Thông tin chung | `TC-01` số hợp đồng; `TC-02` ngày ký; `TC-03` gói thầu; `TC-04` dự án; `TC-05` địa điểm; `TC-06` Bên A/giao thầu; `TC-07` Bên B/nhận thầu; `TC-08` hiệu lực |
| Giá hợp đồng | `TT-01` loại hợp đồng; `TT-02` giá trị; `TT-03` đã gồm VAT; `TT-04` thuế suất; `TT-05` cơ sở thanh toán khối lượng |
| Tạm ứng | `TT-10` tỷ lệ tạm ứng/cơ sở trước-sau VAT; `TT-11` thu hồi; `TT-12` bảo lãnh tạm ứng |
| Thanh toán đợt | `TT-20` tỷ lệ thanh toán mỗi đợt theo khối lượng; `TT-21` giữ lại mỗi đợt; `TT-22` thời hạn thanh toán |
| Quyết toán/bảo hành | `TT-30` tỷ lệ thanh toán quyết toán; `TT-31` bảo hành/bảo lãnh bảo hành; `TT-32` thời hạn bảo hành; `TT-33` bảo lãnh thực hiện |
| Điều chỉnh/phát sinh | `TT-40` điều kiện điều chỉnh giá; `TT-41` ngưỡng biến động/giá gốc; `TT-42` khối lượng phát sinh/vượt hợp đồng |
| Tiến độ/phạt | `TT-50` thời gian thực hiện; `TT-51` phạt chất lượng; `TT-52` mức chậm giai đoạn 1; `TT-53` mức 2; `TT-54` phạt chậm tổng tiến độ; `TT-55` trần tổng phạt; `TT-56` khấu trừ phạt |
| Hồ sơ | `TT-60` hồ sơ thanh toán; `TT-61` hồ sơ quyết toán; `TT-62` số bộ hồ sơ |

Các bẫy mapping:

- `TT-01` là trọn gói/đơn giá/thời gian/kết hợp, **không phải** loại hình doanh thu KCN/nhà ở.
- `TC-06/07` dùng nghĩa Bên A/B trong hợp đồng xây dựng. Không mặc nhiên map chúng thành bên bán/bên mua của hợp đồng nhà ở.
- `TT-20` không phải bảng lịch thu. Không chia một giá trị text thành nhiều đợt bằng luật đoán.
- `TT-21` có mô tả catalog cho phép suy `100% - tỷ lệ thanh toán`; vẫn giữ `Suy ra`, không biến thành giá trị giữ lại đã được kế toán xác nhận. Không đồng nhất `TT-21` với bảo hành `TT-31`.
- Catalog có thể thêm/bớt/đổi mã và mô tả. `YEU_CAU_THEM.txt` tạo `Y-01…` từ đầu theo thứ tự dòng của mỗi đợt; mã này không tự có ý nghĩa ổn định giữa lượt chạy. Chưa đọc file yêu cầu thêm thực tế, không khẳng định lượt vận hành nào có/không có Y.

Profile phải pin version và bảng mã → field/kiểu/đơn vị/ý nghĩa, giữ hash artifact/catalog nếu có. JSON nguồn không chứng minh catalog đang dùng; dùng catalog hash hiện tại làm bằng chứng của một artifact lịch sử là sai. Mã lạ hoặc cùng mã khác nghĩa phải được giữ raw/chờ mapping, không âm thầm bỏ hoặc tái nghĩa.

## 5. Oracle độc lập đề nghị cho CRM-01

Các trường hợp sau dùng dữ liệu tự dựng, nhãn DEMO và expected viết trước khi đọc kết quả sản phẩm. Chúng là **tiêu chí cần chạy**, chưa được đánh dấu đạt từ review tĩnh này.

| Ca | Input/biến đổi kỹ thuật | Expected có thể đo |
|---|---|---|
| S01 — shape nguồn thật | JSON theo `_ghi_json`; citation/vị trí là string; chế độ AI với catalog DEMO pin version | Nhận được, giữ raw/hash/provenance; trạng thái ban đầu CHO_DUYET; không đòi nguồn phải có UUID/lịch/citation object chưa từng xuất |
| S02 — chưa AI | `che_do=chua_chay_AI`, `model=null`, giá trị rỗng, có `doan_lien_quan` chứa số | Không lấy số từ đoạn gợi ý làm giá trị, không sinh lịch hiệu lực hoặc mặc định 0 |
| S03 — citation thiếu | Giá trị có số, `kiem_tra=OK` nhưng thiếu/rỗng `trich_dan` | Giá trị hiệu lực NULL/chờ căn cứ; số tự kiểm và đáp án không vượt cổng |
| S04 — nguồn chứng minh thiếu/sai | Citation trông hợp lệ nhưng thiếu Word/manifest hoặc Word hash không khớp | Không gắn đã kiểm nguồn; có giới hạn/việc cần kiểm; bản đủ fixture mới xác minh được |
| S05 — vị trí sai | Citation tồn tại ở khoản khác, vị trí dò có ba ứng viên; hoặc chỉ ghi Điều mà không trang | Giữ địa chỉ gốc, không tự điền trang 1; không xác nhận đúng khoản chỉ vì text có trong toàn văn |
| S06 — nguồn tự kiểm yếu | `OK (khớp gần đúng)`, citation có dấu …, `ghi_chu=Suy ra`, hoặc cảnh báo nhiều giá trị | Giữ mức bằng chứng/cảnh báo; không suy autoapproval, không dùng giá trị phái sinh làm lịch tường minh |
| S07 — nhận lại | Cùng bytes JSON và cùng envelope định danh đã xác nhận nhận hai lần | Delta hợp đồng/phiên bản pháp lý/link/quyết định = 0 ở lần hai; không sinh nghĩa vụ trùng |
| S08 — trích lại | Cùng hash Word, JSON khác do `tao_luc`/model/token/citation hoặc giá trị thay đổi | Revision kết quả trích có vết để đối chiếu; không tự thành phụ lục hay thay lịch đã duyệt |
| S09 — phụ lục thật sự | Envelope khai phụ lục nhưng thiếu căn cứ riêng/quan hệ gốc/ngày hiệu lực; sau đó ca đủ | Ca thiếu chờ xử lý; ca đủ tạo phiên bản pháp lý chờ duyệt, chưa đổi bản/lịch hiệu lực |
| S10 — thiếu hash Word | Chỉ có tên file hoặc hai file cùng basename ở namespace/pháp nhân khác | Không tạo hash giả, fuzzy merge hoặc gộp theo tên; mapping rõ và kiểm quyền/pháp nhân |
| S11 — độ chính xác | Giá trị text DEMO `100000000000000001`; canonical decimal DEMO `1000000000000.00001` qua parser/profile phù hợp | DB/API/UI/export giữ đúng giá trị; không binary float/JS Number làm tròn; raw hash và typed amount khác đúng với giá trị gần kề |
| S12 — locale/đơn vị | VN `1.234.567,89`, `%`, diện tích, đơn giá; chuỗi mơ hồ với dấu phân cách/currency thiếu | Parse chỉ theo profile công khai, các đại lượng tách biệt; mơ hồ chờ xử lý, không đoán VND/VAT/đơn vị |
| S13 — mã trùng/xung đột | Hai tham số cùng mã khác giá trị hoặc hai mã map cùng field mâu thuẫn | Không last-write-wins; raw vẫn đủ, việc chờ có lý do; không lịch hiệu lực |
| S14 — version/profile | Cùng `Y-01` nhưng mô tả/đơn vị đổi; profile chưa tồn tại; profile sửa sau khi đã duyệt | Không tái nghĩa theo profile mới; hồ sơ pin version/hash đã dùng, version không tương thích chờ mapping |
| S15 — lịch DEMO rõ | Catalog tùy biến mô tả rõ từng đợt/currency/amount/basis/ngày hoặc sự kiện; hai profile KCN/nhà ở | Lịch đúng expected fixture đã viết; ghi rõ mã/profile DEMO bổ sung, không tuyên bố mã mặc định nguồn đã có |
| S16 — lịch %/sự kiện thiếu căn cứ | Có tỷ lệ nhưng thiếu cơ sở VAT/phí/rounding; có sự kiện chưa có ngày | Giữ %/sự kiện và provenance, không tự chia tiền, suy ngày hoặc gắn quá hạn |
| S17 — self-check/answer không duyệt | `so_ok_tu_kiem=so_tham_so`, `so_voi_dap_an=ĐÚNG`, actor kế toán/người nộp | Không V3 approved; chỉ CFO mô phỏng đủ quyền/pháp nhân mới duyệt ca đủ |
| S18 — phụ lục và tiền cũ | Đợt bản 1 đã thu, phụ lục chỉ đổi đợt chưa thu; thêm ca đợt đã thu một phần/chia gộp mơ hồ | Link cũ giữ đúng phiên bản/đợt; thay phần hợp lệ; ca mơ hồ chờ; BANK/đề xuất hạch toán không tăng vì nhận hợp đồng |

Với S11 phải kiểm giá trị lưu thực trong PostgreSQL và payload/UI/export, không chỉ tổng đã chuyển sang float; giá trị kế bên phải cho typed/hash khác. Nguồn xuất text, do đó test không nên yêu cầu nguồn đổi sang money JSON number để vượt parser. JSON trùng key, NaN/Infinity hoặc field sai kiểu là ca adapter cần chặn/cách ly mà vẫn giữ bằng chứng raw, không phải khả năng nguồn đã hứa hỗ trợ.

## 6. Trạng thái bàn giao

Đã xác minh tĩnh interface, catalog 36 mã và giới hạn provenance/tự kiểm của #6. Chưa xác minh phiên bản đang deploy, quyền kết nối, chất lượng dữ liệu thật, parser/profile CRM, K2/RLS, workflow hay GUI. Oracle trên phải được chạy độc lập khi Claude bàn giao CRM-01; không dùng báo cáo tự kiểm của nguồn hoặc fixture sản phẩm tự tạo làm đáp án duy nhất.
