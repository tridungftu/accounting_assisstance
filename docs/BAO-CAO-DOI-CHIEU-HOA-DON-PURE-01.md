# BÁO CÁO ĐỐI CHIẾU HÓA ĐƠN — PURE01 (CODE_ONLY)

**Căn cứ:** `docs/GIAO-CODE-DOI-CHIEU-HOA-DON-PURE-01.md`.

**CODE_ONLY:** chỉ dùng file tools. Không chạy shell/Python/import/test/SQL/process/browser/network. Không đọc var/.env/.git/sourceapps/dữ liệu thật/credentials. Không xóa/di chuyển/đổi tên tệp. App CRM đang mở giữ nguyên, không restart.

**Self-tests: NOT_RUN.** Root chạy kiểm độc lập. Báo cáo này **không** tuyên bố module đối chiếu hay M2/M5 hoàn tất/nghiệm thu.

## 1. Phân biệt trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Code `src/kho_tri_thuc/nguon/doi_chieu_hoa_don.py` | Đã viết (tạo mới) |
| Test `tests/test_doi_chieu_hoa_don.py` | Đã viết, **NOT_RUN** |
| Root kiểm độc lập (chạy test, review, SHA freeze) | Chưa — việc của Root |
| Format import/export M5 thật | **EXTERNAL_BINDING_PENDING** |

## 2. Tệp

| Tệp | Thao tác |
|---|---|
| `src/kho_tri_thuc/nguon/doi_chieu_hoa_don.py` | tạo mới |
| `tests/test_doi_chieu_hoa_don.py` | tạo mới |
| `docs/BAO-CAO-DOI-CHIEU-HOA-DON-PURE-01.md` | tạo mới |

Không sửa tệp hiện có nào: `hoa_don_xml.py`, migrations, CRM/server/UI, M9, guard, fixtures, tài liệu cũ.

## 3. API

### 3.1. DTO nội bộ (frozen)

Đây **không** phải schema nguồn M5 và không phải authority duyệt.

**`DongDoiChieu(tham_chieu_dong, ma_hang, don_vi, so_luong_text, tinh_chat='GOODS', van_de=())`**
- `tham_chieu_dong`: chuỗi không rỗng.
- `ma_hang`, `don_vi`: `str` hoặc `None`. Chuỗi rỗng được nhận và báo riêng.
- `so_luong_text`: chỉ `str` hoặc `None`. `int/float/bool/Decimal` → `DataError DOI_CHIEU_SO_LUONG_KIEU`. Text sai ngữ pháp **được nhận** và báo lý do khi đối chiếu (không crash, không drop).
- `tinh_chat`: một trong `GOODS, PROMOTION, DISCOUNT, NOTE, SPECIAL_GOODS, UNKNOWN` (đúng tập nature của parser M2), khác → `DOI_CHIEU_TINH_CHAT`.
- `van_de`: snapshot thành tuple chuỗi.

**`HoaDonDoiChieu(ma_ban_ghi, tham_chieu_nguon, khoa_hoa_don, dong, van_de=())`**
- `ma_ban_ghi`, `tham_chieu_nguon`: chuỗi không rỗng.
- `khoa_hoa_don`: `None` hoặc đúng 6 chuỗi không rỗng `(PN, chiều, MST bán, mẫu, ký hiệu, số chuẩn)`. Snapshot thành tuple; không normalize, không mặc định, không thay bằng tên/ngày/tiền.
- `dong`: snapshot thành tuple `DongDoiChieu`. `tham_chieu_dong` trùng trong bản ghi → `DOI_CHIEU_REF_DONG_TRUNG`.

### 3.2. `tu_ket_qua_m2(ma_ban_ghi, result: InvoiceReadResult) -> HoaDonDoiChieu`

Hàm này reuse output bộ đọc M2 `nguon/hoa_don_xml.py`, không viết parser hay identity thứ hai:

| DTO | Nguồn trong parser |
|---|---|
| `khoa_hoa_don` | `result.canonical_identity` (None giữ None, không fabricate) |
| `tham_chieu_nguon` | `_prefix(result.raw_ref)` — cùng tiền tố locator issue của parser: `xml:<sha>` hoặc `zip:<container>!<ordinal>:<entry>` |
| `tham_chieu_dong` | `<tham_chieu_nguon>#<InvoiceLine.source_locator>`; locator `…/HHDVu[n]` mang `source_ordinal` |
| `ma_hang` / `don_vi` | `line.field("MHHDVu"/"DVTinh").duy_nhat`, chỉ khi state `TEXT`; absent/empty/trùng/mixed → `None` |
| `so_luong_text` | `line.quantity.exact_text` chỉ khi `quantity.state == "EXACT"`, ngược lại `None` |
| `tinh_chat` | `line.nature` |
| `van_de` dòng | mã `line.issues` |
| `van_de` hóa đơn | mã `result.issues` không thuộc dòng + `result.candidate_reasons` (khử trùng, giữ thứ tự) |

