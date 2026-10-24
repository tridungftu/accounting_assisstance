# Review độc lập CRM-01 pass03 — tích hợp M1

Ngày 19/10/2026. **Sáu nhóm chọn đạt, một nhóm chưa kiểm chứng; chưa nghiệm thu toàn M1/CRM.** Đã đọc lại dữ liệu nguồn/đích của runtime, tự đối chiếu account/amount/core/hash/fact/PK và tính lại các fingerprint, không lấy boolean xanh hoặc exit0 làm kết luận. Hai P1 của M1 review02 không còn tái hiện trong các ca đã chạy: tiền sau HĐ có hiệu lực ra đề xuất Vàng/131 với fact HĐ/đợt; source core_hash sai bị từ chối trước ghi và giữ nguyên target tại boundary âm.

## 1. Bản được kiểm và cách chạy

Root xác nhận CLI89659 terminal exit0/is_error=false, receipt tại `var/codex-dieu-phoi/kiem-chung-20261018-101441/crm03-handoff-20261019-074754-971/terminal-confirmation.json`. Manifest 121 file, SHA256 `82e5e26806e05ef732536fcb0e474ab6ee96f646566e335e728da28921f47c3a`; bộ kiểm so hash trước import/sau runtime. Reviewer đọc evidence sau đó tính lại toàn bộ 121 hash/byte: **0 khác biệt**.

| Thành phần cuối | SHA256 |
|---|---|
| `k2/m1_demo.py` | `e751679f221774d08bf2af95843c4947ebc1262f5be54bc704be663ecb0728e4` |
| `giao_dien/server.py` | `08956f59cd1fde6a677fab8357e381950b4b031df4fae3cba4fec4ec218931ed` |
| `de_xuat/engine.py` | `2df748ba483b795adaf2c5b0bb7cf45ae789cd6965dd30fdf8ada4e912d993fc` |
| `giao_dien/quick.py` | `5cfa91a10e925f75a0decaf29103f06f82866f7a1001adf0a003a2dd077fc9c8` |
| `tools/chuyen_sqlite_sang_pg.py` | `97c577768014e6139a2270d02551f5e1863b686c4b103581bfea2e411532a19c` |

Runtime retained: `var/codex-dieu-phoi/crm-m1-reuse-recheck03/runtime-1792371233389663800/`. Binding `binding_final_89659.py` SHA256 `6bb0d1feef6acbf5ee0a41e23821205e9cfb0d9dc60e9db91e6d57e647bf0b9c`; scaffold SHA256 `d02015813e72a888d0033abcf08e68ed0041a0e5f50fa64171e8bf8eaa4de958`. Root review AST/binding rồi mở `binding-release.json`; guard active từ startup, SHA256 `a517c5359ceada062900edd34280d4dc7daa2a001d5e05c84a9eae174813a229`, đúng isolated PYTHONUSERBASE, CODEX_NO_DELETE_FILES=1, PYTHONDONTWRITEBYTECODE=1.

Root chạy host với secret trong environment tiến trình, không CLI args/log/evidence. Reviewer/binding không đọc `.env`, credential file, backup hoặc dữ liệu thật. DB retained `kho_test_m1r03_a1022eddee36`, role retained `kho_test_m1r03_927d8df9fd90`; ordinary request role thực `NOSUPERUSER/NOBYPASSRLS`, member app_web. Admin chỉ seed/migrate, projection và read-only observer. Mọi workflow dùng `MO_PHONG_*`, không fake APPROVED bằng SQL. Không cleanup/reset/drop/delete của bộ kiểm; source/staging/DB/role và chứng cứ các lượt trước giữ lại.

## 2. Oracle và phạm vi kết quả

Expected lấy từ TL32 dòng quyết định102 đã chốt: chưa HĐ→344; có HĐ hiệu lực→131 đợt gần nhất, đề xuất Vàng; HĐ đến sau chỉ nối liên kết. Input là lựa chọn DEMO route đã công bố (300m trước HĐ, 500m/900m sau HĐ); expected không lấy từ test/output coder. Không tạo policy approved hoặc công nợ Junsky giả để ép131. Staging sau G02 chỉ có **3 BANK**, không có JOURNAL/OPEN_ITEM giả.

