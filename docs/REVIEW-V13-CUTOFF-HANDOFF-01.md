# Review độc lập handoff V13 cutoff 01

**19/10/2026 · STATIC_ONLY / PREPARE_ONLY / NOT_RUN.** Đã đọc toàn handoff và gate, kiểm10 frozen source hashes rồi đọc các selected entrypoints/consumers. Không đọc backup-coder interim, real rows/credential; không product imports/test/SQL/runtime, không sửa source/public ledger. Claude backup đang active; chưa cấp quyền chạy cutoff hoặc M9.

| Căn cứ | SHA256 |
|---|---|
| `GIAO-SUA-V13-CUTOFF-01.md` | `36270d099726272efc44cb3e28927af0bfa931dec0d892db31b51b45322ac92a` |
| `V13-CONG-KIEM-CHUNG-CUTOFF-33.md` | `38fcae6ff91b4d54361b388dd0061e83cbdfe24e9b00f0295f7ee3a8fad3e7c3` |
| Frozen whole manifest được handoff viện dẫn | `19c3476cb01fde17ec0382c16c3537813cec804b725e1bcd6eb730e5db8da276` |

Các source line bên dưới thuộc frozen `m9-typed01-handoff-20261019-111048-752/frozen/src/kho_tri_thuc/`; tên thư mục chỉ provenance, không cho phép resume M9. Mười selected file khớp đúng bảng hash handoff; không suy toàn manifest đã kiểm lại trong review này.

**Kết luận:** chín write targets đủ làm tuyến context/filter/projection/cache và báo NV theo T01–T08 mà không dựng engine/schema mới hoặc sửa approval/runtime/v9b. Chưa đủ căn cứ dispatch một lượt “baseline rồi sửa” ngay: cần tách phase rõ và chốt proof/API fixture contract; thêm exact invoice/current-config bypass vào case oracle. Không cần quyết định nghiệp vụ mới khi temporal evidence thật thiếu: giữ NOT_VERIFIED đúng gate.

## R1 — P2: tách phase terminal, không để Claude chờ release giữa lượt sửa

Handoff `:59` yêu cầu coder lập DEMO vectors rồi root review/release actual baseline **trước semantic change**; `:77` lại yêu cầu root đọc exact tests/runner/commands/observer trước dispatch. Các file mới/API context/fixture vectors chưa có, nên chưa có một phase contract có thể chạy trọn không chờ approval giữa CLI.

Đề nghị ghi hai lần giao riêng trong cùng session khi được root phát lệnh: **Phase A PREPARE** chỉ context DTO/proof variants/callgraph + inputs/expected/tests/runner plan, không sửa semantic/execute, kết thúc CLI; root đọc/pin/release. **Phase B BASELINE+FIX** mới chạy baseline trên frozen pre-change bằng retained runner đã release, lưu fail/NV/positive thật, rồi sửa đúng whitelist và self-check; kết thúc để root freeze/review độc lập. Nếu baseline release cần riêng thì tách thêm lượt, không mở coder khác hoặc để một CLI đứng chờ root giữa write. Source rebase sau backup terminal là gate đầu Phase A như đã nêu.

## R2 — P2: thêm exact invoice/identity-config consumers vào oracle chống tương lai

Handoff `:34,47,50–51` đã cấm current-DB bypass về nguyên tắc. Tuy nhiên D05 hiện chỉ làm adversarial cash/BANK, còn D09 mới yêu cầu XML nonempty; một fix chỉ prefilter `Quick._bundle/_context` sẽ không phủ các reader độc lập sau:

- `engine.py:894–913 _invoice_mst_account_fields` tự SELECT **mọi JOURNAL** rồi `document(...,C)`, không nhận bundle/cohort đã lọc; same invoice number có thể cấp debit/credit/evidence từ nguồn ngoài TRAIN/L. Query known≤C không tự phân biệt ORACLE hoặc future-to-L. Đây là đường tĩnh cần khóa, chưa khẳng định dữ liệu hiện tại đã làm rò rỉ.
- `engine.py:70–95 _own_codes/own_words` lấy `v9b_derived_own_codes` ngoài `_runtime_settings` và raw COUNTERPARTY core/name hiện tại. Chỉ pin `v9b_runtime_settings`/Knowledge catalog không bao phủ các input này; name-ignore/ranking/evidence có thể phụ thuộc state/config ngoài context.
- `quick.py:542–544 _knowledge_payload`, `:614–620 _enrich`, `:557–563/:636–639 _cfo_notes` là re-read cho explanation; có `document(...,doc_id)` không C và CFO notes workspace hiện tại. Những route này phải dùng pinned facts/config hoặc explicit unavailable provenance, không mới chỉ output fields sạch còn basis/why đọc current.

