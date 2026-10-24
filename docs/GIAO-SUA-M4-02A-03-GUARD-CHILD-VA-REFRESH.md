# M4-02A FIX03 — guard child, refresh GET và nút báo cáo

**21/10/2026 · CODE_ONLY_PENDING_ROOT_RELEASE.** Chỉ khép ba repair dưới đây trên code hiện có; kế thừa [handoff đầy đủ](GIAO-VIEC-M4-02A-REVIEW-L1-L2.md), [FIX01](GIAO-SUA-M4-02A-01-KHEP-RUNTIME-VA-UI.md), [FIX02](GIAO-SUA-M4-02A-02-GUARD-MOUNT-VA-RECEIPT.md) và [ưu tiên reuse bản gốc](M4-UU-TIEN-DUNG-LAI-BAN-GOC-20261021.md). Không dựng lại engine, renderer, receipt/job framework hoặc master.

## 1. Baseline và bằng chứng phải đọc đúng

- Actual FIX02:91225/cddd3a đã terminal exit0; Root xác nhận owned stop/scope/idle/freeze. Baseline367source/435runtime,354protected,NEW0; sourceH`e743ca90b32bad64f05c17b9f6f54e88f85d64e3d4324cf1291b61b39937d55f`, runtimeH`82053276e1e22132adaf3dd8d3a4b3d28355f3285191c52a5b758315403c5fd8`.
- Root actual native pure45/45PASS,0fail/error/skip; bốn kiểm độc lập QD/NA/rawNULL/physical0 đều PASS. Giữ các counterpart này. Guard-CWD diagnostic thực tế vẫn FAIL: dấu vân khác chỉ ở hai hàm stdlib frozen, dù original A517 hooks đang active.
- Actual public-DOM UI07 cuối cùng:5PASS/2CONTRACT_FAIL/7NOT_VERIFIED,0unhandled; hai late-refresh success/error thực sự đổi status của nháp B. P02 exact original headers đã PASS sau JSON normalization hai realm; lỗi cross-realm deepStrictEqual của lượt trước là harness, KHÔNG phải product bug và không yêu coder sửa header đúng để vừa harness.
- Bảy ca tải chưa qua setup vì không thấy actual artifact button: đó không phải bảy download-behaviorFAIL. Source nested-array giải thích một lỗi render nút riêng ở §4. Các child đã dừng, source posthash giữ nguyên; external Review worker/PG/HTTP/browser/fullM4 vẫn chưa được nghiệm thu.

## 2. F1 — provenance của stdlib frozen phải ổn định giữa parent và child

- `review_compute.dau_van_guard622–649` hiện đưa mọi `code.co_filename` qua `_chuan_duong`/abspath. Sentinel chuẩn `<frozen os>` của `os.removedirs` và `os.renames` bị coi như filename tương đối ngoài stdlib; `tep` thành CWD/sentinel và `goc=False`.
- Parent ở CWD máy chủ và child ở thư mục run riêng vì vậy có dấu vân khác tại `guard_dang_nap675`; worker bị từ chối dù các original hooks đúng. Sentinel còn có thể bị tính nhầm là hook bởi `hook_hoat_dong` chỉ xét có `goc=False`.
- Nhận diện đúng actual frozen-stdlib origin/code provenance trước khi chuẩn hóa đường dẫn: sentinel không phải tệp tương đối, không phụ thuộc CWD và không tự là bằng chứng no-delete hook. Không mặc nhiên tin mọi chuỗi sentinel/module/marker là stdlib hoặc guard thật.
- Original guard A517 bất biến. Giữ kiểm actual installed hooks và provenance parent→child; có hook thật nhưng không có sitecustomize vẫn được nhận, chỉ marker/missing hook/wrong provenance vẫn từ chối. Không copy/patch/disable guard, nạp guard khác, gỡ retention env hoặc né check để thông test.
- Giữ startup/dependency/no-bytecode allowlist không PG/DSN/password/token/credential. Child vẫn fail closed trước vendor/OpenPyXL/report I/O khi guard thực được yêu cầu mà không active; không đưa đường dẫn/hook facts từ browser vào authority.
- Meaningful checks: actual original hooks + parent/child khác CWD cho cùng provenance; untouched frozen-stdlib funcs không bị đếm là guard; marker-only/nohook/wrong binding bị từ chối. Không thay actual startup proof bằng dict giả duy nhất, không thử xóa tệp để kiểm.

## 3. F2 — late refresh GET phải giữ nháp và status của ngữ cảnh mới

