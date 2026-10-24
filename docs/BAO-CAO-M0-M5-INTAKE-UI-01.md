# Báo cáo M0–M5 — intake, history, API/UI, gói 01 (CODE ONLY)

**19/10/2026 · tự báo cáo của coder · CODE ONLY, chưa chạy gì · CHỜ ROOT freeze/full-read/review độc lập.** Đây không phải nghiệm thu. Actual DDL, runtime, test, HTTP và GUI chỉ được release riêng sau review. Không có nhãn PASS nào cho M0/M5/L11/UI.

Căn cứ đã đọc: `docs/GIAO-CODE-M0-M5-INTAKE-UI-01.md` (SHA `86854344…0030e`), `docs/M0-M5-SQL-VA-FIXTURE-01.md` (root pin), `docs/BINDING-M5-CORE-SAU-CRM03.md`, DTO03 và các fixture `tests/fixtures/m0_m5/*` (registry `780180aa…`, manifest `51b794ae…`, lineage-pins `41819401…`). Pure reader final (`nguon/kho_10.py`) được dùng nguyên, không sửa.

## 1. Trạng thái thực thi

| Hạng mục | Kết quả |
|---|---|
| Chạy/import product, tests, SQL/PG, HTTP, GUI, launcher, process | **UNRUN** — gói CODE ONLY không có công cụ thực thi. Không dùng Bash, không import, không compile |
| `tests/test_m0_m5_migrations.py` | **UNRUN** (5 test tĩnh + 4 test PG chỉ chạy khi có `KHO_PG_DSN_TEST`) |
| `tests/test_m5_k2.py` | **UNRUN** (6 test thuần + 21 test PG) |
| `tests/test_m5_http.py` | **UNRUN** (1 test PG/HTTP) |
| PASS / FAIL / ERROR / SKIP | 0 / 0 / 0 / 0 — không có lần chạy nào. Không suy PASS từ việc đọc mã |
| Checksum SQL COMMON13 / M5 14 | **Chưa tính** (cần chạy Python); root tính khi freeze |

## 2. File đã sửa/tạo (15/17 target trong whitelist)

| # | File | Thay đổi |
|---|---|---|
| 1 | `src/kho_tri_thuc/ha_tang/pg_migrations.py` | **Chỉ thêm** sau M0013. M0001–M0012, `M0013` full-M9 và các helper sinh ra nó **giữ nguyên bytes**. Thêm `PG_MIGRATIONS_LICH_SU_FULL_M9` (định nghĩa lịch sử, không execute), `LEGACY_FULL_M9_M0013_SHA256` theo root pin, `M0013_COMMON` (52 câu) và `M0014_M5` (24 câu). Chuỗi mặc định đổi thành `M0001..M0012 + M0013_COMMON + M0014_M5`; `PG_SCHEMA_VERSION = 14`. `PG_MIGRATION_TUONG_THICH` không đổi |
| 2 | `src/kho_tri_thuc/ha_tang/postgres.py` | Thêm `kiem_lich_su` (cổng lineage chạy TRƯỚC mọi DDL/marker/seed) và `kiem_lineage_ung_dung` (cổng mở app: đúng lineage và đúng bản mới nhất). `migrate()` từ chối chuỗi `migrations=` tùy chỉnh dài hơn M0012 |
| 3 | `src/kho_tri_thuc/k2/quyen.py` | Thêm action M5 (`M5_READ`, `M5_FILE_SOAT`, `M5_MAP_V4` cần V4, `M5_SOURCE_REVIEW_V8` cần V8) và `kiem_nguon()`. Hàm này gọi CSDL `master.ktt_nguon_duoc` để kiểm năng lực nguồn trước PN, không dùng `kiem` với PN giả. Các action CRM/M1/M9 giữ nguyên |
| 4 | `src/kho_tri_thuc/k2/nguon_chung.py` (mới) | Intake trung tính: kiểm digest registry bằng canonical, artifact theo vai trò, envelope + H `m0-capture/v1`, bundle digest, blob content-addressed ghi độc quyền + kiểm hash, các lời gọi hàm integration trong CSDL |
| 5 | `src/kho_tri_thuc/k2/kho_so_luong.py` (mới) | `KhoSoLuongK2`: nhận nguồn trước PN → dựng context từ phía máy chủ → reader final → promote → danh sách/chi tiết/lịch sử → review V8, mapping V4, file soát. Kiểm kê/tồn báo chưa có producer; L11 trả mã sạch |
| 6 | `src/kho_tri_thuc/k2/m5_demo.py` (mới) | Seed DEMO chỉ thêm từ registry đã pin (kiểm SHA file, canonical digest, master bytes); 8 actor + phân quyền + năng lực nguồn. Hàng bất biến đã có mà khác nội dung → `NGUON_SEED_XUNG_DOT`, không ghi đè. Không seed history/accepted/digest K01–K10 |
| 7 | `src/kho_tri_thuc/k2/crm_khoi_dong.py` | Bổ sung: gọi `m5_demo.khoi_tao` sau seed CRM; cổng lineage thay cho `max(version)`; `giao_tiep` được thêm vào danh sách schema cấm login ứng dụng sở hữu |
| 8 | `src/kho_tri_thuc/giao_dien/server.py` | Cổng mở CRM dùng `kiem_lineage_ung_dung` (nếu là legacy full-M9 thì báo đúng mã). Thêm dịch vụ M5 dùng chung kết nối/cookie phiên/khóa thao tác của CRM, và các route `/api/m5*`. Mã HTTP riêng cho M5 (403 phạm vi / 409 xung đột / 501 L11); CRM/M9 giữ hành vi cũ |
| 9 | `src/kho_tri_thuc/giao_dien/assets/index.html` | Thêm nav và trang `#phieukho`; vùng CRM/M9 không đổi |
| 10 | `src/kho_tri_thuc/giao_dien/assets/app.js` | Thêm khối JS M5 (chèn mới, không sửa dòng CRM/M9; trang đăng ký qua `pages.phieukho`) |
| 11 | `src/kho_tri_thuc/giao_dien/assets/style.css` | Thêm vài class `.m5-*` |
| 12–14 | `tests/test_m0_m5_migrations.py`, `tests/test_m5_k2.py`, `tests/test_m5_http.py` (mới) | Xem §1 |
| 15 | `docs/BAO-CAO-M0-M5-INTAKE-UI-01.md` (mới) | Báo cáo này |

