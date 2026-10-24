# BÁO CÁO CRM-41-03 — G2 Báo giá → G3 Soạn hợp đồng từ mẫu · FIX04 CODE_WRITTEN · NOT_RUN_CODE_ONLY

## FIX04 (CRM_41_03_FIX04_TEST_FIXTURE_CODE_ONLY) — CODE_WRITTEN / NOT_RUN

**Căn cứ:** `GIAO-SUA-CRM-41-03-04-DOCX-DEMO-CHO-WORD.md`.

**Bằng chứng do Root ghi (coder không tự chạy):**
- F18 sau FIX03: nonWord 51/51, async 18 nhóm, privateUI 3/3, PG 5/5; GUI thật Save → Convert → Save rev2 → reload giữ đúng trường/lịch.
- Word native: ca timeout PASS. Ca xuất PDF dương SKIP vì DOCX control bị từ chối: `_control` tại `crm_docx.py:987`, `Documents.Open` → `com_error` HRESULT -2147352567, scode -2146822496, "The file appears to be corrupted".
- Ownership/Job/stop và Word có sẵn đều đạt theo Root.
- DOCX bị từ chối là DOCX tổng hợp do `mau_docx()` trong test tạo, không phải tài liệu thật.

**Nguyên nhân xác định từ markup** (suy luận từ đặc tả WordprocessingML, chưa kiểm bằng Word):
1. Ô ngoài của bảng kết thúc bằng bảng lồng `</w:tbl></w:tc>`. Theo schema, mỗi `w:tc` phải kết thúc bằng một `w:p`; Word coi vi phạm này là tệp hỏng.
2. Cả hai bảng thiếu `w:tblPr`/`w:tblGrid` (bắt buộc theo schema).
3. Bảng là khối cuối của thân ngay trước `w:sectPr`; Word luôn ghi một đoạn sau bảng.

**Sửa:** chỉ `tests/test_crm_giao_ket.py` (fixture dùng chung) và báo cáo này.
- Thêm helper `_bang(o_xml, rong)` dựng bảng 1×1 hợp lệ: `w:tblPr/w:tblW`, `w:tblGrid/w:gridCol`, `w:tcPr/w:tcW`. Ô kết thúc bằng bảng lồng thì được thêm một `<w:p/>` trống.
- `mau_docx(than_them='')`: giữ nguyên signature và các yếu tố sau:
  - mọi văn bản và tên ô (`{{so_` in đậm tách run + `hop_dong}}`, `{{ngay_ky}}`, `{{ho_ten}}` ở ô ngoài, `{{gia_tri}}` ở bảng lồng);
  - header/footer được tham chiếu qua `sectPr`;
  - `than_them` chèn trước `sectPr`;
  - gói OPC (Content_Types/rels) không đổi.
- Thêm một `<w:p/>` trống sau bảng ngoài.

**Không đổi:**
- Số lần xuất hiện ô vẫn 6 (đoạn trống không có văn bản nên không có ô).
- Bộ đọc G1 (`mau_docx._quet_phan`) và renderer (`crm_docx._doan_theo_thu_tu`) cùng đếm mọi `w:p` theo một thứ tự. Facts và `dien_mau` vẫn khớp vì cùng sinh từ một bytes.
- Ca lệch facts (`than_them` thêm đoạn → chỉ số đoạn header lệch) vẫn giữ đúng mục tiêu.
- Không assertion, test, skip hay oracle nào bị bỏ hoặc đổi.
- `test_crm_giao_ket_http.py` (`mau_hieu_luc`) và `WordThat` dùng lại đúng fixture này, không sửa file đó.
- Không sửa product, SQL, CJS, provider, Word ownership hay M9; không thêm dependency.

**Kết quả: NOT_RUN.** Chưa chứng minh Word mở được tệp mới; Root kiểm nonWord, native Word positive/timeout, nội dung PDF và hình hiển thị.

**Giới hạn:** nếu Word vẫn từ chối thì cần thêm phần tùy chọn (`styles.xml`/`settings.xml`/`docProps`). Lượt này không thêm vì chưa có bằng chứng cần. Không tuyên bố Word/PDF đạt.

---

# (FIX03 — giữ nguyên bên dưới)

## FIX03 (CRM_41_03_FIX03_CODE_ONLY) — CODE_WRITTEN / NOT_RUN_CODE_ONLY

**Căn cứ:** `GIAO-SUA-CRM-41-03-03-GUI-VA-PDF.md` (5 finding F17) và binding `CRM-41-03-WORD-OWNERSHIP-FIX02.md` (giữ nguyên).

**Cách làm:**
- Coder chỉ dùng Read/Glob/Grep/Edit/Write.
- Không chạy Python/Node/SQL/HTTP/Word/COM/trình duyệt, không import, không AST.
- **Mọi test mới: NOT_RUN.**
- Kết quả F17 của Root là bằng chứng để sửa, không phải kết quả của bản này.

**Phạm vi ghi (đúng 6 file đã có, NEW = 0):**
- `src/kho_tri_thuc/giao_dien/assets/crm_g.js`
- `src/kho_tri_thuc/nguon/crm_docx.py`
- `tests/crm_giao_ket_async.cjs`
- `tests/test_crm_giao_ket.py`
- `tests/test_crm_giao_ket_http.py`
- `docs/BAO-CAO-CRM-41-03.md`

**Không đụng:** service, SQL/M21, route, CSS/index, host/engine dùng chung, M4/M9, reference, dependency, quyền. Không thêm schema, provider hay workflow. Không xóa, đổi tên hay ghi đè tệp nào.

