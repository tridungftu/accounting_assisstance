# BÁO CÁO V13 — an toàn chép/sao lưu legacy, 01

Ngày 19/10/2026. Thực hiện `docs/GIAO-SUA-V13-LEGACY-BACKUP-01.md` (SHA `23942877…a2ae` theo lệnh root). Đã đọc các review được chỉ định:
`REVIEW-V13-PG-BACKUP-01.md`, `REVIEW-V13-LEGACY-HANDOFF-01.md` (R1/R2 + closure), `REVIEW-V13-SQLITE-BACKUP-01.md`, `REVIEW-V13-IMPORT-BOUNDARY-01.md`.
M9 repair02 cũ bỏ hoàn toàn; không đụng schema/nguồn/service/UI M9 hay common M9. **Không tự nghiệm thu V13**; chờ Codex freeze/review/run độc lập.

> **Trạng thái kiểm thử: CHƯA CHẠY ĐƯỢC.** Cả hai lệnh tự kiểm được cấp đều không khởi chạy được vì công cụ shell của phiên (Git Bash) lỗi ngay khi khởi động:
> `bash.exe: *** fatal error - NtCreateDirectoryObject(\BaseNamedObjects\msys-2.0S5-…): 0xC0000022` (exit 66), lặp lại 5 lần, kể cả lệnh unittest không-PG.
> Đây là lỗi môi trường tiến trình shell (quyền tạo named object), không phải kết quả test. Tôi không vượt sandbox hay dùng shell khác.
> Vì vậy: **0 test chạy, 0 pass, 0 fail — toàn bộ UNRUN.** Mã và test chỉ được rà tĩnh. Root/Codex cần chạy:
> ```
> python -X utf8 -m unittest discover -s tests -p test_v13_backup_safety.py
> python -X utf8 var/codex-dieu-phoi/run-pg-tests-retained.py test_v13_backup_safety_pg.py
> ```

## 1. File thay đổi (đúng whitelist, 7 file)

| File | Thay đổi |
|---|---|
| `src/kho_tri_thuc/ha_tang/an_toan_sao_chep.py` (mới) | Nguồn quy tắc duy nhất "đích mới tương thích" (tránh circular import). Hợp đồng dựng từ `database.MIGRATIONS` trên SQLite `:memory:`: 49 bảng theo thứ tự tạo, cột theo thứ tự, đối tượng schema SQLite nguyên văn, checksum lịch sử, seed (hiện chỉ `knowledge_epoch=(1,'initial')`). `phan_loai_pg` / `phan_loai_sqlite` → `VANG_MAT / TRONG_HOAN_TOAN / MOI_KHOP / CO_DU_LIEU / CU / KHONG_TUONG_THICH`; `tu_choi_neu_khong_moi` → mã nghiệp vụ. |
| `src/kho_tri_thuc/ha_tang/sao_chep_bang.py` | Hai entrypoint chép dùng guard chung; `bang_theo_thu_tu` lấy từ hợp đồng chung. |
| `src/kho_tri_thuc/ha_tang/ket_noi.py` | Admission trước `_migrate` khi có autoload; `_nap_neu_can` bỏ sentinel, mở nguồn chỉ-đọc; `_trang_thai_schema` dùng phân loại chung (giữ chữ ký `(dấu, có dữ liệu)` để `kiem_dich_phuc_hoi`/test cũ dùng tiếp). |
| `tools/sao_luu_pg.py` | CLI backup legacy viết lại an toàn. |
| `tests/test_v13_backup_safety.py` (mới) | Test không-PG. |
| `tests/test_v13_backup_safety_pg.py` (mới) | Test PG trên DB `kho_test_v13_*` mới, giữ lại. |
| `docs/BAO-CAO-V13-LEGACY-BACKUP-01.md` | Báo cáo này. |

Không sửa `pg_migrations.py`, `postgres.py`, `database.py`, `feature_migrations.py`, `backup.py`, `store.py`, `k2/`, `nguon/vay_9.py`, CRM, launcher/config/dependencies, source app, CHANGELOG/hàng đợi/coverage, review/probe.

## 2. Hiện thực theo "Sửa bắt buộc"

