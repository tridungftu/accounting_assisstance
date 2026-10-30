# ENGINE-1 — Lát giao được ngay / Lát chờ Anh

| Engine | Lát giao được ngay | Lát chờ Anh |
|---|---|---|
| `e_ocr` | OCR-1…OCR-5, gồm OCR-4b/5b: **giao được**; ABBYY theo ngoại lệ phiên Windows có màn hình và tài khoản riêng đã duyệt tại CD-038 câu 3A. | Không còn chờ Câu 3; vẫn phải kiểm chứng quyền/bí mật trước nghiệm thu. |
| `e_mask` | MASK-1, MASK-5, MASK-6: **giao được** theo CD-038 câu 3A; MASK-2…4 giao được về chính sách tài khoản/vòng đời. | MASK-2…4 vẫn phụ thuộc schema liên quan; MASK-3/4 còn cần bằng chứng nguồn/API, không tự công bố capability. |
| `e_hoi_ai` | AI-1a, AI-4a/4b, AI-5a/5b: **giao được** về chính sách bí mật; AI-3 giao được theo câu 3A khi đủ contract Mask; AI-6 kiểm tích hợp mẫu cổng chung theo câu 1C: **giao được**. | AI-1b, AI-2: chờ schema đầu vào/cờ chỉ Local; AI-3/5b còn phụ thuộc contract Mask liên quan, không còn chờ Câu 1/3. |

“Giao được” là không còn bị các câu hỏi đã chốt tại CD-038 chặn; SDK bản 2 đã duyệt, chỉ mở lập trình khi chuẩn SDK v1.0 xong và Opus review theo CD-038; lead khóa whitelist ≤3 tệp/lát gồm test. Lượt này **chỉ sửa tài liệu, không lập trình**. Phụ thuộc schema/bằng chứng còn thiếu giữ nguyên. Thứ tự tích hợp: **e_mask → e_hoi_ai → e_trich_xuat**; các lát giả lập độc lập có thể giao trước.

**Chính sách chung — CD-038 câu 3A:** engine giữ bí mật (Mask, AI Cloud, tải hóa đơn, ABBYY) **mỗi engine một tài khoản máy riêng**, khác tài khoản module và Core; không dùng chung `ktt_module`. Core quản lý két, chỉ cấp bí mật theo việc qua stdin/handle, giữ trong RAM, không args/env/log. Ngoại lệ Mask đang mở danh mục không tự đóng theo CD-028 mục 3; ngoại lệ phiên có màn hình áp dụng ABBYY và tải hóa đơn. Quyết định cho phép giao lát triển khai, không thay bằng chứng ca âm/ACL hoặc cho phép gọi dịch vụ thật.

# Bản giao việc `e_ocr` — v1.2

**Ngày Anh duyệt căn cứ:** 30/10/2026. **Căn cứ:** CD-028, CD-033, CD-035, CD-036; `docs\47-core\PHIEU-DUYET-CSDL.md` (1A/2A/3A), `PHIEU-DUYET-API.md` (1A/2A).  
**Thay đổi:** v1.2 — áp CD-038 câu 3A cho tài khoản/ngoại lệ ABBYY, bỏ chờ quyết định đã duyệt; giữ xử lý review v1.1. **Trạng thái:** chỉ tài liệu; lập trình theo điều kiện chuẩn SDK v1.0 + Opus review của CD-038.

**Kết luận:** Bọc nguồn OCR chính thức thành `e_ocr`, lấy ABBYY FineReader/Hot Folder làm lõi theo CD-035. Giữ thuật toán và test gốc; Core quản lý thư mục in/out, quyền, việc và lưu kết quả.

**Bắt buộc — mục tiêu và contract kỹ thuật**

| Capability | Vào → ra |
|---|---|
| `ocr.trich_van_ban@1` | `tham_chieu_tep.v1` → `van_ban_tai_lieu.v1` |
| `ocr.trich_bang@1` | `tham_chieu_tep.v1` → `du_lieu_bang.v1` |

Core kiểm quyền rồi cấp bytes/tham chiếu theo việc. Adapter chuyển DOCX hoặc kết quả cấu trúc nguồn sang contract; giữ hash, revision, vị trí và cảnh báo, không tự suy kiểu/đơn vị còn thiếu. Core tự gắn provenance từ instance/lease. Hoàn thành OCR, hết mục cần soát và duyệt nghiệp vụ là ba trạng thái riêng; chỉ công bố capability thực đạt.

**Nguồn chính thức và bảng "dùng lại nguyên / bọc / sửa / viết mới"** — ký hiệu `O` = `D:\GPT\OCR`.

