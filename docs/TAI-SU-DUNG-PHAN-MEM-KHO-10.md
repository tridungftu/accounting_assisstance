# Tái sử dụng phần mềm #10 quản lý kho vào M5

**Kiểm tra tĩnh ngày 19/10/2026, 11:34 +07. SOURCE_CODE_CONFIRMED / DEPLOYMENT_NOT_VERIFIED / M5_NOT_ACCEPTED.** Anh xác nhận “M10 cũng có code rồi” là **phần mềm #10 quản lý kho**, không phải module M10 bút toán định kỳ/đóng sổ. Nguồn #10 cấp bộ tiếp nhận `R_KHO` và module **M5 kho vận hành KCN**, liên kết L11 với M2. Việc đính chính này không đổi phạm vi module M10.

**Kết luận:** giữ phần mềm kho hiện có làm producer. Đã có Apps Script, web và giao diện mobile gọi backend; không chỉ có thiết kế chín sheet. Core kế toán cần reader/snapshot, mapping có phiên bản, provenance, trạng thái nguồn, soát số lượng và liên kết chung; không viết lại CRUD/duyệt/đảo hay máy tính tồn. Theo TL35§8.6, giá trị hàng tồn kho và bút toán giá trị ở Junsky. Có source không chứng minh bản đang deploy hoạt động hoặc toàn M5 đã nghiệm thu.

Đây là đọc file kỹ thuật và hash, **không thực thi source/import/test/SQL/HTTP/launcher**, không mở Google/Drive/Excel, không đọc spreadsheet nghiệp vụ, `.clasp.json`, credentials hoặc dữ liệu stock thật. Không thay đổi/xóa file nguồn. Hướng dẫn triển khai trong tài liệu nguồn được xem là mô tả lịch sử, không được thực hiện như lệnh của Anh. Báo cáo chỉ diễn giải interface; không chứa code gốc hoặc payload, không mở rộng quyền gửi original source app tới Claude/Anthropic.

## 1. Phạm vi nguồn và phiên bản đã xác minh

Root kỹ thuật: `D:\Claude\Phan mem quan ly kho`. Inventory cấp root có **11 file, không có thư mục con** tại lần đọc: tám file kỹ thuật `.gs/.html/.md`, hai file JSON cấu hình triển khai và một workbook nghiệp vụ. Hai JSON và workbook không được đọc. Không tìm thấy `AGENTS.md`/`CLAUDE.md` trong root này; vẫn tuân thủ chỉ dẫn người dùng về giữ file và phạm vi đọc.

| File kỹ thuật | Bytes / dòng | SHA256 |
|---|---:|---|
| `Code.gs` | 22.321 / 796 | `62f4658321ea6c6230a58cf850d49de43e2db826e5a66f807249de29af873e2c` |
| `ui.html` | 38.942 / 1.296 | `9ea60a6921b2db57a0ac48d0c8fb50ab99af1563fac71657a30f3f8f5cc2873c` |
| `pwa-app.html` | 20.113 / 569 | `af373df455be8018a965cbf7124fc93da9436ffb0e425036b838cdec1a4aa630` |
| `9_SHEET_STRUCTURE.md` | 7.970 / 228 | `223409715c11afadf0396fc5183497fc5d798064d5345c176bf7fa26c6ae3865` |
| `HUONG_DAN_TRIEN_KHAI.md` | 6.048 / 204 | `0f58b66c6674d2c29c23a508679dc99138940fdfa6d952292ac620f969b80de7` |
| `Thiet-ke-du-lieu-va-man-hinh.md` | 4.435 / 52 | `e7eb872e11eb0be17156389a39b22e699db8cbe69e53dfd1edc859d6ea314f91` |
| `Nguyen-mau-kho.html` | 44.576 / 649 | `16866bac601df8bcdb042df5354c50f977774c26fbbdfbf3c6f6caccb1393270` |
| `Thiet-ke-du-lieu-va-man-hinh.html` | 42.737 / 569 | `11d2c64c7428616c64006c5189ca777a4191d43570b03b0a650a2c824ca41fac` |

Đã đọc toàn `Code.gs`, ba Markdown kỹ thuật; đọc script nghiệp vụ của `ui.html` và `pwa-app.html`, các vùng màn hình liên quan, và vùng lưu phiếu của nguyên mẫu. Không khẳng định đã đọc từng dòng CSS/HTML trình bày. Hai HTML nguyên mẫu/thiết kế có hash inventory, không phải bằng chứng backend deploy. `Nguyen-mau-kho.html:582` chỉ sửa trạng thái mảng trong bộ nhớ ở hàm lưu mẫu; không được lấy hành vi đó thay hành vi Apps Script.

