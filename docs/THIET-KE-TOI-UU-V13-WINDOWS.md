# Thiết kế tối ưu V13 trên Windows — giao Claude Code sau A3–A6

Ngày: 18/10/2026. Trạng thái: **thiết kế triển khai và kiểm chứng; chưa có mã tối ưu, chưa đạt gate hiệu năng**. Codex lập thiết kế và kiểm tra độc lập; Claude Code sửa mã chính, trong session đang dùng. Không coi tài liệu này là nghiệm thu V13.

## 1. Mục tiêu, căn cứ và ranh giới

Giảm thời gian **recompute đầy đủ 105 sao kê T8 xuống ≤10 giây** trên Windows, tính cả dựng context, đề xuất, giải thích, lưu trạng thái và trả kết quả; giữ nguyên toàn bộ kết quả từng dòng so với baseline đã giữ. Tiếp tục phương án C của V13: hai engine dùng lớp kết nối hiện hữu; không chuyển lõi sang schema K2 của V14, không chuyển kho thật, không thêm dependency hoặc sửa schema để giải quyết chi phí Python đã đo.

Căn cứ nghiệp vụ và quyền thực hiện: goal hiện hành; `../CLAUDE.md`; TL 35/37/38/39/40; `QUYET-DINH.md`; `GIAO-VIEC-CLAUDE-V13-WINDOWS.md`. Thực hiện sau khi nhóm A3–A6 đã sửa và được kiểm tra. A1–A2 là cổng parity bắt buộc trước kết luận kết quả và tốc độ; nếu đang sửa công cụ này, tránh hai bên cùng sửa một file. Tài liệu không phê duyệt bất kỳ tri thức, bút toán, thao tác Junsky hoặc cloud AI nào.

Chỉ Codex chạy trên snapshot dữ liệu thật ở máy. Claude nhận source được phép, fixture DEMO và số tổng hợp. Không gửi dữ liệu trong `var/`, SQL chứa giá trị thật, nội dung payload từng dòng, tài khoản ngân hàng, tên đối tác hay secrets tới Claude hoặc Git. Mô phỏng dùng actor `MO_PHONG_`; kho thật và backup cũ giữ nguyên.

## 2. Hiện trạng đã đo

Pointer cục bộ `var/codex-dieu-phoi/evidence-current.txt` hiện dẫn tới `var/codex-dieu-phoi/kiem-chung-20261018-101441/`. Nguồn thiết kế là ba file **chỉ gồm aggregate/function names** trong `perf-audit/`: `summary.json`, `callers-and-comparison.json`, `recommendations.json`; không dùng dữ liệu giao dịch để viết tài liệu này.

| Chỉ số | Bằng chứng hiện tại | Ý nghĩa |
|---|---:|---|
| Baseline không profiler | 31,942 giây / 105 dòng | Chưa đạt ≤10 giây; cần đo lại cùng điều kiện sau A3–A6 |
| Lần có cProfile | 50,719 giây | Dùng xác định điểm nóng; không so trực tiếp với 31,942 giây |
| Đối chiếu baseline ↔ lần profile | 105 chung; 0 chỉ một bên; 105 payload và 105 trạng thái/cờ loại xuất giống nhau | Có baseline bảo toàn semantic; không chỉ so tổng số/màu |
| Phân mức baseline | Xanh/Vàng/Đỏ = 62/33/10 | Số kiểm soát hồi quy, không là ngưỡng chất lượng kế toán |
| `Knowledge.query` | 440 lần; cumulative 17,244 giây | 822.560 lần `json.loads` phát sinh trong chính `query` |
| `resolve_identifiers` | 105 lần; cumulative 14,864 giây | Mỗi dòng quét/copy cả catalog để lấy vài định danh |
| `_opposite_accounts` | 329.120 lần; cumulative 11,858 giây | 203.280 từ ranking; 125.840 từ học mẫu |
| `offset_account_ranking` / `journal_suggestion` | 10,797 / 9,290 giây cumulative | Hai đường cùng tính lại đặc trưng lịch sử |
| `match_bank_to_journal` | 315 lần; cumulative 5,476 giây | 105 lần ở mỗi nơi: suy TK tiền, ghép nhóm, engine preview |
| SQLite `execute` | 4.483 lần; 0,218 giây | Không có căn cứ chọn SQL/index làm tối ưu chính |

