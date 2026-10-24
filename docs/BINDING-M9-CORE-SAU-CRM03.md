# Binding M9 vào core sau CRM03

19/10/2026. **DOCS_ONLY / BOUND_TO_FROZEN_CRM03 / M9_NOT_IMPLEMENTED.** Tài liệu này cụ thể hóa điểm tái sử dụng và extension DDL/API để root giao Claude; không phải migration đã chạy, policy mới hoặc nghiệm thu M9. Lượt này chỉ đọc tài liệu/mã kỹ thuật frozen, không import/chạy product/test/SQL, đọc credential/row thật, gọi nguồn ngoài hay xóa file.

**Amendment R1–R4 trước handoff:** root đã thông qua hướng sửa trong `REVIEW-BINDING-M9-CORE-01.md`, SHA256 `080b32acecf7d569ec184d113fb6f388cb9bb61853418b692562a78c4d93fa24`. Bản binding trước sửa SHA256 `44e28e161b63280d7c7462eaec73fef1461b53b9e26d139b306e42575a68af9d` được copy/hash kiểm khớp tại `var/codex-dieu-phoi/m9-binding-before-r1r4-20261019-080802-fc6363d9`. §9 là contract bổ sung bắt buộc, không phải finding runtime CRM mới. Root đang điều phối bootstrap04/05 (handle32050 còn active theo cập nhật mới); schema/source M0001–12 vẫn pin frozen03, amendment hoàn toàn docs-only.

## 1. Baseline và ranh giới

- Proposal revision2 `THIET-KE-M9-TYPED-DEMO-33.md`, SHA256 **`e3e9704f5af808bc3c398a84ba85e3a80e0bc4b51c4042c1bda90fb73cfa9bf3`**, cùng `REVIEW-THIET-KE-M9-33.md` và `GIAO-VIEC-BRIDGE-KHOAN-VAY-M9-33.md` là đầu bài. Các bảng typed/field/grain trong revision2 giữ nguyên ý nghĩa; dưới đây giải quyết binding vào code thực.
- Core frozen: `var/codex-dieu-phoi/kiem-chung-20261018-101441/crm03-handoff-20261019-074754-971/frozen/`, manifest121 file `82e5e26806e05ef732536fcb0e474ab6ee96f646566e335e728da28921f47c3a`. Migration12 file `31f25277b5e08a0f54843191bce2b3e54126dc6770ad02ece310c8265fcac1e5`; `k2/crm.py` `7ac089c5df5501cf24aadf699caa1d02121c662b3d58fee6a561d916abd39336`; `ha_tang/postgres.py` `ffca2c38527ade742d12c5332ff29e3c54eae77f111362c7d5f9b0453bbdf6f8`.
- Review SQL/schema03 có73 criterion đạt riêng phần đã giao; root đang kiểm M1/launcher. Không biến frozen source hoặc kiểm schema thành nghiệm thu M1/launcher/GUI.
- Đã đọc toàn TL35. Giữ K1→K2→K3→K4→K5, một master/version/link/audit, mã Junsky chỉ nhận từ danh mục, không engine vay/lãi/tiền thứ hai. Google Sheets là nguồn ngoài: chỉ readonly API qua K1; tài khoản Google không có PostgreSQL. Phần mềm nội bộ chỉ qua `giao_tiep` view/hàm có phiên bản và role riêng, không cấp quyền bảng nghiệp vụ/bao_mat.
- Full M9 vẫn gồm C4a–d, ngắn/dài hạn, draw, trả gốc/lãi/phí, LC/bảo lãnh, L7/L8/L12 và lãi dự trả/M10. Các gap nguồn/policy dưới đây là công việc còn phải hoàn thiện, không bị loại khỏi toàn33.

## 2. Bảng và API hiện có: reuse chính xác

| Core thực trong frozen03 | Tái sử dụng | Extension bắt buộc trước M9 |
|---|---|---|
| `master.hop_dong` M0004 dòng301; đã có `loai=VAY`, mã/PN/đối tác/dự án/current PB | Một logical HĐ, ngân hàng là đối tác có ObjectID của PN | RLS hiện yêu cầu CRM với **mọi** HĐ; dispatch VAY→M9, giữ semantics các HĐ CRM hiện có. Không lấy default HIEU_LUC/VND làm approved/currency nguồn. Unique số HĐ trùng vẫn mở conflict mapping, không sửa số để lách |
| `master.hop_dong_phien_ban` M0004 dòng318 + M0010/11/12 | CHO_DUYET/DA_DUYET/TU_CHOI/THAY_THE, kiểm/duyệt/validity/thay_cho | Giữ lifecycle M12. Thêm domain-aware RLS/fingerprint/validation cho typed VAY; `CrmK2._phan_tich_pb` là parser doanh thu, không dùng làm validator vay |
| `master.lich_tra_no` M0004 dòng362 | Mở rộng chính bảng này | Hiện chỉ PB/ky/ngay/gốc/lãi/currency/text khế ước, UNIQUE(PB,ky), gốc/lãi NOT NULL default0; chưa có PN/draw/component/precision/provenance/RLS M9 |
| `kho.chung_tu SAO_KE`, proposal/dòng M1 | Một BANK logic, giữ ID/hash/proposal đã có | M9 chỉ thêm evidence/link/allocation; không nhận PhatSinh/draw/snapshot thành SAO_KE hoặc chạy bộ chiếu để tạo tiền M9 |
| `kho.lien_ket_chung_tu` + M10/11 | Một parent link, tombstone HUY, idempotency cũ | Chưa có child allocation/model/currency scale; trigger chỉ hiểu lịch thu CRM. Phải mở rộng chung, không bảng tiền riêng |
| `kho.viec_can_duyet`, `nhat_ky.su_kien`, `kho.lo_xuat/lo_xuat_dong`, `kho.khoa_ky` | K5/work/audit/file/kỳ chung | M9 dùng module/chu_trinh M9; binding workflow/period/protected lines phải thêm kiểm phù hợp, không suy tất cả thao tác đã được guard |
| `k2/quyen.nap_danh_tinh/kiem/pham_vi`; `_tx`, `_su_kien` trong CrmK2 | Một identity/quyền/context/audit | `HANH_DONG` hiện action CRM/M1, `_viec` hardcode chu_trinh M3. Tách vài helper chung nhận module/action có allowlist; không subclass CRM để duyệt VAY hoặc tạo hệ quyền riêng |
| `master.crm_*` M12 | Mẫu kiểm scope, không quyền dùng cho M9 | Wrapper hiện kiểm CRM. Giữ ACL đã đạt; thêm wrapper M9/common có PN/module đúng, không cấp lại internal/PUBLIC để M9 gọi thuận tiện |
| `store.write_immutable`, `primitives`, `xuat/excel.py` | Raw writer/canonical/hash/exact integer/date/XLSX | Dùng cùng file store và guard giữ file. Parser nguồn mới khai báo locale/precision riêng; không gọi writer/temp cleanup ngoài phạm vi giữ file |
| `LocalApp.crm_phien`, `_crm_db`, `mutation_lock`, shell DEMO | Cookie/server actor/error filter/shell chung | Phiên DEMO hiện tên CRM và lưu trong memory; mở menu M9 bằng session chung có scope hành động, không tạo actor từ body. Mutation lock trong process không thay lock PostgreSQL/concurrency liên process |

