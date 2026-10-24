# CRM-41-01 FIX04 — Integrity còn thiếu và chặn endpoint legacy

1. Root đã review và cho phép một lượt CODE_ONLY sửa đúng R1–R5 dưới đây, cùng session Claude hiện hành. Đây là chỉ dẫn code, chưa là kết luận nghiệm thu.
2. Baseline F9: `crm-41-01-fix03-frozen-24f2ce525f40`, actual 88779/998ea1; source370 `83c7cdcf6c7bd05b291200f27b5b53f5ac473a91ab56af9f4046eded4175cae5`, runtime438 `1b4a11b581e088abc4d02e597febfe5324dde2d4e7bf18d04ef41ed3077544ea`.
3. Root đã áp patch kỹ thuật vào source thật có backup: `source6-apply-33558ed4aa71/receipt.json`, source37 `d8c442620c9e44c67b0f7a90680af6edf8f14741d6bb4ed2a3d40ebb80ef37f1`; chưa nghiệm thu toàn module.
4. Actual source native18: 18 PASS/0 fail/0 error/0 skip, 26,651 giây; parent/child đều posthash true, server thread joined, Job đã dừng. Không có native failure bổ sung vào brief.
5. Bốn finding source và guard client dưới đây là counterexample static; không gắn nhãn đã runtime FAIL. Giữ mọi assertion của 18 native tests và central tests đã đạt.
6. Tuân thủ quyết định một engine #6/common/v1: không fallback core chép, không AI/cloud/SQL/approval/master tự động; workflow M4/CRM vẫn riêng.

## 1. Phạm vi đề xuất chính xác 6 file hiện có, NEW0

- `docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py`
- `docs/CRM-41-01-SOURCE-PATCH/may_chu/server.py`
- `docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py`
- `src/kho_tri_thuc/nguon/trich_chung_6.py`
- `tests/test_trich_chung_6.py`
- `docs/BAO-CAO-CRM-41-01.md`

7. Giữ nguyên CRM service/UI, M4 adapter, vendor, catalog, ba file thuật toán, các migration 1–20 và M9. Chỉ sửa staged source; Root kiểm hash/backup rồi tự áp dụng vào source app sau terminal, coder không được viết source gốc.
8. Source anchors dưới đây là F9 `may_chu/dich_vu.py` 1943 dòng/H`b595b9cce875e7ae5d006ada55cb1d3a4eb667cc70ee14737b0b51a22ba48252`; client392/H`b86fd12b3ef3d9dedde4646a139b53271f0f266a9af6fdac9391bcf124bf7796`.

## 2. R1 — Registry không được đổi sang lượt trống chưa từng giữ

9. `luot_moi_common` 434–443 kiểm occupied target nhưng nếu registry `luot` bị đổi bằng JSON hợp lệ sang tên regex-valid chưa tồn tại thì `d.exists()` false và vẫn mkdir/link mới. `_kiem_ban_ghi` 464–482 chỉ kiểm regex/identity body; body hash không ràng buộc trường `luot`.
10. Ràng buộc target luot với reservation đã chọn bằng dữ kiện bền có thể kiểm độc lập; không lấy tên luot vừa bị sửa rồi băm lại làm expected. Khe ghi thật sau reserve vẫn phải đối soát đúng target cũ, hoặc UNKNOWN có lý do; không cấp/chuyển sang target khác.
11. Test: positive reserve/replay trước; CreateNew backup registry DEMO rồi chỉ sửa `luot` sang tên hợp lệ còn trống, giữ body/hash cũ. Require 409 `COMMON_CHUA_RO`, target mới không xuất hiện, không compute, original luot/registry/history còn nguyên theo baseline sau mutation. Giữ counterpart occupied legacy target của c18.

## 3. R2 — Cached done vẫn phải kiểm snapshot HĐ/catalog đang tồn tại

12. `_nap_lai_common` 605–606 trả cache; `_cong_bo` 489–502 gọi `_kiem_seal` 691–723 chỉ kiểm request/raw/seal, không kiểm SHA snapshot HĐ/catalog tại 635–639 nếu cache đã done.
13. Gate công bố terminal phải kiểm lại đúng immutable input/catalog snapshots, canonical request và seal bằng dữ kiện của lượt, kể cả cached done; không cần restart/pop cache để phát hiện, không rerun/overwrite khi hỏng.
14. Test positive nonempty done còn trong COMMON; backup rồi mutate riêng bytes snapshot DOCX và catalog, không pop COMMON. Status/list/viec phải UNKNOWN có lý do; raw/view/download không mở kết quả. Lặp counterpart sau restart; toàn history/output không phát sinh compute hay ghi đè.

## 4. R3 — DTO typed phải kiểm cả giá trị reachable, không chỉ container

15. `_kiem_dto_luot` 541–557 chỉ kiểm `tep` là dict: `_luot.json.tep={"x":["bad"]}` vẫn qua, `_bo_sung_tai` 1116 ghép Path/list có thể TypeError. `log=[[1e300,"demo"]]` qua numeric553 rồi `_chi_tiet_common` 1161 localtime có thể OverflowError.
16. `_luot_da_dat_cho` 368–372 còn đưa `registry.luot=[]` vào set trước validator khi tạo intent khác. Mọi đường reachable phải kiểm typed fields trước hash/set/path/time conversion; lỗi dữ kiện common thành UNKNOWN có lý do, không generic 500 hay bỏ qua identity.
17. Test valid JSON từng mutation độc lập, các field khác từ positive thật: status200 common UNKNOWN/reason; raw/view409 `COMMON_CHUA_NIEM_PHONG`, không mất history/rerun. Kiểm create intent khác gặp registry luot sai kiểu cũng trả finite common UNKNOWN; không coi generic exception là PASS.
18. Giữ branch legacy tương thích và positive DTO bình thường; không harden hay viết lại toàn ứng dụng legacy.

