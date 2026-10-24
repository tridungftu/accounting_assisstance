# Giao Claude M4-01 — Review dùng lại và Cổng hồ sơ có gate nộp thật

**CODE_ONLY / M4_APPROVED / 20-10-2026.** Đọc kế hoạch `docs/M4-KE-HOACH-DA-CHOT-20261020.md`. User đã yêu cầu IMPLEMENT, không dừng lại để xin xác nhận lại kiến trúc. Cùng session52783bcd; Root kiểm độc lập sau terminal. Gói này là lát đầu của fullM4, không gọi toàn M4 hoàn tất. Không tự chuyển sang gói2.

## 1. Đầu ra gói này

Trong shell hiện có, mục M4/Bàn review có Cổng hồ sơ nội bộ chạy thật: danh sách theo quyền PN/dự án/người phụ trách; tạo/lưu nháp; upload nguồn HĐ; chạy trích bằng core nguồn; xem/sửa/xác nhận tham số bởi DU_AN; khai PL và bổ sung; nhập/map BOQ; upload hồ sơ đợt; preflight chỉ rõ thiếu và Nộp chính thức khi đủ. Dùng lại HĐ đã có cho đợt sau. Thay căn cứ có revision/stale guard.

Đưa cấu trúc workbench/source UI và reusable engines vào package M4 để các chức năng hiện có tiếp tục được nối ở gói2. Không làm tám nút menu giả rồi báo fullreuse. Gói1 phải hoàn thiện luồng intake/departmentconfirmation/BOQ/submit bên trên; các phần review/downstream chưa nối phải ghi đúng trạng thái, không tạo kết quả giả.

## 2. Tái sử dụng code có căn cứ

- Reference65file đã lọc tại `docs/M4-REVIEW-REFERENCE-20261020/`, có manifest SHA256. Đây là technicalsource, không phải authority đang chạy; không đọc app nguồn ngoài workspace.
- Có thể viết `tools/nap_nguon_review_m4.py` để Root chạy sau terminal, sao chép byteforbyte các module/assets/catalog cần dùng từ reference đã pin vào package mới. Script chỉ tạo file mới/kiểm hash, không xóa/replace/overwrite source. Claude viết code wrapper/adapter trong package; không phải chép lại hàng nghìn dòng qua model. Liệt kê file generated cần thiết và lệnh bước này trong report.
- Tái dùng `TrichXuat(...).xu_ly()` cùng `doc_hop_dong/cau_truc/danh_muc/kiem_tra/logic`; catalogue37 mã, không lấy `csdl_hop_dong.DS_THAM_SO`36 mã làm contract vì thiếuTC09. K2 giữ đủ nguyên giá trị+nguồn+trích dẫn+trạng thái.
- Tái dùng parser BOQ/map cột ở `may_chu/nghiep_vu.py:70–183`; PL/BOQ/tham số hiệu lực ở `csdl_hop_dong.py:352–434`. L1 `toan_ven.KiemTra(path).chay()` và L2 `tinh_doi_chieu_dot` để seam gói2.
- **Seam SQLite legacy:** chỉ projection `sqlite3.connect(':memory:')` mỗi job, từ snapshot K2 cùng PN/HĐ/revision, load schema source rồi gọi thuật toán bằng connection inject; không gọi mo_csdl/_cs/_csdl, không fileDB/masterpersist thứhai, không SQLtranslator. Readonly sau populate; mapping/decision muốn giữ phải đi qua K2 service. Không nạp dữ liệu thật vào projection.
- Không bê nguyên global config/paths/key/cloudfallback/scanLAN của nguồn. Inject output path trong DataRoot riêng, config/AI local/OCR availability tường minh; cloud luôn tắt gói này. Không đọc cấu hình/key/sourceDB của app gốc. Nếu AI/Word/OCR chưa sẵn phải trạng thái thật, không đánh dấu trích xong/xác nhận giả.
- Văn bản DOCX nhỏ hợp lệ và BOQ XLSX DEMO phải có đường xử lý file thực; AI contract test có thể inject fake thuật toán đã khai rõ để test plumbing, nhưng không gọi mock đó là localAI thực. Các trường thông tin chung có quy tắc nguồn dùng lại, không tự bịa tiền.
- UI giữ ngôn ngữ source/Bàn kiểm soát: font Be Vietnam Pro (fonts/OFL có reference), navy#19334d, bg#f4f6f9, ink#24364a, border#dfe5ec, cảnh báo amber#895a14. Sidebar/bảng/chi tiết nguồn và checklist đủ/thiếu là trọng tâm. Không framework/dependency UI mới; CSS namespace M4 để không ảnh hưởngCRM.

## 3. Dữ liệu/quyền và migration

