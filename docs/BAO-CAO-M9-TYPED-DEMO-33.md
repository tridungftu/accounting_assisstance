# BÁO CÁO M9 TYPED + COMMON M0/K2/K5/MONEY — DEMO (lượt 33)

Ngày 19/10/2026. Theo `docs/GIAO-CODE-M9-COMMON-K2-33.md`, `docs/ROOT-CHOT-BINDING-MODULE-33-20261019.md` (binding 28af9c1, proposal e3e9704f).
Người làm: Claude (coder). **Không tự nghiệm thu** — chờ Codex review độc lập/host. CHANGELOG/HANG-DOI/coverage do Codex giữ (không sửa).

## 0. Tóm tắt trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Migration M0013 (sau 12, không sửa 1–12) fresh + nâng cấp từ 12 có CRM DIRECT/HUY | Đã code, đã test PG (đạt) |
| Common M0/K1 intake/snapshot/row/mapping/derivative, registry tiền tệ, khóa identity công ty, interval, retarget impact | Đã code, đã test PG (đạt) |
| Typed M9 (HĐ/PB tái dùng, lich_tra_no mở rộng, loan/draw/rate/event/LC→SHORT, LOAN/DRAW, NULL≠0, nguyên tệ/VND, precision holding) | Đã code, đã test PG (đạt) |
| K5 dùng chung (action/owner discriminator, resolver typed, eligibility + digest toàn đồ thị, bất biến, prelock, RLS app_web) | Đã code, đã test PG (đạt) |
| Money L8 (parent CHILD + child, biên nhận, đích logic, remaining, proof encoding BANK, ngân sách chung CRM DIRECT + M9 CHILD, race) | Đã code, đã test PG (đạt) |
| API/UI/file trong shell hiện có (menu "Khoản vay") | API + file: đã test (HTTP thật trong test); UI: chỉ kiểm tĩnh — **GUI chưa kiểm** (không có công cụ trình duyệt) |
| Launcher | Không đổi (M9 dùng cùng kết nối/phiên CRM; nút mở migrate lên 13 qua `chuan_bi` hiện có) — host chưa chạy (Codex kiểm) |
| Full M9/33 (C4a–d, bảo lãnh, LC thanh toán, L7/L12, đầu tư) | Một phần — xem §6 gap |

## 1. Migration M0013 (`src/kho_tri_thuc/ha_tang/pg_migrations.py`)

M0001–M0012 và `_rls_v11` giữ nguyên (checksum được test so khớp). `PG_SCHEMA_VERSION = 13`. M0013 gồm (theo thứ tự):