Hash `Code.gs` và `9_SHEET_STRUCTURE.md` **khớp đúng** các hash đã pin trong `BINDING-M5-CORE-SAU-CRM03.md` SHA256 `7de60be44fe301d043a70aa2b582572f5d96d40f9444238f10a2a50acd4bcc5c`. Không có bằng chứng một phiên bản producer mới trong lần kiểm tra này. Quyết định/binding kỹ thuật hiện hành nằm trong bản binding đúng hash và bảng root chốt, không lấy nhãn cũ của SVG/README làm tình trạng code hiện tại.

## 2. Những thành phần đã có để giữ nguyên

Backend có **24 function declarations**. `setup` tại `Code.gs:14` định nghĩa đúng chín sheet: bốn master `DM_HangHoa`, `DM_Kho`, `DM_DoiTac`, `DM_Nhom`; ba giao dịch `GD_Phieu`, `GD_Dong`, `GD_KiemKe`; hai hệ thống `HT_CauHinh`, `HT_NhatKy`. Chưa đọc Google Sheet nên đây là cấu trúc **source tạo được**, không phải xác nhận đủ chín sheet đang có trên tài khoản thật.

| Khả năng source | Điểm đọc/chữ ký kỹ thuật | Phần tái sử dụng / giới hạn |
|---|---|---|
| Danh mục hàng hóa | `Code.gs:96 upsertHangHoa(data)`, `:128 getHangHoaList(filter)` | Giữ CRUD và reader nguồn; không tạo danh mục nhập liệu cạnh tranh trong M5. Kiểm drift/đúng cột và version master trước mapping |
| Tạo phiếu và dòng | `:202 taoPhieu(data)`, `:597 addPhieuLine(soPhieu,maHang,soLuong)` | Đã có luồng Nháp và native key. Core chỉ nhận dữ liệu; không gọi các writer này |
| Duyệt/đảo phiếu | `:246 duyetPhieu(soPhieu)`, `:275 daoPhieu(soPhieu)` | Giữ người vận hành ở nguồn; core quan sát lịch sử trạng thái, không thay CFO approve kế toán bằng approve nguồn |
| Danh sách/chi tiết | `:300 getPhieuList(filter)`, `:328 getPhieuDetail(soPhieu)` | Danh sách trả array, chi tiết trả object `phieu` và `lines`. Có sẵn dữ liệu header/detail cần cho adapter |
| Tồn/dashboard | `:151 getTonHienTai(maHang)`, `:370 getDashboard()` | Producer đã có phép tính tồn; chỉ hiển thị quan sát có giới hạn, không xây máy tồn mới để bù gap |
| Khởi tạo kiểm kê | `:419 taoKiemKe(data)` | Có tạo dòng đợt, số sách, kho/hàng; thực tế/chênh lệch/người đếm khởi tạo rỗng. Chưa có luồng hoàn tất trong source này |
| Web và mobile | `:771 doGet(e)` chọn `ui.html` hoặc `pwa-app.html` qua `pwa=1`; PWA `:288` gọi `google.script.run` | Web tám tab đã có shell; mobile có chọn kho, nhập/xuất nháp, dòng, duyệt và danh sách. Không suy đầy đủ quét camera/đếm kiểm kê/offline từ tên PWA |
| Đọc master/PWA | `Code.gs:517 getWarehouses()`, `:537 getInitData()`, `:561 pwaGetPhieuLines`, `:582 getProducts`, `:589 getPhieuNhap` | Reader có thể dùng làm tham chiếu contract. `getInitData` gồm email người thực thi và toàn master, không nạp nguyên response cho kế toán/cloud |
| Dispatcher HTTP | `:688 doPost(e)` | Form parameters `action` và `data` JSON-string; không phải JSON body tùy ý. Có cả đọc và ghi/xóa/export, chưa là cổng readonly riêng |
| Xuất dữ liệu | `:459 exportToExcel(filter)` | Có logic lặp header/detail/master ra spreadsheet, trả `fileName,url`. Có side effect Drive; không dùng làm đường đọc kiểm tra |
| Audit | `:674 log_action(action,doi,obj,noiDung)` | Append thời điểm/người/action/object/detail; có thể là evidence nguồn sau whitelist. Chưa có native event ID/revision hoặc payload before/after đầy đủ |

