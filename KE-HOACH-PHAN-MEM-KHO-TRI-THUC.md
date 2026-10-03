# Kế hoạch xây dựng phần mềm Python — kho tri thức kế toán và học liên tục

**Ngày 17/09/2026 · Bản 1.2** — mục 4.4 đổi từ "đối soát tháng" sang "mỗi phiên có ba cổng" theo quyết định của anh: xuất 131/331 + danh mục trước mỗi lần chạy, chạy xong phải chốt
Căn cứ: (1) toàn bộ khảo sát trong dự án này — sao kê, Base, hóa đơn điện tử, sổ nhật ký chung, mẫu nhập Junsky; (2) tài liệu *Phản biện vòng 2 và quyết định chốt* (17/09/2026).

---

## 0. Giả định phạm vi — lấy nguyên từ quyết định đã chốt

| Đã chốt | Ý nghĩa cho kế hoạch này |
|---|---|
| Pilot **một pháp nhân** (PLHN), ưu tiên **sao kê + đối chiếu công nợ** | Máy đề xuất phiên bản 1 chỉ xử lý dòng sao kê. Hóa đơn và Base là **nguồn bằng chứng** cho tầng 0, không phải đối tượng đề xuất ở pilot. |
| Tích hợp Junsky chỉ bằng **import Excel** | Không API. Trạng thái sổ là **ảnh chụp theo đợt**, không thời gian thực. |
| **IT nội bộ** xây; trọng tâm là kho tri thức và học liên tục | Kế hoạch viết cho đội IT nội bộ đọc được; ưu tiên đơn giản, ít thành phần. |
| **Không dùng AI**, chỉ Python thuần | Đã rà 13 thao tác, không thao tác nào cần AI. Thư viện: pandas · openpyxl · lxml · pdfplumber · sqlite3 (chuẩn) · re · json. |
| Kho tri thức 5 nhóm · kho trạng thái vận hành tách riêng · thống kê là view dẫn xuất · liên kết lịch sử mức A/B/C · độ tin cậy từng trường · point-in-time | Là khung kiến trúc của phần mềm, mục 3. |

---

## 1. Kết luận điều hành

- **Khoảng 60% khối lượng đã có sẵn dưới dạng script khảo sát.** Đọc sao kê PDF (24 file, 1.874 dòng, 4 phép kiểm tra), đọc hóa đơn XML (1.907 hóa đơn, 0 lỗi), đọc Base (1.115 đề nghị), kho tri thức thống kê phiên bản 1 (71% phủ / 92% đúng ngoài mẫu), bộ 431 từ khóa có 3 con số bằng chứng, bộ xuất Junsky `CB_tmpEntry1/2`. Việc còn lại **không phải viết lại**, mà là **tái cấu trúc** các script rời thành một hệ thống có kho trạng thái, kho tri thức 5 nhóm và vòng học có điều kiện.
- **Ba phát hiện bằng số liệu trong dự án buộc phải ghi vào thiết kế, không có trong tài liệu phản biện:** (a) *học phải cân theo giá trị* — Vietinbank có 134 hóa đơn phí ngân hàng chỉ 15 triệu và 13 hóa đơn lãi vay 45 tỷ, học theo tần suất sẽ sai 100% giá trị; (b) *tài khoản đổi theo giai đoạn dự án* — cùng nhà cung cấp vào 24126 rồi sang 6427, độ thuần MST trong mẫu 78% nhưng ngoài mẫu 25%; (c) *thông tin "đối tượng chịu chi phí" không nằm trên hóa đơn hay sao kê* — nó nằm ở đề nghị Base (`du_an`, `chi_phi`) và hợp đồng.
- **Tỷ lệ nối được vào sổ đã đo, quyết định thứ tự làm:** hóa đơn 82–91% · sao kê 80% (chi 94%, thu 66%) · Base 5%. Tầng 0 đối chiếu nên dựng từ **hóa đơn ↔ sổ** trước, vì đó là liên kết mạnh nhất và tạo ra công nợ mở theo hóa đơn.
- **Trong 5 câu hỏi kiến trúc còn treo, 3 câu đã có lời đáp** (mục 7): E1 anh chốt xuất 131/331 + danh mục trước mỗi phiên; E4 nhờ đó không còn là điều kiện; E2 đo được từ dữ liệu sẵn có. Còn E3 (TT99) và E5 (ai kiểm tra mù) phải hỏi người.
- **Mỗi lần chạy là một phiên có ba cổng** (mục 4.4): cổng vào kiểm tra bằng dữ liệu rằng 131/331 và danh mục là bản mới nhất, cổng ra bắt buộc chốt. Đối soát tự xảy ra ở cổng vào phiên kế tiếp — vừa cập nhật công nợ, vừa xác nhận "đã ghi sổ", vừa là tập đáp án khách quan cho vòng học. Khóa sổ tháng chỉ là phiên cuối tháng với điều kiện chênh = 0.
- **Đề xuất:** vào Giai đoạn 0 ngay, không cần chờ trả lời hết 5 câu, vì tầng 0 + tầng 1 không cần lịch sử — chỉ cần danh mục sạch và ảnh chụp công nợ.

