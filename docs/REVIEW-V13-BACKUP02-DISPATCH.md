# Review độc lập dispatch V13 backup02

**19/10/2026 — STATIC_ONLY. Đủ điều kiện gửi auto-review cho dispatch hẹp đã được root ủy quyền; không phải runtime acceptance.** Đã đọc handoff/settings/helper/retained runner và technical manifest/guard-loader metadata. Không chạy helper/Claude/product/tests/SQL/CLI, đọc .env/credential/source-app data, sửa inputs hoặc xóa file.

## Exact inputs hiện hành

| Artifact | SHA256 hiện tại |
|---|---|
| `docs/GIAO-SUA-V13-LEGACY-BACKUP-02.md` | `6c1973b830ce7ce71e461ea3bf4e96527eb852cd5c9d83dc4b3d15bba5e5f163` |
| `var/codex-dieu-phoi/claude-v13-legacy-backup-settings-20261019-02.json` | `b500ab46a8b75e0eaf6e41c4628024da36bc61ab90b69a644f458b13a5a8f07c` |
| `var/codex-dieu-phoi/dispatch-v13-legacy-backup-02-20261019.ps1` | `9efce183c0802dbbcab50979c991413b2ace4854ba7bc4de2a6651efbeea6b0b` |
| Before-source146 `source-hashes.json` | `da3f41f317efebd3d00246b9ec845b2ff612743c8176f7f4c81fc3256fd75e72` |
| `run-pg-tests-retained.py` | `9ea31579b154716f9ef87761fec9d410a09c3c40da8be8c7222e83526ce4002e` |

Helper ban đầu618a, sau pathset-fix20f0 và pin-settings89d1 được supersede bởi9efce; settings4c39 được supersede bởib500. Root giữ lịch sử trước sửa, gồm `dispatch02-before-pathset-fix-20261019-123359-567/` và `dispatch02-before-process-filter-fix-20261019-124546-807/`; review không xóa/ghi đè lịch sử.

## Phạm vi và các điều kiện đã khép

- Handoff chỉ bảy write targets: ba legacy guard/copy/connection files, CLI backup, hai test files và **report02 mới**. Report01/reviews/independent probes/migrations/K2/business sources/launchers/config/dependencies/source apps giữ nguyên. R1 physical schema, R2 sequence rollback và F1–F7 là sửa đúng finding hiện có; không thêm engine nghiệp vụ hoặc mở lại kiến trúc.
- M9 không được resume sửa; chỉ root giữ phạm vi nhận diện cách lấy dữ liệu từ app hiện có. Không giao tiếp tục M9/cutoff/M5/source #10/Google/cloud/real approval. Kho thật vẫn SQLite; runtime chỉ new retained DEMO `kho_test_*` resources, không cleanup.
- Helper pin full146 source bytes, kiểm full pathset (đã thêm `pyproject.toml`), report02 chưa tồn tại và không có Claude CLI process trước dispatch; tạo source/input backup và so hash trước khi launch. Root báo readonly preflight **146/146 paths,0 hash delta,0 path delta, parser0errors, active CLI0, report02absent**; helper còn kiểm lại lúc thực thi. Auto-review lần đầu đã cho dispatch chạy nhưng helper cũ dừng ngay process gate trước backup/coder vì đếm nhầm9 Claude Desktop WindowsApps. Root báo readonly CIM xác nhận toàn Desktop; không dừng process nào. Bản9efce chỉ lọc CLI executable đúng user-local bin/share path bằng CIM, giữ Desktop; tôi đọc lại predicate và hash, không chạy process gate. Root retry riêng cùng bounded scope; chưa có coder/runtime result trong review này.
- Blocker read-source-app ngoài scope đã được root sửa: settingsb500 có `blockReadsOutsideWorkingDirectories=true`; absolute Read deny cho hai original source-app roots, global `.env*` và home secret directories; bỏ bare Glob/Grep allow. Paths Windows dùng POSIX-normalized lower-case drive. `Read` là rule dùng cho file-tool access; không dựa riêng vào path-scoped `Write/Glob` rules để chứng minh fence. [Claude permissions](https://code.claude.com/docs/en/permissions#read-and-edit).
- Seven Edit allows khớp handoff; deny protected core/migration/nguon/K2/var/env/Git. Hai explicit Bash selftest allows đúng commands đã giao, không mở arbitrary `python -c`/shell đổi policy. `--safe-mode`, `--permission-mode dontAsk`, builtin tool list và strict empty MCP không thêm connector/Web tools. Helper xác nhận settingsb500 trước launch, MCP server map rỗng.
- System Python3.13 PATH, PYTHONUSERBASE/no-delete/no-bytecode/UTF8/PYTHONPATH được bind; clear storage override và inherited test DSN. Guard pin a517c535…3a229; `.pth` hiện có `import codex_no_delete_guard` (SHA21756585…c818b9). Retained runner assert guard/module/userbase, nạp credential **local process**, hardcode loopback endpoint, giữ new DB/test artifacts và redact password/DSN trước output. Claude không được Read runner/var/.env; quyền execute exact retained command là quyền riêng đã cấp. Tôi chỉ đọc source runner, không đọc credential file mà runner tham chiếu.
- Outside-filesystem-sandbox execution là yêu cầu dispatch kỹ thuật hẹp để khắc phục MSYS startup đã được root chẩn đoán. Không dùng bypassPermissions hoặc cho Claude tự đổi sandbox/guard/runner/whitelist. User authorization về local file access không được mở thành quyền gửi original source apps hoặc real rows/bí mật sang Anthropic.

## Giới hạn kết luận

Không còn blocker cụ thể trong ba input hiện tại để root gửi **auto-review**. Đây không phải kết quả của automatic approval reviewer và không tự cấp quyền launch. Policy/tool rules và Python guard không phải chứng nhận OS sandbox hay ngăn mọi hành vi của Python test code; root vẫn phải giám sát đúng hai selftest commands, freeze/review toàn source sau Claude terminal và xử lý mọi file ngoài scope.

Không nâng unit7/7 component có fake-PG thành end-to-end, không dùng report/exit0 làm acceptance. Selftests sau sửa, current-candidate PostgreSQL probes/actual races/CLI, source/old-artifact preservation và root fatal-profile/watchdog binding đều cần receipt riêng. Private glue02b663 vẫn false/not released; review dispatch này không đóng findings của race harness hoặc nghiệm thu V13/full33.