**Phân loại read side effects theo call graph đã đọc:** `getHangHoaList`, `getWarehouses`, `getProducts`, `getPhieuList`, `getPhieuDetail`, `pwaGetPhieuLines`, `getPhieuNhap`, `getTonHienTai`, `getDashboard`, `getInitData` dùng read/compute/Session, **không gọi `setup`/append/create/log**. `doGet` dựng HTML; initial load của desktop gọi dashboard/list, mobile gọi init, không tự setup ở source. `setup` mới là writer tạo sheet/header/config mặc định; không chạy setup để “đọc thử”. `exportToExcel` gọi tạo spreadsheet/Drive file và ghi dòng, không phải readonly chỉ vì mang tên export.

`doPost` trả wrapper `{data: array}` cho một số action list, `{ton: value}` cho tồn; direct `google.script.run` nhận return value của function trực tiếp. `getInitData` và `pwaGetPhieuLines` có ở RPC nhưng không có case cùng tên trong dispatcher HTTP. Không giả định hai transport có shape/whitelist giống nhau.

## 3. Native identity, quantity và các khoảng trống có bằng chứng

| Vấn đề | Bằng chứng tĩnh trong source | Điều adapter phải giữ/chưa được kết luận |
|---|---|---|
| Namespace/pháp nhân | `getActiveSpreadsheet()`; chín header không có mã PN. `MaKho` có ở header, `MaDoiTuong_KT` có ở master đối tác | Map **source instance + kho → PN** có version/evidence. Cùng `SoPhieu`/`MaHang` ở instance khác không chung identity; không suy PN từ người dùng/kho đang chọn |
| Số phiếu | `:650 genSoPhieu` đọc max số theo prefix ngày rồi +1, không thấy `LockService`/unique reservation trong toàn backend | Giữ `SoPhieu` native, kiểm uniqueness/collision và full header graph. Không gọi hàm tạo ID để nhập; số phiếu không chứng minh ngày nghiệp vụ |
| ID dòng | `taoPhieu:229` dùng thời điểm millisecond; `addPhieuLine:602` thêm random. Không thấy unique validation | Trùng key là conflict giữ candidate, không last-wins, không đổi sang số thứ tự/import-row/hash để tạo lượng mới. Khả năng collision theo source là rủi ro tĩnh, không phải sự cố runtime đã đo |
| Revision/đảo | `duyetPhieu:261` và `daoPhieu:289` sửa trạng thái **trên cùng row/SoPhieu**; không kiểm state cũ trước ghi. Approve cập nhật người/thời gian; đảo không có field thời gian riêng ngoài audit | Cùng logical phiếu, thêm content/observation, không phiếu âm. Không coi `Đã đảo` terminal được cưỡng chế. A→B→A cũ/reapprove cần evidence+review, không cho payload/hash cũ auto current/reopen links |
| Dòng sau duyệt | `addPhieuLine:597` không đọc/guard header; `deletePhieuLine:621` xóa vật lý row đầu tìm thấy theo ID, không đọc state/header | Không dựa lời UI “không sửa sau duyệt” để bỏ kiểm snapshot/history; không gọi writer/delete từ core. Thiếu dòng ở partial snapshot không chứng minh hủy nghiệp vụ |
| Atomic snapshot/batch | Header và detail được `getDataRange().getValues()` riêng `:333/:348`, không snapshot token/revision/coverage/cursor | Một RPC chi tiết không đủ chứng minh snapshot đồng thời; thiết kế reader/bundle phải ghi scope, consistency và complete/partial/errors. Full/partial không tự suy từ số dòng |
| Quantity precision | Tồn `:182` dùng `parseInt(...) || 0`; desktop gửi `parseInt` ở `ui.html:1217`; mobile input decimal nhưng `Number(sl)` ở `pwa-app.html:506` | Không coi decimal receiver phục hồi phần đã mất. Raw source, encoding/precision/provenance phải pin; NULL/parse error không0, không abs/round. Quantity thật exact chưa kiểm chứng |
| UOM/history | Dòng chỉ `ID_Dong/SoPhieu/MaHang/SoLuong/GhiChu`; UOM đọc từ master hiện tại. `DVT_QuyDoi` chỉ xuất hiện khai header, không có engine áp/ghi conversion trong backend | Không gán UOM hiện tại cho mọi lịch sử; không tự nhân hệ số hoặc mặc định1. Giữ master revision/basis, mapping/approved conversion proof theo binding M5 |
| Tồn theo kho/as-of | `getTonHienTai(maHang)` chỉ group mã hàng trên toàn header/detail, không tham số/lọc `MaKho`, không ngày as-of. Chỉ tính Nhập/Xuất đã duyệt; dòng `:190` TODO kiểm kê | Chỉ gọi là aggregate nguồn theo logic hiện có, không tồn riêng kho, không điều chỉnh đầy đủ hay lịch sử tồn exact. Không làm stock engine ở receiver |
| Kiểm kê | `:419–448` tạo tất cả hàng đang hoạt động, gắn kho được nhập nhưng số sách là aggregate trên. Không có function đọc/cập nhật thực tế/hoàn tất/điều chỉnh kiểm kê trong 24 declarations/dispatcher | Phân biệt đã có khởi tạo với quy trình đếm hoàn tất. `SL_ThucTe` rỗng phải UNKNOWN, không0; không tự tạo phiếu điều chỉnh |
| Liên kết kế toán | Header có đối tác/kho, master có `MaDoiTuong_KT`; chưa có typed invoice/RQ/project/department/PN refs trong header/detail | Những liên kết này là phần bridge cần làm. Không bóc tự do `GhiChu` thành khóa/provenance; `TK_KeToan` master nhóm không thành policy/bút toán giá trị |
| Phân quyền/cấu hình | `Session.getEffectiveUser()` ghi người thực thi; không có guard PN/role/actor-action theo function. Config mặc định chỉ tạo trong setup; không thấy writer nghiệp vụ đọc để cưỡng chế tồn âm/khóa kỳ/tách người duyệt | Google deployment/access thực chưa đọc/kiểm; không coi effective user là người dùng đã phân quyền hoặc approval kế toán. Core giữ RLS/common approval/period guards độc lập |
| File xuất | `:463–507` đặt tên `.xlsx`, tạo đối tượng Drive/spreadsheet, trả URL; không có luồng xuất MIME XLSX/CSV bytes. Mười cột export bỏ `ID_Dong`, trạng thái, người/thời gian duyệt, phiếu gốc | Không gọi output này là file XLSX hợp lệ hoặc native-key-preserving. Nếu dùng file phải có contract/bundle/raw+manifest đủ identity/history, không dựng ID từ STT |

