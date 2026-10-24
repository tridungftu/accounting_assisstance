# M5 — contract fingerprint và history cho reader thuần

**2026-10-19 · PREPARE_ONLY / ROOT_REVIEW_REQUIRED / NOT_RUN / NOT_DISPATCHED.** Root chọn hướng kỹ thuật dưới đây để chuẩn bị sau V13; chưa release coder hoặc chốt DTO/digest thực. Chỉ tạo tài liệu này; không sửa handoff/corpus/package/product, không chạy/import sản phẩm/test/SQL/Google/source app và không tiếp tục M9. Không tính hay bind semantic/request digest trong lượt này.

Căn cứ `GIAO-CODE-M5-READER-33.md` SHA `24be8a2049e67c186b9943e80e1620b4f46fdc60b9668311c2a5ace281c5c254`; binding M5 SHA `7de60be44fe301d043a70aa2b582572f5d96d40f9444238f10a2a50acd4bcc5c`; private native manifest SHA `7ff31e80afe18cee6b19b9adb02978c1ef9d05714a7922e02a35ac3fdef7558f`. Đây là technical contract bổ sung; không thay scope toàn M5/L11 hoặc TL35§8.6.

## 1. Ba fingerprint và quy tắc nền

`raw_sha256 = sha256(content_bytes)` của đúng native bytes `{phieu,lines}`; khác outer-fixture SHA. Giữ bytes/token kinds/quantity text nguyên; không serialize lại native qua Decimal audit tags. BOM/whitespace có thể đổi raw SHA nhưng không tự đổi nghĩa business. `doc_json_chinh_xac` dùng để đọc strict UTF-8/BOM/Decimal và chặn khóa lặp/NaN/Infinity; `canonical_json` và `sha256` dùng đúng primitives hiện hành.

Ký hiệu `N(x)=chuan_hoa_so(x)` **chỉ trên envelope đã qua shape validation**, sau đó `H(x)=sha256(canonical_json(N(x)).encode('utf-8'))`. N giữ text nguyên, int nguyên; Decimal nguyên→int, Decimal có phần lẻ→audit-tag theo R_REV. Đây là encoding fingerprint, không sửa native, không phục hồi source Number precision và không cấp measurement proof. JSON numeric1 và numeric1.0 có thể cùng N; raw/token audit vẫn phân biệt. Quantity text `"1"`/`"1.0"` không bị trim/parse thành Number.

Version tags cố định bên dưới là contract của encoding, không phải software build/profile hash thay mỗi deploy. Đổi thuật toán/whitelist/version cần root review và compatibility plan, không tự tạo source revision chỉ vì code mới. Unknown proof/precision/UOM/mapping không được tự điền0/1/date/PN hoặc PROVEN.

## 2. Semantic envelope `kho10-content/v1`

Trước H: raw object đúng `{phieu:object,lines:array}`; không duplicate JSON key/native ID_Dong, orphan SoPhieu hoặc ambiguous/duplicate referenced master keys. Native identifiers là exact text_id, không casefold/strip/fuzzy. Object/array/boolean không hợp lệ tại scalar quantity; raw quantity chỉ text/JSON Number/null theo profile. Validate field types, finite decimal syntax và declared graph; không nhận object giả `$so_thap_phan` làm quantity rồi hash đụng audit encoding. Master graph sai không last-wins.

Envelope có **đúng năm keys**:

```text
{
  "contract": "kho10-content/v1",
  "logical_source": {"source_instance": <trusted instance>, "SoPhieu": <native SoPhieu>},
  "native_header": <copy các native header keys hiện diện trong whitelist>,
  "ordered_native_lines": [<copy native line whitelist theo đúng source order>],
  "related_master_facts": {"DM_HangHoa": [...], "DM_Kho": [...], "DM_DoiTac": [...]}
}
```

Header whitelist: `SoPhieu,LoaiPhieu,NgayChungTu,MaKho,MaDoiTac,DienGiai,TrangThai,NguoiLap,NguoiDuyet,ThoiDiemDuyet,SoPhieu_Goc`. Line whitelist: `ID_Dong,SoPhieu,MaHang,SoLuong,GhiChu`. Copy nguyên giá trị/kiểu; missing key khác explicit null/empty, không tạo default. Unknown/extra native key giữ raw+issue và không silently bỏ khỏi semantic contract; cần profile review trước khi semantic-ready. Line array giữ thứ tự; STT không thành identity.