- `SET LOCAL check_function_bodies = off`; schema `giao_tiep`.
- **Registry tiền tệ** `master.don_vi_tien` (VND scale 0, USD scale 2, căn cứ `DEMO_FIXTURE_CONTRACT`, có hash nội dung) — chỉ mô tả đơn vị, **không** làm proof cho BANK.
- **R1 discriminator**: `kho.chung_tu.module_nghiep_vu` (backfill `HOP_DONG_TEP→CRM`, còn lại `M1`; loại mới `HO_SO_VAY→M9`, phải trỏ HĐ VAY cùng PN; bất biến); `kho.kiem_chu_so_huu_noi_bo` (resolver allowlist typed); trigger việc K5 (`viec_chu_so_huu`) và lô xuất (`lo_xuat_chu_so_huu`) buộc module/PN của chủ thể; `lien_ket_chung_tu.link_purpose/allocation_model` do CSDL suy (MONEY/EVIDENCE/LEGACY_UNCLASSIFIED; DIRECT/CHILD), client khai sai → `LIEN_KET_PHAN_LOAI_SAI`.
- **M0/K1**: `giao_tiep.tep_tiep_nhan` (metadata raw toàn phần, chỉ integration — app_web không có quyền), `kho.anh_chup_nguon` (profile/hash/coverage/state/known time), `kho.ban_ghi_nguon` (PN nullable, gán một lần theo mapping), `master.dinh_danh_cong_ty_nguon` (khóa identity trước kiểm chồng lấn), `master.anh_xa_nguon` (COMPANY/BANK/PROJECT, revision, interval, chỉ đóng — không sửa/mở lại; CFO V4 + M9 của phiên), `giao_tiep.tep_tach_phap_nhan` (derivative theo PN, FK composite tới `kho.tep_goc`). Hàm definer `giao_tiep.ghi_anh_chup`, `gan_phap_nhan_theo_anh_xa`, `cong_ty_chua_map` (chỉ khóa công ty + số dòng, không raw).
- **Typed M9**: `master.vay_dinh_danh_nguon` (alias ổn định, không chứa financing kind/PN đích), `master.vay_phien_ban` (1:1 PB, LONG_TERM/SHORT_TERM/LC/GUARANTEE, currency+scale, nguyên tệ riêng, tỷ giá nguồn chỉ metadata, precision contract/status/fields, blockers, mapping pin), `master.khe_uoc_vay` + `master.khe_uoc_vay_phien_ban`, `master.lai_suat_vay`, `kho.su_kien_vay` + `kho.su_kien_vay_phan`, `kho.dich_phan_bo_tien` (đích logic ổn định `OBL:/DRAW:`), mở rộng **`master.lich_tra_no` hiện có** (`model_version LEGACY|M9_TYPED`, một nghĩa vụ/một cấu phần, LOAN/DRAW, NULL≠0; lịch cũ giữ nguyên, không ghi mới).
- Trigger ghi typed `master.m9_ghi_nhap_noi_bo`: chỉ INSERT vào PB `CHO_DUYET`, khóa HĐ trước, kế toán M9 của phiên, kiểm cha (OLD+NEW); UPDATE/DELETE → `M9_BAT_BIEN` (kể cả chủ CSDL). `phien_ban_cam_xoa`.
- **R2**: `m9_manifest_phien_ban_noi_bo` (M9_MANIFEST_V1, sort ổn định) → `m9_van_tay_noi_bo`; validator `m9_kiem_do_thi_noi_bo(pb, CHECK|APPROVE)`; wrapper app `m9_van_tay`, `m9_chan`, `m9_phien_ban_hieu_luc` (phạm vi M9). `phien_ban_kiem_duyet` dispatch theo `hop_dong.loai`: VAY → quyền KT/CFO + M9, digest toàn đồ thị khi kiểm và khi duyệt, đọc lại blocker khi duyệt; nhánh CRM giữ logic M0012. Wrapper `crm_phien_ban_hieu_luc/crm_van_tay_phien_ban` thay thế trong M0013 để không trả dữ liệu HĐ VAY qua đường CRM.
- **R4**: `kho.chung_tu_tien_encoding` (bất biến; HIEU_LUC duy nhất / bằng chứng bổ sung cùng digest), `kho.tien_digest_noi_bo`, verifier `kho.ghi_proof_tien_noi_bo` (chỉ chủ CSDL).
- **L8**: `kho.bien_nhan_thao_tac` (PN, module, operation, client_key + hash yêu cầu; actor = phiên), `kho.lien_ket_phan_bo` (child; đích logic + revision exactly-one; chỉ HUY có vết), ngân sách `kho.tien_da_phan_bo_noi_bo` (DIRECT + CHILD), `kho.dich_da_phan_bo_noi_bo`, sức chứa theo revision hiệu lực, wrapper `kho.tien_con_lai` (chặn `KHONG_CO_PROOF_TIEN / PROOF_TIEN_CHUA_CHUNG_MINH / PROOF_TIEN_LECH / LINK_TIEN_CHUA_PHAN_LOAI`) và `kho.dich_tien_con_lai`; constraint trigger DEFERRED kiểm tổng parent = Σ child, hủy parent phải hủy child, vượt đích (xuyên revision), vượt BANK (mọi module); `lien_ket_kiem` thay thế: nhánh CRM giữ nguyên nhưng ngân sách BANK dùng tổng chung; nhánh `VAY_TIEN` (BANK M1 ↔ HO_SO_VAY đúng HĐ VAY, phiên có M1 + M9).
- Quyền app_web: SELECT/INSERT typed, UPDATE chỉ `anh_xa_nguon` (đóng) và `lien_ket_phan_bo` (hủy); không quyền proof/identity/raw metadata; RLS v13 cho mọi bảng mới (cùng mẫu v11).

