# Báo cáo bàn giao CRM-01 DEMO — hợp đồng & lịch thu trên K2 PostgreSQL

Ngày: 19/10/2026 · Claude Code sửa chính, Codex kiểm độc lập · Theo `GIAO-VIEC-CRM-KE-TOAN-33.md`, lượt sửa 02 (`CRM-01-YEU-CAU-SUA-REVIEW-02.md`) và **lượt sửa 03 (`CRM-01-YEU-CAU-SUA-REVIEW-03.md` + `CRM-01-BO-SUNG-BAN-GIAO-NUT-MO-DEMO.md`)**.
**Trạng thái sau lượt 06: stdout JSON máy cho PowerShell 5.1 thuần ASCII (Unicode thoát), log UTF-8 giữ nguyên; targeted unit đạt; Windows 5.1/nút/GUI NOT_RUN; chưa review độc lập.**
**Trạng thái sau lượt 05: chuỗi cấu hình idempotent + interface runtime app (`runtime.local.json`) + bộ chọn runtime; self-test thuần/stub/PG đã chạy; launcher/host/GUI NOT_RUN; chưa review độc lập.**
**Trạng thái sau lượt 04 (khởi động DEMO): validator DSN chung + helper bảo đảm cluster đã có; self-test thuần/stub + PG đã chạy; host/launcher/cold-start/GUI NOT_RUN; chưa review độc lập.**
**Trạng thái sau lượt 03: code + self-test (unit và PostgreSQL thật) đã chạy; GUI, nút mở thật trên host, restart tiến trình CHƯA kiểm; CHƯA qua review độc lập — Claude không tự nghiệm thu.** Không phải M3/M1/V13/toàn 33 hoàn thành, không phải tích hợp production #6.

## 0000. Lượt sửa 06 — JSON máy qua Windows PowerShell 5.1 (theo `CRM-01-YEU-CAU-SUA-REVIEW-06.md`)

**Lỗi:** PowerShell 5.1 giải mã stdout của tiến trình con bằng codepage console 437 / OutputEncoding 20127. JSON UTF-8 thô có đường dẫn tiếng Việt bị hỏng sau `ConvertFrom-Json`. Hệ quả: `pythonpath` sai → `RUNTIME_THIEU_DRIVER`, server không thấy `kho_tri_thuc`.

**Sửa (không đổi interface/giá trị JSON, validator, cluster, CRM/schema/M1):**
- Rà mọi JSON máy mà PowerShell đọc từ stdout: chỉ có `tools/chon_runtime.py` (runtime) và `tools/chuan_bi_crm_demo.py` (trạng thái bootstrap). Cả hai giờ in `json.dumps(..., ensure_ascii=True)`: stdout thuần ASCII, Unicode thoát `\uXXXX`, nên `ConvertFrom-Json`/`json.loads` phục hồi nguyên chuỗi.
- `tools/kiem_runtime.py` do Python đọc và vốn đã ASCII, không đổi.
- Tệp log/trạng thái trên đĩa giữ UTF-8 có chữ Việt: `logs/runtime-*.json` và `crm-demo/chuan-bi-*.json`.
- Không đổi codepage/encoding global, không đổi `start-web.ps1`, không hardcode đường dẫn.
- `chon_runtime.main` truyền `_chay_that` lúc gọi, để test thay được probe.

**Self-test lượt 06 (chỉ targeted unit; không chạy PowerShell/launcher/PG/HTTP):**
| Lệnh | Pass | Fail | Setup/Error | Skip |
|---|---:|---:|---:|---:|
| `test_crm_khoi_dong.py` | 35 | 0 | 0 | 0 |
| `test_crm_phan_tich.py` | 20 | 0 | 0 | 0 |

Hai ca mới gọi `main()` thật (probe/bootstrap là stub), lấy đúng stdout rồi mô phỏng transport byte → giải mã cp437 và ascii → `json.loads`:
- **`chon_runtime`:** root, python, hai thư mục phụ thuộc và guard đều có dấu + khoảng trắng; repo thật cũng có dấu.
  - stdout encode ASCII được; sau cả hai kiểu giải mã, `pythonpath` đúng chuỗi mong đợi và cả 4 đường dẫn tồn tại.
  - Oracle nhân quả: cùng nội dung in kiểu cũ (UTF-8 thô) qua cp437 cho `pythonpath` sai.
  - Log UTF-8 chứa nguyên "Phần mềm kho tri thức".
- **`chuan_bi_crm_demo`:** thông điệp lỗi Unicode (có dấu, gạch dài, ngoặc kép cong) phục hồi đúng sau cp437/ascii; tệp trạng thái UTF-8 giữ nguyên thông điệp.

**Chưa kiểm:** Windows PowerShell 5.1 thật, nút CMD mặc định mở lần đầu/mở lại, xuất file, restart — root chạy lại sau terminal. **GUI chưa bấm.** Không chạy lại suite SQL/web vì lượt này không đổi các phần đó.

## 000. Lượt sửa 05 — chuỗi cấu hình idempotent + runtime nút mặc định (theo `CRM-01-YEU-CAU-SUA-REVIEW-05.md`)

Không đổi CRM core/parser/M1/migration 1–12; giữ validator, role/endpoint và helper cluster của lượt 04.

### 000.1 P1 — JSON hợp lệ bị chặn khi bootstrap kiểm lần hai
- Nguyên nhân: `doc_ket_noi` trả chuỗi đã chuẩn hóa có `hostaddr`, rồi `chuan_bi` kiểm lại và từ chối `hostaddr`.
- Sửa: `chuan_hoa_dsn` nhận `hostaddr` **chỉ khi** là đúng literal loopback mà host chuẩn hóa thành (127.0.0.1→127.0.0.1, localhost→127.0.0.1, ::1→::1). hostaddr remote, nhiều địa chỉ, lệch host, hoặc hostaddr không kèm host vẫn bị từ chối như cũ.
- Chuỗi đầu ra dựng theo **thứ tự khóa cố định**, nên `chuan_hoa_dsn(kq["conninfo"]) == kq`.
- Vòng kiểm lại trong `chuan_bi`/server vẫn chạy, không tin dict của caller.
- Thiếu driver psycopg → `RUNTIME_THIEU_DRIVER` (validator, bootstrap, server), không còn ImportError/đứt HTTP.

### 000.2 Interface runtime app cho nút mặc định (root/Codex cài sau review)
**Tệp `<DataRoot>\crm-demo\runtime.local.json`** (không chứa DSN/mật khẩu/token; tách khỏi `ket-noi.local.json` và `cum-pg.local.json`):
```json
{"phien_ban": 1,
 "python": "<đường dẫn TUYỆT ĐỐI python.exe của runtime app (vd Python 3.13.14 root copy)>",
 "duong_dan_phu_thuoc": ["<thư mục TUYỆT ĐỐI chứa psycopg[binary], tzdata, openpyxl… (nếu không nằm sẵn trong site-packages của python đó)>"],
 "thu_muc_khoi_dong": "<thư mục TUYỆT ĐỐI chứa sitecustomize.py = guard giữ file do root quản lý (tùy chọn)>"}
```
- Khóa khác → `RUNTIME_CAU_HINH_SAI`. Python không tuyệt đối hoặc không tồn tại → `RUNTIME_PYTHON_KHONG_CO`. Thư mục phụ thuộc không có → `RUNTIME_PHU_THUOC_KHONG_CO`. Thư mục khởi động thiếu `sitecustomize.py` → `RUNTIME_KHOI_DONG_KHONG_CO`.
- **Bộ chọn `tools/chon_runtime.py`** (chỉ stdlib; launcher gọi bằng Python tìm được đầu tiên):
  - Thứ tự ứng viên: `-PythonExecutable` tường minh → `python` trong runtime.local.json → Python kèm workspace → `python` trên PATH. Tường minh hoặc runtime.local.json thì chỉ dùng đúng Python đó, không rơi về ứng viên khác.
  - Mỗi ứng viên được probe thật bằng `tools/kiem_runtime.py` chạy dưới chính nó, với đúng môi trường con.
  - Python 3.11+ có openpyxl thì app chạy được.
  - CRM cần thêm cả bốn điều kiện: không isolated (`-I`/`-E`), thư mục phụ thuộc có trong `sys.path`, guard nạp từ đúng thư mục (nếu cấu hình), và import psycopg thật được.
  - Thiếu một điều kiện → `crm=false` với mã `RUNTIME_ISOLATED` / `RUNTIME_PHU_THUOC_KHONG_NAP` / `RUNTIME_GUARD_KHONG_NAP` / `RUNTIME_THIEU_DRIVER`. Không có runtime.local.json và không ứng viên nào đủ → `RUNTIME_CHUA_CAU_HINH`. Không có Python dùng được → `RUNTIME_KHONG_CO_PYTHON` / `RUNTIME_KHONG_DUNG_DUOC` (launcher dừng có mã).
  - Mỗi lần chọn ghi một tệp trạng thái mới `<root>\logs\runtime-<UTC>-<pid>.json`.
