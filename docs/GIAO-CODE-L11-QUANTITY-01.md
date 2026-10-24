# R16 L11 — handoff độc lập v5: hai lượng native, hai quantity pools

**ROOT_REVIEWED_CODE_ONLY_RELEASE / L11_QUANTITY_CODE_ONLY01.** Claude được viết đúng15 files trong §9. Không được execute/import/test/SQL/HTTP/GUI; root chạy kiểm độc lập sau actual terminal, freeze và review.

## Root release binding — actual evidence, 2026-10-19

- R15 repair03 accepted finite DEMO dependency, không full M2/M5/L11/33 acceptance. Root acceptance SHA `502c48f9d46f08d53b08544ee8842c0917279e66620fd18934ad91b4b2b53eba`; actual terminal receipt SHA `8d2f9e7a9651ac2bafa0d5d416153c798df4aebd9475a3f080e169d1ff935af2`, exec handle46081/chunk162cc8/exit0/same Claude session52783bcd-6e1d-46d2-9e45-3c527aa43e5b.
- Actual root checks: migration7/7, service18/18, HTTP3/3, M5 service36/36, independent defects20/20, selected15groups; zero skip in native selected suites. Không coi coder report là bằng chứng; GUI02 finite only, P09–14/full module chưa nghiệm thu.
- Accepted source249 SHA `8002cbe331cb222110d7ed6beef7e2f9a7e2157128bb31abde796834a0baa7c0`; actual data-only staging receipt SHA `f341de1576550a60cdc1f0f76d017305314ab1d03a359fc899b6c56edbd94a28`. Không có approval seed hoặc product/SQL/test trong staging.
- Frozen initial source269 SHA `57b5b7bcbc49319565bd010003c74333cba98455c0fa65097235d1a3dd1bcbab`; immutable public fixture20 manifest SHA `227980804428af52fb153b9c15a9142e5b261f2b50bbd4b8e873ba421b3081dd`. Existing10 write targets, new4source + newreport; protected259, finalsource273.
- Public cases `docs/L11-QUANTITY-CASES-01.json`, SHA `6ab9e6603fc7d3d067f4fd557630a11e84b91cfb4eb30e7c5e077e0a11c1f66f`. Cases/generated migration checksums chỉ là test oracles, service không đọc docs/cases/private paths.
- Reuse existing COMMON/shared MASTER/M2 pure readers/M5 source reader and quantity services. All old fixture hashes/actor revocations preserved; no file deletion, no M9 tracking changes.

## 1. Baseline, phạm vi và inputs

Final R15 repair03: source manifest249 `8002cbe331cb222110d7ed6beef7e2f9a7e2157128bb31abde796834a0baa7c0`; migration source `626619b8a9b73261c6370119d39ac8eece92e8b512e45d26eaef76d6a7130989`; HoaDon service `176d6d23bf79279205d06a20a90af7d4b2d096e7e0e367352f6713beb653f075`. Root-generated M15: **91 statements**, SQL checksum `5f77b6acf51fab70a248a18c109a3678925efd285e95805596c1cb8f1de82a68`. Giữ nguyên toàn bộ literal/generated SQL, ordering/checksums1–15; append `M0016_L11_QUANTITY`, mọi CREATE OR REPLACE cần thiết nằm trong16. Không đổi historical M9 definition/history/grants, không install full-M9.

M5 binding `docs/BINDING-M5-CORE-SAU-CRM03.md` SHA`7de60be44fe301d043a70aa2b582572f5d96d40f9444238f10a2a50acd4bcc5c` và M2 binding `docs/BINDING-M2-CORE-SAU-CRM03.md` SHA`001aefc2d7cb8e9d0b6017325c465c2f536962b56331d3ef08c44b3388c0eea2` giữ mọi quy tắc ngoài một grain clarification trong §3 dưới đây. Quantity-only: không financial/stock/recognition/BANK/331/M9/sourceapp/Google/Junsky; không delete/drop/reset/cleanup. Reuse COMMON artifacts/raw/closed stages/receipts, shared MASTER và existing source readers/services, không engine/registry cạnh tranh.

