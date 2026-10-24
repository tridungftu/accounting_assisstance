# Báo cáo V11 — Sửa cách tạo tri thức theo 5 case T8 (11/10/2026)

Người thực hiện: Claude (phiên Cowork), theo ghi chú `var/vong-2/phan-tich-loai-giao-dich/00-GHI-CHU-CAC-CASE.md` và tài liệu dự án số 25.
Quy tắc giữ nguyên: **không tự nhập Junsky; chỉ giao dịch "Đã đồng ý" mới được xuất.** Mọi mức tin cậy mới chỉ đổi màu đề xuất (Xanh/Vàng/Đỏ), không bao giờ đổi trạng thái.

## 1. Kết luận

- **Chạy lại T8 (máy học đến 30/06/2026, chấm bằng chứng từ Junsky tháng 8)** — cùng dữ liệu, cùng cách chấm với V10:

| | V10 | V11 |
|---|---|---|
| Xanh | 27 dòng · TK đối ứng đúng 19/20 · đối tượng đúng 12/12 | **41 dòng · 35/36 · 27/27** |
| Vàng | 44 dòng · 25/41 · 20/28 | 52 dòng · 37/44 · 36/37 |
| Đỏ | 34 dòng · 5/26 · 8/16 | 12 dòng · 5/7 · 7/7 |
| Dòng sai TK hoặc sai đối tượng | 44 | **10** |

  - Cách chấm: ghép dòng sao kê với chứng từ Junsky tháng 8 theo ngày + số tiền (gộp dòng 112; nhiều lần chuyển cùng ngày = 1 chứng từ), so TK đối ứng và đối tượng. Không có chứng từ tháng 7–8 nào được dùng để học.
  - Dòng Xanh sai duy nhất: một khoản chi cho công ty liên quan, 30/30 chứng từ cùng dạng trước đó ghi 33111, kế toán tháng 8 ghi 12831 (cho vay) — trường hợp phải phán đoán.
- **5 case Anh nêu đều ra đúng trong chạy thử:** phí SMS → Xanh, Nợ 1331 + 6427 / Có 112111, "106/106 chứng từ (06/2025–06/2026)"; Sunrise, An Thuận, Hoàng Dũng → đúng đối tượng, Có 131171; trả nợ vay → Nợ 34112.
- Kiểm thử: **240/240 test PASS** trên Python 3.13 và 3.11 (224 test cũ + 16 test V11, dữ liệu giả). Một lượt rà soát độc lập, 11 phát hiện đã sửa (ghi ở mục 5).

## 2. Thay đổi phần lõi (theo lỗi H1–H16 trong ghi chú case)

