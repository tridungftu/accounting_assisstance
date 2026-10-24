# CRM-41-01-06 — Nút DEMO tự mở engine #6 dùng chung

**21/10/2026 · CODE_ONLY sau Root release · một product writer cùng session hiện hành.** Đây là phần triển khai của quyết định engine chung đã được Anh chốt; không mở lại kiến trúc, không dựng extractor khác. Root chạy kiểm độc lập sau writer terminal, rồi bàn giao bằng nút bấm khi đủ bằng chứng.

## Căn cứ và điểm bắt đầu

- Quyết định `docs/QUYET-DINH-ENGINE-TRICH-THAM-SO-DUNG-CHUNG.md`, SHA256 `54be96e958c8fe9e00c93788c2d3becd6bf8522a832ab2415b63e17e811dfadb`. Engine thật duy nhất ở `D:/Claude/Ho tro review ho so xay dung/review_xaydung/trich_xuat`; central dùng API/client/projection chung, từng lần truyền loại/catalog/version/mã yêu cầu. Không copy/import staged extractor làm runtime.
- Central F11: freeze `crm-41-01-fix05-frozen-57b6750bf49a`, source370 `f7966e448815b68a0aabd9d7306e1b89d75116ad3338d4afcacb1a5c80cbdfb3`, runtime438 `69f613c650a7a8e4226231048e33f57648e47c62557df071a92e1d539bd4e1a2`. Actual source37 đã áp F11, manifest `50c507258878b4b5c49f12deb5b9dfc8704bb97d53ed86e5dcc5ae54f13556a4`; source thật chỉ đọc trong lượt Claude này. Root áp staged patch có backup sau review.
- Đã kiểm độc lập: native nguồn24/24; client/projection/wiring28/28; source literal ALL37 + hai subset/7 denials/replay/conflict; actual-client API1; actual M4/CRM HTTP→PG8 ca PASS, mọi owned test service đã dừng. GUI/launcher chưa đạt. Không chạy lại toàn bộ chỉ vì thêm launcher; chọn kiểm hữu hạn theo thay đổi.
- `MỞ BẢN DEMO.cmd`→`start-web.ps1` hiện chỉ mở central; `serve()` sở hữu LocalApp/LocalServer, hai callsite CRM/M4 tự dựng client từ URL environment. Nối đúng seam này; không đổi master, DB, approval, thuật toán trích hoặc Review khác.

## Phạm vi ghi chính xác: 10 existing, 2 NEW

Existing: `src/kho_tri_thuc/giao_dien/server.py`; `src/kho_tri_thuc/giao_dien/m4.py`; `start-web.ps1`; `src/kho_tri_thuc/nguon/trich_chung_6.py`; `src/kho_tri_thuc/k2/crm.py`; `src/kho_tri_thuc/k2/xay_dung.py`; `tests/test_trich_chung_6.py`; `docs/CRM-41-01-SOURCE-PATCH/may_chu/dich_vu.py`; `docs/CRM-41-01-SOURCE-PATCH/tests/test_common_api.py`; `docs/BAO-CAO-CRM-41-01.md`.

NEW: `src/kho_tri_thuc/nguon/trich6_host.py`; `tests/test_trich6_host.py`. Chỉ một host adapter nhỏ và test vòng đời có ý nghĩa. Không thêm framework/provider/core/catalog/DB hoặc ứng dụng riêng. Không sửa CMD, runtime selector, bootstrap, source server staged, migrations1–20, M9 hay file ngoài allowlist.

## 1. Vòng đời owned source, tách dữ liệu DEMO

