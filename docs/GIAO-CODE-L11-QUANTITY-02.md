# L11 QUANTITY — repair02, root bounded handoff

**ROOT_REVIEWED_BOUNDED_CODE_ONLY_HANDOFF / L11_QUANTITY_CODE_ONLY02.** Root chỉ phát hành thực tế qua dispatcher đã pin handoff/bindings; file này không tự khởi chạy Claude hoặc cấp runtime. Chỉ viết code theo exact15 targets tại §7. Không execute/import/compile/tests/SQL/HTTP/JS/browser/server/CLI, không provision, đọc secrets/sourceapps/real data hoặc delete/drop/reset/cleanup. Selftests của coder ghi **UNRUN**. Không tạo engine, registry, file store hoặc auth framework mới; không M9 work.

## 1. Inputs và baseline bất biến

Kế thừa đầy đủ `docs/GIAO-CODE-L11-QUANTITY-01.md` SHA `ce65bd92dc0c97509b69a9062969b55cefea2dee2e01bffa75822ba73ddcb4a5`, `docs/L11-QUANTITY-CASES-01.json` SHA `6ab9e6603fc7d3d067f4fd557630a11e84b91cfb4eb30e7c5e077e0a11c1f66f` và toàn bộ binding M2/M5 đã dẫn trong handoff01, trừ các sửa cụ thể bên dưới. Không sửa các inputs này.

Actual candidate01: Claude handle4168/chunk316fbb/exit0/sameUUID `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`; source273 manifest SHA `22c58d26171217b869dca4e74d483feb7313f5e1f4883e4166ea15e900c2bccf`, freeze receipt SHA `992fbcc7bcd543512a11690093baa71f84db2b5d9a03bd4d8aae211db3a9d5bd`. Root froze scope clean, chưa L11 acceptance. Fixture20 manifest `227980804428af52fb153b9c15a9142e5b261f2b50bbd4b8e873ba421b3081dd` giữ nguyên bytes; pure readers/tests, old source snapshots/actors/revocations và report01 bất biến.

Authoritative service findings: `docs/REVIEW-L11-SERVICE-02.md` SHA `54d0edbd337ea46bfbbf57a93c3a7ca59bef4d7e535f2da9796687d390f313c1`; UI/API: `docs/REVIEW-L11-HTTP-UI-01.md` SHA `fe6a4eb3058a8f9f628cae0d8a747eea71b02e3fb3e5d115ddc71d8bd41fe9f0`. Review01's G01 instanceB bypass example đã rút vì upstream verified-CAI context guard; không dùng lại làm failure/oracle. THUNG context negative là static/unrun và phải có legitimate typed-bridge positive trước khi kết luận.

SQL: **chỉ sửa migration16**. Literal/generated SQL1–15, thứ tự/checksums và historical M9 definitions giữ byte-identical với handoff01/cases01. CREATE OR REPLACE các entrypoints cũ chỉ được đặt trong16, không sửa lịch sử hoặc append17 để né lỗi16 chưa accepted. Root chọn fresh retained DEMO sau freeze; không thay checksum DB đã có16 hoặc tự upgrade/cleanup các attempts01.

## 2. R1 — whole-batch DB lock/impact protocol

Thay AFTER-trigger-only impact bằng precollection thực ở **toàn bộ11 đường nguồn** trong migration16: M5 `m5_khoa_phieu`, `m5_tieu_thu_quan_sat`, `m5_giu_cho_anh_huong`, `m5_xem_xet_nguon`, `m5_anh_xa_v4`; M2 `m2_tieu_thu_quan_sat`, `m2_xem_xet_nguon`, `m2_mapping_dong`, `m2_route`, `m2_mapping_cong_ty`; shared `master.anh_xa_nguon_kiem` cùng caller/writer paths cần thiết. Actual frozen anchors lần lượt4073/4144/4270/4361/4430,5912/6100/6146/6287/6359 và5386. Giữ original admission/receipt/history behavior ngoài typed quantity impacts.

Current identity/source/PN/module caps→operation namespace/key/H/replay→precollect toàn batch affected logical roots/children/peers→canonical sorted roots **cả hai phía**→sorted pools→fixed source/mapping/proof/encoding/child row locks→reread closure→effects/holds/finalreceipt cùng transaction. Không mutate source/mapping tuple hoặc giữ pool trước khi biết/khóa toàn closure; không phụ thuộc XML/ZIP iteration order. Closure mới phát hiện phải restart toàn mutation trước effects, không xin root thấp hơn sau pool. Consistent protocol cả direct-definer paths; Python mutex, owner membership/GUC, AFTER row-trigger xin khóa muộn không thay được DB guarantee.

