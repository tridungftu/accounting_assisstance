# Gói M5 — nhận phiếu kho số lượng và nối chứng từ kế toán

Ngày chuẩn bị: 19/10/2026. **Draft đầu bài để review trước coding; chưa triển khai/chạy/nghiệm thu M5.** Phủ C8a–C8b, R_KHO, L11 và bằng chứng L12 trong toàn cây 33. Chỉ đọc technical header/function, không đọc seed/sample/row thật/tên công ty/credential; không gọi app nguồn, Google API hoặc import/chạy product khi Claude còn sửa CRM. Không xóa file/temp/DB.

**Ranh giới đã chốt TL35 §8.6:** M5 chỉ số lượng nhập–xuất–tồn/cấp phát/kiểm kê, kèm liên kết hóa đơn/yêu cầu cấp phát/dự án/bộ phận. Giá nhập, giá xuất, giá vốn và giá trị/phân bổ 242 ở Junsky. M5 không sinh bút toán giá trị kho và không xây stock engine hay app kho thứ hai; #10 tiếp tục chủ CRUD/duyệt/đảo/kiểm kê và phép tính nguồn.

## 1. Căn cứ và năng lực dùng lại

- `CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md` M5/L11/L12; `LO-TRINH-TRIEN-KHAI-TOAN-BO-33.md` C8a–C8b; `HOP-DONG-TICH-HOP-VA-TAI-SU-DUNG-33.md` R_KHO; `DANH-MUC-TAI-SU-DUNG-PHAN-MEM.md` §5.
- TL35 §8.6, TL38 file gốc/chứng từ/dòng/link/nhật ký/pháp nhân; TL40 #10 là nguồn Google **đọc qua Sheets API**, không nối Apps Script vào PostgreSQL. Typed K2/quyền/link/K5/shell dùng chung sau review các gói nền; không coi việc có bảng là đã có runtime M5.
- Root kỹ thuật #10: `D:\Claude\Phan mem quan ly kho`. `Code.gs` hash `62f4658321ea6c6230a58cf850d49de43e2db826e5a66f807249de29af873e2c`; `9_SHEET_STRUCTURE.md` hash `223409715c11afadf0396fc5183497fc5d798064d5345c176bf7fa26c6ae3865`. Kiểm tra tĩnh, chưa chứng minh version đang deploy, quyền Google, web/PWA hoặc dữ liệu vận hành.

## 2. Contract source thực — giữ khóa, đơn vị và giới hạn

Header từ `Code.gs:19–49`; không dùng mẫu dữ liệu nguồn làm fixture:

| Sheet | Field kỹ thuật nhận / ý nghĩa |
|---|---|
| `DM_HangHoa` | `MaHang, TenHang, DVT_Goc, MaNhom, MaVach, DVT_QuyDoi, TonToiThieu, TonToiDa, GhiChu, TrangThai`; DVT_Goc là đơn vị gốc, DVT_QuyDoi được tài liệu mô tả là hệ số, chưa đủ chứng minh nhãn đơn vị thay thế/cách áp cho từng dòng |
| `DM_Kho` | `MaKho, TenKho, DiaChi, NguoiPhuTrach, TrangThai`; không có field pháp nhân được xác minh trong header này |
| `DM_DoiTac` | `MaDoiTac, TenDoiTac, Loai, MaSoThue, MaDoiTuong_KT, DienThoai, DiaChi, TrangThai`; `MaDoiTuong_KT` là đầu mối map ObjectID theo PN, không là quyền tự sinh mã Junsky |
| `DM_Nhom` | `MaNhom, TenNhom, TK_KeToan, GhiChu`; TK tham chiếu không được biến thành bút toán giá trị M5 |
| `GD_Phieu` | `SoPhieu, LoaiPhieu, NgayChungTu, MaKho, MaDoiTac, DienGiai, TrangThai, NguoiLap, NguoiDuyet, ThoiDiemDuyet, SoPhieu_Goc` |
| `GD_Dong` | `ID_Dong, SoPhieu, MaHang, SoLuong, GhiChu`; **không có UOM riêng từng dòng** hoặc mã dự án/bộ phận đã kiểm |
| `GD_KiemKe` | `ID_KK, DotKiemKe, NgayKiemKe, MaKho, MaHang, SL_SoSach, SL_ThucTe, ChenhLech, LyDo, NguoiDem, TrangThai`; số kiểm kê chưa nhập khác số 0 |
| `HT_CauHinh`, `HT_NhatKy` | Header tương ứng `Key/Value` và `ThoiDiem/NguoiThucHien/HanhDong/DoiTuong/NoiDung`; chỉ whitelist thông số/bằng chứng cần thiết, không đọc nguyên cấu hình vào prompt hoặc coi log là approval kế toán |

