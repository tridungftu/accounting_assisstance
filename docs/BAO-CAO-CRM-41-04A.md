# BÁO CÁO CRM-41-04A — G4 ký lần đầu (CODE_ONLY)

## Mốc 2 — CRM_M4_PARALLEL_THREE_CODE_ONLY (3 worker song song, đã join)

**Trạng thái: NOT_RUN_CODE_ONLY.** Ba named worker (crm-data, crm-ui, m4-ui) chạy song song, ở foreground, mỗi loại một lần. Cả ba đều **kết thúc và trả kết quả**; không có worker nào lỗi hay dừng dở (worker error/incomplete: không có). Coordinator không sửa file nào của worker. Mọi kết quả dưới đây là phần worker tự khai, coordinator chỉ đọc đối chiếu một điểm (DTO, xem cuối mục). Không ai chạy test, migration, SQL, Node, GUI hay Word. PASS của baseline, hay của mốc 1, **không** chuyển thành PASS cho mốc này.

### crm-data (5 file: `pg_migrations.py` chỉ trong M0023, `crm_g.py`, `k2/crm_ky_ket.py`, `tests/test_crm_ky_ket.py`, `tests/test_crm_ky_ket_http.py`)

- **Đọc bản ký phải có phạm vi tường minh.**
  - Hàm chung mới `master.crm_ky_pham_vi_hd(p_soan, p_hanh, p_vai)`.
  - Ký: chỉ BAN_HANG với `CRM_KY_KET`.
  - Đọc: người ký trong phạm vi, hoặc KE_TOAN/KE_TOAN_TRUONG/CFO có phân công `CRM_KY_DOC` cộng binding đúng hợp đồng.
  - Bỏ nhánh cũ cho KT/KTT/CFO đọc chỉ nhờ pháp nhân + module + vai.
  - Không seed và không tự cấp quyền. DEMO KT/CFO sẽ không xem được chi tiết bản ký cho tới khi quản trị cấp quyền.
- **`crm_ky_tep` khóa quyền và binding trước khi kiểm đọc**, để không lọt khe thu hồi giữa lúc kiểm và lúc ghi audit/hash.
- **PDF ký trùng byte với PDF xuất G3 giờ hợp lệ.**
  - Bỏ CHECK `ky_pdf_sha256 <> g3_pdf_sha256` và mã lỗi `CRM_KY_PDF_LA_BAN_XUAT`.
  - Mục 3 và mục 5 (§7 tiêu chí 1) bên dưới thuộc **mốc 1** và đã lỗi thời ở điểm này.
  - Vẫn giữ: kiểm hash/độ dài, bản xuất phải mới nhất, mỗi hợp đồng một bản ký, khóa mới + cùng PDF trả lại cùng bản ký, mọi khác biệt sau ký thành Q-RETURN.
- **Route:** POST `ky-ket` trước đây nhận query string mà không báo lỗi; nay trả 400 (`_khong_query`), kể cả `?x` và `?x=`, trước khi đọc header/body/phiên/lock. Hai route GET G4 dùng cùng kiểm này.
- **Tests (NOT_RUN):**
  - Fixture service mock dùng `chuan_hoa_bao_gia(bao_gia())`, sửa 3 lỗi KeyError mà worker khai từ baseline PASS26 ERROR3.
  - Test tĩnh/mock/PG mới cho phạm vi đọc, PDF trùng byte và query.
  - HTTP:
    - k02: KT không có phân công thì không đọc được; CFO nhận 404.
    - k03b mới: các ca âm về phạm vi KT/CFO.
    - k07: thu hồi binding của KT.
    - k08 mới: ký trùng byte trên hợp đồng riêng.
  - k01: `_co_word()` chỉ là dò. Ca dương chỉ chạy sau `g3_dat_that` (có PDF_DAT thật: dòng CSDL, CHO_KY, tải G3 qua HTTP khớp hash/độ dài).
  - **Nới một assertion, có chủ ý:** khi dò Word đạt, k01 chấp nhận PDF_DAT, PDF_LOI hoặc PDF_CHUA_SAN_SANG và ghi lại trạng thái thật. Root cần duyệt điểm này.

### crm-ui (2 file: `assets/crm_g.js` chỉ trong khối G4, `tests/crm_ky_ket_async.cjs`)