- K2 PostgreSQL là authority; dùng master.hop_dong/hop_dong_phien_ban/hop_dong_tham_so/du_an hiện có với typed extensionM4 cần thiết (files/extraction/BOQ/PL/dossier/projectpermission/revision/preflight/submission). Không tạo HĐmaster song song hoặc lấy CRMlịchthu làm hợpđồngxây dựng.
- **Append migration17** sau common13/14/15/16; giữ byte/checksum prefix1–16 và fullM9 legacy không đưa lại. Currentrole đã có DU_AN; thêm M4 actions riêng, không sửa CRM.DUYET/CFO thành DU_AN.
- RLS/guard core hiện gắn HOP_DONG_TEP→CRM, NGHIEM_THU→M1: phải thêm discriminator/ownership M4 tại M17, giữ behavior hàng cũ. Không cấp CRM rộng hoặc bypassRLS cho DU_AN. Chỉ PN/module chưa đủ: project+dossier scope/owner được khai báo và kiểm phía backend/CSDL; same-PN khác project phải có ca âm.
- Session server ID+login hiện có, không nhận actor/confirmation/approved/projectauthority/provenfacts từ browser. RoleDEMOchỉMO_PHONG_. Kiểm ordinaryapp login, publichelper privileges và compositeFK; ownerconn (nếu thật cần capture) tách khỏiusercommands.
- Raw files immutable bằng storage primitives; gắn PN/project/docrole/sourcehash/revision. Upload pending chưa đầy đủ vẫn lưu được. Wrongtype/path traversal/byteszero/media mismatch báo lỗi, không trả rawfile ngoài quyền.
- Nếu tận dụng M0capture thì thêm scope M4 đúng nghĩa hẹp trong `k2/nguon_chung.py` và DDL/cap; không fake scope warehouse/MaKho/SoPhieu. Có thể dùng raw sharedstorage +typedM4 commands hiện có nếu không cần prePNcapture; không dựng universalframework mới.
- Tách xac_nhan_tham_so_M4 (DU_AN) khỏi duyet_ho_so_dot_M4 (CFO/reviewer) và KTconfirmation gói3. User chỉ giao department tựsoát/xácnhậnkhôngCFO. Xác nhận gắn source/extraction/catalog/revision; sửa giá trị hoặc căn cứ làm xác nhận liên quan hết hiệu lực. Tham số không áp dụng có trạng thái/lý do, khôngzero.
- Các trường thiếu phải có trong preflight: sourceHĐ, extraction actualsamehash, departmentconfirmation, PL declaration/completeness, BOQ parsed/mapped, hồ sơđợt/ngày. `van_nap` không bypass. PL khôngcó khác chưa khai; future/draftPL không áp sai ngày. Uploadfile không tự là parseOK.
- Formal Nộp chốt snapshot/refs/digest của cùngrevision; transaction lock+expectedrevision+unique operation receipts, replay bodykhác reject. Repeat/newinstallmentreuse khôngduplicate master. Quyền kiểm trước replay/file. Reviewer xem hồ sơ đãnộp theo scope; chưa autoapprove/downstream.

## 4. API/shell và fixtures

- Tạo namespace `/api/m4` trên LocalApp/session/token/mutationlock hiện có, service riêng `k2/xay_dung.py` + HTTPthin `giao_dien/m4.py`. Không dùng `/api/nghiem-thu` legacyactorcốđịnh, không webserver nguồn/iframebypass hoặc X-HDauth.
- API cần list/detail/create/save/upload/download/extract/parameterconfirm/PLdeclaration/PLimport/BOQpreview+map+import/preflight/submit; đặt tên rõ nhất quán và viết report routecontract. Không nhận filesystempath/URLtựdo hoặc import executable từ upload.
- Body số exact/currencyraw, requestIDs string; bảo vệ XML/ZIP/Office path/resource có liênquan. Khôngnewlibrary; optionaltool unavailable báo thiếu. Nếu cầnpackagedata thêm pyproject chỉ vìassets/template/catalog, không đổi dependencies.
- UI rolechange/navigation/file phải epoch/barrier giữcurrentrights, khôngreanimate oldasyncresponse; giữ behaviorCRM/M2/M5/L11. Formcó trạngthái lỗi/thiếu cụ thể và nút tiếp tục tương ứng, bàn giao tại #m4 hoặc route cùng shell.
- SeedDEMO riêng bằng `k2/m4_demo.py`/`fixtures_m4.py`:2PN,ít nhất2projectcùngPN,DU_AN owners/otherproject/reviewer/KT/readonly; đừngmở permission của actorCRM hiệncó. Seed cósourcecatalog andDocx/BOQfakefixtures builders, khôngsourceactualdocs. DBprovision/migrate sẽ doRoot sauterminal.

## 5. Test và kết thúc

Viết tests có oracle rõ, không mirrorimplementation: thiếu từngcăn cứ→submitblockedkhôngbusinessdelta; draft/uploadallowed; pipelinefilethực vs mockAI declared; deptconfirm khôngCFO; fakebodyflags/wrongproject/samePNwrongowner/directSQL bypass reject; PLnone vsunknown; mappedBOQ vsfileexists; reuse acrossinstallments; changedsource invalidatesconfirmation/submitstale; duplicate/retry/concurrent namespace; downloadrights;37catalogpreserved; prefixold16immutable +ordinaryRLS. Keep all artifacts; noTemporaryDirectory cleanup/unlink/rmtree/rename/DROP/DELETE/truncate. Không sửaguard hoặcskiptestđểpass.

**CODE_ONLY**: không Bash/SQL/product/import/test/HTTP/browser/server/localAI/OCR/cloud. Self-test ghi NOT_RUN; đưa lệnh cần chạy trongreport choRoot. Không sửa protectedfiles ngoài allowlist, không chạm CRM/M9/M1/L11/oldbridge/guards/root.env/sourceapp. Chỉ tạo/sửa allowlistedfile. Đừng tựrun bộ vendoring script. Thoát khi code/test/report đầyđủ; không giữprocesschờ. Report `docs/BAO-CAO-M4-01.md` phải nêu phần đãcode/gói sau/limitations/source reuse mapping/migrationprefix/routes/testsNOT_RUN. Không gọi sourceanalysis hoặc menuplaceholder là fullM4done.
