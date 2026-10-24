# CRM-41-02 — G1 mẫu DOCX / G7 chuẩn dự án tối thiểu / S6

**21/10/2026 · CODE_ONLY KHI ROOT PHÁT RELEASE · SELFTEST/INDEPENDENT NOT_RUN.** Triển khai phần G1/G7/S6 đã chốt theo A1/A2; Claude là product writer duy nhất. Root chỉ phát sau actual terminal và baseline C4; tài liệu chưa thay execution authority của controller.

## 1. Authority, baseline và đích giao

1. Authority đã chốt: draft04 SHA69337720c00291d0622b8b5c4c63e6284a71ab38f3c22a0e4b0bffdc9270d3da và A1/A2 dưới đây; không yêu cầu đọc private preparation files, không đổi business policy.
2. A1 `docs/CRM-42-00-MA-TRAN-MAN-HINH-VA-CA-KIEM.md` SHA68acd97632c2958f7f9908df630402b16cca2c3df4e28f99bc46f18ff2c6a34b; A2 `docs/CRM-42-00-DELTA-DU-LIEU-API-QUYEN.md` SHAe21551eab629bca2a6f411390392a330bde2bf304bae4c484e9638d98dca2f68. A1 S6:224–236 có KT Trả lại mẫu; A2 G7 là KT lập/gửi CFO, CFO duyệt, API trả 4 cột/CHUA_CO, không thêm G7 return lifecycle.
3. C3 đã terminal handle48960/output082b72; frozen `m4c3-runtime-frozen-23d9dbf37547/files`, source352 SHA4ec6b3b29e4aabcbe909ddaa6d58279d7db5bf175c667c53ead5b8c7a43c0644, runtime418 SHAef6f061b7249f7bd4a0f0718f747a3af830951d2488df32f3fa0bd2d4b96cb66. Receipt f9a22f8e5a698e39d4c52b0d03fb83144a16e3ab107faf6ae3cc9728ad9f4e0b là scope-clean/code-only, không full GUI/M4 acceptance.
4. `SOURCE-BINDINGS-C3.json` ghi đúng 11 source tham khảo và 14 write targets; 6 existing +7 new code/tests +1 new report, source352→360 nếu Root giữ pathset này; 346 baseline existing còn lại phải nguyên byte. Không để Claude đọc private var/oracle.
5. Giao được ngay sau Root release: G1 upload DOCX → discovery thật → map/version → synthetic preview → KT kiểm/Trả lại → CFO+CRM+V4 approve effective version; G7 chuẩn dự án/giai đoạn 4 cột; màn S6 vận hành các nút này. Không phụ thuộc full M4 Review/PDF/AP/Request.
6. Không làm G2 FX/báo giá, G3 renderer DOCX/PDF, G4 bản ký, G5 sampling, G6 A-EFF, G8 tổng hợp; không sửa CRM-B CFO+V3, M1/Junsky/M4/M9, không tạo lịch thu/công nợ/thuế từ mẫu/chuẩn. Q_RETURN bản ký, PII thật và sampling chỉ chặn nhánh tương ứng.

## 2. Scope 14 targets, không mở thêm framework

| Loại | Exact target — prefix source là `src/kho_tri_thuc/` |
|---|---|
| Existing 1–3 | `ha_tang/pg_migrations.py`; `k2/quyen.py`; `giao_dien/server.py` |
| Existing 4–6 | `giao_dien/assets/index.html`; `giao_dien/assets/app.js`; `k2/crm_khoi_dong.py` |
| New 1–3 | `nguon/mau_docx.py`; `k2/crm_mau.py`; `giao_dien/crm_g.py` |
| New 4–5 | `k2/crm_g_demo.py`; `giao_dien/assets/crm_g.js` |
| New 6–7 | `tests/test_crm_41_02.py`; `tests/test_crm_41_02_http.py` |
| New report | `docs/BAO-CAO-CRM-41-02.md` |