**(1) Guard toàn đích, hai chiều.** Đích chỉ được nhận khi:
- đúng 49 bảng ứng dụng + `schema_migrations`;
- không có relation lạ (bảng/view/matview/foreign/sequence không thuộc identity);
- cột từng bảng đúng thứ tự hợp đồng, PG có cột `rowid` identity;
- lịch sử liên tục và đúng checksum từng version;
- dữ liệu đúng nguyên văn seed.

Các ca từ chối:
- Bất kỳ dòng ngoài seed (cash-only, knowledge-only, dòng thêm), seed bị đổi hoặc bị xóa, bảng lạ có dòng → `CO_DU_LIEU` → mã legacy `PG_NAP_DO`; PG có dấu nạp → `PG_KHO_SQLITE_CON` qua `quyet_dinh_nap`.
- Schema cũ không dữ liệu → `PG_DICH_SCHEMA_CU` / `SQLITE_DICH_SCHEMA_CU`.
- Dở dang/lạ/lịch sử sai/tương lai/cột lệch → `PG_DICH_KHONG_TUONG_THICH` / `SQLITE_DICH_KHONG_TUONG_THICH`.

Không dùng sentinel `workspace_meta/attempts` hay "một bảng rỗng". Khi so dữ liệu, `schema_migrations` được coi là metadata, không phải bảng nghiệp vụ.

**(2) Guard trước mọi thay đổi, chặn writer thật.**
- **SQLite→PG:** gói trong **một giao dịch**, theo thứ tự:
  1. `pg_advisory_xact_lock(hashtext('mo-kho:'+schema))`;
  2. `pg_advisory_xact_lock(hashtext(schema))` — đúng khóa mà `BEGIN IMMEDIATE` legacy dùng;
  3. `LOCK TABLE … IN EXCLUSIVE MODE` các bảng đang có, theo thứ tự cố định (`schema_migrations`, 49 bảng, bảng lạ). Khóa này chặn INSERT/UPDATE/DELETE thô, vẫn cho đọc, và giữ đến COMMIT;
  4. guard;
  5. `SET CONSTRAINTS ALL DEFERRED`;
  6. chỉ xóa đúng dòng seed đã kiểm (để nguồn mang `knowledge_epoch` của nó);
  7. COPY với `rowid` — **bỏ hẳn ALTER identity**, dựa vào việc COPY FROM ghi giá trị identity được cung cấp;
  8. dấu nạp bằng `INSERT … OVERRIDING SYSTEM VALUE`;
  9. `SET CONSTRAINTS ALL IMMEDIATE`;
  10. `setval`;
  11. COMMIT.

  Đích bị từ chối không trải qua bước ghi nào, nên không có hiệu ứng trung gian cần "hoàn tác về cùng hash". Nếu kết nối đích đang trong giao dịch của người gọi → `ACTIVE_TRANSACTION`, không commit hộ. Khóa `mo-kho` dạng xact lồng được với khóa phiên của constructor (cùng session) và tự nhả khi giao dịch kết thúc, nên không lệch số lần unlock.
- **PG→SQLite:** `BEGIN IMMEDIATE` ở đích, rồi guard; chỉ sau khi qua guard mới mở ảnh chụp PG `REPEATABLE READ READ ONLY`. **Không đổi `PRAGMA foreign_keys`** — dùng `defer_foreign_keys` trong giao dịch và `foreign_key_check` trước COMMIT. Đích bị từ chối giữ nguyên dữ liệu và PRAGMA.

**(3) Restore/open thật.**
- Constructor `KetNoiPG`: khi có `kho.sqlite` để autoload, admission chạy dưới khóa `mo-kho` **trước `_migrate`**. Chỉ nhận đích vắng mặt, schema rỗng hoàn toàn (không relation), hoặc schema hiện hành mới đúng seed. Schema cũ/dở/lạ/có dữ liệu bị từ chối trước mọi thay đổi schema/lịch sử. Khi không autoload, nâng cấp bình thường giữ nguyên.
- Sau init, bộ chép kiểm lại dưới khóa writer — đây là late revalidation.
- Preflight restore (`kiem_dich_phuc_hoi` → `_trang_thai_schema`) chạy trước khi `restore_backup` chép/publish, với cùng quy tắc chung, nên ca knowledge-only bị chặn trước khi publish.
- Nguồn autoload giờ mở `mode=ro` (không migrate/sửa tệp nguồn); đổi tên sau khi nạp thành công giữ như cũ.

