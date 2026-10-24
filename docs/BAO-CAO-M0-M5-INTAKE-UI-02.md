# Báo cáo M0–M5 — intake, history, API/UI, sửa 02 (CODE ONLY)

**19/10/2026 · tự báo cáo của coder · CODE ONLY, không chạy gì · CHỜ ROOT freeze/full-read/independent validation.** Đây không phải nghiệm thu. Không có nhãn PASS nào cho M0, M5, L11, UI hay M9. Actual DDL và runtime chỉ được release riêng sau review.

Căn cứ: `docs/GIAO-SUA-M0-M5-INTAKE-UI-02.md` (SHA `43902e6e…6b0e7eb`), ba review final (`REVIEW-M0-M5-MIGRATION-01`, `-SERVICE-01`, `-HTTP-UI-01`), contract `M0-M5-SQL-VA-FIXTURE-01.md`, handoff01. Baseline 210 file đã đóng băng có manifest `c36773ae…2b89a`.

## 1. Trạng thái thực thi

| Hạng mục | Kết quả |
|---|---|
| Import/compile/chạy product, test, SQL/PG, HTTP, GUI, launcher, process, network | **UNRUN**. Không dùng Bash hay công cụ thực thi nào; chỉ Read/Glob/Grep/Edit/Write |
| `tests/test_m0_m5_migrations.py` | **UNRUN**: 6 test tĩnh, 6 test PG (chạy khi có `KHO_PG_DSN_TEST`) |
| `tests/test_m5_k2.py` | **UNRUN**: 8 test thuần, 22 test PG |
| `tests/test_m5_http.py` | **UNRUN**: 2 test PG/HTTP |
| PASS / FAIL / ERROR / SKIP | 0 / 0 / 0 / 0 — chưa có lần chạy nào. Kết quả 11 pure-test PASS của root thuộc candidate01, **không** chuyển sang bản này |
| Số câu lệnh và checksum COMMON13 / M5 14 mới | **Chưa tính** (cần Python). Định nghĩa đã đổi so với pin candidate01 (`b396ce05…`, `31f3db6a…`); root tính và pin lại khi freeze |

## 2. File đã sửa (16/17 target trong whitelist)

Đã sửa: `ha_tang/pg_migrations.py`, `ha_tang/postgres.py`; trong `k2/`: `quyen.py` (không đổi thêm ở bản 02), `nguon_chung.py`, `kho_so_luong.py`, `m5_demo.py`, `crm_khoi_dong.py`, `crm_demo.py`; `giao_dien/server.py`; trong `assets/`: `index.html`, `app.js`, `style.css` (không đổi thêm ở bản 02); `tests/test_m0_m5_migrations.py`, `tests/test_m5_k2.py`, `tests/test_m5_http.py`; và **mới** `docs/BAO-CAO-M0-M5-INTAKE-UI-02.md`.

Còn `k2/lien_ket_chung.py`: không cần sửa nên giữ nguyên. Service M5 không còn gọi `tim_bien_nhan`/`ghi_bien_nhan` cho M5, vì biên nhận M5 nay do hàm định nghĩa trong CSDL dẫn xuất.

Giữ nguyên bytes: M0001–M0012, `M0013` full-M9 lịch sử cùng các helper của nó, report01, pure reader, các fixture, DTO, contract và review. Không xóa hay di chuyển file nào. Không chạy git, pip, không đổi config/policy.

## 3. Các finding đã sửa trong code (chưa kiểm runtime)

