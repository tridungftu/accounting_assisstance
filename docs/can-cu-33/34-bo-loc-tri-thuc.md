# 34 · Bộ lọc tri thức — lớp chung chuẩn hóa, nhận diện, liên kết và định tuyến cho mọi chứng từ

**Ngày lập:** 16/10/2026 · **Nguồn ý tưởng:** anh Dũng (16/10): "từ các loại hình dữ liệu phải đi chung vào một bộ lọc tri thức mới tạo ra được các loại nghiệp vụ và liên kết nghiệp vụ; bộ lọc này cần Local AI hoặc LLM cloud để định dạng theo tri thức học rồi mới tiến hành các bước tiếp theo."
**Căn cứ:** tài liệu 01 (đường ống 8 bước: từ bước 3 dùng chung), 03/04/05 (cơ chế nhận dạng, cây loại giao dịch, sơ đồ suy luận), 09 (tri thức theo nhóm nghiệp vụ), 20 (tham khảo TaxHacker cho tầng AI cục bộ), 23 (phễu 6 bước, vị trí LLM), 27 (V12 học từ hóa đơn), 32 (liên kết chéo), 33 (cây nghiệp vụ v2).
**Bảo mật:** tài liệu nêu cách xử lý dữ liệu nội bộ; không đưa ra ngoài.

---

## 0. Kết luận trước

- **Đúng về kiến trúc.** Cái anh gọi là bộ lọc tri thức chính là **bước 2 (bóc tách) + bước 3 (khớp)** của đường ống, gom thành **một lớp chung cho mọi loại chứng từ**. Hiện nay hai bước này đang rải trong từng bộ đọc (sao kê có phễu riêng, hóa đơn có cách học riêng ở V12), nên tri thức không dùng chung được và liên kết chéo khó làm. Gom lại thì: tri thức học một nơi, chữ viết một mẫu, liên kết sinh ra tự nhiên.
- **Bộ lọc có 4 tầng**: ① chuẩn hóa về một mẫu chứng từ chung → ② nhận diện đối tượng / hợp đồng / loại nghiệp vụ bằng tri thức → ③ đề xuất liên kết với chứng từ khác → ④ định tuyến sang chu trình kèm đích và mức tin cậy. Sau bộ lọc, mỗi chu trình M1–M10 chỉ còn làm **bước 4–5** (kiểm tra hợp lệ nghiệp vụ, áp mẫu bút toán) rồi vào màn hình duyệt.
- **LLM đứng ở hai chỗ, không hơn:** (a) tầng ① cho nguồn **phi cấu trúc** (PDF hợp đồng, biên bản, nội dung chuyển khoản tự do) — "định dạng theo tri thức học" nghĩa là ép văn bản tự do vào mẫu chung với bộ từ vựng đã học; (b) tầng ② chọn 1 trong 2–5 ứng viên khi khóa cứng, từ khóa và lịch sử không quyết được. Nguồn đã có cấu trúc (XML, Excel, API) **không cần LLM**. Mọi trường LLM điền phải có trích dẫn hoặc căn cứ; Python kiểm duyệt; kết quả LLM tối đa Vàng (quy tắc đã có từ tài liệu 23).
- **Local AI hay LLM cloud là quyết định chính sách, không phải kỹ thuật.** Quy ước hiện hành (tài liệu 00) là "AI cục bộ, không gọi API ngoài". Anh nêu khả năng dùng cloud — tôi đưa ba phương án ở mục 3 với điều kiện bảo mật; **chưa thay đổi quy ước cho đến khi anh chốt**.
- **Thứ tự làm:** bộ lọc tri thức là xương sống, nên gộp với bảng liên kết chứng từ (đã chốt làm ngay) thành **V13 · Xương sống bước 2–3**, trước M4 · Nghiệm thu & chi phí dự án. Phần có LLM tách thành V riêng sau khi có đáp án mẫu để chấm.

---

## 1. Vị trí trong đường ống

