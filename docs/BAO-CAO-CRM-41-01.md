# BÁO CÁO CRM-41-01 — Một engine #6 dùng chung cho M4 + CRM · NOT_RUN_CODE_ONLY

**21/10/2026 · Trạng thái: NOT_RUN_CODE_ONLY.** Coder chỉ dùng Read/Glob/Grep/Edit/Write. Không chạy lệnh, import, AST, test, SQL, HTTP, mạng, browser hay Office, và không truy cập dự án nguồn thật. Không có self-test, runtime, GUI hay Root acceptance nào. Không mục nào là PASS. Toàn module M4/CRM chưa hoàn tất.

Căn cứ:
- `docs/GIAO-CODE-CRM-41-01-BINDING.md` và handoff `docs/GIAO-CODE-CRM-41-01-ENGINE-DUNG-CHUNG.md` (`70197bf9…d28133`).
- Quyết định engine dùng chung (`54be96e9…dfadb`).
- Bản kỹ thuật nguồn trong `docs/CRM-41-01-SOURCE-PATCH`.

## 1. Kiến trúc đã viết

**Một engine.** Lõi trích duy nhất là #6 ở dự án nguồn. Patch chỉ soạn trên bốn bản sao byte-exact trong `docs/CRM-41-01-SOURCE-PATCH`; **Root áp vào nguồn thật sau terminal**. Central không import/copy lõi trích và không `sys.path` tới docs/review_goc cho việc trích.

**Contract `trich-tham-so-common/v1`.**
- Mở rộng đúng route thật `POST /api/trich_xuat/{luot}/chay`. Nếu body có `contract` thì rẽ nhánh ngay đầu `chay_luot`, trước `doc_cau_hinh`/Claude/khóa/AI.
- Body gồm `contract`, `mode='RULE_ONLY'`, `loai_hop_dong='XD'`, `catalog_id='XD'`, `catalog_sha256=05846a2a…bcd`, `source_sha256`, `request_id`, `tham_so` (danh sách mã hoặc literal `'ALL'`).
- Legacy không có `contract` giữ API cũ. Contract lạ thì lỗi, không fallback.

**Snapshot nghiêm ngặt từng lượt.**
- Giữ chỗ (lượt, ý định) dưới khóa ngắn chung với upload; upload đóng ngay sau đó.
- Đọc raw DOCX và catalog **đúng một lần**, kiểm SHA trên chính bytes đó, rồi ghi bằng CreateNew vào `<lượt>/_common/`.
- `load_params` chạy trên **bản chụp** catalog (không để helper tự tạo catalog).
- Deep-copy tham số đã chọn; ghi `request.json` và `_tuy_chon.json` trước compute.
- Kết quả raw mang `common` (request/body/catalog/source hash, mã yêu cầu/đã dùng, snapshot tham số, rules, implementation SHA của các tệp engine) ngay ở lần ghi JSON đầu.

**Offline thật.** `RULE_ONLY` cho `ai=None`, `cloud=None`, `ra_lai=False`, không thăm dò AI, không cache dùng lại/ghi cache, `ghi_danh_muc_hd=False`, `QLV.tao(dung_ai=False)`. TC-* lấy từ quy tắc nguồn `master_hd.trich_xuat(..., llm=None)` ngay trong engine, có tự kiểm `check` trên văn bản HĐ. Mã khác giữ trạng thái chưa chạy AI cùng vị trí dò được, không bịa giá trị.

**Một client + một projection** (`src/kho_tri_thuc/nguon/trich_chung_6.py`).
- `Trich6Client` chỉ create/upload/run/read/stop.
- URL host cấp tường minh (`KHO_TRICH6_URL`/constructor), chỉ chấp nhận `http://127.0.0.1|localhost:<port>`. Thiếu URL → NOT_READY. Không redirect, không cổng mặc định.
- Ý định bền vững chỉ-ghi-thêm (`trich6-y-dinh/<request_id>/00…30`).
- Thử lại cùng ý định thì đối soát lượt/upload/kết quả; khác yêu cầu → `TRICH6_XUNG_DOT`. Đứt kết nối sau lệnh có hiệu lực hoặc quá hạn chờ → `ChuaRo` (UNKNOWN).
- Kiểm kết quả mang đúng bản chụp của chính yêu cầu.
- `chieu_tham_so` là projection duy nhất `bang[] → tham_so[]`:
  - Trạng thái: CO_GIA_TRI / KHONG_AP_DUNG / KHONG_QUY_DINH (cần trích dẫn) / CHUA_CO / NOT_REQUESTED.
  - Giữ `nguon_sha256` = hash raw, tách khỏi hash view; có version adapter.

**Hai consumer thật.**
- **M4:**
  - `NR.trich_hop_dong` là wrapper mỏng: kiểm an toàn DOCX/Track Changes trước, rồi gọi `client.trich(..., 'XD', 'ALL', request_id)`.
  - Kết quả phải đủ 37 mã như SQL yêu cầu, catalog phải khớp pin; giữ raw kết quả; `che_do=QUY_TAC_KHONG_AI` theo DDL hiện có; không nhận AI, không lõi chép.
  - `XayDungK2.trich`: kiểm SOAN + revision trước upload; ý định ổn định theo (actor, khóa, HĐ, revision, raw); UNKNOWN → `M4_TRICH6_CHUA_RO`, không ghi.
  - Sau lần gọi dài: kiểm lại quyền/revision/tệp, rồi SQL CAS `m4.ghi_trich_xuat`.
  - Route `hop-dong/trich` chạy qua seam kết nối riêng `_review_lenh`, ngoài `mutation_lock`.
- **CRM:**
  - `CrmK2.trich_tu_docx` theo thứ tự:
    1. Kiểm DOCX.
    2. Kiểm pháp nhân + `quyen.kiem(NOP_HOP_DONG)` trước mọi tác động hay gọi engine.
    3. Kiểm hình thức yêu cầu.
    4. Giữ Word gốc.
    5. Gọi engine.
    6. Giữ raw #6.
    7. Projection.
    8. `nhan_ket_qua_6` (kiểm quyền lại trước ghi) với `word_hash` và envelope `common` (version `trich6-common-envelope-v1`, đã kiểm).
  - Legacy `/api/crm/nhan` JSON và `/api/crm/mau` giữ nguyên. Route mới `POST /api/crm/trich6`: khóa chỉ bao bước chụp danh tính; kết nối login ứng dụng riêng, đóng ở mọi nhánh.
- **UI:**
  - `app.js`: vùng "Trích hồ sơ Word (engine dùng chung)" trên thẻ CRM hiện có, dựng bằng DOM, không sửa index. Có tệp .docx, pháp nhân, **loại trích** (chỉ XD, tách khỏi loại hình tài chính), mã `ALL`/danh sách.
  - Ý định gốc giữ theo nội dung form; phản hồi muộn sau đổi vai/form không chạm form mới.
  - `m4.js`: chỉ cập nhật mô tả hành động Trích (engine chung, chưa sẵn sàng, UNKNOWN gửi lại y nguyên).

## 2. Inventory callsite (sau chuyển)

