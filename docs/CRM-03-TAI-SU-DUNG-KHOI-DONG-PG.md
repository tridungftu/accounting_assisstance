# CRM03 → repair04 — tái dùng runtime/cluster PostgreSQL hiện hữu cho nút mở DEMO

**19/10/2026. Đề xuất kỹ thuật từ kiểm source/metadata, chưa code/chạy host/start/stop cluster.** Căn cứ `REVIEW-CRM-KHOI-DONG-03.md` và yêu cầu giữ mọi dữ liệu/file. Không đổi kiến trúc K1–K5/phương án C hoặc cài lại PostgreSQL. Claude sửa product chính; Codex review và root giữ local credentials/host execution gate.

## 1. Tài sản hiện có và phần được tái dùng

| Thành phần | Fact kiểm được lần này | Cách dùng |
|---|---|---|
| Runtime đã có | `D:\Claude\Phan mem ho tro ke toan\var\postgresql16-16.15-runtime\bin\pg_ctl.exe` và `postgres.exe` tồn tại. pg_ctl SHA256 `bed9ec9686fdf66b407f55d15be2466365827feb6b343fdb452c2dbcfbcfe0a1` | Gọi binary đúng đường dẫn đã xác nhận; không winget/download/installer mới. Hash là metadata kiểm hiện diện, không khẳng định runtime đang chạy |
| Cluster đã có | `D:\Claude\Phan mem ho tro ke toan\var\postgresql-ktt-16\data`; chỉ đọc `PG_VERSION`, giá trị16 | Dùng nguyên cluster này, không initdb/reset/recreate, không xóa PID/lock/WAL/DB/role hoặc di chuyển data directory |
| Thiết kế loopback | Endpoint đã dùng trong điều phối và script cài đặt:127.0.0.1:5432 | Ràng buộc bootstrap/DBs DEMO vào đúng cluster này; không tự chuyển sang PostgreSQL khác tìm thấy trên máy |
| Script cài đặt đã giữ | Đã kiểm **cấu trúc lệnh/path whitelist** của script elevated cũ: nhánh đăng ký service `postgresql-ktt-16` với pg_ctl/data-dir hiện hữu, gọi Start-Service rồi pg_isready loopback | Đây là cơ chế cài/service từng được chuẩn bị, **không chứng minh service hiện đã tồn tại/chạy**. Không gọi nguyên script vì có cả cài đặt/setup/quyền/ACL; không đọc cấu hình bí mật hoặc sao chép source private vào gói coder |
| Public installer | `CÀI POSTGRESQL.cmd`/`tools/cai_postgres.ps1` hướng tới cài/service/schema/`.env`; `tools/khoi_tao_pg.py` chạy schema/integrity bằng DSN | Không dùng làm cold-start helper. Không gọi lại installer, tạo roles/password hoặc migrate kho thật để mở DEMO |
| Nút DEMO hiện tại | `MỞ BẢN DEMO.cmd`→`start-web.ps1`→`tools/chuan_bi_crm_demo.py`→`crm_khoi_dong.chuan_bi` | Giữ launcher/health/process ownership/log/one-time local config; bổ sung bước bảo đảm đúng PG cluster trước migrate/seed, không dựng launcher cạnh tranh |

Chưa đọc `.env`, connection JSON, `postgresql.conf`, `pg_hba.conf`, SQL row hoặc log có thể chứa dữ liệu; chưa gọi pg_ctl/pg_isready/service query/start/stop. Trạng thái service/process và khả năng cold-start thật còn phải root kiểm sau release, không lấy metadata làm PASS.

## 2. Phương án đề nghị: helper nhỏ gọi pg_ctl trên cluster đã có

Thêm helper có thể review trong code được phép (`tools/` hoặc package hạ tầng hiện có), caller từ nút mở DEMO. Input là **runtime path + data-dir path + endpoint local đã được cài đặt/whitelist**, không password/DSN. Những đường dẫn này lấy từ cấu hình runtime không bí mật được root cài một lần hoặc relative parent layout rõ; không quét toàn ổ đĩa/tự nhận mọi PostgreSQL trên PATH.

Luồng xử lý:

