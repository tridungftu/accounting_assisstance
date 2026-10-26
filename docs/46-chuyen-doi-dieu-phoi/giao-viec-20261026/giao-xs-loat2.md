# Xương sống (CD-017) loạt 2: XS-1b và XS-4a — phần riêng theo mã lát

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì ghi NOT_RUN; lead chạy test và PG.
- Test PG tự tạo `kho_test_*` (`skipUnless KHO_PG_DSN_TEST`), không đọc `KHO_PG_DEMO_*`. Dữ liệu giả đúng trigger/ràng buộc thật. Chạy được dưới guard giữ tệp `CODEX_NO_DELETE_FILES`.
- **Căn cứ:**
  - TL 53 `D:\Claude\Phan mem ho tro ke toan\53-kien-truc-xuong-song-engine-module.md`;
  - CD-017;
  - `docs\46-chuyen-doi-dieu-phoi\KK-XUONG-SONG.md` §2 dòng của lát.
- **Đã có:**
  - **M0052** `k2/sql_bus_su_kien.py` (schema `bus`, outbox/inbox, dedupe, ACK, RLS);
  - `ha_tang/engine.py`, `ha_tang/danh_ba_engine.py` (XS-3a).
- **Không đổi hành vi hiện có**; chỉ thêm.

## XS-1b · Lớp Python bus sự kiện

**Tệp (2):**
- `ha_tang/bus_su_kien.py` mới;
- `tests/test_xs1_bus.py` mới.

**Việc:**
- API Python mỏng trên các hàm SQL M0052:
  - `phat(conn, loai, phien_ban, khoa_dedupe, tham_chieu)`: gọi **trong giao dịch của bên gọi**, không tự commit;
  - `nhan(conn, ben_nhan, loai, gioi_han)`;
  - `ack(conn, ben_nhan, su_kien_id)`.
- Nhận lại không nhân đôi. Lỗi giữa ghi kết quả và ACK → bên gọi rollback cả hai (ghi rõ hợp đồng trong docstring).
- Không log payload. Không thêm thư viện.

**Test (PG):**
- phát trong giao dịch rollback → không có;
- hai bên nhận độc lập;
- ACK lại không nhân đôi;
- ghi kết quả + ACK cùng giao dịch, lỗi → cả hai mất;
- sai PN không thấy.

## XS-4a · Mô hình khai báo module tổng quát (không sửa khung hiện có)

**Tệp (2):**
- `ha_tang/khai_bao_module.py` mới;
- `tests/test_xs4_khai_bao.py` mới.

**Không sửa `giao_dien/khung_khai_bao.py`.** Dòng giao diện có bản khác của tệp này đang chờ cổng A.

**Việc:**
- Kiểu dữ liệu thuần cho khai báo một module:
  - mã, tên, icon, nhóm màu, thứ tự;
  - các phần/màn (mã, tên, đường dẫn, quyền xem);
  - thẻ đếm;
  - danh mục hành động theo màn (để ma trận thẩm quyền đọc cột ở XS-4d);
  - engine dùng (mã engine từ danh bạ XS-3a);
  - mặc định công tắc.
- Kiểm hợp lệ: mã duy nhất, đường dẫn bắt đầu `#`, hành động thuộc {XEM, LAP, SUA, KIEM, DUYET, HUY}.
- **Bộ chuyển đổi** đọc khai báo CRM hiện có (`khung_khai_bao.MODULE["crm"]`, chỉ import) sang mô hình mới. Kết quả tương đương: không mất trường, thứ tự giữ.
- Chưa có công tắc SQL (XS-4b), chưa nối HTTP/UI.

**Test:**
- khai báo hợp lệ/không hợp lệ;
- chuyển CRM sang mô hình rồi trở lại so khớp các trường;
- engine không có trong danh bạ → cảnh báo/từ chối theo cờ.

**Báo cáo (≤ ¼ trang)** mỗi lát, "Cần lead", thông điệp commit `[XS-1b] …` / `[XS-4a] …`.
