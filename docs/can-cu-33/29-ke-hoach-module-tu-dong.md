# 29 · Kế hoạch các module dự kiến tự động — đầu vào · cách xử lý · việc của con người

**Ngày lập:** 15/10/2026 · **Phạm vi:** bỏ giá thành sản xuất, kho sản xuất và hợp nhất theo yêu cầu anh Dũng 15/10. Còn 10 module tự động + 1 xương sống dùng chung.
**Mục đích:** trả lời cho từng module ba câu: (1) đầu vào là gì, chạy qua những bước nào, đầu ra là gì; (2) máy dự kiến xử lý ra sao; (3) với đầu vào/đầu ra như vậy, con người còn phải làm gì. Tài liệu này là bước **trước** khi chia giai đoạn lập trình.
**Căn cứ:** tài liệu 01 (bản đồ module), 08 (file nhập Junsky), 23 (phễu 6 bước), 24 (go-live), 27 (V12 hóa đơn), 28 (sơ đồ phần hành). Nơi nào chưa có tài liệu, ghi rõ **[giả định — cần anh xác nhận]**.

---

## 0. Kết luận trước

- **Mọi module đều chạy chung một đường ống 8 bước** (tài liệu 01). Chỉ bước 1–2 (tiếp nhận, bóc tách) khác nhau theo loại chứng từ; từ bước 3 (khớp) đến bước 8 (đối chiếu ngược) dùng chung xương sống. Vì vậy kế hoạch dưới đây mô tả xương sống **một lần** (mục 1), rồi mỗi module chỉ nêu phần riêng.
- **Đầu ra cuối cùng của mọi module là một dòng trong file Excel nhập Junsky** (2 sheet `CB_tmpEntry1/2`, tài liệu 08), kèm lý do đề xuất để người duyệt soát. Module nào không kết thúc bằng dòng Excel thì chỉ ra **bảng kê / danh sách việc** chứ không ra bút toán.
- **Máy chỉ đề xuất, người duyệt** — cho đến khi có số đo thật trên ba tháng liên tiếp. Kết quả đề xuất chia 3 mức: **Xanh** (đủ điều kiện nhập, duyệt hàng loạt), **Vàng** (máy đề xuất, người xác nhận từng dòng), **Đỏ** (máy không đủ căn cứ, người chọn hoặc máy đi hỏi phòng ban).
- **Con người giữ 5 việc không giao máy:** (a) cung cấp chứng từ đúng định dạng tại nguồn; (b) duyệt Vàng, quyết Đỏ; (c) trả lời câu hỏi của máy; (d) quyết định chính sách và ngưỡng (CFO); (e) đối chiếu ngược sau khi nạp Junsky (bước 8). Mục tiêu của tự động hóa là **thu hẹp (b)** theo thời gian, không phải xóa (a), (d), (e).
- **Thứ tự triển khai đề xuất** (theo mức độ sẵn sàng của dữ liệu đầu vào): M1 sao kê (đang chạy) → M2 hóa đơn mua / M3 hóa đơn bán (V12 đã có) → M8 bảng kê thuế (chỉ là đầu ra của M2–M3) → M4 nghiệm thu dự án → M9 vay → M10 định kỳ & đóng sổ → M6 TSCĐ → M7 lương → M5 kho vận hành. Thứ tự này cần anh chốt (câu hỏi cuối tài liệu).

### Quyết định anh Dũng chốt 15/10/2026 (sau khi đọc bản này)
1. **Thứ tự triển khai sau M1–M3: chưa chọn — khảo sát đầu vào trước.** Bảng khảo sát ở tài liệu 30 (nháp, chờ anh duyệt rồi mới gửi phòng ban).
2. **Kênh hỏi phòng ban: Zalo, tạo một agent Zalo tự gửi câu hỏi, tự nhận trả lời và phân tích.** Thiết kế ở mục 1.4.
3. **Tự duyệt theo loại giao dịch:** phí ngân hàng, lãi tiền gửi, lương, bút toán định kỳ được đưa thẳng vào file nhập Junsky không cần bấm duyệt; các loại khác người duyệt. Điều kiện ở mục 1.5.
4. **Nguồn M4 đã xác nhận:** Ban QLDA có bảng Excel theo dõi + biên bản ký PDF → máy đọc Excel, PDF lưu làm chứng từ gốc; không cần OCR.

**Bổ sung sau tài liệu 31 (cùng ngày, 22:30):**
5. **M4 nhận kết quả từ dự án "Review hồ sơ thanh toán khối lượng xây dựng"** (đã có, Python + Local AI): phần mềm kế toán không tự khớp nghiệm thu ↔ hợp đồng/BOQ, chỉ đọc dòng kết quả review (mã hợp đồng, đợt, giá trị chấp nhận VND, tạm ứng, bảo hành, trạng thái) và sinh bút toán. Bảng Excel của Ban QLDA là nguồn của dự án review, không phải của M4.
6. **M9 đọc thẳng Google Sheets API** của "Phần mềm theo dõi khoản vay" (Sheet là nguồn duy nhất về hợp đồng vay, lịch trả nợ); xác thực bằng service account chỉ đọc đặt trong `.env`.
7. **Agent Zalo dùng lại lõi bot Telegram trợ lý** (nhận tin, nhắc hạn, nhật ký), thay lớp Telegram bằng Zalo Bot, bỏ gọi API AI ngoài.
8. **Thứ tự triển khai sau M1–M3: M4 → M9 → M8** (đầu vào đã có cấu trúc nhờ ba dự án sẵn có: review xây dựng, Sheet khoản vay, tải hóa đơn/bảng kê cổng thuế); M5, M7, M10 chờ khảo sát (tài liệu 30 đã rút gọn).
9. Đã tạo `CLAUDE.md`, `CHANGELOG.md`, `HANG-DOI-YEU-CAU.md` trong thư mục dự án (tài liệu 31 mục 3).

### Bảng tổng hợp

