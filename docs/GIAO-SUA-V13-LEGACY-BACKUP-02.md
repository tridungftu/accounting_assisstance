# Giao sửa V13 — an toàn copy và sao lưu legacy, 02

**19/10/2026 — READY_FOR_ROOT_DISPATCH; chưa nghiệm thu.** Cùng session Claude `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`. Đây là vòng sửa hữu hạn theo review của candidate01, không mở lại kiến trúc. **M9 chỉ xác định cách lấy JSON+Excel từ ứng dụng vay hiện có; không sửa M9, nguồn, schema, service, UI hoặc xây lại tracking/tính vay.** Phần mềm #10 quản lý kho thuộc M5, không phải M10 đóng sổ; cũng không thuộc vòng sửa này.

## 1. Đầu vào đã kiểm và phạm vi

Candidate01 terminal79641/exit0, frozen146 manifest SHA256 `da3f41f317efebd3d00246b9ec845b2ff612743c8176f7f4c81fc3256fd75e72`. Root đã đọc đủ sáu file code/test thay đổi và báo cáo01, kiểm 0 file ngoài whitelist/0 thiếu/0 xóa. Claude chưa chạy được test: Git Bash bị Windows từ chối MSYS named object trước Python. Root chạy native Python trên frozen được **7/7 unit component SQLite**, có ba fake-PG tests; không phải PG end-to-end hoặc acceptance. Lỗi setup/shell không được gọi là test sản phẩm FAIL/PASS.

Đọc toàn các review mới:

- `REVIEW-V13-BACKUP-SAFETY-01.md`, SHA `3a06f42b37e87da3d5ad0de5fc041a3c8fb6e05f6a91c373865aef3945cb585c` — R1/R2, hai P1.
- `REVIEW-V13-BACKUP-CLI-TESTS-01.md`, SHA `aaee82f575bd1fa0652609380108f63cb827d96fc66228f7aa6fcc05efa365d2` — F1–F7.
- Đầu bài01 và các gate/review legacy/PG/SQLite/import đã chỉ định vẫn là căn cứ; giữ các positive, locks và refusal codes đã có. Baseline độc lập trước01 là SQLite10PASS, PG4positivePASS/6nonempty-refusalFAIL; không dùng số cũ để nhận candidate mới đạt.

**Chỉ bảy write targets:** `src/kho_tri_thuc/ha_tang/an_toan_sao_chep.py`, `sao_chep_bang.py`, `ket_noi.py` (cùng thư mục); `tools/sao_luu_pg.py`; `tests/test_v13_backup_safety.py`; `tests/test_v13_backup_safety_pg.py`; **báo cáo mới** `docs/BAO-CAO-V13-LEGACY-BACKUP-02.md`. Báo cáo01 và reviews giữ nguyên. `ket_noi.py` chỉ sửa admission/autoload/restore/preflight/readonly backup open cần thiết, giữ normal supported upgrade và migration statements/checksums. Không sửa `database.py`, `feature_migrations.py`, `postgres.py`, `pg_migrations.py`, `k2/`, nguồn nghiệp vụ/CRM/M9, launcher/config/dependencies/real store, source apps, public ledgers hoặc independent probes. Nếu cần ngoài whitelist, báo exact dependency, không tự mở rộng.

## 2. Sửa P1 guard/schema và rollback

**R1 — physical contract trước effects.** Shared guard PG hiện chỉ tên cột/rowid identity và dict history nên chưa đủ. Phải kiểm expected legacy physical schema: types/typmods, nullability/defaults/identity mode, PK/FK/UNIQUE/CHECK/indexes/required triggers và inventory objects/functions/types/operators cùng dependencies hợp lệ. Kiểm cả `schema_migrations` shape `(version bigint PK, checksum text NOT NULL, applied_at text NOT NULL)` và uniqueness; không để dict collapse che duplicate. Tiền `documents.amount_minor` phải BIGINT, không cho double precision nhận int64 rồi mất một đơn vị. Không coi schema chỉ có function/type/operator là hoàn toàn trống; không chạy bootstrap thay object lạ. Unknown/partial/drift reject trước constructor `_migrate`/bootstrap, trước thay seed/COPY/identity/sequence hoặc restore publish. Contract phải dựa trên trusted DDL/metadata được review, không caller flag/hash tự chứng nhận hoặc tạo reference objects trong chính target trước guard. Không tự sửa schema lạ trong đường copy.