Master facts lấy từ trusted snapshot context, chỉ các key được header/lines tham chiếu: hàng theo MaHang, kho theo MaKho, đối tác theo MaDoiTac khi có. Whitelist lần lượt `(MaHang,DVT_Goc,DVT_QuyDoi)`, `(MaKho,TrangThai)`, `(MaDoiTac,MaDoiTuong_KT)`; mỗi section sort tăng theo exact native key, không theo label/locator. Duplicate referenced key kể cả hai row giống nhau→issue/HOLD, semantic=NULL. Missing required referenced row hoặc unresolved master graph→raw+issue, semantic=NULL; không tự làm row rỗng. UOM hiện diện nhưng rỗng là source fact unknown, không default unit/factor.

`semantic_digest=H(envelope)` chỉ khi semantic-ready. Không có PN đích, mapping revision, receipt/capture ID/time, server_known_at, source observation order, history, approval/proof refs, master row UUID/raw SHA hoặc code/build hash trong envelope. Native actor/approval-time/status **nguồn** vẫn là native business facts trong header, không phải core approval. DVT_QuyDoi chỉ được hash như observed fact, không áp hệ số.

K01/K03/K05 có cùng identity/native/master facts→cùng semantic; K02 khác instance→khác logical identity/digest; K04 đổi status→khác; K09/K10 đổi UOM facts→khác. Reorder lines→khác semantic nhưng logical line IDs giữ nguyên. Đổi master-row order/JSON whitespace/BOM mà facts không đổi→semantic không đổi. Nội dung/proof/mapping mới không tạo quantity pool mới; logical pool và consumption xuyên revision theo binding M5.

Malformed/ambiguous graph hoặc không đạt declared semantic validation: `semantic_digest=NULL`, không dựng digest từ phần graph hợp lệ/row cuối. Result vẫn giữ raw SHA/native values/locators/Issue[]; không request replay/eligibility tự động. Missing/invalid ngày giữ candidate, không ngày giả/business projection; validity gate chưa đạt thì semantic=NULL. Quantity ngoài miền/scale38,12 không có normalized output/rounding; việc tính H không biến raw fact thành capacity.

## 3. Request envelope `kho10-request/v1`

Chỉ tính khi semantic đã bound và toàn request refs/scope/authority cần thiết đã resolve; thiếu→`request_digest=NULL` + issue/PENDING. Request envelope có đúng keys dưới đây; scalar/tuple refs phải canonical, immutable và thuộc cùng logical source/scope, không browser tự chứng nhận.

```text
{
  "contract": "kho10-request/v1",
  "logical_source": <đúng tuple semantic.logical_source>,
  "native_raw_sha256": <actual bytes SHA>, "semantic_digest": <content SHA>,
  "source_profile_ref": <context.profile_ref>,
  "source_scope": {"source_instance": ..., "SoPhieu": ..., "MaKho": ..., "sections": [...], "coverage": ...},
  "capture_consistency": {"claim": ..., "reported_errors": [...]},
  "mapping_revision": {"reference_id": ..., "version": ..., "source_instance": ..., "MaKho": ..., "phap_nhan": ...},
  "master_snapshot": {"reference_id": ..., "raw_subtree_sha256": ...},
  "measurement_refs": {"profile_ref": ..., "native_encoding_kind": ..., "conversion_kind": ..., "unit_definition_ref": ...,
      "approved_conversion_proof_ref": ..., "prior_unit_definition_ref": ..., "master_revision_ref": ...,
      "ratio_numerator_text": ..., "ratio_denominator_text": ...}
}
```

`request_digest=H(request_envelope)`. Projection: source_profile_ref←context.profile_ref; source_scope.source_instance←context.scope.source_instance_id, các scope fields còn lại copy từ context.scope và phải khớp logical/header. capture_consistency.claim←context.capture_consistency_claim; reported_errors←context.reported_capture_errors hoặc[]; mapping_revision/master_snapshot lấy đúng named fields trong context cùng tên; measurement_refs lấy named fields của context.quantity_evidence, gồm conversion_kind←context.quantity_evidence.conversion_kind. Scope.sections là set whitelist được sort; reported_errors là codes sort/unique, không exception message.