- Chỉ đường `serve()`/CLI DEMO khởi động owned host; **không khởi động trong LocalApp constructor** vì fixture hiện có tự tạo LocalApp. `environment=that` không tự mở engine. Nút CMD hiện có vẫn dùng được; không yêu cầu Anh gõ lệnh/cấp URL.
- Host parent dùng đúng runtime hiện hành/guard, Windows Job `KILL_ON_JOB_CLOSE` sở hữu child và nested workers. Assign Job **trước khi** cấp cấu hình/secret qua stdin. Child chưa nhận input không được import source/mở server. Không detached orphan; không spawn theo process-name; không gọi source `main()`, AI probe hoặc `_thay_ban_cu`.
- NEW host có parent adapter và child entry tối thiểu. Chỉ child đặt đủ `HD_DU_LIEU`, `HD_OUT_DIR`, `HD_DANH_MUC_HD`, `HD_CSDL`, `HD_THU_MUC_KHOA` vào subtree riêng của central DEMO DataRoot **trước import actual source**, rồi dùng factory có sẵn `may_chu.server.tao_may_chu(0)`. Không dùng kho/config/keyDB thực của app nguồn; không invocation/probe/network/cấu hình AI/cloud/OCR/Office. Cho phép import các module kỹ thuật có sẵn do factory thật phụ thuộc, không gọi chức năng AI. Giữ mọi run/input/output/history qua restart; không xóa file.
- Child environment lọc bỏ PG/admin/API keys và biến cloud/credentials không cần thiết; chỉ giữ runtime/guard cùng dữ liệu kỹ thuật cần chạy. Source path do host tin cậy quyết định, không nhận từ browser; không dò/copy source engine. Parent/child chỉ trao handshake hữu hạn trong memory/stdin/stdout riêng: instance/root identity, PID, actual bound loopback port và implementation identity. Không nhầm endpoint test đã dừng với runtime sẵn sàng. Startup timeout/failure dọn đúng owned process/Job; runtime lỗi báo rõ.
- Normal stop: owner gửi EOF/shutdown qua lifecycle, đóng server và chờ worker/join hữu hạn; fallback Job kill chỉ của mình. Central bị force-stop cũng đóng Job và mọi source worker. Không tắt app nguồn/người dùng hoặc chiếm cổng8600/64900. Parent socket/server lỗi ở bất kỳ bước nào cũng vào finally cleanup.

## 2. Owned endpoint chỉ common/v1, có quyền nội bộ theo instance

- Factory nguồn bình thường vẫn giữ legacy; owned child bọc Handler theo instance, không mutate global ROUTES/token/legacy behavior. `_hop_le` của owned handler dùng `self.server.server_port`, không dựa global PORT của source.
- Token random memory-only per owned instance; parent cấp qua stdin sau Job assign; child/server attribute và shared client optional header. So sánh `hmac.compare_digest`. **Không token trong argv/env/file/URL/query/health/UI/log/report/intent/raw metadata**. Mọi request owned, cả preflight/download, phải có token; giữ Host/Origin/X-HD hiện có.
- Gate method/path/auth **trước** route legacy/static và trước `do_POST` nhánh riêng `/api/tat`. Chỉ mở GET `/api/trich_xuat/common`; POST `/api/trich_xuat`; GET `/api/trich_xuat/<luot>`; POST cùng lượt `/tep`, `/chay`, `/dung`; GET `/tai/...` đúng canonical sealed common result trong owned outputroot. Không mở list/viec/UI/settings/AI/master/BOQ/DELETE/chay_lai/nap_csdl/tat.
- Riêng create/chay bắt buộc body common/v1 + RULE_ONLY trước delegate; thiếu contract hoặc `{}` phải bị chặn, không chạm cfg/AI/legacycreate. Download phải bind seal/common run/ref và containment resolved, không generic arbitrary source file. Dùng lại validator/seal/factory thật, không viết lại thuật toán trích.

## 3. Nối hai consumer và health/nút mở

- LocalApp thêm factory client nhỏ có scope theo app/owned host; cả CRM `server.py` và M4 `giao_dien/m4.py` dùng nó. Owned URL/token truyền trong memory bằng constructor option; không nhận từ browser hoặc token environment. Managed-mode được đánh dấu trước spawn; host lỗi/chết/stale vẫn giữ managed-mode, không fallback URL environment. Direct LocalApp fixtures explicit chưa sở hữu host vẫn giữ existing external URL/transport seam để không phá regression; constructor không có side effect mới.
- `/api/health` chỉ bổ sung readiness và nonsecret owned identity phù hợp; không URL/path/bearer/DSN. Ready phải phản ánh owned child còn sống + actual authenticated common capability/implementation khớp boot identity đã nạp, không chỉ cached bool hoặc hash file mới trên đĩa từ startup. Child chết hoặc identity không khớp ⇒ NOT_READY; không tự dùng legacy/default endpoint.
- `start-web.ps1` dùng health mới để reuse đúng cùng central/root/PID/listener/source ownership; source chết/oldhealth thiếu identity không được báo ready. Reopen/restart chỉ tác động central thuộc đúng kho đã chứng minh; giữ hidden launch, runtime selector, PG bootstrap/ordinary role và guards. THAT không bị bắt phải có owned DEMO engine.