```
Nguồn → Bộ tiếp nhận (bước 1: lấy file / API)
      → BỘ LỌC TRI THỨC (bước 2–3, dùng chung)
            ① chuẩn hóa  ② nhận diện  ③ liên kết  ④ định tuyến
      → Chu trình M1–M10 (bước 4–5: kiểm tra hợp lệ nghiệp vụ, mẫu bút toán)
      → Màn hình duyệt (bước 6) → Excel Junsky (7) → đối chiếu ngược (8)
```
Hiện trạng: bộ đọc sao kê (V10–V12) đã làm ①②④ cho sao kê; V12 làm ①②④ cho hóa đơn theo cách khác; ③ chỉ có bậc 0 tiền ↔ công nợ. Việc của V13 là **tách phần chung ra khỏi hai bộ đọc** và cho các nguồn còn lại đi qua cùng một chỗ.

## 2. Bốn tầng của bộ lọc

### 2.1 Tầng ① — Chuẩn hóa về mẫu chứng từ chung
Mọi loại chứng từ → một bản ghi `chung_tu_chuan` (một dòng = một chứng từ; dòng chi tiết ở bảng con):

| Nhóm trường | Nội dung | Nguồn điền |
|---|---|---|
| Định danh | mã chứng từ chuẩn, loại chứng từ (sao kê / hóa đơn mua / hóa đơn bán / RQ / hợp đồng / nghiệm thu / bảng lương / phiếu kho / bảng phân bổ), nguồn, mã tham chiếu gốc, file gốc (A6) | Bộ tiếp nhận |
| Thời gian | ngày chứng từ, kỳ | Python |
| Đối tác thô | tên như trên chứng từ, MST, CCCD, STK, tên chủ TK | Python (XML, sao kê, RQ) · LLM (PDF) |
| Tiền | số tiền, tiền tệ (VND/USD), tỷ giá nếu có, thuế suất, tiền thuế | Python |
| Chi tiết | dòng hàng / đợt / hạng mục: mô tả, số lượng, đơn giá, thành tiền | Python (XML) · LLM (PDF hợp đồng, nghiệm thu) |
| Tham chiếu | số hóa đơn, mã RQ, mã hợp đồng, mã dự án, số PO ghi trên chứng từ | Python (regex) · LLM khi tự do |
| Văn bản tự do | nội dung chuyển khoản, diễn giải, điều khoản trích dẫn | giữ nguyên + bản không dấu |
| Chất lượng | trường nào do LLM điền, trích dẫn nguyên văn, độ tin cậy từng trường | bắt buộc |

Nguyên tắc: Python đọc được thì không gọi LLM; LLM chỉ điền trường còn trống từ văn bản tự do và **phải kèm trích dẫn**; không có trích dẫn → để trống, ghi "cần người xem".

### 2.2 Tầng ② — Nhận diện bằng tri thức
Ba câu hỏi cho mọi chứng từ, mỗi câu đi theo thang **khóa cứng → từ khóa cụm dài → lịch sử sổ → LLM chọn trong ứng viên → người**:
1. **Đối tượng là ai?** danh bạ đối tác (3 quy tắc STK, MST), danh mục đối tượng Junsky; tri thức CFO.
2. **Thuộc hợp đồng / dự án nào?** danh mục hợp đồng (CRM kế toán, hợp đồng thầu, hợp đồng vay), mã dự án; lịch sử đối tác → dự án (V12).
3. **Loại nghiệp vụ gì?** cây loại giao dịch (tài liệu 04), 33 nhóm G, loại hình doanh thu; tri thức học từ sổ (cùng đối tác + tên hàng → TK, như V12) → suy ra **đích** (chi phí / 241 / tài sản / kho) theo nguyên tắc 2 đã chốt.

Tri thức dùng chung ở đây: danh mục A1 · bộ từ khóa 432 cụm không dấu · tri thức học từ sổ (đến 30/06/2026 khi chấm điểm) · tri thức CFO (`TRI-THUC-CFO.json`) · tri thức chờ duyệt từ sửa chữa của kế toán (tài liệu 09, 26).

