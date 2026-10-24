# M9 typed DEMO — proposal DDL, API và workflow

**DRAFT FOR ROOT REVIEW / NOT_IMPLEMENTED / NOT_ACCEPTED — 19/10/2026.** Tài liệu cụ thể hóa gói M9 để giao sau common core/CRM. Chỉ đọc tài liệu, corpus DEMO và header/function kỹ thuật; không import/chạy product/test/SQL, gọi app/Google/network, đọc dữ liệu thật/credential/backup hoặc xóa file. Claude03 handle89659 đang sửa core; tên bảng dưới đây là proposal, phải bind lại DDL/service/quyền cuối đã review trước coding, không patch core đang viết.

Đề xuất: giữ `master.hop_dong/hop_dong_phien_ban`, mở rộng lịch trả nợ hiện có, thêm typed facts còn thiếu của vay; dùng snapshot/raw, K5, đề xuất, link/phân bổ, lô và quyền chung. Không viết engine vay/lãi hoặc phần mềm nguồn thứ hai. Full M9 vẫn gồm ngắn/dài hạn, giải ngân/trả gốc/lãi/phí, lãi dự trả/L7/M10, LC/bảo lãnh và C4d đầu tư; phần thiếu nguồn/policy có việc chờ cụ thể, không bị bỏ khỏi toàn33.

## 1. Căn cứ và source contract được pin

| Căn cứ | Pin / ý nghĩa |
|---|---|
| Gói `GIAO-VIEC-BRIDGE-KHOAN-VAY-M9-33.md` | SHA256 `fb8c5f00834520625217f999b2b45a12246fa958787dca4d2261b04bcaa5f946` |
| Corpus `m9-independent-inputs-20261019-v2` | Manifest `80baa534b9c0e7740d7cebad0c896ccc424a14214bfc59bc1f0972d8157288ee`; kiểm lại 18 hash/byte, 0 mismatch, 19 ca; chưa chạy product |
| `REVIEW-CONTRACT-M9-INPUTS-01.md` | `60b5968fdfeb64c487ac854136d8a265a36ae6d05bdb2b1b15a08b02d401455b` |
| `VAY_DEPLOY_20260922` | `D:/Claude/Phan mem theo doi khoan vay/apps-script-deploy/Code.js`: `593d6ba8efce4a301a3f42ad2b2c2936ed90119ccfdc8375e11fd3a85768d8f4` |
| UI deploy native v6 | `apps-script-deploy/Index.html`: `767f1f17680633564681ba3fdafd1aba4decc7e9406bc696a30dcfab2495e6b7` |
| Profile root khác, không tự nhận | `Code.gs`: `98774668ddf909b328e21e399d938d6740f1db4266e1661df78ec87e665b38db`; lịch gốc không có `maKheUoc`. Root thiếu `Index.html` tương ứng; không coi cùng v6 là cùng schema |
| Đầu tư C4d | `KIEM-KE-NGUON-DAU-TU-M9-33.md`: `48625d8a87a8f039f4dec602fea39fcfac7720c2fc2075639410e9e812c981fa`, historical/incomplete candidate inventory, không phải register/policy đã xác nhận; không đọc lại dữ liệu kiểm kê trong lượt này |

Nguồn nghiệp vụ vẫn chương trình toàn33 M9/C4a–d/C3c, L7/L8/L12; TL29/30/31/32/33/35/37/38/40 đã lọc trong gói. Metadata khảo sát/hash không chứng minh phiên bản đang deploy trên Google. Không đưa quy định pháp lý, tỷ lệ/thời hạn/cutoff hoặc chính sách tài chính mới vào thiết kế.

### 1.1 Header manifest DEMO cụ thể

Đọc đúng `Code.js:37–60`, không đọc seed/row nguồn. `M9_HEADER_SET_ASCII_SORTED_LF_V1`: tên sheet theo thứ tự bên dưới; mỗi dòng `Sheet|header...` với header sort ordinal ASCII, UTF-8 không BOM, LF và LF cuối. SHA256 **`3d4d006a8c0bb459288ced136f204a8b5937d05cbef5aa393e5ee33a37a02967`**, 1.042 byte. Đây chỉ hash tập tên cột; type/precision/schema con còn nằm trong profile có version/hash riêng. Đảo cột vật lý hợp lệ; cột trùng/thiếu không hợp lệ; không dùng physical order làm khóa.

```text
DaiHan|anHan|congTy|duAn|duNoSaoKe|ghiChu|hanMuc|kyHan|maKV|nganHang|ngaySaoKe|nhom|quyUocTinhLai|soHD|tienTe|trangThai|tsdb|updatedAt|updatedBy
HanMucTinDung|congTy|ghiChu|hanMucDuocCap|hieuLucDen|hieuLucTu|id|loaiHanMuc|nganHang|updatedAt|updatedBy
HopDongMua|congTyMua|donGia|duAn|eta|etd|ghiChu|hinhThucVay|id|loaiHD|loaiHang|maHDM|maHDTDLienKet|maHang|nganHang|ngayHD|ngayNhanHang|ngayThanhToan|nhaCungCap|paymentTerm|soHD|soHoaDon|soLuong|soToKhai|tenHang|tienTe|triGia|triGiaNT|tyGia|updatedAt|updatedBy|xuatXu
KheUoc|ghiChu|maKV|maKheUoc|ngayGiaiNgan|soTien|updatedAt|updatedBy
LichLaiSuat|apDungTuNgay|ghiChu|laiSuat|maKheUoc
LichTraGoc|ghiChu|kySo|maKV|maKheUoc|ngayDenHan|soTienGoc
PhatSinh|ghiChu|id|maKV|maKheUoc|ngay|phi|soChungTu|traGoc|traLai|updatedAt|updatedBy
VayNganHan|chiTiet|congTy|ghiChu|id|kyHan|laiSuat|maLienKet|nganHang|ngayDenHan|ngayMoLC|ngayNhanNo|ngayTraNoThucTe|nhaCungCap|quyUocTinhLai|soDaTra|soHoaDon|soLC|soNguyenTe|soNhanNo|soToKhai|soVay|tenHang|tienTe|trangThai|trangThaiHang|tyGia|updatedAt|updatedBy
```

Full native JSON phải có đủ 16 key `version, exportedAt, seqS, seqL, shortLoans, longLoans, kheUoc, lichGoc, laiSuat, phatSinh, hopDongMua, vayNH, hanMuc, rates, bankCfg, manualRows`. Section phụ chỉ giữ raw/whitelist kỹ thuật, không tạo FX/cutoff/policy. `vayNH` native khác `vayNganHan` response load; mỗi transport có profile riêng. Không gọi `load/ensureSheet` vì chưa thuần đọc; vận hành đọc Sheets API readonly whitelist. Không dùng SpreadsheetML `.xls` mất ID/scope làm canonical. Không nhận shape thiếu rồi tự thêm empty sections.

## 2. Quy tắc typed, số và thời điểm dùng chung

