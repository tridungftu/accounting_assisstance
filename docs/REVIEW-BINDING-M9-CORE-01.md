# Review độc lập binding M9/core — 01

19/10/2026. **STATIC_ONLY / M9_NOT_IMPLEMENTED / NOT_ACCEPTED.** Bản reviewed: `BINDING-M9-CORE-SAU-CRM03.md` SHA256 `44e28e161b63280d7c7462eaec73fef1461b53b9e26d139b306e42575a68af9d`; proposal revision2 `THIET-KE-M9-TYPED-DEMO-33.md` SHA256 `e3e9704f5af808bc3c398a84ba85e3a80e0bc4b51c4042c1bda90fb73cfa9bf3`. Chỉ đọc docs và source **frozen03**, không import/chạy product/test/SQL, đọc credential/row thật/backup, gọi source ngoài hoặc sửa binding của tác giả. Launcher04 đang sửa không được dùng làm final source.

Các finding dưới là điều kiện kỹ thuật cần cụ thể hóa trước triển khai, **không phải lỗi runtime đã tái hiện**. Root đã đồng ý hướng xử lý ba điểm P1; tác giả/root quyết định amendment. Không cần mở lại policy hoặc kiến trúc đã chốt.

## P1 — R1. Khóa các discriminator quyết định quyền và cách tính ngân sách tại DB

**Anchors:** binding dòng76–78,87–94,109; frozen `pg_migrations.py:1296` (`hop_dong_kiem`),`:1172` (RLS),`:1455` (`lien_ket_kiem`). Frozen03 đã cấm đổi `hop_dong.loai/PN/identity` ở UPDATE; phải **giữ** guard này khi dispatch VAY→M9, không xem loai đang mutable.

Hai field mới `module_nghiep_vu` và `allocation_model` chưa có contract mutation tương đương. “Server đặt/guard”, allowlist giá trị và RLS USING/WITH CHECK chưa tự bảo đảm SQL không đổi discriminator: actor có cả hai module có thể đổi ownership module; DIRECT→CHILD không child có thể làm amount cũ không còn tiêu budget. `viec_can_duyet.module` và lô `du_lieu.module` cũng cần gắn owner subject, không trở thành đường đổi phạm vi file/work.

**Bổ sung:** DB xác định/check owner module từ subject/nguồn đã bind; SAO_KE luôn M1, M9 evidence/proposal thuộc M9. Chặn user UPDATE discriminator/reparent; field phải immutable sau tạo hợp lệ. Nếu thực sự chuyển DIRECT/CHILD thì chỉ qua transition được cấp riêng, khóa common budget và kiểm nguyên totals/FK/refs/history cùng transaction; không tự đổi model vì có/không có child, không client-set GUC để bỏ guard. Work/lô/proposal và FK subject không được mang module khác chủ thể thật.

**Ca cần có:** ordinary SQL thử đổi VAY→CRM (giữ denial cũ), M9→M1 trên chứng từ/work/lô, DIRECT→CHILD rỗng, child→parent khác cùng PN. Đối chứng tạo đúng domain/model bằng workflow thật đạt; ca trái phép0 business delta, budget/file visibility không đổi.

## P1 — R2. Fingerprint không thay kiểm eligibility/V4 và guard toàn graph khi SQL trực tiếp

**Anchors:** binding dòng52–66,76–80,125; proposal §5; frozen `pg_migrations.py:1286` (fingerprint),`:1321` (insert PB),`:1389` (guard tham số),`:1549–1614` (M12 approve); frozen `crm.py:491` (V4/blocker xử lý ở service).

M12 DB transition chủ yếu kiểm actor/V3/check-digest; blocker domain và việc V4 còn mở nằm trong service CRM. Chỉ thay hàm fingerprint rồi dùng lại trigger này cho VAY chưa chứng minh được direct SQL không duyệt một graph thiếu `vay_phien_ban`, amount/precision/basis, có overlap LOAN/DRAW hoặc V4 chưa xong. Hash có thể khớp hoàn toàn với **graph chưa đủ điều kiện**. RLS theo PN+module cũng chưa cấp/phủ quyền WRITE/CHECK/APPROVE cho từng role; viewer M9 không được sửa child draft chỉ vì cùng PN/module.

**Bổ sung:** một DB domain validator/transition contract cho VAY, gọi ở đúng INSERT/check/approve/state-change, kiểm typed graph đủ và V4 theo subject/thời điểm transition. Mọi INSERT/UPDATE/DELETE child phải kiểm action/OLD và NEW parent, cấm đổi identity/reparent để đưa row đã duyệt sang PB draft; approved/referenced graph bất biến. Draft child đổi có quyền phải làm check cũ mất hiệu lực. Child mutation và check/approve cùng khóa HĐ/PB để không có commit chen sau fingerprint nhưng trước approval.

