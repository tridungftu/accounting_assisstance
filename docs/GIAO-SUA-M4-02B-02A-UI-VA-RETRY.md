# M4-02B FIX02A — sửa UI, pending intent và retry

Trạng thái: CODE_ONLY_PLANNED_ROOT_RELEASE_REQUIRED. Đây là gói sửa hữu hạn trong M4 đầy đủ đã chốt, không thay phạm vi module hay kiến trúc. Claude là bên sửa mã; Root cấp release và kiểm độc lập sau terminal. Không tự chạy lệnh/test/SQL/launcher/provider/Office; chỉ dùng Read/Glob/Grep/Edit/Write trong scope.

## Căn cứ và kết quả trước lượt này

Dùng code hiện hành, tận dụng chung kttChung của app.js và màn Chứng từ L3. Không dựng framework trạng thái, engine, master hay server khác. FIX01 đã có 28/28 kiểm thuần, 7/7 tình huống native độc lập và async U1–U7 chạy đạt; các kiểm này chưa phủ các race dưới đây. Không nói L3 hay M4 hoàn tất từ những kết quả này. HTTP/PG/current rights/GUI và các phần duyệt/PDF, kế toán/công nợ, Request vẫn còn trong hàng chờ.

## Scope sửa đúng 3 file hiện có, không tạo file mới

1. `src/kho_tri_thuc/m4/giao_dien/chung_tu.js`
2. `tests/m4_02b_async.cjs`
3. `docs/BAO-CAO-M4-02B.md`

Mọi file khác chỉ đọc. Không sửa adapter/vendor, app.js, shell m4.js, HTTP, service, SQL/migration, CRM, M9 hoặc phần mềm nguồn. Không xóa file/lịch sử/intent chưa rõ kết quả. Không sửa các invariant quyền, receipt/key/body hay ngưỡng nguồn để làm test xanh.

## U-A — continuation phải giữ ngữ cảnh gốc sau mọi await

Hiện `moSau` await `napDs()` rồi gọi `moRun(r.run_id)` không xét lại fence của ý định gốc. `napDs` mất hiệu lực chỉ return void, nên continuation cũ có thể lấy fence mới và mở run A dưới hồ sơ B.

- Bind continuation của chay/chay-lai với context gốc (actor/PN/project/HĐ/đợt/tab/generation/run); kiểm sau mỗi await trước follow-up GET/detail/render/toast/cleanup.
- Kết quả A mất hiệu lực không được mở/hiển thị dưới B, kể cả tài khoản có quyền cả A và B. Không dùng một fence mới để hợp thức hóa continuation cũ.
- Test giữ follow-up GET sau POST ACK, rồi đổi đợt/HĐ/vai; nhả GET cũ và xác nhận không phát effect/detail/request của context cũ lên context mới. Có same actor đổi PN/project và đường teardown/mount thật của shell/common barrier khi phù hợp.

## U-B — marker đang gửi phải có ownership theo incarnation

Hiện `dangGui` là Set chuỗi, ACK/error cũ xóa nhãn trước hoặc bất chấp fence. Trong A POST1 → B → A POST2, completion POST1 có thể nhả marker POST2 và cho phát POST3 dù POST2 còn bay.

- Marker gắn exact intent/ticket/record và scope; chỉ chủ marker hiện hành được nhả. Cả success, lỗi rõ và UNKNOWN đều phải giữ ownership đúng.
- Không chỉ dựa vào button.disabled: hàm hành động cũng chặn trùng đúng target đang bay.
- Test A→B→A, POST2 còn chờ; trả success và error của POST1 muộn, nhập thêm/bấm lại phải 0 POST3. Kiểm cả sửa metadata và row-map khi dùng cùng cơ chế.

## U-C — UNKNOWN không mất đường đối soát hoặc khóa form khác

Hiện một `guiLai` bị gỡ khi đổi đợt/tab hoặc bị lệnh khác ghi đè; marker `sua`/`ghep:row` có thể vẫn giữ. Form mới bị khóa vô hạn, intent cũ không còn retry; hoặc UNKNOWN lệnh sau làm mất retry lệnh trước.

- Giữ đúng body/key/route/target/scope của mỗi intent UNKNOWN, có đường đối soát hữu hạn cho đúng intent. Có thể dùng cấu trúc hẹp theo context/intent hoặc tuần tự hóa khi còn UNKNOWN, không thêm generic queue framework.
- Đổi vai/PN/project/HĐ/đợt/tab không mang marker cũ sang form mới, không làm mất khả năng đối soát khi trở lại đúng context và còn quyền. Không chặn đổi vai để giữ dữ liệu cũ; không hiện private view của actor/phạm vi cũ trong context mới.
- Không tự tạo key mới hoặc tính lại khi chưa rõ kết quả. Không coi HTTP200 JSON đứt, mất kết nối hay 5xx là thành công hoặc thất bại chắc chắn.
- Test UNKNOWN→đổi đợt→trở lại, UNKNOWN→tab away/back, sửa UNKNOWN→ghép hoặc hai row-map UNKNOWN; mọi intent còn đủ retry/body/key hoặc lệnh kế tiếp bị chặn có giải thích. ACK đối soát chỉ dọn đúng giá trị đã gửi, giữ chỉnh sửa mới.

## U-D — dấu đủ/thiếu theo đúng tolerance nguồn

Ma trận hiện dùng 1e-9 trong khi C01/C03 nguồn chỉ phát thiếu khi chênh vượt max(1e-3, abs(observed)*1e-6). Không để ma trận đánh dấu thiếu ngoài ngưỡng nguồn.

- Chỉ hiển thị kết luận lượng khi typed SO_DUOC; giữ NULL/0, UOM và các trạng thái chưa so được đúng như FIX01.
- Dùng đúng threshold/source operands cho phần trình bày, không đổi thuật toán nguồn hoặc thêm engine. Không suy dấu đủ từ việc không có finding.
- Test biên hai phía ngưỡng tuyệt đối và tương đối cho NT/KL kỳ này và GN/KL lũy kế, cùng NULL/khác UOM/0. Giữ toàn bộ assertions U1–U7 trước đó, không nới expectation hoặc xóa case để pass.

## Bàn giao trong lượt hữu hạn

Ưu tiên sửa đúng các nhánh trên và bổ sung regression có lịch Promise điều khiển; đọc lại phần đã sửa. Không sa đà khảo sát phần không thuộc scope. Cập nhật báo cáo rõ từng thay đổi, test đã viết và NOT_RUN_CODE_ONLY; không tự ghi đã chạy hay đã nghiệm thu. Ghi rõ các điểm backend/adapter/PG/HTTP/GUI còn chờ ngoài gói này. Kết thúc bằng tóm tắt file đã sửa, tiêu chí đã xử lý và phần chưa xong. Không có công việc sau report trong cùng lượt.