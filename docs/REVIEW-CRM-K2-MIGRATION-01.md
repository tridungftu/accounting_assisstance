# Review độc lập CRM-01 — migration và ranh giới quyền

**Cập nhật runtime 19/10/2026 06:30:** sau khi root xác nhận CLI Claude exit 0, hai probe độc lập đã chạy trên hash bàn giao không đổi: SQL **7 đạt / 19 vi phạm**; service **1 positive control đạt / 7 vi phạm**. Không lỗi setup/binding, không test skip. Phần runtime và reproduction ở cuối tài liệu; các đoạn dưới ghi lịch sử quan sát khi coder còn viết.

Mốc đọc: **19/10/2026 06:13 +07:00**. Claude còn viết gói CRM; tài liệu này ghi nhận code đã xuất hiện, **chưa phải kết luận runtime hoặc kết luận bàn giao cuối**. Không chạy app/test trong lượt review tĩnh này.

File quan sát: `src/kho_tri_thuc/ha_tang/pg_migrations.py`, SHA256 `5f8f9361e5f2cb5bfeefb3c496b4cb310cf80209e3e08b73c4442200171c3d0b`. Số dòng bên dưới thuộc snapshot này, cần đối chiếu lại sau khi coder kết thúc. Runtime CRM mới thấy thư mục `k2` và profile DEMO, chưa đủ để đánh giá endpoint hoặc scope phiên HTTP.

## Sáu nhóm cần kiểm chứng/sửa

1. **P1 — INSERT bỏ qua gate kiểm/duyệt.** Baseline dòng 328 cho phép trạng thái phiên bản `DA_DUYET`/`TU_CHOI`; M0010 dòng 1150 cấp INSERT bảng phiên bản cho `app_web`, nhưng trigger dòng 1136 chỉ `BEFORE UPDATE`. DDL hiện không chặn app_web chèn thẳng bản đã duyệt mà không qua kế toán/CFO. Cần ca vai ứng dụng thường chèn DA_DUYET và ca kiểm/duyệt hợp lệ làm đối chứng; không dùng superuser để kết luận quyền đã đúng.

2. **P1 — Bản đã duyệt và nội dung con chưa được khóa.** Dòng 1108–1110 return ngay khi trạng thái và `kiem_boi` không đổi; app_web được UPDATE bảng phiên bản/tham số/lịch tại 1150. UPDATE nội dung `tham_so`, liên kết nguồn/hợp đồng hoặc người duyệt trên bản đã duyệt đi qua nhánh return; bảng tham số/lịch không có trigger khóa nội dung sau duyệt trong snapshot. Cần kiểm riêng cả ba bảng; phụ lục mới chờ duyệt vẫn phải làm được.

3. **P1 — Gate danh tính chưa fail closed và chưa gắn cùng danh tính RLS.** Hàm RLS dòng 1099–1102 đọc `ktt.nguoi_dung_id`; trigger dòng 1115 đọc login khác, rồi 1119/1130 chỉ so khi login khác NULL. Thiếu login vẫn có thể ghi tên một CFO có quyền; ID của phiên và login không được đối chiếu với nhau. Ca cần chạy: thiếu cả GUC; chỉ có ID; ID BAN_HANG + login CFO; ID/login đúng KT/CFO làm đối chứng. Chưa có bằng chứng endpoint cho phép người dùng sửa GUC; finding này nói về gate CSDL hiện hữu, không khẳng định exploit HTTP đã chạy.

4. **P1 — Tenant của dòng chưa ràng buộc tenant/quan hệ của FK.** `lich_thu.phap_nhan_id` tại 1002 độc lập FK `phien_ban_id` dòng 351; RLS dòng 926 chỉ kiểm pháp nhân trên lịch. FK tồn tại không chứng minh parent thuộc cùng pháp nhân, do đó lịch A có thể trỏ phiên bản B ở mức DDL. Các quan hệ khác cần cùng ca: hợp đồng → profile/dự án tại 308–309; con trỏ bản hiện hành tại 334–335; phiên bản `thay_cho_id` tại 973; lịch `thay_cho_id` tại 1004. Phải kiểm cả cùng pháp nhân nhưng khác hợp đồng/nghĩa vụ, không chỉ khác pháp nhân.

