# Báo cáo sửa M0–M5 intake/history/API/UI — gói 03 (CODE ONLY)

**19/10/2026 — CODE ONLY / RUNTIME_UNRUN / CHƯA NGHIỆM THU.** Cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`, sửa tiếp candidate02 (manifest root `3d5acde6…9906`) theo `docs/GIAO-SUA-M0-M5-INTAKE-UI-03.md` (SHA do root pin `c3e9ef21…3993de`) và bốn review final02 (MIGRATION/SERVICE/HTTP-UI/ROOT-TEST). Handoff02 `43902e6e…7816`, handoff01, binding/DTO/SQL contract giữ làm căn cứ.

Coder **chỉ dùng Read/Glob/Grep/Edit/Write**. **Không** chạy/import/compile product, test, SQL, PostgreSQL, HTTP, GUI, launcher, process hay mạng; không Bash/command tool. Không đọc var/.env/secret/source app/dòng thật. Không xóa/move/cleanup/drop/reset file/DB/role/attempt; không đổi git/pip/config/policy/shell. Không sửa/chạy M9, tracker, nguồn #10, L11, engine tồn/giá trị/bút toán. Không cấp/reset quyền để né guard. **Mọi kết quả runtime dưới đây là UNRUN.** Test 01/02 và báo cáo coder không được suy thành PASS cho 03. Checksum mới của M0013_COMMON/M0014_M5 **chưa tính** (definition đã đổi so với 02 — root pin riêng; DB đã áp 02 không dùng cho 03).

## 1. File đã sửa (trong 17 target)

| File | Thay đổi |
|---|---|
| `src/kho_tri_thuc/k2/crm_khoi_dong.py` | `kiem_ket_noi_chu`: alias duy nhất `hien_tai/chu_stage/chu_phieu/chu_lo`, đọc theo tên cột qua `_theo_ten` (tuple đúng 4 cột hoặc dict đúng 4 khóa); sai dạng/NULL/sai chủ → `KET_NOI_CHU_SAI` (không IndexError). Giữ kiểm đích thực trước, exact current_user = relowner. |
| `src/kho_tri_thuc/ha_tang/postgres.py` | `_current_state`: verified-empty dùng `_dem_doi_tuong_nguoi_dung` (pg_class trừ index, pg_proc, pg_type độc lập, collation, operator; ngoài schema hệ thống/temp/toast; trừ thành viên extension `pg_depend 'e'`). Schema rỗng không tính. Áp cho cả nhánh không có master và master-thiếu-lịch-sử. S06 whitelist giữ nguyên. |
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` | COMMON: bảng `giao_tiep.ket_qua_cuoi_tiep_nhan` (bất biến, INVOKER owner-only + actor + khớp biên nhận/stage/H), `nguon_tim_lan_nhan` trả thêm `ket_qua_cuoi`, getter `nguon_anh_xa_hien_hanh` dùng `ktt_nguon_duoc(...,'SOURCE_MAP', target)` (instance HOAT_DONG + ID/login phiên) và lọc hàng theo đúng PN đích; RLS/REVOKE bảng mới. M5: `kho.m5_quan_sat_du_dieu_kien` (cổng eligible), trigger con trỏ dùng cùng cổng, `giao_tiep.nguon_chot_ket_qua` (INVOKER, không cấp app_web), `kho.m5_co_so_file_noi_bo`/`kho.m5_co_so_file` (basis + token), namespace lock trong review/mapping/FILE, FILE guard hiện hành trước cached result, H FILE gồm token, lô/biên nhận mang token + refs. Prefix 1–12 và M0013 full-M9 lịch sử **không đổi**. |
| `src/kho_tri_thuc/k2/nguon_chung.py` | `chot_ket_qua` (gọi hàm chốt trên kết nối chủ). |
| `src/kho_tri_thuc/k2/kho_so_luong.py` | `nhan`: chốt kết quả cuối sau typed/hold cùng giao dịch, fresh trả đúng bản đã chốt; replay `_phat_lai` trả kết quả cuối đã chốt (thiếu → lỗi rõ, không tính lại). `xuat_file_soat`: bắt buộc `co_so_truoc`, đưa vào preflight/stage. `chi_tiet` trả `co_so_file` (token + kỳ + khóa kỳ). Workbook thêm sheet `CO_SO` (provenance) và `DONG_NGUON_CAPTURE` (raw token/loại/validation/lỗi). |
| `src/kho_tri_thuc/giao_dien/server.py` | `xuat-file-soat` whitelist đúng 6 trường (phiếu, khóa, ba con trỏ, `co_so_truoc`); `KET_QUA_CUOI_CHI_CHU` → 403. |
| `src/kho_tri_thuc/giao_dien/assets/app.js` | R1: `m5Act` kiểm epoch lại sau `await m5Load()`; caller kiểm epoch trước render. R2: `m5FormEpoch`, `m5XoaForm` (xóa File input/lỗi/khóa khi đổi vai hoặc nguồn/phạm vi), refresh giữ lựa chọn còn hợp lệ, coverage theo phạm vi đang chọn, submit chụp claim + File object trước FileReader, form đổi trong lúc đọc → hủy lần gửi. `m5GioiHan` có epoch. R3/R4: khóa FILE trong `m5KhoaFile` theo (actor, PN, phiếu, ba con trỏ, token basis), sống qua refresh; nút "Lần xuất mới" mới đổi khóa; body gửi `co_so_truoc`. |
| `src/kho_tri_thuc/giao_dien/assets/index.html` | Thêm một dòng hướng dẫn form nhận tệp. |
| `tests/test_m0_m5_migrations.py`, `tests/test_m5_k2.py`, `tests/test_m5_http.py` | Regression (mục 3). |
| `docs/BAO-CAO-M0-M5-INTAKE-UI-03.md` | Báo cáo này. |

