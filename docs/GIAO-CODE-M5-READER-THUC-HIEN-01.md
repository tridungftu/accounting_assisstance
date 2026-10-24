# M5 — thực hiện reader thuần nguồn kho #10, gói 01

**19/10/2026 · READY_FOR_ROOT_REVIEW; chỉ chạy sau root dispatch.** Đây là code đầu của M5; toàn M5/L11/intake/API/UI/core tiếp tục sau gói thuần. Tái dùng producer #10; không viết lại kho, tính tồn, costing hoặc ledger. M9 chỉ read-method theo yêu cầu mới nhất của Anh, không sửa/chạy M9 hay tracker.

## 1. Căn cứ và đầu vào chỉ đọc

- `docs/GIAO-CODE-M5-READER-33.md` SHA `24be8a2049e67c186b9943e80e1620b4f46fdc60b9668311c2a5ace281c5c254` chốt phạm vi extraction/classification; áp DTO cụ thể bên dưới thay tên interface còn đề nghị trong bản đó.
- `docs/M5-HOP-DONG-FINGERPRINT-VA-HISTORY-33.md` SHA `7fcf0e3d24564ae129dabb615791097640609aaaa6d016bcd6121c24062e02bf` chốt semantic/request projection.
- **DTO có thẩm quyền cho gói này:** `docs/M5-HOP-DONG-DTO-33.json`, bản03 SHA `d1b3577074794d8d09af2d5ccb58aa0caa47540f7ccaf3e62475599fb6e6f73f`. Các marker PREPARE_ONLY trong lịch sử DTO/fingerprint không cho phép tự mở scope; root dispatch riêng release code thuần theo chính nội dung đã review.
- `docs/BINDING-M5-CORE-SAU-CRM03.md` SHA `7de60be44fe301d043a70aa2b582572f5d96d40f9444238f10a2a50acd4bcc5c`; `docs/TAI-SU-DUNG-PHAN-MEM-KHO-10.md` SHA `92dfe44947baad6cc2d0f34bb27c2a8d5f21949cf33ffc9bd91a8dbe9c1621c4` là technical/sanitized audit, không actual deployment proof.
- Root đã chuẩn bị43 fixture files trong `tests/fixtures/kho_10/`, manifest SHA `5d680a1cd4a691fba5d6eca7056bdc94f9fbf558b80e2415d97f9808215c8e66`: lexical native bytes10, contexts10, histories10, golden observer,6 native controls,2 context controls,19-control observer, original oracle, README và manifest. Không đọc `var`/private helper/source app. Golden và oracle chỉ observer; DEMO preconditions không là link DB/approval production. Root baseline189 gồm146 cũ giữ nguyên+43 fixture files; hash pin trong dispatch.

## 2. Đúng ba write targets mới

1. `src/kho_tri_thuc/nguon/kho_10.py`
2. `tests/test_kho_10.py`
3. `docs/BAO-CAO-M5-READER-01.md`

Fixtures/DTO/contracts/reuse files giữ nguyên. Không sửa `__init__`, Store/intake/server/migrations/K2/DB/schema/source registry/config/dependencies/guard/runner/dispatch/ledgers hay source app. Không dùng test runner để ghi fixture/expected/contract hoặc mở DB/network/process. Không tạo helper product khác để vượt whitelist.

## 3. Reader và DTO bắt buộc

Implement `doc_phieu_kho(content: bytes, context: KhoReadContext) -> KhoReadResult` và `phan_loai_quan_sat(candidate, summary: KhoHistorySummary | None)` trong cùng file. Constructors `KhoReadContext.tu_dict`/`KhoHistorySummary.tu_dict` chỉ cho trusted caller/root DEMO; không đọc context/history từ native/browser. Result giữ receipt/source-profile/scope refs cần cho classifier theo DTO03; classifier không tra fixture ID/order/expected để quyết định.

Deep-immutable bằng frozen typed DTO; `FrozenObject`/`FrozenArray` tagged riêng để `{}` khác `[]`, recursively freeze; `KhoIssue` snapshot bất biến vì shared `fixture.Issue` hiện mutable. Không tuple chứa dict/list/Issue mutable, không input mutation/cache/global history. Reuse definitions `doc_json_chinh_xac`, `chuan_hoa_so`, primitives `DataError/canonical_json/sha256/text_id/date_iso` và semantics Issue; không sửa các file reuse. Không import Store/K2/server/postgres/migrations hoặc app nguồn.

Malformed container/type có lỗi rõ; missing/null/unresolved business refs (mapping/PN/profile/scope/master/evidence) phải giữ candidate+issue/HOLD thay constructor abort. Missing mapping/PN/profile không xóa valid semantic source facts; thiếu logical/master graph hoặc native shape/date không hợp lệ thì semantic/request NULL. Giữ native values/locator khi recover được; logical key nullable, invalid scalar vẫn giữ exact FrozenValue và kind INVALID, không biến object/bool thành NULL.

