# M9 K2 — review độc lập tĩnh 01

**19/10/2026 — STATIC_REVIEW / REPAIR_REQUIRED / NOT_RUNTIME_ACCEPTANCE.** Coder terminal88862 exit0 không thay nghiệm thu. F = `var/codex-dieu-phoi/kiem-chung-20261018-101441/m9-typed01-handoff-20261019-111048-752/frozen/`; whole143 manifest SHA256 `19c3476cb01fde17ec0382c16c3537813cec804b725e1bcd6eb730e5db8da276`. Đọc các SQL/helper/permission/consumer được dẫn bên dưới, accepted M9 binding SHA256 `28af9c1045c8da5448056baa45b679fd476f48aaa40d897ff92430764b168bc5`, reviewed PLAN SHA256 `5925a37880bd50eb23e8b951d1ee7aca622ad93ad9a5c50aad507ae48eec290f`. Không import/chạy product/test/SQL/HTTP/launcher, kết nối DB, đọc credential/real rows/source apps hoặc xóa file.

`F/src/kho_tri_thuc/ha_tang/pg_migrations.py` SHA256 **`2ee87c8437de6f5f2af9ded324d33a6b651f57ba3f5c48eef19938208013dfbb`**; mọi SQL line dưới đây ở file này. `F/src/kho_tri_thuc/k2/quyen.py` SHA256 `4ba17ed0d8667847f859b20264fd3c5f1006a6cd973e2407acc243e8319e88de`; `k2/lien_ket_chung.py` `af185732ae46155733b28e8b347e40ac22378efd37f03b4384e049252027261b`; `k2/crm.py` `71027f1df9959d352d2b69594fb76794c8602a091bce61209c0b7dd5511acb9c`; `k2/vay.py` `00996e3edadab00e311af5dcfb980f14f4faf5ef746e672338be857811a8ffbf`.

**Kết luận:5 finding P1 cần sửa trước release schema/money/approval; source evidence là static counterexample, chưa phải SQL exploit đã chạy.** Báo cáo coder ghi DIRECT không cần proof là gap đã nhận biết, không phải ngoại lệ được accepted binding cho phép. Root review parser/service/UI riêng, không cộng vào kết luận này.

## R1 · P1 — CRM DIRECT vẫn nhận tiền chưa có proof hoặc proof đã lệch

**Neo:** SQL2938–2969 kiểm DIRECT bằng BANK amount/currency và sums, không đọc encoding proof; đối lập CHILD2856–2862 bắt PROVEN+digest+currency-scale. Wrapper2734–2752 có thể trả `KHONG_CO_PROOF_TIEN/PROOF_TIEN_LECH` nhưng không nằm trên DIRECT write path. `F/src/kho_tri_thuc/k2/crm.py:583–623` cũng không gọi proof wrapper trước INSERT; việc API nạp M1 mới có thể gắn proof không bảo vệ legacy/direct SQL.

**Counterexample:** BANK VND integer10000 không có encoding proof, CRM approved schedule10000, KT đúng quyền nối DIRECT1000: scalar money/target checks đều đạt. Sau verifier gắn proof hợp lệ, sửa amount trên bản DEMO làm digest lệch; DIRECT mới vẫn chỉ kiểm số/currency hiện tại và có thể tiêu thêm, trong khi CHILD bị chặn. Binding§9.R4 đòi proof của chính BANK trước eligible allocation, không suy scale0 từ VND/registry.

**Sửa/control:** cùng common proof/encoding/legacy-unclassified eligibility cho mọi MONEY consumer tại DB trước write/replay phù hợp; preserve old links/IDs/tombstones, legacy thiếu proof giữ blocked/task. Positive cùng BANK có verified proof hợp lệ phải nối DIRECT và CHILD được; missing/UNPROVEN/LOST/tamper/scale mismatch phải reject0businessdelta. Owner observer tính DIRECT+effective CHILD một lần, không lấy wrapper tự báo số làm oracle duy nhất.

## R2 · P1 — SQL APPROVE không giữ aggregate lock với typed child mutation

