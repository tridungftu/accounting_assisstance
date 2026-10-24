# CRM — sửa hẹp JSON qua Windows PowerShell 5.1 trước M9

19/10/2026. CLI32050 terminal0, frozen125 manifest `b9bd8c6dd61af2df17ebc5ab4257681bd28caafdee7654406a6a015f835fde82`. Tiếp tục **cùng session**, không đổi migration1–12, CRM/parser/M1/domain. Mục đích là nút Windows mặc định; không thêm tính năng hoặc chạy lại các suite SQL đã đạt.

## Lỗi P1 đã tái hiện trên máy Anh

Root đã cấu hình runtime app bằng Python3.13, dependencies và guard riêng; không cần Claude đọc var/config/credentials. `tools/chon_runtime.py` probe thật báo `crm=true`, cả ba thư mục dependency dự kiến có tồn tại. Khi nút CMD gọi **Windows PowerShell5.1**, JSON stdout được decode bằng Console codepage **437**, pipeline OutputEncoding **20127**. Sau ConvertFrom-Json, `pythonpath` **khác chuỗi dự kiến**, cả ba thư mục decode đều không tồn tại (chuỗi đúng cả ba tồn tại). Đường dẫn repository có tiếng Việt và khoảng trắng.

Kết quả bootstrap `RUNTIME_THIEU_DRIVER`, rồi server không tìm được `kho_tri_thuc`. Runtime log UTF8 trên đĩa giữ đúng đường dẫn và crm=true. Đây là hỏng **machine JSON transport Python→PS**, không phải thiếu package. Source125 giữ nguyên trước/sau repro; probe encoding không chạy SQL/server.

`tools/chon_runtime.py:171` hiện print JSON ensure_ascii=False. `tools/chuan_bi_crm_demo.py:70` cũng vậy; audit cả machine JSON đi qua PS. Phương án nhỏ phù hợp là stdout JSON ASCII-escaped (json.loads vẫn hồi phục nguyên Unicode), log UTF8 riêng giữ nguyên. Hoặc sửa decoding cục bộ có restore đầy đủ, nhưng không đổi codepage/encoding global/cài lại Python/dependencies/đổi tên folder/junction để né đường dẫn. Không hardcode đường dẫn máy.

## Phạm vi sửa và kiểm chứng

- Giữ interface/giá trị JSON, normalize/validator/role/endpoint/cluster helpers đã qua review. Không nới guard/quyền hoặc fallback runtime sai để xanh.
- Kiểm hồi quy có ý nghĩa: Unicode path có dấu/khoảng trắng roundtrip **qua byte transport codepage437/ASCII** vẫn đúng, stdout chỉ ASCII khi dùng phương án escaped; JSON stdout/runtime config giữ đủ src/deps/guard. Gọi main/CLI thật có fake resolver/probe cần thiết; không chỉ json.dumps trong test tách khỏi production code.
- Machine status bootstrap có thông điệp Unicode vẫn parse đúng; file log UTF8 không bị mất Unicode. Giữ parent environment restore/no-bytecode.
- Coder không chạy launcher/PG/HTTP/Windows thật; root chạy lại exact Windows5.1 probe, defaultCMD first/reopen, file export và restart sau terminal/freeze. Không gọi pure Python resolver là bằng chứng click.
- Chỉ chạy targeted unit cần thiết cho thay đổi, không rerun SQL/web rộng khi không đổi chúng. Báo pass/fail/setup/skip riêng trong BAO-CAO-CRM-01-DEMO.md, chưa tự nghiệm thu.

Root đã xử lý riêng tương thích retention: bootstrap app giữ `.raw-*` file tạm dưới var/web thay vì ném PermissionError sau immutable hardlink; original guard/private test policy giữ nguyên. Không sửa product write_immutable hoặc xóa file để chữa. Lượt HTTP trước đó chỉ có raw file, **0 hồ sơ/0 hợp đồng/0 file xuất/0 tiền**; server cũ đã dừng qua shutdown ứng dụng, PostgreSQL không dừng. Không cần Claude đọc evidence private hoặc thử lại host.

## Giới hạn vẫn áp dụng

Claude là coder chính, Codex kiểm độc lập. Chỉ nguồn nội bộ đã được Anh cho phép: src/tests/tools/script mở/pyproject/test.ps1 và tài liệu kỹ thuật đã lọc. Không đọc/transmit var/.env/backups/dữ liệu thật/secrets/source phần mềm khác. **Không xóa bất kỳ file/temp/DB/role; không reset/clean/commit; giữ guard và PYTHONDONTWRITEBYTECODE.** Root giữ CHANGELOG/hàng đợi/coverage. Không CFO_NTD, duyệt/nhập thật, cloud AI, Junsky mức2.

M9 binding `28af9c1045c8da5448056baa45b679fd476f48aaa40d897ff92430764b168bc5` đã root duyệt ở mức contract để giao code sau gate này. M2 cũng đã đóng5/5 findings ở mức contract; M5/M6–M7 đang review. Toàn M0–M10/9receiver/L1–L12 là mục tiêu; không thu hẹp thành kho tri thức và không xây lại review xây dựng/app vay.
