# MTQ-5a vòng 2: điểm nên sửa của review (sửa trước khi gộp, vì seed vào DEMO của Anh không gỡ được)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-5a` (8d635b1).
- Căn cứ: thiết kế `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md` §5.1, đoạn "Mức đọc nhạy cảm".

**Việc:**
1. `k2/mtq_demo.py`: mẫu tick của **Người xem** phải tick **Xem màn gốc**, không chỉ màn con nhạy cảm.
   - Phòng Dự án: có Xem `M4 HO_SO`, không chỉ `PDF_DA_DUYET`.
   - Phòng Kế toán: có Xem `M1 TIEN`, không chỉ `XEM_TIEN`.
   - Rà các vai và phòng khác theo cùng nguyên tắc: màn con nhạy cảm không thay cho màn gốc.
   - Cập nhật test tĩnh tương ứng.
2. `k2/crm_khoi_dong.py`: log khi seed lỗi ghi thêm sqlstate hoặc mã `MTQ_*` đã làm sạch, không chỉ tên lớp lỗi. Không ghi dữ liệu, không ghi DSN.
3. `tests/test_mtq_demo.py`: thêm ca PG cho lớp chặn "không phải DEMO".
   - Trong một giao dịch sẽ bị hủy, chèn một pháp nhân không có tiền tố `PN_DEMO_`, gọi seed, khẳng định trạng thái `KHONG_PHAI_DEMO` và không ghi dòng nào (so ảnh chụp số dòng các bảng MTQ trước và sau).
   - Thêm ca thiếu dấu seed CRM DEMO.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_demo tests.test_crm_khoi_dong`, với PYTHONPATH=`src;.;tests`.

**Tệp (≤ 3):** `k2/mtq_demo.py`, `k2/crm_khoi_dong.py`, `tests/test_mtq_demo.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[MTQ-5a] vòng 2: …`.