Những gì **không** dùng hoặc **không** làm:
- Không dùng số lượng chuẩn hóa (`normalized_quantity_text`) hay proof L11. THUNG native EXACT vẫn được so với THUNG native.
- Không tạo hay sửa `InvoiceReadContext`.
- Input không phải `InvoiceReadResult` → `DataError`.

### 3.3. `doi_chieu_hoa_don(m2, m5) -> dict`

Input là tuple/list `HoaDonDoiChieu` mỗi phía. `ma_ban_ghi` trùng trong một phía → `DOI_CHIEU_MA_BAN_GHI_TRUNG`, raise trước khi dựng báo cáo; replay không bị tính thành hóa đơn trùng. Cùng ID ở hai phía là hợp lệ.

Output là dict/list/str/int/None **mới** mỗi lần gọi. Hàm kiểm JSON-safe bằng `canonical_json`, cho kết quả xác định và không phụ thuộc thứ tự input:

```
{
  "contract": "DOI_CHIEU_HOA_DON_PURE_V1",
  "delta_basis": "M5_MINUS_M2",
  "tom_tat": {...},                              # §4
  "hoa_don": [                                   # sort theo khóa tuple
    {"khoa": [6 chuỗi], "trang_thai", "ly_do": [...], "trung_phia": [] | ["M2"] | ["M5"] | ["M2","M5"],
     "m2": [ban_ghi...], "m5": [ban_ghi...],       # sort theo ma_ban_ghi; giữ MỌI bản ghi
     "dong": [muc_dong...]}                         # chỉ khi PAIRED
  ],
  "chua_xac_dinh": [                             # khóa None; sort (phía, ma_ban_ghi)
    {"phia": "M2"|"M5", "khoa": null, "trang_thai": "UNRESOLVED_KEY", "ly_do": ["INVOICE_KEY_NULL"], "ban_ghi": {...}}
  ]
}
ban_ghi  = {"ma_ban_ghi", "tham_chieu_nguon", "van_de": [...], "so_dong", "tham_chieu_dong": [sorted]}
muc_dong = {"trang_thai", "ma_hang", "ly_do": [...], "delta": str|null,
            "m2": [dong...], "m5": [dong...]}       # dòng sort theo tham_chieu_dong
dong     = {"tham_chieu_dong", "ma_hang", "don_vi", "so_luong_text" (text gốc), "tinh_chat", "van_de": [...]}
```

**Trạng thái hóa đơn** (mỗi khóa đúng một trạng thái):

| Trạng thái | Điều kiện | `ly_do` |
|---|---|---|
| `PAIRED` | đúng 1 bản ghi mỗi phía → so dòng | `[]` |
| `MISSING_IN_M5` | chỉ M2 có | `ABSENT_M5` |
| `EXCESS_IN_M5` | chỉ M5 có | `ABSENT_M2` |
| `DUPLICATE` | ≥2 `ma_ban_ghi` khác cùng khóa ở ≥1 phía; không so dòng, không chọn đầu/cuối, không gộp | `DUPLICATE_M2`/`DUPLICATE_M5` + `ABSENT_*` nếu một phía vắng + `LINES_NOT_COMPARED` |

Nhiều dòng trên một hóa đơn không phải là trùng hóa đơn. Hàm không suy phiên bản sửa/hủy/điều chỉnh; caller phải tự cấp đúng dataset/scope.

**Trạng thái mục dòng** (chỉ trong khóa `PAIRED`):

- Ghép theo `ma_hang` exact, chỉ khi mã đó duy nhất ở **cả hai** bản ghi.
- Không fuzzy theo tên, không ghép theo STT/ordinal, không gộp nhiều dòng cùng mã.

