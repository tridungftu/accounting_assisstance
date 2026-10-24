# CRM-41-02 — sửa các điểm còn lại sau review độc lập bản cuối

**21/10/2026 · CODE_ONLY · cùng session Claude hiện có.** Bổ sung handoff gốc và `GIAO-SUA-CRM-41-02-TIEP-01.md`; giữ đầy đủ CRM41–42 và M4 đã chốt. Không mở thêm quyết định nghiệp vụ hoặc đổi kiến trúc.

## 1. Bản gốc và phạm vi hữu hạn

- Lượt41064/4369a1 đã terminal thành công `b652bc`, exit0, không timeout; stop/scope/posthash được Root xác nhận. Bản lưu360 source/428 runtime có đủ code/test/báo cáo. Thành công này chỉ là kết thúc lượt viết code, chưa phải nghiệm thu.
- Source manifest SHA `294fa6b76a67c3c14aad4a530418661e428a0df8d476a571aad9ef756aa7ee43`; runtime manifest SHA `8b6bf4a02017b4abb0a157570b20b93307b625684e7bae51625bbef9bbc6671e`. Không đọc private Root corpus/oracle/runner/biên bản kỹ thuật trong `var/`.
- Chỉ sửa **5 file đã có**, không tạo file sản phẩm/test/helper mới: `src/kho_tri_thuc/nguon/mau_docx.py`, `src/kho_tri_thuc/giao_dien/assets/crm_g.js`, `tests/test_crm_41_02.py`, `tests/test_crm_41_02_http.py`, `docs/BAO-CAO-CRM-41-02.md`.
- Các file khác giữ nguyên, gồm `pg_migrations.py`, `crm_mau.py`, `quyen.py`, `server.py`, `app.js`, seed/bootstrap và native M4 setup SHA `f77bdfe66772a2494d36f40cb1f2119d27af351ae8f101b1a3dc42bd9274a9d2`. Không thay migration1–18 hoặc block M9; không làm lại S01 đã khép static.

## 2. P02 còn lại — phân loại kênh bằng quan hệ/cấu trúc, không bằng tên file

Root và agent đã đọc source371: `mau_docx.py:340–345` thêm XML đích được document tham chiếu, nhưng `:348–351` bỏ qua `styles.xml/settings.xml/...`, `/theme/` hoặc `headerN.xml/footerN.xml` trước parse chỉ dựa vào tên.

Ví dụ hữu hạn: thân tài liệu có `w:footnoteReference id=1`; quan hệ loại `/footnotes` trỏ tới part có tên `styles.xml`; ContentType/root là footnotes, note1 có token `{{ho_ten}}` tách bốn run. Đây vẫn là kênh được tham chiếu, nhưng basename hiện làm nó bị bỏ qua. Tương tự khi part mang tên header1.xml mà quan hệ thực là footnotes. Đây là counterexample source; không giả là đã có runtime proof.

- Không cho basename/đường dẫn ghi đè loại quan hệ và nội dung thực. Kênh hiển thị chưa hỗ trợ có ngoặc phải INCOMPLETE với lý do cụ thể hoặc bị từ chối semantic rõ; không trả DU do skip theo tên. Metadata mâu thuẫn không được suy COMPLETE.
- Chỉ bỏ qua phần định dạng hoặc header/footer không hiển thị khi có căn cứ phù hợp; giữ header/footer thực sự được `sectPr` tham chiếu, strict/transitional namespaces và thứ tự phát hiện body/table/nested/run đã có.
- Thêm native positive hợp lệ và negative cho part tham chiếu mang tên dễ bị skip; tiếp tục kiểm nguyên UTF16 positive/DTD, canonical footnote split-run, raw/member hashes và full paragraph/run spans. Không sửa output theo đáp án Root, không dùng exception bất kỳ hoặc 0tokens làm safety PASS.

## 3. U02 còn lại — kiểm cả thành công, lỗi và mọi side effect

Root đọc FULL549 dòng; agent kiểm độc lập cùng SHA `d53ef5e4000d8f7b6e9e20dff4bdbe56114810f3c2e58359935fde04ec7c45cd`. U01 giữ chỗ đồng bộ/owner cleanup và G7 query generation đã sửa về source; không phá hai sửa này.

- **Upload chưa giữ general form context (`:79,184,203–207`):** upload v2 đang chờ, người dùng sửa mapping/KT/CFO input của v1 chỉ tăng genForm; completion cũ vẫn chọn v2, toast và refresh. Capture/kiểm đúng form generation ngoài File/loại/mã/tab/version/actor; completion/retry cũ không ghi cache/DOM/status/toast, đổi lựa chọn hay xóa nháp mới.
- **Tải tệp gốc thiếu tab/form fence (`:222–236,308`):** đang tải DOCX ở G1, chuyển G7 nhưng pbChon giữ nguyên; blob cũ vẫn a.click và ghi status. Kiểm trước request, sau mọi await kể cả blob/arrayBuffer/digest, ngay trước tạo URL/click/status. Context cũ không tự tải tệp; current-context download vẫn hoạt động và kiểm hash được.
- **GET catch thiếu fence (`:256–260,289`):** danh sách GET đang chờ, người dùng nhập nháp mới rồi gặp network/500; catch vẫn ds=null/ve làm mất editor đang nhập. G7 GET lỗi về sau chuyển tab vẫn ghi status cũ. Áp dụng fence đồng nhất cho success/error/retry timer của GET, giữ nháp và editor mới. Không giữ dữ liệu vượt quyền khi có sự kiện thu hồi/đổi vai hiện hành; xử lý security invalidation theo seam chung.
- Rà các đường async trong chính file này để cùng invariant, không chỉ sửa ba dòng minh họa. Một intent giữ nguyên File/bytes/header/key khi retry trong context hợp lệ; không cấp khóa mới để che kết quả unknown. Barrier đổi vai, current-rights backend và phân biệt JSON mutation/GET giữ nguyên.
- Ca cần chứng minh sau terminal: current-context positive; initial doubleclick1POST; unknown exact retry; upload chờ rồi sửa form; blob chờ rồi đổi tab/form; GET lỗi sau nháp mới/đổi tab; G7 A/B về ngược thứ tự. Syntax/source-string checks không thay kiểm hành vi.

