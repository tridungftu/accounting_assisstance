# BÁO CÁO L11 QUANTITY R16 — 01 (CODE_ONLY)

- Handoff: `docs/GIAO-CODE-L11-QUANTITY-01.md` (SHA pin ce65bd92…cb4a5), cases `docs/L11-QUANTITY-CASES-01.json` (SHA pin 6ab9e660…1c66f), fixture L11 20 tệp (manifest 22798080…081dd).
- Chế độ: **CODE_ONLY**. Không execute/import/compile/test/SQL/PG/HTTP/JS/browser/CLI/process/network. Không đọc var/.env/.git/credentials/sourceapps/real rows. Không delete/move/drop/reset tệp/DB/role.
- **Mọi test ở trạng thái UNRUN. Không có PASS nào được khẳng định.** Chưa có checksum/số statement M0016 thực đo — root đo sau khi freeze.

## 1. Tệp đã ghi (đúng 15 đích được phép)

| # | Tệp | Loại | Vị trí chính |
|---|-----|------|--------------|
| 1 | `src/kho_tri_thuc/ha_tang/pg_migrations.py` | sửa (append) | khối L11 `6502–8186`; `PG_MIGRATIONS` thêm `M0016_L11_QUANTITY` tại `8188`; `PG_SCHEMA_VERSION = len(PG_MIGRATIONS)` (= 16) tại `8202` |
| 2 | `src/kho_tri_thuc/k2/lien_ket_chung.py` | sửa | `L11_KHONG_NHAN`/`L11_LIEN_KET_TRUONG` `73–81`, `l11_so_luong_text` `85`, `l11_yeu_cau` `92`, `l11_goi` `113`, `luong_con_lai` `121` |
| 3 | `src/kho_tri_thuc/k2/kho_so_luong.py` | sửa | `tep_file_soat` nhánh `che_do == L11_QUANTITY` `729`; `_doc_json_bang_chung` `748`; `l11_nhan_bang_chung` `770`; `l11_bang_chung` `837`; `_l11_than` `848`; `l11_xac_nhan_bang_chung` `859`; `l11_huy_bang_chung` `866`; `l11_ma_hoa` `873`; `lien_ket` `882`; `l11_tong_quan` `893`; `l11_xuat_file` `937`; `_workbook_l11` `969`. `L11_THONG_BAO` dòng `43` giữ NGUYÊN (bytes workbook M5 cũ) |
| 4 | `src/kho_tri_thuc/k2/hoa_don.py` | sửa | `L11_THONG_BAO` `36`; `chi_tiet` thêm `l11_lien_ket` (`~575–585`, đọc qua RLS app, chỉ có hàng khi BOTH READ). `HoaDonK2.lien_ket` (M2 501) giữ nguyên `647` |
| 5 | `src/kho_tri_thuc/k2/quyen.py` | sửa | `L11_THAO_TAC` `53`; `kiem_l11` `103`; `duoc_l11` `118` |
| 6 | `src/kho_tri_thuc/k2/crm_khoi_dong.py` | sửa | import `l11_demo` `188`; `l11_demo.khoi_tao(admin)` `208`; trả `"l11_seed"` `222` |
| 7 | `src/kho_tri_thuc/k2/nguon_chung.py` | sửa | `doc_pham_vi` trả `phap_nhan_id` (docstring `61`); `phong_bi_capture` nhánh `L11_EVIDENCE_SET` `153–155` |
| 8 | `src/kho_tri_thuc/giao_dien/server.py` | sửa | `_m5_action`: `lien-ket/*` `554–555`, `l11/*` `556–557`; `_l11_action` `561–593`; `l11_state` `595–616`; `M5_MA_409`/`M5_MA_403` `739–752`; GET `/api/m5/l11` `957–961` |
| 9 | `src/kho_tri_thuc/giao_dien/assets/app.js` | sửa | khối L11 `1181–1412` (`l11Epoch/l11FormEpoch/l11Gen`, `l11Act`, `l11Tai`, `l11Render*`, `l11Load`, handler) |
| 10 | `src/kho_tri_thuc/giao_dien/assets/index.html` | sửa | nav `#lienketsoluong` `22`; `section#page-lienketsoluong` `158–177` |
| 11 | `src/kho_tri_thuc/k2/l11_demo.py` | MỚI (259 dòng) | seed DEMO cấu hình/raw + 2 actor |
| 12 | `tests/test_l11_migrations.py` | MỚI (≈211 dòng) | UNRUN |
| 13 | `tests/test_l11_k2.py` | MỚI (≈548 dòng) | UNRUN |
| 14 | `tests/test_l11_http.py` | MỚI (≈256 dòng) | UNRUN |
| 15 | `docs/BAO-CAO-L11-QUANTITY-01.md` | MỚI | báo cáo này |

