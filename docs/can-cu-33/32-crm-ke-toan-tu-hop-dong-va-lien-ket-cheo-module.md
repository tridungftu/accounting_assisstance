# 32 · "CRM kế toán" từ trích tham số hợp đồng & bản đồ liên kết chéo giữa các chu trình

**Ngày lập:** 16/10/2026 · **Nguồn ý tưởng:** anh Dũng (16/10): (1) dùng "#6 Trích tham số hợp đồng bằng AI local" làm CRM cho M3 · Hóa đơn bán ra & doanh thu BĐS; (2) các chu trình liên kết chéo: Phải trả ↔ TSCĐ ↔ XDCB; Phải thu ↔ Thu tiền.
**Căn cứ:** tài liệu 01 (QT02 không làm thay nghiệp vụ gốc; "quản lý bán hàng & môi giới BĐS" đã cắt, N4/N5 nhận hợp đồng đã chốt), 07 (bậc 0 khớp chứng từ công nợ), 08 (`EntryDM` mã chứng từ công nợ trong file Junsky), 29, 31; `DANH-MUC-DU-AN.md` mục #6 (theo mô tả, chưa mở mã).
**Quy ước gọi tên:** từ nay mã module luôn kèm tên chu trình (anh yêu cầu 16/10).

---

## 0. Kết luận trước

- **Ý tưởng dùng #6 làm CRM là đúng hướng, với phạm vi "CRM kế toán"**: trích tham số từ hợp đồng mua bán / thuê đất đã ký → nạp vào **danh mục hợp đồng (A1)** kèm **lịch thu theo đợt** và **trạng thái vòng đời** (ký → đang thu → bàn giao → thanh lý). Đó là toàn bộ những gì M3 · Hóa đơn bán ra & doanh thu BĐS và M1 · Tiền về / tiền đi cần. Không làm phần CRM bán hàng (pipeline, lead, môi giới) — đúng QT02 và phạm vi đã cắt ở tài liệu 01.
- **Điều kiện để dùng được:** #6 đang tối ưu cho hợp đồng xây dựng (36+ tham số, có đáp án mẫu); cần **bộ tham số mới + đáp án mẫu mới** cho hợp đồng thuê đất KCN và mua bán nhà ở; mọi tham số trích ra là **đề xuất có trích dẫn nguyên văn**, kế toán duyệt trước khi vào danh mục; phụ lục thay đổi lịch thu phải tạo **phiên bản mới** của hợp đồng, không ghi đè.
- **Liên kết chéo không phải là module riêng, mà là ba nguyên tắc thiết kế xương sống (M0):** (a) mọi module nối nhau qua **khóa chung** trong danh mục A1 — mã hợp đồng, số hóa đơn, mã đối tượng, mã dự án, mã tài sản, mã RQ; (b) **công nợ trước, tiền sau**: hóa đơn / nghiệm thu / hợp đồng tạo công nợ mở, tiền về/đi khớp vào công nợ mở (bậc 0); tiền đến trước thì treo và **khớp ngược** khi chứng từ công nợ đến; (c) **một chứng từ một đích**: hóa đơn mua phải được gán đích (chi phí / XDCB 241 / tài sản 211–153 / kho 152) trước khi sinh bút toán, đích quyết định module tiếp nhận tiếp theo.
- **Hệ quả về schema:** cần một **bảng liên kết chứng từ dùng chung** (`lien_ket_chung_tu`) trong kho tri thức mà mọi module đọc/ghi, thay vì mỗi module tự giữ liên kết riêng. Cơ chế bậc 0 (tài liệu 07) và `EntryDM` (tài liệu 08) đã là trường hợp riêng "tiền ↔ công nợ" của bảng này.

---

## 1. "CRM kế toán" cho M3 từ "#6 Trích tham số hợp đồng bằng AI local"

### 1.1 Cái gì đã có, cái gì phải thêm

