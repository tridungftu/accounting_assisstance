# Báo cáo M4-01C — Cổng hồ sơ xây dựng và giao diện gói 1 (CODE_ONLY)

**20/10/2026 · CODE_ONLY · self-test của Claude: NOT_RUN.** Không chạy lệnh/Python/Node/import/test/SQL/HTTP/browser/AI/OCR/launcher. Chưa có screenshot hay runtime nào. Đây là bàn giao mã nguồn, **không** phải nghiệm thu GUI, C hay toàn M4. Root kiểm HTTP/GUI/18 ca sau terminal/freeze.

Căn cứ: [GIAO-CODE-M4-01C](GIAO-CODE-M4-01C-KHEP-CONG-HO-SO-VA-GUI.md), [kế hoạch M4](M4-KE-HOACH-DA-CHOT-20261020.md), B/B2/B3 và báo cáo [M4-01B](BAO-CAO-M4-01B.md). Contract UI lấy đúng `giao_dien/m4.py` + `k2/xay_dung.py` của B6.

## 1. Tệp đã ghi (đúng 11 target)

| Tệp | Loại | Nội dung |
|---|---|---|
| `src/kho_tri_thuc/m4/giao_dien/m4.js` | mới | Toàn bộ client Cổng hồ sơ trong `#page-m4` |
| `src/kho_tri_thuc/m4/giao_dien/m4.css` | sửa | Thêm lớp trạng thái/lỗi/ô gốc BOQ/khổ 1280–1440; mọi selector dưới `.m4` |
| `src/kho_tri_thuc/giao_dien/assets/app.js` | sửa | Seam đổi vai chung có đăng ký; CRM vào seam; `pages.m4`; `window.kttChung` |
| `src/kho_tri_thuc/giao_dien/assets/index.html` | sửa | Nội dung chờ trong `#page-m4` (khi m4.js chưa chạy). Nav/asset `/m4.js` `/m4.css` đã có từ trước |
| `src/kho_tri_thuc/giao_dien/m4.py` | sửa | Route tệp mẫu DEMO `GET /api/m4/mau`, `GET /api/m4/mau/{tên}` (whitelist) |
| `src/kho_tri_thuc/k2/crm_khoi_dong.py` | sửa | `chuan_bi` gọi `m4_demo.khoi_tao(admin)` và trả `m4_seed` |
| `pyproject.toml` | sửa | Package data cho `kho_tri_thuc.m4` (UI + tệp vendor không-Python + mã vendor) |
| `tests/test_m4_01c.py` | mới | Kiểm tĩnh/thuần |
| `tests/test_m4_01c_http.py` | mới | HTTP thật + PostgreSQL DEMO mới |
| `tests/m4_01c_async.cjs` | mới | Ca bất đồng bộ trên mã thật app.js + m4.js |
| `docs/BAO-CAO-M4-01C.md` | mới | Báo cáo này + hướng dẫn bấm 18 ca |

Không sửa: `server.py` (đã dispatch `/api/m4*`, `/m4*`), `k2/xay_dung.py`, `m4_demo.py`, `sql_m17.py`, `nguon_review`/`nap_ghim`/`docx_an_toan`/`store`, migrations 1–17, vendor/reference, fixtures, M9, CRM/M2/M5/L11 business logic. Không có SQL/schema mới. Không xóa/rename/cleanup tệp nào.

## 2. Đường gọi thật (không bịa API)

| Thao tác trên UI | HTTP | Ghi chú |
|---|---|---|
| Mở `#m4`, Làm mới | `GET /api/m4` | `cau_hinh:false` → hướng dẫn mở MỞ BẢN DEMO.cmd. `ghi_nguon.san_sang=false` → khóa tải/trích/BOQ/sửa tham số, giữ nháp. `pham_vi` rỗng → báo vai không có phạm vi |
| Đổi vai | `POST /api/m4/danh-tinh {dang_nhap}` | Danh sách lấy từ `danh_tinh_demo`; qua cổng đổi vai chung |
| Mở HĐ | `GET /api/m4/hop-dong/{id}` | 404/403 → bỏ lựa chọn, báo ngoài phạm vi |
| Mở đợt | `GET /api/m4/dot/{id}` | `thieu`/`du_can_cu`/`nop`/`hieu_luc` |
| Tải tệp | `GET /api/m4/tep/{id}` | Có token + cookie. Chỉ click khi fence còn đúng và bytes khác rỗng |
| Tải lên | `POST /api/m4/tep` | Body là bytes File. `X-M4-Info=encodeURIComponent(JSON{du_an_id,vai_tro,ten,media_type,khoa})`, ≤ 4000. Chặn rỗng/vượt `tai_len_toi_da_byte` trước khi gửi. Hash/byte trong response chỉ hiển thị |
| Tệp mẫu DEMO | `GET /api/m4/mau`, `GET /api/m4/mau/{tên}` → rồi `POST /api/m4/tep` | Xem §4 |
| Tạo HĐ / gắn tệp / trích | `POST hop-dong/{tao,gan-tep,trich}` | revision = `ho_so.revision` của GET hiện hành |
| Sửa / xác nhận tham số | `POST tham-so/{sua,xac-nhan}` | UI không gửi `kiem_tra`; kết quả máy kiểm hiển thị từ response |
| Phụ lục | `POST phu-luc/{khai,them,huy}` | Lựa chọn khai chỉ KHONG_CO/CO_CHUA_DU/CO_DU; `CHUA_KHAI` chỉ hiển thị trạng thái |
| BOQ | `POST boq/xem {tep_id}` → `{tep_id,sheet}` → `POST boq/nhap` | Gợi ý tiêu đề/cột chỉ điền sẵn. Nhập theo đúng sheet đang xem trước. `phu_luc_id` null = BOQ gốc |
| Đợt | `POST dot/{tao,sua,gan-tep,nop}` | Nộp lấy `revision_ho_so = dot.revision_ho_so` và `revision_dot = dot.revision` từ GET đợt hiện hành |

Response mutation là kết quả lệnh đã flatten, kèm `lap_lai`; UI báo rõ khi là biên nhận cũ. Sau mỗi lệnh thành công, UI GET lại (có fence), không tự suy trạng thái.

Lỗi `{error,message}` được hiện nguyên văn:
- **409 `M4_REVISION_CU`:** tải lại dữ liệu hiện hành và **giữ nháp** trên form (khôi phục theo id ô). Người dùng xem lại rồi gửi với revision mới; UI không tự vượt revision.
- **Mất kết nối / 5xx:** nút **“Gửi lại y nguyên (cùng khóa)”** gửi đúng body + khóa cũ.
- **403 / 404 / 413 / 503 / 400:** hiện message; giữ nháp và khóa.

