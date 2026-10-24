# Review độc lập CRM host 05 — bản nháp, chưa nghiệm thu workflow

Ngày 19/10/2026. Mốc bằng chứng: đã chạy GET diagnostic trước adapter và kiểm riêng retention adapter; root đang thử mở lại default app. Reviewer chỉ đọc JSON, code frozen, log guard và metadata file; không chạy HTTP, SQL, product imports, process actions hoặc đọc credentials.

**Kết luận hiện tại:** GET của app đang chạy đạt; lần workflow đầu thất bại HTTP 500 và chưa có hồ sơ/HĐ được ghi. Bằng chứng hỗ trợ rất mạnh lỗi cleanup file tạm tại retention boundary. App-only adapter đã qua control giữ file; chưa có bằng chứng trong bản nháp này rằng default launcher và workflow sau adapter đã đạt. Không chuyển trạng thái các hạng mục đang chờ thành PASS.

## Phạm vi và bằng chứng đã đọc

Đường dẫn tương đối tính từ `D:\Claude\Phan mem ho tro ke toan\Phần mềm kho tri thức`. Handoff handle 32050 terminal exit 0; manifest 125 source files SHA `b9bd8c6dd61af2df17ebc5ab4257681bd28caafdee7654406a6a015f835fde82`. Bằng chứng pure/stub và B05 compatibility deviation nằm trong `docs/REVIEW-CRM-KHOI-DONG-05.md`; không dùng các kết quả đó để suy ra host PASS.

| Bằng chứng | SHA256 | Điều xác nhận |
|---|---|---|
| `var/codex-dieu-phoi/crm-launcher-recheck05/host-http-first-32050/result.json` | `428b05e1428be7223f2add2146415c9a1b7e98325860f370cfa4599136003742` | HTTP 500 thật; health PID 26840; chưa có snapshot/workflow hoàn tất; source125 trước/sau giữ nguyên |
| `.../host-http-diagnostic-before-app-retention/result.json` | `f6f711f1d6ba042b9bb987d8784ca20ba4367df5ef377ceee7552451b6772d3d` | Cùng PID/root; 4 GET độc lập đều 200, không error code; source125 giữ nguyên |
| `var/codex-dieu-phoi/app-retention-control-1792377774558258100.json` | `fa36c39df5c7f62b442885268b1c2c67e13e73a2328a61863824c5a327090bcf` | Raw cleanup được giữ; non-raw bị từ chối và file vẫn tồn tại; không xóa file |
| `.../crm-launcher-recheck05/owned-shutdown-before-retention-1792377848563286100.json` | `0041e84044d6607c27c06852bd7dc2ef2b44a9d3f0ba1ddc8b3ad18298ccdec9` | Root dùng API shutdown của PID cũ; đếm nghiệp vụ trước shutdown đều 0; không dừng PostgreSQL |

GET diagnostic thực tế: `/api/health`, `/`, `/api/crm`, `/api/state`, tất cả status 200/error_code=null. Health root_id `c12f2e9a2d9ca46e3bb668b5462dd62fe6401524bcc42d3fa8c742c7c26708ba` khớp `var/web`, PID 26840, started_at 1792377229, version 0.6.0. Diagnostic không lưu body, cookie hoặc token. Kết quả này xác nhận các read paths tại thời điểm chẩn đoán, chưa chứng minh POST nhận mẫu/kiểm/duyệt/xuất.

Artifact shutdown ghi `pre_shutdown_counts`: ho_so=0, hop_dong=0, file_soat=0, tien=0. Đây là số đếm qua HTTP theo quyền phiên, không phải kiểm riêng mọi bảng PostgreSQL. Root xác nhận process cũ đã vắng sau shutdown; JSON được review ở đây ghi trạng thái `SHUTDOWN_REQUEST_ACCEPTED`, chưa kèm OS process-absence snapshot riêng.

## Lần HTTP 500 và nguyên nhân

Initial observer không lưu route khi request thất bại, chỉ có HTTP_STATUS_500 sau health. Không coi thiếu trace là bằng chứng endpoint nào đã đạt. Log `var/web/logs/server-error-20261019-023347-25472-1.log` rỗng; stdout chỉ startup. Frozen `giao_dien/server.py:354` tắt access log, `:654` trả 500 cho OSError/sqlite3.Error, không ghi traceback cho nhánh này. Sai validation/token/role theo DataError sẽ ra 400/403.

