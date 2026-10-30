# ENGINE-2 — Lát giao được ngay / Lát chờ Anh

| Engine | Lát giao được ngay | Lát chờ Anh |
|---|---|---|
| `e_trich_xuat` | TRICH-1a/1b, TRICH-3a/3b và TRICH-4 đo độ chính xác trước/sau: **giao được theo CD-038 câu 1C/3A**; chép có sửa vào gói engine, dùng mẫu cổng AI chung. | TRICH-2a `trich.bang@1`: chưa hỗ trợ, chờ bằng chứng nguồn/test và contract; TRICH-2b E1-MUA: chờ Anh cho phép bản chép có vá riêng, không sửa X. |
| `e_hoa_don` | HD-1, HD-2a/2b/2c, HD-3a/3b: **giao được theo CD-038 câu 2A/3A**; phiên Windows riêng có màn hình, tài khoản riêng, profile từng pháp nhân/phiên, mật khẩu từ két Core. | Phần ZIP chưa đủ schema chờ Anh duyệt; gọi cổng thuế thật vẫn cần lệnh riêng của Anh. |

“Giao được” là không còn bị ba câu hỏi đã chốt tại CD-038 chặn; SDK bản 2 đã duyệt, chỉ mở lập trình khi chuẩn SDK v1.0 xong và Opus review theo CD-038; lead khóa whitelist ≤3 tệp/lát gồm test. Lượt này **chỉ sửa tài liệu, không lập trình**. Lát giả lập không được coi là capability tải/AI thực đã sẵn sàng. Thứ tự tích hợp **e_mask → e_hoi_ai → e_trich_xuat**; giữ phụ thuộc schema/bằng chứng khác, không chặn các lát độc lập. Engine giữ bí mật (Mask, AI Cloud, tải hóa đơn, ABBYY) mỗi engine một tài khoản máy riêng, khác module và Core theo câu 3A; chính sách Mask không tự đóng khi danh mục đang mở xem ENGINE-1.

# ENGINE-2 — Bản giao việc `e_trich_xuat` — v1.2

**Ngày Anh duyệt các quyết định Core làm căn cứ:** 30/10/2026.  
**Căn cứ:** CD-026, CD-028, CD-031…CD-036; CD-011 ngày 26/10/2026; `docs\47-core\PHIEU-DUYET-CSDL.md` — 1A, 2A, 3A; `docs\47-core\PHIEU-DUYET-API.md` — 1A, 2A.  
**Trạng thái:** chỉ tài liệu. CD-038 đã duyệt SDK bản 2 và câu 1C/3A; lập trình theo điều kiện chuẩn SDK v1.0 xong + Opus review, không hỏi lại các quyết định này.

## Thay đổi

- **v1.1:** xử lý RV-ENGINE-OPUS và RV-ENGINE; tách AI/bảng/E1-MUA đang CHỜ, chặn Word COM và OCR riêng của X.
- **v1.2 — CD-038:** chép có sửa phần trích xuất vào `e_trich_xuat`, đổi câu hỏi sang mẫu cổng AI chung; thêm lát đo độ chính xác trước/sau, giữ bản review gốc đóng băng.

## Kết luận

1. **Chép có sửa** phần `trich_xuat` của phần mềm review xây dựng vào gói `e_trich_xuat`: 37 tham số, cấu trúc hợp đồng, dẫn chứng và kiểm tra kết quả; ghi nguồn, phiên bản và SHA256 bản gốc, không sửa bản gốc.
2. Capability đích: `trich.tham_so_hop_dong@1`; `trich.bang@1` **chưa hỗ trợ**, không công bố trước khi có nguồn/test bảo toàn cấu trúc và contract được duyệt.
3. **CD-038 câu 1C:** đổi câu hỏi của bản chép sang mẫu cổng AI chung; không gọi thẳng máy AI, không thêm đường riêng. Đo lại độ chính xác trên `DAP_AN_*.tsv` (37 tham số) trước/sau; thấp hơn bản gốc → dừng, báo Anh kèm số liệu.
4. Bản review gốc đóng băng theo CD-011: chỉ đọc, không sửa.
5. E1-MUA là **bản chép có vá**, chưa được coi là dùng lại nguyên hoặc đã triển khai vào X; giữ chờ Anh cho phép.
6. Chỉ công bố capability, loại hợp đồng và định dạng đã có bằng chứng chạy đạt.

## Bắt buộc

### Contract vào/ra

