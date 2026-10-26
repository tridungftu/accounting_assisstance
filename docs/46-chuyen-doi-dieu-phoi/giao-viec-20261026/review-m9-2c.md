## Review Codex (chỉ đọc) — m9-2c · 26/10 ~17:27

(a) **Đạt — chỉ Local AI:** `src/kho_tri_thuc/m9/dich_vu_hoi_dap.py:22` gọi qua `hoi_dap_vay.tra_loi`, giữ định tuyến `HOI_DAP_VAY` chỉ Local. Không thêm đường Cloud/Mask; grep M9 không có chuỗi cấm.

(b) **Đạt — nhật ký một lần/lượt:** `src/kho_tri_thuc/m9/dich_vu_hoi_dap.py:25` chỉ gọi một callback, ghi đúng các khóa yêu cầu; không đưa câu trả lời hoặc nội dung câu trích vào bản ghi.

(c) **Đạt — câu hỏi rỗng không gọi cổng:** `src/kho_tri_thuc/m9/dich_vu_hoi_dap.py:21` bỏ tìm kiếm khi rỗng/trắng; danh sách trích dẫn rỗng khiến tầng trả lời trả `KHONG_THAY` trước khi gọi AI. Test tại `tests/test_m9_dich_vu_hoi_dap.py:88`.

(d) **Đạt — truyền đúng bộ lọc:** `src/kho_tri_thuc/m9/dich_vu_hoi_dap.py:20` chuyển nguyên `loc_tai_lieu`; test kiểm cả đúng đối tượng tại `tests/test_m9_dich_vu_hoi_dap.py:107`.

Năm kết luận kiểm tra:

- **Phạm vi: Đạt.** Diff chỉ thêm hai tệp được giao; dữ liệu DEMO trong bộ nhớ. Báo cáo worker khớp số test: 9 mới + 16 + 30 = 55, không có skip khai báo.
- **Đúng yêu cầu: Đạt.** Nối tìm kiếm → trả lời, giữ nguyên đối tượng kết quả; nhật ký giờ Việt Nam ISO UTC+07:00.
- **Tiền, số liệu, quyền: Đạt trong phạm vi lát.** Không thêm phép tính tiền; chuyển bộ lọc xuống chỉ mục và ghi rõ trách nhiệm lọc quyền thuộc tầng gọi.
- **Không phá phần cũ: Đạt.** Không sửa mã cũ, không thêm lời gọi API trực tiếp.
- **Giao diện/câu người dùng: Đạt.** Không thêm giao diện hoặc thông báo kỹ thuật cho người dùng.

**Chặn: 0 · Nên sửa: 0 · Để sau: 0. Hỏi Claude: không có.**

**Kết luận: Đạt, có thể gộp.** Tôi chưa chạy lại test; gate **73 đạt, 0 lỗi, 0 skip** là kết quả runner Anh cung cấp.
**Lead lọc (Claude):** Đạt, không lọc. Kiểm xác suất: khong.
