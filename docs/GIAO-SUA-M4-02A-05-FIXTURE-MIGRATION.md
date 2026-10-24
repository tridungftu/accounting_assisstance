# M4-02A FIX05 — Sửa fixture nâng migration 19 lên 20

**Lượt sửa test-only hữu hạn, CODE_ONLY; kế thừa code hiện có, không thay product hoặc migration.** Task `M4_02A_L1_L2_FIX_CODE_ONLY05`, cùng Claude session đã được Root điều phối.

## 1. Căn cứ đã chạy thực

- Native21 của Root, actual18201/58a81f: K2 chạy14 ca,13PASS/1FAIL/0ERROR/0skip; duy nhất R00 lỗi tại test_m4_review_k2.py dòng282. HTTP7/7PASS/0skip. Process/Job đã dừng và source435 trước/sau giữ nguyên hash; không gọi cả21ca PASS.
- Nguyên nhân setup: R00 gọi `pg.migrate(c,19)` rồi `crm_demo.khoi_tao(c)`; helper CRM ở dòng44 gọi migrate default20, nên biến lịch sử dự định chụp tại19 thực tế đã có20. Đây là lỗi fixture kiểm nâng cấp, không phải bằng chứng product migration thất bại.
- Independent M20 actual53940/2f4ec6 đã PASS: có nonempty draft tạo qua ordinary public APIs; nâng19→20 bảo toàn toàn bộ old rows/sequences/files/catalog ngoài đúng function body và row history20; migrate lại whole-zero; sáu fresh owner read-only calls đúng SOAN/NULL/domain P0001. Đây là kiểm hữu hạn, không fullM4/GUI acceptance.
- Migration1–20 đã được áp dụng vào các DEMO retained và sealed; không sửa SQL, checksum, registry hoặc helper product để làm xanh test.

## 2. Sửa duy nhất setup của R00

1. Chỉ trong `M4ReviewPG.test_r00_nang_19_len_20`: bỏ lời gọi CRM seed gây auto-upgrade. Không gọi helper khác có thể tự migrate; không sửa `crm_demo.khoi_tao` hoặc product.
2. Sau `pg.migrate(c,19)`, kiểm schema version19 và đúng lịch sử versions1..19. Dựng đúng hai fixture pháp nhân `PN_DEMO_A`/`PN_DEMO_B` bằng schema hiện có, với nhãn DEMO; không seed CRM/M9, không tạo hồ sơ đã duyệt hoặc quyền giả để bỏ qua service.
3. Gọi actual `m4_demo.khoi_tao(c)` và assert trạng thái `DU`. Kiểm lại schema19/versions1..19 ngay sau seed, trước khi chụp `ls19`, counts và ACL. Mục tiêu là bảo đảm baseline nâng cấp thực sự dừng ở19.
4. Giữ nguyên mọi oracle còn lại của R00: checksum/identity/history1–19 và applied_at bất biến, default lên20, row20 checksum đúng, dữ liệu/ACL/chủ sở hữu/SECURITY DEFINER/STABLE/search_path giữ nguyên, migrate lại20 whole-zero theo các kiểm hiện có và function M20 thực sự được áp dụng.
5. Giữ nguyên13 method K2 khác và toàn bộ HTTP7, pure/DOM/guard, mọi assertion/expected/code domain. Chỉ bỏ import CRM cục bộ của R00 nếu không còn dùng; không thay class setup hoặc helpers phục vụ ca khác.

## 3. Hai đích sửa chính xác và giới hạn

- Existing `tests/test_m4_review_k2.py` — chỉ fixture/setup R00 nêu trên.
- Existing `docs/BAO-CAO-M4-02A.md` — thêm phần FIX05, nguyên nhân fixture và thay đổi đã viết; self-test `NOT_RUN_CODE_ONLY`.
- NEW0; source367 giữ367,365 existing còn lại được bảo vệ. Không sửa product, migrations1–20, vendor/reference, CRM/M9, guard, UI/API hoặc các tests khác. Không xóa, rename, move, reset hay cleanup file/DB/roles; giữ mọi bằng chứng và lịch sử.
- Chỉ dùng Read/Glob/Grep/Edit/Write theo settings; không Agent/Task/Skill, Bash/lệnh, import/AST/Python/Node/test/SQL/HTTP/network/browser/Office/launcher. Không đọc var/.env, credentials, dữ liệu thật, sourceapps hoặc oracle riêng của Root.
- Coder chỉ viết code/report và dừng. Root kiểm diff/hash sau actualterminal rồi mới quyết định chạy lại test hữu hạn; không tự tuyên bố runtime/fullM4/GUI PASS.