| # | Finding | Sửa (file · hàm) | Test đã viết | Kết quả |
|---|---|---|---|---|
| R1 | Định danh nháp MỚI: MOI → MOI không được nhận ID/revision của nháp trước | `crm_g.js`:<br>• `nhapMoi = {so, tao}` tạo mới ở mỗi "+ Báo giá mới"; `boChon` xóa; fence của editor gồm `nhapMoi === nm0`<br>• phần tiếp Lưu ghi `nm.tao` vào ĐÚNG định danh của ý định<br>• phạm vi khóa `pham = nm.so` (hai nháp mới có body trùng không dùng chung khóa)<br>• cùng nháp gõ tiếp: Lưu sau cập nhật đúng ID/revision đã ACK<br>• lần TẠO chưa rõ của nháp này: Lưu lại bị chặn (không tạo bản thứ hai), hiện lại nút đối soát đúng body/khóa gốc<br>• bỏ `bgMoi` | cjs **C1**:<br>• Mới A → Lưu chờ → Mới B → gõ B → ACK A ⇒ không hiệu ứng; Lưu B = tạo (`null`/`null`, khóa khác A)<br>• hai nháp body trùng → khóa khác<br>• dương: cùng nháp gõ tiếp → cập nhật `bg-C` rev 1 với nội dung gõ tiếp<br>• mất ACK → Lưu lại bị chặn → gửi lại → 409 đang xử lý → đối soát → FINAL cùng body/khóa<br>• tạo chưa rõ + gõ tiếp → đối soát body gốc, không hiệu ứng → Lưu sau = cập nhật `bg-E` | NOT_RUN |
| R2 | fv gốc kiểm mọi hiệu ứng nhìn thấy TRƯỚC khi POST gửi lại và sau mọi await | `crm_g.js`:<br>• `gui`: vận chuyển không hợp lệ → im lặng (bỏ thông báo "vai/lựa chọn cũ")<br>• `veGuiLai(null)` / "Đang gửi…" chỉ khi `fv()`; lỗi/chưa rõ/FINAL chỉ hiện khi `fv()`<br>• nút gửi lại: không POST khi `f` sai hoặc khóa đã FINAL; chỉ dọn nút khi `fv()`<br>• gửi lại dùng đúng body/khóa/`f`/`fv`/`sau`/phạm vi gốc; không chụp thế hệ mới; không vòng tự gửi | cjs **C2**: gõ B TRƯỚC khi bấm gửi lại A → ngay sau click (trước phản hồi) và sau thành công / UNKNOWN / lỗi xác định: trạng thái/toast/form B và nút gửi lại không bị A sửa; đúng 1 POST với body/khóa gốc; nút cũ sau FINAL không POST; vận chuyển dưới lựa chọn khác không gửi; dương hiện hành: hoàn tất đúng 1 lần, làm mới 1 lần, toast có | NOT_RUN |
| R3 | Số trang bị biến số lần ghi đè | `crm_docx.py` `kiem_pdf`: số trang `so_trang`/`so_trang2` tách khỏi biến số lần `can`; cổng chéo hai bộ đọc, trang không rỗng, render, phông, CỘNG số lần và `VAN_BAN_CO_BAN` giữ nguyên | `KiemPdfDem.test_so_trang_tach_khoi_so_lan`:<br>• 1 trang với số lần cuối 2<br>• 3 trang với số lần cuối 1<br>• thiếu số lần<br>• hai bộ đọc lệch số trang<br>• trang rỗng<br>Giữ 3 ca cũ (774/786/799) | NOT_RUN |
| R4 | Giao thức/ngoại lệ bất ngờ vẫn phải dừng có bằng chứng, kết quả có cấu trúc | `crm_docx.py`:<br>• `LoiGiaoThuc` + `_doc_giao_thuc` kiểm JSON object/kiểu/hình dạng PID (int > 0, `gan_job is True`, một lần) và XONG<br>• `_chuyen_pdf_mot` coi dòng sai là lỗi giao thức (không bỏ qua); ngoại lệ bất ngờ → `<pha>:NGOAI_LE_BAT_NGO:<loại>`<br>• mọi đường đi qua `_dung_cay`; `_dung_cay` bọc ngoại lệ bất ngờ trong wait/truy vấn/dừng → UNKNOWN<br>• file PDF tồn tại không thành thành công; giữ PDF/DOCX | `VongDoiParent`:<br>• `test_giao_thuc_sai_hinh_dang_dung_cay_va_khong_thanh_cong` (18 dòng sai, có PDF trên đĩa, + UNKNOWN khi Job không rỗng)<br>• `test_ngoai_le_bat_ngo_doc_wait_truy_van`<br>• `test_doc_giao_thuc_duong_tinh`<br>Giữ mọi ca FIX02 | NOT_RUN |
| R5 | g05 chứng minh guard bằng đúng ngữ cảnh thường (CHỈ TEST) | `test_crm_giao_ket_http.py` g05:<br>• (a) kết nối thường mới, không ngữ cảnh: SELECT thấy 0, UPDATE GỐC tác động 0 dòng, không lỗi; owner quan sát `md5(row_to_json)` toàn dòng không đổi<br>• (b) kết nối thường mới khác, giao dịch tường minh, LOCAL `ktt.nguoi_dung_id` + `ktt.nguoi_dung_dang_nhap` = UUID + login thật của BH (theo `crm_mau._tx`): SELECT thấy 1 → UPDATE GỐC trong `assertRaises(psycopg.Error)` GỐC; thêm SQLSTATE `P0001` + mã chính bắt đầu `CRM_G_CHI_CHU`; toàn dòng + trạng thái không đổi<br>• không sửa SQL/quyền | g05 | NOT_RUN |

