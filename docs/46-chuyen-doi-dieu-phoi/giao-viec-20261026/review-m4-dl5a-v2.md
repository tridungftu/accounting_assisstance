## Review Codex (chỉ đọc) — M4-DL5a vòng 2 · 26/10 ~16:10

- **(a) Đạt:** kiểm quyền trên chính `c`, không mở rộng quyền của từng luồng; các cổng `review_kiem`/`duyet_kiem`/`kt_kiem` vẫn giữ nguyên. `nguon_review.py:625`, `xay_dung.py:954`, `duyet_dot.py:414`, `ghi_nhan_nghiem_thu.py:25`.
- **(b) Đạt:** `sha_nay=None` khi `FAILED` đúng hợp đồng SQL: không xét STALE cho FAILED, không công bố kết quả và cột SHA cho phép NULL. `xay_dung.py:957`, `sql_review.py:115`, `sql_review.py:341`.
- **(c) Đạt:** ba trạng thái không có bản chụp trả nguyên đối tượng basis; test kiểm cả byte và SHA. `nguon_review.py:632`, `test_m4_review_compute.py:838`.
- **(d) Đạt:** chỉ kiểm trùng PL chéo hai nguồn; PL cùng nguồn cùng ngày để vendor xếp; THAY/BO kiểm trên tập gộp. Parity so với SQLite độc lập tại hai ngày. `nguon_review.py:652`, `nguon_review.py:683`, `test_m4_review_compute.py:1114`, `test_m4_review_compute.py:1148`.

**Kết luận vòng 2: Đạt trong phạm vi được giao; không có điểm Chặn.** Các số dòng trên thuộc `lat/m4-dl5a`.

| Nội dung kiểm | Kết luận |
|---|---|
| **1. Phạm vi** | **Đạt:** đúng ba tệp được giao, fixture DEMO; báo cáo khớp phần sửa. Số test/skip dựa trên báo cáo worker và gate lead Anh cung cấp; tôi không chạy lại. |
| **2. Đúng yêu cầu** | **Đạt:** hai Chặn và các điểm 3–6 vòng 1 đã xử lý: bỏ giao dịch phiên phụ, đóng lỗi đọc nguồn, kiểm xung đột và lọc basis, bỏ dữ liệu lặp. `xay_dung.py:699`, `xay_dung.py:960`, `nguon_review.py:604`, `nguon_review.py:702`. |
| **3. Tiền, số liệu, quyền** | **Đạt:** giữ đường chuyển số/NULL và thuật toán vendor; quyền kiểm ở máy chủ. Test parity đối chiếu BOQ, tham số và kết quả P/B. `nguon_review.py:739`, `nguon_review.py:760`, `test_m4_review_compute.py:1107`. |
| **4. Không phá phần cũ** | **Đạt:** `_tx_review` trở về `yield c`; không sửa vendor hay thêm gọi API AI trực tiếp. Gate lead: thuần 123 đạt; PG 228 đạt/12 module, không lỗi mới, skip khớp nền; tám lỗi fallback đã hết. |
| **5. Câu cho người dùng** | **Đạt:** thông báo xung đột dùng câu nghiệp vụ trung tính, bỏ “Cần Anh/lead”; diff không thêm hiển thị ngày/tiền. `xay_dung.py:853`, `nguon_review.py:715`. |

**Chặn / Nên sửa / Để sau:** không có điểm cần ghi thêm trong vòng này.

**Hỏi Claude:** Không có.
**Lead lọc (Claude):** Đạt, không lọc. Kiểm xác suất: co.
