# CRM neutral compatibility 01 — handoff CODE_ONLY

20/10/2026. Task `CRM_NEUTRAL_COMPAT_CODE_ONLY01`; Root đã chọn OptionA: khôi phục compatibility CRM/M1 đã có, không mở kiến trúc/nghiệp vụ mới. Claude chỉ đọc/ghi file bằng năm file tools được cấp; không chạy shell, Python, import, AST, tests, SQL, HTTP, browser, launcher hoặc process. Self-tests phải ghi NOT_RUN; Root chỉ release runtime sau actual terminal, freeze và FULL independent review.

## 1. Baseline và vấn đề cụ thể

Root pin baseline hiện hành 273 source, manifest SHA `d483184e9e48e4698db43a4d8085c8f417ad76bd22934e217282ef117e0ed299`; mọi file ngoài allowlist giữ nguyên. Đây là diagnosis tĩnh, chưa phải một runtime failure mới.
- `src/kho_tri_thuc/k2/crm.py` SHA `71027f1df9959d352d2b69594fb76794c8602a091bce61209c0b7dd5511acb9c`: `danh_sach` dòng771 gọi `kho.tien_con_lai`.
- `src/kho_tri_thuc/giao_dien/server.py` SHA `218f50b0ff194f63c680f6f4574845c5348c8f7c91bcc3a864e1454d24deb0e3`: `crm_m1_sao_ke` dòng330 gọi `_ghi_proof_tien` sau ingest/projection.
- Các object tiền đó thuộc constant legacy full-M13, không nằm trong default prefix1–12 + COMMON13 + M5/M2/L11 hiện hành. Không cài legacy-M9, alias checksum hoặc thay default registry để chữa CRM.
- `m1_demo.ghi_proof_tien` còn tham chiếu `kho.chung_tu_tien_encoding`/`kho.ghi_proof_tien_noi_bo`. CRM route hiện có thể lỗi sau khi projection đã commit; HTTP lỗi không chứng minh toàn pipeline đã rollback.

## 2. Exact write allowlist — chỉ bốn file

1. Existing `src/kho_tri_thuc/k2/crm.py` — chỉ read-query hunk trong `danh_sach` nêu ở §3.
2. Existing `src/kho_tri_thuc/giao_dien/server.py` — chỉ return hunk của `crm_m1_sao_ke` nêu ở §3.
3. NEW `tests/test_crm_neutral_compat.py` — regression có ý nghĩa, self-contained, DEMO thật như §5; không sửa test cũ.
4. NEW `docs/BAO-CAO-CRM-NEUTRAL-COMPAT-01.md` — changed files, behavior, test definitions/NOT_RUN và limits.

Không sửa handoff này, reports cũ, fixtures, config, source apps, dữ liệu thật hoặc bất kỳ file khác. Không xóa, move, cleanup/reset file/DB/role; tests cũng không DELETE/DROP/TRUNCATE, kể cả ca âm/rollback.

## 3. Hai thay đổi production bắt buộc

R01: Trong `CrmK2.danh_sach`, thay duy nhất subquery tính `da_noi` bằng historical CRM read: `SELECT coalesce(sum(k.so_tien_khop_minor),0) FROM kho.lien_ket_chung_tu k WHERE k.chung_tu_a_id=c.id AND k.trang_thai<>'HUY'`. Giữ alias/shape `da_noi`, lọc BANK/THU/pháp nhân, outer request identity/M1 scope và transaction như hiện tại. SUM các active parent theo chính BANK, không lọc chỉ một hợp đồng, không cộng child quantity; NULL financial amount của evidence không thành tiền. Không gọi helper legacy, không catch UndefinedFunction rồi giả0, không thêm fallback theo catalog.

R02: Trong `LocalApp.crm_m1_sao_ke`, giữ nguyên quyền trước ingest, fact hợp đồng, `Store.ingest`/engine M1, converter hiện có và kiểm `chieu['ok']`; return đúng historical CRM API `{'m1': <các field hiện tại trừ sqlite>, 'chieu': chieu}`. Bỏ duy nhất lời gọi/properties `proof` ở CRM return. Không trả proof giả, PROVEN giả hoặc success khi converter từ chối. Không đổi response/logic route M9.

Giữ byte-exact `_ghi_proof_tien` và M9 caller hiện tại dòng418 trong `server.py`, mọi phần M9 khác và filter domain hiện có trong `crm.py`. Không sửa `m1_demo.py` hoặc helper tiền trong `lien_ket_chung.py`; việc chúng chưa dùng được trên neutral lineage không cấp quyền kích hoạt chúng.

## 4. Bảo toàn nghiệp vụ/quyền/SQL hiện có

