# Phiếu cổng A — M9 · Vốn vay & đầu tư tài chính (Kho hợp đồng vay) · 26/10/2026

**BẢN NHÁP CHO LEAD — chỉ tài liệu; chưa có màn hình/CSDL theo thiết kế mới, chưa tự thử trình duyệt, chưa nghiệm thu.** Phạm vi phiếu: kho hợp đồng vay, hỏi đáp và báo cáo lãi suất; không mở thêm nghiệp vụ đầu tư tài chính.

**Căn cứ:** [Thiết kế M9 §1–§7](<D:/Claude/Phan mem ho tro ke toan/THIET-KE-MODULE-DE-CHOT-2026-10-20/M9-KHO-HOP-DONG-VAY-HOI-DAP-20261026.md>), [CD-015 và CD-012](CHI-DAO-TU-ANH.md), [TL 49 §1–§4](<D:/Claude/Phan mem ho tro ke toan/49-trang-chu-luoi-icon.md>), [thiết kế ma trận](THIET-KE-MA-TRAN-THAM-QUYEN.md); cùng cấu trúc [phiếu M3](PHIEU-CONG-A-M3.md), [phiếu lưới icon](PHIEU-CONG-A-TRANG-CHU-LUOI-ICON.md). CD-015 nhắc §8 nhưng tệp thiết kế đọc được chỉ có §1–§7: phần đã chốt bên dưới lấy trực tiếp CD-015. CD-015 mở lại M9, thay trạng thái “Tạm dừng” trong TL 49/thiết kế ma trận cũ.

**Bản thử:** CHỜ LEAD ĐIỀN URL/CỔNG DEMO và vai mô phỏng sau khi có giao diện. Phiếu gồm 3 phần tương ứng 3 trang; chỉ dùng hồ sơ giả khi thử. Ngày **dd/mm/yyyy**, mốc **dd/mm/yyyy hh:mm**, tiền luôn có **VND/USD**, lãi suất **%/năm**, chênh lệch **điểm %**; nhãn tiếng Việt nghiệp vụ, không lộ mã kỹ thuật.

## A. Trang chủ và kho tài liệu — trang 1/3

1. Trang chủ hệ thống → **M9 · Vốn vay & đầu tư tài chính** → ba thẻ tổng quan bấm được:

| Thẻ | Hiển thị / nơi mở |
|---|---|
| Tổng dư nợ | Số tiền từ Sheet, đơn vị, mốc kéo; mở Dư nợ & lãi suất đúng phạm vi. Nhiều đồng tiền: chờ chốt cách trình bày, không tự quy đổi. |
| Khoản vay lãi cao | Số khoản cao hơn bình quân gia quyền cùng mốc; mở danh sách tương ứng. |
| Hợp đồng chưa đủ tài liệu | Số hồ sơ và lý do thiếu; mở Kho hợp đồng đã lọc. Tiêu chí đủ/thiếu chờ Anh chốt. |

| 📁 Kho hợp đồng | ⬆ Tải lên | 💬 Hỏi đáp |
|---|---|---|
| 💰 Dư nợ & lãi suất | 📊 Báo cáo lãi suất | ⚙ Cài đặt nguồn |

Theo TL 49: thẻ/icon chỉ hiện trong quyền và pháp nhân được cấp; vào màn có thanh icon trái, Trang chủ/Lưới module, đường dẫn và dấu màn đang mở. Badge đếm **việc chờ người đăng nhập**, 0 ẩn, xám chưa quá hạn/đỏ quá hạn; không lấy tổng tài liệu làm việc chờ. Loại việc M9 chưa chốt thì chưa gán số. Thiếu nguồn hiện **Chưa có dữ liệu**, không coi là 0; lỗi tải hiện lý do tiếng Việt + **Thử lại**.

**Quyền chung:** các vai **Người thực hiện 1 · Người thực hiện 2 · Trưởng phòng · CFO · Người xem** theo phòng/pháp nhân; chỉ làm khi có ô **Xem/Lập/Sửa/Duyệt** tương ứng được Anh tick, không tự cấp theo chức danh. Chỉ Admin cấp/sửa ma trận; kiểm quyền ở máy chủ cho cả thẻ, danh sách, tệp và trích dẫn. Ánh xạ nút M9 bên dưới là **nháp cần chốt tại C1**, chưa phải ma trận thật; hành động duyệt tuân hạn mức CD-012.

