# Bàn giao giao diện — Kho tri thức kế toán · màn hình Định khoản

Tài liệu đi kèm file `dinh-khoan-prototype.html`. Đọc file này trước, sau đó mở file HTML để xem và thao tác thử.

## 1. Gói bàn giao

| File | Nội dung |
|---|---|
| `dinh-khoan-prototype.html` | Prototype bấm được, gói trong **một file** HTML + CSS + JavaScript thuần. Chạy không cần mạng. |
| `BAN-GIAO-dinh-khoan.md` | Tài liệu này: cấu trúc mã, chỗ cần nối phần lõi, quy tắc, danh sách thành phần và trạng thái. |

Toàn bộ dữ liệu trong prototype là **dữ liệu giả**: 10 giao dịch tháng 08/2026, đối tác giả, số tài khoản ngân hàng đã che. Không có tên công ty hay số liệu nội bộ.

## 2. Cách mở và xem trạng thái

- Mở thẳng file bằng trình duyệt (Chrome/Edge), không cần máy chủ. Khi chạy trong ứng dụng thật sẽ mở qua `localhost`.
- Chân menu trái có ô **“Xem trạng thái mẫu”** để chuyển nhanh giữa 12 trạng thái. Ô này chỉ có trong prototype, khi dựng thật thì bỏ đi.
- Cũng có thể mở thẳng một trạng thái bằng cách thêm tham số vào địa chỉ: `dinh-khoan-prototype.html?trang-thai=<mã>`.

| Mã | Trạng thái |
|---|---|
| `danh-sach` | Danh sách đầy đủ (mặc định) |
| `chua-co-file` | Chưa có file |
| `dang-xu-ly` | Đang đề xuất 6/10 |
| `mo-giao-dich` | Giao dịch Vàng đang mở, có phương án |
| `giao-dich-do` | Giao dịch Đỏ đang mở: ô thiếu, gợi ý TK |
| `ngan-sua` | Ngăn Sửa đang mở, ô Đối tượng đang tìm “dien” |
| `dong-y-hang-loat` | Hộp xác nhận đồng ý hàng loạt |
| `xuat-file` | Hộp xuất file, vẫn còn giao dịch chờ duyệt |
| `loi-chan` | Lỗi chặn: chưa có danh mục đối tượng |
| `nguon-du-lieu` · `tra-cuu` · `lich-su` | Màn hình 2, 3, 4 |

## 3. Ràng buộc kỹ thuật (đã tuân thủ)

- HTML + CSS + JavaScript thuần, không React hay framework nào.
- Không tải font, biểu tượng hay thư viện từ internet. Font hệ thống: `'Segoe UI', system-ui, …`. Biểu tượng là SVG nét vẽ khai báo trong đối tượng `ICONS`.
- Thiết kế cho màn hình 1366–1920px (khung ứng dụng đặt `min-width: 1280px`), không có bản di động.
- Màu được khai báo thành biến CSS trong `:root` (xem mục 9).

## 4. Cấu trúc mã trong file

Phần `<script>` chia làm 9 khối, có tiêu đề đánh số trong chú thích:

1. **Tiện ích**: `fmt` (tiền VND, dấu chấm), `norm` (bỏ dấu để tìm), `esc` (chống chèn HTML), `ICONS`, `badge`.
2. **Danh mục** `CAT` (tk, dt, da, km, cp) — dữ liệu giả.
3. **Dữ liệu giả** `seed()` (10 giao dịch) và `KB_RULES` (tri thức cho màn hình Tra cứu).
4. **Trạng thái** `S`. Hàm `set(patch)` cập nhật trạng thái rồi vẽ lại; `initState(mode)` dựng các trạng thái mẫu.
5. **Quy tắc nghiệp vụ trên giao diện**: `check(lines)`, `reasonText`, `visible` (lọc), `nextPending`, `bulkList`.
6. **Hành động**: `approve`, `edit`, `skip`, `confirmSkip`, `useOption`, `pickSuggest`, `confirmBulk`, `doExport`, `reloadSrc`, `saveDrawer`… và bảng `ACT` nối với thuộc tính `data-act` trên nút.
7. **Giao diện**: mỗi phần là một hàm trả về chuỗi HTML (`viewRow`, `viewDetail`, `viewDrawer`, `viewModal`, `pageNguon`…).
8. **Vẽ lại** `render()`: dựng lại toàn bộ `#app`, đồng thời giữ tiêu điểm, vị trí con trỏ chữ và vị trí cuộn.
9. **Sự kiện**: một bộ nghe cho mỗi loại sự kiện (click, input, keydown…), gắn trên `#app` và phân việc theo `data-act`, `data-input`, `data-combo`.

