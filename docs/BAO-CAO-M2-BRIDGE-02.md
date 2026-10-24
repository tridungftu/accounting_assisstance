# Báo cáo M2 BRIDGE repair02 R15 — CODE_ONLY

**19/10/2026 — CODE_ONLY / RUNTIME_UNRUN / CHƯA NGHIỆM THU.** Báo cáo này không phải self-test. Không có dòng nào là PASS.

- **Phiên:** cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`.
- **Căn cứ:** `docs/GIAO-SUA-M2-BRIDGE-02.md` (pin `0ad88e77…8c09`), đã đọc toàn bộ. Cùng handoff gốc `GIAO-CODE-M2-BRIDGE-01.md`, các review `REVIEW-M2-BRIDGE-MIGRATION-01`, `-TESTS-01`, `-ROOT-PROBE-01`, `-HTTP-UI-01/02/03`, declarations/manifest/line-facts đã pin.
- **Baseline:** whole249 frozen `e515b4ef…f033c`.
- Report01, các review, handoff, pure reader/test, fixtures, M9 và M5 cũ (ngoài helper dùng chung) **không sửa**.

**Coder chỉ dùng Read/Glob/Grep/Edit/Write.**
- Không execute/import/compile/test, không SQL/PG/HTTP/JS/browser/CLI/process/network/Bash.
- Không đọc var/.env/credential/.git/sourceapp/realrows.
- Không xóa/move/drop/reset/cleanup file/DB/role/attempt.
- Không chạy migration/seed. Không chạm DB15 cũ hay bằng chứng lịch sử.

## 1. File đã sửa (trong 13 target)

| File | Thay đổi |
|---|---|
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` | Chỉ sửa **định nghĩa candidate M0015** (dùng cho DB DEMO fresh mới). Literal/checksum M0001–M0014 không đổi (mọi edit nằm trong khối `M0015_M2_BRIDGE`; một edit trùng chuỗi với M0014 đã được tách bằng ngữ cảnh riêng của M0015). Chi tiết ở §2. |
| `src/kho_tri_thuc/k2/hoa_don.py` | Thêm `TAI_LEN_TOI_DA_BYTE = 700_000` và kiểm `M2_TEP_QUA_LON`.<br>`_don_vi` kiểm lại digest canonical, reference/scope và trường nghĩa (`DON_VI_DIGEST_SAI`).<br>`chi_tiet` trả thêm `ung_vien_dong`.<br>`mapping_line(..., evidence_ref, evidence_revision, reason)`: hai tham số bằng chứng nay **bắt buộc**. |
| `src/kho_tri_thuc/k2/m2_demo.py` | `doc_ung_vien_dong()` đọc `line-facts.json` qua manifest và declarations đã pin. Seed admit đúng 8 hàng vào `master.m2_ung_vien_dong`: chỉ thêm, xung đột thì `NGUON_SEED_XUNG_DOT`. Số đếm có thêm `ung_vien_dong`. Actor/quyền vẫn một lần, không regrant. |
| `src/kho_tri_thuc/giao_dien/server.py` | **F3:** `_crm_db` nhận mã dạng `[A-Z][A-Z0-9_]*` neo hai đầu, tối đa 80 ký tự; text khác → `CSDL_TU_CHOI`.<br>Whitelist `mapping-line` thêm `evidence_revision`.<br>State `/api/m2` có `gioi_han_tai_len_byte`.<br>Thân JSON vượt giới hạn trên `/api/m2/*` → `M2_TEP_QUA_LON`; `M2_TEP_QUA_LON` trả HTTP 413. |
| `src/kho_tri_thuc/giao_dien/assets/app.js` | **F1:** `m2Tai(receipt, role)` kiểm điều kiện hiện hành: `m2Epoch`, actor, và lần nhận còn `doc_raw` trong state. Kiểm cả trước khi tải lẫn trước khi hiện lỗi. `m5Tai` giữ nguyên.<br>**F2:** thêm `m2DocGen` và `m2CtGen`; chỉ phản hồi của GET bắt đầu sau cùng được vẽ hoặc báo lỗi.<br>**R2:** nút CFO map dòng chỉ chọn trong `ung_vien_dong` của đúng dòng; mặc định là "— chọn —", không tự lấy ứng viên đầu. Gửi `evidence_ref` + `evidence_revision` + dòng logic của ứng viên. Không có ứng viên, hoặc nhiều dòng logic → hiển thị HOLD.<br>**Upload:** kiểm `size` trước khi đọc tệp. |
| `src/kho_tri_thuc/giao_dien/assets/index.html` | Thêm `#m2-tl-gioi-han`: công bố giới hạn mỗi lần nhận. |
| `tests/test_m2_migrations.py` | Đổi assertion thứ tự R1; thêm `test_sql_repair02_r2_r3_r4_s1`. ROOT_SEED: setup ngoài `assertRaises`, kiểm đúng mã `ANH_XA_SEED_SAI` của chính INSERT và 0 delta. |
| `tests/test_m2_k2.py` | Sửa theo hợp đồng (§4). |
| `tests/test_m2_http.py` | Sửa theo hợp đồng; thêm lớp `PhanLoaiMaCsdl` không cần DB. |
| `docs/BAO-CAO-M2-BRIDGE-02.md` | Báo cáo này (mới). |

