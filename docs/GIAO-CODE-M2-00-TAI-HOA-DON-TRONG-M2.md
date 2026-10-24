# M2-00 — Bộ "#7 Tải hóa đơn điện tử hàng loạt" thành nút "Tải từ cổng thuế" trong M2 · Hóa đơn mua vào → phải trả

**Handoff triển khai CODE — lập 21/10/2026, trạng thái SAN_SANG_GIAO khi anh Dũng ra lệnh code.** Thiết kế đã chốt 20/10 (phạm vi mục 2–6 và policy tiền tệ "Kết hợp" — TL 43 §9). Không thuộc `IMPLEMENTATION_AUTHORIZED_M4_ONLY`; chỉ bắt đầu khi anh ra lệnh cho gói này. Claude Code là coder duy nhất; không mở gói khác song song; kho thật vẫn SQLite; không nhập Junsky, không duyệt thật, không bật cloud.

## 1. Căn cứ và pin

| Căn cứ | SHA-256 (tại thời điểm lập) |
|---|---|
| [Thiết kế M2-00 = TL 43](../../THIET-KE-MODULE-DE-CHOT-2026-10-20/M2-00-NHAN-NGUON-TU-CONG-THUE.md) | `8d91ae6f1800eb9e6193fe7d5b01643322903ffed1db8443a4d73b5f0e5a5089` |
| Bản thiết kế M2 20/10 (`M2-MUA-HANG-VA-CONG-NO.md`) mục 2, 3, 4, 5, 7 | bản hiện hành trong thư mục thiết kế |
| #7 `src\server.js` / `src\job.js` / `src\portal.js` / `src\build.js` / `config.js` tại `D:\Claude\Phan mem download hoa don\` | `b8a5a222…88dd8e` / `a7fcd2e7…f1a553` / `e60575f1…d22b127` / `ca7fe35c…976f209` / `48cb8cb1…f90b02` |
| Hàng đợi `HANG-DOI-YEU-CAU.md` #40; `HANG-CHO-CODE.md` gói M2-00 | — |
| TL 40 (nhóm 2 "agent tại chỗ", nguyên tắc 11), TL 36 (mã pháp nhân), TL 38 (`nhat_ky.su_kien`, mã hóa dữ liệu nhạy cảm) | — |

Coder đọc TL 43 trọn vẹn trước khi sửa; mục này chỉ nhắc điểm neo. Nếu SHA của tệp #7 khác pin → dừng, báo Root, không tự hợp nhất.

## 2. Kết quả phải có và phần không làm

**Có:** (a) bấm "Tải từ cổng thuế" trong M2, không `run.bat`; (b) profile theo pháp nhân (`profiles\<MA_PHAP_NHAN>.env`, hồ sơ Chrome riêng, thư mục tải riêng); (c) `manifest.json` mỗi lần tải, không ghi đè; (d) bảng kê thêm 5 cột; (e) tên file XML có MST bán; (f) M2 nhận **chỉ theo manifest**, nhận hồi cứu 33 tháng đã có; (g) policy `POLICY-TIENTE-01 v1` (TL 43 §6); (h) đo captcha (`captcha_da_go`, `token_tai_su_dung`); (i) nhật ký `nhat_ky.su_kien` cho mỗi lần tải/sửa profile; (j) 11 ca M2-00-01…11 có bằng chứng DEMO.

**Không:** captcha tự động hay dịch vụ giải captcha ngoài (anh quyết 20/10); viết lại #7 sang Python; đổi endpoint/tham số API cổng thuế (chỉ `config.js`); lập lịch tự động bước tải; coi PDF là bằng chứng; suy tiền tệ/số lượng ngoài policy; nhập Junsky; phân nghĩa vụ M2/M3/M8 (M2-00 chỉ tiếp nhận K1); xóa/di chuyển dữ liệu đã tải; gửi mật khẩu/MST qua log, chat, báo cáo.

## 3. Đường gọi actual — không bịa API

