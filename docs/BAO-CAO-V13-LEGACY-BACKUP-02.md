# BÁO CÁO V13 — an toàn chép/sao lưu legacy, 02

Ngày 19/10/2026. Thực hiện `docs/GIAO-SUA-V13-LEGACY-BACKUP-02.md` (SHA `6c1973b8…f163` theo lệnh root). Đã đọc đủ `REVIEW-V13-BACKUP-SAFETY-01.md` (R1/R2) và `REVIEW-V13-BACKUP-CLI-TESTS-01.md` (F1–F7), cùng báo cáo 01 (giữ nguyên, không sửa). **Không tự nghiệm thu V13/33**; chờ root freeze/review/chạy độc lập. M9: không làm gì (không sửa nguồn/schema/service/UI, không xây tracking/tính lãi).

## 0. Trạng thái kiểm thử (thực tế)

| Lệnh đã cấp | Kết quả |
|---|---|
| `python -X utf8 -m unittest discover -s tests -p test_v13_backup_safety.py` | **Chạy: 11 test, 11 PASS, 0 FAIL, 0 skip** (có ResourceWarning do kết nối test giữ mở — không phải lỗi). |
| `python -X utf8 var/codex-dieu-phoi/run-pg-tests-retained.py test_v13_backup_safety_pg.py` | **UNRUN** — công cụ Bash của phiên trả `Permission to use Bash with command … has been denied` cho đúng nguyên văn lệnh (thử 3 lần: có `cd` tiền tố, nguyên văn, nguyên văn ngoài sandbox). Không có test PG nào chạy; 0 pass/0 fail PG. Không thử đường vòng. |

Vì vậy mọi phần PostgreSQL (R1 hợp đồng vật lý trên catalog thật, R2 rollback sequence, chuỗi StorePG/backup/restore, race, CLI) **chỉ được rà tĩnh**; root cần chạy lệnh PG. Không suy PASS từ unit không-PG.

## 1. File thay đổi (đúng 7 file whitelist)

| File | Thay đổi |
|---|---|
| `src/kho_tri_thuc/ha_tang/an_toan_sao_chep.py` | R1: hợp đồng vật lý PG dựng từ DDL tin cậy; inventory toàn namespace; shape `schema_migrations` trước lịch sử; preflight nguồn sao lưu chỉ đọc; SQLite kiểm shape lịch sử trước khi đọc. |
| `src/kho_tri_thuc/ha_tang/sao_chep_bang.py` | R2: kế hoạch sequence trước hiệu ứng + `ALTER SEQUENCE … RESTART` trong giao dịch; đối chiếu canonical có kiểu + rowid trước COMMIT (cả hai chiều); F4 hash gồm rowid; F3 callback cùng ảnh chụp. |
| `src/kho_tri_thuc/ha_tang/ket_noi.py` | Tách `ke_hoach_migration`/`ap_dung_migration` (cùng câu lệnh + checksum, `_migrate`/`_ap_migration` gọi lại); admission/restore preflight dùng classifier mới (giao dịch luôn hoàn tác); `KetNoiPG.mo_nguon_sao_luu` (mở nguồn sao lưu không migrate). |
| `tools/sao_luu_pg.py` | F2/F3/F4/F5: nguồn chỉ đọc; chép + kiểm cùng ảnh chụp; SHA trước công bố; công bố bundle bằng một lần rename thư mục; biên nhận lỗi trung thực. |
| `tests/test_v13_backup_safety.py` | Fixture DEMO tự chứa 49 bảng (F1) + test không-PG mới. |
| `tests/test_v13_backup_safety_pg.py` | Viết lại theo fixture tự chứa, controls bắt buộc, assert không lộ bí mật (F7). |
| `docs/BAO-CAO-V13-LEGACY-BACKUP-02.md` | Báo cáo này (mới). |

Không sửa `database.py`, `feature_migrations.py`, `postgres.py`, `pg_migrations.py`, `backup.py`, `store.py`, `dich_sqlite_pg.py`, `k2/`, CRM/M9, launcher/config/dependencies, reviews/probes, báo cáo 01, ledgers.

## 2. R1 — hợp đồng vật lý PG trước mọi hiệu ứng

