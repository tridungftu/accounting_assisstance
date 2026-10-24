# CRM-41-01 — Binding thực thi common engine, CODE_ONLY

**21/10/2026 · phạm vi đã được Anh giao; CODE_ONLY khi Root release.** Bổ sung handoff GIAO-CODE-CRM-41-01-ENGINE-DUNG-CHUNG.md (70197bf9830eab6201c8f5a25e27e63cefedd28ef5fd4735cdb24c50e5d28133). Chỉ viết trong 18 targets cuối file; không tự chạy.

## Source patch và một implementation
- Thư mục docs/CRM-41-01-SOURCE-PATCH là bản kỹ thuật byte-exact để soạn patch, KHÔNG là core runtime, package import hoặc dependency central. Manifest 6f8ebda24fdef5f8038bd5995f65b8662966e096d2e53fbc9a9354cbed23d2dc. Claude chỉ sửa bốn bản patch và viết test nguồn ở đó; không truy cập dự án nguồn thật.
- Sau terminal, Root rà diff, backup và kiểm source originals chưa đổi rồi áp đúng patch vào dự án nguồn #6. Runtime/test phải dùng source #6 thật; cấm sys.path/import từ thư mục docs hoặc copied review_goc extractor. Giữ mọi bản lịch sử/file.
- Dùng đúng bốn source EDIT và một source test NEW đã bind. Không sửa master_hd.py, server.py, cau_hinh.py, viec.py, catalog XLSX hoặc source test cũ.

## API đã có và common/v1 được bind
- Base URL do host cung cấp tường minh: http://127.0.0.1:<port>, thiếu URL báo NOT_READY; không mặc định gọi port8600, LAN/redirect hoặc khởi chạy app thật. Header X-HD:1 và Host khớp source.
- POST /api/trich_xuat {} → luot; upload POST /api/trich_xuat/{luot}/tep?ten=<urlencoded.docx> raw bytes; POST /api/trich_xuat/{luot}/chay → viec; GET /api/trich_xuat/{luot} → trạng thái/hd[].tai.json. Lấy native JSON bytes theo tai.json (GET hd/{ten} là VIEW đã bổ sung trường, không hash view thay raw). POST /{luot}/dung chỉ dừng việc thuộc intent của client. Lỗi nguồn dùng loi/chi_tiet.
- New start DTO: contract='trich-tham-so-common/v1', mode='RULE_ONLY', loai_hop_dong='XD', catalog_id='XD', catalog_sha256='05846a2acd60f2cde708d13a163a137ee3fb0b4e08fd84f85a7e14e7ef861bcd', source_sha256=<rawH>, request_id=<stable caller intent>, tham_so=<unique nonempty codes> hoặc literal 'ALL'. Một DOCX/lượt common. Catalog SHA là content version; không bịa version/catalog có sẵn.
- Kiểm contract/mode/type/catalog tồn tại+SHA TRƯỚC load_params/read_catalog (helper có thể tự tạo catalog khi thiếu). Missing/[]/unknown/duplicate/wrong-type/hash mismatch khác nhau, báo rõ trước compute; ALL expand thành mã thật. Giữ legacy không có contract theo API cũ; contract lạ không fallback legacy/XD.
- Snapshot deep-copy params/thuộc tính, rules version/hash, requested/expanded codes, raw sourceH và implementation identity ngay lúc nhận start. Lưu vào tuy_chon và output trước lần ghi raw JSON đầu; không giữ tham chiếu global mutable. Run khác/đổi catalog không đổi snapshot cũ.
- COMMON reserve run/intent và đóng upload trước capture; upload/start cùng run dùng chung khóa ngắn. Đọc raw DOCX và catalog bytes đúng một lần, kiểm SHA trên chính bytes đó; giữ bằng CreateNew trong run và parse/load_params chính snapshot ấy. Deep-copy expanded params/rules/request metadata; worker không đọc lại live upload/catalog. Khác request_id/body/catalog/bytes → conflict; capture lỗi phải ghi trạng thái rõ. Thêm test interleaved replacement để chứng minh snapshot cũ giữ nguyên, không sửa legacy API.
- COMMON branch trước doc_cau_hinh/la_claude/keys/AI probe. LuotChay mode RULE_ONLY bỏ kiem_tra_ai/cache; TrichXuat ai=None/cloud=None/ra_lai=False; QuanLyViec.tao dung_ai=False; ghi_danh_muc_hd=False. Không config inheritance, cloud, OCR hoặc Office.
- Giữ đúng XD37 semantics hiện tại: tái dùng actual master_hd.trich_xuat(...,llm=None) và TC rules bên trong source common engine; NR hiện chỉ nhận TC-* từ supplemental rules. Không mở thêm TT financial policy hoặc coi đoạn liên quan là giá trị. Source bỏ qua AI không đồng nghĩa bỏ rule positives; không đổi legacy thuật toán.

