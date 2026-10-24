# Danh mục tái sử dụng phần mềm — kiểm tra source/interface ngày 18/10/2026

**Chỉ đạo M9 mới nhất 19/10/2026:** Anh đã cấp `D:\Claude\Phan mem theo doi khoan vay\Code final` và giới hạn **chỉ xác định cách lấy dữ liệu; theo dõi khoản vay đã ở ứng dụng nguồn, không sửa hoặc xây lại**. Root đã đọc report `TAI-SU-DUNG-NGUON-VAY-CODE-FINAL-33.md` SHA15197208…e089 và kiểm lại hai source hashes trước/sau (backend2c29a5a6…ba89; UI0108bada…1a9e). Đường ưu tiên từ code hiện có là **cặp JSON + Excel cùng phiên/mốc/phạm vi**: JSON giữ native keys/dữ liệu gốc, Excel dùng engine nguồn xuất kết quả dư nợ/đã trả/lãi/kỳ tới. Sheets raw riêng không đủ các output tính sẵn. RPC gắn UI/auth và load/login có side effects; chưa gọi thử hoặc kết nối Google. Source mới khác profile cũ, không tự resume repair M9/core hoặc sửa app nguồn. Các ghi “chờ Anh cấp code” dưới đây là lịch sử đã được thay bằng nguồn này; việc lấy dữ liệu thật/ingest vẫn chưa thực hiện.


**Đối chiếu19/10/2026:** Anh xác nhận phần mềm #10 quản lý kho là nguồn R_KHO→M5, khác module M10 định kỳ. Root đã đọc đủ `TAI-SU-DUNG-PHAN-MEM-KHO-10.md` SHA92dfe449…621c4: Code.gs796dòng/24hàm,9sheet definitions, web/mobile/API/CRUD/duyệt/đảo đã có, sourcehash62f46583…873e2c khớp bindingM5 hiện hành.8technical hashes trước/sau giữ nguyên. Dùng lại producer; bổ sung reader/profile/snapshot/mapping/provenance và liên kết số lượng. Các gap status/nativeID/precision-UOM/perKho/kiểm kê/export/desktop transport/mastercolumn là static chưa runtime; không sửa app nguồn, đọc workbook/secrets hoặc truyền originalsource tới Claude. M9 vẫn DỪNG theo Anh.

**Kết luận:** đã có đủ thành phần nguồn để tránh xây lại bộ tải hóa đơn, backup Base, bóc tách hợp đồng, theo dõi vay, kho số lượng, tính phí nước thải và lõi nhắc việc. Phần cần làm trong phần mềm kế toán chủ yếu là **adapter có phiên bản, mapping mã/pháp nhân, provenance, liên kết và duyệt chung**. Local Mask có lõi thay thế/kiểm tra/mapping mã hóa để dùng lại, nhưng chưa phải cổng tự động bảo đảm bảy nhóm thông tin theo hợp đồng kế toán.

Đây là kiểm tra tĩnh tài liệu kỹ thuật và định nghĩa source/API/export. Không chạy ứng dụng, test, import module ứng dụng hoặc kết nối mạng; không đọc dữ liệu thật, `.env`, credentials, cấu hình chứa bí mật, spreadsheet đang dùng hoặc thư mục đầu vào/đầu ra. **Có code không đồng nghĩa đã kiểm chứng triển khai hoặc chất lượng trên nguồn thật.** Tài liệu chỉ ghi path kỹ thuật, tên trường, interface và trạng thái; không chép payload nguồn. Review xây dựng do luồng kiểm tra riêng phụ trách.

## 1. Phân loại kết quả