Cumulative của các hàm lồng nhau **không cộng được** thành số giây tiết kiệm. Đạt ≤10 giây là giả thuyết phải kiểm chứng, không suy ra từ profile này.

## 3. Hợp đồng phải giữ

1. **Hai trục thời gian:** `known_at <= cutoff`; hiệu lực nghiệp vụ là `[valid_from, valid_to)`. Event chỉ có tác dụng khi `event_at <= cutoff`. `cutoff` thời điểm biết và `learning_cutoff` ngày học là hai điều kiện riêng, không gộp hoặc đổi cách chuẩn hóa.
2. **Học đến 30/06/2026:** giữ bộ lọc lịch sử và `source_row.lan_dau`, các phép `< cutoff_day`, mốc ngày kế tiếp và `object_learning_from` đúng từng đường đang dùng. Không lấy sổ T7–T8 làm mẫu học khi nó là đáp án; không đổi ngưỡng, window hoặc tập ứng viên để chạy nhanh.
3. **Trạng thái tri thức:** `APPROVED` chỉ khi có APPROVE và không có REVOKE trong cutoff. PENDING được phép chỉ ở đường đã cho `include_pending=True`; bản đã có event không được tự đưa về PENDING. Chế độ bình thường không dùng PENDING thay tri thức đã duyệt.
4. **Supersession:** bản thay thế đã APPROVE tạo khoảng bị thay thế ngay cả khi sau đó REVOKE; không làm bản cũ sống lại trong khoảng đó. Giữ truy tổ tiên, lỗi overlap, category và logical key, kể cả `query(category=None)`.
5. **Cache:** `knowledge_epoch` hiện là revision giao dịch của versions/events. Cache phải thấy thay đổi trong cùng transaction, instance khác, connection khác khi thay đổi đã nhìn thấy được, rollback, và event mới sau rollback. Không đổi epoch thành counter dễ tái dùng; không bỏ đọc epoch hoặc chỉ kiểm ở đầu run.
6. **Isolation:** caller sửa list, row, payload lồng, matches, pattern lines, options hoặc source IDs trả về không được sửa snapshot, kết quả lần sau, dòng khác hoặc run khác. Không dùng cache global chứa mutable object của kho. `cache_enabled=False` vẫn là đường không cache đúng semantic.
7. **Thứ tự:** giữ thứ tự sổ của bundle, thứ tự evidence/source IDs, ưu tiên cơ sở khớp, tie của `Counter.most_common`, thứ tự account đã sort, tie của primary account và alternatives. Không chuyển iterable có thứ tự thành set rồi dùng để phát kết quả. Không dùng thứ tự dictionary do một index mới tạo ra thay thứ tự sổ.
8. **Vận hành:** giữ WAIT/EXISTING, `excluded_from_export`, dòng đã quyết định, cờ “Không trùng”, scoring mask, nguyên tắc MANUAL thắng suy luận, PENDING staging và atomic transaction. Không hoãn ghi tri thức mới tới cuối run nếu điều đó làm đổi tri thức nhìn thấy của dòng kế tiếp.

## 4. Thiết kế đề xuất

### P1 — Index định danh và catalog theo tri thức đang thấy

Tách **chọn phiên bản hợp lệ** khỏi **tạo bản mutable trả caller**. Một selector nội bộ duy nhất thực hiện hợp đồng mục 3; `query`, lookup định danh và các derived index đều dùng selector đó. Không viết một bộ SQL/lọc “gần giống” riêng cho lookup.

`Knowledge.query` giữ signature, kiểu kết quả, thứ tự và defensive copy hiện hữu. Không tăng tốc bằng cách trả trực tiếp `payload` trong `_snapshot`, đổi thành shallow copy hoặc bỏ kiểm overlap. Đường selector chỉ giữ private references/IDs; mọi reference tới payload snapshot ở trong module và không được mutate/đưa vào payload kết quả.