- PK mới UUID; bảng promoted có `UNIQUE(phap_nhan_id,id)` (bảng 1:1 PB dùng `UNIQUE(phap_nhan_id,phien_ban_id)`), để FK nghiệp vụ dùng composite key chặn tham chiếu chéo PN ở DB, không chỉ service. `ON DELETE RESTRICT/NO ACTION`; lịch sử không xóa cascade. Source key là text nguyên bản đã normalize theo profile khai báo, không float hoặc số dòng; giữ cả source token/locator raw.
- Mọi bảng promoted có `phap_nhan_id NOT NULL`; snapshot/row chưa map chỉ integration role thấy. Tenant đến từ session/quyền + mapping đã duyệt, không tin actor/entity/approval từ body. Source company đổi mapping PN sau promote phải mở việc tác động, không âm thầm chuyển master/link sang PN khác.
- Money canonical dùng `bigint amount_minor` theo currency/scale đã khai báo, giữ toàn miền int64 của K2, gồm text `9007199254740993`. Scale/currency không có default VND. Amount lớn hơn miền hoặc sai scale → giữ raw/chờ, không clamp. Rate/FX dùng numeric exact và unit/basis rõ; cấm boolean/NaN/Infinity, duplicate JSON key và locale mơ hồ. API/UI/file soát xuất decimal/minor dạng **string**, không qua JS Number.
- Mỗi amount mang `currency_code, currency_scale`; registry currency/scale dùng chung nếu đã có, nếu chưa phải root review phần bổ sung M0 tối thiểu, không dựng registry riêng M9. VND DEMO scale0, USD DEMO scale2 chỉ là fixture contract; không là quyết định hỗ trợ FX vận hành.
- `soVay/soDaTra` của ngắn hạn là VND nguồn; `soNguyenTe/tienTe` là đại lượng riêng. Lưu độc lập `amount_original_minor/currency/scale`, `equivalent_vnd_minor`, `source_fx_rate/source_fx_basis`. Không CHECK VND=NT×rate, không tự recompute nếu profile chưa tuyên bố quan hệ/cơ sở. Không chia tổng đã trả thành lần trả tưởng tượng.
- Provenance của field số: `encoding=EXACT_TEXT|SOURCE_NUMBER`, precision contract ID/version/hash và `precision_status=PROVEN|UNPROVEN|LOST`. Decimal chỉ bảo toàn payload nhận; không phục hồi chữ số đã mất từ Number. Thiếu chứng cứ precision → chờ, không đổi thành 0/duyệt/xuất/học. S10 không được đưa oracle original vào input như bằng chứng.
- Phân biệt **business effective time**, **known_at_server lần đầu**, **recorded_at server**. `received_started_at/finished_at`, `last_seen_at` và `source_updated_at/exportedAt` là metadata riêng. Source timestamp thiếu zone giữ raw + lỗi, không tự UTC. Source backdate/valid date không kéo known_at về quá khứ. S06 nhận 19/10 không eligible tại 30/06 dù rate hiệu lực trước đó; API as-of phải áp cả valid time và knowledge cutoff.
- Mọi content hash canonical gồm typed values + namespace/profile + basis/mapping revision có ý nghĩa; không gồm lần fetch cuối để tạo revision giả. Raw hash vẫn hash bytes gốc. Repeat không thay first-known; mapping/profile đổi cần candidate revision/impact review, không rewrite bản cũ.

## 3. Proposal DDL: phần dùng chung và phần M9

Các tên sau là logical-to-physical proposal. Nếu common core nhận bàn giao đã có bảng/service cùng grain thì bind/reuse đúng cái đó, không tạo bản song song. Nếu chưa có, root review các extension tối thiểu dưới đây trước coding; không xem chúng là schema đã tồn tại. Không dùng JSON làm master/lịch authoritative; JSON được phép cho raw, cấu hình profile và bằng chứng bổ sung.

### 3.1 Snapshot và mapping — extension chung M0/K1

| Bảng proposed | Cột / kiểu chính | FK, unique/check và vai trò |
|---|---|---|
| `giao_tiep.tep_tiep_nhan` — metadata staging M0/integration | `id uuid`, `source_instance_id text`, `object_key text`, `raw_sha256 text`, `byte_length bigint`, `media_type text`, `received_at_server timestamptz`, `access_domain text` | `access_domain=INTEGRATION_ONLY`, size≥0/hash64; unique `(source_instance_id,raw_sha256)`. Object key do immutable file store hiện có cấp, không nhận arbitrary path/URL từ client. **Không FK raw vào `kho.tep_goc`** khi raw chưa map hoặc multi-PN; bảng metadata này không là kho file/engine raw mới |
| `kho.anh_chup_nguon` | `id uuid`, `source_instance_id text`, `profile_code/version text`, `profile_sha256/source_code_sha256/ui_sha256/header_set_sha256 text`, `transport text`, `tep_tiep_nhan_id uuid`, `raw_sha256/typed_sha256 text`, `received_started_at/finished_at timestamptz`, `exported_at_source timestamptz NULL`, `known_at_server timestamptz`, `coverage_kind text`, `coverage_manifest jsonb`, `state text`, `error_code text NULL` | FK original raw→`giao_tiep.tep_tiep_nhan`, cùng source instance/hash; state RECEIVED/VALIDATED/PARTIAL/INCONSISTENT/REJECTED/STAGED, hash64 check, finish≥start. Unique `(source_instance_id,profile_sha256,raw_sha256)` dùng nhận lại; mỗi lần fetch có audit riêng, không thêm snapshot chỉ vì fetch time. Coverage FULL_SHAPE khác SOURCE_SCOPE_COMPLETE. Snapshot không phải bằng chứng mọi row đã được kế toán duyệt |
| `giao_tiep.tep_tach_phap_nhan` — provenance derivative M0 | `id uuid`, `tep_tiep_nhan_id uuid`, `snapshot_id uuid`, `phap_nhan_id uuid`, `tep_goc_id uuid`, `profile_sha256/mapping_revision_sha256/selected_rows_sha256 text`, `transformation_profile text`, `created_at_server timestamptz` | FK original→staging metadata; composite FK `(PN,tep_goc_id)`→tenant artifact, sau review unique PN/id tương ứng. Unique `(tep_tiep_nhan_id,PN,profile_sha256,mapping_revision_sha256,selected_rows_sha256)`. Derivative chỉ chứa row đúng PN và provenance envelope; không trỏ bản raw full dưới tên derivative |
| `kho.ban_ghi_nguon` | `id uuid`, `snapshot_id uuid`, `phap_nhan_id uuid NULL trước map`, `section text`, `source_key text NULL khi lỗi`, `locator text`, `row_raw jsonb`, `row_raw_sha256/typed_sha256 text`, `validation_state/error_code text`, `mapping_revision_id uuid NULL` | FK snapshot; unique `(snapshot_id,section,locator)` chỉ chống lặp locator. **Không** unique source_key làm mất hai row xung đột; cùng key/same payload có thể nhiều evidence nhưng chỉ một logical candidate. Raw/locator chỉ có ý nghĩa trong snapshot. Row lỗi không lọt master/lịch |
| `master.anh_xa_nguon` | `id uuid`, `source_instance_id text`, `source_company_key text`, `kind text`, `source_value text`, `phap_nhan_id uuid`, `doi_tac_id/du_an_id/hop_dong_id uuid NULL`, `revision integer`, `valid_from/to timestamptz`, `known_at_server/recorded_at timestamptz`, `state text`, `can_cu_chung_tu_id uuid` | Kind COMPANY/BANK/PROJECT/LOAN; FK typed tới PN/đối tác/dự án/HĐ. COMPANY `source_value=source_company_key`, target chỉ PN; BANK chỉ đối tác, PROJECT chỉ dự án, LOAN chỉ HĐ, CHECK theo kind. Unique revision `(instance,source_company_key,kind,source_value,revision)` không chứa target PN; COMPANY exclusion approved interval theo instance/company key, BANK/PROJECT/LOAN theo cùng source namespace + kind/value. Không fuzzy tên. State/approval dùng K5/V4–V3 chung, không bảng duyệt mới |

