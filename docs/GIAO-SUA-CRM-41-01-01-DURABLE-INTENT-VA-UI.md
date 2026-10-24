# CRM-41-01 FIX01 — Đường dẫn Windows, durable intent/replay và CRM async

**CODE_ONLY, phạm vi Anh đã giao; cùng session52783bcd-6e1d-46d2-9e45-3c527aa43e5b.** Kế thừa toàn bộ common engine/API/client/M4/CRM đã viết, giữ kiến trúc một #6 và một adapter. Không thu hẹp mục tiêu. Bản trước actual55438/terminal667036 đã dừng đúng phạm vi18targets; source patch CHƯA áp vào nguồn thật.

## 1. Bằng chứng và phạm vi kiểm
- Root freeze source370/runtime438; AST mọi Python đã sửa đạt, Node --check hai JS đạt. Chưa có product/API/PG/GUI runtime PASS. Native client/API test không gọi hai business routes/PG, không thay kiểm actual hai consumer.
- Root đã đọc FULL client/report; ba reviewer đã đọc source/UI/service/test diffs. Các lỗi dưới đây là kết luận static, riêng đường dẫn Windows đã kiểm metadata-only: logical ID m4:0123456789abcdef làm tên thư mục gây WinError267/errno20. Không chạy product/SQL để chứng minh ca này.
- Toàn bộ source originals vẫn giữ nguyên (36 technical files/catalog). Chỉ sửa staged patch được liệt kê; Root sẽ backup/hash/review rồi áp vào nguồn #6 thật. Không runtime import docs/reference/copied core.

## 2. Sửa gộp hữu hạn
### F1 — Logical request_id không được làm tên thư mục
- Client hiện ghép thẳng request_id vào goc/trich6-y-dinh, trong khi actual M4 sinh m4:<hex>; Windows không tạo được thư mục đó. Dùng hash/encoding an toàn của logical ID khi làm đường dẫn, giữ ID logic trong body/receipt; mọi path resolve vẫn trong root, xử lý được colon và token . / .. mà không đi ra root. Không bẻ actual caller ID hay đổi identity giữa retry.
- Thêm test client có goc thật trên Windows với ID m4:... và IDs có ký tự đặc biệt cho phép; không chỉ transport không lưu intent.

### F2 — Durable create/UNKNOWN và một lần tạo mỗi intent
- Source route create hiện body{} không bind request ID; client210–224 mất ACK create thì retry tạo lượt mới. Hai caller cùng intent cũng có thể cùng create trước immutable10 conflict.
- Cho phép route POST /api/trich_xuat nhận OPTIONAL common/v1 create body chứa stable request_id và canonical full common request; body{} legacy giữ nguyên. Đây là lý do bổ sung staged may_chu/server.py vào đúng allowlist lần này. Tận dụng cùng luot_moi/registry/storage, không pipeline/DB/queue mới.
- Common create persist/reserve theo request_id + canonical full body (sourceH/catalogH/type/requested set) trước ACK; exact retry trả đúng lượt, changed body409. Tên registry/lock/path hash-safe. Việc chưa rõ kết quả phải đối soát cùng intent, không tự create/run lần hai. Concurrent cùng intent đúng một lượt; hai intent khác tạo đồng thời không lỗi check→mkdir timestamp.
- Giữ raw bytes và original body/key/reference trước tác động. Mất ACK create/upload/start hay GET/poll/raw-download sau accepted start đều giữ trạng thái chưa rõ, stable luot/intent. Khi chưa rõ, M4 không ghi FINAL LOI/revision/receipt; retry original key đọc tiếp source run. NR hiện propagate ChuaRo nhưng generic GET transport DataError bị đổi LOI: sửa phân loại từ client theo lifecycle, không sửa SQL hay giảm kiểm.
- Thêm test lost-create-response sau server thực sự đã tạo, concurrent same/different intents, upload/start lost ACK, GET/poll/raw connection loss sau accepted start. Ghi rõ IO-mock vs actual loopback; không chỉ kiểm substring source.

### F3 — Restart replay và reservation chung với legacy
- COMMON hiện chỉ memory. Restart rồi exactsame luot/body gặp _common.mkdir(False)→500 dù request/result còn nguyên. Rehydrate durable request/state/receipt/result với đúng hashes. Completed→exact replay, không sửa raw/history; capturing/running không còn owned worker sống→UNKNOWN/orphaned, không tự rerun/reset/ghi đè.
- Legacy start537–571 check ngoài _KHOA_LUOT rồi mới reserve; common có thể reserve ở giữa và bị legacy ghi đè LUOT/_tuy_chon + nhận cfg/AI. Cả common/legacy create/start/upload dùng cùng reservation boundary ngắn; cfg/compute/network ở ngoài khóa. Giữ hành vi legacy hợp lệ, common không thừa hưởng AI/config.
- Test held/interleaved common-versus-legacy start ở cả thứ tự, exact replay sau rehydrate/khởi động lại, orphan UNKNOWN và two creates. Không gọi AI thật hoặc main() nguồn.