Sửa trong lượt khi test: policy RLS `kho.anh_chup_nguon` ban đầu dùng `id` không định danh (bị phân giải thành `b.id`) → đã sửa `anh_chup_nguon.id`.

## 2. Mã ứng dụng

| Tệp | Nội dung |
|---|---|
| `src/kho_tri_thuc/nguon/vay_9.py` | Adapter #9 v1 theo profile pin (native JSON v6 16 key, header set `3d4d00…`, bảng lãi xác nhận DEMO), precision theo field, khóa/trùng/mơ hồ, đồ thị typed theo alias. Sửa lượt này: mốc lãi mơ hồ cha (S16, không có công ty) chặn mọi HĐ có khế ước cùng mã thay vì bị lọc mất. |
| `src/kho_tri_thuc/kiem_chung/fixtures_m9.py` | Fixture DEMO tự dựng đúng shape + biến thể corpus; sao kê M9 DEMO cho M1. |
| `src/kho_tri_thuc/k2/vay.py` (mới) | `VayK2(CrmK2)`: nhận nguồn (raw content-addressed trước khi đọc), mapping CFO (+ impact/đóng), lập HĐ/PB theo PN nguyên tử (derivative, alias, typed, đích logic, việc V3/V4, nhật ký), xác nhận phạm vi lịch S05, kiểm/duyệt V3/V4/từ chối, chứng từ `HO_SO_VAY`, gợi ý nối (không ghi), xem trước/xác nhận (token preview, biên nhận idempotent, khóa HĐ→BANK)/gỡ cả liên kết, file soát XLSX (tiền dạng chữ), danh sách as-of/known-cutoff, danh mục gap. |
| `src/kho_tri_thuc/k2/lien_ket_chung.py` (mới) | Lớp liên kết dùng chung: hash yêu cầu, biên nhận, thứ tự khóa, đọc ngân sách BANK/đích; docstring map contract cho M2/M10. |
| `src/kho_tri_thuc/k2/quyen.py` | Hành động M9 (READ/INTAKE/STAGE/MAP_APPROVE/CHECK/APPROVE/APPROVE_V4/MATCH/MATCH_M1/EXPORT) + loại việc cần. |
| `src/kho_tri_thuc/k2/crm_demo.py` | Ngân hàng DEMO (ObjectID theo PN), module M9 cho KT/CFO DEMO, hai vai âm (`MO_PHONG_XEM_M9_A`, `MO_PHONG_KT_M9_KHONG_M1_A`). |
| `src/kho_tri_thuc/k2/crm.py` | CRM không liệt kê HĐ VAY; "đã nối" lấy từ ngân sách chung. |
| `src/kho_tri_thuc/k2/m1_demo.py` | `ghi_proof_tien`: verifier proof encoding (contract `V12_STORE_VND_SCALE0`) cho BANK chiếu từ M1, chạy bằng tài khoản chủ CSDL như bộ chiếu; không đổi số tiền. |
| `src/kho_tri_thuc/giao_dien/server.py` | `/api/m9` (GET, cùng cookie phiên CRM), `/api/m9/<thao tác>` (POST, cùng khóa thao tác), `/api/m9/file-soat/<id>`; tiền M9 qua M1 + bộ chiếu + proof; luồng tiền CRM cũng ghi proof sau bộ chiếu. |
| `src/kho_tri_thuc/giao_dien/assets/index.html`, `app.js` | Trang "Khoản vay": vai, xem theo ngày, nguồn/snapshot/lập hồ sơ, mapping (duyệt/ảnh hưởng/đóng), khoản vay (phiên bản, chặn, kiểm/duyệt/từ chối/V4, phạm vi lịch, khế ước, lãi suất, lịch, phát sinh, liên kết + gỡ), tiền M1 (gợi ý → xem trước → xác nhận), việc/file soát/khoảng trống. Chỉ `textContent`, tiền định dạng bằng chuỗi. |

