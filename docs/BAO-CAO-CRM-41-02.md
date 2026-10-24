# BÁO CÁO CRM-41-02 — G1 mẫu DOCX / G7 bộ chuẩn dự án tối thiểu / S6

**Trạng thái: `NOT_RUN_CODE_ONLY`.** Claude chỉ viết/sửa mã bằng Read/Glob/Grep/Edit/Write. Không chạy Python/Node/test/SQL/migration/HTTP/server/
trình duyệt/Office/AI; không import/AST; không đọc var/.env/credentials/oracle riêng/app nguồn thật; không xóa/rename/move/reset/cleanup.
Không có kết quả selftest, independent, native hay GUI nào **của Claude** trong báo cáo này. Không tuyên bố nghiệm thu CRM/M4/GUI/wheel.
Static review và việc lượt viết kết thúc exit 0 **không** phải test/GUI/full CRM acceptance.

Căn cứ: handoff gốc `docs/GIAO-CODE-CRM-41-02-MAU-DOCX-G7-S6.md`, handoff sửa `docs/GIAO-SUA-CRM-41-02-TIEP-01.md` và
`docs/GIAO-SUA-CRM-41-02-TIEP-02.md`, hai input công khai `docs/CRM-41-02-DEMO-INPUTS.json`, `docs/CRM-41-02-MIGRATION-PREFIX-17.json`.

## 0. Lượt TIEP-03 — N06: quyền sở hữu nút gửi lại tệp (`crm_g.js`)

**Căn cứ:** `docs/GIAO-SUA-CRM-41-02-TIEP-03.md`. Root ghi nhận trên baseline `71e7d2` (kiểm của **Root**, không phải Claude self-test): 29/29 thuần,
AST/JS syntax, 9/9 DOCX độc lập, 4/4 ca bổ sung, native HTTP 13/13 trên PostgreSQL DEMO; harness DOM riêng của Root: 10/11 PASS, chỉ N06 lỗi.

**Lỗi N06 (Root tái hiện):** mở v1 → tải lên A đang chờ → sửa ánh xạ → bấm lại cùng nút, cùng File/loại/mã → ý định B → B trả 500 (chưa rõ), nút gửi
lại B hiện → A thành công muộn. Callback A gỡ mất nút gửi lại của B, vì (1) chuỗi khóa ý định không chứa `genForm` nên A và B trùng chuỗi dù khác khóa
thao tác, (2) dọn DOM so bằng chuỗi `dataset.tep`. Đây là lỗi sở hữu giao diện; không phải lỗi DB/idempotency/quyền.

**Sửa (chỉ vòng đời có sẵn, không framework, không timeout):**
- Mỗi ý định có `id` riêng (bộ đếm `soYDinh`); khóa Map của ý định thêm `genForm` → A và B là hai chủ khác nhau dù cùng tệp/loại/mã.
- Nút gửi lại tệp có đúng một chủ `chuNutTep`, so bằng **tham chiếu đối tượng**: `veNutTep(y)` đặt chủ; `goNutTep(y)` chỉ gỡ khi `chuNutTep === y`.
  `dataset.tep` chỉ còn là cờ "đang giữ nút tệp" (để nút gửi lại lệnh JSON không đè), không còn là căn cứ sở hữu.
- `boYDinh(y)` chỉ xóa Map-entry mà chính y giữ (`taiDang.get(y.intent) === y`), đặt `y.het`, gỡ nút nếu y là chủ. Callback phản hồi/lỗi/finally của A
  vì vậy không thể xóa, vô hiệu hay thay khóa, nút gửi lại hay trạng thái đang gửi (`dangGui` là của từng đối tượng) của B.
- Vô hiệu toàn bộ chỉ còn ở sự kiện context chung (`huyYDinhTai`: đổi tệp/loại/mã/tab/phiên bản, lỗi an ninh; đổi vai qua `xoa`).

**Giữ nguyên:** giữ chỗ đồng bộ (bấm đôi cùng ý định → 1 POST; bấm đôi nút gửi lại → 1 POST nhờ `dangGui`); gửi lại dùng đúng File gốc + header gốc
(loại/mã/tên/khóa) + khóa gốc; A cũ không gửi thêm, không toast/trạng thái, không chọn phiên bản, không làm mới, không xóa nháp. Fence actor/epoch/tệp/
loại/mã/tab/phiên bản/form chung sau mọi bước chờ. B do người dùng chủ động bấm vẫn dùng được: nút gửi lại B còn sau khi A về muộn; gửi lại B đúng
File/header/khóa của B, hoàn tất một lần, chọn đúng phiên bản. Tải về, GET, G7 A/B, barrier đổi vai chung không đổi. Không sửa parser, test, oracle,
`tests/m4_01c_async.cjs`, migration, service, server, index, app.js.

