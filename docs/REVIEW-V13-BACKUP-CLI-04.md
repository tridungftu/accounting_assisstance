# Review độc lập V13 backup04 — CLI và unit controls

**19/10/2026 — STATIC ONLY. Không còn blocker cụ thể trong diff CLI/unit vòng04 đã đọc.** Late-collision P2 của review03 đã được xử lý đúng ở source và có control operation thật; exact nonempty owned-partial inventory được kiểm. Đây là kết luận static/control-design, chưa là reviewer runtime hoặc PG04 acceptance.

## Input và pins

Frozen146: `var/codex-dieu-phoi/kiem-chung-20261018-101441/v13-legacy-backup04-handoff-20261019-140133-848/frozen`; manifest `../source-hashes.json` đã kiểm SHA256 `be1c388b86baa7554705d29d13f9fb7e86617cfe72404c04ab87af445694d4b3`. Root bàn giao actual terminal35645/exit0/c99c72, freeze910c97: exact hai product files thay đổi, 0 off-scope/missing/deletion. Reviewer đọc đầy đủ CLI/report04, targeted unit additions cùng diff so03 và hash các core/callers cần thiết; không thay root audit toàn146.

| File dưới frozen04 | SHA256 |
|---|---|
| `tools/sao_luu_pg.py` | `264ebee6026a489f80d2ca56176a565e44303b6bfadc4dc27a6f43694bb2e0b4` |
| `tests/test_v13_backup_safety.py` | `383455c0cf91d4d661cd70e30b55e9ba9e98c72a482e8f5406a4d4449fd65b75` |
| `docs/BAO-CAO-V13-LEGACY-BACKUP-04.md` | `9faef342c87b5a74c28e326c979a8c03da7bb7af378c4ceb1baefa9078c55f0b` |
| `src/kho_tri_thuc/ha_tang/sao_chep_bang.py` — giống03 | `cf0a0753ea09f4dedf0ae2ae26ba80f3bf6ac0a73cc67721c28219b81cb561c7` |
| `src/kho_tri_thuc/ha_tang/ket_noi.py` — giống03 | `a18d02e6370dcede8a7c4506e919c1c4df5643c9ad0c03dce9f812970452341d` |
| `src/kho_tri_thuc/ha_tang/an_toan_sao_chep.py` — giống03 | `d63bfd865367614d265dc07a3e86c2254923f62d592a4348eb5cbc506fef05a2` |
| `tests/test_v13_backup_safety_pg.py` — giống03 | `7c0802704dfbe527370f9ca457835b252a57d01d894d47f09bd9efd96446a396` |

Chỉ tạo review này. Không import/run product/tests/AST/SQL/CLI/process/HTTP/host; không đọc DSN/.env/secret/real rows/source apps, sửa inputs/M9 hoặc xóa artifact.

## F1/P2 review03 — closure source và control

**CLI:63–80:** precheck thấy final vẫn trả `DESTINATION_EXISTS`/`VA_CHAM_BEN_KHAC`. Riêng operation quyết định `os.rename:73` được bọc `except FileExistsError:74–76`: final bên khác được ghi True, own publish giữ False và business code `DESTINATION_EXISTS` được raise sạch `from None`. `da_cong_bo=True/DA_CONG_BO` chỉ đặt sau successful rename tại80. Không retry/replace/delete hoặc move rival/old partial. Cửa sổ rival xuất hiện sau precheck của03 không còn rơi vào lỗi KHAC không phân loại.

**Operation control: unit366–395.** Lưu original `_os.rename` trước patch (371). Wrapper chỉ chạy khi `_cong_bo` đã qua precheck, xác nhận final còn vắng, tạo rival nonempty rồi gọi chính saved rename (373–380). Assertion `goi == ['FileExistsError']` (385) đòi exception đến từ lần gọi rename thật; không chỉ stub ném exception. Kiểm exact business code, own False/other True/state collision, sanitized code; receipt chính xác `[partial/, partial/ban.sqlite, partial/ban.sqlite.sha256]` và không nhận rival (386–395). DB+SHA nonempty exclusive fixtures tại353–360, hai SHA256 trước/sau giữ nguyên; rival inventory/bytes được so trực tiếp (392–393).

