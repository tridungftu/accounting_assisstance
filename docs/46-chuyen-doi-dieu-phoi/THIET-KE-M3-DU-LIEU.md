# M3-0 · Thiết kế dữ liệu M3 — bản nháp 26/10/2026

**Phạm vi:** 8 thực thể logic (6 nghiệp vụ, 2 chuyển lớp); tái sử dụng CRM/M1/M2, chưa quy định bảng SQL. Căn cứ: `M3-HOA-DON-BAN-VA-DOANH-THU-v2-20261026.md` (§16 thắng mục trước), [CD-013/CD-014](CHI-DAO-TU-ANH.md). Tệp v2 đã đọc chưa có §17; **bảng mốc cụ thể chờ mục 17 của thiết kế v2**, không tự điền.

## 1. Thực thể và nguồn — trang 1/3

Quy ước chung: khóa kỹ thuật ổn định, luôn kèm pháp nhân; ghim phiên bản nguồn, không nối theo tên/số tiền. Mỗi phiên bản giữ nguồn/file/hash/vị trí, người xác nhận, ngày nghiệp vụ, thời điểm nhận và hiệu lực riêng. Tiền dùng số exact + `currency`, thiếu là NULL với trạng thái `PENDING`, không thay bằng 0, không tự đổi tỷ giá. Ngày hiển thị dd/mm/yyyy; tiền luôn kèm đơn vị. Phụ lục/nguồn thay đổi tạo phiên bản, giữ lịch sử.