- **ACK được kiểm trước khi coi là FINAL (`ackKy`).** Phản hồi 2xx thiếu hoặc lệch bất kỳ trường nào thì coi là UNKNOWN:
  - định danh và trạng thái: ky_id, trang_thai DA_KY, lap_lai;
  - khớp ý định gốc: soan_id, hop_dong_id, revision, xuat_id, ngay_ky, co_sua;
  - khớp tệp và căn cứ: ky_pdf_len bằng kích thước File, ky_pdf_sha256, g3_pdf_sha256 bằng căn cứ đã chụp;
  - G5 khớp với khai báo Có/Không.

  Khi UNKNOWN, giữ nguyên File, header và khóa; không hiện nhãn "đã ký" và không làm mới.
- **Tách ý định bền khỏi guard hiển thị.** Guard `ht` chụp một lần cho mỗi lần gửi, gồm epoch, vai, bản soạn, tab, form, điều hướng và `#hopdong`. Bỏ `y.ep = ep`. Kết quả về muộn thì im lặng.
- **Tải bản ký** có thêm fence điều hướng (`genVao`, hashchange) và kiểm lại ngay trước khi click.
- **Harness:**
  - chỉ `unref()` các timer 60000 ms;
  - mô phỏng hashchange của crm_g.js;
  - K6 dùng ACK đầy đủ;
  - thêm K9 (20 biến thể ACK sai), K10 (ABA vai/tab), K11 (tải tệp qua điều hướng);
  - giữ nguyên assertion K0–K8.
- **Còn mở:** `taiTep` của G3 (khoảng dòng 763) chưa có fence điều hướng; worker cố ý giữ nguyên G3.

**Đối chiếu DTO (coordinator chỉ đọc):** `master.crm_ky_kq` cùng `lap_lai` từ `CrmKyKetK2.ky` có đủ các trường mà `ackKy` cần. Đây là đọc mã tĩnh, chưa chạy.

### m4-ui (tham chiếu, ngoài phạm vi CRM)

Worker m4-ui sửa `m4/giao_dien/chung_tu.js` (R5/R6: giữ khóa đích đang bay, `treo` theo khóa), thêm U8–U11 vào `tests/m4_02b_async.cjs` và hoàn thiện `docs/BAO-CAO-M4-02B.md`. Chi tiết và các gate xem trong báo cáo đó. Tất cả là NOT_RUN_CODE_ONLY. Toàn bộ M4 **chưa** được nghiệm thu.

### Gate còn OPEN (mốc 2)

- SQL/migration M0023 trên PG thật, gồm sha prefix 928356 byte và sha `crm_giao_ket.py`. Worker không hash được.
- Quyền hiện hành (current rights) với phạm vi `CRM_KY_KET`/`CRM_KY_DOC` thật, đồng thời, và review Q-PII.
- Ca dương Word G3 (PDF_DAT thật) cho k05–k08. Chưa có thì các ca này skip với nhãn NOT_RUN.
- GUI trình duyệt thật, và một lần chạy/kiểm độc lập.
- Chạy `node tests/crm_ky_ket_async.cjs` và hồi quy `crm_giao_ket_async.cjs`.
- Các assertion đếm số migration cũ xung đột với M0023 (mục 8.5 của mốc 1).
- Chưa nghiệm thu toàn bộ CRM, cũng chưa nghiệm thu toàn bộ M4.

---

## Mốc 1 — CRM_41_04A_FIRST_SIGN_CODE_ONLY (lịch sử, giữ nguyên)

**Trạng thái: NOT_RUN_CODE_ONLY.** Lượt này chỉ viết mã và test theo `docs/GIAO-CODE-CRM-41-04A-KY-KET-LAN-DAU.md`. Chưa chạy test, migration, SQL, Node, trình duyệt, Word/Office hay launcher. Không có kết quả PASS nào ở đây. PASS của baseline G1–G3/M4 trước đây **không** áp dụng cho bản mới. Chưa kiểm GUI/SQL/runtime, và CRM chưa được nghiệm thu toàn bộ.

## 1. Đúng 8 file

