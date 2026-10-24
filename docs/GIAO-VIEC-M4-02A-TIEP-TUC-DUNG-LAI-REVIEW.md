# M4-02A — tiếp tục hoàn thành bằng Review gốc đã copy

**21/10/2026 · CODE_ONLY_CONTINUATION_PENDING_ROOT_RELEASE.** Đây là bổ sung ưu tiên và correction cho cùng gói, không thay hoặc thu hẹp handoff đầy đủ [GIAO-VIEC-M4-02A-REVIEW-L1-L2.md](GIAO-VIEC-M4-02A-REVIEW-L1-L2.md). Tuân thủ [M4-UU-TIEN-DUNG-LAI-BAN-GOC-20261021.md](M4-UU-TIEN-DUNG-LAI-BAN-GOC-20261021.md); không quyết định lại kiến trúc/nghiệp vụ đã chốt.

## 1. Mốc tiếp tục thật

- Lượt code-only trước dừng timebox900s, actual53961/fabfff; Root đã xác nhận owned stop. Frozen partial có362source/430runtime; mới đổi PG/NR, thêm compute/SQL. Chưa hoàn thành service/HTTP/UI/tests/report, report chưa có: **NOT_COMPLETE / NO_RUNTIME_ACCEPTANCE**.
- Source baseline362 SHA`c270a5a84ac5fae7418d0752fee6b023331b443c1e8310d48be48f956493b2e9`; runtime430 SHA`570375b3a6c2594b46e97f162033b29f7ddfbe1171c7d92d9220932d42179533`. Exact launch inputs/release do Root bind; không tự đọc private runtime/evidence hoặc khởi chạy lượt khác.
- Root đã đối chiếu56/56 vendor runtime và65/65 references khớp nguyên byte với app Review nguồn. Giữ chúng nguyên byte. Compute đã gọi `toan_ven.KiemTra.chay`, `nghiep_vu._lop1`, `csdl_hop_dong.tinh_doi_chieu_dot`, `_lop2`, `bang_kiem_lop2`, `_lop2b`; hoàn thiện adapter, không thay bằng thuật toán kiểm khác.

## 2. Ưu tiên đưa giao diện Review đang có vào M4

- Lấy `src/kho_tri_thuc/m4/review_goc/giao_dien/checks.js`626dòng làm điểm xuất phát: render/form178–250, bảng hạng mục254–310, cây311–339, history/render361–445, actions448 trở đi. Giữ layout/cột/filter/findings/evidence/manual-match/rerun; không vẽ lại UI hoặc tạo engine mới.
- Reuse helper/render cần thiết từ `ui.js`, `chon_hd.js`, formatter `api.js` và style nguồn vào working `m4/giao_dien/review.js`/scoped `m4.css` trong target hiện có. Scope CSS/DOM/event vào vùng Review thuộc M4; không boot source app/router/daemon, không iframe/legacy server hoặc shell/master/quyền song song.
- Bridge callback hiện có của shell M4; thay `X-HD`, legacy textual HĐ/endpoints/source path bằng current KTT token/session và server-scoped IDs/basis/revision. Không chọn HĐ đầu danh sách để suy quyền, không lấy browser machine-facts làm authority.
- Reuse shared role barrier `window.kttChung`, một chuỗi đổi vai chung; kiểm actor/project/HĐ/đợt/file/run/form/tab/generation sau từng await, trước DOM/cache/status/refresh/header/blob/download. Pending role phải chặn dữ liệu vai cũ hồi sinh; context stale không xóa nháp, retry hay pending record mới.
- Mount route/load-order exact `review.js` qua current `giao_dien/m4.py`; không mở generic filesystem/static server. Vendor UI modules/styles chưa được package đầy đủ: đưa helper cần dùng vào working entry trong13targets thay vì thêm dependency/assets/targets hoặc giả đã copy là wheel đã phục vụ được.
- Legacy checks “Nạp đợt đã duyệt” `/nap` là import/replace dữ liệu cũ, không phải Nộp/Approve M4: không copy hoặc đổi nhãn nút để bỏ gate. Giữ Nộp hiện hành, DU_AN confirm, reviewer, approval/PDF và AP/Request đúng kế hoạch.

## 3. Correction và ranh giới backend phải khép

