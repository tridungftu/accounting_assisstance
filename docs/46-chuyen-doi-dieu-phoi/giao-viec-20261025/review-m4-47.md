# REVIEW M4-4/7 · vòng 1/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Anh đã duyệt qua lead: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8. Python hệ thống không dùng được trong sandbox; nếu cần chạy thử dùng `& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"` (thiếu psycopg là bình thường — chỉ chạy kiểm tĩnh).

**Đối tượng:** nhánh `lat/m4-47` (worktree hiện tại), 4 commit trên `da3d666`. Diff: `git diff da3d666..lat/m4-47`.
**Nội dung:** đăng ký migration PostgreSQL **M0028** = `M4_MASTER_DUNG_CHUNG_SQL` (`src/kho_tri_thuc/m4/sql_master_dung_chung.py`) và **M0029** = `M4_03B_COMMON_SQL` (`src/kho_tri_thuc/k2/sql_ghi_nhan_chung.py`) — APPEND cuối `src/kho_tri_thuc/ha_tang/pg_migrations.py` theo mẫu khối M0026/M0027; 2 test tích hợp mới (`tests/test_m4_master_m28_integration.py`, `tests/test_m4_03b_m29_integration.py`); sửa 4 test cũ; `.gitattributes`. Worker báo áp thật được 0→29 và 27→29 trên CSDL DEMO riêng.

**Kiểm 4 việc, Đạt/Không:**
1. **Chỉ append:** byte của `pg_migrations.py` trước khối mới trùng y hệt `da3d666` (so `git show da3d666:...` với prefix của bản mới); không đổi số/nội dung migration 1–27; khối mới đúng mẫu (import hằng thuần `# noqa: E402`, alias một lần, `PG_MIGRATIONS = (*PG_MIGRATIONS, …)`, `PG_SCHEMA_VERSION = len(...)`).
2. **Thứ tự phụ thuộc:** đọc SQL hai module — mọi bảng/hàm/schema được tham chiếu (vd `m4.kt_xac_nhan` của M0026, bảng biên nhận, `kho.l11_*`) đều được tạo ở migration số NHỎ HƠN; không có tham chiếu tới đối tượng tạo ở migration lớn hơn hoặc không tồn tại. Nêu đối tượng nghi ngờ (file:dòng).
3. **Test:** 2 test mới ghim đúng (prefix 1–27, SHA module, đúng object, ordinal, một lần); sửa regex trong `test_m4_master_dung_chung_tinh.py` (thêm `0-9`) không nới ý nghĩa; 3 test cũ chỉ đổi chú thích/thông báo skip.
4. **Ràng buộc:** không sửa module SQL hay code sản phẩm ngoài `pg_migrations.py`; không dữ liệu thật; không xóa file.

**Báo cáo cuối (≤ 1 trang, tiếng Việt, ≤ 10 điểm):**
```
REVIEW M4-4/7 · vòng 1/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi migration 1–27 bị đổi byte, thứ tự phụ thuộc sai (tham chiếu đối tượng chưa tạo), hoặc vi phạm ràng buộc cứng.
