# Review độc lập binding M8/core — 01

19/10/2026. **STATIC_ONLY / PRECODE_REVIEW / NOT_IMPLEMENTED / NOT_ACCEPTED.** Đọc toàn binding98 dòng SHA `11d27c73f434d0efc5a874ce722d439a92a791630a0cc2afcc09763bc1cf153c`, draft SHA `4c41ce6a58ee5a72e85d464fb560949b2ab80dc05ed57dbcf3a52808a630509b`, common M2 SHA `001aefc2d7cb8e9d0b6017325c465c2f536962b56331d3ef08c44b3388c0eea2` và M9 amended SHA `28af9c1045c8da5448056baa45b679fd476f48aaa40d897ff92430764b168bc5`.

Chỉ docs và schema **frozen06** (các bảng liên quan chưa đổi so core03); không đọc source app #7/rows thật/credentials, không import/test/SQL/HTTP/process/runtime, không lấy interim M9 handle88862 làm final. Giữ nguyên binding/draft/product. Findings là các điểm contract cần cụ thể hóa trước code, không phải runtime failure đã tái hiện; không bổ sung policy thuế/pháp lý/FX/dung sai.

## P1 — R1. Parent common link phải trỏ core document, không trỏ invoice PB UUID

**Anchors:** M8:43–45,64; accepted M2:44,48,251; M9:89,96,154–158. Frozen `pg_migrations.py:550–566` giữ `chung_tu_a_id/chung_tu_b_id` FK tới **kho.chung_tu**; index `lien_ket_cap_uq` tại1028 giữ active A/B/type unique. M2 PB là row registry riêng, có `chung_tu_id` backing document HD_MUA/HD_BAN của chính semantic version.

M8:64 ghi “A=typed invoice PB/B=SO_JUNSKY core document”, chưa bind cầu nối vật lý. Với PB UUID p1/backing chứng từ c1, ghi p1 vào chung_tu_a_id không thể qua FK; không được coi hai miền UUID là alias hoặc tạo chứng từ giả để làm parent hợp lệ. Chỉ thêm type CHECK/dispatch HOA_DON_SO không sửa được mismatch này.

**Cần chốt:** parent A=`invoicePB.chung_tu_id`, B=SO_JUNSKY document; typed evidence/parts giữ composite tuple `(PN,invoice identity,PB,core A)` và ledger-line/snapshot/core B đúng input manifest. Không cho line của chứng từ B khác cùngPN. Nếu chọn một mô hình typed parent khác phải khai DDL/FK/compatibility cụ thể, không bỏ FK cũ.

Đồng thời bind **reuse grain/lifecycle**: nhiều measure/group/resultPB có cùng A/B/type phải tham chiếu cùng canonical parent hoặc một extension có unique tương ứng được review; không INSERT parent mới cho mỗi report để va active unique. Per-result decisions/parts phải giữ immutable refs. Gỡ một xác nhận scoped cần nói rõ là gỡ assertion của report hay canonical crosswalk; nếu đổi canonical link thì resolve/invalidate toàn tập kết quả phụ thuộc, không làm các scope khác vẫn KHOP với parent HUY. Không hủy money allocation hoặc đổi EVIDENCE sang MONEY.

**Ca:** đúng PB→backing document→ledger-line đạt; UUID PB thay core A hoặc PB_A+core document_B cùngPN bị từ chối0mutation. Hai report/PB kết quả dùng cùng canonical pair hoạt động không tạo parent trùng; revoke đúng phạm vi/impact, historical result/file vẫn giữ refs và không thay BANK remaining.

## P1 — R2. N:N cần bảo toàn attribution hai phía trên toàn result, không chỉ dedup grand total

**Anchors:** M8:42–45,48,53–54,58,70,92; common M2§9.R1/R3 và M9 wholegraph/R2. Binding đã nêu full-scope/conservation và không cộng duplicate joins; thiếu invariant cụ thể phân biệt **source amount**, **matched parts** và **unmatched residual** xuyên các group cùng resultPB.

**Counterexample:** invoice A100 và B100, cùng ledger-line J100, cùng channel/currency/basis. Hai group độc lập A↔J và B↔J đều ghi matched100; cached equality từng group có thể cho hai KHOP. Grand total dedup J chỉ còn100 không tự chặn persisted attribution J200 hoặc hai confirmed evidence links đầy đủ. Ngược lại, buộc tổng invoice=ledger để “conserve” sẽ chặn cả kết quả LECH hợp lệ mà M8 cần lưu.