Không chạm: M9/tracker/vay, sourceapps, fixtures/expected, báo cáo cũ, profile nguồn cũ, pure reader, migration 1–15.

## 2. Migration M0016_L11_QUANTITY (append-only)

- 1–15: literal và generated giữ nguyên ký tự. `M0016` là phần tử cuối. Finalizer `giao_tiep.nguon_chot_ket_qua` chỉ được `CREATE OR REPLACE` trong 16: `_CHOT_M16 = _CHOT_M15.replace(_CHOT_NEO, _CHOT_NHANH_L11 + _CHOT_NEO, 1)`, tức là chỉ chèn nhánh `s.du_lieu ? 'l11_proof'` (promote `{"module":"L11"}`) ngay trước nhánh M2. Có `assert _CHOT_M15.count(_CHOT_NEO) == 1`.
- **COMMON**:
  - `master.nguon_pham_vi` thêm cột `phap_nhan_id`. Bỏ `nguon_pham_vi_kind_m2_check`, thay bằng `nguon_pham_vi_kind_l11_check`, có thêm kind `L11_EVIDENCE_SET` (PN NOT NULL, sections = `['L11_PROOF_JSON']`).
  - `giao_tiep.stage_tin_cay`: thay `stage_tin_cay_muc_dich_check` bằng `stage_tin_cay_muc_dich_l11_check` (CAPTURE, FILE_SOAT, L11_PROOF, L11_FILE), thêm `stage_tin_cay_l11_pn_check`.
- **Parent dùng lại** `kho.lien_ket_chung_tu`:
  - Thêm UNIQUE(phap_nhan_id, id) và các cột `chu_so_huu_module`, `muc_dich_lien_ket`, `hoa_don_id`, `phieu_id`.
  - CHECK `lien_ket_l11_check`: M5/EVIDENCE/HD_PHIEU_KHO, tiền NULL, `lich_thu_id` NULL.
  - Trigger `lien_ket_l11_kiem`, với các lỗi:
    - `L11_CHA_BAT_BIEN`: parent L11 bất biến hoàn toàn, kể cả HUY chung.
    - `L11_CHA_CHI_CHU`: chỉ chủ bảng được ghi.
    - `L11_CHA_SAI_DO_THI`: cặp chứng từ phải là HD_MUA M2 ↔ PHIEU_KHO M5 đúng gốc typed.
    - `L11_LIEN_KET_CHUNG_GIA`: liên kết chung (chủ NULL) không được trỏ chứng từ core M2/M5.
- **Bảng mới** (RLS bật, REVOKE mọi vai, app_web chỉ SELECT với BOTH M2+M5; riêng `bang_chung_ung_vien` không cấp cho app):
  - `kho.bang_chung_ung_vien`: raw candidate, UNG_VIEN/HOLD + issues.
  - `kho.bang_chung_quy_doi_luong`: GOODS_EQUIVALENCE / CROSS_NATIVE_RATIO / NATIVE_ENCODING; `gcd(tu,mau)=1`; trạng thái DA_XAC_NHAN/DA_THU_HOI.
  - `kho.dich_so_luong`: pool L11, một pool cho mỗi gốc logic, đơn vị cố định.
  - `kho.ma_hoa_luong_nguon`: mã hóa bất biến, có `basis_revision`.
  - `kho.lien_ket_dong`: một biên nhận xác nhận = một child; UNIQUE(phap_nhan_id, xac_nhan_bien_nhan_id); CHO/DA_KHOP/HUY × CO_HIEU_LUC/CAN_SOAT; lượng numeric(38,12) > 0.
  - Guards: `kho.l11_chi_chu_ghi_them`, `kho.bang_chung_quy_doi_kiem`, `kho.lien_ket_dong_kiem` (chỉ cho chuyển CO_HIEU_LUC→CAN_SOAT và DA_KHOP→HUY; đồ thị child nhất quán khi chèn).
