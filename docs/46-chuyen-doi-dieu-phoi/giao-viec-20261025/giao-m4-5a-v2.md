# M4-5a vòng 2 — chống gắn trùng hóa đơn giữa các đối chiếu (checklist 03B dòng 7) — sửa trong M0033 (chưa gộp)

Bạn là worker Codex, chạy không tương tác. Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`, `CLAUDE.md` (§2). UTF-8 không BOM — **ghi tệp bằng UTF-8**. Worktree hiện tại, nhánh `lat/m4-5a` (commit vòng 1 vừa xong, M0033 chưa gộp → **được sửa SQL M0033** trong `k2/sql_ghi_nhan_so_tien.py`). Sandbox không ghi `.git`: **không commit**. Không nối CSDL (lead chạy PostgreSQL sau).

**Bạn đã báo:** "guard lưu M0029 vẫn cho cùng hóa đơn ở nhiều gốc, chưa bảo đảm chống gắn trùng". Checklist Anh duyệt (`docs/46-chuyen-doi-dieu-phoi/CHECKLIST-M4-03B.md`): dòng 3 **nhiều–nhiều trong một đối chiếu** (một đợt ↔ nhiều hóa đơn, một hóa đơn ↔ nhiều đợt); dòng 7 **hóa đơn đã gắn ở đối chiếu khác → báo rõ "đã gắn ở …", không cho gắn trùng**; quy tắc máy chủ đầu checklist: "hóa đơn đã thuộc đối chiếu khác bị từ chối".

**Việc:**
1. M0033 (`sql_ghi_nhan_so_tien.py`): khi lưu/xác nhận phiên bản đối chiếu, hóa đơn mua đã thuộc **đối chiếu khác (gốc khác) đang còn hiệu lực** → **từ chối** với mã lỗi rõ và thông tin "đã gắn ở" (định danh đối chiếu/đợt hiển thị được, không lộ dữ liệu ngoài quyền). Trong **cùng một đối chiếu** vẫn cho nhiều–nhiều. Phiên bản mới của **cùng** đối chiếu (thêm/bớt nguồn) không bị coi là gắn trùng với chính nó. Kiểm tại CSDL (khóa phù hợp để hai giao dịch song song không cùng gắn được), không chỉ ở Python. **Không** sửa SQL M0029 (`sql_ghi_nhan_chung.py` giữ nguyên byte); dùng `CREATE OR REPLACE` hàm lưu (cùng chữ ký/kiểu trả) hoặc trigger mới trong M0033.
2. Python `k2/ghi_nhan_chung.py`: chuyển lỗi CSDL thành `DataError` tiếng Việt có trường; `goi_y_hoa_don` giữ cờ `da_gan`/`da_gan_o` khớp đúng quy tắc trên.
3. Test: thuần (mock) + ca PG viết sẵn trong `tests/test_m4_03b_common_pg.py`: hóa đơn đã ở đối chiếu A → gắn vào đối chiếu B bị từ chối có "đã gắn ở"; cùng đối chiếu nhiều đợt OK; phiên bản mới của A giữ hóa đơn đó OK.

**File được sửa (chỉ):** `src/kho_tri_thuc/k2/sql_ghi_nhan_so_tien.py`, `src/kho_tri_thuc/k2/ghi_nhan_chung.py`, `tests/test_m4_03b_so_tien.py`, `tests/test_m4_03b_common_pg.py`. Không sửa `pg_migrations.py`, `sql_ghi_nhan_chung.py`; không xóa file.
**Test phải đạt:** `--module test_m4_03b_so_tien --module "test_m4_*"` không thêm mã lỗi so với nền v4.
**Báo cáo cuối (≤ ⅓ trang):** cơ chế chống gắn trùng (file:dòng, khóa gì) · ca test · thông điệp commit `[M4-5a] vòng 2: …`.