| Nguồn | Đã xác minh từ source | Phương thức tái sử dụng ưu tiên | Trạng thái còn thiếu |
|---|---|---|---|
| Trích tham số hợp đồng | Reader Word, cấu trúc Điều/Khoản, định vị, kiểm trích dẫn, xuất JSON/XLSX và giao diện tác vụ | Đọc kết quả JSON vào hợp đồng/phiên bản/tham số chờ duyệt; tái dùng bộ đọc và kiểm trích dẫn | Mapping loại hợp đồng/lịch thu và cổng AI theo chính sách kế toán |
| Tải hóa đơn | Node/Playwright tải theo kỳ, ghi XML/PDF/bảng kê, tiến trình SSE | Giữ nguyên ứng dụng; K1 đọc thư mục kết quả | Manifest phiên tải và kiểm luồng DEMO; không xây lại đăng nhập cổng thuế |
| Backup Base | JSON request đầy đủ, file đính kèm/manifest, index Excel, retry/phân trang | K1 đã có parser khớp format JSON này | Kiểm mapping form, số tiền/tiền tệ và lỗi thiếu field; không xây lại backup |
| Theo dõi khoản vay | Apps Script có dữ liệu dài hạn, khế ước, lịch gốc/lãi suất, phát sinh; ngắn hạn/LC/hạn mức; export phía giao diện | Đọc các sheet cần thiết qua API chỉ đọc hoặc export có whitelist | Hai bộ source đang khác phiên bản; cần khóa contract adapter theo phiên bản được dùng |
| Kho | Có code CRUD/duyệt/đảo phiếu, tồn số lượng, kiểm kê, PWA/API và export | Đọc header/detail phiếu đã duyệt hoặc các sheet số lượng | Kiểm triển khai; mapping liên kết hóa đơn/dự án/bộ phận; export chưa được chứng minh là file XLSX thực |
| Phí xử lý nước thải | Jobs/chống trùng, master, tính và tạo thông báo, SELLING1/2; nhận OCR cục bộ | Giữ pipeline tính phí; bridge dữ liệu/lô đã soát sang M3 | Mapping chứng từ nguồn, trạng thái duyệt, mã/pháp nhân/kỳ; thông số template xuất còn cảnh báo production |
| Local Mask | Thư viện suggest/replace/verify, rule schema, vault mã hóa, FastAPI có phiên/CSRF/revision | Adapter gọi lõi cục bộ; giữ giao diện Mask riêng khi cần người rà | Bổ sung lớp chính sách tài chính bảy nhóm, chuyển token và khôi phục có kiểm tra; chưa kích hoạt cloud |
| Trợ lý | Telegram transport, webhook xử lý trả lời, task/message binding, dedup, reminder, logbook | Tái dùng máy trạng thái/nhắc việc; thay transport Zalo, nối việc K5 | Không có bằng chứng Zalo transport đã tồn tại; AI hiện gọi trực tiếp cần đi qua cổng chung |

## 2. Hợp đồng — không xây lại công cụ trích xuất

**Root kỹ thuật:** `D:\Claude\Local AI\hop_dong`.

- `doc_reader.py:292` có `read_contract(path)`; `:179` đọc DOCX; bộ đọc giữ số Điều/Khoản và phát hiện cấu trúc cần người kiểm. `cau_truc_hop_dong.py:62` có `build_structure(info)`, `:126` định vị theo tham số, `:165` xuất cấu trúc/phiếu kiểm.
- `trich_xuat_v3.py:460` có `process(path, params, dung_ai)`; `:255` kiểm giá trị/trích dẫn trong văn bản nguồn. `:623–638` xuất `<tên>_KET_QUA.json` dành cho máy khác đọc tiếp.
- JSON ngoài có `hop_dong`, `che_do`, `model`, `tao_luc`, `tham_so[]`, `phieu_kiem_tra`, số đo lượt chạy. Mỗi tham số dùng các khóa `ma`, `nhom`, `tham_so`, `gia_tri`, `don_vi`, `dieu_khoan`, `trich_dan`, `ghi_chu`, `kiem_tra`, `vi_tri_do_duoc`; trường chấm đáp án không dùng làm nhãn huấn luyện tự động. Khi chưa chạy AI có thêm đoạn liên quan.
- `giao_dien.py:131` bắt đầu tác vụ, `:144` đọc trạng thái, `:214/:241` là GET/POST handler. Không cần dựng lại giao diện upload/chạy/xuất của dự án này trong kế toán.

