# Review độc lập V13 backup CLI và tests — 01

**19/10/2026 — STATIC_ONLY / NOT_RUN / CHƯA NGHIỆM THU.** Đọc frozen candidate sau Claude terminal79641/exit0/resultfalse; không import/chạy product/tests/CLI, SQL, DB, DSN/.env, host hoặc source app; không sửa product/probe, không xóa file. M9 không thay đổi. Scope: CLI, hai test files, coder report và selected legacy definitions để bind API/oracle. Không thay review core guard/schema của agent khác.

Frozen: `var/codex-dieu-phoi/kiem-chung-20261018-101441/v13-legacy-backup01-handoff-20261019-122107-919/frozen`,146 files; manifest do root cấp **`da3f41f317efebd3d00246b9ec845b2ff612743c8176f7f4c81fc3256fd75e72`**. Không đọc interim/live candidate. Các line dưới gắn đúng frozen path.

| File trong frozen | SHA256 |
|---|---|
| `tools/sao_luu_pg.py` | `3d08850f272e8f6c4040a8bf1c7a23de53dc08237a636ed077cc0a400a543c5d` |
| `tests/test_v13_backup_safety.py` | `dcdf14ae5d5b9b5fdfd09961e40c06625f233e123e1ad839834872ddc3b27475` |
| `tests/test_v13_backup_safety_pg.py` | `307c8b6da08166cacb497e6316f68a40f035ba538ebae46ffcc5ab9d0d4c4f64` |
| `docs/BAO-CAO-V13-LEGACY-BACKUP-01.md` | `fa2e2a2b4116eaf4470dc458867b9750e3873b406bee1824e487dad088dba125` |
| `src/kho_tri_thuc/ha_tang/an_toan_sao_chep.py` | `c72204c8cde2bf6ad4620fec3837a38900a16627db00114508a3971eaa7df09d` |
| `src/kho_tri_thuc/ha_tang/sao_chep_bang.py` | `e68cf5b027f4d4c8d6a9442d44ca68f5cf935a032fc684cc10586ab476c2db69` |
| `src/kho_tri_thuc/ha_tang/ket_noi.py` | `7793cb316087e445fe3d3d80541971b8b41cc2938fbb3069311c1ce36f45b027` |

## Findings cần xử lý hoặc bind trước nghiệm thu

**F1 — P1, PG test setup chưa chạy được dưới release no-delete và chưa tự chứa config.** `test_v13_backup_safety_pg.py:72–79` đọc `ROOT/cau_hinh.toml`, rồi `Store.ingest(sao_ke.json)`. Frozen146 không có `cau_hinh.toml`; `config.py:40–41` luôn read_bytes nên chạy chính frozen sẽ lỗi setup. Nếu chạy workspace có config thì vẫn tới unchanged `store.py:119 → write_immutable:29–41`: tạo `.raw-*`, hard-link rồi **`temporary.unlink(missing_ok=True)`** trong finally. Required guard chặn unlink; đây là nhánh setup dự kiến lỗi trước business tests, không phải runtime result đã đo. Không bỏ guard hoặc sửa Store ngoài whitelist để chạy xanh. Test cần config DEMO local đã pin và fixture setup không xóa file (có thể dùng retained seed pattern), giữ raw/config/state không rỗng. Store source pin `7c6c3fa4225b6089c4913a2870c6f4c26d7f813608d017901f6aea9aa7288dc5`.

**F2 — P2, publish DB trước SHA tạo nhánh false-failure và partial receipt sai.** CLI `:75–81` rename partial sang final DB rồi mới hash/read DB và exclusive-create/write SHA. Ví dụ process khác tạo đúng `<final>.sha256` sau khi tên partial đã lộ, hoặc ghi SHA bị permission/disk-full: DB mới đã publish, partial đã mất, `main` trả2 nhưng `sao_luu:52–53` vẫn gắn `partial_giu_lai=tam.name` không còn tồn tại. Old files vẫn được giữ, song deliverable đôi DB+SHA chưa hoàn tất và failure contract không đúng. Test `:457–468` chỉ inject trước publish nên không bắt nhánh này. Chuẩn bị/verify checksum trước publish, rồi có publish protocol giữ đúng partial/final state và receipt cho mọi lỗi; không sửa bằng xóa/rollback file đã tạo. Cần fault sau DB publish/trước SHA completion trong retained output mới, không lấy copy-fault mock thay thế.