`crm.py`, `store.py`, M4 source/UI, old tests/fixtures/SQL tuples 1–17 và all original apps giữ nguyên. Không renderer/job framework/launcher/config thật/dependency mới. New targets đều vắng trong actual C3; Root phải recheck ngay trước dispatch.

## 3. Actual seams và các phần thực sự còn thiếu

| Actual C3 source / anchor | Reuse hoặc bổ sung hữu hạn |
|---|---|
| `pg_migrations.py:9594–9597` | Active 1–12 + COMMON13/M5-14/M2-15/L11-16/M4-17. Append next migration riêng (18 chỉ được chốt bởi Root release), không sửa checksum/prefix hoặc bật legacy full-M13. |
| `pg_migrations.py:148–159,287–300,1262–1266` | Reuse `master.du_an`, `master.loai_hinh_doanh_thu`; typed FK đúng existing UNIQUE `(id,phap_nhan_id)`. Không master/project/type song song hoặc HĐ giả. |
| `pg_migrations.py:569–589,1092–1098,1154,1187,1437–1448` | Reuse `kho.viec_can_duyet`; active generic completion guard chưa đủ typed template/standard. Legacy resolver1780–1818 không active, không dùng. |
| `k2/crm.py:51–73,96–109`; `quyen.py:61–95` | Reuse identity/date/audit/transaction patterns; CRM HĐ methods không phải template approval. Thêm action assignment/scoped helper đã duyệt A2, không enum PHAP_CHE hoặc auth framework mới. |
| `server.py:164–234,256–284,447–465,873–892` | Same cookie/token/session/mutation lock; `_crm_db` chỉ chuyển code; `_m5_ket_noi_chu` mở validated same-endpoint/table-owner connection. New `crm_g.dich_vu(app)`/cache dùng các seam này; thiếu owner config phải báo explicit, không fallback ordinary machine writes. |
| `store.py:23–46`; `m4/docx_an_toan.py:48` | Retained `.ktt-staging`, immutable hash/no-overwrite giữ nguyên; có thể gọi pure TrackChanges checker sau ZIP bounds. Chưa có placeholder parser; utility này không thay engine discovery. |
| `app.js:709–722,1563`; `index.html` | `window.kttChung.{dangKyVai,vaiDangChan,doiVaiTuanTu,node,empty,toast,size,date}` đã có. New `crm_g.js` đăng ký một participant, mount S6 sau APP; giữ CRM landing/old routes/M4/M9. APP C3 SHA6e63fd52fc9b96d59bf8f61738539ea17b62909578394658f912f468d084ac91. |
| `crm_khoi_dong.py:203–225` | Additive `crm_g_demo.khoi_tao` hook sau seed cũ, trả trạng thái thật; không reset/regrant actor/revocation hoặc fake approved template/standard. |

## 4. Typed schema/DB boundary tối thiểu — toàn bộ là phần thêm mới

