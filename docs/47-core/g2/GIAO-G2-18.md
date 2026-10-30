# G2 · giao G2-18 — HTTP boundary và Dispatcher `/api/v1/` theo registry

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `hop-nhat-20261023` (G2-00…G2-12, G2-14, G2-17 sổ contract, G2-24, CR1/CR2).

Lát này **chỉ Python**, không SQL mới.

## Lát G2-18

**Tệp:**
- `src\kho_tri_thuc\core\http.py`
- `src\kho_tri_thuc\core\dispatcher.py`
- `tests\test_g2_18.py`

**Căn cứ:**
- `docs\47-core\chuan\CHUAN-CORE-API-v1.0.md`:
  - §3.1 route / namespace / đăng ký;
  - §3.2 phiên / Origin / CSRF;
  - §3.3 pháp nhân / quyền;
  - §3.4 JSON / schema, giới hạn 1 MiB;
  - §3.5 lỗi chuẩn và mã HTTP;
  - §3.6 chống trùng (dùng G2-11);
  - §3.7 CAS / 409 / phân trang;
  - §3.8 việc lâu 202 sau commit (dùng G2-14);
  - §3.12 danh sách route;
  - §6 ví dụ;
  - §7 checklist.
- `docs\47-core\g1\DAC-TA-API.md` (OpenAPI 3.1) và `ANH-XA-ROUTE.md`.
- **Dùng lại:**
  - registry route / contract G2-05 / G2-17;
  - phiên G2-03;
  - biên nhận G2-11;
  - hàng việc G2-14;
  - bộ kiểm schema G2-17 / G2-24.
- **Bọc** phần xử lý HTTP hiện có trong `giao_dien\server.py` (chỉ đọc, **không sửa** — tệp dùng chung): Origin / CSRF / giới hạn thân, nếu đã có.

**Việc:**
- **`http.py`** — biên HTTP:
  - đọc phiên từ cookie;
  - kiểm Origin / CSRF cho phương thức ghi;
  - giới hạn JSON 1 MiB **đếm khi nhận luồng**;
  - envelope và lỗi chuẩn theo §3.5;
  - không để lộ traceback / thông báo driver.
- **`dispatcher.py`:**
  - tra route `/api/v1/` theo registry → module đích;
  - kiểm pháp nhân / quyền trước khi chuyển;
  - chống trùng qua biên nhận;
  - việc lâu → 202 **sau commit**;
  - CAS lệch → 409;
  - phân trang theo §3.7;
  - **response của module sai contract → 502**, không trả nguyên văn cho trình duyệt.
- Không mở cổng thật trong test: dùng WSGI / handler giả hoặc server loopback cổng 0 trong tiến trình test.

**Test:**
- **Thuần:**
  - Origin sai / thiếu CSRF → 403;
  - thân 1 MiB + 1 byte → 413 ngay khi đếm;
  - envelope lỗi đúng mẫu;
  - route không đăng ký → 404;
  - response sai schema → 502;
  - phân trang.
- **PG (login thật):**
  - chống trùng phát lại qua biên nhận G2-11;
  - việc lâu trả 202 chỉ khi đã commit (rollback → không có việc);
  - CAS 409;
  - sai pháp nhân bị chặn.

Báo cáo ≤ 3 dòng.
