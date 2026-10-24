# Review độc lập bằng chứng backup SQLite V13 — 01

**19/10/2026 — EVIDENCE_REVIEW / SELECTED_LEGACY_SQLITE_ONLY / NO_REEXECUTION.** Tôi không viết product/probe này; đã đọc toàn probe02 và release/pins/result, đối chiếu source legacy được pin. Root đã chạy một lượt retained DEMO; review này chỉ đọc code/evidence, không mở DB/raw/config, không import/chạy test/SQL/HTTP/host/source app hoặc sửa product. **M9 vẫn STOP**.

## Byte binding và phạm vi lượt chạy

| Artifact | SHA256 |
|---|---|
| `var/codex-dieu-phoi/v13-backup-independent01/probe_sqlite_backup02.py` | `c992906cbfeeb090da305f1fd8bf74c0453fd8324065ab8620895c19eff1b22b` |
| Cùng thư mục `source-pins.json` | `70958ecbfbd187c9a135db72080c7ecd771194f76c5f77aa0eacc58edc5f96f4` |
| `release-root-20261019-113909-009.json` | `5d4a595893fff18dcf5dde72622d16811a89d5ca91d51d27b9d49ddd8a800d95` |
| `runs/run-root-20261019-113909-006/result.json` | `af4cc67617fb471d757a3c4d46c81e97e21cabf98795664984c28cf84cd13716` |

Root release chỉ standalone SQLite, pin probe02/pins/guard `a517c5359ceada062900edd34280d4dc7daa2a001d5e05c84a9eae174813a229`; PG/HTTP/host/M9/source-app/cleanup đều false. `authorize:57–93` kiểm release/root-review/guard/no-bytecode/fresh run/pins trước product import và tạo run. README01/02 cùng false `release.json` là preparation artifacts lịch sử, không phải release vừa chạy. Có sửa lỗi binding tên guard từ probe01 sang02; đây là harness setup correction, không product backup failure.

Đối chiếu độc lập **13/13 selected source files** (4 primary +9 dependency/package pins): current hashes=frozen hashes=source-pins và từng entry manifest143 SHA `19c3476cb01fde17ec0382c16c3537813cec804b725e1bcd6eb730e5db8da276`; không đọc/chạy M9 modules hoặc coi toàn143files đã được review. Result liệt kê12 imported legacy modules từ frozen allowlist, không `postgres`/`pg_migrations`/M9; SQLite restore preflight `ket_noi.py:481–482` trả sớm trước DSN/PG import. Python3.13/guard là run context root cung cấp; probe không ghi đủ interpreter/OS inventory để suy thêm host acceptance.

## Kết quả thực và oracle

Result có đúng **10 probe criteria B01–B10: 10 PASS,0 FAIL,0 NOT_RUN**, không có `setup_or_harness_error`; không lấy exit0 hoặc status self-report đơn lẻ làm kết luận. Các IDs này **khác scope** contract B01–B08 trong `V13-CONG-SAO-LUU-PHUC-HOI-33.md` SHA `21d788594719437b1d31a44695beac22ec56644e8c7eb1c7f53a53f5dc6554e0`.

- **Probe B01–B03:** `seed:149–177` tạo3 DEMO BANK/JOURNAL/INVOICE, int64 `9007199254740993`,0,NULL, raw/config/audit/knowledge; đây là SQL fixture setup, **không ingest/parser/approval workflow**. `:230–247` gọi thật `create_backup→verify_backup→restore_backup`, mở lại thật `Store`, kiểm status3kinds/config BLOB/raw. Source `backup.py:55–83,120–147` đúng là backup SQLite nhất quán, verify manifest/raw/integrity và publish vào new destination.
- **Independent content oracle:** `snapshot:117–130` kiểm exact table set **49 application +schema_migrations**, actual typed cells/implicit rowid/column definitions/schema SQL/application_id/user_version; NULL/int/text/BLOB/REAL được tag riêng, không gọi product hash helper hoặc tin copied content_hash. Snapshot copy và restored sau Store-open phải bằng initial toàn bộ; history exact, không marker/timestamp exemption. Result before/after có50 table hashes,0 mismatch. **13 nonempty là trên50tables =12/49 application +schema history20rows;37application tables rỗng.** Không ghi “49 bảng đều nonempty” hoặc “mọi branch đã thử”.
- **Probe B04:** so canonical source/schema/history, raw tree, original good bundle và selected source bytes sau các thao tác; result giữ bằng nhau. Main/WAL/SHM hashes bằng tại hai observed boundaries **trước source connection close**. `finally:283–286` đóng connection sau boundary: đây không chứng minh toàn vòng đời native SQLite không tạo/xóa sidecars, không thay bằng một listing sau cùng hoặc tuyên no-delete toàn OS.
- **Probe B05–B10:** negative có expected error cụ thể và preservation predicate, không “bất kỳ exception là PASS”. Raw được seed **chưa từng tạo**→FileNotFoundError/no final backup/source canonical giữ; existing backup và restored folder→DESTINATION_EXISTS/old tree giữ; separate new truncated DB và raw-length manifest tamper→BACKUP_CHECKSUM; new traversal manifest→UNSAFE_BACKUP_PATH/no escape file. Good bundle giữ bytes. Failed partials được giữ; không dùng xóa raw, cleanup hoặc owner reset để tạo ca âm. Chưa thử mọi manifest/version/symlink/race/fault branch.

## Quyết định review và giới hạn còn lại

**Chấp nhận bằng chứng của 10 selected standalone legacy SQLite probe criteria trong lượt này; không có blocker làm vô hiệu kết quả ấy.** Đây là tiến bộ runtime có thật so với chỉ chuẩn bị contract. Không đóng trọn contract B01: chưa có NT/proposal/published file và ingest/approval/use-after-restore workflow đại diện; không có full nonempty coverage. Không suy precision parser/Excel/UI từ storage roundtrip int64.

Legacy PG fallback/copy-target all49/exactseed/identity-sequence-before-DML guards ở cả hai chiều, concurrent target/source consistency, full typed K2/archive/artifact/proof/role/RLS/encryption recovery, app ordinary-role behavior, GUI/OS restart/DR vẫn **NOT_RUN/NOT_VERIFIED theo gate tương ứng**. Selected unchanged legacy bytes nằm trong handoff mang tên M9 không cấp quyền resume M9 hoặc chứng minh dữ liệu/module M9 đã backup được. Kho thật vẫn SQLite; không có vận hành Junsky/duyệt thật hoặc full V13 acceptance. Probe/pins/release/result hashes được kiểm lại trước bàn giao, giữ nguyên inputs và mọi attempts/artifacts.