Hai target **không cần sửa nên giữ nguyên**: `k2/lien_ket_chung.py` (`tim_bien_nhan`/`ghi_bien_nhan`/`bam_yeu_cau` dùng lại được) và `k2/crm_demo.py` (actor M5 là login mới, nên UPSERT của CRM không đụng tới; không gọi blind rồi vá).

Ngoài whitelist không đụng gì: không sửa fixture, DTO, pure reader/test/report03, file tái dùng, launcher, guard, policy, M9 service/schema/tracker. Không xóa/move file, không chạy git.

## 3. SQL units

**COMMON13 (`M0013_COMMON`, 52 câu)**
- **Registry, chủ CSDL seed, app chỉ đọc:**
  - `master.nguon_instance`.
  - `master.nguon_profile`: UNIQUE(instance, ref) và (instance, ref, SHA); bất biến.
  - `master.nguon_pham_vi`.
  - `master.nang_luc_nguon`: UNIQUE NULLS NOT DISTINCT(actor, instance, ref, SHA, action, PN đích); `SOURCE_MAP` ⇔ có PN đích. Chỉ thêm hoặc thu hồi, không UPDATE. RLS chỉ cho thấy dòng của chính phiên.
  - `master.nguon_master_noi_dung`, `master.nguon_su_kien_do_luong`: khóa gồm instance + profile ref/SHA + declaration + payload SHA.
- **Raw:**
  - `giao_tiep.tep_tiep_nhan`: object key = `m0-raw/<sha>`, UNIQUE(instance, raw SHA), integration-only, app không có quyền.
  - Nội dung `kho.anh_chup_nguon`: UNIQUE(instance, profile, SHA, bundle digest).
  - `kho.anh_chup_nguon_vai_tro`: vai trò có mặt có FK composite tới raw; vai trò vắng phải ghi lý do, không có hash.