| Phân loại | Phần việc và căn cứ |
|---|---|
| **Dùng lại nguyên** | Chỉ lõi ABBYY `HotFolderClient.convert`, `O\abbyy-hotfolder\abbyy_hotfolder\client.py:113`, với `Config` adapter dựng. Không gọi `load_config` tại `O\abbyy-hotfolder\abbyy_hotfolder\config.py:28`. |
| **Bọc** | ABBYY → DOCX → `extract_docx` tại `O\mask_ocr\extraction.py:135` + `word_layout(..., embedded_pages=[])` tại `O\mask_ocr\layout.py:149` → contract văn bản/bảng. Không chạy `structured._docx_result` tại `O\mask_ocr\structured.py:349` vì có OCR ảnh nhúng Tesseract/Paddle. Backend khác phải khai riêng, không đưa vào capability ABBYY này. |
| **Bọc** | Cổng OCR-1 đã có `src\kho_tri_thuc\ha_tang\cong_ocr.py:1`, rủi ro tương tranh tại `src\kho_tri_thuc\ha_tang\cong_ocr.py:8`; đang dùng ở `src\kho_tri_thuc\m9\ocr_hot_folder.py:10` và `src\kho_tri_thuc\ha_tang\engine_cong.py:15`. Dùng một chủ điều phối Hot Folder và một sổ hạn mức, không tạo cổng/sổ thứ hai. |
| **Sửa — không giao sửa nguồn** | `O\ocr-abbyy-ai\ocr_web\app.py:27` import `hieu_dinh` ngoài nguồn chính thức, `O\ocr-abbyy-ai\ocr_web\app.py:315` luôn hiệu đính/gọi Ollama trực tiếp và ghi thư mục nguồn. `app.py` chỉ tham khảo, không chạy/import vào engine; hiệu đính không thuộc lát này. |
| **Viết mới** | Chỉ adapter contract/Config và vận hành Core còn thiếu theo `docs\47-core\g1\DAC-TA-SDK.md:83`, `docs\47-core\g1\DAC-TA-SDK.md:110`; tái dùng bắt tay/readiness/Windows Job theo `docs\47-core\g1\DAC-TA-SDK.md:90`, không viết lại nền hoặc OCR. |

Không giữ nhận định cũ "Dùng lại nguyên `app.py:25/:277`, giữ xử lý `:315`"; yêu cầu OPUS-2, chép nguyên:

> "Dùng lại nguyên chỉ `HotFolderClient.convert` (`O\abbyy-hotfolder\abbyy_hotfolder\client.py:113`) với `Config` do adapter dựng; không gọi `load_config` (thứ tự nạp `config.py:28` lấy `config.json` thật trong thư mục nguồn). `app.py` chỉ tham khảo, không chạy. `test_app.py` ngoài phạm vi engine; test gốc của engine là `abbyy-hotfolder\tests` và `O\tests\test_structured_docx.py`."

Ưu tiên bọc; chỉ sao chép code khi bắt buộc, ghi nguồn, phiên bản và SHA256 bản gốc.

**Bắt buộc — vận hành:** Core giữ cổng loopback cố định; nhận listener bằng `socket.share()`/`fromshare()`. Nhánh nguồn cũ nhận `--port` là chuyển tiếp có khoảng hở; cổng bị chiếm thì báo lỗi, không dò cổng khác. Kiểm instance, phiên bản và capability thực trước phục vụ. Bàn giao kết quả, chờ Core xác nhận rồi mới giải phóng/dừng. Mặc định tự kích hoạt/tự dừng; Core ghi thời gian yêu cầu, tới ready, xử lý, rảnh, số lần/ngày, RAM/CPU; chỉ Admin áp dụng đề xuất chế độ.

Chạy bằng tài khoản hạn chế riêng cho ABBYY/`e_ocr`, khác Core, module và các engine giữ bí mật khác theo CD-038 câu 3A; không login CSDL, không đọc két Core. Ngoại lệ ABBYY chạy trong phiên Windows riêng có màn hình đã duyệt. Bí mật được cấp chỉ ở RAM qua stdin/handle; không đưa vào dòng lệnh, biến môi trường, đĩa hoặc log. Script tài khoản/ACL phải chạy lại được; ca âm phải chạy từ chính tiến trình engine với bí mật DEMO theo SDK §4.4.

`client.wait()` đọc xong có thể dọn tệp nguồn trước khi Core xác nhận; nếu engine chết trong khoảng này thì kết quả mất trong khi hạn mức đã trừ (`O\abbyy-hotfolder\abbyy_hotfolder\client.py:170`). Core phải ghi nhận việc gián đoạn/chưa bàn giao để đối chiếu; không tự gửi lại hoặc hoàn hạn mức khi chưa chứng minh chưa gửi/rút được đầu vào. Thư mục in/out do Core cấp theo việc; không dùng thư mục kết quả của `app.py`.

