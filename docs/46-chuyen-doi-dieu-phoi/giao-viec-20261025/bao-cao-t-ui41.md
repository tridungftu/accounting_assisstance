[T-UI41] Đã cập nhật duy nhất `tests/test_crm_41_02.py`, UTF-8 không BOM.
Ghim SHA-256 toàn tệp `tests/m4_01c_async.cjs` để bảo vệ setup C4; đổi `f77bdfe6…` → `70cd8da4…` do BG-e4 sửa kiểm vai CRM.
Setup C4 giữ nguyên; S6 mount đúng một lần, route/id còn đúng; cập nhật khẳng định cú pháp route theo MDA-2.
Đã thêm chú thích “UI-1/UI-3 dòng giao diện 26/10”.
Test chỉ định: **29/29 đạt**, không lỗi mới; `git diff --check` đạt.
Không commit, không mở server/PostgreSQL.