API M9 (POST `/api/m9/…`): `danh-tinh, mau, anh-xa, anh-xa/anh-huong, anh-xa/dong, lap, pham-vi, kiem, duyet, duyet-v4, tu-choi, m1-sao-ke, goi-y, xem-truoc, xac-nhan, go, file-soat`. Danh tính/PN/trạng thái không nhận từ client (`CRM_CLIENT_IDENTITY`).

## 3. Yêu cầu → hiện thực → kiểm thử

| Yêu cầu (GIAO-CODE/binding) | Hiện thực | Test |
|---|---|---|
| Raw nhiều PN/chưa map không ép PN giả, không nới hash global | intake `giao_tiep` + row PN NULL; derivative theo PN | m01, m03, m04 |
| Profile/shape: thiếu key PARTIAL, key/version lạ/profile root REJECTED (giữ raw, không lập) | `vay_9.doc_native` + `SNAPSHOT_TU_CHOI` | m02, phan_tich |
| Mapping CFO V4+M9, chồng lấn bị chặn, đóng chỉ một chiều, impact retarget, alias PN cũ chặn ở PN mới | `anh_xa_nguon_kiem`, `anh_huong_anh_xa`, `CHAN_ALIAS_PHAP_NHAN_KHAC` | m03, m15 |
| Thiếu mapping/field vẫn nhận, giữ task, bổ sung xong thì promote/kiểm được | blocker + việc V3/V4; lập lại khi mapping có | m04, m11 |
| S01 hai draw cùng kỳ = hai nghĩa vụ; S06 lịch sử lãi; NULL≠0; nguyên tệ/VND riêng | typed + đích logic | m04 |
| Replay cùng nội dung không tạo revision giả | `source_revision_sha256` | m04 |
| LC→SHORT cùng identity, không hai HĐ | alias theo (instance, section, công ty, khóa) | m10 |
| S05 LOAN+DRAW chờ xác nhận phạm vi, thao tác bổ sung có vết | `xac_nhan_pham_vi` | m11 |
| Precision UNPROVEN/S10, xung đột S04, mơ hồ S16 → holding; S09 text exact > 2^53 giữ đủ | validator + blockers | m12, phan_tich |
| Quyền hành động/module/PN, RLS, KT không duyệt, CFO không kiểm, V4 tách V3 | `quyen` + trigger CSDL | m01, m05, m06, m07 |
| Digest toàn đồ thị: đổi đồ thị sau kiểm → duyệt bị chặn | `phien_ban_kiem_duyet` (VAY) | m06 |
| Bất biến typed (không ghi vào bản đã duyệt, không sửa/xóa), không xóa PB | trigger | m05 |
| Discriminator chủ sở hữu (chứng từ/việc/lô), domain dispatch CRM↔VAY | R1 | m05 |
| Proof BANK: không proof → chặn; proof bất biến; sửa số sau proof → chặn | R4 | m07 |
| Parent CHILD + child, biên nhận (cùng khóa cùng nội dung → cũ; khác → 409; quyền trước replay), preview cũ → chặn, gỡ cả parent | L8 | m07 |
| Ngân sách BANK chung CRM DIRECT + M9 CHILD, race hai domain | `kiem_tong_lien_ket_noi_bo`, `lien_ket_kiem` | m08 |
| Tiêu thụ đích logic xuyên revision | `dich_suc_chua_noi_bo` theo revision hiệu lực | m09 |
| Tiền trước – nguồn sau và ngược lại | PN_B tiền trước; PN_A nguồn trước | m06, m07 |
| BANK từ M1 hiện có, không tạo SAO_KE/112 | `m1_demo.nhan_sao_ke` + bộ chiếu | m06–m08 |
| File soát lossless (ô chữ), tải về đúng hash, quyền | `xuat_file_soat` | m13, m14 |
| HTTP cùng phiên/cookie/token, không nhận danh tính client | server | m14 |
| Nhật ký chỉ ghi thêm | `nhat_ky.su_kien` | m16 |
| Nâng cấp từ 12 giữ dữ liệu/checksum, phân loại link cũ, lịch cũ giữ khóa | M0013 | M9MigrationTest m02 |