**Không sửa:** `k2/lien_ket_chung.py`, `k2/quyen.py`, `k2/m5_demo.py`, `k2/crm_demo.py`, `assets/style.css`. Ngoài ra không sửa reader/fixture/DTO/report01–02/handoff/review/contract/tools/launcher.

## 2. Findings và trạng thái (tĩnh; runtime UNRUN)

| Finding | Sửa | Trạng thái |
|---|---|---|
| SR02-0 / root P1: dict_row gộp cột trùng tên → IndexError | Alias duy nhất + đọc theo tên. Giữ đích thực + exact owner. | Đã sửa code. Cần root chạy lại M5K2Pg/HTTP bootstrap. |
| Business-key namespace FILE/MAP/review | Khóa `BIEN_NHAN|PN|M5|op|key` trước tra biên nhận. Thứ tự: namespace → subject/mapping (FILE: mapping FOR SHARE) → advisory `PHIEU_KHO` → hàng danh tính. FILE giữ xuyên preflight→ghi file→stage→consumer cùng giao dịch chủ. MAP tra biên nhận sau namespace + subject. Quyền hiện hành vẫn kiểm trước. | Đã sửa code. Race chưa chạy. |
| I-M05 accepted ≠ eligible | eligible chỉ khi đạt `m5_quan_sat_du_dieu_kien`: Đã duyệt + KNOWN + phân loại chỉ mã thông tin + capture không PARTIAL + master pin + mọi dòng nguồn HOP_LE + ≥1 dòng, mọi dòng STRING exact có số chuẩn hóa và đơn vị. Trigger con trỏ ép cùng cổng (kể cả chủ bảng). Accepted giữ trục riêng. | Đã sửa code. Không chặn FILE export HOLD. |
| FILE whole basis + replay | Token = SHA-256 của basis jsonb do DB dẫn xuất, không timestamp biến động, gồm: phiếu, con trỏ, mapping của danh tính + mapping hiện hành subject, quan sát/nội dung chọn, capture/bundle/vai trò/profile, master catalog, facts đo lường, dòng content, dòng nguồn, cổng eligible, kỳ + trạng thái khóa, chuỗi quan sát. Luồng: chi_tiet → UI → HTTP → service → preflight (kỳ → con trỏ → token **trước** tra biên nhận) → stage → consumer (kiểm lại) → lô/biên nhận (token + refs) → workbook (`CO_SO`). | Đã sửa code. |
| SR02-1 capture final-result replay | Bảng kết quả cuối bất biến, chốt bằng `nguon_chot_ket_qua` sau typed/hold cùng giao dịch. Hàm đối chiếu refs quan sát / HOLD stage / kỳ khóa thật / snapshot_moi với DB. Replay đọc lại qua `nguon_tim_lan_nhan`. Không UPDATE stage/biên nhận, không cấp app_web. | Đã sửa code. |
| I-S01 SOURCE_MAP getter với instance DUNG | Predicate nguồn hiện hành theo đúng PN đích; CFO không cần INTAKE/READ_SOURCE. | Đã sửa code. |
| I-S02 verified-empty chỉ bảng | Đếm catalog người dùng (mục 1). | Đã sửa code. Chưa chạy reproducer. |
| R1/R2/R3 UI | Mục 1. | Đã sửa code. Browser chưa chạy; assertion chuỗi trong test HTTP chỉ là có mặt giao diện, không thay kiểm GUI. |