| Lỗi | Sửa |
|---|---|
| H1 Quy tắc từ khóa ghép "chết" | `A + B` được dịch thành điều kiện "có cả A và B", so theo biên từ (`tri_thuc/matching.py`). 192 quy tắc sống lại. |
| H2/H3 Chứng từ có VAT bị bỏ qua | Gộp các dòng 112 cùng TK trước khi học và trước khi so "Đã có trong Junsky" (`v9b.py`). |
| H4 Quy tắc nháp thắng tri thức sổ | Quy tắc yếu (độ ổn định < 0,9, gặp < 3 lần, trạng thái nháp, hoặc từ đơn quá rộng chưa đủ 5 lần đúng) không chặn bước học từ sổ nữa; nếu sổ có mẫu nhất quán, quy tắc chỉ còn là gợi ý và màn hình nói rõ. |
| H5 So từ khóa theo chứa chuỗi | So theo biên từ. |
| H6/H15 Ngưỡng giống diễn giải cứng | **Vân tay diễn giải**: bỏ số, ngày, số điện thoại, "VND", từ nối chung ("thanh toan", "chuyen tien"…); diễn giải ngắn của kế toán khớp diễn giải dài của ngân hàng khi trùng các từ đặc trưng. |
| A5 Xác suất đo được | Mẫu học từ sổ xét **cửa sổ 12 tháng gần nhất** của các chứng từ tương tự; nhất quán 100 % và ≥ 3 chứng từ → Xanh; màn hình ghi "n/n chứng từ (từ–đến)". Đa số ≥ 80 % → Vàng kèm phương án. |
| H7/H12 Không nhận diện theo tên | Mô-đun `tri_thuc/ten_doi_tuong.py`: chuẩn hóa viết tắt (CT/CTCP/CTY CP/TNHH MTV/XNK…), trùng hẳn và duy nhất → mức mạnh; gần giống → Vàng kèm chip chọn; tên ứng nhiều mã → liệt kê. |
| H13 Tên chỉ nằm trong diễn giải | Tìm tên danh mục trong diễn giải (đúng thứ tự từ, cửa sổ ngắn, phải có từ hiếm) → Vàng "cần xem". |
| H10/H11 Ánh xạ STK sai | Sau khi nhận diện bằng STK, so tên trên sao kê với tên của mã; tên trỏ sang mã khác trong danh mục → bỏ ánh xạ, báo "cần Anh xác nhận"; Anh Đồng ý thì danh bạ học lại STK → mã đúng. Cùng tên nhiều mã → ưu tiên mã sổ đang dùng. |
| H14 Dòng đã khớp Junsky không lấy đối tượng | Dòng "Đã có trong Junsky" hiển thị đúng bút toán của chính chứng từ đó (đối tượng, dự án, TK, nhiều dòng). |
| H8 Nhiều lần chuyển = 1 chứng từ | Gộp các dòng cùng ngày, cùng chiều, cùng STK/tên; tổng bằng đúng một chứng từ chưa được dòng nào khác nhận → cả nhóm "Đã có trong Junsky" (ghi rõ "n lần chuyển = 1 chứng từ"). Một chứng từ không bao giờ bị hai nhóm cùng nhận. |
| H9 Công nợ không được dùng | Hóa đơn/công nợ mở của đối tượng: khớp đúng số tiền (hoặc tổng các lần chuyển trong ngày) → mức mạnh; chỉ có một tài khoản còn số dư đủ → Vàng; nhiều tài khoản → chip gợi ý. |
| H16 Gợi ý TK theo tần suất chung | Gợi ý "TK hay gặp" ưu tiên chứng từ cũ có từ đặc trưng trùng diễn giải (trả nợ vay → 341x). |
| F4 Khóa số khế ước | Khi Anh Đồng ý một dòng không có STK đối ứng, các số dài ≥ 10 chữ số trong diễn giải (số TK vay, số hợp đồng; không tính số tiền, ngày, STK) thành khóa riêng: lần sau cùng số → "theo lần Anh đã duyệt". |

## 3. Chức năng mới trên màn hình

