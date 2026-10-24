# Giao sửa V13 legacy backup — 04

**19/10/2026 — READY_FOR_ROOT_DISPATCH; chưa nghiệm thu.** Chỉ sửa residual atomic-rename collision của CLI; không mở kiến trúc/phạm vi khác. Chỉ thực thi khi root dispatch cùng session hiện có.

## 1. Input và bằng chứng

Candidate03 terminal7921/exit0; frozen146 `var/codex-dieu-phoi/kiem-chung-20261018-101441/v13-legacy-backup03-handoff-20261019-134511-250/frozen`; manifest SHA256 `08e5b5a9394d632d8c6c8e184cd5f08698decd5ee98f50c887c16b275a28ed19`. Root unit03 **15/15 PASS**; actual PG03 handle12238 **terminal0 theo e9f9e5:11/11 PASS,0fail/error/skip,190.319s**. Summary SHA `17afb4385854441c6ac46414cc5f503182e9c5ba3270861811e15c6d52e459aa`; source146 nguyên,20explicitresolver/0forbiddenK2-M9calls, newlocalDEMODB retained. Root đã full-read 3reviews03 và toàn bộ code/test diffs. Actual Store backup/restore/reopen và rowid refusal/target preservation được suite này kiểm; đây vẫn là coder-authored suite root chạy, không ordinary-role/actual childCLI/fullV13 acceptance. Không Read var để đọc receipts. **Vòng04 không chạy lại full PG**, chỉ sửa và kiểm receipt unit vì core/PGtests giữ nguyên.

Căn cứ `docs/REVIEW-V13-BACKUP-CLI-03.md` SHA `bf5d9825369e30a3b3e8b27abbf4de7c6f1909967302626e0725dc7aa0343153`, F1/P2. CLI frozen03 SHA `01ce14dac7fd5b83edaf6e9862dc79a951566aa0035ba79af37525e7b128dc96`; unit SHA `22d42031596d75cf8ea98fabb034df7284fa687f4c2de2b4bf082c5dc7deeb36`. R1 actual-rowid/same-snapshot/source-readonly/publication order đã có cơ sở static; không sửa lại chúng để xử lý lỗi receipt này.

## 2. Tối đa ba write targets

- `tools/sao_luu_pg.py`
- `tests/test_v13_backup_safety.py`
- **Mới:** `docs/BAO-CAO-V13-LEGACY-BACKUP-04.md`

Core/copier, PG test, utility, ket_noi, schema/migrations, dependencies/Store/config/launcher và mọi source ngoài ba file giữ nguyên. Không sửa reports01/02/03, reviews/đầu bài/ledgers, corpus/private probes, runner/guard/policy/dispatch. Không làm M9/source app/M5/K2/Google/HTTP/UI/service hoặc kho thật; runtime chỉ fixture SQLite/DEMO của unit được root release, không mở framework hay thêm format backup.

## 3. Sửa hẹp tại operation quyết định

Frozen03 `_cong_bo:67–71`: final.exists() có thể False, rồi rival tạo final trước os.rename. Windows actual rename từ chối đích tồn tại, nhưng chưa có catch nên `final_ben_khac=False`, lỗi chung KHAC thay `DESTINATION_EXISTS`.

Xử lý **FileExistsError từ chính actual os.rename**: trả business `DESTINATION_EXISTS`, own `da_cong_bo=False`, `final_ben_khac=True`; chỉ nhận own publish sau rename thực sự thành công. Giữ staging và rival nguyên, không kiểm kê rival như tài sản của run. Không retry overwrite/replace, không xóa/move/rotate bất kỳ old/rival/partial nào.

Các OSError khác giữ loại/mã lỗi gốc đã sanitize; không gom PermissionError/I/O failure thành destination collision. Khi không đủ metadata để xác định trạng thái, ghi UNKNOWN rõ thay suy absence/collision hoặc nhận ownership. Giữ logic UNKNOWN inventory, bảo toàn original failure, không lộ exception message/DSN/rows/traceback. Không sửa core/source để làm unit xanh.

## 4. Regression controls nhỏ, có operation thật

- Tạo retained DEMO staging độc quyền, **DB+SHA đều nonempty** với bytes/hash biết trước; rival bundle có bytes khác. Cho rival xuất hiện **sau precheck `_cong_bo` nhưng ngay trước actual os.rename**, rồi gọi chính Windows rename. Có thể wrap điểm gọi để phối hợp fixture, nhưng giữ hàm rename thật và chứng minh nó đã được gọi; không chỉ mock ném FileExistsError hoặc tạo rival trước khi vào `_cong_bo`.
- Đòi exact business code/flags trên; own partial inventory chính xác gồm directory+DB+SHA, không chứa rival; staging DB/SHA và rival bytes/hash giữ nguyên, không published success. Giữ positive owned rename success và collision được thấy ngay precheck.
- Control noncollision OSError (có thể inject PermissionError tại rename): không báo `DESTINATION_EXISTS`/khẳng định rival từ lỗi đó; own publish không True, original sanitized failure và UNKNOWN phù hợp, artifacts giữ nguyên. Giữ unit metadata/iterdir UNKNOWN + lỗi receipt không thay lỗi gốc và các controls15 hiện có; không bỏ/đổi expected để hợp output sai.

## 5. Thực thi và bàn giao sau root release

Runtime04 chỉ selected SQLite/component unit dưới đây, với system Python/guard/no-bytecode do root bind. Không chạy PG, suite khác, product CLI độc lập, SQL ngoài fixture SQLite của unit, HTTP/host/source app; không đọc var/runner/.env/credential hoặc dump env. DRAFT này chưa cho phép chạy:

```text
python -X utf8 -m unittest discover -s tests -p test_v13_backup_safety.py
```

Nếu tool/policy chặn, báo UNRUN và dừng đường đó; không đổi shell/settings/guard để vượt deny. Không delete/cleanup file/temp/DB/role/attempt, không DROP/reset/clean/commit; giữ tất cả failed artifacts. Báo cáo04 nêu exact diff, controls operation thật so với injection, PASS/FAIL/UNRUN/skip và giới hạn Windows/static/không PG. Kết thúc CLI để root freeze/review riêng; không tự nghiệm thu V13/33 hoặc bắt đầu việc khác.