Index lookup private có khóa `(category='CATALOG', business_date, cutoff chuẩn hóa, include_pending, knowledge_epoch)` và gắn với đúng `Knowledge`/Store. Xây từ các phiên bản đã qua đủ eligibility/supersession/overlap. Khóa tra cứu là `(identifier_type, normalized_value)`; **chỉ ALIAS dùng `normalize_text` như hiện tại**, không tự chuẩn hóa lại BANK_ACCOUNT/TAX_ID/COUNTERPARTY_NAME hoặc làm mất zero đầu. Giá trị là các record nhỏ có đúng trường hiện tại, theo thứ tự nguồn; không phải cả payload catalog.

`resolve_identifier` và `resolve_identifiers` dùng chung lookup này. Batch trả key theo cặp đầu vào gốc, kể cả giá trị ALIAS được chuẩn hóa nội bộ; cặp lặp không làm tăng matches. `verified`/`include_pending`, UNIQUE/CONFLICT/UNKNOWN và thứ tự matches giữ nguyên. Trả fresh list và fresh match dict mỗi lần; dữ liệu ngoài hợp đồng nếu có phải được copy đủ sâu.

Catalog membership và đầu vào `NameIndex` có thể lấy cùng selection private để tránh parse/copy mọi IDENTIFIER chỉ để bỏ đi ngay sau đó. Chỉ materialize row độc lập ở boundary cần trả row/payload. Giữ API công khai cũ; không truyền immutable proxy vào `canonical_json` hoặc payload GUI nếu serializer chỉ nhận dict/list.

Memo `Engine.name_index` hiện giới hạn tám key trong khi profile dựng 43 index. Thay cơ chế xóa cả cache khi vượt tám bằng memo có giới hạn hợp lý cho một run và đo số key/hit/build. Có thể giữ đủ các ngày thực có trong lô 105 dòng, hoặc reuse khi **tập entries có thứ tự thực sự bằng nhau**; không coi cùng tháng/cutoff là tương đương. Catalog và identifier index không cache theo ngày mà bỏ epoch. Khi epoch đổi, invalidation bảo thủ toàn bộ vẫn đúng; không bỏ invalidation CATALOG chỉ vì event mới là RULE nếu chưa có cơ chế chứng minh được category không đổi.

**Giả thuyết H1:** lookup vài cặp định danh và dựng name/catalog index một lần cho mỗi context sẽ loại phần lớn 822.560 lần decode và quét catalog. Đo số query calls, decoded payloads, index builds/hits, wall time và peak memory. Đừng chọn deepcopy toàn catalog để thay json.loads; đó là chi phí cũ V10 đã tránh.

### P2 — Đặc trưng lịch sử tính một lần cho mỗi bundle

Tạo đối tượng context lịch sử private, sống trong một `propose/repropose`, xây từ chính bundle đã qua cutoff bằng `documents_bulk`. Mỗi journal có một entry theo **vị trí sổ**, gồm ID/ngày/trạng thái, cờ BR/BP, cash legs/merged cash legs, fingerprint, tập số trong mô tả và kết quả opposite pattern cho từng chiều IN/OUT khi cần. Các line/leg lưu ở dạng private bất biến; khi phát kết quả có mutable lines phải tạo bản riêng.

Không cache bằng journal ID toàn cục hoặc chỉ `id(bundle)` rồi giữ lâu: journal cùng ID có thể có phiên bản/core/lines khác trong bundle khác. Context giữ sở hữu bundle không đổi; không mutate journal đã dựng context. Nếu một đường cho phép sửa bundle, phải xây context mới hoặc vô hiệu hóa đúng nội dung, không dùng dữ liệu cũ.

`offset_account_ranking` và `journal_suggestion` nhận context tùy chọn hoặc adapter nội bộ tương đương; đường gọi cũ vẫn hoạt động. Context chỉ tiết kiệm **đặc trưng thuần**; mỗi consumer vẫn giữ tập được phép riêng:

- Ranking hiện nhận toàn bộ journals từ hints, lọc BR/BP và ngày `< first_day`, không tự đổi thành posted-only. Tính một Counter tổng theo chiều/cutoff và context riêng theo fingerprint của từng dòng; nếu memo ranking, key gồm chiều, cutoff_day, limit, fingerprint đầu vào và `ignore_words`. Giữ thứ tự first-seen của account qua sổ và sort account trong từng journal như hiện tại.
- Học mẫu dùng journals posted của engine, ngày `< cutoff_day`; giữ ưu tiên same-account → fingerprint similarity → same-party, phép lọc cash account, mốc 365 ngày khi đủ ba mẫu, tỷ lệ 80% và điều kiện unanimous. Đặc trưng chung không được gộp các bước ưu tiên hoặc đổi `total_found` thành số sau lọc cash/window.
- Fingerprint lưu dạng đã chuẩn hóa, nhưng `ignore_words` trừ ở đúng consumer. Cache kết quả similarity phải có threshold và ignore_words; không dùng fingerprint ranking làm thay hàm `fingerprint_similar` vì hai phép khớp khác nhau.

Sau khi đo P2, nếu vòng scan còn chiếm nhiều thời gian, xây index phụ theo ngày/chiều, từ fingerprint, số trong mô tả hoặc counterparty. Index chỉ chọn superset đủ ứng viên; chạy predicate hiện hữu để quyết định. Khi union candidate IDs, sắp lại bằng vị trí sổ trước đếm/chọn. Riêng ranking, ứng viên context từ inverted index phải đúng phép giao một/hai từ đang có; Counter tổng có thể dựng một lần theo `(chiều, cutoff_day)`.

**Giả thuyết H2:** đưa `_opposite_accounts`, merged legs và BR/BP checks về mức một journal/chiều trong run sẽ giảm mạnh chi phí Python. Cần đo số feature builds, số scan, ranking/học mẫu, memory và thời gian end-to-end; không cam kết tốc độ từ số lần gọi đơn thuần.

### P3 — Lookup duplicate theo ngày/chiều/số tiền, tách tập ứng viên

Dùng merged cash legs của P2 dựng index `(business_date, side, abs(amount_minor)) -> journal entries` theo thứ tự sổ, trong **từng pool**. Predicate BR/BP và yêu cầu đúng một cash leg khớp trong journal phải như cũ: hai TK tiền cùng chiều/cùng tiền làm journal không đủ điều kiện, không tự chọn một leg.

`infer_cash_mappings` nhận toàn bộ journals hiện tại; ghép nhóm và engine preview nhận posted pool. Trong scoring, preview có thể `require_description=False`, còn hai đường khác mặc định True. Vì vậy **không** biến 315 phép gọi thành 105 bằng memo theo bank ID. Reuse match cuối chỉ khi bank core, ordered pool, threshold, `require_description` và context thực sự giống nhau. Index candidates thuần có thể dùng chung features; mỗi đường tự áp dụng quy tắc UNIQUE/AMBIGUOUS/UNMATCHED của mình.

Giữ ghép nhóm, các voucher đã giải thích bởi một dòng, cash mapping fallback, cleared-match và scoring mask. Không mở cache theo đáp án hoặc dùng kết quả match của posted pool để suy mapping từ một pool khác.

**Giả thuyết H3:** index loại bỏ các vòng quét tất cả journals chỉ để kiểm ngày/tiền, giảm thêm thời gian context và preview. Nếu P1–P2 đã đạt với đủ biên ổn định, chỉ triển khai P3 khi đo còn cho thấy cần; không mở rộng sửa thuật toán học hoặc normalization.

## 5. Gói giao Claude: đầu vào, đầu ra, cổng đạt