Giữ absent namespace hoặc truly empty namespace positive theo authority/locking đã chứng minh. Inventory phải phân biệt objects do PG tự tạo phụ thuộc expected objects với user objects lạ; không reject canonical fresh vì auto objects. Không mở scope sang K2. Nếu cần metadata reference generated từ DDL, nêu cách tạo, version, authority, ownership và test drift; tránh nhiều nguồn quy tắc mâu thuẫn. Canonical validation dùng typed content gồm actual rowid sau copy, không chỉ row count.

**R2 — sequence rollback thật.** Các `setval` liên tiếp không rollback theo data transaction. Lập toàn sequence plan trước effects: bounds/exhaustion, identity ownership, privileges và next/is_called semantics. Source hợp lệ với hidden `documents.rowid=9223372036854775807` phải bị từ chối an toàn; lỗi sequence muộn không được để các sequence trước đó đổi sau rollback. Dùng cơ chế transactional được chứng minh hoặc protocol bảo toàn thực sự mọi lỗi muộn; preflight một mình hay compensation best-effort không đủ. PostgreSQL16 [ALTER SEQUENCE RESTART](https://www.postgresql.org/docs/16/sql-altersequence.html) có transactional semantics nhưng cần owner và khác `setval`; kiểm đúng quyền/call path, không phá đường được hỗ trợ hoặc đổi identity mode. Đo toàn sequence `last_value/is_called` trước/sau lỗi, không chỉ sequence cuối/data rows.

Giữ một transaction + actual ordered table write exclusion, cả hai advisory locks và SQLite BEGIN IMMEDIATE hiện có. Không commit transaction của caller, không thay FK-mode để né validation. Constructor autoload phải admission trước migration; normal upgrade không autoload vẫn hoạt động. Mã refusal đã bind: nonempty `PG_NAP_DO`, older fresh `PG_DICH_SCHEMA_CU`, marker/nonempty `PG_KHO_SQLITE_CON`, unknown/drift có mã business rõ; không dùng lỗi driver/auth/timeout làm proof từ chối đúng.

## 3. CLI: snapshot, source, parity và publish

**F3/F5:** backup source phải current-compatible/read-only preflight trước mọi normal migrate, không nâng schema nguồn vì `tao_moi=False`. Giữ normal upgrade bên ngoài backup. Copy và independent content verify phải cùng authoritative source snapshot hoặc exclusion xuyên cả hai; writer commit hợp lệ giữa hai thời điểm không được làm một snapshot backup đúng thành `BACKUP_VERIFY`. Phải kiểm nội dung thực, không bỏ verify để né race.

**F4:** canonical parity phải gồm actual hidden/alias rowid với type/value rõ, cùng data/column contract. ORDER BY rowid không chứng minh giá trị rowid. Control thay rowid giữ nguyên thứ tự/content phải bị phát hiện; positive int64 >2^53, NULL và0 phải giữ đúng.

**F2:** chuẩn bị và verify checksum trước publish; chọn publish protocol trên Windows giữ đúng trạng thái DB+SHA cả khi lỗi giữa các bước. Không báo partial được giữ nếu partial đã rename/mất. Nếu final mới đã hiện diện một phần, failure receipt phải trung thực về exact artifacts còn lại và không báo backup thành công; ưu tiên publication atomic của owned bundle nếu giữ compatibility được. Không xóa/ghi đè/di chuyển bất kỳ backup/partial cũ để rollback hoặc rotate. Hai lần cùng phút unique/exclusive, `--giu` vẫn báo retention không áp dụng. Giữ nhãn LEGACY_DB_FALLBACK, không coi DB-only là full artifact/K2 backup. Lỗi trả sanitized code, không DSN/rows/traceback. Fault sau publish đầu/trước hoàn tất checksum cũng phải có control, không chỉ fault trước copy.

## 4. Sửa fixture/test trước khi chạy và bằng chứng cần có

**F1:** PG tests phải tự chứa config DEMO. Frozen không có `cau_hinh.toml`; không đọc config đang vận hành. Không dùng `Store.ingest()` trong setup vì unchanged `write_immutable` gọi temporary.unlink dưới guard. Tạo new DEMO config bytes, raw fixture exclusive và direct legacy SQL seed rõ ràng, retained paths; chứng minh raw/config/data không rỗng. Đây là fixture setup, không tuyên bố đã test ingest workflow. Không sửa Store/guard hoặc tắt no-delete để có test xanh. Có thể đọc các legacy config/Store definitions đã cho phép; không đọc var/.env/raw thật.

**F7:** không đặt DSN/password/raw output/actor exception vào assertion args hay error message; `assertNotIn(secret, output)` có thể tự in secret khi fail. Dùng predicate boolean và message hằng, sanitized code/class/sqlstate. Test failure cũng phải không làm lộ credential; không dump env/locals/traceback.

Tự kiểm bằng đúng hai lệnh đã cấp, không tự chạy suite khác:

```text
python -X utf8 -m unittest discover -s tests -p test_v13_backup_safety.py
python -X utf8 var/codex-dieu-phoi/run-pg-tests-retained.py test_v13_backup_safety_pg.py
```

Root cấp system Python3.13/guard/no-bytecode và `PYTHONPATH=src;var/codex-dieu-phoi/runtime-deps`. Retained runner giữ credential local process/redact output; chỉ execute exact command, không Read runner/var/.env. Chỉ tạo new retained `kho_test_*` DB/schema và direct legacy KetNoiPG; explicit DSN resolver key. `postgres`/`pg_migrations` imports definitions-only được review, cấm connect/migrate/integrity/K2 business SQL. Không drop/cleanup file/DB/role, không sửa guard. Git Bash ngoài filesystem sandbox đã được root chẩn đoán chạy được; quyền thực thi task do root dispatch, không tự đổi shell/policy.

Controls bắt buộc trong scope:

- Giữ actual StorePG→backup→verify→restore fresh PG config→StorePG reopen và original SQLite typed49/raw/config equality. Exact generated marker exempt riêng; history versions/checksums kiểm riêng. Không suy empty tables chứng minh đầy đủ49nonempty.
- Existing nonempty/changed seed/extra inventory, old fresh/old nonempty/partial, float-money/history malformed+duplicate/missing required constraints/extra mutating trigger/function-only và type/operator-only: refusal đúng, schema/history/data/identity/all-sequences nguyên trước/sau, function definition lạ không bị thay. Các damaged fixture tạo riêng, không sửa/reset target cũ.
- Positive sequence next identity, int64/NULL/0 và failure BIGINT_MAX/later-sequence fault đo full state. Thêm rowid parity negative và source-old backup refusal/source unchanged.
- Causal writer giữa copy/verify chứng minh consistent snapshot. Concurrency selftests cần exact blocker PID/relation/mode và full49+exact writer-row oracle; monkeypatch barrier/inprocess CLI nếu còn dùng phải ghi đúng giới hạn, không gọi đó là proof actual child/races độc lập. Root sẽ chạy riêng actual races/CLI khi terminal và review xong; không sửa independent probes/expected.
- CLI same-minute unique/new exclusive outputs, old backups/partials unchanged, actual content+rowid/sha match, retained failure artifacts/receipt đúng ở copy/verify/publish fault. Không nhận skipped/setup/driver failure là đạt. Giữ mọi failed attempt/evidence.

## 5. Bàn giao

Sửa các finding thực, chạy selftests đã cấp khi fixture an toàn, báo rõ PASS/FAIL/UNRUN/skip và receipt path kỹ thuật/số tổng hợp trong báo cáo02. Nêu exact files và hạn chế ordinary role/full49/race/CLI/fullK2/GUI, không tự nghiệm thu toàn V13 hoặc33. Sau báo cáo, kết thúc CLI để root freeze toàn source, review độc lập, bind actual APIs và run candidate-bound probes; không tự bắt đầu cutoff/M5/M9. Không commit/reset/clean/xóa file, không Google/cloud/real approval/CFO_NTD. Kho thật tiếp tục SQLite; chỉ DEMO/MO_PHONG_.