**Chia lát — Codex làm chính:** OCR-1 manifest + schema hiện có + test; OCR-2 adapter văn bản + test; OCR-3 adapter bảng + test; OCR-4a khung chạy giả lập + test vòng đời; OCR-5a adapter Core/hạn mức/bàn giao + test giả lập: **giao được**, theo phụ thuộc kỹ thuật. OCR-4b khởi chạy ABBYY/tài khoản riêng và OCR-5b tích hợp quyền/bí mật: **giao được theo CD-038 câu 3A**, kiểm bằng bí mật DEMO và ngoại lệ ABBYY đã duyệt. Mỗi lát ≤3 tệp, tính cả test; lead khóa danh sách đường dẫn trước giao.

**Khuyến nghị:** Dùng `O\abbyy-hotfolder\tests\fake_hotfolder.py` để kiểm độc lập bằng dữ liệu tổng hợp.

**Module được làm / không được làm:** `mau_demo` được gửi capability qua SDK Core và theo dõi việc; không gọi cổng engine, đọc thư mục Hot Folder hoặc tự phê duyệt OCR. Không gọi Cloud trực tiếp, không che tiền/ngày.

**Checklist trước khi nộp gói**

- [ ] Test gốc `O\abbyy-hotfolder\tests` và `O\tests\test_structured_docx.py` đạt; kiểm lại các ca phù hợp qua engine bằng cùng dữ liệu giả. `O\ocr-abbyy-ai\tests\test_app.py:77` kiểm hiệu đính/`bao_cao`, ngoài phạm vi engine, không chạy hiệu đính để làm xanh test này.
- [ ] Schema, bảng/ô gộp, revision, bàn giao trước dừng, readiness, tài khoản hạn chế và cổng đạt kiểm.
- [ ] Chỉ đường ABBYY → DOCX; không import `app.py`/`hieu_dinh`, không nạp cấu hình thật, không OCR ảnh nhúng bằng backend khác, không gọi AI trực tiếp.
- [ ] Một chủ điều phối/một sổ hạn mức cho các bên gọi; kiểm tương tranh, giữ chỗ/hủy, không tính hai lần, và rủi ro Review cũ không khóa theo `cong_ocr.py:8` (đối chiếu `KS-E.md:66`, `KS-E.md:146`). Chưa cách ly được chủ chạy cũ thì không nghiệm thu bảo đảm một sổ.
- [ ] Giả lập crash sau `wait()` trước xác nhận Core: ghi việc gián đoạn, không tự OCR lại/hoàn hạn mức; kết quả chưa xác nhận không bị coi là đã bàn giao.
- [ ] Không lỗi mới so với `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md`; báo đạt/tổng và phần chưa kiểm, không tính skip là đạt. Lát tài liệu này chưa chạy test.

**Phụ lục:** `docs\47-core\g1\DAC-TA-SDK.md` §4, §6.2; `CONTRACT-DU-LIEU.md` §4–6, §13, §15.2 và bộ kiểm KT06/08/09/10/14/16; khảo sát `docs\47-core\g0\KS-E.md`.

---

# Bản giao việc `e_mask` — v1.2

**Ngày Anh duyệt căn cứ:** 30/10/2026. **Căn cứ:** CD-028, CD-033, CD-035, CD-036; `docs\47-core\PHIEU-DUYET-CSDL.md` (1A/2A/3A), `PHIEU-DUYET-API.md` (1A/2A).  
**Thay đổi:** v1.2 — áp CD-038 câu 3A về mở khóa/vòng đời/tài khoản; giữ phụ thuộc schema và bọc HTTP của v1.1. **Trạng thái:** chỉ tài liệu; lập trình theo điều kiện chuẩn SDK v1.0 + Opus review của CD-038.

**Kết luận:** Bọc Mask file v2 thành `e_mask`; giữ bộ nhận diện, che/mở che và kiểm soát an toàn. Không che tiền/ngày. Không coi API che văn bản hiện có là bằng chứng đã hỗ trợ che tài liệu độc lập.

**Bắt buộc — mục tiêu và contract kỹ thuật**

| Capability | Vào → ra; giới hạn đặc tả |
|---|---|
| `mask.phat_hien@1` | Văn bản → gợi ý định danh; schema độc lập: **chờ Anh**, không tự chốt. |
| `mask.che_van_ban@1` | Văn bản và định danh đã biết → `noi_dung_da_che.v1`; schema đầu vào Core riêng: **chờ Anh**. |
| `mask.che_tai_lieu@1` | Tệp được Core cấp quyền → tài liệu đã che; contract độc lập: **chờ Anh**, chưa công bố khả năng chỉ từ schema văn bản. |
| `mask.mo_che@1` | Văn bản và lượt che được Core xác minh → văn bản mở che; schema Core riêng: **chờ Anh**. API nguồn nhận `ma_luot`, `van_ban`, `ket_thuc_luot`. |