2. **Kho hợp đồng** — Tìm và mở hồ sơ vay đúng pháp nhân/ngân hàng/khoản vay.
   **Trường:** bộ lọc pháp nhân, ngân hàng, mã khoản vay; loại tài liệu, tên tệp, phiên bản, trạng thái OCR, tài liệu còn thiếu; chi tiết có file gốc và dấu kiểm toàn vẹn. **Nút/quyền:** Lọc, Mở hồ sơ/tệp/phiên bản = Xem; Bổ sung tài liệu → Tải lên = Lập; Sửa thông tin gắn hồ sơ = Sửa; chưa đặt bước duyệt hồ sơ. **Trống/lỗi:** Chưa có hợp đồng/Không có kết quả; tệp không đọc được hoặc OCR lỗi phải nêu lý do, không hiện đã sẵn sàng hỏi đáp.

3. **Tải lên** — Nhận PDF scan/DOCX và gắn đúng khoản vay trước khi lập chỉ mục.
   **Trường:** tệp, loại tài liệu (chờ C1), pháp nhân, ngân hàng, mã khoản vay khớp Sheet, phiên bản, trạng thái tiếp nhận/OCR/lập chỉ mục. **Nút/quyền:** Chọn tệp, Tải lên = Lập; Sửa thông tin gắn hồ sơ = Sửa; Xem kết quả = Xem; không tự sinh bước duyệt. **Trống/lỗi:** Chưa chọn tệp; sai định dạng, thiếu thông tin, OCR hết thời gian/lỗi/hết hạn mức phải báo rõ; chưa có văn bản thì chưa đưa vào hỏi đáp.

<div style="page-break-after: always;"></div>

## B. Hỏi đáp, số liệu và báo cáo — trang 2/3

4. **Hỏi đáp** — Tra điều khoản và số liệu vay có căn cứ, chỉ dùng Local AI.
   **Trường:** phạm vi pháp nhân/ngân hàng/khoản vay, câu hỏi, câu trả lời; trích dẫn **tệp · phiên bản · trang · điều/khoản · câu nguyên văn**; số dư/lãi suất hiện hành ghi **nguồn Sheet, mốc dd/mm/yyyy hh:mm**. **Nút/quyền:** Hỏi, Mở trích dẫn đúng trang; ai được Hỏi và ánh xạ Xem/Lập chờ C1, không mặc định mọi người có Xem đều được Hỏi; không có Sửa/Duyệt câu trả lời. **Trống/lỗi:** Chưa có câu hỏi; không có căn cứ → **Không thấy trong hợp đồng**; không trích dẫn được thì không trả lời bằng số. Local lỗi/không đủ căn cứ chỉ hiển thị trích dẫn tìm được và lý do, không chuyển Cloud. Sheet lệch thông báo lãi mới nhất → báo hai nguồn, không tự chọn. Nhật ký ai/lúc nào/câu hỏi lưu nội bộ, không đưa trả lời ra ngoài máy.

5. **Dư nợ & lãi suất** — Xem snapshot của phần mềm theo dõi khoản vay, không tính lại sổ vay.
   **Trường:** pháp nhân, ngân hàng, mã khoản vay, dư nợ/đồng tiền, lãi suất áp dụng, cố định/thả nổi, lãi cơ sở + biên độ, kỳ điều chỉnh kế tiếp, ngày đáo hạn; Sheet/tab, mốc kéo, dấu kiểm toàn vẹn, dòng dữ liệu lỗi. **Nút/quyền:** Lọc, Xem snapshot = Xem; **Kéo ngay** là đề xuất chờ C1 về lịch/quyền; không có nút sửa số dư/lãi suất, không có duyệt để ghi lại Sheet. **Trống/lỗi:** Chưa cấu hình nguồn/Chưa có snapshot; lỗi quyền đọc, thiếu cột, trùng mã, sai ngày/số ghi rõ dòng/cột; dữ liệu thiếu không đổi thành 0. Lần kéo lỗi không được gắn mốc mới cho số cũ.

