# MTQ-4a0 vòng 2: cổng SQL ma trận, sửa điểm Chặn của review và các điểm nên sửa quan trọng

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại.**
- Ghi tệp UTF-8 không BOM. `pg_migrations.py` giữ LF. **Không commit**.
- Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-4a0` (530d528).
- **Không sửa `pg_migrations.py`** ở vòng này; chỉ sửa 2 tệp dưới.

**1. Chặn — `tests/test_mtq_cong_sql.py` dòng ~53–55.**
- Test đang ghim migration này là **cuối cùng** (`PG_MIGRATIONS[-1]`, `[:-1]`) và ghim tên tạm `PM.M00xx_MTQ_CONG`.
- Sửa theo mẫu `tests/test_mtq_sql.py` dòng 38–41:
  - exec phần đầu `pg_migrations.py` trước dấu `# MTQ-4a0 — CD-012:` để lấy `previous`;
  - kiểm `PG_MIGRATIONS[:len(previous)] == previous` và `PG_MIGRATIONS[len(previous)] is MTQ_CONG_SQL`.
- **Bỏ** dòng kiểm tên `M00xx`; lead sẽ đổi sang M0041.

**2. Ca PG đỏ `test_hoi_khong_ghi_audit_logger_ghi_dung_mot_dong` (dòng ~264):**
- Test khẳng định bảng `nhat_ky.mtq_tu_choi` **trống** trước lúc hỏi, nhưng các test khác dùng chung CSDL của lớp đã ghi trước.
- Sửa: đếm **trước và sau** lời gọi `mtq_quyet_dinh_phien` và khẳng định không đổi. Giữ ca ghi đúng một dòng bằng đếm trước/sau.

**3. Nên sửa — pháp nhân chưa bật phải trả `CU`** (`k2/sql_mtq_cong.py` dòng ~41, ~45):
- Hiện HĐ M4 (`module_chu` khác rỗng), bản soạn G3/G4 hay bảng ngoài danh sách cho phép trả `MTQ_CAN_RESOLVER_MTQ4` **kể cả khi pháp nhân chưa bật**. MTQ-4a nối vào sẽ làm hỏng đường cũ.
- Sửa:
  - tìm pháp nhân của `master.hop_dong` bất kể module, và của `master.du_an`;
  - pháp nhân chưa bật → **`CU`**;
  - chỉ khi pháp nhân **đã bật** mới áp danh sách đối tượng hỗ trợ và chặn đối tượng chưa có resolver;
  - bảng không xác định được pháp nhân: trả `CU` nếu **không pháp nhân nào** đang bật, còn lại thì chặn.
- Không đọc thêm bảng nào ngoài cần thiết; không dùng quyền cũ trong SQL.

**4. Nên sửa — hàm ghi từ chối** (dòng ~107–124):
- **Chống trùng theo `p_request`:** đã có dòng cùng `request_id` thì trả lại `id` dòng đó, không ghi thêm.
- `p_hanh_dong` phải thuộc danh mục hành động MTQ (bảng danh mục M0039); không thuộc thì từ chối.
- Không có danh tính phiên thì **không ghi**, báo lỗi.

**5. Test thêm:**
- `has_function_privilege` khẳng định `app_ke_toan`, `app_doc`, `app_cong_ai` (vai nào tồn tại) **không** có EXECUTE trên 2 hàm mới.
- Pháp nhân chưa bật + HĐ M4 → `CU`.
- Ghi từ chối trùng `request_id` → cùng `id`, số dòng không tăng.
- `hanh_dong` lạ bị từ chối.
- Không danh tính → không ghi.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_cong_sql tests.test_mtq_sql`, với PYTHONPATH=`src;.;tests`.

**Tệp (2):** `k2/sql_mtq_cong.py`, `tests/test_mtq_cong_sql.py`.

**Báo cáo (≤ 5 dòng)**, thông điệp commit `[MTQ-4a0] vòng 2: …`.
