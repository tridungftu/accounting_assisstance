# CRM-01 — yêu cầu sửa review 03 và hoàn tất nút mở DEMO

Ngày 19/10/2026. **Đầu bài đã hợp nhất sau bàn giao 02; toàn bộ probe độc lập đã kết thúc trước lượt sửa03.** Cùng session, sửa có mục tiêu, không viết lại CRM/core. Phạm vi cuối vẫn toàn cây 33; CRM là phần nền M3/M1 cần đạt để chuyển M9.

## 1. Bản bàn giao và phần đã kiểm

CLI51099 đã terminal exit0. Source/test/tool snapshot 117 file được giữ riêng; schema hiện11, profile2. HTTP độc lập23/23: isolation hai cookie phiên, quyền KT/CFO/V3/V4, xuất và tải XLSX bytes/cell, mở lại LocalApp/connection trong cùng process đều đạt. JavaScript syntax check đạt. Parser25criterion=23đạt/2P1,18source-format báo riêng. Không coi selftest17đạt/1skip hoặc HTTP là nghiệm thu toàn CRM. Xem `REVIEW-CRM-HTTP-02.md`, `REVIEW-CRM-NGUON-VA-PARSER-02.md` và `REVIEW-CRM-K2-MIGRATION-02.md` khi có.

Không làm lại các nhóm đã đạt nếu không cần cho sửa hiện tại. Không xóa file/temp/DB/role, reset/clean/commit hoặc thay expected theo output. Không đọc var/.env/backup/row thật/credential; Codex cung cấp số tổng hợp và lỗi DEMO. Không production approvals/CFO_NTD, cloud AI, Junsky mức2 hoặc chuyển kho thật.

## 2. P1 — bảo vệ biên hiệu lực phiên bản đã duyệt

Direct SQL từ login thường/SET ROLE app_web, actor bán hàng CRM đúng PN nhưng không quyền duyệt, vẫn UPDATE `master.hop_dong_phien_ban.valid_to` của bản đã duyệt: đóng và mở lại, mỗi ca một row thay đổi. Nhánh bất biến hiện bỏ qua valid_to rồi RETURN trước kiểm quyền.

Phải chặn người gửi/reader/không đủ V3/V4 tự đóng/mở lịch sử, kể cả tự truyền actor hoặc chỉ thay valid_to. Đường CFO duyệt phụ lục đúng quyền vẫn đóng đúng predecessor trong cùng hợp đồng và đúng mốc hiệu lực; không chặn toàn bộ valid_to để làm hỏng replacement. Positive replacement UTC của probe độc lập đã đạt sau sửa fixture timezone, không coi lỗi fixture đó là product bug. Giữ lịch sử và audit, không cho sửa lại arbitrary boundary sau duyệt bằng SQL ứng dụng.

## 3. P1 — bốn helper SECURITY DEFINER vượt phạm vi

`master.da_lien_ket`, `master.da_lien_ket_dong`, `master.phien_ban_hieu_luc`, `master.van_tay_phien_ban` đang được app_web gọi với ID đã biết mà không kiểm đủ caller/PN/module. Tám ca độc lập tái hiện: actor CRM PN_A đọc dữ liệu PN_B, hoặc actor không module đọc PN_A. Positive fixture có amountA70/B60 nên không dùng số0 mặc định làm control giả; cả bốn helper có kết quả thật ngoài phạm vi.

Giữ helper cần thiết cho service nhưng kiểm danh tính ID/login khớp, pháp nhân/module/quyền trên chính ID tham số. Không để effective owner của SECURITY DEFINER bỏ qua quyền; không dựa chỉ vào service phía ngoài. Actor CRM chỉ được aggregate phù hợp trong phạm vi của mình; không bắt mọi viewer phải có quyền M1 raw chỉ để sửa leak. Kiểm thiếu/mismatched context và foreign IDs không lộ dữ liệu hoặc dấu hiệu tồn tại trái quyền; control own-PN hợp lệ vẫn làm việc.

