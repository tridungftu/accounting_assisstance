# Review độc lập M5 reader 01

**19/10/2026 · CHƯA NGHIỆM THU · cần sửa sáu nhóm dưới đây.** Unit tests do coder viết đều qua; kiểm tra độc lập vẫn phát hiện lỗi. Kết quả chỉ thuộc reader thuần, chưa là M5/L11/core/UI/production acceptance.

## Bản được kiểm và bằng chứng

- Claude đã kết thúc thực: handle `88260`, exit `0`, tool chunk `0b73be`, session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`. Receipt `terminal-confirmation.json` SHA256 `e05fb810bc6aeac0141b3cf807cb5947bb8147ed4c5e688905694ab3b341e1a4`.
- Frozen root: `var/codex-dieu-phoi/kiem-chung-20261018-101441/m5-reader01-handoff-20261019-144223-879/frozen`. Manifest anh em `source-hashes.json`: **191 files**, SHA256 `2074981cec804c709b595d491efa5d21c88143f8241e6a821ae36e31e08a8028`.
- Reader `src/kho_tri_thuc/nguon/kho_10.py`: **976 dòng**, SHA256 `0e886ca8314f940421adcb96064ba92fd916927c91cbb8dfefd6218e61dd44de`; các line anchors dưới đây thuộc đúng bản frozen này. Tests `tests/test_kho_10.py`: SHA256 `51addec2585fede9382ed681dd311fef6290c0bbdd33d48a469f0607016ba215`.
- Fixture manifest `tests/fixtures/kho_10/manifest.json`: SHA256 `5d680a1cd4a691fba5d6eca7056bdc94f9fbf558b80e2415d97f9808215c8e66`, pin 42 files con và chính manifest, tổng **43 inputs**. Native/oracle/context/history là DEMO do root chuẩn bị độc lập trước code.

| Kiểm tra root đã thực hiện | Kết quả thực | Evidence JSON / SHA256 |
|---|---|---|
| Coder-authored pure unit suite | **40 PASS, 0 FAIL, 0 ERROR, 0 SKIP**; source191 không đổi | `var/codex-dieu-phoi/m5-root-unit01-b0e8f81dfb2e/summary.json` / `b8d4fe6130bb128477f049500c493856b6b55279210bef47c665d62d8840b944` |
| Independent probe03, tool `41c723` | **FAIL**, hoàn tất 14 nhóm trước khi dừng ở `HISTORY_REF_ACCEPTED`; source191/input43 không đổi | `var/codex-dieu-phoi/m5-reader-independent03-result-20261019-1444.json` / `e5cfcf2f708b3cad4e093f351504af403e6687f4412abfb23536a27b25669db6` |
| Independent targeted counterexamples | **17 ca: 2 PASS, 15 FAIL, 0 setup errors**; source191 không đổi | `var/codex-dieu-phoi/m5-targeted01-556daabf1c93.json` / `07a396d04aa7e408c3419866fb08a7fa6568f194187c9b7ffdbde0c3bb7bc9fd` |

Probe03 SHA256 `ca37956e327ada7d6e1d34ce0fa4090fc592a0d92a6d77d01dbf556ab8d7469b` dùng golden raw/semantic/request digests đã pin; không lấy coder tests hoặc công thức hash của product làm expected. Mười ca `K01–K10`, replay `K03`, reversed `K04`, ABA hold `K05` và fresh receipt đã qua trước điểm dừng. Những controls nằm sau điểm dừng **chưa chạy trong probe03**; không suy chúng PASS từ unit suite. Targeted17 là lần kiểm độc lập riêng.

## Sáu nhóm cần sửa

**R1 — Header/status: năm negative cases.** `STATUS_OBJECT` và `STATUS_ARRAY` thực tế ném `TypeError`: reader đã ghi field issue ở dòng 658–661 nhưng vẫn dùng giá trị không hashable trong `SOURCE_STATE.get` tại **665**. `MISSING_LoaiPhieu` và `MISSING_TrangThai` vẫn có semantic/request digests, không issue: checks 631–640 chỉ bắt hai required IDs, không kiểm đủ required header. `UNMAPPED_STATUS_HOLD` trả `needs_review=false`, chỉ `FIRST_OBSERVATION_CANDIDATE`: source-state không map tại 665 không được giữ issue/HOLD trong classifier 924–975. Cần giữ candidate/native values+issue khi sai shape, không crash; thiếu required fields làm graph unhashable; trạng thái nguồn chưa map phải cần xem xét, không suy approved từ dữ liệu khác.

**R2 — Quantity lexical graph: hai negative cases.** `NONDECIMAL_QUANTITY_NaN` và `NONDECIMAL_QUANTITY_abc` là **chuỗi** trong JSON hợp lệ. Thực tế vẫn có semantic/request digests, chỉ có `KHO_MEASUREMENT_NOT_EXACT`. Nhánh STRING **728–729** chưa kiểm finite decimal syntax trước semantic construction **771–777**; kiểm lexical diễn ra muộn ở **896–904**. Phải phân biệt chuỗi decimal hợp lệ nhưng precision chưa chứng minh với giá trị không phải finite decimal theo declared graph; trường hợp graph sai giữ raw/native/locator và cả hai digest null. Không đổi native Number thành text/audit tag.

**R3 — Encoding evidence mâu thuẫn: một negative case.** `ACTUAL_NUMBER_CONTRADICTS_EXACT_TEXT` vẫn có request digest và **một dòng đã normalized**. `_facts_mau_thuan` **841–864** so hai nhãn encoding với nhau nhưng không đối chiếu actual quantity token kinds. `_do_luong` **891–904** chỉ HOLD dòng Number rồi tiếp tục normalize dòng text theo cùng declaration đã mâu thuẫn. Cần request null+normalized null khi resolved exact-text declaration bị actual Number bác bỏ, giữ native và issue. Ngược lại, `POSITIVE_UNKNOWN_NUMBER` **PASS** chứng minh Number với evidence unknown hợp lệ vẫn phải giữ request identity và UNPROVEN/HOLD; không chặn mọi Number hoặc mọi proof thiếu.

**R4 — History ref/digest validation: năm negative cases.** `HISTORY_accepted`, `HISTORY_receipt`, `HISTORY_raw_null`, `HISTORY_master_null`, `HISTORY_duplicate_ref` đều giữ `history_state=KNOWN`. Tại **934–949**, classifier chỉ kiểm membership trong seen digests/logical identity, chưa kiểm unique content reference IDs, ref resolution/digest consistency hoặc tất cả prior reference digests. `_hist_digest` **143–145**, loaders **495–503** giữ null/unbound để classifier xử lý, nhưng tập kiểm **936–940** bỏ qua raw/master/reference digests.

- `HISTORY_accepted`: giữ refB nhưng đổi accepted digest thành A trong seenA/B; thực tế thành `SAME_CONTENT_FRESH_OBSERVATION`, `needs_review=false`, thay vì HISTORY_MISMATCH/UNKNOWN/HOLD. Đây cũng là điểm dừng thực của probe03.
- `HISTORY_receipt`: receipt có refB nhưng contentA; thực tế chỉ REAPPEARANCE_HOLD/KNOWN, chưa nhận diện contradiction.
- `HISTORY_raw_null`, `HISTORY_master_null`: prior digest null vẫn KNOWN; cần UNBOUND/UNKNOWN/HOLD.
- `HISTORY_duplicate_ref`: reference ID lặp vẫn KNOWN; cần mismatch/UNKNOWN/HOLD, không last-wins.

Sửa phải giữ optional reference absent khác present-but-unresolved; không bắt buộc bổ sung ref không có trong schema. K03 replay, fresh receipt và K05 acceptedB-reversed/seenA,B/A-reappearance vẫn phải đúng; không đổi accepted pointers, links hoặc history input.

**R5 — Explicit null capture errors: một negative case.** `EXPLICIT_NULL_CAPTURE_ERRORS` thực tế không bị constructor từ chối. `KhoReadContext.tu_dict` **390–394** đổi explicit null thành `[]`, trong khi contract chỉ cho absent default empty; reader **809–810** dùng empty tuple để không đánh dấu partial. Chặn invalid container/type hoặc giữ unresolved+HOLD đúng contract; không âm thầm biến unknown thành known-empty.

**R6 — Exact Digest: một negative case.** `EXACT_DIGEST_TRAILING_NEWLINE` thực tế không bị constructor từ chối. Pattern **41** với `$` rồi `.match` tại **138**, **939** chấp nhận 64 hex trước final newline. Cần full-string exact 64 lowercase hex tại mọi Digest gate; không trim hoặc normalize digest nhập vào.

Hai positive controls targeted là `POSITIVE_EXACT_TEXT` và `POSITIVE_UNKNOWN_NUMBER`, đều giữ request digest như yêu cầu. **15 FAIL là 15 counterexamples thuộc sáu nhóm trên, không phải 15 finding P1 độc lập.**

## Giới hạn và điều kiện kiểm lại

Review này tổng hợp evidence root đã chạy và đối chiếu source frozen; tác giả review không chạy thêm product/SQL/DB/HTTP/Google/source app/M9. Không phát hiện alias mutable có thể đi qua `tu_dict` với input đúng shape trong phần đã đọc; đây chưa là bằng chứng exhaustive về immutability.

Lần sửa chỉ reader/tests/report được root duyệt, giữ 43 inputs/golden/oracle và reuse modules nguyên hash; không sửa producer #10, engine kho, Store/K2/M9 hoặc thêm storage/UI. Sau authoritative terminal mới freeze và kiểm lại suite + toàn bộ independent controls; không đổi expected cho khớp implementation. M5_READER_PURE_VERIFIED và toàn module M5 hiện **PENDING**.
