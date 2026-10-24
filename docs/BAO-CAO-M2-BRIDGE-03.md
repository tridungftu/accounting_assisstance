# Báo cáo M2 BRIDGE repair03 R15 — CODE_ONLY

**19/10/2026 — CODE_ONLY / RUNTIME_UNRUN / CHƯA NGHIỆM THU.** Đây không phải self-test; không dòng nào là PASS.

- **Phiên:** cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`.
- **Căn cứ:** đã đọc toàn bộ `docs/GIAO-SUA-M2-BRIDGE-03.md` (pin `b4496c4f…12bf`) và `docs/REVIEW-M2-BRIDGE-ROOT-ACTUAL-02.md`.
- **Baseline:** repair02 frozen249 `4c81093f…7bab`.
- **Phạm vi:** chỉ sửa R4 (gắn đơn vị với tuple tài liệu khai báo) và tách oracle HTTP. R1/R2/R3/S1, server/UI, common, pure, fixtures, M5/M9, report01–02, review và handoff đều giữ nguyên.

**Coder chỉ dùng Read/Glob/Grep/Edit/Write.**
- Không execute/import/compile/test, không SQL/PG/HTTP/JS/browser/process/network.
- Không đọc var/.env/credential/sourceapp/realrows.
- Không xóa/move/drop/reset/cleanup.
- M0001–M0014 giữ nguyên literal/checksum/thứ tự. Chỉ sửa định nghĩa candidate M0015, dùng cho DB DEMO fresh mới. Không chạm DB15 hay bằng chứng cũ.

## 1. File và dòng (7 target)

| File | Dòng (sau sửa) | Nội dung |
|---|---|---|
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` | 4788–4836, 4840–4865, 4886–4971, 6206–6222, 6436–6449 | Xem §2. |
| `src/kho_tri_thuc/k2/hoa_don.py` | 145–197, 199–220, 308, 366–367 | `kiem_don_vi_khai_bao` (static, kiểm độc lập); `_don_vi(c, inst, profile) → (facts, mã HOLD)`; `ket_qua.don_vi_khai_bao`. |
| `src/kho_tri_thuc/k2/m2_demo.py` | 32–36, 111, 138–167 | Hằng `DECLARATIONS_REF` / `DECLARATIONS_BASIS` / `UNIT_DECLARATION_LOCATOR`; admit catalog + tài liệu + hàng đơn vị theo tuple; số đếm có thêm `tai_lieu`. |
| `tests/test_m2_migrations.py` | 1–8, 33–34, 122–136, 138–184, 219–226 | Xem §4. |
| `tests/test_m2_k2.py` | 1, 196–197, 583–717 | t01 thêm `tai_lieu`; bỏ "positive" R4 sai cũ; thêm `owner_tu_choi`, `INS_DV`, `dv`, `dem_don_vi`, `test_t17_…`, `_trong_savepoint`. |
| `tests/test_m2_http.py` | 188–203 | Tách hai negative route. |
| `docs/BAO-CAO-M2-BRIDGE-03.md` | — | Báo cáo này (mới). |

## 2. DDL và interface trong M0015 candidate

### 2.1 Catalog dùng chung (`master.nguon_master_noi_dung`, từ M0013)
Chỉ thêm `UNIQUE (reference_id, raw_sha256, byte_length)` (constraint `nguon_master_noi_dung_ref_sha_len_m2_uq`) để làm đích FK. Hàng cũ và trigger chỉ-thêm không đổi.

### 2.2 `master.tai_lieu_khai_bao_don_vi` (mới) — bytes thô của tài liệu khai báo đã admit
- **Cột:** `reference_id` PK, `raw_sha256` UNIQUE, `byte_length`, `noi_dung bytea`, `source_basis_ref` UNIQUE.
- **Ràng buộc:**
  - CHECK `octet_length = byte_length` và `sha256(bytes) = raw_sha256`;
  - FK `(reference_id, raw_sha256, byte_length)` → catalog.
- **Trigger `master.tai_lieu_khai_bao_kiem`:**

  | Mã | Điều kiện |
  |---|---|
  | `DON_VI_TAI_LIEU_BAT_BIEN` | không phải INSERT |
  | `DON_VI_TAI_LIEU_CHI_CHU` | không phải chủ bảng |
  | `DON_VI_TAI_LIEU_KHONG_CO_CATALOG` | chưa có trong catalog với đúng ref/SHA/độ dài |
  | `DON_VI_TAI_LIEU_SAI_HASH` | bytes không khớp SHA/độ dài |
  | `DON_VI_TAI_LIEU_CAN_CU_DA_DUNG` | căn cứ đã gắn với tài liệu khác |
  | `DON_VI_TAI_LIEU_CAN_CU_SAI` | căn cứ nêu một SHA256 khác SHA thật |
  | `DON_VI_TAI_LIEU_KHONG_DOC_DUOC` | không phải JSON object UTF-8 |

- RLS bật, không có policy cho app; REVOKE ALL khỏi app roles.