`master.nguon_tu_dong` đã có `SHEET_VAY_9`, nhưng PN NOT NULL và UNIQUE(PN,loai): dùng cho binding cấu hình nguồn của PN khi phù hợp, **không** coi nó là instance/snapshot/mapping registry đã hoàn chỉnh cho nhiều instance hoặc raw nhiều PN. Chưa có các bảng M0 snapshot/mapping/derivative, child allocation, currency-scale registry trong frozen03.

## 3. Extension M0/intake và provenance

Thêm ở migration mới các bảng đã review trong revision2: `giao_tiep.tep_tiep_nhan`, `kho.anh_chup_nguon`, `kho.ban_ghi_nguon`, `giao_tiep.tep_tach_phap_nhan`, `master.anh_xa_nguon`. Đây là common M0/K1; M9 là consumer đầu, không namespace/store riêng M9. Khóa source instance/profile là cấu hình server pin theo code/UI/header/precision contract, không URL hoặc credential do client truyền.

DDL/permission cụ thể cần giữ:

1. `kho.tep_goc.phap_nhan_id NOT NULL` và `hash UNIQUE` toàn bảng **không nới**. Thêm UNIQUE(PN,id) để derivative/typed reference dùng composite FK. Raw full chưa map/nhiều PN chỉ metadata integration + immutable object key; không PN giả, không gán theo PN của người đang mở màn hình.
2. Derivative PN có canonical envelope gồm instance, PN UUID, original raw hash, profile hash, mapping revision hash, selected locator/row hashes và exact rows của PN. Không timestamp fetch/random salt để tạo hash mới; hash derivative không được ghi thành hash nguyên bản. Owner PN/hash/bytes phải được kiểm khi dedup.
3. Snapshot unique `(instance,profile_sha256,raw_sha256)`; row unique `(snapshot,section,locator)`, không UNIQUE source_key làm mất hai row xung đột. Promote atomically graph hợp lệ trong một PN; partial/inconsistent/reject giữ raw/error nhưng0 mutation business. Một fetch mới có audit riêng, không tạo source revision chỉ vì fetch time.
4. COMPANY revision key không chứa target PN. Cần một lock identity bền vững theo `(instance,source_company_key)` và DB guard overlap approved intervals; có thể thêm common identity row tối thiểu để khóa trước khi duyệt mapping. Không chỉ service check rồi INSERT hai mapping A/B đồng thời. Nguồn không disambiguate→AMBIGUOUS_COMPANY; retarget sau promote→impact task, không chuyển master/link/lô hoặc sinh alias PN mới.
5. BANK/PROJECT/LOAN mapping dùng company source identity đã map + source value, composite FK đúng PN tới danh mục. Cùng mã ở hai instance/company thật vẫn độc lập. Lender `nganHang→ObjectID` khác tài khoản ngân hàng của doanh nghiệp/M1; không nối chúng bằng tên ngân hàng giống nhau.
6. Metadata bảng trong `giao_tiep` vẫn do core sở hữu. Không GRANT ALL/SELECT bảng raw cho role phần mềm nguồn chỉ vì schema mang tên giao_tiep. Integration service chỉ vào source instance được cấu hình; PN actor chỉ metadata/row/derivative đã map của PN. Không cấp download full snapshot theo quyền đọc một row.
7. Chưa có common currency/scale registry. Bổ sung M0 tối thiểu có code/scale/version/hash/căn cứ, hoặc binding cấu hình chung có invariant tương đương được root review; không registry private M9. VND0/USD2 trong DEMO chỉ fixture contract, không policy FX. Amount/currency/scale trên typed rows là cột, không chỉ JSON config. Registry không chứng minh encoding của BANK cụ thể: phải có immutable money proof theo R4 (§9), thiếu proof giữ blocked thay vì đoán scale từ registry hiện hành.

**Chốt kỹ thuật missing date từ root:** snapshot/candidate có received_at/known_at server và typed intake/evidence; **không** tạo `kho.chung_tu` nghiệp vụ nếu chưa có ngày nghiệp vụ thật, không thay bằng ngày import hoặc nới NOT NULL. `master.hop_dong.ngay_ky` nullable giữ unknown; validity có căn cứ thực có thể độc lập với ngày ký. `hop_dong_phien_ban.chung_tu_id` hiện nullable nên candidate/typed source reference không cần chứng từ giả; source row/derivative là provenance bắt buộc của M9. Khi bước nghiệp vụ/match/proposal cần chứng từ có ngày mà nguồn thiếu, tạo worktask bổ sung; dated source hợp lệ vẫn promote. Không tự lấy hạn trả/ngày giải ngân làm ngày ký HĐ; mỗi ngày giữ đúng vai trò field nguồn.

## 4. Typed M9 và compatibility lịch trả nợ

