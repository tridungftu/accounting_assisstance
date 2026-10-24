# Review độc lập candidate A5 V13 — vòng 01

19/10/2026. **STATIC_ONLY / ONE_SCOPE_CLARIFICATION / NO_RUNTIME / NOT_ACCEPTANCE.** Đã đọc toàn `V13-GIAO-SUA-A5-VA-PHU-SONG-33.md` SHA256 **`7489b0f720a6ddfb24f0aad02f82a6680d1a7b8c6243229a01fd94ddfd6890dd`**, toàn converter frozen và các đoạn DDL/copy/SQLite liên quan. Không đọc source product M9 live/interim, DB, secrets, row thật hoặc source app; không import/tests/SQL/HTTP/host/process/delete, không sửa product. Yêu cầu mới của Anh dừng M9 được giữ: review này chỉ chuẩn bị A5 độc lập, không cho phép tiếp tục coding M9.

## 1. Source và phạm vi được đối chiếu

Frozen CRM06 `var/codex-dieu-phoi/kiem-chung-20261018-101441/crm06-handoff-20261019-095149-416/frozen/`, manifest125files SHA `c828d1fff9593a0dce6d47e079df8adf76a4609cb936e2f1a627cf1a9948dd08`. Tôi hash các file sau; không tuyên bố đã tính lại toàn125bytes.