## 3. Phiên chung, fence, retention

### Seam đổi vai (`app.js`)

- `dangKyVai(ten, xoa, nap)` + `vaiThanhVien`. Đăng ký `crm`, `m5`, `m2`, `l11`; `m4.js` tự đăng ký `m4`.
- `doiVaiChung()` gọi `xoa()` của **mọi** người tham gia, đồng bộ, trước await đầu tiên. Sau đó dùng một hàng POST đổi vai tuần tự (`vaiCho`) và barrier GET (`vaiChan`/`vaiDangChan`). Chỉ ý định mới nhất mở barrier; `moChanVaNap` nạp lại module khởi tạo và các module đã xin nạp trong lúc chặn.
- **CRM vào seam:**
  - `crmXoaTrangThai` (epoch + xóa cache/DOM/selector);
  - `crmLoad` có barrier + thế hệ GET;
  - `crmAct` bỏ phản hồi của epoch cũ;
  - đối chiếu trích lại có fence;
  - tải file soát qua `crmTai` có fence;
  - nút đổi vai CRM đi qua `doiVaiTuanTu`.
- **M9 giữ nguyên trạng.** Không đăng ký vào seam, không sửa mã. Đổi vai trong M9 vẫn theo cơ chế cũ của M9; đây là giới hạn đã khai.
- `window.kttChung` chỉ lộ: `node`, `empty`, `toast`, `size`, `date`, `dangKyVai`, `vaiDangChan`, `doiVaiTuanTu`. Không lộ token, actor hay quyền.

### Fence trong `m4.js`

- Fence gồm epoch vai/lựa chọn, actor, HĐ và đợt đang mở, cộng thế hệ GET (tổng quan/HĐ/đợt). Kiểm sau mọi await, trước khi vẽ/toast/tải.
- Đổi HĐ cũng tăng epoch: nháp/kết quả của HĐ cũ không gắn sang HĐ mới.
- Tải về: bytes đến trễ sau đổi vai/lựa chọn thì không click. UI không tuyên bố thu hồi được bytes đã giao hợp lệ trước đó.

### Khóa thao tác

- Khóa sinh theo `(route, body gốc)` và giữ đến khi có kết quả thật.
- Bấm lặp khi còn chờ không gửi thêm.
- Gửi lại cùng body dùng cùng khóa, nên máy chủ trả biên nhận cũ và không chạy lại parse/AI.
- Đổi vai thì xóa khóa và nháp.

### Retention

UI/test/helper không xóa nguồn, tệp, DB, role, attempt hay staging.

## 4. Tệp mẫu DEMO (route mỏng, đề xuất C)

- `GET /api/m4/mau` liệt kê `{ma, vai_tro, media_type, mo_ta}`. `GET /api/m4/mau/{tên}` trả **bytes nguồn** do builder có sẵn trong `kiem_chung/fixtures_m4.py` dựng.
- Danh sách tên cố định (`MAU`): `hop_dong.docx`, `hop_dong_con_sua_doi.docx`, `hop_dong.pdf`, `boq_goc.xlsx`, `boq_lech_so_hoc.xlsx`, `boq_trong_va_0.xlsx`, `boq_so_khong_doc.xlsx`, `boq_ten_gia_loi.xlsx`, `boq_phu_luc.xlsx`, `phu_luc_01.pdf`, `ho_so_dot_ky1.pdf`, `ho_so_dot_ky2.pdf`.
- **Điều kiện truy cập:**
  - cần token (`/api/` là private);
  - cần cookie phiên hiện có (`crm_phien`, không tự cấp phiên mới);
  - cần quyền **soạn M4 hiện hành** ở ít nhất một dự án (`tong_quan(...).pham_vi[].soan` đọc từ CSDL).
  - Tên ngoài whitelist → 404. Không nhận đường dẫn.
- **Phạm vi:** route không ghi gì và không seed trích XONG / BOQ DA_MAP / xác nhận / nộp / biên nhận. Người dùng chọn mẫu, UI tải bytes, rồi đi **đúng** `POST /api/m4/tep` như tệp thật. Máy chủ kiểm bytes/tên/media/OOXML như mọi tệp.

## 5. Bootstrap, launcher, package

- **Bootstrap:** `crm_khoi_dong.chuan_bi` gọi `m4_demo.khoi_tao(admin)` sau CRM/M5/M2/L11, bằng **cùng kết nối chủ** của bước chuẩn bị. Kết quả trả nguyên trạng ở `m4_seed` (`DU` / `THIEU` / `CHUA_SAN_SANG` / `DA_THU_HOI` theo từng actor). Không đổi thành DU, không chặn CRM khi M4 thiếu. `m4_demo` vốn một lần, giữ thu hồi, không cấp lại.
- **Launcher:** không sửa. `MỞ BẢN DEMO.cmd` → `start-web.ps1` → `tools/chuan_bi_crm_demo.py` → `chuan_bi` giờ seed M4. Bấm mở shell rồi chọn **Hồ sơ xây dựng (M4)** là đủ; không cần CLI/DSN/SQL.
- **Package data `kho_tri_thuc.m4`:** khai báo:
  - `giao_dien/*.js|*.css`;
  - `review_goc/**/*.py` (vendor nạp qua bộ nạp ghim);
  - `trich_xuat/DANH_MUC_THAM_SO.xlsx`;
  - `app_kiem_tra_ho_so/danh_muc_tai_lieu.csv`;
  - `giao_dien/fonts/*.css|*.woff2|OFL.txt`.

  **Chưa build wheel/cài thử — NOT_RUN.** Khai báo glob không đồng nghĩa đã đóng gói đạt. Nguồn/pin/vendor không đổi.

## 6. Màn hình — hiện có / nối ở C / gói sau