- Root `master.crm_mau`: `id,phap_nhan_id,ma_mau,loai_hinh_id`, unique PN+ma_mau; immutable `crm_mau_phien_ban`: root/version/state/raw SHA+length+retained reference/parser version+facts digest/catalog version/current-map/current-check/valid_from/valid_to. FK root/type/PN kín; facts/member records owner-only.
- `master.crm_mau_anh_xa`: immutable version/revision/ordered occurrence→field mappings + catalog digest; `master.crm_mau_kiem_tra`: immutable KT-check pin version/raw/facts/catalog/map revision+hash/actor/time/result. Change map invalidates current-check pointer, giữ old check/history. Không ordinary app INSERT machinefacts/check/receipt/FINAL.
- `master.crm_danh_muc_truong`: versioned field key/type/PII metadata, type-of-contract scope; dùng một catalog, không song song field authority. DEMO catalog/actors được Root khai báo và publish hữu hạn trước launch; private expected assets không phải input hay authority.
- `master.crm_bo_chuan` root PN/project/giai_doan + immutable version/ordered rows. Bốn cột hiển thị **Lần | Giá trị | Mốc thời gian | Ghi chú**; retain typed percent/amount-minor/currency/date-or-event/order. Exact decimal string, NULL≠0; không FX/VAT/base, không đổi event thành date hoặc ép tổng100% từ rule G2.
- `master.phan_cong_hanh_dong`: current assignment `(user,PN,CRM,action,optional_type)` với revoked history/unique nullable-scope kín; helper `master.ktt_hanh_dong_duoc` theo A2, vẫn require active identity/module/current role. Owner/admin admission, chỉ actor MO_PHONG mới; không reset grants thật/cũ.
- NEW typed K5 resolver/INVOKER guard chỉ hai subjects `master.crm_mau_phien_ban` và `master.crm_bo_chuan_phien_ban`: exact existence/same PN/module CRM/V4; branch **OLD typed OR NEW typed**, cấm retarget ref/PN/module/loai cả generic→typed và typed→generic. Actual current_user phải là relation owner của guarded write; không member/GUC bypass.
- Domain phase CHO_KIEM/CHO_CFO thuộc version/DTO; **không chèn các giá trị này vào K5 `trang_thai` CHECK** hiện chỉ CHO_DUYET/DANG_HOI/CHO_BO_SUNG/DA_DUYET/BO_QUA/DONG. Một K5 ID xuyên phase, KT-return về CHO_BO_SUNG rồi resubmit; CFO decision+K5+audit+receipt cùng transaction, không approval table song song.
- Typed K5 guard chặn ordinary INSERT/UPDATE/DONG/BO_QUA/DA_DUYET/reopen/retarget; typed scoped-read phải phủ mọi state kể cả closed, có hiệu lực qua các permissive legacy policies. Giữ positive generic M1/CRM/M4 behavior cũ; không nới common guard để hợp thức hóa template.
- Owner-only domain receipt provenance; namespace `(PN,actor,action,key)`, immutable FINAL. Current rights trước lookup; exact same body/key replay cả sau own/later revision phải zero DB/catalog/seq/audit/K5/file delta, không reparse. Changed H→409 trước parse/stage/blob; chỉ fresh intent mới CAS token. One same configured privileged connection/transaction, không app+owner self-lock.
- Detail/map/check/history/capabilities/token một owned REPEATABLE READ aggregate; refuse unsupported outer transaction. Lock namespace→root→version/map/check→K5; không mixed READ COMMITTED DTO/token.

## 5. Service / HTTP contract để coder triển khai, không giả API hiện đã có

`CrmMauK2(app_conn, artifact_root, *, conn_tin_cay, chi_mo_phong=True, hom_nay=...)`; public method luôn có `dang_nhap` từ server session. Browser không cấp actor/PN authority/facts/path/approval.
Methods: `danh_sach`, `chi_tiet`, `tai_mau(raw,loai_hinh_id,ma_mau,ten_tep,khoa)`, `luu_anh_xa(version_id,map,expected_graph,khoa)`, `gui_kiem`, `kiem_mau`, `tra_lai_mau(version_id,ly_do,expected_graph,khoa)`, `duyet_mau(...,valid_from,...)`, `tu_choi_mau`, `xem_thu`, `so_sanh`, `tep_mau`; G7 `lap_bo_chuan`, `gui_duyet_bo_chuan`, `duyet_bo_chuan`, `doc_bo_chuan(project_id,giai_doan,as_of)`.
GET `/api/crm/mau`, `/mau/{id}`, `/mau/so-sanh`, `/mau/tep/{version_id}`; POST `/mau/{tai,anh-xa,gui-kiem,kiem,tra-lai,duyet,tu-choi,xem-thu}`; G7 GET `/api/crm/bo-chuan`, POST `/bo-chuan/{lap,gui-duyet,duyet}` (tất cả dưới `/api/crm`). Giữ **POST `/api/crm/mau`** nhận #6 DEMO cũ; không collision với new GET list.
Exact special routes trước generic UUID và trước old catch-all `/api/crm/`; new thin HTTP module giữ authorize/token/session/mutation-lock. `crm_g.js` thêm static allowlist ở server.py:889 và defer sau APP. JSON strict unknown-field reject, binary upload bounded metadata; code map403 quyền/404 hidden target/409 CAS-idempotency/400 shape/503 owner config rõ ràng.
Read nguyên DOCX/version current quyền trước registry/path/hash read; escaped synthetic fake-preview không render Office/PDF/PII. BH chỉ effective đúng scope; KT/check và CFO draft/history theo quyền riêng. Dùng current session UI role selector, không manual UUID/factor/DSN hoặc actor authority trong body.

