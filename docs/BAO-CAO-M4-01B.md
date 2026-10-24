# Báo cáo M4-01B / B2 / B3 / B5 / B6 — Sửa cổng tiếp nhận, replay, ranh giới tái sử dụng (CODE_ONLY)

**20/10/2026 · Trạng thái: CODE_ONLY hoàn tất phần viết; MỌI self-test NOT_RUN.** Không chạy lệnh, import, AST, test, SQL, HTTP, AI/OCR, browser, launcher hay tool nạp nguồn. Chưa migrate DEMO. Gói B (M4-01B + B2) **chưa nghiệm thu**; M4-01 và toàn M4 **chưa xong**. Không mở GUI gói C (M4-01C).

Căn cứ: [GIAO-CODE-M4-01B](GIAO-CODE-M4-01B-SUA-GATE-VA-BO-SUNG-KIEM.md) (B1–B6), [GIAO-CODE-M4-01B2](GIAO-CODE-M4-01B2-KHEP-SUA-VA-KIEM.md) (sáu sửa), [kế hoạch M4](M4-KE-HOACH-DA-CHOT-20261020.md).

## 1. File đã ghi

| File | Loại | Nội dung |
|---|---|---|
| `src/kho_tri_thuc/m4/sql_m17.py` | mới (B), sửa (B2) | M17 hiện hành `M0017_M4` + danh mục 37 mã/28 mục hồ sơ, danh sách hàm theo nhóm quyền |
| `src/kho_tri_thuc/ha_tang/pg_migrations.py` | sửa | Bản M17 partial cũ đổi tên `_M0017_M4_PARTIAL_M4_01` (giữ nguyên văn để đối chiếu, KHÔNG trong `PG_MIGRATIONS`); `PG_MIGRATIONS[16] = sql_m17.M0017_M4`. Prefix 1–16 không đụng |
| `src/kho_tri_thuc/ha_tang/store.py` | sửa (B2-1) | Chỉ `write_immutable`: giữ staging |
| `src/kho_tri_thuc/m4/nap_ghim.py` | mới (B), sửa (B2-2) | Bộ nạp ghim + xác minh cache |
| `src/kho_tri_thuc/m4/docx_an_toan.py` | mới (B2-4) | Đếm Track Changes theo namespace XML |
| `src/kho_tri_thuc/m4/nguon_review.py` | sửa | Adapter: nạp ghim, `_m()`, guard DOCX, BOQ phân loại có cấu trúc + ô gốc |
| `src/kho_tri_thuc/k2/xay_dung.py` | sửa | Service: hai kết nối, biên nhận trước mọi xử lý, lệnh tin cậy |
| `src/kho_tri_thuc/giao_dien/m4.py` | sửa | Factory máy chủ inject đường tin cậy; bảng mã lỗi; `ghi_nguon` trong trạng thái |
| `tools/nap_nguon_review_m4.py` | sửa | `--kiem` thiếu tệp → mã 1; tham số hóa nguồn/đích/PIN cho test |
| `src/kho_tri_thuc/k2/m4_demo.py` | sửa | Seed báo DU/THIEU/CHUA_SAN_SANG/DA_THU_HOI, không cấp lại |
| `src/kho_tri_thuc/kiem_chung/fixtures_m4.py` | sửa | Thêm `BOQ_TRONG_VA_0`, `BOQ_SO_KHONG_DOC`, `BOQ_TEN_GIA_LOI` |
| `tests/test_m4_01b_tinh.py` | mới | Kiểm tĩnh/thuần + phản ví dụ B2 |
| `tests/test_m4_01b_pg.py` | mới | Kiểm PostgreSQL thật T01–T10 |
| `docs/BAO-CAO-M4-01B.md` | mới | Báo cáo này |

Không sửa: `server.py` (factory chỉ gọi `app._m5_ket_noi_chu` sẵn có, không cần sửa), `m4/__init__.py`, migrations 1–16, CRM/M1/M9/L11, guards, credentials, nguồn app gốc, bytes vendor/reference. Không xóa/move/replace file nào.

## 2. Dependency và factory tin cậy (B1)

- `XayDungK2(conn, thu_muc, *, conn_tin_cay=None, …)`:
  - `conn` là login ứng dụng (thành viên `app_web`, NOSUPERUSER/NOBYPASSRLS). Kết nối này dùng cho đọc qua RLS và lệnh người dùng (SECURITY DEFINER, `GRANT EXECUTE … TO app_web`).
  - `conn_tin_cay` là kết nối **chủ bảng** của máy chủ, chỉ dùng cho bốn bước mà máy chủ đã tự xác minh bytes/kết quả: `ghi_tep`, `ghi_trich_xuat`, `ghi_boq`, `sua_tham_so` (kèm kết quả máy kiểm).
- Factory `giao_dien/m4.py::dich_vu(app)` dùng `app._m5_ket_noi_chu(crm.conn)`. Đây là cùng đường M5/M2 đang dùng: admin DSN cục bộ đã qua validator, `kiem_ket_noi_chu` kiểm đúng đích và đúng chủ bảng. Factory không nhận DSN/đường dẫn/khóa từ request.
  - Không có admin DSN, hoặc kết nối lỗi: `conn_tin_cay=None` và `ly_do_chua_san_sang` ghi lý do (`CHUA_CAU_HINH_ADMIN_DSN` / mã lỗi). Tải tệp, trích, nhập BOQ và sửa tham số trả `M4_CHUA_SAN_SANG_GHI_NGUON` (HTTP 503), **không fallback** sang quyền người dùng thường. Các route đọc vẫn chạy.
  - `GET /api/m4` trả thêm `ghi_nguon: {san_sang, ly_do}`.