Thêm đúng các grain mới của revision2: `master.vay_dinh_danh_nguon`, `master.vay_phien_ban`, `master.khe_uoc_vay`, `master.khe_uoc_vay_phien_ban`, `master.lai_suat_vay`, `kho.su_kien_vay`, `kho.su_kien_vay_phan`.

- Alias unique `(instance,section,source_company_key,source_key)`, không có financing_kind/target PN. VayNganHan.id từ LC sang SHORT_TERM vẫn một alias/HĐ, PB mới chờ nếu facts đổi. `soHD/soNhanNo/soLC` là nhãn typed, không khóa nguồn hoặc lý do tạo BANK.
- Bảng mới promoted có PN NOT NULL, UNIQUE(PN,id), composite FK tới HĐ/PB/draw/source row/derivative đúng PN. Cặp `(PB,HD)` đã UNIQUE ở M11; cần thêm các unique PN/id và PN/PB/HD để FK mới không bỏ tenant. Child tới source row phải kiểm row thuộc snapshot và PN đã map đúng revision, không chỉ row UUID tồn tại.
- `vay_phien_ban` 1:1 PB chứa kind LONG_TERM/SHORT_TERM/LC/GUARANTEE, facts hạn mức/dư nợ/rate basis/nguyên tệ/VND riêng, precision/known_at/recorded_at. `hop_dong_phien_ban.tham_so` chỉ pin/profile/provenance bổ sung; không nhét draw/rate/schedule JSON làm master authoritative.
- Draw là identity + revision; source giải ngân là assertion, chưa là tiền. Rate numeric exact %/năm theo source unit; ambiguity maKheUoc→giữ chờ, không last-row-wins. Rate effective date khác known_at_server; view valid_on/known_cutoff áp cả hai.
- PhatSinh.id một logical source event, có GOC/LAI/PHI child; không ba BANK. Cumulative soDaTra chỉ balance assertion; không tách thành lần trả giả. Source Number UNPROVEN/LOST giữ chờ, Decimal không phục hồi số đã mất.

`master.lich_tra_no` phải ALTER thay vì tạo lịch song song:

| Thay đổi DDL mới | Compatibility phải giữ |
|---|---|
| Thêm `model_version` LEGACY/M9_TYPED; PN/HD suy được từ FK PB; thêm scope/draw/component/key/amount/currency_scale/source/basis/known-time/replacement như revision2 | Backfill PN/HD là metadata từ cha đã tồn tại; không suy số/precision/scope từ default0 |
| Bỏ UNIQUE(PB,ky) toàn bảng; tạo partial UNIQUE(PB,ky) cho LEGACY và partial UNIQUE(PB,nghia_vu_key) cho M9_TYPED | Giữ IDs, ky/ngay/so_khe_uoc/goc/lai/da_tra của row cũ; không tách cũ thành nhiều row |
| Cho goc_minor/lai_minor nullable, bỏ default0 cho đường M9; CHECK M9_TYPED→hai cột này NULL và dùng `cau_phan+amount_minor` | LEGACY giữ giá trị cũ cùng cách đọc cũ. Không có hai nguồn amount authoritative |
| `ky` cũ chỉ bắt buộc LEGACY; `ky_nguon`/period nullable đúng nguồn ở M9, date pair check khi có đủ | Không tự tạo kỳ/số0/ngày hiện tại để qua NOT NULL cũ |
| CHECK LOAN→draw NULL, DRAW→draw NOT NULL; FK draw đúng HD/PB/PN; replacement cùng logical obligation và không cycle | LOAN+DRAW overlap cần domain check dưới lock; unique key không tự chứng minh không double count |
| Eligible allocation/proposal yêu cầu amount/currency/scale/precision/basis đủ; zero rõ không tự là payable | Candidate NULL giữ NULL; trạng thái giữ chờ thiếu căn cứ, không biến thiếu thành số0 |
| RLS/immutability/audit cho lịch và mọi typed child; FK mới NO ACTION/RESTRICT | FK PB→lich_tra_no hiện ON DELETE CASCADE phải được review/thay ở migration mới nếu cần bảo vệ lịch sử; chỉ thêm FK mới không tự vô hiệu cascade cũ |

View compatibility phân nhánh model rõ. `da_tra_minor`/trạng thái M9 là derived từ allocation thực, không tăng do source PhatSinh hoặc cumulative assertion. LAI obligation/accrual và settlement dùng cùng logical obligation/financial event; basis/PB/rate revision là căn cứ có phiên bản, **không** tự thành identity/consumption key mới. R3 (§9) giữ old consumption xuyên revision và tách recognition consumption khỏi phân bổ tiền.

## 5. Domain dispatch và K5

Không gọi trực tiếp `CrmK2.duyet/kiem_truoc/_tao_phien_ban`: chúng dùng profile doanh thu, nguồn TRICH_6/BAN_HANG, khoản phải thu, dự án bắt buộc và chu_trinh M3.

Extension cụ thể:

1. RLS HĐ/PB/child phân VAY→M9 theo header typed, giữ nhánh CRM cũ. Thêm RLS trên lich_tra_no/typed source rows/mapping/allocation, cùng USING/WITH CHECK. Không dùng module từ payload/raw để đổi domain; giữ guard DB đang cấm đổi HD.loai/PN/identity. Module/model/subject owner và quyền mutation phải theo R1/R2 (§9), RLS theo PN/module riêng chưa đủ.
2. `kho.chung_tu` hiện HOP_DONG_TEP→CRM, còn lại→M1; proposal/dòng cũng chỉM1. Binding proposed thêm `module_nghiep_vu text` được server đặt/guard (SAO_KE luônM1; evidence/proposal nguồn M9 làM9), RLS dùng owner module typed. Backfill legacy đúng CASE hiện có để giữ quyền cũ, không suy từ ghi chú/client. Proposal/dòng theo module chủ của chứng từ và domain action; link tới M1 không đổi owner BANK sangM9. New M9 provenance không được giấu vào HOP_DONG_TEP rồi cấp CRM đại trà. Snapshot thiếu ngày vẫn ở intake như§3, không sửa schema ngày để né.
3. M12 internal fingerprint bao header+tham số/mapping doanh thu. M9 cần canonical wholegraph manifest/digest theo R2 (§9). Trigger kiểm/duyệt phải dispatch đúng domain, chạy **eligibility/V4/action validator độc lập với digest**; graph thiếu vẫn có thể có digest khớp, không được approved. Giữ CRM controls khi mở rộng common gate; không ghi thiếu sót tĩnh này thành lỗi CRM runtime đã tái hiện.
4. Lifecycle valid_to M12 giữ: chỉ CFO có V3 của phiên đóng một lần đúng predecessor/boundary của bản thay vừa duyệt, không mở lại. Common V4 new master/mapping và V3 facts giữ tách quyền. Source changes sau check invalidates check, không chỉ kiem_boi khác NULL.
5. Thêm allowlisted action M9_READ/INTAKE/MAP/CHECK/APPROVE/APPROVE_V4/MATCH/UNDO/EXPORT theo role/module/PN. MATCH cần cả M1 BANK và M9 target; viewer M9 chỉ đọc aggregate phạm vi HĐ của mình, không raw sao kê. Nguồn/integration không tự có CFO.
6. Tái dùng `_tx` LOCAL ID/login/business date, identity loader, audit, work/lô. Tách helper nhỏ dùng chung nhận module/chu_trinh/subject; không hệ quyền/K5/store mới. Server session/error sanitizer/mutation lock dùng lại, production login vẫn gate riêng.