## 6. Lifecycle, parser và S6 có thể nghiệm thu

G1 DRAFT→CHO_KIEM→CHO_CFO→approved interval; KT/KTTrưởng có CRM/scope được trả từ CHO_KIEM về DRAFT với reason, current check inactive, giữ mọi raw/map/check/history và cùng K5. BH hoặc CFO giả KT/return approved deny; CFO TU_CHOI là action riêng từ CHO_CFO. Map sau check stale approval deny; approved raw giống tạo version mới, không sửa version/HĐ cũ.
CFO+CRM+V4 approve pin check/raw/map/catalog/facts; no overlap root interval; future version không che current as_of; chỉ successor audited đóng valid_to. G7 KT lập/gửi→CFO+V4 duyệt, read theo project/stage/as_of; missing trả `CHUA_CO/version:null/rows:[]`, không “lệch” và không sinh `lich_thu`.
Pure `doc_mau_docx(raw:bytes,*,limits=...)`: no file/actor/I/O/Office/AI/network; raw/member SHA, parser version, names/count/order/part/paragraph/run/joined-text spans. Không native byte-span giả/ET.tostring hash. `{{ten_o}}` có thể map field khác tên, đúng catalog/type/version; required field absent chỉ warning, unmapped/typebad/INCOMPLETE block approve.
Validate bounded ZIP/XML trước traversal: dup/traversal/encrypted/bomb/macro/active-content/DTD/entities/externalrel reject; body/table/nested + thực referenced header/footer. Ghép w:t qua runs chỉ cùng paragraph; không ghép p/cell/part. Unsupported visible channel/TrackChanges phải reject hoặc INCOMPLETE chặn approve, không lặng bỏ sót.
S6 thật: list/version upload/discovery/map/synthetic preview/KT kiểm+Trả lại/CFO duyệt+Từ chối/effective comparison/original download; tab G7 4 cột/submit/approve/as_of. 1280–1440 readable labels; mount nhỏ trong shell, không làm bảy màn rỗng hay đổi S1 landing.
Register actual `kttChung.dangKyVai`: synchronous clear S6/preview/selection/keys/generation, block GET trong shared role pending; fence role/form/tab/version sau every await, headers/blob/error và post-success refresh. Unknown upload retry giữ original File/body/key; không refetch sample, không tự key mới, không overwrite nháp mới. Những patterns C3 đã sửa là seam tái dùng, không chứng nhận fullGUI.

## 7. Acceptance mapping sang draft04 — native/independent/GUI tách riêng

| Nhóm | Oracle hữu hạn bắt buộc, không dùng testname/setup failure làm PASS |
|---|---|
| A01 = D4.9.1 | Literal DOCX discovery nhiều part/split runs/duplicate occurrences/nested/header/footer; no cross-boundary join; 7 hazards failclosed. Root có 9 DOCX độc lập đã tạo, private oracle không cho coder đọc. |
| A02 = D4.9.2 | Nonempty upload→map khác tên hợp lệ→KT→CFO+V4→effective; required-absent warning vẫn có positive; unmapped/fake facts/direct DML/KT+V4/noV4/crossPN deny chính xác. |
| A03 = D4.9.3 | KT return reason + cùng K5/currentcheckinactive/history preserved→resubmit/check/approve; BH/CFO giả KT/emptyreason/approved-return deny; separate CFOreject; typed retarget/terminalclose/reopen/closed-read qua inherited roles deny; generic old positive. |
| A04 = D4.9.4 | Map-change invalidates check; v2 rawsame/mapdifferent; old raw/map/check/file/HĐ unchanged; future/as_of đúng và two-approval same-root không overlap. |
| A05 = D4.9.5 | Exact original-body replay own/later revision toàn rows/catalog/sequences/audit/K5/files0delta; changedH409 beforeeffects; active role/action revoked denies replay/download; no DELETE/cleanup probes. |
| A06 = D4.9.6 | G7 nonempty ordered 4-column schedule, typedNULL/0/date/event/currency, KT→CFO, CHUA_CO/future effective/crossPNproject; zero money obligation delta. Không G7 return route. |
| A07 = D4.9.7 | Real HTTP/session/token/raw authority; S6 shared pending-role/late GET/POST/download fences và one actual current-role positive; original DOCX download hash. Native test files có fixture DEMO retained, không private Root helper imports. |
| A08 = D4.9.8 | Root mới chạy regression CRM-neutral/M1/K5 phù hợp sau terminal/freeze/FULL. Report code/selftest/root-static/runtime/GUI riêng; không allCRM/M3/M4 acceptance từ finite DEMO. |

