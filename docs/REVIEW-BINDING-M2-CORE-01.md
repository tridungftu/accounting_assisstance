# Review độc lập binding M2/core — 01

19/10/2026. **STATIC_ONLY / PRECODE_REVIEW / M2_NOT_IMPLEMENTED / NOT_ACCEPTED.** Đọc full binding `BINDING-M2-CORE-SAU-CRM03.md` SHA256 `e800641166610dbd935b7a83eebb35450b8be2eec6a3212bace25155605b01f1` và draft `GIAO-VIEC-M2-MUA-HANG-VA-CONG-NO-DEMO-33.md` SHA256 `3660745409a6e23840282774ed203c6dd1e5e3f871cee36da29fc91c857c3d42`, đối chiếu source **frozen03** CLI89659/manifest121 `82e5e26806e05ef732536fcb0e474ab6ee96f646566e335e728da28921f47c3a`. Không lấy source sửa04 đang viết làm final; không import/chạy product/tests/SQL, đọc secret/row thật, sửa binding tác giả hoặc xóa file.

Finding là lỗ cần cụ thể hóa trong contract DDL/service trước coding, **chưa phải lỗi runtime đã tái hiện**. Root chưa approve toàn binding; báo cáo này không thay root review. Không thêm policy mua/thuế/FX hoặc bút toán giá trị hàng tồn kho; TL35§8.6/M5 chỉ số lượng giữ nguyên.

## P1 — R1. Unique theo event chưa ngăn cùng nguồn tạo hai event ghi nhận

**Anchors binding:** dòng48–50 (một identity/một sự kiện nghĩa vụ),78–81 (`su_kien_ghi_nhan*`, `ghi_nhan_de_xuat`),88–93 và I3. `UNIQUE(PN,event_key)` cùng partial UNIQUE(event,component,GOC) chỉ chống trùng **sau khi đã chọn đúng event/component**. Bảng source→event chưa có cardinality/capacity guard theo stable economic source grain.

**Counterexample tĩnh:** cùng logical invoice/component hoặc NT đã map có thể được hai request gán eventA/eventB khác key; mỗi event có một GOC và FK cùng PN đều hợp lệ, nhưng tổng vẫn ghi331 hai lần. XML/bảng kê/semantic revision/alias RQ khác source-row ID không được làm economic component mới. Xác nhận mapping có quyền không thay được constraint chống double recognition.

**Bổ sung:** canonical source economic component/alias registry hoặc ràng buộc tương đương, scope theo identity và logical component xuyên semantic revisions; khóa identity/component **trước** resolve/tạo event/claim. Một component nguồn chỉ map một logical recognition event, hoặc decomposition đã xác nhận với conservation capacity giữa các component/event. Không UNIQUE toàn header NT/invoice để chặn trường hợp một NT nhiều invoice/một invoice nhiều NT hợp lệ. Missing crosswalk/đã có legacy RQ/M4 proposal chưa quy về event thì giữ blocker, không tạo key mới để đi tiếp. DB guard phải áp cho cả M2 và M4, không chỉ endpoint M2.

**Ca cần có:** hai connection cùng invoice/source economic component nhưng event_key khác, M2↔M4 và XML↔bảng kê/semantic revision; tối đa một GOC hoặc decomposition được xác nhận đủ tổng, không hai liability đầy đủ. Control nhiều invoice/component thật sự khác vẫn tạo được claim riêng. Đã xuất/nạp thì alias/mapping mới không giải phóng nguồn để tạo GOC khác.

## P1 — R2. DIEU_CHINH cần semantic consumption riêng, receipt không đủ

**Anchors:** dòng79–81,91 và145–146. Partial unique chỉ áp role=GOC. DIEU_CHINH chỉ bắt buộc goc_id cùng event/component, chưa có uniqueness cho **cùng sự kiện chuyển basis/nội dung đã được ghi nhận**; operation receipt chỉ chống lặp một client_key.