Root stage đúng **20 files** trong `tests/fixtures/l11_quantity/`, không fixture21 cho evidence profile. Sau stage:249+20=**269 source inventory**; thêm4 source/tests ở §9 thành **273**, report docs ngoài inventory. Fixture manifest SHA và poststage source269 SHA được bind tại release header bên dưới. Chỉ nạp explicit public paths dưới folder này, không private paths hoặc duyệt upstream manifest:

- `declarations.json`, `manifest.json` (root-filtered membership).
- `shared-unit-definitions-v2.json`, `candidate-line-facts-r16-v2.json`, `native/new-thung-one.xml`.
- `proofs/goods-equivalence-A-v2.json`, `proofs/cai-crossunit-1to1-v2.json`, `proofs/thung-native-unit-and-encoding-v2.json`, `proofs/thung-to-cai-12to1-v2.json`.
- `warehouse_split/configuration/admission-proposal.json`, `warehouse_split/configuration/source-profile.json`, `warehouse_split/configuration/source-scope.json`, `warehouse_split/context/reader-context.json`, `warehouse_split/declarations/measurement-declaration.json`, `warehouse_split/history/repository-history-empty.json`, `warehouse_split/master/master-raw.json`, `warehouse_split/native/warehouse-split-six.json`, `warehouse_split/upstream-manifest.json`.
- `unit-declarations/m5-cai-unit-declaration.json`, `unit-declarations/thung-unit-declaration.json`.

Upstream manifest chỉ opaque hash provenance, không resolve/load inventory hoặc private paths bên trong. Context/history/cases không là current DB authority. Raw proposal statuses/approved:false/DBIDsNULL không là approval; server không seed DA_XAC_NHAN. Profile constant ở §2 là literal trong public handoff để implement trong `l11_demo.py`; runtime không parse docs/oracles.

Inputs: existing G01 invoice TEXT10 CAI/itemDEMO_ITEM_A, PN_A/MUA_VAO; existing K01 warehouse TEXT8 CAI/itemHH_DEMO_A vẫn8. Hai CAI definitions khác nhau, không auto1:1 theo label. New THUNG XML SHA`65ce193e68053e59d5b18e4a7fa6879fa31499fbc2cd1ca5d138a95a30883a7a`/480bytes: qty1 THUNG, number009001, actual date/currency; không bịa money0. Pure CAI-only reader/profile/normalizedNULL của THUNG giữ nguyên; L11 encoding là authority riêng.

New split native SHA`adfd623e4f4432272646ef925a5db0d5d3fd209fb50e870549d28223b4af009b`/875bytes; MASTER SHA`3c67491146ef8025aa6b07a8092000fe400be6f3ed7f51671e4c06c35e1c7665`/441bytes. DEMO_KHO_A/KHO_DEMO, SoPhieuNK20261019006, IDs`ID_1792382400001`,`ID_1792382400002`, TEXT6 CAI mỗi dòng, hai stable logical roots. New scope/master/measurement/history phải actual configure→capture→sourceaccept; history EXPLICIT_EMPTY/acceptedNULL/seen[] không sửa thành approved. Raw producer Đãduyệt là synthetic claim. Full1THUNG↔6+6 chỉ eligible sau actual admissions/proof confirmation, không relabel K01 8→12.

## 2. Evidence profile, scope và declaration compatibility

Dedicated instance `DEMO_L11_EVIDENCE_INSTANCE_A`; profile `DEMO_L11_QUANTITY_EVIDENCE_JSON_V1`; scope `DEMO_L11_EVIDENCE_SCOPE_A`. DB scope typed PN_DEMO_A, scope_kind=`L11_EVIDENCE_SET`, sections=`['L11_PROOF_JSON']`; MaKho/SoPhieu/companykeys NULL, không giả warehouse. Thêm typed scope PN column/admission nếu cần trong16; resolve current PN từ scope, không browser. Old instances vẫn một profile, old profile payload/media guards không nới.