| Gói | Đầu vào | Đầu ra phải giao | Cổng đạt trước bước sau |
|---|---|---|---|
| P1 | `tri_thuc/service.py`, `de_xuat/engine.py`, matching contract; tests cache/identifier hiện hữu; aggregate profile trên | Selector và lookup/index private; catalog/name reuse nếu đo có ích; test DEMO semantic mới cần thiết | Cache on/off giữ kết quả; mutation/epoch/rollback/cutoff/pending/supersession không hồi quy; không đổi public contract |
| P2 | `giao_dien/v9b.py`, `quick.py`, `engine.py`; P1 đã kiểm | Context features theo bundle; ranking/học mẫu dùng lại; không đổi pool/order; test DEMO pattern/ranking | Payload và options/evidence giữ nguyên; không dùng mẫu sau mốc học; không alias line giữa kết quả |
| P3, có điều kiện | Profile sau P1–P2; duplicate/group semantics | Index ngày/tiền và reuse có key đầy đủ nếu cần | Tập toàn bộ/posted, scoring/normal, ambiguous và cleared-match tách đúng; đủ baseline parity |
| Kiểm độc lập | Mã Claude đã chốt; snapshot không đổi; A1–A2 đã đáng tin | Diff review, test hai engine, so 105 payload/states/exclusions, chấm Junsky và timing không profiler | 0 lỗi chặn; đầy đủ 105 recompute; parity từng dòng; ≤10 giây theo mục 7 |

Claude chỉ sửa các file đã được giao; Codex không sửa chồng. Claude báo danh sách file, test thực chạy, skip, aggregate hiệu năng DEMO, giả thuyết được/không được dữ liệu ủng hộ và điểm cần Codex đo tại máy. Không chỉ báo “cache đã nhanh” hoặc tự dùng aggregate của lần trước như kiểm chứng sau thay đổi.

## 6. Kiểm thử semantic cần có

Tận dụng các test hiện có trong `test_v1b`, `test_v1_matching`, `test_modules`, `test_v10`, `test_v11`, `test_v9b`, `test_v12` và bộ PostgreSQL. Bổ sung ca còn thiếu theo hành vi quan sát được; không assert tên private function, hình dạng cache, số lần gọi cứng hoặc output tính bằng cùng helper mới với implementation.

| Nhóm hành vi | Fixture DEMO / phép thử | Kết quả cần chứng minh |
|---|---|---|
| Biên thời gian | Hai phiên bản kề ngày; known/event trước, đúng và sau cutoff; mốc 30/06–01/07; lan_dau tương lai | Chỉ phiên bản/chứng cứ được phép hiện ra; bộ lọc ngày học không bị cache che |
| Supersession/overlap | Chuỗi A→B→C; B đã approve rồi revoke; bản pending thay A; hai bản overlap không có quan hệ | Khoảng bị carve-out đúng; bản revoked không làm A sống lại; pending không tự carve-out; overlap vẫn lỗi |
| Trạng thái lookup | Verified/unverified × approved/pending/revoked; một mã có nhiều evidence hoặc hai mã xung đột; ALIAS biến thể và zero đầu | Giá trị, trạng thái và thứ tự matches như contract; cặp lặp/batch bằng lookup đơn |
| Mutation isolation | Sửa sâu payload query, expired, matches, pattern/options trả lần đầu rồi gọi lại; thử hai Engine/Store khác nhau | Kết quả kế tiếp và kho khác nguyên vẹn; không cần biết cache chứa gì |
| Epoch/transaction | Cache trước/sau stage/approve/revoke; connection khác commit; rollback sau khi đã đọc thay đổi rồi event mới | Thấy đúng revision được transaction cho thấy; không dùng thế hệ cache của transaction đã rollback |
| Thứ tự/tie | Sổ cố ý không theo ngày; hai account/signature đồng số lần, line nhập đảo thứ tự; nhiều PYTHONHASHSEED | Ranking, primary, signatures, source IDs, lý do và options đúng thứ tự đã xác lập, ổn định giữa process |
| Pattern nhiều dòng | Split 112 + VAT; cùng tài khoản lặp; hai TK tiền; âm/0/unbalanced; đổi direction | Giữ mẫu hợp lệ, loại mẫu sai đúng như cũ; scale integer và phần dư không đổi; không alias lines |
| Khác pool/điều kiện | Cùng bank với journal posted/unposted, threshold khác; require_description True/False; cùng ngày/tiền nhiều cash legs | Kết quả khác nhau đúng predicate, không bị match memo của đường trước làm nhiễm |
| Scoring và quyết định | WAIT/EXISTING, dòng đã duyệt/bỏ/xuất, “Không trùng”; pending pattern mới trong vòng lặp | Recompute đúng tập; giữ exclusion; không lộ đáp án; ghi pending/audit nguyên tử; dòng quyết định không bị sửa |
| Index không stale | Hai bundle cùng journal ID nhưng khác amount/lines/description; hai run/cutoff khác nhau | Context/index mới phản ánh đúng nội dung, không reuse ID của bundle cũ |