**Neo:** typed INSERT `_M9_KIEM_GHI`1712–1721 khóa HĐ, trigger2283–2358 đọc PB CHO_DUYET ở2313–2317. Nhưng SQL `phien_ban_kiem_duyet`2469–2574 chỉ đọc HĐ ở2476, không FOR UPDATE/prelock; digest2506 và eligibility2528 không cùng parent lock. Service `F/src/kho_tri_thuc/k2/vay.py:475–491,508–537` có HĐ prelock, không thay DB boundary cho ordinary SQL được grant UPDATE ở1153.

**Counterexample:** đã CHECKG0/D0 bằng KT, V4 đã giải quyết. TransactionKT INSERT một child hợp lệ làm manifestG1, giữ HĐ lock và chưa commit. Ordinary CFO dùng exact approval UPDATE của service ở`vay.py:529–530`: trigger không chờ HĐ, nhìn committedG0 và có thể approveD0; KT commit sau đó→approvedG1/D0. Reverse order cũng có khoảng approval giữ PB row trong khi child thấy old CHO_DUYET. FK/row locks riêng không chứng minh aggregate serialization.

**Sửa/control:** DB-authoritative mutation/check/approve wrappers hoặc cơ chế tương đương lấy HĐ trước child/PB row, thu hẹp direct DML nếu không bảo đảm prelock; không client GUC flag. APPROVE đọc lại graph/eligibility/expected checked digest dưới lock. SG08 hai APPROVE winner orders bằng2ordinary PG connections+owner read-only observer: mutation-first→oldD0approve bị stale reject; approve-first→không append child vào protectedG0. Valid newly supplied source-backed child positive, CHECK và APPROVE positives phải đạt; G0/G1 facts độc lập, không chỉ stored digest. Không lấy timing, deadlock, timeout hay mutation sai nguồn làm proof.

## R3 · P1 — viewer M9 có thể sửa dữ liệu PB draft bằng ordinary SQL

**Neo:** app_web SELECT/INSERT/UPDATE PB được grant1153; RLS1661 chỉ PN/module. Trong VAY trigger, identity tuple2499–2501 không chứa `tham_so/so_phu_luc/ngay/tep_goc_id/chung_tu_id`; role/action chỉ được xét khi check/state thay đổi2507–2541. Giữ CHO_DUYET và check fields cũ sẽ tới RETURN2543 mà không kiểm WRITE_DRAFT. Service `k2/quyen.py:28–39,70–81` phân viewer/KT/CFO đúng ý, nhưng không bảo vệ direct SQL này.

**Counterexample:** actor XEM có PN_A+M9, login app_web thường, UPDATE `master.hop_dong_phien_ban SET tham_so=... WHERE id=draft_A`; không đổi owner/check/state nên RLS cho phạm vi và trigger không từ chối vai. Cùng người có nhiều module cũng không được dùng RLS như action delegation.

**Sửa/control:** DB action gate cho toàn bộ fact edit của draft, OLD+NEW typed parent/owner/subject, invalidation/audit; hoặc revoke direct write và chỉ cấp wrapper đúng action. Viewer negative0delta, KT WRITE_DRAFT positive, KT/CFO CHECK/APPROVE/V4 tách, wrongPN/module negative; giữ CRM authorized positive để không sửa bằng blanket-deny mọi PB.

## R4 · P1 — full source graph eligibility vẫn chỉ kiểm các child đã được chèn

**Neo:** root typed2080–2122 chứa `precision_status/blockers/mapping_pin` mà app có INSERT2979–2980. `m9_kiem_do_thi_noi_bo`2397–2439 kiểm exactly1root, v.blockers và các rows đang có; không đối chiếu required source graph/coverage/profile/known mapping với snapshot declared children. Source row state2411–2414 còn không bao events/event parts. Manifest2364–2390 hash graph được chèn và row hashes, không tự chứng minh graph đủ; chỉ root INSERT2323–2325 đối chiếu snapshot membership, child source FKs như2176 chủ yếu samePN.

**Counterexample:** source native_v6 đã có draws/rates/schedules, map/proof hợp lệ. KT lập PB mới cùng alias/source root, giữ PROVEN và blockers rỗng nhưng không chèn các child mà source đã khai: các EXISTS child validation đều false, digest khớp graph thiếu vẫn không tạo blocker. Hoặc samePN child nhận source row từ snapshot/semantic parent khác nhưng validation_state HOP_LE. Đây là missing DB derivation/coverage, không thể sửa chỉ thêm một stored blocker do service tự khai.