| | #6 hiện có (theo danh mục) | Phải thêm cho M3 |
|---|---|---|
| Đầu vào | PDF hợp đồng xây dựng | PDF hợp đồng thuê đất / hạ tầng KCN; hợp đồng mua bán nhà ở; **phụ lục** (gia hạn, đổi lịch, chuyển nhượng); biên bản bàn giao |
| Bộ tham số | 36+ tham số xây dựng | Bộ tham số riêng cho từng loại (mục 1.2) |
| Chấm điểm | Đáp án mẫu hợp đồng xây dựng | Đáp án mẫu 10–20 hợp đồng mỗi loại (che tên khách) |
| Đầu ra | Excel có trích dẫn nguyên văn | Nạp vào **danh mục hợp đồng (A1)** + **lịch thu** + **khách hàng** (đối tượng Junsky) với trạng thái duyệt |
| Người duyệt | — | Kế toán công nợ duyệt tham số; phòng kinh doanh xác nhận lệch |
| OCR | Không | Hợp đồng ký tay scan → "#12 OCR module 2.1" trước (tầng thấp nhất, chỉ khi không có bản mềm) |

### 1.2 Bộ tham số cần trích (nháp — chốt sau khi xem 2–3 hợp đồng mẫu)

**Thuê đất / hạ tầng KCN** (đơn vị thí điểm PLHN): bên thuê (tên, MST, địa chỉ, người đại diện, STK), lô/vị trí, diện tích (m²), đơn giá thuê (USD hay VND, theo m²/năm hay trọn đời), **tiền thuê trả một lần hay hằng năm**, lịch thanh toán (đợt, % hoặc số tiền, hạn), **phí hạ tầng / quản lý / dịch vụ** (đơn giá, kỳ thu), ngày bàn giao đất, thời hạn thuê, điều khoản tỷ giá, phạt chậm trả, cọc.
**Mua bán nhà ở**: bên mua (tên, CCCD/MST, STK), mã căn/lô, dự án – giai đoạn, giá bán VND (gồm/không gồm VAT, phí bảo trì), lịch thanh toán theo tiến độ (đợt, %, mốc: ký/xây xong tầng n/bàn giao/sổ), ngày bàn giao dự kiến, phạt chậm trả, phí quản lý, cọc.
**Chung cho cả hai**: số hợp đồng, ngày ký, phụ lục số/ngày và điều khoản thay đổi, mã dự án Junsky (KCN-DVI0/1/2…), trạng thái.

### 1.3 Luồng
PDF hợp đồng/phụ lục (phòng kinh doanh nộp) → #6 trích tham số + trích dẫn → màn hình duyệt tham số (kế toán) → danh mục hợp đồng A1 (phiên bản n) + lịch thu sinh tự động → **M3** dùng lịch để đối chiếu hóa đơn bán ra và ghi nhận doanh thu; **M1** dùng lịch để khớp tiền về theo đợt (bậc 0); **M4 · Nghiệm thu & chi phí dự án** dùng mã dự án/căn để kết chuyển giá vốn khi bàn giao; **M10** dùng lịch phân bổ doanh thu KCN.

### 1.4 Rủi ro và cách chặn
- **Trích sai lịch thu → khớp tiền sai → bút toán sai hàng loạt.** Chặn: tham số lịch thu chỉ có hiệu lực sau khi kế toán duyệt; mỗi tham số kèm trích dẫn nguyên văn; không có trích dẫn → "Không quy định", không điền.
- **Phụ lục ghi đè**: lưu phiên bản; lịch thu của phiên bản cũ đã khớp tiền thì giữ nguyên liên kết.
- **Hai nguồn song song** (Excel phòng kinh doanh và hợp đồng trích): phải chốt nguồn chính (câu hỏi cuối tài liệu).
- **#6 chạy Ollama trên RunPod** (theo danh mục): hợp đồng khách hàng đi ra máy chủ thuê ngoài → phải qua "#13 Local Mask" hoặc chạy mô hình trên máy nội bộ; điểm này cần anh xác nhận trước khi dùng cho hợp đồng khách.