| Capability | Đầu vào | Đầu ra và giới hạn |
|---|---|---|
| `trich.tham_so_hop_dong@1` | Chỉ DOCX từ `tham_chieu_tep.v1`; lệnh Core có `tai_lieu_id`, `tep_id`, `loai`, `danh_muc_phien_ban`; PDF phải qua `e_ocr` | `tham_so.v1`: giữ loại, danh mục/hash, giá trị đã định kiểu hoặc lý do chưa xác định, dẫn chứng và tham chiếu phản hồi nguồn. Luồng AI qua mẫu cổng chung **giao được** theo CD-038; chỉ công bố sau kiểm tương thích và đo độ chính xác không thấp hơn gốc. |
| `trich.bang@1` | **Chưa hỗ trợ.** Không dùng bộ đọc hợp đồng làm bằng chứng bảo toàn bảng | Đích kỹ thuật `du_lieu_bang.v1`; chưa có nguồn/test được xác nhận giữ hàng/cột, ô rỗng, ô gộp, vị trí. `X\trich_xuat\doc_hop_dong.py:341` bỏ ô rỗng/ghép chuỗi, không đạt. OpenAPI chưa khai lệnh: **CHỜ Anh — contract bảng** và bằng chứng nguồn/test; không tạo route/schema hoặc viết thuật toán bù thiếu. |

Phản hồi nguồn phải được giữ để không mất `ghi_chu`, `kiem_tra`, `dieu_khoan`, `trich_dan`, `vi_tri_do_duoc`. Không suy giá trị chưa rõ thành `0`, tiền hoặc ngày.

### Nguồn chính thức và cách dùng lại

Quy ước **X** = `D:\Claude\Ho tro review ho so xay dung\review_xaydung`; đường dẫn không có tiền tố X tính từ repo hiện tại.

| Phần | Dùng lại nguyên / bọc / sửa / viết mới |
|---|---|
| Danh mục | **Dùng lại nguyên:** `X\trich_xuat\danh_muc.py:149`, `X\trich_xuat\danh_muc.py:186`; giữ danh mục XD đã chứng minh và test gốc. |
| Lõi trích | **Chép có sửa vào `e_trich_xuat` — CD-038 câu 1C:** nguồn `X\trich_xuat\quy_trinh.py:91`, `:92`, `:272`; đổi câu hỏi sang mẫu cổng AI chung vì prompt/protocol gốc không tương thích. Ghi nguồn + phiên bản + SHA256 bản gốc trước chép và phần thay đổi; không sửa X. Giữ 37 tham số/dẫn chứng, dựng `TrichXuat(cloud=None)`, `ai.la_cloud=False`; chỉ DOCX, không đi nhánh PDF gọi OCR riêng tại `:292`. |
| Đọc hợp đồng | **Bọc, không dùng lại nguyên toàn bộ:** `X\trich_xuat\doc_hop_dong.py:296`, `X\trich_xuat\doc_hop_dong.py:453`; lớp bọc chặn `_word` tại `X\trich_xuat\doc_hop_dong.py:63`, `X\trich_xuat\doc_hop_dong.py:468` để nguồn rơi về Python chấp nhận sửa đổi XML tại `X\trich_xuat\doc_hop_dong.py:69`. Phải có test chứng minh không tạo Word COM. |
| Local AI/câu hỏi | **Chép có sửa phần tích hợp — CD-038 câu 1C:** nguồn seam `X\trich_xuat\quy_trinh.py:92`, câu hỏi/protocol tại `X\trich_xuat\ai_local.py:104`; chuyển sang mẫu cổng chung `src\kho_tri_thuc\tri_thuc\cong_ai.py:1236` vì `/api/chat` + `format: schema`/`num_ctx`/`think` gốc khác cổng hiện có. Không mang client gọi thẳng máy AI sang engine, không thêm đường riêng; ghi nguồn + SHA256, đo trước/sau và ghi ca test đổi/lý do. |
| Bảng hợp đồng | **Chưa hỗ trợ, không giao viết thuật toán mới:** `X\trich_xuat\doc_hop_dong.py:341` không giữ ô rỗng/cấu trúc. Chưa có nguồn/test đạt cho `trich.bang@1`; nguồn bảng OCR tại ENGINE-1 không tự chứng minh capability của engine này. |
| Danh mục E1-MUA | **Sửa / chép có vá — CHỜ Anh:** `tools\source6_g5_e5\trich_xuat\danh_muc.py:25` đổi import tương đối `.cau_hinh`; đăng ký/đường dẫn danh mục tại `tools\source6_g5_e5\trich_xuat\danh_muc.py:291`, `tools\source6_g5_e5\trich_xuat\danh_muc.py:307`. XLSX theo loại phải đặt cạnh `DANH_MUC_THAM_SO.xlsx` của X; không suy là gói nguồn đã có đủ tệp. Không áp bản vá vào X. |
| Adapter và vận hành | **Viết mới chỉ phần cần thiết:** chuyển contract, chặn nhánh không được phép, khung cổng/bàn giao Core theo `docs\47-core\g1\DAC-TA-SDK.md:83`, `docs\47-core\g1\DAC-TA-SDK.md:110`; tái dùng bắt tay/readiness/Windows Job theo `docs\47-core\g1\DAC-TA-SDK.md:90`. **Sửa nguồn gốc: không**; câu hỏi và test liên quan chỉ sửa trong bản chép theo CD-038, không tự mở rộng phạm vi. |

