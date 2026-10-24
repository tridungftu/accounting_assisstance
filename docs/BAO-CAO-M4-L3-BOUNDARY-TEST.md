# Báo cáo M4 L3 — cập nhật test boundary M22 sau migration M23

Task: M4_L3_TEST_BOUNDARY_FIX_CODE_ONLY (fresh session riêng, isolated workspace). Căn cứ: docs/GIAO-CODE-M4-L3-BOUNDARY-TEST-REFERENCE.md,
docs/M4-L3-BOUNDARY-TEST-CONTRACT.md. Sửa assumption test lỗi thời; KHÔNG sửa migration/product/schema để test xanh.

## Trạng thái
- Successor (snapshot sau sửa): **NOT_RUN_CODE_ONLY** — không chạy test/import/AST/SQL/GUI; chỉ đọc lại bằng file tools.
- Baseline frozen8390 (Root đã chạy thật, snapshot CŨ): native44 run44 PASS43 FAIL1 ERROR0 SKIP0, terminal e30171; FAIL duy nhất
  tests/test_m4_02b_pure.py:59. Kết quả này chỉ chứng minh snapshot cũ, KHÔNG kế thừa thành PASS cho successor.

## Nguyên nhân FAIL baseline
`M22Tinh.test_prefix_927604_byte_va_append_m22` đòi toàn file `src/kho_tri_thuc/ha_tang/pg_migrations.py` kết thúc ở đăng ký M22
(`endswith(... M0022_M4_CHUNG_TU) ... PG_SCHEMA_VERSION = len(PG_MIGRATIONS)`) và `(PG_SCHEMA_VERSION, len(PG_MIGRATIONS)) == (22, 22)`.
`M0023_CRM_KY` đã được append hợp lệ sau M22 (pg_migrations.py dòng 11283–11789), nên assumption "cuối file = M22/tổng 22" lỗi thời.

## Thay đổi (đúng 1 method + 1 report mới)
EDIT `tests/test_m4_02b_pure.py`, chỉ method `M22Tinh.test_prefix_927604_byte_va_append_m22` (tên/case giữ nguyên; nay dòng 54–65):
- GIỮ: SHA256 prefix 927604 B = `0e87d8e1a39aef582d79ffd7cef30b7dcdf523d151009729e6cb1d5b64452dce`.
- THÊM: SHA256 toàn boundary M1–22 prefix 928356 B = `225cc40f14670e8428bf8afcc58318c04c15707bdddffa31242067f20199cce2` (giá trị Root đọc từ frozen bytes thực;
  không sinh từ output sản phẩm).
- ĐỔI: đoạn kiểm append M22 từ `raw[927604:]` (đến hết file) thành đúng `raw[927604:928356]`; giữ nguyên hai kiểm trong đoạn này:
  có `from ..m4.sql_chung_tu import M0022_M4_CHUNG_TU`, và đoạn (rstrip) kết thúc bằng
  `PG_MIGRATIONS = (*PG_MIGRATIONS, M0022_M4_CHUNG_TU)\nPG_SCHEMA_VERSION = len(PG_MIGRATIONS)`.
- ĐỔI: `(PG_SCHEMA_VERSION, len(PG_MIGRATIONS)) == (22, 22)` → `PG_SCHEMA_VERSION == len(PG_MIGRATIONS)` và `len(PG_MIGRATIONS) >= 22`
  (cho phép append registry hợp lệ sau boundary; không hardcode tổng 22 hay 23).
- GIỮ: `PG_MIGRATIONS[21] is SC.M0022_M4_CHUNG_TU`, `PG_MIGRATIONS[20] is PM.M0021_CRM_G2G3`.
- Không nới/bỏ prefix hash, không bỏ identity, không skip/xóa/đổi tên testcase.

NEW `docs/BAO-CAO-M4-L3-BOUNDARY-TEST.md` (file này).

## Không đổi
- Mọi byte ngoài method trên trong tests/test_m4_02b_pure.py; native36 case + S1 MOCK_BOUNDARY8 cùng assertions/fixtures khác giữ nguyên.
- Không sửa tests/test_m4_02b_k2.py, adapter/vendor/engine/HTTP/SQL/schema/migration/GUI/master/M9/source37; không helper/framework mới; không xóa file.
- Source388 giữ nguyên path count (chỉ sửa file đã có); thêm report mới → runtime kỳ vọng 460 (baseline 459).

## Gate còn mở (chưa khép bằng gói này)
- Root review + freeze successor + chạy độc lập native44 mới (kỳ vọng mới chưa được chứng minh).
- PostgreSQL thật, GUI, full M4 nghiệm thu: chưa thực hiện, không khẳng định.
