# M4-02A FIX01 — khép runtime và vòng đời Review UI

**21/10/2026 · CODE_ONLY_PENDING_ROOT_RELEASE.** Sửa hữu hạn cùng gói, theo [handoff đầy đủ](GIAO-VIEC-M4-02A-REVIEW-L1-L2.md), [ưu tiên dùng lại bản gốc](M4-UU-TIEN-DUNG-LAI-BAN-GOC-20261021.md) và [brief tiếp tục](GIAO-VIEC-M4-02A-TIEP-TUC-DUNG-LAI-REVIEW.md). Không quyết định lại nghiệp vụ/kiến trúc, không thêm engine/master/renderer/queue framework/quyền song song.

## 1. Actual baseline và giới hạn bằng chứng

- Actual82481/d1934c đã success, owned stop/scope được Root xác nhận. Final367source/435runtime,354protected; source manifest`bd194d443eebc7772949a93e842981ff7976f2e3fa35e185e0577c7f28503299`, runtime manifest`80c8ac36934facc4a1e5a3a001abaaec6d944fbc512c71696e17558115d2de91`. Root bind actual input pins trước dispatch; không tự đọc private runtime/evidence.
- Root đã chạy guarded native pure:30PASS/0skip; ca độc lập KHONG_QUY_DINH +rawNULL thất bại vì actualKHONG_AP_DUNG thay vìINCOMPLETE. Owned child đã dừng, live/frozen posthash nguyên. Đây là component evidence, không full Review/M4 PASS.
- Native PG/HTTP/worker Review **NOT_RUN**: source đã xác nhận worker bỏ retention startup flags. Các concurrency/UI schedules dưới là findings tĩnh, chưa giả là runtime reproduction. Không lấy native pure PASS thay chúng.

## 2. Các sửa bắt buộc

### R1. KHONG_QUY_DINH không phải explicit KHONG_AP_DUNG

- `review_compute.phu_thuoc113–116` đang gộp hai state vào flag `tuong_minh_khong_ap_dung`; coverage297–300 dùng flag để rawmissing/NULL thành KHONG_AP_DUNG/DAT_DU. Chỉ cho exception khi có explicitNA/basis proof hợp lệ; không suy “HĐ không quy định” thành “không giữ lại/không tạm ứng” hoặc số0.
- Giữ nguyên vendor và raw/source state, original findings, RC02 unrounded counts, TRUOC chưa có provider→INCOMPLETE và K7LIMITED→B7. Toàn bộ8coverage requirements của handoff gốc vẫn bắt buộc; companion phải đi cùng persisted/UI/report, không xóa finding hoặc nới assertion để đạt.

### R2. Worker giữ original retention startup, không mang credential

- `xay_dung._worker_review687–690` đã có PYTHONDONTWRITEBYTECODE=1 nhưng env allowlist làm rơi PYTHONUSERBASE/CODEX_NO_DELETE_FILES. Giữ đúng nonsecret retention startup của parent, frozen module-origin/runtime dependency paths và no-bytecode; không truyền toàn bộ env hoặc DSN/PG/password/session credentials vào worker.
- Nếu parent bật chế độ retention/no-delete thì child phải fail closed khi original guard thực sự không active, trước vendor/OpenPyXL/report I/O. Không patch/giảm guard hoặc tạo bản guard khác để qua test; retain raw/temp/partial/report. Worker vẫn chỉ nhận immutable inputs+basis, không mở PG.

### R3. Không giữ global HTTP mutation lock qua CPU; không dùng shared GUC/connection thay thế

- Current `giao_dien/m4.py292–302` bọc Review tới subprocess dài, chặn GET/đổi vai và tác vụ module khác. Không chỉ bỏ lock vì cached service/factory60–78 đang dùng app/owner connection chung và GUC actor/transaction.
- Capture actor/context từ current session dưới boundary ngắn, dùng operation-owned ordinary app và validated same-endpoint/sameDB owner connections cho Review, lifecycle close ở mọi nhánh. Tách transaction/GUC khỏi connection dùng chung; không nhận actor/DSN từ body. Giữ các API khác và role barrier hiện có, không tạo factory/framework tổng quát mới.
- One RR capture đầy đủ → đóng transaction ngắn → owned compute → recheck current module/PN/project/exact raw scope +whole-basis CAS publish. GET/đổi vai không chờ hết CPU, và actor mới không đổi identity của operation cũ; actor bị revoke/source đổi không publish current result.

### R4. Setup lỗi sau durable RUNNING phải kết thúc có bằng chứng

- `xay_dung775–788` đã commit RUNNING nhưng mkdir/_raw/working-copy/input699–708 nằm trước try710. Bao trọn setup/compute/admission vào terminal-failure path: missing/hash-corrupt raw, mkdir/write failure hoặc worker chưa start không để RUNNING vĩnh viễn.
- Giữ partial/evidence, terminal FAILED/CANCELLED đúng nguyên nhân và current-rights boundary; exact original key/body retry đọc cùng terminal FINAL, không tự key mới, chạy lại vô hạn hoặc cleanup che lỗi. Timeout/stop chưa xác nhận không được báo thành công.

### R5. Same actor/key khác action: chặn conflict trước effect, không vòng khóa BN↔HĐ

- Review session namespace BN611–622 đi trước publish HĐ lock, trong khi M17 ordinary action khóa HĐ rồi lấy cùng BN namespace. Khi bỏ global CPU lock, cross-action cùng actor/key có thể tạo cycle.
- Chọn protocol/namespace/lock-order nhất quán với protected1–18, xử lý reservation/replay ngay trước effect; samekey khác action/body phải precise conflict, không deadlock/timeout hoặc hai reservation mâu thuẫn. Giữ original-body replay và atomic receipt/audit semantics; không đổi prefix cũ hay bỏ key conflict để tránh khóa.

