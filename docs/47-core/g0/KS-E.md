# KS-E · Khảo sát mã OCR để hiệu chỉnh thành `e_ocr`

**Kết luận:** Nên lấy **`D:\GPT\OCR` làm nguồn hiệu chỉnh**, giữ nguyên thuật toán OCR, bổ sung adapter và lớp vận hành theo Core. Nguồn này khai báo phiên bản **2.1.0**; `ocr-dual-release` khai báo **2.0.0**, có installer hướng tới thư mục OCR cũ. Không có căn cứ coi bản release là nguồn phát triển hiện hành (`O\AGENTS.md:5`; `O\pyproject.toml:7`; `R\pyproject.toml:7`; `R\install_release.py:6`).

Phần cần làm đáng kể nằm ở **contract, quản lý tiến trình/cổng, tiếp nhận kết quả trước khi mất RAM, duyệt có truy vết và điều phối nhiều người dùng**. Không cần viết lại pipeline nhận dạng.

## 1. Phạm vi và căn cứ

Khảo sát ngày **30/10/2026**, repo kế toán đang checkout `hop-nhat-20261023`, commit `5823f1a`. Chỉ đọc; không sửa tệp, chạy dịch vụ, gọi AI/ABBYY, mở dữ liệu thật hoặc chạy test.

Quy ước đường dẫn dùng trong mọi dẫn chiếu `tệp:dòng`:

| Ký hiệu | Đường dẫn gốc |
|---|---|
| `O` | `D:\GPT\OCR` |
| `R` | `D:\GPT\Local AI\ocr-dual-release` |
| `S` | `D:\GPT\Local AI\engine-console` |
| `K` | Repo kế toán đang khảo sát |
| TL 54 / TL 55 | Hai tài liệu kế hoạch tại thư mục cha của `K` |
| CD | `K\docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` |

Đã đọc TL 54, TL 55, CD-026…CD-030, các tài liệu OCR được giao và mã liên quan. Áp dụng TL 54 §14; nguyên tắc cổng theo CD-028: Core cấp cổng cố định, chuyển giao ổ nghe, mặc định tự kích hoạt/tự đóng; không mặc định OCR luôn chạy (`TL 54:385`; `CD:329–335`).

## 2. Bản đồ `D:\GPT\OCR`

| Thành phần | Vai trò và điểm vào đã thấy |
|---|---|
| `mask_ocr` | Dịch vụ OCR PDF/DOCX, CLI, pipeline Tesseract/VietOCR, dựng bảng, đối chiếu, duyệt và xuất tài liệu. Package chính chỉ đóng gói `mask_ocr*` (`O\pyproject.toml:12–19`; `O\PROJECT_CONTEXT.md:24–31`). |
| `abbyy-hotfolder` | Cầu nối độc lập tới ABBYY Hot Folder; API, CLI và thư viện Python. Điểm vào `python -m abbyy_hotfolder … serve --port …` (`O\abbyy-hotfolder\README.md:59–66`). |
| `ocr-abbyy-ai` | Ứng dụng ghép ABBYY → hiệu đính → DOCX Track Changes; import trực tiếp hai thư viện con, mặc định cổng 8030 (`O\ocr-abbyy-ai\ocr_web\app.py:25–40`). |
| `hieu-dinh-ocr` | Hiệu đính DOCX bằng từ điển và AI; có CLI, xuất Track Changes/báo cáo. Đây là phần xử lý sau OCR (`O\hieu-dinh-ocr\README.md:3–10`; `O\hieu-dinh-ocr\hieu_dinh\__main__.py:50–64`). |
| `runtimes` | Đã thấy `paddle`, `vietocr`, `paddle-onnx-deps`; đường dẫn runtime do cấu hình điều khiển (`O\setup_dual.py:13–14`; `O\mask_ocr\runtime.py:28–36`; `O\requirements-paddle-onnx.txt:1`). |
| `models-dual` | Đã thấy model VietOCR, `tessdata_best`, `paddlex`; mã đọc model từ cấu hình, hỗ trợ Paddle native hoặc ONNX (`O\setup_dual.py:32–46`; `O\mask_ocr\runtime.py:72–91`). |
| `config` | Có các cặp `service.example.json`/`service.json`, `dual-runtime.example.json`/`dual-runtime.json`. Mã đọc cổng, đường dẫn model/runtime và giới hạn worker (`O\mask_ocr\installation.py:16–24`; `O\mask_ocr\runtime.py:15–48`). Không mở cấu hình thực tế. |
| `examples` | Client HTTP độc lập: gửi bytes, poll, lấy JSON rồi DELETE. Ví dụ này ghi JSON ra đĩa và mặc định chờ 960 giây; không nên dùng nguyên trạng cho dual OCR dưới Core (`O\examples\api_client.py:37–55`). |