- Hàm tin cậy là `LANGUAGE plpgsql` **SECURITY INVOKER** (không DEFINER), mở đầu bằng chốt `master.la_chu_bang('m4.tep')` → `M4_CHI_MAY_CHU_NGUON`. Các hàm này bị REVOKE khỏi PUBLIC và không cấp cho `app_web`. Không cấp vai worker cho `app_web`, nên app không SET ROLE được.
- Danh tính phiên vẫn kiểm trên đường tin cậy: GUC `ktt.nguoi_dung_id`/`ktt.nguoi_dung_dang_nhap`/`ktt.ngay_hieu_luc` của nhân viên, `m4.ai_id()`, `master.m4_duoc(..., 'SOAN')` hiện hành. Đường tin cậy không tự duyệt thay phòng dự án hay CFO.
- Lineage trong CSDL:
  - `m4.tep.object_key = 'm4-raw/' || raw_sha256`.
  - Lần trích gắn FK `(tep_id, du_an_id, raw_sha256)`; `ghi_trich_xuat` từ chối khi hash bytes đã xử lý khác tệp đã nhận (`M4_TRICH_HASH_KHAC`).
  - `ghi_boq` buộc đúng tệp BOQ của dự án với `raw_sha256 = p_raw_sha`.
- Tên tệp:
  - CHECK SQL bỏ `chr(0)`, dùng `[[:cntrl:]]`, chặn `/`, `\`, `.`/`..` và khoảng trắng đầu/cuối.
  - Máy chủ chặn NUL, đường dẫn và ký tự cấm (`kiem_ten`) trước khi ghi bytes.
  - Đuôi tệp, media và chữ ký tệp phải khớp nhau; OOXML được kiểm (`kiem_tep`).

## 3. Biên nhận / replay (B2) và FINAL bất biến (B2-6)

- Thứ tự trong service cho mọi lệnh:
  1. Kiểm cú pháp yêu cầu.
  2. `_tra_lai` gọi `m4.tra_bien_nhan(khoa)`. Hàm này là SECDEF, chỉ đọc biên nhận của chính người dùng, và **kiểm quyền SOAN hiện hành của dự án trong biên nhận** (đã thu hồi → `M4_KHONG_CO_QUYEN_DU_AN`).
  3. Nếu có biên nhận: so `hanh_dong` và `yeu_cau` gốc với yêu cầu hiện tại. Khớp → trả `ket_qua` cũ kèm `lap_lai: true`; khác → `M4_IDEMPOTENCY_KHAC`.
  4. Chỉ khi chưa có biên nhận mới chạy kiểm revision, đọc tệp, parse/AI, tạo thư mục làm việc, rồi gọi lệnh SQL.
- Trong SQL, mỗi lệnh lặp lại `m4._bn_tra` dưới khóa tư vấn `(người, khóa)`, trước khi kiểm revision. Kết quả FINAL do **chính lệnh** chốt bằng `m4._bn_ghi(...)` trong cùng giao dịch.
  - Không còn `m4.ket_thuc`/`m4.bat_dau`; caller không tự chốt JSON được.
  - `_bn_ghi`/`_bn_tra` không cấp cho `app_web`; `bien_nhan` chỉ ghi thêm và chỉ cho đọc.
- Digest `body_sha256 = sha256(hanh_dong ␟ yeu_cau)` lấy từ yêu cầu gốc bất biến, không từ con trỏ nguồn hiện tại.
- Khóa của `yeu_cau` theo từng hành động:

  | Hành động | Khóa của `yeu_cau` |
  |---|---|
  | TAO_HOP_DONG | du_an_id, so_hop_dong, ten |
  | TAI_TEP | du_an_id, vai_tro, ten, media_type, sha256, byte_length |
  | GAN_TEP_HOP_DONG | hop_dong_id, revision, tep_id |
  | TRICH | hop_dong_id, revision |
  | SUA_THAM_SO | hop_dong_id, revision, ma, trang_thai, gia_tri, don_vi, dieu_khoan, trich_dan, ly_do |
  | XAC_NHAN_THAM_SO | hop_dong_id, revision, ly_do |
  | KHAI_PHU_LUC | hop_dong_id, revision, khai |
  | THEM_PHU_LUC | hop_dong_id, revision, so_pl, ngay_ky, ngay_hieu_luc, trang_thai, doi_boq, noi_dung, tep_id |
  | HUY_PHU_LUC | phu_luc_id, revision, ly_do |
  | NHAP_BOQ | hop_dong_id, revision, tep_id, phu_luc_id, sheet, hang_tieu_de, cot |
  | TAO_DOT | hop_dong_id, so_dot, ngay_nghiem_thu |
  | SUA_DOT | dot_id, revision, ngay_nghiem_thu |
  | GAN_TEP_DOT | dot_id, revision, tep_id, muc |
  | NOP | dot_id, revision_ho_so, revision_dot |

- `ket_qua` FINAL theo lệnh:

  | Lệnh | `ket_qua` |
  |---|---|
  | `tao_hop_dong` | `{hop_dong_id}` |
  | `ghi_tep` | `{tep_id, sha256, byte_length, hang_moi}` |
  | `gan_tep_hop_dong`, `khai_phu_luc`, `huy_phu_luc`, `sua_dot`, `gan_tep_dot` | `{revision}` |
  | `ghi_trich_xuat` | `{trich_xuat_id, trang_thai, che_do, ly_do, revision}` |
  | `sua_tham_so` | `{revision, kiem_tra}` |
  | `xac_nhan_tham_so` | `{xac_nhan_id, rev_tham_so}` |
  | `them_phu_luc` | `{phu_luc_id, revision}` |
  | `ghi_boq` | **`{boq_id, so_dong, trang_thai, so_loi_chan, so_phat_hien, loi_chan[], phat_hien[], revision}`** |
  | `tao_dot` | `{dot_id}` |
  | `nop` | `{nop_id, digest}` |

- **B2-6:** mảng `loi_chan`/`phat_hien` đầy đủ của chính lần đọc nằm trong FINAL. `boq_nhap` trả nguyên FINAL, không thêm mảng sau lệnh, nên lần đầu và replay có cùng hình dạng. Replay không đọc lại BOQ hiện tại.
  - Phần Python thêm vào kết quả, giống nhau ở lần đầu và replay: `lap_lai` (chỉ báo replay), `nhanh_sau` (hằng) ở `nop`, `goi_y_muc` (tính lại từ tên tệp) ở `tai_tep` vai HO_SO_DOT.
- Đồng thời: hai kết nối cùng khóa/body được tuần tự hóa bằng khóa tư vấn, nên chỉ có một hàng nghiệp vụ và một biên nhận.
- Raw capture: cùng bytes, cùng dự án, cùng vai trả cùng `tep_id` (`hang_moi=false`), không thêm hàng.

## 4. Kiểm nguồn tái sử dụng (B3/B4, B2-2/B2-4)

- **Nạp ghim** (`nap_ghim.BoNapGhim`):
  - Finder đầu `sys.meta_path` chỉ phục vụ các gói gốc lõi nguồn. Bytes được kiểm SHA trước `compile/exec`; không sys.path, không `.pyc`. Module chưa ghim → `M4_NGUON_REVIEW_CHUA_GHIM`.
  - B2-2: `hop_le(ten, module)` đòi module gắn đúng instance loader (`__spec__.loader` và `__loader__`), đúng tên, dấu ghim bằng PIN của đúng tệp, và `__file__ == spec.origin == review_goc/<rel>`. `sai_cache()` liệt kê mọi cache không hợp lệ.
  - `NR._m(ten)` xác minh lại toàn bộ cache trước **mỗi lần dùng** module. Mọi lời gọi lõi trong adapter đi qua `_m`.
  - Tệp dữ liệu ghim (danh mục 37 mã, checklist) được kiểm lại SHA ngay trước khi dùng (`_tep_ghim`).
  - Đây không phải sandbox chống mã Python độc hại đã chạy trong tiến trình.
- **Track Changes** (B2-4, `m4/docx_an_toan.py`):
  - Phân tích XML thật mọi phần `word/*.xml` (document, header/footer, footnotes, endnotes, comments, numbering, styles…).
  - Thẻ sửa đổi được nhận theo URI namespace (Transitional + Strict): ins, del, moveFrom/To(+Range), rPr/pPr/sectPr/tblPr/tblPrEx/trPr/tcPrChange, tblGridChange, numberingChange, cellIns/Del/Merge, customXml*RangeStart. Vì vậy prefix khác hay xuống dòng sau QName vẫn bị bắt.
  - DOCTYPE/ENTITY, XML hỏng, thiếu `word/document.xml` hoặc không phải ZIP → `M4_DOCX_KHONG_HO_TRO` (không coi là sạch).
  - Không phụ thuộc mã vendor; không Word/LibreOffice, không accept-change, không cleanup.
  - Áp trước mọi entrypoint đọc DOCX: `van_ban_hop_dong`, dùng cho sửa tham số có trích dẫn (`POST /api/m4/tham-so/sua → sua_tham_so → van_ban_hop_dong`). Với `trich_hop_dong`, guard chạy trước khi tạo thư mục làm việc / gọi `read_contract` / `TrichXuat`.
- **Projection** hiệu lực PL/BOQ vẫn chạy trên `sqlite3.connect(':memory:')` rồi `PRAGMA query_only`. Không mo_csdl, không file DB.
- **Tool nạp nguồn:**
  - CreateNew (`open(...,'xb')`). Cùng bytes → bỏ qua; khác bytes/symlink → mã 3, không ghi đè.
  - Reference khác manifest, hoặc manifest khác PIN → mã 2.
  - `--kiem` còn tệp chưa nạp → **mã 1**, liệt kê từng tệp.

## 5. Retention tệp (B3, B2-1)

- `write_immutable`: staging nằm ở `<thư mục đích>/.ktt-staging/.raw-*`. Đây là thư mục con cùng filesystem, nên `os.link` vẫn nguyên tử.
  - Staging **được giữ** khi thành công, lỗi và retry.
  - Đích không bị ghi đè: khác bytes → `ARTIFACT_CHANGED`. Từ chối đích/staging là symlink.
  - Không có `unlink`, không store thứ hai, không cleanup nơi khác.
- **Tác động chung, cần Root rà:** mọi caller của `write_immutable` sẽ có thêm thư mục ẩn `.ktt-staging/` trong thư mục đích. Các caller gồm xuat/shadow/service, intake, CRM `k2-tep`/`crm-xuat`, M5/M2 nguồn, M1 demo, runtime, store, cli, tri_thuc, nghiem_thu. Hợp đồng nghiệp vụ không đổi. Bất kỳ test lịch sử nào liệt kê/so toàn bộ tệp dưới thư mục artifact (vd `rglob('*')` + `is_file()`) sẽ thấy thêm tệp staging. Tôi **chưa sửa** test lịch sử nào, theo đúng ràng buộc.
- M4: bytes gốc ở `m4-k2/m4-raw/<sha>`; bản làm việc content-addressed ở `m4-lam-viec/`; mỗi lần trích có thư mục riêng `m4-trich/<HĐ>/<uuid>`. Tất cả được giữ.

## 6. Phân loại BOQ (B5, B2-3)

- `boq_doc` trả `(rows, loi_chan, phat_hien)`.
- Mỗi lỗi parser nguồn được phân loại bằng **dữ liệu có cấu trúc của chính dòng** (item cùng số dòng) và **so khớp nguyên văn** với thông điệp mà nhánh nguồn sinh cho đúng dòng đó. Không tìm từ khóa tự do, vì tên hạng mục có thể chứa "KL × ĐG" hay "bị trùng".

  | Điều kiện | Loại | Mã |
  |---|---|---|
  | KL hoặc ĐG không phải số | chặn | `BOQ_SO_KHONG_DOC_DUOC` |
  | KL, ĐG, thành tiền đều là số; lệch vượt ngưỡng nguồn; thông điệp đúng mẫu số học của dòng | phát hiện, **không chặn nộp** | `BOQ_SO_HOC_LECH` |
  | Mã trùng, thông điệp đúng mẫu | chặn | `BOQ_MA_TRUNG` |
  | Không khớp | chặn | `BOQ_LOI_KHAC` |
  | Adapter tự thêm: khóa hạng mục trùng | chặn | `BOQ_KHOA_TRUNG` |
  | Adapter tự thêm: không có dòng | chặn | `BOQ_KHONG_CO_DONG` |

  Map sai (thiếu cột bắt buộc, trùng cột, cột không phải chữ) → `M4_BOQ_MAP_SAI`.
- Mỗi mục lỗi có `{ma, dong, sheet, noi_dung, o:[ô]}`.
- Mỗi dòng có `o_goc` `{kl, don_gia, thanh_tien: {tho, kieu: TRONG|SO|CHU|KHONG_MAP, o}}`, đọc lại ô thật bằng openpyxl. Số typed là NULL khi ô TRỐNG, nên **trống khác 0 tường minh**. Thành tiền ghi trong tệp được giữ nguyên.
- Tính toán legacy không đổi.
- `trang_thai = DA_MAP` khi có dòng và không có lỗi chặn (CHECK trong bảng `m4.boq`). Preflight `m4.thieu` chỉ báo `BOQ_CO_LOI` cho lỗi chặn.

## 7. Phạm vi hiện hành và thu hồi (B6, B2-5)

- `m4.quyen_du_an` có thu hồi chỉ ghi thêm:
  - `thu_hoi_luc/boi/ly_do` ghi **một lần** qua `m4.thu_hoi_quyen_du_an(id, boi, ly_do)`. Hàm này chỉ dành cho chủ bảng/quản trị; app thường không cấp/thu hồi được.
  - Trigger cấm DELETE, cấm sửa phạm vi, cấm gỡ dấu thu hồi (`M4_QUYEN_BAT_BIEN`).
  - Cấp lại = hàng mới (unique một phần trên các hàng chưa thu hồi).
- `master.m4_duoc` chỉ tính hàng chưa thu hồi và module M4 hiện hành của PN (`ktt_duoc`). SOAN cần vai `PHU_TRACH` và vai trò `DU_AN`, nên reviewer không xác nhận tham số được.
- Không thêm chính sách owner-only. Reviewer xem theo assignment `REVIEW` (đợt/tệp hồ sơ đợt đã NỘP).
- RLS `bien_nhan_web` thêm `master.m4_duoc(du_an_id,'XEM')`; `tra_bien_nhan` kiểm SOAN hiện hành.
- **B2-5:** `m4.tep_da_nop(uuid)` (SECDEF, dùng trong policy `tep_web`) chỉ trả `true` khi phiên có XEM/REVIEW hiện hành trên đúng dự án của tệp, và dot/dot_tep cùng dự án. UUID ngoài phạm vi hoặc sau thu hồi → `false`. Người xem/review hợp lệ không đổi.
- Seed `m4_demo.khoi_tao`:
  - Không raise khi chưa sẵn sàng (thiếu schema/PN) → `CHUA_SAN_SANG`.
  - Từng actor được báo `DU`, `THIEU` (kèm danh sách thiếu/sai), hoặc `DA_THU_HOI` (assignment đã thu hồi). Toàn bộ là `DU` khi mọi actor đủ, còn lại là `THIEU`.
  - Một lần, chỉ thêm (marker hoặc đã có actor → không thêm). Quyền dự án chỉ chèn khi chưa từng có hàng nào, kể cả hàng đã thu hồi, nên không cấp lại.
  - Chỉ actor `MO_PHONG_*` (assert).

## 8. API/UDF

- Không thêm route HTTP. Route và tham số giữ như M4-01. Các mã lỗi mới được ánh xạ:

  | HTTP | Mã lỗi |
  |---|---|
  | 503 | `M4_CHUA_SAN_SANG_GHI_NGUON`, `M4_NGUON_REVIEW_CHUA_GHIM` |
  | 403 | `M4_CHI_MAY_CHU_NGUON`, `M4_QUYEN_CHI_QUAN_TRI` |
  | 409 | `M4_TRICH_HASH_KHAC`, `M4_CHUA_TRICH`, `M4_DOCX_CON_SUA_DOI`, `M4_TEP_XUNG_DOT`, `M4_QUYEN_BAT_BIEN` |

- UDF M17:

  | Nhóm | Hàm | Quyền |
  |---|---|---|
  | Lệnh | `tao_hop_dong`, `gan_tep_hop_dong`, `xac_nhan_tham_so`, `khai_phu_luc`, `them_phu_luc`, `huy_phu_luc`, `tao_dot`, `sua_dot`, `gan_tep_dot`, `nop` | app_web (DEFINER, tham số đầu `p_khoa`) |
  | Đọc | `thieu`, `digest_tham_so`, `tra_bien_nhan`, `tep_da_nop` | app_web |
  | Tin cậy | `ghi_tep`, `ghi_trich_xuat`, `ghi_boq`, `sua_tham_so`, `thu_hoi_quyen_du_an` | INVOKER, chủ bảng, **không cấp app_web** |
  | Nội bộ | `ai_id`, `_bn_tra`, `_bn_ghi`, `_khoa_dot` | không cấp |

## 9. Ca kiểm đã viết (NOT_RUN)

`tests/test_m4_01b_tinh.py` (không cần PG):

| Lớp | Nội dung |
|---|---|
| Lineage | first17 theo identity, cho phép nối migration; 715.854 byte đầu = SHA `208a0335…de0a` (từ handoff); 37 mã có TC-09, chỉ XAY_DUNG |
| Tĩnh M17 | không `chr(0)`/`ket_thuc`/`bat_dau`; hàm tin cậy không DEFINER, có chốt, không cấp app_web; tra biên nhận trước kiểm revision và `_bn_ghi` trong lệnh; `bien_nhan` RLS theo phạm vi; thu hồi chỉ ghi thêm; `tep_da_nop` theo phạm vi; FINAL BOQ có đủ mảng |
| Tên/media | NUL, `../`, `:`, khoảng trắng, giả media bị chặn; SHA tính từ bytes |
| Bộ nạp ghim | đúng pin nạp được; sai pin/chưa ghim không exec sentinel; trùng tên trong `sys.modules` |
| Cache (B2-2) | dấu ghim sai pin, loader khác, instance khác, origin khác đều không hợp lệ; trùng tên trên sys.path không chạy (cần lõi) |
| Track Changes (B2-4) | prefix khác, xuống dòng sau QName, Strict + pPrChange, header, thẻ `ins` namespace khác không tính, XML hỏng/DOCTYPE/thiếu document; sentinel cấm subprocess/rmtree/startfile/os.system |
| BOQ cấu trúc (B2-3) | tên chứa mẫu số học + KL None vẫn chặn; lệch thật là phát hiện; số khớp nhưng thông điệp giả là chặn; trùng mã; XLSX thật `BOQ_TEN_GIA_LOI` (cần lõi) |
| BOQ XLSX thật (cần lõi) | lệch số học không chặn; ô trống vs 0; chữ trong số chặn; map sai chặn |
| Staging (B2-1) | thành công/retry/lỗi đều giữ; `ban_lam_viec` giữ |
| Tool | `--kiem` thiếu → 1; nạp đủ → 0 và bytes đúng; khác bytes → 3, không ghi đè; PIN/manifest lệch → 2 |
| Seed | ma trận MO_PHONG_, reviewer không PHU_TRACH |

`tests/test_m4_01b_pg.py` (cần `KHO_PG_DSN_TEST`; DB mới `kho_test_m4b_*`, role app tạm, kết nối chủ riêng làm đường tin cậy):

| Ca | Nội dung |
|---|---|
| T01 | migrate ≥17, không có `ket_thuc`; seed DU 8 actor; chạy lại không thêm |
| T02 | thiếu đường tin cậy → chưa sẵn sàng, không có raw; bytes thật → raw giữ; replay (sentinel `write_immutable`); đổi body; cùng bytes khóa khác; tên/media xấu; CHECK CSDL tên điều khiển/đường dẫn trên đường tin cậy |
| T03 | 10 giả mạo bằng app thường **của actor có quyền** đều `InsufficientPrivilege`, 0 delta: ghi_tep, ghi_trich_xuat XONG, ghi_boq, sua_tham_so máy kiểm giả, `_bn_ghi`, INSERT biên nhận/tệp, UPDATE XONG/DA_MAP/kiem_tra; đường tin cậy với actor reviewer bị chặn |
| T04 (cần lõi) | luồng dương đầy đủ tới nộp thật (xem dưới) |
| T05 | hai kết nối cùng khóa → một đợt, một biên nhận, `[False, True]`; treo = fail |
| T06 | DOCX Track Changes qua sửa tham số → `M4_DOCX_CON_SUA_DOI`, không Office/cleanup, không bản làm việc mới, raw giữ, revision không đổi |
| T07 (cần lõi) | BOQ `BOQ_TEN_GIA_LOI` → CO_LOI, có `SO_KHONG_DOC` dòng 2 và phát hiện dòng 4; `o_goc` `abc/CHU/E2`, kl NULL; preflight chặn; nộp → `M4_CHUA_DU_CAN_CU` |
| T08 | khác PN/dự án, KE_TOAN có PHU_TRACH, PN không M4, reviewer (soạn/khai/xác nhận) đều chặn với 0 delta; bit đã nộp: A1/REVIEW `true`, B1/A2 `false`; B1 không tải được tệp, reviewer tải được |
| T09 | thu hồi dự án A2 (ghi thêm) → replay, chi tiết, tệp, biên nhận RLS, `tra_bien_nhan` đều chặn; actor HOAT_DONG, module M4 còn, hàng quyền giữ; gỡ dấu → `M4_QUYEN_BAT_BIEN`; seed báo `DA_THU_HOI`, không cấp lại; thu hồi REVIEW → bit/tệp đã nộp chặn |
| T10 | factory: có admin DSN → có đường tin cậy; không có → `None`, tải tệp 503 code, không raw |

Luồng dương T04 (cần lõi):
1. Tạo HĐ, tải DOCX, gắn tệp, trích XONG (QUY_TAC_KHONG_AI).
2. Trích dẫn sai cho TT-32 → `M4_TRICH_DAN_KHONG_KHOP`.
3. **(B3)** Nhập đủ 37 mã theo oracle thủ công `PHIEU_THAM_SO`/`VANG` (xem §12), không theo `CHUA_CO` của parser, rồi xác nhận.
4. PL: khai, thêm, hủy, khai lại.
5. BOQ có phát hiện → DA_MAP, ô G4 giữ 999.
6. Đợt + hồ sơ bắt buộc → `thieu=[]` → **nộp thật**; snapshot `so_phat_hien=1`.
7. Replay đúng key/body/revision gốc mọi lệnh sau các thay đổi về sau. Sentinel cấm trích/BOQ/văn bản/ghi tệp. Kết quả giống hệt, kể cả mảng BOQ; 0 delta.
8. Đổi body → `M4_IDEMPOTENCY_KHAC`, 0 delta.

**Chưa có:** Local AI thật và fake-AI plumbing (chưa có ca AI giả lập khai báo trong gói này); OCR; HTTP xuyên luồng (gói C).

## 10. Lệnh Root cần chạy (sau terminal/freeze)

1. Nạp lõi nguồn từ reference đã lọc: `python tools/nap_nguon_review_m4.py`, rồi `python tools/nap_nguon_review_m4.py --kiem`. Kỳ vọng mã 0.
2. Kiểm tĩnh: `python -m unittest tests.test_m4_01b_tinh -v`.
3. Kiểm PG (DSN chủ CSDL qua env lúc chạy): `$env:KHO_PG_DSN_TEST = "<DSN chủ>"; python -m unittest tests.test_m4_01b_pg -v`.
4. Hồi quy toàn bộ, gồm các test lịch sử có thể bị ảnh hưởng bởi staging giữ lại (§5): `python tests/run_suite.py` (và `--engine postgres` nếu dùng).
5. Khi đạt: migrate DEMO tới 17, seed CRM DEMO rồi `m4_demo.khoi_tao(admin_conn)` và kiểm `trang_thai == "DU"`.

Mọi ca skip (thiếu DSN, thiếu lõi nguồn, thiếu openpyxl) là NOT_RUN/NOT_VERIFIED, không tính đạt.

## 11. Rủi ro / việc còn mở

- Staging giữ lại làm đổi danh sách tệp trong mọi thư mục artifact (§5). Root cần rà test/consumer lịch sử; tôi chưa sửa test lịch sử.
- Kiểm tra cache theo dấu/loader/origin không chống được mã độc đã chạy trong tiến trình (ngoài phạm vi, đúng handoff).
- T10 giả định `_crm_ket_noi` không tự lấy admin DSN từ tệp cấu hình cục bộ khi env không có. Nếu có nguồn cấu hình khác, ca "không có admin" có thể không tái hiện được; khi đó kết quả là NOT_VERIFIED, không phải đạt.
- Các ca có kỳ vọng phụ thuộc hành vi parser nguồn (dòng nhóm, `XONG` của fixture HĐ) chưa từng chạy, nên có thể lộ lệch khi Root chạy. Không được sửa vendor hay đáp án để làm xanh.
- Gói C (GUI/Cổng/bootstrap/launcher), Review L1–L3/PDF, NT–công nợ, Request và nghiệm thu xuyên suốt vẫn chưa làm.

## 12. M4-01B3 — hai sửa bộ kiểm PG (CODE_ONLY, NOT_RUN)

Căn cứ: [GIAO-CODE-M4-01B3](GIAO-CODE-M4-01B3-SUA-BO-KIEM-PG.md). Chỉ sửa `tests/test_m4_01b_pg.py` và báo cáo này. Không đổi product, fixture, vendor, schema, guard hay test khác.

1. **Nonce không che `unittest.TestCase.run`.** `cls.run` đổi thành `cls.run_id`, và mọi chỗ dùng đều đổi theo: khóa thao tác `K()`, số HĐ `HDXD-01B/DT/TC/BOQ/PV/A2-{run_id}` (gồm replay T09). Phương thức `run` của unittest giữ nguyên; không bypass runner.
2. **Oracle dương T04 theo đúng DOCX nguồn.** Bỏ cách đổi mọi mã `CHUA_CO` thành `KHONG_QUY_DINH`. Thay bằng bảng thủ công lập từ `fixtures_m4.DONG_HOP_DONG` và tên 37 mã danh mục:
   - **21 mã có căn cứ.** Mỗi mã có giá trị, trích dẫn nguyên văn đúng dòng HĐ và Điều khoản (nếu có). Máy kiểm thật phải trả `OK…`:

     | Nhóm | Mã | Căn cứ trong HĐ |
     |---|---|---|
     | Thông tin chung | TC-01…07 | số, ngày ký, gói thầu, dự án, địa điểm, bên A, bên B |
     | | TC-08 | hiệu lực kể từ ngày ký, Điều 6.1 |
     | | TC-09 | tiêu đề "HỢP ĐỒNG THI CÔNG XÂY DỰNG" |
     | Giá | TT-01 | trọn gói, 2.2 |
     | | TT-02 | 1.000.000.000 đồng, 2.1 |
     | | TT-03 | đã bao gồm thuế VAT, 2.1 |
     | | TT-04 | 8%, 2.1 |
     | | TT-05 | giá trị khối lượng hoàn thành được nghiệm thu, 3.2 |
     | Thanh toán | TT-20 | tối đa 90%, 3.2 |
     | | TT-22 | tối đa 30 ngày, 3.3 |
     | Bảo hành | TT-32 | 12 tháng, 4.1 |
     | Tiến độ | TT-50 | 180 ngày, 5.1 |

     Tạm ứng TT-10/11/12 khai **Không áp dụng**, kèm trích dẫn "3.1 Tạm ứng: Không áp dụng." và máy kiểm thật.
   - **16 mã thật sự vắng** khai **Không quy định**, có lý do theo tên mã: TT-21, TT-30, TT-31, TT-33, TT-40…42, TT-51…56, TT-60…62. TT-21 (tỷ lệ giữ lại) **không** suy thành 100%−90%.
   - **Test tự kiểm oracle trước khi chạy:**
     - Có/vắng là partition đúng đủ 37 mã danh mục.
     - Mỗi trích dẫn có thật trong dòng fixture.
     - Mỗi giá trị là chuỗi con của trích dẫn.

     Sau khi nhập, toàn bộ `m4.tham_so` (trạng thái, giá trị, trích dẫn) phải bằng oracle.
   - Mỗi lần nhập là một lệnh `sua_tham_so` có biên nhận riêng, nên đều nằm trong phần replay muộn của T04.
   - Luồng sau đó giữ nguyên: DU_AN thường xác nhận và nộp thật. Không seed XONG/DA_MAP/FINAL, không đổi guard.

Vẫn giữ:
- Đủ mười method T01–T10.
- T05 hai kết nối với Barrier.
- Quyền app thường và đường tin cậy tách riêng.
- Replay đúng key/body/revision gốc và ca đổi body.
- Thu hồi theo dự án hiện hành.
- Tệp được giữ lại.

Suite này kiểm replay **muộn**, sau các thay đổi hợp lệ về sau. Phần kiểm immediate+later cho cả sáu nhóm biên nhận thuộc bộ kiểm độc lập riêng; báo cáo này không nhận phạm vi đó.

**Self-test: NOT_RUN.** Chưa có runtime hay test nào đạt. Rủi ro còn mở: máy kiểm nguồn (`kiem_tra.check`) chưa từng chạy trên các cặp giá trị/trích dẫn này. Nếu Root thấy một mã không ra `OK`, phải xem lại oracle đối chiếu nguồn, không hạ expected. B/M4 chưa nghiệm thu; không chuyển sang gói C hay CRM.

## 13. M4-01B5 — khép lỗi phát hiện khi kiểm thực tế (CODE_ONLY, NOT_RUN)

Căn cứ: [GIAO-CODE-M4-01B5](GIAO-CODE-M4-01B5-KHEP-LOI-KIEM-THUC-TE.md). B5 thay B4; B4 không triển khai riêng. Chỉ sửa ba tệp: `src/kho_tri_thuc/m4/sql_m17.py`, `tests/test_m4_01b_tinh.py` và báo cáo này. Không tạo tệp mới.

### 13.1 Kết quả thực tế Root ghi nhận trước B5 (không phải của Claude)

| Bộ kiểm | Kết quả | Nguyên nhân |
|---|---|---|
| Pure 50 sau B3 | 47 PASS, 3 ERROR, 0 failure, 0 skip | Xem dưới |
| `BoNapGhim.test_dung_pin_nap_duoc` | ERROR | Fixture ghi bằng `write_text`, nên Windows tạo CRLF lệch SHA literal LF. Đây là lỗi của test; `nap_ghim` chặn đúng. |
| Hai ca `GiuStaging` | ERROR | WinError 5 tại `os.link` trong sandbox. Kiểm riêng trên host Windows tạo được hardlink, no-delete guard gốc hoạt động, nguồn và hardlink được giữ. Đó là chẩn đoán riêng, **không** phải bộ test PASS trên host. |
| Native PostgreSQL 10 | Dừng ở `setUpClass`, 0 method nghiệp vụ | Neutral16 dựng thành công; nâng M17 lỗi `InvalidForeignKey` / SQLSTATE 42830 (`REFERENCED_KEYS_NOT_UNIQUE`) trên `master.hop_dong` |
| Independent 8 | Dừng trước các nhóm nghiệp vụ | Cùng lỗi migration M17 |

Mọi lần dựng thất bại đã rollback; DB/role/tệp được giữ. Không ca nào được tính đạt.

### 13.2 Sửa code

- **M17 — khóa đích cho FK hai cột.**
  - `m4.ho_so_hop_dong` có `FOREIGN KEY (phap_nhan_id, hop_dong_id) REFERENCES master.hop_dong (phap_nhan_id, id)`. Neutral COMMON 1–16 không có UNIQUE tương ứng; chỉ nhánh M13 legacy đầy đủ có `hop_dong_pn_id_uq`. `hop_dong_id_du_an_uq (id, du_an_id)` không thay được cho cặp này.
  - Đã thêm `ALTER TABLE master.hop_dong ADD CONSTRAINT hop_dong_m4_pn_id_uq UNIQUE (phap_nhan_id, id)` ngay sau `hop_dong_id_du_an_uq`, trong khối master HĐ của M17. Vị trí này đứng trước `CREATE TABLE m4.tep` và `m4.ho_so_hop_dong` (bảng chứa FK).
  - Tên riêng M4 để không trùng tên legacy.
  - Giữ nguyên:
    - FK hai cột;
    - FK `(hop_dong_id, du_an_id)` và FK `du_an`;
    - discriminator `module_chu` và trigger/policy quyền hiện hành;
    - thứ tự phụ thuộc.
  - Không thay FK bằng `id` đơn.
  - Không đổi `pg_migrations.py`, prefix 1–16 (byte/SHA), registry COMMON, checksum lịch sử, M9 hay seed.
  - FK `du_an (id, phap_nhan_id)` của `m4.quyen_du_an` đứng trước trong M17 và không phải điểm lỗi Root ghi nhận. Tôi không đổi FK này.
- **Pure test — fixture LF.** Helper `BoNapGhim._goi` ghi `__init__.py` và `con.py` bằng `write_bytes(text.encode("utf-8"))`, tức bytes UTF-8/LF xác định.
  - Giữ nguyên:
    - SHA literal mong đợi (`hashlib.sha256(b"GIA_TRI = 1\n")`);
    - ca dương/âm;
    - đủ 50 method và mọi assertion.
  - Không lấy hash tệp vừa ghi làm đáp án. Không skip/catch/suppress. Không monkeypatch `os.link`, quyền, no-delete guard hay loader.
  - Hai ca `GiuStaging` không đổi; Root chạy lại trên host.
- **Không thêm test mô phỏng SQL.** PG 10 và independent 16→17 giữ nguyên định nghĩa để kiểm migration thật.

### 13.3 Trạng thái

- **Self-test của Claude: NOT_RUN** (không lệnh/import/test/SQL).
- Phần code M17 mới chưa qua cổng kiểm. Root cần dựng DB DEMO mới, migrate neutral16 → 17, rồi chạy:
  - `python -m unittest tests.test_m4_01b_tinh -v` trên host;
  - `KHO_PG_DSN_TEST=… python -m unittest tests.test_m4_01b_pg -v`;
  - bộ independent.
- Chưa có kết quả nghiệp vụ PG nào: replay, giả mạo, thu hồi, nộp thật đều **chưa từng chạy tới**.
- Giới hạn cũ vẫn giữ: chưa có Local AI hay ca fake-AI khai báo, chưa OCR, chưa GUI/Cổng (gói C).
- Không gọi nguồn hoàn chỉnh, gói B hay toàn M4 đã PASS/nghiệm thu. Không tự sang gói C hay CRM.

## 14. M4-01B6 — sửa helper kiểm PG (CODE_ONLY, NOT_RUN)

Căn cứ: [GIAO-CODE-M4-01B6](GIAO-CODE-M4-01B6-SUA-HELPER-KIEM-PG.md). Chỉ sửa `tests/test_m4_01b_pg.py` và báo cáo này. Không đổi product, M17/prefix 1–16, pure50, fixture/vendor, store/guard, quyền/master, CRM/M2/M5/L11/M9. Không tạo tệp mới.

### 14.1 Kết quả thực tế Root ghi nhận sau B5 (không phải của Claude)

| Bộ kiểm | Kết quả |
|---|---|
| Pure 50 (host) | **50 PASS**, 0 fail/error/skip |
| Bốn nhóm độc lập | Đạt: retention, cache nguồn, DOCX, BOQ vật lý (Decimal chính xác, giữ ô gốc) |
| PostgreSQL migration | M17 tạo được sau khi thêm `hop_dong_m4_pn_id_uq` |
| Native PG 10 method | **8 PASS, 2 ERROR (TypeError)**, 0 fail/skip |
| PG độc lập | Dừng ở đáp án BOQ gắn nhầm dòng của chính verifier. Đúng theo tệp nguồn: HM_A `2 × 100`, thành tiền ghi `999` ở G2; HM_B `3.5 × 20` = `70` ở G3. Root đang sửa verifier riêng; không đổi tệp nguồn hay product. |

Hai ca ERROR là T04 (luồng đầy đủ + replay muộn) và T05 (đồng thời). Cả hai dừng **trước** khi gọi `tao_hop_dong`, nên chưa có bằng chứng hai ca này đạt.

Các lát pass này không cộng thành nghiệm thu toàn M4.

### 14.2 Nguyên nhân và sửa

- **Nguyên nhân:** `def lam(self, login, ten, **kw)` nhận tên phương thức ở tham số positional `ten`. Lệnh `tao_hop_dong` lại có business keyword `ten=...`, nên Python báo một tham số nhận nhiều giá trị.
- **Sửa:**
  - Tham số của helper đổi thành `ten_lenh`.
  - Các tham chiếu trong helper đổi theo: `getattr(self.svc, ten_lenh)`, thông tin assertion, tuple lưu replay `(login, ten_lenh, kw, r)`.
  - Hai vòng replay/đổi-body của T04 đổi biến lặp thành `ten_lenh` cho nhất quán.
- **Giữ nguyên:**
  - business keyword `ten` gửi service, kể cả `doi["ten"]` ở ca đổi body;
  - mọi call site, body, khóa, revision và nội dung tuple replay;
  - đủ 10 method T01–T10 và mọi assertion;
  - T05 với `Barrier(2)` và hai connection thật;
  - snapshot/replay toàn bộ, oracle thủ công 37 mã và trích dẫn nguồn;
  - kiểm quyền hiện hành.
- Không skip, không catch/suppress TypeError hay lỗi nghiệp vụ, không đổi oracle hay expected.

### 14.3 Trạng thái

- **Self-test của Claude: NOT_RUN.** Không ghi 10/10 PG hay 8 nhóm độc lập đã đạt.
- Root cần freeze rồi chạy lại T04/T05 (hoặc cả bộ PG) trên DB DEMO mới, cùng bộ PG độc lập sau khi Root sửa verifier BOQ.
- Pure50 và bốn nhóm độc lập đã đạt chỉ kế thừa được khi xác nhận product và bộ pure không đổi. Lượt này không sửa chúng.
- Chưa có HTTP/GUI, Local AI/fake-AI khai báo, OCR. Không gọi B hay toàn M4 nghiệm thu. Không tự sang gói C hay CRM.
