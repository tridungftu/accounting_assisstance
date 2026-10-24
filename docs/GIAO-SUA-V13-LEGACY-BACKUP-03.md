# Giao sửa V13 — legacy backup, 03

**19/10/2026 — READY_FOR_ROOT_DISPATCH; chưa nghiệm thu.** Đây là vòng sửa hữu hạn R1–R3 dưới đây, giữ kiến trúc/phạm vi legacy đã thống nhất. Root đã đọc đầy đủ source/tests/reviews và chạy kiểm thử candidate02. Chỉ thực thi khi root dispatch đúng session; không tự bắt đầu việc khác.

## 1. Input và write scope

Candidate02 terminal94818/exit0; frozen146 tại `var/codex-dieu-phoi/kiem-chung-20261018-101441/v13-legacy-backup02-handoff-20261019-131139-361/frozen`; manifest SHA256 `314fb1f10b6c61a93505680d3573c792900e4c1cc94f97e1370866b2c726adb4`. Root ghi 0 off-scope/0 missing. Đầu bài02 SHA `6c1973b830ce7ce71e461ea3bf4e96527eb852cd5c9d83dc4b3d15bba5e5f163` và các giới hạn còn hiệu lực; các yêu cầu sửa cụ thể của vòng này ở dưới.

Đọc đủ ba review độc lập (không biến nhận xét static thành runtime FAIL):

- `docs/REVIEW-V13-BACKUP-SAFETY-02.md`, SHA `319f89ce3763a593ad1f0a7f6f1e24f5d9b2b4ce718ef181b139448e1761c066` — actual rowid/P1, physical/sequence call paths và giới hạn.
- `docs/REVIEW-V13-BACKUP-CLI-02.md`, SHA `1c11afc8e32e505bebf01ac36ab2479bd3a65840993cb3486acbb5b142b950ff` — actual rowid/P1 và receipt/P2; F2/F3/F5 có cơ sở tĩnh.
- `docs/REVIEW-V13-BACKUP-TESTS-02.md`, SHA `31d16ace8421fed560b97f1b341f493d32671d5d2604bb1df41827d8505ed44b` — sequence oracle/P2 tại sai boundary; giữ setup/redaction an toàn.

**Trạng thái bằng chứng thực tế trên Windows:** root native SQLite unit **11/11 PASS**, 0 fail/error/skip, frozen146 giữ nguyên. Summary `var/codex-dieu-phoi/v13-root-sqlite-unit02-74d7e0001d61/summary.json`, SHA `d33946bb64dd66247c12c912002339ad9ebc4f2934ba0ede4870446a2db815af`. Root actual PG suite candidate02 handle8905 **terminal exit1**, tool8712e3: **10 chạy, 9 PASS, 1 FAIL, 0 error/skip, 133.472s**. Failure duy nhất P01 tại218→192 `SEQUENCE_SAU_CHEP_SAI`, phù hợp finding R3 về boundary; không quy thành product sequence regression. Summary `var/codex-dieu-phoi/pg-retained-20261019-133136-c9c550f1/summary.json`, SHA `e0d4a43e0d70d4193294f343bcd3720e8fae1b862f7ac99dfddfb5e03e28b6fa`. Wrapper summary SHA `bd10259aa5639bb1fc2171f9e5cadc047038f6201eb1b9892f7b64ae9098e130`: 146 source unchanged, original guard active, 17 explicit resolver calls, 0 forbidden K2/M9 calls, new local retained DB. Các assertions sau điểm FAIL của P01 chưa được chạy; không gọi full P01 PASS. Đây vẫn là coder-authored suite được root chạy, không phải oracle hoàn toàn độc lập hay ordinary-role/child-CLI/full V13 acceptance. PG tự kiểm của Claude02 vẫn UNRUN vì Bash permission denied ba lần. **Không Read var để đọc các receipts; số tổng hợp/hash ở đây là root evidence đã lọc.** Không sửa product theo assertion sai.

**Chỉ bảy write targets:**

1. `src/kho_tri_thuc/ha_tang/an_toan_sao_chep.py`
2. `src/kho_tri_thuc/ha_tang/sao_chep_bang.py`
3. `src/kho_tri_thuc/ha_tang/ket_noi.py`
4. `tools/sao_luu_pg.py`
5. `tests/test_v13_backup_safety.py`
6. `tests/test_v13_backup_safety_pg.py`
7. **Mới:** `docs/BAO-CAO-V13-LEGACY-BACKUP-03.md`

