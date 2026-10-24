# Review độc lập CRM-01 pass02 — tích hợp M1

**Kết luận: NOT_ACCEPTED, cần pass03.** Đã kiểm main path HTTP local với DB/role DEMO mới, actor MO_PHONG_ và actual Store → QuickPosting → converter. G01 trước hợp đồng và G03 nhận hợp đồng/nối tiền cũ có control dương. Hai điểm chặn là nhánh tiền sau hợp đồng vẫn Có 344 và projection lỗi nguồn đã trả thất bại nhưng vẫn commit thay đổi K2. Không dùng coder expected làm oracle; expected 344/131 dựa TL32 §3.2, dòng quyết định 102 đã chốt trong PLAN.

## Bản được kiểm và phạm vi

Root xác nhận terminal authoritative handle51099/exit0 qua `crm02-handoff-20261019-071834-580/terminal-confirmation.json`. Manifest 117 file src/tests/tools SHA256 `5d85cd7b822c3ae09e0b88d83421309904307a905d29da4f639fc5de933a44f2`; trước import và sau runtime đều khớp toàn bộ 117 hash.

| File | SHA256 |
|---|---|
| `src/kho_tri_thuc/k2/m1_demo.py` | `411e3bf9e06101d32d65bb37ab057276bd82b44cb47f902bbE09eab85352676d` |
| `src/kho_tri_thuc/giao_dien/server.py` | `f76110907f6aa550fc25b7b8d6df0af917434b8d6768a0da51b85d4620c93a54` |
| `tools/chuyen_sqlite_sang_pg.py` | `cae8de77473f26e79892b2beea0875591b3d7c5f5e0db5459c3c9e8b7169f9da` |

Runtime chính: `var/codex-dieu-phoi/crm-m1-reuse-recheck02/runtime-20261019-072249-40e135/`. Script `runtime_route_probe.py` SHA256 `3de3e70d133388e00204a6824ae1e0af573b2e7fea12cc5e204576d8e27d951a`. Guard active từ startup, isolated PYTHONUSERBASE, CODEX_NO_DELETE_FILES=1, PYTHONDONTWRITEBYTECODE=1. Guard nested-comment revision root đã bổ sung, hash lúc đọc trước chạy `a517c5359ceada062900edd34280d4dc7daa2a001d5e05c84a9eae174813a229`.

DB retained `kho_test_m1r02_e3b8294bb904`, role retained `kho_test_m1r02_2b09a26c69cc`; login thật NOSUPERUSER/NOBYPASSRLS, member app_web, actor theo cookie do server cấp. Secrets chỉ ở process, không lưu credential/token. Không sửa product, backup hoặc dữ liệu thật; không cleanup/delete file, DB hay role.

Lần sandbox trước `runtime-20261019-072209-58772e` trả HTTP500 LOCAL_STORAGE_ERROR, không tạo kho M1/BANK. Harness sau đó đọc kho chưa có gây OperationalError. Lần này là setup/storage limitation, **không business result**; giữ DB `kho_test_m1r02_189cfe4bfd40` và role `kho_test_m1r02_b6be72b2e8f9`. Chỉ lần host sau mới có control dương và các finding dưới đây. Exit0 của script private chỉ cho biết script đã ghi summary; phải đọc status/cases, không dùng process exit làm acceptance.

## Kết quả đã kiểm

| Gate | Evidence quan sát độc lập | Trạng thái |
|---|---|---|
| G01 main path trước HĐ | HTTP200; delta 1 BANK → 1 SAO_KE → 1 proposal/2 dòng; N1121/C344 đúng 300.000.000, ObjectID DEMO A01 đúng; 0 lô | Control dương đạt trong ca này |
| Source proof | Cả 3 BANK trong staging A nối đúng natural_key/legacy ID, amount/currency/date, exact core/hash, quick_item ID, nguyên proposal; source record/raw ↔ artifact hash/size/PN ở K2 khớp. 6 nhóm kiểm đều true | Đạt phần quan sát này, không thay cho toàn A5 |
| G03 HĐ đến sau | Nhận #6, kế toán kiểm, MO_PHONG_CFO duyệt thật qua HTTP; sinh 3 đợt. Nối tiền cũ vào COC-1, 1 link; không thêm/đổi BANK/proposal/dòng/lô | Control dương đạt; money hash trước/sau cùng `59fde5b1744c0577132456ce5ab0a5c8467ca253cb319828f30e2e19ee51ebd2` |
| G02 tiền sau HĐ | HĐ đang hiệu lực, đã duyệt đúng workflow. HTTP200 nhận hai khoản 500.000.000/900.000.000 nhưng cả hai Có 344; expected Có 131/đợt DOT-1 gần nhất | **FAIL, chặn** |
| G04 nhận lại | HTTP200; inserted0/duplicate2/proposal mới0; BANK3→3, proposal3→3, dòng6→6, lô0→0. BANK/proposal giữ fingerprint; chỉ 6 PK dòng chưa duyệt được tái sinh, semantic sau bỏ đúng PK riêng của dòng giữ nguyên | Không có nhân đôi tiền/số lượng; row identity không ổn định. G10 với dòng đã quyết/có reference **chưa kiểm** |
| G12 error detection | **Helper/converter direct, không phải HTTP negative**. Bản copy SQLite DEMO riêng có 1 core_hash sai; destination đồng thời có surplus CRM ở 3 bảng. raw exit1, chieu.ok=false, lech_noi_dung=[core_hash_nguon] | Detector không nuốt lỗi nguồn trong ca mixed này |
| G12 atomicity | Dù wrapper false, 1 BANK hash K2 đổi, 6 PK dòng tái sinh. Số lượng BANK3/proposal3/dòng6/lô0 giữ; amount/currency/account chưa đổi trong ca này | **FAIL, chặn**: không được gọi toàn G12 pass |