- **Nguồn hợp đồng (authority):** chính đường migration legacy — `ke_hoach_migration(version)` + `ap_dung_migration` (BOOT_STRAP, operator, DDL dịch; tách từ `_ap_migration`, câu lệnh/checksum không đổi). Tham chiếu dựng vào schema ngẫu nhiên `ktt_ref_<16hex>` **trong SAVEPOINT `force_rollback`** (không đụng schema đích, không để lại đối tượng; DDL PG có giao dịch). Version = version lịch sử của đích (đích cũ so với tham chiếu cũ). Cache theo (phiên bản máy chủ, version) trong tiến trình. Không cờ caller, không hash tự khai.
- **Mô tả catalog chuẩn hóa** (search_path = `pg_catalog` trong savepoint, tên schema → `@S`), so multiset (trùng cũng là lệch): relation (kind/persistence/RLS/reloptions), cột theo thứ tự (format_type+typmod, NOT NULL, default, identity mode, generated, collation), ràng buộc (định nghĩa, deferrable/validated), chỉ mục (định nghĩa, cờ), trigger (định nghĩa + `tgenabled`; trigger nội bộ FK theo tên ràng buộc, không theo OID), rule, policy, hàm/aggregate (`pg_get_functiondef`, proconfig, aggregate transfn/kiểu), operator, kiểu, sequence (tham số + cột sở hữu), collation/conversion/opclass/opfamily/ts_*/statistics/extension. Đối tượng PG tự sinh (kiểu hàng/mảng, sequence identity, trigger FK) có ở cả hai phía nên không bị coi là lạ.
- **Thứ tự phân loại** (`phan_loai_pg(raw, schema)`, chạy trong giao dịch/savepoint luôn rollback): namespace vắng → `VANG_MAT`; namespace không có BẤT KỲ đối tượng nào → `TRONG_HOAN_TOAN`; chỉ có hàm/kiểu/operator → không còn là "trống". Shape `schema_migrations` kiểm trước (bảng thường; `version bigint NOT NULL`, `checksum text NOT NULL`, `applied_at text NOT NULL`, đúng một `PRIMARY KEY (version)`, không trigger/rule/RLS) rồi mới đọc lịch sử dạng **danh sách** (`LICH_SU_TRUNG` nếu trùng). Lịch sử đúng → so catalog với tham chiếu cùng version. Dữ liệu: chỉ đọc theo cột ở bảng đúng hợp đồng; bảng lạ chỉ đếm nếu không có policy/rule. Có dòng ngoài seed → `CO_DU_LIEU`; còn lỗi/lệch → `KHONG_TUONG_THICH`; version cũ → `CU`; còn lại `MOI_KHOP`.
- **Mã đã bind giữ nguyên:** nonempty `PG_NAP_DO`; marker `PG_KHO_SQLITE_CON`; cũ trống `PG_DICH_SCHEMA_CU`; lệch/dở/lạ/chỉ hàm-kiểu-operator `PG_DICH_KHONG_TUONG_THICH`. Mới: thiếu quyền dựng tham chiếu `PG_HOP_DONG_THAM_CHIEU`; tự kiểm mâu thuẫn hằng shape `PG_HOP_DONG_MAU_THUAN`.
- **Điểm gọi:** constructor autoload (`_kiem_dich_nap`, dưới khóa mở-kho, trước `_migrate`/bootstrap — schema chỉ có `json_extract` lạ bị từ chối, bootstrap không chạy); bộ chép SQLite→PG (trong giao dịch chép, sau khóa); restore preflight (`_trang_thai_schema`, ảnh chụp REPEATABLE READ trong giao dịch luôn hoàn tác — trước đây READ ONLY, nay cần ghi tạm schema tham chiếu rồi hoàn tác).
- Bộ chép còn **đối chiếu canonical trước COMMIT** (giá trị có kiểu + rowid canonical mọi bảng, `PG_CHEP_LECH_NOI_DUNG` → hoàn tác): lớp chặn thứ hai cho mất số (vd tiền double).
- SQLite: shape `schema_migrations` so nguyên câu SQL trước khi đọc lịch sử; đối tượng so với hợp đồng ở đúng version.

## 3. R2 — sequence có rollback thật

- `_ke_hoach_sequence` lập kế hoạch cho **mọi** cột identity (rowid + cột INTEGER PRIMARY KEY) từ ảnh chụp đọc nguồn, **sau guard, trước mọi hiệu ứng**: giá trị = max nguồn + 1 (workspace_meta tính dòng dấu nạp sẽ thêm), không thấp hơn `seqmin`; vượt `seqmax`/int64 → `PG_SEQUENCE_TRAN`; bước không dương/không xác định sequence sở hữu → `PG_SEQUENCE_KE_HOACH`; không có quyền chủ sequence → `PG_SEQUENCE_QUYEN`. Nguồn hợp lệ có `documents.rowid = 9223372036854775807` bị từ chối ở đây.
- Thực thi bằng `ALTER SEQUENCE <seq> RESTART WITH v` (last_value = v, is_called = false — cùng ngữ nghĩa `setval(v,false)` cũ) **sau** COPY/FK/đối chiếu, trong cùng giao dịch; hậu kiểm giá trị kế tiếp > max thực. Không đổi identity mode, không `setval`. Lỗi muộn bất kỳ → toàn giao dịch hoàn tác. **Giả định cần chạy PG xác nhận:** RESTART có ngữ nghĩa giao dịch (tài liệu PG16 + handoff); test `n02b` đo mọi sequence trước/sau lỗi ở lần đặt thứ 6.
- Quyền: đường được hỗ trợ (role tạo schema = chủ bảng/sequence) giữ chạy; role thường không phải chủ → từ chối có mã thay vì đổi một phần.