| Callsite | Loại | Sau CRM-41-01 |
|---|---|---|
| `k2/xay_dung.py: XayDungK2.trich → NR.trich_hop_dong` | runtime M4 | qua `Trich6Client` (engine #6 chung) |
| `m4/nguon_review.py: trich_hop_dong` | runtime M4 | wrapper common; **không còn** `TrichXuat(...)`/`master_hd.trich_xuat` |
| `m4/nguon_review.py: danh_muc_tham_so()` (`load_params` trên catalog ghim) | runtime M4 (hiển thị/kiểm danh mục 37 mã, không trích) | giữ |
| `m4/nguon_review.py: van_ban_hop_dong`/`kiem_trich_dan` (read_contract/check pinned) | runtime M4 (đối chiếu trích dẫn khi sửa tay, không trích) | giữ, theo binding |
| `k2/crm.py: nhan_ket_qua_6` | runtime CRM (JSON cũ) | giữ; thêm `common` tùy chọn |
| `k2/crm.py: trich_tu_docx` | runtime CRM mới | qua `Trich6Client` |
| `m4/review_goc/**` (TrichXuat/master_hd chép) | vendor/reference | giữ nguyên byte; không còn đường TRÍCH active gọi |
| `docs/CRM-41-01-SOURCE-PATCH/**` | bản kỹ thuật patch | không runtime import |

## 3. File đã sửa / tạo (đúng 18 đích)

**Nguồn #6 (bản patch; Root áp):**
- `may_chu/dich_vu.py`: `_chay_common`, `_kiem_common`, `_implementation`, `_ghi_moi`, `COMMON`/`_KHOA_LUOT`. Có rẽ nhánh trong `chay_luot`; khóa giữ chỗ trong `tai_len_hop_dong`/`xoa_tep_luot`; `chi_tiet_luot.common`.
- `trich_xuat/danh_muc.py`: `CATALOG_COMMON`, `LoiChonMa`, `kiem_tham_so_yeu_cau`, `load_params_ban_chup`, `chon_tham_so`.
- `trich_xuat/lo.py`: `LuotChay(che_do, meta)` — RULE_ONLY không AI/cache.
- `trich_xuat/quy_trinh.py`: `TrichXuat(che_do, meta)` — TC theo quy tắc (llm=None), `che_do='RULE_ONLY'`, `kq['common']`.
- `tests/test_common_api.py` (NEW).

**Central:**
- NEW: `nguon/trich_chung_6.py`.
- Sửa: `nguon/trich_hop_dong_6.py` (envelope `common`, cảnh báo RULE_ONLY), `k2/xay_dung.py`, `k2/crm.py`, `giao_dien/server.py`, `giao_dien/m4.py`, `giao_dien/assets/app.js`, `m4/giao_dien/m4.js`, `m4/nguon_review.py`.

**Tests:**
- NEW: `tests/test_trich_chung_6.py`.
- Sửa: `tests/test_crm_phan_tich.py` (thêm ca legacy/common trong AdapterTests), `tests/test_m4_01b_tinh.py` (chỉ wiring ca Track Changes: client sentinel).

**Báo cáo:** báo cáo này.

**Không sửa:** `master_hd.py`, `server.py`/`cau_hinh.py`/`viec.py` nguồn, catalog XLSX, test nguồn cũ, migrations 1–20, pyproject/index, M9, vendor/review_goc, Review L1/L2.

## 4. Tests đã viết (NOT_RUN)

**`docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py`** — **API nguồn thật** sau khi áp patch: `tao_may_chu(0)`, dữ liệu tạm, sentinel chặn AI/cấu hình.
- C01: RULE_ONLY + ALL ra 37 mã, có bản chụp/implementation, positive quy tắc TC, không bịa giá trị.
- C02: tập con.
- C03: lỗi phân biệt trước compute (thiếu/[]/sai kiểu/trùng/lạ/contract/mode/loại/catalog id+SHA/request_id/trường lạ/source SHA).
- C04: cùng ý định thì lặp lại không chạy lại; khác ý định → xung đột; upload đóng.
- C05: thay tệp và đổi tham số xen kẽ không đổi bản chụp.
- C06: đồng thời, đúng một bên thắng.
- C07: nhánh cũ không đổi.

**`tests/test_trich_chung_6.py`:**
- `ClientIoMockTests`/`ProjectionTests` — **IO-mock**: chỉ chứng minh giao thức client, không chứng minh độ đúng trích. Phủ URL loopback/NOT_READY, header, lỗi trước gọi, ý định UNKNOWN → đối soát không tạo/tải lại, xung đột, kết quả khác yêu cầu, projection CHUA_CO ≠ NOT_REQUESTED, hash view ≠ hash raw, đọc được qua `doc_ket_qua`.
- `WiringTests`: M4 không còn lõi chép; SOAN/revision trước, kiểm lại sau; route ngoài lock; wrapper đủ 37 qua client; AI bị chặn; Track Changes chặn trước gửi; CRM quyền trước gọi engine, route ngoài lock, đóng kết nối; envelope tương thích cũ.
- `ApiNguonThatTests`: **API nguồn thật** khi Root cấp `KHO_TRICH6_URL`, nếu không thì skip = NOT_RUN. M4 ALL 37 và CRM tập con cùng một implementation, mã lạ → lỗi rõ.

**`test_crm_phan_tich.AdapterTests.test_legacy_va_common_cung_adapter`:** unit, không IO.

## 5. Giới hạn trung thực

- **Chưa chạy gì.** Patch nguồn chưa áp. Đường gọi thật cần Root dựng engine loopback (`tao_may_chu(0)`, `HD_*` tạm) và đặt `KHO_TRICH6_URL` cho máy chủ central.
- **Kết quả RULE_ONLY chỉ có TC-*** từ quy tắc nguồn. Mã TT-* là CHUA_CO (không AI); phòng dự án/CRM nhập/soát tay như trước. Không mở chính sách tài chính TT.
- ~~Lượt nguồn cũ chỉ giữ chỗ trong bộ nhớ~~ — đã sửa ở FIX01 F3 (§6).
- ~~Tạo lượt đứt kết nối thì thử lại tạo lượt mới~~ — đã sửa ở FIX01 F2 (§6).
- **Không có dừng tự động khi hết hạn chờ:** client báo UNKNOWN, giữ ý định để đọc tiếp. API `dung` có nhưng chỉ dùng theo ý định.
- **CRM:**
  - Dùng hàm hình thức `T6.yeu_cau_common` để báo lỗi sớm trước khi lưu Word.
  - Map tham số XD vào profile tài chính KCN/nhà ở (`tham_so_typed`) có thể không ra dòng nào — đúng thiết kế: loại trích ≠ loại hình; KCN/nhà ở chưa có catalog trích.
- **UI:** `request()` của app không mang mã HTTP, nên vùng CRM giữ ý định tới khi thành công (bấm lại cùng tệp/lựa chọn sẽ đối soát), không phân biệt lỗi rõ với UNKNOWN trên giao diện. GUI chưa kiểm.
- **E3** (bảng typed theo dòng/ô), catalog KCN/nhà ở/MUA, M2-00, E1-MUA: ngoài gói, theo hàng đợi.
- **Timebox 1200 s:** phần code/test/report trên đã viết đầy đủ theo binding. Còn lại là kiểm tĩnh do Root làm và chạy thật — **không** phải placeholder bị bỏ dở.

## 6. FIX01 — đường dẫn Windows, ý định bền/replay và CRM async (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-CRM-41-01-01-DURABLE-INTENT-VA-UI.md`.

Phạm vi:
- Đúng 9 đích đã có, NEW = 0. Patch nguồn vẫn chỉ ở bản staged, Root áp sau.
- `danh_muc.py`/`lo.py`/`quy_trinh.py` nguồn, migrations 1–20, vendor, M9 và các oracle tài chính/quyền không đổi.
- `k2/xay_dung.py`, `giao_dien/server.py` central không đổi: chúng đã xử lý `ChuaRo` / route ngoài lock từ lượt trước.
- Không chạy gì.

| # | Lỗi | Sửa | Tệp |
|---|---|---|---|
| F1 | ID logic `m4:<hex>` làm tên thư mục → Windows không tạo được | Thư mục ý định = **SHA-256 hex của ID logic**, resolve và kiểm vẫn nằm trong gốc. ID logic giữ nguyên trong body/biên nhận (`00_yeu_cau.json` chứa `request_id`). Registry nguồn (`_common_y_dinh/<sha>.json`) và ý định CRM (`crm-trich-y-dinh/<sha>.json`) cũng dùng tên băm | `trich_chung_6.py`, `dich_vu.py`, `crm.py` |
| F2 | Create không gắn ý định: mất ACK thì tạo lượt mới; hai caller cùng ý định tạo hai lượt; lỗi GET/poll/raw sau khi start được nhận bị đổi thành LOI cuối | Xem chi tiết F2 bên dưới bảng | `server.py`, `dich_vu.py`, `trich_chung_6.py`, `nguon_review.py` |
| F3 | `COMMON` chỉ trong bộ nhớ; restart rồi gửi lại đúng body → `mkdir` 500; start legacy kiểm ngoài khóa nên có thể ghi đè common | Xem chi tiết F3 bên dưới bảng | `dich_vu.py` |
| F4 | `request_id` từ trình duyệt chỉ gắn raw/loại/mã; đổi envelope cùng ID có thể rơi vào TRUNG_RAW cũ | Xem chi tiết F4 bên dưới bảng | `crm.py` |
| F5 | Ba race UI CRM | Xem chi tiết F5 bên dưới bảng | `app.js` |
| F6 | `HD_OUT_DIR` ngoài `HD_DU_LIEU` → `duong_dan_tai` rỗng, ca dương không tải được raw | Đặt `HD_OUT_DIR`/`HD_DANH_MUC_HD` dưới `TMP/du_lieu`; giữ toàn bộ tmp/DB/tệp | `tests/test_common_api.py` |

**Chi tiết F2.**
- Route create sẵn có `POST /api/trich_xuat` nhận **tùy chọn** `{contract, request_id, yeu_cau}` (`luot_moi_common`); body `{}` cũ giữ nguyên.
- Nguồn kiểm `yeu_cau` bằng đúng `_kiem_common`, rồi trong `_KHOA_LUOT` ghi bền **CreateNew** registry và `<lượt>/_common_y_dinh.json` **trước ACK**. Cùng ý định → đúng lượt cũ (`lap_lai`); khác body → 409.
- Create legacy cũng vào khóa, nên kiểm-tồn-tại → `mkdir` theo nhãn thời gian không va nhau.
- Upload vào lượt của ý định chỉ nhận đúng bytes `source_sha256`; gửi lại cùng bytes là idempotent, không thêm tệp.
- Client luôn create theo ý định và giữ bytes gốc + yêu cầu gốc **trước** mọi tác động. Bỏ qua upload nếu lượt đã có đầu vào/đã giữ chỗ.
- Mọi lỗi chưa rõ **sau khi gửi create** đều thành `ChuaRo`: đứt kết nối, đọc dở, 5xx không mã, `COMMON_MO_COI`, kể cả GET/poll/raw sau khi start đã được nhận.
- `NR.trich_hop_dong` phân loại lại phòng thủ, nên M4 không ghi FINAL LOI/revision/biên nhận khi chưa rõ. Biên nhận start ghi nội dung ổn định để nhiều caller cùng ý định không va nhau.

**Chi tiết F3.**
- Giữ chỗ **bền** `<lượt>/_common_giu.json` (CreateNew) trong khóa; lỗi chụp bền `_common_loi.json`.
- `_nap_lai_common` dựng lại trạng thái từ dữ kiện bền: done / loi / da_dung / loi_capture / **orphaned** (chụp hoặc chạy bị cắt, không còn tiến trình sở hữu). Thử lại đúng body: `done` → replay `lap_lai`, không đụng raw/lịch sử; `orphaned` → 409 `COMMON_MO_COI` (UNKNOWN), không tự chạy lại/đặt lại/ghi đè.
- Worker xong thì cập nhật trạng thái.
- Start legacy giữ chỗ trong cùng khóa (`GIU_LEGACY`), đọc cấu hình/dựng `LuotChay` ngoài khóa, rồi chuyển sang `LUOT` trong khóa. Upload, xóa tệp, start common và start legacy dùng chung `_dang_giu`.
- Common không thừa hưởng cấu hình/AI.

**Chi tiết F4.**
- Sau khi kiểm quyền và **trước** mọi lưu tệp/gọi engine, máy chủ ghi bền một lần ý định gốc đầy đủ:
  - actor từ danh tính phiên (không từ trình duyệt);
  - envelope đã chọn (PN, loại hình tài chính, dự án, loại bản, HĐ gốc, mã HĐ chung, ObjectID);
  - loại trích (danh mục), mã, SHA Word.
- Cùng (actor, ID) mà nội dung khác → `CRM_TRICH_XUNG_DOT`: không gọi engine, không ghi nghiệp vụ.
- ID gửi engine dẫn xuất từ toàn bộ ý định. Actor khác dùng cùng ID logic → ý định riêng.
- Trường ngoài phạm vi → `CRM_ENVELOPE`. Quyền hiện hành kiểm lại trong `nhan_ket_qua_6` trước khi ghi.

**Chi tiết F5.**
- (1) Định danh tệp theo **SHA-256 bytes thật** (không theo tên/cỡ/lastModified); ý định giữ đúng bytes gốc để gửi lại.
- (2) Rào vai/form/ngữ cảnh **sau** `arrayBuffer()` và sau khi băm, **trước** POST; giá trị form chụp tại lúc bấm.
- (3) Form trích là **DOM cố định theo vai**: làm mới nền (`crmLoad` → `crmRender`) gắn lại đúng vùng này, chỉ cập nhật danh sách PN khi thực sự đổi, nên nháp B không bị xóa. Đổi vai thì tăng thế hệ và dựng lại form cho vai mới.

### Tests FIX01 (viết thêm, **NOT_RUN**)

**`docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py`** — API nguồn thật in-process sau khi áp patch:
- C08: create mất ACK (máy chủ đã tạo) → đúng lượt; ID `m4:…` registry tên băm; khác body → 409; body `{}` cũ; đồng thời cùng/khác ý định.
- C09: upload theo ý định (bytes khác → 409, gửi lại idempotent), start mất ACK → `lap_lai`, chạy trọn vòng.
- C10: legacy đang giữ chỗ (trong lúc đọc cấu hình) → common bị chặn, và ngược lại.
- C11: mô phỏng khởi động lại → replay `done` không đổi tệp; lượt mồ côi → `COMMON_MO_COI`, `orphaned`, upload vẫn đóng.
- F6 sửa gốc dữ liệu.

**`tests/test_trich_chung_6.py`:**
- F1: gốc thật, các ID `m4:…`/`.`/`..`.
- F2 (IO-mock): mất ACK create/upload/start sau xử lý; đứt GET/raw; ba caller một lượt; NR chưa rõ → `ChuaRo`, 4xx có mã → LOI.
- F4: **UNIT** trên đối tượng thay thế, `quyen.kiem` stub ghi rõ — đổi PN/dự án/loại hình/loại bản/bytes → xung đột, 0 engine/0 ghi; actor khác tách; trường lạ bị chặn; tên băm.
- F5: **TĨNH** trên `app.js` — chưa phải kiểm trình duyệt.

### Giới hạn sau FIX01
- Chưa có kiểm thật hai consumer qua HTTP/PG (`XayDungK2`/`CrmK2` + engine thật); ca F4 là unit có stub quyền; F5 chưa có kiểm DOM/trình duyệt.
- Lượt `orphaned` cần ý định mới để trích lại (theo yêu cầu không tự chạy lại); chưa có công cụ đánh dấu/dọn — giữ nguyên làm bằng chứng.
- Lỗi rõ và UNKNOWN trên UI CRM vẫn hiển thị chung (hàm `request()` hiện có không trả mã HTTP); ý định luôn được giữ tới khi có kết quả.

## 7. FIX02 — replay, toàn vẹn dữ kiện bền và actor của ý định (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-CRM-41-01-02-REPLAY-VA-TOAN-VEN.md`.

Phạm vi:
- Đúng 6 đích đã có, NEW = 0. Không xóa tệp nào. Patch nguồn chỉ ở bản staged.
- Giữ nguyên byte: `app.js`, `server.py` (nguồn và central), `nguon_review.py`, `danh_muc`/`lo`/`quy_trinh`, catalog, vendor, migrations 1–20, M9.
- Oracle quyền/tài chính không nới.

| # | Lỗi | Sửa | Tệp |
|---|---|---|---|
| R1 | Lịch: B GET (chưa có đầu vào) bị giữ → A upload/start → B upload nhận 409 không mã → lỗi cuối | Xem chi tiết R1 bên dưới bảng | `dich_vu.py`, `trich_chung_6.py` |
| R2 | Create ghi `mkdir` và liên kết per-run trước registry; dừng giữa chừng thì lần thử lại cấp lượt thứ hai | Xem chi tiết R2 bên dưới bảng | `dich_vu.py` |
| R3 | Rehydrate tin `_luot.tt=xong` và metadata đã parse; gộp tệp hỏng với tệp thiếu | Xem chi tiết R3 bên dưới bảng | `dich_vu.py`, `trich_chung_6.py` |
| R4 | Bản ghi ý định CRM khóa theo actor + ID, nên actor B cùng ID tạo ý định mới | Xem chi tiết R4 bên dưới bảng | `crm.py` |
| R5 | Test F4 đọc mọi entry (vấp thư mục staging do guard giữ); c08 chưa đủ 4 phản hồi; c11 so (basename, size) | Xem chi tiết R5 bên dưới bảng | `test_trich_chung_6.py`, `test_common_api.py` |

**Chi tiết R1.**
- Nguồn: với lượt của ý định common, cùng bytes được **replay trước** mọi kiểm giữ chỗ (kể cả khi lượt đã giữ chỗ/đang chạy/đã xong), trả đúng tên tệp cũ, không ghi thêm/ghi đè. Bytes khác → 409 `COMMON_SOURCE_SHA_KHAC`. Lượt đã giữ chỗ nhưng không thấy đầu vào → 409 `COMMON_CHUA_RO`. Upload legacy sau start vẫn đóng như cũ.
- Client: gặp 409 **không mã** khi upload thì đối soát lại lượt của chính ý định (GET); đã có đầu vào/giữ chỗ thì tiếp tục start idempotent, chưa đủ dữ kiện thì `ChuaRo`. 409 có mã vẫn là lỗi rõ.
- M4 giữ UNKNOWN, không ghi FINAL LOI.

**Chi tiết R2.**
- **Một điểm giữ chỗ bền duy nhất**: registry `_common_y_dinh/<sha(request_id)>.json` (CreateNew) gắn request_id + body + **đúng tên lượt**, ghi **trước** `mkdir`/liên kết.
- Thử lại: đọc nghiêm ngặt, khôi phục idempotent cùng lượt — `mkdir(exist_ok)` và liên kết đúng **bytes registry**; liên kết khác thì không ghi đè → UNKNOWN.
- Registry hỏng hoặc ghi dở → 409 `COMMON_CHUA_RO` có lý do, không cấp lượt khác.
- Cấp tên lượt (legacy và common) bỏ qua tên đã được registry giữ, kể cả khi thư mục chưa kịp tạo.

**Chi tiết R3.**
- `_doc_json_chat` tách *thiếu* (None) khỏi *hỏng* (`_Hong`).
- `_kiem_toan_ven` đối chiếu giữ chỗ ↔ liên kết ↔ `request.json` (đủ trường) ↔ bản chụp HĐ/danh mục đúng **SHA trên bytes thật** ↔ tập mã yêu cầu/đã dùng ↔ implementation.
- Worker xong thì **niêm phong** tệp kết quả gốc (`_common/ket_qua_seal.json`: ref tương đối + SHA + độ dài + request/body, CreateNew). Chỉ `done` khi niêm phong khớp bytes. `_luot.json` xong mà không có niêm phong, hash lệch, JSON hỏng/thiếu trường, snapshot thiếu → `unknown`: start trả 409 `COMMON_CHUA_RO`, không chạy lại/ghi đè.
- Replay `done` trả niêm phong cũ.
- Client: `unknown`/`orphaned` → `ChuaRo`; lượt xong mà chưa niêm phong thì chờ; bytes tải về khác niêm phong → `ChuaRo`.

**Chi tiết R4.**
- Khóa theo **ID logic** (`crm-y-dinh|<request_id>`, tên băm); actor có thẩm quyền nằm **trong** nội dung bất biến cùng PN/loại hình/dự án/loại bản/tệp/loại trích/mã.
- Cùng ID mà khác actor hoặc khác nội dung → `CRM_TRICH_XUNG_DOT` với thông báo không lộ chủ/nội dung cũ.
- Đối chiếu **trước khi ghi**, nên lần thử xung đột không để lại tệp nào (kể cả staging của `write_immutable`).
- Quyền hiện hành vẫn kiểm trước tra cứu.

**Chi tiết R5.**
- F4 chỉ đọc **tệp** `.json` thường; thư mục `.ktt-staging` kiểm riêng là thư mục, không bỏ qua tệp lạ. Đúng 2 bản ghi (A `crm:1`, B `crm:2`) với nội dung/owner/path/hash đầy đủ.
- c08 thu đủ **4** phản hồi, không thread sống, không ngoại lệ chìm.
- c11 so **đường dẫn tương đối + SHA + độ dài**.

### Tests FIX02 (viết thêm, **NOT_RUN**) — phân loại

**API nguồn thật in-process, sau khi Root áp patch** (`test_common_api.py`):
- c12: upload replay khi đang chạy/đã xong; bytes khác 409; legacy vẫn đóng.
- c13: tiêm lỗi ở khe ghi liên kết → thử lại cùng lượt, một lượt mới; registry hỏng cùng kích thước (sao lưu CreateNew trước) → UNKNOWN, ảnh thư mục không đổi.
- c14: replay `done` sau mất bộ nhớ đúng niêm phong; hỏng cùng kích thước ở kết quả / bản chụp HĐ / `request.json` → `COMMON_CHUA_RO` + `unknown`, không đổi tệp.
- c08/c11 nâng oracle như trên.

**IO-mock** (`test_trich_chung_6.py`, không phải HTTP nguồn thật):
- R1: lịch nhân quả B GET cũ → A upload/start → B upload 409 không mã. Một lượt/một start; B cùng kết quả hoặc UNKNOWN rồi thử lại hoàn tất; thu đủ kết quả.
- R3: bytes tải về lệch niêm phong → `ChuaRo`.

**UNIT** (đối tượng thay thế, `quyen.kiem` stub — không phải kiểm quyền PG thật):
- F4/R4: A nhận; B cùng ID → xung đột, 0 engine / 0 ghi / 0 tệp (đường dẫn + SHA); B ID mới là ca dương chủ B.

**Chưa có:** kiểm thật hai consumer `XayDungK2`/`CrmK2` qua HTTP/PG + engine nguồn thật; GUI.

### Giới hạn sau FIX02
- Hỏng ghi dở ngay trong lần ghi registry/liên kết đầu tiên được phát hiện và báo UNKNOWN, nhưng không tự khôi phục. Cần người xử lý bằng ý định mới; mọi bằng chứng được giữ.
- Niêm phong kết quả nằm ở nguồn. Lượt common chạy bằng patch **trước** FIX02 (không có niêm phong) sẽ ở trạng thái `unknown` khi rehydrate — fail closed theo yêu cầu.
- Timebox: các mục R1–R5 đã viết đầy đủ. Toàn bộ test **chưa chạy**; không có kết quả PASS nào.

## 8. FIX03 — niêm phong, recovery toàn vẹn, UNKNOWN trước conflict (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-CRM-41-01-03-SEAL-VA-RECOVERY.md`. Sửa đúng **5 file hiện có**, **NEW = 0**, không xóa file nào:
`docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py`, `docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py`, `src/kho_tri_thuc/nguon/trich_chung_6.py`, `tests/test_trich_chung_6.py` và báo cáo này.

Các phần giữ nguyên byte: CRM service/UI (`k2/crm.py`, `app.js`, `m4.js`), `nguon_review.py`, staged `server.py`/`viec.py`, `danh_muc`/`lo`/`quy_trinh`, catalog, vendor, M9 và migration 1–20. Không thêm core, framework, DB hay queue. Vẫn chỉ có một engine #6, một client và một projection.

**Trạng thái source:** patch nguồn vẫn **chưa áp dụng**, Root áp sau khi kiểm. Kết quả central 18/18 PASS mà Root đã chạy trước FIX03 **không** phải là source HTTP PASS và không phủ phần sửa này.

### R1 — Chỉ công bố qua niêm phong hợp lệ (nguồn)
- **Gate chung `_cong_bo`.** Gate nhận diện lượt common (giữ chỗ / liên kết / bộ nhớ) **trước** khi đọc `_luot.json` hay `_tuy_chon.json`. Với lượt `done`, mỗi lần công bố gate đều kiểm lại các điểm sau:
  - tệp seal trên đĩa phải bằng seal đã ghim lúc niêm phong hoặc nạp lại;
  - chuỗi `_kiem_seal` phải khớp trên bytes hiện tại;
  - DTO `_luot.json` (khi lượt không còn trong bộ nhớ) và `_tuy_chon.json` phải đúng kiểu.

  Sai ở bất kỳ điểm nào → `unknown` có lý do.
- **Các đường đi qua gate:**
  - `chi_tiet_luot` (qua `_chi_tiet_common`);
  - `ds_luot`;
  - callback chi tiết của viec (`_trang_thai_common`);
  - `_json_hd`;
  - `file_tai` (qua `_chan_tai_common`).

  Chưa niêm phong → trạng thái được ẩn bằng `_an_ket_qua`: không `xong`, `tai = {}`, `hd` không có đường tải. Đường tải/xem trả 409 `COMMON_CHUA_NIEM_PHONG`.
- **Kết quả đã niêm phong là bất biến.** `sua_o`, `ghi_lai_danh_muc` và `nap_csdl_tu_ket_qua` trên lượt common → 409 `COMMON_BAT_BIEN`. `_json_hd` chỉ phục vụ đúng tệp mà `seal.ref` trỏ tới. Nhánh legacy không đổi.
- **DTO sai kiểu.** Kiểm `tt`, `hd[]` (gồm `file`/`ten`/`tt`/`so_vang`), `log`, `tep`, `pct`. JSON hợp lệ nhưng sai kiểu → `unknown` có lý do, trả 200, không 500.
- **Callback.** Mọi lỗi niêm phong (`Exception`) → `unknown`; việc báo `loi` với `COMMON_CHUA_RO` và không chạy lại.
- **Seal là sidecar** (`_common/ket_qua_seal.json`, typed `seal_common/v1`, CreateNew). Seal gồm `ref` tương đối, SHA và độ dài của raw, `request_sha256`, `meta_sha256` và identity. Raw không bị sửa và không chứa hash của chính nó.

### R1 — Client central
- `body_sha256(yc)` dùng cùng quy tắc canonical với nguồn.
- **Chỉ nhận kết quả khi đủ:** `common.tt == "done"`, seal typed đúng `request_id` và body H, `ref` tương đối an toàn, SHA và độ dài đúng kiểu.
- **Không đủ (chờ, hết hạn → `ChuaRo`):** top-level `xong` mà thiếu common hoặc thiếu seal. Không bao giờ coi là kết quả tốt, cũng không thành lỗi cuối.
- **Lỗi cuối** chỉ khi common khẳng định `loi`/`da_dung`.
- Client tải đúng `hd` có `tai.json` kết thúc bằng `/{luot}/{seal.ref}`. Bytes tải về phải đúng SHA/độ dài của seal, lệch → `ChuaRo`. `kiem_ket_qua` kiểm thêm `body_sha256`.

### R2 — Toàn vẹn canonical (nguồn)
- **Bản ghi typed** (`registry_common/v1`, `giu_common/v1`, link = bytes của registry) mang `request_id`, `luot`, `source_sha256`, body và `body_sha256`.
- `_kiem_ban_ghi` dẫn xuất lại body bằng `_kiem_common`, băm lại canonical và kiểm sự nhất quán `luot`/`source`/`request_id`.
- **Registry trỏ tới lượt đã có dữ kiện** mà chưa có liên kết → `COMMON_CHUA_RO`, không gắn ý định vào lượt khác. Khôi phục khe ghi chỉ được phép trên thư mục lượt trống.
- **Metadata tin cậy** được dẫn xuất bằng cùng hàm `_meta_ky_vong` cho cả lúc chụp lẫn lúc recovery:
  - kiểm SHA bytes của bản chụp HĐ và danh mục;
  - `chon_tham_so` chạy lại trên **bản chụp danh mục**, nên ALL được mở rộng đúng tập/thứ tự và tập con không lạ hay trùng;
  - snapshot tham số được dẫn xuất lại.
- **Implementation.** `_sha_impl(tep_sha256)` phải bằng `implementation.sha256` đã chụp của chính lượt đó, và `rules.master_hd_sha256` phải khớp map.
- **Trước khi seal:** bytes của `request.json` phải đúng SHA đã chụp, và `native.common` phải khớp **từng trường** của metadata tin cậy (bản deepcopy bất biến). Tập mã và thứ tự `bang` đúng, chế độ RULE_ONLY.
- **Phân biệt thiếu và hỏng:** `_doc_json_chat` trả `None` khi thiếu, `_Hong` khi hỏng. Thiếu `request.json` → `orphaned`. Có nhưng sai → `unknown`. `_luot.json` `xong` mà không có seal → `unknown`.

### R3 — UNKNOWN trước conflict
- Ở replay/start/create, bản ghi không kiểm được → `COMMON_CHUA_RO` **trước** khi so `request_id`/body để kết luận `COMMON_XUNG_DOT`. Không chạy lại, không ghi đè.

### Tests FIX03 (viết thêm, **NOT_RUN**) — phân loại

**API nguồn thật in-process sau khi Root áp patch** (`test_common_api.py`, HTTP loopback tới `tao_may_chu(0)`; chưa chạy):
- `ket_qua_goc` (dùng cho c01/c02/c05/c09/c15–c17) nay bắt buộc: `done` + seal, đường tải đúng `/{luot}/{ref}`, và SHA/độ dài của **bytes thô tải thật** bằng seal. Đây là các ca positive không rỗng, chạy trước negative.
- **c15 — barrier thật** giữ `_niem_phong` sau khi worker đã `xong` và raw đã nằm trên đĩa.
  - Trước khi thả: status/list/viec/`/tai/`/view hd đều chưa công bố; ảnh thư mục không đổi.
  - Thả: đúng bytes của seal; PATCH ô → `COMMON_BAT_BIEN`.
  - Seal lỗi trong cùng cửa sổ: `unknown` có lý do, việc báo `loi`, replay → 409 `COMMON_CHUA_RO`.
  - Khởi động lại trong cửa sổ (mô phỏng bằng xóa bộ nhớ sau khi callback lỗi): vẫn `unknown`, không có LUOT mới, ảnh không đổi.
  - Giới hạn: "restart" ở đây là mô phỏng in-process, không phải kill tiến trình thật.
- **c16 — DTO sai kiểu** (JSON hợp lệ) ở `_luot.json` (5 ca) và `_tuy_chon.json` (2 ca) → `unknown` có lý do trên mọi đường, không 500. Khôi phục bytes (ghi đè, đã sao lưu CreateNew) → công bố lại đúng seal.
- **c17 — 17 đột biến có mục tiêu** (giữ khớp các hash đối chiếu cũ khi cần, assert **đúng chuỗi lý do**):
  - `request.json`: loại, catalog_id, source, ALL→tập con, `tham_so_yeu_cau`, snapshot;
  - implementation: SHA, và map + SHA nhất quán (bắt ở `native.common`);
  - `native.common` / thứ tự `bang`;
  - seal `ref` trỏ sang `request.json`;
  - liên kết: luot/source/body/thiếu trường;
  - giữ chỗ: luot/kiểu;
  - thêm một ca seal bị thay khi lượt còn trong bộ nhớ.

  Mỗi ca: replay 409 `COMMON_CHUA_RO`, không LUOT mới, ảnh thư mục không đổi.
- **c18 — registry và khe ghi:**
  - registry đổi luot sang lượt legacy đã có tệp, hoặc đổi source → `COMMON_CHUA_RO`, ảnh không đổi;
  - registry ghi thiếu `luot` ở khe ghi → `COMMON_CHUA_RO`, không cấp lượt;
  - tiến trình chết (BaseException) ở khe ghi bản chụp danh mục → `orphaned` / `COMMON_MO_COI`, không chạy lại;
  - ghi danh mục lỗi → `COMMON_CHUP_LOI` bền.
- c08 giữ nguyên: đúng **4** phản hồi, không thread sống. c11/c13/c14 giữ oracle đường dẫn + SHA + độ dài.

**IO-mock** (`test_trich_chung_6.py`, không phải HTTP nguồn thật):
- `NguonGia` nay trả common `done` + seal typed tính trên bytes thật. Hook `sua_tt` cho phép tiêm sai.
- Positive trước: tập con không rỗng, `raw_sha256` bằng bytes, `body_sha256` khớp.
- 11 ca thiếu common / chưa `done` / thiếu seal / seal sai kiểu, ý định, body, ref (`..`, tuyệt đối), độ dài, SHA → `ChuaRo` và **không tải raw**. Seal ref hợp lệ nhưng khác đường tải → `ChuaRo`.
- Top-level `loi` không có common → `ChuaRo`; common khẳng định `loi` → `TRICH6_LUOT_LOI`.
- R3 seal lệch được giữ.
- Ba caller: đúng **3** kết quả, không thread sống, thu mọi `BaseException`, một raw hash.

**UNIT:** `kiem_ket_qua` có thêm đột biến `body_sha256`.

**Chưa kiểm:** source API/HTTP thật (chưa áp patch, chưa chạy); hai consumer `XayDungK2`/`CrmK2` qua HTTP central/PG với engine thật; GUI; kill tiến trình thật.

**Retained staging:** FIX03 không đổi `write_immutable`/storage của central nên không phát sinh staging mới. Kiểm kê staging diagnostics (parent/hash/bytes/số lượng) cần làm khi Root chạy; báo cáo này **không** khẳng định "zero file".

### Giới hạn sau FIX03
- Tệp `_tuy_chon.json` vẫn được ghi bằng `open("w")` như trước (không phải CreateNew). Giờ nó được kiểm kiểu nhưng không băm/niêm phong.
- Lượt common tạo bằng patch **trước** FIX03 (bản ghi chưa typed, seal chưa có `kieu`/`request_sha256`/`meta_sha256`) sẽ là `unknown` khi nạp lại. Đây là fail closed có chủ ý, không có migration.
- `_cong_bo` đưa bản ghi trong bộ nhớ về `unknown` vĩnh viễn khi phát hiện lệch. Sửa lại bytes không tự mở lại công bố cho tới khi khởi động lại hoặc nạp lại.
- Toàn bộ là CODE_ONLY: **không** chạy import/AST/test/HTTP/SQL. Chưa có kết quả PASS nào cho FIX03. Mọi tên hàm hay hành vi của `QLV.lay`, `ket_thuc` và route PATCH ô mà test dùng đều bám staged `server.py`/`viec.py` đọc tĩnh.

## 9. FIX04 — integrity còn thiếu và chặn endpoint legacy (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-CRM-41-01-04-INTEGRITY-VA-CAPABILITY.md`. Sửa đúng **6 file hiện có**, **NEW = 0**, không xóa file nào:
`docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py`, `docs/CRM-41-01-SOURCE-PATCH/may_chu/server.py`, `docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py`, `src/kho_tri_thuc/nguon/trich_chung_6.py`, `tests/test_trich_chung_6.py` và báo cáo này.

Không sửa thuật toán, catalog, CRM service/UI, adapter M4, M9 hay migration. Chỉ sửa staged source patch; coder không đọc hay ghi source gốc.

**Baseline:** native18 18/0/0/0 và kiểm độc lập HTTP nguồn mà Root báo chỉ mô tả mã **trước** FIX04. Self-test cho mã sửa mới: **NOT_RUN**.

### Đã sửa
- **R1 — tên lượt gắn với giữ chỗ bằng dữ kiện độc lập.**
  - Create common ghi **bản ghi đặt lượt** `ket_qua/_common_dat_luot/<luot>.json` (typed `dat_luot_common/v1`, CreateNew, gồm `luot`, `request_id`, body H) **trước** registry.
  - Mọi lần đọc lại registry đều yêu cầu bản ghi đặt lượt khớp (`_kiem_dat_luot`). Registry bị đổi `luot` sang tên hợp lệ còn trống → 409 `COMMON_CHUA_RO` (`ly_do = dat_luot`), không mkdir và không link.
  - Khe ghi sau khi đặt lượt nhưng trước registry: lần thử lại tìm đúng bản ghi đặt lượt của ý định (`_tim_dat_luot`). Chỉ dùng lại được khi thư mục lượt chưa có hoặc còn trống, nên không cấp lượt khác.
  - Tên trong `_common_dat_luot` được tính vào tập tên đã giữ.
- **R2 — `done` còn trong cache vẫn bị kiểm lại.** Gate `_cong_bo` kiểm lại bản ghi giữ chỗ typed và chạy `_kiem_request`, tức kiểm SHA bytes bản chụp DOCX/danh mục, chọn lại tham số từ bản chụp và so `request.json` với metadata dẫn xuất. Sau đó mới kiểm seal ghim + `_kiem_seal`. Không cần pop cache hay restart; không chạy lại, không ghi đè.
- **R3 — DTO kiểm cả giá trị reachable.**
  - `_kiem_dto_luot` kiểm:
    - `tep`: khóa/giá trị là chuỗi, đường dẫn tương đối an toàn;
    - `log`: mốc thời gian hữu hạn trong `[0, năm 9999)`, không nhận bool, thông điệp là chuỗi;
    - `hd[].ten`: một thành phần tên an toàn;
    - `danh_muc` là chuỗi, `pct` hữu hạn.
  - `_common_loi.json` có `loi` phải là chuỗi.
  - `_luot_da_dat_cho(chat=True)` khi create common: registry đọc được mà `luot` sai kiểu → 409 `COMMON_CHUA_RO` có lý do, không bị đưa vào set. API cũ (`chat=False`) giữ hành vi bỏ qua.
- **R4 — chặn ghi danh mục trên lượt common.** `ghi_lai_danh_muc` chặn lượt common bằng 409 `COMMON_BAT_BIEN` **trước** khi liệt kê kết quả, trước nhánh danh sách rỗng và mọi I/O workbook. `_json_hd(ghi=True)` trả `COMMON_BAT_BIEN` ở mọi trạng thái, trước gate công bố. Legacy không đổi.
- **R5 — preflight và ACK.**
  - Server có route mới `GET /api/trich_xuat/common` → `dv.nang_luc_common()`. Kết quả typed `nang_luc_common/v1` gồm contract, `modes=["RULE_ONLY"]`, mỗi loại `catalog_id`/`catalog_sha256` đã ghim, và readiness tính từ bytes catalog thật cùng các tệp implementation. Preflight không đọc cấu hình/AI, không mkdir, không ghi.
  - Client `nang_luc()` chạy **trước** mọi POST và trước khi ghi ý định cục bộ. Endpoint 404/HTML/không phải object, thiếu/sai kiểu, khác mode/contract, chưa sẵn sàng, hoặc khác catalog id/sha → `DataError TRICH6_KHONG_HO_TRO_COMMON`. Đây không phải `ChuaRo` và client không fallback sang API cũ.
  - `tao_luot` (common) yêu cầu ACK có `request_id` bằng ID logic, `type(lap_lai) is bool` và `luot` hợp lệ. Sai → `ChuaRo` (rewrap `TRICH6_CHUA_RO`), dừng trước khi lưu `10_luot`, trước upload/start.

### Tests FIX04 (viết thêm, **NOT_RUN**)
**Source API in-process** (`test_common_api.py`, chưa chạy):
- c19: positive reserve/replay → registry đổi `luot` sang tên trống → 409; tên mới không xuất hiện, `anh(out)` không đổi, không compute; khôi phục thì đúng lượt cũ. Khe ghi registry lỗi sau khi đặt lượt → thử lại đúng lượt đã đặt, một bản ghi đặt lượt. Đối ứng "lượt legacy đã có tệp" của c18 vẫn giữ.
- c20: DOCX và catalog snapshot, mỗi loại hai ca (cache còn / sau restart) → UNKNOWN đúng lý do trên status/list/viec/raw/view, replay 409, ảnh không đổi.
- c21: 9 đột biến độc lập trên `_luot.json` thật → UNKNOWN đúng lý do, replay 409; khôi phục thì công bố lại. Registry `luot = []` → create ý định khác 409 `COMMON_CHUA_RO` với lý do "luot sai kiểu"; API cũ vẫn 200.
- c22: lượt common chờ (create + upload) và lượt `done`, có và không có `ten` → `COMMON_BAT_BIEN`. Sentinel `ghi_danh_muc` không bị chạm; ảnh `HD_DU_LIEU` không đổi. Có đối chứng legacy 200 trên workbook DEMO trong HD env.
- c23: preflight typed/ready/chỉ đọc. Catalog ghim không có → `san_sang = false`, `CATALOG_THIEU`. ACK create đúng DTO.

**IO-mock** (`test_trich_chung_6.py`):
- `NguonGia` trả preflight và ACK `{luot, lap_lai, request_id}` đúng DTO nguồn.
- Positive kiểm thứ tự gọi: preflight → create → GET → upload → start.
- 14 ca preflight lỗi: lỗi rõ, chỉ một GET, zero POST, không thư mục ý định.
- 6 ca ACK sai: ChuaRo, đúng một POST create, zero upload/start, không có `10_luot`. Thử lại cùng ID → cùng lượt/body, một start.
- Lịch R1 của FIX02: điều kiện giữ GET loại trừ GET preflight để giữ đúng lịch nhân quả cũ. Assertion không đổi.

### Còn thiếu / giới hạn
- Kiểm kê retained `.raw-*` staging (parent/hash/bytes/count) chưa làm được vì không chạy. Báo cáo không khẳng định zero.
- Registry/lượt common tạo trước FIX04 không có bản ghi đặt lượt, nên replay create sẽ 409 `COMMON_CHUA_RO` (fail closed, không có migration).
- `_cong_bo` giờ đọc lại bản chụp catalog và chọn lại tham số mỗi lần công bố một lượt `done`. Chi phí I/O mỗi lần poll chưa đo.
- Test c23 giả định mọi tệp trong `_TEP_IMPL` có mặt ở source thật; chưa kiểm.
- Consumer M4/CRM nhận `TRICH6_KHONG_HO_TRO_COMMON` như một DataError thường (không sửa consumer theo phạm vi). Chưa có central PG/GUI/two-consumer HTTP.
- Không có kết quả PASS nào cho FIX04.

## 10. FIX05 — Windows và trạng thái phục hồi (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-CRM-41-01-05-WINDOWS-VA-TRANG-THAI.md`. Sửa đúng **5 file hiện có**, **NEW = 0**, không xóa file nào:
`docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py`, `docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py`, `src/kho_tri_thuc/nguon/trich_chung_6.py`, `tests/test_trich_chung_6.py` và báo cáo này.

Các phần giữ nguyên: staged `server.py` (route), UI, CRM, adapter M4, catalog, thuật toán, migration 1–20 và M9. Không thêm state DB hay framework. Chỉ sửa staged patch; source thật vẫn ở bản trước FIX04.

**Baseline:** 23/24 client PASS và 1 FAIL Windows do Root chạy là baseline **trước** FIX05. Self-test mã sửa mới: **NOT_RUN**.

### Đã sửa
- **R1 — Windows, đường dẫn extended-length.** Hàm mới `dang_chuan_duong_dan`/`cung_duong_dan` chỉ bỏ đúng hai tiền tố `\\?\X:\` và `\\?\UNC\`; các tiền tố khác giữ nguyên nên không bằng. Sau đó dùng `normcase`.
  - `_thu_muc` vẫn resolve và vẫn băm tên ID. Hàm kiểm `d.name == sha` và cha của `d` bằng gốc theo dạng chuẩn.
  - Junction/symlink trỏ ra ngoài (resolve ra cha khác) vẫn bị chặn. Không tắt guard, không nuốt lỗi.
- **R2 — ý định đã giữ cộng preflight lỗi → UNKNOWN.**
  - `trich()` đọc `00_yeu_cau.json` (chỉ đọc) **trước** preflight; body khác → `TRICH6_XUNG_DOT` như cũ.
  - Ý định đã giữ mà preflight lỗi (404/chưa sẵn sàng/catalog khác/mất kết nối) → `ChuaRo TRICH6_CHUA_RO`: không POST, không ghi, không đổi bytes/body/khóa.
  - Ý định mới gặp preflight lỗi vẫn là `TRICH6_KHONG_HO_TRO_COMMON`, zero POST, zero ghi.
  - Bảo thủ: nếu `00_yeu_cau` tồn tại thì luôn coi là có thể đã có hiệu lực.
- **R3 — timestamp.**
  - `_kiem_dto_luot` kiểm kiểu trước: loại bool, chỉ nhận int/float.
  - int được so miền trực tiếp, không `float()`, nên `10**400` không còn gây `OverflowError`.
  - float phải hữu hạn và trong miền.
  - Cuối cùng gọi `_dinh_dang_gio` (`localtime` + `strftime` như đường hiển thị). Lỗi → `_Hong` "không định dạng được".
  - `_chi_tiet_common` render qua cùng hàm, lỗi → UNKNOWN. Legacy và module `time` toàn cục không đổi.
- **R4 — bản ghi đặt lượt ghi dở.** `_tim_dat_luot` không còn bỏ qua bản ghi đặt lượt hỏng, ghi dở, sai kiểu hay lệch tên: trả `_Hong` → 409 `COMMON_CHUA_RO` (ly_do nêu tên tệp). Không cấp lượt khác, không xóa/ghi đè.
  - Hệ quả có chủ ý (fail closed): **mọi** create common mới cũng UNKNOWN cho tới khi người vận hành xử lý bản ghi đó.
- **C22 — đối chứng legacy.** Chuyển sang writer **spy** do test sở hữu; template và đầu ra DEMO trong `HD_DU_LIEU/demo_c22`. Test kiểm route + forwarding: đúng 1 lần gọi, đúng args `([], out, mau)`, đúng response, ảnh dữ liệu không đổi.
  - **Full workbook writer I/O = NOT_RUN** ở ca này. Đây không phải round-trip workbook đạt.
  - Các ca common pending/done có và không có `ten` (`COMMON_BAT_BIEN`, sentinel zero call, ảnh zero effect) giữ nguyên.

### Tests FIX05 (viết thêm, **NOT_RUN**)
**Unit / IO-mock** (`test_trich_chung_6.py`):
- Dạng chuẩn đường dẫn (thuần chuỗi, mọi OS).
- *Chỉ Windows:* ba caller đồng thời với `Path.resolve` trả `\\?\` xác định cho thư mục ý định đã có → đúng 3 kết quả / 1 lượt / 1 start, join đủ. Đường thoát ra ngoài (có tiền tố) vẫn `TRICH6_DUONG_DAN_Y_DINH`.
- *Chỉ Windows:* gốc thật dài > 260 ký tự, ba caller. Máy không cho tạo đường dài thì skip có lý do.
- ACK sai → preflight 404/chưa sẵn sàng/catalog khác/mất kết nối → `ChuaRo`, không POST thêm, ảnh ý định không đổi. Body khác vẫn xung đột. Ý định mới vẫn lỗi rõ, zero ghi. Phục hồi → đúng lượt cũ, body cũ, một start.
- Test 3 caller cũ giữ nguyên.

**Source API** (`test_common_api.py`):
- c21 thêm `±10**400` và ca lỗi định dạng có kiểm soát: proxy chỉ thay tên `time` trong `dich_vu`, từ chối `localtime` cho mốc DEMO trong miền. Kết quả UNKNOWN trên status/list/viec/raw/view, replay 409, ảnh không đổi; khôi phục thì công bố lại.
- c22: legacy spy như trên.
- c24: bản ghi đặt lượt ghi dở → retry ×2 409 có tên tệp, `anh(out)` không đổi, không compute, bản ghi dở giữ nguyên bytes. Ý định khác cũng 409 (đặt cuối thứ tự tên).

### Còn thiếu
- Workbook writer I/O thật (legacy round-trip) chưa có ca chạy nào trong phạm vi này.
- Chưa có cơ chế vận hành xử lý bản ghi đặt lượt ghi dở; create common mới bị chặn tới khi Root/người vận hành xử lý.
- Hai ca Windows phụ thuộc OS; ca đường dài có thể skip nếu máy không bật long path.
- Không có kết quả PASS nào cho FIX05. Toàn M4/CRM/M2 chưa xong.

## 11. CRM-41-01-06 — Nút DEMO tự mở engine #6 dùng chung (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-CODE-CRM-41-01-06-MO-DEMO-ENGINE.md` và quyết định engine chung (`54be96e9…dfadb`). Sửa **10 file hiện có + 2 file mới**, không xóa file nào:

| Loại | File |
|---|---|
| Hiện có | `src/kho_tri_thuc/giao_dien/server.py` |
| Hiện có | `src/kho_tri_thuc/giao_dien/m4.py` |
| Hiện có | `start-web.ps1` |
| Hiện có | `src/kho_tri_thuc/nguon/trich_chung_6.py` |
| Hiện có | `src/kho_tri_thuc/k2/crm.py` |
| Hiện có | `src/kho_tri_thuc/k2/xay_dung.py` |
| Hiện có | `tests/test_trich_chung_6.py` |
| Hiện có | `docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py` |
| Hiện có | `docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py` |
| Hiện có | báo cáo này |
| Mới | `src/kho_tri_thuc/nguon/trich6_host.py` |
| Mới | `tests/test_trich6_host.py` |

Các phần giữ nguyên: CMD, runtime selector, bootstrap PG, staged `server.py` nguồn, NR, thuật toán, catalog, migration 1–20 và M9. Không đọc hay ghi mã nguồn thật; không có framework, core hay DB mới.

### Đã sửa
- **Vòng đời host** (`trich6_host.py`).
  - `LocalApp` constructor không spawn.
  - Chỉ `serve()`/CLI DEMO (`environment ≠ that`) tạo `Trich6Host(<DataRoot>/trich6-demo, nguồn đã chốt)`, đánh dấu chế độ quản lý **trước** khi spawn, rồi khởi động trong luồng nền sau khi central đã nghe cổng. `finally` gọi `host.stop()`.
  - Tiến trình con chạy `sys.executable -X utf8 -m kho_tri_thuc.nguon.trich6_host --child`: cùng runtime, `PYTHONPATH` = src central + runtime/guard hiện hành, chạy ẩn (`CREATE_NO_WINDOW`), `cwd` = DataRoot DEMO.
  - Môi trường con lọc theo danh sách giữ: bỏ `PG*`, API key, `KHO_*`, `HD_*` của parent. `PYTHONDONTWRITEBYTECODE=1`.
  - Windows Job `KILL_ON_JOB_CLOSE` được gán **trước** khi ghi cấu hình (có token) vào stdin.
  - Con đọc một dòng cấu hình **trước** mọi import nguồn. Con đặt `HD_DU_LIEU`/`HD_OUT_DIR`/`HD_DANH_MUC_HD`/`HD_CSDL`/`HD_THU_MUC_KHOA` vào DataRoot DEMO, bỏ biến AI, `sys.dont_write_bytecode`, rồi gọi `may_chu.server.tao_may_chu(0)` thật. Con không gọi `main()`, không thăm dò AI, không gọi `_thay_ban_cu`.
  - Bắt tay qua kênh stdout riêng (sys.stdout của con chuyển sang stderr, mà stderr đã bỏ): `{instance_id, pid, port, implementation_sha256}`. Sau đó parent kiểm preflight có xác thực, implementation phải khớp.
  - Dừng bình thường: EOF stdin → server shutdown/close → chờ việc tối đa ~25 giây. Quá hạn thì `TerminateJobObject`. Mọi lỗi khởi động đều dọn đúng tiến trình/Job của instance đó.
- **Handler sở hữu theo instance.** `lop_handler_so_huu` bọc `srv.RequestHandlerClass` sau factory và trước `serve_forever`, không đổi ROUTES/Handler toàn cục.
  - `_hop_le` theo `self.server.server_port`. Token 256-bit chỉ trong bộ nhớ, so bằng `hmac.compare_digest` qua header `X-Trich6-Token`, áp cho **mọi** request.
  - Cổng chặn đứng trước legacy/static và `/api/tat`. Chỉ mở:
    - GET `/api/trich_xuat/common`;
    - POST `/api/trich_xuat` (đúng `{contract, request_id, yeu_cau}` common, `RULE_ONLY`);
    - GET `/api/trich_xuat/<lượt common>`;
    - POST `/tep`, `/dung` và `/chay` (`/chay` cần body common `RULE_ONLY`) trên lượt common;
    - GET `/tai/…` chỉ khi khớp đúng `seal.ref` của lượt đã niêm phong.
- **Consumer.**
  - `LocalApp.trich6_client(goc)`: ở chế độ quản lý, host chết/chưa có → client `""` (NOT_READY, không fallback `KHO_TRICH6_URL`). Ngoài chế độ quản lý → seam cũ.
  - CRM `crm_trich` và M4 `_review_lenh` đều dùng factory này.
  - `Trich6Client(token=…)` có header riêng; `repr` không lộ token hay địa chỉ.
- **Health.** `/api/health` có thêm `trich6`: `{quan_ly, san_sang, ly_do, instance, pid, implementation_sha256}`, không URL/cổng/token. Mỗi lần gọi đều kiểm sống thật.
- **start-web.ps1.**
  - Xác định `$kttIsThat` sớm.
  - Health cũ thiếu `trich6`, hoặc engine chết/lệch implementation → stale → tái khởi động đúng central đã xác minh.
  - `Assert-KttListener` (PID trong health = PID đang nghe = đúng tiến trình của kho này) chạy cả khi dùng lại lẫn sau khi khởi động.
  - `Wait-KttTrich6` báo engine DEMO sẵn sàng hoặc chưa kèm mã. Engine chưa sẵn sàng không chặn các chức năng khác. Bản THẬT không bị bắt có engine.
- **Thiếu URL theo giai đoạn.**
  - Client: `trich()` không còn chặn sớm. Sau khi tra ý định (chỉ đọc): ý định mới → `TRICH6_CHUA_SAN_SANG`, zero POST, zero ghi; đã giữ → `ChuaRo`. `kiem_giai_doan(request_id)` chỉ đọc.
  - M4 `XayDungK2.trich`: kiểm giai đoạn **trước NR**, sau quyền/hồ sơ/revision. Ý định mới → `M4_TRICH6_CHUA_SAN_SANG`; đã giữ → `M4_TRICH6_CHUA_RO`. Không gọi NR nên không ghi FINAL LOI.
  - CRM `trich_tu_docx`: client `None` → lỗi cấu hình. Chưa sẵn sàng: ý định đầy đủ đã có thì kiểm xung đột trước, rồi `ChuaRo`; chưa có → `CRM_TRICH6_CHUA_SAN_SANG`, không ghi ý định hay raw.
- **Staged `_tim_dat_luot`.** `request_id` phải khớp `RE_REQUEST_ID`; rỗng hoặc sai định dạng → UNKNOWN.

### Tests (viết thêm, **NOT_RUN**)
- **`tests/test_trich6_host.py` (mới).**
  - *Đơn vị:* argv/env con không chứa bí mật; khởi tạo không spawn; thiếu nguồn → `NGUON_KHONG_CO` mà không spawn; factory ở chế độ quản lý không fallback môi trường; kiểm tĩnh constructor/serve/m4/start-web.
  - *HTTP in-process với handler gốc và `dv` giả:* 7 route positive tới được handler gốc, body được đệm nguyên bytes. 25 ca bị chặn (token, Host, Origin, X-HD, `/api/tat`, `{}` create/chay, mode AI, lượt legacy, list/viec/UI/cài đặt/AI, tải tệp không phải ref niêm phong hoặc thoát gốc, `nap_csdl`, `chay_lai`, DELETE, PUT) và **không** request nào tới handler gốc.
  - *Thật, chỉ Windows và khi có nguồn tại vị trí đã chốt:* bootstrap/ready, health không chứa token, DataRoot riêng, preflight thật cùng implementation, không token → 403, `/api/tat` → 404 và engine vẫn sống, `{}` → 404, legacy → 404, stop thì tiến trình chết và cổng đóng; hai instance độc lập; buộc dừng "central" thay thế → Job giết engine của nó, instance khác không bị chạm. **Skip không phải PASS.**
- **`tests/test_trich_chung_6.py`.** Thiếu URL theo giai đoạn (mới/đã giữ/xung đột/phục hồi); token chỉ trong header. M4 và CRM chạy unit trên đối tượng thay thế (không PG/HTTP central), `quyen.kiem` được thay ghi rõ: quyền trước, zero ghi K2, không gọi NR.
- **`test_common_api.py`.** c23b: bản ghi đặt lượt có `request_id` rỗng/sai định dạng → 409; được ghi đè thành ý định khác hợp lệ (có sao lưu CreateNew) để không ảnh hưởng c24.

### Còn thiếu / giới hạn
- Chưa chạy gì: không launcher thật, không GUI, không HTTP central→PG với engine sở hữu, không trích hai consumer qua nút. **Không tuyên bố GUI, độ chính xác hay toàn bộ CRM/M4 PASS.**
- Đường nguồn mặc định là hằng số theo quyết định engine chung, có thể ghi đè bằng `--trich6-source` (host tin cậy). Máy không có nguồn → health `NGUON_KHONG_CO`.
- Mã nguồn thật phải có patch F11+ (`_implementation`, `_cong_bo`, `_la_luot_common`, preflight). Chưa kiểm khả năng import nguồn chạm cấu hình hay khóa ở mức module.
- Trên Windows, central dùng venv redirector thì `pid` trong health là PID python thật do con báo (vẫn nằm trong Job). Ngoài Windows không có Job.
- Health mỗi lần gọi một preflight loopback (timeout 3 giây). `start-web` đã tăng timeout health lên 5 giây.
- Bản ghi đặt lượt ghi dở (FIX05) vẫn chặn create mới cho tới khi người vận hành xử lý.

## 12. CRM-41-01-06A — Giữ guard và xác nhận dừng owned engine (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-CRM-41-01-06A-GUARD-VA-DUNG-ENGINE.md`. Sửa đúng **3 file hiện có**, **NEW = 0**, không xóa file nào:
`src/kho_tri_thuc/nguon/trich6_host.py`, `tests/test_trich6_host.py` và báo cáo này.

Không sửa client, callers, `server.py`, launcher, SQL, staged source, source thật, catalog, thuật toán hay M9. Vẫn giữ: Job gán trước khi gửi stdin, factory thật, chỉ common/v1, auth bằng token, tải chỉ đúng ref niêm phong, chế độ quản lý.

**Baseline:** 32/32 pure và lịch sử native/HTTP→PG đều là kết quả **trước** 06A. Self-test cho mã mới: **NOT_RUN**.

### Đã sửa
- **Guard (mục 1).**
  - `ENV_GIU` thêm `PYTHONUSERBASE` và `CODEX_NO_DELETE_FILES`, giữ được cả hai đường khởi động guard (tệp `.pth` trong user site-packages qua USERBASE — *06B sửa mô tả: không phải usercustomize* — và sitecustomize qua PYTHONPATH). Vẫn lọc PG/DSN/API/cloud/`KHO_*`/`HD_*`. Token vẫn chỉ đi qua stdin.
  - `chung_cu_guard()` chỉ đọc, không import guard:
    - module `codex_no_delete_guard` phải có sẵn trong `sys.modules` từ khởi động;
    - SHA-256 bytes tệp guard đang nạp;
    - cờ `CODEX_NO_DELETE_FILES`;
    - danh sách điểm vào xóa/ghi đè (`os`/`shutil`/`pathlib`) đang là hàm định nghĩa **trong chính tệp guard**;
    - `sys.flags.dont_write_bytecode` (cờ lúc khởi động, không phải giá trị tự đặt).

    Kết quả không chứa đường dẫn.
  - `guard_hop_le()` yêu cầu đủ: module có, SHA = `a517c535…a229`, cờ bật, ít nhất một hook thật, bytecode tắt. Thiếu điều nào thì trả mã `GUARD_*` tương ứng.
  - Parent kiểm guard của chính nó trước khi spawn: thiếu → `LoiHost GUARD_*`, không spawn, health NOT_READY.
  - Child kiểm **ngay sau khi đọc cấu hình, trước** mkdir/`HD_*`/import nguồn/server: thiếu → báo `{kieu: loi, ma: GUARD_*}` rồi thoát mã 4.
  - Bắt tay gửi kèm `guard` (lấy lại sau khi nạp nguồn). Parent kiểm lại bằng cùng quy tắc, không chỉ tin chuỗi hash.
  - Entry `_con(stdin, kenh)` nhận kênh bắt tay từ `__main__`, nhờ vậy test trong tiến trình không đổi `sys.stdout`.
- **Dừng có xác nhận (mục 2).**
  - `_JobWindows` thêm `so_tien_trinh()` (`QueryInformationJobObject`, BasicAccounting → `ActiveProcesses`; lỗi → `LoiHost`). `ket_thuc()` thất bại thì báo `LoiHost`.
  - `_don()`: EOF → chờ grace → nếu quá hạn thì kết thúc đúng Job (hoặc kill đúng Popen khi không có Job) → chờ tiến trình kết thúc (quá hạn thì báo lỗi). Sau khi con đã thoát vẫn kiểm Job: còn worker active thì kết thúc Job, rồi chờ Job rỗng trong hạn `cho_job`.
  - Mọi lỗi đều thành `LoiHost` có `pha`. `finally` luôn đóng đúng handle Job sở hữu; không quét theo tên tiến trình, không chạm PID ngoài.
  - `stop()` chỉ đặt `DA_DUNG` sau khi đã xác nhận. Chưa xác nhận → `LoiHost DUNG_CHUA_XAC_NHAN`, trạng thái `DUNG_CHUA_XAC_NHAN`, witness `{popen_pid, pid, pha, ma}` hiện trong health (không có token/cổng), client NOT_READY.
  - Dọn sau lỗi khởi động không che lỗi gốc mà ghi thêm `+DUNG_CHUA_XAC_NHAN`.
  - **Lưu ý:** `serve()` (không sửa ở lượt này) gọi `host.stop()` trong `finally`. Nếu dừng chưa xác nhận, lỗi đó sẽ lộ ra khi thoát central thay vì bị nuốt.

### Tests 06A (viết thêm, **NOT_RUN**)
**MOCK:**
- Whitelist giữ hai biến và vẫn lọc bí mật.
- Quy tắc guard: 7 ca thiếu/sai.
- Chứng cứ hook với module guard giả + `os.remove` tạm thay bằng hàm trong tệp giả: nhận đúng `os.remove`, SHA sai → `GUARD_SHA_SAI`, không lộ đường dẫn.
- Entry con thiếu guard (3 ca): mã 4, zero import `may_chu`/`trich_xuat`, zero mkdir, `HD_*` không đổi.
- `StopXacNhanTests`:
  - positive: EOF sạch; worker còn sống → kết thúc Job → xác nhận;
  - không false-success: wait cuối quá hạn, Job không rỗng, kết thúc Job lỗi, truy vấn lỗi;
  - không Job: kill đúng Popen.

**THỰC** (chỉ Windows và khi có nguồn tại vị trí đã chốt; skip không phải PASS):
- Guard của tiến trình test (skip nếu không bật cờ).
- Lifecycle cũ, thêm guard của con (SHA/hooks khớp cha) và `DA_DUNG` đã xác nhận.
- Ca DOCX DEMO đáp án ghim (`Số: 0001/2026`) qua `h.client(...)`:
  - ALL37: đúng 37 mã, catalog H, cùng implementation lúc khởi động; TC-01 = `0001/2026`, trích dẫn là nguyên văn input; seal khớp hash/độ dài raw.
  - Tập con `['TC-01','TT-02']` trên cùng host.
  - Replay cùng ý định: cùng lượt/raw, không thêm lượt.
  - Các từ chối vẫn giữ (thiếu/sai token, `{}` create/chay, `/api/tat`, UI/cài đặt/AI/list, tải ngoài ref niêm phong); engine vẫn sống; dừng có xác nhận; instance B sống và không đổi.
- Hai đường khởi động guard (USERBASE-only / PYTHONPATH sitecustomize); nhánh nào runtime không có thì skip riêng.
- Test buộc dừng central: `finally` kill nếu cần **và** wait đúng Popen; cả hai host được dọn dù một nhánh lỗi.

Ca DOCX thật **không** chứng minh độ chính xác toàn 37 mã hay theo loại, cũng không chứng minh central hai consumer/GUI.

### Còn thiếu
- Chưa chạy gì.
- Hook guard chỉ được nhận diện khi guard thay hàm Python bằng hàm định nghĩa trong chính tệp guard. Nếu guard A517 dùng cơ chế khác (vd chỉ audit hook) thì sẽ báo `GUARD_KHONG_HOOK` (fail closed); cần Root xác nhận khi chạy.
- Ngoài Windows không có Job; ca thật chỉ chạy trên Windows.
- Launcher thật, GUI, central→PG hai consumer qua engine sở hữu vẫn chưa kiểm.

## 13. CRM-41-01-06B — Đủ ba hook guard và kiểm đúng hai đường khởi động (NOT_RUN_CODE_ONLY)

Căn cứ: `docs/GIAO-SUA-CRM-41-01-06B-GUARD-VA-KHOI-DONG.md`. Sửa đúng **3 file hiện có**, **NEW = 0**, không xóa file nào:
`src/kho_tri_thuc/nguon/trich6_host.py`, `tests/test_trich6_host.py` và báo cáo này.

Các phần giữ nguyên byte: client, callers, `server.py`, launcher, source thật, staged patch, catalog, thuật toán, SQL/master/quyền và M9. Vòng đời Job/EOF/xác nhận Job rỗng của 06A không đổi. Không sửa đường dẫn Windows theo giả thuyết.

### Bằng chứng Root (phân loại riêng, không gộp)
- source native 25/25;
- pure 32/32 (client/callers);
- owned host 17 PASS + 1 ERROR `ChuaRo` ở ca DOCX ALL37/subset/replay (**không** phải 18 PASS);
- recovery GET đọc lại lượt đã lưu: status 200 `done`, raw 200 đúng 50151 bytes/hash.

Nguyên nhân `ChuaRo` **chưa xác định**. Lượt này không đổi fixture/expected để che lỗi đó và không sửa prefix đường dẫn. Root sẽ chạy lại với witness mã lỗi.

### Đã sửa
- `HOOK_BAT_BUOC = {os.unlink, os.remove, shutil.rmtree}`. `guard_hop_le` yêu cầu **đủ ba** hook thật (hàm định nghĩa trong chính tệp guard đã nạp, nhận diện theo `co_filename`), cộng với các điều kiện cũ: module có sẵn từ khởi động, SHA A517, cờ bật, bytecode tắt.
  - Tập con một/hai hook, hoặc tên ngoài `HAM_XOA` → `GUARD_KHONG_HOOK`.
  - Không đòi đủ 13 tên.
  - Quy tắc dùng chung cho cha (trước spawn) và con (trước mkdir/`HD_*`/import nguồn).
- Sửa giả định khởi động: đường USERBASE là tệp `.pth` (`import codex_no_delete_guard`) trong user site-packages. Code không đòi sitecustomize/usercustomize; test không import guard bù.

### Tests 06B (viết thêm/sửa, **NOT_RUN**)
**MOCK:**
- Chứng cứ đạt giờ dùng đủ ba hook; thêm hook khác trong `HAM_XOA` vẫn đạt.
- 7 tổ hợp thiếu (một hoặc hai hook, kể cả có hook phụ) → `GUARD_KHONG_HOOK`.
- Con thiếu `shutil.rmtree` → mã 4, zero import nguồn/mkdir/`HD_*`.
- Cha thiếu hook → `LoiHost GUARD_KHONG_HOOK`, không spawn, không mkdir DataRoot.

**THỰC:**
- `test_06a_guard_that_cua_tien_trinh_kiem` bỏ điều kiện sitecustomize/usercustomize và thêm kiểm đủ ba hook.
- Ca kết hợp 06A (lệ thuộc `usercustomize`) được thay bằng **hai method riêng**:
  - `test_06b_userbase_pth_only`: dò provider thật bằng cách đọc `*.pth` trong user site-packages; bỏ mọi thư mục PYTHONPATH có `sitecustomize.py` nhưng giữ src/phụ thuộc.
  - `test_06b_pythonpath_sitecustomize_only`: bỏ `PYTHONUSERBASE`.

  Mỗi method kiểm guard của con hợp lệ và đủ ba hook. Thiếu provider thì skip riêng có lý do; skip **không** phải PASS.
- Ca DOCX thật (ALL37, subset TC-01/TT-02, TC-01 = `0001/2026` cùng trích dẫn input, catalog/implementation/seal/hash + độ dài raw, replay không thêm lượt, từ chối route/token, instance B không đổi, dừng có xác nhận) giữ nguyên, không đổi expected.

### Còn thiếu / giới hạn
- Chưa chạy gì. Không tuyên bố owned 18 PASS, GUI, toàn module hay độ chính xác 37 tham số.
- Nguyên nhân `ChuaRo` ở ca DOCX thật chưa được tìm hay sửa; cần Root chạy lại với witness mã lỗi.
- Nếu `.pth` hoặc sitecustomize ở máy khác nạp guard dưới dạng khác (khác tên module hoặc không cài đủ ba hook), engine sẽ fail closed `GUARD_*`.
