Đã hoàn tất, Anh.

- `khung_khai_bao.py:319`: DEMO thiếu phiên được cấp phiên và cookie đúng `/api/crm`; phiên hợp lệ được dùng lại; kho thật giữ UI-3c.
- `tests/test_khung_he_thong.py:215`: kiểm tra cấp cookie, refresh không sinh phiên và kho thật không tạo phiên.
- Test chỉ định: **45/45 đạt**, không lỗi mới. Hai file UTF-8 không BOM; `git diff --check` đạt.
- Không commit. Thông điệp đề xuất: `[UI-3d] Cấp phiên kèm cookie cho trang chủ DEMO khi thiếu phiên`.

File review không có tại đường dẫn được giao; đã thực hiện theo yêu cầu chi tiết của Anh.