**Giới hạn còn mở (FIX03):**
- **Gửi lại vô hình:** khi người dùng đã gõ tiếp, gửi lại một ý định chưa rõ chỉ đối soát vận chuyển, không hiện kết quả (theo R2). Người dùng thấy trạng thái sau ↻ Làm mới hoặc lần Lưu kế tiếp.
- **Nháp mới bị bỏ:** khi đã chuyển sang nháp mới khác, ACK của nháp cũ không được ghi đâu cả. Báo giá đã tạo vẫn có trên máy chủ (thấy ở danh sách); không gắn vào nháp mới.
- **Chưa kiểm thật:** Word/PDF thật, GUI trình duyệt và PostgreSQL toàn bộ chưa chạy. Harness cjs là DOM giả. R5 chỉ là fixture và kiểm chứng của test; bằng chứng vật lý do Root giữ.
- Các giới hạn FIX01/FIX02 bên dưới vẫn áp dụng: Word có thể NOT_READY; chỗ đặt có thể kẹt khi tiến trình chết.

---

# (FIX02 — giữ nguyên bên dưới)

## FIX02 (CRM_41_03_FIX02_CODE_ONLY) — CODE_WRITTEN / NOT_RUN

Căn cứ: `GIAO-SUA-CRM-41-03-02-GUI-VA-WORD.md` và binding `CRM-41-03-WORD-OWNERSHIP-FIX02.md`.
- Binding mới chỉ thay cách tạo/sở hữu Word và native test.
- Nghiệp vụ, quyền, tiền, lịch, CAS và giữ file vẫn theo main CRM-41-03, FIX01 và đặc tả 41–42.

Cách làm:
- Coder chỉ dùng Read/Glob/Grep/Edit/Write. Không chạy Python, Node, SQL, Word/COM, trình duyệt hay launcher.
- **Mọi test dưới đây: NOT_RUN.**
- Kết quả F16 Root đã chạy (31/31 thuần, 11/11 CJS) **không** chứng minh các nhánh FIX02.
- Không tuyên bố full CRM/M4, GUI thật, Word hay PDF thật đạt.

**Phạm vi ghi** (6 file đã có, NEW = 0):
- `src/kho_tri_thuc/giao_dien/assets/crm_g.js`
- `src/kho_tri_thuc/nguon/crm_docx.py`
- `tests/crm_giao_ket_async.cjs`
- `tests/test_crm_giao_ket.py`
- `tests/test_crm_giao_ket_http.py`
- `docs/BAO-CAO-CRM-41-03.md`

**Không sửa:** service tài chính `crm_giao_ket.py`, route `crm_g.py`, CSS, SQL/M21, host/guard `trich6_host.py` (chỉ dùng lại `_JobWindows`/`_doc_dong`/`env_con`/guard), M4/M9, Review/engine, reference/staged patch, dependency/launcher/master/quyền. Không xóa, đổi tên hay ghi đè tệp.