5. **P1 — Grants/RLS chưa khép kín quyền BAN_HANG và dòng con.** Dòng 1149 cấp SELECT toàn bộ master; 1151–1152 cấp SELECT de_xuat và de_xuat_dong. Danh sách RLS 921–935 không có `de_xuat_dong`, `chung_tu_dong`, `master.nhan_vien`; hàm phạm vi chỉ lọc pháp nhân, không xét module/role. Tại mức SQL, app_web có thể đọc dòng bút toán/nhân viên không qua policy tenant tương ứng; BAN_HANG còn có SELECT đề xuất cùng pháp nhân, trái TL40 §7 yêu cầu không thấy bút toán. Cần kiểm role thực, không tính việc menu ẩn là bằng chứng RLS.

6. **P1 — Upgrade v9 có link HUY hợp lệ bị constraint mới chặn.** Dòng 1020–1022 thêm ba cột hủy nullable; 1029–1030 lập tức yêu cầu mọi dòng HUY có đủ ba giá trị, không có backfill hay phân biệt lịch sử. Schema cũ dòng 559 cho HUY hợp lệ khi chưa có các cột đó. DB v9 có dòng HUY như vậy là ca upgrade bắt buộc. Không sửa bằng xóa lịch sử hoặc bịa người/thời điểm hủy.

## Probe chuẩn bị, chưa chạy

Private script: `var/codex-dieu-phoi/crm-k2-independent-probe-01.py`. Script chỉ được thực thi sau root xác nhận coder terminal, bật guard giữ file, dùng PostgreSQL localhost và credentials trong process. Tạo DB DEMO tên riêng và giữ lại; không DROP DB/role/file. Đây là scaffold chưa chạy, fixture hoặc SQL không hợp schema sau bàn giao phải sửa và ghi nhận trước khi dùng số pass/fail.

Phạm vi: migration PG mới; upgrade v9 có link HUY và checksum lịch sử giữ nguyên; vai app_web đọc dữ liệu đúng/chéo pháp nhân; INSERT approved; sửa bản đã duyệt/tham số/lịch; thiếu/spoof context; FK profile/project/current-version/replacement khác tenant hoặc khác hợp đồng. Test không chạy/skip/setup lỗi không tính đạt. Chưa đánh giá service, UI, lịch/phụ lục/payment link hoàn chỉnh từ review này.

Quan sát bổ sung để kiểm sau: trigger link 1036–1044 chỉ bảo vệ một tập cột khi UPDATE; kiểm các cột loại/hợp đồng/idempotency và provenance còn lại. Nhánh INSERT 1059 chỉ yêu cầu phiên bản DA_DUYET, chưa chứng minh chặn lịch phiên bản cũ đã bị thay hoặc chống race trên cùng nghĩa vụ qua nhiều phiên bản. Chưa kết luận lỗi runtime ở hai điểm này.

## Đối chiếu service vừa xuất hiện — 06:19 ngày 19/10/2026

Snapshot `src/kho_tri_thuc/k2/crm.py`: SHA256 `6936db70742446a255ac865553012ac086b4beb0c4df6bef0176221eaf19965a`. Claude vẫn viết, chưa chạy test/probe. Đã đọc thêm `k2/quyen.py`, `k2/crm_phan_tich.py` và `nguon/trich_hop_dong_6.py`.

### Gate service hiện có, không được bỏ qua khi mô tả findings SQL