**#7 (Node, giữ nguyên lõi):** `server.js` hiện có `GET /api/config` · `POST /api/start {year, month, mode: month|year, types: [purchase|sold], formats: [xml|pdf|excel]}` → `{ok, jobId}` · `GET /api/events` (SSE, heartbeat 15 s, sự kiện `log|progress|phase|month|error|done`) · `POST /api/open-folder {path}`. `job.js`: một job tại một thời điểm (`state.running`), thư mục `baseRoot/<YYYY-MM>/<mua_vao|ban_ra>/`, tên file `invoiceFileName()`, bảng kê `writeExcelSafe()`, log `last_run.log`. `portal.js`: `launchAndLogin({username,password,onStatus})` dùng `userDataDir = ../.browser-profile`, `headless:false`; `waitForToken` đọc JWT có sẵn trước khi chờ captcha; `fetchAllInvoices` gộp trùng theo `nbmst|khmshdon|khhdon|shdon`; `exportInvoiceXml` không retry với HĐ không mã. `config.js`: `QUERY_GROUPS`, `EXPORT_XML`, `EXCEL_COLUMNS`, `THROTTLE_MS`, `LOGIN_TIMEOUT_MS`.

**M2 (Python, `src\kho_tri_thuc\`):** máy chủ `giao_dien/server.py` (stdlib `ThreadingHTTPServer`, route `/api/m2`, `hoa-don/*`, dùng `k2/m2_demo.py::dang_nhap_m2, mau_danh_sach`, `k2/hoa_don.py::HoaDonK2`); tiếp nhận `giao_dien/intake.py::Intake` (kho `ho-so-goc`, `SOURCES`, `MAX_FILE_SIZE`); bộ đọc XML `nguon/hoa_don_xml.py` (identity binding 6 phần: PN, chiều, MST bán, mẫu, ký hiệu, số); quyền `k2/quyen.py`; nhật ký `ha_tang/ket_noi.py` / `ha_tang/runtime.py` (`su_kien`); cấu hình `ha_tang/config.py` + `cau_hinh.*.toml`; đường dẫn hóa đơn V12 ở `var\web-that\source-settings.json` (`paths.invoice`). Coder **đọc các tệp này trước** và nối vào contract đã có; không tạo bộ đọc XML, bộ quyền hay nhật ký mới.

## 4. Thay đổi theo tệp (danh sách được sửa; ngoài danh sách phải xin Root)

| Tệp | Thay đổi | Ghi chú |
|---|---|---|
| `#7 src\server.js` | `GET /api/profiles` (liệt kê `profiles\*.env`, không trả mật khẩu); `POST /api/start` thêm `profile` (bắt buộc), `run_by`; tùy chọn `--no-open` để không mở dashboard | Dashboard cũ giữ làm đường dự phòng, thêm ô chọn profile ở `public\index.html` |
| `#7 src\job.js` | Nhận credential theo job; `run_id = YYYYMMDD-HHMMSS`; thư mục `Download hoa don\<MA_PHAP_NHAN>\<YYYY-MM>\<chiều>\<run_id>\`; tên file `<mẫu><ký hiệu>-<số>__<MST_bán>.xml`; ghi `manifest.json` theo TL 43 §5; không ghi đè; `xml_status` từng HĐ; nhóm truy vấn lỗi ghi `nhom[].loi` | `DOWNLOAD_DIR` bỏ khỏi `.env` profile; gốc lấy từ `config.js`/tham số |
| `#7 src\portal.js` | `userDataDir` theo pháp nhân `.browser-profile\<MA_PHAP_NHAN>`; trả về `captcha_da_go`, `token_tai_su_dung`, thời gian chờ đăng nhập | Không đổi cách đăng nhập/captcha |
| `#7 config.js` | `EXCEL_COLUMNS` + 5 cột `scope, ttxly, xml_status, file_xml, hash_xml`; `PROFILES_DIR` | Cột cũ giữ nguyên thứ tự (M8 đọc) |
| `#7 .env.example`, `README.md`, `.gitignore` | Mô tả profile; `profiles\` và `.browser-profile\` vào `.gitignore` | — |
| `src\kho_tri_thuc\m2\tai_hoa_don\` (gói con mới) | `tien_trinh.py` (khởi động/kiểm sống/tắt `node src\server.js`, port từ cấu hình), `khach.py` (client HTTP + SSE), `manifest.py` (đọc/validate manifest, sinh manifest `HOI_CUU`), `nhan.py` (intake theo manifest → `HoaDonK2` / `Intake`, policy tiền tệ, revision/conflict) | Chỉ stdlib + `openpyxl` (đọc bảng kê); không thêm thư viện |
| `src\kho_tri_thuc\giao_dien\server.py` + assets | Route `GET/POST /api/m2/tai-hoa-don/*` (profiles, bắt đầu, sự kiện, trạng thái, nhận); nút/ô chọn/thanh trạng thái trong tab Hóa đơn mua theo TL 43 §3 | Giữ look shell hiện có; quyền theo `k2/quyen.py` |
| `cau_hinh.*.toml` / `ha_tang/config.py` | `[tai_hoa_don] goc_bo_tai`, `port`, `thu_muc_tai` | Giá trị thật chỉ trong `cau_hinh.that.toml` trên máy anh |
| `tests\` | Test cho manifest/intake/policy/hồi cứu (fixture tự tạo, **không dữ liệu thật**); test tiến trình con mock | Không đưa XML thật vào `tests\fixtures` |
| `CHANGELOG.md`, `docs\BAO-CAO-M2-00.md`, `HANG-DOI-YEU-CAU.md` #40 | Dòng CHANGELOG có số đo trước/sau; báo cáo có bảng 11 ca; trạng thái #40 | — |

## 5. Hợp đồng dữ liệu

`manifest.json` đúng bảng TL 43 §5 (các nhóm Lần chạy · Đăng nhập · Truy vấn · Tổng · Từng hóa đơn · Lỗi chung). Khóa identity trong manifest là `key_canonical = nbmst|khmshdon|khhdon|shdon`; intake ánh xạ sang identity binding 6 phần của `nguon/hoa_don_xml.py` bằng cách thêm pháp nhân (từ profile) và chiều (từ thư mục). Hash = SHA-256 bytes. Manifest `HOI_CUU`: `nguon = "HOI_CUU"`, `xap_xi = true`, thời điểm = mtime file, `xml_status` suy từ bảng kê có dòng mà không có XML. Policy tiền tệ ghi trong một tệp quy tắc có phiên bản (`POLICY-TIENTE-01`, v1) nạp lúc intake, không hard-code trong hàm.

## 6. Ca kiểm bắt buộc (bằng chứng DEMO không rỗng)

M2-00-01…11 nguyên văn TL 43 §8. Thêm ba ràng buộc kiểm: (1) chạy lại intake cùng manifest → số bản ghi không đổi (idempotent); (2) manifest bị sửa tay (hash lệch file) → M2 từ chối, báo đúng file; (3) mật khẩu không xuất hiện trong manifest, log, nhật ký, HTTP response (grep bằng chứng). Ca có captcha (M2-00-07) được phép ghi nhận bằng cách coder tự đăng nhập trong DEMO trên máy anh; Root không yêu cầu anh thao tác.

## 7. Điều kiện kết thúc và bàn giao

- Self-test: `.\test.ps1` xanh toàn bộ + test mới; `node` self-test của #7 (`test\test.js`) không đổi kết quả.
- Báo cáo `docs\BAO-CAO-M2-00.md`: 11 ca + 3 ràng buộc có PASS/FAIL và đường dẫn bằng chứng; số đo: số lần chạy có/không captcha, thời gian khởi động Node, thời gian intake hồi cứu 33 tháng; danh sách tệp đã sửa + SHA trước/sau.
- Review độc lập (agent riêng chưa thấy quá trình) trước khi xếp `CHO_ANH_NGHIEM_THU`; anh chỉ bấm thử nút trên máy anh.
- Mọi quyết định mới phát sinh (ví dụ bảng mã `tthai`, danh sách pháp nhân) ghi `[CẦN ANH XÁC NHẬN]` trong báo cáo, không tự chốt.