| # | Finding | Sửa (file · hàm) | Test đã viết | Kết quả |
|---|---|---|---|---|
| GUI-1 | 409 pending phải giữ body/khóa gốc tới FINAL | `crm_g.js`:<br>• `MA_DANG_XU_LY` = {`CRM_GK_DANG_XU_LY`, `CRM_GK_LAN_KHONG_KHOP`}; `dangXuLy`; `chuaRo` coi hai mã này là chưa rõ<br>• `gui` giữ khóa; `veGuiLai` hiện nút "Đối soát y nguyên (cùng khóa)", không tự gửi lại<br>• bấm lại nút lệnh gốc dùng CÙNG khóa<br>• 409 khác (xung đột body/revision/quyền/chặn) là kết quả xác định → nhả khóa, không nút | cjs **B1** (cả hai mã → FINAL cùng body/khóa; IDEMPOTENCY_KHAC / REVISION_CU → không nút, khóa mới) | NOT_RUN |
| GUI-2 | Fence của ý định gốc xuyên POST/làm mới/Chuyển/toast/lỗi/gửi lại/G7/blob | `crm_g.js`:<br>• `fenceForm`; `gui(path, body, ok, f, sau, fv)` có `f` (vận chuyển) và `fv` (hiển thị, chụp thế hệ form MỘT lần trước lệnh)<br>• toast/trạng thái/nút/làm mới/đổi chế độ chỉ khi `fv()`<br>• `veGuiLai` gửi lại bằng đúng `f`/`fv`/`sau` gốc<br>• phần tiếp `sau` cho Lưu G2/G3, In, Chuyển, Hủy, Xuất<br>• Chuyển chỉ đổi sang G3 khi `fv()`, fence lồng chụp ngay sau chuyển trạng thái của chính lệnh<br>• lưu về muộn khi người dùng đã gõ: im lặng, chỉ ghi `revDaLuu`/`bgMoi` để lần lưu sau là revision kế tiếp của đúng đối tượng (không tạo báo giá trùng)<br>• bỏ thông báo "dữ liệu mới đã về" của chuỗi cũ<br>• lỗi G7 có fence thế hệ | cjs:<br>• **B2**: Chuyển về muộn (thành công/lỗi) sau khi gõ → không đổi chế độ, không GET, không thông báo; ca dương sang G3<br>• **B3**: Lưu mất ACK → gửi lại → gõ → FINAL im lặng; lần sau khóa mới + `expected_revision` = 7; G7 lỗi muộn im lặng<br>• **B4**: Xuất về muộn im lặng<br>• giữ A1–A10 (blob: A5) | NOT_RUN |
| GUI-3 | Chỉ đổi mẫu cũng là bẩn | `crm_g.js`: `NOI_DUNG = /^gk-(bg-\|so-)(?!mau-\|huy-)/` → `so-doi-*` là nội dung bản soạn. `bg-mau-*` (tham số Chuyển) và `bg-huy-*` không buộc lưu. Lưu mang mẫu/lý do/revision; Xuất chỉ mở khi revision mới đã nạp về form. Cổng In 100%/FX không chặn Lưu/Chuyển (giữ A7) | cjs **B4** | NOT_RUN |
| GUI-4 | Số tự tính đang hiện phải hết hiệu lực ngay khi sửa | `crm_g.js`:<br>• `khoaChuaLuu` (chạy ngay trong handler input) đánh dấu mọi `.gk-tu-tinh` là "đã sửa: chưa tính lại" (`data-het-hieu-luc`) và gắn nhãn "[Revision đã lưu …]" cho tổng/VND ở `veKiem`; bỏ `xemTruoc`<br>• không vẽ lại form (giữ caret), không tính ở client, không POST mỗi phím<br>• tính thử về muộn không khôi phục số cũ | cjs **B5** (kiểm DOM ngay, cùng phần tử input, trước khi đổi tab; tính thử muộn bị bỏ; tính thử hiện hành hiện) | NOT_RUN |
| W-1 | Sở hữu Word theo binding FIX02 | `crm_docx.py`:<br>• `WordSoHuu.tao`: CreateProcessW(đúng WINWORD ghim, `"…" /w`, `CREATE_SUSPENDED`, `STARTF_USESHOWWINDOW` + `SW_HIDE`), giữ handle process/thread → Job riêng → `IsProcessInJob` + ảnh tiến trình qua handle + thời điểm tạo → `ResumeThread`<br>• `cho_cua_so`: chờ hữu hạn `_WwG` của đúng PID<br>• `chung_minh`: chỉ tại đây mới import/khởi tạo pythoncom (STA); NativeOM → Word.Window, roundtrip `Window.Hwnd` → PID, vẫn trong Job → `Window.Application`<br>• bỏ `DispatchEx`, PID-delta, `_com_thuoc_pid`/`chung_minh_so_huu`<br>• worker chỉ Close/Quit đối tượng đã chứng minh; không sở hữu được → `KHONG_SO_HUU:*` (PDF_CHUA_SAN_SANG, DOCX giữ)<br>• `PHIEN_BAN_RENDERER` → `word-com/2` | `KetLuanWorker.test_so_huu_word_theo_binding_fix02` (tĩnh: thứ tự, cờ, không fallback, không import COM cấp module) | NOT_RUN |
| W-2 | Mọi nhánh lỗi/quá hạn có stop witness hữu hạn hoặc UNKNOWN | `crm_docx.py`:<br>• `_chuyen_pdf_mot` bắt mọi lỗi spawn/gán Job/stdin/giao thức/EOF/quá hạn<br>• `_dung_cay` dừng đúng cây đã sở hữu (Job; chưa gán thì TerminateProcess đúng handle, worker chưa nhận stdin) và chờ worker + Job rỗng có hạn → `DA_DUNG` hoặc `UNKNOWN` (PDF_LOI); `CloseHandle`/KILL_ON_CLOSE không tính là bằng chứng<br>• `WordSoHuu.dung`: handle signaled + Job Word rỗng, hoặc None<br>• COM treo → hạn của parent kết thúc Job ngoài (Word là con không breakaway nên nằm trong cây) | `VongDoiParent` (7 ca: gán Job lỗi không ghi stdin, EOF/quá hạn, Job không rỗng / truy vấn lỗi / worker treo → UNKNOWN, stdin lỗi, PDF có sẵn không spawn, dừng false/chưa rõ, dương)<br>`DungWordSoHuu` (8 nhánh) | NOT_RUN |
| W-3 | Native test an toàn | `test_crm_giao_ket.py`:<br>• `_co_word` chỉ đọc metadata (`find_spec`, không import pythoncom)<br>• `_ConSoHuu`: native child, Job trước stdin, đọc có hạn, dừng qua `_dung_cay`; không dừng được → fail<br>• `crm_docx --word-control`: Word control tổng hợp do child tạo/sở hữu/chứng minh như worker trước khi Open<br>• `WordThat` không gọi COM ở test chính; Word có sẵn chỉ xem PID; không sở hữu control → skip NOT_VERIFIED (không PASS) | `WordThat` (cần Word ghim + guard; Root chạy riêng) | NOT_RUN |
| W-4 | Cộng số lần cho văn bản trùng | `crm_docx.py` `kiem_pdf`: cộng số lần của các mục có cùng văn bản sau NFC + bỏ khoảng trắng; không max/khử trùng; giữ giá trị 1 ký tự và `VAN_BAN_CO_BAN` | `KiemPdfDem.test_cong_so_lan_cua_muc_trung_van_ban` (hai "0" cần 2 lần; một "0" thiếu; trùng sau khoảng trắng; trùng sau NFC) | NOT_RUN |
| HTTP | Fixture đưa nhãn "MAU V1/V2" vào khóa, sai `KHOA_RE` | `test_crm_giao_ket_http.py`: `khoa_may` (deterministic, ví dụ `mau-v1`) cho các khóa `tai-`/`map-`/`gui-`/`kiem-`/`duyet-`. DOCX vẫn chứa đúng "MAU V1"/"MAU V2"; luồng tải → KT → CFO, assertion g01–g10 và regex sản phẩm giữ nguyên. Thêm `test_g00_khoa_fixture_hop_le` | g00 (+ g01 → g04/g05 hết lỗi dây chuyền nếu đúng nguyên nhân) | NOT_RUN |

