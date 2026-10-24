# M0–M5 — SQL và trusted fixture DEMO, bản 01

**19/10/2026 — ROOT_REVIEWED_TECHNICAL_CONTRACT / CODE_ONLY / NOT_SEEDED / NOT_RUN.** Root đã đọc toàn bộ binding và kiểm hashes của registry/raw fixtures. Contract cho phép Claude viết code theo handoff17targets; chưa cấp import product, test, SQL/migration, HTTP hoặc GUI. Actual candidate SQL/grants phải full-read sau terminal rồi mới release runtime riêng; không đợi DDL chưa viết để bắt đầu code. Không đổi fixtures pure43 hoặc tự chọn quyền production.

## 1. Nguồn và pins

- Handoff `GIAO-CODE-M0-M5-INTAKE-UI-01.md` SHA `868543441451eb7f8573f48bdcfa2cacd7d83e438f3a5f2088b7f5b42650030e`; M5 binding SHA `7de60be44fe301d043a70aa2b582572f5d96d40f9444238f10a2a50acd4bcc5c`; DTO03 SHA `d1b3577074794d8d09af2d5ccb58aa0caa47540f7ccaf3e62475599fb6e6f73f`.
- Pure43 manifest `tests/fixtures/kho_10/manifest.json` SHA `5d680a1cd4a691fba5d6eca7056bdc94f9fbf558b80e2415d97f9808215c8e66`; current contexts là nguồn DEMO đã pin, không browser authority hoặc production proof.
- Registry mới `tests/fixtures/m0_m5/trusted-registry.json` SHA `780180aaa8da3d135ada9693e1dcc9f5a32173f7fc05d22c92cd2c745d0b3883`: 2 source instances, 1 shared profile payload, 2 warehouse mappings, 3 master contents, 2 source-scoped measurement facts, đúng 8 actors.
- Root đã DATA_ONLY verify digests/provenance `6f6520`, pin manifest `tests/fixtures/m0_m5/manifest.json` SHA `51b794ae55559c7245d99c163270fdb5fdd8405eb4a73b1d45c3e7a8ea2bbf5e`: 12 listed files+manifest=13; đây là fixture preparation, không product acceptance.
- Root báo actual lexical preparation exit0 `c903ab`; manifest private SHA `3bfd70abb56ded266fa7fb48fd2049b96d4706e19f0e5f4ae5ed022b32db27a0`. Root đã copy 10 rawmaster vào `tests/fixtures/m0_m5/masterraw`; bản này không tuyên bố đã độc lập chạy lại helper.
- `tests/fixtures/m0_m5/lineage-pins.json` SHA `418194019d14cb859f10ed2d545ace0e8c5e1c96b09f534a0a549d2d4f6e5f15`; exact historical full-M9 M13 checksum `2a2acb81bc85f57a5643a4736528d120f9f48ee1d005ad8bec0a178ba1926d40` (155 SQL strings), definitions only, không execute.

## 2. Exact registry và cách resolve