- **Môi trường con dùng chung** cho probe, bước chuẩn bị CRM và server web:
  - Sao từ môi trường caller; `PYTHONPATH = <repo>\src;<phụ thuộc…>;<thư mục khởi động>`. PYTHONPATH riêng của caller không được gộp, để không phụ thuộc môi trường kiểm thử.
  - `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`.
- **`start-web.ps1`:**
  - Dùng python + PYTHONPATH do bộ chọn trả về cho cả bước chuẩn bị CRM và server.
  - Đặt/khôi phục môi trường bằng `Set-KttChildEnv` / `Restore-KttEnv`; môi trường caller được trả lại sau mỗi lần spawn.
  - Bước CRM chỉ chạy khi `crm=true` và không phải kho thật; `crm=false` thì in mã rõ và vẫn mở các chức năng khác.
  - Không còn đặt PYTHONPATH chỉ `src`. `MỞ BẢN DEMO.cmd` không đổi; người dùng không cần gõ lệnh hay đặt biến môi trường.
- Root/Codex làm: copy runtime + dependency, cài guard, tạo runtime.local.json; không cài package global, không sửa `python._pth`/bundle.

### 000.3 Self-test lượt 05 (guard + no-bytecode; DB/role/thư mục giữ lại)
| Lệnh | Pass | Fail | Setup/Error | Skip | Ghi chú |
|---|---:|---:|---:|---:|---|
| `test_crm_khoi_dong.py` | 33 | 0 | 0 | 0 | 21 ca lượt 04 giữ nguyên + 12 ca mới |
| `test_crm_phan_tich.py` | 20 | 0 | 0 | 0 | |
| helper PG `test_crm_k2.py` | 22 | 0 | 0 | 1 | skip t17 (`app_ke_toan` không có — không tính đạt) |
| `test_web.py` | 22 | 1 | 0 | 0 | fail guard đã biết |

Ca mới:
- **Idempotent:** 5 dạng DSN gốc → chuẩn hóa lại cho kết quả giống hệt. Năm ca hostaddr sai bị từ chối.
- **Chuỗi thật raw → JSON → `doc_ket_noi` → `chuan_bi` → connector stub:**
  - Môi trường giả đặt PGHOSTADDR/PGSERVICE/PGPORT; không mock bước kiểm.
  - Lần 2 dùng lại đầu ra chuẩn hóa ghi vào JSON.
  - 4 lần connect đều 127.0.0.1:5432/DB đúng; seed 2 lần.
- **Env → server → connector:** cả DSN gốc và DSN đã chuẩn hóa, mỗi lần đúng 1 connect tới đích chuẩn hóa.
- **Thiếu driver:** `RUNTIME_THIEU_DRIVER` ở validator, bootstrap và server.
- **Runtime (stub probe ghi argv/env):**
  - Hợp đồng tệp (6 ca âm + dương).
  - Môi trường con đúng thứ tự, không sửa môi trường caller.
  - runtime.local.json đủ → một probe, argv/expect đúng, PYTHONPATH trả về = PYTHONPATH của probe.
  - Năm kiểu thiếu khả năng → `crm=false` với đúng mã, không rơi về Python khác. Python 3.10 → không chạy app. Probe lỗi → `RUNTIME_PROBE_LOI`.
  - `-PythonExecutable` chỉ dùng đúng Python đó.
  - Không cấu hình: thử lần lượt workspace → PATH; không ứng viên đủ → `RUNTIME_CHUA_CAU_HINH`; không có Python → `RUNTIME_KHONG_CO_PYTHON`.
  - Kiểm tĩnh launcher.
- **Probe thật (`tools/kiem_runtime.py` dưới Python hiện tại):**
  - Thư mục phụ thuộc có/không trên `sys.path`.
  - `-I` → isolated, PYTHONPATH bị bỏ qua → `RUNTIME_ISOLATED`.
  - Thư mục không có `sitecustomize` → `RUNTIME_GUARD_KHONG_NAP`.
  - Không tạo sitecustomize lạ trong tiến trình con, để không che guard.

### 000.4 Chưa kiểm / hạn chế lượt 05
- **NOT_RUN:** launcher thật, nút mặc định trên máy chưa cài runtime / đã cài runtime, PowerShell `Set-KttChildEnv`/`Restore-KttEnv` (chỉ kiểm tĩnh), cold-start, OS restart. **GUI chưa bấm.**
- Probe thật chỉ chạy dưới Python của môi trường kiểm (có driver); ca "Python kèm workspace 3.12 thiếu psycopg" và "PATH không userbase" chỉ kiểm qua stub.
- Guard chỉ được xác minh là đã nạp từ đúng thư mục (`sitecustomize.__file__`), không kiểm nội dung hay chức năng của guard.
- Python kèm workspace vẫn là ứng viên khi không có runtime.local.json; nó sẽ mở app nhưng báo `RUNTIME_CHUA_CAU_HINH` cho CRM.

## 00. Lượt sửa 04 — khởi động DEMO (theo `CRM-01-YEU-CAU-SUA-REVIEW-04.md`, `REVIEW-CRM-KHOI-DONG-03.md`, `CRM-03-TAI-SU-DUNG-KHOI-DONG-PG.md`)

SQL/parser/HTTP/M1 lượt 03 đã đạt ở review độc lập; lượt 04 **không đổi** migration (M0001–M0012 giữ nguyên statement/checksum, không thêm M0013), parser, M1 hay CRM core.

