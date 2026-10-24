# Giao Claude CRM-41-03 FIX02 · Khép GUI G2/G3 và Word local

Ngày 21/10/2026. Root giao tiếp trong same Claude session, CODE_ONLY. Kế thừa main `GIAO-CODE-CRM-41-03-BAO-GIA-VA-SOAN-HD.md`, FIX01, đặc tả CRM 41–42 và engine dùng chung. Áp dụng binding mới `CRM-41-03-WORD-OWNERSHIP-FIX02.md` cho riêng ownership/native tests. Tái sử dụng code hiện có, không viết lại G2/G3/G1/G7, calculator, master hoặc engine.

## 1. Baseline và phạm vi ghi

- F16 đã terminal, scope đúng. Root đã chạy: AST 6 file đạt; 31/31 pure/DOCX/mock-PDF đạt; 11/11 CJS fake-DOM đạt, gồm A3 cũ. Những kết quả đó không chứng minh các nhánh bổ sung bên dưới, Word thật, PostgreSQL toàn bộ hoặc GUI thật.
- Root tái hiện ba tình huống bổ sung trên actual UI code với fake DOM: Convert held rồi gõ cùng báo giá và nested list về làm mất nháp; lost ACK → pending409 → In lại đổi khóa; sửa amount vẫn nhìn thấy derived cũ. Không có private oracle/runtime dữ liệu thật trong packet gửi Claude.
- Chỉ sửa **6 file đã có**, NEW=0: `src/kho_tri_thuc/giao_dien/assets/crm_g.js`; `src/kho_tri_thuc/nguon/crm_docx.py`; `tests/crm_giao_ket_async.cjs`; `tests/test_crm_giao_ket.py`; `tests/test_crm_giao_ket_http.py`; `docs/BAO-CAO-CRM-41-03.md`.
- Toàn bộ file khác readonly, gồm service tài chính, route, CSS, SQL/M21 (giữ full bytes), shared host/guard, M4/M9, source Review/engine, reference/staged patch. HTTP test chỉ sửa fixture hợp lệ và bổ sung kiểm chứng; không hạ assertion. Không đổi dependency/launcher/settings/master/quyền để né test. Không đọc var/.env/backup/real data/credentials. Controller Root dùng riêng, Claude không được đọc.

## 2. GUI cần khép