- `_tx` dòng 42–45 đặt cả ID/login bằng `set_config(...,true)` trong transaction. Nếu connection đúng `autocommit=True` như yêu cầu constructor thì PostgreSQL tự kết thúc context local khi commit/rollback. Chưa có bằng chứng factory HTTP dùng connection/role nào; constructor chỉ nhận conn, không ép role hoặc autocommit. Không suy từ docstring rằng runtime đã dùng role thường.
- `duyet` dòng 296–306 có kiểm CFO/V3, CHO_DUYET, kế toán kiểm và tính lại điều kiện. `_tao_phien_ban` dòng 191–193 luôn INSERT CHO_DUYET. Vì vậy backdoor INSERT approved ở DDL chưa đồng nghĩa đã có endpoint INSERT approved.
- `cap_nhat_mapping` dòng 254–269 kiểm quyền, giới hạn GOC đang chờ, whitelist field, map ObjectID/dự án theo đúng pháp nhân. `lien_ket` dòng 386–387 chặn lịch không hiện hành khi xử lý tuần tự; cross-tenant/currency/số tiền còn dựa trigger DB.
- Re-extraction có cùng `word_hash` được giữ thành việc đối chiếu tại 130–137; phụ lục được tạo mới và kế thừa có provenance tại 188–210; không ghi đè bản cũ ở đường import này. Chưa xác minh runtime.

### Findings domain cần probe sau bàn giao

1. **P1 — Read service chưa kiểm module/hành động.** `danh_sach` dòng 429–471 không gọi `quyen.kiem`, dù hành động XEM tồn tại trong `quyen.py`. RLS chỉ lọc pháp nhân. Actor có quyền PN nhưng `module={}` hoặc vai DU_AN/NHAP_JUNSKY vẫn có đường nhận hợp đồng, tham số, raw envelope và toàn bộ SAO_KE trong PN từ service. Ca kiểm cần actor đúng PN/không CRM và actor CRM bị giới hạn role; kiểm cả gọi API trực tiếp.
2. **P1 — Phụ lục có ngày hiệu lực tương lai được dùng ngay.** Dòng 309–321 ghi ngày vào valid_from/valid_to nhưng lập tức thay con trỏ hiện hành; dòng 386 chỉ kiểm con trỏ, không kiểm thời gian. Cần ca phụ lục hiệu lực sau ngày kiểm thử: trước ngày vẫn dùng nghĩa vụ cũ; đến ngày mới áp bản mới; vẫn xem được bản đã duyệt sắp có hiệu lực.
3. **P1 — V3 đang đóng cả V4 mà không kiểm quyền V4.** `quyen.py:22` chỉ đòi V3 cho DUYET; `crm.py:324` đóng việc V4 của hợp đồng. Ca CFO có V3 nhưng thiếu V4 phải không tự hoàn tất việc V4 ngoài quyền; không lấy seed CFO có cả hai làm bằng chứng.
4. **P1 — Đổi mapping sau kiểm không làm hết hiệu lực lần kiểm.** Dòng 269 thay đối tác/dự án nhưng không vô hiệu hóa kiem_boi/kiem_luc; dòng 303 chỉ cần dấu kiểm cũ khác NULL. Ca: KT kiểm mapping A → đổi sang ObjectID/dự án B hợp lệ → CFO duyệt. Cần kiểm lại nội dung sau thay đổi, giữ lịch sử lần kiểm cũ.
5. **Cần probe concurrency — Duyệt phụ lục và nhận tiền không khóa chung contract/nghĩa vụ.** Dòng 299 đọc kế hoạch/tiền đã thu không FOR UPDATE; dòng 381/386 đọc con trỏ hiện hành không khóa. Gate tuần tự đúng không chứng minh hai transaction (duyệt đổi lịch chưa thu và link vào lịch cũ) không cùng vượt. Trigger link khóa receipt và đúng một lịch, nhưng chưa khóa cùng parent mà service duyệt dùng. Cần điều khiển hai connection theo barrier; không gọi race đạt chỉ từ hai tác vụ chạy tuần tự.
6. **Cần probe idempotency — Concurrent retry.** Dòng 375 SELECT khóa thao tác rồi INSERT tại 390, không xử lý xung đột concurrent. Hai request cùng khóa/payload có thể cùng qua SELECT rồi một bên nhận unique/over-allocation thay vì trả cùng kết quả. Ngoài ra nhánh retry trả trước kiểm quyền LIEN_KET_TIEN ở 385; cần kiểm actor khác vai với cùng request và trạng thái link đã HUY. Chưa kết luận semantics hủy/retry khi chưa có runtime UI/API.
7. **Cần kiểm khả năng hoàn tất hồ sơ thiếu mapping/khóa.** Đường nhận 126–128/143–145 giữ hồ sơ ở V4 không có phiên bản; retry cùng raw tại 109–112 trả TRUNG_RAW. Hàm sửa mapping hiện nhận pb_id và chỉ ObjectID/dự án. Chưa thấy đường sửa envelope/profile/khóa rồi tiếp tục đúng artifact đã nhận. Không khắc phục bằng đổi namespace giả hoặc tạo lại raw; kiểm UI/service mới khi writer kết thúc trước kết luận thiếu chức năng.

