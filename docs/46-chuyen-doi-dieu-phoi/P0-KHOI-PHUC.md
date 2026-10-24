# P0 — Khôi phục file chưa vào git (24/10/2026)

Nhánh `lat/p0` từ `hop-nhat-20261023` @ `a1da3d4`. Chỉ chép **nguyên file** từ bản chụp `var\codex-dieu-phoi\` (hoặc nhánh `luu/*`), không viết logic mới, không sửa `pg_migrations.py`, không đổi số migration.

**Kết quả:** `kho_tri_thuc.ha_tang.pg_migrations` nạp được (`len(PG_MIGRATIONS) = 25`: M0024 duyệt 02C, M0025 CRM G6A). Module có lỗi N1 (thiếu file) **29 → 1** (`test_m4_02c_pg`, để L0-2c). Test cả bộ (sqlite, 180 giây/module): ok **501 → 1067**, ERROR+FAIL 137 → 160 (lỗi tăng là lỗi **lộ ra** ở module trước đây không nạp được; không module nào nạp được trước đó có lỗi mới), skip 140 → 274, TREO 1 → 1 (`test_source6_g5_e5`, có sẵn).

**Cách chọn phiên bản:** mỗi file lấy từ frozen head của gói sở hữu (`TAN-DUNG-CODE.md`). Đã quét 131 bản chụp: trong frozen head của gói sở hữu **mỗi file chỉ có đúng một phiên bản**; bản khác (nếu có) chỉ nằm ở bản chụp cũ hơn của cùng gói. Kiểm: import + chạy test. Đã rà nội dung: chỉ dữ liệu DEMO (không tên công ty, MST, STK; số tiền là số tròn giả).

## File đã khôi phục (24)

| # | Đường dẫn | sha256(12) | Nguồn | Lý do chọn |
|---|---|---|---|---|
| 1 | `src/kho_tri_thuc/k2/crm_kiem_hd.py` | fdcf127d1d8c | `crm-g5-doi-chieu-20261023-01-code-frozen-3cb518064b79\files` | = head G6A `crm-g6a-20261022-01-code-frozen-7c9df8b14ad4`; bản 5a34f7… chỉ ở bản chụp G6A cũ ad57ea |
| 2 | `src/kho_tri_thuc/k2/sql_crm_kiem_hd.py` | 119cd881ea12 | như trên | = head G6A; khớp SHA ghim trong `test_crm_g6a_m25_integration`; pg_migrations M0025 import |
| 3 | `src/kho_tri_thuc/k2/crm_doi_chieu.py` | ecf859fd9b84 | như trên | head G5 (3cb518 mới nhất của gói); `crm_g.py` (L0-2d) gọi lười |
| 4 | `src/kho_tri_thuc/k2/sql_crm_doi_chieu.py` | 8d72a65f201d | như trên | head G5 |
| 5 | `src/kho_tri_thuc/m4/sql_duyet.py` | 7920155662eb | `git show luu/m4-02c-backend-20261022-01` | trùng byte bản chụp head 02C-backend cdb836 và 3cb518; pg_migrations M0024 import |
| 6 | `src/kho_tri_thuc/giao_dien/assets/crm_g.js` | 27a0d3db7f99 | head G5 3cb518 | dòng dõi chinh `cd36951` → G6A `c2dc96` → G5 `27a0d3db`; `git diff` với bản hop-nhat: **+678 / −0 dòng** (không mất hàm/route) |
| 7–9 | `tests/test_crm_kiem_hd.py`, `tests/test_crm_kiem_hd_http.py`, `tests/test_crm_doi_chieu_pg.py` | dbf607e8562e · 282a144156c5 · 0d06d49a1a00 | head G5 3cb518 | G6A: một phiên bản duy nhất; doi_chieu_pg: head G5 |
| 10–11 | `tests/crm_kiem_hd_async.cjs`, `tests/crm_doi_chieu_async.cjs` | 9aabbfc470d9 · 5c4c48376f0e | head G5 3cb518 | đi kèm test G6A/G5-B |
| 12 | `src/kho_tri_thuc/m4/request_api.py` | 3992272132b3 | head `m4-04a-request-backend-20261023-01-code-frozen-60589ad2fbd3` (chép từ head 04b 2902e8, trùng byte) | một phiên bản duy nhất; `m4/request_nhap.py`, `giao_dien/m4_request.py` import |
| 13 | `src/kho_tri_thuc/m4/sql_request_nhap.py` | 453ed0831839 | head 04a 60589a | bản 04c74a… chỉ ở bản chụp 04a cũ e6e840 |
| 14 | `src/kho_tri_thuc/m4/giao_dien/m4_request_nhap.js` | b3f56c992192 | head `m4-04b-request-wiring-...-2902e80fd63e` | một phiên bản; `giao_dien/m4.py`, `m4_request.py` tham chiếu |
| 15–17 | `tests/test_m4_request_fix01.py`, `_http.py`, `_pg.py` | aff4e89b3fcc · 1fd2061fc6a6 · e6e3e5b5a33b | head 04a 60589a | một phiên bản |
| 18–20 | `tests/test_m4_03a_pg.py`, `test_m4_03a_graph_guard_pg.py`, `_tinh.py` | 3ed522f2e91a · 4ef17484e7f9 · 4f3cb6bc6e34 | head `m4-03a-kt-backend-...-dccd810be387` | một phiên bản; `test_m4_03a_full_basis_pg`, `test_m4_03b_common_pg` import `test_m4_03a_pg` |
| 21–22 | `tests/test_m4_03a_http.py`, `test_m4_03a_gui_fix01_http.py` | bb2d605bc0c6 · 6dd3ddba23ee | head `m4-03a-gui-...-ff1677c7c157` | một phiên bản |
| 23 | `tests/m4_03a_async.cjs` | fcf93d9f2c7c | head 03a-gui ff1677 | `test_m4_03a_http` chạy nó; `m4_03a_gui_fix02_async.cjs` (đã có) ghim đúng SHA này. **Không có trong CSV L0-2i** |
| 24 | `tests/test_m4_02c_dto_ui.py` | 18c9ea8f87d6 | head `m4-02c-integration-repair-...-5b20eead36ad` | một phiên bản; `test_m4_04b_request_wiring_http` import |

## Không khôi phục
- **Nhóm `mua_tai_chinh_*`** (6 file, job `m4-financial-basis-a-20261023-01`): không file nào trên hop-nhat import. Job này là **03B02A "MUA financial basis phase"**: quy tắc kiểu `mua-phase-plan/v1` (duyệt/thu hồi CAS, nhật ký chỉ-thêm), sự kiện kinh tế trung tính + thành phần theo phase, `FinancialBasisV1` (nháp/xác nhận, HOLD) và hợp đồng đọc `SubjectV1` — 7 file mới, SQL `MUA_FINANCIAL_BASIS_SQL` **chưa đăng ký** registry. Trạng thái báo cáo: **WRITTEN_NOT_RUN** (chưa chạy test); phụ thuộc 03A + 03B common + fix01–03 đã migrate (nguồn: `workspace\docs\BAO-CAO-MUA-FINANCIAL-BASIS-PHASE.md`, `GIAO-CODE-MUA-FINANCIAL-BASIS-02.md`).
- `tools/source6_lazy_excel/master_hd.py` (Source6, ngoài phạm vi P0).
- `.cjs` bị L0-2i bỏ sót nhưng không ai chạy: `tests/m4_03a_gui_fix01_async.cjs`; `tests/m2_00a_source7_{fix01,job,manifest}.cjs` (M2, không có ở nhánh nào).

## Để L0-2c (gộp đầy đủ `m4-02c-backend` + `m4-04c-request-m27`) — không sửa ở P0
- `kiem_chung/fixtures_m4.py` thiếu `KET_LUAN_VND` (luu/m4-02c-backend có +29 dòng) → `test_m4_02c_pg` lỗi nạp; sau khi sửa N4 sẽ chặn tiếp `test_m4_03a_pg`, `test_m4_03a_graph_guard_pg`, `test_m4_request_pg` (đều import `test_m4_02c_pg`).
- `pg_migrations.py` chưa đăng ký **M0026** (KT 03A) và **M0027** (Request nháp): `test_m4_03a_m26_integration` 2 lỗi, `test_m4_request_tinh` 1 lỗi (cần ≥ 27 migration).
- `giao_dien/m4.py`, `m4/duyet_dot.py` khác bản `luu/m4-02c-backend` (~95 dòng mỗi file; hop-nhat có thêm nội dung của gói sau) — xung đột thật, gộp ba bên.
- `tests/m4_02c_fix01_async.cjs` chỉ có ở `luu/m4-02c-ui-fix01-20261022-01`; `m4_02c_dto_ui_async.cjs` gọi nó.

## Test trước / sau theo nhóm (ERROR+FAIL)

| Nhóm | Trước (a1da3d4) | Sau (lat/p0) | Ghi chú |
|---|---:|---:|---|
| N1 thiếu file / đăng ký của gói chưa gộp | 45 (29 module) | 4 (3 module) | còn lại để L0-2c (mục trên) |
| N2 thiếu psycopg | 45 | 82 | +37 lộ ra: test G6A/G5-B ghi FAIL `NOT_VERIFIED` thay vì skip |
| N3 fixture bị .gitignore + CRLF | 26 | 38 | +12 lộ ra: ghim SHA/byte đầu `pg_migrations.py` tính trên LF; bản xuất LF (`git -c core.autocrlf=false archive`) đạt các ca này |
| N4 điều kiện ngoài runner (`from tests…`) | 14 | 20 | 13 module lỗi `No module named 'tests'` (5 module mới khôi phục, 2 chuyển từ N1) |
| N5 test lỗi thời | 7 | 16 | +9 lộ ra: đếm migration cứng (25 ≠ 14/15/16/18/20), "chỉ append sau M00xx"; **trùng đúng `ids_loi` của nền `chinh`** |
| Cộng | 137 | 160 | ok 501 → 1067 |

Lệnh: `python -X utf8 tools\chay_test_theo_module.py . --ra <file.json>`; so `ids_loi` với `nen-test-hop-nhat.json` và `nen-test-chinh.json`.
