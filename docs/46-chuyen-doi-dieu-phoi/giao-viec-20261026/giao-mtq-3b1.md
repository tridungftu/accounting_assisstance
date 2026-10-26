# MTQ-3b1: Ma trận thẩm quyền, nối route `/api/tham-quyen/*` vào bộ điều phối máy chủ (CD-012; thiết kế dòng MTQ-3b, phần máy chủ)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Đọc `AGENTS.md`, `CLAUDE.md` §4. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-3b1`, dựng từ hợp nhất. Đã có MTQ-2, MTQ-2b và module giao diện MTQ-3a; MTQ-2c đang làm song song ở tệp khác.

**Căn cứ:**
- `src/kho_tri_thuc/giao_dien/ma_tran_tham_quyen.py`: `la_route(post, path)`, `dieu_huong(h, app, post, path, query)`, docstring "route mỏng cho dispatcher MTQ-3b".
- Cách `server.py` điều phối các nhóm route khác: ví dụ `crm_g.dieu_huong` (khoảng dòng 972) và `khung.dieu_huong`.
- Cách phục vụ tệp tĩnh `assets/*.js`.

**Việc:** chỉ sửa `src/kho_tri_thuc/giao_dien/server.py`.
1. Trong bộ điều phối GET và POST, chuyển yêu cầu có `path` bắt đầu bằng `/api/tham-quyen/` sang `ma_tran_tham_quyen.dieu_huong`, đúng mẫu các nhóm route khác.
   - Đường lạ dưới tiền tố này trả 404 qua `dieu_huong`.
   - Không thêm kiểm quyền ở `server.py`; module đã tự kiểm.
   - **Không** giữ `mutation_lock` khi gọi, vì module tự lấy khóa. Đây là bài học deadlock của E1-4u.
2. Bảo đảm `assets/ma_tran_tham_quyen.js` được phục vụ như các asset khác. Nếu danh sách asset là whitelist thì thêm vào; không mở rộng phục vụ tệp tùy ý.
3. Không thêm menu, không sửa `app.js`/`index.html` (lát MTQ-3b2). Không bật ma trận cho pháp nhân nào.

**Test:** thêm vào tệp test HTTP đang có của `server.py`, chọn tệp test dispatcher gần nhất, hoặc tệp mới `tests/test_mtq_http_dispatch.py`.
- GET `/api/tham-quyen/cua-toi` đi tới module (giả lập module, kiểm được gọi đúng một lần với `post`/`path`).
- POST `/api/tham-quyen/luu-nhap` đi tới module.
- Đường lạ `/api/tham-quyen/bootstrap` trả 404.
- Lúc gọi module, `mutation_lock` **không** bị giữ (`threading.Lock()` thật, kiểm `locked()` là False).
- Asset `ma_tran_tham_quyen.js` phục vụ được.

**Chạy thuần:** test mới, cùng `tests.test_mtq_dich_vu` (PYTHONPATH=`src;.;tests`).

**Tệp (≤ 2):** `giao_dien/server.py`, 1 tệp test.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[MTQ-3b1] …`.