| # | Module | Đầu vào chính | Đầu ra chính | Mức sẵn sàng | Con người làm chủ yếu |
|---|---|---|---|---|---|
| M0 | Xương sống (A1–A6, V1–V3) | Danh mục Junsky, sổ NKC lịch sử, quy tắc | Màn hình duyệt, file Excel nhập Junsky, nhật ký | Đã có V10–V12, mức 2 còn khóa | Duyệt, chốt danh mục, trả lời 3 câu Junsky |
| M1 | Tiền về / tiền đi từ sao kê (N1) | Sao kê eFAST .xlsx, danh bạ đối tác, công nợ mở | Phiếu thu/chi NH đề xuất | **Đang chạy thật** (V10, TK 112111) | Duyệt Vàng/Đỏ, trả lời khoản thu chưa rõ |
| M2 | Hóa đơn mua vào (N2 + N3) | XML HĐĐT mua, đề nghị thanh toán Base, PO/nghiệm thu | Bút toán 331/1331 + nối chứng từ thanh toán | V12 có đề xuất, chưa khớp 3 chiều | Chọn TK chi phí cho mua lẻ, bổ sung chứng từ thiếu |
| M3 | Hóa đơn bán ra & doanh thu BĐS (N2 + N4/N5) | XML HĐĐT bán, hợp đồng + lịch thu, biên bản bàn giao | Bút toán 131/3331; bút toán doanh thu nhận trước / ghi nhận | V12 có đề xuất bán ra; lịch thu chưa nối | Cung cấp hợp đồng & lịch thu có cấu trúc, quyết thời điểm bàn giao |
| M4 | Nghiệm thu & chi phí dự án (N3 xây lắp, F) | Hồ sơ nghiệm thu khối lượng, hợp đồng thầu, hóa đơn nhà thầu | Bút toán 241/154 theo dự án, giữ lại bảo hành, thu hồi tạm ứng | Chưa bắt đầu | Ban QLDA nộp nghiệm thu bản mềm; kế toán duyệt lệch |
| M5 | Kho vận hành KCN (N6) | Phiếu nhập/xuất, yêu cầu cấp phát, hóa đơn mua | Bút toán nhập/xuất kho, CCDC cấp phát | Chưa bắt đầu; có thiết kế 9 sheet | Thủ kho ghi phiếu đúng mẫu, kiểm kê |
| M6 | TSCĐ & CCDC (N3 + N8) | Hóa đơn + biên bản bàn giao, bảng khấu hao, bảng phân bổ 242 | Ghi tăng, khấu hao, phân bổ định kỳ | Chưa bắt đầu | Quyết phân loại TS, thời gian khấu hao |
| M7 | Lương & bảo hiểm (N7) | Bảng lương Excel đã tính, bảng phân bổ bộ phận/dự án | Bút toán lương, BH, TNCN; khớp lệnh chi lương | Chưa bắt đầu | Nhân sự nộp bảng lương đúng mẫu; duyệt biến động |
| M8 | Bảng kê thuế & đối chiếu cổng thuế (N2) | XML HĐĐT, dữ liệu tra cứu cổng thuế, sổ đã nạp | Bảng kê GTGT hỗ trợ tờ khai, danh sách hóa đơn lệch | Có dữ liệu XML, chưa có bảng kê | Lập tờ khai trong Junsky, xử lý hóa đơn sai sót |
| M9 | Vốn vay (A1 + N1 + N8) | Hợp đồng vay, lịch trả nợ, sao kê | Khớp giải ngân/trả nợ, lãi dự trả, phân loại vốn hóa | Chưa bắt đầu | Pháp chế/tài chính nhập hợp đồng vay vào danh mục |
| M10 | Bút toán định kỳ & đóng sổ (N8 + V4 + A4) | Bảng phân bổ, lịch trích trước, checklist | Bút toán định kỳ, checklist đóng sổ, báo cáo đối chiếu ngược | Bước 8 chưa chạy (mức 2 khóa) | Người làm đối chiếu ngược, ký đóng sổ |

---

## 1. M0 · Xương sống dùng chung (A1–A6, V1–V3) — mô tả một lần

### 1.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý (bước 3–8 chung) | Đầu ra |
|---|---|---|
| 6 danh mục Junsky đã xuất: đối tượng, tài khoản, dự án (KCN-DVI0/1/2), 29 trung tâm chi phí, 52 khoản mục, đơn vị (`02`) | **Bước 3 – Khớp:** chứng từ ↔ danh mục, danh bạ đối tác (STK/MST), công nợ mở | Hàng chờ duyệt: mỗi dòng có bút toán đề xuất + cột **lý do** (nguồn suy luận TK, nguồn suy luận đối tượng, độ tin cậy) |
| Sổ NKC lịch sử (học đến 30/06/2026), dgbList 2024–2025 | **Bước 4 – Kiểm tra hợp lệ:** Nợ = Có, mã trong danh mục, TK công nợ có đối tượng, kỳ chưa khóa, chống trùng | Danh sách việc cần xử lý (V1): dòng vướng, lý do, người phụ trách, số ngày tồn |
| Danh bạ đối tác (STK, MST, vai trò) theo 3 quy tắc STK đã chốt 25/09 | **Bước 5 – Sinh bút toán:** bộ quy tắc định khoản + tri thức CFO (`TRI-THUC-CFO.json`) + tri thức học từ sổ | File soát Excel (mức 1) · File nhập Junsky 2 sheet, chỉ dòng Xanh đã duyệt (mức 2) |
| Bộ quy tắc: 432 từ khóa không dấu, 33 nhóm G, mẫu bút toán theo điều kiện | **Bước 6 – Duyệt:** màn hình Định khoản (Đồng ý / Sửa / Bỏ qua / hàng loạt Xanh) | Nhật ký: ai duyệt, sửa gì, khi nào; chứng từ gốc gắn bút toán (A6) |
| Lịch chạy (V3): tiếp nhận định kỳ, cảnh báo nguồn im lặng | **Bước 7 – Xuất Excel theo lô:** mã lô, mã bút toán nguồn, phiếu kiểm · **Bước 8 – Đối chiếu ngược:** đọc sổ Junsky sau nạp ↔ lô đã đẩy | Bảng tình trạng đường ống (V2) · Báo cáo đối chiếu ngược: dòng khớp / lệch / thiếu |