Không sửa migrations/constants/helpers/registry/checksum1–16, không thêm migration17, schema/table/function/grant hoặc financial ledger. `pg_migrations.py` SHA `4d53efd98740047d6fff74d941795b86899082f76dfacb6a49c1b299f135ab3b`, `m1_demo.py` SHA `9cad67529b155c2be702317f5cac20fff5ef2db33b37b0b942bb6856781e3c2e`, `lien_ket_chung.py` SHA `9f256e3b622ded3a0ec10fb6ee471f358ae95173f7e7b7d2295d81805b074b8b` phải nguyên byte.
Giữ `lien_ket`, `go_lien_ket`, quyền trước replay, lock HĐ→BANK→đợt, hiệu lực/phụ lục, PN/currency, hai budget guards CRM, current HUY/idempotency và audit. Không thay GUC/owner để bỏ guard. Không retag CRM/M1 core hoặc sửa parent quantity L11.
Giới hạn rõ: M11 bank guard hiện SUM các link có `lich_thu_id`; lượt này bảo toàn compatibility và conservation CRM đã có, không tuyên bố tạo all-module allocation ledger hoặc nghiệm thu G10/period/production.

## 5. File regression mới — native neutral16, không giả thành công

Tham khảo setup/API thật trong `tests/test_crm_k2.py` (helpers136–166, t08, t15) và `tests/test_m2_http.py`42–92; chỉ tái sử dụng official `fixtures_crm`, `crm_demo`, LocalApp/LocalServer và pipeline M1 hiện có. Không inherit/import test classes hoặc state/setup cũ, không chạy migration9/legacy-M13 rồi gọi đó là neutral16, không mock product/UDF/converter/kết quả lỗi.
Root cấp `KHO_PG_DSN_TEST` khi chạy sau review; test không tìm/đọc `.env` hoặc credentials trên đĩa. Tạo fresh retained `kho_test_*`, migrate mặc định16, official CRM DEMO seed; HTTP/service dùng LOGIN thật NOSUPERUSER/NOBYPASSRLS member app_web, không owner. Admin chỉ setup/projection/read-only observer. Loopback/cổng ngẫu nhiên, token/cookie thật; secrets chỉ memory, không argv/log/assertion output. Close đúng connections/server/thread đã sở hữu; giữ artifacts.
- T01: fresh neutral16, chứng minh legacy money function/table không tồn tại; GET CRM bằng KT_A vẫn200, `tien=[]`; actor không CRM bị chặn. Không kiểm bằng text/regex source đơn thuần.
- T02: actual HTTP `m1-sao-ke` nhận fixture `PN_DEMO_A:truoc_hop_dong`300m qua ingest→engine→converter;200, exact top-level keys `m1/chieu`, converter success thật, một BANK logic/proposal đúng nguồn, `da_noi='0'`; legacy objects vẫn vắng. Retry không thêm BANK/proposal/dòng hoặc đổi PK/business fields; technical ingestion evidence chỉ được khác khi khai báo rõ.
- T03: actual #6 `kcn_goc`→KT kiểm→CFO V3/V4 DEMO duyệt; lịch300m/1.2b/1.5b đúng fixture. Nối một phần, kiểm `da_noi` tăng chính xác; cùng key/body replay cùng ID, changed body từ chối; gỡ→HUY, `da_noi` giảm đúng, old key trả currentHUY và không tái tạo.
- T04: giữ các positive/negative guards hiện có: vượt phần BANK còn lại trong khi nghĩa vụ đủ, vượt nghĩa vụ trong khi BANK đủ, khác PN/CFO không có quyền nối. Dùng inputs/fixtures DEMO sẵn và quantities viết tay; ca âm phải chặn đúng lỗi với business rows/audit/sequence/artifacts0delta. Không đếm một lỗi tham chiếu/thiếu dữ liệu làm budget PASS.
- T05: có HTTP positive trước/sau, KT_B không thấy tiền/HĐ của A; snapshot nonempty BANK/proposal/PK/source hashes giữ qua link/undo và denied actions; full read SUM phải bao hết active CRM links của BANK. Không dùng counts-only để che mutation hoặc chỉ assert không exception.
Thiếu runtime/driver/DSN là NOT_RUN/skip có khai báo, không PASS. Không sửa expected của tests cũ để làm xanh; bất kỳ setup/contract blocker ngoài hai hunk báo Root thay vì mở rộng allowlist.

## 6. Báo cáo và giới hạn nghiệm thu

Đọc technical reports công khai `REVIEW-CRM-HOST-06.md`, `REVIEW-CRM-HTTP-03.md`, `REVIEW-CRM-M1-03.md` để giữ đúng historical behavior; không đọc private var/credentials/source apps. Historical host06 đã kiểm HTTP KT→CFO/export/restart, GUI vẫn chưa nghiệm thu; không biến report đó thành current-source PASS.
Report mới ghi hai exact diffs, bốn-file scope, protected hashes, test case definitions và self-tests NOT_RUN/CODE_ONLY; không tuyên bố đã chạy HTTP/GUI/PG hoặc full CRM/M1/M3/33. Root freeze/review và thực thi chọn lọc độc lập sau actual terminal. Lượt này không thay yêu cầu mới M2/M5 về báo cáo thiếu/thừa/trùng theo từng dòng/số lượng và không mở lại Q09 hay M9.