- **Ghi chú cho AI / gửi Claude** (mỗi giao dịch): nút "Ghi chú cho AI" mở ô ghi chú; "Lưu ghi chú"; "Gửi Claude (tạo gói ngữ cảnh)" tạo file Markdown gồm giao dịch, đề xuất, vì sao, số đo, căn cứ, chứng từ Junsky và ghi chú của Anh, lưu ở `var\web-that\ghi-chu-ai\` (bản mới nhất: `MOI-NHAT.md`). Trong Cowork, Anh chỉ cần nói "đọc ghi chú AI mới nhất".
- **Chế độ chấm điểm (so với Junsky)** ở màn Nguồn dữ liệu: bật → máy không dùng chứng từ sau mốc học để học, **không đánh dấu "Đã có trong Junsky"**, không hiện chứng từ khớp; nút **So với Junsky** ở màn Định khoản chấm từng dòng và ghi file `SO-VOI-JUNSKY.xlsx` (sheet TONG HOP, CHI TIET). Tắt trước khi dùng thật.
- Chip "Đối tượng gợi ý theo tên", chip "TK đối ứng gợi ý" (công nợ đang mở), ghi chú mâu thuẫn danh bạ STK, dòng "Vì sao" có số đo và tên quy tắc bị hạ quyền.
- AI cục bộ (tùy chọn, tắt mặc định): `settings.local_ai` trong `source-settings.json` (`enabled`, `url` chỉ nhận localhost, `model`). Chỉ được hỏi khi so tên cho ra nhiều ứng viên; câu trả lời luôn ở mức Vàng.

## 4. API mới (chỉ trên máy, có mã phiên)

| Phương thức | Đường dẫn |
|---|---|
| POST | `/api/that/quick/ai-note` {run_id, id, note} |
| POST | `/api/that/quick/ai-context` {run_id, ids?} → file + markdown |
| POST | `/api/that/quick/score` {run_id} → bảng chấm + file |
| POST | `/api/that/open` {ai_folder: true} |
| POST | `/api/that/learning-settings` nhận thêm `scoring_mode`, `local_ai` |

Kho: migration v20 thêm `quick_items.ai_note`, `ai_note_at`. `rows()` trả thêm `levels`, `stats`, `name_options`, `account_options`, `identifier_conflict`, `group`, `demoted_rule`, `ai_note`.

## 5. Rà soát độc lập — đã sửa

1. Nhóm nhiều dòng không được nhận chứng từ đã thuộc một dòng khác; hai nhóm cùng tổng → không nhóm nào được đánh dấu.
2. AI cục bộ: bắt mọi lỗi, không theo chuyển hướng, không đọc quá 2 MB.
3. Chế độ chấm điểm: chứng từ đáp án không lộ ở "Xem căn cứ" hay số CT; xếp hạng mã trùng tên chỉ dùng sổ đến mốc học.
4. Khóa số: bỏ số tiền, ngày, số < 10 chữ số; tối đa 2 khóa.
5. Vân tay: thêm từ nối chung vào danh sách bỏ; nhánh nới lỏng cần ≥ 3 từ trùng.
6. Ánh xạ STK "Cao"/"Trung bình" được tin; ánh xạ yếu chỉ bị gạt khi tên sao kê trỏ sang mã khác, nếu không chỉ ghi chú.
7. Ghi chú AI đang gõ không mất khi màn hình tải lại.
8. Tên trong diễn giải phải có từ hiếm không phải từ của câu diễn giải.
9. Từ khóa ghép viết `A+B`/thường/có dấu vẫn được dịch đúng.
10. Cờ AI cục bộ chỉ "bật" khi URL là localhost.
11. Chỉ hạ quyền quy tắc có số đo (từ bộ quy tắc); không hạ quyền CASE.

## 6. Giới hạn còn lại

- Chứng từ tháng 7–8 không được "bỏ" khỏi kho; chế độ chấm điểm **giấu** chúng khỏi việc học và khỏi đánh dấu, rồi dùng làm đáp án. Danh sách công nợ (dgbList) là ảnh chụp hiện tại nên vẫn chứa thông tin sau mốc.
- Đối tượng chỉ học từ sổ từ ngày "Chỉ học đối tượng từ" (mặc định 01/07/2026); phí SMS vì vậy chưa có đối tượng ngân hàng — Anh duyệt một lần là máy nhớ.
- Trường hợp phán đoán (cho vay công ty liên quan, nhân viên nộp hộ, hai cách ghi đối tượng cho trả nợ vay) vẫn cần Anh quyết.

## 7. Bản vá V11.1 (11/10/2026, chiều) — "chạy lại không thấy khác"

- **Nguyên nhân:** phần mềm V10 mở từ 10/10 vẫn chạy ẩn trên cổng 8766. `start-web.ps1` thấy cùng kho, cùng phiên bản `0.3.0` nên dùng lại nó; mã V11 chưa bao giờ được nạp (kho vẫn ở schema 19, chưa có migration v20; cài đặt chưa có `scoring_mode`).
- **Sửa khởi động:** phiên bản lên `0.4.0`; `/api/health` trả thêm `started_at`, `pid`. `start-web.ps1` đọc phiên bản từ mã trên đĩa; nếu phần mềm đang chạy là của cùng kho nhưng khác phiên bản hoặc mã trên đĩa mới hơn lúc nó khởi động → tự tắt tiến trình python đó (theo `pid`, hoặc theo cổng với bản cũ) rồi mở bản mới; chờ cổng giải phóng tối đa 90 giây. Kho/ứng dụng khác trên cổng → vẫn báo lỗi như cũ.
- **Sửa chế độ chấm điểm:** "Đề xuất lại" khi đang bật chấm điểm tính lại **cả dòng "Đã có trong Junsky"** (trước đây chỉ dòng Chờ). Dòng đó hiện như dòng Chờ nhưng vẫn bị giữ ngoài mọi file xuất. Đang bật chấm điểm thì không xuất được File soát; "So với Junsky" báo lỗi nếu còn dòng "Đã có trong Junsky" chưa tính lại. Tắt chấm điểm + "Đề xuất lại" → các dòng được đánh dấu lại.
- **Kiểm chứng trên dữ liệu thật (cloud, đúng kịch bản của Anh):** lần T8 làm ở chế độ thường (87 dòng "Đã có", 18 Chờ) → bật chấm điểm, mốc 30/06 → Đề xuất lại → 105 Chờ, 0 dòng lộ đáp án → So với Junsky: Xanh 41 (TK đúng 35/36, đối tượng 27/27), Vàng 52 (37/45, 37/38), Đỏ 12 (5/7, 7/7) → tắt chấm điểm + Đề xuất lại → 87 "Đã có", 18 Chờ.
- Kiểm thử: 243/243 PASS (Python 3.13 và 3.11); `start-web.ps1` thử bằng PowerShell 7: khởi động mới, dùng lại, tự khởi động lại khi mã đổi, tắt bản 0.3.0 không có `pid`.

## 8. V11.2 (12/10/2026) — Kho thử đã xóa thật dữ liệu Junsky sau 30/06

- **Bối cảnh:** chạy chấm điểm trên kho thật vẫn ra 87 dòng "Đã có trong Junsky" vì ngày 30/06/2026 được nhập vào ô "Chỉ học đối tượng từ ngày" (ô "Máy học từ sổ đến" trống) và công tắc Chế độ chấm điểm chưa bật. Anh chọn cách **kho thử đã xóa thật** thay vì giấu dữ liệu trong kho thật.
- **Kho thử:** mở bằng `MỞ PHẦN MỀM THỬ T8.cmd` (cổng 8767, thư mục `var\web-thu-T8`, kho `var\plhn-thu-T8`). Nền Junsky đọc từ thư mục `Mang ngan hang\Thu nghiem T8 (hoc den 30-06)`: sổ NKC chỉ có chứng từ đến 30/06/2026 (4.222 chứng từ trên bản thử đám mây); danh mục, dgbList giống bản thật. Kho thật không bị động đến.
- **Chấm điểm:** thiết lập mới `answer_ledger` (đường dẫn sổ NKC đầy đủ). "So với Junsky" đọc file đó **chỉ để chấm**, không nạp vào kho. Bảng chấm và file `SO-VOI-JUNSKY.xlsx` ghi rõ "Đáp án lấy từ". Màn Định khoản hiện băng "Kho thử chấm điểm: sổ Junsky trong kho này chỉ có đến …". Kho thử không xuất File soát.
- **Thử trên đám mây với đúng các file của Anh (hash khớp):** kho thử có chứng từ đến 30/06/2026; thả Sao kê T08 → 105 dòng Chờ, 0 "Đã có"; Xanh 41 (TK đúng 35/36, đối tượng 27/27), Vàng 52 (37/45, 37/38), Đỏ 12 (5/7, 7/7) — trùng kết quả chế độ chấm điểm trên kho thật.
- Kiểm thử: 244/244 PASS (Python 3.13 và 3.11). Phiên bản 0.4.1.

## 9. V11.3 (12/10/2026, tối) — Xóa dữ liệu Junsky tháng 7–8 khỏi kho thật (theo yêu cầu Anh)

- **Bối cảnh:** Anh vẫn mở kho thật (`MỞ PHẦN MỀM.cmd`), đã đặt mốc học 30/06 nhưng công tắc chấm điểm chưa bật → "Đề xuất lại" chế độ thường giữ 87 dòng "Đã có". Anh yêu cầu xóa dữ liệu Junsky tháng 7, 8 và sẽ cấp lại sau.
- **Cách làm:** kho thật cũ (`var\plhn-that\kho.sqlite` + `raw\`) chuyển nguyên vẹn sang `var\sao-luu-truoc-xoa-T7T8-20261012\`; nguồn Junsky của kho thật trỏ sang thư mục `Mang ngan hang\Thu nghiem T8 (hoc den 30-06)` (sổ NKC chỉ đến 30/06/2026; danh mục, dgbList, bộ quy tắc giống hệt bản thật — đã so hash); lần mở tới phần mềm tự tạo kho mới và nạp nền từ đó. Kho cũ không có quyết định nào của Anh (0 dòng đã duyệt, 0 lần xuất, tri thức chỉ do hệ thống tự duyệt), nên không mất gì.
- **Chấm điểm:** bật sẵn chế độ chấm điểm, `answer_ledger` = sổ NKC đầy đủ (chỉ đọc để chấm). "Chỉ học đối tượng từ ngày" trả về 01/07/2026.
- **Sửa lỗi nạp lại Junsky (có từ trước):** "Nạp lại" khi file Junsky thay đổi từng hỏng với `KNOWLEDGE_OVERLAP` vì danh mục được tạo bản mới chồng hiệu lực. Nay dòng danh mục không đổi được giữ nguyên, dòng đổi thì thay thế bản cũ. Đã thử: kho cắt 30/06 → đổi sang sổ đầy đủ → Nạp lại → 4.507 chứng từ đến 29/08/2026; tắt chấm điểm + Đề xuất lại → 87 "Đã có", 18 Chờ.
- **Cấp lại dữ liệu sau này:** trỏ lại ba đường dẫn Junsky về `Mang ngan hang`, tắt chế độ chấm điểm, "Nạp lại".
- Kiểm thử: 245/245 PASS (Python 3.13 và 3.11). Phiên bản 0.4.2.

## 10. V11.4 (13/10/2026) — Vì sao Sunrise, tiền nước Hanvico vẫn Vàng

- **Tiền nước (5 dòng, 331.00003 Hanvico):** tên trên sao kê "CONG TY CP NUOC SACH HA NAM", danh mục ghi "Công ty cổ phần Nước sạch Hà Nam (Hanvico)" → máy coi là "gần giống" vì phần trong ngoặc. Ngoài ra danh bạ STK (file đối tác) gắn số tài khoản này cho 331.00145 (Nước sạch Hà Nội) — máy đã gạt ánh xạ sai đó. **Sửa:** tên thương mại trong ngoặc là phần không bắt buộc; hai mã cùng tên rút gọn thì vẫn coi là mơ hồ. Khi gạt ánh xạ sai và tên sao kê trùng đúng tên mã khác → mức mạnh. Kết quả: 5 dòng → Xanh, đúng TK và đối tượng (so sổ T8).
- **Sunrise (9 dòng, DVB1.SUNRISE.01):** TK Có 131171 lấy từ công nợ mở, trước đây luôn Vàng nếu không khớp đúng số tiền. Đồng thời "căn cứ" hiển thị 2 chứng từ của đơn vị khác vì từ "PLASCHEM HA NAM" (tên công ty mình) bị coi là từ giống nhau. **Sửa:** (1) đối tượng xác định chắc chắn + chỉ một TK công nợ mở đủ số tiền → mức mạnh `OPEN_ITEM_SINGLE`; (2) các từ trong tên công ty mình không còn là bằng chứng giống diễn giải. Sau sửa, máy tìm đúng lịch sử của Sunrise: 10 chứng từ 04–12/2025, 8/10 ghi **Có 344**, khác TK công nợ mở 131171 → vẫn **Vàng**, dòng "Vì sao" ghi rõ mâu thuẫn. Kế toán T8 ghi Có 131171, dự án KCN-DVI2 → máy đúng cả hai.
- **Chạy lại T8 (kho cắt 30/06, chấm bằng sổ đầy đủ):** Xanh 41 → 47 (TK đúng 41/42, đối tượng 33/33), Vàng 52 → 46, Đỏ 12 → 12. Đổi mức: 5 dòng tiền nước Vàng → Xanh (đúng); 1 dòng thu tiền thuê đất Đỏ → Xanh (đúng); 1 dòng chi 150.000 VND Vàng → Đỏ (trước và sau đều sai TK).
- Kiểm thử: 247/247 PASS (Python 3.13 và 3.11). Phiên bản 0.4.3.

### 10b. Quyết định của Anh ngày 13/10 (V11.4, phiên bản 0.4.4)

- **Công nợ mở thắng lịch sử cũ (phương án 2):** đối tượng chắc chắn + chỉ một TK công nợ mở đủ số tiền → Xanh; **dự án lấy theo chính công nợ mở đó**. Lịch sử khác TK chỉ còn là dòng "Lưu ý"; khi lịch sử ghi 344 còn công nợ là 131, dòng lưu ý ghi thêm "theo Anh: 344 chỉ dùng cho lần đặt cọc ban đầu, các lần thu sau ghi 131".
- **Rút tiền mặt nhập quỹ:** tệp mới `TRI-THUC-CFO.json` (cạnh tệp cấu hình) chứa các quy tắc Anh quyết định trong trao đổi với Claude; phần mềm đọc mỗi lần mở và duyệt dưới tên Anh (`CFO_NTD`), quy tắc không đổi thì không tạo bản mới, quy tắc sửa thì thay bản cũ. Quy tắc **CFO-01**: chi, diễn giải có số căn cước (CC/CCCD + 9–12 chữ số) và nhận ra mã nhân viên (NV.…) → Nợ 1111 / Có TK ngân hàng, Xanh; không nhận ra mã nhân viên → Vàng.
- **Chạy lại T8 (kho cắt 30/06, chấm bằng sổ đầy đủ):** Xanh **62** (TK đúng 54/55, đối tượng 46/46), Vàng 33, Đỏ 10. Đổi mức so với 0.4.2: 18 Vàng → Xanh và 3 Đỏ → Xanh (đều đúng TK, đối tượng khi so được); 1 Vàng → Đỏ (dòng 150.000 VND, trước sau đều sai TK). Khoản rút tiền mặt ngày 27/08 khớp Junsky (Nợ 1111, NV.KET.05); hai khoản 03/08 không có chứng từ phía ngân hàng trong sổ để so.
- **Còn tồn:** 6 dòng Xanh máy điền dự án KCN-DVI0 (theo quy tắc chờ duyệt) trong khi kế toán để trống dự án; 1 dòng Xanh sai TK (cho công ty liên quan vay, 12831).
- Kiểm thử: 248/248 PASS (Python 3.13 và 3.11).

## 11. V11.5 (15/10/2026) — Màn hình "Tri thức CFO"

Anh chốt 15/10: (1) xem/quản lý tri thức CFO bằng **màn hình trong phần mềm**; (2) CFO-01 **giữ Xanh**; (3) nguyên tắc 344/131 **chuyển vào tệp tri thức CFO**.

- **Màn "Tri thức CFO"** (mục 4 trên thanh trái): mỗi quy tắc hiện mã, loại (QUY TẮC / LƯU Ý), ngày Anh duyệt, trạng thái, KHI – THÌ – NGUỒN bằng lời, và bảng **đã dùng theo tháng**: số lần áp dụng, Anh đồng ý giữ nguyên, Anh sửa, bỏ qua, chưa xử lý. Nút **Tắt quy tắc / Bật lại**: ghi vào tệp và áp dụng ngay vào kho (tắt = thu hồi phiên bản đang dùng; bật lại = phiên bản mới); bấm "Đề xuất lại" để tính lại giao dịch đang chờ.
- **Tệp `TRI-THUC-CFO.json`** nay có hai loại: `QUY_TAC` (định khoản, như CFO-01) và `LUU_Y` (chỉ thêm dòng lưu ý, như **CFO-02**: lịch sử ghi 344 nhưng công nợ mở là 131 → "344 chỉ dùng cho lần đặt cọc ban đầu, các lần thu sau ghi 131"). Phần viết cứng trong mã đã bỏ.
- **Công nợ mở thắng cả lịch sử nhất quán 100 %** (đúng phương án 2: "luôn Xanh"), không chỉ lịch sử đa số. Chạy lại T8: không đổi kết quả (Xanh 62 · TK đúng 54/55 · đối tượng 46/46; Vàng 33; Đỏ 10).
- Kiểm thử: 249/249 PASS (Python 3.13 và 3.11); màn hình thử bằng trình duyệt tự động (không lỗi JavaScript, tắt/bật hoạt động). Phiên bản 0.4.5.