**Root correction RC1:** `kho.tep_goc` hiện có `phap_nhan_id NOT NULL` và `hash UNIQUE` toàn bảng (M0003:196–206). Giữ nguyên hai ràng buộc này; không gán raw chưa map/multi-PN vào PN giả, không nới tenant/NULL và không dùng artifact của PN khác chỉ vì hash trùng. Original bytes lưu bất biến bằng file store hiện có, metadata ở staging integration phía trên; chỉ integration role có quyền theo instance đọc. App/Google account không được truy cập metadata/raw full staging hoặc ghi thẳng bảng này.

Sau mapping đã duyệt, producer dùng **cùng immutable file store** ghi derivative có canonical envelope gồm source instance, target PN UUID, original raw hash, profile hash, mapping revision hash và tập locator/row hashes được chọn, cùng exact raw rows của PN. Envelope có target PN nên hai PN có nội dung row giống nhau vẫn có byte/hash riêng; không thêm fetch time/random ID để tạo derivative giả mới. `kho.tep_goc` chỉ nhận derivative đúng PN, hash của derivative khác original raw hash và được ghi đúng nhãn. Nếu hash đã tồn tại phải kiểm owner PN/bytes, không mượn tenant của row hiện có. Provenance đi `original staging artifact → snapshot/row locator → derivative manifest → kho.tep_goc PN → typed master/evidence`; exact row values/hashes phải truy ngược được original, không coi hash derivative là hash file nguồn.

Actor PN chỉ xem row đã map và derivative/file soát đúng PN; không cấp download full artifact dựa vào việc thấy một row hoặc một `tep_goc_id`. Snapshot list chỉ trả metadata phạm vi PN được phép; row chưa map chỉ integration thấy, không thành PN mặc định. Candidate/master chứng từ dùng FK derivative PN, original staging ID/hash chỉ dùng reference provenance qua service có quyền. Original full bytes vẫn local, không gửi cho AI/Claude. Nếu core sau03 đã có metadata intake/derivative cùng grain thì bind vào đó, không tạo bảng M9 hoặc file store song song.

**Root correction RC4:** COMPANY mapping có source identity `(instance,source_company_key)` độc lập target PN; key dựa mã/token company nguồn được profile pin, không sinh từ target PN, tên fuzzy hoặc thứ tự row. Ngoài unique revision, bắt buộc exclusion/constraint tương đương ngăn **mọi** approved valid interval chồng nhau cho key đó, không đưa target PN vào khóa ngăn overlap. Trong transaction khóa source-company identity trước khi duyệt; hai request duyệt A/B cùng key không được cùng thành công. Nguồn không đủ disambiguation cho token giống nhau → `AMBIGUOUS_COMPANY`, giữ chờ và không derivative/promote, không cho hai approved mapping để lách.

BANK/PROJECT/LOAN mapping được scope bởi source company key đã map + PN, vì cùng mã nguồn ở hai công ty/PN có thể là hai đối tượng độc lập. Corpus S15 giữ nguyên: khác instance hoặc khác source company identity đã chứng minh thì cùng maKV/maKheUoc/soHD vẫn hai namespace, không fuzzy merge. Row con thiếu company resolve qua parent duy nhất trong source namespace; nếu parent key cũng trùng mà không có disambiguation thì chờ, không gán theo quyền PN người đang mở màn hình.

COMPANY đổi target PN sau khi đã promote không tự tạo alias/master mới ở PN mới, không move HĐ/link/lô cũ và không cho hai mapping active. Mở impact/conflict task có old/new mapping revision + alias/master/link đang tham chiếu; block promotion của nguồn liên quan tới khi phương án điều chỉnh/chuyển có căn cứ và thẩm quyền được review. Không tự diễn giải đây là giao dịch chuyển nợ hoặc tạo bút toán giữa hai PN.

Google nhiều range không mặc nhiên là transaction snapshot: lưu time window/coverage và consistency evidence; thiếu range, quyền lỗi/truncated hoặc phát hiện source đổi trong lần lấy → PARTIAL/INCONSISTENT, không promote rồi retire row cũ. DEMO file bytes đầy đủ kiểm shape được; chưa claim tính nhất quán point-in-time của Google thật.

### 3.2 Hợp đồng và revision typed

`master.hop_dong` tiếp tục là logical HĐ. Dùng `loai=VAY`; thêm phân loại tài trợ ở child typed, không ép LC là giải ngân hoặc thêm loại treasury. `soHD/soNhanNo` là nhãn, không thay source identity; số hợp đồng trùng giữa hai instance không tự gộp. Nếu unique hiện tại `(PN,loai,so_hop_dong)` cản hai hồ sơ nguồn độc lập thì **mở conflict mapping**, không thêm hậu tố vào số HĐ để lách constraint. Gộp vào cùng master chỉ bằng mapping được duyệt có căn cứ.

| Bảng proposed | Cột / kiểu | Ràng buộc / nghĩa |
|---|---|---|
| `master.vay_dinh_danh_nguon` | `id uuid`, `phap_nhan_id uuid`, `source_instance_id text`, `source_section text`, `source_company_key text`, `source_key text`, `hop_dong_id uuid`, `first_known_at timestamptz` | Stable unique `(instance,source_section,source_company_key,source_key)` **không** chứa financial kind hoặc target PN; FK `(PN,HĐ)`, mapping company history phải khớp PN. `source_section=DaiHan` dùng maKV, `source_section=VayNganHan` dùng id; section bảo lãnh tương lai chỉ khi profile riêng được duyệt. Một alias chỉ trỏ một master; chuyển target PN sau promote giữ chờ impact, không tạo alias mới |
| `master.vay_phien_ban` | `phien_ban_id uuid PK`, `phap_nhan_id/hop_dong_id uuid`, `source_alias_id uuid`, `snapshot_id/source_row_id uuid`, `source_revision_sha256 text`, `financing_kind text`, `currency_code char(3)`, `currency_scale smallint`, `han_muc_minor bigint NULL`, `du_no_nguon_minor bigint NULL`, `ngay_du_no_nguon date NULL`, `ky_han_nguon text NULL`, `an_han_nguon text NULL`, `quy_uoc_lai_nguon text NULL`, `source_status text NULL`, `precision_contract_id/version text`, `precision_status text`, `known_at_server/recorded_at timestamptz` | FK composite PN/HĐ/PB, source row cùng snapshot/PN, alias đúng master. Kind LONG_TERM/SHORT_TERM/LC/GUARANTEE. Hạn mức không phải giải ngân; dư nợ nguồn là balance assertion ở ngày cụ thể, không thành M1 money/event. NULL giữ NULL, không default số0. Trạng thái phê duyệt/valid interval/current pointer dùng `hop_dong_phien_ban` chung |

