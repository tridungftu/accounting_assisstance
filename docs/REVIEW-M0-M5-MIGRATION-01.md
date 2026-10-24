# Review độc lập COMMON13 / M5 14 — candidate01

**19/10/2026 — STATIC_NOT_RUNTIME / CHƯA ĐẠT ĐỂ NGHIỆM THU DB.** Chỉ đọc final đã đóng băng; không sửa product, import/run product, áp SQL, chạy PG/HTTP/GUI hoặc M9 trong review này. Các đường lỗi dưới đây là kết luận từ control flow/DDL, chưa phải kết quả tái hiện trên PostgreSQL.

## 1. Candidate và bằng chứng

- Actual terminal Claude `77423`, exit0, tool `6e1b6c`; receipt SHA `27b6946161970312489749d5d3ea601548db1ee6fe384ee0efb8028698b024cb`.
- Frozen: `var/codex-dieu-phoi/kiem-chung-20261018-101441/m0-m5-intake-ui01-handoff-20261019-155812-863-45941662/frozen/`; manifest210 SHA `c36773ae0b147665dab725b875c61dc7708037b23df806e5bb507079d2f2b89a`. Root freeze ghi 0 offscope/missing/fixture/protected drift.
- `src/kho_tri_thuc/ha_tang/pg_migrations.py`: 3958 dòng, SHA `84ad70a2e44044e9338f1fba986e0822dce9072e7fa79292354e78ca2d5ef064`; `postgres.py`: 210 dòng, SHA `9f4abf60043cafd210f069d9e708e84296129ae041905934ddff0adb1ec09c09`. Mọi line anchor bên dưới thuộc đúng frozen này.
- Report coder `BAO-CAO-M0-M5-INTAKE-UI-01.md` SHA `65d3ed2a48d801e5f4a9c03fdabba4c61d6dd8d15bfa48d9983eb0e0ac5cb262`; report không thay bằng chứng runtime.
- Interim `m0-m5-interim-schema-20261019-153835-510/findings-static01.json` SHA `4bdc0fdb119462fa725500c20f48f7508b489f40f9ea83706f8a467604b30814` được giữ nguyên. Đã rebind toàn bộ findings vào final; chỉ hai thay đổi SQL so interim: bỏ hai lý do đảo khỏi blocklist3526–3527, trả thêm latest_observation_id3727.
- Root actual 11 pure-component tests PASS, 0 fail/error/skip, source210 nguyên/guard0 forbidden; `m0-m5-root-pure01-08aee5053b1e/summary.json`. Không PG/HTTP/GUI; không chứng minh các đường SQL dưới đây.

## 2. Lineage: phần đã xác nhận, giới hạn

Review AST final theo raw UTF-8-sig xác nhận 23 historical definition segments nguyên và default registry chỉ prefix1–12 + COMMON13 + M5 14, không tham chiếu historical full-M9 helpers trong unit mới. Root kiểm definition-only cùng candidate, 0 connections/0 SQL applied: prefix1–12 SQL checksums nguyên; legacy M13 vẫn `2a2acb81bc85f57a5643a4736528d120f9f48ee1d005ad8bec0a178ba1926d40`.

Root pins `m0-m5-root-pure01-08aee5053b1e/sql-definition-pins.json` SHA `430302f522cb5476d7bc5a410f6d8b4f9575d2425bdd48bb35d9f0fa9d768ea4`: COMMON13 52 statements SHA `b396ce05fe525006d6dde3ec6d4b1a87d3b40f4cca8de98d462471919d3be4b5`; M5 14 24 statements SHA `31f3db6ad752932eb9e9280709af2a1264a44e6f5c11d7d9184f6c0d844d73cd`. Đây là definition preservation, chưa có catalog/grants/DDL execution evidence.

## 3. Findings cần đóng trước nghiệm thu DB

**S01 / P1 — capture H và bundle do caller tự khai có thể thay sự thật đã kiểm.** `giao_tiep.nguon_ghi_lan_nhan(jsonb)`3325–3411 là definer, app_web được EXECUTE3514. Retry3336–3340 chỉ so hai H caller gửi; không bind lại H với envelope/role tuple. Snapshot3368–3370 chỉ lookup bundle_sha caller gửi; khi tồn tại thì bỏ qua đối chiếu/ghi roles và rows3371–3404. Vì vậy actor INTAKE hợp lệ có thể gọi SQL với role/master khác nhưng H cũ để replay, hoặc bundle cũ để gắn lại master cũ. Python validation không đóng cổng JSON definer trực tiếp này; report95 tự xác nhận giới hạn nhưng contract không miễn trừ DEMO.

**S02 / P1 — typed promotion không được bind với kết quả reader đáng tin.** `kho.m5_ghi_quan_sat(jsonb)`3760–3851 / grant3939 nhận semantic/status/native/quantity/unit/precision/classification/history từ p. Header3797 và lines3815 chỉ xác nhận locator thuộc snapshot; các facts insert3803–3810,3819–3823,3827–3831 không so equality với source rows/proof đã resolve. FK đúng snapshot không chứng minh quantity/ID/status đúng nguồn. Cần chặn việc app trực tiếp tự khai typed facts; không nhân bản reader thành engine SQL.

