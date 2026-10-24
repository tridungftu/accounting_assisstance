# Review tĩnh tests V13 backup03

**2026-10-19 · STATIC ONLY / NOT_RUN bởi reviewer.** Đã đối chiếu toàn diff unit/PG tests từ bản02 đã đọc đầy đủ, đọc tất cả phần mới, report03 và related copier/CLI diff. Không import/run sản phẩm/test/SQL/process/DSN/.env, không sửa source/test hoặc xóa file. M9 STOP. **Không thấy P1 safety mới; R3 sequence-boundary đã đóng ở thiết kế test. Có một P2 nhỏ ở độ đầy đủ oracle receipt, không cản việc root release selected tests an toàn.** Không gọi đây là runtime acceptance.

## Pins

Frozen146: `var/codex-dieu-phoi/kiem-chung-20261018-101441/v13-legacy-backup03-handoff-20261019-134511-250/frozen`; manifest SHA256 `08e5b5a9394d632d8c6c8e184cd5f08698decd5ee98f50c887c16b275a28ed19`.

| File frozen | SHA256 |
|---|---|
| `tests/test_v13_backup_safety.py` (409 dòng) | `22d42031596d75cf8ea98fabb034df7284fa687f4c2de2b4bf082c5dc7deeb36` |
| `tests/test_v13_backup_safety_pg.py` (808 dòng) | `7c0802704dfbe527370f9ca457835b252a57d01d894d47f09bd9efd96446a396` |
| `src/kho_tri_thuc/ha_tang/sao_chep_bang.py` | `cf0a0753ea09f4dedf0ae2ae26ba80f3bf6ac0a73cc67721c28219b81cb561c7` |
| `tools/sao_luu_pg.py` | `01ce14dac7fd5b83edaf6e9862dc79a951566aa0035ba79af37525e7b128dc96` |
| `docs/BAO-CAO-V13-LEGACY-BACKUP-03.md` | `398ee0c189e67cecb7aaf80e7d8cb1050fe82de56c29b7a3a9cdcf6c7e19c070` |

Report03 ghi15 unit PASS và PG command bị Bash permission denial một lần→PG03 UNRUN/0 pass/fail. Đây là receipt/report của coder, không phải test reviewer chạy. Bằng chứng actual candidate02 không thay bằng chứng candidate03; không suy PG03 đạt từ15 unit.

## C1 — R3 sequence oracle: đóng ở mức static

PG201–212 tách `kiem_sequence_strict` và `kiem_sequence_an_toan`. N02 gọi strict ngay sau direct copy, trước INSERT/Store; vẫn đo actual cash INSERT và rowid=max+1. P01238 dùng safe-next sau Store open/backup/restore/reopen, cho phép legitimate nextval đã bị tiêu thụ bởi INSERT ON CONFLICT DO NOTHING; không ép `is_called=false` sai boundary như bản02.

P01232–246 vẫn so full typed49 với SQLite gốc, actual raw/config bytes, history version/checksum và marker riêng; sau đó247–259 thực INSERT cash trên schema đã reopen, kiểm generated rowid>oldmax và so lại toàn baseline chỉ bỏ đúng dòng đo mới có unique bank_account. Không xóa dòng thật, không mock nextval hoặc đổi product để làm test xanh. Fixture sequence là increment1/noncycle theo fresh legacy contract; đây không phải oracle cho arbitrary altered sequence/ordinary role.

## C2 — R1 actual rowid alias controls và safety: phù hợp

PG `rowid_thuc_khop`419–440 lấy table inventory từ SQLite sqlite_master, PK từ PRAGMA, so SQLite rowid với cột rowid PG thực; với INTEGER PK còn kiểm PG rowid=PK. Không gọi production alias resolver cho phép đo này. Positive N03 dùng actual copy. `chuan_pg` cũng chuyển sang rowid PG thực; table/column list của full content oracle vẫn lấy production contract và docstring nay nêu đúng giới hạn.

N09 dựng source PG từ positive copy rồi actual INSERT hai audit_events id100/50 với rowid identity riêng; tiền điều kiện quan sát trực tiếp có đúng hai rows lệch. Hai actual paths direct PG→SQLite và CLI đòi `PG_ROWID_ALIAS_LECH`, source/full target snapshot nguyên, source transactions đã đóng, không publish, staging/old backup được giữ. Unit RowidAliasGuardTests chỉ là fake-source control kiểm toàn alias group và mã lỗi, không được tính như PG proof. Related copier đặt guard trong cùng read snapshot trước seed DELETE/INSERT SQLite; không sửa nguồn để làm hai rowid khớp.

## R1 / P2 còn lại — receipt foreign-final có thể bỏ sót owned inventory mà test vẫn xanh

**Anchor PG766–783, đặc biệt781:** sau real copy+SHA, injection tạo final bên khác, expected rc2/DESTINATION_EXISTS và ownership flags đúng. Nhưng `all(x.startswith(part[0]) for x in e['con_lai'])` là True khi `con_lai=[]`; các assertions còn lại không đòi danh sách chứa chính partial directory/DB/SHA. Counterexample output có đúng `partial_giu_lai`, flags/kiem_ke=DAY_DU nhưng `con_lai=[]` vẫn qua riêng nhánh này dù receipt thiếu toàn bộ tài sản owned.

**Control nhỏ cần bổ sung hoặc bind ở independent probe trước claim đủ R2:** đọc independent actual retained partial sau fault, assert exact nonempty `con_lai = [partial+'/'] + sorted(partial children)` và DB+SHA thực còn, đồng thời foreign final marker/bytes nguyên và không xuất hiện trong receipt. Không chỉ assert all-prefix hoặc len(new directories). Unit foreign-final đã có expected list cụ thể (DB-only) và các fault PG khác761–764 có exact inventory; khe hở này chỉ ở nhánh foreign-final mới. Không sửa test trong review này, không xem đây là product bug/runtime FAIL đã quan sát.

## Safety và giới hạn giữ nguyên

Setup config/raw exclusive + direct SQL seed49 nonempty, int64/0/NULL và actual Store→backup→restore→reopen không đổi. Không quay lại Store.ingest/write_immutable/unlink; Config chỉ đọc DEMO config, resolver key tường minh. Unit receipt helper `_chep_kiem_cong_bo` bị chặn trước DB call nên DSN placeholder không mở kết nối; alias unit cũng không kết nối. Các paths/tên final của “bên khác” đều được tạo mới trong owned DEMO temp root, không source thật/backup cũ.

Receipt controls mới kiểm actual owned rename positive, foreign final không nhận sở hữu, listing-error UNKNOWN và original error giữ nguyên; mock fault được ghi rõ, không fake full PG success. UNKNOWN test785–794 còn yêu cầu retained partial thật không rỗng. Existing race actual SQL/blocker PID/relation/mode/full baseline, late sequence-fault actual first5 calls, CLI same-snapshot/content/SHA/retention và no-cleanup controls giữ nguyên. Không thấy DSN/password đưa vào assertion args hay thông điệp mới.

Các gate trước root execution của review02 vẫn áp dụng: frozen module/dynamic CLI pins, original guard/no-bytecode, outer retained-runner redaction cho setup/unexpected traceback, explicit localhost/known URI DSN trước CREATE new retained kho_test DB, không fallback.env/K2/M9. Không đọc runner/credential trong lượt này. No ordinary-role, independent OS-process race/CLI, ACL/full inventory independence, full K2/GUI/full V13 acceptance từ suite này; các scope đó vẫn NOT_VERIFIED. Root tự quyết release và chạy selected actual tests sau full-read; reviewer không thực thi.
