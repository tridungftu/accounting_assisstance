## Review M4-DL5b (a877282) — review-lat (Opus), 26/10 ~15:55 · PG lead 15:19: 0 mã mới, 0 skip

**Kết luận: Cần sửa.** 1 điểm chặn.

**Chặn**
1. **Cộng khối lượng khác ĐVT** (`m4/duyet_dot.py:240-262`, `gom_lich_su_review_chep`). Số được gộp theo mã HM mà không xét ĐVT.
   - Reviewer thử: seal đợt 2 mã HM ĐVT `m2` = 100, seal đợt 3 ĐVT `m3` = 7, Review = 5 → trả **CO = 112**. Kiểm kê §5.1(6) cấm cộng lượng khác ĐVT.
   - Sửa phía seal: dòng seal có `dvt` (`sql_duyet.py:479`), dòng `_dong` hiện tại cũng có `dvt`. So ĐVT giữa các seal và với dòng hiện tại; khác hoặc thiếu → `None` + `INCOMPLETE`.
   - Sửa phía Review: `review_chep_kl_thanh_toan` không có ĐVT. Lấy ĐVT từ `review_chep_boq_dong` (cùng HĐ, mã HM, bản chụp), hoặc coi chưa rõ → `INCOMPLETE`. Ghi "Cần Anh" phương án đã chọn.

**Nên sửa**
2. `duyet_dot.py:314` (`_gan_lich_su_review_chep`): đợt hiện tại có 2 dòng cùng mã HM thì cả hai nhận cùng một tổng, nhìn như nhân đôi. Mã HM trùng trong `dong_nt` → `None`/`CAN_XEM_LAI`.
3. Phần mới không xét ngày nghiệm thu, trong khi `lich_su_da_duyet` coi đợt trước có ngày NT sau đợt này là INCOMPLETE; hai số đặt cạnh nhau có thể vênh trạng thái. Áp cùng điều kiện ngày, ít nhất cho đợt `M4_SEAL`.

**Để sau / điều kiện gộp**
4. Báo cáo worker ghi skip 37 → 37 nhưng diff thêm 4 test PG. Ghi lại cho đúng.
5. 4 test PG `test_dl5b_*` là bằng chứng duy nhất cho quyền/RLS và 3 trạng thái NULL. Lead: PG 15:19 skip = 0, các test này đã chạy và đạt.

**Đạt**
- Basis (`co`), `truoc_da_duyet`, JSON kết luận/seal giữ nguyên byte; hàm đọc chép không được gọi trong `ket_luan`.
- Seal thắng Review cùng đợt (`bo_qua_trung`).
- `m4_dot_id` lệch hoặc đợt M4 chưa seal → `CAN_XEM_LAI`.
- NULL, không mã HM, mã HM trùng trong seal → `None`/INCOMPLETE.
- Decimal; DTO đổi qua `so_chuan`.
- `LECH_LUY_KE_REVIEW` giữ cả hai số.
- Quyền: đọc trên đúng kết nối/RR của 02C, tự kiểm `master.m4_duoc(...,'XEM')`; 3 trạng thái NULL → None.
- Nhãn trung tính, không lộ ID/đường dẫn/người nạp.
- JS validator không vỡ.
- Đúng 4 tệp, không Cloud.
