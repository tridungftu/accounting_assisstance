# Giao sửa V13 — an toàn copy và sao lưu legacy, 01

**19/10/2026 — READY_FOR_SEPARATE_ROOT_DISPATCH, chưa nghiệm thu.** Đây là đầu việc V13 độc lập ngoài M9 trong phạm vi đã được Anh ủy quyền. Thực hiện khi root phát lệnh cùng session với whitelist riêng bên dưới. **M9 chỉ xác định cách lấy dữ liệu từ Code final Anh đã cấp; ứng dụng nguồn đã làm theo dõi vay. Không tiếp tục repair02, sửa schema/nguồn/service/UI M9, xây lại engine vay hoặc đổi tên sửa M9 thành common core.**

## Mục tiêu và căn cứ

Sao chép hai chiều phải từ chối kho đích đã có dữ liệu trước mọi thay đổi; sao lưu mới không được ghi đè, xóa file hoặc di chuyển bản cũ. Giữ phương án C: legacy V12 trên SQLite/PostgreSQL; kho thật vẫn SQLite. Không chuyển lõi sang K2 hay thêm engine nghiệp vụ. Căn cứ TL39, `V13-CONG-SAO-LUU-PHUC-HOI-33.md` SHA21d78859…54e0, actual source hiện tại và probe độc lập mà root bổ sung lúc release.

Standalone SQLite đã có10/10 tiêu chí chọn lọc PASS, review `REVIEW-V13-SQLITE-BACKUP-01.md` SHA352917fe…82b6. Phải giữ các positive guard/roundtrip/raw/manifest đó; không suy thành toàn V13 hoặc full K2 đạt.

## Phạm vi file được sửa

- `src/kho_tri_thuc/ha_tang/sao_chep_bang.py`: hai direct-copy entrypoints và guard dùng chung.
- `src/kho_tri_thuc/ha_tang/ket_noi.py`: chỉ guard đích legacy ở `_nap_neu_can`, `_trang_thai_schema`, `kiem_dich_phuc_hoi`, cùng admission trước `_migrate` trong constructor khi có autoload source và lock cần thiết cho các đường này. Không sửa journal/K2/nguồn/schema migration hoặc normal supported upgrade không có autoload.
- Có thể thêm một utility `src/kho_tri_thuc/ha_tang/an_toan_sao_chep.py` nếu cần để tránh circular import; không nhân đôi nguồn quy tắc đích trống.
- `tools/sao_luu_pg.py`: duy nhất CLI backup legacy đã có.
- `tests/test_v13_backup_safety.py` và `tests/test_v13_backup_safety_pg.py`: DEMO tests mới, retained resources, không cleanup xóa file/DB/role.
- `docs/BAO-CAO-V13-LEGACY-BACKUP-01.md`: báo cáo coder. Không sửa public CHANGELOG/hàng đợi/coverage hoặc review/probe của Codex.

Các file product khác giữ bytes nguyên. Đặc biệt không sửa `pg_migrations.py`, `postgres.py`, `database.py`, `feature_migrations.py`, `k2/`, `nguon/vay_9.py`, CRM, launcher/config/dependencies hoặc source app gốc. Không sửa source #10 quản lý kho. Không đổi lịch sử/checksum migrations hoặc thêm ngoại lệ migration.

## Sửa bắt buộc

