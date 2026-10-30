# G2 · giao G2-14 — hàng việc bền vững: việc – bước – lần thử

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `hop-nhat-20261023` (đã có G2-00…G2-12, CR1/CR2; G2-13 đang ở nhánh riêng — số 013 có thể chưa có, sổ migration cho phép bỏ số).

Quy ước như cũ:
- login thật + phiên xác minh; không DROP;
- **không sửa migration đã phát hành (001–012)**;
- test tự áp chuỗi SQL theo số;
- không đặt thuộc tính test trùng tên phương thức `TestCase`.

## Lát G2-14

**Tệp:**
- `src\kho_tri_thuc\core\sql\014_viec.sql`
- `src\kho_tri_thuc\core\viec.py`
- `tests\test_g2_14.py`

**Căn cứ:**
- `docs\47-core\chuan\CHUAN-CORE-CSDL-v1.0.md`:
  - khối `loi` (hàng việc);
  - `lan_thu` (dòng ~112);
  - lease / thế hệ / CAS (~172);
  - mã ủy nhiệm theo việc (~257, ~279).
- `docs\47-core\chuan\CHUAN-CORE-SDK-v1.0.md`:
  - `GiuViec` (~92);
  - Core tự gắn việc / bước / lần thử (~157);
  - cùng `tx` (~199);
  - mất lease (~230–232).
- Đặc tả chi tiết: `docs\47-core\g1\DAC-TA-CSDL.md` (tìm "hàng việc", "lease", "CHUA_RO"), `DAC-TA-SDK.md`.
- **Nâng (không viết lại)** hàng việc hiện có: `src\kho_tri_thuc\ha_tang\hang_viec.py` và định nghĩa SQL cuối của nó trong `ha_tang\pg_migrations.py` — chỉ đọc để giữ ngữ nghĩa (CD-036: dùng lại / bọc / sửa / viết mới).

**Việc:**
- **Bảng trong `loi`:** việc, bước, lần thử (thêm dòng, không sửa đè lịch sử).
- **Hàm Core DEFINER:**
  - nhận việc (lease có hạn + thế hệ + mã ủy nhiệm riêng của lease, chỉ lưu hash);
  - heartbeat (CAS theo thế hệ);
  - hoàn tất / lỗi / hủy.
- **Mất lease / thế hệ cũ / mã cũ** → từ chối, rollback phần ghi liên quan.
- **Khởi động lại:** lần thử đang chạy chuyển `GIAN_DOAN` (interrupted). Trạng thái `CHUA_RO` (tác động ngoài CSDL chưa đối chiếu) **không tự retry mù**: chờ đối chiếu.
- Module / engine chỉ thấy việc của mình (RLS theo phiên / instance).
- Không tuyên bố exactly-once cho tác động ngoài CSDL.

**Test PG** (login thật):
- hai worker tranh một việc: chỉ một nhận được;
- lease hết hạn → worker cũ heartbeat / hoàn tất bị từ chối, token cũ vô hiệu;
- CAS lệch thế hệ → lỗi;
- rollback nghiệp vụ cùng `tx` → trạng thái việc cũng rollback;
- restart → `GIAN_DOAN`;
- `CHUA_RO` không được nhận lại tự động;
- runtime không ghi thẳng bảng; sai pháp nhân / module bị chặn;
- token không lưu dạng rõ.

Báo cáo ≤ 3 dòng.