Khi ghép vào ứng dụng có sẵn, có thể giữ nguyên mô hình “trạng thái → vẽ lại”, chỉ cần thay dữ liệu giả và nối các chỗ ở mục 5.

## 5. Chỗ cần nối phần lõi (tìm chữ `NỐI LÕI` trong file)

| Vị trí | Prototype đang làm | Khi dựng thật |
|---|---|---|
| `CAT` | Danh mục giả | Nạp danh mục đối tượng, tài khoản, khoản mục, dự án, trung tâm chi phí từ dữ liệu xuất từ Junsky |
| `seed()` | 10 giao dịch giả | Kết quả đề xuất của lõi cho file vừa thả, theo cấu trúc ở mục 6 |
| `KB_RULES` | 7 quy tắc giả | Tri thức lõi đã học (chỉ đọc) |
| `startLoad()` và sự kiện `drop` | Giả lập tiến trình 10 bước | Đọc file thả vào (`e.dataTransfer.files`) hoặc file chọn qua hộp chọn file → tự nhận loại → gọi lõi → cập nhật `S.progress` theo tiến độ thật → báo lỗi chặn nếu thiếu dữ liệu nền |
| `saveDrawer()` | Lưu vào trạng thái | Nếu `remember = true`: gửi lõi ghi nhớ quy tắc theo số tài khoản đối ứng |
| `doExport()` | Tạo tên file giả | Ghi File soát (Excel) **chỉ gồm giao dịch `status = "dongy"`**, trả về đường dẫn thật; thêm một dòng vào lịch sử |
| `reloadSrc(k)` | Chờ 1,2 giây rồi báo xong | Nạp lại nguồn tương ứng; báo lỗi bằng một câu tiếng Việt kèm việc cần làm |
| `applyMoc()` | Đổi chữ trên thanh trên | Đổi mốc học của lõi |
| `'open-folder'`, `'open-file'`, `'add-bank'` | Chỉ hiện thông báo | Mở thư mục/file thật; thêm dòng ánh xạ TK ngân hàng |
| Tình trạng dữ liệu nền ở thanh trên | Ghi cứng “29/08/2026” | Lấy từ nguồn dữ liệu thật |

Phần mềm **không bao giờ tự nhập Junsky**. Lựa chọn “File nhập Junsky” trong hộp xuất file đang khóa, chỉ mở sau khi nhập thử thành công.

## 6. Dữ liệu một giao dịch

```text
id:        1
date:      "02/08/2026"                    // dd/mm/yyyy
dir:       "thu" | "chi"
amt:       55000                           // VND, số nguyên
desc:      "Thu phi SMS BDSD T7/2026"      // diễn giải gốc của ngân hàng
level:     "xanh" | "vang" | "do" | "junsky"
status:    "cho" | "dongy" | "boqua" | "junsky"
lines:     [ { side: "N" | "C", tk: "6427", amt: 50000, dt: "NH.MAU", da: "", km: "KM.PNH", cp: "TT.VP" }, … ]
why:       "5/5 chứng từ cũ giống nhất hạch toán Nợ 6427 + 1331 …"
basis:     [ { d: "02/06/2026", no: "02BP2606-0011", desc: "…", hk: "Nợ 6427 + 1331 / Có 1121" } ]
options:   [ { label, note, lines } ] | null      // mức Vàng: phương án 1, 2 (3)
chosen:    0                                     // phương án đang dùng
suggest:   [ { kind: "tk" | "dt", value: "331" } ] | null
sgTitle:   "TK hay gặp cho chi tiền:"
junskyNo:  "02BP2608-0012"                       // khi status = "junsky"
skipReason: ""
```

