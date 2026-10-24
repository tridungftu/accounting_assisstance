# Giao Claude M4-01B2 — Khép sửa, viết kiểm PG thật và báo cáo

**20/10/2026 · CODE_ONLY · READY_FOR_SEQUENTIAL_HANDOFF.** Tiếp tục cùng session, không hỏi lại quyền triển khai M4/CRM đã được Anh giao. Đây là phần tiếp tục gói B, không phải thu hẹp M4 thành kiểm tĩnh. Giữ [kế hoạch M4](M4-KE-HOACH-DA-CHOT-20261020.md) và [B1–B6](GIAO-CODE-M4-01B-SUA-GATE-VA-BO-SUNG-KIEM.md).

## 1. Mốc thực tế

Lượt B trước dừng ở giới hạn 1.800 giây, không result và chưa có report. Root đã xác nhận terminal, stop và kiểm scope; snapshot288 SHA256 `eda724f82caf17479ea931a33856df2afe13e26e88b4269bc0b37be1eeab5579`. Có code và `test_m4_01b_tinh.py`, chưa có kiểm PG thực hoặc runtime nào được chạy. M17 chưa triển khai lên DEMO; prefix1–16 vẫn nguyên 715.854 bytes, SHA256 `208a03354a989e2d1b469271ed3e324638e1dc0d1e0ae1db376c195d0d57de0a`.

Root và ba agent đã đọc source tĩnh. Các phát hiện sau được rebind đúng hash cuối; không phải test runtime thất bại. Không đọc var/ hoặc source app thật; dùng source hiện hành và reference65 đã lọc. Các cải thiện trusted fact/FINAL/revoke đã có phải giữ, không viết lại cả M17 hoặc framework.

## 2. Sáu sửa hữu hạn bắt buộc

1. **Giữ staging của primitive dùng chung.** `ha_tang/store.py:23–41` có finally unlink. Call path thật: upload `xay_dung.py:333`; quote/BOQ qua adapter `ban_lam_viec`; extract qua adapter312. Mở đúng helper `write_immutable` để giữ toàn bộ tệp staging khi thành công/lỗi/retry, đồng thời giữ atomic promotion, content-addressed bytes, chống ghi đè và kiểm đường dẫn. Không dựng store thứ hai, không monkeypatch hoặc sửa guard để che unlink; không thêm cleanup nơi khác. Tác động chỉ retention của primitive, giữ hợp đồng nghiệp vụ/caller khác.
2. **Cache module phải đúng nguồn/pin trước khi dùng.** `nap_ghim.py:80–83` và `nguon_review.py:133–135` đang tin marker chỉ cần khác None. Cache marker giả/stale/sai origin phải bị từ chối theo exact approved origin/pin/loader binding trước khi dùng module; giữ pre-exec check cache-miss đang có. Không đòi sandbox chống mọi Python code độc hại, không bỏ cache hoặc sửa vendor để lách.
3. **Không để tên hạng mục điều khiển loại lỗi BOQ.** Adapter395–404 match `KL × ĐG` trên cả thông báo trước lỗi số. Source parser đưa tên hạng mục vào thông báo; tên chứa chuỗi này và KL=`abc` tạo row KL=null nhưng bị hạ thành finding, service→ghi_boq→DA_MAP. Phân loại theo dữ liệu lỗi có cấu trúc/đoạn nguồn cố định hoặc thứ tự lỗi số/map thật, không keyword tự do trong tên. Giữ supplied amount, raw/locator/missing và findings; parse/map invalid phải chặn, lỗi số học thuần vẫn cho review khi căn cứ đủ.
4. **Track Changes theo namespace XML.** Guard hiện dùng dem_sua_doi legacy chỉ đếm literal có dấu cách. DOCX hợp lệ có newline sau QName hoặc prefix khác cùng namespace vẫn lọt. Chặn thay đổi nội dung chưa chốt bằng XML namespace/tag trước mọi reader entrypoint; không Word/LibreOffice/accept-change/cleanup. Kiểm XML/định dạng lỗi phải trung thực. Không sửa byte vendor.
5. **Helper đọc trạng thái tệp theo current scope.** `sql_m17.py:536–539` m4.tep_da_nop là SECDEF được app_web gọi trực tiếp nhưng không kiểm identity/project/module/file. Đóng việc đọc submitted-bit của UUID ngoài quyền hoặc sau revoke, đồng thời giữ đúng policy tep_web và viewer hợp lệ. Không thêm owner-only policy hoặc cấm mọi draft HĐ cho reviewer.
6. **BOQ FINAL shape bất biến.** `boq_nhap` fresh thêm loi_chan/phat_hien arrays sau command; receipt SQL chỉ lưu counts/status/revision, replay trả thiếu arrays. First/retry exact key/body phải trả cùng kết quả/chi tiết bất biến (trừ replay indicator được khai rõ), không reparse, không lấy findings của BOQ hiện tại khác version. Giữ quyền trước lookup và exact original request sau own/later revision.

