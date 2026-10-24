# M4-02A FIX02 — guard, receipt và mount Review

**21/10/2026 · CODE_ONLY_PENDING_ROOT_RELEASE.** Sửa đúng sáu điểm dưới đây trên code hiện có. Giữ [handoff đầy đủ](GIAO-VIEC-M4-02A-REVIEW-L1-L2.md), [ưu tiên reuse](M4-UU-TIEN-DUNG-LAI-BAN-GOC-20261021.md) và [FIX01](GIAO-SUA-M4-02A-01-KHEP-RUNTIME-VA-UI.md); không viết engine/renderer/job/receipt framework mới.

## 1. Baseline và bằng chứng thật

- Actual FIX01:24813/c51c0c đã terminal, owned stop/scope/freeze do Root xác nhận. Base367source/435runtime,354protected,NEW0; sourceH`cc223ce2311989341d620ea8d8ddafbfd6e57ef124745e3dc4da2bf1d21e0efa`, runtimeH`47cb3e3984a9c53691af55af294d87cc17436c62670e98c904f0dc877d565027`.
- Guarded native pure thực tế:38run,36PASS,1FAIL,1ERROR,0skip. FAIL: worker main trả4 thay3 dù original guard A517 đang active nhưng không có module sitecustomize; ERROR: NameError trong ba assertion đặt nhầm ở test env. Bốn kiểm độc lập QD/NA/rawNULL/physical0 đều PASS. Không gọi đây là38PASS.
- Public-DOM diagnostic thực tế chưa vào được positive: P01 và toàn12ca STOPSETUP_PUBLIC_FIELD,0PASS/0contractFAIL/12NOT_VERIFIED/0unhandled. Source pre-attach giải thích không có form. Syntax APP/M4/Review đạt kiểm hữu hạn; không phải browser/HTTP/12productFAIL.
- Các child đã dừng và live/frozen posthash giữ nguyên. PG/HTTP/external Review worker vẫn NOT_RUN. Các race/toast/nonzero bên dưới là finding tĩnh, chưa ghi là runtime reproduction. Root giữ bằng chứng riêng; không yêu cầu coder đọc private fixtures/oracles/logs.

## 2. F1 — nhận diện guard thật, không lấy sitecustomize làm bằng chứng

- `review_compute.guard_dang_nap613–630` hiện chỉ xét module sitecustomize/file directory; đây không đồng nghĩa actual original no-delete hooks đang hoạt động. Có original hook thật nhưng không có sitecustomize → false rejection; có module giả/metadata đường dẫn nhưng hook không active → false acceptance.
- Kiểm actual installed hook/startup provenance của original guard mà runtime đang dùng, qua dữ kiện không bí mật do server giữ; không tin một tên module/marker hoặc browser flag. Original guard A517 bất biến: không copy/patch/disable/giảm guard, không nạp guard khác hoặc tạo bypass để thông test.
- Parent→child giữ đúng nonsecret startup/dependency/origin/no-bytecode; không mang PG/DSN/password/token/actor credential. Child fail closed TRƯỚC vendor/OpenPyXL/report I/O nếu retention được yêu cầu mà actual hooks không active; active original hooks không bị từ chối chỉ vì thiếu sitecustomize.
- Test có positive actual guard đã active và negative marker-only/missing/wrong binding; mock metadata không thay cho proof actual startup. Không gỡ retention env để đổi FAIL thành PASS.

## 3. F2 — chuyển đúng ba assertion về test worker lỗi

- `tests/test_m4_review_compute.py397–399` đọc thu_muc/ket_qua, kiểm trạng thái FAILED và bao_cao[] nhưng đang nằm trong `test_fix01_r2_env_worker_giu_khoi_dong_khong_credential`; thu_muc không thuộc scope đó.
- Chuyển nguyên ba assertion về `test_worker_luon_ghi_ket_qua_khi_loi358–362` sau lời gọi main và kiểm exit3, dùng đúng thư mục của chính test đó. Không xóa assertion, đổi expectedFAILED/[]/3, catch NameError hay dùng tệp của test khác.
- Giữ env/no-credential test và toàn bộ case IDs/oracles trước đây; chỉ sửa placement và bổ sung ca guard thật có ý nghĩa. Báo count/skip đúng sau Root kiểm, không tự ghi đã chạy.

## 4. F3 — nonzero worker exit không được công bố kết quả thành công

- `XayDungK2._review_tinh754–757` chỉ xử lý riêng exit4; nonzero khác kèm ket_qua.json SUCCEEDED/PARTIAL đúng raw/basis vẫn có thể được nhận tại775–808.
- Chỉ nhận SUCCEEDED/PARTIAL khi direct owned child đã terminal với exit0 và output đúng scope/raw/basis/shape. Nonzero/timeout/unknown terminal → FAILED hoặc trạng thái chưa xác minh phù hợp; không publish current success vì còn JSON hoàn chỉnh.
- Giữ toàn bộ stdout/stderr/input/JSON/report/partial như evidence, gắn exit/status thật; exact original body/key retry trả cùng terminal receipt. Không cleanup, key mới hoặc coi file tồn tại là success.
- Thêm counterpart nonempty exit0 và nonzero có success-looking JSON; worker chưa dừng phải fail closed, không báo stop/posthash giả.

## 5. F4 — cross-action reservation phải atomic qua RR capture

