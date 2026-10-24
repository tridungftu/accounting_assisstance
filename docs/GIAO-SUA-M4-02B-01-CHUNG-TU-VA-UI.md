# Giao sửa M4-02B FIX01 — hoàn tất Chứng từ L3 dùng lại nguồn

**CODE_ONLY_AUTHORIZED_SCOPE / ROOT_RELEASE_REQUIRED.** Chỉ được giao sau Root xác nhận các lượt kiểm sở hữu đã dừng, pin baseline và public handoff. Tiếp tục cùng session Claude đang dùng; một product writer. Không chạy product/import/test/SQL/Office/GUI/launcher/CLI/network; chỉ dùng Read/Glob/Grep/Edit/Write trong scope đã cấp. Không xóa file, không cleanup/reset hoặc sửa vendor/nguồn ứng dụng thật.

## 1. Mục tiêu và hiện trạng cần giữ đúng

Hoàn tất **toàn gói M4-02B Chứng từ L3** theo `docs/GIAO-CODE-M4-02B-CHUNG-TU-L3.md` và kế hoạch M4 đã chốt, tận dụng nguyên reader/matcher/C01–C09 của Review xây dựng. Bản vừa viết còn thiếu async test, report mới là stub và có các lỗi dưới đây; không coi timeout của writer là hoàn tất. Root đã chạy bộ native16:15 đạt,1 lỗi thuộc fixture sinh lại XLSX, không phải16/16. Các lỗi coverage/UI/service còn phải sửa và kiểm độc lập, không được dùng số test này thay full-L3 acceptance.

M4-02C duyệt/PDF seal, M4-03 KT/commonAP và M4-04 Request vẫn gói sau. Review findings/matrix không là NT/thanh toán được chấp nhận. Không nối lại M9, không nhập Junsky, không cloudAI/realRequest/realapproval; dữ liệu thật và kho thậtSQLite không chạm.

## 2. Lỗi service/adapter cần sửa

1. **L2 stale so với current basis.** `k2/xay_dung.py:_chung_tu_co_so` đang chọn latest published L2 có bảng dòng nhưng chưa chứng minh L2 basis còn đúng HĐ/PL/BOQ/ngày/ghép tay/source hiện tại. L3 adapter lấy quantities L2 cũ nhưng BOQ current. Kiểm exact dependent basis/file/dossier/version phía server trước khi cấp `l2=CO`; giữ historic result/run, nếu stale thì refs/lý do rõ và BOQ-only/INCOMPLETE hoặc yêu cầu chạy L2 lại. Current L3 CAS không thay kiểm correspondence L2↔current; không sửa `cong_bo` lịch sử để che stale.
2. **C01/C03 quantity NULL hoặc chứng từ0 dòng.** Companion chỉ gate source=L2 và NULL của dòng chứng từ, chưa kiểm `kl_kn/kl_lk` thực cần so của matched item. Vendor bỏ branch quantity thiếu, nhưng companion vẫn CHECKED. Có BB_NT/BB_GN không table/rows cũng có thể CHECKED. Kiểm coverage theo operands thật/row/item/scope; NULL khác0, không suy chưa thấy=0. Thiếu→INCOMPLETE/LIMITED có lý do. Không đòi mọi HM không liên quan đều đủ lượng và không sửa original C01/C03 findings.
3. **C06 UOM cross-document.** Hai ĐVT không rỗng nhưng khác GN↔CO/CQ/PL vẫn có thể CHECKED; nguồn cùng hàng theo model/lô/tên và so numeric không theoĐVT. Companion phải xét comparability từng cặp, dùng normalization nguồn; thiếu/khác/mapping chưa được xác nhận→không tuyên bố so lượng. Không tự factor/quy đổi; serial/lô/ngày còn kiểm được giữ riêng. Giữ raw vendor numeric findings và thêm status trình bày đúng phần so được/chưa so được.
4. **DOCX form chưa đọc dòng hàng.** Source trả canh_bao không table/ai=None nhưng adapter vẫn docCHECKED, C05/C06 coi bộ đã đọc đủ. Giữ metadata đọc thật, tách trạng thái đọc dòng/provider/coverage thành LIMITED/NOT_AVAILABLE/NOT_CONFIGURED đúng thực tế; tài liệu đã có nhưng chưa đọc được không thành thiếu tài liệu chắc chắn. Không gọi AI hoặc tạo rows giả; C09 finding gốc vẫn giữ.
5. **Manual target stale cùng mã HM.** Persisted map giữ `boq_id/boq_dong` nhưng adapter tạo callback chỉ còn ma_hm và áp nếu mã còn tồn tại. PL THAY/reimport BOQ giữ cùng mã nhưng target row/version đổi có thể tự áp quyết định cũ lên nguồn mới. Giữ exact selectedBOQ ID/physicalrow/sourcePB/effective basis và raw row identity/revision trong worker provenance; kiểm target hiện hành trước áp. Khác target→STALE/NEEDS_RECONFIRM và auto fallback rõ, không silently DA_AP chỉ nhờ cùng ma_hm. Service đã có `_dich_hieu_luc` cho lệnh Ghép mới: giữ guard đó, sửa đường áp **map cũ**; không gọi đây là ordinary SQL bypass. Raw/auto/map history cũ không xóa/ghi đè.

