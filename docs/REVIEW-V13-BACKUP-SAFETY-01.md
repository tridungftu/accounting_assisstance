# Review độc lập V13 legacy backup — bản đóng băng 01

Ngày 2026-10-19. **STATIC ONLY; hai P1 cần sửa trước nghiệm thu.** Không import sản phẩm, chạy test/SQL/DB/HTTP/process, đọc dữ liệu thật/secret, sửa sản phẩm hoặc xóa file. Không tiếp tục M9; scope chỉ legacy V12/V13 backup. Các counterexample dưới đây suy ra từ source, **chưa phải kết quả chạy**.

## 1. Đầu vào và ranh giới bằng chứng

- Frozen146: `var/codex-dieu-phoi/kiem-chung-20261018-101441/v13-legacy-backup01-handoff-20261019-122107-919/frozen`; manifest `source-hashes.json` SHA256 `da3f41f317efebd3d00246b9ec845b2ff612743c8176f7f4c81fc3256fd75e72` (146 entries).
- Đã đọc toàn `an_toan_sao_chep.py` (204 dòng), `sao_chep_bang.py` (260 dòng), các đoạn constructor/admission/migration/preflight trong `ket_noi.py`, DDL gốc và translator cần cho hai finding. Năm source dưới đây khớp cả `sha256` và `frozen_sha256` trong manifest; kiểm hash lại sau review.

| Source, dưới `src/kho_tri_thuc/ha_tang/` | SHA256 frozen |
|---|---|
| `an_toan_sao_chep.py` | `c72204c8cde2bf6ad4620fec3837a38900a16627db00114508a3971eaa7df09d` |
| `sao_chep_bang.py` | `e68cf5b027f4d4c8d6a9442d44ca68f5cf935a032fc684cc10586ab476c2db69` |
| `ket_noi.py` | `7793cb316087e445fe3d3d80541971b8b41cc2938fbb3069311c1ce36f45b027` |
| `database.py` | `0e7db1d4ac499dcd620a7a23d3e08b91efd42a5cbeb9529047db5b28bf886c57` |
| `dich_sqlite_pg.py` | `c8446c7a9d45dba9856e5ba9280063577956e058f699f247d9438692070be386` |

So với baseline copy `cf39c0470635106647992c478fdf03a1ebe3991dacf3697b064070e6d94ef130`, bản mới đã gom SQLite→PG thành một transaction, thêm guard toàn bảng và khóa writer thật. Không dùng self-report hay test mới chưa chạy làm bằng chứng PASS; lỗi khởi động Git Bash 66 không chứng minh test sản phẩm thành công/thất bại.

## 2. R1 / P1 — PG “mới tương thích” chưa kiểm physical schema/namespace đầy đủ

**Điểm gọi:** `an_toan_sao_chep.py:93–101,108–145`; `sao_chep_bang.py:95–104,108–114`; constructor `ket_noi.py:216–224,234–238`; restore preflight `ket_noi.py:470–503`.

`phan_loai_pg` chỉ kiểm tên bảng, history version/checksum, tên cột và `rowid.is_identity == YES`. Không kiểm type/nullability/default/identity generation, PK/FK/UNIQUE/CHECK/index/trigger, physical shape của `schema_migrations`, hay đầy đủ namespace objects. Lịch sử checksum đúng chỉ chứng minh chuỗi ghi nhận migration, không chứng minh schema hiện tại còn đúng.

**Counterexample 1 — mất số tiền:** kho PG mới đúng seed/history, giữ nguyên tên mọi cột nhưng đổi `documents.amount_minor` thành `double precision`. Đây đúng là cột tiền tại `database.py:32–37` (dòng 35), được translator chuyển `INTEGER→bigint` tại `dich_sqlite_pg.py:171–178`; không nhầm với `document_lines.amount_minor`. Classifier vẫn trả `MOI_KHOP`; `_cot_pg` cũng chỉ trả tên. COPY giá trị int64 `9007199254740993` có thể ghi thành `9007199254740992`; đếm nguồn/đích vẫn bằng nhau, helper không gọi đối chiếu nội dung trước COMMIT. Guard vì vậy chưa bảo đảm yêu cầu không mất số nguyên trên 15 chữ số.

**Counterexample 2 — history/trigger drift:** `schema_migrations` chuẩn là `(version bigint PRIMARY KEY, checksum text NOT NULL, applied_at text NOT NULL)` (`ket_noi.py:375`). Bảng giả chỉ có `version/checksum` với đủ các giá trị hiện hành vẫn qua phép đọc tại utility109; shape không nằm trong vòng kiểm cột134–142. Bỏ PK rồi lặp cùng version/checksum cũng bị dict collapse. Tương tự, extra BEFORE INSERT trigger sửa tiền trên `documents` hoặc mất required FK/index/trigger không được phát hiện; COPY có thể đổi giá trị/thiếu ràng buộc mà count vẫn giữ nguyên.

**Counterexample 3 — namespace không trống trước autoload:** schema chỉ chứa một function `json_extract(text,text)` chưa thuộc ứng dụng, không có relation trong tập `r,p,v,m,f` và không có sequence lạ, được trả `TRONG_HOAN_TOAN` tại100–101. Constructor cho phép trạng thái này trước `_migrate`; `_ap_migration` chạy BOOT_STRAP (`ket_noi.py:375–377`) gồm `CREATE OR REPLACE FUNCTION json_extract` (`dich_sqlite_pg.py:209–216`), có thể thay function đã có. Schema chỉ có type/operator cũng bị suy là trống; restore preflight dùng cùng classifier có thể chấp nhận/publish đích đó. Đây là lỗ admission trước effects, không phải yêu cầu mở rộng sang K2.