| Finding | Đã làm |
|---|---|
| **S01/S02/SR1** — writer free-JSON | **Bỏ** hẳn `nguon_ghi_lan_nhan(jsonb)` và `m5_ghi_quan_sat(jsonb)`. Thêm bảng `giao_tiep.stage_tin_cay` bất biến: trigger INVOKER chỉ cho **đúng chủ bảng** ghi (`master.la_chu_bang`, so `relowner` với `current_user`, không xét membership hay GUC), và actor phải là phiên hiện tại. App và vai trò cũ không có quyền nào trên bảng này. Consumer `giao_tiep.nguon_tieu_thu_capture(stage, H)` và `kho.m5_tieu_thu_quan_sat(stage, H)` đọc mọi fact từ stage, kiểm lại actor, quyền INTAKE hiện hành, khóa namespace và biên nhận; với bundle đã có, so lại từng vai trò thật (`BUNDLE_XUNG_DOT`) và kiểm envelope khớp vai trò. Intake chạy **một giao dịch** trên kết nối chủ đã cấu hình, theo thứ tự: danh tính → INTAKE → khóa + tra biên nhận/H → blob → reader → khóa logic + lịch sử → stage → consumer capture → consumer typed/core |
| **Biên nhận M5** | Thêm trigger INVOKER `bien_nhan_m5_chi_chu`: chỉ chủ bảng (tức consumer/hàm định nghĩa trong cùng giao dịch) mới tạo được biên nhận M5. App không prefill, retag hay sửa được. Biên nhận CRM/M1/M2 giữ hành vi cũ. Review/mapping/file: hash yêu cầu do CSDL tính, quyền hiện hành kiểm **trước** replay |
| **S03** — đảo thứ tự khóa | Thứ tự chung: namespace capture → hàng mapping (`FOR SHARE`/`FOR UPDATE`) → advisory logic phiếu → hàng danh tính `FOR UPDATE`. Review và file đều theo advisory → hàng; mapping theo subject → hàng mapping → logic |
| **S04/SR4** — stale A | `m5_xem_xet_nguon` chỉ chấp nhận khi quan sát được chọn **là latest**; cộng với blocklist và lịch sử KNOWN. B đảo vẫn chấp nhận được (accepted = B, eligible NULL). A cũ lấy lại sau đó vẫn bị `KHO_SOURCE_REAPPROVAL_REVIEW` |
| **S05** — master có bảng nhưng thiếu lịch sử | `_current_state`: có master mà thiếu `schema_migrations` nhưng có bảng → từ chối; có `schema_migrations` mà thiếu marker → từ chối. Chỉ DB trống thật mới khởi tạo |
| **S06** — `migrations=` tùy chỉnh | Thêm `kiem_chuoi_lich_su`: từng phần tử phải trùng checksum M000k mặc định (vị trí 10 chấp nhận đúng tiền thân M0010 đã liệt kê), tối đa 12 phần tử |
| **S07** — mapping CFO bị chặn ở helper | Mọi ghi mapping qua `kho.m5_anh_xa_v4` (definer của chủ) nên helper chạy với quyền chủ. Trigger vẫn kiểm actor: ĐỒNG THỜI SOURCE_MAP đúng PN đích + CFO V4 + M5. App chỉ còn quyền đọc. Retarget đóng bản cũ (yêu cầu quyền trên PN cũ), mở việc V4, không chuyển danh tính |
| **S08** — lộ metadata nguồn | Bật RLS theo năng lực nguồn (`ktt_nguon_co_nang_luc`) trên instance/profile/scope. Master catalog và facts đo lường chỉ máy chủ đọc được. `REVOKE ALL` cho `app_ke_toan`/`app_cong_ai`/`app_doc` (và app_web) trên **chính** các object mới. Policy kế thừa của vai trò cũ trên `chung_tu`/`chung_tu_dong`/`lo_xuat`/`viec_can_duyet` loại M5 trừ khi có quyền M5 hiện hành |
| **SR6** — thiếu core PHIEU_KHO | Thêm cột `kho.chung_tu.module_nghiep_vu`; backfill HOP_DONG_TEP → CRM, **mọi hàng cũ khác → M1, kể cả PHIEU_KHO cũ**; sau đó NOT NULL + CHECK CRM/M1/M5. Trigger INVOKER suy chủ cho hàng mới (PHIEU_KHO → M5), từ chối module do caller khai và cấm đổi chủ. Chỉ chủ bảng ghi được M5; M5 bắt buộc tiền/tiền tệ/chiều NULL và trạng thái DANG_XU_LY. `no_minor`/`co_minor` bỏ NOT NULL nhưng **giữ DEFAULT 0**; trigger cha-con giữ dòng không phải M5 luôn NOT NULL, dòng M5 phải NULL Nợ/Có/đơn giá/thuế/TK. Consumer typed tạo core header + dòng cho mỗi content mới với khóa R3 sau dedup; typed có FK composite NOT NULL tới core (PN/header/module, header/dòng/STT). Policy app_web theo PN + chủ do DB suy |
| **SR2/SR3/I4** — file soát | Pha 1 `m5_file_bat_dau`: quyền FILE trước tra biên nhận, khóa, expected, kỳ mở, trả snapshot nhất quán. Pha 2 máy chủ dựng xlsx (text/formula-safe), ghi độc quyền `m5-xuat/<sha>.xlsx` rồi đọc lại kiểm, ghi stage FILE_SOAT. Pha 3 `m5_file_tieu_thu` dẫn xuất lô + biên nhận `(PN, M5, FILE_SOAT, key)`. Trigger lô INVOKER: lô M5 chỉ do chủ bảng ghi, đúng đường dẫn/stage/mục đích, bất biến. Tải về kiểm module, mục đích, mẫu đường dẫn, SHA và độ dài. UI → HTTP → service truyền khóa + expected |
| **SR5** — bootstrap không additive | `crm_demo`: khởi tạo người dùng/quyền **một lần** (marker, hoặc DB DEMO cũ đã có dữ liệu); không UPSERT, không ghi đè mảng; seed ban đầu **không cấp M9**. `m5_demo`: actor/quyền/năng lực chỉ khởi tạo một lần; mở lại không cấp lại năng lực đã thu hồi |
| **SR7/I2** — `reported_errors` | Thêm `kiem_ma_loi`: vắng = []; hiện diện phải là list mã, null/bool/0/chuỗi/object đều bị từ chối trước H. Server không còn `or []`. Coverage hiệu lực tách khỏi claim gốc (thiếu vai trò bắt buộc → PARTIAL), lưu riêng `coverage_hieu_luc` và đưa vào context reader |
| **I1** — phản hồi cũ vẫn render | Thêm epoch: đổi vai, lọc hay mở phiếu khác thì tăng epoch và xóa cache/panel/nút ngay. Mọi phản hồi state/chi tiết/raw/file của epoch cũ bị bỏ (`m5Tai` cũng không lưu bytes cũ) |
| **I3** — bộ chọn vai | Bộ chọn và đổi vai M5 chỉ gồm đúng 8 login của registry (`dang_nhap_m5`) giao với người dùng đang hoạt động; vai khác bị trả `DANH_TINH_M5` |
| **I5** — không nhận được file thật | Thêm form chọn tệp native/master, nguồn/phạm vi (từ năng lực), coverage, danh sách mã lỗi, khóa có thể giữ để nhận lại. `FileReader.readAsArrayBuffer` → base64 nguyên bytes; server tự hash, kiểm độ dài và vai trò, không nhận đường dẫn/URL/facts |
| **Oracle test** | Sửa: t06 review dương trên latest; t08 stale A là âm; t19 so sentinel chuẩn non-M5 (HD_MUA/HD_BAN/SAO_KE/dòng/đề xuất 331/liên kết/công nợ) cùng số core M5 đúng; thêm test forgery (stage/biên nhận/lô/core/mapping/metadata) và một ca dương consume stage hợp lệ của chủ; file idempotent/expected/cells; kỳ khóa 0 delta nghiệp vụ; seed mở lại giữ quyền/thu hồi |

