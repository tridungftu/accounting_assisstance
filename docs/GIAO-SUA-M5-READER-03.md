# M5 reader thuần — sửa 03, finite text có dấu cộng

**19/10/2026 · READY_FOR_ROOT_REVIEW; chưa dispatch/nghiệm thu.** Tiếp tục session `52783bcd-6e1d-46d2-9e45-3c527aa43e5b`; sửa đúng P2 grammar, không mở scope reader/core/UI/source app/M9.

Reader02 terminal0; frozen191 manifest SHA `1ec0a69d17f5c8c01a2428f35c6a804643af5162c2b297c1ff3f96b299e20249`. Reader SHA `ad0378e1dd43fe27fde27588628444e525c6e43569d804ecf25e3dc5590cb1bf`, test `5186ae876831c63aaa9ffc45ed9e7eb90155a88d3a238e71b65ee9478893258a`, report02 `e12dedb550a0fab3a9796eb305012a2bd1da39ffbd555de8b182a42440a5fd55`. Coder tự báo cáo48unit PASS (root chưa chạy suite02); independent probe04 **26groups PASS**, evidence SHA `28f7bcce8f90c88705a0d7d26256e545e3d442ce5f9a49f24f64bf6bdd2f6fd0`; source191/43fixtures nguyên. Separate pluscounter **1baseline PASS+1'+8' FAIL**, evidence SHA `9a747c5c73ea8b1e93e090a4ea9e6b5e2b2c02382a5b75f0398844075d9042de`. Không đọc `var`; sanitized trigger/expected nêu đủ dưới đây.

Chỉ ba write targets: `src/kho_tri_thuc/nguon/kho_10.py`, `tests/test_kho_10.py`, **mới** `docs/BAO-CAO-M5-READER-03.md`. Giữ report01+02/43fixtures/expected/oracle/DTO03/contracts/reuse files và mọi product khác nguyên hash; không sửa helpers/runner/guard/settings/dispatch/public ledgers hoặc thêm file khác.

Actual `_FINITE_DEC` dùng `-?`, khác grammar của independent helper03 đã root review/pin (`[+-]?`, SHA `97b55bf04a062a19fe338b91504dc5af376aa617ba9d62cb18a784de3554eacf`). Sửa **chỉ optional leading sign của `_FINITE_DEC` từ `-?` thành `[+-]?`**. Không broaden `_DEC` normalization hoặc sửa profile/eligibility, không sign-strip/trim/parse Number/round để làm test qua.

Regression mutation DEMO trong memory, không đổi fixtures/golden:

- Positive K01 baseline vẫn giữ golden. Đổi một native `SoLuong` thành text `"+8"`: giữ STRING/native text/raw bytes thực, semantic/request H hiện diện khi context hợp lệ, semantic khác baseline; không KHO_FIELD_TYPE/graph issue. Có thể vẫn normalizedNULL/HOLD theo `_DEC`/profile hiện tại; không test ép eligibility.
- Negative texts `"++8"`, `"+"`, `" +8"`: giữ exact raw/text/kind STRING, graph issue và semantic/request NULL; không tự sửa whitespace/sign. Giữ negative NaN/abc và controls48 hiện có, lexical NUMBER/exponent/zeros, history/replay/ABA, null/digest guards02.

DTO03 `docs/M5-HOP-DONG-DTO-33.json` SHA `d1b3577074794d8d09af2d5ccb58aa0caa47540f7ccaf3e62475599fb6e6f73f`, fingerprint SHA `7fcf0e3d24564ae129dabb615791097640609aaaa6d016bcd6121c24062e02bf`, fixture manifest `5d680a1cd4a691fba5d6eca7056bdc94f9fbf558b80e2415d97f9808215c8e66` giữ nguyên; handoff01/repair02 tiếp tục áp ngoài thay đổi hẹp này. Observer expected không truyền reader, không lấy output reader làm golden.

Sau root dispatch chỉ command exact dưới guard/no-bytecode:

```text
python -X utf8 -m unittest discover -s tests -p test_kho_10.py
```

Không command khác/PG/SQL/Store/K2/API/UI/HTTP/network/Google/cloud/host/config/realstore/env/secret/source app/M9. Bash denied=>UNRUN/dừng đường đó, không đổi policy/shell. Không xóa/move/cleanup file/temp/DB/role/attempt. Report03 ghi exact counts+diff+limits rồi kết thúc CLI để root freeze/review/independent rerun; chưa tự nghiệm thu M5/33 hoặc bắt đầu việc khác.