1. **Xác nhận identity:** resolved binary/data-dir nằm đúng runtime/cluster được chỉ định; PG_VERSION tương thích; endpoint127.0.0.1:5432; quyền truy cập đủ. Không sửa bất kỳ file cluster nào để “sửa startup”. Cấu hình sai/không truy cập được phải lỗi riêng, không coi là cluster chưa tạo.
2. **Serialize startup:** một lock/mutex có danh tính cluster dùng chung cho các lần bấm. Không tạo/cắt/xóa `postmaster.pid` hoặc lấy lock bằng xóa file. Hai launchers cùng lúc không spawn hai postmasters; caller sau kiểm lại status/ready và tái dùng.
3. **Status + ownership:** dùng pg_ctl status cho đúng data-dir và đối chiếu OS/listener PID, executable và commandline/data-dir chính xác trước reuse/action. Không dựa tên python/postgres chung hoặc substring path. Nếu listener thuộc cluster khác, status/port mâu thuẫn hoặc không xác minh được owner → thông báo/cổng lỗi, không terminate hay giành port.
4. **Đang chạy đúng cluster:** dùng lại, không restart/stop/register/cài lại; kiểm readiness loopback rồi tiếp tục bootstrap. App/DB/admin identity vẫn phải được kiểm ở bước dưới, pg_isready chỉ là server readiness.
5. **Đã xác minh chưa chạy:** gọi binary pg_ctl hiện có với action **start**, data-dir hiện có, wait/timeout hữu hạn và **log mới duy nhất**, bind host/port explicit. Dạng lệnh là `pg_ctl start -D <existing-data-dir> -l <new-retained-log> -w -t <timeout> -o "-h 127.0.0.1 -p 5432"`. Đây là mô tả contract CLI, chưa được chạy lần này. Không initdb/register service/Start-Service mới, không xóa lock khi start lỗi.
6. **Khởi chạy ẩn và lỗi sạch:** nếu dùng Start-Process phải `-WindowStyle Hidden`; nếu Python subprocess, dùng lựa chọn Windows tương ứng, không bật console hoặc gọi shell dựng chuỗi có secret. Không DSN/password trong pg_ctl args. Log/status mới theo UTC+PID+nonce và create-new semantics, giữ mọi retry/log cũ.
7. **Ready đúng identity rồi bootstrap:** validate **cả app và admin** từ mọi đường JSON/env/direct helper trước side effect, explicit loopback/endpoint/DB; sau connect local xác nhận DB/cluster thực và app ordinary non-owner. Migrate/seed bằng admin riêng, request thường bằng app; không “SAN_SANG” chỉ vì schema version trên DB khác trùng nhau.

Nếu đã có **Windows service thực sự được root xác nhận** trỏ đúng binary/data-dir/endpoint, có thể reuse start của service đó theo cùng ownership gate thay nhánh pg_ctl trực tiếp. Không auto-register, nâng quyền/UAC hoặc gọi installer chỉ vì service không có. Root chọn một cơ chế đúng hiện trạng sau read-only host check; default không giả service đã được cài từ một script có nhánh register.

Không coi mọi nonzero pg_ctl status là “not running”: phân biệt unknown/access/config/runtime error theo contract CLI được kiểm trước code. Timeout/port busy giữ log và trả lỗi; không kill PID lạ, không reset data, không loop vô hạn. Nếu D: không sẵn sàng, báo đường dẫn unavailable, không tạo cluster mới ở ổ khác.

## 3. Ghép với sửa validation và local setup

`REVIEW-CRM-KHOI-DONG-03.md` đã có28pure/stubcase,9FAIL. Bước start cluster không che các lỗi đó: host thiếu/env/service, hostaddr/multihost, cùng dbname khác port, env server bỏ validator và direct helper admin-side-effect-before-app-validation phải được sửa/kiểm lại bằng pure/stub trước host.

Root tự tạo/quản local app/admin credentials và ACL ngoài phạm vi coder; không gửi cho Claude/chat/log/browser/CLI. Local setup runtime paths không secret phải tách khỏi tệp credentials. Khi runtime thiếu hoặc credential chưa được cài, UI/status nói đúng trạng thái cần chuẩn bị, không silent fallback kho thật/DSN khác hoặc bắt Anh tự gõ SQL.

Guard file/DB/role và no-bytecode kế thừa tới bootstrap/server/child processes; helper không gọi cleanup. Source/runtime identity và logs có manifest/hash, nhưng không đưa các secret values vào receipt/evidence. Không đọc toàn bộ environment/process commandline để ghi log.

## 4. Ca kiểm trước nghiệm thu cold-start

- **Pure helper cases:** runtime/data-dir sai, PG_VERSION không tương thích, access denied, status unknown, listener khác/PID mismatch, đúng cluster đang chạy, đúng cluster chưa chạy; parser/wait timeout; guard và argv không secret. Stub pg_ctl/service/process để kiểm call order và không có install/init/delete/stop.
- **Hai launchers:** serialized status/start, chỉ một owned start, logs không overwrite, retry hữu hạn. Có positive control thật sau source freeze; timeout/setup tách khỏi business fail.
- **Host running path:** root cho phép host execution, đi đúng nút/code path; reuse cluster đang chạy đúng PID/data-dir/port, migrate/seed DEMO đúng DB, app ordinary non-owner; first/reopen không duplicate seed/data.
- **Host cold path:** chỉ khi root có cửa sổ an toàn và cluster đúng ownership; không tự stop shared PG để tạo case. Khởi động lại đúng cluster cũ, DB/hồ sơ/lô/source hash/history giữ; không tạo cluster khác. Chưa có cửa sổ thì NOT_RUN, không suy từ running path thành cold path PASS.
- **Web OS restart/persistence:** dừng chỉ server do probe sở hữu, mở process mới bằng launcher; dữ liệu/lô/export bytes và role/registry giữ. Không dùng LocalApp mới trong cùng interpreter để thay OS restart.
- **GUI:** công cụ đang khả dụng và thao tác thật trên DEMO mới ghi đã bấm; host NoBrowser/HTTP không thay GUI hoặc tải tệp thực.

Đây là phương án reuse cụ thể để root review/giao repair04; chưa phải permission chạy host, cài đặt hoặc quyết định production. Không sửa product/khởi động/dừng gì trong nhiệm vụ nghiên cứu này.
