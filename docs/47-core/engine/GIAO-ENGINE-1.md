# Bản giao việc `e_ocr` — v1.0

**Ngày Anh duyệt căn cứ:** 30/10/2026. **Căn cứ:** CD-028, CD-033, CD-035, CD-036; `docs\47-core\PHIEU-DUYET-CSDL.md` (1A/2A/3A), `PHIEU-DUYET-API.md` (1A/2A).  
**Thay đổi:** v1.0 — bản đầu. **Trạng thái:** chỉ tài liệu; chỉ lập trình sau khi Anh duyệt SDK bản 2 và có CD mở lại.

**Kết luận:** Bọc nguồn OCR chính thức thành `e_ocr`, lấy ABBYY FineReader/Hot Folder làm lõi theo CD-035. Giữ thuật toán và test gốc; Core quản lý thư mục in/out, quyền, việc và lưu kết quả.

**Bắt buộc — mục tiêu và contract kỹ thuật**

| Capability | Vào → ra |
|---|---|
| `ocr.trich_van_ban@1` | `tham_chieu_tep.v1` → `van_ban_tai_lieu.v1` |
| `ocr.trich_bang@1` | `tham_chieu_tep.v1` → `du_lieu_bang.v1` |

Core kiểm quyền rồi cấp bytes/tham chiếu theo việc. Adapter chuyển DOCX hoặc kết quả cấu trúc nguồn sang contract; giữ hash, revision, vị trí và cảnh báo, không tự suy kiểu/đơn vị còn thiếu. Core tự gắn provenance từ instance/lease. Hoàn thành OCR, hết mục cần soát và duyệt nghiệp vụ là ba trạng thái riêng; chỉ công bố capability thực đạt.

**Nguồn chính thức và bảng dùng lại** — ký hiệu `O` = `D:\GPT\OCR`.

| Phân loại | Phần việc và căn cứ |
|---|---|
| **Dùng lại nguyên** | Tích hợp ABBYY của `O\ocr-abbyy-ai\ocr_web\app.py:25`, nhận DOCX tại `:277`; thư viện `O\abbyy-hotfolder\abbyy_hotfolder\client.py:113`. Giữ phần xử lý/tệp kết quả hiện có tại `app.py:315`, không mặc nhiên đưa hiệu đính AI vào phạm vi. |
| **Bọc** | Chuyển kết quả văn bản/bảng từ `O\mask_ocr\layout.py:28`, `:149`; dùng pipeline có sẵn tại `O\mask_ocr\structured.py:244`. |
| **Sửa** | Không sửa bản gốc khi chưa hỏi Anh. Phạm vi hiệu đính AI: **chờ Anh**; nếu được đưa vào, gọi qua `e_hoi_ai`. |
| **Viết mới** | Chỉ adapter contract, khung nhận cổng/readiness/dừng và lớp vận hành Core, vì nguồn chưa có giao tiếp/vòng đời Core đầy đủ. Không viết lại OCR. |

Ưu tiên bọc; chỉ sao chép code khi bắt buộc, ghi nguồn, phiên bản và SHA256 bản gốc.

**Bắt buộc — vận hành:** Core giữ cổng loopback cố định; nhận listener bằng `socket.share()`/`fromshare()`. Nhánh nguồn cũ nhận `--port` là chuyển tiếp có khoảng hở; cổng bị chiếm thì báo lỗi, không dò cổng khác. Kiểm instance, phiên bản và capability thực trước phục vụ. Bàn giao kết quả, chờ Core xác nhận rồi mới giải phóng/dừng. Mặc định tự kích hoạt/tự dừng; Core ghi thời gian yêu cầu, tới ready, xử lý, rảnh, số lần/ngày, RAM/CPU; chỉ Admin áp dụng đề xuất chế độ.

Chạy bằng tài khoản hạn chế khác Core; không login CSDL, không giữ mật khẩu/khóa. **ABBYY cần tài khoản riêng: ngoại lệ, hỏi Anh**; không tự nới quyền. Script tài khoản/ACL phải chạy lại được.