## 4. Kết quả chạy (tách pass/fail/setup/error/skip/unrun)

PostgreSQL qua runner retained (`python -X utf8 var/codex-dieu-phoi/run-pg-tests-retained.py …`, guard bật, DB giữ lại):

| Bộ | Run | Pass | Fail | Error | Skip | Evidence |
|---|---|---|---|---|---|---|
| `test_m9_k2.py` | 18 | 18 | 0 | 0 | 0 | `pg-retained-20261019-105216-bb567383` |
| `test_crm_k2.py` (hồi quy CRM trên 13) | 23 | 22 | 0 | 0 | 1 (t17: máy test không có `app_ke_toan`) | `pg-retained-20261019-105238-5931bcee` |
| `test_pg_schema.py` | 18 | 16 | 1 | 0 | 1 (t15: không có `app_ke_toan`) | `pg-retained-20261019-105900-2a7f07d2` |
| `test_pg_bo_chuyen_schema10.py` | 1 | 1 | 0 | 0 | 0 | `pg-retained-20261019-105911-5b14be5b` |

- `test_pg_schema.test_t16_bo_chuyen_demo` **FAIL**: fixture của test ghi `core_hash = "0"*64`; bộ chiếu (từ vòng CRM trước) từ chối trước mọi ghi với `tu_choi: CORE_HASH_NGUON_TRUOC_GHI` (`sai: 6`). Không do M0013. Không sửa expected/fixture của test này.
- Nhánh race trong m08: mỗi lần chạy chỉ một nhánh (CRM thắng hoặc M9 thắng) được thực thi; lần chạy evidence trên đi nhánh nào không được ghi riêng. Cả hai nhánh có assert.

Không PG (`python -X utf8 -m unittest discover -s tests -p …`, `PYTHONDONTWRITEBYTECODE=1`):

| Bộ | Run | Kết quả |
|---|---|---|
| `test_m9_phan_tich.py` (adapter + kiểm tĩnh UI) | 10 | OK |
| `test_crm_*.py` | 78 | OK, 23 skip (các test PG khi chạy trực tiếp không có DSN — đã chạy qua runner ở trên) |
| Toàn bộ `test_*.py` | 446 | 2 FAIL, 74 skip |

- 2 FAIL ngoài phạm vi M9: `test_m1.test_backup_does_not_succeed_without_referenced_raw` (dựa vào `raw.unlink()` để tạo raw thiếu) và `test_web.test_scope_changes_receipt_not_raw_storage_size` (đếm thư mục raw, còn tệp tạm `.raw-*` mà `write_immutable` định `unlink`). Cả hai phụ thuộc thao tác xóa tệp — phù hợp với guard không-xóa đang bật; **chưa đối chứng baseline** nên ghi là "nghi do guard", không sửa.
- Sửa test lượt này: `test_crm_khoi_dong.py` (stub mã cứng schema 12 → `PG_SCHEMA_VERSION`), `test_crm_k2.py` (phiên bản schema động, từ vòng trước của lượt).

Unrun / chưa kiểm: GUI trình duyệt (không có công cụ), launcher/nút mở trên host, cold start, Windows PowerShell 5.1, DB DEMO thật của root (giữ ở 12, không đụng), Google readonly.

## 5. Ghi chú thiết kế/giới hạn cần Codex xem