Không lấy `hop_dong.trang_thai` default HIEU_LUC làm nguồn đã duyệt: create candidate phải CHO_DUYET qua service/trigger đúng domain; chỉ V3/V4 đủ quyền mới đổi approved/current. Mỗi source meaningful change có PB mới chờ; source row biến mất không tự hủy HĐ/PB. Approval chỉ tạo/update typed master/lịch trong cùng transaction, không sinh BANK/proposal/112.

Mở rộng typed `vay_phien_ban` cho SHORT_TERM/LC được review ngay trong proposal: `so_nhan_no text NULL, so_lc text NULL, ngay_mo_lc date NULL, ngay_nhan_no date NULL, ngay_den_han date NULL, ngay_tra_no_thuc_te date NULL, so_vay_vnd_minor bigint NULL, so_da_tra_vnd_minor bigint NULL, so_nguyen_te_minor bigint NULL, nguyen_te_code char(3) NULL, nguyen_te_scale smallint NULL, source_fx_rate numeric NULL, source_fx_basis text NULL, ma_lien_ket_nguon text NULL`. Cặp original amount/currency/scale phải đủ khi dùng số nguyên tệ; số VND nguồn có đơn vị VND rõ. Tỷ giá nullable, không default1; source status không thay ngày/số thực tế. `chiTiet` giữ raw tới khi pin schema con, không biến thành untyped master.

Tái dùng cơ chế quyền/K5/version/audit; **không gọi parser hoặc validator loại hình doanh thu của `CrmK2` để duyệt vay**. Domain validator M9 chỉ kiểm facts nhập/scope/precision/basis và workflow đã chốt, không tính engine lãi. Common trigger phải biết module/domain và được bind/review sau03.

### 3.3 Khế ước/draw và mốc rate

| Bảng proposed | Cột / kiểu | FK/unique/check |
|---|---|---|
| `master.khe_uoc_vay` | `id uuid`, `phap_nhan_id/hop_dong_id uuid`, `source_alias_id uuid`, `ma_khe_uoc_nguon text`, `first_known_at timestamptz` | Unique `(source_alias_id,ma_khe_uoc_nguon)`; FK PN/HĐ/alias. Parent không đổi âm thầm. Đây identity, không là một khoản tiền M1 |
| `master.khe_uoc_vay_phien_ban` | `id uuid`, `phap_nhan_id uuid`, `khe_uoc_id uuid`, `hop_dong_phien_ban_id uuid`, `source_row_id uuid`, `ngay_giai_ngan_nguon date NULL`, `so_tien_minor bigint NULL`, `currency_code/scale`, `revision_sha256 text`, `precision_status text`, `known_at_server/recorded_at timestamptz` | Unique `(khe_uoc_id,hop_dong_phien_ban_id)`; composite FK bảo đảm draw thuộc đúng HĐ/PN của PB. Currency kế thừa chỉ từ cha đã xác nhận cùng revision; cha thiếu currency → chờ, không VND. Ngày/amount là source disbursement assertion, BANK mới là money |
| `master.lai_suat_vay` | `id uuid`, `phap_nhan_id uuid`, `khe_uoc_phien_ban_id uuid`, `source_row_id uuid`, `ap_dung_tu date`, `lai_suat_pct_nam numeric`, `source_unit text`, `quy_uoc_nguon text NULL`, `precision_status text`, `known_at_server/recorded_at timestamptz`, `revision_sha256 text` | Unique `(draw_revision,ap_dung_tu)` trong approved PB; cùng khóa/different rate giữ raw conflict, không last-row-wins. Source %/năm giữ 6 nghĩa 6%, không 0,06. Numeric finite, không ép rounding/rate band từ policy chưa chốt |

Rate sheet chỉ có `maKheUoc`, không `maKV`: resolve đúng instance/PN và **đúng một parent**. S16 trùng mã draw hai HĐ → `AMBIGUOUS_RATE_PARENT`, không gán theo thứ tự và không promote aggregate có rate chưa xác định. Các mốc rate không phải số lãi đã tính. View lịch sử có thể trình bày interval `[ap_dung_tu,next_ap_dung_tu)` trong cùng version để đọc; mốc cuối là open-as-reported, không bảo đảm tương lai hoặc tự tính accrual. Không sửa mốc cũ khi rate mới đến; PB/revision giữ known-time và FK link cũ.

### 3.4 Mở rộng `master.lich_tra_no` — một nghĩa vụ/một cấu phần

Lịch hiện quan sát có `UNIQUE(phien_ban_id,ky)`, goc/lai default0 và `so_khe_uoc text`; **chưa đủ** cho hai DRAW cùng `kySo`, thiếu lãi/blank và phân bổ gốc/lãi/phí. Proposal mở rộng bảng hiện có, không tạo lịch hoặc stock/loan engine thứ hai:

| Cột mới / điều chỉnh | Kiểu / quy tắc |
|---|---|
| `model_version` | LEGACY/M9_TYPED; legacy giữ nguyên dữ liệu và cách diễn giải cũ, không giả đã migrate đầy đủ |
| `phap_nhan_id`, `hop_dong_id`, `phien_ban_id` | UUID NOT NULL cho M9; composite FK PN/HĐ/PB |
| `nghia_vu_key` | Text ổn định: LONG principal=`alias/LOAN/kySo/GOC` hoặc `alias/DRAW/maKheUoc/kySo/GOC`; scope và kỳ không lấy row number |
| `pham_vi`, `khe_uoc_id` | LOAN/DRAW; CHECK LOAN→draw NULL, DRAW→draw NOT NULL; draw đúng parent HĐ/PN |
| `cau_phan` | GOC/LAI/PHI/KY_QUY/LC_THANH_TOAN/BAO_LANH_PHI/GIAI_TOA; chỉ tạo khi có nguồn cho cấu phần đó; enum kỹ thuật không là policy hạch toán |
| `ky_nguon`, `period_from/to`, `ngay_den_han` | kySo integer>0 nếu principal source có; date kỳ/phạm vi tiền lãi từ bảng đã duyệt; thiếu không tự lấy tháng hiện tại. period_to>period_from nếu cả hai có; không dựng lãi từ rate |
| `amount_minor`, `currency_code`, `currency_scale` | Amount nullable khi chưa đủ căn cứ; khi approved/eligible phải NOT NULL và precision PROVEN; source zero tường minh hợp lệ nhưng không là obligation payable tự động |
| `source_row_id`, `can_cu_chung_tu_id`, `basis_revision_sha256`, `known_at_server/recorded_at` | FK row/bảng lãi hoặc giấy báo; ghi rõ amount kind SOURCE_SCHEDULE/CONFIRMED_ACCOUNTING_RESULT/ESTIMATE. ESTIMATE không đủ tạo accrual/export |
| `thay_cho_id`, `trang_thai` | FK cùng PN/HĐ/logical nghĩa vụ, chuỗi supersession không cycle; giữ HUY/canceled history bằng trạng thái nếu cần, không delete row |

