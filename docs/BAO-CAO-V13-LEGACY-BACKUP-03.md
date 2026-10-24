# BÁO CÁO V13 — legacy backup, 03

Ngày 19/10/2026. Thực hiện `docs/GIAO-SUA-V13-LEGACY-BACKUP-03.md` (SHA `fe816d01…27ae` theo lệnh root). Đã đọc đủ `REVIEW-V13-BACKUP-SAFETY-02.md`, `REVIEW-V13-BACKUP-CLI-02.md`, `REVIEW-V13-BACKUP-TESTS-02.md`. Báo cáo 01/02, reviews, đầu bài giữ nguyên. **Không tự nghiệm thu V13/33.** M9: không làm gì (không code/schema/service/UI/tracking).

## 0. Kết quả tự kiểm (thực tế)

| Lệnh đã cấp | Kết quả |
|---|---|
| `python -X utf8 -m unittest discover -s tests -p test_v13_backup_safety.py` | **15 test, 15 PASS**, 0 fail/error/skip (ResourceWarning do kết nối test giữ mở, không phải lỗi). |
| `python -X utf8 var/codex-dieu-phoi/run-pg-tests-retained.py test_v13_backup_safety_pg.py` | **UNRUN** — Bash trả `Permission to use Bash with command … has been denied` cho đúng nguyên văn lệnh (1 lần, dừng ngay theo đầu bài; không thử biến thể/shell khác). 0 PG pass/fail. |

Root evidence candidate02 (đầu bài, không tự đọc var): SQLite unit 11/11 PASS; PG 10 chạy, 9 PASS, 1 FAIL tại P01 `SEQUENCE_SAU_CHEP_SAI` (oracle sai ranh giới — R3 dưới). Các phần PG của vòng 03 chỉ được rà tĩnh.

## 1. File thay đổi (6 trong whitelist 7)

| File | Thay đổi |
|---|---|
| `src/kho_tri_thuc/ha_tang/sao_chep_bang.py` | R1: `kiem_rowid_alias_pg` + gọi trong ảnh chụp PG→SQLite; `van_tay_pg` dùng rowid PG thực ở mọi bảng. |
| `tools/sao_luu_pg.py` | R2: trạng thái công bố theo chính lần chạy, `final_ben_khac`, kiểm kê có UNKNOWN, lỗi kiểm kê không thay lỗi gốc. |
| `tests/test_v13_backup_safety.py` | Unit mới: guard alias (nguồn giả) + biên nhận CLI (thư mục tạm DEMO). |
| `tests/test_v13_backup_safety_pg.py` | R1 test n09 + oracle rowid thực độc lập; R3 tách oracle sequence strict/an toàn; R2 ca bên khác + lỗi metadata. |
| `docs/BAO-CAO-V13-LEGACY-BACKUP-03.md` | Báo cáo này. |

`an_toan_sao_chep.py`, `ket_noi.py` **không sửa** vòng này. Không sửa `database.py`, translator, `postgres.py`, `pg_migrations.py`, Store/backup/config/launcher, báo cáo 01/02, reviews, guard/runner/policy.

## 2. R1 / P1 — rowid PG thực khác cột INTEGER PRIMARY KEY

- **Mã từ chối mới: `PG_ROWID_ALIAS_LECH`.** `kiem_rowid_alias_pg(raw, schema)` duyệt **toàn bộ** bảng alias của hợp đồng (bảng có `INTEGER PRIMARY KEY`: `issues`, `audit_events`, `evidence`, `knowledge_events`, `activity_log`, `label_events`, `knowledge_epoch`… theo `hop_dong()["alias"]`), đếm dòng `rowid IS DISTINCT FROM <pk>`; có lệch → từ chối, liệt kê tên bảng (không giá trị dòng).
- **Vị trí:** trong `chep_pg_sang_sqlite`, ngay sau `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY` — cùng ảnh chụp dùng để chép và kiểm (cả callback CLI), **trước** xóa seed/INSERT/COMMIT SQLite, nên trước mọi công bố. Đường `backup.create_backup` và CLI đều đi qua đây. Không sửa dữ liệu/identity nguồn, không đổi DDL/format.
- **Oracle:** `van_tay_pg` nay luôn dùng cột `rowid` thực của PG (không thay bằng PK alias); SQLite dùng rowid thực. Với nguồn biểu diễn được (đã qua guard), rowid + giá trị có kiểu + cột phải khớp; tệp copy bị sửa rowid giữ thứ tự/nội dung vẫn bị phát hiện (control F4 giữ). Chiều SQLite→PG: rowid PG = rowid SQLite (= PK với bảng alias) nên đối chiếu nội bộ không đổi ý nghĩa.
- **Test:** unit `RowidAliasGuardTests` (nguồn giả, PASS: hỏi đúng toàn nhóm alias, lệch → mã). PG `n09` (UNRUN): nguồn hiện hành hợp lệ, `audit_events` thêm id 100 và 50 với rowid identity sinh độc lập (tiền điều kiện quan sát trực tiếp `rowid ≠ id` ở 2 dòng); PG→SQLite → `PG_ROWID_ALIAS_LECH`, đích SQLite và nguồn nguyên; CLI → rc 2, cùng mã, `da_cong_bo=false`, một staging giữ, bản cũ nguyên. Control dương `n03` thêm `rowid_thuc_khop` **độc lập**: bảng lấy từ `sqlite_master`, PK từ `PRAGMA table_info`, so rowid SQLite thực với cột `rowid` PG thực ở cả 49 bảng (gồm documents rowid ẩn 9007199254740993), và PG rowid = PK ở bảng INTEGER PK. `chuan_pg` cũng đổi sang rowid PG thực ở mọi bảng (danh sách bảng/cột vẫn từ hợp đồng sản phẩm — ghi rõ trong docstring).