**Bridge cần làm:** JSON kết quả + hash file nguồn → hợp đồng/phiên bản/tham số có provenance → việc V3/V4; giữ kết quả chờ CFO duyệt. Trạng thái kiểm tra tự động của nguồn không thay approval. Nguồn có đầu ra tham số, **chưa chứng minh đã có CRM lịch thu theo các loại doanh thu của kế toán**; phần bổ sung là mapping và cấu hình lịch, không làm lại reader/locate/check.

Pipeline AI hiện tại dùng giao thức Ollama theo tài liệu nguồn; không coi việc đã có pipeline đó là đã đáp ứng cổng cloud/Mask của hệ thống kế toán. Có thể dùng ngay đầu ra hiện có và các hàm thuần đọc/kiểm; thay đường gọi AI qua adapter theo chính sách chung khi tích hợp.

## 3. Hóa đơn và Base — có thể giữ đường file hiện có

**Hóa đơn:** root `D:\Claude\Phan mem download hoa don`.

- `src/job.js:125–158` chia kỳ, chiều mua/bán và ghi kết quả theo thư mục kỳ/chiều; `:226–227` xuất bảng kê. `src/build.js:18` có `buildExcel`, `:113` có parser XML phục vụ kết quả nguồn.
- `src/server.js:41` nhận `/api/start`, `:64` phát `/api/events`. Đây là interface vận hành của ứng dụng nguồn, không cần đưa tài khoản cổng thuế vào hệ thống kế toán để tải lại cùng nghiệp vụ.
- Trong repo kế toán, `src/kho_tri_thuc/nguon/that.py:459` đã có `_xml_rows`, `:478` có `_invoice_table_rows`. **Đường tích hợp ưu tiên: file XML/bảng kê → K1 hiện có**; PDF chỉ làm tài liệu xem.
- Adapter bổ sung chỉ cần manifest theo lần tải: pháp nhân, kỳ/chiều, thời điểm lấy, file/hash, trạng thái thành công/thiếu/lỗi; không coi kỳ thư mục là bằng chứng thời điểm biết. Runtime/chất lượng tải trên máy chưa kiểm chứng trong nhiệm vụ này.

**Base:** root `D:\Claude\Base back up module`.

- `backup_requests.py:649–736` tạo bundle có `id`, `fetched_at`, `get`, `custom_table`, `posts`, `_attachment_results`; xuất `requests/request_<id>/request_<id>.json`, `attachments_manifest.json` và các file đính kèm. `:853` ghi index Excel. Không cần xây lại gọi API, phân trang, retry và tải đính kèm.
- Parser kế toán `nguon/that.py:502–549` **đã nhận đúng nhánh** `get.request`, form, `custom_table` và `_attachment_results`. Nó đang đọc các field form kỹ thuật như `tong_thanh_tien`, `du_an`, `chi_phi`; giữ `fetched_at` và metadata file đính kèm.
- Không dùng cột tiền trong index Excel làm nguồn tiền duy nhất: `README.md:123–124` xác định cột này là best-effort và chưa rõ đơn vị. Bridge phải kiểm field/currency, báo thiếu thay vì dựng số; không yêu cầu Anh mô tả lại toàn bộ Base. Tích hợp Request thay thế dùng cùng canonical RQ rồi thêm adapter nguồn mới khi nguồn đó sẵn sàng.

## 4. Khoản vay — tái dùng toàn bộ mô hình đang có, khóa đúng phiên bản

**Root kỹ thuật:** `D:\Claude\Phan mem theo doi khoan vay`.