`nguon_chung.py`, `quyen.py`, `crm_khoi_dong.py` không cần sửa: `crm_khoi_dong` vẫn gọi `m2_demo.khoi_tao` và trả `m2_seed`.

## 2. M0015 candidate — đối tượng và lỗi mới hoặc đổi

### 2.1 R1 — exact retry và quyền hiện hành
Ba hàm `kho.m2_xem_xet_nguon`, `kho.m2_mapping_dong`, `kho.m2_route` nay chạy theo thứ tự:
1. Quyền hiện hành (M2 + CFO V4; mapping cần thêm SOURCE_MAP đúng PN).
2. Kiểm input.
3. Khóa `BIEN_NHAN|pn|M2|op|key` → `HOA_DON_ROOT|id` → hàng `FOR UPDATE`.
4. Dựng H từ **body gốc**, tra biên nhận cùng PN/module/operation/key:
   - cùng H → trả nguyên `result_json` + `lap_lai:true`;
   - khác H → `IDEMPOTENCY_KHAC`.
5. Chỉ khi là yêu cầu mới: CAS `expected_graph` dưới khóa (`M2_VERSION_CHANGED`).

Thu hồi quyền thì bị từ chối trước khi tra biên nhận. `kho.m2_mapping_cong_ty` giữ ngữ nghĩa cũ; replay retarget kiểm thêm quyền hiện hành trên PN cũ đã đóng (`ANH_XA_KHONG_CO_QUYEN`).

### 2.2 R2 — ứng viên literal được bind tại DB
- **`master.m2_ung_vien_dong`**: chỉ là raw candidate evidence, không phải registry duyệt.
  - Cột seed ghi: `payload` / `fact_sha256` / `source_document_ref` / `source_document_sha256`. Các cột còn lại (`mapping_ref`, revision, instance/profile/scope, company/PN, native SHA+len, bộ ZIP, identity, locator/ordinal, logical key) do trigger **dẫn xuất từ payload**.
  - Trigger `master.m2_ung_vien_dong_kiem`:
    - chỉ chủ bảng (`M2_UNG_VIEN_CHI_CHU`), chỉ thêm (`M2_UNG_VIEN_BAT_BIEN`);
    - digest canonical (`M2_UNG_VIEN_DIGEST`);
    - kiểu trường; scope INVOICE_SET chứa company key; identity là MUA_VAO của PN khai (`M2_UNG_VIEN_HINH_DANG`).
  - CHECK hai trị cho bộ ZIP và identity 6 phần. UNIQUE(mapping_ref, revision). RLS bật, app không có policy.