Envelope request luôn có đủ keys đã liệt kê: optional measurement field vắng→explicit NULL; ratio chỉ copy từ explicit pinned evidence, không default1 hoặc suy từ DVT_QuyDoi. Required source profile/scope/mapping/master ref thiếu→request=NULL, không default. Proof/basis/profile refs phải resolve đúng immutable revision; resolved facts không khớp native unit/profile/declared conversion_kind→issue/HOLD, không tin label hay kind do caller tự gán. Quy tắc DTO projection/NULL này phải được root review/test độc lập trước H; không đổi native values.

Nhánh `conversion_kind=SAME_VERIFIED_UNIT_ONLY` chỉ đủ căn cứ khi unit definitions/context thực sự cùng verified identity và có explicit pinned ratio evidence1/1; `approved_conversion_proof_ref=NULL` là **N/A cho phép kiểm same-unit**, không mặc định unknown chỉ vì không cần đổi đơn vị. K01 exact-text/same-unit là positive **synthetic DEMO explicit**, không phải bằng chứng producer thật; các guard precision/history/scope khác vẫn bắt buộc. Không tự thêm ratio1/1 khi thiếu evidence.

Nhánh khác đơn vị cần approved immutable conversion proof đúng from/to units/context/ratio; proof NULL hoặc chưa xác minh→UNPROVEN/HOLD. `UNKNOWN`/`NO_NEW_PROOF` không đủ để cho phép đổi đơn vị; không đổi kind hoặc lấy factor12 để né proof. Same-unit label nhưng resolved unit/proof/profile facts mâu thuẫn cũng HOLD, không được dùng nhánh N/A làm bypass.

Loại `receipt_id`, capture ID/ref/time, known/received/as-of hệ thống, history summary, fixture_id/order/after_fixture và expected/oracle khỏi request. Source business date/approval-time đã nằm trong semantic nên vẫn ảnh hưởng request. Same facts/raw/context nhưng receipt/capture mới→request có thể giống; raw/BOM đổi→request đổi dù semantic giống. Mapping/master/proof revision đổi→request đổi, không mutate semantic source hoặc di chuyển PN/old links.

## 4. DTO/history và phân loại receipt tách biệt

`KhoReadContext`, `KhoReadResult`, `KhoHistorySummary` cần concrete frozen/deep-immutable DTO trước code: names/path projections từ native package sang các envelope trên; digest version/64hex validation; missing vs NULL; field whitelist và error codes. Không dùng mutable dict history toàn cục hoặc boolean trusted từ raw. Reader trả candidate/raw SHA/semantic/request nullable/issues/native quantity kind/text; không tự promote/approve/chọn current.

Summary đúng exact logical identity+scope/profile; `None` khác explicit empty. Minimum: `receipts_seen[(receipt_id,request_digest,content_digest)]`, seen content digests, accepted `(content_digest,observation_ref,source_state)` nullable, old native-line/unit/basis/proof refs. Summary mismatch hoặc digest chưa bound→HOLD/UNKNOWN; không đọc fixture labels để đoán. Chưa có history→`HISTORY_UNAVAILABLE`/PENDING, không tự chấp nhận raw `Đã duyệt`.

Order logic phải giữ đồng thời issues: receipt đã thấy + request/content khớp→REPLAY; cùng receipt nhưng digest khác→CONFLICT/HOLD, không replay hoặc sửa old receipt; receipt mới + accepted content giống→fresh same-content observation. Current source đảo→REVERSED/ineligible. AcceptedB=DA_DAO+seenA,B rồi A cũ xuất hiện→REAPPEARANCE_HOLD, acceptedB không bị A thắng, không reopen/free old links. Partial/UOM-continuity/precision issues không bị replay/hash-match che mất. Classifier chỉ trả reasons, không accepted pointer/reservation hoặc storage machine mới.

## 5. Gate còn mở

Các digest trong package `contexts/*`, `history/*` vẫn **NOT_BOUND**; symbolic content/request refs không phải hashes thực. Root phải review tài liệu này, chốt DTO/canonical projection/NULL rules/codes, rồi seed/pin digest bindings bằng quy trình DEMO độc lập trong bản mới trước tests/dispatch; không lấy output reader làm expected. K04/K05/K09 matched6 chỉ future setup, chưa có link DB thật.

Actual source profile/history/deployment, PN mapping và precision/conversion proof vẫn NOT_VERIFIED. M5_READER_PURE_VERIFIED chưa đạt; toàn M5/L11/API/DB/RLS/period/file/UI/restart vẫn PENDING. Không calculator, valuation/stock journal/duplicate recognition, không sửa source #10/M9 và không đổi release FALSE của mọi package hiện có.