### R6. Manual target phải là đúng effective vendor lineage

- `sql_review351–360` chỉ kiểm latest DA_MAP/sameHĐ, chưa đủ: PL draft/future/hủy hoặc GOC đã bị effective PL THAY không được nhận như target đang có hiệu lực. Service849–854 có whole token không thay validation này.
- Resolve target theo cùng actual source `phu_luc_ap_dung/boq_hieu_luc`, cùng snapshot/ngàyNT/status/BOQ replacement row và stable provenance. Ghi map phải trỏ đúng row/source mà engine dùng, không chỉ trùng ma_hm; stale/wrong/future/replaced target deny trước map/audit/receipt effect. Phần PL delta chưa typed giữ INCOMPLETE, không tự đọc prose/điền0 hoặc dựng PL master khác.

### R7. UI continuation không được xóa nháp mới hay tải ngoài context

- `review.js.moRun118–136` và `ghep181–183` cần giữ form/selection generation từ entry qua mọi await/clear/toast/refresh; GET lịch sử A hoặc POST ghép A trả muộn sau khi nhập B không được đóng form/đổi lựa chọn/xóa mã-lý do/retry B. Request cũ có thể commit hợp lệ; UI stale không được áp vào nháp mới. UNKNOWN giữ đúng original body/key/selection, không tái dựng request.
- Shell tab/HĐ/đợt change và unmount phải invalidate/deactivate Review ngay lúc intent đổi, không chờ mount mới cập nhật ctx. Fence dùng current active region +generation/context chung, kiểm cả trước request và sau headers/blob; late report A không link.click/download/toast khi đã qua tab/HĐ/đợt B. Giữ positive download/current context và shared role barrier, không sửa quyền backend để thay UI fence.
- Tiếp tục reuse layout/template/helper Review gốc trong working review.js/scopedCSS; không thiết kế UI khác, iframe/source server hoặc legacy “Nạp đợt đã duyệt”.

## 3. Exact13existing paths; không tạo source/report mới

| Đường dẫn được sửa | Giới hạn |
|---|---|
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` | M19 chưa apply PG; chỉ hoàn thiện append M19, giữ nguyên868867byte prefix1–18 SHA d95a14dd962d866c64915c18fded7871c6b3610d1f6e2f7c57f0583f820c0244 |
| `src/kho_tri_thuc/m4/nguon_review.py` | Existing pinned adapter/projection seam |
| `src/kho_tri_thuc/k2/xay_dung.py` | Review orchestration/ownership/lifecycle |
| `src/kho_tri_thuc/giao_dien/m4.py` | Narrow Review HTTP/factory/session boundary |
| `src/kho_tri_thuc/m4/giao_dien/m4.js` | Existing shell context/Review lifecycle bridge |
| `src/kho_tri_thuc/m4/giao_dien/m4.css` | Scoped existing Review styling only nếu cần |
| `src/kho_tri_thuc/m4/review_compute.py` | R1 và worker/coverage boundary |
| `src/kho_tri_thuc/m4/sql_review.py` | M19 receipt/reservation/effective-map guards |
| `src/kho_tri_thuc/m4/giao_dien/review.js` | Existing DOM handlers/fences |
| `tests/test_m4_review_compute.py` | Extend meaningful state/guard checks |
| `tests/test_m4_review_k2.py` | Extend actual lifecycle/rights/replay/causal checks |
| `tests/test_m4_review_http.py` | Extend native HTTP/session/worker/UI-support checks |
| `docs/BAO-CAO-M4-02A.md` | Update existing report, honest code/selftest/runtime limits |

Baseline367/protected354/final367; NEW paths=0. Brief này là Root-owned READ input thêm, không cho sửa. Vendor56/reference/app gốc/quyền/master/oldseed/CRM/M9/guard/fixtures/resources/histories/prefix1–18 và mọi path khác giữ nguyên.

## 4. Acceptance và thực thi

- Extend đúng3bộ kiểm hiện có: positive trước negative; QD+NULL vs explicitNA/physical0; retained worker guard và no-PG; GET/đổi vai song song compute bằng ordinary owned connections; setup failure terminal/exactretry; cross-action conflict không deadlock; effective-map counterparts; controlled lateA/formB/tab/blob fences cùng nonempty positive. Không mock quyền hoặc normalize lỗi để gọi PASS.
- R02 nonfinite→NULL vẫn là ghi chú source-state/diagnostic chưa có physical reproduction, không bắt mở thêm validator/engineering không liên quan trong lượt sửa này. Không thay fixture/oracle hoặc diễn giải native30 là full integration.
- **CODE_ONLY, tests viết nhưng NOT_RUN.** Chỉ5filetools của cùng session Root cấp; không Agent/Task/controller/session mới. Không import/AST/tests/SQL/server/HTTP/Node/GUI/Office/AI/OCR/credentials/subprocess; Root sẽ kiểm sau actual terminal/stop/scope/freeze. Không DELETE/DROP/TRUNCATE/cleanup/reset/overwrite artifacts; giữ mọi attempt, raw, temp, partial, DB/roles và history.
- Full M4 vẫn gồm L1/L2/L3/OCR/jobs/reports/reviewer approval/PDF/nghiệm thu–AP/Request; CAD deferred/M9 dừng. Fix này không thêm accounting/Request authority, không thu scope hoặc tuyên bố whole-module acceptance.
