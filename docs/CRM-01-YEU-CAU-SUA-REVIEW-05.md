# CRM-01 — hoàn tất chain cấu hình và runtime nút mặc định

19/10/2026. Sửa hẹp tiếp cùng session sau CLI60630 terminal exit0. Root freeze123file, manifest SHA256 `8a0f52db26e6645b1c26370c8135e1672045f0970c10a22f28d0662426c66ec9`. Chưa chạy host/launcher/coldstart/GUI. Không sửa lại CRM/parser/M1/schema; chuyển M9 ngay sau gate nút đủ bằng chứng.

## 1. P1 — JSON hợp lệ bị chặn khi bootstrap kiểm lần hai

Root kiểm pure/stub sau terminal, đủ123hash trước/sau, guardactive,0network/SQL. Chuỗi **doc_ket_noi→chuan_bi** với cùng host127.0.0.1/port5432/DBkho_crm_demo fake và hai userfake không password: `doc_ket_noi` thành công, nhưng `chuan_bi(parsed)` trả `KET_NOI_KHOA_KHONG_HO_TRO`, connectorcall0. Evidence private giữ, root không yêu cầu Claude đọc var.

Nguyên nhân từ final04: normalization dựng conninfo có `hostaddr` loopback; `doc_ket_noi` trả normalizedconninfo; `chuan_bi` gọi `kiem_cap/chuan_hoa_dsn` lại, nơi hostaddr nằm ngoài allowlist. Selftest từng hàm với inputraw không chứng minh được chain của nút.

Sửa normalization/typed validated config **idempotent trên đầu ra hợp lệ** mà giữ chặn remote/implicit/service/sameendpoint trước sideeffect. Không bỏ vòng validation để tin dict caller hoặc trả lại raw khiến PGHOSTADDR/PGSERVICE đổi target. Nếu nhận hostaddr thì kiểm literal loopback và tương thích chính host rõ, không nhận remote/multihost/options/service. Có ca dương raw→JSON→bootstrap thực đến connectorstub; normalized→normalize; env→server→connector, cùng ca âm nguyên28 được giữ ý nghĩa. Testgọi bootstrap thật với fakeconnector, không mock bỏ đúng bước gây lỗi.

## 2. Runtime mặc định phải chạy được ngoài môi trường kiểm của Codex

Root kiểm stdlib/runtime metadata, không product/SQL:

| Runtime/context | Python | openpyxl | psycopg | guard startup |
|---|---|---|---|---|
| Bundled do start-web hiện ưu tiên |3.12.14|có|không|không|
| PATH với coordinator private userbase |3.13.14|có|có|có|
| PATH **không** private PYTHONUSERBASE/PYTHONPATH |3.13.14|có|không|không|

Nút cmd mặc định không truyền PythonExecutable. Root không coi NoBrowser với override/environment private là bằng chứng Anh click dùng được. Hai note runtime đã thêm muộn trong request04 có thể chưa được đọc lúc coder sửa.

**Dùng lại tài sản đã có, không tải/cài lại:** Codex có Python3.13.14 và các package psycopg[binary]/tzdata3.13 cục bộ, sẽ copy vào runtime riêng của app sau source review; không sửa dependency bundle. Codex quản lý nonsecret runtime config và retentionbootstrap, credentials localJSON+ACL riêng. Claude không đọc privatevar/.env/package cục bộ hoặc credential để tìm đường dẫn; định nghĩa interface nhỏ trong launcher và báo cáo để root cấu hình.

Đề nghị interface `<DataRoot>/crm-demo/runtime.local.json` phien_ban1, Python executable tuyệt đối, danh sách dependency directories và guard/bootstrap directory do root quản lý (tên field cụ thể coder ghi rõ). Không chứa DSN/password/token. Nếu có lựa chọn kỹ thuật đơn giản hơn vẫn đáp ứng clean-click thì dùng và ghi contract cụ thể; không phụ thuộc private test env. Không thay config/rootthat hoặc cài global package/environment.

Launcher phải:

- Chọn explicit PythonExecutable hợp lệ nếu có; mặc định đọc app runtime config/candidates rồi probe **capability thực** Python3.11+,openpyxl,psycopg và retention nếu đã cấu hình. Không mặc định bundled luôn đủ; không silent fallback làm mất CRM.
- Cùng executable/dependency path/guard/no-bytecode áp dụng cho capability probe, bootstrap và server child. Không ghi đè PYTHONPATH chỉ cònsrc làm mấtdeps; quote đường dẫn có khoảng trắng đúng và giữ môi trường caller sau khi spawn.
- Root cung cấp guard đãreview khi cấu hình giữ file; không tắt/né guard để launch xanh. Python isolated không nhận env phải được phát hiện, không nhận như runtime đủ. Không chỉnh Python._pth/dependency bundle hoặc quyền global để chữa.
- Thiếuconfig/driver/runtime báo mã sạch cụ thể, giữ log/status riêng. Nút mặc định đã root cài runtime không yêu cầu Anh gõ lệnh, setenv hay nhập DSN.

Không khởi động/dừng PG/launcher thật ở lượt coder. Test nhỏ có ý nghĩa cho chain normalize, selected runtime/dependencyinheritance, explicit override, missingdriver/isolated, cùng bootstrap/server môi trường; dùng stub và kiểm argv/env, không fake cả resolver rồi gọi e2e. Giữ cold helper04, validator04, role/endpoint đã viết; root sẽ kiểm chúng độc lập trên final05 để tránh chạy lặp interim.

## 3. Bàn giao

Chỉ src/tests/tools/docs +start-web.ps1/MỞ BẢN DEMO.cmd như quyền hiện tại. Không xóa file/temp/DB/role, reset/clean/commit; migration1–12 bất biến. Không đọc/transmit dữliệuthật hoặc nguồn ngoài authorized. Giữ guard+PYTHONDONTWRITEBYTECODE. Root quản lý CHANGELOG/HANG/coverage.

Cập nhật BAO-CAO-CRM-01-DEMO.md: selftests thật và interface runtime config, kết quảpass/fail/setup/skip riêng, những gì host/GUI chưa chạy. Không tự nghiệm thu. Full M0–M10/9receiver/L1–L12 vẫn là đích, M9 typed binding đang được root hoàn thiện, không xây lại app vay/review xây dựng/knowledge engine.
