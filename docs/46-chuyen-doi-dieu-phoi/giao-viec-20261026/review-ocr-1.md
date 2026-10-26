## Review Codex (chỉ đọc) — ocr-1 · 26/10 ~17:37

- **(a) Đạt** — `src/kho_tri_thuc/ha_tang/cong_ocr.py:151,164,203,375`: sổ `[epoch, trang]`, cửa sổ 30 ngày; kiểm tổng chung và giữ chỗ trước khi đưa tệp.
- **(b) Đạt theo phương án lead đã duyệt** — `cong_ocr.py:71,179,182,191,192`: khóa liên tiến trình, ghi atomic, gộp giữ số lần xuất hiện của bản ghi, kiểm sau ghi và thử phục hồi một lần. Rủi ro Review không tham gia khóa đã được chấp nhận và ghi tại dòng 7.
- **(c) Đạt** — `cong_ocr.py:100,229,241,277`: mã `hd…_hex6`; nhận, rút và dọn theo đúng mã việc.
- **(d) Đạt** — `cong_ocr.py:128,137,195,390`: đường dẫn nhận từ bên gọi; thông báo lỗi/log không chứa đường dẫn hoặc nội dung tài liệu.
- **(e) Đạt** — `src/kho_tri_thuc/m9/ocr_hot_folder.py:14,20,36`: giữ cách gọi `HotFolderM9.ocr(...)`, ánh xạ lỗi về `M9_OCR_*`.

Các vị trí `cong_ocr.py` trên thuộc `src/kho_tri_thuc/ha_tang/`, dòng theo nhánh `lat/ocr-1`.

| Kiểm tra bắt buộc | Kết luận |
|---|---|
| **1. Phạm vi** | **Đạt.** Đúng 4 tệp được phép sau bổ sung của lead; fixture dùng DEMO/thư mục tạm. Báo cáo khớp diff và số ca khai báo: 20 mới + 21 M9; worker ghi rõ NOT_RUN. |
| **2. Đúng yêu cầu** | **Đạt.** Cổng chung nhận cấu hình sổ/Hot Folder/đệm; adapter M9 và các tình huống kiểm thử được giao đều có. |
| **3. Tiền, số liệu, quyền** | **Đạt trong phạm vi lát.** Tổng trang được kiểm trong khóa sổ, kiểm lại sau gộp; hoàn theo bản ghi giữ chỗ. Không thay đổi tiền hoặc quyền. |
| **4. Không phá phần cũ** | **Đạt qua đối chiếu diff và gate lead cung cấp.** Giữ xử lý đệm, hủy, timeout và lỗi M9; không thêm gọi mạng/API AI. |
| **5. Giao diện/câu người dùng** | **Đạt.** Thông báo tiếng Việt, không đưa mã việc/đường dẫn vào câu lỗi; không có trường ngày hoặc tiền mới. |

**Kết luận: Đạt — không có Chặn, Nên sửa hoặc Để sau.** `git diff --check` đạt. Tôi không chạy test vì phiên review chỉ đọc; gate do lead cung cấp: guard **28 OK / 13 skip** ở phần kiểm dọn, Python thường OK.

**Hỏi Claude:** Không.
**Lead lọc (Claude):** Đạt, không lọc. Kiểm xác suất: khong.