**Giới hạn còn mở (FIX02):**
1. **Word native chưa được kiểm.**
   - Chưa rõ `/w` + `SW_HIDE` có tạo cửa sổ `_WwG` trả NativeOM trong hạn trên máy Anh không. Nếu không, kết quả là `KHONG_SO_HUU:KHONG_CO_CUA_SO_TAI_LIEU_TRONG_HAN` (PDF_CHUA_SAN_SANG, DOCX giữ). Như vậy là trung thực nhưng **chưa** đạt mục tiêu PDF thật.
   - Khả năng ẩn thực tế của cửa sổ, tệp tạm native của Office và tác động lên Word có sẵn chỉ có thể báo theo bằng chứng sau khi Root chạy. Guard Python không chứng minh được Office không tạo/xóa tệp tạm.
2. Service `crm_giao_ket.py` không sửa (ngoài phạm vi lượt này): danh sách nội dung kỳ vọng G2/G3 giữ như FIX01. Phép cộng số lần thực hiện trong `kiem_pdf`, nên mọi đường gọi đều được áp dụng. Không đổi chính sách tài chính.
3. **GUI:**
   - Lệnh chưa rõ mà người dùng gõ tiếp trước khi có kết quả: khóa vẫn giữ, gửi lại vẫn dùng body gốc, nhưng kết quả về muộn **không hiển thị** (theo yêu cầu không có thông báo cũ). Trạng thái thực thấy được sau ↻ Làm mới.
   - Harness cjs là DOM giả, không phải trình duyệt.
4. Chỗ đặt in/xuất kẹt khi tiến trình chết trước `ket_qua.json` vẫn như FIX01 (409 đang xử lý; người dùng đối soát hoặc dùng ý định mới). Chưa có công cụ giải phóng.

---

Trạng thái lượt **CRM_41_03_FIX01_CODE_ONLY**: **CODE_WRITTEN — NOT_RUN_CODE_ONLY**.
Coder chỉ dùng Read/Glob/Grep/Edit/Write. Không chạy Python, node, SQL, Word/COM, trình duyệt hay launcher; không chạy test nào. Root chạy các test ở §5. Mọi ô "Kết quả" bên dưới đều là **NOT_RUN**.
Báo cáo này **không** tuyên bố: full CRM, M4, actual GUI đạt, hay Word native đạt.

## 1. Phạm vi G2/G3 (giữ nguyên như đã chốt; FIX01 không viết lại)

- **Dữ liệu:** migration `M0021_CRM_G2G3` được append sau SQL 1–20; 870225 byte đầu giữ nguyên, không có M0022. M21 chưa áp vào DB nên FIX01 sửa trực tiếp phần append. Nội dung:
  - bảng báo giá và revision;
  - điều khoản tham chiếu;
  - bản soạn và revision (ghim mẫu, danh mục, profile);
  - lần xuất `crm_gk_xuat`;
  - discriminator `hop_dong.crm_giao_ket` (SOAN_THAO/CHO_KY).

  Mọi lệnh đều là hàm INVOKER chỉ chạy trên kết nối chủ bảng và dùng chung biên nhận `crm_g_bn_*`. Không sinh nghĩa vụ, lịch thu hay M1.
- **Service** `k2/crm_giao_ket.py`, chạy trên cùng `CrmMauK2`:
  - chuẩn hóa và tính báo giá bằng số nguyên đơn vị nhỏ nhất + Fraction, không float, không làm tròn;
  - so lệch G7;
  - cổng In (100% / FX tay);
  - Chuyển sang Soạn tạo đúng một hợp đồng;
  - soạn theo mẫu đã ghim;
  - in/xuất ba pha: A dưới khóa → B ngoài khóa (DOCX → Word → PDF) → C dưới khóa (quyền + CAS → công bố).
- **Renderer** `nguon/crm_docx.py`:
  - điền DOCX theo run-map: xử lý run bị tách, bảng lồng, header/footer;
  - DOCX báo giá;
  - định dạng tiền, ngày, số bằng chữ;
  - Word COM worker có Job riêng;
  - kiểm PDF bằng PDFium và pdfplumber.
- **Route** `giao_dien/crm_g.py`: lệnh ngắn đi dưới mutation lock; lệnh dài `bao-gia/in` và `soan/xuat` render ngoài khóa.
- **Giao diện** `#crm-gk` trong `crm_g.js` + `style.css`: G2 hai cột, G3 ba cột, dùng lại cổng đổi vai `window.kttChung`.

## 2. FIX01 — finding → sửa → test đã viết → kết quả