Không viết lại rule engine hoặc nâng ngưỡng nguồn để tránh finding. Bổ sung typed per-item/per-pair comparability để UI/report dùng đúng; coverage tổng không chứng minh một dòng đủ lượng. Giữ cùng owned credential-free worker, admission trước reader, physical locators trước compressedblankrows và bất biến bytes/hash/length. Unsupported/provider/TrackChanges vẫn trạng thái thật.

## 3. Lỗi UI và HTTP cần sửa

- **UI01 edit→Save:** `chung_tu.js` sửa loại/số/ngày chỉ ghi ui.sua nhưng không bật nút Lưu. Cập nhật enabled state khi edit không render lại toàn form mỗi phím làm mất focus. Payload/căn cứ/revision đúng; ACK chỉ dọn đúng draft đã gửi.
- **UI02 dấu đủ lượng sai:** cột Đã giao có thể ✓ khi kl_lk=NULL; NT/GN không xét ĐVT/căn cứ so được. Phân biệt có tài liệu với đủ lượng; khi NULL/UOM khác/không rõ→chưa so được/— có lý do. Giữ0 tường minh. Dùng comparability typed theo đúng row/item, không một cờ coverage toàn bộ để làm xanh từng dòng.
- **UI03 UNKNOWN→retry ACK:** generic Gửi lại chưa chạy completion cleanup của sửa metadata/Ghép; draft cũ còn giữ, có thể tạo append/key mới sau ACK. Intent phải giữ payload/key và completion semantics gắn form generation; retry cùngkey thành công dọn đúng thay đổi gốc nếu draft vẫn đúng, không xóa edit mới. Không phát command mới chỉ vì UI giữ nhầm draft đã lưu.
- **Detail/artifact race:** chọn runB phải clear/disable detail artifact của runA hoặc bind nút/download với exact runA; không lấy runChonB ghép artifactA. Luôn current rights và byte/hash phía backend.
- **Late error fence:** GET detail error sau người dùng edit/đổi context không rerender/toast/dọn draft mới sai generation. Success/error/retry/download đều fence actor/PN/project/dot/run/tab/connected/generation phù hợp. Thu hồi quyền403/404 xử lý có chủ ý, không che revoke.
- **Strict query:** detail/download L3 hiện bỏ query lạ/lặp. Reject theo contract `_q(query,set())` hoặc helper tương đương và test đúng status; không cấp authority từ query.
- **HTTP assertion H02:** top-level authority actor/PN/path trả403; thêm top-level tai_lieu vào route chay là unknownfield400, không403. Tách assertions đúng validator thực. Nested authority kiểm trên route sua hợp contract; không nới allowlist để thỏa expected sai.

## 4. Hoàn thiện tests có ý nghĩa và report