1. **Pending giữ ý định gốc.** `CRM_GK_DANG_XU_LY` và `CRM_GK_LAN_KHONG_KHOP` là pending/unknown409; giữ original body/key/phase qua lost ACK → đối soát → FINAL. Không xóa key rồi phát K2/Word/render mới cho ý định chưa rõ. Chỉ nhận đúng recoverable codes, không biến mọi409/body-conflict/revision/permission thành retry. Hiển thị đang xử lý/chưa rõ và thao tác đối soát y nguyên, không auto retry loop.
2. **Fence xuyên toàn callback.** Original epoch/actor/selection/mode/**form generation** được giữ từ trước command qua POST/JSON/refresh1/refresh2/toast/status/error/Convert đổi mode/retry/G7/blob. Không chụp generation mới sau await/retry. A trả muộn khi người dùng gõ B trên cùng object không được đổi B/mode/lựa chọn, hiện thông báo cũ hoặc refresh đè B. Vẫn lưu/đối soát transport intent đúng cách và giữ current positive. Nhánh Convert và retry hiện thiếu; Save/Print/Export/G7 error cũng kiểm trước mọi visible effect.
3. **Đổi template phải lưu.** Chỉ chọn template v2 hoặc lý do đổi trong G3 cũng làm draft dirty, disable Xuất + lý do ngay. Save mang đúng template/reason/revision, nạp revision mới rồi mới cho Xuất. Save/Convert nháp không bị gate Print100%/FX. `bg-mau-*` là tham số Convert, không buộc lưu quote vô ích vì đổi picker đó.
4. **Derived đang nhìn thấy hết hiệu lực ngay khi sửa.** Sửa %/amount/FX/đầu vào liên quan phải ngay lập tức đánh dấu counterpart/VND hiện trên DOM là chưa tính/chưa lưu hoặc old revision rõ; không cần đổi tab/rerender toàn form làm mất caret. Không calculator float/rounding mới trên client, không POST mỗi keystroke. Dùng cùng server preview; response cũ không khôi phục số cũ lên current form.

## 3. Word/PDF cần khép

- Triển khai đầy đủ binding `CRM-41-03-WORD-OWNERSHIP-FIX02.md`: pinned binary, single `/w`, CreateProcessW suspended → exact handles/Job → ResumeThread → PID-restricted NativeOM Window/Application/Hwnd → proof rồi mới mutate/Open. Outer child Job-before-stdin giữ. Không DispatchEx fallback/Title/PID-delta proof hoặc sửa protected host.
- Mọi nhánh parent/worker lỗi/quá hạn phải có stop witness hữu hạn hoặc UNKNOWN, không chỉ đóng Job rồi báo xong. Native Word test cũng có child/Job/deadline/cleanup từ setup, không COM call có thể treo ở test main. Availability metadata không initialize COM trước ownership boundary.
- Trong renderer, cộng counts của expected cùng normalized display text; không `max`/khử trùng làm mất multiplicity. Hai field/header/footer trùng text cần tổng số occurrence; một ký tự vẫn kiểm. Giữ `VAN_BAN_CO_BAN`, typed input và full FX/content. Không sửa service/financial policy để đạt.
- Mục tiêu vẫn là PDF thật chạy được sau Root review/release; honest NOT_READY cần báo nhưng chưa là hoàn tất. Giữ toàn bộ DOCX/PDF/attempt/file cũ, không dọn/xóa/đổi tên/ghi đè.

## 4. Test viết kèm, không chạy trong lượt này

- Giữ nguyên P0 và A1–A10 assertions. Thêm connected-handler cases: pending409 hai code → original retry FINAL cùng body/key, definitive conflict counterpart; held Convert cùng selection rồi edit trước success/error/nested GET; held retry/Save/Export và stale toast/error; template-only dirty/Save v2/new revision; derived invalidation kiểm ngay DOM trước bất kỳ tab click, late preview rồi current positive.
- Giữ ca money/scale/null/maintenance/canonical/milestone/guard hiện có. Bổ sung equal normalized display multiplicity one0 fail/two0 pass; all-error lifecycle/assign/EOF/false-unknownstop/fileexists/timeout; safe native Word positive và independent control Word giữ nguyên theo binding. Không sửa oracle để né lỗi hoặc biến skip thành PASS.
- Pure/mock tests ghi đúng nhãn; CJS fake DOM không là browser. Native provider/SQL/GUI chỉ chạy sau Root review bằng dữ liệu DEMO, giữ file. Không Python/Node/Bash/SQL/COM/Word/browser/launcher/tool khác ngoài Read/Glob/Grep/Edit/Write trong lượt code.
- **Sửa fixture HTTP:** Root đã chạy subset PostgreSQL DEMO g01/g03/g04/g05/g09: 2 PASS, 2 FAIL, 1 ERROR, không skip, toàn bộ server/thread/connection/Job đã dừng. `mau_hieu_luc` đưa human label `MAU V1`/`MAU V2` vào khóa `tai-`/`map-`/`gui-`/`kiem-`/`duyet-`, trái `KHOA_RE` của G1. Tách machine key hợp lệ, deterministic theo cùng ý định, khỏi ghi chú hiển thị; giữ nội dung DOCX, mẫu v1/v2, luồng upload→KT→CFO, replay/conflict/current-rights và toàn assertions. Không nới product regex/quyền để nhận fixture sai. g04 thiếu G7/g05 thiếu v1 là lỗi dây chuyền sau g01, không được bỏ qua hoặc đổi expected sang trạng thái thiếu. Nếu phát hiện lỗi khác, báo chính xác, không sửa protected product ngoài scope.

## 5. Bàn giao và hàng chờ

Đầu lượt cập nhật report IN_PROGRESS. Cuối lượt ghi CODE_WRITTEN/NOT_RUN, finding → sửa → test viết → giới hạn còn lại và exact file scope; không tuyên bố full CRM/M4. Thứ tự ưu tiên sửa GUI để Root kiểm và mở G2/G3 DEMO; PDF thật có bằng chứng riêng. Không gác backlog CRM catalog KCN/NHA/E3/E5/G4–G6 sang E1; M4 full Review/Cổng/L3/duyệt-PDF/kế toán-công nợ/Request và M2-00 → E1-MUA vẫn theo hàng chờ đã chốt. M9 giữ dừng, kho thật SQLite, không bật cloud AI hay dùng dữ liệu thật.