- **Biên nhận capture + occurrence mỏng:** `giao_tiep.lan_tiep_nhan_nguon`, UNIQUE(instance, `CAPTURE`, client_key), capture H NOT NULL.
- **Dòng nguồn:** `kho.ban_ghi_nguon` theo snapshot/vai trò/section/locator; giữ loại JSON + token số lượng; bất biến.
- **Mapping trung tính:** `master.anh_xa_nguon` (WAREHOUSE, instance/profile/MaKho → PN, revision, hiệu lực). Trigger INVOKER chặn DELETE, chỉ cho đóng một lần, chống chồng lấn dưới advisory lock subject, đòi revision = max+1. Ghi cần đồng thời SOURCE_MAP đúng PN đích + CFO V4 + M5 của phiên; chủ CSDL chỉ được seed `ROOT_SEED_DEMO`.
- **Khác:** `giao_tiep.tep_tach_phap_nhan` (derivative theo PN/M5); `kho.bien_nhan_thao_tac` dạng trung tính (module CRM/M1/M2/M5, trigger kiểm actor = phiên có module).
- **Hàm definer** (search_path cố định, REVOKE PUBLIC, GRANT app_web): `master.ktt_nguon_duoc`, `giao_tiep.nguon_tim_lan_nhan` / `nguon_ghi_lan_nhan` (đều kiểm INTAKE rồi mới khóa/tra), `nguon_anh_xa_hien_hanh`, `nguon_doc_lan_nhan` / `nguon_danh_sach_lan_nhan` / `nguon_doc_tep` (cần READ_SOURCE).
- **Không có:** loan/money/M9, `_rls_v13`, UNIQUE raw/profile nuốt lần fetch.

**M5 14 (`M0014_M5`, 24 câu)**
- **Năm bảng typed** theo binding §2: `kho.phieu_kho_danh_tinh`, `phieu_kho_phien_ban`, `phieu_kho_quan_sat`, `phieu_kho_dong_danh_tinh`, `phieu_kho_dong_phien_ban`.
  - FK composite PN/phiếu/content/logical-line/snapshot/source-row/mapping.
  - Ba con trỏ latest / accepted / eligible có FK deferrable cùng PN/phiếu.
  - Trigger: danh tính bất biến; latest chỉ tiến; eligible chỉ là content của accepted ở trạng thái Đã duyệt.
  - Các bảng còn lại chỉ ghi thêm.
- **Hàm definer:**
  - `kho.m5_khoa_phieu`: khóa danh tính, đọc lịch sử repository dưới khóa, phát hiện retarget/xung đột khóa.
  - `kho.m5_ghi_quan_sat`: dedup content, dòng logical ổn định, observation theo biên nhận, kỳ khóa → GIU_CHO, nguồn đảo → eligible NULL, việc V8.
  - `kho.m5_giu_cho_anh_huong`: việc V4.
  - `kho.m5_xem_xet_nguon`: CFO + M5 + V8, kỳ mở, expected pointers; lý do chặn → `KHO_SOURCE_REAPPROVAL_REVIEW`.
- **RLS:** chỉ SELECT theo `ktt_duoc(PN, 'M5')`.

## 4. Quyết định đã áp dụng

- **Lineage:** checksum đúng M0013 full-M9 (`2a2acb81…`) → `LEGACY_FULL_M9_LINEAGE`, kể cả khi DB đã có version sau 13, và giữ nguyên DB. Lịch sử trùng/hụt/sai hình dạng → `MIGRATION_HISTORY`; checksum lạ → `MIGRATION_CHANGED`; vượt chuỗi → `FUTURE_SCHEMA`. CRM12 → 13 → 14; `target=12` chỉ dùng cho lịch sử.
- **Ba grain hash tách nhau:**
  - Capture H `m0-capture/v1` gồm instance, profile {ref, sha}, scope cấu hình (sections sorted), coverage, lỗi báo cáo sorted, và artifacts theo vai trò từ bytes thực. Không có actor/key/time/PN/mapping/review.
  - Reader semantic/request H.
  - Business H `(PN, M5, operation, key)`.