Common API hiện có chỉ chạy `RULE_ONLY`, không AI/Cloud/OCR; không coi đó là bằng chứng luồng Local AI đã tích hợp. E1-MUA chưa xác nhận triển khai: **CHỜ Anh — cho phép bản chép có vá/danh mục theo loại** (quyết định riêng, không phải đã trả lời Câu 1). Có XD, DV, MUA_HH, THUE_TS, NHAP_KHAU; DV_KY/DV_1L chỉ chọn tường minh. Không fallback sang XD khi thiếu/sai loại hoặc danh mục.

SHA256 đối chiếu ngày 30/10/2026: nguồn `X\trich_xuat\danh_muc.py` = `4309decb0b62b9ee76ba449f69ea5080c33abb23d4e488b6a1d8cc2602e5bf6b`; bản chép có vá `tools\source6_g5_e5\trich_xuat\danh_muc.py` = `919b1271b76a9678f1dafbac6bb74dcd487cd5bd07446b42487dfc8c5bb7c955`. Đây là hash mã Python để xác định nguồn/bản vá, không thay hash XLSX trong registry; khi giao lát phải ghi thêm phiên bản nguồn và kiểm đủ tệp danh mục, không lập manifest hash riêng.

### CD-038 câu 1C đã chốt: AI của trích xuất hợp đồng

Nhận định cũ "Bọc seam AI chuyển qua cổng AI" chưa khả thi nếu không sửa nguồn/cổng. X gọi Ollama `/api/chat` với `format: schema`, `num_ctx`, `think` và chặn câu hỏi bị cắt (`X\trich_xuat\ai_local.py:104`–`:160`); `CongAI.goi` ép prompt/định dạng khác, Local hiện nói `/v1/chat/completions` không schema (`src\kho_tri_thuc\tri_thuc\ai_cuc_bo.py:213`–`:241`). Test gốc `X\tests\test_trich_xuat.py:304`, `X\tests\test_trich_xuat.py:313` dùng `mock_ollama` cho `/api/chat`, chưa chứng minh chạy qua cổng AI.

**Anh đã chọn C tại CD-038:** chép phần trích xuất review vào gói `e_trich_xuat`, ghi đường dẫn nguồn, phiên bản và SHA256 bản gốc; **không sửa bản gốc X đang đóng băng**. Đổi câu hỏi trong bản chép sang mẫu cổng AI chung; không gọi thẳng máy AI, không thêm đường Local/Cloud riêng. TRICH-1b/TRICH-3b và AI-6 **giao được** theo hướng này; Cloud chưa thuộc luồng trích xuất này.

**Cổng nghiệm thu độ chính xác:** đo **trước/sau** trên cùng bộ đáp án hiện có `DAP_AN_*.tsv`, đủ **37 tham số**, cùng tài liệu DEMO, cách chấm và điều kiện model/cấu hình; ghi nguồn/SHA và điều kiện đo trong báo cáo lát, không tạo manifest riêng. Số trước lấy từ bản review gốc với đường chạy đã được phép; không sửa/chạy đường gọi thẳng máy AI từ worker để lấy số. Chưa có phép đo gốc hợp lệ thì ghi chưa đo, không suy từ mock hay số test xanh. Báo đạt/tổng, tỷ lệ chính xác tổng và theo từng tham số, chênh lệch trước/sau và ca sai; không đổi đáp án/loại ca để nâng điểm. Độ chính xác sau **không được thấp hơn bản gốc**; thấp hơn → **dừng, báo Anh kèm số liệu**, không nghiệm thu tích hợp.

**Test gốc:** giữ bộ test gốc trong X; nếu cần sửa test cho bản chép, ghi rõ tên/ID từng ca đổi, kỳ vọng trước/sau và lý do (đổi câu hỏi/protocol sang mẫu cổng chung). Ca không bị ảnh hưởng phải giữ nguyên; không nới assertion hoặc bỏ ca chỉ để xanh. Đo độ chính xác là kiểm riêng, mock `/api/chat` và test adapter không thay thế phép đo này.

Yêu cầu OPUS-5, chép nguyên:

> "Adapter chỉ nhận DOCX (PDF phải qua `e_ocr`). Chặn `_word` bằng lớp bọc có test → nguồn rơi về nhánh Python chấp nhận sửa đổi trong XML (`:69-70`). `TrichXuat(cloud=None)`, `ai.la_cloud=False`. `out_dir` thư mục tạm theo việc, xóa sau khi bàn giao."

Đây là yêu cầu vòng đời tệp của engine tương lai; lượt sửa tài liệu này không xóa tệp. `out_dir` không nằm trong nguồn X. Không gọi `ocr_abbyy.py` của X, tránh engine OCR/sổ hạn mức thứ hai.

### Khung chạy và thứ tự lát

Engine chạy bằng tài khoản Windows hạn chế, khác Core; không có login CSDL, không nhận khóa Cloud hoặc đọc kho bí mật. CD-038 câu 3A đã chốt tài khoản riêng cho từng engine giữ bí mật tại ENGINE-1; trích xuất không tự đọc khóa để lách cổng AI. Core cấp/giữ/nhả cổng; xác minh instance, phiên bản, capability và readiness trước phục vụ; drain, bàn giao kết quả và chờ Core xác nhận trước dừng/dọn thư mục tạm. Core ghi số đo khởi động, xử lý, thời gian rảnh, RAM/CPU; chỉ Admin áp dụng thay đổi chế độ chạy.