### 00.1 Thay đổi
| Việc | Sửa | File |
|---|---|---|
| 9 FAIL validator (E01–03, C04, D03–05, S02–03) | **Một lớp chuẩn hóa/kiểm DSN dùng chung** (`chuan_hoa_dsn`, `kiem_cap`), áp cho tệp JSON, `chuan_bi` trực tiếp và biến môi trường server, chạy TRƯỚC mọi connect/CREATE/migrate/seed. Quy tắc: (1) chỉ nhận các khóa host/port/dbname/user/password/sslmode/connect_timeout/application_name; service, servicefile, hostaddr, options… bị từ chối, không đọc tệp service. (2) host, port, dbname bắt buộc tường minh; thiếu → `KET_NOI_THIEU_ENDPOINT`, không lấy PGHOST/PGHOSTADDR/PGPORT/PGSERVICE. (3) host chỉ là một trong 127.0.0.1 / localhost / ::1, không multihost/multiport. (4) Chuỗi dùng để kết nối được dựng lại có `hostaddr` loopback tường minh (localhost → 127.0.0.1) nên biến môi trường libpq không đổi được đích sau khi kiểm. (5) app/admin phải cùng (hostaddr, port, dbname) → `KET_NOI_KHAC_ENDPOINT` / `KET_NOI_KHAC_DB`. | `k2/crm_khoi_dong.py` |
| Đích thực + role không phải chủ | Sau khi kết nối: so (địa chỉ máy chủ, cổng, OID DB) giữa kết nối quản trị và ứng dụng. `kiem_role_ung_dung` thêm điều kiện: không là (thành viên của) chủ DB, schema `master/kho/nhat_ky/bao_mat` hay bảng trong đó → `ROLE_UNG_DUNG_LA_CHU`. Mọi cột có alias: kết nối `dict_row` của server từng gộp cột trùng tên — PG self-test phát hiện, đã sửa. | `k2/crm_khoi_dong.py` |
| Server env | `_crm_ket_noi` dùng cùng validator. Chỉ DB `kho_crm_demo*`; DB fixture `kho_test_*` chỉ khi tiến trình đặt rõ `KTT_CRM_CHO_PHEP_DB_KIEM_THU=1`. Có admin mà thiếu app → lỗi. Lỗi kết nối/kiểm được bọc thành mã sạch (`PG_KHONG_KET_NOI`, `CRM_KIEM_KET_NOI_LOI`), không còn đứt HTTP. | `giao_dien/server.py` |
| Cold-start cluster đã có | **`ha_tang/pg_cum.py`**: định danh runtime/data dir. Mặc định theo bố cục thư mục cha `<cha>/var/postgresql16-16.15-runtime/bin/pg_ctl.exe` + `<cha>/var/postgresql-ktt-16/data`, PG_VERSION 16, 127.0.0.1:5432, SHA256 pg_ctl `bed9ec96…e0a1`. Có thể ghi đè bằng tệp không bí mật `<DataRoot>/crm-demo/cum-pg.local.json`, tách khỏi tệp credentials. Luồng: khóa tệp theo danh tính cluster (chờ có hạn, tệp khóa giữ lại) → `pg_ctl status -D`: 0 = chạy, 3 = dừng, 4 = không truy cập, mã khác = không rõ → dừng. Đang chạy: PID status = PID nghe cổng, exe = postgres.exe của runtime, `-D` = đúng data dir (so đường dẫn chuẩn hóa) → dùng lại. Dừng + cổng trống: `pg_ctl start -D … -l <log mới> -w -t 60 -o "-h 127.0.0.1 -p 5432"` (ẩn cửa sổ). Lỗi/timeout: kiểm status + định danh lại một lần, không spawn lại. **Không** stop/kill/initdb/cài/đăng ký service/xóa pid-lock/sửa tệp cluster. Lỗi riêng: `CUM_O_DIA_VANG`, `CUM_SAI_RUNTIME`, `CUM_KHONG_TRUY_CAP`, `CUM_PG_VERSION`, `CUM_TRANG_THAI_KHONG_RO`, `CUM_KHONG_XAC_MINH`, `CUM_CONG_BI_CHIEM`, `CUM_KHONG_KHOI_DONG`, `CUM_DANG_BAN`. Log start: `<root>/logs/pg-start-<UTC>-<pid>-<nonce>.log`, tạo độc quyền. | `ha_tang/pg_cum.py` |
| Thứ tự trong tool | `chay`: kho thật → bỏ qua hoàn toàn (không đọc cấu hình, không đụng cluster) → kiểm cấu hình kết nối (cả hai DSN) → đích cấu hình phải = endpoint cluster (`KET_NOI_KHONG_DUNG_CUM`) → bảo đảm cluster → mới tạo DB/migrate/seed. Không cấu hình → mã 2, không đụng cluster. Lỗi cluster → không bootstrap. | `tools/chuan_bi_crm_demo.py` |
| Launcher | Console hiện thêm kết quả cluster (`DUNG_LAI`/`DA_KHOI_DONG`). Các phần lượt 03 giữ nguyên: log riêng, xác minh PID trước khi dừng server web cũ, bỏ qua bước PG khi `environment = "that"`. `MỞ BẢN DEMO.cmd` không đổi. | `start-web.ps1` |

### 00.2 Self-test lượt 04 (guard không xóa + no-bytecode; DB/role/thư mục giữ lại)
| Lệnh | Pass | Fail | Setup/Error | Skip | Ghi chú |
|---|---:|---:|---:|---:|---|
| `test_crm_khoi_dong.py` (mới, **thuần/stub**) | 21 | 0 | 0 | 0 | 0 mạng, 0 SQL thật, 0 pg_ctl/launcher thật; connector là bẫy/kết nối giả, hệ điều hành là `StubHDH` |
| `test_crm_phan_tich.py` | 20 | 0 | 0 | 0 | DSN giả cập nhật có port tường minh |
| helper PG `test_crm_k2.py` | 22 | 0 | 0 | 1 | skip t17 (`app_ke_toan` không có — không tính đạt). Hai lần chạy giữa chừng có 1 error t15: lần đầu do dict_row gộp cột (lỗi product thật, đã sửa), lần sau do chèn kiểm tra trực tiếp để lộ ngoại lệ |
| `test_web.py` / `test_nghiem_thu_bridge.py` | 22 / 21 | 1 / 0 | 0 | 0 | fail guard đã biết |

Ca thuần/stub đã có:
- **E01–E03:** môi trường giả đặt PGHOST/PGHOSTADDR/PGPORT/PGSERVICE; DSN thiếu host, thiếu port hoặc có service bị từ chối. Control: DSN đủ endpoint dựng lại có `hostaddr`.
- **Khóa/host không hỗ trợ:** hostaddr, multihost, multiport, remote, options, servicefile, sai DB, cổng sai, chuỗi hỏng đều bị từ chối. Control loopback 127.0.0.1/localhost/::1/URL, và DB fixture với tiền tố truyền rõ.
- **C04:** khác cổng, khác host loopback, khác DB đều bị từ chối, cả qua tệp. Control: localhost ≡ 127.0.0.1.
- **D03–D05 + admin remote:** 0 lần connect, 0 seed. Control dương: kết nối giả → `SAN_SANG`, kết nối bằng chuỗi chuẩn hóa. Sau khi kết nối: OID DB khác → `KET_NOI_KHAC_DB`; chủ bảng/chủ DB → `ROLE_UNG_DUNG_LA_CHU`; superuser → `ROLE_UNG_DUNG_SAI`.
- **S02/S03:** remote, DB không phải DEMO, `kho_test_*` khi chưa có cờ, thiếu endpoint, khác cổng → bẫy connector 0 lần. Control: DEMO hợp lệ; fixture có cờ; thiếu cấu hình → `cau_hinh=false`.
- **Cluster:**
  - Sai hash/thiếu runtime/thiếu data/PG_VERSION/ổ vắng → không chạy lệnh nào.
  - Status 4/1/2/timeout → không start.
  - Đúng cluster đang chạy → `DUNG_LAI`, không log start.
  - Năm ca không xác minh được (PID nghe khác, runtime khác, data dir tiền tố chung, thiếu `-D`, không nghe cổng) → dừng, chỉ có lệnh status.
  - Cổng bị chiếm → không start.
  - Dừng + cổng trống → đúng một start với argv chính xác, log mới, log cũ nguyên vẹn, hai lần chạy hai log khác nhau.
  - Start lỗi nhưng server lên → `DA_KHOI_DONG`; start hỏng → `CUM_KHONG_KHOI_DONG`; cả hai không spawn lại.
  - Hai lần mở đồng thời → đúng một start (một `DA_KHOI_DONG`, một `DUNG_LAI`).
  - Không argv nào chứa stop/kill/initdb/register/restart/password/dsn.
- **Tool:**
  - Kho thật → 0 lần gọi cấu hình/cluster.
  - Chưa cấu hình / cấu hình sai / sai cluster → không đụng cluster, không bootstrap.
  - Lỗi cluster → không bootstrap.
  - Cluster dừng hoặc đang chạy → bootstrap đúng một lần với chuỗi đã chuẩn hóa.

### 00.3 Chưa kiểm / hạn chế thật lượt 04
- **NOT_RUN trên host:** chưa chạy `pg_ctl` thật, launcher, nút mở, cold-start, mở lại sau OS restart. Các lệnh hệ điều hành thật trong `pg_cum.HeDieuHanh` (netstat, Get-CimInstance, pg_ctl) chưa thực thi lần nào. Codex kiểm trên host với cấu hình đã review. **GUI chưa bấm.**
- Bước cluster không chạy `pg_isready` riêng: dùng lại dựa vào status + định danh tiến trình/cổng; start dựa vào `pg_ctl -w`. Nếu server chưa nhận kết nối, bootstrap sẽ báo `PG_KHONG_KET_NOI`.
- Đích thực sau kết nối so địa chỉ/cổng/OID DB, không so system identifier của cluster (hàm điều khiển cần quyền cao hơn login ứng dụng).
- Kiểm "không là chủ" dựa trên catalog (chủ DB/schema/bảng của bốn schema nghiệp vụ). Exploit RLS bằng role chủ chưa chạy thật.
- Lượt 03 vẫn còn mở: G10, toàn A5, t17 `app_ke_toan`, nhánh tạo DB lần đầu phụ thuộc thông điệp/SQLSTATE 3D000, bộ chiếu M1 cần DSN quản trị khi bấm sao kê M1.
- Root CHANGELOG/HANG-DOI do Codex cập nhật.

## 0. Lượt sửa 03 — thay đổi, cách chạy bằng nút, kết quả self-test

