# KK-VUNG-DU-LIEU: bản đồ vùng dữ liệu của các module đang có (CD-018) — chỉ tài liệu

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- **Chỉ tạo một tệp** `docs\46-chuyen-doi-dieu-phoi\KK-VUNG-DU-LIEU.md` trong worktree hiện tại (nhánh `lat/kk-cd018`).
- Không sửa mã, không commit, không mở server/PostgreSQL. Không xóa file.
- Không đọc `var\`, tệp bí mật, dữ liệu thật. Không in DSN.
- Chỗ chưa rõ: ghi mục "Cần lead".

**Căn cứ (đọc):**
- `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` mục **CD-018** (và CD-017, CD-019).
- `D:\Claude\Phan mem ho tro ke toan\53-kien-truc-xuong-song-engine-module.md` (TL 53, nhất là §7 vùng dữ liệu, §8 dùng chung).
- `docs\46-chuyen-doi-dieu-phoi\KK-XUONG-SONG.md` (chuỗi XS đã chia).
- Mã: `src\kho_tri_thuc\ha_tang\pg_migrations.py` và các hằng SQL trong `src\kho_tri_thuc\k2\sql_*.py` (schema, bảng, hàm, GRANT, RLS); mã Python truy vấn (`k2\`, `m2\`, `m3\`, `m4\`, `m9\`, `giao_dien\crm_g.py`, `giao_dien\m4.py`, `giao_dien\server.py`, `tri_thuc\`…).

**Việc:** tài liệu gồm:
1. **Bảng tóm tắt 1 trang** (để lead báo Anh): module × vùng ghi riêng × vùng ghi chung (qua hàm gì) × vùng đọc danh mục chung × vùng đọc của module khác × **chỗ đọc/ghi chéo trực tiếp cần sửa** (đếm số chỗ). Module: CRM, M2, M3, M4, M9, M0 (lõi/master/nhật ký) và các phần chung (K2 MTQ, bus `bus`, nhật ký).
2. **Chi tiết theo module:** danh sách schema/bảng/khung nhìn/hàm SQL mà module **ghi** và **đọc**, kèm tệp:dòng nơi mã chạm tới. Phân loại theo 4 vùng của CD-018 mục 1:
   - ghi riêng = schema/bảng của chính module;
   - ghi chung chỉ qua hàm xương sống (sự kiện, liên kết chứng từ, việc chờ/duyệt, kho file);
   - đọc danh mục chung (pháp nhân, đối tác, tài khoản, người dùng…);
   - đọc dữ liệu công bố của module khác + sự kiện đăng ký nhận.
3. **Chỗ đọc/ghi chéo trực tiếp** (module A SQL thẳng vào bảng của module B): liệt kê tệp:dòng, mức (đọc/ghi), đề xuất thay bằng gì (khung nhìn công bố, hàm xương sống, sự kiện). Không đề xuất dừng việc đang chạy; chuyển dần khi chạm tới.
4. **Role PostgreSQL hiện có** (`app_web`, `ktt_*`…) và đề xuất **một role mỗi module** theo bản đồ (tên role, GRANT gì) — chỉ đề xuất, chưa viết SQL.
5. **Đề xuất chia lát XS-5** (mỗi lát ≤ 3 tệp kể cả test; lát SQL dùng migration append tên tạm `M00xx_*`):
   - XS-5a: khai báo vùng dữ liệu trong mô hình khai báo module XS-4a (`ha_tang\khai_bao_module.py`);
   - XS-5b: role PG theo module trên DEMO;
   - XS-5c: test so mọi bảng/khung nhìn module chạm tới (bắt từ SQL chạy test) với bản đồ — lệch là đỏ;
   - màn quản trị Admin xem bản đồ.
   Ghi phụ thuộc giữa lát và lát nào đụng tệp dùng chung (`server.py`, `pg_migrations.py`, `khung_khai_bao.py`, `app.js`).
6. **"Cần lead"**.

Tối đa khoảng 4 trang. Nêu số đếm, không in dữ liệu. Không đề xuất ngoài TL 53/CD-018.