Fingerprint M9 cần field manifest/canonical version rõ: alias/PN/HĐ/PB, draw identity+revision, mọi rate theo effective date, lịch scope/component/logical key/amount/currency/scale/period, event parts, source/derivative refs, mapping/profile/precision/basis revisions; phân biệt NULL/0 và thứ tự tập con ổn định. Không dùng RLS-filtered graph hoặc concat delimiter/NULL omission cũ làm digest đầy đủ; tách audit/check/state/derived-paid khỏi fact digest có giải thích, không bỏ field nguồn quyết định eligibility.

**Ca cần có:** role thường SQL chèn approved PB/child, viewer sửa draft, chuyển child approved sang PB khác, KT check graph thiếu rồi CFO/V3 approve trực tiếp khi V4 còn mở; tất cả phải từ chối ở DB. Có workflow hợp lệ làm control dương. Sau check thay riêng rate/amount/precision/mapping/basis/source link thì stale approve bị chặn; approved child không đổi; concurrency child-vs-approve không có bản approved mang graph ngoài digest.

## P1 — R3. Target remaining phải giữ consumption xuyên revision của cùng draw/nghĩa vụ

**Anchors:** binding dòng52–66,87–115; proposal dòng94–100,110–122,144–164. Draw giữ identity nhưng mỗi PB có `khe_uoc_vay_phien_ban.id` mới; allocation giải ngân trỏ **draw revision**. Binding đã bảo vệ BANK remaining chung, song chưa neo rõ target consumption khi PK/basis revision đổi.

Nếu giải ngân đã nối vào draw revision cũ, sau một PB/rate/basis revision cùng draw identity lại tính target remaining chỉ theo revision UUID mới, tiền cũ sẽ không tiêu capacity mới. Một BANK khác có thể được nối lần nữa cho cùng financial event, dù từng BANK riêng đều không vượt ngân sách. Cùng vấn đề với nghĩa vụ có logical key ổn định nhưng row/basis revision mới. Đổi basis không được tạo financial event mới mặc định.

**Bổ sung:** target consumption/remaining dựa stable logical draw/financial event hoặc obligation+component và policy/basis transition được bind, **tính cả allocation cũ còn hiệu lực**. Giữ FK tới old revision, audit/protected refs; không move link hoặc reset Paid vì PK mới. Khi basis thay sau đã nối, giữ consumption cũ hoặc impact/reconcile/holding; không mặc định free capacity. Amount giảm dưới consumed phải reject/hold; amount tăng chỉ là candidate capacity có căn cứ sau review, không tạo BANK/112 hay mở lại phần đã thanh toán. Undo dùng cùng identity/effective-history và lock protocol HĐ→BANK→target.

**Ca cần có:** cùng draw identity đã nối tiền, nhập lại/đổi PB/rate/basis revision rồi thử BANK khác và same-BANK retry; cross-revision remaining vẫn trừ old active allocations. Thêm amount decrease/increase, nghĩa vụ superseded cùng key, undo/retry tombstone, old link/PK/lô đã bảo vệ. Có control tạo draw/event **thực sự khác identity** để không reject mọi thay đổi. RC3 CRM DIRECT + M9 CHILD và hai race order vẫn bắt buộc; một winner/loser thật, không lấy timeout làm pass.

## P2 — R4. Neo scale/precision eligibility vào chính BANK hiện có

**Anchors:** binding dòng42,91,95–109; frozen `pg_migrations.py:207–234`. BANK hiện có `so_tien_minor/tien_te`, chưa có currency_scale/precision-contract typed. Registry chung có scale không tự chứng minh cách encode **BANK lịch sử cụ thể**.

Khi bind `tien_con_lai`/currency-scale equality phải chỉ ra cột/reference/immutable money contract của BANK và cách backfill kỹ thuật có chứng cứ; không dùng registry hiện hành hoặc default0/VND để đoán legacy. BANK chưa đủ precision/scale phải blocked/holding đúng contract đã nêu; không trả numeric remaining giả. Control VND0 có nguồn chứng minh, USD2 có source contract và scale mismatch/unknown giữ chờ. Đây là việc neo schema cần hoàn tất, không yêu cầu chính sách FX mới.

## Các phần phù hợp giữ nguyên

Grain raw→snapshot/row→derivative PN→typed source graph, alias không chứa financial kind/target PN, FK composite PN/HĐ/PB, LC→SHORT giữ identity, lịch LEGACY/M9_TYPED và kiểm ON DELETE CASCADE cũ là đúng hướng. Missing-date không tạo chứng từ giả/không lấy ngày import là rõ; dated positive vẫn promote. Common DIRECT/CHILD, parent=sum child, full-BANK aggregate không bị RLS che, idempotency receipt, tombstone và lock order đã có căn cứ phù hợp; cần triển khai/test cùng consumer CRM, không bật CHILD riêng M9. Per-PN atomic promotion, giữ source reject và không default NULL/precision đều phù hợp.

Chưa có migration/API/runtime M9 từ review này. Điều kiện nghiệm thu sau coding vẫn corpus19 + RC2–4, các ca R1–R4, ordinary SQL/RLS hai PN, concurrency có observer, protected period/refs, exact artifacts/restart/GUI đúng phạm vi; không cộng static review thành số test PASS.