`luot_che_id` là ID Core, không phải `ma_luot` hoặc quyền mở che. Mapping do Mask quản lý. Chỉ cho gửi khi danh mục `da_mo`, `gui_duoc=true`, không còn sót và tiền/ngày được bảo toàn thực tế; không chỉ tin cờ `giu_nguyen_tien_ngay=true`. Không tự tạo revision quy tắc chưa công bố.

**Nguồn chính thức và bảng dùng lại** — ký hiệu `M` = `D:\GPT\Phan mem Mask file\Mask file v2`.

| Phân loại | Phần việc và căn cứ |
|---|---|
| **Dùng lại nguyên — bên trong tiến trình Mask** | Nhận diện/che/kiểm tại `M\privacy\core.py:79`, `M\privacy\core.py:308`, `M\privacy\core.py:325`; `TurnStore` tại `M\privacy\auto_api.py:172` và che/mở tại `M\privacy\auto_api.py:291`, `M\privacy\auto_api.py:362` do server sử dụng nội bộ. Adapter không import/gọi trực tiếp các hàm này. |
| **Bọc — HTTP, giao được theo CD-038 câu 3A** | Chạy nguyên `M\run_privacy.py:18` bằng `--port`; chỉ gọi `/api/v1/trang-thai`, `/che`, `/mo-che` của MASK-1/2 (`M\privacy\server.py:1554`, `M\privacy\server.py:1561`, `M\privacy\server.py:1600`). Giữ closure danh mục/mật khẩu/duyệt/TurnStore tại `M\privacy\server.py:1543`; không lấy `mapping` từ `auto_api.mask_text`. |
| **Bọc — chưa hỗ trợ độc lập** | Xuất tài liệu tại `M\privacy\server.py:982` thuộc UI có session/revision/duyệt; chưa có bằng chứng endpoint độc lập. `mask.phat_hien@1` và `mask.che_tai_lieu@1` chưa kích hoạt, không thêm API UI vào allowlist để lấp contract thiếu. |
| **Sửa — không giao sửa nguồn** | `M\CLAUDE.md:43`, `M\CLAUDE.md:45`, `M\CLAUDE.md:51`: không nới chặn host/origin, không vá Mask khi chưa được Anh cho phép; nếu được phép thì không git, ghi CHANGELOG, test và benchmark độ phủ không giảm. |
| **Viết mới** | Chỉ adapter HTTP/contract và vận hành Core còn thiếu theo `docs\47-core\g1\DAC-TA-SDK.md:83`, `docs\47-core\g1\DAC-TA-SDK.md:110`; tái dùng bắt tay/Windows Job theo `docs\47-core\g1\DAC-TA-SDK.md:90`. Không tạo bộ che hay viết lại logic an ninh. |

Không giữ nhãn "Dùng lại nguyên `auto_api.mask_text`" ở adapter. Yêu cầu OPUS-6, chép nguyên; chính sách tài khoản/vòng đời đã chốt tại CD-038 câu 3A:

> "Bọc = chạy nguyên `run_privacy.py --port`, chỉ gọi HTTP `/api/v1/trang-thai`, `/che`, `/mo-che`. Adapter không import `mask_text`/`unmask_text`."

### CD-038 câu 3A đã chốt: Mask và bí mật của engine

Hiện trạng chưa đáp ứng câu "không giữ mật khẩu/khóa": Mask giữ mật khẩu danh mục trong RAM (`M\privacy\server.py:236`), dùng khóa tại `config\mask-api.key` với ACL cho tài khoản chạy Mask (`M\run_privacy.py:25`, `M\privacy\auto_api.py:43`, `M\privacy\auto_api.py:118`). Dùng chung tài khoản `ktt_module` có thể làm module đọc được khóa Mask. Không đọc khóa thật để kiểm.

Yêu cầu OPUS-4, chép nguyên (mục tiêu cấp bí mật; chưa coi nguồn Mask đã hỗ trợ):

> "Engine chỉ giữ bí mật trong RAM, nhận qua stdin/handle từ két Core. `e_hoi_ai` tiêm qua seam `moi_truong` (`:988`) và đối tượng `mask`; không sửa nguồn. Không ghi đĩa, không log."

