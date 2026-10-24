# Gói M10 — định kỳ, checklist khóa kỳ và đối chiếu ngược toàn cây 33

**Ngày 19/10/2026. Trạng thái: bản đầu bài kỹ thuật để Codex review trước thiết kế DDL/coding; chưa triển khai, chưa chạy kiểm thử, chưa nghiệm thu.** Phủ **C9a–C9c, N5 và L12** trong chương trình toàn file 33. Giữ M0–M10 và các phụ thuộc; gói DEMO không thay đích hoàn thành toàn bộ phần mềm.

M10 đọc lịch nghiệp vụ đã được duyệt từ M3/M4/M6/M9 và bảng kế toán 335; tạo đề xuất định kỳ, tổ chức checklist, kiểm điều kiện khóa kỳ và đối chiếu ngược mọi lô. **Module nguồn sở hữu phép tính và lịch; M10 không tính lại lương, khấu hao, doanh thu, lãi hoặc trích trước.** Sổ chính thức, BCTC, tờ khai và việc nhập vẫn ở Junsky.

Giữ kiến trúc K1–K5, typed K2 PostgreSQL, một màn duyệt TL37 và quyền theo TL40; tái dùng các engine/UI/adapter hiện có. Kho thật tiếp tục SQLite theo phương án C cho tới cổng chuyển riêng. Trong gói DEMO: dữ liệu giả, actor `MO_PHONG_*`, mức 2 khóa, không duyệt/nhập Junsky thật, không `CFO_NTD`, không cloud AI hoặc gửi Zalo. **Không xóa bất kỳ file nào**; giữ artifact, phiên bản, log, DB và bằng chứng kiểm thử. Không sửa checksum migration cũ hoặc dựng ledger/app closing riêng.

## 1. Căn cứ, phạm vi đúng và giới hạn của hiện trạng

