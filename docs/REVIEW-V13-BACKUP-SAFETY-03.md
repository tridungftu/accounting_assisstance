# Review độc lập V13 backup safety — frozen03, core R1

**19/10/2026 — STATIC_ONLY / NOT_RUN. Không còn blocker R1 cụ thể trong core/copy diff đã đọc.** Source03 đóng đường bỏ actual PG rowid của02 bằng business refusal trong cùng snapshot và đổi fingerprint sang actual rowid. Đây là kết luận control flow/source, chưa phải runtime acceptance. Không import/AST/test/product/SQL/DB/CLI/host, đọc secret/source app, sửa product/private probes/framework hoặc xóa file; không làm M9. Chỉ tạo report này.

## 1. Exact candidate và nguồn đã đối chiếu

Root bàn giao terminal handle7921/exit0, frozen146 tại `var/codex-dieu-phoi/kiem-chung-20261018-101441/v13-legacy-backup03-handoff-20261019-134511-250/frozen`; manifest SHA **`08e5b5a9394d632d8c6c8e184cd5f08698decd5ee98f50c887c16b275a28ed19`**. Review này đọc full copy347 dòng và exact diff02→03, report03; đối chiếu request03 SHA `fe816d011e5d56a790d8bf48fec923fe2abca7388e5e3deb45db53c87fa327ae` và finding F4/P1 của safety02 SHA `319f89ce3763a593ad1f0a7f6f1e24f5d9b2b4ce718ef181b139448e1761c066`.

| File dưới frozen03 | SHA256 |
|---|---|
| `src/kho_tri_thuc/ha_tang/sao_chep_bang.py` | `cf0a0753ea09f4dedf0ae2ae26ba80f3bf6ac0a73cc67721c28219b81cb561c7` |
| `src/kho_tri_thuc/ha_tang/an_toan_sao_chep.py` | `d63bfd865367614d265dc07a3e86c2254923f62d592a4348eb5cbc506fef05a2` |
| `src/kho_tri_thuc/ha_tang/ket_noi.py` | `a18d02e6370dcede8a7c4506e919c1c4df5643c9ad0c03dce9f812970452341d` |
| `src/kho_tri_thuc/ha_tang/database.py` | `0e7db1d4ac499dcd620a7a23d3e08b91efd42a5cbeb9529047db5b28bf886c57` |
| `src/kho_tri_thuc/ha_tang/dich_sqlite_pg.py` | `c8446c7a9d45dba9856e5ba9280063577956e058f699f247d9438692070be386` |
| `src/kho_tri_thuc/ha_tang/feature_migrations.py` | `04737a323e286ca3507011130b069e3857a7d1dfccf3395a9b6e989ee6dc05b4` |
| `docs/BAO-CAO-V13-LEGACY-BACKUP-03.md` | `398ee0c189e67cecb7aaf80e7d8cb1050fe82de56c29b7a3a9cdcf6c7e19c070` |

Utility/connection/DDL/translator/feature migration hashes giữ nguyên02 đã đọc trước; không suy có DDL mới ràng buộc id=rowid. Old copy02 SHA `92251dda5fe263cc819ad6c204a7a1bd5ef67a053616d26e3a2e14e72d3031db`, old manifest `314fb1f10b6c61a93505680d3573c792900e4c1cc94f97e1370866b2c726adb4`.

## 2. R1: refusal toàn nhóm alias trước SQLite writes/commit