### 2.3 Tầng ③ — Liên kết
Với chứng từ vừa nhận diện, tìm chứng từ khác đã có để nối: tiền ↔ công nợ mở (bậc 0), hóa đơn ↔ RQ, hóa đơn ↔ nghiệm thu, hóa đơn ↔ phiếu nhập kho, hợp đồng ↔ đợt ↔ tiền, 241 ↔ tài sản. Kết quả ghi vào `lien_ket_chung_tu` (tài liệu 32, đã chốt làm ngay) với trạng thái "đề xuất" cho đến khi người duyệt. Tiền đến trước → nguyên tắc 1 đã chốt (Vàng theo quy tắc CFO, không treo).

### 2.4 Tầng ④ — Định tuyến
Gắn cho chứng từ: **nhãn nghiệp vụ** (loại giao dịch / nhóm G / loại hình doanh thu) → **chu trình tiếp nhận** (M1–M10) → **đích** → **mức tin cậy** Xanh / Vàng / Đỏ (theo căn cứ ở tầng ②③) → nếu Đỏ và có người phụ trách rõ: **câu hỏi cho agent Zalo** với phương án đánh số. Một chứng từ nhiều dòng có thể đi nhiều chu trình (hóa đơn có dòng vật tư → M5 · Kho và dòng dịch vụ → M2 · Phải trả), nhưng mỗi dòng một đích.

## 3. LLM trong bộ lọc — ba phương án (chờ anh chốt)