### 1.2 Dự kiến xử lý
- Khớp theo **thứ tự cứng → mềm**: mã (STK, MST, số hóa đơn, số RQ) → công nợ mở → từ khóa cụm dài → lịch sử đối tác → LLM cục bộ chọn 1 trong 2–5 phương án → người. Mỗi tầng ghi lại căn cứ vào cột lý do (phễu 6 bước, tài liệu 23).
- Mức Xanh chỉ khi **mọi trục đều có căn cứ chắc** (TK cấp chi tiết, đối tượng có mã Junsky, dự án/TTCP/khoản mục đủ) — "dựng được" chưa phải "nhập được" (tài liệu 08: T7 24 dòng dựng được, 17 nhập được).
- Mọi sửa chữa của người duyệt → **tri thức chờ duyệt** (tài liệu 09, 26) → lần sau khớp ở tầng cao hơn. Đây là cơ chế làm tỷ lệ Xanh tăng dần.
- Máy chủ chặn Đồng ý khi vi phạm bước 4 (đã có từ V10). Không có đường tắt nào bỏ qua kiểm tra này.
- Mức 2 (file nhập Junsky) chỉ mở sau khi **nhập thử 1 → 5 chứng từ** và chốt 3 câu với nhà cung cấp Junsky (tài liệu 08: Entry2 chứa cả vế tiền hay chỉ đối ứng; Junsky giữ `EntryID` hay tự đánh; `DebtID` bỏ trống?) cùng danh mục `BankID`.

### 1.3 Con người làm gì
- **Kế toán viên (người duyệt):** mỗi ngày mở màn hình Định khoản, duyệt hàng loạt Xanh, xác nhận từng dòng Vàng, quyết Đỏ hoặc chuyển câu hỏi; không sửa tay trong file Excel sau khi xuất.
- **CFO / kế toán trưởng:** duyệt tri thức chờ (`CFO_NTD`), chốt danh sách TK công nợ bắt buộc có đối tượng (đang dùng 131, 331, 141, 344, 1388, 3388), chốt ngưỡng tự duyệt khi có số đo, ký đóng sổ.
- **Người nhập Junsky:** nạp đúng file lô, không sửa file trước khi nạp, báo lại `ErrorText` nếu Junsky trả lỗi.
- **Nhà cung cấp Junsky:** trả lời 3 câu + cấp danh mục `BankID`, `CashflowID`.
- **Claude/Codex:** lập trình, chạy thử, chấm điểm trên tháng thật; anh không gõ lệnh.

