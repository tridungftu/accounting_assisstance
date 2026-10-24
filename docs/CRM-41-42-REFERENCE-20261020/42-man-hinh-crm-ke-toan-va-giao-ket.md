# 42 · Màn hình CRM (kế toán + giao kết) — đặc tả để chốt trước schema

**Ngày lập:** 20/10/2026 · **Trạng thái:** **ĐÃ CHỐT 4 điểm 20/10/2026 (17:10)** — bỏ "Việc của tôi"; menu riêng; bán hàng thấy cả hai nhãn thu; chỉ máy tính (mục 16). Còn các điểm "trả lời sau". Chưa lập trình · **Vị trí:** module CRM trong web trung tâm (TL 40 §2 nhóm 1), hiện thực V16.
**Kế thừa:** TL 37 (màn hình duyệt chung K5 — 8 nguyên tắc, cột chuẩn, nút, phím tắt, quy tắc hiển thị §12); yêu cầu thiết kế giao diện của #5 Review hồ sơ thanh toán xây dựng (`review_xaydung/thiet_ke/YEU_CAU_THIET_KE_GIAO_DIEN.md`: menu trái, thanh trên, ngăn việc đang chạy, nền sáng 1280–1440 px, Be Vietnam Pro, số canh phải dấu chấm, màu luôn kèm chữ); file `CRM-CHUC-NANG-VA-THIET-KE.md` mục 5 (5 màn hình đề xuất); TL 41 (CRM-G vòng đời 7 trạng thái).
**Vì sao làm bước này:** tiêu chuẩn nội bộ "chốt màn hình rồi chốt schema" (TL 31). Màn hình quyết định cột → cột quyết định bảng.
**Không lập trình trong bước này.** Dữ liệu ví dụ là giả hoặc chỉ là mã.

---

## 0. Kết luận trước

- **CRM không có màn duyệt riêng.** Mọi việc cần người quyết (tham số chờ kiểm, mẫu chờ CFO, đối tượng mới, liên kết tiền) là dòng **V3/V4/V2 trên màn hình duyệt chung K5** (TL 37). CRM chỉ có **màn làm việc**: lập, xem, tra cứu, bấm Ký kết.
- **Một bộ màn hình cho hai mảng và hai luồng.** KCN và nhà ở khác nhau ở *profile* (cột, nhãn, tiền tệ), không khác màn hình. Luồng A (sinh từ mẫu, TL 41) và luồng B (trích từ bản ký, TL 32) gặp nhau ở **Chi tiết hợp đồng**.
- **Trang mở đầu của CRM là Danh sách hợp đồng** (có thẻ số đếm bấm được). **Không có màn "Việc của tôi" trong CRM** — anh chốt 20/10: sau này web trung tâm có "Việc của tôi" theo từng nhân viên cho mọi module; CRM chỉ **cung cấp loại việc** (mục 3) để gom vào đó và vào K5.
- **Mọi nút dùng ngôn ngữ nghiệp vụ và chỉ hiện khi đúng vai + đúng trạng thái** (file CRM mục 5). Nút không đủ điều kiện thì mờ và nói rõ thiếu gì (TL 37 nguyên tắc 4).
- **9 màn hình** (mục 4–12), 4 điểm đã chốt + điểm trả lời sau (mục 16), 16 trạng thái cần vẽ cho Claude Design (mục 15).

---

## 1. Người dùng và ma trận vai × màn hình

| Màn | Bán hàng | Kế toán công nợ | CFO | Người xem | Pháp chế / người tải mẫu |
|---|---|---|---|---|---|
| 1 Danh sách hợp đồng (trang mở đầu) | khách/dự án mình | theo pháp nhân | tất cả pháp nhân | theo phạm vi | — |
| 2 Chi tiết hợp đồng | xem; sửa khi còn dự thảo | xem; kiểm; nối tiền | xem; duyệt | xem | — |
| 3 Báo giá | **lập** | xem | xem | — | — |
| 4 Soạn hợp đồng từ mẫu | **lập, xuất, Ký kết** | xem | xem | — | — |
| 5 Hộp Ký kết | **bấm** | — | — | — | — |
| 6 Mẫu hợp đồng | xem mẫu hiệu lực | **kiểm ánh xạ** | **duyệt phiên bản** | — | **tải mẫu** |
| 7 Tiếp nhận hợp đồng ký (luồng B) | nộp file | **kiểm, mapping, bổ sung** | duyệt (ở K5) | — | — |
| 8 Thu tiền theo hợp đồng | xem tình hình thu + công nợ Junsky khách mình (chỉ đọc) | **nối/gỡ tiền** (ở K5 V2 + tab Thu tiền) | xem | xem | — |
| 9 Báo cáo & file soát | báo giá/HĐ của mình | ✔ | ✔ | theo phạm vi | — |

