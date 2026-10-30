# ENGINE-2 — Bản giao việc `e_trich_xuat` — v1.0

**Ngày Anh duyệt các quyết định Core làm căn cứ:** 30/10/2026.  
**Căn cứ:** CD-026, CD-028, CD-031…CD-036; CD-011 ngày 26/10/2026; `docs\47-core\PHIEU-DUYET-CSDL.md` — 1A, 2A, 3A; `docs\47-core\PHIEU-DUYET-API.md` — 1A, 2A.  
**Trạng thái:** chỉ tài liệu. Phiếu SDK bản 2 **chờ Anh**; chỉ bắt đầu lập trình khi có CD mở lại.

## Thay đổi

- **v1.0:** bản đầu; giao phạm vi bọc nguồn trích xuất hiện có, không thay thuật toán.

## Kết luận

1. Bọc phần `trich_xuat` của phần mềm review xây dựng: 37 tham số, cấu trúc hợp đồng, dẫn chứng và kiểm tra kết quả.
2. Capability đích: `trich.tham_so_hop_dong@1`, `trich.bang@1`.
3. Local AI đi qua cổng AI phần mềm; không mở đường Cloud trực tiếp.
4. Bản review gốc đóng băng theo CD-011: chỉ đọc, không sửa.
5. E1-MUA có bản vá danh mục theo loại; chưa chứng minh đã triển khai vào nguồn.
6. Chỉ công bố capability, loại hợp đồng và định dạng đã có bằng chứng chạy đạt.

## Bắt buộc

### Contract vào/ra

| Capability | Đầu vào | Đầu ra và giới hạn |
|---|---|---|
| `trich.tham_so_hop_dong@1` | `tham_chieu_tep.v1`; lệnh Core có `tai_lieu_id`, `tep_id`, `loai`, `danh_muc_phien_ban` | `tham_so.v1`: giữ loại, danh mục/hash, giá trị đã định kiểu hoặc lý do chưa xác định, dẫn chứng và tham chiếu phản hồi nguồn. |
| `trich.bang@1` | Tệp hoặc kết quả nguồn được Core cấp quyền; dùng lại bộ đọc bảng hiện có | Đích kỹ thuật `du_lieu_bang.v1`; giữ hàng/cột, ô gộp, vị trí và cảnh báo nguồn. OpenAPI hiện chưa khai lệnh `trich.bang@1`; phần lệnh bổ sung **chờ Anh**, không tự tạo route/schema cạnh tranh. |

Phản hồi nguồn phải được giữ để không mất `ghi_chu`, `kiem_tra`, `dieu_khoan`, `trich_dan`, `vi_tri_do_duoc`. Không suy giá trị chưa rõ thành `0`, tiền hoặc ngày.

### Nguồn chính thức và cách dùng lại

Quy ước **X** = `D:\Claude\Ho tro review ho so xay dung\review_xaydung`; đường dẫn không có tiền tố X tính từ repo hiện tại.

| Phần | Dùng lại nguyên / bọc / sửa / viết mới |
|---|---|
| Danh mục và lõi trích | **Dùng lại nguyên, bọc:** `X\trich_xuat\danh_muc.py:149`, `:186`; `X\trich_xuat\quy_trinh.py:91`, `:272`. Giữ thuật toán, prompt và test gốc. |
| Đọc hợp đồng | **Dùng lại nguyên:** `X\trich_xuat\doc_hop_dong.py:296`, `:453`. Không kích hoạt nhánh Word COM; không tự nhận mọi định dạng là đã hỗ trợ. |
| Local AI | **Bọc seam AI** của `TrichXuat(..., ai=...)`, `X\trich_xuat\quy_trinh.py:92`; chuyển qua cổng AI phần mềm. Không gọi trực tiếp client mạng tại `X\trich_xuat\ai_local.py:61`. |
| Danh mục E1-MUA | **Đối chiếu, dùng lại:** `tools\source6_g5_e5\trich_xuat\danh_muc.py:287`, `:307`. Có XD, DV, MUA_HH, THUE_TS, NHAP_KHAU; DV_KY/DV_1L chỉ chọn tường minh. Không áp bản vá vào X. |
| Adapter và vận hành | **Viết mới chỉ phần cần thiết:** chuyển contract, khung nhận cổng/sẵn sàng/dừng và tích hợp Core; nguồn cũ chưa đáp ứng giao thức Core. **Sửa nguồn gốc: không.** |