- **RC01 — raw NULL khác explicit0:** `review_compute.khong_nhan_dang207–228` hiện chỉ ghi numeric giá trị nhỏ, bỏ nhãn có ô blank/NULL; source `doi_chieu_tham_so679/768–769` có thể coerce thiếu thu hồi thành0/Đạt, rồi companion258–274 cho CHECKED. Phân biệt actual raw/source states NULL/missing/observed0/not-recognized/provider-error; thiếu căn cứ không được có coverage tốt hơn physical0. Giữ nguyên finding/threshold vendor, không tự điền hoặc tính số để hợp thức hóa.
- **RC02 — eligibility K2:** coverage154–156 dùng tỷ lệ hiển thị đã round ở vendor347 trong khi rule gốc349 xét tỷ lệ trước round. Eligibility phải đúng counts/ngưỡng thực của nguồn, không quyết CHECKED từ số đã làm tròn; không giảm ngưỡng hoặc sửa vendor.
- Giữ **toàn bộ8 yêu cầu coverage bắt buộc tại §10 handoff gốc**: K7 thiếu target/K8 không nhận bảng, provider/state B8, B7 thiếu/cắt cây, raw0/NULL/locator, eligible thresholds/limits, nonempty và missing controls, input states, persisted/UI/report cùng semantics. Không dùng empty findings, catch lỗi hoặc KHONG_AP_DUNG giả để báo Đạt; K7 LIMITED phải giữ giới hạn khi trình bày B7. First-period/prior-approved-history chưa bind thì chưa tự suy từ số đợt hay vắng dữ liệu.
- **Manual-map SQL visibility:** policy SELECT `review_manual_map` không được chỉ OR current REVIEW của project. Buộc visibility của origin run/raw/dot hiện hành, dùng `review_doc_duoc(run_id)` hoặc guard tương đương cùng PN/project; reviewer không thấy map từ draft/unsubmitted/unrelated source qua direct ordinary SELECT. Giữ current XEM/SOAN behavior hợp lệ, không cấp/regrant thêm quyền để qua positive.
- Hoàn thiện service: current module+PN+project/exact source scope trước lookup/replay/download; reviewer-only trên exact submitted dot/raw chạy và replay được không cần SOAN; old SOAN receipt giữ nguyên. Exact original body/key replay trả stored FINAL trước token/work; changedH409 trước effect.
- **One owned RR capture → compute không credential/PG → current-rights + whole-basis CAS publish.** Basis đầy đủ raw/extraction/catalog/confirmation, effective PL/BOQ, parameters/states, date/period, maps và available approved-prior; không dùng GUI truncated rows hoặc chỉ vài pointer. PL metadata chưa đủ GT/parameter/BO semantics thì INCOMPLETE, không default0/DA_NOP-as-approved.
- Reuse `NR.projection_l2` in-memory/query_only và source compute. Không call legacy `cs.kiem_dot` vì wrapper có journal/commit; giữ report builder đã tách. Unique CreateNew-owned run paths, retained input/temp/partial/output và artifact H/length; source/map/quyền đổi không publish current result, giữ STALE/error evidence. Không giữ DB lock toàn CPU run hoặc coi timeout là PASS.

## 4. Exact13paths giữ nguyên, không mở scope

Tất cả source dưới `src/kho_tri_thuc/`; hiện8existing editable,5absent;354source protected, final pathset mục tiêu367 theo Root scope binding.

| Trạng thái | Đường dẫn được ghi |
|---|---|
| Existing | `src/kho_tri_thuc/ha_tang/pg_migrations.py` — chỉ hoàn thiện M19 append sau protected toàn bộ1–18 |
| Existing | `src/kho_tri_thuc/m4/nguon_review.py` |
| Existing | `src/kho_tri_thuc/k2/xay_dung.py` |
| Existing | `src/kho_tri_thuc/giao_dien/m4.py` |
| Existing | `src/kho_tri_thuc/m4/giao_dien/m4.js` |
| Existing | `src/kho_tri_thuc/m4/giao_dien/m4.css` |
| Existing | `src/kho_tri_thuc/m4/review_compute.py` |
| Existing | `src/kho_tri_thuc/m4/sql_review.py` |
| Absent, tạo mới | `src/kho_tri_thuc/m4/giao_dien/review.js` |
| Absent, tạo mới | `tests/test_m4_review_compute.py` |
| Absent, tạo mới | `tests/test_m4_review_k2.py` |
| Absent, tạo mới | `tests/test_m4_review_http.py` |
| Absent, tạo mới | `docs/BAO-CAO-M4-02A.md` |

## 5. Điều kiện hoàn thành lượt code-only

- Hoàn thiện luồng chọn captured file → Review → xem bảng/nguồn/cây → ghép/chạy lại → lịch sử/report bằng bố cục nguồn. Test source phải kiểm meaningful positive/negative, scoped rights/current replay và async behavior theo handoff; viết test nhưng **NOT_RUN_CODE_ONLY**.
- Report liệt kê file/component dùng nguyên, seam thích nghi, phần chưa nối; tách code/selftest/Root independent/GUI. Không tự nhận full L1/L2/M4 hoặc runtime PASS; full L3/OCR/jobs/reports/reviewer approval/PDF/NT–AP/Request vẫn giữ để giao tiếp, CAD deferred/M9 dừng.
- Không sửa vendor/reference/app gốc/master/quyền/oldseed/CRM/M9/guard/runtime controller, không thêm file ngoài13targets. Không DELETE/DROP/TRUNCATE/cleanup/overwrite artifacts. Không import/AST/test/SQL/server/Node/browser/Office/AI/OCR/network/credentials hoặc chạy subprocess. Chỉ5filetools code-only được Root cấp; không Agent/Task/dispatch/session khác. Root terminal/stop/scope/freeze rồi mới release kiểm độc lập.
- Guard nguồn kỳ trước: `phu_thuoc124–126` hiện đặt `TRUOC.dot_dau` chỉ từ `so_dot==1`, rồi coverage255–264 bỏ dependency/cho KHONG_AP_DUNG. Ordinal1 không chứng minh provider prior-approved đầy đủ hoặc thật sự không có đợt trước; thiếu nguồn giữ INCOMPLETE, không tự tạo approval/provider hoặc vắng=0.
- Chốt cách UI ít dependency: working `review.js` tái dùng template/helper nguồn, `m4.css` scope và exact route trong `giao_dien/m4.py`, tất cả trong13targets; không import vendorJS trực tiếp để rồi cần sửa/thêm package-data hoặc `pyproject.toml` ngoài scope.
