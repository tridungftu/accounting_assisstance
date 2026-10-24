# M2 bridge repair02 — kiểm nút giao diện DEMO

19/10/2026. **G01_BUTTON_FLOW_VERIFIED_NOT_FULL_GUI_ACCEPTANCE.** Root dùng CUA trên actual LocalApp/LocalServer, vai PostgreSQL ứng dụng thường, DB mới chỉ trên 127.0.0.1. Source249 workspace khớp frozen manifest `4c81093fbe59bc3ba6c894d4a7d7a55fe4b99405bde9292687302256c7755bab`. Đây là lát giao diện của repair02; R4 source-basis còn mở, L11 chưa có code.

- Vai INTAKE thực chọn G01 và bấm **Nhận mẫu**: giao diện hiển thị lần nhận XML, hai dòng nguồn dẫn xuất và một quan sát đưa vào M2.
- Đổi sang CFO mua A, mở hóa đơn: quantity raw `10`, normalized `10`, đơn vị CAI; tiền vẫn NULL/chưa có căn cứ.
- Chọn explicit candidate `DEMO_M2_LITERAL_LINE_FACT_01_V1 r1`, nhập lý do và bấm **CFO map dòng**: giao diện báo đã map, có cầu nối dòng quantity10.
- Chọn KHO, nhập lý do và bấm **CFO tạo + duyệt tuyến**: tuyến hiện hành KHO v1 DA_DUYET và lịch sử tuyến xuất hiện. Đây là định tuyến bằng chứng, không phải duyệt tồn kho/tài chính.
- Đổi sang VIEW A: chỉ M2_READ; mở chi tiết vẫn thấy kết quả, không có nút source-review, mapping hoặc tạo tuyến. Đây là quan sát UI; quyền DB/API có bằng chứng kiểm độc lập riêng.

Root bấm NATIVE bằng vai READ_SOURCE; chưa thu được saved-download path/hash nên không tính là kiểm bytes tải về đạt. Chưa kiểm upload filechooser XML/ZIP, đổi vai trong actual network delay, mọi kích thước màn hình hoặc toàn bộ trường hợp GUI. Sáu case controlled Promise/DOM đã chạy riêng là async unit, không thay các phép kiểm GUI còn thiếu. Viewport hẹp có horizontal scrolling; chưa đánh giá trải nghiệm desktop rộng.

Server do root sở hữu: parent11604/child37596, handle3404, launch64ba46/READY071c69; stop bằng sentinel riêng và actual terminal `c7bd9a`, exit0/STOPPED_RETAINED, không lỗi đóng kết nối và không xóa tài nguyên. Server đã dừng trước dispatch Claude repair03 `571f2a`/46081. Bằng chứng giữ tại `var/codex-dieu-phoi/m2-gui-actual02-65eff8d442ce/`: ready.json, stopped.json, gui-view-only.txt, gui-kho-route.png. Hashes trong continuity-current.json; không có credential trong report hoặc các receipt hiển thị.

![Tuyến KHO trên DEMO](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/var/codex-dieu-phoi/m2-gui-actual02-65eff8d442ce/gui-kho-route.png>)
