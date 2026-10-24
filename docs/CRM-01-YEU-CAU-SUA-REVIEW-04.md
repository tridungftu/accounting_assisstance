# CRM-01 — sửa phần khởi động DEMO sau review03

19/10/2026. Sửa có mục tiêu trong cùng session. Claude89659 đã terminal exit0; Codex đã kiểm độc lập trên frozen121file. SQL73criterion, parser27criterion, HTTP23criterion và sáu nhóm M1 chọn lọc đạt; không làm lại CRM/core. Toàn phạm vi vẫn M0–M10/9receiver/L1–L12 file33, bước tiếp theo M9 tái sử dụng phần mềm nguồn.

## 1. Phần đã đạt và giới hạn

Đọc `REVIEW-CRM-K2-MIGRATION-03.md`, `REVIEW-CRM-NGUON-VA-PARSER-03.md`, `REVIEW-CRM-HTTP-03.md`, `REVIEW-CRM-M1-03.md` và `REVIEW-CRM-KHOI-DONG-03.md` khi hiện diện. M1 trướcHĐ344/sauHĐ131 đúng fact, tiền cũ không đổi khi HĐ đến sau, retry giữ3BANK/3proposal/6line kể cả PK. Negative nguồn sai core_hash nativeexit1/da_ghi=false trước ghi;27bảng business và audit không đổi. Đây không phải fullM1/G10/GUI/toànCRM. Không sửa expected hoặc nhãn báo cáo để làm xanh.

## 2. Chặn cấu hình không rõ trước mọi side effect

Pure/stub độc lập28ca=19đạt/9fail, không mạng/SQL thật. Các fail:

- E01–03: thiếu host nhưng có PGHOST/PGHOSTADDR/service vẫn accepted; `kiem_dsn` tự thay thiếu host bằnglocalhost trong khi libpq còn có thể lấy môi trường/service.
- C04: hai DSN cùng dbname khác port vẫn accepted.
- D03–05: direct `chuan_bi` không validate appDSN và cặp target trước adminconnect/migrate/seed. Remote app hoặc khácport vẫn SAN_SANG dưới stub; khácDB chỉ bị từ chối sauseed.
- S02–03: server lấy DSN qua env bỏ qua validator, remote/nonDEMODB tới connector trap.

Sửa chung một lớp normalization/validation, dùng lại cho localJSON, direct bootstrap và env server. Kiểm cả hai DSN trước connect/create/migrate/seed. Yêu cầu endpoint loopback rõ và cùng host/port/dbname đã chuẩn hóa; không dựa vào stringdbname. Cấu hình service/implicit endpoint phải fail closed hoặc chuyển thành target tường minh đã kiểm trướcconnect, không đọc servicefile ngoài phạm vi. Môi trường PGHOST/PGHOSTADDR/PGPORT/PGSERVICE không được đổi target sauvalidation. Không reject mọi input để qua ca âm: literal127.0.0.1/localhost/::1 hợp lệ và cặp cùng endpoint vẫn cần positivecontrol.

Server DEMO env chỉ cho target DEMO/test được định danh; không mở arbitrary DB chỉ vì localhost. Duy trì fixture test riêng có tên `kho_test_*`/`ktt_test_*` bằng điều kiện fixture rõ, không nới kho thật. Admin/app phải cùng target; không trả credential qua lỗi/log/browser. Login ứng dụng thường/memberapp_web, khôngsuper/BYPASSRLS; không dùng role owner nghiệp vụ. Metadata owner/endpoint/schema được kiểm bằng positivecontrols thực sau khi Codex cấu hình cục bộ. Chưa có config phải báo thiếu rõ và app khác vẫn mở được; môi trườngthat bỏ qua hoàn toàn bootstrap.

## 3. Nút mở DEMO khi cluster chưa chạy

Final callchain cmd→start-web→tool→bootstrap hiện không startcluster. Hoàn tất yêu cầu đã giao trong review03 bằng **runtime và cluster hiện hữu**, không cài/register/init lần nữa:

- Parentworkspace `D:/Claude/Phan mem ho tro ke toan`; runtime `var/postgresql16-16.15-runtime/bin`; cluster `var/postgresql-ktt-16/data`, PG_VERSION16; server16.15 loopback127.0.0.1:5432, không Windowsservice.
- Binary pg_ctl.exe SHA256 `bed9ec9686fdf66b407f55d15be2466365827feb6b343fdb452c2dbcfbcfe0a1` do Codex kiểm metadata. Claude không đọc parentvar, config/secret hoặc privateinstaller; các facts trên đủ để viết helper dùng đường dẫn đã định danh. Codex sẽ kiểm và chạyhost.
- Tận dụng launcher hiện có. Kiểm status/identity/data directory/port trước; khi đúng cluster đã chạy thì reuse; khi cluster được định danh đang dừng và port không bị tiến trình khác chiếm mới start. Không stop/kill tiến trình lạ, không xóa pid/lock, không init/install/register/UAC. Nếu không chứng minh ownership thì dừng bước CRM với lỗi rõ.
- Start hidden, loopback, serialize theo cluster và bounded readiness, log riêng từng lần; không log DSN/password, không overwrite/xóa log cũ. Không đưa command hay adminDSN lên browser. Không startcluster trong request HTTP; đây là bước chuẩn bị launcher trước bootstrap khi configfixture hợp lệ.
- Mở lại cùng DB/root/profile, không resetseed tạo hồ sơ/lô trùng. Giữ root/config thật và SQLite hiện tại.

