# Giao Claude M4-01B — Sửa cửa tiếp nhận, replay và ranh giới tái sử dụng

**20/10/2026 · CODE_ONLY · READY_FOR_SEQUENTIAL_HANDOFF, chưa dispatch.** Tiếp tục cùng session. Anh đã giao triển khai dần cả M4 và CRM. Đây là sửa và tiếp tục gói M4-01 đã chốt, không thu hẹp mục tiêu thành một parser hoặc schema. Gói kế tiếp M4-01C phải khép giao diện Cổng hồ sơ, demo và kiểm xuyên luồng intake; sau đó vẫn còn full Review/PDF, NT–công nợ và Request theo [kế hoạch M4](M4-KE-HOACH-DA-CHOT-20261020.md).

## 1. Bối cảnh và bằng chứng

Lượt M4 trước đã hết giới hạn 1.800 giây, chưa có result báo xong. Root xác nhận terminal và không còn process cùng session. Bản partial có 285 file; ba file nền đổi, tám file mới, không thiếu file hoặc sửa ngoài phạm vi. Manifest SHA256 `76580a1f6c652a6ee1583000fac34fac17d57d084685085bb0d1695eae19bf46`. Đọc code hiện hành đã được Root đối chiếu snapshot, không tìm đọc var/ hoặc nguồn ứng dụng gốc.

Code partial đã có M17, adapter dùng lại, service/HTTP, fixtures/seed và CSS. Chưa có `m4.js`, tests, báo cáo, package nguồn đã nạp hoặc GUI đủ luồng. Không có kiểm runtime; các phát hiện dưới đây là review tĩnh có call path, không phải báo test thất bại. Root chưa chạy SQL, sản phẩm, AI/OCR hoặc tool nạp nguồn.

Giữ nguyên prefix migrations 1–16: 715.854 bytes trước phần mới đã khớp bản trước. M17 chưa được Root triển khai lên DEMO, nên sửa chính M17 trong gói này; không dùng lại full migration M9 cũ. Không sửa quyền CRM/CFO để giải quyết quyền M4.

## 2. Các sửa bắt buộc, có kết quả hữu hạn

### B1 — Tên tệp và cửa ghi nguồn thật

- M17 `m4.tep` có CHECK gọi `chr(0)` tại `pg_migrations.py:8849–8850`. Sửa để tệp hợp lệ ghi được; chuỗi NUL/path traversal/tên sai bị từ chối trước ghi file, không đánh đồng mọi tên tệp hợp lệ với lỗi.
- Các hàm `m4.ghi_tep`, `m4.ghi_trich_xuat`, `m4.ghi_boq` cùng grants cuối M17 hiện cho ordinary `app_web` khai metadata/hash, kết quả trích XONG và BOQ DA_MAP. Không được lấy metadata/status do caller khai làm chứng cứ đã có bytes, đã trích hoặc đã parse.
- Tạo ranh giới ghi nguồn tin cậy hẹp, tận dụng capture/storage và kết nối ghi nguồn đã có nếu phù hợp. Ordinary user commands và đường worker/capture tin cậy phải tách quyền. Không cấp role worker cho app_web để app tự SET ROLE vượt gate; không cho body browser chứa actor, cờ trusted hoặc kết quả parse làm authority.
- Worker phía máy chủ phải kiểm bytes/hash, nguồn–HĐ–revision/catalog và kết quả xử lý thật trước khi xác nhận fact; CSDL ràng buộc lineage của fact với nguồn đã nhận. Session và quyền hiện tại của nhân viên vẫn kiểm ở lệnh sử dụng/confirm/submit. Trusted worker không được tự duyệt thay phòng dự án hoặc CFO.
- Giữ quyền phòng dự án nhập/sửa thủ công đúng phạm vi, nhưng ordinary caller không tự xác nhận kết quả machine verification/provenance qua `p_kiem_tra` hoặc metadata; kết quả kiểm phải do đường kiểm tin cậy sinh từ nguồn và giá trị thực.
- Service/factory hiện chỉ truyền `crm.conn` vào XayDungK2. Nếu thêm dependency kết nối tin cậy, inject qua cấu hình/factory server được bảo vệ, không nhận DSN/path/key từ request và không đọc .env/var trong lượt Claude. Thiếu đường ghi tin cậy phải trạng thái chưa sẵn sàng, không fallback cho ordinary login tự khai XONG.
- Không dựng lại storage, master, auth hoặc một framework intake tổng quát. Không fake scope MaKho/SoPhieu. M4 dùng chung contract identity và typed extension; giải thích rõ seam phiên bản/tham số và consumer, không tạo master HĐ song song.

### B2 — Retry nguyên request phải nhận đúng kết quả cũ

