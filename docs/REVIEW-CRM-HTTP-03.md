# Review độc lập CRM — HTTP lần 03

19/10/2026. **23/23 criterion đạt, 0 setup error; exit0.** Đã chạy HTTP loopback thực với hai cookie jar độc lập và login PostgreSQL thường; không service mock. Chỉ DEMO, không truy cập kho thật.

CLI89659 kết thúc exit0 trước khi root freeze/release. Manifest121 file SHA256 `82e5e26806e05ef732536fcb0e474ab6ee96f646566e335e728da28921f47c3a` giữ nguyên trước/sau; sáu file trọng yếu HTTP/CRM/UI/M1/fixture cũng giữ nguyên. Guard không xóa và bytecode tắt. Giữ lại DB/role/file của lần kiểm; không lưu credentials/session token vào evidence.

Đạt control caller isolation: đổi actor ở phiên B không đổi quyền phiên A; body spoof, thiếu token, đọc/ghi pháp nhân khác bị chặn. KT không nhận quyền CFO từ phiên khác. CFO chỉ V3 không đóng việc V4; CFO hợp lệ duyệt đúng phiên bản qua phiên của mình. Kết nối HTTP thực `rolsuper=false`, `rolbypassrls=false`.

Luồng dương tạo ba đợt DEMO đúng300m/1,2b/1,5b. Xuất và tải XLSX qua HTTP trả **9.161 byte**, hash đúng đăng ký, có đủ sheet, ba dòng lịch và0formula; phiên pháp nhân khác không tải được. Reopen LocalApp/server/connection giữ bản duyệt, đăng ký export và cùng byte tải.

Giới hạn: reopen thực hiện **trong cùng Python process**. Chưa chứng minh OS process restart, nút mở DEMO, cold PostgreSQL startup hoặc GUI trình duyệt; các phần đó thuộc review riêng. Token ứng dụng chung là lớp CSRF, quyền actor vẫn được kiểm theo phiên; bộ kiểm không khẳng định mọi mô hình auth production đã nghiệm thu.

Probe `var/codex-dieu-phoi/crm-http-independent-probe-03.py`, SHA256 `d88c223a307f45aa8b2d11a1be6776b6ad8ec965f6cc5d66c43ccd79255b01b7`.

Evidence `var/codex-dieu-phoi/crm-http-independent-03-20261019-074948-3ce7e7/result.json`, SHA256 `3a95ceebfe43c769a74295bbdc8050b9e9c6d8e234d421c03c5879072674fe5d`. Kết quả này không thay nghiệm thu toàn CRM/M1/V13/toàn cây33.