**Anh đã chọn A tại CD-038:** Anh mở khóa danh mục Mask ngay tại máy chủ; Mask **không tự đóng/tự dừng khi danh mục đang mở**, là ngoại lệ CD-028 mục 3. Mask, AI Cloud, tải hóa đơn, ABBYY mỗi engine một tài khoản máy riêng, khác tài khoản module và Core. Không lưu mật khẩu để tự mở lại.

Mở khóa chỉ qua UI tại `127.0.0.1`; TrustedHost/Origin tại `M\privacy\server.py:240`, `M\privacy\server.py:263` chặn Core chuyển tiếp. Không proxy UI hoặc nới chặn (quy tắc 3 của `M\CLAUDE.md`). Nguồn hiện vẫn chuẩn bị khóa trên đĩa: chưa có bằng chứng chạy nguyên `run_privacy.py` vừa không ghi khóa vừa nhận qua stdin/handle. **Giao được** lát tài khoản/ACL/vòng đời và kiểm chứng cấp bí mật theo câu 3A; ghi rõ thiếu hụt kỹ thuật nếu nguồn chưa đáp ứng, không coi quyết định tài khoản là bằng chứng đã chạy đạt. Không tự thêm seam/sửa nguồn hoặc nới host/origin; nếu bắt buộc sửa nguồn phải báo phạm vi cụ thể.

Ưu tiên bọc; sao chép bắt buộc phải ghi nguồn, phiên bản và SHA256. Không đọc/sửa dữ liệu thật, `*.key`, `*.maskvault`, `*.maskkeep`.

**Bắt buộc — vận hành:** Tài khoản hạn chế riêng cho Mask, khác Core/module và các engine giữ bí mật khác; không login CSDL/đọc két Core. Theo CD-038 câu 3A, **không tự đóng khi danh mục đang mở** (ngoại lệ CD-028 mục 3), kể cả lúc rảnh. Script tài khoản/ACL chạy lại được, có ca âm từ chính engine bằng bí mật DEMO. Core giữ/chuyển giao cổng loopback; nhánh cũ dùng đúng `--port` có khoảng hở, bị chiếm thì lỗi, không dò cổng khác. Readiness kiểm instance, phiên bản và tình trạng danh mục/capability, không chỉ `/healthz`. Không dừng khi lượt che còn dùng hoặc kết quả chưa bàn giao. Không lưu mật khẩu để tự mở lại. Core đo yêu cầu→ready, xử lý, rảnh, số lần/ngày, RAM/CPU; chỉ Admin áp dụng đề xuất chế độ.

**Chia lát — Codex làm chính:** MASK-1 manifest + test phần đã có; lead soạn dự thảo 4 schema ánh xạ đúng trường MASK-1/2 để Anh duyệt, không công bố capability/schema mới: **giao được**. MASK-2 adapter HTTP che/mở + test; MASK-3 phát hiện + test; MASK-4 tài liệu + test: **giao được về chính sách câu 3A**, còn phụ thuộc schema liên quan; MASK-3/4 còn chờ bằng chứng nguồn/API phù hợp, không tự viết thuật toán/endpoint để lấp thiếu. MASK-5 khung chạy/tài khoản riêng + test và MASK-6 vận hành Core/vòng đời danh mục + test tích hợp: **giao được theo CD-038**, phần chưa đủ schema dùng giả lập. Mỗi lát ≤3 tệp, gồm test; lead khóa đường dẫn trước giao.

**Khuyến nghị:** Dùng fixtures tổng hợp và transport giả hiện có; giữ nguyên bộ benchmark chính và `held_out`.

**Module được làm / không được làm:** `mau_demo` được yêu cầu Mask qua Core; không lấy mapping, khóa hoặc gọi API UI để bỏ qua quyền/revision. Không gọi Cloud trực tiếp; không che tiền/ngày.

**Checklist trước khi nộp gói**

- [ ] Test gốc `M\tests` đạt và các ca tương ứng đạt qua engine bằng dữ liệu giả; benchmark chính/`held_out` không giảm.
- [ ] Kiểm danh mục khóa, còn sót, lượt hết hạn/sai pháp nhân, restart, bảo toàn tiền/ngày; không tự đóng khi danh mục đang mở theo CD-038, không dừng khi lượt còn dùng.
- [ ] Adapter chỉ dùng 3 HTTP endpoint được phép; không import hàm che/mở, không lộ mapping, không proxy UI/nới host/origin. Kiểm chứng cấp khóa/ACL/tài khoản riêng và vòng đời đã duyệt tại CD-038 câu 3A trước nghiệm thu chạy thật.
- [ ] Contract chưa chốt không được kích hoạt; không lỗi mới so với nền. Báo đạt/tổng, phần chưa kiểm; lát tài liệu này chưa chạy test.

