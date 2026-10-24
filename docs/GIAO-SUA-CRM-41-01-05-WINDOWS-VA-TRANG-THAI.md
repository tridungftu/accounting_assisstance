# CRM-41-01 FIX05 — Windows và trạng thái phục hồi

Root giao một lượt CODE_ONLY hữu hạn, cùng Claude session, bám quyết định một engine #6. Không mở lại kiến trúc, thuật toán, catalog hay workflow. Chỉ sửa đúng 5 existing files, NEW0:

- docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py
- docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py
- src/kho_tri_thuc/nguon/trich_chung_6.py
- tests/test_trich_chung_6.py
- docs/BAO-CAO-CRM-41-01.md

Baseline: FIX04 đã terminal exit0/empty Job, 370 source/438 runtime; đúng 6 existing đã đổi, không có file mới. Mã source thật vẫn ở bản đã kiểm trước FIX04; coder không ghi vào dự án nguồn. Giữ nguyên source server route, UI, CRM service, M4 adapter, M9, migrations1–20 và mọi assertion cũ. Self-test mã sửa mới = NOT_RUN.

## 1. Lỗi Windows đã tái hiện khi ba caller dùng cùng ý định

Root chạy 24 ca client/projection/wiring: 23 PASS, 1 FAIL, 0 error/skip. Test `test_f2_hai_caller_cung_y_dinh_mot_luot` nhận TRICH6_DUONG_DAN_Y_DINH. Probe độc lập giữ traceback locals tái hiện sau 5 lần: `_thu_muc` có goc dạng `D:\...\trich6-y-dinh`, còn d và d.parent dạng extended path `\\?\D:\...` khi thư mục dài mới xuất hiện; đó là cùng thư mục vật lý nhưng so sánh Path khác biểu diễn trả false.

Sửa so sánh canonical Windows/containment cho cả tồn tại và chưa tồn tại, vẫn giữ đường đã resolve và hash tên ID, vẫn chặn thoát gốc/junction/symlink. Không tắt guard, bỏ containment, bỏ mọi dấu prefix một cách không kiểm soát hoặc nuốt lỗi. Thêm ca deterministic đường dài + canonical prefix và chạy đồng thời; giữ assertion đúng 3 kết quả, 1 luot, 1 start và join/exception đầy đủ. Giữ các ca ID có dấu `:`, `.`, `..` được băm an toàn và đường thoát bị chặn. Không đổi expected để bỏ caller lỗi.

## 2. Ý định có thể đã có hiệu lực phải giữ UNKNOWN khi preflight đổi

FIX04 gọi `nang_luc` trước khi đọc ý định bền và ngoài try. Lịch: create đã được nguồn chấp nhận nhưng ACK sai/mất → client ChuaRo và có 00_yeu_cau; lần thử lại cùng raw/type/ID gặp preflight404/not-ready/catalog khác hoặc endpoint cấu hình mất → hiện có thể thành DataError lỗi cuối dù ý định cũ có thể đã tồn tại/chạy.

Tra cứu và kiểm ý định cũ bằng thao tác chỉ đọc; giữ phân loại UNKNOWN cho availability/preflight failures của ý định có thể đã có hiệu lực. Ý định mới gặp preflight không hỗ trợ vẫn phải lỗi rõ, ZERO POST và ZERO ghi ý định. Không dựng state DB/lifecycle framework mới; có thể bảo thủ UNKNOWN khi hồ sơ bền chưa chứng minh kết quả cuối. Test lịch ACK sai → preflight lỗi → không POST thêm/không đổi raw/body/key → phục hồi đúng preflight/ACK thì nhận đúng luot cũ và một compute. Giữ xung đột khi body khác, không tự sinh khóa mới.

## 3. DTO timestamp phải hữu hạn và format được trên máy hiện tại

Source `_kiem_dto_luot` gọi math.isfinite trên int tùy ý trước bound; JSON hợp lệ `10**400` (401 chữ số) gây OverflowError rồi generic500. Bound năm9999 cũng chưa bảo đảm time.localtime/strftime chấp nhận trên Windows.

Kiểm type/range trước chuyển float; chuyển/render timestamp phải thành _Hong có lý do nếu không hợp lệ, không generic500. Giữ finite UNKNOWN qua status/list/viec/raw/view/replay và không ghi đè/rerun. Mở rộng C21 bằng huge integer literal và conversion failure có kiểm soát trên timestamp DEMO để kiểm đường format; không sửa global legacy time behavior hay date policy khác. Giữ các ca float1e300/negative/bool/tep/path đã có.

## 4. Reservation ghi dở không được im lặng bỏ qua rồi cấp lượt khác

`_tim_dat_luot` bỏ qua _Hong của slot record. Nếu dừng giữa ghi `_common_dat_luot/<slot>.json` và registry, slot malformed/ghi dở bị coi như không có, rồi retry chọn slot mới. Khi binding chưa kiểm được phải trả UNKNOWN có lý do, không tạo registry/link/slot/luot khác. Không khôi phục bằng cách xóa hay viết đè record cũ. Test CreateNew backup, mô phỏng partial slot trước registry, snapshot mọi path/hash/bytes sau mutation; retry không tạo gì thêm, không compute; giữ positive crash sau slot hoàn chỉnh đã được C19 kiểm.

## 5. C22 là kiểm common immutability/legacy forwarding, không được ghi workbook nguồn thật

C22 mới thêm đang gọi writer workbook thật ở legacy positive: đọc MAU_DANH_MUC_HD nguồn và os.replace lên copy đã có. Không thay guard hay thuật toán writer để chiều test.

Giữ nguyên common pending/done, có/không ten: exact COMMON_BAT_BIEN, sentinel writer zero calls và snapshot zero effect. Đổi riêng legacy positive mới này sang owned DEMO writer spy/stub, bind template/output DEMO, kiểm được forwarding đúng args và đúng một call/response. Ghi rõ đây là legacy route/forwarding positive; full workbook writer I/O là NOT_RUN trong ca này. Không gọi đây là workbook round-trip đã đạt; không bỏ qua test hoặc sửa 18 assertion cũ.

## 6. Kết thúc

Chỉ Read/Glob/Grep/Edit/Write trong allowlist. Không shell/import/AST/tests/runtime/SQL/network/Agent/MCP/cloud, không đọc var/.env/bí mật/dữ liệu thật. Không xóa file. Sửa đủ bốn lỗi và boundary test mới, giữ mọi ca đã đạt; report existing nói rõ phần thực sửa/chưa sửa, self-test NOT_RUN và phạm vi mock/real. Root sẽ freeze, review và tự chạy kiểm; chưa gọi toàn M4/CRM/M2 xong.