- R5 FIX01 đã bỏ long-held BN↔HĐ cycle bằng namespace riêng và đúng thứ tự map; GIỮ closure đó. Nhưng initial RC receipt847 có thể trảNone, RR snapshot850–852 mở, ordinary action cùng actor/key commit receipt, rồi Review tạo run857 trên snapshot không thấy receipt mới.
- Trigger chỉ trên INSERT bien_nhan không tự ngăn INSERT review_run trong RR cũ. Khi công bố gặp receipt-key unique conflict, cả fallbackFAILED vẫn va key và có thể để RUNNING/artifact orphan thay precise conflict trước work.
- Khép shared actor/key reservation/replay theo protocol atomic cả hai chiều, kể cả commit sau RR snapshot; không chỉ thêm EXISTS trên cùng snapshot. Có thể dùng gate/reservation ngắn nhất quán trước snapshot/effect; không giữ old BN namespace xuyên CPU hay lấy lại thứ tự nghịch HĐ↔BN.
- Same action/body exactretry trả cùng FINAL trước freshness/compute; khác action/body precise M4_IDEMPOTENCY_KHAC trước run/compute/business/audit/file effect. Giữ current-rights/source scope trước lookup; không bỏ cross-action key namespace hoặc sửa prefix1–18 để né conflict.
- Thêm controlled barrier: ordinary commit giữa initial receipt/RR snapshot và create-run, cùng reverse order. Kiểm winner duy nhất và loser đúng denial/whole delta, không chỉ đồng loạt start threads rồi dựa timing; không mock auth hay tự seed approved state. Không thêm generic framework.

## 6. F5 — mount sau khi vùng đã attached, giữ connected fence

- `m4.js:veHd522` gọi veReview→R.ve966 trước `box.replaceChildren(card)525`; `review.ve480–481` gọi napDs nhưng napDs107 yêu vungSong/isConnected. Positive có thể không gửi GET/không có form.
- Attach actual Review region vào document TRƯỚC mount/load callback; hoặc dùng narrow post-attach lifecycle gắn đúng generation/context. Giữ connected/active/current actor/HĐ/đợt fence, không bỏ isConnected để làm positive.
- Actual normal mount phải tạo nonempty selector/form bằng GET đúng current context; dynamic script first-load và already-loaded/reopen đều hoạt động. Nếu tab/HĐ/role đã đổi trước callback thì không mount/load cũ.
- Case dùng actual connected shell flow, không gọi module trực tiếp sau khi harness tự attach để che thứ tự product; stale/unmount negative vẫn không GET/POST/download ngoài context.

## 7. F6 — toast/status continuation A cũng phải giữ form generation

- `review.js:lenh84` đã chụp genForm nhưng success/error88–95 chỉ kiểm f() trước toast/status/callback. Nếu POST A pending rồi người dùng nhập B cùng HĐ/context, callback trong lenh có thể chạm UI B trước khi outer handler kiểm generation.
- Capture form/selection generation tại original intent và kiểm nó TRƯỚC mọi toast/status/error/refresh/clear/lenh callback, không chỉ trước moSauLenh. Giữ generation qua mọi await đến nested refresh/detail/blob/download.
- Request A có thể commit hợp lệ; UI stale A không đóng/xóa nháp B, đổi selection/retry B hoặc báo trạng thái A vào B. UNKNOWN vẫn giữ đúng original body/header/key/selection và không tái dựng từ B; không xóa intent chỉ để tránh late update.
- Positive current request success/error/unknown-retry vẫn hiện đúng và hoàn tất một lần; late success/error/unknown sau formB đều bị fence trước callback. Đây còn là finding source; chưa có actual UI/browser reproduction PASS/FAIL.

## 8. Scope và điều phải giữ

- Đúng13EXISTING/NEW0, baseline367/protected354/final367: `src/kho_tri_thuc/ha_tang/pg_migrations.py`, `src/kho_tri_thuc/m4/nguon_review.py`, `src/kho_tri_thuc/k2/xay_dung.py`, `src/kho_tri_thuc/giao_dien/m4.py`, `src/kho_tri_thuc/m4/giao_dien/{m4.js,m4.css,review.js}`, `src/kho_tri_thuc/m4/{review_compute.py,sql_review.py}`, `tests/{test_m4_review_compute.py,test_m4_review_k2.py,test_m4_review_http.py}`, `docs/BAO-CAO-M4-02A.md`.
- pg_migrations.py giữ nguyên868867byte prefix1–18 H`d95a14dd962d866c64915c18fded7871c6b3610d1f6e2f7c57f0583f820c0244`; chỉ sửa append M19 chưa áp PG. Vendor/reference/app gốc/fixtures/CRM/M9/rights/oldseed/guard và mọi path khác giữ nguyên byte.
- Preserve R3: Review operation-owned validated ordinary app/owner sameDB connections, captured actor, nhả global lock khi compute và close mọi nhánh. Preserve R4 setup→terminal và R6 actual vendor effective-row lineage/date/provenance. Giữ RR fullbasis/current rights/CAS, map origin RLS, old receipts/history và rawNULL≠0/QD≠NA.
- Chỉ extend đúng3bộ kiểm hiện có cho sáu fix và update report trung thực. Report phải đổi +ít nhất một source khác đổi; code/selftest/Root independent/GUI tách riêng. Không lấy count/native PASS thay independent/source-bound contracts.
- CODE_ONLY cùng session và5filetools do Root cấp; không Agent/Task/session/controller/framework mới. Không import/AST/tests/SQL/process/server/HTTP/Node/browser/Office/AI/OCR/network/credentials. Root kiểm sau actual terminal/stop/scope/freeze.
- Không DELETE/DROP/TRUNCATE/cleanup/reset/rename/ghi đè artifacts; giữ mọi raw/temp/attempt/partial/DB/role/history. Full M4/L3/OCR/reviewer approval/PDF/NT–AP/Request vẫn theo roadmap; CAD deferred/M9 dừng, không tuyên bố whole module đạt.