## 3. Viết kiểm có ý nghĩa, không chỉ tìm chuỗi SQL

- Giữ/sửa ca thuần hiện có và thêm counterexamples cụ thể: cached marker khác None nhưng sai pin/origin; DOCX namespace alias/newline; BOQ tên chứa KL × ĐG + KL abc cùng dòng hợp lệ; retained upload/work-artifact thành công/lỗi/retry; helper file ngoài quyền; BOQ fresh/replay đầy đủ arrays.
- Viết mới **tests/test_m4_01b_pg.py**: native PostgreSQL trên fresh retained DEMO bằng DSN Root cấp qua env lúc chạy, actor MO_PHONG_, ordinary app và trusted writer riêng. Không đọc .env/var hoặc hardcode credentials. Không DROP/DELETE/TRUNCATE/cleanup kể cả rollback.
- PG positive: migrate neutral1–16→M17, seed đủ, valid raw bytes→trusted source/extraction/BOQ facts→ordinary DU_AN dùng/xác nhận; actual nonempty submission khi đủ căn cứ. Chưa có Local AI thì tách native DOCX/XLSX parse với fake-AI plumbing khai báo rõ; không nhận accuracy đã chứng minh.
- PG negatives: authorized ordinary app trực tiếp giả file/XONG/DA_MAP/machine-check/FINAL không được; actor thật có quyền để ca âm không xanh chỉ vì ngoài scope. Helper trạng thái tệp/receipt/file sau revoke đúng project bị chặn trong khi actor vẫn active/module M4 còn quyền.
- PG replay: mỗi TRICH/SUA_THAM_SO/KHAI_PL/THEM_PL/HUY_PL/BOQ first→exact original key/body/revision retry→later legitimate revision→retry cũ; IDs/result giữ, không fresh parse/AI/rows. Same-key changed body và hai connection đồng thời không nhân business outcome; timeout/deadlock không là PASS.
- BOQ numeric-invalid khác arithmetic-finding: physical XLSX, giữ raw null/0/999/locator; đủ map nhưng finding số học không tự chặn Nộp; thiếu từng căn cứ vẫn chặn backend.
- Prefix test phải kiểm first17/identity của prefix, cho phép append migration tương lai; không hardcode latest schema luôn bằng17 rồi phải sửa test khi CRM thêm migration.
- Expected từ fixture/source/manual case; không parser tự sinh đáp án hoặc all-denied thay valid positive. Test skip/setup/unconfigured ghi NOT_VERIFIED/NOT_RUN, không nhận đạt. Không sửa các test/guard lịch sử để làm xanh.

## 4. Phạm vi ghi, phân công và kết thúc

Root phát exact settings. Existing targets: tám file gói B, cộng `ha_tang/store.py`, `m4/sql_m17.py`, `m4/nap_ghim.py`, `tests/test_m4_01b_tinh.py`; helper/test mới chỉ trong phạm vi được cấp. Không sửa baseline migrations1–16, CRM/M1/M9/L11 business logic, secrets, guards hoặc nguồn app gốc. Không mở GUI gói C trong lượt này.

Nếu Root cấu hình được built-in test subagent an toàn trong cùng Claude Code: main giữ source và test_tinh; một test agent chỉ viết mới test_m4_01b_pg.py, không sửa source hoặc spawn thêm agent. Hai bên không cùng sửa một file; main đợi test agent hoàn tất và nêu kết quả trong report. Nếu không có cơ chế này, cùng main thực hiện tuần tự; không tự bỏ SafeMode hoặc mở session/worktree/CLI khác để tạo song song.

CODE_ONLY: chỉ file tools được Root cấp; không chạy lệnh/import/AST/tests/SQL/HTTP/AI/OCR/browser/launcher/cloud hoặc tool nạp nguồn. Hoàn thành **docs/BAO-CAO-M4-01B.md** với file/API/UDF/dependency/trusted factory/retention/replay contracts, test cases và lệnh Root cần chạy; self-tests NOT_RUN. Thiếu phần nào báo đúng, không chuyển gói hoặc nhận B/M4 đã nghiệm thu.

Sau terminal/freeze, Root review và chạy kiểm độc lập. M4-01C vẫn phải khép GUI/Cổng/bootstrap/launcher; full Review L1–L3/PDF/NT–công nợ/Request và nghiệm thu xuyên suốt vẫn giữ đủ. CRM G1/G7/S6 có gói riêng trên shared baseline ổn định; CAD để sau như đã chốt.
