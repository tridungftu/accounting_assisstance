# Review độc lập handoff M5 reader thuần — 01

**2026-10-19 · STATIC ONLY · NOT_RUN.** Phạm vi hai file reader/test mới và fixture DEMO phù hợp; không phát hiện yêu cầu xây lại kho, calculator hoặc valuation/331. Có **hai P2 cần khóa contract để tiêu chí extraction-classification10case kiểm được độc lập**. Không phải chấp nhận runtime hay lệnh dispatch M5. Không đọc source app/Google/live config/secret; không import/chạy sản phẩm/test/SQL/HTTP/process, sửa input/source hoặc xóa file. M9 giữ STOP/read-method-only.

## Đầu vào và kiểm tĩnh

| Tài liệu/corpus | SHA256 |
|---|---|
| `GIAO-CODE-M5-READER-33.md` | `13369247a390651b0b3fc7df54d37982bb63e0545695004f74b5348c5a067e04` |
| `TAI-SU-DUNG-PHAN-MEM-KHO-10.md` | `92dfe44947baad6cc2d0f34bb27c2a8d5f21949cf33ffc9bd91a8dbe9c1621c4` |
| `BINDING-M5-CORE-SAU-CRM03.md` | `7de60be44fe301d043a70aa2b582572f5d96d40f9444238f10a2a50acd4bcc5c` |
| Corpus `m5-source-inputs-20261019/manifest.json` | `0dce3a08bedfa96b31bdc75859e03caaaec97972b29d239ad247ef5d1d73a29a` |
| Oracle `expected-casefacts.json` | `8e260e2c2dd979c87b8f614ef084dd0e83d8c336aba5fcc4590602daff26aabb` |

Đã đọc toàn handoff/reuse, binding và10 input JSON + README/oracle; kiểm12/12 file trong manifest đúng hash/bytes, JSON không khóa lặp/nonfinite token. Đây là kiểm file/cú pháp, không test sản phẩm. Các pins nguyên sau review. Đọc definitions frozen146 của R_REV/primitives/DTO/#6 chỉ để đối chiếu reuse; không import chúng. R_REV/primitives/DTO khớp pins trong handoff§1.

## R1 / P2 — chưa khóa bridge corpus wrapper → native bytes/context và nghĩa raw hash

**Anchor:** handoff27–29 định `doc_phieu_kho(content: bytes, context)` với raw chỉ `{phieu,lines}`;45 sao chép corpus vào tests;57/67 đòi raw/hash/representation bất biến. Corpus thực có outer `{fixture_id,format,fixture_context,source_detail,source_master}`; native shape nằm tại `/source_detail`, master nằm ngoài nó. Đây không phải file native của reader được nhận nguyên bytes.

**Counterexample:** đưa nguyên `K01_APPROVED_A.json` vào reader thì shape khác contract; bóc `/source_detail` bằng `doc_json_chinh_xac` rồi serialize qua `chuan_hoa_so` như đường audit R_REV lại đổi K08 `/lines/2/SoLuong` từ numeric token `2.5` thành object `{"$so_thap_phan":"2.5"}` (`review_xay_dung.py:43,48–56`). Reader có thể reject sai K08 hoặc mất phân biệt native Number/text. JSON canonicalization/serialization bất kỳ cũng không được gọi là hash bytes nguồn gốc corpus hay actual source API. Hiện chưa có quy tắc xác định raw hash nào test phải so; coder có thể tự tạo expected từ chính preprocessing của mình.

**Amend nhỏ:** root bind rõ test bridge, không thay public reader nhận cả wrapper: `source_detail` → native-only bytes theo fixture contract có pin riêng; `source_master` + whitelist `fixture_context` → typed trusted context; oracle/fixture_id/expected tuyệt đối không vào parser. Dùng native fixture bytes riêng đã root kiểm hoặc cơ chế lossless giữ nguyên JSON token kinds, không dùng normalized audit-tag output làm native payload. Ghi raw SHA là SHA chính bytes truyền vào reader, khác outer-fixture SHA; semantic digest tách fetch/receipt/fixture_id. Không tuyên bố native test serialization là export thực/byte capture của #10.

