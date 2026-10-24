# M0/M5 candidate03 — kiểm chứng độc lập trên Windows

19/10/2026. **SELECTED_RUNTIME_VERIFIED / CHƯA NGHIỆM THU TOÀN MODULE.** Actual Claude35965 terminal0 `69e9ac`; freeze210source manifest `37b671d7869134b2c2552bbc913916fdec03f9a1218157e62c53acce3d58056a`,11file đổi đúng phạm vi,0drift được bảo vệ. Root đọc final reports/test diffs và chạy dưới guard giữ mọi file/DB/role; toàn210source trước/sau nguyên. Kho thật SQLite; không chạy hoặc sửa M9.

| Bộ kiểm tra root thực chạy | Kết quả | Giới hạn |
| --- | --- | --- |
| Pure03 `e13d17` |17/17 PASS,0skip |7migration-pure+10service-pure; không PG |
| Migration03 `9eeb17` |16/16 PASS,0skip,30.549s |7pure+9PG; overlap với pure03 |
| Service03 trên host `99feea` |34/35 PASS,1FAIL,0error/skip,6.411s |10pure+25PG; FAIL assertion phạm vi đếm partial |
| HTTP03 trên host `4627a9` |2/2 PASS,0error/skip,4.935s |API loopback DEMO, không browser/picker |

Không cộng các tập chồng lấn thành tổng kiểm tra độc lập. Đây vẫn là tests do coder viết được root đọc/chạy; probes dưới đây có oracle độc lập.

Service attempt sandbox `5ca0e5` có35run/17PASS/2FAIL/16ERROR, nguyên nhân đầu tiên WinError5 tại os.link; các lỗi thiếu state sau đó không chứng minh từng chức năng hỏng. Probe riêng `83bb2d` tái hiện sandbox chặn hard link; actual host `e140dc` tạo thành công bằng bytes DEMO, giữ cả source/link. Root chạy lại cùng nguồn/guard trên host, không vá product hoặc bỏ quyền. Giữ cả attempt lỗi.

## Lỗi test được xác định

`tests/test_m5_k2.py:582` đếm toàn bộ id_dong_nguon prefix rồi kỳ vọng2, trong khi K01/PN_A và K02/PN_B cố ý dùng cùng native line IDs ở hai logical phiếu. Root read-only query trên DB DEMO retained (`b333a3`) xác nhận count4 = nguồnA2+nguồnB2, receipt SHA `89115ef97ea09312d17075edd4e33e757c82d36693ccb04ac18e3ce16fda6d20`. Không đổi FAIL thành PASS; sửa oracle phải giới hạn đúng phieu_id/PN, so tập logical IDs trước/sau partial và giữ instanceB nguyên. Query cuối không tự chứng minh mọi intermediate assertion đã chạy.

## Hai counterexample độc lập thực chạy

**PreviewA/tokenB — DEFECT_REPRODUCED `04f4a3`, không product PASS.** DB DEMO mới,3kết nối thật: app_web, configured owner intake/FILE, owner mutation riêng. Actual K01 intake tạo version/lines/history không rỗng; ordinary CFO_A detail→FILE→download đúng SHA/length là positive. Timing wrapper chỉ delegate nguyên SQL/results: actual mapping SELECT.fetchall(A) hoàn tất → second owner dùng existing CFO_A/current SOURCE_MAP+M5/V4 đóng mappingA và append samePN ROOT_SEED_DEMO successorB, triggers bật/0newgrants → basis SELECT thực chạy. DTO vẫn mappingA(open), token bằng freshB khác tokenA,3pointers giữ nguyên; ordinary FILE với mixed response được nhận và download hash/length khớp. Cùng một finding với ba review final, không cộng lỗi. Synthetic trusted catalog mutation, không claim đây là ordinary samePN remap hoặc HTTP/browser exploit. Handoff03 đã yêu cầu coherent graph đang xem; cùng transaction READ COMMITTED chưa đáp ứng.

Probe callable đầu tiên `9e52e7` ERROR_NOT_OBSERVED vì wrapper thiếu cursor iteration, không product FAIL/PASS. Root giữ attempt, sửa riêng harness (terminal schema đúng receipt thực +delegate iteration), không sửa product; actual rerun mới `04f4a3` có observer và FILE controls đầy đủ. Result SHA `dc72b7b118273ae57bf5c4b1cb21e22f2bbf6d06a3dded796677ca126f958134`, harness final `41448e8fd385f9a278c7336cb74b295a971e67e9aa5d82b87ba56e0d3c4cb476`.

**Catalog admission — 2positive PASS/2negative FAIL `d2badb`,0error/notrun.** Bốn DB template0 mới được giữ. Empty master+empty schema và approved pgcrypto có actual36extension routines vẫn được admission0. Hai DB có standalone non-extension public TEXT SEARCH CONFIGURATION +19mapping rows, có/không empty master, vẫn bị `_current_state` actual nhận là fresh0 thay FOREIGN_DATABASE/MIGRATION_HISTORY. Gọi admission trong READ ONLY; independent catalog before/after giữ nguyên cả4; không gọi migrate/DDL ứng dụng để làm hỏng foreign fixture. Kết quả chỉ chứng minh admission bug và prewrite order từ source, không claim đã quan sát application DDL đè lên foreign DB. Result SHA `32451827aac6b10a7cf67c43813655f5df5c57a75f1f0cc352fc570c5393e6b3`.

Hai probes dùng owned child watchdog60/90s, actual5.437/3.705s,0timeout; original no-delete guard và210source nguyên; không biến launcher exit0 thành product PASS.

## Phần còn mở

- Preview coherent snapshot và catalog text-search admission nêu trên cần sửa, giữ các positive/current FILE guards đã đạt.
- JS form epoch sau POST/refresh chỉ actor epoch: review final F1 còn source-proven; chưa actual browser causal test. Actor epoch cũ đã sửa, không lặp finding.
- FILE namespace test hiện mô phỏng receipt winner; cần hai phiếu hợp lệ cùngPN/cùngkey qua service thực, observer chờ namespace và xác nhận loser0artifact/stage/lo delta. Không thay bằng fake receipt hoặc barrier-only.
- Browser picker/actor/form delayed response, full source/forgery matrix, L11 và toàn33 vẫn chưa nghiệm thu. Không kéo M2 hoặc nghiệp vụ vay vào repair này.

Chi tiết private retained evidence: pg-retained-20261019-173136-cce7781b; pg-retained-20261019-173324-54ec7235; pg-retained-20261019-173350-d7361f23; root03-finite-probes-ea0700aad82e; m0-m5-catalog-admission-private01/root-run-be19b4ee335f. Chỉ root đọc var; Claude nhận báo cáo tổng hợp này và final source/reviews đã lọc.