### 0.1 Đã sửa (theo lỗi có bằng chứng của bốn review 02)
| Lỗi review | Sửa | File |
|---|---|---|
| P1 `valid_to` bản đã duyệt bị người nộp đóng/mở (K2-MIGRATION-02) | **M0012** thay `master.phien_ban_kiem_duyet`: bản `DA_DUYET` chỉ đổi `valid_to` khi (a) đang NULL → có giá trị (không mở lại, không đổi mốc đã đóng: `HIEU_LUC_DA_DONG`), (b) danh tính phiên là CFO có V3 trên PN, (c) tồn tại bản thay **cùng hợp đồng**, `thay_cho_id` = bản này, `DA_DUYET` bởi chính người đó, `duyet_luc = now()` (cùng giao dịch), `valid_from = valid_to` mới; sai → `HIEU_LUC_KHONG_HOP_LE`. Bản chờ duyệt không được tự đặt biên hiệu lực; bản vừa duyệt phải `valid_to` NULL và `duyet_luc = now()`. Đường CFO duyệt phụ lục qua service giữ nguyên (thứ tự: duyệt bản mới rồi đóng bản cũ). | `ha_tang/pg_migrations.py` |
| P1 bốn helper SECURITY DEFINER đọc ngoài PN/module, PUBLIC EXECUTE | M0012: `da_lien_ket`, `da_lien_ket_dong`, `phien_ban_hieu_luc`, `van_tay_phien_ban` thành **hàm nội bộ** — thu hồi EXECUTE của PUBLIC và app_web (trigger của chủ CSDL vẫn gọi được). Ứng dụng dùng `master.crm_da_lien_ket/crm_da_lien_ket_dong/crm_phien_ban_hieu_luc/crm_van_tay_phien_ban`: SECURITY DEFINER nhưng kiểm danh tính ID+login khớp và `ktt_duoc(PN của chính ID tham số, 'CRM')`; ngoài phạm vi, thiếu/lệch danh tính, ID không tồn tại → cùng NULL (không lộ tồn tại). Actor chỉ CRM (bán hàng) vẫn đọc aggregate PN của mình, không cần M1. Chỉ cấp EXECUTE cho app_web. | `pg_migrations.py`, `k2/crm.py` |
| P1 parser: token số và loại tiền (NGUON-VA-PARSER-02) | So khớp **token trọn vẹn** (số không là phần của số dài hơn: 40.000.000 ⊄ 140.000.000; 1.000 ⊄ 11.000; ngày không dính chữ số; chữ không dính chữ); tiền có kiểu = số + loại tiền: loại tiền ghi ngay sau token trong trích dẫn (alias profile hoặc mã ISO) phải đúng loại tiền typed. Khác loại tiền → `GIA_TRI_KHONG_KHOP_TRICH_DAN` + lỗi cứng `TIEN_TE_KHONG_KHOP_TRICH_DAN` (xác nhận thủ công không vượt được, không quy đổi/đổi nhãn); trích dẫn không nêu loại tiền → giữ chờ, chỉ hiệu lực sau xác nhận thủ công có lý do. Giữ alias `đồng/VNĐ/đ` ≡ VND, USD scale 2, `%`, 0, NULL, các sửa Suy ra/optional/Điều-Khoản. | `k2/crm_phan_tich.py` |
| G02 tiền sau HĐ vẫn Có 344 (M1-02 F1) | Không thêm engine/policy 131 chung: `Engine.contract_facts` (context của engine M1 hiện có, giống `party_projects`) nhận fact HĐ/lịch **đã duyệt, hiệu lực ngày tiền về** từ K2 (`CrmK2.fact_hop_dong_m1`, theo quyền người thao tác, kèm provenance HĐ/phiên bản/profile/người duyệt/quy tắc TL32 §3.2). Có fact của đúng đối tượng/loại tiền → Có **131** (thay mức yếu/chờ duyệt; không vượt mẫu đã duyệt, chứng từ Junsky, công nợ khớp đúng số), dự án theo HĐ, bằng chứng đợt gần nhất còn phải thu, `auto_allocate=false`; vượt phần còn lại của đợt gần nhất → `CONTRACT_AMOUNT_EXCEEDS_INSTALLMENT_WAIT`; nhiều HĐ → `CONTRACT_MULTIPLE_WAIT`. Không có fact hiệu lực ngày tiền về → giữ nhánh 344 của tri thức DEMO chờ duyệt. Tiền đã đề xuất trước không bị đề xuất lại khi HĐ đến sau. | `de_xuat/engine.py`, `giao_dien/quick.py` (`propose(..., contract_facts=)`), `k2/crm.py`, `k2/m1_demo.py`, `giao_dien/server.py` |
| G12 lỗi nguồn vẫn commit projection (M1-02 F2) | Bộ chiếu hiện có: (1) tính hash nguồn **trước mọi ghi**, sai → từ chối `CORE_HASH_NGUON_TRUOC_GHI`, không mở giao dịch ghi; (2) đối chiếu số đếm + nội dung tính **trong** giao dịch, không đạt → ném `_HoanTac` → PostgreSQL rollback toàn bộ (`DOI_CHIEU_KHONG_DAT_DA_HOAN_TAC`, `da_ghi=false`); (3) cờ `--cho-phep-du-dung-chung`: đích nhiều hơn nguồn ở đối tác/dự án/tệp gốc chỉ đạt khi **mọi bản ghi nguồn** có ở đích theo mã Junsky/hash tệp. **Thay đổi hành vi V13:** trước đây mã 1 vẫn commit; nay mã 1 = không ghi gì. | `tools/chuyen_sqlite_sang_pg.py`, `k2/m1_demo.py` |
| G04 ID dòng đề xuất bị tái sinh khi chạy lại | `_de_xuat` chỉ xóa–tạo lại dòng khi nội dung khác; cùng nội dung → giữ nguyên dòng và ID. Dòng đã duyệt/khóa kỳ/có tham chiếu (G10) **chưa kiểm**. | `tools/chuyen_sqlite_sang_pg.py` |

### 0.2 Nút mở DEMO
- `MỞ BẢN DEMO.cmd` không đổi (vẫn gọi `start-web.ps1` với `cau_hinh.toml`, `var\web`, giữ tham số CLI).
- `start-web.ps1`:
  - **Bước PG CRM chỉ khi cấu hình không phải `environment = "that"`.** Gọi `tools/chuan_bi_crm_demo.py --config --root`, đọc một dòng JSON trạng thái. Lỗi không chặn mở phần mềm; console ghi mã và tên tệp trạng thái đã lọc.
  - **Log riêng mỗi lần khởi chạy và mỗi lần thử lại:** `<root>\logs\server-out|error-<UTC>-<pid>-<lần>.log`. Không ghi đè, không xóa log cũ.
  - **Chỉ dừng server cũ khi xác minh được:** PID do `/api/health` trả phải trùng PID đang nghe cổng, là python, và dòng lệnh chứa `kho_tri_thuc.giao_dien.server` cùng `--root` của kho này. Không khớp thì không dừng gì.
- **Giao diện cấu hình bí mật cục bộ (Codex cấu hình sau review, Claude không tạo):**
  - Tệp `<DataRoot>\crm-demo\ket-noi.local.json`, hoặc đường dẫn trong biến môi trường `KTT_CRM_DEMO_KET_NOI`.
  - Nội dung: `{"phien_ban": 1, "app_dsn": "...", "admin_dsn": "..."}`.
  - Code kiểm: host chỉ `localhost/127.0.0.1/::1`; tên DB bắt đầu `kho_crm_demo`; hai DSN cùng DB; thông điệp lỗi không chứa DSN.
  - Codex chịu trách nhiệm đặt quyền tệp. Không có tệp thì app vẫn mở, trang CRM báo chưa cấu hình.
- **`k2/crm_khoi_dong.chuan_bi`** (bước chuẩn bị, dùng quyền quản trị cục bộ):
  - DB chưa có thì `CREATE DATABASE` đúng tên DEMO. Không bao giờ DROP, không khởi động/cài cluster, không dừng tiến trình.
  - Migrate có audit tương thích, seed DEMO idempotent.
  - Kiểm login ứng dụng: không superuser, không BYPASSRLS, thành viên `app_web`, cùng DB, schema = 12.
  - Ghi trạng thái không bí mật vào `<root>\crm-demo\chuan-bi-<UTC>-<pid>.json` (tệp mới mỗi lần).