**S03 / P1 — thứ tự khóa intake/review đảo nhau.** Intake3782 lấy advisory PHIEU_KHO rồi row lock3786; review3882 lấy row lock rồi advisory3886. Hai connection có thể mỗi bên giữ khóa thứ nhất và chờ khóa bên kia. Dùng cùng domain lock order; actual causal race phải có positive+observer, không lấy timeout/error làm PASS.

**S04 / P1 — review có thể lùi accepted/eligible bằng quan sát cũ.** Review3887–3889 kiểm expected current pointers, nhưng3891–3892 cho chọn bất kỳ observation cũ cùng phiếu. Old A từng có classification hợp lệ vẫn qua3900;3904–3905 khôi phục eligible A dù latest/accepted đã là B đảo, nếu caller gửi expected refs B hiện hành. Cần ràng buộc event/transition được review để không dùng lại old good A thay bằng chứng nguồn mới. Subfinding interim “không chấp nhận được B đảo” đã đóng tĩnh nhờ3526–3527; B có thể accepted với eligible NULL. Điều này chưa đóng stale-A path.

**S05 / P1 — master tồn tại nhưng thiếu history bị coi fresh trước marker check.** `postgres.py`89–91 trả version0 ngay khi thiếu schema_migrations; bỏ qua marker94–97 rồi migrate167–171 tạo/ghi schema/marker/history. DB partial/foreign có master nhưng thiếu history phải từ chối trước ghi; fresh chỉ dành cho DB đã xác minh trống. Chưa chạy DB reproducer.

**S06 / P2 — custom migrations chỉ kiểm số phần tử, chưa whitelist historical units.** `postgres.py`156–158 cho mọi tuple ≤12; có thể gộp historical M13 SQL vào một phần tử trong tuple12. Đây là bypass hook trái yêu cầu “chỉ historical prefix”, không phải default registry tự cài M9. Cần exact known-prefix validation hoặc loại hook khỏi đường release; giữ checksum lịch sử nguyên.

**S07 / P1 — mapping V4 hợp lệ thiếu quyền gọi helper từ trigger INVOKER.** Trigger3229–3231 không SECURITY DEFINER, gọi `master.anh_xa_nguon_noi_bo`3264; EXECUTE helper bị revoke PUBLIC3475 và app_web grants3513–3515 không cấp lại. Ordinary app CFO/source-map hợp lệ dự kiến bị permission denied ở nhánh dương, trong khi owner seed không thấy lỗi. Cần internal trigger call path có thẩm quyền đúng, không mở helper chéo PN tùy ý. Chưa có PG positive counterpart.

**S08 / P1 — source metadata không theo source-cap scope.** Grant SELECT3494 mở cả instance/profile/configured scope/master-hash/measurement payload cho mọi app_web; RLS3480–3488 không gồm các bảng này. M5-only/M1-only viewer có thể xem metadata nguồn A/B, trái contract§4.62. Không kết luận có đọc raw bytes. Ngoài ra prefix902–911 có inherited default ACL cho app_ke_toan/app_doc/app_cong_ai nếu roles tồn tại; bảng config mới không RLS và revoke3495 chỉ nhắm app_web. Cần kiểm/revoke inherited ACL trên chính objects mới, nhất là quyền INSERT profile/proof của legacy app_ke_toan; không thay quyền legacy objects để che lỗi.

## 4. Phạm vi còn thiếu và hướng sửa hẹp

Core projection PHIEU_KHO đã được handoff§5.62–63 và binding R3 yêu cầu nhưng chưa thực hiện: core refs3573/3610 nullable, không có core INSERT/owner discriminator; coder report87 xác nhận. Giữ đây là phần triển khai còn thiếu trong scope, không coi NULL refs là nghiệm thu lát cắt này. Cần owner neutral bảo toàn legacy CRM/M1, core quantity-only dùng ngày thật và R3 key từ content đã dedup; không fake amount0 hoặc V1 journal.

Đề xuất đóng S01/S02 bằng common immutable trusted-stage: chỉ server privileged configured connection được ghi stage, app/source-integration không được ghi/đổi; stage giữ exact artifact graph/H + reader/facts/history đã kiểm, consumer chỉ nhận stage_ref/expectedH. Recheck session/current caps/capture key dưới cùng transaction và thứ tự khóa thống nhất trước stage/artifact delta; chỉ reuse existing private connection pattern, không dựng auth/parser mới. Quyền owner không thay guard actor hiện hành. Kiểm ordinary direct-SQL positive/negative, bundle-collision/retry, metadata isolation và stale-review bằng retained DEMO sau root release; generic exception, rỗng hay timeout không đạt.

Không có runtime acceptance cho COMMON/M5 DDL/RLS/capture/review/race/core/API/UI trong tài liệu này. M9/source apps/kho thật không chạy hoặc chỉnh. Giữ nhãn candidate01 CODE_WRITTEN_WITH_BLOCKERS; pure reader DEMO đã kiểm trước đó không bị suy rộng thành full M5.
