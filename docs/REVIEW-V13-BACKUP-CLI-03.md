# Review độc lập V13 backup03 — CLI/receipt/call path

**19/10/2026 — STATIC ONLY.** R1 mất actual rowid đã được sửa đúng ở mức source. R2 đã sửa ownership, UNKNOWN inventory và bảo toàn lỗi gốc, nhưng còn **một P2 ở cửa sổ collision ngay trong rename**. Chưa nghiệm thu runtime hoặc toàn V13; finding này không thay quyền root chạy các controls theo release riêng.

## Input và phạm vi

Frozen146: `var/codex-dieu-phoi/kiem-chung-20261018-101441/v13-legacy-backup03-handoff-20261019-134511-250/frozen`; manifest `../source-hashes.json` đã kiểm SHA256 `08e5b5a9394d632d8c6c8e184cd5f08698decd5ee98f50c887c16b275a28ed19`. Root bàn giao terminal7921/exit0. Đọc đầy đủ CLI, phần copier rowid/snapshot/verify cùng call paths cần thiết, report03; xem targeted receipt/alias controls và hai consumer hiện hữu. Không audit thay review test/core toàn bộ.

| File dưới frozen | SHA256 |
|---|---|
| `tools/sao_luu_pg.py` | `01ce14dac7fd5b83edaf6e9862dc79a951566aa0035ba79af37525e7b128dc96` |
| `src/kho_tri_thuc/ha_tang/sao_chep_bang.py` | `cf0a0753ea09f4dedf0ae2ae26ba80f3bf6ac0a73cc67721c28219b81cb561c7` |
| `src/kho_tri_thuc/ha_tang/ket_noi.py` | `a18d02e6370dcede8a7c4506e919c1c4df5643c9ad0c03dce9f812970452341d` |
| `src/kho_tri_thuc/ha_tang/an_toan_sao_chep.py` | `d63bfd865367614d265dc07a3e86c2254923f62d592a4348eb5cbc506fef05a2` |
| `tests/test_v13_backup_safety.py` | `22d42031596d75cf8ea98fabb034df7284fa687f4c2de2b4bf082c5dc7deeb36` |
| `tests/test_v13_backup_safety_pg.py` | `7c0802704dfbe527370f9ca457835b252a57d01d894d47f09bd9efd96446a396` |
| `docs/BAO-CAO-V13-LEGACY-BACKUP-03.md` | `398ee0c189e67cecb7aaf80e7d8cb1050fe82de56c29b7a3a9cdcf6c7e19c070` |

Chỉ tạo report này. Không import/run sản phẩm/tests/AST/SQL/CLI/process/HTTP/host, đọc credential/.env/real rows/source app, sửa source/input/M9 hoặc xóa artifact. M5 amendment không thuộc review ưu tiên này.

## F1 / P2 — late destination collision chưa được ghi nhận là tài sản bên khác

**Vị trí:** `sao_luu_pg.py:63–71,86–88,121–128,178–180`.

`_cong_bo` chỉ đặt `final_ben_khac=True` khi `final.exists()` tại dòng 67 đã thấy đích. Cửa sổ còn lại: precheck trả False → rival tạo final → Windows `os.rename(staging,final)` tại dòng 70 từ chối vì đích đã có. Không có catch tại rename để phân loại collision. `trang` vẫn `(da_cong_bo=False,final_ben_khac=False)`; receipt giữ hai giá trị đó, còn `loi_sach(FileExistsError)` chỉ trả lỗi chung KHAC/kieu, không có mã `DESTINATION_EXISTS` (ket_noi.py:145–154).

Vì thế không còn nhận bundle rival là đã publish bởi mình và không ghi đè nó — hai điểm an toàn đã sửa — nhưng biên nhận phủ nhận/không nhận diện chính collision đã xảy ra ở operation quyết định. Đây là residual của yêu cầu R2 “final xung đột ghi rõ collision/bên khác”, chưa phải lỗi mất dữ liệu hay counterexample runtime đã chạy.

**Sửa hẹp:** xử lý lỗi destination-exists từ chính rename, giữ own-published=False, đánh dấu collision/bên khác và trả mã business phù hợp; không quy mọi OSError thành collision. Không retry ghi đè, move/delete rival hoặc partial. Nếu không xác định được cause/ownership từ lỗi/metadata, báo UNKNOWN thay vì khẳng định False. Thêm control cho rival xuất hiện **sau** precheck của `_cong_bo` và trước actual rename, giữ staging/rival bytes; không chỉ tạo final trước khi vào `_cong_bo`.

Các controls hiện có chưa đóng cửa sổ này: unit `test_final_ben_khac_khong_nhan_so_huu:333–343` tạo final trước hàm; PG N08 `:766–783` tạo final tại `_ghi_sha`, cũng trước precheck dòng 67. Ca publish OSError `:749–764` stub toàn `_cong_bo`, chỉ kiểm generic failure với `final_ben_khac=False`, không phải actual destination-collision control.

