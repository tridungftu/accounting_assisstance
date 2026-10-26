# KK-MA-HOA-LUU-RIENG: cột nhạy cảm, mã hóa, sao lưu, đo BitLocker (CD-019) — chỉ tài liệu

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- **Chỉ tạo một tệp** `docs\46-chuyen-doi-dieu-phoi\KK-MA-HOA-LUU-RIENG.md` trong worktree hiện tại (nhánh `lat/kk-cd019`).
- Không sửa mã, không commit, không mở server/PostgreSQL, không chạy pgbench. Không xóa file.
- Không đọc `var\`, tệp bí mật, dữ liệu thật, `.env`. Danh sách cột lấy **từ mã/schema**, không từ dữ liệu. Không in DSN.
- Chỗ chưa rõ: ghi mục "Cần lead".

**Căn cứ (đọc):**
- `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` mục **CD-019** (và CD-016, CD-018).
- `D:\Claude\Phan mem ho tro ke toan\53-kien-truc-xuong-song-engine-module.md` §8.
- `docs\46-chuyen-doi-dieu-phoi\KE-HOACH-CHUYEN-KHO-THAT-SQLITE-PG.md`, `CHECKLIST-PHAT-HANH.md`, `KK-VUNG-DU-LIEU.md`.
- Mã: `src\kho_tri_thuc\ha_tang\pg_migrations.py`, `k2\sql_*.py`, `m4\sql_*.py`, schema SQLite cũ (`ha_tang\database.py`, `ha_tang\feature_migrations.py`), `tools\cai_postgres.ps1` và các script sao lưu hiện có (nếu có).

**Việc:** tài liệu gồm:
1. **Danh sách cột nhạy cảm để Anh duyệt** (bảng: schema.bảng.cột · module · loại dữ liệu · mức đề xuất A = mã hóa ngay / B = cân nhắc / C = không mã hóa · lý do). Ít nhất: số CCCD/CMND/hộ chiếu, số ĐKDN/mã số thuế cá nhân, số tài khoản ngân hàng, số điện thoại/email cá nhân, địa chỉ cá nhân, lương/thu nhập cá nhân. Ghi rõ cột nào đang dùng để **tìm/khớp/UNIQUE/JOIN/RLS** (ví dụ khớp sao kê theo số tài khoản) và cách giữ được chức năng đó khi mã hóa (cột băm tra cứu HMAC riêng, hiển thị che một phần…). Số tiền, ngày: **không** mã hóa (TL 48: không che số tiền/ngày).
2. **Thiết kế mã hóa cột bằng pgcrypto:** hàm dùng, nơi gọi (SQL hay Python), định dạng lưu, cột phiên bản khóa; **khóa nằm ngoài CSDL và ngoài thư mục phần mềm** (đề xuất vị trí cụ thể dưới `D:\DU-LIEU-KE-TOAN\` hoặc nơi khác, quyền NTFS, có/không DPAPI); chỉ code đọc lúc chạy; rủi ro khóa lọt qua nhật ký câu lệnh PostgreSQL (`log_statement`, `pg_stat_activity`, lỗi) và cách chặn; **xoay khóa** (thêm phiên bản, mã hóa lại theo lô, kiểm đủ). Không thêm thư viện ngoài nếu pgcrypto/thư viện chuẩn làm được (CD-019).
3. **Sao lưu mã hóa:** công cụ (pg_dump + công cụ mã hóa sẵn có trên máy — nêu công cụ nào đã có, không giả định cài mới), nơi lưu `D:\DU-LIEU-KE-TOAN\sao-luu\`, khóa giữ riêng khác khóa cột, lịch, đề xuất chép thêm ra ổ khác/ổ ngoài định kỳ; **hướng dẫn khôi phục** từng bước và **kịch bản thử khôi phục một lần** (trên CSDL thử, đo thời gian, so số dòng/tổng kiểm soát).
4. **Bộ đo trước BitLocker:** danh sách phép đo lặp lại được (pgbench cấu hình cụ thể + vài thao tác lưu thật của phần mềm trên DEMO: nhập hóa đơn XML, lưu hồ sơ M4, lưu báo giá CRM…), số lần chạy, cách ghi kết quả, ngưỡng chênh lệch đáng báo Anh. Chạy trên `D:\DU-LIEU-KE-TOAN` (cụm DEMO tạm hoặc bản sao), không đụng cụm DEMO đang dùng khi lead chưa bố trí.
5. **Chuyển cụm DEMO ra ngoài thư mục phần mềm** (CD-019 mục 3, không gấp): các bước, điểm dừng an toàn, cách không làm gián đoạn cổng A. **SSL**: một dòng thêm vào checklist chuyển lên máy chủ.
6. **Chia lát code** (mỗi lát ≤ 3 tệp kể cả test, SQL append `M00xx_*`), thứ tự, phụ thuộc vào XS-5b (role theo module) và kế hoạch chuyển kho thật.
7. **"Cần lead"** và **câu cần Anh chốt** (tách riêng, câu ngắn, có phương án đề xuất).

Tối đa khoảng 4 trang. Nêu số đếm, không in dữ liệu.
