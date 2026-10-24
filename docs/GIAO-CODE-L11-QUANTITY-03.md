# L11 QUANTITY — bounded repair03

**L11_QUANTITY_CODE_ONLY03 / ROOT HANDOFF.** Cùng session52783bcd-6e1d-46d2-9e45-3c527aa43e5b; root dispatcher riêng mới là authority khởi chạy. Chỉ Read/Glob/Grep/Edit/Write, CODE_ONLY. Không execute/import/compile/test/SQL/PG/HTTP/Node/browser/server/CLI/process/network, không credentials/.env/var/.git/sourceapps/real rows. Selftests UNRUN. Không delete/move/drop/reset/cleanup file/DB/role/attempt. M9 chỉ reuse retrieval, không sửa tracker. Kho thật vẫn SQLite.

Kế thừa handoff01 ce65bd92dc0c97509b69a9062969b55cefea2dee2e01bffa75822ba73ddcb4a5 và handoff02 5cc2c222decb841e94ab9f2e1bf041df2c26bc9930b5d5be7b51110b56207d2a, cases01 6ab9e6603fc7d3d067f4fd557630a11e84b91cfb4eb30e7c5e077e0a11c1f66f. Chỉ sửa các điểm cụ thể dưới đây; không mở rộng sang mô-đun khác hoặc viết lại phần đã có.

Baseline actual02: handle47839/chunk60f60e/exit0; frozen273 manifest81abd25aad43aed3b0e991c91c080b86da354662f2a5f3721970bf1bcb750e2f, receipt96f3a7497c3a3833a18a37076640599050eb697f48f53a643b2e396716f37fb9,8 changes,259 protected0drift. Fixture20 manifest227980804428af52fb153b9c15a9142e5b261f2b50bbd4b8e873ba421b3081dd giữ nguyên. Root02 đã chạy migration12/11pass/1fail, service18/17pass/1fail, HTTP2/2pass,0skip. Hai failures là exact-error test oracles; native nonidentity positive/negative đã chạy đạt, không full acceptance.

Đọc FULL `docs/REVIEW-L11-ROOT-ACTUAL-02.md`, `docs/REVIEW-L11-HTTP-UI-02.md`, `docs/REVIEW-L11-LOCK-02.md` và report02. Reviews là nguồn lỗi/giới hạn, không tự cấp runtime. Không coi report02 hoặc các test của chính coder là independent acceptance. Không sửa old reports/reviews/handoffs/fixtures/controllers/guard. Literal/generated SQL1–15, checksum/order giữ nguyên; chỉ replacement/new SQL trong16, không append17 hoặc sửa DB attempts đã có16.

## A. Whole-batch identity gates trước root/pool/effects

Repair02 precollect chỉ existing invoices; old M2 promote loop vẫn lấy HOA_DON identity namespace rồi tạo/khóa root theo XML/ZIP order. Hai batch mới [A,B]/[B,A] có thể cycle; mixed new/existing còn namespace sau existing-root/pool prefix. Đóng toàn giao thức cho mọi identity trong batch, không chỉ sort output hoặc thêm khóa muộn.

Current identity/caps→operation namespace/H/replay→shared pre-root namespace/subject gates cho TOÀN batch→resolve mọi identity→collect toàn affected closure gồm peer roots→canonical roots cả hai phía→sorted pools→fixed rows→reread closure→business effects/holds/receipt cùng TX. Các identity mới cần quy trình tạo/reserve có cùng order, không giữ row/root/pool trái order rồi mới xin namespace khác. Giữ shape/content/CAS/admission/observer semantics của M2/M5 cũ. Không giả định hai batch cùng input order; không append lower root khi closure mở. Kiểm tất cả11source paths cùng confirm/encoding/revoke/undo/file paths và đường source-only direct DB definer. Một gate/prefix mới chỉ có nghĩa nếu mọi contender liên quan tuân theo cùng order; Python mutex hoặc comment không chứng minh DB safety.

Tận dụng `_m16_thay`, common lock helpers và namespaces có sẵn; được bỏ hạn chế “insert-only diff” của test mới trong16 nếu cần refactor đúng generated replacement. Hạn chế đó không được giữ một loop sai order. Lịch sử1–15 vẫn byte-identical. Không đổi stable logical LINE pool grain/parent document-pair/immutable child. Không làm deadlock/timeout thành expected PASS.

Sort lock plan, giữ nguyên delivery/occurrence order của observation loop và classification/history A→B→A/duplicate ZIP. Closure recheck phải so đầy đủ child IDs/pool IDs cùng roots: helper6600–6604 chỉ kiểm root containment, revoke7180–7191 còn có pool query mới trước khi biết root closure đã mở. Nếu tập đã đổi, restart/deny toàn mutation trước effects; không xin pool/row mới rồi mới phát hiện chưa khóa root. Report rõ inherited inverse-new-batch issue và introduced late-visible namespace/root inversion, không bịa runtime exploit.

Thêm ca meaningful trong test hiện có: batch2identity cả hai order, existing/new mix; source-only intake hold atomic, A,A/duplicate ZIP không hold và A→B→A không tự active. Q09 cần disjoint actual PG app connections, current actor contexts, actual functions/transactions, pg_blocking_pids exact contender/winner và finite watchdog; route-vs-confirm, used-proof revoke-vs-confirm, undo-held-vs-new-confirm cả hai winner orders. Return từ function chưa COMMIT phải giữ giao dịch để quan sát causal wait; không dùng sleep/giả UDF outcome thay bằng chứng. Ca stale CAS phải nhận đúng mã và0own mutation; fresh-token sequential control ghi riêng, không gọi là concurrent success. Thiếu control ghi UNRUN/chưa viết cụ thể.