### 1.5 Con người làm gì
- Phòng kinh doanh: nộp PDF hợp đồng + phụ lục + biên bản bàn giao ngay khi ký; trả lời lệch qua agent Zalo.
- Kế toán công nợ: duyệt tham số trích (nhìn trích dẫn), không nhập lại tay.
- CFO: chốt bộ tham số, chốt nguồn chính, chốt chính sách ghi nhận doanh thu (bàn giao) và phân bổ KCN.

---

## 2. Bản đồ liên kết chéo giữa các chu trình

### 2.1 Khóa chung (nằm trong danh mục A1, mọi module dùng chung)

| Khóa | Ai tạo | Ai dùng | Ghi chú |
|---|---|---|---|
| Mã đối tượng (Junsky `ObjectID`) + MST/CCCD + STK | Danh bạ đối tác (A1) | Tất cả | Ba quy tắc STK đã chốt 25/09 |
| Số hóa đơn (ký hiệu + số + MST người bán) | M2 · Hóa đơn mua vào, M3 · Hóa đơn bán ra | M1, M4, M6, M8 | Khóa hóa đơn thống nhất đã dùng trong kho (bảng kê ↔ XML) |
| Mã hợp đồng (thầu / mua bán / thuê / vay) | Danh mục hợp đồng (A1), nạp từ #6, #5, #9 | M1, M3, M4, M9, M10 | Phải là **một mã** dùng chung với #5 Review xây dựng và #9 Sheet khoản vay |
| Mã dự án · giai đoạn · hạng mục (`ProjectID`) | A1 (từ Junsky) | M2, M3, M4, M6, M9 | Bắt buộc với mọi bút toán BĐS |
| Mã tài sản | M6 · TSCĐ & CCDC | M2, M4, M10 | Sinh khi ghi tăng |
| Mã RQ (Base) | #8 Backup Base | M1, M2 | Nối lệnh chi với đề nghị và hóa đơn |
| Mã chứng từ công nợ (`EntryDM`) | M2, M3 (hóa đơn), M4 (nghiệm thu), M3 (đợt hợp đồng) | M1 | Trường L sheet `CB_tmpEntry2` (tài liệu 08) |
| Mã lô đẩy, mã bút toán nguồn | M0 bước 7 | M10 bước 8 | Đối chiếu ngược |

### 2.2 Các cặp liên kết (ai cung cấp → ai nhận; chuyện gì xảy ra khi đến trước/sau)