## 7. Quy tắc hành vi

- **Nút Đồng ý bấm được khi** thỏa cả ba điều kiện:
  - tổng Nợ = tổng Có và lớn hơn 0;
  - dòng nào cũng có tài khoản;
  - dòng có tài khoản công nợ thì có đối tượng.
  Danh sách tài khoản công nợ nằm ở hằng `DEBT_ACCOUNTS` = 131, 331, 141, 344, 1388, 3388. **Danh sách này chờ CFO xác nhận.**
- **Khi chưa đủ điều kiện**: nút Đồng ý mờ. Rê chuột thì hiện lý do. Bấm vào thì mở chi tiết giao dịch và báo lý do.
- **Sau khi Đồng ý**: dòng chuyển “Đã đồng ý” ngay. Thông báo có nút Hoàn tác hiện 6 giây. Con trỏ và phần chi tiết tự chuyển sang giao dịch chờ duyệt kế tiếp, trong phạm vi bộ lọc đang chọn.
- **Đồng ý hàng loạt**: chỉ gồm giao dịch mức Xanh, đang Chờ duyệt, khớp bộ lọc và đủ điều kiện. Luôn qua hộp xác nhận ghi rõ số giao dịch và tổng tiền.
- **Bỏ qua**: hỏi lý do nhưng không bắt buộc. Giao dịch đã bỏ qua không được xuất; muốn xử lý lại thì bấm “Duyệt lại”.
- **Đã có trong Junsky**: hiển thị mờ, ghi số chứng từ Junsky, không có nút Đồng ý và không bao giờ được xuất.
- **Ngăn Sửa**:
  - Nợ = Có được kiểm tra ngay khi sửa.
  - “Ghi nhớ cho lần sau” bật sẵn.
  - Mỗi bút toán tối thiểu 2 dòng.
  - Đóng bằng ✕, nút Hủy, phím Esc hoặc bấm ra ngoài ngăn.
- **Ô chọn có tìm kiếm**: tìm theo mã hoặc tên, gõ không dấu vẫn ra. Enter chọn kết quả đầu tiên, Esc đóng danh sách.
- **Phím tắt trong danh sách**: ↑/↓ chuyển giao dịch (đang mở chi tiết thì chi tiết đi theo), Enter mở/đóng, A đồng ý, E sửa, S bỏ qua. Phím tắt không chạy khi đang gõ trong ô nhập.
- **Tìm giao dịch**: tìm trong diễn giải và đối tượng (không phân biệt dấu); tìm số tiền khi gõ từ 3 chữ số trở lên.

## 8. Thành phần và trạng thái

| Thành phần | Trạng thái cần dựng |
|---|---|
| Thanh trên | Bình thường; mốc học cập nhật khi bấm Áp dụng |
| Menu trái | Thường · Rê chuột · Đang chọn · Tiêu điểm bàn phím |
| Vùng thả file | Trống · Kéo file đè lên · Đã nạp (thu gọn thành thẻ tóm tắt + nút “Thả file khác”) |
| Thẻ tóm tắt file | Số dư khớp ✓ · *Số dư lệch (chưa vẽ)* |
| Tiến trình đề xuất | Đang chạy · Xong (tự chuyển sang danh sách) · Lỗi chặn |
| Khối lỗi chặn | Tiêu đề + nguyên nhân + việc cần làm + nút sang màn hình xử lý + Thử lại |
| Ô tổng theo mức (×4) | Thường · Đang lọc · Rê chuột |
| Tiến độ duyệt + Xuất file | 0% · đang duyệt · 100% |
| Nút lọc (Mức, Trạng thái, Chiều) | Thường · Đang chọn |
| Ô tìm kiếm | Trống · Có chữ · Không có kết quả (khối “Xóa bộ lọc”) |
| Đồng ý tất cả dòng Xanh đang lọc | Có giao dịch (hiện số) · Không có (mờ) |
| Dòng giao dịch | Chờ duyệt · Con trỏ bàn phím · Đang mở · Đã đồng ý · Đã bỏ qua · Đã có trong Junsky |
| Nhãn mức | Đủ căn cứ · Cần xem · Thiếu căn cứ · Có trong Junsky (luôn có biểu tượng + chữ) |
| Bảng bút toán | Cân · Lệch · Ô thiếu (viền đỏ + chữ) · Ô không bắt buộc bỏ trống (—) |
| Khối “Vì sao” | Có căn cứ (nút xem) · Không có căn cứ · Bảng căn cứ đang mở |
| Thẻ phương án | Đang dùng · Phương án khác |
| Gợi ý điền nhanh | Hiện khi còn ô thiếu · Ẩn khi đã đủ |
| Ngăn Sửa | Hợp lệ · Chưa hợp lệ (nút Lưu mờ + lý do) |
| Ô chọn có tìm kiếm | Đóng · Mở · Đang lọc · Không có kết quả · Bắt buộc còn trống · Có giá trị (nút xóa) |
| Hộp đồng ý hàng loạt / Hộp bỏ qua | Một trạng thái mỗi hộp; có Hoàn tác sau khi thực hiện |
| Hộp xuất file | Cấu hình · Có cảnh báo còn chờ duyệt · Chưa có giao dịch đồng ý (nút Xuất mờ) · Đã xuất |
| Thông báo | Có Hoàn tác (6 giây) · Chỉ thông báo (4 giây) |
| Thẻ nguồn dữ liệu | Sẵn sàng · Cần bổ sung · Lỗi · Đang nạp |
| Mốc học | Hợp lệ · Sai định dạng |
| Thẻ tri thức | Có kết quả · Không có kết quả |
| Bảng lịch sử xuất file | Có dòng (mới nhất ở trên cùng) |