Codex làm chính; mỗi lát tối đa **3 tệp đích**, gồm test:

1. **TRICH-1a — giao được:** chép/bọc đọc DOCX, chặn `_word` và ánh xạ `tham_so.v1` bằng AI giả; giữ đối chiếu 37 tham số XD, test không gọi COM/OCR/Cloud. **TRICH-1b — giao được theo CD-038 câu 1C:** chép có sửa câu hỏi vào `e_trich_xuat`, dùng mẫu cổng chung; ghi nguồn/SHA, ca test đổi và lý do, không sửa X. Lấy số trước tại TRICH-4 trước khi đo bản sửa.
2. **TRICH-2a — CHỜ bằng chứng nguồn/test và Anh duyệt contract:** `trich.bang@1` chưa hỗ trợ, không công bố/viết bù thuật toán. **TRICH-2b — CHỜ Anh — E1-MUA:** danh mục theo loại là bản chép có vá, kiểm nguồn/hash/vị trí XLSX trước khi cho phép dùng.
3. **TRICH-3a — giao được:** manifest, khung tiến trình và Core giả lập, không bí mật. **TRICH-3b — giao được theo CD-038 câu 1C/3A:** tích hợp AI qua cổng chung, theo phụ thuộc contract liên quan; nghiệm thu chỉ sau TRICH-4 không giảm độ chính xác. Không sửa X.
4. **TRICH-4 — giao được: đo độ chính xác trước/sau** trên `DAP_AN_*.tsv` (37 tham số): lấy số trước của bản gốc theo đường được phép, đo bản chép đã đổi câu hỏi sau TRICH-1b, cùng bộ dữ liệu/điều kiện/cách chấm; báo đạt/tổng, tỷ lệ và chênh lệch theo mục trên. **Sau thấp hơn gốc → dừng, báo Anh kèm số liệu**; thiếu phép đo không được coi là đạt.

Lead chốt danh sách đường dẫn được sửa trước khi giao code; không tự mở rộng whitelist. Nếu buộc phải chép code, ghi nguồn, SHA256 và phiên bản bản gốc theo CD-036.

## Khuyến nghị

Không bổ sung lựa chọn thiết kế trong bản giao việc này; các phần chưa đủ bằng chứng giữ trạng thái chờ.

## Module được làm / không được làm

- **Được:** `mau_demo` dùng tệp giả, gửi yêu cầu qua Core và đọc kết quả theo quyền; ví dụ hợp đồng XD giả phải khai rõ `loai=XD` và phiên bản danh mục.
- **Không được:** gọi thẳng cổng engine/AI, tự duyệt kết quả, sinh nghĩa vụ nghiệp vụ trong engine, sửa X hoặc mở `X\co_so_du_lieu\*.db`.

## Checklist trước khi nộp gói

- [ ] Có CD mở lại, whitelist tệp và phiên bản contract được phép dùng.
- [ ] Giữ test gốc tại `X\tests\test_trich_xuat.py:97`, `:304`, `:313`; kiểm ca tương ứng qua engine bằng dữ liệu giả. Test cần sửa chỉ sửa bản chép, ghi tên/ID ca, kỳ vọng trước/sau và lý do theo CD-038 câu 1C; mock `/api/chat` không chứng minh cổng chung đã tương thích.
- [ ] Có nguồn + phiên bản + SHA256 phần trích xuất đã chép vào `e_trich_xuat`, không sửa X; không gọi thẳng máy AI/thêm đường riêng. Có số đo `DAP_AN_*.tsv` đủ 37 tham số trước/sau, cùng cách chấm/điều kiện; sau không thấp hơn gốc, nếu thấp hơn phải dừng/báo Anh kèm số liệu, không thay bằng test xanh.
- [ ] DOCX Track Changes trên Windows vẫn không tạo Word COM; lớp bọc chặn `_word` thực sự dùng nhánh XML Python, không chỉ ghi cờ. PDF bị chặn/đi qua `e_ocr`, không gọi ABBYY riêng của X; `cloud=None`, `ai.la_cloud=False` có hiệu lực.
- [ ] Kiểm loại/danh mục/hash, dẫn chứng, dữ liệu thiếu; không fallback hoặc mất trường nguồn. `trich.bang@1` chưa hỗ trợ phải không xuất hiện trong capability ready; chỉ mở khi có nguồn/test ô rỗng, hàng/cột, ô gộp, vị trí và contract được duyệt.
- [ ] Kiểm cổng, readiness, tài khoản hạn chế, bàn giao/dừng, retry và việc bị gián đoạn.
- [ ] Ca âm từ chính tiến trình engine bằng bí mật DEMO chứng minh không đọc két/Core process/handle; script ACL chạy lại được. Thư mục tạm theo việc chỉ dọn sau xác nhận bàn giao.
- [ ] Không thêm lỗi so với `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md`; báo đạt/tổng, lỗi mới, phần chưa kiểm và rủi ro.