| # | File | Loại | Nội dung |
|---|------|------|----------|
| 1 | `src/kho_tri_thuc/ha_tang/pg_migrations.py` | sửa (chỉ append) | `M0023_CRM_KY` nối sau prefix 1–22. Giữ nguyên 928356 byte đầu (sha `225cc40f…cce2`). Không có M0024, không bootstrap/M9. |
| 2 | `src/kho_tri_thuc/giao_dien/crm_g.py` | sửa | Route `POST /api/crm/giao-ket/ky-ket`, `GET /api/crm/giao-ket/ky/{soan_id}`, `GET /api/crm/giao-ket/ban-ky/{ky_id}/tep`; ánh xạ mã lỗi sang 400/403/404/409/413/503 |
| 3 | `src/kho_tri_thuc/giao_dien/assets/crm_g.js` | sửa | Khối G4 (nút Ký kết…, dialog, ý định ký, gửi lại y nguyên, khối bản ký, tải PDF bản ký); chế độ chỉ xem cho DA_KY |
| 4 | `src/kho_tri_thuc/k2/crm_ky_ket.py` | mới | Service `CrmKyKetK2`: kiểm quyền, đọc G3, ký, đọc, tải tệp; `kiem_pdf_ky` (fail-closed); `chuan_hoa` |
| 5 | `tests/test_crm_ky_ket.py` | mới | Static/pure/mock service và guard PG thật (skip khi không có DSN) |
| 6 | `tests/test_crm_ky_ket_http.py` | mới | HTTP trên kho PG thử thật (skip khi không có DSN, Word hoặc pypdfium2) |
| 7 | `tests/crm_ky_ket_async.cjs` | mới | Controlled-Promise trên mã thật app.js + crm_g.js, DOM giả (không phải trình duyệt) |
| 8 | `docs/BAO-CAO-CRM-41-04A.md` | mới | Báo cáo này |

Không sửa `crm_giao_ket.py` (test so sha `c155c533…3cc56`). Không sửa M4 (`m4/sql_review.py` và `m4/sql_chung_tu.py`), source app, adapter, master, role hay engine. Không đụng `chung_tu.js`, `m4_02b_async.cjs` hay `BAO-CAO-M4-02B.md`.

## 2. Schema (M0023_CRM_KY)

- **Ràng buộc trạng thái.** `crm_gk_soan` và `master.hop_dong.crm_giao_ket` chấp nhận thêm `DA_KY`. Ràng buộc cũ được thay bằng phiên bản có thêm đúng giá trị đó.
- **`master.crm_ky_pham_vi`** là thin scope binding G4 đúng theo handoff:
  - phạm vi ký theo hợp đồng/dự án/khách, do quản trị (owner) cấp;
  - chỉ INSERT, không UPDATE/DELETE (`CRM_KY_PHAM_VI_BAT_BIEN`);
  - trigger `crm_ky_pham_vi_kiem` kiểm khóa ngoài/khớp chuỗi (`CRM_KY_PHAM_VI_SAI`);
  - **không** suy phạm vi từ người tạo bản soạn.
- **`master.crm_hd_ky`** lưu bản ký bất biến (`crm_g_bat_bien`):
  - ngày ký, người ký phía khách, `co_sua` và mô tả;
  - sha/len/số trang của PDF ký, đường dẫn kho;
  - liên kết đúng `xuat_id`/revision G3, sha/len PDF_DAT G3, tóm tắt (số dòng/tổng minor/tiền tệ);
  - khóa idempotency, người ghi.
  - Trigger `crm_hd_ky_kiem` chặn bản ký lệch G3: bản xuất phải là PDF_DAT, cùng revision, là bản xuất mới nhất, đúng sha (`CRM_KY_G3_LECH`).
- **`master.crm_hd_ky_g5`** lưu trạng thái G5 khởi tạo:
  - `co_sua = true` → `PENDING` (bắt buộc);
  - `co_sua = false` → `NOT_SELECTED`;
  - trạng thái khác → `CRM_KY_G5_SAI` (trigger `crm_hd_ky_g5_kiem`).
  - Bảng bất biến; không có cột kết quả trích hay duyệt.
- **Guard sau ký:**
  - G3 (`crm_gk_soan`, revision, xuất, công bố hiện hành) bị chặn ở CSDL với `CRM_GK_DA_KY`;
  - đặt `DA_KY` mà không có bản ký → `CRM_KY_TRANG_THAI`;
  - `crm_gk_xuat_ghi` được tạo lại, đổi đúng một dòng: kết quả xuất muộn của bản soạn đã ký → `DA_CU`.