1. **Guard toàn đích ở cả hai chiều.** Hiện SQLite→PG ALTER identity rồi DELETE49 bảng; PG→SQLite DELETE49 bảng, không kiểm tất cả đích. Hai sentinel workspace_meta/attempts bỏ lọt cash-only/knowledge-only. Chỉ nhận đích mới tương thích: exact49 application tables, column/schema contract và lịch sử version/checksum hợp lệ; exact fresh seeds, gồm knowledge_epoch=(1,'initial'). Extra/changed seed, extra dữ liệu hoặc unknown inventory phải từ chối rõ. Không coi bảng rỗng duy nhất hay marker là bằng chứng đích trống; schema-history là metadata thứ50, không phải business table.
2. **Guard trước effects và tránh race.** SQLite→PG giữ admission/open lock `mo-kho:<schema>` nhưng không coi khóa đó đủ để chặn writer: legacy BEGIN IMMEDIATE dùng key khác `hashtext(schema)`; raw INSERT không tự tuân advisory lock. Chốt actual write exclusion cho mọi allowed writer trong toàn guard/copy/sequence window, kể cả raw DML. Ưu tiên một transaction với ordered table locks ngăn writer và inventory/guard bên trong; nếu vẫn nhiều phase commits phải chứng minh exclusion xuyên toàn phases, không chỉ lock ở phase đầu. Direct helper không được đi đường vòng. Guard chạy trước ALTER/sequence/DELETE/COPY. Tôn trọng constructor nested lock/caller transaction ownership, release đúng số lần; không tự commit caller. PG→SQLite kiểm dưới write lock/transaction đích trước FK-mode/DML. Nonempty/unknown rejection bảo toàn dữ liệu/schema/history/identity/sequences/FK-mode, không hoàn tác về cùng hash để che effects trung gian.
3. **Actual restore/open.** Khi có autoload source và existing schema, admission phải thực hiện dưới constructor lock **trước `_migrate`**: existing older/partial/unknown/nonempty schema reject trước schema/history delta. Phân biệt absent schema được tạo mới với existing current exact fresh-seed schema; không dùng thiếu sentinel làm fresh. Giữ normal supported migration khi không có autoload. Early restore preflight chạy trước publish files và actual StorePG/autoload revalidate sau init dưới write exclusion; đối thủ ghi sau preflight phải làm late open từ chối thay vì ghi đè. Hai helper vẫn tự bảo vệ khi gọi trực tiếp. Existing source DB/backup/partial không xóa/sửa. Không đóng full acceptance chỉ vì restore trả verified trước khi Store mở.
4. **CLI backup giữ mọi file.** Tên đích/staging unique, tạo exclusive, không reuse partial hoặc ghi đè. Bỏ explicit sidecar unlink và việc move/rotate bản cũ; `--giu` nếu giữ compatibility phải báo rõ retention không áp dụng, không tự dọn. Verify integrity và independently recomputed source/destination content/columns trước publish, không chỉ counts. Giữ DB+SHA deliverable được mô tả đúng là legacy DB fallback; không gọi DB-only là full artifact/K2 backup. Lỗi giữ partial và trả sanitized failure.
5. **Không làm lộ dữ liệu.** Không đọc var/.env/backup thật/source app hoặc in DSN/traceback/rows. DSN test chỉ do root-retained runner cung cấp trong process; báo mã lỗi/sqlstate/count/hash. Không dùng CFO_NTD, Junsky/cloud/Google/host/launcher.

## Tiêu chí kiểm thử và bàn giao

- Positive nonempty DEMO actual StorePG→create/verify backup→restore fresh configPG→actual StorePG reopen, độc lập49-table canonical equality với rowid/typed values/raw/config. Chỉ exempt exact generated `v13_nap_tu_sqlite`; kiểm shape/marker riêng. Legacy regenerated history so version/checksum; full K2 không nằm scope.
- Negative riêng từng chiều: cash-only, knowledge-only, changed seed/extra row/table, marker/nonempty; không pass generic exception/driver failure. Reject trước mutation, state/identity/sequences nguyên. Không xóa dữ liệu để tái dùng target; mỗi ca tạo target DEMO mới và giữ lại.
- Actual restore preflight và late open với đích có dữ liệu phải reject đúng; thêm existing older-version nonempty/partial autoload target, đo schema/history/identity/sequence không đổi và fresh supported counterpart. Concurrency dùng hai connections thực, actor2 thực INSERT/COMMIT vào cash/knowledge tại causal barrier sau guard/giữa phases. Chỉ nhận writer bị block/denied trong exclusive window rồi row sau copy giữ, hoặc writer thắng trước admission khiến copy reject trước mutation. Không nhận writer commit rồi mất row, no-op writer, generic timeout/setup PASS hoặc chỉ tranh advisory lock. Không fake atomicity bằng final hash bằng nhau sau ALTER rồi hoàn tác.
- CLI hai lần cùng phút tạo hai file khác, existing backups/partials nguyên hash; injection copy/verify failure giữ partial và không final success. Không chạy CLI cũ còn unlink để tạo baseline âm.
- Các SQLite positive/negative đã chấp nhận giữ hành vi; tests không mirror guard implementation và phải có positive control thực.

Claude tự chạy tests cho file mới qua retained runner mà root cấp; không chạy suite M9 hoặc K2 migrations. Có thể import `postgres`/`pg_migrations` **chỉ definitions/DSN resolver** với explicit nonempty test env, không gọi postgres.connect/migrate/integrity hay execute K2 SQL. Nếu cần file khác hoặc quyết định mới, báo dependency cụ thể và làm phần còn lại; không tự mở rộng scope.

