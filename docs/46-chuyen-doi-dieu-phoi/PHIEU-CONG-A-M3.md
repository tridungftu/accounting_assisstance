# Phiếu cổng A — M3 · Hóa đơn bán & doanh thu BĐS · 26/10/2026

**BẢN NHÁP CHO LEAD — chưa có màn M3 để thử, chưa tự thử trình duyệt, chưa nghiệm thu.** Căn cứ: thiết kế M3 v2 §6, §7.2, §16; [CD-013/CD-014](CHI-DAO-TU-ANH.md); [mẫu phiếu Báo giá lần 2](PHIEU-CONG-A-BAO-GIA-LAN-2.md); [mô hình dữ liệu M3](THIET-KE-M3-DU-LIEU.md). Tệp v2 đã đọc chưa có §17. Lead bổ sung bảng mốc khi có §17, URL/cổng DEMO và kết quả tự thử trước khi gửi Anh duyệt. Mọi số/ngày/hồ sơ dưới đây đều là **giả DEMO**, không phải quyết định policy thuế.

**Bản thử:** CHỜ LEAD ĐIỀN URL/CỔNG DEMO. **Ngày giả lập:** 26/10/2026. Ngày trên màn dd/mm/yyyy, tiền ghi đơn vị VND. Khối **Vai mô phỏng** dùng nhãn tiếng Việt, không lộ mã kỹ thuật:

| Vai DEMO dự kiến | Phạm vi kiểm khi lead dựng màn |
|---|---|
| Kế toán · Pháp nhân DEMO A | Xem căn cứ, nối nguồn, kiểm tra, chuẩn bị đề xuất theo quyền. |
| Kế toán trưởng · Pháp nhân DEMO A | Duyệt đề xuất qua K5 theo phân quyền. |
| Chỉ xem · Pháp nhân DEMO A | Đọc hồ sơ; không được duyệt/xuất. |
| Kế toán · Pháp nhân DEMO B | Chỉ thấy dữ liệu và số việc chờ trong phạm vi DEMO B. |

## A. Trang chủ và lưới icon hai cấp

1. Trang chủ hệ thống → icon **M3 · Hóa đơn bán & doanh thu** → thẻ tổng quan và lưới sáu icon dưới đây. Số đỏ là **việc chờ người đăng nhập**, đã lọc quyền/pháp nhân; không phải tổng số chứng từ. Bấm số đỏ mở đúng danh sách việc chờ, thấy lý do và tuổi chờ.

| 🧾 Hóa đơn bán · 🔴2 | 📄 Hợp đồng/bàn giao · 🔴1 | 💰 Đợt thu KCN · 🔴1 |
|---|---|---|
| ⚙ Tham số phân bổ | ✓ Đề xuất/duyệt · 🔴1 | 🕘 Lịch sử |

Các số đỏ là minh họa DEMO, không cộng thành tổng khi cùng hồ sơ có nhiều việc. Tổng quan gồm hồ sơ thiếu căn cứ, hóa đơn lệch cơ sở và đề xuất chờ duyệt. Không có lịch tính/đối chiếu định kỳ trong M3; đó là M10.

## B. Danh sách và chi tiết hóa đơn–hợp đồng

2. **Hóa đơn bán**: lọc pháp nhân, kỳ, loại nghiệp vụ/hình thức doanh thu, dự án, hợp đồng, khách hàng, trạng thái. Các cột: hóa đơn/ngày · hợp đồng/phiên bản/căn-lô · khách hàng · trước VAT/VAT/tổng · hình thức doanh thu · kết quả ba đẳng thức · việc chờ/tuổi chờ. Chưa nối nguồn phải hiện **Chờ mapping**, không tự chọn theo số tiền.

3. Mở **HĐ-DEMO-01 · phiên bản 1 · Lô DEMO-01**. Ngăn chi tiết: Nguồn hóa đơn · Hợp đồng-cơ sở · Bàn giao · Đợt thu · Tham số phân bổ · Đề xuất · Lịch sử. Mỗi số xem được căn cứ, file/phiên bản; hóa đơn giữ đúng số nguồn. DEMO số học độc lập với policy thuế đang chờ #7:

| Cơ sở hợp đồng DEMO | Giá trị |
|---|---:|
| Giá trị trước VAT | 1.000.000.000 VND |
| Giá đất được trừ | 200.000.000 VND |
| Phần chịu thuế | 800.000.000 VND |
| VAT | 80.000.000 VND |
| Tổng thanh toán | 1.080.000.000 VND |

Hai hóa đơn DEMO lập ngày 01/10/2026 và 20/10/2026; mỗi hóa đơn có tổng 540.000.000 VND, phần không chịu thuế 100.000.000 VND, net chịu thuế 400.000.000 VND, VAT 40.000.000 VND. Tập DEMO này giả định đã xác nhận đủ đợt và phân loại thành phần; không áp mặc định này cho KCN/nhà ở thật.

| Ba đẳng thức phải thấy trên màn | Lũy kế hóa đơn | Cơ sở hợp đồng | Chênh · trạng thái DEMO |
|---|---:|---:|---|
| Σ tổng thanh toán = tổng hợp đồng | 1.080.000.000 VND | 1.080.000.000 VND | 0 VND · Khớp |
| Σ phần không chịu thuế = đất được trừ | 200.000.000 VND | 200.000.000 VND | 0 VND · Khớp |
| Σ net chịu thuế = phần chịu thuế | 800.000.000 VND | 800.000.000 VND | 0 VND · Khớp |

