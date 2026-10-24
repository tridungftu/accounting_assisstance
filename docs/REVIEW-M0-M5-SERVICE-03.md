# M0/M5 — service, bootstrap và seed final03

19/10/2026. **FINAL_SOURCE_BOUND / STATIC_ONLY / CHƯA NGHIỆM THU PG/HTTP/GUI.** Root đã quan sát Claude35965 terminal0 `69e9ac`, freeze `d9ace8`; manifest210source SHA `37b671d7869134b2c2552bbc913916fdec03f9a1218157e62c53acce3d58056a`. Bản đọc: `var/codex-dieu-phoi/kiem-chung-20261018-101441/m0-m5-intake-ui03-handoff-20261019-172347-991-62d56e08/frozen/`. Handoff03 SHA `c3e9ef21017ababea429cd10d530f9554ac7118c9ece6425a62f4d49473993de`. Reviewer chỉ đọc/hash nguồn và viết báo cáo mới này; không import/compile/test/SQL/process/HTTP/GUI, không sửa product/corpus/input.

## Source pins và phạm vi

Các path dưới `frozen/src/kho_tri_thuc/`; SHA đối chiếu đúng manifest final. Service/helper/bootstrap trùng bytes snapshot interim root đã đọc, nhưng mọi kết luận dưới đây được rebind bằng đọc trực tiếp final, không lấy SQL interim làm chứng cứ cuối.

| File | SHA256 | Đã đọc |
|---|---|---|
| k2/kho_so_luong.py | `945aa0a2341c232c1441611490e8223122cfe9092d02cb34e729f3a24052540c` | toàn728lines |
| k2/nguon_chung.py | `8f1b670886870475a3b8c79877401a98d5ef7bb4f6598f4d86459bf1363e3561` | toàn237lines |
| k2/crm_khoi_dong.py | `1629fd79562baa0b02916d85617fa1337e14128244726cf4e1a003590e08ad93` | toàn221lines |
| k2/m5_demo.py | `6dff7b8c0e45b0f99f46ec07e85aed49fc6b1484e58aa785ae8628fb8e57f350` | toàn178lines, không đổi02 |
| k2/crm_demo.py | `71f0f9567af04619d95d363aa7045a076162a690d8479e7465d87945cae01f90` | toàn78lines, không đổi02 |
| k2/quyen.py | `8a3570dc6aa5e63006b26f79e8209c75c6f46e57798ed02c2a6e77d7a9893d6b` | toàn102lines; không chạy hành vi M9 lịch sử |
| ha_tang/pg_migrations.py | `f05753fdecd21d06d5524b5a43394eafd5982fcb06461bfd96e27a50fdebdcb9` | chỉ3030–3036,3102–3120,3231–3266,3586–3609,3728–3772,4297–4363,4511–4778 |
| giao_dien/server.py | `2e948604576486e1f153e5010ad00685dc11f275390b446eeb0c946be0d19c81` | wiring431–475; HTTP/UI rộng do peer review |

## Finding còn mở

**SR03-1 — P2: read model đang xem và expected FILE basis chưa cùng một snapshot.** `kho_so_luong.py`92–96 chỉ mở transaction/set GUC, không đặt isolation hoặc khóa read model. `chi_tiet`505–519 lấy root/content/rows/observations/mapping/work bằng nhiều SELECT;521 mới gọi getter token. Final SQL4583–4594 là STABLE definer, gọi basis4513–4581 nhưng không bao các SELECT display trước bằng một snapshot/lock chung. Cùng transaction dưới default READ COMMITTED không bảo đảm cùng snapshot.

Counterexample tĩnh: detail đã đọc mappingA đang mở; mappingV4 đóngA/mởB commit, ba source pointers vẫn giữ; query521 tạo tokenB. Response có thể mang displayA cùng tokenB. FILE615–616 + SQL4623–4630 nhận ba pointers cũ còn đúng và tokenB hiện hành, nên current-basis guard không chứng minh token thuộc chính dữ liệu user vừa xem. Không claim đã actual race, sai core/tiền hoặc leak. Đây cùng finding preview-coherence của root interim/migration peer; chỉ tính một lỗi. Interim gọi P1; final đánh P2 theo tác động evidence/read model, vẫn là gap so với handoff03§4.

Sửa hữu hạn: lấy display graph và token từ cùng một statement/snapshot, hoặc đặt một snapshot đọc nhất quán bao toàn bộ SELECT detail trước đọc đầu tiên. Giữ FILE current-rights/current-period/full-basis guards riêng tại thời điểm action. Regression cần positive không mutation và interleave có observer: mappingA được đọc → V4B commit → detail phải trả toànA+tokenA hoặc toànB+tokenB; không displayA+tokenB. Không dùng kiểm tra chỉ có token hoặc sleep/barrier làm bằng chứng đóng lỗi.