---

## 2. Bản đồ tái sử dụng — cái gì đã có, đi vào đâu

| Tài sản đã có | Đo được | Đi vào gói | Mức tái dùng |
|---|---|---|---|
| `15_doc_pdf_2nam.py` — đọc sao kê Vietinbank 2 định dạng, 4 phép kiểm tra | 24/24 file cân đối, 1.874 dòng | `nguon/sao_ke` | Giữ nguyên, bọc thành hàm |
| `17_doi_chieu_2nam.py` — khớp sao kê ↔ sổ ở mức chứng từ (3 bước) | 80% | `doi_chieu/lien_ket_lich_su` | Tái cấu trúc: thêm mức A/B/C và điểm bằng chứng |
| `doc_hd.py` — đọc XML hóa đơn lược đồ TCT 2.1.0, bảng 2 cấp | 1.907 HĐ, 5.198 dòng, 0 lỗi | `nguon/hoa_don_xml` | Giữ nguyên |
| Đọc bảng kê Excel cổng thuế (67 file) | 2.716 HĐ, có trạng thái xử lý | `nguon/hoa_don_bang_ke` | Giữ nguyên |
| Đọc Base (Excel chỉ mục + JSON, giải mã base64) | 1.115 ĐN | `nguon/base` | Bổ sung: quét thư mục thay vì chỉ mục (1.283 ≠ 1.115) |
| `kho_tri_thuc.py` — sự kiện đếm dồn, vòng đời MỚI→ĐỀ CỬ→ĐÃ DUYỆT, người thắng máy | 71% phủ / 92% đúng | `tri_thuc/thong_ke` | **Sửa lớn**: thành view dẫn xuất từ nhãn đủ điều kiện; thêm trọng số giá trị; thêm kỳ hiệu lực |
| `TU-DIEN-NHOM-NGHIEP-VU.xlsx` — 431 từ khóa, 3 con số bằng chứng, sheet CHỜ DUYỆT / NHẬT KÝ | 100% Base phân loại | `tri_thuc/quy_tac` + giao diện Excel | Giữ cấu trúc; đổi nguồn ghi từ script sang gói `hoc` |
| Sheet KHÓA CỨNG (biển số, số HĐ, MST, số TK) | 15 MST chắc chắn, 20 khá chắc | `tri_thuc/danh_muc` | Giữ; nạp thêm từ dữ liệu hóa đơn |
| 28 mã khoản mục phí Junsky + ánh xạ 22/28 nhóm G | 3.038 dòng sổ | `tri_thuc/chinh_sach` | Là bộ phân loại chính thức — nhóm G phải quy về đây |
| Cây phân nhánh hóa đơn (7 nhánh mua, 5 nhánh bán) + mẫu bút toán | 496/535 một mẫu | `tri_thuc/chinh_sach/mau` | Là 2 mẫu định khoản đầu tiên cho hóa đơn (giai đoạn 3) |
| `14_xuat_junsky.py` — `CB_tmpEntry1/2`, đọc chú thích nhà cung cấp | Đã nhập thử 17/24 | `xuat/junsky` | Giữ; 3 câu hỏi nhà cung cấp chưa trả lời |
| `kho_tri_thuc_data/` — 1.337 sự kiện, 723 dòng log | 468 KB | Dữ liệu khởi tạo cho `tri_thuc/thong_ke` | Nạp lại qua vòng học, không copy thẳng |