Quyền kiểm ở backend theo pháp nhân + dự án + người phụ trách (ca A7); bộ lọc giao diện không thay kiểm quyền. CCCD/STK hiện **4 số cuối** trừ vai kế toán công nợ và CFO khi mở chi tiết (ghi nhật ký lần xem).

---

## 2. Khung chung

- **Thanh trên** (dùng chung web trung tâm, TL 37 §2): tên phần mềm · KHO THẬT / KHO THỬ · **ô chọn pháp nhân** (CFO có "Tất cả") · ngăn **Việc đang chạy** (trích #6, đối chiếu bản ký, sinh file hợp đồng) · trạng thái cổng AI · người đăng nhập.
- **Menu trái**: mục riêng **Hợp đồng bán hàng** (anh chốt 20/10) với 6 mục con — Hợp đồng (trang mở đầu) · Báo giá · Mẫu hợp đồng · Tiếp nhận hợp đồng ký · Thu tiền · Báo cáo & file soát. Mục con ẩn theo quyền. "Danh mục master" (TL 37 menu 3) chỉ còn liên kết sang đây cho hợp đồng bán hàng.
- **Thanh ngữ cảnh** trên mỗi màn: đường dẫn (Hợp đồng › HĐ-nội-bộ › Lịch nghĩa vụ) · nhãn loại (KCN / Nhà ở) · nhãn trạng thái · nút hành động chính bên phải.
- **Toast** khi việc nền xong/lỗi; **ngăn phải** cho chi tiết nhanh và nhật ký (như K5).
- Phím tắt giữ bộ của K5 (↑/↓, Enter, Esc); màn soạn hợp đồng thêm Ctrl+S lưu nháp.

---

## 3. Loại việc CRM cung cấp cho K5 và cho "Việc của tôi" cấp hệ thống (sau này)

CRM **không có màn "Việc của tôi"** (anh chốt 20/10). Mỗi việc dưới đây là một dòng ở K5 (TL 37) với loại việc tương ứng, và sẽ được gom vào "Việc của tôi" theo nhân viên khi web trung tâm có màn đó. Mỗi dòng phải trả lời *việc gì — của hợp đồng nào — tôi phải làm gì* trong 3 giây; bấm dòng mở đúng tab của Chi tiết hợp đồng.

| Loại việc CRM | Người nhận | Loại việc K5 | Mở tab |
|---|---|---|---|
| Hợp đồng bị trả lại (lý do, ngày) · Yêu cầu bổ sung đang mở | Bán hàng | V4 / V5 | Nguồn & tham số |
| Hợp đồng chờ ký quá n ngày · Báo giá sắp hết hạn | Bán hàng | V8 (nhắc) | Tổng quan |
| Hợp đồng chờ kiểm (ngày tồn) · Phụ lục chờ kiểm | Kế toán công nợ | V3 / V4 | Nguồn & tham số |
| Lệch đối chiếu bản ký chưa xử lý | Kế toán công nợ | V3 | Bản ký & đối chiếu |
| Đợt đến hạn hôm nay / 7 ngày (chỉ đợt có ngày xác định) · Tiền chưa rõ khoản (M1 · Tiền về / tiền đi) · Thu thừa/thiếu | Kế toán công nợ | V2 | Thu tiền |
| Đối tượng chưa có mã Junsky | Kế toán công nợ | V4 | Tổng quan |
| Mẫu hợp đồng chờ kiểm ánh xạ / chờ CFO duyệt | Kế toán / CFO | V4 | Màn Mẫu hợp đồng |
| Hợp đồng luồng B chờ duyệt tham số | CFO | V3 | Nguồn & tham số |
| Hợp đồng lệch bộ chuẩn dự án đã hiệu lực | CFO | V8 (cảnh báo) | Lịch nghĩa vụ |

Thẻ số đếm cho các loại việc này đặt ở đầu **Danh sách hợp đồng** (mục 4), bấm là lọc.

---

## 4. Màn 1 · Danh sách hợp đồng (trang mở đầu của CRM)

**Thẻ số đầu trang** (bấm là lọc, theo vai): Chờ kiểm · Chờ ký · Đến hạn 7 ngày · Lệch chưa xử lý · Tiền chưa rõ · Trả lại.

**Cột mặc định** (đề xuất cho CRM-Q2; anh bỏ/thêm):

| # | Cột | KCN | Nhà ở | Ghi chú |
|---|---|---|---|---|
| 1 | Pháp nhân | chỉ khi xem "Tất cả" | — | |
| 2 | Mã nội bộ · Số hợp đồng | ✔ | ✔ | mã nội bộ là khóa; số HĐ là nhãn |
| 3 | Loại · loại hình doanh thu | Đất có hạ tầng / Phí quản lý / XLNT / Điện | Mua bán / Đặt cọc | |
| 4 | Khách hàng (mã Junsky – tên) | ✔ | ✔ | đối tượng dự thảo hiện nhãn "chưa có mã" |
| 5 | Dự án · lô / căn | lô, diện tích m² | dự án – giai đoạn – mã căn | |
| 6 | Giá trị hợp đồng · tiền tệ | USD (kèm VND quy đổi + tỷ giá) hoặc VND | VND | giá trị có căn cứ; thiếu căn cứ hiện "—" không hiện 0 |
| 7 | Phiên bản hiệu lực | v1 / PL02 | | phụ lục đã duyệt nhưng chưa đến ngày hiệu lực hiện nhãn riêng |
| 8 | Trạng thái giao kết | Báo giá → Soạn thảo → Chờ ký → Đã ký → Chờ kiểm → Hiệu lực / Trả lại / Hủy | | nguồn: Mẫu v<n> / Trích bản ký / Nhập tay |
| 9 | Tình hình thu theo CRM | đã thu / còn lại · % | | theo lịch và tiền đã nối |
| 10 | Công nợ ghi sổ Junsky | số dư 131 theo đối tượng (chỉ đọc) | | **bán hàng thấy cho khách mình** (anh chốt 20/10); nhãn và nền khác cột 9; nguồn `kho.cong_no_mo` (TL 40 §7), ghi "sổ đến dd/mm" |
| 11 | Đợt kế tiếp | ngày hoặc mốc sự kiện | | mốc chưa có ngày: hiện mốc, không đếm quá hạn |
| 12 | Cờ | thiếu căn cứ · lệch bản ký · lệch chuẩn · quá hạn · tiền chưa rõ · **chênh CRM ↔ Junsky** | | màu + chữ |
| 13 | Người phụ trách | ✔ | ✔ | |

Bộ lọc: pháp nhân · loại · dự án · trạng thái giao kết · cờ · người phụ trách · khoảng ngày ký / ngày hiệu lực · tìm (số HĐ, tên khách, mã căn/lô). Lưu bộ lọc theo người dùng.
Nút theo vai: Bán hàng *Lập báo giá*, *Soạn hợp đồng*; Kế toán *Tiếp nhận hợp đồng ký*; CFO *Xuất file soát*. Xuất Excel danh sách đang lọc (ghi nhật ký tải).
Trạng thái rỗng / lỗi quyền: "Không có hợp đồng trong phạm vi của bạn" (không lộ số đếm pháp nhân khác).

---

## 5. Màn 2 · Chi tiết hợp đồng (7 tab)

Đầu trang: số HĐ · khách · dự án/lô/căn · giá trị (tiền tệ) · trạng thái giao kết · phiên bản hiệu lực · nguồn tham số · nút hành động chính theo vai/trạng thái (mục 13).

| Tab | Nội dung | Nút (vai) |
|---|---|---|
| **Tổng quan** | Thẻ: giá trị · đã thu · còn lại · đợt kế tiếp · cờ. Dòng thời gian trạng thái (ai, lúc nào). Chuỗi chứng từ ngang (TL 37 §6): Hợp đồng → Đợt → Hóa đơn (M3 · Hóa đơn bán ra & doanh thu BĐS, chỉ đọc) → Tiền | — |
| **Nguồn & tham số** | Bảng: mã · tên · **giá trị hiệu lực** · đơn vị/tiền tệ · Điều/Khoản · **trích dẫn nguyên văn** · nguồn (Mẫu v<n> / Trích / Nhập tay) · trạng thái kiểm · mức quan trọng. Lọc "chỉ thiếu căn cứ". Bấm trích dẫn → ngăn phải hiện đoạn văn bản + locator; với bản ký PDF mở đúng trang | Kế toán: *Yêu cầu bổ sung*, *Đánh dấu đã kiểm*; CFO (luồng B): *Duyệt tham số* (dẫn sang K5) |
| **Lịch nghĩa vụ** | Bảng **Lần · Giá trị · Mốc thời gian · Ghi chú** (anh chốt 20/10) + cột hệ thống: % · tiền tệ · ngày tính được · đã nối · còn lại · trạng thái đợt (chưa đến hạn / đến hạn / quá hạn / đã thu đủ / mốc chưa có ngày) · phiên bản căn cứ. KCN: Giá trị hiện USD và VND quy đổi + tỷ giá ghi tay. Dòng tổng = 100% và tổng tiền | Bán hàng (chỉ khi Soạn thảo): *Sửa lịch*; Kế toán: *Mở việc xử lý* |
| **Thu tiền** | Danh sách khoản thu đã nối (ngày, BANK/proposal M1, số tiền, đợt, người nối, lý do nếu gỡ). Tổng đã nối theo đợt. Hai ô tách nhãn và nền: **"Tình hình thu theo CRM"** và **"Công nợ ghi sổ Junsky"** (chỉ đọc, kèm "sổ đến dd/mm"); **bán hàng thấy cả hai cho khách mình** (anh chốt 20/10); chênh lệch hai ô hiện cờ | Kế toán: *Nối tiền* (mở K5 V2 lọc sẵn theo hợp đồng), *Gỡ liên kết* (bắt buộc lý do) |
| **Phụ lục / phiên bản** | Danh sách phiên bản: gốc/PL · số/ngày · ngày hiệu lực · trạng thái · người kiểm/duyệt · thay đổi tham số cũ → mới · thay đổi lịch (dòng thêm/bớt/sửa). So sánh hai phiên bản cạnh nhau | Bán hàng: *Soạn phụ lục từ mẫu* / *Nộp phụ lục ký*; Kế toán: *Kiểm* |
| **Bản ký & đối chiếu** | File PDF ký (xem trong trang) · hash · ngày ký · người tải · khai có sửa · kết quả đối chiếu (chưa chọn / khớp / lệch mức n / không đối chiếu được) · bảng lệch (tham số · bản sinh · bản ký · trích dẫn · mức). Mọi bản xuất trước ký (revision, hash) | Kế toán: *Xử lý lệch* (chấp nhận có lý do / trả lại bán hàng); *Chạy đối chiếu* thủ công |
| **Lịch sử** | Nhật ký chỉ thêm: ai, lúc nào, trước/sau, căn cứ, file; lượt gọi cổng AI (loại việc, không nội dung) | *Xuất nhật ký* |

---

## 6. Màn 3 · Báo giá / lịch thanh toán dự kiến (CRM-G2)

Bố cục hai cột: **trái** form, **phải** bảng lịch + xem trước bản in.

- Form: pháp nhân (theo quyền) · loại (KCN/Nhà ở) · dự án → lô/căn (chọn từ danh mục; hiện diện tích, trạng thái lô/căn) · khách (tìm theo mã Junsky/tên/MST; hoặc *Khách mới* → đối tượng dự thảo) · giá (KCN: đơn giá USD/m² hoặc VND, tổng; nhà ở: giá VND, có/không VAT, phí bảo trì nếu có) · **tỷ giá** (ô nhập tay, bắt buộc khi tiền tệ ≠ VND; hiện người/ngày) · tiến độ: *Theo dự án* (nạp bộ chuẩn G7) / *Theo khách*.
- Bảng lịch **Lần · Giá trị · Mốc thời gian · Ghi chú**: Giá trị nhập % hoặc số tiền, ô còn lại tự tính và hiện mờ; Mốc chọn *ngày* hoặc *sự kiện* (ký · xây xong tầng n · bàn giao · sổ · ngày cố định sau ký + n ngày); KCN thêm cột USD/VND. Dòng tổng: % (phải = 100) và tiền. Thêm/xóa/kéo thứ tự dòng.
- Nút: *Lưu nháp* · *In cho khách* (PDF có số báo giá, ngày, người lập, dòng tham chiếu tỷ giá; không có số liệu nội bộ) · *Chuyển sang soạn hợp đồng* (giữ nguyên lịch) · *Hủy* (lý do).
- Chặn: tổng % ≠ 100 → không in; thiếu tỷ giá khi USD → không in; lô/căn đang có hợp đồng hiệu lực → cảnh báo (không chặn báo giá).
- Danh sách báo giá: số · ngày · khách · lô/căn · giá trị · trạng thái (nháp / đã in / đã chuyển HĐ / hủy / hết hạn) · người lập.

---

## 7. Màn 4 · Soạn hợp đồng từ mẫu (CRM-G3)

Bố cục ba cột, màn 1440 px:

| Trái · Nhập liệu (theo nhóm của ánh xạ mẫu) | Giữa · Xem trước văn bản | Phải · Kiểm tra |
|---|---|---|
| Nhóm: **Bên mua/thuê** (từ đối tượng: tên, MST/CCCD, địa chỉ, người đại diện, chức vụ, STK) · **Tài sản** (dự án, lô/căn, diện tích, vị trí) · **Giá & thuế** (giá, tiền tệ, VAT, tỷ giá) · **Lịch thanh toán** (bảng 4 cột, nạp từ báo giá) · **Điều khoản tùy chọn** (ô mẫu cho phép) · **Khác**. Trường bắt buộc có dấu; trường "theo mẫu" hiện khóa | Văn bản mẫu v<n> với ô điền được tô nền; bấm ô → nhảy tới trường trái; số tiền tự sinh "bằng chữ"; cuộn đồng bộ | Danh sách kiểm: trường bắt buộc trống · tổng % · lệch bộ chuẩn dự án (từng dòng) · khách chưa có mã Junsky · lô/căn trùng hợp đồng. Mỗi dòng bấm nhảy tới ô |

- Thanh trên của màn: mẫu đang dùng (loại · phiên bản · hiệu lực từ) — mẫu mới hiệu lực thì hợp đồng đang soạn **vẫn giữ** phiên bản cũ, hiện nhắc "có mẫu mới, bấm để chuyển (sinh lại)".
- Nút: *Lưu nháp* · *Xuất hợp đồng* (DOCX + PDF; revision +1; hash) · *Ký kết* (chỉ hiện ở trạng thái Chờ ký) · *Hủy*.
- Trạng thái: đang sinh file (việc nền, thanh tiến độ), lỗi mẫu (placeholder không có dữ liệu — nêu tên ô), xong (link tải + mở xem).

---

## 8. Màn 5 · Hộp Ký kết (CRM-G4)

Hộp thoại giữa màn, không rời trang:
1. Kéo thả **PDF bản ký** (bắt buộc; hiện tên, dung lượng, số trang, hash sau khi tải).
2. Ngày ký (mặc định hôm nay) · Người ký phía khách (tùy chọn).
3. Khai: **"Bản ký có sửa so với bản in gần nhất?"** Có / Không (bắt buộc chọn). Chọn Có → ô mô tả ngắn.
4. Tóm tắt khóa: số dòng lịch, tổng giá trị, mẫu v<n>, revision bản in.
5. Nút *Xác nhận ký kết* (mờ khi thiếu PDF hoặc chưa chọn Có/Không) · *Hủy*.
Sau xác nhận: trạng thái → Đã ký; tham số khóa; toast "Đã chuyển kế toán kiểm"; nếu khai Có hoặc được chọn kiểm mẫu → việc nền "Đối chiếu bản ký" xuất hiện ở ngăn Việc đang chạy. Tải lại cùng PDF → thông báo "đã có bằng chứng này", không tạo bản mới.

---

## 9. Màn 6 · Mẫu hợp đồng (CRM-G1)

- **Danh sách mẫu**: tên · loại · pháp nhân · phiên bản · trạng thái (Chờ kiểm ánh xạ / Chờ CFO duyệt / Hiệu lực / Hết hiệu lực) · hiệu lực từ–đến · số HĐ đã dùng · người tải/kiểm/duyệt. Nút *Tải mẫu mới* (tạo phiên bản mới của mẫu đang chọn hoặc mẫu mới).
- **Màn ánh xạ** (hai cột): **trái** danh sách ô đánh dấu tìm thấy trong DOCX (tên ô, số lần xuất hiện, đoạn ngữ cảnh); **phải** trường dữ liệu chọn từ danh mục trường (nhóm, kiểu, định dạng hiển thị: số bằng chữ, dd/mm/yyyy, VND dấu chấm) · bắt buộc · ghi chú. Ô chưa ánh xạ tô vàng; trường bắt buộc không có trong mẫu tô đỏ. Nút *Xem thử với dữ liệu giả* (sinh bản xem trước, không lưu).
- Nút theo vai: Người tải: *Gửi kế toán kiểm*; Kế toán: *Đã kiểm, gửi CFO* / *Trả lại*; CFO: *Duyệt, hiệu lực từ ngày* / *Từ chối* (duyệt là dòng V4 ở K5, hộp này là lối tắt).
- So sánh hai phiên bản mẫu: ô thêm/bớt, trường đổi ánh xạ.

---

## 10. Màn 7 · Tiếp nhận hợp đồng ký (luồng B — F1/F2, kế thừa màn "Trích tham số" của #5)

- Vùng kéo thả **PDF/DOCX bản ký** hoặc **JSON kết quả #6**; chọn loại hợp đồng (quyết định danh mục tham số); hàng đợi file với trạng thái.
- Tiến độ 9 bước + nhật ký + nút Dừng (giữ nguyên của #5); OCR scan qua ABBYY hiện là một bước.
- Kết quả: bảng tham số (cột như tab Nguồn & tham số) + **nhận trùng** (cùng hash → mở hồ sơ cũ) + **mapping** (pháp nhân, loại, khách ↔ mã Junsky, dự án/lô/căn) với ô gợi ý và trạng thái chờ khóa; nút *Bổ sung & lập tiếp* (lưu dở, giao người xử lý), *Yêu cầu bổ sung* (gửi bán hàng), *Gửi kiểm* → tạo dòng V3 ở K5 (CFO duyệt theo mục 1 file CRM, trừ khi anh đổi ở TL 41 §9).
- Tham số dạng bảng (lịch đợt) hiện thành bảng 4 cột ngay trong kết quả, mỗi dòng có trích dẫn/locator.

---

## 11. Màn 8 · Thu tiền theo hợp đồng (F7)

Không dựng sổ thu riêng. Màn này là **góc nhìn theo hợp đồng** của việc V2 ở K5:
- Trái: danh sách hợp đồng có đợt đến hạn / có tiền chưa rõ; phải: tiền từ M1 · Tiền về / tiền đi (BANK/proposal) cùng pháp nhân, cùng tiền tệ, chưa nối hết; kéo tiền vào đợt → hộp xác nhận phần tiền (cho phép một tiền → nhiều đợt, nhiều tiền → một đợt; chặn vượt phần còn lại, chặn sai pháp nhân/tiền tệ).
- Gỡ liên kết: lý do bắt buộc; lịch sử giữ. Tiền chưa rõ khoản: hiện nhãn "Vàng theo CFO-03" và nút *Hỏi phòng kinh doanh* (agent Zalo).

---

## 12. Màn 9 · Báo cáo & file soát (F8 + G8)

- Chọn pháp nhân · kỳ · phạm vi (dự án, loại) → **tổng kiểm soát** trên màn (số HĐ, tổng giá trị theo tiền tệ, đã thu, còn lại, số đợt quá hạn có ngày, số lệch chưa xử lý) → *Xuất file soát*.
- Sheet đề xuất (4 sheet hiện có + 2): Hợp đồng & phiên bản · Lịch nghĩa vụ · Liên kết tiền · Truy vết nguồn · **Chênh lệch tình hình thu CRM so với công nợ Junsky theo đối tượng** · **Giao kết** (số đếm theo trạng thái × dự án; HĐ lệch chuẩn; tỷ lệ kiểm mẫu). Không đặt nhãn "file nhập Junsky".
- Bấm một dòng số → mở danh sách lọc tương ứng (truy ngược).

---

## 13. Nút hành động × vai × trạng thái (ngôn ngữ nghiệp vụ)

| Nút | Vai | Hiện khi trạng thái | Điều kiện bấm được | Kết quả |
|---|---|---|---|---|
| Lập báo giá | Bán hàng | — | có quyền dự án | Báo giá nháp |
| Chuyển sang soạn hợp đồng | Bán hàng | Báo giá nháp/đã in | mẫu hiệu lực tồn tại cho loại | Soạn thảo, lịch giữ nguyên |
| Xuất hợp đồng | Bán hàng | Soạn thảo / Chờ ký | không còn trường bắt buộc trống; tổng % = 100 | Chờ ký, revision +1 |
| Ký kết | Bán hàng | Chờ ký | có PDF + khai Có/Không | Đã ký → Chờ kiểm |
| Thay bằng chứng | Bán hàng | Đã ký, chưa hiệu lực | lý do | PDF mới, hash mới, đối chiếu lại |
| Đánh dấu đã kiểm / Hiệu lực | Kế toán công nợ | Chờ kiểm | khách có mã Junsky; không còn lệch chưa xử lý; không còn tham số thiếu căn cứ mức ≥ 2 | Hiệu lực, sinh nghĩa vụ |
| Trả lại | Kế toán công nợ | Chờ kiểm | lý do | Soạn thảo (mở khóa), thông báo bán hàng |
| Yêu cầu bổ sung | Kế toán công nợ | Chờ kiểm / luồng B | chọn loại thiếu | việc mở cho bán hàng, đếm ngày |
| Xử lý lệch | Kế toán công nợ | có lệch bản ký | chọn "chấp nhận có lý do" hoặc "trả lại" | ghi nhật ký; cập nhật tỷ lệ kiểm mẫu |
| Nối tiền / Gỡ liên kết | Kế toán công nợ | Hiệu lực | ngân sách phần còn lại; cùng pháp nhân/tiền tệ | cập nhật tình hình thu |
| Duyệt phiên bản mẫu | CFO | Mẫu chờ CFO | không còn ô chưa ánh xạ | mẫu hiệu lực từ ngày |
| Duyệt tham số (luồng B) | CFO | Chờ duyệt ở K5 | tham số bắt buộc có trích dẫn | Hiệu lực |
| Soạn phụ lục từ mẫu / Nộp phụ lục ký | Bán hàng | Hiệu lực | mẫu phụ lục hiệu lực | phiên bản mới chờ kiểm |
| Hủy | Bán hàng (nháp) / Kế toán (sau ký) | trước Hiệu lực | lý do | Hủy; giữ lịch sử |

Nút không áp dụng thì **ẩn**; áp dụng nhưng thiếu điều kiện thì **mờ** và rê chuột hiện đúng điều thiếu (TL 37 §5.3).

---

## 14. Quy tắc hiển thị (kế thừa TL 37 §12 + #5, bổ sung cho CRM)

- Tiếng Việt; ngày dd/mm/yyyy; VND dấu chấm không lẻ; **USD luôn kèm VND quy đổi và tỷ giá + ngày + người nhập**; mọi số tiền có ký hiệu tiền tệ.
- **"—" cho chưa có căn cứ; "0" chỉ khi hợp đồng ghi 0** (NULL ≠ 0, file CRM mục 8).
- Đợt có mốc sự kiện chưa có ngày: hiện tên mốc, **không** đếm quá hạn, không tô đỏ.
- Hai nhãn không được lẫn: **"Tình hình thu theo CRM"** và **"Công nợ ghi sổ Junsky"**; đặt ở hai ô riêng, khác màu nền.
- Trạng thái giao kết luôn kèm nguồn tham số (Mẫu v<n> / Trích bản ký / Nhập tay).
- CCCD/STK: 4 số cuối ở danh sách và màn bán hàng; đầy đủ chỉ khi vai được phép mở chi tiết, có nhật ký.
- Không thuật ngữ kỹ thuật trên màn hình ("máy", "cổng AI", "đối chiếu bản ký", không "OCR/LLM/hash" — hash hiện là "mã kiểm tra file").
- Màu luôn kèm chữ/biểu tượng: Xanh đạt · Vàng cần xem · Đỏ lệch/chặn · Xám không áp dụng.
- Màn bán hàng không hiện bút toán, tri thức, số liệu pháp nhân khác; không hiện bí danh.
- **Thiết bị: chỉ máy tính 1280–1440 px** (anh chốt 20/10), cùng chuẩn #5 và K5; không thiết kế bố cục điện thoại.

---

## 15. Trạng thái cần vẽ (đầu bài cho Claude Design, sau khi chốt)

1 Danh sách hợp đồng KCN — trang mở đầu, thẻ số, có USD/VND, cờ · 2 Danh sách hợp đồng nhà ở — vai bán hàng (4 số cuối CCCD, hai ô thu CRM / công nợ Junsky) · 3 Chi tiết — tab Nguồn & tham số với ngăn trích dẫn mở · 4 Chi tiết — tab Lịch nghĩa vụ KCN · 5 Chi tiết — tab Lịch nghĩa vụ nhà ở có mốc sự kiện · 6 Chi tiết — tab Thu tiền với hai ô tách nhãn và cờ chênh · 7 Chi tiết — tab Bản ký & đối chiếu có lệch · 8 Báo giá KCN đang nhập (tổng % ≠ 100, nút In mờ) · 9 Bản in báo giá cho khách · 10 Soạn hợp đồng ba cột, có lỗi kiểm bên phải · 11 Soạn hợp đồng — nhắc có mẫu mới · 12 Hộp Ký kết thiếu PDF · 13 Hộp Ký kết hoàn tất · 14 Mẫu hợp đồng — màn ánh xạ có ô chưa ánh xạ · 15 Tiếp nhận hợp đồng ký — đang chạy 9 bước · 16 Thu tiền — kéo tiền vào đợt, bị chặn vượt · (17 Báo cáo & file soát — tổng kiểm soát).

---

## 16. Điểm đã chốt và còn mở

**Đã chốt 20/10/2026 (17:10) — bảng chọn:**
1. **Bỏ hẳn màn "Việc của tôi" trong CRM**; trang mở đầu là Danh sách hợp đồng. Sau này web trung tâm có "Việc của tôi" theo từng nhân viên cho mọi module (ghi vào điểm mở TL 40); CRM chỉ cung cấp loại việc (mục 3).
2. **"Hợp đồng bán hàng" là mục riêng** trên menu trái, 6 mục con.
3. **Bán hàng thấy cả hai**: "Tình hình thu theo CRM" và "Công nợ ghi sổ Junsky" của khách mình, hai ô tách nhãn và nền (đúng TL 40 §7).
4. **Chỉ máy tính** 1280–1440 px.

**Trả lời sau (không chặn):** cột bắt buộc anh muốn bớt/thêm ở mục 4 (CRM-Q2); hạn "chờ ký quá n ngày" cho bán hàng; có cho bán hàng tự *Hủy* hợp đồng đã ký trước khi kế toán kiểm không; 2 điểm của TL 41 §9 (CFO duyệt luồng B; tham số kiểm mẫu ngẫu nhiên).

## 17. Sau khi chốt
- Cập nhật TL 38 schema: trường theo cột mục 4–5, trạng thái mục 13, bảng mới TL 41 §5; TL 40 thêm điểm mở "Việc của tôi cấp hệ thống".
- Soạn prompt Claude Design cho 17 trạng thái mục 15 (dữ liệu giả, không tên khách/số HĐ thật) → anh chạy Claude Design → bản HTML bàn giao → đưa vào hàng đợi V16 → chỉ code khi anh ra lệnh.