6. **Báo cáo lãi suất** — Xếp khoản lãi cao để Anh xem cơ sở xin điều chỉnh/đàm phán.
   **Trường:** kỳ báo cáo, nguồn/mốc; pháp nhân, ngân hàng, mã khoản vay, dư nợ/đơn vị, lãi suất, cách tính cố định/thả nổi = lãi cơ sở + biên độ, bình quân gia quyền, chênh lệch, nhãn Lãi cao, kỳ điều chỉnh, đáo hạn; điều khoản biên độ/điều chỉnh/phí trả trước hạn có trích dẫn. Cột **Lãi trả thêm ước tính một năm** = dư nợ × chênh lãi suất (điểm % chia 100), có đơn vị, ghi rõ ước tính; xếp chênh cao nhất trước, cảnh báo điều chỉnh trong 30 ngày.
   **Nút/quyền:** Xem/Mở căn cứ/Xuất Excel = Xem; Lập báo cáo = Lập (ánh xạ nháp); không sửa số nguồn. **Anh duyệt trước khi gửi ai**; ô Duyệt/cách ghi nhận chờ C1, chưa thêm luồng K5 hoặc nút gửi. **Trống/lỗi:** Chưa có snapshot/kỳ báo cáo; thiếu dư nợ/lãi suất → Chưa đủ dữ liệu, không kết luận lãi cao hay ước tính; thiếu điều khoản → Chờ nối trích dẫn, không bịa căn cứ.

7. **Cài đặt nguồn** — Khai báo nguồn Sheet chỉ đọc và lịch lấy snapshot.
   **Trường:** Sheet, tab kết quả, ánh xạ cột, tài khoản dịch vụ được cấp chỉ đọc (không hiện khóa), lịch/giờ kéo, lần kéo gần nhất và kết quả. **Nút/quyền:** Xem cấu hình, Lưu cấu hình, Kéo ngay (chờ C1); **chỉ Admin**, đồng thời đúng ô Xem/Lập/Sửa liên quan; không có Duyệt để nâng quyền Sheet. **Trống/lỗi:** Chờ Sheet/tab/tài khoản dịch vụ; cấu hình thiếu, không được cấp quyền đọc hoặc lỗi kéo → thông báo rõ, không hiện kết nối thành công. Khóa chỉ do ứng dụng đọc từ `.env` lúc chạy.

**Đã chốt — trích ý CD-015, không hỏi lại:**

| Căn cứ | Quyết định phải giữ |
|---|---|
| Mục 2 | Chỉ mục và hỏi đáp chỉ Local AI qua cổng AI phần mềm; không Cloud, kể cả Mask v2. |
| Mục 3 | Trích dẫn tệp/trang/điều khoản/câu nguyên văn; số dư/lãi suất từ snapshot Sheet có mốc; không căn cứ thì không trả lời bằng số. |
| Mục 4 | Google Sheets API chỉ đọc; khóa chỉ trong `.env`; thử bằng Sheet giả, chờ thông tin để nối thật. |
| Mục 5 | Báo cáo hằng tháng; “lãi cao” = cao hơn bình quân gia quyền theo dư nợ của danh mục cùng mốc; cảnh báo trước kỳ điều chỉnh 30 ngày; không tự gửi ra ngoài. |
| Mục 6 | OCR scan dùng cách ABBYY Hot Folder của Review, không sửa bản gốc đang đóng băng. |

<div style="page-break-after: always;"></div>

## C. Cần Anh chốt và điều kiện thử — trang 3/3

### C1. Cần Anh chốt

Các đề xuất dưới đây **chưa được chọn thay Anh**; phần phụ thuộc giữ trạng thái chờ.

| Điểm mở / căn cứ | Nội dung cần quyết định |
|---|---|
| Loại tài liệu — §6 #1 | Có nhận đủ HĐ tín dụng, khế ước nhận nợ, phụ lục, HĐ bảo đảm, thông báo điều chỉnh lãi như đề xuất không? Danh mục trong mã chưa thay quyết định này. |
| Quyền — §6 #6, CD-012 | Ai được hỏi đáp: CFO, kế toán vay, người xem theo pháp nhân như đề xuất? Anh tick vai × màn × Xem/Lập/Sửa/Duyệt; chốt ánh xạ Hỏi, Kéo ngay, Lập/Xuất báo cáo và cách ghi nhận Anh duyệt trước khi gửi. Không tự cấp CFO mọi pháp nhân. |
| Lịch kéo — §6 #4 | Một lần/ngày + Kéo ngay như đề xuất hay lịch khác; giờ nào, vai nào được kéo ngay? |
| Nguồn thật — §6 #5 | Sheet nào, tab kết quả nào, tài khoản dịch vụ nào, ai cấp quyền chỉ đọc; xác nhận ánh xạ cột/mã khoản vay. Chưa có thì chưa nối thật. |
| ABBYY — hiện trạng mã | Có gộp sổ đếm trang M9 với Review không, ai quản lý? Mã ghi hạn mức giấy phép chung 5.000 trang/30 ngày nhưng hai sổ đang tách; chưa bảo đảm hạn mức chung. |
| Ngày lập báo cáo — §6 #3 | Hằng tháng đã chốt; có chọn ngày làm việc đầu tháng như đề xuất không? Chưa chốt giờ chạy. |
| Danh mục nhiều đồng tiền | Chốt phạm vi danh mục dùng tính bình quân và cách hiển thị thẻ khi có VND/USD; mã hiện tính riêng từng đồng tiền, chưa coi đó là policy đã duyệt; không tự quy đổi/cộng khác đồng tiền. |
| Đủ tài liệu / việc chờ — §3, TL 49 | Bộ tài liệu bắt buộc theo hồ sơ, cách đếm “chưa đủ”, loại việc chờ/ai phụ trách và điều kiện quá hạn để gắn badge; không tự đặt hạn mới. |