- **Hàm** (đều `SET search_path`; mọi hàm definer không phải trigger đều `REVOKE … FROM PUBLIC`):
  - Quyền: `kho.l11_quyen_noi_bo(pn, READ|LINK|CFO|FILE)`.
  - Primitive số: `kho.l11_uuid`, `kho.l11_so_nguon`, `kho.l11_so_ty_le`, `kho.l11_quy_doi`, `kho.l11_text`.
  - Khóa: `kho.l11_khoa_goc_noi_bo`, `kho.l11_khoa_pool_noi_bo`.
  - Ngân sách: `kho.luong_da_khop_noi_bo` (confirmed, held), `kho.l11_ngan_sach_noi_bo`, `kho.luong_con_lai` (scoped BOTH READ).
  - Bằng chứng: `kho.l11_tieu_thu_bang_chung`, `kho.l11_co_so_bang_chung_noi_bo`, `kho.l11_danh_sach_bang_chung`, `kho.l11_xac_nhan_bang_chung`, `kho.l11_huy_bang_chung`, `kho.l11_dong_dung_bang_chung_noi_bo`.
  - Mã hóa: `kho.l11_co_so_ma_hoa_noi_bo`, `kho.l11_co_so_ma_hoa`, `kho.l11_ma_hoa`.
  - Liên kết: `kho.l11_danh_gia_noi_bo`, `kho.l11_xem_truoc`, `kho.l11_ket_qua_dong_noi_bo`, `kho.l11_xac_nhan`, `kho.l11_huy`.
  - Giữ soát: `kho.l11_can_soat_noi_bo` cùng các trigger `hoa_don_l11_can_soat`, `phieu_kho_l11_can_soat`, `mua_dich_dong_l11_can_soat`, `anh_xa_nguon_l11_can_soat`.
  - FILE: `kho.l11_co_so_file_noi_bo`, `kho.l11_co_so_file` (kèm `token_dong`), `kho.l11_file_bat_dau`, `kho.l11_file_tieu_thu`.
- **Cấp quyền**:
  - EXECUTE cho app_web: `luong_con_lai`, `l11_danh_sach_bang_chung`, `l11_xac_nhan_bang_chung`, `l11_huy_bang_chung`, `l11_co_so_ma_hoa`, `l11_ma_hoa`, `l11_xem_truoc`, `l11_xac_nhan`, `l11_huy`, `l11_co_so_file`.
  - Hàm `*_noi_bo`, consumer stage và `l11_can_soat_noi_bo` không cấp cho app.
- **Policy thay trong 16**:
  - `lien_ket_chung_tu`: app_web thấy hàng L11 khi có BOTH, hàng cũ khi có M1, và chỉ ghi được nhánh chung; app_ke_toan/app_doc/app_cong_ai chỉ thấy `chu_so_huu_module IS NULL`.
  - `lo_xuat`: phân theo `che_do` — L11_QUANTITY cần BOTH; app không tự ghi được `che_do`.

## 3. Interface ứng dụng

**HTTP** (cùng token `X-KTT-Token`, cookie HttpOnly):

