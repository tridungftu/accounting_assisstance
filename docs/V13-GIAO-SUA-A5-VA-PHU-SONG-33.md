# V13 — candidate sửa A5 và coverage trước khi đóng gate

**19/10/2026 · STATIC_ONLY / TECHNICAL_CANDIDATE / ROOT_REVIEW_PENDING / REBASE_AUTHORITATIVE_BASELINE_REQUIRED / M9_STOP / NOT_IMPLEMENTED / NOT_ACCEPTED.** Chỉ cụ thể hóa bốn lỗi A5 đã ghi trong `KIEM-CHUNG-WINDOWS-V13.md`; không đổi chương trình toàn33 hoặc mở policy mới. Claude chỉ nhận code package khi root review/release riêng về sau; hiện không có handoff hoặc runtime release. Lượt này không đọc live M9/source app/real rows/DB/credentials, import/chạy product/test/SQL/HTTP/host/process hoặc xóa file. Yêu cầu mới của Anh **dừng M9** có hiệu lực tuyệt đối; các dependency M9 lịch sử bên dưới không là chỉ dẫn tiếp tục M9.

Giữ **V13 option C**: runtime V12 chạy qua bộ dịch/chép nguyên bảng; converter K2 là projection riêng, chuyển lõi K2 thuộc V14; kho thật vẫn SQLite. Không sửa cutoff30/06/2026, nâng Junsky mức2/cloud hoặc duyệt thật. A5 đạt không chứng minh backtest sạch, chất lượng dự đoán, hiệu năng, backup/restore/quyền/GUI hay toàn V13/toàn33 đã đạt.

## 1. Baseline được đọc và bằng chứng đang có

Frozen root duy nhất: `var/codex-dieu-phoi/kiem-chung-20261018-101441/crm06-handoff-20261019-095149-416/frozen/`. Manifest125files SHA256 **`c828d1fff9593a0dce6d47e079df8adf76a4609cb936e2f1a627cf1a9948dd08`**. Đã đối chiếu hash9technical files được đọc với entries tương ứng trong manifest, đều khớp; không gọi đây là kiểm lại toàn125bytes.