Canonical profile payload SHA256 **`3cc2d403d3ae7986c75fd21767763c2fe23678d59290618225463c870e3d9251`**: UTF8, recursively sorted object keys, no whitespace, array order retained. Đây là root-approved technical DEMO declaration, không production verification hay CFO approval; source_code_sha chưa được bịa.

```json
{"artifact_roles":[{"media_type":"application/json","required":true,"role":"NATIVE"}],"capture_contract":"m0-capture/v1","contract":"m0-source-profile/v1","coverage_values":["COMPLETE_INPUT","PARTIAL_INPUT","UNKNOWN"],"encoding":"JSON_UTF8","module":"M5","native_detail_shape":"l11-quantity-proof-json/v1","proof_references":[{"byte_length":3927,"evidence_revision":2,"kind":"GOODS_EQUIVALENCE","raw_sha256":"aef5de224e04fd64ef67a272689f72a041097ae93c5160393ef2297640d2bb4f","reference_id":"DEMO_M2_M5_GOODS_EQ_A_V1"},{"byte_length":2968,"evidence_revision":2,"kind":"CROSS_NATIVE_RATIO","raw_sha256":"bf4d47208740e16ad6cb59bdade9aae015bc8e5031fa797371eadf29e55cc319","reference_id":"DEMO_M2_M5_CAI_EQ_A_V1"},{"byte_length":1722,"evidence_revision":2,"kind":"NATIVE_ENCODING","raw_sha256":"a860439cf802e9b21ea1fabc24c1d9d6b79d8ca7a0402fba4bd62416a979b60f","reference_id":"DEMO_R16_THUNG_NATIVE_ENCODING_V1"},{"byte_length":3038,"evidence_revision":2,"kind":"CROSS_NATIVE_RATIO","raw_sha256":"c6e2fa840efd2644816192c8b753e68ebad241987cf69623f09022a665e4181b","reference_id":"DEMO_NEW_THUNG12CAI_PROOF_V1"}],"purpose":"L11_PROOF","verification":"SYNTHETIC_DEMO_ONLY_NOT_PRODUCTION_VERIFIED"}
```

`COMPLETE_INPUT` chỉ toàn bộ **một proof input được gửi**, không toàn bộ proof inventory/period/production coverage. Strict UTF8 JSON, đúng bốn configured references/raw hashes/lengths/revision2 trong payload; kind derive từ configured binding, không đòi raw JSON có top-level kind. GOODS_EQUIVALENCE, CROSS_NATIVE_RATIO, NATIVE_ENCODING, CROSS_NATIVE_RATIO là bốn consumers. Unsupported/contradictory→HOLD/denial. Không nhận browser factor/kind/approved/PN/owner/PROVEN làm authority. Source metadata approved:false hoặc NULL IDs vẫn raw evidence, không bị diễn giải thành approval hoặc làm lý do bỏ kiểm shape.

Hai declaration docs dùng full R15 tuple/semantic validator; không dùng raw bundle cũ như declaration document mới:

| Unit | Document raw SHA / bytes | Canonical definition SHA | Declaration locator |
|---|---|---|---|
| DEMO_UNIT_CAI_A | `4890796ad2d8799506e831e9256723a14c964a100add7f2dc4c206a2e4051d50` /2522 | `206b26eac399c240adf71f26c8daec5de13f8be45b4badc64523c7ae76b3977f` | `/unit/payload` |
| DEMO_M2_UNIT_THUNG_R16_V1 | `881992f011460e37b3eff58d0c9cadeb570b584ab1b7d4d21ee348e8730a8157` /2544 | `774d51c9017314e156e19729b64870d55a34187628fb6d21e2080ee90b83bdb1` | `/unit/payload` |

