# NEN-TEST — nền test của `chinh` và `hop-nhat` (L0-1, 24/10/2026)

Nền để "xanh" = **không thêm lỗi so với bảng này**. Đo bằng `tools/chay_test_theo_module.py`: mỗi module test chạy trong tiến trình con riêng, giới hạn 180 giây/module, engine sqlite, không PostgreSQL, không đụng kho thật.

## 0b. Nền v2 — dùng từ 24/10 chiều (hop-nhat `7b114e2`, sau P0 + L0-3a)

Đo bằng `python -X utf8 tools/chay_test_theo_module.py <worktree> --runtime <repo chính>/var/web/crm-demo/runtime.local.json` trên worktree mới `nen-hop-nhat-v2` (checkout mới nên `.gitattributes` có hiệu lực). Dạng máy đọc: `nen-test-hop-nhat-v2.json`. **Lát mới so với nền v2**, không so với v1.

| | module | ok / ERROR / FAIL / skip | treo |
|---|---|---|---|
| chinh `59b7d8e` | 60 | 711 / 25 / 31 / 272 | 0 |
| hop-nhat v1 `1502fe7` | 80 | 501 / 112 / 20 / 140 | 1 |
| **hop-nhat v2 `7b114e2`** | **94** | **1276 / 34 / 57 / 292** | **1** (`test_source6_g5_e5`) |

So với `chinh` theo mã lỗi: chỉ 3 module có lỗi không có ở chinh — `test_crm_khoi_dong` (3, kết nối giả trong test thiếu `transaction`), `test_m0_m5_migrations` (2, đếm cứng số migration 25 ≠ 14), `test_m4_01c` (1, test giao diện cũ không ngờ có route `/api/m4/ke-toan`) — đều là test lỗi thời (N5) → lát L0-3c. Còn lại là module mới hoặc lỗi có sẵn ở chinh.

Module còn lỗi trên nền v2 (ok/ERROR/FAIL/skip):

