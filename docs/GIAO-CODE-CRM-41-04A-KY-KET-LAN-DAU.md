# CRM-41-04A — Ký lần đầu bất biến, có giao diện
Trạng thái: ROOT_PUBLISHED_AUTHORIZED_CODE_SCOPE_NOT_PRODUCT_ACCEPTANCE. Gói coding hữu hạn đã được Root chọn từ yêu cầu Anh triển khai CRM song song kiểm M4; không phải thay kiến trúc hay xin chốt lại nghiệp vụ.
Mục tiêu: từ bản xuất G3 hợp lệ, Bán hàng ghi nhận PDF ký lần đầu; lưu bằng chứng/lineage và khóa bản soạn, xem lại/tải trong quyền. Chỉ G4 và trạng thái G5 ban đầu; không làm engine, G6, correction hay Word infrastructure.
Căn cứ: spec41:25/44/88/103, spec42:107/138–146/191; delta3.7 và queue4–5. Q-RETURN/Q-SAMPLE/Q-PII chỉ chặn nhánh tương ứng, không chặn coding first-sign DEMO.
Tài liệu giao code: docs/GIAO-CODE-CRM-41-04A-KY-KET-LAN-DAU.md; Root bind hash/release trước dispatch. Chỉ một product writer CRM; các agent kiểm M4 không sửa các target CRM của lượt này.

## 1. Baseline và tái dùng
- Baseline Root bind: frozen m4-ui-awake-partial-frozen-b96dc1984440, source384/runtime454. Prefix toàn pg_migrations.py hiện có 928356B H225cc40f14670e8428bf8afcc58318c04c15707bdddffa31242067f20199cce2 phải NGUYÊN BYTE (migration1–22). Chỉ append migration23 theo cấu trúc hiện có, không sửa một dòng cũ.
- CRM current byte-exact F19: k2/crm_giao_ket.py885L Hc155c5336f88a97640556cbc17ae7fb007fcf96806d49ab56b4f05815843cc56; HTTP crm_g.py292L H1ee1b2a8ec91f17b7139854b0bfb0a4bb34f0181bf0633fd6f2c1a71b364c5dd; UI crm_g.js1126L H49d449972c2e05302e2127f181ab925fdb80e543c5deac96d22b620653fff1ac.
- Reuse CrmMauK2 factory/identity/_tx/_uuid/_khoa/_h/_v, crm_g_bn receipt/current rights, write_immutable content store, existing master HĐ/PN/project/customer/template/profile, crm_hd_soan/rev và crm_gk_xuat/lan. Không lập master/role/engine/server khác.
- Existing CRM G3 Word positive vẫn OPEN; không khảo sát Office/Normal.dotm/registry. Có thể code contract/storage/state/UI ngay, nhưng positive xuyên chuỗi G3→G4 chỉ được nghiệm thu sau actual G3 PDF_DAT được tạo hợp lệ. Không owner-forge producer receipt/PDF_DAT để bỏ gate.
- Không sửa engine #6 hoặc API engine dùng chung; M4/M2/CRM tiếp tục dùng ONE engine theo quyết định đã chốt. Gói này không gọi OCR/AI/Word/provider.

