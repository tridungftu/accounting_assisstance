# M0–M5 HTTP/UI — review độc lập candidate01

**19/10/2026 · CẦN SỬA / STATIC_ONLY / CHƯA NGHIỆM THU.** Actual CLI77423 terminal0, tool `6e1b6c`; root freeze `0509ca`,210files CLEAN, manifest SHA `c36773ae0b147665dab725b875c61dc7708037b23df806e5bb507079d2f2b89a`. Nguồn đọc là `var/codex-dieu-phoi/kiem-chung-20261018-101441/m0-m5-intake-ui01-handoff-20261019-155812-863-45941662/frozen`. Tác giả chỉ đọc/diff source+tests; không import/test/SQL/HTTP/GUI/CUA/node init. CLEAN scope không là runtime acceptance.

Căn cứ handoff SHA `868543441451eb7f8573f48bdcfa2cacd7d83e438f3a5f2088b7f5b42650030e`, SQL/fixture contract SHA `0ddb3aa17f0b34492905d3d2e89bcd9aadbe532e89d93bfe635063257754e957`, checklist12U private SHA `30db1c80e1b8d00e6ada3d0c42a25fceb27295d34cfac2928bc5e7756797c0d0`. Các4file UI/API final giữ nguyên hashes so interim đã đọc, nên I1–I5 dưới đây đã rebind final, không suy từ source cũ.

| Final file | SHA256 |
|---|---|
| `src/kho_tri_thuc/giao_dien/server.py` | ed54f39fa8a1b009ee5077caaa964c87e6c8cfc12719307059966763242daf2f |
| `src/kho_tri_thuc/giao_dien/assets/app.js` | cd9ea6995a69c7a14883251a9e0d56a24916980913ce8c27c15bcc11606856dc |
| `src/kho_tri_thuc/giao_dien/assets/index.html` | ea7db6b789e5e72d7d91193dbcfb9baf2a85ed26f3add87f89a6be56ba86905f |
| `src/kho_tri_thuc/giao_dien/assets/style.css` | 29a19358c8b3d87c5c88108eaeb0030f8697dceb1ffdf2422a16665c616631b0 |
| `tests/test_m5_http.py` | fa3e21e4ba9da10139eb657b0ea14e79103fa63f6e0e08eeade93a43d86339d3 |
| `src/kho_tri_thuc/k2/kho_so_luong.py` | 8d0faefb96abc6870d04e043998478d0476f8befee3687ac8a71cd0645df5f6f |
| `src/kho_tri_thuc/k2/nguon_chung.py` | c6260937677c9d21f160cb654987575f6364acddf5509c0a06a8b9b4f67e0723 |
| `src/kho_tri_thuc/k2/m5_demo.py` | 1b95653a076405e8b91dd11432511d0855f7cc32c918a7fafb535f923ffcbde4 |

## Findings cần sửa

**I1/P1 · U02/U05/U08 — actor/PN đổi nhưng response cũ vẫn render.** JS754–760 await detail rồi ghi global `m5ChiTiet`/mở box,788–792 ghi state/render, không epoch/actor/request guard. Đổi vai796→680 không clear selected/detail/raw/file DOM trước switch;719 chỉ hide detail khi load mới đã trả denied, không vô hiệu response cũ đang bay. Counterexample: KT_A slow detail PN_A hoàn tất sau khi đã chuyển KT_B/VIEW/M1-only và state mới render, mở lại PN_A data/buttons cũ. Backend reject request mới không loại response cũ. Cần clear cache/panels và bind/discard theo actor/source/PN epoch, positive current response vẫn render; kiểm delayed response có phối hợp, không chỉ nút disabled.

**I2/P2 · U03/U04 — reported errors bị đổi nghĩa trước capture H.** Server509 dùng `g("reported_errors") or []`; `nguon_chung.phong_bi_capture`117 lại `list(reported_errors or [])`. Null/false/0/empty scalar thành known-empty; nonempty string hoặc object có keys hợp regex thành array ký tự/keys. Payload malformed có thể được hash/capture/replay như claim khác thay reject400. Root chốt absent default[] hợp lệ nhưng **mọi present value phải là list đúng codes**, không boolean/coercion; validate trước H/artifact write tại HTTP lẫn common boundary. Positive[] và valid codes giữ canonical H; codes đổi phải ảnh hưởng H/409 đúng namespace, unknown Number vẫn capture được.

**I3/P2 · U02/U08 — M5 selector không phải8actor registry.** Server459 query mọi active `mo_phong`, JS705 hiển thị nguyên,493–496 đổi sang generic DEMO identity. `m5_demo.doc_registry`34–48 đã có trusted registry và kiểm8actor, nhưng handler không dùng allowlist đó. Khi preserved CRM/M1/M9 demo actors tồn tại, M5 selector thêm login ngoài8 đã chốt. Lọc chỉ selector/DEMO role-change M5 theo registry8, không xóa/reset old records/other selectors; service/DB vẫn current capabilities. Positive8 source-only/KT/CFO/VIEW/M1-negative phải đủ, không suy quyền từ suffix.