## 4. Giới hạn và điểm root cần biết (không coi là đã đóng)

1. **Chưa chạy gì**, nên mọi kết luận ở §3 là thiết kế/mã tĩnh. Cú pháp Python/SQL/JS, định danh PL/pgSQL, thứ tự trigger/RLS, đồng thời và hành vi UI đều chưa được kiểm. Test race có `lock_timeout`/`statement_timeout` và kiểm worker còn sống, nhưng chưa có observer nhân quả độc lập. Epoch UI (I1) và file picker (I5) **chưa có test tương tác trình duyệt**; test HTTP chỉ kiểm tài nguyên được phục vụ và API.
2. **Gốc tin cậy của stage là kết nối chủ bảng** (admin DSN cục bộ đã kiểm loopback, đích thực và đúng owner). CSDL không tự tính lại reader/H (contract cấm `SHA(jsonb::text)` cho digest nguồn). Hash yêu cầu nghiệp vụ trong CSDL dùng `jsonb::text` chỉ để chống trùng nội bộ. Không có admin DSN thì intake/file trả `M5_CHU_CHUA_CAU_HINH`; route đọc vẫn chạy.
3. **Ảnh hưởng ngoài whitelist** (không sửa; root cần quyết):
   - `tests/test_crm_k2.py`, `tests/test_m9_k2.py`, `tests/test_crm_khoi_dong.py` còn kỳ vọng schema 13, các checksum cũ, M9 trong seed CRM, chuỗi `migrations=` tùy chỉnh (nay bị `MIGRATION_TUY_CHINH` từ chối sớm), và mock cổng `max(version)`.
   - M9 runtime (`vay.py`, `/api/m9`) không có schema trong chuỗi mặc định.
   - DB DEMO cũ có M13 legacy bị từ chối.
4. Chủ M5 suy từ `PHIEU_KHO` cho **mọi** INSERT mới (theo handoff02). Nếu còn caller cũ (ngoài repo) tạo PHIEU_KHO kiểu M1, caller đó sẽ bị chặn. Hàng PHIEU_KHO cũ vẫn là M1.
5. `nhat_ky.su_kien` (không có RLS ở prefix) vẫn chứa sự kiện M5 và vai trò cũ đọc được như trước. Bản này không đổi quyền object cũ.
6. Retarget dương cần actor có quyền trên cả hai PN; ma trận DEMO không có actor như vậy, nên chỉ có test âm.
7. L11/M2 bridge, producer tồn/kiểm kê và triển khai nguồn thật vẫn là phụ thuộc của gói sau: API trả 501/“chưa có producer”, không giả số đã khớp, capacity hay tồn.

Kết thúc CLI để root freeze/full-read/kiểm độc lập. Không tự nghiệm thu M0/M5/L11/33 hoặc M9, không mở việc khác.