Đây là allowlist tối đa, không yêu cầu chạm cả bảy file. Không sửa báo cáo01/02, reviews, đầu bài, guard/policy/runner/dispatch/private probes/ledgers; không sửa `database.py`, `feature_migrations.py`, translator, `postgres.py`, `pg_migrations.py`, Store/backup/config/dependencies/launcher. `ket_noi.py` chỉ sửa call path cần thiết trong phạm vi legacy, giữ normal upgrade/migration statements/checksums. Nếu cần ngoài scope, báo exact dependency cho root trước. **Không làm M9, code/schema/service/UI của M9, original source apps, K2, nghiệp vụ mới hoặc kho thật.** M9 chỉ đang xác định cách lấy JSON+Excel hiện có do root xử lý riêng.

## 2. R1 / P1 — actual PG rowid không biểu diễn được phải bị từ chối an toàn

Frozen02 `sao_chep_bang.py:247–248` dùng INTEGER-PK alias thay actual PG rowid; `:308,313–315` bỏ actual rowid khi chép bảng alias; nội kiểm `:322` và CLI callback đều dùng oracle đó. DDL hiện hữu có hai identity độc lập, không có invariant ép bằng nhau. Nguồn chuẩn có `audit_events(id,rowid)=(100,7),(1,8)` cùng các trường bắt buộc hợp lệ là counterexample tĩnh: copy giữ id nhưng actual SQLite rowid thành100/1, thứ tự đổi, hai hash vẫn có thể khớp. Không coi lời mô tả hạn chế trong report02 là chấp thuận mất rowid.

Sửa theo hướng hữu hạn: kiểm **mọi bảng INTEGER-PK alias** trong cùng authoritative PG repeatable-read snapshot dùng để chép/verify; nếu actual PG rowid khác alias thì trả business refusal rõ **trước SQLite COMMIT và trước publish**. Không sửa/đồng bộ dữ liệu hoặc identity nguồn, không thay DDL, không thêm format/engine mới. Giữ nguyên source, target cũ và các backup/partial cũ; staging của lần thử mới phải được giữ và báo trung thực. Công bố exact refusal code mới trong report/test; lỗi driver/auth/timeout không thay business refusal.

Oracle phải quan sát actual PG rowid riêng với PK alias; không tái dùng lựa chọn alias của product làm expected rồi gọi đó là kiểm actual rowid. CLI independent reader/callback tiếp tục nằm trong cùng source snapshot; không bỏ kiểm nội dung để né mismatch/race. Với nguồn biểu diễn được, actual rowid, typed values và column contract phải giữ; không chỉ ORDER BY hoặc row count.

Controls: positive alias-aligned và non-alias hidden rowid; negative hai dòng lệch trên (có thể thêm một alias table không cần FK để test nhỏ) với history/DDL/FK hợp lệ, từ chối đúng và source nguyên; không publish success. Giữ control sửa rowid nhưng giữ thứ tự/content ở tệp copy bị bộ kiểm thật phát hiện; int64 >2^53, NULL và0 không đổi. Không cần chạy lại mọi alias bằng cách tạo framework mới; product guard phải áp dụng toàn nhóm alias thực.

## 3. R2 / P2 — receipt xác định ownership và trạng thái không biết

Frozen02 `sao_luu_pg.py:63–77,89–90,139–142` suy `da_cong_bo` từ final.exists(): final do rival tạo làm run chưa rename vẫn báo đã công bố, còn liệt kê artifact rival là của run. Nếu metadata/iterdir lỗi, receipt exception che lỗi gốc rồi CLI fallback báo `con_lai=[]/partial=null` dù chưa biết staging còn gì.

Theo dõi publish-state của **chính run**, chỉ xác nhận đã công bố sau owned rename hoàn tất. Final xung đột phải được ghi là collision/bên khác; không nhận ownership hoặc ghi đè/di chuyển nó. Receipt collection không được thay lỗi gốc; giữ sanitized original code/class và tách các artifacts đã xác nhận với inventory UNKNOWN/error khi không đọc được metadata. Không dùng absence mặc định cho phần chưa quan sát được; không cleanup để tạo trạng thái phù hợp receipt.

