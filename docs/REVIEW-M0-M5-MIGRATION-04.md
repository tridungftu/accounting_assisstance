# Review độc lập M0/M5 migration04 — text-search admission

19/10/2026. **STATIC_REVIEW_CLOSED_FOR_SCOPED_RUNTIME / RUNTIME_NOT_RUN_BY_REVIEWER / CHƯA NGHIỆM THU.** Không thấy blocker mới trong sửa hữu hạn mục3 handoff04. M03-2 được đóng về cấu trúc mã cho counterexample TEXT SEARCH CONFIGURATION đã tái hiện ở03; chưa thay kết quả02negative FAIL của probe03 thành04 PASS.

## Pins và phạm vi đọc

- Actual coder72850 terminal `7ee109`; freeze `9487ed`, folder `var/codex-dieu-phoi/kiem-chung-20261018-101441/m0-m5-intake-ui04-handoff-20261019-175226-626-cf1d4eda/frozen`; manifest210 SHA `bb25b5d6d0b06403bce04d22a6c239b269d1b024f7b3a493d56f26b7512ec780` theo root; 6 thay đổi/0 drift theo freeze.
- Đọc đủ `src/kho_tri_thuc/ha_tang/postgres.py:1–277`, SHA `aa90a9a99c17f491afeda5fa54766e7cfa0df4e08560251cc8781bf6882f7668`; đọc toàn diff với03 `8e00312d…96d2`.
- Đọc toàn diff regression và actual setup/control `tests/test_m0_m5_migrations.py:178–202,287–345`, SHA `8e74b0cc96a7812706c2abe2080563b1e212c4f2a4918aec11611a7ddfda9bf2`; report04 đủ105 dòng, SHA `a3bdee18051e8db9e4830a567d0347d3d6614b7ee17f333f72ce96f8b967c613`.
- `pg_migrations.py` SHA `f05753fdecd21d06d5524b5a43394eafd5982fcb06461bfd96e27a50fdebdcb9` khớp03: 0 SQL/checksum/schema change. Handoff04 SHA `aedd9f87b9f78a0b7dea0c511e2bfad76348b2379befdf9c8b4dd1fe56fd539e`; root-test03 SHA `352b50644d9efc3a31dff33ae32a259f4d2c17aa2e38ddb4a0406e127b3d7ff6`.

## Closure cấu trúc và oracle

1. `postgres.py:132–143` đếm trực tiếp `pg_ts_config/dict/parser/template`, conversion và opfamily bằng đúng namespace columns; mỗi lớp loại extension members theo cả `classid` và `objid`, giữ namespace/system/temp exclusions ở116–119. Standalone config ở public có ít nhất một row nên count>0, không phụ thuộc nó có bảng hoặc hàm riêng. 11 alias trong query khớp11 keys `_COT_DOI_TUONG:147–148`; tuple/dict reducer151–160 giữ nguyên semantics, không thêm alias trùng.
2. Hai nhánh actual `_current_state:82–94` đều dùng count đó: không master→`FOREIGN_DATABASE`, master thiếu history→`MIGRATION_HISTORY`. `migrate:229` gọi admission trước `CREATE SCHEMA/TABLE:234–238`, vòng migration253 hoặc marker256; phần call order này không đổi. Chỉ thêm SELECT catalog và keys, không có DDL/DML/credential output trong admission.
3. Regression305–326 tạo config thật từ `pg_catalog.simple`, yêu cầu1config, mapping không rỗng và không extension membership. Nó yêu cầu đúng mã ở actual READ ONLY admission, rồi actual migrate, và so độc lập before/after. Setup181–190 dùng DB template0 mới, chỉ close connection/giữ DB; không DROP/reset. Không fake connection/monkeypatch product để làm negative xanh.
4. Controls empty schema/master và actual pgcrypto337–345 giữ nguyên từ03; extension không có hoặc setup lỗi không được tính PASS. Routine/enum/sequence/view/domain và lineage/default registry cũng không đổi trong diff. Không cài hoặc resume M9; historical definitions/helpers được giữ nguyên trong file SQL cùng hash03.

## Giới hạn

Đây là finite inventory, không phải chứng minh mọi object class của PostgreSQL đã được phủ; report04:98 nói rõ giới hạn. Regression `catalog_doc_lap:291–303` quan sát count config/map/relations/routines, namespaces và presence history/marker; không phải full catalog-content fingerprint và không thực đo type count dù docstring nhắc kiểu. Giới hạn mô tả này không chặn counterexample config hiện được giao. Không thêm yêu cầu speculative cho object classes khác.

Reviewer không import/AST/compile/run product, SQL/PG/tests/HTTP/process hoặc đọc DSN/.env/real rows; chỉ tạo review này. Actual04 positives/negatives, no-change evidence và toàn module vẫn chờ root runtime riêng; 03 PASS và terminal/freeze không thay thế chúng. Service snapshot/UI/test namespace do reviewer khác/root kiểm, không được closure bởi review migration này.