Native `{phieu,lines}` đúng whitelist/line order; chặn duplicate JSON keys/native ID_Dong, orphan SoPhieu, NaN/Infinity/audit-tag giả. Không last-wins, sort STT, fake date/zero/PN/unit, suy ngày từ SoPhieu hoặc sinh phiếu âm khi đảo. Raw SHA đúng **bytes thực truyền reader**, không outer wrapper/re-serialized tree. Quantity text/type/token giữ nguyên: NUMBER quantity_text lấy đúng lexical token native (vd `1e+03` khác `str(Decimal)`), không reserialize; giữ strict parser và capture token/locator lossless bằng stdlib, không dependency mới. Test exponent/trailing-zero/negative-zero cùng raw SHA. Exact JSON Decimal không chứng minh precision Number nguồn. Miền38,12 không rounding/truncate/abs/float/parseInt.

Semantic/request envelope/version/projection đúng contract, normalize Decimal chỉ trong fingerprint tree. Request identity tách eligibility: optional measurement/proof unknown vẫn explicit NULL hashable khi required refs hợp lệ; K08/K09/K10 còn request H nhưng normalized quantity NULL/HOLD. Required refs thiếu hoặc resolved facts mâu thuẫn thì request NULL. Digest/replay không cấp precision, approval hoặc capacity.

Normalized quantity chỉ khi trusted `resolved_measurement_facts` coherent với source instance/source profile/measurement profile, declared actual encoding/domain38,12, immutable unit ref→native master UOM và explicit same-unit ratio1/1. Không tin opaque ref spelling/native/browser label, không suy1/1 hoặc factor12. K01–K07 facts là **explicit synthetic DEMO**, không proof producer thật; K06 graph vẫn invalid. K08 facts NULL/Number unproven; K09 changed UOM và K10 blank UOM không có new proof. Same verified unit proof conversion NULL là N/A; khác unit cần approved immutable proof, chưa có thì HOLD.

History đúng logical+scope/profile; None khác explicit empty, mismatch/unbound digest => UNKNOWN/HOLD. Same receipt+request/content => REPLAY; cùng receipt khác digest => CONFLICT/HOLD; new receipt+accepted content same => fresh; current đảo => REVERSED; acceptedB đảo+seenA/B rồi A => REAPPEARANCE_HOLD. Không reopen/free old links, promote/approve/choose current; partial/precision/UOM/continuity issues phải tồn tại đồng thời dù replay. Không dựng state store/pool/budget/valuation.

## 4. Controls và command duy nhất

Tests đọc native/context/history **riêng**; observer expected hashes/oracle chỉ assert ở test, không truyền vào reader/classifier. Không import private binding helper, không lấy output reader làm golden, không sửa expected/input. Assert mười case extraction/classification theo phạm vi reader: K01 exact DEMO, K02 instanceB, K03 replay, K04 reverse, K05 ABA hold, K06 duplicate, K07 partial, K08 NULL/0/fraction/Number, K09 UOM continuity, K10 unknown UOM. DB/L11 consumption/period/RLS chưa kiểm ở gói này.

Thêm adversarial controls có positive counterpart: missing/null refs; malformed quantity giữ representation; date missing/invalid; wrapper/duplicate key/NaN; duplicate referenced master kể cả identical; BOM/whitespace vs raw/semantic; native business/status/line order đổi semantic, master order/receipt/fetch không đổi semantic; request mapping/proof change và unknown optional proof hashable; resolved payload source/profile/unit/encoding mismatch HOLD; source partial không delete; history missing/mismatch/receipt conflict/fresh vs replay; immutable nested object/array/Issue và caller mutation sau constructor không đổi DTO. Giữ toàn bộ root input hashes trước/sau.

Chỉ root-dispatched môi trường system Python+no-delete guard/no-bytecode cho phép đúng command:

```text
python -X utf8 -m unittest discover -s tests -p test_kho_10.py
```

Không command khác, PG/SQL/Store/API/HTTP/UI/Google/cloud/host/launcher/git/pip/cleanup. Tool/Bash denied => báo UNRUN và dừng đường đó, không đổi policy/shell/runner. Không xóa/move/replace file/DB/role/temp/attempt. Tests dùng memory và readonly DEMO fixtures; không tự tạo nguồn thật/config/secret.

## 5. Bàn giao

Hoàn thành ba file, chạy command nếu được release, báo exact test counts PASS/FAIL/ERROR/SKIP/UNRUN, changes/reuse/limits và kết thúc CLI để root freeze/hash/review độc lập. Không lấy self-report làm nghiệm thu. Nhãn tối đa sau root verification là M5_READER_PURE_VERIFIED; toàn M5/L11/API/UI/runtime/production vẫn PENDING. Không tiếp tục đầu việc khác hoặc hỏi lại kiến trúc đã thống nhất.
