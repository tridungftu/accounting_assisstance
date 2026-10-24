# Giao Claude — M9 typed và common K2/K5 trong phần mềm kế toán

19/10/2026. Root cho triển khai theo kiến trúc và phạm vi Anh đã chốt; không hỏi thống nhất lại. Claude là coder chính; Codex review độc lập sau authoritative terminal/freeze. Mục tiêu bàn giao lượt này là **chuỗi M9 DEMO dùng được trong cùng shell**, không chỉ adapter/schema hoặc bảng JSON hiển thị. Toàn M0–M10/9receiver/L1–L12 vẫn là đích tiếp tục sau từng lượt kiểm.

## 1. Căn cứ phải đọc

- `ROOT-CHOT-BINDING-MODULE-33-20261019.md` — root đã duyệt contract và dependency.
- `GIAO-VIEC-BRIDGE-KHOAN-VAY-M9-33.md` SHA `fb8c5f00834520625217f999b2b45a12246fa958787dca4d2261b04bcaa5f946`.
- `THIET-KE-M9-TYPED-DEMO-33.md` revision2 SHA `e3e9704f5af808bc3c398a84ba85e3a80e0bc4b51c4042c1bda90fb73cfa9bf3`.
- **`BINDING-M9-CORE-SAU-CRM03.md` SHA `28af9c1045c8da5448056baa45b679fd476f48aaa40d897ff92430764b168bc5`, gồm toàn §9 R1–R4 bắt buộc.** Root review `REVIEW-THIET-KE-M9-33.md` và independent `REVIEW-BINDING-M9-CORE-01.md`.
- `REVIEW-CONTRACT-M9-INPUTS-01.md` — các ca nguồn/precision/transport đã khảo sát; corpus private do Codex giữ để kiểm độc lập, không yêu cầu đọc var.

Core hiện là bàn giao06 CLI51883 terminal0,125files manifest `c828d1fff9593a0dce6d47e079df8adf76a4609cb936e2f1a627cf1a9948dd08`. Core nghiệp vụ/schema1–12 vẫn như03;04–06 chỉ hoàn thiện runtime/nút/JSON. Giữ những sửa này, không rollback theo frozen03. Root đã giữ source/hash/backup; không đọc backup/var để lấy đầu vào.

## 2. Triển khai theo phụ thuộc trong cùng lượt

1. **Common M0/K1:** source instance/profile/immutable intake metadata/snapshot/row/mapping/derivative theo binding; raw nhiều PN/chưa map không ép vào tep_goc PN giả hoặc nới globalhash. One file store/registry. Integration role khác PN actor; alias ổn định trước target PN, approved interval/source mapping locks và impact retarget. Currency-scale/precision/date/known time giữ rõ; không fake ngày/scale0/VND/amount0.
2. **Typed M9:** tái dùng HĐ/PB và mở rộng lịch trả nợ hiện có, typed loan/draw/rate/event/LC/ngắn-dài hạn theo contract. Source kind LC→SHORT cùng source identity không hai HĐ. LOAN/DRAW scope, NULL≠0, nguyên tệ/VND riêng, precision UNPROVEN/LOST giữ holding; không tính engine lãi mới. Nguồn đọc qua adapter v1/file DEMO đúng contract; Google readonly deployment/credentials còn gate. Không gọi load/ensureSheet/exportToExcel/AppsScript mutation để giả đọc.
3. **Shared K5/domain/quyền:** action/owner discriminator/typed subject resolver/DB eligibility+wholegraph digest/OLD+NEW parent protections+prelocks, RLS ordinary role. Validator VAY không gọi parser doanh thu CRM. Giữ CRM positive controls và ACL scoped đã sửa, không cấp M1/CRM rộng để chạy M9. Thiếu field/proof/mapping vẫn nhận giữ raw/candidate/task; dated+proven positive phải promote/kiểm/duyệt được.
4. **Common money L8:** một parent DIRECT/CHILD+child/receipt+logical target+remaining đúng R1–R4; CRM DIRECT và M9 CHILD cùng full BANK budget. BANK encoding proof có căn cứ và immutable, không lấy registry hiện tại làm proof; unknown blocked. Cả BANK lẫn logical target consumption xuyên revision/basis/alias, held/tombstone/rights-before-replay/locks và two-domain race. BANK tiền đi/tiền về từ M1 hiện có, không tạo SAO_KE hoặc bút toán112 mới từ draw/PhatSinh. Common helper là chỗ duy nhất cho consumer M2/M7 tiếp theo.
5. **API/UI/file:** trong shell/session/actor MO_PHONG hiện có, menu M9/hồ sơ/source/map/holding/kiểm/duyệt/lịch/preview-xácnhận-gỡ link/file-soát. Reuse audit/work/lô/export writer/guard; amounts JSON/UI/XLSX lossless text/formula-safe. Hồ sơ chưa đủ vẫn thao tác bổ sung được; không nút placeholder hoặc chỉ raw snapshot. Source/versions/profile/proof/approval/link/remaining/history truy được. Launcher mặc định dùng runtime hiện có; không đòi Anh gõ lệnh hoặc nhập DSN.