### 1.4 Agent Zalo — hỏi phòng ban và nhận trả lời (anh chốt 15/10)
- **Nền tảng:** Zalo Bot (tạo bot tại `bot.zapps.me` bằng tài khoản Zalo, nhận Bot Token; nhận tin qua webhook có secret; gửi tin bằng API). Theo tài liệu của bộ chuyển đổi cộng đồng Chat SDK: chỉ văn bản thuần, tối đa 2.000 ký tự/tin, không sửa/xóa tin, không lấy lịch sử tin nhắn, nhóm chat chưa hỗ trợ ([chat-sdk.dev/adapters/zalo](https://chat-sdk.dev/adapters/zalo)). **Chưa kiểm chứng trên tài liệu gốc của Zalo** hai điểm quan trọng: bot có được nhắn trước cho người chưa mở chat không, và giới hạn tần suất — phải thử thật trước khi lập trình.
- **Không dùng** Zalo cá nhân tự động hóa (rủi ro khóa tài khoản) và **không dùng** Zalo OA cho việc này: OA đòi xác thực doanh nghiệp, người nhận phải quan tâm OA hoặc có giao dịch, tin theo mẫu duyệt và có hạn mức ([helpcenter.esms.vn](https://helpcenter.esms.vn/cau-hoi-thuong-gap/zalo-oa), [pos.manual.nhanh.vn](https://pos.manual.nhanh.vn/pos/cai-dat/gui-zalo-zns/cac-loai-tin-cua-oa)) — phù hợp nhắn khách hàng, không phù hợp hỏi nội bộ.
- **Luồng:** dòng Đỏ/Vàng cần hỏi → máy xác định người phụ trách (danh bạ nội bộ: sales theo khách, kế toán công nợ theo công ty thành viên, Ban QLDA theo dự án) → soạn tin ngắn: ngày, số tiền VND, nội dung chuyển khoản rút gọn, **các phương án đánh số** → gửi → người trả lời bằng số hoặc câu ngắn → máy phân tích (số → chọn phương án; câu tự do → LLM cục bộ xếp vào phương án hoặc đánh dấu "cần kế toán đọc") → ghi vào hồ sơ giao dịch và tri thức chờ duyệt → nhắc sau 24 giờ nếu chưa trả lời, chuyển kế toán sau 48 giờ.
- **Bảo mật:** tin gửi đi không ghi tên tài khoản ngân hàng, không ghi số dư; mỗi nhân viên mở chat với bot một lần và được kế toán gán vào danh bạ nội bộ; nhật ký đầy đủ mọi tin gửi/nhận.
- **Giai đoạn đầu:** bot tự gửi nhưng kế toán xem được hàng đợi tin đã gửi và câu trả lời; câu trả lời chỉ **đề xuất** bút toán, vẫn qua bước 6.

### 1.5 Tự duyệt theo loại giao dịch (anh chốt 15/10)
- Danh sách loại được tự duyệt lần đầu: **phí ngân hàng** (người bán là ngân hàng, khớp dòng phí sổ phụ), **lãi tiền gửi** (515), **lương** (lô từ bảng lương đã kiểm tổng), **bút toán định kỳ** (khấu hao, phân bổ 242, trích trước, phân bổ doanh thu KCN theo bảng đã duyệt).
- Điều kiện để một dòng được tự duyệt: đúng loại trong danh sách **và** qua đủ kiểm tra bước 4 **và** đối tượng/TK/dự án lấy từ bảng người đã duyệt hoặc từ khớp cứng (không từ LLM, không từ từ khóa đơn). Lệch mẫu (số tiền bất thường so với kỳ trước, đối tượng mới) → rơi về Vàng.
- Dòng tự duyệt vẫn ghi nhật ký "tự duyệt theo loại", vẫn vào file lô và vẫn qua đối chiếu ngược; CFO ký danh sách loại và xem lại mỗi quý. Chỉ có hiệu lực khi mức 2 (file nhập Junsky) đã mở.

---

## 2. M1 · Tiền về / tiền đi từ sao kê ngân hàng (N1) — đang chạy thật

### 2.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý riêng (bước 1–2) | Đầu ra |
|---|---|---|
| Sao kê eFAST VietinBank `.xlsx` theo tháng, mỗi file một tài khoản (go-live TK 112111; ánh xạ STK •••• 0496 → 112111 trong `source-settings.json`) | Đọc từng dòng: ngày, số tiền, STK/tên đối tác, nội dung (không dấu), mã GD ngân hàng; đánh số chứng từ dạng `02BR/02BP{YYMM}-{nnnn}` | Phiếu thu NH (Nợ 112 / Có đối ứng) · Phiếu chi NH (Nợ đối ứng / Có 112), có đối tượng, dự án, TTCP, khoản mục |
| Danh bạ đối tác PLHN (STK ↔ mã đối tượng, vai trò KH/NCC/NH/NV) | Nhận diện đối tượng theo 3 quy tắc STK; vai trò → tập TK ứng viên (thu KH: 131/344/138; thu NH: 515; chi NH: 133/642/241/341; chi NCC: 331/338) | Dòng Đỏ kèm **câu hỏi soạn sẵn** cho sales / kế toán công nợ (M0-Agent, mở rộng V1) |
| Công nợ mở từ sổ Junsky (131/331/141/344 theo đối tượng) + mã RQ/hóa đơn trong nội dung chuyển khoản (khi có app lệnh thanh toán) | Khớp bậc 0 (tài liệu 07): đúng 1 chứng từ · tổng nhiều chứng từ · một phần · lệch phí NH; có mã RQ/hóa đơn → chốt luôn | Báo cáo chấm điểm theo tháng (so với Sổ NKC): Xanh/Vàng/Đỏ, TK đúng, đối tượng đúng |

### 2.2 Dự kiến xử lý
- Thứ tự phễu: loại chứng từ (vế 112 cố định) → đối tượng + vai trò → loại giao dịch (từ khóa cụm dài, lịch sử, LLM chọn trong ứng viên) → mẫu bút toán (tách thuế, điều kiện giai đoạn/khu) → dự án/khoản mục/TTCP → kiểm tra.
- Trường hợp đã chốt: phí ngân hàng có hóa đơn của chính ngân hàng → một bút toán trên sổ phụ (Nợ 6427 + 1331 / Có 112), không qua 331; rút tiền mặt nhập quỹ (CFO-01) → Nợ 1111 / Có 112111; 344 chỉ cho lần đặt cọc đầu, các lần sau 131.
- Chưa quyết (tài liệu 23, điểm dừng): đối tác hai vai trò KH+NCC xử lý ra sao; tiền khách về không khớp công nợ, không nói rõ cọc/thanh toán → Đỏ chờ hay Vàng 131.
- **Cải thiện đầu vào tại nguồn** (ý tưởng app lệnh thanh toán, tài liệu 23): chi trả đối tác chiếm 34% phiếu và là nhóm máy sai nhiều nhất → người lập lệnh chọn nhóm G từ đề nghị Base, nội dung chuyển khoản mang số RQ/hóa đơn + mã nhóm ngắn → máy khớp ở tầng mã, không phải đoán từ nội dung.
- Số đo hiện có (T8/2026, học đến 30/06, tài liệu 24): 105 dòng → Xanh 27 (TK đúng 19/20 dòng ghép được), Vàng 44 (TK đúng 22/33), Đỏ 34. Nút thắt là thiếu mẫu và thiếu đối tượng, không phải thuật toán.

### 2.3 Con người làm gì
- **Trước:** kế toán thả file sao kê `.xlsx` vào thư mục quy ước mỗi ngày/tuần (eFAST không có API trong phạm vi hiện tại); mỗi file một tài khoản.
- **Trong:** duyệt Xanh hàng loạt (riêng phí NH, lãi tiền gửi: tự duyệt theo mục 1.5); với Vàng xác nhận TK/đối tượng; với Đỏ chọn phương án hoặc để agent Zalo (mục 1.4) tự hỏi sales/kế toán công nợ, theo dõi trả lời, nhắc hạn; người trả lời chỉ cần **chọn số** trong các phương án máy đưa.
- **Người lập lệnh thanh toán:** (khi có app) xác nhận nhóm G máy đề xuất và dùng nội dung chuyển khoản chuẩn; không tự phân loại.
- **CFO:** trả lời 2 câu chưa quyết ở trên; sau 3 tháng có số đo, quyết ngưỡng tự duyệt Xanh (ví dụ dưới một mức tiền VND và đối tượng đã gặp ≥ n lần).
- **Sau:** người nhập Junsky nạp file lô; kế toán chạy đối chiếu ngược (M10) và xử lý dòng lệch.

---

## 3. M2 · Hóa đơn mua vào → công nợ phải trả (N2 + N3)

### 3.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý riêng | Đầu ra |
|---|---|---|
| XML HĐĐT mua vào theo tháng từ thư mục công cụ tải hóa đơn (`paths.invoice`, có 01/2024 → 09/2026) | Đọc XML: người bán (MST, tên), số/ký hiệu/ngày, từng dòng hàng, tiền chưa thuế, thuế suất, tiền thuế; kiểm tra hợp lệ: MST có trong danh mục, trạng thái hóa đơn (gốc/thay thế/điều chỉnh/hủy), trùng số | Bút toán mua: Nợ TK chi phí/tài sản/241 + Nợ 1331 / Có 331 (đối tượng NCC), đủ dự án/TTCP/khoản mục; điền nhóm cột hóa đơn (`InvNo, InvDate, VatID, BaseBefVat, BaseAmtVat`…) |
| Đề nghị thanh toán Base (RQ): Dự án, Chi phí (Dự án/Vận hành), nội dung, STK thụ hưởng, người đề nghị **[Base xuất được file hay phải đọc API — cần anh xác nhận]** | Khớp hóa đơn ↔ RQ theo MST + số tiền + thời gian; RQ cho biết dự án/vận hành và nhân viên mua hộ | Dòng hóa đơn đã nối RQ (biết nhân viên, mục đích chi) |
| PO / hợp đồng mua, phiếu nhập kho (M5), hồ sơ nghiệm thu (M4) **[giả định nguồn: Excel/PDF của phòng mua hàng & Ban QLDA — cần xác nhận]** | Khớp 3 chiều hóa đơn ↔ PO/hợp đồng ↔ nghiệm thu/nhập kho: đúng, lệch số lượng/đơn giá, thiếu chứng từ | Danh sách vướng (V1): hóa đơn thiếu nghiệm thu/PO, lệch giá, NCC lạ |
| Sao kê (M1) | Nối hóa đơn ↔ chứng từ thanh toán: điều kiện khấu trừ GTGT (mua từ 5.000.000 VND trở lên phải thanh toán không dùng tiền mặt — NĐ 181/2025, kiểm tra lại khi triển khai) | Cờ "đủ điều kiện khấu trừ" / "chưa có chứng từ thanh toán" |

### 3.2 Dự kiến xử lý
- Đã có từ V12: học 12 tháng hóa đơn ghép chứng từ Junsky theo tiền chưa thuế + thuế (−20/+75 ngày); TK theo cùng đối tác + tên hàng tương tự → tên hàng tương tự đối tác khác → toàn bộ hóa đơn của đối tác; Xanh khi 100% và ≥ 3 lần.
- Số đo T8/2026 mua vào (75 HĐ): Xanh 0, Vàng 22 (ghép 14, TK đúng 13/14, đối tượng đúng 5/14), Đỏ 17. Nguyên nhân chính: mua lẻ do nhân viên mua hộ (TK chi phí theo mục đích 6427/6423/6428/1547 không có trên hóa đơn; đối tượng Junsky ghi NV.x) và 11/17 Đỏ chưa thấy chứng từ Junsky.
- Hướng xử lý tiếp: nối Base RQ để biết nhân viên và mục đích → nhóm G → TK = f(nhóm G, Dự án/Vận hành), TTCP = f(dự án, nhóm) — hai bảng ánh xạ anh duyệt một lần.
- Hóa đơn phí ngân hàng: không qua 331, hạch toán trên sổ phụ (đã chốt).
- Xây lắp/thầu phụ: hóa đơn nhà thầu **chỉ Xanh khi khớp nghiệm thu** (M4); không có nghiệm thu → Vàng tối đa, treo chờ.
- Thứ tự ưu tiên nguồn: XML (đã có) → Excel/API Base → PDF có cấu trúc → OCR sau cùng. Không làm OCR trong đợt này.

### 3.3 Con người làm gì
- **Phòng mua hàng / người đề nghị:** lập RQ trên Base đủ 3 ô Dự án, Chi phí, nội dung; đính hóa đơn hoặc số hóa đơn vào RQ; yêu cầu NCC gửi XML (quy định nội bộ).
- **Kế toán:** với hóa đơn mua lẻ, chọn nhân viên và TK chi phí trong danh sách máy gợi ý (Vàng); với hóa đơn thiếu RQ/nghiệm thu, bấm "yêu cầu bổ sung" → máy gửi cho phòng mua hàng/Ban QLDA và đếm ngày tồn.
- **CFO:** duyệt hai bảng ánh xạ nhóm G × (Dự án/Vận hành) → TK, khoản mục, TTCP; quyết mua lẻ không có RQ xử lý thế nào (đang tạm giữ Vàng + ghi chú).
- **Người nhập Junsky:** như M1. Lưu ý V12 hiện **không tạo file nhập Junsky cho hóa đơn** — mở sau khi mức 2 của M1 chạy ổn.

---

## 4. M3 · Hóa đơn bán ra & doanh thu BĐS (N2 + N4 nhà ở + N5 KCN)

### 4.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý riêng | Đầu ra |
|---|---|---|
| XML HĐĐT bán ra theo tháng (cùng thư mục với mua vào, nhãn Bán ra) | Đọc XML: người mua (MST/CCCD), hàng hóa/dịch vụ (căn/lô/đợt, phí hạ tầng, dịch vụ), tiền, thuế | Bút toán bán: Nợ 131 (đối tượng KH) / Có 511x hoặc Có 3387 + Có 3331, dự án, TTCP |
| Hợp đồng mua bán nhà ở / hợp đồng thuê đất KCN + **lịch thanh toán theo đợt** (cọc, đợt 1..n, phí quản lý) **[giả định nguồn: CRM/Excel phòng kinh doanh — cần anh xác nhận có xuất được dạng bảng không]** | Nối hóa đơn ↔ hợp đồng ↔ đợt; so tiền về (M1) với đợt đến hạn; phạt chậm trả theo điều khoản | Bảng theo dõi hợp đồng: đợt đã thu / chưa thu / quá hạn; dòng Xanh ở M1 khi tiền về khớp đợt |
| Biên bản bàn giao (nhà ở) / ngày bắt đầu thuê (KCN) **[giả định: Excel hoặc PDF ký — cần xác nhận]** | Nhà ở: tiền thu trước → 131 dư Có hoặc 3387 theo chính sách; khi bàn giao → ghi nhận 511 và kết chuyển giá vốn (M4). KCN: doanh thu nhận trước → lịch phân bổ hằng kỳ → bút toán định kỳ (M10) | Bút toán ghi nhận doanh thu khi bàn giao; lịch phân bổ KCN; hợp đồng USD thu VND lưu hai đồng tiền + tỷ giá |

### 4.2 Dự kiến xử lý
- Đã có từ V12 bán ra T8: Xanh 11 (TK 11/11, dự án 10/11), Vàng 20 (TK 20/20, dự án 15/20), Đỏ 5 — bán ra ổn hơn mua vào vì ít biến thể TK. Bán ra không ghép chứng từ thu tiền (chỉ ghép sổ).
- Thuế đầu ra (tài liệu 23): Nợ 131 77%, Nợ 138 10%, Nợ 112 10% — trường hợp 138 chưa rõ, cần anh chỉ ra là gì.
- NĐ 70/2025: BĐS lập hóa đơn khi thu tiền trước hoặc quyết toán; hủy/chấm dứt → điều chỉnh hóa đơn, cần **văn bản thỏa thuận** lưu ở kho chứng từ (A6).
- Thời điểm ghi nhận doanh thu nhà ở là **quyết định chính sách** — máy chỉ đề xuất theo ngày bàn giao được cung cấp, không tự suy.
- Phụ thuộc: M1 (tiền về), M4 (giá vốn dự án), M10 (phân bổ định kỳ KCN).

### 4.3 Con người làm gì
- **Phòng kinh doanh BĐS:** cung cấp hợp đồng + lịch thanh toán dạng bảng (một dòng một đợt: mã HĐ, khách, đợt, số tiền VND, hạn); báo bàn giao kèm biên bản; cập nhật khi thay đổi lịch.
- **Kế toán:** xác nhận đợt khi tiền về khớp nhiều đợt hoặc một phần; chọn 131 dư Có / 3387 theo chính sách đã chốt; xử lý hóa đơn điều chỉnh.
- **CFO:** chốt chính sách ghi nhận doanh thu nhà ở (bàn giao) và phân bổ KCN; chỉ rõ trường hợp Nợ 138; quyết có tự động nhắc nợ/gửi biên bản đối chiếu cho khách hay không (chưa có trong 01).

---

## 5. M4 · Hồ sơ nghiệm thu & chi phí dự án (N3 xây lắp, phần hành F)

### 5.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý riêng | Đầu ra |
|---|---|---|
| Hợp đồng thầu: giá trị, hạng mục, tỷ lệ tạm ứng, tỷ lệ giữ lại bảo hành, dự án/giai đoạn (KCN-DVI0/1/2) — **đã xác nhận 15/10: Ban QLDA có bảng Excel theo dõi** (cần xin mẫu để chốt cột) | Danh mục hợp đồng (A1): mỗi hợp đồng một mã, gắn dự án, hạng mục, nhà thầu (MST) | Hồ sơ hợp đồng có cấu trúc |
| Hồ sơ nghiệm thu khối lượng theo đợt: giá trị đợt, lũy kế, khấu trừ tạm ứng, giữ lại bảo hành — **đã xác nhận 15/10: biên bản ký PDF + bảng Excel theo dõi của Ban QLDA** | Khớp nghiệm thu ↔ hợp đồng (không vượt giá trị, đúng hạng mục) ↔ hóa đơn nhà thầu (M2) theo số tiền và kỳ | Bút toán: Nợ 241 (hoặc 154 theo chính sách) + Nợ 1331 / Có 331; Có 141/331 tạm ứng thu hồi; Có 3388/331 giữ lại bảo hành |
| Hóa đơn nhà thầu (từ M2), lệnh chi (M1) | Theo dõi vòng đời: tạm ứng → nghiệm thu → hóa đơn → thanh toán → bảo hành | Bảng theo dõi theo hợp đồng: tạm ứng còn lại, đã nghiệm thu, đã thanh toán, bảo hành chưa trả; danh sách vướng |

### 5.2 Dự kiến xử lý
- Khớp theo **số tiền và kỳ**, không OCR biên bản: máy đọc bảng Excel kèm hồ sơ; PDF chỉ lưu làm chứng từ gốc.
- Hóa đơn nhà thầu không có nghiệm thu khớp → treo Vàng ở M2; nghiệm thu không có hóa đơn → nhắc Ban QLDA/NCC.
- Lãi vay vốn hóa (M9) và chi phí chung phân bổ vào dự án → bút toán định kỳ (M10); kết chuyển giá vốn khi bàn giao (M3) ở mức **dự án**, không tính giá vốn từng căn/lô (đã cắt).
- Dự toán vs thực hiện: ngoài đợt (QT01).

### 5.3 Con người làm gì
- **Ban QLDA:** nộp nghiệm thu bằng bản mềm theo mẫu bảng thống nhất (mã hợp đồng, đợt, giá trị, tạm ứng khấu trừ, bảo hành) cùng biên bản ký; cập nhật phụ lục hợp đồng.
- **Kế toán:** duyệt lệch giữa nghiệm thu và hóa đơn (chênh làm tròn, thuế), xác nhận tỷ lệ khi hợp đồng không ghi rõ.
- **CFO:** chốt dùng 241 hay 154 cho từng loại dự án; chính sách vốn hóa lãi vay; mẫu bảng nghiệm thu bắt buộc.

---

## 6. M5 · Kho vận hành KCN (N6) — vật tư bảo trì, CCDC cấp phát

### 6.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý riêng | Đầu ra |
|---|---|---|
| Phiếu nhập kho (từ hóa đơn mua M2), phiếu xuất/cấp phát theo yêu cầu bộ phận **[giả định: thủ kho ghi Excel theo thiết kế 9 sheet đã có — cần xác nhận hiện trạng]** | Nhập – xuất – tồn đơn giản theo mã vật tư; giá nhập = hóa đơn + chi phí mua; giá xuất bình quân | Bút toán nhập kho (Nợ 152/153 / Có 331), xuất dùng (Nợ 627/642/241 / Có 152), CCDC cấp phát (Nợ 242 / Có 153 → phân bổ M10) |
| Biên bản kiểm kê định kỳ | So sổ ↔ thực tế | Bút toán chênh lệch (sau khi người quyết), danh sách chênh |

### 6.2 Dự kiến xử lý
- Khớp phiếu nhập ↔ hóa đơn mua theo NCC + số tiền; phiếu xuất ↔ yêu cầu cấp phát theo bộ phận/dự án → quyết TK chi phí và TTCP.
- Ranh giới với phân hệ kho của Junsky phải chốt: hệ thống mới là nguồn duy nhất / Junsky là nguồn duy nhất / chỉ đọc đối chiếu (tài liệu 01, lưu ý 1).

### 6.3 Con người làm gì
- **Thủ kho:** ghi phiếu đúng mẫu, mã vật tư thống nhất, kiểm kê định kỳ.
- **Kế toán:** duyệt bút toán xuất dùng khi yêu cầu không ghi bộ phận/dự án; quyết xử lý chênh lệch kiểm kê.
- **CFO:** chốt ranh giới với kho Junsky trước khi lập trình.

---

## 7. M6 · TSCĐ & CCDC (N3 + N8)

### 7.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý riêng | Đầu ra |
|---|---|---|
| Hóa đơn mua TSCĐ/CCDC (M2) + biên bản bàn giao/nghiệm thu đưa vào sử dụng | Nhận diện hóa đơn là tài sản (ngưỡng giá trị, từ khóa, nhóm G) → đề xuất ghi tăng, phân loại, bộ phận sử dụng | Bút toán ghi tăng: Nợ 211/213/242 + 1331 / Có 331 hoặc Có 241 (từ XDCB hoàn thành) |
| Bảng khấu hao / bảng phân bổ 242 **đã có** (Excel kế toán đang dùng) **[giả định — cần xác nhận hiện có bảng này không]** | Nhận bảng, kiểm tra tổng, đối chiếu danh sách tài sản | Bút toán khấu hao/phân bổ hằng tháng theo bộ phận/dự án (chạy trong M10) |

### 7.2 Dự kiến xử lý
- Không xây hệ quản lý tài sản (QT02); máy chỉ nhận bảng khấu hao và biến thành bút toán, cộng với ghi tăng từ hóa đơn.
- Kiểm kê, điều chuyển, thanh lý, đánh giá lại: ngoài đợt (chưa có trong 01).

### 7.3 Con người làm gì
- **Kế toán TSCĐ:** duy trì bảng khấu hao; quyết thời gian khấu hao, phân loại TS/CCDC khi máy gợi ý; xác nhận ngày đưa vào sử dụng.
- **Bộ phận sử dụng:** ký biên bản bàn giao, báo điều chuyển.

---

## 8. M7 · Lương & bảo hiểm (N7)

### 8.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý riêng | Đầu ra |
|---|---|---|
| Bảng lương Excel **đã tính** của nhân sự: mã NV, bộ phận, lương, BHXH/BHYT/BHTN (NV & DN), TNCN, thực lĩnh **[giả định mẫu — cần anh cấp mẫu bảng lương để chốt cột]** | Kiểm tra (bước 4): tổng khớp, mã NV/bộ phận có trong danh mục, so với kỳ trước | Bút toán lương: Nợ 642/627/241 theo bộ phận/dự án / Có 334, 338x, 3335; cảnh báo biến động |
| Bảng phân bổ bộ phận → TTCP/dự án (anh duyệt một lần) | Áp bảng phân bổ | Dòng bút toán đã có TTCP/dự án |
| Sao kê (M1): lệnh chi lương | Khớp tổng thực lĩnh ↔ lệnh chi | Dòng chi lương ở M1 thành Xanh; lệch → Đỏ |

### 8.2 Dự kiến xử lý
- Không chấm công, không tính lương (QT02). Một tháng một lô; bút toán mẫu cố định, chỉ số tiền và phân bổ thay đổi.
- Cảnh báo biến động: chưa có trong 01, đề xuất bổ sung vì rẻ (so kỳ trước).

### 8.3 Con người làm gì
- **Nhân sự:** nộp bảng lương đúng mẫu, đúng hạn; báo thay đổi bộ phận.
- **Kế toán:** duyệt lô lương (một lần/tháng), giải thích biến động vượt ngưỡng.
- **CFO:** duyệt bảng phân bổ bộ phận → TTCP/dự án.

---

## 9. M8 · Bảng kê thuế & đối chiếu cổng thuế (N2)

### 9.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý riêng | Đầu ra |
|---|---|---|
| XML HĐĐT mua/bán (M2, M3); danh sách hóa đơn tra cứu từ cổng thuế **[giả định: xuất Excel từ hoadondientu.gdt.gov.vn — cần xác nhận cách lấy]** | Đối chiếu 3 chiều: XML đã tải ↔ cổng thuế ↔ bút toán đã nạp Junsky; phát hiện thiếu, trùng, hủy, thay thế | Bảng kê hỗ trợ tờ khai GTGT (tiền hàng, thuế, thuế suất theo hóa đơn); danh sách hóa đơn lệch |
| Trạng thái NCC (rủi ro, bỏ địa chỉ) **[nguồn: tra cứu thủ công — chưa tự động]** | Gắn cờ rủi ro lên hóa đơn | Cảnh báo trước khi khấu trừ |

### 9.2 Dự kiến xử lý
- **Không lập tờ khai** (QT03) — tờ khai chính thức làm trong Junsky/HTKK; hệ thống chỉ ra bảng kê và danh sách lệch.
- Điều kiện khấu trừ (thanh toán không dùng tiền mặt) lấy từ M2 ↔ M1.
- Hóa đơn sai sót: cần văn bản thỏa thuận hai bên (NĐ 70/2025) → kho chứng từ A6.

### 9.3 Con người làm gì
- **Kế toán thuế:** tải danh sách từ cổng thuế theo tháng; xử lý hóa đơn lệch; lập và nộp tờ khai trong Junsky/HTKK; tra cứu rủi ro NCC khi máy cảnh báo.

---

## 10. M9 · Vốn vay & đầu tư tài chính (A1 + N1 + N8)

### 10.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý riêng | Đầu ra |
|---|---|---|
| Hợp đồng vay: ngân hàng, hạn mức, lãi suất, lịch trả gốc/lãi, mục đích (dự án nào) **[giả định: pháp chế/tài chính nhập bằng tay vào danh mục hợp đồng A1 — cần xác nhận ai giữ]** | Danh mục hợp đồng vay; sinh lịch dự kiến | Bảng theo dõi dư nợ, đáo hạn |
| Sao kê (M1): giải ngân, trả gốc, trả lãi, lãi tiền gửi | Khớp dòng sao kê ↔ lịch hợp đồng theo ngân hàng + số tiền + kỳ | Bút toán Xanh ở M1: Nợ 112 / Có 341 (giải ngân); Nợ 341 / Có 112 (trả gốc); Nợ 635 hoặc 241 / Có 112 (lãi) |
| Chính sách vốn hóa lãi vay theo dự án | Phân loại lãi: vốn hóa 241 vs chi phí 635; lãi dự trả cuối kỳ | Bút toán định kỳ (M10) |

### 10.2 Dự kiến xử lý
- Chi cho ngân hàng chiếm 506 dòng lịch sử với 133/642/241/341 (tài liệu 23) → khi có lịch hợp đồng, phần 341 và lãi thành khớp cứng thay vì đoán từ nội dung.
- Covenant, hạn mức, bảo lãnh: ngoài đợt (chưa có trong 01).

### 10.3 Con người làm gì
- **Tài chính/pháp chế:** nhập hợp đồng vay và cập nhật khi tái cơ cấu.
- **Kế toán:** xác nhận khi ngân hàng tự trích lãi lệch lịch; CFO chốt tỷ lệ vốn hóa theo dự án.

---

## 11. M10 · Bút toán định kỳ, đóng sổ & đối chiếu ngược (N8 + V4 + A4)

### 11.1 Đầu vào → xử lý → đầu ra

| Đầu vào | Xử lý riêng | Đầu ra |
|---|---|---|
| Bảng khấu hao (M6), bảng phân bổ 242, lịch trích trước 335, lịch phân bổ doanh thu KCN (M3), lãi dự trả (M9), tỷ giá cuối kỳ | Mỗi tháng sinh lô bút toán định kỳ theo mẫu cố định; so với tháng trước, cảnh báo lệch | Lô bút toán định kỳ (02GJ) chờ duyệt |
| Checklist đóng sổ (anh duyệt một lần: việc, người, hạn, điều kiện) | Theo dõi trạng thái từng việc; nhắc việc chưa xong | Bảng checklist theo ngày của kỳ đóng |
| Sổ Junsky sau khi nạp (xuất Excel từ Junsky) + nhật ký lô đã đẩy | **Bước 8:** đối chiếu từng chứng từ theo `EntryID`/`DocsNo` ↔ mã bút toán nguồn; số dư 112 theo sao kê ↔ Junsky | Báo cáo đối chiếu ngược: khớp / lệch / thiếu / thừa; bảng tình trạng đường ống (V2) |

### 11.2 Dự kiến xử lý
- Bút toán định kỳ là nơi **tự động hóa dễ nhất và an toàn nhất**: mẫu cố định, dữ liệu từ bảng người đã duyệt; mức Xanh gần 100% sau tháng đầu.
- Đối chiếu ngược phụ thuộc mẫu xuất sổ của Junsky (chưa có — việc gấp nhất trong tài liệu 01) và câu trả lời Junsky có giữ `EntryID` hay không.
- Không bỏ bước 8: nếu không đối chiếu ngược, hệ thống chỉ là công cụ tạo file.

### 11.3 Con người làm gì
- **Kế toán tổng hợp:** duyệt lô định kỳ (một lần/tháng), chạy đối chiếu ngược sau mỗi lần nạp, xử lý dòng lệch trong Junsky, tích checklist.
- **CFO:** duyệt checklist đóng sổ lần đầu; xem bảng tình trạng đường ống; ký đóng sổ.
- **Nhà cung cấp Junsky:** cấp mẫu xuất sổ/chứng từ để máy đọc ngược.

---

## 12. Thông tin đầu vào còn thiếu — phải xác nhận trước khi chia giai đoạn

| # | Cần biết | Ảnh hưởng module | Ai trả lời |
|---|---|---|---|
| 1 | Base xuất được RQ dạng file/API không; các loại form ngoài RQ 2025 | M1, M2 | Anh / quản trị Base |
| 2 | PO, hợp đồng mua, hồ sơ nghiệm thu đang lưu ở đâu, định dạng gì | M2, M4 | Phòng mua hàng, Ban QLDA |
| 3 | Hợp đồng BĐS + lịch thu có xuất dạng bảng từ CRM không; biên bản bàn giao lưu ở đâu | M3 | Phòng kinh doanh |
| 4 | Mẫu bảng lương, bảng khấu hao, bảng phân bổ 242 hiện dùng | M6, M7, M10 | Kế toán, nhân sự |
| 5 | Hợp đồng vay ai giữ, có bảng theo dõi chưa | M9 | Tài chính/pháp chế |
| 6 | Cách lấy danh sách hóa đơn từ cổng thuế (xuất Excel?) | M8 | Kế toán thuế |
| 7 | 3 câu Junsky + danh mục `BankID`, `CashflowID` + mẫu xuất sổ | M0, M10 | Nhà cung cấp Junsky |
| 8 | ~~Kênh hỏi phòng ban~~ — **đã chốt: agent Zalo Bot (mục 1.4)**; còn phải thử bot có nhắn trước được không | M1, M2, M4 | Claude thử |
| 9 | Hai câu bước 2 phễu: đối tác hai vai trò; tiền khách về không khớp công nợ | M1 | Anh |
| 10 | Ranh giới với phân hệ kho Junsky | M5 | Anh |
| 11 | Mẫu bảng Excel theo dõi hợp đồng/nghiệm thu của Ban QLDA (đã xác nhận có) | M4 | Ban QLDA |

## 13. Bước tiếp theo
1. ~~Anh chốt 4 điểm~~ — đã chốt 15/10 (xem mục 0).
2. Anh duyệt bảng khảo sát đầu vào (tài liệu 30) → kế toán gửi các phòng ban → thu câu trả lời và mẫu file.
3. Song song: Claude thử Zalo Bot (tạo bot thử, gửi/nhận một tin) để xác nhận điều kiện nhắn trước và nhóm chat.
4. Khi có câu trả lời khảo sát, chia giai đoạn lập trình theo nguyên tắc tài liệu 01: mỗi giai đoạn đi trọn 8 bước cho **một** loại chứng từ.