Báo file thay đổi, test thực đã chạy/fail/skip, hạn chế còn lại. Root kiểm diff/pins, chạy probe độc lập và agent chưa tham gia code review trước khi chấp nhận. Không tự tuyên bố V13/full33 hoàn thành, không commit/reset/clean/xóa bất kỳ file/DB/role.

## Căn cứ sửa review R1/R2 trước dispatch

Root đã đọc `REVIEW-V13-LEGACY-HANDOFF-01.md` SHAcb169525…f0ee và bổ sung writer exclusion/control cùng constructor admission-before-migrate nêu trên. Hướng giảm phases cần được Claude kiểm thật: PostgreSQL16 `COPY FROM` cho phép ghi giá trị identity được cung cấp, nên không mặc định cần ALTER identity rồi COMMIT trước COPY. [COPY16](https://www.postgresql.org/docs/16/sql-copy.html). Advisory lock do ứng dụng tự tuân; table lock có thể chặn actual INSERT/UPDATE và giữ đến hết transaction. Chọn lock mode/order tương thích, không đổi migration statements. [Explicit locking16](https://www.postgresql.org/docs/16/explicit-locking.html). Đây là căn cứ kỹ thuật và hướng xử lý, không bằng chứng runtime của candidate.

## Bằng chứng baseline và lệnh chạy trong package riêng

Root đã chạy probe PostgreSQL02 trên DB DEMO mới: **4 positive PASS /6 ca từ chối nonempty FAIL**,0 unexpected/forbidden K2 calls. Independent `REVIEW-V13-PG-BACKUP-01.md` SHA `2d4d924dfb42e6d842937164d7f777fc3aee2e98065e8a6b8bde157433af566c` được root đọc đủ. Result SHA `06883a8f6c41ee5f2340d06db39772e5dc36dd9b31ffa1e1c1d0c807e7d93f4a`; không cấp coder đọc var hoặc raw evidence.

- Actual StorePG→backup→verify→restore(configPG)→StorePG reopen/49-table canonical preservation đã chạy;12/49 application tables có dữ liệu,37 rỗng. Giữ positive này.
- Direct-copy hai chiều và constructor autoload bỏ lọt cash-only/knowledge-only: cash row bị mất; knowledge cùng count nhưng content bị thay. Source/bundle/15selected product pins giữ nguyên; lỗi nằm đúng các entrypoints trong scope.
- Restore preflight knowledge-only chấp nhận và publish folder; PG target **chưa đổi** trong ca đó vì chưa mở Store sau restore. Phải từ chối trước publish, không gọi đây là PG overwrite đã xảy ra.
- Expected business refusal cho các đích nonempty này giữ mã legacy **`PG_NAP_DO`**; unknown/older schema có mã cụ thể thích hợp nhưng không dùng driver/auth/timeout thay business refusal. Không sửa probe/expected hoặc dữ liệu để làm xanh.

Coder dùng system Python có guard/no-bytecode/PYTHONPATH do root cấp. Lệnh tự kiểm được cấp đúng hai patterns:

```text
python -X utf8 -m unittest discover -s tests -p test_v13_backup_safety.py
python -X utf8 var/codex-dieu-phoi/run-pg-tests-retained.py test_v13_backup_safety_pg.py
```

Retained runner nạp credential trong process và redact log; không đọc source runner/var/.env hoặc dump env. PG tests phải tự tạo **new retained `kho_test_*` DB** rồi dùng direct `KetNoiPG`; không dùng postgres.connect/migrate/K2 SQL. Đặt DSN resolver key tường minh theo test process; không fallback tới .env. Không cleanup DROP/file/role. Nếu command bị permission deny, báo lệnh và tiếp tục code trong whitelist; không dùng shell khác vượt policy.

Root đã chấp nhận import-boundary review `REVIEW-V13-IMPORT-BOUNDARY-01.md` SHAa67c5a82…9066 và R1/R2 closure ở `REVIEW-V13-LEGACY-HANDOFF-01.md` SHAc3c8f944…5258. Đây là lệnh kỹ thuật đã có phạm vi; không hỏi lại kiến trúc hoặc lệnh M9 cũ. Trả báo cáo mới trong whitelist rồi dừng để Codex freeze/review/run độc lập. Root không chạy product/SQL/HTTP song song lúc coder sửa.