**Counterexample tĩnh:** GOC100 đã xuất; cùng source correction được xác nhận100→120 và template DEMO cho delta20. Hai client_key khác nhau hoặc import source cùng nghĩa qua hai observations tạo hai DIEU_CHINH20 cùng goc_id; cả hai ngoài partial unique GOC và mỗi receipt đều mới. Mọi account/balance/fingerprint riêng vẫn có thể đúng nhưng tổng delta40.

**Bổ sung:** stable correction event/transition identity và DB consumption guard trên logical event/component, source correction/supersession và recognized predecessor; canonical payload hash để khác payload thành conflict. Policy/crosswalk/basis version hoặc PK mới không mặc định là quyền ghi delta mới. Correction chain không cycle/fork trái phép; claim/proposal/receipt được khóa và ghi cùng transaction. Claim đã xuất/nạp và refs cũ không hạ hiệu lực để lách. Chưa có adjustment policy thì đúng như binding: holding, không tự chọn delta/account.

**Ca cần có khi fixture adjustment đủ căn cứ:** cùng correction hai keys/two connections chỉ một semantic delta; receipt mới có thể trỏ cùng kết quả được phép hoặc trả conflict rõ. Thay policy version nhưng cùng economic correction không tạo delta lần hai. Một correction **thực sự kế tiếp** có predecessor/source change mới vẫn được xử lý đúng, không chặn mọi điều chỉnh bằng UNIQUE(goc_id) quá rộng.

## P1 — R3. Attribution phải chứng minh đủ coverage của phạm vi ghi nhận, không chỉ ≤ nguồn

**Anchors:** dòng58–62,132 và I2; frozen `engine.py:1030–1057`, `quick.py:1176–1215`. Core cũ sinh nhiều NET cùng debit header; writer tiếp tục áp header lên mọi NET, nên typed wrapper phải thực sự bảo toàn route/posting mapping như binding đã yêu cầu.

Contract hiện chốt sum attribution=posting magnitude và sum source/component≤amount có căn cứ. Hai điều này cùng Nợ=Có>0 **vẫn cho under-coverage**: fixture invoice full scope NET4m+6m, explicit tax0/total10m; proposal chỉ Nợ4m/đối ứng phải trả4m có attribution đủ cho dòng4m, header payable4m≤10m, dòng6m bị bỏ. Nếu recognition component xác nhận full10m, proposal này không đầy đủ dù tất cả bất đẳng thức nêu trên đúng.

**Bổ sung:** domain validator DB tại check/approve/export đối chiếu **equality/conservation theo approved recognition scope/basis**, gồm source NET components, TAX_HEADER/TAX_LINE/OTHER và payable đối ứng có căn cứ. Partial recognition chỉ hợp lệ khi scope/component/amount đã được xác nhận rõ, không suy từ số dòng còn lại hoặc tự phân VAT/discount. Mỗi NET attribution phải tới đúng source+route version và account/dimensions được policy cho phép; nhiều source chung một posting chỉ khi route/account/basis tương thích. Không header-edit/repropose/export làm mất đích rồi vẫn giữ fingerprint/claim cũ.

**Ca cần có:** full10m chỉ post4m bị chặn; double NET/source, thiếu6m, line account sai route, VAT header bị bịa chia dòng, header overwrite mixed destinations đều reject0 mutation. Control full4m CHI_PHI+6m XDCB theo **template DEMO được khai báo** có đầy đủ lineage; partial4m chỉ đạt với scope/basis partial đã xác nhận. Test này không tạo route KHO value journal và không chốt account/thuế production.

## P2 — R4. Tách immutable source snapshot khỏi route projection mutable

**Anchors:** dòng37/48 (version/source lines bất biến),58–60 (`chung_tu_dong.dich` projection route),132 (invalidation); frozen `pg_migrations.py:238–260`.