## 6. Common BANK remaining và allocation

Core frozen chưa đủ để gọi link M9 an toàn: `CrmK2.lien_ket` chỉ nhận lịch thu, parse integer VND, type HOP_DONG_DOT_TIEN. `kho.lien_ket_kiem` M11 khóa HĐ khi lich_thu_id có giá trị, sau đó BANK; nhánh lich_thu_id NULL return sớm. Budget `tong_a` chỉ SUM parent có lich_thu_id. `CrmK2.danh_sach` lại SUM mọi parent active. Hai query này phải cùng bind một invariant trước khi thêm CHILD.

Thêm child **chung** `kho.lien_ket_phan_bo` theo revision2 và cột parent `allocation_model` DIRECT/CHILD (tên cuối allowlist, không suy từ sự hiện diện tình cờ của child). Parent mới M9 vẫn A=SAO_KE M1, B=chứng từ evidence đủ căn cứ/date của aggregate PN; thiếu evidence nghiệp vụ cần thiết thì preview/holding, không parent đã xác nhận giả. Gốc/lãi/phí target typed lich_tra_no; giải ngân target draw revision; LC/event evidence thiếu nghĩa vụ/template không là active allocation.

DDL/invariant cần triển khai cùng nhau:

- Composite FK PN/parent/target; exactly đúng target theo component, amount>0, cùng currency+scale với BANK/nghĩa vụ. Parent một aggregate/HĐ; thao tác nhiều HĐ có thể nhiều parent cùng operation receipt, không bỏ parent HĐ hoặc dùng JSON target để né FK.
- Parent CHILD amount là SUM child active effective, cập nhật/kiểm deferred trong cùng transaction; child chưa active không tiêu remaining. DIRECT không có child và góp parent một lần; cấm mixed. Không migrate CRM DIRECT thành0, không cộng parent+child đôi.
- Parent amount hiện immutable bởi trigger M11: phải thay trigger ở migration mới để hỗ trợ cache derived có kiểm, không đơn giản GRANT user sửa amount. Nếu cần owner helper, scope/ACL cố định; không dùng GUC client có thể set để bỏ guard. Child/parent HUY còn history, retry cũ trả tombstone.
- Thêm type M9 trong CHECK loai chung, index active target và model-specific unique. Index `lien_ket_cap_uq` hiện cặp A/B/type khi không lich_thu; giữ vai trò chống parent lặp, còn nhiều kỳ/phần nằm ở child. Không dùng NULL target để lách unique.
- Common money budget phải tính mọi allocation có hiệu lực cho cùng BANK/PN/currency, qua mọi module. Internal aggregate quyền owner kiểm full số, wrapper chỉ trả remaining/scope cần thiết sau kiểm M1/PN và target module; không trả chi tiết module khác hoặc dùng RLS-filtered sum thiếu dòng.
- Phân loại legacy non-CRM parent nào thực là phân bổ tiền phải có mapping type/meaning rõ. CRM type HOP_DONG_DOT_TIEN đã rõ. Generic evidence link có amount không tự thành tiền đã tiêu; nếu gặp legacy money link chưa phân loại thì giữ BANK chờ review, không mặc định free/0 để overallocate.
- Mọi CRM INSERT/link/undo và M9 allocation/undo cùng dùng common budget. Query UI `da_noi`, CRM trigger VUOT_TIEN_KHA_DUNG, M9 preview/confirm và audit lấy cùng effective amount; không sửa riêng M9 rồi để CRM vẫn bỏ qua CHILD.
- Idempotency common unique `(PN,module,operation,key)` + canonical request hash/receipt, hoặc namespace server vào global text key hiện có và lưu persistent receipt/hash. Check quyền trước replay, payload khác409; max120 ký tự hiện tại cần kiểm độ dài có namespace, không truncate làm collision. Không cache memory-only.

Tên contract chung để các gói M9/M2 dùng cùng một đường, cần root review trước coding:

| Contract proposed | Chữ ký/grain và điều kiện |
|---|---|
| `kho.bien_nhan_thao_tac` | UUID, PN/module/operation/client_key, request_sha256, result_json, actor/server-time, state; UNIQUE(PN,module,operation,client_key). Result JSON là receipt/audit, không master amount. Nhiều parent trong một confirm dùng cùng receipt; parent key phụ do server derive ổn định, không dùng cùng global text key cho nhiều parent |
| `kho.tien_da_phan_bo_noi_bo(bank_id uuid)` | Internal owner-only amount aggregate theo representation DIRECT/CHILD và currency/PN BANK. Không PUBLIC/app_web EXECUTE, không output row/details của module khác |
| `kho.tien_con_lai(bank_id uuid)` | Wrapper kiểm ID/login+M1+PN, trả amount_minor/currency/scale/version_digest/blocked_reason trong phạm vi được phép; ngoài quyền/không tồn tại không trả data. Legacy link chưa phân loại/precision/budget chưa đủ→remaining không eligible, không0 giả. M9/M2 preview gọi cùng wrapper sau kiểm quyền target |
| `kho.dich_phan_bo_tien` / `kho.dich_da_phan_bo_noi_bo` / `kho.dich_tien_con_lai` | Stable typed logical target và consumption xuyên PB/rate/basis revisions theo R3 (§9), ngoài ngân sách BANK. Revision FK cũ giữ nguyên; target UUID mới chỉ có khi financial identity thực sự mới |
| `k2/lien_ket_chung.py` | Một repository/service cho BANK remaining **và** logical target remaining, preview, confirm, undo và `khoa_lien_ket(conn,contract_ids,bank_ids,typed_targets)`. CRM delegate phần ngân sách chung; domain validator giữ riêng. Đây là tách/bổ sung core link hiện có, không engine hạch toán mới |

New CHILD effective amount chỉ tính child đã xác nhận khi parent đã xác nhận và chưa HUY; draft/preview không tiêu budget. DIRECT giữ semantics active lịch sử đã bind (`trang_thai<>'HUY'` ở core hiện có), không tự đổi CHO cũ thành ngân sách free. Direction THU/CHI cũng phải khớp operation/target có căn cứ; không chỉ so amount/currency hoặc cộng bù hai chiều.

M2 đã được điều phối dùng cùng parent/child/receipt/functions/lock helper trên; FK target M2 proposed `kho.mua_nghia_vu_phien_ban` sẽ được review trong binding M2 rồi thêm vào **cùng child** với exactly-one-target constraint, không tạo child/remaining khác. Chống trùng recognition/proposal là invariant khác money allocation, không lấy remaining tiền thay khóa đã ghi nhận công nợ/lãi. Không reserve số migration toàn cục cho M2 trước M9.

**Lock protocol bind vào thực tế:** CRM đã dùng HĐ→BANK→lịch và barrier race đã được review riêng. Mở rộng thành **HĐ UUID sorted → BANK UUID sorted → stable logical target UUID sorted → PB/nghĩa vụ/draw revision UUID sorted**, resolve đủ set trước lấy lock, rồi đọc lại version/basis/eligibility/cả hai ngân sách dưới lock. Pure graph mutation/check/approve không chạm BANK vẫn khóa HĐ trước rồi target/PB; nếu cần thêm HĐ/BANK ngoài set thì rollback/retry, không khóa ngược. Parent/child mutation, confirm/undo, approve/revision và reprojection có liên quan phải dùng cùng order; không giữ nhánh M9 lich_thu_id NULL đi BANK trước rồi mới khóa HĐ. `go_lien_ket` hiện chỉ khóa HĐ khi hủy, cần thêm BANK/common target/child lock để nhất quán ngân sách. R2 quy định đường mutation DB lấy parent lock trước child row, không trông vào mutex Python hoặc flag GUC client tự set.

Một BANK dùng chung CRM↔M9 phải có concurrency control winner/loser thực, số total không vượt eligible money; parent/child mismatch, reverse order và replay/undo sau revision đều có negative + positive oracle. Không tuyên bố gate này đã đạt từ concurrency CRM đơn domain.

## 7. API/service và file soát giao Claude

Thêm domain service M9 dùng repository chung; giữ route proposal của revision2, không đăng ký như route đang có:

| Route nhóm | Bind implementation cần có |
|---|---|
| `/api/m9/snapshots/demo`, snapshot detail, stage, sync | K1 common intake immutable bytes/profile/coverage, mapping source-company, atomic candidate graph. Google sync chỉ configured instance/ranges readonly sau gate; không load/ensureSheet hoặc arbitrary path/URL |
| `/api/m9/mappings/confirm` | M0 mapping revision + identity lock + K5 V4/V3, retarget impact; không client actor/PN/status/known_at |
| `/api/m9/versions/{id}/check,approve` | Cùng DB transition/eligibility/V4/action validator và wholegraph digest như SQL path R2; current/validity đổi cùng graph, không BANK/proposal112 mới |
| `/api/m9/loans`/detail | As-of valid time + known_cutoff, PN/M9 scoped; money string, precision/basis/source unknown hiển thị đúng; không estimated rate→lãi phải trả |
| `/api/m9/matches/preview,confirm`, undo | M1 existing BANK có immutable encoding proof + common BANK/logical-target remaining/receipt/locks; giữ consumption xuyên revision R3. Stale/version/payload conflict409, quyền403 theo shell error mapping; không HTTP200+chuỗi lỗi làm đạt |
| `/api/m9/proposals/prepare` | Reuse proposal/dòng/work/lô chung, event/obligation consumption key+policy version, không overwrite protected lines hoặc tạo dòng112 lần thứ hai; thiếu policy→holding |
| `/api/m9/file-soat` và download | `xuat/excel.table/workbook/to_bytes`, immutable bytes/hash + `kho.lo_xuat FILE_SOAT` moduleM9; kiểm quyền/hash khi tải/restart. Source int64 vượt15chữ số xuất string như CRM, cell không công thức injection |

M0/session/quyền/audit/lock/receipt được tách tối thiểu khỏi helper private CRM hoặc bổ sung dùng chung; không copy một engine tiền/kế toán khác. Launcher mở cùng shell/DB, không admin DSN trong browser/client, request dùng login thường. Kho thật SQLite và Junsky mức2 giữ gate.

## 8. Migration/acceptance và gap còn phải làm

**M0001–M0012 bất biến** gồm helper-generated statements, không chỉ file literal. DDL mới thêm sau12; số migration thực đặt khi handoff final vì root có thể còn sửa core. Giữ exact historical checksum/applied_at và audit known-oldM10, không thêm allowlist mismatch tùy tiện. New migration phải nâng fresh12+DB có CRM DIRECT/approved/future versions/legacy HUY, schedule legacy, proposal/lô/kỳ được bảo vệ; không reset/recreate.