---

## 3. Kiến trúc phần mềm — 7 gói Python, 1 file SQLite, Excel cho người

```
kho_tri_thuc/
├── nguon/          đọc 5 nguồn → bảng chuẩn hóa 2 cấp (chứng từ / dòng)
│     sao_ke · hoa_don_xml · hoa_don_bang_ke · base · junsky_xuat
├── trang_thai/     KHO TRẠNG THÁI VẬN HÀNH — tách khỏi tri thức
│     cong_no_mo (ảnh chụp as-of) · phan_bo (M:N, giữ chỗ) · xu_ly (5 bước)
├── tri_thuc/       KHO TRI THỨC 5 NHÓM — có phiên bản, có ngày hiệu lực
│     danh_muc · chinh_sach (mẫu, ràng buộc, ánh xạ TK) · tinh_huong
│     thong_ke (VIEW dẫn xuất) · quy_tac (+ nhật ký quyết định)
├── de_xuat/        MÁY ĐỀ XUẤT — chuỗi 5 bước, mỗi bước một module
│     nhan_dien → doi_chieu (ứng viên + điểm) → rang_buoc → xep_hang → tin_cay
├── hoc/            VÒNG HỌC CÓ ĐIỀU KIỆN
│     nhat_ky · du_dieu_kien · tinh_lai_thong_ke · de_cu_quy_tac (+ báo cáo tác động)
│     kiem_tra_mu · bao_cao_ky
├── xuat/           Excel Junsky · xác nhận ghi sổ
└── cli.py          lệnh theo phiên: mo_phien (cổng vào) · de_xuat · hoc · chot_phien (cổng ra) · bao_cao · backtest
```

**Bốn quyết định kỹ thuật:**

| Quyết định | Chọn | Vì sao |
|---|---|---|
| Lưu trữ máy | **SQLite, một file** `kho.sqlite` | Không cần server; IT nội bộ quản được; backup = copy file; đủ cho vài trăm nghìn dòng. |
| Bản gốc cho người | **Excel** (`TU-DIEN-*.xlsx`, sheet CHỜ DUYỆT, NHẬT KÝ) | Đã chốt từ bước Base: người sửa Excel, máy đọc Excel → SQLite. Không ai sửa SQLite tay. |
| Chạy | **Theo đợt bằng dòng lệnh**, không màn hình | Pilot không xây UI (đã chốt). Kế toán duyệt trên Excel. |
| Định danh dòng | Khóa tự nhiên có sẵn: sao kê = mã tham chiếu NH + ngày + tiền + TK · hóa đơn = MST bán + ký hiệu + số · Base = ID · sổ = số chứng từ | Chống trùng khi nhập lại file — lỗi thật đã gặp ở mảng ngân hàng. |

---

## 4. Mô hình dữ liệu tối thiểu

### 4.1 Kho trạng thái vận hành (bắt buộc từ đầu)

| Bảng | Khóa | Cột chính | Nguồn cấp |
|---|---|---|---|
| `cong_no_mo` | (id phiên, mã đối tượng, số HĐ) | phát sinh, đã trả, còn lại, TK 131/331 | Junsky xuất **trước mỗi phiên** (anh chốt 17/09). Phần mềm chỉ cộng dồn trong phiên. |
| `cong_no_ky_vong` | (id phiên, mã đối tượng, số HĐ) | còn lại kỳ vọng sau phiên = ảnh chụp vào + phân bổ đã duyệt | Ghi ở cổng ra; so với ảnh chụp phiên sau |
| `doi_soat` | (id phiên, mã đối tượng, số HĐ) | kỳ vọng · Junsky · chênh · nhóm A/B/C | Tự sinh ở cổng vào phiên kế tiếp — xem 4.4 |
| `phien_log` | id phiên | as_of, hash 5 file đầu vào, số dòng, tổng tiền, người chốt, trạng thái mở/chốt | Ghi ở cổng vào và cổng ra |
| `phan_bo` | id | dòng sao kê × hóa đơn × số tiền × trạng thái (giữ chỗ / duyệt / ghi sổ / hủy) | Máy tạo, người duyệt |
| `xu_ly` | (id chứng từ, phiên bản) | đề xuất → duyệt cuối → đã xuất → đã ghi sổ → đã đối soát; thời điểm; người | Máy + kết quả import |
| `nhom_chung_tu` | case_id | gom sao kê + hóa đơn + đề nghị Base cùng một nghiệp vụ | Máy |

