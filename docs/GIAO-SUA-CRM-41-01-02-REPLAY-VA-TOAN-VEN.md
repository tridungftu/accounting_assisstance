# CRM-41-01 FIX02 — Replay, toàn vẹn durable state và actor của intent

**CODE_ONLY · PREPARED_NOT_DISPATCHED · cùng session 52783bcd-6e1d-46d2-9e45-3c527aa43e5b.** Sửa đúng sáu file existing cuối tài liệu, NEW0; Root release sau peer. Giữ kiến trúc một engine #6, một client/adapter và toàn bộ mục tiêu M4/CRM đã giao.

## 1. Baseline và bằng chứng
- FIX01 actual77296/terminal1012f0 đã dừng, owned Job rỗng và scope đạt; frozen source370/runtime438. Source SHA d499d0460654e0c6ea3194c839bffc138d3d6d27689371ed649dc67091e99ee4; runtime SHA b9a63aa956e34cd2367527efa53c85ff58fdb052e1ed7ab967ea0c9b90afaf8c; patch SHA 93405a802bf4b67ecfa3fa607ae91e0b9b8285cdfc4653fd297d8d1e8d298fde.
- Source originals vẫn chưa áp patch. Các thay đổi lần này chỉ ở staged source/central được chỉ rõ; không import/runtime từ docs hoặc copied engine.
- Root đã tái hiện bằng **causal IO-mock**, chưa phải actual source HTTP: B GET thấy chưa có input và bị giữ; A upload/start được nhận; B nhận GET cũ rồi upload bị generic409/LoiNguon, trong khi A thành công. Một luot/một start; B phải nhận cùng kết quả hoặc UNKNOWN, không FINAL LOI.
- Các khe durable create/rehydrate và actor nêu dưới là finding static. Test F4 còn vấp retained directory của original no-delete guard. Chưa có product/API/PG/GUI acceptance; không đổi cách gọi bằng chứng thành PASS.

## 2. Sửa hữu hạn
### R1 — Upload replay sau khi run đã reserve/chạy
- Source tai_len_hop_dong đang chặn _dang_giu trước khi kiểm exact samebytes của bound intent. Cho common intent hợp lệ replay cùng rawH/file đã nhận dù run đã reserve/chạy/xong; trả actual reference/tên cũ, **không ghi thêm/ghi đè**. Bytes hoặc identity khác vẫn conflict; legacy upload đóng sau start giữ nguyên.
- Client phải đối soát original intent/luot/full request khi GET cũ dẫn tới upload409. Không biến generic409 chưa xác định thành lỗi cuối; source conflict có mã và body khác vẫn là lỗi rõ. M4 tiếp tục giữ UNKNOWN, không FINAL LOI/revision/receipt mới vì lịch này.
- Regression giữ chính lịch B GET(no input) → A upload/start → B upload; thu đủ A initial, B initial và B retry/reconcile, không exception chìm/thread sống; cùng luot, một start, B cùng kết quả hoặc UNKNOWN và retry đúng intent hoàn tất.

### R2 — Durable create không tạo lượt thứ hai ở khe ghi
- Hiện luot_moi_common tạo mkdir/per-run _common_y_dinh.json trước registry global. Exception/stop giữa các bước làm retry không thấy registry và allocate luot khác.
- Dùng một durable reservation/recovery point trong storage hiện có để bind request_id + canonical full body + đúng luot trước khi side effect có thể bị mất dấu. Khép cả khe mkdir, per-run linked receipt và registry missing/ghi dở; exact retry recover cùng reservation, body khác conflict. Không thêm DB/queue/framework.
- Partial/corrupt state không được coi như chưa từng có intent; không tự create/run lần hai, không xóa/reset/ghi đè bằng chứng. Nếu chưa đủ dữ kiện để recover an toàn thì UNKNOWN có lý do rõ; không trả success giả hoặc generic failure làm client bỏ intent.
- Test inject lỗi/giữ chờ ở các write boundary rồi retry/rehydrate; kiểm full relative path + SHA/bytes toàn bộ dữ liệu trước/sau, một logical intent chỉ một reservation/run và một lần compute.

