**Biên bản review chéo OCR-2 — Kết luận: Đạt**

Nhánh `lat/g3-ocr-2`, HEAD `c204c7c`; commit triển khai `11ce9a8`. Đối chiếu với `hop-nhat-20261023`, đề OCR-2, kế hoạch, chuẩn Core và đặc tả G1.

Các đường dẫn `engines/…` dưới đây thuộc `src/kho_tri_thuc/`.

| Nội dung kiểm | Kết quả và căn cứ |
|---|---|
| Phạm vi | **Đạt.** Diff đúng 3 tệp whitelist: `engines/e_ocr/van_ban.py`, `engines/e_ocr/engine.json`, `tests/test_g3_ocr_2.py`. |
| Dùng lại nguồn | **Đạt.** Gọi cổng `CongOCR` được tiêm, bọc parser gốc; không viết lại OCR, không import `app.py`, không hiệu đính. Callback rỗng chặn OCR ảnh nhúng; dùng `embedded_pages=[]`. `van_ban.py:105–119`. |
| Contract và nguồn | **Đạt.** Trả `van_ban_tai_lieu.v1`, giữ revision, ID nguồn, hash/kích thước DOCX và định vị logic. `trang=[]` phù hợp đặc tả §5 khi DOCX không có phân trang xác định; không tự chuyển thành đã duyệt. `van_ban.py:126–152`. |
| Manifest | **Đạt.** Chỉ khai `ocr.trich_van_ban@1`, có adapter và test; không khai trích bảng. `headless=false`, ngoại lệ đúng `CD-038-ENGINE-3A`, `login_csdl=false`. `engine.json:9–32`; `test_g3_ocr_2.py:230–249`. |
| Chuẩn và an toàn | **Đạt trong phạm vi lát.** Không thêm SQL, GRANT, DEFINER hoặc kết nối CSDL; kiểm role/RLS/`search_path` và login thật không áp dụng. Không thêm thao tác xóa hay log/audit chứa bí mật. Fixture DEMO, cổng giả; ca dùng `CongOCR` thay seam Hot Folder và bật guard không xóa. `test_g3_ocr_2.py:78–96`, `302–315`. |
| Test kiểm đúng hành vi | **Đạt qua đọc mã.** Có kiểm schema đầu ra, nguồn/hash/revision, MIME, metadata sai, hết hạn, hủy, không retry, lỗi parser và khối trùng. Nhóm parser nguồn kiểm DOCX có bảng/header/ảnh nhúng, Track Changes và bảng lồng. `test_g3_ocr_2.py:100–300`. |

| Phát hiện | Mức | Tệp:dòng |
|---|---|---|
| Không phát hiện lỗi cần sửa trong diff và phạm vi được giao. | — | — |

**Xác minh:** `git diff --check` đạt. Reviewer chỉ đọc, không chạy lại test/runtime, không gọi ABBYY thật, không đọc kho thật, tệp bí mật hoặc `*.local.json`. Kết quả test thuần đạt dựa trên thông tin lead cung cấp; nhóm parser nguồn và meta-schema có điều kiện skip rõ ràng, không tính skip là đạt.