| Vùng | Trạng thái C | Thao tác thật |
|---|---|---|
| Vai & phạm vi | NỐI Ở C | Đổi vai qua seam chung. Phạm vi từ máy chủ; dự án ngoài phạm vi không hiện |
| Danh sách HĐ/đợt | NỐI Ở C | Lọc theo chữ. Mở HĐ/đợt. Tạo hồ sơ HĐ (một lần/HĐ). Trạng thái trống/không quyền/chưa sẵn sàng |
| Nguồn HĐ & trích | NỐI Ở C | Tải tệp thật/mẫu. Pool tệp dự án tách khỏi “tệp HĐ hiện hành”. Gắn tệp HĐ. Chạy trích (quy tắc, chưa có Local AI). Lịch sử trích |
| Tham số (37) | NỐI Ở C | Bảng đủ cột máy chủ; lọc mã thiếu; sửa có trích dẫn/lý do; máy kiểm do máy chủ trả; phòng dự án xác nhận; hiển thị còn/hết hiệu lực. Không tự xác nhận |
| Phụ lục | NỐI Ở C | Khai; thêm (Đã ký/Dự thảo, đổi BOQ, tệp); hủy có lý do (giữ lịch sử) |
| BOQ | NỐI Ở C | Tệp → sheet → xem trước → dòng tiêu đề → map 7 trường → nhập gốc/PL. Lỗi chặn vs phát hiện tách riêng. Ô gốc trống ≠ 0, chữ hiện nguyên văn, thành tiền giữ nguyên. Tối đa 2.000 dòng BOQ gốc |
| Đợt/checklist | NỐI Ở C | Tạo đợt; sửa ngày; checklist; tải + gắn tài liệu theo mục (gợi ý mục chỉ tham khảo); hiệu lực PL/BOQ tại ngày |
| Kiểm trước nộp / Nộp | NỐI Ở C | `thieu` từ GET đợt, mỗi mục có nút **“Bổ sung →”** tới vùng tương ứng. Nộp chỉ bật khi `du_can_cu`, vẫn xử lý từ chối của máy chủ. Ảnh chụp căn cứ sau nộp |
| Reviewer | NỐI Ở C | Thấy đợt đã nộp, đọc checklist/ảnh chụp, tải tệp được phép; không có nút soạn/duyệt |
| Lộ trình Review | HIỆN TRẠNG THẬT | Tab “Lộ trình Review” |

Các nhánh còn **CHƯA NỐI**, không có nút:
- **M4-02:** Review L1–L3, ghép/chạy lại, OCR/Local AI, Duyệt + PDF, báo cáo/tác vụ;
- **M4-03:** kế toán NT/công nợ;
- **M4-04:** Request;
- **M4-05:** kiểm xuyên suốt;
- **HOÃN:** CAD và tài khoản nhà thầu ngoài.

## 7. Ca kiểm đã viết (NOT_RUN)

**`tests/test_m4_01c.py`** (tĩnh/thuần):
- **Shell:** thứ tự app.js → m4.js; nav/section; `pages.m4` trước `route()`; seam đăng ký `crm`/`m5`/`m2`/`l11`, không `m9`; CRM đổi vai qua `doiVaiTuanTu`, barrier, `crmGen`, `crmTai`.
- **m4.js:**
  - mọi POST thuộc `TRUONG` thật và đủ 15 route;
  - không gửi khóa authority (`kiem_tra`, `sha256`, `actor`, `trang_thai`, …);
  - không innerHTML/eval;
  - seam + fence; tải chỉ click sau fence và khi bytes khác rỗng;
  - giữ khóa đến khi có kết quả; có nút gửi lại;
  - đủ cột tham số; Nộp lấy hai revision từ GET;
  - không route giả Duyệt/PDF/Request.
- **CSS:** mọi selector dưới `.m4`; font/màu.
- **Tệp mẫu:** mỗi tệp qua đúng `NR.kiem_tep` với vai/media khai; route cần phiên + quyền soạn, không `tao=True`, whitelist.
- **Bootstrap:** thứ tự và `m4_seed`.
- **Package data:** khớp mọi `PIN`/`FONT_PIN` và UI.

**`tests/test_m4_01c_http.py`** (PG + LocalServer, h01–h08):

| Ca | Nội dung |
|---|---|
| h01 | Tài sản, trạng thái, seed DU, `ghi_nguon` sẵn sàng, phạm vi đúng, thiếu token 403 |
| h02 | Tệp mẫu (danh sách/bytes, đường dẫn lạ 404, KE_TOAN chỉ xem 403, không phiên ≠ 200); tệp rỗng/giả media/đường dẫn/khóa authority |
| h03 | Tạo HĐ, replay cùng khóa, đổi body 409, khóa khác cùng số HĐ 409; bytes tải về = nguồn; thiếu căn cứ + Nộp trực tiếp 409; phiên chung CRM thấy cùng vai |
| h04 | B1 ngoài phạm vi: 404 đọc/tệp/đợt/UUID đoán, 403 lệnh ghi |
| h05 | Track Changes qua sửa tham số 409, revision không đổi, nguồn giữ; trích → KHONG_HO_TRO khi có lõi |
| h06 | Cần lõi nguồn. Luồng đầy đủ: trích XONG, đủ 37 mã/TC-09; oracle thủ công B3 với máy kiểm OK; trích dẫn sai 400; revision cũ 409; KT/reviewer không xác nhận; xác nhận; PL khai/thêm/hủy; BOQ xem/nhập với phát hiện 999 giữ nguyên; đợt 1 đủ căn cứ → Nộp thật; ảnh chụp; reviewer đọc/tải và không sửa được; đợt 2 phải có ngày riêng |
| h07 | Thu hồi dự án A2: replay 403, đọc/tệp 404, tổng quan rỗng, actor vẫn hoạt động |
| h08 | Danh tính ngoài danh sách M4 / khóa authority bị từ chối |

**`tests/m4_01c_async.cjs`:** chạy **mã thật** app.js + m4.js trên DOM giả tối thiểu với fetch Promise điều khiển được.

| Ca | Nội dung |
|---|---|
| A1 | Nạp |
| A2 | Đổi vai xóa đồng bộ M4 + CRM; barrier chặn GET M4/CRM; ý định thứ hai xếp hàng; ý định cũ không mở barrier; ý định mới nhất nạp lại M4 + CRM |
| A3 | Chi tiết trễ của vai cũ không vẽ |
| A4 | Bytes trễ không click |
| A5 | Bấm lặp một POST; mất kết nối → gửi lại đúng body + khóa |
| A6 | Đổi vai từ CRM xóa M4 |

Đây không phải trình duyệt thật.

Không sửa test/guard/expected cũ (B/native/CRM/M2/M5/L11).

## 8. Hướng dẫn bấm 18 ca GUI (Root kiểm sau freeze, DEMO mới giữ lại; Claude chưa chạy — NOT_RUN)

Chuẩn bị chung:
1. Bấm `MỞ BẢN DEMO.cmd`.
2. Mở **Hồ sơ xây dựng (M4)** ở menu trái.
3. Chọn vai ở ô “Vai mô phỏng”, bấm **Dùng vai này**.
4. Tệp mẫu chọn ở ô **“Hoặc tệp mẫu DEMO”** rồi bấm **Dùng tệp mẫu**.