- `review.js.napDs107–125`: success117–118 đổi `ds`/`dsLoi`/`sel.tep` TRƯỚC kiểm `fs()`119; khi form generation đã đổi còn ghi status cảnh báo. Error122–125 cũng có thể xóa `ds/kq/runChon` và ghi error/status trước form guard.
- Lịch đã tái hiện: POST A thành công → nested refresh GET pending → người dùng mở/nhập nháp B → GET success hoặc error A về. Mọi hiệu ứng A phải bị fence TRƯỚC mutation dữ liệu/lựa chọn, status/error, toast, clear hoặc render; không chỉ chặn `ve_()` cuối cùng.
- Giữ original form/selection generation từ entry qua mọi await của nested refresh, bên cạnh epoch/actor/HĐ/đợt/tệp/GET-generation/active-connected scope. Khi stale, bỏ continuation, không ghi thông báo A vào status B và không làm đổi basis/lựa chọn dùng cho lệnh B.
- Positive current-context refresh success/error vẫn phản ánh đúng dữ liệu và lỗi hiện hành; không bỏ mọi GET/error hoặc freeze UI để tránh counterexample. Current permission denial vẫn có hiệu lực đúng ngữ cảnh.
- Extend bộ kiểm hiện có bằng public connected handlers, controlled response barriers và counterpart không rỗng: late success, late error giữ nguyên nháp/status B; current refresh hoạt động. Giữ direct-POST generation fence, original UNKNOWN File/body/header/key/selection, current completion once và mount/role/unmount fences của FIX02.

## 4. F3 — render actual artifact buttons thay vì stringify nested arrays

- `review.js.exportButtons401–405` đưa `kinds.map(...art.filter(...).map(button))` thành nested arrays vào `el`; helper25 chỉ `con.flat()` một mức rồi stringify phần tử không phải Node. Có artifact DTO không rỗng/finding hiện nhưng không có report button thật để bấm.
- Sửa hẹp child-list composition/render hiện có để mỗi actual artifact record tạo đúng connected button tương ứng; giữ thứ tự loại/nhãn/style/layout nguồn. Không dựng UI/renderer mới, fake button, hardcode artifact ID hoặc tự tạo tệp/report để giả positive.
- Giữ exact registered run/artifact IDs, report kind/name/hash/length và actual `tai(a)` qua current-rights download route; không lấy finding hiện hoặc file tồn tại làm bằng chứng đã tải.
- Positive: actual nonempty registered artifact → public button → đúng current request → nonempty bytes/hash. Giữ late headers/blob sau đổi form/tab/HĐ/đợt/role/unmount không click download, không status/toast cũ. UI mock không thay browser/HTTP/physical-XLSX acceptance; không nới expected để nhận nút giả.

## 5. Scope và closures phải giữ

- Đúng13EXISTING/NEW0, baseline367/protected354/final367: `src/kho_tri_thuc/ha_tang/pg_migrations.py`, `src/kho_tri_thuc/m4/nguon_review.py`, `src/kho_tri_thuc/k2/xay_dung.py`, `src/kho_tri_thuc/giao_dien/m4.py`, `src/kho_tri_thuc/m4/giao_dien/{m4.js,m4.css,review.js}`, `src/kho_tri_thuc/m4/{review_compute.py,sql_review.py}`, `tests/{test_m4_review_compute.py,test_m4_review_k2.py,test_m4_review_http.py}`, `docs/BAO-CAO-M4-02A.md`.
- Chỉ sửa tối thiểu cần cho ba repair; extend đúng ba bộ kiểm hiện có và cập nhật report trung thực. Giữ case IDs/assertions/counterparts cũ; report phải đổi và ít nhất một nonreport source phải đổi, không thêm file/source mới.
- Giữ nguyên868867byte prefix1–18 H`d95a14dd962d866c64915c18fded7871c6b3610d1f6e2f7c57f0583f820c0244`; M19 chưa áp PG chỉ sửa append khi thực sự cần trong scope. Vendor/reference/app gốc/fixtures/CRM/rights/oldseed/M9/guard và các protected paths giữ nguyên byte.
- Preserve strict owned worker exit0/raw/basis/shape trước success, retain evidence/nonzero FAILED, setup→terminal, operation-owned validated PG connections/actor snapshot/close, RR fullbasis→compute→current-rights CAS, effective manual-target lineage và origin-run RLS.
- Shared actor/key commit-claim protocol của FIX02 giữ closure tĩnh; actual PG causal verification vẫn pending, không nâng thành runtime PASS. Không mở lại architecture, cắt coverage hoặc đổi nguồn/approval/provider để làm kiểm đạt.
- CODE_ONLY cùng session và5filetools do Root cấp: không Agent/Task/session/controller/framework mới, import/AST/tests/SQL/process/server/HTTP/Node/browser/Office/AI/OCR/network/credentials. Root kiểm sau actual terminal/stop/scope/freeze.
- Không DELETE/DROP/TRUNCATE/cleanup/reset/rename/ghi đè artifacts; giữ raw/temp/attempt/partial/DB/role/history. Full M4/L3/OCR/reviewer approval/PDF/NT–AP/Request và CRM đã chốt vẫn nguyên roadmap; CAD deferred/M9 dừng, không tuyên bố whole module đạt.
