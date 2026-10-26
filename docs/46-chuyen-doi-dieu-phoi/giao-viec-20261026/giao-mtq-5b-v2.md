# MTQ-5b vòng 2: API chọn vai DEMO của ma trận, 3 điểm nên sửa của review (lead chốt bỏ nhóm vai cũ)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. **Không commit**. Không mở server hay PostgreSQL. Không xóa file.
- Test PG tự tạo CSDL `kho_test_*`, không đọc `KHO_PG_DEMO_*`.
- Làm trong worktree hiện tại, nhánh `lat/mtq-5b` (b0555b2).

**Việc trong `src/kho_tri_thuc/giao_dien/server.py` (`demo_vai`, khoảng dòng 301–320):**
1. **Lead chốt: bỏ nhóm "Vai DEMO hiện có"** (`ma: "CU"`) khỏi `/api/demo/vai`. API chỉ trả nhóm "Ma trận thẩm quyền (DEMO)" gồm đúng 5 vai, và nhóm "Quản trị DEMO" gồm Admin DEMO. Vai cũ vẫn chọn ở bộ chọn của từng phân hệ như hiện nay.
2. Đổi tên khóa cấp MTQ trong DTO từ `vai_tro` sang **`cap`**, để không trùng nghĩa với vai cũ.
3. CRM chưa cấu hình: trả `{"cau_hinh": false, "nhom": []}` với HTTP 200, giống `/api/crm`, thay cho 400.

**Test `tests/test_mtq_demo_phien.py`:**
- Ca PG gọi **thật** `GET /api/demo/vai` (đi qua câu SQL `ANY(%s)`/`starts_with`) và kiểm đúng 5 vai cùng Admin DEMO.
- Nếu cần, gọi `crm_g_demo.khoi_tao` như test MTQ-5a trước `cua-toi`.
- Thêm:
  - không có nhóm `CU`;
  - khóa `cap`;
  - CRM chưa cấu hình → 200 `cau_hinh: false`.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_demo_phien tests.test_mtq_demo`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `giao_dien/server.py`, `tests/test_mtq_demo_phien.py`.

**Báo cáo (≤ 3 dòng)**, thông điệp commit `[MTQ-5b] vòng 2: …`.