ACL metadata còn xác nhận cả bốn helper có **PUBLIC EXECUTE**. Thu hẹp EXECUTE tới đúng role cần thiết trong migration mới, đồng thời sửa kiểm caller/scope; thu hồi PUBLIC riêng không đủ nếu app_web vẫn đọc chéo PN/module.

## 4. P1 — token số và currency của bằng chứng parser

Hai ca đúng structured source/Điều/Khoản, không manual:

- Raw D1 `40.000.000 VND`, quote `140.000.000 đồng`, D2=60m/tổng100m → hiện vẫn `CO_CAN_CU`, typed40m và lịch40+60, `chan=[]`.
- Raw D1 `1.000.000 VND`, quote `1.000.000 USD`, D2=99m/tổng100m → hiện vẫn `CO_CAN_CU`, typedVND1m và lịch1+99, `chan=[]`.

Giá trị phải có căn cứ theo token/kiểu/currency thực, không substring. Alias đồng/VND đã cấu hình tương đương vẫn phải đạt; raw khác currency quote phải giữ chờ, không tự quy đổi/relabel. Bảo toàn exact integer/locale/USD scale/%/NULL/0, các lỗi Suyra/optional/clause đã sửa; không chỉ chặn đúng hai chuỗi, không tự bật xác nhận thủ công mặc định.

## 5. Migration và kiểm thử

M0011 đã hiện diện trong DB DEMO được giữ lại. **Không sửa lại checksum hoặc statement M0001–M0011 để né nâng cấp.** Thêm migration mới có version cho các sửa SQL; fresh, exact schema11 đã có dữ liệu/approved history và các đường v9/oldM10 phải lên cùng đích. Giữ `schema_migrations`, audit tương thích cũ và dấu legacyHUY không bịa actor/time. Không drop hoặc tạo lại DB/role để chạy qua.

Selftest phải có ordinary LOGIN NOSUPERUSER/NOBYPASSRLS và positive controls trước negative, kiểm số row thực và trước/sau. Tách failure của guard/setup/skip khỏi đạt. Chạy tập liên quan và regression phù hợp; giữ guard + `PYTHONDONTWRITEBYTECODE=1`. Test gọi helper của điều phối theo allowlist; không đọc chứng cứ private hoặc tìm secret.

## 6. Nút mở DEMO cho người dùng cuối

Đọc và hoàn tất `CRM-01-BO-SUNG-BAN-GIAO-NUT-MO-DEMO.md`: nút hiện có phải mở được CRM trên PostgreSQL DEMO, không yêu cầu Anh gõ DSN/SQL. Launcher/root file chỉ được sửa trong các đường Codex cấp thêm rõ ràng; ưu tiên helper trong tools và shell có sẵn. Dùng runtime/cluster localhost đã tồn tại, không cài lại/UAC/dừng tiến trình lạ/xóa pid/lock. Kho thật và config thật giữ nguyên.

Bootstrap/migrate/seed dùng quyền local riêng; request DB thường dùng app_web non-super/non-BYPASSRLS. Credential nằm local được Codex cấu hình sau review, không hardcode/print/log/browser/CLI args hay đưa vào prompt. Không tạo nút chứa admin DSN hoặc nhận arbitrary đường dẫn nguồn từ client. First open/reopen giữ cùng DB/hồ sơ/lô; lỗi hiện rõ có log được lọc/tên riêng, không reset/xóa/ghi đè evidence. Guard không bị tắt để làm launcher xanh.

Source `start-web.ps1` hiện dùng hai tên log cố định, cả retry có thể ghi đè; sửa sang tên riêng cho từng lần khởi chạy/thử lại. Nhận diện đúng app/root/PID trước dừng server cũ; không dừng tiến trình không thuộc ứng dụng để giành port. Giữ CLI parameters và luồng mở những workspace hiện có; bước PG CRM chỉ áp dụng DEMO tương ứng, không chạy lúc mở kho thật.

Claude có thể kiểm code và unit/helper được cấp; Codex sẽ review bootstrap trước khi chạy trên host và cung cấp local configuration cần thiết. Báo riêng HTTP, restart đối tượng ứng dụng, restart tiến trình và GUI; chưa bấm GUI không tuyên bố đã đạt.

## 7. Kết quả probe M1/concurrency

