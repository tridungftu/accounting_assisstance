# Review độc lập M9 service/nguồn — vòng 01

19/10/2026. **CHƯA ĐẠT / STATIC_REVIEW + ROOT_NARROW_PARSER_EVIDENCE.** Chưa phát hành M9 lên host. Tôi chỉ đọc source frozen, contracts, tests dưới dạng văn bản và kết quả probe được root cung cấp; không import/chạy product, test, SQL, HTTP, launcher, đọc credential/row thật hoặc xóa file. Kết quả coder tự báo không được tính thành kiểm chứng độc lập.

## 1. Baseline và phạm vi

Frozen `F = var/codex-dieu-phoi/kiem-chung-20261018-101441/m9-typed01-handoff-20261019-111048-752/frozen/`, 143 file, manifest SHA256 **`19c3476cb01fde17ec0382c16c3537813cec804b725e1bcd6eb730e5db8da276`**. Receipt handoff không cấp product/host execution; probe hẹp của root dùng release riêng ở §3. Các line dưới đây tính từ 1 trong frozen.

| Tệp / contract | SHA256 đã đọc/kiểm |
|---|---|
| `F/src/kho_tri_thuc/k2/vay.py` | `00996e3edadab00e311af5dcfb980f14f4faf5ef746e672338be857811a8ffbf` |
| `F/src/kho_tri_thuc/nguon/vay_9.py` | `2a27c076176713534c743bd0cbadfb4f7f866b3113045de7457e892a60a37c66` |
| `F/src/kho_tri_thuc/k2/lien_ket_chung.py` | `af185732ae46155733b28e8b347e40ac22378efd37f03b4384e049252027261b` |
| `F/src/kho_tri_thuc/k2/quyen.py` | `4ba17ed0d8667847f859b20264fd3c5f1006a6cd973e2407acc243e8319e88de` |
| `F/src/kho_tri_thuc/ha_tang/pg_migrations.py` — đọc phần liên quan | `2ee87c8437de6f5f2af9ded324d33a6b651f57ba3f5c48eef19938208013dfbb` |
| `F/src/kho_tri_thuc/giao_dien/server.py` — routes M9 | `f2a700522a3c9ead770afe2002e0edcfd2fee1eb7e22a9de9c365eaec72abf4b` |
| `docs/BINDING-M9-CORE-SAU-CRM03.md` | `28af9c1045c8da5448056baa45b679fd476f48aaa40d897ff92430764b168bc5` |
| `docs/THIET-KE-M9-TYPED-DEMO-33.md` | `e3e9704f5af808bc3c398a84ba85e3a80e0bc4b51c4042c1bda90fb73cfa9bf3` |
| `docs/GIAO-VIEC-BRIDGE-KHOAN-VAY-M9-33.md` | `fb8c5f00834520625217f999b2b45a12246fa958787dca4d2261b04bcaa5f946` |
| `docs/BAO-CAO-M9-TYPED-DEMO-33.md` | `720b000d1bbb870e1763962af855720c8c43aed5dcddb1c047680194779dbde1` |

Đã đọc toàn `vay.py`, `vay_9.py`, `lien_ket_chung.py`, `quyen.py`; đối chiếu các helper CRM `_tx/danh_tinh/_pn/_su_kien/_dong_viec`, các đoạn DDL manifest/eligibility/remaining, routes và test tương ứng. Không tuyên bố đã audit toàn bộ PostgreSQL migration/ACL/HTTP/UI. Root và reviewer SQL giữ phạm vi đó riêng.

## 2. Finding phải xử lý

### SV01 — P1: precision của nguồn được nâng thành PROVEN chỉ từ hình dạng payload

**Vị trí:** `nguon/vay_9.py:48–53,83–114,117–144`; `k2/vay.py:383–392`.

`tien` coi mọi text đúng định dạng là exact proven, JSON integer trong safe-int là proven, Decimal có tối đa 15 significant digits là proven; rate/FX cũng dùng tiêu chí độ dài chữ số. Profile native thật được gắn một `DEMO_M9_PRECISION_V1` tổng quát. Không có binding theo field + đường nhập/ghi/export + bằng chứng số gốc đã được review. `precision_fields` lưu duy nhất mức tổng `{"vay": ...}` chứ không giữ encoding/proof từng field.

**Phản ví dụ:** payload native `1`, `0.10` USD hoặc rate `7` vẫn có thể là kết quả sau mất phần lẻ/chữ số tại nguồn; text `"9007199254740992"` sinh sau Number cũng không tự thành exact-original. Safe-int/Decimal/hash chứng minh payload nhận được, không chứng minh đầu vào gốc. Contract nguồn §3.1 và design §2 yêu cầu unknown/lost giữ chờ; không cho mượn proof của fixture text hoặc registry.