### Các function và khác biệt với giả định cũ

| Điểm neo | Fact đã đọc | Ảnh hưởng bridge |
|---|---|---|
| `taoPhieu:202–239` | Tạo header `Nháp` và dòng; nhận `SoPhieu_Goc`; ID dòng theo `ID_ + Date.now()` | Cần kiểm key trùng/mồ côi từ snapshot; không tự đổi ID hoặc lấy row number làm ID vĩnh viễn. Cùng mã dòng khác nội dung phải cách ly |
| `duyetPhieu:246–269` | Ghi `Đã duyệt`, người và thời điểm nguồn | Là duyệt **nguồn kho**, không tự là duyệt mapping/liên kết/kế toán |
| **`daoPhieu:275–295`** | **Đổi chính header cùng SoPhieu sang `Đã đảo`**, có log; không tạo phiếu âm/dòng đảo mới, không tự điền SoPhieu_Goc | Không bắt nguồn phải xuất phiếu âm tưởng tượng. Theo dõi revision/trạng thái cùng phiếu, giữ bản đã nhận và phản ánh hết hiệu lực; nhận lại không đảo lần hai |
| `getPhieuList:300–326`, `getPhieuDetail:328–360` | Đọc header và `{phieu,lines}` theo tên cột; detail có ID_Dong | Interface nguồn đủ dùng để thiết kế adapter; chưa gọi runtime. Snapshot cần header/master/phạm vi đầy đủ, không chỉ list rút gọn |
| `getTonHienTai:151–193` | Chỉ tính phiếu `Đã duyệt`; cộng Nhập/trừ Xuất; dùng `parseInt(SoLuong)||0`, lọc **MaHang, không MaKho**; còn TODO điều chỉnh GD_KiemKe | Không gọi số này là tồn theo kho/đã gồm kiểm kê hoặc chính xác cho lượng phân số. Giữ nguồn/phạm vi/phương pháp; thiếu căn cứ thì “chưa kiểm chứng”, không tự sửa bằng stock engine kế toán |
| `taoKiemKe:419–448` | Tạo dòng theo hàng hóa, SL_SoSach từ getTonHienTai, SL_ThucTe/ChenhLech ban đầu rỗng, `Đang đếm` | Có workflow nguồn, chưa chứng minh tự điều chỉnh tồn sau kiểm kê. Không dùng SL_SoSach đó làm tồn đúng từng MaKho khi source chưa lọc kho |
| `exportToExcel:459–507` | Tạo spreadsheet/file qua Drive, trả **`{fileName,url}`**; tên có đuôi `.xlsx` không chứng minh bytes XLSX | Là mutation tạo file Google, không là đọc thuần. Không phụ thuộc đường export; bảng xuất thiếu ID_Dong/trạng thái/approval/SoPhieu_Goc nên không đủ canonical contract đầy đủ |
| `doPost:688–759` | Cùng dispatcher có action đọc và ghi/duyệt/đảo/xóa dòng/export; `doGet:771–795` phục vụ UI/PWA | Không gọi endpoint vì tên POST mà cho toàn quyền; ưu tiên Sheets API scope readonly. Không chạy setup/create/export để “đọc thử” |

