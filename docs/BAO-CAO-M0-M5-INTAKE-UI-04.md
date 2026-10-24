# Báo cáo sửa M0–M5 — gói 04 (CODE ONLY)

**19/10/2026 — CODE ONLY / RUNTIME_UNRUN / CHƯA NGHIỆM THU.**

- **Phiên:** cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`.
- **Baseline:** frozen210 final03 `37b671d7…58056a` (actual 35965, terminal `69e9ac`).
- **Căn cứ:** `docs/GIAO-SUA-M0-M5-INTAKE-UI-04.md` (root pin `aedd9f87…d539e`), `REVIEW-M0-M5-ROOT-TEST-03.md`, `REVIEW-M0-M5-MIGRATION-03.md`, `REVIEW-M0-M5-SERVICE-03.md`, `REVIEW-M0-M5-HTTP-UI-03.md`. Handoff01–03, DTO, binding và fixture vẫn ràng buộc.
- **Coder chỉ dùng Read/Glob/Grep/Edit/Write.** Không chạy/import/compile product hoặc test; không SQL/PG/HTTP/UI/process/network/Bash.
- **Giới hạn đọc/ghi:** không đọc var/.env/secret/source app/dòng thật. Không xóa/move/drop/reset/cleanup. Không git/pip/config/policy/shell.
- **Không đụng:** M9, M2/L11, engine tồn/giá trị/bút toán, policy production mới.
- **Runtime:** mọi kết quả dưới đây là **UNRUN**. FAIL service03 (`t12`) và hai probe của root (mixed preview, text-search admission) không được coder coi là đã đóng khi chưa chạy lại.

## 1. File sửa (6/8 target; không cần sửa `pg_migrations.py`)

| File | Thay đổi |
|---|---|
| `k2/kho_so_luong.py` | **Mục 1.** `_tx_doc` mở giao dịch rồi chạy `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY` làm statement ĐẦU TIÊN, trước GUC/SELECT nào. Nếu kết nối đang có giao dịch (outer/nested), từ chối rõ bằng `M5_DOC_NHAT_QUAN`, không hạ cấp thành savepoint. `chi_tiet` dùng `_tx_doc`, nên mọi SELECT hiển thị và `kho.m5_co_so_file` (token) cùng một snapshot. Guard quyền/kỳ/con trỏ/basis hiện hành tại FILE action và đường tải lô cũ không đổi. |
| `ha_tang/postgres.py` | **Mục 3.** Inventory verified-empty thêm `pg_ts_config`, `pg_ts_dict`, `pg_ts_parser`, `pg_ts_template`, `pg_conversion`, `pg_opfamily` (opclass luôn thuộc opfamily). Cùng quy tắc ngoài schema hệ thống/temp/toast, trừ thành viên extension. Schema rỗng, master rỗng và pgcrypto vẫn dương. Áp cho cả nhánh không master (`FOREIGN_DATABASE`) và master-thiếu-lịch-sử (`MIGRATION_HISTORY`), trước DDL/lịch sử/marker/seed. Whitelist tiền tố lịch sử S06 nguyên. |
| `giao_dien/assets/app.js` | **Mục 2.** `m5Act(path, body, ok, conHieuLuc)` kiểm predicate của caller cùng actor epoch ở mọi điểm hoàn tất: sau POST (trước toast), sau `await m5Load`, và trong nhánh lỗi. Upload truyền `() => fe === m5FormEpoch`. Nếu form/nguồn/phạm vi/coverage/khóa đã đổi, thì:<br>• không toast;<br>• không tóm tắt kết quả;<br>• không gắn lỗi vào form hiện tại;<br>• chỉ hiện ghi chú trung tính `M5_FORM_DA_DOI`.<br>Capture đã commit không bị rollback. Các phần giữ nguyên: actor epoch, raw ArrayBuffer→base64, khóa FILE sống qua refresh, nút "Lần xuất mới". |
| `tests/test_m5_k2.py` | Mục 1, 4, 5 (xem §2). Helper `nhan` truyền phạm vi registry tường minh. Bỏ test winner mô phỏng của 03, thay bằng hai phiếu thật. |
| `tests/test_m0_m5_migrations.py` | Mục 3 (xem §2). |
| `tests/test_m5_http.py` | Chỉ thêm chuỗi `conHieuLuc` vào kiểm có mặt. Đây không phải bằng chứng GUI. |
| `docs/BAO-CAO-M0-M5-INTAKE-UI-04.md` | Báo cáo này. |

`pg_migrations.py` không đổi, nên checksum COMMON/M5 của 03 giữ nguyên. Prefix 1–12, M0013 full-M9 lịch sử, server/seed/quyền/DTO/reader/fixture không đổi.

## 2. Regression đã viết (UNRUN)

### Mục 1 — `t18b_chi_tiet_va_token_cung_snapshot`

Interleave thật, không mock quyền hay kết quả:

- **Cách chèn interleave:** `_HenGio` ủy quyền nguyên SQL, tham số và kết quả. Nó chỉ chèn một hook ngay trước SELECT `viec_can_duyet`, tức sau khi SELECT mapping đã đọc xong.
- **Đột biến:** hook dùng kết nối chủ thứ hai với CFO_A hiện hành, trigger bật, 0 grant mới. Nó đóng mapping A, nối successor B cùng PN (`ROOT_SEED_DEMO`) rồi COMMIT. Một observer độc lập xác nhận `DONG` + successor đã thấy được.
- **Oracle:**
  - Preview không rỗng.
  - Không đột biến thì cùng token.
  - Có đột biến:
    - kết quả là trọn view A (A mở, số mapping cũ) + tokenA;
    - đọc lại thì thấy view B + tokenB ≠ A, ba con trỏ giữ nguyên;
    - FILE với view cũ → `KHO_VERSION_CHANGED`, 0 delta DB/file;
    - FILE với view mới → dương, tải đúng hash/độ dài.

### Mục 4 — `t12`

- Lấy tập logical line ID theo đúng `phieu_id` + PN trước và sau K07.
- Tập của A không đổi: không xóa, không clone, không trùng.
- Nội dung partial chỉ chứa tập con thực sự.
- Tập và hàng của instance B nguyên vẹn.
- Không nâng expected lên 4, không xóa instance.

### Mục 5 — `t18c_file_namespace_hai_phieu_that_ca_hai_thu_tu`

- **Tạo phiếu sibling:**
  - Trong DB test mới, chủ CSDL thêm một hàng `master.nguon_pham_vi` sibling cho DEMO_KHO_A (SoPhieu `NK20260814002`), sao chép profile/kho/sections/coverage_binding.
  - Bytes K01 được đổi chuỗi SoPhieu.
  - Intake thật bằng M0A tạo phiếu thứ hai cùng PN.
  - Không đổi file fixture/registry, 8 actor hay grant.
- **Mỗi thứ tự thắng (khóa mới):**
  - Request thắng (service với kết nối chủ 1) được giữ ngay trước INSERT stage: đã khóa namespace và ghi file.
  - Kẻ thua (service với kết nối chủ 2): observer thấy advisory NOT granted, và 0 stage/lô/file mới trong lúc chờ.
  - Thả request thắng: thắng commit; thua nhận `IDEMPOTENCY_KHAC`.
  - Delta chỉ gồm stage/lô/biên nhận của bên thắng; file chỉ của bên thắng.
  - Thắng gửi lại cùng H → cùng lô. Thua gửi lại vẫn 409.
- Timeout hoặc treo không tính đạt.

### Mục 3 — `test_repair04_text_search_config_ngoai_lai_tu_choi_truoc_ghi`

- **Thiết lập:** `CREATE TEXT SEARCH CONFIGURATION public.ngoai_ts (COPY = pg_catalog.simple)`, có mapping, không thuộc extension. Chạy hai ca: không master và master rỗng.
- **Kiểm:**
  - Admission trong giao dịch READ ONLY ra đúng `FOREIGN_DATABASE` / `MIGRATION_HISTORY`.
  - `migrate` cũng từ chối với cùng mã.
  - Catalog độc lập trước/sau (ts config/map, quan hệ, hàm, namespace, lịch sử, marker) có 0 delta.
- Các test dương empty/pgcrypto của 03 giữ nguyên.

### Mục 2 — chỉ có trong code JS

Không có test trình duyệt. Root kiểm GUI sau release riêng.

## 3. Trạng thái

| Mục | Trạng thái |
|---|---|
| 1. Preview + token cùng snapshot | Đã sửa code + regression interleave thật; UNRUN. |
| 2. Form predicate xuyên completion | Đã sửa code; browser UNRUN. |
| 3. Text-search config admission | Đã sửa code + regression; UNRUN. |
| 4. Oracle partial theo phiếu | Đã sửa test; UNRUN. |
| 5. Namespace hai phiếu thật, hai thứ tự | Test đã viết; UNRUN. |

## 4. Giới hạn và rủi ro thật

1. **Không runtime.** Các giả định chưa được chứng minh:
   - SET TRANSACTION đầu giao dịch trên kết nối autocommit psycopg.
   - `_HenGio` ủy quyền qua `__getattr__` (adapters/info/transaction).
   - Phiếu sibling qua reader: kỳ vọng scope/SoPhieu khớp, mapping hiện hành B cùng PN, không giữ chờ.
   - Thứ tự test phụ thuộc trạng thái: t18b đổi mapping hiện hành của kho DEMO_KHO_A sang successor B cùng PN trước t18c/t20/t23.
2. **Đọc hai lần trong REPEATABLE READ.** Snapshot chi tiết chỉ bảo đảm display + token nhất quán với nhau, không bảo đảm còn hiện hành. Việc đó do guard FILE (kỳ → con trỏ → token) tại thời điểm xuất xử lý. Snapshot cũ dẫn tới 409, không chấp nhận âm thầm.
3. **Inventory catalog hữu hạn:** 5 lớp của 03 + 6 lớp ts/conversion/opfamily. Event trigger, FDW/server, publication/subscription, extended statistics cấp DB vẫn ngoài inventory. Không fail-closed blanket.
4. **UI:**
   - Ghi chú `M5_FORM_DA_DOI` là trạng thái chung, không gắn kết quả cũ vào form mới.
   - Lần nhận cũ vẫn hiện trong bảng nguồn sau refresh, như là dữ liệu đã commit.
   - Chưa có kiểm causal trên trình duyệt.
5. **Test 03 đã bỏ:** test winner mô phỏng t18b của 03 được thay, không giữ song song. Test MAP namespace (t17b) giữ nguyên.

Kết thúc phạm vi 04. Root freeze → review → runtime riêng.