**Bằng chứng root:** probe02 N01–N04 đều FAIL đúng lỗi tự nâng `PROVEN`; xem §3. S10 giá trị lớn đã làm tròn được giữ UNPROVEN riêng không khép lỗ hổng này.

**Sửa / nghiệm thu:** tách profile text exact có chứng cứ khỏi native Number; pin per-field encoding/contract/version/hash/bằng chứng đường nguồn. Không có chứng cứ → UNPROVEN và ineligible. Positive native DEMO chỉ dùng contract giả định minh bạch do root review, không đổi nghĩa nguồn thật; S09 text-int64 vẫn hợp lệ. Kiểm cả tiền, rate, FX và event parts; không thêm oracle original của S10 vào request/profile để làm proof.

### SV02 — P1: child mơ hồ công ty bị lọc khỏi graph thay vì chặn các aggregate liên quan

**Vị trí:** `nguon/vay_9.py:284–317,339–354,376–384`; `pg_migrations.py:2405–2434`.

`_gan_cong_ty` đánh dấu đúng `AMBIGUOUS_COMPANY` khi hai công ty có cùng `maKV`, nhưng child này có `company_key=None`. `do_thi` lọc theo tập công ty của PN ở line341 trước khi gắn blocker; chỉ nhánh rate có bù riêng cho child không có công ty ở line417. Root loan của từng công ty vẫn có thể có `blockers` rỗng và graph không draw/lịch. Validator DB chỉ kiểm các row đã được đưa vào graph, không đối chiếu child nguồn còn unresolved.

**Phản ví dụ:** hai `DaiHan` công ty A/B cùng `maKV=KV`, một child KheUoc/LichTraGoc chỉ có `maKV=KV`. Cần giữ cả graph liên quan chờ disambiguation; hiện child bị bỏ khỏi cả hai trong khi parent nhìn hợp lệ. Không phải cross-PN FK đã đủ bảo vệ: child bị mất trước khi tạo FK.

**Bằng chứng root:** probe02 P08 xác nhận child mơ hồ vẫn ở snapshot; N05 FAIL vì cả hai parent không có blocker. Việc DB thực sự approve trường hợp này chưa chạy và không được ghi là runtime PASS/FAIL SQL.

**Sửa / nghiệm thu:** lập index unresolved-child → toàn bộ possible parent source identities trước khi PN filter; gắn blocker và giữ locator/source reference. Kiểm lại ở domain validator với source coverage, không chỉ kiểm row đã insert. Có positive hai namespace thực sự phân biệt được; child thiếu disambiguation phải chặn đúng lý do, không gán theo actor/row order.

### SV03 — P1: quyết định LOAN/DRAW loại cả tầng lịch và có thể mở lại capacity khi đổi scope

**Vị trí:** `k2/vay.py:323–332,414–430,456–472`; `nguon/vay_9.py:400–403`; `pg_migrations.py:2430–2432,2716–2731`.

Quyết định chỉ lưu `DUNG_DRAW|DUNG_LOAN`, được tái dùng cho mọi revision. Service bỏ **mọi** dòng GOC của tầng còn lại, không bind cùng kỳ/coverage/nhóm phần được quyết định. Giá trị bị bỏ không nằm trong typed revision digest; chỉ danh sách key bị bỏ được giữ. DB chỉ phát hiện đồng thời có LOAN GOC và DRAW GOC sau lọc.

**Phản ví dụ A — mất nghĩa vụ:** nguồn có LOAN kỳ1 và DRAW kỳ1 cùng coverage, đồng thời LOAN kỳ2 độc lập. Chọn DRAW để giải quyết overlap kỳ1 làm mất cả LOAN kỳ2. Revision sau thêm kỳ LOAN độc lập cũng bị quyết định cũ loại mà không có review mới.

**Phản ví dụ B — tiêu thụ lại:** cùng nghĩa vụ kinh tế LOAN100/DRAW100, đã chọn DRAW và nối70. Đổi sang LOAN tạo key `OBL:<alias>:LOAN/-/1/GOC` khác key DRAW cũ. SUM consumption chỉ theo `logical_target_id`; không có impact/conservation gate trong approve cho các nghĩa vụ bị bỏ. LOAN mới có capacity100 trong khi70 vẫn nằm ở target DRAW cũ. Đây là counterexample tĩnh; chưa chạy SQL để khẳng định giao dịch cuối được commit.

**Sửa / nghiệm thu:** quyết định phải là typed revision có exact source/coverage/period/member pins và nằm trong graph được kiểm/duyệt; giữ các kỳ không overlap. Scope change sau consumption phải hold impact hoặc có crosswalk canonical economic obligation bảo toàn consumption, không tạo capacity mới bằng quyết định trình bày. Bổ sung positive kỳ độc lập, negative stale decision, same-coverage switch sau đã nối70, và thật sự khác financial identity phải vẫn có positive riêng.

