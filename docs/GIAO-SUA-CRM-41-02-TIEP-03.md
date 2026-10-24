# CRM-41-02 — sửa tiếp03: giữ đúng chủ của nút gửi lại tệp

Đây là lượt sửa kỹ thuật CODE_ONLY trong phạm vi CRM41–42 Anh đã chốt. Tiếp tục cùng Claude UUID `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`. Không đổi nghiệp vụ, schema, quyền hay kiến trúc. Root sẽ kiểm độc lập sau terminal.

## Phạm vi

- Chỉ sửa hai file đã có: `src/kho_tri_thuc/giao_dien/assets/crm_g.js` và `docs/BAO-CAO-CRM-41-02.md`. NEW0; 358 source khác giữ byte-exact.
- Giữ nguyên parser, pure/HTTP tests, M4, `tests/m4_01c_async.cjs`, app/index/CSS, server/API/service/seed/bootstrap, toàn migration1–18, nguồn Review dùng lại, fixtures và M9.
- Baseline repair02 owned50595/terminal71e7d2 đã kết thúc, exit0, stop/scope/posthash đạt. JS hiện578 dòng, SHA256 `2c399e8581fdce6cec14bb3c133609b196dcde008b24ef071d9b5f88e72b946e`; report `27ceaad90f6a14a5c52877afc2c05bbe0f627df8b3fa271bb1b199c8eda98073`.

## Lỗi đã được Root tái hiện

Mở v1 → upload A đang chờ → sửa mapping → bấm lại cùng nút upload, cùng File/loại/mã để tạo intent B → B trả500 chưa rõ kết quả, nút gửi lại B xuất hiện → A trả thành công muộn. Callback A đang làm mất nút gửi lại của B.

Trong `giuChoYDinh` dòng180, chuỗi intent không có `genForm`; A/B có chuỗi giống nhau dù key khác. Dòng183 cho tạo B sau khi form đổi. Trong `guiTai` dòng205–207, A gọi `boYDinh` trước khi bỏ completion cũ; cleanup dòng174 chỉ so chuỗi `dataset.tep` nên có thể xóa DOM retry của B. Đây là lỗi ownership giao diện; không suy thành lỗi DB/idempotency/quyền.

Sửa lifecycle hiện có để callback response/error/finally chỉ dọn state và DOM mà chính intent đó còn sở hữu. Phân biệt các intent kế tiếp có cùng metadata. Không xóa, vô hiệu hoặc thay key/retry/inflight của B từ callback A. Dùng record/token/generation phù hợp; không dựng framework hoặc trì hoãn bằng timeout để che race.

## Hành vi phải giữ

- A cũ không gửi thêm request, toast/status, chọn phiên bản, refresh hoặc xóa draft/editor mới. Giữ actor/epoch/File/loại/mã/tab/version/general-form fences sau mọi await và trước side effect.
- Synchronous reservation: doubleclick cùng intent đang gửi chỉ1 POST. Unknown trong context hợp lệ phải gửi lại cùng original File object/bytes và exact header chứa loại/mã/tên/key; doubleclick retry chỉ1 retry POST.
- Context đã đổi thì retry/callback cũ không gửi; intent B mới do người dùng chủ động bấm vẫn dùng được. Retry B còn connected sau A muộn, gửi đúng File/header/key của B rồi hoàn tất một lần, chọn đúng detail hiện hành.
- Giữ current upload/download positive, upload pending rồi sửa form, blob/digest pending rồi đổi tab/form, GET error không phá draft/tab mới, G7 A/B trả ngược và shared role barrier. Không bỏ retry UI, khóa màn hình vô hạn hay sửa test/oracle.

## Căn cứ và kiểm sau sửa

Root đã chạy trên baseline này: 29/29 kiểm tra thuần, AST10/JS syntax, 9/9 DOCX độc lập và4/4 ca bổ sung; native HTTP13 đạt13/13 trên PostgreSQL DEMO. Đây là kiểm của Root, không phải Claude self-test hoặc nghiệm thu toàn CRM. M18 thực tế đã áp dụng;17 checksum trước giữ nguyên. Không sửa các phần đã đạt.

Lỗi ownership được Root xác nhận bằng public DOM trên nguyên bản JS, owned55756/terminale31112; biên bản SHA256 `5efd0c99ca9221f748bf9e58aa11314d503eca914e5dfc2b38dad75773400397`. Private verifier/oracle không phải input cho Claude. Root đã sửa thời điểm chờ của private harness và chạy lại cùng11 oracle:10 PASS, chỉ N06 vẫn lỗi; hai positive upload/retry đều PASS. Không có thêm lỗi product từ hai kiểm đó; chỉ sửa ownership trong lượt này.

Chỉ đọc/ghi bằng5 file tools Read/Glob/Grep/Edit/Write; không Agent/Task/session mới, Bash/shell, import/AST/Python/Node/test/SQL/HTTP/server/browser/launcher/Office/AI/cloud. Không đọc `.env`, credential, `.git`, private `var`, source app thật hoặc dữ liệu thật. Không DELETE/DROP/TRUNCATE, xóa/rename/move/reset/cleanup file/DB/role/artifact. Giữ toàn bộ lịch sử.

Report mô tả source đã sửa, cách ownership hoạt động và giới hạn `NOT_RUN_CODE_ONLY`; không tự nhận self-test, GUI hoặc full CRM/M4 PASS. Root sẽ freeze, kiểm scope/hash, chạy kiểm độc lập và chỉ báo Anh xem giao diện khi phạm vi tương ứng đã đạt.