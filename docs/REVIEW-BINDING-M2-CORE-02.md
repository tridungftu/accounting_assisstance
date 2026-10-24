# Review độc lập binding M2/core — 02, sau amendment R1–R5

**19/10/2026 — STATIC_ONLY / CONTRACT_RECHECK / M2_NOT_IMPLEMENTED.** Đã đọc toàn bộ289dòng binding M2 SHA256 `001aefc2d7cb8e9d0b6017325c465c2f536962b56331d3ef08c44b3388c0eea2` và review01 SHA256 `3c7325403345a109dfcc8c5ed8c86a2c5c05f4cbc724f244aa288c57b7bbdaed`. Giữ nguyên review01/binding/product; không import/chạy product/tests/SQL/HTTP/host, không đọc source ngoài/rows thật/secrets, không xóa gì.

**Kết luận:** **R1–R5 được đóng ở mức contract tài liệu,5/5**. Chưa thấy **blocking gap M2 mới độc lập** trong bản này. Có thể dùng làm nội dung handoff sau root review và rebase các dependency dưới đây; đây không phải nghiệm thu DDL/runtime hoặc cho phép bỏ các ca âm/race.

## Matrix closure

| Finding review01 | Neo binding cuối | Vì sao đóng ở mức contract / gate còn phải chứng minh |
|---|---|---|
| R1 — cùng nguồn tạo nhiều event/GOC | §9.R1 dòng187–204; bảng191–198; API271; ca279–280 | Stable source component→slot/approved partition→source-use **trước** event, không khóa theo event_key client chọn. WHOLE/SINGLE chỉ một event; decomposition có equality tổng capacity và giữ consumption xuyên revision/alias. M2/M4/legacy dùng cùng DB function/lock; chưa crosswalk legacy thì hold. Ca hai event keys/two connections, M2↔M4, positive nhiều components thật đã được ghi rõ. Không còn dựa riêng partial UNIQUE GOC sau event. |
| R2 — cùng correction ghi delta hai lần | §9.R2 dòng208–220; ca281–282 | Canonical economic change độc lập receipt/policy/PB; UNIQUE(event,component,change), active-attempt guard và consumed tombstone sau protection. Predecessor head + partial unique chống fork **từ lúc reserve**, không chỉ export; change kế tiếp thật được xử lý, không UNIQUE(goc_id) quá rộng. Claim/transition/scope cùng component và signed correction vector tại R3. |
| R3 — cân và ≤nguồn vẫn thiếu coverage | §9.R3 dòng224–236; bảng62; ca283–284 | Scope FULL/PARTIAL/correction có căn cứ trước, FULL server enumerate đủ source; lineage set equality, mỗi scope channel và posting line đều conservation exact; counterpart PAYABLE theo basis. NET route/account/dimensions pin đúng, header VAT không bịa phân dòng. FULL10m chỉ post4m bị chặn; PARTIAL4m cần scope đã xác nhận và residual6m theo dõi. Unsupported/KHO trong FULL vẫn blocker, không journal giá trị kho hoặc bỏ phần thiếu. |
| R4 — immutable snapshot xung đột route cache | dòng54–60; §9.R4 dòng240–242; ca285 | Không UPDATE source `chung_tu_dong.dich`; view `mua_dong_hien_hanh` + typed DTO lấy route có version. Source PK/hash/quantity/amount bất biến; route đổi invalidate scope/check, protected file/route refs giữ. Vì đã chọn view/join nên không còn hai lựa chọn cache gây mâu thuẫn. |
| R5 — FK cùng PN chưa giữ đúng identity/PB; REQUEST_ALIAS thiếu target | §9.R5 dòng246–261; ca286 | NULL-pair và MATCH SIMPLE đúng cho observation; composite identity/PB/line/route/component/slot/claim/RQ/obligation tuples được liệt kê. REQUEST_ALIAS thêm typed rq_id vào common mapping, exactly-one kind target, source key không gồm target PN; approved interval/retarget/consumption guard dùng cùng M9. Không còn RQ UUID trong hop_dong_id/JSON hoặc identityA+PB_B chỉ vì cùng PN. |

## Đối chiếu core thực tế, không suy contract đã được cài

Baseline frozen03 CLI89659/manifest121 `82e5e26806e05ef732536fcb0e474ab6ee96f646566e335e728da28921f47c3a`. Đã đối chiếu hash **actual=frozen** các file kỹ thuật sau; chỉ đọc source:

| File actual/frozen | SHA256 / neo đã đọc |
|---|---|
| `ha_tang/pg_migrations.py` | `31f25277b5e08a0f54843191bce2b3e54126dc6770ad02ece310c8265fcac1e5`; dòng207–259 core chứng từ/dòng,501–549 proposal,742–753 protected-line trigger,837–893 V1 balance/catalog/period,1182–1183 module dispatch,1455–1494 generic link |
| `de_xuat/engine.py` | `2df748ba483b795adaf2c5b0bb7cf45ae789cd6965dd30fdf8ada4e912d993fc`; dòng1030–1056 NET header account và fallback header source |
| `giao_dien/quick.py` | `5cfa91a10e925f75a0decaf29103f06f82866f7a1001adf0a003a2dd077fc9c8`; dòng1176–1212 fallback net=total/tax0 và header overwrite NET/dimensions |
| `nguon/that.py` | `f7330761f1ef8dbbcdc49429a09919f6135001dd0a50d804e6212af3de0ff1fc`; dòng689–747 parser currency default/rounding/STT fallback/GOODS và chưa typed qty/UOM/unitprice |
| `k2/quyen.py` | `5aa03556789214a18df028866cdb64df67eae09aa784772ce654984d3d21c737`; action map CRM/M1 hiện có, chưa actions M2 |
| `tools/chuyen_sqlite_sang_pg.py` | `97c577768014e6139a2270d02551f5e1863b686c4b103581bfea2e411532a19c`; dòng279–297 chỉ chiếu JOURNAL/BANK |

Như vậy binding dòng15–21/33/48/60/131–137 và §9 mô tả đúng phần cần **thêm/thay đường typed**: promoter HD_MUA/HD_BAN mới, giữ nguồn exact, route→posting lineage thay overwrite, domain guard ngoài balance, module/actions/RLS mới, common money dispatch. Không có source evidence rằng M2 typed/registry/claim/FK/functions đã tồn tại hoặc đã pass. Parity legacy, engine cũ cân Nợ=Có hoặc current M12 scoped CRM helper không thay những gate mới này.

## Dependency/handoff còn mở, không nâng thành finding M2 mới

1. **Common M9 final:** giữ binding amended `28af9c1045c8da5448056baa45b679fd476f48aaa40d897ff92430764b168bc5`, một money remaining/target/receipt/lock protocol và immutable BANK encoding proof. M2 phải rebase manifest sau core05/M9 terminal/freeze, không giữ migration number trước hoặc sửa M0001–M0012. M9 approval ở root và wording “cần root review” trong M2 là trạng thái handoff cần cập nhật, không một DDL defect mới.
2. **M5 quantity/shared observation:** M2 hiện pin M5 `33488e31…c92a8c`; review M5 `REVIEW-BINDING-M5-CORE-01.md` SHA256 `37172d03aa1b8b532c765a73c76a3f1a2337623e85edb567e5eb6550556589ac` đang chờ root xử lý content occurrence/UOM encoding/projection. Rebase bản M5 được duyệt trước quantity confirm. Reuse chính `hoa_don_dong_danh_tinh/hoa_don_dong_phien_ban` đã chốt ở M2 dòng191–192, không tạo identity/conversion/remaining khác. Common M0 observation chronology nếu được amend phải áp thống nhất, không thêm kho raw M2.
3. **Core protected-graph gate đã mở:** current `de_xuat_dong_khoa_sau_xuat` dòng742–753 chỉ lookup `coalesce(NEW.de_xuat_id,OLD.de_xuat_id)`. Handoff phải mang gate OLD+NEW parent và toàn graph từ common M9/root M1 review tới M2; thử moving protected posting/attribution/claim sang parent khác, mutation source/route/scope sau check/export, cả direct SQL và service. Đây là inherited core integration gate đã nêu ở M9§8/R2 và M2 dòng133/137/236–242, **không tuyên bố được sửa hoặc là finding M2 mới**.
4. **Không bỏ acceptance:** chạy R1A/B–R5 + C-M9 và I1–I8 sau terminal/freeze, role ordinary non-owner, positive trước denial, race hai winner orders+observer. Nối NT/invoice cùng nghĩa vụ dùng source role/crosswalk/scope đã xác nhận, không cộng đôi corroborating evidence hoặc làm hai GOC; advance rebind fault giữa cancel/create rollback toàn graph. Kỳ/lô/download giữ lịch sử; receipt mới/alias/PB không giải phóng semantic consumption. Counts runtime hiện **unrun**, không cộng5 closures vào test pass.

TL35§8.6/#10 ownership giữ nguyên. Policy kế toán/thuế/FX/rounding/partial/adjustment, source samples/production crosswalk và approver thật tiếp tục là gate full M2; DEMO hợp lệ dùng profile/template đã khai báo, không tự đặt policy để gọi hoàn thành.
