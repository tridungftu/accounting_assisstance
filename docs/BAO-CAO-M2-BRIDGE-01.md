# Báo cáo M2 BRIDGE01 R15 — CODE_ONLY

**19/10/2026 — CODE_ONLY / RUNTIME_UNRUN / CHƯA NGHIỆM THU.**

- **Phiên:** cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`.
- **Căn cứ:** `docs/GIAO-CODE-M2-BRIDGE-01.md` (pin `33c380ba…4f93`); binding M2/M5; pure DTO/profile; bridge fixture manifest `d65efac0…e9e7` (chỉ đọc).
- **Baseline:** root staged whole244 `158f957d…0ca0e6` (old240 + 28 pure fixture + 4 bridge fixture). Pure reader `fcccdd39…bc2` và test `2ee3bea9…becc` không sửa.

**Coder chỉ dùng Read/Glob/Grep/Edit/Write.**
- Không execute, import, compile hay test; không SQL/PG/Store/HTTP/GUI/CLI/process/network/Bash.
- Không đọc var/.env/credential/.git/source app/real rows/private evidence.
- Không xóa, move, drop, reset hay cleanup bất kỳ file/DB/role/attempt nào. Không git/pip/config/policy/shell.
- Không cài hay chạy migration/seed/bootstrap. Không đụng M9/tracker/loan.
- Fixture, golden và declarations chỉ đọc.

**Mọi kết quả là UNRUN.** Không có dòng nào trong báo cáo này là PASS.

## 1. Thay đổi (đúng 13 target)

| File | Loại | Nội dung |
|---|---|---|
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` | sửa | Thêm `M0015_M2_BRIDGE` vào cuối `PG_MIGRATIONS` (append-only); `PG_SCHEMA_VERSION` = 15. Prefix 1–14 và checksum giữ nguyên byte. Chi tiết ở §2. |
| `src/kho_tri_thuc/k2/nguon_chung.py` | sửa | Các thay đổi dùng chung:<br>• `doc_pham_vi` trả thêm `scope_kind`/`company_keys`;<br>• `artifacts(..., media_types)` hỗ trợ `allowed_media_types` theo vai trò;<br>• `phong_bi_capture` dựng scope INVOICE_SET (`scope_ref`, `scope_kind`, `company_keys`, `sections`);<br>• `ghi_stage(..., module=None)` ghi cột `module`.<br>Shape M5 không đổi. |
| `src/kho_tri_thuc/k2/quyen.py` | sửa | Thêm các hành động:<br>• `M2_READ`: KE_TOAN/KE_TOAN_TRUONG/CFO/XEM;<br>• `M2_MAP`, `M2_ROUTE`, `M2_SOURCE_REVIEW`: chỉ CFO, cần V4. |
| `src/kho_tri_thuc/k2/crm_khoi_dong.py` | sửa | `chuan_bi` gọi `m2_demo.khoi_tao(admin)` sau seed M5 và trả `"m2_seed"`. |
| `src/kho_tri_thuc/k2/m2_demo.py` | **mới** | Seed DEMO pin theo declarations/manifest:<br>• instance, profile, scope INVOICE_SET, định nghĩa đơn vị CAI;<br>• 2 mapping COMPANY ROOT_SEED;<br>• 8 actor, `phan_quyen` (chỉ M1/M2), `nang_luc_nguon`.<br>Actor chỉ được tạo **một lần**: khi mở lại, quyền hiện hành (kể cả quyền đã thu hồi) được giữ nguyên, không cấp lại, không chạm actor M5. Thêm `mau_danh_sach()`/`mau(rel)` (bytes đúng SHA manifest) và `dang_nhap_m2()`. |
| `src/kho_tri_thuc/k2/hoa_don.py` | **mới** | Service `HoaDonK2` (§3). |
| `src/kho_tri_thuc/giao_dien/server.py` | sửa | Section M2:<br>• `m2()` dùng kết nối chủ riêng qua `_m5_ket_noi_chu`;<br>• `m2_body` chặn khóa client-authority (`M2_CLIENT_AUTHORITY`);<br>• whitelist field theo từng thao tác;<br>• route GET `/api/m2`, `/api/m2/hoa-don/{id}`, `/api/m2/nguon/{r}`, `/api/m2/nguon/{r}/raw/{role}`;<br>• POST `danh-tinh`, `nhan`, `mapping`, `mapping-line`, `nguon/kiem-lai`, `route`, `lien-ket/*`;<br>• phân loại status: `M2_MA_409`, `M2_MA_403`, L11 → 501. |
| `src/kho_tri_thuc/giao_dien/assets/index.html` | sửa | Nav `#hoadonmua` và `section#page-hoadonmua` (vai, nhận mẫu/tệp NATIVE + CROSSWALK, danh sách nguồn, lọc, danh sách/chi tiết hóa đơn, mapping công ty). |
| `src/kho_tri_thuc/giao_dien/assets/app.js` | sửa | Khối M2 mỏng:<br>• `m2Epoch`/`m2FormEpoch`, khóa thao tác theo (actor, hóa đơn, op, target, graph);<br>• `m2Act` có form predicate;<br>• `m2Load`/`m2Render`/`m2Detail`: chọn nguồn, map dòng, tuyến, luôn gửi `expected_graph`;<br>• upload snapshot `File` trước `FileReader`. |
| `tests/test_m2_migrations.py` | **mới** | Static + PG cho M0015 (§4). |
| `tests/test_m2_k2.py` | **mới** | Service trên PG (§4). |
| `tests/test_m2_http.py` | **mới** | HTTP trong cùng shell (§4). |
| `docs/BAO-CAO-M2-BRIDGE-01.md` | **mới** | Báo cáo này. |

