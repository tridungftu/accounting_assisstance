**BIÊN BẢN REVIEW CHÉO CORE v1.0 — 30/10/2026**

**Kết luận: Cần sửa.** Kiểm mẫu **24 khẳng định: 22 Đúng, 1 Sai, 1 Thêm mới; tỉ lệ đúng 91,7%**. Không phát hiện dữ liệu thật trong hai chuẩn; không có phát hiện mức **Chặn**.

Chỉ review tĩnh các tài liệu được giao; không sửa file, chạy ứng dụng, kết nối CSDL hoặc đọc kho thật, tệp bí mật, `*.local.json`.

Quy ước căn cứ, số sau dấu `:` là dòng: **C** = [chuẩn CSDL](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/docs/47-core/chuan/CHUAN-CORE-CSDL-v1.0.md>); **A** = [chuẩn API](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/docs/47-core/chuan/CHUAN-CORE-API-v1.0.md>); **D** = [đặc tả CSDL](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/docs/47-core/g1/DAC-TA-CSDL.md>); **O** = [đặc tả API/OpenAPI](<D:/Claude/Phan mem ho tro ke toan/Phần mềm kho tri thức/docs/47-core/g1/DAC-TA-API.md>); **PC/PA** = hai phiếu duyệt CSDL/API; **R** = `g1/ANH-XA-ROUTE.md`.

**Bảng phát hiện**

| Phát hiện | Mức | Căn cứ và yêu cầu sửa |
|---|---|---|
| **Thêm mới tên cột migration:** `nguoi_ap_dung`, `nguon_lich_su`. | **Cần sửa** | C:438 ấn định hai tên kỹ thuật; D:151,405 chỉ nêu “người áp dụng”, “nguồn lịch sử”, chưa định nghĩa tên cột. Giữ mô tả ý nghĩa hoặc bổ sung căn cứ đã duyệt cho tên chính xác. |
| **Tên path parameter chưa khớp đúng chữ:** `GET /api/v1/module/{ma}`. | **Cần sửa** | A:69 dùng `{ma}`; O:800 dùng `{ma_module}`; chính A:651 cũng dùng `{ma_module}`. Đồng bộ tên template. |
| **Giới hạn upload chưa thống nhất đơn vị giữa nguồn duyệt và OpenAPI.** | **Cần sửa** | A:416 khớp PA:91: **20 MB**. O:140 ghi **20 MiB**; O:1781,2484 ghi **20.971.520 bytes**. Nếu MB theo hệ thập phân thì giới hạn là 20.000.000 bytes. Cần thống nhất số byte theo quyết định được duyệt; không tự đổi lựa chọn 2A. |
| **Ví dụ CAS `mau_demo` chưa thể xác nhận khớp route OpenAPI nguồn.** | **Cần sửa** | A:890 dùng `/module/mau_demo/bao-gia/{id}`; O:1378 chỉ khai `/module/crm/bao-gia/{id}`. Ba body phù hợp schema CRM, nhưng route mẫu chưa có khai báo OpenAPI tương ứng. Cần chỉ rõ ánh xạ schema và khai báo method/path của mẫu. |
| **Dẫn chiếu “§8 OpenAPI” không có đích tương ứng.** | **Gợi ý** | A:996; O:437 đặt tên **“Phụ lục — openapi-v1.yaml”**, không có mục §8. Sửa tên dẫn chiếu. |

**Kiểm mẫu khẳng định**