Không thấy `ensureSheet` trong `Code.gs` đã đọc; `setup()` tạo sheet là mutation riêng. Các hàm đọc nêu trên dùng getSheet/getValues, không gọi setup trong body đã kiểm; điều này **chưa chứng minh deployment/wrapper hiện hành thuần đọc**. Pin hash và kiểm lại call chain trước vận hành, không suy từ audit #9 rằng #10 cũng có load→ensureSheet.

**Cần sửa giả định của đầu bài cũ khi review:** R_KHO từng mô tả “phiếu đảo → bút trừ có SoPhieu_Goc”; source hiện tại chủ yếu là trạng thái `Đã đảo` trên cùng khóa. Adapter phải hỗ trợ đúng profile đã pin và giữ lịch sử trạng thái; một chứng từ đảo riêng chỉ nhận khi nguồn thực có khóa/quan hệ/căn cứ riêng. Không sinh cả một khoản trừ suy diễn và một lần loại phiếu để đảo kép.

## 3. K1 readonly, snapshot và namespace

Vận hành đích: Sheets API service account **readonly**, whitelist spreadsheet/range/field; credential ở `.env` cục bộ, không vào prompt/report. Apps Script vẫn là nguồn vận hành, không ghi PostgreSQL. File/JSON DEMO đúng contract dùng để phát triển/kiểm thử, không chuyển đích thành CSV tay. Chưa có quyền Google/file đang dùng là gate vận hành, không chặn chuẩn bị adapter DEMO.

Manifest dùng registry chung: instance nguồn ổn định, profile/schema/header hash, PN mapping version, khoảng snapshot/time server, scope kho/loại phiếu/trạng thái/kỳ, row count, file/hash/size, master version, success/partial/error. Một snapshot nhiều sheet cần cùng phạm vi/as-of hoặc phát hiện lệch lần chụp; orphan/missing detail không được promote thành phiếu hoàn chỉnh. Không có dữ liệu hoặc mất row không tự là số tồn0, phiếu hủy hay xóa master.

Namespace tối thiểu `(source_instance, phap_nhan, SoPhieu)` và `(source_instance, phap_nhan, SoPhieu, ID_Dong)`; master theo instance/PN/MaKho/MaHang/đơn vị và version. Không có PN trong row nguồn thì mapping spreadsheet/MaKho→PN phải tường minh/có người xác nhận, không suy tên kho. Trùng ID_Dong trong cùng phiếu, một dòng chỉ tới nhiều header, SoPhieu_Goc trỏ sai PN/kho/hàng hoặc vòng lặp → chờ xử lý, không chọn dòng cuối. Việc đưa SoPhieu vào khóa dòng không thay kiểm chứng ID_Dong có bền/duy nhất theo profile.

Giữ LoaiPhieu raw, TrangThai raw, ngày nguồn, người/lúc duyệt; chuẩn hóa qua mapping profile đã review. `Đã duyệt` mới đủ điều kiện nhận vào tập phiếu nguồn có hiệu lực; `Nháp` giữ raw/coverage nếu cần, không vào tập đã duyệt. `Đã đảo` đã từng nhận phải được nhận như **thay đổi trạng thái**, không lọc bỏ rồi giữ phiếu cũ hiệu lực mãi. Snapshot đầu tiên chỉ thấy phiếu đảo nhưng thiếu bản trước thì giữ hồ sơ/trạng thái/giới hạn, không bịa số phát sinh trước đó.

Revision mới khi nội dung/trạng thái quan trọng thay đổi; cùng snapshot/ngữ nghĩa nhận lại → delta canonical/logical phiếu/dòng/link = 0. Log lần lấy có thể tăng. Lưu business_date, known_at do server ghi, approval nguồn và approval kế toán riêng; source backdate/đổi trạng thái hôm nay không thay lịch sử/cutoff đã biết. Không rewrite file hoặc snapshot cũ.

## 4. Số lượng, UOM và mapping kế toán