4. Biến thể DEMO lệch: phân loại lại hóa đơn thứ hai thành phần không chịu thuế 90.000.000 VND, net chịu thuế 410.000.000 VND; giữ VAT/tổng nguồn. Đẳng thức 1 vẫn khớp; đẳng thức 2 lệch **−10.000.000 VND**, đẳng thức 3 lệch **+10.000.000 VND**, tạo việc chờ; hệ thống không tự sửa số hoặc lấy net làm doanh thu. Khi thiếu hóa đơn/phiên bản, cơ sở thuế chưa duyệt #7 hoặc chưa rõ quan hệ thay thế: **PENDING** kèm lý do; chưa đủ đợt: **Chưa đủ đợt**, không kết luận lỗi toàn hợp đồng.

## C. Đợt thu KCN — bốn trường chính

5. **Đợt thu KCN** → mở **Đợt DEMO-01**, gắn HĐ-DEMO-01/phiên bản 1. Khối để kế toán nhìn và nhập Junsky chỉ gồm bốn trường đã chốt §16 #5:

| Pháp nhân | Số tiền trước VAT | Ngày bàn giao mặt bằng | Ngày kết thúc thuê |
|---|---:|---|---|
| Pháp nhân DEMO A | 500.000.000 VND | 20/10/2026 | 19/10/2031 |

Bên dưới **Nguồn & liên kết**: mã đợt, khách hàng, nghĩa vụ CRM, tiền M1/ngày thu thực tế, hóa đơn/VAT, currency, biên bản CRM và phiên bản, trạng thái xử lý, lớp ghi nhận. Không lấy tổng thực thu thay số trước VAT; không tạo khoản tiền mới khi nối hóa đơn/hợp đồng.

6. Thiếu biên bản: ngày bàn giao có nhãn **Chưa đủ căn cứ**, hồ sơ **PENDING — Chờ biên bản bàn giao theo hợp đồng/lô**, không chuyển lớp. Tham số phân bổ hiển thị nguồn/phiên bản; phí hạ tầng kỳ tháng; phương pháp A/B và làm tròn chưa hiệu chuẩn hiện **PENDING — Chờ K0**. #8 chưa chốt thì mapping Junsky chờ, không giả định mã khách là mã hợp đồng.

## D. Chuyển lớp theo mốc và đề xuất/duyệt

7. **Đề xuất/duyệt** phải hiển thị cấu trúc sau; **chưa có dòng chuyển lớp DEMO vì thiếu §17**, không tự tạo bảng mốc từ các mô tả trước đó:

| Mốc | Ngày dự kiến / thực tế | Căn cứ · phiên bản | Lớp trước → lớp sau | Giá trị · đơn vị | Trạng thái / lý do chờ |
|---|---|---|---|---|---|

Tập lớp để xem: **Đặt cọc · Người mua trả trước · Phải thu chưa đến hạn/đến hạn · Doanh thu chờ phân bổ · Doanh thu đã ghi nhận · Đã đảo/điều chỉnh**. Theo từng phần giá trị, không áp một lớp cho toàn hợp đồng. Không hiện số tài khoản; ánh xạ tài khoản do kế toán trưởng điền ở bước sau.

8. Khi lead đã bổ sung §17: thử thiếu nguồn quyết định → giữ lớp trước, nêu lý do, không cho duyệt; chỉ có ngày dự kiến → chưa chuyển, chưa tính đợt quá hạn. Quá dự kiến → việc chỉnh ngày có lý do/lịch sử. Có ngày thực tế vẫn phải kiểm biên bản đúng hợp đồng/lô. Nhận lại cùng sự kiện không tạo giá trị lần hai. Chuyển lớp là đề xuất qua K5, không đồng nghĩa đã ghi sổ Junsky.

9. Nút **Xem căn cứ · Bổ sung mapping · Kiểm tra · Chuẩn bị đề xuất · Duyệt · Xem bản hiển thị** theo quyền, bị chặn phải ghi rõ trường/căn cứ thiếu. **Xuất file nhập Junsky** chờ #10; chưa có file thì không hiện thành công “đã xuất”. Người chỉ xem không duyệt/xuất; vai DEMO B không thấy hồ sơ/số đỏ DEMO A. **Lịch sử** giữ cũ → mới, ai, lúc nào, lý do và phiên bản; sửa sau xuất/nhập đi điều chỉnh, giữ nguồn cũ.

## E. Anh sửa bảng mốc — để trống chờ §17

**CHỜ MỤC 17 CỦA THIẾT KẾ V2.** Lead đưa bảng đề xuất vào đây để Anh sửa trước khi duyệt cổng A; hiện chỉ có cấu trúc cột, không có dòng mốc.

| Loại hình · hình thức | Mốc | Nguồn quyết định | Điều kiện ngày/phạm vi | Lớp trước | Lớp sau | Cơ sở giá trị | Anh sửa |
|---|---|---|---|---|---|---|---|

## Đã biết / chờ hoàn thiện

- §17 chưa có: chưa chốt bảng mốc và chưa thể nghiệm thu chuyển lớp.
- #7 cơ sở thuế; #8 mapping đối tượng; #10 file nhập; #11 nguồn/mẫu/ID biên bản và policy nhà ở; #12 mẫu K0: **PENDING**, không chọn thay Anh. Khung hỗ trợ cả ghi nhận luôn và phân bổ; phần nhà ở phụ thuộc #11 còn bị chặn.
- Lead chưa điền URL, tài khoản/vai DEMO thực tế, bằng chứng tự thử và kết quả từng bước; phiếu này không xác nhận đã có giao diện chạy được.

**Kết luận của Anh:** [ ] Đạt  [ ] Cần sửa (ghi bước)  [ ] Chờ bảng mốc §17.