- **Server:**
  - Request thường chỉ dùng `app_dsn`. Khi kết nối, server kiểm role không superuser/BYPASSRLS và schema đúng phiên bản; server **không còn tự migrate/seed**.
  - `admin_dsn` chỉ truyền qua biến môi trường cho tiến trình con bộ chiếu M1 khi bấm "Sao kê M1 DEMO". Đây là đường đồng bộ đặc quyền, ghi ở mục hạn chế.
- **Cách chạy sau khi Codex cấu hình:** bấm `MỞ BẢN DEMO.cmd` → console báo "CRM DEMO sẵn sàng: CSDL …, schema 12" → trình duyệt → **Hợp đồng & lịch thu**. Mở lại dùng cùng DB/hồ sơ/lô.

### 0.3 Self-test lượt 03 (Claude tự chạy; guard không xóa bật; DB/role/thư mục giữ lại)
| Lệnh | Pass | Fail | Error | Skip | Ghi chú |
|---|---:|---:|---:|---:|---|
| `unittest test_crm_phan_tich.py` | 20 | 0 | 0 | 0 | thêm token/currency, cấu hình kết nối, tool chưa cấu hình, kiểm tĩnh launcher |
| helper `test_crm_k2.py` (login thường NOSUPERUSER/NOBYPASSRLS, thành viên app_web) | 22 | 0 | 0 | 1 | skip `t17`: máy chủ test không có role `app_ke_toan` — **không tính đạt** |
| helper `test_pg_bo_chuyen_schema10.py` | 1 | 0 | 0 | 0 | |
| `test_v1*.py` | 115 | 0 | 0 | 3 | gồm engine/QuickPosting sau khi thêm `contract_facts` |
| `test_v9b.py` / `test_nghiem_thu_bridge.py` | 19 / 21 | 0 | 0 | 0 | |
| `test_v13_doi_chieu.py` / `test_ket_noi.py` (phần không PG) | 15 / 12 | 0 | 0 | 3 / 11 | phần PG không chạy (teardown có DROP DATABASE) |
| `test_m1.py` | 42 | 1 | 0 | 0 | fail guard đã biết (`test_backup_does_not_succeed_without_referenced_raw`) |
| `test_web.py` | 22 | 1 | 0/1 | 0 | fail guard đã biết; lần chạy đầu có thêm 1 error WinError 10053 (socket), chạy lại không tái hiện |
| `test_pg_schema.py` | — | — | — | — | không chạy (DROP DATABASE/OWNED/ROLE) |

Ca PG mới/đổi trong `test_crm_k2.py`:
- **t01/t01b:** đích 12.
  - Từ v9 có HUY lịch sử: dữ liệu giữ nguyên, 12 dòng checksum đúng.
  - Từ M10 bản đầu: 10 dòng cũ không đổi, audit tương thích một dòng, thêm 11 và 12.
- **t01c (mới):** DB dừng ở 11 có bản đã duyệt + lịch + tham số (KT kiểm/CFO duyệt bằng danh tính phiên) → 12.
  - Bốn bảng trước/sau giống hệt; 11 dòng `schema_migrations` cũ giữ nguyên.
  - CFO đóng `valid_to` bản cũ không có bản thay → `HIEU_LUC_KHONG_HOP_LE`.
  - app_web không còn EXECUTE hàm nội bộ.
- **t08 (đổi):** M1 thật với fact HĐ.
  - Tiền 25/08 (trước ngày hiệu lực 01/09) → C344/A01. Tiền 10/10 và 14/10 (sau khi cọc đã nối) → **C131/A01**, `contract_evidence.applied`, đợt gần nhất DOT-1, provenance `HDC-KCN-DEMO-01`, `allocations=[]`, mức tin cậy `CONTRACT_FACT`.
  - Nạp lại + chiếu lại: không nhân, **ID dòng đề xuất giữ nguyên**.
- **t10:** nhà ở → cả hai khoản C131; khoản 300m vượt cọc 100m chưa nối → `CONTRACT_AMOUNT_EXCEEDS_INSTALLMENT_WAIT`.
- **t14b (mới, G12, oracle nhân quả):**
  - (1) Bản sao nguồn có `core_hash` sai → `CORE_HASH_NGUON_TRUOC_GHI`, `da_ghi=false`; ảnh chụp K2 (SAO_KE hash/mô tả/du_lieu, đề xuất, ID + giá trị dòng, link, lô, tệp) trước/sau giống hệt.
  - (2) Chạy lại nguồn đúng → đạt, ảnh chụp giống hệt.
  - (3) Nguồn hợp lệ nhưng đổi mô tả một BANK (hash tính lại đúng), đích có một bản ghi lạ → bộ chiếu ghi rồi đối chiếu thấy thừa → `DOI_CHIEU_KHONG_DAT_DA_HOAN_TAC`, ảnh chụp giống hệt, không dòng nào mang mô tả sửa.
  - Bản ghi lạ `DEMO-MO-COI-T14B` giữ lại làm bằng chứng.
- **t18 (mới):**
  - Control dương: bản 1 đóng đúng `valid_from` bản 2.
  - Bán hàng/XEM/CFO đóng bản đang mở không có bản thay, mở lại hay đổi mốc bản đã đóng → bị chặn; KT đặt `valid_from` bản chờ → chặn.
  - Biên hiệu lực trước/sau không đổi.
- **t19 (mới):**
  - Control dương trước: KT_A và bán hàng nhận cùng giá trị thật (DOT-1 1.200.000.000; hiệu lực = bản 2; vân tay không rỗng); KT_B đọc được PN_B.
  - Bốn hàm × năm ca ngoài phạm vi (PN khác, không module CRM, thiếu login, ID/login lệch, ID ngẫu nhiên, không danh tính) → NULL.
  - Bốn hàm nội bộ → `permission denied`. ACL của 8 hàm không có PUBLIC; chỉ hàm `crm_*` cấp cho app_web.
- **t21 (mới):** `chuan_bi` với kết nối truyền trong bộ nhớ (không ghi DSN ra đĩa).
  - DB mới → tạo + migrate 0→12 + seed + kiểm role; mở lại → không tạo mới, giữ dữ liệu đã thêm.
  - Trạng thái không chứa mật khẩu; tên DB ngoài tiền tố → `KET_NOI_DB_KHONG_DEMO`.
  - Login superuser làm app → `ROLE_UNG_DUNG_SAI` (nhánh này chỉ chạy khi DSN quản trị test là superuser).

### 0.4 Chưa kiểm / hạn chế thật của lượt 03
- **GUI chưa bấm.** Nút `MỞ BẢN DEMO.cmd` và `start-web.ps1` chưa chạy thật trên host: chỉ kiểm tĩnh nội dung, chưa có tệp kết nối cục bộ. Restart tiến trình hệ điều hành chưa kiểm. HTTP chỉ kiểm mở lại đối tượng app/kết nối trong cùng process (t14/t15).
- Lần chạy đầu khi DB DEMO chưa có dựa vào thông điệp lỗi "does not exist"/SQLSTATE 3D000 để quyết định tạo DB. Locale máy chủ khác có thể làm nhánh này báo `PG_KHONG_KET_NOI` thay vì tạo DB. Codex nên kiểm trên host.
- Bộ chiếu M1 vẫn cần DSN quản trị khi bấm sao kê M1 (DISABLE TRIGGER lúc chuyển). DSN chỉ đi qua biến môi trường tiến trình con, không vào trình duyệt/log, nhưng vẫn là quyền đặc quyền trong lúc chạy server.
- Fact HĐ cho engine tính phần còn phải thu theo link **hiện tại**, không theo thời điểm tiền về.
- G10 (dòng đã duyệt/khóa kỳ/protected approval qua bộ chiếu), toàn A5, snapshot nguồn sát biên negative: **chưa kiểm**.
- `t17` (role cũ `app_ke_toan`) skip.
- Không sửa được `CHANGELOG.md` và `HANG-DOI-YEU-CAU.md` (ngoài phạm vi file được cấp). Đề xuất Codex thêm: "19/10/2026 — CRM bàn giao 03 (Claude sửa, chờ kiểm độc lập): M0012 (valid_to + helper scope), parser token/currency, nhánh 131 qua context engine M1, bộ chiếu atomic, nút mở DEMO có bước chuẩn bị PG; unit 20/20, PG 22 pass/1 skip; GUI/launcher thật chưa kiểm."

---