## Phụ lục — đặc tả chi tiết

- `docs\47-core\g1\DAC-TA-API.md` §2.6, §4, OpenAPI `LenhTrich`.
- `docs\47-core\g1\DAC-TA-SDK.md` §4, §6.2 — phiếu SDK bản 2 đã duyệt tại CD-038; lập trình theo điều kiện chuẩn SDK v1.0 + Opus review.
- `docs\47-core\g1\CONTRACT-DU-LIEU.md` §6, §7, §13, §15 và bộ kiểm tuân thủ.
- `docs\47-core\g0\KS-D.md` §3.2; `docs\GIAO-CODE-E1-MUA-DANH-MUC-THAM-SO-THEO-LOAI.md` — đối chiếu hiện trạng E1-MUA; không dùng để vượt lệnh đóng băng.

---

# ENGINE-2 — Bản giao việc `e_hoa_don` — v1.2

**Ngày Anh duyệt các quyết định Core làm căn cứ:** 30/10/2026.  
**Căn cứ:** CD-026, CD-028, CD-031…CD-036; `docs\47-core\PHIEU-DUYET-CSDL.md` — 1A, 2A, 3A; `docs\47-core\PHIEU-DUYET-API.md` — 1A, 2A.  
**Trạng thái:** chỉ tài liệu. CD-038 đã duyệt SDK bản 2 và câu 2A/3A; lập trình theo điều kiện chuẩn SDK v1.0 xong + Opus review. Gọi cổng thuế thật cần **lệnh riêng của Anh**.

## Thay đổi

- **v1.1:** xử lý hai review; tải thực CHỜ Câu 2/3, tách tải stub/bảng kê, quy định kỳ tháng, profile và PARTIAL.
- **v1.2 — CD-038:** tải trong phiên Windows riêng có màn hình, tài khoản engine riêng; mỗi pháp nhân một profile xóa sau phiên, mật khẩu từ két Core; các lát tương ứng giao được.

## Kết luận

1. Capability đích: `hoa_don.doc_xml@1`, `hoa_don.doc_zip_bang_ke@1` theo contract đã đủ; `hoa_don.tai_cong_thue@1` **giao được theo CD-038 câu 2A/3A**, chỉ công bố ready sau kiểm chứng, không tự gọi cổng thuế thật.
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
| `hoa_don.tai_cong_thue@1` | `nguon_id`, `tu_ngay`, `den_ngay`, `huong=mua_vao\|ban_ra`; Core kiểm nguồn thuộc pháp nhân. Adapter **chỉ nhận trọn tháng**, ánh xạ tháng/năm theo `H\src\job.js:55`; kỳ thiếu ngày/lẻ tháng bị từ chối, không âm thầm mở rộng kỳ. | **Giao được theo CD-038 câu 2A/3A:** phiên Windows riêng có màn hình để người gõ CAPTCHA, profile từng pháp nhân xóa sau phiên, mật khẩu từ két Core. Tệp bàn giao thành tham chiếu Core, theo dõi qua `viec.v1`; không cam kết đường chuyển CAPTCHA về Core. Chỉ gọi thuế thật khi Anh ra lệnh riêng. Lỗi một nhóm truy vấn phải báo **PARTIAL** kèm coverage/nhóm lỗi; không coi tải xong là đã đọc hoặc nhận nghiệp vụ. |

Giữ số hóa đơn dạng chuỗi, decimal chính xác, số `0` đầu, dữ liệu thiếu và lỗi nguồn. Không suy tiền tệ/số lượng/thuế suất, không cộng dòng để tự thay tổng nguồn. XML/ZIP và JSON chi tiết nguồn có tham chiếu riêng.

### Nguồn chính thức và cách dùng lại

Quy ước **H** = `D:\Claude\Phan mem download hoa don`; đường dẫn không có tiền tố H tính từ repo hiện tại.

| Phần | Dùng lại nguyên / bọc / sửa / viết mới |
|---|---|
| Job tải | **Bọc, chạy stub trước:** `H\src\job.js:75`, `H\src\job.js:96`; tháng/năm tại `H\src\job.js:55`. `opts.env` là object nhận `TAX_PASSWORD` (`H\src\job.js:73`, `:109`): adapter dựng trong RAM từ stdin/handle do két Core cấp, không dùng biến môi trường OS. **Giao được theo CD-038 câu 2A/3A**, tài khoản riêng và phiên có màn hình. |
| Phiên cổng thuế | **Bọc có điều kiện, giao được theo CD-038:** `H\src\portal.js:27`, `:29` dùng profile cố định và `headless: false`; truy vấn tại `:223`, xuất XML tại `:251`. Chạy phiên Windows riêng có màn hình, thay profile cố định bằng profile từng pháp nhân/phiên có ACL, xóa sau phiên; kiểm lỗi nhóm truy vấn. Không tự sửa nguồn; nếu seam chưa đáp ứng phải báo thiếu hụt cụ thể. |
| Bảng kê/xuất nguồn | **Dùng lại nguyên:** `H\src\build.js:18`. Không dùng parser phục vụ hiển thị/PDF thay parser strict của contract. |
| Đọc XML/ZIP | **Dùng lại nguyên lõi, bọc contract:** `src\kho_tri_thuc\nguon\hoa_don_xml.py:1183`, `src\kho_tri_thuc\nguon\hoa_don_xml.py:1191`, `src\kho_tri_thuc\nguon\hoa_don_xml.py:618`; wrapper có sẵn `src\kho_tri_thuc\ha_tang\engine_hoa_don.py:109`. Wrapper hiện chưa bọc tải cổng thuế. |
| Adapter và vận hành | **Viết mới chỉ phần cần thiết:** ánh xạ contract/kỳ/PARTIAL, phiên có màn hình/profile/bí mật theo CD-038, nhận cổng/readiness và bàn giao Core theo `docs\47-core\g1\DAC-TA-SDK.md:83`, `:110`; tái dùng bắt tay/Windows Job theo `docs\47-core\g1\DAC-TA-SDK.md:90`. **Sửa nguồn gốc: không**, trừ khi Anh cho phép riêng phạm vi cụ thể. |