| Source / tài liệu | SHA256 |
|---|---|
| `tools/chuyen_sqlite_sang_pg.py` (C), đọc toàn | `97c577768014e6139a2270d02551f5e1863b686c4b103581bfea2e411532a19c` |
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` (P), đoạn liên quan | `31f25277b5e08a0f54843191bce2b3e54126dc6770ad02ece310c8265fcac1e5` |
| `database.py`, SQLite tables/identity | `0e7db1d4ac499dcd620a7a23d3e08b91efd42a5cbeb9529047db5b28bf886c57` |
| `feature_migrations.py`, table/cardinality inventory | `04737a323e286ca3507011130b069e3857a7d1dfccf3395a9b6e989ee6dc05b4` |
| `sao_chep_bang.py`, table extraction/hash-marker đoạn liên quan | `cf39c0470635106647992c478fdf03a1ebe3991dacf3697b064070e6d94ef130` |
| `docs/KIEM-CHUNG-WINDOWS-V13.md`, đọc toàn | `cab7d6215c0598f35d6b85896499113d4fe77d6ae4a78db97449806c3aa2e162` |
| `docs/REVIEW-CRM-M1-03.md`, đọc toàn | `2d8b30eab1cfbe7df1e45ce0dee008ae8720747be247019a9b293e1aa3f84180` |

Literal read-only inventory (regex trên văn bản, không import/migrate) xác nhận **42 distinct CREATE TABLE nghiệp vụ K2**, **49 distinct application CREATE TABLE SQLite** trong database+feature migrations. Converter C ghi **19 target tables** như bảng candidate. Đây là inventory tĩnh, không là actual catalog/runtime coverage; schema metadata và final source additions vẫn phải rebase riêng.

## 2. R1 — P1: plain supersedes composite FK vượt phạm vi converted edges

**Neo:** candidate §4 line53 và §6 line121; P:607–624; tài liệu căn cứ `docs/can-cu-33/38-schema-lop-du-lieu.md:12,68`.

Candidate nói DDL dành cho **converted tenant rows** và không đổi nghĩa native/global tri thức, nhưng đề nghị một FK không có predicate:

`(supersedes_id, phap_nhan_id) → kho.tri_thuc(id, phap_nhan_id)`.

FK này áp dụng cho **mọi** local child có PN nonNULL, gồm native K3 rows không được converter tạo. `MATCH SIMPLE` chỉ bỏ kiểm khi một cột **ở child** NULL; nó không cho local child `(parentUUID, PN_A)` tham chiếu parent global `(parentUUID, NULL)`.

**Counterexample cấu trúc:** một native local row PN_A đang tham chiếu native global predecessor. UUID FK frozen ở P:621 chấp nhận cấu trúc đó; plain FK mới từ chối/không validate dù cạnh này không thuộc source projection A5. Chưa có accepted K3 rule trong đầu bài chứng minh native local→global phải bị cấm. Vì vậy không khẳng định cạnh đó đúng nghiệp vụ, nhưng cũng không được lấy case cross-tenant converted A2→B1 để tự quyết định thay native/global semantics. Giữ global rows trong inventory không giải quyết thay đổi constraint này.

Author candidate đã xác nhận ý định chỉ khóa converted tenant edge, chưa có K3 contract đã chốt để blanket-restrict native local→global. Đây là clarification cần khép trước handoff code, không phải lỗi runtime được tái hiện.

**Amend tối thiểu:** chọn một phạm vi có thể thực thi: guard conditional theo **trusted typed converted provenance/source ownership** cho converted edges, với discriminator không thể bị caller đổi/để NULL để lách; hoặc root đối chiếu riêng accepted K3 semantics rồi mới cho phép guard áp toàn native rows. Không dùng lời khẳng định “global semantics unchanged” thay physical predicate. Existing native/global edges chưa phân loại phải giữ nguyên/block theo đúng phần chưa được phê duyệt, không xóa/NULL/reparent/retag để validate.

**Controls đúng phạm vi:** converted A2→A1 cùng source tenant positive; A2→B1 cùng `_sqlite_id` phải verifier mismatch và final DB rejection riêng. Native global→global và native local→global/local→local có baseline/provenance tách riêng; case chưa có business contract giữ NOT_VERIFIED hoặc giữ nguyên, không gộp vào quyền blanket migration. Sau chọn guard, chứng minh caller không giả converted/native discriminator để bỏ tenant check.

## 3. Các phần contract đã đúng, nên giữ

- **A5-L:** C:319–332 thực có global fallback `m+1` và upsert theo STT; C:602–606/739–741 wildcard bỏ actual STT phi số. Candidate pin exact text identity, per-document injective ordinal, numeric alias/overflow holding, đọc actual target STT, independent vectors và giữ PK là hướng đúng. Không cần biến STT thành thứ tự nghiệp vụ không có căn cứ.
- **Hai project FK:** P:221/274 chỉ UUID FK; parent composite unique đã có. Tagged actual parent PN/code, không same-PN JOIN che wrong parent, hai detector/constraint controls riêng và NULL legitimate đều phù hợp. Không thấy contradiction với native project owner scope vốn nonNULL.
- **Supersedes verifier:** C:686/715/757 thật chỉ so predecessor source ID. Bổ sung actual predecessor tenant/source identity và unresolved holding là đúng; R1 chỉ giới hạn phạm vi physical guard.
- **Coverage19:** `_dem_dich` có19table diagnostics; `_doi_chieu` có14rows/13distinct targets; actual content hashes chỉ4tables. Candidate thêm15contracts, source subset/shared-surplus preservation, MST grouping, derived proposal/work/bank/account cardinalities, exact source audit namespace và không `all([])` PASS đều đúng yêu cầu A5. Source quick_items unique `(run_id,document_id)` không phải one-row-per-document; registry phải giữ rule version/cardinality và unsupported-shape holding như candidate đã yêu cầu, không làm phẳng thành một proposal rồi gọi đủ coverage.
- **Preservation/oracle:** global ACCOUNT/EXPENSE/TTCP chỉ source-code subset; reused approved global partner lấy independently pinned baseline thay ép source name overwrite là hợp lý. FK/identity/typed content cần so thật, không coi stored JSON/hash là oracle. Shared surplus full rows/PK/FKs trước=sau, protected change holding và không DELETE/reinsert proposal lines khép đúng lỗ source C:402–407.
- **Migration/atomicity:** append sau authoritative final baseline, exact old checksum/history, nonempty retained upgrade/replay, không disable mới để làm pass; phân biệt preflight rejection với midtransaction rollback và owner projection với ordinary app quyền là đúng. A5 verifier synthetic/retained pre-fix scope để tách detector khỏi constraint denial cũng phù hợp.
- **Inventories/limits:** 19 converter targets khác42K2business và49option-C tables; legacy marker/history ngoại lệ hẹp không áp full-K2. Không dùng CRM-M1-03 nguồn COUNTERPARTY/PROJECT0 hoặc A5 xanh để đóng full converter/backtest/V13/GUI. Không thấy yêu cầu chuyển kho thật, mở V14, policy mới hoặc xóa dữ liệu.

## 4. Kết luận

Khép R1 về phạm vi supersedes guard rồi root pin bản candidate amended; chưa có lý do phải mở lại kiến trúc/kế toán hoặc tạo engine mới. Mọi case A5 vẫn **NOT_RUN**, chưa có converter/migration/atomicity/restore acceptance mới. Khi được giao coding A5 sau này phải chọn authoritative source/frozen baseline riêng; không tự tiếp tục M9 đang được Anh yêu cầu dừng, không dùng snapshot cũ hoặc receipt lịch sử làm runtime release.