Controls: rival final xuất hiện giữa precheck/publish phải bị từ chối, bundle rival và old artifacts nguyên, own published=false; lỗi metadata/iterdir sau một lỗi copy/verify phải giữ mã lỗi gốc và UNKNOWN rõ, file partial giữ nguyên. Giữ positive hai lần cùng phút unique/exclusive, SHA và actual-content checks trước single-bundle publish, failures sau SHA/trước publish, nguồn cũ readonly refusal, `--giu` không rotate, nhãn `LEGACY_DB_FALLBACK`. Không nới cam kết Windows thành portable/crash-durable hoặc full artifact/K2 backup.

## 4. R3 / P2 — đo sequence đúng ranh giới, không sửa product để khớp assertion sai

Frozen02 PG test `kiem_sequence_sau_chep:183–192`, P01 `:204–218`: strict `last_value=max+1/is_called=false` được kiểm sau Store constructor. Store thực hiện legitimate INSERT ... ON CONFLICT DO NOTHING; default nextval có thể đã được tiêu thụ dù row không thêm. Đây không đủ để kết luận copy/rollback sai.

Giữ strict RESTART-state oracle **ngay direct-copy boundary**, trước Store/probe INSERT có thể gọi nextval (counterpart N02 đã có). Sau actual Store open/backup/restore/reopen, kiểm content/identity mode và next generated identity an toàn, không trùng, tương ứng operations đã xảy ra; không buộc sequence quay về trạng thái trước legitimate conflict attempts. Nếu test INSERT để đo next value, phân biệt baseline content và dòng DEMO mới do phép đo tạo. Không mock nextval hoặc sửa Store/product để assertion max+1 sau Store xanh.

Giữ positive actual sequence advance; BIGINT_MAX refusal trước effects và fault sequence muộn rollback **mọi** last_value/is_called/data/catalog so với đúng before-state. Không thay oracle strict toàn bộ bằng row counts/call counts, không bỏ controls hoặc đổi expected để hợp failure chưa phân loại. Oracle inventory vẫn cần chỉ rõ phần dựa production contract và phần quan sát độc lập; không tự gọi selftest là độc lập hoàn toàn.

## 5. Kiểm tra, giới hạn và bàn giao sau khi root release

Giữ fixture DEMO tự chứa config/raw exclusive +49 bảng nonempty, actual StorePG→backup→verify→restore fresh PG→StorePG reopen, original SQLite typed equality/raw/config/history version+checksum; marker chỉ exempt đúng key và kiểm riêng. Giữ nonempty/changed seed/old/partial/drift/history/trigger/function-type-operator inventory refusals, locks/transactions/caller transaction/FK-mode, source-old không migrate. Giữ race relation/mode/exact blocker PID và full49+exact writer row; in-process/monkeypatch controls phải ghi đúng giới hạn. Không buộc product phù hợp một test oracle không hợp lệ.

Chỉ sau root chốt dispatch/runtime gate mới tự kiểm đúng hai lệnh đã cấp; không execute từ DRAFT:

```text
python -X utf8 -m unittest discover -s tests -p test_v13_backup_safety.py
python -X utf8 var/codex-dieu-phoi/run-pg-tests-retained.py test_v13_backup_safety_pg.py
```

Root bind system Python/guard/no-bytecode/dependencies/retained runner; credential chỉ trong runner local, explicit resolver test key, localhost, DB/schema DEMO mới retained. Chỉ execute exact runner command, không Read runner/var/.env/credential hoặc dump env. Imports postgres/pg definitions trong giới hạn đã review; cấm postgres.connect/migrate/integrity và SQL K2/M9. Không sửa policy/guard/shell để vượt denial; nếu bị chặn, báo UNRUN cùng sanitized reason và dừng đường đó. Không DROP/cleanup/delete file/temp/DB/role/attempt, không reset/clean/commit; giữ mọi failed artifact. Không Google/cloud/approval thật/CFO_NTD.

Báo cáo03 nêu exact files, từng R1–R3 và kết quả PASS/FAIL/UNRUN/skip cùng technical receipt path/số tổng hợp; không in DSN/password/raw rows/traceback/locals. Bảo toàn outer redaction cả failure setup/SQL ngoài helper. Sau report kết thúc CLI để root freeze/review và chạy independent candidate-bound probes; không tự nghiệm thu V13/33, ordinary role, full K2, actual child race/CLI hoặc GUI.
