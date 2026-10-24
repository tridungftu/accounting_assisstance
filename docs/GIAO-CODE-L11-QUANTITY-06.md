# Giao Claude sửa L11 quantity 06 — barrier đổi vai chung

Căn cứ: yêu cầu hiện hành nối bộ đọc XML/ZIP M2 với M5 qua L11; kiến trúc và phạm vi đã chốt. Tận dụng code hiện có. Đọc `docs/REVIEW-L11-ROOT-ACTUAL-05.md`, `docs/BAO-CAO-L11-QUANTITY-05.md` và đặc tả các bản trước liên quan.

## Phạm vi

Chỉ sửa `src/kho_tri_thuc/giao_dien/assets/app.js`, tạo `docs/BAO-CAO-L11-QUANTITY-06.md`. Giữ nguyên tất cả function/handler M9 và CRM không liên quan. Không sửa backend, SQL, service, tests hoặc fixture. Không đọc dữ liệu thật, var, .env, .git, source app hoặc thông tin đăng nhập. Không xóa, di chuyển, đổi tên hoặc reset bất kỳ file nào.

**CODE ONLY**: chỉ dùng công cụ file đã cấp. Không chạy lệnh, process, product, Node, Python, browser, test, SQL hoặc network. Báo self-test UNRUN, không tự tuyên bố đã kiểm hay nghiệm thu.

## Sửa đúng counterexample đã chạy

Bản05 được kiểm 23 ca: 14 PASS/9 FAIL/0 setup error. Chín ca FAIL là đủ tổ hợp bộ chọn vai M2/M5/L11 × module M2/M5/L11 điều hướng/refresh khi POST đổi vai còn chờ. GET mới sau click lấy context actor cũ vì POST chưa commit, nhưng epoch mới nên vẫn được áp dụng. Tham khảo nguyên nhân và giới hạn trong review05.

1. Tạo trạng thái/barrier đổi vai chung để cả `m2Load`, `m5Load`, `l11Load` và đường điều hướng/refresh không khôi phục context cũ trong lúc đổi vai chưa giải quyết. Có thể chặn hoặc đợi GET; không được dựa vào tăng epoch một lần rồi để GET mới lọt.
2. Giữ việc xóa đồng bộ cả ba module trước await, serialization POST, latest-intent semantics và fencing actor/generation gốc cho các action/FILE đang chờ. Không dùng context mới cho action cũ.
3. Barrier phải đi theo ý định mới nhất; completion/error/finally cũ không được mở barrier hoặc render vào ý định mới. Sau thành công hoặc lỗi của ý định mới nhất, nạp context phù hợp và giao diện tiếp tục dùng được. Tránh deadlock do loader tự đợi chính lời gọi đổi vai của mình.
4. Giữ cơ chế từ chối của server, token/version/capacity/CAS và khả năng xuất FILE hợp lệ. Không bỏ positive control, không che lỗi hoặc làm mọi GET/action im lặng vĩnh viễn.

## Bàn giao

Report06 ghi rõ đoạn sửa, vòng đời barrier/GET/actions, cách giải quyết chuỗi vai và nhánh lỗi, giới hạn nhiều tab/M9 nếu vẫn ngoài phạm vi. Tất cả test ghi UNRUN do giới hạn CODE ONLY. Root sẽ đóng băng, đọc diff, thực chạy lại bộ 23 ca và regression liên quan, rồi kiểm browser trước nghiệm thu. Không ghi full L11/Q09/file33 hoàn tất.
