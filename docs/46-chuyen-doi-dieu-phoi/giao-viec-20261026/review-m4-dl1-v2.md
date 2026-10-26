# Review M4-DL1 vòng 2 (review-lat, Opus) — 26/10/2026 ~11:00

**Kết luận: ĐẠT, không còn điểm Chặn.** Hai điểm Chặn vòng 1 đã sửa:
- HĐ nguồn theo **lần chụp riêng** (`m4.review_chep_hop_dong`), không còn một nguồn bất biến duy nhất cho mỗi HĐ.
- Tiền và số lượng dùng `numeric`, không còn `double precision`.

**Nên sửa (chuyển sang lát M4-DL2, vì DL1 đã gộp là M0038 và chưa CSDL bền nào chạy):**
1. UNIQUE `(nguon_id, hop_dong_id)` cho bảng chụp HĐ: không ghi trùng một HĐ trong cùng một lần chụp.
2. Cột `chup_luc` riêng, NOT NULL, **không** mặc định `now()`. Giá trị lấy từ thời điểm chụp tệp nguồn, không phải lúc nạp.
3. Quy tắc "bản hiện hành" tính cả HĐ đã bị xóa ở lần chụp sau: HĐ không còn trong lần chụp mới nhất thì không hiện là đang có.
4. DTO đọc ra màn hình không lộ `file_nguon`, đường dẫn tệp hay mã kỹ thuật.

**Điều kiện gộp (lead):**
- [x] Chạy 11 test PG: 67 ok, 0 mã lỗi mới so với nền v3.
- [x] Cấp số migration: **M0038** (sau M0037 KY-G5TAY, trước M0039 MTQ-1).
- [x] Không CSDL bền nào chạy migration v1: chưa mở server DEMO nào trên `lat/m4-dl1`; CSDL test `kho_test_*` đã tự xóa.

**Cần Anh** (đã có trong báo cáo): bảng ánh xạ `ma_hd → hợp đồng / pháp nhân / dự án` trước khi nạp dữ liệu thật (CD-011).
