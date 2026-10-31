# MD-1 — khung dự án module mẫu `Module\_mau\` (CD-043)

**Vị trí:** `D:\Claude\Phan mem ho tro ke toan\Module\_mau\` — git riêng, nhánh `chinh`, lead đã tạo. Bạn làm việc trong thư mục đó.

**Căn cứ:**
- CD-043 (`docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`);
- chuẩn SDK v1.1 (`docs\47-core\chuan\CHUAN-CORE-SDK-v1.0.md`): §3.8 `module.json` mẫu đầy đủ, §3.10 `contract/`, §3.13 cài / nâng cấp;
- G2-24 kiểm gói (`src\kho_tri_thuc\core\goi.py`), G2-25 áp gói (`core\kich_hoat.py`) — đọc để gói mẫu **qua được** kiểm gói;
- CD-044 (bảng có dữ liệu theo pháp nhân phải có cột `phap_nhan_id`).

**Tạo** (mỗi thư mục có tệp tối thiểu, dữ liệu DEMO):
- `module.json`: mã `mau_demo`, phiên bản, khai SDK / Core tương thích;
- `contract\` (1 contract mẫu + ví dụ);
- `migrations\001_khoi_tao.sql` (1 bảng có `phap_nhan_id`);
- `backend\` (1 handler mẫu dùng SDK);
- `frontend\` (1 trang nội dung dùng SDK JS, không tự dựng khung);
- `quy_trinh\`;
- `tests\`;
- `README.md` 1 trang;
- `CHANGELOG.md`;
- `dong_goi.py`: script đóng gói ra `dist\mau_demo-<phiên bản>.zip` kèm SHA256, chỉ thư viện chuẩn.

**Kiểm:** chạy `dong_goi.py` ra gói. Gói qua được bộ kiểm G2-24, gọi hàm kiểm gói từ repo Core bằng đường dẫn chỉ đọc. Ghi lệnh kiểm vào `README.md`.

Không sửa repo Core. Không commit (lead commit).

Báo cáo ≤ 3 dòng.
