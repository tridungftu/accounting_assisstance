# Kết quả review M4-5a + DA-3a vòng 1/2 (Claude, 25/10) — ĐẠT cả hai, không Chặn

## M4-5a (M0033) — Đạt; Nên sửa/Để sau
- A1 Nên sửa `k2/ghi_nhan_chung.py:348`: `max(0, giá trị đợt − số khai)` che khai vượt → thêm cờ `KHAI_VUOT_GIA_TRI_DOT` trong `phan_khai_con_thieu`.
- A2 Nên sửa `k2/ghi_nhan_chung.py:110-114`: khi xác nhận, locator `thanh_phan.{i}.nguon` trỏ danh sách gộp → chỉ gắn khi lưu; xác nhận dùng `$`.
- A3 Để sau: chạy ca PG c11–c18 trên clone M0033 trước khi gộp; danh sách hàm từ chối `app_web` thiếu `_dc_goi_y_hoa_don`, `_dc_dot_goi_y`, `_dc_kiem_tien_tp`, `_dc_so_tien_hop_le`; `_dc_hd_da_gan` quét mọi phiên bản, gợi ý không giới hạn dòng.
- A4 Để sau `:387`: tiền VND dạng "1100000.00" bị từ chối khi đọc tín hiệu chênh tiền → chấp nhận phần lẻ toàn 0.

## DA-3a — Đạt; Nên sửa/Để sau
- B1 Nên sửa (lead quyết) `k2/crm_giao_ket.py:871-880, 1066`: `luu` luôn gọi `_gan_tieu_chuan`, dự án NGUNG_BAN làm nháp cũ không lưu được → chỉ chặn khi tạo mới/đổi dự án/có `lo_id`, còn lại chỉ ghi `khac_tieu_chuan`.
- B2 Để sau (DA-3b) `:1277`: luồng Soạn chuẩn hóa lại làm rơi `nguon_tieu_chuan`/`khac_tieu_chuan`.
- B3 Để sau: `xem_truoc` chỉ tính nguồn chuẩn khi có `lo_id`; ca PG `MacDinhPostgres` cần biến `KTT_DA3A_KET_NOI` — chạy trước khi gộp.