## Những điểm được sửa đúng ở mức source

- **R1:** `van_tay_pg:244–246` dùng actual PG `rowid` ở mọi bảng. `kiem_rowid_alias_pg:249–260` duyệt toàn `hop_dong()['alias']`, đếm `rowid IS DISTINCT FROM PK`, trả `PG_ROWID_ALIAS_LECH`; không sửa nguồn. Gọi tại `:312` ngay sau PG `BEGIN REPEATABLE READ READ ONLY:311`, trước seed DELETE/INSERT `:313–328`, SQLite COMMIT `:337` và CLI publish. Nội kiểm `:334` không còn thay actual rowid bằng alias. SQLite→PG vẫn ghi actual rowid từ SQLite và dùng cùng parity mới `:167–184`; không thấy thay đổi ý nghĩa positive biểu diễn được ở call path đã đọc.
- **Cùng snapshot/callback:** CLI `:134–139` vẫn mở source bằng `mo_nguon_sao_luu` và dùng independent SQLite reader mode=ro (`:45–49`); copier callback `:342–343` chạy sau SQLite COMMIT nhưng trước PG ROLLBACK `:344–346`. Alias guard, copy, nội kiểm và callback cùng RR snapshot, không có source reread từ snapshot mới. SQLite reader độc lập kết nối; không gọi đây là oracle độc lập hoàn toàn với thuật toán product.
- **Source read-only:** `ket_noi.py:249–264` không đổi hash so02; dùng `__new__/_mo_raw/preflight`, không `_migrate`/bootstrap. Lịch sử nguồn cũ/tương lai/lỗi vẫn bị từ chối bởi utility `:328–346`; normal upgrade ngoài backup giữ đường cũ. Không suy preflight lịch sử là chứng minh toàn physical schema nguồn.
- **Receipt ngoài F1:** `da_cong_bo=True` chỉ sau owned rename thành công (`CLI:70–71`); final chỉ kiểm kê khi own flag True (`:88`). Metadata error giữ confirmed entries, thêm `khong_xac_dinh/kiem_ke=UNKNOWN` (`:90–107`); lỗi bất ngờ trong receipt được bọc để re-raise exception gốc và báo UNKNOWN (`:121–128`). `loi_sach`/`_ma_loi` không in exception message/DSN/rows. Đây là closure source cho hai lỗi report02, với late-collision residual nêu trên.
- **Publication/retention:** staging/DB/SHA vẫn exclusive, content/integrity/close/SHA-verify trước một rename directory (`:40–71,111–155`); không explicit unlink/cleanup/rotate/move bản hay partial cũ; `--giu` báo không áp dụng (`:182–183`). Cam kết rename giới hạn Windows, chưa xác nhận portable no-clobber/crash durability. SQLite journal/checkpoint là lifecycle của tệp DEMO mới, không bằng chứng bảo toàn mọi sidecar của kho thật.

## Controls, compatibility và quyết định

PG N09 `:441–479` có actual INSERT explicit id100/50 tạo lệch identity, xác nhận precondition bằng direct SELECT, direct-copy refusal + snapshot nguồn/đích nguyên và CLI refusal/retained partial/old file nguyên. Positive N03 thêm direct actual-rowid comparison `:405–438`. Đây là controls có ý nghĩa theo source, **chưa reviewer chạy**. Report03 dòng 9–12 ghi coder 15 unit PASS, PG UNRUN do một Bash denial; root PG9/10 candidate02 không phải bằng chứng candidate03. Không tính mock-PG unit thành PG acceptance.

Hai consumers frozen chưa đổi: `tools/dong_bo_dem.ps1:33–35` (SHA `3d9486fc0158be4095da1e5d9e193b9b089ab4a87f4bc3c33c24f53dcddf1a27`) dùng exit code/output; `tools/chep_v12_sang_pg.py:82–86` (SHA `f55f6729cacddf1472338fe4e9fbd1bdc9f74e4a37c6c3fdb528c9ff5a5eac45`) dùng returncode. Chưa thấy break do receipt fields mới hoặc bundle path ở hai caller này; không chạy consumers, đặc biệt đường --lam-lai có DROP hiện hữu nằm ngoài runtime được giao. Unknown consumers/GUI không được xác nhận.

**Không còn P1 CLI/rowid cụ thể đã xác định; giữ F1/P2 trước khi gọi R2 hoàn tất.** Runtime rowid/receipt/PG controls cần root release riêng. Không xác nhận R3 test oracle toàn bộ, ordinary role, actual child race/CLI, full restore/DR/K2/V13 hoặc module M5/M9.