| Route | Gọi |
|---|---|
| GET `/api/m5/l11` | `LocalApp.l11_state` (tạo phiên; 2 login L11, picker, ứng viên nếu có READ_SOURCE) |
| POST `/api/m5/l11/danh-tinh` | chỉ `MO_PHONG_L11_LINK_A` / `MO_PHONG_L11_PROOF_CFO_A` (khác → 403 `DANH_TINH_L11`) |
| POST `/api/m5/l11/proof/nhan` | `KhoSoLuongK2.l11_nhan_bang_chung` (`source_instance, scope_ref, coverage, reported_errors?, khoa` + đúng một: `native_b64` hoặc `fixture_ref` ∈ `PROOF_FILES`) |
| POST `/api/m5/l11/proof/xac-nhan` | `l11_xac_nhan_bang_chung` (`candidate_id, expected_graph, khoa, ly_do`) |
| POST `/api/m5/l11/proof/huy` | `l11_huy_bang_chung` (`proof_id, expected_graph, khoa, ly_do`) |
| POST `/api/m5/l11/ma-hoa` | `l11_ma_hoa` (`side` M2/M5, `line_id`, `proof_id?`, `expected_graph`, `khoa`, `ly_do`) |
| POST `/api/m5/lien-ket/preview` | `lien_ket("preview")` → `kho.l11_xem_truoc` (0 ghi) |
| POST `/api/m5/lien-ket/xac-nhan` | `lien_ket("xac-nhan")` → `kho.l11_xac_nhan` |
| POST `/api/m5/lien-ket/huy` | `lien_ket("huy")` → `kho.l11_huy` (`child_id, expected_graph = token_dong[child], khoa, ly_do`) |
| POST `/api/m5/l11/file-soat` | `l11_xuat_file` (`lien_ket_id, co_so_truoc, khoa, ly_do`) |
| GET `/api/m5/file-soat/{lo}` | dùng chung; lô `che_do = L11_QUANTITY` cần `kiem_l11(FILE)` = BOTH READ + quyền file M5 |

Trình duyệt không được gửi `factor/he_so/tu_so/mau_so/ratio/kind/approved/PROVEN/phap_nhan(_id)/owner(_module)/pool_id/don_vi/so_luong_pool_*/trang_thai/hieu_luc/path/url/duong_dan` (403 `L11_CLIENT_AUTHORITY` hoặc `M5_CLIENT_AUTHORITY`). Lượng phải là chuỗi exact (400 `L11_SO_LUONG_SAI`).

**Mã lỗi:**