- **`kho.m2_ung_vien_khop_noi_bo(fact, row, obs)`** — nội bộ, không grant: một quy tắc đối chiếu duy nhất, trả `NULL` hoặc mã lỗi.

  | Mã | Đối chiếu |
  |---|---|
  | `M2_UNG_VIEN_SAI_NGUON` | instance/profile SHA/scope của lần nhận |
  | `M2_UNG_VIEN_SAI_PHAP_NHAN` | company key → PN theo mapping công ty của quan sát |
  | `M2_UNG_VIEN_SAI_ARTIFACT` | native SHA + độ dài thực; container SHA + độ dài vai trò NATIVE + entry ordinal/name, hoặc tất cả NULL |
  | `M2_UNG_VIEN_SAI_DINH_DANH` | identity tự dẫn xuất |
  | `M2_UNG_VIEN_SAI_VI_TRI` | locator/ordinal |

- **`kho.m2_ung_vien_hien_hanh(hoa_don)`**: grant `app_web`. Có quyền M2 hiện hành thì trả `{source_row_id, evidence_ref, evidence_revision, logical_line_key, authority:"CANDIDATE_EVIDENCE_NOT_APPROVAL"}` cho các XML_LINE của quan sát mới nhất. Không trả raw bundle.
- **`kho.m2_mapping_dong`:**
  - `evidence_ref` + `evidence_revision` bắt buộc (`M2_YEU_CAU_SAI`) và nằm trong request H.
  - Với yêu cầu mới, sau kiểm dòng hiện hành: resolve ứng viên (`M2_UNG_VIEN_KHONG_CO`) → hàm khớp → `M2_UNG_VIEN_SAI_DONG_LOGIC`.
  - Tất cả xảy ra **trước** mọi INSERT root/mapping/bridge/receipt/audit.
  - Mapping ghi `line_ung_vien_id`; kết quả có `evidence_ref` / `evidence_revision` / `ung_vien_id`.
- **`master.anh_xa_nguon`:**
  - thêm `line_ung_vien_id` (FK);
  - trigger thêm lớp phòng thủ thứ hai `M2_UNG_VIEN_KHONG_KHOP`;
  - so sánh bất biến gồm cả cột mới.
- Capture ban đầu vẫn có 0 logical/bridge/map/route. Upload CROSSWALK không admit ứng viên.

### 2.3 R3 — core M2 bất biến
- `kho.m2_core_nguon_bat_bien()` với trigger `chung_tu_zz_m2_nguon_bat_bien` / `chung_tu_dong_zz_m2_nguon_bat_bien`, BEFORE UPDATE OR DELETE.
- Khi chứng từ (cũ) là M2: mọi DELETE và mọi UPDATE có `NEW IS DISTINCT FROM OLD` → `M2_NGUON_BAT_BIEN`, **kể cả chủ bảng**.
- Tên `zz` để trigger chạy sau cùng, so trên NEW cuối cùng, kể cả `cap_nhat_luc` do trigger khác gán.
- M1/M5/CRM không đổi.

### 2.4 R4 — authority đơn vị
- `master.json_chuan(jsonb)`: canonical theo hợp đồng digest.
  - Khóa sắp theo `COLLATE "C"` (= code point), đệ quy; `,` `:` compact; giữ thứ tự mảng.
  - Số chỉ nhận số nguyên (`JSON_CHUAN_SO`, fail closed).
- `master.dinh_nghia_don_vi_kiem` thêm:
  - `DON_VI_DIGEST_SAI`: digest khai ≠ canonical của payload;
  - `DON_VI_NGHIA_THIEU`: thiếu reference/scope/native_unit_code/definition_kind/meaning/label/authority/version, hoặc không khớp cột;
  - `DON_VI_CAN_CU_SAI`: `source_basis_ref` không có dạng `<BASIS>:<tài liệu>:<sha256>`.