Thứ tự phụ thuộc kỹ thuật: M0 intake/mapping/derivative+domain RLS/fingerprint → typed M9 và compatibility lịch → common allocation/remaining/lock+consumer CRM → workflow/UI/file/restart. Có thể chia migration nhưng không bật confirm CHILD khi CRM chưa đọc cùng ngân sách. Trước enabled phải preflight legacy rows/FK/domain; thiếu căn cứ giữ candidate/task, không backfill policy/amount/date/precision cho đẹp.

Chưa có bằng chứng independent cho mutation protected proposal/locked period ở mọi đường. `kho.chung_tu_kiem_trang_thai` kiểm khóa kỳ lúc duyệt và `de_xuat_dong_khoa_sau_xuat` chặn dòng sau xuất là điểm reuse; chưa bao toàn graph M9/link/undo/projection. Bổ sung gate theo đúng transition có căn cứ, không fake approved SQL hoặc disable trigger để vượt. Finding M1 atomicity/protected IDs root đang xử lý phải được nối vào handoff M9, không coi binding này giải quyết xong A5.

Phải chạy sau coder terminal: corpus19ca + RC2 LC→nhận nợ, RC3 DIRECT/CHILD/cross-module BANK/race/mismatch, RC4 company-overlap/retarget; role thường hai PN, precision/null/known-time, missing-date holding + dated positive, atomic reject0 business delta, protected period/lô/IDs, workbook bytes/cell, restart và GUI khi có tool. Không dùng adapter/schema hoặc một file soát để nghiệm thu toàn M9.

Các việc full M9 còn mở phải ghi task cụ thể: Google deployed profile/readonly/coverage; source chiTiet/LC/bảo lãnh chi tiết; bảng lãi kỳ được xác nhận/actual rate/day basis/cutoff/rounding; capitalization/FX/template chi tiết có version; current register/loại/hồ sơ C4d đầu tư. Dùng neutral typed DEMO và workflow holding cho phần làm được, không tự đặt policy hoặc coi lack-of-design là ngoài đích chương trình. Mỗi nhánh chỉ chuyển đạt theo yêu cầu→DDL/API→test→evidence→trạng thái của chính nhánh đó.

## 9. Amendment R1–R4: contract DB/consumption/proof bắt buộc

Các tên entrypoint mới dưới đây là binding giao code, chưa là hàm tồn tại. Thêm bằng migration sau12, giữ exact statement/checksum M0001–M0012 và audit lịch sử. Không sửa source trong lượt tài liệu này.

### R1 — owner module, model và subject không được đổi bằng SQL

- `module_nghiep_vu` trên chứng từ, module của work/proposal/lô/receipt và `allocation_model/link_purpose` trên parent link là **discriminator có guard DB**, không chỉ allowlist/RLS. INSERT phải kiểm owner từ source profile đã bind hoặc typed subject chain; SAO_KE luônM1, M9 evidence→M9. Actor có cả hai module cũng không được đổi M9→M1, đổi subject để đổi phạm vi hoặc tự gắn source envelope của domain khác.
- Giữ `hop_dong_kiem` cấm đổi HD.loai/PN/identity. Chặn UPDATE PN/module/model/source-owner/subject FK và child parent FK sau tạo hợp lệ. RLS `USING/WITH CHECK` không thay immutability; caller không tự chọn owner từ JSON/body hoặc truyền actor vào hàm để bypass.
- Work `tham_chieu_bang/id` phải resolve subject bằng **allowlist typed** và DB-check subject tồn tại, PN/module/loại việc khớp. Lô FILE_SOAT có typed subject/manifest references tới HĐ/PB cùng owner; lô proposal resolve qua `lo_xuat_dong→de_xuat→chung_tu`. `du_lieu.module` chỉ là metadata/copy đã kiểm, không nguồn quyền. Unknown subject kind fail closed, không dynamic SQL arbitrary table/path.
- `link_purpose` MONEY/EVIDENCE/LEGACY_UNCLASSIFIED gắn type/typed target bằng DB rule. MONEY mới dùng DIRECT/CHILD; EVIDENCE/quantity có amount tiềnNULL và không financial child. Legacy chưa rõ giữ blocked budget, không caller tự đổi thành EVIDENCE để giải phóng tiền. DIRECT→CHILD conversion mặc định cấm; nếu triển khai transition riêng phải có action được cấp, expected revision/receipt, lock common budget và kiểm nguyên totals/FK/refs/history trong một transaction. Không suy model từ số child hoặc dùng GUC để bỏ trigger.
- Entrypoint proposed `kho.kiem_chu_so_huu_noi_bo(subject_kind,subject_id)` và trigger owner validation dùng resolver allowlist, không PUBLIC EXECUTE. DML work/lô/child vẫn kiểm action của GUC ID/login thật, không coi definer current_user là caller. Không cho raw client sửa `result_json`/subject của receipt sau thành công.

### R2 — DB transition, eligibility, quyền action và wholegraph digest

Một digest khớp chứng minh nội dung được kiểm không đổi; **không** chứng minh graph đủ điều kiện. Cần cùng một contract SQL mà service cũng gọi:

| Entrypoint proposed | Điều kiện phải thực thi tại DB |
|---|---|
| `master.kiem_dieu_kien_hop_dong_noi_bo(pb_id,transition)` | Dispatch theo HD.loai immutable; VAY gọi M9 validator, domain CRM giữ control tương ứng. Kiểm actor/action/PN/module, đúng subject/V4 cần thiết tại thời điểm transition, source/profile/mapping/precision/basis, typed graph/parent/currency/scope/overlap/known-time; graph thiếu child/root typed không approved dù hash khớp |
| `master.m9_kiem_do_thi_noi_bo(pb_id,transition)` | Exactly1 typed vay revision đúng HĐ/PN/alias; children đúng PB/parent/source; draw/rate/lịch/event phần hợp lệ, không orphan/ambiguity/overlap chưa giải quyết. Transition CHECK và APPROVE đều kiểm điều kiện của mình; APPROVE đọc lại không chỉ tin blocker/digest lần CHECK |
| `master.m9_manifest_phien_ban_noi_bo(pb_id)` | Canonical manifest version rõ, owner-only đọc graph đầy đủ không bị RLS che. Digest canonical bytes và `kiem_manifest_version` được lưu cùng lần kiểm; không concat delimiter, NULL omission hoặc dùng hash một JSON chưa chuẩn hóa |
| `master.m9_ghi_nhap_noi_bo(...)` / wrapper mutation/check/approve được cấp | Đường ghi draft/transition lấy parent locks theo protocol trước child row, kiểm expected version/action và OLD+NEW parent. Không nhận actor/owner/approval/known_at do body tự đặt; service không có đường validator riêng yếu hơn SQL |