### SV04 — P1: `biet_den` chưa tạo được as-of view và provenance bảng lãi bị gán thời gian của native snapshot cũ

**Vị trí:** `k2/vay.py:246–253,428–430,814–875,886–934`; `k2/lien_ket_chung.py:55–58`; `pg_migrations.py:1280–1284,2452–2455,2722–2731,2754–2769`.

`_chi_tiet_hd` chỉ lọc `p.tao_luc <= biet_den`. Chọn effective PB, capacity và consumed không nhận knowledge cutoff; rates/children không lọc first-known/recorded time. Danh sách snapshot/mapping/BANK/link/file/work cũng là trạng thái hiện tại. Mặt khác `_lap` lấy BangLai mới nhất nhưng lịch LAI/PHI lại ghi `known_at_server` của native snapshot `s`, thay vì provenance BangLai `bl`.

**Phản ví dụ:** PB tạo t0, child/rate hoặc CFO approval ở t2, query `biet_den=t1` với t0<t1<t2 vẫn trả các fact/approval mới trên PB đó. Một allocation sau cutoff vẫn làm giảm remaining trong view trước cutoff. BangLai mới biết t2 gắn vào native nhận t0 thì row lịch mang first-known t0 không đúng nguồn. Source rate có effective date trước cutoff không làm nguồn đó được biết sớm hơn.

**Sửa / nghiệm thu:** bind valid-time + knowledge-cutoff cho source facts, approval/decision và budget/history theo semantics đã chốt; không dùng current status hay PB-created-time thay knowledge state. Row BangLai pin own snapshot/row/first-known và derivative của nó. S06 cần một positive thực sự eligible ở later cutoff và bị loại ở earlier cutoff cùng valid date; hai view rỗng hoặc draft chưa eligible không chứng minh gate.

### SV05 — P2: event không đổi không có membership trong graph mới; gợi ý đọc cả event ở phiên chưa được duyệt

**Vị trí:** `k2/vay.py:431–445,719–733,843–847`; `pg_migrations.py:2382–2390,2411–2434`; `nguon/vay_9.py:407–412`.

Service bỏ INSERT event nếu latest payload cùng hash, kể cả event thuộc PB cũ chưa được duyệt/đã thay. Manifest và chi tiết PB mới chỉ lấy event có `hop_dong_phien_ban_id = PB mới`, nên không có membership/reference tới event được tái dùng. `goi_y_noi` lại tìm latest event toàn alias, không ràng buộc event thuộc effective approved graph, không lọc state/precision/known-time. Event parts UNPROVEN không được validator kiểm cùng draws/rates/lịch; parse error mới đổi `XUNG_DOT`.

**Phản ví dụ:** PB1 chứa E, sau đó PB2 thay fact khác nhưng E không đổi. PB2 được check trên manifest thiếu E; màn hình PB2 cũng mất E. Gợi ý vẫn kéo E từ PB1. Nếu E ở graph chờ/conflict hoặc part precision chưa chứng minh thì không có bước gate tương ứng. Đây chưa phải bằng chứng tự ghi sai tiền: confirm còn kiểm BANK và obligation capacity, nhưng provenance/approval của căn cứ gợi ý không đạt wholegraph contract.

**Sửa / nghiệm thu:** giữ event identity/revision một lần, thêm graph membership typed để PB mới pin revision cụ thể, không nhân event hoặc bỏ khỏi manifest. Gợi ý chỉ đọc revision được graph nguồn có quyền và đủ điều kiện cho phép, trả holding reason cho precision/orphan/conflict/late-known. Thêm unknown `maKheUoc` phải giữ unresolved, không `ku_id.get(...)` thành loan-level im lặng.

### SV06 — P2: concurrent same-key retry không được đọc lại receipt sau khi lấy lock

**Vị trí:** `k2/vay.py:645–659,679–697`; `k2/lien_ket_chung.py:24–42`.

Confirm/undo đọc receipt trước HĐ→BANK lock. Sau khi chờ lock không reread receipt. Hai connection cùng key + cùng request đều có thể đọc chưa tồn tại; request thứ nhất commit, request thứ hai tiếp tục và bị stale preview / `LIEN_KET_DA_HUY` thay vì nhận receipt cũ. Unique key và budget còn giúp ngăn ghi lặp; finding này là contract retry/concurrency, không tuyên bố double allocation.

