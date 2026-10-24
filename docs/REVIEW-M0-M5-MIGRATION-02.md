# Review độc lập migration M0/M5 — final candidate02

**19/10/2026 — STATIC_FINAL_REVIEW / CÒN BLOCKER / RUNTIME_NOT_RUN.** Review chỉ đọc frozen source; không sửa product, import/runpy/AST/SQL/DB/test/process/HTTP/GUI hoặc M9. Counterexamples dưới là control flow tĩnh, chưa phải lỗi đã tái hiện trên PostgreSQL. Không chuyển kết quả test của candidate01 sang candidate02.

## 1. Exact candidate và phạm vi đã đọc

- Root actual terminal Claude68305 exit0, tools.write_stdin `5dc8f8`; authoritative receipt SHA `b92103039a672866c71e034ffe53442fab8206d194c26483427b4d68d891b837`. Freeze `2c578f`:210source,13changed,0offscope/missing/fixture/protected drift.
- Frozen `var/codex-dieu-phoi/kiem-chung-20261018-101441/m0-m5-intake-ui02-handoff-20261019-165145-481-cec6fac8/frozen/`; source manifest SHA `3d5acde6e1327542aeca488c8d72599eef042c704dcf505b372165dead069906`.
- `src/kho_tri_thuc/ha_tang/pg_migrations.py`:4540dòng,SHA `74319fd22db1cb0f0b68edd1e256f7b34fdb64679ac6fb6a9b41c9f1a52b6c4f`; `postgres.py`:232dòng,SHA `b0212af0913492fa91dc5d2aa67d5d4d5e2a106d339596af5711316f08598dc8`. Mọi source anchor sau đây thuộc final này, không dùng số dòng interim.
- Căn cứ handoff02 SHA `43902e6e3db1d61552b99a4070b2437eeb0c4189d709417e2e5267f2d06a7816`. Interim graph review SHA `85c64a703eb45f25a36e1ffe63f81fb346a6998e26a7af6cff86b2f9af676046` được giữ nguyên và rebind.
- Đã đọc toàn M0014 tail của interim285d72 và kiểm final tail từ `M0014_M5 = (` **exact text bằng toàn bộ**, không thay semantics; đọc lại final review/FILE/mapping/ACL paths. Final chỉ thêm27dòng lo/work legacy RLS3525–3551 so snapshot đó. Đọc đủ final postgres1–232, neutral owner/line/receipt/stage/core FKs và capability/capture/getter paths liên quan. Phần service/writer/HTTP/UI do root/peer review riêng, không suy kết quả từ code SQL.

## 2. Findings còn mở, theo ưu tiên

### P1 — Business receipt namespace chưa khóa trước tác dụng file / mapping retry

`kho.m5_file_bat_dau`4391–4397 chỉ khóa PHIEU_KHO rồi lookup receipt; consumer4455–4458 cũng chỉ cùng khóa phiếu, receipt UNIQUE được ghi4487–4488. Hai valid flows cùngPN, **khácphiếu nhưng cùng `(PN,M5,FILE_SOAT,key)`**, khácH đều có thể miss khi flow kia chưa commit, rồi cả hai dựng stage/artifact. Loser chỉ gặp UNIQUE khi ghi receipt, sau file delta; rollback DB không làm file đã ghi biến mất. Đây trái409-before-artifact-delta; không phải lỗi path guard đã sửa.

Mapping có cùng nguyên nhân: receipt lookup4323–4329 đứng **trước** subject lock4331. Hai cùngkey/cùngpayload cùngmiss; loser sau winner commit đi tới4335–4336 và trả ANH_XA_DA_CO thay cùng idempotent result. Cần serialize business-key namespace trước lookup/graph/file delta, thống nhất lock rank và recheck sau wait. Không chữa bằng HTTP mutex hoặc chỉ đổi UNIQUE exception thành PASS. Ca sau release: FILE cùngkey/khácphiếu hai winner orders phải conflict trước loser file/stage/lo delta; MAP samekey/samepayload phải replay cùng receipt; có positive control và observer/timeout hữu hạn.

### P1 / I-M05 — eligible_content vẫn lấy từ trạng thái nguồn, thiếu quantity/proof gate

Review4279 kiểm blocklist/historyKNOWN rồi4283 đặt eligible theo DA_DUYET duy nhất. Không kiểm measurement/UOM/precision/continuity/normalizedNULL của lines. Trusted K08/09/10-style source approved/historyKNOWN nhưng proofUNKNOWN/UNPROVEN có thể được accepted **và eligible UUID**, dù quantity chưa đủ căn cứ.

Theo binding và technical clarification của root trong phạm vi đã duyệt: accepted latest source/history và eligible quantity là hai trục. Accepted có thể giữ source evidence trong khi eligible=NULL; proof/UOM/precision/continuity/context/partial HOLD hoặc line unknown/nonexact normalized phải chặn eligibility. Cần exact positive eligibleUUID; K08/09/10 source accepted positive nhưng eligibleNULL; reversal/ABA vẫnNULL. Không chặn file soát HOLD để giấu issues. L11 sau này vẫn kiểm per-line encoding/two-pool/cross-proof riêng, không dùng accepted/requestH làm proof. Đây là sửa gate đã yêu cầu, không thêm policy kế toán.

### P1 — FILE expected basis chưa thực hiện đầy đủ handoff