RLS chỉ chia phạm vi đọc/ghi PN/module; DB action gate còn phải phân WRITE_DRAFT/CHECK/APPROVE/APPROVE_V4/UNDO. Viewer M9 không được sửa draft chỉ vì có M9 và PN. INSERT child kiểm NEW parent; UPDATE kiểm cả OLD/NEW và cấm reparent/đổi identity; DELETE kiểm OLD parent và lịch sử, không hard-delete approved/referenced rows. Không chuyển row approved sang PB draft để vượt guard. Draft sửa có quyền phải invalidate lần kiểm cũ và có audit, nhưng check/approval/state/derived paid không tự tạo fact revision.

Để tránh row-trigger nhận child lock rồi mới chờ HĐ gây ngược order, đường app phải dùng DB wrapper mutation lấy HĐ/PB/target locks trước; **thu hẹp trực tiếp INSERT/UPDATE/DELETE của app trên typed child nếu không bảo đảm prelock bằng DB mechanism tương đương**. Direct SQL của login thường hoặc bị42501 trước mutation, hoặc đi cùng validator/trigger; không dựa client-set flag “đã khóa/đã kiểm”. Triggers vẫn bảo vệ OLD/NEW graph/state khi privileged wrapper ghi. Consumer CRM phải được đưa qua cùng action/eligibility/transition boundary có regression dương, không để service CRM một đường còn direct SQL một đường. Đây là yêu cầu thiết kế shared core, **chưa phải CRM bypass runtime được tái hiện**.

Manifest M9 bắt buộc bao: PN/HĐ/PB/alias/source identity; typed loan/draw identity+revision; mọi rate với effective date; lịch với logical target/scope/component/amount/currency/scale/period; event identities/parts; source row/derivative/reference hashes; immutable first-known time/provenance dùng cho eligibility; mapping/profile/precision/basis versions. Tập con sort theo stable typed key, field names/type tags/canonical version rõ; phân biệt NULL/0/empty và exact decimal strings. Audit/check/approval timestamps/status workflow, last-seen/fetch metadata và derived paid được tách khỏi fact digest để không tự làm stale; source status quyết định eligibility, ngày/số nguồn, source links và basis có ý nghĩa **không** bị bỏ khỏi digest. Child mutation và check/approve cùng khóa aggregate; không commit graph mới chen giữa fingerprint và approve.

### R3 — stable logical target và consumption xuyên revision

Một BANK remaining đúng chưa đủ: hai BANK khác nhau có thể trả cùng financial target lần2 nếu mỗi revision mở capacity mới. Bổ sung common **`kho.dich_phan_bo_tien`** để giữ stable target identity, không phải engine/bảng tiền M9 khác:

- DDL grain: `id uuid`, `phap_nhan_id`, `module_nghiep_vu`, `target_kind`, `hop_dong_id`, typed anchors `khe_uoc_id` hoặc source financial-event identity hoặc `nghia_vu_key`, `cau_phan`, `logical_key`, first-known/recorded time. UNIQUE `(PN,module,logical_key)` và UNIQUE(PN,id); CHECK target_kind xác định đúng tập typed FK/anchor, FK composite cùng PN/HĐ; không generic JSON target. Key lấy từ stable source alias/draw/event/obligation identity đã được xác minh, **không gồm PB/rate/basis revision, amount hoặc lần fetch**.
- `master.khe_uoc_vay.id` là draw identity; draw revision mới không đổi target giải ngân của cùng financial event. Nếu nguồn hỗ trợ nhiều financial events cho một draw, thêm logical event identity `(alias,source_event_key)` có revision riêng; không lấy ngày/số/soChungTu hay kind mới làm event identity. `kho.su_kien_vay` revision FK tới identity này, evidence PhatSinh không tự tạo target capacity khác cho cùng nghĩa vụ.
- Nghĩa vụ stable theo `(HĐ,scope/draw,nghia_vu_key,cau_phan)` được domain validator xác nhận; lịch/PB superseded tham chiếu cùng target identity. Child `kho.lien_ket_phan_bo` thêm `logical_target_id NOT NULL` cho model mới, đồng thời **giữ FK revision cũ** `lich_tra_no_id/khe_uoc_phien_ban_id/source event part` làm căn cứ. DB kiểm revision target thuộc đúng logical identity/PN/HĐ/component, không reparent allocation cũ sang row mới.
- CRM DIRECT cũ được resolve logical target từ HĐ+`khoa_nghia_vu` có căn cứ, giữ link/lịch ID gốc. `kho.dich_da_phan_bo_noi_bo(logical_target_id)` hợp nhất old DIRECT và child active của mọi revision **mỗi amount một lần**. `kho.dich_tien_con_lai(logical_target_id,valid_on,known_cutoff)` trả approved capacity/basis, consumed xuyên revision và eligible remaining sau kiểm domain/PN; không chỉ SUM theo revision UUID đang mở.
- Same logical identity và amount/rate/PB revision không đổi consumption. Giảm capacity dưới consumed→reject/holding/impact; tăng amount chỉ là candidate capacity bổ sung có căn cứ sau review, vẫn trừ old consumed. Basis/currency/scope change chưa chứng minh continuity→impact/reconcile/hold, **không** cấp logical_target mới hoặc zero paid để né. Không move link/PK/lô đã được bảo vệ; undo/rebind nếu được phép phải có audit/history và common locks/period gate, không delete/resurrect qua retry.
- Confirm kiểm **cả** BANK remaining theo immutable money proof và logical target remaining dưới lock HĐ→BANK→logical target→revision. Preview trả hai ngân sách và capacity/basis revision IDs/digests; confirm nhận expected target identity+revision nhưng không cho client quyết định identity mapping. Same-key retry/tombstone giữ receipt cũ, key mới cũng không mở thêm capacity cũ.
- Recognition consumption cho accrual/proposal giữ stable `(PN,logical financial event/obligation,accounting event kind,kỳ)`; basis revision pin làm căn cứ và chống stale, không là cách mở kỳ/event mới. Đổi căn cứ sau đã xuất mở adjustment/impact thay vì đổi key để ghi lại chi phí. Chỉ financial event/obligation **thực sự khác identity có chứng cứ** mới có target/consumption mới.

