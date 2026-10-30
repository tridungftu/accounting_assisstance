# G2 · giao G2-16 — sổ cổng, instance, thế hệ sở hữu và số đo bền vững

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** worktree dựng từ `lat/g2-15` (G2-00…G2-12, CR1/CR2, G2-14, G2-15; G2-13 ở nhánh riêng — sổ cho phép bỏ số). G2-14 có thể được sửa vòng 2 song song: không phụ thuộc vào nội dung hàm tạo việc.

Quy ước như cũ:
- login thật + phiên xác minh; không DROP;
- không sửa migration đã phát hành;
- test tự áp chuỗi SQL theo số.

## Lát G2-16

**Tệp:**
- `src\kho_tri_thuc\core\sql\016_so_cong.sql`
- `src\kho_tri_thuc\core\so_cong.py`
- `tests\test_g2_16.py`

**Căn cứ:**
- `docs\47-core\g1\DAC-TA-CSDL.md` §3.2 (dòng ~168–180: engine, `so_cong`, số đo; UNIQUE `(may_chu_id, dia_chi_nghe, cong)`, FK module **hoặc** hồ sơ engine);
- `CHUAN-CORE-CSDL-v1.0.md` ~172 (một phiên hoạt động cho một mã module / máy; lease, thế hệ sở hữu, CAS);
- `CHUAN-CORE-API-v1.0.md` ~471 (cổng nội bộ cố định do Core cấp);
- `CHUAN-CORE-SDK-v1.0.md` ~327 (khóa phối hợp theo chủ chạy / máy chủ; lấy cổng cố định và thế hệ sở hữu từ sổ cổng);
- CD-028 (giữ cổng `socket.share`; tài khoản Windows riêng — **chỉ phần sổ**, chưa làm socket: socket là G2-21).
- **Dùng lại** registry G2-05 (module / engine) và cách tính số đo hiện có (tìm trong `ha_tang\chay_engine.py`, `ha_tang\pg_migrations.py`) — chỉ đọc.

**Việc:**
- Bảng `loi.so_cong`, instance và số đo bền vững (đặt tên theo đặc tả).
- Hàm Core DEFINER:
  - cấp cổng cố định;
  - nhận quyền sở hữu (CAS theo thế hệ + lease);
  - gia hạn (không rút ngắn hạn — bài học G2-14);
  - trả quyền;
  - ghi trạng thái lỗi khởi động.
- **Hai instance cùng mã module / máy:** chỉ một giữ được; thế hệ cũ bị từ chối.
- **Khóa lỗi khởi động còn sau restart:** không tự xóa trạng thái lỗi khi tiến trình mới lên; chỉ Admin hoặc thao tác mở khóa có audit.
- **Không có login engine:** engine không có login CSDL riêng; Core ghi thay. Test kiểm không có role LOGIN nào cho engine.
- Thêm dòng / hết hiệu lực; không xóa.

**Test PG** (login thật):
- UNIQUE chủ / cổng;
- CAS chống hai instance (hai kết nối song song);
- lease hết → instance mới nhận được, instance cũ bị từ chối;
- gia hạn không rút ngắn;
- khóa lỗi khởi động còn sau restart;
- không có role LOGIN cho engine;
- runtime / module không ghi thẳng bảng;
- sai pháp nhân / module bị chặn nếu có cột pháp nhân.

Báo cáo ≤ 3 dòng.
