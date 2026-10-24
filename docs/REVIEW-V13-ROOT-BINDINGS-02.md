# Review độc lập root bindings02

**19/10/2026 — STATIC_ONLY / ALL_RELEASE_FALSE / NOT_RUN.** Đã đọc đủ bốn file ổn định và đối chiếu glue02/protocol02 đã đọc trước; không import, AST-parse, test, process query/spawn/stop, SQL, host, M9/product hoặc credential. Không sửa input. **Hai P1 cần sửa trước release; F1–F3 của harness chưa đóng runtime.**

Base `var/codex-dieu-phoi/v13-race-cli-planned02/`:

| Input | SHA256 đã kiểm |
|---|---|
| `ROOT-BINDINGS-PLAN.md` | `96e2c6aac57ff209ddc390e7dc8e2e5c52ffb716cafc6e374908636ad9db8893` |
| `root_child_bindings02.py` | `ff8c59539553ba945e7dcbb11e965d1548d7d8c5b66881ba8af0fb0a0ec013f2` |
| `root_watchdog02.py` | `add4f25048c682b8a45697695be030d2a5a12ef996d821e0857e8eb9c2246fe6` |
| `root-bindings-release-template.json` | `2a8849d1b164582c8fc19a5210bfe1693a47b23058f9fa3b2b392484487c5caf` |

Sibling glue02 vẫn SHA `b66312095150dfa4ccdf1a557469e0ed3ae1f1c129ba0adca047ed5cedc9f427`; protocol02 `01727f19f8ddb884e60afd85098b371fd3f61ce8cc4a381e9e02b65ff152ad2f`. Không nâng package thành actual bootstrap/runner.

## Findings trước release

**R1 — P1, authority có thể được phát sau expiry và child không kiểm expiry.** Watcher `:78–79` đặt deadline trước Popen; `:108–114` luôn start timer với `max(0,remaining)` rồi publish `root_child_watchdog_armed=true`, không kiểm now/deadline/timeout state. Counterexample static: Popen trả sau deadline; timer0 chưa được schedule, parent publish attestation, child nhận authority rồi có thể hoàn thành trước timer; main `:123–126` cancel timer. Receipt có thể timeout=false dù case đã vượt hạn. Child `arm_owned_child:143–167` chỉ kiểm timeout duration hợp lệ/PIDs/nonce/flags; không dùng actual deadline, `spawn_elapsed_seconds` hoặc freshness nên không từ chối attestation đã hết hạn. Đây là latch đã-start, chưa phải live unexpired authority.

Sửa hẹp: parent không publish authority nếu expired/timeout/child đã dừng; bind actual monotonic expiry vào child gate trước arm/product/glue/connection và các guard boundary cần thiết. Đóng race check-versus-publication bằng handshake/expiry đã review, không chỉ thêm check rồi vẫn phát cờ true sau deadline. Case expired/timeout phải FAIL/NOT_VERIFIED, không hủy timer rồi để outcome như transport bình thường. Child bootstrap thực vẫn NOT_BOUND nên chưa có đường bù ngoài skeleton.

**R2 — P1, kill-attempt chưa bảo đảm child dừng trước receipt I/O hoặc timer cancellation.** Timer `:90–99` có thứ tự gọi kill trước ghi receipt ở nhánh thành công, nhưng `kill_created_child:83–85` không wait/xác nhận termination; nếu kill raise, `:92–95` chỉ gắn watchdog_error rồi vẫn đi vào I/O. Nếu parent đang kẹt attestation flush/fsync `:114`, outer finally chưa chạy; timer receipt I/O cũng có thể kẹt khi child còn sống và vẫn giữ attestation armed. Thêm vào đó, parent-error finally `:123–136` cancel/join timer **trước** kill/wait child, tạo khoảng child sống nhưng watchdog đã bị hủy. Nested finally hiện bảo đảm thử finalize về sau, không đóng hai khoảng này.

Sửa hẹp: mọi timeout/parent-error phải stop và xác nhận đúng owned Popen child trước receipt I/O hoặc cancel watchdog; giữ nested-finally để vẫn finalize khi timer/join lỗi. Nhánh không thể stop do OS phải để capability unresolved/failure và không chạy case mới/claim armed; không giả định hard wall bảo đảm trong mọi OS failure hoặc ghi receipt trước để thay cho stop. Chỉ exact owned handle, không tìm/kill process theo tên/PID ngoại lai và không tạo framework supervisor mới để né finding.

## Những nhánh có cơ sở và giới hạn giữ nguyên

- **F1 callback entry:** child `root_profile:105–121` bọc ownership/identity/delegate/checker bằng catch BaseException; violation/internal error đi fatal rồi fallback `os._exit(97)`, không raise về SQLite trước trace body. `_owned_state` trước try của `fatal_abort:87` có thể raise, nhưng root_profile finally và glue `_fatal` có own-process exit fallback. Đây là closure về control flow **có điều kiện** exact hook được arm trong owned child; actual original guard delegate/checker API chưa bind nên chưa certify compatibility/runtime.
- **Không exit parent:** watcher chỉ import stdlib và không import/call/install child profile/glue; không có os._exit trong watcher. Popen tạo child riêng, kill dùng chính object đã tạo; argv chỉ paths/nonce/job, DEVNULL không phát child traceback/DSN; env tường minh, không serialize. Parent tuyệt đối không arm/call root_profile: hook fallback vẫn có thể exit caller nếu dùng sai construction contract.
- **F2 chưa đủ:** duration int1–60 loại bool,11 file pins/self pin và riêng job nonce có ích; không chứng minh parent timer còn hiệu lực tại child gate. R1/R2 cần sửa. Pin/file hash không là liveness proof. Không claim whole parent call kết thúc trong60s khi spawn/I/O/OS có thể chậm.
- **F3:** glue02 clear-trace/join nested-finally và fatal khi worker alive/error được giữ. Parent có nested finally thử child finalization dù timer join lỗi, nhưng phải đổi stop-before-cancel như R2. Outer child runner từ trước setup, source/connection closure và descendant policy vẫn chưa viết/bind. Raw workers giữ closed call graph; main profile không tự bao phủ mọi thread.
- Fatal receipt dùng exclusive new file, sanitized whitelist, không exception text/code/rows/env; receipt I/O có thể làm child chờ tới watchdog, không tự là proof process đã exit. Exit97/timeout/missing receipt không PASS. Watcher luôn `product_pass=false`, exit0 chỉ transport chưa đánh giá.
- Template có12 `allowed_*` flags và `root_child_watchdog_armed` (tổng13) đều false; review/pins/PIDs/DB/schema null. Actual child bootstrap, candidate02 bytes/API, original guard profile/checker, runtime/env/endpoint/schema authority và independent oracle đều **NOT_BOUND**. Không runtime release, không DB setup và không criterion PASS tại lượt review này.

Root đã chốt hướng giữ nguyên02, giao tác giả tạo sibling03 sửa expiry và owned-child-stop ordering. Review này không sửa input hoặc cấp runtime; cần review bytes03 rồi bind actual bootstrap/guard/oracle/DB sau candidate freeze.