Metadata tại 09:36:57 cho thấy `var/web/crm-k2/k2-tep` có đúng hai file, một `.raw-*` và một content-addressed `.bin`, mỗi file 2742 bytes; không có source text hoặc thư mục export. Guard event cùng PID 26840 tại 1792377417.0097942 ghi `operation=file_cleanup, retained=false`. Reviewer không đọc payload các file.

Frozen `k2/crm.py:115` gọi `write_immutable` raw trước khi kiểm/nạp PostgreSQL. `ha_tang/store.py:23` tạo NamedTemporaryFile, hardlink sang file đích rồi `finally temporary.unlink` (`:41`). Guard SHA `a517c5359ceada062900edd34280d4dc7daa2a001d5e05c84a9eae174813a229` chỉ no-op retain cleanup trong `var/codex-dieu-phoi`; ngoài phạm vi sẽ ném PermissionError. Chuỗi raw đã publish + temp còn lại + guard event cùng thời điểm + nghiệp vụ vẫn 0 + GET đọc đều đạt hỗ trợ rất mạnh: POST `/api/crm/mau` đến immutable write, bị chặn cleanup trước source text/DB ingest và Handler trả 500. Đây là suy luận nhân quả có căn cứ, không phải failed-route trace/stack trace trực tiếp.

Phân loại: lỗi tích hợp runtime với yêu cầu giữ file, không phải expected kế toán sai. Observer cũ có thiếu observability; thiếu đó không biến HTTP 500 thành harness-only PASS. Không xóa temp, tắt guard hoặc giả tạo DB approval để đi tiếp. Initial FAIL phải giữ trong lịch sử dù lượt sau đạt.

## Adapter và observer được chuẩn bị

Root giữ backup và adjustment tại `var/app-runtime/app-runtime-20261019-092310-807/app-retention-adjustment-20261019-094241-121.json`. Sitecustomize app-only hiện SHA `9d84b170dcecfe707552c0f09ef54862f953c15d86b24205af3ef870bcb74844`; guard gốc a517 không sửa. Static review: adapter chỉ mở rộng hàm xác định phạm vi retain cho file `.raw-*` tồn tại, là regular file, không symlink và resolve nằm dưới `var/web`. Nó vẫn dùng cleanup no-op của guard, không gọi unlink thật. File khác giữ quy tắc cũ. Control JSON xác nhận raw còn tồn tại, non-raw bị từ chối và vẫn còn, private_userbase_absent=true, workspace guard đúng. Đây là control riêng, chưa chứng minh web process mới đã nạp adapter và hoàn tất nghiệp vụ.

Original observer SHA `e1231b6c8b2b89c0d022e124434eeca3568bf323faeebde8f384e5e0fc3238f8` được giữ nguyên. Revision `host_http_observer_rev2.py` SHA `04392d496bee24bfe0cda7867a4a66fa73e847fea1bf77804f5b04638fe4fa2a` chỉ thêm route/method/status/safe error-code trace và persist khi lỗi; AST đối chiếu workflow/expected không đổi. GET diagnostic SHA `f537696941dead4e57dbec889ecfe8596030f497a4556c2d5282c4c063902776`. Cookie/token chỉ ở memory; không lưu headers hoặc response body.

## Checklist chờ bổ sung bằng chứng root

| Hạng mục | Trạng thái tại mốc bản nháp |
|---|---|
| Default CMD sau adapter; no private PYTHONUSERBASE/PYTHONPATH và không Python override | NOT_VERIFIED — root đang thử, chưa đọc kết quả cuối |
| Web process mới nạp đúng runtime/deps/guard/adapter, owned PG đúng endpoint/data directory | NOT_VERIFIED trong review này — root cung cấp host proof riêng |
| Nhận mẫu kcn_goc → KT kiểm exact PB → MO_CFO duyệt qua HTTP thật | Chưa hoàn tất; initial attempt FAIL, lượt sau adapter chưa có evidence |
| Xuất, đăng ký và download XLSX; expected sheet/cells/hash/ID | NOT_RUN sau adapter |
| Reopen default launcher, giữ cùng app/endpoint/DB, không tạo hồ sơ/HĐ/lô trùng | NOT_RUN sau adapter |
| Owned OS web-process restart, session mới; giữ approved PB/lịch/export bytes/cells/ID sets | NOT_RUN sau adapter |
| PowerShell parent env restore; SQL login nonowner/RLS thực tế | NOT_VERIFIED tại reviewer; không suy ra từ GET/pure |
| GUI | NOT_RUN |
| Cold cluster | NOT_RUN; chỉ quan sát khi tự nhiên dừng đúng cluster, không stop PG để tạo ca |