Không sửa report cũ, pure reader/test, fixture, M9 hay bất kỳ file ngoài 13 target.

## 2. M0015 (append 15)

### 2.1 Registry
- **`master.dinh_nghia_don_vi_luong`** (định nghĩa đơn vị): chỉ chủ bảng được ghi, chỉ INSERT.
- **`nguon_pham_vi`:**
  - thêm `scope_kind` (DEFAULT `KHO10_PHIEU`, nên M5 cũ không đổi) và `company_keys`;
  - `ma_kho`/`so_phieu` bỏ NOT NULL, có CHECK theo kind.
- **`nguon_profile`:** thêm UNIQUE(id, profile_sha256).

### 2.2 Stage COMMON và hàng nguồn
- **`stage_tin_cay.module`:** NULL cho M5, `M2` cho M2.
- **Consumer capture** được thay bằng CREATE OR REPLACE, cùng chữ ký:
  - kiểm module của stage khớp module của profile;
  - hỗ trợ `allowed_media_types`;
  - ghi `hash_basis`; khi có basis thì `row_raw_sha256` NULL.
- **`ban_ghi_nguon`:**
  - `row_raw_sha256` bỏ NOT NULL; thêm `hash_basis` (XML_DECODED_FIELD_STATES / ZIP_ENTRY_INVENTORY / CROSSWALK_METADATA) và `derived_record_sha256` do trigger CSDL tính.
  - Trigger `kho.ban_ghi_nguon_m2_kiem`:
    - profile M2 bắt buộc có basis; hàng có basis bắt buộc profile M2;
    - section phải khớp basis;
    - `row_raw.artifact_sha256` phải bằng SHA của vai trò NATIVE/CROSSWALK trong snapshot.
  - Không có row span giả. Ngữ nghĩa row JSON của M5 không đổi.

### 2.3 Core
- **CHECK module:** `chung_tu` nhận thêm `M2`; `tep_tach_phap_nhan` nhận M5/M2.
- **Owner trigger:** chứng từ HD_MUA chỉ thành M2 khi projector chủ bảng khai `module_nghiep_vu='M2'`; HD_MUA không khai vẫn là M1.
  - **Header M2:** tiền, tiền tệ, chiều, đối tác đều NULL; trạng thái `DANG_XU_LY`.
  - **Dòng M2:** Nợ/Có/đơn giá/thuế/TK/đích đều NULL, ghi tường minh, không dùng 0.
  - **Dòng không phải M5/M2:** vẫn bắt buộc no/co.
- **Receipt:** `bien_nhan_thao_tac` của M5/M2 chỉ chủ bảng được ghi.

### 2.4 Bảng M2
| Bảng | Vai trò |
|---|---|
| `kho.hoa_don_danh_tinh` | Định danh hóa đơn MUA_VAO và con trỏ latest/accepted/eligible. |
| `kho.hoa_don_phien_ban` | Phiên bản nội dung. Tiền ở mức minor NULL; `money_basis_state='UNPROVEN_NO_MINOR'`; có supersedes. |
| `kho.hoa_don_quan_sat` | Mỗi lần giao nhận một quan sát, FK về receipt/snapshot; bộ ZIP (container, ordinal, name); predecessor. |
| `kho.hoa_don_dong_danh_tinh` | Gốc dòng logic. |
| `kho.hoa_don_dong_phien_ban` | Cầu nối phiên bản ↔ dòng logic ↔ dòng core ↔ hàng nguồn ↔ mapping ↔ đơn vị. |
| `kho.mua_dich_dong` | Tuyến dòng. |