Common artifact + `master.tai_lieu_khai_bao_don_vi` giữ exact docbytes/hash/length; registry document basis riêng **`urn:demo:l11:unitdecl:<document_raw_sha256>`**. Full unit tuple: reference, definition SHA, canonicalpayload, unit source_basis_ref, declared scope, declaration_ref/rawSHA/locator, supporting sourceinstance/profile/refSHA/rawSHA/locator. Top document source/profile và parent `definition_payload_sha256,payload,source_basis_ref` phải khớp actual document/context, không chỉ self-H.

Parent unit basis giữ nguyên: CAI `urn:demo:l11:sourcebasis:m5cai:3a806526917dac322ee9ba4c6f7ea5ed88e02b780ea282c0300465e980e16801`; THUNG `urn:demo:l11:sourcebasis:thung:65ce193e68053e59d5b18e4a7fa6879fa31499fbc2cd1ca5d138a95a30883a7a`. Origin bundle SHA`2a3c5b3323c1bf46020aba8807640070c12b32b20344da55badc587319cd4504`, payloads/URN/proofbytes không đổi.

CAI support MASTER3a8065…/548bytes: actual JSONpointer `/DM_HangHoa/0/DVT_Goc`, item pointer `/DM_HangHoa/0/MaHang`=HH_DEMO_A; descriptive `/DM_HangHoa/MaHang=HH_DEMO_A/DVT_Goc` chỉ selector provenance. THUNG support XML65ce…/480bytes: `/HDon/DLHDon/NDHDon/DSHHDVu/HHDVu[1]/DVTinh` và itemMHHDVu. Supporting context CAI=DEMO_KHO_A/profile`urn:demo:m5:source-profile:f05eee570c7c8861b219ca97`/SHA`b8735806b72701dc6a4a54c3b3772e70326efbc812543b1c5969576be3eedb41`; THUNG=DEMO_M2_XML_INSTANCE_A/profileDEMO_M2_XML_QD1271_FIELDS_V1/SHA`7e17794151a7711317da3d9ab00d96427d2b1e1c688b132feb78ce540bb2188d`.

MASTER3a8… là evidentiary source của definition CAI. Current split MASTER3c6… được kiểm độc lập bằng current measurement/goods binding và raw fields; không ép current deliverySHA==declarationSHA/supportSHA, không tạo unit mới mỗi delivery. Identity encoding CAI chỉ sau verified same canonical definition/context, không theo label. Four proof files raw-source-bound gồm explicit domain và five supporting bindings (G01,THUNG,K01,hai split6); không tự mở rộng cho artifact/item/context chưa liệt kê.

## 3. Migration16, typed graph và allocation grain

Bốn bảng quantity, dùng shared MASTER unit/goods mapping:

| Bảng | Bất biến/keys chính |
|---|---|
| `kho.dich_so_luong` | UUID/PN/ownerM2\|M5/pool_kindL11; exactly-one typed invoice hoặc phiếu logical-root FK; shared unit FK/EXACT_DECIMAL_38_12/immutable basis; UNIQUE(PN,pool_kind,typed logical root). Pool identity không gồm PB/profile/UOM/factor/capacity/operationkey; composite keys cho samePN/root/owner. |
| `kho.bang_chung_quy_doi_luong` | PN/ref/revision; from/to unit-definition FKs, approved goods/context mapping FK; reduced positive numerator/denominator numeric38,0; actual COMMON artifact/source/field/profile/basis/rawfact digest; immutable facts, guarded confirmation/revocation/audit. Conflicting active ratio cùng definitions/context/overlap→HOLD. |
| `kho.ma_hoa_luong_nguon` | Exactly-one typed M2 PB-line bridge hoặc M5 PB-line; samePN/sourceidentity/PB/logical/core/locator/profile; raw quantity text/native quantity/unit/precision declaration; approved native→pool proof và exact capacity/basis/state. UNIQUE(PN,typed PB-line,measurement basis revision); composite pool/root FKs. Old amounts không diễn giải lại bằng current registry. |
| `kho.lien_ket_dong` | HOA_DON_PHIEU_KHO child; parent, full M2/M5 identity/PB/logical/bridge/core/line/encoding/pool/unit/crossproof FKs, bốn quantities numeric38,12 positive; CHO/DA_KHOP/HUY, CO_HIEU_LUC/CAN_SOAT, receipt/actor/reason/time/supersedes; facts bất biến khi confirmed/held. |