## 4. CLI `tools/sao_luu_pg.py`

- **F5:** `KetNoiPG.mo_nguon_sao_luu` — preflight trong giao dịch `READ ONLY` luôn hoàn tác (namespace, shape lịch sử, lịch sử đúng, **đúng phiên bản hiện hành**), không bao giờ gọi `_migrate`/bootstrap. Nguồn cũ → `PG_NGUON_SCHEMA_CU`, lạ → `PG_NGUON_KHONG_TUONG_THICH`, tương lai → `FUTURE_SCHEMA`. Đường nâng cấp thường ngoài backup giữ nguyên.
- **F3:** `chep_pg_sang_sqlite(..., kiem_trong_anh_chup=cb)` gọi `cb(raw)` sau COMMIT SQLite nhưng **vẫn trong ảnh chụp REPEATABLE READ của lần chép**; CLI đối chiếu độc lập bằng kết nối SQLite chỉ đọc riêng tới tệp vừa chép. Người ghi commit giữa chép và kiểm không làm `BACKUP_VERIFY` sai.
- **F4:** fingerprint mỗi dòng = [rowid canonical có tag] + giá trị có tag (`int` bằng chuỗi chữ số đầy đủ, float `repr`, bytes hex, NULL riêng). Bảng INTEGER PRIMARY KEY: rowid canonical = cột đó (SQLite rowid là cột đó; PG so cột đó). Hạn chế: rowid ẩn PG của bảng INTEGER PK không biểu diễn được trong SQLite nên không so.
- **F2:** staging `<ten>.partial-<uuid>/` tạo độc quyền (`mkdir`); DB tạo độc quyền; chép + kiểm + integrity + checkpoint/`journal_mode=DELETE`; SHA tính, ghi độc quyền, đọc lại kiểm **trước** công bố; công bố = **một** `os.rename(staging_dir, <ten>/)` (Windows: đích tồn tại → lỗi). Không bước nào sau công bố → không có trạng thái "DB đã công bố, SHA chưa". Biên nhận lỗi: `partial_giu_lai` (chỉ khi còn tồn tại), `da_cong_bo`, `con_lai` = đúng thư mục/tệp còn trên đĩa. Không xóa/ghi đè/di chuyển bản hay partial cũ; `--giu` báo `ap_dung:false`; nhãn `LEGACY_DB_FALLBACK`.
- **Đổi bố cục output:** bản sao lưu là thư mục bundle (`thu_muc_ban`, `file = <bundle>/<ten>.sqlite`) thay vì cặp tệp phẳng. Consumer hiện có (`tools/dong_bo_dem.ps1`, `tools/chep_v12_sang_pg.py`, ngoài whitelist) chỉ dùng mã thoát/chuỗi in ra → tương thích. `chep_v12_sang_pg --lam-lai` với schema cũ nay bị CLI từ chối sao lưu (an toàn hơn: không xóa schema khi không sao lưu được). POSIX: rename thư mục vào thư mục rỗng có sẵn có thể thay thế — chỉ cam kết Windows (đã kiểm `exists` trước).

## 5. Fixture và test (F1, F6, F7)