**Sửa / nghiệm thu:** kiểm quyền trước replay; sau khi khóa đúng namespace/aggregate đọc lại receipt rồi mới đánh giá preview/state. Cùng key khác payload vẫn409. Chạy thật hai request chồng lấn, cả confirm và undo, cả hai winner order, so receipt IDs/counts và tombstone không reactivation; timeout/exception ngẫu nhiên không là pass.

## 3. Bằng chứng độc lập root đã có, giới hạn chính xác

Root đã chạy **probe parser hẹp revision2**, tôi đọc kết quả `var/codex-dieu-phoi/m9-root-parser-result-1792383339624832100/result.json`: **13 criterion, 8 PASS / 5 FAIL**, 0 SQL / 0 HTTP / 0 host. Source143 và corpus18 hash không đổi, guard bật, no bytecode. Probe SHA256 `a00866a97d8ef9cd6ae8dcb06a7edd722b563a10a06e641938d0f2ca7a10efc4`; release `76aa626accced4affa2276082cbbe193bc07f7a881b0003b1b0767de250d4f78`; corpus manifest `80baa534b9c0e7740d7cebad0c896ccc424a14214bfc59bc1f0972d8157288ee`.

PASS hẹp: typed exact-text int64 `9007199254740993`, NULL khác0, bool bị từ chối, native shape một loan/hai draw/ba rate/hai lịch, snapshot nhận diện child mơ hồ, S10 draw lớn giữ UNPROVEN, S14 profile root bị từ chối. Các PASS typed không tự chứng minh source encoding/provenance hoặc nghiệp vụ SQL/API/file.

FAIL: N01 native integer không proof; N02 native decimal không proof; N03 native rate không proof; N04 native graph tự PROVEN; N05 child mơ hồ không chặn hai parent. Bốn FAIL precision quy về SV01; một FAIL ambiguity quy về SV02, không nhân thành năm bug độc lập.

Probe01 có lỗi harness nhầm field S10 loan-header thay vì actual draw; artifact được giữ, probe02 chỉ sửa field mapping. Không tính lỗi đó thành product failure. Corpus19 chưa chạy đầy đủ; S18 vẫn là inventory gap không có runtime input.

## 4. Điểm có hướng đúng và các giới hạn còn lại

- Raw được ghi trước parse, snapshot có stable instance/profile/raw key; row giữ locator và source-company; có mapping V4, impact khi đóng, alias không chứa financing kind/PN đích. Parser dùng exact JSON/Decimal helper, giữ NULL/zero và không tạo M1 BANK từ source event.
- Dùng chung HĐ/PB/lich_tra_no, identity/session/audit, common BANK budgets và child allocations; preview nêu cả BANK và target capacity. Service check quyền M9+M1 trước receipt replay; confirm tính lại sau HĐ→BANK lock. Các điểm này là nhận xét source, không thay kiểm direct SQL/race.
- Dated evidence `HO_SO_VAY` không tạo khi không có ngày nguồn; không viết ngày ký HĐ giả. Số tiền API/file chuyển string; download kiểm quyền, path containment và bytes hash. Host/actual workbook cần root kiểm riêng.
- Derivative hiện là JSON chỉ chứa raw/profile/PN + sorted row hashes/mapping pins (`vay.py:269–286`), thiếu exact selected rows/locators/source-instance như binding §3. Không được gọi đây là derivative self-contained đã đạt full M0. Root nên đưa vào vòng sửa/provenance review cùng membership BangLai; việc dùng cùng immutable writer chưa tự chứng minh common artifact contract.
- HTTP chỉ có `mau` cho intake fixture, service `nhan_tep` chưa có route upload raw/instance selector. Vì vậy không báo corpus private/namespace/custom input đã chạy HTTP qua endpoint hiện có. API/UI/host binding do root xử lý.
- Không có kiểm chứng ở review này cho full period/lô protection, toàn bộ ordinary-role ACL/RLS, money proof DIRECT/CHILD, migration prefix, crash/restart/GUI hoặc toàn M9/M0–M10. Gap C4d/bảo lãnh/LC thanh toán/L7/L12/policy vẫn là công việc phải hoàn thiện, không loại khỏi mục tiêu.

## 5. Điều kiện giao sửa và kiểm lại

Giữ nguyên frozen143 và toàn bộ evidence hiện có; root giao cùng Claude session các SV01–SV06 cùng finding SQL/HTTP khác. Không đổi independent expected/corpus để theo implementation. Sau coder terminal mới freeze toàn bộ source lại, bind thực tế SQL/service/HTTP và cấp release riêng; thứ tự kiểm: precision/source graph → scope/canonical consumption → known-time → event membership → concurrent receipt → common money/protected workflow/API/file/host. Mọi trường hợp không chạy hoặc setup chưa đủ tiếp tục NOT_VERIFIED, không suy từ coder selftest hay số lượng test PASS.
