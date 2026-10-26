# CD-016 · soạn tài liệu (chỉ đọc mã/tài liệu, KHÔNG đọc kho thật) — phần riêng theo mã lát

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- **Chỉ tạo đúng tệp tài liệu** ghi trong mục của lát. Không sửa mã, không commit, không mở server/PostgreSQL. Không xóa file.
- **Tuyệt đối không đọc/liệt kê** `var\plhn-that`, `var\web-that`, `cau_hinh.that.toml`, `.env` hay bất kỳ dữ liệu thật nào. Chỉ suy từ **mã nguồn** (schema SQLite trong `src/`, migration PG `ha_tang/pg_migrations.py`) và tài liệu.
- Chỗ chưa rõ: ghi vào mục "Cần Anh/lead", không đoán.

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` mục **CD-016** (và CD-011 bước 4).
- `CLAUDE.md` (mục 2: ngoại lệ kho thật; mục 5: lệnh test).
- `docs\46-chuyen-doi-dieu-phoi\TRANG-THAI.md`, `4-KE-HOACH-LEAD.md`, `NEN-TEST-PG.md`, `docs\QUYET-DINH.md`.
- Project TL 52 có thể không có trong repo: nếu không thấy thì chỉ dựa CD-016.

## CD016-KH · `docs\46-chuyen-doi-dieu-phoi\KE-HOACH-CHUYEN-KHO-THAT-SQLITE-PG.md`

Kế hoạch chuyển kho thật SQLite sang **một CSDL PostgreSQL thật chung**. Chỉ là kế hoạch; chạy khi Anh ra lệnh riêng. Gồm:
1. **Bảng nguồn → đích:** từng bảng SQLite (đọc từ mã tạo schema SQLite trong `src/`, ghi tệp:dòng) → bảng/cột PG tương ứng (migration nào). Ghi rõ bảng không có đích (cần lát mới).
2. **Công cụ chuyển:** dùng lại cách của `tools/chuyen_review_sqlite_sang_pg.py` (M4 CD1/CD2): chỉ đọc nguồn, idempotent, một giao dịch, SHA nguồn.
3. **Biên bản đối chiếu:** số dòng, tổng tiền, khóa.
4. **Sao lưu trước** vào `LUU-TRU` + SHA. **Chạy thử trên bản sao.**
5. **Đường lùi:** kho SQLite giữ nguyên, chỉ đọc; quay lại thế nào.
6. **Thứ tự:** M4 nạp trước (CD-011); các module khác sau.
7. **Rủi ro**, và mục "Cần Anh/lead".

Tối đa khoảng 3 trang.

## CD016-PH · `docs\46-chuyen-doi-dieu-phoi\CHECKLIST-PHAT-HANH.md` và `docs\46-chuyen-doi-dieu-phoi\BANG-DIEU-KIEN-GO-LIVE.md`

**1. `CHECKLIST-PHAT-HANH.md`:** phát hành hằng tuần tối thứ Sáu lên nhánh `chinh`/kho thật; sửa khẩn đi đường riêng. Các bước có ô đánh dấu:
- sao lưu (CSDL + tệp, SHA);
- nâng dữ liệu **chỉ thêm** (migration append, không sửa cũ);
- chạy test (lệnh trong CLAUDE.md, so nền PG mới nhất);
- bật;
- kiểm sau bật;
- **đường lùi**;
- biên bản.

Không bật module lẻ (CD-016 mục 4).

**2. `BANG-DIEU-KIEN-GO-LIVE.md`:** bảng cho **M0, M2, M3, M4, M9**, mỗi module ghi:
- tình trạng cổng A/cổng B;
- các điểm còn chờ Anh chốt (lấy từ TRANG-THAI "Cần Anh", QUYET-DINH, các phiếu cổng A);
- dữ liệu thật cần nạp;
- việc còn lại;
- phụ thuộc ma trận thẩm quyền (chưa bật pháp nhân nào).

Ghi rõ nguồn (tệp:dòng) cho từng ô. Chưa có căn cứ thì ghi "chưa rõ".
