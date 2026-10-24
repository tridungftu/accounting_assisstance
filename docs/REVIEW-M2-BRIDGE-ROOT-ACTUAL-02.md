# Kiểm độc lập M2 bridge repair02

19/10/2026. **CHƯA ĐẠT CẦU NỐI: R4 source-basis còn mở; HTTP oracle cần tách.**

M2 repair02 đã terminal90087/chunk9a721c và frozen249 SHA4c81093f. Root chạy độc lập: migration6/6, service17/17, selected15nhóm/15PASS, async6/6; không cộng các tập chồng lấn. Probe15case:5positive+9denialPASS,1R4source-basis VIOLATION (ownerINSERT self-digest đúng nhưng meaning/ref không được tài liệu4fe4 khai; rollback toàn trạng thái phục hồi). HTTP3method:2PASS,1FAIL do request đổi route dùng token cũ cùng expected_route_id cũ, nhận409/M2_VERSION_CHANGED trước ROUTE_STALE; cần tách oracle hai điều kiện. GUI/P09–14/L11 chưa chạy/triển khai, không phải nghiệm thu toànM2. Tiếp: Claude sửa hữu hạn R4 + HTTP oracle gói03 cùng session, sau kiểm đạt mới code R16 L11. M9/kho thậtSQLite/khôngxóafile giữ nguyên.

Actual root tools: migration1e8efb, service6fc84c, HTTP16dc07, defects d4347d, selected001e4c, asyncac10f7; tất cả terminal, không còn test/writer/server của root hoạt động. Mã249 workspace/frozen và guard gốc không đổi trước/sau mỗi lần chạy. PostgreSQL chỉ127.0.0.1, DB/role/artefacts DEMO mới đều giữ lại. Không chạy SQL DELETE, không cleanup.

- migration: `var/codex-dieu-phoi/pg-retained-20261019-215549-305eb6ea/summary.json`, SHA256 `3a2e0eb9b54b22553dddd5a5caf664bf4bc475696fda091baf4ebeeb8061f97b`.
- service: `var/codex-dieu-phoi/pg-retained-20261019-215549-65789a21/summary.json`, SHA256 `d9888b397b3050a63e25ade08057129e89fdd423397b407999788de60b9d50e0`.
- HTTP: `var/codex-dieu-phoi/pg-retained-20261019-215549-8d100908/summary.json`, SHA256 `ed68af53b8dfbf8225649ebe0d6d2d396f154b58e444cbfa4ffe492ce374262c`.
- selected: `var/codex-dieu-phoi/m2-r15-independent-selected-8ae1751746cd/result.json`, SHA256 `c60099fdf97ae1c0ce393fe1fab3529085f9ce35b16c3a44781fb79feb95af3c`.
- defects: `var/codex-dieu-phoi/m2-r15-independent-defects-52a73280fd4b/result.json`, SHA256 `178236fb2991ce6881cf5e4c2dd68332df896871b71498b5167ee01425e36f6f`.
- async: `var/codex-dieu-phoi/m2-ui-async-independent02/root-result02-4e0526a953dd.json`, SHA256 `31540d7007a8bddc6a0bd72af58ddbc0d1fe224b8434cbe8589321bab1a23939`.

R1 exact retries giữ nguyên request/tokenA, changed-H và current module withdrawal đã PASS; capability-row DELETE không chạy theo lệnh cấm xóa. R2 literal binding, R3 immutable core quantity/header, S1 partial NULL và R4 claimed-digest denial đã PASS với exact SQLSTATE/prefix/constraint, full state0delta. R4 source-basis contradiction là owner-admission gap, không phải ordinary app bypass hoặc current original CAI bị sửa. Async sáu ca là extracted actual JS với controlled Promise/DOM, không là browser/HTTP/GUI acceptance. Native test t16 new meaning trên nguồn cũ không được tính là chứng minh authority. L11 v2/data/proofs chỉ PREPARE_ONLY, chưa có code16.