**Giới hạn:** `NOT_RUN_CODE_ONLY`. Chưa chạy lại harness DOM của Root sau sửa; chưa có self-test/GUI/full CRM–M4 PASS nào của Claude.

## 1. Lịch sử các lượt

| Lượt | Kết thúc | Ý nghĩa |
|---|---|---|
| handle 70436 / terminal `eca51c` | Hết giới hạn 1800 s, exit 1, chưa có result/report | Partial code; Root xác nhận dừng/scope/posthash. Không phải kết quả kiểm sản phẩm. |
| handle 41064 / terminal `b652bc` (TIEP-01) | exit 0, không timeout; 360 source / 428 runtime | Chỉ là kết thúc lượt **viết code**. Root kiểm hữu hạn sau đó còn phát hiện P02/U02/T01–T04 → TIEP-02. |
| TIEP-02 (owned 50595 / terminal `71e7d2`) | exit 0; stop/scope/posthash đạt; 360 source / 428 runtime | Sửa 5 file (§2–§3). Root kiểm sau đó: xem §0. |
| Lượt này (TIEP-03) | — | Chỉ sửa 2 file đã có: `crm_g.js` (N06) và báo cáo này. NEW 0. |

**Kết quả Root đã ghi (không phải Claude self-test):** trên bản freeze `b652bc`, Root chạy 27 ca thuần của `tests/test_crm_41_02.py`: 25 PASS, 1 FAIL
(`test_c4_setup_dung_mot_dong`), 1 ERROR (`test_guard_chu_the_k5_chi_them_nhanh_typed`, StopIteration), 0 skip; AST/JS syntax đạt. Lượt này sửa hai
ca đó (§3.4). HTTP/PG/GUI **chưa** có PASS nào.

## 2. Phạm vi lượt TIEP-02 (lượt TIEP-03: xem §0)

Chỉ 5 file đã có: `src/kho_tri_thuc/nguon/mau_docx.py`, `src/kho_tri_thuc/giao_dien/assets/crm_g.js`, `tests/test_crm_41_02.py`,
`tests/test_crm_41_02_http.py`, `docs/BAO-CAO-CRM-41-02.md`. Không tạo file. Không chạm `pg_migrations.py` (791902 byte đầu, migration 1–18, khối M9),
`crm_mau.py`, `quyen.py`, `server.py`, `crm_g.py`, `index.html`, `app.js`, seed/bootstrap, `tests/m4_01c_async.cjs` (SHA `f77bdfe6…a9d2`), vendor, fixtures.

Toàn bộ gói (15 target của handoff gốc) vẫn như lượt trước: 13 file existing đã sửa ở các lượt trước + 2 file mới; `app.js` nguyên byte C4.

## 3. Sửa theo TIEP-02

### 3.1 P02 — phân loại phần theo quan hệ/cấu trúc, không theo tên (`mau_docx.py`)
- Gom LOẠI quan hệ trỏ VÀO từng phần từ **mọi** `.rels` (đuôi URI; transitional/strict như nhau) và ContentType override từ `[Content_Types].xml`.
- Mỗi phần XML còn lại (và mọi phần có quan hệ loại văn bản/định dạng trỏ vào, bất kể đuôi) được phân tích XML. Bảng `LOAI_QUAN_HE` → phần tử gốc
  mong đợi + đuôi ContentType. `_kiem_sieu_du_lieu`: gốc thực ↔ quan hệ ↔ ContentType (↔ vai trò sectPr) mâu thuẫn → `SIEU_DU_LIEU_MAU_THUAN`
  (INCOMPLETE). Áp dụng cho văn bản chính, header/footer được sectPr tham chiếu và mọi phần khác.
- **Bỏ hẳn** skip theo basename (`styles.xml`, `settings.xml`, `/theme/`, `headerN.xml`…). Chỉ không quét văn bản cho header/footer KHÔNG được sectPr
  tham chiếu khi gốc là `w:hdr`/`w:ftr` và mọi căn cứ nhất quán (không hiển thị). Mọi phần khác: ghép toàn bộ `w:t`/`w:delText`/`w:instrText`/`w:instr`
  của cả phần; có `{`/`}` → `KENH_CHUA_QUET` (kèm gốc + loại quan hệ).
