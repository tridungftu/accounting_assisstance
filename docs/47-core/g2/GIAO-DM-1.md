# DM-1 — pháp nhân DEMO (`la_demo`) và rào chắn trong CSDL chung (CD-044, review Opus bắt buộc)

**Phần chung:** như `docs\47-core\g2\GIAO-G2-DOT-A.md`, mục "Phần chung". **Nền:** `hop-nhat-20261023` (G2-00…G2-21, 13b, 17b).

Quy ước:
- login thật + phiên xác minh; không DROP;
- **không sửa migration đã phát hành** (001–020);
- test tự áp chuỗi SQL theo số.

**Tệp:**
- `src\kho_tri_thuc\core\sql\023_phap_nhan_demo.sql` (mới; số 023 không trùng lát nào có SQL)
- `src\kho_tri_thuc\core\phap_nhan_demo.py`
- `tests\test_dm_1.py`

**Căn cứ:**
- CD-044 trong `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`;
- dòng "Dữ liệu DEMO trong CSDL dự án" trong `CLAUDE.md` của repo;
- `loi.phap_nhan` ở `002_danh_tinh.sql`;
- RLS theo phiên G2-06 / G2-07;
- cửa ghi V2 G2-12 / G2-13 / G2-20.

**Việc:**
1. **Cờ `la_demo boolean NOT NULL DEFAULT false`** trên `loi.phap_nhan`, thêm qua 023.
   - Đổi cờ chỉ qua hàm Core DEFINER (Admin, CAS, audit).
   - Pháp nhân đã có dữ liệu nghiệp vụ thì **không** đổi cờ được (chặn đổi thật ↔ DEMO).
2. **Không ghi chéo DEMO ↔ thật** bằng ràng buộc CSDL ở các điểm liên kết chéo pháp nhân đang có: liên kết tiền G2-13, MTQ đa pháp nhân G2-06, công bố. Mọi bản ghi liên kết hai đầu phải cùng `la_demo`. Trigger hoặc ràng buộc trong 023, dạng `CREATE OR REPLACE` / thêm, không sửa tệp cũ.
3. **Mặc định loại pháp nhân DEMO:** hàm Core cho tổng hợp / báo cáo / file nhập Junsky trả danh sách pháp nhân phạm vi mặc định **không gồm DEMO**, trừ khi tham số chọn rõ. Viết hàm dùng chung `loi.phap_nhan_pham_vi(p_gom_demo boolean default false)`; các lát xuất / báo cáo sau gọi hàm này.
4. **Python `phap_nhan_demo.py`:** bọc gọi hàm; trả nhãn hiển thị "DEMO" cho giao diện (DM-5 dùng).
5. **Chưa** làm công cụ chuyển (DM-3) hay xóa (DM-4).

**Test PG** (login thật, FORCE RLS):
- đặt cờ đúng quyền / sai quyền; CAS lệch → lỗi; có audit;
- đổi cờ khi đã có dữ liệu → từ chối;
- liên kết tiền / MTQ giữa pháp nhân DEMO và thật → từ chối, có mã;
- `phap_nhan_pham_vi()` mặc định không có DEMO; `true` thì có;
- runtime không ghi thẳng bảng.

Báo cáo ≤ 3 dòng. Lead chạy PG và gọi review Opus.