## Client chung và consumer thật
- Một file nguon/trich_chung_6.py cho common client và một projection bang[]→tham_so[]. Giữ native bytes/hash riêng với normalized view/adapter version; không ghi đè raw, không đặt lại output source hash bằng hash view. Không ghi raw document values vào report.
- Source errors/timeouts/UNKNOWN phải rõ. Giữ stable request_id/body/key và durable reference tới luot/viec/result trước publish. Retry cùng intent đối soát status/result đã biết; không tự create/run lại khi chưa rõ kết quả. Same intent khác body/catalog/codes báo conflict. Không dựng queue/framework thứ hai.
- NR.trich_hop_dong thành thin common wrapper; không còn active copied TrichXuat/master_hd extraction hoặc silent fallback. Giữ nguyên document safety/quote validation/BOQ/Review L1–L3 và vendor pins. XayDungK2 giữ SOAN trước upload, raw/revision preflight và SQL CAS/current rights trước publish.
- M4 gửi XD/catalogH/ALL37 tường minh: SQL XONG cần đủ37, không đổi DDL để nhận subset M4. Common engine/CRM có thể chọn subset và phân biệt NOT_REQUESTED với CHUA_CO; chưa có catalog KCN/nhà ở/MUA thì unsupported, không mượn XD.
- CRM thêm raw DOCX intake + loại/catalog/mã trích trên card hiện có (app.js tạo DOM, không sửa index). Financial loai_hinh không phải extraction type. Giữ legacy /api/crm/nhan JSON và mẫu /api/crm/mau, một master và quyền A/B/CFO/KT hiện hành. Auth PN/module/project trước side effect/common call; recheck trước ghi kết quả. Envelope common metadata phải explicit versioned/validated, giữ legacy keys compatibility.
- Network/compute/polling ngoài K2 transaction và global mutation_lock. Reuse m4.py owned ordinary+owner seam _review_lenh; route CRM dùng owned connection riêng, không cached mutable CRM connection cho việc dài. Context/role/source-revision thay đổi không publish sai; giữ original intent khi retry, callback muộn không đổi draft mới.
- Source endpoint cấu hình host qua KHO_TRICH6_URL/explicit constructor injection; không từ browser arbitrary URL/path. Demo source có sẵn HD_DU_LIEU/HD_OUT_DIR/HD_DANH_MUC_HD/HD_CSDL/HD_THU_MUC_KHOA; Root đặt fresh retained paths trước import và gọi tao_may_chu(0), KHÔNG main(). Không thêm startup/workroot framework.

## Kiểm và giới hạn
- Viết source test strict snapshot/khác tập mã/concurrency/legacy/offline và central test client/projection/actual two consumer wiring/current-rights/revision/UNKNOWN. Dùng DEMO không rỗng; không fake output rồi gọi engine accuracy đạt. Tests runtime do Root chạy sau terminal.
- Existing test_crm_phan_tich.py chỉ AdapterTests/legacy-common wiring; giữ financial oracles khác. test_m4_01b_tinh.py chỉ đổi wiring engine dependency phù hợp refactor, không giảm quyền/quote/state/financial oracles; báo rõ test nào unit IO-mock và test nào actual source API. Native review K2/HTTP và migrations1–20 giữ nguyên bytes.
- Không DDL, migrations21, pyproject/index, M9, M2 mới, E1 catalog/table typed mới, PDF/Request/AP, cloud/realdata. M2-00 sau CRM dùng #7; E1-MUA tiếp sau và mở cùng #6.
- CODE_ONLY: chỉ Read/Glob/Grep/Edit/Write; không import/AST/commands/test/SQL/network/Office/browser/launcher/delete/cleanup. Report NOT_RUN_CODE_ONLY, nêu file/function/limitations cụ thể. Nếu timebox chưa xong, giữ partial và ghi thật, không thu hẹp mục tiêu hoặc tạo placeholder thành hoàn tất.

## Exact editable existing (14)
- docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py
- docs/CRM-41-01-SOURCE-PATCH/trich_xuat/danh_muc.py
- docs/CRM-41-01-SOURCE-PATCH/trich_xuat/lo.py
- docs/CRM-41-01-SOURCE-PATCH/trich_xuat/quy_trinh.py
- src/kho_tri_thuc/nguon/trich_hop_dong_6.py
- src/kho_tri_thuc/k2/xay_dung.py
- src/kho_tri_thuc/k2/crm.py
- src/kho_tri_thuc/giao_dien/server.py
- src/kho_tri_thuc/giao_dien/m4.py
- src/kho_tri_thuc/giao_dien/assets/app.js
- src/kho_tri_thuc/m4/giao_dien/m4.js
- src/kho_tri_thuc/m4/nguon_review.py
- tests/test_crm_phan_tich.py
- tests/test_m4_01b_tinh.py

## Exact new (4)
- docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py
- src/kho_tri_thuc/nguon/trich_chung_6.py
- tests/test_trich_chung_6.py
- docs/BAO-CAO-CRM-41-01.md
