# Review độc lập bản L11 quantity 05

Trạng thái: **CHƯA ĐẠT**. Claude đã bàn giao code; Root đã đọc toàn bộ diff, đóng băng đúng 273 file nguồn và kiểm độc lập bằng Node với dữ liệu tổng hợp DEMO. Chỉ app.js thay đổi so với bản04; 272 file còn lại nguyên hash. Không sửa M9, backend, SQL, service hoặc fixture.

## Kết quả thực chạy

- Bản app.js đã kiểm: `5e7781daf08884a7e4e5a1049247b2b6752cde47a88f60213c038945fa85d806`.
- Tiến trình Claude05 kết thúc exit0 trước kiểm tra. Bộ kiểm riêng kết thúc exit1 vì có counterexample, không phải timeout hay lỗi thiết lập.
- 23 ca hữu hạn: **14 PASS, 9 FAIL, 0 setup error**, stderr rỗng. Kiểm hash toàn 273 file trước/sau đạt.
- PASS gồm: một ca FILE không rỗng với click thật của handler/Blob 4 byte trong sandbox; ba ca đổi vai xóa đồng bộ cả M2/M5/L11; tám ca đổi vai từ M2/M5 tại các điểm FILE POST/refresh/headers/Blob; hai chuỗi ba ý định đổi vai, gồm phản hồi lỗi cũ. Nguồn05 xếp tuần tự POST nên đảo thứ tự phản hồi đồng thời đã bị ngăn; không tuyên bố đã chạy một lịch đảo phản hồi không thể xảy ra.
- FAIL là chín tổ hợp: bộ chọn vai M2/M5/L11 đang chờ POST, rồi điều hướng/tải lại M2/M5/L11. Mỗi ca quan sát hai GET mới sau click lấy actor cũ của server, khôi phục cache/DOM cũ trước khi POST hoàn tất. Với màn L11, actor LINK và dữ liệu cũ được render trở lại.

## Nguyên nhân và yêu cầu sửa

`doiVaiChung()` xóa cache và tăng epoch ngay khi click, nhưng `m2Load`, `m5Load`, `l11Load` vẫn cho GET mới chạy khi đổi vai còn pending. GET mới giữ epoch mới nên vượt qua các fence vốn chỉ chặn phản hồi GET cũ. Server chưa xử lý xong POST vẫn trả context của vai trước. Khi POST xong, chỉ module khởi tạo đổi vai được tải lại; cache của module khác có thể còn context cũ.

Cần một barrier chung cho trạng thái đổi vai đang chờ, áp dụng từ lúc nhận ý định mới nhất đến khi POST hiện hành đã giải quyết và nạp lại context phù hợp. Getter/điều hướng/refresh của cả ba module không được nạp hay render context cũ trong khoảng này. Giữ serialization và latest-intent semantics, không để completion/finally cũ mở barrier của ý định mới. Nhánh lỗi cũng phải thoát trạng thái chờ theo context mới nhất và có thể dùng tiếp.

Không đổi backend để né ca kiểm. Giữ nguyên actor/generation fence của action và FILE, cùng kiểm quyền server. Không sửa M9.

## Giới hạn bằng chứng

Đây là sandbox thực thi đúng đoạn mã nguồn M5–M2–L11, DOM/network tổng hợp và lịch phản hồi có điều khiển; không phải lần tái hiện browser thật của bản05. Không quan sát được việc tải byte FILE trái quyền qua backend. Blob 4 byte chỉ là positive control của handler, không phải kiểm workbook.

Bộ 14 ca async cũ của bản04 **chưa chạy trên05**; không nhầm với 14 PASS trong bộ 23 ca mới. Kết quả nghiệp vụ/HTTP/physical workbook đã kiểm ở bản04 giữ đúng phạm vi lịch sử; không trình bày thành thực chạy05. Cần chạy lại các kiểm liên quan sau bản sửa06 và kiểm browser thực. Chưa nghiệm thu toàn GUI/L11/Q09/file33.