**Hai chỗ lệch interface giữa desktop và backend, chưa chạy để xác nhận lỗi vận hành:**

1. `ui.html:1023/1049/1101/1132` sử dụng `result.data`; call site `:1036/1071/1120/1149` lại gọi trực tiếp `google.script.run.getPhieuList/getHangHoaList`. Các function trực tiếp `Code.gs:145/:322` trả array; wrapper `{data}` chỉ được dựng ở `doPost`. Tồn desktop còn chờ `tonData.ton` (`:1103`) dù trực tiếp `getTonHienTai` trả number (`Code.gs:192`). PWA sử dụng raw arrays/objects đúng shape này. Không dùng checklist `[x]` trong hướng dẫn để kết luận desktop load đã đạt.
2. `ui.html:1155–1165 saveHangHoa` dựng object chín trường, đặt `MaVach` trước `MaNhom` và thiếu `DVT_QuyDoi`; `Code.gs:112/:117` ghi `Object.values(data)` theo thứ tự object vào sheet mười header (`:19–22`). Vì vậy source có đường ghi lệch vị trí master/UOM/config tồn; receiver phải kiểm nội dung/header/version thay vì mặc định master đã đúng. Chưa có thay đổi sửa ở ứng dụng nguồn trong nhiệm vụ này.

Web tám tab không đồng nghĩa tám luồng hoàn tất: bảng kiểm kê `ui.html:634–645` chưa có loader trong điều hướng `:976–981`; nút lưu cấu hình `:706` chỉ toast, không gọi backend. Mobile `pwa-app.html:242–246` có ba nav Nhập/Xuất/Phiếu; không thấy màn đếm kiểm kê, gọi camera/service worker/offline trong file đã đọc. Tài liệu hướng dẫn có snippet backup tùy chọn nhưng `Code.gs` không có function `backupDaily`; chưa chứng minh trigger hoặc backup chạy. Những hạn chế producer giữ trong backlog đúng nguồn, không trở thành lý do xây lại kho trong core.

## 4. Mapping tái sử dụng vào R_KHO/M5/L11

