# CRM-41-01 FIX03 — Seal kết quả và recovery toàn vẹn

Trạng thái: PREPARED_CODE_ONLY / ROOT_RELEASE_REQUIRED; đây là một lượt sửa hữu hạn, chưa phải lệnh chạy hay áp dụng source gốc.
Căn cứ: [engine dùng chung](GIAO-CODE-CRM-41-01-ENGINE-DUNG-CHUNG.md), [binding](GIAO-CODE-CRM-41-01-BINDING.md), [FIX02](GIAO-SUA-CRM-41-01-02-REPLAY-VA-TOAN-VEN.md) và quyết định một engine #6. Predecessor FIX02 đã dừng thành công; source gốc vẫn chưa áp dụng patch.
Root đã chạy kiểm thuần central: 18/18 PASS, 0 skip. Các lỗi dưới đây là phát hiện static trên patch FIX02; kết quả đó không chứng minh source HTTP, GUI hay toàn module đã đạt.

## 1. Phạm vi đúng 5 file hiện có, NEW0
- `docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py`
- `docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py`
- `src/kho_tri_thuc/nguon/trich_chung_6.py`
- `tests/test_trich_chung_6.py`
- `docs/BAO-CAO-CRM-41-01.md`
Giữ byte nguyên CRM service/UI, M4 adapter, staged `server.py`/`viec.py`, ba file thuật toán, catalog, vendor, M9 và migration 1–20. Không sửa source app gốc, thêm core, DDL hay framework.
Giữ các sửa đã có: upload cùng bytes replay sau reserve; giữ chỗ bền trước mkdir; cùng logical ID đổi actor là conflict sau kiểm quyền hiện hành; RULE_ONLY, không AI/cloud, không cập nhật master, không cache ngầm, không DELETE/cleanup.

## 2. R1 — Mọi đường công bố common phải qua seal hợp lệ
Không dùng riêng `lc.s.tt == xong` hoặc `_luot.json` để công bố hoàn tất: worker có thể đã ghi xong nhưng callback chưa seal hoặc seal thất bại. Trong lúc đó chỉ trả pending/UNKNOWN có lý do, không trả native result hay đường tải kết quả như đã hoàn tất.
Áp dụng cùng gate hẹp cho `chi_tiet_luot`/`_bo_sung_tai`, `ds_luot`, callback chi tiết của QLV/viec, `_json_hd` và `file_tai` cho tài nguyên kết quả common; không đổi nhánh legacy. Không cần sửa `server.py`/`viec.py`.
Nhận diện common trước khi dùng `_luot.json`/`_tuy_chon.json` lưu trên đĩa; kiểm kiểu các trường DTO/collection được dùng. JSON hỏng, trường thiếu/sai kiểu hoặc dữ kiện chưa kiểm được phải cho trạng thái common UNKNOWN có lý do, không lỗi 500 hay lộ kết quả chưa kiểm.
Central chỉ nhận kết quả khi trạng thái common hoàn tất có seal hợp lệ, đúng ý định và đúng ref tương đối/SHA/độ dài bytes tải thật. Top-level xong, thiếu common hoặc thiếu seal không đủ; không biến chúng thành kết quả tốt hay FINAL LOI chắc chắn.
Seal là sidecar/trạng thái ngoài raw JSON: giữ nguyên raw bytes đã băm, không chèn hash của chính raw vào raw để tạo vòng tự băm. Seal thất bại/gián đoạn/restart không được mở đường tải kết quả hoặc tự chạy lại.

