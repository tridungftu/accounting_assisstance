# MH-1 · Cổng khóa mã hóa cột và tra cứu HMAC (CD-019, QD-20261026-11 M1–M2)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. Không commit. Không mở server/PostgreSQL. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật, `.env`.
- **Không tạo, không đọc, không ghi gì trong `D:\DU-LIEU-KE-TOAN\`.** Test chỉ dùng thư mục tạm riêng mỗi ca. Khóa thật do lead tạo sau.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy test.
- Không thêm thư viện ngoài: chỉ thư viện chuẩn (`ctypes`, `secrets`, `hmac`, `hashlib`, `base64`) (CD-019).

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\KK-MA-HOA-LUU-RIENG.md` §1 (nhóm A, cách giữ tìm/khớp), §2 (pgcrypto, khóa, chống lọt), §6 dòng MH-1;
- `docs\QUYET-DINH.md` QD-20261026-11.

**Tệp (2):** `ha_tang/ma_hoa_cot.py` mới; `tests/test_ma_hoa_cot.py` mới.

**Việc:**
1. **Nguồn khóa:**
   - Đọc khóa cột `vNN` và khóa tra cứu `vNN` (hai khóa **độc lập**) từ thư mục khóa được truyền vào (mặc định khai báo `D:\DU-LIEU-KE-TOAN\bi-mat\cot\` và `...\tra-cuu\`, chỉ là hằng mặc định, không truy cập khi import).
   - Tệp khóa bọc **DPAPI CurrentUser** qua `ctypes` (`CryptProtectData`/`CryptUnprotectData`). Giữ khóa trong RAM trong vòng đời tiến trình.
   - Thiếu khóa / sai phiên bản / giải DPAPI lỗi → ngoại lệ có **mã** (ví dụ `MH_THIEU_KHOA`), không kèm đường dẫn đầy đủ hay bytes khóa.
2. **Tạo khóa mới:**
   - hàm sinh 32 byte ngẫu nhiên (`secrets`), bọc DPAPI, ghi tệp **tạo mới độc quyền** (không ghi đè tệp có sẵn), trả số phiên bản.
   - Dùng cho lead tạo khóa thật sau; test chỉ gọi trên thư mục tạm.
3. **Tra cứu HMAC-SHA256:**
   - chuẩn hóa theo loại: STK, CCCD, MST, SĐT, email. Không bỏ số 0 đầu; STK dùng lại chuẩn hóa `bank_account` sẵn có nếu có (tìm trong repo, ví dụ `giao_dien/v9b.py`) thay vì viết mới.
   - trả hex 64 ký tự + `lookup_ver`. Cùng giá trị chuẩn hóa → cùng token.
4. **Tham số bind cho SQL:**
   - hàm trả `(khóa, phiên bản)` để caller truyền qua tham số psycopg cho `pgp_sym_encrypt(text, key, 'cipher-algo=aes256,compress-algo=0')` / `pgp_sym_decrypt`;
   - hằng mẫu câu SQL có placeholder; **không** f-string/ghép khóa vào SQL. Chưa nối caller nào (MH-3).
5. **Che hiển thị:** STK/CCCD còn 4 số cuối; email/SĐT che phần giữa.
6. **Chống lọt:**
   - đối tượng giữ khóa có `__repr__`/`__str__` không lộ bytes;
   - không ghi log giá trị hay khóa;
   - thông điệp lỗi không chứa giá trị.

**Test (thuần, Windows có DPAPI thật trong thư mục tạm):**
- tạo → đọc lại khóa đúng; tạo trùng phiên bản bị từ chối, không ghi đè;
- thiếu khóa → đúng mã lỗi;
- hai khóa cột và tra cứu khác nhau;
- HMAC ổn định, giữ số 0 đầu; chuẩn hóa từng loại;
- che hiển thị;
- **khóa canary**: không xuất hiện trong `repr`, thông điệp lỗi, log bắt được;
- mẫu SQL không chứa khóa.

**Báo cáo (≤ ¼ trang)**, "Cần lead", thông điệp commit `[MH-1] …`.