**Phụ lục:** `docs\47-core\g1\DAC-TA-SDK.md` §4, §6.2; `CONTRACT-DU-LIEU.md` §8, §13, §15.2, bộ kiểm KT06/08/09/10/16; khảo sát `docs\47-core\g0\KS-D.md` §3.1.

---

# Bản giao việc `e_hoi_ai` — v1.2

**Ngày Anh duyệt căn cứ:** 30/10/2026. **Căn cứ:** CD-028, CD-033, CD-035, CD-036; `docs\47-core\PHIEU-DUYET-CSDL.md` (1A/2A/3A), `PHIEU-DUYET-API.md` (1A/2A); nguyên tắc cổng AI tại TL 48.  
**Thay đổi:** v1.2 — áp CD-038 câu 1C/3A: trích xuất đổi sang mẫu cổng chung, tài khoản AI Cloud riêng; giữ lõi và nhật ký/thống kê của v1.1. **Trạng thái:** chỉ tài liệu; lập trình theo điều kiện chuẩn SDK v1.0 + Opus review của CD-038.

**Kết luận:** Tách giao tiếp cổng AI hiện có thành engine chung `e_hoi_ai`, capability `ai.hoi@1`. Local luôn có đường sử dụng; Cloud chỉ qua quy trình che/mở che của `e_mask`. “Local luôn có” không có nghĩa tiến trình/model mặc định luôn chạy.

**Bắt buộc — contract kỹ thuật**

Đầu vào chuyển từ `YeuCauAI`: `loai_viec`, `van_ban`, `chi_dan`, `truong`, `dinh_danh_da_biet`; danh tính, pháp nhân và việc lấy từ Core đã xác thực. Phải hỗ trợ cờ **“chỉ Local”** cho M9: không gọi Cloud kể cả Local lỗi, thiếu chắc chắn hoặc được chọn kiểm xác suất. Tên trường và JSON Schema đầu vào chứa cờ này: **chờ Anh**, không tự chốt contract mới.

Đầu ra `tra_loi_ai.v1`: giữ trường, dẫn chứng, nguồn từng trường, giá trị Local trước khi Cloud thay, lý do và trường bị loại; không tự biến kết quả theo trường thành câu trả lời tự do. CLOUD/LOCAL+CLOUD phải gắn `luot_che_id` đúng việc/pháp nhân, còn hạn và kết quả kiểm mở che. Model cấu hình không được ghi thành bằng chứng model thực chạy. Có kết quả không đồng nghĩa đã duyệt.

**Nguồn chính thức và bảng dùng lại** — ký hiệu `A` = `src\kho_tri_thuc\tri_thuc\cong_ai.py`, `L` = `src\kho_tri_thuc\tri_thuc\ai_cuc_bo.py` trong repo.

| Phân loại | Phần việc và căn cứ |
|---|---|
| **Dùng lại nguyên** | DTO `YeuCauAI`, `TruongAI`, `KetQuaAI` tại `src\kho_tri_thuc\tri_thuc\cong_ai.py:275`, `A:296`, `A:305`; thuật toán thống kê/chọn kiểm tại `A:1009`, `A:1033`, Local trước tại `A:1236`. Lưu trữ thống kê phải bọc qua Core, không chỉ dùng bộ nhớ. |
| **Dùng lại nguyên** | `ai_cuc_bo.ask_local` tại `src\kho_tri_thuc\tri_thuc\ai_cuc_bo.py:243`; `MaskV2` tại `A:623`; `NhaCungCapAnthropic` tại `A:724`, `NhaCungCapOpenAI` tại `A:761`. Chỉ dùng trong cổng AI phần mềm, Cloud phải qua `e_mask`; không viết client/bộ che riêng. |
| **Bọc** | Seam Local/Mask/provider/`moi_truong` tại `src\kho_tri_thuc\tri_thuc\cong_ai.py:988`; cờ chỉ Local bằng instance theo request `cloud_bat=False` tại `A:1149`, không sửa nguồn/đổi trạng thái instance chung; che/mở tại `A:663`, `A:683`. Tiêm đối tượng `mask` và mapping `moi_truong` trong RAM, không phải biến môi trường của tiến trình. |
| **Sửa — không giao sửa nguồn** | Không mang `BoGhiPostgres` tại `src\kho_tri_thuc\tri_thuc\cong_ai.py:421`/credential CSDL vào engine; không dùng `BoGhiBoNho` làm kho thống kê lâu dài vì tự dừng sẽ về mặc định (`A:1002`, `A:1045`). Đọc khóa tại `A:1174` phải dùng mapping RAM đã tiêm, không fallback sang môi trường tiến trình; đối tượng `mask` tiêm sẵn tránh đọc khóa từ tệp tại `A:606`. |
| **Viết mới** | Hiện thực `BoGhiNhatKy` theo seam `src\kho_tri_thuc\tri_thuc\cong_ai.py:988`: bàn giao bản ghi Core lưu, đọc `thong_ke` qua Core để giữ tỷ lệ kiểm/độ chính xác Local qua restart. Adapter contract và vận hành còn thiếu theo `docs\47-core\g1\DAC-TA-SDK.md:83`, `docs\47-core\g1\DAC-TA-SDK.md:110`; tái dùng bắt tay/Windows Job theo `docs\47-core\g1\DAC-TA-SDK.md:90`. |

