# 31 · Tận dụng dự án hiện có cho các module kế toán & áp dụng tiêu chuẩn xây dựng phần mềm nội bộ

**Ngày lập:** 15/10/2026 · **Căn cứ:** `DANH-MUC-DU-AN.md` (15/10, bản nháp theo tài liệu, chưa đọc mã nguồn), `CACH-LAM-VIEC-CHUNG-DRAFT.md`, `TIEU-CHUAN-XAY-DUNG-PHAN-MEM-NOI-BO.md`, tài liệu 29 (kế hoạch 10 module). Mọi nhận định về dự án khác là **theo mô tả trong danh mục**, chưa kiểm chứng bằng cách mở mã.
**Bảo mật:** tài liệu nêu tên dự án nội bộ — không đưa ra ngoài.

---

## 0. Kết luận trước

- **7 dự án tận dụng được trực tiếp** cho 7/10 module; trong đó 3 dự án giải quyết gần trọn phần đầu vào khó nhất của tài liệu 29: **Review hồ sơ thanh toán xây dựng (#5) cho M4**, **Theo dõi khoản vay (#9) cho M9**, **Tải hóa đơn điện tử (#7) cho M2/M3/M8**. Nếu dùng, thứ tự triển khai sau M1–M3 thay đổi: M4 và M9 lên trước vì đầu vào đã có cấu trúc.
- **Nguyên tắc nối:** hệ thống kế toán **không xây lại** nghiệp vụ các dự án đó đang làm (QT02 tài liệu 01); chỉ **nhận kết quả** của chúng dưới dạng file có cấu trúc (CSV/Excel/XML) qua bước 1–2 của đường ống, đúng tinh thần "nạp CSV có kiểm soát" trong tiêu chuẩn nội bộ. Ba dự án chạy trên Google Sheets (#9, #10, #11) nối bằng xuất CSV định kỳ, không gọi API Sheets trong đợt này.
- **Đối chiếu với tiêu chuẩn:** dự án kế toán đã làm đúng các cổng *code theo giai đoạn, kiểm thử có số đo, lưu vết trong Project*; **đang thiếu 5 việc**: CLAUDE.md riêng của dự án, hàng đợi yêu cầu tập trung, chốt giao diện + schema **trước** khi code cho mỗi module mới, khuyến nghị model cho từng loại việc, review độc lập cố định cuối giai đoạn. Đề xuất bổ sung ngay ở mục 3, không cần chờ bản chung có hiệu lực.
- **Hai việc phải xử lý trước mọi thứ khác** (từ danh mục mục D): kiểm tra repo GitHub của dự án kế toán đã Private chưa (08/10 vẫn Public, tài liệu 24); file `API token.txt` ở gốc `D:\Claude` chuyển vào biến môi trường.

---

## 1. Bảng tận dụng: dự án hiện có → module kế toán

Mức: **A** = dùng ngay, chỉ viết bộ đọc file kết quả · **B** = dùng lại thành phần/mẫu, phải sửa · **C** = cùng nghiệp vụ nhưng chỉ tham khảo · **—** = không liên quan.

| # | Dự án (danh mục) | Nền tảng | Module hưởng lợi | Mức | Tận dụng cái gì | Cách nối | Rủi ro / phải kiểm |
|---|---|---|---|---|---|---|---|
| 5 | Review hồ sơ thanh toán khối lượng xây dựng | Python, web 8600, Local AI, quy trình P01–P18 | **M4** nghiệm thu & chi phí dự án; M2 hóa đơn nhà thầu | **A** | Kết quả review từng hồ sơ: giá trị đề nghị ↔ hợp đồng/BOQ/phụ lục, tạm ứng khấu trừ, giữ lại bảo hành, kết luận đạt/không | Review xuất một dòng kết quả có cấu trúc (mã hợp đồng, đợt, giá trị chấp nhận VND, tạm ứng, bảo hành, trạng thái) → M4 đọc như một "chứng từ nghiệm thu đã kiểm" → sinh bút toán 241/154 | Chưa rõ review xuất file gì; cần thống nhất khóa chung **mã hợp đồng** giữa hai hệ thống. Không làm lại việc khớp BOQ trong M4 |
| 6 | Trích tham số hợp đồng bằng AI local | Python thư viện chuẩn, Ollama (RunPod) | **M4** danh mục hợp đồng thầu; **M9** hợp đồng vay; **M3** hợp đồng BĐS (lịch thu) | **B** | Bộ trích 36+ tham số có trích dẫn nguyên văn; đáp án mẫu để chấm | Dùng để **điền danh mục hợp đồng (A1)** từ PDF hợp đồng: giá trị, tạm ứng %, bảo hành %, dự án; mở rộng bộ tham số cho hợp đồng vay và hợp đồng mua bán BĐS | Kết quả AI chỉ là đề xuất, người duyệt trước khi vào danh mục (đúng quy tắc "LLM đề xuất, Python kiểm duyệt"); phụ thuộc RunPod |
| 7 | Tải hóa đơn điện tử hàng loạt | Node + Playwright, localhost:3456 | **M2, M3** (XML), **M8** (bảng kê cổng thuế) | **A** | Đã là nguồn `paths.invoice` của V12; tải được cả **bảng kê** từ cổng thuế (kho đã nạp bảng kê mua/bán T8) | Giữ nguyên; M8 đọc bảng kê đã tải để đối chiếu XML ↔ cổng thuế ↔ bút toán | Câu D4 trong khảo sát (tài liệu 30) gần như đã có đáp án — chỉ cần xác nhận kỳ tải |
| 8 | Backup dữ liệu Base Request | Python, Base API, Excel index + đính kèm | **M2** (RQ ↔ hóa đơn), M1 (STK thụ hưởng), M4 | **A** | Bộ đọc Base API + file index Excel; tài liệu 10 đã chốt bước đọc Base, kho đã nạp 168 bản ghi Base | Lịch chạy (V3) gọi backup theo ngày → M2 đọc index: Dự án, Chi phí (Dự án/Vận hành), nội dung, STK, người đề nghị | Câu A1 khảo sát đã có đáp án một phần (Base có API). Kiểm tra token Base nằm trong `.env`, không trong mã |
| 1 | Phần mềm kiểm tra đề xuất Base | Python 3.13, hồ sơ loại chi phí YAML, HTML localhost | **M2** nhóm G → TK; **M0** bộ quy tắc | **B** | **Hồ sơ loại chi phí YAML** = cùng khái niệm "33 nhóm G" của phễu (tài liệu 23); cách trình bày bằng chứng cho CFO duyệt | Dùng **một danh mục loại chi phí chung** cho cả hai phần mềm (anh đang chờ đặt tên ở dự án #1) → bảng ánh xạ nhóm G × (Dự án/Vận hành) → TK, khoản mục, TTCP chỉ lập một lần | Hai dự án đang định nghĩa loại chi phí độc lập → nguy cơ lệch; cần chốt ai là chủ danh mục |
| 9 | Phần mềm theo dõi khoản vay | Google Sheets + Apps Script | **M9** vốn vay | **A** | Danh mục hợp đồng vay, LC, nhận nợ, lịch trả, dư nợ tính on-the-fly | Xuất CSV định kỳ (chuẩn nội bộ: "xuất Excel có công thức sống") → M9 khớp sao kê ↔ lịch trả nợ; câu F1–F2 khảo sát đã có đáp án | Mã hợp đồng vay trong Sheet phải trùng mã trong danh mục A1; tỷ lệ vốn hóa theo dự án chưa có trong Sheet |
| 10 | Phần mềm quản lý kho (9 sheet) | Google Sheets + Apps Script, PWA | **M5** kho vận hành KCN | **A/B** | Thiết kế 9 sheet (tài liệu 01 đã ghi "dùng lại") | Xuất CSV phiếu nhập/xuất → M5 sinh bút toán; không xây kho mới | Danh mục ghi "chưa rõ mức triển khai" → câu G1 khảo sát vẫn cần |
| 11 | Phí / doanh thu xử lý nước thải | Sheets + Apps Script, OCR | **M3** doanh thu dịch vụ KCN | **B** | SELLING_1/2 = cơ sở lập hóa đơn phí dịch vụ cho khách thuê KCN | Xuất CSV bảng tính tiền theo khách → M3 khớp với hóa đơn bán ra và 131 theo khách | Stage A "chờ triển khai và test song song" — chưa phải nguồn ổn định |
| 14/15 | Bot trợ lý Telegram (troly, my_task_bot) | Python, Claude Haiku, SQLite, Sheets | **M0** agent Zalo | **B** | Khung bot: nhận tin tiếng Việt → phân tích → ghi logbook → nhắc việc | Giữ lõi (phân tích câu trả lời, nhắc hạn, nhật ký), thay lớp Telegram bằng Zalo Bot webhook | Bot dùng Claude Haiku qua API ngoài → trái quy ước "AI cục bộ, không gọi API ngoài" của dự án kế toán; agent Zalo phải phân tích bằng quy tắc + LLM cục bộ, chỉ gửi dữ liệu tối thiểu |
| 4 | Phần mềm HR (Frappe HR, WSL2) | Frappe, WSL2 | **M7** lương; M2 tạm ứng/công tác phí | **C → A sau** | Tạm ứng, quyết toán công tác phí (M3, M4 của HR); chấm công | Khi HR xuất được bảng lương/bảng tạm ứng → M7, M2 đọc CSV. Hiện HR ở giai đoạn 1, chưa có lương | Câu E1 khảo sát vẫn cần: lương đang tính ở đâu hôm nay |
| 2 | Phần mềm Request (thay Base) | Node/TS, 130 người dùng, go-live 31/12/2026 | **M2**, app lệnh thanh toán | **C** | Sẽ thay Base làm nguồn RQ → M2 phải đọc được **cả Base lẫn Request** cùng cấu trúc trường | Thiết kế bộ đọc RQ của M2 theo **một schema trung gian** (Dự án, Chi phí, nội dung, STK, nhóm G, hóa đơn) để đổi nguồn không đổi phễu; ý tưởng app lệnh thanh toán (tài liệu 23) nên là một chức năng của Request | Không nối ngay; chỉ chốt schema trung gian |
| 12 | OCR module 2.1 | FastAPI 8018, Tesseract + VietOCR, ABBYY | Bước 2 tầng OCR (biên bản PDF scan) | **C** | Sẵn sàng khi cần; tài liệu 01 xếp OCR sau cùng | Không dùng trong đợt này; M4 đã xác nhận có Excel kèm PDF | — |
| 13 | Local Mask | FastAPI 8017/8019 | Quy trình (không phải module) | **B** | Che tên/mã trước khi gửi prompt cho Codex/Claude Design | Mọi prompt có dữ liệu mẫu đi qua Mask (quy ước bảo mật mục 6 bản chung) | — |
| 21 / 6 | Local AI POC, Ollama RunPod | — | **M0** tầng LLM cục bộ (phễu bước 3) | **B** | Mô hình và cách gọi đã thử ở #6 | Tầng 4 phễu chọn 1 trong 2–5 phương án; chỉ sau khi có số đo | Tài liệu 23 vẫn chờ anh cho biết mô hình đã cài |
| C | Check Kế toán / Check VAT input-output vs invoice (Excel) | Excel | **M8** | **C** | Phương pháp đối chiếu 1331/3331 ↔ hóa đơn đang làm tay | Viết thành quy tắc đối chiếu của M8 | Chưa có tài liệu phương pháp — hỏi kế toán thuế |
| 20 | Trợ lý pháp chế | Markdown | M3, M8 (NĐ 70/2025, luật GTGT) | **C** | Quy trình kiểm tra hiệu lực văn bản | Dùng khi chốt quy tắc pháp lý trong bộ quy tắc | — |
| 16, 17, 18, 19 | FusionSolar, học tập cho Sò, Thư ký ảo | — | — | **—** | Thư ký ảo: chỉ dùng quy trình gate khi làm tài liệu | — | — |

### Hệ quả cho thứ tự triển khai (đề xuất, chờ anh chốt)
- **M4** (nhờ #5 + #6) và **M9** (nhờ #9) có đầu vào có cấu trúc sẵn → có thể lên ngay sau M1–M3, trước khi khảo sát xong các phòng khác.
- **M8** gần như chỉ còn viết bảng kê và đối chiếu vì #7 đã tải đủ.
- **M5, M7** vẫn chờ khảo sát (G1, E1).
- Khảo sát (tài liệu 30) rút gọn: bỏ/giảm câu A1 (Base có API), D4 (cổng thuế), F1–F2 (Sheet vay); thêm câu cho chủ dự án #5 (review xuất gì) và #1 (danh mục loại chi phí).

---

## 2. Đối chiếu cách làm của dự án kế toán với hai bộ quy tắc

Tiêu chuẩn nội bộ sinh ra từ app Apps Script; dự án kế toán đã **chốt nền tảng khác** (Python chạy máy cục bộ, giao diện HTML cục bộ, cầu Excel sang Junsky — tài liệu 02). Nền tảng không đổi; áp dụng phần **quy trình** và **nguyên tắc dữ liệu**.

| Cổng (bản chung mục 3 / tiêu chuẩn mục 5) | Dự án kế toán đang làm | Đánh giá | Việc bổ sung |
|---|---|---|---|
| 1. Chốt yêu cầu + nền tảng | Tài liệu 01, 02 (đợt 1); tài liệu 29 cho 10 module | Đạt cho M1–M3; M4–M10 mới ở mức kế hoạch | Khảo sát đầu vào (30) chính là cổng 1 của M4–M10 |
| 2. Phản biện & tinh giản dữ liệu | Có trong 08 (sheet chung 41 cột), 23 (phễu) | Chưa làm theo từng trường cho module mới | Mỗi module mới: bảng trường "cần / gộp / bỏ" trước khi vẽ màn hình |
| 3. Chốt giao diện → chốt schema → khóa | M1: Claude Design → V10; schema kho v19 | Đạt cho M1; M2–M3 giao diện V11 mới có prompt; schema module mới chưa | **Không code module mới khi chưa có mô tả màn hình + schema đã duyệt** |
| 4. Khuyến nghị model coding | Chưa ghi ở đâu | Thiếu | Mục 3.3 dưới |
| 5. Hàng đợi yêu cầu, chỉ code khi có lệnh | "Việc để sau" rải trong tài liệu 24, 27 | Thiếu hàng đợi tập trung | File `HANG-DOI-YEU-CAU.md` trong thư mục phần mềm, một dòng một yêu cầu (ngày, ai, nội dung, module, trạng thái) |
| 6. Code theo giai đoạn nhỏ, test trước/cùng lúc | V-số, 258/258 test (V12) | Đạt | Giữ |
| 7. Kiểm tra trước bàn giao, số đo trước/sau | Chấm điểm T7/T8 so Sổ NKC, hash file | Đạt | Giữ; thêm chạy headless cho giao diện (tiêu chuẩn mục 4) |
| 8. Review độc lập | V10 có một lượt | Chưa cố định | Cuối mỗi V: một agent chưa thấy quá trình soát theo đặc tả, ghi vào `docs/BAO-CAO-Vxx.md` |
| 9. Lưu vết: CHANGELOG, nhật ký quyết định, registry | Project `claude/NN-*.md`, `docs/BAO-CAO-Vxx.md`; git `accounting_assisstance` | Đạt một phần; không có CHANGELOG có số đo; **repo cần kiểm Private** | Thêm `CHANGELOG.md` (mỗi V một dòng kèm số đo); tri thức CFO đã là nhật ký quyết định nghiệp vụ |
| 10. Cải tiến → CLAUDE.md / skill | Tài liệu 00 trong Project đóng vai CLAUDE.md | Thiếu CLAUDE.md **trong thư mục dự án** | Mục 3.1 dưới |
| Bảo mật (bản chung mục 6) | Token `.env`, không dữ liệu thật trong fixture, prompt chỉ mô tả cấu trúc | Đạt | Kiểm `API token.txt` gốc `D:\Claude` |
| Dùng lại thành phần trước khi viết mới (bản chung mục 7) | Chưa có registry chung | Thiếu | Bảng mục 1 tài liệu này làm registry tạm; mỗi module mới ghi "dùng lại từ #…" |
| Nguyên tắc dữ liệu (tiêu chuẩn mục 4) | Không bịa, có nguồn, đơn vị VND | Đạt | Giữ |

### Điểm tiêu chuẩn Apps Script **không áp dụng** nguyên văn
- "Một file HTML qua HtmlService", "clasp deploy", "backup bằng time-trigger Drive": thay bằng giao diện HTML cục bộ + sao lưu `var\sao-luu-truoc-Vxx` (đang làm) + git.
- "Google Sheet = CSDL": dự án dùng SQLite (`kho.sqlite`); nguyên tắc **khóa cấu trúc** vẫn áp dụng dưới dạng migration schema có số phiên bản (đang là v19).
- Phân quyền 3 mức + PIN: chưa cần khi một người dùng; ghi vào hàng đợi cho lúc nhiều kế toán dùng.

---

## 3. Đề xuất áp dụng ngay (chưa làm, chờ anh chốt)

### 3.1 CLAUDE.md cho thư mục `D:\Claude\Phan mem ho tro ke toan` (theo mẫu mục 10 bản chung)
```markdown
# CLAUDE.md — Phần mềm hỗ trợ kế toán & Kho tri thức

Đọc trước: `D:\Claude\CACH-LAM-VIEC-CHUNG.md` (khi có hiệu lực), rồi file này; quy ước chi tiết ở Project claude/00.

## Mục tiêu và phạm vi
- Biến chứng từ (sao kê, hóa đơn XML, RQ Base, nghiệm thu, bảng lương…) thành bút toán đề xuất, người duyệt, xuất file Excel nạp Junsky. KHÔNG thay Junsky, KHÔNG hạch toán hộ phòng ban khác, KHÔNG làm giá thành SX và hợp nhất.

## Trạng thái hiện tại
- Kho tri thức V12 (0.5.0) 15/10/2026; go-live sao kê TK 112111; mức 2 (file nhập Junsky) còn khóa.

## Nền tảng và lệnh
- Python ≥ 3.11, SQLite, giao diện HTML cục bộ 127.0.0.1:8766/8767; mở bằng `MỞ PHẦN MỀM.cmd`; test: (khối lệnh trong README kho tri thức).
- Không gọi API AI ngoài; LLM cục bộ chỉ ở tầng 4. Thư viện ngoài: nêu lý do, hỏi một lần.

## Quy tắc riêng
- Dữ liệu thật chỉ trong `var\` (gitignore); fixture dùng dữ liệu DEMO. Học đến 30/06/2026 khi chấm điểm.
- Máy chỉ đề xuất; tự duyệt chỉ với 4 loại đã chốt (phí NH, lãi tiền gửi, lương, định kỳ) khi mức 2 mở.
- Thà bỏ sót còn hơn nhập sai; không sửa tay file nhập Junsky.

## Tài liệu tham chiếu
- Project claude/01 (bản đồ module), 08 (file Junsky), 23 (phễu), 29 (kế hoạch 10 module), 31 (tận dụng dự án).
- Hàng đợi: `HANG-DOI-YEU-CAU.md` · Nhật ký: `CHANGELOG.md`, `docs/BAO-CAO-Vxx.md`.

## Điểm đang chờ CFO chốt
- Hai câu bước 2 phễu (tài liệu 23); 3 câu Junsky (08); danh mục loại chi phí chung với dự án kiểm tra đề xuất.
```

### 3.2 Hàng đợi yêu cầu — nội dung ban đầu (gom từ tài liệu 24, 27, 29)
| Ngày | Yêu cầu | Module | Trạng thái |
|---|---|---|---|
| 15/10 | Nối Base RQ cho hóa đơn mua lẻ (nhân viên mua hộ) | M2 | Chờ lệnh code |
| 15/10 | Nối Base cho "chi phí chung" | M2 | Chờ lệnh code |
| 15/10 | Sửa danh bạ đối tác (một STK gắn sai mã 331) | M0 | Chờ lệnh code |
| 15/10 | 6 dòng sao kê Xanh ghi dự án KCN-DVI0 trong khi Junsky trống | M1 | Chờ phân tích |
| 15/10 | Agent Zalo Bot (thử nhắn trước, webhook) | M0 | Chờ thử nghiệm |
| 15/10 | Bộ đọc kết quả review hồ sơ xây dựng (#5) | M4 | Chờ chốt schema |
| 15/10 | Bộ đọc CSV Sheet khoản vay (#9) | M9 | Chờ chốt schema |
| 15/10 | Màn hình Hóa đơn XML (V11 Design) | M2–M3 | Prompt đã có |
| 15/10 | Phân quyền nhiều kế toán | M0 | Để sau |

### 3.3 Khuyến nghị model cho từng loại việc (cổng 4)
| Loại việc | Khuyến nghị | Lý do |
|---|---|---|
| Thiết kế phễu, quy tắc định khoản, schema, review độc lập, chấm điểm sai lệch nghiệp vụ | Mô hình mạnh nhất đang có (lớp Opus / Fable) | Sai một quy tắc là sai hàng trăm bút toán |
| Giao diện HTML, bộ đọc file (CSV/XML/Excel), adapter Zalo Bot, script xuất Excel | Lớp Sonnet, hoặc Codex tự chạy thử (quy ước hiện tại) | Việc có đặc tả rõ, test tự động bắt được lỗi |
| Script lặp nhỏ, đổi tên cột, chuyển đổi định dạng | Lớp Haiku | Rẻ, đủ dùng |
| Phân tích câu trả lời Zalo, chọn 1 trong 2–5 phương án | LLM cục bộ (tầng 4) | Dữ liệu nội bộ không ra ngoài |

### 3.4 Sửa bảng khảo sát (tài liệu 30) theo mục 1
- Bỏ A1 (thay bằng: "xác nhận token Base còn hiệu lực, lịch chạy backup"), D4, F1–F2.
- Thêm phần H · Chủ dự án Review hồ sơ xây dựng: review xuất kết quả dạng gì, có mã hợp đồng không, mỗi tháng bao nhiêu hồ sơ.
- Thêm vào phần A: danh mục loại chi phí của dự án kiểm tra đề xuất — ai là chủ, đã đặt tên chưa.

---

## 4. Quyết định anh Dũng chốt 15/10/2026
1. **M4 nhận kết quả review từ dự án #5**; không tự khớp BOQ trong phần mềm kế toán; thống nhất mã hợp đồng chung.
2. **M9 đọc thẳng Google Sheets API** của Theo dõi khoản vay (#9) — không xuất CSV tay. Điều kiện: thông tin xác thực Google (service account, quyền chỉ đọc) đặt trong `.env`, mở mạng ngoài chỉ tới Google API; Sheet là nguồn duy nhất về hợp đồng vay; mã hợp đồng vay trùng danh mục A1.
3. **Agent Zalo dùng lại lõi bot Telegram (#14)**, thay lớp Telegram bằng Zalo Bot, bỏ gọi API AI ngoài; phân tích trả lời bằng quy tắc + LLM cục bộ.
4. **Tạo ngay ba file** theo mục 3: `CLAUDE.md` (thư mục cha `Phan mem ho tro ke toan`, áp dụng cho cả thư mục con), `CHANGELOG.md` và `HANG-DOI-YEU-CAU.md` (trong `Phần mềm kho tri thức`, để git theo dõi). Đã ghi 15/10/2026; hàng đợi khởi đầu 17 mục.

## 5. Việc tiếp theo
- Tài liệu 29: thứ tự đề xuất sau M1–M3 là **M4 → M9 → M8**, phần còn lại chờ khảo sát. Tài liệu 30: rút gọn theo mục 3.4.
- Lập mô tả màn hình + schema cho M4 và M9 (cổng 3) → ghi hàng đợi → chờ anh ra lệnh code.
- Anh đẩy git từ máy chính để `CHANGELOG.md`, `HANG-DOI-YEU-CAU.md` vào repo (CLAUDE.md ở thư mục cha, ngoài repo).
