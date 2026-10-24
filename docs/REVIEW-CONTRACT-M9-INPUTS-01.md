# Oracle đầu vào độc lập cho M9-01 — corpus DEMO

Ngày lập: 19/10/2026. **Chỉ chuẩn bị input/expected; chưa chạy parser, product, app nguồn, Google Sheets hoặc test.** Không phải code M9 hoặc nghiệm thu. Claude đang sửa CRM nên công việc này không import/chạy/sửa product. Không có dữ liệu thật, credential, tính lãi/FX hoặc quyết định chính sách mới; không xóa file/temp/DB.

**Revision 2 dùng cho handoff:** `var/codex-dieu-phoi/m9-independent-inputs-20261019-v2/`, **19 ca**, 18 file được hash (17 file dữ liệu/expected/mapping và bản review v1 được giữ); manifest là file thứ 19. SHA-256 manifest v2: `80baa534b9c0e7740d7cebad0c896ccc424a14214bfc59bc1f0972d8157288ee`.

Corpus v1 `var/codex-dieu-phoi/m9-independent-inputs-20261019/` được giữ nguyên toàn bộ, manifest vẫn `46e1ef362e918cb29b272b979ab198745ed1dcdb01119f611a21f43d5145d5aa`; không dùng nhãn native-positive/S08 của v1 làm oracle hiện hành. Nội dung review v1 lưu tại `v2/review-v1-preserved.md`. Mỗi file có hash/byte riêng; expected viết độc lập, không lấy output sản phẩm làm đáp án.

## 1. Căn cứ và phạm vi nguồn

- Gói `GIAO-VIEC-BRIDGE-KHOAN-VAY-M9-33.md`, hash `fb8c5f00834520625217f999b2b45a12246fa958787dca4d2261b04bcaa5f946`.
- Root kỹ thuật `D:\Claude\Phan mem theo doi khoan vay`: `Code.gs` hash `98774668ddf909b328e21e399d938d6740f1db4266e1661df78ec87e665b38db`; `apps-script-deploy/Code.js` hash `593d6ba8efce4a301a3f42ad2b2c2936ed90119ccfdc8375e11fd3a85768d8f4`; `apps-script-deploy/Index.html` hash `767f1f17680633564681ba3fdafd1aba4decc7e9406bc696a30dcfab2495e6b7`.
- Schema/profile được pin cho fixture; chưa xác nhận đang deploy trên Google. Cùng `version:6` không chứng minh cùng schema. Full native control `00-native-deploy-full-shape.json` có đủ `version`, `exportedAt`, tám section `longLoans/kheUoc/lichGoc/laiSuat/phatSinh/hopDongMua/vayNH/hanMuc` và sáu key thực của `exportJSON`: **`seqS, seqL, shortLoans, rates, bankCfg, manualRows`**. Counter 1001/2001 là DEMO; bốn section phụ được ghi rỗng **tường minh**, không suy từ key vắng. Các snapshot native khác trong v2 cũng đủ các key này. Không section rỗng nào tạo bank cutoff 25, tỷ giá hoặc policy FX.
- `19-partial-core-sections.json` giữ artifact thiếu sáu key từ v1 để kiểm riêng full-shape so với partial/unsupported. Không được tự default key vắng thành rỗng hoặc coi đủ phạm vi snapshot. Full shape JSON tự nó cũng không chứng minh source nghiệp vụ đã đủ phạm vi, profile đang deploy hoặc snapshot Google thực đã hoàn chỉnh. Artifact được tự dựng theo contract, không là output chạy thật của source; mapping/known-at/expected nằm ngoài raw.
- `09-exact-text-sheet-values.json` là snapshot **raw text của Sheets được tự dựng**, không tuyên bố UI/Apps Script hiện có giữ text exact. `13-export-interest-projection.json` là projection kỹ thuật của công thức/đầu vào nguồn, không giả là native JSON export lãi. `.xls` tự dựng là SpreadsheetML XML và chủ ý thiếu khóa.

## 2. Catalog và expected

