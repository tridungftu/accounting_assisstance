# Review độc lập V13 race glue 01

**19/10/2026 · STATIC_ONLY / NOT_RUN / NOT_RELEASED.** Đã đọc toàn glue, protocol và release; không import/chạy glue/product, test, SQL, DB, host hoặc CLI. Claude đang sửa backup nên không kiểm runtime đồng thời; M9 giữ dừng. Review chỉ tạo tài liệu này, không sửa glue/product/public ledgers.

| Artifact đã đọc | SHA256 |
|---|---|
| `var/codex-dieu-phoi/v13-race-cli-planned01/race_glue01.py` | `59ee823f07feee7d2cd345621748d56489d720443e0e69b43d4f331264608225` |
| `PROTOCOL-01.md` | `a04fdcd4bdcb4d8166199b7544cf92a2ececc36a43fb8f5279bf4f49383f3b39` |
| `release-template.json` | `ebe19f72dbefafcf150b65c9d1cefd862be81ab77d25eb4b83f8a59929f56ad8` |

**Kết luận: giữ toàn capability FALSE.** Causal design hợp lý và không tự tuyên bố PASS, nhưng chưa đủ điều kiện thực thi: callback/profile failure có khoảng chạy tiếp trước fatal check; dừng main copier và kết thúc worker còn phụ thuộc runner chưa có. Root cần author xử lý/bind những điểm dưới rồi review lại trước release.

## Findings cần author xử lý trước release