- View `kho.mua_dong_hien_hanh` dùng `security_invoker`.
- **Guard:**
  - chỉ chủ bảng ghi thêm;
  - supersedes phải trỏ về phiên bản trước;
  - con trỏ latest chỉ tiến về phía trước, accepted/eligible phải nhất quán;
  - đồ thị cầu nối phải có mapping đã duyệt và XML_LINE/digest khớp;
  - tuyến chỉ INSERT ở `DA_DUYET` + `hien_hanh`; chỉ được chuyển `hien_hanh`→false và `DA_DUYET`→`THAY_THE`.

### 2.5 Mapping `anh_xa_nguon`
- **Kind mới:** COMPANY, INVOICE_LINE.
- **Cột binding mới:** target hóa đơn/dòng logic; phiên bản, hàng nguồn, native/container/entry, locator/ordinal và tuple định danh của dòng.
- **Ràng buộc:**
  - CHECK target và FK;
  - module theo kind: WAREHOUSE→M5, còn lại→M2;
  - INVOICE_LINE không được là ROOT_SEED;
  - các cột mới bất biến.

### 2.6 Hàm
- **`kho.m2_tieu_thu_quan_sat(stage, H)`:** consumer typed.
  - MUA_VAO của đúng PN theo mapping COMPANY hiện hành → danh tính, phiên bản, core HD_MUA M2 kèm dòng NULL, quan sát, con trỏ, `tep_tach`.
  - **Phân loại:**
    - FIRST_OBSERVATION;
    - SAME_CONTENT_REPEAT: accepted chỉ tiến khi accepted cùng nội dung;
    - CHANGED_CONTENT_HOLD và ANCESTOR_REAPPEARANCE_HOLD: eligible = NULL, accepted giữ nguyên.
- **Finalizer:** thay bằng CREATE OR REPLACE.
  - Nhánh M2 tự dẫn xuất `items` từ CSDL và chỉ nhận `p_promote = {"module":"M2"}`.
  - Nhánh M5 giữ nguyên.
- **Token đồ thị:**
  - `kho.m2_co_so_noi_bo`/`kho.m2_co_so` cho CAS thao tác (gồm cả quan sát);
  - `kho.m2_basis_tuyen_noi_bo` cho basis ngữ nghĩa của tuyến (không gồm delivery).
- **`kho.m2_dong_nguon`:** trả các XML_LINE của quan sát mới nhất.
- **Thao tác CFO** (V4 + M2, kèm SOURCE_MAP khi map):
  - `kho.m2_xem_xet_nguon`;
  - `kho.m2_mapping_dong`;
  - `kho.m2_route` (tạo và duyệt trong một thao tác; tuyến cũ chuyển THAY_THE qua successor);
  - `kho.m2_mapping_cong_ty`.
- **Thứ tự khóa:**
  - thao tác nghiệp vụ: `BIEN_NHAN|pn|M2|op|key` → `HOA_DON_ROOT|id` → hàng danh tính FOR UPDATE;
  - consumer: `HOA_DON|pn|identity` → ROOT → hàng.
  - Quyền hiện hành được kiểm trước khi tra receipt. Request hash do CSDL dẫn xuất.

### 2.7 Grant và RLS
- REVOKE PUBLIC; bật RLS.
- `app_web` được SELECT theo policy PN + M2.
- `app_web` được EXECUTE các hàm M2 công khai, **trừ** `_noi_bo` và finalizer.
- Policy legacy của `chung_tu`/`chung_tu_dong` loại M5/M2 trừ khi có `ktt_duoc`.

## 3. Interface service `HoaDonK2`

`HoaDonK2(conn_app, root, *, conn_chu=None, chi_mo_phong=True, hom_nay=None)`

### 3.1 Nhận nguồn
**`nhan(actor, *, source_instance, scope_ref, coverage, reported_errors=VANG, client_key, native, artifact_name=None, crosswalk=None)`**
- Media xác định theo magic bytes `PK\x03\x04`, không theo tên tệp.
- Quyền INTAKE được kiểm trước replay. Cùng khóa + cùng H → trả kết quả cuối đã chốt. Khác H → `CAPTURE_KHAC_NOI_DUNG`, trước khi ghi blob/stage.
- Pure reader chạy theo **từng** công ty cấu hình (XOR theo từng key).
- **BAN_RA:** `SOURCE_CANDIDATE`, 0 M2/M3.
- **HOLD**, không tạo dòng typed/core khi gặp:
  - cả hai phía (`COMPANY_BOTH_SIDES`);
  - nhiều bên mua;
  - thiếu ngày/tiền tệ/nội dung;
  - mapping công ty vắng hoặc xung đột.