Common API hiện có chỉ chạy `RULE_ONLY`, không AI/Cloud/OCR; không coi đó là bằng chứng luồng Local AI đã tích hợp. E1-MUA chưa xác nhận triển khai: **chờ Anh**. Không fallback sang XD khi thiếu/sai loại hoặc danh mục.

### Khung chạy và thứ tự lát

Engine chạy bằng tài khoản Windows hạn chế, khác Core; không có login CSDL, không giữ mật khẩu/khóa, không đọc kho bí mật. Core cấp/giữ/nhả cổng; xác minh instance, phiên bản, capability và readiness trước phục vụ; drain, bàn giao kết quả trước dừng. Core ghi số đo khởi động, xử lý, thời gian rảnh, RAM/CPU; chỉ Admin áp dụng thay đổi chế độ chạy.

Codex làm chính; mỗi lát tối đa **3 tệp đích**, gồm test:

1. Bọc lõi và ánh xạ `tham_so.v1`; giữ đối chiếu 37 tham số XD.
2. Bọc bảng và danh mục theo loại đã được xác nhận; giữ phần chưa đủ contract ở trạng thái chờ.
3. Ghép khung tiến trình, manifest và kiểm vận hành Core.

Lead chốt danh sách đường dẫn được sửa trước khi giao code; không tự mở rộng whitelist. Nếu buộc phải chép code, ghi nguồn, SHA256 và phiên bản bản gốc theo CD-036.

## Khuyến nghị

Không bổ sung lựa chọn thiết kế trong bản giao việc này; các phần chưa đủ bằng chứng giữ trạng thái chờ.

## Module được làm / không được làm

- **Được:** `mau_demo` dùng tệp giả, gửi yêu cầu qua Core và đọc kết quả theo quyền; ví dụ hợp đồng XD giả phải khai rõ `loai=XD` và phiên bản danh mục.
- **Không được:** gọi thẳng cổng engine/AI, tự duyệt kết quả, sinh nghĩa vụ nghiệp vụ trong engine, sửa X hoặc mở `X\co_so_du_lieu\*.db`.

## Checklist trước khi nộp gói

- [ ] Có CD mở lại, whitelist tệp và phiên bản contract được phép dùng.
- [ ] Test gốc liên quan tại `X\tests\test_trich_xuat.py:97`, `:313` đạt qua engine với cùng dữ liệu giả; không dùng ca hợp đồng thật.
- [ ] Kiểm loại/danh mục/hash, dẫn chứng, dữ liệu thiếu và bảng; không fallback hoặc mất trường nguồn.
- [ ] Kiểm cổng, readiness, tài khoản hạn chế, bàn giao/dừng, retry và việc bị gián đoạn.
- [ ] Không thêm lỗi so với `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md`; báo đạt/tổng, lỗi mới, phần chưa kiểm và rủi ro.

## Phụ lục — đặc tả chi tiết

- `docs\47-core\g1\DAC-TA-API.md` §2.6, §4, OpenAPI `LenhTrich`.
- `docs\47-core\g1\DAC-TA-SDK.md` §4, §6.2 — đặc tả SDK, toàn phiếu bản 2 **chờ Anh**.
- `docs\47-core\g1\CONTRACT-DU-LIEU.md` §6, §7, §13, §15 và bộ kiểm tuân thủ.
- `docs\47-core\g0\KS-D.md` §3.2; `docs\GIAO-CODE-E1-MUA-DANH-MUC-THAM-SO-THEO-LOAI.md` — đối chiếu hiện trạng E1-MUA; không dùng để vượt lệnh đóng băng.

---

# ENGINE-2 — Bản giao việc `e_hoa_don` — v1.0

**Ngày Anh duyệt các quyết định Core làm căn cứ:** 30/10/2026.  
**Căn cứ:** CD-026, CD-028, CD-031…CD-036; `docs\47-core\PHIEU-DUYET-CSDL.md` — 1A, 2A, 3A; `docs\47-core\PHIEU-DUYET-API.md` — 1A, 2A.  
**Trạng thái:** chỉ tài liệu. Phiếu SDK bản 2 **chờ Anh**; chỉ bắt đầu lập trình khi có CD mở lại. Gọi cổng thuế thật cần **lệnh riêng của Anh**.