### 2.3 `master.dinh_nghia_don_vi_luong` (bảng của M0015) — thêm tuple khai báo
- **Cột mới:** `declaration_ref`, `declaration_raw_sha256`, `declaration_locator` (JSON pointer `^(/[A-Za-z0-9_]+)+$`), `support_source_instance_id` / `support_profile_ref` / `support_profile_sha256` (NOT NULL); tùy chọn `support_raw_sha256` + `support_locator` (all-or-none, hai trị).
- **FK:**
  - → tài liệu `(reference_id, raw_sha256)`;
  - → `nguon_profile`;
  - → catalog `(raw_sha256)`.
- **UNIQUE** `(declaration_ref, declaration_locator)`.

### 2.4 `master.don_vi_khop_khai_bao(payload, sha, ref, scope, decl_ref, decl_sha, locator, basis, inst, pref, psha) → text`
- SECURITY DEFINER, STABLE. REVOKE PUBLIC, không grant.
- Là **một** quy tắc dùng chung cho admission và consumer. Kỳ vọng lấy từ **bytes tài liệu**, không từ chính hàng đơn vị. Trả `NULL` khi khớp, ngược lại một trong các mã:

  | Mã | Điều kiện |
  |---|---|
  | `DON_VI_TAI_LIEU_KHONG_CO` | không có tài liệu |
  | `DON_VI_TAI_LIEU_SAI_HASH` | SHA/độ dài sai |
  | `DON_VI_TAI_LIEU_KHONG_DOC_DUOC` | tài liệu không đọc được |
  | `DON_VI_VI_TRI_KHONG_CO` | locator sai hoặc không có |
  | `DON_VI_KHONG_KHOP_TAI_LIEU` | subtree tại locator ≠ payload (so `master.json_chuan`), hoặc ref/scope khác |
  | `DON_VI_DIGEST_SAI` | tài liệu không khai `definition_payload_sha256` ở object cha, hoặc giá trị khai ≠ canonical tự tính / ≠ claimed |
  | `DON_VI_CAN_CU_SAI` | sai căn cứ (quy tắc bên dưới) |
  | `DON_VI_PHAM_VI_SAI` | instance/profile hỗ trợ khác cái tài liệu khai ở top-level (`source_instance` / `profile_ref` / `profile_payload_sha256`) |

- **Quy tắc căn cứ:** nếu object cha khai `source_basis_ref` thì basis phải bằng đúng chuỗi đó (cách để URN mờ chỉ được nhận khi gắn đúng). Ngược lại, basis phải bằng căn cứ đã gắn với tài liệu.
- Không hardcode `CAI` / `ONE` / `ROOT_SEED_DEMO`. Regex cú pháp cũ đã bị bỏ.

### 2.5 Admission và consumer
- **Trigger `master.dinh_nghia_don_vi_kiem`:** giữ `DON_VI_BAT_BIEN`, `DON_VI_CHI_CHU`, `DON_VI_DIGEST_SAI` (self) và `DON_VI_NGHIA_THIEU`; sau đó gọi hàm ở §2.4 và báo nguyên mã. Trường hợp "self-H đúng + tài liệu/căn cứ cũ + ref/nghĩa mới" bị chặn với `DON_VI_KHONG_KHOP_TAI_LIEU`.
- **Consumer `kho.m2_mapping_dong`:** sau kiểm ứng viên literal và **trước mọi ghi** (root/mapping/bridge/receipt/audit), nạp đơn vị theo `row_raw.unit_definition_ref` và gọi hàm ở §2.4. Thêm `DON_VI_NGOAI_PHAM_VI` nếu profile hỗ trợ ≠ instance/profile của snapshot. Phép kiểm digest cũ ở chỗ insert bridge đã bỏ (đã thay bằng kiểm ở trên).

## 3. Service và seed

- **`HoaDonK2.kiem_don_vi_khai_bao(unit, doc, inst, profile_ref, profile_sha) → str | None`:** cùng quy tắc với §2.4 nhưng chạy bằng Python, từ bytes tài liệu. Có thêm `DON_VI_NGHIA_THIEU` và `DON_VI_NGOAI_PHAM_VI`.
- **`_don_vi(c, inst, profile) → (facts, mã)`:**
  - không có hàng đơn vị → `DON_VI_CHUA_KHAI_BAO`;
  - lệch tuple → `facts = None`. Dòng giữ raw, số chuẩn hóa NULL / `UNIT_UNPROVEN`, không gán hệ số.
  - Kết quả nhận ghi `don_vi_khai_bao: {"state": "BOUND" | "HOLD", "reason": mã | null}`.
  - Thay đổi hành vi so với repair02: repair02 raise lỗi; nay HOLD có mã để không mất raw capture.
