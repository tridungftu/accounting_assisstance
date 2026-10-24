# M0–M5 candidate03 — HTTP/UI final static review

**FINAL_SOURCE_STATIC / NO_RUNTIME_PASS / NOT_ACCEPTED — 19/10/2026.** Root báo actual Claude35965 terminal0 `69e9ac`, freeze `d9ace8`. Reviewer chỉ đọc frozen/copy, so text/hash và viết review này; không product import/test/SQL/PG/HTTP/GUI/browser/node/CUA/process launch hoặc sửa product. Root chạy tests, m9 review SQL và root review service/bootstrap riêng; không suy các kết quả đó thành GUI proof.

## Final source và cách rebind

F = `var/codex-dieu-phoi/kiem-chung-20261018-101441/m0-m5-intake-ui03-handoff-20261019-172347-991-62d56e08/frozen/`. Whole210 manifest SHA `37b671d7869134b2c2552bbc913916fdec03f9a1218157e62c53acce3d58056a`, count210 kiểm từ metadata. Căn cứ handoff03 `c3e9ef21017ababea429cd10d530f9554ac7118c9ece6425a62f4d49473993de` và final02 review `188cd62b54e3d275bc16b5824d3615354f16aa548cc3d8745d061bad5831e055`.

| Final source | SHA256 / đọc trước đó và rebind |
|---|---|
| giao_dien/server.py ·956lines | `2e948604576486e1f153e5010ad00685dc11f275390b446eeb0c946be0d19c81` · M5 region433–570 + M9/common-region comparisons |
| giao_dien/assets/app.js ·918lines | `cc950ea963456655825ea583e9fa8eb43d095d68865473fdf14d0f479b28b5c8` · toàn M5 region672–918 |
| giao_dien/assets/index.html ·165lines | `94d52da8f6a23d28e7b1f87ebf9cd5228397135e1f06c059cffd0a3eec462779` · M5 form101–127 + prefix comparison |
| giao_dien/assets/style.css | `29a19358c8b3d87c5c88108eaeb0030f8697dceb1ffdf2422a16665c616631b0` · nguyên toàn file so frozen02 |
| k2/kho_so_luong.py ·728lines | `945aa0a2341c232c1441611490e8223122cfe9092d02cb34e729f3a24052540c` · selected detail480–550/mapping575–584/file597–695; không full service audit |

**Final server/app/index/service đều có SHA bằng interim và full-file text equality/diff rỗng** với bundle `m0-m5-repair03-interim-20261019-171708-007-a00c63bd` (snapshot `2e84c6cc6a48d0aefc7b0eeb1f24643f47464a89c9863e4d641fb00ca3662574`) đã đọc. Vì vậy line findings/closures trong private `INTERIM-FINDINGS-03.md` SHA `c0a4f448a0c920b62792396f2f634d67873a243cfd43522253079c0476f4d075` được rebind vào F, không lấy live source làm final. `pg_migrations.py` final SHA `f05753fdecd21d06d5524b5a43394eafd5982fcb06461bfd96e27a50fdebdcb9` khác interim; review này không đánh giá lại toàn SQL và không bê stale-SQL finding02 thành kết luận03.

## R1–R4: phần đã sửa cấu trúc

- **R1 actor-epoch sau refresh:** JS703 recheck sau `await m5Load`, trước return704. Callers sample770/mapping820/upload911 kiểm actor epoch; m5GioiHan805–807 đã guard success/error. Đường stale actor result trong final02 đã sửa ở source, không lặp nó thành finding còn mở. Còn form-context trong F1 dưới đây; causal browser test vẫn UNRUN.
- **R2 lựa chọn/claims trước FileReader:** clear685 actual file inputs/errors/key,691 clear source/coverage choices khi đổi vai/filter. Source/scope change890 xóa selections; input/change891–893 tăng form epoch. Submit899–904 chụp toàn claims và File objects trước await,905–906 check actor+form epochs. Refresh776–782 giữ scope/coverage còn hợp lệ, invalid selection clear. Đã sửa việc ghép pre/post-FileReader claims của02. ArrayBuffer→base64 ở710–717 vẫn giữ bytes, không parse/reserialize native; form-context sau POST còn F1.
- **R3 FILE operation key qua render:** Map680/727–730 giữ key theo actor/PN/phiếu/3pointers/basis837–840; re-render cùng tuple không tự sinh key mới. Nút explicit new operation842 thay key; basis đổi tạo tuple khác. Đường reset809 của02 đã sửa, nhưng actual same lo/bytes/cells sau refresh chưa chạy.
- **R4 expected basis:** service521/533 trả `co_so_file`, UI835/840 gửi `co_so_truoc`, server548–551 whitelist phiếu/key/expected-only, service607–616 fullmatch64lowerhex và chuyển vào preflight. Stage/result627–631 pin co_so_sha256; workbook có CO_SO657, raw capture rows658–661 và mapper669+ gồm mapping/content/observation/capture/master/measurement refs. Interface không còn chỉ3pointers; chưa coi completeness/current guard/replay/namespace SQL đã PASS. Preview coherence còn F2.
- Exact8 registry/server role change480–481/517–520, strict absent-error sentinel523–524, raw base64 decode537–540 và legitimate mapping targetPN543–544 giữ. Không blanket chặn target `phap_nhan` hoặc thêm quyền để positive qua. Source/PN/current-role negatives và actual cells/hash/token/session vẫn cần runtime riêng.