## 5. R4 — Empty catalog command vẫn phải bị common immutability gate chặn

19. POST `/api/trich_xuat/{luot}/danh_muc` (server283–285) với common vừa create/upload chưa có result, không truyền `ten`: `ghi_lai_danh_muc` 1244 cho `tens=[]`, bỏ `_json_hd(...,ghi=True)` tại1245 rồi gọi `ghi_danh_muc`1247.
20. Source `xuat.py` 256–258/353–355 vẫn có copy/save/replace workbook khi `ds=[]`; vì vậy gate common phải nằm trước enumerate/empty shortcut và trước mọi workbook I/O, không chỉ trong vòng lặp từng result.
21. Test common pending/empty result và done đều nhận finite `COMMON_BAT_BIEN` (hoặc exact existing common mutation-denial contract được Root bind trước run), no workbook I/O/zero effect; có legacy non-common positive control. Chỉ dùng retained DEMO workbook từ HD env, không workbook thật/global.

## 6. R5 — Preflight common trước create; ACK đúng intent trước upload/start

22. F9 client `tao_luot`197–204 chỉ nhận `.luot` regex; `trich`268→278→287 vẫn có thể upload/start vào endpoint cũ không có common. Original server238–239 bỏ body, trả legacy `{luot}`; original `dich_vu.chay_luot`383–425 đọc config/AI/cloud theo nhánh legacy dù request có contract/mode.
23. Với subset hợp lệ, nhánh cũ có thể đi tới AI/cloud; ALL string thường bị legacy filter thành rỗng rồi400, nhưng vẫn đã đọc config/catalog. Không khẳng định đã phát sinh AI runtime; đây là path static cần chặn.
24. Thêm preflight read-only cụ thể trước mọi POST common create: đề xuất GET `/api/trich_xuat/common` trong server/DV hiện có. Response typed công bố đúng common/v1, RULE_ONLY, loại/catalog được hỗ trợ và readiness từ actual pinned catalog/implementation; không AI/config-secret probe, không mkdir, ghi catalog/master hay health giả always-ready.
25. Client phải kiểm capability/readiness/contract/type/catalog identity trước create. Endpoint legacy404/body thiếu/sai kiểu/khác mode hay catalog phải fail closed, không POST create/upload/start và không fallback; lỗi preflight trước side effect phân biệt với UNKNOWN sau lệnh có thể đã có hiệu lực.
26. Sau create, require ACK `request_id` bằng đúng logical ID đã gửi, `type(lap_lai) is bool`, `luot` hợp lệ; kiểm trước lưu `10_luot.json`, upload/start. ACK thiếu/sai/khác ID sau POST có thể đã tạo lượt: giữ intent và UNKNOWN/not-supported có lý do, không FINAL LOI chắc chắn, không tạo ý định mới hay thử legacy tiếp.
27. Tests: true common positive; legacy `{luot}`; missing/wrong-id/non-bool ACK; malformed/not-ready/wrong-catalog preflight. Assert actual request ordering và zero upload/start; no config/AI sentinel hit; cùng ID retry đúng common vẫn dùng nguyên luot/body/key và no recompute.
28. Positive mock ACK phải khớp actual source DTO, không bỏ guard để fixture cũ qua. Native legacy API vẫn giữ hành vi cũ khi consumer legacy gọi trực tiếp; guard mới chỉ là common client/route đã chốt.

## 7. Kiểm và bàn giao

29. Giữ native18/central hiện có; thêm finite cases cho đúng R1–R5, positive trước negative, thread count/exception/join assertions đầy đủ. Không đổi literals hay lấy mutated/runtime output làm expected.
30. Mutation chỉ ở isolated DEMO snapshots sau CreateNew backup; giữ raw/catalog/source gốc nguyên byte. Snapshot các old file/path/hash/bytes và directories cần thiết để chứng minh không tạo free target; không DELETE/cleanup kể cả rollback.
31. Replay: DB/catalog/seq/all old files/published/history giữ nguyên; retained `.raw-*` diagnostics phải kê riêng exact parent/hash/bytes/bound count, không blanket-ignore và không gọi whole recursive files zero nếu có diagnostic mới.
32. CODE_ONLY: chỉ Read/Glob/Grep/Edit/Write trong đúng scope, cùng Claude session được Root bind; không shell/import/test/runtime/network/SQL/Agent/MCP, không tự áp patch vào source gốc.
33. Report existing phải đổi và nói rõ selftest NOT_RUN nếu coder chỉ viết; chỉ Root FULL review + actual bounded native/source HTTP/central two-consumer HTTP mới tạo bằng chứng tương ứng. Source18 PASS không phải central PG/GUI/full M4/CRM PASS.
34. Kiểm độc lập HTTP nguồn đã đạt 3 lượt thật (ALL37 và hai tập con chạy đồng thời), 7 loại từ chối, replay nguyên raw và xung đột đổi body; chỉ positive TC-01 được chấm literal, chưa phải độ chính xác trích toàn danh mục. Không đưa fixture/oracle kiểm độc lập vào mã nguồn hoặc dựa vào output để đặt expected.
35. Khi mã lạ được phát hiện trên catalog snapshot trước compute, source ghi lỗi capture là hợp lệ; giữ native test c03 và không buộc trạng thái này thành chua_chay. Đây không phải finding cần sửa.