G01/G02 dùng selections DEMO do route hỗ trợ làm input; expected account branch do reviewer đặt từ quyết định đã chốt, không lấy output hoặc test expected coder. Main path chưa nhận arbitrary input của private corpus; vì vậy PN/profile collision, USD, bigint và các fixture tự đặt không được coi đã chạy nhờ các ca selection này.

## Finding cần sửa

**F1 — P1: tiền sau hợp đồng vẫn được áp quy tắc trước hợp đồng.** `m1_demo.py:29–40` stage một policy pending luôn credit344; `nhan_sao_ke:47–72` không nhận fact HĐ/đợt. `server.py:276–292` gọi đường này sau kiểm quyền nhưng không cung cấp contract/installment fact. Runtime G02 đã có HĐ/đợt được kiểm/duyệt, cả hai payment vẫn C344. Cần giữ reuse M1, bổ sung fact/provenance theo PN/profile/object và đợt gần nhất qua đường đã chốt; không tự approve policy pending, không dựng thêm engine/SAO_KE hoặc chỉ đổi lời giải thích header. Tiền trước HĐ đã quyết/nối không được tự viết lại khi HĐ đến sau.

**F2 — P1: thất bại validation nguồn vẫn commit projection.** `m1_demo.py:81–101` gọi converter rồi mới diễn giải report. Converter `_chuyen:89–116` commit transaction sau tính report; `_chay:84–86` mới quyết exit1 từ mismatch. Ca source core_hash sai đã ghi hash sai vào BANK đích trước khi wrapper trả ok=false. Tiêu chí pass03: source validation failure hoặc content mismatch không half-promote, không đổi hash/amount/currency/decision/link/line/lô đã có; source và before/after retained. Không cần mở rộng sửa toàn bộ A5 ở đây, không đổi expected failure thành pass vì số lượng vẫn bằng nhau.

**G04/G10 giới hạn:** converter `_de_xuat:357–379` DELETE/insert dòng chưa export; retry ca chưa duyệt chỉ đổi PK dòng. Không gọi đây là duplicate tiền, cũng không dùng semantic hash bỏ ID để chứng minh dòng đã duyệt/có FK/reference an toàn. G10 approved/protected line, khóa kỳ và M11 bypass qua converter chưa có control dương trong lượt này; **NOT_VERIFIED**, không tạo SQL fake approval.

## G12 before/after cụ thể

| Collection | Count | Field đổi | SHA256 trước | SHA256 sau |
|---|---:|---|---|---|
| BANK | 3→3 | hash của 1 record | `c5f23786d7a8c825e176b840f354bceadce664e0cedd96b11f9e2fc6f014440a` | `eb424341d9a9abf00ec7db92c8d828608602a0fd2e7cd6ddeca5e8e6a0903093` |
| Proposal | 3→3 | không | `5c10839d6704c25d847ed9531bf16440e020554eae26cadcfcb9b16cacd40fb3` | cùng hash |
| Dòng proposal | 6→6 | 6 PK id; semantic giữ | `535a1ee505c73d117b3b84cec0b26f50bac498fb990f1748fcb7042ab1e4f92e` | `25001f5c5fd87f4e11d2ffc666f021135de2d6ee99329cfe99d6d8a9306dfc5c` |
| Lô | 0→0 | không | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` | cùng hash |

Mẫu before hash nguồn SQLite ở summary v1 được lấy **trước legitimate retry**, không đúng sát boundary negative. Chênh hash đó không được gán cho negative; script âm chỉ chạy trên bản copy và mở source readonly, nhưng exact pre-negative source file hash chưa đo. `review-revision-2.json` ghi rõ giới hạn. Không sửa/xóa v1 để che khác biệt.

## Evidence chốt để dispatch pass03

`review-revision-2.json` là phân loại cuối sau review, SHA256 `9dc8c4a0adc06f901049120ee3c3c19b99218af4dd63e8b34ebbf33ca1830abd`; nó giữ G04 business values vs PK churn và tách G12 detector đạt/atomicity fail. `summary.json` v1 retained SHA256 `7dc79a48b2bdf7329bee5acc5675ea1f6f2d283aa5529dbf74177d52a8b3c30a`: nhãn G04 FAIL là raw fingerprint; G12 PASS chỉ predicate detection, không là acceptance. Phải đọc revision2 + báo cáo này.

`analyze_route_evidence.py` SHA256 `1a279bf7489307c77b3314607505d08096dfcab2b190ccd19f7bef834c176aeb` chỉ đọc evidence + source SQLite readonly + retained PG read-only để đóng provenance, không import/action product. Target quan sát có 3 artifact, 4 counterparty mapping và 2 project ở hai PN; mọi source BANK được so từng record, không dùng global count hoặc nhãn khop của converter làm oracle. Toàn33/M1/CRM chưa được nghiệm thu từ lượt này; G05/G06/G07/G08/G09/G10/G11 và phần failure-route HTTP cụ thể còn theo gate tương ứng.
