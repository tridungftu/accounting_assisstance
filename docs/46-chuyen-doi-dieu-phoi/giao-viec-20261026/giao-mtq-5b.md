# MTQ-5b: Ma trận thẩm quyền, bộ chọn vai DEMO có 5 vai MTQ và Admin DEMO (CD-012; thiết kế dòng MTQ-5b)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Đọc `AGENTS.md`, `CLAUDE.md` §4. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-5b`, dựng từ hợp nhất. Đã có MTQ-5a: seed 6 actor `MO_PHONG_MTQ_*` gồm Admin DEMO, công bố nhưng chưa bật.

**Căn cứ:**
- Thiết kế `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md`, dòng MTQ-5b: "Bộ chọn hiển thị đúng 5 cấp theo phòng/PN cho chế độ MTQ; Admin DEMO tách ở quản trị. Registry cũ còn dùng cho test âm/PN chưa bật, không bị xóa hay đổi vai."
- Review MTQ-5a (`giao-viec-20261026/review-...`): bộ chọn danh tính DEMO của CRM và M9 (`giao_dien/server.py` khoảng dòng 275 và 391) liệt kê người mô phỏng `mo_phong`; nên lọc cho rõ.
- `k2/mtq_demo.py`: danh sách actor và tên hiển thị.

**Việc:**
1. Trong bộ chọn vai DEMO của **trang chủ hệ thống / ma trận**, thêm nhóm "Ma trận thẩm quyền (DEMO)" gồm:
   - 5 vai: Người thực hiện 1, Người thực hiện 2, Trưởng phòng, CFO, Người xem;
   - nhóm riêng "Quản trị DEMO" cho Admin DEMO.
   - Đổi sang vai nào thì phiên CRM dùng đúng actor đó; danh tính vẫn do máy chủ cấp như cơ chế đổi vai hiện có.
2. **Không** thêm actor MTQ vào bộ chọn của CRM, M9, M5. Lọc bỏ `MO_PHONG_MTQ_*` khỏi các bộ chọn đó để khỏi nhầm ở cổng A.
3. Registry vai cũ giữ nguyên, không xóa, không đổi vai.
4. Chỉ ở DEMO; chế độ kho thật không có bộ chọn này.

**Tệp (≤ 3):**
- `giao_dien/server.py`: danh sách vai mô phỏng theo nhóm, lọc bỏ MTQ khỏi bộ chọn CRM/M9.
- Nếu giao diện cần nhóm mới thì `giao_dien/khung_khai_bao.py` hoặc tệp test; **không** sửa `app.js` (dòng giao diện riêng).
- Test mới `tests/test_mtq_demo_phien.py`:
  - nhóm MTQ có đúng 5 vai + Admin tách;
  - bộ chọn CRM/M9 không có `MO_PHONG_MTQ_*`;
  - đổi sang Admin DEMO thì `cua-toi` trả `la_admin=true` (PG, `skipUnless KHO_PG_DSN_TEST`, tự tạo CSDL `kho_test_*`);
  - kho thật không có bộ chọn.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_demo_phien tests.test_mtq_demo`, cùng các test server có bộ chọn vai (tìm `danh-tinh`/`mo_phong` trong `tests/`). PYTHONPATH=`src;.;tests`.

**Báo cáo (≤ ¼ trang)**, thông điệp commit `[MTQ-5b] …`.
