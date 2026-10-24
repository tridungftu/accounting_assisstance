# Báo cáo M5 — reader thuần nguồn kho #10, gói 01

**19/10/2026 · tự báo cáo của coder, CHỜ ROOT freeze/hash/review độc lập.** Nhãn tối đa sau khi root xác minh là `M5_READER_PURE_VERIFIED`; toàn M5/L11/intake/API/UI/runtime/production vẫn PENDING. Báo cáo này không phải nghiệm thu.

Căn cứ: `docs/GIAO-CODE-M5-READER-THUC-HIEN-01.md` (SHA `dad1cbe8…1f74e33`), DTO03 `docs/M5-HOP-DONG-DTO-33.json` (SHA `d1b35770…b6f6f73f`), hợp đồng fingerprint `docs/M5-HOP-DONG-FINGERPRINT-VA-HISTORY-33.md`, fixture root `tests/fixtures/kho_10/` (manifest `5d680a1c…`).

## 1. Ba file tạo mới (không sửa file nào khác)

| File | Nội dung |
|---|---|
| `src/kho_tri_thuc/nguon/kho_10.py` | `doc_phieu_kho(content: bytes, context: KhoReadContext) -> KhoReadResult`, `phan_loai_quan_sat(candidate, summary: KhoHistorySummary \| None) -> KhoClassification`, các DTO frozen, `KhoReadContext.tu_dict` / `KhoHistorySummary.tu_dict` |
| `tests/test_kho_10.py` | 40 test: golden K01–K10, controls C01–C19, các control đối kháng, kiểm hash input |
| `docs/BAO-CAO-M5-READER-01.md` | báo cáo này |

Không đụng tới fixture, expected, DTO, contract, các file tái dùng, `__init__`, Store, K2, server, migrations, config, guard, runner hay app nguồn. Không xóa, di chuyển hay dọn dẹp file nào. Không chạy git.

## 2. Tái dùng (import, không sửa)

- `review_xay_dung.doc_json_chinh_xac`: parser JSON strict — chặn khóa lặp, NaN và Infinity. `chuan_hoa_so`: chỉ dùng trong cây fingerprint.
- `ha_tang.primitives`: `DataError`, `canonical_json`, `sha256`, `text_id`, `date_iso`.
- `fixture._unique_object`: chỉ dùng cho lần parse thứ hai, để giữ token số. Ngữ nghĩa của `fixture.Issue` được chép sang `KhoIssue` frozen, có `KhoIssue.tu_issue`.
- Lần parse thứ hai dùng `json` của stdlib với `parse_int`/`parse_float` để nhận đúng chuỗi token gốc. Không thêm dependency.

## 3. Các điểm thực hiện chính

- **Bất biến sâu:** mọi DTO đều là frozen dataclass. `FrozenObject(entries)` và `FrozenArray(items)` mang tag riêng, nên `{}` khác `[]`. Không có tuple nào chứa dict, list hay Issue mutable. Không có cache hay history toàn cục.
- **Constructor tin cậy:** nếu container sai, kiểu sai, có khóa lạ, hoặc `request_digest` khác null thì ném `DataError`. Ref nghiệp vụ thiếu hoặc null được giữ là NULL, kèm issue HOLD; constructor không abort.
- **Raw SHA** tính trên đúng bytes truyền vào. Nếu có BOM hoặc khác khoảng trắng thì raw khác, nhưng semantic vẫn bằng nhau.
- **Semantic `kho10-content/v1`** dựng theo whitelist header và line, giữ nguyên thứ tự dòng. Master chỉ lấy các khóa được tham chiếu, sắp xếp theo khóa. Master tham chiếu bị lặp (kể cả lặp giống hệt) cho `KHO_MASTER_GRAPH_CONFLICT`; thiếu master tham chiếu cho `KHO_MASTER_MISSING`. Lỗi graph, shape hoặc ngày, hoặc thiếu logical identity hay master, đều làm semantic và request NULL.
- **Request `kho10-request/v1`:** NULL khi thiếu ref bắt buộc (profile, scope_ref, scope, mapping, master ref/raw) hoặc khi scope/mapping lệch với logical/header (`KHO_CONTEXT_SCOPE_MISMATCH`), hoặc khi resolved facts mâu thuẫn (`KHO_CONTEXT_PROOF_MISMATCH`). Measurement/proof tùy chọn mà chưa biết thì vẫn hash được, với giá trị NULL tường minh.
- **Số lượng:** NUMBER giữ đúng token gốc (`1e+03`, `1.50`, `-0`…), luôn ở trạng thái `UNPROVEN` và có `KHO_PRECISION_UNVERIFIED`. STRING chỉ được chuẩn hóa khi resolved facts khớp đầy đủ: nguồn, source profile, measurement profile, encoding, miền (38,12), unit ref ứng với `DVT_Goc` của mọi hàng được tham chiếu, và tỉ lệ 1/1 tường minh. Ngoài miền thì là `OUT_OF_DOMAIN`, không làm tròn. `DVT_Goc` rỗng cho `KHO_UOM_UNKNOWN`. Không bao giờ suy ra tỉ lệ 1/1, và không dùng `DVT_QuyDoi`.
- **Classifier thuần:**
  - Không có history (`None`) → `HISTORY_UNAVAILABLE`, `MISSING`.
  - Logical/scope/profile lệch, hoặc history không nhất quán → `HISTORY_MISMATCH`, `UNKNOWN`. Digest không phải 64 hex → `HISTORY_UNBOUND`.
  - Cùng receipt, cùng request và content → `REPLAY`. Cùng receipt nhưng khác → `KHO_RECEIPT_CONFLICT`.
  - Receipt mới, content trùng accepted → `SAME_CONTENT_FRESH_OBSERVATION`. Content đã thấy nhưng không phải accepted → `REAPPEARANCE_HOLD`. Còn lại → `FIRST_OBSERVATION_CANDIDATE`.
  - Phiếu đã đảo → `REVERSED`. Unit ref của dòng khác basis cũ → `KHO_POOL_CONTINUITY_UNPROVEN`, cộng `KHO_CONVERSION_PROOF_MISSING` khi chưa có proof đã duyệt.
  - Mọi issue của reader (partial, precision, UOM…) vẫn được giữ, kể cả khi là replay. Classifier không cấp capacity, không lưu storage, không duyệt, không chọn current.

