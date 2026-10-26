# MTQ-3a: Ma trận thẩm quyền, bảng tick ở giao diện (CD-012; thiết kế MTQ-0 §6, dòng MTQ-3a)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md` §4. Giao diện dùng tiếng Việt nghiệp vụ, không hiện mã kỹ thuật; ngày dd/mm/yyyy; tiền có đơn vị.
- Ghi tệp UTF-8 không BOM. Sandbox không ghi được `.git`: **không commit**. Không mở server. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-3a`, dựng từ `lat/mtq-2` (đã có dịch vụ và HTTP).

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md`: §2.1 (năm vai, tên hiển thị), §4.1 (ô khả dụng), §5.2 (hạn mức), §6 (màn hình), dòng MTQ-3a.
- Hình dạng dữ liệu máy chủ trả: đọc `src/kho_tri_thuc/k2/ma_tran_tham_quyen.py` và `giao_dien/ma_tran_tham_quyen.py`. Route `/api/tham-quyen/{ma-tran,cua-toi,nhat-ky,luu-nhap,cong-bo,kich-hoat}`; mã 403/409. **Không đoán trường**: chỉ dùng trường mà DTO thật có.
- Cách viết một tệp asset độc lập và test node có DOM giả: xem `src/kho_tri_thuc/giao_dien/assets/*.js` và `tests/*_async.cjs`.

**Việc: tệp mới `src/kho_tri_thuc/giao_dien/assets/ma_tran_tham_quyen.js`.** Module độc lập, xuất một hàm dựng màn vào một phần tử cho trước. **Không** nối vào `app.js`/`index.html`/`server.py`; việc đó thuộc MTQ-3b.

Màn Admin:
- Chọn pháp nhân rồi phòng. Hiện trạng thái Chưa bật/Đang dùng, số phiên bản, lần sửa cuối và người sửa.
- Bảng năm dòng vai. Ghim cột Vai và **một cột "Giới hạn số tiền (VND)"**.
- Nhóm cột theo module rồi màn; mỗi nhóm sáu hành động Xem/Lập/Sửa/Kiểm/Duyệt/Hủy; gấp/mở được, gấp nhóm không làm mất tick.
- Ô không có chức năng hiện "—" và không tick được. M9 hiện "Tạm dừng", mờ.
- Tiền canh phải, dấu chấm phân nhóm. Ô trống hiện "Không giới hạn"; 0 hiện "0 VND"; số âm hay sai kiểu bị chặn ngay trên màn.
- Lưu nháp: hiện **diff** ô và hạn mức cũ → mới; bắt buộc nhập lý do; gửi kèm `expected_revision` và khóa yêu cầu đúng như máy chủ đòi.
- 409 → báo "Đã có người khác sửa, tải lại", không ghi đè. 403 → câu không có quyền.
- Công bố có hộp xác nhận. Bật: chỉ hiện nút khi máy chủ báo được phép; máy chủ từ chối thì hiện lý do bằng câu Việt.
- Không có nút "tick hết", không có nút mẫu ngoài DEMO, không tự áp mẫu.
- Xem nhật ký: thời điểm dd/mm/yyyy hh:mm, người (tên hiển thị), lý do, nội dung đổi.

Màn "Quyền của tôi" cho người không phải Admin: chỉ gọi `cua-toi`, chỉ đọc. Không tải toàn ma trận rồi ẩn bằng JavaScript.

An toàn:
- Mọi chuỗi từ máy chủ đều escape trước khi hiển thị; không đưa chuỗi chưa escape vào `innerHTML`.
- Chống bấm đúp.
- Không gửi actor, vai hay pháp nhân của người dùng làm căn cứ quyền.

**`src/kho_tri_thuc/giao_dien/assets/style.css`:** chỉ thêm khối lớp riêng có tiền tố `mtq-`, không sửa lớp có sẵn.

**Test, tệp mới `tests/mtq_bang_tick.cjs`** (node, DOM giả như các bộ `*_async.cjs`):
- dựng năm dòng;
- ô "—" không tick được;
- gấp/mở giữ tick;
- định dạng tiền (trống, 0, 500.000.000);
- chặn số âm;
- diff và lý do bắt buộc;
- thân lưu nháp đúng trường;
- 409 và 403 ra câu Việt;
- người không phải Admin chỉ gọi `cua-toi`;
- escape chuỗi chứa `<script>`.

**Chạy:**
- `node tests/mtq_bang_tick.cjs`;
- **toàn bộ** `tests/*.cjs`, báo số đạt/không đạt và so với trước khi sửa (bộ đã đỏ sẵn thì ghi rõ).

**Tệp (≤ 3):** `ma_tran_tham_quyen.js`, `style.css`, `tests/mtq_bang_tick.cjs`.

**Báo cáo (≤ ¼ trang):** số test, phần "Cần Anh", thông điệp commit `[MTQ-3a] …`.