## 3. R2 / P2 — biên nhận CLI

- `_cong_bo(staging, final, trang)`: final đã tồn tại → `trang["final_ben_khac"]=True` + `DESTINATION_EXISTS`; `trang["da_cong_bo"]=True` **chỉ sau** `os.rename` của chính lần chạy hoàn tất.
- `_bien_nhan(staging, final, trang)`: chỉ kiểm kê tài sản của lần chạy (staging; final chỉ khi chính nó đã công bố) — không liệt kê bundle bên khác. Mỗi bước metadata bọc riêng: `exists` lỗi → mục vào `khong_xac_dinh`; `iterdir` lỗi → `<staging>/*` vào `khong_xac_dinh`; khi đó `kiem_ke="UNKNOWN"`, `kiem_ke_loi` = tên lớp lỗi đã làm sạch. Không suy "không có" từ việc không đọc được.
- `sao_luu`: lỗi trong chính hàm kiểm kê không thay lỗi gốc — exception gốc được raise lại với biên nhận `kiem_ke="UNKNOWN"`, `partial_giu_lai="UNKNOWN"`. `main`: lỗi trước khi có staging → `kiem_ke="KHONG_AP_DUNG"`. Trường mới trong JSON lỗi: `final_ben_khac`, `khong_xac_dinh`, `kiem_ke`, `kiem_ke_loi`.
- Giữ: bundle tên giây+UUID, mkdir/tạo tệp độc quyền, SHA trước công bố, một lần rename (cam kết Windows, không portable/crash-durable), nguồn cũ từ chối chỉ đọc, `--giu` không rotate, nhãn `LEGACY_DB_FALLBACK`, không xóa/di chuyển bản/partial cũ.
- **Test:** unit `BienNhanCliTests` (PASS): final bên khác không nhận sở hữu + staging/bundle bên khác nguyên; công bố của chính mình mới `da_cong_bo=true`; lỗi `iterdir` → UNKNOWN; lỗi trong hàm kiểm kê → giữ mã gốc `DEMO_LOI_GOC`, staging thực còn. PG `n08` (UNRUN) thêm: bên khác tạo final sau SHA/trước công bố → `DESTINATION_EXISTS`, `final_ben_khac=true`, biên nhận chỉ chứa staging, tệp bên khác nguyên; lỗi metadata sau lỗi chép → mã `DEMO_LOI_CHEP` giữ, `kiem_ke=UNKNOWN`, partial thực còn.

## 4. R3 / P2 — oracle sequence đúng ranh giới (không sửa sản phẩm)

- `kiem_sequence_strict` (RESTART: `last_value=max+1`, `is_called=false`) chỉ dùng ở ranh giới chép trực tiếp `n02`, trước mọi INSERT/Store; giữ phép đo INSERT thật sau đó (`rowid = max+1`).
- P01 sau Store open/backup/restore/reopen dùng `kiem_sequence_an_toan`: giá trị sinh kế tiếp (`last_value` nếu chưa gọi, `last_value+1` nếu đã gọi) > max mọi cột identity — không ép quay về trạng thái trước các `INSERT … ON CONFLICT DO NOTHING` hợp lệ của Store; kiểm identity mode `ALWAYS`; thêm phép đo INSERT thật trên schema phục hồi, dòng DEMO mới tách khỏi nội dung nền (nền vẫn bằng SQLite gốc). Không mock `nextval`, không sửa Store/sản phẩm.
- Giữ `n02b`: BIGINT_MAX từ chối trước hiệu ứng; lỗi ở lần đặt sequence thứ 6 → ảnh độc lập (MỌI `last_value/is_called`, dữ liệu, catalog) như trước.

## 5. Giữ nguyên controls

Fixture DEMO tự chứa (config/raw tạo độc quyền, 49 bảng có dòng, int64 > 2^53 / NULL / 0); P01 StorePG→backup→verify→restore→reopen so SQLite gốc, raw, config, lịch sử, dấu nạp riêng; R1 inventory/drift/history/trigger/function-type-operator refusals; locks/giao dịch người gọi/FK mode; nguồn cũ không migrate; race với PID chặn/relation/mode + full 48 bảng + đúng dòng người ghi (giới hạn: luồng trong tiến trình + barrier monkeypatch); CLI gọi `main` trong tiến trình với đồng hồ cố định (giới hạn ghi rõ). Assert không đưa DSN/mật khẩu/output thô vào thông điệp.

## 6. Hạn chế

1. Toàn bộ PG vòng 03 (n09, p01 sửa, n03 thêm, n08 thêm) **UNRUN** — cần root chạy.
2. Guard alias quét `count(*)` từng bảng alias trong mỗi lần backup (thêm chi phí đọc).
3. Unit guard alias và biên nhận dùng nguồn giả/thư mục tạm, không phải PG/CLI tiến trình con.
4. Không chứng minh: ordinary role, full race/CLI tiến trình con, full K2, GUI, restore lifecycle ngoài các ca nêu.

## 7. Tuân thủ

Không đọc var/.env/runner/backup thật/source app/secret; không dump env/rows/traceback; không xóa file/temp/DB/role/attempt, không DROP; không postgres.connect/migrate/integrity, không SQL K2/M9; không sửa guard/runner/policy/whitelist; không Git/launcher/host/Google/cloud/cutoff/M5/M9/real store/approval/CFO_NTD. Chỉ chạy hai lệnh đã cấp (lệnh PG bị từ chối quyền → UNRUN).
