# M5 reader thuần — sửa 02

**19/10/2026 · READY_FOR_ROOT_REVIEW; chưa dispatch/chưa nghiệm thu.** Tiếp tục session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`, chỉ sửa các counterexamples của gói reader; không mở core/API/UI/Store/K2/M9/source app.

## 1. Căn cứ và bằng chứng đã chạy

Reader01 terminal0,62turns; frozen191 manifest SHA `2074981cec804c709b595d491efa5d21c88143f8241e6a821ae36e31e08a8028`. Reader SHA `0e886ca8314f940421adcb96064ba92fd916927c91cbb8dfefd6218e61dd44de`; test SHA `51addec2585fede9382ed681dd311fef6290c0bbdd33d48a469f0607016ba215`; report01 SHA `87deef7983790b66544817c354e3534794f04e1c9589fa6834ff9fc9f209c161`.

Root actual coder-suite40/40 PASS, nhưng independent probe03 dừng ở HISTORY_REF_ACCEPTED sau14groups; targeted17 kiểm tiếp có **2 positive PASS+15 negative FAIL,0setup**, source191 nguyên. Aggregate targeted SHA `07a396d04aa7e408c3419866fb08a7fa6568f194187c9b7ffdbde0c3bb7bc9fd`: coder không đọc `var`; kết quả sanitized được nêu đủ bên dưới. Không coi40test xanh là đạt reader khi counterexamples này còn lỗi.

Giữ nội dung `docs/GIAO-CODE-M5-READER-THUC-HIEN-01.md` SHA `dad1cbe80cbd9e601296211454c02edc1cb3d708127dd03dea035c96b1f74e33`; DTO03 `docs/M5-HOP-DONG-DTO-33.json` SHA `d1b3577074794d8d09af2d5ccb58aa0caa47540f7ccaf3e62475599fb6e6f73f`; fingerprint SHA `7fcf0e3d24564ae129dabb615791097640609aaaa6d016bcd6121c24062e02bf`; fixtures43 manifest `5d680a1cd4a691fba5d6eca7056bdc94f9fbf558b80e2415d97f9808215c8e66` giữ nguyên. Review sanitized `docs/REVIEW-M5-READER-01.md` SHA `9f915aacee251bf5f1ac9fd7d00f891858b73707ada614ae72c86d78b2b1262b` chốt sáu nhóm15 negatives, không phải15 P1 độc lập.

## 2. Đúng ba write targets

- `src/kho_tri_thuc/nguon/kho_10.py`
- `tests/test_kho_10.py`
- **Mới:** `docs/BAO-CAO-M5-READER-02.md`

Không sửa báo cáo01/tests fixtures/oracle/expected/DTO/contracts/reuse files, dependencies/Store/intake/server/ha_tang/K2/DB/schema/config/guard/runner/settings/dispatch/public ledgers. Không thêm helper product/file khác. Không vận hành/source/tracking/M9; không đọc source app/Google/real rows/var/.env/secret.

## 3. Sáu nhóm phải sửa, đủ15 counterexamples

| Nhóm / actual cases lỗi | Sửa tại điểm quyết định và expected | Positive counterpart giữ nguyên |
|---|---|---|
| Status: STATUS_OBJECT, STATUS_ARRAY gây TypeError ở SOURCE_STATE.get; MISSING_LoaiPhieu, MISSING_TrangThai vẫn semantic/request; UNMAPPED_STATUS_HOLD hiện needs_review=False | Validate required `LoaiPhieu`/`TrangThai` exact nonempty text, cùng các required header khác, trước lookup/hash. Object/array/missing/null/invalid required field giữ candidate+issue, semantic/request NULL, không crash. Status text chưa map giữ observed fact nhưng phải explicit issue/HOLD/needs_review=True; không suy approved/eligible từ status chưa biết | K01 `Đã duyệt` vẫn golden; K04 đảo; unknown status không bị tự đổi thành `Đã duyệt` |
| Finite decimal graph: NONDECIMAL_QUANTITY_NaN, NONDECIMAL_QUANTITY_abc hiện vẫn semantic/request H | Validate scalar quantity **finite decimal syntax trước semantic envelope**, text invalid giữ exact raw/text+issue và semantic/request NULL; không chỉ thêm measurement issue sau H. Không nhận audit-tag object/boolean. Decimal không qua float; giữ null≠0, lexical text/type/order | Finite decimal text, zero/fraction/exponent/raw NUMBER lexical vẫn giữ đúng observed facts; Number unproven không được chuyển thành text exact |
| Actual encoding: ACTUAL_NUMBER_CONTRADICTS_EXACT_TEXT hiện requestH+1 sibling normalized | Resolved declaration exact-text nhưng actual NUMBER mâu thuẫn encoding=>KHO_CONTEXT_PROOF_MISMATCH/HOLD, request NULL và **toàn candidate normalized quantity NULL**, không giữ sibling normalization dưới cùng contradictory measurement context. Giữ raw/native/semantic nếu graph hợp lệ | K01 coherent exact-text vẫn normalize; K08 facts=None vẫn requestH+UNPROVEN/HOLD+normalizedNULL: không proof-gate request cho unknowns |
| History graph: HISTORY_accepted, HISTORY_receipt, HISTORY_raw_null, HISTORY_master_null, HISTORY_duplicate_ref hiện đều stateKNOWN | Validate unique content reference IDs, exact same logical tuple; accepted/receipt `content_reference_id` phải resolve duy nhất và content digest khớp đúng referenced row (không chỉ thuộc seen set). Referenced raw/master/semantic digests NULL/NOT_BOUND/bad64hex=>HISTORY_UNBOUND/UNKNOWN; orphan/conflicting/duplicate ref=>HISTORY_MISMATCH/UNKNOWN. UNKNOWN không báo replay/fresh/first/ABA như kết luận KNOWN. Không sửa/rebind history hoặc raw→semantic | Root K03 linked replay, K04 priorA, K05 acceptedB/seenA+B và K09 oldbasis giữ đúng classification; missing summary khác explicit-empty |
| Container: EXPLICIT_NULL_CAPTURE_ERRORS hiện constructor chấp nhận như[] | `reported_capture_errors` vắng mặc định empty; **hiện diện nhưng null** là malformed array container=>DataError KHO_FIELD_TYPE. Không silent-coerce null→[]; không thay quy tắc business refs nullable | Omitted field và explicit[] hợp lệ; business refs missing/null vẫn candidateHOLD theo DTO |
| Digest: EXACT_DIGEST_TRAILING_NEWLINE hiện constructor chấp nhận | Dùng exact fullmatch64 lowercase hex cho mọi Digest validation; không regex `$` cho phép newline cuối. Context malformed digest từ chối; history digest string invalid/unbound giữ UNKNOWN/HOLD khi contract cho nullable audit value, tuyệt đối không valid64/replay. Không strip/lowercase sửa input | Exact64 lowercase hex hợp lệ; null business ref giữ đúng nullable semantics; raw SHA thực không đổi |

`content_reference_id` là optional: absent/NULL không bắt lookup hoặc tự bịa ref; chỉ ref hiện diện khácNULL phải resolve unique và khớp digest/logical; mọi ContentReference row đã cung cấp vẫn unique/fully-bound, và valid minimal summary/replay không có optional ref phải giữ positive control.

## 4. Regression và thực thi sau root dispatch

Giữ40baseline và golden independent, bổ sung15 negatives trên cùng positive counterparts; tests tạo mutation DEMO **trong memory**, không sửa fixture/expected. Assert exact outcomes (candidate/no exception, digest NULL hay H đúng nhánh, normalized toàn bộNULL khi contradiction, history UNKNOWN/reasons, constructor rejection đúng container/fullmatch); không generic `needs_review` che graph/history sai, không PASS nhờ exception/setup/skip. Token exponent/trailing-zero/negative-zero giữ bytes và lexical text; deepimmutability/raw hashes/replay/ABA/partial/UOM continuity giữ controls01.

Chỉ exact command đã release dưới guard root:

```text
python -X utf8 -m unittest discover -s tests -p test_kho_10.py
```

Không command khác, PG/SQL/Store/HTTP/API/UI/Google/cloud/host/launcher/git/pip/env/realstore. Bash denied=>UNRUN và dừng đường đó, không thay policy/shell. Không xóa/move/cleanup file/temp/DB/role/attempt. Kết thúc CLI sau report02 để root freeze/review/rerun independently; không tự nghiệm thu M5/33 hoặc mở việc khác. Báo exact PASS/FAIL/ERROR/SKIP/UNRUN và giới hạn pure-reader; full M5/L11/core/UI tiếp tục sau gói này.