Nguồn kiến trúc ở `D:\Claude\Phan mem ho tro ke toan\`: TL33 SVG/Markdown, TL35 §1/§3A/§5/§8, TL37 V1/V7/V8 và §5, TL38 §3/§4/§7, TL40 §3–§5/§8. Căn cứ chương trình trong repo: `CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md` §1–§5, `LO-TRINH-TRIEN-KHAI-TOAN-BO-33.md` N5/C9/§6, `DANH-MUC-TAI-SU-DUNG-PHAN-MEM.md`, `HOP-DONG-TICH-HOP-VA-TAI-SU-DUNG-33.md` R_KH, `GIAO-VIEC-M6-M7-DU-LIEU-VA-WORKFLOW-DEMO-33.md` §3–§7 và `KHAO-SAT-MAU-DAU-VAO-M6-M7-M10.md`.

- **Đúng TL33:** M10 = “Bút toán định kỳ, đóng sổ & đối chiếu ngược”; output = bút toán định kỳ **02GJ**, checklist đóng sổ, báo cáo đối chiếu bước 8. L12 lấy lịch từ M3 (phân bổ doanh thu KCN), M4 (trích trước), M6 (khấu hao), M9 (lãi dự trả); mọi lô đã đẩy phải qua đối chiếu ngược.
- **Nhãn cũ “sau khi mở mức 2” trong SVG không chặn chuẩn bị/DEMO M10.** Chương trình hiện hành cho phép hoàn thiện contract, dữ liệu, workflow và kiểm DEMO trước; nhập/đối chiếu thật vẫn cần cổng Junsky riêng.
- **335 là nguồn kế toán/trích trước, thuộc định kỳ M10**, có thể dẫn căn cứ từ hồ sơ M4; không ép thành tài sản hoặc bảng khấu hao M6. R_KH là đường nhận nhóm bảng đã tính, không có nghĩa mọi bảng cùng một loại chứng từ.
- **Không gom mọi “kết chuyển” vào M10.** L5 XDCB hoàn thành → tài sản và L6 bàn giao → giá vốn thuộc M4 nối M6/M3. M10 đọc lịch/kết quả đã đủ căn cứ hoặc theo dõi chúng trong checklist. Chưa có căn cứ để tự thêm engine kết chuyển lãi/lỗ, kết chuyển tự do từ số dư hoặc công thức trích trước.
- Khảo sát đã kiểm phạm vi **35 workbook**, chưa xác định được mẫu lịch 335/doanh thu/checklist dùng được; không suy toàn máy không có mẫu. Chưa có mapping production, checklist thật hoặc chính sách trích trước được chứng minh trong gói này.

Chỉ kiểm tĩnh tài liệu/source kỹ thuật trong nhiệm vụ chuẩn bị; không đọc row thật, `.env`, credentials hoặc backup; không import/chạy product, test, SQL hay ứng dụng nguồn. CRM đang được Claude sửa, vì vậy các interface dưới đây là điểm tái dùng cần khóa lại ở lần bàn giao, không phải chứng nhận runtime.

| Thành phần | Có căn cứ từ thiết kế/source | Tái dùng và phần phải làm tiếp |
|---|---|---|
| Kỳ/khóa kỳ | TL38 và `ha_tang/pg_migrations.py`: `kho.khoa_ky` PK `(phap_nhan_id, ky)`, người/thời điểm/bằng chứng; máy trạng thái, kiểm kỳ khi duyệt | Dùng cùng kỳ/lock cho các module; cần policy closing/checklist, audit mở lại, kiểm khóa trên mọi đường ghi nghiệp vụ liên quan và chạy đồng thời |
| Legacy `month-close` | `kiem_chung/service.py::close_month`: nguồn bao phủ tháng/công nợ, không phiên mở, từng BANK đã đối soát với bộ cuối kỳ, kiểm phát sinh ngoài batch; trả `CLOSED_FIXTURE`, `fixture_only` | Tái dùng logic kiểm phạm vi/evidence và idempotency; **không gọi là checklist M10 hoặc khóa kỳ đa pháp nhân mọi phần hành đã có**. Nhãn `M6` trong log legacy là gói kỹ thuật cũ, không chứng minh nghiệp vụ tài sản M6 |
| Đề xuất/duyệt/lô | `kho.de_xuat*`, `viec_can_duyet`, `lo_xuat*`, `nhat_ky.su_kien`; UI/service xuất hiện có | Dùng V1/V7/V8 và máy trạng thái chung, mở rộng M10; không tạo cơ chế approve/export độc lập |
| Xuất file | `xuat/service.py::export` hiện chặn target thật và sinh file fixture; `xuat/shadow.py` có `CB_tmpEntry1/2` 17/37 cột và file thu/chi shadow | Tái dùng writer, immutable artifact, manifest/hash/recover. **Không coi có cột Excel là đã có mapping 02GJ production**; adapter GJ/EntryID/Entry2 phải có contract và ca riêng |
| Đối chiếu legacy | `hoc/service.py::Reconciliation.reconcile`: bundle sau xuất, phạm vi, chống dùng bản cũ, identity/amount/fields/allocations, công nợ theo biến động nhiều batch; `shadow.py::reconcile` match tham chiếu ngân hàng/tài khoản | Giữ các kiểm tra và provenance; bổ sung khóa bút toán/dòng phù hợp GJ và các module không có bank reference. Không ép GJ thành BANK hoặc bỏ các field chưa đối chiếu được |
| Typed kết quả lô | `lo_xuat_dong` có proposal/EntryID/trạng thái khớp-lệch-thiếu-thừa, nhưng bắt buộc `de_xuat_id` | Cần review biểu diễn **dòng sổ thừa không có proposal** và lịch sử nhiều lần đối chiếu; không tạo fake proposal để nhét THUA_JUNSKY |
| Quyền | `k2/quyen.py` đọc actor/quyền pháp nhân/module; đang có action CRM/M1, danh tính DEMO do server giữ | Mở action M10 và kiểm DB/HTTP tương ứng; không dùng quyền CRM/CFO chung thay quyền khóa kỳ/đối chiếu. Chỉ tái dùng sau kiểm chứng invariant tương ứng |
| Lịch và nhắc việc | Draft M6/M7 đề xuất lịch typed chung; reuse catalog xác định lõi reminder/dedup/binding của trợ lý có sẵn | Một mô hình lịch dùng chung, không mỗi module một bộ lịch. Nhắc checklist dùng adapter chung khi có; mock transport trong DEMO, không gửi tin thật |

## 2. Ma trận yêu cầu → nguồn → tái dùng → output → ca → phụ thuộc

| Nhánh | Nguồn chuẩn | Tái dùng | Output phải xem/soát được | Ca DEMO độc lập | Phụ thuộc/gap thật |
|---|---|---|---|---|---|
| C9a doanh thu | Lịch đã duyệt C1d/M3, phiên bản HĐ/tham số và căn cứ sự kiện | CRM/master/version + lịch chung + V1 | Đề xuất kỳ có source row/version và amount đã xác định | Nhận lại/chạy lại không thêm; lịch chưa duyệt không thành bút toán | C1d sản xuất lịch trước; không suy lịch doanh thu từ lịch thu tiền |
| C9a KH/242 | Lịch/bảng đã tính C6b/M6, mã tài sản/đối tượng phân bổ | R_KH/catalog/lịch chung | Đề xuất và so kỳ trước, truy tới bảng đã tính | Kỳ 1m+2m kiểm đúng 3m; bảng 242 riêng, không tính lại | Mẫu/mapping/phương pháp production thiếu; M5 không cung cấp giá trị kho |
| C9a trích trước/335 | Bảng kế toán amount/kỳ/cơ sở đã duyệt, có thể dẫn hồ sơ M4 | K1 raw/version + lịch chung, link nguồn M4 | Nghĩa vụ định kỳ riêng, việc chờ thiếu căn cứ | 0,7m/kỳ nguồn tường minh; không cần gắn tài sản; nhận lại 0 mới | Mẫu 335/policy/tài khoản và hoàn nhập/điều chỉnh production chưa rõ |
| C9a lãi dự trả | Lịch được M9 xác nhận theo contract nguồn | #9/M9 giữ phép tính, typed lịch + V1 | Amount/lãi/kỳ/currency/căn cứ khoản vay rõ | Lịch 0,4m nguồn tường minh; không lấy export lãi hiện tại làm oracle lịch sử | C4a/M9 phải sản xuất lịch, precision và ngày tính có bằng chứng |
| C9a chống lặp/lô | Lịch đủ điều kiện, kỳ và snapshot inputs | Đề xuất/lô/artifact/recover chung | Một nghĩa vụ kỳ không bị tiêu thụ hai lần; lô/so kỳ trước có lý do lệch | Chạy tuần tự và hai worker cùng kỳ chỉ một kết quả hiệu lực | Unique/lock/recovery typed phải review, không chỉ khóa bằng nút UI |
| C9b checklist | Template và task có người/hạn/căn cứ, trạng thái các module/lô | Việc K5/V7/V8, `khoa_ky`, audit | Việc còn thiếu, người phụ trách, trạng thái, nguồn; kiểm sẵn sàng khóa | Còn treo/nguồn thiếu/phát sinh ngoài lô chưa xử lý → không khóa | Checklist thật và tiêu chí bắt buộc chưa có; template DEMO không thay chính sách thật |
| C9b khóa/mở lại | Kỳ/pháp nhân, checklist version, snapshot evidence và actor đúng quyền | `khoa_ky`, policy/ràng buộc chung | Khóa kỳ kèm bằng chứng; lịch sử mở lại/điều chỉnh có lý do | A khóa không ảnh hưởng B; race khóa↔duyệt/xuất không để lọt | Quyền khóa/mở lại và cách điều chỉnh sau khóa phải xác nhận trước vận hành thật |
| C9c mọi lô/L12 | Lô bất biến + sổ sau nạp, scope manifest/EntryID/khóa dòng | Parser Junsky, reconciliation/evidence/nhãn học chung | KHOP/LECH_GIA_TRI/THIEU_JUNSKY/THUA_JUNSKY; trường hợp chưa đủ căn cứ riêng | 4 expected/4 actual → 2 khớp, 1 lệch, 1 thiếu, 1 thừa | Mẫu xuất sổ/EntryID/GJ và phạm vi production chưa chứng minh |
| C9c xử lý lệch | Observation đã có bằng chứng, phản hồi người kiểm | V7 → V1 điều chỉnh/link/audit | Hồ sơ xử lý và chứng từ điều chỉnh riêng; bản gốc giữ nguyên | Bỏ qua/chấp nhận có lý do không biến sai thành KHOP; không học sai | Approval policy và kỳ điều chỉnh production còn thiếu |

## 3. Contract lịch trung tính và C9a

Tận dụng **một lịch typed chung** với gói M6/M7; M3/M4/M6/M9 là chủ nguồn. Tên bảng/field dưới đây là đề xuất để review DDL, không phải schema đã chốt:

- **Header/version:** pháp nhân, loại lịch `DOANH_THU/KHAU_HAO/PHAN_BO_242/TRICH_TRUOC_335/LAI_DU_TRA`, namespace/instance nguồn, source schedule ID, source document/row/version, artifact SHA256, profile/version/hash, ngày nghiệp vụ/hiệu lực và `known_at`, currency/scale, approval nguồn và approval dùng cho kế toán, supersedes/thu hồi có căn cứ.
- **Dòng nghĩa vụ kỳ:** stable source row/occurrence key, kỳ và ngày ghi nhận do nguồn cung cấp, amount nguồn đã xác định, đối tượng/dự án/tài sản/TTCP/khoản mục nếu áp dụng, basis/nguồn xác định amount, trạng thái hiệu lực. Giữ NULL khác 0, không cộng khác currency/cơ sở; dùng Decimal/minor units và giới hạn DB rõ, không round qua float.
- **Quan hệ sử dụng:** nghĩa vụ kỳ → phiên bản đề xuất → lô/dòng lô. Khóa logical occurrence phải sống qua revision: **chỉ unique `(source_version, kỳ)` là chưa đủ**, vì phiên bản mới cùng nghĩa vụ có thể xuất lần hai. Khi revision ảnh hưởng kỳ đã dùng, phải phát hiện và tạo việc xử lý/điều chỉnh; không reset khóa chống trùng bằng version mới.

Không lấy file name làm pháp nhân/kỳ/approval; không suy lịch doanh thu từ lịch thu, hoặc lãi dự trả từ số dư/lãi suất cuối kỳ hiện tại. Nguồn đã approved là evidence, không tự thành quyết định kế toán. Mẫu bút toán/tài khoản/rounding chỉ từ policy có phiên bản được duyệt; thiếu giữ hồ sơ và việc chờ cụ thể, không tạo cặp Nợ/Có giả để cho luồng xanh.

**Luồng DEMO:** nhận bảng/lịch đã tính → raw/hash/version → map catalog và kiểm tổng/cơ sở/kỳ → phê duyệt lịch theo quyền → “Chuẩn bị định kỳ” → preview các nghĩa vụ đủ điều kiện và so kỳ trước → V1 M10 chờ duyệt → duyệt tay → file soát/lô DEMO → đối chiếu bằng sổ giả sau nạp mô phỏng. Không có tự nhập hoặc tự duyệt. Lịch đến sau chỉ bổ sung đúng nghĩa vụ chưa dùng, không dựng lại khoản tiền M1 hoặc đề xuất do module nguồn đã xuất.

Ghi nhận `generation_run`/inputs/outputs bằng typed FK trong core hiện có, không chỉ log JSON. Trong một transaction PG: kiểm actor/PN/module/loại việc; chọn phiên bản có hiệu lực/as-of; khóa phạm vi kỳ/nghĩa vụ; kiểm lại khóa kỳ và consumption; tạo proposal/quan hệ sử dụng/audit. Hai worker hoặc retry sau lỗi trả cùng kết quả/việc chờ, không hai lần tiêu thụ. Chốt lại version fingerprint khi duyệt và xuất; thay lịch, mapping hoặc policy giữa preview và duyệt phải mở việc kiểm lại.

File soát dùng artifact writer/manifest/recover đang có. Phân biệt file soát và lô đủ điều kiện nạp; file soát không chứng minh đã nạp. Nếu ghi file ngoài transaction thất bại, giữ trạng thái chuẩn bị có thể recover và hash dự kiến; không báo thành công, không xóa file/lô để retry. Lô xuất xong bất biến; sửa sau xuất/nạp tạo chứng từ điều chỉnh theo TL37, không ghi đè file hoặc dòng gốc.

## 4. C9b — checklist và khóa kỳ

Đề xuất mô hình typed **template có phiên bản → checklist pháp nhân/kỳ → task → evidence/decision events**. Tái dùng `viec_can_duyet`, owner/due/status, cảnh báo và nhật ký; không phát minh V9 hoặc app quản lý công việc. Task checklist không phải bút toán nên không bị buộc phải có Nợ/Có; khi task tạo bút toán, dùng V1 chuẩn. Quy ước task loại nào đi vào V7/V8 và trường bổ sung phải được review với K5.

Checklist DEMO phải ghi rõ `MO_PHONG`, chủ nguồn, ngày áp dụng, version/hash và điều kiện nào là giả định. Tách **điều kiện hệ thống tính được** (kỳ, quyền, nguồn/phạm vi thiếu, việc/lô chưa xử lý, lỗi đối chiếu) với **việc người kiểm chứng** (căn cứ/nhận xét/quyết định có evidence). Một ô tick không vượt ràng buộc dữ liệu.

Trước khóa, hiển thị đầy đủ số việc chờ/bị chặn/ngoài phạm vi, lô chưa hoàn tất, nguồn chưa đủ/đến muộn, các lệch chưa xử lý; drill-down từng nguồn/lô/việc. Phạm vi theo các phần hành cấu hình áp dụng cho pháp nhân/kỳ; “không áp dụng” phải có lý do/người có quyền, không đánh dấu hoàn tất mọi M1–M9 khi chưa có dữ liệu hoặc chưa triển khai. **Còn treo thì liệt kê và chặn khóa**, không tự chuyển Vàng khi thiếu căn cứ/quy tắc CFO đã duyệt. Các câu chữ cũ “cuối tháng chuyển Vàng” không là quyền duyệt tự động.

Khóa chỉ thành công khi actor được cấp hành động khóa ở đúng PN/module, checklist/evidence snapshot còn hiện hành và điều kiện bắt buộc đạt. Dùng cùng lock giao dịch với các thao tác duyệt/sinh lô nghiệp vụ kỳ để tránh khoảng hở “kiểm xong rồi dữ liệu đổi”. Khóa phải chặn đúng các đường thay đổi nghiệp vụ/duyệt/sinh lô ảnh hưởng kỳ; vẫn cho phép tiếp nhận raw, xem/đối chiếu và tạo cảnh báo có kiểm soát, không mất chứng từ đến muộn. Không sửa ngược số kỳ đã khóa.

`khoa_ky` hiện chỉ là bản ghi khóa, chưa phải lịch sử mở lại. Review extension typed/state/event bảo toàn mọi lần khóa/mở và căn cứ; không triển khai mở lại bằng DELETE bản khóa. **Quyền mở lại và cách chọn kỳ điều chỉnh thật là gap nghiệp vụ**, chưa tự mặc định ai có vai CFO đều được mở. DEMO chỉ dùng policy giả công bố rõ; mở lại đúng quyền có lý do/bằng chứng, hoặc tiếp tục giữ chờ nếu chưa có policy. Không coi `CLOSED_FIXTURE` là khóa kỳ Junsky.

## 5. C9c — đối chiếu ngược mọi lô

Tái dùng parser sổ, artifact/hash/source manifest và kiểm identity/amount/fields đang có; mở rộng cho lô M1–M10, đặc biệt GJ không có bank reference. Contract cần `EntryID`/khóa chứng từ và dòng Junsky, pháp nhân, loại/ngày/kỳ/currency, TK, Nợ/Có và các chiều phải kiểm (ObjectID, ProjectID, TTCP, khoản mục, EntryDM, thuế… khi áp dụng). Không tự sinh EntryID production; mã giả chỉ trong DEMO có nhãn.

**Typed extension cần review:** header `doi_chieu_run` gắn lô + nguồn sổ + hash/profile + phạm vi/thời gian + actor; detail kết quả gắn expected dòng lô **hoặc** actual dòng sổ (để biểu diễn thừa), bằng chứng và field checks; liên kết cả hai phía khi match. FK/unique phải scoped PN; giữ các run cũ, projection hiện hành riêng. `lo_xuat_dong.doi_chieu` có thể là trạng thái hiện hành, không thay lịch sử quan sát. Không thêm JSON authoritative hoặc proposal giả cho dòng sổ ngoài lô.

| Kết quả | Điều kiện đủ để kết luận | Cách xử lý |
|---|---|---|
| `KHOP` | Khóa đủ mạnh, duy nhất; các dòng/amount/currency/các field bắt buộc khớp và nguồn có bằng chứng ghi sổ đầy đủ | Ghi bằng chứng từng dòng; chỉ lúc này mới xét điều kiện học TL38 và cutoff/eligible_at |
| `LECH_GIA_TRI` | Đã xác định đúng identity và có giá trị mâu thuẫn quan sát được | Nêu expected/actual/delta theo từng cơ sở/currency; lệch TK/chiều/danh mục cũng cần mã lý do field cụ thể, không chỉ tổng tiền |
| `THIEU_JUNSKY` | Expected thuộc lô nhưng không có actual, **nguồn sổ xác nhận đủ phạm vi** sau lần nạp cần kiểm | V7 điều tra/chờ nạp; không kết luận thiếu từ file không đủ scope |
| `THUA_JUNSKY` | Actual nằm trong phạm vi đối chiếu đã xác định nhưng không thuộc expected/không được giải thích bởi lô khác | Giữ actual evidence không fake proposal; điều tra nguồn/lô khác trước kết luận thừa |
| Chưa đủ căn cứ/khóa mơ hồ | Thiếu field/line, trùng EntryID, identity không duy nhất, nguồn cũ/thiếu scope hoặc parser chưa hỗ trợ | Trạng thái chưa kết luận riêng cần review DDL/UI; không ép thành khớp, thiếu hoặc lệch |

Expected là snapshot đề xuất **đã duyệt tại lúc xuất**, không dùng proposal/master mới nhất để thay bản đã xuất. Match theo khóa có căn cứ, không fuzzy tên hoặc chỉ tổng Nợ=Có. So sánh đầy đủ tập dòng/multiplicity và field typed; dòng không số thứ tự hợp lệ phải báo lỗi, không bỏ qua để tổng hash vẫn khớp. Không cộng tổng khác currency hoặc dùng ô trống thay 0; không bỏ lỗi precision >2^53.

Scope phải khai rõ pháp nhân/kỳ/loại chứng từ/lô và độ bao phủ sổ. Actual ngoài một lô nhưng thuộc lô khác hoặc phát sinh hợp lệ cần hiển thị “ngoài lô/chưa phân loại”, không tự gắn THUA. Khớp theo field chỉ được học field thực sự có evidence; cả chứng từ đủ điều kiện học theo TL38 khi đã đối chiếu KHOP, không chỉ vì người bấm “đã nạp”. Sổ đến sau, thay/cancel hoặc đối chiếu mới mâu thuẫn phải có event vô hiệu hóa eligibility thích hợp; không xóa nhãn/observation cũ hoặc rò cutoff.

Người nhập Junsky đánh dấu đã nạp kèm ngày/người/evidence theo quyền là bước riêng; đối chiếu không tự chứng minh đã nhập từ chính ứng dụng. DEMO dùng **nạp mô phỏng/sổ giả** với mode bắt buộc. Xử lý lệch tạo việc V7 và, khi cần/đủ policy, V1 điều chỉnh gắn bản gốc + run; người có quyền duyệt. “Chấp nhận lệch” có lý do là quyết định xử lý, **không đổi actual thành KHOP hoặc tự cho học**.

## 6. Review schema/quyền trước coding và màn hình bàn giao

Đầu ra review trước coding phải gồm: mapping TL38 → field hiện có/extension; migration mới với fresh/upgrade giữ dữ liệu/checksum cũ; FK/unique/check, actor/quyền/RLS, audit append-only, lock/idempotency/recovery; trạng thái chuyển hợp lệ và API/UI contract. Review cùng lịch typed M6/M7, tránh hai thiết kế lịch song song. Không lấy bảng tồn tại làm bằng chứng invariant đã đạt.

Mở quyền hành động tách **xem M10, chuẩn bị định kỳ, duyệt V1, xuất file soát/lô, ghi nhận nạp, đối chiếu/xử lý lệch, quản lý checklist, khóa kỳ, mở lại** theo PN/module/loại việc. Vai trò cụ thể theo policy DEMO công bố; production chưa chốt thì chưa cho dùng. Kiểm cả service/HTTP và SQL app role thường `NOSUPERUSER/NOBYPASSRLS`; helper `SECURITY DEFINER` cũng kiểm danh tính thực và scope, không dùng effective owner để bỏ qua quyền. Actor/PN từ server session, không từ body client; phiên người A/B không ảnh hưởng nhau.

Trong shell hiện có, lọc **M10 · PN · kỳ · loại việc · trạng thái**, có các thao tác/chi tiết:

1. **Lịch định kỳ:** nguồn/module/version, nghĩa vụ kỳ, amount/currency/cơ sở, policy, tình trạng đủ/chờ/đã dùng; nút chuẩn bị + preview/so kỳ trước, mở nguồn và lịch sử.
2. **Việc cần duyệt:** V1 M10 chung, lý do/field thiếu/chuỗi tới lịch và chứng từ nguồn; duyệt/sửa/bỏ theo quyền. Chưa đủ policy vẫn xem/soát được hồ sơ nhưng không có proposal giả.
3. **Checklist kỳ:** task/người/hạn/evidence, điều kiện hệ thống, cảnh báo phạm vi; “Kiểm tra sẵn sàng” giải thích từng blocker; khóa/mở lại có quyền, lý do và lịch sử.
4. **Lô & đối chiếu V7:** snapshot file/manifest/hash, mode DEMO, nạp mô phỏng và nhận sổ giả, tổng từng nhóm/field/dòng, việc xử lý và điều chỉnh. Tải bytes thực qua cùng quyền; thông tin kỹ thuật chi tiết nằm ở provenance, không nhét vào luồng kế toán nếu không giúp ra quyết định.

Có nút mở DEMO phù hợp launcher chung, không yêu cầu Anh nhập DSN/lệnh SQL. First open/reopen/restart giữ lịch, lô và history; không reset DB hoặc ghi đè log để “khởi tạo lại”. Không tuyên bố GUI đạt chỉ từ HTTP hoặc ảnh mock.

## 7. Corpus/ca DEMO độc lập và evidence yêu cầu

Fixture chỉ dữ liệu giả, hai PN, source ID/catalog scoped, amount đã được nguồn cung cấp tường minh; policy DEMO ghi rõ không phải chính sách kế toán thật. Expected viết trước output và ghi profile/hash; không sửa expected theo kết quả code. Chạy sau khi coder bàn giao terminal và khóa source snapshot; không chạy song song lúc Claude sửa.

| Ca | Dữ liệu/trigger | Kết quả phải chứng minh |
|---|---|---|
| D01 lịch nhiều nguồn | Kỳ có DT 4m, KH 1m+2m, 242 0,5m, 335 0,7m, lãi dự trả 0,4m; từng source/basis/currency riêng | Đúng **5 nhóm, 6 source rows** và tổng theo nhóm; không cộng lịch thu/tiền M1 hoặc tính lại amount; thiếu một policy chỉ chặn nhánh đó rõ ràng |
| D02 idempotency | Nhận cùng raw, bấm chuẩn bị hai lần; retry sau response mất | Source/occurrence/proposal/lô không tăng ngoài dự kiến; cùng request trả kết quả cũ; payload đổi không trả thành công cũ |
| D03 concurrency | Hai connection chuẩn bị cùng nghĩa vụ; observer chứng minh lock/đợi, thử cả thứ tự thắng | Một consumption hiệu lực; không deadlock giả hoặc hai lô. Timeout/setup không được tính pass |
| D04 revision | Cùng nghĩa vụ/version mới giảm 0,7→0,6 trước duyệt và sau xuất/nạp mô phỏng | Trước xuất kiểm lại/hoàn tác đúng; sau xuất giữ bản cũ, việc điều chỉnh có delta/căn cứ; không xuất đủ 0,6 lần hai |
| D05 nguồn chưa đủ | Lịch draft/thu hồi/tương lai, thiếu approval/basis/currency/profile; raw blank/0/negative | Giữ lỗi/chờ đúng nghĩa, không mặc định amount/policy; zero không bịa thành absent; negative chỉ theo contract có căn cứ |
| D06 quyền/PN | Actor CRM-only/V3-only/reader hoặc PN B gọi M10 A, body giả actor; hai browser sessions | Đọc/ghi/export/khóa/mở bị kiểm đúng quyền; legitimate control đạt trước negative; không lộ dữ liệu/chuyển vai giữa phiên |
| D07 closing | Task còn treo, thiếu nguồn/lô, chờ nạp, unresolved/ngoài lô chưa kiểm | Liệt kê blocker và không khóa; không chuyển Vàng/học/duyệt tự động; tick tay không vượt blocker |
| D08 khóa/race | A khóa, B mở; đồng thời khóa↔duyệt/sinh lô và thử SQL trực tiếp | Một thứ tự giao dịch hợp lệ, không lọt ghi nghiệp vụ kỳ đã khóa; raw đến muộn vẫn lưu/chờ, không mất evidence |
| D09 mở lại | Người thiếu quyền và người đúng policy DEMO mở lại kèm/lacking lý do | Không DELETE lịch sử; gate đúng, mọi lần khóa/mở có evidence. Không tự mở production |
| D10 bốn nhóm | Expected E1=100, E2=200, E3=300, E4=400; actual A1=100 khớp E1, A2=200 khớp E2, A3=350 cùng identity E3, A5=500 ngoài mọi expected trong scope | 2 KHOP, 1 LECH (50), 1 THIEU, 1 THUA: 4 expected/4 actual, **5 kết quả đối chiếu**, không nhầm thành 5 dòng nguồn. Chỉ 2 KHOP xét học |
| D11 scope/identity | Source trước xuất/cùng mốc, file thiếu kỳ, EntryID trùng, thiếu field/line, actual thuộc lô khác | Chưa kết luận/ngoài lô có lý do; không fake KHOP/THUA/THIEU. Thử GJ không có bank reference để chứng minh không phụ thuộc BANK |
| D12 đầy đủ field | Số tiền bằng nhưng sai TK/ObjectID/ProjectID/EntryDM/currency; cùng dòng lặp; `stt` text không hợp lệ | Field/multiplicity mismatch có evidence; không bỏ dòng hoặc chỉ so tổng/hash subset |
| D13 precision/file | Amount chính xác `100000000000000001` nếu trong giới hạn schema, chuỗi giống formula, NULL/0, currency scale rõ | DB→API→file đọc lại không đổi số, formula-safe, raw/hash đúng; vượt bigint/profile bị từ chối rõ; không chuyển float |
| D14 lifecycle | Trước xuất undo; sau xuất sửa; lỗi ghi file, recover, restart/reopen, đối chiếu lại cùng source/newsource | Không mất/ghi đè artifact, không tạo thêm lô/quyết định ngoài dự kiến; new run giữ old evidence, không lùi trạng thái bằng sửa/xóa |
| D15 L12/mốc học | Lô từ M1/M3/M6/M9/M10 DEMO; đánh dấu nạp nhưng thiếu sổ; observation mới mâu thuẫn hoặc known_at sau cutoff | Mọi lô có kết quả hoặc blocker rõ; nạp không đủ điều kiện học; eligibility/cutoff và event thu hồi đúng, không sửa lịch sử |

D01 phải ghi danh sách ID và expected cụ thể trong fixture; không dùng tổng đếm mơ hồ làm acceptance. Tổng same-currency chỉ là kiểm số nguồn khi thực sự cùng basis; không cộng các nhóm thành số hạch toán mới.

Evidence bàn giao: matrix yêu cầu→source/migration/API/UI→case→số trước/sau→actual outcome; PG fresh và upgrade có dữ liệu giữ checksum/history; role thường/RLS/direct SQL; concurrency hai connection có observer; artifact bytes/hash đọc lại; restart; GUI thao tác được với ảnh dữ liệu giả; regression các phần dùng chung sau coder terminal. Ghi pass/fail/setup/skip riêng, không tự báo 100% khi GUI/production còn chưa kiểm. Giữ toàn bộ file/temp/DB/evidence.

## 8. Phần làm tiếp được và quyết định thật còn thiếu

Sau review kỹ thuật có thể giao **neutral DEMO đủ chuỗi**: contract lịch/335/checklist và sổ giả có profile; nhận raw/version/typed rows; validator/mapping và việc chờ; lịch chung/idempotency; V1/lô/file soát; checklist/closing DEMO; đối chiếu bốn nhóm + chưa đủ căn cứ; điều chỉnh và audit; GUI/launcher/restart. Không đợi mở mức 2 để làm các phần này.

Các gap trước vận hành thật phải giữ trong backlog, tìm từ đúng nguồn hiện có trước khi hỏi Anh:

- Mẫu đang dùng cho 335/doanh thu/KH/242/lãi dự trả/checklist; source version/profile và người chịu trách nhiệm; không thay bằng sample tự dựng rồi coi đã chốt.
- Chính sách/căn cứ trích trước, hoàn nhập, kỳ/amount điều chỉnh; mẫu bút toán/tài khoản/các chiều, currency/rounding; quyền khóa/mở lại và tiêu chí bắt buộc/ngoại lệ checklist. Không chọn hộ bằng suy đoán tài chính hoặc luật thuế.
- Lịch đủ điều kiện từ M3/M4/M6/M9, version/approval và dữ liệu nguồn; không tạo phụ thuộc vòng bắt M10 tính lịch thay module nguồn.
- Contract Junsky GJ/EntryID/khóa dòng/mẫu xuất sổ/phạm vi và xác nhận mapping mức 2; nhập thử và vận hành thật là cổng riêng. Bốn nhóm DEMO hoặc bảng K2 tồn tại chưa phải nghiệm thu Junsky.

Không yêu cầu Anh mô tả lại K1–K5 hay phần mềm đã có. Root review bản này, hợp nhất thiết kế lịch chung và kiểm phần tái dùng trước khi giao Claude code. Sau DEMO vẫn tiếp tục nguồn/policy/tích hợp thật và liên kết L12 tới đủ module trong cây 33; không tuyên bố hoàn thành M10 hoặc toàn chương trình từ một lịch/lô chạy được.