## Findings còn trên final

**F1 / P2 / tiếp I03-1 — source/form epoch không đi xuyên completion của POST.** `m5FormEpoch` thay đổi ở890–893, nhưng `m5Act`696–707 chỉ guard actor `m5Epoch`. Upload906 kiểm fe trước POST; sau await910,911 chỉ ep, catch912 cũng chỉ ep. Counterexample: đọc file xong dưới formF1→POST/refresh pending→người dùng đổi source/scope hoặc coverage/key thànhF2→old success/error/summary F1 vẫn có thể hiện trong contextF2. Đây không phải actor leak cũ; capture cũ có thể commit hợp lệ, nhưng kết quả không được gắn như phản hồi cho claims đang chọn mới. Bind form-current predicate qua upload completion/toast/error/refresh render hoặc flow không cho thay form trong request có trạng thái rõ. Không delete/rollback capture đã commit để chữa UI. Positive: unchangedform→receipt; negative: delay POST và delay refresh sau successful POST rồi đổi form, không chỉ delay FileReader. Chưa actual browser result.

**F2 / P1 conditional READ COMMITTED / tiếp I03-2 — displayed graph và token chưa bảo đảm một snapshot.** `chi_tiet`502–521 đọc root/versions/lines/observations/maps/tasks bằng các statements riêng, cuối mới gọi `m5_co_so_file(id)`521 rồi trả token533 cùng DTO đã đọc trước. Ở READ COMMITTED, một authorized independent DB/service connection có thể đổi mapping/proof giữa SELECTmaps515–517 và token521 trong khi3pointers giữ nguyên (ví dụ phiếu HOLD/eligibleNULL). DTO hiển thị old mapping/graph nhưng mang new token; next FILE gửi new token+same3pointers có thể chứng nhận basis chưa hiển thị. Getter STABLE chỉ coherent trong statement của nó, không làm các reads trước thành cùng snapshot.

Đây là **một shared finding** root đã độc lập ghi ở service review, không cộng thành hai lỗi. LocalApp mutation mutex serialize HTTP trong cùng instance; counterexample là independent connection, không claim actual HTTP exploit/race. Cần derive displayed DTO và token từ cùng coherent snapshot/lock đã có, hoặc thiết lập snapshot từ trước reads; không hash graph mới ở cuối rồi gọi đó là expected-preview binding. Same current graph/token positive vẫn xuất được; mapping/proof-only change với unchanged3pointers không được silently certify old display. Không đề xuất auth/engine/policy mới, chưa chạy reproducer.

## M9 và giới hạn nghiệm thu

So trực tiếp F với frozen02 manifest `3d5acde6e1327542aeca488c8d72599eef042c704dcf505b372165dead069906`: toàn server prefix trước M5 (bao methods M9), M9 GET/POST blocks, toàn JS prefix trước M5 và HTML prefix trước M5 đều text-identical; CSS toàn-file SHA bằng nhau. Chỉ xác nhận các vùng đã so, không thay SQL/seed review khác. **0 actual M9 calls**, không resume/sửa source tracking.

F1/F2 vẫn đúng final vì full-file equality nêu trên. Phần structurally fixed không được gọi runtime PASS; không lặp stale findings đã sửa. Root cần final DB/service/HTTP/picker/actor/delayed-response/file-cell/guard/retained evidence theo release riêng. Browser plan02 còn UNRUN; HTML/source assertions không thay GUI, HTTP pass không thay RLS/race/byte/cell oracle. Không nghiệm thu M0/M5/L11/full33 từ review này.