**F3 — P2, verify bằng source snapshot khác làm từ chối backup nhất quán khi writer hợp lệ chạy.** CLI `:62` gọi helper copy; helper `sao_chep_bang.py:230–259` dùng một PG REPEATABLE READ, commit SQLite rồi ROLLBACK PG. CLI `:63 → _kiem_noi_dung:38–40` mở PG snapshot mới để so. Writer commit giữa hai snapshot sẽ làm `BACKUP_VERIFY` dù SQLite là bản nhất quán đúng snapshot đầu; nguồn đang ghi thường xuyên có thể không backup được. Không phải bằng chứng bản copy sai hay dữ liệu bị mất. Hai phép đọc kiểm độc lập phải cùng source snapshot có thẩm quyền, hoặc có source exclusion được bind xuyên cả copy/verify; không so snapshot thời điểm khác rồi gọi content corruption. Test cần causal writer giữa hai bước, chưa có trong candidate.

**F4 — P2, CLI content oracle không hash giá trị rowid.** CLI `:40` gọi product `doi_chieu_noi_dung`; helper `:189–195` lấy data columns từ PRAGMA/_cot_pg (PG loại rowid), và `:170` chỉ SELECT các cột đó, ORDER BY rowid. Với bảng TEXT-PK/implicit rowid, dịch toàn rowid1,2 thành101,102 nhưng giữ thứ tự/data sẽ cho cùng hash và khop=true. CLI không phát hiện vi phạm cam kết giữ rowid. Thêm actual rowid có type tag vào parity oracle (xử lý INTEGER-PK alias rõ), không chỉ ORDER BY. Test CLI `:449–454` chỉ SHA tự tính/integrity, không independent source canonical nên cũng bỏ lọt phản ví dụ này.

**F5 — P2, CLI backup có thể tự nâng cấp source schema trước khi sao lưu.** `_chep_va_cong_bo:58` gọi `KetNoiPG(...,tao_moi=False)` với target current mặc định; constructor `ket_noi.py:216–224` luôn `_migrate(target)` khi không autoload. `tao_moi=False` chỉ cấm tạo schema vắng mặt, không cấm nâng cấp existing old source. Backup một schema hợp lệ cũ vì thế có thể ghi DDL/history trước snapshot; không bảo toàn source và không còn bản trước upgrade. Thêm readonly current-schema preflight/refusal riêng ở CLI hoặc cách open nguồn không migrate đã review; giữ normal supported upgrade ngoài đường backup. Đây là suy luận static từ actual call path, chưa chạy trên old source.

**F6 — P2, self-test oracles chưa đủ thay cho acceptance độc lập đã chốt.** Đây là giới hạn cụ thể của tests, không suy ra candidate core race sai:

- `p01:161–171` so PG1 với PG2 và raw existence, chưa so original SQLite typed49/raw/config hash. Lỗi biến đổi data ngay autoload đầu có thể lặp qua cả hai schema và vẫn pass. `chuan_tac:138–140` lấy table list từ product guard, chưa inventory độc lập.
- `n06:337–348,364–401` monkeypatch guard làm barrier, chỉ thấy `wait_event_type=Lock`/tên loại; chưa nối writer blocker PID và exact cash relation/mode với copier. Kiểm hai cash keys/counts và bỏ cả cash table khỏi kq parity, không so full49 cộng exact writer row. `n07:405–412` writer đã COMMIT trước khi copier bắt đầu, không kiểm writer uncommitted thắng rồi copier thực sự chờ admission.
- `n08:436–468` gọi `mod.main()` trong process và hai lần nối tiếp, chưa assert cùng wall-clock minute/child entrypoint/guard, không independent canonical source→DB; injected function return/error chỉ kiểm flow của mock, không chứng minh detector thực phát hiện corrupt content. Cần root chạy hai actual races/actual CLI bằng oracle đã bind; không nâng các ca này thành proof đầy đủ chỉ vì unittest xanh.

**F7 — P2, DSN leak regression có thể bị unittest in lại credential.** `test_v13_backup_safety_pg.py:440` dùng `assertNotIn(self.dsn,captured_output)`. Nếu output thật chứa DSN, assertion failure tự format member/haystack, đưa DSN vào failure log. Dùng boolean predicate với message hằng đã làm sạch, không đặt secret/output gốc vào assertion arguments/message. `:395` cũng chuyển raw actor exception vào assertion message; cần sanitized class/code/sqlstate nếu failure path này được release. Review không đọc hay in bất kỳ DSN value nào; đây là nhánh lỗi static, chưa có leak thực quan sát.

