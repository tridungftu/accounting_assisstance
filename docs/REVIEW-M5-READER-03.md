# Review độc lập M5 reader — final 03

**19/10/2026 · M5_READER_PURE_VERIFIED — DEMO.** Sáu nhóm lỗi của review01 và lỗi grammar dấu cộng đã đóng trong bản frozen dưới đây, với bằng chứng root chạy độc lập. Nhãn chỉ áp dụng reader/classifier thuần và các ca đã kiểm; toàn M5/L11/M0 intake/API/UI/DB/production vẫn **PENDING**.

## Bản và bằng chứng đã đối chiếu

- Actual terminal: handle `25858`, exit `0`, tool `38f73d`, session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`; receipt SHA256 `635232cd0560ea3db2e1f54f8e4ed1b28c0a9dda76eab536b2fc9d175c276863`.
- Frozen root: `var/codex-dieu-phoi/kiem-chung-20261018-101441/m5-reader03-handoff-20261019-150429-132/frozen`; manifest `source-hashes.json` bên cạnh, **191 files**, SHA256 `ebd1c5e966446a863c23ba93f67617c5c91cc5b239f950ccbf0457b8fe22d63f`.
- Reader `src/kho_tri_thuc/nguon/kho_10.py`: **1027 dòng**, SHA256 `666d8417dcde6b6c0425ab6f55c36d33aa074eb44b3fba11e283e54564930c53`. Test file SHA256 `39c6f69999d7648fe723902cecf7189c289f20d6f389749072ae4756c9e58832`.
- Fixture manifest SHA256 `5d680a1cd4a691fba5d6eca7056bdc94f9fbf558b80e2415d97f9808215c8e66`; 43 inputs/goldens giữ nguyên. Report coder03 SHA256 `60b81406689a514af664ed3c4d3e2897dbe571eaa6cf6821ec3cb725d499ab29` đã đọc; kết luận dưới đây dùng actual root evidence.

| Lần kiểm actual của root | Kết quả | Evidence / SHA256 |
|---|---|---|
| Pure unit suite, tool `133bc5` | **49 PASS; 0 FAIL/ERROR/SKIP**; source191 không đổi | `var/codex-dieu-phoi/m5-root-unit03-5d93225415cb/summary.json` / `b584034d5ed74eba799922549ff28cf7e927d238a4b67d9dbc13be6196da996d` |
| Independent probe05, tool `f63b40` | **26 nhóm PASS**; source191/input43 không đổi | `var/codex-dieu-phoi/m5-reader-independent05-result-20261019-1506.json` / `ff117f5c5d2cfcdb9a4f21393687faf93082c14108a56f5b3a32112cd3847f8f` |
| Independent targeted21, tool `3b7817` | **21 PASS; 0 FAIL/setup errors**; source191/input43 không đổi | `var/codex-dieu-phoi/m5-targeted03-a161072746d0.json` / `064cd7e4f47d6ab4e7e6a3940581faeba0aa6574e5064516c4b622e588ff1365` |

Các bộ kiểm có coverage trùng nhau, không cộng thành một tổng số test độc lập. Probe05 SHA256 `f2fa91976ae50500b5593b221096d39c761230a76e529ca5bf18d454cfa5f3cb`; diff so probe04 chỉ đổi terminal gate `33755→25858`, không đổi assertion/fixture pin/expected. Cả 26 nhóm đã chạy hết, gồm mười golden raw/semantic/request, replay/reversed/ABA/fresh, history ref contradictions, missing context, proof contradictions, invalid-vs-null và deep immutability/caller mutation.

## Closure theo nhóm

Line anchors thuộc đúng reader frozen SHA `666d8417…930c53`.

| Nhóm cũ | Closure đã đối chiếu source và actual controls |
|---|---|
| R1 header/status | Required fields được kiểm trước lookup tại **637**; unhashable status giữ candidate+issue thay crash; thiếu LoaiPhieu/TrangThai không hash; unknown status **652** giữ CHUA_MAP/HOLD. Năm targeted negatives cũ đều PASS. |
| R2 finite quantity graph | `_FINITE_DEC.fullmatch` tại **742** kiểm trước semantic/request. Chuỗi NaN/abc giữ native+issue và null digests; cả hai targeted cases PASS. |
| R3 encoding | `_facts_mau_thuan` **857–864** xét actual Number dưới declaration exact-text; request/normalization bị giữ null. Counterexample PASS; positive unknown Number vẫn hash được và UNPROVEN, không bị blanket reject. |
| R4 history | `_kiem_history` **933–971**, gọi tại **993**, kiểm raw/master/semantic prior digests, unique reference IDs, optional present-reference resolution/digest consistency và identity. Accepted/refB→digestA, receipt mismatch, null raw/master và duplicate ref đều PASS; không trả fresh/replay khi UNKNOWN. K03/K04/K05/fresh positives vẫn PASS. |
| R5 explicit null errors | Constructor **397–399** chỉ absent default empty, explicit null bị từ chối; targeted PASS. Nullable business references vẫn giữ candidate/HOLD qua các probe missing-mapping/PN/profile/all-context. |
| R6 exact Digest | `la_digest` **47–49** dùng fullmatch cho context/history; trailing newline không được chấp nhận. Targeted PASS. |
| Dấu cộng hữu hạn | Diff product02→03 chỉ một dòng **44**: grammar thêm optional `+`. `_DEC.fullmatch` **917** không mở rộng: `+8` giữ nguyên STRING/native/text và có hash, nhưng chưa normalized/eligible; `++8`, `+`, ` +8` giữ issue/null digests. Bốn controls bổ sung đều PASS. |

Diff tests02→03 chỉ thêm 23 dòng test dấu cộng, giữ tests cũ. Không thấy regression mới trong phạm vi final diff; code/reuse/fixture/hash semantics khác giữ nguyên so bản02 đã review. Review01 và evidence FAIL cũ vẫn là lịch sử, không bị thay expected để làm test xanh.

## Giới hạn nhãn

Đây là DEMO exact-text/resolved facts do root pin; không chứng minh Number của producer hiện tại đã exact, source profile/deployment thật đã được xác minh hoặc Google readonly đã kết nối. Probe không import coder tests và không dùng công thức hash của product làm expected.

Chưa có acceptance về common capture/receipt/RLS, typed M5 persistence/current pointers, M2 bridge, dual quantity pools/child/L11, source review API/UI/file/restart hoặc tồn/kiểm kê producer. Reader không cấp capacity, không đổi accepted state/links và không vận hành M9/source app. Tác giả review chỉ đọc static diff/evidence và tạo tài liệu này, không chạy thêm product/runtime/SQL.