- Giữ nguyên: thân/bảng/bảng lồng/run, header/footer sectPr, P01 giải mã UTF-8/UTF-16 + chặn DTD, P03 văn bản đoạn/khoảng run, hash raw/member.
  Bộ đọc vẫn `crm.mau_docx/2` (Root quyết có cần nâng phiên bản không).

### 3.2 U02 — fence đồng nhất cho mọi đường async (`crm_g.js`)
- **Tải lên:** context ý định gồm cả `genForm` (thế hệ form chung) ngoài epoch/actor/`genTai`/tab. Sửa ánh xạ/lý do/ngày/G7 trong lúc chờ ⇒ hoàn tất cũ
  không chọn phiên bản/toast/làm mới/xóa nháp; ý định chưa rõ kết quả không được gửi lại. Bấm lại khi context cũ đã hết hiệu lực = ý định MỚI (do người
  dùng bấm). Cùng context còn hiệu lực: vẫn một File/header/khóa gốc, đang gửi → 0 POST, chưa rõ → gửi lại y nguyên. U01 giữ chỗ đồng bộ giữ nguyên.
- **Tải tệp gốc:** fence = epoch + actor + phiên bản + tab G1 + `genForm`; kiểm trước request, sau phản hồi, sau `blob`, sau `arrayBuffer`, sau `digest`
  và ngay trước tạo URL/click/trạng thái (6 điểm).
- **GET:** `napDs`/`napCt`/`napBc`/`docChuan`/so sánh dùng cùng invariant cho thành công, lỗi và hẹn giờ thử lại (`if (dung()) napDs()`). Lỗi tạm
  (mạng/5xx/400) không xóa dữ liệu/editor, chỉ báo trạng thái khi còn đúng context; lỗi an ninh (401/403/`CRM_PHIEN`/`DANH_TINH*`) xóa dữ liệu thuộc
  quyền cũ. G7 GET lỗi về sau khi đã chuyển tab không ghi trạng thái. Kết quả xem thử/so sánh không dựng lại DOM khi form đã đổi.
- Barrier đổi vai chung, phân biệt lệnh JSON/GET và quyền hiện hành ở backend giữ nguyên.

### 3.3 T01–T03 (`tests/test_crm_41_02_http.py`)
- **T01:** bỏ thăm dò `DELETE FROM kho.viec_can_duyet`; giữ hai UPDATE âm (retarget, mở lại) và thêm UPDATE đóng lại việc đã đóng; giữ INSERT/SELECT/
  EXECUTE âm. Không có lệnh DELETE/DROP/TRUNCATE nào trong file.
- **T02:** `addClassCleanup` đăng ký ngay khi tạo từng tài nguyên (chạy cả khi setUpClass lỗi): dừng server + join hữu hạn, đóng socket, đóng kết nối CRM
  thường `app._crm.conn` và chủ bảng `app._crm_g.conn_tin_cay`, khôi phục env, đóng admin. g10/g11 dùng `addCleanup`: nhả Event, join 60 s, đóng đúng
  kết nối do test tạo, báo worker còn sống là lỗi. Giữ DB/role/thư mục/artifact.
- **T03:** bỏ `sleep + is_alive` làm bằng chứng. `cho_bi_chan(pid, boi)` dùng kết nối observer trên chính DB DEMO mới: chờ (hạn 30 s, quá hạn = FAIL)
  đến khi `pg_blocking_pids(pid)` chứa đúng backend chặn, rồi đọc `pg_stat_activity` + `pg_locks`. g10: hai kết nối chủ bảng thật (PID khác nhau),
  A đang giữ khóa advisory, B bị chính A chặn, `wait_event = advisory`, câu đang chạy là `crm_g_tra`. g11: backend kết nối chủ bảng của máy chủ (chạy
  request HTTP) bị backend giao dịch thu hồi chặn trên khóa `transactionid`/`tuple`, câu `crm_g_tra`; worker lỗi được báo, không nuốt.

### 3.4 T04 (`tests/test_crm_41_02.py`)
- `test_c4_setup_dung_mot_dong`: tệp f77 có đúng **3** câu chọn nguồn trực tiếp — một câu có từ trước và hai câu bổ sung §11; kiểm từng câu theo dòng
  trước/sau và thứ tự, giữ kiểm SHA toàn tệp, kiểm hàm `chonMau` vẫn một lần. Không sửa tệp M4.