**Khởi động/cài đặt:**

- `start-ocr.bat` gọi `run_ocr.py`; `start-api.bat` lại gọi `start-ocr.bat`, nên hiện vẫn đi qua launcher mở trình duyệt (`O\start-ocr.bat:8`; `O\start-api.bat:8`).
- Dịch vụ trực tiếp: `.venv-api\Scripts\python.exe -B -m mask_ocr.service --port <cổng>`, nghe `127.0.0.1` (`O\mask_ocr\service.py:10–18`).
- `setup-api.bat` cài `requirements-api-lock.txt`; `setup-ocr.bat` tạo môi trường CLI từ `requirements-runtime-lock.txt` (`O\setup-api.bat:3–7`; `O\setup-ocr.bat:3–9`).
- `setup-dual.bat` gọi `setup_dual.py --import-from`; script sao chép runtime/model đã kiểm chứng trên máy, không phải bộ cài portable hoàn chỉnh (`O\setup-dual.bat:3–9`; `O\setup_dual.py:29–50`).

**Phụ thuộc và model:**

| Tệp | Nội dung chính |
|---|---|
| `requirements-api-lock.txt` | FastAPI 0.141.1, Pydantic 2.13.5, Uvicorn 0.53.0, PyMuPDF 1.28.2 (`O\requirements-api-lock.txt:6–15`). |
| `requirements-runtime-lock.txt` | `defusedxml`, PyMuPDF (`O\requirements-runtime-lock.txt:1–2`). |
| `requirements-paddle-lock.txt` | PaddlePaddle 3.2.2, PaddleOCR 3.7.0, PaddleX 3.7.2; NumPy 2.3.5 (`O\requirements-paddle-lock.txt:36–42`). |
| `requirements-vietocr-lock.txt` | VietOCR 0.3.13, Torch/Torchvision CPU; NumPy 1.26.4. Cần giữ môi trường riêng với Paddle (`O\requirements-vietocr-lock.txt:27`; `:48–53`). |
| `requirements-paddle-onnx.txt` | Sáu package inference, gồm ONNX Runtime 1.23.2, cài riêng bằng `--no-deps --target` (`O\requirements-paddle-onnx.txt:1–8`). |
| `model_hashes.json` | Hash các model Tesseract/VietOCR/Paddle, dùng tên đường dẫn `models\…`; không thấy mục ONNX trong danh sách này. `setup_dual.py` sao chép tệp hash, không xác minh model theo tệp đó (`O\model_hashes.json:2–13`; `O\setup_dual.py:49–50`). |

Các tài liệu QA là **bằng chứng lịch sử**: migration ghi 29 test OCR; pipeline ghi 100; bản sửa Paddle ghi 110. Không phải kết quả test của lượt khảo sát này (`O\MIGRATION_QA.md:7`; `O\PIPELINE_QA.md:5`; `O\PADDLE_FIX_QA.md:29`).

## 3. Quan hệ giữa các nguồn