Confirm/source review/reversal/route/profile/map/unit/proof change hoặc revoke, encoding và undo phải dùng cùng root→pool→row order, conflict locks đủ chặn non-key UPDATE, sau chờ đọc lại trạng thái. Source-owner intake tự đánh dấu CAN_SOAT dưới own current intake cap, không đòi human BOTH V2 hoặc lộ peer invoice cho source-only actor. Atomically hold mọi affected live child và giữ nguyên stored native/pool amounts/proof/pool/child IDs trước commit mới; capacity blockedNULL không free held. A,A/duplicate ZIP chỉ observation/CAS, không hold semantic-equivalent content; A→B→A không auto-reactivate.

Undo held/ineligible dùng current BOTH V2/period/protection/reason, giải phóng đúng stored amounts một lần và giữ tombstone/audit; không đòi confirm eligibility/liveproof/current capacity. Receipt replay đọc current child/HUY/CAN_SOAT sau current rights, không historical resurrection. Human confirmation vẫn cần cả hai budgets/eligible/approved route/proofs hiện hành.

## 3. R2 — ba quantity semantics và source-bound evidence

Cross-native ratio áp lên **native A/B và native unit definitions**: a×cross_num=b×cross_den. Hai own-pool consumptions derive riêng bằng each approved native→own-pool encoding. Không so cross proof với pool unit hoặc dùng poolA×ratio=poolB. Giữ exact integer-string rational38digits/reduced positive, Decimal38,12 representability trước cast, không rounding/float/abs/default1. Có nonidentity-own-encoding positive chứng minh hai phép tính độc lập; THUNG pure CAI-only normalizedNULL không bị đổi.

**Cần đóng cả schema, không chỉ sửa equality:** frozen approve6913–6916 ép `pool_unit_definition_ref` bằng native `unit_definition.reference_id`; NATIVE_ENCODING CHECK7924–7927 chỉ lưu một unit tuple và bắt from/toNULL, encoding7140 dùng tuple đó làm target. Lưu/kiểm rõ native-unit tuple và own-pool-unit tuple (ID+definitionSHA/FK), cả hai đã verified qua shared MASTER; actual declared native→pool rational độc lập, không suy transitive hoặc đồng nhất theo label. Cập nhật typed encoding/child facts/preview/FILE tương ứng trong16; giữ existing THUNG→THUNG1/1 proof bytes/behavior. Không sửa20fixtures/four default configured references.

Nonidentity finite test admission được tạo **trong14 files đã allow** (ví dụ in-memory synthetic bytes/profile ở `test_l11_k2.py`), không new fixture/source file: new dedicated registered evidence instance/profile + exact H/length/reference/revision dùng COMMON existing registration/closed intake→candidate→current CFO approve, không owner INSERT approved rows/encodings hoặc sửa old profile. Existing consumer6722 lấy `proof_references` từ selected registered profile, không hardcode4refs. Declared synthetic nativeTHUNG→existing invoice-sideCAI pool12/1 với proper native/domain/support facts là technical DEMO control, không policy tài chính mới. Positive native0.01THUNG/0.12warehouseCAI phải consume0.12/0.12poolCAI (capacity12/8, remaining11.88/7.88); negative native0.01/1.44 phải bị đúng native-equality guard dù ownpool0.12/1.44 và cả hai budgets đủ. Cả hai đi actual source→approved evidence→encoding workflow; wrong raw SHA/unconfigured profile/duplicate key không phải negative PASS.

Chặn source-bound support thiếu/khác actual raw field: unit declaration raw SHA/length/locator/payload/context; supporting artifact raw+length; actual unit/item field at declared locator; sourceinstance/profile/refSHA/scope/company/warehouse; typed line identity/source locator và original **source_ordinal**, không tùy ý dùng rendered/core STT. M5 goods/cross/encoding binds cả current `measurement_payload_sha256` và actual native/master bindings. Verified declaration self-H/catalog FK hoặc same CAI label không thay raw support field proof. Giữ distinction definition evidentiary MASTER3a8… với current split MASTER3c6…; không ép các delivery về cùng rawSHA và không tạo unit/pool mới mỗi delivery.

Reuse actual readers/lexical support extraction và COMMON closed owner stage, không viết SQL reader cạnh tranh. Authoritative extracted facts phải derive từ pinned bytes/current typed graph cùng configured owner transaction, DB consumer kiểm stage/H/current tuple/caps; không nhận free JSON/browser assertion. Goods domain và native-encoding authority giữ exact configured sourceinstance/profile/company/item context ngoài supporting native tuples. Add legitimate in-domain positive + changed field/unit/item/locator/context/measurement/sourceordinal negatives, giữ raw/audit nhưng0new approved proof/encoding/link. THUNG alternative-context test chỉ có ý nghĩa sau legitimate actual capture/mapping/bridge được admit; không resurrect withdrawn G01B example hoặc nới pure profile.