SOURCE_A/B tương ứng chính xác `DEMO_KHO_A` / `DEMO_KHO_B`. Cả hai dùng profile ref `urn:demo:m5:source-profile:f05eee570c7c8861b219ca97`, payload SHA `b8735806b72701dc6a4a54c3b3772e70326efbc812543b1c5969576be3eedb41`; khóa quyền luôn gồm instance+ref+digest. Digest là SHA256 UTF-8 của `canonical_json(payload)` hiện có (`primitives.py:24–25`), không newline; không phải source-code SHA `62f4658321ea6c6230a58cf850d49de43e2db826e5a66f807249de29af873e2c`.
Profile chỉ khai báo lexical transport/artifact roles/native shape và nhận STRING/NUMBER/NULL, **không** chứng minh precision cho toàn instance. NUMBER, NULL, unit mới/thiếu vẫn được capture và giữ issue/HOLD; không đổi thành exact text, 0 hoặc ratio1.
Root chốt alias rõ: `DEMO_PN_A → master.phap_nhan.ma PN_DEMO_A`, `DEMO_PN_B → PN_DEMO_B`; service resolve UUID thật theo ma này. Không tạo PN trùng, không đổi CRM PN/actor/modules. Pure context labels giữ nguyên chỉ cho standalone reader; repository/service context dùng UUID hoặc stable ma đã resolve, không đưa alias chưa resolve vào tenant FK.
Configured scopes A/B lần lượt có refs `urn:demo:m5:scope:f08b4a9bf0c11f07cee2f2fc` / `urn:demo:m5:scope:90e1a693fba951fe386c0e16`, cùng `MaKho=KHO_DEMO`, `SoPhieu=NK20260814001`, sections GD_Dong/GD_Phieu/MASTER_WHITELIST. K07 dùng lại scope_ref A nhưng coverage PARTIAL: configured scope không đóng băng reported coverage; coverage/errors thuộc từng capture và H.
Warehouse mapping `DEMO_MAP_A_V1` / `DEMO_MAP_B_V1`, revision1, subject WAREHOUSE, exact instance/profile/MaKho→existing PN tương ứng; validity DEMO từ 2026-01-01Z. Đây là root-prepared DEMO decision, actual mapping verification vẫn NOT_VERIFIED. Không giả MaKho thành company key để qua COMPANY-only guard.
Master refs `...:7aea96355efd196e316f1ccc`, `...:4bc13845117c9bfad17bbb2f`, `...:d1d891226e6ea7605a8e6d96` gắn lần lượt actual raw SHA `3a806526917dac322ee9ba4c6f7ea5ed88e02b780ea282c0300465e980e16801`, `a232e15b51faf6423e94f935bc6ecd082d8730f0b9983b11b9cb3d7700dc1123`, `be8849306a58e04c94ae1d5dc44ab9d5074c1541fac36669c1e12b55bd88bdd5`. Hash content dùng chung không cấp quyền đọc nguồn; capture-role/source edge vẫn scoped.
Measurement declaration ref `ROOT_DEMO_CAI_EXACT_TEXT_38_12_V1` bị dùng chung A/B nhưng payload khác source/measurement/unit. Key phải có instance+profile ref/digest+declaration ref+payload digest; không lookup declaration_ref một mình. Payload A SHA `4ef4dcf27d5044a76729d6f617b4381c6fff0fcced4bdf9f9315c638ffd515f1`, B SHA `75c34bafb939b121c6837ec42102fdee51e3f60b2886e559d48690d216263548`.
Chỉ resolve fact khi actual captured master SHA=3a8065…, mọi referenced master UOM=CAI, có quantity STRING và mọi present/non-null quantity đều STRING. Bind exact `DEMO_EXACT_TEXT_CAI_A/B_V1`, `DEMO_UNIT_CAI_A/B`, domain38,12 và explicit same-unit1/1 từ immutable payload. Sai/thiếu một điều kiện→resolved facts NULL+issues/HOLD; same-unit conversion proof NULL là N/A, không suy bằng native DVT_QuyDoi. Partial/duplicate/history issues vẫn giữ riêng dù measurement đủ.
Server xây context từ artifact bytes đã kiểm+registry+repository state; client không cấp authority/PN/PROVEN/ratio/accepted state. Registry không seed K01–K10 expected history, accepted/eligible pointers hoặc semantic/request digests; reader và DB review phải tạo các kết quả thực.

## 3. Ma trận đúng 8 actors

Mọi login có `mo_phong=true`, active và UUID server lookup theo exact login; không suy source/PN từ suffix. Các grants dưới đây chỉ additive cho actor mới; không gọi blind seed CRM để reset arrays.

| Login | Vai | Source capability | Business PN/module/action |
|---|---|---|---|
| MO_PHONG_M0_KHO_A | KE_TOAN | SOURCE_A INTAKE, READ_SOURCE | Không |
| MO_PHONG_M0_KHO_B | KE_TOAN | SOURCE_B INTAKE, READ_SOURCE | Không |
| MO_PHONG_KT_KHO_A | KE_TOAN | Không | PN_DEMO_A / M5 READ, FILE_SOAT |
| MO_PHONG_KT_KHO_B | KE_TOAN | Không | PN_DEMO_B / M5 READ, FILE_SOAT |
| MO_PHONG_CFO_KHO_A | CFO | SOURCE_A SOURCE_MAP, target PN_DEMO_A only | PN_DEMO_A / M5 READ, FILE_SOAT, MAP_V4, SOURCE_REVIEW_V8; V4,V8 |
| MO_PHONG_CFO_KHO_B | CFO | SOURCE_B SOURCE_MAP, target PN_DEMO_B only | PN_DEMO_B / M5 cùng actions; V4,V8 |
| MO_PHONG_VIEW_KHO_A | XEM | Không | PN_DEMO_A / M5 READ only |
| MO_PHONG_M1_ONLY_KHO_A | KE_TOAN | Không | PN_DEMO_A / M1 READ; M5 negative |

