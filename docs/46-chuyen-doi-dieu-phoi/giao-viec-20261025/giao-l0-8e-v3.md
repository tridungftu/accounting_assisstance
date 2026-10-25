# L0-8e vòng 3 — hồi quy: test tự `CREATE DATABASE` bị bộ chạy từ chối "tên có sẵn/đã dùng" (lead đã hoàn tác gộp)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Cùng quy tắc `giao-l0-8e.md` (UTF-8 không BOM; không commit; không nối CSDL/không khởi động PostgreSQL — lead chạy PG; **không nới bảo vệ**). Worktree hiện tại, nhánh `lat/l0-8e` (vòng 1 a897d87 + vòng 2 45a71f4).

**Bằng chứng (lead 25/10 21:13):** gộp L0-8e vào hop-nhat (e657998) rồi chạy `--runtime <runtime DEMO có thu_muc_khoi_dong> --pg-demo`: `test_crm_k2`, `test_crm_giao_ket_http`, `test_crm_41_02_http`, `test_crm_42_s1_http`, `test_crm_ky_ket`, `test_crm_ky_ket_http`, `test_crm_neutral_compat` lỗi **ngay `setUpClass`** — `ValueError: Từ chối CREATE: tên có sẵn/đã dùng hoặc không hợp lệ.` (`tools/chay_test_theo_module.py` `_SoHuuPg.dang_ky` ~:288-293). Tên CSDL của các test này **ngẫu nhiên** (`"kho_test_crm_" + uuid4().hex[:8]`, ví dụ `tests/test_crm_k2.py:85-92`) nên không thể trùng thật. Cùng mã, **bộ chạy trước L0-8e** chạy `test_crm_k2` 19 ca bình thường. Các module dùng bản sao do bộ chạy dựng (03a, 03b) và `test_trich6_host` thì đạt — vì không tự CREATE trong test. Nghi gốc: trong tiến trình test, **guard A517 (sitecustomize) bọc ngoài hook sở hữu PG của bộ chạy** (cả hai vá `psycopg` `Connection/Cursor.execute`) → một lệnh `CREATE DATABASE` đi qua hook sở hữu **hai lần** (lần 2 thấy tên đã ở `d["muc"]` → từ chối), hoặc guard chạy lại lệnh. Lead đã hoàn tác gộp (b25ff7a).

**Việc:**
1. Tái hiện bằng test thuần (psycopg giả, có cả guard giả bọc ngoài như A517 và hook sở hữu của bộ chạy) và tìm đúng gốc.
2. Sửa sao cho trong tiến trình test: một lệnh `CREATE DATABASE kho_test_*` đăng ký sở hữu **đúng một lần** dù có guard bọc ngoài (idempotent theo đúng lệnh/kết nối, không nới kiểm "tên có sẵn trước lần chạy"); `DROP` do test gọi bị guard giữ lại thì mục vẫn được `_goi` (không guard) dọn sau module như vòng 2. Không tắt guard trong tiến trình test (host #6 cần).
3. Test: ca hồi quy trên (guard bọc ngoài + CREATE trong test → thành công, sổ 1 mục); ca âm: tên có sẵn trước lần chạy vẫn bị từ chối; ca DROP bị guard giữ → dọn sau module.

**File được sửa (chỉ 2):** `tools/chay_test_theo_module.py`, `tests/test_chay_test_pg_demo.py`. Không xóa file, không sửa mã sản phẩm.
**Lead sẽ kiểm (bắt buộc trước khi gộp lại):** dưới runtime thật + `--pg-demo`: `test_crm_*` (cả bộ) không thêm mã lỗi so với nền; `test_m4_03a_pg` 13/13; `test_trich6_host`; `test_chay_test_pg_demo`; số CSDL `kho_test_*` trước/sau không tăng.
**Báo cáo cuối (≤ ⅓ trang):** gốc lỗi (tệp:dòng) · cách sửa · ca test · thông điệp commit `[L0-8e] vòng 3: …`.