- **409** (`M5_MA_409`): `L11_VERSION_CHANGED`, `L11_CLOSURE_MO_RONG`, `L11_VUOT_SO_LUONG_HOA_DON`, `L11_VUOT_SO_LUONG_PHIEU`, `L11_TY_LE_XUNG_DOT`, `L11_BANG_CHUNG_DA_XAC_NHAN`, `L11_BANG_CHUNG_DA_THU_HOI`, `L11_BANG_CHUNG_HOLD`, `L11_DA_HUY`, `L11_MA_HOA_DA_CO`, `L11_POOL_HOA_DON_BI_CHAN`, `L11_POOL_PHIEU_BI_CHAN`, `L11_HOA_DON_KHONG_DU_DIEU_KIEN`, `L11_PHIEU_KHONG_DU_DIEU_KIEN`, `L11_TUYEN_KHONG_PHAI_KHO`, `L11_MAPPING_KHONG_HIEN_HANH`, `L11_DON_VI_POOL_KHAC`, `L11_MA_HOA_HOA_DON_KHONG_HIEN_HANH`, `L11_MA_HOA_PHIEU_KHONG_HIEN_HANH`, `L11_CHA_KHONG_PHAI_L11`, cùng `IDEMPOTENCY_KHAC`, `CAPTURE_KHAC_NOI_DUNG`, `KY_DA_KHOA`.
- **403** (`M5_MA_403`): `KHONG_CO_QUYEN_L11_LIEN_KET`, `KHONG_CO_QUYEN_L11_BANG_CHUNG`, `KHONG_CO_QUYEN_L11_MA_HOA`, `KHONG_CO_QUYEN_L11_FILE`, `KHONG_CO_QUYEN_L11_XEM`, `L11_CHI_CHU`, `L11_CHA_CHI_CHU`, `DANH_TINH_L11`, `L11_CLIENT_AUTHORITY`, `NGUON_KHONG_CO_QUYEN`.
- **400** (còn lại):
  - Yêu cầu sai: `L11_YEU_CAU_SAI`, `L11_SO_LUONG_SAI`, `L11_SAI_PHEP_NHAN`, `L11_KHONG_BIEU_DIEN_DUOC`.
  - Bằng chứng: `L11_BANG_CHUNG_HANG_THIEU`, `L11_BANG_CHUNG_HANG_KHONG_PHU`, `L11_BANG_CHUNG_TY_LE_THIEU`, `L11_BANG_CHUNG_TY_LE_KHAC_HANG`, `L11_BANG_CHUNG_TY_LE_KHONG_PHU`, `L11_BANG_CHUNG_HINH_DANG`, `L11_BANG_CHUNG_MA_HOA_KHONG_KHOP`, `L11_BANG_CHUNG_MA_HOA_THU_HOI`, `L11_THIEU_BANG_CHUNG_HANG`, `L11_THIEU_BANG_CHUNG_MA_HOA`.
  - Tỷ lệ và đơn vị: `L11_TY_LE_DON_VI_KHAC`, `L11_TY_LE_SAI`, `L11_TY_LE_CHUA_TOI_GIAN`, `L11_TY_LE_CUNG_DON_VI`, `L11_DON_VI_CHUA_DANG_KY`, `L11_DON_VI_CHUA_XAC_MINH`.
  - Mã hóa và nguồn: `L11_MA_HOA_KHONG_CAN_BANG_CHUNG`, `L11_SO_LUONG_NGUON_SAI`, `L11_PHAP_NHAN_KHAC`.
  - Cặp, phạm vi, profile: `L11_CAP_KHONG_TON_TAI`, `L11_CAP_KHAC_PHAP_NHAN`, `L11_PHAM_VI_SAI`, `L11_PROFILE_SAI`.
  - Mẫu và trigger: `L11_MAU`, `L11_FILE_KHONG_CO`, `L11_LIEN_KET_CHUNG_GIA`, `L11_CHA_BAT_BIEN`, `L11_CHA_SAI_DO_THI`.
  - Stage: `STAGE_KHONG_HOP_LE`, `STAGE_CHUA_CAPTURE`, `STAGE_KHONG_NHAT_QUAN`.

**K2 công khai mới**:

- `KhoSoLuongK2`: `l11_nhan_bang_chung`, `l11_bang_chung`, `l11_xac_nhan_bang_chung`, `l11_huy_bang_chung`, `l11_ma_hoa`, `lien_ket(dang_nhap, hanh_dong, yeu_cau)`, `l11_tong_quan`, `l11_xuat_file`.
- `quyen`: `kiem_l11(dt, loai, pn)`, `duoc_l11(dt, loai, pn)`.
- `lien_ket_chung`: `l11_yeu_cau`, `l11_goi`, `luong_con_lai`, `l11_so_luong_text`.
- `l11_demo`: `khoi_tao`, `doc`, `mau_bang_chung`, `mau_nguon`, `dang_nhap_l11`.

**Seed `l11_demo.khoi_tao`** (chỉ thêm, chạy một lần, kiểm xung đột):

- Instance, profile (payload literal, canonical SHA 3cc2d403…) và scope bằng chứng (PN_DEMO_A).
- 2 tài liệu khai báo đơn vị kèm catalog, 2 định nghĩa đơn vị với tuple đầy đủ (`DEMO_UNIT_CAI_A`, `DEMO_M2_UNIT_THUNG_R16_V1`).
- 1 ứng viên dòng THUNG.
- Scope/master catalog/khai báo đo lường cho phiếu tách sáu.
- 2 actor, chỉ ghi một lần (marker `demo_seed_l11_actor`); khi mở lại không cấp lại quyền.
- Không seed approval/pool/mã hóa/child.

## 4. Trạng thái nghiệm thu theo nhóm (tất cả UNRUN)