| Nhóm | Quan sát và tiêu chí đã đối chiếu từ raw evidence | Kết quả |
|---|---|---|
| G01 HTTP trước HĐ | HTTP200; BANK0→1, proposal0→1, dòng0→2; N1121/C344 300m, ObjectID DEMO A01, Vàng; raw/core/artifact/quick identity nối đúng; 0 approval tri thức, 0 lô | PASS control dương |
| G03 HTTP HĐ đến sau | Nhận/kiểm/duyệt HĐ qua HTTP đúng actor, duyệt ra3đợt; link cọc300m; active link0→1. Toàn BANK/proposal/dòng/lô cũ giữ nguyên, gồm PK | PASS control dương |
| G02 HTTP sau HĐ | Hai khoản500m/900m Có131/N1121, Vàng, đúng ObjectID/PN; PB đã duyệt, hiệu lực từ01/09/2026; profilev2 và fact DOT-1 1,2b hạn15/10 có provenance khớp nguồn/đích; không thêm link/autoallocation | PASS trong hai input này |
| G04 HTTP retry | BANK3→3, quick_items3→3, proposal3→3, dòng6→6, lô0→0; business fields và **sáu PK dòng đều giữ**; source quick_items full rows giữ | PASS trong ca chưa quyết |
| G12 positive direct helper | Source tốt, target có CRM dùng chung: native exit0, da_ghi=true, wrapperok=true;3BANK đối chiếu từng core/source/quick/artifact; ba nhóm shared full rows giữ | PASS phạm vi này |
| G12 negative direct helper | Bad-copy chỉ sai1BANK core_hash; native exit1, da_ghi=false, tu_choi=CORE_HASH_NGUON_TRUOC_GHI, wrapperok=false;27bảng business và audit/nguồn không đổi ở boundary âm | PASS detector **và** atomicity ca preflight này |
| G10 protected approval/kỳ khóa | Không có workflow thật được gắn và chạy để duyệt M1/protected references/khóa kỳ | **NOT_VERIFIED** |

Kết quả là **6 PASS, 0 FAIL, 0 SETUP_ERROR, 0 HARNESS_ERROR, 1 NOT_VERIFIED** theo bảy nhóm được khai báo; không phải toàn bộ G01–G12 đã đạt. `summary.json` cũng giữ `full_m1_acceptance=NOT_ACCEPTED`.

## 3. G02 — kiểm fact và provenance từ dữ liệu gốc

Reviewer đối chiếu lại từng BANK nguồn → natural_key/legacy ID → SAO_KE → quick_item/proposal gốc → typed proposal/dòng. Hai số tiền là exact integer ở core và typed; currencyVND, hash core tính trực tiếp từ core_json khớp source/target. Cả hai Có131 theo đúng khách/PN, không chỉ đổi câu giải thích header.

`contract_evidence` trong original engine proposal tham chiếu đúng HĐ/PB đã duyệt từ workflow G03, đúng profilema/version/hash pin ở tham_so PB, đúng PN và ObjectID. Fact đợt là DOT-1, số nghĩa vụ/phần còn lại1.200.000.000, hạn15/10/2026; cọc đã nối đủ300m trong G03. Ngày tiền10/10 và14/10 nằm trong khoảng hiệu lực PB. Approval actor/timestamp được đối chiếu tới PB thực. Không gọi helper tính nearest của product làm oracle; đợt expected đã chốt trong independent-cases, từ input lịch và cọc đã thu. Hai proposal có `auto_allocate=false`, allocations rỗng; số link và full link rows trước/sau G02 giữ nguyên.

Một điểm cần đọc đúng evidence: `proposal_json` nguồn giữ raw JSON, còn normalized target evidence chuyển technical float thành text. Khi parse nguồn không normalize, nguyên payload khác **duy nhất** tại `name_options[0].score` (float → chuỗi repr của cùng số); không phải thay account/amount/fact. Reviewer đã tìm toàn bộ diff path, chỉ thấy trường score này ở mỗi khoản. Sau phép chuyển technical score đã khai báo, toàn payload khớp. Riêng `contract_evidence` khớp nguyên cấu trúc mà không cần normalize. Không bỏ field nghiệp vụ để ép equality.