Unique M9 `(phien_ban_id,nghia_vu_key)` và một active obligation cho mỗi logical key trong đúng effective PB. Không cộng LOAN+DRAW cùng coverage: trước approve, service so phạm vi, overlap chưa có quyết định → `CHO_XAC_NHAN_PHAM_VI_LICH`; check này cần khóa aggregate, không chỉ unique key. Không chia lịch LOAN sang các draw.

Hai trường legacy `goc_minor/lai_minor` không cùng làm nguồn authoritative với `amount_minor`: đề xuất giữ nguyên cho `model_version=LEGACY`, M9_TYPED để NULL và dùng duy nhất `cau_phan+amount_minor`; bỏ default0 cho đường M9, compatibility view đọc rõ model_version. Migration không tự diễn giải zero cũ thành missing hoặc tự tách mọi legacy row thành nghĩa vụ mới. Phải root review compatibility callers/constraint/upgrade trước quyết định DDL cuối; tên `ky/ngay/so_khe_uoc` cũ có thể giữ cho compatibility nhưng không dùng làm khóa M9.

`da_tra_minor/trang_thai` là derived read view từ active allocations theo cấu phần/currency; nếu cache dùng trigger transaction và đối chiếu lại. Không lấy `PhatSinh`/`soDaTra` để tăng amount đã khớp khi chưa có BANK link.

### 3.5 Phát sinh nguồn, ngắn hạn/LC/bảo lãnh

| Bảng proposed | Cột / kiểu | Ràng buộc |
|---|---|---|
| `kho.su_kien_vay` | `id uuid`, `phap_nhan_id uuid`, `source_alias_id uuid`, `hop_dong_phien_ban_id/khe_uoc_phien_ban_id uuid NULL`, `source_event_key text`, `revision integer`, `source_row_id uuid`, `loai_su_kien text`, `ngay_nguon date NULL`, `so_chung_tu_nguon text NULL`, `payload_sha256 text`, `supersedes_id uuid NULL`, `known_at_server/recorded_at timestamptz` | Unique `(alias,source_event_key,revision)`; same key+same payload no logical event mới; different payload candidate revision/conflict, không ghi đè đã khớp/xuất. `PhatSinh.id` bắt buộc; không derive từ date/amount/soChungTu |
| `kho.su_kien_vay_phan` | `id uuid`, `phap_nhan_id uuid`, `su_kien_id uuid`, `cau_phan text`, `amount_minor bigint NULL`, `currency_code/scale`, `amount_original_minor/currency_original/scale_original NULL`, `equivalent_vnd_minor bigint NULL`, `source_fx_rate numeric NULL`, `source_fx_basis text NULL`, `precision_status text`, `can_cu_chung_tu_id uuid NULL` | Unique `(su_kien_id,cau_phan)` khi profile mỗi loại một field; FK PN/event/căn cứ. PhatSinh gốc/lãi/phí là ba phần cùng event, không ba BANK. Unknown field NULL, không đổi blank→0. Event không đủ parent/currency giữ staging |

**Root correction RC2:** ngắn hạn/LC dùng cùng source alias `section=VayNganHan` với key `id`; `financing_kind=LC|SHORT_TERM` chỉ thuộc revision, không identity. Khi cùng source instance/company/id từ LC_OPEN sang nhận nợ thì giữ alias/HĐ, tạo candidate PB mới nếu facts đổi; không thêm khoản vay/master vì đổi kind. `soNhanNo/soLC`, ngày mở/nhận nợ/đến hạn/trả thực tế, source status và link HĐ mua lưu typed facts trong `vay_phien_ban` extension cùng nguyên tệ/VND riêng; không parse tự do `chiTiet` khi schema con chưa pin. `soDaTra` chỉ cumulative assertion để so, không tạo events.

LC_OPEN là non-cash fact, có thể chưa có ngày nhận nợ/amount giải ngân. Ký quỹ, phí, nhận nợ/thanh toán LC, giải tỏa, phát hành/phí bảo lãnh phải có source event key + chứng từ và source field contract riêng; không tạo từ `bankCfg.baoLanh/manualRows.lcBl` tổng hoặc LC status. HĐ mua grain dòng hàng giữ evidence/typed source reference `maHDM+id`; group header chỉ link một hợp đồng mua/một tài trợ đã map. Không duplicate nợ/vay/M2 invoice khi nhiều dòng cùng maHDM; root review extension reference typed vào `kho.lien_ket_chung_tu`, không master mua thứ hai.

Nguồn #9 chưa có chi tiết bảo lãnh đủ dùng: DEMO có thể nhận hồ sơ kỹ thuật giả lập đủ field và giữ workflow chờ template; không gọi đó là source Google bảo lãnh đã hỗ trợ. Hạn mức nguồn chỉ metadata tham chiếu, không thành dashboard/covenant/limit engine.

### 3.6 Link/phân bổ chung L8, không tạo tiền lần hai

Tái dùng `kho.lien_ket_chung_tu`: đầu A là BANK/SAO_KE M1 hiện có, đầu B là chứng từ evidence/snapshot M9 của aggregate đúng PN. Cần thêm link type M9 có nghĩa rõ qua check enum chung. Không tạo `m9_payment` hoặc BANK riêng. Do header hiện unique cặp A/B/type và một amount, đề xuất **child chung** `kho.lien_ket_phan_bo` nếu core sau03 chưa có:

```text
id UUID PK; phap_nhan_id UUID NOT NULL;
lien_ket_id UUID NOT NULL; cau_phan TEXT NOT NULL;
lich_tra_no_id UUID NULL; khe_uoc_phien_ban_id UUID NULL;
su_kien_vay_phan_id UUID NULL;  -- evidence source event, không tự là tiền
amount_minor BIGINT NOT NULL; currency_code CHAR(3) NOT NULL;
currency_scale SMALLINT NOT NULL;
trang_thai TEXT NOT NULL; huy_boi/huy_luc/ly_do_huy;
basis_revision_sha256 TEXT NOT NULL; operation_receipt_id UUID;
```