| Nhóm | Phủ trong test viết sẵn | Trạng thái |
|---|---|---|
| Q00 proof admission | `test_l11_k2.t01` (quyền INTAKE, HOLD, READ_SOURCE, CFO BOTH V4 + SOURCE_MAP, PROVEN/tu_so bị chặn, token cũ, tỷ lệ trước hàng, thứ tự 4 bằng chứng); `test_l11_migrations` (vector `l11_so_ty_le` "1.5"/Number/"0"/39 chữ số); `test_l11_http` | UNRUN |
| Q01 8/10 + replay | HTTP 8/8 + replay; K2 dùng 4/4 ×2 | UNRUN |
| Q02 hai ngân sách | `t03` (1 parent / 2 child, vượt pool phiếu 0 delta). **Chưa viết**: hai dòng hóa đơn chung một pool phiếu (tổng 9) và hai dòng phiếu chung một pool hóa đơn (tổng 11) | UNRUN / thiếu một phần |
| Q03 THUNG exact | `t07` (phiếu tách sáu 0.5↔6 ×2, sai phép nhân, đơn vị khác, cần bằng chứng mã hóa); `test_l11_migrations` (1/12 → NULL, 0.5×12 = 6). **Chưa viết**: K01 0.5↔6 (pool K01 đã dùng hết trong luồng tuần tự) | UNRUN / thiếu một phần |
| Q04 held | `t08` (đổi tuyến → CAN_SOAT giữ lượng, NULL + held 8), `t10` (thu hồi bằng chứng). **Chưa viết**: sức chứa 8/4, nguồn đảo, đổi profile/đơn vị | UNRUN / thiếu một phần |
| Q05 AA/ABA/ZIP | **chưa viết** (thiết kế: trigger `phieu_kho_l11_can_soat`/`hoa_don_l11_can_soat` khi eligible đổi; eligible NULL → ngân sách bị chặn) | UNRUN / không có test |
| Q06 forgery | `t04` (app INSERT/UPDATE child/parent/pool/bằng chứng/biên nhận, hàm nội bộ; chủ bảng sửa parent/child; liên kết chung giả; cặp/mã hóa/bằng chứng sai), `test_l11_migrations` (liên kết chung M1 thật vẫn chạy, M2 bị chặn) | UNRUN |
| Q07 quyền hiện hành | `t05` (M5-only, M2-only, CFO V4 không LINK, thu hồi trước replay rồi trả lại bằng UPDATE), FILE M5-only 403. **Chưa viết**: login ngưng hoạt động, kỳ khóa (cần `kho.khoa_ky` mà không gỡ được nếu không DELETE) | UNRUN / thiếu một phần |
| Q08 undo/file/reopen | `t06` (FILE + replay + tải lại theo quyền), `t09` (undo held, replay khóa cũ trả HUY, giải phóng đúng 4), `t11` (mở lại 0 delta) | UNRUN |
| Q09 race nhân quả | **không viết** — cần observer `pg_blocking_pids` và watchdog; root viết/chạy riêng | NOT IMPLEMENTED |

## 5. Lệch so với handoff / giới hạn (cần review)