### 4.2 Kho tri thức (5 nhóm, mọi bảng có `hieu_luc_tu`, `hieu_luc_den`, `phien_ban`)

| Nhóm | Bảng | Khóa | Ghi chú từ dữ liệu đã đo |
|---|---|---|---|
| 1 Danh mục & định danh | `doi_tuong` (mã nội bộ Junsky) · `dinh_danh` (MST, số TK, bí danh, biển số, số HĐ → mã nội bộ, **mức xác minh**) | mã nội bộ | Vietinbank có 4 cách viết tên, 1 MST → khóa theo MST. 255 MST bán + 95 MST mua chưa có mã Junsky. |
| 2 Chính sách, ràng buộc, mẫu | `mau_dinh_khoan` (slot bắt buộc, mẫu đảo) · `rang_buoc` (kỳ khóa, số còn mở, trùng, MST người mua ≠ MST công ty) · `anh_xa_tk` (có hiệu lực) · `khoan_muc_phi` (28 mã) | mã mẫu | Mẫu hóa đơn mua vào đã xác định: `Nợ 1331 + Nợ ⟨TK⟩ / Có 33111` (496/535). Ngưỡng 30 triệu CCDC/TSCĐ là **tham số**. |
| 3 Bộ nhớ tình huống | `lien_ket` (chứng từ ↔ bút toán, **mức A/B/C**, bằng chứng, bối cảnh, ngày) | (chứng từ, bút toán) | Tỷ lệ nối đã đo: hóa đơn XML 82%, hóa đơn Excel 91%, sao kê 80%, Base 5%. |
| 4 Thống kê | `thong_ke_*` — **view dẫn xuất**, tính lại từ `nhan` đủ điều kiện | khóa điều kiện | Đếm **cả số lần lẫn giá trị**; phân vùng theo kỳ hiệu lực; giảm trọng số mềm trong vùng. |
| 5 Quy tắc & nhật ký | `tu_khoa` (431 dòng, 3 con số bằng chứng) · `khoa_cung` · `quy_tac_de_cu` (+ báo cáo tác động) · `nhat_ky_quyet_dinh` (mã lý do 7 loại) · `ngoai_le` | id | Từ Excel hiện có, không thiết kế mới. |

### 4.3 Nhãn học

`nhan` (id chứng từ, phiên bản, giá trị từng trường, trạng thái: **duyệt cuối → đã xuất → đã ghi sổ → đủ điều kiện học / ngoại lệ / bị thay thế**, mã lý do, giá trị tiền). Mỗi chứng từ **một nhãn hiệu lực**. Thu hồi = đổi trạng thái, không trừ.

### 4.4 Mỗi lần chạy là một phiên có cổng — dữ liệu luôn là bản mới nhất

Quyết định của anh (17/09/2026, hai bước): Junsky xuất 131/331 và danh mục **trước mỗi lần chạy**; **chạy xong phải chốt lại**. Điều này thay thế "ảnh chụp theo tháng" bằng "ảnh chụp theo phiên" và **đóng ba vòng** mà thiết kế đang cần:

| Vòng | Trước | Nay |
|---|---|---|
| Trạng thái công nợ | Phần mềm tự cộng dồn nhiều tuần giữa hai ảnh chụp | **Mỗi phiên bắt đầu từ ảnh chụp mới của Junsky**; chỉ cộng dồn trong phiên. Hai rủi ro "phân bổ hai lần" và "hóa đơn đến muộn" thu hẹp vào trong một phiên. |
| Xác nhận "đã ghi sổ" (E4) | Cần Junsky trả kết quả import | **Không cần.** Ảnh chụp phiên sau so với "kỳ vọng" của phiên trước: hóa đơn đã đóng = đã nhập |
| Sự thật khách quan cho vòng học | Chỉ có kiểm tra mù | Bảng chênh lệch **mỗi phiên** là tập đáp án do sổ cái sinh ra |

**"Xác nhận" phải là kiểm tra bằng dữ liệu, không phải ô để bấm "Có".** Người bấm xác nhận theo thói quen; máy thì không. Ba cổng của một phiên:

| Cổng | Máy kiểm tra gì | Không đạt thì |
|---|---|---|
| **Cổng vào** — trước khi đề xuất | (a) Ảnh chụp 131/331 có `as_of` ≥ ngày cuối của dữ liệu cần xử lý và **dấu vân tay file** (hash) khác phiên trước — hoặc giống nhưng kế toán ghi rõ "không có thay đổi". (b) Danh mục: so với phiên trước, **mọi mã mới / đổi tên / đổi MST** được liệt kê và đưa vào CHỜ DUYỆT. (c) **Phiên trước đã chốt.** | Dừng, in lý do. Không có chế độ "chạy tạm". |
| **Trong phiên** — khóa | Chỉ một phiên tại một thời điểm; mọi phân bổ đang chờ duyệt mang cờ **giữ chỗ** | Phiên thứ hai bị từ chối |
| **Cổng ra** — chốt | (a) Ghi **công nợ kỳ vọng** = ảnh chụp vào + phân bổ đã duyệt. (b) Xuất Excel Junsky. (c) Ghi `phien_log`: id, as_of, hash, số dòng, tổng tiền, người chốt. (d) Đổi trạng thái nhãn → "đã xuất". | Phiên ở trạng thái "chưa chốt"; phiên sau không mở được |

Đối soát trở thành **tự động ở cổng vào của phiên kế tiếp**: ảnh chụp mới ⟷ công nợ kỳ vọng của phiên trước → ba nhóm chênh. Không cần một việc đối soát tháng riêng; **khóa sổ tháng chỉ là phiên cuối cùng của tháng**, thêm điều kiện chênh = 0.

Báo cáo đối soát có đúng **ba nhóm chênh**, mỗi nhóm một hành động:

| Nhóm chênh | Nghĩa | Hành động |
|---|---|---|
| A · Phần mềm có, Junsky không | Đề xuất đã duyệt nhưng chưa nhập / nhập lỗi | Nhập lại; nhãn giữ trạng thái "đã xuất", chưa lên "đã ghi sổ" |
| B · Junsky có, phần mềm không | Kế toán ghi ngoài phần mềm (điều chỉnh, chứng từ đến muộn, bút toán tay) | Phần mềm học: đây là nhãn mới **không do máy đề xuất** — quý nhất vì không có automation bias |
| C · Cả hai có nhưng khác số / khác hóa đơn | Phân bổ sai hóa đơn, trả một phần, cấn trừ | Kế toán chốt; nhãn cũ → "bị thay thế", nhãn mới → học |

Chênh lệch = 0 sau xử lý là **cổng bắt buộc** để chốt phiên cuối tháng — giống nguyên tắc cân đối đã áp cho sao kê (24/24 file phải cân).

**Gói xuất chuẩn trước mỗi phiên** (cố định, kế toán xuất từ Junsky, vài phút):

| # | File | Dùng ở cổng | Tần suất đổi |
|---|---|---|---|
| 1 | Sổ chi tiết 131 và 331 **theo từng hóa đơn**, còn mở, as-of | Cổng vào (a) | Mỗi phiên |
| 2 | Danh mục đối tượng: mã nội bộ, tên, MST, số TK ngân hàng | Cổng vào (b) | Hiếm — máy chỉ báo phần thay đổi |
| 3 | Hệ thống tài khoản chi tiết đang hiệu lực | Cổng vào (b) | Rất hiếm; đổi là **phân vùng cứng** (TT99) |
| 4 | Danh mục khoản mục phí (28 mã), dự án | Cổng vào (b) | Hiếm |
| 5 | Kỳ đã khóa | Ràng buộc | Mỗi tháng |

**Cái giá phải trả:** mỗi phiên tốn kế toán một lần xuất 5 file. Nhịp phiên nên gắn với **nhịp sao kê về** (theo tuần hoặc theo đợt), không chạy vì chạy. Trong một phiên, hai rủi ro cũ vẫn còn nhưng nhỏ: kế toán ghi tay ở Junsky **trong lúc** phiên đang mở → phân bổ hai lần; chặn bằng ràng buộc "số còn mở" + giữ chỗ, và phát hiện ở cổng vào phiên sau (nhóm chênh B).

