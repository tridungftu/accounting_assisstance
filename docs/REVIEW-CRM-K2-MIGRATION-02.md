# Review độc lập CRM-01 — schema, migration và ranh giới dữ liệu lần 02

19/10/2026, khoảng 07:19–07:23 +07. **Chưa nghiệm thu: 19 ca vi phạm SQL cũ đã được kiểm lại đạt trong phạm vi dưới đây; còn 10 criterion vi phạm thuộc hai nhóm P1 mới.** Không suy kết quả SQL thành HTTP exploit hoặc GUI đã kiểm.

## Bản bàn giao và phương pháp

Root đã xác nhận CLI Claude handle **51099** terminal `exit_code=0`, `ClaudeExit=0`, trước mọi import product/SQL. Receipt: `var/codex-dieu-phoi/kiem-chung-20261018-101441/crm02-handoff-20261019-071834-580/terminal-confirmation.json`; manifest 117 file SHA256 `5d85cd7b822c3ae09e0b88d83421309904307a905d29da4f639fc5de933a44f2`.

Ba file được bind đúng receipt, hash trước/sau toàn bộ probe không đổi:

| File | SHA256 |
|---|---|
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` | `be17668b173ecc50d6fd4557c105562b6059156889fe53e98429a4953c4bcb3d` |
| `src/kho_tri_thuc/ha_tang/postgres.py` | `ffca2c38527ade742d12c5332ff29e3c54eae77f111362c7d5f9b0453bbdf6f8` |
| `src/kho_tri_thuc/k2/crm.py` | `0cadce38ad7618de10dc0e8c067d07d25017393f88d6f65e9e08291964888d59` |

Toàn bộ là fixture DEMO độc lập, actor `MO_PHONG_`, PostgreSQL loopback `127.0.0.1:5432`; credential chỉ đọc trong process, không ghi/in. Các boundary probe đăng nhập bằng **LOGIN thực NOSUPERUSER, NOBYPASSRLS, NOINHERIT**, sau đó `SET ROLE app_web`; kiểm cả `current_user`, `session_user`, `rolsuper=false`, `rolbypassrls=false`. Không chỉ dùng superuser rồi kết luận quyền đúng. Context ID/login được đặt LOCAL mỗi transaction. Guard không xóa và `PYTHONDONTWRITEBYTECODE=1` bật; giữ 3 DB mới, 4 login role mới cùng 2 DB lịch sử đã nâng cấp; không cleanup, không sửa product.

| Lượt | PASS | FAIL ghi nguyên bản | Setup error | Diễn giải |
|---|---:|---:|---:|---|
| First schema probe | 69 | 9 | 0 | 8 vi phạm product; 1 positive control sai convention múi giờ của fixture |
| Targeted lifecycle/helper/legacy | 14 | 2 | 0 | Sửa riêng literal fixture sang UTC; control CFO đạt; thêm 2 vi phạm ở helper thứ tư |
| Targeted hai FK lịch | 7 | 0 | 0 | Có positive lịch và replacement trong chính transaction duyệt |
| Targeted FK mapping trước duyệt | 6 | 0 | 0 | Positive cùng PN; sai profile/project bị đúng FK23503 |

Không cộng các lượt thành một tỷ lệ nghiệm thu: có control lặp và hai ca quan sát cố ý xác nhận giá trị bị lộ. First result được giữ nguyên, SHA256 `fee14d309d618b9343152a11b7b17dd960e10d90eb019996130d33d221a4f02a`. Ca positive đầu dùng timestamptz không ghi timezone, khác convention UTC midnight của service; targeted dùng `2030-01-01T00:00:00+00`, KT kiểm/CFO duyệt/biên hiệu lực đều đạt. **Không tính ca fixture này là lỗi product thứ 11.**

## P1 — người nộp tự đóng hoặc mở lại hiệu lực bản đã duyệt

`pg_migrations.py:1346–1355`, nhánh `OLD.trang_thai='DA_DUYET'`, bỏ `valid_to` khỏi phép so sánh bất biến rồi `RETURN NEW` trước khi kiểm danh tính/quyền hoặc điều kiện bản thay thế.

Với login thường, actor BAN_HANG chỉ có CRM trên PN A:

1. `UPDATE master.hop_dong_phien_ban SET valid_to='2026-01-02' WHERE id=<bản đã duyệt đang mở>` trả **1 row**, không exception. Người nộp có thể làm bản đã duyệt mất hiệu lực hồi tố.
2. `UPDATE ... SET valid_to=NULL WHERE id=<bản đã duyệt đã đóng>` trả **1 row**, không exception. Người nộp có thể mở lại bản đã đóng.

Hai thao tác được rollback sau khi đo. Positive control riêng: KT kiểm vân tay, CFO duyệt phụ lục, CFO đóng đúng predecessor tại UTC midnight; trước biên trả bản cũ, tại biên trả bản mới. Vì vậy cần ràng buộc **ai được đóng, đóng về thời điểm nào, bản thay thế đã được duyệt của chính hợp đồng**, và chặn unclose tùy tiện, đồng thời giữ đường CFO hợp lệ.

## P1 — bốn SECURITY DEFINER helper đọc ngoài PN/module

Các hàm tại `pg_migrations.py:1271–1298` truy vấn bảng nghiệp vụ bằng quyền owner, không kiểm caller PN/module:

- `master.da_lien_ket(hd, khoa)`;
- `master.da_lien_ket_dong(lich)`;
- `master.phien_ban_hieu_luc(hd, ngay)`;
- `master.van_tay_phien_ban(pb)`.

Mỗi hàm đều tái hiện hai ca, tổng **8 criterion vi phạm**: actor CRM A gọi với ID fixture B, và actor A `module=[]` gọi ID A. Các SELECT đều thành công, trả giá trị khác NULL/0. Aggregate B đúng **60 VND** DEMO; A đúng **70 VND** DEMO; effective helper trả đúng ID bản B; fingerprint trả chuỗi không rỗng. SQL không báo lỗi — đây là vi phạm kiểm quyền, không phải exception/setup error.

Positive controls: cùng actor CRM A thấy đúng hợp đồng A, không thấy header B qua RLS thường; chỉ CRM không đọc được sao kê/đề xuất M1, nhưng đọc aggregate của chính hợp đồng A bằng helper trả 70 là hợp lệ. Không yêu cầu có M1 để xem mọi aggregate CRM; yêu cầu helper giữ PN và module CRM của caller.

Metadata ACL thực cho thấy **cả bốn đều `prosecdef=true`, `PUBLIC EXECUTE=true`**. Chưa chạy thêm exploit với login không có app_web; không suy rộng runtime ra HTTP hoặc toàn bộ role ngoài phạm vi đã chạy. Sửa cần kiểm scope trong helper hoặc chia rõ hàm nội bộ có quyền với API đọc được cấp đúng caller; chỉ ẩn UI hoặc bỏ GRANT app_web không đủ nếu PUBLIC EXECUTE còn hiệu lực.

## 19 ca vi phạm SQL lần đầu đã kiểm lại

| Nhóm cũ | Số ca | Kết quả mới và giới hạn bằng chứng |
|---|---:|---|
| Upgrade v9 có HUY thiếu audit mới | 1 | Lên11, giữ HUY và dữ liệu; marker legacy true; actor/time/reason vẫn NULL |
| Đọc dòng đề xuất, dòng chứng từ, nhân viên khác PN; BAN_HANG đọc đề xuất M1 | 4 | SELECT trả0; positive KT M1 cùng PN trả1 |
| INSERT trực tiếp DA_DUYET | 1 | P0001; positive INSERT CHO_DUYET cùng actor/PN thành công |
| Sửa header/tham số/tiền lịch đã duyệt | 3 | P0001 ở cả ba; không suy thành lifecycle valid_to đã khóa |
| Thiếu login hoặc ID/login khác người khi duyệt | 2 | Bản đã được KT kiểm; UPDATE duyệt trả0; positive CFO khớp ID/login duyệt được |
| Profile/project khác PN | 2 | Ca đầu bị gate mapping đã duyệt; **không dùng làm bằng chứng FK**. Targeted tạo header chưa duyệt: cùng PN INSERT đạt, sai profile/project đều23503 |
| Current version khác PN hoặc khác hợp đồng cùng PN | 2 | P0001; hợp đồng/bản giữ nguyên |
| Replacement version khác PN hoặc khác hợp đồng cùng PN | 2 |23503; pending version giữ nguyên |
| Lịch sai PN với parent; replacement lịch sai hợp đồng | 2 | Targeted duyệt version mới trong cùng transaction; positive chèn lịch/replacement cùng PN/chuỗi đạt, hai ca sai P0001. Tránh dùng lỗi “ngoài transaction duyệt” che tenant invariant |

Ngoài 19 ca: SQL V3/V4 thực đã chặn BAN_HANG hoàn tất V3/V4 và CFO chỉ V3 hoàn tất V4 (P0001); CFO đủ quyền hoàn tất V4 được. Hypothesis `ktt_la_chu` bị owner của SECURITY DEFINER bỏ qua gate **đã được sửa trước final**: `kho.viec_kiem` không còn SECURITY DEFINER. Không ghi hypothesis cũ là vi phạm runtime mới.

Link HUY legacy: actor thường không xóa cờ legacy, không viết bịa người/thời điểm/lý do, không mở lại HUY (đềuP0001). Link mới không tự bật marker, không INSERT HUY/marker (P0001); chuyển HUY thiếu audit bị23514, cùng thao tác có actor/time/reason hợp lệ đạt. Những kiểm tra này giữ nguyên NULL lịch sử, không chế tạo audit để vượt migration.

## Migration, checksum và dữ liệu lịch sử

Đã so AST M0001–M0009 với backup trước sửa và so **exact SHA256 của joined SQL statements**, tất cả không đổi. Không dùng hash cả file thay checksum statement.

- Fresh →11.
- Dựng v9 hợp lệ có HUY rồi →11.
- Dựng đúng M10 bàn giao đầu từ file frozen rồi →11.
- Hai DB DEMO đã tồn tại từ review01 được snapshot trước rồi nâng cấp: `kho_test_crm_20261019_062952_972f51_upgrade_huy` (v9) và `kho_test_crm_20261019_062953_9ac238_upgrade_clean` (oldM10). Cả hai lên11; hash/số dòng của **các cột đã tồn tại trước upgrade** không đổi ở mọi bảng theo dõi; historical `version/checksum/applied_at` giữ nguyên. Cột mới được backfill không được giả là “không thay đổi”.
- Operational signature (columns/constraints/policies/function bodies, loại trừ metadata audit tương thích) của fresh/v9/oldM10 và hai DB lịch sử đều `b962ed2bf0e26e3444a1fc8373d400962d6db969355a33a9ed7a4a28fab55fa0`.
- Migrate lặp ổn định history/data/signature; audit oldM10 không thêm dòng lần hai.
- OldM10 statement checksum `345d562665cdd5b91bd5229b6e8108f4ceb227510ecbd1dd3c77afa754b4b353` được giữ nguyên trong `schema_migrations`; audit đúng một dòng sang currentM10 `8f34e92ba911436bed9f5aa8c1afaa4a70a6ce72e4fae34b90413441532208d7`. M11 checksum `308f095f7a28d688c6629607579a2de40ea4919596920e5a8a4ac3db46dd9549`.
- Inject digest M10 ngẫu nhiên trong transaction của DB DEMO → đúng `MIGRATION_CHANGED`; rollback giữ lịch sử gốc. Không rewrite checksum để làm migration xanh.

Đây là upgrade DEMO thực, không phải kiểm chuyển kho thật SQLite, V13/A5 đã hoàn tất hoặc mọi tích hợp K2 đã nghiệm thu.

## Evidence và bước sửa

Các đường dẫn sau đều tương đối repo, chỉ chứa dữ liệu DEMO và metadata tổng hợp:

- `var/codex-dieu-phoi/crm-schema-recheck02/run-20261019-071909-fad74d3c/result.json` — first; có snapshot trước của cả DB mới/lịch sử bên cạnh.
- `var/codex-dieu-phoi/crm-schema-recheck02/targeted-20261019-072059-952eeb67/result.json` — SHA256 `2a9dd2180e49642783c99b44f7bce164e8962272bf891aec9b56a6809f84f983`.
- `var/codex-dieu-phoi/crm-schema-recheck02/remaining-20261019-072232-8b58a213/result.json` — SHA256 `8d8acc8f870b84db10bd1d0d4a67bbc13719aedc7aa5b8c94fbaf1ff110cd6b8`.
- `var/codex-dieu-phoi/crm-schema-recheck02/mapping-20261019-072321-77b77dad/result.json` — SHA256 `57458305907ba7fe2191dab7b6d20614905b24e95756f65cd826b56804e24cce`.

Giao Claude sửa hai nhóm P1 mới và thêm regression đúng positive controls. M11 đã tồn tại trong DB thử: mọi sửa migration tiếp theo phải giữ khả năng nâng cấp có audit và lịch sử checksum, không reset DB/role/file. Sau coder terminal mới chạy lại đúng ca mới và control bị ảnh hưởng; chưa cần lặp toàn bộ migration/performance do hai lỗi scope này.