**Chia lát — Codex làm chính:** tuần tự (1) manifest + schema + test contract; (2) adapter văn bản + test; (3) adapter bảng + test; (4) khung chạy + test vòng đời; (5) adapter vận hành Core + test tích hợp. Mỗi lát ≤3 tệp, tính cả test; lead khóa danh sách đường dẫn trước giao.

**Khuyến nghị:** Dùng `O\abbyy-hotfolder\tests\fake_hotfolder.py` để kiểm độc lập bằng dữ liệu tổng hợp.

**Module được làm / không được làm:** `mau_demo` được gửi capability qua SDK Core và theo dõi việc; không gọi cổng engine, đọc thư mục Hot Folder hoặc tự phê duyệt OCR. Không gọi Cloud trực tiếp, không che tiền/ngày.

**Checklist trước khi nộp gói**

- [ ] Test gốc tại `O\ocr-abbyy-ai\tests`, `O\abbyy-hotfolder\tests`, `O\tests` đạt; kiểm lại các ca tương ứng qua engine bằng cùng dữ liệu giả.
- [ ] Schema, bảng/ô gộp, revision, bàn giao trước dừng, readiness, tài khoản hạn chế và cổng đạt kiểm.
- [ ] Không lỗi mới so với `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md`; báo đạt/tổng và phần chưa kiểm, không tính skip là đạt. Lát tài liệu này chưa chạy test.

**Phụ lục:** `docs\47-core\g1\DAC-TA-SDK.md` §4, §6.2; `CONTRACT-DU-LIEU.md` §4–6, §13, §15.2 và bộ kiểm KT06/08/09/10/14/16; khảo sát `docs\47-core\g0\KS-E.md`.

---

# Bản giao việc `e_mask` — v1.0

**Ngày Anh duyệt căn cứ:** 30/10/2026. **Căn cứ:** CD-028, CD-033, CD-035, CD-036; `docs\47-core\PHIEU-DUYET-CSDL.md` (1A/2A/3A), `PHIEU-DUYET-API.md` (1A/2A).  
**Thay đổi:** v1.0 — bản đầu. **Trạng thái:** chỉ tài liệu; chỉ lập trình sau khi Anh duyệt SDK bản 2 và có CD mở lại.

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
| **Dùng lại nguyên** | Gợi ý/che/kiểm tại `M\privacy\core.py:79`, `:308`, `:325`; API che/mở tại `M\privacy\auto_api.py:291`, `:362`; kho lượt tại `:172`. |
| **Bọc** | API MASK-1/2: `M\privacy\server.py:1554`, `:1561`, `:1600`. Phần xuất tài liệu tại `:982` hiện thuộc luồng UI, cần adapter theo contract được chốt. |
| **Sửa** | Không sửa bản gốc khi chưa hỏi Anh. Nếu được phép sửa Mask v2, theo `M\CLAUDE.md:43`: không git, ghi CHANGELOG, test và benchmark độ phủ không giảm. |
| **Viết mới** | Chỉ adapter contract, khung cổng/readiness/dừng và lớp vận hành Core; cần để nối quyền, lượt và vòng đời Core, không tạo bộ che khác. |

Ưu tiên bọc; sao chép bắt buộc phải ghi nguồn, phiên bản và SHA256. Không đọc/sửa dữ liệu thật, `*.key`, `*.maskvault`, `*.maskkeep`.

**Bắt buộc — vận hành:** Tài khoản hạn chế khác Core, không login CSDL hoặc giữ mật khẩu/khóa; script tài khoản/ACL chạy lại được. Core giữ/chuyển giao cổng loopback; nhánh cũ dùng đúng `--port`, không dò cổng khác. Readiness kiểm instance, phiên bản và tình trạng danh mục/capability, không chỉ `/healthz`. Không dừng khi lượt che còn dùng hoặc kết quả chưa bàn giao. Cách mở lại danh mục sau restart: **chờ Anh**, không lưu mật khẩu để tự mở. Core đo yêu cầu→ready, xử lý, rảnh, số lần/ngày, RAM/CPU; chỉ Admin áp dụng đề xuất chế độ.

