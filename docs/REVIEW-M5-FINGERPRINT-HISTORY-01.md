# Review độc lập M5 fingerprint/history — 01

**19/10/2026 — STATIC ONLY / NOT_RUN.** Còn hai P2 cần sửa trước khi chốt contract/digest fixtures; chưa dispatch M5. Chỉ đọc tài liệu/corpus DEMO, không import/run product/tests/SQL/HTTP/process, đọc secret/source app, sửa input/M9 hoặc xóa artifact.

## Input

- `docs/M5-HOP-DONG-FINGERPRINT-VA-HISTORY-33.md` SHA256 `c8dabeac562096260f0b166a1083ee535e9220821315c52d0062dc68a61cf498` (đọc đủ 79 dòng).
- Handoff `docs/GIAO-CODE-M5-READER-33.md` SHA `24be8a2049e67c186b9943e80e1620b4f46fdc60b9668311c2a5ace281c5c254` (đọc đủ); binding M5 SHA `7de60be44fe301d043a70aa2b582572f5d96d40f9444238f10a2a50acd4bcc5c` (đối chiếu các đoạn identity/quantity/history/acceptance).
- Private native corpus `var/codex-dieu-phoi/m5-native-inputs-20261019/`: README SHA `422f11fa4eb9e2e157f2cdc7ed9c273ec8e5b2d321646cdcdce96fc06c847626`; manifest được contract pin `7ff31e80afe18cee6b19b9adb02978c1ef9d05714a7922e02a35ac3fdef7558f`. Chỉ xem manifest/README và contexts K01/K07/K09, history K05 cần thiết; không tự nhận audit mọi file hoặc bind digest thật.

## R1 / P2 — NULL conversion proof bị áp thành blanket ineligible cho same-unit positive

Contract dòng 63 nói absent `approved_conversion_proof_ref=NULL` có nghĩa unknown, không eligible. Nhưng handoff dòng 37/59 cho positive exact-text synthetic K01; binding dòng 131 yêu cầu **same verified unit positive**, tách với khác-unit thiếu proof. Context K01 dòng 72–81 có explicit exact-text profile, unit definition, `conversion_kind=SAME_VERIFIED_UNIT_ONLY`, `approved_conversion_proof_ref=null`, ratio1/1 pinned DEMO. Cùng đơn vị đã xác minh không có phép chuyển đổi cần phê duyệt.

Nếu áp câu 63 cho mọi request, K01 bị chặn chỉ vì conversion proof NULL dù các căn cứ same-unit đã đủ; đây là mâu thuẫn hợp đồng, không phải runtime product failure. Cần phân biệt **conversion not applicable cho same verified unit** với **conversion required nhưng proof missing/unknown**. NULL không tự tạo factor1/proof; same-unit cũng không tự cấp approval/eligibility khi các gate khác chưa đạt. Giữ exact precision/unit-definition/history guards.

## R2 / P2 — request bỏ conversion_kind dù đây là measurement decision input

Request `measurement_refs` dòng 55–57 và projection dòng 61 liệt kê các named fields nhưng không có `quantity_evidence.conversion_kind` (context K01 dòng 76; K09 dòng 76 là UNKNOWN). Contract chưa nói mode này phải được derive duy nhất từ immutable refs hoặc mismatch phải bị từ chối.

Counterexample tĩnh: cùng native/semantic/scope, cùng profile/unit/proof/ratio refs, chỉ đổi trusted measurement mode từ SAME_VERIFIED_UNIT_ONLY sang UNKNOWN/CONVERSION_REQUIRED. Envelope hiện không có trường đổi nên có thể cùng request digest, trong khi căn cứ measurement/issue và việc đòi conversion proof khác. Đây là thiếu binding của request; chưa phải hash collision hoặc exploit đã chạy. Việc raw/semantic giữ nguyên là đúng, nhưng request cần phản ánh quyết định measurement đã resolve.

Sửa hữu hạn: đưa **validated canonical `conversion_kind`** vào request projection và đối chiếu nó với facts của immutable profile/unit/proof refs. Reject mode/ref/ratio mâu thuẫn; không nhận boolean/string tự chứng nhận từ browser/native. Với cùng mode/facts thì capture/receipt mới vẫn không tự đổi request. Chốt DTO projection/NULL/N/A enum rồi pin bản fixture mới; không tự sửa corpus cũ hoặc lấy output reader làm expected.

## Các điểm chưa thấy blocker khác

Raw SHA tách native bytes khỏi wrapper; semantic giữ logical instance/native facts/master referenced facts, không PN/mapping/capture metadata; request mới bind raw/context/revisions; line order khác master-row order được phân biệt. Duplicate/ambiguous graph giữ NULL/issue, không last-wins. History tách missing/empty, same receipt conflict/replay, fresh observation và A→B→A HOLD; không cập nhật accepted pointer trong reader. Không phát hiện thêm mâu thuẫn cụ thể trong phạm vi đã đọc.

DTO/canonical projections/codes và các semantic/request digest vẫn **NOT_BOUND** (contract dòng 69/77); private corpus history hiện là symbolic refs, không executable digest oracle. PREPARE_ONLY/all release FALSE và giới hạn pure reader/full M5 PENDING được giữ trung thực. Hai sửa trên là dependency trước binding/dispatch, không mở schema/API/storage/framework mới hoặc tạo quyền chạy runtime.