- Kết quả trả về: `artifact_kind`, `artifact_sha256`, `coverage_hieu_luc`, `native_fiscal_status:"UNKNOWN"`, `lan_tiep_nhan_id`, `capture_sha256`, `lap_lai`, `stage_id`, `snapshot_moi`, `promote{module, trang_thai, items[], candidates[]}`.

### 3.2 Đọc
- Phía nguồn (không cần PN, theo năng lực nguồn): `nguon_danh_sach`, `nguon_chi_tiet`, `nguon_raw` (cần READ_SOURCE), `nang_luc_cua_toi`, `pham_vi_cua_toi`.
- `danh_sach(actor, phap_nhan, ky, trang, co)` và `chi_tiet(actor, hoa_don_id)` dùng snapshot REPEATABLE READ READ ONLY.
- `chi_tiet` trả: `dinh_danh`, `con_tro`, `expected_graph`, `phien_ban`, `dong_core`, `quan_sat`, `dong_nguon_hien_hanh`, `dong_logic`, `cau_noi`, `tuyen`, `anh_xa_dong`, `duoc`, `l11`.

### 3.3 Thao tác
- `mapping_company(actor, {source_instance, company_key, phap_nhan, revision_hien_tai, ly_do, khoa})`
- `mapping_line(actor, *, client_key, hoa_don_id, expected_graph, source_row_id, logical_line_key, evidence_ref=None, reason)`:
  - `evidence_ref` chỉ là tham chiếu bằng chứng (`EVIDENCE_ONLY_NOT_APPROVAL`);
  - dòng nguồn phải là XML_LINE của quan sát mới nhất;
  - không chọn theo STT/MaHang.
- `xem_xet_nguon(actor, {hoa_don_id, observation_id, expected_graph, ly_do, khoa})`: chỉ quan sát mới nhất.
- `route(actor, {hoa_don_id, cau_noi_id, dich ∈ CHI_PHI|XDCB_241|TAI_SAN|KHO, expected_route_id, expected_graph, ly_do, khoa})`
- `lien_ket` → `M2_L11_CHUA_PHAT_HANH` (HTTP 501).

## 4. Test (đều UNRUN)

### 4.1 `tests/test_m2_migrations.py`
**Static:**
- append 15; pin prefix và lineage;
- SQL không chạm M9/tiền; định nghĩa đúng definer/revoke;
- thứ tự khóa;
- no/co NULL tường minh.

**PG:**
- fresh 0→15;
- nâng 14→15 giữ nguyên dòng HD_MUA M1 cũ;
- guard core M2;
- INVOICE_LINE seed bị từ chối;
- lịch sử legacy13 bị từ chối trước khi ghi.

### 4.2 `tests/test_m2_k2.py`
| Test | Nội dung |
|---|---|
| t01 | Seed một lần; mở lại cho 0 delta; quyền/năng lực/actor M5 không đổi; không M9. |
| t02–t07 | Workflow tối thiểu theo `workflow.json`, đúng 4 bước đếm:<br>• G01 capture không tự map;<br>• CFO map dòng `DEMO_LINE_G01_A`;<br>• CFO tuyến KHO;<br>• G03 ZIP: thêm 2 quan sát, ID ổn định, basis tuyến không đổi, token OP đổi. |
| t03 | Replay và 409 với 0 delta (DB và blob). |
| t04 | Từ chối trước mapping/tuyến:<br>• intake actor, CFO PN B, kế toán;<br>• SQL trực tiếp;<br>• token cũ;<br>• header forgery;<br>• tuyến khi chưa có cầu nối. |
| t08 | Successor/stale/không đổi đích; bất biến tuyến; dòng core không mang đích. |
| t09 | Vòng đời G04: changed/ancestor HOLD, review của CFO, PN B tách riêng, sale-A là candidate. |
| t10 | Intercompany tổng hợp (bytes G01 thay MST) và trường hợp cả hai phía. |
| t11 | Thiếu ngày → HOLD; đơn vị chưa có fact → giữ định danh, normalized NULL; không có bảng pool/L11. |
| t12 | Mơ hồ STT → 0 cầu nối; G05 reorder do CFO map tường minh → 2 gốc / 4 cầu nối. |
| t13 | Forgery qua app_web; ma trận đọc RLS; quyền raw/intake. |
| t14 | CROSSWALK chỉ là bằng chứng, 0 mapping. |
| t15 | Sentinel M5/M1 không đổi; no/co NULL; fiscal UNKNOWN. |