Source actions exact `INTAKE`, `READ_SOURCE`, `SOURCE_MAP`; business action keys đề nghị `M5_READ`, `M5_FILE_SOAT`, `M5_MAP_V4`, `M5_SOURCE_REVIEW_V8` (M1_READ trong fixture là semantic mapping tới existing XEM_TIEN, không thêm action M1 mới). Mapping cần BOTH exact source capability+allowed target PN và M5/CFO/V4. V8 review cần M5/CFO/V8, không thừa hưởng raw/source-read hoặc INTAKE. Business READ/FILE không tự có source capability.

## 4. COMMON13 — unit SQL trung tính tối thiểu

Default chain prefix1–12 nguyên bytes/checksums → COMMON13 → M5 14; giữ nguyên historical M0013 SQL/helpers nhưng không register/execute. Exact legacy13 hoặc unknown/duplicate/gapped history từ chối trước DDL/markers/seed, kể cả có version sau13; không alias/skip/rewrite checksum hay `migrations=` test bypass. CRM startup kiểm lineage, không chỉ MAX(version).
Root chốt contract cột/khóa/grants tối thiểu dưới đây để viết unit COMMON. Tên helper hoặc bảng phụ có thể chọn trong cùng grain; actual DDL vẫn phải review trước chạy. Giữ common names đã duyệt, không tạo registry quyền/M5 raw-store song song:

| Grain | Cột/khóa/guard tối thiểu |
|---|---|
| `master.nguon_instance` | PK source_instance_id text, active state; không PN bắt buộc trước capture |
| `master.nguon_profile` | source instance FK, immutable profile_ref+profile_sha256+payload; UNIQUE(instance,ref), UNIQUE(instance,ref,SHA). Cùng ref khác payload phải revision/ref mới, không UPDATE. Owner seed kiểm canonical payload hash; không dùng SHA(jsonb::text) thay canonical_json |
| `master.nang_luc_nguon` | actor UUID FK, instance/ref/SHA composite FK, action enum, target PN nullable; UNIQUE NULLS NOT DISTINCT(actor,instance,ref,SHA,action,targetPN). SOURCE_MAP bắt buộc targetPN; INTAKE/READ_SOURCE bắt buộc targetPN NULL; chỉ admin/approved seed thay grants |
| `giao_tiep.tep_tiep_nhan` | immutable actual object key/rawSHA/byte_length/media, UNIQUE(instance,rawSHA), exclusive file/hash verify; integration/source-cap scope, không app-wide raw grant |
| `kho.anh_chup_nguon` + immutable artifact-role bundle | content identity gồm instance/profile/SHA + exact native/master role tuple digest. Unique role trong bundle; mỗi present role FK đúng raw instance/hash/length/media, missing required role phải ghi absence/error/PARTIAL và giữ raw/candidate, không bịa role/hash hoặc coi validated; snapshot/occurrence composite FKs cùng bundle. Không reuse snapshot bằng nativeSHA-only khi master thay đổi |
| `giao_tiep.lan_tiep_nhan_nguon` + prePN capture receipt | namespace UNIQUE(instance,CAPTURE,client_key), capture H NOT NULL, immutable profile/scope/coverage/error/bundle refs, actor/time audit; một successful new key→một thin occurrence, same key/H→0delta. Có thể gộp hai grain trong một row nếu vẫn giữ các invariants; không PN giả/không PN-business receipt thay thế |
| `kho.ban_ghi_nguon` | exact snapshot/bundle/section/locator/native row/ref/hash, UNIQUE(snapshot,section,locator); PN nullable trước mapping. M5 quantity exact token/type/ordinal được giữ từ raw, JSONB không thay lexical evidence |
| `master.anh_xa_nguon` | immutable revision+validity, neutral WAREHOUSE subject và exact instance/profile/MaKho→PN; DB overlap/retarget guard, expected revision, source+target-PN rights; reuse cùng mapping store, không company-key giả |
| trusted measurement fact / master binding | immutable composite identity như§2, payload digest+master raw/rows basis; seed-only writes, source-scoped resolution. Có thể dùng neutral profile payload subrecords, không operational item/warehouse master mới |
| `giao_tiep.tep_tach_phap_nhan`, `kho.bien_nhan_thao_tac` | derivative chỉ PN/module được phép; receipt business PN/M5/operation/key tách capture; current action guards trước replay/result lookup, immutable request/result/audit |

