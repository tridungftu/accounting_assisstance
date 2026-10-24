# Nguồn vay Code final — xác định cách lấy dữ liệu sẵn có

**19/10/2026 · STATIC_READ_ONLY · chưa kết nối/chạy/xuất dữ liệu thật.** Anh cấp đúng source tại `D:\Claude\Phan mem theo doi khoan vay\Code final` và chốt: **chỉ xác định cách lấy dữ liệu; việc theo dõi khoản vay nằm ở ứng dụng này; không điều chỉnh code**. Báo cáo không giao sửa/tái triển khai M9 hoặc làm lại engine vay/lãi.

**Đường lấy phù hợp nhất từ code đang có: cặp JSON + Excel do chính giao diện nguồn xuất trong cùng phiên, cùng mốc số liệu và phạm vi quyền.** JSON giữ dữ liệu gốc/native keys; Excel đã gọi engine nguồn để đưa dư nợ/lãi/lịch tại mốc ra file. Chỉ Sheets raw hoặc JSON raw riêng lẻ không thay thế toàn bộ kết quả tính sẵn đó.

| File nguồn đã đọc cấu trúc | Bytes / dòng / named function declarations | SHA256 |
|---|---:|---|
| `COde gs- Vay -final.txt` | 389.343 / 5.305 / 322 | `2c29a5a6b099fb907f0ee65e52ff7c9fbef1757e17cb1c53b477b1220cddba89` |
| `giaodienhtml.txt` | 666.197 / 6.465 / 242 | `0108badae4f44a3bdb39f5a19757374c16e0900c70ed073f95a6d5d9f26b1a9e` |

Đọc bằng metadata function/call graph và đoạn đã che string/comment literals; không trích payload, tên thật, tài khoản, URL/ID hoặc credential hardcode. Không sao chép code gốc vào repo/tài liệu/Claude. Không đọc `.env/.clasp`, không execute/import source, Apps Script, Google, SQL, test hoặc deploy. Hash cả hai file trước/sau audit khớp; không suy hash source là hash deployment thật.

## 1. Cách giao diện hiện tại lấy dữ liệu

| Điểm source hiện có | Input/output thực và ý nghĩa cho việc đọc |
|---|---|
| Backend `doGet():122` | Dựng HTML. Không tìm thấy declaration `doPost` trong source mới; chưa có căn cứ coi URL web app là JSON HTTP `/load` endpoint |
| UI `goi(fn,...args):765–804` | Gọi `google.script.run[fn](...args)` trong trang Apps Script; một số mutation dùng wrapper `goiRoiTai`. Đây là RPC của giao diện, không phải REST public được chứng minh |
| Backend `dangNhap_:579–630`, `kiemTra_:734–752` | Token phiên do login tạo; backend nạp user/quyền/phạm vi. Token không phải Google OAuth token. Không ghi token/password vào URL, chat, tài liệu hoặc adapter fixture |
| UI `taiLai:926–952` → backend `taiDuLieuNhanh(token,kieu):1179` | UI gọi tên `taiDuLieuNhanh`, token phiên và selector `gon` tại `:932`; nhận JSON string, JSON.parse rồi `napDuLieu:1018`. Selector này đi qua `taiDuLieuGon_(token,null):1188` lấy full compact; lựa chọn khác về `taiDuLieu(token):826` |
| Backend `taiDuLieu:826` → `gomDuLieu_:834–890` | Trả object chứa chín bảng dữ liệu bên dưới, master/config/user/phạm vi và metadata. Các bảng đã lọc quyền phần ngắn/dài hạn và công ty/khoản được phép; không nạp toàn response/user/account/config vào kế toán |
| `goiGon_:1134–1144`, `taiDuLieuGon_:1188–1210` | Compact table là `{c:[tên_cột],r:[[giá_trị]]}`, `gonBang=1`; response tăng dần có `gon/bang/ver`. UI giải compact, merge phần thay đổi vào cùng user. Thiếu bảng ở delta không phải bảng rỗng/xóa; phải có full baseline đúng phiên |
| Backend `maPhienBan(token):1212`, UI `napDuLieu:1018` | Có version-map/hỗ trợ refresh. Chưa chứng minh là snapshot toàn bộ bảng đồng thời hoặc lịch sử as-of có authority; không tự lấy version-cache/fetch time làm nghiệp vụ |

Chín nhóm dữ liệu actual: `HopDongMua`, `VayNganHan`, `TraNoNH`, `HanMuc`, `HDTD`, `KheUoc`, `LichGoc`, `LaiSuat`, `PhatSinh`. Native keys/joins hiện thấy gồm `maHDM/id/hdmDongId`, `vayId`, **`maHDTD/maKU`**. Đây là shape khác nguồn cũ `longLoans/lichGoc/...` và `maKV/maKheUoc`; không áp nguyên old adapter/profile. Chỉ xác định profile/mapping đọc mới, không thay khóa hoặc mô hình của ứng dụng nguồn.

## 2. Dữ liệu lưu sẵn và kết quả engine hiện có

