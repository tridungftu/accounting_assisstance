# XS-4c2 · Route máy chủ cho công tắc module (CD-017, QD-20261026-11)

Bạn là worker Codex, chạy không tương tác. **Làm ngay.**
- Ghi UTF-8 không BOM. **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell nháy kép.** Không commit. Không mở server/PostgreSQL DEMO. Không xóa file. Không đọc `var\`, tệp bí mật, dữ liệu thật.
- Chỗ chưa rõ: dừng, ghi "Cần lead". Không có `python` thì NOT_RUN; lead chạy test.
- Test HTTP dùng mẫu test hiện có (`tests/test_mtq_http_dispatch.py`), không mở cổng thật, chạy được dưới guard giữ tệp. Không kiểm CRLF/LF trên tệp nguồn.

**Đã có (nhánh này dựng trên XS-4c1, đã review Đạt):**
- `k2/module.py` (`CongTacModuleK2`, `kiem_module`, `trang_thai_cho`);
- SQL M0056 (`k2/sql_module.py`).
- Mẫu route: `giao_dien/ma_tran_tham_quyen.py` (`la_route`, `dich_vu(app)`, `dieu_huong(h, app, post, path, query)`; dùng `h.authorize`, `app.mutation_lock`, `app.crm_phien(h.crm_sid())`, `app._crm_db`), và nhánh gọi trong `giao_dien/server.py` ~dòng 981.

**Tệp (3):** `giao_dien/module_cong_tac.py` mới; `giao_dien/server.py` (chỉ thêm **một nhánh** chuyển `/api/cong-tac-module/` sang module mới, đặt cạnh nhánh `/api/tham-quyen/`); `tests/test_xs4_http.py` mới.

**Việc:**
1. Route (tiền tố `/api/cong-tac-module/`):
   - `GET trang-thai?module=<mã>`: trả cờ cho **pháp nhân của phiên** (lấy từ phiên máy chủ như route MTQ). Không nhận PN từ client. Mã module chỉ nhận theo danh mục; mã lạ → 400 câu tiếng Việt.
   - `POST che-do` {module, phap_nhan_id, che_do, ly_do, revision} — chỉ Admin (SQL kiểm).
     - Đây là lệnh quản trị nên được nhận `phap_nhan_id` mục tiêu, nhưng phải là PN Admin được quản trị theo cơ chế MTQ hiện có. Nếu không có cách kiểm sẵn → "Cần lead".
   - `POST nguoi-thu/cap`, `POST nguoi-thu/thu-hoi`, `GET nguoi-thu?module=` — chỉ Admin.
2. Mã HTTP: 403 khi không phải Admin; 409 khi sai revision (CAS); 400 khi dữ liệu sai; 503 khi CSDL chưa sẵn sàng — theo mẫu `ma_tran_tham_quyen.py`. Thông báo tiếng Việt nghiệp vụ, không mã kỹ thuật trong câu.
3. Dùng `mutation_lock` cho POST, `authorize(private=True)`. Không log danh sách người thử. Không thêm thư viện.
4. **Không** gắn hàm chặn vào route của module khác ở lát này (pilot XS-T1 làm). Không sửa giao diện JS.

**Test:**
- route lạ → 404;
- GET trạng thái đúng cờ theo PN phiên; client gửi `phap_nhan_id` trong query → bị từ chối;
- POST không Admin → 403; Admin → 200; sai revision → 409;
- người thử: cấp/thu hồi/xem chỉ Admin;
- nhánh trong `server.py` chỉ bắt đúng tiền tố.

**Báo cáo (≤ ¼ trang)**, "Cần lead", thông điệp commit `[XS-4c2] …`.
