# Báo cáo M5 — reader thuần nguồn kho #10, sửa 02

**19/10/2026 · tự báo cáo của coder, CHỜ ROOT freeze/review/chạy lại độc lập.** Báo cáo này không phải nghiệm thu. Nhãn tối đa sau khi root xác minh là `M5_READER_PURE_VERIFIED`; toàn bộ M5/L11/core/UI vẫn PENDING.

Căn cứ: `docs/GIAO-SUA-M5-READER-02.md` (SHA `2b415fec…56b0e7eb`) và `docs/REVIEW-M5-READER-01.md` (root pin). Tôi không đọc `var`, nên không đối chiếu được 15 counterexample thực của targeted17. Các test mới dưới đây được dựng lại từ mô tả trong review.

## 1. File thay đổi

- `src/kho_tri_thuc/nguon/kho_10.py`: sửa.
- `tests/test_kho_10.py`: thêm class `D_Repair02`. 40 test cũ giữ nguyên, chỉ thêm test mới.
- `docs/BAO-CAO-M5-READER-02.md`: file mới.

Không sửa báo cáo 01, 43 fixture, DTO, contract hay các file tái dùng. Không thêm file nào khác. Không xóa hay di chuyển file nào. Không chạy git.

## 2. Sáu nhóm đã sửa

| Nhóm | Thay đổi trong reader | Test âm | Positive giữ nguyên |
|---|---|---|---|
| R1 header/status | `REQUIRED_HEADER_TEXT = (SoPhieu, LoaiPhieu, MaKho, TrangThai)` được kiểm bằng `text_id` **trước** mọi lookup/hash. Thiếu khóa → `KHO_SHAPE`; null/object/array/rỗng → `INVALID_TEXT_ID`; khi đó semantic và request đều NULL, candidate và native header vẫn được giữ, không còn crash vì kiểu không hashable. Chỉ lookup `SOURCE_STATE` khi `TrangThai` là text hợp lệ. Text chưa map → `source_state="CHUA_MAP"`, giữ nguyên giá trị quan sát, thêm issue HOLD ở `/phieu/TrangThai`, classifier trả `needs_review=True`. | STATUS_OBJECT/ARRAY/NULL, MISSING_LoaiPhieu/TrangThai, LoaiPhieu rỗng, status chưa map | K01 `DA_DUYET` không có issue; K04 `DA_DAO` |
| R2 graph thập phân hữu hạn | Ở nhánh STRING, `_FINITE_DEC` (`-?\d+(\.\d+)?([eE][+-]?\d+)?`, fullmatch) được kiểm **trước** khi dựng envelope. Không khớp → `KHO_FIELD_TYPE`, semantic và request NULL, giữ nguyên text/kind/locator. | "NaN", "abc", "Infinity", "", " 8", "1,5", "0x10" | "0", "2.5", "-0", "1.50", "1e3", "1E-2" vẫn hash được và giữ text |
| R3 encoding thực | `_facts_mau_thuan` nhận loại token thực: khai báo `EXACT_TEXT_SYNTHETIC_ONLY` mà có dòng NUMBER → `KHO_CONTEXT_PROOF_MISMATCH`, request NULL, và **mọi** dòng có `normalized`/`unit_ref` NULL. Native và semantic vẫn giữ. | Dòng 1 là Number 8, dòng 2 là "2" | K01 vẫn chuẩn hóa; K08 (facts=None) vẫn có request digest đúng observer, không bị gắn PROOF_MISMATCH |
| R4 graph history | Thêm `_kiem_history`. **UNBOUND** khi bất kỳ digest nào được cung cấp (receipt, seen, accepted, raw/master/semantic của content ref) không phải đúng 64 hex. **MISMATCH** khi: id receipt hoặc ref lặp; seen digest lặp; `content_reference_id` có mặt nhưng không resolve được đúng một ref, hoặc semantic digest của ref khác digest của receipt/accepted; ref lệch logical; digest nằm ngoài seen; EXPLICIT_EMPTY mà có dữ liệu. Khi UNKNOWN thì không kết luận replay/fresh/first/ABA. Ref tùy chọn vắng hoặc null thì không tra. | accepted, receipt, raw_null, master_null, semantic NOT_BOUND, duplicate_ref, orphan_ref, ref_logical, duplicate_seen | K03 REPLAY, K04 REVERSED, K05 REAPPEARANCE_HOLD, K09 continuity; replay tối thiểu không có ref tùy chọn; None→MISSING, EXPLICIT_EMPTY→KNOWN |
| R5 capture errors | Field vắng → `()`. Field có mặt nhưng null → `DataError KHO_FIELD_TYPE`, không còn tự đổi null thành `[]`. | null tường minh | Field vắng hoặc `[]` vẫn hợp lệ và có cùng request digest; business ref null vẫn cho candidate + HOLD |
| R6 Digest | Thêm `la_digest` dùng `fullmatch` `[0-9a-f]{64}` cho mọi điểm kiểm digest (context và history). Không strip, không lowercase. | Newline cuối, chữ hoa, khoảng trắng đầu, 63 hoặc 65 ký tự, ở `source_code_sha256` và `master.raw_subtree_sha256`; history digest có newline → UNBOUND, không REPLAY | Digest đúng 64 hex thường; raw SHA của K01 không đổi |