M2 phải dùng logical `mua_nghia_vu_id`+component/financial event cho cùng common target, giữ `mua_nghia_vu_phien_ban_id` làm FK basis; source-line renumber/basis revision không free capacity. Quantity sibling dùng cùng nguyên tắc stable line/UOM identity và history nhưng **không** cộng vào money remaining. Chuyển advance/evidence sang invoice có căn cứ nếu được phép là explicit audited rebind trong một transaction giữ BANK total, không cancel ngầm vì import revision.

### R4 — immutable money encoding proof của chính BANK

`kho.chung_tu.so_tien_minor/tien_te` hiện chưa có currency_scale/precision proof typed. Common currency registry mô tả đơn vị; không chứng minh amount của BANK lịch sử được encode theo đơn vị đó. Thêm common **`kho.chung_tu_tien_encoding`** (hoặc cột/reference tương đương có cùng invariant) trước khi eligible allocation:

- DDL tối thiểu: UUID, PN/BANK ID composite FK và unique theo BANK/proof revision; `encoding_kind=MINOR_INT64`, `currency_code`, `currency_scale`, `precision_status`, source profile/precision-contract ID/version/hash, immutable source artifact/field locator, normalized money digest gồm BANK identity+amount+currency+scale+direction, known_at/recorded_at, proof state. BANK trỏ proof eligible cụ thể; typed scale/proof ref cùng amount/currency/encoding là binding bất biến, không dùng registry “hiện tại” lúc query.
- Proof được ingestion/migration verifier kiểm từ nguồn/cấu hình encoding đã pin có căn cứ, DB guard chỉ cho đường được cấp tạo/đổi proof eligible. App/body không tự khai PROVEN/scale; không convert module/model hoặc sửa tiền/currency để làm proof khớp. Proof được cải thiện bằng evidence revision/audit nhưng không rewrite amount/encoding cũ đã được bảo vệ; đổi nghĩa tài chính cần correction có căn cứ.
- UNKNOWN nghĩa chưa có eligible binding; verifier có thể gắn proof có chứng cứ lần đầu qua transition riêng dưới lock/audit. Sau khi đã pin, bổ sung evidence chỉ được giữ cùng amount/currency/scale/encoding và normalized money digest; không tự retarget sang contract mới của registry. Pointer/evidence history được giữ, không user UPDATE proof_ref để giải phóng hoặc đổi nghĩa số đã phân bổ.
- Backfill chỉ khi chứng minh encoding của BANK đó: VND0 có source contract xác nhận minor VND, USD2 có source contract riêng. Chỉ thấy `tien_te='VND'`/số nguyên, registry scale0 hoặc amount dưới2^53 không đủ. UNKNOWN/UNPROVEN/LOST/mismatch giữ raw/worktask và `tien_con_lai` không trả numeric eligible remaining; không default0/VND/scale0 hoặc suy lại chữ số mất.
- Child/target currency-scale CHECK so với proof pinned của BANK và capacity basis của target. Registry/profile đổi sau này không đổi proof/paid/remaining của BANK cũ. Chưa có chính sách FX thì khác currency/scale/basis giữ chờ, không quy đổi để khớp. Giữ nguồn amount nguyên tệ và VND độc lập như revision2, không thêm account/FX/capitalization policy ở amendment.

### Ca nghiệm thu bổ sung R1–R4

| Nhóm | Positive control và negative/temporal/race phải chứng minh sau coding |
|---|---|
| R1 discriminator | Tạo đúng domain/model bằng workflow thật đạt. SQL thường đổi VAY→CRM, M9→M1 trên chứng từ/work/lô, DIRECT→CHILD rỗng, child→parent khác cùngPN đều bị từ chối;0 business delta, visibility/budget không đổi |
| R2 action/eligibility | Viewer sửa draft, chèn approved PB/child, chuyển approved child vào draft, graph thiếu typed root/precision/amount/basis hoặc LOAN/DRAW overlap, V4 chưa xong dù digest khớp đều bị DB chặn. KT/CFO đúng quyền+đủ graph đạt; service và direct SQL/function path cùng gate |
| R2 manifest/concurrency | Sau check đổi riêng rate/amount/precision/mapping/basis/source link→stale approval bị chặn; approved/referenced child immutable. Child-vs-approve có observer lock và positive winner: không approved graph ngoài digest, không timeout/deadlock được tính thành pass |
| R3 crossrevision | Draw đã nối tiền→repeat/PB/rate/basis revision→BANK khác và same-BANK retry không mở lại capacity. Nghĩa vụ superseded cùng key trừ old active; decrease dưới consumed hold, increase có review vẫn giữ paid; old FK/PK/lô không move. New financial identity có căn cứ là positive không bị chặn nhầm; undo/tombstone/correction có audit đúng |
| R3 common consumer | CRM DIRECT+M9 CHILD cùng BANK/logical target kiểm mỗi amount một lần; hai race order winner/loser thực; parent/child mismatch reject. M2 advance/invoice rebind và quantity source-line revision giữ consumption tương ứng, không hai đường money remaining |
| R4 BANK proof | VND0 proven và USD2 proven match đúng amount/scale; scale mismatch, source precision unknown/lost, proof/amount/currency tamper và legacy chưa xác minh bị blocked, không numeric remaining giả. Đổi registry không thay BANK encoding đã pin; giữ exact int64/string qua API/file |

Không chạy các ca này trong lượt amendment. Tài liệu sửa điều kiện handoff/acceptance, không cộng số test, không khẳng định runtime bypass CRM hoặc kết nối source/M9 đã triển khai.