Lịch gốc nằm trong `LichGoc`; lần trả ngắn hạn trong `TraNoNH`, phát sinh dài hạn trong `PhatSinh`; khế ước và mức/lịch lãi suất nằm trong `KheUoc/LaiSuat`. Dư nợ tại mốc và các kỳ lãi/kết quả dự tính được **giao diện nguồn tính**, không phải một bảng output tương đương đã được chứng minh lưu sẵn trong Sheets.

Các điểm reuse đã thấy: UI `nganHan(D):1194` gọi `vayTaiMoc`; `daiHan(D):1380` gọi `tinhHDTD`; `laiHDTD(h,D):1588` tạo nhóm/kỳ/kết quả lãi. Chỉ ghi nhận nơi lấy output, không review hay sửa công thức này. Field statement như `duNoSaoKe/ngaySaoKe` không tự coi bằng computed `duNo(D)`.

| Đầu ra sẵn có | Chính xác lấy được gì / giới hạn |
|---|---|
| UI `xuatJSON():6210–6216` | Từ dữ liệu `S.d` đã nạp, xuất chín raw arrays + `DanhMuc`, metadata `app/xuatLuc/soLieuDen/nguoiXuat`. Giữ native fields/IDs trong object; không gọi server trong hàm xuất. Không có toàn bộ computed dư nợ/lãi; `xuatLuc` là giờ xuất, `soLieuDen` là mốc đang chọn, không chứng minh freshness/as-of của mọi row |
| UI `xuatExcel():6262–6330` | Từ `S.d` và mốc `S.moc`, gọi engine nguồn; có trả gốc/dư nợ ngắn hạn (`:6285–6289`), tổng giải ngân/trả gốc/dư nợ/kỳ tới và lãi dài hạn (`:6298–6299`), cùng raw khế ước/lịch gốc/lãi suất/phát sinh (`:6317–6324`). Gọi `sheetLaiCongThuc:6219–6261` ở `:6327`; có sheet công thức, chưa kiểm file bytes/cached values thực |
| Phạm vi export Excel | `co(phan)` tại `:6269` phụ thuộc quyền và tab đang chọn; nhánh `:6297` có thể xuất sớm trước phần dài hạn. Không mặc định một file chứa đủ ngắn+dài hạn chỉ vì hàm tên “Excel”. Phải ghi tab/quyền/mốc/file nhận thực |

Excel có một số bảng trình bày/tổng hợp không giữ đủ native IDs như JSON. Vì vậy cặp file cùng phạm vi giúp lấy **kết quả nguồn** đồng thời giữ tham chiếu row gốc; bên nhận không tự tính lại lãi/dư nợ để bù output thiếu. Hạn chế scope/key liên kết phải được xác minh bằng file DEMO thực sau khi có kết nối, không tự coi ghép tên/số hợp đồng là duy nhất.

## 3. Hai đường tiếp nhận, không sửa ứng dụng

1. **Ưu tiên dùng export hiện có:** lấy JSON + Excel từ phiên nguồn đã tải đúng dữ liệu, cùng mốc và đúng tab/phạm vi; lưu local raw bytes/hash/thời điểm nhận và metadata xuất. Phần kế toán chỉ đọc/mapping/provenance/soát liên kết. Chưa bấm nút hoặc tạo file trong audit này; cần xác định deployment đang dùng hai file mới và nhận mẫu DEMO không rỗng để khóa cột/keys/output.
2. **Nếu cần tự động:** reuse RPC/read/export của chính app hiện có sau khi xác minh deployment/quyền/phiên, thay vì dựng máy tính lãi mới. Chưa có API HTTP readonly chuyên dụng được chứng minh; Apps Script RPC gắn giao diện/auth, không được coi là endpoint server-to-server chỉ từ tên function. Sheets API readonly chỉ là đường lấy **raw đã lưu**; không đủ computed outputs nêu trên nên không chọn làm phương án thay thế trọn luồng nếu phải viết lại phép tính.

**Điều phải kiểm trước bất kỳ live read mới:** các tên `taiDuLieu/kiemTra` không bảo đảm call graph chỉ đọc. `kiemTra_:742` có thể gọi `damBaoTaiKhoan_:373–402` để tạo/nâng cấp sheet/cột/quyền; login có cập nhật account/trạng thái password, session và audit (`:594–626`). Đường read cũng có CacheService/metadata/version cache. Không tự gọi đăng nhập/load/ensure/setup để “thử đọc” khi chưa xác định side effects và quyền hiện trạng. Export từ state đã nạp không đồng nghĩa toàn hành trình mở/đăng nhập/load không ghi.

Thông tin còn cần cho đường dùng thật: bản deploy/Sheet instance được Anh dùng, người/phạm vi có quyền đọc, cách nhận cặp export đúng mốc và khả năng lấy đủ raw+computed outputs. Mọi URL/ID/token/credential chỉ ở cấu hình/phiên cục bộ có quyền, không gửi chat/Claude. Chưa kết nối Google, chưa chứng minh export chạy được, chưa có runtime acceptance và **không có lệnh resume/sửa M9**.

Nguồn final khác nguyên bytes với root `Code.gs` cũ (`98774668…38db`) và deploy `Code.js` cũ (`593d6ba8…d8f4`), UI cũ (`767f1f17…e6b7`). Old source catalog/binding là căn cứ lịch sử; hợp đồng đọc phải pin source mới và actual output, không tiếp tục triển khai tracking theo schema cũ.