- **Hàm SECURITY DEFINER:**
  - `crm_ky_pham_vi_duoc`, `crm_ky_doc_duoc`, `crm_ky_dich`, `crm_ky_tra` (receipt/replay), `crm_ky_kq`;
  - `crm_ky_ket` (17 tham số; khóa hàng; thứ tự: quyền → phạm vi → replay → CAS revision/bản xuất → PDF_DAT → ghi);
  - `crm_ky_doc`, `crm_ky_tep` (kiểm quyền trước metadata/bytes, ghi audit tải).
- **RLS bật.** REVOKE trên bảng/hàm cho app role và PUBLIC. Truy cập chỉ qua hàm.
- **Ngày ký không phải ngày hiệu lực.** Bản ký chỉ cập nhật đúng `UPDATE master.hop_dong SET trang_thai = 'DA_KY', crm_giao_ket = 'DA_KY' WHERE id = s.hop_dong_id;`. Không đặt ngày hiệu lực, phiên bản, lịch thu, số tiền hay công nợ.

## 3. API (crm_g.py → k2/crm_ky_ket.py)

- **`POST /api/crm/giao-ket/ky-ket`**
  - Body là raw `application/pdf`, metadata nằm trong header `X-CRM-G-Info` (JSON URL-encoded). Trường cho phép: `soan_id, expected_revision, expected_xuat_id, ten_tep, ngay_ky, co_sua, mo_ta, nguoi_ky_khach, khoa`.
  - Gửi actor/trạng thái/sha/… → 403 `CRM_G_CLIENT_AUTHORITY`. Trường lạ → 400.
  - Thứ tự xử lý: kiểm quyền và phạm vi **trước** khi parse bytes PDF; sau đó `kiem_pdf_ky` (thiếu pypdfium2 → 503 `CRM_KY_PDF_CHUA_KIEM_DUOC`, fail-closed); PDF rỗng/hỏng → 400; > 50 MB → 413; trùng bytes với bản xuất G3 → `CRM_KY_PDF_LA_BAN_XUAT`; ghi tệp vào kho; gọi `crm_ky_ket` (CAS + replay).
  - Replay cùng khóa và cùng nội dung trả biên nhận cũ (`lap_lai`). Cùng khóa, nội dung khác → 409 `CRM_G_IDEMPOTENCY_KHAC`. Đã ký → 409 `CRM_KY_DA_KY`. Căn cứ cũ → 409 `CRM_KY_XUAT_CU` / `CRM_GK_REVISION_CU`.
  - Phản hồi `hien_thi = "Đã ký — chờ kế toán kiểm"` kèm `g5`.
- **`GET /api/crm/giao-ket/ky/{soan_id}`** trả điều kiện ký (`quyen.ky/doc/ly_do`, `can_cu` đã chụp) hoặc bản ký và lịch sử. Ngoài phạm vi đọc → 404. Query string → 400.
- **`GET /api/crm/giao-ket/ban-ky/{ky_id}/tep`** kiểm quyền trước, rồi kiểm sha/len khi đọc. Trả `application/pdf`, `attachment` với tên do máy chủ đặt, `no-store`, và ghi audit. IDOR hoặc sau khi thu hồi phạm vi → 404.

## 4. UI (crm_g.js)

- **Nút "Ký kết…"** chỉ có ở bản CHO_KY. Nút vô hiệu, kèm lý do `dataset.lyKy`, khi:
  - chưa tải điều kiện, hoặc không có quyền/phạm vi (`LY_KY`);
  - lệch revision, hoặc chưa có PDF_DAT;
  - form G3 chưa lưu.
- **Dialog** (role=dialog):
  - hiện căn cứ đã chụp: mẫu, revision, bản xuất, sha/len, bộ render, tóm tắt;
  - nhập tệp PDF, ngày ký, người ký phía khách, Có/Không (mặc định trống), mô tả khi chọn Có;
  - ghi rõ "Ngày ký không phải ngày hiệu lực" và ý nghĩa G5.
- **Ý định ký đồng bộ (`kyYDinh`, không await):**
  - khóa và header tạo **một lần** cho mỗi bộ (vai, bản soạn, căn cứ, File, khai báo);
  - bấm lặp → 0 POST thêm;
  - còn ý định đang gửi hoặc chưa rõ → chặn ý định mới.
- **Kết quả chưa rõ (UNKNOWN: mất mạng/5xx/đọc dở):**
  - giữ File, header và khóa gốc;
  - nút "Gửi lại bản ký y nguyên (cùng khóa)" chỉ hiện cho đúng vai và đúng bản soạn;
  - đổi vai không xóa ý định, nhưng không bao giờ gửi dưới vai khác.