| Ca | Bấm | Phải thấy |
|---|---|---|
| C01 | Mở DEMO → menu M4. Đóng/mở lại DEMO | Tiêu đề “Hồ sơ xây dựng”, vai, phạm vi, danh sách. Mở lại không nhân actor/không cấp lại (`m4_seed` của bước chuẩn bị). Kho chưa sẵn sàng → thông báo kèm hướng xử lý |
| C02 | A1: Tạo hồ sơ HĐ → tab Đợt → Tạo đợt 1 (chưa ngày) → mở đợt | Mục “Kiểm trước khi nộp” liệt kê đúng thiếu (tệp HĐ, khai PL, BOQ, ngày, tài liệu); Nộp tắt; POST trực tiếp bị 409 |
| C03 | Tab Nguồn: mẫu `hop_dong.docx` (vai Hợp đồng) → Gắn làm tệp HĐ → Chạy trích | Tên/loại/byte/H rút gọn/người/ngày; lần trích “Đã trích”, chế độ quy tắc; tab Tham số 37 mã theo thứ tự máy chủ, có TC-09; không tự điền giá trị |
| C04 | Tab Tham số: Sửa mã → nhập giá trị + trích dẫn đúng câu HĐ / Không áp dụng + lý do → Lưu → Xác nhận | Máy kiểm “OK…”; trích dẫn giả bị từ chối. Vai KT/Review không có nút Sửa/Xác nhận, gọi trực tiếp bị 403 |
| C05 | Mẫu `hop_dong_con_sua_doi.docx` → gắn → Sửa tham số có trích dẫn / Chạy trích; trang khi ghi nguồn chưa sẵn sàng | Bị chặn trước Office/cleanup, nguồn giữ; trích báo chưa hỗ trợ. Ghi nguồn chưa sẵn sàng → nút khóa, nháp giữ. Chưa có AI/OCR được ghi rõ |
| C06 | Tab Phụ lục: khai Có chưa đủ → thêm PL Dự thảo có tệp → Hủy có lý do → khai Không có / Có đủ | Lịch sử giữ cả PL đã hủy; khai mâu thuẫn bị chặn; PL dự thảo/tương lai không áp vào đợt (mục Hiệu lực) |
| C07 | Tab BOQ: `boq_lech_so_hoc.xlsx` → Đọc sheet → Xem trước → map → Nhập. Lặp với `boq_ten_gia_loi.xlsx`, `boq_trong_va_0.xlsx`, map sai | Phát hiện dòng 4, thành tiền 999 giữ nguyên, trạng thái “Đọc/map đủ”; “abc” → lỗi chặn; trống hiện “(trống)” khác 0; map thiếu cột bị từ chối |
| C08 | Đợt: ngày → tải `ho_so_dot_ky1.pdf` → chọn mục → Gắn. Thử tệp rỗng, sai đuôi, tên có “../” | Checklist đúng mục; tệp xấu bị từ chối; thiếu một mục hiện đúng mục đó |
| C09 | Đủ căn cứ → Nộp chính thức → đổi vai MO_PHONG_REVIEW_M4 → mở đợt → Tải tài liệu | Ảnh chụp/revision/tham chiếu; reviewer đọc/tải đúng tệp; không có nút Duyệt/PDF/kế toán/Request; các bước sau ghi “Chưa nối” |
| C10 | Tạo đợt 2 cùng HĐ | Dùng lại HĐ/PL/BOQ; vẫn thiếu ngày + tài liệu kỳ 2; không nhân hồ sơ HĐ |
| C11 | Mở HĐ ở hai tab; tab 1 sửa tham số; tab 2 xác nhận/khai bằng revision cũ | 409 “Hồ sơ đã đổi”, nháp tab 2 giữ, xác nhận cũ hiện “Hết hiệu lực” theo máy chủ; đợt đã nộp giữ ảnh chụp |
| C12 | Bấm đúp nút lệnh; ngắt kết nối giữa chừng rồi “Gửi lại y nguyên”; sửa body với cùng khóa (HTTP) | Một kết quả; gửi lại trả biên nhận cũ (không trích/đọc BOQ lại); đổi body 409; mảng lỗi/phát hiện BOQ giống lần đầu |
| C13 | Vai A2/B1/PN không M4/KT có PHU_TRACH: danh sách, mở UUID đoán, tải tệp | Không thấy/không tải được ngoài phạm vi (404/403), không lộ tên/trích dẫn/bytes |
| C14 | Đổi vai rồi ngay lập tức Làm mới / mở HĐ / Nộp / Tải / đổi vai tiếp | Không GET khi barrier; phản hồi trễ không vẽ; ý định cuối thắng; không treo |
| C15 | Đổi vai ở M4, sang CRM/M2/M5/L11, đổi vai ở đó, quay lại M4 | Cả năm module xóa và nạp lại theo vai mới; M9 không đổi mã |
| C16 | Root thu hồi phạm vi DEMO của A2 → A2 thao tác/gửi lại/tải | Bị chặn, UI xóa dữ liệu khi tải lại; mở lại DEMO không cấp lại. Bytes đã tải trước đó không được tuyên bố thu hồi |
| C17 | Tải tệp nguồn | Bytes khác rỗng, độ dài/H khớp tệp đã nhận; GET thiếu token không tính là tải thành công |
| C18 | Màn hình 1280 và 1440: danh sách, tham số, BOQ thô, checklist, cảnh báo revision/quyền | Đọc được, nút không khuất, bảng cuộn có chủ đích, không rò style sang CRM |

Root giữ screenshot/case/actor/kích thước thật trong attempt mới: cổng, tham số, phát hiện BOQ, checklist thiếu, reviewer sau nộp, từ chối revision cũ.

## 9. Lệnh Root cần chạy (sau terminal/freeze)

1. `python -m unittest tests.test_m4_01c -v`
2. `node tests/m4_01c_async.cjs` (Node ≥ 18; mã thoát 0 = đạt)
3. `$env:KHO_PG_DSN_TEST = "<DSN chủ>"; python -m unittest tests.test_m4_01c_http -v`. Ca h05 (trích) / h06 cần lõi nguồn đã nạp.
4. Hồi quy không đổi: `python -m unittest tests.test_m4_01b_tinh tests.test_m4_01b_pg -v` cùng các bộ CRM/M2/M5/L11 hiện có (app.js đổi seam đổi vai và CRM).
5. Build wheel + cài thử để xác nhận package data (hiện NOT_RUN).
6. Kiểm 18 ca GUI ở §8 trên DEMO mới.

Skip vì thiếu DSN/Node/lõi nguồn là NOT_RUN/NOT_VERIFIED, không tính đạt.

## 10. Giới hạn và rủi ro trung thực