- **Seed `m2_demo`:**
  - đọc và kiểm pin `declarations.json` (4fe4…);
  - catalog: `DECLARATIONS_REF = "tests/fixtures/m2_bridge/declarations.json"`, đúng SHA và độ dài;
  - tài liệu: bytes thô, basis nguyên văn `ROOT_SEED_DEMO:declarations.json:4fe4cffd…e44f9`;
  - đơn vị `DEMO_M2_UNIT_CAI_V1`: payloadSHA 923a98…, locator `/shared_master_unit_definition/payload`, profile hỗ trợ `DEMO_M2_XML_INSTANCE_A` / profile 7e…;
  - thêm-only; hàng đã có mà khác tuple → `NGUON_SEED_XUNG_DOT`. Không seed approval/conversion/logical line; actor, quyền và 8 ứng viên literal giữ nguyên.

## 4. Test (tất cả UNRUN)

### 4.1 `tests/test_m2_migrations.py`
- Static:
  - `test_sql_m0015…` cập nhật: trigger đơn vị gọi hàm đối chiếu, không còn regex.
  - `test_sql_repair03_r4_tuple_khai_bao` mới: DDL tài liệu/catalog UNIQUE/FK, mã lỗi trigger, cột tuple, kỳ vọng lấy từ bytes, không hardcode đơn vị/prefix, consumer đứng trước mọi INSERT, REVOKE/không grant/RLS.
- PG: nâng 14→15 giữ nguyên hàng catalog cũ có từ schema 14.

### 4.2 `tests/test_m2_k2.py`
- `t01`: seed `tai_lieu` = 1; mở lại = 0.
- `t17`:
  - **Positive gốc:** tuple CAI khớp 4fe4 / 923a98 / locator / basis, và hàm DB trả NULL.
  - **10 negative owner** (rollback-only; mutation được nhận được ghi là VIOLATION):
    - claimed-H sai;
    - **self-H đúng + ref/nghĩa mới + tài liệu/căn cứ cũ**;
    - tài liệu không tồn tại;
    - SHA trông hợp lệ nhưng sai;
    - locator không tồn tại;
    - sai subtree;
    - đổi native;
    - đổi scope;
    - căn cứ không gắn tài liệu;
    - ngữ cảnh sai.
  - **Tamper** đơn vị / tài liệu / catalog.
  - **App role** INSERT bị từ chối.
  - **Positive nghĩa mới:** bằng **bytes tài liệu tổng hợp riêng** trong test, có căn cứ URN do tài liệu khai. Trong cùng giao dịch rollback có kèm các negative: tái dùng căn cứ cũ, căn cứ nêu SHA khác, dùng căn cứ tài liệu thay căn cứ khai, và nghĩa mới trên tài liệu cũ.
  - **Đối chiếu độc lập:** hàm DB và hàm dịch vụ trả đúng mã khi tuple bị sửa.
  - **Capture thật:** G01 có `BOUND` và `so_luong = 10`.
  - Đếm registry trước/sau = nhau. Không DELETE, không disable trigger.

### 4.3 `tests/test_m2_http.py`, dòng 188–203
1. Khóa mới + đồ thị cũ → đúng `(409, M2_VERSION_CHANGED)`.
2. Lấy đồ thị hiện hành từ chi tiết thật sau route đầu; khóa mới + `expected_route_id` NULL trong khi đã có tuyến KHO → đúng `(409, M2_ROUTE_STALE)`.

Mỗi ca có nền không rỗng và `dem()` không đổi. Route đầu, retry cùng body/token A trước và sau các negative vẫn trả 200 với `lap_lai: true`. Product/CAS không đổi.

## 5. Giới hạn và rủi ro (chưa kiểm runtime)

- **Hợp đồng tài liệu khai báo cho R16:** tài liệu phải là JSON object UTF-8; object cha của payload phải khai `definition_payload_sha256`; locator dạng JSON pointer chỉ gồm `[A-Za-z0-9_]`. Nếu tài liệu R16 dùng tên khóa khác, root cần tạo synthetic bytes theo hợp đồng này. Hàm sẽ fail closed (`DON_VI_DIGEST_SAI` / `DON_VI_VI_TRI_KHONG_CO`), không tự nới.
- **Tuple hỗ trợ raw native/master** (`support_raw_sha256` / `support_locator`): mới có cột, hình dạng và FK catalog. Chưa đối chiếu nội dung native/master vì R15 CAI không khai; R16 sẽ dùng.
- **Canonical:** `json_chuan` (DB) và `canonical_json` (Python) phải cho cùng chuỗi trên payload thật. t01/t17 sẽ chứng minh hoặc bác bỏ khi root chạy.
- **Đơn vị không khớp lúc capture:** nay là HOLD có mã, không raise. Consumer DB tại mapping dòng vẫn từ chối cứng.
- **Blocker cũ ngoài target, giữ nguyên:** test schema 14/13 trong `test_m0_m5_migrations.py`, `test_crm_k2.py`, `test_m9_k2.py`.
- **DB15 cũ (01/02)** có checksum M0015 khác; không mở, không viết lại.
- **Ngoài phạm vi:** R16/THUNG/proof/L11/BANK/331/journal/tài chính/thuế.

## 6. Việc của root
Chạy riêng terminal, freeze, review, rồi runtime trên DB DEMO fresh mới. Coder thoát CLI tại đây.