Không khởi chạy nguyên trạng `H\src\server.js`: nguồn này nạp `.env` tại dòng 5, có trạng thái tải RAM toàn cục và giao diện riêng. Adapter không đọc `.env`, không đưa mật khẩu/token vào manifest, dòng lệnh, log hoặc kết quả. Không mặc định nguồn H hỗ trợ owned protocol của `tools\source7_m2_patch`.

Parser có giới hạn riêng tại `hoa_don_xml.py:61`: XML 16 MiB, ZIP 64 MiB, 1.000 entry. Đây không phải quyền nâng giới hạn upload Core đã duyệt **20 MB**; áp giới hạn nhỏ hơn của đường tiếp nhận và capability.

### CD-038 câu 2A đã chốt: tải hóa đơn cần người gõ CAPTCHA

`H\src\portal.js:29`–`:30` mở Chromium `headless: false`; CAPTCHA được gõ ở màn hình máy chủ. Chưa có đường chuyển CAPTCHA về Core, trái giả định headless SDK §4.1. `.browser-profile` cố định trong thư mục nguồn (`H\src\portal.js:28`) còn lưu phiên giữa các lần chạy; không được mặc định dùng lại qua pháp nhân.

**Anh đã chọn A tại CD-038:** phần tải chạy trong **phiên Windows riêng có màn hình** (ngoại lệ như ABBYY) để người gõ CAPTCHA; **mỗi pháp nhân một hồ sơ trình duyệt**, xóa sau phiên, không tái sử dụng phiên cũ. Mật khẩu lấy từ **két Core**, chỉ cấp qua stdin/handle. Theo câu 3A, engine tải có **tài khoản máy riêng**, khác module, Core, Mask, AI Cloud và ABBYY. **Gọi cổng thuế thật chỉ khi Anh ra lệnh riêng**; quyết định này cho phép triển khai, không thay lệnh đó.

HD-2c/HD-3b **giao được** theo câu 2A/3A. Không coi `waiting_input` hay khung headless là đường chuyển CAPTCHA về Core. Nguồn `job.js` nhận mật khẩu qua object `opts.env`; adapter nhận stdin/handle từ két Core rồi dựng object trong RAM, không dùng `process.env` hay tệp cấu hình. Kiểm chứng đường cấp bí mật, phiên có màn hình/profile và ACL bằng dữ liệu DEMO trước nghiệm thu; nếu cần sửa nguồn thì báo phạm vi cụ thể, không tự mở rộng ngoại lệ.

### Ranh giới phiên, lỗi nhóm truy vấn và tiến trình

- Profile thuộc **một pháp nhân, một phiên**, nằm trong vùng kho tệp Core cấp có ACL theo tài khoản riêng của engine tải; không dùng `.browser-profile` ở nguồn, không dùng profile thật để thử. Credential/cookie không đưa vào manifest, args, env, log, kết quả; mật khẩu do két Core cấp qua stdin/handle, engine không tự đọc két. Trạng thái xác thực chỉ trong profile có vòng đời xóa sau phiên theo ngoại lệ CD-038 câu 2A; phải kiểm chứng, chưa coi là đã đáp ứng.
- Core theo dõi profile theo việc/phiên; chỉ dọn sau đóng browser và bàn giao được xác nhận, gồm kết thúc, lỗi, hủy và dọn phần sót sau crash trước khi mở phiên mới. Nếu chưa dọn được phải báo lỗi, chặn tái sử dụng; không cho pháp nhân khác mở. Đây là yêu cầu triển khai tương lai, lượt tài liệu này không xóa gì.
- `H\src\portal.js:223`–`:244` bỏ qua lỗi nhóm truy vấn; adapter phải nhận biết và báo **PARTIAL**, giữ nhóm lỗi/coverage và tệp đã nhận, không báo đủ kỳ. Nếu seam nguồn không cung cấp lỗi/coverage thì giữ nghiệm thu tải CHỜ, báo phần cần xin phép sửa nguồn, không bịa coverage hay âm thầm coi thành công.
- Node là **tiến trình con** của khung engine; Core quản lý cả cây Node/Chromium bằng Windows Job. Nguồn không có owned protocol: listener adapter đi đường `--port` chuyển tiếp có khoảng hở (SDK §4.1), không mặc định Node hỗ trợ `socket.share()`. Core nhả listener để bind đúng cổng; bị chiếm thì lỗi, không dò cổng khác; xác minh readiness/instance trước dispatch. Stub không chứng minh nguồn H đã có giao thức này.