- `KHOA-CAU-TRUC-VAY-DAI-HAN.md:13–29` khóa năm sheet: `DaiHan`, `KheUoc`, `LichTraGoc`, `LichLaiSuat`, `PhatSinh`. Khóa nối là `maKV` và `maKheUoc`; phát sinh có `id`, ngày, trả gốc/lãi/phí, tham chiếu chứng từ. Không tạo lại danh mục/lịch vay riêng cạnh nguồn này.
- Source `apps-script-deploy/Code.js:37–60` có các bộ cột dài hạn và ngắn hạn/LC/hợp đồng mua/hạn mức; `:110` có route `load/loadMaster` và các action nghiệp vụ; `:233–282` trả `longLoans`, `kheUoc`, `lichGoc`, `laiSuat`, `phatSinh`, `hopDongMua`, `vayNganHan`, `hanMuc` sau lọc phạm vi công ty.
- `apps-script-deploy/Index.html:1719/:1760/:1807` có `exportExcel`, `exportLai`, `exportJSON`. Vì vậy không phải chỉ có đặc tả sheet; đã có code nhận/xử lý/xuất cần được giữ.
- **Khác phiên bản cần chú ý:** `Code.gs` ở root có 920 dòng, bộ deploy `Code.js` có 1.203 dòng và khác nội dung; lịch gốc trong bộ deploy bổ sung `maKheUoc`, các bảng ngắn hạn có trường bổ sung. Không gán một schema cũ cho cả hai hoặc suy rằng bộ deploy đã được triển khai chỉ từ tên thư mục.

**Bridge cần làm:** nguồn Sheets/API chỉ đọc hoặc export có whitelist → contract có phiên bản → `maKV/maKheUoc` ↔ hợp đồng nội bộ, công ty ↔ pháp nhân, dự án/mã Junsky, lịch và phát sinh → M9/M1/M4. Chụp thời điểm và hash nguồn; giữ lịch/lãi suất theo thời gian. `load` hiện trả cả dữ liệu phụ nên không dùng nguyên toàn bộ response làm payload kế toán hoặc cloud. Thiếu phép đọc nguồn là thiếu kết nối vận hành, không phải lý do xây lại phần mềm vay.

## 5. Kho — đã có code vận hành phiếu, không chỉ thiết kế chín sheet

**Root kỹ thuật:** `D:\Claude\Phan mem quan ly kho`.

- `9_SHEET_STRUCTURE.md` và `Thiet-ke-du-lieu-va-man-hinh.md:20–29` định nghĩa `DM_HangHoa`, `DM_Kho`, `DM_DoiTac`, `DM_Nhom`, `GD_Phieu`, `GD_Dong`, `GD_KiemKe`, `HT_CauHinh`, `HT_NhatKy`; phạm vi chỉ số lượng.
- Header phiếu: `SoPhieu`, `LoaiPhieu`, `NgayChungTu`, `MaKho`, `MaDoiTac`, `TrangThai`, người/thời điểm duyệt, `SoPhieu_Goc`. Detail: `ID_Dong`, `SoPhieu`, `MaHang`, `SoLuong`, `GhiChu`. Đối tác đã có field `MaDoiTuong_KT` để map sang mã kế toán.
- `Code.gs:202/:246/:275` có tạo/duyệt/đảo phiếu; `:328–360` trả `{phieu, lines}`; `:419` có kiểm kê; `:688` có POST action/data cho các thao tác và truy vấn; `:537` trở đi có API hỗ trợ PWA.
- `Code.gs:459–507` có hàm `exportToExcel` nhưng interface hiện trả `{fileName,url}` sau tạo spreadsheet; **chưa kiểm chứng tạo được bytes XLSX/CSV**. Không đặt phụ thuộc vào tên hàm này: adapter có thể đọc sheet hoặc `{phieu,lines}` đã tồn tại.

**Bridge cần làm:** phiếu đã duyệt/phiếu đảo → chứng từ chuẩn + dòng số lượng → nối hóa đơn, yêu cầu cấp phát, dự án/bộ phận; bảo toàn khóa phiếu và dòng. Đọc qua API Sheets/file theo kiến trúc đã chốt, không nối Google Apps Script trực tiếp vào bảng nghiệp vụ PostgreSQL. Không xây lại tồn kho số lượng, không thêm tính giá vốn trong kế toán hỗ trợ.

## 6. Nước thải — tái dùng pipeline tính phí và tạo chứng từ bán

**Root kỹ thuật:** `D:\Claude\Phan mem phi xu ly nuoc thai`.