Source adapter đọc JSON chính xác và tách envelope/raw; `che_do=chua_chay_AI` không được coi là tham số hiệu lực trong parser. Mã tham số lặp chưa bị adapter loại bỏ; parser có báo mâu thuẫn, nhưng `_ghi_tham_so` INSERT từng dòng vào unique `(phien_ban_id,ten)` có thể làm import rollback trước khi hiện việc chờ. Đây là ca cần chạy với fixture mâu thuẫn hợp lệ, không kết luận từ lỗi setup.

## Private service probe đã chuẩn bị — chưa thực thi

`var/codex-dieu-phoi/crm-k2-independent-service-probe-01.py` là file riêng, không thay scaffold SQL cũ. Đã AST parse/compile dưới guard; chưa import/chạy script hoặc kết nối PostgreSQL. Cần root xác nhận coder terminal trước khi dùng cờ chạy.

Fixture tự tạo tổng 1.000 VND, các nghĩa vụ **100 + 400 + 500 VND**, hai profile KCN/nhà ở, hai pháp nhân và các actor DEMO. Dự kiến tạo login PostgreSQL riêng NOSUPERUSER/NOBYPASSRLS, SET ROLE app_web; giữ login role và DB, không DROP/cleanup. Credentials chỉ trong process. Positive control hai pháp nhân và GUC local hết sau transaction phải đạt trước khi tính negative cases.

Ca riêng: actor có PN nhưng không module; phụ lục **01/01/2099** đối chiếu as-of thật trước 2099; CFO chỉ V3 không V4; kiểm rồi đổi mapping cần kiểm lại; hồ sơ thiếu profile rồi bổ sung; race duyệt đổi đợt với link tiền vào lịch cũ; hai retry cùng khóa/payload. Race dùng barrier ở SQL boundary nhưng không sửa query/result; timeout/setup lỗi không tính đạt. Ca bổ sung mapping đang bind API nhận lại đã quan sát; nếu coder thêm API resolve riêng phải đọc và bind lại trước khi kết luận thiếu chức năng.

## Gate regression converter/schema — phân biệt negative diagnostic với positive acceptance

Đã đọc code `tests/test_pg_bo_chuyen_schema10.py`: fixture dòng 36 dùng `H = '0' * 64`; dòng 62–66 chủ ý assert `core_hash_nguon.sai = 6` và exit code **1**. Vì vậy test này xanh chỉ chứng minh báo lỗi của fixture hash giả trong phạm vi report đang so, **không chứng minh converter chuyển dữ liệu hợp lệ exit 0 trên schema 10**. Không được gộp nó thành positive compatibility gate.

`tests/test_pg_schema.py:225–249` vẫn có fixture H giả và positive assertion exit 0. Root báo lượt chạy hiện tại t16 fail, t15 skip vì thiếu role app_ke_toan; đây là kết quả root cung cấp, agent review này không chạy lại. Không đổi expected lỗi thành xanh rồi ghi regression đạt.

Bằng chứng còn cần:

1. Fixture hợp lệ có core hash đúng nội dung bằng contract hashing thật, chạy converter → **exit 0**, số đếm/nội dung/trạng thái đúng expected độc lập. Không bỏ/giảm kiểm hash để làm ca này xanh.
2. Nhận lại fixture hợp lệ → exit 0, số đếm và khóa không nhân đôi. Kiểm đúng nhóm bảng converter thực sự bao phủ, không suy thành toàn bộ K2 đã đối chiếu.
3. Fixture tamper tách riêng → exit 1 và mismatch đúng; không dùng expected của ca âm thay bằng chứng ca dương.
4. Quyền legacy app_ke_toan cần kiểm bằng role thường thật, không tính skip đạt. Test t15 hiện có finally DROP OWNED/DROP ROLE tại 214–215; không chạy cleanup đó trong probe giữ nguyên DB/role/file. Dùng đường kiểm tương đương có retention đã kiểm hoặc chỉnh chính thức theo phân công root, không sửa code/tests của Claude trong lượt review này.

## Kết quả runtime độc lập — 06:29–06:30 ngày 19/10/2026

Root xác nhận process CLI 3863 terminal exit_code 0/ClaudeExit 0 trước khi cho chạy. Đã freeze 6 source files cùng manifest tại `var/codex-dieu-phoi/crm-independent-frozen-20261019-062926/`; hash source/copy khớp. Hash `pg_migrations.py` và `crm.py` trước/sau probe không đổi, đúng hai hash ghi ở trên.

| Probe | Đạt | Vi phạm kỳ vọng | Setup/binding lỗi | Skip |
|---|---:|---:|---:|---:|
| SQL/schema/RLS | 7 | 19 | 0 | 0 |
| Service/transaction/concurrency | 1 | 7 | 0 | 0 |

Hai exception sản phẩm được ghi trong ca vi phạm, không che thành lỗi fixture: upgrade hợp lệ bị CHECK `23514`; concurrent retry bị UniqueViolation `23505`. Service probe đăng nhập PostgreSQL bằng login DEMO thực NOSUPERUSER, sau đó SET ROLE app_web; đã kiểm `rolsuper=false`, `rolbypassrls=false`. SQL probe SET LOCAL ROLE app_web trong từng transaction và rollback mỗi thao tác thử. Tất cả là dữ liệu DEMO tự tạo; credentials chỉ trong process. Guard giữ file hoạt động; giữ lại **4 DB kiểm thử và login role DEMO**, không DROP hoặc cleanup.

Evidence nguyên bản:

- `var/codex-dieu-phoi/crm-k2-independent-20261019-062951-9bb7233c/result.json`
- `var/codex-dieu-phoi/crm-service-independent-20261019_063004_9a2c6418/result.json`

### Positive controls và phần đã chứng minh đạt

- PostgreSQL mới migrate lên version 10 thành công.
- Upgrade v9 không có link HUY thành công, 9 checksum lịch sử giữ nguyên qua upgrade.
- app_web thấy hợp đồng thuộc PN được cấp và không thấy header hợp đồng PN khác.
- Kế toán kiểm và CFO có quyền duyệt được ca đủ điều kiện.
- Thiếu **cả hai** GUC không sửa được bản chờ do RLS lọc 0 dòng. Vì vậy không được nói mọi trường hợp thiếu context đều lọt; lỗi đã chứng minh là thiếu login hoặc ID/login mâu thuẫn.
- Service thực hiện nhận → kiểm → CFO duyệt trên **hai pháp nhân/hai profile KCN và nhà ở**, mỗi hợp đồng ra đúng expected độc lập **100, 400, 500 VND**.
- ID/login GUC local đều hết sau transaction của service. Đây là bằng chứng transaction local trong library, chưa chứng minh toàn bộ phiên HTTP/UI production.

### SQL — 19 ca vi phạm có thao tác thực