SoLuong giữ Decimal/text exact, scale/UOM khai báo; phân biệt NULL/blank/0, số âm theo ý nghĩa nguồn đã xác nhận, không tự parseInt/rounding hoặc thêm dấu đảo. Nguồn đã bị Number/parseInt/Excel làm tròn thì receiver không phục hồi chữ số; cần precision contract/bằng chứng gốc, giữ giới hạn thay vì gọi hash khớp là đúng lượng gốc.

DVT_Goc lấy từ master đúng version; vì detail không có UOM, phải xác nhận SoLuong đang theo đơn vị nào và DVT_QuyDoi dùng ra sao. Không tự lấy hệ số mới nhân lịch sử, coi hệ số là nhãn đơn vị, hoặc cộng kg/cái/m². Thay UOM/hệ số tạo master version; chưa rõ quy đổi → giữ lượng raw/chờ, không xuất so sánh lượng đã chuyển đổi. Mã hàng tương đương giữa hóa đơn/RQ/kho cần mapping có phiên bản/approval, không fuzzy theo tên.

Mapping PN, MaKho, MaHang/UOM, MaDoiTac→ObjectID Junsky theo PN, dự án/ProjectID, bộ phận/TTCP và RQ/yêu cầu cấp phát phải có nguồn/căn cứ/version. Source header hiện không có dự án/bộ phận/invoice ID: chỉ bổ sung qua link/cấu hình được duyệt, không dựng từ GhiChu. Mã Junsky do Junsky cấp. `DM_Nhom.TK_KeToan` không tự cấp quyền định khoản hoặc tính giá trị kho. Không tạo 242, giá vốn, phiếu thu/chi hoặc bút toán hàng tồn kho trong M5.

## 5. Ma trận yêu cầu → reuse → output → DEMO → gap

| Yêu cầu | Căn cứ/API/field | Dùng lại | Output kế toán hỗ trợ | Ca DEMO | Gap |
|---|---|---|---|---|---|
| Nhận phiếu đã duyệt | GD_Phieu/GD_Dong; getPhieuDetail | #10 và K1/raw/hash/evidence | PHIEU_KHO + dòng số lượng truy nguồn | Hai PN, cùng số phiếu/mã hàng không trộn; nháp không thành duyệt | Profile/header/phạm vi/Google auth thật |
| Nhận trạng thái đảo | Cùng SoPhieu `Đã duyệt→Đã đảo`; SoPhieu_Goc nếu thật có | Source daoPhieu; revision/audit chung | Bản cũ còn xem, trạng thái hiện hành đúng; cảnh báo link cần soát | Nhập10/xuất4; đảo **toàn phiếu xuất4**: nguồn loại phiếu đó, không suy thành đảo1; nhận lại không đảo kép | Partial reversal/chứng từ đảo riêng chỉ làm khi source có contract |
| Tồn từ nguồn | getTonHienTai hoặc snapshot tồn có producer/scope | Giữ phép tính #10 | Snapshot **số lượng nguồn** với phương pháp/phạm vi/giới hạn, không ledger tồn mới | Hai kho cùng MaHang; lượng phân số/kiểm kê chưa hoàn thành phải ghi chưa kiểm, không số0 | Chưa chứng minh snapshot tồn theo kho/UOM đúng; aggregate hiện toàn mã hàng, còn TODO kiểm kê |
| Kiểm kê | GD_KiemKe, status/căn cứ đếm | Workflow #10 | Hồ sơ số sách/thực tế/chênh nguồn + việc chờ | SL_ThucTe rỗng khác0; Đang đếm không tự điều chỉnh; revision giữ lịch sử | Quy trình chốt/điều chỉnh nguồn và producer tồn thực |
| L11 nhập kho↔hóa đơn | Key dòng phiếu/hàng/UOM/ObjectID, INVOICE line/RQ | Link/phân bổ chung M2, một dòng một đích | Link lượng cùng cơ sở; thiếu/khớp/lệch có căn cứ | HĐ10↔phiếu8 lệch2 khi cùng UOM; HĐ nhiều phiếu/phiếu nhiều HĐ; trước/sau HĐ không nhân công nợ | Mapping mã hàng/UOM/đích KHO và quan hệ invoice/RQ thật |
| Cấp phát/dự án/bộ phận | Phiếu xuất + RQ/link/cấu hình đã duyệt | #10, RQ/M2/core master | Hồ sơ số lượng và nơi sử dụng, không phân bổ giá trị | Thiếu dự án/bộ phận không tự điền; cross-PN/link sai kho từ chối | Chưa có các field đó tại header nguồn đã kiểm |
| L12/file soát | Snapshot/revision/link/việc/kỳ | K5/lô/file registry chung | File soát số lượng và chênh, lịch sử xử lý | Restart/dedup/quyền/kỳ khóa/tải file; không có cột giá trị hạch toán | Schema extension/runtime và web pilot chưa có bằng chứng |