- Guard K5: `viec_chu_so_huu` chỉ có trong `M0013` full-M9 **lịch sử** (không thuộc chuỗi mặc định 1–17). Test mới `test_guard_k5_typed_dang_active` kiểm
  guard thực sự active là trigger `crm_g_viec_kiem` do M18 tạo. Test cũ lấy định nghĩa lịch sử từ `PM.M0013`, khẳng định M0013 không thuộc
  `PG_MIGRATIONS`, không migration 1–18 nào gắn trigger `viec_chu_so_huu`, và bản M18 của hàm chỉ thêm nhánh typed. Không bật lineage full-M9, không sửa
  migration.
- Thêm ca P02 TIEP-02: phần footnotes được tham chiếu mang tên `styles.xml`/`header1.xml`/`theme/theme1.xml`/`settings.xml`/`fontTable.xml` với token
  tách 4 run → INCOMPLETE (thân vẫn phát hiện); đối chứng DU (styles thật + footnotes sạch tên lạ, hash raw/member); mâu thuẫn quan hệ↔gốc,
  ContentType↔quan hệ, sectPr↔gốc → `SIEU_DU_LIEU_MAU_THUAN`; phần mồ côi tên header nhưng gốc footnotes → quét; header nhất quán không tham chiếu → DU.
- Thêm kiểm tĩnh U02 (fence `genForm` của ý định, 6 điểm kiểm của tải tệp gốc, fence lỗi/hẹn giờ của GET). Kiểm chuỗi nguồn **không** thay kiểm hành vi.

## 4. Sửa diễn giải từ báo cáo trước

Báo cáo TIEP-01 viết rằng `kho.viec_chu_so_huu` chặn K5 typed nên phải thay hàm. **Sai về căn cứ:** hàm và trigger đó chỉ thuộc M0013 full-M9 lịch sử;
chuỗi mặc định 1–17 không có trigger này. M18 tạo lại HÀM (kèm nhánh typed + `kho.crm_g_chu_the`) nhưng không gắn trigger, nên ở chuỗi mặc định hàm này
**không active** và không được dùng làm bằng chứng typed K5 bị chặn. Guard active được review là `crm_g_viec_kiem`. Migration không thuộc phạm vi
lượt này nên không gỡ phần thừa; Root quyết định có giữ hay không ở lượt sau.

## 5. Giới hạn kiểm thử (trung thực)

- Tất cả test lượt này: **NOT_RUN_CODE_ONLY**. HTTP test cần `KHO_PG_DSN_TEST`; thiếu → skip = NOT_RUN, không tính đạt.
- Observer trong HTTP test chỉ đếm số hàng/sequence nhật ký/số K5/tên tệp cấp đầu thư mục — **không** phải so sánh toàn bộ hàng/danh mục hay hash tệp đệ quy.
- g03 chỉ kiểm replay tải lên trước revision sau; **chưa** bao phủ replay đúng body/token gốc sau mọi revision, cũng chưa kiểm race REPEATABLE READ.
- Chưa có harness GUI/trình duyệt cho S6: double-click 1 POST, retry chưa rõ, upload chờ rồi sửa form, blob chờ rồi đổi tab/form, GET lỗi sau nháp
  mới/đổi tab, G7 A/B về ngược thứ tự — phải kiểm hành vi sau terminal.
- Rủi ro còn mở: thứ tự trigger theo tên cho mã lỗi g08; giả định `ET.fromstring(str)`; P02 bảo thủ (chú thích có ngoặc thường cũng INCOMPLETE); đọc K5 kế
  thừa của KT/CFO; test cũ khẳng định schema 14/15/16 sẽ lệch khi lên 18 (file bảo vệ, không sửa); checksum M18 chờ Root bind.
- Không approval seed, không reset grant cũ, không master song song, không IAM engine; chỉ actor `MO_PHONG_CRM_G_*`.

## 6. Còn chờ Root

Freeze/terminal thực tế → kiểm phạm vi (TIEP-03: 2 target `crm_g.js` + báo cáo, NEW 0, protected 358, source 360) → chạy lại harness DOM N06 + các
oracle upload/retry dương → chạy `test_crm_41_02.py`, `test_crm_41_02_http.py`,
regression CRM-neutral/M1/K5/M4 phù hợp, harness GUI S6 → bind checksum M18. Mọi PASS phải ghi theo kết quả thực tế của Root.