- **Fence theo ep/actor/genKy/genForm:** GET điều kiện cũ về trễ thì bị bỏ; ACK/lỗi muộn thì im lặng; blob tải về sau khi đổi vai thì không click.
- **409 căn cứ hoặc 401/403:** đóng dialog, tải lại danh sách → bản soạn → điều kiện. Không tự chọn bản khác.
- **Ký thành công:** hiện "Đã ký — chờ kế toán kiểm · G5: …". Không có chữ "Đã chuyển" hay "hiệu lực".
- **DA_KY:**
  - tham số, lịch và mẫu chỉ xem (`tatNhap`);
  - không còn Lưu, Xuất hay đổi mẫu;
  - có khối "Bản ký & đối chiếu" (sha bản ký so với sha bản xuất G3, snapshot, G5, lịch sử) và nút "PDF bản ký ↓".
  - Việc chặn thật nằm ở backend/CSDL.

## 5. Đối chiếu §7 handoff ↔ mã/test (tất cả NOT_RUN)

| §7 | Yêu cầu | Mã | Test đã viết |
|----|---------|----|--------------|
| 1 | Validation | `chuan_hoa`, `kiem_pdf_ky`, `_than` | `ChuanHoa`, `KiemPdf` (pure); HTTP k02, k04, k05 (NGAY_SAI, PDF_LA_BAN_XUAT); async K1 |
| 2 | 409 khi căn cứ cũ hoặc không PDF_DAT | `crm_ky_ket` CAS, `crm_hd_ky_kiem` | `M23Tinh` (thứ tự mệnh đề); ServiceMock; HTTP k03 (XUAT_CU, XUAT_CHUA_DAT nhánh không Word), k05 (REVISION_CU); async K5 |
| 3 | Đúng một bản ký có snapshot lineage | `crm_hd_ky`, `G3_LECH` | ServiceMock (lineage/ghim lệch); `GuardCsdlThat` (G3_LECH); HTTP k05 |
| 4 | Idempotency | `crm_ky_tra`, khóa | ServiceMock replay; HTTP k05 (cùng khóa, khóa mới + cùng PDF, khóa cùng body khác → IDEMPOTENCY_KHAC); async K2/K3 |
| 5 | Bất biến sau ký; publish muộn → DA_CU | guard trigger, `_KY_XG` | `PrefixVaPhamVi` (`_KY_XG` khác đúng 1 dòng); `GuardCsdlThat` (CRM_KY_TRANG_THAI); HTTP k06 (luu/xuat 409, owner UPDATE/DELETE bị chặn) |
| 6 | G5 chỉ PENDING/NOT_SELECTED | `crm_hd_ky_g5` | `M23Tinh`; `GuardCsdlThat` (G5_SAI); HTTP k05 (NOT_SELECTED); async K6/K7 |
| 7 | Quyền trước replay/metadata/bytes | thứ tự trong `crm_ky_ket`/`crm_ky_tep`/`_ky_ket` | `RouteTinh`, `M23Tinh` (thứ tự); HTTP k02 (403 trước parse), k07 (thu hồi phạm vi → 403 trước biên nhận, 404 tải) |
| 8 | Download: hash/len/MIME/attachment/no-store + audit | `crm_ky_tep`, route tải | ServiceMock download; HTTP k06 (BH/KT, audit +1); async K7 (fence click) |
| 9 | UI controlled-Promise | khối G4 crm_g.js | `crm_ky_ket_async.cjs` K0–K8 |
| 10 | Prefix nguyên; nhãn test | append-only | `PrefixVaPhamVi` (sha prefix, (23, 23), không M0024, sha crm_giao_ket); nhãn ở §6 |

## 6. Tests đã viết — NOT_RUN_CODE_ONLY