## 6. K5, quyền và ranh giới thao tác nguồn

Shell chung: **Nhận snapshot DEMO → xem coverage/lỗi → mapping → danh sách phiếu/dòng/nguồn trạng thái → nối HĐ/RQ/dự án/bộ phận → xem chênh/đảo/kiểm kê → xác nhận hoặc yêu cầu bổ sung → xuất file soát số lượng → xem lịch sử/restart**. Có label truy cập được, server xác thực actor–hành động–PN/module và RLS/FK cùng PN; DEMO actor `MO_PHONG_`, không duyệt thật/CFO_NTD/mức2 Junsky.

Nút “Mở phần mềm kho” chỉ mở ứng dụng đã có khi địa chỉ đã xác nhận; tạo/duyệt/đảo/kiểm kê thực hiện tại **#10** theo quyền nguồn. K5 chỉ kiểm mapping/liên kết/hồ sơ kế toán và xử lý ngoại lệ, không gửi action `taoPhieu/duyetPhieu/daoPhieu/taoKiemKe/deletePhieuLine/exportToExcel`. Quyền xem hoặc chốt liên kết kế toán không nâng quyền thủ kho và không sửa source approval. “Điều chỉnh” ở K5 là đề nghị/hồ sơ chờ; không tự sửa tồn hay giá trị Junsky.

Phiếu đảo/thay revision làm link cũ cần soát: giữ link/hồ sơ đã chốt, tạo việc và trạng thái hiệu lực mới, không tự xóa/cấn trừ/chuyển sang phiếu khác. Gỡ/xác nhận link phải transaction và idempotency, kiểm quantity còn khả dụng theo đúng nguồn/UOM/phạm vi; không double allocation. Invoice tới sau chỉ thêm bằng chứng/liên kết, không thêm INVOICE/công nợ/phiếu/khoản tiền lần hai. Kỳ/lô khóa theo cơ chế chung và đường xử lý có vết, không rewrite lịch sử.

## 7. Typed extension đề xuất — chưa chốt/chưa được phép migrate ngay

Tái dùng `tep_goc/chung_tu(loai=PHIEU_KHO)/chung_tu_dong` và link/evidence chung; JSONB giữ raw/locator/cảnh báo, không thay FK/quantity/UOM typed cần kiểm. Cần review core runtime sau CRM trước quyết định có cần extension:

- Source observation/snapshot: instance/profile/hash, PN/scope/known_at/coverage, source header/row/version/status/approval provenance; giữ immutable revision thay đổi và source-key uniqueness.
- Dòng phiếu hoặc extension typed tham chiếu đúng chứng từ/dòng hiện có: MaKho/MaHang được map, SoLuong numeric exact, UOM/master version, source ID_Dong, trạng thái/quan hệ đảo; không thêm amount/unit cost/inventory value.
- Chỉ khi nguồn thực xuất tồn: bảng snapshot tồn **không phải stock ledger**, có source/PN/kho hoặc phạm vi aggregate rõ, hàng/UOM/as-of/quantity/phương pháp/giới hạn, hash/căn cứ. Nếu không có producer đủ căn cứ thì chưa tạo số giả để lấp bảng.
- Link chung mở loại/tham chiếu dòng kho–invoice–RQ nếu chưa đủ: FK/type/entity/reference rõ, quantity+UOM phù hợp, unique/idempotency/undo-audit; không lập bảng link riêng chỉ M5 hoặc giả ID_Dong thành ID hóa đơn.

