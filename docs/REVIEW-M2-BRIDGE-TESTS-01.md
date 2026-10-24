# Review độc lập tests M2 bridge 01

Trạng thái: FINAL_STATIC_REVIEW / AGENT_RUNTIME_NOT_RUN. Căn cứ handoff `33c380ba98f818819890a64f4657d7c87c078c38a0ab1c0d949cc5e337b54f93`; frozen 249 file tại `var/codex-dieu-phoi/m2-bridge01-handoff-20261019-205156-365-0655562d/frozen`, manifest `e515b4ef76a6990f84bed4245558e4aa82cf53234e07c4111fddd2f1bdcf033c`.

Đã đọc toàn bộ ba tests, `m2_demo.py`, `hoa_don.py` và các SQL replay liên quan. Không import sản phẩm, chạy test/SQL/HTTP/process, đọc secrets/sourceapps hoặc sửa sản phẩm.

## Findings

**T01 — P1, sản phẩm: exact retry mapping/route không đến receipt.** `pg_migrations.py:5797–5811` và `5900–5913` so expected graph hiện tại trước tra business receipt. Lần đầu đã đổi graph A thành B; retry nguyên body/key/token A bị `M2_VERSION_CHANGED`, thay vì trả cùng immutable result. Tests service `237–243` và `255–262` giữ nguyên body khi retry; HTTP `143–159` cũng vậy. Đây là oracle đúng, không được dựng lại token B để test qua. Cần giữ quyền hiện tại trước replay, nhưng tìm receipt theo namespace/key và kiểm request H trước khi áp stale-CAS cho request mới. Review source tại `5745–5758` có cùng thứ tự cần kiểm tra.

Root báo kết quả actual ngày 19/10: migration 5/5 PASS; service 15 gồm 9 PASS, 2 FAIL, 4 ERROR (`cf6a6d`, retained `pg-retained-20261019-205843-ca885407`). Mapping t05 và route t06 xác nhận lỗi retry; KeyError t07/t08 là hệ quả fixture state, không tự đếm lỗi sản phẩm mới. Hai assertion classification LIST/STR cần sửa oracle theo DTO. HTTP actual stale trả 400 `CSDL_TU_CHOI` và retry thiếu `lap_lai` (`9455bd`); agent không tự chạy hoặc xác nhận lại runtime này.

**T02 — P2, test không chứng minh đúng denial ROOT_SEED.** `test_m2_migrations.py:140–145` đặt cả tạo instance, tạo profile và INSERT INVOICE_LINE trong một `assertRaises(psycopg.Error)`. Lỗi ở một trong hai bước setup cũng làm test PASS mà chưa chạm guard cần thử. Chuẩn bị instance/profile hợp lệ ngoài khối assertion, rồi kiểm đúng mã lỗi của riêng INSERT mapping và state invariance. Không kết luận setup hiện đã lỗi từ đọc tĩnh.

**T03 — điều chỉnh riêng oracle độc lập, không phải lỗi sản phẩm.** Capture trả `lap_lai=False` lần đầu và `True` khi replay (`hoa_don.py:350–358`); SQL mapping cũng trả hai giá trị này (`5807–5811`, `5881`). So toàn response bằng nhau sẽ báo sai. Sibling `m2-r15-independent-controls02.py` chỉ loại field `lap_lai` khỏi hai so sánh P02/P04, đồng thời bắt buộc False→True; mọi field khác, nguyên request/token và DB/files 0delta giữ nguyên. Không nhận stale error thay kết quả replay.

## Giá trị và giới hạn của tests

- Migration test có sentinel M1 không rỗng trước/sau upgrade14→15, explicit NULL cho M2 và control giữ NOT NULL legacy (`112–139`). Legacy13 chỉ chèn checksum lịch sử sau migrate12 (`147–155`), không cài schema M9. Assertion dùng chính constant13/14 không tự chứng minh checksum lịch sử; cần root pin độc lập.
- Service tests có capture bytes thật, actual CFO line mapping/route, ZIP observations và source-row counts, A,A/B/A, reordered lines, candidate, raw-only crosswalk và core không tiền. Không import coder test helpers vào probe độc lập. `raises` bắt lỗi rộng và so substring (`140–145`); independent adapter phải chấp nhận đúng mã đã bind, để setup/connection/timeout lỗi thật nổi lên.
- Replay tests dùng nguyên body là control có ý nghĩa. So JSON classification phải theo actual DTO array, không đổi nghiệp vụ để khớp assertion STRING. Không dùng lỗi cascading hoặc aggregate count để kết luận thêm defect.
- Seed dùng INSERT/ON CONFLICT và dấu one-time; không thấy reset/regrant/delete trong `m2_demo.py`. Test t01 so quyền trước/sau seed nhưng không chủ động revoke quyền trước reopen: chưa phải bằng chứng revoked grant được giữ trong ca đó.
- HTTP gọi server local thật với cookie/token và bytes base64; kiểm HTML/JS bằng substring chưa phải GUI. Các observers hiện chủ yếu counts/IDs; chưa thay được canonical all-table/files snapshot, causal race, snapshot coherence hoặc thực revoke/current-role controls.

## Điều kiện an toàn cho root runtime

Tests tạo DB/role DEMO tên mới từ `KHO_PG_DSN_TEST`; chúng không tự bảo đảm endpoint là loopback/fresh trước CREATE DATABASE. Chỉ chạy bằng retained bridge/root wrapper đã review, DSN không in hoặc đưa vào argv, original no-delete guard, owned-process watchdog và source pre/post pins. Không dùng bare unittest với cấu hình máy thật.

Không thấy cleanup DROP/DELETE/unlink/rmtree trong ba test; retained temp folders/DB/roles được giữ, teardown chỉ đóng connection/server/thread và phục hồi biến môi trường test. HTTP `LocalApp` vẫn phải nhận root DEMO riêng. Không chạy standalone launcher hoặc seed vào DB có dữ liệu thật. Không tuyên bố M2 đã nghiệm thu từ báo cáo Claude hoặc nhóm tests này.

## Source pins

| File frozen | SHA256 |
|---|---|
| tests/test_m2_migrations.py (159 lines) | 93c292ad11363ddb164e7375eee540d6739bd3bb4968ae6d04d9df60f9cff6b4 |
| tests/test_m2_k2.py (443) | 4ac3965ee1a366910f378103f64c1a9fec082408f0a554588a1a82dd6a74a8e7 |
| tests/test_m2_http.py (198) | 3f3df1760a54bf4547cb14d565d7b05048a85e7c07c0e9cd47b6c2901bc9ab82 |
| k2/m2_demo.py (162) | 76c48d1d6c73728f85073002e7b707e7e0d7a2524934fcf4a56546995cd92acd |
| k2/hoa_don.py (558) | 8280a50eb616b27521dcce35b31a0f3f9c504ce94e02ccf3f81e7fba4734a862 |
| ha_tang/pg_migrations.py | 037e037ce8fa00c0b79a59769a67b9840b547cdac0fe6ae15351d24d8dd10644 |