## 4. Đóng hai lỗi nhỏ đã xác định, cùng lượt

- F11 `Trich6Client.trich()` gọi `_can_san_sang()` trước đọc durable00 và ngoài preflight catch. Chuyển đúng check vào đường stage-aware hiện có: fresh unconfigured rõ NOT_READY/zero POST/không tạo own intent; đã giữ intent có thể create hiệu lực + mất URL ⇒ UNKNOWN, giữ nguyên body/key/raw, khi cấu hình lại đối soát lượt cũ. Không dựng state DB mới.
- Caller `CrmK2.trich_tu_docx` và `XayDungK2.trich` hiện short-circuit `not client.san_sang` trước intent lookup/client.trich. Sửa hẹp để classification stage-aware đi hết callchain; client None vẫn lỗi cấu hình rõ. Giữ quyền hiện hành/pháp nhân/revision/full envelope conflict trước source effect và CAS trước công bố. **M4 không chỉ bỏ guard san_sang**: NR343–346 sẽ chuyển fresh NOT_READY thành kết quả LOI rồi ghi revision; dùng readonly stage-aware check hẹp trước NR (hoặc tương đương trong exact allowlist) để fresh thiếu URL lỗi rõ, prior accepted/UNKNOWN thiếu URL vẫn UNKNOWN, cả hai zero POST/zero ghi K2; không ghi FINAL LOI. CRM giữ fresh thiếu URL không tạo ý định/raw mới, prior full intent phải được kiểm xung đột rồi phân loại UNKNOWN. Không sửa NR protected. Client-only test không tự chứng minh central HTTP.
- Source staged `_tim_dat_luot`: request_id đã là str nhưng chưa `RE_REQUEST_ID.fullmatch`; bản ghi rỗng/invalid format phải UNKNOWN/fail closed, không coi là other-intent rồi allocate mới. Thêm counterpart vào existing native test; không thêm reservation framework hoặc nới historical slot behavior.

## 5. Test và đầu ra

- Giữ assertion hiện có. NEW lifecycle test chứng minh actual owned child bootstrap/ready, memory auth/common-only (kể cả `/api/tat`, `{}` create/chay, download), same implementation, own DataRoot, stop/force-stop và foreign instance untouched; tests chỉ định dữ liệu DEMO, không dùng instance/dữ liệu/config/key thật của người dùng hay vô hiệu guard (vẫn dùng source CODE thật). Phân biệt mock với actual process/HTTP; Windows-only skip ghi rõ, không gọi skip là PASS.
- Existing client test thêm prior-marker + unconfigured URL UNKNOWN / fresh unconfigured clear; test qua CRM/M4 callers kiểm current rights vẫn trước side effects. Source native thêm slot invalid-string. Không chạy cả suite/M9/import source thật trong lượt code-only.
- **Lượt Claude này chỉ Read/Glob/Grep/Edit/Write**, không shell/import/AST/test/runtime/SQL/network/MCP/Agent/cloud, không xóa file. Root kiểm sau terminal rồi chọn actual owned launcher/HTTP/GUI; self-test ghi NOT_RUN đúng sự thật.
- Report existing ghi file đã sửa, lifecycle và filter thực có, phần còn thiếu; không tuyên bố GUI/accuracy/full CRM/M4 hoàn tất từ test cũ. Gói sau tiếp tục CRM G2/G3 và KCN/Nhà ở/E3/E5 theo hàng đợi, không mắc vòng sửa plumbing vô hạn. M2-00 rồi E1-MUA tuần tự sau CRM, M9 giữ dừng.