## 1. Đã sửa theo review 02 (lịch sử lượt 02)

| Nhóm review | Sửa |
|---|---|
| Ranh giới CSDL — danh tính | `master.ktt_danh_tinh()`: ID **và** login phải cùng có và cùng một người dùng hoạt động; thiếu một trong hai hoặc lệch → không thấy dòng nào (fail-closed). RLS, trigger kiểm/duyệt/việc đều dùng hàm này. Máy chủ đặt `ktt.nguoi_dung_id`, `ktt.nguoi_dung_dang_nhap`, `ktt.ngay_hieu_luc` LOCAL mỗi giao dịch. |
| Quyền theo module | RLS v11 theo **pháp nhân + module**: bảng CRM cần module `CRM`; `kho.chung_tu` theo loại (`HOP_DONG_TEP`→CRM, còn lại→M1); `de_xuat`, `de_xuat_dong`, `chung_tu_dong`, `lien_ket` → M1; `viec`/`lo_xuat` theo module ghi trên dòng; bật RLS thêm cho `nhan_vien`, `chung_tu_dong`, `de_xuat_dong`, `lo_xuat`. Service kiểm `XEM`/`XEM_TIEN` trước khi đọc. Bán hàng (chỉ CRM) không đọc được sao kê/đề xuất M1. |
| Bất biến | Trigger: phiên bản mới chỉ chèn ở `CHO_DUYET`; bản `DA_DUYET` chỉ đổi `valid_to`; `TU_CHOI/THAY_THE` khóa; tham số chỉ ghi khi phiên bản còn chờ; lịch không xóa, chỉ đổi trạng thái thu, chỉ sinh trong chính giao dịch duyệt; hợp đồng không đổi định danh, không đổi mapping sau khi có bản duyệt; con trỏ hiện hành phải là bản đã duyệt của chính hợp đồng. |
| FK cùng pháp nhân / cùng hợp đồng | FK ghép `(loai_hinh, pn)`, `(du_an, pn)`, `(phien_ban_hien_hanh, hop_dong)` (deferrable), `(thay_cho, hop_dong)`; trigger đối tác phải có mã Junsky của đúng pháp nhân; profile/chứng từ của phiên bản phải cùng pháp nhân. |
| Nâng cấp v9 có link HUY | M0010 hiện hành = bản bàn giao đầu **bỏ đúng CHECK `lien_ket_huy_co_vet`**; M0011 thêm cột `huy_khong_vet_truoc_v10`, đánh dấu link HUY lịch sử thiếu người/thời điểm/lý do (không bịa), tạo lại CHECK có miễn trừ cờ; cờ không sửa được, dòng mới không được tạo ở trạng thái HUY/cờ. |
| DB đã nhận M0010 bản đầu | `PG_MIGRATION_TUONG_THICH = {10: {sha256(M0010_V1_BAN_GIAO_DAU): ghi chú}}`. `migrate()` chỉ chấp nhận đúng hash liệt kê (và chỉ với bộ migration chuẩn), ghi `master.migration_tuong_thich (version, checksum_da_ghi, checksum_hien_tai, ghi_nhan_luc, ghi_chu)`; **không sửa `schema_migrations`, không drop/recreate**. Hash khác → `MIGRATION_CHANGED`. Checksum 0001–0009 không đổi. |
| V3/V4 | Tách quyền `DUYET` (V3) và `DUYET_V4`. Hợp đồng mới còn việc V4: CFO chỉ có V3 bị `KHONG_CO_QUYEN_LOAI_VIEC`; CFO có V4 hoàn tất V4 cùng giao dịch hoặc riêng (`duyet_v4`). Trigger `kho.viec_kiem`: hoàn tất việc phải đúng người của phiên có loại việc trên pháp nhân (trigger không SECURITY DEFINER để thấy vai trò thật). |
| Mapping sau kiểm | Lần kiểm lưu **vân tay** (`master.van_tay_phien_ban`: nội dung phiên bản + tham số + mapping hợp đồng). Đổi mapping/xác nhận tham số qua service → hủy lần kiểm (sự kiện `VO_HIEU_KIEM`); client sửa thẳng mapping bằng SQL → CSDL chặn duyệt `KIEM_DA_HET_HIEU_LUC`. |
| Phụ lục có hiệu lực tương lai | `valid_from` = ngày hiệu lực (nửa đêm UTC), bản cũ `valid_to` = cùng ngày; `master.phien_ban_hieu_luc(hd, ngày)` quyết định đợt nào được nối tiền theo **đồng hồ nghiệp vụ** (service nhận `hom_nay`). Giao diện hiện “đang hiệu lực/sắp hiệu lực”. Nối vào đợt bản cũ mà phụ lục đã duyệt sẽ đổi/bỏ → CSDL `NGHIA_VU_SAP_THAY_DOI`. |
| Race nghĩa vụ–tiền, retry đồng thời | Thứ tự khóa chung **hợp đồng → khoản tiền → đợt** ở service (duyệt, nối, gỡ, mapping, kiểm, trích lại) và trigger link; duyệt tính lại kế hoạch phụ lục **sau** khi khóa. Retry: kiểm quyền trước, khóa hợp đồng, đọc theo khóa idempotency (cùng nội dung → trả đúng link kể cả đã HUY; khác → `IDEMPOTENCY_KHAC`), `INSERT … ON CONFLICT` dự phòng. |
| Parser / căn cứ | Giá trị phải nằm **trong câu trích dẫn** (`GIA_TRI_KHONG_KHOP_TRICH_DAN`); ghi chú “Suy ra/suy luận/ước tính/nội suy” → `SUY_RA`; văn bản có mục Điều/Khoản → kiểm vị trí (`VI_TRI_KHONG_KHOP`), văn bản phẳng có điều khoản → `CHUA_DOI_CHIEU_VI_TRI`. Hai trạng thái giá trị chỉ hiệu lực sau **xác nhận thủ công từng tham số** có lý do (`xac_nhan_tham_so`); xác nhận chung cấp phiên bản không thay. Tham số optional rỗng không phải nghĩa vụ, không chặn. Đơn vị tiền theo alias profile có provenance (`đồng`→VND, ghi `don_vi_nguon`, `alias_profile`); `%` nhận “30%” hoặc “30” + đơn vị “%”. Mã lặp lưu đủ từng dòng (`ma`, `ma#2`…), khác giá trị → `THAM_SO_TRUNG_MA`. Phụ lục đổi cơ sở tiền/loại/số đợt của đợt đã thu → chặn. |
| HTTP danh tính theo phiên | Cookie `ktt_crm` (HttpOnly, SameSite=Strict, ngẫu nhiên) do máy chủ cấp; mỗi phiên giữ danh tính riêng; POST/tải file không có phiên hợp lệ → `CRM_PHIEN`; body chứa actor/pháp nhân/trạng thái → `CRM_CLIENT_IDENTITY`. |
| Hồ sơ CHO_KHOA/CHO_MAPPING | `bo_sung_ho_so`: kế toán bổ sung loại hình/loại bản/mã HĐ chung/HĐ gốc/ObjectID/dự án cho **đúng chứng từ** (không nhận raw lần 2, không đổi namespace), ghi trước/sau vào nhật ký, tính lại tham số, lập tiếp; trùng hợp đồng đã có → giữ `XUNG_DOT`. |
| Trích lại cùng Word | `word_tham_chieu` (DEMO) tách khỏi `word_hash` (chỉ sha256 bytes Word thật). Bản trích lại → việc đối chiếu; `doi_chieu_trich_lai` so từng mã (giá trị, trích dẫn, căn cứ); `xu_ly_trich_lai`: **Giữ bản cũ** hoặc **Áp dụng** (chỉ khi bản đang chờ duyệt: bản cũ `THAY_THE` có vết, phiên bản mới chờ KT kiểm/CFO duyệt lại). Bản đã duyệt không thay bằng trích lại (`TRICH_LAI_BAN_DA_DUYET`). |
| File soát CRM | `xuat_file_soat` dùng export Excel chung (`xuat/excel.py`): sheet `HOP_DONG_PHIEN_BAN`, `LICH_NGHIA_VU` (mọi phiên bản, cột hiệu lực hôm nay), `THAM_SO_CAN_CU`, `CANH_BAO` (“không phải phiếu thu/chi, không phải file nhập Junsky”); số ≥ 10^15 ghi dạng chữ; tệp bất biến theo sha256; đăng ký `kho.lo_xuat` loại `FILE_SOAT`, `du_lieu.module = CRM`; tải về kiểm lại hash, RLS theo pháp nhân. |
| Tái sử dụng M1 thật | Bỏ đường tạo tiền riêng của CRM (`nhan_tien_demo`). `k2/m1_demo.py`: sao kê DEMO định dạng nguồn V12 → `Store.ingest` (raw/hash/staging/evidence) → `QuickPosting.propose` (engine M1 hiện có; tri thức DEMO ở trạng thái **chờ duyệt**) → **bộ chiếu hiện có** `tools/chuyen_sqlite_sang_pg.py` (chủ CSDL) → `kho.chung_tu SAO_KE` + `kho.de_xuat`. Một BANK logic = một chứng từ K2; CRM chỉ thêm liên kết. |

