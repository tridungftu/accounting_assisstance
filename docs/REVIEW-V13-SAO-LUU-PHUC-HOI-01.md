# Review độc lập cổng sao lưu/phục hồi V13 — 01

**19/10/2026 · STATIC_ONLY / TWO_CONTRACT_CLARIFICATIONS / NO_RUNTIME / NOT_ACCEPTANCE.** Đọc toàn `V13-CONG-SAO-LUU-PHUC-HOI-33.md` SHA256 **`52a2cafb3df8365650d89d67b9629f45ae94cf1ceb72647dfa2be2c6c3bd6f27`**, toàn frozen `backup.py/sao_chep_bang.py/tools/sao_luu_pg.py` và connection/restore guards liên quan. Source duy nhất CRM06 manifest `c828d1fff9593a0dce6d47e079df8adf76a4609cb936e2f1a627cf1a9948dd08`; không đọc live M9, source app, DB/real rows/secrets hoặc import/tests/SQL/HTTP/host/process/delete. Không amend input/product.

## Các claims source đã đối chiếu

Bốn SHA trong §1 khớp actual frozen bytes: backup `e28853902ad327d28e38b7b6cd6588ba6e0911a52714f45f6bd2f6ee271d7fea`; copy `cf39c0470635106647992c478fdf03a1ebe3991dacf3697b064070e6d94ef130`; connection `0ea269d5270c8519b304ae1c2a45d95405a3b5fd26b1dd67dbaa28edaea3bf36`; tool `aa6fd43ebdfa32cf9b52b9590fe7de5e372dfd78f790014b33af4e64f6831696`. Source claims đúng: backup API bundle SQLite+legacy artifacts và verify raw bytes/path/hash/length; copy chỉ legacy table set; CLI không pg_dump, dùng minute-name/fixed partial/unlink/move; manifest fixture_only/schema_version không proof nguồn; full K2 vẫn primitive/work gate riêng. Không có static claim này tự tạo runtime PASS.

## R1 — P1: Empty-target gate cần bao cả SQLite→PG, toàn legacy table set và cùng authoritative boundary

**Neo:** Contract§1/§2.4/B02/B06; frozen `ket_noi.py:233–235,460–488`; `sao_chep_bang.py:71–89,106–129,201–221`. Contract chỉ nêu rõ DELETE-target limitation PG→SQLite. Chiều SQLite→PG cũng DELETE toàn tables ở89 và ALTER identity modes **trước data-copy transaction** ở79–81, sequence changes ởfinally. `kiem_dich_phuc_hoi` trước filecopy và `_nap_neu_can` khi mở lại chỉ dùng hai sentinels `workspace_meta/attempts`, không chứng minh target business-empty.

**Counterexample cụ thể:** Một compatible migrated PG schema không có workspace_meta/attempts rows/marker nhưng có `cash_account_mappings` hoặc `knowledge_versions`. Preflight có thể coi trống; restore folder được publish, lần mở sau qua cùng predicate rồi helper xóa rows cũ để seed. Đây là static path, chưa runtime tái hiện. Advisory `mo-kho:<schema>` ở connection214–221 là điểm reuse đúng; kiểm lại hai sentinels dưới lock vẫn không đủ. Direct copy helper cũng không tự bảo vệ chỉ vì caller được khuyên “new target”.

**Amend tối thiểu:** Bind target-new/owned claim và kiểm **đủ49application tables** cho cả hai chiều copy, tại copy entrypoint/cùng authoritative lock boundary **trước ALTER identity/DELETE/COPY/DML/file publish**; guard restore preflight riêng vẫn giữ nhưng không thay late revalidation. Actual existence/content hoặc unsupported table/column set phải reject/holding, không gọi reset/copy vào target cũ. Bootstrap seeds phải allowlist exact fresh state: ví dụ `knowledge_epoch=(1,'initial')` từ `feature_migrations.py:114–115`, metadata schema-history đúng version/checksum; revision khác/extra rows không là seed. Không nới mọi metadata thành empty. Direct invocation và concurrent target change cần cùng contract, không monkeypatch/disable guard hoặc dùng privileged cleanup.

**Controls:** fresh migrated target với exact seeds positive; (a) target chỉ có cash mapping, (b) target chỉ có knowledge version, (c) changed seed/extra table/marker, (d) concurrent target creation/write trước seed đều reject0old-business/identity/sequence/file mutation hoặc đúng owned-new rollback contract. Same expected input qua supported safe-new path vẫn restore/open được. PG→SQLite nonempty control giữ như draft. Nếu interface không chứng minh guard/race boundary thì NOT_VERIFIED, không tạo negative bằng xóa target thật.

## R2 — P2: Legacy roundtrip hash phải phân loại marker/history, không false fail hoặc miễn toàn metadata

**Neo:** Contract§2.5/§3/B01–B03 yêu cầu exact rows/hashes nhưng chưa pin legacy metadata exceptions; frozen `sao_chep_bang.py:24–32,101–106,133–161,174–187`; `ket_noi.py:350–354`. Table set copy/hash thực có **49app tables**, `schema_migrations` là metadata table dựng riêng. Hash helper đã chỉ loại exact workspace key `DAU_NAP_XONG='v13_nap_tu_sqlite'`, không loại toàn workspace_meta.

**Counterexample:** Legacy PG backup mang marker giá trị luc_old; restore vào fresh PG copy ghi lại marker luc_new/tong_dong mới. Đây không tự là mất financial facts; nếu B02 bắt literal mọi workspace_meta bytes=source sẽ false fail. Ngược lại bỏ workspace_meta hoặc mọi metadata/timestamps có thể che entity/config/known-state/history sai. Schema migration applied_at của newly seeded legacy target cũng không cùng nghĩa với full K2 archive khôi phục chính source history.

**Amend tối thiểu:** Pin exact49table inventory từ MIGRATIONS và exact column/rowid/fingerprint rules; chỉ exclude marker value do restore tự sinh, kiểm riêng marker presence/shape/source-binding/one-time seed và no resurrection. Workspace entity/config/evidence metadata khác vẫn exact. Legacy regenerated schema history so exact version/checksum/allowed target-derived timestamps theo source schema contract, không ép source applied_at khi không copy history; full K2 pg_restore history/IDs/checksums/applied_at vẫn exact từ archive, không kế thừa ngoại lệ legacy. Không dùng count49/50 hoặc stored hash làm proof nội dung.

**Controls:** Legacy SQLite→PG→SQLite→freshPG giữ toàn business values/PK/rowid/source refs, marker-only expected delta được báo rõ; tamper entity/config/nonmarker meta hoặc migration checksum phải fail. Full-K2 history tamper vẫn fail; không green vì marker đang đúng. Đây là bổ sung oracle trước run, không sửa expected sau output.

## Phần nên giữ và bước đóng review

Giữ phân biệt legacy fallback/full K2/full role+encryption+filesystem scope, fresh retained DB/no-clean, no overwrite/partial retention, ordinary-role use-after-restore khác owner inventory, source snapshot+immutable file refs, PENDING_FILE/recovery và native sidecar boundary đúng grain. B01–B08 đều NOT_RUN; GUI/host/cold/DR/new-host/key recovery chưa có evidence không tự đạt. Future final-M9 inventory/release/runner/tool hashes và source freeze vẫn bắt buộc; không runtime từ review này.

Root amend R1/R2 rồi closure final SHA trước implementation/release; không cần mở lại accounting policy/kiến trúc hoặc tạo app backup mới. Review này chỉ tạo tài liệu, không chứng minh backup/restore đã chạy hoặc kho thật đã an toàn để chuyển.