L7/lãi dự trả/M10 chỉ nhận bảng kỳ/amount/căn cứ đã được cung cấp và kiểm đúng policy/template đã khai báo. Không lấy exportLai currentbalance/lastrate làm accrual oracle hoặc tự chốt daycount/cutoff/FX/vốn hóa/TK. Neutral DEMO được dựng theo explicit fixture contract; phải ghi rõ giả định DEMO, thiếu actual policy giữ task. Recognition consumption phải dùng primitive chung tương thích M2 final, không private table/key chỉ có PB làm reset kỳ/event. Nếu phần common cần đổi tên cho trung tính, ghi map tới các contract M2/M6/M10 để một registry được dùng tiếp.

Full M9 gồm C4a–d,LC/bảo lãnh,L7/L8/L12 và đầu tư. **C4d chưa đủ current register/loại/hồ sơ nên chưa được tự tạo securities/valuation schema hoặc bảng rỗng rồi gọi xong.** Phải có work gate/checklist cụ thể theo nguồn/căn cứ thiếu và tiếp tục tìm đúng nguồn ở bước điều phối; không loại nhánh khỏi chương trình. Không biến gap policy thành dữ liệu tưởng tượng. Phần đủ thiết kế của M9 phải đi hết chuỗi DEMO ở lượt này; báo rành mạch phần đã code/đã test/holding/unrun.

## 3. Migration và kiểm chứng của coder

- Migration mới sau12, không sửa bất kỳ statement/checksum M0001–M0012, reset/recreate database hoặc đổi nghĩa legacy lịch/link. Fresh+upgrade fixture từ12/CRM DIRECT/HUY, giữ IDs/lô/audit/approved content. M9_TYPED compatibility chọn rõ; không blanket null/zero backfill. Bảo vệ approved child và cả OLD+NEW parent, không reparent sang draft.
- Self-tests targeted nhưng đầy đủ domain dương/âm: source replay/multi-PN ambiguity/precision/date/LOAN-DRAW/mapping; action/FK/RLS/V4/wholegraph stale; money parent-child/fullbudget/logic target xuyên revision/encoding; source đến trước-tiền đến sau và ngược lại; export bytes/cells; regression CRM đang dùng commoncore. Negative phải có positive control, lỗi setup/skip không là đạt.
- PostgreSQL chỉ dùng retained runner đã cho phép: `python -X utf8 var/codex-dieu-phoi/run-pg-tests-retained.py test_*`. Không đọc .env/privateconfig/credential hoặc làm SQL từ shell; root private runner giữ DSN tại máy và chỉ báo tổng hợp. Không viết teardown DROP/DELETE hoặc cleanup xóa file/role; fixture IDs riêng và giữ DB. Guard+PYTHONDONTWRITEBYTECODE luôn bật. Không chạy launcher/server/Google/GUI/cluster host; Codex kiểm host sau terminal.
- Ghi `docs/BAO-CAO-M9-TYPED-DEMO-33.md`: migrations/actual API/UI/interface/runtime, requirements→implementation→tests→evidence→status; pass/fail/setup/error/skip/unrun riêng. Không tự nghiệm thu hoặc sửa expected của independent corpus.

## 4. Phạm vi dữ liệu và thao tác

Anh cho phép gửi Claude **src/tests/tools/script mở/pyproject/test.ps1/tài liệu kỹ thuật đã lọc**. Không truy cập/transmit var/.env/backups/realrows/tên đối tác/STK/secrets hoặc source app vay/review/kho/HR ngoài phạm vi đó; source reuse dựa contract sanitized đã pin. Không mở lại source ngoài hoặc gửi code nguồn đó vào prompt dưới dạng tài liệu. Không thay source app trong lượt core này.

**Không xóa bất kỳ file/temp/DB/role, không reset/clean/commit.** Giữ immutable artifacts và no-delete guard; không tắt để suite xanh. Không tự chuyển kho thật SQLite, duyệt thật/CFO_NTD, cloud AI/Junsky mức2, Google writes hoặc cài global software. Codex giữ CHANGELOG/hàng đợi/coverage. Nếu thiếu quyền tools cụ thể thì báo đúng tác vụ bị chặn và tiếp tục phần độc lập, không tự bỏ phần đã giao hoặc yêu cầu Anh mô tả lại workflow.