### C2. Đã có mã thuần / chưa làm

Đối chiếu tĩnh [thư mục M9](../../src/kho_tri_thuc/m9/); **không xác nhận test đạt hay đã tích hợp**.

| Phần | Đã có | Chưa làm/nối theo thiết kế mới |
|---|---|---|
| Tài liệu + OCR | `tai_lieu_vay.py`: đọc DOCX, cắt điều/khoản, hash/thông tin trong bộ nhớ; trang dựa ngắt trang có trong DOCX. `ocr_hot_folder.py`: bộ nối Hot Folder, cache DOCX, sổ trang riêng. | Kho file gốc/phiên bản nghiệp vụ và CSDL; nối tải lên; kiểm mở đúng trang bản gốc (không suy trang DOCX như bản dàn trang); xử lý quyết định gộp sổ. Cache OCR không phải kho hợp đồng. |
| Tìm + hỏi | `chi_muc_vay.py`: tìm từ khóa BM25, trích dẫn, cấu trúc JSON. `hoi_dap_vay.py`: qua cổng AI, chỉ nhận kết quả Local có căn cứ. | Vector/embedding Local, lưu chỉ mục bền vững, tích hợp quyền/pháp nhân, nối hỏi đáp snapshot và nhật ký đầy đủ theo §5. |
| Sheet | `snapshot_sheet.py`: chuẩn hóa dữ liệu có sẵn trong bộ nhớ, mốc/hash, báo lỗi dòng/cột. | Gọi Google API chỉ đọc, lịch kéo/Kéo ngay, lưu snapshot CSDL; nối Sheet thật. |
| Báo cáo | `bao_cao_lai_suat.py`: bình quân theo dư nợ, đánh dấu lãi cao, ước tính, cảnh báo 30 ngày, xuất Excel trong bộ nhớ. | Nối điều khoản/trích dẫn (hiện còn trống), lịch hằng tháng, giao diện và ghi nhận duyệt. |
| Khung module | Sáu tệp xử lý trên. | Sáu màn, thẻ/lưới icon, API tích hợp, CSDL và quyền theo thiết kế mới; chưa có DEMO M9 để thử. |

### C3. Lead tự thử trước khi gửi Anh

Đánh **Đạt/Không đạt + ghi chú** sau khi có DEMO: (1) từng vai/pháp nhân chỉ thấy đúng thẻ/icon/tệp/trích dẫn, chặn cả truy cập trực tiếp; (2) bấm thẻ khớp danh sách, thanh icon/Back đúng TL 49; (3) PDF scan/DOCX giả đi tới trích dẫn mở đúng trang, thử OCR lỗi/hạn mức; (4) hỏi có/không căn cứ, Local lỗi, Sheet lệch hợp đồng; (5) snapshot thiếu/lỗi không thành số 0, báo cáo/Excel đúng mốc/đơn vị/ước tính và cảnh báo 30 ngày, không gửi ra ngoài. **Hiện chưa thực hiện các bước này.** Không tính lại dư nợ/lịch trả/lãi, không sửa Sheet, không bút toán/đẩy Junsky.

**Kết luận của Anh:** [ ] Đạt về bố cục/phạm vi nháp  [ ] Cần sửa (ghi màn)  [ ] Chờ chốt C1. Duyệt phiếu nháp không đồng nghĩa nghiệm thu phần mềm.