Request H4393–4394 chỉ gồm phiếu/latest/accepted/eligible. Preflight4404–4406 và consumer4465–4472 cũng chỉ kiểm3pointers/ky. Chưa bind explicit selectedcontent/sourcecapture-bundle/mapping/master/measurement/proof/period refs như handoff§6.58; snapshot4421–4435 có vài refs không thay được expected-basis/current-proof contract. Thay hoặc stale các basis refs phải được nhận biết trước stage/file/lo delta; không chấp nhận “3pointerH tương đương toàn graph” khi không có binding/oracle đó. Giữ samekey/samebasis replay, positive HOLD export và old immutable download.

### P2 / I-S01 — inactive source vẫn qua nhánh SOURCE_MAP metadata getter

`giao_tiep.nguon_anh_xa_hien_hanh`3696–3699 dùng current INTAKE predicate **OR** manual EXISTS SOURCE_MAP. Nhánh EXISTS không join/check instance HOAT_DONG như guard3104–3110/metadata3115–3121. Actor còn capability row nhưng instance DUNG có thể nhận mapping id/revision/PN3702–3704 dù current source predicate deny. Chỉ kết luận metadata admission gap, không claim raw/business mutation/cross-PN exploit. Reuse current-source SOURCE_MAP predicate; giữ permitted CFO positive, không cấp READ_SOURCE/INTAKE để né lỗi.

### P2 / I-S02 — verified-empty chỉ kiểm bảng, bỏ non-table catalog objects

`postgres.py`84–95 chỉ đếm information_schema.tables. DB có master plus standalone enum/sequence, hoặc foreign schema chỉ có routine mà không có bảng, vẫn trảfresh0; migrate184 rồi189–193 bắt đầu DDL. Đây chưa phải verified empty/partial-foreign refusal trước ghi. Cần kiểm actual non-system catalog/namespace phù hợp bằng quyền migration thật, có fresh positive và retained enum/sequence/routine negative; không lấy eventual CREATE error hoặc rollback thay admission proof. Chưa chạy DB reproducer.

## 3. Closure tĩnh có căn cứ, không là runtime PASS

- **Historical/default chain:** text trước marker COMMON bằng candidate01, giữ M1–12/full-M9 historical definitions/helpers; literal registry4527 chỉ prefix1–12+COMMON13+M5 14. Không gọi/render/apply SQL hoặc nghiệm thu M9. Current unit checksums cần root definition-only pin riêng, không tái dùng old13/14 checksum.
- **S06:** postgres150–158/178–180 giờ whitelist exact historical-prefix checksums+approved predecessor, thay len-only bypass. **S05 partial-table/marker:**90–108 đã từ chối tables-without-history và missing marker; I-S02 non-table state vẫn mở, không gọi S05 fully closed.
- **S01/S02 trust boundary:** stage3173–3205 owner-only INVOKER/immutable/current actor; capture consumer3571–3608 nhận stageID/H/purpose và rechecks INTAKE/namespace/role-envelope consistency. Typed consumer4079+ lấy facts từ CAPTURE stage, không app JSON typed override. Producer actual-byte/hash/reader validation thuộc service review, chưa coi facts đã đúng chỉ vì stage tồn tại.
- **S03/S04:** intake/review/file cùng logical advisory→root row; review4276–4277 chỉ chấp nhận latest observation. Old-A chọn lại với currentB refs bị chặn ở control flow; reversal vẫn có thể accepted/eligibleNULL. Business-key rank/quantity eligibility vẫn chưa đóng.
- **Core quantity projection/R3:** owner3401–3464 backfill oldHOP_DONG→CRM/allothers→M1 (oldPHIEU gồm), NOTNULL/CHECKCRM,M1,M5; INVOKER actual-table-owner M5 guard. Header4140–4145 real date/DANG_XU_LY, nullable financial fields; lines4165–4169 explicit no/coNULL. Defaults0 legacy giữ, nonM5 line no/coNOTNULL được trigger bảo toàn. Semantic dedup4131 trước core inserts; typed refs3882–3887/3922–3926 giữ NOTNULL+PN/header/content/STT graph, logical-line identity riêng. Final R3 producer/precision/current-graph oracles còn phải chạy.
- **Receipt/file provenance và ACL:** M5 receipt3380–3398 NEW/OLD owner-only, lo3466–3494 owner-only/immutable/purpose/exactm5-xuat SHA path; app không forge M5 lo→m0-raw bằng ordinary INSERT. Core RLS3500–3558 replace owner paths/legacy USINGtrue; final thêmlo/work legacy isolation3525–3551. New COMMON/typed tables revoke inherited legacy ACL, M5 typed appSELECT theoPN/M5; guarded public EXECUTE list4493–4522. Mapping definer4311–4313 và INVOKER trigger3313–3317 giữ BOTH SOURCE_MAPtargetPN+M5/CFO/V4, không còn helper-permission failure của01; mapping namespace retry vẫn mở.

Không có PG/HTTP/GUI/test PASS mới trong review này. Period-closing race/catalog actual/grants ordinary positive/forgery negative, full artifact inventories, service same-connection transaction và coherent file producer cần bằng chứng sau root release. Giữ toàn bộ failures/DB/files; không cleanup, không stock/value/journal engine, không M9 resume hoặc source-app thay đổi. Candidate02 có tiến triển rõ nhưng chưa đủ nghiệm thu COMMON/M5/full33.
