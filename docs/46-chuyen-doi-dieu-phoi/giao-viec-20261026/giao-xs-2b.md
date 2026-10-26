# XS-2b · Worker chung chạy hàng việc nền + gọi engine (CD-017)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell.** Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy PG.
- Test PG tự tạo `kho_test_*` (`skipUnless KHO_PG_DSN_TEST`) và **chạy dưới vai ứng dụng thật** (như `tests/test_xs4_dich_vu.py`, `tests/test_xs1_bus.py`). Dữ liệu giả, chạy được dưới guard giữ tệp. Không kiểm CRLF/LF.

**Đã có trên nhánh hợp nhất:**
- **M0060** `k2/sql_hang_viec.py` — hàm SQL: tạo việc, nhận (`SKIP LOCKED` + lease, kiểm công tắc), gia hạn, tiến độ, kết thúc CAS, dừng hợp tác, thử lại, `CHUA_RO`;
- **M0056** công tắc + `k2/module.py` (`kiem_module`);
- **XS-3a** `ha_tang/engine.py`, `ha_tang/danh_ba_engine.py`;
- engine thật đã bọc: `ha_tang/engine_cong.py` (E-OCR, E-AI), `ha_tang/engine_hoa_don.py` (E-HOADON);
- **XS-1b** `ha_tang/bus_su_kien.py`.

**Căn cứ:** TL 53; `KK-XUONG-SONG.md` §2 dòng XS-2b, §5 (giao nhận tối thiểu một lần, không hứa exactly-once cho tác động ngoài, hết lease giữ `CHUA_RO`); QD-20261026-09 và -11 (S4: tắt thì không nhận việc mới, việc đang chạy chạy nốt).

**Tệp (3):** `ha_tang/hang_viec.py` mới (API Python mỏng trên hàm SQL M0060); `ha_tang/chay_engine.py` mới (vòng worker); `tests/test_xs2_worker.py` mới.

**Việc:**
1. `hang_viec.py`: `tao_viec(conn, …)` (trong giao dịch bên gọi, không tự commit), `nhan`, `gia_han`, `tien_do`, `ket_thuc`, `yeu_cau_dung`. Gọi đúng hàm SQL; không SQL thẳng bảng; không log tham chiếu/kết quả nhạy cảm.
2. `chay_engine.py`: worker chung:
   - nhận một việc → tra engine theo (mã, phiên bản) trong `DanhBaEngine` → `engine.chay(dau_vao)` ngoài giao dịch dài → ghi kết quả bằng CAS trong giao dịch ngắn;
   - gia hạn lease định kỳ trong lúc chạy; kiểm yêu cầu dừng giữa các bước (dừng hợp tác);
   - mất lease → không ghi kết quả;
   - engine `CHO` → kết thúc với trạng thái chờ có lý do;
   - `LOI` → thử lại theo SQL;
   - ngoại lệ lạ → ghi lỗi có mã, không nuốt im lặng;
   - việc "có tác động ngoài" không tự chạy lại khi lease hết (SQL đã chuyển `CHUA_RO`).
   - Công tắc: SQL M0060 đã không giao việc của module không cho ghi. Worker **không** tự vượt.
   - Đầu vào engine lấy từ tham chiếu việc qua hàm do module đăng ký (callback nạp đầu vào); worker **không** đọc bảng module.
3. Không nối worker vào server/khởi động tự động (lát sau). Không thêm thư viện. Không đụng hàng việc cũ (G5, M4, Request, M2).

**Test (PG + engine giả):**
- một việc XONG (ghi kết quả + bằng chứng engine);
- engine CHO;
- engine LOI → thử lại đến giới hạn;
- hai worker cùng chạy không làm trùng;
- lease hết giữa chừng → kết quả cũ bị từ chối;
- yêu cầu dừng → worker dừng ở bước kế;
- module TẮT ở PN A → worker không nhận việc mới của A, vẫn chạy PN B;
- ngoại lệ lạ → lỗi có mã;
- không đọc bảng module (callback giả).

**Báo cáo (≤ ⅓ trang)**, "Cần lead", thông điệp commit `[XS-2b] …`.
