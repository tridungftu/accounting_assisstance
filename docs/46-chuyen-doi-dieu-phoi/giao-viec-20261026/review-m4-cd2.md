## Review M4-CD2 · M4 · Nghiệm thu & chi phí dự án (commit 5183ab6) — review-lat (Opus), 26/10 ~15:10

**Kết luận: Đạt.** Không có điểm phải sửa trước khi gộp.

1. **Đúng yêu cầu: Đạt.**
   - Đủ các phép so: số dòng 12 bảng, từng ô, khóa thiếu mỗi phía, trùng khóa, tổng theo HĐ/BOQ (GOC/THAY/THEM/BO) và theo đợt, số HĐ có cờ DL3.
   - Độc lập với bộ nạp: tự khai cột/khóa, đọc lại SQLite, đọc PG trong `REPEATABLE READ, READ ONLY`. Không dùng hàm của bộ nạp.
2. **Tiền/số liệu/quyền: Đạt.**
   - `Decimal(str(x))`, so chính xác không dung sai. NULL khác 0.
   - Lệch bù trừ giữa 2 HĐ, giữa 2 đợt và giữa 2 dòng cùng đợt đều bị bắt, có test tĩnh và PG.
3. **Không phá phần cũ: Đạt.**
   - Chỉ 3 tệp, không có đường Cloud.
   - Thuần 37 ok / 9 skip; PG (lead) 128 ok, 0 mã mới.
   - Nguồn mở `mode=ro&immutable=1` + `query_only`, từ chối khi có WAL.
   - Mã thoát: lệch 2, lỗi 1. Test PG tạo CSDL `kho_test_*` riêng.
4. **Báo cáo worker khớp diff: Đạt.**

**Nên sửa (không chặn gộp) → lát M4-CD2b, làm trước lần nạp dữ liệu thật:**
1. `tools/chuyen_review_sqlite_sang_pg.py:404–405`: khi có `--doi-chieu`, mọi lỗi đều báo như lỗi đối chiếu, kể cả lỗi ở bước nạp (đã hoàn tác). HOAN_TAT (dòng 379) chỉ in sau đối chiếu, nên đối chiếu lỗi thì mất số đếm nạp. Sửa: thêm cờ giai đoạn, in HOAN_TAT ngay sau `ghi_pg`, thông báo theo giai đoạn.
2. `m4/review_doi_chieu.py:151–157`: chưa đếm riêng dòng mồ côi (§5.1.3) và chưa đọc `hop_dong_id` ở PG. Ở `canh_bao`, `nhat_ky`, `khop_hang_muc`, dòng mồ côi bị gán HĐ hoặc dòng gán nhầm HĐ sẽ không bị phát hiện. Sửa:
   - thêm `so_dong_mo_coi` cho từng bảng ở hai phía;
   - kiểm mồ côi ⇒ `hop_dong_id` NULL;
   - kiểm không mồ côi ⇒ `hop_dong_id` đúng HĐ cùng `ma_hd`.
3. `m4/review_doi_chieu.py:204–206`: đưa `tong_sqlite == tong_pg` vào `khop`, kèm danh sách HĐ/đợt lệch tổng.
4. Thủ tục khi chạy thật: `tung_hd[]`/`tung_dot[]` là số tiền từng HĐ/đợt. Ghi stdout ra tệp ngoài git; chat chỉ nêu `trang_thai`, `so_dong_loi`, số đếm từng bảng, `so_hd_can_xem_lai`, tổng chung.

**Để sau:**
5. `:198` ngày cắt cờ DL3 theo múi giờ phiên PG, chưa cố định giờ Việt Nam.
6. `:90–109` chưa so SHA256 tệp nguồn với `review_chep_nguon.mo_ta`; nên in `sha256_khop`.
7. Ba điểm nhỏ:
   - mã thoát 2 trùng mã lỗi argparse;
   - vòng lọc lồng `:118–136`, `:199–202` chậm với dữ liệu lớn, nên chạy nền;
   - `K000001` không truy ngược về khóa nguồn.