Controls đã đóng ở 02 được giữ nguyên:
- Stage owner-only.
- Consumer chỉ nhận stage ID + H.
- Core quantity-only.
- RLS/REVOKE legacy.
- Đường dẫn/purpose lô.
- Exact 8 actor.
- Strict `reported_errors`.
- Seed một lần.
- Old-A âm, reversed-B accepted với eligible NULL.

## 3. Regression đã viết (UNRUN)

- **Thuần (`test_m5_k2.ThuanM5`):**
  - `test_kiem_ket_noi_chu_tuple_va_dict_row`:
    - tuple và dict đúng chủ là dương;
    - các ca âm `KET_NOI_CHU_SAI`: sai chủ, dict cột gộp kiểu cũ, thiếu cột, NULL;
    - khác cổng là âm `KET_NOI_KHAC_DB`.
  - `test_workbook_co_so_provenance`: provenance, NULL trống, `-0`/NULL nguyên văn, ô không formula.
- **PG (`test_m5_k2.M5K2Pg`, theo thứ tự):**
  - t01: tuple owner dương, login ứng dụng làm "chủ" âm.
  - t03: replay K01 trả đúng promote/stage/snapshot_moi + refs, 0 delta (counts gồm bảng kết quả cuối).
  - t06: K01 exact cho eligible UUID và cổng = true.
  - t13/t14: K08, K09, K10 là quan sát mới nhất Đã duyệt/KNOWN, không mã chặn → CFO chấp nhận (accepted = obs) nhưng eligible NULL, cổng = false. Chủ bảng UPDATE eligible trực tiếp → `CON_TRO_ELIGIBLE_SAI`.
  - t16: hai kết nối cùng khóa → kẻ thua có cùng promote/stage.
  - t17b: MAP namespace.
    - Yêu cầu 1 giữ giao dịch chưa commit. Observer thấy backend app2 chờ advisory. Commit → yêu cầu 2 REPLAY cùng mapping/biên nhận.
    - Positive control: khóa khác → `ANH_XA_DA_CO`.
    - Hết giờ/treo là không đạt.
  - t18: basis token.
    - Token xác định.
    - Expected sai (con trỏ, token, thiếu token) → 409/400 với 0 delta file/DB.
    - Cùng khóa + cùng basis → cùng lô. Cells/`CO_SO`/token trong lô.
    - Chủ CSDL thêm một khai báo đo lường **không khớp điều kiện**: ba con trỏ giữ nguyên nhưng token đổi. Retry khóa cũ → `KHO_VERSION_CHANGED` (không cached success). Cùng khóa + basis mới → `IDEMPOTENCY_KHAC`. 0 delta. File cũ tải đúng bytes. Khóa mới xuất được.
  - t18b: FILE namespace.
    - Một giao dịch chủ khác giữ khóa namespace, mô phỏng winner của phiếu khác cùng PN/khóa. Yêu cầu FILE chờ (observer) với 0 stage/file/lô trong lúc chờ.
    - Winner ghi biên nhận khác H rồi commit → yêu cầu FILE nhận `IDEMPOTENCY_KHAC`, delta duy nhất là biên nhận của winner, không file mới.
    - Positive control: khóa mới.
  - t20: kỳ khóa.
    - Capture GIU_CHO/KY_DA_KHOA có kết quả cuối; replay trả đúng HOLD, 0 delta.
    - Retry FILE đúng khóa/basis của lô t18 → `KY_DA_KHOA` (kỳ trước cached). File cũ tải đúng hash.
  - t23 (chạy cuối, đổi lifecycle):
    - CFO chỉ SOURCE_MAP đọc getter dương; KTA âm.
    - Instance → DUNG: cùng getter `NGUON_KHONG_CO_QUYEN`; năng lực/đếm không đổi.
