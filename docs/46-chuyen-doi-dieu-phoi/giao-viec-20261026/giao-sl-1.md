# SL-1 · Công cụ sao lưu PostgreSQL mã hóa (CD-019, QD-20261026-11 M2–M3)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. Không commit. **Không chạy pg_dump/gpg thật, không mở PostgreSQL.** Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật, `.env`, không in DSN.
- **Không tạo, không đọc, không ghi gì trong `D:\DU-LIEU-KE-TOAN\`.** Test dùng thư mục tạm riêng mỗi ca và chương trình giả.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy test.
- Không thêm thư viện ngoài (CD-019).

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\KK-MA-HOA-LUU-RIENG.md` §3 (luồng, khóa, lịch, giữ bản) và §6 dòng SL-1;
- `docs\QUYET-DINH.md` QD-20261026-11.

**Lead đã xác minh trên máy:**
- `pg_dump.exe`/`pg_restore.exe` có ở `D:\Claude\Phan mem ho tro ke toan\var\postgresql16-16.15-runtime\bin`;
- `gpg.exe` 2.4.9 ở `C:\Program Files\Git\usr\bin`.

Đường dẫn là **tham số cấu hình**, không cứng trong mã.

**Tệp (2):** `tools/sao_luu_ma_hoa.py` mới; `tests/test_sao_luu_ma_hoa.py` mới.

**Việc:**
1. **Ống dẫn nhị phân:**
   - `subprocess` chạy `pg_dump --format=custom --no-password` → stdin của `gpg --encrypt --recipient <fingerprint ghim> --cipher-algo AES256 --trust-model always --batch` (keyring riêng truyền qua `--homedir`) → tệp đích.
   - Không qua văn bản/PowerShell; **không bao giờ** ghi dump rõ ra đĩa.
2. **Kết nối:**
   - Thông tin kết nối truyền cho tiến trình con bằng **biến môi trường** (`PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE` hoặc `PGSERVICEFILE`), **không** trên argv.
   - Đọc cấu hình kết nối theo cơ chế hiện có của repo (tìm helper đọc `ket-noi.local.json` mà không in DSN). Không tự viết parser mới nếu đã có.
3. **Tệp đích:**
   - thư mục `<gốc sao lưu>\<mã lần YYYYMMDD-HHMMSS>\`, tạo mới độc quyền;
   - ghi `.partial.gpg`; chỉ khi **cả hai** tiến trình exit 0 thì tính SHA-256 bản mã, đổi tên thành `.gpg` và ghi một dòng biên bản (mã lần, dung lượng, SHA, thời gian từng bước, phiên bản pg_dump/gpg);
   - lỗi → giữ `.partial.gpg`, trả mã lỗi đã làm sạch (không lộ DSN/đường khóa). **Không tự xóa** tệp nào, kể cả partial.
4. **Lịch giữ (M3):**
   - chỉ **phân loại** bản nào thuộc "30 bản ngày + 12 bản tháng" và bản nào ngoài hạn giữ — in danh sách đề xuất, **không xóa**;
   - lệnh chép bản mã sang thư mục đích khác (ổ khác / ổ ngoài) có kiểm SHA sau chép.
5. **Kiểm tra trước khi chạy:**
   - đủ chương trình;
   - fingerprint khóa công khai đúng ghim;
   - thư mục gốc sao lưu không nằm trong thư mục phần mềm/repo;
   - còn đủ dung lượng.
6. Chưa làm khôi phục (SL-2), chưa đặt lịch Windows (lead làm sau khi Anh chỉ định người giữ khóa).

**Test (chương trình giả bằng script Python tạm, không gọi pg_dump/gpg thật):**
- thành công → `.gpg` + SHA đúng + biên bản; không có tệp rõ nào trên đĩa;
- pg_dump lỗi giữa chừng / gpg lỗi / gpg thoát sớm → giữ partial, không công bố, mã lỗi đúng;
- argv không chứa mật khẩu/DSN;
- phân loại lịch giữ đúng 30 ngày + 12 tháng, không xóa;
- chép kèm kiểm SHA phát hiện sai lệch;
- thư mục đích trong repo → từ chối.

**Báo cáo (≤ ¼ trang)**, "Cần lead", thông điệp commit `[SL-1] …`.
