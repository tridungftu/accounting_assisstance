# CRM-41-02 — tiếp tục lượt code dang dở và sửa phát hiện kiểm độc lập

**21/10/2026 · CODE_ONLY · cùng session Claude hiện có · chưa có runtime/GUI PASS.** Tài liệu này bổ sung `GIAO-CODE-CRM-41-02-MAU-DOCX-G7-S6.md`; giữ nguyên nghiệp vụ CRM41–42, phạm vi G1/G7_MIN/S6 và các phần còn lại trong hàng chờ. Không yêu cầu Anh chốt lại kiến trúc.

## 1. Hiện trạng thực tế và phạm vi sửa

- Lượt trước: handle70436, terminal `eca51c`; hết giới hạn1800 giây, exit1, chưa có result/report hoàn tất. Đã xác nhận tiến trình dừng, scope check đạt, không có lỗi kiểm phạm vi. Không được đổi thành native success hoặc coi timeout là kết quả kiểm sản phẩm.
- Bản đã lưu có358 source files,424 runtime files;345 existing files được bảo vệ. Sáu file existing thay đổi và sáu file mới đã có. Đây là partial, chưa nghiệm thu CRM/M4.
- Còn thiếu `tests/test_crm_41_02_http.py` và `docs/BAO-CAO-CRM-41-02.md`. `app.js` hiện nguyên byte C4; không bắt sửa nếu integration dùng được seam hiện có.
- Vẫn đúng15 write targets của handoff gốc:13 hiện đã tồn tại được sửa trong phạm vi này, chỉ hai đường dẫn thiếu ở trên được tạo mới. Không thêm file sản phẩm/test/helper khác.
- Giữ nguyên791902 byte đầu `pg_migrations.py`, SHA36ed5ad1035f3cf85593cbfdc2e5ca84b3a73ecffd1df010aa4987d6826b3964; chỉ sửa phần M18 đã append. Không thay17 migration cũ, M17 imported, COMMON13 hoặc khôi phục full M9.
- `tests/m4_01c_async.cjs` đã có đúng sửa setup, SHA phải giữ `f77bdfe66772a2494d36f40cb1f2119d27af351ae8f101b1a3dc42bd9274a9d2`. Không thêm hai câu selection lần nữa, không sửa assertion. M9 byte block và các module/file khác tiếp tục bảo vệ.

## 2. S01 — giữ transaction upload đến FINAL

Source hiện tại `crm_mau.py:148–151` commit transaction tra receipt; `tai_mau:301–308` parse/ghi blob sau đó, rồi mở transaction khác để ghi command. SQL namespace lock là `pg_advisory_xact_lock`, đã thả khi preflight trả về.

Hai request cùng actor/action/key nhưng H khác có thể cùng thấy chưa có receipt; request thua vẫn parse/ghi artifact rồi mới nhận409. Khoảng tách transaction cũng làm quyền có thể đổi giữa preflight và filesystem.

- Sửa bằng cùng owner connection/transaction từ current-authority + namespace preflight qua parse/artifact/command/immutable FINAL. Không gọi helper tự mở transaction khác hoặc dùng connection thứ hai tự chặn nhau.
- Exact same-body replay trả FINAL trước parse/blob; changed H bị409 trước parse/staging/blob, không xóa artifact để che delta. Giữ primitive lưu bất biến/retained hiện có.
- Chứng minh ranh giới quyền và namespace dưới thao tác đồng thời: revocation thắng trước protected preflight phải deny không có filesystem delta; không để giao dịch bị từ chối cuối cùng đã tạo artifact vì preflight hết hiệu lực. Không dựng IAM/approval engine mới.
- Bổ sung ca có hai service/owner connections thật: giữ request A ở parse bằng wrapper vẫn gọi parser thật, request B cùng key phải chờ đúng namespace; A FINAL xong, B khác H nhận409 mà không parse/ghi file. Có positive nonempty, same-H replay và observer file/row/sequence/audit counts. Không dùng global LocalApp mutation lock làm bằng chứng cho service nhiều connection.

## 3. P01/P02 — parser không bỏ sót theo encoding/kênh

Hai counterexample tĩnh, chưa chạy:

- `_parse:61–67` dò DOCTYPE/ENTITY bằng ASCII-byte regex rồi `ET.fromstring(raw)`. XML UTF-16 có thể vượt guard. Chặn DTD/entities trước traversal với cách xử lý encoding nhất quán/an toàn cho mọi XML đã nhận; không chỉ thêm một regex trên UTF-8. Giữ kiểm bounds, lỗi semantic riêng và ca valid đối chứng.
- `:267–279` dò ngoặc trong raw XML của kênh chưa quét. Footnote/endnote/comment có dấu ngoặc hoặc token tách qua các `w:t` không chứa byte `{{`/`}}` liên tục, có thể bị bỏ qua và trả DU. Kênh hiển thị chưa hỗ trợ phải reject hoặc INCOMPLETE rõ, chặn kiểm/duyệt; không suy complete từ không tìm được regex raw. Giữ body/table/nested/referenced header/footer đúng, không ghép qua paragraph/cell/part.

Thêm native cases cho UTF-16 DTD/entity và kênh chưa hỗ trợ có ngoặc tách run, cùng positive hợp lệ. Chỉ generic exception/setup error hoặc COMPLETE+0tokens không phải safety PASS. Không đọc private Root corpus/oracle.

Hoàn thiện output theo handoff§65: giữ paragraph/joined-text spans và provenance run có thể kiểm chứng. Hiện `runs` chỉ có indices, `ngu_canh` cắt400 ký tự. Bổ sung full joined paragraph text trong giới hạn đã chặn và character spans thực trong từng run, với đơn vị/chỉ số rõ; tính từ traversal thực, không từ tên placeholder/oracle, không byte-span giả hay ET.tostring hash. Giữ các field đang dùng trên UI; provenance không bị bịa sau parse.

## 4. U01/U02 — một upload intent, fence đúng context

Source `crm_g.js` hiện có các đường sau:

- `taoYDinh:153–157` chỉ lấy Map, nhưng Map chỉ được set sau unknown ở183. Hai click trước response tạo hai object/khóa riêng; `dangGui` per-object không chặn hai POST. Reserve đồng bộ intent trước POST đầu tiên, release/retain đúng owner, một File/body/header/key gốc cho retry cùng context.
- Upload hiện dùng `fence()` chỉ actor/epoch; đổi File/loại/mã, tab hoặc phiên bản làm `genForm` đổi nhưng intent vẫn hợp lệ. Retry/completion cũ có thể gửi, chọn phiên bản/toast/refresh trên form mới. Capture đúng context và kiểm trước request, sau từng await và trước mọi side effect; invalidation phải giữ nguyên lịch sử/file, không dùng key mới để retry unknown.
- `docChuan:259–266` cũng chỉ fence actor, không query/form/tab/generation. GET dự án/giai đoạn/ngày A về sau B có thể thay `bcDoc` và dựng lại form đang nhập. Dùng generation/query/context thật; kết quả cũ không được ghi DOM/cache/status hoặc làm mất nháp mới. Giữ shared pending-role barrier.

Ca bắt buộc: double click initial upload đúng1POST/1key; unknown cùng context retry đúng original File/bytes/header/key; đổi selection/File/tab/version/role trước completion hoặc trước retry không gửi lại intent cũ và không overwrite nháp; G7 hai GET trả ngược thứ tự chỉ lựa chọn mới nhất được vẽ. Có current-context positive để tránh khóa mọi thao tác. Đây mới là counterexample source, chưa có bằng chứng số bản ghi trùng thực tế.

## 5. Hoàn thiện kiểm thử và báo cáo

- Hoàn thiện hai file test trong15 targets, nhất là HTTP test đang thiếu: session/token thật, đúng API, positive upload→map khác tên→KT return/resubmit cùngK5→KT check→CFO+V4→effective/raw download; G7 typed4columns/as_of/CHUA_CO và các negative quyền. Giữ CRM-B CFO+V3 cũ.
- Test source/pure hiện đọc hai JSON public DEMO/prefix17. Root sẽ stage byte-exact vào runtime snapshot trước khi chạy; không tự tìm `.env`, `var`, credentials hoặc nhập dữ liệu thật. Không coi FileNotFound/setup/skip là PASS.
- Báo cáo phải ghi `NOT_RUN_CODE_ONLY`: nêu đúng timeout trước, các sửa đã viết, các test đã viết nhưng chưa chạy, giới hạn và tiêu chí còn chờ Root. SQL/static review không phải migration/HTTP/concurrency/GUI PASS.
- Trong lượt code: chỉ Read/Glob/Grep/Edit/Write, safe-mode/dontAsk/strict-emptyMCP; không Bash/Agent/session mới/worktree/AST/import/test/SQL/server/Office/AI/cloud, không xóa/rename/move/reset/cleanup. Root review và chạy kiểm sau terminal riêng.

Không thu hẹp full CRM41–42 hoặc full M4. Các phần Review L1–L3/OCR/approval–PDF/nghiệm thu–công nợ/Request vẫn giữ trong hàng chờ đã chốt; gói này hoàn thiện trước phần CRM đang dang dở.