Bản nháp này không tuyên bố nghiệm thu launcher hoặc toàn bộ CRM/M1. Bổ sung actual host evidence vào phần tiếp theo khi root cung cấp; giữ nguyên initial failure và các giới hạn chưa được kiểm chứng.

## Cập nhật: default Windows PowerShell 5.1 hỏng Unicode transport — chờ sửa06

Root tái hiện độc lập ngày 19/10/2026, trước khi dispatch Claude handle 51883. Reviewer đã đọc `var/codex-dieu-phoi/crm-launcher-recheck05/windows-ps-encoding-before-20261019-094625-027.json` SHA `30dda3d9a863a4ac0e84745a357d92420573f5bb612c3d510d824b176007e841` và script probe SHA `aa9af388a5b34012f6e711a721af56dd841ebfc78f95b65d9a37c7e117cdd77e`. Probe chỉ chạy selector/capability process, không SQL hoặc server, không sửa source.

Actual JSON: PowerShell `5.1.26100.9711`, Console output codepage 437, pipeline OutputEncoding 20127; selector báo `crm=true`, nhưng `decoded_pythonpath_matches_expected=false`; cả 3 decoded paths không tồn tại, cả 3 expected paths tồn tại. Probe đọc cấu hình runtime **không bí mật**, dựng chuỗi expected rồi so case-sensitive với chuỗi JSON stdout được Windows PowerShell decode. Reviewer không đọc secret config. Đây là bằng chứng lỗi machine JSON transport Python→PS ở đường dẫn có tiếng Việt/khoảng trắng; runtime capability PASS không đủ chứng minh đường dẫn đến child còn đúng.

Theo root và dispatch spec `docs/CRM-01-YEU-CAU-SUA-REVIEW-06.md` SHA `a493a6a1318ce6671d5d843cd81960e463f5430fe50b29c0af7b5a14748fe086`, default bootstrap báo `RUNTIME_THIEU_DRIVER`, sau đó server không import được `kho_tri_thuc`; runtime log UTF8 vẫn giữ đường dẫn đúng. Các lỗi bootstrap/server này là bằng chứng root báo riêng, không gán cho probe vốn không khởi chạy server. Chưa có default clean click PASS sau adapter.

Trạng thái mới nhất: **default Windows5.1 path FAIL, cần sửa06 và kiểm lại**. Control retention trước đó vẫn là control riêng, không chữa lỗi decode stdout. Không cài lại dependencies, đổi tên folder, hardcode đường dẫn hoặc đổi codepage global để né lỗi. Giữ initial500/expected/raw evidence05. Recheck06 chỉ nhắm machine stdout Unicode roundtrip/Windows5.1 thực tế, default first/reopen và owned web-process restart cùng workflow/export/snapshot; không mở lại các suite SQL/parser/domain đã đạt khi không đổi chúng.

Claude 51883 còn active tại mốc cập nhật: không chạy product/HTTP/SQL/launcher, không dùng source interim làm final. Recheck06 đang chuẩn bị riêng, phải có authoritative terminal + manifest mới + root release sau review API cuối. Workflow/export/reopen/restart/GUI/cold vẫn chưa được đánh dấu PASS.

Cập nhật sau đó: authoritative51883 terminal exit0; freeze06 `crm06-handoff-20261019-095149-416` có125 file, manifest SHA `c828d1fff9593a0dce6d47e079df8adf76a4609cb936e2f1a627cf1a9948dd08`. Reviewer kiểm hash/bytes125 file, xác nhận chỉ `tools/chon_runtime.py`, `tools/chuan_bi_crm_demo.py`, `tests/test_crm_khoi_dong.py` khác05. Static final `chon_runtime.py:173` và `chuan_bi_crm_demo.py:70` in stdout `ensure_ascii=True`; runtime file log vẫn UTF8/`ensure_ascii=False`. Đây là sửa code đã đọc, chưa là bằng chứng Windows/default click PASS. Ba private scripts06 AST đạt; AST Client/target/workbook/snapshot giữ nguyên expected từ rev2; root còn phải release và thực thi host. Reviewer chưa chạy product/tests/HTTP/SQL/launcher.