## 8. Điều kiện phát gói và giữ baseline

Mọi execution phải dùng Root release + actual C4 terminal/current source baseline đã ghim. C3 ở §1 là provenance của schema/current17 và shared seam, không tự thay final C4 baseline. Root bảo vệ literal17prefix/old modules,14write targets và mọi fixture/report cũ; Claude chỉ Read/Glob/Grep/Edit/Write, không tự chạy/import/test/SQL/AI/network hoặc xóa/cleanup.
Không chờ full M4 Review/PDF/AP/Request, signed correction, PII thật hoặc sampling để thực hiện G1/G7 đã chốt. Root publish hai readonly technical inputs bên dưới trước launch; đó không phải write targets của Claude và không mở rộng14targets.

## 9. Technical DEMO và actual prefix17

Readonly **`docs/CRM-41-02-DEMO-INPUTS.json`** phải là byte-exact literal đã Root/FULL/peer CLOSED, SHA **7faa27ca4f5ce70f7ddeb909e9e2ab025ea884052c4c02af83f1c7230874653e**. Nó chốt4fields/8newactors/2uploadassignments/10technicalaction names và business-key resolver PN_DEMO_A/B, typeDT-KCN-THUE-DAT-DEMO@2/DT-NHA-O-DEMO@2, projectDA_KCN_DEMO/DA_NHA_DEMO. Mapping ho_ten→ten_hien_thi_demo hợp lệ; required gia_tri_hop_dong vắng chỉ warning. Không PHAP_CHE/newmaster/oldgrant reset hoặc seed approval; current assignment/CRM/KT-vsCFO/V4 vẫn enforce đúng draft04.
Readonly **`docs/CRM-41-02-MIGRATION-PREFIX-17.json`** phải là completed binding đã Root ghim, SHA **c698764baa4e15febbe6ee6cc091c7612110539842621428d165b8d286a5d75d**;17actual checksums lấy từ Root readonly owned freshDEMO17 export SHA **aa62504c7015e1d42387473b4554d2b22b5e1564add5e4fb42d8f1baf471547e**, transaction read-only/connection closed/whole352+418 prepost unchanged. Ordered17 digest **010a5da17d75072db462c60dcd7247f83e1fd3241efb956b5b79a94ee6c075a9** dùng ASCII `version:checksum` + LF cho từng version1..17, có finalLF; không phảiwhole-fileH haystatement-count estimate. Statement counts13–17 không có trong export và không được bịa.
Append **`M0018_CRM_G`** sau đúng active1–17, schema18; không sửa tuple/checksum cũ/importedM17, không alias legacy10/fullM9-13. Actual existing17 đã đầy đủ trong completed input; chỉ checksumM18mới phải Root bind từ sản phẩm sau terminal. Completed input chưa tự cấp code/runtime authority; Root release vẫn phải ghim actual final C4baseline.
Không đọc private var/oracle/source-assets hoặc lấy expected facts từ verifier. Gói literal không cấp quyền thật/cài template/check/CFO decision/standard/K5completed, không là complete KCN/nhàở policy. Native/independent/GUI chỉ được ghi kết quả thực tế theo §7.