## 2. Exact write scope: 3 existing + 5 new = 8 files
EDIT existing:
1. src/kho_tri_thuc/ha_tang/pg_migrations.py — append ONLY sau toàn928356B nền, migration23; M4/M9/B và migration1–22 bất biến.
2. src/kho_tri_thuc/giao_dien/crm_g.py — route/factory G4 mỏng trong namespace giao-ket đã được dispatcher nhận, không cần sửa server.py.
3. src/kho_tri_thuc/giao_dien/assets/crm_g.js — dialog ký và khối bằng chứng/lịch sử tại bản soạn hiện có; dùng kttChung.
NEW:
4. src/kho_tri_thuc/k2/crm_ky_ket.py — service G4 hẹp.
5. tests/test_crm_ky_ket.py — kiểm thuần, storage/lineage/CAS/DB guards theo pattern hiện có; phân biệt mock với actual PG.
6. tests/test_crm_ky_ket_http.py — contract/session/current rights/file/replay.
7. tests/crm_ky_ket_async.cjs — fakeDOM trên actual UI, controlled Promise/file/key/context; không nới assertions cũ.
8. docs/BAO-CAO-CRM-41-04A.md — code đã làm, kiểm đã viết nhưng NOT_RUN_CODE_ONLY, giới hạn và bước kiểm còn lại.
Không tạo file khác. Kết quả dự kiến source388/runtime459 nếu đủ5new (report không thuộc source); Root xác minh thực tế sau terminal. Không sửa crm_giao_ket.py, crm.py, crm_mau.py, renderer, app.js, server.py, M4JS/sql_review/source37, M9 hoặc file test/report lịch sử.

## 3. Backend ký lần đầu và lineage
- Input tối thiểu: soan_id, expected_revision, expected_xuat_id (bản PDF_DAT hiện hành mà dialog đã chụp), raw PDF bản ký, tên tệp thuần, ngày ký, co_sua boolean Có/Không bắt buộc, mô tả khi Có, người ký khách tùy chọn, khoa. Actor/PN/status/hash/result/receipt/path không nhận từ client.
- Đọc quyền hiện hành trước lookup/replay/hash/path/bytes. Nhận raw PDF có giới hạn dùng lại cap/runtime sẵn có; kiểm PDF cấu trúc hợp lệ/có trang bằng parser sẵn có. Scan hợp lệ được nhận; đuôi/magic không đủ, hỏng/mã hóa không đọc được fail closed. Không OCR hoặc so nội dung với bản sinh ở G4.
- Chỉ ký từ CHO_KY của cùng CRM MAU master HĐ; đúng revision, đúng template/map/catalog/profile/source snapshot đã pin và đúng bản xuất G3 HOP_DONG/PDF_DAT đã công bố hợp lệ.
- Pin expected_xuat_id và CAS với bản xuất hợp lệ HIỆN HÀNH/MỚI NHẤT của revision; nếu có export mới cùng revision sau khi mở dialog thì 409/reload, không chọn ngầm bản khác. Resolve hash/bytes/input lineage ở server; không tin hash client. Xác minh artifact G3 còn đúng hash/length trước commit.
- Signed PDF là evidence KHÁC bản PDF G3; lưu hai hash/length/ID riêng. Snapshot nguồn đã ký là snapshot bất biến của bản xuất được chọn, không đọc tham số draft hiện hành thay thế khi xem lại.
- Lưu content-addressed bằng write_immutable TRƯỚC commit DB; lỗi/rollback vẫn giữ raw, không cleanup. Đúng một transaction cho signed entity, pinned lineage/snapshot, DA_KY, G5 initial state, audit và receipt; lock cùng subject HĐ để ngăn ký/sửa/xuất đồng thời.
- Unique (HĐ, signed_pdf_hash); cùng khoa+cùng business body/hash trả receipt cũ; khác body cùng key→409. Cùng PDF/key mới và cùng căn cứ/ngày/khai báo trả cùng signed ID, không tạo record/audit/queue mới. Cùng PDF nhưng metadata/căn cứ xung đột không được âm thầm ghi đè.
- Sau ký lần đầu, PDF khác/đổi ngày/khai báo/thay bằng chứng/mở khóa/correction/hủy sau ký đều chặn rõ Q-RETURN, giữ bản ký/lịch sử. Không làm replacement/reopen.
- Không sinh master HĐ thứ hai, hop_dong_phien_ban hiệu lực, lich_thu, nghĩa vụ, tiền M1, doanh thu hay Junsky write ở gói G4.
- G5 initial state cùng transaction: co_sua=true→PENDING, reason BAT_BUOC_KHAI_CO/chưa thực thi; false→NOT_SELECTED/chưa áp dụng chọn mẫu. Không MATCH, không đối chiếu tay/dispatch worker, không random policy50/10/20. UI không nói worker đang chạy.
- Trạng thái hiển thị “Đã ký — chờ kế toán kiểm”. Chưa tạo persistent K5 work/KT queue thì KHÔNG toast “Đã chuyển kế toán kiểm”; K5 bridge/G6 để gói tiếp.