- Chưa runtime/screenshot nào. Mã JS chưa từng chạy trong trình duyệt hay Node.
- Có thể có lỗi giao diện chỉ lộ khi Root bấm: bố cục, focus, mất nháp khi vẽ lại tổng quan.
- **Nháp:** nháp được giữ khi 409 revision cũ và khi nạp danh sách mẫu. Sau lệnh thành công, form của lệnh đó làm mới (không giữ). Ô “Tạo hồ sơ HĐ” vẽ lại khi tổng quan tải lại.
- **Tệp hồ sơ đợt:** chi tiết HĐ (B6) không trả tệp vai `HO_SO_DOT` chưa gắn. Vì vậy danh sách “vừa tải trong phiên này” là trạng thái phía client (theo đợt, xóa khi đổi vai/lựa chọn), kèm các tệp đã gắn đợt. Tải lại trang làm mất danh sách này, nhưng tệp vẫn ở máy chủ: tải lại cùng bytes trả đúng tệp cũ. Đây là giới hạn của API B6; tôi không sửa backend.
- **M9** chưa vào seam đổi vai chung (đúng phạm vi giao). Đổi vai ở M9 không xóa module khác.
- **Bỏ trống:** chưa có Local AI/OCR/PDF, chưa đọc PDF. Fake AI chỉ là plumbing đã khai ở B, không chứng minh độ chính xác.
- **Package data:** dùng glob `**` (setuptools ≥ 62.3). Chưa build/cài thử.
- Không gọi C, gói 1 hay toàn M4 đã xong. M4-02…05 và CRM tiếp tục theo hàng chờ. Không tự chuyển gói.

## 11. M4-01C2 — sửa vòng đời giao diện (CODE_ONLY, 21/10/2026)

Căn cứ: [GIAO-CODE-M4-01C2](GIAO-CODE-M4-01C2-SUA-VONG-DOI-GIAO-DIEN.md). Root/peer đã xác nhận 4 lỗi bằng đọc mã tĩnh; C1 chưa có runtime PASS.

Chỉ sửa 5 tệp có sẵn: `app.js`, `m4.js`, `tests/m4_01c_async.cjs`, `tests/test_m4_01c.py`, báo cáo này. Không tạo tệp mới.

Không đổi: HTTP/bootstrap/pyproject/CSS/index, backend/service/SQL/schema, vendor, guard, fixtures, test HTTP, M9 (khối M9 trong app.js không chạm). Lịch sử §1–§10 giữ nguyên.

### 11.1 Sửa và ca kiểm tương ứng

| # | Lỗi (đối chiếu độc lập) | Sửa | Ca trong `m4_01c_async.cjs` |
|---|---|---|---|
| 1 | Lần gửi POST/tải lên cũ về trễ xóa khóa/“đang gửi” của lần gửi mới cùng body (A→B→A); HTTP 200 nhưng JSON đứt bị coi là xong/thất bại | Xem §11.1.1 | **C2-1a**, **C2-1b** |
| 2 | BOQ đổi tệp/sheet nhưng phản hồi cũ kéo về lựa chọn cũ; nút Nhập cũ dùng sheet cũ khi xem trước mới còn chờ | Xem §11.1.2 | **C2-2** |
| 3 | Continuation lệnh cũ đóng/vẽ đè form mới (lưu tham số A rồi mở B); tệp mẫu cũ vẫn gửi sau khi đổi lựa chọn | Xem §11.1.3 | **C2-3** |
| 4 | Hàng POST đổi vai giữ tới khi các GET nạp lại xong — một GET treo chặn ý định đổi vai mới | Xem §11.1.4 | **C2-4** + **P0** |

#### 11.1.1 Sửa 1 — vé sở hữu cho từng lần gửi

- Mỗi `(route, body gốc)` có **bản ghi** `{khoa, chu}`, quản lý bằng `nhanBanGhi`/`traBanGhi`. Mỗi lần gửi giữ một **vé**.
- Thành công, lỗi hay `finally` chỉ nhả đúng vé và bản ghi của chính lần gửi đó. Khóa chỉ bị bỏ khi có kết quả thật **và** bản ghi trong map vẫn là của mình.
- Đổi vai xóa map. Bản ghi cũ thành mồ côi, nên lần gửi cũ không chạm được bản ghi mới.
- HTTP 2xx mà JSON đứt → `KET_QUA_CHUA_RO` (status 0): giữ khóa, hiện nút “Gửi lại y nguyên” với đúng body và khóa cũ.
- Tải lên dùng cùng cơ chế. `X-M4-Info` khi gửi lại giữ y nguyên.

#### 11.1.2 Sửa 2 — vé lựa chọn BOQ (`genBoq`)

- Đổi tệp, đổi sheet, bấm Đọc hay Xem đều tăng vé. Chỉ phản hồi của vé mới nhất được vẽ; lỗi của vé cũ không vẽ.
- Đổi lựa chọn → vẽ lại đồng bộ, **gỡ ngay** form Nhập cũ. Khi xem trước còn chờ thì không có nút Nhập.
- Nút Nhập kiểm lại: vé, đối tượng xem trước, tệp/sheet, trạng thái chờ. Body lấy từ chính tệp/sheet/header/map đang hiện.
- Lựa chọn tệp giữ ở `boqTep`, không bị vẽ lại làm mất.

#### 11.1.3 Sửa 3 — thế hệ form (`genForm`)

- `genForm` tăng khi người dùng sửa bất kỳ ô nhập nào (listener `input`/`change` trong `o()`), đổi tab, mở “Sửa” mã khác, bấm “Đóng”, “Bổ sung →”, đổi HĐ/đợt hoặc đổi vai.
- Mỗi lệnh chụp `formCon()` lúc bấm. Sau lệnh thành công (`sauLenh`): form không đổi → làm mới như cũ; form đã đổi → **không** vẽ lại/đóng form, giữ nháp mới, báo “bấm ↻ Làm mới”.
- Lệnh đã gửi vẫn có thể commit hợp lệ ở máy chủ. Thế hệ form chỉ chặn continuation cũ ghi đè giao diện mới.
- Tệp mẫu: lấy bytes xong mà lựa chọn mẫu/tệp/vai đã đổi → **không gửi** tệp mẫu cũ.
- Không dùng debounce/delay.

#### 11.1.4 Sửa 4 — hàng đổi vai chỉ tuần tự hóa POST