## 4. Kết quả lệnh duy nhất

Lệnh: `python -X utf8 -m unittest discover -s tests -p test_kho_10.py`

```
Ran 40 tests in 0.056s
OK
```

| PASS | FAIL | ERROR | SKIP | UNRUN |
|---:|---:|---:|---:|---:|
| 40 | 0 | 0 | 0 | 0 |

Test có gì:

- **Golden:** K01–K10 khớp raw/semantic/request digest, cả hai envelope, issue graph và request, và measurement issue kỳ vọng (dạng tập con) so với observer độc lập.
- **Controls:** C01–C19 đều có test.
- **Đối kháng:** ref thiếu hoặc null; constructor gặp dữ liệu sai; số lượng sai kiểu bool/{}/[] vẫn giữ nguyên dạng; ngày thiếu hoặc sai; master lặp hoặc thiếu; đổi thứ tự master hay thêm hàng không tham chiếu thì semantic không đổi; whitespace; thay đổi nghiệp vụ làm đổi semantic; receipt/fetch không làm đổi digest; mapping/proof chỉ đổi request; measurement chưa biết vẫn hash được; 8 kiểu facts mâu thuẫn; miền 38,12; 8 token NUMBER; receipt conflict và digest unbound; replay vẫn giữ partial; bất biến và caller mutation.
- **Hash input:** cả 43 file fixture khớp manifest, và khớp lại sau khi chạy test.

Không chạy lệnh nào khác: không PG/SQL, network, Store, API, UI, Google, cloud hay git. Không đọc `var`, `.env`, source app hay secret.

## 5. Giới hạn và điểm root nên soát

1. `KhoReadResult` có thêm vài trường ngoài danh sách tối thiểu của DTO: `semantic_envelope`, `request_envelope`, `master_raw_subtree_sha256`, `source_state`, và helper `ma_loi()`. Classifier dùng `source_state` để xử lý REVERSED. Root nên xem các trường này có được chấp nhận không.
2. `date_iso` báo `AMBIGUOUS_DATE` khi sai định dạng; reader quy về `INVALID_DATE` vì DTO03 không có mã AMBIGUOUS. Ngày null hoặc rỗng → `KHO_DATE_MISSING`.
3. Với K08 (ngoài `KHO_MEASUREMENT_UNRESOLVED` mà observer liệt kê), reader thêm `KHO_PRECISION_UNVERIFIED` cho mỗi dòng NUMBER. Vì vậy test chỉ assert measurement issue kỳ vọng là tập con, không so bằng tuyệt đối.
4. `KHO_SOURCE_PARTIAL` được gắn khi `coverage = PARTIAL` hoặc có `reported_capture_errors`; mã này không ảnh hưởng semantic hay request.
5. Kiểm tính liên tục đơn vị chỉ so `unit_definition_ref` của dòng hiện tại với `old_line_unit_basis_refs`. Không tạo basis/pool mới, không giải phóng hay mở lại link cũ.
6. Phạm vi gói này chưa kiểm DB/L11 consumption/period/RLS, và oracle tương lai (matched6, link L11) cũng chưa. Facts của K01–K07 chỉ là DEMO tổng hợp, không chứng minh được producer thật.

Dừng tại đây để root freeze/review. Không mở đầu việc khác.