## Thay đổi

- **v1.0:** bản đầu; giao phạm vi bọc bộ tải hóa đơn và bộ đọc XML/ZIP hiện có.

## Kết luận

1. Capability đích: `hoa_don.tai_cong_thue@1`, `hoa_don.doc_xml@1`, `hoa_don.doc_zip_bang_ke@1`.
2. Dùng lại bộ tải tại nguồn chính thức và parser XML/ZIP trong repo.
3. Mặc định chỉ chạy với tệp mẫu; không đăng nhập hoặc gọi cổng thuế thật.
4. Bộ đọc hiện chỉ hỗ trợ profile DEMO strict, không phải mọi XML thuế.
5. `hoa_don.v1` là kết quả đọc; không chứng minh hợp lệ thuế, đủ kỳ hoặc đã hạch toán.
6. Bộ tải nguồn khác protocol bản vá M2-00; không coi hai bản là tương thích sẵn.

## Bắt buộc

### Contract vào/ra

| Capability | Đầu vào | Đầu ra và giới hạn |
|---|---|---|
| `hoa_don.doc_xml@1` | `tham_chieu_tep.v1`; lệnh có `tep_id`, `ho_so_doc` đã đăng ký; Core cấp bytes/context hợp lệ | `hoa_don.v1`, kèm tham chiếu XML và chi tiết nguồn; giữ profile, hash, vấn đề và trạng thái đọc. |
| `hoa_don.doc_zip_bang_ke@1` | Tham chiếu ZIP, `tep_id`, `ho_so_doc`; context theo từng nguồn | Giữ từng entry, coverage, lỗi và hóa đơn đọc được. Báo cáo ZIP chuẩn chỉ công bố sau khi đủ schema/bằng chứng; phần còn thiếu **chờ Anh**, không tự đặt vỏ JSON mới. |
| `hoa_don.tai_cong_thue@1` | `nguon_id`, `tu_ngay`, `den_ngay`, `huong=mua_vao\|ban_ra`; Core kiểm nguồn thuộc pháp nhân | Tệp tải được bàn giao thành tham chiếu Core; việc được theo dõi qua `viec.v1`. Đăng nhập/CAPTCHA có thể cần `waiting_input`; không coi tải xong là đã đọc hoặc nhận nghiệp vụ. |

Giữ số hóa đơn dạng chuỗi, decimal chính xác, số `0` đầu, dữ liệu thiếu và lỗi nguồn. Không suy tiền tệ/số lượng/thuế suất, không cộng dòng để tự thay tổng nguồn. XML/ZIP và JSON chi tiết nguồn có tham chiếu riêng.

### Nguồn chính thức và cách dùng lại

Quy ước **H** = `D:\Claude\Phan mem download hoa don`; đường dẫn không có tiền tố H tính từ repo hiện tại.

| Phần | Dùng lại nguyên / bọc / sửa / viết mới |
|---|---|
| Tải và phiên cổng thuế | **Dùng lại nguyên, bọc:** `H\src\job.js:75`, `:96`; `H\src\portal.js:27`, `:223`, `:251`. Giữ thuật toán; mặc định dùng giả lập, không thực hiện kết nối thật. |
| Bảng kê/xuất nguồn | **Dùng lại nguyên:** `H\src\build.js:18`. Không dùng parser phục vụ hiển thị/PDF thay parser strict của contract. |
| Đọc XML/ZIP | **Dùng lại nguyên, bọc:** `src\kho_tri_thuc\nguon\hoa_don_xml.py:1183`, `:1191`, `:618`; wrapper có sẵn `src\kho_tri_thuc\ha_tang\engine_hoa_don.py:109`. Wrapper hiện chưa bọc tải cổng thuế. |
| Adapter và vận hành | **Viết mới chỉ phần cần thiết:** ánh xạ contract, nhận cổng/sẵn sàng/dừng và bàn giao Core. **Sửa nguồn gốc: không**, trừ khi Anh cho phép riêng. |