FK `(PN,link)` và `(PN,target)` typed. Repayment GOC/LAI/PHI target một `lich_tra_no_id` đã đủ căn cứ; disbursement target draw revision; LC/ký quỹ/phí chỉ có event evidence mà thiếu nghĩa vụ/template phải ở candidate chưa được approved financial allocation. CHECK kind xác định đúng target, amount>0 và currency/scale trùng BANK + nghĩa vụ; không dùng generic JSON target hay FK đa hình không kiểm được. Mỗi allocation có identity/history; không xóa child khi undo/retry.

Unique active `(link,cau_phan,lich_tra_no_id)` khi target obligation có giá trị, hoặc `(link,cau_phan,khe_uoc_phien_ban_id)` khi target draw; dùng partial index theo target/state đã chốt. Không dùng `NULL` để lách duplicate target. Nhiều source event làm bằng chứng cho cùng phân bổ không tạo nhiều allocation cùng amount; primary evidence FK và các evidence phụ theo cơ chế provenance chung, cần giữ reference/digest để truy ngược từng row.

Khóa idempotency chung `(PN,module,operation,key)` với request canonical hash; cùng key+payload trả receipt cũ kể cả đã hủy, khác payload →409. Nếu core chỉ có text key global, namespace server `M9:<PN>:<operation>:<key>` và giữ payload hash/receipt chung; không tạo cache chỉ in-memory. Check quyền trước replay. Parent link HUY làm child không còn hiệu lực nhưng history còn; link mới phải key mới/theo semantics được review, không resurrect bằng retry cũ.

**Root correction RC3 — một nguồn tính remaining:** với link model CHILD, `parent.so_tien_khop_minor = SUM(amount_minor của child active)` cùng currency/scale; parent là giá trị derived/cache cập nhật và kiểm deferred trong transaction, không nhập/sửa như amount độc lập. Child chưa có hoặc chưa active không chiếm remaining; không cộng parent thêm lần nữa. Link LEGACY_DIRECT hiện có (ví dụ CRM trước common child) chỉ góp parent amount **một lần khi không có child**, không tự diễn giải thành zero vì chưa migrate. Phân loại DIRECT/CHILD tường minh và cấm mixed representation; conversion model phải atomic có kiểm totals/reference, không fallback lúc query.

Common view/service remaining cho **cùng BANK qua mọi module** hợp nhất child active của CHILD links với parent active của DIRECT links, mỗi amount một lần. `BANK_remaining = eligible_bank_amount - SUM(common effective allocation amounts)` và nghĩa vụ remaining tương tự theo target/currency. Không chỉ cộng M9 hoặc chỉ link actor đang nhìn thấy. Constraint/privileged aggregate được review phải kiểm full same-PN BANK budget kể cả module khác, đồng thời không trả row/details module ngoài quyền; không lấy RLS-filtered sum thiếu dòng làm remaining lớn giả. Header total và child sum lệch bị chặn, không sửa header để ép pass. Undo/retry/current revision dùng cùng view và trạng thái hiệu lực này.

**Thứ tự khóa chung proposed để bind core cuối:** resolve các HĐ liên quan trước; khóa **HĐ IDs sorted → BANK IDs sorted → nghĩa vụ/draw IDs sorted**, đúng domain order CRM hiện root đã đọc (HĐ→BANK→đợt). Không khóa BANK trước rồi quay lại HĐ. Sau khóa phải đọc lại routing/revision/remaining; nếu phát hiện thêm HĐ nằm ngoài lock set đã chọn thì rollback/retry từ đầu, không lấy lock ngược thứ tự. Duyệt/annex/link/undo/reprojection có liên quan phải theo cùng helper/protocol đã review ở core cuối; proposal này không thay core đang sửa. Kiểm cross-module CRM↔M9 tranh cùng BANK là gate bắt buộc, không chỉ hai request M9 cùng nghĩa vụ.

Trong lock kiểm expected revision và tổng common allocation không vượt BANK spendable amount hoặc nghĩa vụ; đủ gốc+lãi+phí khi chấp nhận full match. Nhiều bank→một kỳ, một bank→nhiều kỳ/phần đều dùng child này. Tổng checked ở currency riêng, không cộng USD+VND; cần FX bridge chỉ khi có policy/basis được duyệt. Chỉ candidate match nếu reference+ngày+số gần, không auto-confirm từ `soChungTu`.

Lịch/PhatSinh đến sau BANK chỉ thêm evidence/link/phân bổ. Proposal M1 cũ đã duyệt/xuất không ghi đè/tạo112 lần hai; chưa duyệt chỉ tạo proposal revision qua service chung có before/after, không reset state bằng converter. Khoản lãi đã dự trả dùng link tới cùng LAI obligation/accrual proposal để settle, không tạo expense lại khi trả tiền. Gốc341/112 chỉ theo mẫu đã chốt/currency đủ; không hardcode tài khoản chi tiết/FX/phí/LC từ source status.

## 4. API DEMO và workflow trên shell hiện có

Đây là route proposal, chưa endpoint thật. Session/token/cookie/mutation lock và quyền bind lại sau CRM03. JSON request không nhận actor, approval state hoặc known_at_server; PN selector chỉ chọn trong quyền server và mapping, không thay PN của record bằng body.

| Method/route proposed | Input chính | Output / invariant |
|---|---|---|
| `POST /api/m9/snapshots/demo` | Chọn fixture ID allowlist hoặc upload raw+profile+source_instance đã cấu hình; idempotency key | Receipt snapshot/count/error, không trả raw full multi-PN. Decode/validate toàn shape/schema/precision/parent trước promote; raw/log được giữ nếu reject |
| `GET /api/m9/snapshots/{id}` | Session hiện có | Metadata PN-visible, full/partial/error, row errors/locators và diff; không bí mật/row PN khác |
| `POST /api/m9/mappings/confirm` | Mapping candidate ID, expected version, reason | K5/V4–V3 đúng quyền; version mới, không overwrite mapping/source identity cũ |
| `POST /api/m9/snapshots/{id}/stage` | Expected raw/profile/mapping digests | Atomically candidate HĐ/draw/rate/lịch/source event của phạm vi PN đã định. Validation conflict → không promote nửa graph; repeat →0 business delta |
| `POST /api/m9/versions/{id}/check` | Expected content/version | Kế toán kiểm field/parent/precision/scope; receipt có blockers, không tự approved |
| `POST /api/m9/versions/{id}/approve` | Expected version + reason, server actor | CFO mô phỏng đúng V3/V4; typed current đổi cùng transaction, không BANK/112 mới; stale snapshot/diff sau check cần check lại |
| `GET /api/m9/loans` và `/{id}` | PN/as_of/known_cutoff trong quyền | HĐ/versions/draw/rate/lịch/source events, số nguồn/khớp/còn lại; API money strings, scope rõ, không gọi estimated interest là payable |
| `POST /api/m9/matches/preview` | BANK ID + candidate target IDs | Chỉ preview từng thành phần/currency/basis; không mutation money/proposal/lô |
| `POST /api/m9/matches/confirm` | BANK/targets/amount strings, expected versions, key | Common link/allocation transaction; insufficient basis→chờ, conflict/stale→409, quyền→403; không M1 duplicate |
| `POST /api/m9/links/{id}/undo` | Reason/key/expected link version | HUY có actor/time/history, kỳ/lô bảo vệ; không delete/restore hidden row hoặc sửa original BANK |
| `POST /api/m9/proposals/prepare` | Approved obligation IDs + template/policy version ID | Reuse common proposal; thiếu account/FX/capitalization/accrual basis → việc chờ với NULL expected, không xuất giả |
| `POST /api/m9/file-soat` / `GET /api/m9/file-soat/{id}` | Approved/current accessible versions và kỳ | Common lô/file bytes/hash/cell thực, nguyên tệ/exact strings; công thức injection được xử lý; không bật Junsky mức2 |
| `POST /api/m9/sync` | Chọn configured source instance, không URL/credential tùy ý | Đường Google readonly vận hành sau gate quyền, cùng parser/snapshot contract; timeout/retry/thay header không làm mất active data |