| # | Finding (GIAO-SUA §2–4) | Sửa (file · hàm) | Test đã viết | Kết quả |
|---|---|---|---|---|
| 1 | Giữ fence của ý định gốc xuyên cả chuỗi async (A3) | `crm_g.js`:<br>• `napDs(fs0)` trả bool<br>• `nap(…, fs0)`, `napBgCt(fs0)`, `napSoCt(fs0)`<br>• `napLai(fs0)` dừng khi người dùng gõ hoặc đổi chế độ<br>• callback Lưu G2/G3, In, Xuất truyền `fc` (`napDs(fc) && fc() → napBgCt/napSoCt(fc)`)<br>• lỗi/toast muộn bị fence trong `gui` | `crm_giao_ket_async.cjs`:<br>• A3 giữ nguyên assertion<br>• A6: lỗi POST muộn sau "+ Báo giá mới"<br>• A10: G3 làm mới treo → gõ → không GET đè; POST Lưu G3 mất kết nối sau khi đổi tab → không có nút gửi lại hay thông báo cũ | NOT_RUN |
| 2 | Nạp G7 AMOUNT không mất dữ liệu | `crm_g.js`:<br>• `minorSangChinh` chuyển chuỗi chính xác, VND 0 / USD 2<br>• `napG7` giữ loại, thứ tự, mốc, ghi chú, số tiền, tiền tệ; tiền tệ lạ thì không nạp và giữ lịch<br>• cột tiền tệ dòng `tt` trong `COT_L`, `ghiLich`, `docLich` (`tien_te`) | `cjs` A8:<br>• AMOUNT USD 123456 → `1234.56`<br>• AMOUNT VND 5000000<br>• AMOUNT USD 5 → `0.05`<br>• PERCENT 10<br>• body Lưu đúng<br>• EUR → không nạp | NOT_RUN |
| 3 | Thay đổi chưa lưu ≠ revision dùng cho In/Chuyển/Xuất | `crm_g.js`:<br>• `soSua`/`dongBo`/`chuaLuu`; `o()` đếm sửa nội dung<br>• `ghiFormBg`/`ghiFormSo`/`boChon` đồng bộ<br>• `nutLuuTruoc` + `khoaChuaLuu` vô hiệu ngay khi gõ, có lý do (`oLyDo`), kiểm lại lúc bấm<br>• Lưu không bị chặn; cổng In không chặn Lưu/Chuyển<br>`style.css`: `.gk-ly-do` | `cjs`:<br>• A7: In/Chuyển khóa ngay, 0 POST; lưu + nạp → bật lại; `chan_in` không khóa Lưu/Chuyển<br>• A10: Xuất khóa khi chưa lưu | NOT_RUN |
| 4 | Hiện phía còn lại (%↔tiền) và VND tham chiếu từng dòng | `crm_giao_ket.py`:<br>• `xem_truoc` chỉ đọc, RR, dùng cùng `chuan_hoa_bao_gia` + `tinh_bao_gia`, kiểm quyền PN<br>`crm_g.py`:<br>• `TRUONG_GK["bao-gia/xem-truoc"]={"du_lieu"}`, `_lenh_gk`<br>`crm_g.js`:<br>• nút "Tính thử", `tinhChoForm`/`tuTinh`, cột "Tự tính (chỉ đọc)"; kết quả cũ không áp lên form đã đổi<br>`style.css`: `.gk-tu-tinh` | `cjs` A9<br>`test_crm_giao_ket.py` `RouteTinh`<br>HTTP g10: số chính xác, VND theo dòng, 0 ghi, DTO chặt (khóa thừa → 400) | NOT_RUN |
| 5 | Đặt chỗ render bền trước pha B; cùng khóa → đối soát; khác body → 409 | `pg_migrations.py` (M21):<br>• bảng `crm_gk_lan` + trigger `crm_gk_lan_kiem`<br>• `crm_gk_pn`, `crm_gk_dat_lan`<br>• `crm_gk_xuat_ghi` chỉ công bố đúng chỗ đặt (`CRM_GK_LAN_KHONG_KHOP`) rồi chuyển chỗ đặt sang DA_CONG_BO<br>`crm_giao_ket.py`:<br>• `_dat_lan`; `render` dùng thư mục `kho/lan/<lan_id>` (không UUID mới) và `ket_qua.json` bất biến; `doi_soat`; lỗi xác định được ghi bền<br>`crm_g.py`: `MA_409_GK` | `test_crm_giao_ket.py`:<br>• `M21Tinh.test_lan_dat_cho_ben_va_cong_bo_dung_lan`<br>• `DatChoRender` (1 lần render/1 thư mục, render chồng → lỗi, đối soát không gọi Word, lỗi đã ghi được trả lại)<br>HTTP g08 (deterministic):<br>• lần 1 dừng giữa pha B<br>• cùng khóa → 409 `CRM_GK_DANG_XU_LY`<br>• bản soạn khác cùng khóa → 409 `CRM_G_IDEMPOTENCY_KHAC`<br>• replay → `lap_lai`<br>• đếm: render = 1, `crm_gk_lan` +1, thư mục lần chạy +1, xuat +1 | NOT_RUN |
| 6 | Ghim quyền trước khi chờ khóa namespace, ở mọi lệnh | `pg_migrations.py`: `_GK_GHIM` (`crm_g_ghim_quyen(crm_gk_pn(…))`) trước `crm_gk_dich` trong:<br>• `bao_gia_luu`, `bao_gia_huy`, `chuyen`, `soan_luu`<br>• `xuat_ghi` (công bố)<br>• `dat_lan` | `M21Tinh.test_ham_lenh_invoker_quyen_truoc_bien_nhan` (6 hàm, thứ tự ghim < dich < bn_tra)<br>HTTP g09: giữ đúng advisory lock của (PN, actor, HUY, khóa) → lệnh đứng chờ (thấy trong `pg_locks`) → thu hồi bằng `lock_timeout 1s` phải lỗi `LockNotAvailable` → nhả → 200 → thu hồi → replay bị từ chối | NOT_RUN |
| 7 | Tổng canonical theo profile `kiem_tong` | `crm_giao_ket.py`:<br>• `rang_buoc_tong` (chỉ cơ sở `*_CHUA_VAT` mới được hiểu là NET)<br>• `kiem_tong_canonical` (`CO_SO_TONG_KHONG_KHOP`, `TONG_TRUONG_KHAC_TONG_LICH`, cảnh báo `CHUA_CO_RANG_BUOC_TONG`)<br>• `chuyen` chỉ tự điền đúng trường đó khi NET khớp<br>• `_profile` + `PROFILE_DA_DOI` trong `kiem_soan`/`doc_soan`/`chuan_bi_xuat` | `TongCanonical` (6 ca)<br>HTTP g10: NET USD → `{"so_tien":"1000","tien_te":"USD"}`; khác tổng → chặn Xuất; GROSS → không điền, nhập tay → `CO_SO_TONG_KHONG_KHOP` | NOT_RUN |
| 8 | Mốc trống chỉ là cảnh báo; in không TypeError | `crm_giao_ket.py`: `tinh_bao_gia` cảnh báo `MOC_TRONG` cả khi NGAY/SU_KIEN có giá trị NULL; `_moc` in "Ngày: chưa xác định" / "Sự kiện: chưa xác định" / "Chưa xác định" | `MocTrong`<br>HTTP g10: in USD có mốc trống, DOCX chứa đúng chuỗi | NOT_RUN |
| 9 | Dừng trước khi công bố; thành công chỉ khi Word sở hữu đã dừng | `crm_docx.py`:<br>• `_ket_luan` thuần: PDF_DA_TAO chỉ khi thoát mã 0, `da_dung is True`, PID đã chứng minh + gán Job, PID trong báo cáo khớp, Job rỗng, PDF tồn tại; ngược lại PDF_LOI và giữ PDF làm bằng chứng<br>• worker hạ PDF_DA_TAO khi chưa xác nhận dừng<br>`crm_giao_ket.py`: `_render_trong` không kiểm/công bố PDF khi `da_dung` khác True | `KetLuanWorker` (10 ca tiêm lỗi + PDF vắng + chưa sở hữu)<br>`test_render_pdf_co_nhung_word_chua_dung_khong_pdf_dat` | NOT_RUN |
| 10 | Chứng minh sở hữu trước mọi mutate/Open/Quit; không Caption/FindWindow/Hwnd tự đặt | `crm_docx.py`:<br>• `_com_thuoc_pid`: chỉ đọc, OLEACC `OBJID_NATIVEOM` trên cửa sổ của PID, so định danh COM<br>• `chung_minh_so_huu` dùng chung, `cho_handle_dung`<br>• worker gọi `chung_minh_so_huu`; không chứng minh được → `KHONG_SO_HUU:*`, NOT_VERIFIED, không Open/Quit/kill, giữ DOCX | `KetLuanWorker.test_worker_khong_caption_findwindow` (tĩnh) | NOT_RUN |
| 11 | An toàn của test Word | `test_crm_giao_ket.py` `WordThat`:<br>• instance "Word người dùng" của test phải qua `chung_minh_so_huu` trước Open; không chứng minh được → skip NOT_VERIFIED, không Quit/kill<br>• chỉ Quit instance đã chứng minh; dừng có hạn `cho_handle_dung(h, 30)` phải True; đóng handle<br>• tiêm lỗi thuần ở `KetLuanWorker` (không dùng làm bằng chứng native PASS) | như cột trái | NOT_RUN |
| 12 | Kiểm nội dung PDF đầy đủ, ghi nhãn đúng mức | `crm_docx.py`: `kiem_pdf` nhận `(chuỗi, số lần)`, đếm sau NFC + bỏ khoảng trắng, không bỏ giá trị ngắn; `muc_kiem="VAN_BAN_CO_BAN"`<br>`crm_giao_ket.py`:<br>• G3: mọi giá trị đã ánh xạ × số ô<br>• G2: số, ngày, người lập, khách, thông tin giá, từng ô lịch, câu FX đầy đủ, phí bảo trì, điều khoản, hết hạn | `KiemPdfDem` (pypdfium2/pdfplumber giả chỉ trong test thuần)<br>`WordThat` dùng số lần (header/footer = 2) | NOT_RUN |
| g07 | Fixture: PDF lỗi sau CHO_KY không được hạ trạng thái | `test_crm_giao_ket_http.py` g07: ghi nhận (soạn, hợp đồng, discriminator) trước lần thử, assert giữ nguyên sau PDF_LOI; ghi rõ nhánh đã chạy (CHO_KY khi có Word, SOAN_THAO khi không). Không sửa product để khớp oracle cũ | g07 | NOT_RUN |