- `m2_mapping_dong` kiểm lại digest khi gắn đơn vị vào bridge. Không có hệ số mặc định. Payload CAI `923a98…` và profile `7e…` không đổi.

### 2.5 S1 — CHECK hai trị
CHECK quan sát (bộ ZIP), CHECK `anh_xa_nguon_target_m2_check` (thêm `line_ung_vien_id`) và CHECK của bảng ứng viên đều dùng `coalesce(…, false)` kèm `IS NOT NULL` từng cột. XML: tất cả NULL; ZIP: tất cả có mặt, hash/ordinal/tên hợp lệ; identity 6 phần không NULL/rỗng.

### 2.6 Grant
- REVOKE PUBLIC hai hàm mới.
- Grant `m2_ung_vien_hien_hanh` cho `app_web`.
- `master.m2_ung_vien_dong` nằm trong danh sách REVOKE ALL từ app roles.

## 3. Interface HTTP/UI

| Mục | Hành vi |
|---|---|
| `POST /api/m2/mapping-line` | Field cho phép: `hoa_don_id, expected_graph, source_row_id, logical_line_key, evidence_ref, evidence_revision, ly_do, khoa`. |
| Mã lỗi | Mã SQL M2 nay giữ nguyên: `M2_VERSION_CHANGED` → 409, `KHONG_CO_QUYEN_M2_*` → 403. `M2_UNG_VIEN_*` → 400. `M2_TEP_QUA_LON` → 413. |
| `GET /api/m2` | Có `gioi_han_tai_len_byte` (700000). |
| `GET /api/m2/hoa-don/{id}` | Có `ung_vien_dong`. |
| Giới hạn upload | Tổng NATIVE + CROSSWALK ≤ 700000 byte mỗi lần nhận. JSON 1 MiB chứa đủ base64 cộng các trường. Không tuyên bố hỗ trợ tệp lớn. |

## 4. Test (đều UNRUN)

### 4.1 `tests/test_m2_migrations.py`
- R1 static: quyền → khóa → biên nhận → `lap_lai` → CAS → INSERT biên nhận.
- R2 static: các check nằm trước mọi INSERT; revision nằm trong H; không grant hàm nội bộ.
- R3 static: có nhánh DELETE, không có ngoại lệ chủ bảng.
- R4 static: dùng `json_chuan`, có COLLATE "C".
- S1 static: `coalesce`/`IS NOT NULL`.
- PG ROOT_SEED: đúng mã, 0 delta.

### 4.2 `tests/test_m2_k2.py`
| Test | Nội dung |
|---|---|
| t01 | 8 ứng viên, digest DB = digest Python, 0 INVOICE_LINE; unit digest DB = pin. |
| t02 | `ung_vien_dong` của dòng G01 = fact01 + fact02. |
| t04 | 7 negative R2 qua service **và** gọi trực tiếp definer: unknown ref, alias kiểu oracle, sai revision, fact05→G01, fact03→XML trần, logical tùy ý, logical của hóa đơn khác. Thiếu bằng chứng → `M2_YEU_CAU_SAI`. Delta phụ = 0. |
| t05 / t06 / t09 | Retry nguyên body/token A: bằng nhau trừ `lap_lai`; khác H → 409; delta phụ = 0. Áp dụng cho mapping / route / source-review. |
| t07 | Sau ZIP, ứng viên chỉ còn fact04; retry mapping sau delivery mới vẫn trả kết quả cũ. |
| t08 | Owner UPDATE so_luong / mo_ta / du_lieu / ngày / hash / payload / khoa_nguon → `M2_NGUON_BAT_BIEN`. App role bị từ chối hoặc 0 hàng. Core snapshot trước = sau successor tuyến. |
| t09 / t14 | Classification đọc theo **mảng** DTO. |
| t12 | Hóa đơn STT mơ hồ có 0 ứng viên; G05 map qua ứng viên. |
| t16 | S1: 5 bộ ZIP thiếu một phần → CheckViolation, 0 delta. Ứng viên thiếu một phần / digest sai / UPDATE bị từ chối. R4: digest khai sai, căn cứ sai, thiếu nghĩa bị từ chối; positive đúng digest trong giao dịch `psycopg.Rollback`. |
| t99 | Còn quyền thì replay được; đổi `trang_thai` CFO A (UPDATE, không xóa) → `KHONG_CO_QUYEN_M2_MAP` / `DANH_TINH`, 0 delta. |