Existing `kho.lien_ket_chung_tu` parent typeHD_PHIEU_KHO: A=HD_MUA/M2 PB, B=PHIEU_KHO/M5 PB, samePN; new immutable ownerM5/purposeEVIDENCE/typed subject logical phiếu. so_tien_khop_minor=NULL; không money child `lien_ket_phan_bo`, quantity trong amount/resultJSON hoặc currency-as-UOM. Reuse canonical immutable document-snapshot-pair parent, UNIQUE/locks và full composite graph; không duplicate model/M9 DDL hay rewrite oldparents.

Root grain clarification chỉ supersede accepted M5 binding §4 line86 active(parent,pair,basis) uniqueness: **one confirm receipt/one typed pair→one immutable allocationchild UUID**, UNIQUE(PN,confirmation_receipt_id). Legitimate4+4 cùngpair/basis qua hai keys có hai children/một parent khi both budgets đủ. Samekey/H cùngchild; differentH409; không UPDATE oldqty hoặc resurrect tombstone. Bindingfile/hash không sửa; stable pools/fullSUM/held/constraints khác giữ.

New tables/functions/defaultACL revoke inherited/public/broad grants theo branch, exact actual table-owner INVOKER guards where appropriate + explicit currentactor/caps trong consumer. App không prefill receipt/parent/child/proof/encoding hoặc retarget stage/PN/purpose/facts. Replace/condition mọi old permissive parent RLS (M1/legacyUSINGtrue) đối với new quantity branch: current BOTH M2_READ+M5_READ trước projection có invoice/crossrefs. Thêm M5 policy OR riêng không đủ. Generic legacy paths không giả oldrow trỏ newM2/M5 graph; preserve genuine oldCRM/M1 (kể cả oldHD_PHIEU_KHO), không global revoke/retag. Generic parent HUY không free child SUM hoặc bypass BOTH V2/lifecycle.

## 4. Exact arithmetic và reservations

Ba căn cứ riêng: approved goods equivalence, native→own-pool encoding mỗi phía, cross-native equivalence. Một proof không tự chứng minh precision/capacity phía kia. For native strings a,b: **a×cross_num=b×cross_den**; derive invoice_pool và warehouse_pool độc lập theo own encodings. Raw ratio phải positive integer **strings≤38digits**, lexical/zero/gcd trước cast numeric38,0; reject1.5/Number/float, không rounding. Native amounts independently exact38,12 positive, representability/crossmultiplication trước cast; không abs/defaultfactor1/NULL→0/newpoolunit để hợp thức1/12 không biểu diễn được.

Stable capacity lấy từ current eligible encoding. Full-domain SUM từng pool qua mọi PB/profile/UOM/proof revision/key: DA_KHOP+CO_HIEU_LUC=confirmed; DA_KHOP+CAN_SOAT=held; HUY=0. used=confirmed+held mỗichild một lần; held6 không count12. CHO không claimed consumption. No remaining table/cache; internal owner-only `kho.luong_da_khop_noi_bo(pool)`, scoped `kho.luong_con_lai(pool)` trả capacity/confirmed/held/unit/proofs và available chỉ khi exact eligible basis hiện hành; otherwise blocked/availableNULL, không clamp0/free/retarget. Không SUM nativeA như budgetB.

## 5. Authorization, closure locks và lifecycle

Hai actors mới additive, old8M2/8M5/grants/revocations không đổi: `MO_PHONG_L11_LINK_A` current BOTH READ+V2 hai module và actual **M5_FILE_SOAT**; `MO_PHONG_L11_PROOF_CFO_A` BOTH READ+V4 hai module, INTAKE/READ_SOURCE/SOURCE_MAP **chỉ dedicated evidence instance/profile/scope PN_A**, không oldsourcecaps. Bổ sung selectors/admission đúng hai login/currentcaps, không all-MO_PHONG prefix hoặc blanket CFO grant. Current identity/PN/caps trước lookup/replay/rawread; stageID không bearer authority.