## 2. File, schema, profile
- Migration: `ha_tang/pg_migrations.py` — `M0010_V1_BAN_GIAO_DAU` (giữ nguyên văn để tính hash), `M0010` (bản hiện hành, lọc bỏ CHECK), **`M0011`** + `_rls_v11()`; `PG_MIGRATION_TUONG_THICH`; **`PG_SCHEMA_VERSION = 11`**. `ha_tang/postgres.py` — `migrate(..., migrations=None)` + bảng audit tương thích.
- Hash tương thích: giá trị là `sha256("\n".join(M0010_V1_BAN_GIAO_DAU))`, tính trong code (không chép tay). Test `t01b` ghi bộ ba hash (M0010 bản đầu / M0010 hiện hành / M0011) vào dòng `CRM_K2_AGGREGATE` của bằng chứng helper và vào `master.migration_tuong_thich` của DB giữ lại `kho_test_crm_v10_*`; Claude không đọc thư mục `var/` nên không chép literal vào đây — Codex đối chiếu ở đó.
- Code: `k2/crm.py` (viết lại), `k2/crm_phan_tich.py`, `k2/quyen.py`, `k2/crm_demo.py` (thêm `MO_PHONG_CFO_CHI_V3`, `MO_PHONG_KT_KHONG_CRM_A`, module theo người), `k2/m1_demo.py` (mới), `k2/loai_hinh_demo.py`, `nguon/trich_hop_dong_6.py`, `kiem_chung/fixtures_crm.py` (văn bản KCN có mục Điều/Khoản, đơn vị `đồng`, sao kê M1 DEMO), `giao_dien/server.py`, `assets/app.js`, `assets/index.html`.
- Profile: `DT-KCN-THUE-DAT-DEMO` **v2**, `DT-NHA-O-DEMO` **v2** (thêm alias đơn vị tiền); v1 giữ trong CSDL làm lịch sử (`valid_to` đóng khi seed v2), cùng version khác nội dung → từ chối. **Giả định để mô phỏng, không phải policy.** Phiên bản hợp đồng ghi `profile {ma, phien_ban, hash}`.
- Cấu hình GUI: `KHO_PG_DSN_CRM_DEMO` (vai trò `app_web`); `KHO_PG_DSN_CRM_DEMO_ADMIN` (migrate + seed + bộ chiếu M1). Thiếu DSN chủ → nút sao kê M1 báo chưa cấu hình. Không đọc/sửa kho thật hay `.env`.

## 3. Luồng và cách bấm (chưa bấm thử)
Shell DEMO → **Hợp đồng & lịch thu** → Nhận mẫu `kcn_goc`/`nha_goc` → Mở → (vai `MO_PHONG_KT_A`) Kế toán kiểm trước → đổi vai `MO_PHONG_CFO` → CFO duyệt (hoặc vai `MO_PHONG_CFO_CHI_V3`: phải có người duyệt V4 trước) → **Sao kê M1 DEMO** `PN_DEMO_A:…` → (vai kế toán) Nối ở dòng lịch của bản đang hiệu lực → Nhận mẫu `kcn_phu_luc` → kiểm → duyệt → **Xuất file soát lịch nghĩa vụ** → mục 4 Tải ↓. Hồ sơ chờ khóa/mapping có ô **Bổ sung & lập tiếp**; bản trích lại có **Đối chiếu / Giữ bản cũ / Áp dụng**; tham số Suy ra có **Xác nhận thủ công** kèm lý do. Danh tính đổi trong một tab chỉ áp dụng cho phiên trình duyệt đó.

## 4. Kết quả kiểm thử thật (Claude tự chạy, 19/10/2026; guard không xóa bật, DB/role/thư mục giữ lại)
| Lệnh | Kết quả |
|---|---|
| `unittest test_crm_phan_tich.py` (không PG) | **16/16 pass** |
| helper `test_crm_k2.py` (PostgreSQL, psycopg 3.3.6, vai trò `app_web` thật) | **18 chạy: 17 pass, 0 fail, 0 error, 1 skip** — skip `t17` (máy chủ test không có vai trò `app_ke_toan`; **không tính đạt**) |
| helper `test_pg_bo_chuyen_schema10.py` | 1/1 pass |
| `unittest test_nghiem_thu_bridge.py` | 21/21 pass |
| `unittest test_v9b.py` | 19/19 pass |
| `unittest test_v1*.py` | 118 chạy, 115 pass, 3 skip |
| `unittest test_v13_doi_chieu.py` (phần không PG) | 15 pass, 3 skip (phần PG không chạy lượt này) |
| `unittest test_ket_noi.py` (phần không PG) | 12 pass, 11 skip (phần PG không chạy lượt này) |
| `unittest test_web.py` | 22 pass, **1 fail** `test_scope_changes_receipt_not_raw_storage_size` (guard không xóa giữ tệp tạm — đã biết) |
| `unittest test_m1.py` | 42 pass, **1 fail** `test_backup_does_not_succeed_without_referenced_raw` (guard — đã biết) |
| `test_pg_schema.py` | **không chạy**: có `DROP DATABASE` khi teardown và `DROP OWNED/DROP ROLE` ở t15; thay bằng `test_crm_k2.t17` giữ role (đang skip như trên). Phần PG của `test_ket_noi`/`test_v13_doi_chieu` cũng có `DROP DATABASE` nên không chạy. |

