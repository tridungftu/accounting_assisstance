Anh, đã hoàn tất đúng 3 tệp được giao: seed 5 vai + Admin DEMO riêng, công bố nhưng chưa bật; chạy lại không ghi đè/cấp lại quyền. Lỗi seed có log và không chặn CRM.

- **Test:** 50 test — 22 đạt, 28 PostgreSQL skip; không lỗi trong bộ yêu cầu. `git diff --check` đạt; UTF-8 không BOM.
- **Cần Anh:** Lead chạy test PG ngoài sandbox. Worktree thiếu `crm_kiem_demo.py` và seed phòng; tôi tái dùng master CRM/M4, dùng duy nhất `mtq_phong`.
- **Chưa commit**, đúng yêu cầu. Thông điệp đề xuất: `[MTQ-5a] Thêm mẫu ma trận DEMO 5 vai, seed một lần và giữ chưa bật`.