## 10. Root: baseline C4 và cách append M18

C4 đã terminal thực tế: handle69281, output59ecd1; native exit0/success, stop/scope đúng. Root freeze source352 SHAa6aa7f3c0bdb323a85f8d6dc2b936a7784531d8fb6ef6ccc8f788d4baa3f5c29 và runtime418 SHA47c292d919ce3a11164bfa5a0d786aef93f43c0df0194dce61daf79821a65965; receipt6f2072efe88813e4732553a6a1e2cb33b5c480e57b7af0d69e7e86113132a6ea. Đây là final source baseline thay C3 ở §1 cho lần giao này; C3 vẫn là provenance của 17 SQL checksum. Root release riêng sẽ ghim kết quả kiểm hữu hạn C4 trước khi phát lệnh CRM. Không coi C4 code-only là GUI hoặc toàn M4 đã nghiệm thu.

M18 dùng cách append, giữ nguyên toàn bộ **791902 byte đầu** của `src/kho_tri_thuc/ha_tang/pg_migrations.py` (SHA36ed5ad1035f3cf85593cbfdc2e5ca84b3a73ecffd1df010aa4987d6826b3964). Định nghĩa `M0018_CRM_G` ở cuối phần thêm mới, sau đó append `PG_MIGRATIONS = (*PG_MIGRATIONS, M0018_CRM_G)` và `PG_SCHEMA_VERSION = len(PG_MIGRATIONS)`. Không sửa registry/tuple/helper/checksum của 17 migration cũ hoặc file M17 được import, không tách thêm file ngoài 14 targets. Đây là ràng buộc kỹ thuật để bảo toàn lịch sử hiện có, không đổi nghiệp vụ.

Hai JSON technical inputs ở §9 chỉ là dữ liệu khai báo đã rà soát; các nhãn code/runtime false hoặc C4 future-null trong provenance cũ không thay Root release hiện hành. Chỉ Root release có actual C4 terminal, manifest và kiểm hữu hạn mới cho phép Claude viết 14 file trong gói này; không có quyền tự cài migration, chạy test/SQL/AI, hoặc thay dữ liệu thật.

## 11. Sửa setup test C4 trong cùng lượt, giữ nguyên mọi assertion

Root chạy actual C4: 5/5 contracts upload độc lập đạt; native đạt 12 nhóm, nhóm cuối dừng ở setup vì sau refresh selector mẫu được dựng lại với giá trị rỗng. Test bấm mẫu lần hai khi chưa chọn lại nên không phát GET. Chỉ thêm lại thao tác chọn mẫu sau dòng `const soGet2 = dem(get("/api/m4/mau/hop_dong.docx"));`, trước nút bấm kế tiếp:

```javascript
    $("m4f-nguon-mau").value = "hop_dong.docx"; $("m4f-nguon-mau").dispatch("change");
```

Thêm đúng dòng trên vào **`tests/m4_01c_async.cjs`**; không sửa assertions, fixtures, product M4 hoặc ca kiểm nào khác. SHA sau đúng sửa setup này phải là **f77bdfe66772a2494d36f40cb1f2119d27af351ae8f101b1a3dc42bd9274a9d2** (bản gốc d744d1b02a85c2e52849ab5999cb90a514de5f0ea8cc31999afb45b14c1f992e). Root đã xác nhận bằng diagnostic setup riêng không sửa file gốc; chưa gọi native chưa sửa là PASS.

Scope thực thi cuối gồm 14 targets CRM ở §2 **cộng một test setup này: 15 targets = 7 existing + 8 new, bảo vệ 345 existing**, source352→360. Các đoạn nêu 14/protected346 phía trên là scope CRM gốc; chỉ mở thêm đúng test setup này, không tính là tính năng hoặc module mới. M4JS vẫn giữ nguyên. Báo cáo CRM ghi riêng sửa setup; self-test của Claude vẫn `NOT_RUN_CODE_ONLY`. Root sẽ chạy native thật và regression liên quan sau terminal; không bỏ qua ca đang lỗi hoặc thay bằng kết quả diagnostic.