### F4 — CRM bind full original intent ở server
- Browser request_id hiện chỉ bind raw/type/catalog/codes, thiếu authoritative actor + PN/loai_hinh/du_an/loai_ban và envelope đã chọn. Cùng ID đổi envelope có thể rơi vào TRUNG_RAW của envelope cũ.
- Sau auth và trước mọi source/storage side effect, giữ canonical original full allowed payload + actor vào intent record dùng storage hiện có; cùng logical ID/body khác thì conflict trước source call. Phân biệt extraction type và financial profile. Current rights/PN/project/revision recheck trước publish giữ nguyên. Không DDL/master/approval mới.
- Regression sameID/sameraw nhưng đổi PN/project/profile/loai_ban/actor; không ghi business/source mới. Exact retry giữ bản cũ đúng owner.

### F5 — CRM File/context/refresh không làm mất draft
- app.js448–458 đang dùng name/size/lastModified làm identity và tái dùng File A khi File B khác bytes nhưng cùng metadata. Giữ đúng File/bytes/hash original; lựa chọn mới phải được phân biệt an toàn.
- Sau await arrayBuffer()458 và trước POST459 phải kiểm current role/form/context; context đổi trong lúc đọc thì không phát mutation dưới session mới. Rào ở mọi await cần thiết, không chỉ lúc vẽ response.
- Success462 gọi crmLoad; GET592 chỉ epoch+GETgen nên render506–507 có thể xóa form B mới nhập khi refresh chờ. Rào refresh bằng generation/intent của draft, hoặc giữ DOM/draft mới; background response không xóa/ghi đè draft khác. Quyền đổi vai và refresh có chủ đích vẫn hoạt động.
- Regression ba lịch trên phải dựa hành vi (File B cùng metadata; role/form đổi khi arrayBuffer đang giữ; nhập draftB khi post-success GET đang giữ). Giữ original intent khi UNKNOWN; không tạo request mới chỉ vì timeout.

### F6 — Native test data root
- Source test_common_api.py30 đặt HD_DU_LIEU=TMP/du_lieu nhưng HD_OUT_DIR=TMP/ket_qua ngoài root; duong_dan_tai relative_to(DATA) trả rỗng nên positive không tải raw. Đặt OUT dưới DATA, giữ toàn bộ tmp/DB/file, không cleanup/delete.
- Giữ source TC-rule positives/37/strict snapshots/offline/no-cache, legacy behavior và mọi financial/rights/current-revision oracle. Source danh_muc/lo/quy_trinh và migrations1–20/vendor/M9 giữ nguyên byte trong lượt sửa này.

## 3. Giới hạn và bàn giao
- Chỉ9 existing targets cuối file, NEW0. Source patch thêm server.py là sửa chính route create có sẵn; Root mới áp vào actual source sau kiểm. Không vào source app thật, var/.env/credentials/realdata; không AI/cloud/Office/OCR/PDF/AP/Request/M2/E1 mới hoặc lifecycle framework.
- Chỉ5filetools; không Bash/commands/import/AST/run/tests/SQL/HTTP/browser/delete/cleanup. Code/test/report NOT_RUN_CODE_ONLY. Tests API thật chỉ là source/client nếu chưa gọi actual XayDungK2/CrmK2/HTTP/PG; ghi đúng giới hạn.
- Report thêm FIX01 và nêu sửa theo F1–F6, test đã viết/chưa chạy; không gọi full package/module hoàn tất. Timebox1200s; nếu thiếu phần nào ghi partial thật, không bỏ requirement để báo xanh.

## Exact existing edit targets (9)
- docs/CRM-41-01-SOURCE-PATCH/may_chu/server.py
- docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py
- docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py
- src/kho_tri_thuc/nguon/trich_chung_6.py
- src/kho_tri_thuc/k2/crm.py
- src/kho_tri_thuc/m4/nguon_review.py
- src/kho_tri_thuc/giao_dien/assets/app.js
- tests/test_trich_chung_6.py
- docs/BAO-CAO-CRM-41-01.md