**F1 — P1, mất profile trong SQLite callback không dừng copier tại boundary.** `race_glue01.py:157–174` bắt `BaseException`, ghi `callback_fatal`, rồi callback trả về; `copy_fn` ở `:181` có thể tiếp tục thực hiện/commit trước `_boundary` ở `:189`. Nếu lỗi đến từ profile guard, profiler có thể đã bị unset; lỗi tại callback entry thậm chí có thể bị SQLite nuốt trước khi body ghi được flag. Check sau khi `copy_fn` xong ngăn kết luận PASS nhưng không thực hiện yêu cầu “fatal-stop trước product actions tiếp theo”. Đây là nhánh suy ra từ source và semantics Python, **chưa tái hiện runtime**. [Python sys.setprofile](https://docs.python.org/3.13/library/sys.html#sys.setprofile), [SQLite trace callback](https://docs.python.org/3.13/library/sqlite3.html#sqlite3.Connection.set_trace_callback).

Author cần cơ chế fail-closed tại ranh giới callback/SQLite operation khi guard mất hoặc callback fatal; phải chứng minh product không tiếp tục tới PG writes/commit sau lỗi đó. Chỉ thêm `raise` vào callback hoặc bật traceback không đủ vì exception trace callback không được truyền ra. Bind cơ chế dừng thực bằng API connection/watchdog phù hợp, không patch hàm product; nếu chưa làm được thì B giữ NOT_BOUND, không release. Không tự cài lại profiler rồi tiếp tục chạy ca.

**F2 — P2, timeout của main copier chưa có trong glue.** `_gate:49–51` chỉ đặt timeout cho writer/observer; `race_a:120` và `race_b:181` gọi copier đồng bộ trên main. `_finish:86–89` chỉ chạy sau copier return/raise nên join20s không giới hạn được copier bị treo. Protocol yêu cầu root watchdog là đúng, nhưng runner/watchdog thực chưa bind. Trước release cần pin watchdog/cancel policy cho **owned fixture sessions/run**, timeout hữu hạn cho copier SQL và giới hạn toàn case; timeout không được map sang expected business refusal. Không ảnh hưởng PostgreSQL cluster hoặc process ứng dụng khác.

**F3 — P2, teardown callback có thể bỏ qua join worker.** Trong B `:186–188`, nếu `source.set_trace_callback(None)` raise thì `_finish(worker)` không chạy. Worker là non-daemon, có thể vẫn chờ/INSERT/COMMIT; caller không được coi exception là đã kết thúc mọi actor rồi chụp state/chạy ca khác. Sửa tối thiểu đề nghị tại đúng block này: đặt clear-callback trong một `try`, `_finish(worker)` trong `finally` lồng để luôn cố join, giữ nguyên lỗi/fatal evidence; tôi chưa sửa glue. Runner vẫn cần hủy/đóng session có kiểm soát và chứng minh thread đã dừng khi join báo alive, không chỉ bắt RuntimeError rồi tiếp tục.

## Guard/thread boundary phải ghi đúng phạm vi

`_boundary:58–60` kiểm profiler của **thread đang gọi**. Hai worker `:116/:176` không cài profiler riêng và không gọi `_boundary`; profile main không tự bao phủ chúng. Đây không tự động là lỗi của phương án main-product/raw-worker: worker hiện chỉ thực hiện raw INSERT/COMMIT/observer queries đã pin, còn SQLite/product copier nằm main, tránh lỗi cross-thread SQLite. Tuy nhiên không được ghi thành “no-delete guard bảo vệ mọi SQL/thread”. [Python threading.setprofile](https://docs.python.org/3.13/library/threading.html#threading.setprofile).

Root runner phải chọn và review rõ: pin closed worker call graph + đúng ba connection/owned fixture database/schema/SQL allowlist; hoặc cài guard phù hợp từng worker và fatal channel về main. `guard_ok` cần kiểm exact profile identity/forbidden count trên main như protocol yêu cầu, không chỉ non-None. Không gọi arbitrary callback/product/cleanup trong worker. Lỗi worker/profile/callback là fatal toàn run, không phải negative business pass.

## Những điểm thiết kế có cơ sở

- A giữ writer transaction chưa commit, chụp expected bằng chính writer trước khởi động copier (`:99–101`); observer nối blocker PID thật với relation cash và lock modes thật (`:63–83`), sau đó writer commit (`:111`). Không dùng một advisory contention hoặc timing sleep làm bằng chứng business refusal.
- B dùng SQLite trace tại bulk SELECT làm trigger, **không dùng trace như oracle lock**. Writer INSERT thật; observer phải thấy writer chờ RowExclusive và copier giữ mode đối nghịch. Main callback giữ copier đứng trong window witness; dùng returned rowid để bắt row writer sau copy. Hai hướng đều không di chuyển SQLite source sang worker.
- `_error` chỉ class/code/sqlstate, không str(exception)/DSN/rows; release template toàn false, standalone từ chối; không có provision/cleanup hoặc product imports trong glue. Những điểm này không thay root release/full candidate review.

## Các điều kiện bind còn thiếu, không coi là kết quả đã đạt

1. **Gate bên ngoài thật:** `_gate:31–55` chỉ kiểm candidate digest có dạng64hex, tên/type API và schema pattern; không tự xác minh candidate/source/oracle hashes, DB/role/endpoint hay exact owned schema list. Protocol đã giao root runner chịu trách nhiệm. Phải có runner đã review kiểm những pins/authority đó trước gọi `_gate`; không chuyển template true rồi gọi glue riêng.
2. **Candidate API/barrier:** bind actual signature/schema của `chep_sqlite_sang_pg`, regex bulk SELECT ở `:24`, real copied49table inventory và source không trùng cash key writer; static proof lock/admission trước ALTER/sequence/DELETE/COPY và giữ exclusion xuyên commit phases. Callback match một bảng không tự chứng minh toàn49 hoặc toàn writer types.
3. **Oracle và expected outcomes:** A bắt đúng `PG_NAP_DO`, writer committed, before-writer expected = after toàn state; B copy returned, writer committed, exact49source + returned writer rowid/values, marker/history rules/sequences. `read_state` phải pinned độc lập, cùng connection, không nested transaction/second session/migration/product fingerprint.
4. **Error flags bắt buộc fatal:** `coordinator_error/writer_error/callback_fatal`, thiếu barrier/witness, writer commit trước release, thiếu write-excluding inventory, copy outcome sai, timeout hoặc worker chưa dừng đều không PASS. `copy.returned=true` riêng hoặc “có row cuối” không đủ. Hiện glue trả evidence dù flag fatal; decision layer chưa có nên không được lấy output dict làm acceptance.
5. **Outer finally từ trước setup:** A bắt đầu writer/đọc expected trước block try (`:99–101`), B start worker/register trace trước try (`:176–179`). Runner cần giữ/finalize toàn connections và abort scope kể cả setup/oracle/registration lỗi; giữ raw files/schema/DB/partials, không cleanup. Đóng connection có thể rollback transaction dở; không ghi transaction dở là writer COMMIT thành công.

Older-target autoload và CLI trong protocol vẫn **NOT_BOUND/NOT_RUN**, không được bao phủ bởi hai race functions. Các pin business code/fault/staging point/child guard cần chốt sau coder terminal/freeze. Không mượn regex/type-name/static report để chứng minh runtime, ordinary-role security, GUI/full K2 hoặc tracking M9.

Review hiện nêu **3 finding trước release**, cùng guard-scope và runner binding gates. Không có SQL/test/CLI nào được chạy và không có criterion nào được nâng PASS.