### Khung chạy và thứ tự lát

Engine chạy dưới tài khoản Windows hạn chế riêng, khác Core/module và các engine giữ bí mật khác; không login CSDL hoặc tự đọc kho bí mật. **CD-038 câu 2A/3A đã duyệt** phiên Windows riêng có màn hình và nhận mật khẩu từ két Core. Core quản lý cổng, danh tính instance, readiness, việc lâu, bàn giao và drain; chờ Core xác nhận trước giải phóng/dừng, ghi số đo khởi động/RAM/CPU. Không dùng `/api/config` nguồn làm bằng chứng đã sẵn sàng tải.

Codex làm chính; mỗi lát tối đa **3 tệp đích**, gồm test:

1. **HD-1 — giao được:** bọc parser/wrapper hiện có sang `hoa_don.v1`, kiểm bảo toàn chi tiết nguồn theo contract đã chốt. Phần báo cáo ZIP thiếu schema giữ chờ, không tự thêm vỏ JSON.
2. **HD-2a — giao được:** tải giả qua engine với stub `portal` (không mở Chromium/nhận mật khẩu/kết nối thuế); kiểm trạng thái chờ đăng nhập giả, lỗi nhóm/PARTIAL, profile giả và bàn giao/chống trùng. **HD-2b — giao được:** bọc `build.js` xuất bảng kê và test riêng, không phụ thuộc tải thật. **HD-2c — giao được theo CD-038 câu 2A/3A:** ghép job/portal, CAPTCHA trong phiên Windows riêng có màn hình, profile từng pháp nhân xóa sau phiên, credential từ két Core; không gọi thuế thật nếu chưa có lệnh riêng.
3. **HD-3a — giao được:** manifest, khung tiến trình/Core và Node giả lập, kiểm cổng bị chiếm/Job/drain. **HD-3b — giao được theo CD-038 câu 2A/3A:** tài khoản riêng/ACL/phiên có màn hình/bí mật và vòng đời profile, test DEMO; lệnh gọi cổng thuế thật vẫn tách riêng.

Lead chốt đường dẫn được sửa trước giao code. Nếu bắt buộc chép code, ghi nguồn, SHA256 và phiên bản bản gốc. Không viết lại thuật toán tải hoặc parser.

## Khuyến nghị

Không bổ sung lựa chọn thiết kế trong bản giao việc này; schema/phạm vi chưa đủ căn cứ giữ trạng thái chờ.

## Module được làm / không được làm

- **Được:** `mau_demo` đưa XML/ZIP giả qua kho tệp Core, gọi capability đọc và xem issues/coverage theo quyền.
- **Không được:** gọi trực tiếp engine/cổng thuế, truyền credential từ frontend, ghi bảng M2 từ engine, tự xác nhận hợp lệ thuế, đủ kỳ hoặc đã hạch toán. Lệnh mở lại lập trình không thay lệnh riêng cho cổng thuế thật.

## Checklist trước khi nộp gói

- [ ] Có CD mở lại, whitelist tệp, profile và contract được phép dùng.
- [ ] Giữ test gốc `H\test\test.js:4`, `H\test\test.js:19`, `H\test\test.js:24`, `H\test\test.js:33` cho build/parse/PDF; không coi đó là test job/portal hoặc bằng chứng tải qua engine. Bổ sung ca engine với stub `portal`: tải, đăng nhập chờ giả, lỗi nhóm truy vấn/PARTIAL, bàn giao và chống trùng; không gọi cổng thuế.
- [ ] `tests\test_hoa_don_xml.py`, `tests\test_xs3_hoa_don.py` đạt; kiểm XML hỏng, namespace/profile lạ, ZIP lỗi/CRC/trùng tên/partial và thiếu context.
- [ ] Giữ nguyên decimal, định danh, hash, entry/coverage, issues và trạng thái chưa xác định; không báo thành công toàn bộ khi nguồn chỉ đọc được một phần.
- [ ] Từ chối kỳ lẻ tháng; ánh xạ đúng trọn tháng/tháng-năm, kiểm tháng 2/năm nhuận và biên đổi năm. Nhóm truy vấn lỗi không bị nuốt, phải PARTIAL/coverage, không gắn đủ kỳ.
- [ ] Hai pháp nhân giả không dùng chéo profile/cookie/credential; hai phiên cùng pháp nhân cũng không dùng lại profile cũ. Kiểm ACL, vòng đời profile khi xong/lỗi/hủy/crash và trường hợp dọn thất bại; không mở profile thật. Bí mật DEMO chỉ cấp qua đường được duyệt, không env/args/log/đĩa ngoài profile theo ngoại lệ đã duyệt.
- [ ] Kiểm tài khoản hạn chế, cổng/readiness, chống chạy trùng, bàn giao/dừng; restart không tự biến việc dở thành xong hoặc tải lại mù.
- [ ] Node/Chromium thuộc cây Job Core; cổng `--port` bị chiếm báo lỗi, không dò cổng; ca âm từ chính engine với bí mật DEMO chứng minh không đọc két/Core process/handle. Script tài khoản/ACL chạy lại được.
- [ ] Không thêm lỗi so với `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md`; báo đạt/tổng, lỗi mới, phần chưa kiểm và rủi ro.

