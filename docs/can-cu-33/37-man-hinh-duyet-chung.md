# 37 · Màn hình duyệt chung (K5) — đặc tả để chốt trước schema

**Ngày lập:** 16/10/2026 · **Trạng thái:** **ĐÃ CHỐT 16/10/2026 (chiều)** — anh trả lời 4 câu §13: một danh sách gộp · CFO duyệt cả tham số hợp đồng · agent Zalo tự hỏi cho loại việc đã định · chọn một pháp nhân mỗi lúc, CFO có "Tất cả". Bước kế tiếp: tài liệu 38 (schema) · **Vị trí trong kiến trúc:** khối K5 "Duyệt → Junsky → đối chiếu ngược" (TL 35 §1), bước 6–8 đường ống (TL 01).
**Vì sao làm bước này trước schema:** tiêu chuẩn nội bộ "chốt màn hình rồi chốt schema" (TL 31; CLAUDE.md). Màn hình quyết định dữ liệu nào phải có trên mỗi dòng → đó chính là trường của bảng.
**Kế thừa:** màn hình Định khoản V11/V12 đang chạy thật (`docs/HUONG-DAN-DINH-KHOAN.md`, prototype `docs/thiet-ke/dinh-khoan-prototype.html` + `BAN-GIAO-dinh-khoan.md`): giữ nguyên cách làm việc đã quen (Xanh/Vàng/Đỏ, Đồng ý/Sửa/Bỏ qua, "vì sao" có số đo, ngăn Sửa bên phải, phím tắt). Tài liệu này chỉ **mở rộng** cho mọi loại việc, mọi chu trình, nhiều pháp nhân, chuỗi liên kết, agent Zalo và vòng Junsky.
**Sơ đồ luồng bấm:** `37-man-hinh-duyet-chung.drawio` (mở bằng draw.io, kéo thả được) + `.png`/`.svg` xem trước + `.sinh-so-do.py` sinh lại — trên máy anh tại `D:\Claude\Phan mem ho tro ke toan\`.
**Không lập trình trong bước này.** Dữ liệu ví dụ trong tài liệu là giả hoặc chỉ là mã danh mục.

---

## 0. Mục đích và tám nguyên tắc của màn hình

1. **Một màn hình cho mọi việc cần người quyết** — không mỗi chu trình một màn hình. Kế toán mở phần mềm là thấy ngay "hôm nay có bao nhiêu việc, việc nào gấp".
2. **Nhìn một dòng hiểu ngay máy đề xuất gì và vì sao** (giữ từ V11): mỗi dòng có đề xuất tóm tắt + một câu "vì sao" có số đo.
3. **Máy chỉ đề xuất; chỉ dòng ĐÃ DUYỆT mới ra khỏi hệ thống** (file Excel). Không nút nào ghi vào Junsky.
4. **Thà bỏ sót còn hơn nhập sai**: nút Đồng ý chỉ bấm được khi dòng đủ điều kiện (§5.3); thiếu thì mờ và nói rõ thiếu gì.
5. **Mọi thao tác là một dòng nhật ký** (ai, lúc nào, trước/sau, căn cứ); Hoàn tác là một dòng nhật ký mới, không xóa.
6. **Sửa = tri thức chờ duyệt**: kế toán sửa → máy đề cử tri thức → CFO duyệt ở màn Tri thức → mới áp cho dòng khác (TL 35 §2).
7. **Mã pháp nhân trên mọi dòng**; người dùng chỉ thấy pháp nhân được phân quyền (TL 35 §8.3).
8. **Màn hình nội bộ hiện tên thật**; Mask chỉ áp dụng khi dữ liệu rời máy qua cổng AI (TL 35 §3). Không bao giờ hiện bí danh cho kế toán.

## 1. Đơn vị của màn hình: "việc cần duyệt"

Mọi thứ cần người quyết là **một dòng** trong cùng danh sách. Tám loại việc:

| # | Loại việc | Do khối nào sinh | Ai duyệt (đề xuất) | Nút chính | Ví dụ tại PLHN |
|---|---|---|---|---|---|
| V1 | **Bút toán đề xuất** | K4 chu trình M1–M10 | Kế toán phần hành | Đồng ý / Sửa / Hỏi / Bỏ qua | tiền về 131171 đợt 2; hóa đơn phí quản lý; trả nợ gốc vay 34112; bút toán phân bổ 33871 |
| V2 | **Liên kết chứng từ cần xác nhận** | K3 ③ (bảng `lien_ket_chung_tu`) | Kế toán | Xác nhận / Gỡ / Chọn khác | 9 lần chuyển cùng ngày = 1 hóa đơn; hóa đơn nhà thầu ↔ nghiệm thu đợt 3; tiền ↔ đợt thu |
| V3 | **Tham số bóc tách chờ duyệt** | K2 (LLM bóc PDF: hợp đồng, phụ lục, nghiệm thu) | **CFO_NTD duyệt** (anh chốt 16/10); kế toán công nợ kiểm trước, phòng kinh doanh / Ban QLDA chỉ xác nhận | Đồng ý tham số / Sửa (có trích dẫn nguyên văn) | lịch thu 5 đợt của một hợp đồng thuê đất; tỷ lệ bảo hành hợp đồng thầu |
| V4 | **Danh mục / master file thay đổi** | K2–K3 | Kế toán; CFO với danh mục nhạy cảm | Đồng ý / Sửa / Từ chối | STK mới của một khách; đối tác mới chưa có mã Junsky (→ "tạo ở Junsky trước"); phụ lục đổi lịch |
| V5 | **Câu hỏi đang chờ phòng ban** | agent Zalo (do Hỏi hoặc do máy Đỏ) | Kế toán theo dõi | Xem trả lời / Nhắc lại / Tự quyết | "tiền về lệch đợt — phòng kinh doanh chọn 1/2/3" |
| V6 | **Tri thức chờ CFO duyệt** | từ Sửa có "ghi nhớ", từ quy tắc máy đề cử | **CFO_NTD** | Duyệt / Sửa / Từ chối, kèm số đo tác động | "STK X → mã Y" (3 lần nhất quán); "TRA NO + VAY → 34112" |
| V7 | **Lô Junsky & đối chiếu ngược** | K5 bước 7–8 (M10) | Kế toán tổng hợp | Đánh dấu đã nạp / Xử lý lệch / Tạo bút toán điều chỉnh | lô T8-01: 2 dòng lệch giá trị, 1 dòng thừa ở Junsky |
| V8 | **Cảnh báo / khóa** | xương sống | Kế toán / CFO | Mở màn hình xử lý | "chưa nạp danh mục đối tượng"; "kỳ 08/2026 đã khóa"; "sao kê 112121 chưa nạp 2 tháng" |

Nguyên tắc: **một danh sách, nhiều loại việc, cùng bộ nút**. Loại việc chỉ là một bộ lọc và quyết định ngăn chi tiết hiện gì.

## 2. Bố cục màn hình

**Thanh trên:** tên phần mềm · nhãn KHO THẬT / KHO THỬ · **ô chọn pháp nhân** (PLHN · pháp nhân 2 · Tất cả — chỉ CFO thấy "Tất cả") · "Không tự nhập Junsky — chỉ tạo file" · tình trạng dữ liệu nền ("Sổ Junsky đến dd/mm · Máy học đến dd/mm") · trạng thái cổng AI (tắt / cloud / local) · mức 2 (khóa/mở).

**Menu trái (6 mục, luôn hiện chữ):**
1. **Việc cần duyệt** (màn hình chính — tài liệu này)
2. **Chứng từ & chuỗi liên kết** (tra cứu mọi chứng từ đã bóc tách, theo trạng thái; mở chuỗi liên kết)
3. **Danh mục master** (9 danh mục: hợp đồng xây dựng, hợp đồng bán hàng + lịch thu, đối tác, dự án, vay, tài sản, nhân viên, pháp nhân & bối cảnh — chỉ đọc + phiên bản; phòng kinh doanh xem ở đây)
4. **Tri thức** (tra cứu + hàng chờ CFO duyệt — V6)
5. **Lô Junsky & đối chiếu** (lịch sử xuất, nạp, đối chiếu ngược — V7)
6. **Nguồn dữ liệu & cài đặt** (nạp lại, mốc học, chế độ chấm điểm, TK ngân hàng ↔ TK kế toán, cổng AI, danh bạ Zalo nội bộ)

**Màn hình chính — sáu vùng:**

| Vùng | Nội dung | So với V11 |
|---|---|---|
| A · Nhập chứng từ | ô thả file (tự nhận loại) **+ thẻ "nguồn tự động"** (thư mục hóa đơn #7, backup Base #8, kết quả review #5, Sheet vay #9 — máy tự lấy theo lịch, hiện "lấy lúc hh:mm, n chứng từ mới") | thêm nguồn tự động |
| B · Thanh tổng | ô theo **mức**: Xanh · Vàng · Đỏ · Đã có Junsky; ô theo **trạng thái người**: Đang hỏi · Chờ bổ sung; mỗi ô: số dòng + tổng tiền VND, bấm là lọc. Thanh tiến độ kỳ "Đã duyệt n/N"; **ngày tồn** lớn nhất của việc chờ | thêm Đang hỏi, Chờ bổ sung, ngày tồn |
| C · Bộ lọc | pháp nhân · **loại việc V1–V8** · **chu trình M1–M10** · mức · trạng thái · chiều · **người phụ trách** · **hạn / ngày tồn** · tìm (diễn giải, đối tác, số tiền, số hợp đồng, số hóa đơn) | thêm loại việc, chu trình, người, hạn |
| D · Danh sách | dòng thu gọn (§3), mở chi tiết tại chỗ (§4) | giữ, thêm cột |
| E · Ngăn phải | Sửa (giữ) · **Chuỗi chứng từ** · **Hỏi Zalo** · **Yêu cầu bổ sung** · Ghi chú AI | thêm 3 ngăn |
| F · Hàng loạt & xuất | "Đồng ý tất cả dòng Xanh đang lọc" (giữ) · "Xuất lô" (giữ; thêm chọn pháp nhân, kỳ) | giữ |

## 3. Dòng thu gọn — cột chuẩn cho mọi loại việc

| Cột | Nội dung | Ghi chú |
|---|---|---|
| Mức | ● Xanh / ● Vàng / ● Đỏ / ○ Junsky — màu + biểu tượng + chữ | giữ V11 |
| Loại việc · chu trình | ví dụ "V1 · M1 Tiền về", "V3 · Hợp đồng", "V7 · Lô T8-01" | mới |
| Ngày | ngày chứng từ (dd/mm/yyyy) | |
| Pháp nhân | chỉ hiện khi đang xem "Tất cả" | mới |
| Tóm tắt | diễn giải sao kê / "HĐ 0001234 · số HĐ" / "Nghiệm thu đợt 3 · HĐ thầu …" / "Lịch thu 5 đợt" — cắt một dòng | theo loại việc |
| Đối tác | mã – tên (tên thật) | |
| Số tiền | VND, dấu chấm, không lẻ; USD hiện kèm VND quy đổi + tỷ giá | giữ; thêm ngoại tệ |
| Đề xuất | V1: "Nợ 6427 + 1331 / Có 112111" · V2: "= 1 chứng từ 02BR…" · V3: "5 tham số, 2 chưa có trích dẫn" · V6: "STK → mã, 3/3" | theo loại việc |
| Trạng thái | Chờ duyệt · Đang hỏi (n ngày) · Chờ bổ sung (n ngày) · Đã duyệt · Đã xuất · Đã nạp · Đã đối chiếu · Bỏ qua · Đã có Junsky | mới: 4 trạng thái |
| Nút | [Đồng ý] [Sửa] [Hỏi] [Bỏ qua] — nút không áp dụng thì ẩn (ví dụ V7 không có Sửa) | thêm Hỏi |

## 4. Ngăn chi tiết (mở tại chỗ bằng Enter hoặc bấm dòng)

1. **Bảng đề xuất** — V1: bút toán (Nợ/Có · TK mã – tên · số tiền · đối tượng · dự án · khoản mục · TTCP), dòng tổng Nợ = Có, lệch báo đỏ. V3: bảng tham số (tên · giá trị · **trích dẫn nguyên văn** · trang). V2: hai cột chứng từ A ↔ B + số tiền đã khớp.
2. **"Vì sao"** — một câu + số đo (giữ V11): "40/40 chứng từ 2 năm → Nợ 34112"; "theo chứng từ Junsky 02BR…"; "LLM chọn phương án 2 trong 3 ứng viên — trích dẫn: …" (kết quả có LLM tối đa Vàng).
3. **Xem căn cứ** — chứng từ cũ được dùng (ngày, số, diễn giải, hạch toán) (giữ).
4. **Chuỗi chứng từ** (mới, §6) — hợp đồng → nghiệm thu → hóa đơn → tiền → tài sản; dòng đang xem được tô đậm.
5. **Phương án** (Vàng) 1/2/3 dạng thẻ, "Dùng phương án này" (giữ); với V5 hiện thêm **trả lời của phòng ban** và người trả lời.
6. **Ô thiếu** (Đỏ) viền đỏ + "TK hay gặp" / "Đối tượng gợi ý theo tên" (giữ).
7. **Ghi chú cho AI / gửi Claude** (giữ) + **nhật ký của dòng** (ai làm gì lúc nào).

## 5. Hành động và trạng thái

### 5.1 Bảng hành động

| Nút | Có ở loại việc | Điều kiện | Kết quả | Nhật ký |
|---|---|---|---|---|
| **Đồng ý** (A) | V1 V2 V3 V4 V6 | §5.3 | → Đã duyệt; Hoàn tác 6 giây; tự nhảy dòng chờ kế tiếp | có |
| **Sửa** (E) | V1 V3 V4 | — | ngăn phải; Nợ = Có kiểm ngay; "Ghi nhớ cho lần sau" bật sẵn → **Lưu và đồng ý** → Đã duyệt + tri thức chờ CFO (V6) | có, trước/sau |
| **Hỏi** (H) | V1 V2 V3 | có người phụ trách trong danh bạ nội bộ (đã quét QR bot) | máy soạn câu hỏi có phương án đánh số → gửi Zalo → trạng thái Đang hỏi (đếm ngày) | có, kèm nội dung hỏi |
| **Yêu cầu bổ sung** | V1 V2 | chọn loại chứng từ thiếu (RQ, nghiệm thu, hợp đồng, biên bản) | gửi phòng ban/Ban QLDA → Chờ bổ sung (đếm ngày tồn); chứng từ về → máy khớp lại, nâng mức | có |
| **Bỏ qua** (S) | V1 V2 V3 V4 | lý do không bắt buộc | → Bỏ qua; không xuất; không học | có |
| **Hoàn tác** | sau Đồng ý/Bỏ qua, chưa xuất | 6 giây hoặc nút "Duyệt lại" | → Chờ duyệt | có |
| **Đổi đích** (V1 hóa đơn mua) | đã duyệt, chưa xuất / đã xuất | — | chưa xuất: hoàn tác + bút toán mới; đã xuất: **bút toán điều chỉnh** (không sửa file cũ) | có, bắt buộc lý do |
| **Xác nhận / Gỡ liên kết** | V2 | — | ghi vào `lien_ket_chung_tu` (đã khớp / hủy, người duyệt) | có |
| **Đánh dấu đã nạp** | V7 | lô Đã xuất | → Đã nạp (ngày, người) | có |
| **Xử lý lệch** | V7 | sau đối chiếu ngược | tạo việc V1 "bút toán điều chỉnh" hoặc ghi "chấp nhận lệch" có lý do | có |
| **Đồng ý hàng loạt** | V1 Xanh | chỉ Xanh · Chờ duyệt · đủ §5.3 · đang lọc | hộp xác nhận: số dòng + tổng tiền VND (giữ V11) | có, một dòng/lô |
| **Xuất lô** | V1 Đã duyệt | chọn pháp nhân + kỳ; cảnh báo nếu còn dòng chờ | File soát Excel (luôn) · File nhập Junsky `CB_tmpEntry1/2` (mức 2 — khóa) → Đã xuất, mã lô + hash | có |

### 5.2 Máy trạng thái của một dòng (TL 35 §3A: "cùng bảng, phân biệt bằng trạng thái")
`Chờ duyệt` ⇄ `Đang hỏi` / `Chờ bổ sung` → `Đã duyệt` → `Đã xuất` → `Đã nạp` → `Đã đối chiếu`; nhánh: `Bỏ qua`; `Đã có Junsky` (không duyệt, không xuất). Quay lại chỉ được từ `Đã duyệt`/`Bỏ qua` về `Chờ duyệt` **khi chưa xuất**; sau `Đã xuất` mọi thay đổi là bút toán điều chỉnh. Chỉ dòng `Đã đối chiếu` (khớp) mới **đủ điều kiện học**.

### 5.3 Nút Đồng ý bấm được khi (mở rộng từ V11)
1. tổng Nợ = tổng Có > 0 (V1);
2. mọi dòng có **TK chi tiết** (không TK tổng hợp như 131, 331, 3387);
3. TK công nợ (131x, 331x, 141, 344, 1388x, 3388x — danh sách **chờ CFO xác nhận**, hiện là hằng `DEBT_ACCOUNTS`) có **mã đối tượng Junsky**; đối tượng mới chưa có mã → nút mờ, gợi ý "tạo ở Junsky trước" (TL 35 §3A);
4. pháp nhân của dòng = pháp nhân đang chọn; kỳ chưa khóa;
5. V3: tham số bắt buộc có trích dẫn; không trích dẫn → "Không quy định", không điền (TL 32 §1.4).
Thiếu điều kiện nào thì nút mờ, rê chuột hiện đúng điều đó; bấm vào thì mở chi tiết và chỉ ô thiếu.

### 5.4 Phím tắt (giữ V11, thêm H)
↑/↓ chuyển dòng · Enter mở/đóng · A Đồng ý · E Sửa · H Hỏi · S Bỏ qua · Esc đóng ngăn.

## 6. Chuỗi chứng từ (ngăn mới — nguyên tắc 3 TL 32)
- Vẽ ngang: **Hợp đồng** (tham số, phiên bản) → **Nghiệm thu / đợt** → **Hóa đơn** → **Tiền** (một hoặc nhiều lần chuyển) → **Tài sản / 241**; mỗi ô ghi số, ngày, số tiền; đường nối ghi trạng thái liên kết (đã khớp / chờ / hủy) và nguồn (máy / người).
- Hành động: bấm một ô → mở chứng từ đó; "Xác nhận" / "Gỡ" / "Thêm liên kết thủ công" (chọn chứng từ trong hộp tìm).
- Dùng cho: khớp nhiều lần chuyển = 1 chứng từ (TL 25 H8); hóa đơn nhà thầu chỉ Xanh khi khớp nghiệm thu (TL 29); đợt thu theo lịch hợp đồng (CRM kế toán, TL 32); bước 8 đối chiếu ngược và M8 điều kiện khấu trừ đọc từ cùng bảng.

## 7. Hỏi Zalo và Yêu cầu bổ sung
- **Hỏi:** máy **tự gửi cho các loại việc CFO đã định** (anh chốt 16/10) — danh sách ban đầu: tiền về lệch đợt / chưa xếp được cọc hay đợt (CFO-03) → hỏi phòng kinh doanh; hóa đơn mua thiếu RQ hoặc nghiệm thu → hỏi phòng mua hàng / Ban QLDA. Danh sách này là **cấu hình** CFO sửa được, không sửa mã; mọi loại khác chỉ gửi khi người bấm Hỏi. Dòng được máy tự hỏi hiện nhãn "máy đã hỏi … lúc …" và vẫn cho kế toán tự quyết trước khi có trả lời. Máy soạn: bối cảnh ngắn (không số tài khoản), câu hỏi, phương án đánh số, hạn trả lời. Người nhận trả lời "1/2/3" hoặc văn bản → cổng AI phân tích → dòng về Chờ duyệt kèm phương án đã chọn (Vàng, có ghi "theo trả lời của …").
- **Hạn:** mặc định 5 ngày làm việc (TL 32 §2.5 khuyến nghị); quá hạn → nhắc lại một lần → Vàng theo quy tắc CFO; **cuối tháng mọi dòng treo chuyển Vàng để đóng sổ**.
- **Yêu cầu bổ sung:** như Hỏi nhưng đích là chứng từ; khi chứng từ về (qua nguồn tự động hoặc thả file) máy tự khớp lại và nâng mức, dòng mất trạng thái Chờ bổ sung.
- Danh bạ nội bộ (ai phụ trách gì, đã quét QR chưa) ở màn 6.

## 8. Nhiều pháp nhân và phân quyền (TL 35 §8.3)
- Ô chọn pháp nhân ở thanh trên; danh sách, thanh tổng, xuất lô đều theo pháp nhân đang chọn. CFO có "Tất cả" (thêm cột pháp nhân).
- Kế toán pháp nhân A không thấy dòng của B; cùng một đối tác ở hai pháp nhân hiện đúng mã Junsky của từng pháp nhân (bảng ánh xạ).
- Giao dịch nội bộ (hai bên đều trong master file) hiện nhãn "nội bộ tập đoàn" trên dòng — chỉ nhận diện, không hợp nhất.

## 9. Các màn hình phụ (tóm tắt — chi tiết khi làm từng cái)
| Màn | Nội dung chính | Kế thừa |
|---|---|---|
| 2 Chứng từ & chuỗi liên kết | bảng mọi chứng từ đã bóc tách (loại, pháp nhân, ngày, đối tác, tiền, trạng thái, lô); mở chuỗi | mới |
| 3 Danh mục master | 9 danh mục chỉ đọc + phiên bản + nhật ký thay đổi; phòng kinh doanh xem hợp đồng & lịch thu; "tạo ở Junsky trước" cho mã mới | mới (một phần từ Nguồn dữ liệu) |
| 4 Tri thức | tra cứu "Khi … / Thì … / Vì sao" (giữ) + **hàng chờ CFO duyệt** (V6) với số đo tác động ("áp cho 12 dòng đang chờ") | V8 + mới |
| 5 Lô Junsky & đối chiếu | lịch sử lô (giữ "Lịch sử xuất file") + trạng thái nạp + kết quả đối chiếu 4 nhóm + nút xử lý lệch | mới |
| 6 Nguồn dữ liệu & cài đặt | giữ V11 (nạp lại, mốc học, chấm điểm, TK ngân hàng ↔ TK kế toán) + cổng AI (bật/tắt, loại chứng từ được gửi, nhật ký lượt gọi) + danh bạ Zalo + lịch nguồn tự động | V11 + mới |

## 10. Giữ nguyên từ V11/V12 — thêm mới
| Giữ nguyên | Thêm mới |
|---|---|
| Xanh/Vàng/Đỏ/Đã có Junsky; "vì sao" có số đo; phương án 1/2/3; ô thiếu + gợi ý; ngăn Sửa với ô tìm không dấu, Nợ = Có, ghi nhớ; Hoàn tác 6 giây; Đồng ý hàng loạt có hộp xác nhận; phím tắt; xuất file soát; mức 2 khóa; chế độ chấm điểm; ghi chú AI; nhiều lần chuyển = 1 chứng từ | 8 loại việc trong một danh sách; cột loại việc/chu trình/pháp nhân/trạng thái người; nút Hỏi, Yêu cầu bổ sung; ngăn Chuỗi chứng từ; trạng thái Đã xuất → Đã nạp → Đã đối chiếu; Đổi đích = bút toán điều chỉnh; ô chọn pháp nhân + phân quyền; nguồn tự động; hàng chờ CFO duyệt tri thức; màn Lô Junsky & đối chiếu; màn Danh mục master |

## 11. Trạng thái cần vẽ (đầu bài cho Claude Design v2 — sau khi chốt)
Danh sách đầy đủ nhiều loại việc · dòng V1 Vàng mở (phương án) · dòng V1 Đỏ mở (ô thiếu) · dòng V2 liên kết (9 lần chuyển = 1 hóa đơn) · dòng V3 tham số có trích dẫn · dòng Đang hỏi có trả lời về · ngăn Sửa · ngăn Hỏi Zalo (chọn người, phương án) · ngăn Chuỗi chứng từ · hộp Đồng ý hàng loạt · hộp Xuất lô (mức 2 khóa) · màn Lô Junsky có lệch · màn Tri thức hàng chờ CFO · thanh trên với ô pháp nhân "Tất cả" (CFO) · lỗi chặn.

## 12. Quy tắc hiển thị (giữ V11 + bổ sung)
- Tiếng Việt; ngày dd/mm/yyyy; VND dấu chấm không lẻ; ngoại tệ kèm VND quy đổi và tỷ giá; màu luôn kèm biểu tượng + chữ.
- Mỗi dòng phải trả lời được 3 câu trong 3 giây: *máy đề xuất gì — vì sao — tôi phải làm gì*.
- Không hiện số liệu của pháp nhân khác; không hiện bí danh.
- Việc quá hạn (Đang hỏi / Chờ bổ sung quá 5 ngày) nổi lên đầu danh sách và đếm ngày bằng chữ đỏ.
- Không dùng thuật ngữ kỹ thuật trên màn hình (không "LLM", "schema"); ghi "máy", "cổng AI", "tri thức".

## 13. Điểm cần anh chốt

**Đã chốt 16/10/2026 (chiều) — bảng chọn:**
1. **Một danh sách gộp 8 loại việc, lọc theo loại** (không tab riêng).
2. **Ai duyệt gì:** kế toán duyệt V1 V2 V4 V5 V7; **CFO_NTD duyệt V3 tham số hợp đồng** (kế toán công nợ kiểm trước, phòng kinh doanh chỉ xác nhận), **V6 tri thức** và danh mục nhạy cảm (đối tác mới, STK, phụ lục đổi lịch).
3. **Agent Zalo tự hỏi cho loại việc đã định** (cấu hình CFO duyệt; ban đầu: tiền về lệch đợt — CFO-03; hóa đơn thiếu RQ/nghiệm thu); loại khác chỉ khi người bấm Hỏi.
4. **Chọn một pháp nhân mỗi lúc; CFO có "Tất cả"** (thêm cột pháp nhân khi xem gộp).

**Trả lời sau:** danh sách TK công nợ bắt buộc có đối tượng (`DEBT_ACCOUNTS`) — CFO xác nhận; hạn trả lời Zalo mặc định (5 ngày?); có cho "Đồng ý hàng loạt" với V2 liên kết Xanh không; định dạng tên lô (pháp nhân – kỳ – STT).

## 14. Sau khi chốt
- **Tài liệu 38 — schema lớp dữ liệu** (bước kế tiếp theo tiêu chuẩn): từ cột §3 + hành động §5 + trạng thái §5.2 → bảng `viec_can_duyet` (một bản ghi cho mọi loại việc, trỏ tới chứng từ/tham số/liên kết/tri thức/lô), `chung_tu` + trạng thái, `lien_ket_chung_tu`, `nhat_ky`, 9 danh mục master (có `phap_nhan_boi_canh` từ TL 36), `lo_xuat`, `cau_hoi_zalo`.
- **Prompt Claude Design v2**: cập nhật `docs/thiet-ke/PROMPT-CLAUDE-DESIGN.md` theo §2–§12, dữ liệu giả, 15 trạng thái §11 → anh chạy Claude Design → bản bàn giao HTML → Codex/Claude dựng vào phần mềm **khi anh ra lệnh code**.
- Hàng đợi #28 (màn hình K5) — **đã chốt thiết kế 16/10**; #23/#24 (K2/K3) nhận thêm điều kiện "schema theo TL 38".
