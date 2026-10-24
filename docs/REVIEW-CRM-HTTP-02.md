# CRM-01 — kiểm HTTP độc lập sau lượt sửa 02

Ngày 19/10/2026. **23/23 ca đạt, 0 fail, 0 setup error.** Kết quả này xác nhận phạm vi HTTP dưới đây; CRM/toàn M3 và chương trình cây 33 chưa được nghiệm thu.

Claude handle **51099** đã kết thúc thực sự, exit 0, trước khi chạy. Receipt và 117 file src/tests/tools được đóng băng, sao chép và kiểm SHA256 tại `var/codex-dieu-phoi/kiem-chung-20261018-101441/crm02-handoff-20261019-071834-580/`; manifest SHA256 `5d85cd7b822c3ae09e0b88d83421309904307a905d29da4f639fc5de933a44f2`.

Probe độc lập: `var/codex-dieu-phoi/crm-http-independent-probe-02.py`. Evidence: `var/codex-dieu-phoi/crm-http-independent-02-20261019-071914-01a98f/result.json`. Chạy HTTP loopback thật, hai CookieJar riêng, actor `MO_PHONG_*`, hai pháp nhân DEMO. Kết nối ứng dụng là LOGIN thường, không superuser, không BYPASSRLS. Kho thật không được mở. File, DB và role kiểm thử được giữ lại; no-delete guard hoạt động, không lưu token/credential.

## Kết quả đã chứng minh

- Hai phiên nhận cookie CRM riêng từ server. Đổi phiên B sang KT_B/CFO không đổi danh tính hoặc phạm vi PN_A của A; A không kiểm hợp đồng B hay nhận quyền CFO từ B. Bốn vi phạm isolation của lượt 01 không còn tái hiện.
- Không token bị HTTP 403; body giả actor bị từ chối. KT không duyệt được trước/sau các lần đổi phiên. CFO chỉ V3 không hoàn tất hợp đồng mới còn V4.
- Control dương trên **chính phiên bản vừa bị từ chối**: phiên CFO đủ quyền duyệt thành công; A vẫn là KT_A. Lịch có đúng ba dòng 300.000.000 / 1.200.000.000 / 1.500.000.000 VND và V4 đã duyệt. Không dùng tập rỗng hoặc workflow hỏng để gọi negative đạt.
- KT_A xuất file soát qua HTTP và tải bytes thực: **9.160 bytes**, SHA256 khớp registry, header attachment. Openpyxl đọc đủ bốn sheet, đúng ba dòng tiền ở `LICH_NGHIA_VU`, không có formula. KT_B bị chặn tải file PN_A; tải không token bị 403.
- Đóng server/connection và tạo lại LocalApp/server trên cùng DB/workspace trong **cùng tiến trình Python**: phiên bản đã duyệt và registry lô còn nguyên, tải lại cùng bytes/hash. Đây là kiểm mở lại các đối tượng ứng dụng/kết nối, chưa phải restart tiến trình hệ điều hành hoặc nút launcher.

Sáu file được probe khóa hash trước/sau đều không đổi. JavaScript `giao_dien/assets/app.js` qua `node --check` exit 0; syntax check không chứng minh thao tác UI.

## Giới hạn còn giữ

Chưa bấm giao diện bằng browser; công cụ điều khiển GUI hiện không có trong phiên. Nút mở DEMO/first open/restart tiến trình đầy đủ chưa được kiểm. Danh tính chọn vai DEMO không phải production authentication. Kiểm này không chạy đường tiền M1, concurrency hai transaction, nâng cấp schema hoặc toàn bộ nghiệp vụ parser/phụ lục; các phạm vi ấy có probe độc lập riêng. Không suy 23 ca HTTP thành nghiệm thu CRM/M1/V13 hoặc vận hành thật.
