# Review độc lập V13 backup safety — frozen02

**19/10/2026 — STATIC_ONLY / CHƯA NGHIỆM THU.** Còn một **P1 về bảo toàn actual PG rowid ở bảng INTEGER PRIMARY KEY**. R1 physical contract và R2 sequence đã có sửa đáng kể về source/control flow; chưa chứng minh PG runtime hoặc các positive. Không import/chạy product/test/SQL/DB/CLI/host, đọc secret/source app, sửa product hoặc xóa file; không làm M9. Counterexample dưới là suy luận source, chưa phải exploit đã chạy.

## 1. Input/pins và phạm vi đã đọc

Root giao candidate02 đã terminal94818/exit0; frozen tại `var/codex-dieu-phoi/kiem-chung-20261018-101441/v13-legacy-backup02-handoff-20261019-131139-361/frozen`. Manifest146 `../source-hashes.json` SHA **`314fb1f10b6c61a93505680d3573c792900e4c1cc94f97e1370866b2c726adb4`**. Review này kiểm sáu selected hashes khớp cả `sha256` và `frozen_sha256`; không tự nhận đã audit đủ146 files.

Đọc request02 SHA `6c1973b830ce7ce71e461ea3bf4e96527eb852cd5c9d83dc4b3d15bba5e5f163`, review safety01 SHA `3a06f42b37e87da3d5ad0de5fc041a3c8fb6e05f6a91c373865aef3945cb585c`; full utility417/copier335, constructor/admission/source-backup/normal-upgrade/restore trong ket_noi; exact diff utility/copier/ket_noi so frozen01 `v13-legacy-backup01-handoff-20261019-122107-919/frozen`. DDL/translator/feature migration chỉ đọc các phần cần cho contract và kiểm coupling rowid; không review nghiệp vụ K2/M9.

| File dưới `src/kho_tri_thuc/ha_tang/` của frozen02 | SHA256 |
|---|---|
| `an_toan_sao_chep.py` | `d63bfd865367614d265dc07a3e86c2254923f62d592a4348eb5cbc506fef05a2` |
| `sao_chep_bang.py` | `92251dda5fe263cc819ad6c204a7a1bd5ef67a053616d26e3a2e14e72d3031db` |
| `ket_noi.py` | `a18d02e6370dcede8a7c4506e919c1c4df5643c9ad0c03dce9f812970452341d` |
| `database.py` | `0e7db1d4ac499dcd620a7a23d3e08b91efd42a5cbeb9529047db5b28bf886c57` |
| `dich_sqlite_pg.py` | `c8446c7a9d45dba9856e5ba9280063577956e058f699f247d9438692070be386` |
| `feature_migrations.py` | `04737a323e286ca3507011130b069e3857a7d1dfccf3395a9b6e989ee6dc05b4` |

## 2. F4 / P1 — actual PG rowid bị bỏ và cùng oracle che mất khác biệt

**Điểm cần sửa:** `sao_chep_bang.py:243–248,303–325`; nguồn alias tại `an_toan_sao_chep.py:59–64,81–83`. Đây là yêu cầu F4 còn thiếu, không khẳng định mất rowid chỉ mới sinh ở02.

DDL SQLite `database.py:38–43,50–56` có `issues`, `audit_events`, `evidence` với `id INTEGER PRIMARY KEY`; SQLite dùng id làm alias rowid. Translator `dich_sqlite_pg.py:171–177` đổi id thành identity PK **và** `:190–196` thêm một cột rowid identity riêng. Không có CHECK id=rowid hoặc trigger đồng bộ hai cột trong DDL/feature migrations/translator đã kiểm. Do đó physical PG schema hợp lệ không bảo đảm hai giá trị bằng nhau.

**Counterexample static:** nguồn PG hiện hành, history/DDL chuẩn, hai dòng DEMO hợp lệ của `audit_events` có `(id,rowid)=(100,7)` và `(1,8)`; các trường bắt buộc hợp lệ, optional attempt_id NULL. Không cần schema drift hoặc FK hỏng. Cặp identity độc lập cho phép trạng thái này; chưa chạy INSERT hay backup để dựng nó.

- Bộ chép `:313` đọc actual rowid7/8 và các cột, nhưng `:315` bỏ phần tử đầu khi int_pk_alias. SQLite nhận id100/1 và buộc rowid100/1. Vì thế ORDER BY actual rowid của nguồn cho dòng100 trước1; SQLite cho dòng1 trước100.
- Fingerprint PG `:247–248` lại dùng **id** làm khóa canonical và ORDER BY id. SQLite fingerprint `:258` dùng rowid (=id); cả hai cùng hash khóa1/100 và cùng values. Đối chiếu `:322` không phát hiện actual PG7/8 đã mất, nên đường source cho phép commit `:325` và caller có thể publish backup như đã verify.
- `KetNoiPG.mo_nguon_sao_luu:249–264` gọi utility `kiem_nguon_sao_luu:328–346` chỉ kiểm history shape/checksum/current version, không kiểm alignment alias. Đường PG→SQLite không có guard khác chứng minh invariant đó. Việc report02 gọi actual hidden rowid PG của bảng INTEGER PK “không biểu diễn được” không thay thế safe refusal.