| Trạng thái | Điều kiện | `ly_do` / `delta` |
|---|---|---|
| `AMBIGUOUS` | mã lặp ở ≥1 phía; giữ mọi ref hai phía | `CODE_REPEATED_M2/M5`, `CODE_ABSENT_M2/M5`; delta null |
| `MISSING_IN_M5` / `EXCESS_IN_M5` | mã duy nhất chỉ ở một phía; bên vắng **không** thành 0 | `CODE_ABSENT_M5` / `CODE_ABSENT_M2`; delta null |
| `UNMATCHED_NO_CODE` | mã `None`/`""`; mỗi dòng một mục | `CODE_MISSING_<phía>` / `CODE_EMPTY_<phía>` |
| `OUT_OF_SCOPE` | một phía là DISCOUNT/NOTE/SPECIAL_GOODS | `NATURE_OUT_OF_SCOPE` (+ lý do khác nếu có) |
| `UNKNOWN` | nature UNKNOWN (`NATURE_UNKNOWN_<phía>`), nature khác nhau (`NATURE_MISMATCH`), đơn vị thiếu/rỗng (`UNIT_MISSING_/UNIT_EMPTY_<phía>`), hoặc số lượng thiếu/rỗng/sai/vượt miền | delta null |
| `UNIT_MISMATCH` | hai đơn vị có giá trị nhưng khác nhau (exact: không trim/casefold/quy đổi) | `UNIT_MISMATCH`; delta null |
| `MATCH` / `DIFFERENCE` | GOODS/PROMOTION cùng nature, cùng đơn vị, số lượng hợp lệ hai phía | delta = M5 − M2; `"0"` → MATCH |

Các lý do về số lượng: `QUANTITY_MISSING`, `QUANTITY_EMPTY`, `QUANTITY_LEXEME_INVALID`, `QUANTITY_DIGITS_EXCEEDED`, `QUANTITY_SCALE_EXCEEDED`, mỗi mã kèm hậu tố `_M2`/`_M5`.

`ly_do` gom đủ lý do theo thứ tự tính chất → đơn vị → số lượng. Trạng thái chọn theo ưu tiên: `OUT_OF_SCOPE` > `UNKNOWN` (tính chất) > `UNKNOWN` (đơn vị thiếu) > `UNIT_MISMATCH` > `UNKNOWN` (số lượng) > `MATCH`/`DIFFERENCE`.

**Quyết định cần Root xác nhận:** GOODS ↔ PROMOTION cùng mã → `UNKNOWN NATURE_MISMATCH`. Đây là fail-closed; handoff không quy định ca này.

**Số lượng:**
- Ngữ pháp và miền reuse từ M2: `_DECIMAL` (`-?[0-9]+(?:\.[0-9]+)?`, chỉ chữ số ASCII), `QUANTITY_MAX_DIGITS = 21`, `QUANTITY_MAX_SCALE = 6`.
- Giá trị dựng bằng `Decimal(text)` (exact, không float).
- Phép trừ chạy trong `Context` riêng: prec 64, bẫy `Inexact`/`Rounded`. Vì vậy kết quả không phụ thuộc context ambient (prec=2, ROUND_FLOOR…).
- Delta được ghi bằng `format(d, "f")` như M2: không exponent, bỏ 0 thừa sau dấu chấm, `0`/`-0` → `"0"`.
- Không tolerance, không quy đổi, không allocation/pool, không cộng tiền hay số lượng khác mã/đơn vị, không thuế/duyệt/ghi sổ.

## 4. Summary counts (`tom_tat`)

| Nhóm | Khóa | Ý nghĩa |
|---|---|---|
| `ban_ghi` | `m2`, `m5` | số bản ghi riêng biệt mỗi phía (gồm khóa None) |
| | `m2_khoa_null`, `m5_khoa_null` | số bản ghi khóa None (nằm trong `chua_xac_dinh`) |
| `khoa_hoa_don` | `tong` | số **khóa** khác None riêng biệt (≠ số bản ghi) |
| | `PAIRED`, `MISSING_IN_M5`, `EXCESS_IN_M5`, `DUPLICATE` | phân hoạch `tong`: cộng lại đúng `tong`, mỗi khóa một trạng thái, không đếm double |
| `khoa_trung_theo_phia` | `M2_ONLY`, `M5_ONLY`, `BOTH` | phân hoạch các khóa `DUPLICATE` |
| `muc_dong` | `tong` + 9 trạng thái dòng | đếm **mục** (một nhóm `AMBIGUOUS` = 1 mục dù nhiều dòng). `AMBIGUOUS` không bao giờ được tính là `MATCH` |
| `dong_nguon` | `m2_da_xet`, `m5_da_xet` | số dòng nguồn thuộc bản ghi của khóa `PAIRED` |
| | `m2_khong_xet`, `m5_khong_xet` | dòng còn lại (khóa thiếu/thừa/trùng/None). `da_xet + khong_xet` = tổng dòng mỗi phía |
| | `m2_trong_nhom_mo_ho`, `m5_trong_nhom_mo_ho` | số dòng nguồn nằm trong các nhóm `AMBIGUOUS` |

Các counts này chỉ phục vụ báo cáo, không phải nghiệm thu M2/M5.

## 5. Reuse cụ thể

- **`ha_tang.primitives`:**
  - `DataError(code, message, locator)` cho mọi lỗi input;
  - `canonical_json` để chốt output JSON-safe.