| File | Nhãn | Ghi chú |
|------|------|---------|
| `tests/test_crm_ky_ket.py` `PrefixVaPhamVi`, `M23Tinh`, `RouteTinh` | static (đọc chuỗi mã) | Không thay cho chạy SQL thật |
| `tests/test_crm_ky_ket.py` `ChuanHoa`, `KiemPdf` | pure | `KiemPdf` dương skip nếu thiếu pypdfium2; có test fail-closed khi thiếu module |
| `tests/test_crm_ky_ket.py` `ServiceMock` | mock (cursor/CSDL giả) | Không phải PG thật |
| `tests/test_crm_ky_ket.py` `GuardCsdlThat` | actual PG (`KHO_PG_DSN_TEST`, kho thử tạo/xóa riêng) | Skip khi không có DSN |
| `tests/test_crm_ky_ket_http.py` k01–k07 | actual PG + HTTP in-process | Ca dương ký cần Word thật + PDF_DAT thật (`_co_word()`) và pypdfium2. Thiếu thì skip và ghi NOT_RUN. Không giả mạo PDF_DAT bằng owner. |
| `tests/crm_ky_ket_async.cjs` K0–K8 | mock DOM (Node vm), không phải trình duyệt | Chạy: `node tests/crm_ky_ket_async.cjs` |

Owner chỉ được cấp `phan_cong_hanh_dong` (CRM_KY_KET) và `crm_ky_pham_vi` trong kho thử, vì đó là cấu hình quản trị. Owner không bao giờ ghi bản xuất PDF_DAT.

## 7. Phạm vi G5 trong lượt này

Lượt này chỉ có trạng thái khởi tạo trung thực: khai Có → `PENDING` (bắt buộc, chưa thực hiện); khai Không → `NOT_SELECTED`. Ghi nhận Có **không** có nghĩa là đã đối chiếu, đã trích hay đã duyệt. Không có extraction/execution, random sample, engine hay kết quả G5 giả.

## 8. Còn chờ / ngoài lượt

1. **Chức năng chưa làm:**
   - G5 extraction/execution;
   - G6 hiệu lực thật (ngày hiệu lực, phiên bản hợp đồng, lịch thu, công nợ);
   - correction/ký sửa (Q-RETURN).
2. **Chạy Word/PDF G3 thật** cho ca dương k05/k06. Trên máy không có Word, chỉ nhánh 409 `CRM_KY_XUAT_CHUA_DAT` chạy được.
3. **Review cần Root/kiến trúc:** grants và Q-PII (tên người ký khách, mô tả sửa) của M0023.
4. **Chưa chạy gì cả:** GUI trình duyệt thật, migration trên PG, toàn bộ test mới, và một lần chạy độc lập.
5. **Assertion đếm số migration cũ sẽ xung đột với M0023** (không sửa vì ngoài allowlist; Root đánh giá):
   - `tests/test_m4_02b_pure.py:59–60` kỳ vọng phần tử cuối là M0022 và (22, 22);
   - `tests/test_crm_giao_ket.py:122–123` kỳ vọng 21;
   - `tests/test_crm_41_02.py:109–110` kỳ vọng 18;
   - `tests/test_m4_review_compute.py:67,78–83` kỳ vọng 20;
   - các test M2/L11/M0–M5 có cùng kiểu;
   - các test HTTP kiểm `self.version` bằng 20/21/22.
6. **Lưu ý về test:**
   - k03 kiểm `crm_ky_pham_vi` BAT_BIEN sau `can_pdf()`, nên bị skip khi thiếu pypdfium2;
   - k02/k06 chấp nhận một tập mã lỗi (ví dụ `{CRM_GK_DA_KY, CRM_GK_TRANG_THAI}`), vì guard nào bắn trước phụ thuộc đường gọi;
   - mock DOM không chứng minh hành vi GUI thật.
7. **Thay đổi ngoài trọng tâm trong crm_g.py:** chỉnh một dòng chú thích trong `_ky_ket` ("quyền + phạm vi TRƯỚC khi parse bytes PDF"). Không đổi logic G2/G3.
8. **Task M4_02B_FIX02A_UI_CODE_ONLY trước đó dừng dở do đổi ưu tiên:**
   - `chung_tu.js` U-A đến U-D đã sửa;
   - `tests/m4_02b_async.cjs` còn thiếu U8–U11;
   - `docs/BAO-CAO-M4-02B.md` còn là stub.

---

## Mốc 3 — 2026-10-22 — crm-ui U2 File-only + fixture native33 + chẩn đoán K10/K11 (CODE_ONLY, baseline 2a4b1bf55d3f)

**Trạng thái: NOT_RUN_CODE_ONLY.** Worker crm-ui không chạy Node, Python, SQL, GUI hay Word. Không có PASS nào từ mốc 1, mốc 2, CRMasync12 hay native33 được chuyển thành PASS cho mốc này. Chưa nghiệm thu GUI, CRM, G3 hay PDF.

### Đầu vào từ Root (actual, worker chỉ đọc lại)

