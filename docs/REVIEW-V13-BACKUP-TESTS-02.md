# Review độc lập test safety V13 backup02

**2026-10-19 · STATIC ONLY.** Đã đọc FULL unit324 dòng và PG680 dòng cùng report02/fixture/config/Store/backup/CLI/callsites cần thiết. Không import/run sản phẩm hoặc test/SQL/DB/process/HTTP, không đọc DSN/.env/secret/source app, không sửa source/test hoặc xóa file. M9 STOP/read-method-only. **Không thấy test setup còn đi qua ingest/unlink hoặc gọi K2/M9; có một P2 oracle cần sửa/giới hạn trước khi dùng kết quả PG để kết luận.** Đây không phải release chạy suite hoặc runtime acceptance.

## Pins và bằng chứng

Frozen146 `var/codex-dieu-phoi/kiem-chung-20261018-101441/v13-legacy-backup02-handoff-20261019-131139-361/frozen`; manifest SHA256 `314fb1f10b6c61a93505680d3573c792900e4c1cc94f97e1370866b2c726adb4`.

| File | SHA256 |
|---|---|
| `tests/test_v13_backup_safety.py` | `19856ba4906fb77226d75e9b5910b5db6b3744174287d7e7d5d44c8e9bf6743a` |
| `tests/test_v13_backup_safety_pg.py` | `a77c080934d111aec17e3401457a1e440f6c873c68a74ef1485378c67cfe3deb` |
| `src/kho_tri_thuc/ha_tang/store.py` | `7c6c3fa4225b6089c4913a2870c6f4c26d7f813608d017901f6aea9aa7288dc5` |
| `src/kho_tri_thuc/ha_tang/config.py` | `349cc70d4adfc5014dbb4c5eb406a4647d7bc46d8e3d91bd89ff6bc12e92e023` |
| `src/kho_tri_thuc/ha_tang/backup.py` | `e28853902ad327d28e38b7b6cd6588ba6e0911a52714f45f6bd2f6ee271d7fea` |
| `src/kho_tri_thuc/ha_tang/ket_noi.py` | `a18d02e6370dcede8a7c4506e919c1c4df5643c9ad0c03dce9f812970452341d` |
| `tools/sao_luu_pg.py` | `4d53ac600362dcd908cd4af2d55c6dca954dcb302e6f98e5186d8071c85961b3` |

Report02 là technical document đọc riêng ngoài manifest product: `docs/BAO-CAO-V13-LEGACY-BACKUP-02.md` SHA `5ab29eda68dbbb289b933c983cb2fb336251501572b6e28f82a78592b9c5416c`; handoff02 SHA `6c1973b830ce7ce71e461ea3bf4e96527eb852cd5c9d83dc4b3d15bba5e5f163`. Root thông báo unit11OK từ stream; report9–12 ghi11 unit PASS và3 Bash permission denials cho PG = **PG UNRUN,0 PG PASS/FAIL**. Reviewer không rerun hoặc tự xác nhận runtime qua source.

## R1 / P2 — strict sequence oracle được áp sau Store đã tiêu thụ identity

**Anchor:** PG test183–192 và P01 `test_p01_storepg_backup_restore_mo_lai_bang_sqlite_goc`204–218; unchanged `Store.__init__`87–94; translator biến INSERT OR IGNORE thành ON CONFLICT DO NOTHING.

`kiem_sequence_sau_chep` đòi `last_value = max(column)+1` và `is_called=false` cho bảng có dòng. P01 gọi helper này **sau** actual Store open/autoload. Sau copy đặt RESTART, Store vẫn thực hiện INSERT OR IGNORE entity/environment/config_history vốn đã có trong source fixture. PostgreSQL có thể cấp default identity `nextval` trước khi bỏ insert vì conflict: row không thêm nhưng sequence tiến và `is_called=true`. Vì vậy P01 có thể FAIL ở218 dù content/copy/next identity đều hợp lệ; đây không phải bằng chứng sequence rollback hoặc copy hỏng.

**Counterpart:** N02 direct copy301–320 kiểm strict trạng thái ngay sau copy, rồi actual cash INSERT không cấp rowid và kiểm `max+1`; ở đúng boundary đó strict oracle có ý nghĩa. Giữ counterpart này. Với P01 nên kiểm next generated value an toàn/không trùng theo các operation đã xảy ra, hoặc đo strict RESTART state ngay ở direct-copy boundary; không ép Store giữ nguyên sequence sau legitimate conflict attempts. Không sửa product để làm assertion này xanh. Root cần xử lý oracle trước khi coi thất bại P01 là product regression; agent không sửa test.

## Safety và actual callgraph đã đối chiếu tĩnh

