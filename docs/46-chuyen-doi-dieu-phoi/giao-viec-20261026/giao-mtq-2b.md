# MTQ-2b: Ma trận thẩm quyền, sửa 6 điểm "nên sửa" của review MTQ-2 (dịch vụ + HTTP)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-2b`, dựng từ hợp nhất (đã gộp MTQ-1 = M0039 và MTQ-2).
- Căn cứ: thiết kế `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md` §5.2 và §6; SQL `k2/sql_ma_tran_tham_quyen.py` (**không sửa**, không thêm migration).

**Việc:**
1. `giao_dien/ma_tran_tham_quyen.py`: đọc và chuẩn hóa thân yêu cầu (`h.json_body()` và kiểm khóa lạ) **trước** khi lấy `app.mutation_lock` và trước khi mở kết nối chủ bảng, giống `giao_dien/crm_g.py` khoảng dòng 638–645. Thân sai thì trả 400 mà không mở kết nối PG.
2. Lỗi ghi nhật ký (khi ghi từ chối hoặc ghi biên nhận) không được thành 400 "dữ liệu nhập".
   - Dùng mã riêng, trả 503 với câu tiếng Việt "Chưa ghi được nhật ký thẩm quyền, thao tác không được thực hiện. Báo quản trị."
   - Vẫn **không** chuyển thành cho phép.
3. Lưu nháp: đọc hiện trạng **một lần**, **bỏ qua ô và dòng không đổi**, chỉ gọi lệnh SQL cho phần thay đổi.
   - Hạ giới hạn thân yêu cầu xuống mức hợp lý (ví dụ ≤ 5 vai × số ô của danh mục một phòng); ghi rõ hằng số.
   - **Lead chốt:** revision tăng theo từng thay đổi như SQL MTQ-1 hiện làm; không đổi SQL. CAS `expected_revision` vẫn kiểm một lần ở đầu lần lưu, trong khóa.
4. Đọc:
   - GET `/ma-tran` chỉ Admin; người khác nhận 403 với câu "Chỉ quản trị xem được toàn bộ ma trận; xem Quyền của tôi." Người khác dùng `/cua-toi`.
   - `nhat_ky()` có giới hạn số dòng (mặc định 200, mới nhất trước) và **không** trả `boi_csdl` hay tên vai CSDL.
   - Đọc ô của ma trận bằng một truy vấn, không N+1.
   - Bỏ `LIKE 'HTTP_%'`, dùng so khớp đúng cột hoặc giá trị.
5. Câu chữ hiện cho người dùng: bỏ từ kỹ thuật.
   - "Revision…" → "Phiên bản…".
   - "…phải là UUID" → "Mã không hợp lệ".
   - "snapshot nguồn" → "bản đang áp".
   - "CSDL từ chối cấu hình (MTQ_…)" → câu nghiệp vụ không kèm mã.
   - Rà hết các câu trong 2 tệp nguồn.
6. Test `tests/test_mtq_dich_vu.py`:
   - App giả dùng `threading.Lock()` (không phải `RLock`).
   - Thêm ca chạy `dich_vu` **thật** với app giả: không treo, nhả khóa, đóng kết nối chủ bảng khi lỗi.
   - Thêm các ca:
     - thân sai → 400 mà không mở kết nối;
     - GET `/ma-tran` của người không phải Admin → 403;
     - lưu không đổi → không gọi lệnh ghi;
     - lỗi ghi nhật ký → 503;
     - nhật ký không có `boi_csdl`;
     - câu không có "UUID", "Revision", "snapshot".

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_dich_vu tests.test_mtq_sql`, với PYTHONPATH=`src;.;tests`.

**Tệp (≤ 3):** `k2/ma_tran_tham_quyen.py`, `giao_dien/ma_tran_tham_quyen.py`, `tests/test_mtq_dich_vu.py`.

**Báo cáo (≤ ¼ trang):** số test, phần "Cần Anh", thông điệp commit `[MTQ-2b] …`.