- `doiVaiTuanTu` nhả hàng **ngay khi POST của ý định settle** (thành công hoặc lỗi), trước khi nạp lại. GET nạp lại treo không chặn ý định sau.
- Chỉ ý định mới nhất mở barrier. Phản hồi, lỗi hay finally của ý định cũ không mở barrier, không toast, không nạp.
- Mọi GET/lỗi của từng module vẫn rào theo epoch/thế hệ riêng. Thêm `m5Gen` để GET M5 cũ không đè GET mới cùng epoch.
- Áp chung cho CRM/M4/M2/M5/L11 qua seam. M9 giữ nguyên.

### 11.2 Bộ kiểm

**`tests/m4_01c_async.cjs`** (viết lại, chưa chạy):
- **DOM giả:**
  - có quan hệ cha–con thật; `getElementById` chỉ trả phần tử **đang gắn** vào trang;
  - id tĩnh lấy từ `index.html` thật; id khác chưa gắn → `null`.
- **Rejection:** `unhandledRejection` được **ghi lại và làm FAIL**, không nuốt. Lỗi của module ngoài ca (GET 404 lúc khởi động) đi qua đường bắt lỗi có sẵn của module.
- **P0 (dương không rỗng):** M4, CRM, M2, M5, L11 đều nạp payload có cấu hình (không dùng `cau_hinh:false`) và vẽ đúng vai mới sau đổi vai. Trước đó kiểm GET bị chặn trong barrier.
- **C2-1a:** gửi A, đổi vai A→B→A, gửi lại cùng body (khóa mới); lần cũ về trước.
  - Bấm lặp vẫn 0 POST.
  - Mất kết nối → gửi lại đúng body+khóa.
  - 200 + JSON đứt → vẫn “chưa rõ” → gửi lại đúng body+khóa.
- **C2-1b:** tương tự cho tải lên, so `X-M4-Info`.
- **C2-2:**
  - đổi tệp khi đọc sheet còn chờ, phản hồi B trước A, A về trễ không kéo lựa chọn về;
  - đổi sheet → nút Nhập biến mất ngay; lỗi của sheet cũ không vẽ;
  - dương: nhập đúng tệp/sheet/header/map đang hiện.
- **C2-3:**
  - lưu TC-01 còn chờ → mở TC-02 và gõ → phản hồi TC-01 không đóng/không làm mới; dương: lưu TC-02 rồi làm mới;
  - mẫu cũ không gửi sau khi đổi mẫu; dương: mẫu hiện tại gửi đúng tên/vai.
- **C2-4:**
  - POST ý định 2 gửi được khi GET nạp lại của ý định 1 còn treo; GET treo về trễ không vẽ;
  - GET M2 bắt đầu trước đổi vai về trễ không vẽ; bytes tải về trễ không click;
  - chiều ngược từ selector CRM (GET CRM treo, ý định M4 vẫn gửi POST ngay).

**`tests/test_m4_01c.py`:** chỉ chỉnh assertion cấu trúc của khóa (bản ghi + vé, không còn `dangGui`). Không thêm test mirror để che race; hành vi race kiểm ở harness async.

Test HTTP (`test_m4_01c_http.py`) giữ nguyên, không sửa, không chạy.

### 11.3 Trạng thái trung thực

| Hạng mục | Trạng thái |
|---|---|
| Self-test của Claude | **NOT_RUN** |
| Root static/runtime cho bản C2 (`test_m4_01c`, `node tests/m4_01c_async.cjs`, `test_m4_01c_http`) | **NOT_RUN** cho tới khi có chứng cứ |
| 18 ca GUI | **NOT_RUN** |
| Build wheel | **NOT_RUN** |

Rủi ro còn lại:
- **Không vẽ lại khi form đã đổi.** Khi người dùng đã sửa form trong lúc lệnh chờ, giao diện không tự làm mới. Số liệu trên màn hình có thể cũ tới khi bấm ↻ Làm mới (có báo rõ). Đây là đánh đổi có chủ đích để không mất nháp.
- **`genForm` tăng với mọi ô nhập**, gồm cả ô lọc “Chỉ mã còn thiếu”.
- **Harness chạy mã thật trên DOM giả tối thiểu**, không phải trình duyệt. Chưa từng chạy, nên có thể lộ lỗi harness khi Root chạy.
- Không nhận C2 là GUI PASS hay toàn M4 xong. CRM G1/G7/S6 và full Review M4 tiếp tục theo hàng chờ sau khi C ổn định.

## 12. M4-01C3 — giữ nháp qua toàn bộ lượt tải và gửi lại đúng tệp (CODE_ONLY, 21/10/2026)

Căn cứ: [GIAO-CODE-M4-01C3](GIAO-CODE-M4-01C3-GIU-NHAP-VA-GUI-LAI-TEP.md).

Bằng chứng Root ghi nhận cho C2 (không phải của Claude): 16 pure tests + 6 nhóm async native đạt, 0 skip/error; hai ca độc lập (ownership POST cũ, xem trước BOQ đảo thứ tự) đạt. Đây là bằng chứng hữu hạn, **không** phải GUI hay toàn M4.

Lượt này sửa 2 residual Root/peer đã đối chiếu trên mã thật.

| Tệp | Thay đổi |
|---|---|
| `m4.js` | Sửa |
| `tests/m4_01c_async.cjs` | Thêm ca C3 |
| báo cáo này | Bổ sung §12 |
| `app.js` | **Không cần sửa** (seam hiện có đủ). Khối M9 nguyên byte |
| `tests/test_m4_01c.py` | **Không sửa**: không có assertion cấu trúc nào bị thay đổi; không dùng assertion mã nguồn thay bằng chứng race |

Không tạo tệp mới. Backend/HTTP/SQL/service/bootstrap/pyproject/index/CSS/vendor/guard/fixtures/test HTTP giữ nguyên.

### 12.1 C2UI-01 — guard tới tác động DOM cuối

- **Chuỗi nạp mang thế hệ form:** mỗi chuỗi nạp (`m4Nap → napHd → napDot`) chụp thế hệ form `fs` lúc GET **đầu tiên** bắt đầu và mang nó qua mọi await. Phản hồi về mà người dùng đã mở/nhập form sau lúc đó → **không vẽ lại**: giữ nguyên DOM, form đang mở và nháp mới nhất. Không gán dữ liệu mới vào màn hình; chỉ báo “Dữ liệu mới đã về … bấm ↻ Làm mới”.
- **Luồng không có sửa mới** vẫn nhận dữ liệu và revision, vẽ bình thường (form đã lưu đóng, revision mới hiện).
- **Khôi phục sau 409 `M4_REVISION_CU`:** gọi `napHd({giu: true})`. Phản hồi về thì vẽ revision mới với nháp **chụp ngay trước khi vẽ** (`veGiu`), không dùng snapshot lúc bắt đầu.
- **Danh sách tệp mẫu (`napMau`)** về sau khi người dùng đã nhập → không dựng lại; danh sách hiện ở lần vẽ kế tiếp.
- **BOQ (`docSheet`/`xemSheet`):** phản hồi/lỗi cập nhật **trạng thái** BOQ theo vé. Chỉ vẽ khi vẫn đang ở tab BOQ, và vẽ bằng `veGiu`. Đang ở tab khác/nhập form khác → không dựng lại; quay lại tab BOQ thấy đúng kết quả mới nhất.
- **Hết quyền vẫn xóa** (không giữ nháp trái phạm vi): đổi vai, actor máy chủ khác, 403/404, HĐ không còn trong danh sách tổng quan hiện hành → xóa lựa chọn/nháp và vẽ lại.
- Không dùng delay/debounce.