| File frozen / tài liệu technical | SHA256 |
|---|---|
| `tools/chuyen_sqlite_sang_pg.py` (gọi tắt C) | `97c577768014e6139a2270d02551f5e1863b686c4b103581bfea2e411532a19c` |
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` (P) | `31f25277b5e08a0f54843191bce2b3e54126dc6770ad02ece310c8265fcac1e5` |
| `src/kho_tri_thuc/ha_tang/postgres.py` | `ffca2c38527ade742d12c5332ff29e3c54eae77f111362c7d5f9b0453bbdf6f8` |
| `src/kho_tri_thuc/ha_tang/sao_chep_bang.py` | `cf39c0470635106647992c478fdf03a1ebe3991dacf3697b064070e6d94ef130` |
| `docs/KIEM-CHUNG-WINDOWS-V13.md` | `cab7d6215c0598f35d6b85896499113d4fe77d6ae4a78db97449806c3aa2e162` |
| `docs/GIAO-VIEC-CLAUDE-V13-WINDOWS.md` | `53aa376205a6c7fff7aca51386f08ad40002b2fb5d608a417360ab4081d4cbbb` |
| `docs/REVIEW-CRM-M1-03.md` | `2d8b30eab1cfbe7df1e45ce0dee008ae8720747be247019a9b293e1aa3f84180` |

Windows report đã ghi probe runtime phát hiện ba semantic blind spots và15bảng chưa hash; lượt này chỉ xác nhận đường code tĩnh gây chúng, không tái chạy probe. Review CRM-M1-03§5 chỉ chứng minh source3BANK/2artifact và bảo toàn shared target, **source COUNTERPARTY/PROJECT đều0**, nên không thay positive chuyển đủ danh mục. Negative G12 là preflight core-hash failure trước ghi, không chứng minh mọi lỗi giữa transaction rollback. Không mở lại artifacts/DB thật từ các báo cáo này.

## 2. A5-L — line_key phi số: thứ tự phải xác định, injective và được kiểm thật

**Trigger hiện có:** C:319 query `document_lines` không ORDER BY; C:325–327 dùng `int(line_key)` hoặc fallback **m+1 toàn lượt**, không theo chứng từ. Upsert C:329–332 theo `(chung_tu_id,stt)` có thể ghi đè line khác khi numeric/fallback đụng nhau. C:602–606 trả `"*"` cho key phi số; source fingerprint C:668–670 và target C:739–741 cùng bỏ actual STT, nên đổi STT vẫn có thể khớp. Nguồn SQLite chỉ unique `(document_id,line_key)` (`database.py:46–49`), không bảo đảm `int(line_key)` injective.

**Contract sửa cụ thể, mapping version phải pin trước run:**

- Logical converter line key = source namespace/PN + source document identity + **nguyên text line_key**, không STT/row position; không trim/case-fold/ép số để gộp keys. STT chỉ technical projection, không tự nhận là thứ tự nghiệp vụ nguồn nếu nguồn không cung cấp.
- Trước connect/ghi, lập toàn mapping **theo từng document**. Giữ numeric ordinal trong integer range khi phép chiếu injective và hợp lệ; phát hiện `"1"`/`"01"` cùng chiếu1, overflow hoặc ordinal chưa có nghĩa rõ thì structured conflict/holding, không merge/clamp. Với key phi số theo profile đã pin, cấp ordinals không đụng numeric đã giữ, theo stable exact source-key order; ví dụ numeric1,2 và A→1,2,3; toàn A,B→1,2. Không dùng iteration order/global m; document khác thêm dòng không đổi map cũ. Nếu hết integer range, reject trước mutation.
- Pin một representation source-key→lineUUID/STT. Nếu final common core chưa có equivalent exact bridge, đề nghị nullable typed `kho.chung_tu_dong.nguon_v13_line_key` + partial UNIQUE(chung_tu_id,nguon_v13_line_key) cho converted lines; giữ existing `(chung_tu_id,stt)` UNIQUE. Converter resolve/upsert **source line identity** rồi assert expected STT, không dùng STT làm identity để overwrite line khác. Backfill chỉ với exact unique parent-source/line_key correspondence; unknown/duplicate giữ task. Không đặt global index lên mọi JSON line_key của M2/M5 native profiles khác.
- Source fingerprint lấy **expected integer STT từ independently specified mapping**; target đọc và hash **actual `d.stt` mọi dòng**, kể cả phi số, đồng thời so source-key/parent/typed column/JSON và missing/extra/duplicate. Không tái suy STT từ target line_key hoặc thay bằng wildcard. Cùng helper map có thể reuse trong writer/reader, nhưng independent DEMO vectors/oracle không chỉ gọi helper đang kiểm.
- Replay giữ line UUID/parent/source key/STT và content. Legacy nonnumeric STT do fallback cũ không được lấy từ đích rồi mặc nhiên gọi là expected đúng; cần proof/crosswalk độc lập trên bản retained. Nếu chưa tái dựng được thì holding, không sửa approved/protected order/file refs, xóa/reinsert hoặc cho `ON CONFLICT(stt)` che xung đột. New technical metadata backfill phải giữ old columns/PK/history, không rewrite source JSON/hash để hợp thức hóa.

**Before→after expected:** Source key A, expected STT1, typed target tamper STT9 trong khi JSON/hash cũ giữ nguyên: hiện có thể `khop=true`; bản sửa phải `lech>0/khop=false`. Mixed numeric+phi số không overwrite; collision numeric alias bị reject trước ghi. Existing canonical numeric fixtures vẫn positive; ordinal mapping xác định qua hai lần chạy và đổi thứ tự đọc.

## 3. A5-P — hai project FK cùng mã nhưng khác pháp nhân

**Trigger:** C:632–638 source project key chỉ `ma_junsky`; C:697–712 JOIN dự án theo UUID nhưng chỉ chọn `da.ma_junsky`; C:735/749 hash mã đó, không parent PN. P:221 và274 chỉ UUID FK cho `kho.chung_tu.du_an_id`/`kho.cong_no_mo.du_an_id`. Đổi row PN_A sang project PN_B có cùng mã có thể bị verifier bỏ qua. Parent UNIQUE(id,phap_nhan_id) **đã có** ở P:1263, chỉ `master.hop_dong` đang reuse composite FK ở1266.

**Contract:** Source expected project ref là tagged `(canonical source-PN,project_code)` hoặc explicit NULL khi không được ánh xạ; target fingerprint phải dùng **actual FK presence + actual referenced parent PN/code**, normalize PN qua `master.phap_nhan.ma`/approved source identity, không UUID ngẫu nhiên giữa DBs. `doc_dich` chọn child PN/du_an_id và referenced PN/code; không thêm same-PN JOIN filter để che wrong-parent thành NULL. FK nonNULL nhưng parent không đọc được/missing→mismatch/NOT_VERIFIED, không so NULL=unknown. Raw `du_an_junsky` vẫn được hash riêng.

DDL candidate append sau final M9, reuse parent unique: composite FK `(du_an_id,phap_nhan_id)` của **cả hai bảng** →`master.du_an(id,phap_nhan_id)`, RESTRICT/NO ACTION; không MATCH FULL vì project NULL là legitimate khi child PN nonNULL. Không cần sửa M0001–12 hoặc xóa UUID FK cũ. Audit existing violations trước validate; bad rows giữ nguyên và báo blocker/impact, không tự đổi project về cùng mã/NULL hoặc PN của record.

**Hai controls bắt buộc riêng:** P-DOC và P-OPEN_ITEM: PN_A/source project DEMO_X→actual project PN_A/DEMO_X positive; đổi đúng FK sang PN_B/DEMO_X phải (a) verifier phát hiện wrong-scope trên synthetic target rows/retained pre-fix schema và (b) final DB composite FK từ chối ở correct constraint boundary. RLS/ACL/protected-state denial trước khi chạm FK chỉ chứng minh denial đó, không được cộng thành FK hoặc verifier PASS. Source expected NULL và genuine same-code project của PN_B trong hồ sơ PN_B là positive counterparts.

## 4. A5-K — supersedes_id tri thức phải giữ tenant/source scope

**Trigger:** C:686 source chỉ predecessor `_sqlite_id`; C:715 target JOIN `supersedes_id` theo UUID rồi chọn cùng source ID, C:757 hash một string này. P:621 là self UUID FK. PN_A/KV2 trỏ nhầm PN_B/KV1, cùng `_sqlite_id=KV1`, có thể vẫn khớp.

**Contract:** Fingerprint predecessor dùng tagged `(actual predecessor canonical PN/source scope,_sqlite_id)` + presence, không dùng PN của **child** để mặc định cho parent. Source expected dùng source-PN của converter và exact predecessor source identity. Target query chọn actual child/parent PN+source-key; same ID text khác PN phải khác hash; nonNULL FK nhưng thiếu typed/source provenance không thành NULL/khớp. Giữ known_at/valid_from/to/actor/evidence/approval namespace nguyên; không lùi ngày về cutoff hoặc sửa payload/hash để chữa relation.

**Phạm vi physical guard là converted edges, không toàn `kho.tri_thuc`:** không thêm plain `(supersedes_id,phap_nhan_id)` FK trên mọi knowledge row. FK đó sẽ áp cả native local child→global predecessor (parent PN NULL), dù MATCH SIMPLE không cho quan hệ ấy vượt kiểm khi child PN nonNULL; hiện chưa có accepted K3 rule trong đầu bài để quyết định cấm quan hệ native này. Giữ existing UUID FK; source verifier vẫn phải phát hiện actual predecessor PN/source-key sai như trên. Native/global rows/edges có baseline riêng được bảo toàn; chưa có business rule thì giữ NOT_VERIFIED phần semantics, không tự xóa/NULL/reparent/retag để validate.

**Typed ownership làm predicate không thể bị caller tắt:** trước implementation root phải bind vào trusted immutable converted-source registry sẵn có nếu có cùng invariant trong authoritative baseline. Nếu chưa có, đề nghị sidecar typed `kho.tri_thuc_nguon_v13` chỉ cho converted versions: `tri_thuc_id` PK/FK, `phap_nhan_id NOT NULL`, `source_namespace NOT NULL`, `source_key NOT NULL`, pinned converter/profile + validated source artifact/attempt identity; UNIQUE(PN,source_namespace,source_key), composite FK `(tri_thuc_id,phap_nhan_id)`→`tri_thuc(id,phap_nhan_id)` dùng parent UNIQUE tương ứng. Sidecar không đặt composite predecessor FK lên native rows. Registry identity/PN/namespace/provenance bất biến, không suy ownership từ `_sqlite_id`/JSON/source flag tự khai hoặc PN NULL.

- Trusted conversion path đăng ký ownership và knowledge row/edge nguyên tử, kiểm đủ mọi expected source identity trước commit. Ordinary caller/converter caller không có quyền UPDATE/DELETE registry hoặc tự chọn provenance để đăng ký thành native; routine đăng ký hẹp phải xác thực source namespace/attempt/artifact/identity từ trusted conversion context, không tin boolean caller. Backfill chỉ từ exact independently verified source↔row correspondence; thiếu proof giữ blocker, không coi registry thiếu/NULL là chứng minh row native. Không chép global/native rows vào registry để ép policy mới.
- DB guard trên INSERT/UPDATE `tri_thuc.supersedes_id` của **owned converted child** resolve registry bằng immutable child UUID; predecessor nonNULL phải có typed converted ownership cùng PN/source namespace. Kiểm cả lúc ownership được đăng ký và cuối transaction khi các predecessor đã resolve; source exact predecessor-key còn được verifier/two-pass map đối chiếu. Parent/child PN, registry identity hoặc provenance đổi sau đó cũng không được phá invariant. Thay JSON/source flag/known-time hoặc gửi native/NULL discriminator không làm mất lookup theo UUID; bị từ chối ở đúng guard/immutability boundary, không fallback bỏ kiểm. Fake native row với source-looking JSON không được resolver/verifier nhận là converted counterpart.
- Native global→global/local→global/local→local ngoài registry giữ existing constraints/baseline; chưa có approved K3 semantics không tuyên các quan hệ ấy đúng nghiệp vụ hoặc blanket cấm. Review hardening của registry/routine/ACL/transaction và coverage là gate technical còn phải thực hiện; các tên extension ở đây là đề xuất, chưa là DDL có sẵn hoặc quyền runtime được cấp.

Converter giữ hai lượt C:442–459: resolve/upsert toàn versions cùng source PN rồi nối predecessors bằng exact map; unresolved/duplicate/cross-scope relation phải preflight/holding, không sửa target theo bare `_sqlite_id` hoặc bỏ FK âm thầm. Self/sequence/validity mới ngoài yêu cầu A5 này không tự thành policy cho knowledge; không dùng relation sửa để tự approve tri thức thật.

**K-SUP control:** converted A2→A1 cùng source scope positive; converted A2→B1 cùng source ID text phải verifier mismatch và final conditional DB guard reject, báo hai loại evidence riêng như §3. Converted A1 không predecessor giữ NULL. Thử caller đổi/xóa ownership, đổi PN/namespace, set discriminator NULL/native, sửa source JSON, hoặc thay bằng fake-native counterpart: không bỏ tenant check/source identity gate; có correct-owner retry positive riêng. Pin native global→global/local→global/local→local baseline trước/sau; preserve các edges ấy, semantics chưa được chốt giữ NOT_VERIFIED, không cộng native preservation thành converted-guard proof. Source/target known-time/hash/old IDs không đổi vì migrate guard. Chưa đo runtime mới.

## 5. A5-C — exact converter coverage, không “14/14 toàn K2”

C:_dem_dich526–543 thu counts của19written tables; `_doi_chieu`777–793 chỉ có14mapping rows/13distinct targets vì JOURNAL/BANK cùng `kho.chung_tu`. Sáu bảng dưới đây có diagnostic count nhưng không equality assertion. A5 fingerprints623–771 hardcode **4tables**, `core_hash_nguon` là preflight, không table thứ5. Cần source-scoped content contracts cho đủ19targets, thêm15chưa hash:

| Converter target | Write C:line | Count equality hiện có | Content hash hiện có |
|---|---:|:---:|:---:|
| master.phap_nhan |166|—|—|
| master.tai_khoan |184|Có|—|
| master.khoan_muc_phi |190|Có|—|
| master.ttcp |195|Có|—|
| master.du_an |200|Có|—|
| master.doi_tac |231|—|—|
| master.doi_tac_ma_junsky |252|Có|—|
| master.doi_tac_dinh_danh |259|—|—|
| master.tai_khoan_ngan_hang |512|—|—|
| kho.tep_goc |270|Có|—|
| kho.chung_tu |305|Có, JOURNAL/BANK|Có|
| kho.chung_tu_dong |329|Có|Có|
| kho.cong_no_mo |349|Có|Có|
| kho.de_xuat |382|Có|—|
| kho.de_xuat_dong |406|—|—|
| kho.viec_can_duyet |418/425|—|—|
| kho.tri_thuc |449/459|Có|Có|
| kho.canh_bao |494/500|Có|—|
| nhat_ky.su_kien |140/477/483|Có, projection V12|—|

**Registry coverage phải khai từng table:** source locator→stable source/target identity/cardinality→mapped typed fields/JSON/FK tuples→allowed server-derived/default/NULL fields→scope+duplicate/extra policy→expected/observed hashes/counts. `required - implemented` hoặc unsupported shape khác rỗng→NOT_VERIFIED/fail gate, không `all([])=True`; report tách total written19, covered19, exercised-nonempty, scope exemptions. Tái tính canonical payload từ source và actual target columns/FKs; không tin stored hash, copied JSON, flag hoặc chỉ tổng Nợ/Có/count. Preserve exact text/int64/Decimal, NULL≠0≠empty/absent, datetime UTC rule/profile; amount9007199254740993 không qua float/JS Number/Excel rounding. No raw keys/values trong báo cáo public/Claude.

Các15vectors mới tối thiểu sau phải có representation thật trong registry, không chỉ một TODO “hash table”; column ngoài writer không tự default thành source fact. Server timestamps/IDs được kiểm preservation/allowed derived metadata riêng, không bỏ mọi timestamps hoặc mọi FKs khỏi business hash:

| Target chưa hash | Stable identity/cardinality và expected mapped vector |
|---|---|
| master.phap_nhan | source workspace entity→PN.ma; exact ma/ten/ma_don_vi_junsky theo C:160–172, approved existing PN baseline/COALESCE rule, không default PLHN cho fixture thiếu scope rồi gọi map đúng |
| master.tai_khoan | GLOBAL+source code; ten/cap/tk_cong_no/tk_tien/valid_from, existing nullable/default/valid_to fields giữ theo catalog contract |
| master.khoan_muc_phi | GLOBAL+source code; ten/valid_from+typed scope/default fields |
| master.ttcp | GLOBAL+source code; ten/valid_from+typed scope/default fields |
| master.du_an | PN+source code; ten/valid_from+parent/status fields writer không set theo defined NULL/default/preservation, actual PN không chỉ code |
| master.doi_tac | Source MST group hoặc no-MST source provenance; new rows ten_phap_ly/ten_chuan_hoa/mst/loai/vai_tro/ghi_chu theo C:217–246. Reused approved global master C:221–229 giữ independently pinned pre-run authoritative baseline, source/MST correspondence và alias edges đúng; không giả source name overwrite mọi existing master là parity |
| master.doi_tac_ma_junsky | PN+object_id_junsky; actual resolved doi_tac identity/MST/scope, tien_to/ten_junsky/valid_from; reused immutable/validity fields giữ đúng converter update-vs-insert contract |
| master.doi_tac_dinh_danh | Resolved parent+kindMST+value hash; gia_tri/gia_tri_hash/nguon/do_tin_cay đối chiếu từ source group, no-MST không fake identifier; hash value độc lập stored hash |
| master.tai_khoan_ngan_hang | PN+tk_ke_toan; stk_hash tái tính từ fixture source text+ngan_hang/co_sao_ke/nguon_sao_ke theo insert/update branch; conflicting source rows collapse vào same target phải detect/hold, không last-row-wins. Không public STK hoặc biến hash thành money encoding proof |
| kho.tep_goc | PN/source artifact hash+resolved UUID; loai_nguon/duong_dan/hash/kich_thuoc/nhan_luc/nguon; wrong tenant/value phát hiện dù hash key còn, actual bytes nếu được source contract yêu cầu vẫn kiểm ở private input boundary |
| kho.de_xuat | Parent PN/source document +V12 quick_item identity+version; chu_trinh/muc/hien_hanh/vi_sao/can_cu toàn provenance/nguon_suy_luan/tao_boi theo C:368–385; protected skip có baseline evidence, không bỏ qua rồi tính0source rows là đạt |
| kho.de_xuat_dong | Exact proposal identity/version+offset; no_co/acct_id/base_deb/base_crd/object/project/cost/center; source explicit lines hoặc fallback cash/noncash branches từ supplied proposal, hai branch có fixture riêng, không đổi account policy |
| kho.viec_can_duyet | PN+typed proposal subject/V1/state lifecycle; module/chu_trinh/muc/trang_thai/tom_tat/amount/currency; source WAIT→một eligible pending work, quyết định source→đóng đúng work giữ history; không đếm mọi existing work hoặc tự tạo V1 thật |
| kho.canh_bao | PN+source namespace ISSUE/QUARANTINE+logical source identity; ma/muc/thong_diep/viec_can_lam/trang_thai+dedup multiplicity đúng declared rule; samecode/message khác PN không suppress, missing source IDs/cardinality không suy từ count n được writer cộng |
| nhat_ky.su_kien | PN+source log-kind+_sqlite_id, không collision activity/audit; luc/nguoi/loai/doi_tuong_bang/hanh_dong/sau typed JSON+recorded_at theo C:463–484. Conversion marker/other live audit riêng allowed append/preservation, không xóa/ignore toàn audit để xanh |

C:402–407 hiện còn nhánh **DELETE rồi INSERT proposal lines khi nội dung khác**. Không dùng nhánh này để “sửa parity”/clear mismatched rows; scoped package phải giữ line PK/history/protected refs bằng common version/impact path đã duyệt, hoặc holding khi chưa có path. Same-content rerun bỏ qua DELETE không chứng minh changed-source preservation. Không triển khai đường thay thế bằng xóa record/file hoặc vô hiệu guard.

**Scope/cardinality cụ thể:** global ACCOUNT/EXPENSE/TTCP chỉ source codes (C:177–200), không hash toàn global table như imported subset. Global doi_tac gộp theo MST/nguồn không MST đúng existing converter contract (C:209–246), hash resolved parent+typed identity và alias edges, không ép count source1:target1. Three shared PN tables `doi_tac_ma_junsky/du_an/tep_goc`: cờ `cho_phep_du_dung_chung` hiện chỉ kiểm đủ key (C:104–115,149–154); bản sửa cần **source subset content equal** và surplus full-row/PK/foreign refs trước=sau, không cho count surplus che wrong content/tenant. `de_xuat_dong/viec_can_duyet/doi_tac_dinh_danh/tai_khoan_ngan_hang` có cardinality derived; expected từ explicit conversion rules, không ép một row mỗi document. Projection nhật ký chỉ `v12.*` có `_sqlite_id` đúng namespace log/audit; marker CHUYEN_DOI `doi_tuong_bang=kho.sqlite` và live audit hooks kiểm riêng theo allowed append delta, không cộng thành source parity hoặc xóa marker.

**Không nhầm ba inventories:**

- Option C runtime copy/hash là **49app tables**, không phải19convertertargets; `sao_chep_bang.py:24–32,71,89,174–185` derive từ SQLite MIGRATIONS. `schema_migrations` là bảng thứ50 được migration dựng/kiểm history riêng. Chỉ loại exact `workspace_meta.DAU_NAP_XONG` marker (`:135–138,155–161`), vẫn hash metadata source khác và rowid theo contract; không normalize mất source state.
- Full K2 frozen có **42business tables** trong P, ngoài19convertertargets còn23table: `master.phap_nhan_boi_canh/cau_hinh/nguoi_dung/phan_quyen/nguon_tu_dong/loai_hinh_doanh_thu/hop_dong/hop_dong_phien_ban/hop_dong_tham_so/lich_thu/lich_tra_no/tai_san/nhan_vien`; `nhat_ky.cong_ai_goi/tin_zalo`; `bao_mat.mask_bi_danh`; `kho.phien/khoa_ky/lien_ket_chung_tu/cau_hoi/nhan_hoc/lo_xuat/lo_xuat_dong`. Không project chúng không tự là converter bug; chúng phải thuộc **preservation/full-K2 backup inventory**, không được tuyên bố đã source-parity từ A5. Riêng `master.schema_migrations/he_thong` luôn tạo, `master.migration_tuong_thich` chỉ khi compatibility path chạy (`postgres.py:118–130`), metadata không business-table numerator.
- Sau M9 final phải regenerate exact schema/path-set inventory gồm additions và pin count/DDL/hash mới; không cố giữ42/19/49 nếu actual supported schema thay. New module tables chưa có source conversion spec không tự được gọi transferred/hashed; đánh coverage work gate hoặc preservation, không mở V14/parallel engine vì thiếu gate.

## 6. Thứ tự sửa/migrate/chuyển an toàn sau release

1. Root đọc final M9 terminal/frozen whole manifest/DDL/runner rồi chốt candidate này; không dùng receipt51883 hoặc baseline125 để cấp chạy final. Freeze exact old statements/checksums1–12 và current M9 prefix; append migration mới sau final, không reserve migration number hoặc sửa old checksum/compat allowlist để xanh.
2. Preflight chỉ đọc nguồn consistent snapshot và target metadata: scope/entity, source core hashes, line map injective/range, known identity/crosswalk và existing tenant FK violations. `_chay` hiện kiểm source core trước connect/write (C:79–83); giữ guard này và mở planned-line validation trước mọi side effect. Bad input phải0business delta, không vừa retry/setup rồi gọi đó là before/after của negative.
3. New DDL transaction: source-key representation/index/backfill exact unique correspondence nếu cần; reuse/add parent composite unique; thêm hai project FKs, còn knowledge chỉ thêm trusted typed converted ownership + conditional supersedes guard theo §4. Validate toàn bộ identified converted edges và chứng minh inventory không bỏ missing/unknown ownership; không plain-FK/validate toàn native knowledge để tự thay policy. `NOT VALID` chỉ là bước trong migration được review, không final accepted state; invalid/unknown legacy converted rows làm migration rollback/blocked với scoped aggregate, không delete/NULL/retag/disable tenant guards. `postgres.migrate` frozen đã dùng một transaction (:114–136); final phải giữ đúng boundary và history. Native/global rows/edges/old IDs/bytes/history bảo toàn.
4. Converter chạy riêng trên retained DEMO DB/snapshot sau schema guard: PN/catalog/global refs→counterparty/artifact→headers/line identity-map→open items/proposals→knowledge insert rồi predecessors→audit/other projections. Current `_chuyen` C:121–156 đã có transaction và content gate **trước commit**, giữ rollback; mở gate đủ19tables. Đừng tắt new FK/RLS/proof/period/immutability để qua A5. Hai legacy business triggers đang được converter tạm disable ở C:125–144 là privileged historical path có sẵn, **không là quyền cho harness làm vậy**; root phải review/rebase việc này với final protected/owner/period rules, không mở rộng bypass hoặc dùng owner success thay application safety.
5. Replay lần2/upgrade: giữ original converted IDs/source-line mapping/old source refs và other-module rows; scope không resolve/protected khác incoming source→hold/impact, không delete/reinsert hoặc silently repair bằng converter. Commit xong mở read-only connection mới, độc lập tính lại19source-scoped target contents; report/exitcode chỉ success khi whole gate đạt. Nếu bất kỳ hash/rowset/source-prefix thay ngoài allowed delta thì giữ retained evidence và không đóng A5.

## 7. Các independent DEMO cases phải giao, hiện tất cả NOT_RUN

| ID | Positive/negative và expected evidence |
|---|---|
| A5-L01 | A,B phi số expected ordinals1,2; sửa **actual STT** một row, JSON/hash không đổi→verifier mismatch; không dùng `_stt('*')` làm oracle. Restore bằng rollback own transaction, không xóa history |
| A5-L02 | Numeric1,2+A và document khác: map source keys/ordinal/UUID injective, query iteration khác và replay giữ map; old fallback collision không overwrite. 1/01 hoặc overflow→preflight conflict0target delta, canonical numeric counterpart đạt |
| A5-PDOC/PITEM | Hai cases project tenant độc lập: same code ở A/B, correctA→A positive, tamperA→B verifier mismatch **và** final DB composite rejection theo §3; permission/protected failure không thay exact-FK evidence |
| A5-KSUP | Converted KnowledgeA2→A1 positive; A2→B1 cùng `_sqlite_id` verifier mismatch và conditional DB rejection; predecessorNULL positive. Ownership/provenance không thể UPDATE/DELETE/NULL/retag/JSON-fallback để né guard; fake-native counterpart không được nhận là converted. Native global/local edges baseline giữ, semantics chưa chốt NV; known/valid/source bytes/old history giữ |
| A5-C19 | Nonempty source fixture thực thi mọi19targets+derived branches, đủ source COUNTERPARTY/PROJECT; source/target scoped content matched19, missing/extra/duplicate/mapped-value/FK mutation ít nhất mỗi table/branch phải phát hiện. Nếu constraint chặn trước verifier, kiểm verifier bằng synthetic target projection/retained pre-fix schema hợp lệ, không disable trigger/FK. Missing branch/empty fixture ghiNOT_VERIFIED |
| A5-SHARED | Global/source-code subset, MST grouping, twoPN same project code, shared surplus CRM/PB/link/protected lô; source subset vẫn đúng và unowned/surplus PK+full values/hashes giữ. Cờ shared không đổi FAIL thành PASS bằng đủ key; audit marker/replay delta tách khỏi projection V12 |
| A5-UPGRADE | Fresh final và retained nonempty old schema có numeric/nonnumeric legacy lines+knowledge edges+othermodule protected data; append migrate/repeat không đổi historical checksum/applied_at/IDs. Ambiguous line legacy/FKbad giữ blocker/rollback, không auto sửa. Snapshot columns/PK/FKs/bytes/source1–12 trước/sau, không chỉ rowcount |
| A5-ATOMIC | Valid hashes/nonempty positive phải tới conversion thật (`da_ghi=true`), rồi causal negative sourcepreflight và fault giữa transaction riêng; each before→one action→after, reject0business delta/allowed audit riêng; valid retry ở boundary khác. Không đem preflight reject thay midtransaction rollback |
| A5-EXACT/C | Integer9007199254740993, explicit0/NULL/absent, offset/localUTC/time strings, Unicode/formula-like text: canonical serialization/tagged fields không mất precision/meaning; source schema/known dates không tự backdate. OptionC49table copy/hash và marker/history rules kiểm riêng, không lấy A5-19table làm hai-engine parity |

`tests/test_v13_doi_chieu.py` frozen:80–82 chỉ numeric1/2; PG typed mutations460–483 chỉ chieu/con_lai/known_at của3tables. Cần bổ sung các ca trên, không gọi tests cũ xanh là proof ba blind spots. `test_pg_bo_chuyen_schema10.py` dùng fake core_hash và chấp nhận source-error6: với preflight hiện có, không chứng minh converter đã chuyển các positive tables; phải có valid-core counterpart và nonempty observed outputs cho A5 acceptance.

Evidence private do root giữ: manifest/source hashes before/after; typed expected fixture manifest; case/criterion result và actual constraint name/SQLSTATE vs verifier diff counts; app-role positive và owner read-only full-domain observation riêng; source consistent snapshot/main+WAL+SHM tại exact boundary nếu có, business PK+fullrow semantic hashes, protected artifacts/file bytes, allowed audit events. Không chỉ hash `.sqlite` khi WAL tồn tại; không dump row/DSN/secrets vào report. Không chạy DROP/DELETE/TRUNCATE/reset/cleanup file/DB/role/temp; giữ retained failure và phân biệt FAIL/SETUP_ERROR/NOT_VERIFIED/NOT_RUN.

## 8. Bàn giao và giới hạn chốt gate

Sau root review, Claude nhận riêng scoped code package: converter source identity/order+tenant-aware fingerprints; append tenant guards; registry19table content coverage; targeted independent cases/upgrade report. Rebase accepted common M9/domain/period/owner rules trước sửa, không cạnh tranh file coder active. Chỉ báo A5 sẵn nghiệm thu khi từng criterion có nonempty expected/observed/evidence, converter replay/atomicity và preservation đạt trên final source hash; giữ log raw failed cases khi repair, không đổi expected theo output. Temporal/cutoff có gói kiểm riêng; A5 không chữa hoặc chứng nhận backtest sạch. Tất cả trong tài liệu này hiện là **technical candidate/NOT_RUN**, chưa có test/runtime/actual migration acceptance mới.

### Closure note R1 — chỉ amendment phạm vi guard, chưa nghiệm thu

Đối chiếu toàn `REVIEW-V13-A5-CONTRACT-01.md` SHA256 `dc2e26b7ab9b4db24a96911d0e340759df39c9a48d2587dae4df1338978998d0`: bỏ plain knowledge predecessor composite FK ở §4/§6.3, thay bằng trusted immutable typed converted ownership + conditional DB guard; giữ tenant-aware actual-parent verifier, converted positives/negatives và bổ sung no-bypass/native-preservation controls tại §4/§7. Parent composite unique/sidecar FK chỉ ràng buộc ownership rows, không mở policy native/global. Nếu phải thêm sidecar thì regenerate actual written/schema inventory và kiểm nonempty content/provenance/immutability/preservation của bảng mới; **19/42/49 là số baseline CRM06**, không bỏ table hỗ trợ mới khỏi coverage hoặc giữ numerator cũ để xanh. Chưa reserve migration number, chưa có implementation/handoff/runtime. **M9 vẫn STOP**; root phải chọn/review authoritative baseline và release A5 độc lập về sau, không dùng các câu “sau final M9” lịch sử để resume M9.