| Ca | Phép thử / căn cứ đầu vào | Expected độc lập |
|---|---|---|
| S01 | Một HĐ dài hạn, hai khế ước, hai lịch DRAW có cùng kỳ số | Hai nghĩa vụ phân biệt bằng HĐ/scope/khế ước/kỳ; 12.000.000 và 8.000.000 VND; ban đầu chờ duyệt, không sinh tiền |
| S02 | Nhận lại cùng artifact + mapping | Delta master/nghĩa vụ/phiên bản pháp lý/tiền = 0 |
| S03 | Hai `PhatSinh` cùng id, cùng payload | Một sự kiện nguồn logic, không phân bổ hai lần |
| S04 | Cùng id nhưng gốc khác 1 VND | Xung đột có cả hai raw, không chọn hàng cuối hoặc tự hạch toán |
| S05 | Thêm lịch LOAN 20.000.000 bao phủ hai DRAW 12.000.000 + 8.000.000 | Chờ xác nhận phạm vi, không cộng thành 40.000.000 hoặc nhân lịch LOAN theo khế ước |
| S06 | Mốc lãi 16/01 và 01/04; lần đầu hệ thống nhận 19/10 | Giữ hai mốc; không dùng lãi cuối cho kỳ cũ; không eligible tại cutoff 30/06; chưa có số lãi dự trả expected |
| S07 | Ngắn hạn lưu `soVay=250000000` VND, `soNguyenTe=10000`, `tienTe=USD` | Giữ hai đại lượng/đơn vị riêng; không gắn 10.000 thành VND hoặc chọn policy FX |
| S08 | Tỷ giá nguồn đổi 25.000→26.000, tiền VND nguồn vẫn 250.000.000 | Giữ hai đại lượng có thể độc lập; không tự sửa tiền thành 260.000.000 hoặc kết luận sai chỉ vì tỷ giá đổi. Chỉ kiểm mâu thuẫn khi profile tuyên bố quan hệ và cơ sở tỷ giá đã được chốt; FX posting vẫn cần policy riêng |
| S09 | Sheet text exact `9007199254740993` | Khi có profile text/scale rõ, giữ đúng giá trị; không vòng qua Number; chưa chứng minh source hiện tại có đường này |
| S10 | Payload đã qua Number chỉ còn `9007199254740992`; chuỗi gốc khác được ghi **chỉ trong oracle** | Không thể biết chuỗi gốc từ output; giữ precision chưa chứng minh, chỉ kết luận mất khi có bằng chứng độc lập. Không phục hồi chữ số bằng Decimal hoặc cho oracle gốc lọt vào đường nhận như bằng chứng nguồn |
| S11 | SpreadsheetML `.xls` mất `maKheUoc` lịch gốc và `id` phát sinh | Báo mất định danh; không đoán khế ước/id từ ngày, số tiền hoặc thứ tự; không promote canonical lịch/sự kiện |
| S12 | `LC đã mở`, chưa có ngày nhận nợ/giải ngân | Không sinh giải ngân/tiền/phí/ký quỹ từ trạng thái hoặc số LC; mẫu nghiệp vụ vẫn chờ |
| S13 | Projection exportLai dùng dư nợ hiện tại 48.000.000 và lãi cuối 7% cho kỳ 02 | Không làm oracle lãi lịch sử/lãi kế toán; `expected_accounting_accrual=NULL`; cần căn cứ/bảng đã duyệt |
| S14 | JSON version 6 nhưng lịch gốc root không có `maKheUoc`, nhận dưới profile deploy | Không tự nhận vì số version trùng; báo profile/schema không hỗ trợ, không chọn khế ước gần nhất |
| S15 | Hai instance/pháp nhân, mã vay/khế ước/số HĐ trùng | Hai namespace riêng, không fuzzy merge hoặc link chéo pháp nhân |
| S16 | Cùng mã khế ước bị gắn hai HĐ cha, mốc lãi chỉ có mã khế ước | Chờ xung đột khóa; không gán rate theo thứ tự dòng |
| S17 | Liên kết với BANK M1 đã có `DEMO-REF-01` / 12.850.000 | Khi mẫu DEMO/đủ quyền được khai báo: 12.000.000 gốc + 800.000 lãi + 50.000 phí; trước/sau nhận nguồn đều không thêm BANK hoặc bút toán 112 |
| S18 | Coverage phần còn lại | Bảo lãnh chi tiết/loại đầu tư/hồ sơ/policy vốn hóa/FX/actual-rate/lãi dự trả chưa đủ; **toàn M9 chưa hoàn thành** |
| S19 | Chỉ tám section nghiệp vụ, thiếu sáu key native, nhận dưới full-native profile | Partial hoặc unsupported; không tự bổ sung section rỗng, promote snapshot đầy đủ hay retire dữ liệu cũ |

Trạng thái trong `expected-cases.json` là nhãn ý nghĩa của oracle, không chứng minh enum/service tương ứng đã có. Runner sau này phải đối chiếu mã trạng thái thực và hiệu lực hành động; không chỉ tìm chuỗi thông báo để tính đạt. Các số gốc/lãi/phí S17 là mẫu **kỹ thuật DEMO đã khai báo**, không được dùng làm chính sách tính lãi hoặc FX thật.

## 3. Hợp đồng handoff và interface còn thiếu

`expected-cases.json` liệt kê ID ca, file raw, thao tác và expected có kiểu JSON. `mapping-demo.json` chứa namespace, hai mapping công ty/dự án/ngân hàng DEMO, `known_at_server`, cutoff và profile/hash. Runner cần ghi hash input, phiên bản adapter/profile, delta số bản ghi, giá trị typed thực, lỗi/quyền/approval và chứng từ/link/lô trước–sau. Không import product trong bước chuẩn bị này.

Khi M9 tới lượt: dùng typed K2/quyền/link/K5 đã review từ CRM; cần xác định API nhận snapshot, lưu raw/hash/provenance, duyệt master/lịch, nối M1 và export file soát thực. Chưa có những interface đó trong corpus nên chưa có executable runner gọi sản phẩm, kết quả pass/fail hoặc bằng chứng PG/UI. Expected không phụ thuộc cách đặt tên hàm chưa tồn tại.

Phải bổ sung về sau: nhận lỗi/partial snapshot/retry/đổi schema/quyền Google readonly thực; precision contract theo field và nguồn chứng minh gốc; ngân hàng/lịch/cutoff đã duyệt; các ca transaction/concurrency/kỳ khóa/phụ lục lịch đã khớp và GUI; template LC/ký quỹ/phí/bảo lãnh; kiểm kê aggregate đầu tư tài chính và hồ sơ thực có. Giữ các gap này trong toàn M9/L7/L8/L12, không thay đích bằng bridge vay hoặc quay sang CSV thủ công.

Không có policy thì expected là giữ chờ/NULL và có căn cứ thiếu, không tự tính lãi, tỷ lệ vốn hóa hoặc FX để tạo đáp án xanh. Corpus phải qua review và chạy độc lập khi Claude bàn giao M9; giữ mọi file/bằng chứng, không cleanup. Nếu dùng Python, đặt guard `PYTHONUSERBASE` riêng, `CODEX_NO_DELETE_FILES=1` và `PYTHONDONTWRITEBYTECODE=1` trước khởi động.