| Quan hệ | Kết quả đối chiếu |
|---|---|
| `O` ↔ `R` | `R` là bộ release 2.0 với installer chép vào `D:\GPT\Phan mem Mask file\OCR module`; tài liệu `O` xác định `D:\GPT\OCR` là nguồn chính sau chuyển project (`R\install_release.py:5–11`; `O\PROJECT_CONTEXT.md:7–11`). |
| Khác biệt xử lý | `R` xử lý scan theo từng trang, mở/đóng detector và VietOCR trong `scan_page`. `O` chạy theo lượt toàn tài liệu: Tesseract → detection → VietOCR → hợp nhất; có VietOCR-only, manifest/reference và thời gian từng pha (`R\mask_ocr\structured.py:42–72`; `O\mask_ocr\structured.py:244–311`). |
| `O` ↔ Engine Studio | Studio đăng ký cấu hình tại GET/POST `/api/config`, kiểm tra kết nối tại POST `/api/test`, lưu registry vào SQLite. Không thấy OCR tự đăng ký vào Studio (`S\server.py:19–27`; `:224–269`; `O\mask_ocr\service.py:10–18`). |
| Contract Studio ↔ OCR | Mẫu Studio dùng `/v1/ocr/extract-text/jobs`, JSON, trường kết quả `output`; OCR thực tế dùng `/v1/jobs`, raw binary và endpoint `/result` riêng. Studio hiện chỉ chấp nhận JSON hoặc multipart trong cấu hình function (`S\server.py:35–43`; `:185–186`; `O\mask_ocr\api.py:181–213`). |
| `O` ↔ OCR-1 | OCR-1 là `CongOCR`, nhận Hot Folder/sổ Review/đệm qua constructor; không import cầu nối `abbyy_hotfolder`. M9 bọc lại `CongOCR`; `EngineOCR` hiện trả DOCX bytes qua lời gọi Python (`K\src\kho_tri_thuc\ha_tang\cong_ocr.py:127–140`; `K\src\kho_tri_thuc\m9\ocr_hot_folder.py:10–28`; `K\src\kho_tri_thuc\ha_tang\engine_cong.py:127–143`). |
| Sổ ABBYY | Cầu nối ngoài dùng `usage.json`, cấu trúc `entries` và khóa tạo tệp độc quyền; OCR-1 dùng sổ Review dạng `[epoch, số trang]` và khóa byte của hệ điều hành. Không thể coi hai sổ/khóa là dùng chung sẵn (`O\abbyy-hotfolder\abbyy_hotfolder\quota.py:21–27`; `:50–71`; `K\src\kho_tri_thuc\ha_tang\cong_ocr.py:53–77`; `:151–165`). |

**Rủi ro còn tồn tại:** OCR-1 ghi rõ Review cũ không tham gia khóa chung, vẫn có khe đua chen hàng/ghi đè sổ. Không được mô tả việc dùng chung ABBYY hiện nay là đã an toàn tuyệt đối (`K\src\kho_tri_thuc\ha_tang\cong_ocr.py:8–12`).

## 4. API thực tế và vòng đời dữ liệu

### 4.1. API `mask_ocr`

| Endpoint | Hành vi và căn cứ |
|---|---|
| GET `/healthz` | Không cần Bearer; trả service, API/UI version, `installation_id`; chưa chứng minh model chạy được (`O\mask_ocr\api.py:117`; `:152–155`). |
| GET `/v1/capabilities` | Bearer; readiness từng engine, định dạng và giới hạn (`O\mask_ocr\api.py:157–170`). |
| GET `/v1/openapi.json` | Bearer; khai báo security và các kiểu API (`O\mask_ocr\api.py:172–179`). |
| POST `/v1/jobs` | HTTP 202; query `filename`, `force_ocr`, `engine=tesseract/vietocr/dual`; body raw binary, `application/octet-stream`, có `Content-Length` (`O\mask_ocr\api.py:131–137`; `:181–202`). |
| GET `/v1/jobs/{job_id}` | Trạng thái `queued/running/succeeded/failed`, tiến độ, lỗi, TTL (`O\mask_ocr\api.py:36–44`; `:204–206`). |
| GET `/v1/jobs/{job_id}/result` | JSON; chỉ kiểm tra job `succeeded`, **không chặn bản chưa duyệt** (`O\mask_ocr\api.py:208–213`). |
| PUT `/v1/jobs/{job_id}/review` | JSON chứa revision, quyết định/vùng sửa; chỉ nhận schema 2 (`O\mask_ocr\api.py:220–226`; `O\mask_ocr\review_api.py:13–27`). |
| GET `/v1/jobs/{job_id}/download/{kind}` | DOCX/TXT/JSON; chặn khi còn pending, trừ yêu cầu draft (`O\mask_ocr\api.py:228–233`; `O\mask_ocr\review_api.py:30–46`). |
| DELETE `/v1/jobs/{job_id}` | HTTP 204; hủy việc đang chạy hoặc xóa dữ liệu RAM (`O\mask_ocr\api.py:215–218`; `O\mask_ocr\jobs.py:134–139`). |