RLS/trigger/definer phải đọc lại `master.ktt_danh_tinh()` hiện có (ID+login active, migration11:1224–1230), DB capability/current role/action/targetPN; business thêm existing `ktt_duoc`+`ktt_co_vai` và kỳ. Không tin Python boolean hoặc receipt actor cũ. Ordinary non-owner direct SQL có positive/negative source+PN counterparts; app không được INSERT quyền/profile, UPDATE pointers hoặc execute unrestricted definer. SECURITY DEFINER fixed search_path, schema-qualified refs, REVOKE PUBLIC EXECUTE; chỉ grants trên common objects thật tồn tại. Đây là DEMO trong identity/session boundary hiện có, không tuyên bố raw DB credential chống được giả mạo một valid session pair hoặc production auth đã đạt.
Raw/snapshot/raw-role lookup cần current READ_SOURCE, capture cần INTAKE trước receipt/artifact lookup; integration metadata không lộ cho M5-only viewer. Source actor không có PN vẫn capture được. Không dùng old creator==actor shortcut, `_rls_v13` hoặc full-M9 grants; không cài loan/money schema/functions.

## 5. Capture H và M5 14

Capture H `SHA256(canonical_json(envelope).encode('utf-8'))`, envelope contract `m0-capture/v1`: exact source instance; source_profile `{reference_id,sha256}`; configured source_scope (sections sorted unique); reported coverage; reported error codes sorted unique; artifacts unique/sorted role với `{role,raw_sha256,byte_length,media_type}` từ actual bytes. Profile/scope resolve server-side. Required-role thiếu giữ absence/error đúng profile và raw/candidate, không hash placeholder giả. Actor/client_key/time/PN/mapping/source review loại khỏi H, vẫn audit riêng. Capture H khác reader request H và PN-operation H; optional reader request NULL không ngăn valid prePN capture.
Same key/H replay0delta; changed native/master/profile/scope/coverage/errors→409 trước artifact write; fresh key/same bundle→1thin occurrence reuse blobs/content. DB transaction+namespace lock/unique serializes hai connections; rights/revocation trước replay, không Python mutex-only. Artifact write failure giữ owned partial/evidence, không xóa để giả rollback.
M5 14 chỉ tạo năm typed tables trong binding§3 (`phieu_kho_danh_tinh/phien_ban/quan_sat`, `phieu_kho_dong_danh_tinh/phien_ban`), PN+identity+content+logical-line+snapshot/role-bundle composite FKs; giữ exact native values/source order/nullable normalized quantities. DB guard owner PHIEU_KHO→M5, immutable content dedup, unique receipt observation, accepted/latest/eligible pointers cập nhật có expected graph dưới lock.
A→B đảo→A cũ giữ accepted B/eligible NULL và REAPPEARANCE_HOLD; mapping retarget mở impact/HOLD, không move PN/copy identity. Source-review V8 không core journal DA_DUYET, không V1 journal0. Kỳ khóa giữ raw/capture nhưng chặn business action đúng existing gate. L11 dual-pool/M2 bridge còn gói sau; tồn/kiểm kê chỉ actual producer snapshot hoặc unknown, không tính mới.

## 6. Gate còn lại trước release

Full `m0_m5` fixture manifest đã được root pin ở§1. Baseline trước code gồm204files, private manifest SHA `83be12cc0886dc847a471ada88c6524ca483430fba054887b679c5b64b92e67c`;13newfixtures,191oldfiles giữ nguyên. CODE_ONLY dùng finite17targets, zero execution tools. COMMON/M5 actual SQL checksums, ordinary DB-role/grants và test commands là gate runtime SAU source terminal/freeze/full-read; không là blocker cho viết code hiện tại. Không tự coi doc là DDL đã chạy. Registry seed phải validate all canonical digests/aliases/master bytes và refuse conflicting existing immutable rows, không overwrite/reset CRM. Acceptance phải quan sát actual role-bound DB/HTTP/UI/replay/race/history/file behavior; registry và old pure goldens không thay kết quả thực.