| # · Thực thể | Khóa ổn định / phiên bản | Trường nghiệp vụ và nguồn |
|---|---|---|
| 1 · Hợp đồng-cơ sở | CRM `hop_dong.id` + căn/lô/phạm vi; ghim `hop_dong_phien_ban.id`; mỗi bộ cơ sở có revision | Pháp nhân, khách hàng, dự án, loại hình, trạng thái duyệt **[CRM]**; giá trị trước VAT, giá đất được trừ, phần chịu thuế, VAT, tổng thanh toán, currency **[hợp đồng/phiên bản CRM đã xác nhận]**. Phần chịu thuế = trước VAT − đất được trừ chỉ khi đủ căn cứ. Doanh thu lấy cơ sở hợp đồng, không lấy net hóa đơn. |
| 2 · Liên kết hóa đơn–hợp đồng | ID liên kết; ghim danh tính + phiên bản/quan sát hóa đơn và hợp đồng-cơ sở; revision mapping | Chiều bán, mẫu/ký hiệu/số/ngày, MST bán/mua, currency; net chịu thuế, phần không chịu thuế, VAT, tổng, quan hệ hủy/thay thế/điều chỉnh **[M2/M0]**; phạm vi căn/lô, đợt, căn cứ mapping, người duyệt **[CRM/xác nhận]**. Giữ nguyên số nguồn; một hóa đơn chỉ tính một lần trong phạm vi đã xác nhận; chia nhiều hợp đồng phải có căn cứ, thiếu thì PENDING. |
| 3 · Đợt thu | ID + mã đợt ổn định theo pháp nhân; ghim revision đợt, khóa nghĩa vụ CRM và các nguồn M1/M2 | **Lớp hiển thị để nhập Junsky:** pháp nhân, số tiền trước VAT, ngày bàn giao mặt bằng, ngày kết thúc thuê (§16 #5). **Lớp hệ thống:** mã đợt; hợp đồng/phiên bản, khách hàng; ngày thu thực tế, số tiền thực thu và liên kết tiền **[M1]**; hóa đơn/phiên bản và VAT **[M2]**; trước VAT **[hợp đồng/đợt được xác nhận]**; hai ngày thuê **[CRM/biên bản]**; currency, lớp ghi nhận, trạng thái xử lý, nguồn/căn cứ. Không đồng nhất tiền thực thu với tiền trước VAT. |
| 4 · Sự kiện bàn giao | ID sự kiện nội bộ ổn định + revision; ghim hợp đồng/phiên bản + căn/lô/phần bàn giao | Loại/phạm vi bàn giao, ngày thực tế, người xác nhận, file biên bản/hash/vị trí tải lên CRM, tham chiếu mốc dự án + lần lịch sử **[biên bản CRM theo hợp đồng/lô, §16 #6]**. ID nội bộ không thay ID biên bản nhà ở còn chờ #11; không lấy hash/ngày đơn lẻ làm khóa sự kiện. |
| 5 · Tham số phân bổ | ID bộ tham số; ghim hợp đồng/phiên bản; revision; dòng con tham chiếu mã đợt | Ngày bắt đầu = bàn giao có biên bản cho mọi đợt, ngày kết thúc thuê, kỳ/đơn vị, giá trị trước VAT từng đợt, ngày vào lớp chờ phân bổ có căn cứ **[CRM/đợt/biên bản]**; phương pháp A/B, cơ sở tháng/ngày, tháng lẻ/làm tròn, hiệu lực **[policy sau K0]**; mã đối tượng ngoài **[mapping, chờ #8]**. Một bộ đang hiệu lực/hợp đồng-phiên bản; phí hạ tầng đơn vị tháng đã chốt. |
| 6 · Policy hình thức doanh thu | Khóa policy theo pháp nhân + loại hình/loại nghiệp vụ; phiên bản, hiệu lực, người duyệt | `hinh_thuc`: **ghi nhận luôn / phân bổ** **[policy §16 #1, #9]**. Phạm vi đã chốt: nhà ở tại bàn giao; điện/nước/xử lý nước thải theo hóa đơn kỳ; thuê đất KCN và phí hạ tầng/quản lý thu trước nhiều kỳ theo phân bổ. Loại chưa xác nhận để PENDING; không gắn cứng lựa chọn theo tên loại. |

Lớp hệ thống của đợt thu giữ để đối chiếu, không tự đưa sang Junsky; trường mang mã đợt chờ #8/#10. M1 giữ tiền; M3 chỉ tham chiếu, không ghi tiền lần hai. M3 giữ tham số; **M10** tính lịch A/B kiểm chéo, nhận sổ Junsky, đối chiếu định kỳ và cảnh báo phân bổ/phụ lục/chấm dứt. Junsky là sổ gốc; M3 không tính lịch hoặc tạo nghiệp vụ phân bổ.

<div style="page-break-after: always;"></div>

## 2. Lớp ghi nhận và máy chuyển lớp — trang 2/3

| # · Thực thể hỗ trợ | Khóa / phiên bản | Trường và nguồn |
|---|---|---|
| 7 · Cấu hình chuyển lớp | ID quy tắc + phiên bản; phạm vi pháp nhân/loại hình/hình thức; hiệu lực và người duyệt | Mốc tham chiếu CRM, nguồn quyết định bắt buộc, điều kiện ngày/phạm vi, lớp trước/sau, cơ sở giá trị, bằng chứng phụ, trạng thái duyệt **[bảng §17 sau cổng A]**. Chưa có §17: không có dòng cấu hình hiệu lực. |
| 8 · Hồ sơ/đề xuất chuyển lớp | ID hồ sơ + revision; khóa chống lặp: pháp nhân + sự kiện logic + phần giá trị + quy tắc áp dụng; liên kết hồ sơ gốc khi điều chỉnh | Mốc; ngày dự kiến/thực tế + lần mốc; căn cứ + phiên bản; lớp trước → sau; giá trị/currency; phiên bản hợp đồng/policy; người lập/duyệt; trạng thái, lý do chờ, bắt đầu chờ; lịch sử **[nguồn quyết định + quy tắc #7 + K5]**. Nguồn đổi phải kiểm lại, không mặc nhiên tạo khoản mới. |

Các lớp nghiệp vụ, độc lập với trạng thái xử lý hồ sơ:

| Lớp | Nội dung lưu/hiển thị |
|---|---|
| Đặt cọc | Phần giá trị được xác nhận là cọc. |
| Người mua trả trước | Phần thu trước theo căn cứ hợp đồng/đợt. |
| Phải thu chưa đến hạn/đến hạn | Phần phải thu + trạng thái hạn; ngày dự kiến không phải ngày đến hạn. |
| Doanh thu chờ phân bổ | Phần giá trị đủ căn cứ vào lớp chờ phân bổ. |
| Doanh thu đã ghi nhận | Giá trị có căn cứ ghi nhận; tách đề xuất nội bộ với xác nhận trên sổ gốc. |
| Đã đảo/điều chỉnh | Liên kết bản gốc, quyết định và giá trị điều chỉnh; giữ bản cũ. |

Theo dõi lớp **theo từng phần giá trị/đợt/phạm vi bàn giao**, không ép cả hợp đồng vào một lớp; không cộng cơ học các lớp để tính doanh thu. Trước khi đủ căn cứ, không tự gán lớp. Các quyết định §16 #3/#3b được bảo lưu làm yêu cầu nghiệp vụ; không biến thành bảng mốc hoặc chuyển tự động khi §17 chưa có.

**Bảng mốc cụ thể — CHỜ MỤC 17 CỦA THIẾT KẾ V2. Chỉ cấu trúc cột, chưa có dòng:**

| Mã/phiên bản quy tắc | Loại hình · hình thức | Mốc CRM | Điều kiện ngày/phạm vi | Nguồn quyết định | Bằng chứng phụ | Lớp trước | Lớp sau | Cơ sở giá trị · currency | Hiệu lực · người duyệt |
|---|---|---|---|---|---|---|---|---|---|

Máy xử lý dự kiến: nhận thay đổi nguồn → ghim đúng phiên bản → tra cấu hình hiệu lực → kiểm ngày, nguồn quyết định và phạm vi → lập **đề xuất chuyển lớp** qua K5. Không có quy tắc, biên bản hoặc nguồn quyết định: giữ lớp trước, hồ sơ `PENDING` kèm lý do và tuổi chờ. Duyệt nguồn CRM khác duyệt kế toán; chuyển lớp trong M3 không chứng minh đã ghi sổ Junsky.

Tái sử dụng `crm_da_moc.id` + `crm_da_moc_ls.lan` (M0035): ngày dự kiến để theo dõi; chưa có thực tế không chuyển vì đã tới dự kiến, không tính đợt quá hạn. Qua dự kiến sinh việc chỉnh ngày, bắt buộc lý do và lịch sử; ngày thực tế + độ lệch ngày đã khai mới xác định hạn (CD-007). Ngày thực tế cấp dự án **không thay** biên bản riêng hợp đồng/lô. Bàn giao từng phần phải có định danh; cùng sự kiện qua nhiều nguồn chỉ thêm bằng chứng. Sau xuất/nhập/khóa kỳ, đi điều chỉnh có căn cứ.

**Không có số tài khoản trong mô hình M3 này.** Ánh xạ lớp → tài khoản là bảng policy bước sau do kế toán trưởng điền và duyệt; không suy từ trường tài khoản cũ của CRM, không sinh bút toán có số tài khoản ở giai đoạn này (CD-014). Chuỗi xử lý giữ riêng: chuẩn bị → đã duyệt → đã xuất → đã nhập Junsky → đã đối chiếu; #10 chưa chốt thì chỉ có bản hiển thị, không đánh dấu đã xuất/nhập. Đối chiếu định kỳ thuộc M10.

<div style="page-break-after: always;"></div>

## 3. Ba đẳng thức, điểm mở và tương thích — trang 3/3

Đối chiếu theo pháp nhân + hợp đồng/căn/lô + cơ sở phiên bản đã xác nhận + currency; ghim tập hóa đơn và mapping. Hóa đơn hủy/thay thế/điều chỉnh phải xác định quan hệ, phạm vi và dấu theo nguồn; chưa rõ thì PENDING, không cộng bản cũ với bản thay thế. Không tự coi quan sát mới nhất là hóa đơn hợp lệ.

| Đẳng thức §6 | Dữ liệu vào | Kết quả cần giữ |
|---|---|---|
| 1 · Σ tổng thanh toán hóa đơn tiến độ = tổng hợp đồng, khi xuất đủ đợt | Tổng từng hóa đơn M2 + tổng hợp đồng-cơ sở CRM + căn cứ xác nhận đã xuất đủ | Vế trái, phải, chênh = trái − phải, danh sách nguồn/phiên bản, trạng thái. |
| 2 · Σ phần không chịu thuế hóa đơn = giá đất được trừ hợp đồng | Thành phần hóa đơn M2 đã xác nhận cách thể hiện + cơ sở CRM + policy #7 | Như trên; chưa xác nhận cơ sở không được kết luận khớp. |
| 3 · Σ net chịu thuế hóa đơn = phần chịu thuế hợp đồng | Net chịu thuế M2 + phần chịu thuế CRM cùng phạm vi + policy #7 | Như trên; không lấy net hóa đơn thay doanh thu hợp đồng. |

Đủ nguồn và phạm vi: chênh 0 = **KHỚP**; khác 0 = **LỆCH**, ghi việc chờ và tuổi chờ, người xử lý/nguyên nhân; không đặt dung sai. Chưa đủ đợt: **CHƯA ĐỦ ĐỢT**, chỉ hiện số lũy kế/chênh tạm, chưa kết luận lỗi cơ sở toàn hợp đồng. Thiếu trường/mapping/policy/currency: **PENDING**, nêu chính xác dữ liệu thiếu, không coi là 0. Không tự sửa hợp đồng, hóa đơn hoặc bù lệch; khớp số không thay phê duyệt thuế.

| [CHỜ CHỐT] | Vùng bị ảnh hưởng | Giá trị/trạng thái tạm và giới hạn |
|---|---|---|
| #7 · Cơ sở thuế, cách thể hiện đất được trừ, kê khai thuế thu nhập | Cơ sở hợp đồng; phân loại tiền hóa đơn; đẳng thức 2/3 cho phạm vi chưa xác nhận | Policy `PENDING`; trường chưa xác nhận NULL/PENDING; giữ raw, không lấy mặc định 0, không tính thuế hoặc suy cách tách dòng/ghi chú. Bộ phận thuế xác nhận. |
| #8 · Đối tượng Junsky và trường mang mã đợt | Tham số/mapping ngoài, đợt thu, xác nhận đã nhập và M10 | Mapping `PENDING`; không giả định một khách = một hợp đồng hoặc một hợp đồng = một đối tượng. Mã đợt nội bộ vẫn ổn định. |
| #10 · Định dạng file nhập | Đề xuất, hồ sơ xuất và đối soát mã đợt | Định dạng `PENDING`; chỉ bản hiển thị 4 trường, chưa tạo file nhập hoặc đánh dấu đã xuất. |
| #11 · Biên bản và policy nhà ở | Sự kiện bàn giao, ID biên bản/người chịu trách nhiệm, quy tắc đề xuất nhà ở | Nguồn/mẫu/ID nghiệp vụ/người phụ trách/policy `PENDING`; chỉ giữ khung và ID nội bộ, chặn đề xuất nhà ở phụ thuộc. Không chặn phần KCN đủ căn cứ. |
| #12 · Mẫu hiệu chuẩn K0 | Tham số phương pháp của M10 và nghiệm thu | K0, A/B, cơ sở kỳ/làm tròn chưa hiệu chuẩn `PENDING`; không chọn mặc định. Chặn nghiệm thu K1–K5; vẫn lưu thông số đã xác nhận. |

**Đối chiếu code đã đọc (không sửa code):**

- `crm.py`/`m1_demo.py`: quy tắc tiền cũ phân nhánh theo có hợp đồng; `loai_hinh_doanh_thu` có trường tài khoản. Không dùng chúng thay policy cọc/trả trước và máy chuyển lớp CD-014; đây là khác biệt cần kiểm khi tích hợp, không kết luận toàn CRM sai.
- `sql_crm_du_an_ban.py`: `gia_dat_tru` là mức/m², có mặc định 0; M3 cần tổng đất được trừ theo hợp đồng/phiên bản đã xác nhận. Không sao chép hoặc nhân diện tích khi chưa đủ cơ sở.
- `sql_crm_du_an_moc.py` + M0035/`crm_du_an_ban.py`/`crm_s1.py`: đã có ID mốc, lịch sử và hai ngày; mốc cấp dự án chưa có file/người xác nhận biên bản theo hợp đồng/lô. Đây là phần còn thiếu, không phải nguồn thay thế bàn giao.
- `hoa_don.py` (`_ke_hoach`): bán ra hiện chỉ `SOURCE_CANDIDATE`, chưa promote M3; tiền còn giữ trạng thái raw. Tái sử dụng capture/danh tính/phiên bản, không giả định đã có dữ liệu bán ra chuẩn hóa để chạy ba đẳng thức. `master.lich_thu` là nghĩa vụ CRM, khác khoản tiền M1 và mã đợt nghiệp vụ M3.
