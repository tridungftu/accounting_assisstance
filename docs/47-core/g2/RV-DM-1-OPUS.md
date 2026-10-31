# Review Opus DM-1 — Kết luận: Cần sửa, không Chặn (31/10 ~09:30)

Nhánh `lat/dm-1`. PG: test_dm_1 18/18; G2-06/07/12/13/13b/20 đạt.

| # | Mức | Phát hiện | Tệp:dòng | Xử lý |
|---|---|---|---|---|
| 1 | Cần sửa | `demo_kiem_tap_noi_bo` đòi READ COMMITTED **cả khi tập chỉ có 1 pháp nhân**. Kết quả: ghi danh mục trong REPEATABLE READ nay ra `DEMO_CAN_READ_COMMITTED` thay cho `DANH_MUC_CAN_READ_COMMITTED` (hoặc thay cho việc ghi được); `kiem_khoa_ky_v2` SUA ra `LIEN_KET_…` thay `DANH_MUC_…`. Chỉ đòi READ COMMITTED khi ≥ 2 pháp nhân khác nhau; thêm ca DANH_MUC vào test thứ tự kiểm. | 023:73-75, 250-258; 012:291, 330-331, 417-420 | v4 |
| 2 | Nên sửa | Audit đổi cờ không ghi hướng đổi (bật / tắt DEMO). | 023:205 | v4 |
| 3 | Nên sửa | Bảng cài sau 023 chưa có hàm gắn rào chắn dùng chung → sau khi cài module đầu tiên, **không pháp nhân nào đổi cờ được** (`DEMO_SCHEMA_CHUA_BAO_VE`), chặn DM-3; ghi chéo trong bảng module mới không có trigger. Cần hàm Core gắn trigger / quyền đọc / policy vai kiểm cho bảng mới, để G2-25 / Module Manager gọi; test `DEMO_SCHEMA_CHUA_BAO_VE`. | 023:3-4, 144-149, 165-175 | v4 + G2-25 gọi |
| 4 | Nên sửa | Kiểm "đã có dữ liệu" chỉ nhận bảng có cột `phap_nhan_id`; test chỉ thử `phap_nhan_boi_canh`. Thêm ca dữ liệu trong `loi_tai_lieu` và `mod_*`; ghi rõ quy ước bảng module phải có cột `phap_nhan_id`. | 023:136-153; test:241-250 | v4 |
| 5 | Để sau | Policy `demo_chu_doi_co` mở UPDATE mọi cột `loi.phap_nhan` cho owner (hiện không có đường vòng). | 023:37-39 | Ghi nợ |
| 6 | Để sau | Gắn policy / trigger bằng vai provisioning siêu quyền, không theo owner từng khối như 013. | 023:41-61, 164-175 | Ghi nợ (bộ cài không siêu quyền) |
| 7 | Để sau | `phap_nhan_pham_vi` chỉ cấp `vai_chay_loi`; lát báo cáo / xuất Junsky dưới vai module cần cấp thêm. | 023:212-217 | G2-25 / lát xuất |
| 8 | Để sau | Thêm truy vấn catalog + SELECT mỗi FK + advisory lock cho mỗi dòng ghi → đo khi DM-3. `DEMO_SCHEMA_CHUA_BAO_VE` nên 409. | 023:92-122; py:19-20 | 409 làm ở v4; đo ở DM-3 |

**Đạt:**
- đổi cờ qua DEFINER Admin + CAS + audit + advisory;
- có dữ liệu thì từ chối hai chiều;
- trigger `aaa_demo_lien_ket` chạy trước, chặn ghi chéo, MTQ đa pháp nhân chặn được;
- không đường vòng DEFINER;
- owner / `search_path` / REVOKE đúng; vai kiểm NOLOGIN, không thành viên;
- không sửa 001–022;
- test login thật + FORCE RLS, không xanh giả.