### 12.2 C2UI-02 — gửi lại tải lên chưa rõ đúng ý định gốc

- **Một ý định tải lên** là `{intent, File gốc, vai, fence, form, continuation}`:
  - tệp thật: khóa ý định theo dự án/vai/tên/kích thước/thời điểm sửa;
  - tệp mẫu: theo dự án/vai/tên mẫu.
- **Kết quả chưa rõ** (mất kết nối, 5xx, hoặc HTTP 2xx mà JSON đứt) → giữ ý định trong `taiChuaRo` và hiện nút **“Gửi lại tệp y nguyên (cùng khóa)”**.
- **Gửi lại dùng đúng đối tượng File gốc:** cùng bytes, cùng `X-M4-Info`/khóa, cùng continuation.
  - Bấm lại **“Dùng tệp mẫu”** cho cùng mẫu → dùng ý định đang giữ, **không lấy lại tệp mẫu** (File mới có thời điểm/bytes khác).
  - Chọn lại cùng tệp thật (File mới cùng tên/kích thước/thời điểm sửa) → gửi File gốc đang giữ.
  - Không cố định timestamp, không gửi hash/authority từ client, không đổi DTO.
- **Bấm lặp khi còn bay:** 0 POST thêm (vé sở hữu C2).
- **Kết quả rõ:** continuation (gắn vào danh sách hồ sơ đợt, làm mới) chạy **đúng một lần**; bỏ ý định đang giữ và nút gửi lại.
- **Đổi vai/HĐ/đợt** xóa các ý định đang giữ. Ownership A→B→A của C2 giữ nguyên; continuation cũ không chạm lựa chọn/vai mới.

### 12.3 Ca kiểm thêm trong `tests/m4_01c_async.cjs` (mã thật, chưa chạy)

- **Mock File** giống trình duyệt: không khai `lastModified` thì mỗi lần tạo một giá trị khác (không hardcode).
- **DOM giả:** chỉ trả id đang gắn; id tĩnh lấy từ `index.html`.
- **`unhandledRejection`:** ghi lại và làm FAIL.

| Ca | Nội dung |
|---|---|
| **C3-1** | Lưu TC-01 thành công. GET tổng quan về khi chưa sửa. GET HĐ còn chờ → mở TC-02 và nhập → GET về: form TC-02 + nháp còn nguyên, không GET đợt. Dương: lưu TC-02 không sửa thêm → form đóng, hiện revision 5. GET **đợt** còn chờ → nhập ngày → GET về: ngày mới nhất còn, panel không bị vẽ đè |
| **C3-2** | 409 revision cũ → GET khôi phục bắt đầu → nhập thêm → GET về: hiện “revision 6” với giá trị mới nhất (`v2`), không snapshot `v1` |
| **C3-3** | Đọc sheet còn chờ → sang tab Phụ lục và nhập → phản hồi về: nháp PL còn, không vẽ BOQ. Quay lại BOQ thấy danh sách sheet mới nhất. Xem trước S2 còn chờ → sang PL nhập → lỗi 400 về: nháp PL còn. Dương: xem trước lại S2 → nhập đúng tệp/sheet/header/map đang hiện |
| **C3-4** | Mẫu nhận 200 + JSON đứt → bấm “Dùng tệp mẫu” lại: 0 GET mẫu, POST dùng **cùng đối tượng File** và cùng `X-M4-Info`. Bấm lặp khi còn bay: 0 POST. Mất kết nối → gửi lại cùng File/khóa → thành công: continuation làm mới đúng một lần, nút gửi lại biến mất. Tệp thật: lỗi mạng → chọn lại File mới cùng tên/kích thước/thời điểm → POST gửi File gốc, cùng metadata |

Giữ các ca cũ P0 (dương không rỗng CRM/M4/M2/M5/L11), C2-1a/b, C2-2, C2-3, C2-4 (hàng chỉ tuần tự POST, barrier GET, ý định mới nhất thắng, raw không click khi đổi vai).

### 12.4 Trạng thái trung thực

| Hạng mục | Trạng thái |
|---|---|
| Self-test của Claude | **NOT_RUN** |
| Root static/async/HTTP cho bản C3 | **NOT_RUN** tới khi có chứng cứ thực tế đúng lớp |
| GUI 18 ca | **NOT_RUN** |
| Wheel | **NOT_RUN** |

Rủi ro còn lại:
- **Nhập trong lúc làm mới = không vẽ lại.** Khi người dùng nhập trong lúc chuỗi làm mới đang chờ, màn hình giữ dữ liệu cũ (có báo) tới khi bấm ↻ Làm mới. Sau thao tác thành công + có sửa mới, nút trên form vẫn mang revision cũ; gửi sẽ nhận 409 rồi được khôi phục với nháp mới nhất.
- **Khôi phục sau 409 vẽ lại form**, nên ô chọn tệp (`input type=file`) không giữ được lựa chọn. Trình duyệt không cho đặt lại giá trị ô này.
- **Hiển thị sau tải lên muộn:** nếu tải lên chưa rõ được gửi lại thành công sau khi người dùng đã sửa form khác, continuation vẫn chạy (cập nhật danh sách tệp vừa tải) nhưng không vẽ lại.
- Harness chưa chạy; có thể lộ lỗi harness khi Root chạy.
- Không nhận C3 là GUI PASS hay toàn M4. Full Review M4 (L1–L3, duyệt/PDF), nghiệm thu–công nợ, Request và CRM 41–42 (G1/G7/S6) tiếp tục theo hàng chờ; không có nút giả.

## 13. M4-01C4 — khóa ý định tải tệp theo ngữ cảnh gốc và gộp lần lấy mẫu đang chờ (CODE_ONLY, 21/10/2026)