1. Phiên bản typed duyệt có `valid_from = now()` (bản mới), bản cũ `valid_to = now()` — hiệu lực theo ngày nghiệp vụ qua `phien_ban_hieu_luc`; không có ngày hiệu lực nguồn cho revision #9.
2. Sự kiện PhatSinh không đổi nội dung không ghi lại ở phiên bản mới (revision chỉ tăng khi payload đổi); manifest mỗi PB chỉ chứa sự kiện mới/đổi ở PB đó.
3. Chứng từ `HO_SO_VAY` tạo khi CFO duyệt, ngày = ngày nguồn sớm nhất (giải ngân/nhận nợ/mở LC); không có ngày nguồn → không tạo, nối tiền chặn `HO_SO_VAY_CHUA_CO`.
4. Gỡ liên kết M9 chỉ gỡ cả parent (mọi child), không gỡ một phần child.
5. CRM DIRECT giữ kiểm số cũ (không cần proof) nhưng trừ chung ngân sách BANK; child M9 bắt buộc proof còn khớp.
6. Proof encoding chỉ cho BANK có `_sqlite_id` (chiếu từ kho M1 V12) và VND; contract `V12_STORE_VND_SCALE0` (amount_minor INTEGER, bộ chiếu ghi |amount| + chiều) — không lấy registry làm proof.
7. Gợi ý nối là đọc bằng chứng (PhatSinh cùng số chứng từ / khế ước cùng ngày-số), không phải policy phân bổ; người dùng phải xem trước + xác nhận.
8. `giao_tiep.cong_ty_chua_map` cho mọi người có M9 (KT/CFO) thấy khóa công ty nguồn chưa map (không raw, không PN) để CFO có ứng viên mapping — DEMO; cần quyết định nếu production yêu cầu hẹp hơn.
9. M0013 chưa phát hành: checksum chốt tại bàn giao này; các DB test retained của lần chạy trung gian mang checksum trung gian (không tái dùng).

## 6. Gap full M9/33 (work gate — không tạo schema/bảng rỗng)

Cũng hiển thị trong API/UI (`khoang_trong`):

| Nhánh | Trạng thái | Còn thiếu |
|---|---|---|
| C4d đầu tư/chứng khoán | WORK_GATE | register danh mục hiện hành có căn cứ; phân loại công cụ; hồ sơ nguồn (sổ CK/xác nhận số dư); chính sách định giá/dự phòng — chưa tạo schema chứng khoán/định giá |
| Đọc #9 trực tiếp (Google readonly) | GATE | deployment readonly đã pin; credential |
| Bảo lãnh (GUARANTEE) | WORK_GATE | shape nguồn; template phí/ký quỹ |
| LC thanh toán/ký quỹ | WORK_GATE | lịch ký quỹ/thanh toán; template |
| L7 lãi dự trả/accrual | HOLD_POLICY | daycount/cutoff đã duyệt; template ghi nhận — chỉ nhận bảng lãi đã xác nhận (DEMO) |
| FX/đánh giá lại nguyên tệ | HOLD_POLICY | chính sách tỷ giá |
| Vốn hóa lãi vay | HOLD_POLICY | chính sách vốn hóa theo dự án |
| Phân loại ngắn/dài hạn | HOLD_POLICY | quy tắc kết chuyển + TK |
| M10 ghi nhận/định khoản M9 | CONTRACT_ONLY | template/policy; khóa ghi nhận (PN, đích logic, loại sự kiện, kỳ) đã map trong `k2/lien_ket_chung.py` |
| HĐ mua/hạn mức tín dụng typed | RAW_ONLY | contract typed |
| Proof cho CRM DIRECT | GAP_DOCUMENTED | áp proof cho nhánh DIRECT |

## 7. Tuân thủ ràng buộc lượt

Không đọc var/.env/secrets/backups/dữ liệu thật; PG chỉ qua runner retained; không DROP/DELETE teardown, không xóa file/temp/DB/role; guard + `PYTHONDONTWRITEBYTECODE=1`; không chạy launcher/server host/Google/GUI; không commit; M0001–M0012 không sửa; không sửa CHANGELOG/HANG-DOI/coverage; không đổi expected của corpus độc lập.