Control tạo collision có causal ordering cụ thể ngay boundary và dùng Windows operation thật theo source. Đây là unit phối hợp trong một process, không hai OS processes. File DB/SHA ở control là DEMO byte fixtures (`DB_BYTES`, `SHA_BYTES`), nên phép đo chứng minh rename/ownership/inventory/byte preservation; việc valid SQLite backup/checksum/content qua cả pipeline thuộc controls khác.

Positive actual rename với DB+SHA (417–422) kiểm own True, state DA_CONG_BO, staging đã rename và final bytes nguyên. Control precheck collision cũ (333–343) vẫn giữ. Không thấy negative chỉ do helper luôn từ chối hoặc phải bỏ positive để xanh.

## Noncollision error / UNKNOWN / original failure

**CLI:77–79,95–119:** OSError khác được raise nguyên loại; state UNKNOWN thêm final vào `khong_xac_dinh`, kéo `kiem_ke=UNKNOWN`. Không map mọi OSError sang collision hoặc nhận ownership. Hai boolean phải được đọc cùng `trang_thai_cong_bo`: UNKNOWN không xác nhận final vắng/của ai. Metadata đã quan sát vẫn nằm trong `con_lai`; phần chưa đọc được tách riêng.

Unit397–415 ghi rõ injection PermissionError tại rename, đòi giữ original class, không có `ma=DESTINATION_EXISTS`, không leak message DEMO, own/other không True, state/inventory UNKNOWN và exact nonempty staging inventory. Test này chủ ý không gọi rename thật. Nó so DB hash trước/sau; collision/positive controls riêng so cả DB+SHA. Logic `sao_luu:133–140` vẫn bọc receipt error để giữ exception gốc; các unit metadata/receipt-failure controls424–440 giữ nguyên so03. Chưa thấy regression cụ thể ở failure paths được sửa.

## PG/source/publication và compatibility được giữ

Core/copier/utility/ket_noi và PG test hashes giống03. Vì vậy source-level R1 alias refusal trước write/COMMIT, actual-rowid fingerprint và same-PG-snapshot callback tiếp tục như review03; CLI04 `:146–151` vẫn readonly source open/callback, close/verify/SHA trước publish `:152–164`. Không thấy thêm PG/K2/M9 call hoặc migration/launcher/cleanup trong diff. Kiểm toàn source PG runtime không thuộc lần đọc này.

Known callers cũng giống03: `tools/dong_bo_dem.ps1` SHA `3d9486fc0158be4095da1e5d9e193b9b089ab4a87f4bc3c33c24f53dcddf1a27` và `tools/chep_v12_sang_pg.py` SHA `f55f6729cacddf1472338fe4e9fbd1bdc9f74e4a37c6c3fdb528c9ff5a5eac45` chỉ dùng exit code/output như review03. Trường lỗi thêm `trang_thai_cong_bo` chưa cho thấy break hai caller đó; không chạy caller hoặc đường --lam-lai/DROP hiện hữu. Consumer khác chưa được xác nhận.

Report04 dòng9–11 ghi coder **18/18 unit PASS**, 0 fail/error/skip trên Windows, có ResourceWarning; reviewer chưa chạy và không thay receipt runtime của root. Vòng04 không chạy PG; PG03 evidence chỉ áp cho exact unchanged core/test của03 và không được đổi tên thành PG04 retest. Existing PG N08 vẫn là in-process control/precheck collision như report04 đã nêu; unit late-collision closure không mở rộng thành actual child CLI acceptance.

**Khép residual F1/P2 của review03 ở mức static/control-design, không phát hiện finding mới cần giao sửa trong phạm vi04.** Giữ giới hạn Windows/no crash-durability claim, ordinary-role/actual child race/CLI/full restore/K2/V13/GUI chưa được nghiệm thu từ review này; không mở thêm framework hoặc cấp runtime/M9 authorization.
