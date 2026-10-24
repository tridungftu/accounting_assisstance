# M2 XML/ZIP PURE02 — sửa giới hạn chuẩn hóa số lượng

19/10/2026. **AUTHORIZED_CODE_ONLY / ROOT_RUNTIME_AFTER_TERMINAL / CHƯA NGHIỆM THU.** Tiếp đúng session Claude hiện có. Gói01 đã terminal0 theo actual `29af58`, frozen240 manifest `59d2456e12cca6d64e583855091a06982e8949f060f3d2d54432529924422c8c`;238file nền/fixture nguyên. Không sửa thêm kiến trúc hoặc policy nghiệp vụ.

## Bằng chứng và hai việc cần sửa

Root đã đọc toàn bộ reader/test/report01. Actual root chạy27unit PASS,0fail/error/skip; verifier riêng đối chiếu232fieldstates,11observations/6identities/8contents,8crosswalkrows,15quantityboundaries,3duplicateZIPentries cùng mutation controls đạt. Existing legacy XML/month-folder test1PASS; toàn240source nguyên. Các tập có overlap, không cộng thành tổng test độc lập. Đây chưa là nghiệm thu parser vì counterexample bổ sung dưới đây chưa đạt; DB/API/UI/L11 vẫn ngoài gói này.

1. **R1 — chỉ chuẩn hóa theo quy tắc CAI1/1 đã chốt.** DTO/handoff01 chỉ hỗ trợ explicit same-CAI ratio1/1 và21digits/6scale. Hiện `InvoiceMeasurementFacts.ho_tro` nhận mọi `raw_unit==canonical_unit`. Root actual đã đổi đúng native `DVTinh` sangTHUNG, dùng factTHUNG1/1 với rawref tính lại đúng bytes: reader trả normalized`10`,0issue, trong khi expected normalizedNULL/HOLD. Positive CAI hiện vẫn trả`10`. Chỉ hỗ trợ CAI của profile này; đơn vị khác phải giữ raw/Decimal facts, issue unsupported/unproven và normalizedNULL. Không suy hệ số từ label hoặc mở rộng sang THUNG ở pure phase. Quy đổi L11 có proof riêng ở gói sau.

2. **R2 — không dùng fact chuẩn hóa của context mâu thuẫn.** Root actual rawref mismatch đã cho identity/contentNULL nhưng normalized vẫn`10`. Khi context có mâu thuẫn raw binding/profile ref/profile document (kể cả payload bị nhầm document), không cấp normalized quantity từ fact đó. Giữ nguyên raw bytes/hash, field states, exact Decimal/native unit và issue. Không sửa native để khớp context. Positive context hợp lệ phải giữ nguyên; `expected_raw_ref=None` chỉ là NOT_BOUND như gói01, không tự đổi thành mismatch. Missing unit/crosswalk/registry payload vẫn không làm mất semantic identity/content đã đủ căn cứ.

Không dùng thay đổi này để thêm financial eligibility, quantity pool hoặc L11 boolean. `normalized` thuần vẫn không cấp quyền business matching.

## Phạm vi ghi đúng3file

- `src/kho_tri_thuc/nguon/hoa_don_xml.py` — sửa hẹp R1/R2; baseline SHA `e6d65f77936b88619562011e280ef52e00d51ac8db1b1d7baa50de09d5f48b71`.
- `tests/test_hoa_don_xml.py` — giữ nguyên27tests hiện có, thêm counterexamples R1/R2 và positives; baseline SHA `c764a445d55ee82947f0935df3cb7413530ce98937cba7462d071e5d097366d5`.
- `docs/BAO-CAO-M2-XML-PURE-02.md` — report MỚI, CODE_ONLY/UNRUN; mô tả diff và giới hạn.

Report01 SHA `6527d70e6c55c40d24abcea52394c2c68586953e255da35201826665567856a7` và mọi report/review/fixture/oracle/golden/profile cũ giữ nguyên. Không sửa that.py/fixture.py/primitives.py, M0/M5/K2/server/UI/schema/seed/launcher/config/guards hoặc sourceapp. Không sửa expected để nhận đơn vị ngoài contract. Không blanket disable chuẩn hóa hoặc mất mọi identity/content.

## Kiểm sau bàn giao

Root chạy lại27+tests mới, cùng verifier độc lập và supplemental CAI-positive/THUNG-negative/raw-profile-context negatives. Kiểm exact golden digests, deep immutability, raw/ZIP bindings và nguồn/fixture hashes giữ nguyên. Legacy that.py vẫn pin `f7330761f1ef8dbbcdc49429a09919f6135001dd0a50d804e6212af3de0ff1fc`; source thực không đổi thì không gọi legacy test cũ là đã chạy lại02.

CODE_ONLY: chỉRead/Glob/Grep/Edit/Write, không execute/import/compile/test/SQL/Store/PG/HTTP/GUI/process/network/Bash. Không đọcvar/.env/secret/sourceapps hoặc realrows; không delete/move/drop/reset/cleanup file/DB/role/attempt. M9 chỉ phương pháp lấy dữ liệu, không sửa theo dõi/lãi/lịch trả hoặc gọi nguồn vay. Sau viết3file thì kết thúc CLI để root xác nhận terminal/freeze/review/runtime riêng. Đạt pure mới tiếp M2 source bridge15 rồi quantityL11; không lấn sang gói sau trong lần sửa này.
