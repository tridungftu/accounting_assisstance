# G2 · giao G2-19 — SDK context và transaction đúng login / ủy nhiệm (lát cốt lõi, review Opus bắt buộc)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-18` (G2-00…G2-15, CR1/CR2, G2-18 HTTP / dispatcher). Gói SDK mới: `src\kho_tri_thuc\sdk_core\`. Tạo `__init__.py` rỗng nếu chưa có; tính trong 3 tệp chỉ khi không tránh được — nếu cần thì ghi "Cần lead".

## Lát G2-19

**Tệp:**
- `src\kho_tri_thuc\sdk_core\ngu_canh.py`
- `src\kho_tri_thuc\sdk_core\giao_dich.py`
- `tests\test_g2_19.py`

**Căn cứ:**
- `docs\47-core\chuan\CHUAN-CORE-SDK-v1.0.md`:
  - §3.1 ranh giới SDK / quyền;
  - §3.2 kiểu và quy ước (`NguCanh`, `GiuViec`…);
  - §3.4 transaction / chống trùng / việc nền (cùng `tx`, cùng kết nối);
  - §3.6 khung chạy;
  - §7.3 checklist bí mật.
- `docs\47-core\chuan\CHUAN-CORE-API-v1.0.md` §3.11: thẻ liên tiến trình, mã ủy nhiệm, credential instance; thẻ ≤ 30 giây.
- `docs\47-core\g1\DAC-TA-SDK.md`.
- **Dùng lại:**
  - phiên G2-03 (`core\phien.py`);
  - biên nhận G2-11;
  - hàng việc G2-14 (`GiuViec`, lease, mã ủy nhiệm theo việc);
  - bus G2-15;
  - dispatcher G2-18.

**Việc:**
- **`ngu_canh.py`:**
  - dựng context của một request từ thẻ liên tiến trình do Core ký: hạn ≤ 30 giây, chữ ký, instance, hash thân request, nonce;
  - **nonce dùng một lần**: hai request đồng thời cùng nonce → chỉ một vào handler;
  - context bất biến;
  - bí mật (mã ủy nhiệm, thẻ, credential) không lộ qua `repr` / `str` / log / pickle / traceback locals.
- **`giao_dich.py`:**
  - mở transaction trên **đúng login module** và gắn phiên / ủy nhiệm đã xác minh vào kết nối (`set_config` cục bộ theo transaction, qua hàm Core);
  - trả `tx` cho handler, để biên nhận / việc / bus dùng chung `tx`;
  - **pool không rò context**: kết thúc transaction (commit / rollback / lỗi) phải xóa sạch, kết nối trả pool không còn phiên cũ;
  - SDK không tự commit thay handler khi chưa xong.
- Không gọi HTTP để mô phỏng nguyên tử.

**Test:**
- **Thuần:**
  - thẻ quá 30 giây / sai chữ ký / sai instance / sai hash → từ chối;
  - repr / log / pickle không lộ bí mật.
- **PG (login thật):**
  - nonce đồng thời (hai luồng) → một vào handler;
  - context rò: transaction 1 của người A xong, transaction 2 trên cùng kết nối không thấy phiên A;
  - rollback handler → biên nhận / việc / sự kiện cũng rollback;
  - login sai (module khác) bị chặn.

Báo cáo ≤ 3 dòng. Lead chạy PG và gọi review Opus trước khi gộp.