## 4. T01–T03 — bộ kiểm HTTP hữu hạn, giữ toàn bộ dữ liệu

Root kiểm trực tiếp `tests/test_crm_41_02_http.py:90–135,366–388,423–510`, agent đã đọc FULL581.

- **T01:** bỏ probe SQL `DELETE FROM kho.viec_can_duyet` ở383. Lệnh được kỳ vọng bị từ chối vẫn trái yêu cầu không DELETE. Giữ các negative INSERT/UPDATE/SELECT có ý nghĩa; không thay bằng DELETE/DROP/TRUNCATE/cleanup khác, không bỏ cả nhóm typed K5.
- **T02:** đóng đúng các connection được test sở hữu, kể cả cached ordinary `app._crm.conn`, owner `app._crm_g.conn_tin_cay` và các kết nối direct service g10. Dùng finally/cleanup idempotent phù hợp cả setup lỗi, assertion lỗi hoặc worker lỗi; nhả Events, join hữu hạn, dừng server/đóng socket, khôi phục env. Không bỏ connection/thread chạy sau test hoặc đóng nhầm tài nguyên người dùng. Giữ DB/role/files/artifacts.
- **T03:** g10/g11 không được dùng sleep+is_alive làm bằng chứng đã đến đúng namespace/quyền lock. Quan sát actual worker backend PID và `pg_blocking_pids`/wait evidence bằng connection observer trên chính fresh DEMO DB; chứng minh đúng blocker trước khi release. g10 dùng hai owner service connections thật; g11 nối PID đúng request đang chờ row quyền của transaction thu hồi. Finite deadline/setup lỗi/deadlock/timeout không tính PASS. Workers phải kết thúc cả đường lỗi.
- **T04 — hai lỗi native pure đã chạy thật:** Root chạy đủ27 ca trên bản freeze:25 PASS,1 FAIL,1 ERROR,0skip; AST10/JS syntax đạt, toàn bộ source/runtime giữ hash, owned children đã dừng. `test_c4_setup_dung_mot_dong:405` đếm1 nhưng tệp f77 thực có3 dòng chọn nguồn tại519/626/654, gồm dòng đã có và hai bổ sung đúng phạm vi; sửa kỳ vọng theo từng ngữ cảnh và giữ whole-file SHA, không sửa tệp M4 cho vừa test. `test_guard_chu_the_k5_chi_them_nhanh_typed:158` StopIteration do tìm hàm legacy trong active `PG_MIGRATIONS[:17]`; chọn đúng căn cứ và kiểm guard thực sự active, phân biệt định nghĩa lịch sử với trigger đang dùng. Không bật lineage fullM9, không sửa migration để làm xanh test; không xóa/bỏ qua case hoặc hạ kiểm typed K5. Các kết quả Root này không phải Claude self-test.
- Observer native hiện chỉ count/sequence/top-level filenames; không mô tả như whole rows/catalog/recursive file hashes 0delta. Native g03 chỉ upload replay trước later revision; không gọi là đã bao phủ exact original-body/token replay sau mọi revision hoặc RR race. Các kiểm độc lập này vẫn phải làm riêng sau terminal.

## 5. Báo cáo và giới hạn thực thi

- Cập nhật báo cáo đúng lượt trước exit0 và các sửa P02/U02/T01–T03 đã viết; các test mới chỉ được ghi **NOT_RUN_CODE_ONLY**. Root sẽ ghi kết quả chạy của mình riêng, không tự chép thành Claude self-test PASS.
- Sửa diễn giải guard: hàm `viec_chu_so_huu` được thay ở M18 chưa có trigger active trong default chain, không dùng nó chứng minh typed K5 đang chặn. Guard active được review là `crm_g_viec_kiem`; migration không nằm trong phạm vi sửa lượt này.
- Chỉ Read/Glob/Grep/Edit/Write trên phạm vi đã cho; không Bash/Agent/Task/session mới/AST/import/test/SQL/server/Office/AI/cloud. Không xóa/rename/move/reset/cleanup bất kỳ file hoặc dữ liệu nào. Root review và chạy kiểm sau terminal, không chạy đồng thời writer.
- Những gì còn lại của full CRM41–42 và M4 (Review L1–L3/OCR/approval/PDF/nghiệm thu–công nợ/Request) giữ nguyên trong hàng chờ đã chốt; gói sửa này không thay định nghĩa hoàn thành module.