Same configured privileged connection/transaction: current actor/caps→operation namespace/key/H/replay→precollect BOTH-side/toàn batch logical-root/affected-child closure→canonical shared root order→sorted poolUUIDs→fixed observation/content/route/map/encoding/proof/child roworder→effects/stageconsume/receipt. Pre-root identity/subject gates có sharedorder; không xin namespace/subject muộn sau pools. No money lock helpers. Re-read closure dưới khóa; có root/pool/dependency mới thì rollback/retry wholemutation trước effects, không append out-of-order locks. Không Python-only lock khi app gọi trực tiếp DBdefiner; bypassDML chặn/DB-verifiedprotocol, không arbitraryGUC/member-of-owner bypass.

Final SQL entrypoints cần extend trong16: M5 m5_khoa_phieu4073/tieu_thu4144/giu_cho_anh_huong4270/xem_xet4361/anh_xa_v44430; M2 tieu_thu5912/xem_xet6100/mapping_dong6146/route6287/mapping_cong_ty6359; shared mapping guard5386; M5 FILE4598/4669. Mapping row locks hiện có không thay whole affected roots/pools. Source/map/review/route transitions collect peers trước tuple mutation; batch không lock theo XML/ZIP order. Preflight không giữ partial lockprefix trái sharedorder.

Confirm current BOTH V2, exactsamePNpair, accepted/eligible invoice+currentapprovedKHOroute, warehouseeligibility/history, goods/nativeencoding/crossproof/period/protection và both budgets. Proof/state reads cần lock xung đột non-key UPDATE (FOR SHARE, không chỉ KEY SHARE). Revoker chờ lock rồi đọc lại allocations, mở rộngclosure thì restart trước revoke; rowtrigger xinrootsauDML không đủ.

A,A/samecontentZIP chỉ observations/OP CAS; PB/core/logical/semanticroute/proofs/pools/children giữ. A→B/reversed/ineligible/capacityreduction/route-away-KHO/profile-map-unit-proof change/revoke **synchronous CAN_SOAT** mọi affectedlivechildren, giữ oldnative/poolamounts/proof/pool/parent/childIDs. Sourceineligible availableNULL/blocked, heldreservation không giảm. B→A/acceptsource không tự reactivate; permissionrevoke không autoHUY. Human handling cần V2 riêng.

Automatic HOLD during oldsource INTAKE cùng trusted source-ownerTX dựa owncurrentintakecap, **không đòi human BOTH V2**; deriveaffectedclosure actualstage/sourcegraph, không callerpeerIDs, không exposethirdpartyinvoice/children cho sourceactor. Raw-only/candidate/periodHOLDsemantics giữ; typed/pointer/impact/finalreceipt commit cùngholds.

Undo current BOTH V2+owner/protection/period/reason/sameprotocol, HUY+tombstone+audit release **chỉ stored old pool amounts** đúngchild exactlyonce. Held/ineligiblesource vẫnundođược; không đòi confirmeligibility/currentcapacity/liveproof. Partial/missing/revoked không auto-undo. Samekey/H resolvechild rồi currentCAN_SOAT/HUY/tombstone, không historicalDA_KHOP/resurrection; changedH409. Genericparentstate không giấu/free consumption.

## 6. Actual API và proof-to-link buttons

Reuse COMMON strictpurpose/profile/role admission; thêm closed L11_PROOF stage purpose, không JSONquaXMLconsumer/freeJSONbusiness authority. Codes400shape/403scope/409stale/overproof/period giữ legacyclassifier; currentrights trước lookup/replay, wrong-H/stale0newstage/blob/businessdelta.

