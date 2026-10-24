# L11 HTTP/UI 01 — independent FINAL STATIC review

19/10/2026. **STATIC_ONLY / RUNTIME_UNRUN.** Claude4168 actual terminal316fbb; frozen273 manifest `22c58d26171217b869dca4e74d483feb7313f5e1f4883e4166ea15e900c2bccf`, folder `var/codex-dieu-phoi/l11-quantity01-handoff-20261019-233416-872-7d867124/frozen`. Compared all server/JS/HTML deltas against before-l11 source269; FULL read new HTTP test256 and new JS1178–1415, plus selected actual service/SQL/role callpaths. No imports, AST/compile, JS/HTTP/tests/browser/SQL/server/process or product edits. Handoff v5/public CODE_ONLY is the oracle, not coder report.

| Input | SHA256 |
|---|---|
| server.py1177 | 1924712cc51c5c55354f0b1d24b60c539593d50ec30cd9b686c8fdd242f17ec7 |
| assets/app.js1415 | 50e360d4d37d18aaf86cfcf65ddb1ff5ef98ed46ea5670cee154aa0f67d52976 |
| assets/index.html215 | 11ee4c1fe452d4dbec614dca3aa250a6b74021a62c3bc880e7f63340742b8e16 |
| tests/test_l11_http.py256 | b22bf6d059987b0502b0c06ccccb6857a3ad4a0bcf1830b0ba2df946f36ff0d4 |
| kho_so_luong.py1002 | 306660bf1aaae103f60c63268fe8375e7292056cb94f181adf6a7c2dc9cfcf2a |
| l11_demo.py258 | 522f05d9a7e35dafa3f684dabe6f41d83c7334e55c69827f29f6c33068ef6191 |
| pg_migrations.py8202 selected anchors only | 92562517a53a233cf54090cd6b6f809c0d9419846f53be31833bb67c1ffbc057 |

## Findings

**U01 — P2, automatic FILE download loses the original epoch after awaited refresh.** JS1192–1201 checks epoch/actor before `await l11Load()`, then returns the old operation result without another fence. FILE callback1306–1309 invokes `l11Tai(r.id)`; that function1207–1209 captures the *current* epoch/actor, so it re-arms the old result. Concrete ordering: LINK FILE POST succeeds; its follow-up GET is pending; user changes L11 role (1383–1388 clears epoch), newer role GET wins; old GET is discarded1377 but old `l11Act` still returns lo; automatic download runs in the new role. Current DB download guards can deny unauthorized roles; this finding is a UI fence violation, not a claim of unauthorized DB/file disclosure. Keep the original operation fence through every await and the automatic-download callback. Verify both role-switch orders and pair/form invalidation with a nonempty downloaded-file positive; no old-response click/download after invalidation.

**U02 — P2, CFO cannot inspect raw-derived facts/hash/length before approving.** Candidate renderer JS1244–1251 displays only ref/revision/configured kind/state/issues and approval input/button. Actual SQL6790–6794 returns `raw_sha256,byte_length,facts`; none is rendered. Ratio/items appear only in the *already approved* table1254–1263. Thus the required receive→facts/issues→CFO approve path cannot show the ratio/domain/native bindings being approved. Add readable candidate details from the existing scoped DTO (including exact raw H/length and relevant units/ratio/domain/source bindings), without manual UUID/factor inputs or extra raw access for LINK. UI and HTTP DTO assertions must demonstrate those facts before the actual approve button.

**U03 — P2, required proof GET endpoint is absent.** Handoff §6 specifies GET `/api/m5/l11/proof`. Server957–961 handles only aggregate `/api/m5/l11`; authenticated GET proof falls through972–974 to `m5_get("l11/proof")`, which495–507 raises NOT_FOUND, classified400 at1141–1142. POST routes exist. Tests use aggregate GET only (135–140/161ff), so do not cover the promised endpoint. Add the finite current-scope proof-read route using the existing service and both-read/raw-source guards; retain aggregate page behavior.