**CD-038 câu 1C:** trích xuất chép có sửa câu hỏi sang mẫu cổng AI chung tại ENGINE-2; không mở rộng cổng bằng đường Local có schema riêng, không gọi thẳng máy AI. AI-6 **giao được** để kiểm tích hợp qua mẫu `CongAI.goi` hiện có và phối hợp đo độ chính xác trước/sau của `e_trich_xuat`.

**CD-038 câu 3A:** áp dụng cấp bí mật RAM qua stdin/handle tại mục `e_mask`; dùng seam `moi_truong`/`mask` thay nhánh mặc định đọc env/tệp. `e_hoi_ai` giữ khóa AI Cloud dưới tài khoản máy riêng, khác Mask, tải hóa đơn, ABBYY, module và Core. Không ghi khóa vào đĩa/log/dòng lệnh/biến môi trường, không đưa `BoGhiPostgres` vào engine; không tự đóng Mask khi danh mục đang mở.

Ưu tiên bọc; chỉ sao chép khi bắt buộc, ghi nguồn, phiên bản và SHA256.

**Bắt buộc — AI và vận hành:** Giữ đánh giá độ chính xác Local và kiểm xác suất theo TL 48; không tự đặt lịch/ngưỡng mới. Che cả dữ liệu và chỉ dẫn có nội dung nguồn trước nhánh Cloud; kiểm mở che và dẫn chứng sau trả lời. Không gửi XML hóa đơn thô, không che tiền/ngày, không tạo đường Cloud trực tiếp ngoài cổng AI hiện có.

Engine chạy tài khoản hạn chế riêng theo CD-038 câu 3A, không login CSDL/đọc két Core; bí mật chỉ giữ RAM qua stdin/handle. Metadata/nhật ký bàn giao Core ghi, `thong_ke` đọc lại qua Core trước khi tính tỷ lệ; không âm thầm về mặc định sau restart hoặc khi đọc thống kê lỗi. Core giữ/chuyển giao cổng loopback, xác minh instance/phiên bản/capability và Local thực sẵn sàng; không chỉ đọc cấu hình. Drain, bàn giao rồi xác nhận dừng; giữ lượt Mask tới khi dùng xong. AI mặc định tự kích hoạt/tự dừng; Mask không tự đóng khi danh mục đang mở theo ngoại lệ CD-028 mục 3 tại CD-038. Core đo yêu cầu→ready, xử lý, rảnh, số lần/ngày, RAM/CPU; chỉ Admin áp dụng đề xuất. Script tài khoản/ACL chạy lại được, ca âm chạy từ chính engine với bí mật DEMO.

**Chia lát — Codex làm chính:** AI-1a manifest/DTO + test, AI-4a khung chạy giả lập + test, AI-5a `BoGhiNhatKy`/metadata qua Core + test restart: **giao được**, dùng provider/Mask/transport giả, không cần bí mật. AI-1b schema đầu vào và AI-2 adapter `ai.hoi@1`/chỉ Local + test: **CHỜ Anh — schema cờ chỉ Local**. AI-3 adapter `e_mask` + test, AI-4b khởi chạy có bí mật/tài khoản riêng và AI-5b tích hợp Cloud/vận hành: **giao được theo CD-038 câu 3A**, phần tích hợp còn phụ thuộc contract Mask. AI-6 kiểm trích xuất dùng mẫu cổng chung: **giao được theo câu 1C**, không thêm đường riêng; phối hợp lát đo trước/sau tại ENGINE-2. Mỗi lát ≤3 tệp, gồm test; lead khóa đường dẫn trước giao. Mã lát ở đây không phải mã AI-1/AI-2 của nguồn.

**Khuyến nghị:** Tận dụng `local_transport`, Mask/provider giả và hàm chọn kiểm xác suất được tiêm sẵn để kiểm độc lập, xác định được kết quả.

**Module được làm / không được làm:** `mau_demo` được gọi `ai.hoi@1` qua SDK Core và yêu cầu chỉ Local; không chọn URL/provider tùy ý, lấy khóa, gọi Cloud trực tiếp hoặc coi AI là người duyệt.