| Module | Số | So với chinh | Lỗi đầu |
|---|---|---|---|
| `test_crm_41_02` | 27/0/2/0 | 0 mã lỗi không có ở chinh | AssertionError: 25 != 18 |
| `test_crm_doi_chieu_pg` | 0/0/16/0 | mới (không có ở chinh) | AssertionError: NOT_VERIFIED: thiếu biến môi trường KTT_G6A_CLONE_OWNER_DSN, KTT_G6A_CLONE |
| `test_crm_g6a_m25_integration` | 9/0/7/0 | mới (không có ở chinh) | AssertionError: NOT_VERIFIED: thiếu biến môi trường KTT_G6A_CLONE_OWNER_DSN, KTT_G6A_CLONE |
| `test_crm_giao_ket` | 50/0/1/2 | 0 mã lỗi không có ở chinh | AssertionError: False is not true : iem_hd import CRM_G6A_SQL  # noqa: E402 — module chỉ h |
| `test_crm_khoi_dong` | 32/3/0/0 | 3 mã lỗi không có ở chinh | AttributeError: '_KetNoiGia' object has no attribute 'transaction' |
| `test_crm_kiem_hd` | 22/0/4/0 | mới (không có ở chinh) | AssertionError: NOT_VERIFIED: thiếu biến môi trường KTT_G6A_CLONE_OWNER_DSN, KTT_G6A_CLONE |
| `test_crm_kiem_hd_http` | 8/0/10/0 | mới (không có ở chinh) | AssertionError: NOT_VERIFIED: thiếu biến môi trường KTT_G6A_CLONE_OWNER_DSN, KTT_G6A_CLONE |
| `test_crm_ky_ket` | 32/0/1/6 | 0 mã lỗi không có ở chinh | AssertionError: False is not true : iem_hd import CRM_G6A_SQL  # noqa: E402 — module chỉ h |
| `test_l11_k2` | 2/1/0/20 | 0 mã lỗi không có ở chinh | kho_tri_thuc.ha_tang.primitives.DataError: Manifest fixture L11 không khớp SHA đã pin. |
| `test_l11_migrations` | 11/0/1/2 | 0 mã lỗi không có ở chinh | AssertionError: 25 != 16 |
| `test_m0_m5_migrations` | 5/0/2/10 | 2 mã lỗi không có ở chinh | AssertionError: 25 != 14 |
| `test_m2_k2` | 0/1/0/0 | 0 mã lỗi không có ở chinh | AssertionError: workflow.json khác pin |
| `test_m2_migrations` | 3/0/1/3 | 0 mã lỗi không có ở chinh | AssertionError: 25 != 15 |
| `test_m4_01c` | 15/0/1/0 | 1 mã lỗi không có ở chinh | AssertionError: '/api/m4/ke-toan' unexpectedly found in '"use strict";\n// M4-01C — Cổng h |
| `test_m4_02b_pure` | 17/0/1/18 | 0 mã lỗi không có ở chinh | AssertionError: False is not true : iem_hd import CRM_G6A_SQL  # noqa: E402 — module chỉ h |
| `test_m4_02c_pg` | 0/1/0/0 | mới (không có ở chinh) | AttributeError: module 'kho_tri_thuc.kiem_chung.fixtures_m4' has no attribute 'KET_LUAN_VN |
| `test_m4_03a_full_basis_pg` | 0/1/0/0 | mới (không có ở chinh) | AttributeError: module 'kho_tri_thuc.kiem_chung.fixtures_m4' has no attribute 'KET_LUAN_VN |
| `test_m4_03a_graph_guard_pg` | 0/1/0/0 | mới (không có ở chinh) | AttributeError: module 'kho_tri_thuc.kiem_chung.fixtures_m4' has no attribute 'KET_LUAN_VN |
| `test_m4_03a_m26_integration` | 5/0/3/0 | mới (không có ở chinh) | AssertionError: Tuples differ: () != ('from ..m4.sql_ke_toan_nghiem_thu import [184 chars] |
| `test_m4_03a_pg` | 0/1/0/0 | mới (không có ở chinh) | AttributeError: module 'kho_tri_thuc.kiem_chung.fixtures_m4' has no attribute 'KET_LUAN_VN |
| `test_m4_03b_common_pg` | 0/1/0/0 | mới (không có ở chinh) | AttributeError: module 'kho_tri_thuc.kiem_chung.fixtures_m4' has no attribute 'KET_LUAN_VN |
| `test_m4_04b_request_wiring_http` | 3/13/0/0 | mới (không có ở chinh) | AttributeError: 'LocalApp' object has no attribute 'go_request_nhap' |
| `test_m4_master_dung_chung_http` | 0/1/0/0 | mới (không có ở chinh) | AttributeError: module 'kho_tri_thuc.kiem_chung.fixtures_m4' has no attribute 'KET_LUAN_VN |
| `test_m4_master_dung_chung_pg` | 0/1/0/0 | mới (không có ở chinh) | AttributeError: module 'kho_tri_thuc.kiem_chung.fixtures_m4' has no attribute 'KET_LUAN_VN |
| `test_m4_master_dung_chung_tinh` | 12/0/2/0 | mới (không có ở chinh) | AssertionError: 'm' not found in {'m4.master_can_cu_phien_ban', 'm4.master_can_cu'} : chỉ  |
| `test_m4_request_http` | 0/1/0/0 | mới (không có ở chinh) | AttributeError: module 'kho_tri_thuc.kiem_chung.fixtures_m4' has no attribute 'KET_LUAN_VN |
| `test_m4_request_pg` | 0/1/0/0 | mới (không có ở chinh) | AttributeError: module 'kho_tri_thuc.kiem_chung.fixtures_m4' has no attribute 'KET_LUAN_VN |
| `test_m4_request_tinh` | 55/0/1/0 | mới (không có ở chinh) | AssertionError: 973003 not greater than or equal to 973783 |
| `test_m4_review_compute` | 46/0/2/3 | 0 mã lỗi không có ở chinh | AssertionError: 25 != 20 |
| `test_source6_docx_tables` | 0/1/0/0 | mới (không có ở chinh) | RuntimeError: Thiếu KTT_SOURCE6_E3_OVERLAY (overlay đóng băng + hai artifact) — không skip |
| `test_source6_g5_e5` | 6/0/0/1 · TREO | mới (không có ở chinh) |  |
| `test_source6_lazy_excel` | 0/3/0/0 | mới (không có ở chinh) | RuntimeError: SETUP NOT_VERIFIED (baseline/bố cục): thư mục chứa tests/tools phải là 'file |
| `test_trich6_host` | 14/3/0/3 | 0 mã lỗi không có ở chinh | kho_tri_thuc.nguon.trich6_host.LoiHost: Guard giữ tệp của tiến trình central chưa đạt — kh |
| `test_trich_chung_6` | 31/0/1/1 | 0 mã lỗi không có ở chinh | AssertionError: 'LENH_RIENG = REVIEW_LENH / {"hop-dong/trich"}' not found in '"""M4-01 — H |
| `test_web` | 22/0/1/0 | 0 mã lỗi không có ở chinh | AssertionError: 1 != 2 |

## 0. Cách đo và số liệu chung

| | `chinh` | `hop-nhat` |
|---|---|---|
| Commit đã đo | `59b7d8e` (worktree `nen-chinh-59b7d8e`, detached) | `1502fe7` (nhánh `lat/l0-1` = `hop-nhat-20261023` + cấu hình lead) |
| Số module test | 60 | 80 (20 module chỉ có ở hop-nhat) |
| Thời gian chạy | 209 giây | 365 giây (lần 2: 352 giây, **kết quả y hệt lần 1** — không có module chập chờn) |
| ok / ERROR / FAIL / skip | 711 / 25 / 31 / 272 | 501 / 112 / 20 / 140 |
| Module TREO (> 180 giây) | 0 | **1** — `test_source6_g5_e5` |
| Số kết quả ghi được | 1039 | 773 (module lỗi nạp che mất test, xem N1) |

- Lệnh: `python -X utf8 tools/chay_test_theo_module.py <thư mục worktree> --ra <file.json>` (thêm `--module test_m1` để chạy riêng một module; có thể lặp `--module`, cho phép dấu `*`). Chạy hai bên **lần lượt**.
- Môi trường đo: Python 3.13.14 (`python` trên PATH), openpyxl 3.1.5, xlrd 2.0.2, **không có psycopg**; `PYTHONPATH=<repo>\src`, `-X utf8`; bỏ mọi biến `KHO_*`/`PG*` khỏi tiến trình con. Cách tìm test giống `test.ps1` → `tests/run_suite.py` (`tests/test_*.py`). Worktree sạch: không có `var/`, `TRI-THUC-CFO.json`, `cau_hinh.*.toml` và mọi file bị `.gitignore`.
- Nền dạng máy đọc: `nen-test-hop-nhat.json`, `nen-test-chinh.json` (cùng thư mục). Mỗi module: `ok, error, fail, skip, treo, giay` + `tong` (số test nạp được), `ids_loi` (id từng test lỗi — dùng để so "lỗi mới" chính xác khi số lỗi không đổi), `loi_dau` (dòng ngoại lệ đầu tiên), `test_treo`. Module không có trong file = chưa tồn tại ở nền (mọi lỗi của nó là lỗi mới).
- Gợi ý luật cổng test: với mỗi module worker chạm tới, `set(ids_loi mới) ⊆ set(ids_loi nền)`, `treo` không tăng, và module nạp được ở nền thì không được thành lỗi nạp (`tong` không tụt về 1).
- Quy ước ô trong bảng: `ok/ERROR/FAIL/skip`. ERROR 1 và ok 0 ở module có nhiều test = **lỗi nạp module** (che toàn bộ test của module).

### Đối chiếu với H4 (275 ERROR)
H4 chạy cả bộ trong một tiến trình ở kho chính: 206 ok / 275 ERROR / 4 FAIL / 140 skip rồi treo. **Không tái hiện được** trong worktree sạch: chạy từng module, hay chạy cả bộ một tiến trình (trừ module treo, 77 giây), đều ra cùng số (hop-nhat: 112 ERROR / 20 FAIL / 140 skip — số skip trùng H4); năm module chủ chốt chạy lại bằng Python 3.12 (bản đi kèm Codex) cũng cho cùng kết quả. `test_m1` (H4: 52 ERROR), `test_modules` (48), `test_nghiem_thu_bridge` (21), `test_m2_00b_tien_trinh` (32) đều **đạt** ở đây; riêng M2-00B quyền/tính lỗi vì thiếu psycopg (37). Nghi phần chênh do trạng thái kho chính lúc chạy H4 (có `var/`, tiến trình Codex chạy song song giữ khóa file) — chưa xác định vì log H4 không có traceback (tiến trình bị ngắt). Coi nền ở đây là nền cho worker; không dùng số H4.

### Module treo
- `test_source6_g5_e5` (chỉ có ở hop-nhat), test `E5ClientIoMockTests.test_raw_khac_yeu_cau_khong_nhan`: 6 test đầu đạt, rồi test này chạy mãi (CPU 100%, ngăn xếp dừng ở `json.decoder.raw_decode` — vòng lặp bận, không phải chờ I/O). Đúng chỗ H4 đứng. 22 test còn lại của module không chạy tới. Lỗi mã/test, không do môi trường; lát sửa: nhóm Source6 trong L0-3 (hoặc ghi `skip` có lý do cho tới khi sửa).

## 1. Năm nhóm nguyên nhân gốc

Số lỗi = ERROR + FAIL (FAIL tính theo từng subtest, như `run_suite.py`).

| # | Nhóm | Loại | Lỗi hop-nhat | Lỗi chinh | Module (hop-nhat) |
|---|---|---|---|---|---|
| N1 | Thiếu file của gói chưa gộp → `import` hỏng | **CODE** | 43 | 0 | 28 |
| N2 | Python chạy test không có `psycopg` | môi trường | 43 | 6 | 5 |
| N3 | Worktree khác kho chính: fixture `.xml/.zip` bị `.gitignore` + CRLF làm lệch SHA | môi trường | 26 | 31 | 4 |
| N4 | Test đòi điều kiện ngoài repo/ngoài runner | môi trường (runner) | 13 | 5 | 9 |
| N5 | Test lỗi thời hoặc lệch với code (và 1 module treo) | code/test | 7 (+1 treo) | 14 | 6 |
| | **Cộng** | | **132** | **56** | |

**N1 — thiếu file của gói chưa gộp (CODE, chỉ ở hop-nhat).** `ha_tang/pg_migrations.py` (dòng 11781 và 11791) import `m4/sql_duyet.py` và `k2/sql_crm_kiem_hd.py`; không có hai file này trong cây hop-nhat nên mọi module nạp `ha_tang.postgres`/`pg_migrations` đều chết khi `import` (kể cả `test_m1`). Đối chiếu: **25 module** lỗi đúng vì `sql_duyet` (39 lỗi + `test_m1` qua `ha_tang.postgres`); trong đó **20 module không chạy được test nào** — 14 module có ở `chinh` (ở đó chạy được 375 test, 222 ok) và 6 module mới. 5 module còn lại chạy một phần (`test_m4_master_dung_chung_tinh`, `test_trich_chung_6`, `test_v13_backup_safety`, `test_v13_doi_chieu`, `test_m1`). Bù `sql_duyet` chưa đủ: dòng 11791 sẽ dừng tiếp ở `sql_crm_kiem_hd`. Vị trí các file thiếu (đã đối chiếu mọi nhánh local):
- `m4/sql_duyet.py`, `fixtures_m4.KET_LUAN_VND` → có ở `luu/m4-02c-backend-20261022-01`. **Lát sửa: L0-2c** (đã trong hàng đợi).
- `k2/sql_crm_kiem_hd.py`, `tests/test_crm_kiem_hd.py`, `tests/test_crm_kiem_hd_http.py` → **không có ở nhánh nào**; chỉ có ngoài git, trong `var\codex-dieu-phoi\crm-g5-doi-chieu-20261023-01-code-frozen-{3cb518064b79,c77f4bbb9daf,dd4ef3638d78}\files\` (các thư mục này cũng chứa `m4/sql_duyet.py`). **Lát sửa: L0-2d** (chép bản đúng vào git; lead chọn thư mục freeze nào là bản cuối).
- `m4/request_api.py` (`test_m4_request_fix02` lỗi trực tiếp; `m4/request_nhap.py` và `giao_dien/m4_request.py` đã gộp cũng import nó) → **không có ở nhánh nào**; chỉ có trong `var\codex-dieu-phoi\isolated-head-jobs\m4-04a-request-backend-20261023-01\workspace\src\kho_tri_thuc\m4\` (và các workspace m4-04b/04c sau đó). **Lát sửa: L0-2c** (chuỗi `m4-04c-request-m27`) hoặc lát riêng đưa file vào git.
- Sau N1, đo lại nền hop-nhat: các lỗi N5 đang bị che sẽ lộ ra.

**N2 — thiếu psycopg (môi trường).** `test_m2_00b_quyen` 21, `test_m2_00b_tinh` 16, `test_v13_backup_safety` 4, `test_crm_khoi_dong` 1, `test_crm_phan_tich` 1. Các test PG khác tự `skip` khi thiếu psycopg, riêng nhóm M2-00B và vài test CRM thì **lỗi** thay vì skip. Lát sửa (L0-3, nhóm M2-00B/CRM): thêm `skipUnless` psycopg/`KHO_PG_DSN_TEST` cho các test này; cài psycopg vào Python test chỉ khi anh Dũng duyệt thư viện ngoài (CLAUDE.md dự án).

**N3 — worktree khác kho chính (môi trường).** (a) 17 file `.xml` và 2 file `.zip` trong `tests/fixtures` bị `.gitignore` nên chỉ có ở kho chính: `test_doi_chieu_hoa_don` 5, `test_hoa_don_xml` 1 (cả hai bên). (b) Git for Windows đặt `core.autocrlf=true` (cấu hình hệ thống) nên worktree checkout ra **CRLF** trong khi SHA pin tính trên LF (kho chính: `w/lf`): `test_kho_10` 15, `test_m5_k2` 5 (hop-nhat); chinh còn thêm `test_crm_ky_ket`, `test_m4_01b_tinh`, `test_m4_02b_pure`. Kiểm bằng bản xuất LF (`git -c core.autocrlf=false archive`) cho 17 module: lỗi của `chinh` giảm 42 → 16, của `hop-nhat` giảm 38 → 18 (hết hẳn ở các module trên). Lát sửa (file chung, lead làm): thêm `.gitattributes` (tối thiểu `-text` hoặc `eol=lf` cho `tests/fixtures/**`; lead quyết định có áp cho `src/**`) rồi làm tươi các worktree; đưa 19 fixture DEMO vào git bằng `git add -f` sau khi anh/lead xác nhận là dữ liệu giả (không đọc nội dung ở lát này).

**N4 — test đòi điều kiện ngoài runner/ngoài repo (môi trường).** (a) `from tests.xxx import …` ở 6 module hop-nhat (`test_m4_02b_http/_k2`, `test_m4_03a_full_basis_pg`, `test_m4_03b_common_pg`, `test_m4_master_dung_chung_http/_pg`) và 2 module chinh: `test.ps1` chạy `tests\run_suite.py` nên `sys.path[0]` là `tests\`, gốc repo không có trong đường dẫn. Sửa: thêm gốc repo vào `PYTHONPATH` trong `test.ps1`/runner — **sau đó phải đo lại nền** vì các module này sẽ chạy thật (nền hiện tại chưa phản ánh chúng). (b) `test_source6_docx_tables` 1, `test_source6_lazy_excel` 3: đòi `KTT_SOURCE6_E3_OVERLAY` / bố cục thư mục đóng băng ngoài repo (không skip, báo NOT_VERIFIED) → lát Source6 đổi thành skip có lý do khi thiếu. (c) `test_trich6_host` 3 (cả hai bên): "Guard giữ tệp của tiến trình central" — cần runtime app (`crm-demo/runtime.local.json`).

**N5 — test lỗi thời hoặc lệch code (code/test) + treo.** Có sẵn ở `chinh` (14 lỗi, 10 module): các test đếm migration cứng ("23 ≠ 14/15/16/18/20": `test_crm_41_02`, `test_crm_giao_ket`, `test_l11_migrations`, `test_m0_m5_migrations`, `test_m2_migrations`, `test_m4_review_compute`), test "byte đầu migration", pin `test_l11_k2`/`test_m2_k2` lệch (không do CRLF), `test_web` (1 ≠ 2), `test_trich_chung_6` (chuỗi `LENH_RIENG`). Riêng hop-nhat thêm: `test_m4_01c` (test cấm `/api/m4/ke-toan` trong JS, JS mới có) và `test_m4_master_dung_chung_tinh` 2 (assert SQL), cộng module treo ở trên. Lát sửa: L0-3 theo nhóm module; riêng test đếm migration nên sửa một lần theo danh sách migration hiện hành.

**Thứ tự gợi ý cho L0-3:** N1 (L0-2c/L0-2d) → đo lại → N3 (`.gitattributes` + fixture) và N4(a) (PYTHONPATH) → đo lại nền → N2 và N5 theo nhóm.

## 2. Bảng theo module

`chênh` = lỗi (ERROR+FAIL) và ok của hop-nhat trừ chinh. Nguyên nhân gốc lấy từ traceback đầu tiên (mã nhóm N1–N5 ở mục 1).

| Module | chinh | hop-nhat | chênh | nguyên nhân gốc | treo? |
|---|---|---|---|---|---|
| `test_crm_41_02` | 26/0/3/0 | 0/1/0/0 | lỗi −2 · ok −26 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_crm_41_02_http` | 0/0/0/13 | 0/0/0/13 | = | — |  |
| `test_crm_g6a_m25_integration` | — | 0/1/0/0 | mới · lỗi 1 | N1 thiếu `tests/test_crm_kiem_hd.py` |  |
| `test_crm_giao_ket` | 50/0/1/2 | 0/1/0/0 | lỗi +0 · ok −50 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_crm_giao_ket_http` | 0/0/0/11 | 0/1/0/0 | lỗi +1 · ok +0 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_crm_k2` | 0/0/0/23 | 0/1/0/0 | lỗi +1 · ok +0 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_crm_khoi_dong` | 0/1/0/0 | 0/1/0/0 | = | N2 thiếu driver psycopg |  |
| `test_crm_ky_ket` | 31/0/2/6 | 0/1/0/0 | lỗi −1 · ok −31 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_crm_ky_ket_http` | 0/0/0/9 | 0/1/0/0 | lỗi +1 · ok +0 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_crm_neutral_compat` | 0/0/0/5 | 0/0/0/5 | = | — |  |
| `test_crm_phan_tich` | 20/1/0/0 | 20/1/0/0 | = | N2 thiếu driver psycopg |  |
| `test_doi_chieu_hoa_don` | 27/5/0/0 | 27/5/0/0 | = | N3 thiếu fixture .xml/.zip (bị .gitignore) ×5 |  |
| `test_hoa_don_xml` | 0/1/0/0 | 0/1/0/0 | = | N3 thiếu fixture .xml/.zip (bị .gitignore) |  |
| `test_ket_noi` | 12/0/0/11 | 12/0/0/11 | = | — |  |
| `test_kho_10` | 43/0/15/0 | 43/0/15/0 | = | N3 SHA fixture lệch do CRLF (autocrlf=true) ×15 |  |
| `test_l11_http` | 0/0/0/2 | 0/0/0/2 | = | — |  |
| `test_l11_k2` | 2/1/0/20 | 2/1/0/20 | = | N5 pin manifest/fixture lệch (không do CRLF) |  |
| `test_l11_migrations` | 11/0/1/2 | 0/1/0/0 | lỗi +0 · ok −11 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m0_m5_migrations` | 0/1/0/10 | 0/1/0/0 | lỗi +0 · ok +0 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m1` | 43/0/0/0 | 42/1/0/0 | lỗi +1 · ok −1 | N1 `ha_tang.postgres` không nạp được (qua pg_migrations → sql_duyet) |  |
| `test_m2_00b_quyen` | — | 1/21/0/0 | mới · lỗi 21 | N2 thiếu driver psycopg ×21 |  |
| `test_m2_00b_tien_trinh` | — | 16/0/0/0 | mới · lỗi 0 | — |  |
| `test_m2_00b_tinh` | — | 3/16/0/0 | mới · lỗi 16 | N2 thiếu driver psycopg ×16 |  |
| `test_m2_http` | 0/0/0/3 | 0/0/0/3 | = | — |  |
| `test_m2_k2` | 0/1/0/0 | 0/1/0/0 | = | N5 pin manifest/fixture lệch (không do CRLF) |  |
| `test_m2_migrations` | 3/0/1/3 | 0/1/0/0 | lỗi +0 · ok −3 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m4_01b_pg` | 0/0/0/10 | 0/0/0/10 | = | — |  |
| `test_m4_01b_tinh` | 40/0/1/9 | 0/1/0/0 | lỗi +0 · ok −40 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m4_01c` | 16/0/0/0 | 15/0/1/0 | lỗi +1 · ok −1 | N5 test cấm `/api/m4/ke-toan` trong JS nhưng JS mới có |  |
| `test_m4_01c_http` | 0/0/0/8 | 0/0/0/8 | = | — |  |
| `test_m4_02b_http` | 0/1/0/0 | 0/1/0/0 | = | N4 `from tests.… import`: gốc repo không nằm trong sys.path |  |
| `test_m4_02b_k2` | 0/1/0/0 | 0/1/0/0 | = | N4 `from tests.… import`: gốc repo không nằm trong sys.path |  |
| `test_m4_02b_pure` | 16/0/2/18 | 0/1/0/0 | lỗi −1 · ok −16 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m4_02c_pg` | — | 0/1/0/0 | mới · lỗi 1 | N1 thiếu `fixtures_m4.KET_LUAN_VND` |  |
| `test_m4_03a_full_basis_pg` | — | 0/1/0/0 | mới · lỗi 1 | N4 `from tests.… import`: gốc repo không nằm trong sys.path |  |
| `test_m4_03a_full_basis_tinh` | — | 0/1/0/0 | mới · lỗi 1 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m4_03a_m26_integration` | — | 0/1/0/0 | mới · lỗi 1 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m4_03a_tinh` | — | 0/1/0/0 | mới · lỗi 1 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m4_03b_common_pg` | — | 0/1/0/0 | mới · lỗi 1 | N4 `from tests.… import`: gốc repo không nằm trong sys.path |  |
| `test_m4_03b_common_tinh` | — | 0/1/0/0 | mới · lỗi 1 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m4_04b_request_wiring_http` | — | 0/1/0/0 | mới · lỗi 1 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m4_master_dung_chung_http` | — | 0/1/0/0 | mới · lỗi 1 | N4 `from tests.… import`: gốc repo không nằm trong sys.path |  |
| `test_m4_master_dung_chung_pg` | — | 0/1/0/0 | mới · lỗi 1 | N4 `from tests.… import`: gốc repo không nằm trong sys.path |  |
| `test_m4_master_dung_chung_tinh` | — | 9/3/2/0 | mới · lỗi 5 | N1 thiếu `m4/sql_duyet.py` ×3; N5 assert SQL master (ALTER bảng cũ; thiếu `SET search_path`) ×2 |  |
| `test_m4_request_fix02` | — | 0/1/0/0 | mới · lỗi 1 | N1 thiếu `m4/request_api.py` |  |
| `test_m4_request_tinh` | — | 0/1/0/0 | mới · lỗi 1 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m4_review_compute` | 45/0/3/3 | 0/1/0/0 | lỗi −2 · ok −45 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m4_review_http` | 0/0/0/7 | 0/0/0/7 | = | — |  |
| `test_m4_review_k2` | 0/0/0/14 | 0/0/0/14 | = | — |  |
| `test_m5_http` | 0/0/0/2 | 0/0/0/2 | = | — |  |
| `test_m5_k2` | 5/5/0/26 | 5/5/0/26 | = | N3 SHA fixture lệch do CRLF (autocrlf=true) ×5 |  |
| `test_m9_k2` | 0/0/0/18 | 0/1/0/0 | lỗi +1 · ok +0 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_m9_phan_tich` | 10/0/0/0 | 10/0/0/0 | = | — |  |
| `test_modules` | 48/0/0/0 | 48/0/0/0 | = | — |  |
| `test_nghiem_thu_bridge` | 21/0/0/0 | 21/0/0/0 | = | — |  |
| `test_pg_bo_chuyen_schema10` | 0/0/0/1 | 0/0/0/1 | = | — |  |
| `test_pg_schema` | 0/0/0/18 | 0/1/0/0 | lỗi +1 · ok +0 | N1 thiếu `m4/sql_duyet.py` |  |
| `test_source6_docx_tables` | — | 0/1/0/0 | mới · lỗi 1 | N4 đòi `KTT_SOURCE6_E3_OVERLAY` (bố cục đóng băng ngoài repo) |  |
| `test_source6_g5_e5` | — | 6/0/0/0 TREO | mới · lỗi 0 | vòng lặp bận trong `json.raw_decode` (không tới được lỗi) | **TREO** `E5ClientIoMockTests.test_raw_khac_yeu_cau_khong_nhan` |
| `test_source6_lazy_excel` | — | 0/3/0/0 | mới · lỗi 3 | N4 đòi bố cục đóng băng ngoài repo (SETUP NOT_VERIFIED) ×3 |  |
| `test_trich6_host` | 14/3/0/3 | 14/3/0/3 | = | N4 Guard engine #6 chưa đạt (cần runtime app) ×3 |  |
| `test_trich_chung_6` | 31/0/1/1 | 30/1/1/1 | lỗi +1 · ok −1 | N1 thiếu `m4/sql_duyet.py`; N5 test chờ chuỗi `LENH_RIENG = …` đã đổi trong code |  |
| `test_v10` | 25/0/0/0 | 25/0/0/0 | = | — |  |
| `test_v11` | 25/0/0/0 | 25/0/0/0 | = | — |  |
| `test_v12` | 9/0/0/0 | 9/0/0/0 | = | — |  |
| `test_v13_backup_safety` | 15/4/0/0 | 9/5/0/0 | lỗi +1 · ok −6 | N1 thiếu `m4/sql_duyet.py`; N2 thiếu driver psycopg ×4 |  |
| `test_v13_backup_safety_pg` | 0/0/0/11 | 0/0/0/11 | = | — |  |
| `test_v13_doi_chieu` | 15/0/0/3 | 1/14/0/3 | lỗi +14 · ok −14 | N1 thiếu `m4/sql_duyet.py` ×14 |  |
| `test_v1_matching` | 27/0/0/0 | 27/0/0/0 | = | — |  |
| `test_v1b` | 14/0/0/0 | 14/0/0/0 | = | — |  |
| `test_v2` | 5/0/0/0 | 5/0/0/0 | = | — |  |
| `test_v3` | 4/0/0/0 | 4/0/0/0 | = | — |  |
| `test_v4` | 2/0/0/0 | 2/0/0/0 | = | — |  |
| `test_v5` | 2/0/0/0 | 2/0/0/0 | = | — |  |
| `test_v6` | 1/0/0/0 | 1/0/0/0 | = | — |  |
| `test_v7` | 6/0/0/0 | 6/0/0/0 | = | — |  |
| `test_v8` | 3/0/0/0 | 3/0/0/0 | = | — |  |
| `test_v9` | 3/0/0/0 | 3/0/0/0 | = | — |  |
| `test_v9b` | 19/0/0/0 | 19/0/0/0 | = | — |  |
| `test_web` | 22/0/1/0 | 22/0/1/0 | = | N5 `IntakeTests` 1 ≠ 2 (biên nhận/scope) |  |