**(4) CLI backup** (`tools/sao_luu_pg.py`):
- Tên duy nhất `<schema>-YYYYmmdd-HHMMSS-<12hex>.sqlite`; staging `.partial-<uuid>` tạo độc quyền (`open(...,'xb')`); `.sha256` tạo bằng `'x'`.
- Bỏ unlink sidecar và bỏ move/xoay vòng bản cũ. `--giu` vẫn nhận để tương thích nhưng báo rõ `ap_dung: false`.
- Trước khi công bố: integrity + đối chiếu nội dung/cột **tái tính hai phía** (`doi_chieu_noi_dung` trên ảnh chụp PG READ ONLY so với tệp vừa chép), không chỉ số đếm. Sau đó `wal_checkpoint(TRUNCATE)` + `journal_mode=DELETE` để tệp tự chứa — SQLite tự xử lý WAL của nó, công cụ không unlink.
- Lỗi: giữ partial, in JSON đã làm sạch (`loi_sach`: mã/sqlstate, `partial_giu_lai`), exit 2.
- Nhãn `LEGACY_DB_FALLBACK`: "bản DB legacy dự phòng — không phải backup đầy đủ/K2/artifact".

**(5) Không lộ dữ liệu.** Lỗi chỉ mang mã/sqlstate/số đếm. Test đặt DSN của runner vào khóa resolver riêng `KTT_V13_BACKUP_TEST_DSN` trong tiến trình (không fallback `.env`), và kiểm rằng DSN không xuất hiện trong output CLI.

## 3. Test đã viết (UNRUN — xem đầu báo cáo)

`test_v13_backup_safety.py` (không PG):
- Hợp đồng 49 bảng + seed duy nhất.
- Phân loại SQLite:
  - mới → nhận;
  - cash-only, knowledge-only, seed đổi, seed xóa, dòng thêm, dấu nạp → `PG_NAP_DO`;
  - bảng lạ → `SQLITE_DICH_KHONG_TUONG_THICH`; bảng lạ có dòng → có dữ liệu;
  - schema cũ → `SQLITE_DICH_SCHEMA_CU`.
- PG→SQLite với nguồn PG giả ghi lại mọi lệnh:
  - đích có dữ liệu bị từ chối **khi chưa có lệnh nào tới PG**; ảnh đích (bảng + PRAGMA + schema) không đổi;
  - control dương: đích mới qua guard và dừng ở bước `BEGIN` PG, seed còn nguyên;
  - đích đang trong giao dịch của người gọi → `ACTIVE_TRANSACTION`, giao dịch không bị đụng.

`test_v13_backup_safety_pg.py` (PG, DB `kho_test_v13_*` mới, mỗi ca một schema mới, giữ lại):
- **p01:** Store SQLite DEMO → StorePG (autoload) → `create_backup` → `verify_backup` → `restore_backup` vào schema vắng mặt → StorePG mở lại. So 49 bảng chuẩn tắc (rowid + giá trị) giữa hai schema PG, chỉ miễn đúng khóa dấu nạp (kiểm riêng shape `{luc, tong_dong}`); so lịch sử version/checksum; raw có trong thư mục phục hồi.
- **n01:** SQLite→PG với cash-only, knowledge-only, seed đổi, dòng thêm, dấu nạp, bảng lạ, bảng lạ có dòng, schema cũ trống/có dữ liệu → mã đúng. Ảnh trước/sau gồm relation, nội dung mọi bảng, lịch sử (kèm `applied_at`), identity, `last_value/is_called` của sequence — đều không đổi.
- **n02:** giao dịch người gọi bị tôn trọng; control dương chép đủ; `rowid` vẫn identity `ALWAYS` (không ALTER); sequence đặt đúng (INSERT mới không trùng).
- **n03:** PG→SQLite với các ca âm (bảng + PRAGMA không đổi) và control dương (`foreign_keys` vẫn 1).
- **n04:** constructor autoload:
  - đích hiện hành có cash/knowledge → `PG_NAP_DO`;
  - đích cũ trống → `PG_DICH_SCHEMA_CU`; đích cũ có dữ liệu → `PG_NAP_DO`;
  - đích dở dang → `PG_DICH_KHONG_TUONG_THICH`;
  - ảnh schema không đổi (không migrate) và hash tệp nguồn không đổi;
  - counterpart: đích cũ không autoload nâng cấp lên hiện hành; đích vắng mặt + autoload nạp được.
