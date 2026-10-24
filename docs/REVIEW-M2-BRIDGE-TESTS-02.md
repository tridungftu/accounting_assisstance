# M2 bridge repair02 — review tests và binding probe độc lập

FINAL_STATIC / AGENT_RUNTIME_NOT_RUN. Frozen249: `var/codex-dieu-phoi/m2-bridge02-handoff-20261019-214410-319-d41b1a49/frozen`, manifest `4c81093fbe59bc3ba6c894d4a7d7a55fe4b99405bde9292687302256c7755bab`. Không import sản phẩm, test/SQL/HTTP/process hoặc đọc secrets/sourceapps. Báo cáo/probe cũ giữ nguyên.

Đã đọc đủ tests migration222, service616, HTTP260 dòng; toàn seed199 dòng, diff đầy đủ HoaDon01→02 và trực tiếp chữ ký/body mapping/source-review hiện tại. Các SQL replay/guard liên quan được đọc từ frozen02, không suy từ bản01.

## Kết luận tĩnh

Không thấy blocker an toàn mới cho root chạy các suite đã scope vào DB DEMO mới bằng bridge/guard/watchdog đã review. Chưa tuyên bố tests PASS hoặc sản phẩm đã nghiệm thu.

- Lỗi oracle/setup T02 trước đã đóng về cấu trúc: migration `197–208` tạo instance/profile bên ngoài assertRaises; riêng INSERT ROOT_SEED INVOICE_LINE phải có `ANH_XA_SEED_SAI`, count mapping không đổi. Prefix1–12 có literal lineage pin; assertIs13/14 vẫn không thay bằng chứng checksum lịch sử độc lập.
- Service `297–311`, `322–334`, `426–436` giữ nguyên body/key/tokenA cho mapping, route, source-review; so mọi field ngoài `lap_lai` và kiểm True khi retry. Các changed-H dùng cùng key; không đổi token để che stale. Source-review current-rights chưa được t99 thử trực tiếp; independent sibling03 bổ sung cả service và direct SQL.
- Service `269–285` có seven literal mismatch cases cho cả API và direct definer, thêm missing-evidence; nonempty G01 phải tạo actual CFO mapping và route. Literal candidate trong seed là raw evidence, không approved UUID/logical root. API mới bắt buộc `evidence_revision` (`hoa_don.py:542–555`); probe mới bind explicit integer1 từ fixture pin, không dùng request cũ thiếu field.
- Classification ARRAY được sửa ở service `406/418/539`; nghiệp vụ không đổi theo STRING oracle. G01/ZIP/G04/ABA/reorder/NULL quantity và M1/M5 sentinel positives vẫn tồn tại. ZIP có actual member ordinal/name/hash, receipt/core/logical/route identities được giữ.
- R3 `359–395` có successor route hợp lệ rồi owner UPDATE core quantity/date/hash/payload/key negatives với core/raw snapshot không rỗng; app UPDATE có thể bị deny hoặc 0rows, sau đó kiểm toàn core không đổi. DELETE branch chỉ kiểm tĩnh, không chạy DELETE.
- T16 `555–582` thử các ZIP partial NULL ở observation/candidate bằng CheckViolation và giữ counts. Partial mapping-shape chủ yếu được kiểm tĩnh ở migration `136–144`; không coi substring SQL assertions là toàn bộ runtime NULL-shape proof.
- Unit digest tests `583–597` có negative canonical mismatch/missing meaning/bad basis shape; positive INSERT chỉ tồn tại trong transaction rồi Rollback, chưa chứng minh reopen/persistence. Nó là new owner-admitted definition, không tự thành current CAI authority: profile vẫn pin existing ref/digest923a98. Source-basis hiện là declared syntax, chưa phải verified raw-artifact FK/actual CFO conversion proof; không suy một P1 chỉ từ trusted owner thêm new definition.
- T99 `600–612` khóa actor DEMO bằng UPDATE, thử direct SQL mapping trước/sau và API denial, giữ counts. Đây là current identity revocation, không source-capability DELETE. Seed snapshot trước/sau chưa có actual revoke→reopen control của M5/M2; không tuyên bố phần đó đã kiểm.
- Helper `raises:167–172` còn so substring trên DataError/psycopg.Error; đây không phải oracle exact-code độc lập. Probe root giữ P0001 primary-prefix/DataError.code với exact prebound sets, không nhận setup/connection/timeout thành denial.

HTTP `100–204` dùng actual local server/cookie/token/raw bytes, nguyên mapping body cho retry, wrong-ref/key/artifact errors và bounded upload700000. `206–215` chỉ kiểm served shell/JS bytes, không GUI. `218–256` là isolated error-sanitization unit với synthetic driver exception; integrated stale409 ở `159–167` là control riêng. Không thay GUI/Promise race proof bằng hai loại tests này.

## Safety và giới hạn

Setup vẫn nhận `KHO_PG_DSN_TEST`, tự CREATE DATABASE/ROLE, gọi CRM/M5 DEMO seeds; tests không tự chứng minh DSN loopback/fresh trước CREATE. Chỉ root scoped wrapper được phép cấp credentials và endpoint mới; không dùng bare unittest. Không thấy DROP/DELETE/unlink/rmtree hoặc đọc sourceapps; retained folders/DB/roles giữ, teardown chỉ đóng connection/server/thread/phục hồi test env. Unit-positive Rollback được ghi rõ, không gọi là retained committed admission.

Không có causal concurrency/coherent interleave/actual GUI trong ba file. Root independent selected controls giữ nguyên11 oracle labels trước, bổ sung source-review exact service/direct replay, changed-H và current M2-module UPDATE control trên actor mới; capability-row DELETE vẫn UNVERIFIED, P09–14 chưa chạy. Các file mới chỉ definitions với release false; root FULLREAD/peer và release riêng trước mọi import/PG.

| Frozen source | SHA256 |
|---|---|
| tests/test_m2_migrations.py | b85bc5252bceace31a28c66d2866acb015488daa2eb990e415195b071920d391 |
| tests/test_m2_k2.py | c32010e9719f0995cdac9a1378aa329875bda3aa0b490ac012cf681d6e369431 |
| tests/test_m2_http.py | adf93d8a7f6fb4616bbaded6c1fef2fe076edb76da284465890677e1d18833f3 |
| k2/hoa_don.py | ad806ea2020109ae4a3cce5b463fc8e7934f0bb14ef8fcffb9693730174af548 |
| k2/m2_demo.py | 16b75651e7a0782b028a4cfedc768a68df0317c9cc3909adfbcff0346e1bd76a |
| ha_tang/pg_migrations.py | 172e14feb2ae7314c8152422175178b767ee28a3667dcfe54a64af4ec4ce99fa |