**Chia lát — Codex làm chính:** tuần tự (1) manifest + khai báo contract đã chốt + test; (2) adapter che/mở + test; (3) adapter phát hiện + test, sau chốt contract; (4) adapter tài liệu + test, sau chốt contract; (5) khung chạy + test; (6) adapter vận hành Core + test tích hợp. Mỗi lát ≤3 tệp, gồm test; lead khóa đường dẫn trước giao.

**Khuyến nghị:** Dùng fixtures tổng hợp và transport giả hiện có; giữ nguyên bộ benchmark chính và `held_out`.

**Module được làm / không được làm:** `mau_demo` được yêu cầu Mask qua Core; không lấy mapping, khóa hoặc gọi API UI để bỏ qua quyền/revision. Không gọi Cloud trực tiếp; không che tiền/ngày.

**Checklist trước khi nộp gói**

- [ ] Test gốc `M\tests` đạt và các ca tương ứng đạt qua engine bằng dữ liệu giả; benchmark chính/`held_out` không giảm.
- [ ] Kiểm danh mục khóa, còn sót, lượt hết hạn/sai pháp nhân, restart, bảo toàn tiền/ngày và không dừng khi lượt còn dùng.
- [ ] Contract chưa chốt không được kích hoạt; không lỗi mới so với nền. Báo đạt/tổng, phần chưa kiểm; lát tài liệu này chưa chạy test.

**Phụ lục:** `docs\47-core\g1\DAC-TA-SDK.md` §4, §6.2; `CONTRACT-DU-LIEU.md` §8, §13, §15.2, bộ kiểm KT06/08/09/10/16; khảo sát `docs\47-core\g0\KS-D.md` §3.1.

---

# Bản giao việc `e_hoi_ai` — v1.0

**Ngày Anh duyệt căn cứ:** 30/10/2026. **Căn cứ:** CD-028, CD-033, CD-035, CD-036; `docs\47-core\PHIEU-DUYET-CSDL.md` (1A/2A/3A), `PHIEU-DUYET-API.md` (1A/2A); nguyên tắc cổng AI tại TL 48.  
**Thay đổi:** v1.0 — bản đầu. **Trạng thái:** chỉ tài liệu; chỉ lập trình sau khi Anh duyệt SDK bản 2 và có CD mở lại.

**Kết luận:** Tách giao tiếp cổng AI hiện có thành engine chung `e_hoi_ai`, capability `ai.hoi@1`. Local luôn có đường sử dụng; Cloud chỉ qua quy trình che/mở che của `e_mask`. “Local luôn có” không có nghĩa tiến trình/model mặc định luôn chạy.

**Bắt buộc — contract kỹ thuật**

Đầu vào chuyển từ `YeuCauAI`: `loai_viec`, `van_ban`, `chi_dan`, `truong`, `dinh_danh_da_biet`; danh tính, pháp nhân và việc lấy từ Core đã xác thực. Phải hỗ trợ cờ **“chỉ Local”** cho M9: không gọi Cloud kể cả Local lỗi, thiếu chắc chắn hoặc được chọn kiểm xác suất. Tên trường và JSON Schema đầu vào chứa cờ này: **chờ Anh**, không tự chốt contract mới.

Đầu ra `tra_loi_ai.v1`: giữ trường, dẫn chứng, nguồn từng trường, giá trị Local trước khi Cloud thay, lý do và trường bị loại; không tự biến kết quả theo trường thành câu trả lời tự do. CLOUD/LOCAL+CLOUD phải gắn `luot_che_id` đúng việc/pháp nhân, còn hạn và kết quả kiểm mở che. Model cấu hình không được ghi thành bằng chứng model thực chạy. Có kết quả không đồng nghĩa đã duyệt.

**Nguồn chính thức và bảng dùng lại** — ký hiệu `A` = `src\kho_tri_thuc\tri_thuc\cong_ai.py` trong repo.