- Giữ các case/assertions gốc về source findings, quantities/metadata/physical rows; chỉ sửa fixture bytes identity cho đúng actualinput: tạo XLSX một lần, giữ tuple/raw đó, tính expected row_id từ **chính raw đã cấp**, không serialize workbook lần2 hoặc lấy expected từ output sản phẩm.
- Thêm native pure cases L2 kl_knNULL/kl_lkNULL/explicit0, NT/GN0rows, CO/CQ form không table, GN↔CO/CQ/PL differing/unknownUOM và per-pair lot/date còn kiểm được, map target đổi cùng mã, missingbasis. Không skip lỗi rồi cộngPASS, không đổi vendor/checks để hợpgolden.
- Thêm K2/HTTP cases actual staleL2basis, current effective target đổi cùngma_hm sau PL/reimport, revision/manual replay/cross-PN/revoked/currentrights before receipt/file/publish, statusassertions và strictquery. Chứng minh raw/auto/history giữ; map cũ stale không được DA_AP hoặc âm thầm rebind.
- **Hoàn thành NEW `tests/m4_02b_async.cjs`** bằng harness hiện có, thực thi UI code thật trên fakeDOM/fetch có kiểm payload. Các luồng tối thiểu: edit từng trường→Save enabled/payload đúng; UNKNOWNretry→ACKcleanup; edit mới khi requestpending giữdraft; crossrole/dot/run/tab staleACK+lateerror; run/detail/artifact exactbinding; NULL/UOM/0 matrix; stale same-key body conflict; source/metadata/manual revision refresh. Không chỉ regex/search/comment asserts, không assertions mirror implementation.
- Không thêm framework/deps. Không gọi product/test/SQL/Office/GUI hoặc CLI trong lượt CODE_ONLY; Root tự chạy sau actual terminal/freeze/fullreview.
- Hoàn thiện `docs/BAO-CAO-M4-02B.md`: files/contract/service/routes/UI/schema/coverage/limits/provider/reuse thật; phân biệt code và test NOT_RUN_CODE_ONLY. Không tự gọi fullM4/GUI/PDF/AP/Request done. Missing async/reportstub không được ghi đãxong.

## 5. Schema và scope cứng

Giữ nguyên toàn prefix SQL1–21 (927604 bytes, SHA256 `0e87d8e1a39aef582d79ffd7cef30b7dcdf523d151009729e6cb1d5b64452dce`) và nguyên `m4/sql_review.py`40029 bytes/SHA256 `273cb440b22f3d646cf2145e8bbcf9b56c9944fe607860e37c9cea05a161881f`. M22 của gói02B chưa được áp DB trong vòng kiểm này: có thể sửa **candidate M22 hiện hữu** khi cần vì chưa phát hành, không appendM23 để che thiếu. Không chạy migration hoặc tự coi schemaDBđã22. Root phải xác nhận gate M22 chưaapplied trước dispatch.

**13 file hiện có được sửa:**

1. `src/kho_tri_thuc/giao_dien/m4.py`
2. `src/kho_tri_thuc/ha_tang/pg_migrations.py` — chỉ suffixM22, giữ prefix1–21
3. `src/kho_tri_thuc/k2/xay_dung.py`
4. `src/kho_tri_thuc/m4/giao_dien/m4.js`
5. `src/kho_tri_thuc/m4/nguon_review.py`
6. `src/kho_tri_thuc/m4/review_compute.py`
7. `src/kho_tri_thuc/m4/chung_tu_adapter.py`
8. `src/kho_tri_thuc/m4/giao_dien/chung_tu.js`
9. `src/kho_tri_thuc/m4/sql_chung_tu.py`
10. `tests/test_m4_02b_http.py`
11. `tests/test_m4_02b_k2.py`
12. `tests/test_m4_02b_pure.py`
13. `docs/BAO-CAO-M4-02B.md`

**Chỉ1 file mới:** `tests/m4_02b_async.cjs`. Tổng14targets. Các source/vendor/references và các module khác read-only, không editfiles ngoàiallowlist hoặc viết thêm helper/control/launcher. Không đưa realdata/secret/env/credentials/backup vào code/prompt/report. Root có bộ kiểm độc lập riêng; không nhận oracle private hoặc sinh expected bằng output sản phẩm.

Kết thúc phải nêu files actualsửa/mới, điểm còn chưa chạy và từng finding đã xử lý bằng function/line/contract nào. Hoàn tất phạmvi L3 đã giao; không dừng ở test xanh giả hoặc phầnmôphỏngkhôngUI.
## 6. Bổ sung từ review SQL/service — hữu hạn, không framework

