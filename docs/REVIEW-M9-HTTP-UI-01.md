# M9 — root review HTTP/UI/file trước host

19/10/2026. **HANDOFF01_NOT_ACCEPTED / STATIC_HTTP_UI / INDEPENDENT_PARSER_EXECUTED_ONLY.** Claude handle88862 đã terminal exit0, ClaudeExit0, result.is_error=false. Whole freeze143 tại `var/codex-dieu-phoi/kiem-chung-20261018-101441/m9-typed01-handoff-20261019-111048-752/`; manifest `19c3476cb01fde17ec0382c16c3537813cec804b725e1bcd6eb730e5db8da276`. Không lấy report18/18 của coder làm nghiệm thu. Owned web đã dừng trước lượt M9; chưa nâng DB DEMO root từ12, chưa launcher/HTTP/GUI M9.

## 1. Final API đã đọc

Root đọc frozen `giao_dien/server.py` các vùng135–235,318–418,450–530,535–548,592–625,680–748; `assets/app.js`1–40,250–269,499–673; HTML M9 section80–94; service receive100–133/export746–811/read814–943. SHA server `f2a700522a3c9ead770afe2002e0edcfd2fee1eb7e22a9de9c365eaec72abf4b`, JS `0227b29ed32c2ea87e479298645120af3643c400e8ff398cc5370ecb2c97f13a`, HTML `3910da9a9d850d2bb2338bad2ddc56352ad6257426bc123e0cf28c3fa10d51da`, vay service `00996e3edadab00e311af5dcfb980f14f4faf5ef746e672338be857811a8ffbf`.

Actual public contract: GET `/api/m9?ngay=<date>&biet_den=<instant>`; POST `/api/m9/{danh-tinh,mau,anh-xa,anh-xa/anh-huong,anh-xa/dong,lap,pham-vi,kiem,duyet,duyet-v4,tu-choi,m1-sao-ke,goi-y,xem-truoc,xac-nhan,go,file-soat}`; GET `/api/m9/file-soat/<id>`. Map body uses `snapshot,phap_nhan` ma at stage, `cong_ty,nguon,dich` at mapping; allocation `[{dich:<logical-target UUID>,so_tien:<minor text>}]`, receipt `khoa`, preview `xem_truoc_token`. These are source observations, no actual request executed by root.

Positive design reused: one CRM connection/service identity, cookie HttpOnly/SameSite Strict, token and origin checks, app mutation_lock, MO identity validation, server capability checks, strings via textContent and amount strings, preview/confirm separation, raw bytes content-addressed before parser, file registry and hash-checked download. M1 import/project/proof is reused instead of generating BANK from loan source. None substitutes ordinary-role DB/protected/race/source-provenance evidence.

## 2. Findings

| ID | Severity / final trigger | Concrete effect and required correction |
|---|---|---|
| H-R1 | P1 functional completeness — server366–395,725–728; JS553–554; HTML87–88 | Only `mau` calls service `nhan_mau`, constructing built-in fixtures. `VayK2.nhan_tep:100` exists but has no HTTP/file-picker route. Independent native JSON/profile cannot traverse the delivered app; legacy general file cabinet does not call this typed intake. Add actual supported file intake/diagnostic route+button reusing this method/common store/profile authority and bounded envelope/body/rights; no source app execution or Google. Built-in samples remain positive controls. Raw-invalid/unmapped/partial must be retained and visible rather than rejected before storage solely because no accounting PN/date. |
| H-R2 | P2 currency display — JS636–638,657–658; vnd255–260 | M9 links and preview amount/capacity/remaining use formatter always adding VND. Main table uses currency-aware `tien9`; the preview/link branch ignores the pinned currency/scale. A supported USD minor100 preview must not render100 VND. Current BANK proof only VND is an implementation limit, not permission to mislabel retained/blocked native units. Bind response currency/scale to each displayed amount, keep exact text and NULL0. No FX calculation. |
| H-R3 | P2 historical UI — JS664–670 vs server344–355 | Server exposes biet_den, UI only sends ngay. Together with service known-cutoff gaps in separate review, user cannot select/inspect knowledge time. Once service genuinely enforces cutoff throughout, expose/select it and make current vs historical state clear; historical view must not silently drive current mutation/preview token. Do not solve by hiding the source cutoff gate or backdating receipt. |

File export actual implementation has seven sheets, string amounts and registry/hash checks; no bytes/cells/HTTP acceptance yet. Repeated `file-soat` creates XLSX/registry through INSERT, so future H08 observer must export once then reuse/download existing ID for restart, not assume export method idempotent. Undo is whole parent in current API; partial-undo requirement needs explicit scoped design, not silently equated with whole-parent undo.

## 3. Independent narrow parser execution

Root released **only pure frozen adapter import**, no SQL/HTTP/launcher, under original guard a517c535… + no-bytecode. Full143 product and18 corpus file hashes checked before/after unchanged. Helper `var/codex-dieu-phoi/m9-root-parser-probe02.py` SHA `a00866a97d8ef9cd6ae8dcb06a7edd722b563a10a06e641938d0f2ca7a10efc4`; result `var/codex-dieu-phoi/m9-root-parser-result-1792383339624832100/result.json`: **13 criteria,8PASS,5FAIL**,0SQL/0HTTP/0host.

- Four precision criteria fail: native integer1, USD decimal0.1, rate7, and native S01 graph all become PROVEN without independent field/domain/input-path precision proof. Source contract§3.1 explicitly says safe integer/15digits/payload precision cannot prove pre-Number source fidelity. Exact text capability remains legitimate under reviewed transport proof; do not ban large exact int64 or default all real native fields to approved DEMO proof.
- Ambiguous-company criterion fails: duplicate maKV under source companiesA/B causes source children AMBIGUOUS_COMPANY, yet both parent graphs have empty blockers after filtering unresolved children out. This runtime observation concerns parser graph only; SQL full approval bypass requires separate evidence. Retain raw parents/children and block affected aggregate eligibility with explicit unresolved relation.
- Positive controls pass: exact text9007199254740993, NULL distinct text0, bool rejection, native shape1loan/2draw/3rates/2principal schedules, S10 affected **A1 draw** UNPROVEN, root-profile mismatch reject. These are scoped parser controls, not full19 source integration/known-time/typed approval PASS.

First probe01 retained a harness mistake comparing S10 loan-header precision instead of the A1 draw containing the large number; that raw failure is retained and not a product finding. Probe02 corrects only field mapping and adds the independently specified two-company ambiguous-child controls, without product/corpus/oracle mutation. No duplicated pass aggregation across attempts.

## 4. Disposition

Do not start host to call this accepted. Combine actual SQL/service/target findings into same-Claude-session repair, then authoritative new terminal+whole freeze; bind actual final API before independent fresh/upgrade/ordinary-role/source19/budget/race/HTTP/file/host checks. Public status M9 remains CODED_FIRST_PASS_REVIEW_FAILED, not complete. Full M0–M10/9receivers/L1–L12 and all prior module bindings remain the program; this repair is shared-core work required by those consumers.
