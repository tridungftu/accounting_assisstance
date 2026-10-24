# M4-01C4 — chặn gửi lại tệp sai hồ sơ và gộp lần lấy mẫu đang chờ

Trạng thái: PUBLIC_CODE_ONLY / ROOT_RELEASE_REQUIRED. Root duyệt, phát hành bản công khai và release riêng trước khi Claude chạy. Không phải nghiệm thu M4.

## 1. Căn cứ và phạm vi

- Giữ kế hoạch M4 đã chốt và gói C đầy đủ; đây chỉ là sửa hai lỗi upload của giao diện đang có.
- C3 đã kết thúc thật: handle48960, terminal082b72, exit0; source352/runtime418 đã frozen và posthash đúng. C3 là code-only, không suy thành mọi ca đã đạt.
- Supplemental độc lập actual b562fe/owned65099: một positive không rỗng và hai lỗi đều tái hiện; live352/frozen418 trước/sau không đổi. Đây là actual Node handlers, chưa phải kiểm browser/HTTP cho hai race.
- Lỗi C4-01: upload A có kết quả chưa rõ; chuyển qua HĐ/project B bằng nút đang nối DOM và tải detail B xong; nút gửi lại toàn cục còn nối, bấm gửi lại mang File/bytes A nhưng header project B. Expected: 0 POST.
- Lỗi C4-02: bấm Dùng tệp mẫu hai lần trước GET mẫu đầu trả về; hai GET tạo hai File có lastModified/operation key khác nhau, dẫn tới 2 POST cùng bytes. Expected: một logical intent và tối đa 1 POST đang chờ.
- GUI C3 đã dừng thật theo Root: owned10178/cd212e exit0, child3352 stopped, sourceposthash đúng, tài nguyên giữ nguyên. Bộ điều khiển phải kiểm receipt và đúng PID đã dừng trước launch; không dừng ứng dụng khác.

## 2. Đúng ba file được sửa, không tạo file mới

1. `src/kho_tri_thuc/m4/giao_dien/m4.js`.
2. `tests/m4_01c_async.cjs`.
3. `docs/BAO-CAO-M4-01C.md` — append kết quả C4, giữ lịch sử C/C2/C3.

Source352 giữ nguyên pathset; 349 file còn lại được bảo vệ. Không sửa APP.JS, Python tests, backend/routes/HTTP/SQL/services/bootstrap/package/CSS/index/vendor/fixtures/guard/M9. Không đổi nghiệp vụ hay mở rộng kế hoạch.

## 3. C4-01 — kiểm đúng context trước mọi request

- Một upload intent phải giữ nguyên File, bytes, vai tài liệu, project/HĐ/đợt, metadata và operation key thuộc context gốc. Không dựng lại header từ hồ sơ đang chọn để gửi tệp cũ.
- Khi đổi HĐ/project/đợt hoặc đổi vai/lựa chọn có liên quan: vô hiệu intent cũ theo generation/context; gỡ/khóa retry UI toàn cục ngay. Không để nút cũ còn hoạt động trên context mới.
- Tại entrypoint gửi lại và ngay trước POST phải kiểm intent còn hợp lệ, quyền/context hiện hành còn phù hợp. Kiểm sau response không thay thế gate trước request.
- Callback cũ hoặc nút đã gỡ không được gửi thêm POST. Không giải quyết bằng đổi đích gửi, đổi khóa hoặc tự gắn tệp A sang B.
- Khi vẫn ở đúng context và kết quả upload chưa rõ: gửi lại đúng File/bytes/header/key gốc, không GET mẫu lại, không tạo File mới. Kết quả rõ chỉ gắn/preview/làm mới đúng một lần.

## 4. C4-02 — giữ một ý định trước await đầu tiên

- Dùng tệp mẫu phải reserve logical intent hoặc khóa control đồng bộ trước GET/await đầu tiên. Bấm lặp khi đang lấy mẫu không tạo request upload thứ hai.
- Intent có context, lựa chọn mẫu/vai và ownership rõ; lựa chọn/context đã đổi trong lúc GET chờ thì không upload mẫu cũ. Phản hồi cũ không nhả trạng thái của lần mới.
- Khi GET thành công, File gốc và key của ý định được giữ qua unknown retry. Không dùng lastModified cố định hoặc chỉ thay timestamp để che hai ý định.
- GET lỗi chắc chắn có đường thử lại hợp lệ; network/5xx/HTTP200 nhưng JSON đứt sau POST vẫn giữ đúng intent chưa rõ. Không tự coi lỗi JSON là upload thành công.

## 5. Ca kiểm thật qua actual handlers

- Giữ các ca C3 hiện có (10 ca, gồm positives và các guard C2/C3), không rút bớt assertion, không nuốt unhandledRejection.
- Positive hiện hành không rỗng: lấy mẫu, POST đúng bytes/project/key; response thành công đi qua refresh thật và render source-row mới đúng một lần.
- Stale retry: cùng actor có hai project/HĐ trong trusted DTO; unknown A → click HĐ B thật → detail B hoàn tất → reacquire retry control còn nối DOM nếu có → expected0POST. Không dùng detached.click hay sửa state/epoch nội bộ để dựng lỗi.
- Thêm chuyển đợt/lựa chọn/context làm retry cũ vô hiệu; chặn trước POST, không chỉ chặn render muộn.
- Double initial sample: bấm control đang nối hai lần trước GET settle; native Blob/File timestamp thay đổi như browser; expected tối đa một pending upload. Không chỉ assert string source.
- Unknown retry cùng context: giữ original File identity/bytes/header/key và completion một lần; vẫn có positive lấy mẫu và tệp thật. Phản hồi đảo thứ tự không phá guard hiện hành.

## 6. Giới hạn thực thi và báo cáo

- Claude chỉ Read/Glob/Grep/Edit/Write trong cùng session52783bcd-6e1d-46d2-9e45-3c527aa43e5b, safe-mode/dontAsk/strict-empty-MCP, timeout1800s. Không Bash/Agent/session/worktree khác.
- Không chạy Node/Python/import/AST/tests/SQL/HTTP/browser/Office/AI/cloud/launcher; không đọc var/.env/secrets/source app thật; không xóa/rename/move/reset/cleanup/overwrite nguồn ngoài ba file cho phép.
- Append báo cáo mô tả thay đổi, ca đã viết và self-test `NOT_RUN_CODE_ONLY`; không gọi C4/GUI18/wheel/full M4 đã đạt. Root sẽ đọc full diff, frozen và kiểm độc lập sau terminal thật.
- B50+4/native10/independent8 là bằng chứng hữu hạn B đã có; không cần chạy lại hay sửa B trong lượt C4. Các phần Review/PDF/AP/Request và CRM giữ lộ trình riêng đã chốt.