**Sửa có giới hạn:** giữ một contract legacy dùng chung, kiểm catalog PG theo DDL legacy đã dịch: toàn bộ column type/nullability/default/identity mode và required constraints/indexes/triggers; kiểm riêng shape/history uniqueness của `schema_migrations`; inventory expected namespace objects và tự động phụ thuộc của chúng, không suy “hoàn toàn trống” chỉ từ một phần `pg_class`. Có thể dùng đường tạo mới có ownership đáng tin cậy nếu chứng minh nguyên tử namespace thật sự chưa tồn tại/trống và đúng generated contract; không dùng cờ từ caller hoặc checksum history thay physical proof. Reject old/partial/unknown/drift **trước autoload migration/bootstrap và trước DELETE seed/COPY**; không tự sửa schema lạ trong đường copy.

**Control cần có khi root cho phép chạy:** positive absent/namespace thật sự trống được tạo có thẩm quyền và fresh đúng contract; negative float-money, thiếu FK/trigger, extra mutating trigger, thiếu `applied_at`/PK/duplicate history và function/type/operator-only namespace. Mỗi negative phải có baseline không rỗng phù hợp, exact mã từ chối và before/after schema/objects/history/data/sequence bằng nhau; function cùng signature phải giữ nguyên. Positive int64/0/NULL phải đối chiếu typed cell, không chỉ count. Native normal upgrade vẫn giữ behavior cũ ngoài autoload/restore admission.

## 3. R2 / P1 — lỗi muộn khi đặt sequence để lại đích đổi sau rollback

**Điểm gọi:** `sao_chep_bang.py:121–136`. Đã chuyển kiểm FK lên trước `setval`, nhưng các `setval` liên tiếp vẫn không rollback cùng data transaction. Lỗi của một sequence phía sau không hoàn tác trạng thái sequence đã đặt phía trước.

**Counterexample cụ thể:** nguồn SQLite hiện hành, hợp lệ về FK; `documents.id` vẫn TEXT hợp lệ, chỉ hidden `documents.rowid = 9223372036854775807`. COPY vào rowid bigint chấp nhận giá trị này. Sau FK check, các sequence của các bảng đứng trước `documents` đã được đặt; phép `max(documents.rowid)+1` tại124 overflow bigint. Transaction rollback phần seed/COPY/marker nhưng các sequence trước đó có thể còn giá trị mới. Lỗi quyền ở một sequence về sau cũng tạo cùng dạng partial effect. Không cần nguồn sai checksum hay schema đích drift để kích hoạt lỗi này.

**Sửa có giới hạn:** lập và kiểm toàn bộ sequence plan trước thay đổi sequence đầu tiên: đúng ownership/identity targets, giá trị kế tiếp không overflow/exhaustion/out-of-range, quyền cần thiết của toàn bộ sequence và chế độ `is_called`. Sau đó dùng cơ chế cập nhật sequence có rollback thực sự, hoặc phương án bảo toàn/khôi phục old state được chứng minh cho mọi lỗi muộn; chỉ preflight không đủ bảo đảm khi lỗi sau preflight/COMMIT vẫn xảy ra. Không để cleanup/compensation thất bại bị nuốt rồi báo đích nguyên trạng. Không đổi identity mode hoặc xóa dữ liệu để né lỗi.

**Control cần có:** positive copy đúng và subsequent generated identity không trùng; negative rowid BIGINT_MAX và fault/permission ở sequence nằm sau ít nhất một sequence đã có khả năng đổi. Snapshot độc lập toàn data/schema/history/identity/sequence gồm `last_value/is_called` trước/sau; phải từ chối trước irreversible effects hoặc rollback mọi thay đổi. Không dùng assertion chỉ kiểm data, count hay sequence cuối.

## 4. Những phần source mới đã đáp ứng ở mức tĩnh và giới hạn còn lại

- SQLite→PG: từ chối transaction đích do caller sở hữu trước copy84–85; tự mở/đóng read transaction nguồn nếu cần89–91,137–139; một PG transaction94; khóa `mo-kho`, legacy writer `hashtext(schema)` rồi EXCLUSIVE toàn bảng đang có theo thứ tự64–74; guard96 trước thay seed98–99/COPY. Khóa bảng này có thể chặn raw DML, khác advisory lock chỉ có tác dụng với caller tuân thủ. Chưa chạy race observer/barrier nên không ghi race PASS.
- PG→SQLite: từ chối transaction caller217–220; BEGIN IMMEDIATE226 trước guard228; chỉ thay seed đã kiểm; giữ `foreign_keys` mode, dùng transaction defer229; nguồn REPEATABLE READ READ ONLY230; foreign_key_check249–251 trước commit; rollback owned transaction khi lỗi253–259. Utility SQLite so toàn bộ `sqlite_master` object contract178–179; finding R1 nhắm PG classifier, không suy hai phía đều chỉ kiểm tên.
- Constructor autoload đã đưa admission trước `_migrate` và mở SQLite source `mode=ro` (`ket_noi.py:218–247`); guard lại trong transaction copy. Điều này đóng đường nâng schema cũ trước admission về cấu trúc, nhưng độ đúng admission còn phụ thuộc R1. Đường mở thường không autoload không bị áp guard mới.
- Bằng chứng này chỉ là source review. Chưa có PASS mới cho helper hai chiều, đủ 49 bảng nonempty, raw-writer races, lỗi muộn, ordinary role/permission, CLI/GUI, restore lifecycle hoặc toàn V13/K2. Root cần sửa R1/R2 và chuẩn bị DEMO seed an toàn trước vòng thực thi độc lập; không dựa vào setup `Store.ingest` nếu đụng guard unlink. Không mở rộng hoặc tiếp tục nghiệp vụ M9.
