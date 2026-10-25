[DA-6] Đã khôi phục phiên khi gặp `CRM_PHIEN`, thử lại đúng một lần; giữ fence và không retry 403 quyền.
File đổi: `crm_g.js`, `tests/crm_du_an_ban_async.cjs`; UTF-8 không BOM.
Test đạt: dự án 44/44, giao kết 48/48, khung lưới 33/33, ký kết 14/14; lỗi mới: không.
Đã thử bằng mock DOM/fetch: phục hồi thành công, lỗi hai lần, 403 quyền và rời tab khi đang chờ.
Chưa thử trình duyệt thật; không commit, không mở server.