**Controls:** K01 native positive và K08 vẫn lần lượt NULL/int0/numeric2.5/numeric9007199254740992; không xuất object/tag/string thay Number, không sửa integer dự định, vẫn UNPROVEN. Test nguyên outer-wrapper bị từ chối; đổi fixture_id/receipt không đổi source content digest, đổi business field/status có đổi; raw bytes/hash trước/sau nguyên. BOM/duplicate key/NaN controls phải dùng native bytes trực tiếp, không preprocessing đã làm mất lỗi.

## R2 / P2 — history classifier optional nhưng nhãn bàn giao đòi10case classification

**Anchor:** handoff33/35 giữ identity/status rõ;39 chỉ “có thể thêm” classifier với summary/history;49–55 và67 đòi replay/ABA/continuity/extraction-classification. Binding§3 dòng57–61 phân biệt content/observation/accepted/eligible, không cho hash cũ tự thắng source đảo.

**Counterexample đã kiểm equality tĩnh:** K01, K03 và K05 có **cùng `source_detail` và `source_master`**. K03 khác receipt context để mô phỏng retry; K05 có order3/after_fixture nhưng không native transition evidence. Một lần gọi reader thuần không có history summary không thể phân biệt “A lần đầu”, “retry A” và “A cũ sau B đảo”. Nếu classifier bị bỏ vì optional, nhãn10case classification không kiểm được K03/K05; nếu phân loại bằng fixture_id/order/after_fixture hoặc chỉ raw `Đã duyệt`, kết quả là đọc đáp án fixture/auto-eligible sai. Việc không side effect chưa giải quyết thiếu đầu vào phân loại.

**Amend nhỏ:** hoặc bắt buộc một pure classifier riêng trong gói khi giữ nhãn10case extraction-classification, hoặc giới hạn acceptance rõ chỉ extraction và để history classification PENDING. Nếu chọn classifier, bind tối thiểu trusted immutable summary cùng logical `(instance,SoPhieu)`: receipt seen+request/content digest, seen content digests, accepted source state/content/observation và căn cứ continuity đã biết; summary thiếu/sai identity → issue/UNKNOWN, không suy history từ fixture metadata. Classifier chỉ trả reason/needs-review; không accepted pointer, approval, reservation hoặc máy trạng thái lưu trữ mới. Context proof DEMO không thành quyền production.

**Controls:** caller đưa summary empty đáng tin + K01 → first-observation candidate; summary đã nhận cùng receipt/digest + K03 → replay; new receipt cùng A khi acceptedA → same-content fresh observation, không lẫn retry; summary acceptedB=Đã đảo/seenA,B + K05 → REAPPEARANCE_HOLD, không eligible/reopen. Đổi summary sang instance/SoPhieu khác phải bị từ chối/giữ issue; bỏ summary không được tái tạo “B đã đảo” từ oracle. K09 dùng old unit/basis refs explicit trong summary/context, không cần DB thật cho pure classification và không tự nhân12.

## Những ranh giới đã đủ rõ và giới hạn nghiệm thu

Handoff35–37 và corpus K08 giữ NULL≠0, fraction không truncate, Number boundary UNPROVEN dù Decimal đọc token đúng; miền38,12 không được round/cast để nhận. Cùng key đảo giữ logical identity, không phiếu âm; partial không chứng minh mất/xóa dòng. K09/K10 giữ unknown UOM/continuity, không lấy DVT_QuyDoi12 làm proof. K01 positive exact text/proof là synthetic explicit, không suy current producer đã exact. Scope mapping instance+kho→PN có version, không thêm PN/UOM tự khai vào native line.

Reuse source report62–66 phân biệt tồn aggregate toàn kho, không as-of/perKho, kiểm kê chưa hoàn tất và Drive export không native-key-preserving XLSX bytes. Handoff31/41/61–67 giữ chúng là dependency gói sau, không yêu cầu pure reader giả tồn/as-of/export hay import Google. Chưa thấy mâu thuẫn cần mở scope qua source app/common core/M9 để làm hai-file reader. Toàn M5/L11/API/RLS/period/file/restart/production vẫn PENDING; tất cả reader tests hiện **NOT_RUN**, không có M5_READER_PURE_VERIFIED trong review này.
