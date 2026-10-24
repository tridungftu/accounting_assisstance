# Review độc lập binding M5 vào core CRM03 — 01

**19/10/2026 — static docs/source review; chưa chạy product/import/test/SQL/HTTP/GUI.** Reviewer không viết binding M5 và không sửa binding/source. Không mở lại source app #10, actual rows hoặc secrets; không xóa file/DB/role.

**Kết luận:** ranh giới kiến trúc đúng; cần chốt **2 amendment P1 và 1 binding P2** dưới đây trước handoff code. Đây là thiếu/không rõ contract trong tài liệu, **không phải 3 lỗi runtime đã tái hiện**. Không bổ sung policy giá trị kho, định mức hoặc quy tắc duyệt nguồn.

## Baseline và các phần đã đủ rõ

- Binding M5 đã đọc toàn bộ: `BINDING-M5-CORE-SAU-CRM03.md` SHA256 `33488e3125a77776a2ed6b6b7b89802bd0fb10f33dbbbb4a5d55598540c92a8c`; draft M5 SHA256 `f4a5ad4895a7d1ffca1f9129ca8d7dac255527fd924e2e2957c0c098d9582d6a`.
- Frozen03 manifest121 SHA256 `82e5e26806e05ef732536fcb0e474ab6ee96f646566e335e728da28921f47c3a`; `frozen/src/kho_tri_thuc/ha_tang/pg_migrations.py` SHA256 `31f25277b5e08a0f54843191bce2b3e54126dc6770ad02ece310c8265fcac1e5`. Migration M0001–M0012 không sửa.
- TL35 đọc đầy đủ, §8.6 giữ số lượng ở M5, giá trị/242 ở Junsky. Binding dòng7/18–20/46/78/117 giữ #10 chủ CRUD/duyệt/đảo/kiểm kê/phép tính nguồn, producer thiếu tiếp tục là việc full M5 tại #10; không receiver stock engine.
- Dòng31–48 giữ M0 chung, source identity trước mapping không chứa target PN, derivative/provenance/snapshot scope và FK cùng PN; retarget sau promote phải hold. Dòng52–56 tách source approval khỏi V1 Nợ=Có và nhận đảo trên **cùng** SoPhieu.
- Dòng62–74 dùng parent HD_PHIEU_KHO EVIDENCE/moneyNULL + sibling chung `lien_ket_dong`, không money allocation/remaining riêng. Stable logical-line ở hai phía, confirmed/CAN_SOAT giữ reservation xuyên revision, explicit undo có tombstone, quyền trước replay, lock và DB whole-graph/action gate đã được yêu cầu. Đây là contract cần triển khai mới, không suy core12 đã có quantity engine.

## R1 · P1 — Tách content dedup khỏi lần quan sát trở lại sau đảo

**Neo:** binding dòng40 `UNIQUE(phiếu,semanticSHA)`, dòng46 kiểm kê unique theo semanticSHA; dòng54 replay cùng semantic không thêm version, nhưng dòng56/109 yêu cầu observation/history cho đảo→duyệt lại. Common M9 §3 snapshot unique(instance,profile,rawSHA), fetch mới có audit riêng: raw cũ có thể quay về đúng snapshot cũ.

**Ca cần bind:** A=Đã duyệt, link6; B=Đã đảo, link6 CAN_SOAT/held; lần lấy sau thấy đúng payload A cũ (reappearance, stale/out-of-order hoặc source khôi phục dữ liệu — chưa biết nguyên nhân). A cũ trùng semanticSHA và có thể trùng raw snapshot. Dedup nội dung hợp lệ, nhưng trả A cũ như một replay bình thường sẽ không biểu diễn lần quan sát A-sau-B và có nguy cơ chọn lại eligibility/approval/link cũ. Ngược lại, cấm nhận vì unique không thực hiện được yêu cầu tiếp nhận observation và mở SOURCE_REAPPROVAL_REVIEW. **Không khẳng định duyetPhieu thực luôn tạo payload giống A; đây là ca nhận nguồn mà contract phải phân biệt.**

**Amendment tối thiểu:** quy định semantic version là content hay transition. Có thể giữ content unique nhưng thêm thin typed observation/transition reference tới common fetch receipt + source row + logical phiếu + semantic version + predecessor observation/known_at; FK cùng PN/identity. Chỉ occurrence có căn cứ source event/transition mới được xét eligibility; không lấy fetch time làm business revision. Nếu chọn version theo transition thì phải chốt transition key, content vẫn dedup độc lập. Latest observation, latest accepted source state và current eligible semantic version phải có nghĩa riêng, không đơn giản MAX(version)/known_at của content cũ. Cùng quy tắc cho kiểm kê có status/history; không làm raw store thứ hai.

**Ca nghiệm thu:** A,A liên tiếp→0 content/business delta; A,B,A→giữ đủ thứ tự quan sát, A cuối thiếu history vẫn hold, reservation6 và old link IDs không đổi; stale A không vượt B; source transition mới có evidence hợp lệ mới được xử lý qua action riêng, không auto resurrect. Receipt retry của cùng lần lấy không thêm transition. Lần đầu chỉ thấy B không bịa A.

