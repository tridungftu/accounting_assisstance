# M2-BRIDGE01 — bổ sung bằng chứng probe độc lập actual root

19/10/2026. **ACTUAL_SELECTED_DEMO_EVIDENCE / 8_VIOLATIONS / NOT_ACCEPTED.** Báo cáo mới bổ sung review tĩnh `REVIEW-M2-BRIDGE-MIGRATION-01.md` SHA `737b4827511b42ff98400a8da02d3b751e70946fd313d7c0c2ec85a2c3a0c9e7`; giữ nguyên báo cáo cũ. Agent chỉ đọc evidence/source frozen và viết tài liệu này; **root** là bên thực thi.

## Phạm vi và pins

- Root actual tool `ff339b`, defects child handle9141 terminal exit1. Evidence `var/codex-dieu-phoi/m2-r15-independent-defects-f9e578b7bc55/result.json`, SHA `9e1c9a5406beee7cc9e813e43f17587966110adc32c6606533a7635abd852306`, thực thi21:18:27.
- Frozen249 manifest `e515b4ef76a6990f84bed4245558e4aa82cf53234e07c4111fddd2f1bdcf033c`; SQL `037e037ce8fa00c0b79a59769a67b9840b547cdac0fe6ae15351d24d8dd10644`; service `8280a50eb616b27521dcce35b31a0f3f9c504ce94e02ccf3f81e7fba4734a862`. Root báo workspace/frozen249 và original no-delete guard giữ nguyên sau chạy.
- Probe `eeb07b59bf6709148e564df56765d11f087229a2b3f55d3e6f42f215a8ace84c`; factory `8bcd486042e5482b819dc204c948d9ad122a4ce96f80c18fcb2be31a268fc09b`; root runner01 `7a662d0589c9a13797bf034a2b098c7604366f9b40ad04e44287560c0c5f0bd3`. Fresh retained local `kho_test_*` DEMO, actual HoaDon/m2_demo, ordinary app_web+configured owner+independent observer; không coder unittest setup hoặc oracle làm runtime facts.

## Kết quả thực sự quan sát

Tổng **4 positive PASS, 8 VIOLATION, 0 setup/unexpected error** trong probe hữu hạn này. Tám negatives đều được product/DB chấp nhận và mutation đã quan sát **trước rollback**; rollback không đổi VIOLATION thành PASS.

| Nhóm | Ca actual | Kết quả và giới hạn |
|---|---|---|
| R2 literal binding | `R2_WRONG_LOGICAL`, `R2_UNKNOWN_FACT`, `R2_ORACLE_ALIAS` | Cả3 tạo được bridge qua ordinary app definer call với current CFO hợp lệ; sai candidate fact/target vẫn được duyệt. Cả3 `whole_state_restored_after_rollback=false`; không báo0delta hoặc “đã phục hồi toàn bộ”. |
| R3 core source immutable | `R3_CORE_QUANTITY`, `R3_CORE_SOURCE_HEADER` | Configured **owner** UPDATE quantity và source header được chấp nhận; cả2 có whole-state restored=true sau rollback. Đây là thiếu source immutability guard, **không phải** chứng cứ app role vượt owner-only INSERT/UPDATE guard. |
| R4 unit payload/SHA | `R4_CLAIMED_SHA_MISMATCH` | Owner INSERT unit payload có meaning khác nhưng claimed SHA của payload tốt vẫn được nhận; restored=true. Chứng minh thiếu payload/hash binding, không chứng minh caller thường được sửa registry hoặc conversion đã được approve. |
| S1 typed NULL shape | `S1_ZIP_MISSING_HASH`, `S1_ZIP_MISSING_ORDINAL` | Owner INSERT observation ZIP triple chỉ có một phần được nhận; restored=true cả2. Đo trực tiếp2ZIP shapes; mapping partial-NULL ở review tĩnh chưa được probe này kiểm. |

Positive controls không rỗng: actual capture có identity/core line; actual CFO+literal đúng tạo bridge; unit canonical đúng được owner INSERT trong rollback-only transaction; actual direct-XML observation có ZIP triple allNULL. Các positives này bảo đảm negative không chỉ cùng fail setup hoặc tập rỗng.

Snapshot dùng independent observer: app-table rows, structural catalog/functions/policies/triggers/ACL, sequence last_value/is_called và retained artifact-file hashes. R2 function có INSERT audit (`pg_migrations.py:5879–5880`), audit ID là `bigserial` (`:413–414`): có căn cứ nguồn cho giả thuyết sequence gây khác snapshot sau rollback. Nhưng result chỉ lưu restored=false, không lưu per-object before/after diff; báo cáo này **không kết luận chỉ sequence**, không loại trừ delta khác và không sửa lại expected để làm xanh. Giữ nguyên resources/evidence, không cleanup.

## Verifier setup và những phần chưa được chứng minh

Selected runner01 riêng, actual handle40692/chunk513c5a, dừng `SETUP ProgrammingError`, các case còn lại NOT_RUN. Evidence `var/codex-dieu-phoi/m2-r15-independent-selected-c5a7a5a9ded7/result.json`, SHA `4d983c0c3a79b65830204b0e5297a77b58f32e5f5afc6670a2630f67ee2fe6bf`. Root xác định adapter truyền `params=()` cho query có literal `%`; **không tính lỗi verifier này là product FAIL hoặc PASS**. Sibling adapter02 chỉ sửa2call q/all thành `params or None`, runner02 chỉ đổi adapter filename/hash; static diff CLOSED, chưa đưa kết quả rerun chưa có vào báo cáo.

Root đã báo migration suite5PASS và M5 service regression36PASS là component evidence riêng; không cộng các số đó vào12case của probe hoặc coi mọi P01–P14 đã đạt. R1 exact business replay đã có lỗi trong service suite root, không được đo lại bởi probe R2/R3/R4/S1 này. Current-capability-row revocation, full RLS/stage/races/retained14→15sentinels, browser/GUI, R16/L11/fullM2/M5/33 chưa được nghiệm thu từ receipt này. Không M9/sourceapp/realdata execution, không file/DB/role removal; mọi tài nguyên được giữ.
