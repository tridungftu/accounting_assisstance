# Báo cáo M2 XML/ZIP PURE01 — CODE_ONLY

**19/10/2026 — CODE_ONLY / RUNTIME_UNRUN / CHƯA NGHIỆM THU.**

- **Phiên:** cùng session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`.
- **Căn cứ:**
  - `docs/GIAO-CODE-M2-XML-PURE-01.md` (root pin `0934b62c…deaf55`);
  - `docs/M2-XML-PURE-DTO-01.json`;
  - `docs/M2-PROFILE-XML-DEMO-01.md`;
  - fixture `tests/fixtures/m2_invoice_xml/` (manifest pin `43ad2825…2b177`, chỉ đọc).
- **Baseline:** post-stage 238 file `10002247…8bac8e759` do root kiểm.

**Coder chỉ dùng Read/Glob/Grep/Write**:
- Không execute/import/compile/test/SQL/Store/PG/HTTP/GUI/CLI/process/network/Bash.
- Không đọc var/.env/secret/source app/dòng thật.
- Không xóa/move/reset bất kỳ file/DB/role/attempt.
- Không sửa `that.py`/`fixture.py`/`primitives.py`/`kho_10.py`, K2/SQL/server/UI, legacy tests, fixture, expected, manifest.

**Mọi kết quả là UNRUN.** Không suy kiểm tra data corpus của root hay proof M5 thành PASS sản phẩm M2. Nhãn tối đa sau khi root chạy đạt: `M2_XML_PURE_DEMO_VERIFIED`. DB, persistence định danh, ROUTE, API/UI, L11, tài chính và nguồn production vẫn PENDING.

## 1. File mới (đúng 3 target)

| File | Nội dung |
|---|---|
| `src/kho_tri_thuc/nguon/hoa_don_xml.py` | Adapter strict thuần + DTO frozen + 2 entry API. |
| `tests/test_hoa_don_xml.py` | Pure tests trên fixture đã pin, cùng counterexample DEMO tự dựng từ bytes fixture. |
| `docs/BAO-CAO-M2-XML-PURE-01.md` | Báo cáo này. |

Không file nào khác bị sửa. `that.py` không bị import hay gọi; test kiểm SHA `f7330761…ff1fc` nguyên vẹn. Không có blocker cần mở thêm target.

## 2. Interfaces

```
doc_hoa_don_xml(raw: bytes, context: InvoiceReadContext | None = None, *, artifact_name: str | None = None) -> InvoiceReadResult
doc_goi_hoa_don_zip(raw_zip: bytes, contexts: tuple[InvoiceReadContext, ...] = (), *, archive_name: str | None = None) -> InvoiceZipReadResult
ra_json(dto) -> bản sao JSON-compatible mới (Decimal → text exact; trường bytes không đưa vào)
```

### Đầu vào

- Chỉ nhận `bytes`; `bytearray` được snapshot thành bytes.
- `str`, path, `memoryview`, file object → `DataError("INPUT_NOT_BYTES")`.
- Context sai kiểu → `DataError("CONTEXT_FIELD_TYPE")`.
- Lỗi nguồn không làm reader dừng: raw được giữ, kèm issues/candidate.

### DTO (frozen, tuple, snapshot sâu)

`FieldValue`, `InvoiceField`, `InvoiceIssue` (`as_issue()` trả một `fixture.Issue` mới mỗi lần), `XmlRawRef`, `CompanyFact`, `LineCrosswalkFact`, `InvoiceMeasurementFacts`, `InvoiceReadContext` (có `tu_dict`; từ chối key cấm/lạ), `DecimalFact`, `InvoiceLine`, `InvoiceContentEnvelope`, `InvoiceReadResult`, `ZipEntryResult`, `InvoiceZipReadResult`.

Các field ngoài outline:

| DTO | Field thêm |
|---|---|
| `InvoiceField` | `locator`, `mixed_content` |
| `InvoiceLine` | `continuity_ref` |
| `InvoiceReadResult` | `shape`, `artifact_name`, `header_total_section`, `profile_payload_binding` |
| `InvoiceZipReadResult` | `archive_name` |

### Reuse

- `primitives`: `DataError`, `canonical_json`, `sha256`, `date_iso`. Không dùng `normalize_text`, `text_id`, `money_minor`.
- `fixture.Issue`: qua `as_issue()`, import lazy.
- stdlib `ElementTree`/`zipfile`: cùng họ với `that.py`.

## 3. Hành vi chính (theo đầu bài)

### Path

- Exact, không namespace: `HDon/DLHDon/TTChung/{PBan,KHMSHDon,KHHDon,SHDon,NLap,DVTTe}`, `NDHDon/{NBan,NMua}/MST`, `NDHDon/DSHHDVu/HHDVu/{STT,TChat,MHHDVu,THHDVu,DVTinh,SLuong,DGia,ThTien,TSuat}`.
- Không có alias `DChat`, không descendant fallback, không strip namespace.
- Ngoài profile thì không trích:
  - namespace → `UNSUPPORTED_NAMESPACE`;
  - sai path / direct legacy → `UNSUPPORTED_PATH`;
  - phần tử cấu trúc trùng → `STRUCTURE_DUPLICATE`;
  - XML lỗi → `XML_MALFORMED`;
  - DOCTYPE, mã hóa ngoài UTF-8, hoặc quá lớn → `UNSUPPORTED_INPUT`.
- Phần tử/thuộc tính/text lạ (vd `DChat`) và mục `TToan`: giữ bằng chứng kèm issue, không cấp content digest.

### Field state

- Thiếu → `(ABSENT,)`; rỗng → `(EMPTY,"")`; có text → `(TEXT, nguyên văn)`, không trim.
- Trùng: giữ mọi occurrence, kèm issue, không chọn bản nào; content digest NULL.
- Mixed content: không ghép `itertext`, kèm issue.
- `lexeme_basis` = `XML_DECODED_CHARACTER_DATA_NO_TRIM`; `row_raw_sha256` luôn NULL.
- Có entity/CDATA/comment/PI/CR trong bytes → `XML_LITERAL_LEXEME_NOT_PROVEN`, content digest NULL.

### Decimal

- Ngữ pháp `^-?[0-9]+(\.[0-9]+)?$`. Số chữ số đếm theo lexical (loại dấu `-` và `.`).
- Số lượng và đơn giá: tối đa 21 chữ số / 6 thập phân.
  - Vượt → `OVER_DOMAIN`, giá trị NULL, vẫn giữ digits/scale.
  - Sai ngữ pháp, rỗng hoặc thiếu → NULL kèm issue; không bao giờ thành 0.
- Tiền (`ThTien`): exact + `PRECISION_UNDECLARED`; không kiểm tổng/thuế, không quy đổi minor.
- Không dùng float, không round; JSON xuất text bằng `format(Decimal, "f")`.

### Chuẩn hóa số lượng

Chỉ khi đủ cả ba:
- số lượng EXACT;
- `DVTinh` khớp `raw_unit` của fact đo lường;
- fact được hỗ trợ (cùng đơn vị, tỉ lệ 1/1, `EXACT_TEXT_DECIMAL`, ≤21/6, đúng profile document SHA).

Ngược lại normalized NULL kèm `UNIT_*`. Fact không hỗ trợ → `MEASUREMENT_FACTS_UNSUPPORTED`. Proof không làm đổi content hash.

### Tính chất dòng và STT

- `TChat`: 1..4 → GOODS/PROMOTION/DISCOUNT/NOTE; 5 → SPECIAL_GOODS + `SPECIAL_GOODS_HOLD`; còn lại hoặc thiếu/rỗng → UNKNOWN kèm issue. Không mặc định GOODS.
- STT thiếu/rỗng/trùng → issue + `LINE_IDENTITY_UNRESOLVED`. STT không phải khóa logic.

### Định danh `DEMO_M2_ID_DIGITS_V1`

- Mẫu số, ký hiệu, MST: ASCII in được, không rỗng, không trim/casefold.
- Số hóa đơn: chỉ chữ số ASCII; bỏ số 0 đầu bằng thao tác chuỗi; toàn 0 → `"0"`.
- Chiều:
  - Công ty cấu hình là người mua → `MUA_VAO`; là người bán → `BAN_RA`.
  - Cả hai phía → `COMPANY_BOTH_SIDES`; không phía nào → `COMPANY_UNMATCHED`. Cả hai trường hợp: identity NULL, vẫn giữ candidate.
- Tuple `(PN, chiều, mst_ban, mau_so, ky_hieu, so_chuan)` tự dẫn xuất từ native, không nhận tuple làm authority.
- Thiếu ngày hoặc tiền tệ không xóa identity.

### Content `M2_XML_CONTENT_V1`

- Digest = `sha256(canonical_json(envelope))`. Envelope gồm tuple định danh + header states + các dòng có thứ tự kèm `source_ordinal` + `header_total_section` (ABSENT).
- Không đưa vào: delivery, container, actor, thời gian, route, proof, UUID.
- Chỉ tính khi: có identity, không mơ hồ, không có phần ngoài envelope, literal không bị nghi ngờ.
- Raw SHA, container SHA, content digest và profile payload (NULL/NOT_BOUND) là các hash riêng; payload trùng document SHA → `PROFILE_PAYLOAD_CONFUSED`.

### Context

Mâu thuẫn hoặc thiếu ở context đều dẫn tới HOLD (identity/content NULL); native không bao giờ bị ghi đè. Các mã: `RAW_REF_MISMATCH`, `PROFILE_REF_MISMATCH`, `PROFILE_DOCUMENT_MISMATCH`, `IDENTITY_PROFILE_*`, `COMPANY_ABSENT`.

Thiếu context → `CONTEXT_ABSENT`, vẫn giữ toàn bộ fields/lines. Thiếu `expected_raw_ref` chỉ ghi `RAW_REF_NOT_BOUND`, không chặn content.

### Crosswalk

- Chỉ áp khi đủ:
  - content digest đã có;
  - artifact SHA khớp;
  - identity binding bằng đúng tuple tự dẫn xuất;
  - locator và ordinal khớp;
  - mỗi dòng có tối đa 1 fact.
- Sai → issue, không áp. Không ghép theo MaHang/STT.

### ZIP

- Duyệt bằng `infolist()` + `open(ZipInfo)`; mỗi entry có ordinal 1-based, tên, SHA và độ dài thực.
- Tên trùng không bị gộp (`ZIP_DUPLICATE_ENTRY_NAME`).
- Entry đọc lỗi: state `READ_ERROR`, raw NULL. XML hỏng: `CANDIDATE`. Entry không phải `.xml`: `IGNORED_NON_XML`.
- Context chỉ gán khi khớp đúng (container SHA, ordinal, tên); SHA entry được reader so lại.
  - Không khớp → `CONTEXT_UNMATCHED`.
  - Nhiều context cho một entry → `CONTEXT_AMBIGUOUS`.
- Coverage COMPLETE/PARTIAL chỉ nói về chính bundle; `period_completeness` = UNKNOWN; `source_revocation` = NOT_INFERRED.
- ZIP hỏng giữ container bytes.
- Giới hạn DEMO: XML 16 MiB, ZIP 64 MiB, 1000 entry; đọc entry có cap.

## 4. Test đã viết (UNRUN)

Manifest SHA và mọi file được kiểm trước; lệch thì FAIL, không skip.

- **Kiểm `that.py`:** SHA nguyên vẹn; module không import legacy, UUID, giờ hiện tại, env hay I/O.
- **Oracle 8 nhóm / 18 artifact:**
  - G01: golden envelope/digest, raw ref, issues rỗng.
  - G02: `UNSUPPORTED_PATH`.
  - G05: STT ambiguity.
  - G06: 15 dòng quantity (10, 0, phân số, 2^53+1, 21 vs 22 chữ số, 7 thập phân, rỗng/thiếu/không hợp lệ, âm, 0 đầu).
  - G07: thiếu basis, natures 1..5/9/rỗng/thiếu, `DChat`, namespace, sai path, malformed, unit chưa có fact.
  - G08: hai `same.xml` + `broken.xml` → PARTIAL.
- **Overlay 11 observation:** đúng 6 identity / 8 content / raw ref.
  - G01+G03: 4 observation cùng identity và content.
  - G04: bản đệm/không đệm số 0 cùng identity, khác content; PN/chiều tách.
  - G05: đảo thứ tự cho 2 logical / 4 bridge; ambiguity 0 bridge.
- **Counterexample:**
  - Thiếu context; thiếu proof (giữ identity/digest, normalized NULL); fact không hỗ trợ.
  - Công ty lạ / cả hai phía; số hóa đơn sai, toàn 0, chữ số fullwidth.
  - Profile document mismatch; payload trùng document.
  - Raw ref mâu thuẫn, kể cả binding ZIP dùng cho XML rời.
  - Crosswalk sai identity/locator/artifact/trùng dòng; intercompany PN khác.
  - Scalar trùng ở header và dòng; mixed content; entity/CDATA; DOCTYPE; không trim.
  - Context ZIP sai container/ordinal, trùng, sai SHA; ZIP hỏng.
  - Đột biến sâu dict/list sau khi tạo context; frozen; key cấm; ordinal kiểu bool; bộ ba ZIP thiếu.
  - Bản sao JSON mới, không float; `as_issue` trả object mới; kiểu đầu vào sai.

Context ZIP của G08 dựng từ SHA member mà test tự đọc độc lập bằng `zipfile`, không lấy output của product.

## 5. Giới hạn thật

1. **UNRUN.** Chưa chạy lần nào: import, cú pháp, assertion, đối chiếu golden digest/envelope và mọi đường lỗi ZIP. Root chạy riêng sau freeze. Không tuyên bố parity với 75 XML legacy.
2. **Lexeme** là text đã decode (ElementTree), không phải byte span. Chưa có tokenizer; mọi nghi ngờ về literal chỉ dẫn tới chặn digest.
3. **Kiểm tra literal bằng byte rất thô:** có `&`, CDATA, comment, PI hoặc CR ở bất kỳ đâu → chặn digest. Nếu checkout đổi LF→CRLF thì golden test sẽ FAIL. Manifest pin bytes nên đây là tín hiệu phát hiện đúng, không phải lỗi cần nới.
4. **Profile là subset DEMO:**
   - Không kiểm theo full XSD; `PBan` vắng thì vẫn vắng.
   - Field `TTChung`/`NBan` thật ngoài subset (tên, địa chỉ…) sẽ cho UNSUPPORTED_ELEMENT kèm digest NULL; mở rộng phải qua root review profile sau.
5. **Mã issue là nhãn ngữ nghĩa DEMO:** không phải enum sản phẩm có sẵn. Severity ERROR/WARNING theo bảng trong module.
6. **Context chỉ có MỘT công ty.** Đa công ty trong cùng instance cần context theo từng observation (như overlay).
7. **Ngoài phạm vi:** route/actor chỉ là dependency của fixture. Không có seed, DB, API, UI, L11, ghi nhận nghiệp vụ hay engine mới. M9 không bị chạm.

Kết thúc phạm vi PURE01. Root terminal → freeze → full-read → pure tests riêng.