Codex quản lý secret localJSON+ACL và ordinaryrole sau source review. Không hardcode credential, đọc `.env` hoặc tìm secret. Không cần yêu cầu Anh gõ lệnh hoặc nhập DSN.

**Bổ sung runtime host08:03 khi lượt04 đang chạy:** preflight chỉstdlib (không product/SQL) trên máy này cho thấy Python bundled mà launcher hiện ưu tiên là3.12.14, `psycopg_available=false`, không nạp guard từ PYTHONUSERBASE đã đặt. Python mặc định trên PATH là3.13.14, `psycopg_available=true`, guardloaded=true. Nút cmd không truyền PythonExecutable mặc định. Vì vậy phải chọn runtime theo capability thực openpyxl+psycopg và nạp src/guard đúng, không mặc định bundled luôn đủ. Reuse Python đã sẵn sàng, không sửa/cài package vào dependency bundle hoặc bắt Anh truyền CLI. Giữ explicit -PythonExecutable nếu hợp lệ; không silent thay bằng runtime thiếudriver. Codex kiểm default cmd path riêng; chạy NoBrowser với overridePython không thay bằng chứng nút mặc định.

**Làm rõ môi trường08:07:** PATH3.13.14 chỉ có driver khi coordinator đặt PYTHONUSERBASE riêng; khi bỏ PYTHONUSERBASE/PYTHONPATH thì openpyxl=true nhưng psycopg=false, guard=false. Không coi process môi trường kiểm đã đủ là môi trường click của Anh đã đủ. Driver/binary3.13 đã có cục bộ dưới repo, Codex có thể triển khai bản copy dependency vào runtime riêng của app và nonsecret cấu hình đường dẫn sau review; không truyền secret hoặc yêu cầu tải/cài lại. Nếu launcher cần runtime config thì định nghĩa interface nhỏ rõ PythonExe/dependencyroot/retentionbootstrap, dùng mặc định nút bấm và child process thật, Codex cấu hình một lần; không phụ thuộc private test overrides hoặc caller shell đã được chuẩn bị.

Đọc thêm `CRM-03-TAI-SU-DUNG-KHOI-DONG-PG.md`. Theo [tài liệu PostgreSQL16 pg_ctl](https://www.postgresql.org/docs/16/app-pg-ctl.html), `status` code3 là server không chạy, code4 là thiếu/không truy cập được data directory; không coi mọi nonzero là đượcstart. Startup timeout có thể vẫn tiếp tục nền nên kiểm identity/status lại, không spawn lặp hoặc xóa lock. Root không tự stop sharedcluster chỉ để tạo ca cold-start; khi chưa có cửa sổ host thì báo NOT_RUN, không giả từ stub thành đạt.

## 4. Kiểm và bàn giao

Thêm test có ý nghĩa cho9ca validation, đối chứng hợp lệ, environmentthat bỏqua, cold/reuse/foreignport/ownershipfail và khôngsideeffect. Stub được ghi rõ làstub. Không chạy launcher/startstopcluster thật trong lượt coder; Codex chạyhost sau terminal với configđãreview. Không bịa GUI/OSrestart đạt. Giữ các kiểm parser/M1/SQL liên quan đúng phạmvi; không broadrepeat khi không sửa chúng.

M0001–M0012 đã có DB thật được giữ; **không đổi statement/checksum1–12**. Nếu thật sự cần SQL mới thì append, khôngrewrite; ưu tiên sửa cấu hình/launcher khôngschema. Giữ guard khôngxóa+PYTHONDONTWRITEBYTECODE; không xóa file/temp/DB/role, không reset/clean/commit. Mọi thao tác `.env`/privatevar/dữliệuthật/secret ngoài quyền bị cấm. Claude chỉ sửa src/tests/tools/docs và hai launcher đã cấp quyền; rootCHANGELOG/HANG do Codex cập nhật.

Cập nhật `BAO-CAO-CRM-01-DEMO.md` với kết quả thực, filechanged, selftest/setup/skip và phầnchưađạt. Kết thúc rõ exit, không lặp vô hạn. Sau terminal Codex kiểm độc lập rồi chuyển M9 core binding đã chuẩn bị; đây không mở production/Junsky/cloudAI/CFO_NTD hoặc thay quyền vận hành.