- Unit30 tạo unique retained temp root. `CONFIG_DEMO`34 có entity suffix `_FIXTURE`, `environment=fixture`, VND/0; `tao_kho_demo`101–113 tạo config/raw bằng `xb`, mở DB mới và seed SQL legacy. `Config.load` chỉ đọc chính DEMO config path, không config đang vận hành. Seed56–98 đi qua toàn49 bảng, FK/CHECK enum cụ thể và ba amount0/NULL/int64; đây là bulk-copy fixture setup, không ingest/parser/business workflow.
- PG setUpClass78–90 tạo new retained `kho_test_v13_<uuid>` DB, new legacy schema mỗi ca, cùng DEMO config/raw/source49. Không DROP/cleanup; teardown chỉ close observer. `ban_sao_nguon`157–166 dùng SQLite backup và raw `xb`, không write_immutable. P01/N05 gọi Store constructor/open, không `Store.ingest`: Store constructor chỉ mkdir/mo_ket_noi/DB initialization; `write_immutable(...).unlink` chỉ nằm ở ingest119 và không vào callgraph này.
- `mo_ket_noi` dùng explicit config storage engine/schema/key → `postgres.dsn_from_env` resolver → direct `KetNoiPG`; tests không gọi postgres.connect/migrate/integrity hoặc K2 services/SQL. N04 normal-upgrade counterpart nằm trong legacy schema. Import `postgres`/pg constants qua definitions không tự chứng minh được phép execute K2. Root guard vẫn phải enforce forbidden-call boundary.
- P01/N05 dùng `patch.dict` với key `KTT_V13_BACKUP_TEST_DSN` nonempty; env loại `KHO_STORAGE_*` overrides. CLI N08 truyền `--dsn-key KEY`; dynamic import chỉ `tools/sao_luu_pg.py`, rồi gọi actual `main`. CLI explicit resolver trả env value, không cần `.env`; CLI source preflight/SQL là legacy `KetNoiPG.mo_nguon_sao_luu`, không normal migrate hoặc M9. Không gọi Google/source app/host launcher.
- Raw source/bundle/backup paths đều DEMO temp root; backup.create/restore dùng staging unique và giữ error partial, không unlink. CLI tạo DB/SHA exclusive và rename owned staging directory; tests kiểm old backups/partials SHA nguyên. `journal_mode=DELETE` là chế độ SQLite cho chính tệp mới, không explicit unlink trong Python. Không lấy việc đóng SQLite/native sidecars làm bằng chứng bảo toàn mọi tệp thật; suite không đụng kho thật.
- F7: `co_bi_mat` chỉ trả boolean, asserts message hằng thay assertNotIn(secret,output); `ma` bọc unexpected operation exception thành class/code/sqlstate. Assertions so row values chỉ dùng DEMO fixture; không có print DSN/env/raw rows. **Setup/observer SQL exceptions ngoài `ma` vẫn có thể đi ra unittest traceback**, nên không bỏ outer retained-runner redaction/no-locals guard. Không xem code assertion sạch là đủ bảo đảm mọi failure path không lộ credential.

## Oracle coverage và điều kiện root trước thực thi

- Unit fake-PG tests286–320 chỉ chứng minh SQLite target guard, source-call order và caller transaction; positive chủ ý dừng bằng fake source exception. Không tính chúng là PG copy/roundtrip PASS. Source49/int64/rowid mutation test là component evidence riêng.
- PG N01 có actual damaged schemas: float-money, renamed applied_at, missing FK, duplicate physical history, extra mutating trigger/disabled required trigger và inventory drift; N04 có function/type/operator-only cùng absent/truly-empty/normal-upgrade positives. N05 gọi actual restore và late Store open. `ma` đòi exact business code; auth/driver/timeout không thành PASS. Final `anh` snapshots có data/history/catalog/functions/all sequence last_value/is_called; không phải query/effect trace trước bootstrap, ACL/ordinary role hoặc chứng cứ không từng có transient effects.
- N02b324–355: BIGINT_MAX source được dựng từ DB DEMO/FK hợp lệ; mock chỉ chặn ở `_dat_sequence` lần6, năm lần trước gọi **hàm thật**, full copy không bị stub. Snapshot all sequences/data trước/sau cần PG thực để xác nhận. Chạy/đánh giá fault này phải có direct positive N02 chứng minh sequence thật được đặt khác baseline; call-count6 một mình không chứng minh ACK/mutation hoặc actual permission-denial/crash recovery. Suite không có ordinary non-owner/later privilege case; giữ NOT_VERIFIED.
- Race N06 có actual writer SQL+COMMIT, causal barrier, exact blocker PID/relation/mode,48 bảng khác và cash = nguồn+đúng một writer row. Giới hạn là threads+patched guard trong một process, không hai OS processes; N07 chỉ writer commit trước admission. Không đổi giới hạn thành full race acceptance. CLI N08 dùng actual main/copy/verify/bundle; patch clock/injections ghi rõ, có success controls và fault after SHA/publish, không mock nguyên công đoạn rồi gọi đó là success runtime.
- `chuan_tac_sqlite`/`chuan_pg` tự SELECT typed data nhưng dùng **production** `at.bang_ung_dung/hop_dong` để chọn tables/columns/alias. Vì vậy không gọi chúng là oracle hoàn toàn độc lập cho inventory/column/alias correctness; root independent probe cần source-pinned expected49+direct PRAGMA/catalog và cả actual hidden/alias rowid contract. Count49/nonempty và exact document tuple là controls bổ sung, không thay full independent contract. History P01 so version/checksum, không đòi applied_at tái sinh giống source.
- Trước root release: bind toàn imported modules và dynamic CLI vào frozen314fb, original guard/no-bytecode/retained-runner redaction, explicit localhost server identity và URI DSN contract. `setUpClass` tạo DB qua ADMIN_DSN trước khi tự kiểm endpoint; `dsn = ADMIN_DSN.rsplit('/',1)[0]+'/'+db`81 giả định URI đơn giản, không hỗ trợ tùy ý libpq string/query path. Chỉ dùng runner đã chứng minh đúng URI/target và không expose secret; không gửi DSN cho agent/coder. Thiếu driver/env phải SKIP/NOT_VERIFIED, không PASS; no cleanup.

Không phát hiện thêm P1 safety từ setup/callgraph đã đọc. Root có thể dùng review này để quyết định **selected suite sau release riêng**, không phải cho agent thực thi; P01 oracle R1 phải được diễn giải/sửa đúng boundary. Candidate02 PG thực, ordinary-role, independent process race/CLI, full K2/GUI/full V13 đều chưa được chấp nhận ở đây.