- Các đường TRICH, SUA_THAM_SO, KHAI_PHU_LUC, THEM_PHU_LUC, HUY_PHU_LUC và NHAP_BOQ hiện kiểm `_kiem_rev` trước `_lenh`, trong khi SQL của chính lệnh tăng revision. Retry nguyên key/body sau thành công vì thế bị M4_REVISION_CU thay vì receipt. XAC_NHAN và các lệnh khác cũng phải giữ replay đúng khi có thay đổi hợp lệ về sau.
- Kiểm danh tính/quyền hiện tại trước lookup; tính digest từ request gốc bất biến, không từ pointer nguồn hiện tại đã đổi; tra receipt trước validation revision mới và trước parse/AI/tạo working artifact. Chỉ lệnh mới mới chạy xử lý và chốt revision cùng snapshot có khóa nhất quán.
- Cùng key/body trả lại cùng IDs/kết quả; cùng key/body khác bị từ chối; revoke rồi replay bị chặn. Không rerun AI hoặc tạo thêm kết quả chỉ để biết request đã chạy. Không đổi key tự động khi chưa rõ kết quả.
- `m4.ket_thuc(text,jsonb)` hiện nhận JSON tùy ý và ordinary app có EXECUTE: có thể tạo receipt rồi giả FINAL success khi command chưa chạy. Đóng cửa này: FINAL/result phải do command hợp lệ hoặc consumer tin cậy hẹp sinh trong cùng transaction, không cho ordinary caller tự chốt JSON. Không thêm quyền rộng hoặc framework mới.
- Raw capture được admit hợp lệ có thể giữ artifact append-only theo contract đã nêu. Không xóa blob để làm test xanh, không bắt mọi file phải bất biến ở sai lớp; phân biệt raw capture với business submission/approval/AP/Request. Tuy vậy lookup key phải ngăn fresh expensive work vô ích và không sinh business duplicate.

### B3 — Đọc tài liệu phải giữ nguyên mọi file, mọi entrypoint

- Có call path thật: `POST /api/m4/tham-so/sua` → service `sua_tham_so` → `NR.van_ban_hop_dong` → legacy `read_contract`. Helper này chưa chặn DOCX Track Changes, trong khi legacy có thể gọi Word/LibreOffice rồi rmtree temp. Guard SQL chạy sau không ngăn side effect trước đó.
- Đóng đường này ở mọi entrypoint. Có thể báo rõ bản DOCX chưa chốt thay đổi/chưa hỗ trợ an toàn ở gói này; không lén mở Office hoặc cleanup. Không đánh dấu đã đọc/trích xong khi chưa xử lý được. Các định dạng/chức năng đầy đủ vẫn nằm trong roadmap M4, không xóa khỏi scope.
- Chỉ dùng path trong DataRoot riêng, giữ bản nguồn, artifact và lịch sử. Không unlink/rmtree/rename/replace/cleanup file, kể cả khi lỗi hoặc retry. Không đọc cấu hình/keys/DB của app nguồn.

### B4 — Origin đúng trước khi import và kết quả tool nạp nguồn trung thực

- `NR.nap` hiện append sys.path rồi import trước khi kiểm __file__. Module/cache/dependency sai nguồn có thể chạy trước khi bị từ chối. Xác minh origin/namespace và cache trước bất kỳ exec module nào, gồm các dependency cấu hình/AI/OCR/SQLite. Không dùng global module của app nguồn hoặc package trùng tên.
- Không tự gọi mo_csdl/_cs/_csdl hay tạo SQLite master trên đĩa. Projection vẫn chỉ :memory:, inject snapshot K2 rồi read-only.
- Giữ reference byte-for-byte và hash; không sửa file vendor để che lỗi. Tool `nap_nguon_review_m4.py --kiem` phải nonzero nếu thiếu bất kỳ file bắt buộc, không chỉ in “Chưa nạp” rồi exit0. Mode nạp chỉ CreateNew/cùng bytes bỏ qua, khác bytes dừng, không overwrite/delete.

### B5 — BOQ đủ căn cứ khác BOQ không có finding

- Reference parser gom cả lỗi map/đọc với finding số học vào `loi`; adapter/service/SQL đang biến mọi `loi` thành CO_LOI và chặn Nộp. Fixture BOQ_LOI_SO_HOC có dòng đọc/map đầy đủ nhưng KL×ĐG khác thành tiền phải đi vào review có finding, không tự thành thiếu căn cứ (kế hoạch M4 §2/A5).
- Tách lỗi đọc/map/evidence blocking khỏi finding nghiệp vụ; giữ finding, locator và dữ liệu gốc cho review, không làm mất hoặc chuyển thành OK giả. Không sửa tính toán legacy để khớp đầu ra mong muốn.
- Reference có nhánh đổi blank KL/ĐG thành 0. Wrapper/typed payload phải giữ raw và trạng thái thiếu riêng; explicit 0 khác missing. Không thêm quy tắc tài chính hay yêu cầu mọi số phải dương. Bảo toàn nguyên tệp/cell để truy nguồn.

### B6 — Quyền hiện tại và seed trung thực