Ca PG đã khẳng định trong `test_crm_k2.py`:
- **t01** DB schema 9 có hợp đồng/lịch/link + **link HUY lịch sử** → migrate 11 giữ dữ liệu; link HUY còn nguyên, cờ `huy_khong_vet_truoc_v10 = true`, người/thời điểm/lý do hủy vẫn NULL; 11 dòng `schema_migrations` đúng checksum từng migration; không tạo bảng tương thích. **t01b** DB dựng bằng M0010 bản đầu → migrate 11 (hai lần): 10 dòng `schema_migrations` cũ không đổi (cả `applied_at`), 1 dòng `migration_tuong_thich`; DB có M0010 bị sửa khác → `MIGRATION_CHANGED`.
- **t02/t04** vai trò thật không superuser, không đọc `bao_mat`, không DELETE; thiếu login / thiếu ID / ID và login hai người → 0 dòng; KT_A chỉ A, KT_B chỉ B, CFO cả hai; KT có pháp nhân A nhưng không module CRM → service `KHONG_CO_QUYEN_MODULE`, SQL thẳng thấy 0 hợp đồng/phiên bản/tham số/profile/hồ sơ #6; vai XEM không thấy khoản thu, không kiểm được; ghi chéo pháp nhân bị RLS chặn.
- **t03** nhận lại cùng raw → mọi số đếm không đổi; tham số có giá trị đều `CO_CAN_CU`, dòng optional rỗng `KHONG_QUY_DINH`; `đồng` → VND kèm alias profile v2.
- **t05** vai trò duyệt (bán hàng/kế toán/chưa kiểm/danh tính không mô phỏng bị chặn); KT ghi thẳng `DA_DUYET` (kể cả mạo `nguoi_duyet` = CFO) → `KHONG_CO_QUYEN_DUYET`; CFO chỉ V3 → `KHONG_CO_QUYEN_LOAI_VIEC` ở service, `duyet_v4` và SQL thẳng; số đếm không đổi; CFO đủ quyền duyệt → V4 đóng; lịch đúng expected viết tay; không thêm đề xuất/lô/chứng từ. Nhà ở: CFO duyệt V4 riêng → CFO chỉ V3 duyệt tham số được.
- **t06** SQL thẳng: chèn bản `DA_DUYET`, sửa bản đã duyệt, sửa/chèn tham số bản đã duyệt, sửa số tiền lịch, chèn lịch ngoài giao dịch duyệt, xóa lịch, đổi mapping/định danh hợp đồng đã duyệt, trỏ con trỏ sang phiên bản hợp đồng khác → đều bị chặn; chủ CSDL cũng không ghi được dự án/loại hình/đối tác/chứng từ/profile của pháp nhân khác hay `thay_cho` sang hợp đồng khác.
- **t07** thiếu căn cứ → giá trị NULL (không 0); mapping mã pháp nhân khác bị từ chối; `CHO_KHOA` → bổ sung mã HĐ chung → hợp đồng chờ duyệt, cùng chứng từ, không thêm chứng từ/tệp, có sự kiện `BO_SUNG_HO_SO`, việc chờ đóng, bổ sung lần 2 → `HO_SO_DA_LAP`; `CHO_MAPPING` → bổ sung → trùng hợp đồng đã có → `XUNG_DOT`.
- **t08** M1 thật: 1 + 2 BANK → +3 chứng từ `SAO_KE`, số đề xuất K2 tăng đúng số đề xuất engine M1 sinh (>0); nạp lại + chiếu lại → 0 mới, mọi bảng (trừ nhật ký chuyển đổi) không đổi. Bộ chiếu trả mã 1 vì đếm theo pháp nhân ở 3 bảng dùng chung với CRM (`doi_tac_ma_junsky`, `du_an`, `tep_goc`: đích > nguồn do seed/tệp #6); `m1_demo` chỉ chấp nhận đúng trường hợp đó, mọi ánh xạ khác (BANK→SAO_KE, quick_items→de_xuat, …) và **đối chiếu nội dung từng bản ghi** phải khớp. Bán hàng đọc 0 sao kê/đề xuất. Nối: cọc từ tiền đến trước hợp đồng; CFO dùng khóa đã có → bị chặn quyền trước nhánh lặp; retry cùng khóa → lặp; khác nội dung → `IDEMPOTENCY_KHAC`; nối trùng đợt → `LIEN_KET_DA_CO`; vượt nghĩa vụ/tiền/khác currency/khác pháp nhân bị chặn; gỡ (gỡ lại → lặp); dùng lại khóa của link đã gỡ → trả đúng link HUY, không tạo lại. Nối/gỡ không thêm đề xuất/dòng.
- **t09** phụ lục hiệu lực 01/10/2026 (quá khứ): kế hoạch `GIU/GIU/DOI`, bản 2 hiệu lực hôm nay, lịch bản 1 giữ nguyên, nối vào đợt bản cũ → `LICH_KHONG_HIEU_LUC`.
- **t10** phụ lục mơ hồ đổi đợt đã thu → chặn, từ chối, không nhân lịch; phụ lục nhà ở hiệu lực **01/11/2026** (tương lai so với ngày nghiệp vụ 19/10): duyệt xong bản 1 vẫn hiệu lực, bản 3 “sắp hiệu lực”; nối vào đợt bản 3 → `LICH_KHONG_HIEU_LUC`; nối vào DOT-2 bản 1 → CSDL `NGHIA_VU_SAP_THAY_DOI`; đặt đồng hồ 02/11/2026 → bản 3 hiệu lực, nối qua kiểm hiệu lực (dừng ở hết tiền).
- **t11** race hai thứ tự trên hai kết nối, có xác nhận phía sau thực sự chờ khóa (`pg_stat_activity`): nối tiền giữ khóa → duyệt phụ lục đổi đợt đó chờ rồi bị chặn (kế hoạch tính lại thấy đợt đã có tiền); duyệt phụ lục giữ khóa → nối vào đợt cũ chờ rồi `LICH_KHONG_HIEU_LUC`. Retry đồng thời cùng khóa (barrier, hai kết nối) → đúng 1 link, một lần `lap_lai`.
- **t12** đổi mapping sau kiểm → lần kiểm hủy, CFO duyệt `CHUA_KIEM_TRUOC`; SQL thẳng đổi mapping sau kiểm → `KIEM_DA_HET_HIEU_LUC`; tham số Suy ra chặn đến khi KT xác nhận riêng có lý do, xác nhận chung không thay.
- **t13** trích lại bản đã duyệt → đối chiếu 0 khác, không áp dụng được, giữ bản cũ; bản đang chờ: đối chiếu đúng 1 mã khác → áp dụng → bản cũ `THAY_THE` (không sửa được), bản mới kiểm/duyệt → lịch theo bản trích lại.
- **t14** file soát: +1 `lo_xuat` (FILE_SOAT, module CRM), không đổi đề xuất/chứng từ/link/lịch; tải về đúng sha256; 4 sheet, 6 dòng lịch (2 phiên bản), cảnh báo không phải file Junsky; pháp nhân khác không tải được; kết nối mới tải lại đúng bytes.
- **t15** HTTP: hai phiên cookie độc lập (đổi vai phiên này không đổi phiên kia, phiên cũ không cấp cookie mới); không cookie / sid tự đặt → `CRM_PHIEN`; actor trong body → chặn; KT duyệt, CFO nối tiền → chặn; tạo + tải file soát qua HTTP đúng hash; người không module CRM thấy thông báo không quyền, không dữ liệu. Route `m1-sao-ke` chỉ kiểm nhánh thiếu DSN chủ (luồng M1 dương kiểm ở service t08/t10/t11).
- **t16** kết nối mới thấy cùng dữ liệu; nhật ký không UPDATE được. Số đếm cuối và các lần chiếu M1 in ở dòng `CRM_K2_AGGREGATE` của bằng chứng helper `var/codex-dieu-phoi/pg-retained-20261019-071446-791983e9` (Claude không đọc).

## 5. Precision, NULL, căn cứ
Số #6 đọc bằng Decimal; tiền typed là minor units theo currency profile (VND 0, USD 2); tiền qua API là chuỗi. Căn cứ: `CO_CAN_CU`, `KHONG_QUY_DINH` (hiệu lực NULL), `CAN_CU_KHONG_KHOP`, `VI_TRI_KHONG_KHOP` (chặn); `CHUA_DOI_CHIEU_NGUON`, `CHUA_DOI_CHIEU_VI_TRI` (cần KT xác nhận chung có vết); `SUY_RA`, `GIA_TRI_KHONG_KHOP_TRICH_DAN` (cần xác nhận từng tham số có lý do). `kiem_tra`/`tao_luc`/`dap_an`/model nguồn không thay duyệt/known_at/expected/căn cứ.

## 6. Hạn chế và việc còn mở (thật)
- **GUI chưa bấm**; HTTP/artifact test không phải kiểm GUI.
- `t17` (vai trò cũ `app_ke_toan`) skip vì máy chủ test không có vai trò đó → policy cho vai trò cũ chưa kiểm thực tế. `test_pg_schema.py` và phần PG của `test_ket_noi`/`test_v13_doi_chieu` không chạy lượt này (có lệnh DROP).
- Bộ chiếu legacy→K2 vẫn đối chiếu số đếm theo pháp nhân; với pháp nhân có dữ liệu module khác nó trả mã 1 — `m1_demo` lọc đúng 3 bảng dùng chung, không sửa bộ chiếu. Tri thức M1 DEMO ở trạng thái chờ duyệt nên đề xuất M1 là đề xuất chờ, không phải policy.
- Danh tính DEMO là trình chọn vai theo phiên trình duyệt — **không phải đăng nhập production** (TL40 §8 chưa làm); phiên giữ trong bộ nhớ tiến trình; một kết nối CSDL dùng chung trong tiến trình DEMO (thao tác được tuần tự hóa bằng mutation lock).
- Mapping chỉ cho hợp đồng mới đang chờ; áp dụng bản trích lại chỉ khi bản đang chờ duyệt.
- Chính sách ghi nhận doanh thu/VAT/FX/giá vốn, profile production, cách chuyển nghĩa vụ khi phụ lục đổi phần đã thu: **chờ CFO**; DEMO giữ chờ, không tự chọn.
- Production #6 → `giao_tiep` + vai trò riêng chưa làm; nguồn thật, cloud AI, Junsky mức 2, `CFO_NTD` vẫn khóa.
- Bước chương trình tiếp theo **sau khi CRM-01 qua review độc lập**: tái sử dụng cùng lớp quyền/liên kết/lịch cho M9 khoản vay và phần còn lại của cây 33.