**Checklist trước khi nộp gói**

- [ ] Test gốc `tests\test_cong_ai.py`, `test_cong_ai_nhat_ky.py` và ca liên quan trong `test_xs3_cong.py` đạt; các ca tương ứng đạt qua engine bằng dữ liệu giả.
- [ ] Chỉ Local tạo **0 lời gọi Cloud**; Mask lỗi/khóa/còn sót, lượt hết hạn, mở che lỗi và dẫn chứng sai đều bị chặn đúng.
- [ ] Hai request khác cờ chỉ Local không làm đổi cấu hình của nhau; chỉ Local vẫn 0 Cloud khi Local lỗi/kiểm xác suất. Không đọc env/tệp khóa mặc định.
- [ ] `BoGhiNhatKy` bàn giao Core rồi restart vẫn giữ `thong_ke`, tỷ lệ kiểm và độ chính xác Local; không dùng `BoGhiBoNho` thay kho lưu, không âm thầm dùng mặc định nếu Core chưa trả thống kê. Engine không login CSDL.
- [ ] Không lộ bí mật, không login CSDL, bảo toàn tiền/ngày và giá trị Local; không lỗi mới so với nền. Báo đạt/tổng, phần chưa kiểm; lát tài liệu này chưa chạy test.

**Phụ lục:** `docs\47-core\g1\DAC-TA-SDK.md` §2–4, §6.2; `CONTRACT-DU-LIEU.md` §8–9, §13, §15.2, bộ kiểm KT06/08/09/10/14/16; khảo sát `docs\47-core\g0\KS-A.md`, `KS-D.md`.

## Đã xử lý review

Mã **OPUS-n** theo số mục của `RV-ENGINE-OPUS.md`; **RV-Chặn**, **RV-CS2/3/4** theo bốn dòng phát hiện của `RV-ENGINE.md`; **OPUS-S1…S5** theo thứ tự “Để sau / nên làm”.

| Mã | Chỗ sửa trong tệp này |
|---|---|
| OPUS-2 | `e_ocr` — bảng dùng lại, trích nguyên yêu cầu, đường ABBYY → DOCX và checklist test; loại `app.py`/hiệu đính/test_app. |
| RV-CS2; OPUS-S1 | `e_ocr` — bọc `cong_ocr`, một chủ điều phối/một sổ hạn mức, nghiệm thu tương tranh và Review cũ. |
| OPUS-S2; OPUS-S3 | `e_ocr` — `extract_docx` + `word_layout(embedded_pages=[])`; crash sau `wait()` không tự gửi lại/hoàn hạn mức. |
| OPUS-4 | `e_mask`/`e_hoi_ai`/`e_ocr` — CD-038 câu 3A đã chốt tài khoản riêng, mở khóa tại máy chủ và ngoại lệ vòng đời; giữ kiểm chứng cấp bí mật/ACL, không tự sửa nguồn. |
| OPUS-6 | `e_mask` — bảng dùng lại và nguyên văn bọc HTTP; closure/mapping/UI/TrustedHost/Origin; chưa chạy nguồn khi cấp khóa chưa giải quyết. |
| OPUS-7 | `e_hoi_ai` — bảng lõi dùng lại, `BoGhiNhatKy`/`thong_ke` qua Core, instance chỉ Local theo request và test restart. |
| OPUS-3 (phần cổng AI) | `e_hoi_ai` — CD-038 câu 1C, AI-6 giao được, dùng mẫu cổng chung; bản chép trích xuất và đo trước/sau ở ENGINE-2. |
| OPUS-S4; OPUS-S5 | Bảng đầu tệp/thứ tự tích hợp; MASK-1 soạn dự thảo đúng MASK-1/2, giữ phụ thuộc schema; câu 3A đã chốt. |
| RV — yêu cầu chung cuối review | Bảng đầu tệp và từng bảng nguồn/lát/checklist: tái dùng bắt tay/Windows Job, ≤3 tệp gồm test, whitelist trước giao, ca âm từ chính engine. |

OPUS-1/5/8/9 và RV-Chặn/RV-CS3/RV-CS4 được đối chiếu tại mục “Đã xử lý review” cuối `GIAO-ENGINE-2.md`. Đây là hoàn tất sửa tài liệu theo quyết định đã duyệt tại CD-038; phụ thuộc schema/bằng chứng khác còn giữ nguyên, chưa chạy test code/dịch vụ.

CD-038 (30/10): đã áp câu 1C/3A: dùng mẫu cổng AI chung; Anh mở khóa Mask tại máy chủ, không tự đóng khi danh mục mở; mỗi engine giữ bí mật một tài khoản máy riêng; chuyển lát tương ứng sang giao được.