**Cần chốt:** DB validator enumerate toàn declared input rowset, theo canonical source unit+revision/measure/channel/direction/currency/scale/basis; ràng buộc matched parts trên **cả hai phía**, xuyên mọi group của một result, không vượt source amount có căn cứ. Mỗi part chỉ được tính một lần bằng typed semantic key, không UUID mới; matched+residual=source scope amount. KHOP đầy đủ chỉ khi residual tương ứng bằng0 và field/coverage/basis đủ; LECH/partial giữ residual typed/reason, không bỏ dòng không ghép được. Không net hai direction/counterpart để che oversubscription. Validator full-domain không lấy RLS-filtered sum; check/confirm/export và đường SQL đều cùng invariant/action/protected-state gate dưới source-root→result locks.

Giới hạn theo **report/declared union**; không tạo financial remaining/budget M8 hoặc cấm cùng source xuất hiện hợp lệ trong hai báo cáo. Cross-scope union phải reuse/collapse cùng canonical parts/basis, không sum lại assertion copies; các mapping được xác nhận mâu thuẫn cho cùng source unit phải conflict/impact, không âm thầm chọn một group thắng. Payment L9 vẫn chỉ đọc M2/M9 common allocations.

**Ca:** A60+B40↔J100 với explicit parts60/40 đạt; A100+B100↔J100 không được có hai full KHOP. Full200 với ledger100 vẫn lưu LECH/residual100 đúng; duplicate part/new group UUID, missing row hoặc sign/counterpart netting không che lỗi. Hai report lặp cùng evidence không nhân union totals; input/confirm race không chốt graph ngoài phạm vi/conservation đã kiểm.

## P2 — R3. Bind revision của coverage assertion khi thêm proof mà raw/scope không đổi

**Anchors:** M8:23–25,35,40–41,58–60; M9 common M0:39–40. Source-scope row hiện UNIQUE(PN,snapshot,derivative,role,scope_sha256), chứa counters/coverage/manifest refs; source facts được giữ append-only. M0 snapshot dedup `(instance,profile,raw hash)`, derivative không dùng fetch time/random salt. Input coverage mới phải làm result stale nhưng chưa có đường version coverage cụ thể trong DDL này.

**Case cần bind:** raw bảng kê/selected rows/profile/query scope giữ nguyên; lúc đầu expected count/producer proof thiếu→UNKNOWN, sau nhận manifest/parse proof có căn cứ→COMPLETE. Không UPDATE coverage/counters đã được historical result pin, không đổi scope key hoặc bịa source revision chỉ để vượt unique; old cutoff vẫn không được nhận proof biết muộn.

**Bổ sung:** pin common M0 coverage/proof assertion version nếu đã có, hoặc identity scope + append assertion revision (manifest/counters/coverage/reason/first-known/predecessor/evidence, guarded accepted pointer). Result input trỏ exact assertion ID/version/digest và known-time. Nếu dùng manifest raw snapshot riêng làm assertion thì bind quan hệ typed scope→payload snapshot→manifest assertion rõ, không coi bare receipt/fetch là business source revision. Cùng proof retry reuse; proof mới đủ căn cứ tạo assertion/result mới tại cutoff hợp lệ; historical UNKNOWN/file cũ nguyên. Đây là metadata provenance, không invoice/raw store M8 khác.

## Những phần phù hợp cần giữ

Coverage từng role/opposite scope, unknown/empty/parse-error không thành PASS; source observation sparse/presence/precision/status namespaces và A→B→A occurrence history; date/first-known/valid/cutoff không đánh tráo; typed common invoice registry và candidate missing-date; proposal/FILE_SOAT không phải ledger; L9 shared target thiếu invoice attribution giữ CHUA_XAC_NHAN; không double BANK/112/recognition hoặc tự chọn policy thuế đều đúng hướng.

RLS+action, scoped minimal source projection, owner-only fullgraph validator, module/subject immutability, rights-before-replay, expected digest, period/protected refs/undo atomicity và giữ source/history/file cũng đã có căn cứ. Không nêu lại chúng như lỗi runtime hoặc yêu cầu mở rộng quyền. Sau khi chốt R1–R3, root cần review final common interfaces trước giao code; acceptance T1–T7 vẫn phải có ordinary role/direct-DB negatives/positive controls/coverage/time/conservation/restart và GUI thật. Review này không cộng test PASS hoặc nghiệm thu M8.