**Pool LINE grain hiện đã đúng** (`hoa_don_dong_id`/`phieu_dong_id`, stable logical LINE); giữ nguyên, không chuyển sang document pool. Hai split6 trong một phiếu có hai pools6; parent vẫn document-snapshot pair. Same logical pair/basis có hai confirmkeys4/4→hai immutablechildren/một parent; không thêm UNIQUE(pair,basis), không UPDATE old amounts hoặc pool perkey/PB/profile/UOM.

## 4. R3 — admission/privacy, generic parent và capture semantics

Preview phải resolve/check **cả hai** typed endpoints, samePN và current BOTH READ trước unscoped owner projection/budget/peer refs. CrossPN/wrong graph trả denial trước trả B latest/accepted/eligible/map/rawunit/PB/core/logical/pool/available; không chỉ thêm blocker rồi vẫn serialize peer DTO. Test PN_B private sentinels và nonempty authorized samePN positive; read-only preview không ghi stage/pool/receipt/file.

Generic `kho.lien_ket_chung_tu` guard kiểm new core endpoints khi **INSERT và UPDATE**, kể cả old ownerNULL/M1 parent có owner/subject fields không đổi. Không cho legacy row retarget vào new M2/M5 graph rồi đi permissive policy; genuine old CRM/M1 paths giữ nguyên. Typed parent immutable actual-owner-only branch, BOTH READ RLS/legacy OR conditions, no generic HUY freeing child reservation, no money child trên EVIDENCE giữ nguyên.

Proof candidate retains original claimed coverage/errors trong COMMON H/receipt, tách validated effective coverage/issues. PARTIAL_INPUT/UNKNOWN/nonempty reported errors hoặc contradictory required-role evidence phải HOLD/deny approval/encoding, không nhận UNG_VIEN complete implicit chỉ vì raw hash đúng. COMPLETE_INPUT nghĩa một submitted proof input; không đòi đủ cả4 proof files trong một capture. Không silently normalize các claims khác về cùngH hoặc fake artifact. Same key changed claim/error H→409 trước extra blob/stage/receipt; raw retained allowed, approved business delta0.

## 5. R4 — HTTP/UI snapshot và proof-to-FILE flow

- FILE continuation giữ **original operation epoch/actor/PN/pair/form fence qua mọi await**, cả awaited refresh và auto-download; không lấy current epoch để re-arm old response. Role/pair invalidation trong POST→GET gap hoặc newer GET thắng phải discard old result,0auto click/download. Existing server rights-before-replay/download vẫn bắt buộc.
- Candidate picker/detail hiển thị current scoped raw H/length, reference/revision/kind/state/issues và **facts trước approve**: source/domain/native bindings, items, native/from/to/pool unit definitions và exact ratio khi relevant. LINK không nhận raw candidate qua derivative/XLSX; CFO chỉ relevant source READ. Dùng DTO pickers, actual receive/approve/revoke/encoding buttons, không nhậpUUID/factor.
- Thêm actual GET `/api/m5/l11/proof` theo handoff01/current source caps. Giữ exact two-login selector; no blanket MO_PHONG prefix; body compatibility hiện hành không nới authority fields.
- Toàn visible aggregate `/api/m5/l11` (approved proofs/lines/encoding/candidates/scope/FILE basis/tokens/actions) thuộc **một owned REPEATABLE_READ snapshot, một connection**; internal readers reuse, không gọi hai standalone RR rồi ghép. Preserve unsupported outer-TX refusal; standalone proof GET có own RR. Current-role capability refresh/fences không nhận browser proof/PN.
- Cross FILE vẫn same configured owner TX/closed stage, immutable L11_QUANTITY, whole quantity graph+H/current BOTH M2_READ+M5_READ+M5_FILE_SOAT trước lookup/replay/list/download. Existing `m5-xuat/<sha>.xlsx`/lo provenance giữ. Old M5 source-only format/bytes/rights không thêm invoice fields hoặc rewrite; exact-text/formula-safe bốn quantities/units/proofs/routes/held/current states.

## 6. Regression controls và actual evidence boundary

Giữ toàn Q00–Q09/cases01, nonempty positives trước negatives. Add exact-code + row/hash/sequence/file observers cho denial/zero delta; không coi broad substring `L11_`, expected stale exception, counts-only, empty setup hoặc cascade là PASS. Direct ordinary-app owner-prepared valid-stage positive và forged graph/receipt/parent/unit/proof negatives; owner helper không được fake authority cho app.