Tên bảng/cột/constraint cụ thể và migration có version là **đề xuất phải review trước coding**, không là schema đã chốt hoặc đang vận hành. Kiểm reference cha/con cùng snapshot/PN, key trùng, master version/UOM, các source status transitions và scope; không dùng soft-default để né FK hoặc coi missing=0. Không xây stock engine để bù thiếu producer nguồn.

## 8. Nghiệm thu sau triển khai và gap giữ nguyên

Sau khi giao coding: Claude tự chạy unit/PG/upgrade với dữ liệu DEMO và role thường; Codex/agent độc lập kiểm negative cases, hai PN, input/output actual, restart/UI/file soát bytes/cell. Nguồn chỉ được đọc; kiểm hash trước–sau không đổi. Tập rỗng/skip/cùng lỗi/so tổng nguồn bị parseInt không đủ chứng minh lượng chính xác. Thử phiếu đã duyệt→đảo cùng key, bị sửa nội dung không có revision, ID trùng, orphan, missing master/UOM, partial multi-sheet, unknown status, số lượng phân số/lớn, invoice/RQ link một phần/nhiều dòng, thiếu/quy đổi UOM và FK/RLS/kỳ khóa.

**Gap thật:** file/profile đang deploy và Google readonly; mapping PN/kho/hàng/ObjectID/dự án/bộ phận; semantics UOM/precision/quy đổi; source ID_Dong trùng khả dĩ từ Date.now; producer tồn theo kho/kiểm kê; quy trình chốt điều chỉnh nguồn; web/PWA pilot; extension typed và interface core cuối. Các phần này là công việc phải hoàn thiện của toàn33, không mặc định đã đạt hoặc tự thay bằng giá trị0. Không yêu cầu Anh mô tả lại CRUD/duyệt/đảo đã có; kiểm technical artifact có sẵn rồi chỉ đưa quyết định/mẫu/quyền thật còn thiếu.

**Hướng hoàn thiện tại source/contract để review sau, chưa được triển khai trong gói chuẩn bị:** (i) export snapshot chỉ đọc có version/scope/row counts/master UOM và cả phiếu đã duyệt/đã đảo, không tạo Drive file hoặc gọi setup; (ii) producer tồn phiên bản mới trong **#10** nhận rõ kho/hàng/as-of và trạng thái kiểm kê, giữ interface cũ tương thích, để kế toán chỉ nhận snapshot; (iii) sửa bảo toàn precision/UOM trước parseInt/Number ở nguồn, rồi kiểm ca lượng phân số/lớn và dữ liệu cũ đã mất precision, không dùng Decimal receiver để giả phục hồi; (iv) ID dòng mới ổn định/duy nhất và kế hoạch xử lý duplicate cũ có audit, không đổi ID lịch sử tùy tiện; (v) lịch sử duyệt/đảo có event/version/căn cứ rõ. Riêng `duyetPhieu` hiện ghi Đã duyệt cho khóa tìm thấy mà chưa thấy kiểm trạng thái trước, nên không suy tính bất khả đảo ngược chỉ từ comment của `daoPhieu`. Review transition/nguồn history phải bao gồm ca đảo rồi duyệt lại. Những sửa đổi này thuộc source #10 và cần gói/quyền/kiểm triển khai riêng trước vận hành thật; không sửa source ngoài nhiệm vụ, không viết bù stock engine ở kế toán, không loại tồn theo kho/kiểm kê ra khỏi toàn M5.

Lưu báo cáo yêu cầu→source→implementation→DEMO→bằng chứng→trạng thái, cập nhật coverage khi đã kiểm. Một adapter phiếu không tự là toàn M5/L11/L12 hoàn thành; source limitation phải hiện rõ, không giấu bằng app kho mới, phép tính giá vốn hoặc test xanh giả.