Bearer được ánh xạ thành **owner/client**; client khác không lấy được job. API chỉ nhận kết nối local, chặn yêu cầu trình duyệt không phù hợp. Core phải gọi từ backend, không đưa khóa engine xuống frontend (`O\mask_ocr\api.py:99–130`; `O\mask_ocr\jobs.py:108–112`).

Idempotency hiện có phạm vi **owner + key trong RAM của một tiến trình**; fingerprint gồm bytes, tên tệp, `force_ocr`, engine. Cùng key nhưng khác fingerprint trả 409 (`O\mask_ocr\jobs.py:91–105`).

### 4.2. Kết quả, duyệt và giới hạn

- Schema 1 trả text/pages tương thích cũ; schema 2 bổ sung units/blocks/issues, manifest, comparison và review. Các trường cấu trúc trong response model vẫn dùng nhiều `dict`, chưa phải contract Core chặt chẽ (`O\mask_ocr\api.py:47–62`; `O\mask_ocr\structured.py:138–148`).
- Revision cũ bị từ chối 409. `review.status=final` chỉ được suy từ không còn pending; không có nghĩa đã được người có thẩm quyền nghiệp vụ phê duyệt. `comparison.performed` là thông tin riêng (`O\mask_ocr\review.py:56–81`; `O\mask_ocr\structured.py:66–70`).
- Mặc định: 20 MiB/file, 60 trang/PDF, 500.000 ký tự, 15.000 vùng; 8 job đang giữ, tổng đầu vào chờ/chạy 64 MiB; một job OCR hoạt động mỗi lúc (`O\mask_ocr\extraction.py:17–19`; `O\mask_ocr\structured.py:19`; `O\mask_ocr\jobs.py:83–103`; `:174–190`).
- Chờ hàng đợi/Tesseract mặc định 900 giây; dual/VietOCR chạy tối đa ít nhất 3.600 giây. Kết quả/lỗi hết hạn **600 giây từ lúc kết thúc**; GET/PUT review không cập nhật mốc `finished` (`O\mask_ocr\jobs.py:146–165`; `O\mask_ocr\api.py:208–226`).
- UI giữ bản riêng trong session RAM, hết hạn sau 3.600 giây không thao tác; preview cần bytes gốc. Chính sách này khác TTL API (`O\mask_ocr\web.py:25`; `:76–95`; `:114–118`; `:222–242`).
- Worker OCR trao đổi qua pipe và chặn mạng; khi dịch vụ dừng, job/result bị giải phóng (`O\mask_ocr\jobs.py:24–48`; `:192–201`).

Readiness hiện kiểm tra chủ yếu **sự tồn tại của executable/model/dependency**, chưa thử nạp và inference. Không thấy `/readyz` trong các route của `mask_ocr/api.py` (`O\mask_ocr\runtime.py:66–91`; `O\mask_ocr\api.py:152–235`).

Cổng mặc định khi thiếu cấu hình là **8016**; tài liệu bản cài ghi **8018**, chưa kiểm chứng dịch vụ đang chạy. Launcher có thể tìm thêm 10 cổng khi gặp bản 2.0; dịch vụ đã hỗ trợ `--port`, chưa thấy nhận socket chuyển giao (`O\mask_ocr\installation.py:16–24`; `O\README.md:3–5`; `O\run_ocr.py:36–71`; `O\mask_ocr\service.py:10–18`).

### 4.3. Nhánh ABBYY có API khác

Cầu nối ABBYY dùng Bearer chung, raw body, `/v1/health`, `/v1/usage`, `/v1/diagnose`, `/v1/convert`, `/v1/jobs` và tải `/files/{fmt}`. Trạng thái là `queued/running/done/failed/cancelled`; kết quả giữ RAM mặc định một giờ, nhưng Hot Folder bắt buộc trao đổi qua tệp trên đĩa (`O\abbyy-hotfolder\abbyy_hotfolder\server.py:61`; `:212–310`; `O\abbyy-hotfolder\abbyy_hotfolder\config.py:78`; `O\abbyy-hotfolder\README.md:23–26`).

Mặc định bridge nghe cổng 8020, giới hạn 100 MiB và một worker; không thấy owner theo từng client trong `Record`/`Service.get`. Không được áp dụng nguyên các bảo đảm RAM-only, owner isolation và giới hạn của dual API cho nhánh ABBYY (`O\abbyy-hotfolder\abbyy_hotfolder\config.py:70–78`; `O\abbyy-hotfolder\abbyy_hotfolder\server.py:55–67`; `:134–136`).