Căn cứ: [GIAO-CODE-M4-01C4](GIAO-CODE-M4-01C4-KHOA-Y-DINH-TAI-TEP.md). Root ghi nhận supplemental độc lập trên actual Node handlers: một positive không rỗng, hai lỗi tái hiện. Đó là bằng chứng hữu hạn của lớp handler, chưa phải browser/HTTP.

Chỉ sửa 3 tệp: `src/kho_tri_thuc/m4/giao_dien/m4.js`, `tests/m4_01c_async.cjs`, báo cáo này. Không tạo tệp mới. `app.js`, test Python, backend/route/HTTP/SQL/service/bootstrap/package/CSS/index/vendor/fixtures/guard/M9 giữ nguyên.

### 13.1 C4-01 — kiểm đúng ngữ cảnh trước mọi request

- **Ý định chụp ngữ cảnh gốc.** Ý định tải lên được tạo đồng bộ trong handler (`taoYDinh`). Khóa ý định gồm epoch/HĐ/đợt/dự án/vai/tên, kèm fence (epoch, actor, HĐ, đợt), **dự án gốc** `du_an_id`, File gốc và continuation.
- **Đích lấy từ ý định.** `taiLen(y)` lấy dự án/metadata/khóa từ **ý định**, không dựng lại từ `hd` đang chọn. Header `X-M4-Info` của lần gửi đầu được giữ trong ý định (`y.enc`). Lần gửi lại có header khác → không gửi.
- **Ba cổng kiểm trước request:**
  - entrypoint `guiTep` (cả nút gửi lại);
  - đầu `taiLen`;
  - ngay trước `fetch` POST.

  Ý định hết hiệu lực → `boYDinh`: bỏ giữ, gỡ nút, báo “không gửi”. Không đổi đích, không đổi khóa, không gắn tệp A sang B.
- **Đổi ngữ cảnh vô hiệu ngay.** Đổi HĐ (`boChon`, cả khi đổi vai), đổi đợt (`moDot`) → `huyYDinhTai()` **đồng bộ**: đánh dấu hết hiệu lực mọi ý định đang giữ hoặc đang lấy mẫu, xóa map, **gỡ nút gửi lại toàn cục**, gồm cả nút gửi lại lệnh POST.
- Nút gửi lại lệnh POST cũng kiểm fence trước khi gửi.
- Cùng ngữ cảnh và kết quả chưa rõ → vẫn gửi lại đúng File/bytes/header/khóa gốc. Kết quả rõ → gắn/làm mới đúng một lần (giữ C3).

### 13.2 C4-02 — giữ một ý định trước await đầu tiên

- **Giữ chỗ đồng bộ.** “Dùng tệp mẫu” giữ chỗ **một ý định logic** (`mauDang`) đồng bộ, trước GET/await đầu tiên. Bấm lặp khi đang lấy mẫu hoặc đang tải lên → không GET/POST thêm. Giữ chỗ được nhả trong `finally` của chính ý định đó (đúng sở hữu).
- **Đổi lựa chọn/ngữ cảnh** trong lúc GET chờ → không tải mẫu cũ.
- **GET mẫu lỗi chắc chắn** → nhả giữ chỗ; bấm lại là lần lấy hợp lệ mới.
- **Sau GET thành công,** File gốc gắn vào ý định. Chưa rõ sau POST (mạng, 5xx, HTTP 200 + JSON đứt) → giữ trong `taiChuaRo`; bấm lại dùng File gốc, không GET mẫu, không tạo File mới. Không dùng `lastModified` cố định.

### 13.3 Ca kiểm thêm trong `tests/m4_01c_async.cjs` (actual handlers, chưa chạy)

- **Harness:**
  - dùng **Blob/File gốc của Node** khi có (`lastModified` mặc định = thời điểm tạo, như trình duyệt); lớp thay thế chỉ khi Node không có;
  - DOM chỉ trả id đang nối;
  - `unhandledRejection` làm FAIL.
- **Fixture:** DTO tổng quan có **hai dự án/HĐ** cho cùng actor (`TONG2`); chi tiết HĐ có hai đợt.

| Ca | Nội dung |
|---|---|
| **C4-01a** | Tải tệp thật ở HĐ A (header dự án `da1`) → mất kết nối (nút gửi lại hiện) → bấm phần tử HĐ B **đang nối DOM** → chi tiết B hoàn tất → lấy lại nút gửi lại còn nối (nếu có thì bấm) → **0 POST**, không còn nút. Quay về A bằng control thật: không tự gửi, không còn nút |
| **C4-01b** | Tải hồ sơ đợt 1 → 503 (chưa rõ) → bấm “Mở” đợt 2 thật → chi tiết đợt 2 xong → không còn nút gửi lại, **0 POST** |
| **C4-02** | Bấm “Dùng tệp mẫu” **hai lần trước khi GET mẫu settle** → 1 GET. Bấm thêm khi POST còn chờ → vẫn 1 POST, 0 GET thêm |
| **C4-02 dương** | Header dự án/vai/tên đúng; body là File tên `hop_dong.docx`, 30 byte. Thành công → đúng 1 lần làm mới → GET HĐ trả hàng nguồn mới → hàng hiện **đúng một lần** |
| **C4-02 chưa rõ** | Lần lấy mẫu hợp lệ mới → POST 200 + JSON đứt → bấm lại: 0 GET mẫu, **cùng đối tượng File** và cùng `X-M4-Info` → thành công → continuation một lần |

- Giữ nguyên 10 ca hiện có (P0, C2-1a/b, C2-2, C2-3, C2-4, C3-1…C3-4) và mọi assertion. Chỉ đổi phần dựng tệp của C3-4 sang bytes `Uint8Array` để chạy được với File gốc của Node.
- Các guard khác giữ nguyên: vai hiện hành, nháp mới nhất, ownership POST, gửi lại, barrier GET.

### 13.4 Trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Self-test của Claude | **NOT_RUN_CODE_ONLY** |
| C4, 18 ca GUI, wheel, toàn M4 | Không được ghi là đạt; Root đọc diff, freeze và kiểm độc lập sau terminal thật |
| B50+4 / native10 / independent8 | Bằng chứng hữu hạn của B, không chạy lại trong lượt này |

Rủi ro: khóa ý định tệp thật dùng tên/kích thước/`lastModified`. Chọn lại một tệp khác nhưng trùng cả ba trong cùng ngữ cảnh khi còn ý định chưa rõ sẽ được coi là cùng ý định và gửi File gốc. Đây là đánh đổi có chủ đích để gửi lại đúng bytes gốc.

Review/PDF/AP/Request và CRM giữ lộ trình riêng đã chốt; không có nút giả.