| # | Liên kết | Chiều thuận (công nợ trước) | Chiều ngược (tiền/chứng từ đến trước) | Khóa |
|---|---|---|---|---|
| L1 | **M3 · Hóa đơn bán ra & doanh thu ↔ M1 · Tiền về** (Phải thu ↔ Thu tiền) | Hóa đơn bán / đợt theo lịch hợp đồng tạo 131 mở → tiền về khớp đợt/hóa đơn (bậc 0) → Xanh | Tiền về trước hóa đơn (cọc, trả trước) → 131 dư Có hoặc 344 (cọc đầu) → treo trong `lien_ket_chung_tu` → khi hóa đơn/đợt đến, khớp ngược, không sinh bút toán mới | Mã hợp đồng + đợt, số hóa đơn, mã KH |
| L2 | **M2 · Hóa đơn mua vào ↔ M1 · Tiền đi** (Phải trả ↔ Chi tiền) | Hóa đơn tạo 331 mở → lệnh chi (có RQ/số hóa đơn trong nội dung) khớp → Xanh; đồng thời đánh dấu "đã thanh toán không tiền mặt" cho M8 | Chi trước hóa đơn (tạm ứng NCC) → 331 dư Nợ / 141 → khớp ngược khi hóa đơn về | Số hóa đơn, mã RQ, mã NCC |
| L3 | **M2 · Hóa đơn mua vào → M4 · Nghiệm thu & chi phí dự án** (Phải trả ↔ XDCB) | Nghiệm thu (từ #5) tạo quyền ghi 241 theo đợt → hóa đơn nhà thầu khớp nghiệm thu → Xanh; tạm ứng nhà thầu thu hồi, bảo hành giữ lại theo tỷ lệ hợp đồng | Hóa đơn nhà thầu về trước nghiệm thu → Vàng, treo chờ; nghiệm thu không có hóa đơn → nhắc Ban QLDA/NCC | Mã hợp đồng thầu + đợt, số hóa đơn, mã dự án |
| L4 | **M2 · Hóa đơn mua vào → M6 · TSCĐ & CCDC** (Phải trả ↔ TSCĐ) | Hóa đơn gán đích "tài sản" (ngưỡng giá trị + nhóm G) → ghi tăng 211/153 từ hóa đơn + biên bản bàn giao → mã tài sản → khấu hao (M10) | Biên bản bàn giao có trước hóa đơn → tạm ghi tăng theo giá dự kiến, Vàng, sửa khi hóa đơn về | Số hóa đơn, mã tài sản |
| L5 | **M4 · Nghiệm thu & chi phí dự án → M6 · TSCĐ** (XDCB ↔ TSCĐ) | Công trình hoàn thành → kết chuyển 241 → 211 (hạ tầng KCN) theo quyết toán → mã tài sản | — | Mã dự án/hạng mục, mã tài sản |
| L6 | **M4 → M3** (XDCB ↔ Doanh thu) | Bàn giao căn/lô (từ CRM kế toán) → kết chuyển giá vốn dự án tương ứng (mức dự án, không tính từng căn) | — | Mã dự án, mã hợp đồng bán |
| L7 | **M9 · Vốn vay → M4 / M10** | Lãi vay theo hợp đồng vay gắn dự án → vốn hóa 241 (M4) hoặc chi phí 635; lãi dự trả cuối kỳ (M10) | — | Mã hợp đồng vay, mã dự án |
| L8 | **M9 ↔ M1** | Lịch trả nợ từ #9 Sheet khoản vay → giải ngân/trả gốc/lãi trên sao kê khớp → Xanh | Ngân hàng trích lệch lịch → Vàng, hỏi tài chính | Mã hợp đồng vay |
| L9 | **M2 + M1 → M8 · Bảng kê thuế** | Hóa đơn có chứng từ thanh toán không tiền mặt (L2) → đủ điều kiện khấu trừ; M3 → thuế đầu ra | Hóa đơn chưa có thanh toán → cờ "chờ chứng từ thanh toán" trên bảng kê | Số hóa đơn |
| L10 | **M7 · Lương ↔ M1, M2, M4** | Bảng lương → bút toán lương; lệnh chi lương khớp tổng (M1); lương Ban QLDA phân bổ vào 241 (M4); tạm ứng NV (141) ↔ hoàn ứng qua RQ (M2) | — | Mã NV, mã bộ phận/dự án |
| L11 | **M5 · Kho vận hành KCN ↔ M2, M6** | Hóa đơn mua vật tư → phiếu nhập kho (M5); CCDC xuất dùng → 242 (M6/M10) | Phiếu nhập trước hóa đơn → Vàng | Số hóa đơn, mã vật tư |
| L12 | **Mọi module → M10 · Đóng sổ & đối chiếu ngược** | Lô đã đẩy ↔ sổ Junsky; bút toán định kỳ lấy từ M6, M9, M3 (KCN), M4 (trích trước) | — | Mã lô, `EntryID` |

### 2.3 Ba nguyên tắc rút ra cho xương sống (đưa vào bộ quy tắc A2 và schema)
1. **Công nợ trước, tiền sau.** Thứ tự chạy trong kỳ: hợp đồng/nghiệm thu/hóa đơn (tạo công nợ mở) → tiền (khớp công nợ mở). Tiền đến trước thì **treo có liên kết chờ**, không đoán; khi chứng từ công nợ đến, hệ thống khớp ngược và nâng mức tin cậy, không tạo bút toán trùng.
2. **Một chứng từ một đích.** Hóa đơn mua được gán đích (chi phí / 241 / 211–153 / 152) ở bước 3 (nhóm G × Dự án/Vận hành); đích đổi thì bút toán cũ phải hoàn tác có nhật ký. Cùng một hóa đơn không được vào hai module.
3. **Liên kết là dữ liệu, không phải suy luận lặp lại.** Mọi liên kết (hóa đơn ↔ tiền, hóa đơn ↔ nghiệm thu, hợp đồng ↔ đợt ↔ tiền, 241 ↔ tài sản) ghi vào một bảng `lien_ket_chung_tu` (chứng từ A, chứng từ B, loại liên kết, số tiền VND đã khớp, trạng thái, nguồn suy luận, người duyệt). Màn hình duyệt hiện "chuỗi chứng từ" của dòng đang xem; bước 8 đối chiếu ngược và M8 bảng kê thuế đọc từ bảng này.

### 2.4 Hệ quả cho thứ tự triển khai
- L1 và L2 đã có nền (bậc 0, `EntryDM`) → chuẩn hóa thành `lien_ket_chung_tu` ngay trong V kế tiếp của xương sống, trước khi làm M4 · Nghiệm thu & chi phí dự án.
- M4 · Nghiệm thu & chi phí dự án và M6 · TSCĐ & CCDC phải **thiết kế schema cùng lúc** (L3, L4, L5 dùng chung mã tài sản, mã hợp đồng thầu, đích hóa đơn), dù code M6 sau.
- "CRM kế toán" (mục 1) là tiền đề của L1 và L6 → nên đưa vào ngay sau M4, cùng đợt với M9 · Vốn vay (cả hai đều là "nạp danh mục hợp đồng từ nguồn có sẵn").

---

## 3. Quyết định anh Dũng chốt 16/10/2026
1. **Dùng #6 + danh mục hợp đồng làm "CRM kế toán"** cho M3 · Hóa đơn bán ra & doanh thu BĐS: hợp đồng + lịch thu + trạng thái; không pipeline bán hàng.
2. **Làm cả hai loại hợp đồng (thuê đất KCN, mua bán nhà ở), nhưng thiết kế "loại hình doanh thu" để mở:** mỗi loại hình doanh thu có **một bộ tham số riêng dưới dạng cấu hình** (file YAML/JSON như hồ sơ loại chi phí của #1), kèm đáp án mẫu riêng; thêm loại hình doanh thu mới (ví dụ cho thuê nhà xưởng, dịch vụ tiện ích) = thêm một file cấu hình tham số + mẫu bút toán, **không sửa mã**. Cấu trúc chung mọi loại: khách hàng, mã hợp đồng, dự án, giá trị, đồng tiền, lịch thu (đợt – mốc – số tiền/% – hạn), sự kiện ghi nhận doanh thu (bàn giao / theo kỳ), phụ lục.
3. **Một nguồn duy nhất: hợp đồng ký → danh mục hợp đồng của hệ thống; bỏ Excel lịch thu của phòng kinh doanh.** Phòng kinh doanh xem và xác nhận trên danh mục hợp đồng; muốn đổi lịch phải có phụ lục ký (tạo phiên bản mới).
4. **Ba nguyên tắc liên kết chéo — chốt sau khi bàn thêm (16/10, cùng ngày):**
   - **Nguyên tắc 1:** chiều chi (phải trả) không có bài toán "tiền đến trước mà không rõ khoản" — tạm ứng theo RQ hạch toán ngay 331 dư Nợ / 141, liên kết chờ hóa đơn. Chiều thu (phải thu): tiền về chưa xếp được vào cọc hay đợt → **đề xuất Vàng ngay theo quy tắc CFO** (khách chưa có hợp đồng → 344; có hợp đồng → 131 đợt gần nhất; lệch số tiền → agent Zalo hỏi), **không treo**; hợp đồng/đợt nạp sau chỉ nối liên kết. Quyết định này trả lời luôn câu hỏi 2 còn mở ở tài liệu 23 (bước 2 phễu).
   - **Nguyên tắc 2:** máy đề xuất đích **theo tri thức học từ sổ quá khứ** (cùng đối tác + tên hàng → TK → đích, như V12); quy tắc nhóm G × Dự án/Vận hành × ngưỡng TSCĐ là tầng kiểm tra/dự phòng; người duyệt.
   - **Nguyên tắc 3:** bảng `lien_ket_chung_tu` **làm ngay trong V kế tiếp của xương sống, trước M4 · Nghiệm thu & chi phí dự án**.
   - Sơ đồ cây toàn bộ nghiệp vụ thể hiện các liên kết này: tài liệu 33.

### 2.5 Giải thích thêm ba nguyên tắc liên kết chéo (theo yêu cầu anh 16/10)

**Nguyên tắc 1 — Công nợ trước, tiền sau; tiền đến trước thì xử lý theo "biết gì"**
- *Nghĩa là gì:* trong một đợt xử lý, máy nạp hợp đồng/nghiệm thu/hóa đơn (tạo công nợ mở) **trước**, rồi mới khớp sao kê vào công nợ mở (bậc 0 đã có). Chỉ là thứ tự chạy, không thay đổi cách định khoản.
- *Khi tiền đến trước chứng từ công nợ, có ba mức "biết":*
  - **Biết đối tượng và bản chất** (cọc theo thỏa thuận, tạm ứng nhà thầu 30 % theo hợp đồng thầu đã có trong danh mục): **hạch toán ngay** vào TK ứng trước (344 cọc đầu / 131 dư Có / 331 dư Nợ), kèm **liên kết chờ** tới hợp đồng; khi hóa đơn/đợt đến, máy chỉ nối liên kết, không sinh bút toán mới. Đây là đa số trường hợp và không bị treo.
  - **Biết đối tượng, chưa rõ khoản** (khách chuyển tiền, không nói cọc hay đợt — đúng câu hỏi còn mở ở tài liệu 23): hai cách — (a) **treo có hạn** N ngày làm việc chờ phòng kinh doanh/agent Zalo trả lời, quá hạn thì đề xuất Vàng với TK mặc định theo vai trò (131 khách hàng / 331 NCC); (b) **đề xuất Vàng ngay**, kế toán duyệt, nối liên kết sau. Khác nhau ở chỗ: (a) giữ sổ sạch, nhưng số dư 112 trên sổ lệch sao kê cho đến khi khớp — rủi ro khi đóng sổ cuối tháng nếu phòng kinh doanh chậm; (b) định khoản sớm, nhưng nếu duyệt sai TK (344 thay vì 131) phải sửa trong Junsky.
  - **Không biết đối tượng**: Đỏ như hiện nay, agent Zalo hỏi.
- *Khuyến nghị:* mức 1 hạch toán ngay; mức 2 treo có hạn **5 ngày làm việc** rồi Vàng theo vai trò; mức 3 Đỏ. Cuối tháng, mọi dòng treo chuyển Vàng để đóng sổ.

**Nguyên tắc 2 — Một chứng từ (dòng hóa đơn) một đích**
- *Nghĩa là gì:* trước khi sinh bút toán, mỗi **dòng** hóa đơn mua được gán một "đích": chi phí (6xx) · XDCB (241) · tài sản (211/213/153) · kho (152). Đích = f(nhóm G, Dự án/Vận hành, ngưỡng TSCĐ). Đích quyết định dòng đó đi tiếp sang M4 · Nghiệm thu & chi phí dự án hay M6 · TSCĐ & CCDC hay M5 · Kho.
- *Ví dụ:* hóa đơn mua máy phát điện cho KCN: nếu "Dự án" → 241 (M4); nếu "Vận hành" và ≥ ngưỡng TSCĐ → 211 (M6); nếu dưới ngưỡng → 153/242. Cùng một hóa đơn không được vừa vào 241 vừa vào 211. Hóa đơn có hai dòng (vật tư + dịch vụ lắp đặt) thì mỗi dòng một đích riêng.
- *Ngưỡng TSCĐ:* theo Thông tư 45/2013/TT-BTC, nguyên giá từ 30.000.000 VND và thời gian sử dụng trên 1 năm — **kiểm tra lại văn bản hiện hành khi lập quy tắc**.
- *Lựa chọn:* (a) máy đề xuất đích, người duyệt (như mọi đề xuất khác) — khuyến nghị; (b) người gán đích tay toàn bộ — an toàn nhưng chậm; (c) không gán đích, để từng module tự nhận — rủi ro hóa đơn vào hai nơi hoặc không nơi nào nhận.
- *Đổi đích sau khi đã duyệt:* hoàn tác bút toán cũ có nhật ký, sinh bút toán mới; nếu đã nạp Junsky thì tạo bút toán điều chỉnh, không sửa file cũ.

**Nguyên tắc 3 — Liên kết là dữ liệu trong một bảng dùng chung**
- *Hiện nay:* liên kết tiền ↔ công nợ nằm trong kết quả đề xuất của từng dòng (bậc 0) và được đẩy sang Junsky qua `EntryDM`. Không có chỗ ghi liên kết nghiệm thu ↔ hóa đơn, hóa đơn ↔ tài sản, 241 ↔ tài sản, hợp đồng ↔ đợt ↔ tiền, hay thanh toán một phần cho nhiều hóa đơn.
- *Đề xuất:* một bảng `lien_ket_chung_tu` (chứng từ A, chứng từ B, loại liên kết, số tiền VND đã khớp, trạng thái chờ/đã khớp/hủy, nguồn suy luận, người duyệt, thời điểm). Mọi module ghi vào đây; màn hình duyệt hiện "chuỗi chứng từ" (hợp đồng → nghiệm thu → hóa đơn → thanh toán → tài sản); bước 8 đối chiếu ngược và M8 · Bảng kê thuế (điều kiện khấu trừ) đọc từ đây.
- *Chi phí:* một migration schema + sửa bậc 0 để ghi vào bảng (thay vì chỉ ghi trong đề xuất) + một màn hình chuỗi chứng từ. *Lợi:* L1–L12 dùng chung một cơ chế, có vết kiểm toán, thanh toán một phần/nhiều hóa đơn xử lý được.
- *Lựa chọn:* (a) làm ngay trong V kế tiếp của xương sống, trước M4; (b) để đến khi bắt đầu M4 (lúc đó buộc phải có vì nghiệm thu ↔ hóa đơn); (c) không làm bảng riêng, chỉ dựa vào `EntryDM` của Junsky — không đủ vì Junsky không biết nghiệm thu, tài sản, hợp đồng.

## 4. Việc tiếp theo
- Ghi hàng đợi: bộ tham số theo loại hình doanh thu (cấu hình) + đáp án mẫu cho #6; màn hình duyệt tham số hợp đồng; `lien_ket_chung_tu` (chờ anh chốt nguyên tắc 3).
- Cập nhật tài liệu 29 (M3 đầu vào = danh mục hợp đồng từ #6, bỏ CRM/Excel kinh doanh), 31 (#6 lên mức A cho M3), khảo sát 30 (phần C: xin 2–3 hợp đồng mẫu + phụ lục mỗi loại hình, bỏ câu C1 về CRM/Excel).
- Vẽ sơ đồ cây toàn bộ nghiệp vụ (đầu vào → chứng từ → bộ tiếp nhận → chu trình → bút toán → Junsky, kèm L1–L12) — anh yêu cầu 16/10.