Đường cache disabled là oracle kiểm đối chiếu hữu ích nhưng **không đủ** nếu dùng cùng selector bị lỗi; các ca có đáp án DEMO tường minh ở trên mới chứng minh được quy tắc nghiệp vụ.

## 7. Cách đo và nghiệm thu

1. Giữ baseline bằng hash source/cấu hình/snapshot và phiên bản công cụ trước sửa. Sau A3–A6, nếu source đổi, lập một baseline lại bằng mã trước tối ưu; không trộn số 31,942 giây lịch sử với điều kiện mới. Dùng snapshot sao chép độc lập cho từng lần để side effects staging/pending không làm khác đầu vào.
2. DEMO: Claude tự chạy relevant tests rồi full suite hai engine. Chỉ ghi số thực chạy, failure/error/skip; thiếu PostgreSQL hoặc test skip là chưa kiểm chứng phần đó. Đo thêm fixture có quy mô 2.027 mã và 105 dòng, đủ lịch sử/pattern nhiều dòng; không dùng fixture rỗng/nhỏ để kết luận ngưỡng thật.
3. Codex chạy cục bộ trên bản sao: cùng run/tháng, cutoff, scoring và mốc học 30/06. Bảo đảm `eligible=105`, `recomputed=105`, không thiếu/ngoài tập. So **toàn bộ** proposal payload, thứ tự arrays, state và exclusion từng document với baseline: 105 giống, 0 lệch, 0 chỉ một bên. Chỉ bỏ metadata do công cụ đo tự thêm và đã liệt kê trước; không bỏ why/options/evidence để làm parity xanh.
4. Chấm Junsky lại: 105 dòng, matched/unmatched giữ 88/17 và toàn bộ kết quả từng dòng bằng baseline; phân mức 62/33/10 giữ nguyên. Aggregate là số kiểm soát, không thay kiểm từng dòng và không chứng nhận chất lượng nghiệp vụ. Hóa đơn 75 dòng chấm riêng mua/bán cũng phải giữ parity vì P1 và context chung chạm đường hóa đơn; dùng cổng A2, không suy từ sao kê.
5. Timing bằng `perf_counter` **không cProfile** trên cả SQLite và PostgreSQL, tính từ trước `repropose` tới khi trả toàn bộ rows; dựng index/caches mới phải nằm trong cửa sổ đo. Không tính cài đặt/chuyển dữ liệu hay chấm đáp án vào 10 giây. Báo thêm timing context/preview/persist để chẩn đoán, không dùng đoạn nhanh nhất thay end-to-end.
6. Ít nhất ba lần fresh Engine/context trên bản sao đồng nhất cho mỗi engine; ghi từng số, min/median/max, CPU/RAM/Python/engine và điều kiện tải máy. Phân biệt cold process, warm process và OS file cache; không tuyên bố cold disk nếu chỉ khởi tạo lại object. Mục tiêu ≤10 giây phải đạt ở từng lần nghiệm thu đã thống nhất; nếu có ngoại lệ phải giải thích/đo lại, không chọn riêng lần tốt nhất. Báo peak memory khi index mới tăng RAM.
7. Chạy cProfile riêng sau tối ưu để kiểm H1–H3. Báo giảm chi phí/scan/decode và bottleneck còn lại, không so cProfile wall với timing không profiler. Nếu chưa ≤10 giây, dùng profile mới chọn bước kế tiếp trong thiết kế; không hạ tiêu chí hay đổi semantic. Nếu cần thay thuật toán nghiệp vụ/kiến trúc ngoài mục này thì trình quyết định riêng.

Bằng chứng tại máy chứa detail chỉ trong `var/` bị Git ignore; báo cáo/Claude chỉ nhận số tổng hợp và lỗi đã lọc. Kết thúc bằng review độc lập không tham gia triển khai, xử lý lỗi chặn, rồi mới cập nhật checklist nghiệm thu V13. Tối ưu đạt tốc độ riêng không đóng các gate V13 còn lại.