- **`nguon.hoa_don_xml`:**
  - `InvoiceReadResult`;
  - `_DECIMAL`, `QUANTITY_MAX_DIGITS`, `QUANTITY_MAX_SCALE`;
  - `_prefix` (định dạng tham chiếu nguồn);
  - `InvoiceField.duy_nhat`, `InvoiceLine.field`, `DecimalFact.state/exact_text`, `canonical_identity`, `raw_ref`, `issues`, `candidate_reasons`.

  `_DECIMAL` và `_prefix` là tên private. Module mới chỉ import chúng, không sửa `hoa_don_xml.py`. Nếu Root muốn API công khai thì đó là gói riêng.
- Chỉ dùng stdlib (`dataclasses`, `decimal`), không thêm dependency.

## 6. EXTERNAL_BINDING_PENDING / ngoài phạm vi

- **Format M5 thật:** không có reader/adapter M5. Toàn bộ dữ liệu M5 trong test là DTO synthetic nội bộ, **không** phải format M5. Caller tương lai phải bind format thật, scope và mapping khóa 6 chuỗi (PN/chiều/số chuẩn) **trước** khi dựng DTO.
- **Không có:** DB, API, route, UI, pool, financial engine, link/approval.
- **Không suy:** phiên bản sửa/hủy/điều chỉnh của hóa đơn; trạng thái thuế native.

## 7. Test viết sẵn (NOT_RUN)

`tests/test_doi_chieu_hoa_don.py` dùng expected viết tay, không mock, không DB, không ghi file/process/network/skip.

| Lớp | Ca |
|---|---|
| `Golden` | Toàn bộ output ITEM_A/CAI 10 vs 8 → `-2`; 0/0 MATCH; None/0 UNKNOWN delta null; −2/−1 → `1`; `…123456` vs `…123457` → `0.000001`; cùng các ca dưới ambient prec=2 + ROUND_FLOOR + bẫy Inexact/Rounded (không ra `-0`, context caller không đổi); biên 21 chữ số → `1999999999999999999998` |
| `HoaDon` | Khớp chính xác (nhiều dòng không là trùng); thiếu/thừa hai phía; trùng M2/M5/cả hai/M2 + M5 vắng; 6 trường khóa khác lần lượt (gồm `"01"` ≠ `"1"`); khóa None không ghép; ID/ref trùng → DataError; cùng ID hai phía hợp lệ |
| `Dong` | Mã lặp một/hai phía/lặp + vắng (4+6 không gộp thành 10); mã exact (`item_a` ≠ `ITEM_A`); mã None/rỗng; dòng một phía; đơn vị khác/thiếu/rỗng/khác hoa thường/khoảng trắng; tính chất NOTE/DISCOUNT/SPECIAL_GOODS/UNKNOWN/PROMOTION/mismatch |
| `SoLuong` | None ≠ 0; rỗng; 22 lexeme sai (NaN, Infinity, exponent, dấu phẩy, khoảng trắng, `+`, `.5`, `1.`, fullwidth, Arabic-Indic, `1_000`, …); int/float/NaN float/bool/Decimal → DataError; miền 21/6 và vượt; âm, `-0`, giữ text gốc `10.000` |
| `XacDinh` | Thứ tự ổn định qua 4 hoán vị bản ghi/dòng; input không đổi (so deepcopy); sửa output không ảnh hưởng lần gọi sau; DTO snapshot list/frozen; 14 đầu vào sai; JSON-safe; module không chứa token cấm (I/O, giờ, uuid, env, DB, float, số lượng chuẩn hóa, context ambient) |
| `TichHopM2` | Parser thật, fixture DEMO chỉ-đọc, SHA pin trước dùng: G01 XML → DTO → DIFFERENCE `-2`; G04 `0007` → số chuẩn `7` do parser (M5 `"0007"` không ghép), padded + unpadded = DUPLICATE M2; G03 ZIP hai entry cùng khóa = DUPLICATE với ref `zip:…!1/2:…`, ZIP không context → khóa None unresolved; biến thể G01 trong bộ nhớ: DVTinh/SLuong/MHHDVu trùng → None + mã issue parser, không đoán; THUNG native: `normalized NULL` nhưng exact `1` được report, THUNG/THUNG MATCH, THUNG/CAI 12 UNIT_MISMATCH (không quy đổi) |

**Giả định chưa xác minh bằng runtime** (nếu sai, đó là phát hiện cần báo, không nới assert):
- Fixture G01, G04 và THUNG dùng LF (không có `\r`). Expected `van_de` chính xác của G01 dựa trên test M2 hiện có: `issues == ()` với context đã bind.
- `deepcopy` frozen dataclass hoạt động như mặc định.
- Entry G03 dài 523 byte (theo overlay `trusted-contexts.json`).