### 4.3 `tests/test_m2_http.py`
- 403 khi thiếu token; bộ chọn đúng 8 vai.
- Khóa client-authority → 403; field lạ → 400; base64 sai → 400 với 0 delta.
- Bytes thật đi trọn vòng; 409 với 0 delta.
- Raw cần READ_SOURCE.
- CFO map dòng và tuyến; token cũ → 409; stale → 409; L11 → 501.
- Viewer, PN B, M1-only.
- Kiểm có mặt các tài nguyên shell.

**Giả định chưa kiểm (sẽ lộ khi root chạy):**
- năng lực nguồn cụ thể của từng actor theo declarations (ví dụ KT_MUA_A không có READ_SOURCE);
- mã lỗi khi RLS ẩn hàng: `HOA_DON`, so với lỗi quyền (test chấp nhận cả hai);
- chuỗi `<NMua>/<NBan>` trong G01: test có `assertNotEqual` để fail sớm.

## 5. Blocker cụ thể (cần root quyết, ngoài 13 target)

1. **`tests/test_m0_m5_migrations.py` pin schema 14** (dòng 66, 73, 206, 207, 216, 332, 335, 345, 375). Với M0015, các assert `PG_SCHEMA_VERSION == 14`, `migrate == 14`, `kiem_lich_su == 14` và ca FUTURE_SCHEMA sẽ **fail**. File này không phải target nên không sửa. Root cần mở target riêng: đổi thành `PG_SCHEMA_VERSION`/15 hoặc `migrate(c, target=14)`.
2. **Pin cũ đã lệch từ trước R15:**
   - `tests/test_crm_k2.py:194` pin `(13, 13, 13)`;
   - `tests/test_m9_k2.py:72` pin `PG_SCHEMA_VERSION == 13`.
   Các pin này đã lệch từ R14 và không do R15 gây ra, nhưng vẫn fail. Không sửa vì không phải target và M9 thuộc phần cấm.

## 6. Giới hạn và lệch so với handoff (ghi rõ, không giả PASS)

- **HD_MUA M2:** chỉ thành M2 khi projector chủ bảng khai. HD_MUA legacy/M1 không đổi. Cách này giữ hành vi M1 và sentinel, nhưng hẹp hơn câu chữ "HD_MUA thuộc M2".
- **Consumer và finalizer:** được thay bằng CREATE OR REPLACE trong M0015, cùng chữ ký; nhánh M5 sao chép nguyên văn. Cần review diff SQL với M0013/M0014.
- **Không khóa kỳ (`khoa_ky`) cho M2 ở R15**, vì không có ghi nhận tài chính.
- **`definition_sha256` của đơn vị** không được tính lại trong CSDL; seed tự kiểm pin.
- **Coverage hiệu lực** là `PARTIAL_INPUT` khi ZIP partial hoặc coverage báo partial.
- **Tuyến** cần cầu nối trên phiên bản của quan sát mới nhất. Tuyến không phải duyệt tài chính/kho (`financial_or_inventory_approval:false`).
- **UI:** tải raw M2 dùng lại `m5Tai`, nên đi theo epoch M5. Epoch/form predicate cần root kiểm bằng trình duyệt; test HTTP chỉ kiểm có mặt chuỗi.
- **Ngoài phạm vi R15 (để R16):** quantity/pool/held/undo/proof, L11. Không có ghi nhận tài chính, thanh toán, BANK, stock engine hay M9.
- **Grant:** `kho.m2_tieu_thu_quan_sat` được grant EXECUTE cho `app_web` (cùng mẫu M5). Hàm vẫn tự kiểm stage do chủ bảng tạo, đúng actor và INTAKE hiện hành, nên gọi trực tiếp với stage lạ trả `STAGE_KHONG_HOP_LE`. Root review có thể cân nhắc thu hẹp grant này.

## 7. Việc của root
Chạy riêng các bước: terminal thật, freeze, review, runtime (3 file test mới cùng suite cũ), và xử lý blocker ở §5. Coder kết thúc phiên CLI tại đây.
