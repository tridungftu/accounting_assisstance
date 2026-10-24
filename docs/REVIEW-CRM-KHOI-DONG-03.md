# CRM03 bootstrap — kết quả pure validation/stub, host chưa chạy

**19/10/2026. Kết luận:** 28 ca **19 PASS / 9 FAIL / 0 SETUP_ERROR / 0 skip**, trên source cuối của CLI89659. Đây là kiểm validator và call order bằng connector/query **giả trong bộ nhớ**, không phải test kết nối PostgreSQL, nút mở, GUI hoặc nghiệm thu CRM. Không sửa product.

## Gate và bằng chứng

Các file evidence/runner nêu dưới nằm trong `var/codex-dieu-phoi/crm-launcher-recheck03/`; receipt/freeze nằm trong `var/codex-dieu-phoi/kiem-chung-20261018-101441/crm03-handoff-20261019-074754-971/`. Chỉ dữ liệu giả/metadata kỹ thuật, không credentials.

- Receipt authoritative89659 exit0, `coder_terminal_confirmed/allow_product_execution=true`; `allow_host_launcher_execution=false` được giữ nguyên. Không dùng receipt51099.
- Freeze121file từ `kiem-chung-20261018-101441/crm03-handoff-20261019-074754-971/source-hashes.json`, SHA256 `82e5e26806e05ef732536fcb0e474ab6ee96f646566e335e728da28921f47c3a`; đối chiếu đủ path/bytes/hash **trước và sau**. Không mismatch.
- Private guard đã nạp, no-bytecode; guard SHA256 `a517c5359ceada062900edd34280d4dc7daa2a001d5e05c84a9eae174813a229` trước/sau khớp.
- Runner `pure_validation03.py` SHA256 `a26fe8314f35378cb46c9af797c95cf46954fde4a07baa6ef36ea85175d58468`.
- Actual evidence `pure-result-20261019-005111-874.json` SHA256 `a8b91fdfb0b5b028df94da323434d04dca41c362850dcbeb1fae3cc7d8717130`.
- Runner bind receipt và freeze121 trực tiếp; scaffold chuẩn bị `gate_preflight.py` trước đó chưa được gọi và còn contract launcher riêng, không phải gate đã dùng cho run này. Trước host sau này phải bind scaffold với field release/source manifest thật của root.

Không đọc credential/`.env`/local config thật; JSON config giả patch `Path.is_file/read_text` trong memory. DSN giả không password, user/service không tồn tại; không được dùng làm credentials kết nối. `psycopg.connect`, Connection/AsyncConnection.connect và socket connect bị thay; các case cần bootstrap dùng fake connection/seed/schema functions. **0 real network, 0 SQL thực, 0 launcher/cluster actions**, không tạo credential/config. Toàn bộ evidence/file được giữ.

## 9 FAIL thực ở cấp validation/stub

| Nhóm | Case | Actual | Ý nghĩa và giới hạn |
|---|---|---|---|
| Endpoint không tường minh | E01 omitted host + fake PGHOST; E02 omitted host + fake PGHOSTADDR; E03 service-only | `kiem_dsn` đều ACCEPTED DB DEMO | Code fallback host thiếu thành localhost, không buộc mọi yếu tố libpq có thể kế thừa phải được ràng buộc/loại trừ. **Chưa kết nối/resolve service**, không nói đã quan sát DB remote; chứng minh validator không fail-closed trước bước đó |
| App/admin khác port | C04 | `doc_ket_noi` ACCEPTED khi app127.0.0.1:6543/admin127.0.0.1:5432 cùng dbname | Validator so tên DB, không kiểm endpoint tương đương. Config giả trong memory; không có server ở6543 được gọi |
| Helper side-effect order | D03 app remote; D04 app khácport | `chuan_bi` trả SAN_SANG trong stub,2 connector calls/1 seed call/2 schema calls | Direct helper chỉ kiểm admin trước seed, không kiểm app local/same-target trước đó. Stub làm app trả cùng DB name/version nên validator chấp nhận; không chứng minh DB thật đã bị seed nhầm |
| Helper phát hiện sai DB muộn | D05 | Có `KET_NOI_KHAC_DB`, nhưng sau2 stub connectors/1 stub seed | Có check DB name ở cuối, **không phải không check DB**. Điều kiện kỳ vọng là reject trước admin side effect; hiện chậm hơn |
| Env server bỏ validator | S02 remote app env; S03 non-DEMO DB app env | Đến connector trap1 lần trước DataError local/DB-prefix | `_crm_ket_noi` trả env app string thẳng, `crm()` gọi connect rồi mới role/schema check. Không có network thực; trap chứng minh thứ tự connect được gọi trước validator. Local JSON có validate không bao phủ đường env |

19 controls PASS gồm explicit loopback/localhost/IPv6 syntax, reject explicit remote/hostaddr/multihost, sai DB prefix/identifier/conninfo, same-target config/different-db/invalid JSON, local bootstrap stub, remote admin bị chặn trước connector, role normal/super/BYPASS/nonmember input rows, và server thiếu config không gọi connector. PASS syntax IPv6/localhost không chứng minh endpoint đó đang chạy hoặc trỏ đúng cluster.