**U04 — P2, aggregate page is assembled from two independent RR snapshots.** Server606 calls `l11_tong_quan`, then612 calls `l11_bang_chung`; these independently open/close RR at kho_so_luong900 and840. The page combines approved proofs/lines/encoding/FILE tokens from A with candidates/scope from B. An independent CFO proof transition between calls can yield a candidate with a new proof ID/state while the page's approved-proof picker still omits it, or display an old approved proof with newer candidate state. The app mutation_lock serializes this one HTTP process, not independent DB connections. Return the aggregate visible DTO+tokens from one owned RR snapshot using shared internal readers, preserving outer-TX refusal; separate standalone proof GET may own its own RR. This is a static coherence-contract gap; no token bypass or runtime race is claimed.

These four findings are not added to other agents' SQL/service findings as a unique aggregate count.

## Positive coverage and practical limits

- Exact two-role selector server563–569/603–604, no all-MO_PHONG prefix. JS pickers derive IDs from server DTO; quantities remain strings, FileReader uses actual ArrayBuffer helper728–730. No browser factor/PN/owner/PROVEN accepted via new body paths; profile/config resolves purpose.
- Actual buttons present for upload/template/approve/revoke/encoding/preview/confirm/undo/FILE; four native/pool quantities and units are rendered1354–1367. Blocked budget helper1221 currently abbreviates confirmed/held into used; this is a presentation limitation, not a conservation proof.
- Typed line/encoding/parent/FILE basis in `l11_tong_quan`901–925 itself shares one RR and preview887–889 uses RR; U04 concerns server aggregation across the second independent service call. GET generations and preview epoch/form fences1373–1380/1345–1350 exist; U01 concerns the additional post-refresh await.
- Cross FILE service944–966 checks current both-read+FILE before receipt replay/write, uses same configured owner TX and server-derived L11_QUANTITY stage/mode. Shared download720–742 applies ordinary RLS then current mode-specific rights, exact m5-xuat/H.xlsx and byte SHA/length. Selected SQL7639–7657 checks FILE before receipt;7754–7780 conditions app_web and legacy lo policies. Old source-only export route549–553 and format remain separate. These are static positives, not a completed direct-SQL/RLS race review.
- All new HTML/JS/server deltas reviewed are quantity/proof/UI routing; no money/stock engine or M9 edits in this slice. Unchanged historical source/UI presence is not acceptance of those modules.

## HTTP test safety and oracle strength

FULL256 lines: fresh random kho_test_l11http DB59–61 and new random app_web member68–70; synthetic fixtures only; no DROP/DELETE/file cleanup. Environment patch only binds actual app/admin connections71–72; it is not an authorization mock. Source setup83–109 uses actual M2/M5 intake/map/route/source-review services, and proof/encoding/confirm/undo are actual HTTP actions. Temp dirs/DB/role retained. Requires root's already guarded loopback-admin bridge; test code alone is not a safe arbitrary ADMIN_DSN validator.

Positive and exact original-body replay215–218 plus confirm-after-undo240–241 are meaningful. FILE231–232 reads actual response bytes and checks SHA, stronger than saved-bytes-only; it does not inspect workbook cells/formulas or prove old source-file bytes unchanged. Preview count observer145–154/202–206 is table counts only, not all-row/hash/sequence/file invariance. Download-denial233 accepts400 or403 without an exact scope code; no permission-revocation-before-replay/download test. Authority-shape/path denial171–174 allows either400/403. Both are bounded denial checks, not exact-code proofs. Asset test243–252 checks served strings and explicitly does not prove actual JS fences/pickers/browser behavior. No U01–U04 behavioral tests, causal races, GUI or runtime execution were performed in this review.

tearDown114–119 closes setup connections/server/thread but not cached LocalApp service connections; the owned root child/timeout must bound process lifetime, and GUI starter must explicitly close actual caches. Class-setup failure may skip tearDown; retained resources remain evidence, never cleanup. No runtime PASS or L11/full33 completion is concluded.