- `AppsScript/Code.gs` và `apps-script-deploy/Code.js` **khớp nguyên bytes**, cùng 1.947 dòng tại lần kiểm tra.
- `Code.gs:429` có Jobs với `batch_id`, `company_id`, `period`, `status`, `source_fingerprint`, thời điểm, tên sheet tính/SELLING/thông báo, warnings/error. `:453–479` có fingerprint và phát hiện lô đã tồn tại. `:710` có MASTER_COLUMNS gồm ObjectID, thông tin hợp đồng, đơn giá và mã khách nguồn.
- `:587` định nghĩa `OCR_SCHEMA`; `:1691` kiểm trường bắt buộc; `:1719` có `apiIngestOcrBatchFromClient_`. `doPost` tại `:1526` nhận action `ingest_ocr_batch`; body có pháp nhân nguồn, kỳ, người vận hành, `files[]` gồm tên/MIME/base64 và object `ocr`. Có thể giữ nhánh OCR cục bộ đã có contract; không bắt gửi lại file cho cloud để nhận cùng dữ liệu.
- `:968` dựng bảng tính/thông báo; `:1266–1344` sinh `SELLING1/SELLING2` bằng template `SM_tmpSelling1/SM_tmpSelling2`. Đây **không phải** format ngân hàng `CB_tmpEntry1/2`.
- Source `:1336–1339` tự cảnh báo `EntryID/EntryDate/InvDate/InvSeri` còn theo template thử nghiệm, cần xác nhận trước import production. Không chuyển cảnh báo này thành trạng thái đã nghiệm thu.

**Bridge cần làm:** đọc lô/bảng tính đã soát hoặc export SELLING qua K1; map pháp nhân, ObjectID, kỳ, hợp đồng và trạng thái duyệt; giữ fingerprint chống trùng. Phân biệt bản tính phí/chứng từ bán đề xuất với XML hóa đơn chính thức đến sau; nối hai nguồn để không ghi nhận hai lần. Giữ phép tính, master/tariff, thông báo và pipeline OCR ở ứng dụng nguồn; bổ sung liên kết và duyệt chung ở kế toán.

## 7. Local Mask — tái dùng lõi, bổ sung adapter chính sách tài chính

**Root kỹ thuật:** `D:\GPT\Phan mem Mask file\Mask file v2`.

- `privacy/core.py:46` nhận rule `{source,token,category,enabled,canonical?}`; `:77` suggest; `:306` replace trả `(text,count)`; `:315` verify kiểm không còn cụm đã chọn; `:391/:400` mã hóa/giải mã mapping bằng AES-GCM/Scrypt. Các component này có thể dùng lại qua adapter, không viết một bộ thay tên mới.
- `privacy/server.py` có `/healthz`, upload/state/rules, review từng tài liệu, export và vault. Request có phiên, CSRF và revision; đây là API của workflow duyệt tài liệu, **không có bằng chứng API headless `mask → cloud → restore` hoàn chỉnh**.
- `privacy/core.py:25–31` có các nhóm doanh nghiệp/cá nhân/MST/tài khoản/giấy tờ/hợp đồng/địa chỉ/dự án… và token dạng `[A-Z…]` trong ngoặc vuông; `:322` kiểm việc thay đổi số. `privacy/detectors.py:151/:165` chủ động tránh coi số tiền là tài khoản. Vì vậy không được suy rằng detector này đã tự mask số tiền theo yêu cầu kế toán.
- `docs/ARCHITECTURE.md:47–57` xác định runtime cục bộ, phiên trong RAM, duyệt và kiểm lại file; `README.md:138–143` nêu còn khả năng bỏ sót. `verify` chỉ kiểm rules đã biết, không chứng minh không còn mọi dữ liệu nhạy cảm.