HTTP status/error code cụ thể bind quy ước shell sau review, không lấy status200 + chuỗi OK làm pass. No Google role truy cập DB; integration account chỉ staging quyền riêng; external app không ghi master nghiệp vụ. Lỗi parse/profile/source validation phải giữ raw/log nhưng **0 mutation business**, không gọi converter commit rồi kiểm lỗi mới báo false như finding M1-02.

UI: thẻ nguồn → lần lấy/profile/coverage/lỗi → master HĐ/draw/phiên bản → K5 kiểm/duyệt → lịch scope rõ → nối BANK M1 theo gốc/lãi/phí → file soát. Mỗi nút có label, busy/error/retry và bước tiếp tục sau restart; không bắt Anh chạy CLI. Nút mở #9 dùng launcher/link sẵn có chỉ mở nguồn; thay/duyệt ở nguồn khác phê duyệt kế toán, bridge không gọi action ghi/xóa. Màn chờ liệt kê thiếu field/policy/source, không tô Xanh vì 0 hoặc empty.

## 5. RLS, audit, version/period và migration gate

RLS/trigger phải đặt trên tất cả typed child/snapshot row/mapping/allocation, không chỉ HĐ header. `USING/WITH CHECK` cùng PN được module M9 cho phép, actor ID+login khớp session, state mô phỏng đúng. Link BANK còn cần quyền M1/PN; nguồn có quyền đọc không có quyền CFO. App login thật NOSUPERUSER/NOBYPASSRLS; admin migration/projection không là đường dùng của user. Helper SECURITY DEFINER nếu buộc cần phải schema-qualified, search_path cố định, kiểm actor/PN/module và revoke PUBLIC EXECUTE; không lấy helper CRM đang sửa là mẫu đã an toàn.

Mọi approve/reject/check/mapping/change/match/undo/export ghi `nhat_ky.su_kien` chung với actor/server-time/PN/type/before-after digest/subject/basis revision/operation key. Không sửa audit cũ hoặc log secret/full raw. Approved/current rows và referenced line/obligation IDs immutable; thay thế bằng revision/correction có lý do. Kỳ khóa/lô đã xuất/đã đối chiếu chặn update/undo/projection vượt phạm vi; không disable trigger để chạy M9 bridge. Link đến phiên bản cũ vẫn giữ khi lịch mới được duyệt; việc điều chỉnh riêng, không tự mở lại phần đã trả/xuất.

Migration sau review: kiểm source/common core hash cuối, mới DB + upgrade DB có dữ liệu, idempotent checksum. Backfill chỉ cột kỹ thuật có căn cứ; legacy schedule không đủ scope/amount meaning → flag cần review, không lấy default0 làm số đã xác nhận. Kiểm FK composite, unique hiện hành, nullable amount, source hash, role thật/RLS hai PN và rollback atomic. Giữ mọi file/DB/role, không DROP/reset để làm ca đạt. Không chốt số migration khi CRM/M12 đang viết.

## 6. L7/lãi dự trả/M10 và LC/đầu tư: giữ đủ scope, không bịa policy

| Phần | Neutral DEMO làm được sau review | Gate thật / không suy |
|---|---|---|
| Lịch gốc/rate | Nhận typed version/source scope; đọc interval; đối chiếu BANK/PhatSinh | Lịch LOAN+DRAW overlap cần quyết định phạm vi; không tự cộng/cắt chia |
| Lãi kỳ/dự trả | Nhận bảng/giấy báo đã xác nhận amount+period+draw+provenance thành LAI obligation; common proposal/M10 đọc lịch này | exportLai current balance/last rate không là oracle. Thiếu bảng/cutoff/actual rate/day basis/rounding → NULL/chờ, không tính engine mới |
| L7 vốn hóa | Link LAI obligation tới project; DEMO có policy fixture/version rõ mới kiểm proposal/partition | Production capitalization eligibility/time/rate/allocation/TK chưa chốt thì giữ việc chờ, không mặc định 0%/100% hoặc tự chuyển635/241 |
| Ngoại tệ | Giữ source original và VND equivalent độc lập, exactness/UI/file | FX ghi sổ/đánh giá/settlement cần policy/basis; orgl_rate không default1 để ép xuất, không dùng dashboard rate |
| LC/ngắn hạn | Nhận hồ sơ có ID, ngày/trạng thái/đại lượng riêng; LC_OPEN non-cash; nối từng BANK/event có căn cứ | Template LC/ký quỹ/phí/nhận nợ/giải tỏa chưa chốt thì không proposal đủ điều kiện xuất; chiTiet cần schema con |
| Bảo lãnh | Profile hồ sơ DEMO có identity/version/evidence, flow chờ/mapping/link | #9 tổng dashboard không thay hồ sơ chi tiết; cần nguồn phát hành/phí/ký quỹ/giải tỏa và mẫu CFO; không covenant/limit monitoring |
| C4d đầu tư | Giữ inventory candidate và danh sách hồ sơ còn cần; dùng chung source snapshot/master/version/evidence/BANK-link pattern khi loại/mẫu được xác nhận | Current register/loại thực có/hồ sơ/policy chưa xác nhận. Không tạo bảng đầu tư rỗng gọi done, không suy sổ prefix/open item là phát sinh đầu tư, không tự thêm securities/derivative/valuation. Lãi đã M1 nối cùng sự kiện |

M10 consumption key là logical obligation + accounting event kind + kỳ + approved basis version có kiểm supersession, không đơn thuần source snapshot ID. Cùng kỳ import/retry không tạo lô lần2; revision mới sau đã xuất mở correction task, không đổi basis key để lách chống trùng. Lãi accrual rồi thanh toán: cùng LAI obligation được settle, expense recognition chỉ một lần theo policy có căn cứ.

## 7. Requirement → table/API → corpus → evidence cần chạy