## 3. R2 — Ràng buộc toàn bộ ý định, snapshot và metadata
Tái dựng canonical body theo cùng quy tắc nhận request và băm lại đủ trường contract/mode/type/catalog/source/requested set; so với ý định đã giữ, không chỉ so hai chuỗi `body_sha256` lấy từ các file có thể cùng sai.
Trước compute, chụp sâu metadata tin cậy từ chính bytes HĐ/catalog, params đã chọn và implementation map; giữ bản bất biến cho callback. Ghim canonical request/metadata hash và các ref bằng dữ kiện này, không đọc lại request/output đã thay đổi rồi coi đó là expected.
Trước seal terminal, kiểm request lưu và `native.common` khớp bản chụp tin cậy: type/catalog/version, source, requested/expanded set, params snapshot, implementation và rules provenance. Chỉ sau đó seal ref tương đối đầy đủ, raw SHA và độ dài thực tế.
Recovery kiểm lại bytes HĐ/catalog; chọn params từ đúng catalog snapshot để chứng minh ALL mở rộng đúng tập và thứ tự catalog, subset không lạ/trùng và snapshot giá trị đúng. Kiểm request/native metadata/seal cùng identity và hash; raw đúng bytes riêng lẻ chưa đủ.
Implementation SHA phải kiểm từ captured file-map theo cùng canonical rule, khớp request/native/seal; chuỗi đúng 64 ký tự chưa đủ. Không bắt lượt lịch sử phải bằng implementation đang triển khai mới; kiểm đúng identity đã chụp của lượt đó.
Registry/giữ chỗ/link phải là record typed và có ràng buộc nội dung canonical kiểm được, gồm logical ID, luot, source H, full body H và các ref liên quan; không để đổi luot/source/ref bằng valid JSON mà vẫn được phục hồi/định tuyến như hợp lệ.
Phân biệt file thật sự chưa tồn tại ở khe ghi với file có nhưng thiếu/sai nội dung. Mọi khe reserve → mkdir → link/request/catalog → seal phải giữ đúng ý định đã chọn, hoặc UNKNOWN/orphan có lý do và không tái compute/ghi đè kết quả.

## 4. R3 — UNKNOWN đi trước kết luận conflict
Ở nhánh replay/start/recovery, record hỏng/thiếu identity không đáng tin phải được phân loại UNKNOWN trước khi so request ID/body để kết luận `COMMON_XUNG_DOT`; không biến identity rỗng do parse lỗi thành conflict chắc chắn.
Giữ current-rights check phía central trước lookup/replay và không lộ body actor khác. Source common replay không tái compute hoặc ghi đè published/history; DB/catalog/sequence và old files/published/history giữ nguyên. Retained staging diagnostics của storage hiện có phải kê riêng đúng parent/hash/bytes/số lượng, không blanket-ignore và không gọi đó là zero toàn bộ file. Changed body hợp lệ vẫn conflict; dữ kiện không kiểm được không rerun, không overwrite, không FINAL LOI chỉ vì 409 chung.
Không mở rộng việc harden mọi file legacy: sửa đúng nhánh common mới và các đường đọc/tải reachable của nó, giữ API legacy tương thích.

## 5. Kiểm hữu hạn phải bắt được lỗi thực, không làm yếu oracle
Có positive nonempty RULE_ONLY trước negative. Dùng barrier thật giữ callback trước seal sau khi raw/native đã xong: trước release chưa đường common nào công bố hoàn tất/result; release thành công mới đọc được đúng bytes. Kiểm seal lỗi và restart ở cửa sổ này vẫn UNKNOWN, không chạy lại.
Kiểm các đường status/list/viec/detail/raw-download nói trên, gồm JSON hợp lệ nhưng DTO sai kiểu ở `_luot.json`/`_tuy_chon.json`; không chỉ test một helper độc lập hay chấp nhận generic exception làm PASS.
Thêm valid-JSON targeted mutations riêng cho canonical request/type/catalog/source, ALL→subset/params snapshot, implementation map/SHA, native.common và registry luot/source/ref; giữ hash/độ dài hoặc các trường đối chiếu cũ khi cần để chứng minh guard mới bắt đúng lý do, không chỉ UTF-8 hỏng.
Giữ kiểm reserve/mkdir/link và bổ sung thiếu catalog/registry field ở các khe ghi; kiểm tồn lưu đủ trước/sau theo relative path đầy đủ + SHA + bytes, không basename/size đơn lẻ và không DELETE dù trong rollback.
Kiểm đồng thời thu đủ mọi caller: central bài ba caller phải đúng 3 kết quả; source bài bốn caller phải đúng 4. Join hữu hạn, không thread còn sống, thu mọi exception và không bỏ qua caller thất bại; các count/assertion cũ vẫn giữ.
Giữ nguyên thuật toán tài chính, expected literals, original no-delete guard và các oracle đã đạt. Test chỉ chạy khi Root cho phép; không copy, patch hay bypass guard, không lấy output bị sửa làm expected.

## 6. Bàn giao
Báo cáo đúng phần sửa và selftest NOT_RUN nếu chỉ đọc/viết code; không gắn 18/18 central thành source HTTP PASS. Nêu rõ source gốc còn unapplied và các đường recovery/publication đã phủ, giữ mọi attempt/fixture/bản cũ.
Cùng phiên Claude đã bind, CODE_ONLY 1200 giây, chỉ Read/Glob/Grep/Edit/Write, safe-mode/dontAsk và MCP rỗng; không shell/import/test/runtime/network/SQL hay tự áp dụng patch. Root bind pins, review và release riêng trước runtime.
