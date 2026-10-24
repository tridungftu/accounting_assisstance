# L11 R16 candidate01 — root review và actual checks

**NOT_ACCEPTED / REPAIR_REQUIRED.** Đây là kết quả review độc lập của Codex đối với candidate01, không phải self-test của Claude. M2 XML/ZIP và R15 bridge đã được chấp nhận hữu hạn làm dependency DEMO; toàn M2/M5/L11/file33 chưa nghiệm thu.

## Bản được kiểm và ranh giới bằng chứng

Claude cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b` kết thúc thực tế handle4168/chunk316fbb/exit0. Root đóng băng source273 SHA `22c58d26171217b869dca4e74d483feb7313f5e1f4883e4166ea15e900c2bccf`, receipt SHA `992fbcc7bcd543512a11690093baa71f84db2b5d9a03bd4d8aae211db3a9d5bd`:10 file sửa,4 source mới,259 file được bảo vệ,0 drift ngoài phạm vi/fixture. Root đọc FULL delta SQL16,10 source deltas,4 new source/tests, report01 và handoff/cases; ba nhánh peer review SQL/service/UI đọc độc lập. Các vị trí dưới đây là line của frozen01, không là line của repair02 tương lai.

Review service authoritative: `REVIEW-L11-SERVICE-02.md` SHA `54d0edbd337ea46bfbbf57a93c3a7ca59bef4d7e535f2da9796687d390f313c1`. Review HTTP/UI: `REVIEW-L11-HTTP-UI-01.md` SHA `fe6a4eb3058a8f9f628cae0d8a747eea71b02e3fb3e5d115ddc71d8bd41fe9f0`. Ví dụ G01 instanceB trong service review01 đã rút: upstream verified-CAI context guard chặn nó. Không dùng ví dụ đó làm lỗi được tái hiện.

## Actual runtime sau terminal, trên DEMO riêng

| Phần | Quan sát thực tế | Giới hạn |
|---|---|---|
| Migration/primitive | Native9/9 PASS,0skip; root tool1bb4c9, retained `pg-retained-20261019-234122-58a24e8c` | Outer gate01 REFUSED sau runtime vì validator chỉ nhận slash, bridge trả Windows backslash. Giữ nguyên cả native9PASS và outerREFUSED; không chạy lại9 chỉ để sửa định dạng. Chưa full nonempty15→16 upgrade. |
| Service | Handle51480 terminal0b0dca exit1; native run15/failure2/error10/skip0, retained `pg-retained-20261019-234915-dff1fd39` | Log có6 named methods ok; summary passed3 trừ cả subtest errors nên không dùng làm unique pass count. Hai lỗi đầu ở helper token; các missing-state/StopIteration tiếp theo là cascade, không10 lỗi nghiệp vụ độc lập. |
| HTTP | Root tool97ba89 terminal exit1, run2/pass1/error1/skip0; retained `pg-retained-20261019-235032-9d911c6c` | Resource serving test ok; workflow dừng ở KeyError `trang_thai` khi approve. Chưa xác nhận business HTTP workflow/FILE/undo. |

Native service t02 expected `L11_MA_HOA_KHONG_CAN_BANG_CHUNG` nhưng nhận `L11_VERSION_CHANGED`; t07 expected missing encoding proof nhưng nhận cùng VERSION_CHANGED. Static root-cause: test helper210–212 hash `master.json_chuan(g)` trong khi SQL4781/6510 hash PostgreSQL `{x}::text`. Public encoding DTO7044–7057 đã trả đúng token; sửa helper dùng token đó, giữ stale/business guards. Đây là lỗi test setup có căn cứ tĩnh, chưa phải bằng chứng product tự đổi token.

HTTP test180 dùng `hc-{ref[-8:]}`; cả GOODS_EQ_A và CAI_EQ_A đều có suffix `_EQ_A_V1`, gây cùng key cho hai approve requests khác nhau. Khả năng response thứ hai là đúng idempotency denial; log hiện chỉ chứng minh KeyError, chưa ghi response code. Sửa key theo toàn reference/action và giữ deliberate same-key/different-H conflict test. Root chưa chạy finite independent control xác nhận suy luận này.

Gate02/watchdog02 được root FULL-read và peer CLOSED; chỉ normalize evidence separator trước strict regex, đổi pin gate và diagnostic allowlist. Service/HTTP đều whole273 live+frozen pre/post unchanged, protected259 unchanged, original no-delete guard unchanged; không có test đang chạy sau hai terminal trên. Không ghi bí mật hoặc dữ liệu thật vào tài liệu này.

## Các sửa bắt buộc — static findings, chưa gọi là runtime exploits

| ID | Mức | Bằng chứng frozen01 và yêu cầu sửa |
|---|---|---|
| R01 | P1 | SQL7557/7567/7577/7590 chỉ thêm AFTER impact triggers;11 legacy source/mapping/route entrypoints không precollect whole-batch peer roots/pools trước source tuple locks. Confirm/root→pool→row và source-side late locks chưa có cùng protocol. Phải giữ atomically CAN_SOAT mọi live child, không đổi stored quantities hoặc tự free held; source-only intake không cần human BOTH V2. |
| R02 | P1 | SQL7293 so cross unit refs với pool units;7325 áp `poolA*num=poolB*den`. Approve6913–6916 còn ép own-pool unit==native unit; CHECK7924–7927 chỉ một tuple và encoding7140 dùng làm pool target. Phải lưu/check riêng verified native và own-pool definition tuples, kiểm nativeA/nativeB với native definitions, rồi derive mỗi own-pool amount độc lập; thêm genuine configured nonidentity12/1 admission/positive/negative đủ budgets qua COMMON→CFO. Identity-only4proofs không bắt lỗi này; giữ chúng nguyên, dùng new in-memory synthetic profile/case ở existing test file. |
| R03 | P1 | M5 encoding7152–7165/binding7277–7298 thiếu current measurement SHA và dùng rendered `lw.stt` thay original source ordinal; raw domain/context kiểm chưa đủ. R15 unit declaration verifier đối chiếu declaration payload nhưng support raw chỉ catalog FK/shape, chưa trích actual unit/item field; seed L11 chỉ đăng ký H/length. Cần derive support facts từ actual pinned bytes qua COMMON trusted stage, không owner/browser assertions hoặc unit mới mỗi delivery. |
| R04 | P1 | THUNG native branch7133–7140 kiểm H/locator/lexeme/item nhưng chưa exact instance/profile/domain context của current typed source. Đây là static gap; test phải có legitimate alternative-context THUNG bridge được admit trước negative. Không dùng withdrawn G01B counterexample. |
| R05 | P1 | Generic parent guard7812–7850 chỉ kiểm M2/M5 core endpoints trong TG_OP INSERT7829. UPDATE genuine legacy ownerNULL parent có thể retarget endpoint mà4 typed fields vẫnNULL, đi old permissive policy. Kiểm cả INSERT/UPDATE, giữ genuine CRM/M1 compatibility. |
| R06 | P1 | Preview7364–7373 chỉ auth invoicePN_A; internal evaluator7230 đọc warehousePN_B và7358–7360 serialize refs/raw units/budget dù có crossPN blocker7252. Phải deny trước foreign projection và require samePN/currentBOTHREAD cho hai endpoints. Chưa có runtime sentinel probe, không gọi là actual data disclosure. |
| R07 | P2 | Proof consumer6685–6767 bỏ qua effective coverage/reported_errors; confirm6813–6850 approve UNG_VIEN. Exact configured raw bytes với PARTIAL/UNKNOWN/errors cần raw retention+HOLD và deny approve, không tự complete; original claims vẫn vào receiptH. |
| R08 | P2 | JS1192–1201 thiếu original-epoch check sau awaited refresh; FILE callback1306–1309 gọi download1207 lấy new current epoch. Role đổi trong POST→GET gap có thể re-arm old result. Giữ original fence qua refresh/download; backend current FILE guards vẫn là positive, không gọi UI finding là DB bypass. |
| R09 | P2 | JS1244–1251 chưa render raw H/length/facts trước CFO approve dù SQL6790–6794 có DTO. Hiển thị scoped source/domain/units/ratio/facts trước actual approve, không cho LINK raw-source access. |
| R10 | P2 | Required GET `/api/m5/l11/proof` chưa có; server957 chỉ aggregate GET, proof path rơi vào generic NOT_FOUND495–507/972. Thêm actual scoped route, không lấy aggregate test làm proof-route PASS. |
| R11 | P2 | Server606/612 ghép overview và proof candidates từ hai standalone RR transactions (service900/840). Toàn visible aggregate+tokens cần một owned RR/connection; standalone proof GET có thể own riêng. Local process mutex không chặn independent DB commit. |

Không cộng máy móc11 rows thành số bugs unique; R03/R04 cùng họ source evidence. Runtime helper failures là test issues riêng, không tự chứng minh R01–R11. Report01§5 có tự khai deviations nhưng không thay thế root evidence.

## Phần đã đúng về cấu trúc và phần còn kiểm

Stable pool theo **logical LINE** đúng: SQL7940–7962 dùng invoice logical-line ID hoặc warehouse logical-line ID, samePN typed FKs và uniqueness per stable line. Hai dòng split6 trong một phiếu có hai warehouse pools6; parent theo document-snapshot pair; hai keys4/4 cho cùng cặp sinh hai immutable children/một parent là yêu cầu đã chốt. Không chuyển sang document pool hoặc thêm unique pair+basis.

Seed mới additive, không preapprove proof/encoding/child, không regrant old actors; fixture20 và pure readers giữ nguyên. Exact integer rational parsing/representability primitives đạt native9 hữu hạn. Bốn stored quantities/held versus confirmed/undo tombstones/current replay/typed parent/current FILE guards đã có code, cần chạy đúng setup và kiểm independent toàn rows/hash/sequence/files, direct DB consumers, causal races hai winner orders, nonempty15→16 upgrade và actual browser/download bytes/cells. Counts-only, substring assets, generic exception hoặc empty/cascade setup không là bằng chứng tương đương.

Repair02 tiếp tục reuse COMMON/shared MASTER/M2 pure XML/ZIP/M5 nguồn #10/shell/filestore. Không tạo loan/stock/money engine, không sửa M9, không chuyển kho thật SQLite, không CFO_NTD/Junsky/cloud activation. Giữ mọi attempts/report/DB/roles/files; không xóa. Chỉ được giao Claude CODE_ONLY trong14 source hiện có + report02 mới; root sẽ kiểm sau terminal/freeze riêng.