### R3 — Rehydrate phải kiểm toàn vẹn, không chỉ đọc tt
- _nap_lai_common hiện tin _luot.tt=xong và các metadata đã parse, chưa đối chiếu request/body/source/catalog/result hashes; _doc_json còn gộp corrupt và missing.
- Bind và kiểm canonical full request với reservation/create receipt, raw DOCX snapshotH, catalog snapshotH, requested/expanded set và implementation identity đã lưu. Seal terminal raw result bằng reference/hash/length từ bytes thật; chỉ công bố completed/replay sau khi có seal nhất quán. Không lấy output mới để làm expected của bản cũ.
- Rehydrate completed trả đúng raw bytes/reference cũ và không đổi history. Hash mismatch, JSON hỏng/thiếu field, partial write, snapshot/result thiếu hoặc trạng thái running không còn owner phải UNKNOWN/fail closed; không tự rerun/overwrite. Không đánh dấu done chỉ vì _luot.json ghi xong.
- Regression genuine completed replay qua trạng thái memory mất; orphan không chạy lại; corrupt request/source/catalog/result và same-size byte corruption bị phát hiện. Oracle dùng full relative path + SHA + byte length, không basename/size hay count đơn thuần; giữ mọi file.
- Inject corruption chỉ trên snapshot/resource DEMO riêng, backup bytes trước bằng CreateNew; catalog/source gốc giữ byte-exact, không xóa rồi tạo lại để làm xanh ca kiểm.

### R4 — Logical CRM intent không tách mới theo actor
- FIX01 đã yêu cầu cùng logical ID mà actor/envelope khác phải conflict trước engine. F7 lại đặt record key theo actor+ID, cho actor B cùng ID tạo intent/source request mới; đó không phải hợp đồng đã giao.
- Identity record theo logical request_id tại namespace CRM hiện có; authoritative actor nằm trong immutable full body cùng PN/profile/project/loai_ban/rawH/type/catalog/codes. Kiểm current rights trước lookup/tác động; same ID khác actor/body trả conflict hữu hạn, không lộ body/owner cũ, không gọi engine hoặc ghi business/source mới.
- Exact retry đúng actor/body giữ original source intent. Test A nhận, B cùng ID conflict và zero side effect; B dùng ID mới là positive riêng, giữ đúng owner B. Không DDL/master/quyền mới; không suy actor từ browser.

### R5 — Khép test theo original guard, giữ oracle
- F4 test hiện read_text mọi entry trong crm-trich-y-dinh nên gặp .ktt-staging directory được guard giữ lại. Chỉ đọc regular .json records; kiểm riêng retained directory đúng loại/vị trí, không blanket-ignore file lạ/extra JSON và không sửa guard.
- Giữ exact hai accepted JSON cho hai logical intents hợp lệ A/B ở R4; cùng ID đổi actor phải conflict, không dùng actor split để đạt hai file. Kiểm đầy đủ nội dung/owner/path/hash, không giảm assertion.
- Source c08 phải đủ **bốn** responses và không thread còn sống/exception chưa thu; các ca causal có ba kết quả phải đủ cả ba. Nâng c11 từ (basename,size) sang full relative path + SHA/bytes. Phân rõ IO-mock, actual loopback và static wiring; không gắn UNIT thành kiểm quyền PG thật.

## 3. Giới hạn và bàn giao
- Giữ byte-exact UI/app.js, CRM routes/server.py, M4 NR, ba algorithm files danh_muc/lo/quy_trinh, catalog/vendor và migrations1–20. Giữ các fix Windows path, shared reservation, offline/no-cache/TC positives/37, raw-vs-view hash, quyền và financial oracles đã có.
- Không source app thật, secrets/realdata, AI/cloud/Office/OCR, SQL/DB, source catalog mutation, delete/cleanup hoặc framework mới. Chỉ Read/Glob/Grep/Edit/Write; không commands/import/AST/run/tests/network/browser. Timebox1200s; report FIX02 NOT_RUN_CODE_ONLY, phần chưa xong ghi partial thật.

## Exact existing edit targets (6), NEW0
- docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py
- docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py
- src/kho_tri_thuc/nguon/trich_chung_6.py
- src/kho_tri_thuc/k2/crm.py
- tests/test_trich_chung_6.py
- docs/BAO-CAO-CRM-41-01.md
