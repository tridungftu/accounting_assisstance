# L11 HTTP/UI03 — independent STATIC review

Reviewed actual CODE_ONLY03 terminal handle82131/chunk9729ca/exit0, frozen `var/codex-dieu-phoi/l11-quantity03-handoff-20261020-005748-609-00361db3/frozen`; source273 manifest `09d6589358501f7feea479c0e277bdfde008cdd02d1328c78bce0bba8447914e`, freeze receipt `c9aef1848afea649505418dc483c6c29050355ac65641b8889d72f7660beedbb`. Scope-clean is not product acceptance. Handoff03 `27af004c1fa49a33d0c3936ee20dfa01b35fdfd83d8b2a6378888153bbd86d06` §B is the oracle.

FULL-read actual JS diff82 lines and final L11 slice1178–1461, HTTP diff16 and final HTTP test288 lines; coder report03 read as claims. Rebound unchanged server/service/HTML by exact SHA to the prior FULL static review; no new HTTP/service implementation was inferred from coder claims. No product import, test, JS/Node/VM, SQL, HTTP, browser, provisioning or process run by this reviewer. All behavioral statements below are static; independent root async execution is separate evidence.

| Frozen file | Exact SHA256 |
|---|---|
| `src/kho_tri_thuc/giao_dien/assets/app.js` | `77f9c1b56509fc00e02788667cec5eb3e98206f3e4357a1a88f4754f21ef1425` |
| `tests/test_l11_http.py` | `6d42dad7611829c7d206703a43349ca56a5567b6e51ba5233409b5a497bf7fe4` |
| `src/kho_tri_thuc/giao_dien/server.py` | `218f50b0ff194f63c680f6f4574845c5348c8f7c91bcc3a864e1454d24deb0e3` |
| `src/kho_tri_thuc/k2/kho_so_luong.py` | `6bcc353924eaebf4cd9c28433b8c9fddee69e5ed36bfafbc89ce558432d2b094` |
| `src/kho_tri_thuc/giao_dien/assets/index.html` | `44ed8c523a9fae5191d84980ae0f72bc2fcbc1e29be911e138cae6195550370d` |
| `docs/BAO-CAO-L11-QUANTITY-03.md` | `dfb1df9f2a8e3ed25846401390954400ce67d89afc06a65b40c58d80c329c225` |

## UI03-1 — P2: FILE refresh can still replace the form after its original context became invalid

Final JS `l11Act:1205–1207` checks the captured FILE predicate only **after** `await l11Load()`. Inside that awaited load, `1422–1424` checks only role epoch/GET generation and then assigns DTO/render; it does not check the caller's original form/pair predicate. `l11Render:1327` invokes `l11RenderCap`; `1366–1373,1393` recreate pair/amount controls and clear preview.

Concrete static schedule: a nonempty FILE click starts its POST and own aggregate refresh; while that GET is pending, the same actor changes pair or quantity (form epoch advances); its response is still the newest GET and same role epoch, so `1424` renders/replaces those newer controls. Only afterwards does `1207` see the invalid original form predicate and suppress the FILE continuation. This is **not** a remaining automatic-download counterexample: the download now has the right predicate. It is an earlier DOM effect in the invalidated continuation, contrary to §B's check-before-DOM requirement. Expected control: preserve the new selection/input/preview and emit no old FILE status/download while allowing a separately requested valid refresh. Bind the actual handler test to the chosen DOM behavior; do not mistake substring tests or zero clicks alone for that control. Root async/GUI reproduction remains separate.

## Structural closures and limits

- The old FILE download finding is structurally addressed: `1346–1350` captures form epoch, parent and basis and passes the real predicate into `l11Act`; `1206` retains the own-refresh ticket in the returned fence. A later GET changes `l11Gen`, so an old Blob completion no longer passes. `1218–1221` rechecks after headers and Blob before actual click. Role invalidation and late POST-error suppression remain guarded (`1198–1211`). These are static closures, not measured async PASS.
- Newest-GET rendering is guarded both response orders (`1419–1424`); candidate facts now include native byte length (`1247`). Existing facts/H/raw length before CFO approval, proof GET/current source filtering, BOTH READ plus `M5_FILE_SOAT`, owner FILE registry/path checks, one-RR aggregate and source-only FILE byte preservation are unchanged from02. This review does not newly prove SQL rights/revocation races or source/proof semantic admission.
- HTTP test setup remains a fresh retained `kho_test_l11http_*` DB/new random app_web login, actual source capture/map/route/review and local127.0.0.1 server, with no DROP/DELETE/file cleanup. It needs the root's reviewed credential/loopback/no-delete release. Environment patch is configuration only. No new runtime safety blocker in the03 delta.
- HTTP assertions keep actual nonempty proof facts, unique full-reference approval keys, exact replay/stale/conflict codes, preview0write, confirm/undo and FILE payload SHA (`175–272`). The03 addition (`280–283`) only asserts source strings/native length; it explicitly does **not** execute JS. Existing count-only `dem()` does not prove whole-row/sequence/file invariance, and HTTP two methods do not cover the remaining four causal schedules. No money/M9/sourceapp changes were made by this reviewer.

Runtime status for this review: **UNRUN**. No overall L11/full33 acceptance claimed.