## R2 · P1 — Quantity child cần một encoding đo lường đủ để kiểm hai budget

**Neo:** dòng42/58 giữ native quantity/UOM/basis đúng nguồn; dòng66 child chỉ mô tả một `quantity numeric >0` và source UOM/basis; dòng69 yêu cầu SUM xuyên UOM/basis revision, cho conversion khi có căn cứ; dòng72 yêu cầu full held/confirmed quantity ở cả hai logical roots. Chưa bind rõ con số trên child được đo theo phía nào/canonical unit nào, hoặc hai native quantities tương đương ở hai phía.

**Ca cần bind:** invoice1 thùng, phiếu12 cái, chỉ khi source/profile có conversion1 thùng=12cái được duyệt. Child quantity1 có thể tiêu1 thùng nhưng chỉ trừ1cái; child quantity12 có thể tiêu12cái nhưng vượt invoice1 nếu helper SUM trực tiếp. Dù mỗi snapshot giữ UOM đúng, cùng một raw numeric không thể SUM vào cả hai native budgets mà thiếu contract measurement. Revision đổi display unit hoặc mapping PK không được mở lại capacity hay diễn giải link cũ bằng factor hiện hành.

**Amendment tối thiểu:** chốt một canonical measure/unit bất biến trên logical quantity pool và exact conversion proof, hoặc ghi rõ hai native consumed quantities + native UOM/scale + pinned conversion/basis version chứng minh tương đương. DB validator derive/check encoding từ typed source/profile/mapping đã duyệt, không tin factor/đơn vị client; FK giữ đúng source snapshot ở cả hai phía. Helper capacity đổi về cùng measure bằng proof đã pin trước SUM, giữ old held consumption; unknown/noncomparable/precision loss/không biểu diễn exact→blocked, không rounding hoặc factor mặc định. Nếu phase đầu chỉ hỗ trợ cùng UOM thì CHECK/validator phải chặn khác UOM tường minh, còn conversion là việc full M5 chờ contract, không coi đã đạt. Không tự chọn hệ số hoặc thêm valuation policy.

**Ca nghiệm thu:** same-unit positive; khác đơn vị thiếu proof bị chặn; proof12 được duyệt nối invoice1thùng↔phiếu12cái tiêu đủ đúng cả hai phía; split6+6, race hai connection và basis/unit revision không tiêu thêm; đổi factor không rewrite proof/link cũ, hold nếu continuity chưa được xác nhận. Cả API và direct SQL dùng cùng validator dưới lock; parent MONEY total không đổi.

## R3 · P2 — Chốt projection key và rebase interface invoice hiện hành

**Neo:** dòng40/42 mỗi phiếu version có `chung_tu_id UNIQUE` và mỗi dòng version có core-line riêng; chưa ghi cách tạo `khoa_nguon`/STT. Frozen03 `pg_migrations.py:207–233` có UNIQUE(PN,loai,khoa_nguon), ngày nghiệp vụ NOT NULL; dòng238–259 có UNIQUE(chung_tu_id,stt). Chỉ dùng SoPhieu làm khoa_nguon cho mọi version sẽ conflict; update/upsert row cũ sẽ phá snapshots/link history.

**Amendment:** dùng convention tương thích M2: key server-derived từ source identity + semantic-version identity đã chốt ở R1, có canonical encoding/version; cùng logical phiếu khác accepted content revision có core IDs mới, exact replay reuse IDs. STT là vị trí trong snapshot, không stable source-line identity; source ID_Dong/logical anchor/FK giữ riêng, reorder không reparent link cũ. Thiếu ngày ở M0 candidate, không fake ngày import để tạo core projection. M2 hiện SHA256 `001aefc2d7cb8e9d0b6017325c465c2f536962b56331d3ef08c44b3388c0eea2` đã khác pin e80064 của M5 dòng5; rebase/pin bản root duyệt, reuse `hoa_don_dong_danh_tinh` + snapshot bridge đã có trong binding M2 mới, không tạo anchor cạnh tranh.

**Ca nghiệm thu:** cùng SoPhieu hai content revisions giữ2 bộ snapshot core IDs, một logical phiếu và các logical lines ổn định; reorder lines giữ đúng old refs; replay0 ID mới; thiếu ngày0 business nhưng dated positive promote; M1/CRM legacy IDs/hash/migration histories giữ nguyên.

## Gate handoff

R1–R3 cần sửa **binding** và root review trước coder; không yêu cầu sửa nguồn #10 ngay trong core. Các gate đã có giữ nguyên: compatible migration sau12; FK composite/source derivative đúng PN; module/model/owner immutable; eligible source/current/route KHO/V2/V4 và fingerprint toàn graph tại DB; parent/child undo/source-revision cùng lock order; CAN_SOAT không free reservation; protected period/lô và scoped helper/file rights. Cần positive control trước denial, direct SQL bên cạnh API, và race observer sau coder terminal/freeze. Review này chưa nghiệm thu bất cứ gate runtime nào.