- Snapshot tĩnh cbcb9e/a4474b: `change` của ô PDF bản ký (khoảng dòng 1227) không tăng `genForm`. Vì vậy ACK hợp lệ cũ (khoảng dòng 1331) vẫn qua `ht()` và xóa File vừa chọn, khi vai, PN, dự án, hợp đồng và tab đều giữ nguyên.
- native33 (563fda, receipt `58bf39a526005371ca4bbf407cae8907b582b40516a02ce7e38f25b7d10f98de`, trace 6750aa): 33 test, PASS32 FAIL1 ERROR0 SKIP0. Test lỗi là `ServiceMock.test_digest_khong_gom_khoa_va_doi_than_doi_digest`.
- CRMasync12 (output 48eedb/312a0b): chỉ in K0–K9 (10 nhóm). Tiến trình Node con hết thời gian ở 45 s, không có K10, K11 hay dòng kết thúc. Cleanup và hash đạt. Kết quả là **NOT_VERIFIED**, không phải PASS.

### Thay đổi

1. **`src/kho_tri_thuc/giao_dien/assets/crm_g.js`**: sửa đúng một listener trong `veKyDialog`, dùng cơ chế sẵn có.
   - Cũ: `fi.addEventListener("change", () => { kyTep = …; ve(); })`
   - Mới: `fi.addEventListener("change", () => { kyTep = …; genForm += 1; ve(); })`, kèm một dòng chú thích.
   - Hệ quả: đổi File trở thành một hiển thị mới. `ht()` của lần gửi gốc và của lần gửi lại đều chụp `gf0`, nên ACK hoặc lỗi cũ chỉ nhả đúng bản ghi `y`, không toast, không đóng dialog, không xóa File/nháp, không GET làm mới.
   - Không đổi: ý định `kyYD` (File, header, khóa gốc), `ackKy`, ngày/người/Có-Không, chặn ý định mới khi UNKNOWN, ABA vai/tab, `genVao`/hash route, `taiBanKy`, G1/G2/G3. Không thêm queue, framework, API hay schema.
2. **`tests/crm_ky_ket_async.cjs`**: thêm nhóm **K12** sau K11. K0–K11 không bị sửa: không đổi assertion, timer hay thứ tự.
   - **K12a:** POST gốc (F1) còn bay → **chỉ** đổi File sang F2 (ngày `2026-10-22`, Không) → ACK hợp lệ của POST gốc về. Phải im lặng: không toast, không ghi trạng thái "Đã ký", dialog còn, vẫn "Đã chọn: F2", ngày và Có/Không còn, nút gửi còn bật, số GET danh sách/bản soạn/điều kiện không đổi. Đối chứng: ý định F2 gửi khóa mới, đúng File F2; ACK của chính nó thì hiển thị.
   - **K12b:** POST gốc mất kết nối (UNKNOWN) → "Gửi lại bản ký y nguyên" gửi đúng F1 và đúng header/khóa gốc → khi lần gửi lại còn bay, **chỉ** đổi File → ACK hợp lệ cũ. Kiểm cùng các điều im lặng như K12a, cộng với nút gửi lại không còn. Đối chứng: ý định F2 dùng khóa khác khóa gốc.
   - Với mã trước khi sửa, K12a và K12b phải hỏng ở assertion toast (ACK cũ đi vào nhánh FINAL hiển thị). Điều này là suy luận tĩnh, chưa chạy.
3. **`tests/test_crm_ky_ket.py`**: chỉ sửa chỗ lấy dữ liệu trong `test_digest_khong_gom_khoa_va_doi_than_doi_digest`.
   - Production gọi `crm_ky_tra(%s, %s::uuid, %s)` với `(khoa, soan_id, h)`, tức digest nằm ở `[2]`. Test cũ đọc `[1]`, là UUID bản soạn.
   - Nay test lấy `params[2]` và kiểm: có đúng 3 lời gọi, mỗi lời gọi có 3 tham số, `params[1] == SO`, digest là chuỗi hex 64 ký tự.
   - Giữ nguyên `assertEqual(hs[0], hs[1])` (khác khóa, cùng thân), `assertNotEqual(hs[0], hs[2])` (đổi ngày ký) và kịch bản đổi ngày `2026-10-19`.
   - Không sửa `k2/crm_ky_ket.py`. Không đụng assertion tài chính hay nghiệp vụ nào khác.