**Bridge cần làm:** áp danh sách bảy nhóm và bí danh đã chốt cho kế toán, bao gồm số tiền; map token nội bộ của Mask với mã Junsky/bí danh của kế toán mà vẫn khôi phục được; giữ mapping ở máy, không gửi cloud. Bổ sung bộ kiểm token/trích dẫn sau khôi phục, context pháp nhân đã duyệt, logging và công tắc tắt. Dùng lại core/detector/vault, không tự sửa mục tiêu của ứng dụng Mask hoặc coi cổng kế toán đã sẵn sàng chỉ vì Mask có web API. Chỉ thử runtime bằng DEMO trong bước triển khai được giao tiếp theo.

## 8. Trợ lý — tái dùng máy công việc, thay kênh giao tiếp

**Root kỹ thuật:** `D:\Claude\Virtual secrectary\troly`.

- `tg.py:19/:32/:37/:42` có send/callback/can-send/webhook cho **Telegram**.
- `app.py:30` nhận webhook; `:66` xử lý trả lời theo task; `:504` nối message với task; `:616` xử lý callback. `store.py:51` dedup update; `:119` lưu task; `:156–166` nối `(chat_id,message_id)` với `task_id`; `:170` có pending confirmation.
- `reminders.py:58` lập lịch công việc; `:82` gửi nhắc; `:193–211` có tick/loop. `store.py` có bảng tasks/logbook/seen/pending/task_msgs và API đọc logbook. Giữ cơ chế deadline, quá hạn, pending, dedup và liên kết trả lời, không lập trình lại bot từ đầu.
- `brain.py:70/:105` hiện gọi `_client.messages.create` trực tiếp. Khi dùng vào kế toán, không giữ đường gọi này ngoài cổng AI/Mask chung.

**Bridge cần làm:** transport Zalo thay Telegram; map người/pháp nhân/vai trò sang danh bạ nội bộ, `task_id` ↔ việc K5/câu hỏi, callback 1/2/3 ↔ phương án; bổ sung giới hạn nội dung và audit kế toán. Phản hồi phòng ban đưa việc về chờ duyệt, không tự hạch toán. Lõi hiện có chưa chứng minh Zalo đã được tích hợp hoặc đã đáp ứng phân quyền pháp nhân; vẫn tái sử dụng được scheduler/dedup/task-message binding dưới adapter.

## 9. Phần còn thiếu và thứ tự làm bridge

1. **Dùng ngay interface file đang khớp:** giữ #7 và #8; chỉ bổ sung manifest/provenance, mapping và ca DEMO ở K1. Không đợi xây xong mọi schema mới bắt đầu luồng chứng từ.
2. **Bổ sung adapter JSON có sẵn:** kết quả hợp đồng → tham số chờ duyệt; nước thải → lô/bảng tính có liên kết và trạng thái. Không tái tạo phép bóc tách hoặc tính phí ở kế toán.
3. **Đọc các nguồn Sheets theo contract:** khóa phiên bản code khoản vay; map các sheet và phiếu kho đã duyệt. Bộ adapter ghi version/schema, hash/cursor và cảnh báo field chưa hỗ trợ; không sửa source cũ hoặc dữ liệu nguồn trong nhiệm vụ này.
4. **Dùng thư viện, thay đường biên:** Local Mask → adapter tài chính/cổng AI; trợ lý → transport Zalo/việc K5. Không gọi ứng dụng nguồn hoặc cloud trong kiểm kê này.
5. **Chưa kiểm chứng:** phiên bản đang deploy, quyền kết nối thực, lịch tự động, khả năng export chạy được và đúng số liệu, đồng bộ hai lần không trùng, nguồn thay đổi schema, hết phiên/token, phân quyền thật và hiệu năng. Các bước này cần chạy DEMO/integration test sau khi bridge cụ thể có thể review; không yêu cầu Anh kể lại thiết kế đã có.

Theo TL40: phần mềm trong nhà khi cần ghi qua PostgreSQL chỉ dùng vai trò riêng và hàm/view `giao_tiep`; Google Sheets/Base/Junsky đi qua K1/API nguồn; dịch vụ Mask/OCR là HTTP cục bộ. Không phần tích hợp nào được cấp quyền trực tiếp bảng nghiệp vụ hoặc `bao_mat` cho thuận tiện.