## Những phần source đã đáp ứng về thiết kế, chưa runtime-verified

- CLI `:30–32,45–49,79–81` có UUID name, partial exclusive và SHA exclusive; bỏ explicit unlink sidecar và toàn bộ rotate/move old backups. Chỉ rename owned partial để publish; `--giu` báo `ap_dung=false`. Final rename dùng giả định Windows trong `:77`; chưa chạy publish-race trên máy. Không suy ra no-overwrite portable từ exists-check trên mọi OS.
- `:35–40,63–74` có actual recomputation content/columns và integrity trước DB publish, tốt hơn counts-only; F3/F4 vẫn giới hạn oracle. Nhãn `LEGACY_DB_FALLBACK` nói rõ DB-only, không raw/full K2. Error boundary dùng `loi_sach`, không trực tiếp str(exc)/traceback; F2 receipt và F7 test logging còn thiếu.
- Tests có actual PG/SQLite/Store paths, exact DataError codes, retained DB/schema/temp folders và before/after rows/history/identity/sequence; không có DROP/file cleanup trong test files. Non-PG `_NguonGia` là fake nguồn cố ý để kiểm guard, **không full PG positive**; `schema_version()` của fake trả constant nên `lenh=[]` không chứng minh actual PG không có SELECT-version trước guard (`helper:221`).
- Đọc selected call graph không thấy tests gọi postgres.connect/migrate/integrity hoặc M9/K2 business. DSN resolver key explicit là `KTT_V13_BACKUP_TEST_DSN`; root vẫn phải bind process/module/DB authority, driver và fixture paths trước run. Không coi skipUnless/driver/setup failure là đạt.

## Actual candidate binding cho private glue sau này

Chỉ ghi binding static, **không sửa/bật glue02**:

- `chep_sqlite_sang_pg(src,pg,*,schema=None)` vẫn ở `sao_chep_bang.py:52`; actual bulk source `SELECT rowid,... FROM "{table}" ORDER BY rowid` ở `:109` khớp regex cash của glue02. Nó nằm sau `_khoa_dich_pg:95` và admission `:96`, trong một `raw.transaction:94–136`. Ordered locks `:67–74`: hai advisory keys rồi EXCLUSIVE trên history/all existing application/extra tables; không còn ALTER identity. Đây là causal barrier phù hợp để root bind, chưa proof runtime/writer completeness.
- Constructor có source tồn tại gọi `_kiem_dich_nap:220` trước `_migrate:221`; current code `an_toan_sao_chep.py` phân loại nonempty trước old-version: **older exact fresh-seed → `PG_DICH_SCHEMA_CU`; older có row ngoài seed/no marker → `PG_NAP_DO`; marker/nonempty → `PG_KHO_SQLITE_CON`**. Bind những mã này trước runtime; không generic PG_CHEP/auth/timeout. Partial/unknown → `PG_DICH_KHONG_TUONG_THICH` nếu đọc classifier được, không tự coi malformed-driver error là business refusal.
- Planned CLI cash-lock fault có thể bind về static order: exclusive partial `CLI:49` trước constructor/copy; current no-autoload constructor chỉ đọc history khi schema current; first source cash bulk SELECT là `helper:243` trong copy, sau partial đã tạo. Root actual raw source AccessExclusive + observer đúng CLI PID/relation + default lock_timeout có thể tạo real copy error giữ partial. Expected outer business code qua helper wrapper là **`PG_CHEP`**; `loi_sach(DataError)` hiện giữ code, không giữ sqlstate field của cause. Chưa execute/inspect DB hoặc triển khai fault wrapper.

Private glue02 vẫn pin **`b66312095150dfa4ccdf1a557469e0ed3ae1f1c129ba0adca047ed5cedc9f427`**, release FALSE. Actual root fatal-profile hook/watchdog/oracle/child-process binding chưa có; không đóng F1–F3 của `REVIEW-V13-RACE-GLUE-01.md` nhờ review product này.

## Trạng thái bằng chứng

Coder report `:7–16` ghi đúng **0 test run,0 pass,0 fail,UNRUN** do Git Bash exit66 trước Python. Root báo một readonly Bash probe khác đã exit0; điều đó không biến các test thành đã chạy hoặc chứng minh hết lỗi setup. Nếu root mở validation-only session sau freeze, kết quả của session đó phải có receipt riêng; review hiện không viện dẫn kết quả tương lai. **Giữ candidate CHƯA NGHIỆM THU; sửa/bind findings, chạy guard-safe validations và independent probes trước khi kết luận.**