---

## 5. Mười quy tắc thiết kế đã được dữ liệu của chính dự án chứng minh

| # | Quy tắc | Bằng chứng |
|---|---|---|
| 1 | **Thống kê cân theo giá trị tiền, không chỉ tần suất** | Vietinbank: 134 HĐ phí = 0,0% giá trị; 13 HĐ lãi vay = 100% giá trị |
| 2 | **Mọi ánh xạ có kỳ hiệu lực; phân vùng cứng khi thay đổi được khai báo** | VETC 24126 → 6427; nhóm 24x từ 51–64% xuống 19–28%; MST ngoài mẫu chỉ 25% |
| 3 | **Khóa đối tượng là mã nội bộ; MST/số TK/tên là định danh có mức xác minh** | Một MST, 4 tên; một nhà cung cấp, nhiều tài khoản chi phí |
| 4 | **Khóa cứng thắng từ khóa; từ khóa có 3 con số bằng chứng** | 104/431 từ khóa chết; từ khóa hợp đồng của G22 khớp 48 dòng ngoài nhóm |
| 5 | **"Đối tượng chịu chi phí" lấy từ Base/hợp đồng, không đoán từ hóa đơn** | 99% chứng từ sổ có mã dự án; hóa đơn điện EVN tách 3 tài khoản mà hóa đơn không nói |
| 6 | **Hóa đơn hai luồng: XML (dòng hàng) và Excel (chỉ mức hóa đơn)** | 811 hóa đơn không mã = ngân hàng, điện, nước; nối sổ 91% |
| 7 | **Chuẩn hóa chữ: thay Đ→D trước NFD** | "ĐIỆN" thành "IEN" — lỗi gặp hai lần |
| 8 | **Người thắng máy; máy chỉ đề cử vào CHỜ DUYỆT** | Đã chốt và đã vận hành ở bộ từ khóa Base |
| 9 | **Mọi ngưỡng là tham số trong file cấu hình, không chôn trong code** | 30 triệu (TSCĐ), 5 triệu (khấu trừ), 80%/≥3 mẫu, 18 tháng ngủ, 7 ngày |
| 10 | **Đối chiếu ngược với sổ là thước đo duy nhất; không tin ý kiến máy** | Phép thử AI: 13/34 dòng AI trả lời sai một cách hợp lý |

---

## 6. Lộ trình theo cổng điều kiện

Thời lượng là **ước lượng thô để xin nguồn lực**, không phải cam kết; chốt lại sau Giai đoạn 0.

### Giai đoạn 0 — Kiểm chứng trước đầu tư (ước 4–6 tuần, 1 IT + kế toán 2 giờ/tuần)

| Việc | Đầu ra | Cổng |
|---|---|---|
| 0.1 Gói `nguon/`: bọc 5 bộ đọc đã có thành hàm chuẩn, bảng 2 cấp, khóa tự nhiên chống trùng | Nạp 12 tháng gần nhất của PLHN vào `kho.sqlite` | 100% file đọc được, tổng khớp bảng kê/sao kê |
| 0.2 Liên kết lịch sử mức A/B/C: sao kê ↔ sổ 112 ↔ công nợ; hóa đơn ↔ sổ | Báo cáo tỷ lệ A/B/C theo nguồn; kế toán kiểm ngẫu nhiên 100 A + 100 B | **A đúng ≥ ngưỡng anh chốt (gợi ý 98%)**; nếu A < 50% dòng sao kê → xem lại nguồn |
| 0.3 Tái dựng công nợ mở as-of cho **backtest lịch sử**: neo bằng ảnh chụp cuối tháng (lịch sử chỉ có mốc tháng), phát lại trong tháng | Số dư tái dựng cuối mỗi tháng = ảnh chụp Junsky tháng đó | Chênh lệch = 0 hoặc giải thích hết. Khi vận hành thật, mốc neo là **mỗi phiên** nên việc này còn nhẹ hơn. |
| 0.4 Baseline A: tầng 0 + ràng buộc + 10–15 mẫu sao kê do kế toán trưởng viết, chạy point-in-time 3 tháng cuối | Độ đúng toàn bộ, độ đúng phân bổ, độ phủ, sai sót theo giá trị tiền | Mốc, không cổng |
| 0.5 Baseline B: A + thống kê có điều kiện (9 tháng học, 3 tháng thử) | So với A | B hơn A về phủ mà không giảm đúng |
| 0.6 Phân tích phần dư | Tỷ trọng theo nguyên nhân | Quyết định có cần tầng cao hơn không |