### Tests đã viết — NOT_RUN_CODE_ONLY

| Test | Loại | Root chạy |
|---|---|---|
| `tests/crm_ky_ket_async.cjs` K12a, K12b (mới) | mock DOM (Node vm), không phải trình duyệt | `node tests/crm_ky_ket_async.cjs` |
| `tests/test_crm_ky_ket.py::ServiceMock::test_digest_khong_gom_khoa_va_doi_than_doi_digest` (sửa chỗ lấy dữ liệu) | mock service, không phải PG | lệnh unittest của Root |

### Chẩn đoán K10/K11: OPEN, chưa xác định nguyên nhân, harness không sửa

- **Đã đọc tĩnh K10 và không thấy await nào treo vĩnh viễn.** Mọi `await` trong K10 là `chay()` hoặc helper chỉ gồm `chay()`/`cho()`. `cho()` thiếu yêu cầu thì `assert` ném lỗi, và `main().catch` sẽ in lỗi rồi thoát mã 1, chứ không treo. Promise POST/GET do ca điều khiển và không được `await` trực tiếp. Mock `phanHoi` có `json()`/`blob()` async nên luôn settle. Vì vậy không có await nhân quả hay mock nào chưa settle được xác nhận, và harness K0–K11 được giữ nguyên.
- **Giả thuyết H1 (mạnh nhất, CHƯA đo): tổng thời gian timer trên Windows.**
  - `chay()` gồm 12 lần `setTimeout(0)`. Theo đếm tĩnh, K0–K9 gọi khoảng 196 lần `chay()` (khoảng 2.350 timer), K10 khoảng 67 lần (khoảng 800 timer).
  - Nếu độ phân giải timer của tiến trình Node trên Windows khoảng 15,6 ms, K0–K9 mất khoảng 37 s và K10 thêm khoảng 12 s. Như vậy timeout 45 s rơi vào giữa K10, khớp với dấu vết "chỉ K0–K9".
  - Root cần đo (ví dụ thời điểm in của từng nhóm, hoặc chạy không giới hạn 45 s) trước khi kết luận.
  - Sửa đúng cho H1 phải đổi timer/nhịp chờ hoặc giới hạn thời gian. Đây là việc ngoài quyền của worker, Root cần quyết định.
  - **Lưu ý:** K12 thêm khoảng 36 lần `chay()`. Nếu H1 đúng, tổng thời gian còn tăng, và K12 cũng sẽ không chạy tới dưới giới hạn 45 s.
- **H2 (CHƯA xác nhận): vòng lặp CPU đồng bộ hoặc vi tác vụ.** Có thể có vòng lặp chặn `setTimeout`, ví dụ trong `ve()`, `tatNhap` (nếu DOM giả tạo chu trình) hoặc app.js `doiVaiTuanTu`/`moChanVaNap` qua bốn lần đổi vai liên tiếp của K10. Đọc tĩnh không tìm thấy vòng lặp như vậy.
- **H3 (phụ):** `reg` của DOM giả giữ mọi phần tử từng có id, nên `getElementById` chậm dần theo số lần vẽ. Khả năng là yếu tố phụ, không đủ để treo.

### Defect UI khác: báo OPEN, không sửa

- Vẫn còn từ mốc 2: `taiTep` của G3 chưa có fence điều hướng (ngoài phạm vi U2).
- `napKy` bỏ qua `ve()` khi `genForm` đổi. Sau mốc 3, nếu người dùng chọn File trong lúc GET điều kiện ký đang chờ, điều kiện mới vẫn được ghi vào `kyCt` nhưng chỉ hiện ở lần vẽ sau. Hành vi này giống mọi ô nhập khác, nên không coi là lỗi mới. Root có thể xét.

### Gate còn OPEN (mốc 3)

- Root chạy actual `node tests/crm_ky_ket_async.cjs` cho K10, K11, K12 và dòng kết thúc, đồng thời đo H1/H2. Hiện kết quả CRMasync vẫn là NOT_VERIFIED.
- Root chạy lại native33 sau khi sửa chỗ lấy dữ liệu (cần receipt mới).
- Chưa làm: PG/migration M0023 thật, HTTP thật với quyền hiện hành, GUI trình duyệt thật, Word G3 PDF_DAT thật cho ca dương, một lần chạy độc lập, và nghiệm thu. Đây đều là việc của Root.
- Không sửa báo cáo M4 và không đụng file M4.
