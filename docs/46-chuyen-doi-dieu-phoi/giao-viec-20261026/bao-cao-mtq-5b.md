Anh, đã hoàn tất phần backend MTQ-5b trong 2 tệp: `giao_dien/server.py` và `tests/test_mtq_demo_phien.py`.

- API `/api/demo/vai` trả đúng 5 vai MTQ, Admin DEMO tách nhóm; dùng phiên CRM hiện có và chặn kho thật.
- CRM/M9 lọc bỏ actor MTQ; M5 giữ allowlist riêng. Registry cũ nguyên trạng.
- **Test: 84/209 đạt, 125 skip, 0 lỗi; không lỗi mới so nền v4.** Đã kiểm cookie, đổi đủ 6 actor, cách ly phiên, token/query và UTF-8 không BOM.
- Còn thiếu: test PG `cua-toi.la_admin=true` chưa chạy vì thiếu DSN/driver; nối hiển thị thuộc lát giao diện riêng.

Không mở server, không commit. Thông điệp đề xuất: `[MTQ-5b] Bổ sung nhóm vai DEMO MTQ và tách Admin DEMO`.