- **n05:** preflight restore knowledge-only/cash-only → `PG_NAP_DO`, không có thư mục đích hay staging. Late open: preflight qua, sau đó đối thủ tạo schema và ghi → `Store(...)` → `PG_NAP_DO`; schema và `kho.sqlite` không đổi.
- **n06:** race với actor 2 thật — DML thô qua psycopg riêng, và writer legacy `KetNoiPG` mở trước (`BEGIN IMMEDIATE` + INSERT/COMMIT). Barrier đặt sau guard bằng cách bọc `tu_choi_neu_khong_moi`; test chờ `pg_stat_activity` của actor 2 báo `wait_event_type=Lock` (`relation` / `advisory`), rồi mới để chép đi tiếp. Kỳ vọng: actor 2 COMMIT sau đó, dòng của nó còn sau chép, dòng nguồn có đủ.
- **n07:** writer commit trước admission → chép bị từ chối `PG_NAP_DO`, ảnh không đổi.
- **n08:** CLI chạy hai lần trong cùng phút → hai tệp khác nhau, sha khớp, integrity ok. Bản cũ và partial cũ dựng sẵn giữ nguyên hash. Tiêm lỗi chép → rc 2, mã `DEMO_LOI_CHEP`, chỉ thêm tệp `.partial-*`. Tiêm lệch verify → `BACKUP_VERIFY`, partial giữ, không công bố. DSN không có trong output.

Ràng buộc test: không `postgres.connect/migrate/integrity`, không SQL K2; chỉ `KetNoiPG`, bộ chép, backup/restore, CLI, cộng psycopg trực tiếp cho setup/quan sát DEMO. Không DROP/DELETE/cleanup.

## 4. Hạn chế và điểm cần review

1. **Chưa chạy bất kỳ test nào** (lỗi khởi động shell). Có thể còn lỗi mà chỉ runtime mới lộ. Các giả định kỹ thuật cần runtime xác nhận:
   - COPY FROM ghi được `rowid GENERATED ALWAYS` mà không ALTER (theo tài liệu PG16);
   - `LOCK TABLE … EXCLUSIVE` đủ quyền với role chạy;
   - `pg_stat_activity` báo `wait_event` là `relation` / `advisory` như test kỳ vọng.
2. Hợp đồng cột PG chỉ so tên + thứ tự + identity `rowid`, chưa so kiểu/ràng buộc/chỉ mục/trigger. Inventory PG xét relation (bảng/view/matview/foreign/sequence lạ), không xét hàm/operator/kiểu. SQLite thì so nguyên văn `sqlite_master`.
3. Schema PG tồn tại nhưng **không có relation nào** được coi như vắng mặt (`TRONG_HOAN_TOAN`) và được phép tạo mới. Nếu root muốn coi đây là "dở dang", cần đổi `cho_phep`.
4. Đích PG có dữ liệu **và** dấu nạp trả `PG_KHO_SQLITE_CON` (giữ ngữ nghĩa legacy), không phải `PG_NAP_DO`.
5. Writer chạy ngoài mọi cơ chế khóa (DDL, `TRUNCATE` bởi chủ bảng…) không được certify. DML thường bị chặn bởi khóa bảng, writer legacy bị chặn bởi advisory key.
6. `tools/chep_v12_sang_pg.py` (ngoài whitelist) dùng `chep_sqlite_sang_pg` và gọi CLI với `--giu 0`. Nhánh `--lam-lai` của nó vẫn có `DROP SCHEMA` sẵn từ trước — tôi không sửa.
7. Backup DB-only không phải full artifact/K2. Full K2/roles/RLS/encryption/M9 nằm ngoài phạm vi.

## 5. Tuân thủ

Không đọc var/.env/backups/source app/dữ liệu thật; không dump env; không xóa file/temp/DB/role; không Git/reset/clean/launcher/host/Google/cloud; không K2 migration/business SQL; không sửa public ledgers/reviews/probe; không chạy suite M9/K2.