## 4. Scope quyền có căn cứ, không suy owner
- Existing crm_gk_duoc10856 chỉ PN+CRM+vai/action; master.phan_cong_hanh_dong9691 chỉ PN/module/action/loai_hinh. Chúng CHƯA chứng minh quyền dự án/khách được giao; không dùng tao_boi==owner thay policy42.
- Root đã chốt kỹ thuật: append thin scope binding tham chiếu master.phan_cong_hanh_dong + subject HĐ CRM (FK cùng PN), snapshot/current project+customer đối chiếu đúng master/soan. Coder chọn physical name/DDL tối thiểu; không tạo role/master hay IAM khác.
- Bán hàng ký: current active user + moduleCRM/PN + vai Bán hàng hiện hành + assigned action + explicit current PN/project/customer/HĐ binding còn hiệu lực. Missing/stale/revoked/cross-PN/same-PN-wrong-project-or-customer→fail closed TRƯỚC replay và trước trả metadata/bytes.
- Khách dự thảo chưa Junsky không tự bị coi là đã gán mã; scope binding phải nhận diện đúng customer snapshot/draft reference đã có, không suy từ tên. Binding đổi revision/source/customer phải được kiểm lại; thiếu căn cứ thì báo chưa cấu hình phạm vi.
- KT/CFO đọc bám existing roles/PN và action narrow/current scope; không tự broad grant để làm DEMO pass. Subject/assignment snapshots bất biến, thu hồi có dấu/audit, không xóa. Chỉ owner/admin có thể tạo explicit DEMO assignment cho MO_PHONG mới, không auto-grant khi seed/reopen và không cấp tài khoản thật.
- Q-PII: DEMO dữ liệu giả; giữ gate tài liệu thật chứa fullCCCD/STK. Không log nội dung/PII trong audit/errors; audit tải ghi actor/subject/mục đích/hash/time, kiểm quyền trước đọc kho. Không chỉ mask CSS.

## 5. Khóa G3 sau ký và bảo toàn công bố muộn
- Cần backend guard thực, không chỉ disabled UI. Existing crm_gk_soan_luu11093–11134 luôn tạo revision; crm_gk_xuat_ghi11137–11185 có thể đưa CHO_KY khi PDF_DAT: append guard scoped signed HĐ cho CẢ save, new export reservation, và publish render đang bay.
- Sau first-sign, sửa trường/lịch/đổi mẫu/re-export mới bị chặn; ordinary SQL/app bypass không tạo rev mới/ghi đè snapshot. Không sửa tại chỗ signed row/source/revision/raw.
- Render G3 bắt đầu trước ký nhưng trả sau ký: giữ artifact/history, chỉ công bố lịch sử DA_CU hoặc từ chối chuyển trạng thái có lý do; tuyệt đối không hồi DA_KY→CHO_KY/SOAN_THAO hoặc sửa signed lineage. Replay receipt cũ có quyền hiện tại trả lịch sử cũ mà không lặp side effects.
- Không thay nhánh B/CFO, M9/VAY, M4 hay general master guards. Chỉ nhánh HĐ CRM có signed evidence.

