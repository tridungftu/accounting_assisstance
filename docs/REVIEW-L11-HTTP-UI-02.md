# L11 repair02 HTTP/UI — independent FINAL STATIC review

**STATIC_ONLY / RUNTIME_UNRUN / RESIDUAL_REPAIR_REQUIRED.** Actual Claude47839 terminal60f60e; root freeze23b22f: source273 manifest `81abd25aad43aed3b0e991c91c080b86da354662f2a5f3721970bf1bcb750e2f`, receipt `96f3a7497c3a3833a18a37076640599050eb697f48f53a643b2e396716f37fb9`, folder `var/codex-dieu-phoi/l11-quantity02-handoff-20261020-003103-912-61b0d271/frozen`. Compared all server/service/JS/HTML deltas against frozen01; FULL final JS1178–1454, HTTP test287, report02 claims; selected actual SQL rights/proof/FILE anchors. No product imports/AST/compile/tests/SQL/HTTP/Node/JS/browser/process or product edits.

| Input | SHA256 |
|---|---|
| server.py1184 | 218f50b0ff194f63c680f6f4574845c5348c8f7c91bcc3a864e1454d24deb0e3 |
| app.js1454 | c0152bfe9443cba30e898654efb3a368c1dd60ab785fa956c3c2d1563b0c48b5 |
| index.html215 | 44ed8c523a9fae5191d84980ae0f72bc2fcbc1e29be911e138cae6195550370d |
| kho_so_luong.py1035 | 6bcc353924eaebf4cd9c28433b8c9fddee69e5ed36bfafbc89ce558432d2b094 |
| test_l11_http.py287 | 1e4ebac38f6514118e5a640dc6dffc015e6f5cc5468531d9dc8a0f359ba5ed34 |
| pg_migrations.py selected anchors only | d3823958ae459070be03b6310255657adc2d66d27b60277725bee7b46752b7d8 |
| report02 — claims, not runtime evidence | fa4ad8a8d7fe322588c308d0e1792595613a51d0be1f0bf57874f524fabd4f06 |

## UI02-01 — P2: FILE still omits form/pair and download-lifetime generation fences

JS1194 defaults `conHieuLuc=()=>true`; returned fence1196 checks epoch/actor plus that predicate. FILE1341–1343 supplies no fourth predicate/captured form epoch. Its `conCap`1340 only checks that the same parent ID remains in the list. Pair/input changes1359/1366 increment **l11FormEpoch**, not l11Epoch. Concrete counterexample: FILE POST succeeds→follow-up GET pending→user changes pair/amount→GET returns with same parent→default fence remains true→automatic file GET/click still runs. Or change pair/form while Blob awaits1215: final guard1216 still passes. Backend current rights/immutable file checks remain; this is a stale-UI continuation issue, not a DB disclosure claim.

Generation is also compared only once1204. The returned fence does not retain that generation; a newer GET can finish while Blob is pending and the old result still clicks when it resolves (same actor/parent). Carry the original operation context through the actual download/click, including captured form/pair and applicable generation, and suppress old continuation/status when invalidated. Review02 report§6 claim “đổi vai/cặp/form thì bỏ kết quả cũ” is therefore broader than the implemented FILE wiring. Existing static asset substring test276–283 cannot close this. Prepared private async schedules A05/A06/A09/A10 cover the form/pair orders; generation-during-Blob needs an additive schedule once actual binding is reviewed. None has run.

## Structural closures and limits

- Original role-switch/post-refresh gap U01 is structurally corrected:1195–1205 preserves original epoch/actor across awaited refresh;1211–1219 requires the passed original fence before request and after Blob. GET1411–1419 checks both epoch and latest generation; older A is discarded whether A or B responds first. Role handler1422–1427 clears epoch before its POST. These positives do not close UI02-01.
- Candidate facts before approve U02 is structurally corrected:1228–1249 renders scoped domain/native/unit/ratio/bindings;1273–1283 adds actual raw H/length, original/effective coverage, errors and facts before the approval column. SQL6940–6951 still requires BOTH READ + current READ_SOURCE for raw candidate facts. Display is a readable summary, not a new authority channel; browser rendering/actual approval remain UNRUN.
- Required GET proof U03 exists at server615–618/966–968, uses actual service837–854 with its own RR and source-cap scope filtering. HTTP test179–190 asserts H/length/domain/ratio before approve;222–224 asserts LINK sees approved only, no candidate/source scope. No HTTP/auth PASS is claimed from source.
- Two-domain-snapshot U04 is structurally corrected: server607 calls only `l11_trang`; service859–870 opens one `_tx_doc` around both internal proof and quantity readers. All domain SELECTs/token queries843–854/926–966 use that connection/snapshot; `_tx_doc`100–111 refuses outer transactions. Identity/cap DTO is loaded before RR and selector metadata server603 is separate; this report does not assert a single-instant role-revocation race proof. Root's second-owner-commit coherence control remains needed.
- Actual cross FILE service968–997 remains same owner TX; SQL7930–7948 current FILE guard precedes replay. Shared download720–742 retains current mode-specific rights/exact m5-xuat/H.xlsx/hash/length checks. All service changes are in L11 readers/cross workbook: original source-only M5 exporter/workbook/download branches and legacy L11_THONG_BAO bytes are unchanged against frozen01. Actual old-file byte invariance still requires runtime hash comparison.
- HTTP test FULL287 remains fresh retained DEMO/ordinary app + configured owner, no DROP/DELETE/cleanup. It now uses full-reference approve keys, exact domain error assertions, explicit same-body approve replay and deliberate cross-body key conflict202–211. It reads actual FILE bytes/hash259–261; no cells/formulas or async handlers are executed. Counts observer148–157 is not an all-row/sequence/file oracle. Test setup/teardown still needs root-owned child/watchdog and explicit GUI cache closure; no causal/browser/partial-revocation acceptance.

Private async definitions remain NOT_BOUND/releasefalse. Because UI02-01 remains concrete, this review does not create a runnable final02 adapter or claim all eleven async controls pass. Preserve code01 failures/report and future source pins; no L11/full33 acceptance follows.
