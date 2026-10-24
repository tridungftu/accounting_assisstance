# BÁO CÁO L11 QUANTITY — REPAIR02 (CODE_ONLY)

- **Căn cứ:**
  - Handoff `docs/GIAO-CODE-L11-QUANTITY-02.md` (pin 5cc2c222…7d2a), kế thừa handoff01 (ce65bd92…) và cases01 (6ab9e660…).
  - Review `REVIEW-L11-ROOT-ACTUAL-01.md`, `REVIEW-L11-SERVICE-02.md`, `REVIEW-L11-HTTP-UI-01.md`.
  - Candidate01 đã frozen273 (manifest 22c58d26…); fixture20 (227980804…) không đổi.
- **Chế độ: CODE_ONLY.** Không execute/import/compile/test/SQL/PG/HTTP/JS/browser/CLI/process/network. Không đọc credentials/.env/var/.git/sourceapps/dữ liệu thật. Không delete/move/drop/reset bất kỳ tệp/DB/role/attempt nào.
- **Mọi selftest của coder: UNRUN.** Không khẳng định PASS. Chưa đo số statement/checksum M0016 mới; root đo khi freeze.

## 1. Tệp đã ghi (14 tệp hiện có + tạo mới report02)

| Tệp | Thay đổi chính (line hiện hành) |
|---|---|
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` | **Chỉ phần 16.** `_L11_R1_HAM` `6560–~6700` (helper giao thức + admission + hỗ trợ nguồn); `l11_ngan_sach_noi_bo` `6749`; `l11_tieu_thu_bang_chung` `6826`; `l11_xac_nhan_bang_chung` `6966`; `l11_huy_bang_chung` `7150`; `l11_ma_hoa` `7261`; `l11_danh_gia_noi_bo` `7469`; `l11_xem_truoc` `7645`; `l11_xac_nhan` `7681`; `l11_can_soat_noi_bo` `7822`; `_m16_thay` `8078`; `_L11_R1_THAY` `8090–8138`; `M0016_L11_QUANTITY` `8140` (bảng ứng viên `8210`, bằng chứng `8240`, mã hóa `8331`, parent guard `8167`, child guard `8494`); tổ hợp `8565` = `(...) + M0016_L11_HAM + _L11_R1_THAY` |
| `src/kho_tri_thuc/k2/kho_so_luong.py` | `l11_bang_chung` `837` (RR riêng, GET proof); `_l11_bang_chung_trong` `843` (lọc phạm vi theo INTAKE/READ_SOURCE hiện hành); `l11_trang` `856` (một RR cho toàn aggregate); `l11_tong_quan` `917` / `_l11_tong_quan_trong` `926` (reader nội bộ, thêm `source_ordinal`, `dinh_nghia_nguon`, `do_luong_sha256`); `_workbook_l11` `1000` (thêm 2 cột định nghĩa đơn vị native) |
| `src/kho_tri_thuc/giao_dien/server.py` | `l11_state` `595` dùng `l11_trang`; `l11_proof` `615`; GET `/api/m5/l11/proof` `966`; mã 409/403 mới trong `M5_MA_409`/`M5_MA_403` |
| `src/kho_tri_thuc/giao_dien/assets/app.js` | `l11Act` `1194` (giữ fence gốc qua POST + GET làm mới, so thế hệ, trả `{r, fence}`); `l11Tai` `1211` (chỉ dùng fence gốc truyền vào); `l11Facts` `1228`; bảng ứng viên hiển thị H/độ dài/coverage/facts trước nút duyệt; nút FILE `1343` tải dưới fence gốc + cặp còn hiện hành; `l11Load` `1411` trả thế hệ; xem trước hiển thị tỷ lệ áp trên native |
| `src/kho_tri_thuc/giao_dien/assets/index.html` | Chỉ sửa câu mô tả mục 1 và mục 4 (HOLD theo coverage, facts trước duyệt, tỷ lệ trên lượng gốc) |
| `tests/test_l11_migrations.py` | R1/R2/R3 tĩnh, PG UPDATE retarget — UNRUN |
| `tests/test_l11_k2.py` | Lớp nền `_L11Nen`, sửa token/mã lỗi, lớp mới `L11PhiDongNhatPg` — UNRUN |
| `tests/test_l11_http.py` | Khóa duyệt, GET proof, mã lỗi chính xác — UNRUN |
| `docs/BAO-CAO-L11-QUANTITY-02.md` | Tạo mới |

Không cần sửa và **không sửa**: `lien_ket_chung.py`, `hoa_don.py`, `quyen.py`, `crm_khoi_dong.py`, `nguon_chung.py`, `l11_demo.py`.

Không chạm: report01, review docs, fixtures, pure readers, controllers, `m2_demo.py`/`m5_demo.py`, M9.

## 2. Giữ nguyên 1–15

- Không sửa byte nào của literal/generated SQL 1–15.
- Các đường cũ cần đổi được **sinh trong 16** bằng `_m16_thay(nguon, dau, cu, moi)`. Hàm này lấy **đúng** statement lịch sử cuối cùng của M14/M15, `assert` chuỗi cần thay xuất hiện đúng một lần, rồi chỉ chèn thêm dòng.
- `test_r1_11_duong_chi_chen_closure` (UNRUN) kiểm bằng `difflib` rằng mỗi đường chỉ có opcode `insert` so với bản lịch sử.
- Finalizer 16 vẫn bằng finalizer 15 cộng đúng nhánh L11.
- Không append 17, không sửa DB attempts01. Bảng/hàm L11 chỉ đổi trong 16, vì 16 chưa được nghiệm thu.

## 3. R1 — giao thức khóa/ảnh hưởng toàn batch

**Helper (`_L11_R1_HAM`)**, tất cả đều definer, đặt `search_path` và bị REVOKE PUBLIC:

- `kho.l11_khoa_dong_nguon_noi_bo(hd[], pk[]) → uuid[]`, chạy theo thứ tự:
  1. Precollect child sống chạm gốc batch.
  2. Tính gốc ngang hàng **cả hai phía**.
  3. Khóa gốc theo thứ tự `l11_khoa_goc_noi_bo` (HOA_DON_ROOT sorted, rồi PHIEU_KHO sorted).
  4. Khóa pool sorted `FOR UPDATE`.
  5. Khóa child `FOR UPDATE ORDER BY id`.
  6. **Đọc lại closure**: nếu có child mới chạm gốc batch mà gốc ngang hàng chưa khóa thì `L11_CLOSURE_MO_RONG`, toàn thao tác hủy trước mọi hiệu lực.
- `kho.l11_giu_khoa_noi_bo(k)`: đọc `pg_locks` (advisory, `pg_backend_pid()`, classid/objid tách từ `hashtextextended`).
- `kho.l11_kiem_khoa_dong_noi_bo(child[])`: mỗi child sống bị ảnh hưởng phải đang được giữ khóa gốc hai phía, nếu không thì `L11_KHOA_GOC_THIEU`.
- `kho.l11_dong_anh_xa_noi_bo(mapping)`: closure khi đóng mapping dòng / công ty / WAREHOUSE.

**11 đường** (CREATE OR REPLACE trong 16; ACL lịch sử giữ nguyên):

| Đường | Điểm chèn closure |
|---|---|
| `m5_khoa_phieu`, `m5_tieu_thu_quan_sat`, `m5_giu_cho_anh_huong` | tại điểm khóa gốc phiếu cũ, theo khóa (instance, SoPhieu) |
| `m5_xem_xet_nguon` | `(NULL, [phiếu])` trước khóa gốc |
| `m5_anh_xa_v4` | toàn bộ phiếu của kho trước `UPDATE … DONG` |
| `m2_tieu_thu_quan_sat` | toàn batch XML/ZIP: mọi hàng mapping công ty `FOR SHARE ORDER BY id`, rồi closure mọi hóa đơn **đã có** của batch, trước vòng lặp (không phụ thuộc thứ tự lặp) |
| `m2_xem_xet_nguon`, `m2_mapping_dong`, `m2_route` | `([hóa đơn], NULL)` trước khóa gốc |
| `m2_mapping_cong_ty` | mọi hóa đơn có phiên bản dưới mapping công ty đó, trước `UPDATE … DONG` |
| `master.anh_xa_nguon_kiem` (trigger BEFORE dùng chung) | khi đóng mapping, kiểm closure đã khóa **trước tuple** |

Khóa gốc cũ sau điểm chèn là tái nhập (advisory xact lock cùng phiên), không tạo thứ tự mới.

**Hiệu lực CAN_SOAT:**

- Bốn trigger AFTER giữ nguyên vai trò ghi, trong cùng giao dịch, không cần BOTH V2 và không lộ hóa đơn ngang hàng.
- `l11_can_soat_noi_bo` gọi `l11_kiem_khoa_dong_noi_bo` **trước** UPDATE và không tự xin khóa.
- Hệ quả: ghi trực tiếp bỏ giao thức (kể cả chủ bảng) bị `L11_KHOA_GOC_THIEU`; đường hợp lệ đã khóa từ precollect.
- A,A/ZIP trùng nội dung: eligible không đổi, nên không có child nào bị giữ.
- A→B→A: không có đường nào chuyển CAN_SOAT về CO_HIEU_LUC (guard child).
- Held giữ nguyên lượng/ID, sức chứa NULL khi bị chặn.

**Các thao tác L11:**

- Xác nhận: gốc → pool → hàng danh tính FOR SHARE → bằng chứng → tuyến. Đã đổi thứ tự để pool đứng trước hàng.
- Mã hóa: gốc → pool sẵn có → hàng.
- Undo: gốc → pool → child.
- Thu hồi bằng chứng: gốc → pool của closure → bằng chứng FOR UPDATE → đọc lại closure.

**Lệch có chủ đích, cần root quyết:** hàng mapping (MASTER cố định) giữ thứ tự R14/R15 là **trước** gốc trong các đường M5/M2. Lý do:

- Không đường L11 nào khóa hàng mapping.
- Đảo thứ tự này chỉ ở 11 đường sẽ tạo vòng với `m5_file_bat_dau` và intake cũ (mapping FOR SHARE → gốc), vốn ngoài danh sách 11.
- Thứ tự toàn cục vì vậy là: namespace → hàng mapping → gốc → pool → hàng.

## 4. R2 — ba phép tính số lượng

**Schema:**

- `bang_chung_quy_doi_luong`, kind NATIVE_ENCODING: `tu_don_vi_*` là định nghĩa **native**, `den_don_vi_*` là định nghĩa **own-pool**, `don_vi_*` bằng NULL, kèm `mien` (ngữ cảnh hỗ trợ native).
- Cùng định nghĩa native và pool chỉ được tỷ lệ 1/1.
- GOODS lưu `mien` (miền khai báo tường minh); CROSS có `mien` NULL.
- `ma_hoa_luong_nguon` thêm `don_vi_nguon_id/sha` (FK MASTER), `do_luong_sha256` (bắt buộc với M5). SAME_VERIFIED yêu cầu native = pool và 1/1.

**Duyệt bằng chứng:**

- NATIVE_ENCODING:
  - Native lấy từ `unit_definition` (ref + digest); pool lấy từ `pool_unit_definition_ref` (+ `pool_unit_definition_sha256` nếu khai báo).
  - Cả hai phải đạt `l11_don_vi_xac_minh_noi_bo` (tuple tài liệu khai báo R15).
  - Tôn trọng `same_definition_required`.
  - Hỗ trợ khai báo của định nghĩa native phải trỏ đúng artifact/locator/lexeme/profile của mã hóa.
  - Đã bỏ phép ép pool = native của frozen01.
- CROSS: hai định nghĩa native phải đã xác minh.

**Đánh giá cặp:**

- `x.tu_don_vi = ei.don_vi_nguon` và `x.den_don_vi = ew.don_vi_nguon`.
- Phương trình **`a × tử = b × mẫu`** trên lượng native.
- `pa`, `pb` dẫn xuất riêng qua mã hóa của từng phía.
- Guard child `lien_ket_dong_kiem` kiểm lại cùng phương trình native khi chèn.

**Giữ nguyên:** grain pool theo LINE; hai dòng split6 có hai pool; parent là cặp chứng từ; hai khóa xác nhận sinh hai child; bytes/hành vi THUNG→THUNG 1/1; profile thuần CAI-only (THUNG → normalized NULL).

**Đối chứng không đồng nhất** (`L11PhiDongNhatPg`, DB riêng, UNRUN):

- Bằng chứng tổng hợp trong bộ nhớ: THUNG native → pool `DEMO_M2_UNIT_CAI_V1`, tỷ lệ 12/1.
- Đi qua đăng ký COMMON sẵn có: instance/profile/scope bằng chứng riêng + năng lực nguồn của CFO, rồi nhận raw → CFO duyệt → mã hóa.
- Dương: 0.01/0.12 tiêu thụ 0.12/0.12; sức chứa 12/8, còn 11.88/7.88.
- Âm: 0.01/1.44 cho đúng blocker `["L11_SAI_PHEP_NHAN"]` dù pool 0.12/1.44 đều đủ ngân sách; 0 delta.

## 5. R3 — nguồn thật, miền, admission/privacy, parent, coverage

- **Binding phía kho** (bằng chứng hàng và tỷ lệ) gồm:
  - NATIVE_DETAIL SHA **và độ dài**, `SoPhieu`, `ID_Dong`;
  - **source_ordinal gốc của reader** (`lw.source_ordinal + 1`), không còn `lw.stt`;
  - master SHA thật;
  - **`measurement_payload_sha256` hiện hành** (`l11_do_luong_dong_noi_bo`: đúng một fact của instance/profile, điều kiện master SHA thật, đúng định nghĩa đơn vị, payload SHA tự tính);
  - mã hàng.
- **Miền hàng** (`mien`) đối chiếu ngữ cảnh thật của cặp: instance/profile/payload SHA của snapshot hóa đơn, company key + ref mapping công ty, instance/profile phiếu, MaKho + ref mapping kho. Sai thì `L11_BANG_CHUNG_HANG_NGOAI_MIEN`.
- **Mã hóa M2 qua bằng chứng (THUNG):** ngoài artifact/locator/lexeme/hàng, còn kiểm ngữ cảnh `q.mien` = instance/profile của snapshot dòng, miền hóa đơn của bằng chứng hàng = ngữ cảnh dòng, và định nghĩa native = DVTinh thật.
- **`l11_ho_tro_don_vi_noi_bo(dv, item)`:** artifact hỗ trợ (raw SHA + độ dài catalog) phải **đã capture** trong đúng ngữ cảnh hỗ trợ, và trường đơn vị (+ mã hàng) tại locator khai báo, do reader thật trích, phải bằng mã đơn vị. Áp cho mã hóa M5, M2 SAME_VERIFIED và M2 qua bằng chứng.
  - Giữ phân biệt MASTER chứng cứ định nghĩa 3a8… với MASTER split hiện hành 3c6…; không ép các delivery về một raw SHA.
- **Mã hóa M5** bắt buộc có khai báo đo lường hiện hành, lưu vào encoding. Ngân sách/đánh giá chặn (`L11_DO_LUONG_KHONG_HIEN_HANH`) khi đo lường đổi; held giữ nguyên.
- **Preview/xác nhận:** `l11_trang_thai_cap_noi_bo(p)` resolve **hai** endpoint typed cùng PN, cùng mọi mã hóa/bằng chứng được tham chiếu, **trước** mọi projection.
  - `l11_xem_truoc` từ chối `KHONG_CO_QUYEN_L11_XEM` thống nhất (không tồn tại / khác PN / không quyền).
  - `l11_danh_gia_noi_bo` chỉ nạp mã hóa/bằng chứng cùng PN.
  - Xác nhận khác PN cho `L11_CAP_KHAC_PHAP_NHAN`.
- **Parent chung:** `lien_ket_l11_kiem` kiểm endpoint mới cả INSERT lẫn **UPDATE đổi endpoint** của hàng chủ NULL. UPDATE giữ endpoint (CRM/M1 thật) giữ hành vi cũ. Nhánh typed bất biến/owner-only như cũ.
- **Coverage:** ứng viên lưu `coverage`, `coverage_hieu_luc`, `reported_errors` (claim gốc vẫn trong H/biên nhận COMMON).
  - PARTIAL_INPUT/UNKNOWN cho `L11_COVERAGE_<giá trị>`; hiệu lực chưa COMPLETE cho `L11_COVERAGE_HIEU_LUC_CHUA_DU`; có lỗi báo cho `L11_LOI_BAO_CAO_NGUON`. Các trường hợp này đều HOLD.
  - CHECK bảng bắt UNG_VIEN phải COMPLETE/không lỗi.
  - Duyệt HOLD cho `L11_BANG_CHUNG_HOLD`.
  - Cùng khóa đổi claim cho 409 `CAPTURE_KHAC_NOI_DUNG` trước khi ghi blob/stage.

## 6. R4 — HTTP/UI

- Aggregate `/api/m5/l11` dùng **một** snapshot RR trên một kết nối (`l11_trang`, gọi reader nội bộ dùng chung). Vẫn từ chối mở trong giao dịch ngoài.
- GET `/api/m5/l11/proof` thật, với RR riêng. Phạm vi bằng chứng lọc theo INTAKE/READ_SOURCE hiện hành. Selector giữ đúng 2 login.
- JS:
  - Fence gốc giữ qua POST → GET làm mới → tải tự động.
  - GET mới hơn thắng hoặc đổi vai/cặp/form thì bỏ kết quả cũ, không click/tải.
  - `l11Tai` không còn tự tạo fence từ epoch hiện tại.
  - CFO thấy H/độ dài/coverage/lỗi báo/facts (miền, binding, đơn vị native/pool, tỷ lệ) trước nút duyệt; LINK không nhận raw candidate (CSDL lọc READ_SOURCE).
- FILE: guard hiện hành giữ nguyên. Workbook thêm 2 cột định nghĩa đơn vị native; định dạng/bytes file nguồn M5 cũ không đổi.

## 7. Sửa test setup có căn cứ (không nới guard sản phẩm)

- **K2:**
  - `ma_hoa` lấy token **nguyên văn từ DTO công khai** `ma_hoa.expected_graph` (frozen01 tự băm `master.json_chuan` khác `{x}::text` của SQL).
  - `raises` so **mã chính xác**: tiền tố `MÃ:` của lỗi CSDL hoặc `DataError.code`, không còn chuỗi con `L11_`. Các kỳ vọng sai được sửa: GOODS làm bằng chứng mã hóa cho `L11_THIEU_BANG_CHUNG_MA_HOA`; HOLD cho `L11_BANG_CHUNG_HOLD`; tỷ lệ trước bằng chứng hàng cho `L11_THIEU_BANG_CHUNG_HANG`; FILE ngoài quyền cho `FILE_SOAT`.
  - ACL/RLS dùng SQLSTATE 42501.
- **HTTP:**
  - Khóa duyệt theo **toàn bộ** tham chiếu + thao tác (frozen01 `ref[-8:]` làm GOODS/CAI trùng khóa). Đây là **suy luận** nguyên nhân KeyError `trang_thai`, chưa xác nhận.
  - Thêm đối chứng trùng khóa cố ý cho 409 `IDEMPOTENCY_KHAC` với 0 delta, và replay đúng body cho cùng bằng chứng.
- Giữ nguyên: token ổn định cùng đồ thị, stale cho 409 0 delta, replay bất biến.

## 8. Mã lỗi mới / đổi

- **409:** `L11_KHOA_GOC_THIEU`, `L11_DO_LUONG_KHONG_HIEN_HANH`, `L11_BANG_CHUNG_HANG_NGOAI_MIEN`, `L11_CLOSURE_MO_RONG` (đã có; nay cả 11 đường nguồn có thể trả).
- **403:** `L11_CAP_KHAC_PHAP_NHAN`.
- **400:** `L11_HO_TRO_DON_VI_THIEU`, `L11_HO_TRO_DON_VI_KHONG_KHOP`, `L11_DON_VI_KHONG_CO`.
- **Issues HOLD:** `L11_COVERAGE_<giá trị>`, `L11_COVERAGE_HIEU_LUC_CHUA_DU`, `L11_LOI_BAO_CAO_NGUON`.
- **Mã sẵn có, nay dùng thêm:** `L11_DON_VI_CHUA_XAC_MINH` (thêm cho tỷ lệ/mã hóa), `L11_DON_VI_POOL_KHAC` (khai báo same-definition), `L11_TY_LE_SAI` (cùng định nghĩa ≠ 1/1), `L11_BANG_CHUNG_MA_HOA_KHONG_KHOP` (thêm ngữ cảnh).

## 9. Binding cần root xác nhận (không tự mở phạm vi)

1. **source_ordinal:**
   - Reader M5 lưu `source_ordinal` = chỉ số mảng 0-based (`/lines/{i}`), trong khi binding fixture ghi `source_ordinal: 1` cho dòng đầu.
   - Code so `binding = lw.source_ordinal + 1`, tức vị trí 1-based dẫn xuất từ ordinal gốc của reader, không dùng `stt`.
   - Nếu root định nghĩa khác thì chỉ cần sửa 2 vị trí trong `l11_danh_gia_noi_bo`.
2. **`DEMO_M2_UNIT_CAI_V1` (seed R15, `m2_demo.py` ngoài phạm vi) có `support_raw_sha256`/`support_locator` NULL:**
   - Với định nghĩa không khai hỗ trợ, bằng chứng trường thật là **chính dòng đã capture**: reader resolve đúng `unit_definition_ref` trong cùng ngữ cảnh và `unit_raw` bằng mã đơn vị.
   - Định nghĩa có khai hỗ trợ thì kiểm artifact/locator qua `l11_ho_tro_don_vi_noi_bo`.
   - Muốn ép hỗ trợ cho mọi định nghĩa thì cần sửa seed R15, việc này ngoài 14 tệp.
3. **Ref mapping kho** của miền bằng chứng hàng (`DEMO_MAP_A_V1`) được giả định bằng `reference_id` mapping kho do `m5_demo` seed; chưa chạy để xác nhận.
4. **Thứ tự hàng mapping trước gốc** (§3): lệch chữ so với handoff, giữ để tránh vòng khóa với đường cũ ngoài danh sách 11.

## 10. Kiểm soát còn thiếu (UNRUN / chưa viết)

- **Q09 race nhân quả:** chưa viết. Thiếu các ca: hai kết nối PG, `pg_blocking_pids`, watchdog; confirm đối đầu nguồn/map/review/tuyến/thu hồi; undo đối đầu confirm; multipool hai thứ tự thắng. Riêng `L11_CLOSURE_MO_RONG`/`L11_KHOA_GOC_THIEU` chỉ có đối chứng tĩnh và một âm ghi trực tiếp.
- **Q02 multipool:** chưa có ca tổng 9 (hai dòng hóa đơn chung một pool phiếu) và tổng 11.
- **Q05:** AA/ABA/ZIP chưa có test chạy.
- **Q04:** chưa có ca sức chứa 8/4, nguồn đảo, đổi profile/đơn vị.
- **Q07:** chưa có ca login ngưng hoạt động và kỳ khóa (không gỡ được nếu không DELETE).
- **R3/R4 âm** đổi field/unit/item/locator/ngữ cảnh/đo lường/source_ordinal với giữ raw: mới có ngoài miền và sai cặp; chưa đủ từng trường.
- **THUNG ngữ cảnh khác:** cần một cầu nối THUNG hợp lệ ở ngữ cảnh thứ hai được admit trước (không dùng lại ví dụ G01B đã rút). Chưa có dữ liệu cấu hình.
- **UI:** chưa có kiểm trình duyệt cho fence hai thứ tự đổi vai, coherence one-RR dưới commit của kết nối chủ thứ hai, và tải file thật. Test tài nguyên chỉ là chuỗi.
- **Nâng cấp 15→16 có dữ liệu L11:** không áp dụng, vì 16 chưa từng chạy trên DB đã nghiệm thu.
- **Test cũ sẽ đổi** (ngoài phạm vi, như report01): `test_m5_http.py:170–171` (501 thành 400 `L11_YEU_CAU_SAI`), `test_m2_migrations.py` (schema 15).

**Kết luận:** repair02 CODE_ONLY đã viết xong; mọi selftest UNRUN; không có nghiệm thu GUI/L11 đầy đủ/full33. Runtime thật do root phát hành riêng sau terminal + freeze + review.