- **Fixture tự chứa** (`tao_kho_demo`): cấu hình DEMO viết mới (`[app] entity_id = "DEMO_V13_FIXTURE"`, `environment = "fixture"`, VND/0) tạo độc quyền; raw DEMO tạo độc quyền tại `raw/<sha>.bin`; kho SQLite `database.connect` + seed SQL legacy trực tiếp đủ **49 bảng có dòng** (FK/CHECK hợp lệ, `foreign_key_check` rỗng). `documents`: `amount_minor` 0 / NULL / 9007199254740993, rowid ẩn 1 / 2 / 9007199254740993. Không `Store.ingest`, không sửa Store/guard. Đây là fixture setup, không phải test ingest.
- **Không-PG (đã chạy, 11 PASS):** hợp đồng 49 bảng/alias/version cũ; hằng shape lịch sử; fixture đủ 49 + giá trị int64/NULL/0; đổi rowid giữ thứ tự/nội dung bị phát hiện (cash, documents) + control nguyên vẹn; phân loại SQLite các ca dữ liệu/bảng lạ/schema cũ; schema_migrations không PK + dòng trùng → không tương thích (không dict); PG→SQLite với nguồn giả từ chối trước lệnh PG + control dương + giao dịch người gọi.
- **PG (viết, UNRUN):** `p01` StorePG→backup→verify→restore→StorePG, so 49 bảng với **SQLite gốc** (không chỉ PG1↔PG2), config bytea, raw, lịch sử, dấu nạp riêng, sequence; `n01` 15 ca đích (dữ liệu/marker/bảng-chỉ mục-sequence-view-hàm lạ/tiền double/thiếu applied_at/trigger lạ sửa tiền/trigger bắt buộc tắt) + 2 đích hỏng dựng riêng bằng migration thật có chủ đích (thiếu FK; lịch sử không PK + dòng trùng) + cũ trống/cũ có dữ liệu, ảnh độc lập (catalog, định nghĩa hàm, dữ liệu, MỌI sequence) trước/sau; `n02` chép dương, identity ALWAYS, sequence kế tiếp, int64/NULL/0; `n02b` BIGINT_MAX và lỗi sequence thứ 6; `n03` PG→SQLite; `n04` constructor autoload (gồm chỉ-hàm `json_extract` lạ/chỉ-kiểu/chỉ-operator/tiền double) + dương vắng mặt/namespace thật sự trống; `n05` restore preflight (gồm chỉ-hàm) + late open; `n06` race với PID chặn = người chép, relation/mode đúng, oracle 48 bảng + cash = nguồn + đúng một dòng người ghi; `n07`; `n08` CLI (cùng giây, bundle khác tên, nội dung khớp nguồn độc lập, writer giữa chép/kiểm, đổi rowid bị bộ kiểm thật phát hiện, lỗi chép/sau SHA/công bố với biên nhận đúng tệp còn lại, nguồn cũ bị từ chối không nâng cấp, bản/partial cũ nguyên).
- **F7:** không đưa DSN/mật khẩu/output thô/exception gốc vào đối số assert hay message; dùng vị từ boolean + thông điệp hằng; lỗi ngoài dự kiến chỉ báo `kiểu:mã/sqlstate`.
- **Giới hạn đã ghi trong test:** race dùng luồng trong tiến trình + barrier monkeypatch guard; CLI gọi `main` trong tiến trình với đồng hồ cố định; không phải tiến trình con độc lập. Root chạy races/CLI thật riêng.

## 6. Hạn chế, rủi ro cần review

1. **PG UNRUN** — có thể còn lỗi chỉ lộ khi chạy (cú pháp catalog query, chuẩn hóa định nghĩa giữa schema đích và tham chiếu, `force_rollback` lồng, RESTART giao dịch). Đặc biệt so sánh catalog phải khớp tuyệt đối với đích tạo bởi constructor; nếu lệch do khác biệt vô hại (vd dạng chuỗi `proconfig`), positive control `p01/n02/n04` sẽ lộ.
2. Dựng tham chiếu cần quyền `CREATE` trên database (schema tạm luôn hoàn tác). Role thường không có quyền → `PG_HOP_DONG_THAM_CHIEU` (fail-closed) ở admission/restore preflight/chép. Restore preflight không còn là giao dịch READ ONLY (ghi tạm rồi hoàn tác).
3. ACL/owner của đối tượng không nằm trong hợp đồng; event trigger toàn DB, đối tượng ở schema khác phụ thuộc vào bảng đích ngoài phạm vi. Đường mở thường không autoload vẫn migrate/bootstrap như cũ (không áp guard).
4. `RESTART` cần quyền chủ sequence (khác `setval` cần UPDATE).
5. Đối chiếu canonical thêm một lượt đọc toàn bộ hai phía mỗi lần chép (chi phí thời gian với kho lớn).
6. Fingerprint `doi_chieu_noi_dung` đổi định dạng (tag kiểu + rowid); `tests/test_v13_doi_chieu.py` và `tools/chep_v12_sang_pg.py` (ngoài whitelist) dùng cùng chữ ký — đọc tĩnh thấy tương thích, chưa chạy.
7. Không chứng minh: ordinary role, full race/CLI tiến trình con, full K2, GUI, restore lifecycle ngoài các ca trên.

## 7. Tuân thủ

Không đọc var/.env/runner/backup thật/source app/secret, không dump env; không xóa file/temp/DB/role/attempt, không DROP trong test (đích hỏng dựng mới, chỉ ALTER/CREATE/DISABLE trên schema DEMO mới); không postgres.connect/migrate/integrity, không SQL K2; không sửa guard/runner/policy/whitelist; không Git/launcher/host/Google/cloud/cutoff/M5/M9/real store/approval/CFO_NTD. Chỉ chạy lệnh tự kiểm đã cấp (lệnh PG bị từ chối quyền — UNRUN).