| Nhóm | Số ca | Reproduction và kết quả |
|---|---:|---|
| Upgrade | 1 | Tạo v9 với một link HUY hợp lệ chưa có ba cột provenance mới → migrate10 bị `23514`. |
| Grants/RLS | 4 | Với app_web/actor PN A, SELECT ID dòng đề xuất B, dòng chứng từ B và nhân viên B đều trả 1; BAN_HANG còn đọc được đề xuất kế toán PN A. Header B vẫn bị lọc đúng như control ở trên. |
| Chèn duyệt | 1 | INSERT phiên bản `DA_DUYET` bằng app_web/BAN_HANG được 1 dòng, bỏ qua bước kiểm/CFO. |
| Bất biến | 3 | UPDATE nội dung phiên bản đã duyệt, tham số của nó và số tiền lịch đều được 1 dòng. |
| Danh tính | 2 | ID BAN_HANG + login NULL hoặc login CFO hợp lệ đều duyệt được bản đã được KT kiểm. |
| FK/tenant/quan hệ | 8 | Đổi profile sang PN B; dự án sang B; con trỏ hiện hành sang bản B hoặc bản hợp đồng khác cùng A; replacement phiên bản sang B hoặc khác hợp đồng cùng A; lịch A trỏ phiên bản B; lịch A replacement lịch B: đều được 1 dòng. |

### Service — 7 ca vi phạm có reproduction

1. **Đọc thiếu module:** actor XEM có quyền PN nhưng `module=[]` gọi `danh_sach`; nhận **3 hồ sơ raw/envelope, 3 hợp đồng, 1 khoản tiền**. Không bị gate module chặn.
2. **Hiệu lực tương lai:** base đã duyệt; nhận phụ lục đổi đợt cuối 500→600, tổng 1.000→1.100, ngày hiệu lực **01/01/2099**; KT kiểm, CFO duyệt. As-of thực **19/10/2026**, con trỏ hiện hành đã thành phụ lục tương lai.
3. **V3/V4:** actor CFO chỉ có V3, không V4 duyệt bản GOC đủ điều kiện đã KT kiểm. Việc V4 thành DA_DUYET và hợp đồng được kích hoạt, không có từ chối quyền.
4. **Mapping sau kiểm:** KT kiểm xong; đổi sang ObjectID/dự án khác đều hợp lệ trong cùng PN. `kiem_boi/kiem_luc` vẫn giữ; CFO duyệt thành công không qua lần kiểm mới. Nhánh positive kiểm lại chỉ dành cho phiên bản đã sửa guard, chưa được dùng để cộng pass.
5. **Bổ sung hồ sơ thiếu profile:** nhận raw với `loai_hinh=NULL` → CHO_MAPPING; nhận lại đúng raw/namespace nhưng profile đã bổ sung → TRUNG_RAW. Giữ 1 artifact nhưng **0 hợp đồng**. Đây là bằng chứng API import/resubmit hiện hữu; cần kiểm/bind API resolve riêng nếu được bổ sung sau bản này.
6. **Race phụ lục–tiền:** base có đợt cuối 500 chưa thu; phụ lục muốn đổi còn 400/tổng900. Barrier cho CFO phân tích xong rồi dừng trước UPDATE duyệt; connection KT đọc lịch cũ là hiện hành rồi dừng trước INSERT link. Cho CFO duyệt/commit trước, sau đó cho link cũ 500 tiếp tục. **Cả hai trả thành công**; phụ lục DA_DUYET, nghĩa vụ hiện hành **400**, tiền đã nối theo chuỗi nghĩa vụ **500**. Fixture không đổi SQL/result, chỉ điều khiển thứ tự ở boundary connection.
7. **Concurrent retry:** hai connection cùng khóa và payload link100; cả hai SELECT chưa có khóa trước khi thả barrier. Một request trả ID thành công, request kia **UniqueViolation23505**; DB giữ 1 link100. Tính không nhân bản đạt riêng về số đếm, nhưng hành vi idempotency trả kết quả ổn định cho hai request chưa đạt.

Không sử dụng kết quả này để gọi toàn CRM/M3 đạt hoặc kết luận HTTP exploit/production login đã kiểm. Cần sửa product theo phân công Claude, giữ scope typed K2 PG và legacy SQLite, rồi rerun đúng các ca vi phạm cùng positive controls trên hash mới. Không sửa fixture expected để biến vi phạm thành đạt.