| Requirement | Proposal/reuse | Corpus/control độc lập | Expected/evidence |
|---|---|---|---|
| Full shape/profile/header | Snapshot + profile parser | S01/S14/S19, header đảo/trùng/thiếu | Chỉ pinned profile nhận; partial không promote/retire; native16key đủ không tự đủ coverage |
| Hai draw cùng kỳ | Draw revision + mở rộng lịch trả nợ | S01 | 1 HĐ/2 draw/2 GOC obligation 12m+8m scope phân biệt, chờ duyệt, 0 tiền |
| Repeat/revision/duplicate | Source alias + PB + event revision | S02/S03/S04 | Repeat0 business; same PS ID same payload1logical; conflict giữ cả raw/chờ |
| Scope và parent | Composite FK + aggregate check | S05/S15/S16 | LOAN/DRAW overlap chờ, namespace PN riêng, rate ambiguous không gán theo row order |
| Time/rate | Rate facts + known/valid clock | S06/S13 | 2 mốc giữ lịch sử; known19/10 không eligible30/06; estimated accrual=NULL |
| Amount/currency precision | Exact strings + per-field precision contract | S07/S08/S09/S10/S11 | Hai đại lượng NT/VND giữ; rate đổi không tự sửa tiền; exact text lớn đúng; Number uncertainty không hồi phục; xls mất key bị chặn |
| LC non-cash | Typed financial kind/source events | S12/S18 + LC fee/deposit DEMO bổ sung | LC mở không giải ngân; tổng bảo lãnh không phát sinh; thiếu template chờ đúng |
| LC→nhận nợ giữ identity | Stable section/company/source-id alias; financial kind ở PB | Control bổ sung thiết kế RC2, chưa sửa corpus: hai snapshot cùng `VayNganHan.id`, LC_OPEN rồi SHORT_TERM | Một alias/HĐ, PB mới chờ nếu facts đổi; transition tự nó 0 BANK/112; retry transition0 business delta |
| L8 hai thứ tự/phân bổ | Common BANK/link/allocation | S17 + BANK before/after, partial/multiple/concurrent/undo | 12m gốc+800k lãi+50k phí=12.85m theo fixture; 1BANK/không thêm112; zero/skip/cùng lỗi không pass |
| Common remaining/lock order | CHILD sum + DIRECT compatibility, HĐ→BANK→nghĩa vụ | Control bổ sung RC3: M9/CRM cùng BANK, tổng vượt ngân sách; parent/child mismatch; reverse-order race | Tổng cross-module chỉ tính mỗi allocation một lần; không overallocate/deadlock giả thành pass, expected atomic winner/loser; header mismatch reject |
| Company ambiguity/retarget | Unique source-company interval không chứa PN; alias stable | S15 và control bổ sung RC4: cùng company key approvedA/B, mapping đổiPN sau promote | S15 hai namespace thật độc lập; token không đủ phân biệt giữ chờ; không approved haiPN hoặc âm thầm thêm master khi retarget |
| L7/M10 | Approved amount obligation + policy/proposal/lô chung | Policy thiếu và policy DEMO/version cụ thể | Không policy→NULL/chờ; đủ fixture→đúng expected; accrual+payment không expense đôi; kỳ/lô chống lặp |
| Quyền/atomicity/upgrade/UI | K5/session/RLS/audit/transaction/shell | Role thật hai PN, stale race, failure, period/export/restart | Denial có positive control; source reject0 business mutation; giữ row IDs protected; workbook bytes/cell thực và GUI bấm được |

Corpus 19 ca là nền đầu vào, chưa phủ hết concurrency/Google/RLS/UI/migration/policy. Sau common core nhận bàn giao phải bind final API/schema/role rồi bổ sung runner/expected độc lập, giữ zero-row/skip/setup error khác business result. Không chạy product trong lượt thiết kế này.

## 8. Đề xuất thứ tự review/giao và quyết định còn thiếu

1. Root review grain snapshot/alias/draw/rate và phương án mở rộng `lich_tra_no` M9_TYPED; chốt bind source snapshot/mapping/currency registry/common allocation hiện có sau CRM03/M12. Chưa thông qua thì giữ proposal, không tự migrate.
2. Giao M9-01 DEMO C4a: source profile+snapshot+typed candidate/master/rate/lịch+K5+quyền/UI+corpus; không cần chờ Google credential để viết/test DEMO. Tiêu chí trên không chỉ có schema, phải đủ workflow và failure controls.
3. M9-02 L8/common allocation qua M1 thật; dùng kết quả gate M1/atomicity đã sửa để không tái dùng đường commit-rồi-báo-lỗi. Giữ proposal/dòng/lô/period/link đã quyết, kiểm hai thứ tự và concurrency.
4. M9-03 LC/ngắn hạn/bảo lãnh, L7/lãi dự trả/M10: neutral receive/evidence/workflow làm được; policy/template/source sub-schema thiếu giữ task/gap cụ thể. Không hỏi lại cấu trúc #9 đã đọc; chỉ gom quyết định nghiệp vụ thật/nguồn không tự lấy được.
5. C4d theo inventory historical/incomplete: xác nhận loại/current register/hồ sơ và mẫu trước coding từng nhánh; phần này vẫn là việc toàn33. Google vận hành gate riêng: xác nhận spreadsheet/deploy/profile thực, tài khoản readonly/quyền/coverage/retry/schemachange/UI; không thay bằng CSV tay.

## 9. Root review corrections — revision 2

Baseline trước root review SHA256 `c5bd5a67d445469e2cd0a02690f331d2674dd568c4ed10f8f168fbb06203cf40`, root đã giữ tại `var/codex-dieu-phoi/m9-design-before-root-review-20261019-073655-232`; lượt chỉnh lý không đọc/sửa/xóa backup đó.

- RC1 thay FK raw→tenant artifact bằng metadata staging integration M0 + derivative PN có provenance, reuse immutable file store; giữ NOT NULL PN và global UNIQUE hash của `kho.tep_goc`.
- RC2 identity dựa section/company/source-id ổn định; LC/SHORT chỉ là revision. Thêm expected chuyển LC→nhận nợ, không thay corpus baseline hoặc tự tạo runner.
- RC3 parent derived=sum child và common remaining toàn BANK qua mọi module, DIRECT/CHILD không cộng đôi; chốt order HĐ sorted→BANK sorted→nghĩa vụ để bind core sau89659; thêm cross-module race/mismatch controls.
- RC4 một approved COMPANY target theo source identity/valid interval, thiếu disambiguation chờ; retargetPN không tự tạo alias/master. S15 source codes trùng ở hai namespace/company thật vẫn độc lập.

**Trạng thái cuối:** revision2 vẫn DRAFT/NOT_IMPLEMENTED/NOT_ACCEPTED, cần root review trước coding. Không product/test/SQL/migration/acceptance mới, không sửa baseline corpus hoặc policy nghiệp vụ. Không chốt vốn hóa, actual rate/cutoff/FX/LC/bảo lãnh hoặc loại đầu tư production từ tài liệu này.
