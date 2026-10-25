# REVIEW L0-8 (bật test PostgreSQL trên cụm DEMO) · vòng 1/2 · reviewer Codex (chỉ đọc)

Bạn là reviewer chéo, chạy không tương tác (`codex exec`, sandbox chỉ đọc). Lead giao: **làm ngay, không hỏi lại**. Đọc `AGENTS.md`. UTF-8. **Không** chạy công cụ với `--pg-demo` (sandbox, và không được nối CSDL); chỉ đọc mã + chạy test thuần nếu có.

**Đối tượng:** worktree hiện tại, nhánh `lat/l0-8` (4 commit, đầu `2a0af6c`); diff `git diff hop-nhat-20261023...lat/l0-8` — chủ yếu `tools/chay_test_theo_module.py` (cờ `--pg-demo <ket-noi.local.json>`, `--pg-demo-don-so <sổ>`), `CLAUDE.md` §5 (1 dòng), tài liệu `docs/46-chuyen-doi-dieu-phoi/NEN-TEST-PG.md` + 3 tệp JSON nền.
**Quyết định Anh (QD-20261025-10):** bộ chạy tạo CSDL tạm tiền tố `kho_test_` trên cụm PostgreSQL DEMO rồi xóa sau khi chạy; không đụng CSDL DEMO của Anh hay CSDL khác; không in/log DSN/mật khẩu.

**Kiểm 5 việc — trọng tâm AN TOÀN XÓA, Đạt/Không:**
1. **DROP chỉ đúng CSDL do chính lần chạy tạo:** đủ ba điều kiện (tên khớp `^kho_test_[a-z0-9_]+$`; không có trong ảnh chụp danh sách trước khi chạy; có trong sổ "đã tạo" ghi **trước** khi CREATE); tên đưa vào SQL được trích dẫn an toàn (identifier quoting, không ghép chuỗi thô); không `FORCE`; không có đường nào DROP `kho_crm_demo_*`, `postgres`, CSDL có sẵn, hay DROP ROLE.
2. **Bí mật:** DSN/mật khẩu chỉ nằm trong môi trường tiến trình con; không in, không ghi nhật ký/kết quả/ngoại lệ (kể cả thông điệp lỗi psycopg có thể chứa DSN); DSN không loopback bị từ chối.
3. **Khóa chống chạy song song** và **dọn khi chết giữa chừng** (`--pg-demo-don-so`) đúng; sổ ghi bền (ghi trước, xóa dòng sau khi DROP thành công).
4. `PYTHONUSERBASE` tạm + `.pth` chỉ nằm trong thư mục nhật ký, không ghi vào hồ sơ người dùng thật.
5. Không đổi hành vi khi **không** có `--pg-demo` (so với hop-nhat: cùng kết quả, cùng tệp ra); `CLAUDE.md` chỉ đổi đúng dòng mô tả.

**Báo cáo cuối (≤ 1 trang, tiếng Việt, ≤ 8 điểm):**
```
REVIEW L0-8 · vòng 1/2 · Codex
Kết luận: Đạt / Cần sửa
| # | Mức (Chặn/Nên sửa/Để sau) | File:dòng | Vấn đề | Đề xuất |
```
"Chặn" khi có đường DROP CSDL/vai trò không do lần chạy tạo, lộ DSN/mật khẩu, hoặc ghi ngoài thư mục nhật ký.