## 5. Danh sách hiệu chỉnh thành `e_ocr`

Đây là **đề xuất chênh lệch**, chưa phải công việc được phép lập trình. Mức nhỏ/vừa/lớn phản ánh phạm vi tích hợp, chưa phải ước lượng thời gian.

| Hiện trạng có căn cứ | Cần đổi theo Core | Mức |
|---|---|---|
| Chỉ công bố các mode nhận dạng, chưa có capability Core (`O\mask_ocr\api.py:162–170`). | Đăng ký `e_ocr`, `ocr.trich_van_ban@1`, `ocr.trich_bang@1`; khai rõ backend và giới hạn từng capability. | Vừa |
| Bảng đã có rows/cols/cells/unit_ids; vùng không chắc có cảnh báo (`O\mask_ocr\layout.py:28–51`; `:103–107`). | Adapter chuyển sang `du_lieu_bang.v1`; giữ tọa độ/cảnh báo. Chưa khẳng định suy ra kiểu dữ liệu, đơn vị hoặc bảng không đường kẻ đầy đủ. | Vừa |
| Output gồm nhiều dict; `document_id` là SHA-256 bytes (`O\mask_ocr\api.py:47–62`; `O\mask_ocr\structured.py:386`). | JSON Schema `van_ban_tai_lieu.v1`/`du_lieu_bang.v1`; ánh xạ ID Core riêng với hash nguồn, giữ provenance/revision. | Vừa |
| Health luôn trả `ok`; readiness kiểm tệp (`O\mask_ocr\api.py:152–170`; `O\mask_ocr\runtime.py:66–91`). | Phân biệt liveness/readiness; kiểm đúng danh tính/phiên bản/năng lực, bổ sung kiểm nạp model thích hợp. | Vừa |
| Chưa có trạng thái instance; job chỉ có bốn trạng thái (`O\mask_ocr\api.py:36–44`). | Engine Manager quản lý `stopped/starting/ready/busy/failed`, heartbeat và process identity, tách khỏi job. | Vừa |
| Có `--port`, Uvicorn tự bind; launcher tự dò cổng (`O\mask_ocr\service.py:12–18`; `O\run_ocr.py:36–48`). | Ưu tiên nhận `socket.fromshare`; phương án chuyển tiếp dùng `--port` do Core cấp. Không tự chọn cổng khác; xung đột phải báo lỗi. | Vừa |
| Launcher mở browser, theo dõi process rồi terminate; shutdown xóa RAM (`O\run_ocr.py:82–98`; `O\mask_ocr\jobs.py:197–201`). | Core khởi động headless; drain việc đang chạy, xác nhận bàn giao kết quả trước khi đóng; Core giữ lại cổng. | Vừa |
| Service nhận đường dẫn registry Bearer; không thấy kết nối PostgreSQL trong luồng service/API/job đã khảo sát (`O\mask_ocr\service.py:10–18`; `O\mask_ocr\api.py:65–92`). | Giữ engine không có mật khẩu CSDL; Core giữ tham chiếu khóa dịch vụ và thực hiện lưu kết quả. | Nhỏ |
| TTL API 600 giây, DELETE xóa RAM; preview cần bản gốc (`O\mask_ocr\jobs.py:134–150`; `O\mask_ocr\web.py:229–242`). | Core lấy ngay snapshot, xử lý/giữ theo chính sách được duyệt rồi mới ACK. Đặc tả cách tiếp tục review sau khi RAM engine được giải phóng; không mặc định lưu lâu dài. | Lớn |
| `/result` chỉ kiểm `succeeded`; `final` suy từ pending (`O\mask_ocr\api.py:208–213`; `O\mask_ocr\review.py:72–74`). | Tách hoàn thành xử lý, hết mục cần soát và phê duyệt nghiệp vụ; chỉ người có quyền xác nhận phê duyệt. Giữ revision/audit mỗi lần sửa. | Vừa |
| Idempotency/job queue chỉ trong một process; owner là client (`O\mask_ocr\jobs.py:83–112`). | Core chống khởi động trùng instance, claim/lease bước việc, ánh xạ người dùng/pháp nhân và idempotency bền vững; giữ một job OCR/instance ban đầu. | Lớn |
| ABBYY ngoài và OCR-1 khác sổ/khóa; Review cũ còn khe đua (`O\abbyy-hotfolder\abbyy_hotfolder\quota.py:21–71`; `K\src\kho_tri_thuc\ha_tang\cong_ocr.py:8–12`). | Một chủ điều phối Hot Folder và hạn mức chung; chuyển các bên gọi qua chủ này, không chạy song song hai hệ sổ độc lập. | Lớn |
| Hiệu đính gọi thẳng Ollama; ứng dụng ghi DOCX/báo cáo và có cache AI tùy chọn (`O\hieu-dinh-ocr\hieu_dinh\ai.py:142–177`; `O\ocr-abbyy-ai\ocr_web\app.py:315–319`). | Nếu đưa vào phạm vi: thay đường gọi bằng cổng AI phần mềm, chuyển quyền lưu/retention sang Core; giữ thuật toán từ điển/kiểm duyệt/Track Changes. | Lớn |
| Studio mới lưu mẫu cấu hình, thiếu raw binary và mẫu route không khớp (`S\server.py:35–43`; `:185–186`). | Dùng lại UI đăng ký; registry/lifecycle thuộc Core; bổ sung adapter raw binary, endpoint result riêng và lỗi chuẩn. | Vừa |