## Closure về cấu trúc, chưa gọi runtime PASS

- **Bootstrap alias/dict-row:** `crm_khoi_dong.py`153–160 có4alias riêng và so exact current_user=owner stage/typed/lo;166–175 đọc dict theo đúng khóa, tuple theo đúng số cột, lỗi shape có DataError. Endpoint/OID check120–123/150–151, app role guard126–143 và wiring server445–463 vẫn giữ. Không còn nguồn gây IndexError02 từ ba alias trùng. Actual correct-owner tuple/dict và wrong-owner controls vẫn phải đọc kết quả root chạy.
- **Final capture result normal/HOLD:** service264–310 giữ một configured owner connection/transaction xuyên current INTAKE→namespace/H→bytes/reader/history→stage→capture→typed/hold→finalize. Fresh309 gọi helper203–209 sau typed/hold; replay278–281/313–319 chỉ trả stored final `{stage_id,snapshot_moi,promote}`, không chạy lại reader/promote. Final SQL4302–4357 INVOKER kiểm actual table owner, stage/H/current actor+INTAKE, capture thật, snapshot mới/cũ, observation IDs hoặc candidate/impact/period HOLD; ghi một lần. Trigger3246–3263 chặn UPDATE/DELETE/ordinary writer;4735–4767 không cấp finalize cho app_web. Đây đóng nguyên nhân mất refs/HOLD ở SR02-1 về cấu trúc; chưa compare actual fresh/replay payload hoặc0delta.
- **Whole FILE basis/replay:** service607–616 nhận opaque DB token cùng expected pointers, preflight trước workbook/file/stage;627–632 bind token vào immutable stage/consumer. Final SQL4513–4581 gồm mapping/current mapping, selected content/observation/capture/bundle/roles/master/measurement/rows/eligibility/period/history. SQL4611–4614/4686–4689 giữ namespace→mapping share→logical→root lock; period/pointers/token4620–4630 và4691–4703 nằm trước cached receipt. Token vào requestH4632–4634 và registry/result4722–4728. Đây đóng service omission ba-pointer-only SR02-2; coherence SR03-1 còn riêng. Broad SQL race/catalog/direct-role acceptance do migration peer/root kiểm.
- **Workbook/old GET:** service635–702 ghi CO_SO và DONG_NGUON_CAPTURE cùng raw/native/NULL/issues; không làm tiền/tồn/L11. Download704–723 giữ M5+FILE current permission, exact `m5-xuat/<sha>.xlsx`, subroot, hash/length; old lo không bị rewrite theo basis mới. Formula/NULL/cell/provenance và exact oldbytes cần actual file controls; không gọi các sheet tồn tại là acceptance.
- **Inactive SOURCE_MAP getter:** final SQL3736–3745 dùng `ktt_nguon_duoc` cả target SOURCE_MAP trước/ở từng mapping row; predicate3104–3110 kiểm active actor+instance và exact profile/target. Cấu trúc manual-EXISTS-bỏ-active của SR02-3 đã sửa, vẫn giữ CFO SOURCE_MAP dương không cần INTAKE/READ_SOURCE. Runtime inactive/active controls chưa chạy bởi reviewer.
- **Seed/revocation/no M9:** CRM34–39/69–77 marker-or-existing DEMO rồi INSERT DO NOTHING; modules22–29 không M9. M5 seed145–171 bỏ qua toàn bộ actor/grant/source-cap creation nếu marker hoặc bất kỳ registry actor đã có; không restore quyền/cap đã thu hồi. Registry/mapping chỉ thêm hoặc conflict, không overwrite; seed hashes trùng02. Bootstrap205–206 gọi đúng CRM+M5 seed; final migration registry4772 là prefix1–12→COMMON13→M5 14. Không gọi/cài/cấp M9 trong các đường đã đọc. Historical byte/SQL checksum audit toàn file thuộc root/migration review, không suy từ một registry line.

## Giới hạn bằng chứng

Root thông báo17 pure tests PASS (`e13d17`); reviewer không chạy/đọc log để biến chúng thành kết quả PG. Tại lúc viết, PG03/HTTP/browser chưa có kết quả được giao cho reviewer. Không cộng PASS02 sang03 hoặc gọi các closure tĩnh là full M0/M5/33 acceptance. Cần actual normal/HOLD exact replay, current-cap revoke, FILE changed/full-basis/period/idempotency/cells, scoped positive+forgery negatives và coherent-preview observer controls trước nghiệm thu phạm vi tương ứng. M9 giữ dừng; M2 bridge/L11/tồn/kiểm kê không triển khai trong review này.
