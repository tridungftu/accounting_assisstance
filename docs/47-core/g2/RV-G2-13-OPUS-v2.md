# Review Opus G2-13 vòng 2 — Kết luận: Đạt (31/10 ~00:50)

Phạm vi: `git diff 9a0fa56 lat/g2-13` (vòng 3 `5225511` + vòng 4 `3a2f6bc`), 3 tệp. PG: test_g2_13 31/31, test_g2_12 23/23.

**Đã đóng:** 1 Chặn (khóa mọi chứng từ), 3 Cần sửa, 4 Nên sửa của `RV-G2-13-OPUS.md`.
- khóa chỉ `p_ids` đã sắp xếp; test kiểm bằng `pg_locks`;
- hàm kiểm trả boolean, ràng `current_user` = `vai_kiem_toan_ven_mod_<module>`;
- 4 hàm nội bộ buộc `p_pn ∈ mtq_phien_rls()`; chặn policy RESTRICTIVE;
- HUY không gọi resolver, không kiểm tiền;
- đọc `cu` trước rồi khóa hợp;
- `ghi_v2` thay thế giống 012, chỉ thêm khóa;
- test kiểm đúng mã / sqlstate, 55P03 tách riêng, có 60+60 phía chứng từ.

| Mức | Phát hiện | Tệp:dòng | Xử lý |
|---|---|---|---|
| Nên sửa | Tra resolver không ràng một dòng (nhiều contract cùng `dang_dung` → chọn ngẫu nhiên). Đếm dòng, khác 1 → RAISE / `CHO`. | 013:64-69 | Lát **G2-13b** |
| Để sau | Kiểm wrapper module chưa xét EXECUTE PUBLIC / login, chưa kiểm `vai_kiem_toan_ven_mod_X` không có thành viên. G2-25 phải cấp `USAGE loi` + `mtq_phien_rls()` cho role kiểm module. Trước G2-25 **không có lỗ**: chỉ superuser tạo wrapper; thiếu wrapper → đóng cửa. | 013:9-13, 160-173 | Ghi vào đề giao **G2-25** |
| Để sau | Boolean với ngưỡng do người gọi đưa vào vẫn dò được tổng bằng chia đôi — chỉ role kiểm của chính module. | 013:191 | **Rủi ro chấp nhận** |
| Để sau | `LIEN_KET_CAN_READ_COMMITTED` không có trong `_LOI` của `danh_muc.py` → ra `DANH_MUC_THAT_BAI` (vẫn đóng cửa). | 013:304; danh_muc.py:30 | Gộp vào **G2-13b** |
| Để sau | Không có vòng khóa giữa các đường (đều lấy khóa pháp nhân trước); giao dịch ngoài giữ khóa khác → PG báo 40P01. | 013:14-16 | Đã có trong mục khóa hẹp |