| | A · Local AI (tự vận hành) | B · Lai: Local mặc định, cloud qua Mask cho ca khó | C · LLM cloud qua Mask cho toàn bộ |
|---|---|---|---|
| Dữ liệu đi đâu | Máy nội bộ hoặc GPU thuê (RunPod như #6 đang dùng — vẫn là hạ tầng ngoài, nhưng mô hình do ta vận hành) | Phần lớn ở nội bộ; ca khó đi ra ngoài sau khi "#13 Local Mask" thay tên/mã bằng bí danh | Toàn bộ văn bản tự do đi ra ngoài sau Mask |
| Chất lượng tiếng Việt / hợp đồng | Phụ thuộc mô hình (qwen3.6:35b ở #6 — chưa có số đo cho hợp đồng BĐS, nội dung chuyển khoản) | Tốt nhất ở ca khó | Tốt nhất, ổn định |
| Chi phí vận hành | GPU thuê theo giờ hoặc mua máy (POC #21 chưa chốt) | Thấp hơn A nếu GPU chỉ bật khi cần | Trả theo lượt; không cần GPU |
| Phù hợp quy ước 00 | Đúng ("AI cục bộ, không gọi API ngoài") | Phải sửa quy ước, kèm điều kiện | Phải sửa quy ước, kèm điều kiện |
| Điều kiện bắt buộc nếu chọn B/C | — | Mask bí danh nhất quán cho tên, MST, STK, số hợp đồng; không gửi số dư; log mọi lượt gọi; anh duyệt **từng loại chứng từ** được phép gửi; có công tắc tắt cloud | như B, cộng thêm đánh giá nhà cung cấp |

Khuyến nghị của tôi: **A để bắt đầu, thiết kế sẵn công tắc để nâng lên B** khi có số đo cho thấy Local AI không đủ trên ca khó. Lý do: dữ liệu bộ lọc là toàn bộ hợp đồng, công nợ, lương của tập đoàn; và theo số đo V11–V12, phần lớn chứng từ giải được bằng khóa cứng + lịch sử, LLM chỉ còn cho phần đuôi.

Dù chọn gì, ba điều không đổi: **LLM đề xuất – Python kiểm duyệt**; trường LLM điền phải có trích dẫn; kết quả có LLM tham gia tối đa Vàng; mỗi loại chứng từ có **đáp án mẫu** để chấm trước khi bật LLM cho loại đó.

## 4. Con người làm gì khi có bộ lọc
- Kế toán duyệt ở **một màn hình** cho mọi loại chứng từ (không mỗi loại một màn): thấy chứng từ chuẩn hóa, nhãn nghiệp vụ, liên kết đề xuất, căn cứ; Đồng ý / Sửa / Bỏ; sửa chữa thành tri thức chờ duyệt.
- CFO duyệt tri thức, chốt chính sách LLM (mục 3), ký danh sách loại chứng từ được dùng LLM.
- Phòng ban: trả lời câu hỏi agent Zalo; nộp chứng từ đúng định dạng tại nguồn.

## 5. Thay đổi đối với kế hoạch đã có
- Tài liệu 29: mục "bước 3–5 trong từng module" chuyển phần ①②③④ về bộ lọc; module giữ bước 4–5 riêng của nghiệp vụ.
- Tài liệu 32: bảng liên kết là tầng ③ của bộ lọc.
- Tài liệu 33: cây v2 đã thêm cột bộ lọc tri thức (16/10).
- Hàng đợi: mục #23 "Bộ lọc tri thức — tách phần chung khỏi bộ đọc sao kê và hóa đơn; `chung_tu_chuan`; màn hình duyệt chung" — gộp với #18 thành V13; mục #24 "LLM trong bộ lọc — chờ chốt phương án A/B/C + đáp án mẫu".
- Quy ước 00: dòng "AI cục bộ, không gọi API ngoài" **giữ nguyên cho đến khi anh chốt mục 3**.

## 6. Trả lời của anh Dũng 16/10/2026 và điều chỉnh thiết kế

### 6.1 Kiến trúc — anh tinh chỉnh: bước 2 bóc tách **vừa để nhận diện, vừa để tạo cơ sở dữ liệu**, rồi dữ liệu mới đi chung vào phần tri thức
Điều chỉnh so với mục 1–2 ở trên (cây v3, tài liệu 33):
```
Bộ tiếp nhận (bước 1)
  → BƯỚC 2 · BÓC TÁCH → KHO DỮ LIỆU CHUNG           ← tầng ① chuyển về đây, có lưu trữ
        bảng chứng từ chuẩn + bảng chuyên biệt (hợp đồng & lịch thu, nghiệm thu,
        hóa đơn & dòng hàng, sao kê, RQ, bảng lương, phiếu kho, bảng phân bổ)
        + danh mục A1 (đối tượng, hợp đồng, dự án, tài sản, tài khoản)
  → BỘ LỌC TRI THỨC (bước 3) đọc từ kho dữ liệu chung:   ② nhận diện · ③ liên kết · ④ định tuyến
  → Chu trình M1–M10 (bước 4–5) → duyệt (6) → Junsky (7) → đối chiếu ngược (8)
```
- Ý nghĩa: bóc tách không chỉ là "đọc để phân loại" mà **tạo ra database nghiệp vụ** — ví dụ hợp đồng được bóc tách thành bản ghi hợp đồng + lịch thu (CRM kế toán), nghiệm thu thành bản ghi nghiệm thu có mã hợp đồng, hóa đơn thành bản ghi hóa đơn + dòng hàng. Bộ lọc tri thức làm việc **trên các bảng đó**, không trên file thô; vì vậy một chứng từ có thể được nhận diện lại nhiều lần khi tri thức thay đổi mà không cần đọc lại file.
- Dữ liệu bóc tách bằng LLM (PDF, văn bản tự do) vào kho ở trạng thái **chờ duyệt**; kế toán duyệt (nhìn trích dẫn) thì mới có hiệu lực cho bộ lọc và cho các chu trình.
- Hệ quả schema cho V13: `chung_tu_chuan` (chung) + bảng chuyên biệt theo loại + `lien_ket_chung_tu` + các cột "nguồn điền / trích dẫn / trạng thái duyệt" trên mọi bảng bóc tách.

### 6.2 LLM — anh chốt: **"Trước hết qua Cloud có Local Mask"**; đồng thời hỏi *"có cần qua Jev để quyết định trước không?"*
- Ghi nhận: phương án **C (cloud qua Local Mask) đi trước**, Local AI giữ làm công tắc dự phòng (A) để chuyển khi cần. Điều này phù hợp bản chung mục 6 ("tài liệu nội bộ chuyển cho AI bên ngoài thì đi qua Local Mask và Anh duyệt"), nhưng **khác quy ước 00** của dự án kế toán ("AI cục bộ, không gọi API ngoài") → sẽ sửa 00 sau khi anh xác nhận điều kiện dưới đây.
- Điều kiện bắt buộc khi gọi cloud: (1) mọi văn bản đi qua "#13 Local Mask" với **bí danh nhất quán** cho tên người/công ty, MST, STK, số hợp đồng, mã nhân viên; số tiền và ngày giữ nguyên (cần cho nhận diện); (2) không gửi số dư, không gửi cả sao kê/sổ — chỉ gửi từng chứng từ cần bóc tách hoặc câu hỏi chọn phương án; (3) khóa API trong `.env`, log mọi lượt gọi (loại chứng từ, số ký tự, thời điểm, chi phí); (4) anh duyệt **danh sách loại chứng từ** được phép gửi cloud (đề xuất ban đầu: hợp đồng PDF, biên bản nghiệm thu PDF, nội dung chuyển khoản tự do; **không** gửi bảng lương); (5) công tắc tắt cloud ngay trong cấu hình; (6) nhà cung cấp: chưa chốt — đề xuất dùng API của mô hình Claude vì anh đang dùng Claude cho toàn bộ dự án; chi phí theo lượt sẽ đo trên tháng thử, không ước lượng trước.
- **"JEV" — anh giải thích 16/10:** là *Jev Router* (TypeSafe) — model quyết định Jev 1.13 chấm độ khó request rồi chuyển sang tầng model Light / Standard / Heavy (GPT, DeepSeek, Gemini, Claude) qua gateway AI/ML API hoặc OpenRouter; phí định tuyến nhỏ cộng vào giá model trả lời ([Jev Router explained](https://aimlapi.com/blog/jev-router-explained), [OpenRouter](https://openrouter.ai/typesafe/jev-router)). Nội dung (đã Mask) đi qua gateway trung gian và tới nhà cung cấp do router chọn; chính sách lưu dữ liệu của router không được nêu.
- **Anh chốt 16/10: cổng AI định tuyến tĩnh theo loại việc, thiết kế để cắm Jev sau** khi có số đo chi phí API (khối lượng nhỏ, độ khó biết trước theo loại việc, dữ liệu nhạy cảm → một nhà cung cấp, dữ liệu đi một nơi).

### 6.3 Thứ tự — anh chốt: **V13 làm cả LLM**
V13 · Xương sống bước 2–3, chia ba phần giao nộp nhỏ (đúng tiêu chuẩn "code theo giai đoạn nhỏ, test xanh mới sang phần sau"), nhưng cùng một V:
- **V13.1 Kho dữ liệu chung + bảng liên kết**: schema `chung_tu_chuan`, bảng chuyên biệt, `lien_ket_chung_tu`; tách phần chung khỏi bộ đọc sao kê và hóa đơn; chấm lại T8 phải **không kém** V12 (sao kê 41/52/12, hóa đơn bán ra 11/20/5, mua vào 0/22/17).
- **V13.2 Bộ lọc tri thức không LLM**: ②③④ trên kho dữ liệu chung, một màn hình duyệt chung, CFO-02, đích theo tri thức học.
- **V13.3 LLM qua Local Mask**: bóc tách PDF hợp đồng / nghiệm thu, chọn trong ứng viên; **bắt buộc có đáp án mẫu trước** (10–20 hợp đồng mỗi loại hình doanh thu, 10 nghiệm thu, 50 nội dung chuyển khoản khó) và báo điểm trước/sau; nối Mask (#13, cổng 8017/8019).
- Trước khi xin lệnh code V13: chốt **màn hình duyệt chung** rồi **schema** (cổng 3 của tiêu chuẩn) — tài liệu 35.

### 6.4 Còn chờ anh (bảng chọn gửi kèm)
1. Xác nhận kiến trúc đã điều chỉnh ở 6.1 (bước 2 tạo kho dữ liệu chung → bộ lọc tri thức đọc từ kho).
2. "Jev" là gì/ai.
3. Danh sách loại chứng từ được phép gửi cloud qua Mask và nhà cung cấp LLM.