**I4/P1 · U07/U09 — file export UI/API chưa nối mutation receipt/expected graph; cùng root finding S09.** JS762 POST chỉ `{phieu_id}`; server515–516 gọi đúng signature hiện có `xuat_file_soat(me,phieu_id)` tại service548, không TypeError. Nhưng service552–592 đọc graph không khóa snapshot/expected token/operation key, viết artifact585 rồi INSERT lo587, không business receipt. Retry/click lặp hoặc concurrent review có thể sinh thêm file/lô hay snapshot không gắn preview. Sửa S09 phải bao gồm UI→handler→service key+expected graph/snapshot, lock/check/stage/receipt+registry cùng reviewed transaction; giữ immutable bytes/history. Positive same key+same graph→samefile/0newdelta; changed/stale/revoked action→conflict/deny trước mutation. Không riêng sửa signature để test qua.

**I5/P2 · U01/U03/U04 — thiếu đường nhận native/master file thực từ UI, root chốt REQUIRED.** Index104–105/JS710–717 chỉ sample buttons; branch server503–510 nhận native/master base64 có thật nhưng không có HTML file controls/source-profile/scope/coverage/errors/client-key form nối tới nó. Người có INTAKE không thể dùng UI nhận cặp actual artifacts hoặc retry cùng key; sample không thay luồng đó. Giữ sample và thêm file pickers cùng allowed source/profile/scope, coverage/error list và client key; đọc ArrayBuffer/FileReader→base64 **giữ nguyên bytes**, không JSON.parse/Number/reserialize. Server tự kiểm actual hash/length/role, không arbitrary path/URL; cross-source/unknown context/partial/NULL cases vẫn có candidate/HOLD. Đây là scope đã root xác nhận, không defer sang gói khác.

## Coverage tĩnh theo12U và giới hạn HTTP tests

U01/U03 có nav/page/API thật nhưng I5 chặn luồng artifact upload; U02/U08 có I1/I3. U04 reuse Host/Origin/token/cookie và body limits ở server583–605, GET724–741/POST853–856, nhưng I2 còn sai. U05/U06 có scoped list/detail/history/pointers/issues render; chưa runtime, stale UI I1 còn chặn. U07/U09 cần I4 và independent service/SQL guards; U10 explicit producer-unavailable/L11 dependency đã có JS731–736/index113, không tính tồn mới. U11 period/reopen/error behavior chưa chạy; U12 safe `node.textContent` reuse có trong code, không chứng minh DOM interaction/browser behavior. Tất cả runtime12U vẫn NOT_RUN.

Legitimate MAP target `phap_nhan` ở JS749 được server435–449 cho qua, trong khi actor/facts/`phap_nhan_id`/`PN` giả bị chặn; giữ positive này và BOTH source+targetPN/V4 ở service/DB, không blanket deny làm hỏng mapping. 409 adapter server530–533/883–887 có capture/idempotency/stale/mapping codes; actual error→HTTP mapping vẫn cần chạy sau source/SQL release. Raw URL JS700 khớp handler734–738; không khẳng định quyền/bytes từ chỉ route.

`test_m5_http.py` là **real local HTTP server + real PostgreSQL services**, không fake service: setup38–58 CREATE fresh DB/role, seed CRM+M5, LocalApp/LocalServer127.0.0.1 port0, http.client requests; `patch.dict` chỉ environment binding. Một monolithic `test_luong_http_m5`90–150, có subtests; fail sớm làm phần sau UNRUN. Skip guard35 nếu thiếu psycopg/DSN phải NOT_RUN, không PASS. Tác giả chưa chạy file này.

Test chỉ kiểm HTML chứa page ID/JS chứa m5Load (93/95), **không chạy JS/browser**, không phát hiện I1/I5; không kiểm selector exact8, mapping positive, actorB intake/CFOB/VIEW actions. Capture409 assertion110 chưa đo artifact/DB0delta; file130 chỉ ZIP signature+SHA, chưa cells/snapshot/idempotency/revoke. KTB list rỗng144 không có positive PN_B record counterpart. Cần controls theo findings+independent observer, không suy full12U từ một test xanh.

**Gate trước root chạy tests:** setup46 gọi `crm_demo.khoi_tao` trước M5 seed (root S10 đang review additive/noM9-grant),45/50 dựng DSN bằng URI string splitting và54 LocalApp dùng repo `cau_hinh.toml` thay self-contained config. Chỉ bind sau root review approved localhost test DB/ordinary-role/DEMO config; không đọc credential/config thật hoặc chạy blindly. Teardown61–67 giữ DB/role/temp, chỉ đóng đúng server/connections; không thấy cleanup delete. Đây là code inspection, không runtime-safety acceptance.

M9 service region trong server và M9 state/route/listeners trong JS, M9 HTML section được đối chiếu nguyên bytes với pre-M0 baseline; M5 callgraph không gọi `m9()`/VayK2. **Không có actual M9 execution được thực hiện trong review này.** Bootstrap/test seed qua CRM vẫn là S10 riêng, nên không suy “không M9 effects” chỉ từ UI diff; actual runtime còn cấm trước root release. Root sửa findings sau review riêng, giữ source apps/reader/fixtures/DTO/CRM records, rồi freeze/review/kiểm độc lập lại.