**Sửa hữu hạn cần có:** trong cùng authoritative PG snapshot, từ chối có mã business nếu bất kỳ bảng alias nào có actual PG rowid khác alias, trước SQLite commit/publish; hoặc cung cấp format bảo toàn thật cả hai nếu được thống nhất. Không bỏ actual rowid khỏi oracle để coi khác biệt là đạt. Không cần xây engine/đổi schema nguồn.

**Controls sau khi được root cấp runtime:** positive alias-aligned; negative hai dòng trên và từng nhóm alias thực; source nguyên trước/sau, không publish success, partial/evidence trung thực; hidden-rowid non-alias và int64/NULL/0 positives vẫn giữ. Oracle độc lập phải quan sát actual PG rowid riêng, không tái dùng chính lựa chọn alias của product làm expected. Đây là blocker preservation, chưa phải test FAIL đã chạy.

## 3. R1 — sửa physical/namespace admission có cơ sở tĩnh, positive vẫn chờ PG

- Utility `:127–185,195–203` đã mở catalog contract từ tên cột sang relation/column type+typmod/null/default/identity/generated/collation, constraint/index/trigger/rule/policy, function/operator/type/sequence và namespace inventory. `_kiem_schema_migrations:254–274` kiểm shape/PK/trigger/rule/RLS **trước** đọc lịch sử; `_lich_su:90–104` nhận list và phát hiện trùng. Function/type/operator-only không còn đường “trống” theo phần namespace inventory này.
- Reference `:209–231` dùng trusted migration path `ket_noi:184–211` trong schema `ktt_ref_*` riêng, force-rollback; không bootstrap target trước guard. Cache key `(server_version,version)` và chuẩn hóa catalog cần actual PG positive xác nhận; hash/history một mình không còn là proof physical. Cold cache cần CREATE trên database, có business refusal nếu thiếu — ordinary-role compatibility chưa được nhận đạt.
- SQLite→PG `sao_chep_bang:153–156` giữ transaction/ordered table exclusion, rồi classifier trước seed DELETE/COPY. Constructor autoload `ket_noi:273–280,291–296` gọi admission trước `_migrate`; absent/truly-empty được phép, các target khác dựa classifier. Restore `:511–532` dùng repeatable-read/force-rollback classifier trước caller publish; preflight nay có reference DDL hoàn tác nên không còn là READ ONLY toàn transaction.
- Normal non-autoload `_migrate:395–432` giữ checksum/history và early return current; extraction sang `ap_dung_migration` giữ BOOT_STRAP/operators/migration statements theo diff, không áp classifier mới vào mọi normal upgrade. Chưa thấy thêm P1 cụ thể cho hai call path này trong scope đọc; không suy schema/permission/current-positive/race đã PASS.

## 4. R2 — kế hoạch sequence và transaction đã đổi đúng hướng source

`sao_chep_bang:86–125` lập toàn identity plan từ source snapshot trước seed/COPY: rowid bắt buộc, ownership dependency, source integer, positive increment, min/max/int64, quyền owner và dự kiến marker. Vì phép cộng là Python integer, source documents.rowid=BIGINT_MAX đi refusal `PG_SEQUENCE_TRAN` trước effects, thay vì overflow SQL muộn như01.

`_dat_sequence:128–133` thay các setval liên tiếp bằng `ALTER SEQUENCE … RESTART`; tất cả nằm trong PG transaction `:153–191`, sau FK và canonical compare. Không thấy setval còn trong đường copy được review. Đây là implementation của cơ chế transactional đã yêu cầu, **chưa là proof runtime rollback**. Cần actual PG đo mọi last_value/is_called trước/sau fault muộn, privileges/ownership và next identity positive; không lấy only-row rollback hoặc preflight làm đủ.

PG→SQLite vẫn BEGIN IMMEDIATE trước target classifier và defer FK trong transaction `:295–299`; source repeatable-read cùng content check `:300–324`, callback `:330–331` còn trong cùng source snapshot. Điều này có cơ sở để xử lý writer giữa copy/verify, nhưng không giải quyết F4 alias ở trên. Snapshot/lock/late-error/sequence rollback/normal-upgrade positives vẫn NOT_VERIFIED bởi reviewer này.

## 5. Quyết định và giới hạn

**Giữ blocker F4/P1; chưa nghiệm thu backup/V13.** R1/R2 có sửa source hợp lý nhưng cần independent candidate-bound controls; không mark closed runtime. Tests/report/CLI publication do review chuyên trách/root xử lý; báo cáo này không chứng nhận test-safety, actual child races/CLI, full49 acceptance, ordinary role, GUI/K2/DR hoặc bất kỳ nghiệp vụ M9. Không sửa source/expected/probes để hợp output; input hashes được giữ nguyên.