## B. FILE continuation giữ toàn context tới actual click

Giữ original epoch/actor, captured form epoch và pair/selection context qua POST, refresh, headers/body Blob và actual anchor click. FILE callback phải truyền predicate thật; conCap chỉ parent vẫn tồn tại không đủ. Đổi pair hoặc amount ở refresh pending/blob pending phải0auto-download/click/toast cũ. Newer aggregate GET trong download pending cũng phải hủy continuation cũ; generation không chỉ so một lần rồi bỏ khỏi returned fence. Refresh do chính thao tác được phân biệt với GET cạnh tranh bằng ticket/generation immutable phù hợp; không rearm bằng current epoch/form/gen.

Sau mỗi await kiểm context trước effects/status/toast/DOM/download; catch cũng không đẩy status cũ sang selection mới. Giữ current server rights-before-replay/download và selector đúng2login. Facts/H/length trước approve, proof GET và aggregate one-RR đã sửa, chỉ chỉnh nếu cần để giữ invariant. Không nới quyền hoặc thay body authority. Root có adapter actual-handler độc lập; substring asset test không đóng async acceptance.

## C. Native proof actual support + length trước approval

NATIVE_ENCODING hiện bỏ `native_byte_length`, còn actual supportfield helper chỉ chạy lúc encode. Dùng common captured source/reader facts để kiểm native SHA + **positive exact integer byte length** + locator + actual decoded unit/item field + supporting instance/profile/refSHA trước approved-proof INSERT. Native length claim sai479/actual480 hoặc thiếu capture/field khác phải deny approval/giữ raw,0newapprovedproof/encoding/child. Không coi declaration self-H/catalog FK hoặc registered proof H là kiểm semantic claim.

Lưu tuple native length/support cần thiết cùng immutable proof/basis, CHECK/FK/guard/DTO/preview/FILE khi cần; encode kiểm lại current source context/actual facts. Dùng reader/common stage đã có, không viết SQL parser mới/free-browser proof. SAME_VERIFIED M2 seed supportNULL đã có actual captured row fallback; không sửa old seed/profile để né lỗi. Phân biệt evidentiary MASTER3a8… và current splitMASTER3c6… đúng như02; current measurement/source_ordinal giữ nguyên.

Capture THUNG thật trước khi approve native proof trong test setup (qua service nguồn hiện có), thay thứ tự Q00/t07 nếu cần. Không owner INSERT approved rows, không disable guard, không yêu cầu mọi5 GOODSbindings đã capture vì một suy diễn ngoài scope. GOODS domain vẫn explicit; actual pair validation kiểm binding cụ thể. Default four proofs/20fixture bytes không đổi; nonidentity proof vẫn new registered in-memory instance/profile, giữ positive0.01/0.12→pool0.12/0.12 + negative0.01/1.44 đủbudget.

Thêm negative native length/wrong actual field/context/missing support với exact code và nonempty legitimate positive. Raw/intake evidence được giữ; “0approved business” khác “0capture rows”. Report rõ nhóm nào chưa có test.

## D. Sửa đúng hai expected-code oracles, giữ guard

`test_l11_migrations.py:288`: endpoint retarget đã bị trigger lịch sử `lien_ket_kiem` từ chối trước bằng P0001 `LIEN_KET_KHONG_SUA`; assert đúng mã thực và row unchanged. Không đổi trigger ordering/quyền để ép L11_LIEN_KET_CHUNG_GIA. Ca INSERT có guard L11 riêng vẫn giữ.

`test_l11_k2.py:445` forged parent UPDATE: đúng P0001 `L11_CHA_BAT_BIEN`; assert theo đúng operation này. Không thêm broad substring `L11_`, arbitrary exception hoặc cho mọi code trong mọi ca. Các ACL42501/receipt guards của operations khác giữ chặt. Test-token phải dùng public DTO, full-reference keys và deliberate conflict/replay giữ nguyên.

## E. Exact write scope và delivery

Chỉ14existing files như02 (273 pathset,259protected):

- `src/kho_tri_thuc/ha_tang/pg_migrations.py` (chỉ16)
- `src/kho_tri_thuc/k2/lien_ket_chung.py`, `kho_so_luong.py`, `hoa_don.py`, `quyen.py`, `crm_khoi_dong.py`, `nguon_chung.py`, `l11_demo.py`
- `src/kho_tri_thuc/giao_dien/server.py`, `assets/app.js`, `assets/index.html`
- `tests/test_l11_migrations.py`, `tests/test_l11_k2.py`, `tests/test_l11_http.py`
- CreateNew **`docs/BAO-CAO-L11-QUANTITY-03.md`**, không sửa report01/02.

Không thêm source/fixture21, không xóa hoặc dọn thư mục/DB/role/attempt kể cả rollback/teardown. Không regrant revoked actors bằng reopen/seed. Report03 exactfiles/anchors, interfaces/errors/schema/new lockorder, tests đã viết và thiếu; mọi selftest UNRUN. Root actual terminal+freeze+FULL review rồi mới release independent tests. Không bịa checksum mới, terminal, root receipt hoặc PASS/fullL11/full33.
