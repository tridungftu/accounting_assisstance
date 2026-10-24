# Recheck độc lập root bindings03 — R1/R2

**19/10/2026 — STATIC_ONLY / ALL_RELEASE_FALSE / NOT_RUN. Hai P1 của review02 được xử lý ở mức definitions; không thấy regression material mới trong phạm vi này.** Không cấp runtime hoặc đóng F1–F3 runtime. Đã đọc đủ bốn file ổn định, chỉ đọc/hash; không import/AST/test/process/SQL/product/M9/.env hoặc sửa inputs.

Base `var/codex-dieu-phoi/v13-race-cli-planned03/`:

| Input | SHA256 đã kiểm |
|---|---|
| `ROOT-BINDINGS-PLAN.md` | `f0d61508c4637aa6a7a992cf6651387c84b7af92d52b60d2dbea4cafe29cc40c` |
| `root_child_bindings03.py` (257 dòng) | `cef0462c21076e1bf7691022e5b7ea372fa795723b832f3a1715d2019c02c1ff` |
| `root_watchdog03.py` (233 dòng) | `36d7ad24fe64a7d37241c693075cfc24c381ccc2dead19276a7f05e246531c9e` |
| `root-bindings-release-template.json` | `9eca446c52dacf9075aafab13e6040c8c2051e62505234113b0dec148eca5ee3` |

Đối chiếu `REVIEW-V13-ROOT-BINDINGS-02.md` SHA9e67e6fe…a1736 và existing glue02b663/protocol02. Không thay oracle/glue hoặc đề xuất framework khác.

## R1 — expiry/authority: xử lý đúng ở definitions

- Watcher `:142,146,157,160,170,179,187,190` kiểm actual deadline/live child/timeout, trước và sau các bước handshake. Spawn hết lease không được phát offer. `:147–155,180–184` chỉ publish **OFFER/GRANT với root_child_watchdog_armed=false**, không còn file tự tuyên bố live authority.
- READY phải gắn exact offer digest/nonce/PIDs/expiry và timestamp còn hạn (`:171–178`); grant gắn hash READY/root release. I/O grant có thể vượt expiry nhưng không biến grant thành live authority.
- Child `_offer_state:44–73` kiểm finite actual start/expiry, đúng process/nonce/job và chưa hết hạn. `arm_owned_child:204–240` so **actual released-manifest digest**, required capabilities, offer/READY/grant hash/PIDs/nonce/lease, thứ tự timestamp và `now < expires`; pin/check original delegate trước fresh arm. `:246–251` chỉ trả armed=true trong child memory sau fresh arm/guard.
- `root_profile:163,169` và `guard_ok:183,186` kiểm expiry trước/sau delegate/checker. Lỗi tiếp tục đi nonreturning fatal97; không trả lỗi về SQLite callback entry. Watcher finally `:200–201` còn latch timeout nếu timer chưa schedule mà child đã kết thúc muộn, nên không giấu expired case bằng cancel timer.

Phản ví dụ slow-Popen/timer0/stale attestation của02 không còn đường cấp authority tương ứng trong definitions03. Chưa chứng minh actual shared monotonic clock, timer scheduling hoặc bootstrap gọi đúng thứ tự ở runtime.

## R2 — stop/confirm trước I/O/cancel: xử lý đúng ở definitions

- `stop_and_confirm_created_child:91–111` chỉ dùng chính Popen object; kill là attempt, sau đó wait/poll mới xác nhận termination. Lỗi/chưa dừng giữ `stop_attempt_error/stop_unresolved` thay vì giả success.
- Timer `:123–130` chỉ ghi timeout receipt sau confirmed termination; unresolved thì không disk I/O. Parent finally `:204` stop/confirm **trước** cancel/join timer `:206–213`, và còn thử finalize `:215–216` khi chưa confirm. Timer join/error không bỏ bước stop.
- `:217–219` unresolved vẫn raise/no I/O/no-next-case, không hủy timer hoặc claim armed. Nếu về sau đã confirm, failure flags vẫn sticky, `no_next_case:225–226` giữ failure; final receipt armed=false/product_pass=false.

Hai nhánh kill-error→receipt-I/O và cancel-before-stop của02 đã được loại khỏi definitions tương ứng. Nếu OS không stop được thì vẫn là unresolved failure, không bảo đảm hard wall mọi OS failure hoặc tự cho phép case tiếp.

## Các giới hạn vẫn phải bind

- Watcher không import/call child profile/glue, không có os._exit, không PID scan/kill app/PG/foreign process. Child fatal/profile fallback chỉ hợp lệ với construction contract owned child; không được arm ở watcher/Codex/app. Không có process nào được tạo/dừng trong lượt review.
- Actual child entrypoint/outer finally/READY exclusive write/finite waits, exact runtime/shared clock, original guard delegate/checker, candidate bytes/API, endpoint/schema/fixture authority và independent oracle **NOT_BOUND**. READY kind chưa tự chứng minh không import product; full bootstrap/call graph vẫn cần review trước release.
- Child fatal receipt có thể chậm; parent stop, profile/guard expiry và main-product/raw-worker closed call graph cần runtime receipts. Không tự suy profiler bao phủ worker. Glue02 worker finally/join giữ nguyên; không lấy recheck definitions này làm F1–F3 runtime closure.
- Template vẫn **12 allowed flags + armed flag =13 false**, review/pins/PIDs/DB/schema/clock/deadline null. Old-target/CLI/module/ordinary-role/GUI/fullK2/M9 acceptance không được nâng trạng thái.

**Kết luận:** chấp nhận sửa R1/R2 về control flow trong bốn bytes03 trên để tiếp tục chuẩn bị binding có kiểm soát. Giữ release false và mọi artifact; chưa import/test/process/SQL hoặc nghiệm thu runtime.