Một chỗ yêu cầu nguyên tập chung_tu_dong bất biến, chỗ khác cho sửa `dich` trên chính row đó qua quyết định route. Nếu khóa toàn row, route hợp lệ trước duyệt không cập nhật được; nếu mở UPDATE chung, dễ sửa lẫn source quantity/net/tax/locator hoặc protected route sau xuất.

**Bổ sung:** ưu tiên view/join từ route version làm projection; hoặc cache cột dich có transition hẹp riêng, chứng minh derived-only, guard cả OLD/NEW parent/state, không nằm trong immutable source semantic payload. Source fields/ID/hash không đổi khi route đổi; approval/export pin route cụ thể. Sau đã bảo vệ chỉ correction/revision có căn cứ, không overwrite cache để đổi lịch sử.

**Ca cần có:** đổi route được phép giữ nguyên source fingerprint/PK/quantity/amount và invalidate dependent proposal; SQL sửa source cùng cache bị chặn; file/lô cũ vẫn trỏ route version cũ.

## P2 — R5. Hoàn chỉnh composite FK identity–version và REQUEST_ALIAS

**Anchors:** dòng44–45/66–68/80, M9 common mapping contract§3.

- Observation có cả hoa_don_id và phien_ban_id, nhưng “FK cùng PN tới version” chưa ràng buộc **version thuộc chính identity đó**. Cần composite unique/FK `(PN,hoa_don_id,phien_ban_id)` và trạng thái NULL-pair rõ cho candidate chưa map; tương tự source/event/component/version/route graph, không chỉ tenant cùng nhau. Ca âm identityA+versionB cùng PN phải bị DB từ chối; multiple observations cùng version đúng vẫn hợp lệ.
- REQUEST_ALIAS dùng master.anh_xa_nguon chung nhưng M9 revision2 chỉ có target doi_tac/du_an/hop_dong và CHECK COMPANY/BANK/PROJECT/LOAN. M2 cần extension cụ thể kind+typed canonical-rq target FK cùng PN, exactly-one-target, unique source identity/approved interval và retarget impact khi đã có advance/claim/refs. Không nhét rq_id vào hop_dong_id hay chỉ JSON/source_value. Control Base→Request alias đã xác nhận giữ một logical RQ; alias saiPN/khácRQ/retarget sau consumption giữ chờ, không reset capacity bằng RQ UUID mới.

## Các phần đúng và dependency cần giữ

M2 đã phân source line với posting NET, typed HD_MUA/HD_BAN với legacy INVOICE, một semantic snapshot/nhiều observations và không dùng parity legacy làm bằng chứng promoter typed. PN/composite FK, role action/V1/V2/V4, DB domain validation/fingerprint, raw intake khi thiếu ngày/khóa kỳ, sensitive mapping và M1 ownership đều được nêu đúng hướng; cần code/test chính các rule đó, không chỉ RLS đọc.

Logical nghĩa vụ xuyên versions và revision giảm/basis đổi có allocations đã được ghi rõ ở dòng83/93, nên **không lặp M9-R3 thành finding mới**. Phải dùng bản common M9 sau amendment R1–R4: đổi basis/PK/alias không reset consumption cũ. Full/partial M2_REBIND_PAYMENT dùng common receipt/locks, hủy child cũ+tạo parts/parent cần thiết nguyên tử, giữ BANK tổng30, giữ FK/audit/protected refs. Undo/rebind/revision đều kiểm period/lô; thiếu policy thì old allocation giữ và tạo task. Test rollback sau cancel trước tạo child mới, full30 và partial20→advance10+invoice20, old-parent evidence đúng target, cùng BANK tranh M9/CRM và retry/tombstone phải có positive controls thực.

No stock-value journals theo TL35§8.6 là ràng buộc đúng; KHO chỉ route/evidence/quantity, không làm giá vốn/tồn hay cân journal kho để gọi module xong. Recognition uniqueness không thay money budget; money budget không thay recognition claim. Không có nghiệm thu/runtime/test mới từ review này; root cần review/amend binding trước giao coder và bind evidence độc lập sau terminal/freeze cuối.
