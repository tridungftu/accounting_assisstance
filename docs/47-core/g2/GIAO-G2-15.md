# G2 · giao G2-15 — bus sự kiện: outbox / inbox, ACK cùng transaction

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-14` (G2-00…G2-12, CR1/CR2, G2-14 hàng việc; G2-13 ở nhánh riêng — số 013 có thể chưa có, sổ cho phép bỏ số).

Quy ước như cũ:
- login thật + phiên xác minh; không DROP;
- không sửa migration đã phát hành;
- test tự áp chuỗi SQL theo số.

## Lát G2-15

**Tệp:**
- `src\kho_tri_thuc\core\sql\015_su_kien.sql`
- `src\kho_tri_thuc\core\su_kien.py`
- `tests\test_g2_15.py`

**Căn cứ:**
- `docs\47-core\chuan\CHUAN-CORE-CSDL-v1.0.md` (khối `loi`: bus; V4 công bố — sự kiện đi qua bus Core; hạn giữ hộp nhận đã ACK 30 ngày ~dòng 495);
- `CHUAN-CORE-SDK-v1.0.md` (~199: bus cùng `tx`, cùng kết nối);
- `CHUAN-CORE-API-v1.0.md`;
- `docs\47-core\g1\DAC-TA-CSDL.md` (tìm "bus", "outbox", "inbox", "ACK");
- contract sự kiện ở `docs\47-core\g1\CONTRACT-NGHIEP-VU.md` (payload chỉ UUID tham chiếu, ví dụ `moc_da_xay_ra.v1`).
- **Nâng (không viết lại)** bus hiện có: `src\kho_tri_thuc\ha_tang\bus_su_kien.py` và SQL cuối của nó trong `ha_tang\pg_migrations.py` — chỉ đọc (CD-036).

**Việc:**
- **Outbox:** module ghi sự kiện qua hàm Core DEFINER **trong cùng transaction nghiệp vụ** (rollback nghiệp vụ → không có sự kiện).
- **Payload:**
  - chỉ UUID tham chiếu + loại + phiên bản contract đã đăng ký (G2-17 / registry);
  - từ chối payload chứa dữ liệu nghiệp vụ ngoài khai báo;
  - từ chối contract chưa đăng ký hoặc chưa kích hoạt.
- **Inbox:**
  - module nhận chỉ thấy sự kiện được đăng ký đọc;
  - ACK cùng transaction với xử lý của bên nhận;
  - giao lại không nhân tác động (khóa chống trùng theo bên nhận + sự kiện).
- Gắn với hàng việc G2-14 khi cần đánh thức, nhưng không bắt buộc ở lát này.
- Thêm dòng; không xóa. Cơ chế dọn theo hạn giữ để G2-29.

**Test PG** (login thật):
- rollback nghiệp vụ → không có outbox;
- giao lại hai lần → tác động một lần;
- rollback xử lý → ACK cũng rollback, giao lại được;
- payload có trường dữ liệu ngoài UUID → từ chối;
- module không đăng ký đọc → không thấy sự kiện;
- sai pháp nhân bị chặn;
- runtime không ghi thẳng bảng.

Báo cáo ≤ 3 dòng.
