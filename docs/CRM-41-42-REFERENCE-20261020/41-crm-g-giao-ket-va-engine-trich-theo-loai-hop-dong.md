# 41 · CRM-G Giao kết: báo giá → soạn hợp đồng từ mẫu → ký kết, và engine trích tham số theo loại hợp đồng

**Ngày lập:** 20/10/2026 · **Trạng thái:** yêu cầu mở rộng CHO_ANH_CHOT, chưa coding · **Nguồn:** anh Dũng (20/10, 16:02–16:50) trả lời 10 điểm; bản `CRM-CHUC-NANG-VA-THIET-KE.md` (20/10); đọc mã nguồn `D:\Claude\Ho tro review ho so xay dung\review_xaydung` (README.md, API.md, trich_xuat/danh_muc.py, quy_trinh.py, logic.py, cau_hinh.py).
**Liên quan:** TL 32 (CRM kế toán từ #6), TL 35 §3A (master file), TL 37 (màn hình duyệt chung), TL 38 (schema, mã hóa CCCD/STK), TL 39 §8 (V16 CRM hợp đồng), TL 40 (CRM cho phòng bán hàng qua web trung tâm).

---

## 0. Kết luận trước

- **CRM-G là phần mở rộng phạm vi** so với mục 1 file CRM ("một master từ nguồn ký"): hợp đồng có thể **sinh ra từ hệ thống** (mẫu + tham số) trước khi ký. Không phải sales pipeline (không lead/cơ hội/campaign/môi giới) — chỉ là công cụ **giao kết**: báo giá lịch thanh toán, soạn hợp đồng từ mẫu, ghi nhận bản ký.
- **Hai luồng vào, một master ra.** Luồng A (mới): tham số → sinh văn bản → ký → kế toán kiểm → hiệu lực. Luồng B (đã chốt ở TL 32): bản ký → #6 trích → kiểm → duyệt → hiệu lực. Cả hai đổ vào **cùng bảng master hợp đồng / phiên bản / tham số / nghĩa vụ** (mục 6 file CRM), phân biệt bằng trường `nguon_tham_so`. "Chuyển cơ sở dữ liệu sang hợp đồng ký" là **đổi trạng thái của cùng một bản ghi**, không chép sang kho khác.
- **Engine #6 không viết lại.** Mã hiện có đã nhận danh mục làm đầu vào (`TrichXuat(params, …)`, `load_params(path)`); việc cần làm là tách 3 chỗ gắn cứng với hợp đồng xây dựng và thêm danh mục KCN, nhà ở (mục 4).
- **Anh đã chốt (20/10):** mẫu có phiên bản và ánh xạ trường → ô; tỷ giá nhân viên nhập tay; lịch 4 cột *Lần | Giá trị | Mốc thời gian | Ghi chú*; bán hàng tạo hợp đồng và bấm Ký kết kèm PDF; hợp đồng từ mẫu **kế toán kiểm là đủ** (CFO duyệt ở cấp **phiên bản mẫu**); bản ký đối chiếu bằng **kiểm mẫu ngẫu nhiên, tỷ lệ tự điều chỉnh**; ~10 căn nhà ở/tháng cao điểm.
- **Thí điểm:** KCN trên PLHN (chỉ 4 loại hình KCN — TL 36); nhà ở cấu hình cho pháp nhân khác khi có mẫu.

---

## 1. Vòng đời hợp đồng trong CRM-G

| Trạng thái | Ai đưa vào | Điều kiện vào | Dữ liệu bị khóa | Ghi chú |
|---|---|---|---|---|
| `BAO_GIA` | Bán hàng | Chọn dự án/lô/căn, khách (có thể chưa có mã Junsky) | — | Không ràng buộc; không tạo công nợ; không nối tiền. In cho khách có dòng tham chiếu tỷ giá |
| `SOAN_THAO` | Bán hàng | Chọn **phiên bản mẫu đang hiệu lực**; điền trường; lịch 4 cột | — | Tham số được ghi **ngay khi soạn**, trạng thái "dự thảo", `nguon_tham_so = MAU v<n>` |
| `CHO_KY` | Bán hàng | Bấm "Xuất hợp đồng" → DOCX/PDF | Khóa mềm | Sửa gì thì sinh lại file và tăng `revision_du_thao`; hệ thống giữ mọi bản đã xuất + hash |
| `DA_KY` | Bán hàng | Bấm **Ký kết**: bắt buộc PDF bản ký + ngày ký + khai "có sửa so với bản in: Có/Không" | **Khóa cứng** tham số | Hash PDF; đưa vào hàng kiểm mẫu ngẫu nhiên (mục 3) |
| `KE_TOAN_KIEM` | Kế toán công nợ | Tự động sau `DA_KY` | — | Kiểm: đối tượng ↔ mã Junsky, pháp nhân, dự án/lô/căn, tham số, kết quả đối chiếu (nếu được chọn). Thiếu → **trả lại** kèm lý do |
| `HIEU_LUC` | Hệ thống | Kế toán bấm "Hiệu lực" | — | Sinh nghĩa vụ từ lịch; sang CRM kế toán hiện có (F6 lịch, F7 nối tiền M1 · Tiền về / tiền đi). M3 · Hóa đơn bán ra & doanh thu BĐS đọc từ đây |
| `TU_CHOI` / `HUY` | Kế toán / Bán hàng | Có lý do | — | Giữ lịch sử; báo giá hủy không xóa |

Quy tắc đi kèm:
- Hợp đồng **không sinh từ mẫu** (ký ngoài hệ thống, hợp đồng cũ) đi luồng B TL 32: #6 trích → kế toán kiểm → **CFO duyệt** theo mục 1 file CRM. **[CẦN ANH XÁC NHẬN]** giữ CFO duyệt cho luồng B hay cũng hạ xuống kế toán kiểm.
- Phụ lục của hợp đồng sinh từ mẫu: soạn từ **mẫu phụ lục** cùng cơ chế → phiên bản pháp lý mới (đúng F5); phần đã thu giữ nguyên liên kết.
- Khách mới nhập CCCD/ĐKDN ở `SOAN_THAO` là **đối tượng dự thảo**; Junsky cấp mã (hệ thống không tự sinh mã — TL 35); kế toán gán mã ở bước kiểm. CCCD/STK mã hóa cột (TL 38), màn hình chung chỉ hiện 4 số cuối.

---

## 2. Yêu cầu theo mã (định dạng mục 11 file CRM)

| Mã | Việc cần làm | Người dùng | Đầu vào | Thao tác / màn hình | Kết quả | Ngoại lệ | Tiêu chí đạt | Ưu tiên |
|---|---|---|---|---|---|---|---|---|
| **CRM-G1** Mẫu hợp đồng có phiên bản | Quản lý mẫu và ánh xạ trường → ô | Pháp chế/bán hàng tải; kế toán kiểm; **CFO duyệt** | File DOCX mẫu có chỗ đánh dấu (placeholder) | Màn "Mẫu hợp đồng": tải mẫu → hệ thống liệt kê placeholder tìm thấy → bảng ánh xạ *trường dữ liệu \| ô trong mẫu \| bắt buộc \| kiểu \| định dạng hiển thị* → kế toán kiểm → CFO duyệt → "Hiệu lực từ ngày" | Phiên bản mẫu v<n> theo loại HĐ × pháp nhân; bản cũ giữ để mở lại HĐ cũ | Placeholder không ánh xạ → chặn duyệt; trường bắt buộc thiếu trong mẫu → cảnh báo | Tải mẫu có 1 placeholder lạ → không duyệt được, báo đúng tên ô; HĐ đang soạn giữ v cũ sau khi v mới hiệu lực | Làm trước |
| **CRM-G2** Báo giá / lịch thanh toán dự kiến | Thay Excel chào khách | Bán hàng | Dự án/lô/căn, giá, tiền tệ, tỷ giá (nhập tay), tiến độ "theo dự án" hoặc "theo khách" | Bảng 4 cột **Lần \| Giá trị \| Mốc thời gian \| Ghi chú**; nhập % hoặc số tiền → cột kia tự tính; mốc = ngày hoặc sự kiện (ký / xây xong tầng n / bàn giao / sổ); KCN thêm cột USD và VND quy đổi; nút "In cho khách" | Báo giá có số, ngày, người lập; file in có dòng "Tỷ giá tham chiếu … ngày … do … nhập; giá trị thanh toán theo Điều … của hợp đồng" | Tổng % ≠ 100% → chặn in; mốc trống → cho phép nhưng cảnh báo | Lịch báo giá chuyển nguyên sang G3 không nhập lại; đổi tỷ giá → VND tính lại, USD giữ | Làm trước |
| **CRM-G3** Soạn hợp đồng từ mẫu | Sinh văn bản + ghi tham số cùng lúc | Bán hàng | Phiên bản mẫu hiệu lực; khách (CCCD/ĐKDN, địa chỉ, người đại diện, STK); lịch từ G2 hoặc nhập mới | Form theo ánh xạ của mẫu; xem trước; "Xuất hợp đồng" → DOCX + PDF | Bản ghi master trạng thái `SOAN_THAO`/`CHO_KY`; tham số đã ghi, `nguon = MAU v<n>`; file xuất + hash | Trường bắt buộc trống → không xuất; khách chưa có mã Junsky → đối tượng dự thảo | Mở lại HĐ thấy đúng mẫu v đã dùng; sửa 1 trường → file mới, revision +1, file cũ còn | Làm trước |
| **CRM-G4** Ký kết với bằng chứng | Chuyển sang hợp đồng ký | Bán hàng | PDF bản ký (bắt buộc), ngày ký, khai "có sửa so với bản in" | Nút "Ký kết" chỉ hiện ở `CHO_KY`; không có PDF → không bấm được | `DA_KY`; tham số khóa cứng; hash PDF; vào hàng kiểm mẫu | Tải lại cùng PDF → không tạo bản mới (idempotent); tải PDF khác sau khi đã ký → phải qua "Thay bằng chứng" có lý do | A6-kiểu: gỡ/retry không trùng; không có PDF không thể sang `DA_KY` | Làm trước |
| **CRM-G5** Kiểm mẫu ngẫu nhiên bản ký | Phát hiện bản ký khác bản sinh | Hệ thống + kế toán | HĐ `DA_KY`, tham số đã sinh, PDF bản ký | Chọn theo tỷ lệ (mục 3) → OCR nếu scan → #6 chế độ **đối chiếu** → bảng lệch theo mức quan trọng → kế toán xử lý | Kết quả "Khớp / Lệch mức n" lưu vào HĐ; cập nhật tỷ lệ của nhóm | Khai "có sửa" → **luôn** chạy, không chờ chọn; OCR lỗi → báo "chưa đối chiếu được", không coi là khớp | 20 HĐ khớp liên tiếp → tỷ lệ giảm đúng một bậc; 2 lệch mức ≥2 trong cửa sổ → tăng tới 100% | Làm trước (bản đơn giản) |
| **CRM-G6** Kế toán kiểm → hiệu lực | Thay bước CFO duyệt cho HĐ từ mẫu | Kế toán công nợ | HĐ `DA_KY` | Một dòng trong màn duyệt chung K5 (TL 37): xem tham số, so lịch với bộ chuẩn dự án, gán mã Junsky, xem kết quả G5 → "Hiệu lực" hoặc "Trả lại" | `HIEU_LUC` → nghĩa vụ sinh → F6/F7 | Lệch bộ chuẩn dự án → vẫn cho hiệu lực nhưng ghi nhật ký "lệch chuẩn" và hiện ở "Việc cần xử lý" của CFO | Sau hiệu lực, lịch nghĩa vụ đúng số dòng/số tiền/tiền tệ với bảng 4 cột đã ký | Làm trước |
| **CRM-G7** Bộ tiến độ chuẩn theo dự án | Nguồn cho "theo dự án" ở G2 | Kế toán lập; CFO duyệt | Bảng 4 cột chuẩn mỗi dự án/giai đoạn | Màn "Bộ chuẩn dự án" | So lệch tự động ở G6 | — | HĐ khớp chuẩn không sinh cảnh báo | Làm sau |
| **CRM-G8** Báo cáo giao kết | Theo dõi vòng đời | CFO, kế toán | Master | Bảng số đếm theo trạng thái × dự án × pháp nhân; HĐ lệch chuẩn; tỷ lệ kiểm mẫu hiện hành | Thêm sheet vào workbook soát F8 | — | Khớp số đếm với danh sách | Làm sau |

---

## 3. Kiểm mẫu ngẫu nhiên tự điều chỉnh (anh chốt 20/10)

- **Nhóm điều chỉnh:** theo *loại hợp đồng × phiên bản mẫu*; mẫu mới bắt đầu ở tỷ lệ cao.
- **Tham số mặc định — [CẦN ANH XÁC NHẬN]:** khởi điểm **50%** cho mẫu mới; biên **10%–100%**; cửa sổ **20 HĐ gần nhất** của nhóm; bậc tăng/giảm **20 điểm %**.
  - "Lệch" = ít nhất một tham số **mức quan trọng ≥ 2** khác giữa bản ký và bản sinh (thang 0–3 đã có trong danh mục #6).
  - **0 lệch / 20 HĐ** → giảm một bậc (không dưới 10%). **≥ 2 lệch / 20 HĐ** → lên 100% cho đến khi 20 HĐ kế tiếp sạch.
  - Khai "có sửa so với bản in" → luôn đối chiếu, không tính vào mẫu ngẫu nhiên.
- **Không kết luận "khớp"** khi OCR/trích lỗi; HĐ đó đợi kế toán xem tay.
- Tái dùng: #6 đã có cơ chế lấy mẫu theo tỷ lệ (`cloud.ty_le`, ô mức 2–3) và chế độ so với đáp án (`DAP_AN_*.tsv`) → chế độ đối chiếu là biến thể: "đáp án" = tham số đã sinh.

---

## 4. Thay đổi engine #6 (dự án `review_xaydung`), không đụng nghiệp vụ xây dựng

| Mã | Thay đổi | Căn cứ trong mã hiện có | Ràng buộc |
|---|---|---|---|
| **E1** Danh mục theo loại | `DANH_MUC_THAM_SO_<loai>.xlsx` cùng 10 cột; `POST /api/trich_xuat/{luot}/chay` nhận `loai_hop_dong`; `cau_hinh.DANH_MUC_THAM_SO` thành hàm theo loại | `danh_muc.load_params(path)` đã nhận đường dẫn; `quy_trinh.TrichXuat(params, …)` nhận params | Loại `XD` giữ file hiện tại; `tests/test_trich_xuat.py` phải qua nguyên trạng |
| **E2** Quy tắc logic theo loại | Tách L2/L3/L5 (gắn mã TT-20/21/52/53/54 trong `logic.py`) thành file quy tắc theo loại; KCN/nhà ở: tổng % đợt = 100%; đợt cuối gắn mốc bàn giao/sổ; tiền tệ HĐ ≠ tiền tệ thu → phải có điều khoản tỷ giá; cọc không nằm trong lịch đợt | `logic.py` L1, L4 đã đọc từ danh mục; chỉ L2/L3/L5 gắn cứng | Hành vi XD không đổi (so kết quả trước/sau trên 3 master mẫu) |
| **E3** Tham số dạng bảng | Kiểu `bang` cho lịch đợt: *lần \| % \| số tiền \| tiền tệ \| mốc/ngày \| ghi chú*; đọc bảng từ DOCX/PDF | Bộ đọc bảng BOQ (`doc_hop_dong.py`, Import BOQ qua ABBYY) | Ô text TT-20 kiểu "Giai đoạn 1: 80%; …" vẫn hợp lệ cho XD |
| **E4** Output | JSON thêm `loai_hop_dong`, `mau_id`, `phien_ban_mau`, `che_do ∈ {trich_day_du, doi_chieu_ban_ky}`; giữ `tham_so[]`, `phieu_kiem_tra` | Contract nguồn #6 ở file CRM mục 6 | Không đổi khóa hiện có |
| **E5** Chế độ đối chiếu | Đầu vào thêm bộ tham số kỳ vọng → đầu ra `lech[]` theo mức | Cơ chế `DAP_AN_*.tsv` + `so_voi_dap_an` | Dùng cho CRM-G5 |
| **E6** Không mang sang CRM | BOQ, đợt thanh toán xây dựng, K1–K8, B1–B8, P01–P18 ở lại #5 | `csdl_hop_dong.py`, `nghiep_vu.py` | CRM chỉ gọi API trích/đối chiếu |

**Đầu vào còn thiếu:** 2–3 hợp đồng đã ký (che tên) + phụ lục mỗi loại để chốt danh mục KCN/nhà ở (nháp ở TL 32 §1.2) và lập đáp án mẫu. Chưa có → E1/E2 chỉ làm khung, chưa đo được độ chính xác.

---

## 5. Dữ liệu bổ sung vào master (TL 38), chỉ phần mới

| Nhóm | Trường cốt lõi |
|---|---|
| `mau_hop_dong` | mã mẫu, loại HĐ, pháp nhân, phiên bản, file + hash, người tải / kiểm / duyệt, hiệu lực từ–đến, ghi chú thay đổi |
| `mau_anh_xa` | phiên bản mẫu, trường dữ liệu, placeholder/ô, bắt buộc, kiểu (text/số/ngày/tiền/bảng), định dạng hiển thị (số bằng chữ, dd/mm/yyyy…) |
| `bao_gia` | số, ngày, người lập, pháp nhân, dự án/lô/căn, khách (mã Junsky hoặc đối tượng dự thảo), giá, tiền tệ, **tỷ giá + ngày + người nhập**, trạng thái, liên kết HĐ nếu chuyển |
| `lich_dong` (dùng chung báo giá / HĐ) | lần, %, số tiền, tiền tệ, loại mốc (ngày/sự kiện), ngày hoặc mã sự kiện, ghi chú, thứ tự |
| Master hợp đồng (thêm trường) | `trang_thai_giao_ket` (mục 1), `mau_id`, `phien_ban_mau`, `revision_du_thao`, `nguon_tham_so ∈ {MAU, TRICH, NHAP_TAY}` theo từng tham số |
| `ban_ky` | HĐ, file PDF + hash, ngày ký, người tải, khai có sửa, kết quả đối chiếu (chưa chọn / khớp / lệch mức n / không đối chiếu được), `lech[]` |
| `kiem_mau_cau_hinh` | nhóm (loại × phiên bản mẫu), tỷ lệ hiện hành, cửa sổ, lịch sử điều chỉnh |
| `doi_tuong_du_thao` | thông tin khách chờ mã Junsky; CCCD/STK mã hóa cột; chuyển thành đối tượng khi kế toán gán mã |

Nguyên tắc giữ nguyên từ file CRM mục 8: NULL ≠ 0; không suy %/VAT/FX từ tổng tiền; cùng raw không sinh bản mới; đợt có mốc sự kiện chưa có ngày không báo quá hạn.

---

## 6. Ca nghiệm thu bổ sung

| Mã | Anh bấm/thử | Kết quả phải thấy |
|---|---|---|
| CRM-GA1 | Tải mẫu mới có 1 placeholder chưa ánh xạ | Không duyệt được; báo đúng tên ô; HĐ đang soạn vẫn dùng mẫu cũ |
| CRM-GA2 | Lập báo giá KCN bằng USD, nhập tỷ giá, in | File in có USD, VND, dòng tham chiếu tỷ giá + ngày + người nhập; tổng % = 100% |
| CRM-GA3 | Chuyển báo giá sang soạn HĐ, sửa 1 đợt, xuất 2 lần | Lịch không nhập lại; 2 file xuất với 2 hash, revision 1 → 2 |
| CRM-GA4 | Bấm Ký kết không có PDF; rồi có PDF; tải lại cùng PDF | Lần 1 bị chặn; lần 2 sang `DA_KY`, tham số khóa; lần 3 không tạo bản mới |
| CRM-GA5 | Khai "có sửa", PDF khác bản in ở 1 đợt | HĐ bị đối chiếu bắt buộc; bảng lệch chỉ đúng đợt đó, mức quan trọng đúng |
| CRM-GA6 | 20 HĐ khớp liên tiếp cùng mẫu | Tỷ lệ kiểm mẫu giảm đúng một bậc, không dưới sàn |
| CRM-GA7 | Kế toán bấm Hiệu lực | Nghĩa vụ đúng số dòng/số tiền/tiền tệ; thấy ở F6; M1 nối tiền được; CFO thấy HĐ "lệch chuẩn" (nếu có) ở Việc cần xử lý |
| CRM-GA8 | Người ngoài quyền mở HĐ có CCCD | Chỉ 4 số cuối; không tải được PDF bản ký |

---

## 7. Ảnh hưởng tới các điểm đang chờ chốt (file CRM mục 11)

- **Q4** (loại nghĩa vụ): CRM-G trả lời phần lớn — đợt theo % hoặc số tiền, mốc ngày/sự kiện, tiền tệ USD/VND với tỷ giá nhập tay có người/ngày. Còn mở: cọc, phí quản lý/hạ tầng kỳ, lãi chậm trả.
- **Q5** (phụ lục/thay đổi): mẫu phụ lục đi cùng cơ chế G1/G3; xử lý phần đã thu vẫn chờ anh.
- **Q7** (phân quyền): CCCD/ĐKDN và PDF bản ký là dữ liệu nhạy cảm → quyền theo pháp nhân + dự án; backend kiểm (A7).
- **Mục 1 file CRM** cần sửa một dòng: "CFO duyệt tham số" → "CFO duyệt **phiên bản mẫu**; hợp đồng từ mẫu kế toán kiểm là đủ; hợp đồng không từ mẫu: [CẦN ANH XÁC NHẬN]".

---

## 8. Hàng đợi và lộ trình (đề nghị, chưa ghi vào `HANG-DOI-YEU-CAU.md` trên máy anh)

- **V16a** — E1–E4 engine theo loại + CRM-G1 mẫu/ánh xạ. Điều kiện bắt đầu: có 2–3 hợp đồng mẫu mỗi loại.
- **V16b** — CRM-G2 báo giá, G3 soạn HĐ, G4 ký kết, G6 kế toán kiểm → hiệu lực (nối F6/F7 hiện có).
- **V16c** — E5 + CRM-G5 kiểm mẫu ngẫu nhiên; G7 bộ chuẩn dự án; G8 báo cáo.
- Theo tiêu chuẩn nội bộ (TL 31): **chốt màn hình → chốt schema → hàng đợi → anh ra lệnh code**; mỗi V có test và review độc lập.

---

## 9. Điểm cần anh xác nhận (gom)

**Quyết định ngay**
1. Hợp đồng **không** sinh từ mẫu (luồng B): giữ CFO duyệt hay hạ xuống kế toán kiểm?
2. Tham số kiểm mẫu ngẫu nhiên mặc định (mục 3): 50% khởi điểm, biên 10–100%, cửa sổ 20, bậc 20 điểm — đồng ý hay đổi số?

**Trả lời sau (không chặn)**
3. 2–3 hợp đồng đã ký + phụ lục mỗi loại (che tên) để chốt danh mục KCN/nhà ở.
4. Mẫu phụ lục hiện có cho KCN và nhà ở? Có mẫu đặt cọc/đặt chỗ riêng không (cọc → 344 theo CFO-02)?
5. Ngân hàng/tỷ giá ghi trong mẫu KCN để đặt sẵn câu tham chiếu khi in báo giá.

*Tài liệu không chứa số liệu tài chính, tên khách hàng hay số hợp đồng thật.*