| Phân loại | Phần việc và căn cứ |
|---|---|
| **Dùng lại nguyên** | AI-1/AI-2: `YeuCauAI`, `TruongAI`, `KetQuaAI` tại `A:275`, `:296`, `:305`; đo/thống kê và chọn kiểm tại `:1009`, `:1033`; Local trước tại `:1236`. |
| **Bọc** | Seam tiêm Local/Mask/provider tại `A:988`; kiểm trước gửi Cloud tại `:1149`; che/mở che tại `:663`, `:683`. Bọc kết nối Mask qua `e_mask`, giữ quy tắc hiện có. |
| **Sửa** | Không sửa bản gốc khi chưa hỏi Anh. Không chuyển `BoGhiPostgres` tại `A:421` hoặc credential CSDL vào engine. |
| **Viết mới** | Chỉ adapter contract/cờ chỉ Local, khung cổng/readiness/dừng và lớp vận hành Core; cần cho ranh giới tiến trình, bàn giao kết quả và metadata. Không viết Cloud client hoặc bộ che mới. |

Ưu tiên bọc; chỉ sao chép khi bắt buộc, ghi nguồn, phiên bản và SHA256.

**Bắt buộc — AI và vận hành:** Giữ đánh giá độ chính xác Local và kiểm xác suất theo TL 48; không tự đặt lịch/ngưỡng mới. Che cả dữ liệu và chỉ dẫn có nội dung nguồn trước nhánh Cloud; kiểm mở che và dẫn chứng sau trả lời. Không gửi XML hóa đơn thô, không che tiền/ngày, không tạo đường Cloud trực tiếp ngoài cổng AI hiện có.

Engine chạy tài khoản hạn chế khác Core, không login CSDL, không giữ mật khẩu/khóa; metadata bàn giao Core ghi. Core giữ/chuyển giao cổng loopback, xác minh instance/phiên bản/capability và Local thực sẵn sàng; không chỉ đọc cấu hình. Drain, bàn giao rồi xác nhận dừng; giữ lượt Mask tới khi dùng xong. Mặc định tự kích hoạt/tự dừng. Core đo yêu cầu→ready, xử lý, rảnh, số lần/ngày, RAM/CPU; chỉ Admin áp dụng đề xuất. Script tài khoản/ACL phải chạy lại được.

**Chia lát — Codex làm chính:** tuần tự (1) manifest + schema đầu vào đã chốt + test; (2) adapter `ai.hoi@1`/chỉ Local + test; (3) adapter `e_mask` + test; (4) khung chạy + test; (5) adapter metadata vận hành Core + test tích hợp. Mỗi lát ≤3 tệp, gồm test; lead khóa đường dẫn trước giao.

**Khuyến nghị:** Tận dụng `local_transport`, Mask/provider giả và hàm chọn kiểm xác suất được tiêm sẵn để kiểm độc lập, xác định được kết quả.

**Module được làm / không được làm:** `mau_demo` được gọi `ai.hoi@1` qua SDK Core và yêu cầu chỉ Local; không chọn URL/provider tùy ý, lấy khóa, gọi Cloud trực tiếp hoặc coi AI là người duyệt.

**Checklist trước khi nộp gói**

- [ ] Test gốc `tests\test_cong_ai.py`, `test_cong_ai_nhat_ky.py` và ca liên quan trong `test_xs3_cong.py` đạt; các ca tương ứng đạt qua engine bằng dữ liệu giả.
- [ ] Chỉ Local tạo **0 lời gọi Cloud**; Mask lỗi/khóa/còn sót, lượt hết hạn, mở che lỗi và dẫn chứng sai đều bị chặn đúng.
- [ ] Không lộ bí mật, không login CSDL, bảo toàn tiền/ngày và giá trị Local; không lỗi mới so với nền. Báo đạt/tổng, phần chưa kiểm; lát tài liệu này chưa chạy test.

**Phụ lục:** `docs\47-core\g1\DAC-TA-SDK.md` §2–4, §6.2; `CONTRACT-DU-LIEU.md` §8–9, §13, §15.2, bộ kiểm KT06/08/09/10/14/16; khảo sát `docs\47-core\g0\KS-A.md`, `KS-D.md`.