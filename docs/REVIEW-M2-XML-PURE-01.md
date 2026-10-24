# M2 XML PURE01 — review final và đầu bài sửa02

19/10/2026. **FINAL_STATIC_REVIEW / CẦN SỬA R1–R2 / CHƯA NGHIỆM THU PURE.** Root actual88431 terminal0 `29af58`; đọc frozen `var/codex-dieu-phoi/m2-xml-pure01-handoff-20261019-193932-647-95dbdbea/frozen/`, không dùng interim làm final. Manifest240 SHA `59d2456e12cca6d64e583855091a06982e8949f060f3d2d54432529924422c8c`;238file nền/fixture giữ nguyên theo kiểm root. Reviewer không import/run/compile/test/SQL/HTTP hoặc sửa product; chỉ tài liệu review mới.

Đã FULL-READ reader1031lines, toàn tests và report01, đối chiếu handoff01/DTO/profile đã chốt cùng handoff02. Pins:

| Artifact | SHA256 |
|---|---|
| `nguon/hoa_don_xml.py` | `e6d65f77936b88619562011e280ef52e00d51ac8db1b1d7baa50de09d5f48b71` |
| `tests/test_hoa_don_xml.py` | `c764a445d55ee82947f0935df3cb7413530ce98937cba7462d071e5d097366d5` |
| Report01 | `6527d70e6c55c40d24abcea52394c2c68586953e255da35201826665567856a7` |
| Handoff01 / DTO01 | `0934b62c822459e65e3059363c3d8d0e76806ff375a4f51e224f9e3221deaf55` / `d68a993e3ca15354546b4c599fb6088fccfc4f308894cde594f467d7a4d05d53` |
| Repair handoff02 | `7e010c10ebbf2a8faba4f95c21c38c35ace7eaf15376de7823be8cf7ef1eadf3` |

## R1 — P2: normalized quantity vượt quy tắc CAI đã chốt

`InvoiceMeasurementFacts.ho_tro:349–353` chỉ kiểm `raw_unit == canonical_unit`, ratio1/1, encoding/profile/domain; không buộc cả hai bằng `CAI`. `_doc:680–685/921–928` vì thế nhận factTHUNG1/1 và cấp normalized10 cho nativeDVTinhTHUNG. Message `MEASUREMENT_FACTS_UNSUPPORTED` nói CAI, nhưng predicate không thực hiện giới hạn đó.

Đây là counterexample **root đã chạy**, không suy đoán: cùng native quantity10, đổi unit sangTHUNG, raw-ref tính lại đúng bytes, cung cấp factTHUNG1/1; normalized trả`10`,0issues. PositiveCAI cùng profile đạt. DTO/handoff01 chỉ hỗ trợ explicit same-CAI1/1, nên pure profile chưa đạt dù không có L11/business eligibility.

Sửa hẹp: ruleCAI explicit, unsupported unit giữ exact raw/Decimal/unit, issue/HOLD và normalizedNULL. Test thêm validCAI positive và matchingTHUNG negative; không sửa expected để mở rộng profile, không bịa conversion hoặc thêm stock engine. Existing test thiếu proof/ratio2 (`359–368`) chưa phát hiện outside-unit cùng1/1.

## R2 — P2: context mâu thuẫn vẫn cấp normalized fact

`_doc:662–679` ghi raw/profile contradiction; `682–683` vẫn chọn facts độc lập, còn `ctx_ok:686–688` chỉ gate identity/content. Dòng `921–928` không kiểm contradiction trước unit-definition/normalized output. Root actual raw-ref mismatch đã thấy identity/contentNULL nhưng normalized vẫn`10`; native bytes không bị sửa. Các test raw/profile/ZIP mismatch (`338–342`, `389–403`) hiện chỉ kiểm identity/hash/issue/native, không assert normalizedNULL.

Sửa hẹp đúng handoff02: raw-ref mismatch, profile-ref mismatch, profile-document mismatch hoặc payload nhầm document phải không cấp normalization authority từ context đó; giữ raw/hash, field states, exact Decimal/native unit và issue. ValidCAI vẫn normalized10. **Không dùng blanket `ctx_ok`/identity/content gate:** `expected_raw_ref=None` là NOT_BOUND; thiếu crosswalk/registry payload không tự vô hiệu source identity/content đã đủ; thiếu measurement proof chỉ giữ normalizedNULL. Các trạng thái thiếu/chưa bind khác mâu thuẫn explicit, không phát sinh policy tài chính mới.

## Các đường đã đọc và giới hạn bằng chứng

Strict byte API không có filesystem/env/time/UUID/DB/network I/O trong reader. Exact wrapped/no-namespace paths, unknown element/attribute/text chặn content digest; không descendant fallback/default currency/nature/STT. Duplicate scalar giữ occurrences; **mixed scalar được bảo vệ** bởi `InvoiceField.duy_nhat:236–238`, `_field:605–612`, `line_mo_ho:837` và content gate846; không ghép itertext hoặc chọn first/last thành identity hợp lệ. Decimal dùng ASCII fullmatch→Decimal, giữ21/6/NULL/zero riêng và không float/minor/round.

Identity derive từ native+configured company và string digits; content envelope/ordered lines dùng golden độc lập, không route/proof/receipt làm source content. Crosswalk so actual artifact/identity/locator/ordinal, không auto MaHang/STT. ZIP dùng ZipInfo/ordinal, so container/member refs, giữ duplicate/error members và periodUNKNOWN. Returned/context paths tạo frozen tuples/Issue snapshots; serialization trả bản sao. Trong phạm vi pure đã đọc, không thấy blocker cụ thể khác cần mở rộng sửa02. Đây không phải review DDL/recognition/capacity hoặc acceptance nguồn production.

Tests chỉ đọc DEMO fixture/source pins, in-memory ZIP, không Store/config/DB/temp-cleanup; source-text assertions về reuse/I/O không thay bằng chứng hành vi. Root thông báo actual27unitPASS0fail/error/skip và legacyXML/month-folder1PASS (`be7651`); reviewer không chạy lại. Đã đọc retained independent `result.json` SHA `13349d6d39c7d5910e1d569695609a4dbbe3a5cba288595f294ca3b8c35df090`:232fieldstates,11observations,6identities,8contents,8crosswalkrows,15quantityrows,3duplicateZIPentries, missing-context/proof và mutation controls đạt, fixture28 nguyên. Các số có overlap, không cộng thành tổng tests độc lập.

Supplemental retained `additional-profile-boundary.json` SHA `124f94a9a03486fa58ba8a249d9cb4e333717d395377978c672a60e5e14a2342` xác nhận CAIpositive, THUNGnegative chưa đạt (normalized10/0issues), raw-ref mismatch normalized10, guard và frozen240 nguyên. Vì vậy các PASS trước không đóng R1–R2 hoặc cho phép chuyển sang source bridge/L11 trước sửa và verification riêng.

**Handoff02 CLOSED về kỹ thuật/phạm vi:** đúng hai sửa trên,2existing code/test+newreport02; giữ27tests/goldens/legacy/protected refs, bổ sung positives và explicit contradiction negatives, coder CODE_ONLY/UNRUN. Sau terminal02 cần full finaldiff rebind và root chạy lại selected pure/independent controls; không coi review hoặc terminal là PASS. M9 method-only/no calls/resume; noDelete giữ tuyệt đối.