1. **Giữ soát đồng bộ dùng AFTER trigger**, không `CREATE OR REPLACE` 11 entrypoint M2/M5 cũ. Có 4 trigger: `hoa_don_danh_tinh` (eligible/accepted đổi), `phieu_kho_danh_tinh` (tương tự), `mua_dich_dong` INSERT (tuyến kế tiếp không phải KHO), `master.anh_xa_nguon` UPDATE (mapping đóng). Trigger không tự lấy khóa gốc mà dựa vào việc mỗi entrypoint cũ đã giữ khóa gốc của phía mình. Handoff nói "precollect closure before tuple mutation" và "row trigger insufficient", nên đây là **lệch có chủ đích, cần root quyết định**. Chưa phủ: đổi profile/định nghĩa đơn vị không đi qua bốn bảng trên.
2. **Thứ tự khóa**: mọi `HOA_DON_ROOT|id` (sắp xếp) → mọi `PHIEU_KHO|inst|so` (sắp xếp) → hàng danh tính FOR SHARE → pool `FOR UPDATE` (sắp xếp) → bằng chứng FOR SHARE (`ORDER BY id`) → tuyến FOR SHARE. Entrypoint một phía cũ chỉ giữ khóa của phía mình. Chưa có bằng chứng runtime về deadlock (Q09).
3. **Parent** `tien_te` dùng DEFAULT của cột (VND, NOT NULL), `so_tien_khop_minor` NULL. Parent tìm theo cặp `chung_tu_a/b` HD_PHIEU_KHO chưa HUY. Nếu đã có liên kết chung không thuộc L11 → `L11_CHA_KHONG_PHAI_L11`.
4. **Tỷ lệ chéo** áp lên lượng pool: `pa × tu = pb × mau`.
5. **Binding phía kho**: so `source_ordinal` với `lw.stt`, `ID_Dong`, native SHA của vai `NATIVE_DETAIL` theo `first_snapshot_id`, `master_sha256`, `item_code`. **Không** so `measurement_payload_sha256`.
6. **Ngữ cảnh hỗ trợ đơn vị** kiểm theo profile/instance của snapshot (M2) hoặc phiên bản phiếu (M5); `support_raw_sha256` được kiểm qua `master.don_vi_khop_khai_bao`.
7. **Nhận bằng chứng** dùng hai stage trong một giao dịch chủ: CAPTURE (COMMON, `du_lieu.l11_proof = true`) rồi L11_PROOF. Consumer tự đối chiếu facts từ CSDL; stage lệch → `STAGE_KHONG_NHAT_QUAN`.
8. Giữ nguyên `L11_THONG_BAO` trong `kho_so_luong.py` để bytes workbook M5 cũ không đổi. `HoaDonK2.lien_ket` (M2 501) giữ nguyên.
9. `tests/test_l11_k2.py` dùng `UPDATE master.phan_quyen` để thu hồi rồi trả quyền (không DELETE). Kỳ khóa không được test vì không gỡ được nếu không DELETE.

## 6. Blocker / test cũ sẽ đổi kết quả (không sửa — ngoài 15 đích)

| Test cũ | Vị trí | Thay đổi |
|---|---|---|
| `tests/test_m5_http.py` | `170–171` | Kỳ vọng 501 `M5_L11_CHUA_PHAT_HANH` cho `/api/m5/lien-ket/preview` `{phieu_id}`; nay nhận **400 `L11_YEU_CAU_SAI`** (route đã phát hành) |
| `tests/test_m2_migrations.py` | `52`, `204–205`, `223` | Kỳ vọng `PG_SCHEMA_VERSION`/`migrate` = 15; nay là 16 |
| `tests/test_m0_m5_migrations.py` | `66`, `206–216`, `332`, `345`, `375` | Kỳ vọng 14 (đã stale từ trước) |
| `tests/test_m9_k2.py` | `72`, `107`, `123` | Kỳ vọng 13 (đã stale từ trước) |
| `test_crm_k2` | — | Stale 13 (đã có từ trước) |

Ngoài ra:

- Finalizer `giao_tiep.nguon_chot_ket_qua` được thay lần nữa trong 16. Test nào so ký tự finalizer trong DB với M15 sẽ thấy khác; nhánh M2/M5 cũ vẫn trùng ký tự.
- `crm_khoi_dong` nay seed thêm L11. Test kiểm khóa trả về của `khoi_dong` sẽ thấy thêm `l11_seed`.
- **Binding chưa xác minh bằng runtime**: chưa đo được số statement/checksum M0016. Các giả định cấu trúc (khóa JSON trong 4 proof, `field_states->'MHHDVu'`, `anh_chup_nguon_vai_tro` NATIVE_DETAIL, `phieu_kho_phien_ban.first_snapshot_id/master_raw_sha256`) dựa trên đọc source và fixture, chưa chạy.

## 7. Root cần chạy sau terminal + freeze + review

- `tests/test_l11_migrations.py`, `tests/test_l11_k2.py`, `tests/test_l11_http.py` (cần `KHO_PG_DSN_TEST`).
- Toàn suite để thấy các test cũ ở §6.
- Viết và chạy Q09.
- Kiểm UI trình duyệt trang `#lienketsoluong` (epoch, fence, tải file).

Kết luận: **CODE_ONLY hoàn tất, chưa chạy gì. Không có PASS.**