Cập nhật kèm: `NhaCungCapPdf.test_render_giu_docx_bat_bien_truoc_pdf` thêm `lan_id`. `WordThat.test_qua_han_trung_thuc` nhận mã `WORKER_QUA_HAN_HOAC_EOF`.

## 3. File thay đổi trong lượt FIX01 (9 file đã có + 1 file mới)

- `src/kho_tri_thuc/ha_tang/pg_migrations.py`: chỉ phần append M0021, gồm:
  - `_GK_BANG_MOI` có thêm `crm_gk_lan`;
  - `_GK_GHIM`;
  - bảng/trigger `crm_gk_lan`;
  - `crm_gk_pn`, `crm_gk_dat_lan`;
  - ghim quyền trong 5 hàm lệnh;
  - `crm_gk_xuat_ghi` (đối chiếu chỗ đặt);
  - REVOKE.

  Không đụng SQL 1–20 và không tạo M0022.
- `src/kho_tri_thuc/k2/crm_giao_ket.py`:
  - `tinh_bao_gia`, `_moc`;
  - `rang_buoc_tong`, `kiem_tong_canonical`;
  - `chuyen`, `_profile`, `kiem_soan`, `doc_soan`;
  - `xem_truoc`;
  - `chuan_bi_in`, `chuan_bi_xuat`, `_dat_lan`;
  - `render`, `_render_trong`.
- `src/kho_tri_thuc/nguon/crm_docx.py`:
  - `_chuyen_pdf_mot`, `_ket_luan`;
  - `kiem_pdf`;
  - `_com_thuoc_pid`, `chung_minh_so_huu`, `cho_handle_dung`;
  - `_worker` (bỏ đặt thuộc tính nhận dạng / tìm cửa sổ toàn cục, bỏ `secrets`).