Không thay đổi: token NUMBER nguyên văn, DTO bất biến, classifier thuần không ghi state/capacity, cũng như toàn bộ golden K01–K10 và 19 control.

## 3. Kết quả lệnh

Lệnh: `python -X utf8 -m unittest discover -s tests -p test_kho_10.py`. Đây là lệnh duy nhất đã chạy; tôi chạy nó ba lần.

1. **Baseline trước khi sửa:** 40/40 OK.
2. **Sau khi sửa:** 48 test, 46 PASS, 2 FAIL. Cả hai FAIL nằm ở assertion của chính test mới: khi chỉ thiếu `LoaiPhieu` thì `TrangThai` "Đã duyệt" vẫn là dữ kiện quan sát hợp lệ, nên `source_state=DA_DUYET` là đúng. Tôi sửa assertion trong test, không sửa reader.
3. **Lần cuối:**

```
Ran 48 tests in 0.073s
OK
```

| PASS | FAIL | ERROR | SKIP | UNRUN |
|---:|---:|---:|---:|---:|
| 48 | 0 | 0 | 0 | 0 |

48 = 40 baseline + 8 test mới. Các test mới dùng subTest, tổng cộng khoảng 40 biến thể âm và dương. Kiểm hash cho thấy 43 input không đổi trước và sau khi chạy.

Không chạy PG/SQL/Store/K2/API/UI/HTTP/network/Google/cloud/git. Không đọc `var`, `.env`, source app hay secret.

## 4. Giới hạn và điểm root nên soát

1. Status chưa map dùng mã có sẵn trong DTO là `KHO_FIELD_TYPE` với severity HOLD, vì DTO03 không có mã riêng. Semantic vẫn hash được (giữ dữ kiện quan sát) và không làm graph_ok sai. Nếu root muốn status chưa map làm semantic NULL thì cần chốt lại.
2. Bộ header bắt buộc tôi chọn là SoPhieu/LoaiPhieu/MaKho/TrangThai cộng NgayChungTu (kiểm bằng mã ngày riêng). MaDoiTac, DienGiai, NguoiLap, NguoiDuyet, ThoiDiemDuyet, SoPhieu_Goc vẫn là str|null tùy chọn.
3. Cú pháp graph cho chuỗi số lượng chấp nhận số mũ (`1e3`), nhưng chuẩn hóa exact-text chỉ nhận `-?\d+(\.\d+)?`. Dấu `+` đầu, dạng `.5` và khoảng trắng đều bị coi là graph sai.
4. Mâu thuẫn encoding chỉ được kích hoạt khi có NUMBER thực dưới khai báo exact-text. Dòng `null` dưới exact-text vẫn chỉ là `KHO_MEASUREMENT_NOT_EXACT`/HOLD, không làm request NULL.
5. Vì tôi không có input thật của targeted17, việc root chạy lại suite độc lập là bắt buộc.

Dừng tại đây để root freeze/review. Không mở việc khác.