| Endpoint | Body và hành vi |
|---|---|
| POST `/api/m5/l11/proof/nhan` | source_instance,scope_ref,coverage,reported_errors,client_key và exactly-one native_base64 hoặc whitelistedfixture_ref; không filesystempath/URL. Resolve profile/PN/kind server, actualbytes/hash/length→rawcandidate+receipt trong closed sameownerTX. |
| GET `/api/m5/l11/proof` | BOTH READ, refs/revisions/state/facts/issues/expected_graph/actions theo currentcaps. LINK chỉ approved scopedmetadata; rawcandidate/rawbytes cần relevantREAD_SOURCE. |
| POST `/api/m5/l11/proof/xac-nhan` / `/huy` | candidate_id / proof_id,expected_graph,client_key,reason **only**; actualCFO BOTH V4+relevantsourcecap trước lookup/replay. Derive rawboundfacts; immutablefacts+confirmation/revocation receipt/audit, revoke atomicholdchildren; replay currentstate. |
| POST `/api/m5/l11/ma-hoa` | typedsourcebridge/line/proofrefs+expected_graph/client_key/reason, BOTH V4; derivecurrentfacts→stablepool+immutableencoding. CAIverifiedsamecanonicalcontext; THUNG actualapprovednativeencoding plus crossproof, pureNULLunchanged. Không pool theo key. |
| POST `/api/m5/lien-ket/{preview,xac-nhan,huy}` | Dispatch actual action/body: typedpair/version/encoding/pool/proofrefs, two native strings, expected fullgraph+budget digests,key/reason; derive PN/owner/factors/pool quantities. Preview read0writes, missingencoding blocked/actionable, không seedapproval/pool. |

`k2/lien_ket_chung.py` quantity-only preview/confirm/undo/remaining; implement `KhoSoLuongK2.lien_ket` stub. SQL quantity consumers closedstage/typedrefs (finite names may be l11_preview/l11_xac_nhan/l11_huy/l11_xac_nhan_bang_chung); không moneyhelpercall.

UI thực: role→receiveproof→facts/issues→CFOapprove/revoke→selectsource/proof→“Mã hóa nguồn”→selecttypedpair→two nativeamounts→Previewfourquantities/native-poolunits/confirmed-held-blocked→Confirm/Undo. Pickers scopedDTO, không nhậpUUID/factor. Current epoch/form/selection fences GET/POST/download giữ M5UI05/M2async guards; không applylate response sangrole/PN/pairkhác. Detail/list/previewDTO+token một owned REPEATABLE_READ snapshot/connection; refuseunsupportedouterTX, không tuplesnapshotgiả.

## 7. Cross FILE mode, list và download

POST `/api/m5/l11/file-soat` riêng: typedsubject+expectedquantitygraph/key/reason, serverderived immutable **L11_QUANTITY** mode. Current BOTH READ+M5_FILE_SOAT trướclookup/replay/list/sharedGET; no browserbool/mode. Preflight/requestH/namespace/closedFILEstage/lo bindmode+wholequantitygraph coherently. Use existing`m5-xuat/<sha>.xlsx`, formula-safe text-exact bốnquantities/unit/encoding/proof/pool/source/PB/observation/route/held/linkstates. Stale→0newfile/lo/stage; oldbytes/hash khôngrewrite.

Old source-only POST `/api/m5/xuat-file-soat` format/rights/bytes giữ nguyên, không invoicefields. Shared GET `/api/m5/file-soat/{lo_id}` deriveguards immutable ownerissuedmode; không fakelegacy bypassM2READ. Existing lo registry/purpose/path/provenanceguards giữ; không parallelfilestore. MissingM2READ không crossdownload dùcóM5_FILE_SOAT; raw/evidence đọc theo currentcaps, không throughXLSXleak.

## 8. Finite acceptance sau terminal/freeze/root review

