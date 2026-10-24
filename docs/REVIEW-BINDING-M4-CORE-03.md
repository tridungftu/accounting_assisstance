# Closure review M4 — 03

**19/10/2026 · DOCS_ONLY / DESIGN_FINDINGS_R1_R5_CLOSED / NOT_IMPLEMENTED / NOT_RUNTIME_ACCEPTANCE.** Đã đọc toàn174 dòng `BINDING-M4-XDCB-SAU-CRM06.md` SHA256 **`1760a36bc13af1b9fa8900973f840640bb25a7fea921e7c1fd3937376e489d9a`**, gồm R5 §9.R2/R3; đối chiếu review02 SHA `8669c15e19d36f3282f8709a17dd0d43eb38632b5b27a8eb49ce09a659a62757` và common M2 source/plan/use contract. Không còn contradiction thiết kế chặn nào được xác định trong phạm vi closure R1–R5. Không sửa binding/product, chạy/import/test/SQL/HTTP/process, đọc live M9/source app/real rows/secrets hoặc xóa file.

## 1. R5 đã khép bằng path proposal-time duy nhất

| Điều kiện review02 | Binding cuối đã giải |
|---|---|
| Không reserve lại original S/WHOLE | §9.R2 origin `CHI_PHI_PHASE_INPUT` exactly-one typed FK/UNIQUE(PN,chi_phi_input_id); input identity unique canonical upstream lineage+portion+input phase+measure. Derived entitlement kế thừa approved upstream scope/claim hoặc actual typed crosswalk/proof, không pool độc lập, original source-use giữ nguyên; approved phase lineage/no cycles |
| Không nullable first-claim/fake proposal | Giữ `mua_nguon_su_dung` UNIQUE(PN,part), `first_claim_id NOT NULL`; chỉ financial proposal transaction tạo claim+use+receipt/audit. Confirm nguồn/handover chỉ HOSO/CHUA_DAT_CHO_NGUON,0claim/use/proposal và không financial consumer/KH/acquisition/COGS basis |
| Một budget L5/L6, không new slot vì PB | Derived root dùng chính common WHOLE/PHAN_RA plan, explicit60/40 và residual/conservation; stable part giữ qua plan/PB/mapping revisions. Planpart→output phase/owner/correspondence, use→đúng financial event/component; old consumed/tombstones không được reset |
| Same output30 không thành60 dưới pool100 | Stable `chi_phi_xd_dau_ra` riêng output PB row, canonical key không PB/amount/destination UUID/technical run; aliases reuse logical output. Global effective output triple có full composite FK và guarded CAS kiểm cả parent transfer effective PB/source decision/phase-map/plan PB; wrong input/output/PB hoặc stale refs bị guard |
| Downstream không consume lần hai | Financial accept/basis/file pin exact output PB+planpart+actual claim/use+required accounting approval, reuse same IDs. HOSO/source confirmation và financial eligibility tách rõ; source-only switch không rewrite protected PB/claim/file |

R1/R3/R4 đã design-closed ở review02 và không bị R5 đảo lại: typed NT/source/decision tuples và common payable; actual financial owner khác NT object-owner, BOTH capability cho direct consumer hoặc approved new phase+M4 source-disposition action; L3/L4/L5/L6/L7/L12 và owner335=M10 giữ đúng. No stock-value journals/calculator/ledger/accounting policy mới.

## 2. Interface M3/M6 cần pin theo SHA này

Consumer pin **input `(PN,input_id,input_pb_id)`** kèm canonical input-phase/portion/measure và inherited upstream event/component/claim/scope/decision-or-actual basis; common derived source root+source PB+effective plan PB+stable part. Output pin **`(PN,input_id,output_id,transfer_id,transfer_pb_id,row_id)`**, mapping/application/phase-map PB và expected global effective output triple **cùng** parent effective PB. Financial step thêm actual new-phase event/component/claim/source-use và exact approved scope; không consumer-side capacity/claim alias hoặc latest join. Composite FK/DB validator phải map đầy đủ các tuples đã bind, không chỉ kiểm same-PN.

M3/M6 tiêu trực tiếp event đã có giữ actual owner và BOTH operation caps. Genuine approved L6/L5 phase ownerM3/M6, cần đúng own financial operation+M4 cost-source disposition action; upstream old claim chỉ scoped immutable proof, không reapprove/retag ownerM2/M4 của old event. Source-only HOSO stage không tự yêu cầu/tạo financial V1 claim. Revoke quyền trước lookup/replay/download vẫn không protected output.

## 3. Giới hạn và kiểm chứng sau implementation

Closure này chỉ cho phép root dùng binding cuối để rebase consumer/spec/code handoff theo dependencies đã nêu; **không chứng minh runtime đạt**. Bắt buộc sau final M9 freeze/rebase: original100 giữ nguyên→confirm60/40 HOSO0financial delta→proposal60+40 dùng đúng common parts/claims; same PARTIAL30 qua PB/aliases chỉ30; genuine distinct30+20 còn50; full100+full100/new-phase/new-root/wrong tuple/claimless-use negatives; CAS/protected/current/basis giảm; direct-vs-consumer owner/caps/revoked replay; both winner orders với actual first-shared-lock observer, reject0business delta; nonempty-upgrade giữ IDs/raw/source-use/proposal/lô/file/history và old migration checksums. Các ca đã liệt kê trong binding vẫn **NOT_RUN/NOT_VERIFIED**, không dùng error/empty/setup/timeout hoặc count bridge21/27 làm nghiệm thu M4 mới.

Các gate source samples/correspondence/catalog/precision/supplied phase-map/policy/templates/production source integration/UI/Junsky vẫn là work cần hoàn thiện toàn33; closure không tự chọn các giá trị này hoặc bỏ module vì thiếu chúng.