## 6. Giữ nguyên, bọc adapter, thay lớp tích hợp

| Hướng xử lý | Phạm vi |
|---|---|
| **Giữ nguyên — không đổi thuật toán OCR** | Ưu tiên native text, chuẩn hóa rotation, Tesseract/VietOCR, Paddle detection, backend ONNX hiện có, pipeline theo lượt, dựng bảng, so khác biệt và xuất Word (`O\mask_ocr\structured.py:244–311`; `O\mask_ocr\engine_worker.py:65–104`; `O\mask_ocr\review.py:78–125`). |
| **Bọc adapter** | API v1 raw binary; poll/result/delete; chuẩn hóa text/bảng/provenance/lỗi; chọn backend ABBYY hoặc OCR local và giữ revision. Tận dụng `EngineOCR` hiện có như đầu vào chuyển đổi, chưa coi đó là engine HTTP theo chuẩn mới (`O\mask_ocr\api.py:181–233`; `K\src\kho_tri_thuc\ha_tang\engine_cong.py:127–143`). |
| **Viết mới/thay lớp tích hợp** | Nhận socket, quản lý instance/idle/drain, chống chạy trùng liên worker, bàn giao snapshot, quyền duyệt theo Core, hợp nhất sổ ABBYY và thay đường gọi AI trực tiếp. Đây là thay điều phối/vận hành, không viết lại nhận dạng. |

**Đã tự kiểm:** đối chiếu tĩnh mã và tài liệu; không sửa tệp, không chạy test/model/dịch vụ. Readiness thực tế, tốc độ khởi động và số người dùng chịu tải được **chưa kiểm chứng**.

## Chờ Anh

- Chốt phạm vi đợt đầu: OCR local + ABBYY, hay gồm cả hiệu đính AI/ứng dụng `ocr-abbyy-ai`.
- Chốt chính sách giữ bản gốc, OCR chưa mask, snapshot duyệt và thời hạn; cần tiếp tục duyệt thế nào sau khi engine đóng.
- Chốt máy chạy/tài khoản dịch vụ, tải đồng thời dự kiến và đầu mối Hot Folder/sổ hạn mức chung.
- Ba bộ đặc tả CSDL/API/SDK vẫn phải được Anh duyệt trước G2 (`CD:338–344`).

## Gợi ý cho đặc tả G1

1. Chọn nguồn `O` 2.1; ghi `R` 2.0 là nguồn tham chiếu lịch sử.
2. Lập contract cho hai capability, backend và giới hạn bảng được hỗ trợ.
3. Chốt JSON Schema, ánh xạ ID/hash/reference và trạng thái duyệt độc lập.
4. Đặc tả vòng đời nhận việc → lấy snapshot → xác nhận bàn giao → giải phóng RAM.
5. Đặc tả cổng cố định, socket chuyển giao, nhận diện instance, readiness và drain.
6. Chốt một chủ điều phối ABBYY cùng sổ hạn mức; AI hiệu đính đi qua cổng AI.
7. Tiêu chí nghiệm thu dùng dữ liệu giả: đa người dùng, retry, revision xung đột, hết TTL và khởi động lại.