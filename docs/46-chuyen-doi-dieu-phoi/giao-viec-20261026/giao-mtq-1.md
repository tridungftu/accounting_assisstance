# MTQ-1 — Ma trận thẩm quyền: SQL/migration (CD-012; thiết kế MTQ-0)

Bạn là worker Codex, chạy không tương tác. **Làm ngay, không hỏi lại** (chưa rõ → chọn cách an toàn, ghi "Cần Anh"). Đọc `AGENTS.md`, `CLAUDE.md`. UTF-8 không BOM — ghi tệp bằng UTF-8. Sandbox không ghi `.git`: **không commit**. Không mở server/PostgreSQL (test PG tự skip — lead chạy). Không xóa file.

Worktree hiện tại, nhánh `lat/mtq-1` (hợp nhất, có tài liệu thiết kế). Căn cứ: hộp thư **CD-012**, **CD-010 mục 4**; thiết kế `docs\46-chuyen-doi-dieu-phoi\THIET-KE-MA-TRAN-THAM-QUYEN.md` (làm **đúng dòng "MTQ-1 · SQL/migration"** và các mục mô hình dữ liệu/chuyển tiếp của tài liệu).

**Việc:** tệp mới `src/kho_tri_thuc/k2/sql_ma_tran_tham_quyen.py` (chỉ hằng SQL): bảng/constraint ma trận (pháp nhân/phòng × vai × module × hành động, cột giới hạn tiền VND, phiên bản + nhật ký bất biến), danh mục module × hành động, **lõi quyết định** (một hàm kiểm quyền dùng chung, trả cho phép/chặn + lý do, gồm chặn **duyệt vượt giới hạn tiền**), lệnh ghi cấu hình **chỉ Admin** + nhật ký (ô nào, cũ → mới, ai, lúc), bootstrap Admin tin cậy; **mặc định tắt** (ma trận chưa bật = giữ quyền cũ, chưa nối vào kiểm quyền hiện có — việc đó là MTQ-4). Đăng ký **migration kế tiếp** cuối `ha_tang/pg_migrations.py` (append, không đổi migration cũ; tên biến `M00xx_MA_TRAN_THAM_QUYEN` — lead đánh số khi gộp; **test không ghi cứng số migration**). Quyền/RLS/REVOKE như bảng master cùng loại.
**Test — mới `tests/test_mtq_sql.py`:** thuần (SQL đủ bảng/hàm/REVOKE, mặc định tắt) + PG (`skipUnless KHO_PG_DSN_TEST`): Admin sửa được, người khác bị chặn; nhật ký cũ → mới; khác pháp nhân/phòng tách biệt; lõi quyết định: tắt → không can thiệp, bật → tick mới được, duyệt vượt giới hạn → chặn + lý do; bất biến/audit.
**Không làm:** dịch vụ/HTTP (MTQ-2), màn hình (MTQ-3), nối kiểm quyền (MTQ-4), seed 5 vai (MTQ-5).
**Báo cáo (≤ ⅓ trang):** bảng/hàm, cách chuyển tiếp, số test, Cần Anh, thông điệp commit `[MTQ-1] …`.