- **Hành vi khóa capture:** cùng key + cùng H → biên nhận cũ, 0 delta. Cùng key, H khác → `CAPTURE_KHAC_NOI_DUNG` (409) trước khi ghi artifact. Key mới, cùng bytes → occurrence mới, dùng lại blob/snapshot/content.
- **Context do máy chủ dựng** từ bytes đã kiểm + registry + mapping hiện hành. PN chỉ lấy từ mapping (`DEMO_PN_A` → `PN_DEMO_A`). Facts đo lường chỉ resolve khi đủ điều kiện pin: master SHA thực, UOM tham chiếu = CAI, có ít nhất một STRING và mọi số lượng non-null là STRING. Sai bất kỳ điều kiện nào → NULL + lý do, không default 1/1, không dùng DVT_QuyDoi. Trình duyệt bị từ chối nếu gửi actor/PN/facts/ratio/PROVEN/duyệt (`M5_CLIENT_AUTHORITY`).
- **Promote** chỉ khi có mapping hiện hành, semantic + request + ngày + trạng thái đều có. Nếu thiếu thì giữ candidate với lý do (`KHO_PN_MAPPING_PENDING`, `KHO_GRAPH_CHUA_DU`, `KHO_CONTEXT_UNRESOLVED`, `KHO_DATE_MISSING`); raw/capture vẫn được giữ.
- **A→B đảo→A:** đảo B làm eligible = NULL ngay. CFO được chấp nhận B (accepted = B, eligible vẫn NULL). A xuất hiện lại → `REAPPEARANCE_HOLD`; chấp nhận A bị chặn.

## 5. Blocker và giới hạn — root cần quyết

1. **Projection core `PHIEU_KHO` vào `kho.chung_tu` chưa làm** (`chung_tu_id`/`chung_tu_dong_id` = NULL; khóa R3 `khoa_nguon_chieu` đã lưu). Lý do: chuỗi mới không có discriminator owner trung tính cho `kho.chung_tu`, mà RLS v11 hiện gán mọi loại khác `HOP_DONG_TEP` cho M1. Ghi PHIEU_KHO lúc này sẽ lộ cho người dùng M1, và contract COMMON không định nghĩa cột này. Cần root chốt DDL owner discriminator trước.
2. **Ảnh hưởng M9/CRM cũ:** chuỗi mặc định không còn cài full-M9 M13, nên:
   - `k2/vay.py`, `/api/m9` và UI M9 sẽ lỗi khi chạy trên DB mới (thiếu bảng M9).
   - `tests/test_m9_k2.py` và `tests/test_crm_k2.py` (assert `PG_SCHEMA_VERSION == 13`, checksum `PG_MIGRATIONS`) sẽ không còn đúng.
   - `tests/test_crm_khoi_dong.py`, vốn mock `schema_version`, có thể vỡ ở cổng lineage mới.
   - DB DEMO hiện có đã cài M13 legacy sẽ bị từ chối; phải dùng DB DEMO mới.

   Tôi không sửa các file này vì ngoài whitelist / vùng M9.
3. **CSDL lưu nhưng không tự tính lại capture H** (contract cấm SHA(jsonb::text); canonical tính ở máy chủ). Một actor có INTAKE dùng SQL trực tiếp có thể ghi H không khớp bytes. Đây là giới hạn trong phạm vi DEMO.
4. **Classifier thuần dùng nguyên:** trước khi có nguồn được chấp nhận, lần thấy lại cùng nội dung bị phân loại `REAPPEARANCE_HOLD` (không có accepted để so). Sau khi CFO chấp nhận thì là `SAME_CONTENT_FRESH_OBSERVATION`.
5. **Request digest phía service khác golden pure** (alias PN đã resolve, claim capture của máy chủ); semantic digest thì bằng golden. Test chỉ assert semantic bằng golden và request khác NULL.
6. **Retarget mapping** đòi quyền trên cả PN cũ (để đóng) lẫn PN mới. Actor DEMO chỉ có một PN nên chỉ có test âm; nhánh ảnh hưởng V4 chưa có actor DEMO dương.
7. **File soát** xlsx mỗi lần xuất ra bytes khác nhau (timestamp openpyxl), nên mỗi lần là một lô bất biến mới. Kỳ khóa chặn xuất mới. Kỳ = `YYYY-MM` của `NgayChungTu`.
8. **Kiểm kê/tồn nguồn:** trả `CHUA_CO_SNAPSHOT_PRODUCER`; không bảng nào được tạo. **L11/link:** trả 501 `M5_L11_CHUA_PHAT_HANH`.
9. **Mẫu DEMO** đọc từ `tests/fixtures/...` có kiểm SHA. `reported_capture_errors` của K07 lấy từ pure context (dữ kiện capture DEMO, không phải authority).
10. **Chưa kiểm lại bằng chạy thật:** cú pháp Python/SQL/JS, định danh PL/pgSQL, thứ tự trigger/RLS, đồng thời hai kết nối, UI thật. Root cần full-read rồi mới release runtime.

Kết thúc CLI để root freeze/full-read/review độc lập. Không tự nghiệm thu M5/V13/33, không mở việc khác.