**Không làm ở giai đoạn 0:** màn hình, tích hợp, ML, đưa dữ liệu thật ra ngoài.

### Giai đoạn 1 — Lõi hệ thống, chạy ngầm (ước 6–8 tuần)

Cổng vào: qua 0.2 và 0.3.

- Gói `trang_thai/` đầy đủ; `tri_thuc/` 5 nhóm nạp từ Excel hiện có; `de_xuat/` 5 bước với độ tin cậy từng trường và đầu ra **đầy đủ / một phần / không**; `hoc/` với nhãn đủ điều kiện và view thống kê.
- Chạy ngầm hằng ngày trên dữ liệu thật, không hiển thị; kiểm tra mù 50 chứng từ/tuần.
- Cổng ra: ngưỡng độ đúng do anh chốt sau khi thấy số ở 0.4–0.5; **khoảng cách chấp nhận ↔ độ đúng kiểm tra mù** không tăng.

### Giai đoạn 2 — Đưa vào dùng (ước 4 tuần)

Cổng vào: qua giai đoạn 1.

- Kế toán duyệt trên Excel (sheet CHỜ DUYỆT, mã lý do); xuất `CB_tmpEntry1/2`; xác nhận ghi sổ bằng đối chiếu ảnh chụp công nợ đợt sau (nếu Junsky không trả kết quả import — **câu E4**).
- Báo cáo kỳ 6 phần (đã thiết kế ở bước Base); nhật ký quyết định đầy đủ.
- Duyệt nhanh theo lô: **tắt** trong pilot.

### Giai đoạn 3 — Mở rộng (sau pilot, có cổng riêng)

- Hóa đơn mua vào theo dòng hàng: bộ từ khóa riêng cho tên hàng (bộ Base chỉ phủ 31%); nối hóa đơn ↔ Base để lấy đối tượng chịu chi phí; 2 mẫu đầu tiên đã có.
- Base như nguồn đề xuất (bút toán công nợ), không chỉ nguồn bằng chứng.
- Pháp nhân thứ hai: sản xuất hoặc BĐS nhà ở — kiểm tra lại ràng buộc "thanh toán hộ" và danh mục.

---

## 7. Năm câu hỏi kiến trúc — dữ liệu đã trả lời được gì

| # | Câu hỏi | Dữ liệu trong dự án nói gì | Còn phải hỏi |
|---|---|---|---|
| E1 | Junsky có xuất công nợ 131/331 **theo từng hóa đơn**? | **Anh đã trả lời (17/09): dễ, xuất hàng tháng, đối soát định kỳ với phần mềm.** Sổ nhật ký chung cũng đã có cột số hóa đơn ở 3.263/7.341 dòng. | Chỉ còn xác nhận **định dạng cột** của bản xuất: có tách *phát sinh – đã trả – còn lại theo từng hóa đơn* không, hay chỉ số dư theo đối tượng. Nếu chỉ theo đối tượng, tầng 0 vẫn chạy nhưng bảng `phan_bo` phải hạ xuống mức đối tượng. |
| E2 | Sao kê có mã tham chiếu NH và kế toán có ghi vào sổ 112? | Sao kê Vietinbank **có** cột số giao dịch (đã bóc). Diễn giải sổ mới thấy ghi số RQ ở 15% dòng chi. | Đo được trong 1 ngày: quét cột nội dung sổ 112 tìm số giao dịch NH. Chưa đo. |
| E3 | TT99/2025 — pháp nhân đổi tài khoản chi tiết từ 01/01/2026? | Sổ đang dùng tiểu khoản tự thiết kế (24122, 24126, 131171, 338731…) — đã là cấu trúc riêng. Sổ mới có đến 12/2025. | Cần sổ 2026 + bảng đối chiếu TK cũ–mới từ kế toán trưởng. |
| E4 | Junsky có trả danh sách bút toán đã nhập sau import? | **Không còn là điều kiện.** Cổng vào phiên kế tiếp (mục 4.4) xác nhận "đã ghi sổ" bằng chính sổ cái: hóa đơn đóng ở Junsky = đã nhập. | Vẫn hỏi nhà cung cấp 3 câu về `EntryID`, `DebtID`, Entry2 — để xuất file đúng, không phải để xác nhận ghi sổ. |
| E5 | Ai kiểm tra mù, 2 giờ/tuần? | — | Anh quyết. Không có người này thì mọi chỉ số "độ đúng" chỉ là "độ đồng thuận". |

