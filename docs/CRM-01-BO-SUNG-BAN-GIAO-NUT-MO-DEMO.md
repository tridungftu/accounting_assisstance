# CRM-01 — cổng bàn giao bằng nút mở DEMO

Ngày19/10/2026. Review bổ sung sau khi đã dispatch lượt sửa02; không có nghĩa Claude đã đọc hoặc đã triển khai mục này. Chưa chạy launcher/GUI trong lượt đọc tĩnh.

`MỞ BẢN DEMO.cmd` hiện chỉ gọi `start-web.ps1` với `cau_hinh.toml` và `var/web`. Đã tìm trong launcher/tools hiện có: chưa có bước chuẩn bị `KHO_PG_DSN_CRM_DEMO`. Báo cáo CRM đầu yêu cầu người chạy tự đặt biến môi trường. Vì vậy luồng CRM chưa đủ điều kiện bàn giao cho người dùng cuối theo mục tiêu “bằng nút bấm, không gõ lệnh”. Không lấy test HTTP tự cài env làm bằng chứng nút mở hiện tại đã dùng được.

## Đầu ra cần hoàn tất cùng CRM

- Từ nút mở DEMO hiện có, chuẩn bị hoặc dùng lại PostgreSQL DEMO riêng đã định danh, sau đó mở cùng shell. Không mở app CRM thứ hai, không đổi config/kho thật hoặc chuyển SQLite thật sang PG.
- Dùng runtime PostgreSQL đã có trên máy; không cài lại hoặc xin UAC chỉ vì service không mang tên hệ thống. Chỉ khởi động cluster đã biết và đúng localhost khi có kiểm trạng thái/chủ sở hữu; không xóa pid/lock hay dừng tiến trình lạ để giành port.
- Runtime web kết nối bằng login thường được cấp app_web, kiểm không superuser/BYPASSRLS. Migration/seed dùng quyền quản trị cục bộ riêng chỉ trong bước chuẩn bị; không truyền DSN quản trị vào browser hoặc dùng nó cho request thường.
- Credential/DSN được đọc/ghi bởi bước local đã kiểm, chỉ ở máy và quyền file phù hợp; không hardcode vào source/test/docs, không in log/CLI, không gửi Claude đọc `.env` hoặc biến mật khẩu. Codex chịu phần cấu hình bí mật cục bộ nếu cần; Claude chỉ viết code và dùng helper test được cấp.
- Tên DB/kho DEMO và version rõ, mở lại giữ hồ sơ/lịch/link/danh tính phiên đúng; không xóa hoặc tạo lại DB để qua lỗi migration. Lỗi có thông báo cho người dùng và log đã lọc, không yêu cầu Anh tự gõ DSN/SQL.
- Giữ no-delete guard trong quá trình kiểm, mọi file/temp/output/DB/role retained. Launcher không xóa log cũ; nếu cần log mới thì tên riêng theo lần chạy. Không tắt các test hoặc bảo vệ source để làm nút mở xanh.

## Bằng chứng cần có

Codex đọc script/code bootstrap trước khi chạy; chuẩn bị cấu hình local không lộ bí mật; thử mở lần đầu/mở lại/restart bằng nút tương ứng và kiểm HTTP health/CRM state, role PG, DB/schema, hai pháp nhân/profile, persistence và quyền phiên. Nếu browser tool chưa khả dụng thì ghi **GUI chưa kiểm**, không nhận HTTP hoặc source grep làm bằng chứng đã bấm GUI. Sẵn sàng bàn giao chỉ khi đường mở không đòi người dùng thao tác kỹ thuật.

Gói02 đang sửa source; không chạy thêm app/test hoặc sửa cùng file trong lúc Claude còn hoạt động. Sau terminal, review phần đã làm rồi giao bổ sung có ranh giới file cụ thể, tránh viết trùng bootstrap nếu Claude đã hoàn thiện trong lượt02.
