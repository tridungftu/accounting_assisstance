# Review độc lập actual legacy PostgreSQL backup — 01

**19/10/2026 — EVIDENCE_REVIEW / SELECTED_LEGACY_ONLY / NO_REEXECUTION.** Root báo probe02 terminal1; tôi đọc result/release/10 before-after JSON và kiểm15 source pins, không chạy probe/product import/SQL/PG query, không mở DB/raw/config/secret/source app, không sửa product hoặc xóa file. **M9 vẫn STOP**; chỉ definitions PostgreSQL đã được review import, không K2/M9 business execution.

## Byte binding

Private base `var/codex-dieu-phoi/v13-pg-backup-independent01/`; run `runs/run-b307f531ef71496d/`.

| Artifact | SHA256 |
|---|---|
| `probe_pg_backup02.py` | `98ddc90360d8344c0a1df1e41f8cc658c74fae0174a194e6a99ee448d9b230bd` |
| `source-pins-v2.json` | `f601712901aef3e1dfbf74f3732f35b440c47306bddbf4a3f46f0ece66df3437` |
| `release-root-b307f531ef71496d.json` | `77b9690208bc53be940116d80b9934e1f9763918536f0dbae54fde61716bce16` |
| Run `result.json` | `06883a8f6c41ee5f2340d06db39772e5dc36dd9b31ffa1e1c1d0c807e7d93f4a` |

15/15 selected current/frozen files khớp exact pin; whole handoff identity `19c3476c…da276` không có nghĩa chạy/review toàn M9. Release bind guard `a517c535…3a229`, new owned DEMO database/six schemas, role **postgres**, legacy copy/backup và intrinsic helper DELETE chỉ ở các target DEMO mới. K2 function calls/M9/host/HTTP/cleanup false. Kết quả ghi15 loaded legacy/definition modules,5 resolver calls, **0 forbidden calls,0 unexpected error**. Probe01/harness attempts trước được giữ riêng; kết luận dưới đây gắn đúng probe02/run/result này.

## Bằng chứng và kết luận thực

**Đúng10 criteria:4 positive PASS,6 negative FAIL,0 NOT_RUN/skip/setup error.** Terminal1 phản ánh business safety failures có thật; không quy thành driver/auth failure. Đã đối chiếu nội dung before/after độc lập, không chỉ tin status:

| Criteria | Quan sát artifact thực | Phạm vi kết luận |
|---|---|---|
| P01–P03 | Actual StorePG autoload, `create_backup→verify_backup`, `restore_backup(configPG)→actual StorePG open/status`; code probe so49 canonical table contents/rowid/typed values/config/raw và history version/checksum với baseline không rỗng | Selected supported positive chain PASS, không fake Store/wrapper. P01 kiểm marker keys/luc string/count riêng; không suy toàn marker semantics/one-time seed trên mọi restore |
| P04 | Source SQLite/schema/history/raw, PG source full observed state/history/identity/sequence, good bundle và selected source pins giữ theo predicates;0 forbidden calls | Selected source/bundle preservation PASS; không universal native-file lifecycle hoặc ordinary-role security proof |
| N01 / N03 / N05 | Mỗi before có workspace_meta=0,attempts=0,cash_mapping=1. Direct SQLite→PG / PG→SQLite / constructor autoload đều **ACCEPTED**, sau đó cash_mapping=0 và source data xuất hiện | Existing target row thực bị mất ở ba exact paths, không phải generic exception |
| N02 / N04 | Before knowledge_versions=1,empty sentinels; after vẫn1 nhưng **knowledge table hash đổi**, cùng nhiều bảng khác đổi | Existing knowledge bị thay bằng source content; rowcount equality không bảo toàn dữ liệu |
| N06 | `restore_backup(configPG)` **ACCEPTED**, `destination_exists=true`; PG full before=after,0 table/history/identity/sequence delta | Early preflight bỏ lọt nonempty target và publish restore folder; **chưa ghi đè PG** trong case này vì chưa mở Store ở target |

PG N01/N02/N05 after-body hash đúng source baseline `157e905aaf5153646b61bb0f96ef57e03d6887d85a76523154add38b225c0ea7`;17/16/17 sequence states đổi. Final identity modes/columns/history không đổi ở các case ấy không chứng minh không có transient ALTER. N03/N04 SQLite schema/history/application_id/user_version giữ nhưng business rows đổi. Đây là observed overwrite/publish failures phù hợp static triggers `sao_chep_bang.py:78–129,201–248` và sentinel guards `ket_noi.py:229–246,460–488`, chưa là kết quả sau repair.

Pin10 unique before/after JSON bằng SHA256 vector **`1b50cdf67bb12892c433e94b7bee4b6ed33986ab5b3428233e5cb7d39ed347e6`**: canonical UTF-8 JSON `{basename:sha256(file_bytes)}`, sorted keys, compact separators; gồm N01–N04 mỗi before/after và N05–N06 mỗi before-after bundle. Root giữ exact artifacts/attempts; không cần mở DB lại để xác nhận các delta trên.

## Giới hạn và giao sửa

Fixture seed là SQL setup, không ingest/approval/accounting workflow; three BANK/JOURNAL/INVOICE không NT/proposal/published-file coverage. Từ observed source-equivalent after counts: **12/49 application tables không rỗng,37 rỗng**; schema-history metadata tách riêng, không ghi49nonempty. Cross-engine oracle chỉ bỏ exact marker key khỏi business comparison và so regenerated history version/checksum; within-PG preservation so full history/applied_at. Không áp exemptions đó cho full K2. Chưa có transient-before-effects observer, changedseed/extra-table/older-target/caller-transaction/FK-mode/race/CLI/ordinary-role/GUI/DR proof trong run này.

**Chấp nhận4 selected positive criteria và xác nhận6 safety failures để giao sửa V13 độc lập; không nghiệm thu legacy backup toàn bộ hoặc full V13.** Handoff đã khép technical R1/R2 `GIAO-SUA-V13-LEGACY-BACKUP-01.md` bản26bc là phạm vi sửa phù hợp: all49/exactseed admission trước effects, actual writer exclusion, constructor-before-migrate guard và safe CLI; root phải pin/release riêng trước coder. Không chỉnh expected để biến các FAIL thành PASS hoặc re-use/reset target đã bị overwrite. Full typed K2/roles/RLS/encryption/artifact archive và M9 vẫn ngoài runtime acceptance này. Result/release/probe/pins/source và before-after vector kiểm lại trước bàn giao, giữ nguyên bytes.