## Điểm neo source cuối

- `src/kho_tri_thuc/k2/crm_khoi_dong.py:34–47`: parse DSN/host fallback/DB regex; `:61–64`: compare tên DB; `:67–75`: role checks; `:87–106`: validate admin→connect/seed→connect app; `:108–112`: compare DB name/schema cuối.
- `src/kho_tri_thuc/giao_dien/server.py:175–208`: environment path và connect-before-role/schema; env có app bỏ qua local JSON validator.
- Root scripts `MỞ BẢN DEMO.cmd`→`start-web.ps1:112–133`→`tools/chuan_bi_crm_demo.py::chay`→`crm_khoi_dong.chuan_bi` là đường caller đã đọc. Không gọi launcher hay tool main trong run này.

## Static observations — không cộng vào9FAIL hoặc gọi đã test runtime

1. **Cold PG start chưa có trong đường nút mở:** caller cuối nêu trên không gọi pg_ctl/start service/khởi động cluster đã biết; module bootstrap cũng ghi rõ không start/cài cluster. `start-web.ps1` chạy bootstrap, bootstrap lỗi thì vẫn mở web và in CRM chưa sẵn sàng. Vì vậy code hiện có thể chuẩn bị CRM khi PG đã chạy, **chưa hiện thực bước tự start cluster đã có khi PG đang tắt trong đường này**. Không stop PG để kiểm; capability cold-start host thực còn NOT_RUN.
2. **Non-owner chưa được validator chứng minh:** role query kiểm `rolsuper`, `rolbypassrls`, membership app_web; không query DB/schema/table owner hoặc membership/settable owner. Các role-row stub chỉ xác minh ba flag đó; không tạo role/DB, không chứng minh exploit owner/RLS thực. Root setup ordinary non-owner vẫn phải làm và kiểm SQL riêng.
3. **Actual same cluster/DB chưa được bootstrap query chứng minh:** chỉ current_database/schema version, không endpoint/cluster/database OID. C04/D04 chứng minh configuration check thiếu; actual endpoint equality cần host DB proof riêng sau root release.

## Đề nghị sửa có phạm vi

- Một validator chung cho **mọi đường JSON/env/direct helper**, kiểm app/admin hoàn chỉnh trước connect/CREATE/migrate/seed. Không fallback host thiếu khi libpq còn có thể kế thừa env/service ngoài cấu hình; normalize hoặc reject rõ hostaddr/multihost/service/port không được hỗ trợ.
- Định danh và so target app/admin theo endpoint/port/DB hợp lệ, sau connect local xác nhận DB/cluster thực; không chỉ so tên DB. Không thử remote để “xác minh”. Giữ admin riêng, app non-owner/NOSUPERUSER/NOBYPASSRLS.
- Cổng ordinary role bổ sung ownership/member-owner theo contract thực; không xem membership app_web là đủ. Thử lại bằng LOGIN thật và dữ liệu được RLS bảo vệ trong gate PG riêng.
- Root quyết định bổ sung caller start **đúng cluster đã biết** theo ownership/status hoặc ghi rõ cổng cài đặt cần PG chạy; không coi launcher hiện tại đã đủ cold first-open. Không cài/initdb/reset/delete PID/lock hoặc stop process khác.
- Giữ lỗi sạch, unique retained logs và no-delete guard. Sau sửa kiểm lại pure controls + các case9FAIL, rồi host first/reopen/OS restart/persistence/port/role/config/log/download bằng root release riêng; GUI có công cụ và thao tác thật mới nghiệm thu GUI.

Không tạo host credentials, không cấp host execution hoặc sửa product. Bản public này được root yêu cầu sau kiểm private; không có action tới cluster/server đang chạy.

## Lệnh pure probe đã dùng

Chạy tại root repo, với `PYTHONUSERBASE` riêng `var/codex-dieu-phoi/test-python-userbase`, `CODEX_NO_DELETE_FILES=1`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, `PYTHONPATH=src`. Không có DSN/token trong command:

```powershell
python -X utf8 var/codex-dieu-phoi/crm-launcher-recheck03/pure_validation03.py --source-root . --terminal-receipt var/codex-dieu-phoi/kiem-chung-20261018-101441/crm03-handoff-20261019-074754-971/terminal-confirmation.json --source-manifest var/codex-dieu-phoi/kiem-chung-20261018-101441/crm03-handoff-20261019-074754-971/source-hashes.json --output var/codex-dieu-phoi/crm-launcher-recheck03/pure-result-20261019-005111-874.json
```

Actual process exit1 vì9case FAIL; không phải setup error. File output dùng chế độ tạo mới, không ghi đè; chạy lại phải dùng tên mới. Bản public này được root yêu cầu sau kết quả private, không đổi source/evidence của run. Phương án tái dùng runtime/cluster cho repair04: `CRM-03-TAI-SU-DUNG-KHOI-DONG-PG.md`.