- `kiem_rowid_alias_pg:249–260` duyệt **mọi** entry của `hop_dong()["alias"]`, không chỉ audit_events hoặc fixture. Hợp đồng unchanged dựng alias từ trusted SQLite DDL/PRAGMA (`an_toan_sao_chep:59–64,81–83`). Mỗi query kiểm `rowid IS DISTINCT FROM <PK>` trên chính schema/source raw; có dòng lệch thì `DataError.code="PG_ROWID_ALIAS_LECH"`. Chỉ SELECT/count và tên bảng trong error, không sửa nguồn/identity hoặc in values.
- Actual call `sao_chep_bang:312` nằm ngay sau `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY:311`, trước seed DELETE314, data INSERT328 và SQLite COMMIT337. Các alias checks, full source reads325, nội kiểm334 và callback343 đều dùng **cùng raw connection/giao dịch PG**, không commit hoặc mở session đọc khác giữa chúng. First read của guard thiết lập snapshot được dùng tiếp; writer về sau không thay đổi tập dữ liệu đang chép.
- Negative `(id,rowid)=(100,7),(1,8)` của request không qua guard; việc bỏ actual rowid trong nhánh int_pk_alias327 chỉ còn dùng khi guard đã chứng minh actual rowid=PK cho toàn bộ nguồn biểu diễn được. Không có parameter/flag nhảy guard trong public wrapper278–289 hoặc inner292–347. Đây là closure source của counterexample02, chưa gọi là negative PASS đã chạy.
- DataError refusal không thuộc nhánh `except psycopg.Error:287`; mã business không bị thay bằng driver code. Driver/query/setup failure vẫn là failure khác, không là bằng chứng alias refusal đúng. Exact runtime code cần quan sát từ candidate03, không lấy generic exception làm PASS.

## 3. Actual fingerprint, typed cells và target preservation

`van_tay_pg:244–246` nay truyền literal actual `rowid` ở **mọi bảng**, bỏ lựa chọn PK alias của02. `_van_tay_bang:223–237` hash actual key có tag và mọi cột được chọn, ORDER BY actual rowid; `_gia_tri_chuan:207–220` giữ nguyên phân biệt int bằng digits đầy đủ/float/NULL/bytes/text. `doi_chieu_noi_dung:263–275` vẫn kiểm column set và full typed content, không hạ xuống row count hoặc thứ tự đơn thuần. `ktt_khoa_dong` là alias output của actual rowid, nên không bị row-factory của KetNoiPG giấu như cột có tên rowid.

Chiều SQLite→PG vẫn explicit-copy rowid của SQLite tại167–172; đổi fingerprint kiểm actual PG rowid phù hợp cả bảng alias vì SQLite rowid=PK. Nội kiểm184 trước sequence/COMMIT, locks/transaction/sequence plan không sửa vòng03. Marker workspace_meta vẫn chỉ exempt đúng key cũ; không thêm exception alias hoặc miễn nội dung mới.

Preexisting SQLite/caller transaction: checks298–303 giữ nguyên; BEGIN IMMEDIATE307 → target classifier309 trước DML; nonempty/old/drift target bị từ chối ở guard trước alias query. Alias refusal đi inner except338–341 rollback owned SQLite transaction; PG finally344–346 rollback source read transaction. Khi alias lệch chưa seed DELETE/INSERT; PRAGMA defer_foreign_keys là transaction-local như đường02, không sửa permanent FK-mode. Không có repair/delete old backup/target hoặc commit caller transaction trong diff.

Các call paths backup/CLI gọi cùng public helper nên refusal xảy ra trước callback/publish. Việc staging mới được giữ/báo đúng và receipt ownership là scope CLI review riêng, không tự chứng nhận ở report này.

## 4. Điều kiện còn lại trước acceptance

Không phát hiện P1/P2 mới cụ thể trong core R1 diff. Root có thể dùng kết luận này cùng review CLI/test để quyết định **release kiểm thử riêng**; report không tự cấp runtime. Source03 có cơ sở đóng F4/P1 ở control flow, nhưng **actual refusal/positive/snapshot/rollback chưa được reviewer chạy**.

Cần independent aligned-positive; divergent-source refusal đúng `PG_ROWID_ALIAS_LECH` trong same snapshot, source full49/history/all sequences và SQLite target nguyên, không publish success; actual rowid oracle riêng cho alias/non-alias và int64/NULL/0. Coder-report03 ghi unit15 PASS nhưng PG UNRUN do Bash denied; không suy unitfake/stream exit0 thành PG/full49 acceptance. Root coder-suite và independent probe là hai mức evidence khác nhau. Không nâng ordinary-role, actual child race/CLI, full DR/K2/V13/33 hoặc M9 thành đạt; R1 physical/sequence runtime từ vòng02 và R2/R3 của03 vẫn cần scope review/evidence tương ứng.