## 9. Màu và quy ước hiển thị

| Biến CSS | Mã | Dùng cho |
|---|---|---|
| `--chinh` / `--chinh-nen` | #1F4E9E / #E8EFFB | Nút chính, mục đang chọn, con trỏ bàn phím |
| `--xanh` / `--xanh-nen` / `--xanh-vien` | #17663E / #E6F4EC / #A9D8BD | Mức Xanh, Thu, Đã đồng ý, Nợ = Có |
| `--vang` / `--vang-nen` / `--vang-vien` | #7A4D00 / #FFF3D1 / #EBC870 | Mức Vàng, phương án, cảnh báo |
| `--do` / `--do-nen` / `--do-vien` / `--do-o` | #A8231A / #FDECEA / #F0B4AE / #C4321F | Mức Đỏ, lý do chặn, lệch Nợ/Có, viền ô thiếu |
| `--js` / `--js-nen` / `--js-vien` | #3B4553 / #EEF0F3 / #CDD2D9 | Đã có trong Junsky, Chi |
| `--chu` / `--chu-phu` / `--chu-nhat` | #17202B / #4A5463 / #5A6472 | Chữ chính / phụ / nhạt nhất (vẫn đạt tương phản 4,5:1) |

- **Ngày** viết dd/mm/yyyy.
- **Tiền** là VND, dấu chấm phân cách hàng nghìn, không có số lẻ, chữ số canh đều cột (tabular). Thu có dấu “+”, Chi có dấu “−”.

## 10. Còn chờ xác nhận / chưa làm

1. Danh sách tài khoản công nợ bắt buộc có đối tượng (`DEBT_ACCOUNTS`).
2. Chưa vẽ trạng thái “Số dư đầu–cuối lệch” và “File không nhận được”.
3. Chưa nối hộp chọn file thật: bấm vào vùng thả file hiện chỉ giả lập việc nạp file.
4. Người duyệt trong lịch sử đang ghi “Bạn”. Cần lấy từ người dùng đăng nhập (nếu ứng dụng có đăng nhập).

## 11. Gợi ý câu lệnh cho phiên Cowork

> Đây là bản bàn giao giao diện màn hình Định khoản (`dinh-khoan-prototype.html` + `BAN-GIAO-dinh-khoan.md`). Hãy đọc tài liệu bàn giao, rồi dựng lại giao diện này vào phần mềm hiện có và nối với phần lõi đề xuất bút toán theo bảng “Chỗ cần nối phần lõi”. Giữ nguyên quy tắc: không tự nhập Junsky; chỉ giao dịch “Đã đồng ý” mới được xuất.