**Sửa/control:** authoritative typed source→graph correspondence/required coverage/precision/basis/profile/mapping/known eligibility tại DB và cùng service, exact parent+snapshot/source-row tuples; missing evidence giữ holding, không fake facts. Positive complete source-backed graph đạt; omit từng required draw/rate/schedule/event, samePN wrongsource/parent và mismatched precision/coverage phải blocked ngay cả supplied empty blockers/PROVEN và digest khớp. Independent source fact oracle phải khác builder/validator; parser ambiguity/correction do review service riêng.

## R5 · P1 — target key còn do caller chọn nên có thể mở lại capacity của cùng draw

**Neo:** target2136–2152 chỉ UNIQUE(PN,module,logical_key), không unique/canonical resolver cho typed anchor GIAI_NGAN(khe_uoc) hoặc nghĩa vụ(HĐ/scope/key/component). `logical_key` free text. Trigger2349–2352 chỉ kiểm draw cùng HĐ; draw revision2330–2334 chỉ kiểm target_kind+same khe_uoc, không continuity với old target. Sức chứa2722–2731 lấy revision hiệu lực theo target, consumption2716–2720 SUM theo target UUID; validator2397–2439 không phát hiện alias target cùng anchor.

**Counterexample:** same draw identityKU1 có targetX1 capacity60M, đã tiêu60M. KT ordinary SQL INSERT X2 cùngHĐ/KU1/GIAI_NGAN nhưng logical_key khác; PB mới cùng drawKU1 trỏX2 thỏa existing parent guards/unique(draw,PB). Sau CHECK/APPROVE, X2 capacity60M và consumption0 dù cùng financial event. Service `_dich` ổn định không bảo vệ canonical identity tại DB; key không chứa PB trong service chưa đủ.

**Sửa/control:** DB canonical target resolver/cardinality từ confirmed typed financial identity trước create/claim, UNIQUE anchors có scope đúng và exact FK/revision continuity; không blanket unique cấm financial events thật sự khác có nguồn. NewPB/rate/basis của cùng draw phải reuseX1, paid60M giữ nguyên; different genuine draw positiveX2. Capacity decrease dưới consumed holding/impact, increase có căn cứ vẫn trừ old use. Không kết luận CRM doublecapacity chỉ vì common child SUM chưa có DIRECT projection: CRM đang có `master.da_lien_ket(HĐ,khoa_nghia_vu)` riêng cần controls crossrevision cụ thể khi rebase common consumer.

## Điểm giữ và giới hạn

Static text prefix definitions M0001–M0012 cùng helper generators trong frozen CRM06 SHA`31f25277b5e08a0f54843191bce2b3e54126dc6770ad02ece310c8265fcac1e5` khớp **exact103023characters** tới trước PG_MIGRATIONS của baseline; final chỉ thêm M0013/helper mới và append tuple2994. Chưa serialize generated statements/import hoặc kiểm DB history/checksum/applied_at: MG01/MG02 vẫn NOT_RUN, không dùng exact-prefix thay bằng chứng upgrade retained data.

Các control có thật cần giữ khi sửa: domain dispatch/RLS1660–1679; immutable owner/document/work/link và typed children; proof immutable2603–2640; parent CHILD exact effective sum2772–2811; BANK aggregate2711–2714 tính DIRECT parent một lần+CHILD một lần; HĐ→BANK→target ở child INSERT2832–2835; parent/child tombstones không resurrect. Chúng không bù5gaps trên. UPDATE child HUY2818–2830 và parent UPDATE2876–2895 còn trở về trước insert lock path; review repair phải bind UNDO/action/protected period/OLD+NEW under same common protocol, không suy toàn protected graph đã covered.

Đã chuẩn bị private `var/codex-dieu-phoi/m9-independent-review01/narrow-final01/` cho proof mode và SG08 scaffold. Release template mọi capability=false; **chưa chạy, chưa syntax/runtime verified**. SG08 bị hard-block trước product import vì cần bind newly supplied valid source mutation/G0G1; không dùng rate/date tự chế từ old source row làm positive. Probe chưa thay runner/release root, không trì hoãn repair. Sau code sửa phải terminal/freeze/rebase/review mới; mọi criterion hiện NOT_RUN,0SQL/0newpass.