Không khởi chạy nguyên trạng `H\src\server.js`: nguồn này nạp `.env` tại dòng 5, có trạng thái tải RAM toàn cục và giao diện riêng. Adapter không đọc `.env`, không đưa mật khẩu/token vào manifest, dòng lệnh, log hoặc kết quả. Không mặc định nguồn H hỗ trợ owned protocol của `tools\source7_m2_patch`.

Parser có giới hạn riêng tại `hoa_don_xml.py:61`: XML 16 MiB, ZIP 64 MiB, 1.000 entry. Đây không phải quyền nâng giới hạn upload Core đã duyệt **20 MB**; áp giới hạn nhỏ hơn của đường tiếp nhận và capability.

### Khung chạy và thứ tự lát

Engine chạy dưới tài khoản Windows hạn chế, khác Core; không login CSDL hoặc đọc kho bí mật. Core quản lý cổng, danh tính instance, readiness, việc lâu, bàn giao và drain; ghi số đo khởi động/RAM/CPU. Không dùng `/api/config` nguồn làm bằng chứng đã sẵn sàng tải.

Codex làm chính; mỗi lát tối đa **3 tệp đích**, gồm test:

1. Bọc parser/wrapper hiện có sang `hoa_don.v1`, kiểm bảo toàn chi tiết nguồn.
2. Bọc bộ tải và bảng kê bằng giả lập; đối chiếu protocol, phiên và kết quả bàn giao.
3. Ghép manifest, khung tiến trình và kiểm vận hành Core.

Lead chốt đường dẫn được sửa trước giao code. Nếu bắt buộc chép code, ghi nguồn, SHA256 và phiên bản bản gốc. Không viết lại thuật toán tải hoặc parser.

## Khuyến nghị

Không bổ sung lựa chọn thiết kế trong bản giao việc này; schema/phạm vi chưa đủ căn cứ giữ trạng thái chờ.

## Module được làm / không được làm

- **Được:** `mau_demo` đưa XML/ZIP giả qua kho tệp Core, gọi capability đọc và xem issues/coverage theo quyền.
- **Không được:** gọi trực tiếp engine/cổng thuế, truyền credential từ frontend, ghi bảng M2 từ engine, tự xác nhận hợp lệ thuế, đủ kỳ hoặc đã hạch toán. Lệnh mở lại lập trình không thay lệnh riêng cho cổng thuế thật.

## Checklist trước khi nộp gói

- [ ] Có CD mở lại, whitelist tệp, profile và contract được phép dùng.
- [ ] Test gốc `H\test\test.js` đạt với dữ liệu giả qua phần bọc tương ứng; không gọi cổng thuế.
- [ ] `tests\test_hoa_don_xml.py`, `tests\test_xs3_hoa_don.py` đạt; kiểm XML hỏng, namespace/profile lạ, ZIP lỗi/CRC/trùng tên/partial và thiếu context.
- [ ] Giữ nguyên decimal, định danh, hash, entry/coverage, issues và trạng thái chưa xác định; không báo thành công toàn bộ khi nguồn chỉ đọc được một phần.
- [ ] Kiểm tài khoản hạn chế, cổng/readiness, chống chạy trùng, bàn giao/dừng; restart không tự biến việc dở thành xong hoặc tải lại mù.
- [ ] Không thêm lỗi so với `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md`; báo đạt/tổng, lỗi mới, phần chưa kiểm và rủi ro.

## Phụ lục — đặc tả chi tiết

- `docs\47-core\g1\DAC-TA-API.md` §2.6, §4, OpenAPI `LenhDocHoaDon`, `LenhTaiHoaDon`.
- `docs\47-core\g1\DAC-TA-SDK.md` §4, §6.2 — đặc tả SDK, toàn phiếu bản 2 **chờ Anh**.
- `docs\47-core\g1\CONTRACT-DU-LIEU.md` §10, §13, §15 và bộ kiểm tuân thủ.
- `docs\47-core\g0\KS-D.md` §3.2 — khác biệt bộ tải nguồn/M2-00 và giới hạn parser.
- `docs\M2-PROFILE-XML-DEMO-01.md` — profile XML DEMO hiện có.