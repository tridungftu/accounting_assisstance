# MTQ-4a: Ma trận thẩm quyền, cổng quyết định chung (adapter) và CRM luồng B/M1 (CD-012; thiết kế MTQ-0 §5, dòng MTQ-4a). Rủi ro cao.

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại**; chỗ chưa rõ thì chọn cách **chặn** (không cho phép) và ghi "Cần Anh".
- Đọc `AGENTS.md`, `CLAUDE.md`. Ghi tệp UTF-8 không BOM.
- Sandbox không ghi được `.git`: **không commit**. Không mở server hay PostgreSQL; test PG tự skip. Không xóa file.
- Làm trong worktree hiện tại, nhánh `lat/mtq-4a`, dựng từ hợp nhất (đã có MTQ-1 = M0039 và MTQ-2).

**Căn cứ:**
- `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md`: **§5.1** (hợp đồng cổng, bảng 3 trạng thái pháp nhân, trình tự), **§5.2** (hạn mức VND, mã `MTQ_VUOT_HAN_MUC` / `MTQ_THIEU_CO_SO_TIEN`, nhật ký chặn sống qua rollback), **§4.2** (điểm nối CRM luồng B, M1), §7 dòng MTQ-4a.
- SQL: `k2/sql_ma_tran_tham_quyen.py` (M0039). Lõi quyết định `master.mtq_quyet_dinh`/`mtq_san_sang` và các mã lỗi; dùng đúng tên trong SQL. `mtq_san_sang` hiện là `false` cố định, nên **mọi pháp nhân đang ở trạng thái tắt**.
- Mã hiện có: `k2/quyen.py`, `k2/crm.py`.

**Việc:**
1. `src/kho_tri_thuc/k2/quyen.py`: thêm adapter `kiem_tham_quyen(conn, hanh_dong_ky_thuat, doi_tuong, ngu_canh_tin_cay)`.
   - Trả quyết định gồm: nguồn `CU`/`MA_TRAN`; revision; ô áp dụng; hạn mức và số tiền so (Decimal); mã và lý do tiếng Việt.
   - **Pháp nhân tắt hoặc chưa cấu hình** → gọi **đúng đường cũ**, hành vi và kết quả không đổi một bit (allowlist, V3/V4, phân công).
   - **Pháp nhân đã bật** → chỉ dùng ma trận, không `cũ OR ma trận`, không `cũ AND ma trận`.
   - **Đã bật mà lỗi, thiếu ô hay không rõ đối tượng** → chặn có mã, không fallback.
   - Danh tính lấy từ phiên/GUC máy chủ, không từ body hay header.
   - Tiền lấy từ phiên bản nghiệp vụ đã khóa. CRM V3/G6A dùng tổng giá trị HĐ của phiên bản quyết định. Tiền thiếu → `MTQ_THIEU_CO_SO_TIEN`. Bằng hạn mức thì qua; vượt thì chặn.
2. `src/kho_tri_thuc/k2/crm.py`: các điểm kiểm quyền của CRM luồng B và M1 trong §4.2 gọi adapter với hành động kỹ thuật tường minh theo catalog.
   - Các điểm: nộp HĐ, bổ sung hồ sơ, trích lại, mapping, kiểm trước, duyệt/duyệt V4/từ chối, kiểm nhận tiền, liên kết/gỡ liên kết, file soát.
   - Nhánh tắt giữ nguyên kết quả cũ.
   - Nhật ký từ chối: khi bị chặn, rollback giao dịch nghiệp vụ, rồi ghi `nhat_ky.mtq_tu_choi` bằng giao dịch riêng **trước** khi trả lỗi, theo cách MTQ-2 đang làm.
   - Lỗi ghi nhật ký **không** thành cho phép.
3. Không bật ma trận cho pháp nhân nào; không sửa `mtq_san_sang`; không thêm migration.

**Test, tệp mới `tests/test_mtq_crm.py`:**
- **Hồi quy nhánh tắt:** với mọi điểm nối, kết quả trước và sau khi thêm adapter giống hệt (các vai cũ được và không được, V3/V4).
- **Nhánh bật**, giả lập quyết định của lõi (mock trả bật):
  - không fallback khi thiếu ô;
  - vai cũ được nhưng ô tắt → chặn; vai cũ cấm nhưng ô bật → được;
  - vượt, bằng và dưới hạn mức; tiền thiếu → chặn;
  - nhật ký từ chối được ghi sau rollback;
  - lỗi ghi nhật ký → không cho phép.
- **Giả mạo:** actor trong body bị bỏ qua.
- Phần PG (`skipUnless KHO_PG_DSN_TEST`): nhánh tắt chạy qua lõi SQL thật, kết quả bằng đường cũ.

**Chạy thuần:** `python -X utf8 -m unittest tests.test_mtq_crm tests.test_mtq_sql tests.test_mtq_dich_vu` và các test CRM luồng B hiện có, tìm bằng `tests/test_crm*.py` có gọi `kiem_nhan_tien`/`duyet`/`lien_ket`; PYTHONPATH=`src;.;tests`. **Báo số trước/sau** của các test CRM hiện có, không được giảm.

**Tệp (≤ 3):** `k2/quyen.py`, `k2/crm.py`, `tests/test_mtq_crm.py`.

**Báo cáo (≤ ⅓ trang):**
- các điểm đã nối, kèm hàm;
- số test;
- phần "Cần Anh";
- thông điệp commit `[MTQ-4a] …`.