- `src/kho_tri_thuc/giao_dien/crm_g.py`: `TRUONG_GK`, `_lenh_gk`, `MA_409_GK`.
- `src/kho_tri_thuc/giao_dien/assets/crm_g.js` (IIFE thứ hai `#crm-gk`):
  - trạng thái thay đổi chưa lưu, `minorSangChinh`;
  - chuỗi nạp có fence;
  - `ghiLich`/`docLich` (tiền tệ dòng);
  - `tinhChoForm`/`tuTinh`/`veLich`;
  - `nutLuuTruoc`/`khoaChuaLuu`/`oLyDo`;
  - `veBgEditor` (Tính thử, In/Chuyển dùng revision đã lưu, chọn nguồn lịch thì vẽ lại để hiện nút G7);
  - `napG7`, `ghiFormSo`, `veSoEditor`.
- `src/kho_tri_thuc/giao_dien/assets/style.css`: `.gk-tu-tinh`, `.gk-ly-do`.
- `tests/test_crm_giao_ket.py`:
  - cập nhật `M21Tinh`, `RouteTinh`, `NhaCungCapPdf`, `WordThat`;
  - thêm `MocTrong`, `TongCanonical`, `KetLuanWorker`, `KiemPdfDem`, `DatChoRender`.
- `tests/test_crm_giao_ket_http.py`: sửa g07, viết lại g08; thêm g09, g10 và các helper `tao_soan`, `gt_du`.
- `tests/crm_giao_ket_async.cjs`: giữ nguyên P0 và A1–A5; thêm A6–A10.
- NEW `docs/BAO-CAO-CRM-41-03.md` (báo cáo này).

Không sửa file nào khác. Không xóa hay dọn file. Không đọc var/.env/backup/dữ liệu thật/thông tin đăng nhập. Không sửa hay seed M9, sourceReview, source engine, staged patch hoặc reference.

## 4. Giới hạn còn lại (trung thực)

1. **Có thể Word native sẽ ra NOT_VERIFIED.**
   - Chứng minh sở hữu cần cửa sổ của PID mới mà native Word OM trả về được qua OLEACC. Instance `DispatchEx` ẩn, chưa mở tài liệu, có thể chưa có cửa sổ như vậy.
   - Khi đó worker trả `KHONG_SO_HUU:CHUA_CHUNG_MINH_DOI_TUONG_COM` → PDF_CHUA_SAN_SANG, DOCX vẫn giữ, không có CHO_KY.
   - Đây là kết quả đúng theo giao việc (không giả PDF pass) nhưng nghĩa là đường PDF thật **chưa được chứng minh**. Lượt này không chạy Word native.
   - `WordThat` cũng skip (NOT_VERIFIED) nếu instance của chính test không chứng minh được.
2. **Chỗ đặt có thể kẹt.**
   - Nếu tiến trình chết sau khi đặt chỗ nhưng trước khi ghi `ket_qua.json` (hoặc gặp lỗi không phải DataError, ví dụ OSError), khóa đó luôn trả 409 `CRM_GK_DANG_XU_LY`.
   - Không render lại mù. Người dùng phải dùng khóa mới (ý định mới). Chưa có công cụ để chủ CSDL giải phóng chỗ đặt.
   - Kết quả đã ghi nhưng chưa công bố (mất ACK, vai đổi) được đối soát và công bố bằng đúng khóa đó.
3. **Kiểm PDF chỉ là kiểm văn bản cơ bản** (`muc_kiem=VAN_BAN_CO_BAN`): chữ, số, số lần xuất hiện, số trang, phông có mặt, render được. Không kiểm fidelity bố cục, glyph hay thị giác.
4. **Giao diện:**
   - Chỉ có harness DOM giả `cjs` (NOT_RUN). Chưa chứng minh GUI thật hay khả năng truy cập.
   - Tính thử là thao tác chủ động (nút), không tự chạy khi gõ.
   - Đổi mẫu (`so-doi-*`) không bị tính là thay đổi nội dung; lệnh Lưu bắt buộc khi đổi mẫu.
5. **Cổng tổng canonical** chỉ áp khi profile khai `kiem_tong.co_so` dạng `*_CHUA_VAT`. Cơ sở khác hoặc thiếu → chặn hoặc cảnh báo, không suy đoán. Loại hình chưa khai thì chỉ cảnh báo `CHUA_CO_RANG_BUOC_TONG`.
6. **Chưa chạy bất kỳ test nào.** Test HTTP cần `KHO_PG_DSN_TEST` lúc chạy (do Root cấp); thiếu thì skip = NOT_RUN. Test Word cần Word đã ghim, pywin32 và guard A517.

## 5. Root chạy (gợi ý, chưa chạy)

- `python -m unittest tests.test_crm_giao_ket -v` (thuần + tĩnh; Word có điều kiện).
- `python -m unittest tests.test_crm_giao_ket_http -v` (cần `KHO_PG_DSN_TEST`; chạy g00→g10 theo thứ tự).
- `node tests/crm_giao_ket_async.cjs` (P0, A1–A10, FIX02: B1–B5, FIX03: C1–C2).

## 6. Hàng chờ (không đổi)

- Không đẩy backlog CRM catalog KCN/NHA, E3, E5, G4–G6 sang E1. Full M4 (Review/Cổng/L3/duyệt-PDF/kế toán-công nợ/Request) và M2-00 → E1-MUA giữ theo hàng chờ đã chốt. M9 tiếp tục dừng; kho thật vẫn SQLite; không bật cloud AI, không dùng dữ liệu thật.
- M4 L3, PDF, KT, AP, Request giữ đúng hàng chờ.
- G4 Ký kết chưa nối (giao diện ghi rõ, không có nút giả).
- Không có tuyên bố full CRM, M4, actual GUI hay Word native đạt.