## 6. Route và giao diện hữu hạn
- Dùng /api/crm/giao-ket/ky/{soan_id} (GET thông tin/điều kiện/dialog basis + signed history) và /api/crm/giao-ket/ky-ket (POST rawPDF + X-CRM-G-Info theo pattern upload hiện có); tải ký qua /api/crm/giao-ket/ban-ky/{id}/tep. Tất cả thuộc prefix giao-ket đã route, không sửa server.py.
- HTTP strict keys/query/UUID/header/body/content/size, same-origin/session/token hiện có; actor lấy app.crm_phien, không body. Phân loại 400/403 hoặc404 ngoài scope/409/413/503, không nuốt lỗi generic thành thành công. Không giữ mutation lock dài khi parse PDF.
- Từ editor CHO_KY: nút Ký kết mở dialog giữa trang; chọn PDF/ngày/người ký tùy chọn/Có–Không + mô tả; hiển thị snapshot mẫu/revision/bản xuất/hash/số dòng/tổng/currency để Anh kiểm.
- Chưa chọn Có/Không, thiếu PDF, quyền/basis stale→không gửi. Boolean false là khai Không hợp lệ, không đồng nhất với missing/null.
- Sau ký: read-only tham số/lịch/mẫu; khối Bản ký & đối chiếu có ngày/người/hash/khai báo/G5 honest state và tải/lịch sử; file xuất cũ vẫn mở trong quyền. Không giả G6 hay current acceptance.
- Reuse kttChung role/context barrier và patterns file intent/receipt; exact File+metadata+key được giữ khi UNKNOWN. Bấm lặp không phát request khác; context/PN/project/HĐ/role thay đổi không toast/render/detail/blob-download cũ lên context mới. Trở lại phải còn đường đối soát đúng intent, không blind key mới. Không copy lỗi một-global-retry sang G4; không dựng framework queue.

## 7. Acceptance của gói và cách báo
1. Thiếu/không-PDF/hỏng/quá cap, ngày sai, co_sua missing/null/string, extra authority fields đều chặn; false đúng boolean nhận.
2. Chưa CHO_KY/PDF_G3 chưa DAT/khácHĐ/revision/xuat stale hoặc artifact sai hash/length không ký; export mới cùng revision làm dialog cũ 409.
3. Positive chỉ từ actual valid G3 lineage: đúng một signed record, snapshot/template/revision/two PDF hashes, trạng thái DA_KY, không tạo nghĩa vụ.
4. Cùng key/cùngbody, lost ACK/retry, cùngPDF keymới và concurrent clicks không trùng; khácbody/cùngkey hoặc khácPDF sauký bị chặn.
5. Signed fields/raw/source bất biến; save/new export/directDB bị chặn; late render publish không đưa trạng thái lùi, lịch sử giữ.
6. Khai Có→PENDING mandatory; Không→NOT_SELECTED; không MATCH/worker-running/K5-transferred giả.
7. Current permission trước replay/detail/bytes; âm cùngPN khácproject/khách, revoked grant/user/module, stale binding; không dùng creator policy.
8. Tải signed bytes đúng hash/length/MIME/attachment/no-store và access audit; người ngoài scope không lấy được hash/path/bytes.
9. Controlled-Promise UI: thiếu input/duplicateclick/unknown exactFile+key/role-HĐ-PN-project switch/lateACK+error/blob/current basis refresh; old G1/G2/G3 UI behavior không bị nới.
10. Prefix1–22 toàn928356B và M4/source37/sql_review/M9/B nguyên; hồi quy cần Root chạy sau terminal. Bộ kiểm viết rõ mock vs actual PG vs actual browser; gói này chưa fullCRM.
- Trong lượt Claude CODE_ONLY chỉ Read/Glob/Grep/Edit/Write theo allowlist; không Bash/PowerShell/CLI/import/AST/test/product/SQL/Node/Word/Office/GUI/provider/network/Agent/MCP; không đọc var/.env/credentials/data thật và không xóa file.
- Hoàn tất đúng8targets, đọc lại phần sửa và ghi NOT_RUN_CODE_ONLY; báo còn gate actual G3Word/PDF positive, current grants/Q-PII, GUI/PG/independent checks. Không tự chạy công việc tiếp theo.
Ranh giới M9: chỉ đối chiếu tĩnh byte/guard bảo toàn; không seed, chạy test, khởi động hoặc mở lại code M9.