- Worker output phải kiểm shape và **mọi scalar/number trong full tree hữu hạn**, không chỉ top-level keys. Không chấp nhận JSON NaN/Infinity hoặc structure sai rồi để canonical_json/publication ValueError thoát sau RUNNING. Mọi nonDB exception sau worker đã dừng phải giữ evidence và thử đóng terminal FAILED/CANCELLED đúng phạm vi một cách hữu hạn; không RUNNING vĩnh viễn khiến retry luôn dang_chay. Không ghi PASS/FINAL thành công khi validation lỗi.
- Commit DB không rõ kết quả là UNKNOWN riêng: đối soát same operation/key/run/domain state trước trả/tiếp tục; không compute lại hoặc dùng key mới. Không cam kết FAILED khi thực tế commit chưa biết; giữ receipt/evidence và thông báo đối soát đúng. Không cần queue/scheduler mới.
- Test K09 phải join(timeout) có hạn, assert is_alive và cleanup/stop thread/owned worker trong finally; setup đăng ký cleanup ngay sau mỗi resource được tạo để raise giữa chừng vẫn đóng connection/server/threads đúng sở hữu. No-delete: không dropDB/roles hoặc cleanup file. Giữ artifacts/failed receipts.
- Thêm positive REVIEW trên DA_NOP, XEM-only deniedmutation và revoke current rights trước replay/file/publish, directSQL và effective PL cases phù hợp. Reservation được giữ sau failed precondition là retained slot, **không mặc định là deadlock** và không sửa bằng xóa record/history. Chỉ sửa lỗi có evidence, không bẻ mô hình bảo toàn để test dễpass.
## 7. Clarification về quyền analysis và fixture ghép tay

Giữ SOAN precheck như Review M19: analysis/metadata/map append revision có actor/reason/currentgraph, kể cả sau nộp, **không** formalapproval/DUYET/acceptedNT/AP. REVIEW vẫn chỉ đợt DA_NOP và đúng project/quyền hiện hành. Không nới business grants, cũng không bắt DUYET để chạy engine analysis; gói02C sẽ tách quyền DUYET và pin exact graph.

Case manual thuần cũ chỉ có boq=[]/ma_hm-only từng đạt là fixture chưa đủ contract stabletarget mới. Khi sửa, dùng fixture có BOQ/effective target thực hợp lệ và explicit ID/physicalrow/provenance; không weaken invariant để giữ fixture xanh. In-memory SQLite projection dùng seam Review hiện hữu để tính effective BOQ được phép trong test thuần; không mở legacy fileDB hoặc full/M9 bootstrap. Báo rõ phần in-memoryprojection khác PostgreSQLintegration.
## 8. Lỗi header nguồn được phát hiện khi kiểm native độc lập

Bộ đọc nguồn `may_chu/chung_tu.py:_cot` xét nhánh nhà sản xuất với pattern `hang$` trước cột tên. Header rõ nghĩa “Tên hàng” vì vậy có thể bị nhận thành NSX, khiến `dong_hang` dùng model làm tên dù ô tên thật đã có. Đây là lỗi bảo toàn dữ kiện, không được đổi expected thành model để làm test đạt. Root đã chạy kiểm native bằng bytes DEMO gốc; nhiều ca dừng ở cùng lỗi header này, chưa chứng minh các assertion phía sau đạt.

Sửa trong adapter compatibility mỏng/worker-local dùng lại parser nguồn: nhận diện đúng header tên rõ nghĩa rồi ánh xạ sang alias mà chính parser hỗ trợ (ví dụ “Tên vật tư”), hoặc seam cột cục bộ tương đương có provenance. Giữ nguyên raw file/cell/header/trích dẫn, bản trích nguyên nguồn và dấu vết alias/column adaptation; không ghi đè hay sửa vendor/source app, không monkeypatch module server hoặc viết lại parser/engine. Không áp alias cho “Hãng”, “Nhà sản xuất” hay header mơ hồ; trường chưa rõ giữ chưa xác định. Tên hàng và model phải giữ riêng đúng nguồn. Thêm fixture native có cả tên, model và NSX để kiểm không tráo cột; không lấy output sản phẩm sinh expected. C01–C09/ngưỡng gốc tiếp tục nguyên vẹn.