- RLS `m4.bien_nhan` hiện chỉ kiểm login/user ở phần SELECT, chưa kiểm grant project/module hiện tại. Sửa đường đọc receipt để không mở dữ liệu ngoài scope sau thu hồi; lệnh replay đã có gate quyền đúng vẫn phải giữ.
- `m4.quyen_du_an` hiện chỉ cho thu hồi bằng DELETE và chặn mọi UPDATE. Kiểm thử phải giữ file/DB, nên dùng cơ chế quyền có lịch sử đã có nếu phù hợp, hoặc marker/event thu hồi append-only hẹp cho đúng project grant do admin cấu hình ghi. Ordinary app không tự cấp/thu hồi quyền; `master.m4_duoc` và receipt phải đọc lifecycle hiện tại. Không dựng IAM mới hoặc dùng DELETE kể cả trong rollback.
- Owner-only hoặc cấm reviewer xem mọi master HĐ nháp chưa được chốt thành business policy. Không tự thêm hạn chế owner-only từ một comment seed. Dùng assignment/role hiện hành theo PN/project/dossier; ghi rõ contract và ca âm của người thực sự ngoài quyền. Reviewer không tự xác nhận tham số của phòng dự án.
- Seed phải phân biệt đủ/thiếu/chưa sẵn sàng; không coi thấy một actor là đã seed đủ cả bộ. Không reset dữ liệu, sửa hợp đồng cũ hoặc cấp lại grant đã thu hồi để test xanh. Chỉ actor MO_PHONG_ cho kiểm thử.

## 3. Ca kiểm phải viết, nhưng chưa chạy trong lượt CODE_ONLY

1. File hợp lệ đi qua capture thực; NUL/traversal/giả media bị chặn. Ordinary role không tự tạo source/extraction/BOQ fact thành công hoặc giả XONG/DA_MAP bằng SQL/body; worker đúng quyền với bytes/lineage hợp lệ tạo được fact.
2. Mỗi lệnh bị lỗi replay ở B2: positive lần đầu, retry EXACT key/body/revision gốc trả cùng kết quả; retry sau một thay đổi căn cứ hợp lệ khác vẫn đúng receipt, trừ khi quyền đã bị thu hồi. Changed body và concurrency không tạo thêm business rows; parse/AI không bị chạy lại khi replay. Ordinary SQL tự tạo/chốt receipt với fake resultJSON hoặc giả machine-check phải bị từ chối; command hợp lệ vẫn chốt và replay được đúng kết quả.
3. DOCX physical có Track Changes đi qua đường sửa tham số không gọi Office/cleanup; nguồn/artifact giữ. Collision module có sentinel không được execute trước lỗi origin; dependency cấu hình cũng không chạy nhầm.
4. BOQ XLSX thật: lỗi thiếu/mơ hồ cột vẫn chặn; dòng map/parse đủ nhưng sai số học giữ finding và không tự chặn Nộp khi căn cứ khác đầy đủ. Explicit0 và blank được phân biệt ở raw/typed output.
5. Revoke module/project rồi đọc/replay/file bị kiểm theo quyền hiện tại; ca khác PN/project bị chặn. Ca project revoke phải giữ actor hoạt động và module M4 còn quyền; không gắn nhãn global-disable thành project revoke. Dùng action phù hợp cho vai, không ép policy owner-only chưa có.
6. Tool kiểm nguồn thiếu file → nonzero; đủ →0 và tất cả byte/hash đúng, không xóa/ghi đè. Prefix1–16 không đổi, catalogue XD đủ37 mã/TC-09; không ép catalogue37 vào KCN/nhà ở.

Expected phải từ fixture/source/case tự xác định; không lấy output hệ thống làm đáp án. Test giữ toàn bộ DB/role/file/attempt; không TemporaryDirectory cleanup, DROP/DELETE/TRUNCATE hoặc sửa guard. Không mirror implementation bằng những assert chỉ kiểm cùng một hàm với chính nó. Native Local AI/OCR và fake AI đã khai báo phải báo riêng; mock plumbing không chứng minh accuracy thực.

## 4. Phạm vi ghi và bàn giao

Root sẽ phát settings chính xác trước dispatch. Mục tiêu sửa hẹp: M17, `k2/xay_dung.py`, `giao_dien/m4.py`/factory cần thiết, `m4/nguon_review.py`, tool nạp nguồn, seed/fixtures và tests `test_m4_*.py`; thêm helper M4 hẹp nếu cần. Không sửa source app gốc, baseline migrations1–16, CRM/M1/M9/L11 business logic, guards hoặc credentials. Chưa mở UI gói C trong gói B để tránh trộn repair với thiết kế màn hình.

CODE_ONLY: không lệnh, import, test, SQL, HTTP, AI/OCR, browser, launcher hoặc tool nạp nguồn. Claude viết code/tests và `docs/BAO-CAO-M4-01B.md`, self-tests NOT_RUN; Root chạy sau actual terminal/freeze/FULL review. Báo rõ cách inject trusted dependency, contract receipts, phân loại BOQ, file targets và lệnh Root cần chạy. Không tự chuyển sang gói C hoặc ghi M4-01/toàn M4 đã xong.
