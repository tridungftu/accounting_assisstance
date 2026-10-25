# L0-2a — Gộp m4-03b-common-identity fix01→fix04

Bạn là worker Codex, chạy không tương tác (`codex exec`). Lát này Anh đã duyệt qua lead: **làm ngay đến hết, không hỏi lại, không dừng chờ xác nhận**. Quy tắc "thống nhất trước khi code" trong cấu hình chung đã được đáp ứng bằng chính handoff này.

Đọc trước: `AGENTS.md` (gốc worktree), `CLAUDE.md`, rồi `docs/46-chuyen-doi-dieu-phoi/4-KE-HOACH-LEAD.md` mục 3 (handoff chính thức).

**Mã hóa:** mọi file là UTF-8. Đọc bằng `git show`, `python -X utf8` hoặc `Get-Content -Encoding UTF8`; ghi UTF-8 không BOM. Không để ký tự tiếng Việt bị hỏng.

**Thư mục làm việc:** worktree hiện tại, nhánh `lat/l0-2a` (tạo từ `hop-nhat-20261023` commit 1502fe7). Không đổi nhánh, không đụng worktree khác.

**Đã biết về nguồn:** mỗi nhánh `luu/m4-03b-common-identity-fix01..fix04` = nền `chinh` (59b7d8e) + một commit ảnh chụp NGUYÊN FILE. Trên `hop-nhat` đã có bản gốc common identity (commit cbc9bb7). Vì vậy "áp fix0N" nghĩa là: lấy nội dung các file mà commit fix0N thay đổi (`git show --stat luu/...-fix0N`, `git diff 59b7d8e luu/...-fix0N --stat`) và đặt vào worktree theo quy tắc: **bản kế nhiệm thắng** — file nào có ở fix sau thì nội dung cuối cùng lấy của fix sau cùng chứa file đó. Làm lần lượt fix01, fix02, fix03, fix04, mỗi fix một commit `[L0-2a] áp fix0N`. Không kéo theo file nào khác của `chinh`.

**File được sửa:** chỉ các file mà 4 commit fix chạm tới (dự kiến `src/kho_tri_thuc/k2/sql_ghi_nhan_chung.py`, `ghi_nhan_chung.py`, `tests/test_m4_03b_common_tinh.py`, `tests/test_m4_03b_common_pg.py`; ≤ 5 file). Nếu fix nào chạm file ngoài nhóm này → không áp file đó, ghi vào báo cáo.

**Test:**
- TRƯỚC khi áp: chạy `tests/test_m4_03b_common_tinh.py` và các module test khác có tên chứa `common` hoặc `ghi_nhan` (liệt kê trong `tests/`), mỗi module một lệnh: đặt `PYTHONPATH=src` rồi `python -X utf8 -m unittest tests.<module> -v`, giới hạn 180 giây/lệnh. Ghi ok/ERROR/FAIL/skip.
- SAU khi áp xong fix04: chạy lại đúng các module đó. "Xanh" = không thêm lỗi so với trước. Test PostgreSQL (`_pg`) bị skip vì không có `KHO_PG_DSN_TEST` là bình thường — không cấu hình PostgreSQL.
- Không chạy `test.ps1` toàn bộ (đang treo).

**Không làm:** sửa logic ngoài nội dung các bản fix; thêm tính năng; sửa file khác; xóa file; `git reset --hard`, `git clean`, push; đọc `var/`, `.env`, `cau_hinh.*.toml`; tạo thư mục freeze/manifest/handoff/bản sao repo.

**Báo cáo cuối (≤ 1 trang, tiếng Việt)** — là tin nhắn cuối cùng của bạn:
Đã làm · Commit (hash + tiêu đề) · File đổi · Test trước/sau từng module (ok/ERROR/FAIL/skip) · Lỗi mới so với trước: có/không · Còn thiếu/rủi ro.