- **Migration:**
  - Tĩnh `test_sql_repair03_thu_tu_khoa_guard_va_cong`:
    - thứ tự khóa và guard trước lookup;
    - token thuộc H;
    - eligible qua cổng;
    - getter mới;
    - hàm nội bộ không GRANT app_web.
  - PG:
    - `test_i_s02_*`: enum/sequence/function/view/domain (public, master, schema lạ) bị từ chối, catalog nguyên.
    - DB mới, schema rỗng, master rỗng dương.
    - pgcrypto (skip nếu máy không có — không tính đạt).
- **HTTP:**
  - Token basis trong chi tiết.
  - Trường lạ 400, thiếu token 400, token stale 409, cả ba 0 delta.
  - Lô mang token; replay capture qua HTTP đúng kết quả cuối.
  - Chuỗi JS mới có mặt (chỉ kiểm có mặt, không thay GUI).

Lệnh chạy do root quyết định. Ví dụ phạm vi: `python -X utf8 -m unittest tests.test_m0_m5_migrations tests.test_m5_k2 tests.test_m5_http` với `KHO_PG_DSN_TEST` trên DB DEMO mới. **Coder chưa chạy lệnh nào.**

## 4. Giới hạn và rủi ro còn mở

1. **Không có runtime.** Các điểm sau có thể sai khi chạy thật và cần root kiểm:
   - Cú pháp/ngữ nghĩa SQL mới: cổng eligible, basis jsonb, so sánh token, chốt kết quả.
   - Thứ tự khóa / deadlock.
   - Observer pg_locks.
   - Workbook mở thật.
   - UI trên trình duyệt.
2. **Hai phiếu thật cùng PN:** fixture pin chỉ có `SoPhieu` NK20260814001 cho instance A (scope pin SoPhieu), nên t18b mô phỏng winner "phiếu khác" bằng biên nhận do chủ CSDL ghi trong DB test mới. Chưa có thứ tự winner ngược (service thắng trước rồi phiếu thật khác cùng khóa) bằng hai phiếu thật.
3. **Giả định trong t14:** K09/K10 được giả định không mang mã chặn chấp nhận (vd `REAPPEARANCE_HOLD`). Nếu runtime cho thấy có, test báo rõ nguyên nhân thay vì nới oracle.
4. **Cổng eligible là cổng số lượng DEMO** (`EXACT_SYNTHETIC_DEMO` + đơn vị + master + HOP_LE + capture không PARTIAL). Không phải proof L11/tiền, không dựng policy kế toán. L11/tồn/kiểm kê vẫn chưa có producer.
5. **Basis gồm toàn bộ facts đo lường của profile.** Thêm khai báo mới (kể cả không khớp) làm token đổi, nên file soát cần xem lại. Đây là chủ ý (stale phải bị nhận biết), có thể gây 409 nhiều hơn khi registry thay đổi.
6. **Cách đếm catalog `_current_state`:**
   - Không đếm index riêng (index luôn đi với bảng).
   - Không đếm event trigger/FDW server/publication cấp DB.
   - Đối tượng thuộc extension đã cài được coi là hạ tầng hợp lệ.
7. **UI:**
   - Khóa FILE nằm trong bộ nhớ trang (Map); tải lại trang thì khóa mới. Server vẫn giữ idempotency theo khóa đã gửi.
   - `m5KhoaFile` không bị xóa khi đổi vai: khóa theo actor nên không dùng chéo.
8. **Checksum COMMON/M5 đổi so với 02.** DB đã áp 02 không nâng tại chỗ; runtime 03 cần DB DEMO mới do root cấp.

Kết thúc phạm vi sửa 03. Root freeze → full-read → kiểm chứng độc lập; runtime release riêng.