| Giữ ở phần mềm #10 | Bổ sung đúng phần kế toán hỗ trợ | Điều kiện dùng |
|---|---|---|
| CRUD, nhập/xuất, source approve/reverse, master và phép tính tồn | Reader readonly source-profile pin; M0 raw/artifact/hash/receipt/snapshot + typed header/detail/master projection | Whitelist sheet/field/transport server; khóa instance/ranges, map PN rõ; không `setup`/writer/exportDrive |
| Native `SoPhieu`, `ID_Dong`, trạng thái/audit | Logical identity tách content-version/observation; dedup/replay, full/partial scope, accepted source state/eligibility/impact task | Duplicate/orphan/stale/reappearance/UOM change giữ hold; không fake ngày PN hoặc nguồn gốc |
| Hàng hóa/UOM, số lượng đã nhập ở producer | Mapping vật tư/đối tượng/project/department, source encoding và approved unit proof có phiên bản | Quantity precision unknown và lịch sử UOM chưa có evidence không auto match |
| Phiếu nguồn, không giá trị | Common non-money parent `HD_PHIEU_KHO` + child quantity chung nối M2 invoice PB-line với M5 logical/PB-line; hai native quantities và hai normalized budgets xuyên revision | Dùng đúng binding M5 §3–4, RLS/action/V2 + common receipt/locks/period; không `so_tien_khop_minor`, không BANK budget hoặc proposal mua/331 mới |
| Kiểm kê/tồn | Hiển thị observation nguồn + scope/limitations và file soát | Aggregate/as-of/per-kho/precision chưa đạt phải hiện đúng; không receiver tự tính/tạo điều chỉnh |
| UI kho nguồn | M5 shell xem nhập nguồn/mapping/provenance/soát L11/cấp phát và mở source URL đã cấu hình | Không clone màn CRUD kho, không quyền trực tiếp business schema/bao_mat; không gửi toàn Google response tới cloud |

`kho-source/v1`/`doc_snapshot_v1` trong binding là **contract reader đề nghị**, không endpoint đã có trong `Code.gs`. Có thể tái dùng reader hiện có làm nguồn mô tả field, nhưng source extension/deployment/read API phải có gói riêng được review; nguồn này chưa được sửa. Đích tích hợp theo TL40 giữ Google qua K1/read API; nếu producer nội bộ sau này ghi PostgreSQL chỉ đi qua `giao_tiep`/quyền riêng, không business tables.

Common primitive được tham chiếu từ các binding kỹ thuật trước đây cần rebase theo baseline root cho phép sau khi **M9 đã bị Anh yêu cầu dừng**. Báo cáo này không cho phép chạy lại Claude sửa M9 hoặc sửa loan source để làm nền cho M5; không tự khởi động coding gói mới.

## 5. Bằng chứng còn cần trước nhận M5

1. Xác định bản deploy/source-instance thực và quyền readonly, chưa cần Anh mô tả lại chức năng kho đã có. Đọc có whitelist vào local-only; không gọi setup/write/export để kiểm tra kết nối.
2. Reader DEMO có full/partial/consistent snapshot/profile/known-at và native keys; mapping instance+kho→PN cùng master/UOM history; kiểm raw unchanged/2PN/same key khác instance/replay/duplicate/orphan/date thiếu→M0 giữ chờ.
3. Status revisions và A→B→A stale/reapprove có source evidence; old matched quantities còn held đến đúng action review; không phiếu âm, không tự resurrect/hủy khi mất row partial.
4. Quantity exact hai phía/UOM proof/capacity xuyên version, invoice10↔phiếu8 có chênh2, split/one-many và race/undo dưới common guards; không phát sinh invoice/primary claim/331/BANK khi chỉ link số lượng.
5. Cổng RLS/action/period/file bytes/UI/reopen/restart có ca positive thực trước negative; kiểm source scope không tự biến aggregate thành tồn kho riêng. Quy trình kiểm kê/source gaps và quyền producer cần được xử lý đúng gói chủ nguồn để hoàn tất toàn M5.

Tất cả các mục trên là **NOT_RUN trong lần kiểm tra này**; không cộng số function/chín sheet/hash đúng vào tỷ lệ nghiệm thu runtime. Bổ sung authoritative override cho receiver cũ trong coverage: `R_KHO = EXISTING_SOURCE_CODE_CONFIRMED_STATIC_REUSE_REQUIRED`, trỏ phần mềm #10→M5; giữ `M5 implementation/runtime acceptance pending` và M10 định kỳ riêng.