### 4.3 `tests/test_m2_http.py`
- Mapping dùng ứng viên do máy chủ lọc, giống GUI.
- 409 `M2_VERSION_CHANGED`; R2 negatives 400.
- Retry mapping/route 200 với `lap_lai:true`.
- 413 `M2_TEP_QUA_LON`.
- Shell có `m2Tai`, `m2DocGen`, `m2CtGen`, `evidence_revision`.
- `PhanLoaiMaCsdl`: mã M2/M5/legacy giữ nguyên; text riêng tư, chữ thường, bắt đầu bằng số, có dấu, rỗng, quá dài → `CSDL_TU_CHOI`.

## 5. Giới hạn, rủi ro và việc còn mở

- **Chưa chạy gì.** Các giả định chưa kiểm:
  - `master.json_chuan` cho ra đúng chuỗi như `canonical_json` Python. Hai cách đều escape `"`, `\`, ký tự điều khiển dạng `\u00xx` thường, và không escape non-ASCII; payload hiện có chỉ chứa chuỗi ASCII, số nguyên, bool, null. Root cần xác nhận trên DB thật: t01 so digest DB với pin `923a98…` và với digest của 8 fact.
  - Thứ tự trigger BEFORE trên `kho.chung_tu` theo tên.
  - Mã lỗi khi RLS ẩn hàng.
- **R3, nhánh DELETE:** chỉ kiểm tĩnh. Không chạy DELETE thử vì môi trường cấm xóa. Không disable trigger.
- **F1/F2:** chỉ có thay đổi code và kiểm chuỗi. Sáu oracle async độc lập của root (`REVIEW-…-HTTP-UI-03`) cần chạy lại trên bản freeze mới. Chưa có bằng chứng GUI/browser.
- **F3 / JSON > 1 MiB:** nhánh dịch `FILE_TOO_LARGE` → `M2_TEP_QUA_LON` chưa có test HTTP. Server từ chối trước khi đọc thân, nên client có thể bị ngắt kết nối khi gửi; test HTTP chỉ kiểm nhánh dịch vụ (700001 byte < 1 MiB JSON).
- **Ứng viên PN_B:** không có, vì không có literal cho PN_DEMO_B. Hóa đơn intercompany B hiện HOLD ở UI (0 ứng viên), không map được. Đây là đúng hợp đồng, không tự tạo fact.
- **Blocker cũ, giữ nguyên, không tự sửa ngoài target:** `tests/test_m0_m5_migrations.py` hardcode schema 14; `tests/test_crm_k2.py:194` và `tests/test_m9_k2.py:72` hardcode 13.
- **DB15 cũ đã retain** được dựng từ định nghĩa M0015 trước repair02, nên checksum M0015 khác. Không mở hay sửa các DB đó; candidate mới chỉ dùng cho DB DEMO fresh khác. Theo hợp đồng, `kiem_lich_su` sẽ từ chối DB15 cũ (checksum 15 lạ).
- **Ngoài phạm vi (R16):** THUNG, proof, quantity, pools, L11, M9, tiền, BANK, stock engine.

## 6. Việc của root
Chạy riêng: actual terminal, freeze, review, rồi runtime trên DB DEMO fresh mới (migration / service / HTTP / async UI cùng 6 oracle). Coder thoát CLI tại đây.