---

## 8. Chuẩn kỹ thuật cho đội IT

- **Python 3.11+**, chỉ thư viện chuẩn + pandas, openpyxl, lxml, pdfplumber. Không mạng, không API, không mô hình ngôn ngữ.
- **Cấu hình** `cau_hinh.yaml`: mọi ngưỡng, mã tài khoản, MST công ty, đường dẫn. Đổi ngưỡng không sửa code.
- **Tập vàng cố định** 200–300 chứng từ (từ 0.2 và kiểm tra mù); mọi thay đổi quy tắc/thống kê phải chạy lại trên tập vàng trước khi duyệt.
- **Point-in-time bắt buộc** trong backtest: máy chỉ được thấy dữ liệu có tại ngày cần đề xuất.
- **Nhật ký** mọi lần chạy: file vào, số dòng, tổng tiền, kết quả kiểm tra cân đối — giống 4 phép kiểm tra đã làm ở sao kê.
- **Chuẩn hóa văn bản** một hàm duy nhất (`Đ→D` → NFD → bỏ dấu → viết hoa → gộp khoảng trắng); không ai tự viết lại.
- **Bảo mật**: toàn bộ dữ liệu ở máy nội bộ; file xuất ra ngoài đơn vị phải qua bước ẩn tên đối tác và số tiền.

---

## 9. Rủi ro chính và cách giảm

| Rủi ro | Dấu hiệu | Giảm thiểu |
|---|---|---|
| Junsky không xuất được công nợ mở theo hóa đơn (E1) | 0.3 không tái dựng được | Hạ tầng 0 xuống mức đối tượng; thiết kế `phan_bo` vẫn giữ để nâng cấp sau |
| Sao kê thu (66% nối sổ) kéo độ phủ xuống | Baseline A thấp ở chiều thu | Ưu tiên chiều chi (94%) trong pilot; chiều thu học sau khi có hóa đơn bán ra nối vào |
| Ranh giới vốn hóa không được khai báo | Độ đúng rơi đột ngột theo tháng | Kế toán trưởng khai báo mốc; phân vùng cứng; cảnh báo tự động khi tỷ trọng 24x lệch >15 điểm |
| Kế toán không có 2 giờ/tuần cho kiểm tra mù | Chỉ số độ đúng không đo được | Chốt E5 trước khi vào giai đoạn 1 |
| Script khảo sát bị dùng thẳng làm sản phẩm | Không có test, không có cấu hình | Giai đoạn 0.1 là bước bọc lại có kiểm thử, không bỏ qua |

---

## 10. Việc trong hai tuần tới

1. Anh chốt **E5** (người kiểm tra mù); chuyển **E2** cho IT; xin kế toán **một bộ "gói xuất chuẩn" 5 file** (mục 4.4) của kỳ gần nhất để chốt định dạng cột và đo thời gian xuất.
2. Kế toán trích 12 tháng gần nhất của PLHN theo danh sách D.1 (9 loại dữ liệu) — phần lớn đã có trong dự án này, thiếu: sổ 131/331 theo hóa đơn, danh mục đối tượng kèm MST, TK chi tiết 2026, kỳ đã khóa.
3. IT dựng khung repo 7 gói, bọc 5 bộ đọc hiện có thành gói `nguon/` (việc 0.1).
4. Tôi soạn hai thứ: **phiếu yêu cầu dữ liệu** gửi kế toán (đúng định dạng cột) và **khung 10–15 mẫu định khoản cho sao kê** để kế toán trưởng điền.
5. Đo nhanh E2 trên dữ liệu đã có: quét cột nội dung sổ 112 tìm số giao dịch ngân hàng.

---

*Tài liệu chứa số hiệu tài khoản, MST và số liệu nội bộ — không chia sẻ ra ngoài đơn vị.*
