# M2-BRIDGE01 — actual selected P01–P08, trước repair02

19/10/2026. **ACTUAL_SELECTED_DEMO / 9_PASS_2_FAIL / NOT_ACCEPTED.** Báo cáo bổ sung mới, giữ nguyên static review và actual defects report. Root thực thi; agent chỉ đọc receipt, đối chiếu verifier và ghi tài liệu. Repair02 đang CODE_ONLY, không lấy source interim làm kết quả cuối.

- Root selected handle46746 terminal chunk `e27e3c`, exit1. Result `var/codex-dieu-phoi/m2-r15-independent-selected-586531c035b4/result.json`, SHA `80d4ffbab0863fa7ec60388a9c7ada831f4d93bf60444597d00fae21f4c33941`, executed21:22:37.
- Frozen249 manifest `e515b4ef76a6990f84bed4245558e4aa82cf53234e07c4111fddd2f1bdcf033c`; root báo frozen/workspace249 và original no-delete guard không đổi sau chạy.
- Verifier: factory `8bcd486042e5482b819dc204c948d9ad122a4ce96f80c18fcb2be31a268fc09b`; adapter02 `4a29635f46756e18cf1609b66c7a010e5ae90f4f4b82682db50e1722727d979d`; controls02 `d009afe0e7d3c974e053fcba9131c912536a80f0bf64067f409984016716e158`; selected02 `a4f120605e2b940d2a12e03f84b8098cf12a0f34ea3ee556cfc8f2e440c674f9`; root runner03 `3d85ba188e925420dd350a544c34777eb94673b00115b5f936a646e3ad225e96`.

Receipt có **11 labels: 9 PASS, 2 FAIL, 0 ERROR**; labels là các đoạn của workflow P01–P08, không phải11 module hoặc14 plan groups đã đạt.

| Label | Actual | Phạm vi bằng chứng |
|---|---|---|
| P01 | PASS | Source-only actor capture G01; nonempty identity/PB/core line, quantity exact10, tiền/Nợ/Có NULL, chưa logical/map/bridge/route. |
| P02_CAPTURE_REPLAY | PASS | Capture exact retry giữ kết quả ngoài `lap_lai`, toàn snapshot DB/files0delta. |
| P02_CAPTURE_CONFLICTS | PASS | 3 changed-native/coverage/errors same-key controls, specific denial và snapshot0delta. |
| P03 | PASS | 6 distinct negatives: source/M1/cross-PN/stale mapping, header-as-line và route-before-map; không thay thế các R2 wrong-literal negatives ở probe riêng. |
| P04_EXACT_MAPPING_REPLAY | **FAIL** | First mapping đã thành công nhưng retry **nguyên body/tokenA/key** bị `M2_VERSION_CHANGED`; denial0delta không phải replay PASS. |
| CURRENT_M2_MODULE_WITHDRAWAL | PASS | Tạm rút module M2 của actor CFO DEMO mới bằng UPDATE, current-rights chặn old-key mapping replay, denial0delta rồi khôi phục đúng grant ban đầu. Không kiểm capability-row revocation. |
| P05_FIRST_ROUTE | PASS | Actual CFO tạo+duyệt KHO lần đầu, đúng counts và không thêm downstream finance/quantity rows. |
| P05_EXACT_ROUTE_REPLAY | **FAIL** | Retry nguyên request/tokenA bị `M2_VERSION_CHANGED`, state_delta0; không tự thay token cho xanh. |
| P06 | PASS | Duplicate XML-in-ZIP: capture2/obs3/rawrows8/snapshots2; stable business IDs và semantic route basis; OP token tiến, actual raw inventory đúng bytes. |
| P07 | PASS | G04 padded/unpadded cùng canonical identity nhưng distinct content; PN_B tách; sale raw candidate, không promote M3. |
| P08 | PASS | A,A giữ content/eligibility; A→B→A không tự restore; stale review deny, explicit latest review có quyền chọn latest. Không chứng minh R16 held/proof lifecycle. |

Hai lỗi replay xác nhận R1 ở static review. Probe defects riêng đã xác nhận R2/R3/R4/S1:4positive+8VIOLATION, trong đó3R2 whole-state-restored=false; giữ đúng báo cáo `REVIEW-M2-BRIDGE-ROOT-PROBE-01.md` SHA `b1ed7d1a2663bd40fb20e6f21fd6e7d96c44999f6fd5f17b77e1e84df54c4b53`. Không cộng8violations và2replay failures thành số lỗi độc lập hoặc cộng các positive overlap thành coverage mới.

Hai verifier attempts trước giữ nguyên: adapter01 params=() với literal `%` gây SETUP ProgrammingError; attempt sau gặp P01 assertion so numeric38,12 `::text` với literal"10". Sibling adapter02 đổi params-or-None và selected02 dùng exact Decimal equality, không float/tolerance, bảo toàn original native quantity lexeme. Chúng sửa verifier representation/setup; không sửa product để khớp oracle và không hồi tố hai attempt cũ thành PASS.

**Giới hạn:** P09–P14 UNRUN; capability-row revocation UNVERIFIED vì không chạy thao tác xóa; thử UPDATE module không đồng nghĩa kiểm source-cap revocation. Không GUI/browser/download acceptance, R16/L11/fullM2/M5/33 acceptance hoặc production/source-history truth. Mọi DEMO DB/role/files/attempts được giữ; không M9/sourceapp/realdata execution. Chỉ sau actual repair02 terminal+freeze+review mới rebind independent probes với pins/guard mới; chưa có kết quả sau sửa trong báo cáo này.
