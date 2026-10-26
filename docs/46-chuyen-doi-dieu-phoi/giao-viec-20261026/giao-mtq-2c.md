# MTQ-2c: Ma trận thẩm quyền, route quản trị còn thiếu (khai phòng, gán vai, phạm vi, Admin, khôi phục) và câu báo lỗi theo mã (CD-012; thiết kế §6)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách an toàn và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-2c`, dựng từ hợp nhất (đã có MTQ-1 = M0039, MTQ-2, MTQ-2b).

**Căn cứ:**
- Thiết kế `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md` §6 (bảng API) và §5.3.
- SQL `k2/sql_ma_tran_tham_quyen.py`: đọc các lệnh `mtq_cau_hinh_ghi` mà M0039 đã hỗ trợ cho phòng, gán vai, phạm vi, Admin, khôi phục, và mã lỗi của chúng.
- Mẫu đã có: `k2/ma_tran_tham_quyen.py`, `giao_dien/ma_tran_tham_quyen.py` (đọc thân trước khóa, CAS, khóa yêu cầu, nhật ký từ chối sau rollback, 503 khi nhật ký lỗi).

**Việc:**
1. Thêm route POST `/api/tham-quyen/{phong,gan-vai,pham-vi,admin,khoi-phuc}`.
   - Chỉ Admin; cùng cơ chế với `luu-nhap` và `cong-bo`: token phiên, `expected_revision`, lý do bắt buộc, khóa yêu cầu.
   - Máy chủ dựng actor và diff.
   - Cấp và thu hồi tường minh, không DELETE.
   - **Bảo vệ Admin cuối cùng:** không thu hồi được Admin hoạt động cuối cùng.
   - `khoi-phuc` = công bố bản đã công bố trước đó thành **phiên bản mới**, có nhật ký; không tự tắt.
   - **Lệnh SQL M0039 chưa hỗ trợ thao tác nào thì không tự thêm SQL hay migration.** Bỏ route đó và ghi "Cần lead: thiếu lệnh SQL …" trong báo cáo.
2. **Câu báo lỗi theo mã** (nên sửa của review MTQ-2b):
   - Ánh xạ 6–8 mã `MTQ_*` hay gặp sang câu nghiệp vụ riêng, ví dụ:
     - `MTQ_THIEU_DONG` → "Chưa đủ 5 vai cho mỗi phòng đang dùng; bổ sung trước khi công bố.";
     - `MTQ_CHUA_NOI_MTQ4` → "Chưa bật được: các phân hệ chưa nối xong với ma trận.";
     - `MTQ_REVISION` → "Bản nháp đã thay đổi; tải lại trước khi lưu.";
     - lỗi bảo vệ Admin cuối.
   - Mã khác dùng câu chung.
   - Bỏ cụm từ kỹ thuật "Khóa yêu cầu…" (khoảng dòng 261, 264), thay bằng "Yêu cầu này đã được gửi với nội dung khác; tải lại rồi thử lại."
   - Cột `ly_do` của nhật ký từ chối giữ mã gốc để tra cứu.
3. Không nối `server.py`; MTQ-3b làm phần đó.

**Test `tests/test_mtq_dich_vu.py`:**
- Mỗi route mới:
  - Admin được; người khác 403;
  - CAS 409; khóa yêu cầu lặp không ghi trùng;
  - thân lạ 400.
- Ca thu hồi Admin cuối bị chặn.
- Ca `khoi-phuc` tạo phiên bản mới.
- Câu theo mã.
- Phần PG chạy qua lệnh SQL thật (`skipUnless KHO_PG_DSN_TEST`).

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_dich_vu tests.test_mtq_sql`, với PYTHONPATH=`src;.;tests`.

**Tệp (≤ 3):** `k2/ma_tran_tham_quyen.py`, `giao_dien/ma_tran_tham_quyen.py`, `tests/test_mtq_dich_vu.py`.

**Báo cáo (≤ ¼ trang):** route đã thêm hoặc bỏ (kèm lý do), số test, thông điệp commit `[MTQ-2c] …`.