| Group | Nonempty positive và negative oracle |
|---|---|
| Q00 | Actualrawreceive→CFOgoods/unit/nativeencoding/crossproofapprove; ordinaryapp ownerpreparedstagepositive. SameCAIlabel/unapprovedraw/bodyfactor/PROVEN/wrongpurpose/crossPN/conflictingratio không confirmedchild. |
| Q01 | Invoice10/K018 link8/8: remaining2/0; samekey/H onechild/parent, changedH409, no extras. |
| Q02 | Bothbudgets/full-domainmultipool: repeated4+4→twochildren/oneparent,use8/8; overuse mỗi phía independently0loserdelta, không pool perPB/profile/UOM/key. |
| Q03 | THUNGpureNULLunchanged; approved0.5THUNG↔6CAI/K01 remaining0.5/2. Fullsplit1THUNG↔6+6 twoeligiblelogicalroots remaining0/0/0; invalidcrossproduct/38,12/out-ofrange/nonrepresentable1/12 khônground. |
| Q04 | Confirmed6→capacity8 available2; capacity4/reversal/routeaway/proof/mapchange→held6,availableNULLblocked; khôngfree/clamp/retarget/reinterpret/count12. |
| Q05 | A,A/duplicateZIP observations-only preservePB/route/proofs/pools/child; A→B→A eligibleNULL/held, noautoresurrection. |
| Q06 | Exacttypedgraphpositives; wrongPB/core/STT/logical/encoding/pool/PN/BAN_RA/retarget/proof/freeJSON/directparent-child-receipt writes denied0businessdelta. GenuineoldCRM/M1positivepreserved. |
| Q07 | Twoactors/currentcapspositive; inactive/revoked/M5only/M2only/period/protection/rawleak/fakefilemode blocked beforelookup/replay; seed/reopen no regrant. |
| Q08 | Undoconfirmed/held/ineligible once releasesstoredamounts+HUY/audit/tombstone, oldconfirmkeycurrentHUY; FILEactualcells/download/oldbytehash/reopenheld/pools/revocationspersist; noextra invoice/core/BANK/331. |
| Q09 | RealindependentPGconnections+pg_blocking_pids+actualroot/poolIDs, bothwinnerorders: sharedinvoice/sharedwarehouse; samekeyacrosspairs; confirmvssource/profile/map/review/route/proof/reversal; undovsconfirm/proof. Nonemptywinner+currentreevaluation/loser0delta; timeout/deadlock/exception/emptysetup/NOT_RUN khôngPASS. Directdefinercontrols cũng bắt buộc. |

## 9. Exact15 write targets và delivery

Existing10, exact paths:

- `src/kho_tri_thuc/ha_tang/pg_migrations.py`
- `src/kho_tri_thuc/k2/lien_ket_chung.py`
- `src/kho_tri_thuc/k2/kho_so_luong.py`
- `src/kho_tri_thuc/k2/hoa_don.py`
- `src/kho_tri_thuc/k2/quyen.py`
- `src/kho_tri_thuc/k2/crm_khoi_dong.py`
- `src/kho_tri_thuc/k2/nguon_chung.py`
- `src/kho_tri_thuc/giao_dien/server.py`
- `src/kho_tri_thuc/giao_dien/assets/app.js`
- `src/kho_tri_thuc/giao_dien/assets/index.html`

NEW5: `src/kho_tri_thuc/k2/l11_demo.py`; `tests/test_l11_migrations.py`; `tests/test_l11_k2.py`; `tests/test_l11_http.py`; `docs/BAO-CAO-L11-QUANTITY-01.md`. Không sửa pure/oldfixtures/reports/sourceapp/M9 hoặc files ngoài15. Source269→273 do bốnnewpy; reportngoài sourceinventory. l11_demo chỉ configure/retainrawcandidates+unitdocs/candidateTHUNGlinefact vànewactors mộtlần; no seededapproval/confirmedlink, no oldgrantsrewrite.

Báo cáo final ghi exactchangedfiles, literal/generated1–15 preservation, acceptance/notrun từnggroup, actualAPI/buttons/FILEmode, limitations. RootFULLfinalcode/tests/sourcepins trước runtime; selectedtests, directSQLpositive/negative, causalraces, HTTP/GUIbuttonflow/filecells/download/reopen riêng, không dùng codepresence hoặc syntheticinput như bằng chứng hoànthànhL11/fullM2/M5/33.