Đề nghị thêm vector **invoice** với positive June history/hard key cụ thể rồi chèn same-number JOURNAL thuộc ORACLE/ngoài L; fields/confidence/basis/evidence không đổi. Thêm mutation current derived-own-code/counterparty-name/CFO-note ngoài C với frozen context giữ kết quả hoặc NV đúng contract. Root cần thấy actual call trace của các helper này, không chỉ cache key/used-count ở Quick. Tất cả sửa được trong engine/quick đã whitelist, không cần mở thêm file hay business policy.

## R3 — P2: proof resolver/context API còn phải bind ở Phase A trước semantic patch

Handoff `:30–32` đã quy định context immutable và proof phải đối chiếu artifact/evidence/version; đây là điều kiện đúng nhưng hiện chưa có schema/shape cụ thể để coder và root cùng chấm positive. Cần Phase A nêu chính xác: context constructor/entrypoint kwargs, per-case key D/C, source-role/record-version identity, provenance locator+hash/precision/basis, immutable settings digest và allowed proof variants; actual API nào đọc/đối chiếu từng ref, lỗi/missing/ambiguous trả gì. Không coi một object caller có hash/ngày hoặc `DEMO_SYNTHETIC` là tự cấp authority.

Ưu tiên bind vào existing immutable artifacts/evidence/knowledge version/event/source-bundle guards; DEMO proof là setup độc lập được root review, không giả availability nguồn thật. Historical source thiếu timeline thì AS_KNOWN NV; không đòi tạo bảng/ledger hoặc sửa dates/approval để có positive. D01–D09 expected vectors phải có concrete fields/IDs/confidence/used cohorts; fixture synthetic event times phải ghi đúng regime setup, không được chuyển thành lời khẳng định thao tác production đã xảy ra trước L/C. Baseline cũ chưa nhận keyword `temporal_context`: Phase A cần chỉ rõ cách chạy baseline bằng actual old API và giữ manifest context bên observer, không patch baseline rồi gọi đó là before.

## Những constraint đã đủ rõ, cần giữ nguyên

- Authority at C tách khỏi learned facts at L: `Knowledge.query:110–142` kiểm approval/revoke và che ancestor đã bị approved replacement, kể cả replacement sau đó revoked. Optional projection chỉ **sau** selector; không loại REVOKE15/07 khi C05/08 vì event sau L, không làm ancestor sống lại. Handoff `:53` đã xử lý đúng, không mở lại policy.
- T03/D04 đã đòi closure/zero proof/inventory độc lập trước gọi `reconstruct_open_items:79–106`; helper hiện chỉ phát hiện unavailable trong danh sách được cấp và có default0 cho item mới (`:104`). Không gọi helper.complete hoặc hash partial list là full-source coverage. Thiếu proof giữ NV, không dựng công nợ mới.
- Existing `Learning.eligible/suggest:87–124` và `Quality.evaluate:148–179` nằm trong whitelist: có thể chuyển context/frozen train membership/excluded labels, giữ event history và grouped split; score `:28` đang zip nên strict identity/cardinality check trước chấm là cần thiết. Không cần sửa external workflow để làm test xanh.
- Context digest check trước Quick existing-run reuse (`quick:452–454`), preserve decided rows/history khi repropose và manifest provenance đều nằm trong quick WRITE scope. Không dùng nguồn/mốc mới để âm thầm đổi attempt hoặc ghi cash inference ngược workspace trong evaluation.
- History cache fix nằm trong quick `_history_invoices:368–385`: exact bytes/profile/scope/C/L/settings, defensive copy, stale reject khi replace giữ mtime/count. Parser/history READ files có thể giữ nguyên nếu caller admission đúng; khi thiếu source temporal proof chỉ báo hồi cứu/NV, không cần sửa parser để tạo proof.

Sau ba điểm chuẩn bị trên có thể dispatch đúng phase khi root release. Hiện không có baseline/product run mới, không finding nào chứng minh whole T01–T08 đã đạt; M9/source tracking và kho thật giữ nguyên phạm vi đã chốt.
