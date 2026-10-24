# R15 M2 — bằng chứng async UI độc lập03

19/10/2026. **ACTUAL_FINITE_ASYNC_UNIT / F1_F2_CONFIRMED / CHƯA NGHIỆM THU HTTP/GUI.** Root đã FULLREAD probe rồi thực thi thực bằng guarded Python/owned Node child, timeout ngoài25giây, tool `1b8715`. Reviewer chỉ đọc kết quả và ghi supplement này; không chạy thêm product/JS/HTTP/SQL/browser.

Kết quả retained: `var/codex-dieu-phoi/m2-ui-async-independent01/root-result01-757fd1ea156b.json`, SHA `51135270480e8750b93cef66a7899411444f98f094c4e9a69794595cc04dc870`. Probe02 SHA `d1ab0f3f98d5006921239c298ef44eb3836401da18a1f57835592ed5be76a165`; README SHA `fb09fb6ab8f771b950bffd8dacf320ad17a5de290a0b1c9dc450d610c764afb2`; actual app frozen SHA `2b2cad3bed2a52d4416f42503ed736b82ece71708835abf212d65dc4a793bb42`.

| Nhóm | Positive không rỗng | Negative thực tế | Kết luận |
|---|---|---|---|
| F1 download | PASS:1request/1download spy, synthetic raw size4 | FAIL:`OLD_M2_RAW_DOWNLOADED_AFTER_ROLE_CHANGE` | M2 đổi vai vẫn tải response cũ vì dùng epoch M5 |
| F2 detail | PASS:1request/1detail render | FAIL:`LATE_DETAIL_A_OVERWROTE_B` | GET A đến muộn ghi đè detail B |
| F2 list | PASS:1request/1list render | FAIL:`LATE_LIST_A_OVERWROTE_B` | GET A đến muộn ghi đè state/list B |

Tổng6controls: **3positive PASS,3negative FAIL,0setup errors**. Ba negative tương ứng hai nhóm finding F1/F2; không đếm thành ba lỗi P1 độc lập. Mỗi negative có positive counterpart; detail/list phải render B không rỗng trước khi thả response A. Late exception/toast/status không được xem là guard thành công. Result là `FINITE_ASYNC_UNIT_NOT_VERIFIED`, không phải PASS của candidate.

Probe dùng đúng các hàm/callback lấy từ app frozen, controlled Promises và DOM/render/download spies; không gọi mạng hay kiểm quyền thật. Root xác nhận toàn249 workspace/frozen pins và original guard giữ nguyên; result cũng xác nhận source SHA trước/sau không đổi. Đây xác nhận hành vi async của code hiện tại, không chứng minh browser download bytes, HTTP authorization, DB causal transaction hoặc GUI interaction.

Report01 SHA `948bf9a581be24ef7719a6af8fd85b7b240cc6db998f91dbf0a85a2c8df3888c` và supplement02 SHA `22f4f0a703fc0792ba0577ef40f65786a5866742b2dd33eeb24e7c0e318aef0f` giữ nguyên. Sau sửa phải pin/freeze source mới, review binder/extraction sibling và giữ cùng6oracle; không tự đổi expected để làm xanh. F3 SQL-error classifier và lỗi exact retry của service vẫn là các kiểm riêng. Không claim fullM2/M5/L11/33 hoặc acceptance tài chính/nguồn production.
