# REVIEW L0-8 vòng 2/2 (bộ chạy test PostgreSQL `--pg-demo`) · reviewer Claude (chỉ đọc)

Bạn là reviewer chéo cho bản sửa do Codex viết. **Chỉ đọc**: không sửa tệp, không commit, **không chạy `--pg-demo`, không nối CSDL**. Worktree `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức\.claude\worktrees\lat-l0-8`, nhánh `lat/l0-8`; vòng 2 = commit `4a37c49` (`git -C <worktree> show 4a37c49`); toàn lát: `git -C <worktree> diff hop-nhat-20261023...lat/l0-8`. Được chạy test thuần: `python -X utf8 tools\chay_test_theo_module.py . --module test_chay_test_pg_demo` (trong worktree).

**Review vòng 1 (Codex) 5 Chặn:** (1) mọi `kho_test_*` mới đều bị coi là của mình rồi DROP, sổ chỉ ghi sau DROP; (2) đường `--pg xoa` nội bộ chỉ kiểm regex, dọn theo sổ không xác minh ảnh chụp/cụm nguồn; (3) traceback/stdout/stderr test ghi nguyên văn → DSN/mật khẩu lọt vào log/JSON/console; (4) probe rỗng → `.pth` ghi ra thư mục hiện hành; (5) dọn theo sổ không cập nhật sổ → chạy lại có thể DROP CSDL khác trùng tên. Nên sửa (6): `tests/test_ket_noi.py`, `tests/test_pg_schema.py` dùng `DROP DATABASE … WITH (FORCE)` và `DROP ROLE`.
**Quyết định Anh QD-20261025-10:** chỉ tạo/xóa CSDL tạm `kho_test_*` do chính lần chạy tạo; không đụng CSDL khác; không lộ DSN/mật khẩu.

**Kiểm, Đạt/Không — đọc kỹ đường thực thi, không tin chú thích:**
1. Cả 5 Chặn đã hết: tìm mọi chỗ có `DROP`/`CREATE DATABASE`/`DROP ROLE` trong `tools/chay_test_theo_module.py` và hai test; mỗi DROP đi qua đúng một lớp kiểm đủ ba điều kiện (mẫu tên, có trong sổ của đúng lần chạy + đúng cụm, không có trong ảnh chụp trước); sổ ghi bền **trước** CREATE và đánh dấu "đã xóa" sau DROP; tên SQL dùng `sql.Identifier`.
2. Lọc bí mật phủ mọi đường ghi/in (log module, stdout/stderr tiến trình con, traceback, JSON, console) — tìm đường nào còn ghi thẳng.
3. Hai test sửa ở (6): không còn `FORCE`; `DROP ROLE` chỉ cho vai tự tạo trong chính test hoặc skip có lý do; chạy không `--pg-demo` thì hành vi như cũ.
4. Không có hồi quy khi chạy **không** `--pg-demo`.

**Báo cáo cuối (≤ ½ trang, tiếng Việt, ≤ 6 điểm):**
```
REVIEW L0-8 · vòng 2/2 · Claude
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
Vòng cuối: chỉ "Chặn" khi còn đường DROP/ghi bí mật sai như trên.