Runtime M1 độc lập qua HTTP xác nhận control G01: một BANK→một SAO_KE→một proposal có hai dòng N1121/C344,300m và ObjectID A01; G03 nhận/kiểm/duyệt HĐ rồi nối tiền cọc cũ giữ nguyên fingerprint tiền, chỉ thêm một link. **G02 vi phạm:** sau HĐ đã có hiệu lực/được duyệt, hai khoản500m/900m vẫn C344, HTTP200; không phải131 theo quyết định TL32.

Sửa context của engine M1 hiện có để dùng fact HĐ/lịch/đối tượng/profile/PN có hiệu lực và provenance, không tạo engine tiền thứ hai hoặc rule344 chung cho mọi trường hợp. CFO quyết định tiền chưa rõ đã có căn cứ TL32: chưa có HĐ→344, có HĐ→131 đợt gần nhất; tiền lệch cần hỏi/chờ. Đây là đề xuất Vàng có bằng chứng, không tự duyệt/autoallocate toàn khoản vào một đợt nếu vượt nghĩa vụ. HĐ đến sau chỉ nối bằng chứng/link, không tăng hoặc đổi344 của bút toán tiền đã có. Không bịa policy đã duyệt, không dựng công nợ Junsky giả để ép chọn131.

Concurrency độc lập **9/9 nhóm đạt**, có hai connection thường và observer chứng minh follower chờ khóa winner cho cả hai race order và same-key retry. Link500 thắng→annex400 giữ chờ; annex400 thắng→link lịch cũ bị chặn. Retry/khác payload/quyền trước retry/tombstone HUY/keymới đều đạt. Tiền dùng M1 thật4BANK/4proposal/8dòng; không viết lại locking/idempotency đã kiểm đạt.

G04 nhận cùng raw lại giữ3BANK/3proposal/6dòng và giá trị nghiệp vụ; chỉ ID riêng của sáu dòng đề xuất chưa duyệt bị tạo lại. **Không gọi đây là thêm sáu dòng nghiệp vụ**; phải báo đúng giới hạn identity và giữ nguyên ID/reference của dòng đã được bảo vệ. Protected approval/locked-period G10 chưa kiểm, không fake trạng thái SQL hoặc gọi đã đạt.

**G12 failure atomicity còn lỗi thực ở converter/helper layer, chưa chạy negative này qua HTTP:** trên bản staging DEMO riêng sửa sai source core_hash, converter exit1, wrapper `ok=false`, có lỗi `core_hash_nguon` — detector và wrapper từ chối đúng. Tuy nhiên target3BANK vẫn3 nhưng field hash của một BANK đã bị cập nhật sai; sáu ID dòng proposal được tái sinh trước khi trả lỗi. Không thêm BANK/lô, không có bằng chứng wrapper báo success, nhưng từ chối xảy ra sau mutation.

Sửa có giới hạn đường projection M1→K2: kiểm checksum/source validity trước ghi hoặc rollback toàn giao dịch khi source validation fail. Không chấp nhận target đã thay nội dung rồi trả lỗi; retry sau fail không nhân hoặc làm mất lịch sử. Guard count dư hợp lệ của ba bảng dùng chung vẫn phải kiểm per-source record/provenance; mixed source-validation error phải từ chối và giữ target không đổi. Cho phép sửa converter hiện có ở phạm vi atomic preflight/transaction cần thiết, thêm positive shared-data và negative hash đúng causal oracle; không viết converter thứ hai hoặc mở rộng thành giải quyết toàn A5. Full A5/khóa kỳ/protected approval và snapshot thời điểm nguồn trước negative chưa đủ bằng chứng vẫn giữ gate, không tự báo đạt.

## 8. Bàn giao

Báo file/migration/API thay đổi, số ca pass/fail/error/skip với lý do, hướng chạy bằng nút và limitation còn thật. Cập nhật báo cáo CRM, CHANGELOG/hàng đợi theo phần thực hiện, không gọi toàn M3/M1/V13/toàn33 hoàn thành. Đợi Codex/agent độc lập kiểm source cuối trước nghiệm thu hoặc giao module kế tiếp.