| Proposal khoản DEMO | SHA256 normalized source = typed original payload |
|---|---|
| Khoản500m | `cf1bf205b3ff4fed6105730a24b11ede0b1538df60e5e48bd4b65b5621b48417` |
| Khoản900m | `d0b0920d2082eb8f910067793792fe040aa502948122ec3ea96baff40bd70899` |

## 4. G03/G04 — semantic và identity

G03 money fingerprint (BANK/proposal/dòng/lô/lot_lines, không loại field/PK) trước=sau: `a5ad9b549b0c019382da6ca564b239ac4cafbd0d5402b68d18386afb60fd8371`.

G04 reviewer tính lại từ full rows, không chỉ dùng semantic hash bỏ ID: BANK, proposal, dòng, lô và lot_lines đều bằng nguyên dữ liệu trước/sau. Không còn PK churn ở sáu dòng chưa quyết của ca retry này.

| Collection G04 | Số trước→sau | SHA256 full rows trước = sau |
|---|---:|---|
| BANK |3→3|`f9bf5534fae053f31da269773171d68082aba50713a28d7f99912e818f380847`|
| Proposal |3→3|`4f32fe1983e957787ea503a840d837d7437dda0c0b41a09a1598b476a961b6fc`|
| Dòng proposal |6→6|`e849afbb5fdbf1de4b5d5f25ebdd9bfc6fb554cf384d65117d2a69ceafd1ec36`|
| Lô/lot_lines |0→0|`4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`|

Source documents3→3, quick_items3→3 giữ full rows; artifacts2→2/source_records3→3. Technical quick_runs2→3 và evidence3→5 do nhận raw lại, không là BANK/proposal/112/lô mới. Không lấy ca chưa quyết này thay kiểm protected approval/reference/kỳ khóa; tất cả BANK đang CHO_DUYET, khóa kỳ0, lô0.

## 5. G12 — positive dùng chung và exact causal boundary âm

Positive có nguồn thực3BANK/2artifact. Target full shared có4counterparty mappings,2project,3artifact (cả hai PN); cả ba nhóm full rows giữ nguyên. Native converter exit0 với source-scoped reconcile, không còn việc wrapper đổi nhãn exit1 thành success. Tuy nhiên source COUNTERPARTY/PROJECT **đều0**; do đó ca này chứng minh bảo toàn shared target và coverage BANK/artifact, không chứng minh chuyển positive records của mọi loại danh mục hoặc toàn A5.

Negative dùng bản bad-copy riêng sau mọi retry hợp lệ. Reviewer so `bad_source` với source_after của G04: **chỉ một record documents, chỉ field core_hash thay**; không đổi amount/currency/core_json/quick item. Không có ingest/retry/setup chen giữa before–action–after âm. Preflight từ chối với core_hash_nguon, trước khi converter tạo transaction ghi; vì vậy kết luận ca này là **từ chối trước mutation**, chưa phải mọi lỗi giữa giao dịch đã được kiểm rollback.

27bảng business được snapshot full rows, gồm mọi bảng converter ghi trong phạm vi, shared master/artifact, HĐ/PB/tham số/lịch/link, money/proposal/dòng/tri_thuc/việc/cảnh báo/lô/kỳ. Reviewer tính lại canonical hash hai phía, khớp cả stored hash:

- Business before = after: `448285e6b95ba4501b433730d4e42bbbc8c41431fa945457274464536e13ff06`; **0 bảng thay đổi**.
- Audit được đọc riêng,30→30 và nguyên rows giữ; không bỏ audit để che mutation.
- BANK hash, proposal và toàn6linePK giữ; không dùng số đếm bằng nhau thay fingerprint.

Nguồn gốc và bad-copy được băm **cả main/WAL/SHM ngay sát negative**, tất cả before=after ở đúng action boundary:

| Thành phần ở boundary âm | Bytes | SHA256 trước = sau |
|---|---:|---|
| Original main |577536|`b785ace1db6e11fb6257aede92a46822d9fd9ef1765cbdb51bf87b1c013ed576`|
| Original WAL |98912|`b6376c11c566298e64ac3aa627c652897fd68f8a9096e8cb59ab0649b52a5f6e`|
| Original SHM |32768|`65df98e7ffef4972b60715227b8fb3c667bf48fade1b2d7332e9ec02e35a308b`|
| Bad-copy main |585728|`5cedca0286a01be02598deff3b28c3c6da3b6b0bde3270f20f5ff6c8611bbd1b`|
| Bad-copy WAL |4152|`f18168d6f983a7fb87d65f89f737319662ee3d6d513c12350c8d5f151e7e0672`|
| Bad-copy SHM |32768|`c8fadd73ea5e17b66292d5b496d439c574dcd8c352368a3c1089bb9828125c33`|

Bad-copy main ban đầu trùng good-copy main vì phần tamper đang nằm trong WAL; chỉ hash `.sqlite` sẽ không đủ. Sau khi tiến trình/SQLite đóng, main bad-copy hiện có hash `08aadce0c9d1617b01c269d882476da7bfbbec0f4ac75fa7b5d81af932e6c318` và không còn WAL trong listing. Trạng thái này phù hợp với checkpoint/lifecycle khi đóng nhưng **nguyên nhân sau đóng không được trace riêng**; không gán nó cho negative action, không dùng current main hash thay bộ before/after đã đo. Evidence JSON boundary retained là căn cứ causal của ca âm, không tuyên bố nguyên bộ SQLite luôn byte-identical sau toàn phiên.

G12 ở đây là **DIRECT_HELPER/converter**, không phải HTTP negative. Chưa tạo một request HTTP gây cùng checksum failure qua đường an toàn, không monkeypatch helper rồi gọi đó là end-to-end. Fail giữa transaction/role error/unsupported currency hoặc lỗi khác chưa được phủ bởi preflight âm này.

## 6. Evidence và phần còn chưa kiểm chứng

| Evidence trong runtime retained | SHA256 |
|---|---|
| `G01.json` |`1deea2c17a53ce617b3af96f3d2a60acbbc036c728cc69ee6f1e922360877fcb`|
| `G03.json` |`33dc89acd2f4792978f3e41aee10a88afe0a0ffb53b980d0f3b94743183968e3`|
| `G02.json` |`c73a292368d036e78b9a141a8f41e6da0cf460fe3a41dfd1f02c4ac231062b34`|
| `G04.json` |`4386579ba27806e68fae74f8e2b400e437684a40972ffc041094d0bad0454737`|
| `G12-positive.json` |`93679bfe769442c6aa77013fcdcb5114e69c8c63799ee222409f8d5b8fd94d49`|
| `G12-negative.json` |`e572a5f0cea5e4a183010ccd3e680d26e93366a586e1c8e0724afd9548d5e4e8`|
| `summary.json` |`c793bdf92095df5d654986b7be3872d6ce9a6546ad01917bb367627423ae8a4b`|

G10 approved/protected line references, M1 approval workflow và kỳ khóa vẫn NOT_VERIFIED; snapshot có bảng tương ứng nhưng0kỳ/0lô không là control dương. G05/G06 concurrency có báo cáo khác, không được cộng thành ca M1 mới trong lượt này. Corpus tùy ý hai PN/profile/namespace, USD, bigint, ambiguous mapping/G09, full G11, mọi nhánh A5, HTTP failure-route và GUI chưa được kiểm ở đây. Main path HTTP bốn nhóm là có thật; không thay cho bấm GUI/restart tiến trình hoặc launcher.

Không có finding chặn mới trong sáu nhóm chọn. Kết luận dùng để đóng hai finding M1 cụ thể của review02 trên bản89659 và giữ các gate còn lại đúng phạm vi; không dùng làm bằng chứng toàn M1/CRM/V13 hoặc toàn cây33 hoàn thành.