| # | Khẳng định trong chuẩn | Kết quả | Đối chiếu |
|---:|---|---|---|
| 1 | Core sở hữu `loi`, `loi_tai_lieu`, `danh_muc` | Đúng | C:46–48 ↔ D:45–47 |
| 2 | Module sở hữu phần riêng, công bố qua `cong_bo_*` | Đúng | C:49–50 ↔ D:48–56 |
| 3 | Engine/máy phụ không có login CSDL | Đúng | C:162 ↔ D:271 |
| 4 | Membership PG16: `INHERIT TRUE, SET FALSE, ADMIN FALSE` | Đúng | C:172 ↔ D:274 |
| 5 | RLS/FORCE RLS, kiểm `USING` và `WITH CHECK` | Đúng | C:254 ↔ D:289,312 |
| 6 | CSDL xác minh mã bí mật, không tin GUC tự khai | Đúng | C:201–242 ↔ D:135,310,332–334; PC:85 |
| 7 | Kiểm đủ hai giới hạn tiền, gồm dòng bị che | Đúng | C:278–295 ↔ D:318–320 |
| 8 | Liên kết và kiểm tiền cùng transaction/kết nối | Đúng | C:303–312 ↔ D:387 |
| 9 | Không FK chéo module; ghim ID và mã băm | Đúng | C:330–347 ↔ D:250–251,387 |
| 10 | Khóa mã hóa không truyền qua GUC/SQL, kể cả bind | Đúng | C:419 ↔ D:354 |
| 11 | Bảo toàn checksum; runtime không tự migrate | Đúng | C:443–449 ↔ D:409,432 |
| 12 | Hạn tạm 24 giờ/7 ngày; số đo 90 ngày/1 năm | Đúng | C:485–491 ↔ PC:48,80 |
| 13 | Core tự quản tài khoản; nhân sự thật chờ Anh | Đúng | C:512,522 ↔ PC:81,87 |
| 14 | Cookie an toàn, Origin/CSRF, TLS ngoài loopback | Đúng | A:83–115 ↔ O:41–46 |
| 15 | Cấu trúc lỗi và 12 mã lỗi được sử dụng | Đúng | A:184–238,307–308,515–539 ↔ O:68–98,114–115,243–253 |
| 16 | Tám trạng thái việc; mất heartbeat → `interrupted` | Đúng | A:369–388 ↔ O:134–136,2045–2052 |
| 17 | Biên nhận module bất biến, vĩnh viễn, cùng transaction | Đúng | A:278–292 ↔ O:109–111 |
| 18 | `row_version` là chuỗi; CAS lệch trả 409 | Đúng | A:319–333 ↔ O:118–120 |
| 19 | Phân trang mặc định 25, tối đa 100; cursor 15 phút | Đúng | A:341–349 ↔ O:124 |
| 20 | Module đóng sau 5 phút rảnh | Đúng | A:501 ↔ PA:90 |
| 21 | Bảng route Core §3.12 khớp method/path OpenAPI | Đúng | A:627–689: **40/40 operation** |
| 22 | Phân loại chuyển tiếp `T/T*/D/N/S/B` | Đúng | A:728–733 ↔ R:60–65 |
| 23 | Template metadata module khớp đúng chữ | **Sai** | A:69 ↔ O:800: `{ma}` / `{ma_module}` |
| 24 | Hai tên cột metadata migration đã được nguồn định nghĩa | **Thêm mới** | C:438 ↔ D:151,405 |

**Ví dụ, checklist và dữ liệu**

- **JSON:** `JSON.parse` đạt **12/12** đoạn có JSON: 8 body HTTP, 3 snippet API và 1 snippet CSDL.
- **OpenAPI:** 5 body HTTP của các route Core phù hợp các schema `TaoTaiLieu`, `TaiLieu`, `LenhOcr`, `DaNhanViec`, `Viec`; header và status mẫu phù hợp. Ba body CAS phù hợp `LuuGhiChuBaoGia`, `GhiChuBaoGia`, `Loi`, còn thiếu xác nhận route như phát hiện trên. JSON CSDL là minh họa dữ liệu riêng, chưa gắn operation/schema cụ thể.
- **Checklist:** **68/68 mục** — mỗi chuẩn 34 mục — có thể kiểm bằng catalog/schema, test tình huống hoặc review bằng mắt khi đọc cùng quy tắc tương ứng. Đây là đánh giá tính kiểm được, chưa phải kết quả thực thi checklist.
- **Tên kỹ thuật:** 12 mã lỗi, 8 trạng thái việc, 6 trạng thái tiến trình và 4 trạng thái contract khớp nguồn. Tên khối/bảng/role đối chiếu không phát hiện lệch ngoài phần tên cột nêu trên.
- **Dữ liệu thật:** không phát hiện trong hai chuẩn; ví dụ dùng UUID, tên miền và token giả.

**Kết luận cuối: Cần sửa** các điểm về tên kỹ thuật, route mẫu và tính nhất quán giới hạn upload trước khi xác nhận hai chuẩn khớp đầy đủ nguồn đã duyệt.