## Phụ lục — đặc tả chi tiết

- `docs\47-core\g1\DAC-TA-API.md` §2.6, §4, OpenAPI `LenhDocHoaDon`, `LenhTaiHoaDon`.
- `docs\47-core\g1\DAC-TA-SDK.md` §4, §6.2 — phiếu SDK bản 2 đã duyệt tại CD-038; lập trình theo điều kiện chuẩn SDK v1.0 + Opus review.
- `docs\47-core\g1\CONTRACT-DU-LIEU.md` §10, §13, §15 và bộ kiểm tuân thủ.
- `docs\47-core\g0\KS-D.md` §3.2 — khác biệt bộ tải nguồn/M2-00 và giới hạn parser.
- `docs\M2-PROFILE-XML-DEMO-01.md` — profile XML DEMO hiện có.

## Đã xử lý review

Mã **OPUS-n** theo số mục của `RV-ENGINE-OPUS.md`; **RV-Chặn**, **RV-CS2/3/4** theo bốn dòng phát hiện của `RV-ENGINE.md`; **OPUS-S1…S5** theo thứ tự “Để sau / nên làm”.

| Mã | Chỗ sửa trong tệp này |
|---|---|
| OPUS-1; RV-Chặn | `e_hoa_don` — CD-038 câu 2A/3A đã chốt phiên có màn hình, tài khoản riêng, profile từng pháp nhân/phiên, ACL/vòng đời, mật khẩu két Core; HD-2c/3b giao được, thuế thật cần lệnh riêng. |
| OPUS-3 | `e_trich_xuat` — CD-038 câu 1C: chép có sửa câu hỏi sang mẫu cổng chung, nguồn/SHA, test đổi có lý do; TRICH-1b/3b/4 giao được, đo trước/sau không thấp hơn gốc. |
| OPUS-4 (liên quan) | `e_hoa_don` — tiêm `opts.env` object trong RAM từ stdin/handle, không OS env, tài khoản riêng đã duyệt; `e_trich_xuat` không đọc khóa/lách cổng. Chính sách câu 3A và seam `e_hoi_ai` ở ENGINE-1. |
| OPUS-5 | `e_trich_xuat` — nguyên văn giới hạn DOCX, wrapper chặn `_word`, `cloud=None`/`ai.la_cloud=False`, PDF qua `e_ocr`, thư mục tạm theo việc và test. |
| OPUS-8; RV-CS3 | `e_trich_xuat` — E1-MUA đổi nhãn sửa/chép có vá, SHA256 nguồn/bản vá, vị trí XLSX, giữ CHỜ; `trich.bang@1` chưa hỗ trợ, không dùng reader bỏ ô rỗng làm bằng chứng. |
| OPUS-9; RV-CS4 | `e_hoa_don` — contract chỉ trọn tháng, PARTIAL lỗi nhóm, Node tiến trình con/`--port` có khoảng hở, HD-2a stub tải và HD-2b bảng kê riêng; test gốc không chứng minh job/portal, thêm ca engine giả lập. |
| RV-CS2; OPUS-S1 (liên quan) | `e_trich_xuat` — cấm OCR riêng của X, tránh hai sổ; cổng OCR và nghiệm thu hạn mức chi tiết ở ENGINE-1. |
| OPUS-S4; RV — yêu cầu chung cuối review | Bảng đầu tệp/thứ tự e_mask → e_hoi_ai → e_trich_xuat; bảng nguồn/lát/checklist giữ tái dùng nền bắt tay/Windows Job, whitelist ≤3 tệp gồm test, ca âm từ chính engine. |

OPUS-2/6/7 và OPUS-S2/S3/S5 được đối chiếu tại mục “Đã xử lý review” cuối `GIAO-ENGINE-1.md`. Đây là hoàn tất sửa tài liệu theo CD-038; ba câu 1C/2A/3A đã chốt, giữ các phụ thuộc khác. Chưa chạy test code/dịch vụ, đo độ chính xác hoặc gọi thuế thật trong lát tài liệu này.

CD-038 (30/10): đã áp câu 1C/2A/3A: trích xuất chép có sửa + nguồn/SHA + đo `DAP_AN_*.tsv` 37 tham số trước/sau; tải trong phiên Windows riêng có màn hình, profile theo pháp nhân xóa sau phiên, mật khẩu két Core, tài khoản engine riêng; chuyển lát tương ứng sang giao được.
