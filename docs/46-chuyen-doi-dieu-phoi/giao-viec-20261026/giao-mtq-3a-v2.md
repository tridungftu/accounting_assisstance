# MTQ-3a vòng 2: bảng tick ma trận thẩm quyền, 4 điểm nên sửa của review (sửa trước khi gộp)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-3a` (5f5e82e).
- Máy chủ hiện hành đọc bằng `git show hop-nhat-20261023:src/kho_tri_thuc/k2/ma_tran_tham_quyen.py` và `...:src/kho_tri_thuc/giao_dien/ma_tran_tham_quyen.py`. Bản này đã gồm MTQ-2b: GET `/ma-tran` chỉ Admin, câu lỗi đã đổi, có 503 `MTQ_NHAT_KY_LOI`.

**Việc trong `src/kho_tri_thuc/giao_dien/assets/ma_tran_tham_quyen.js`:**
1. **Hạn mức rất lớn làm màn hỏng.**
   - Nhật ký do trigger ghi `to_jsonb(NEW)`, nên `gioi_han_vnd` về trình duyệt là **số JSON**, có thể vượt 2^53.
   - `money()` trong `auditDetail` báo lỗi làm `render()` dừng giữa chừng. Lệnh vẽ lại ở `load()` (khoảng dòng 284) nằm ngoài khối bắt lỗi, nên các nút bị khóa.
   - Sửa:
     - `auditDetail` và mọi hàm hiển thị tiền **không được ném lỗi**. Nhận cả số lẫn chuỗi; số vượt an toàn thì hiện "Giá trị quá lớn — xem ở máy chủ", không làm tròn sai.
     - `load()` và `render()` bọc lỗi, để màn không bao giờ kẹt ở trạng thái nút vô hiệu.
2. **409:** câu "Đã có người khác sửa, tải lại" chỉ dùng cho `MTQ_REVISION` và `MTQ_IDEMPOTENCY_KHAC`. Các mã khác (`MTQ_THIEU_DONG`, `MTQ_CHUA_NOI_MTQ4`, `MTQ_BAT_BIEN`…) hiện **câu riêng của máy chủ**, không ghép thêm.
3. **503 `MTQ_NHAT_KY_LOI`:** hiện "Chưa ghi được nhật ký, thao tác chưa thực hiện. Báo quản trị."
4. **Câu chữ:**
   - Bỏ xưng "Anh"; dùng "Người dùng đang thực hành không có quyền…" như các màn có sẵn.
   - Người không phải Admin, khi pháp nhân chưa bật ma trận: hiện "Pháp nhân chưa dùng ma trận thẩm quyền; quyền hiện áp dụng theo phân quyền đang có.", không hiện "Chưa có quyền đang áp dụng".

**Test `tests/mtq_bang_tick.cjs`:**
- Dữ liệu mẫu nhật ký ghi hạn mức là **số** như bản thật.
- Thêm ca hạn mức `99999999999999999999` (số JSON) và ca 18 chữ số: màn vẫn vẽ đủ, nút vẫn bấm được sau "Tải lại".
- Sửa ca 409 đang khẳng định câu ghép sai (khoảng dòng 174–181).
- Thêm ca 503.
- Thêm ca câu "chưa dùng ma trận".

**Chạy:** `node tests/mtq_bang_tick.cjs`.

**Tệp (2):** `ma_tran_tham_quyen.js`, `tests/mtq_bang_tick.cjs`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[MTQ-3a] vòng 2: …`.