Causal tests: all11source paths static coverage + actual disjoint PG connections cho confirm versus source/map/review/route/proof change và undo; shared invoice/warehouse multipool cả hai winner orders. Dùng observer `pg_blocking_pids`/actual root+pool IDs, bounded owned watchdog; timeout/deadlock/exception không PASS. No-delete áp cả fixture setup/rollback/teardown; retain DB/roles/files. Reopen/seed additive, không reset hoặc regrant revoked actors.

UI controls phải assert facts-before-approval, actual proof GET, one-RR aggregate coherence dưới second-owner commit, both role-switch orders trong FILE refresh/download và pair invalidation, fresh positive actual FILE bytes/SHA/cells/formula safety/old GET bytes. Substring asset tests không chứng minh async behavior hoặc browser flow.

**Root actual outcomes (separate from coder selftests):** candidate01 native migration suite root đã chạy9/9PASS; outer gate01 REFUSED là post-bridge Windows evidence-path validator error, không rerun/đổi test. Root service attempt handle51480/chunk0b0dca exit1, evidence `pg-retained-20261019-234915-dff1fd39`: native counters run15/fail2/errors10/skip0;6 named methods ok nhưng summary passed3 do subtest accounting, không kết luận unique pass count. t02 expected `L11_MA_HOA_KHONG_CAN_BANG_CHUNG` thực `L11_VERSION_CHANGED`; t07 expected missing encoding proof thực VERSION_CHANGED; các missing-state errors còn lại có cascade, chưa đếm thành bugs mới. Root HTTP attempt exit1/chunk97ba89, evidence `pg-retained-20261019-235032-9d911c6c`: run2/pass1/error1/skip0; approve test line186 KeyError trang_thai. Đây là actual test failure, chưa chứng minh business approve failure. Root independent outcomes **UNBOUND / root sẽ bổ sung sau**, không bịa PASS.

**Sửa test setup có căn cứ, không nới product guard:** frozen SQL `_L11_TOKEN=_M2_TOKEN`6510; `_M2_TOKEN`4781 hash `{x}::text`, trong khi `test_l11_k2.ma_hoa`210–212 tự hash `master.json_chuan(g)` nên encoding VERSION_CHANGED có nguyên nhân test-token mismatch tĩnh, chưa chứng minh product self-changing token. Dùng **actual public DTO token** vừa đọc, không owner/internal JSON canonicalization hay rebuild token để qua stale. HTTP helper180 `hc-{ref[-8:]}` tạo cùng key cho GOODS_EQ_A và CAI_EQ_A (đều `_EQ_A_V1`): đổi unique keys theo toàn ref/action, giữ exact-body/key replay riêng; expected conflict khi cố ý đổiH vẫn409. Key collision là root-cause inference, cần finite positive/negative độc lập xác nhận sau release; không biến inferred failure thành product claim. Giữ actual same-graph stable token, stale external-change0delta, original business-error assertions và immutable replay; report rõ source-level correction, coder không chạy diagnostics/tests.

## 7. Exact15 write targets và delivery

Chỉ14 **existing source/test files** sau; không new source, sourceinventory273 giữ nguyên/protected259. Existing SQL1–15/pure/fixture20/readiness/reports01/reviewinputs/controller/guard/credentials ngoài scope:

1. `src/kho_tri_thuc/ha_tang/pg_migrations.py` — chỉ16.
2. `src/kho_tri_thuc/k2/lien_ket_chung.py`
3. `src/kho_tri_thuc/k2/kho_so_luong.py`
4. `src/kho_tri_thuc/k2/hoa_don.py`
5. `src/kho_tri_thuc/k2/quyen.py`
6. `src/kho_tri_thuc/k2/crm_khoi_dong.py`
7. `src/kho_tri_thuc/k2/nguon_chung.py`
8. `src/kho_tri_thuc/giao_dien/server.py`
9. `src/kho_tri_thuc/giao_dien/assets/app.js`
10. `src/kho_tri_thuc/giao_dien/assets/index.html`
11. `src/kho_tri_thuc/k2/l11_demo.py`
12. `tests/test_l11_migrations.py`
13. `tests/test_l11_k2.py`
14. `tests/test_l11_http.py`
15. **CreateNew** `docs/BAO-CAO-L11-QUANTITY-02.md`; không sửa report01 hoặc review docs.

Final report nêu exact changes, generated1–15 preservation,11entrypoint DB protocol, three quantities/actualfield/domain guards, preview/privacy/coverage/parent/UI closures, missing controls và tất cả selftests UNRUN. Không tự viết terminal/root acceptance hoặc claim GUI/fullL11/full33 complete. Root FULL final source/tests/pins → actual terminal receipt/freeze clean → independent runtime release riêng; dispatch authority chỉ là actual dispatcher invocation, không suy từ handoff; runtime cần release riêng.
